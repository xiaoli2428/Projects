"""Token-based voting system."""
import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from decimal import Decimal
from web3 import Web3

from config.networks import get_network_config
from contracts.smart_contract import SmartContractManager

logger = logging.getLogger(__name__)


class VoteType(Enum):
    """Vote types."""
    AGAINST = 0
    FOR = 1
    ABSTAIN = 2


@dataclass
class Vote:
    """Individual vote record."""
    voter: str
    proposal_id: str
    vote_type: VoteType
    voting_power: Decimal
    reason: Optional[str] = None
    timestamp: int = field(default_factory=lambda: int(time. time()))
    tx_hash: Optional[str] = None


@dataclass
class VotingPower:
    """Voting power data."""
    address: str
    token_balance: Decimal
    delegated_power: Decimal
    delegated_to: Optional[str] = None
    total_power: Decimal = Decimal(0)
    snapshot_block: Optional[int] = None
    
    def __post_init__(self):
        if self.delegated_to:
            self.total_power = Decimal(0)  # Delegated away
        else:
            self.total_power = self.token_balance + self. delegated_power


@dataclass
class DelegationInfo:
    """Delegation information."""
    delegator: str
    delegatee: str
    power: Decimal
    timestamp: int


class VotingManager:
    """Manager for token-based voting."""
    
    # ERC20Votes ABI (OpenZeppelin Votes compatible)
    VOTES_TOKEN_ABI = [
        {"inputs": [{"name": "account", "type": "address"}], "name": "getVotes", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "account", "type": "address"}, {"name": "blockNumber", "type": "uint256"}], "name": "getPastVotes", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "delegatee", "type": "address"}], "name": "delegate", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "account", "type": "address"}], "name": "delegates", "outputs": [{"name": "", "type": "address"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    ]
    
    def __init__(
        self,
        token_address: str,
        network: str = "ethereum",
        private_key: Optional[str] = None
    ):
        """
        Initialize voting manager.
        
        Args:
            token_address: Governance token address
            network: Network name
            private_key: Private key for transactions
        """
        self.token_address = Web3.to_checksum_address(token_address)
        self.network = network
        self._contract_manager = SmartContractManager(network, private_key)
        self._token = self._contract_manager.load_contract(
            token_address, self. VOTES_TOKEN_ABI
        )
        self._votes: Dict[str, List[Vote]] = {}  # proposal_id -> votes
        self._delegations: Dict[str, DelegationInfo] = {}  # delegator -> delegation
        
    def get_voting_power(
        self,
        address: str,
        block_number: Optional[int] = None
    ) -> VotingPower:
        """
        Get voting power for an address. 
        
        Args:
            address: Wallet address
            block_number: Optional snapshot block
            
        Returns:
            VotingPower instance
        """
        address = Web3.to_checksum_address(address)
        
        # Get current votes
        if block_number:
            result = self._contract_manager.read_contract(
                self._token, "getPastVotes", address, block_number
            )
        else:
            result = self._contract_manager. read_contract(
                self._token, "getVotes", address
            )
        
        votes = Decimal(result.data) / Decimal(10**18) if result.success else Decimal(0)
        
        # Get token balance
        balance_result = self._contract_manager.read_contract(
            self._token, "balanceOf", address
        )
        balance = Decimal(balance_result.data) / Decimal(10**18) if balance_result.success else Decimal(0)
        
        # Get delegate
        delegate_result = self._contract_manager.read_contract(
            self._token, "delegates", address
        )
        delegatee = delegate_result.data if delegate_result.success else None
        
        # Calculate delegated power received
        delegated_power = votes - balance if votes > balance else Decimal(0)
        
        return VotingPower(
            address=address,
            token_balance=balance,
            delegated_power=delegated_power,
            delegated_to=delegatee if delegatee and delegatee. lower() != address. lower() else None,
            total_power=votes,
            snapshot_block=block_number
        )
    
    def delegate(
        self,
        delegatee: str,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Delegate voting power to another address.
        
        Args:
            delegatee: Address to delegate to
            gas_limit: Optional gas limit
            
        Returns:
            Transaction result
        """
        delegatee = Web3.to_checksum_address(delegatee)
        
        result = self._contract_manager.write_contract(
            self._token,
            "delegate",
            delegatee,
            gas_limit=gas_limit
        )
        
        if result.success:
            logger.info(f"Delegated voting power to {delegatee}")
            return {
                'success': True,
                'tx_hash': result.tx_hash,
                'gas_used': result. gas_used
            }
        
        return {'success': False, 'error': result.error}
    
    def self_delegate(self, gas_limit: Optional[int] = None) -> Dict[str, Any]:
        """Delegate to self to activate voting power."""
        if self._contract_manager.account:
            return self.delegate(
                self._contract_manager.account.address,
                gas_limit
            )
        return {'success': False, 'error': 'No account configured'}
    
    def get_delegate(self, address: str) -> Optional[str]:
        """Get the delegatee for an address."""
        address = Web3.to_checksum_address(address)
        
        result = self._contract_manager.read_contract(
            self._token, "delegates", address
        )
        
        return result.data if result.success else None
    
    def get_total_supply(self) -> Decimal:
        """Get total token supply."""
        result = self._contract_manager.read_contract(
            self._token, "totalSupply"
        )
        
        if result.success:
            return Decimal(result.data) / Decimal(10**18)
        return Decimal(0)
    
    def calculate_vote_weight(
        self,
        voting_power: Decimal,
        total_supply: Decimal,
        method: str = "linear"
    ) -> Decimal:
        """
        Calculate vote weight using different methods.
        
        Args:
            voting_power: User's voting power
            total_supply: Total token supply
            method: Weighting method ('linear', 'quadratic', 'capped')
            
        Returns:
            Calculated vote weight
        """
        if total_supply == 0:
            return Decimal(0)
        
        if method == "linear":
            return voting_power
        
        elif method == "quadratic":
            # Quadratic voting: weight = sqrt(tokens)
            import math
            return Decimal(str(math.sqrt(float(voting_power))))
        
        elif method == "capped":
            # Capped at 5% of total supply
            max_weight = total_supply * Decimal("0.05")
            return min(voting_power, max_weight)
        
        return voting_power
    
    def record_vote(
        self,
        voter: str,
        proposal_id: str,
        vote_type: VoteType,
        voting_power: Decimal,
        reason: Optional[str] = None,
        tx_hash: Optional[str] = None
    ) -> Vote:
        """
        Record a vote in the local tracker.
        
        Args:
            voter: Voter address
            proposal_id: Proposal ID
            vote_type: Vote type
            voting_power: Voting power used
            reason: Optional vote reason
            tx_hash: Transaction hash
            
        Returns:
            Vote record
        """
        voter = Web3.to_checksum_address(voter)
        
        vote = Vote(
            voter=voter,
            proposal_id=proposal_id,
            vote_type=vote_type,
            voting_power=voting_power,
            reason=reason,
            tx_hash=tx_hash
        )
        
        if proposal_id not in self._votes:
            self._votes[proposal_id] = []
        
        self._votes[proposal_id].append(vote)
        logger.info(f"Recorded vote from {voter} on proposal {proposal_id}")
        
        return vote
    
    def get_proposal_votes(self, proposal_id: str) -> List[Vote]:
        """Get all votes for a proposal."""
        return self._votes.get(proposal_id, [])
    
    def get_vote_summary(self, proposal_id: str) -> Dict[str, Any]:
        """Get vote summary for a proposal."""
        votes = self.get_proposal_votes(proposal_id)
        
        for_power = Decimal(0)
        against_power = Decimal(0)
        abstain_power = Decimal(0)
        
        for vote in votes:
            if vote.vote_type == VoteType.FOR:
                for_power += vote.voting_power
            elif vote.vote_type == VoteType.AGAINST:
                against_power += vote.voting_power
            else:
                abstain_power += vote.voting_power
        
        total = for_power + against_power + abstain_power
        
        return {
            'proposal_id': proposal_id,
            'total_votes': len(votes),
            'for': {
                'power': str(for_power),
                'percentage': str((for_power / total * 100) if total > 0 else 0)
            },
            'against': {
                'power': str(against_power),
                'percentage': str((against_power / total * 100) if total > 0 else 0)
            },
            'abstain': {
                'power': str(abstain_power),
                'percentage': str((abstain_power / total * 100) if total > 0 else 0)
            },
            'total_power': str(total)
        }
    
    def get_voter_history(self, address: str) -> List[Vote]:
        """Get voting history for an address."""
        address = Web3.to_checksum_address(address)
        
        history = []
        for votes in self._votes. values():
            for vote in votes:
                if vote.voter. lower() == address. lower():
                    history.append(vote)
        
        return sorted(history, key=lambda v: v.timestamp, reverse=True)
    
    def calculate_participation_rate(self, proposal_id: str) -> Decimal:
        """Calculate voter participation rate for a proposal."""
        total_supply = self.get_total_supply()
        if total_supply == 0:
            return Decimal(0)
        
        votes = self.get_proposal_votes(proposal_id)
        total_voted = sum(v.voting_power for v in votes)
        
        return (total_voted / total_supply) * Decimal(100)
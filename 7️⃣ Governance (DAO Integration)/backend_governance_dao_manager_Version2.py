"""DAO governance management."""
import logging
import time
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal
from web3 import Web3

from config. networks import get_network_config
from contracts.smart_contract import SmartContractManager

logger = logging. getLogger(__name__)


class ProposalStatus(Enum):
    """Proposal status."""
    PENDING = "pending"
    ACTIVE = "active"
    SUCCEEDED = "succeeded"
    DEFEATED = "defeated"
    QUEUED = "queued"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


@dataclass
class Proposal:
    """DAO proposal."""
    proposal_id: str
    title: str
    description: str
    proposer: str
    status: ProposalStatus
    for_votes: Decimal
    against_votes: Decimal
    abstain_votes: Decimal
    start_time: int
    end_time: int
    execution_time: Optional[int] = None
    targets: List[str] = field(default_factory=list)
    values: List[int] = field(default_factory=list)
    calldatas: List[bytes] = field(default_factory=list)
    snapshot_block: Optional[int] = None
    quorum: Decimal = Decimal(0)
    
    @property
    def total_votes(self) -> Decimal:
        """Get total votes cast."""
        return self.for_votes + self.against_votes + self.abstain_votes
    
    @property
    def for_percentage(self) -> Decimal:
        """Get percentage of for votes."""
        if self.total_votes == 0:
            return Decimal(0)
        return (self.for_votes / self.total_votes) * Decimal(100)
    
    @property
    def has_quorum(self) -> bool:
        """Check if proposal has reached quorum."""
        return self.total_votes >= self. quorum
    
    @property
    def is_passed(self) -> bool:
        """Check if proposal has passed."""
        return self.has_quorum and self.for_votes > self. against_votes


class DAOManager:
    """Manager for DAO governance operations."""
    
    # Standard Governor ABI (OpenZeppelin Governor compatible)
    GOVERNOR_ABI = [
        {"inputs": [{"name": "targets", "type": "address[]"}, {"name": "values", "type": "uint256[]"}, {"name": "calldatas", "type": "bytes[]"}, {"name": "description", "type": "string"}], "name": "propose", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "proposalId", "type": "uint256"}, {"name": "support", "type": "uint8"}], "name": "castVote", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "proposalId", "type": "uint256"}, {"name": "support", "type": "uint8"}, {"name": "reason", "type": "string"}], "name": "castVoteWithReason", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "targets", "type": "address[]"}, {"name": "values", "type": "uint256[]"}, {"name": "calldatas", "type": "bytes[]"}, {"name": "descriptionHash", "type": "bytes32"}], "name": "execute", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "payable", "type": "function"},
        {"inputs": [{"name": "proposalId", "type": "uint256"}], "name": "state", "outputs": [{"name": "", "type": "uint8"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "proposalId", "type": "uint256"}], "name": "proposalVotes", "outputs": [{"name": "againstVotes", "type": "uint256"}, {"name": "forVotes", "type": "uint256"}, {"name": "abstainVotes", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "proposalId", "type": "uint256"}], "name": "proposalSnapshot", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "proposalId", "type": "uint256"}], "name": "proposalDeadline", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "quorum", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "votingDelay", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "votingPeriod", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "account", "type": "address"}, {"name": "blockNumber", "type": "uint256"}], "name": "getVotes", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "account", "type": "address"}, {"name": "proposalId", "type": "uint256"}], "name": "hasVoted", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "view", "type": "function"},
    ]
    
    def __init__(
        self,
        governor_address: str,
        network: str = "ethereum",
        private_key: Optional[str] = None
    ):
        """
        Initialize DAO manager.
        
        Args:
            governor_address: Governor contract address
            network: Network name
            private_key: Private key for transactions
        """
        self.governor_address = Web3.to_checksum_address(governor_address)
        self.network = network
        self._contract_manager = SmartContractManager(network, private_key)
        self._governor = self._contract_manager. load_contract(
            governor_address, self. GOVERNOR_ABI
        )
        self._proposals: Dict[str, Proposal] = {}
        
    def create_proposal(
        self,
        title: str,
        description: str,
        targets: List[str],
        values: List[int],
        calldatas: List[bytes],
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Create a new governance proposal.
        
        Args:
            title: Proposal title
            description: Proposal description
            targets: Target contract addresses
            values: ETH values for each call
            calldatas: Encoded function calls
            gas_limit: Optional gas limit
            
        Returns:
            Transaction result with proposal ID
        """
        # Format description with title
        full_description = f"# {title}\n\n{description}"
        
        # Convert addresses to checksum
        targets = [Web3.to_checksum_address(t) for t in targets]
        
        result = self._contract_manager.write_contract(
            self._governor,
            "propose",
            targets,
            values,
            calldatas,
            full_description,
            gas_limit=gas_limit
        )
        
        if result.success:
            # Extract proposal ID from receipt logs
            logger.info(f"Created proposal: {title}")
            return {
                'success': True,
                'tx_hash': result.tx_hash,
                'gas_used': result.gas_used
            }
        
        return {'success': False, 'error': result.error}
    
    def get_proposal_state(self, proposal_id: int) -> ProposalStatus:
        """Get the current state of a proposal."""
        result = self._contract_manager.read_contract(
            self._governor, "state", proposal_id
        )
        
        if result.success:
            states = [
                ProposalStatus.PENDING,
                ProposalStatus.ACTIVE,
                ProposalStatus.CANCELLED,
                ProposalStatus.DEFEATED,
                ProposalStatus.SUCCEEDED,
                ProposalStatus.QUEUED,
                ProposalStatus. EXPIRED,
                ProposalStatus. EXECUTED
            ]
            return states[result.data] if result.data < len(states) else ProposalStatus. PENDING
        
        return ProposalStatus. PENDING
    
    def get_proposal_votes(self, proposal_id: int) -> Dict[str, Decimal]:
        """Get vote counts for a proposal."""
        result = self._contract_manager.read_contract(
            self._governor, "proposalVotes", proposal_id
        )
        
        if result. success:
            against, for_votes, abstain = result.data
            return {
                'for': Decimal(for_votes) / Decimal(10**18),
                'against': Decimal(against) / Decimal(10**18),
                'abstain': Decimal(abstain) / Decimal(10**18)
            }
        
        return {'for': Decimal(0), 'against': Decimal(0), 'abstain': Decimal(0)}
    
    def cast_vote(
        self,
        proposal_id: int,
        support: int,  # 0=against, 1=for, 2=abstain
        reason: Optional[str] = None,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Cast a vote on a proposal.
        
        Args:
            proposal_id: Proposal ID
            support: Vote type (0=against, 1=for, 2=abstain)
            reason: Optional vote reason
            gas_limit: Optional gas limit
            
        Returns:
            Transaction result
        """
        if reason:
            result = self._contract_manager. write_contract(
                self._governor,
                "castVoteWithReason",
                proposal_id,
                support,
                reason,
                gas_limit=gas_limit
            )
        else:
            result = self._contract_manager.write_contract(
                self._governor,
                "castVote",
                proposal_id,
                support,
                gas_limit=gas_limit
            )
        
        if result.success:
            vote_type = ['against', 'for', 'abstain'][support]
            logger.info(f"Cast vote {vote_type} on proposal {proposal_id}")
            return {
                'success': True,
                'tx_hash': result.tx_hash,
                'gas_used': result.gas_used
            }
        
        return {'success': False, 'error': result.error}
    
    def execute_proposal(
        self,
        targets: List[str],
        values: List[int],
        calldatas: List[bytes],
        description_hash: bytes,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a passed proposal.
        
        Args:
            targets: Target addresses
            values: ETH values
            calldatas: Encoded calls
            description_hash: Hash of proposal description
            gas_limit: Optional gas limit
            
        Returns:
            Transaction result
        """
        targets = [Web3. to_checksum_address(t) for t in targets]
        
        result = self._contract_manager.write_contract(
            self._governor,
            "execute",
            targets,
            values,
            calldatas,
            description_hash,
            gas_limit=gas_limit
        )
        
        if result. success:
            logger.info("Executed proposal")
            return {
                'success': True,
                'tx_hash': result.tx_hash,
                'gas_used': result. gas_used
            }
        
        return {'success': False, 'error': result.error}
    
    def has_voted(self, account: str, proposal_id: int) -> bool:
        """Check if an account has voted on a proposal."""
        result = self._contract_manager.read_contract(
            self._governor,
            "hasVoted",
            Web3.to_checksum_address(account),
            proposal_id
        )
        return result.data if result.success else False
    
    def get_voting_power(self, account: str, block_number: int) -> Decimal:
        """Get voting power of an account at a specific block."""
        result = self._contract_manager.read_contract(
            self._governor,
            "getVotes",
            Web3.to_checksum_address(account),
            block_number
        )
        
        if result. success:
            return Decimal(result. data) / Decimal(10**18)
        return Decimal(0)
    
    def get_quorum(self) -> Decimal:
        """Get the quorum requirement."""
        result = self._contract_manager.read_contract(self._governor, "quorum")
        if result.success:
            return Decimal(result.data) / Decimal(10**18)
        return Decimal(0)
    
    def get_voting_delay(self) -> int:
        """Get the voting delay in blocks."""
        result = self._contract_manager.read_contract(self._governor, "votingDelay")
        return result.data if result.success else 0
    
    def get_voting_period(self) -> int:
        """Get the voting period in blocks."""
        result = self._contract_manager.read_contract(self._governor, "votingPeriod")
        return result.data if result. success else 0
    
    def get_active_proposals(self) -> List[Proposal]:
        """Get all active proposals."""
        return [
            p for p in self._proposals. values()
            if p. status == ProposalStatus.ACTIVE
        ]
    
    def get_proposal_summary(self, proposal_id: int) -> Dict[str, Any]:
        """Get a summary of a proposal."""
        state = self.get_proposal_state(proposal_id)
        votes = self.get_proposal_votes(proposal_id)
        
        return {
            'proposal_id': proposal_id,
            'status': state.value,
            'votes': {
                'for': str(votes['for']),
                'against': str(votes['against']),
                'abstain': str(votes['abstain']),
                'total': str(votes['for'] + votes['against'] + votes['abstain'])
            },
            'quorum': str(self.get_quorum())
        }
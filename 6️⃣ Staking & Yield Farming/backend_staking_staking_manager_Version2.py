"""Staking and yield farming management."""
import logging
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timedelta
from web3 import Web3

from config.networks import get_network_config
from contracts.smart_contract import SmartContractManager

logger = logging.getLogger(__name__)


@dataclass
class PoolInfo:
    """Staking pool information."""
    pool_id: str
    name: str
    staking_token: str
    reward_token: str
    total_staked: Decimal
    reward_rate: Decimal  # tokens per second
    apy: Decimal
    lock_period: int  # seconds
    min_stake: Decimal
    max_stake: Optional[Decimal]
    is_active: bool
    start_time: int
    end_time: Optional[int]
    

@dataclass
class StakePosition:
    """User stake position."""
    user_address: str
    pool_id: str
    staked_amount: Decimal
    reward_earned: Decimal
    reward_claimed: Decimal
    stake_timestamp: int
    unlock_timestamp: int
    last_update: int
    is_locked: bool


@dataclass
class FarmPosition:
    """Yield farming position."""
    user_address: str
    farm_id: str
    lp_token: str
    lp_amount: Decimal
    token0_amount: Decimal
    token1_amount: Decimal
    pending_rewards: Dict[str, Decimal]
    entry_timestamp: int


class StakingManager:
    """Manager for staking operations."""
    
    # Standard staking contract ABI
    STAKING_ABI = [
        {"inputs": [{"name": "amount", "type": "uint256"}], "name": "stake", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "amount", "type": "uint256"}], "name": "withdraw", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [], "name": "getReward", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [], "name": "exit", "outputs": [], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "account", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [{"name": "account", "type": "address"}], "name": "earned", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "rewardRate", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
        {"inputs": [], "name": "rewardPerToken", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"},
    ]
    
    def __init__(self, network: str = "ethereum", private_key: Optional[str] = None):
        """
        Initialize staking manager.
        
        Args:
            network: Network name
            private_key: Private key for transactions
        """
        self.network = network
        self._config = get_network_config(network)
        self._contract_manager = SmartContractManager(network, private_key)
        self._pools: Dict[str, PoolInfo] = {}
        self._user_positions: Dict[str, Dict[str, StakePosition]] = {}  # address -> pool_id -> position
        
    def register_pool(
        self,
        pool_id: str,
        contract_address: str,
        name: str,
        staking_token: str,
        reward_token: str,
        lock_period: int = 0,
        min_stake: Decimal = Decimal(0),
        max_stake: Optional[Decimal] = None,
        custom_abi: Optional[List[Dict]] = None
    ) -> PoolInfo:
        """
        Register a staking pool.
        
        Args:
            pool_id: Unique pool identifier
            contract_address: Staking contract address
            name: Pool display name
            staking_token: Token to stake
            reward_token: Reward token address
            lock_period: Lock period in seconds
            min_stake: Minimum stake amount
            max_stake: Maximum stake amount
            custom_abi: Custom contract ABI
            
        Returns:
            PoolInfo instance
        """
        abi = custom_abi or self.STAKING_ABI
        contract = self._contract_manager.load_contract(contract_address, abi)
        
        # Get pool data from contract
        total_staked_result = self._contract_manager. read_contract(
            contract, "totalSupply"
        )
        reward_rate_result = self._contract_manager.read_contract(
            contract, "rewardRate"
        )
        
        total_staked = Decimal(total_staked_result. data or 0) / Decimal(10**18)
        reward_rate = Decimal(reward_rate_result.data or 0) / Decimal(10**18)
        
        # Calculate APY
        apy = self._calculate_apy(reward_rate, total_staked)
        
        pool_info = PoolInfo(
            pool_id=pool_id,
            name=name,
            staking_token=staking_token,
            reward_token=reward_token,
            total_staked=total_staked,
            reward_rate=reward_rate,
            apy=apy,
            lock_period=lock_period,
            min_stake=min_stake,
            max_stake=max_stake,
            is_active=True,
            start_time=int(time.time()),
            end_time=None
        )
        
        self._pools[pool_id] = pool_info
        logger.info(f"Registered staking pool: {pool_id}")
        
        return pool_info
    
    def _calculate_apy(
        self,
        reward_rate: Decimal,
        total_staked: Decimal,
        reward_price: Decimal = Decimal(1),
        stake_price: Decimal = Decimal(1)
    ) -> Decimal:
        """Calculate APY for a staking pool."""
        if total_staked == 0:
            return Decimal(0)
        
        # Annual rewards
        seconds_per_year = Decimal(365 * 24 * 60 * 60)
        annual_rewards = reward_rate * seconds_per_year
        
        # APY = (annual_rewards * reward_price) / (total_staked * stake_price) * 100
        apy = (annual_rewards * reward_price) / (total_staked * stake_price) * Decimal(100)
        
        return apy. quantize(Decimal('0.01'))
    
    def get_pool(self, pool_id: str) -> Optional[PoolInfo]:
        """Get pool information."""
        return self._pools.get(pool_id)
    
    def get_all_pools(self) -> List[PoolInfo]:
        """Get all registered pools."""
        return list(self._pools.values())
    
    def get_user_position(
        self,
        user_address: str,
        pool_id: str
    ) -> Optional[StakePosition]:
        """
        Get user's stake position in a pool.
        
        Args:
            user_address: User wallet address
            pool_id: Pool identifier
            
        Returns:
            StakePosition or None
        """
        address = Web3.to_checksum_address(user_address)
        
        if address not in self._user_positions:
            return None
        
        return self._user_positions[address].get(pool_id)
    
    def get_staked_balance(
        self,
        user_address: str,
        pool_id: str,
        contract_address: str
    ) -> Decimal:
        """Get user's staked balance from contract."""
        contract = self._contract_manager.get_contract(contract_address)
        if not contract:
            contract = self._contract_manager.load_contract(
                contract_address, self.STAKING_ABI
            )
        
        result = self._contract_manager.read_contract(
            contract,
            "balanceOf",
            Web3.to_checksum_address(user_address)
        )
        
        if result.success:
            return Decimal(result.data) / Decimal(10**18)
        return Decimal(0)
    
    def get_pending_rewards(
        self,
        user_address: str,
        pool_id: str,
        contract_address: str
    ) -> Decimal:
        """Get user's pending rewards."""
        contract = self._contract_manager.get_contract(contract_address)
        if not contract:
            contract = self._contract_manager.load_contract(
                contract_address, self. STAKING_ABI
            )
        
        result = self._contract_manager.read_contract(
            contract,
            "earned",
            Web3.to_checksum_address(user_address)
        )
        
        if result.success:
            return Decimal(result.data) / Decimal(10**18)
        return Decimal(0)
    
    def stake(
        self,
        pool_id: str,
        contract_address: str,
        amount: Decimal,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Stake tokens in a pool.
        
        Args:
            pool_id: Pool identifier
            contract_address: Staking contract address
            amount: Amount to stake
            gas_limit: Optional gas limit
            
        Returns:
            Transaction result
        """
        pool = self._pools.get(pool_id)
        if not pool:
            return {'success': False, 'error': 'Pool not found'}
        
        if amount < pool.min_stake:
            return {'success': False, 'error': f'Minimum stake is {pool.min_stake}'}
        
        if pool.max_stake and amount > pool.max_stake:
            return {'success': False, 'error': f'Maximum stake is {pool.max_stake}'}
        
        contract = self._contract_manager.get_contract(contract_address)
        if not contract:
            contract = self._contract_manager.load_contract(
                contract_address, self. STAKING_ABI
            )
        
        # Convert amount to wei
        amount_wei = int(amount * Decimal(10**18))
        
        result = self._contract_manager.write_contract(
            contract,
            "stake",
            amount_wei,
            gas_limit=gas_limit
        )
        
        if result.success:
            logger.info(f"Staked {amount} tokens in pool {pool_id}")
            return {
                'success': True,
                'tx_hash': result. tx_hash,
                'gas_used': result.gas_used
            }
        
        return {'success': False, 'error': result.error}
    
    def unstake(
        self,
        pool_id: str,
        contract_address: str,
        amount: Decimal,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Unstake tokens from a pool. 
        
        Args:
            pool_id: Pool identifier
            contract_address: Staking contract address
            amount: Amount to unstake
            gas_limit: Optional gas limit
            
        Returns:
            Transaction result
        """
        pool = self._pools.get(pool_id)
        if not pool:
            return {'success': False, 'error': 'Pool not found'}
        
        contract = self._contract_manager.get_contract(contract_address)
        if not contract:
            contract = self._contract_manager.load_contract(
                contract_address, self.STAKING_ABI
            )
        
        amount_wei = int(amount * Decimal(10**18))
        
        result = self._contract_manager.write_contract(
            contract,
            "withdraw",
            amount_wei,
            gas_limit=gas_limit
        )
        
        if result.success:
            logger.info(f"Unstaked {amount} tokens from pool {pool_id}")
            return {
                'success': True,
                'tx_hash': result. tx_hash,
                'gas_used': result.gas_used
            }
        
        return {'success': False, 'error': result. error}
    
    def claim_rewards(
        self,
        pool_id: str,
        contract_address: str,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Claim pending rewards from a pool. 
        
        Args:
            pool_id: Pool identifier
            contract_address: Staking contract address
            gas_limit: Optional gas limit
            
        Returns:
            Transaction result
        """
        contract = self._contract_manager.get_contract(contract_address)
        if not contract:
            contract = self._contract_manager.load_contract(
                contract_address, self.STAKING_ABI
            )
        
        result = self._contract_manager.write_contract(
            contract,
            "getReward",
            gas_limit=gas_limit
        )
        
        if result.success:
            logger.info(f"Claimed rewards from pool {pool_id}")
            return {
                'success': True,
                'tx_hash': result.tx_hash,
                'gas_used': result.gas_used
            }
        
        return {'success': False, 'error': result.error}
    
    def exit_pool(
        self,
        pool_id: str,
        contract_address: str,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Exit pool - unstake all and claim rewards.
        
        Args:
            pool_id: Pool identifier
            contract_address: Staking contract address
            gas_limit: Optional gas limit
            
        Returns:
            Transaction result
        """
        contract = self._contract_manager.get_contract(contract_address)
        if not contract:
            contract = self._contract_manager.load_contract(
                contract_address, self.STAKING_ABI
            )
        
        result = self._contract_manager.write_contract(
            contract,
            "exit",
            gas_limit=gas_limit
        )
        
        if result.success:
            logger.info(f"Exited pool {pool_id}")
            return {
                'success': True,
                'tx_hash': result. tx_hash,
                'gas_used': result.gas_used
            }
        
        return {'success': False, 'error': result. error}
    
    def calculate_rewards(
        self,
        staked_amount: Decimal,
        reward_rate: Decimal,
        duration_seconds: int
    ) -> Decimal:
        """Calculate expected rewards for a staking duration."""
        return staked_amount * reward_rate * Decimal(duration_seconds) / Decimal(10**18)
    
    def get_pool_statistics(self, pool_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive pool statistics."""
        pool = self._pools.get(pool_id)
        if not pool:
            return None
        
        return {
            'pool_id': pool. pool_id,
            'name': pool.name,
            'total_staked': str(pool.total_staked),
            'apy': str(pool.apy),
            'reward_rate': str(pool.reward_rate),
            'lock_period_days': pool.lock_period / (24 * 60 * 60) if pool.lock_period else 0,
            'min_stake': str(pool.min_stake),
            'max_stake': str(pool.max_stake) if pool.max_stake else None,
            'is_active': pool.is_active
        }
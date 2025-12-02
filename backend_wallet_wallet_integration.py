"""Multi-wallet integration and management."""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from decimal import Decimal
from web3 import Web3
from ens import ENS

from config.networks import get_network_config, NETWORKS, NetworkConfig

logger = logging.getLogger(__name__)


@dataclass
class WalletInfo:
    """Wallet information."""
    address: str
    checksum_address: str
    ens_name: Optional[str] = None
    native_balance: Decimal = Decimal(0)
    token_balances: Dict[str, Decimal] = None
    chain_id: int = 1
    is_contract: bool = False
    
    def __post_init__(self):
        if self.token_balances is None:
            self.token_balances = {}


@dataclass
class TokenInfo:
    """ERC20 token information."""
    address: str
    name: str
    symbol: str
    decimals: int
    total_supply: int
    balance: Optional[Decimal] = None


class WalletManager:
    """Manager for wallet operations across multiple chains."""
    
    # Standard ERC20 ABI for common operations
    ERC20_ABI = [
        {"constant": True, "inputs": [], "name": "name", "outputs": [{"name": "", "type": "string"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "symbol", "outputs": [{"name": "", "type": "string"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "decimals", "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "totalSupply", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}, {"name": "_spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "type": "function"},
        {"constant": False, "inputs": [{"name": "_spender", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
        {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    ]
    
    def __init__(self, default_network: str = "ethereum"):
        """
        Initialize wallet manager.
        
        Args:
            default_network: Default network to use
        """
        self. default_network = default_network
        self._web3_instances: Dict[str, Web3] = {}
        self._ens: Optional[ENS] = None
        
        # Initialize Web3 for default network
        self._get_web3(default_network)
        
    def _get_web3(self, network: str) -> Web3:
        """Get or create Web3 instance for a network."""
        if network not in self._web3_instances:
            config = get_network_config(network)
            w3 = Web3(Web3.HTTPProvider(config.rpc_url))
            self._web3_instances[network] = w3
            
            # Initialize ENS for Ethereum mainnet
            if network == "ethereum" and self._ens is None:
                try:
                    self._ens = ENS. from_web3(w3)
                except Exception:
                    pass
                    
        return self._web3_instances[network]
    
    def validate_address(self, address: str) -> bool:
        """
        Validate an Ethereum address.
        
        Args:
            address: Address to validate
            
        Returns:
            True if valid
        """
        return Web3.is_address(address)
    
    def to_checksum(self, address: str) -> str:
        """Convert address to checksum format."""
        return Web3.to_checksum_address(address)
    
    def resolve_ens(self, ens_name: str) -> Optional[str]:
        """
        Resolve ENS name to address. 
        
        Args:
            ens_name: ENS name (e.g., 'vitalik.eth')
            
        Returns:
            Resolved address or None
        """
        if not self._ens:
            return None
            
        try:
            address = self._ens.address(ens_name)
            return address
        except Exception as e:
            logger.error(f"Error resolving ENS: {e}")
            return None
    
    def reverse_ens(self, address: str) -> Optional[str]:
        """
        Get ENS name for an address (reverse lookup).
        
        Args:
            address: Wallet address
            
        Returns:
            ENS name or None
        """
        if not self._ens:
            return None
            
        try:
            name = self._ens.name(address)
            return name
        except Exception as e:
            logger. error(f"Error in reverse ENS lookup: {e}")
            return None
    
    def get_wallet_info(
        self,
        address: str,
        network: str = None,
        include_ens: bool = True
    ) -> WalletInfo:
        """
        Get comprehensive wallet information.
        
        Args:
            address: Wallet address
            network: Network name
            include_ens: Whether to include ENS lookup
            
        Returns:
            WalletInfo instance
        """
        network = network or self. default_network
        w3 = self._get_web3(network)
        config = get_network_config(network)
        
        checksum = self.to_checksum(address)
        
        # Get native balance
        balance_wei = w3.eth.get_balance(checksum)
        balance = Decimal(balance_wei) / Decimal(10 ** config.native_decimals)
        
        # Check if contract
        code = w3.eth.get_code(checksum)
        is_contract = len(code) > 0
        
        # ENS lookup
        ens_name = None
        if include_ens and network == "ethereum":
            ens_name = self.reverse_ens(checksum)
        
        return WalletInfo(
            address=address,
            checksum_address=checksum,
            ens_name=ens_name,
            native_balance=balance,
            chain_id=config. chain_id,
            is_contract=is_contract
        )
    
    def get_native_balance(
        self,
        address: str,
        network: str = None
    ) -> Decimal:
        """Get native token balance."""
        network = network or self. default_network
        w3 = self._get_web3(network)
        config = get_network_config(network)
        
        checksum = self.to_checksum(address)
        balance_wei = w3.eth.get_balance(checksum)
        
        return Decimal(balance_wei) / Decimal(10 ** config.native_decimals)
    
    def get_token_info(
        self,
        token_address: str,
        network: str = None
    ) -> Optional[TokenInfo]:
        """
        Get ERC20 token information.
        
        Args:
            token_address: Token contract address
            network: Network name
            
        Returns:
            TokenInfo instance or None
        """
        network = network or self.default_network
        w3 = self._get_web3(network)
        
        try:
            checksum = self.to_checksum(token_address)
            contract = w3.eth.contract(address=checksum, abi=self.ERC20_ABI)
            
            name = contract.functions. name().call()
            symbol = contract. functions.symbol().call()
            decimals = contract.functions. decimals().call()
            total_supply = contract.functions. totalSupply().call()
            
            return TokenInfo(
                address=checksum,
                name=name,
                symbol=symbol,
                decimals=decimals,
                total_supply=total_supply
            )
        except Exception as e:
            logger. error(f"Error getting token info: {e}")
            return None
    
    def get_token_balance(
        self,
        wallet_address: str,
        token_address: str,
        network: str = None
    ) -> Decimal:
        """
        Get ERC20 token balance.
        
        Args:
            wallet_address: Wallet address
            token_address: Token contract address
            network: Network name
            
        Returns:
            Token balance as Decimal
        """
        network = network or self. default_network
        w3 = self._get_web3(network)
        
        wallet_checksum = self.to_checksum(wallet_address)
        token_checksum = self.to_checksum(token_address)
        
        contract = w3.eth.contract(address=token_checksum, abi=self. ERC20_ABI)
        
        balance = contract. functions.balanceOf(wallet_checksum).call()
        decimals = contract.functions.decimals().call()
        
        return Decimal(balance) / Decimal(10 ** decimals)
    
    def get_multiple_token_balances(
        self,
        wallet_address: str,
        token_addresses: List[str],
        network: str = None
    ) -> Dict[str, Decimal]:
        """
        Get balances for multiple tokens. 
        
        Args:
            wallet_address: Wallet address
            token_addresses: List of token addresses
            network: Network name
            
        Returns:
            Dict mapping token address to balance
        """
        balances = {}
        
        for token in token_addresses:
            try:
                balance = self.get_token_balance(wallet_address, token, network)
                balances[token] = balance
            except Exception as e:
                logger.error(f"Error getting balance for {token}: {e}")
                balances[token] = Decimal(0)
        
        return balances
    
    def get_token_allowance(
        self,
        wallet_address: str,
        token_address: str,
        spender_address: str,
        network: str = None
    ) -> Decimal:
        """
        Get token allowance for a spender. 
        
        Args:
            wallet_address: Token owner address
            token_address: Token contract address
            spender_address: Spender address
            network: Network name
            
        Returns:
            Allowance as Decimal
        """
        network = network or self.default_network
        w3 = self._get_web3(network)
        
        wallet_checksum = self.to_checksum(wallet_address)
        token_checksum = self. to_checksum(token_address)
        spender_checksum = self.to_checksum(spender_address)
        
        contract = w3.eth. contract(address=token_checksum, abi=self.ERC20_ABI)
        
        allowance = contract. functions.allowance(
            wallet_checksum, spender_checksum
        ).call()
        decimals = contract.functions.decimals().call()
        
        return Decimal(allowance) / Decimal(10 ** decimals)
    
    def get_transaction_count(
        self,
        address: str,
        network: str = None
    ) -> int:
        """Get transaction count (nonce) for an address."""
        network = network or self.default_network
        w3 = self._get_web3(network)
        
        checksum = self.to_checksum(address)
        return w3.eth.get_transaction_count(checksum)
    
    def get_gas_price(self, network: str = None) -> Dict[str, int]:
        """
        Get current gas prices.
        
        Args:
            network: Network name
            
        Returns:
            Dict with gas prices in wei
        """
        network = network or self.default_network
        w3 = self._get_web3(network)
        
        gas_price = w3.eth. gas_price
        
        # Try to get EIP-1559 values
        try:
            latest_block = w3.eth.get_block('latest')
            base_fee = latest_block.get('baseFeePerGas', 0)
            
            return {
                'gas_price': gas_price,
                'base_fee': base_fee,
                'max_priority_fee': w3.eth.max_priority_fee if hasattr(w3. eth, 'max_priority_fee') else gas_price // 10,
                'gas_price_gwei': gas_price / 10**9,
            }
        except Exception:
            return {
                'gas_price': gas_price,
                'gas_price_gwei': gas_price / 10**9,
            }
    
    def estimate_transfer_gas(
        self,
        from_address: str,
        to_address: str,
        value_wei: int,
        network: str = None
    ) -> int:
        """Estimate gas for a native token transfer."""
        network = network or self.default_network
        w3 = self._get_web3(network)
        
        return w3.eth. estimate_gas({
            'from': self.to_checksum(from_address),
            'to': self.to_checksum(to_address),
            'value': value_wei
        })
    
    def get_supported_networks(self) -> List[Dict[str, Any]]:
        """Get list of supported networks."""
        return [
            {
                'name': name,
                'chain_id': config.chain_id,
                'display_name': config.name,
                'native_currency': config.native_currency,
                'explorer_url': config. explorer_url,
                'is_testnet': config.is_testnet
            }
            for name, config in NETWORKS.items()
        ]
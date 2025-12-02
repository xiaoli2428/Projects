"""Smart contract interaction utilities."""
import json
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from web3 import Web3
from web3.contract import Contract
from web3.types import TxReceipt, TxParams, Wei
from eth_account import Account
from eth_account.signers. local import LocalAccount

from config.networks import get_network_config, NetworkConfig

logger = logging.getLogger(__name__)


@dataclass
class ContractCall:
    """Result of a contract call."""
    success: bool
    data: Any
    tx_hash: Optional[str] = None
    gas_used: Optional[int] = None
    error: Optional[str] = None


class SmartContractManager:
    """Manager for smart contract interactions."""
    
    def __init__(self, network: str = "ethereum", private_key: Optional[str] = None):
        """
        Initialize the smart contract manager.
        
        Args:
            network: Network name (e.g., 'ethereum', 'bsc', 'polygon')
            private_key: Private key for signing transactions (optional)
        """
        self.network_config: NetworkConfig = get_network_config(network)
        self. w3 = Web3(Web3.HTTPProvider(self.network_config.rpc_url))
        self. account: Optional[LocalAccount] = None
        
        if private_key:
            self. account = Account.from_key(private_key)
            
        self._contracts: Dict[str, Contract] = {}
        self._event_filters: Dict[str, Any] = {}
        
    @property
    def is_connected(self) -> bool:
        """Check if connected to the network."""
        return self.w3.is_connected()
    
    def load_contract(self, address: str, abi: Union[str, List[Dict]]) -> Contract:
        """
        Load a smart contract.
        
        Args:
            address: Contract address
            abi: Contract ABI (JSON string or list)
            
        Returns:
            Contract instance
        """
        if isinstance(abi, str):
            abi = json.loads(abi)
            
        checksum_address = Web3.to_checksum_address(address)
        contract = self. w3.eth. contract(address=checksum_address, abi=abi)
        self._contracts[checksum_address] = contract
        
        logger.info(f"Loaded contract at {checksum_address}")
        return contract
    
    def load_contract_from_file(self, address: str, abi_path: str) -> Contract:
        """Load contract ABI from a JSON file."""
        with open(abi_path, 'r') as f:
            abi = json.load(f)
        return self.load_contract(address, abi)
    
    def get_contract(self, address: str) -> Optional[Contract]:
        """Get a loaded contract by address."""
        checksum_address = Web3.to_checksum_address(address)
        return self._contracts.get(checksum_address)
    
    def read_contract(
        self,
        contract: Contract,
        function_name: str,
        *args,
        **kwargs
    ) -> ContractCall:
        """
        Read data from a smart contract (view/pure function).
        
        Args:
            contract: Contract instance
            function_name: Name of the function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            ContractCall with the result
        """
        try:
            func = getattr(contract. functions, function_name)
            result = func(*args, **kwargs). call()
            return ContractCall(success=True, data=result)
        except Exception as e:
            logger.error(f"Error reading contract: {e}")
            return ContractCall(success=False, data=None, error=str(e))
    
    def write_contract(
        self,
        contract: Contract,
        function_name: str,
        *args,
        value: Wei = Wei(0),
        gas_limit: Optional[int] = None,
        gas_price: Optional[Wei] = None,
        max_fee_per_gas: Optional[Wei] = None,
        max_priority_fee_per_gas: Optional[Wei] = None,
        nonce: Optional[int] = None,
        **kwargs
    ) -> ContractCall:
        """
        Write to a smart contract (state-changing function). 
        
        Args:
            contract: Contract instance
            function_name: Name of the function to call
            *args: Positional arguments for the function
            value: ETH value to send with transaction
            gas_limit: Gas limit for transaction
            gas_price: Gas price (for legacy transactions)
            max_fee_per_gas: Max fee per gas (for EIP-1559)
            max_priority_fee_per_gas: Max priority fee (for EIP-1559)
            nonce: Transaction nonce
            **kwargs: Additional transaction parameters
            
        Returns:
            ContractCall with transaction result
        """
        if not self.account:
            return ContractCall(
                success=False,
                data=None,
                error="No account configured for signing transactions"
            )
        
        try:
            func = getattr(contract.functions, function_name)
            
            # Build transaction
            tx_params: TxParams = {
                'from': self.account.address,
                'value': value,
                'chainId': self.network_config.chain_id,
            }
            
            if nonce is None:
                tx_params['nonce'] = self.w3.eth.get_transaction_count(self.account.address)
            else:
                tx_params['nonce'] = nonce
            
            # Gas settings
            if gas_limit:
                tx_params['gas'] = gas_limit
            
            if max_fee_per_gas and max_priority_fee_per_gas:
                # EIP-1559 transaction
                tx_params['maxFeePerGas'] = max_fee_per_gas
                tx_params['maxPriorityFeePerGas'] = max_priority_fee_per_gas
            elif gas_price:
                tx_params['gasPrice'] = gas_price
            else:
                tx_params['gasPrice'] = self.w3.eth.gas_price
            
            # Build and estimate gas if not provided
            tx = func(*args, **kwargs). build_transaction(tx_params)
            
            if 'gas' not in tx:
                tx['gas'] = self.w3.eth.estimate_gas(tx)
            
            # Sign and send
            signed_tx = self.w3.eth.account.sign_transaction(tx, self.account.key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            
            # Wait for receipt
            receipt: TxReceipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            
            return ContractCall(
                success=receipt['status'] == 1,
                data=receipt,
                tx_hash=tx_hash. hex(),
                gas_used=receipt['gasUsed']
            )
            
        except Exception as e:
            logger.error(f"Error writing to contract: {e}")
            return ContractCall(success=False, data=None, error=str(e))
    
    def estimate_gas(
        self,
        contract: Contract,
        function_name: str,
        *args,
        value: Wei = Wei(0),
        **kwargs
    ) -> Optional[int]:
        """Estimate gas for a contract call."""
        try:
            func = getattr(contract.functions, function_name)
            tx_params = {'value': value}
            if self.account:
                tx_params['from'] = self.account.address
            return func(*args, **kwargs).estimate_gas(tx_params)
        except Exception as e:
            logger. error(f"Error estimating gas: {e}")
            return None
    
    def get_events(
        self,
        contract: Contract,
        event_name: str,
        from_block: int = 0,
        to_block: Union[int, str] = 'latest',
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Get past events from a contract.
        
        Args:
            contract: Contract instance
            event_name: Name of the event
            from_block: Starting block number
            to_block: Ending block number or 'latest'
            filters: Event argument filters
            
        Returns:
            List of event dictionaries
        """
        try:
            event = getattr(contract.events, event_name)
            event_filter = event. create_filter(
                fromBlock=from_block,
                toBlock=to_block,
                argument_filters=filters or {}
            )
            entries = event_filter. get_all_entries()
            
            return [
                {
                    'event': entry['event'],
                    'args': dict(entry['args']),
                    'block_number': entry['blockNumber'],
                    'tx_hash': entry['transactionHash'].hex(),
                    'log_index': entry['logIndex']
                }
                for entry in entries
            ]
        except Exception as e:
            logger.error(f"Error getting events: {e}")
            return []
    
    def subscribe_to_events(
        self,
        contract: Contract,
        event_name: str,
        callback: Callable[[Dict], None],
        poll_interval: float = 2.0
    ) -> str:
        """
        Subscribe to contract events.
        
        Args:
            contract: Contract instance
            event_name: Name of the event
            callback: Callback function for new events
            poll_interval: Polling interval in seconds
            
        Returns:
            Subscription ID
        """
        import threading
        import time
        
        event = getattr(contract. events, event_name)
        event_filter = event. create_filter(fromBlock='latest')
        
        subscription_id = f"{contract.address}_{event_name}"
        self._event_filters[subscription_id] = {
            'filter': event_filter,
            'active': True
        }
        
        def poll_events():
            while self._event_filters. get(subscription_id, {}).get('active', False):
                try:
                    for entry in event_filter.get_new_entries():
                        callback({
                            'event': entry['event'],
                            'args': dict(entry['args']),
                            'block_number': entry['blockNumber'],
                            'tx_hash': entry['transactionHash']. hex()
                        })
                except Exception as e:
                    logger.error(f"Error polling events: {e}")
                time.sleep(poll_interval)
        
        thread = threading. Thread(target=poll_events, daemon=True)
        thread.start()
        
        logger.info(f"Subscribed to {event_name} events on {contract.address}")
        return subscription_id
    
    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        if subscription_id in self._event_filters:
            self._event_filters[subscription_id]['active'] = False
            del self._event_filters[subscription_id]
            return True
        return False
    
    def decode_function_input(self, contract: Contract, tx_input: str) -> Optional[Dict]:
        """Decode transaction input data."""
        try:
            func, params = contract.decode_function_input(tx_input)
            return {
                'function': func. fn_name,
                'params': dict(params)
            }
        except Exception as e:
            logger.error(f"Error decoding input: {e}")
            return None
    
    def get_balance(self, address: str) -> int:
        """Get native token balance for an address."""
        checksum = Web3.to_checksum_address(address)
        return self.w3. eth.get_balance(checksum)
    
    def get_token_balance(
        self,
        token_address: str,
        wallet_address: str,
        decimals: int = 18
    ) -> float:
        """Get ERC20 token balance."""
        # Standard ERC20 balanceOf ABI
        erc20_abi = [
            {
                "constant": True,
                "inputs": [{"name": "_owner", "type": "address"}],
                "name": "balanceOf",
                "outputs": [{"name": "balance", "type": "uint256"}],
                "type": "function"
            }
        ]
        
        token = self.w3.eth.contract(
            address=Web3.to_checksum_address(token_address),
            abi=erc20_abi
        )
        
        balance = token. functions.balanceOf(
            Web3.to_checksum_address(wallet_address)
        ).call()
        
        return balance / (10 ** decimals)
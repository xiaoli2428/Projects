"""Real-time WebSocket handlers for live data."""
import asyncio
import json
import logging
import time
from typing import Dict, Set, Any, Callable, Optional, List
from dataclasses import dataclass, field
from decimal import Decimal
from web3 import Web3

from config. networks import get_network_config

logger = logging.getLogger(__name__)


@dataclass
class Subscription:
    """WebSocket subscription."""
    id: str
    type: str  # 'price', 'transaction', 'block', 'event'
    params: Dict[str, Any]
    callback: Optional[Callable] = None
    created_at: float = field(default_factory=time.time)


@dataclass
class PriceUpdate:
    """Price update data."""
    token: str
    price: Decimal
    change_24h: Decimal
    volume_24h: Decimal
    timestamp: float


@dataclass
class TransactionUpdate:
    """Transaction update data."""
    tx_hash: str
    from_address: str
    to_address: str
    value: Decimal
    status: str  # 'pending', 'confirmed', 'failed'
    confirmations: int
    block_number: Optional[int]
    timestamp: float


class WebSocketManager:
    """Manager for WebSocket connections and subscriptions."""
    
    def __init__(self):
        """Initialize WebSocket manager."""
        self._subscriptions: Dict[str, Subscription] = {}
        self._clients: Dict[str, Set[str]] = {}  # client_id -> subscription_ids
        self._broadcast_callbacks: Dict[str, List[Callable]] = {}
        self._running = False
        
    async def subscribe(
        self,
        client_id: str,
        subscription_type: str,
        params: Dict[str, Any],
        callback: Optional[Callable] = None
    ) -> str:
        """
        Create a new subscription. 
        
        Args:
            client_id: Client identifier
            subscription_type: Type of subscription
            params: Subscription parameters
            callback: Optional callback for updates
            
        Returns:
            Subscription ID
        """
        sub_id = f"{client_id}_{subscription_type}_{int(time.time() * 1000)}"
        
        subscription = Subscription(
            id=sub_id,
            type=subscription_type,
            params=params,
            callback=callback
        )
        
        self._subscriptions[sub_id] = subscription
        
        if client_id not in self._clients:
            self._clients[client_id] = set()
        self._clients[client_id].add(sub_id)
        
        logger.info(f"Created subscription {sub_id} for client {client_id}")
        return sub_id
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from a subscription."""
        if subscription_id not in self._subscriptions:
            return False
        
        sub = self._subscriptions. pop(subscription_id)
        
        # Remove from client subscriptions
        for client_subs in self._clients.values():
            client_subs.discard(subscription_id)
        
        logger. info(f"Removed subscription {subscription_id}")
        return True
    
    async def unsubscribe_client(self, client_id: str) -> int:
        """Remove all subscriptions for a client."""
        if client_id not in self._clients:
            return 0
        
        count = 0
        for sub_id in list(self._clients[client_id]):
            if sub_id in self._subscriptions:
                del self._subscriptions[sub_id]
                count += 1
        
        del self._clients[client_id]
        logger. info(f"Removed {count} subscriptions for client {client_id}")
        return count
    
    async def broadcast(
        self,
        subscription_type: str,
        data: Dict[str, Any],
        filter_params: Optional[Dict[str, Any]] = None
    ):
        """
        Broadcast data to matching subscriptions. 
        
        Args:
            subscription_type: Type of subscription to broadcast to
            data: Data to broadcast
            filter_params: Optional filter to match subscriptions
        """
        for sub_id, sub in self._subscriptions.items():
            if sub. type != subscription_type:
                continue
            
            # Check filter params
            if filter_params:
                match = all(
                    sub. params.get(k) == v
                    for k, v in filter_params. items()
                )
                if not match:
                    continue
            
            # Call callback if exists
            if sub.callback:
                try:
                    await sub.callback(data)
                except Exception as e:
                    logger.error(f"Error in subscription callback: {e}")
    
    def get_client_subscriptions(self, client_id: str) -> List[Dict]:
        """Get all subscriptions for a client."""
        if client_id not in self._clients:
            return []
        
        return [
            {
                'id': sub_id,
                'type': self._subscriptions[sub_id].type,
                'params': self._subscriptions[sub_id].params,
                'created_at': self._subscriptions[sub_id].created_at
            }
            for sub_id in self._clients[client_id]
            if sub_id in self._subscriptions
        ]


class PriceFeed:
    """Real-time price feed handler."""
    
    def __init__(self, ws_manager: WebSocketManager):
        """Initialize price feed."""
        self. ws_manager = ws_manager
        self._price_cache: Dict[str, PriceUpdate] = {}
        self._update_interval = 5.0  # seconds
        self._running = False
        
    async def start(self):
        """Start the price feed."""
        self._running = True
        logger.info("Price feed started")
        
        while self._running:
            await self._fetch_and_broadcast_prices()
            await asyncio.sleep(self._update_interval)
    
    async def stop(self):
        """Stop the price feed."""
        self._running = False
        logger. info("Price feed stopped")
    
    async def _fetch_and_broadcast_prices(self):
        """Fetch prices and broadcast updates."""
        # In production, integrate with price APIs (CoinGecko, CoinMarketCap, etc.)
        for token, cached in self._price_cache. items():
            price_update = PriceUpdate(
                token=token,
                price=cached. price,
                change_24h=cached.change_24h,
                volume_24h=cached. volume_24h,
                timestamp=time.time()
            )
            
            await self.ws_manager.broadcast(
                'price',
                {
                    'token': price_update.token,
                    'price': str(price_update. price),
                    'change_24h': str(price_update.change_24h),
                    'volume_24h': str(price_update.volume_24h),
                    'timestamp': price_update.timestamp
                },
                {'token': token}
            )
    
    def add_token(self, token: str, initial_price: Decimal = Decimal(0)):
        """Add a token to track."""
        self._price_cache[token] = PriceUpdate(
            token=token,
            price=initial_price,
            change_24h=Decimal(0),
            volume_24h=Decimal(0),
            timestamp=time. time()
        )
    
    def update_price(
        self,
        token: str,
        price: Decimal,
        change_24h: Optional[Decimal] = None,
        volume_24h: Optional[Decimal] = None
    ):
        """Update price for a token."""
        if token in self._price_cache:
            cached = self._price_cache[token]
            self._price_cache[token] = PriceUpdate(
                token=token,
                price=price,
                change_24h=change_24h if change_24h is not None else cached. change_24h,
                volume_24h=volume_24h if volume_24h is not None else cached.volume_24h,
                timestamp=time.time()
            )
    
    def get_price(self, token: str) -> Optional[PriceUpdate]:
        """Get cached price for a token."""
        return self._price_cache.get(token)
    
    def get_all_prices(self) -> Dict[str, PriceUpdate]:
        """Get all cached prices."""
        return self._price_cache.copy()


class TransactionMonitor:
    """Monitor transactions in real-time."""
    
    def __init__(self, ws_manager: WebSocketManager, network: str = "ethereum"):
        """Initialize transaction monitor."""
        self.ws_manager = ws_manager
        self.network = network
        self._config = get_network_config(network)
        self._w3 = Web3(Web3.HTTPProvider(self._config. rpc_url))
        self._monitored_txs: Dict[str, TransactionUpdate] = {}
        self._monitored_addresses: Set[str] = set()
        self._running = False
        self._poll_interval = 2.0  # seconds
        
    async def start(self):
        """Start monitoring transactions."""
        self._running = True
        logger.info(f"Transaction monitor started for {self.network}")
        
        while self._running:
            await self._check_transactions()
            await self._check_pending_blocks()
            await asyncio.sleep(self._poll_interval)
    
    async def stop(self):
        """Stop monitoring."""
        self._running = False
        logger.info("Transaction monitor stopped")
    
    def monitor_transaction(self, tx_hash: str) -> str:
        """
        Start monitoring a specific transaction. 
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction hash
        """
        self._monitored_txs[tx_hash] = TransactionUpdate(
            tx_hash=tx_hash,
            from_address="",
            to_address="",
            value=Decimal(0),
            status="pending",
            confirmations=0,
            block_number=None,
            timestamp=time.time()
        )
        return tx_hash
    
    def monitor_address(self, address: str):
        """Monitor all transactions for an address."""
        checksum = Web3.to_checksum_address(address)
        self._monitored_addresses. add(checksum)
        logger.info(f"Monitoring address: {checksum}")
    
    def unmonitor_address(self, address: str):
        """Stop monitoring an address."""
        checksum = Web3.to_checksum_address(address)
        self._monitored_addresses.discard(checksum)
    
    async def _check_transactions(self):
        """Check status of monitored transactions."""
        for tx_hash, tx_update in list(self._monitored_txs.items()):
            try:
                # Get transaction receipt
                try:
                    receipt = self._w3.eth.get_transaction_receipt(tx_hash)
                    tx = self._w3. eth.get_transaction(tx_hash)
                    
                    # Calculate confirmations
                    current_block = self._w3.eth. block_number
                    confirmations = current_block - receipt['blockNumber'] + 1
                    
                    status = "confirmed" if receipt['status'] == 1 else "failed"
                    
                    updated = TransactionUpdate(
                        tx_hash=tx_hash,
                        from_address=tx['from'],
                        to_address=tx. get('to', ''),
                        value=Decimal(tx['value']) / Decimal(10**18),
                        status=status,
                        confirmations=confirmations,
                        block_number=receipt['blockNumber'],
                        timestamp=time.time()
                    )
                    
                    self._monitored_txs[tx_hash] = updated
                    
                    # Broadcast update
                    await self. ws_manager.broadcast(
                        'transaction',
                        {
                            'tx_hash': tx_hash,
                            'status': status,
                            'confirmations': confirmations,
                            'block_number': receipt['blockNumber'],
                            'from': tx['from'],
                            'to': tx.get('to', ''),
                            'value': str(updated.value)
                        }
                    )
                    
                    # Remove from monitoring if enough confirmations
                    if confirmations >= 12:
                        del self._monitored_txs[tx_hash]
                        
                except Exception:
                    # Transaction still pending
                    pass
                    
            except Exception as e:
                logger.error(f"Error checking transaction {tx_hash}: {e}")
    
    async def _check_pending_blocks(self):
        """Check new blocks for transactions to monitored addresses."""
        if not self._monitored_addresses:
            return
            
        try:
            latest_block = self._w3.eth. get_block('latest', full_transactions=True)
            
            for tx in latest_block.get('transactions', []):
                from_addr = tx.get('from', '')
                to_addr = tx.get('to', '')
                
                if from_addr in self._monitored_addresses or to_addr in self._monitored_addresses:
                    await self. ws_manager.broadcast(
                        'address_transaction',
                        {
                            'tx_hash': tx['hash']. hex(),
                            'from': from_addr,
                            'to': to_addr,
                            'value': str(Decimal(tx['value']) / Decimal(10**18)),
                            'block_number': latest_block['number'],
                            'timestamp': time.time()
                        }
                    )
        except Exception as e:
            logger.error(f"Error checking pending blocks: {e}")
    
    def get_transaction_status(self, tx_hash: str) -> Optional[TransactionUpdate]:
        """Get current status of a monitored transaction."""
        return self._monitored_txs.get(tx_hash)


class BlockMonitor:
    """Monitor new blocks in real-time."""
    
    def __init__(self, ws_manager: WebSocketManager, network: str = "ethereum"):
        """Initialize block monitor."""
        self. ws_manager = ws_manager
        self.network = network
        self._config = get_network_config(network)
        self._w3 = Web3(Web3.HTTPProvider(self._config.rpc_url))
        self._last_block = 0
        self._running = False
        
    async def start(self):
        """Start monitoring blocks."""
        self._running = True
        self._last_block = self._w3. eth.block_number
        logger.info(f"Block monitor started at block {self._last_block}")
        
        while self._running:
            await self._check_new_blocks()
            await asyncio.sleep(1. 0)
    
    async def stop(self):
        """Stop monitoring."""
        self._running = False
    
    async def _check_new_blocks(self):
        """Check for new blocks."""
        try:
            current_block = self._w3.eth. block_number
            
            if current_block > self._last_block:
                for block_num in range(self._last_block + 1, current_block + 1):
                    block = self._w3.eth.get_block(block_num)
                    
                    await self.ws_manager.broadcast(
                        'block',
                        {
                            'number': block['number'],
                            'hash': block['hash']. hex(),
                            'timestamp': block['timestamp'],
                            'transactions': len(block['transactions']),
                            'gas_used': block['gasUsed'],
                            'gas_limit': block['gasLimit'],
                            'base_fee': block. get('baseFeePerGas', 0)
                        }
                    )
                
                self._last_block = current_block
                
        except Exception as e:
            logger.error(f"Error checking new blocks: {e}")
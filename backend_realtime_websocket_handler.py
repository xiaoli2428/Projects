"""Real-time WebSocket handlers for live data."""
import asyncio
import json
import logging
import time
from typing import Dict, Set, Any, Callable, Optional, List
from dataclasses import dataclass, field
from decimal import Decimal
from web3 import Web3

from config.networks import get_network_config

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
            client_subs. discard(subscription_id)
        
        logger.info(f"Removed subscription {subscription_id}")
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
        logger.info(f"Removed {count} subscriptions for client {client_id}")
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
            if sub.type != subscription_type:
                continue
            
            # Check filter params
            if filter_params:
                match = all(
                    sub.params.get(k) == v
                    for k, v in filter_params.items()
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
        self.ws_manager = ws_manager
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
        # In production, fetch from price APIs (CoinGecko, CoinMarketCap, etc.)
        # This is a placeholder implementation
        
        for token, cached in self._price_cache.items():
            price_update = PriceUpdate(
                token=token,
                price=cached.price,
                change_24h=cached.change_24h,
                volume_24h=cached.volume_24h,
                timestamp
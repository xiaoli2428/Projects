"""Analytics and dashboard functionality."""
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, timedelta
from collections import defaultdict

from web3 import Web3
from config.networks import get_network_config
from wallet. wallet_integration import WalletManager

logger = logging.getLogger(__name__)


@dataclass
class TokenHolding:
    """Token holding information."""
    token_address: str
    symbol: str
    name: str
    balance: Decimal
    price_usd: Decimal
    value_usd: Decimal
    change_24h: Decimal = Decimal(0)
    allocation_percent: Decimal = Decimal(0)


@dataclass
class PortfolioMetrics:
    """Portfolio metrics."""
    total_value_usd: Decimal
    total_change_24h: Decimal
    total_change_percent_24h: Decimal
    holdings: List[TokenHolding]
    native_balance: Decimal
    native_value_usd: Decimal
    defi_positions_value: Decimal = Decimal(0)
    nft_value: Decimal = Decimal(0)


@dataclass
class
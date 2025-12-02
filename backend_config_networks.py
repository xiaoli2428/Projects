"""Network configurations for multi-chain support."""
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class NetworkConfig:
    """Configuration for a blockchain network."""
    chain_id: int
    name: str
    rpc_url: str
    explorer_url: str
    native_currency: str
    native_decimals: int = 18
    is_testnet: bool = False
    multicall_address: Optional[str] = None
    

NETWORKS: Dict[str, NetworkConfig] = {
    "ethereum": NetworkConfig(
        chain_id=1,
        name="Ethereum Mainnet",
        rpc_url="https://eth.llamarpc.com",
        explorer_url="https://etherscan.io",
        native_currency="ETH",
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11"
    ),
    "goerli": NetworkConfig(
        chain_id=5,
        name="Goerli Testnet",
        rpc_url="https://rpc.ankr. com/eth_goerli",
        explorer_url="https://goerli.etherscan.io",
        native_currency="ETH",
        is_testnet=True
    ),
    "sepolia": NetworkConfig(
        chain_id=11155111,
        name="Sepolia Testnet",
        rpc_url="https://rpc.sepolia.org",
        explorer_url="https://sepolia.etherscan.io",
        native_currency="ETH",
        is_testnet=True
    ),
    "bsc": NetworkConfig(
        chain_id=56,
        name="BNB Smart Chain",
        rpc_url="https://bsc-dataseed.binance.org",
        explorer_url="https://bscscan.com",
        native_currency="BNB",
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11"
    ),
    "polygon": NetworkConfig(
        chain_id=137,
        name="Polygon Mainnet",
        rpc_url="https://polygon-rpc.com",
        explorer_url="https://polygonscan.com",
        native_currency="MATIC",
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11"
    ),
    "arbitrum": NetworkConfig(
        chain_id=42161,
        name="Arbitrum One",
        rpc_url="https://arb1.arbitrum.io/rpc",
        explorer_url="https://arbiscan.io",
        native_currency="ETH",
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11"
    ),
    "optimism": NetworkConfig(
        chain_id=10,
        name="Optimism",
        rpc_url="https://mainnet.optimism. io",
        explorer_url="https://optimistic.etherscan. io",
        native_currency="ETH",
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11"
    ),
    "avalanche": NetworkConfig(
        chain_id=43114,
        name="Avalanche C-Chain",
        rpc_url="https://api.avax.network/ext/bc/C/rpc",
        explorer_url="https://snowtrace.io",
        native_currency="AVAX",
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11"
    ),
    "fantom": NetworkConfig(
        chain_id=250,
        name="Fantom Opera",
        rpc_url="https://rpc.ftm.tools",
        explorer_url="https://ftmscan.com",
        native_currency="FTM",
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11"
    ),
    "base": NetworkConfig(
        chain_id=8453,
        name="Base",
        rpc_url="https://mainnet.base.org",
        explorer_url="https://basescan.org",
        native_currency="ETH",
        multicall_address="0xcA11bde05977b3631167028862bE2a173976CA11"
    ),
}


def get_network_config(network: str) -> NetworkConfig:
    """Get network configuration by name."""
    if network not in NETWORKS:
        raise ValueError(f"Unknown network: {network}. Available: {list(NETWORKS.keys())}")
    return NETWORKS[network]


def get_chain_id(network: str) -> int:
    """Get chain ID for a network."""
    return get_network_config(network).chain_id


def get_rpc_url(network: str) -> str:
    """Get RPC URL for a network."""
    return get_network_config(network).rpc_url


def get_network_by_chain_id(chain_id: int) -> Optional[NetworkConfig]:
    """Get network configuration by chain ID."""
    for config in NETWORKS.values():
        if config.chain_id == chain_id:
            return config
    return None
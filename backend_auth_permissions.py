"""Role-based access control and permissions."""
from enum import Enum, auto
from typing import Set, Dict, Optional, List
from dataclasses import dataclass, field
import logging

from web3 import Web3

logger = logging. getLogger(__name__)


class Permission(Enum):
    """Available permissions."""
    # Read permissions
    READ_PORTFOLIO = auto()
    READ_ANALYTICS = auto()
    READ_GOVERNANCE = auto()
    READ_STAKING = auto()
    READ_NFT = auto()
    
    # Write permissions
    EXECUTE_TRADE = auto()
    STAKE_TOKENS = auto()
    UNSTAKE_TOKENS = auto()
    CLAIM_REWARDS = auto()
    
    # Governance permissions
    CREATE_PROPOSAL = auto()
    VOTE_PROPOSAL = auto()
    DELEGATE_VOTES = auto()
    EXECUTE_PROPOSAL = auto()
    
    # NFT permissions
    LIST_NFT = auto()
    BUY_NFT = auto()
    TRANSFER_NFT = auto()
    
    # Admin permissions
    ADMIN_READ = auto()
    ADMIN_WRITE = auto()
    MANAGE_USERS = auto()
    MANAGE_CONTRACTS = auto()


class Role(Enum):
    """User roles."""
    GUEST = "guest"
    USER = "user"
    STAKER = "staker"
    GOVERNANCE = "governance"
    NFT_TRADER = "nft_trader"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.GUEST: {
        Permission.READ_PORTFOLIO,
        Permission.READ_ANALYTICS,
    },
    Role. USER: {
        Permission.READ_PORTFOLIO,
        Permission.READ_ANALYTICS,
        Permission.READ_GOVERNANCE,
        Permission.READ_STAKING,
        Permission.READ_NFT,
        Permission.EXECUTE_TRADE,
    },
    Role. STAKER: {
        Permission.READ_PORTFOLIO,
        Permission.READ_ANALYTICS,
        Permission.READ_GOVERNANCE,
        Permission.READ_STAKING,
        Permission.READ_NFT,
        Permission. EXECUTE_TRADE,
        Permission. STAKE_TOKENS,
        Permission. UNSTAKE_TOKENS,
        Permission.CLAIM_REWARDS,
    },
    Role. GOVERNANCE: {
        Permission.READ_PORTFOLIO,
        Permission.READ_ANALYTICS,
        Permission.READ_GOVERNANCE,
        Permission.READ_STAKING,
        Permission.READ_NFT,
        Permission. EXECUTE_TRADE,
        Permission. STAKE_TOKENS,
        Permission.UNSTAKE_TOKENS,
        Permission. CLAIM_REWARDS,
        Permission.CREATE_PROPOSAL,
        Permission.VOTE_PROPOSAL,
        Permission.DELEGATE_VOTES,
    },
    Role. NFT_TRADER: {
        Permission.READ_PORTFOLIO,
        Permission. READ_ANALYTICS,
        Permission.READ_NFT,
        Permission.LIST_NFT,
        Permission.BUY_NFT,
        Permission. TRANSFER_NFT,
    },
    Role.ADMIN: {
        Permission. READ_PORTFOLIO,
        Permission.READ_ANALYTICS,
        Permission.READ_GOVERNANCE,
        Permission.READ_STAKING,
        Permission.READ_NFT,
        Permission.EXECUTE_TRADE,
        Permission.STAKE_TOKENS,
        Permission.UNSTAKE_TOKENS,
        Permission. CLAIM_REWARDS,
        Permission.CREATE_PROPOSAL,
        Permission.VOTE_PROPOSAL,
        Permission.DELEGATE_VOTES,
        Permission.EXECUTE_PROPOSAL,
        Permission.LIST_NFT,
        Permission.BUY_NFT,
        Permission. TRANSFER_NFT,
        Permission. ADMIN_READ,
    },
    Role. SUPER_ADMIN: set(Permission),  # All permissions
}


@dataclass
class UserPermissions:
    """User permission data."""
    address: str
    roles: Set[Role] = field(default_factory=lambda: {Role.USER})
    extra_permissions: Set[Permission] = field(default_factory=set)
    denied_permissions: Set[Permission] = field(default_factory=set)
    
    @property
    def all_permissions(self) -> Set[Permission]:
        """Get all permissions for the user."""
        permissions = set()
        for role in self.roles:
            permissions. update(ROLE_PERMISSIONS. get(role, set()))
        permissions. update(self.extra_permissions)
        permissions -= self.denied_permissions
        return permissions
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if user has a specific permission."""
        return permission in self. all_permissions
    
    def has_any_permission(self, permissions: Set[Permission]) -> bool:
        """Check if user has any of the specified permissions."""
        return bool(self.all_permissions & permissions)
    
    def has_all_permissions(self, permissions: Set[Permission]) -> bool:
        """Check if user has all specified permissions."""
        return permissions <= self.all_permissions


class PermissionManager:
    """Manager for user permissions and roles."""
    
    def __init__(self):
        """Initialize the permission manager."""
        self._user_permissions: Dict[str, UserPermissions] = {}
        self._admin_addresses: Set[str] = set()
        
    def register_user(
        self,
        address: str,
        roles: Optional[Set[Role]] = None
    ) -> UserPermissions:
        """
        Register a new user with roles.
        
        Args:
            address: Wallet address
            roles: Initial roles (defaults to USER)
            
        Returns:
            UserPermissions instance
        """
        address = Web3.to_checksum_address(address)
        
        if roles is None:
            roles = {Role.USER}
        
        # Check if admin
        if address in self._admin_addresses:
            roles.add(Role. ADMIN)
        
        user_perms = UserPermissions(address=address, roles=roles)
        self._user_permissions[address] = user_perms
        
        logger.info(f"Registered user {address} with roles: {roles}")
        return user_perms
    
    def get_user_permissions(self, address: str) -> Optional[UserPermissions]:
        """Get user permissions by address."""
        address = Web3.to_checksum_address(address)
        return self._user_permissions.get(address)
    
    def add_role(self, address: str, role: Role) -> bool:
        """Add a role to a user."""
        address = Web3.to_checksum_address(address)
        user_perms = self._user_permissions. get(address)
        
        if not user_perms:
            return False
        
        user_perms.roles.add(role)
        logger.info(f"Added role {role} to {address}")
        return True
    
    def remove_role(self, address: str, role: Role) -> bool:
        """Remove a role from a user."""
        address = Web3. to_checksum_address(address)
        user_perms = self._user_permissions.get(address)
        
        if not user_perms or role not in user_perms.roles:
            return False
        
        user_perms.roles.remove(role)
        logger.info(f"Removed role {role} from {address}")
        return True
    
    def grant_permission(self, address: str, permission: Permission) -> bool:
        """Grant an extra permission to a user."""
        address = Web3.to_checksum_address(address)
        user_perms = self._user_permissions.get(address)
        
        if not user_perms:
            return False
        
        user_perms.extra_permissions.add(permission)
        user_perms.denied_permissions.discard(permission)
        return True
    
    def deny_permission(self, address: str, permission: Permission) -> bool:
        """Deny a permission from a user."""
        address = Web3. to_checksum_address(address)
        user_perms = self._user_permissions.get(address)
        
        if not user_perms:
            return False
        
        user_perms. denied_permissions.add(permission)
        user_perms.extra_permissions.discard(permission)
        return True
    
    def check_permission(self, address: str, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        address = Web3.to_checksum_address(address)
        user_perms = self._user_permissions.get(address)
        
        if not user_perms:
            return False
        
        return user_perms.has_permission(permission)
    
    def add_admin(self, address: str) -> None:
        """Add an address as admin."""
        address = Web3. to_checksum_address(address)
        self._admin_addresses.add(address)
        
        # Update existing user if registered
        if address in self._user_permissions:
            self._user_permissions[address].roles.add(Role. ADMIN)
    
    def remove_admin(self, address: str) -> None:
        """Remove admin status from an address."""
        address = Web3.to_checksum_address(address)
        self._admin_addresses.discard(address)
        
        if address in self._user_permissions:
            self._user_permissions[address].roles. discard(Role. ADMIN)
    
    def get_users_with_role(self, role: Role) -> List[str]:
        """Get all users with a specific role."""
        return [
            addr for addr, perms in self._user_permissions.items()
            if role in perms.roles
        ]
"""Web3 wallet-based authentication."""
import secrets
import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt
from eth_account. messages import encode_defunct
from web3 import Web3

from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """Authentication result."""
    success: bool
    address: Optional[str] = None
    token: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None
    user_data: Optional[Dict[str, Any]] = None


class WalletAuthenticator:
    """Web3 wallet authentication handler."""
    
    def __init__(self):
        """Initialize the authenticator."""
        self.settings = get_settings()
        self._nonces: Dict[str, Dict[str, Any]] = {}  # address -> {nonce, expires}
        self._sessions: Dict[str, Dict[str, Any]] = {}  # token -> session data
        
    def generate_nonce(self, address: str) -> str:
        """
        Generate a unique nonce for wallet signature.
        
        Args:
            address: Wallet address
            
        Returns:
            Unique nonce string
        """
        address = Web3.to_checksum_address(address)
        nonce = secrets.token_hex(16)
        expires = time.time() + 300  # 5 minutes expiry
        
        self._nonces[address] = {
            'nonce': nonce,
            'expires': expires
        }
        
        logger.info(f"Generated nonce for {address}")
        return nonce
    
    def get_sign_message(self, address: str, nonce: str) -> str:
        """
        Get the message to be signed by the wallet.
        
        Args:
            address: Wallet address
            nonce: Generated nonce
            
        Returns:
            Message string to sign
        """
        return (
            f"Welcome to Web3 DeFi App!\n\n"
            f"Please sign this message to verify your wallet ownership.\n\n"
            f"Wallet: {address}\n"
            f"Nonce: {nonce}\n"
            f"Timestamp: {int(time.time())}"
        )
    
    def verify_signature(
        self,
        address: str,
        signature: str,
        message: Optional[str] = None
    ) -> AuthResult:
        """
        Verify wallet signature and authenticate user.
        
        Args:
            address: Wallet address
            signature: Signed message
            message: Original message (optional, will reconstruct if not provided)
            
        Returns:
            AuthResult with token if successful
        """
        try:
            address = Web3.to_checksum_address(address)
            
            # Check nonce exists and is valid
            nonce_data = self._nonces.get(address)
            if not nonce_data:
                return AuthResult(success=False, error="No nonce found.  Request a new one.")
            
            if time.time() > nonce_data['expires']:
                del self._nonces[address]
                return AuthResult(success=False, error="Nonce expired. Request a new one.")
            
            nonce = nonce_data['nonce']
            
            # Reconstruct message if not provided
            if message is None:
                message = self. get_sign_message(address, nonce)
            
            # Verify signature
            message_hash = encode_defunct(text=message)
            w3 = Web3()
            
            recovered_address = w3.eth.account. recover_message(
                message_hash,
                signature=signature
            )
            
            if recovered_address. lower() != address.lower():
                return AuthResult(
                    success=False,
                    error="Signature verification failed"
                )
            
            # Clean up nonce
            del self._nonces[address]
            
            # Generate JWT token
            token, expires_at = self._generate_token(address)
            
            # Store session
            self._sessions[token] = {
                'address': address,
                'created_at': datetime. utcnow(),
                'expires_at': expires_at
            }
            
            logger.info(f"Successfully authenticated {address}")
            
            return AuthResult(
                success=True,
                address=address,
                token=token,
                expires_at=expires_at,
                user_data={'address': address}
            )
            
        except Exception as e:
            logger. error(f"Authentication error: {e}")
            return AuthResult(success=False, error=str(e))
    
    def _generate_token(self, address: str) -> tuple[str, datetime]:
        """Generate JWT token for authenticated user."""
        expires_at = datetime.utcnow() + timedelta(
            hours=self. settings.jwt_expiration_hours
        )
        
        payload = {
            'sub': address,
            'iat': datetime.utcnow(),
            'exp': expires_at,
            'type': 'access'
        }
        
        token = jwt.encode(
            payload,
            self.settings.jwt_secret_key,
            algorithm=self.settings.jwt_algorithm
        )
        
        return token, expires_at
    
    def verify_token(self, token: str) -> AuthResult:
        """
        Verify JWT token. 
        
        Args:
            token: JWT token
            
        Returns:
            AuthResult with user data if valid
        """
        try:
            payload = jwt.decode(
                token,
                self.settings.jwt_secret_key,
                algorithms=[self.settings.jwt_algorithm]
            )
            
            address = payload. get('sub')
            exp = payload.get('exp')
            
            if not address:
                return AuthResult(success=False, error="Invalid token payload")
            
            return AuthResult(
                success=True,
                address=address,
                token=token,
                expires_at=datetime.fromtimestamp(exp),
                user_data={'address': address}
            )
            
        except jwt. ExpiredSignatureError:
            return AuthResult(success=False, error="Token expired")
        except jwt.InvalidTokenError as e:
            return AuthResult(success=False, error=f"Invalid token: {e}")
    
    def refresh_token(self, token: str) -> AuthResult:
        """Refresh an existing valid token."""
        result = self.verify_token(token)
        
        if not result.success:
            return result
        
        # Generate new token
        new_token, expires_at = self._generate_token(result.address)
        
        # Invalidate old session
        if token in self._sessions:
            del self._sessions[token]
        
        # Create new session
        self._sessions[new_token] = {
            'address': result.address,
            'created_at': datetime.utcnow(),
            'expires_at': expires_at
        }
        
        return AuthResult(
            success=True,
            address=result. address,
            token=new_token,
            expires_at=expires_at
        )
    
    def revoke_token(self, token: str) -> bool:
        """Revoke a token (logout)."""
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False
    
    def get_active_sessions(self, address: str) -> list[Dict[str, Any]]:
        """Get all active sessions for an address."""
        address = Web3.to_checksum_address(address)
        sessions = []
        
        for token, data in self._sessions. items():
            if data['address']. lower() == address. lower():
                sessions.append({
                    'created_at': data['created_at'],
                    'expires_at': data['expires_at']
                })
        
        return sessions
"""
Password hashing and verification utilities.

Follows Layer 1 rules:
- Always use a strong hashing algorithm (bcrypt)
- NEVER log plaintext passwords or hashes
"""
from __future__ import annotations
import bcrypt


def hash_password(plain: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    
    Args:
        plain: Plaintext password
    
    Returns:
        Hashed password string
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a hash.
    
    Args:
        plain: Plaintext password to verify
        hashed: Hashed password to compare against
    
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False

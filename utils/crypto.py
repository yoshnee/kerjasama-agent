# utils/crypto.py
"""Cryptographic utilities for token decryption."""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


def get_encryption_key() -> bytes:
    """
    Get encryption key from environment variable.

    Returns:
        Encryption key as bytes

    Raises:
        ValueError: If ENCRYPTION_KEY not set in environment
    """
    key = os.getenv("ENCRYPTION_KEY")

    if not key:
        raise ValueError(
            "ENCRYPTION_KEY not found in environment variables. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )

    return key.encode()


def encrypt_token(plain_token: str) -> Optional[str]:
    """
    Encrypt a token using Fernet symmetric encryption.

    Args:
        plain_token: Plain text token to encrypt

    Returns:
        Encrypted token as base64 string, or None if encryption fails
    """
    if not plain_token:
        return plain_token

    try:
        key = get_encryption_key()
        fernet = Fernet(key)

        encrypted_bytes = fernet.encrypt(plain_token.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        logger.error("Failed to encrypt token: %s", str(e))
        return None


def decrypt_token(encrypted_token: str) -> Optional[str]:
    """
    Decrypt a token using Fernet symmetric encryption.

    Args:
        encrypted_token: Encrypted token as base64 string

    Returns:
        Decrypted plain text token, or None if decryption fails
    """
    if not encrypted_token:
        return encrypted_token

    try:
        key = get_encryption_key()
        fernet = Fernet(key)

        decrypted_bytes = fernet.decrypt(encrypted_token.encode())
        return decrypted_bytes.decode()
    except Exception as e:
        logger.error("Failed to decrypt token: %s", str(e))
        return None

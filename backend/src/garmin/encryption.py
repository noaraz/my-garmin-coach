from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


def derive_fernet_key(user_id: int, secret: str) -> Fernet:
    """Derive a per-user Fernet cipher from the server secret and user id.

    Uses SHA-256 to produce a deterministic 32-byte key, then base64url-encodes
    it so Fernet can consume it.
    """
    raw = hashlib.sha256(f"{secret}:{user_id}".encode()).digest()
    key = base64.urlsafe_b64encode(raw)
    return Fernet(key)


def encrypt_token(user_id: int, secret: str, plaintext: str) -> str:
    """Encrypt a Garmin token string for the given user.

    Args:
        user_id: The user's database id (used to derive the encryption key).
        secret: The server-side master secret (GARMINCOACH_SECRET_KEY).
        plaintext: The token JSON string to encrypt.

    Returns:
        A Fernet-encrypted ciphertext string (URL-safe base64).
    """
    fernet = derive_fernet_key(user_id, secret)
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_token(user_id: int, secret: str, ciphertext: str) -> str:
    """Decrypt a Garmin token string for the given user.

    Args:
        user_id: The user's database id.
        secret: The server-side master secret.
        ciphertext: The Fernet-encrypted token string.

    Returns:
        The decrypted plaintext token JSON string.
    """
    fernet = derive_fernet_key(user_id, secret)
    return fernet.decrypt(ciphertext.encode()).decode()

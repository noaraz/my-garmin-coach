from __future__ import annotations

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def derive_fernet_key(user_id: int, secret: str) -> Fernet:
    """Derive a per-user Fernet cipher from the master secret and user id.

    Uses HKDF (RFC 5869) — the correct primitive for deriving a key from a
    high-entropy master secret.  Per-user isolation is achieved via the salt
    (user_id bytes) and domain separation via the info field.

    NOTE: changing this function invalidates all existing encrypted tokens in
    the DB.  Any connected Garmin accounts must reconnect after deployment.
    """
    kdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=str(user_id).encode(),    # per-user salt — isolates derived keys
        info=b"garmincoach-token-v1",  # domain separation / context binding
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
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

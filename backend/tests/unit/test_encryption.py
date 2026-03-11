from __future__ import annotations

import pytest
from cryptography.fernet import InvalidToken

from src.garmin.encryption import decrypt_token, derive_fernet_key, encrypt_token


class TestDeriveKey:
    def test_derive_key_returns_fernet_instance(self) -> None:
        """derive_fernet_key always returns a usable Fernet object."""
        fernet = derive_fernet_key(user_id=1, secret="any-secret")
        assert fernet is not None

    def test_derive_key_different_users_produce_different_keys(self) -> None:
        """Same master secret + different user_ids → different Fernet keys."""
        f1 = derive_fernet_key(user_id=1, secret="master")
        f2 = derive_fernet_key(user_id=2, secret="master")
        # Encrypt same plaintext — ciphertext must differ (different key → different output)
        ct1 = f1.encrypt(b"token")
        ct2 = f2.encrypt(b"token")
        assert ct1 != ct2

    def test_derive_key_different_secrets_produce_different_keys(self) -> None:
        """Same user_id + different master secrets → different Fernet keys."""
        f1 = derive_fernet_key(user_id=1, secret="secret-a")
        f2 = derive_fernet_key(user_id=1, secret="secret-b")
        ct1 = f1.encrypt(b"token")
        ct2 = f2.encrypt(b"token")
        assert ct1 != ct2

    def test_derive_key_same_inputs_produce_same_key(self) -> None:
        """Derivation is deterministic — same inputs always yield the same key."""
        f1 = derive_fernet_key(user_id=7, secret="stable-secret")
        f2 = derive_fernet_key(user_id=7, secret="stable-secret")
        # Key from f1 can decrypt ciphertext produced by f2
        ct = f2.encrypt(b"payload")
        assert f1.decrypt(ct) == b"payload"


class TestEncryptToken:
    def test_encrypt_token_round_trip(self) -> None:
        """Encrypt then decrypt returns the original plaintext."""
        original = '{"oauth_token": "abc123", "oauth_token_secret": "xyz789"}'
        encrypted = encrypt_token(user_id=42, secret="test-secret", plaintext=original)
        decrypted = decrypt_token(user_id=42, secret="test-secret", ciphertext=encrypted)
        assert decrypted == original

    def test_encrypt_token_produces_ciphertext(self) -> None:
        """Encrypted output is not the same as the plaintext."""
        plaintext = '{"oauth_token": "abc123"}'
        encrypted = encrypt_token(user_id=1, secret="s", plaintext=plaintext)
        assert encrypted != plaintext
        assert "abc123" not in encrypted

    def test_decrypt_token_wrong_secret_raises(self) -> None:
        """Decrypting with a different master secret raises InvalidToken."""
        encrypted = encrypt_token(user_id=1, secret="correct-secret", plaintext="data")
        with pytest.raises(InvalidToken):
            decrypt_token(user_id=1, secret="wrong-secret", ciphertext=encrypted)

    def test_decrypt_token_wrong_user_id_raises(self) -> None:
        """Decrypting with a different user_id raises InvalidToken (per-user keys)."""
        encrypted = encrypt_token(user_id=1, secret="secret", plaintext="data")
        with pytest.raises(InvalidToken):
            decrypt_token(user_id=2, secret="secret", ciphertext=encrypted)

    def test_encrypt_token_different_users_different_ciphertext(self) -> None:
        """Same plaintext + same secret + different user_ids → different ciphertext."""
        plaintext = '{"token": "same-data"}'
        ct1 = encrypt_token(user_id=1, secret="secret", plaintext=plaintext)
        ct2 = encrypt_token(user_id=2, secret="secret", plaintext=plaintext)
        assert ct1 != ct2

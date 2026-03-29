from __future__ import annotations

import pytest
from cryptography.fernet import InvalidToken

from src.garmin.encryption import decrypt_credential, encrypt_credential


class TestEncryptCredential:
    def test_encrypt_returns_string(self):
        # Arrange
        user_id = 1
        secret = "test-secret-key-32-chars-long!"
        email = "test@example.com"
        password = "my-password"

        # Act
        encrypted = encrypt_credential(user_id, secret, email, password)

        # Assert
        assert isinstance(encrypted, str)
        assert len(encrypted) > 0

    def test_round_trip_preserves_credentials(self):
        # Arrange
        user_id = 1
        secret = "test-secret-key-32-chars-long!"
        email = "test@example.com"
        password = "my-password"

        # Act
        encrypted = encrypt_credential(user_id, secret, email, password)
        decrypted = decrypt_credential(user_id, secret, encrypted)

        # Assert
        assert decrypted == {"email": email, "password": password}


class TestDecryptCredential:
    def test_decrypt_returns_dict_with_email_and_password_keys(self):
        # Arrange
        user_id = 1
        secret = "test-secret-key-32-chars-long!"
        email = "test@example.com"
        password = "my-password"
        encrypted = encrypt_credential(user_id, secret, email, password)

        # Act
        decrypted = decrypt_credential(user_id, secret, encrypted)

        # Assert
        assert "email" in decrypted
        assert "password" in decrypted
        assert decrypted["email"] == email
        assert decrypted["password"] == password

    def test_decrypt_with_wrong_user_id_raises(self):
        # Arrange
        user_id = 1
        secret = "test-secret-key-32-chars-long!"
        encrypted = encrypt_credential(user_id, secret, "test@example.com", "my-password")

        # Act & Assert
        with pytest.raises(InvalidToken):
            decrypt_credential(user_id=2, secret=secret, ciphertext=encrypted)

    def test_decrypt_with_wrong_secret_raises(self):
        # Arrange
        user_id = 1
        secret = "test-secret-key-32-chars-long!"
        encrypted = encrypt_credential(user_id, secret, "test@example.com", "my-password")

        # Act & Assert
        with pytest.raises(InvalidToken):
            decrypt_credential(user_id, secret="wrong-secret-key-32-chars-lg!", ciphertext=encrypted)


class TestPerUserIsolation:
    def test_user_1_cannot_decrypt_user_2_credentials(self):
        # Arrange
        secret = "test-secret-key-32-chars-long!"
        user_1_id = 1
        user_2_id = 2
        email = "test@example.com"
        password = "my-password"

        # Act
        user_1_encrypted = encrypt_credential(user_1_id, secret, email, password)

        # Assert
        with pytest.raises(InvalidToken):
            decrypt_credential(user_2_id, secret, user_1_encrypted)

    def test_same_credentials_different_users_produce_different_ciphertext(self):
        # Arrange
        secret = "test-secret-key-32-chars-long!"
        user_1_id = 1
        user_2_id = 2
        email = "test@example.com"
        password = "my-password"

        # Act
        user_1_encrypted = encrypt_credential(user_1_id, secret, email, password)
        user_2_encrypted = encrypt_credential(user_2_id, secret, email, password)

        # Assert
        assert user_1_encrypted != user_2_encrypted

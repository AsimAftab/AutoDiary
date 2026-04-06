import pytest

from autodiary.utils.crypto import CryptoManager


@pytest.fixture
def crypto_manager(tmp_path):
    return CryptoManager(tmp_path)


def test_key_creation(crypto_manager):
    key_file = crypto_manager.key_file
    assert not key_file.exists()

    key = crypto_manager._get_or_create_key()
    assert key_file.exists()
    assert key_file.read_bytes() == key


def test_encrypt_decrypt(crypto_manager):
    plaintext = "super-secret-password"
    encrypted = crypto_manager.encrypt(plaintext)
    assert encrypted != plaintext

    decrypted = crypto_manager.decrypt(encrypted)
    assert decrypted == plaintext


def test_encrypt_empty(crypto_manager):
    assert crypto_manager.encrypt("") == ""
    assert crypto_manager.decrypt("") == ""


def test_decrypt_invalid(crypto_manager):
    with pytest.raises(ValueError, match="Failed to decrypt data"):
        crypto_manager.decrypt("invalid-encrypted-data")


def test_hash_value(crypto_manager):
    value = "test-value"
    hashed = crypto_manager.hash_value(value)
    assert len(hashed) == 64  # SHA-256 is 64 hex chars
    assert hashed == crypto_manager.hash_value(value)
    assert hashed != crypto_manager.hash_value("other-value")

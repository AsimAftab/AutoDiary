"""
Cryptography utilities for secure password storage.
"""

import hashlib
from pathlib import Path

from cryptography.fernet import Fernet


class CryptoManager:
    """Manager for encrypting and decrypting sensitive data."""

    def __init__(self, config_dir: Path):
        """
        Initialize crypto manager.

        Args:
            config_dir: Directory to store encryption key
        """
        self.config_dir = config_dir
        self.key_file = config_dir / ".encryption_key"
        self._key = None
        self._fernet = None

    def _get_or_create_key(self) -> bytes:
        """
        Get existing encryption key or create a new one.

        Returns:
            Encryption key as bytes
        """
        if self._key is not None:
            return self._key

        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        if self.key_file.exists():
            # Load existing key
            self._key = self.key_file.read_bytes()
            try:
                Fernet(self._key)
            except Exception as e:
                raise ValueError(f"Invalid encryption key in {self.key_file}: {e}") from e
        else:
            # Generate new key atomically with restricted permissions from the start
            import os

            self._key = Fernet.generate_key()
            try:
                # O_CREAT|O_EXCL guarantees atomic creation — fails if file already exists
                fd = os.open(str(self.key_file), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                try:
                    os.write(fd, self._key)
                finally:
                    os.close(fd)
            except FileExistsError:
                # Another process created the key first — load theirs instead
                self._key = self.key_file.read_bytes()

        return self._key

    @property
    def fernet(self) -> Fernet:
        """Get Fernet instance for encryption/decryption."""
        if self._fernet is None:
            key = self._get_or_create_key()
            self._fernet = Fernet(key)
        return self._fernet

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Args:
            plaintext: String to encrypt

        Returns:
            Encrypted string (base64 encoded)
        """
        if not plaintext:
            return ""
        encrypted_bytes = self.fernet.encrypt(plaintext.encode())
        return encrypted_bytes.decode()

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt an encrypted string.

        Args:
            encrypted: Encrypted string (base64 encoded)

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails
        """
        if not encrypted:
            return ""
        try:
            decrypted_bytes = self.fernet.decrypt(encrypted.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt data: {e}") from e

    def hash_value(self, value: str) -> str:
        """
        Create a hash of a value (for validation, not encryption).

        Args:
            value: String to hash

        Returns:
            Hex digest of the hash
        """
        return hashlib.sha256(value.encode()).hexdigest()

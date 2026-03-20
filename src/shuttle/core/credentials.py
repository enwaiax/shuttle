"""Credential manager with Fernet encryption for storing secrets."""

from pathlib import Path

from cryptography.fernet import Fernet


class CredentialManager:
    """Manages encryption/decryption of credentials using Fernet symmetric encryption.

    The encryption key is stored in a keyfile at {shuttle_dir}/keyfile with
    permissions 600. The keyfile is auto-generated on first use.
    """

    def __init__(self, shuttle_dir: Path) -> None:
        self._keyfile = shuttle_dir / "keyfile"

    def _get_or_create_key(self) -> bytes:
        """Return the Fernet key, generating and persisting it if it doesn't exist."""
        if not self._keyfile.exists():
            key = Fernet.generate_key()
            self._keyfile.write_bytes(key)
            self._keyfile.chmod(0o600)
        return self._keyfile.read_bytes()

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string and return the Fernet token as a string."""
        key = self._get_or_create_key()
        f = Fernet(key)
        return f.encrypt(plaintext.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt a Fernet token string and return the original plaintext."""
        key = self._get_or_create_key()
        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()

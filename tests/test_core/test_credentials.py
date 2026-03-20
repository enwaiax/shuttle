"""Tests for CredentialManager (Fernet encryption)."""

import pytest
from cryptography.fernet import InvalidToken

from shuttle.core.credentials import CredentialManager


def test_encrypt_decrypt_roundtrip(tmp_shuttle_dir):
    """Encrypting and then decrypting should return the original plaintext."""
    mgr = CredentialManager(tmp_shuttle_dir)
    plaintext = "super_secret_password"
    encrypted = mgr.encrypt(plaintext)
    assert encrypted != plaintext
    assert mgr.decrypt(encrypted) == plaintext


def test_keyfile_created_on_first_use(tmp_shuttle_dir):
    """The keyfile must not exist beforehand but should be created on first encrypt."""
    keyfile = tmp_shuttle_dir / "keyfile"
    assert not keyfile.exists()

    mgr = CredentialManager(tmp_shuttle_dir)
    mgr.encrypt("hello")

    assert keyfile.exists()
    # Permissions should be 600 (owner read/write only)
    assert oct(keyfile.stat().st_mode)[-3:] == "600"


def test_keyfile_reused_across_instances(tmp_shuttle_dir):
    """A second CredentialManager instance must reuse the existing keyfile."""
    mgr1 = CredentialManager(tmp_shuttle_dir)
    encrypted = mgr1.encrypt("shared_secret")

    mgr2 = CredentialManager(tmp_shuttle_dir)
    assert mgr2.decrypt(encrypted) == "shared_secret"


def test_decrypt_fails_with_wrong_key(tmp_shuttle_dir, tmp_path):
    """Decrypting a token with a different key must raise InvalidToken."""
    dir_a = tmp_shuttle_dir
    dir_b = tmp_path / ".shuttle_b"
    dir_b.mkdir()

    mgr_a = CredentialManager(dir_a)
    mgr_b = CredentialManager(dir_b)

    encrypted_with_a = mgr_a.encrypt("secret")

    with pytest.raises(InvalidToken):
        mgr_b.decrypt(encrypted_with_a)

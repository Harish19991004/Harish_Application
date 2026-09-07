"""Tests for consent storage and tamper detection."""
# Import the path helper used by pytest's temporary directory fixture.
from pathlib import Path
# Import the security store under test.
from security import SecureSettings


def test_consent_defaults_to_denied(tmp_path: Path):
    # Create a store with a deterministic test-only secret.
    settings = SecureSettings(tmp_path / "settings.bin", secret=b"test-secret")
    # Verify missing consent is denied by default.
    assert settings.load_consent() is False


def test_consent_round_trip_and_tamper_rejection(tmp_path: Path):
    # Create a store with a deterministic test-only secret.
    settings = SecureSettings(tmp_path / "settings.bin", secret=b"test-secret")
    # Persist explicit user consent.
    settings.save_consent(True)
    # Verify the original record can be loaded.
    assert settings.load_consent() is True
    # Corrupt the stored record to simulate tampering.
    settings.path.write_bytes(settings.path.read_bytes()[:-2] + b"xx")
    # Verify corrupted consent fails closed.
    assert settings.load_consent() is False
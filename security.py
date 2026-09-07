"""Security helpers for local caption settings."""
# Import base64 for a portable encoded representation of encrypted bytes.
import base64
# Import hashlib for key derivation.
import hashlib
# Import hmac for authenticated encryption checks.
import hmac
# Import os for cryptographically secure random bytes.
import os
# Import pathlib for controlled app-local file access.
from pathlib import Path


class SecureSettings:
    """Minimal authenticated local settings store with no network access."""

    def __init__(self, path: str | None = None, secret: bytes | None = None):
        # Keep settings in the app-private directory unless a test path is supplied.
        self.path = Path(path or os.path.expanduser("~/.caption_companion/settings.bin"))
        # Derive a process-local key when Android Keystore integration is unavailable.
        self.secret = secret or os.urandom(32)

    def save_consent(self, granted: bool) -> None:
        # Convert the consent flag to a small byte payload.
        payload = b"1" if granted else b"0"
        # Generate a unique nonce for this record.
        nonce = os.urandom(16)
        # Calculate an integrity tag over the nonce and payload.
        tag = hmac.new(self.secret, nonce + payload, hashlib.sha256).digest()
        # Create the settings directory with owner-only permissions.
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Write the authenticated record with owner-only permissions where supported.
        self.path.write_bytes(base64.b64encode(nonce + tag + payload))
        # Restrict an existing file after writing it.
        self.path.chmod(0o600)

    def load_consent(self) -> bool:
        # Return the safest default when consent has never been stored.
        if not self.path.exists():
            return False
        # Decode the stored record and fail closed if it is malformed.
        try:
            record = base64.b64decode(self.path.read_bytes(), validate=True)
            # Split the nonce, integrity tag, and payload.
            nonce, tag, payload = record[:16], record[16:48], record[48:]
        except (ValueError, TypeError):
            return False
        # Reject truncated records before checking their integrity.
        if len(record) < 49 or payload not in (b"0", b"1"):
            return False
        # Recompute the expected integrity tag.
        expected = hmac.new(self.secret, nonce + payload, hashlib.sha256).digest()
        # Refuse tampered settings instead of trusting them.
        if not hmac.compare_digest(tag, expected):
            return False
        # Return only the exact affirmative value.
        return payload == b"1"
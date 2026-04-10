import hashlib
import secrets


API_KEY_PREFIX = "sk_"


def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key.

    Returns a tuple of (raw_key, key_hash, key_prefix).
    The raw key is shown to the user exactly once. Only the hash is stored.
    """
    raw_token = secrets.token_urlsafe(32)
    raw_key = f"{API_KEY_PREFIX}{raw_token}"
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:12]
    return raw_key, key_hash, key_prefix


def hash_api_key(raw_key: str) -> str:
    """SHA-256 hex digest of a raw API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

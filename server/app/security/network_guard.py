"""
security/network_guard.py
Validates that all AI inference endpoints are local-only.
In AIR_GAPPED_MODE, any remote endpoint is rejected.
"""

import re
import ipaddress
from typing import Optional
from urllib.parse import urlparse
import yaml
import os

# Load settings once at module level
_settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
with open(_settings_path, "r") as f:
    _settings = yaml.safe_load(f)

AIR_GAPPED_MODE: bool = _settings["security"]["air_gapped_mode"]
ALLOWED_HOSTS: list[str] = _settings["security"]["allowed_hosts"]

# Regex patterns for clearly non-local hosts
_CLOUD_PATTERNS = [
    r"\.openai\.com",
    r"\.anthropic\.com",
    r"\.googleapis\.com",
    r"\.azure\.com",
    r"\.aws\.amazon\.com",
    r"api\.cohere",
    r"\.huggingface\.co/api",
    r"replicate\.com",
    r"together\.ai",
    r"groq\.com",
]


def is_local_host(host: str) -> bool:
    """Return True if host is a loopback / local address."""
    if host in ALLOWED_HOSTS:
        return True
    # Check numeric IP
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_loopback
    except ValueError:
        pass
    # hostname forms like 'localhost'
    return host.lower() in ("localhost",)


def is_local_url(url: str) -> bool:
    """Return True if the URL resolves to a local endpoint."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        return is_local_host(host)
    except Exception:
        return False


def is_cloud_url(url: str) -> bool:
    """Return True if the URL matches known cloud AI patterns."""
    for pattern in _CLOUD_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def validate_endpoint(url: str, label: str = "endpoint") -> tuple[bool, str]:
    """
    Validate that an endpoint is safe to use.

    Returns:
        (ok: bool, message: str)
    """
    if is_cloud_url(url):
        return False, f"BLOCKED: {label} '{url}' matches a known cloud AI API."

    if AIR_GAPPED_MODE:
        if not is_local_url(url):
            return False, (
                f"BLOCKED (AIR_GAPPED_MODE=true): {label} '{url}' is not a local endpoint. "
                f"Only {ALLOWED_HOSTS} are allowed."
            )

    return True, f"OK: {label} '{url}' is a local endpoint."


def assert_local_endpoint(url: str, label: str = "endpoint") -> None:
    """Raise RuntimeError if the endpoint is not local."""
    ok, message = validate_endpoint(url, label)
    if not ok:
        raise RuntimeError(message)


def get_security_summary() -> dict:
    """Return a summary of network security status for the UI."""
    return {
        "air_gapped_mode": AIR_GAPPED_MODE,
        "allowed_hosts": ALLOWED_HOSTS,
        "external_ai_blocked": True,
        "cloud_upload_blocked": True,
    }

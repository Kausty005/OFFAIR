import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from security.network_guard import is_local_host, is_cloud_url, validate_endpoint

def test_is_local_host():
    assert is_local_host("localhost") is True
    assert is_local_host("127.0.0.1") is True
    assert is_local_host("::1") is True
    assert is_local_host("api.openai.com") is False
    assert is_local_host("8.8.8.8") is False

def test_is_cloud_url():
    assert is_cloud_url("https://api.openai.com/v1/chat") is True
    assert is_cloud_url("https://generativelanguage.googleapis.com/") is True
    assert is_cloud_url("http://localhost:11434") is False

def test_validate_endpoint():
    # In air-gapped mode (default), external URLs should fail
    ok, msg = validate_endpoint("https://api.openai.com")
    assert ok is False
    assert "BLOCKED" in msg
    
    ok, msg = validate_endpoint("http://localhost:11434")
    assert ok is True
    assert "OK" in msg

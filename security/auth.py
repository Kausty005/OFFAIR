"""
security/auth.py
Local JWT authentication & RBAC for the Sovereign AI Workbench.
No external auth services — everything runs locally.
"""

import hashlib
import os
import sys
import time
from typing import Optional

import jwt

_base = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, _base)

from security.audit import log

# ── Configuration ──────────────────────────────────────────────
JWT_SECRET = os.getenv("OFFAIR_JWT_SECRET", "offair-sovereign-local-secret-key-2024")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# ── Role Hierarchy ─────────────────────────────────────────────
ROLES = {
    "Technician": {
        "level": 1,
        "clearance": ["public"],
        "description": "Field technician — limited document access",
    },
    "Engineer": {
        "level": 2,
        "clearance": ["public", "internal"],
        "description": "Engineer — internal documents + public",
    },
    "Manager": {
        "level": 3,
        "clearance": ["public", "internal", "confidential"],
        "description": "Manager — full document access",
    },
}

# ── Demo Users (local only) ───────────────────────────────────
def _hash_password(password: str) -> str:
    """Simple SHA-256 hash for prototype. Replace with bcrypt for production."""
    return hashlib.sha256(password.encode()).hexdigest()

DEMO_USERS = {
    "EMP-TECH": {
        "name": "Amit Kumar",
        "role": "Technician",
        "department": "Maintenance",
        "password_hash": _hash_password("tech123"),
    },
    "EMP-ENG": {
        "name": "Rahul Sharma",
        "role": "Engineer",
        "department": "Maintenance",
        "password_hash": _hash_password("engineer123"),
    },
    "EMP-MGR": {
        "name": "Priya Patel",
        "role": "Manager",
        "department": "Operations",
        "password_hash": _hash_password("manager123"),
    },
}


# ── Auth Functions ─────────────────────────────────────────────

def authenticate(employee_id: str, password: str) -> Optional[dict]:
    """
    Authenticate a user by employee ID and password.
    Returns user info dict (without password) or None.
    """
    user = DEMO_USERS.get(employee_id.upper())
    if not user:
        log("AUTH_FAILED", employee_id=employee_id, reason="user_not_found")
        return None

    if user["password_hash"] != _hash_password(password):
        log("AUTH_FAILED", employee_id=employee_id, reason="wrong_password")
        return None

    log("AUTH_SUCCESS", employee_id=employee_id, role=user["role"])
    return {
        "employee_id": employee_id.upper(),
        "name": user["name"],
        "role": user["role"],
        "department": user["department"],
    }


def create_token(user_info: dict) -> str:
    """Create a JWT token for an authenticated user."""
    payload = {
        **user_info,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRY_HOURS * 3600,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    """Verify and decode a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        log("AUTH_TOKEN_EXPIRED")
        return None
    except jwt.InvalidTokenError as e:
        log("AUTH_TOKEN_INVALID", error=str(e))
        return None


def get_user_clearance(role: str) -> list[str]:
    """Get the document clearance levels for a role."""
    role_info = ROLES.get(role, ROLES["Technician"])
    return role_info["clearance"]


def get_role_level(role: str) -> int:
    """Get the numeric level for a role (higher = more access)."""
    return ROLES.get(role, {}).get("level", 1)

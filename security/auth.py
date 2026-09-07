"""Local MongoDB-backed authentication and session lookup."""

from datetime import datetime, timezone
import hashlib
import os
import secrets
from typing import Any, Optional

from pymongo import MongoClient
from pymongo.collection import Collection


MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "offair")
ALLOWED_ROLES = frozenset({"hr", "employee", "finance", "engineer", "admin"})
_client: Optional[MongoClient] = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _database():
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
    _client.admin.command("ping")
    return _client[MONGODB_DATABASE]


def _users() -> Collection:
    collection = _database().users
    collection.create_index("username", unique=True)
    return collection


def _sessions() -> Collection:
    collection = _database().sessions
    collection.create_index("token", unique=True)
    collection.create_index("expires_at", expireAfterSeconds=0)
    return collection


def _hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        salt_hex, digest_hex = encoded.split("$", 1)
        expected = _hash_password(password, bytes.fromhex(salt_hex)).split("$", 1)[1]
        return secrets.compare_digest(expected, digest_hex)
    except (ValueError, TypeError):
        return False


def register_user(username: str, password: str, role: str, details: dict[str, Any]) -> dict[str, Any]:
    username = username.strip().lower()
    role = role.strip().lower()
    if role not in ALLOWED_ROLES:
        raise ValueError("Unsupported role")
    if len(username) < 3 or len(password) < 8:
        raise ValueError("Username must have 3+ characters and password must have 8+ characters")

    now = _now()
    document = {
        "username": username,
        "password_hash": _hash_password(password),
        "role": role,
        "details": details,
        "created_at": now,
        "updated_at": now,
    }
    try:
        _users().insert_one(document)
    except Exception as exc:
        if "duplicate" in str(exc).lower():
            raise ValueError("Username already exists") from exc
        raise
    return {"username": username, "role": role, "details": details}


def login_user(username: str, password: str, role: str) -> dict[str, Any]:
    role = role.strip().lower()
    user = _users().find_one({"username": username.strip().lower()})
    if not user or not _verify_password(password, user.get("password_hash", "")):
        raise ValueError("Invalid username or password")
    if user.get("role") != role:
        raise ValueError("Selected role does not match this account")

    token = secrets.token_urlsafe(32)
    now = _now()
    _users().update_one({"_id": user["_id"]}, {"$set": {"last_login_at": now}})
    _sessions().insert_one({
        "token": token,
        "username": user["username"],
        "role": user["role"],
        "created_at": now,
        "expires_at": datetime.fromtimestamp(now.timestamp() + 8 * 60 * 60, timezone.utc),
    })
    _database().login_events.insert_one({
        "username": user["username"],
        "role": user["role"],
        "logged_in_at": now,
    })
    return {"token": token, "username": user["username"], "role": user["role"], "details": user.get("details", {})}


def user_from_token(token: str) -> Optional[dict[str, str]]:
    if not token:
        return None
    session = _sessions().find_one({"token": token})
    if not session:
        return None
    return {"username": session["username"], "role": session["role"]}


def logout_user(token: str) -> None:
    if token:
        _sessions().delete_one({"token": token})
"""Local authentication and session management with MongoDB and zero-dependency JSON fallback."""

from datetime import datetime, timezone
import hashlib
import json
import logging
import os
import secrets
from pathlib import Path
from typing import Any, Optional

from pymongo import MongoClient
from pymongo.collection import Collection

logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "offair")
ALLOWED_ROLES = frozenset({"hr", "employee", "finance", "engineer", "admin"})

_client: Optional[MongoClient] = None
_mongo_status: Optional[bool] = None

DATA_DIR = Path("workspace/auth_data")
USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _check_mongo() -> bool:
    global _client, _mongo_status
    if _mongo_status is not None:
        return _mongo_status
    try:
        if _client is None:
            _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1000)
        _client.admin.command("ping")
        _mongo_status = True
        logger.info("MongoDB connected successfully for authentication storage.")
        return True
    except Exception:
        _mongo_status = False
        logger.info("MongoDB unavailable on localhost:27017. Using local file-backed JSON storage for auth.")
        return False


def _database():
    global _client
    if _client is None:
        _client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=1000)
    _client.admin.command("ping")
    return _client[MONGODB_DATABASE]


def _users_mongo() -> Collection:
    collection = _database().users
    collection.create_index("username", unique=True)
    return collection


def _sessions_mongo() -> Collection:
    collection = _database().sessions
    collection.create_index("token", unique=True)
    collection.create_index("expires_at", expireAfterSeconds=0)
    return collection


# --- JSON File Fallback Implementation ---

def _load_json(file_path: Path) -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not file_path.exists():
        return {}
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(file_path: Path, data: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


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
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }

    if _check_mongo():
        try:
            _users_mongo().insert_one({
                **document,
                "created_at": now,
                "updated_at": now,
            })
            return {"username": username, "role": role, "details": details}
        except Exception as exc:
            if "duplicate" in str(exc).lower():
                raise ValueError("Username already exists") from exc
            logger.warning(f"MongoDB write failed ({exc}), storing user in local JSON store.")

    users = _load_json(USERS_FILE)
    if username in users:
        raise ValueError("Username already exists")
    users[username] = document
    _save_json(USERS_FILE, users)
    return {"username": username, "role": role, "details": details}


def login_user(username: str, password: str, role: str) -> dict[str, Any]:
    username = username.strip().lower()
    role = role.strip().lower()
    now = _now()
    token = secrets.token_urlsafe(32)

    if _check_mongo():
        try:
            user = _users_mongo().find_one({"username": username})
            if not user or not _verify_password(password, user.get("password_hash", "")):
                raise ValueError("Invalid username or password")
            if user.get("role") != role:
                raise ValueError("Selected role does not match this account")

            _users_mongo().update_one({"_id": user["_id"]}, {"$set": {"last_login_at": now}})
            _sessions_mongo().insert_one({
                "token": token,
                "username": user["username"],
                "role": user["role"],
                "created_at": now,
                "expires_at": datetime.fromtimestamp(now.timestamp() + 8 * 60 * 60, timezone.utc),
            })
            return {"token": token, "username": user["username"], "role": user["role"], "details": user.get("details", {})}
        except ValueError:
            raise
        except Exception as exc:
            logger.warning(f"MongoDB login lookup failed ({exc}), attempting local JSON store.")

    users = _load_json(USERS_FILE)
    user = users.get(username)
    if not user or not _verify_password(password, user.get("password_hash", "")):
        raise ValueError("Invalid username or password")
    if user.get("role") != role:
        raise ValueError("Selected role does not match this account")

    sessions = _load_json(SESSIONS_FILE)
    sessions[token] = {
        "token": token,
        "username": username,
        "role": role,
        "expires_at": now.timestamp() + (8 * 3600),
    }
    _save_json(SESSIONS_FILE, sessions)
    return {"token": token, "username": username, "role": role, "details": user.get("details", {})}


def user_from_token(token: str) -> Optional[dict[str, str]]:
    if not token:
        return None

    if _check_mongo():
        try:
            session = _sessions_mongo().find_one({"token": token})
            if session:
                return {"username": session["username"], "role": session["role"]}
        except Exception:
            pass

    sessions = _load_json(SESSIONS_FILE)
    session = sessions.get(token)
    if not session:
        return None
    if session.get("expires_at", 0) < datetime.now(timezone.utc).timestamp():
        return None
    return {"username": session["username"], "role": session["role"]}


def logout_user(token: str) -> None:
    if not token:
        return

    if _check_mongo():
        try:
            _sessions_mongo().delete_one({"token": token})
        except Exception:
            pass

    sessions = _load_json(SESSIONS_FILE)
    if token in sessions:
        del sessions[token]
        _save_json(SESSIONS_FILE, sessions)
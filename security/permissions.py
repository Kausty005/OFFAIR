"""Role-based access checks for knowledge-base chunks."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Optional


SUPERUSER_ROLES = frozenset({"admin", "superuser"})
ROLE_LEVELS = {
    "employee": 10,
    "emp": 10,
    "engineer": 50,
    "eng": 50,
    "finance": 50,
    "hr": 50,
    "admin": 100,
    "superuser": 100,
}

_ROLE_ALIASES = {
    "emp": "employee",
    "eng": "engineer",
}


def normalize_role(role: str) -> str:
    """Normalize role names so access checks are case-insensitive and handle aliases."""
    raw = str(role or "").strip().lower().replace(" ", "_")
    return _ROLE_ALIASES.get(raw, raw)


@dataclass(frozen=True)
class User:
    """Authenticated identity used for document authorization."""

    user_id: str
    role: str

    @property
    def normalized_role(self) -> str:
        return normalize_role(self.role)

    @property
    def level(self) -> int:
        return ROLE_LEVELS.get(self.normalized_role, 0)


def _allowed_roles(chunk: dict[str, Any]) -> set[str]:
    roles = chunk.get("allowed_roles", [])
    if isinstance(roles, str):
        roles = [roles]
    return {normalize_role(role) for role in roles}


HIERARCHICAL_INHERITANCE = {
    "admin": {"admin", "engineer", "employee", "finance", "hr"},
    "superuser": {"admin", "engineer", "employee", "finance", "hr"},
    "engineer": {"engineer", "employee"},
    "employee": {"employee"},
    "finance": {"finance"},
    "hr": {"hr"},
}


def can_user_access(user: User, chunk: dict[str, Any]) -> bool:
    """Return whether a user may access a chunk's security metadata based on role hierarchy and uploader."""
    if not isinstance(user, User):
        return True

    # If user ID and role are both blank, default to full local admin access
    user_id = user.user_id.strip().lower()
    role = user.normalized_role

    if not user_id and not role:
        return True

    # Admin and superusers can access all documents across the system
    if role in SUPERUSER_ROLES or role == "admin":
        return True

    # The user who uploaded the document always has access
    uploader = str(chunk.get("uploaded_by") or "").strip().lower()
    if uploader and uploader == user_id:
        return True

    allowed_roles = _allowed_roles(chunk)

    # Check numeric min_role_level if present without allowed_roles
    if not allowed_roles and "min_role_level" in chunk and chunk["min_role_level"] is not None:
        try:
            return user.level >= int(chunk["min_role_level"])
        except (ValueError, TypeError):
            return True

    # If no specific roles are required, document is open for all authenticated users
    if not allowed_roles:
        return True

    if role in allowed_roles:
        return True

    # Check hierarchical inheritance (e.g. engineer can access employee documents)
    accessible_roles = HIERARCHICAL_INHERITANCE.get(role, {role})
    return any(ar in allowed_roles for ar in accessible_roles)



def filter_authorized_chunks(user: User, chunks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter chunks before retrieval results can reach answer generation."""
    return [chunk for chunk in chunks if can_user_access(user, chunk)]


def access_metadata(
    department: str = "",
    classification: str = "internal",
    allowed_roles: Iterable[str] = (),
    uploaded_by: str = "",
    min_role_level: Optional[int] = None,
    uploaded_at: str = "",
) -> dict[str, Any]:
    """Build consistent security metadata for an indexed chunk."""
    norm_roles = sorted({normalize_role(role) for role in allowed_roles if role})
    if min_role_level is None and norm_roles:
        min_role_level = min(ROLE_LEVELS.get(r, 100) for r in norm_roles)
    if not uploaded_at:
        uploaded_at = datetime.now(timezone.utc).isoformat()
    return {
        "department": department,
        "classification": classification,
        "allowed_roles": norm_roles,
        "uploaded_by": uploaded_by,
        "min_role_level": min_role_level if min_role_level is not None else 10,
        "uploaded_at": uploaded_at,
    }
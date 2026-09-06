"""
tools/files.py
Sandboxed file I/O — restricts access to the application workspace.
The agent can only read/write files within the defined workspace paths.
"""

import os
import shutil
from pathlib import Path
from typing import Optional
import yaml

_settings_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
with open(_settings_path, "r") as f:
    _settings = yaml.safe_load(f)

_WORKSPACE = Path(_settings["paths"]["workspace"]).resolve()
_UPLOADS = Path(_settings["paths"]["uploads"]).resolve()
_OUTPUTS = Path(_settings["paths"]["outputs"]).resolve()
_TEMP = Path(_settings["paths"]["temporary"]).resolve()
_KB = Path(_settings["paths"]["knowledge_base"]).resolve()

# Ensure directories exist
for _d in [_WORKSPACE, _UPLOADS, _OUTPUTS, _TEMP, _KB]:
    _d.mkdir(parents=True, exist_ok=True)

ALLOWED_ROOTS = [_WORKSPACE, _KB]


def _resolve_safe(path: str | Path) -> Path:
    """
    Resolve a path and verify it is within an allowed workspace root.
    Raises PermissionError if the path escapes the workspace.
    """
    resolved = Path(path).resolve()
    for root in ALLOWED_ROOTS:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise PermissionError(
        f"Access denied: '{path}' is outside the allowed workspace. "
        f"Allowed roots: {[str(r) for r in ALLOWED_ROOTS]}"
    )


def read_file(path: str | Path) -> str:
    """Read a text file from within the workspace."""
    safe = _resolve_safe(path)
    return safe.read_text(encoding="utf-8", errors="replace")


def read_bytes(path: str | Path) -> bytes:
    """Read a binary file from within the workspace."""
    safe = _resolve_safe(path)
    return safe.read_bytes()


def write_file(path: str | Path, content: str) -> Path:
    """Write text to a file within the workspace."""
    safe = _resolve_safe(path)
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_text(content, encoding="utf-8")
    return safe


def write_bytes(path: str | Path, content: bytes) -> Path:
    """Write binary content to a file within the workspace."""
    safe = _resolve_safe(path)
    safe.parent.mkdir(parents=True, exist_ok=True)
    safe.write_bytes(content)
    return safe


def list_files(directory: str | Path, pattern: str = "*") -> list[Path]:
    """List files in a workspace directory matching a glob pattern."""
    safe = _resolve_safe(directory)
    if not safe.is_dir():
        return []
    return sorted(safe.glob(pattern))


def create_directory(path: str | Path) -> Path:
    """Create a directory within the workspace."""
    safe = _resolve_safe(path)
    safe.mkdir(parents=True, exist_ok=True)
    return safe


def file_exists(path: str | Path) -> bool:
    """Check if a file exists within the workspace."""
    try:
        safe = _resolve_safe(path)
        return safe.exists()
    except PermissionError:
        return False


def get_output_path(filename: str) -> Path:
    """Return a safe output path for a generated file."""
    return _OUTPUTS / filename


def get_upload_path(filename: str) -> Path:
    """Return the path where an uploaded file should be saved."""
    return _UPLOADS / filename


def get_temp_path(filename: str) -> Path:
    """Return a temporary workspace path."""
    return _TEMP / filename


def save_upload(source_bytes: bytes, filename: str) -> Path:
    """Save uploaded file bytes to the uploads directory."""
    dest = _UPLOADS / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(source_bytes)
    return dest


def cleanup_temp() -> int:
    """Remove all files from the temporary directory. Returns count removed."""
    count = 0
    for f in _TEMP.glob("*"):
        try:
            if f.is_file():
                f.unlink()
                count += 1
            elif f.is_dir():
                shutil.rmtree(f)
                count += 1
        except Exception:
            pass
    return count


def get_workspace_summary() -> dict:
    """Return a summary of workspace contents for UI display."""
    return {
        "uploads": len(list(_UPLOADS.glob("*"))),
        "outputs": len(list(_OUTPUTS.glob("*"))),
        "knowledge_base": len(list(_KB.glob("*"))),
        "workspace_root": str(_WORKSPACE),
    }

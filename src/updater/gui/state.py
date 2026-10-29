"""
Persisted GUI runtime state (last chosen project / packages folder).

Spec: docs/specs/gui_folder_dialog_spec.md section 3.3

Why a second file next to updater.toml: updater.toml is the deployment config an
administrator owns, while "which folder was last opened here" is operator state.
Keeping them apart means the GUI can remember a choice without overwriting the
shipped toml - and users who never touch the source control keep the automatic
chain (toml -> wheels folder above the exe -> built-in default).
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

STATE_FILENAME = "updater_state.json"
STATE_SCHEMA = 1
COMPANY_DIR = "Test Matrix"
PRODUCT_DIR = "Updater"


@dataclass
class GuiState:
    """Last folders chosen in the GUI; None means "use automatic resolution"."""

    project: str | None = None
    source: str | None = None
    updated_at: str = ""

    def is_empty(self) -> bool:
        return not self.project and not self.source


def state_path(exe_dir: Path) -> Path:
    """Primary location: next to the exe, so a portable deployment keeps its state."""
    return exe_dir / STATE_FILENAME


def fallback_state_dir() -> Path:
    """Used when the exe folder is read-only (e.g. the updater runs off a share)."""
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    return base / COMPANY_DIR / PRODUCT_DIR


def state_files(exe_dir: Path) -> list[Path]:
    """Candidate state files, best first: exe folder, then %LOCALAPPDATA%."""
    primary = state_path(exe_dir)
    fallback = fallback_state_dir() / STATE_FILENAME
    return [primary] if fallback == primary else [primary, fallback]


def load_saved_state(exe_dir: Path) -> tuple[GuiState, Path, str]:
    """
    Load whichever state file this deployment uses.

    Returns ``(state, write_target, error)``.  With no file yet, the write target
    is the exe folder, so the first explicit choice is stored next to the exe -
    and a deployment that never chooses one stays stateless (spec section 3.3.4).
    """
    files = state_files(exe_dir)
    for path in files:
        if path.exists():
            state, error = load_state(path)
            return state, path, error
    return GuiState(), files[0], ""


def load_state(path: Path) -> tuple[GuiState, str]:
    """
    Read the state file.

    Returns (state, error).  A missing file is not an error - it yields an empty
    state.  A corrupt file also yields an empty state but reports the problem so
    the GUI can say why nothing was restored.
    """
    if not path.exists():
        return GuiState(), ""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return GuiState(), f"無法讀取 {path.name}: {type(exc).__name__}: {exc}"

    if not isinstance(raw, dict) or raw.get("schema") != STATE_SCHEMA:
        return GuiState(), f"{path.name} 格式不支援（schema 不符），已忽略"

    return (
        GuiState(
            project=_clean(raw.get("project")),
            source=_clean(raw.get("source")),
            updated_at=str(raw.get("updated_at", "")),
        ),
        "",
    )


def save_state(path: Path, state: GuiState) -> str:
    """
    Write the state atomically (tmp file + ``os.replace``).

    Returns "" on success or a human readable error - the GUI logs it but keeps
    running, because losing the memory of a folder is not a reason to fail an update.
    """
    payload = asdict(state)
    payload["schema"] = STATE_SCHEMA
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=f"{STATE_FILENAME}.", suffix=".tmp", dir=str(path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            os.replace(tmp_name, path)
        except OSError:
            Path(tmp_name).unlink(missing_ok=True)
            raise
    except OSError as exc:
        return f"無法儲存 {path}: {type(exc).__name__}: {exc}"
    return ""


def usable(value: str | None) -> bool:
    """True when a remembered path still points at a real folder."""
    if not value:
        return False
    return Path(value).is_dir()


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None

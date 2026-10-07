"""Portable locking and native executable selection for the workflow helpers."""

import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path


if sys.version_info < (3, 11):
    selector = "py -3.11" if sys.platform == "win32" else "python3.11"
    raise SystemExit(
        f"Python 3.11 or later is required; selected interpreter: {sys.executable} "
        f"({sys.version.split()[0]}). Install Python 3.11+ and rerun this helper with {selector}."
    )

try:
    import portalocker
except ModuleNotFoundError as error:
    if error.name != "portalocker":
        raise
    requirements = Path(__file__).resolve().parents[1] / "requirements.txt"
    prefix = "& " if sys.platform == "win32" else ""
    raise SystemExit(
        f"Missing Portalocker for selected interpreter: {sys.executable}. Install with:\n"
        f'{prefix}"{sys.executable}" -m pip install -r "{requirements}"'
    ) from None


class LockError(RuntimeError):
    """The locking backend failed without establishing another holder."""


class LockContended(LockError):
    """Another operation holds the requested exclusive lock."""


class ExecutableError(RuntimeError):
    """The selected Codex executable cannot be used natively."""


def resolve_codex():
    """Select one native executable path, without interpreting shell commands."""
    selected = os.environ.get("IMPLEMENT_SPEC_CODEX")
    if selected is None:
        selected = shutil.which("codex")
    guidance = "Set IMPLEMENT_SPEC_CODEX to one native Codex executable path (without arguments)."
    if not selected:
        raise ExecutableError(f"No Codex executable selected on PATH or in IMPLEMENT_SPEC_CODEX. {guidance}")
    try:
        path = Path(selected).resolve(strict=True)
    except (OSError, ValueError) as error:
        raise ExecutableError(f"Invalid Codex executable {selected!r}: {error}. {guidance}") from error
    if not path.is_file() or not os.access(path, os.X_OK):
        raise ExecutableError(f"Codex selection is not an executable file: {path}. {guidance}")
    try:
        with path.open("rb") as stream:
            header = stream.read(64)
            if os.name == "nt":
                native = len(header) == 64 and header[:2] == b"MZ"
                if native:
                    stream.seek(int.from_bytes(header[60:64], "little"))
                    native = stream.read(4) == b"PE\0\0"
            else:
                native = header[:4] == b"\x7fELF"
    except OSError as error:
        raise ExecutableError(f"Cannot read Codex executable {path}: {error}. {guidance}") from error
    if not native:
        raise ExecutableError(f"Unsupported Codex executable or script wrapper: {path}. {guidance}")
    return path


@contextmanager
def exclusive(path):
    """Acquire immediately or raise; keep the lock file stable after release."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = portalocker.Lock(
        path, mode="a+b", timeout=0,
        flags=portalocker.LOCK_EX | portalocker.LOCK_NB,
        raise_on_release_error=True,
    )
    try:
        handle = lock.acquire()
    except portalocker.AlreadyLocked as error:
        raise LockContended("Another workflow operation owns this checkout.") from error
    except portalocker.LockException as error:
        raise LockError(f"Cannot lock {path}: {error}") from error
    try:
        yield handle.fileno()
    finally:
        try:
            lock.release()
        except portalocker.LockException as error:
            raise LockError(f"Cannot release lock {path}: {error}") from error

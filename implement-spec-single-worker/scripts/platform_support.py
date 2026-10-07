"""Portable checkout locking; workflow ownership stays in the entry helpers."""

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

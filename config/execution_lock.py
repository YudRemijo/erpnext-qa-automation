"""Nonblocking local OS lock; never silently run QA writes without protection."""

import os
from contextlib import contextmanager


class LockUnavailable(RuntimeError):
    pass


def _backend():
    try:
        if os.name == "nt":
            import msvcrt
            return "windows", msvcrt
        if os.name == "posix":
            import fcntl
            return "posix", fcntl
    except ImportError:
        pass
    raise LockUnavailable("No supported OS lock is available; QA writes are disabled")


@contextmanager
def exclusive_qa_lock(path):
    kind, backend = _backend()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if kind == "windows":
                backend.locking(handle.fileno(), backend.LK_NBLCK, 1)
            elif kind == "posix":
                backend.flock(handle.fileno(), backend.LOCK_EX | backend.LOCK_NB)
            else:
                raise LockUnavailable("Unknown OS lock; QA writes are disabled")
        except OSError:
            raise LockUnavailable("Another QA run holds the lock, or locking failed; writes are disabled") from None
        try:
            yield
        finally:
            handle.seek(0)
            if kind == "windows":
                backend.locking(handle.fileno(), backend.LK_UNLCK, 1)
            else:
                backend.flock(handle.fileno(), backend.LOCK_UN)
    # Never unlink: another process may already hold a descriptor for this inode.

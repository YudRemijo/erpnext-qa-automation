"""Local filesystem/OS tests: no ERPNext, authentication or browser."""

import pytest

from config import execution_lock
from config.execution_lock import LockUnavailable, exclusive_qa_lock

pytestmark = pytest.mark.offline


def test_lock_rejects_competing_descriptor_and_releases(tmp_path):
    path = tmp_path / "qa.lock"
    with exclusive_qa_lock(path):
        with pytest.raises(LockUnavailable, match="lock"):
            with exclusive_qa_lock(path):
                pytest.fail("Competing lock was acquired")
    with exclusive_qa_lock(path):
        assert path.exists()


def test_lock_released_when_test_raises(tmp_path):
    path = tmp_path / "qa.lock"
    with pytest.raises(ValueError):
        with exclusive_qa_lock(path):
            raise ValueError("synthetic failure")
    with exclusive_qa_lock(path):
        pass


def test_unknown_backend_refuses_execution(monkeypatch, tmp_path):
    monkeypatch.setattr(execution_lock, "_backend", lambda: ("unsupported", None))
    with pytest.raises(LockUnavailable, match="Unknown OS lock"):
        with exclusive_qa_lock(tmp_path / "qa.lock"):
            pytest.fail("Unsafe execution was allowed")

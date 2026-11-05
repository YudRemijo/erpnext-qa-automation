"""CI safeguards and repository contracts; no browser or local ERPNext required."""

import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from config.settings import Settings
from scripts.check_project import private_path, workflow_contract, read_candidate

pytestmark = pytest.mark.offline
ROOT = Path(__file__).resolve().parents[2]


def test_offline_guard_blocks_network_and_configuration():
    with pytest.raises(AssertionError, match="Offline"):
        socket.create_connection(("127.0.0.1", 8080))
    with pytest.raises(AssertionError, match="Offline"):
        Settings.load()


@pytest.mark.parametrize("name", [".env", "backups/dump.sql.gz", "artifacts/run/manifest.json",
                                 "private/site_config.json", "traces/auth.zip"])
def test_private_files_cannot_be_public_candidates(name):
    assert private_path(name)


def test_reviewed_nonsecret_examples_are_publishable():
    assert not private_path(".env.example")
    assert private_path("infra/common_site_config.json")


def test_index_audit_reads_staged_blob_not_working_tree(tmp_path):
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    source = tmp_path / "example.py"
    source.write_bytes(b"value = 1\n")
    subprocess.run(["git", "-C", str(tmp_path), "-c", "core.autocrlf=false", "add", "--", "example.py"], check=True)
    source.write_text("invalid Python working tree\n", encoding="utf-8")
    assert read_candidate("example.py", staged=True, root=tmp_path) == "value = 1\n"
    assert read_candidate("example.py", root=tmp_path) != "value = 1\n"


def test_workflow_rejects_transaction_flag():
    original = (ROOT / ".github/workflows/ci.yml").read_text()
    assert not workflow_contract(original)
    assert workflow_contract(original + "\n# --run-transactions\n")


@pytest.mark.parametrize("args, message", [
    (["-m", "offline", "--run-transactions"], "--run-transactions is forbidden"),
    (["--collect-only", "-m", "integration"], "select tests with -m offline"),
    (["--definitely-invalid-option"], "unrecognized arguments"),
])
def test_invalid_ci_commands_fail_before_execution(args, message):
    # Child process only collects or fails configuration; no browser or auth starts.
    env = {k: v for k, v in os.environ.items() if not k.startswith("ERPNEXT_")}
    env["CI"] = "true"
    result = subprocess.run([sys.executable, "-m", "pytest", *args], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode != 0
    assert message in result.stdout + result.stderr

"""Dependency-free syntax/configuration and publication-safety checks.

This is a focused project check, not a general secret scanner or YAML/Actions linter.
Never print matched secret values. No network, browser, Docker, or ERPNext is used.
"""

import ast
import argparse
import re
import subprocess
import sys
import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRIVATE_NAMES = {".env", "site_config.json", "common_site_config.json", "auth.json"}
PRIVATE_DIRS = {"artifacts", "reports", "backups", "ERPNext-QA-Backups", ".auth",
                ".venv", "screenshots", "traces", "videos", "test-results", "secrets", "credentials", "infra"}
PRIVATE_SUFFIXES = (".sql", ".sql.gz", ".dump", ".7z", ".zip", ".tar", ".tar.gz", ".tgz", ".pem", ".key")


def git_paths(*options):
    result = subprocess.run(["git", "ls-files", "-z", *options], cwd=ROOT,
                            capture_output=True, check=True)
    return {name.decode("utf-8") for name in result.stdout.split(b"\0") if name}


def private_path(name):
    path = Path(name)
    if name == ".env.example":
        return False
    return (path.name in PRIVATE_NAMES or path.name.startswith(".env.")
            or any(part in PRIVATE_DIRS for part in path.parts)
            or name.endswith(PRIVATE_SUFFIXES)
            or path.name.startswith(("storage-state", "storage_state", "storageState", "auth-state", "auth_state")))


def workflow_contract(text):
    required = ["on: [push, pull_request]", "contents: read", "persist-credentials: false",
                'python-version: "3.12"', 'CI: "true"', "python -m pip install -r requirements-dev.txt",
                "python -m pip check", "python scripts/check_project.py", "python -m pytest -m offline",
                "ubuntu-24.04", "windows-2022"]
    errors = ["Missing required CI contract: " + part for part in required if part not in text]
    for forbidden in ("--run-transactions", "localhost:8080", "secrets.", "pull_request_target",
                      "playwright install", "docker ", "continue-on-error", "write-all"):
        if forbidden in text:
            errors.append("Forbidden CI capability: " + forbidden)
    actions = re.findall(r"uses:\s*([^\s]+)", text)
    if len(actions) != 2 or any(not re.fullmatch(r"actions/(checkout|setup-python)@[0-9a-f]{40}", a) for a in actions):
        errors.append("CI must use exactly two approved SHA-pinned Actions")
    return errors


def read_candidate(name, staged=False, root=ROOT):
    if staged:
        result = subprocess.run(["git", "show", ":" + name], cwd=root,
                                capture_output=True, check=True)
        return result.stdout.decode("utf-8-sig")
    return (root / name).read_text(encoding="utf-8-sig")


def audit(staged=False):
    failures = []
    tracked = git_paths("--cached")
    candidates = tracked if staged else tracked | git_paths("--others", "--exclude-standard")
    if staged and not candidates:
        return ["Staged audit requires a nonempty index"]
    modes = subprocess.check_output(["git", "ls-files", "--stage", "-z"], cwd=ROOT)
    if any(not row.startswith(b"100644 ") and not row.startswith(b"100755 ")
           for row in modes.split(b"\0") if row):
        failures.append("Index contains a symlink, submodule or unsupported file mode; review required")
    for name in sorted(candidates):
        if private_path(name):
            failures.append(f"Private/generated file would be published: {name}")
            continue
        path = ROOT / name
        if not staged and not path.is_file():
            continue
        try:
            content = read_candidate(name, staged)
        except UnicodeError:
            failures.append(f"Unreviewed binary candidate: {name}")
            continue
        if path.suffix == ".py":
            try:
                ast.parse(content, filename=name)
            except (SyntaxError, UnicodeError):
                failures.append(f"Invalid Python syntax/encoding: {name}")
        patterns = [r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                    r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",
                    r"(?i)\b[A-Z]:[\\/]Users[\\/][^\\/\s`]+",
                    r"(?im)^\s*[\"']?(?:ERPNEXT_PASSWORD|db_password|encryption_key|api_secret)[\"']?\s*[:=]\s*[\"']?([^\s\"',}]+)"]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                value = match.group(1) if match.lastindex else match.group()
                if value.startswith(("REPLACE_", "${", "None", "null")):
                    continue
                failures.append(f"Potential secret requires review: {name}:{content.count(chr(10), 0, match.start()) + 1}")
    config = tomllib.loads(read_candidate("pyproject.toml", staged))
    markers = config["tool"]["pytest"]["ini_options"]["markers"]
    for required in ("offline", "integration", "transactional", "browser"):
        if not any(m.startswith(required + ":") for m in markers):
            failures.append(f"Missing registered marker: {required}")
    for line in read_candidate("requirements-dev.txt", staged).splitlines():
        if line and not line.startswith("#") and not re.fullmatch(r"[A-Za-z0-9_-]+==[0-9]+(?:\.[0-9]+)+", line):
            failures.append("Direct dependencies must use exact version pins")
    failures.extend(workflow_contract(read_candidate(".github/workflows/ci.yml", staged)))
    probes = [".env", ".env.private", "artifacts/run/manifest.json", "backups/example.sql.gz",
              "reports/offline.xml", "traces/example.zip", "private/site_config.json", "infra/compose.yaml"]
    for probe in probes:
        ignored = subprocess.run(["git", "check-ignore", "--no-index", "--quiet", probe], cwd=ROOT)
        if ignored.returncode != 0:
            failures.append(f"Required ignore rule is missing: {probe}")
    mode = "index blobs" if staged else "working-tree candidates"
    print(f"Audited {len(candidates)} {mode} and {len(tracked)} indexed files; values suppressed")
    return failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", help="Audit exact Git index blobs, not working-tree content")
    args = parser.parse_args()
    try:
        issues = audit(staged=args.staged)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as error:
        print(f"Project check could not complete: {type(error).__name__}")
        sys.exit(1)
    for issue in issues:
        print(issue)
    print("Project checks FAILED" if issues else "Project checks PASSED")
    sys.exit(bool(issues))

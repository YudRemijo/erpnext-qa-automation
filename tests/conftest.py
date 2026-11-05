"""Isolated authenticated pages; authentication never records browser artifacts."""

import os

import json
import socket
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from collections.abc import Iterator

import pytest
from playwright.sync_api import Browser, Error, Page, expect

from config.settings import Settings
from config.diagnostics import start_restricted_trace
from config.execution_lock import LockUnavailable, exclusive_qa_lock
from pages.login_page import LoginPage


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-transactions", action="store_true", default=False,
                     help="Authorize local QA writes, including marked E2E submissions")
    parser.addini("ui_timeout_ms", "Auto-wait budget for UI actions and assertions", default="15000")
    parser.addini("navigation_timeout_ms", "Document navigation budget", default="30000")


def pytest_configure(config: pytest.Config) -> None:
    # One consistent assertion policy for the entire pytest session.
    expect.set_options(timeout=int(config.getini("ui_timeout_ms")))
    if os.environ.get("CI", "").lower() in {"true", "1"} and config.getoption("--run-transactions"):
        raise pytest.UsageError("CI is offline-only: --run-transactions is forbidden")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    # Classify by the actual fixture dependency closure, not a folder's name.
    for item in items:
        if "authenticated_page" in item.fixturenames:
            item.add_marker(pytest.mark.integration)
        if item.get_closest_marker("offline"):
            forbidden = {"authenticated_page", "settings", "browser", "context", "page", "playwright"}
            if forbidden.intersection(item.fixturenames) or any(
                item.get_closest_marker(m) for m in ("integration", "transactional", "browser")
            ):
                raise pytest.UsageError(f"Offline test has browser/ERPNext dependencies: {item.nodeid}")
    if not config.getoption("--run-transactions"):
        for item in items:
            if item.get_closest_marker("transactional"):
                item.add_marker(pytest.mark.skip(reason="Requires --run-transactions"))


def pytest_collection_finish(session):
    # Runs after -m deselection. GitHub Actions must never silently run integration.
    if os.environ.get("CI", "").lower() in {"true", "1"}:
        if any(not item.get_closest_marker("offline") for item in session.items):
            raise pytest.UsageError("CI is offline-only: select tests with -m offline")


@pytest.fixture(autouse=True)
def offline_safety(request, monkeypatch):
    if not request.node.get_closest_marker("offline"):
        return

    def forbidden(*args, **kwargs):
        raise AssertionError("Offline tests cannot use network, credentials or launch a browser")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(Settings, "load", forbidden)
    # Block direct library calls as well as accidental fixture dependencies.
    from playwright.sync_api import BrowserType
    monkeypatch.setattr(BrowserType, "launch", forbidden)
    monkeypatch.setattr(BrowserType, "launch_persistent_context", forbidden)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    report = yield
    if call.when == "call":
        item._qa_call_result = (report.outcome, call.excinfo.type.__name__ if call.excinfo else None)
    return report


@pytest.fixture(scope="session")
def settings() -> Settings:
    try:
        loaded = Settings.load()
    except (ValueError, OSError):
        pytest.fail("ERPNext configuration is missing or invalid; check local settings.", pytrace=False)
    return loaded


@pytest.fixture
def authenticated_page(
    browser: Browser, settings: Settings, pytestconfig: pytest.Config
) -> Iterator[Page]:
    # Raw API contexts deliberately bypass plugin artifact hooks, including on login failure.
    # Debug protocol logging may include fill values, so refuse it before entering secrets.
    if os.environ.get("DEBUG") or os.environ.get("PWDEBUG"):
        pytest.fail("Disable DEBUG and PWDEBUG before authenticated execution.", pytrace=False)

    context = browser.new_context()
    context.set_default_timeout(int(pytestconfig.getini("ui_timeout_ms")))
    context.set_default_navigation_timeout(int(pytestconfig.getini("navigation_timeout_ms")))
    try:
        page = context.new_page()
        login = LoginPage(page)
        for stage, action in (
            ("UI login", lambda: login.sign_in(settings)),
            ("ERPNext entry", lambda: login.enter_erpnext(settings.base_url)),
            ("workspace availability", login.assert_workspaces_available),
        ):
            stage_failed = False
            try:
                action()
            except (Error, AssertionError):
                stage_failed = True
            if stage_failed:
                # Outside except: no chained Playwright exception can expose fill values.
                pytest.fail(
                    f"Setup failed at stage: {stage}. Sensitive diagnostics suppressed.",
                    pytrace=False,
                )
        yield page
    finally:
        context.close()


@pytest.fixture(autouse=True)
def transaction_lock(request):
    if not (request.node.get_closest_marker("transactional") or request.node.get_closest_marker("negative")):
        yield
        return
    if hasattr(request.config, "workerinput"):
        pytest.fail("Transactional execution must not use parallel workers", pytrace=False)
    try:
        with exclusive_qa_lock(Path("artifacts") / "transaction.lock"):
            yield
    except LockUnavailable as error:
        pytest.fail(str(error), pytrace=False)


@pytest.fixture
def transaction_evidence(authenticated_page, record_property, request):
    run_id = str(uuid4())
    prefix = "qa011" if "qa011" in request.node.name else "negative"
    root = Path("artifacts") / f"{prefix}-{run_id}"
    root.mkdir(parents=True, exist_ok=False)
    record_property("evidence", str(root))
    report = {"run_id": run_id, "started_utc": datetime.now(timezone.utc).isoformat(),
              "result": "INCOMPLETE", "documents": [], "stages": []}

    def record(stage, data):
        # Callers pass curated business fields only, never credentials or cookies.
        report["stages"].append({"stage": stage, "data": data})
        if stage == "persisted":
            report["documents"].append(data)
        if stage == "result":
            report["result"] = data
        (root / "manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"{prefix} {stage}: {json.dumps(data)}", flush=True)

    # In installed Playwright 1.64, snapshotDom=False disables its HAR recorder.
    # Capture actions/screens only: no DOM, network headers/bodies, sources or login.
    context = authenticated_page.context
    start_restricted_trace(context)
    record("started", {"run_id": run_id, "trace_policy": "post-login actions/screens; no DOM/network/sources"})
    yield run_id, record
    outcome, exception_type = getattr(request.node, "_qa_call_result", ("unknown", None))
    if outcome == "failed":
        record("result", "FAIL" if exception_type == "AssertionError" else "INCONCLUSIVE")
        record("failure", {"exception_type": exception_type,
                           "category": "assertion_mismatch_requires_triage" if exception_type == "AssertionError"
                           else "automation_or_environment_requires_triage"})
    elif outcome == "skipped":
        record("result", "SKIP")
    if report["result"] != "PASS":
        record("incomplete", {"last_stage": report["stages"][-1]["stage"],
                              "action": "Inspect persisted IDs before another run; no automatic retry"})
        try:
            authenticated_page.screenshot(path=str(root / "failure-after-login.png"), full_page=True)
        except Exception:
            record("evidence_warning", "Screenshot unavailable; manifest retained")
        context.tracing.stop(path=root / "failure-actions-only.zip")
    else:
        context.tracing.stop()

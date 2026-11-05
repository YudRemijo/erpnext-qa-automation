"""Offline checks for local numeric interpretation and restricted trace privacy."""

from decimal import Decimal
from zipfile import ZipFile

import pytest

from pages.procurement import local_decimal
from config.diagnostics import start_restricted_trace


@pytest.mark.parametrize("display,expected", [
    ("10,000", "10"), ("$ 1.309,00", "1309"), ("-1,000", "-1"),
])
@pytest.mark.offline
def test_local_decimal_preserves_quantity_and_currency(display, expected):
    assert local_decimal(display) == Decimal(expected)


@pytest.mark.browser
def test_actions_only_trace_omits_dom_network_and_synthetic_secret(browser, tmp_path):
    # No ERPNext access, real credentials, dependency installation or real network.
    context = browser.new_context()
    secret = "SYNTHETIC-TRACE-PRIVACY-CHECK"
    context.set_extra_http_headers({"Authorization": "Bearer " + secret})
    page = context.new_page()
    page.route("**/*", lambda route: route.fulfill(body="<button>Diagnostic</button>", content_type="text/html"))
    start_restricted_trace(context)
    page.goto("http://offline-test.invalid/")
    page.get_by_role("button", name="Diagnostic").click()
    path = tmp_path / "restricted-trace.zip"
    context.tracing.stop(path=path)
    context.close()
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        trace_files = [n for n in archive.namelist() if n.endswith(".trace")]
        assert trace_files, "Trace must contain action events"
        for name in archive.namelist():
            content = archive.read(name)
            assert secret.encode() not in content
            if name.endswith(".network"):
                assert not content.strip(), "Restricted trace must not collect HAR/network records"
            if name.endswith(".trace"):
                assert b'"type":"frame-snapshot"' not in content
        assert b'"type":"before"' in b"".join(archive.read(n) for n in trace_files)

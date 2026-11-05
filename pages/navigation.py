"""Shared read-only navigation and loading assertions for ERPNext v16."""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import urlsplit

from playwright.sync_api import Page, Response, expect


LIST_LOAD = "/api/method/frappe.desk.reportview.get"
TREE_LOAD = "/api/method/erpnext.stock.doctype.warehouse.warehouse.get_children"
REPORT_LOAD = "/api/method/frappe.desk.query_report.run"


def assert_no_ui_error(page: Page) -> None:
    # A dialog/alert is not a successful terminal state. Never print its body.
    visible_errors = page.get_by_role("alert").or_(
        page.locator(".modal.show, .msgprint:visible, .error-page:visible")
    ).filter(visible=True)
    expect(visible_errors, "Unexpected application error/alert/dialog").to_have_count(0)


def assert_load_response(response: Response, label: str) -> None:
    assert response.ok, f"{label}: loading request failed (HTTP {response.status})"
    payload = response.json()
    assert isinstance(payload, dict), f"{label}: loading returned an invalid envelope"
    assert not any(payload.get(key) for key in ("exc", "exc_type", "exception", "error")), (
        f"{label}: application reported a loading error; response body suppressed"
    )
    assert "message" in payload, f"{label}: loading response lacks its result envelope"


def assert_loaded(page: Page, label: str) -> str:
    assert_no_ui_error(page)
    if label == "Warehouse":
        tree = page.get_by_role("tree")
        expect(tree.get_by_role("treeitem", name="Atlas Distribution Ltd", exact=True)).to_be_visible()
        # The root alone is generated before data arrives; require rendered child nodes.
        expect(tree.get_by_role("group").get_by_role("treeitem")).not_to_have_count(0)
        state = "tree children rendered"
    elif label == "Stock Ledger":
        report = page.locator('[id="page-query-report"]')
        empty = report.get_by_text("Nothing to show", exact=True).filter(visible=True)
        # Frappe DataTable has no dependable semantic row role; isolate its body rows.
        rows = report.locator(".report-wrapper .dt-scrollable .dt-row").filter(visible=True)
        expect(empty.or_(rows), "Report must render rows or a completed empty state").not_to_have_count(0)
        expect(report.get_by_text(re.compile(r"^Execution Time:.*sec$"))).to_be_visible()
        state = "report empty" if empty.is_visible() else "report rows rendered"
    else:
        root = page.locator(f'[id="page-List/{label}/List"]')
        empty = root.locator(".no-result").filter(
            has_text=re.compile(rf"No {re.escape(label)} (?:created|found)")
        ).filter(visible=True)
        # Only document rows, not the list header, qualify as populated results.
        rows = root.locator(".result .list-row-container").filter(
            has=page.get_by_role("link")
        ).filter(visible=True)
        expect(empty.or_(rows), "List must render documents or its explicit empty state").not_to_have_count(0)
        state = "list empty" if empty.is_visible() else "list rows rendered"
    assert_no_ui_error(page)
    return state


def open_workspace(page: Page, base_url: str, workspace: str) -> None:
    page.get_by_role("button", name=workspace, exact=True).click()
    expect(page).to_have_url(f"{base_url}/desk/{workspace.lower()}")
    expect(
        page.get_by_role("navigation", name="Breadcrumb").get_by_text(
            workspace, exact=True
        )
    ).to_be_visible()
    assert_no_ui_error(page)


def assert_destination(
    page: Page, base_url: str, workspace: str, label: str, route: str, title: str,
    validated_loads: dict[str, Response],
) -> None:
    open_workspace(page, base_url, workspace)
    # Onboarding help can share a name with navigation; only follow desk links.
    link = page.get_by_role("link", name=label, exact=True).and_(
        page.locator('a[href^="/desk/"]')
    )
    expect(link).to_be_visible()
    endpoint = TREE_LOAD if label == "Warehouse" else REPORT_LOAD if label == "Stock Ledger" else LIST_LOAD
    # ERPNext reuses an already-loaded DocType list across workspace routes.
    # Cache evidence belongs only to this test/context, never to another run.
    cached = label in validated_loads and endpoint == LIST_LOAD
    if cached:
        link.click()
        assert_load_response(validated_loads[label], label)
    else:
        with page.expect_response(
            lambda response: urlsplit(response.url).path == endpoint
            and response.url.startswith(base_url + "/api/")
        ) as loading:
            link.click()
        assert_load_response(loading.value, label)
        validated_loads[label] = loading.value
    expect(page).to_have_url(
        re.compile(r"^" + re.escape(base_url + route) + r"(?:[?#].*)?$")
    )
    expect(
        page.get_by_role("navigation", name="Breadcrumb").get_by_text(
            title, exact=True
        )
    ).to_be_visible()
    if label == "Stock Ledger":
        expect(page.get_by_role("combobox", name="Company", exact=True)).to_have_value(
            "Atlas Distribution Ltd"
        )
        expect(page.get_by_role("textbox", name="From Date", exact=True)).to_be_visible()
        expect(page.get_by_role("textbox", name="To Date", exact=True)).to_be_visible()
    else:
        expect(page.get_by_role("button", name=f"Add {label}", exact=True)).to_be_visible()
    state = assert_loaded(page, label)
    source = "validated context cache" if cached else "successful loading response"
    print(f"Verified {workspace} -> {label}: {urlsplit(page.url).path}; {state}; {source}")


@contextmanager
def monitor_form_loading(page: Page, base_url: str) -> Iterator[list[str]]:
    """Collect only sanitized API errors while inspecting an unsaved form."""
    loading_errors: list[str] = []

    def check_form_response(response: Response) -> None:
        if not response.url.startswith(base_url + "/api/"):
            return
        if not response.ok:
            loading_errors.append(f"Form request failed: HTTP {response.status}")
            return
        try:
            payload = response.json()
        except ValueError:
            loading_errors.append("Form request returned invalid JSON")
            return
        if isinstance(payload, dict) and any(
            payload.get(key) for key in ("exc", "exc_type", "exception", "error")
        ):
            loading_errors.append("Form request returned an application error")

    page.on("response", check_form_response)
    try:
        yield loading_errors
    finally:
        page.remove_listener("response", check_form_response)

"""QA-001 / REQ-01 / R-06: procurement and inventory navigation, without data writes."""

from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Page, Response

from config.settings import Settings
from pages.navigation import (
    LIST_LOAD,
    REPORT_LOAD,
    TREE_LOAD,
    assert_destination,
    assert_load_response,
)


@pytest.mark.smoke
def test_qa001_navigate_procurement_and_inventory_workspaces(
    authenticated_page: Page, settings: Settings
) -> None:
    page = authenticated_page
    validated_loads: dict[str, Response] = {}
    loading_errors: list[str] = []

    def watch_loading_errors(response: Response) -> None:
        if urlsplit(response.url).path in {LIST_LOAD, TREE_LOAD, REPORT_LOAD}:
            try:
                assert_load_response(response, "Navigation")
            except (AssertionError, ValueError):
                # Keep only a fixed diagnostic; no response/request bodies in logs.
                loading_errors.append("A navigation loading response reported an error")

    page.on("response", watch_loading_errors)
    for label, route in (
        ("Supplier", "supplier"),
        ("Purchase Order", "purchase-order"),
        ("Purchase Receipt", "purchase-receipt"),
    ):
        assert_destination(
            page, settings.base_url, "Buying", label, f"/desk/buying/{route}", label,
            validated_loads,
        )
        assert not loading_errors, "; ".join(loading_errors)

    for label, route, title in (
        ("Item", "item", "Item"),
        ("Warehouse", "warehouse", "Warehouse Tree"),
        ("Purchase Receipt", "purchase-receipt", "Purchase Receipt"),
        ("Stock Ledger", "query-report/Stock%20Ledger", "Stock Ledger"),
    ):
        assert_destination(
            page, settings.base_url, "Stock", label, f"/desk/stock/{route}", title,
            validated_loads,
        )
        assert not loading_errors, "; ".join(loading_errors)
    page.remove_listener("response", watch_loading_errors)

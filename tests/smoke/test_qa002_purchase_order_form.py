"""QA-002 / REQ-02 / R-01: inspect an unsaved PO; never enter or persist data."""

import re
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Page, expect

from config.settings import Settings
from pages.navigation import (
    assert_destination, assert_loaded, assert_no_ui_error, monitor_form_loading,
)


@pytest.mark.smoke
def test_qa002_inspect_purchase_order_form_contract(
    authenticated_page: Page, settings: Settings
) -> None:
    page = authenticated_page
    assert_destination(
        page, settings.base_url, "Buying", "Purchase Order",
        "/desk/buying/purchase-order", "Purchase Order", {},
    )

    with monitor_form_loading(page, settings.base_url) as loading_errors:
        page.get_by_role("button", name="Add Purchase Order", exact=True).click()
        expect(page, "Form loading: expected a new, local Purchase Order route").to_have_url(
            re.compile(
                r"^" + re.escape(settings.base_url)
                + r"/desk/buying/purchase-order/new-purchase-order-[^/?#]+(?:[?#].*)?$"
            )
        )
        form = page.locator('[id="page-Purchase Order"]')
        details = form.get_by_role("tabpanel", name="Details", exact=True)

        # Readiness is separate from the contract. Poll Frappe's pending AJAX count
        # under the existing action timeout; never await an unbounded JS promise.
        expect(form, "Form loading: form container did not render").to_be_visible()
        expect(details, "Form loading: Details panel did not render").to_be_visible()
        page.wait_for_function("() => window.frappe?.request?.ajax_count === 0")
        assert not loading_errors, "Form loading failed: " + "; ".join(loading_errors)
        assert_no_ui_error(page)

        expect(form.get_by_text("Not Saved", exact=True), "Contract: initial state").to_be_visible()
        expect(form.get_by_role("button", name="Save", exact=True)).to_be_visible()
        for name in ("Details", "Address & Contact", "Terms", "More Info"):
            expect(form.get_by_role("tab", name=name, exact=True), f"Contract: missing tab {name}").to_be_visible()

        # These labels are not associated with controls via HTML for/aria-required.
        # Stable DocType field names scope the observed visual reqd markers.
        for fieldname, label, role in (
            ("naming_series", "Series", "combobox"),
            ("supplier", "Supplier", "combobox"),
            ("transaction_date", "Date", "textbox"),
        ):
            field = details.locator(f'.frappe-control[data-fieldname="{fieldname}"]')
            marker = field.locator("label.control-label")
            expect(marker, f"Contract: field label {label} is not visible").to_be_visible()
            expect(marker, f"Contract: missing field {label}").to_have_text(label)
            expect(marker, f"Contract: missing required marker for {label}").to_have_class(re.compile(r"\breqd\b"))
            expect(field.get_by_role(role), f"Contract: missing control {label}").to_be_visible()

        items = details.locator('.frappe-control[data-fieldname="items"]')
        headings = items.locator(".grid-heading-row")
        expect(headings, "Contract: item grid headings did not render").to_be_visible()
        for fieldname, label in (
            ("item_code", "Item Code"),
            ("schedule_date", "Required By"),
            ("qty", "Quantity"),
            ("uom", "UOM"),
        ):
            column = headings.locator(f'[data-fieldname="{fieldname}"] .static-area')
            expect(column, f"Contract: item column {label} is not visible").to_be_visible()
            expect(column, f"Contract: missing item column {label}").to_have_text(label)
            expect(column, f"Contract: missing required marker for item {label}").to_have_class(re.compile(r"\breqd\b"))

        warehouse = details.locator('.frappe-control[data-fieldname="set_warehouse"]')
        expect(warehouse.locator("label.control-label")).to_have_text("Set Target Warehouse")
        expect(warehouse.get_by_role("combobox")).to_be_visible()
        for fieldname, label in (("rate", "Rate"), ("amount", "Amount")):
            expect(headings.locator(f'[data-fieldname="{fieldname}"] .static-area')).to_have_text(
                re.compile(rf"^{label} \([^)]+\)$")
            )
        for fieldname, label in (("total", "Total"), ("grand_total", "Grand Total")):
            total = details.locator(f'.frappe-control[data-fieldname="{fieldname}"]')
            expect(total.locator("label.control-label")).to_have_text(
                re.compile(rf"^{label} \([^)]+\)$")
            )
            expect(total.locator(".control-value"), f"Contract: {label} value did not render").to_have_text(re.compile(r"\S"))

        assert not loading_errors, "Form loading failed: " + "; ".join(loading_errors)
        assert_no_ui_error(page)
        expect(form.get_by_text("Not Saved", exact=True)).to_be_visible()
        print("Verified PO form: Not Saved; four tabs; required header/item markers; warehouse; rate/amount; totals")

        # Disambiguate the sidebar from the breadcrumb; neither action saves a doc.
        page.get_by_role("link", name="Purchase Order", exact=True).and_(
            page.locator('a[href="/desk/buying/purchase-order"]')
        ).click()
        expect(page).to_have_url(
            re.compile(r"^" + re.escape(settings.base_url + "/desk/buying/purchase-order") + r"(?:[?#].*)?$")
        )
        expect(form).not_to_be_visible()
        assert_loaded(page, "Purchase Order")
        assert not loading_errors, "Loading failed while leaving form: " + "; ".join(loading_errors)
        print(f"Exited without saving: {urlsplit(page.url).path}")

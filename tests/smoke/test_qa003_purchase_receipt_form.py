"""QA-003 / REQ-03 / R-02: inspect the initial PR contract without input or saving."""

import re
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import Page, expect

from config.settings import Settings
from pages.navigation import (
    assert_destination,
    assert_loaded,
    assert_no_ui_error,
    monitor_form_loading,
)


@pytest.mark.smoke
def test_qa003_inspect_purchase_receipt_form_contract(
    authenticated_page: Page, settings: Settings
) -> None:
    page = authenticated_page
    list_url = settings.base_url + "/desk/buying/purchase-receipt"
    assert_destination(
        page, settings.base_url, "Buying", "Purchase Receipt",
        "/desk/buying/purchase-receipt", "Purchase Receipt", {},
    )

    with monitor_form_loading(page, settings.base_url) as loading_errors:
        page.get_by_role("button", name="Add Purchase Receipt", exact=True).click()
        expect(page, "Form loading: expected a local new Purchase Receipt route").to_have_url(
            re.compile(r"^" + re.escape(list_url) + r"/new-purchase-receipt-[^/?#]+(?:[?#].*)?$")
        )
        form = page.locator('[id="page-Purchase Receipt"]')
        details = form.get_by_role("tabpanel", name="Details", exact=True)
        expect(form, "Form loading: form container did not render").to_be_visible()
        expect(details, "Form loading: Details panel did not render").to_be_visible()
        # Same bounded initialization signal used by QA-002; no sleeps or edits.
        page.wait_for_function("() => window.frappe?.request?.ajax_count === 0")
        assert not loading_errors, "Form loading failed: " + "; ".join(loading_errors)
        assert_no_ui_error(page)

        expect(form.get_by_text("Not Saved", exact=True), "Contract: initial state").to_be_visible()
        expect(form.get_by_role("button", name="Save", exact=True)).to_be_visible()
        for name in ("Details", "Address & Contact", "Terms", "More Info"):
            expect(form.get_by_role("tab", name=name, exact=True), f"Contract: missing tab {name}").to_be_visible()

        # Frappe exposes visual reqd classes, not HTML aria-required attributes.
        for fieldname, label in (
            ("naming_series", "Series"),
            ("supplier", "Supplier"),
            ("posting_date", "Date"),
            ("posting_time", "Posting Time"),
        ):
            field = details.locator(f'.frappe-control[data-fieldname="{fieldname}"]')
            marker = field.locator("label.control-label")
            expect(marker, f"Contract: missing visible field {label}").to_be_visible()
            expect(marker).to_have_text(label)
            expect(marker, f"Contract: missing required marker for {label}").to_have_class(re.compile(r"\breqd\b"))
            if fieldname in {"posting_date", "posting_time"}:
                # Initially rendered as read-only values: do not enable editing.
                value = field.locator(".control-value")
                expect(value, f"Contract: {label} value is not visible").to_be_visible()
                expect(value).to_have_text(re.compile(r"\S"))
            else:
                expect(field.get_by_role("combobox")).to_be_visible()

        for fieldname, label, role in (
            ("supplier_delivery_note", "Supplier Delivery Note", "textbox"),
            ("set_warehouse", "Accepted Warehouse", "combobox"),
            ("rejected_warehouse", "Rejected Warehouse", "combobox"),
        ):
            field = details.locator(f'.frappe-control[data-fieldname="{fieldname}"]')
            expect(field.locator("label.control-label")).to_be_visible()
            expect(field.locator("label.control-label")).to_have_text(label)
            expect(field.get_by_role(role), f"Contract: missing control {label}").to_be_visible()

        items = details.locator('.frappe-control[data-fieldname="items"]')
        headings = items.locator(".grid-heading-row")
        expect(headings, "Contract: item grid did not render").to_be_visible()
        item_code = headings.locator('[data-fieldname="item_code"] .static-area')
        expect(item_code).to_be_visible()
        expect(item_code).to_have_text("Item Code")
        expect(item_code, "Contract: Item Code required marker is missing").to_have_class(re.compile(r"\breqd\b"))
        for fieldname, label in (("qty", "Accepted Quantity"), ("rejected_qty", "Rejected Quantity")):
            heading = headings.locator(f'[data-fieldname="{fieldname}"] .static-area')
            expect(heading, f"Contract: missing quantity column {label}").to_be_visible()
            expect(heading).to_have_text(label)
            expect(items.locator(f'.grid-body .grid-static-col[data-fieldname="{fieldname}"]')).to_be_visible()
        rate = headings.locator('[data-fieldname="rate"] .static-area')
        expect(rate).to_be_visible()
        expect(rate).to_have_text(re.compile(r"^Rate \([^)]+\)$"))

        for fieldname, label in (("total", "Total"), ("grand_total", "Grand Total")):
            total = details.locator(f'.frappe-control[data-fieldname="{fieldname}"]')
            expect(total.locator("label.control-label")).to_be_visible()
            expect(total.locator("label.control-label")).to_have_text(re.compile(rf"^{label} \([^)]+\)$"))
            expect(total.locator(".control-value")).to_be_visible()
            expect(total.locator(".control-value")).to_have_text(re.compile(r"\S"))

        for name in ("Edit Posting Date and Time", "Apply Putaway Rule"):
            expect(details.get_by_role("checkbox", name=name, exact=True)).to_be_visible()
        is_return = details.get_by_role("checkbox", name="Is Return", exact=True)
        expect(is_return).to_be_visible()
        expect(is_return, "Contract: Is Return must initially be disabled").to_be_disabled()
        expect(is_return).not_to_be_checked()
        assert not loading_errors, "Form loading failed: " + "; ".join(loading_errors)
        assert_no_ui_error(page)
        expect(form.get_by_text("Not Saved", exact=True)).to_be_visible()
        print("Verified PR form: Not Saved; four tabs; required markers; delivery note; warehouses; quantities; rate/totals; posting/putaway options; Is Return disabled and unchecked")

        page.get_by_role("link", name="Purchase Receipt", exact=True).and_(
            page.locator('a[href="/desk/buying/purchase-receipt"]')
        ).click()
        expect(page).to_have_url(re.compile(r"^" + re.escape(list_url) + r"(?:[?#].*)?$"))
        expect(form).not_to_be_visible()
        assert_loaded(page, "Purchase Receipt")
        assert not loading_errors, "Loading failed while leaving form: " + "; ".join(loading_errors)
        print(f"Exited without saving: {urlsplit(page.url).path}")

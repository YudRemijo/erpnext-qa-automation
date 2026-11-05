"""NEG-004: one new PO; reject 11 against 10, retaining any legitimate PR Draft."""

import pytest
from playwright.sync_api import expect

from pages.negative_validation import observe_rejection
from pages.procurement import ProcurementDocument
from pages.purchase_order import create_verified_draft


@pytest.mark.negative
@pytest.mark.transactional
def test_neg004_over_receipt_is_rejected(
    authenticated_page, settings, record_property, transaction_evidence, negative_baseline,
):
    page = authenticated_page
    reader = negative_baseline
    run_id, record = transaction_evidence
    stock_settings = reader.get("Stock Settings", "Stock Settings")
    item = reader.get("Item", "QA-ADL-TEST-001")
    allowance = item.get("over_delivery_receipt_allowance") or stock_settings.get("over_delivery_receipt_allowance") or 0
    bypass_role = stock_settings.get("role_allowed_to_over_deliver_receive")
    record("policy", {"global_allowance": stock_settings.get("over_delivery_receipt_allowance"),
                      "item_allowance": item.get("over_delivery_receipt_allowance"),
                      "effective_allowance_percent": allowance, "bypass_role": bypass_role})
    if allowance >= 9.99 or bypass_role:
        pytest.skip("11 vs 10 is not a reliable rejection oracle under current allowance/role; no setup created")

    def saved(dt, name):
        record("persisted", {"doctype": dt, "name": name})

    po = create_verified_draft(page, settings, record_property, run_id=run_id, on_saved=saved)
    order_page = ProcurementDocument(page, settings.base_url, reader, "Purchase Order")
    po = order_page.submit_once(po["name"])
    record("po_submitted", {"name": po["name"], "docstatus": po["docstatus"], "status": po["status"]})
    receipt = order_page.create_receipt(10)
    receipt.accepted_quantity(11)
    data = receipt.data()
    assert data["items"][0]["qty"] == data["items"][0]["received_qty"] == data["items"][0]["stock_qty"] == 11
    assert data["items"][0]["purchase_order"] == po["name"]
    assert data["items"][0]["purchase_order_item"] == po["items"][0]["name"]
    assert data["items"][0]["rejected_qty"] == 0
    receipt.visible_totals(11)
    # Installed on_submit validates overflow before posting stock. Draft acceptance
    # is legitimate and deliberately retained, not treated as a failed negative.
    name = receipt.save_once()
    saved("Purchase Receipt", name)
    draft = reader.get("Purchase Receipt", name)
    assert draft["docstatus"] == 0 and draft["items"][0]["qty"] == 11
    record("over_receipt_draft", {"name": name, "docstatus": draft["docstatus"], "accepted": 11,
                                  "net_total": draft["net_total"], "tax": draft["total_taxes_and_charges"],
                                  "grand_total": draft["grand_total"]})
    receipt.reopen(name, draft["status"])

    def confirm_submit():
        receipt.form.get_by_role("button", name="Submit", exact=True).click()
        dialog = page.locator(".modal.show")
        expect(dialog).to_contain_text(f"Permanently Submit {name}?")
        dialog.get_by_role("button", name="Yes", exact=True).click()

    try:
        rejection = observe_rejection(page, confirm_submit, r"over limit|Limit Crossed")
    finally:
        actual = reader.get("Purchase Receipt", name)
        updated_po = reader.get("Purchase Order", po["name"])
        moves = reader.list("Stock Ledger Entry", {"voucher_no": name}, ["name", "actual_qty"])
        record("submit_api_check", {"pr": name, "docstatus": actual["docstatus"], "status": actual["status"],
                                    "po_received": updated_po["items"][0]["received_qty"],
                                    "po_per_received": updated_po["per_received"], "voucher_ledger": moves})
        assert actual["docstatus"] == 0, "Unexpected over-receipt submission; stop, do not cancel or retry"
        assert updated_po["items"][0]["received_qty"] == updated_po["per_received"] == 0
        assert not moves, "Unexpected stock effect from rejected Submit"
    assert rejection["layer"] == "server"
    assert rejection["responses"][0]["exc_type"] == "OverAllowanceError"
    assert "QA-ADL-TEST-001" in rejection["dialog"]
    record("rejection", rejection)
    record("result", "PASS")

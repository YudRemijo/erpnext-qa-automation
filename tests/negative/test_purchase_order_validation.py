"""NEG-001/002/003: invalid unsaved PO attempts, without claiming server coverage."""

import pytest
from playwright.sync_api import expect

from pages.negative_validation import item_input, observe_rejection
from pages.procurement import ProcurementDocument, local_decimal
from pages.purchase_order import create_verified_draft


@pytest.mark.negative
@pytest.mark.parametrize("case, field, invalid, error", [
    ("NEG-001", "supplier", "", r"Supplier"),
    ("NEG-002", "item_code", "", r"Item Code|Items"),
    ("NEG-003", "qty", "0", r"Quantity.*(zero|required)|Missing Fields|Quantity"),
], ids=["NEG-001-missing-supplier", "NEG-002-missing-item", "NEG-003-zero-quantity"])
def test_purchase_order_rejects_invalid_data(
    authenticated_page, settings, record_property, transaction_evidence, negative_baseline,
    case, field, invalid, error,
):
    page = authenticated_page
    reader = negative_baseline
    _, record = transaction_evidence
    if case == "NEG-003":
        assert not reader.get("Buying Settings", "Buying Settings")["allow_zero_qty_in_purchase_order"], "Zero quantity policy changed; review oracle"
    before = reader.list("Purchase Order", {}, ["name"])
    create_verified_draft(page, settings, record_property, persist=False)
    document = ProcurementDocument(page, settings.base_url, reader, "Purchase Order")
    if field == "supplier":
        control = document.form.locator('.frappe-control[data-fieldname="supplier"]').get_by_role("combobox")
    else:
        control = item_input(document, field)
    control.fill(invalid)
    control.press("Tab")
    document.ready()
    if field == "qty":
        assert local_decimal(control.input_value()) == 0
        assert document.data()["items"][0]["qty"] == 0
    elif field == "supplier":
        expect(control).to_have_value("")
        assert not document.data().get("supplier")
    else:
        assert not document.data()["items"][0].get("item_code")
    record("invalid_input", {"case": case, "field": field, "value": invalid})
    try:
        outcome = observe_rejection(page, lambda: document.form.get_by_role("button", name="Save", exact=True).click(), error)
    finally:
        after = reader.list("Purchase Order", {}, ["name", "docstatus", "status"])
        new = [d for d in after if d["name"] not in {r["name"] for r in before}]
        record("save_api_check", {"new_documents": new})
        assert not new, "Invalid Save persisted a PO; stop, do not clean up or repeat"
    record("rejection", outcome)
    assert document.data().get("__islocal"), "Rejected document must remain unsaved"
    # Missing fields must be explicit; a generic modal alone is not an oracle.
    if case in ("NEG-001", "NEG-002"):
        assert outcome["layer"] == "client", "Validation stage changed; inspect before claiming backend coverage"
        assert "Missing Fields" in outcome["dialog"]
    else:
        assert outcome["layer"] == "server", "Zero quantity must exercise the observed backend rule"
        assert outcome["responses"][0]["http_status"] == 417
        assert outcome["responses"][0]["exc_type"] == "InvalidQtyError"
        assert "cannot be zero" in outcome["dialog"]
    record("result", "PASS")

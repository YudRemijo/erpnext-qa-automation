"""QA-011: one independent UI lifecycle, reconciled using read-only REST queries."""

from decimal import Decimal

import pytest

from pages.procurement import ProcurementDocument, ReadAPI
from pages.purchase_order import create_verified_draft


COMPANY = "Atlas Distribution Ltd"
ITEM = "QA-ADL-TEST-001"
WAREHOUSE = "Stores - ADL"
SUPPLIER = "QA Atlas Test Supplier"


@pytest.mark.transactional
def test_qa011_partial_receipts_complete_purchase_order(
    authenticated_page, settings, record_property, transaction_evidence,
):
    page = authenticated_page
    run_id, record = transaction_evidence
    assert settings.base_url == "http://localhost:8080"
    reader = ReadAPI(page.context.request, settings.base_url)

    def balance():
        rows = reader.list("Bin", {"item_code": ITEM, "warehouse": WAREHOUSE},
                           ["name", "actual_qty", "stock_value", "ordered_qty"])
        assert len(rows) <= 1, "Ambiguous Bin for item/warehouse"
        return rows[0]["actual_qty"] if rows else 0

    def ledger():
        return reader.list("Stock Ledger Entry", {"item_code": ITEM, "warehouse": WAREHOUSE},
                           ["name", "company", "item_code", "warehouse", "stock_uom", "voucher_type",
                            "voucher_no", "voucher_detail_no", "actual_qty", "qty_after_transaction", "is_cancelled"])

    def invoices():
        return reader.list("Purchase Invoice", {}, ["name", "docstatus"])

    def summary(doc):
        return {**{k: doc.get(k) for k in ["name", "docstatus", "status", "net_total",
                                           "total_taxes_and_charges", "grand_total", "per_received"]},
                "items": [{k: i.get(k) for k in ["name", "item_code", "qty", "received_qty",
                                                  "rejected_qty", "stock_qty", "warehouse",
                                                  "purchase_order", "purchase_order_item"]}
                          for i in doc["items"]]}

    protected_ids = [("Purchase Order", "PUR-ORD-2026-00001"),
                     ("Purchase Order", "PUR-ORD-2026-00002"),
                     ("Purchase Receipt", "MAT-PRE-2026-00001"),
                     ("Purchase Receipt", "MAT-PRE-2026-00002")]
    protected = {(dt, name): reader.get(dt, name) for dt, name in protected_ids}
    initial_balance, initial_ledger, initial_invoices = balance(), ledger(), invoices()
    all_pr_before = reader.list("Purchase Receipt", {}, ["name"])
    record("baseline", {"physical_balance": initial_balance, "ledger": initial_ledger,
                        "invoices": initial_invoices, "protected_documents": [n for _, n in protected_ids]})

    def on_saved(doctype, name):
        record("persisted", {"doctype": doctype, "name": name})

    po = create_verified_draft(page, settings, record_property, run_id=run_id, on_saved=on_saved)
    po_name, po_line = po["name"], po["items"][0]["name"]
    assert all(po_name != name for _, name in protected_ids)
    assert balance() == initial_balance and ledger() == initial_ledger
    record("po_draft", summary(po))
    order_page = ProcurementDocument(page, settings.base_url, reader, "Purchase Order")
    po = order_page.submit_once(po_name)
    assert po["docstatus"] == 1 and po["per_received"] == 0
    assert po["items"][0]["qty"] == 10 and po["items"][0]["received_qty"] == 0
    assert balance() == initial_balance and ledger() == initial_ledger
    record("po_submitted", summary(po))

    def verify_receipt(doc, quantity, docstatus):
        expected = {"company": COMPANY, "supplier": SUPPLIER, "currency": "USD",
                    "conversion_rate": 1, "docstatus": docstatus, "is_return": 0,
                    "set_warehouse": WAREHOUSE, "taxes_and_charges": "Brazil ICMS 19% - ADL",
                    "total_qty": quantity, "net_total": quantity * 100,
                    "total_taxes_and_charges": quantity * 19, "grand_total": quantity * 119}
        for key, value in expected.items():
            assert doc[key] == value, f"PR {key}"
        assert len(doc["items"]) == 1
        item = doc["items"][0]
        for key, value in {"item_code": ITEM, "qty": quantity, "received_qty": quantity,
                           "rejected_qty": 0, "stock_qty": quantity, "rate": 100,
                           "uom": "Nos", "stock_uom": "Nos", "conversion_factor": 1,
                           "warehouse": WAREHOUSE, "purchase_order": po_name,
                           "purchase_order_item": po_line}.items():
            assert item[key] == value, f"PR item {key}"
        assert len(doc["taxes"]) == 1
        tax = doc["taxes"][0]
        assert tax["charge_type"] == "On Net Total" and tax["account_head"] == "ICMS 19% - ADL"
        assert tax["rate"] == 19 and tax["tax_amount"] == quantity * 19

    receipts = []
    cumulative = 0
    for quantity, suggested in ((4, 10), (6, 6)):
        record("begin_receipt", {"accepted_quantity": quantity, "expected_suggestion": suggested})
        order_page.reopen(po_name, po["status"])
        receipt_page = order_page.create_receipt(suggested)
        mapped = receipt_page.data()
        record("mapped_receipt", summary(mapped))
        assert mapped["company"] == COMPANY and mapped["supplier"] == SUPPLIER
        assert mapped["items"][0]["purchase_order"] == po_name
        assert mapped["items"][0]["purchase_order_item"] == po_line
        assert mapped["items"][0]["rejected_qty"] == 0
        receipt_page.accepted_quantity(quantity)
        receipt_page.visible_totals(quantity)
        verify_receipt(receipt_page.data(), quantity, 0)
        before_draft_ledger, before_draft_balance = ledger(), balance()
        name = receipt_page.save_once()
        on_saved("Purchase Receipt", name)
        draft = reader.get("Purchase Receipt", name)
        verify_receipt(draft, quantity, 0)
        verify_receipt(receipt_page.reopen(name, draft["status"]), quantity, 0)
        assert balance() == before_draft_balance and ledger() == before_draft_ledger
        unchanged_po = reader.get("Purchase Order", po_name)
        assert unchanged_po["items"][0]["received_qty"] == cumulative
        assert unchanged_po["per_received"] == cumulative * 10
        record("receipt_draft", summary(draft))

        submitted = receipt_page.submit_once(name)
        verify_receipt(submitted, quantity, 1)
        verify_receipt(receipt_page.data(), quantity, 1)
        receipts.append(submitted)
        cumulative += quantity
        # Bound polling by the configured UI timeout. It only issues GETs and waits
        # for a persisted business condition; it is not a fixed sleep or a retry.
        page.wait_for_function(
            """async ({po, item, warehouse, received, expectedBalance}) => {
                const read = async path => {
                    const r = await fetch('/api/resource/' + path);
                    if (!r.ok) throw new Error('Read-only reconciliation request failed');
                    return (await r.json()).data;
                };
                const order = await read('Purchase%20Order/' + encodeURIComponent(po));
                const filters = encodeURIComponent(JSON.stringify({item_code:item,warehouse}));
                const bins = await read('Bin?filters=' + filters + '&fields=%5B%22actual_qty%22%5D');
                return order.per_received === received * 10 &&
                       order.items[0].received_qty === received &&
                       bins.length === 1 && bins[0].actual_qty === expectedBalance;
            }""",
            arg={"po": po_name, "item": ITEM, "warehouse": WAREHOUSE, "received": cumulative,
                 "expectedBalance": initial_balance + cumulative},
            polling=250,
        )
        po = reader.get("Purchase Order", po_name)
        assert po["docstatus"] == 1 and po["per_received"] == cumulative * 10
        assert po["items"][0]["qty"] == 10 and po["items"][0]["received_qty"] == cumulative
        assert po["items"][0]["qty"] - po["items"][0]["received_qty"] == 10 - cumulative
        assert balance() == initial_balance + cumulative
        moves = [r for r in ledger() if r["voucher_no"] == name]
        assert moves and sum(r["actual_qty"] for r in moves) == quantity
        for move in moves:
            assert move["company"] == COMPANY and move["item_code"] == ITEM
            assert move["warehouse"] == WAREHOUSE and move["stock_uom"] == "Nos"
            assert move["voucher_type"] == "Purchase Receipt" and not move["is_cancelled"]
            assert move["voucher_detail_no"] == submitted["items"][0]["name"]
        assert invoices() == initial_invoices
        record("receipt_submitted", {"document": summary(submitted), "po": summary(po),
                                     "physical_balance": balance(), "ledger": moves})

    order_page.reopen(po_name, po["status"])
    ui_po = order_page.data()
    assert ui_po["docstatus"] == 1 and ui_po["per_received"] == 100
    assert ui_po["items"][0]["received_qty"] == 10
    assert po["net_total"] == 1000 and po["total_taxes_and_charges"] == 190 and po["grand_total"] == 1190
    final_ledger = ledger()
    old_names = {r["name"] for r in initial_ledger}
    new_moves = [r for r in final_ledger if r["name"] not in old_names]
    expected_vouchers = {r["name"] for r in receipts}
    assert all(r["voucher_no"] in expected_vouchers for r in new_moves), "Unexpected concurrent stock movement"
    assert len({r["name"] for r in final_ledger}) == len(final_ledger)
    assert [r for r in final_ledger if r["name"] in old_names] == initial_ledger
    assert sum(r["actual_qty"] for r in new_moves) == 10
    assert balance() == initial_balance + 10
    assert invoices() == initial_invoices
    all_pr_after = reader.list("Purchase Receipt", {}, ["name"])
    assert {r["name"] for r in all_pr_after} - {r["name"] for r in all_pr_before} == expected_vouchers
    for (doctype, name), original in protected.items():
        assert reader.get(doctype, name) == original, f"Protected document changed: {name}"
    for receipt, quantity in zip(receipts, (4, 6)):
        verify_receipt(reader.get("Purchase Receipt", receipt["name"]), quantity, 1)
    gl = reader.list("GL Entry", {"voucher_type": "Purchase Receipt", "voucher_no": receipts[1]["name"]},
                     ["name", "company", "account", "debit", "credit", "account_currency", "is_cancelled"])
    assert gl and all(r["company"] == COMPANY and not r["is_cancelled"] for r in gl)
    debits = sum(Decimal(str(r["debit"])) for r in gl)
    credits = sum(Decimal(str(r["credit"])) for r in gl)
    assert debits == credits, "Second receipt GL is not balanced"
    record("final_reconciliation", {"po": summary(po), "initial_balance": initial_balance,
                                    "final_balance": balance(), "new_ledger": new_moves,
                                    "gl_second_receipt": gl, "gl_debits": str(debits),
                                    "gl_credits": str(credits), "protected_documents_unchanged": True,
                                    "invoices_unchanged": True})
    record("result", "PASS")

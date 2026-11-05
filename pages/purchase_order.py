"""Shared, verified PO Draft creation extracted from the approved QA-008."""

import re
from datetime import date, timedelta
from decimal import Decimal
from urllib.parse import quote
from uuid import uuid4

from playwright.sync_api import Page, expect

from config.settings import Settings
from pages.navigation import assert_destination, assert_no_ui_error
from pages.procurement import ReadAPI, ProcurementDocument


def create_verified_draft(
    page: Page, settings: Settings, record_property, *, run_id=None, on_saved=None, persist=True,
) -> dict:
    assert settings.base_url == "http://localhost:8080", "Writes limited to approved local ERPNext"
    run_id = run_id or str(uuid4())
    record_property("qa_run_id", run_id)

    reader = ReadAPI(page.context.request, settings.base_url)
    get_resource = reader.get
    list_rows = reader.list

    company = "Atlas Distribution Ltd"
    supplier = "QA Atlas Test Supplier"
    item_code = "QA-ADL-TEST-001"
    warehouse = "Stores - ADL"
    assert get_resource("Company", company)["default_currency"] == "USD"
    supplier_doc = get_resource("Supplier", supplier)
    assert not any(supplier_doc.get(k) for k in ("disabled", "on_hold", "is_frozen"))
    item_doc = get_resource("Item", item_code)
    assert item_doc["is_stock_item"] == item_doc["is_purchase_item"] == 1
    assert not item_doc["disabled"] and item_doc["stock_uom"] == "Nos"
    warehouse_doc = get_resource("Warehouse", warehouse)
    assert warehouse_doc["company"] == company
    assert not warehouse_doc["disabled"] and not warehouse_doc["is_group"]

    item_filter = {"item_code": item_code}
    ledger_fields = ["name", "voucher_type", "voucher_no", "actual_qty", "warehouse"]
    ledger_before = list_rows("Stock Ledger Entry", item_filter, ledger_fields)
    bins_before = list_rows("Bin", {**item_filter, "warehouse": warehouse},
                            ["name", "actual_qty", "stock_value", "ordered_qty"])
    orders_before = {r["name"] for r in list_rows("Purchase Order", {"supplier": supplier}, ["name"])}

    assert_destination(page, settings.base_url, "Buying", "Purchase Order",
                       "/desk/buying/purchase-order", "Purchase Order", {})
    page.get_by_role("button", name="Add Purchase Order", exact=True).click()
    form = page.locator('[id="page-Purchase Order"]')
    expect(form).to_be_visible()

    def ready():
        page.wait_for_function("() => window.frappe?.request?.ajax_count === 0")
        assert_no_ui_error(page)

    def field(name):
        return form.locator(f'.frappe-control[data-fieldname="{name}"] input').filter(visible=True)

    def fill(name, value):
        field(name).fill(value)
        field(name).press("Tab")
        ready()
        expect(field(name)).to_have_value(value)

    def ui_doc():
        # Read-only access supplements visible assertions for hidden derived fields.
        return page.evaluate("() => JSON.parse(JSON.stringify(cur_frm.doc))")

    ready()
    assert ui_doc()["company"] == company, "Unexpected default company; stop before Save"
    due = date.fromisoformat(ui_doc()["transaction_date"]) + timedelta(days=14)
    assert due > date.today()
    fill("supplier", supplier)
    fill("schedule_date", due.strftime("%d/%m/%Y"))
    fill("set_warehouse", warehouse)
    row = form.locator('.frappe-control[data-fieldname="items"] .grid-row[data-idx="1"]')
    # This is the explicit ERPNext row identity of the only new item, not nth().
    if not row.locator('input[data-fieldname="item_code"]').is_visible():
        row.locator('.grid-static-col[data-fieldname="item_code"]').click()
    code = row.get_by_role("combobox", name="Item Code", exact=True)
    expect(code).to_be_visible()
    code.fill(item_code)
    code.press("Tab")
    ready()
    expect(code).to_have_value(item_code)
    for name, value in (("qty", "10"), ("rate", "100")):
        control = row.locator(f'input[data-fieldname="{name}"]')
        if not control.is_visible():
            row.locator(f'.grid-static-col[data-fieldname="{name}"]').click()
        control.fill(value)
        control.press("Tab")
        ready()
        assert Decimal(control.input_value().replace(".", "").replace(",", ".")) == Decimal(value)

    if on_saved is not None:
        form.get_by_role("tab", name="More Info", exact=True).click()
        title = field("title")
        if not title.is_visible():
            form.get_by_text("Additional Info", exact=True).click()
        title.fill(f"QA-E2E-{run_id}")
        title.press("Tab")
        ready()
        form.get_by_role("tab", name="Details", exact=True).click()

    draft = ui_doc()
    template = get_resource("Purchase Taxes and Charges Template", draft["taxes_and_charges"])
    # Only the observed, approved single On Net Total ICMS configuration is supported.
    assert template["company"] == company and not template["disabled"]
    assert len(template["taxes"]) == len(draft["taxes"]) == 1
    tax = template["taxes"][0]
    assert tax["charge_type"] == "On Net Total"
    assert tax["account_head"] == "ICMS 19% - ADL" and Decimal(str(tax["rate"])) == Decimal("19")
    net = Decimal("10") * Decimal("100")
    tax_total = (net * Decimal(str(tax["rate"])) / 100).quantize(Decimal("0.01"))
    expected = {"company": company, "supplier": supplier, "currency": "USD",
                "conversion_rate": 1, "set_warehouse": warehouse, "schedule_date": due.isoformat(),
                "total_qty": 10, "total": net, "net_total": net,
                "total_taxes_and_charges": tax_total, "grand_total": net + tax_total,
                "docstatus": 0, "status": "Draft"}
    expected_item = {"item_code": item_code, "qty": 10, "uom": "Nos", "stock_uom": "Nos",
                     "rate": 100, "amount": net, "warehouse": warehouse,
                     "schedule_date": due.isoformat(), "received_qty": 0, "billed_amt": 0}

    def verify(document):
        for key, value in expected.items():
            assert document[key] == value, key
        assert len(document["items"]) == 1
        for key, value in expected_item.items():
            assert document["items"][0][key] == value, f"Item {key}"
        assert document["taxes_and_charges"] == template["name"]
        actual_tax = document["taxes"][0]
        for key in ("charge_type", "account_head", "rate"):
            assert actual_tax[key] == tax[key], f"Tax {key}"
        assert Decimal(str(actual_tax["tax_amount"])) == tax_total

    verify(draft)
    expect(form.get_by_text("Not Saved", exact=True)).to_be_visible()
    for name, amount in (("total", net), ("total_taxes_and_charges", tax_total),
                         ("grand_total", net + tax_total)):
        displayed = form.locator(f'.frappe-control[data-fieldname="{name}"] .control-value')
        expect(displayed).to_be_visible()
        # This local site renders currency with dot thousands and comma decimals.
        text = displayed.inner_text().replace("$", "").replace("\xa0", "").strip()
        assert Decimal(text.replace(".", "").replace(",", ".")) == amount

    if not persist:
        return draft

    name = ProcurementDocument(page, settings.base_url, reader, "Purchase Order").save_once()
    if on_saved is not None:
        on_saved("Purchase Order", name)

    print(f"QA-008 run={run_id}; created Draft={name}; required_by={due}; retained for audit")
    record_property("purchase_order", name)
    assert name not in orders_before
    ready()
    expect(form.get_by_text("Not Saved", exact=True)).not_to_be_visible()
    persisted = get_resource("Purchase Order", name)
    verify(persisted)
    if on_saved is not None:
        assert persisted["title"] == f"QA-E2E-{run_id}"
    page.goto(f"{settings.base_url}/desk/buying/purchase-order")
    expect(page.locator('[id="page-List/Purchase Order/List"]')).to_be_visible()
    route = f"{settings.base_url}/desk/buying/purchase-order/{quote(name, safe='')}"
    page.goto(route)
    expect(page).to_have_url(re.compile("^" + re.escape(route) + "$"))
    expect(form).to_be_visible()
    ready()
    expect(form.get_by_test_id("page-status")).to_have_text("Draft")
    expect(field("supplier")).to_have_value(supplier)
    expect(field("set_warehouse")).to_have_value(warehouse)
    reopened = ui_doc()
    assert reopened["name"] == name
    verify(reopened)
    assert reopened["items"][0]["name"] == persisted["items"][0]["name"]
    assert list_rows("Stock Ledger Entry", item_filter, ledger_fields) == ledger_before
    assert list_rows("Bin", {**item_filter, "warehouse": warehouse},
                     ["name", "actual_qty", "stock_value", "ordered_qty"]) == bins_before
    assert not list_rows("Stock Ledger Entry", {"voucher_no": name}, ["name"])
    print(f"Verified UI/API: {name}; Draft; net={net}; tax={tax_total}; grand_total={net + tax_total}; stock unchanged")

    return persisted

"""Small UI actions and read-only API access shared by purchasing scenarios."""

import json
from decimal import Decimal
from urllib.parse import quote, urlsplit

import pytest
from playwright.sync_api import Error, expect

from pages.navigation import assert_no_ui_error


def local_decimal(text):
    """Approved local format: 1.000,00 (also quantities such as 6,000)."""
    return Decimal(text.replace("$", "").replace("\xa0", "").strip().replace(".", "").replace(",", "."))


class ReadAPI:
    def __init__(self, request, base_url):
        self.request = request
        self.base_url = base_url

    def get(self, doctype, name):
        response = self.request.get(
            f"{self.base_url}/api/resource/{quote(doctype, safe='')}/{quote(name, safe='')}"
        )
        assert response.ok, f"Infrastructure/API GET {doctype}: HTTP {response.status}"
        payload = response.json()
        assert not payload.get("exc"), f"API GET {doctype}: application error"
        return payload["data"]

    def list(self, doctype, filters, fields):
        result = []
        while True:
            response = self.request.get(
                f"{self.base_url}/api/resource/{quote(doctype, safe='')}",
                params={"filters": json.dumps(filters), "fields": json.dumps(fields),
                        "limit_start": len(result), "limit_page_length": 100,
                        "order_by": "name asc"},
            )
            assert response.ok, f"Infrastructure/API list {doctype}: HTTP {response.status}"
            payload = response.json()
            assert not payload.get("exc"), f"API list {doctype}: application error"
            batch = payload["data"]
            result.extend(batch)
            if len(batch) < 100:
                return result


class ProcurementDocument:
    def __init__(self, page, base_url, reader, doctype):
        self.page, self.base_url, self.reader, self.doctype = page, base_url, reader, doctype
        self.form = page.locator(f'[id="page-{doctype}"]')
        self.route = "purchase-order" if doctype == "Purchase Order" else "purchase-receipt"

    def ready(self):
        expect(self.form).to_be_visible()
        self.page.wait_for_function("() => window.frappe?.request?.ajax_count === 0")
        assert_no_ui_error(self.page)

    def data(self):
        # Inspection only: never mutate Frappe's browser model or call write methods.
        data = self.page.evaluate("() => JSON.parse(JSON.stringify(cur_frm.doc))")
        assert data["doctype"] == self.doctype
        return data

    def reopen(self, name, status):
        # Force a fresh desk load rather than relying on a cached client document.
        self.page.goto(f"{self.base_url}/desk/buying/{self.route}")
        expect(self.page.locator(f'[id="page-List/{self.doctype}/List"]')).to_be_visible()
        url = f"{self.base_url}/desk/buying/{self.route}/{quote(name, safe='')}"
        self.page.goto(url)
        expect(self.page).to_have_url(url)
        self.ready()
        expect(self.form.get_by_test_id("page-status")).to_have_text(status)
        assert self.data()["name"] == name
        return self.data()

    def save_once(self):
        baseline = {r["name"] for r in self.reader.list(self.doctype, {}, ["name"])}
        try:
            with self.page.expect_response(
                lambda r: urlsplit(r.url).path == "/api/method/frappe.desk.form.save.savedocs"
            ) as saving:
                self.form.get_by_role("button", name="Save", exact=True).click()
            response = saving.value
            assert response.ok, f"Save HTTP {response.status}"
            payload = response.json()
            assert not payload.get("exc"), "Save application error"
            docs = [d for d in payload.get("docs", []) if d.get("doctype") == self.doctype]
            assert len(docs) == 1, "Save must identify exactly one persisted document"
            name = docs[0]["name"]
            print(f"Persisted {self.doctype}: {name}", flush=True)
        except (Error, AssertionError, ValueError, KeyError):
            # Query first after any ambiguous Save. Never click again.
            candidates = [r["name"] for r in self.reader.list(self.doctype, {}, ["name"])
                          if r["name"] not in baseline]
            pytest.fail(f"SAVE_UNCERTAIN {self.doctype}; API candidates={candidates}; no retry", pytrace=False)
        return name

    def submit_once(self, name):
        before = self.reader.get(self.doctype, name)
        assert before["docstatus"] == 0, "Submit requires a persisted Draft"
        assert self.data()["name"] == name
        try:
            self.form.get_by_role("button", name="Submit", exact=True).click()
            dialog = self.page.locator(".modal.show")
            expect(dialog).to_be_visible()
            expect(dialog).to_contain_text(f"Permanently Submit {name}?")
            with self.page.expect_response(
                lambda r: urlsplit(r.url).path == "/api/method/frappe.desk.form.save.savedocs"
            ) as submitting:
                dialog.get_by_role("button", name="Yes", exact=True).click()
            response = submitting.value
            assert response.ok, f"Submit HTTP {response.status}"
            assert not response.json().get("exc"), "Submit application error"
            self.ready()
        except (Error, AssertionError, ValueError):
            actual = self.reader.get(self.doctype, name)
            pytest.fail(f"SUBMIT_UNCERTAIN {name}; API docstatus={actual['docstatus']}; "
                        f"status={actual['status']}; no retry", pytrace=False)
        actual = self.reader.get(self.doctype, name)
        assert actual["docstatus"] == 1, "Submit did not persist docstatus=1"
        self.reopen(name, actual["status"])
        return actual

    def create_receipt(self, suggested):
        assert self.doctype == "Purchase Order"
        self.form.get_by_role("button", name="Create", exact=True).click()
        self.page.get_by_role("menuitem", name="Purchase Receipt", exact=True).click()
        receipt = ProcurementDocument(self.page, self.base_url, self.reader, "Purchase Receipt")
        receipt.ready()
        expect(receipt.form.get_by_text("Not Saved", exact=True)).to_be_visible()
        data = receipt.data()
        assert data.get("__islocal") and len(data["items"]) == 1
        assert data["items"][0]["qty"] == suggested, "Unexpected mapped pending quantity"
        return receipt

    def accepted_quantity(self, quantity):
        row = self.form.locator('.frappe-control[data-fieldname="items"] .grid-row[data-idx="1"]')
        control = row.locator('input[data-fieldname="qty"]')
        if not control.is_visible():
            row.locator('.grid-static-col[data-fieldname="qty"]').click()
        data = self.data()["items"][0]
        # Same numeric value does not fire Frappe's qty trigger. Legitimate UI edits
        # only, in the unsaved form; restore the approved final quantity before Save.
        values = [str(quantity)]
        if data["qty"] == quantity and data.get("received_qty") != quantity:
            print(f"Observed stale received_qty={data.get('received_qty')} for accepted={quantity}")
            values.insert(0, str(quantity - 1))
        for value in values:
            control.fill(value)
            control.press("Tab")
            self.ready()
        assert local_decimal(control.input_value()) == quantity

    def visible_totals(self, quantity):
        for field, expected in (("total", quantity * 100),
                                ("total_taxes_and_charges", quantity * 19),
                                ("grand_total", quantity * 119)):
            value = self.form.locator(f'.frappe-control[data-fieldname="{field}"] .control-value')
            expect(value).to_be_visible()
            assert local_decimal(value.inner_text()) == expected, f"Visible {field}"

"""Guard previous purchasing documents and stock around each negative scenario."""

import pytest

from pages.procurement import ReadAPI


@pytest.fixture
def negative_baseline(authenticated_page, settings, transaction_evidence):
    assert settings.base_url == "http://localhost:8080"
    reader = ReadAPI(authenticated_page.context.request, settings.base_url)
    _, record = transaction_evidence
    previous = {}
    for dt in ("Purchase Order", "Purchase Receipt", "Purchase Invoice"):
        for row in reader.list(dt, {}, ["name"]):
            previous[(dt, row["name"])] = reader.get(dt, row["name"])
    ledger = reader.list("Stock Ledger Entry", {"item_code": "QA-ADL-TEST-001"},
                         ["name", "warehouse", "voucher_no", "actual_qty", "is_cancelled"])
    bins = reader.list("Bin", {"item_code": "QA-ADL-TEST-001", "warehouse": "Stores - ADL"},
                       ["name", "actual_qty", "stock_value"])
    record("baseline", {"previous_documents": [list(k) for k in previous], "bin": bins, "ledger": ledger})
    yield reader
    # Always preserve API evidence, even after a failed assertion or ambiguous action.
    ledger_after = reader.list("Stock Ledger Entry", {"item_code": "QA-ADL-TEST-001"},
                               ["name", "warehouse", "voucher_no", "actual_qty", "is_cancelled"])
    bins_after = reader.list("Bin", {"item_code": "QA-ADL-TEST-001", "warehouse": "Stores - ADL"},
                             ["name", "actual_qty", "stock_value"])
    changed = [name for (dt, name), before in previous.items() if reader.get(dt, name) != before]
    new = []
    for dt in ("Purchase Order", "Purchase Receipt", "Purchase Invoice"):
        for row in reader.list(dt, {}, ["name", "docstatus", "status"]):
            if (dt, row["name"]) not in previous:
                new.append({"doctype": dt, **row})
    record("after_api", {"new_documents": new, "changed_prior_documents": changed,
                         "bin": bins_after, "ledger": ledger_after})
    try:
        assert not changed, "A previous purchasing document was modified"
        assert bins_after == bins and ledger_after == ledger, "Unexpected stock effect; inspect before another run"
        assert not any(d["doctype"] == "Purchase Invoice" for d in new)
    except AssertionError:
        record("result", "FAIL")
        raise

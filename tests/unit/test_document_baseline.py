"""Synthetic preservation tests without ERPNext, credentials or browser."""

import pytest

from config.document_baseline import DocumentBaseline

pytestmark = pytest.mark.offline


class Reader:
    def __init__(self):
        self.docs = {}

    def list(self, doctype, filters, fields):
        return [{"name": name} for dt, name in self.docs if dt == doctype]

    def get(self, doctype, name):
        return self.docs[(doctype, name)]

    def add(self, doctype, name):
        self.docs[(doctype, name)] = {"doctype": doctype, "name": name,
                                    "items": [{"qty": 2}], "docstatus": 0}


def created(reader):
    result = {"Purchase Order": ["NEW-ORDER"], "Purchase Receipt": ["NEW-R1", "NEW-R2"]}
    for dt, names in result.items():
        for name in names:
            reader.add(dt, name)
    return result


@pytest.mark.parametrize("existing", [False, True])
def test_empty_or_arbitrary_baseline_allows_only_declared_new_documents(existing):
    reader = Reader()
    if existing:
        reader.add("Purchase Order", "OTHER-ORDER")
        reader.add("Purchase Receipt", "OTHER-RECEIPT")
    baseline = DocumentBaseline.capture(reader)
    baseline.assert_preserved(reader, created(reader))


@pytest.mark.parametrize("mutation", ["nested", "metadata", "deleted", "unexpected"])
def test_detects_preexisting_changes_and_unexpected_inventory(mutation):
    reader = Reader()
    reader.add("Purchase Order", "OLD")
    baseline = DocumentBaseline.capture(reader)
    ids = created(reader)
    if mutation == "nested":
        reader.docs[("Purchase Order", "OLD")]["items"][0]["qty"] = 3
    elif mutation == "metadata":
        reader.docs[("Purchase Order", "OLD")]["modified"] = "changed"
    elif mutation == "deleted":
        del reader.docs[("Purchase Order", "OLD")]
    else:
        reader.add("Purchase Receipt", "UNEXPECTED")
    with pytest.raises(AssertionError):
        baseline.assert_preserved(reader, ids)


@pytest.mark.parametrize("problem", ["duplicate", "reused", "missing_new"])
def test_rejects_duplicate_reused_or_absent_created_ids(problem):
    reader = Reader()
    reader.add("Purchase Order", "OLD")
    baseline = DocumentBaseline.capture(reader)
    ids = created(reader)
    if problem == "duplicate":
        ids["Purchase Receipt"].append("NEW-R1")
    elif problem == "reused":
        ids["Purchase Order"].append("OLD")
    else:
        del reader.docs[("Purchase Receipt", "NEW-R2")]
    with pytest.raises(AssertionError):
        baseline.assert_preserved(reader, ids)


def test_unreadable_document_aborts_baseline():
    class Denied(Reader):
        def get(self, doctype, name):
            raise PermissionError("synthetic read denial")
    reader = Denied()
    reader.add("Purchase Order", "OLD")
    with pytest.raises(PermissionError):
        DocumentBaseline.capture(reader)


def test_inventory_change_during_capture_is_rejected():
    class Concurrent(Reader):
        def get(self, doctype, name):
            self.add("Purchase Receipt", "CONCURRENT")
            return super().get(doctype, name)
    reader = Concurrent()
    reader.add("Purchase Order", "OLD")
    with pytest.raises(AssertionError, match="during baseline"):
        DocumentBaseline.capture(reader)


def test_duplicate_list_results_are_rejected():
    class Duplicate(Reader):
        def list(self, doctype, filters, fields):
            return super().list(doctype, filters, fields) * 2
    reader = Duplicate()
    reader.add("Purchase Order", "OLD")
    with pytest.raises(AssertionError, match="Ambiguous"):
        DocumentBaseline.capture(reader)

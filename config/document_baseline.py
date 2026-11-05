"""Read-only preservation baseline; document contents stay in memory only."""

from copy import deepcopy


class DocumentBaseline:
    DOCTYPES = ("Purchase Order", "Purchase Receipt")

    def __init__(self, documents):
        self.documents = deepcopy(documents)

    @staticmethod
    def names(reader, doctype):
        rows = reader.list(doctype, {}, ["name"])
        names = [row["name"] for row in rows]
        assert len(names) == len(set(names)), f"Ambiguous baseline inventory: {doctype}"
        return set(names)

    @classmethod
    def capture(cls, reader):
        documents = {}
        inventories = {dt: cls.names(reader, dt) for dt in cls.DOCTYPES}
        for dt, names in inventories.items():
            for name in sorted(names):
                doc = reader.get(dt, name)
                assert doc["doctype"] == dt and doc["name"] == name, "Baseline identity mismatch"
                documents[(dt, name)] = deepcopy(doc)
        for dt, names in inventories.items():
            assert cls.names(reader, dt) == names, f"Inventory changed during baseline: {dt}"
        return cls(documents)

    def assert_preserved(self, reader, created):
        assert set(created) == set(self.DOCTYPES), "Declare created IDs for both document types"
        for dt in self.DOCTYPES:
            previous = {name for kind, name in self.documents if kind == dt}
            added = list(created[dt])
            assert len(added) == len(set(added)), f"Duplicate created ID: {dt}"
            assert not previous.intersection(added), f"Reused preexisting ID: {dt}"
            assert self.names(reader, dt) == previous | set(added), f"Unexpected inventory delta: {dt}"
        for (dt, name), original in self.documents.items():
            assert reader.get(dt, name) == original, f"Preexisting document changed: {dt}/{name}"

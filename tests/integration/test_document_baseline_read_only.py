"""Read-only ERPNext regression for dynamic document preservation."""

from config.document_baseline import DocumentBaseline
from pages.procurement import ReadAPI


def test_existing_purchase_documents_can_be_snapshotted_without_writes(authenticated_page, settings):
    reader = ReadAPI(authenticated_page.context.request, settings.base_url)
    baseline = DocumentBaseline.capture(reader)
    baseline.assert_preserved(reader, {dt: [] for dt in baseline.DOCTYPES})

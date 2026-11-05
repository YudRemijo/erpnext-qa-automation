"""QA-008: retain one new UI-created Draft; no submission or cleanup."""

import pytest
from pages.purchase_order import create_verified_draft


@pytest.mark.transactional
def test_qa008_create_purchase_order_in_draft(authenticated_page, settings, record_property):
    create_verified_draft(authenticated_page, settings, record_property)

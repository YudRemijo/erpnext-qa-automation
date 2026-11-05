"""Observe a rejected UI action without bypassing client or server validation."""

import re
from urllib.parse import urlsplit

from playwright.sync_api import expect


SAVE_ENDPOINT = "/api/method/frappe.desk.form.save.savedocs"


def observe_rejection(page, action, message_pattern):
    """One action, explicit error dialog and request/response evidence.

    No response wait is imposed on a client-side rejection. A terminal dialog plus
    zero pending AJAX is the completion signal, not a fixed observation sleep.
    """
    requests, responses = [], []

    def sent(request):
        if urlsplit(request.url).path == SAVE_ENDPOINT:
            requests.append(request)

    def returned(response):
        if urlsplit(response.url).path == SAVE_ENDPOINT:
            payload = response.json()
            responses.append({"http_status": response.status,
                              "exc_type": payload.get("exc_type"),
                              "has_exception": bool(payload.get("exc")),
                              "saved_documents": [d["name"] for d in payload.get("docs", [])
                                                  if d.get("doctype") in ("Purchase Order", "Purchase Receipt")]})

    page.on("request", sent)
    page.on("response", returned)
    try:
        action()
        dialog = page.locator(".modal.show")
        expect(dialog, "Expected an explicit validation error, not a loading failure").to_be_visible()
        expect(dialog).to_contain_text(re.compile(message_pattern, re.I))
        page.wait_for_function("() => window.frappe?.request?.ajax_count === 0")
        if requests:
            assert len(requests) == len(responses) == 1, "Every attempted Save must have one terminal response"
            assert responses[0]["has_exception"] and responses[0]["exc_type"], "Server rejection requires an explicit exception"
            assert not responses[0]["saved_documents"], "Unexpected persistence in error response"
        else:
            assert not responses
        return {"layer": "server" if requests else "client", "save_requests": len(requests),
                "responses": responses, "dialog": dialog.inner_text()}
    finally:
        page.remove_listener("request", sent)
        page.remove_listener("response", returned)


def item_input(document, field):
    row = document.form.locator('.frappe-control[data-fieldname="items"] .grid-row[data-idx="1"]')
    control = row.locator(f'input[data-fieldname="{field}"]')
    if not control.is_visible():
        row.locator(f'.grid-static-col[data-fieldname="{field}"]').click()
    expect(control).to_be_visible()
    return control

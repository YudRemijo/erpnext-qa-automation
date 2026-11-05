"""Restricted diagnostics for the current cookie-authenticated local framework."""


def start_restricted_trace(context):
    # Even snapshots=False serializes context-options.extraHTTPHeaders. Our login
    # uses cookies, not these headers; clear them before recording any metadata.
    # Network/DOM capture stays disabled, so session cookies are not captured.
    context.set_extra_http_headers({})
    context.tracing.start(screenshots=True, snapshots=False, sources=False)

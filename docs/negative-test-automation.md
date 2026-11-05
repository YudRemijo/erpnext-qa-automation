# Negative procurement validation

## Scope and execution contract

These tests exercise ERPNext v16.53.0 using UI actions and read-only REST queries.
They use the existing ADL supplier, stock item, Nos UOM, USD 100 rate and Stores - ADL.
No API writes, SQL writes, invoice creation, cancellation, cleanup, configuration
changes or Docker operations are used. This implements negative coverage of REQ-09 /
R-01 / R-02; assertions distinguish the rejection layer from document persistence.

NEG-001/002/003 prepare an otherwise verified PO form using the shared QA-008 logic
with `persist=False`, change one input, and attempt Save once. A completed validation
dialog and zero pending AJAX are the terminal signal. Request/response listeners
record whether the real Save endpoint was reached; they do not intercept or rewrite it.
The API must show no new PO. A modal by itself, a required asterisk, or a missing Save
request without a terminal error is insufficient to pass.

NEG-004 requires `--run-transactions`. It creates its own UUID-titled PO for 10,
saves/submits that PO and maps a new PR for 11. It does not reuse previous documents.
The observed server validation occurs at Submit, so the legitimate 11-unit Draft is
retained. No automatic correction, cancellation, resubmission or cleanup follows.

## Verified rules and actual results — 2026-11-04

| Case | Preconditions and action | Expected result | Actual result | Classification |
|---|---|---|---|---|
| NEG-001 | Otherwise valid unsaved PO; clear Supplier; Save once | Explicit Supplier rejection; no persisted PO | Missing Fields: Supplier is required; zero Save requests; no PO created | PASS, client-side coverage |
| NEG-002 | Otherwise valid unsaved PO; clear Item Code; Save once | Explicit item rejection; no persisted PO | Missing Fields: In Items, Item Code is required in every row; zero Save requests; no PO created | PASS, client-side coverage |
| NEG-003 | Zero quantities disabled; otherwise valid PO; set qty=0; Save once | Reject zero quantity; no persisted PO | Save HTTP 417, InvalidQtyError; Invalid Quantity: quantity cannot be zero; no PO created | PASS, backend validation via UI |
| NEG-004 | Fresh submitted PO10, zero receipts; effective allowance 0%; no bypass role; PR11 | Reject over-receipt at the enforced lifecycle stage; no physical stock effect | PR Draft Save accepted; Submit HTTP 417, OverAllowanceError, Limit Crossed, over limit by Qty 1.0; PR remains Draft | PASS, backend Submit validation |

Supplier, Items table, Item Code and Quantity have required metadata. Installed
Frappe also contains server-side mandatory validation, but the Supplier/Item cases
did not reach it. Their backend enforcement is **not dynamically proven** by these
tests. No client-validation bypass was performed to manufacture server coverage.

NEG-003 explicitly requires a server response with `InvalidQtyError`, rather than
accepting a generic field error. Its successful execution proves that the current
UI does not treat numeric zero as an empty mandatory value in this path, while the
backend applies a separate nonzero-quantity rule.

Negative quantities were investigated statically but are **not dynamically tested**.
The installed status updater contains negative-quantity checks; a non-return PR also
has client/server negative-quantity checks. These facts do not establish that a
negative PO Draft is rejected at Save. NEG-003 deliberately uses zero, a confirmed
rule, to avoid unnecessary invalid persistent data. No negative-quantity result is
claimed as PASS.

## Current policy and source evidence

Read-only REST inspection confirmed:

- Stock Settings `over_delivery_receipt_allowance = 0`.
- Item QA-ADL-TEST-001 `over_delivery_receipt_allowance = 0`.
- Stock Settings `role_allowed_to_over_deliver_receive = null`.
- Buying Settings `allow_zero_qty_in_purchase_order = 0`.

The installed allowance lookup uses a nonzero Item allowance in preference to the
global value, otherwise falls back to Stock Settings. It also has a configured-role
bypass and a 0.01 percentage-point comparison margin. The test skips before setup
if 11 vs 10 would be within tolerance or a bypass role is configured; it never changes
those settings. A zero-quantity policy change fails NEG-003's precondition before Save.

Installed source paths and inspected locations (inside the backend, read-only):

- `frappe/public/js/frappe/form/save.js:121–270`: mandatory checking and Missing Fields.
- `frappe/model/document.py:1454`: server mandatory validation exists; not exercised
  by the missing Supplier/Item cases.
- `erpnext/controllers/accounts_controller.py:1718–1733`: nonzero quantity check,
  InvalidQtyError, unless the document's zero-quantity flag is allowed.
- `erpnext/buying/doctype/purchase_order/purchase_order.py:195–197,232–241`:
  zero-quantity exception is driven by Buying Settings.
- `erpnext/controllers/status_updater.py:443–538,840–859`: effective allowance,
  configured-role bypass, and OverAllowanceError.
- `erpnext/stock/doctype/purchase_receipt/purchase_receipt.py:393–413`:
  previous-document quantity validation precedes Stock Ledger/GL posting on Submit.

Code inspection supports the oracles; only the observed UI/API execution establishes
the dynamic results reported above. No confirmed product defect is asserted.

## Received Quantity: known behavior and limits

The PO-to-PR mapper was observed to suggest the pending Accepted Quantity while its
internal `received_qty` initially remains zero. Client `buying.js:221–251` recalculates
Received Quantity when Accepted or Rejected Quantity changes. Frappe's numeric
`set_value` does not fire that change handler when the value is unchanged.

The existing E2E helper logs this condition and uses legitimate, unsaved UI edits
6 → 5 → 6 when needed; it never mutates `cur_frm.doc` or calls write APIs. The resulting
Received/Stock Quantity is asserted before saving. NEG-004 changes 10 → 11, so the
normal event recalculates it without that interaction.

Additional source evidence: `buying_controller.py:913–926` fills a zero Received
Quantity from Accepted + Rejected during server validation and checks consistency.
This backfill was inspected, not separately exercised by saving a stale zero in this
suite. The exact origin of the initial mapped zero remains a mapper investigation
topic; the observation alone is not proof of incorrect persisted stock.

## Isolation, recovery and evidence

All negative attempts share the existing local OS lock, including those that should
not persist. Tests reject parallel workers. The lock prevents cooperating processes
on this Windows host from overlapping, not human actions or another host.

Before each negative, the API snapshots every existing PO, PR and PI, the item ledger
and the actual item/warehouse Bin balance. Teardown always records new documents,
changed prior documents, ledger and physical balance, even after a failed action.
Previous documents must be byte-for-byte equivalent as parsed JSON; invoices and
physical stock must remain unchanged. Ordered/projected quantity is not the physical
balance: a newly submitted setup PO legitimately increases outstanding order quantity.

Before retrying after any timeout, inspect the manifest and persisted documents.
Save/Submit are never repeated automatically. The over-receipt test deliberately
retains its PO and PR Draft; **do not manually submit that 11-unit artifact** as a
normal receipt. A repeated run creates a different setup and must be intentional.

Artifacts are ignored by Git under `artifacts/negative-<UUID>/`:

- `manifest.json`: generated IDs, policy, validation layer, sanitized response
  status/exception type, visible validation text, baseline and after-state.
- On failure: post-login screenshot and `failure-actions-only.zip`.
- Authentication is outside capture. Restricted tracing disables DOM/network/source
  capture and clears extra HTTP headers before starting; authentication uses the
  existing cookie-based browser context. No login trace or saved browser state exists.

An offline synthetic-secret test initially demonstrated that Playwright still puts
context extra headers into trace metadata with DOM/network recording disabled. The
diagnostic startup now clears those headers first. The privacy check verifies the
synthetic credential is absent from the archive, the network file is empty, no frame
snapshot is present, and action events remain. It uses intercepted offline responses,
not ERPNext or real credentials. The trace policy assumes the current raw isolated
context; re-review it before introducing storage-state or header-based authentication.

Manifests classify assertion failures as requiring oracle/business triage and other
exceptions as automation/environment triage. A failed assertion is not automatically
a product defect. Incomplete/ambiguous operations are never reported as PASS. A run
manifest remains local and must not be automatically uploaded with unrestricted access.

## Execution

Static syntax checks use Python AST parsing; no external linter is currently installed
or required by the repository. Offline tests cover locale quantities/currency and
trace privacy.

```powershell
# No planned business-document persistence: smoke, mandatory/zero negatives, unit
# checks. QA-008, QA-011 and NEG-004 remain skipped without the opt-in flag.
.\.venv\Scripts\python.exe -m pytest -v --maxfail=1 --durations=8

# One controlled transactional negative only. Do not run the whole transaction suite.
.\.venv\Scripts\python.exe -m pytest tests/negative/test_over_receipt.py --run-transactions -v -s --maxfail=1 --durations=2
```

## Retained controlled execution

NEG-004 run `331c6cc1-0716-4289-a4cb-c4ddc6c0b350` passed in 30.42 seconds.

- New PO PUR-ORD-2026-00004: Submitted, To Receive and Bill; 10 ordered,
  zero received, 10 pending, 0% received.
- New PR MAT-PRE-2026-00005: Draft (`docstatus=0`), accepted/received 11, rejected 0;
  USD 1,100 net, USD 209 tax, USD 1,309 total.
- Submit attempted once and rejected with OverAllowanceError, HTTP 417.
- Physical balance: 20 → 20 Nos. Four pre-existing SLEs unchanged; none for this PR.
- Previous PO/PR documents unchanged; no Purchase Invoice created.
- NEG-001/002/003 initial execution: 3 passed in 35.91 seconds; no new documents.
- Final regression (including strengthened backend assertions and restricted tracing):
  **10 passed, 3 skipped in 46.24 seconds**. Passing tests comprise three negatives,
  three smoke tests and four offline diagnostic checks. QA-008, QA-011 and NEG-004
  were skipped because `--run-transactions` was absent.
- Offline diagnostic checks after the privacy fix: 4 passed in 2.54 seconds. The
  earlier synthetic-header privacy failure was a diagnostic implementation issue,
  corrected before the final regression, not an ERPNext business failure.
- Final read-only check: actual stock 20, ordered quantity 10, projected quantity 30;
  no ledger rows for MAT-PRE-2026-00005 and no Purchase Invoice.

QA-008 and QA-011 were not rerun. The only change to PO creation adds a non-persisting
preparation mode; its default behavior is unchanged. New negative tests exercise that
mode, and NEG-004 exercises the existing default creation/submission path without a
successful receipt submission. No full E2E rerun was needed for this evidence change.

Files added: `config/diagnostics.py`, `pages/negative_validation.py`,
`tests/negative/conftest.py`, `tests/negative/test_purchase_order_validation.py`,
`tests/negative/test_over_receipt.py`, `tests/unit/test_local_diagnostics.py`, and this
document. Files updated: `tests/conftest.py`, `tests/transactions/conftest.py`,
`pages/purchase_order.py`, `pyproject.toml`, and `docs/transactional-automation.md`.
The three original strategy/scenario/exploratory documents and approved test bodies
remain unchanged.

## Remaining limitations and next step

The backup has no independently verified restore. Avoid transaction repetitions for
stability metrics. Locking now uses `msvcrt` on Windows and `flock` on POSIX, with
fail-closed behavior and offline unit tests; Linux runner execution remains pending.
The environment uses shared masters and real accumulated balances, so CI should
start with read-only/unit/negative gates and keep transactional execution manual.
The initial hosted workflow is stricter: offline-only, without browser/ERPNext;
see [ci-cd.md](ci-cd.md) for the current category and publication contract.
Backend Supplier/Item enforcement, negative PO quantities, tolerance boundaries,
configured-role exceptions and failure-induced recovery need dedicated later tests.

# Transactional procurement automation

## Scope and architecture

QA-008 creates and retains one Purchase Order Draft. QA-011 is a single independent
end-to-end test: create a new PO for 10 units, save and submit it, receive 4 units,
then receive the remaining 6. Each receipt is checked in Draft and after submission.
No test depends on another test running first. No invoice, cancellation, or cleanup
is performed. This implements the receipt portion of REQ-08 / R-02 / R-04 and includes
PO persistence coverage from REQ-07 / R-01.

The historical scenario document includes submission in QA-008 and describes the
original hypotheses. The current QA-008 implementation deliberately stops at Draft;
submission and the complete partial-receipt lifecycle are exercised by QA-011.

- `tests/conftest.py`: existing isolated UI authentication and opt-in collection gate.
  Environment variables override the unversioned local `.env`; credentials are never
  included in evidence. Existing smoke tests are unchanged.
- `pages/purchase_order.py`: the approved QA-008 Draft implementation extracted once
  so both tests use the same navigation, filling, totals, persistence and stock checks.
  QA-008 remains a thin test entry point with the same assertions.
- `pages/procurement.py`: authenticated GET-only REST reader with pagination and small
  document actions for readiness, Save, Submit, reopening and PO-to-PR mapping.
- `tests/conftest.py`: shared nonblocking Windows OS file lock, run manifest and
  post-login failure evidence for transactional and negative tests; rejects parallel workers.
- `tests/transactions/conftest.py`: scope note; shared fixtures live at the test root.
- `tests/transactions/test_qa011_partial_receipt_e2e.py`: readable business assertions
  and the complete sequence in one test. It does not write browser model data or use
  API writes to bypass the interface.

## Preconditions and approved data

Use the existing Python environment and installed Pytest/Playwright Chromium. Start
ERPNext separately; these tests do not manage Docker. Writes are restricted to
`http://localhost:8080` and require explicit `--run-transactions`.

Approved masters: Atlas Distribution Ltd, QA Atlas Test Supplier, QA-ADL-TEST-001,
Stores - ADL, Nos, USD 100. Supplier/item enablement and warehouse/company are checked
through the API before saving. Only the approved, enabled ADL tax template with one
On Net Total row, ICMS 19% - ADL at 19%, is supported. Defaults must match this contract;
the test fails before Save rather than changing fiscal/currency configuration.

Required By is calculated as the form's transaction date plus 14 days, with an
additional check that it is in the future. The current site uses day/month/year dates
and comma decimal separators, including quantity values such as `10,000`.

The environment must be dedicated during execution. Do not run manual transactions,
other test processes, or other hosts against the same item/warehouse concurrently.
The local OS lock prevents this repository's transactional test processes on this
Windows machine from overlapping; it cannot lock out human users or another host.

## Oracles and evidence

For quantity Q, independent expected values are Q × USD 100 net, Q × USD 19 tax, and
Q × USD 119 grand total. UI totals and the saved document's REST representation must
agree. Tax policy itself is an approved test assumption, not a fiscal conclusion.

| Checkpoint | PO received | PO pending | Received % | Physical balance |
|---|---:|---:|---:|---:|
| Submitted PO, no receipts | 0 | 10 | 0 | B |
| First PR submitted | 4 | 6 | 40 | B + 4 |
| Second PR submitted | 10 | 0 | 100 | B + 10 |

B is read from Bin at the beginning of each run; zero is not assumed. Draft PO/PR
checks require no physical or ledger change. PRs preserve supplier, company, item,
price, UOM, warehouse, PO identifier and the actual generated PO item identifier.
Submitted records are reopened in the UI and independently queried by REST.

Ledger reconciliation filters by item/warehouse and verifies company, stock UOM,
voucher type, actual voucher IDs and PR line IDs. Net voucher movements must be +4
and +6. Their sum and the Bin increment must equal 10. No fixed number of ledger
rows is assumed. Existing rows must remain unchanged, generated row IDs must be
unique, and unexpected vouchers must not appear in the baseline delta. This detects
unexpected stock effects; it is not a general-purpose ledger deduplication audit.

The four protected prior documents are read before/after and compared in full:
PUR-ORD-2026-00001, PUR-ORD-2026-00002, MAT-PRE-2026-00001 and MAT-PRE-2026-00002.
The Purchase Invoice baseline must remain unchanged. The second receipt's GL Entries
must exist, be active and have equal aggregate debit/credit. Their account selection,
valuation and fiscal correctness are not independently certified by this test.

## Observed mapping behavior

The mapper suggests the correct pending Accepted Quantity (10, then 6), but its
initial internal `received_qty` is zero. Changing the first receipt from 10 to 4
recalculates it. Re-entering the same value 6 does not trigger Frappe's numeric field
change handler. For the second unsaved receipt only, the UI changes 6 → 5 → 6, blurs
the field and waits for AJAX completion. Received/Stock Quantity must then both be 6
before Save. There is no direct model mutation or manually forced tax calculation.

Status strings are recorded from the application and matched between UI/API rather
than used as the only success oracle. In the verified run, both PRs ended To Bill;
the PO changed from To Receive and Bill at 40% to To Bill at 100%.

## Execution and retained data

From the repository root, run smoke and verify the write gate first:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/smoke tests/transactions -v
```

Run only the E2E transaction, not the entire transactional directory:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/transactions/test_qa011_partial_receipt_e2e.py --run-transactions -v -s --durations=2
```

The independent Draft-only entry point remains available, but creates an additional
order and was deliberately not executed during E2E validation:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/transactions/test_qa008_purchase_order_draft.py --run-transactions -v -s
```

Each E2E execution uses a UUID recorded in the PO Title as `QA-E2E-<UUID>`, Pytest
properties, stdout and `artifacts/qa011-<UUID>/manifest.json`. The response to Save
provides the real naming-series identifier; no next-number prediction is used.
All documents remain for audit. Successful repetitions increase stock by another 10;
they do not reset the environment. A lower or higher starting balance is valid.

Save and Submit are each clicked once. After ambiguous errors/timeouts, read-only API
queries report candidates or the persisted docstatus, then fail without repeating
the action. Inspect the retained manifest/documents before authorizing another run;
there is no blind retry or automatic resume/rollback. A partial run remains partial.

Action/assertion limits use the existing 15-second policy; navigation uses 30 seconds.
Reconciliation polls GET-only persisted PO/Bin conditions within the action budget.
There are no fixed sleeps or retries of the full test.

API HTTP failures are environment/access evidence; Playwright locator/readiness
failures require automation/environment triage. A business assertion mismatch is
evidence to investigate, not automatically a product defect. PASS is recorded only
after all final checks. An incomplete manifest is not a passing execution.

The ignored artifacts directory contains a curated business manifest and, on failure,
a post-login screenshot and restricted actions/screens trace. DOM/network/source
capture is disabled and extra HTTP headers are cleared before tracing starts.
Authentication is never recorded. The offline privacy test checks a synthetic secret
is absent from the trace; see [negative-test-automation.md](negative-test-automation.md).
A Save ambiguity is also printed to Pytest output.
Keep artifacts local; do not publish them automatically. Locking now uses a shared
fail-closed OS abstraction (`msvcrt` on Windows, `flock` on POSIX). Windows checks
passed locally; actual Linux runner validation remains pending. Hosted CI deliberately
executes offline tests only; see [ci-cd.md](ci-cd.md).

## Verified execution — 2026-11-04

Run: `a975a6bc-ae58-42e3-8025-c0d811f0a4d7`.

- Smoke/gate: 3 passed, 2 skipped in 22.14 seconds.
- E2E: 1 passed in 34.85 seconds (test call 27.76 seconds); no transactional retry.
- New PO: PUR-ORD-2026-00003, line nhj21bpt4u, docstatus 1, final status To Bill.
- New PR1: MAT-PRE-2026-00003, 4 accepted / 0 rejected, docstatus 1, To Bill;
  USD 400 net + USD 76 tax = USD 476.
- New PR2: MAT-PRE-2026-00004, 6 accepted / 0 rejected, docstatus 1, To Bill;
  USD 600 net + USD 114 tax = USD 714.
- SLE ac1c5eea43: PR1 +4, physical balance 14.
- SLE d9ac2b547b: PR2 +6, physical balance 20.
- Initial Bin 10; final Bin 20; PO received 10, pending 0, received 100%.
- No new Purchase Invoice; protected prior documents unchanged.
- Second PR GL: debit USD 600 to Insumos (materiais diretos) - ADL;
  credit USD 600 to Gastos incluidos en la valoración - ADL; balanced.

This is one successful E2E execution, not a stability study or a validated restore
exercise. The observed stale mapped Received Quantity remains a focused regression
candidate; the documented UI interaction is part of the current test procedure.

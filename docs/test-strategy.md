# ERPNext Enterprise QA Automation â€” Test Strategy

> Historical exploration/design baseline. Later implemented coverage and observed
> executions are indexed in [evidence.md](evidence.md). Hypotheses below describe
> this original stage and are not the current automation execution report.

## Project scope

This portfolio project evaluates procurement and inventory for Atlas Distribution Ltd (ADL). Purchase Order (PO), Purchase Receipt (PR), and Stock Ledger are the priorities. Supplier, Item, and Warehouse are supporting master data.

This strategy uses only the functional exploration recorded in this conversation on 4 November 2026. It is a design artifact, not a test execution report. No defects or transactional outcomes have been established.

Current scope: documentation and planning. A future read-only suite may verify navigation, empty states, form structure, defaults, warehouse hierarchy, and report filters. Transactional tests require separate authorization and approved business rules. No automation, fixtures, application changes, or dependency installation are included in this stage.

### Evidence and requirement classification

- **OBS**: directly observed interface behavior. This does not imply server-side validation or transactional correctness.
- **HYP**: a proposed business invariant or behavior requiring stakeholder confirmation and execution evidence.
- **UI guidance**: text displayed by the application; its operational effect remains HYP.

Requirement IDs below represent local QA requirements derived from exploration and risk analysis, not an approved ERPNext specification. Scenario IDs and detailed procedures are in [test-scenarios.md](test-scenarios.md); evidence boundaries are in [exploratory-findings.md](exploratory-findings.md).

| Requirement | Basis | QA requirement | Risk | Scenarios |
|---|---|---|---|---|
| REQ-01 | OBS | Buying and Stock expose the observed procurement/inventory destinations | R-06 | QA-001 |
| REQ-02 | OBS | PO exposes its observed fields, required markers, and status-filter vocabulary | R-01 | QA-002, QA-004 |
| REQ-03 | OBS | PR exposes its observed quantities, warehouses, required markers, and status-filter vocabulary | R-02 | QA-003, QA-004 |
| REQ-04 | OBS | ADL Stock Ledger exposes the observed filters and a result area | R-04 | QA-005 |
| REQ-05 | OBS | Master-data forms and warehouse hierarchy expose the observed structure and group guard | R-05 | QA-006 |
| REQ-06 | OBS | Blank PO/PR forms displayed USD and Brazil ICMS 19%; suitability needs approval | R-03 | QA-007 |
| REQ-07 | HYP | Approved valid procurement data can progress from PO to PR with traceable references | R-01, R-02 | QA-008, QA-010 |
| REQ-08 | HYP | Submission, partial receipt, and rejection effects reconcile with approved inventory rules | R-02, R-04 | QA-011, QA-012, QA-013 |
| REQ-09 | HYP | Invalid or incomplete input is handled according to approved validation rules without unintended persistence | R-01, R-02, R-05 | QA-009, QA-014 |

## System under test

- Local ERPNext: `http://localhost:8080`, running through Docker Desktop on Windows.
- Docker directory supplied by the user: `<docker-workspace>/frappe_docker`.
- Project directory: `<project-root>`.
- Previously inspected container image: `frappe/erpnext:v16.53.0`. The internal application version was not independently confirmed.
- ADL was visible in the warehouse tree and Stock Ledger company filter.
- Exploration reused an authenticated session. Default-password validity and the session's exact username were not independently verified. Authorization was limited to Administrator authentication and read-only exploration.

Supplier, PO, and PR lists showed empty states. The active-item list returned no results; the workspace displayed zero active items. The warehouse tree contained a group and four children. These are dated baseline observations, not permanent assertions about the environment.

## Business risks

Priorities below are proposed QA impact assessments, not observed incidents or measured likelihoods. P1 is the highest priority in this plan; P2 is supporting coverage.

| Risk | Potential business impact | Priority | Evidence boundary |
|---|---|---|---|
| R-01 â€” Procurement integrity | Incorrect supplier, item, quantity, date, or PO reference could misstate purchasing commitments | P1 | Fields and status options observed; persistence and enforcement untested |
| R-02 â€” Receipt integrity | Duplicate, excessive, partial, or misallocated receipts could misstate goods received and outstanding quantities | P1 | Accepted/rejected quantities and warehouse fields observed; effects untested |
| R-03 â€” Financial defaults | Unapproved currency, tax, or rounding assumptions could produce misleading procurement totals | P1 | USD and Brazil ICMS 19% observed on blank forms; appropriateness/calculations unverified |
| R-04 â€” Inventory traceability | Missing or incorrect ledger quantities, valuation, company scope, or voucher references could hide inventory discrepancies | P1 | ADL report filters and empty result observed; transaction reconciliation untested |
| R-05 â€” Master-data suitability | Ineligible suppliers/items or incorrect warehouse hierarchy could obstruct or misroute procurement | P1 | Structure, guidance, and group-selection guard observed; eligibility rules untested |
| R-06 â€” Access and navigation | Broken destinations or session assumptions could prevent operations and make automation unreliable | P2 | Authenticated navigation worked; role-specific access untested |

## Test levels and types

| Level/type | Proposed coverage | Execution boundary |
|---|---|---|
| UI smoke / system | Buying/Stock navigation, PO/PR forms, filters, Stock Ledger, warehouse guard | Read-only candidates; no suite implemented |
| UI contract / regression | Required markers, tabs, field presence, approved defaults | Assertions describe presentation, not server validation |
| Negative system tests | Missing required data, invalid quantities, over-receipt policy | Future write-capable execution only after approval |
| Integration / end-to-end | PO to PR, full and partial receipts, warehouse/ledger reconciliation | Requires approved fixtures, rules, and transaction authorization |
| Data reconciliation | Compare persisted document quantities and voucher-linked ledger movements | Independent oracle; do not rely only on a status badge |

Unit, API, performance, security, and cross-browser testing are not claimed as covered. Browser smoke checks may use Playwright with Pytest later. API/database writes are outside current authorization. Administrator exploration does not establish least-privilege behavior.

## Test data strategy

1. Keep a read-only baseline separate from future transaction fixtures. Do not create data to satisfy an empty-state test.
2. Discover current data before execution. Empty states are valid only when their preconditions hold; report a blocked or inapplicable scenario if the baseline has changed.
3. For future approved transactional coverage, define a dedicated ADL supplier, a purchasable stock item, its UOM, an eligible non-group warehouse, and explicit currency/tax expectations. Do not assume existing warehouses or suppliers meet all conditions.
4. Use uniquely identifiable run data, with documented quantities and independently calculated expected balances. Proposed quantities in scenarios are examples, not existing records.
5. Obtain explicit authorization for creation, submission, cancellation, and cleanup separately. Prefer an approved resettable environment; deletion or rollback is not implicitly authorized.
6. Keep credentials out of source, fixtures, logs, screenshots, traces, and reports. Use an approved secret source for future login automation. Do not commit authenticated browser state.

## Environment requirements

- Application reachable locally; intended company confirmed as Atlas Distribution Ltd.
- Version/build, browser, locale, date/time zone, currency, and tax baseline recorded for each run.
- Stable authenticated test session with an approved account; exact identity verified before account-specific assertions.
- Read-only smoke execution must avoid Save, Submit, Cancel, Delete, import, and configuration actions. Opening a blank form is permitted only for inspection; no field entry is needed for the initial five candidates.
- No public exposure, Docker changes, or dependency installation under current scope.
- Standalone Playwright packages were not resolved from this project during diagnosis. Browser automation was available through the integrated browser. Future Python/Pytest/Playwright runtime readiness must be checked before implementation; no installation is authorized here.
- Transaction execution additionally requires a reset/cleanup plan, approved fixture ownership, expected starting balances, and permission to mutate data.

## Entry and exit criteria

### Read-only smoke entry

Application reachable, session authenticated, company known, data preconditions checked, and assertions limited to OBS behaviors. Changed defaults require review rather than automatic classification as defects.

### Read-only smoke exit

All selected scenarios executed with evidence and explicit pass/fail/blocked status; every mismatch triaged against the current approved baseline. No unresolved P1 finding affecting the selected coverage. This criterion does not imply transactional readiness.

### Transactional entry

Separate write authorization; approved REQ-07â€“09 acceptance rules; deterministic fixtures; confirmed quantity/UOM, posting, tax, and valuation oracles; known starting balances; and approved recovery procedure.

### Transactional exit

Approved P1 positive, negative, integration, and partial-receipt scenarios pass; PO/PR references and ledger quantities reconcile; no unresolved release-blocking P1 findings; residual risks and blocked cases are explicitly accepted. Exact release gates require stakeholder agreement.

### Documentation-stage completion

The three requested documents exist, scenario/risk/requirement references agree, and no planned scenario is presented as an executed result.

## Evidence and reporting strategy

- Record scenario ID, requirement/risk IDs, build, account role, company, preconditions, timestamps/time zone, steps, expected/actual outcome, and evidence references.
- Use screenshots and focused traces for future executions only when authorized and sanitized. Avoid retaining passwords, cookies, tokens, or sensitive business data.
- Distinguish **planned**, **passed**, **failed**, **blocked**, and **not applicable**. All scenarios in this documentation are currently planned; prior exploration is supporting evidence, not automated execution.
- A mismatch becomes a defect candidate only after reproduction and comparison with an approved expectation. Preserve evidence and uncertainty; do not label an unapproved hypothesis a defect.
- Report coverage separately for OBS presentation checks and HYP transactional behavior. Report blocked cases with their impact rather than counting them as passes.
- No evidence files, code, or reports beyond these three Markdown documents are created in this stage.

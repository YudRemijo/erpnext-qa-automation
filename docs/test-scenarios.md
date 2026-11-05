# ERPNext Enterprise QA Automation — Test Scenarios

> Historical exploration/design baseline. Later implemented coverage and observed
> executions are indexed in [evidence.md](evidence.md). Hypotheses below describe
> this original stage and are not the current automation execution report.

## Interpretation and traceability

All scenarios below are **planned, not executed tests**. OBS means the expectation derives from earlier UI exploration; HYP means a proposed expectation that needs business approval and execution evidence. An OBS marker or help text does not prove backend enforcement. P1 is highest priority; P2 is supporting coverage. Risk and requirement definitions are in [test-strategy.md](test-strategy.md).

Current authorization permits no record mutation. Opening blank forms for inspection does not authorize saving them. Every HYP scenario below is blocked for execution until separately authorized. No defect is asserted by this catalog.

### QA-001 — Navigate procurement and inventory workspaces

- **Traceability:** REQ-01; R-06. **Priority:** P2. **Type:** positive UI smoke. **Basis:** OBS.
- **Preconditions:** Local ERPNext reachable; authenticated session; Buying and Stock visible.
- **Steps:** Open Buying; inspect Supplier, Purchase Order, and Purchase Receipt destinations. Open Stock; inspect Item, Warehouse, Purchase Receipt, and Stock Ledger destinations.
- **Expected results:** The observed destinations are available and open their corresponding screens. Purchase Receipt is accessible through both modules. No document is changed.
- **Automation feasibility:** High; Playwright navigation assertions organized with Pytest. Prefer semantic links/buttons and wait for destination content.

### QA-002 — Inspect Purchase Order form contract

- **Traceability:** REQ-02; R-01. **Priority:** P1. **Type:** positive UI contract. **Basis:** OBS.
- **Preconditions:** Authenticated Buying access; permission to inspect a blank PO form; no field entry or persistence.
- **Steps:** Open Purchase Order list; open Add Purchase Order; inspect Details and available tabs; inspect the item grid; leave without saving.
- **Expected results:** Blank form displays Not Saved; Details, Address & Contact, Terms, and More Info tabs exist. Series, Supplier, and Date have required markers. Item Code, Required By, Quantity, and UOM have grid required markers. Set Target Warehouse, rates, and totals are present. This check does not establish save-time validation.
- **Automation feasibility:** High for field/marker presence; scope locators to the active form/grid. Avoid temporary document IDs and generated asset names.

### QA-003 — Inspect Purchase Receipt form contract

- **Traceability:** REQ-03; R-02. **Priority:** P1. **Type:** positive UI contract. **Basis:** OBS.
- **Preconditions:** Authenticated access; permission to inspect a blank PR form without persistence.
- **Steps:** Open Purchase Receipt; open Add Purchase Receipt; inspect header, item grid, and tabs; leave without saving.
- **Expected results:** Not Saved is displayed. Series, Supplier, Date, Posting Time, and item-row Item Code have required markers. Supplier Delivery Note, Accepted Warehouse, Rejected Warehouse, accepted/rejected quantities, rates, and totals are present. Edit Posting Date and Time and Apply Putaway Rule are visible; Is Return was disabled in the observed initial form. No operational return behavior is asserted.
- **Automation feasibility:** High; semantic navigation plus scoped form/grid assertions.

### QA-004 — Inspect purchasing list states and status vocabulary

- **Traceability:** REQ-02, REQ-03; R-01, R-02. **Priority:** P2. **Type:** UI regression. **Basis:** OBS.
- **Preconditions:** PO and PR lists accessible; no user filters obscuring the inspected baseline. Empty-state assertion additionally requires no matching records.
- **Steps:** Open each list; inspect Status options without changing documents; inspect its result area.
- **Expected results:** PO options include Draft, On Hold, To Pay, To Receive and Bill, To Bill, To Receive, Completed, Cancelled, Closed, Delivered. PR options include Draft, Partly Billed, To Bill, Completed, Return, Return Issued, Cancelled, Closed. With the original empty baseline, each list displays its no-document message. Options do not prove that transitions work.
- **Automation feasibility:** High; parameterize PO/PR in Pytest. Keep empty-state checks conditional on controlled preconditions.

### QA-005 — Open ADL Stock Ledger and inspect report scope

- **Traceability:** REQ-04; R-04. **Priority:** P1. **Type:** positive report smoke. **Basis:** OBS.
- **Preconditions:** Authenticated Stock access; ADL available; the original report window is used only for a baseline replay.
- **Steps:** Open Stock Ledger; inspect Company, From Date, To Date, Warehouses, Items, and Voucher # filters; inspect the result area. For a dated baseline replay, use 4 October–4 November 2026 without modifying records.
- **Expected results:** Report opens with the observed filter controls. ADL was the observed default company. The explored date window returned Nothing to show. A future empty-result assertion requires confirmation that no qualifying movements exist; otherwise assess results against approved fixtures. Relative date defaults must not be hardcoded as timeless behavior.
- **Automation feasibility:** High for opening/filter presence; medium for data assertions until a stable baseline exists. No fixed sleeps.

### QA-006 — Inspect ADL warehouses and group-selection guard

- **Traceability:** REQ-05; R-05. **Priority:** P2. **Type:** positive and negative UI navigation. **Basis:** OBS.
- **Preconditions:** Original ADL hierarchy exists; no group selected before the negative step; permission to inspect dialogs only.
- **Steps:** Open Warehouse tree for ADL. Attempt Add Warehouse without a selected group; dismiss the message. Select All Warehouses - ADL and open Add Warehouse; inspect then close the empty dialog. Open Stores - ADL details without editing.
- **Expected results:** Guard message: Select a group Warehouse first. Under a selected group, the dialog displays required Warehouse Name and Company plus Is Group and group-only child guidance. Existing hierarchy includes Finished Goods, Goods In Transit, Stores, and Work In Progress. Stores is enabled, belongs to ADL, and has All Warehouses - ADL as parent. No Create New or Save action is executed.
- **Automation feasibility:** High with explicit tree selection preconditions; verify selected node before the guard assertion.

### QA-007 — Inspect purchasing currency and tax defaults

- **Traceability:** REQ-06; R-03. **Priority:** P1. **Type:** UI baseline. **Basis:** OBS; business suitability remains HYP.
- **Preconditions:** Original ADL defaults unchanged; blank PO/PR forms inspectable.
- **Steps:** Open each blank form; inspect currency labels, tax template, and tax row; leave without saving.
- **Expected results:** Original baseline displays USD, Brazil ICMS 19%, and an On Net Total row with ICMS 19% - ADL at rate 19. Values are UI observations, not proof that tax is appropriate or correctly calculated. Changed defaults trigger baseline review.
- **Automation feasibility:** High after stakeholder approval of the baseline; do not turn current configuration into an unconditional business rule.

### QA-008 — Persist and submit an approved valid Purchase Order

- **Traceability:** REQ-07; R-01. **Priority:** P1. **Type:** positive system. **Basis:** HYP.
- **Preconditions:** Separate write/submission authorization; approved ADL supplier, purchasable stock item, UOM, warehouse, dates, rates, tax policy, and expected lifecycle state; known starting data.
- **Steps:** Create a PO with approved valid data; save; reopen; submit only under the approved lifecycle procedure; inspect persisted fields, totals, and state.
- **Expected results:** Proposed oracle: authorized valid data persists accurately and reaches the approved post-submission state, with independently calculated totals and traceable identity. Exact state and calculations must be approved before execution; they were not observed.
- **Automation feasibility:** Medium until fixtures, state oracle, and recovery are approved; future Playwright/Pytest transaction coverage.

### QA-009 — Reject incomplete purchasing documents

- **Traceability:** REQ-09; R-01, R-02. **Priority:** P1. **Type:** negative system. **Basis:** HYP derived from OBS required markers.
- **Preconditions:** Write attempts explicitly authorized; controlled data; approved required-field rules and expected validation messages/persistence policy.
- **Steps:** For PO and PR separately, omit one approved mandatory field at a time while satisfying the others; attempt Save; inspect feedback and whether a document persisted.
- **Expected results:** Proposed oracle: save is blocked for the omitted mandatory input and actionable feedback is shown, without unintended persistence. Exact client/server response remains unverified. Supplier/date/item and PO row-required fields are candidates, not assumed equivalent validation paths.
- **Automation feasibility:** Medium; parameterize independent cases after confirming constraints. Never execute these Save attempts under read-only authorization.

### QA-010 — Receive a Purchase Order in full with traceable references

- **Traceability:** REQ-07; R-01, R-02. **Priority:** P1. **Type:** positive integration. **Basis:** HYP.
- **Preconditions:** Approved submitted ADL PO, for example 10 units of one stock item; no prior receipts; approved receiving workflow and reference rules; write authorization.
- **Steps:** Use the approved PO-to-PR workflow; inspect mapped supplier, item, UOM, quantities, and references; receive the full approved quantity in the designated warehouse; save/submit; reopen both documents.
- **Expected results:** Proposed oracle: references and approved source values remain traceable; received/outstanding quantities reconcile to the order; states match approved rules. Mapping actions and exact states were not observed and require confirmation.
- **Automation feasibility:** Medium after workflow and deterministic fixtures are established. Reuse resulting receipt only where test isolation permits.

### QA-011 — Receive a Purchase Order partially, then complete it

- **Traceability:** REQ-08; R-02, R-04. **Priority:** P1. **Type:** partial-receipt integration. **Basis:** HYP.
- **Preconditions:** Approved PO for an illustrative 10 units; zero prior receipts; known warehouse starting quantity B; same stock UOM; no concurrent movements; approved partial-receipt and posting rules; write authorization.
- **Steps:** Receive/submit 4 units; inspect PO, PR, and voucher-linked ledger results. Receive/submit the remaining 6 units; inspect both receipts, PO quantities, and ledger again.
- **Expected results:** Proposed oracle, subject to approval: first receipt leaves 6 outstanding and increases accepted stock from B to B+4; second leaves zero outstanding and stock B+10. Both receipt references remain distinguishable and no quantity is double-counted. Exact statuses, posting timing, and valuation expectations require confirmation.
- **Automation feasibility:** Medium; highest-value transactional candidate after full-receipt baseline. Independent reconciliation is required, not only status checks.

### QA-012 — Reconcile receipt submission with Stock Ledger

- **Traceability:** REQ-08; R-04. **Priority:** P1. **Type:** integration / reconciliation. **Basis:** HYP supported by Maintain Stock UI guidance.
- **Preconditions:** Authorized stock-item receipt with approved accepted quantity Q, warehouse, UOM, posting window, and valuation oracle; starting balance B; no concurrent movements.
- **Steps:** Record starting report state; submit the receipt under the approved procedure; filter Stock Ledger by ADL, warehouse, item, date window, and receipt voucher; compare document and report data.
- **Expected results:** Proposed oracle: receipt-linked net accepted movement equals Q and ending quantity equals B+Q in the same UOM; company, warehouse, and voucher references agree. Use an independently approved valuation calculation; do not assume FIFO or a specific ledger row count.
- **Automation feasibility:** Medium; report readiness, posting behavior, and independent oracle must be confirmed first.

### QA-013 — Reconcile accepted and rejected goods

- **Traceability:** REQ-08; R-02, R-04. **Priority:** P1. **Type:** integration / exception handling. **Basis:** HYP.
- **Preconditions:** Approved receiving policy for an illustrative 10 units, 8 accepted and 2 rejected; approved distinct eligible warehouses and starting balances; explicit transaction authorization.
- **Steps:** Record accepted/rejected quantities and warehouses in the approved receipt workflow; save/submit; inspect receipt references, PO quantities, and warehouse-specific ledger results.
- **Expected results:** Proposed oracle: accepted/rejected allocations and ledger effects match the approved policy without double counting. Whether rejected units count toward PO completion, how they are valued, and how follow-up receipt works must be decided before execution; no fixed result is asserted here.
- **Automation feasibility:** Medium/low until rejection policy and ledger oracle are approved.

### QA-014 — Validate invalid quantities and excess receipt policy

- **Traceability:** REQ-09; R-01, R-02, R-05. **Priority:** P1. **Type:** negative / boundary. **Basis:** HYP.
- **Preconditions:** Authorized isolated data; known outstanding PO quantity; approved rules for zero/negative quantities, UOM precision, and any over-receipt tolerance.
- **Steps:** In separate cases, attempt a non-return zero quantity, a negative quantity, and a quantity just beyond the approved receiving limit; inspect save/submit feedback and persistence/ledger effects.
- **Expected results:** Outcome must match the approved policy. Proposed oracle: invalid input cannot produce unintended document or stock changes. Do not assume every zero/negative value is universally forbidden or that over-receipt tolerance is zero; boundaries and exact responses remain unverified.
- **Automation feasibility:** Medium after policy approval; independently parameterized cases with authorized recovery.

## First automation sequence

Start with **QA-001 → QA-002 → QA-003 → QA-004 → QA-005**. They establish navigation, priority form contracts, purchasing list vocabulary, and report accessibility without requiring transaction creation. This sequence prioritizes feasible read-only coverage, not proof of procurement correctness. Execute QA-006 and QA-007 next after confirming their baseline preconditions. Transactional scenarios remain gated by the strategy's entry criteria.

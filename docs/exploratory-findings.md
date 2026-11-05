# ERPNext Enterprise QA Automation — Exploratory Findings

> Historical exploration/design baseline. Later implemented coverage and observed
> executions are indexed in [evidence.md](evidence.md). Hypotheses below describe
> this original stage and are not the current automation execution report.

## Evidence context

Source: the diagnostic and authenticated functional exploration recorded in this conversation, dated 4 November 2026. This document preserves the observations already obtained; no additional application exploration or test execution was performed for this documentation stage.

The exploration used the local interface in read-only mode. Empty unsaved forms were opened to inspect fields and tabs; no fields were filled and no Save, Submit, Cancel, Delete, or Create New operation was executed. The existing Stores warehouse form was opened through its Edit navigation action, but no values were edited or saved.

**OBS** denotes observed UI behavior. **UI guidance** denotes displayed explanatory text, not an executed business rule. **HYP** denotes a rule or effect awaiting approval and verification. Scenario IDs refer to [test-scenarios.md](test-scenarios.md); risk and requirement IDs refer to [test-strategy.md](test-strategy.md).

## Confirmed functional observations

| Finding | Observed evidence | Traceability |
|---|---|---|
| F-01 — Local connectivity | HTTP 200 and a rendered login page were observed during diagnosis. Docker read access subsequently worked after sandbox elevation. ERPNext containers used image frappe/erpnext:v16.53.0. | R-06; REQ-01; QA-001 |
| F-02 — Authenticated access | An existing authenticated session opened Buying and Stock. No password was entered or recorded during exploration. Exact session username and default-password validity were not independently checked. | R-06; REQ-01; QA-001 |
| F-03 — Buying navigation | Supplier, Material Request, Request for Quotation, Supplier Quotation, PO, PR, Purchase Invoice, and purchasing reports were visible. Supplier, PO, and PR lists opened and showed no documents. | R-01, R-02; REQ-01–03; QA-001, QA-004 |
| F-04 — Stock navigation | Item, Warehouse, Material Request, Stock Entry, Stock Reconciliation, PR, Delivery Note, and inventory/serial/batch report links were visible. Not every linked feature was opened or exercised. | R-04, R-06; REQ-01; QA-001 |
| F-05 — Supplier structure | Full form tabs: Details, Accounting, Tax, Settings, Portal Users, More Info. Name and Type were marked required; Type options included Company, Individual, Partnership. Group, Country, currency, price list, payment terms, tax fields, and restriction flags were exposed. Country defaulted to Brazil on the blank form. Quick entry exposed contact/address fields. | R-05; REQ-05; QA-009 supporting data |
| F-06 — Item structure | Tabs included Details, Accounting, UOM, Tax, Inventory, Purchasing, Sales, Manufacturing, Quality. Code, Group, and Default UOM were marked required. Blank defaults included Nos, Maintain Stock checked, and Allow Purchase checked. Purchasing exposed purchase UOM, minimum quantity, safety stock, lead time, and supplier references. Accounting exposed company/warehouse defaults. | R-05; REQ-05; QA-008–014 supporting data |
| F-07 — Item availability | Active-item route included disabled=0 and returned No Item found. Workspace displayed zero active items. Clearing the list filter was attempted, but its resulting item population was not captured before navigating away; absence of disabled items is not established. | R-05; REQ-05; transactional fixture prerequisite |
| F-08 — ADL warehouse hierarchy | Company Atlas Distribution Ltd; All Warehouses - ADL above Finished Goods, Goods In Transit, Stores, Work In Progress. Workspace displayed five warehouses. Stores was enabled, linked to ADL, and had All Warehouses - ADL as parent. Account, rejected-warehouse indicator, addresses, and contacts were exposed. | R-05; REQ-05; QA-006 |
| F-09 — Warehouse guard | Add Warehouse without a selected group displayed Select a group Warehouse first. After selecting the group, a blank dialog opened with required Name and Company and an Is Group option. Nothing was created. | R-05; REQ-05; QA-006 |
| F-10 — PO form | Not Saved; Details, Address & Contact, Terms, More Info. Required markers: Series, Supplier, Date; item Code, Required By, Quantity, UOM. Target warehouse, rates, totals, taxes, and discounts were exposed. | R-01; REQ-02; QA-002 |
| F-11 — PR form | Not Saved; same four tab names as PO. Required markers: Series, Supplier, Date, Posting Time, item Code. Accepted/rejected quantities and warehouses, Supplier Delivery Note, Edit Posting Date and Time, Apply Putaway Rule, and totals were exposed. Is Return and Is Subcontracted were disabled in the inspected initial form. | R-02; REQ-03; QA-003 |
| F-12 — Status vocabulary | PO filter exposed Draft, On Hold, To Pay, To Receive and Bill, To Bill, To Receive, Completed, Cancelled, Closed, Delivered. PR exposed Draft, Partly Billed, To Bill, Completed, Return, Return Issued, Cancelled, Closed. No transitions were exercised. | R-01, R-02; REQ-02–03; QA-004 |
| F-13 — Financial defaults | Blank PO/PR forms displayed USD totals, Brazil ICMS 19% template, and an On Net Total tax row referencing ICMS 19% - ADL at rate 19. Nonzero calculations were not exercised. | R-03; REQ-06; QA-007 |
| F-14 — Stock Ledger | Opened with ADL company, From/To Date, Warehouses, Items, Voucher # and other filters. For 4 October–4 November 2026 it displayed Nothing to show. This does not establish an empty ledger for all dates or scopes. | R-04; REQ-04; QA-005 |
| F-15 — Automation tooling | Integrated browser supplied Playwright interaction APIs; semantic links, tabs, and buttons were usable. Some labels appeared as generic text. Standalone playwright and @playwright/test packages were not resolved from the project during diagnosis. Pytest readiness was not checked. | R-06; QA-001–007 |

## Rules not yet validated

The following are **not confirmed operational results**:

- Required-marker enforcement, validation messages, client/server consistency, and persistence behavior (QA-009).
- PO save/submit lifecycle and exact state transitions (QA-008).
- PO-to-PR mapping, supplier/item/UOM inheritance, and reference integrity (QA-010).
- Partial-receipt balances, remaining quantities, completion criteria, and multiple-receipt behavior (QA-011).
- Stock posting timing, voucher linkage, quantity reconciliation, valuation, and company/warehouse isolation (QA-012).
- Rejected-goods allocation, valuation, and effect on PO completion (QA-013).
- Quantity precision, zero/negative handling, over-receipt tolerance, duplicate prevention, and date constraints (QA-014 and future policy-driven scenarios).
- Currency suitability, tax applicability, rounding, and nonzero amount calculations (QA-007 and future approved financial tests).
- Cancellation/return reversals, concurrent operations, and role-specific permissions; these require additional scenario design after the baseline workflow is approved.

### Displayed guidance requiring operational verification

- Maintain Stock says transactions generate stock ledger entries; this was not demonstrated.
- Supplier guidance says disabled suppliers are hidden from new selection and frozen suppliers restrict transactions, with a role-related exception. No supplier restriction was exercised.
- Supplier settings expose invoice-without-PO and invoice-without-PR exceptions; effective enforcement is unknown.
- Warehouse guidance describes rejected-material storage and fallback to parent/company accounts; no posting verified these rules.
- Item inventory/purchasing guidance describes negative stock, reorder calculations, and drop shipping; none was transaction-tested.

## Exploration limitations

- No populated PO or PR was available in the inspected lists; no saved Supplier was available there either. Lifecycle controls and existing-document relationships could not be examined.
- Read-only authorization excluded saving, submitting, cancelling, deleting, imports, and configuration changes. Validation attempts that could write were intentionally not executed.
- Blank forms expose only their initial conditions. Conditional fields, link filtering, populated item-row details, and server responses may differ with real data.
- Workspace figures and empty states are dated UI observations, not independent database audits. No database/API write or backend reconciliation was performed.
- No independent internal version, exact session identity, role matrix, browser matrix, or runtime/dependency inventory for a Python suite was established.
- One semantic click on a collapsed PO information section timed out; native accessibility interaction subsequently expanded it. This is a locator/tool reliability observation, not evidence of an ERPNext defect.
- No screenshots or traces are attached to these documents. Evidence is the conversation's recorded interface observations; these notes must not be represented as a completed formal test run.

## Pending risks and questions

| Risk | Question requiring resolution | Needed before |
|---|---|---|
| R-01 | What approved PO submission states, date rules, and mapping behavior should be asserted? | QA-008–010 execution |
| R-02 | Are partial receipts allowed; what tolerances and duplicate controls apply; how do rejected units affect outstanding quantities? | QA-010, QA-011, QA-013, QA-014 execution |
| R-03 | Are USD and Brazil ICMS 19% intentional for ADL; what rates, rounding, and totals form the oracle? | Treating defaults as acceptance rules and testing nonzero totals |
| R-04 | What posting timing, valuation method, starting balances, and ledger reconciliation rules apply? | QA-011–013 execution |
| R-05 | Which approved supplier, stock item, UOM, warehouse, and eligibility settings should fixtures use? | Any transactional test |
| R-06 | Which verified account and future least-privilege role should automation use; what dependencies are approved? | Authentication automation and implementation |
| R-01–06 | Who approves mutation, recovery, cleanup, and residual-risk acceptance? | Any write-capable execution |

No confirmed defect was established. Unresolved questions are test-design inputs, not product failures.

# Initial commit preparation audit — 2026-11-04

## Scope and verdict

The publication set contains the test framework, its pinned dependencies, an
offline-only GitHub workflow and English documentation. The first commit is prepared
for owner review; no commit, remote repository, push or hosted workflow run is made
by this audit. The follow-up local release preparation records the owner-approved MIT License,
Copyright (c) 2026 Yud Remijo. No remote publication is authorized by this record.

## Changes from the final audit

- README now leads with the procurement/inventory risk, explains the 10 → 4 + 6
  workflow, distinguishes UI/API oracles, and separates offline, browser, integration
  and transactional execution. Local historic results are not presented as hosted CI.
- Personal absolute Windows paths were replaced by generic workspace references.
  Historical functional documents are labelled as the original exploration/design
  baseline and link to later execution evidence, without rewriting their observations.
- The retired second-stack `infra/` prototype is ignored and retained locally. It is
  not a validated deployment deliverable and is unnecessary for this framework/CI.
  No local infrastructure, backup or execution evidence was deleted or modified.
- `.gitattributes` normalizes publication text to LF across Windows/Linux.
- The checker can inspect exact index blobs with `--staged`, including syntax and
  secret-pattern checks, rather than accidentally approving a different working copy.
  It rejects private/generated paths, personal user paths and unsupported Git modes.
- A local offline test proves that index inspection reads staged content even when
  the working copy differs. An initial CRLF fixture mismatch was corrected with
  explicit LF bytes; the auditor intentionally does not rewrite staged content.
- Workflow YAML is parsed with the already-installed Playwright YAML utility and
  bundled Node executable; no new dependency or browser installation is needed.
- Removed one unused import. Approved business assertions, lifecycle actions and
  scenario data were not refactored or reexecuted.
- Added an evidence index and third-party notices. No vendored third-party source
  was identified in the approved set; installed dependency metadata was inspected.

## Validation performed in this phase

| Check | Observed result |
|---|---|
| Offline Pytest with ERPNEXT process variables absent and nonexistent browser path | 18 passed, 10 deselected in 10.75 seconds |
| Project Python AST, TOML, pin/config/ignore and focused secret checks | Passed |
| Workflow YAML parse and selected structural invariants | Passed |
| pip check | No broken requirements found |
| Integration selection, collection only | 6 selected, 22 deselected; not executed |
| Transaction gate without opt-in | 3 skipped, 25 deselected in 0.24 seconds |
| Exact local password comparison against candidates | Zero matches; no values displayed/copied |

No ERPNext test, Save, Submit or transaction was executed. No new PO/PR, invoice,
stock movement or Docker action was performed. The earlier documented UI/E2E results
remain historical evidence, not revalidated business behavior in this phase.

Staging validation uses `git diff --cached --check` and
`python scripts/check_project.py --staged`. The approved path list below is the
intended index allowlist and is checked against the actual index after staging.
Raw private files, archives, screenshots and traces are not in this list.

## Approved staging list

```text
.env.example
.gitattributes
.github/workflows/ci.yml
.gitignore
LICENSE
README.md
THIRD_PARTY_NOTICES.md
config/diagnostics.py
config/execution_lock.py
config/settings.py
constraints-dev.txt
docs/ci-cd.md
docs/evidence.md
docs/exploratory-findings.md
docs/negative-test-automation.md
docs/release-audit.md
docs/test-scenarios.md
docs/test-strategy.md
docs/transactional-automation.md
pages/login_page.py
pages/navigation.py
pages/negative_validation.py
pages/procurement.py
pages/purchase_order.py
pyproject.toml
requirements-dev.txt
scripts/check_project.py
scripts/validate_workflow.py
tests/conftest.py
tests/negative/conftest.py
tests/negative/test_over_receipt.py
tests/negative/test_purchase_order_validation.py
tests/smoke/test_qa001_navigation.py
tests/smoke/test_qa002_purchase_order_form.py
tests/smoke/test_qa003_purchase_receipt_form.py
tests/transactions/conftest.py
tests/transactions/test_qa008_purchase_order_draft.py
tests/transactions/test_qa011_partial_receipt_e2e.py
tests/unit/test_execution_lock.py
tests/unit/test_local_diagnostics.py
tests/unit/test_offline_contract.py
```

## Remaining release decisions and technical limits

- Licensing was confirmed in the follow-up local preparation: MIT, Copyright (c)
  2026 Yud Remijo. Dependency notices are preserved separately. Git authorship must
  be explicitly confirmed independently of the copyright holder.
- Real GitHub Actions execution, Linux runner behavior and clean-runner package
  installation remain unverified. YAML parsing is not GitHub's complete schema
  validation. The parser's internal Playwright path must be checked on upgrades.
- The focused checker is not an exhaustive security scanner, formatter or type checker.
  Candidate/index review complements ignore rules; never force-add excluded data.
- The approved test contract uses named ADL masters, local numeric/date formats and
  approved fiscal defaults. QA-011 additionally protects four historic local records;
  running on a clean site requires addressing this documented data prerequisite.
- Transactions remain local, explicit and serial; the lock does not exclude manual
  users or another host. No automatic cleanup or resume is implemented.
- The logical backup has no verified independent restore. No reset/recovery claim
  is made. Integration and transactional CI remain outside the hosted offline job.

After owner review and authorship confirmation, rerun the staged audit and then use,
without treating this example as an executed action:

```text
git commit -m "Initial commit: ERPNext QA automation framework"
```

Create a remote and push only under a separate explicit publication authorization.

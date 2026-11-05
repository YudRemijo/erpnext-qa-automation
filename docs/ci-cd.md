# CI boundary, portability and publication readiness

## Pipeline design

`.github/workflows/ci.yml` runs on push and pull_request, with Python 3.12 on
ubuntu-24.04 and windows-2022. Both matrix jobs are mandatory. Permissions are
read-only, checkout does not persist credentials, and official Actions are pinned
to verified commit SHAs (checkout v6.0.1; setup-python v6.1.0). There is a job timeout
and superseded branch runs can be cancelled. No secrets, Docker, ERPNext services,
browser installation, deployment or automatic artifact publication is configured.

Each job installs exact direct dependencies with the resolved transitive constraints,
runs `pip check`, runs `python scripts/check_project.py`, then runs
`python -m pytest -m offline -v --junitxml=reports/offline.xml`. The JUnit file remains
on that ephemeral runner; no action uploads potentially sensitive local artifacts.
Required steps have no continue-on-error. An empty selection exits unsuccessfully.

The workflow is **CI, not CD**. No deployment target has been approved. A green job
means offline checks passed on that runner, not that ERPNext or procurement passed.
GitHub-hosted localhost belongs to the runner, not to the developer's ERPNext.

Action versions were verified with read-only `git ls-remote` against the official
repositories. References: [checkout](https://github.com/actions/checkout),
[setup-python](https://github.com/actions/setup-python). The first hosted execution and its corrected results are recorded in
[First hosted execution](#first-hosted-execution). Offline CI does not validate ERPNext.

## Capability classification and guards

- `offline`: no browser runtime, ERPNext, credential loading, network or external
  services. Locale parsing, lock behavior and execution/publication contracts qualify.
- `browser`: the synthetic-secret trace test needs Chromium even though it has no
  ERPNext/network dependency. It is excluded from the hosted offline job.
- `integration`: selected by an actual dependency on `authenticated_page`. Smoke
  checks are read-only; NEG-001/002/003 attempt invalid Saves. They are not equivalent
  to a universally read-only API session.
- `transactional`: additive opt-in for QA-008, QA-011 and NEG-004. Collection adds
  Skip without `--run-transactions`. These tests are not selected or executed by CI.

Collection rejects an offline marker combined with authenticated settings, browser
fixtures or integration/transaction/browser markers. Offline execution also blocks
socket connections/DNS, Settings.load and direct synchronous browser launch. CI=true
rejects `--run-transactions` before collection and rejects any selected non-offline
test after marker deselection. These are regression-tested failure paths, including
an invalid CLI option. No failure path initializes authentication.

Commands for selection inspection only:

```powershell
.\.venv\Scripts\python.exe -m pytest --collect-only -q -m offline
.\.venv\Scripts\python.exe -m pytest --collect-only -q -m "integration and not transactional"
.\.venv\Scripts\python.exe -m pytest --collect-only -q -m transactional
```

Current selections: 19 offline, 6 integration without transactions, 3 transactional,
plus 1 separate browser diagnostic. No offline test depends on an installed Chromium
or reads the real `.env`. Installing the Playwright Python package is not installing
a browser. A local proof removed ERPNEXT variables from the child process, set CI=true
and pointed PLAYWRIGHT_BROWSERS_PATH at a verified nonexistent directory.

## Lock portability

`config/execution_lock.py` lazily imports `msvcrt` on Windows or `fcntl` on POSIX.
It acquires a nonblocking exclusive lock, releases on exceptions and refuses unknown
or unavailable locking backends. File contents and inode are preserved rather than
unlinking a lock used by another process. Existing Windows byte-range protection
remains in place; POSIX uses flock. Tests exercise competing descriptors, exception
release and an unsupported backend without any ERPNext operation.

The Windows backend is locally validated, and both Windows and POSIX lock checks
passed in the hosted offline run recorded below. Local file locking is not a distributed database lock;
never run transactions from multiple hosts or concurrently with manual operations.
Parallel Pytest workers remain forbidden for transaction/negative attempts.

## Dependency and tooling decisions

Python 3.12; observed local patch 3.12.10. Existing direct pins are unchanged:
pytest 9.2.0, playwright 1.64.1, pytest-playwright 0.10.0. `constraints-dev.txt` records
the installed dependency closure with Python 3.12 Windows/Linux markers considered.
It constrains transitive resolution without introducing another dependency manager.
Hosted-runner installation was verified in the run below on Linux Python 3.12.15
and Windows Python 3.12.10. Other Python patches and dependency upgrades need fresh
validation. Package artifacts are not hash-pinned.

No new lint/formatting/YAML dependency was installed. `scripts/check_project.py` uses
AST parsing for candidate Python sources, tomllib for Pytest config, exact-pin checks,
Git ignore probes, restricted candidate/secret-pattern review, staged-blob inspection
and a focused workflow contract. This is **not** actionlint, a YAML parser, an
exhaustive secret scanner, a type checker or a guarantee against malicious source.
No actionlint executable was available locally. `scripts/validate_workflow.py` now
parses YAML and selected structural invariants using the existing pinned Playwright
package's bundled parser and Node runtime, without installing tooling or a browser.
This internal parser path is version-sensitive and must be checked on upgrades;
GitHub's complete workflow validation and hosted execution remain pending.

## Security audit

The local Git index had **0 tracked files**, no commits and no remote configured at
the time of audit. Therefore no committed secret was found in existing history,
during that initial audit. The final staged review is recorded in
[release-audit.md](release-audit.md). The checker reviews tracked
files plus all non-ignored untracked candidates and must be rerun after staging.
Ignore rules do not protect files that were already tracked or force-added.

Confirmed:

- Real `.env` exists locally and is ignored; values were not printed or copied.
- `.env.example` contains placeholders for both account and password, plus a local
  URL example. The retired local `infra/` proposal is excluded from publication.
- artifacts/, reports/, screenshots/, videos/, traces/, browser states, keys, dumps,
  logical backups and temporary exports are excluded. Existing evidence was preserved.
- The authorized backup directory is outside the repository. No backups were read,
  copied, restored or removed during this task.
- Real site_config/common_site_config files are ignored, without a publishable template
  exception. The retired, unvalidated second-stack prototype remains local under
  ignored `infra/` and is not a dependency of the checker or hosted workflow.
- Current ignored diagnostics are local. Failure traces retain actions/screens only;
  DOM/network/source recording is disabled and extra headers are cleared before
  capture. The synthetic-secret browser check must continue passing on upgrades.
- Personal absolute Windows paths were redacted from the historical strategy.
  Functional observations were preserved; runtime paths remain repository-relative.

The focused scanner reports only filenames/lines, never matched values. It cannot
certify absence of all possible secrets or inspect ignored private backup contents.
Review the staged diff before an initial commit; do not use `git add -f` for private
files. Licensing and repository visibility require an owner decision before publishing.

## Environment and data limitations

Smoke/negative UI checks require an independently provisioned ERPNext and the exact
ADL master/tax policy contract listed in README. No CI seed or Docker stack is created.
Transactional origins remain restricted to localhost:8080; no tunnel/public exposure
is added. The backup still lacks a verified independent restore.

QA-011 currently protects four historical local records by reading them explicitly:
PUR-ORD-2026-00001, PUR-ORD-2026-00002, MAT-PRE-2026-00001, MAT-PRE-2026-00002. This is
a real portability limitation for a clean ERPNext. This phase does not fabricate those
records or rewrite approved transactional semantics. Generalizing the preservation
baseline is a future targeted change requiring a separately authorized E2E run.
Other tests also depend on named ADL masters; another developer must provision them
deliberately. A passing offline job does not assert these prerequisites exist.

## Local validation record

- Project syntax/configuration/publication check: passed; no secret values printed.
- `pip check`: No broken requirements found.
- Offline selection proof: 17 passed, 10 deselected in 4.97 seconds, with no ERPNEXT
  process variables and a nonexistent browser runtime path.
- Invalid commands: CI transaction flag rejected; CI integration selection rejected;
  unknown CLI option rejected, all before test execution.
- The first offline attempt had temporary-directory permission errors in the Codex
  sandbox (14 passed, 3 setup errors). A unique workspace-local basetemp resolved
  the infrastructure issue; no production setting or OS permission was changed.
- An initial UI regression found a previously implicit assumption that Item Code's
  grid editor would already be open. The failure screenshot showed a closed row;
  API evidence confirmed no new/changed documents or stock. The helper now explicitly
  opens the named cell before filling it. Assertions and transaction oracles are unchanged.
- No QA-008, QA-011 or NEG-004 execution was performed. Only the non-persisting PO
  preparation path was exercised while validating the locator correction.

Failure evidence for the initial UI regression is retained locally under
`artifacts/negative-79dd834e-a48d-41a7-ad5d-b502fa858bc1/`; it is not uploaded by CI.
The completed CI-preparation regression results follow (historical, before final commit review).

- Final browser/integration selection excluding transactions: **7 passed,
  20 deselected in 52.70 seconds** (three negatives, three smoke tests, one browser
  diagnostic). Prior documents and stock remained unchanged in the negative guards.
- All three transactional cases were excluded from actual execution; no new business
  document, receipt submission or inventory movement was authorized or performed.
- Explicit transaction-gate check: **3 skipped, 24 deselected in 0.13 seconds**.
- Preserved real failure trace: ZIP integrity passed; network records empty, no DOM
  snapshots, no extra header metadata; post-login screenshot retained.

Files added in this phase: `.github/workflows/ci.yml`, `config/execution_lock.py`,
`constraints-dev.txt`, `scripts/check_project.py`, `tests/unit/test_execution_lock.py`,
`tests/unit/test_offline_contract.py`, `README.md`, and this document. Files updated:
`tests/conftest.py`, `tests/unit/test_local_diagnostics.py`, `pages/purchase_order.py`,
`pyproject.toml`, `.env.example`, `.gitignore`, and the two implementation guides
(`transactional-automation.md`, `negative-test-automation.md`). The original three
functional documents and Docker infrastructure were not modified.

## Publication checklist and next phase

1. Review the staged candidate list and rerun `python scripts/check_project.py`.
2. Choose license, repository name and visibility; confirm the copyright holder and licensing text.
3. Create the initial commit and publish only with separate owner authorization.
4. Observe the first real Actions run on both OS jobs; investigate any package/platform
   discrepancy before claiming portable CI success.
5. Keep ERPNext integration/manual transactions separate. Before enabling a dedicated
   transactional runner, validate restoration, prepare a reproducible data contract,
   generalize historical-record dependencies and define a single-writer execution window.


## First hosted execution

Public repository: https://github.com/YudRemijo/erpnext-qa-automation. The original
commit 53837b87219f87746f8429740d75c326bd9feaeb was published unchanged on main.

The [initial push run](https://github.com/YudRemijo/erpnext-qa-automation/actions/runs/41951872760)
failed workflow validation before either job started: job-level env referenced
`runner.temp`, where the runner context is unavailable. Local YAML parsing had
validated syntax but not this GitHub expression-context rule. No tests ran in that
failed workflow; it is not a passing CI result.

Commit a53a3ca7f5724ff1e50b679d31993163d83f4b91 replaced the browser sentinel path
with `github.workspace`, added a focused contract check and an offline regression
for the invalid context, and updated the public clone instructions. No test oracle
was weakened. The original commit remains in history; no force push was used.

The [corrected push run](https://github.com/YudRemijo/erpnext-qa-automation/actions/runs/41952077260)
completed successfully. The jobs and logs were read after completion:

| Runner | Python | Offline test result | Mandatory checks |
|---|---|---|---|
| ubuntu-24.04 | 3.12.15 | 19 passed, 10 deselected in 1.32 s | dependency install, pip check, project checker, YAML validation passed |
| windows-2022 | 3.12.10 | 19 passed, 10 deselected in 1.60 s | dependency install, pip check, project checker, YAML validation passed |

Both jobs ran `python -m pytest -m offline -v --junitxml=reports/offline.xml`.
Neither installed a browser nor accessed ERPNext; no transactional tests were run.
These are actual hosted offline results, not hosted UI/E2E coverage. No success
badge or screenshot has been fabricated. The read-only contents permission and
no-persisted-checkout-credentials settings remain unchanged.

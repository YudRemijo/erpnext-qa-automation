# Evidence index

This index distinguishes observed **local business executions** from actual hosted
**offline CI**. No hosted E2E result or public raw runtime archive is asserted. Artifacts stay ignored
because they may include session-adjacent information or environment-specific data.

| Coverage | Recorded evidence | Details |
|---|---|---|
| QA-008 Draft creation | One saved Draft, verified UI/API | [Transactional guide](transactional-automation.md) |
| QA-011 complete partial-receipt lifecycle | Local E2E passed in 34.85 seconds; PO00003, PR00003/00004; stock 10 → 20 | [Run record and reconciliation](transactional-automation.md#verified-execution--2026-11-04) |
| QA-011 dynamic baseline | One controlled E2E passed in 34.87 s; PO00005, PR00006/00007; stock 20 → 30; all 9 prior PO/PR documents preserved | [Dynamic baseline approval](transactional-automation.md#controlled-dynamic-baseline-approval-run--2026-11-04) |
| NEG-001/002/003 | Missing fields blocked by UI; zero quantity rejected by backend; no persisted documents | [Negative expected/actual results](negative-test-automation.md) |
| NEG-004 | PO00004 submitted; PR00005 Draft; HTTP 417 OverAllowanceError; physical stock unchanged | [Retained controlled execution](negative-test-automation.md#retained-controlled-execution) |
| CI preparation | Offline checks, marker selection and nontransactional local regression | [CI validation record](ci-cd.md#local-validation-record) |
| Hosted offline CI | 19 passed on Linux and 19 on Windows; corrected push run completed successfully | [First hosted execution](ci-cd.md#first-hosted-execution) |
| First commit preparation | Syntax, offline checks, exact-index audit and staging review | [Pre-commit audit](release-audit.md) |

Full IDs use the PUR-ORD-2026 and MAT-PRE-2026 naming series in the linked guides;
they identify fictitious records, not reusable inputs for a new execution.

## Inspecting local artifacts

QA-011 and negative runs create `artifacts/<scenario>-<UUID>/manifest.json`. A failed
post-login run may retain a screenshot and restricted actions/screens trace ZIP.
Manifests identify documents and checkpoints; do not retry Save/Submit just because
the UI timed out. Inspect the API state and recorded IDs first. Do not publish traces,
cookies, `.env`, backups or private site configuration as portfolio evidence.

The public record is the documented result and reproducible test logic, not an
attached private runtime archive. A collaborator must run against their own prepared
environment to obtain new UI/API evidence. Historical observations do not replace
the new environment's preconditions, approved tax policy or restore rehearsal.

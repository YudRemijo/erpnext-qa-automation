# Third-party notices and project licensing status

This project's original code is licensed under the MIT License, with
Copyright (c) 2026 Yud Remijo, as confirmed by the owner. See `LICENSE` for the
complete grant and conditions. The dependency notices below remain separate.

## Declared direct dependencies

The following projects are installed separately through pip; their source and binary
distributions are not vendored in this repository. Local installed package metadata
was inspected during the final audit.

| Dependency | Version | Reported license | Upstream |
|---|---|---|---|
| Pytest | 9.2.0 | MIT | https://github.com/pytest-dev/pytest |
| Playwright for Python | 1.64.1 | Apache-2.0 | https://github.com/microsoft/playwright-python |
| pytest-playwright | 0.10.0 | Apache License 2.0 | https://github.com/microsoft/playwright-pytest |

Transitive versions are recorded in `constraints-dev.txt`. Dependency installation
retains each distribution's own notices. Redistribution of dependency distributions
or browser binaries would require a separate license/notice review; they are excluded
here. The workflow parser uses Playwright's already-installed bundled YAML utility;
that utility is not copied into this project.

ERPNext and Frappe are separately provisioned systems under test, not included in
the repository. The documentation identifies installed-source locations used for
behavior investigation; it does not distribute the ERP application source. GitHub
Actions are referenced by upstream commit SHA rather than copied.

No third-party source files or substantial vendored snippets were identified in the
approved publication set. Standard API usage and testing patterns were reviewed as
project-authored framework code; this is not a provenance guarantee for future changes.
The retired infrastructure prototype, originally informed by upstream Compose
examples, is retained locally but excluded from the publication set.

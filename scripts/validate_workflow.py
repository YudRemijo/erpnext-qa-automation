"""Parse YAML with the existing pinned Playwright package's bundled YAML parser.

No browser, network or new dependency is used. This validates syntax and selected
structural invariants, not GitHub's complete Actions schema or a hosted execution.
The bundled parser is an internal dependency; upgrades must revalidate this script.
"""

import subprocess
import sys
from pathlib import Path

import playwright


ROOT = Path(__file__).resolve().parents[1]


def main():
    driver = Path(playwright.__file__).parent / "driver"
    node = driver / ("node.exe" if sys.platform == "win32" else "node")
    bundle = driver / "package/lib/utilsBundle.js"
    script = r"""
const fs = require('fs');
const yaml = require(process.argv[1]).yaml;
const doc = yaml.parseDocument(fs.readFileSync(process.argv[2], 'utf8'));
if (doc.errors.length) throw new Error('Workflow YAML syntax error');
const workflow = doc.toJS();
const fail = message => { throw new Error(message); };
if (JSON.stringify(workflow.on) !== JSON.stringify(['push', 'pull_request'])) fail('Unexpected triggers');
if (workflow.permissions?.contents !== 'read') fail('Permissions must be read-only');
if (Object.keys(workflow.jobs).join() !== 'offline') fail('Only offline job is approved');
const job = workflow.jobs.offline;
if (job.env?.CI !== 'true') fail('CI guard must be enabled');
if (Object.values(job.env || {}).some(v => String(v).includes('${{ runner.'))) fail('Runner context is unavailable in job-level env');
if (job.strategy?.matrix?.os?.length !== 2) fail('Expected two OS runners');
if (!job.steps.some(s => s.run?.startsWith('python -m pytest -m offline '))) fail('Offline command missing');
console.log('Workflow YAML syntax and selected structural invariants PASSED');
"""
    result = subprocess.run([str(node), "-e", script, str(bundle),
                             str(ROOT / ".github/workflows/ci.yml")], capture_output=True, text=True)
    if result.returncode:
        print("Workflow validation FAILED; check YAML, installed Playwright parser and approved structure")
        return 1
    print(result.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())

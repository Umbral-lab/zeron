#!/usr/bin/env python3
"""Read-only bootstrap diagnostics. This is NOT an inference launcher or guard."""
import argparse
import hashlib
import json
from pathlib import Path


def inspect(root):
    root = Path(root).resolve()
    errors = []
    manifest = json.loads((root / 'ops/bootstrap/import-manifest.json').read_text())
    for item in manifest['files']:
        path = root / item['destination']
        if not path.is_file():
            errors.append('Missing import: ' + item['destination'])
            continue
        original = path.read_bytes()[:item['original_bytes']]
        if hashlib.sha256(original).hexdigest() != item['sha256']:
            errors.append('Changed imported instructions: ' + item['destination'])
    if (root / 'repo').exists():
        errors.append('Staging directory repo/ still exists')
    required = ['docs/agent-prompts/02_GPT_WORKER.md',
                'docs/agent-prompts/03_SOL_AUDIT.md']
    missing = [path for path in required if not (root / path).is_file()]
    policy = json.loads((root / 'ops/policy.json').read_text())
    blockers = ['OPS-001 enforcement and independent review are not verified.',
                'No operator-owned effective policy, request ledger or leases verified.',
                'No assigned nightly task packet, run budget or deadline verified.']
    blockers.extend('Missing owner-supplied prompt: ' + path for path in missing)
    if not policy['models']['worker_a_runtime_identifier']:
        blockers.append('Worker A runtime identifier is unresolved.')
    return {'kind': 'bootstrap_diagnostic_only', 'import_count': len(manifest['files']),
            'import_integrity': 'FAIL' if errors else 'PASS', 'errors': errors,
            'unattended_inference': 'BLOCKED', 'blockers': blockers,
            'model_dispatches': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path,
                        default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    try:
        report = inspect(args.root)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'import_integrity': 'FAIL', 'unattended_inference': 'BLOCKED',
                          'error': str(exc), 'model_dispatches': 0}, indent=2))
        return 1
    print(json.dumps(report, indent=2))
    return int(bool(report['errors']))


if __name__ == '__main__':
    raise SystemExit(main())

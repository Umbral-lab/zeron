import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('preflight', Path(__file__).with_name('preflight.py'))
assert spec is not None and spec.loader is not None
preflight = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'ops/bootstrap').mkdir(parents=True)
        self.original = b'# Original instructions\n'
        (self.root / 'AGENTS.md').write_bytes(self.original)
        manifest = {'files': [{'destination': 'AGENTS.md',
                              'original_bytes': len(self.original),
                              'sha256': hashlib.sha256(self.original).hexdigest()}]}
        (self.root / 'ops/bootstrap/import-manifest.json').write_text(json.dumps(manifest))
        (self.root / 'ops/policy.json').write_text(json.dumps({
            'models': {'worker_a_runtime_identifier': None}}))

    def test_preserved_import_is_not_permission_to_launch(self):
        report = preflight.inspect(self.root)
        self.assertEqual(report['import_integrity'], 'PASS')
        self.assertEqual(report['unattended_inference'], 'BLOCKED')
        self.assertEqual(report['model_dispatches'], 0)
        self.assertTrue(any('03_SOL_AUDIT' in b for b in report['blockers']))

    def test_append_preserves_original(self):
        (self.root / 'AGENTS.md').write_bytes(self.original + b'\nSetup annotation\n')
        self.assertEqual(preflight.inspect(self.root)['import_integrity'], 'PASS')

    def test_changed_original_fails(self):
        (self.root / 'AGENTS.md').write_bytes(b'Changed instructions\n')
        self.assertEqual(preflight.inspect(self.root)['import_integrity'], 'FAIL')

    def test_missing_import_fails(self):
        (self.root / 'AGENTS.md').unlink()
        self.assertEqual(preflight.inspect(self.root)['import_integrity'], 'FAIL')

    def test_leftover_staging_fails(self):
        (self.root / 'repo').mkdir()
        self.assertEqual(preflight.inspect(self.root)['import_integrity'], 'FAIL')

    def test_present_prompts_do_not_satisfy_guards(self):
        prompts = self.root / 'docs/agent-prompts'
        prompts.mkdir(parents=True)
        for name in ['02_GPT_WORKER.md', '03_SOL_AUDIT.md']:
            (prompts / name).write_text('Owner-supplied fixture')
        report = preflight.inspect(self.root)
        self.assertFalse(any('Missing owner-supplied prompt' in b for b in report['blockers']))
        self.assertEqual(report['unattended_inference'], 'BLOCKED')


if __name__ == '__main__':
    unittest.main()

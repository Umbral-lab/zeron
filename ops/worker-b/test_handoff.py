"""Publication regression fixtures; no network or inference is used by these tests."""
import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('nightly_handoff', Path(__file__).with_name('zeron-nightly.py'))
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
import zeron_nightly_publish as pub


class FakeGitHub:
    """In-memory remote explicitly used only as a test fixture."""
    def __init__(self, wrong_actor=False):
        self.calls = []
        self.wrong_actor = wrong_actor
        self.issue = {}
        self.pr = {}
        self.content = ''

    def __call__(self, method, path, payload, deadline):
        self.calls.append((method, path, payload))
        user = {'login': 'wrong-fixture' if self.wrong_actor else pub.ACTOR}
        if method == 'GET' and '/git/commits/' in path:
            return {'tree': {'sha': 'b' * 40}}
        if method == 'POST' and path.endswith('/git/trees'):
            self.content = payload['tree'][0]['content']
            return {'sha': 'c' * 40}
        if method == 'POST' and path.endswith('/git/commits'):
            self.commit = payload
            return {'sha': 'd' * 40}
        if method == 'POST' and path.endswith('/git/refs'):
            return {'object': {'sha': payload['sha']}}
        if method == 'POST' and path.endswith('/issues'):
            self.issue = dict(payload, number=11, html_url='https://example.invalid/issues/11', user=user)
            return self.issue.copy()
        if method == 'POST' and path.endswith('/pulls'):
            self.pr = dict(payload, number=12, html_url='https://example.invalid/pull/12',
                           user=user, head={'sha': 'd' * 40})
            return self.pr.copy()
        if method == 'PATCH' and path.endswith('/issues/11'):
            self.issue.update(payload)
            return self.issue.copy()
        if method == 'GET' and path.endswith('/issues/11'):
            return self.issue.copy()
        if method == 'GET' and path.endswith('/pulls/12'):
            return self.pr.copy()
        if method == 'GET' and '/git/ref/heads/' in path:
            return {'object': {'sha': 'd' * 40}}
        if method == 'GET' and '/contents/' in path:
            return {'content': base64.b64encode(self.content.encode()).decode()}
        raise AssertionError('Unexpected fixture API request: ' + method + ' ' + path)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        state = patch.object(m, 'STATE', self.root)
        state.start()
        self.addCleanup(state.stop)
        self.receipt = self.root / '2026-11-01.json'
        self.result = self.root / '2026-11-01-result.json'
        self.record = {'date': '2026-11-01', 'source': 'a' * 40, 'run_id': 'zeron:B:2026-11-01',
                       'requests': 4, 'reserved_generated': 4000,
                       'finished_at': '2026-11-01T00:01:00+00:00', 'returncode': 0}
        m.save(self.receipt, self.record)

    def finish(self, packet, fake, code=0):
        if packet is not None:
            m.save(self.result, packet)
        with patch.object(m, 'reserve', side_effect=AssertionError('Publication used inference')) as inference:
            with patch.object(m, 'publish', lambda r, p, d: pub.publish(r, p, d, call=fake)):
                result = m.finish_run(self.receipt, self.result, code, time.monotonic() + 90)
            inference.assert_not_called()
        return result, json.loads(self.receipt.read_text()), json.loads(self.result.read_text())

    def test_regression_iteration_exhaustion_is_saved_and_published_partial(self):
        fake = FakeGitHub()
        packet = pub.checkpoint({'completed': False, 'final_response': 'Partial source evidence from capped run.'})
        code, receipt, packet = self.finish(packet, fake)
        self.assertEqual(code, 2)
        self.assertEqual(receipt['state'], 'partial')
        self.assertEqual(receipt['requests'], 4)
        self.assertEqual(packet['handoff_status'], 'published')
        self.assertTrue(fake.pr['draft'])
        self.assertIn('Partial source evidence', (self.root / '2026-11-01-report.md').read_text())
        self.assertFalse((self.root / 'last-completed-source.json').exists())

    def test_explicit_complete_report_requires_verified_handoff(self):
        fake = FakeGitHub()
        packet = pub.checkpoint({'completed': True, 'final_response': 'TASK_STATUS: COMPLETE\nVerified bounded report.'})
        code, receipt, packet = self.finish(packet, fake)
        self.assertEqual(code, 0)
        self.assertEqual(receipt['state'], 'complete')
        self.assertFalse(fake.pr['draft'])
        self.assertEqual(fake.commit['author']['name'], 'Umbral Agent')
        self.assertTrue((self.root / 'last-completed-source.json').exists())

    def test_zero_exit_without_checkpoint_is_partial_not_success(self):
        code, receipt, packet = self.finish(None, FakeGitHub())
        self.assertEqual(code, 2)
        self.assertEqual(receipt['state'], 'partial')
        self.assertEqual(packet['handoff_status'], 'published')

    def test_publication_failure_keeps_report_and_fails_run(self):
        def failed(*args):
            raise RuntimeError('Fixture API unavailable')
        packet = pub.checkpoint({'completed': True, 'final_response': 'TASK_STATUS: COMPLETE\nPreserve this report.'})
        code, receipt, packet = self.finish(packet, failed)
        self.assertEqual(code, 2)
        self.assertEqual(receipt['state'], 'partial')
        self.assertEqual(packet['handoff_status'], 'failed')
        self.assertIn('Preserve this report', Path(packet['local_report']).read_text())

    def test_wrong_remote_actor_is_not_claimed_as_published(self):
        packet = pub.checkpoint({'completed': True, 'final_response': 'TASK_STATUS: COMPLETE\nReport.'})
        code, receipt, packet = self.finish(packet, FakeGitHub(wrong_actor=True))
        self.assertEqual(code, 2)
        self.assertEqual(packet['handoff_status'], 'failed')

    def test_nonzero_worker_exit_cannot_claim_complete(self):
        packet = pub.checkpoint({'completed': True, 'final_response': 'TASK_STATUS: COMPLETE\nReport.'})
        code, receipt, packet = self.finish(packet, FakeGitHub(), code=124)
        self.assertEqual(code, 2)
        self.assertEqual(packet['status'], 'partial')

    def test_completion_marker_alone_cannot_override_incomplete_agent(self):
        packet = pub.checkpoint({'completed': False, 'final_response': 'TASK_STATUS: COMPLETE\nSummary after budget exhaustion.'})
        self.assertEqual(packet['status'], 'partial')

    def test_checkpoint_and_report_permissions_are_private(self):
        _, _, packet = self.finish(None, FakeGitHub())
        self.assertEqual(self.result.stat().st_mode & 0o777, 0o600)
        self.assertEqual(Path(packet['local_report']).stat().st_mode & 0o777, 0o600)

    def test_expired_publication_deadline_does_not_call_network(self):
        with patch.object(pub.subprocess, 'run') as network:
            with self.assertRaises(TimeoutError):
                pub.api('POST', 'fixture', {}, time.monotonic() - 1)
            network.assert_not_called()

    def test_secret_material_is_redacted_or_refused(self):
        self.assertNotIn('ghp_' + 'a' * 30, pub.sanitize('ghp_' + 'a' * 30))
        with self.assertRaises(ValueError):
            pub.sanitize('-----BEGIN RSA PRIVATE KEY-----\nfixture')


if __name__ == '__main__':
    unittest.main()

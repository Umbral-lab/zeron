"""Candidate review regressions. All GitHub objects/logs here are explicit fixtures."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('audit_launcher', Path(__file__).with_name('zeron-nightly.py'))
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
import zeron_audit as audit
import zeron_nightly_publish as pub


def candidate():
    paths = ['crates/update/src/lib.rs']
    return {'number': 19, 'base': 'b' * 40, 'head': 'a' * 40,
            'url': 'https://example.invalid/pull/19', 'title': 'Fixture candidate',
            'paths': paths, 'code_paths': paths}


class FixtureGitHub:
    def __init__(self, head='a' * 40, actor=pub.ACTOR):
        self.calls = []
        self.actor = actor
        self.pr = {'state': 'open', 'head': {'sha': head},
                   'user': {'login': audit.BUILDER}, 'html_url': 'https://example.invalid/pull/19'}
        self.review: dict = {}

    def __call__(self, method, path, payload, deadline):
        self.calls.append((method, path, payload))
        if method == 'GET' and path.endswith('/pulls/19'):
            return self.pr
        if method == 'POST' and path.endswith('/pulls/19/reviews'):
            state = {'APPROVE': 'APPROVED', 'REQUEST_CHANGES': 'CHANGES_REQUESTED', 'COMMENT': 'COMMENTED'}[payload['event']]
            self.review = dict(payload, id=123, html_url='https://example.invalid/review/123',
                               commit_id=payload['commit_id'], state=state, user={'login': self.actor})
            return self.review.copy()
        if method == 'GET' and path.endswith('/reviews/123'):
            return self.review.copy()
        raise AssertionError('Unexpected fixture route: ' + method + ' ' + path)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = {'date': '2026-11-08', 'run_id': 'zeron:B:2026-11-08',
                       'audit_contract': audit.CONTRACT, 'source': 'a' * 40,
                       'candidate': candidate(), 'returncode': 0, 'requests': 3, 'reserved_generated': 3000}
        self.record['checks'] = []
        for i, argv in enumerate(audit.check_plan(candidate()['paths'])):
            log = self.root / str(i)
            raw = b'test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out\n'
            log.write_bytes(raw)
            self.record['checks'].append({'argv': argv, 'status': 'passed', 'returncode': 0,
                                          'log': str(log), 'sha256': hashlib.sha256(raw).hexdigest()})
        self.review = {'head': 'a' * 40, 'verdict': 'APPROVE', 'summary': 'Fixture inspection',
                       'inspected_files': candidate()['code_paths'], 'findings': [], 'limitations': []}

    def assess(self):
        return pub.checkpoint({'completed': True, 'final_response': json.dumps(self.review)}, self.record)

    def test_complete_marker_without_tests_cannot_complete(self):
        packet = pub.checkpoint({'completed': True, 'final_response': 'TASK_STATUS: COMPLETE\nOld source report.'})
        self.assertEqual(packet['status'], 'partial')
        self.assertEqual(packet['verdict'], 'INCOMPLETE')

    def test_pinned_coverage_and_real_log_gate_can_approve_fixture(self):
        self.assertEqual(self.assess()['verdict'], 'APPROVE')
        self.assertEqual(self.assess()['status'], 'complete')

    def test_missing_checks_cannot_approve(self):
        self.record['checks'] = []
        self.assertEqual(self.assess()['verdict'], 'INCOMPLETE')

    def test_subset_of_required_checks_cannot_approve(self):
        self.record['checks'].pop()
        self.assertEqual(self.assess()['verdict'], 'INCOMPLETE')

    def test_timeout_and_not_run_cannot_approve(self):
        for status in ['timeout', 'not_run', 'failed']:
            self.record['checks'][0]['status'] = status
            self.record['checks'][0]['returncode'] = 124
            self.assertEqual(self.assess()['verdict'], 'INCOMPLETE')

    def test_tampered_log_cannot_approve(self):
        Path(self.record['checks'][0]['log']).write_text('different log')
        self.assertEqual(self.assess()['verdict'], 'INCOMPLETE')

    def test_zero_test_success_is_not_runtime_evidence(self):
        check = self.record['checks'][0]
        raw = b'test result: ok. 0 passed; 0 failed; 0 ignored\n'
        Path(check['log']).write_bytes(raw)
        check['sha256'] = hashlib.sha256(raw).hexdigest()
        self.assertEqual(self.assess()['verdict'], 'INCOMPLETE')

    def test_wrong_head_missing_coverage_and_ui_gap_cannot_approve(self):
        for key, value in [('head', 'c' * 40), ('inspected_files', []), ('limitations', ['No rendered evidence'])]:
            old = self.review[key]
            self.review[key] = value
            self.assertEqual(self.assess()['verdict'], 'INCOMPLETE')
            self.review[key] = old
        self.record['candidate']['requires_rendered_ui'] = True
        self.assertEqual(self.assess()['verdict'], 'INCOMPLETE')

    def test_failed_test_with_material_finding_is_changes_requested_not_pass(self):
        self.review.update(verdict='CHANGES_REQUESTED', findings=[{'description': 'Fixture blocker'}])
        c = self.record['checks'][0]
        raw = b'test result: FAILED. 0 passed; 1 failed; 0 ignored\n'
        Path(c['log']).write_bytes(raw)
        c.update(status='failed', returncode=101, sha256=hashlib.sha256(raw).hexdigest())
        packet = self.assess()
        self.assertEqual(packet['verdict'], 'CHANGES_REQUESTED')
        self.assertEqual(packet['status'], 'complete')  # Review completed, not product PASS.

    def test_review_goes_only_to_existing_pr_and_reads_back(self):
        fake = FixtureGitHub()
        packet = self.assess()
        pub.publish(self.record, packet, time.monotonic() + 30, call=fake)
        self.assertEqual(packet['handoff_status'], 'published')
        writes = [(method, path) for method, path, _ in fake.calls if method != 'GET']
        self.assertEqual(writes, [('POST', 'repos/Umbral-lab/zeron/pulls/19/reviews')])
        self.assertEqual(fake.review['commit_id'], 'a' * 40)

    def test_stale_head_blocks_before_any_write(self):
        fake = FixtureGitHub(head='c' * 40)
        with self.assertRaises(RuntimeError):
            pub.publish(self.record, self.assess(), time.monotonic() + 30, call=fake)
        self.assertTrue(all(method == 'GET' for method, _, _ in fake.calls))

    def test_wrong_actor_is_not_verified(self):
        fake = FixtureGitHub(actor='wrong-fixture')
        with self.assertRaises(RuntimeError):
            pub.publish(self.record, self.assess(), time.monotonic() + 30, call=fake)

    def test_legacy_publication_cannot_create_markdown_issue_or_pr(self):
        fake = FixtureGitHub()
        with self.assertRaises(ValueError):
            pub.publish({'source': 'a' * 40}, self.assess(), time.monotonic() + 30, call=fake)
        self.assertEqual(fake.calls, [])

    def test_partial_is_comment_never_approval(self):
        self.record['checks'] = []
        packet = self.assess()
        fake = FixtureGitHub()
        pub.publish(self.record, packet, time.monotonic() + 30, call=fake)
        self.assertEqual(fake.review['event'], 'COMMENT')
        self.assertEqual(pub.finalize(self.record, packet), 2)
        self.assertEqual(self.record['state'], 'partial')

    def test_finish_without_checkpoint_keeps_private_failure_and_no_completion(self):
        receipt = self.root / 'receipt.json'
        result = self.root / 'result.json'
        m.save(receipt, self.record)
        fake = FixtureGitHub()
        with patch.object(m, 'STATE', self.root), patch.object(m, 'publish', lambda r,p,d: pub.publish(r,p,d,call=fake)):
            code = m.finish_run(receipt, result, 0, time.monotonic() + 30)
        self.assertEqual(code, 2)
        self.assertFalse((self.root / 'last-reviewed-candidate.json').exists())
        self.assertEqual(fake.review['event'], 'COMMENT')

    def test_write_timeout_is_not_replayed_read_retry_is_bounded(self):
        error = subprocess.TimeoutExpired('fixture', 1)
        ok = subprocess.CompletedProcess(['fixture'], 0, '{}', '')
        with patch.object(pub.subprocess, 'run', side_effect=[error, ok]) as run:
            self.assertEqual(pub.api('GET', 'fixture', None, time.monotonic() + 30), {})
            self.assertEqual(run.call_count, 2)
        with patch.object(pub.subprocess, 'run', side_effect=error) as run:
            with self.assertRaises(subprocess.TimeoutExpired):
                pub.api('POST', 'fixture', {}, time.monotonic() + 30)
            self.assertEqual(run.call_count, 1)

    def test_expired_deadline_never_calls_network(self):
        with patch.object(pub.subprocess, 'run') as run:
            with self.assertRaises(TimeoutError):
                pub.api('POST', 'fixture', {}, time.monotonic() - 1)
            run.assert_not_called()

    def test_secret_material_redacted_or_refused(self):
        self.assertNotIn('ghp_' + 'x' * 30, pub.sanitize('ghp_' + 'x' * 30))
        with self.assertRaises(ValueError):
            pub.sanitize('-----BEGIN PRIVATE KEY-----\nfixture')


if __name__ == '__main__':
    unittest.main()

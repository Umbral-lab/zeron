"""Queue/launcher regression fixtures: no real network, models or Cargo builds."""
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('queue_launcher', Path(__file__).with_name('zeron-nightly.py'))
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
import zeron_audit as audit


def pr(number=19, head='a' * 40, author=audit.BUILDER):
    return {'number': number, 'head': {'sha': head}, 'base': {'sha': 'b' * 40},
            'user': {'login': author}, 'html_url': 'https://example.invalid/pull/' + str(number),
            'title': 'Fixture', 'updated_at': '2026-11-07T01:00:00Z', 'draft': False}


class QueueTests(unittest.TestCase):
    def select(self, pulls, reviews=None, files=None):
        self.calls = []
        def call(method, path, payload, deadline):
            self.calls.append((method, path))
            if 'state=open' in path:
                return pulls
            if '/reviews?' in path:
                return reviews or []
            if '/files?' in path:
                return files if files is not None else [{'filename': 'crates/update/src/lib.rs'}]
            raise AssertionError(path)
        return audit.select_candidate(call, time.monotonic() + 30)

    def test_new_a_head_selected_independently_of_unchanged_main(self):
        old_review = {'user': {'login': audit.REVIEWER}, 'commit_id': 'c' * 40, 'state': 'CHANGES_REQUESTED'}
        selected = self.select([pr()], [old_review])
        assert selected is not None
        self.assertEqual(selected['head'], 'a' * 40)
        self.assertEqual(selected['number'], 19)
        self.assertFalse(any('/main' in path for _, path in self.calls))

    def test_same_reviewed_head_does_not_spend_another_model_job(self):
        for state in ['APPROVED', 'CHANGES_REQUESTED']:
            reviewed = {'user': {'login': audit.REVIEWER}, 'commit_id': 'a' * 40, 'state': state}
            self.assertIsNone(self.select([pr()], [reviewed]))

    def test_b_authored_and_draft_prs_excluded(self):
        a = pr()
        a['draft'] = True
        self.assertIsNone(self.select([pr(author=audit.REVIEWER), a]))
        self.assertEqual(len(self.calls), 1)

    def test_docs_only_queue_is_idle(self):
        self.assertIsNone(self.select([pr()], files=[{'filename': 'docs/audits/fixture.md'}]))

    def test_product_code_preferred_over_ops(self):
        pulls = [pr(8), pr(19)]
        def call(method, path, payload, deadline):
            if 'state=open' in path:
                return pulls
            if '/reviews?' in path:
                return []
            return [{'filename': 'ops/worker-b/zeron-nightly.py' if '/8/' in path else 'crates/update/src/lib.rs'}]
        selected = audit.select_candidate(call, time.monotonic() + 30)
        assert selected is not None
        self.assertEqual(selected['number'], 19)

    def test_truncated_discovery_fails_closed(self):
        with self.assertRaises(RuntimeError):
            self.select([pr()] * 100)
        with self.assertRaises(RuntimeError):
            self.select([pr()], files=[{'filename': 'fixture.rs'}] * 100)

    def test_incomplete_review_can_be_revalidated_not_treated_as_approval(self):
        reviewed = {'user': {'login': audit.REVIEWER}, 'commit_id': 'a' * 40, 'state': 'COMMENTED'}
        self.assertIsNotNone(self.select([pr()], [reviewed]))

    def test_engine_consent_plan_includes_assembled_runtime(self):
        plan = audit.check_plan(['crates/engine/src/harness_updates.rs'])
        self.assertEqual(len(plan), 3)
        self.assertTrue(any('local_first' in command for command in plan))
        self.assertTrue(any('harness_updates::tests' in command for command in plan))
        self.assertTrue(all(isinstance(command, list) for command in plan))

    def test_pr_filename_cannot_inject_shell_command(self):
        self.assertEqual(audit.check_plan(['$(curl evil)/README.md']), [])

    def test_worker_a_candidate_gets_bounded_fixed_plan(self):
        plan = audit.check_plan(['ops/worker-a/run_window_guard.py',
                                 'docs/OPERATIONS_POLICY_MAPPING.md'])
        self.assertEqual(plan, [['python3', '-m', 'unittest', 'discover',
                                 '-s', 'ops/worker-a', '-p', 'test_*.py']])

    def test_worker_b_plan_argv_unchanged_by_worker_a_support(self):
        plan = audit.check_plan(['ops/worker-b/zeron_audit.py'])
        self.assertEqual(plan, [['python3', '-m', 'unittest', 'discover',
                                 '-s', 'ops/worker-b', '-p', 'test_*.py']])

    def test_dirty_worktree_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.worktrees/nightly-review').mkdir(parents=True)
            with patch.object(audit.subprocess, 'run'), \
                 patch.object(audit.subprocess, 'check_output', return_value=' M user.rs') as git:
                with self.assertRaises(RuntimeError):
                    audit.prepare_worktree(root, {'head': 'a' * 40, 'base': 'b' * 40})
            self.assertEqual(git.call_count, 1)
            self.assertNotIn('checkout', git.call_args.args[0])

    def test_idle_launch_never_dispatches_or_publishes_even_with_old_complete_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'last-completed-source.json').write_text(json.dumps({'source': 'b' * 40}))
            when = datetime(2026, 11, 8, 1, 0, tzinfo=m.ZONE)
            def fetch(path, record):
                record['source'] = 'b' * 40
                m.save(path, record)
                return 'b' * 40
            with patch.object(m, 'STATE', root), patch.object(m, 'datetime') as clock, \
                 patch.object(m.time, 'time', return_value=when.timestamp()), \
                 patch.object(m, 'fetch_source', side_effect=fetch), patch.object(m, 'quota', return_value=None), \
                 patch.object(m, 'select_candidate', return_value=None) as select, \
                 patch.object(m, 'supervise') as worker, patch.object(m, 'publish') as publish:
                clock.now.return_value = when
                self.assertEqual(m.launch(), 0)
            select.assert_called_once()
            worker.assert_not_called()
            publish.assert_not_called()
            receipt = json.loads((root / '2026-11-08.json').read_text())
            self.assertEqual(receipt['state'], 'skipped_no_candidate')
            self.assertEqual(receipt['requests'], 0)
            self.assertEqual(receipt['reserved_generated'], 0)


    def test_oversized_candidate_is_blocked_before_any_model_work(self):
        files = [{'filename': f'crates/update/src/file_{i}.rs'} for i in range(13)]
        self.assertIsNone(self.select([pr()], files=files))

    def test_blocked_candidate_notifies_once_without_model_or_report_pr(self):
        for notified in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                when = datetime(2026, 11, 8, 1, 0, tzinfo=m.ZONE)
                def fetch(path, record):
                    record['source'] = 'b' * 40
                    m.save(path, record)
                    return record['source']
                def select(call, deadline, blocked):
                    blocked.append({'number': 19, 'head': 'a' * 40, 'base': 'b' * 40,
                                    'url': 'https://example.invalid/pull/19',
                                    'reason': 'Fixture oversized candidate', 'already_notified': notified})
                    return None
                with patch.object(m, 'STATE', root), patch.object(m, 'datetime') as clock, \
                     patch.object(m.time, 'time', return_value=when.timestamp()), \
                     patch.object(m, 'fetch_source', side_effect=fetch), patch.object(m, 'quota', return_value=None), \
                     patch.object(m, 'select_candidate', side_effect=select), \
                     patch.object(m, 'supervise') as model, patch.object(m, 'publish') as publish:
                    clock.now.return_value = when
                    self.assertEqual(m.launch(), 2)
                model.assert_not_called()
                self.assertEqual(publish.call_count, 0 if notified else 1)
                record = json.loads((root / '2026-11-08.json').read_text())
                self.assertEqual(record['requests'], 0)
                self.assertEqual(record['state'], 'blocked_checks')
                self.assertNotEqual(record['state'], 'reviewed')

    def test_complete_launch_pins_new_pr_head_runs_checks_before_model_and_reviews_existing_pr(self):
        import hashlib
        import zeron_nightly_publish as publisher
        from test_handoff import FixtureGitHub
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            when = datetime(2026, 11, 8, 1, 0, tzinfo=m.ZONE)
            selected = {'number': 19, 'base': 'b' * 40, 'head': 'a' * 40,
                        'paths': ['crates/update/src/lib.rs'], 'code_paths': ['crates/update/src/lib.rs'],
                        'url': 'https://example.invalid/pull/19'}
            (root / 'last-completed-source.json').write_text(json.dumps({'source': 'b' * 40}))
            def fetch(path, record):
                record['source'] = 'b' * 40
                m.save(path, record)
                return record['source']
            checks_ready = []
            def checks(*args):
                for index, argv in enumerate(audit.check_plan(selected['paths'])):
                    log = root / ('check-' + str(index))
                    raw = b'test result: ok. 1 passed; 0 failed; 0 ignored\n'
                    log.write_bytes(raw)
                    checks_ready.append({'argv': argv, 'status': 'passed', 'returncode': 0,
                                         'log': str(log), 'sha256': hashlib.sha256(raw).hexdigest()})
                return checks_ready
            def model(command, cutoff, log):
                self.assertTrue(checks_ready, 'model dispatched before checks')
                path = root / '2026-11-08.json'
                record = json.loads(path.read_text())
                self.assertEqual(record['source'], 'a' * 40)
                self.assertEqual(record['main_source'], 'b' * 40)
                # Fixture simulation of the independently tested outbound reservation guard.
                record.update(requests=3, reserved_generated=3000)
                m.save(path, record)
                review = {'head': 'a' * 40, 'verdict': 'APPROVE', 'summary': 'Fixture code review',
                          'inspected_files': selected['code_paths'], 'findings': [], 'limitations': []}
                packet = publisher.checkpoint({'completed': True, 'final_response': json.dumps(review)}, record)
                m.save(root / '2026-11-08-result.json', packet)
                return 0
            runtime = json.dumps(['python3', '-c', "import runpy; runpy.run_module('hermes_cli.main', run_name='__main__', alter_sys=True)"])
            fake = FixtureGitHub()
            with patch.object(m, 'STATE', root), patch.object(m, 'datetime') as clock, \
                 patch.object(m.time, 'time', return_value=when.timestamp()), \
                 patch.object(m, 'fetch_source', side_effect=fetch), patch.object(m, 'quota', return_value=None), \
                 patch.object(m, 'select_candidate', return_value=selected), \
                 patch.object(m, 'execute_checks', side_effect=checks), \
                 patch.object(m.subprocess, 'check_output', return_value=runtime), \
                 patch.object(m, 'supervise', side_effect=model) as worker, \
                 patch.object(m, 'publish', lambda r,p,d: publisher.publish(r,p,d,call=fake)):
                clock.now.return_value = when
                self.assertEqual(m.launch(), 0)
            worker.assert_called_once()
            receipt = json.loads((root / '2026-11-08.json').read_text())
            self.assertEqual(receipt['state'], 'reviewed')
            self.assertEqual(receipt['review_verdict'], 'APPROVE')
            self.assertEqual(fake.review['commit_id'], 'a' * 40)
            self.assertTrue((root / 'last-reviewed-candidate.json').exists())
            self.assertFalse(any('/issues' in p or '/git/' in p for _, p, _ in fake.calls))


if __name__ == '__main__':
    unittest.main()

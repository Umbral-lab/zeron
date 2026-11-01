"""Startup/DNS regression tests. All transport failures below are fixtures."""
import importlib.util
from datetime import datetime
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('nightly_preflight', Path(__file__).with_name('zeron-nightly.py'))
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        state = patch.object(m, 'STATE', self.root)
        state.start()
        self.addCleanup(state.stop)
        self.receipt = self.root / 'receipt.json'
        self.record = {'state': 'preflight_failed', 'requests': 0, 'reserved_generated': 0,
                       'preflight_attempts': 0}
        m.save(self.receipt, self.record)
        self.dns = subprocess.CompletedProcess(['git'], 128, '', 'Could not resolve host: github.com')
        self.ok = subprocess.CompletedProcess(['git'], 0, '', '')

    def test_dns_gets_exactly_one_persisted_retry(self):
        def fetch(*args, **kwargs):
            saved = json.loads(self.receipt.read_text())
            self.assertEqual(saved['preflight_attempts'], fetches.call_count)
            return self.dns if fetches.call_count == 1 else self.ok
        with patch.object(m.subprocess, 'run', side_effect=fetch) as fetches, \
             patch.object(m.subprocess, 'check_output', return_value='a' * 40), \
             patch.object(m.time, 'sleep'):
            source = m.fetch_source(self.receipt, self.record)
        self.assertEqual(source, 'a' * 40)
        self.assertEqual(fetches.call_count, 2)
        self.assertEqual(json.loads(self.receipt.read_text())['preflight_status'], 'passed')

    def test_launch_failure_has_receipt_before_network_and_never_dispatches(self):
        when = datetime(2026, 11, 2, 1, 0, tzinfo=m.ZONE)
        def failed_fetch(*args, **kwargs):
            path = self.root / '2026-11-02.json'
            self.assertTrue(path.exists())
            self.assertEqual(json.loads(path.read_text())['requests'], 0)
            return self.dns
        with patch.object(m, 'datetime') as clock, \
             patch.object(m.subprocess, 'run', side_effect=failed_fetch) as fetches, \
             patch.object(m.time, 'sleep'), patch.object(m, 'notify_preflight_failure') as notice, \
             patch.object(m, 'supervise') as model:
            clock.now.return_value = when
            code = m.launch()
        saved = json.loads((self.root / '2026-11-02.json').read_text())
        self.assertEqual(code, 1)
        self.assertEqual(saved['state'], 'preflight_failed')
        self.assertEqual(saved['preflight_attempts'], 2)
        self.assertEqual(fetches.call_count, 2)
        self.assertTrue((self.root / '2026-11-02-result.json').exists())
        model.assert_not_called()
        notice.assert_called_once()

    def test_attempt_cap_survives_a_restart(self):
        self.record['preflight_attempts'] = 2
        with patch.object(m.subprocess, 'run') as transport:
            self.assertIsNone(m.fetch_source(self.receipt, self.record))
        transport.assert_not_called()

    def test_auth_failure_is_not_transport_retried(self):
        failed = subprocess.CompletedProcess(['git'], 128, '', 'Authentication failed')
        with patch.object(m.subprocess, 'run', return_value=failed) as transport:
            self.assertIsNone(m.fetch_source(self.receipt, self.record))
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(json.loads(self.receipt.read_text())['state'], 'preflight_failed')

    def test_owner_resume_only_for_proven_unused_preflight(self):
        now = datetime(2026, 11, 1, 1, 32, tzinfo=m.ZONE)
        self.record['preflight_attempts'] = 1
        self.assertTrue(m.resume_allowed(self.record, now))
        for change in [{'requests': 1}, {'reserved_generated': 1000}, {'model_started_at': 'uncertain'},
                       {'owner_resume_count': 1}, {'preflight_attempts': 2}, {'state': 'complete'}]:
            self.assertFalse(m.resume_allowed(dict(self.record, **change), now))
        self.assertFalse(m.resume_allowed(self.record, now.replace(hour=5)))
        self.assertFalse(m.resume_allowed(self.record, now.replace(hour=0)))

    def test_no_automatic_late_start(self):
        with patch.object(m, 'datetime') as clock, patch.object(m, 'fetch_source') as fetch:
            clock.now.return_value = datetime(2026, 11, 1, 1, 32, tzinfo=m.ZONE)
            self.assertEqual(m.launch(), 0)
        fetch.assert_not_called()

    def test_quota_block_is_checkpointed_and_not_dispatched(self):
        sample = {'windows': [{'label': 'Weekly', 'used_percent': 77, 'resets_at': 'fixture'}]}
        def ready(receipt, record):
            record.update(source='a' * 40, state='admitted')
            m.save(receipt, record)
            return record['source']
        with patch.object(m, 'datetime') as clock, patch.object(m, 'fetch_source', side_effect=ready), \
             patch.object(m, 'quota', return_value=sample), patch.object(m, 'notify_preflight_failure') as notice, \
             patch.object(m, 'supervise') as model:
            clock.now.return_value = datetime(2026, 11, 2, 1, 0, tzinfo=m.ZONE)
            self.assertEqual(m.launch(), 1)
        record = json.loads((self.root / '2026-11-02.json').read_text())
        packet = json.loads((self.root / '2026-11-02-result.json').read_text())
        self.assertEqual(record['state'], 'blocked')
        self.assertEqual(packet['reason'], 'Quota reserve reached')
        self.assertTrue((self.root / 'route-block.json').exists())
        model.assert_not_called()
        notice.assert_called_once()

    def test_quota_override_expires_and_does_not_change_default(self):
        now = datetime(2026, 11, 1, 2, 0, tzinfo=m.ZONE)
        _, _, end = m.window(now)
        ledger = {'date': '2026-11-01', 'quota_reserve_override': {'date': '2026-11-01', 'expires_at': end.timestamp()}}
        self.assertTrue(m.quota_override_active(ledger, now))
        self.assertFalse(m.quota_override_active(ledger, now.replace(hour=5)))
        self.assertFalse(m.quota_override_active(ledger, now.replace(day=2)))
        self.assertFalse(m.quota_override_active({}, now))

    def test_override_only_clears_reserve_after_a_fresh_reading(self):
        ledger = {'date': '2026-11-01', 'blocked': 'Quota reserve reached'}
        sample = {'windows': [{'label': 'Weekly', 'used_percent': 77, 'resets_at': 'fixture'}]}
        with patch.object(m, 'quota_override_active', return_value=True):
            with self.assertRaises(RuntimeError):
                m.quota_check(ledger, None)
            m.quota_check(ledger, sample)
        self.assertNotIn('blocked', ledger)

    def test_override_keeps_exhaustion_auth_and_consumption_blocks(self):
        sample = {'windows': [{'label': 'Weekly', 'used_percent': 77, 'resets_at': 'fixture'}]}
        with patch.object(m, 'quota_override_active', return_value=True):
            with self.assertRaises(RuntimeError):
                m.quota_check({'blocked': 'Provider auth/payment/quota status 401'}, sample)
            with self.assertRaises(RuntimeError):
                m.quota_check({}, {'windows': [dict(sample['windows'][0], used_percent=100)]})
            baseline = {'quota_baseline': sample['windows']}
            with self.assertRaises(RuntimeError):
                m.quota_check(baseline, {'windows': [dict(sample['windows'][0], used_percent=79)]})

    def test_quota_recovery_is_once_and_only_on_owner_approved_date(self):
        now = datetime(2026, 11, 1, 2, 0, tzinfo=m.ZONE)
        ledger = {'state': 'blocked', 'blocked': 'Quota reserve reached', 'requests': 0,
                  'reserved_generated': 0, 'preflight_status': 'passed', 'source': 'a' * 40}
        self.assertTrue(m.quota_resume_allowed(ledger, now))
        for change in [{'requests': 1}, {'model_started_at': 'uncertain'}, {'owner_quota_override_count': 1}]:
            self.assertFalse(m.quota_resume_allowed(dict(ledger, **change), now))
        self.assertFalse(m.quota_resume_allowed(ledger, now.replace(day=2)))

    def test_usage_transport_timeout_is_unknown_not_a_crash(self):
        with patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fixture', 30)):
            self.assertIsNone(m.quota())


if __name__ == '__main__':
    unittest.main()

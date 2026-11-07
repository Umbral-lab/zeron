"""Reserve recovery regressions; usage responses here are offline fixtures."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
from itertools import chain, repeat
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('nightly_recovery', Path(__file__).with_name('zeron-nightly.py'))
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        state = patch.object(m, 'STATE', self.root)
        state.start()
        self.addCleanup(state.stop)
        self.now = datetime(2026, 11, 5, 0, 0, tzinfo=timezone.utc)
        self.record = {'date': '2026-11-05', 'state': 'blocked', 'requests': 0,
                       'reserved_generated': 0, 'preflight_attempts': 0}
        self.sample = {'source': 'usage_api', 'fetched_at': self.now.isoformat(), 'windows': [
            {'label': 'Session', 'used_percent': 17, 'resets_at': (self.now + timedelta(hours=2)).isoformat()},
            {'label': 'Weekly', 'used_percent': 18, 'resets_at': (self.now + timedelta(days=6)).isoformat()},
        ]}
        self.block = self.root / 'route-block.json'
        m.save(self.block, {'reason': 'Quota reserve reached'})

    def test_live_recovery_archives_evidence_and_preserves_all_spend(self):
        self.record.update(requests=2, reserved_generated=2000, prior_active_seconds=95)
        self.assertTrue(m.reconcile_reserve_block(self.record, self.sample, self.now))
        self.assertFalse(self.block.exists())
        self.assertEqual(self.record['requests'], 2)
        self.assertEqual(self.record['reserved_generated'], 2000)
        self.assertEqual(self.record['prior_active_seconds'], 95)
        self.assertFalse(m.resume_allowed(self.record, self.now))
        archives = list(self.root.glob('route-block.recovered.*.json'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(archives[0].stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(archives[0].read_text())['usage'], self.sample)

    def test_unknown_stale_partial_high_or_malformed_readings_cannot_clear(self):
        bad = [None, {}, dict(self.sample, source='unknown'),
               dict(self.sample, fetched_at=(self.now-timedelta(minutes=6)).isoformat()),
               dict(self.sample, fetched_at=(self.now+timedelta(seconds=1)).isoformat()),
               dict(self.sample, fetched_at=self.now.replace(tzinfo=None).isoformat()),
               dict(self.sample, windows=self.sample['windows'][:1])]
        for value in [70, 100, -1, float('nan'), float('inf'), True]:
            item = copy.deepcopy(self.sample)
            item['windows'][1]['used_percent'] = value
            bad.append(item)
        item = copy.deepcopy(self.sample)
        item['windows'][0]['resets_at'] = (self.now-timedelta(seconds=1)).isoformat()
        bad.append(item)
        for sample in bad:
            with self.subTest(sample=sample):
                original = copy.deepcopy(self.record)
                self.assertFalse(m.reconcile_reserve_block(self.record, sample, self.now))
                self.assertTrue(self.block.exists())
                self.assertEqual(self.record, original)
        self.assertEqual(list(self.root.glob('route-block.recovered.*.json')), [])

    def test_auth_payment_and_nightly_consumption_remain_blocked(self):
        for reason in ['Provider auth/payment/quota status 401', 'Provider auth/payment/quota status 402',
                       'Provider auth/payment/quota status 429', 'Observed nightly account consumption threshold reached']:
            m.save(self.block, {'reason': reason})
            self.assertFalse(m.reconcile_reserve_block(self.record, self.sample, self.now))
            self.assertTrue(self.block.exists())
        m.save(self.block, {'reason': 'Quota reserve reached'})
        for field, baseline in [('Session', 7), ('Weekly', 16)]:
            record = copy.deepcopy(self.record)
            record['quota_baseline'] = copy.deepcopy(self.sample['windows'])
            next(w for w in record['quota_baseline'] if w['label'] == field)['used_percent'] = baseline
            self.assertFalse(m.reconcile_reserve_block(record, self.sample, self.now))
            self.assertTrue(self.block.exists())
        record = dict(self.record, blocked='Provider auth/payment/quota status 403')
        self.assertFalse(m.reconcile_reserve_block(record, self.sample, self.now))

    def test_operator_resume_requires_recovery_same_day_unused_budget_and_window(self):
        self.assertFalse(m.resume_allowed(self.record, self.now))
        self.assertTrue(m.reconcile_reserve_block(self.record, self.sample, self.now))
        self.assertTrue(m.resume_allowed(self.record, self.now))
        for change in [{'requests': 1}, {'reserved_generated': 1}, {'model_started_at': 'uncertain'},
                       {'owner_resume_count': 1}, {'preflight_attempts': 2}, {'date': '2026-11-04'},
                       {'blocked': 'Provider auth/payment/quota status 401'}]:
            self.assertFalse(m.resume_allowed(dict(self.record, **change), self.now))
        self.assertFalse(m.resume_allowed(self.record, self.now.replace(hour=4)))

    def test_slow_telemetry_is_validated_against_the_post_fetch_clock(self):
        sample = copy.deepcopy(self.sample)
        sample['fetched_at'] = (self.now + timedelta(seconds=2)).isoformat()
        with patch.object(m, 'datetime', wraps=datetime) as clock, \
             patch.object(m.time, 'time', return_value=self.now.timestamp()), \
             patch.object(m, 'quota', return_value=sample), \
             patch.object(m, 'fetch_source', return_value=None) as fetch, \
             patch.object(m, 'notify_preflight_failure'), patch.object(m, 'supervise') as model:
            clock.now.side_effect = chain([self.now], repeat(self.now+timedelta(seconds=3)))
            self.assertEqual(m.launch(), 1)
        fetch.assert_called_once()
        model.assert_not_called()
        self.assertFalse(self.block.exists())

    def test_normal_wake_reconciles_before_repository_preflight(self):
        def preflight(receipt, record):
            self.assertFalse(self.block.exists())
            self.assertIn('route_block_reconciled_at', record)
            return None  # Stop this fixture before any model or publishing.
        with patch.object(m, 'datetime', wraps=datetime) as clock, \
             patch.object(m.time, 'time', return_value=self.now.timestamp()), \
             patch.object(m, 'quota', return_value=self.sample), \
             patch.object(m, 'fetch_source', side_effect=preflight) as fetch, \
             patch.object(m, 'notify_preflight_failure'), patch.object(m, 'supervise') as model:
            clock.now.return_value = self.now
            self.assertEqual(m.launch(), 1)
        fetch.assert_called_once()
        model.assert_not_called()


if __name__ == '__main__':
    unittest.main()

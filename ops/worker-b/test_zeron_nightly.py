import importlib.util
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('nightly', Path(__file__).with_name('zeron-nightly.py'))
assert spec and spec.loader
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class NightlyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        state_patch = patch.object(m, 'STATE', self.root)
        state_patch.start()
        self.addCleanup(state_patch.stop)
        self.ledger = self.root / 'receipt.json'
        self.state = {'requests': 0, 'reserved_generated': 0,
                      'deadline': time.time() + 60, 'monotonic_deadline': time.monotonic() + 60}
        m.save(self.ledger, self.state)

    def test_daytime_and_late_starts_rejected(self):
        for hour, minute in [(0, 59), (1, 16), (5, 0), (11, 0)]:
            _, admitted, _ = m.window(datetime(2026, 10, 31, hour, minute, tzinfo=m.ZONE))
            self.assertFalse(admitted)
        self.assertTrue(m.window(datetime(2026, 10, 31, 1, 0, tzinfo=m.ZONE))[1])

    def test_dst_shorter_of_local_close_and_four_elapsed_hours(self):
        for date, hours in [((2027, 3, 28), 3), ((2027, 10, 31), 4), ((2026, 10, 31), 4)]:
            start = datetime(*date, 1, 0, tzinfo=m.ZONE)
            _, admit, end = m.window(start)
            self.assertTrue(admit)
            self.assertEqual((end - start.astimezone(timezone.utc)).total_seconds(), hours * 3600)

    def test_attempt_and_output_caps_survive_restart(self):
        for _ in range(4):
            self.assertEqual(m.reserve(self.ledger, m.MODEL, 9000, None), 1000)
        with self.assertRaises(RuntimeError):
            m.reserve(self.ledger, m.MODEL, 1000, None)
        saved = json.loads(self.ledger.read_text())
        self.assertEqual(saved['requests'], 4)
        self.assertEqual(saved['reserved_generated'], 4000)

    def test_wrong_model_is_never_admitted(self):
        with self.assertRaises(RuntimeError):
            m.reserve(self.ledger, 'another-model', 1000, None)
        self.assertEqual(json.loads(self.ledger.read_text())['requests'], 0)

    def test_deadline_blocks_before_dispatch(self):
        self.state['deadline'] = time.time() - 1
        m.save(self.ledger, self.state)
        with self.assertRaises(RuntimeError):
            m.reserve(self.ledger, m.MODEL, 1000, None)

    def test_low_quota_remains_blocked_when_unknown(self):
        sample = {'windows': [{'label': 'Weekly', 'used_percent': 70, 'resets_at': 'fixture'}]}
        with self.assertRaises(RuntimeError):
            m.reserve(self.ledger, m.MODEL, 1000, sample)
        with self.assertRaises(RuntimeError):
            m.reserve(self.ledger, m.MODEL, 1000, None)

    def test_weekly_threshold_blocks_same_run(self):
        initial = {'windows': [{'label': 'Weekly', 'used_percent': 50, 'resets_at': 'fixture'}]}
        m.reserve(self.ledger, m.MODEL, 1000, initial)
        later = {'windows': [{'label': 'Weekly', 'used_percent': 52, 'resets_at': 'fixture'}]}
        with self.assertRaises(RuntimeError):
            m.reserve(self.ledger, m.MODEL, 1000, later)

    def test_supervisor_terminates_owned_process(self):
        started = time.monotonic()
        with patch.object(m, 'ROOT', self.root):
            result = m.supervise(['python3', '-c', 'import time; time.sleep(20)'],
                                 time.monotonic() + 0.3, self.root / 'log')
        self.assertNotEqual(result, 0)
        self.assertLess(time.monotonic() - started, 2)

    def test_http_wire_caps_and_retry_accounting(self):
        import httpx
        original_send, original_async = httpx.Client.send, httpx.AsyncClient.send
        seen = []
        transport = httpx.MockTransport(lambda req: (seen.append(json.loads(req.content)),
                                                     httpx.Response(200, json={'fixture': True}))[1])
        with patch.dict('os.environ', {'ZERON_NIGHTLY_LEDGER': str(self.ledger)}), patch.object(m, 'quota', lambda: None):
            try:
                m.install_guard()
                with httpx.Client(transport=transport) as client:
                    for _ in range(4):
                        client.post('https://chatgpt.com/backend-api/codex/responses',
                                    json={'model': m.MODEL, 'max_output_tokens': 9999, 'service_tier': 'priority'})
                    with self.assertRaises(SystemExit):
                        client.post('https://chatgpt.com/backend-api/codex/responses', json={'model': m.MODEL})
                    with self.assertRaises(SystemExit):
                        client.post('https://api.openai.com/v1/responses', json={'model': m.MODEL})
                self.assertEqual(len(seen), 4)
                self.assertTrue(all(d['max_output_tokens'] == 1000 and 'service_tier' not in d for d in seen))
            finally:
                httpx.Client.send, httpx.AsyncClient.send = original_send, original_async


if __name__ == '__main__':
    unittest.main()

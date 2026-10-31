#!/usr/bin/env python3
"""Standalone tests for ops/worker-a/run_window_guard.py (OPS-001A).

Run: python3 ops/worker-a/test_run_window_guard.py
Deterministic, no network, receipts in a temporary directory.
"""

import json
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import run_window_guard as g

MAD = ZoneInfo("Europe/Madrid")


def utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


class WindowTests(unittest.TestCase):
    def test_autumn_night_elapsed_cap(self):
        w = g.compute_window(date(2026, 10, 31))
        self.assertEqual(w["nominal_start_utc"], "2026-10-31T00:00:00+00:00")
        self.assertEqual(w["deadline_utc"], "2026-10-31T04:00:00+00:00")
        self.assertAlmostEqual(w["max_elapsed_hours"], 4.0)

    def test_dst_autumn_night_elapsed_hours(self):
        # 2026-10-25: Madrid changes CEST->CET at 03:00 local (02:00 UTC).
        # 01:00 local is still CEST -> 23:00 UTC of the previous day.
        # 05:00 local is CET -> 04:00 UTC, i.e. exactly 4 elapsed hours:
        # this 01:00-05:00 window is NOT shortened on the autumn night.
        w = g.compute_window(date(2026, 10, 25))
        self.assertEqual(w["nominal_start_utc"], "2026-10-24T23:00:00+00:00")  # 01:00 CEST
        self.assertEqual(w["local_close_utc"], "2026-10-25T04:00:00+00:00")    # 05:00 CET
        self.assertEqual(w["deadline_utc"], "2026-10-25T04:00:00+00:00")       # earlier of close and +4h (equal)
        self.assertAlmostEqual(w["max_elapsed_hours"], 4.0)

    def test_dst_spring_night_elapsed_hours(self):
        # 2027-03-28: Madrid changes CET->CEST at 02:00 local (01:00 UTC).
        # The 01:00 start precedes the change by 1h, 05:00 close follows it
        # by 3h, so this window is exactly 4 elapsed hours too:
        # 00:00 UTC -> 03:00 UTC.
        w = g.compute_window(date(2027, 3, 28))
        self.assertEqual(w["nominal_start_utc"], "2027-03-28T00:00:00+00:00")  # 01:00 CET
        self.assertEqual(w["local_close_utc"], "2027-03-28T03:00:00+00:00")    # 05:00 CEST
        self.assertEqual(w["deadline_utc"], "2027-03-28T03:00:00+00:00")       # +4h == 05:00 instant
        self.assertAlmostEqual(w["max_elapsed_hours"], 4.0)

    def test_phases_derive_from_deadline(self):
        w = g.compute_window(date(2026, 10, 31))
        ph = w["phases"]
        self.assertEqual(ph["freeze_utc"], "2026-10-31T03:00:00+00:00")
        self.assertEqual(ph["close_findings_utc"], "2026-10-31T03:20:00+00:00")
        self.assertEqual(ph["integration_utc"], "2026-10-31T03:45:00+00:00")
        self.assertEqual(ph["shutdown_utc"], "2026-10-31T03:55:00+00:00")
        # phase order is strictly increasing and inside the window
        seq = [w["nominal_start_utc"]] + [ph[k] for k in
               ("freeze_utc", "close_findings_utc", "integration_utc", "shutdown_utc")] + [w["deadline_utc"]]
        iso = [datetime.fromisoformat(x) for x in seq]
        self.assertEqual(iso, sorted(iso))

    def test_short_run_phases_follow_short_deadline(self):
        w = g.compute_window(date(2027, 3, 28))  # 3-hour night
        self.assertEqual(w["phases"]["freeze_utc"], "2027-03-28T02:00:00+00:00")
        self.assertEqual(w["phases"]["shutdown_utc"], "2027-03-28T02:55:00+00:00")


class StartAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.w = g.compute_window(date(2026, 10, 31))

    def test_on_time(self):
        s = g.start_status(self.w, utc(2026, 10, 31, 0, 0))
        self.assertEqual(s["verdict"], "OK")

    def test_late_within_grace_keeps_deadline(self):
        s = g.start_status(self.w, utc(2026, 10, 31, 0, 14))
        self.assertEqual(s["verdict"], "OK_LATE_GRACE")
        self.assertAlmostEqual(s["remaining_h"], 3.7667, places=3)

    def test_late_beyond_grace_skipped(self):
        s = g.start_status(self.w, utc(2026, 10, 31, 0, 16))
        self.assertEqual(s["verdict"], "SKIP_LATE_START")

    def test_exact_grace_boundary_admitted(self):
        s = g.start_status(self.w, utc(2026, 10, 31, 0, 15))
        self.assertIn(s["verdict"], ("OK", "OK_LATE_GRACE"))

    def test_after_deadline_skipped(self):
        s = g.start_status(self.w, utc(2026, 10, 31, 4, 30))
        self.assertEqual(s["verdict"], "SKIP_WINDOW_CLOSED")

    def test_early_start_flagged(self):
        s = g.start_status(self.w, utc(2026, 10, 30, 23, 30))
        self.assertEqual(s["verdict"], "EARLY")

    def test_dst_night_grace_and_elapsed_are_utc_instants(self):
        spring = g.compute_window(date(2027, 3, 28))
        # 01:16 local start = 00:16 UTC -> beyond grace even on a 3h night
        s = g.start_status(spring, utc(2027, 3, 28, 0, 16))
        self.assertEqual(s["verdict"], "SKIP_LATE_START")
        s2 = g.start_status(spring, utc(2027, 3, 28, 0, 10))
        self.assertEqual(s2["verdict"], "OK_LATE_GRACE")


class PhaseTests(unittest.TestCase):
    def test_phase_sequence(self):
        w = g.compute_window(date(2026, 10, 31))
        expected = [
            (utc(2026, 10, 31, 0, 5), "preflight"),
            (utc(2026, 10, 31, 0, 11), "build"),
            (utc(2026, 10, 31, 3, 5), "freeze-audit"),
            (utc(2026, 10, 31, 3, 25), "close-findings"),
            (utc(2026, 10, 31, 3, 50), "integration-report"),
            (utc(2026, 10, 31, 3, 57), "shutdown"),
            (utc(2026, 10, 31, 4, 1), "past-deadline"),
        ]
        for now, want in expected:
            self.assertEqual(g.phase_at(w, now), want)


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.start = utc(2026, 10, 31, 0, 1)

    def tearDown(self):
        self.tmp.cleanup()

    def test_admit_writes_receipt_and_blocks_duplicate(self):
        r1 = g.admit_run(date(2026, 10, 31), self.start, dirpath=self.dir)
        self.assertEqual(r1["status"], "ADMITTED")
        self.assertEqual(r1["start_admission"]["verdict"], "OK")
        r2 = g.admit_run(date(2026, 10, 31), utc(2026, 10, 31, 0, 30), dirpath=self.dir)
        self.assertEqual(r2["status"], "DUPLICATE")
        # the reused receipt keeps the original admission and deadline
        self.assertEqual(r2["existing"]["actual_start_utc"], "2026-10-31T00:01:00+00:00")
        self.assertEqual(r2["existing"]["deadline_utc"], "2026-10-31T04:00:00+00:00")

    def test_late_start_skip_writes_receipt(self):
        r = g.admit_run(date(2026, 10, 31), utc(2026, 10, 31, 0, 40), dirpath=self.dir)
        self.assertEqual(r["status"], "ADMITTED")
        self.assertEqual(r["start_admission"]["verdict"], "SKIP_LATE_START")

    def test_assert_can_work_requires_admission(self):
        with self.assertRaises(RuntimeError):
            g.assert_can_work(date(2026, 10, 31), self.start, dirpath=self.dir)
        g.admit_run(date(2026, 10, 31), self.start, dirpath=self.dir)
        r = g.assert_can_work(date(2026, 10, 31), self.start, dirpath=self.dir)
        self.assertEqual(r["run_id"], "Umbral-lab/zeron:2026-10-31")

    def test_assert_can_work_refuses_past_deadline(self):
        g.admit_run(date(2026, 10, 31), self.start, dirpath=self.dir)
        with self.assertRaises(RuntimeError):
            g.assert_can_work(date(2026, 10, 31), utc(2026, 10, 31, 4, 1), dirpath=self.dir)

    def test_finalize_then_refurther_work(self):
        g.admit_run(date(2026, 10, 31), self.start, dirpath=self.dir)
        g.finalize_run(date(2026, 10, 31), "night complete", utc(2026, 10, 31, 3, 56), dirpath=self.dir)
        with self.assertRaises(RuntimeError):
            g.assert_can_work(date(2026, 10, 31), utc(2026, 10, 31, 3, 57), dirpath=self.dir)
        r = json.loads(open(g.receipt_path(date(2026, 10, 31), self.dir), encoding="utf-8").read())
        self.assertEqual(r["final_state"], "FINALIZED")
        self.assertEqual(r["stop_reason"], "night complete")

    def test_receipt_created_exclusively_and_private(self):
        g.admit_run(date(2026, 10, 31), self.start, dirpath=self.dir)
        mode = os.stat(g.receipt_path(date(2026, 10, 31), self.dir)).st_mode & 0o777
        self.assertEqual(mode, 0o600)

    def test_dry_run_writes_nothing(self):
        r = g.admit_run(date(2026, 10, 31), self.start, dirpath=self.dir, dry_run=True)
        self.assertEqual(r["status"], "DRY_RUN")
        self.assertFalse(os.path.exists(g.receipt_path(date(2026, 10, 31), self.dir)))


if __name__ == "__main__":
    unittest.main(verbosity=2)

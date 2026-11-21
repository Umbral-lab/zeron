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
gw = g  # alias used by the F-B1..F-B4 finding tests below


def utc(y, mo, d, h, mi=0):
    return datetime(y, mo, d, h, mi, tzinfo=timezone.utc)


def real_elapsed_h(window):
    """Real elapsed hours between the recorded nominal start and deadline."""
    nom = datetime.fromisoformat(window["nominal_start_utc"])
    dl = datetime.fromisoformat(window["deadline_utc"])
    return (dl - nom).total_seconds() / 3600.0


class WindowTests(unittest.TestCase):
    def test_autumn_night_elapsed_cap(self):
        w = g.compute_window(date(2026, 10, 31))
        self.assertEqual(w["nominal_start_utc"], "2026-10-31T00:00:00+00:00")
        self.assertEqual(w["deadline_utc"], "2026-10-31T04:00:00+00:00")
        self.assertAlmostEqual(w["max_elapsed_hours"], 4.0)

    def test_dst_autumn_night_elapsed_hours(self):
        # 2026-10-25: Madrid changes CEST->CET at 03:00 local (02:00 UTC).
        # 01:00 local is still CEST -> 2026-10-24T23:00 UTC. The local 05:00
        # close is 04:00 UTC, which is 5 REAL elapsed hours after the start.
        # The 4h cap must shorten this night to 03:00 UTC (finding F-B1).
        w = g.compute_window(date(2026, 10, 25))
        self.assertEqual(w["nominal_start_utc"], "2026-10-24T23:00:00+00:00")  # 01:00 CEST
        self.assertEqual(w["local_close_utc"], "2026-10-25T04:00:00+00:00")    # 05:00 CET
        self.assertEqual(w["deadline_utc"], "2026-10-25T03:00:00+00:00")       # 23:00Z + 4 real hours
        self.assertAlmostEqual(w["max_elapsed_hours"], 4.0)
        self.assertAlmostEqual(real_elapsed_h(w), 4.0)

    def test_dst_spring_night_elapsed_hours(self):
        # 2027-03-28: Madrid changes CET->CEST at 02:00 local (01:00 UTC).
        # 01:00 local is 00:00 UTC and the 05:00 local close is 03:00 UTC:
        # the night is only 3 REAL elapsed hours even though the wall fields
        # differ by 4 (finding F-B1).
        w = g.compute_window(date(2027, 3, 28))
        self.assertEqual(w["nominal_start_utc"], "2027-03-28T00:00:00+00:00")  # 01:00 CET
        self.assertEqual(w["local_close_utc"], "2027-03-28T03:00:00+00:00")    # 05:00 CEST
        self.assertEqual(w["deadline_utc"], "2027-03-28T03:00:00+00:00")       # local close wins
        self.assertAlmostEqual(w["max_elapsed_hours"], 3.0)
        self.assertAlmostEqual(real_elapsed_h(w), 3.0)

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


class RealElapsedTests(unittest.TestCase):
    """Finding F-B1: the 4h cap and the local close must be compared as real
    UTC instants, never as local wall-clock fields or as a timedelta added
    before the ZoneInfo conversion."""

    def test_autumn_clock_change_night_is_capped_to_four_real_hours(self):
        # 2026-10-25 is the Madrid CEST->CET night: nominal 01:00 CEST is
        # 2026-10-24T23:00Z and the local 05:00 close is 2026-10-25T04:00Z, a
        # 5-real-hour wall span. The 4h cap must win: deadline 03:00Z.
        w = gw.compute_window(date(2026, 10, 25))
        self.assertEqual(w["nominal_start_utc"], "2026-10-24T23:00:00+00:00")
        self.assertEqual(w["local_close_utc"], "2026-10-25T04:00:00+00:00")
        self.assertEqual(w["deadline_utc"], "2026-10-25T03:00:00+00:00")
        self.assertEqual(real_elapsed_h(w), 4.0)

    def test_spring_clock_change_night_is_three_real_hours(self):
        # 2026-03-29 is the Madrid CET->CEST night: nominal 01:00 CET is
        # 2026-03-29T00:00Z and the local 05:00 close is 03:00Z - a 3-real-hour
        # night, not 4 elapsed hours of wall arithmetic.
        w = gw.compute_window(date(2026, 3, 29))
        self.assertEqual(w["nominal_start_utc"], "2026-03-29T00:00:00+00:00")
        self.assertEqual(w["local_close_utc"], "2026-03-29T03:00:00+00:00")
        self.assertEqual(w["deadline_utc"], "2026-03-29T03:00:00+00:00")
        self.assertEqual(real_elapsed_h(w), 3.0)

    def test_max_elapsed_hours_equals_the_real_utc_span(self):
        # The recorded max_elapsed_hours must be the real UTC span, so phases
        # derived from it cannot lie about elapsed budget. Both Madrid
        # clock-change nights plus two normal nights are checked.
        for d in (date(2026, 3, 29), date(2026, 10, 25), date(2026, 11, 15), date(2026, 10, 31)):
            w = gw.compute_window(d)
            self.assertEqual(
                real_elapsed_h(w), w["max_elapsed_hours"],
                f"{d}: max_elapsed_hours must equal the real UTC span",
            )

    def test_no_night_exceeds_four_real_elapsed_hours(self):
        # Sweep both 2026 clock-change months: no accepted window may exceed the
        # 4h cap on real time (the wall-arithmetic version silently gave 5h on
        # the autumn night).
        dates = [date(2026, 3, day) for day in range(22, 32)] + \
                [date(2026, 10, day) for day in range(20, 32)]
        for d in dates:
            w = gw.compute_window(d)
            self.assertLessEqual(real_elapsed_h(w), 4.0 + 1e-9,
                                 f"{d}: window is {real_elapsed_h(w)} real hours, over the 4h cap")


class AdmissionGateTests(unittest.TestCase):
    """Finding F-B2: EARLY is not an admission, and no receipt that was not
    admitted may permit work."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        os.chmod(self.dir, 0o700)
        self.addCleanup(self.tmp.cleanup)

    def test_early_start_writes_no_receipt(self):
        r = gw.admit_run(date(2026, 10, 31),
                         datetime(2026, 10, 30, 23, 30, tzinfo=timezone.utc), dirpath=self.dir)
        self.assertEqual(r["status"], "EARLY_NOT_ADMITTED")
        self.assertEqual(r["start_admission"]["verdict"], "EARLY")
        self.assertFalse(os.path.exists(gw.receipt_path(date(2026, 10, 31), self.dir)))

    def test_in_window_admission_still_possible_after_an_early_dispatch(self):
        gw.admit_run(date(2026, 10, 31),
                     datetime(2026, 10, 30, 23, 30, tzinfo=timezone.utc), dirpath=self.dir)
        r = gw.admit_run(date(2026, 10, 31),
                         datetime(2026, 10, 31, 0, 5, tzinfo=timezone.utc), dirpath=self.dir)
        self.assertEqual(r["status"], "ADMITTED")
        self.assertIn(r["start_admission"]["verdict"], gw.ADMITTED_VERDICTS)
        gw.assert_can_work(date(2026, 10, 31), datetime(2026, 10, 31, 1, 0, tzinfo=timezone.utc),
                           dirpath=self.dir)

    def test_assert_can_work_refuses_a_non_admitted_receipt(self):
        # A skipped night must never be usable as permission to continue working,
        # even before its deadline.
        r = gw.admit_run(date(2026, 10, 31),
                         datetime(2026, 10, 31, 0, 40, tzinfo=timezone.utc), dirpath=self.dir)
        self.assertEqual(r["start_admission"]["verdict"], "SKIP_LATE_START")
        with self.assertRaises(RuntimeError):
            gw.assert_can_work(date(2026, 10, 31), datetime(2026, 10, 31, 1, 0, tzinfo=timezone.utc),
                               dirpath=self.dir)

    def test_assert_can_work_refuses_window_closed_receipt(self):
        gw.admit_run(date(2026, 10, 31),
                     datetime(2026, 10, 31, 6, 0, tzinfo=timezone.utc), dirpath=self.dir)
        with self.assertRaises(RuntimeError):
            gw.assert_can_work(date(2026, 10, 31), datetime(2026, 10, 31, 2, 0, tzinfo=timezone.utc),
                               dirpath=self.dir)

    def test_admitted_and_grace_receipts_permit_work(self):
        gw.admit_run(date(2026, 10, 31),
                     datetime(2026, 10, 31, 0, 5, tzinfo=timezone.utc), dirpath=self.dir)
        gw.assert_can_work(date(2026, 10, 31), datetime(2026, 10, 31, 1, 0, tzinfo=timezone.utc),
                           dirpath=self.dir)
        gw.admit_run(date(2026, 11, 1),
                     datetime(2026, 11, 1, 0, 14, tzinfo=timezone.utc), dirpath=self.dir)
        gw.assert_can_work(date(2026, 11, 1), datetime(2026, 11, 1, 1, 0, tzinfo=timezone.utc),
                           dirpath=self.dir)


class FinalizeIdempotenceTests(unittest.TestCase):
    """Finding F-B3: re-finalizing must not create a second stop for one run."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        os.chmod(self.dir, 0o700)
        self.addCleanup(self.tmp.cleanup)

    def test_second_finalize_returns_the_original_checkpoint(self):
        gw.admit_run(date(2026, 10, 31),
                     datetime(2026, 10, 31, 0, 5, tzinfo=timezone.utc), dirpath=self.dir)
        first = gw.finalize_run(date(2026, 10, 31), "STOP_NIGHTLY_CHECKPOINT",
                                datetime(2026, 10, 31, 3, 50, tzinfo=timezone.utc), dirpath=self.dir)
        second = gw.finalize_run(date(2026, 10, 31), "STOP_SHUTDOWN",
                                 datetime(2026, 10, 31, 3, 59, tzinfo=timezone.utc), dirpath=self.dir)
        self.assertEqual(second["finalized_utc"], first["finalized_utc"])
        self.assertEqual(second["stop_reason"], first["stop_reason"])
        self.assertTrue(second.get("already_finalized"))
        stored = json.loads(open(gw.receipt_path(date(2026, 10, 31), self.dir),
                                 encoding="utf-8").read())
        self.assertEqual(stored["finalized_utc"], "2026-10-31T03:50:00+00:00")
        self.assertEqual(stored["stop_reason"], "STOP_NIGHTLY_CHECKPOINT")


class AtomicWriteTests(unittest.TestCase):
    """Finding F-B4 fold: the receipt is placed by an exclusively-created link,
    never a partial canonical write, and never overwrites an existing receipt."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        os.chmod(self.dir, 0o700)
        self.addCleanup(self.tmp.cleanup)

    def test_no_temporary_or_partial_artifact_remains(self):
        gw.admit_run(date(2026, 10, 31),
                     datetime(2026, 10, 31, 0, 5, tzinfo=timezone.utc), dirpath=self.dir)
        leftovers = [n for n in os.listdir(self.dir) if n.endswith(".tmp")]
        self.assertEqual(leftovers, [])
        stored = json.loads(open(gw.receipt_path(date(2026, 10, 31), self.dir),
                                 encoding="utf-8").read())
        self.assertEqual(stored["schema"], "zeron-a-run-receipt/1")

    def test_duplicate_admission_never_overwrites_the_first_receipt(self):
        first = gw.admit_run(date(2026, 10, 31),
                             datetime(2026, 10, 31, 0, 5, tzinfo=timezone.utc), dirpath=self.dir)
        gw.finalize_run(date(2026, 10, 31), "STOP_NIGHTLY_CHECKPOINT",
                        datetime(2026, 10, 31, 3, 50, tzinfo=timezone.utc), dirpath=self.dir)
        dup = gw.admit_run(date(2026, 10, 31),
                           datetime(2026, 10, 31, 1, 30, tzinfo=timezone.utc), dirpath=self.dir)
        self.assertEqual(dup["status"], "DUPLICATE")
        stored = json.loads(open(gw.receipt_path(date(2026, 10, 31), self.dir),
                                 encoding="utf-8").read())
        self.assertEqual(stored["actual_start_utc"], first["receipt"]["actual_start_utc"])
        self.assertEqual(stored["finalized_utc"], "2026-10-31T03:50:00+00:00")


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
        mode = os.stat(g.receipt_path(date(2026, 10, 31), self.dir)).st_mode & 0o777
        self.assertEqual(mode, 0o600)  # finalize rewrite must keep the receipt private

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

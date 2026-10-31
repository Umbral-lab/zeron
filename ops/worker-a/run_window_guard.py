#!/usr/bin/env python3
"""A-side nightly run-window guard and receipt (OPS-001A).

Deterministic, stdlib-only helper implementing the time rules from
docs/OPERATIONS.md and ops/policy.json for worker A on A's host:

- one run per project local date (Europe/Madrid), persisted idempotent
  admission receipt created with exclusive atomic open before any work;
- deadline = earlier of the local 05:00 instant and 4 elapsed hours after
  the nominal 01:00 start, timezone-aware and monotonic (no fixed UTC offset);
- late starts admitted only within the 15-minute grace, keeping the original
  deadline; later starts are skipped for that night;
- phase cutoffs derived from the effective deadline;
- a finalized receipt refuses any further work on the same run.

This is A's own evidence and self-discipline instrument, NOT the operator's
enforcement snapshot. Per docs/OPERATIONS.md, editing this file cannot change
launcher enforcement; the operator-owned controller remains authoritative.

Receipts live outside the repository (default $ZERON_A_STATE_DIR, else
$HERMES_HOME/state/zeron-worker-a, else ~/.zeron-worker-a/state). Commit only
sanitized summaries.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PROJECT = "Umbral-lab/zeron"
ZONE_NAME = "Europe/Madrid"
NOMINAL_START_LOCAL = (1, 0)
LOCAL_CLOSE_LOCAL = (5, 0)
MAX_ELAPSED = timedelta(hours=4)
LATE_GRACE = timedelta(minutes=15)
FREEZE_BEFORE = timedelta(minutes=60)
CLOSE_FINDINGS_BEFORE = timedelta(minutes=40)
INTEGRATION_BEFORE = timedelta(minutes=15)
SHUTDOWN_BEFORE = timedelta(minutes=5)


def zone():
    return ZoneInfo(ZONE_NAME)


def state_dir():
    d = os.environ.get("ZERON_A_STATE_DIR")
    if not d:
        hh = os.environ.get("HERMES_HOME") or os.path.expanduser("~/.zeron-worker-a")
        d = os.path.join(hh, "state", "zeron-worker-a")
    os.makedirs(d, exist_ok=True)
    return d


def compute_window(date_obj):
    """Return timing facts for a project local date (datetime.date)."""
    nominal = datetime(
        date_obj.year, date_obj.month, date_obj.day,
        NOMINAL_START_LOCAL[0], NOMINAL_START_LOCAL[1], tzinfo=zone(),
    )
    local_close = datetime(
        date_obj.year, date_obj.month, date_obj.day,
        LOCAL_CLOSE_LOCAL[0], LOCAL_CLOSE_LOCAL[1], tzinfo=zone(),
    )
    deadline = min(local_close, nominal + MAX_ELAPSED)
    return {
        "run_id": f"{PROJECT}:{date_obj.isoformat()}",
        "local_date": date_obj.isoformat(),
        "zone": ZONE_NAME,
        "nominal_start_utc": nominal.astimezone(timezone.utc).isoformat(),
        "local_close_utc": local_close.astimezone(timezone.utc).isoformat(),
        "deadline_utc": deadline.astimezone(timezone.utc).isoformat(),
        "max_elapsed_hours": (deadline - nominal).total_seconds() / 3600.0,
        "phases": {
            "freeze_utc": (deadline - FREEZE_BEFORE).astimezone(timezone.utc).isoformat(),
            "close_findings_utc": (deadline - CLOSE_FINDINGS_BEFORE).astimezone(timezone.utc).isoformat(),
            "integration_utc": (deadline - INTEGRATION_BEFORE).astimezone(timezone.utc).isoformat(),
            "shutdown_utc": (deadline - SHUTDOWN_BEFORE).astimezone(timezone.utc).isoformat(),
        },
    }


def start_status(window, actual_start_utc):
    """Admission verdict for an actual UTC start instant."""
    nominal = datetime.fromisoformat(window["nominal_start_utc"])
    deadline = datetime.fromisoformat(window["deadline_utc"])
    actual = actual_start_utc.astimezone(timezone.utc)
    delta = actual - nominal
    max_elapsed = timedelta(hours=window["max_elapsed_hours"])
    if delta < timedelta(0):
        return {"verdict": "EARLY", "elapsed_h": round(delta.total_seconds() / 3600.0, 4),
                "remaining_h": round((deadline - actual).total_seconds() / 3600.0, 4),
                "note": "before nominal start; no unattended product work before 01:00 local"}
    if delta <= LATE_GRACE:
        return {"verdict": "OK" if delta <= timedelta(minutes=1) else "OK_LATE_GRACE",
                "elapsed_h": round(delta.total_seconds() / 3600.0, 4),
                "remaining_h": round((deadline - actual).total_seconds() / 3600.0, 4),
                "note": "original deadline kept"}
    if actual < deadline:
        return {"verdict": "SKIP_LATE_START", "elapsed_h": round(delta.total_seconds() / 3600.0, 4),
                "remaining_h": round((deadline - actual).total_seconds() / 3600.0, 4),
                "note": "start beyond 15-minute grace; OPERATIONS.md: skip that night, no catch-up wake"}
    return {"verdict": "SKIP_WINDOW_CLOSED", "elapsed_h": round(delta.total_seconds() / 3600.0, 4),
            "remaining_h": round((deadline - actual).total_seconds() / 3600.0, 4),
            "note": "window already closed at start"}


def phase_at(window, now_utc):
    deadline = datetime.fromisoformat(window["deadline_utc"])
    now = now_utc.astimezone(timezone.utc)
    if now >= deadline:
        return "past-deadline"
    if now >= deadline - SHUTDOWN_BEFORE:
        return "shutdown"
    if now >= deadline - INTEGRATION_BEFORE:
        return "integration-report"
    if now >= deadline - CLOSE_FINDINGS_BEFORE:
        return "close-findings"
    if now >= deadline - FREEZE_BEFORE:
        return "freeze-audit"
    if now >= datetime.fromisoformat(window["nominal_start_utc"]) + timedelta(minutes=10):
        return "build"
    return "preflight"


def receipt_path(date_obj, dirpath=None):
    base = dirpath or state_dir()
    return os.path.join(base, f"run-{date_obj.isoformat()}.json")


def admit_run(date_obj, actual_start_utc, dirpath=None, dry_run=False):
    """Persist admission before work. Idempotent per local date via O_EXCL."""
    window = compute_window(date_obj)
    status = start_status(window, actual_start_utc)
    path = receipt_path(date_obj, dirpath)
    receipt = {
        "schema": "zeron-a-run-receipt/1",
        "run_id": window["run_id"],
        "project": PROJECT,
        "local_date": window["local_date"],
        "zone": ZONE_NAME,
        "nominal_start_utc": window["nominal_start_utc"],
        "actual_start_utc": actual_start_utc.astimezone(timezone.utc).isoformat(),
        "deadline_utc": window["deadline_utc"],
        "max_elapsed_hours": window["max_elapsed_hours"],
        "phases": window["phases"],
        "start_admission": status["verdict"],
        "start_admission_note": status["note"],
        "remaining_h_at_start": status["remaining_h"],
        "final_state": None,
        "stop_reason": None,
        "finalized_utc": None,
    }
    if dry_run:
        return {"status": "DRY_RUN", "window": window, "start_admission": status, "receipt": receipt}
    payload = json.dumps(receipt, indent=1) + "\n"
    fd = None
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        existing = json.loads(open(path, encoding="utf-8").read())
        return {"status": "DUPLICATE", "message": "same-date admission exists; reused, not re-dispatched",
                "window": window, "existing": existing}
    try:
        os.write(fd, payload.encode("utf-8"))
    finally:
        os.close(fd)
    return {"status": "ADMITTED", "window": window, "start_admission": status, "receipt": receipt}


def assert_can_work(date_obj, now_utc, dirpath=None):
    """Refuse to continue a run that was never admitted or was finalized."""
    path = receipt_path(date_obj, dirpath)
    if not os.path.exists(path):
        raise RuntimeError(f"no admission receipt for {date_obj.isoformat()}; call admit first")
    r = json.loads(open(path, encoding="utf-8").read())
    if r.get("final_state") == "FINALIZED":
        raise RuntimeError(f"run {r['run_id']} is finalized; further writes refused")
    deadline = datetime.fromisoformat(r["deadline_utc"])
    if now_utc.astimezone(timezone.utc) >= deadline:
        raise RuntimeError(f"run {r['run_id']} past deadline {r['deadline_utc']}; stop")
    return r


def finalize_run(date_obj, stop_reason, now_utc, dirpath=None):
    path = receipt_path(date_obj, dirpath)
    if not os.path.exists(path):
        raise RuntimeError(f"no admission receipt for {date_obj.isoformat()}; nothing to finalize")
    r = json.loads(open(path, encoding="utf-8").read())
    r["final_state"] = "FINALIZED"
    r["stop_reason"] = stop_reason
    r["finalized_utc"] = now_utc.astimezone(timezone.utc).isoformat()
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(r, indent=1) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    return r


def parse_utc(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zone())
    return dt.astimezone(timezone.utc)


def main(argv=None):
    # A naive local time is interpreted in Europe/Madrid, never as a fixed UTC offset.
    p = argparse.ArgumentParser(description="Zeron worker A run-window guard")
    sub = p.add_subparsers(dest="cmd", required=True)
    pw = sub.add_parser("window"); pw.add_argument("date")
    pa = sub.add_parser("admit"); pa.add_argument("date"); pa.add_argument("--actual-start", default=None); pa.add_argument("--dry-run", action="store_true")
    ps = sub.add_parser("status"); ps.add_argument("date"); ps.add_argument("--now", default=None)
    pf = sub.add_parser("finalize"); pf.add_argument("date"); pf.add_argument("--stop-reason", required=True); pf.add_argument("--now", default=None)
    a = p.parse_args(argv)
    date_obj = datetime.strptime(a.date, "%Y-%m-%d").date()
    now = parse_utc(a.now) if getattr(a, "now", None) else datetime.now(timezone.utc)
    if a.cmd == "window":
        print(json.dumps(compute_window(date_obj), indent=1))
    elif a.cmd == "admit":
        actual = parse_utc(a.actual_start) if a.actual_start else datetime.now(timezone.utc)
        print(json.dumps(admit_run(date_obj, actual, dry_run=a.dry_run), indent=1))
    elif a.cmd == "status":
        w = compute_window(date_obj)
        path = receipt_path(date_obj)
        exists = os.path.exists(path)
        r = json.loads(open(path, encoding="utf-8").read()) if exists else None
        print(json.dumps({"window": w, "receipt_exists": exists,
                          "admission": (r or {}).get("start_admission"),
                          "final_state": (r or {}).get("final_state"),
                          "phase": phase_at(w, now)}, indent=1))
    elif a.cmd == "finalize":
        print(json.dumps(finalize_run(date_obj, a.stop_reason, now), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

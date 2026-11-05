#!/usr/bin/env python3
"""Local B wake-up, not A's shared controller. One conservative Sol job/night."""
import argparse
from datetime import datetime, timedelta, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from zeron_nightly_publish import checkpoint, finalize, publish, render

HOME = Path('/home/jetson/.hermes/profiles/zeron')
ROOT = Path('/home/jetson/Dev/zeron')
STATE = HOME / 'nightly'
ZONE = ZoneInfo('Europe/Madrid')
MODEL = 'gpt-6.1-sol'
MAX_REQUESTS = 4
MAX_SECONDS = 600
MAX_OUTPUT = 1000  # Reserve fully before dispatch; aggregate <=4,000.
PUBLICATION_SECONDS = 180  # Included in, not added to, the existing ten-minute cap.


def window(now):
    local = now.astimezone(ZONE)
    start = local.replace(hour=1, minute=0, second=0, microsecond=0)
    nominal = start.astimezone(timezone.utc)
    end = min(local.replace(hour=5, minute=0, second=0, microsecond=0).astimezone(timezone.utc),
              nominal + timedelta(hours=4))
    admit = nominal <= now.astimezone(timezone.utc) <= nominal + timedelta(minutes=15)
    return start.date().isoformat(), admit, end


def save(path, value):
    temp = path.with_name(path.name + '.' + str(os.getpid()) + '.new')
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(temp, flags, 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def quota():
    try:
        result = subprocess.run(['hermes', 'usage', '--provider', 'openai-codex', '--json'],
                                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode:
        return None
    try:
        data = json.loads(result.stdout)
        if data.get('source') != 'usage_api' or not data.get('windows'):
            return None
        return data
    except (ValueError, KeyError):
        return None


def quota_override_active(ledger, now=None):
    now = now or datetime.now(timezone.utc)
    approval = ledger.get('quota_reserve_override') or {}
    return (approval.get('date') == ledger.get('date') == now.astimezone(ZONE).date().isoformat()
            and approval.get('expires_at', 0) > now.timestamp())


def quota_check(ledger, sample):
    # UNKNOWN cannot clear a previously observed block.
    if sample is None:
        if ledger.get('blocked'):
            raise RuntimeError('Known route/quota block survives UNKNOWN')
        return
    windows = sample['windows']
    override = quota_override_active(ledger)
    for item in windows:
        if float(item['used_percent']) >= 100:
            ledger['blocked'] = 'Observed provider allowance exhaustion'
            raise RuntimeError(ledger['blocked'])
        if float(item['used_percent']) >= 70 and not override:
            ledger['blocked'] = 'Quota reserve reached'
            raise RuntimeError(ledger['blocked'])
    baseline = ledger.setdefault('quota_baseline', windows)
    old = {(w['label'], w.get('resets_at')): float(w['used_percent']) for w in baseline}
    for item in windows:
        key = (item['label'], item.get('resets_at'))
        limit = 2 if 'week' in item['label'].lower() else 10
        if key in old and float(item['used_percent']) - old[key] >= limit:
            ledger['blocked'] = 'Observed nightly account consumption threshold reached'
            raise RuntimeError(ledger['blocked'])
    if override and ledger.get('blocked') == 'Quota reserve reached':
        ledger['reserve_block_overridden_for_date'] = ledger['date']
        ledger.pop('blocked')
    if ledger.get('blocked'):
        raise RuntimeError(ledger['blocked'])


def reconcile_reserve_block(record, sample, now):
    """Under worker-b.lock, clear only a reserve block proven recovered by live usage.

    This is not a quota override: UNKNOWN, auth/payment failures and the
    current run's consumption/call counters remain blocking.
    """
    import math
    block_path = STATE / 'route-block.json'
    if not block_path.exists():
        return False
    block = json.loads(block_path.read_text())
    if block.get('reason') != 'Quota reserve reached' or not isinstance(sample, dict):
        return False
    try:
        if sample.get('source') != 'usage_api':
            return False
        fetched = datetime.fromisoformat(sample['fetched_at'])
        if fetched.tzinfo is None or not 0 <= (now - fetched).total_seconds() <= 300:
            return False
        windows = sample['windows']
        labels = [w['label'].strip().lower() for w in windows]
        if not {'session', 'weekly'}.issubset(labels) or len(set(labels)) != len(labels):
            return False
        for item in windows:
            used = float(item['used_percent'])
            reset = datetime.fromisoformat(item['resets_at'])
            if (isinstance(item['used_percent'], bool) or not math.isfinite(used)
                    or not 0 <= used < 70 or reset.tzinfo is None or reset <= now):
                return False
    except (ValueError, TypeError, KeyError, AttributeError):
        return False
    probe = json.loads(json.dumps(record))
    if probe.get('blocked') == 'Quota reserve reached':
        probe.pop('blocked')
    try:
        quota_check(probe, sample)
    except RuntimeError:
        return False
    archive = STATE / ('route-block.recovered.' + now.strftime('%Y%m%dT%H%M%S%f') + '.json')
    save(archive, {'previous_block': block, 'reconciled_at': now.isoformat(), 'usage': sample})
    os.chmod(archive, 0o600)
    block_path.unlink()
    record.update(probe)
    record.pop('blocked', None)
    record['route_block_reconciled_at'] = now.isoformat()
    return True


def reserve(path, model, requested_output, sample):
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(path.read_text())
        try:
            if (time.time() >= min(ledger['deadline'], ledger.get('inference_deadline', ledger['deadline']))
                    or time.monotonic() >= ledger['monotonic_deadline']):
                raise RuntimeError('Hard deadline reached')
            if model != MODEL:
                raise RuntimeError('Unapproved inference route/model')
            quota_check(ledger, sample)
            if ledger['requests'] >= MAX_REQUESTS:
                raise RuntimeError('Provider attempt cap reached')
            output = min(int(requested_output or MAX_OUTPUT), MAX_OUTPUT)
            if output <= 0 or ledger['reserved_generated'] + output > 4000:
                raise RuntimeError('Generated output reservation exhausted')
            ledger['requests'] += 1
            ledger['reserved_generated'] += output
            ledger['last_attempt_at'] = datetime.now(timezone.utc).isoformat()
            save(path, ledger)
            return output
        except RuntimeError as exc:
            ledger['stop_reason'] = str(exc)
            save(path, ledger)
            if ledger.get('blocked') == 'Quota reserve reached':
                save(STATE / 'route-block.json', {'reason': ledger['blocked']})
            raise


def install_guard():
    """Guard installed HTTP client sends, including SDK retries and helpers."""
    import httpx
    ledger = Path(os.environ['ZERON_NIGHTLY_LEDGER'])
    sync_send, async_send = httpx.Client.send, httpx.AsyncClient.send

    def prepare(request):
        host = request.url.host
        path = request.url.path
        if request.method == 'POST' and path.endswith('/responses'):
            if host != 'chatgpt.com' or not path.startswith('/backend-api/codex/'):
                raise SystemExit('Nightly guard: paid/alternate inference route denied')
            body = request.read()
            if request.headers.get('content-encoding') == 'zstd':
                from compression import zstd
                body = zstd.decompress(body)
            data = json.loads(body)
            maximum = reserve(ledger, data.get('model'), data.get('max_output_tokens'), quota())
            data['max_output_tokens'] = maximum
            # No premium/priority speed and no automatic model substitution.
            data.pop('service_tier', None)
            encoded = json.dumps(data).encode()
            request._content = encoded
            request.stream = httpx.ByteStream(encoded)
            request.headers.pop('content-encoding', None)
            request.headers['Content-Length'] = str(len(encoded))
            return
        # GitHub handoffs and non-inference official OAuth/usage are allowed.
        if host == 'api.github.com':
            return
        if host == 'auth.openai.com' and path.startswith('/oauth/'):
            return
        if host == 'chatgpt.com' and request.method == 'GET' and ('usage' in path or 'models' in path):
            return
        raise SystemExit('Nightly guard: unapproved HTTP route denied')

    def send(client, request, *args, **kwargs):
        try:
            prepare(request)
        except RuntimeError as exc:
            raise SystemExit('Nightly guard: ' + str(exc))
        response = sync_send(client, request, *args, **kwargs)
        record_response(response)
        return response

    async def async_wrapper(client, request, *args, **kwargs):
        try:
            prepare(request)
        except RuntimeError as exc:
            raise SystemExit('Nightly guard: ' + str(exc))
        response = await async_send(client, request, *args, **kwargs)
        record_response(response)
        return response

    def record_response(response):
        if response.status_code in (401, 403, 402, 429):
            with ledger.with_suffix('.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX)
                data = json.loads(ledger.read_text())
                data['blocked'] = 'Provider auth/payment/quota status ' + str(response.status_code)
                save(ledger, data)
                save(STATE / 'route-block.json', {'reason': data['blocked']})
            raise SystemExit('Nightly guard: route parked; no retry')

    httpx.Client.send = send
    httpx.AsyncClient.send = async_wrapper
    # Disable optional model helpers/fallbacks in this process, not the chat profile.
    import hermes_cli.cli_config_load as config_module
    original = config_module.load_cli_config

    def configured():
        cfg = original()
        cfg['fallback_providers'] = []
        cfg.pop('fallback_model', None)
        cfg['model'] = dict(cfg.get('model') or {}, default=MODEL, provider='openai-codex', max_tokens=MAX_OUTPUT)
        agent = cfg.setdefault('agent', {})
        agent.update(api_max_retries=0, auto_recovery_cycles=0, max_turns=3,
                     run_budget_seconds=360, max_verify_nudges=0)
        cfg.setdefault('auxiliary', {}).setdefault('title_generation', {})['enabled'] = False
        cfg['auxiliary'].setdefault('background_review', {})['enabled'] = False
        cfg['mcp_servers'] = {}
        return cfg

    config_module.load_cli_config = configured


def run_worker():
    # Embedded supported AIAgent API: CLI chats in this installed Hermes version
    # run through a separate gateway process and would bypass local HTTP guards.
    install_guard()
    from hermes_cli.runtime_provider import resolve_runtime_provider
    from hermes_constants import parse_reasoning_effort
    from run_agent import AIAgent
    route = resolve_runtime_provider(requested='openai-codex', target_model=MODEL)
    if route.get('provider') != 'openai-codex' or route.get('api_mode') != 'codex_responses':
        raise SystemExit('Nightly guard: unexpected runtime/provider; no inference dispatched')
    smoke = os.environ.get('ZERON_NIGHTLY_SMOKE') == '1'
    agent = AIAgent(model=MODEL, provider=route['provider'], api_mode=route['api_mode'],
                    api_key=route.get('api_key'), base_url=route.get('base_url'),
                    credential_pool=route.get('credential_pool'), requested_provider='openai-codex',
                    enabled_toolsets=[] if smoke else ['terminal', 'file'],
                    skip_context_files=smoke, skip_memory=True, skip_background_review=True,
                    quiet_mode=True, max_iterations=1 if smoke else 3, max_tokens=MAX_OUTPUT,
                    reasoning_config=parse_reasoning_effort('medium'),
                    run_budget_seconds=45 if smoke else 360, platform='cron', cwd=str(ROOT))
    task = 'Setup connectivity test only: reply READY, do not call tools.' if smoke else (HOME / 'nightly-task.md').read_text()
    if not smoke:
        source = os.environ['ZERON_NIGHTLY_SOURCE']
        task += '\nPINNED SOURCE: ' + source + '\nUse git show ' + source + ':<path>; the local checkout branch is not the reviewed source.\n'
    try:
        result = agent.run_conversation(task)
        print(result.get('final_response', ''))
        if not smoke:
            save(Path(os.environ['ZERON_NIGHTLY_RESULT']), checkpoint(result))
        if result.get('failed'):
            raise SystemExit('Nightly worker reported failure')
    finally:
        agent.close()


def supervise(command, cutoff, log):
    with log.open('w') as output:
        child = subprocess.Popen(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        try:
            return child.wait(timeout=max(0.01, cutoff - time.monotonic() - 5))
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                return child.wait(timeout=max(0.01, cutoff - time.monotonic()))
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                return 124


def finish_run(receipt, result_path, result, cutoff):
    """Always checkpoint and attempt handoff, even after budget exhaustion."""
    record = json.loads(receipt.read_text())
    record.update(returncode=result, finished_at=datetime.now(timezone.utc).isoformat())
    packet = json.loads(result_path.read_text()) if result_path.exists() else {
        'status': 'partial', 'handoff_status': 'pending',
        'reason': 'Worker exited without a result checkpoint', 'report': ''}
    if result != 0:
        packet['status'] = 'partial'
        packet['reason'] = 'Worker interrupted or failed; preserving available checkpoint'
    report_path = STATE / (record['date'] + '-report.md')
    fd = os.open(report_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    os.fchmod(fd, 0o600)
    with os.fdopen(fd, 'w') as stream:
        stream.write(render(record, packet))
        stream.flush()
        os.fsync(stream.fileno())
    packet['local_report'] = str(report_path)
    save(result_path, packet)  # Publication failure cannot erase the local report.
    try:
        publish(record, packet, cutoff)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        packet['handoff_status'] = 'failed'
        packet['publication_error'] = type(exc).__name__ + ': ' + str(exc)
    code = finalize(record, packet)
    save(result_path, packet)
    save(receipt, record)
    if code == 0:
        save(STATE / 'last-completed-source.json',
             {'source': record['source'], 'result_packet': str(result_path)})
    print(json.dumps({'run_id': record['run_id'], 'state': record['state'],
                      'requests': record['requests'], 'handoff_status': record['handoff_status'],
                      'issue_url': packet.get('issue_url'), 'pr_url': packet.get('pr_url'),
                      'local_report': str(report_path)}))
    return code


def resume_allowed(record, now):
    """Operator-only recovery of a proven pre-model failure, never an inference retry."""
    local = now.astimezone(ZONE)
    _, _, end = window(now)
    return (local.hour >= 1 and now.astimezone(timezone.utc) < end
            and (record.get('state') == 'preflight_failed'
                 or (record.get('state') == 'blocked'
                     and record.get('route_block_reconciled_at')
                     and not record.get('blocked')
                     and record.get('date') == local.date().isoformat()))
            and record.get('requests', 0) == 0 and record.get('reserved_generated', 0) == 0
            and not record.get('model_started_at') and not record.get('owner_resume_count')
            and record.get('preflight_attempts', 0) < 2)


def fetch_source(receipt, record):
    """Persist BEFORE I/O and permit only one durable transient transport retry."""
    transient = ('could not resolve host', 'temporary failure in name resolution',
                 'failed to connect', 'connection timed out', 'connection reset',
                 'network is unreachable')
    while record.get('preflight_attempts', 0) < 2:
        record['preflight_attempts'] = record.get('preflight_attempts', 0) + 1
        record['state'] = 'preflight'
        save(receipt, record)
        try:
            done = subprocess.run(['git', 'fetch', 'origin', 'main'], cwd=ROOT,
                                  capture_output=True, text=True, timeout=30)
            if done.returncode == 0:
                source = subprocess.check_output(['git', 'rev-parse', 'origin/main'],
                                                 cwd=ROOT, text=True, timeout=10).strip()
                import re
                if not re.fullmatch(r'[0-9a-f]{40}', source):
                    raise ValueError('Invalid fetched revision')
                record.update(source=source, state='admitted', preflight_status='passed')
                save(receipt, record)
                return source
            error = done.stderr.strip()[:1000]
            retryable = any(term in error.lower() for term in transient)
        except subprocess.TimeoutExpired:
            error, retryable = 'Repository fetch timed out', True
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            error, retryable = 'Repository preflight failed: ' + type(exc).__name__, False
        record.update(state='preflight_failed', preflight_status='failed', preflight_error=error)
        save(receipt, record)
        if not retryable or record['preflight_attempts'] >= 2:
            return None
        time.sleep(2)
    return None


def notify_preflight_failure(receipt, record, cutoff):
    """Best effort only: a network outage must still leave private durable evidence."""
    from zeron_nightly_publish import api, sanitize
    record['preflight_notice_attempted'] = True
    save(receipt, record)
    body = ('B startup state ' + record.get('state', 'failed') + ' for ' + record['run_id']
            + '. No model was dispatched. Fetch attempts: ' + str(record.get('preflight_attempts', 0))
            + '. ' + sanitize(record.get('blocked') or record.get('preflight_error', 'Unknown startup error')))
    try:
        result = api('POST', 'repos/Umbral-lab/zeron/issues/4/comments', {'body': body}, cutoff)
        actual = api('GET', 'repos/Umbral-lab/zeron/issues/comments/' + str(result['id']), None, cutoff)
        if actual['body'] != body or actual['user']['login'] != 'umbral-labs-dev[bot]':
            raise RuntimeError('Preflight notice verification failed')
        record['preflight_notice'] = actual['html_url']
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        record['preflight_notice_error'] = type(exc).__name__
    save(receipt, record)


def quota_resume_allowed(record, now):
    local = now.astimezone(ZONE)
    _, _, end = window(now)
    return (local.date().isoformat() == '2026-11-01' and local.hour >= 1
            and now.astimezone(timezone.utc) < end
            and record.get('state') == 'blocked' and record.get('blocked') == 'Quota reserve reached'
            and record.get('requests', 0) == 0 and record.get('reserved_generated', 0) == 0
            and record.get('preflight_status') == 'passed' and record.get('source')
            and not record.get('model_started_at') and not record.get('owner_quota_override_count'))


def launch(owner_resume=False, quota_override=False):
    started = time.monotonic()
    now = datetime.now(timezone.utc)
    date, admitted, end = window(now)
    if not admitted and not (owner_resume or quota_override):
        print('SKIP: outside 01:00–01:15 Europe/Madrid admission window')
        return 0
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (STATE / 'worker-b.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('SKIP: B already active')
            return 0
        receipt = STATE / (date + '.json')
        if receipt.exists():
            record = json.loads(receipt.read_text())
            if owner_resume and record.get('state') == 'blocked':
                reconcile_reserve_block(record, quota(), datetime.now(timezone.utc))
            if quota_override:
                if not quota_resume_allowed(record, now):
                    raise RuntimeError('This one-night quota override cannot admit this record')
                record.update(owner_quota_override_count=1,
                              quota_reserve_override={'date': date, 'expires_at': end.timestamp(),
                              'approved_at': now.isoformat(),
                              'authorization': 'Owner explicitly instructed: override that limit, just for tonight'})
            else:
                if not owner_resume or not resume_allowed(record, now):
                    print('SKIP: existing admission cannot be retried or refilled')
                    return 0
                record.update(owner_resume_count=1, owner_resume_at=now.isoformat(),
                              owner_resume_reason='Explicit owner instruction to repair and resume this pre-model failure')
        else:
            if owner_resume or quota_override:
                raise RuntimeError('Owner recovery requires a recorded pre-model failure')
            record = {'run_id': 'zeron:B:' + date, 'date': date, 'source': None,
                      'requests': 0, 'reserved_generated': 0, 'preflight_attempts': 0,
                      'state': 'preflight', 'first_started_at': now.isoformat(),
                      'model': MODEL, 'quota_metrics': 'UNKNOWN unless observed',
                      'input_token_ceiling': 'UNKNOWN; independent request/output/time limits enforced'}
        allowance = max(0, MAX_SECONDS - record.get('prior_active_seconds', 0))
        cutoff = min(time.monotonic() + max(0, end.timestamp() - time.time()), started + allowance)
        deadline = time.time() + max(0, cutoff - time.monotonic())
        record.update(deadline=deadline, inference_deadline=deadline-PUBLICATION_SECONDS,
                      monotonic_deadline=cutoff)
        save(receipt, record)  # Admission exists before any network/tool operation.
        result_packet = STATE / (date + '-result.json')
        save(result_packet, {'status': 'partial', 'handoff_status': 'pending',
                             'reason': 'Repository preflight in progress; no inference dispatched', 'report': ''})
        if (STATE / 'route-block.json').exists():
            reconcile_reserve_block(record, quota(), datetime.now(timezone.utc))
        if (STATE / 'route-block.json').exists():
            block = json.loads((STATE / 'route-block.json').read_text())
            if block.get('reason') != 'Quota reserve reached' or not quota_override_active(record, now):
                record['state'] = 'blocked'
                record['blocked'] = block.get('reason', 'Unknown route block')
                save(receipt, record)
                print('BLOCKED: route parked pending operator reconciliation')
                return 1
        if quota_override:
            source = record['source']  # Reuse the successful preflight; do not reset/retry network counters.
            record['state'] = 'admitted'
            save(receipt, record)
        else:
            source = fetch_source(receipt, record)
        if source is None:
            record.update(returncode=1, finished_at=datetime.now(timezone.utc).isoformat())
            save(receipt, record)
            save(result_packet, {'status': 'partial', 'handoff_status': 'pending',
                                 'reason': record.get('preflight_error'), 'report': 'No model dispatched.'})
            notify_preflight_failure(receipt, record, cutoff)
            print('PREFLIGHT FAILED: durable receipt retained; no model dispatched')
            return 1
        completed = STATE / 'last-completed-source.json'
        if completed.exists() and json.loads(completed.read_text()).get('source') == source:
            record['state'] = 'skipped_no_work'
            save(receipt, record)
            print('SKIP: assigned source-audit task already completed for unchanged main')
            return 0
        if cutoff - time.monotonic() <= PUBLICATION_SECONDS + 15:
            record['state'] = 'blocked_deadline'
            save(receipt, record)
            return 1
        try:
            quota_check(record, quota())
        except RuntimeError:
            record.update(state='blocked', returncode=1, finished_at=datetime.now(timezone.utc).isoformat())
            save(receipt, record)
            save(result_packet, {'status': 'partial', 'handoff_status': 'pending',
                                 'reason': record.get('blocked', 'Quota admission blocked'),
                                 'report': 'No model dispatched; startup completed but quota policy blocks admission.'})
            if record.get('blocked') == 'Quota reserve reached':
                save(STATE / 'route-block.json', {'reason': record['blocked']})
            notify_preflight_failure(receipt, record, cutoff)
            record['prior_active_seconds'] = record.get('prior_active_seconds', 0) + (time.monotonic() - started)
            save(receipt, record)
            return 1
        save(receipt, record)
        result_packet = STATE / (date + '-result.json')
        save(result_packet, {'status': 'partial', 'handoff_status': 'pending',
                             'reason': 'Admitted; worker has not produced a checkpoint', 'report': ''})
        os.environ['ZERON_NIGHTLY_RESULT'] = str(result_packet)
        os.environ['ZERON_NIGHTLY_SOURCE'] = source
        os.environ['ZERON_NIGHTLY_LEDGER'] = str(receipt)
        os.environ['HERMES_HOME'] = str(HOME)
        runtime = json.loads(subprocess.check_output(['hermes', '--print-runtime-command'], text=True))
        # Use the installed, bootstrapped interpreter; insert the guard BEFORE CLI import.
        code = runtime[-1]
        marker = "runpy.run_module('hermes_cli.main', run_name='__main__', alter_sys=True)"
        if marker not in code:
            raise RuntimeError('Installed runtime launcher changed; refuse unguarded launch')
        guarded = "runpy.run_path(" + repr(str(Path(__file__).resolve())) + ", run_name='zeron_guard')['run_worker']()"
        runtime[-1] = code.replace(marker, guarded)
        record['model_started_at'] = datetime.now(timezone.utc).isoformat()
        save(receipt, record)  # Zero recorded requests after this point is still an uncertain dispatch.
        result = supervise(runtime, cutoff - PUBLICATION_SECONDS, STATE / (date + '.log'))
        return finish_run(receipt, result_packet, result, cutoff)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--owner-resume', action='store_true',
                        help='Explicit operator recovery of a proven pre-model failure only')
    parser.add_argument('--owner-quota-override', action='store_true',
                        help='Owner-approved 2026-11-01 reserve-threshold exception only')
    args = parser.parse_args()
    if args.plan:
        day, admitted, end = window(datetime.now(timezone.utc))
        print(json.dumps({'date': day, 'admitted_now': admitted, 'window_deadline_utc': end.isoformat(),
                          'model': MODEL, 'maximum_requests': MAX_REQUESTS,
                          'maximum_job_seconds': MAX_SECONDS, 'maximum_generated_reservation': 4000}))
    else:
        raise SystemExit(launch(owner_resume=args.owner_resume, quota_override=args.owner_quota_override))

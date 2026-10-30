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

HOME = Path('/home/jetson/.hermes/profiles/zeron')
ROOT = Path('/home/jetson/Dev/zeron')
STATE = HOME / 'nightly'
ZONE = ZoneInfo('Europe/Madrid')
MODEL = 'gpt-6.1-sol'
MAX_REQUESTS = 4
MAX_SECONDS = 600
MAX_OUTPUT = 1000  # Reserve fully before dispatch; aggregate <=4,000.


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
    with temp.open('w') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def quota():
    result = subprocess.run(['hermes', 'usage', '--provider', 'openai-codex', '--json'],
                            capture_output=True, text=True, timeout=30)
    if result.returncode:
        return None
    try:
        data = json.loads(result.stdout)
        if data.get('source') != 'usage_api' or not data.get('windows'):
            return None
        return data
    except (ValueError, KeyError):
        return None


def quota_check(ledger, sample):
    # UNKNOWN cannot clear a previously observed block.
    if sample is None:
        if ledger.get('blocked'):
            raise RuntimeError('Known route/quota block survives UNKNOWN')
        return
    windows = sample['windows']
    for item in windows:
        if float(item['used_percent']) >= 70:
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
    if ledger.get('blocked'):
        raise RuntimeError(ledger['blocked'])


def reserve(path, model, requested_output, sample):
    with path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ledger = json.loads(path.read_text())
        try:
            if time.time() >= ledger['deadline'] or time.monotonic() >= ledger['monotonic_deadline']:
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
                     run_budget_seconds=540, max_verify_nudges=0)
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
                    run_budget_seconds=45 if smoke else 540, platform='cron', cwd=str(ROOT))
    task = 'Setup connectivity test only: reply READY, do not call tools.' if smoke else (HOME / 'nightly-task.md').read_text()
    try:
        result = agent.run_conversation(task)
        print(result.get('final_response', ''))
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


def launch():
    now = datetime.now(timezone.utc)
    date, admitted, end = window(now)
    if not admitted:
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
            print('SKIP: this local date already admitted; no retry/refill')
            return 0
        if (STATE / 'route-block.json').exists():
            print('BLOCKED: route parked pending operator reconciliation')
            return 1
        source = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/main'],
                                         cwd=ROOT, text=True, timeout=30).split()[0]
        completed = STATE / 'last-completed-source.json'
        if completed.exists() and json.loads(completed.read_text()).get('source') == source:
            print('SKIP: assigned source-audit task already completed for unchanged main')
            return 0
        deadline = min(end.timestamp(), time.time() + MAX_SECONDS)
        cutoff = time.monotonic() + max(0, deadline - time.time())
        record = {'run_id': 'zeron:B:' + date, 'requests': 0, 'reserved_generated': 0,
                  'deadline': deadline, 'monotonic_deadline': cutoff, 'state': 'admitted',
                  'model': MODEL, 'quota_metrics': 'UNKNOWN unless observed',
                  'input_token_ceiling': 'UNKNOWN; independent request/output/time limits enforced'}
        save(receipt, record)  # Crash and restart cannot reopen admission.
        try:
            quota_check(record, quota())
        except RuntimeError:
            record['state'] = 'blocked'
            save(receipt, record)
            if record.get('blocked') == 'Quota reserve reached':
                save(STATE / 'route-block.json', {'reason': record['blocked']})
            return 1
        save(receipt, record)
        prompt = HOME / 'nightly-task.md'
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
        result = supervise(runtime, cutoff, STATE / (date + '.log'))
        record = json.loads(receipt.read_text())
        record.update(state='finished' if result == 0 else 'interrupted', returncode=result,
                      finished_at=datetime.now(timezone.utc).isoformat())
        save(receipt, record)
        result_packet = STATE / (date + '-result.json')
        if result == 0 and result_packet.exists():
            packet = json.loads(result_packet.read_text())
            if packet.get('status') == 'complete' and packet.get('issue_url') and packet.get('pr_url'):
                save(completed, {'source': source, 'result_packet': str(result_packet)})
        print(json.dumps({'run_id': record['run_id'], 'state': record['state'],
                          'requests': record['requests'], 'log': str(STATE / (date + '.log'))}))
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    if args.plan:
        day, admitted, end = window(datetime.now(timezone.utc))
        print(json.dumps({'date': day, 'admitted_now': admitted, 'window_deadline_utc': end.isoformat(),
                          'model': MODEL, 'maximum_requests': MAX_REQUESTS,
                          'maximum_job_seconds': MAX_SECONDS, 'maximum_generated_reservation': 4000}))
    else:
        raise SystemExit(launch())

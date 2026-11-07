"""Publish a pinned review on the existing candidate PR, never a report-only PR."""
import json
from pathlib import Path
import re
import subprocess
import time

from zeron_audit import assess

REPO = 'Umbral-lab/zeron'
ACTOR = 'umbral-labs-dev[bot]'
HELPER = Path('/home/jetson/.hermes/profiles/zeron/scripts/zeron-github-app.py')


def sanitize(text):
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', str(text))
    text = re.sub(r'gh[pousr]_[A-Za-z0-9_]{20,}', '[REDACTED]', text)
    text = re.sub(r'(?i)(bearer\s+)[A-Za-z0-9._-]+', r'\1[REDACTED]', text)
    if '-----BEGIN ' in text and 'PRIVATE KEY-----' in text:
        raise ValueError('Refusing possible private key material')
    return text[:40000]


def checkpoint(result, record=None):
    packet = assess(result, record or {})
    packet['report'] = sanitize(packet['report'])
    return packet


def render(record, packet):
    candidate = record.get('candidate', {})
    lines = ['Worker B independent review: ' + packet.get('verdict', 'INCOMPLETE'),
             'Run: ' + record['run_id'],
             'Candidate: PR #' + str(candidate.get('number', 'UNKNOWN')),
             'Target base: ' + candidate.get('base', 'UNKNOWN'),
             'PR diff base: ' + candidate.get('diff_base', 'UNKNOWN'),
             'Head: ' + str(record.get('source', 'UNKNOWN')),
             'Acceptance: ' + packet['status'] + '; ' + packet.get('reason', ''),
             '\nExecuted checks:']
    for check in record.get('checks', []):
        lines.append('- `' + ' '.join(check['argv']) + '`: ' + check['status']
                     + ', exit=' + str(check.get('returncode'))
                     + ', log SHA256=' + check.get('sha256', 'NOT RUN'))
        if check.get('status') != 'passed':
            lines.append('```text\n' + check.get('tail', '')[-3000:] + '\n```')
    if not record.get('checks'):
        lines.append('- NOT RUN. No runtime acceptance claimed.')
    lines.extend(['\nReview:', packet.get('report', '') or 'No final model review available.',
                  '\nNo report-only branch, issue or PR was created. '
                  'A remains integrator. Approval applies only to the exact reviewed head.'])
    return sanitize('\n'.join(lines))


def api(method, path, payload, deadline):
    command = ['python3', str(HELPER), 'api', '--method', method, path]
    if payload is not None:
        command += ['--input', '-']
    for attempt in range(2):
        remaining = deadline - time.monotonic()
        if remaining < 3:
            raise TimeoutError('Publication deadline reached; checkpoint retained')
        try:
            result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                                    text=True, capture_output=True, timeout=min(30, remaining))
        except subprocess.TimeoutExpired:
            if method == 'GET' and attempt == 0:
                continue
            raise  # Never replay an uncertain write.
        if result.returncode:
            transient = any(word in result.stderr for word in ('ConnectionError', 'Timeout', 'Could not resolve'))
            if method == 'GET' and attempt == 0 and transient:
                continue
            raise RuntimeError('GitHub request failed: ' + method + ' ' + path)
        return json.loads(result.stdout) if result.stdout.strip() else None


def publish(record, packet, deadline, call=api):
    candidate = record.get('candidate')
    if not candidate:
        raise ValueError('Legacy source-report publication is disabled')
    head = candidate['head']
    if not re.fullmatch(r'[0-9a-f]{40}', head) or record['source'] != head:
        raise ValueError('Review source mismatch')
    path = f"repos/{REPO}/pulls/{candidate['number']}"
    actual = call('GET', path, None, deadline)
    if actual['state'] != 'open' or actual['head']['sha'] != head:
        raise RuntimeError('Candidate changed or closed; stale publication refused')
    if actual['user']['login'] != 'david-noether[bot]':
        raise RuntimeError('Not an independently reviewable A candidate')
    verdict = packet.get('verdict', 'INCOMPLETE')
    if verdict == 'APPROVE':
        checked = assess({'completed': True, 'final_response': json.dumps(packet.get('review'))}, record)
        if packet.get('status') != 'complete' or checked['verdict'] != 'APPROVE':
            raise ValueError('Incomplete or changed evidence cannot approve')
    event = {'APPROVE': 'APPROVE', 'CHANGES_REQUESTED': 'REQUEST_CHANGES',
             'INCOMPLETE': 'COMMENT'}[verdict]
    body = render(record, packet)
    review = call('POST', path + '/reviews',
                  {'commit_id': head, 'event': event, 'body': body}, deadline)
    packet['review_url'] = review['html_url']  # Preserve the handle before verification.
    verified = call('GET', path + '/reviews/' + str(review['id']), None, deadline)
    expected = {'APPROVE': 'APPROVED', 'REQUEST_CHANGES': 'CHANGES_REQUESTED', 'COMMENT': 'COMMENTED'}[event]
    if not (verified['user']['login'] == ACTOR and verified['body'] == body
            and verified['commit_id'] == head and verified['state'] == expected):
        raise RuntimeError('Remote review verification failed')
    packet.update(handoff_status='published', pr_url=actual['html_url'])
    return packet


def finalize(record, packet):
    published = packet.get('handoff_status') == 'published' and packet.get('review_url')
    complete = record['returncode'] == 0 and packet['status'] == 'complete' and published
    record.update(state='reviewed' if complete else 'partial',
                  review_verdict=packet.get('verdict', 'INCOMPLETE'),
                  review_url=packet.get('review_url'),
                  process_state='exited' if record['returncode'] == 0 else 'interrupted',
                  handoff_status=packet.get('handoff_status', 'pending'))
    return 0 if complete else 2

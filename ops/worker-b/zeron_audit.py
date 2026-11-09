"""Candidate discovery and executed checks. No inference or report-only Git commits."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

CONTRACT = 'candidate-review-v2'
BUILDER = 'david-noether[bot]'
REVIEWER = 'umbral-labs-dev[bot]'
PREFIX = 'repos/Umbral-lab/zeron'
SHA = re.compile(r'[0-9a-f]{40}')
CODE_SUFFIXES = {'.rs', '.py', '.toml', '.json', '.js', '.ts', '.tsx', '.sh'}


def code_paths(paths):
    return [p for p in paths if Path(p).suffix in CODE_SUFFIXES
            and not p.startswith(('docs/', 'ops/tasks/', 'ops/reviews/'))]


def select_candidate(call, deadline, blocked=None):
    """Review new A heads even when main is unchanged; never self-review B PRs."""
    pulls = call('GET', PREFIX + '/pulls?state=open&per_page=100', None, deadline)
    if len(pulls) >= 100:
        raise RuntimeError('PR discovery truncated; refuse a partial queue')
    eligible = []
    for pr in pulls:
        if pr['user']['login'] != BUILDER or pr.get('draft'):
            continue
        number = pr['number']
        if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
            raise ValueError('Invalid PR number')
        head, base = pr['head']['sha'], pr['base']['sha']
        if not SHA.fullmatch(head) or not SHA.fullmatch(base):
            raise ValueError('Invalid candidate revisions')
        reviews = call('GET', f'{PREFIX}/pulls/{number}/reviews?per_page=100', None, deadline)
        if len(reviews) >= 100:
            raise RuntimeError('Review discovery truncated')
        decisive = [r for r in reviews if r['user']['login'] == REVIEWER
                    and r.get('commit_id') == head
                    and r['state'] in ('APPROVED', 'CHANGES_REQUESTED')]
        if decisive:
            continue  # Wait for a changed head; do not repeat the same verdict nightly.
        files = call('GET', f'{PREFIX}/pulls/{number}/files?per_page=100', None, deadline)
        if len(files) >= 100:
            raise RuntimeError('Candidate file list truncated')
        paths = [f['filename'] for f in files]
        code = code_paths(paths)
        if not code:
            continue  # No model calls or report PRs for an idle/docs-only queue.
        if len(code) > 12 or not check_plan(paths):
            reason = (f'{len(code)} changed code files exceed the 12-file bounded review scope; narrow/split the candidate'
                      if len(code) > 12 else 'No supported executable check plan')
            if blocked is not None:
                marker = f'[{CONTRACT}:{head}]'
                blocked.append({'number': number, 'head': head, 'base': base,
                                'url': pr['html_url'], 'reason': reason,
                                'already_notified': any(marker in r.get('body', '')
                                    for r in reviews if r['user']['login'] == REVIEWER)})
            continue
        eligible.append({'number': number, 'head': head, 'base': base,
                         'url': pr['html_url'], 'title': pr['title'],
                         'paths': paths, 'code_paths': code,
                         'updated_at': pr.get('updated_at', ''),
                         'prior_reviews': [{'head': r.get('commit_id'), 'state': r['state'],
                                            'body': r.get('body', '')[-3500:]}
                                           for r in reviews if r['user']['login'] == REVIEWER][-2:]})
    # Product changes before ops; freshest eligible candidate within each group.
    eligible.sort(key=lambda c: c['updated_at'], reverse=True)
    eligible.sort(key=lambda c: not any(p.startswith(('crates/', 'apps/')) for p in c['code_paths']))
    return eligible[0] if eligible else None


def check_plan(paths):
    """Fixed argv only: PR text cannot inject commands into the controller."""
    plans = []
    def add(argv):
        if argv not in plans:
            plans.append(argv)
    if any(p.startswith(('crates/update/', 'crates/engine/')) for p in paths):
        add(['cargo', 'test', '--locked', '-p', 'zeron-update', '--', '--test-threads=1'])
        add(['cargo', 'test', '--locked', '-p', 'zeron-engine', '--test', 'local_first', '--', '--test-threads=1'])
    if any(p.startswith('crates/engine/src/harness_updates') for p in paths):
        add(['cargo', 'test', '--locked', '-p', 'zeron-engine', '--lib', 'harness_updates::tests', '--', '--test-threads=1'])
    for prefix, package in [('crates/rpc/', 'zeron-rpc'), ('crates/harness/', 'zeron-harness')]:
        if any(p.startswith(prefix) for p in paths):
            add(['cargo', 'test', '--locked', '-p', package, '--', '--test-threads=1'])
    if any(p.startswith('apps/zeron/') for p in paths):
        add(['cargo', 'test', '--locked', '-p', 'zeron', '--no-default-features', '--', '--test-threads=1'])
    for directory in ('ops/worker-b/', 'ops/worker-a/'):
        if any(p.startswith(directory) for p in paths):
            add(['python3', '-m', 'unittest', 'discover', '-s', directory.rstrip('/'), '-p', 'test_*.py'])
    return plans


def prepare_worktree(root, candidate):
    """Stable path preserves build fingerprints; dirty review worktrees fail closed."""
    def git(*args, cwd=root):
        return subprocess.check_output(['git', *args], cwd=cwd, text=True, timeout=40).strip()
    head = candidate['head']
    subprocess.run(['git', 'fetch', 'origin', head, candidate['base']], cwd=root, check=True,
                   capture_output=True, text=True, timeout=40)
    work = root / '.worktrees' / 'nightly-review'
    if work.exists():
        if git('status', '--porcelain', cwd=work):
            raise RuntimeError('Review worktree has unpreserved edits')
        git('checkout', '--detach', head, cwd=work)
    else:
        git('worktree', 'add', '--detach', str(work), head)
    if git('rev-parse', 'HEAD', cwd=work) != head:
        raise RuntimeError('Worktree revision mismatch')
    return work


def execute_checks(root, state, candidate, cutoff, execute):
    work = prepare_worktree(root, candidate)
    candidate['worktree'] = str(work)
    plan = check_plan(candidate['paths'])
    env = os.environ.copy()
    home = Path('/home/jetson/.hermes/profiles/zeron')
    env.update(CARGO_HOME=str(home / 'cache/cargo'),
               RUSTUP_HOME=str(home / 'cache/rustup'),
               CARGO_TARGET_DIR=str(home / 'cache/zeron-target'), CARGO_BUILD_JOBS='2')
    env['PATH'] = str(home / 'cache/cargo/bin') + ':' + env.get('PATH', '')
    for key in ('ZERON_UPDATE_CHECKS', 'ZERON_AUTO_UPDATE', 'ZERON_RELEASE_BASE_URL'):
        env.pop(key, None)
    checks = []
    for index, argv in enumerate(plan):
        log = state / f"pr-{candidate['number']}-{candidate['head']}-check-{index}.log"
        if cutoff - time.monotonic() <= 10:
            checks.append({'argv': argv, 'status': 'not_run', 'returncode': None})
            continue
        started = time.monotonic()
        result = execute(argv, cutoff, log, cwd=work, env=env)
        raw = log.read_bytes() if log.exists() else b''
        checks.append({'argv': argv, 'returncode': result,
                       'status': 'passed' if result == 0 else 'timeout' if result == 124 else 'failed',
                       'seconds': round(time.monotonic() - started, 2),
                       'log': str(log), 'sha256': hashlib.sha256(raw).hexdigest(),
                       'tail': raw.decode(errors='replace')[-6000:]})
    diff_base = subprocess.check_output(['git', 'merge-base', candidate['base'], candidate['head']],
                                        cwd=work, text=True, timeout=15).strip()
    candidate['diff_base'] = diff_base  # GitHub PR diffs use merge-base, not inverse main changes.
    diff = subprocess.check_output(['git', 'diff', diff_base, candidate['head'], '--',
                                    *candidate['code_paths']], cwd=work, timeout=30)
    path = state / f"pr-{candidate['number']}-{candidate['head']}.diff"
    path.write_bytes(diff)
    os.chmod(path, 0o600)
    candidate['diff_path'] = str(path)
    candidate['requires_rendered_ui'] = any(p.startswith('crates/ui/') for p in candidate['paths'])
    return checks


def assess(result, record):
    """A model's COMPLETE string cannot replace pinned source and executed checks."""
    text = str(result.get('final_response') or '')
    packet: dict = {'status': 'partial', 'verdict': 'INCOMPLETE', 'report': text,
              'reason': 'Missing or invalid structured review', 'handoff_status': 'pending'}
    try:
        review = json.loads(text)
        if not isinstance(review, dict):
            raise ValueError('Review must be an object')
        candidate = record['candidate']
        valid = (
            record.get('audit_contract') == CONTRACT
            and type(record.get('requests')) is int and record['requests'] > 0
            and result.get('completed') is True and not result.get('failed')
            and review.get('head') == candidate['head'] == record['source']
            and review.get('verdict') in ('APPROVE', 'CHANGES_REQUESTED', 'INCOMPLETE')
            and isinstance(review.get('findings'), list)
            and isinstance(review.get('limitations'), list)
            and isinstance(review.get('summary'), str) and bool(review['summary'].strip())
            and isinstance(review.get('inspected_files'), list)
        )
        if not valid:
            raise ValueError('Invalid independent review evidence')
        covered = bool(candidate['code_paths']) and set(candidate['code_paths']).issubset(review['inspected_files'])
        checks = record.get('checks', [])
        expected = check_plan(candidate['paths'])
        executed = bool(expected) and [c.get('argv') for c in checks] == expected
        for check in checks:
            code = check.get('returncode')
            if (check.get('status') not in ('passed', 'failed') or not isinstance(code, int)
                    or isinstance(code, bool) or code == 124
                    or (check['status'] == 'passed') != (code == 0)):
                executed = False
                continue
            log = Path(check.get('log', ''))
            raw = log.read_bytes() if log.is_file() else b''
            if not raw or hashlib.sha256(raw).hexdigest() != check.get('sha256'):
                executed = False
            text_log = raw.decode(errors='replace')
            rust = re.findall(r'test result: (?:ok|FAILED)\. (\d+) passed; (\d+) failed', text_log)
            count = sum(int(a) + int(b) for a, b in rust)
            count += sum(int(n) for n in re.findall(r'Ran (\d+) tests?', text_log))
            if count == 0:
                executed = False
        passed = executed and all(c['status'] == 'passed' for c in checks)
        verdict = review['verdict']
        if verdict == 'APPROVE' and (not covered or not passed or review['findings']
                                     or review['limitations'] or candidate.get('requires_rendered_ui')):
            verdict = 'INCOMPLETE'
        if verdict == 'CHANGES_REQUESTED' and not review['findings']:
            verdict = 'INCOMPLETE'
        complete = covered and executed and verdict != 'INCOMPLETE'
        packet.update(review=review, verdict=verdict, status='complete' if complete else 'partial',
                      reason='Pinned diff inspected and required checks executed' if complete
                      else 'Missing inspection, checks, acceptance evidence or resolved verdict')
    except (OSError, ValueError, KeyError, TypeError, AssertionError):
        pass
    return packet

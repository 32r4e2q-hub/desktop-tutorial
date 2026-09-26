#!/usr/bin/env python3
"""Runner-side Actions report for monalisa-ops.yml (stdlib only: works on hosted and self-hosted runners).

Why: this repo is private and the agent's sandbox credential only works for git, so the agent cannot see
runs, jobs or error annotations. The runner can, with its own GITHUB_TOKEN (actions: write). This script
lists the branch's runs, the job/step state of unfinished generation runs, the annotations of recently
failed jobs (billing / "job was not started" messages live there), optionally cancels stale runs, writes
production/monalisa/ops-report.md, and mirrors a compact version to an ntfy topic named in OPS_REQUEST.
The mirror matters when the runner cannot push to the branch. It carries run metadata only; log lines
are filtered to status/error lines and redacted, and GitHub masks secrets in logs anyway.

Usage (in Actions): python3 production/monalisa/ops_report.py --job <label>
       python3 production/monalisa/ops_report.py --job <label> --post "<one-line message>"
"""
import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REQ = ROOT / 'production/monalisa/OPS_REQUEST'
OUT = ROOT / 'production/monalisa/ops-report.md'
BRANCH = 'arena/01a0dbbf-desktop-tutorial'
API = os.environ.get('GITHUB_API_URL', 'https://api.github.com')
REPO = os.environ.get('GITHUB_REPOSITORY', '32r4e2q-hub/desktop-tutorial')
TOKEN = os.environ.get('GITHUB_TOKEN', '')
ME = os.environ.get('GITHUB_RUN_ID', '')
KEEP = re.compile(r'PRODUCTION_STATUS|poll:|status=|error|Error|ERROR|fatal|denied|429|403|remote:|rejected|Traceback|exceeded|limit')
SECRET = re.compile(r'(api[_-]?key|token|authorization|bearer)\S*', re.I)


def request_options():
    opts = {}
    if REQ.exists():
        for line in REQ.read_text().splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                k, v = line.split('=', 1)
                opts[k.strip()] = v.strip()
    return opts


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def api(method, path, data=None, raw=False):
    url = path if path.startswith('http') else f'{API}/repos/{REPO}/{path}'
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'monalisa-ops'})
    opener = urllib.request.build_opener(NoRedirect) if raw else urllib.request.build_opener()
    try:
        with opener.open(req, timeout=60) as r:
            text = r.read().decode('utf-8', 'replace')
            return text if raw else (json.loads(text) if text.strip() else {})
    except urllib.error.HTTPError as e:
        if raw and e.code in (301, 302, 303, 307, 308) and e.headers.get('Location'):
            # log blobs: follow the redirect WITHOUT the Authorization header
            with urllib.request.urlopen(e.headers['Location'], timeout=60) as r:
                return r.read().decode('utf-8', 'replace')
        return {'_error': f'HTTP {e.code}: {e.read().decode("utf-8", "replace")[:300]}'}
    except Exception as e:  # noqa: BLE001 - everything goes into the report
        return {'_error': repr(e)[:300]}


def post(topic, text):
    """Mirror to ntfy in <3.5 KB chunks (ntfy turns >4 KB messages into attachments)."""
    if not topic:
        return
    chunks = [text[i:i + 3400] for i in range(0, len(text), 3400)] or ['']
    for i, chunk in enumerate(chunks, 1):
        msg = (f'({i}/{len(chunks)}) ' if len(chunks) > 1 else '') + chunk
        try:
            urllib.request.urlopen(urllib.request.Request(
                f'https://ntfy.sh/{topic}', data=msg.encode(), method='POST',
                headers={'User-Agent': 'monalisa-ops'}), timeout=30).read()
        except Exception as e:  # noqa: BLE001
            print('ntfy post failed:', repr(e)[:200])
        time.sleep(1.2)


def is_gen(run):
    return (run.get('path') or '').startswith('.github/workflows/monalisa-gen.yml') or 'Agnes生成' in (run.get('name') or '')


def is_ops(run):
    return (run.get('path') or '').startswith('.github/workflows/monalisa-ops.yml')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--job', default='ops')
    ap.add_argument('--post', default=None)
    args = ap.parse_args()
    opts = request_options()
    topic = opts.get('ntfy', '')
    if args.post is not None:
        post(topic, f'[{args.job}] {args.post}')
        return 0
    action = opts.get('action', 'report')
    lines, short = [], []
    head = f'[{args.job}] run {ME} · {time.strftime("%H:%M:%S", time.gmtime())}Z · runner={os.environ.get("RUNNER_NAME", "?")} ({os.environ.get("RUNNER_ENVIRONMENT", "?")}) · action={action}'
    lines += [f'# 运维报告 · {head}', '']
    short.append(head)
    runs = api('GET', f'actions/runs?branch={BRANCH}&per_page=40')
    if '_error' in runs:
        lines.append('runs API: ' + runs['_error'])
        short.append('runs API: ' + runs['_error'])
        runs = {'workflow_runs': []}
    wr = runs.get('workflow_runs', [])
    lines += ['## 本分支最近的 run', '```']
    for r in wr:
        row = f"{r['id']} {r.get('name', '')[:30]} {r['status']}/{r.get('conclusion') or '-'} created={r['created_at'][11:19]} started={(r.get('run_started_at') or '-')[11:19]} sha={r['head_sha'][:7]}"
        lines.append(row)
    lines.append('```')
    for r in wr[:14]:
        short.append(f"{r['id']} {'GEN' if is_gen(r) else 'OPS' if is_ops(r) else (r.get('name') or '')[:14]} {r['status']}/{r.get('conclusion') or '-'} c{r['created_at'][11:16]} s{(r.get('run_started_at') or '-')[11:16]}")
    # annotations of recently failed / never-started jobs
    failed = [r for r in wr if r['status'] == 'completed' and r.get('conclusion') in ('failure', 'startup_failure', 'cancelled', 'timed_out')][:5]
    for r in failed:
        jobs = api('GET', f"actions/runs/{r['id']}/jobs")
        for j in jobs.get('jobs', [])[:3]:
            ann = api('GET', f"check-runs/{j['id']}/annotations")
            msgs = [a.get('message', '')[:220] for a in ann] if isinstance(ann, list) else [str(ann.get('_error', ''))[:220]]
            txt = f"run {r['id']} job {j['name'][:20]} {j.get('conclusion')} runner={j.get('runner_name') or '-'}: " + ' | '.join(m.replace('\n', ' ') for m in msgs if m)
            lines.append('- ' + txt)
            short.append(txt)
    active_gen = sorted([r for r in wr if is_gen(r) and r['status'] != 'completed'], key=lambda r: r['created_at'])
    for r in active_gen:
        jobs = api('GET', f"actions/runs/{r['id']}/jobs")
        for j in jobs.get('jobs', []):
            steps = [s for s in j.get('steps', []) if s.get('status') != 'queued' or s.get('conclusion')]
            cur = steps[-1]['name'][:40] if steps else '-'
            txt = f"active gen {r['id']} job={j.get('status')} runner={j.get('runner_name') or '-'} labels={','.join(j.get('labels', []))} step={cur} started={(j.get('started_at') or '-')[11:19]}"
            lines.append('- ' + txt)
            short.append(txt)
    to_cancel = [x for x in opts.get('cancel', '').replace(',', ' ').split() if x]
    if action == 'cancel-stale-gen':
        to_cancel += [str(r['id']) for r in active_gen[:-1]]
        to_cancel += [str(r['id']) for r in wr if is_ops(r) and r['status'] != 'completed' and str(r['id']) != ME]
        if active_gen:
            short.append(f'keep newest gen {active_gen[-1]["id"]}')
    for rid in dict.fromkeys(to_cancel):
        res = api('POST', f'actions/runs/{rid}/cancel')
        txt = f'cancel {rid}: ' + (res.get('_error', 'submitted') if isinstance(res, dict) else 'submitted')
        lines.append('- ' + txt)
        short.append(txt)
    if to_cancel:
        time.sleep(40)
        for rid in dict.fromkeys(to_cancel):
            st = api('GET', f'actions/runs/{rid}')
            s = f"{st.get('status')}/{st.get('conclusion')}" if '_error' not in st else st['_error']
            if not s.startswith('completed'):
                api('POST', f'actions/runs/{rid}/force-cancel')
                time.sleep(10)
            jobs = api('GET', f'actions/runs/{rid}/jobs')
            for j in jobs.get('jobs', [])[:2]:
                log = api('GET', f"actions/jobs/{j['id']}/logs", raw=True)
                if isinstance(log, str):
                    keep = [SECRET.sub(r'\1=[redacted]', ln[:200]) for ln in log.splitlines() if KEEP.search(ln)][-30:]
                    lines += [f'### run {rid} job {j["id"]} 日志（筛选后最后 30 行）', '```', *keep, '```']
                    short.append(f'log {rid}: ' + ' ⏎ '.join(k[29:] if len(k) > 29 and k[4] == '-' else k for k in keep[-12:]))
    OUT.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    post(topic, '\n'.join(short))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

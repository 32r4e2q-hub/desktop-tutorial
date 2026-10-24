"""Bounded workflow relay adapted from Mary Celeste's capacity/exit-42 pattern.
Never uses a marker push alone: GITHUB_TOKEN pushes do not trigger push workflows.
No relay on moderation, auth, schema, unknown POST outcome, or manual identity review.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path


def decide(project, stage, code, max_runs=3):
    project=Path(project)
    request=project/'REQUEST'
    chain=hashlib.sha256(request.read_bytes()+stage.encode()).hexdigest()
    file=project/'relay-state.json'
    old=json.loads(file.read_text()) if file.exists() else {}
    if old.get('chain')!=chain:old={}
    status=json.loads((project/'run-status.json').read_text()) if (project/'run-status.json').exists() else {}
    source=project/('identity-probe/receipts.json' if stage=='identity' else 'receipts.json')
    receipts=json.loads(source.read_text()) if source.exists() else {}
    completed=sum(s.get('status')=='downloaded' for s in receipts.get('shots',{}).values())
    run_key=os.environ.get('GITHUB_RUN_ID','local')+':'+os.environ.get('GITHUB_RUN_ATTEMPT','1')
    if old.get('last_run_key')==run_key:return old
    count=old.get('finished_runs',0)+1
    stale=0 if completed>old.get('completed',0) else old.get('stale_runs',0)+1
    waiting=(code==42 and status.get('automatic_retry_allowed') is True and
             status.get('status') in ('awaiting_provider','provider_transient'))
    resume=waiting and count<max_runs and stale<max_runs
    reason=('same-task/capacity continuation' if resume else
            'bounded relay budget exhausted; paused, not completed' if waiting else
            'stage completed or non-retryable condition; no automatic relay')
    result={'chain':chain,'stage':stage,'last_run_key':run_key,'finished_runs':count,
            'max_runs':max_runs,'stale_runs':stale,'completed':completed,
            'resume':resume,'reason':reason,'observed_status':status.get('status'),
            'dispatch_status':'planned_not_yet_dispatched' if resume else 'not_requested'}
    file.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',required=True)
    parser.add_argument('--code',required=True,type=int)
    args=parser.parse_args()
    result=decide(Path(__file__).resolve().parent,args.stage,args.code)
    output=os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output,'a') as f:f.write('resume='+str(result['resume']).lower()+'\n')
    print(json.dumps(result,ensure_ascii=False))

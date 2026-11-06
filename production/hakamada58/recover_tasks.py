#!/usr/bin/env python3
"""Non-billing recovery probe for Agnes tasks whose receipts were not published."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, sys, urllib.error, urllib.parse, urllib.request
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'production'))


def as_time(value):
    if value is None:return None
    if isinstance(value,(int,float)):
        n=float(value)
        if n>10_000_000_000:n/=1000
        try:return dt.datetime.fromtimestamp(n,dt.timezone.utc)
        except (ValueError,OSError,OverflowError):return None
    try:
        text=str(value).replace('Z','+00:00')
        result=dt.datetime.fromisoformat(text)
        return result.replace(tzinfo=dt.timezone.utc) if result.tzinfo is None else result.astimezone(dt.timezone.utc)
    except (ValueError,TypeError):return None


def parse_window(text):
    result=as_time(text)
    if result is None:raise ValueError('timestamp must be ISO-8601 or epoch seconds')
    return result


def get_json(base,key,path):
    req=urllib.request.Request(base+path,headers={'Authorization':'Bearer '+key,'Accept':'application/json','User-Agent':'hakamada58-task-recovery/1.0'})
    try:
        with urllib.request.urlopen(req,timeout=60) as response:return response.status,response.read()
    except urllib.error.HTTPError as exc:return exc.code,exc.read()


def find_records(body):
    if isinstance(body,list):return [x for x in body if isinstance(x,dict)]
    if not isinstance(body,dict):return []
    for key in ('data','videos','tasks','items','results','records','list','rows'): 
        value=body.get(key)
        if isinstance(value,list):return [x for x in value if isinstance(x,dict)]
        if isinstance(value,dict):
            nested=find_records(value)
            if nested:return nested
    if any(k in body for k in ('id','task_id','video_id')):return [body]
    return []


def nested_value(record,*keys):
    for key in keys:
        value=record.get(key)
        if value is not None:return value
    for parent in ('request','input','metadata','data'):
        value=record.get(parent)
        if isinstance(value,dict):
            for key in keys:
                if value.get(key) is not None:return value[key]
    return None


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--created-after',required=True);ap.add_argument('--created-before',required=True)
    ap.add_argument('--out',default=str(HERE/'recovery_inventory.json'))
    args=ap.parse_args()
    start,end=parse_window(args.created_after),parse_window(args.created_before)
    if end<=start:raise ValueError('created-before must be after created-after')
    key=os.getenv('AGNES_API_KEY','').strip()
    if not key:raise RuntimeError('AGNES_API_KEY is unavailable')
    base=(os.getenv('AGNES_BASE_URL','').strip() or 'https://apihub.agnes-ai.com').rstrip('/')
    routes=['/v1/videos?limit=100&page=1','/v1/videos?limit=100','/v1/videos']
    attempts=[];records=[];used_route=None
    for route in routes:
        try:code,raw=get_json(base,key,route)
        except Exception as exc:
            attempts.append({'route':route,'error':type(exc).__name__});continue
        try:body=json.loads(raw.decode('utf-8','replace')) if raw else None
        except ValueError:body=None
        attempts.append({'route':route,'http_status':code,'response_type':type(body).__name__})
        if 200<=code<300:
            records=find_records(body);used_route=route
            if records:break
            # A successful empty page is meaningful; do not make more requests.
            if isinstance(body,(dict,list)):break
    project=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
    targets={s['id']:s for s in project['shots'] if s['id'] in {'S11','S12','S17'}}
    prompts={hashlib.sha256(s['prompt'].encode()).hexdigest():sid for sid,s in targets.items()}
    selected=[]
    for row in records:
        created=as_time(nested_value(row,'created_at','createdAt','created','submitted_at'))
        model=nested_value(row,'model','model_name','modelName')
        if model and 'agnes-video-2.5-flash' not in str(model):continue
        if created and not (start<=created<=end):continue
        prompt=nested_value(row,'prompt')
        prompt_hash=hashlib.sha256(str(prompt).encode()).hexdigest() if isinstance(prompt,str) else None
        sid=prompts.get(prompt_hash)
        if created is None and sid is None:continue
        video_id=nested_value(row,'video_id','videoId','id','task_id','taskId')
        if not video_id:continue
        url=nested_value(row,'video_url','url')
        status=nested_value(row,'status','state')
        selected.append({'shot_id':sid,'video_id':str(video_id),'task_id':str(nested_value(row,'task_id','taskId','id') or video_id),
                         'status':str(status or 'unknown'),'created_at':created.isoformat().replace('+00:00','Z') if created else None,
                         'model':str(model or ''),'video_url':url if isinstance(url,str) and url.startswith(('https://','http://')) else None,
                         'prompt_sha256':prompt_hash})
    selected.sort(key=lambda x:(x.get('created_at') or '',x['video_id']))
    out={'project':'袴田事件：58年','recovery_window':{'created_after':start.isoformat().replace('+00:00','Z'),'created_before':end.isoformat().replace('+00:00','Z')},
         'query_status':'found' if selected else ('empty' if used_route else 'unsupported_or_unavailable'),
         'endpoint':used_route,'attempts':attempts,'tasks':selected,
         'note':'Read-only API inventory; this probe never creates, cancels, or modifies Agnes tasks.'}
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'query_status':out['query_status'],'tasks_found':len(selected),'matched_shots':[x['shot_id'] for x in selected if x['shot_id']],'out':str(path)},ensure_ascii=False))
    return 0 if out['query_status']=='found' else 2

if __name__=='__main__':raise SystemExit(main())

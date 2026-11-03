"""Read-only connectivity check on the same cloud runner as Setagaya. Never logs credentials."""
import json
import os
import urllib.request
import urllib.error
from pathlib import Path

out = {'api_key_present': bool(os.environ.get('AGNES_API_KEY')), 'requests': [], 'generation_submitted': False}
for url in ['https://agnes-ai.com/en/docs/agnes-video-25', 'https://apihub.agnes-ai.com/v1/models']:
    headers = {'User-Agent': 'crippen-production/1.0'}
    if url.endswith('/v1/models') and os.environ.get('AGNES_API_KEY'):
        headers['Authorization'] = 'Bearer ' + os.environ['AGNES_API_KEY']
    row = {'url': url}
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
            raw = r.read().decode('utf-8', 'replace')
            row['status'] = r.status
            if url.endswith('/v1/models'):
                data = json.loads(raw)
                row['model_ids'] = [x.get('id') for x in data.get('data', []) if isinstance(x, dict)]
            else:
                import re
                text = re.sub('<[^>]+>', ' ', raw)
                row['schema_excerpts'] = [m.group(0) for m in re.finditer(r'.{0,100}(?:first_frame|images|reference|keyframe).{0,180}', text)][:35]
    except urllib.error.HTTPError as e:
        row['status'] = e.code
    except Exception as e:
        row['error_type'] = type(e).__name__
    out['requests'].append(row)
# Read-only diagnostics for existing tasks. Never creates or re-submits footage.
results=Path('production/crippen1910/results.json')
if results.exists():
    import urllib.parse,time
    out['task_checks']=[]
    for sid,row in json.loads(results.read_text()).get('shots',{}).items():
        if row.get('status')=='completed' or not row.get('video_id'):continue
        query=urllib.parse.urlencode({'video_id':row['video_id'],'model_name':'agnes-video-2.5-flash'})
        url='https://apihub.agnes-ai.com/agnesapi?'+query
        item={'shot':sid,'task_id':row.get('task_id'),'checked_at_epoch':int(time.time())}
        try:
            req=urllib.request.Request(url,headers={'Authorization':'Bearer '+os.environ['AGNES_API_KEY']})
            with urllib.request.urlopen(req,timeout=60) as response:data=json.load(response)
            item['response']={key:data.get(key) for key in ['id','video_id','status','progress','created_at','started_at','completed_at','error','queue_position','estimated_wait_time'] if key in data}
        except Exception as exc:item['error_type']=type(exc).__name__
        out['task_checks'].append(item)
Path('production/crippen1910/service-probe.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(out, ensure_ascii=False, indent=2))

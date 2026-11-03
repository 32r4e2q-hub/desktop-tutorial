"""One-shot read-only provider queries. Never creates tasks or publishes download URLs."""
import concurrent.futures,json,os,sys,datetime
from pathlib import Path
from urllib.parse import urlencode
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
import agnes_video as api
key=os.environ['AGNES_API_KEY']
shots=json.loads((HERE/'results.json').read_text())['shots']
def check(item):
    sid,row=item
    if not row.get('video_id'):return sid,{'status':'not_submitted'}
    try:
        url='https://apihub.agnes-ai.com/agnesapi?'+urlencode({'video_id':row['video_id'],'model_name':'agnes-video-2.5-flash'})
        code,body,_=api.http_json('GET',url,key,timeout=40)
        body=body if isinstance(body,dict) else {}
        result={'http_status':code,'status':body.get('status','unknown'),'progress':body.get('progress'),'has_video_url':bool(api.find_video_url(body)),'locally_completed':row.get('status')=='completed'}
        if result['status'] in api.FAILED_STATES:
            result['error']=str(body.get('message') or body.get('error') or '')[:300].replace(key,'[redacted]')
        return sid,result
    except Exception as exc:return sid,{'error_type':type(exc).__name__,'status':'query_error'}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=dict(pool.map(check,shots.items()))
out={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'read_only':True,'generation_submitted':False,'shots':rows}
(HERE/'task-status-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(out,ensure_ascii=False,indent=2))

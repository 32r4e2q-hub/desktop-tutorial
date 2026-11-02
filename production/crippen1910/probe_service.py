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
Path('production/crippen1910/service-probe.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(out, ensure_ascii=False, indent=2))

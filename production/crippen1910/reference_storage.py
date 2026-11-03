"""Hydrate SHA-approved reference PNGs from their immutable ancestor commit.
Large generated images are a local cache, not duplicated into the final delivery patch.
The original Git objects remain reachable in this branch's history. No branch switching.
"""
from pathlib import Path
import hashlib,json,re,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def hydrate():
    approval=json.loads((HERE/'reference/approvals.json').read_text());revision=approval['revision']
    if not re.fullmatch('[0-9a-f]{40}',revision):raise RuntimeError('Immutable reference revision required')
    missing=[]
    for key,row in approval['assets'].items():
        if not re.fullmatch('[A-Za-z0-9_]+',key):raise RuntimeError('Unsafe reference ID')
        path=HERE/'reference'/f'{key}.png'
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:missing.append((key,path,row['sha256']))
    if not missing:return
    exists=subprocess.run(['git','cat-file','-e',revision+'^{commit}'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    if not exists:subprocess.run(['git','fetch','--depth=1','origin',revision],cwd=ROOT,check=True)
    for key,path,expected in missing:
        temporary=path.with_suffix('.download')
        with temporary.open('wb') as stream:
            subprocess.run(['git','show',f'{revision}:production/crippen1910/reference/{key}.png'],cwd=ROOT,stdout=stream,check=True)
        if hashlib.sha256(temporary.read_bytes()).hexdigest()!=expected:
            temporary.unlink();raise RuntimeError('Archived reference SHA mismatch: '+key)
        temporary.replace(path);print('RESTORED_APPROVED_REFERENCE',key,flush=True)
if __name__=='__main__':hydrate()

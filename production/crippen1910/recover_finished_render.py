"""Restore the fully encoded film from the known font-only failure, never regenerate clips.
Artifacts are downloaded by the authenticated GitHub action, not an untrusted movie URL.
Every source, narration clip, and shot decision is compared to this checkout before reuse.
"""
import hashlib,json,shutil
from generate import request_hash
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def restore(root):
    old=root/'production/crippen1910';now=json.loads((HERE/'story.json').read_text())
    keys=('id','start','duration','prompt','references','narration')
    original_rows=json.loads((old/'results.json').read_text())['shots']
    original_voice={x['id']:x for x in json.loads((old/'audio/manifest.json').read_text())['clips']}
    for shot in now['shots']:
        row=original_voice[shot['id']]
        assert (row['text'],row['target_start'],row['target_duration'])==(shot['narration'],shot['start'],shot['duration']), 'Rendered narration or timing changed'
        assert request_hash(now,shot)==original_rows[shot['id']]['request_hash'], 'Rendered visual request changed'
    log=(old/'autopilot.log').read_text();assert 'make_cover(args.sources, cover, story, args.work)' in log and 'Noto CJK fonts are required' in log
    rows=json.loads((HERE/'results.json').read_text())['shots'];src=ROOT/'work/crippen1910/sources';exports=ROOT/'work/crippen1910/clips';src.mkdir(parents=True,exist_ok=True);exports.mkdir(parents=True,exist_ok=True)
    source_hashes={};voice_hashes={}
    for shot in now['shots']:
        sid=shot['id'];clip=root/'work/crippen1910/clips'/f'{sid}.mp4';audio=HERE/'audio'/f'{sid}.mp3'
        assert sha(clip)==rows[sid]['sha256'];assert sha(audio)==sha(old/'audio'/audio.name), 'Narration changed'
        source_hashes[sid]=sha(clip);voice_hashes[sid]=sha(audio)
        shutil.copy2(clip,src/clip.name);shutil.copy2(clip,exports/clip.name)
    original=root/'work/crippen1910/clips'/now['film_name'];film=exports/original.name;shutil.copy2(original,film)
    receipt={'recovered_from_run':41649456908,'artifact_name':'crippen1910-autonomous-production-5','reason':'All encoding completed; only Pillow cover font discovery failed. Reuse exact encoded bytes, rebuild covers/reports and run full actual-film QC.','film_sha256':sha(film),'source_sha256':source_hashes,'voice_sha256':voice_hashes,'shot_decisions_sha256':hashlib.sha256(json.dumps([[s[k] for k in keys] for s in now['shots']],ensure_ascii=False,sort_keys=True).encode()).hexdigest()}
    path=HERE/'qa/finished-film-recovery.json';path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n');print('RECOVERED_ENCODED_FILM',film.stat().st_size,receipt['film_sha256'],flush=True)
if __name__=='__main__':restore(ROOT/'work/crippen1910/recovered-artifact')

#!/usr/bin/env python3
"""Independent medium-model check of chapters with ambiguous small-model evidence.
No script, vocabulary hint or initial prompt is supplied to the recognizer.
"""
import argparse, hashlib, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--film',type=Path,required=True);a=ap.parse_args()
    from faster_whisper import WhisperModel
    from verbatim_check import load_chapters,write_wav,decode_audio,compare
    out=HERE/'revision-2/review';out.mkdir(parents=True,exist_ok=True)
    sha=hashlib.sha256(a.film.read_bytes()).hexdigest()
    assert sha==json.loads((HERE/'revision-2/technical-report.json').read_text())['sha256']
    chapters=[c for c in load_chapters(HERE,None) if c['id'] in ('N01','N03','N06')]
    samples=decode_audio(a.film,out)
    model=WhisperModel('medium',device='cpu',compute_type='int8',cpu_threads=4,download_root='work/secondary-model')
    film={};dry={}
    for ch in chapters:
        cid=ch['id'];start=max(0,ch['start']-.25);end=ch['end']+.25
        path=write_wav(out/(cid+'-medium.wav'),samples[int(start*48000):int(end*48000)])
        segs,_=model.transcribe(str(path),language='zh',beam_size=5,vad_filter=False,condition_on_previous_text=False)
        film[cid]=''.join(s.text for s in segs);path.unlink()
        segs,_=model.transcribe(str(HERE/'audio'/(cid+'.mp3')),language='zh',beam_size=5,vad_filter=False,condition_on_previous_text=False)
        dry[cid]=''.join(s.text for s in segs)
        print('SECONDARY_ASR',cid,'film:',film[cid],'dry:',dry[cid],flush=True)
        report={'film_sha256':sha,'method':'Independent faster-whisper medium, no initial_prompt, no script supplied to recognizer; N01/N03/N06 selected because small-model names/wording were ambiguous. ASR disagreement is not itself proof of a spoken error.','film_pass':compare(chapters,film,.15),'narration_control':compare(chapters,dry,.15)}
        (out/'medium-asr-control.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()

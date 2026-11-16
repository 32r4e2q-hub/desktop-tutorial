#!/usr/bin/env python3
"""Propose pause-based shot cuts from continuous TTS; NEVER auto-approve alignment.

The previous film used three consecutive shot texts per TTS call. We retain that
prosody, but proportional timing is only a prior for finding real silent pauses.
Candidates stay in ignored work/ until transcript/listening verification. Missing
or moderation-blocked groups never become fabricated silence or another voice.
"""
from __future__ import annotations
import hashlib
import itertools
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT / 'work/shibuya2006/audio_candidates'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def measure(path):
    return float(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=nw=1:nk=1', str(path)], text=True).strip())


def pauses(path, duration):
    result = subprocess.run([
        'ffmpeg', '-hide_banner', '-i', str(path), '-af',
        'silencedetect=noise=-35dB:d=0.18', '-f', 'null', '-'],
        capture_output=True, text=True, check=True)
    rows = []
    start = None
    for line in result.stderr.splitlines():
        m = re.search(r'silence_start:\s*([\d.]+)', line)
        if m: start = float(m[1])
        m = re.search(r'silence_end:\s*([\d.]+)', line)
        if m and start is not None:
            end = float(m[1])
            if start > 0.15 and end < duration - 0.15:
                rows.append(dict(start=start, end=end, middle=(start+end)/2))
            start = None
    return rows


def choose_boundaries(texts, duration, candidates):
    """Two ordered actual pauses, weakly guided by spoken-character proportions."""
    weights = [max(1, len(re.sub(r'[^\u4e00-\u9fff0-9A-Za-z]', '', t))) for t in texts]
    priors = [duration * sum(weights[:i]) / sum(weights) for i in [1, 2]]
    pairs = []
    for first, second in itertools.combinations(candidates, 2):
        cuts = [0., first['middle'], second['middle'], duration]
        if min(b-a for a,b in zip(cuts,cuts[1:])) < 1.5:
            continue
        deviation = sum((p-c['middle'])**2 for p,c in zip(priors,[first,second]))
        # Prefer a longer natural pause, without overwhelming the text prior.
        score = deviation - .3 * sum(min(.9,c['end']-c['start']) for c in [first,second])
        pairs.append((score,cuts))
    if not pairs: raise ValueError('No two safe pause boundaries; manual/ASR alignment required')
    return min(pairs, key=lambda x:x[0])[1], priors


def main():
    story = json.loads((HERE/'story.json').read_text())
    source_manifest = json.loads((HERE/'audio/groups/manifest.json').read_text())
    WORK.mkdir(parents=True, exist_ok=True)
    report = dict(status='candidate_only_not_alignment_pass', voice=story['narration_spec']['voice_id'],
                  policy='No final audio/manifest.json until missing groups and transcript boundaries are verified',
                  groups=[], clips=[], missing=[])
    for group in source_manifest['groups']:
        gid = group['id']
        if group['status'] != 'generated':
            report['missing'].append(dict(id=gid,reason=group['status'],shots=group['shots']))
            continue
        path = HERE/'audio/groups'/f'{gid}.mp3'
        if not path.is_file() or digest(path) != group['sha256']:
            raise RuntimeError(f'{gid}: missing/changed original TTS')
        shots = [s for s in story['shots'] if s['id'] in group['shots']]
        texts = [s['narration'] for s in shots]
        if ''.join(texts) != group['text']:
            raise RuntimeError(f'{gid}: text changed after TTS; regenerate rather than relabel')
        duration = measure(path)
        candidates = pauses(path,duration)
        try:
            cuts,priors = choose_boundaries(texts,duration,candidates)
        except ValueError as exc:
            report['missing'].append(dict(id=gid,reason=str(exc),shots=group['shots']))
            continue
        report['groups'].append(dict(id=gid,duration=duration,cuts=cuts,proportional_priors=priors,
                                     detected_silences=candidates,review='pending_listening_or_ASR'))
        for shot, start, end in zip(shots,cuts,cuts[1:]):
            dest = WORK/f"{shot['id']}.mp3"
            subprocess.run(['ffmpeg','-y','-v','error','-ss',str(start),'-t',str(end-start),'-i',str(path),
                            '-af','silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.06,'
                            'areverse,silenceremove=start_periods=1:start_threshold=-48dB:start_silence=0.06,areverse',
                            '-ar','48000','-ac','1','-c:a','libmp3lame','-q:a','2',str(dest)],check=True)
            seconds=measure(dest)
            report['clips'].append(dict(id=shot['id'],group=gid,cut_start=start,cut_end=end,
                seconds=seconds,target=shot['duration'],atempo_required=max(1.,seconds/shot['duration']),
                text=shot['narration'],sha256=digest(dest),file=str(dest.relative_to(ROOT)),
                alignment_review='pending; candidate boundary may split the wrong sentence'))
    (HERE/'qa/group-tts-split-candidates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(f"Candidate audio: {len(report['clips'])}/30; unavailable groups: {len(report['missing'])}; NOT alignment-approved")

if __name__=='__main__':main()

#!/usr/bin/env python3
"""Recover a first cut's clean image track; repair PTS-scheduled blackouts only.

This never generates/replaces footage, never approves the known rejected sources,
and never substitutes frozen/interpolated frames. The original uncaptioned track
is from the same immutable Actions artifact as the SHA-verified first cut.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import av
import numpy as np

from build_audio import measure, assert_audible
from media import probe
import render

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--track', type=Path, required=True)
    ap.add_argument('--film', type=Path, required=True)
    ap.add_argument('--expected-sha', required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--artifact-run', required=True)
    args = ap.parse_args()
    assert sha(args.film) == args.expected_sha, 'Input is not the exact diagnosed cut'
    delivery = HERE/'delivery'
    report = json.loads((delivery/'technical-report.json').read_text())
    assert report['sha256'] == args.expected_sha, 'A newer cut must never be rolled back'
    track_info = probe(args.track)
    assert (track_info['width'], track_info['height'], track_info['frames']) == (1920,1080,5400)
    assert abs(track_info['duration'] - 180) < .1
    edl = json.loads((delivery/'edit-decision-list.json').read_text())
    cues = json.loads((delivery/'caption-timing.json').read_text())
    narration = json.loads((delivery/'narration-timing.json').read_text())
    presentation = json.loads((HERE/'story.json').read_text())['presentation']
    windows = json.loads((delivery/'planned-blackouts.json').read_text())['windows']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subtitle = args.output.parent/'captions.ass'
    render.write_subtitles(subtitle,cues,edl,presentation)

    # Preserve evidence of input parameter transitions which can reset local n.
    data = json.loads(subprocess.check_output([
        'ffprobe','-v','error','-select_streams','v:0','-read_intervals','%+#260',
        '-show_frames','-show_entries','frame=pix_fmt,color_range,color_space,color_primaries,color_transfer',
        '-of','json',str(args.track)],text=True))
    transitions=[];previous=None
    for index, frame in enumerate(data['frames']):
        params={k:frame.get(k) for k in ('pix_fmt','color_range','color_space','color_primaries','color_transfer')}
        if params != previous:
            transitions.append({'frame':index,**params});previous=params

    vf=(render.NORMALISE_COLOUR+
        f",subtitles=filename='{subtitle.resolve().as_posix()}':fontsdir='{render.find_font().parent.as_posix()}'"+
        render.blackout_filters(windows))
    subprocess.run(['ffmpeg','-y','-v','error','-threads','2','-i',str(args.track),'-i',str(args.film),
        '-map','0:v:0','-map','1:a:0','-vf',vf,'-c:v','libx264','-preset','fast','-crf','21',
        '-maxrate','4000k','-bufsize','8000k','-pix_fmt','yuv420p',*render.COLOUR_FLAGS,
        '-r','30','-c:a','copy','-t','180','-movflags','+faststart',str(args.output)],check=True)
    info=probe(args.output)
    assert (info['width'],info['height'],info['frames'],info['audio_channels']) == (1920,1080,5400,2)
    assert abs(info['duration']-180)<.1
    wanted={i for w in windows for i in range(w['start_frame'],w['end_frame'])}
    actual=set();decoded=0
    with av.open(str(args.output)) as container:
        for index,frame in enumerate(container.decode(video=0)):
            a=frame.reformat(width=96,height=54,format='rgb24').to_ndarray()
            if a.mean()<2 and a.std()<2:
                actual.add(index)
            decoded+=1
    assert decoded == 5400
    assert wanted <= actual, f'Missing planned black frames: {sorted(wanted-actual)}'
    end_start=edl[-1]['start_frame']
    allowed_fades=set(range(10)) | set(range(5370,5400)) | set(range(end_start-6,end_start+7))
    unexpected=actual-wanted-allowed_fades
    assert not unexpected, f'Unplanned blackout frames remain: {sorted(unexpected)}'
    audio=measure(args.output,chapters=narration)
    assert_audible(audio)
    audio['measured_on']='delivered mp4 after first-cut blackout repair'
    # Independent review is still required: keep the known source failures open.
    output_sha=sha(args.output)
    report.update(info,sha256=output_sha,decoded_ok=True,status='audio_verified_cut',visual_review='pending',
                  first_cut_technical_repair=True,
                  known_source_rejections='qa/source-review-round1.json',
                  temporal_reverse_present=any(e.get('pingpong') for e in edl))
    repair={'source_cut_sha256':args.expected_sha,'film_sha256':output_sha,
            'image_track_sha256':sha(args.track),'artifact_run_id':args.artifact_run,
            'image_track_initial_parameter_transitions':transitions,
            'blackout_clock':'absolute PTS round(t*30), independent of filter-local n resets',
            'planned_black_frames':len(wanted),'verified_planned_black_frames':len(wanted&actual),
            'unexpected_black_frames':sorted(unexpected),'decoded_frames':decoded,
            'audio':'original AAC stream copied; measured again on the actual repaired MP4',
            'status':'FIRST CUT ONLY: 12 source retakes and semantic/identity approval still outstanding'}
    (delivery/'technical-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (delivery/'final-audio-report.json').write_text(json.dumps(audio,ensure_ascii=False,indent=2)+'\n')
    (delivery/'first-cut-blackout-repair.json').write_text(json.dumps(repair,ensure_ascii=False,indent=2)+'\n')
    (delivery/'planned-blackouts.json').write_text(json.dumps({'film_sha256':output_sha,'fps':30,'windows':windows,
        'purpose':'five verified 0.3-second chapter transitions'},ensure_ascii=False,indent=2)+'\n')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(args.output),'-vf','fps=1/6,scale=320:180,tile=5x6',
                    '-frames:v','1','-q:v','3',str(delivery/'final-contact.jpg')],check=True)
    print('FIRST_CUT_BLACKOUT_REPAIR '+json.dumps(repair,ensure_ascii=False),flush=True)


if __name__ == '__main__':
    main()

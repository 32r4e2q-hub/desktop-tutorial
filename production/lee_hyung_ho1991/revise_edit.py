#!/usr/bin/env python3
"""Prepare revision v2 from actual spoken cue times, never guessed 4-second slots."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
# Each source occurs once; order follows the spoken events, not source generation order.
CUTS=[(0,'S03'),(4.2,'S04'),(7.6,'S05'),(9.6,'S01'),(11.5,'S07'),
      (15.2,'S10'),(19.2,'S06'),(23.6,'S08'),(29.971,'S09'),(33.2,'S15'),
      (35.2,'S33'),(39.0,'S13'),(41.1,'S11'),(43.4,'S12'),(49.8,'S17'),(54.0,'S14'),
      (59.018,'S16'),(61.7,'S20'),(65.2,'S18'),(68.8,'S19'),(71.0,'S21'),
      (75.7,'S22'),(79.5,'S23'),(85.751,'S24'),(90.0,'S25'),(93.6,'S26'),
      (96.8,'S30'),(103.3,'S28'),(106.7,'S27'),(109.0,'S29'),(112.537,'S31'),
      (114.7,'S32'),(116.8,'S35'),(119.2,'S34'),(124.0,'S37'),(130.2,'S36'),
      (132.9,'S41'),(138.898,'S38'),(145.3,'S39'),(148.7,'S40'),(155.0,'S42'),
      (161.3,'S43'),(164.2,'S44'),(170.5,'S45'),(176.2,'END')]

def build():
    rows=[]
    for i,(start,sid) in enumerate(CUTS):
        end=CUTS[i+1][0] if i+1<len(CUTS) else 180.0
        row={'id':sid,'start_frame':round(start*30),'end_frame':round(end*30),
             'narration_id':next((c['id'] for c in reversed(json.loads((HERE/'delivery/final-audio-report.json').read_text()).get('chapters',[])) if c.get('start',999)<=start),'N01')}
        if sid=='S04':row['source_window']=[.12,3.2]
        if sid=='S18':row['source_window']=[1.2,None]
        if sid=='S13':row['source_window']=[1.8,4.8]
        rows.append(row)
    # Actual chapter timing is stored independently in the review's ASR comparison.
    chapters=json.loads((HERE/'review-2026-10-16/verbatim-check.json').read_text())['film_pass']['chapters']
    for row in rows:
        row['narration_id']=next((c['id'] for c in reversed(chapters) if c['start']<=row['start_frame']/30+.6),'N01')
    prior=json.loads((HERE/'review-2026-10-16/caption-sync.json').read_text())['captions']
    cues=[];adjusted=[]
    for c in prior:
        a,b=c['start'],c['end']
        if c.get('asr_match_coverage',0)>=.7 and 'asr_start' in c:
            a=max(0,c['asr_start']-.04);b=min(180,c['asr_end']+.08)
            adjusted.append(c['text'])
        cues.append({'start':a,'end':b,'text':c['text']})
    for i in range(len(cues)-1):
        if cues[i]['end']>cues[i+1]['start']:
            boundary=(cues[i]['end']+cues[i+1]['start'])/2
            cues[i]['end']=boundary;cues[i+1]['start']=boundary
    out=HERE/'revision-2';out.mkdir(exist_ok=True)
    (out/'edit-plan.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    (out/'caption-plan.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2)+'\n')
    (out/'caption-corrections.json').write_text(json.dumps({'method':'independent ASR boundaries, script wording unchanged','adjusted':adjusted,'unresolved_low_coverage':[c['text'] for c in prior if c.get('asr_match_coverage',0)<.7]},ensure_ascii=False,indent=2)+'\n')
    return rows,cues
if __name__=='__main__':build()

"""New Kitakyushu-based Gacy plan: offline tests, not evidence of generated video/QC."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'production/gacy1978'
BRANCH = 'arena/3c0c229a-desktop-tutorial'


class Gacy1978PlanTests(unittest.TestCase):
    def setUp(self):
        self.story = json.loads((PROJECT / 'story.json').read_text())

    def test_exact_template_structure(self):
        s = self.story
        self.assertEqual((s['target_duration'], s['width'], s['height'], s['fps']), (180,1920,1080,30))
        self.assertEqual([r['id'] for r in s['shots']], [f'S{i:02d}' for i in range(1,46)])
        self.assertEqual(sum(x['kind']=='agnes' for x in s['shots']),38)
        self.assertEqual(sum(x['kind']=='graphic' for x in s['shots']),7)
        self.assertEqual(len(s['presentation']['cards']),7)
        self.assertTrue(all(x['duration']==4 and x['start']==i*4 for i,x in enumerate(s['shots'])))

    def test_narration_matches_manifest_and_screenplay(self):
        chapters = self.story['chapters']
        manifest = json.loads((PROJECT/'audio/manifest.json').read_text())
        self.assertEqual(len(chapters),6)
        self.assertTrue(760 <= sum(len(x['text']) for x in chapters) <= 800)
        for c,a in zip(chapters,manifest['clips']):
            self.assertEqual((c['id'],c['text']),(a['id'],a['text']))
            self.assertIn(c['text'],(PROJECT/'screenplay.md').read_text())
        self.assertIn('十五岁',chapters[2]['text'])
        self.assertNotIn('十七岁',chapters[2]['text'])

    def test_registered_adults_and_clown_alias(self):
        cast=json.loads((PROJECT/'cast.json').read_text())
        self.assertEqual({c['id'] for c in cast['characters']},{'C1','C2','C3','C4'})
        self.assertTrue(all(c['age']>=18 for c in cast['characters']))
        self.assertEqual(cast['shots']['S01'],cast['shots']['S09'])
        by_id={c['id']:c for c in cast['characters']}
        for x in self.story['shots']:
            for cid in x.get('cast',[]): self.assertIn(by_id[cid]['face'],x['prompt'])
        refs={x['id']:x['reference_image'] for x in self.story['shots'] if x.get('reference_image')}
        self.assertEqual(set(refs),{'S01','S09','S11','S25','S28','S29','S37','S45'})
        for sid,url in refs.items():
            revision='06cd2bfb9c44c4dc7bb63b977856930a4c159653' if sid in {'S29','S45'} else 'b5be38f39679925ca5ae29fb972145cb77b33eaa'
            self.assertIn('/'+revision+'/production/gacy1978/',url)
            self.assertNotIn('/production/gacy/',url)  # no abandoned identity-experiment assets

    def test_actual_sdk_payload_stays_free_with_optional_first_frame(self):
        code='''import sys,json
sys.path.insert(0,sys.argv[1])
import generate_cogvideox as g
import model_policy as p
s=json.load(open(sys.argv[1]+'/story.json'))
assert p.ALLOWED_MODELS == ('cogvideox-flash',)
for shot in s['shots']:
 if shot['kind']=='graphic':continue
 q=g.full_payload(s,shot)
 assert set(q)=={'model','prompt','quality'},q.keys()
 assert q['model']=='cogvideox-flash' and q['quality']=='speed'
 assert len(s['style_prefix']+shot['prompt']+' '+p.PROMPT_GUARDRAILS)<=2600
 assert 'HOLD:' in q['prompt']
 assert '{C' not in q['prompt']
 g.REF_IMAGE_OK=True
 q_image=g.full_payload(s,shot)
 assert set(q_image)==({'model','prompt','quality','image_url'} if shot.get('reference_image') else {'model','prompt','quality'})
 assert q_image['model']=='cogvideox-flash'
 if shot.get('reference_image'):assert q_image['image_url']==shot['reference_image']
 g.REF_IMAGE_OK=None
'''
        env=dict(os.environ,AGNES_VIDEO_MODEL='agnes-video-2.5')
        proc=subprocess.run([sys.executable,'-c',code,str(PROJECT)],capture_output=True,text=True,env=env)
        self.assertEqual(proc.returncode,0,proc.stderr)
        self.assertEqual(self.story['model'],'cogvideox-flash')

    def test_alternate_provider_cli_is_disabled(self):
        result=subprocess.run([sys.executable,str(PROJECT/'generate.py'),'--payload','{}'],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('Only --validate is enabled',result.stderr)

    def test_four_workflows_are_exact_installed_fixed_branch_copies(self):
        workflows=list((PROJECT/'workflows').glob('*.yml'))
        self.assertEqual(len(workflows),4)
        for f in workflows:
            text=f.read_text()
            self.assertEqual(text,(ROOT/'.github/workflows'/f.name).read_text())
            self.assertIn(BRANCH,text)
            self.assertNotIn('44a8fff6',text)
        gen=(PROJECT/'workflows/gacy1978-cogvideox-gen.yml').read_text()
        self.assertIn('generate.py --validate',gen)
        self.assertIn('face_cast.py check-prompts',gen)

    def test_template_provenance_is_real_and_source_unchanged(self):
        doc=json.loads((PROJECT/'template-provenance.json').read_text())
        for name,sha in doc['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/doc['source']/name).read_bytes()).hexdigest(),sha,name)
        for x in self.story['sources']:
            self.assertNotIn('pending',x['verification'])

    def test_requested_chapter_gaps_and_enlarged_keyword_captions(self):
        code = r'''import sys,json,tempfile
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import render
p=Path(sys.argv[1]);story=json.load(open(p/'story.json'))
report=json.load(open(p/'audio/tighten-report.json'))
tempo=report['total_tight_seconds']/168
start=render.INTRO;rows=[]
for clip in report['clips']:
 end=start+clip['tight_seconds']/tempo
 rows.append({'start':start,'end':end});start=end+render.GAP
windows=render.planned_blackouts(rows)
assert len(windows)==5 and all(x['end_frame']-x['start_frame']==9 for x in windows)
with tempfile.TemporaryDirectory() as tmp:
 path=Path(tmp)/'captions.ass'
 render.write_subtitles(path,[{'start':1,'end':2,'text':'三十三条生命'}],
   [{'id':'S02','kind':'graphic','start_frame':0,'end_frame':120}],story['presentation'])
 text=path.read_text()
 assert r'\fs82\c&H0076DDF2&' in text
 assert r'\fs68\c&H00FFFFFF&' in text
'''
        result=subprocess.run([sys.executable,'-c',code,str(PROJECT)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_revised_edit_needs_no_reverse_padding(self):
        code = r'''import sys,json
sys.path.insert(0,sys.argv[1])
import render
from pathlib import Path
p=Path(sys.argv[1]);story=json.load(open(p/'story.json'))
r=json.load(open(p/'audio/tighten-report.json'))
tempo=r['total_tight_seconds']/168
start=render.INTRO;rows=[]
for c in r['clips']:
 end=start+c['tight_seconds']/tempo
 rows.append({'id':c['id'],'start':start,'end':end,'tempo':tempo})
 start=end+render.GAP
edl=render.make_edl(story,rows)
for e in edl:
 if e['kind']=='agnes':
  duration=(e['end_frame']-e['start_frame'])/30
  assert duration/(5.108108-.24)<=1.33,(e['id'],duration)
assert render.END_CARD==render.OUTRO==6
assert 'reverse,trim=' not in (p/'render.py').read_text()
assert set(render.TIGHTER_CROPS)=={'S14','S43'}
'''
        result=subprocess.run([sys.executable,'-c',code,str(PROJECT)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_preliminary_mix_report_never_claims_final_film_qc(self):
        report=json.loads((PROJECT/'audio/mix-preview-report.json').read_text())
        self.assertIn('not delivered film QC',report['status'])
        self.assertEqual(report['final_silence_seconds'],1.0)
        self.assertAlmostEqual(report['bgm_relative_to_voice_db_speech_active'],-18,places=2)

    def test_sfx_events_are_supported(self):
        self.assertTrue(all(kind in ('paper','machine','press','phone','keys')
                            for _,kind in self.story['presentation']['sfx_events']))


if __name__=='__main__':unittest.main()

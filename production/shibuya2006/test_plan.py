import importlib.util
import json
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import build_story
import generate
class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.story=build_story.build()
    def test_timing(self):
        self.assertEqual(len(self.story['shots']),30)
        self.assertEqual(sum(s['duration'] for s in self.story['shots']),180)
        cursor=0
        for s in self.story['shots']:
            self.assertEqual(s['start'],cursor)
            self.assertIn(s['duration'],[5,6,7]);cursor+=s['duration']
    def test_reference_limit_and_prompt(self):
        for s in self.story['shots']:
            self.assertLessEqual(len(generate.reference_asset_ids(s)),5)
            p=generate.full_prompt(self.story,s)
            self.assertTrue(p.startswith('【STYLE】'))
            self.assertTrue(p.endswith(build_story.NEGATIVE))
            for role in s['characters']:self.assertIn(self.story['characters'][role],p)
    def test_hooks(self):
        hooks=self.story['presentation']['hooks']
        self.assertEqual([h['start'] for h in hooks],[0,8,55,80,125,130,144,156,168])
        self.assertTrue(all(h['end']-h['start']==2 for h in hooks))
    def test_paid_requests_fail_closed(self):
        project=dict(self.story, fact_check={'status':'pending'})
        with self.assertRaisesRegex(RuntimeError,'Fact check'):
            generate.full_payload(project,self.story['shots'][0])
    def test_no_old_case_or_false_receipts(self):
        text=json.dumps(self.story,ensure_ascii=False)
        self.assertNotIn('胶带',text)
        if (HERE/'results.json').exists():
            results=json.loads((HERE/'results.json').read_text())
            for row in results.get('shots',{}).values():
                if row.get('status')=='completed':
                    for field in ['video_url','sha256','bytes','request_hash']:
                        self.assertTrue(row.get(field))
        self.assertEqual(generate.REQUEST_INTERVAL_SECONDS,12.1)
    def test_group_audio_provenance(self):
        import hashlib
        manifest=json.loads((HERE/'audio/groups/manifest.json').read_text())
        story_shots={s['id']:s for s in self.story['shots']}
        for group in manifest['groups']:
            if group['status']!='superseded_script_change':
                self.assertEqual(''.join(story_shots[s]['narration'] for s in group['shots']),group['text'])
            if group['status'] in ['generated','superseded_script_change']:
                path=HERE/'audio/groups'/group['file']
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),group['sha256'])
                self.assertEqual(group['voice_id'],'voice-01')
            else:
                self.assertFalse((HERE/'audio/groups'/f"{group['id']}.mp3").exists())
    def test_no_legacy_tail_freeze(self):
        import render
        for shot in self.story['shots']:
            vf=render.normalized_video_filter(shot['id'],shot['start'],shot['duration'],24*shot['duration'])
            self.assertNotIn('tpad',vf)
    def test_audio_proposals_not_final(self):
        report=json.loads((HERE/'qa/group-tts-split-candidates.json').read_text())
        # 两种候选：静音切分兜底，或 ASR 词边界切分。都不等于对齐签收。
        self.assertIn(report['status'],('candidate_only_not_alignment_pass','asr_boundary_candidate'))
        for clip in report.get('clips',[]):
            self.assertTrue(clip.get('alignment_review','').startswith('pending'),clip['id'])
            self.assertFalse(clip.get('approved',False),clip['id'])
        # 最终 manifest 只允许由 30 条逐镜录音 + 逐条复核记录支撑；
        # 候选切分（三句连读）永远进不来。
        manifest=HERE/'audio/manifest.json'
        if manifest.exists():
            review=json.loads((HERE/'audio/review.json').read_text())
            clips=review['clips']
            self.assertEqual(len(clips),30)
            for row in clips:
                self.assertEqual(row['status'],'approved',row['id'])
                self.assertTrue(row.get('reviewed_by'),row['id'])
                self.assertTrue(row.get('review_method'),row['id'])
                self.assertEqual(len(row.get('sha256','')),64,row['id'])
    def test_character_board_bindings(self):
        import hashlib
        import preflight
        approvals=json.loads((HERE/'reference/approvals.json').read_text())['assets']
        for shot in self.story['shots']:
            self.assertEqual(set(generate.reference_asset_ids(shot)),set(preflight.asset_ids(shot)))
        self.assertIn('C09',self.story['shots'][23]['characters'])
        self.assertNotIn('C09',self.story['shots'][25]['characters'])
        for i in range(1,11):
            row=approvals[f'C{i:02}']
            self.assertEqual(row['status'],'approved')
            self.assertIn('/boards/',row['file'])
            self.assertEqual(hashlib.sha256((HERE/row['file']).read_bytes()).hexdigest(),row['sha256'])
        for board in json.loads((HERE/'reference/boards/manifest.json').read_text())['boards']:
            for source in board['sources']:
                self.assertEqual(hashlib.sha256((HERE/'reference'/source['file']).read_bytes()).hexdigest(),source['sha256'])
    def test_s28_uses_approved_single_views(self):
        urls=generate.reference_image_urls(self.story['shots'][27])
        self.assertFalse(any('/boards/' in u for u in urls))
        self.assertTrue(any('/views/C07-judge-close.png' in u for u in urls))
        self.assertFalse(any('/reference/C01.png' in u for u in urls))
    def test_single_view_cannot_substitute_other_character(self):
        shot=dict(self.story['shots'][27],single_view_references={'C07':'reference/C02.png'})
        with self.assertRaisesRegex(RuntimeError,'not an approved board source'):
            generate.reference_image_urls(shot)
    def test_unreviewed_audio_cannot_be_relabelled(self):
        import build_audio_manifest as audio
        shot=self.story['shots'][0]
        with self.assertRaisesRegex(RuntimeError,'missing approved'):
            audio.require_review(shot,HERE/'audio/S01.mp3','voice-01',{})
    def test_wrong_audio_text_cannot_be_approved(self):
        import build_audio_manifest as audio
        path=HERE/'audio/S01.mp3'
        shot=self.story['shots'][0]
        row={'status':'approved','reviewed_by':'test','review_method':'ASR',
             'text':'wrong sentence','sha256':audio.digest(path),'voice_id':'voice-01'}
        with self.assertRaisesRegex(RuntimeError,'missing approved'):
            audio.require_review(shot,path,'voice-01',{'S01':row})
if __name__=='__main__':unittest.main()

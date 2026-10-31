import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / 'nishiguchi1963'
spec = importlib.util.spec_from_file_location('nishiguchi_generator', HERE / 'generate.py')
# generate.py imports its local throttle module.
import sys
sys.path.insert(0, str(HERE))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

class NishiguchiPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = json.loads((HERE / 'story.json').read_text(encoding='utf-8'))

    def test_plan_and_exact_timeline(self):
        gen.validate(self.project, require_audio=False)
        shots = self.project['shots']
        self.assertEqual(len(shots), 30)
        self.assertEqual(sum(s['duration'] for s in shots), 180)
        self.assertTrue(all(5 <= s['duration'] <= 7 for s in shots))
        self.assertEqual(shots[-1]['start'] + shots[-1]['duration'], 180)

    def test_prompt_assembly_and_payload(self):
        for shot in self.project['shots']:
            prompt = gen.full_prompt(self.project, shot)
            self.assertTrue(prompt.startswith('【STYLE】'))
            self.assertTrue(prompt.endswith(self.project['negative_prompt']))
            for character in shot['characters']:
                self.assertIn(self.project['characters'][character], prompt)
            self.assertEqual(gen.full_payload(self.project, shot)['seconds'], str(shot['duration']))
            self.assertIn('continuous', prompt)

    def test_references_exist_and_audio_not_misrepresented(self):
        for reference in self.project['reference_images']:
            self.assertTrue((HERE / reference['file']).is_file())
        with self.assertRaises(ValueError):
            gen.validate(self.project, require_audio=True)

    def test_chapter_boundaries(self):
        cursor = 0
        for chapter in self.project['chapters']:
            self.assertEqual(chapter['start'], cursor)
            shots = [s for s in self.project['shots'] if s['narration_id'] == chapter['id']]
            self.assertEqual(chapter['shot_ids'], [s['id'] for s in shots])
            self.assertEqual(chapter['duration'], sum(s['duration'] for s in shots))
            cursor += chapter['duration']
        self.assertEqual(cursor, 180)


class RendererTests(unittest.TestCase):
    def test_caption_title_and_control_codes(self):
        import tempfile
        from production.nishiguchi1963 import render
        story = json.loads((HERE / 'story.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            ass=Path(tmp)/'captions.ass'; srt=Path(tmp)/'captions.srt'
            cues=[{'start':0.1,'end':4.0,'text':'七十八天的逃亡。'}]
            render.write_subtitles(ass,cues,story,srt)
            text=ass.read_text(encoding='utf-8')
            self.assertIn('西口彰事件',text)
            self.assertIn('\\pos(960,382)',text)
            self.assertIn('\\fad(420,430)',text)
            self.assertNotIn('\x0c',text)
            self.assertNotIn('\x07',text)
            self.assertIn('七十八天',srt.read_text(encoding='utf-8'))
            self.assertNotIn('世田谷',text)

    def test_refuse_unverified_sources(self):
        import tempfile
        from production.nishiguchi1963 import fetch_sources
        story = json.loads((HERE / 'story.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(RuntimeError, 'S01'):
            fetch_sources.restore(story, {'shots':{}}, Path(tmp))

    def test_shot_locked_audio_timeline_with_fixture(self):
        # This synthetic test intentionally repeats one audio fixture; it is NOT a film or VO review.
        import hashlib
        import shutil
        import tempfile
        from production.nishiguchi1963 import build_audio
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            self.skipTest('requires ffmpeg and ffprobe')
        story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
        fixture=HERE/'audio/S18.mp3'
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp); audio=base/'audio'; audio.mkdir()
            shutil.copy(fixture,audio/'sample.mp3')
            digest=hashlib.sha256(fixture.read_bytes()).hexdigest()
            clips=[dict(id=s['id'],file='sample.mp3',text=s['narration'],voice_id='voice-00',
                        sha256=digest,narration_id=s['narration_id'],target_start=s['start'],
                        target_duration=s['duration'],alignment='shot-locked') for s in story['shots']]
            (audio/'manifest.json').write_text(json.dumps(dict(clips=clips,voice='voice-00',slowdown_allowed=False)))
            voice,cues,report=build_audio.build_narration(story,audio,base/'work')
            self.assertEqual(len(voice),180*48000)
            self.assertEqual(len(cues),30)
            for cue,shot in zip(cues,story['shots']):
                self.assertGreaterEqual(cue['start'],shot['start'])
                self.assertLessEqual(cue['end'],shot['start']+shot['duration'])
            self.assertLessEqual(cues[-1]['end'],179)

    def test_crossfade_keeps_exact_frames(self):
        import shutil, subprocess, tempfile
        from production.nishiguchi1963 import render
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            self.skipTest('requires ffmpeg and ffprobe')
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); a=d/'a.mp4'; b=d/'b.mp4'; out=d/'out.mp4'
            for path,pattern in [(a,'testsrc2'),(b,'smptebars')]:
                subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',
                    f'{pattern}=size=320x180:rate=24:duration=2','-c:v','libx264',
                    '-pix_fmt','yuv420p',str(path)],check=True)
            render.blend_temple_outgoing(a,b,out,48)
            info=render.media_summary(out)
            self.assertEqual(info['frames'],48)
            self.assertAlmostEqual(info['duration_seconds'],2,places=2)

if __name__ == '__main__': unittest.main()

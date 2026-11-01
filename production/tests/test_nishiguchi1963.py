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
        missing = [s for s in self.project['shots'] if not (HERE / 'audio' / (s['id'] + '.mp3')).is_file()]
        if missing:
            with self.assertRaises(ValueError):
                gen.validate(self.project, require_audio=True)
        else:
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

    def test_retime_continues_after_preblended_frames(self):
        import shutil, subprocess, tempfile
        import numpy as np
        from PIL import Image
        from production.nishiguchi1963 import render
        if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
            self.skipTest('requires ffmpeg and ffprobe')
        with tempfile.TemporaryDirectory() as tmp:
            d=Path(tmp); source=d/'original.mp4'; shifted=d/'shifted.mp4'
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i',
                'testsrc2=size=320x180:rate=24:duration=2','-c:v','libx264',
                '-pix_fmt','yuv420p',str(source)],check=True)
            render.retime_after_preblend(source,shifted,48)
            self.assertEqual(render.media_summary(shifted)['frames'],48)
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(source),'-vf',
                "select='eq(n,7)'",'-vsync','0','-frames:v','1',str(d/'frame7.png')],check=True)
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(shifted),
                '-frames:v','1',str(d/'first.png')],check=True)
            with Image.open(d/'frame7.png') as a, Image.open(d/'first.png') as b:
                delta=np.abs(np.asarray(a,dtype=np.float32)-np.asarray(b,dtype=np.float32)).mean()
                self.assertLess(delta,4.0)  # allow normal lossy re-encoding differences

    def test_qc_checks_subtitle_text_and_shot_timing(self):
        import tempfile
        from production.nishiguchi1963 import render, qc
        story=json.loads((HERE/'story.json').read_text(encoding='utf-8'))
        cues=[{'start':s['start']+0.1,'end':s['start']+1.5,'text':s['narration']} for s in story['shots']]
        with tempfile.TemporaryDirectory() as tmp:
            ass=Path(tmp)/'captions.ass'; srt=Path(tmp)/'captions.srt'
            render.write_subtitles(ass,cues,story,srt)
            info=qc.check_subtitles(srt,story)
            self.assertEqual(info['cues'],30)
            self.assertTrue(info['covers_all_lines'])
            self.assertEqual(info['problems'],[])
            srt.write_text(srt.read_text(encoding='utf-8').replace(story['shots'][0]['narration'],'字幕错误'),encoding='utf-8')
            self.assertFalse(qc.check_subtitles(srt,story)['covers_all_lines'])

    def test_writing_mask_only_applies_to_calibrated_source(self):
        import tempfile
        from PIL import Image
        from production.nishiguchi1963 import render
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'mask.png'
            self.assertIsNone(render.writing_soften_mask('S06', 'different source', path))
            self.assertFalse(path.exists())
            expected=render.WRITING_SOFTENING['S06']['sha256']
            self.assertEqual(render.writing_soften_mask('S06', expected, path), path)
            with Image.open(path) as image:
                self.assertEqual(image.size,(1920,1080))
                self.assertEqual(image.getpixel((400,900)),255)
                self.assertEqual(image.getpixel((1000,500)),0)

    def test_ffprobe_shim_reports_real_file_size(self):
        import shutil, subprocess, tempfile
        if not shutil.which('ffmpeg'):
            self.skipTest('requires ffmpeg')
        with tempfile.TemporaryDirectory() as tmp:
            video = Path(tmp) / 'sample.mp4'
            subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'lavfi', '-i',
                            'testsrc2=size=320x180:rate=24:duration=1', '-c:v', 'libx264',
                            '-pix_fmt', 'yuv420p', str(video)], check=True)
            shim = HERE.parents[0] / 'setagaya2000' / 'ffprobe_shim.py'
            output = subprocess.check_output([sys.executable, str(shim), '-show_format',
                                              '-show_streams', '-of', 'json', str(video)], text=True)
            self.assertEqual(int(json.loads(output)['format']['size']), video.stat().st_size)
            # Check the fallback parser as well as the normal PyAV path.
            # Pass paths through explicit arguments to avoid interpolating shell commands.
            script = ("import json,runpy,sys; shim,path=sys.argv[1:]; sys.argv=['ffprobe',path];"
                      "m=runpy.run_path(shim,run_name='shim_test');"
                      "print(json.dumps(m['probe_with_ffmpeg']('ffmpeg')))")
            output = subprocess.check_output([sys.executable, '-c', script, str(shim), str(video)], text=True)
            self.assertEqual(int(json.loads(output)['format']['size']), video.stat().st_size)

    def test_motion_then_render_workflows(self):
        import yaml
        root=HERE.parents[1]
        motion=yaml.safe_load((root/'.github/workflows/nishiguchi1963-gen.yml').read_text())
        render=yaml.safe_load((root/'.github/workflows/nishiguchi1963-render.yml').read_text())
        self.assertEqual(motion['jobs']['first-cut']['needs'],'motion')
        self.assertEqual(motion['jobs']['first-cut']['uses'],'./.github/workflows/nishiguchi1963-render.yml')
        events=render.get('on',render.get(True,{}))
        self.assertIn('workflow_call',events)
        self.assertEqual(motion['jobs']['first-cut']['permissions']['contents'],'write')

if __name__ == '__main__': unittest.main()

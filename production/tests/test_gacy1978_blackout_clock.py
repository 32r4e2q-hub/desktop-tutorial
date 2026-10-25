"""Real mixed-colour-range concat regression: filter-local n may reset, PTS must not."""
from pathlib import Path
import json
import shutil
import sys
import subprocess
import tempfile
import unittest

import av

ROOT=Path(__file__).resolve().parents[2]


@unittest.skipUnless(shutil.which('ffmpeg'), 'native ffmpeg required for codec integration test')
class BlackoutClockTests(unittest.TestCase):
    def test_blackouts_stay_at_exact_pts_after_range_transition(self):
        # Import in a child process to avoid other projects' render.py modules.
        script=r'''
import json,sys
sys.path.insert(0,sys.argv[1])
import render
print(json.dumps({'vf':render.NORMALISE_COLOUR+render.blackout_filters([{'start_frame':150,'end_frame':159}]),
                  'flags':render.COLOUR_FLAGS}))
'''
        cfg=json.loads(subprocess.check_output([sys.executable,'-c',script,str(ROOT/'production/gacy1978')],text=True))
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)
            def ff(*args):
                subprocess.run(['ffmpeg','-v','error','-y',*map(str,args)],check=True,capture_output=True)
            for name,frames,colour_range in [('a',127,'tv'),('b',180,'pc')]:
                ff('-f','lavfi','-i','testsrc2=size=160x90:rate=30','-frames:v',frames,
                   '-pix_fmt','yuv420p','-color_range',colour_range,'-c:v','libx264','-preset','ultrafast',p/f'{name}.mp4')
            (p/'concat.txt').write_text("file 'a.mp4'\nfile 'b.mp4'\n")
            ff('-f','concat','-safe','0','-i',p/'concat.txt','-c','copy',p/'track.mp4')
            ff('-i',p/'track.mp4','-vf',cfg['vf'],*cfg['flags'],'-c:v','libx264','-preset','ultrafast',p/'fixed.mp4')
            black=[];frames=0
            with av.open(str(p/'fixed.mp4')) as container:
                for i,frame in enumerate(container.decode(video=0)):
                    a=frame.to_ndarray(format='rgb24')
                    if a.mean()<2 and a.std()<2:black.append(i)
                    frames+=1
            self.assertEqual(frames,307)
            self.assertEqual(black,list(range(150,159)))


if __name__=='__main__':
    unittest.main()

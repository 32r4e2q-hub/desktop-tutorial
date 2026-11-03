import json,tempfile,unittest
from pathlib import Path
from production.crippen1910.transitions import graph,HANDLE,HANDLE_FRAMES,kind
from production.crippen1910.render import write_subtitles
ROOT=Path(__file__).resolve().parents[2]

class TransitionTests(unittest.TestCase):
    def test_cut_times_never_move(self):
        story=json.loads((ROOT/'production/crippen1910/story.json').read_text())
        filters,rows=graph(story['shots'])
        self.assertEqual(len(rows),29)
        self.assertEqual([r['start'] for r in rows],[s['start'] for s in story['shots'][1:]])
        self.assertAlmostEqual(HANDLE,7/24)
        self.assertEqual(HANDLE_FRAMES,7)
        self.assertIn('circleopen',filters)
        self.assertEqual(sum(s['duration'] for s in story['shots']),180)
    def test_three_required_transition_types(self):
        self.assertEqual(kind('S02'),'radio_ring')
        self.assertEqual(kind('S15'),'wave')
        self.assertEqual(kind('S08'),'fog')
    def test_ass_has_no_accidental_python_escape_characters(self):
        story=json.loads((ROOT/'production/crippen1910/story.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory);write_subtitles(p/'t.ass',[],story,p/'t.srt')
            text=(p/'t.ass').read_text()
            self.assertFalse(any(ord(c)<32 and c not in '\n\r\t' for c in text))
            self.assertIn(r'\fs96',text)

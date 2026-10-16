"""Synthetic controls for independent final-film sync measurements (no ASR/network)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

PATH=Path(__file__).resolve().parents[1]/'lee_hyung_ho1991/deep_review.py'
spec=importlib.util.spec_from_file_location('lee_review',PATH)
review=importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)

class DeepReviewTests(unittest.TestCase):
    def measure(self, lag):
        rate=8000
        reference=np.random.default_rng(42).normal(0,.1,rate*8).astype(np.float32)
        film=np.zeros(rate*12,dtype=np.float32)
        offset=round((1+lag)*rate);film[offset:offset+len(reference)]=reference
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            def decode(path):
                return film if Path(path).name=='film.mp4' else reference
            def run(*args,**kwargs):
                (out/'N01-retimed.wav').touch()
            with patch.object(review,'decode',side_effect=decode),patch.object(review.subprocess,'run',side_effect=run):
                review.waveform_sync(Path('film.mp4'),out,[{'id':'N01','start':1,'end':9}],1)
            return json.loads((out/'waveform-sync.json').read_text())

    def test_small_known_delay_is_measured_not_assumed_zero(self):
        result=self.measure(.04)
        self.assertTrue(result['pass'])
        for row in result['chapters'][0]['windows']:
            self.assertAlmostEqual(row['lag_seconds'],.04,places=4)
            self.assertGreater(row['normalized_correlation'],.99)

    def test_excessive_known_delay_fails_sync_gate(self):
        result=self.measure(.3)
        self.assertFalse(result['pass'])
        for row in result['chapters'][0]['windows']:
            self.assertAlmostEqual(row['lag_seconds'],.3,places=4)

    def test_montage_writes_expected_tile_geometry(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'sheet.jpg'
            review.compose([('a',Image.new('RGB',(200,100)))]*5,path,cols=4,w=128,h=128,label_h=28)
            self.assertEqual(Image.open(path).size,(512,312))

if __name__=='__main__':
    unittest.main()

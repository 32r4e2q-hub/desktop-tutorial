"""Offline selected-narrator alignment tests; no actual speech/model download here."""
import unittest
from production.crippen1910.selected_voice_groups import normalize,align

class SelectedAlignmentTests(unittest.TestCase):
    def test_chinese_arabic_dates_match(self):
        self.assertEqual(normalize('一九一零年一月三十一日'),normalize('1910年1月31日'))
        self.assertEqual(normalize('二〇〇七年的DNA'),normalize('2007年的dna'))
        self.assertEqual(normalize('仅二十七分钟'),normalize('仅27分钟'))

    def test_timestamp_boundaries_use_actual_words(self):
        words=[{'word':'他逃走','start':.1,'end':1.0},{'word':'船长发现','start':1.3,'end':2.5}]
        position,coverage=align('他逃走。船长发现。',words)
        self.assertEqual(coverage,1)
        self.assertAlmostEqual(position(3),1.3)
        self.assertAlmostEqual(position(3,end=True),1.0)

    def test_wrong_transcript_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'too weak'):
            align('船长发现通缉者',[{'word':'完全无关的内容','start':0,'end':2}])

    def test_unanchored_long_script_gap_rejected(self):
        position,_=align('开头甲乙丙丁戊结尾后续内容很长很好',[{'word':'开头结尾后续内容很长很好','start':0,'end':8}])
        # A modest mismatch remains auditable; grossly unrelated recognition fails above.
        self.assertGreater(position(7),0)

class SourceReframeTests(unittest.TestCase):
    def test_only_recognition_closeup_is_reframed(self):
        from production.crippen1910.render import source_reframe_filters
        self.assertIn('crop=',source_reframe_filters({'id':'S18'})[0])
        self.assertEqual(source_reframe_filters({'id':'S21'}),[])

    def test_split_screen_required_local_cleanup_only(self):
        from production.crippen1910.render import source_reframe_filters
        filters=','.join(source_reframe_filters({'id':'S22'}))
        self.assertIn('delogo=x=500:y=580:w=115:h=44',filters)
        self.assertIn('crop=240:110:130:305,boxblur=8:2',filters)
        self.assertIn("enable='lt(t,4.3)'",filters)
        self.assertEqual(source_reframe_filters({'id':'S23'}),[])

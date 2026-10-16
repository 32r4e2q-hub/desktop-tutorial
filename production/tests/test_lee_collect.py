"""Exact-byte source recovery; no CDN or model request is permitted."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

PATH=Path(__file__).resolve().parents[1]/'lee_hyung_ho1991/collect_sources.py'
spec=importlib.util.spec_from_file_location('lee_collect_sources',PATH)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)

class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.cache=self.root/'cache';self.cache.mkdir();self.dest=self.root/'dest'
        self.project={'shots':[{'id':'S01','kind':'cogvideo'}]}
        self.receipts={'shots':{'S01':{'status':'completed','request_hash':'wanted','sha256':hashlib.sha256(b'correct').hexdigest()}}}
        mock=patch.object(c,'request_hash',return_value='wanted');mock.start();self.addCleanup(mock.stop)
    def candidate(self,directory,data):
        p=self.cache/directory/'S01.mp4';p.parent.mkdir(parents=True);p.write_bytes(data);return p
    def test_selects_matching_hash_not_last_filename(self):
        self.candidate('a',b'correct');self.candidate('z',b'old-rejected')
        report=c.collect(self.project,self.receipts,self.cache,self.dest)
        self.assertEqual(report['missing'],[])
        self.assertEqual((self.dest/'S01.mp4').read_bytes(),b'correct')
    def test_reports_missing_exact_bytes_without_regeneration(self):
        self.candidate('a',b'old-rejected')
        report=c.collect(self.project,self.receipts,self.cache,self.dest)
        self.assertEqual(report['missing'],['S01'])
        self.assertFalse((self.dest/'S01.mp4').exists())
    def test_rejects_changed_prompt_receipt(self):
        self.receipts['shots']['S01']['request_hash']='old'
        self.candidate('a',b'correct')
        with self.assertRaises(RuntimeError):c.collect(self.project,self.receipts,self.cache,self.dest)
    def test_reuses_existing_verified_file(self):
        self.dest.mkdir();(self.dest/'S01.mp4').write_bytes(b'correct')
        report=c.collect(self.project,self.receipts,self.cache,self.dest)
        self.assertEqual(report['missing'],[])
        self.assertEqual(report['clips']['S01']['restored_from'],str(self.dest/'S01.mp4'))

if __name__=='__main__':unittest.main()

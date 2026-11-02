import base64
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'production/crippen1910'
spec=importlib.util.spec_from_file_location('crippen_reference_batch',HERE/'batch_references.py')
batch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class BatchReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=batch.plan(json.loads((HERE/'story.json').read_text()))

    def test_complete_thirty_image_queue(self):
        self.assertEqual(len(self.rows),30)
        self.assertEqual(len({r['id'] for r in self.rows}),30)
        self.assertEqual(sum(r['view']=='side' for r in self.rows),10)
        self.assertEqual(sum(r['view']=='back' for r in self.rows),10)
        self.assertEqual(sum(r['view']=='face' for r in self.rows),9)
        self.assertEqual(sum(r['view']=='prop_revision' for r in self.rows),1)

    def test_existing_face_is_not_overwritten(self):
        self.assertNotIn('C01_face',{r['id'] for r in self.rows})

    def test_every_view_uses_its_own_identity_source(self):
        for row in self.rows:
            if row['role']:
                if row['view'] in {'side','back'}:
                    self.assertEqual(row['inputs'][0],f"reference-guides/{row['view']}.png")
                    self.assertEqual(row['inputs'][1:],[f"reference/{row['role']}.png"])
                    self.assertEqual(row['input_transforms'],['full','head_crop'])
                else:
                    self.assertEqual(row['inputs'],[f"reference/{row['role']}.png"])
                    self.assertEqual(row['input_transforms'],['head_crop'])
                self.assertIn('no panels',row['prompt'])
            for source in row['inputs']:
                self.assertTrue((HERE/source).is_file())

    def test_documented_image_to_image_contract(self):
        payload=batch.make_payload(self.rows[0])
        self.assertEqual(payload['model'],'agnes-image-2.5-flash')
        self.assertNotIn('response_format',payload)
        self.assertEqual(payload['extra_body']['response_format'],'url')
        self.assertEqual(payload['size'],'1K')
        uri=payload['extra_body']['image'][0]
        self.assertTrue(uri.startswith('data:image/png;base64,'))
        self.assertEqual(base64.b64decode(uri.split(',',1)[1]),(HERE/self.rows[0]['inputs'][0]).read_bytes())

    def test_portrait_update_has_one_prop_input(self):
        row=next(r for r in self.rows if r['id']=='P02')
        self.assertEqual(row['inputs'],['reference/P02.png'])
        self.assertEqual(row['ratio'],'16:9')

if __name__=='__main__':unittest.main()

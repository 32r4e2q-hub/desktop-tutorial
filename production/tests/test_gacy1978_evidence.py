"""Bound repository previews without discarding the SHA-bound candidate index."""
import importlib.util
import json
from pathlib import Path

PUBLISHER = Path(__file__).resolve().parents[1] / 'gacy1978/publish_visual_review_bundle.py'
spec = importlib.util.spec_from_file_location('gacy1978_evidence', PUBLISHER)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(source, count, reasons):
    source.mkdir()
    rows = []
    for i in range(count):
        name = f'f{i:05}.jpg'
        (source / name).write_bytes(b'fixture')
        rows.append({'frame': i, 'file': name, 'reasons': reasons(i)})
    (source / 'manifest.json').write_text(json.dumps({'film_sha256': 'a'*64, 'frames': rows}))


def test_face_preview_sampling_preserves_complete_missing_index(tmp_path):
    fixture(tmp_path/'in', 90, lambda i: ['temporal-S01-start'] if i==12 else ['face-S01'])
    images, manifests = module._copy_candidate_previews(tmp_path/'in', tmp_path/'out')
    report = json.loads(Path(manifests[0]).read_text())
    assert len(images) == 4
    retained = {r['frame'] for r in report['frames']}
    assert {0,12,45,89} == retained
    assert report['film_sha256'] == 'a'*64
    assert report['full_candidate_count'] == 90
    assert retained | set(report['unpublished_candidate_frames']) == set(range(90))
    assert 'NOT approval' in report['review_status']


def test_many_temporal_previews_are_bounded_and_keep_endpoints(tmp_path):
    fixture(tmp_path/'in', 240, lambda i: [f'temporal-S{i//3}-start'])
    images, manifests = module._copy_candidate_previews(tmp_path/'in', tmp_path/'out')
    report = json.loads(Path(manifests[0]).read_text())
    assert len(images) == 160
    assert report['frames'][0]['frame'] == 0
    assert report['frames'][-1]['frame'] == 239
    assert len(report['unpublished_candidate_frames']) == 80
    assert report['preview_bytes'] <= 12*1024*1024

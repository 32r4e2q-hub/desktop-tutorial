import importlib.util,json,sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parents[1]/'lee_hyung_ho1991'
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location("lee_revision_render",HERE/"render.py")
render=importlib.util.module_from_spec(spec);spec.loader.exec_module(render)
from revise_edit import build

def test_revised_cut_covers_180_seconds_and_all_sources_once():
    rows,cues=build()
    project=json.loads((HERE/'story.json').read_text())
    edl=render.load_edit_plan(HERE/'revision-2/edit-plan.json',project)
    assert len(edl)==46 and edl[-1]['end_frame']==5400
    assert len({r['id'] for r in rows})==46
    assert all(c['start']<c['end'] for c in cues)
    assert all(a['end']<=b['start'] for a,b in zip(cues,cues[1:]))
    positions={r['id']:r['start_frame']/30 for r in rows}
    assert 14<positions['S10']<16
    assert 48<positions['S17']<51
    assert 123<positions['S37']<125
    assert 89<positions['S25']<91

def test_invalid_revision_gap_is_rejected(tmp_path):
    rows,_=build();rows[1]['start_frame']+=1
    f=tmp_path/'bad.json';f.write_text(json.dumps(rows))
    with pytest.raises(ValueError,match='gap'):render.load_edit_plan(f,json.loads((HERE/'story.json').read_text()))

def test_only_replacement_payload_hashes_change():
    spec=importlib.util.spec_from_file_location("lee_revision_generate",HERE/"generate.py")
    generate=importlib.util.module_from_spec(spec);spec.loader.exec_module(generate)
    p=json.loads((HERE/'story.json').read_text())
    ids=set(json.loads((HERE/'REVISION_REQUEST').read_text())['only'].split(','))
    receipts=json.loads((HERE/'results.json').read_text())['shots']
    for s in p['shots']:
        if s['kind']=='cogvideo' and s['id'] not in ids:
            assert generate.request_hash(p,s)==receipts[s['id']]['request_hash']
    for s in p['shots']:
        if s['id'] in ids:
            payload=generate.full_payload(p,s)
            assert 'image_url' not in payload
            assert 'FIRST frame' in s['prompt']
            assert 'No transitions or dissolves' in payload['prompt']

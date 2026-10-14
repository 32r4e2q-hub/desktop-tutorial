"""No network, no provider calls, no generated media needed."""
import copy
import datetime
import importlib.util
import json
from pathlib import Path
import pytest

PROJECT = Path(__file__).resolve().parents[1] / 'kimdaedoo'

def load(name):
    spec = importlib.util.spec_from_file_location('kim_' + name, PROJECT / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

@pytest.fixture
def story():
    return json.loads((PROJECT / 'story.json').read_text())

def test_plan_and_audio_text(story):
    load('generate').validate(story)
    assert len(story['shots']) == 45
    assert sum(s['kind'] == 'agnes' for s in story['shots']) == 38
    assert len(story['presentation']['cards']) == 7
    assert 740 <= sum(len(c['text']) for c in story['chapters']) <= 820
    assert '3D animated reenactment' in story['style_prefix']

def test_agnes_new_payload(story):
    p = load('generate').full_payload(story, story['shots'][0])
    assert p['model'] == 'agnes-video-2.5-flash'
    assert p['mode'] == 'text' and p['size'] == '720P'
    assert p['aspect_ratio'] == '16:9'
    assert not {'width','height','num_frames','frame_rate','seed'} & p.keys()

def test_hash_changes_on_prompt(story):
    g = load('generate')
    shot = copy.deepcopy(story['shots'][0])
    h = g.request_hash(story, shot)
    shot['prompt'] += ' extra'
    assert g.request_hash(story, shot) != h

@pytest.mark.parametrize('model',['cogvideox-flash','agnes-video-2.5','agnes-video-v2.0'])
def test_no_vendor_or_paid_fallback(story,model):
    story['model'] = model
    with pytest.raises(ValueError):
        load('generate').full_payload(story,story['shots'][0])

def test_free_guard_default_closed():
    with pytest.raises(RuntimeError):
        load('generate').billing_gate(json.loads((PROJECT/'billing-policy.json').read_text()))

def test_expired_eligibility_closed():
    with pytest.raises(RuntimeError):
        load('generate').billing_gate({'model':'agnes-video-2.5-flash','zero_cost_verified':True,
            'max_charge':0,'evidence_url':'https://example.com/price','expires_at':'2020-01-01T00:00:00Z'})

@pytest.mark.parametrize('code,text,want',[
    (429,'quota rate limit','rate_limited'),
    (503,'model_not_found No available channel','model_unavailable'),
    (503,'video queue is full','queue_full_not_proof_of_free_generation'),
    (403,'insufficient_user_quota','quota_or_payment_required'),
    (400,'prompt is required','validation_rejected_free_generation_unverified'),
])
def test_honest_probe_classification(code,text,want):
    assert load('probe_models').classify(code,text) == want

def test_submission_is_not_repeated_when_ambiguous(story,tmp_path,monkeypatch):
    g=load('generate')
    shot=story['shots'][0]
    doc={'shots':{'S01':{'status':'submission_ambiguous','request_hash':g.request_hash(story,shot)}}}
    def unexpected(*a,**k):
        raise AssertionError('Never submit a second task after response loss')
    monkeypatch.setattr(g.api,'http_json',unexpected)
    with pytest.raises(RuntimeError,match='reconciliation'):
        g.run_shot(story,shot,doc,'not-a-real-key')

def test_cuts_cover_every_shot_once(story):
    import ast
    tree=ast.parse((PROJECT/'render.py').read_text())
    cuts=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='CUTS' for t in n.targets))
    ids=[sid for rows in cuts.values() for _,sid,_ in rows]
    assert sorted(ids) == sorted(s['id'] for s in story['shots'])

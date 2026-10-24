"""离线校验制作清单；不提交付费请求，不读取或输出密钥。"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

def validate(plan):
    assert (plan['width'], plan['height'], plan['duration']) == (1920, 1080, 180)
    assert len(plan['shots']) == 29
    end = 0
    for index, shot in enumerate(plan['shots'], 1):
        assert shot['id'] == f'S{index:02}'
        assert shot['start'] == end
        assert shot['end'] - shot['start'] == shot['duration']
        assert 4 <= shot['duration'] <= 9
        assert shot['prompt'].startswith(plan['style'])
        assert '【NEGATIVE】' in shot['prompt']
        for role in shot['roles']:
            assert plan['characters'][role] in shot['prompt']
        end = shot['end']
    assert end == 180
    assert sum(s['duration'] for s in plan['shots']) == 180
    assert plan['narration'][0]['start'] == 0
    assert plan['narration'][-1]['end'] == 180
    for a, b in zip(plan['narration'], plan['narration'][1:]):
        assert a['end'] == b['start']
    warnings = []
    for n in plan['narration']:
        count = sum(c.isalnum() for c in n['text'])
        rate = count / (n['end'] - n['start'])
        if rate > 3.7:
            warnings.append(f"{n['start']}–{n['end']}秒旁白约{rate:.2f}字/秒，高于目标3.7；须以实际TTS时长复核，不得删词。")
    return warnings

if __name__ == '__main__':
    plan = json.loads((HERE / 'story.json').read_text())
    warnings = validate(plan)
    print('PASS：29镜头，连续180秒，1920×1080，各镜头4–9秒；风格/角色/负面提示已装配。')
    for warning in warnings:
        print('WARNING：' + warning)
    print('仅校验计划：参考图、视频、旁白与成片尚未生成。')

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFont
import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = ROOT / 'production' / 'mystery-cover-template'
CLI = TOOL_DIR / 'generate_cover.py'
sys.path.insert(0, str(TOOL_DIR))
spec = importlib.util.spec_from_file_location('mystery_generate_cover', CLI)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
from build_template import fitted_font
import template


def run(output, episode='2', line1='逃亡七十八天的谜案', line2='一张通缉照揭开真相', extra=()):
    return subprocess.run(
        [sys.executable, str(CLI), '--episode', str(episode), '--line1', line1,
         '--line2', line2, '--output', str(output), *extra],
        text=True, capture_output=True,
    )


@pytest.mark.parametrize(('number', 'label'), [
    (1, '第一期'), (2, '第二期'), (10, '第十期'), (11, '第十一期'),
    (20, '第二十期'), (101, '第一百零一期'), (1010, '第一千零一十期'),
    (9999, '第九千九百九十九期'),
])
def test_episode_labels(number, label):
    assert generator.episode_text(number) == label


def test_generation_records_different_episode_and_title(tmp_path):
    a, b = tmp_path / 'first.png', tmp_path / 'second.png'
    p1 = run(a, 1, '逃亡78天的西口彰', '却被女孩一眼认出',
             ('--release-title', '西口彰：女孩认出通缉犯', '--fact-basis', '项目剧本'))
    p2 = run(b, 2)
    assert p1.returncode == p2.returncode == 0, (p1.stderr, p2.stderr)
    first, second = Image.open(a), Image.open(b)
    assert first.size == second.size == (1080, 1440)
    assert ImageChops.difference(first.crop((780, 70, 1020, 140)),
                                 second.crop((780, 70, 1020, 140))).getbbox()
    assert ImageChops.difference(first.crop((50, 280, 1030, 560)),
                                 second.crop((50, 280, 1030, 560))).getbbox()
    # Background and layout stay fixed outside the changing text areas: 截图窗口里都是空位，
    # 只有角标和窗口字幕条上的 CASE FILE 编号随期数变。
    assert not ImageChops.difference(first.crop((0, 620, 1080, 970)),
                                     second.crop((0, 620, 1080, 970))).getbbox()
    data = json.loads(a.with_suffix('.json').read_text(encoding='utf8'))
    assert data['episode'] == 1 and data['episode_label'] == '第一期'
    assert data['cover_title_lines'] == ['逃亡78天的西口彰', '却被女孩一眼认出']
    assert data['release_title'] == '西口彰：女孩认出通缉犯'
    assert data['fact_basis'] == '项目剧本'
    assert json.loads(b.with_suffix('.json').read_text(encoding='utf8'))['episode'] == 2


def test_longest_lines_and_episode_fit_layout(tmp_path):
    result = run(tmp_path / 'long.png', 9999, '谜' * 18, '案' * 18)
    assert result.returncode == 0, result.stderr
    draw = ImageDraw.Draw(Image.new('RGB', (1080, 1440)))
    for text, maxsize, width, minimum in [('谜' * 18, 106, 940, 30),
                                          (generator.episode_text(9999), 33, 190, 16)]:
        font = fitted_font(generator.DEFAULT_FONT, draw, text, maxsize, width, minimum)
        left, _, right, _ = draw.textbbox((0, 0), text, font=font)
        assert max(draw.textlength(text, font=font), right) - min(0, left) <= width


@pytest.mark.parametrize(('episode', 'line1', 'line2', 'error'), [
    ('0', '标题', '标题', '期数'), ('10000', '标题', '标题', '期数'),
    ('2', '', '标题', '第一行'), ('2', '谜' * 19, '标题', '第一行'),
    ('2', '一行\n两行', '标题', '第一行'), ('2', '含𠮷字', '标题', '字体缺字'),
])
def test_invalid_input_is_rejected(tmp_path, episode, line1, line2, error):
    output = tmp_path / 'invalid.png'
    result = run(output, episode, line1, line2)
    assert result.returncode != 0 and error in result.stderr
    assert not output.exists() and not output.with_suffix('.json').exists()


def test_no_overwrite_of_either_output_without_force(tmp_path):
    output = tmp_path / 'cover.png'
    metadata = output.with_suffix('.json')
    metadata.write_text('keep', encoding='utf8')
    result = run(output)
    assert result.returncode != 0 and '已存在' in result.stderr
    assert metadata.read_text(encoding='utf8') == 'keep' and not output.exists()
    assert run(output, extra=('--force',)).returncode == 0
    original = output.read_bytes()
    assert run(output, line1='另一个标题').returncode != 0
    assert output.read_bytes() == original
    assert run(output, line1='另一个标题', extra=('--force',)).returncode == 0
    assert output.read_bytes() != original


def test_window_takes_a_frame_from_the_film(tmp_path):
    """窗口里必须是本片的一帧，而不是底板自带的书桌。"""
    shot = Image.new('RGB', (1920, 1080), (0, 0, 0))
    ImageDraw.Draw(shot).rectangle((0, 0, 1920, 400), fill=(230, 40, 40))
    path = tmp_path / 'shot.png'
    shot.save(path)
    empty = template.cover(template.DEFAULT_FONT, 2, '传说里两百万人失踪', '他只承认了九个人')
    filled = template.cover(template.DEFAULT_FONT, 2, '传说里两百万人失踪', '他只承认了九个人', shot=path)
    window = (140, 640, 940, 960)
    assert ImageChops.difference(empty.crop(window), filled.crop(window)).getbbox()
    # 底部标语与期数角标不受截图影响。
    assert not ImageChops.difference(empty.crop((0, 1150, 1080, 1440)),
                                     filled.crop((0, 1150, 1080, 1440))).getbbox()
    # 截图铺满窗口：红色区域出现在窗口上部。
    red = filled.crop(window).split()[0].resize((8, 4))
    assert max(red.get_flattened_data() if hasattr(red, 'get_flattened_data') else red.getdata()) > 180


def test_one_template_drives_the_cli_and_the_editor_sample():
    """CLI 与编辑器样张都走 template.cover，版式只保留一份。"""
    cli_source = CLI.read_text(encoding='utf8')
    build_source = (TOOL_DIR / 'build_template.py').read_text(encoding='utf8')
    assert 'from template import' in cli_source and '_cover(' in build_source
    assert 'def cover(' in (TOOL_DIR / 'template.py').read_text(encoding='utf8')
    # 旧版 16:9 撕裂封面已经从工程里删除。
    for project in ('holmes1893', 'nishiguchi1963', 'setagaya2000'):
        source = (ROOT / 'production' / project / 'render.py').read_text(encoding='utf8')
        assert 'tear_path(' not in source or project != 'holmes1893'


def test_every_project_renders_the_same_template(tmp_path):
    """每部片子的 render.py 都必须走 production/series_cover.py，不允许各写一套封面。"""
    sys.path.insert(0, str(ROOT))
    from production import series_cover

    for project in ('holmes1893', 'nishiguchi1963', 'setagaya2000'):
        source = (ROOT / 'production' / project / 'render.py').read_text(encoding='utf8')
        assert 'series_cover.make(' in source, project
        assert 'tear_path(' not in source, project
        story = json.loads((ROOT / 'production' / project / 'story.json').read_text(encoding='utf8'))
        cfg = series_cover.cover_config(story)
        assert 1 <= cfg['episode'] <= 9999, project
        assert 1 <= len(cfg['line1']) <= 18 and 1 <= len(cfg['line2']) <= 18, project
        assert cfg['shot'] in [shot['id'] for shot in story['shots']], project


def test_series_cover_entry_writes_both_formats(tmp_path):
    sys.path.insert(0, str(ROOT))
    from production import series_cover

    story = {
        'title': '测试案件',
        'shots': [{'id': 'S01', 'start': 0, 'duration': 5}],
        'presentation': {'cover': {'series_episode': 7, 'line1': '第一行标题', 'line2': '第二行标题',
                                   'window_shot': 'S01', 'window_at': 1.0}},
    }
    shot = Image.new('RGB', (1920, 1080), (12, 12, 12))
    output = tmp_path / '封面.jpg'
    image = series_cover.render_with_frame(story, shot, output)
    assert image.size == (1080, 1440)
    assert output.is_file() and output.with_suffix('.png').is_file()
    # 角标写着第七期
    badge = image.crop((790, 76, 1012, 132))
    assert badge.convert('L').getextrema()[1] > 120


def test_film_stills_with_burned_in_subtitles_are_rejected():
    """截图窗口底部一旦压到成片字幕，就要换帧：给出可复现的检测方式。"""
    sys.path.insert(0, str(ROOT))
    from production import series_cover

    template_ = series_cover.template
    left, top, right, bottom = template_.SHOT_BOX
    width, height = right - left, bottom - top
    clean = Image.new('RGB', (1920, 1080), (10, 10, 10))
    dirty = clean.copy()
    ImageDraw.Draw(dirty).text((500, 780), '这是一句很亮的中文字幕',
                               font=ImageFont.truetype(str(template_.DEFAULT_FONT), 64),
                               fill=(255, 255, 255))

    def subtitle_ink(shot):
        band = template_.fill_crop(shot, width, height).convert('L').crop((0, int(height * 0.72), width, height))
        return sum(1 for value in list(band.getdata()) if value > 200)

    assert subtitle_ink(clean) < 60
    assert subtitle_ink(dirty) > 400

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image, ImageChops, ImageDraw
import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = ROOT / 'production' / 'mystery-cover-template'
CLI = TOOL_DIR / 'generate_cover.py'
SAMPLE = TOOL_DIR / '第一期_视频截图示例.jpg'
sys.path.insert(0, str(TOOL_DIR))
spec = importlib.util.spec_from_file_location('mystery_generate_cover', CLI)
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)
from build_template import fitted_font


def run(output, episode='2', line1='逃亡七十八天的谜案', line2='一张通缉照揭开真相', extra=(), source=None):
    if source is None:
        source = ('--screenshot', str(SAMPLE))
    return subprocess.run(
        [sys.executable, str(CLI), '--episode', str(episode), '--line1', line1,
         '--line2', line2, '--output', str(output), *source, *extra],
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
    # Background and layout stay fixed outside the changing text areas.
    assert not ImageChops.difference(first.crop((0, 1080, 1080, 1200)),
                                     second.crop((0, 1080, 1080, 1200))).getbbox()
    data = json.loads(a.with_suffix('.json').read_text(encoding='utf8'))
    assert data['episode'] == 1 and data['episode_label'] == '第一期'
    assert data['cover_title_lines'] == ['逃亡78天的西口彰', '却被女孩一眼认出']
    assert data['release_title'] == '西口彰：女孩认出通缉犯'
    assert data['fact_basis'] == '项目剧本'
    assert data['screenshot_source']['path'] == str(SAMPLE)
    assert data['screenshot_source']['type'] == 'image'
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


def test_screenshot_changes_only_frame_and_is_required(tmp_path):
    red, blue = tmp_path / 'red.png', tmp_path / 'blue.png'
    Image.new('RGB', (300, 200), '#e41919').save(red)
    Image.new('RGB', (300, 200), '#1943e4').save(blue)
    a, b = tmp_path / 'a.png', tmp_path / 'b.png'
    assert run(a, source=('--screenshot', str(red))).returncode == 0
    assert run(b, source=('--screenshot', str(blue))).returncode == 0
    first, second = Image.open(a), Image.open(b)
    assert first.getpixel((500, 800)) == (228, 25, 25)
    assert second.getpixel((500, 800)) == (25, 67, 228)
    assert not ImageChops.difference(first.crop((0, 0, 1080, 600)),
                                     second.crop((0, 0, 1080, 600))).getbbox()
    out = tmp_path / 'missing.png'
    result = run(out, source=())
    assert result.returncode != 0 and not out.exists()


def test_bad_screenshot_crop_and_wrong_time_fail_without_output(tmp_path):
    out = tmp_path / 'bad.png'
    result = run(out, source=('--screenshot', str(SAMPLE)), extra=('--crop', '0', '0', '99999', '800'))
    assert result.returncode != 0 and '裁剪区域越界' in result.stderr and not out.exists()
    result = run(out, source=('--screenshot', str(SAMPLE)), extra=('--time', '1'))
    assert result.returncode != 0 and '--time' in result.stderr and not out.exists()
    result = run(out, source=('--screenshot', str(tmp_path / 'missing.jpg')))
    assert result.returncode != 0 and not out.exists()


def test_extract_from_video_and_record_source(tmp_path):
    import av
    video = tmp_path / 'episode.mp4'
    # An offline synthetic video keeps this test independent of actual media in CI.
    with av.open(str(video), mode='w') as output:
        stream = output.add_stream('mpeg4', rate=2)
        stream.width, stream.height, stream.pix_fmt = 320, 180, 'yuv420p'
        for color in ['#ed1717', '#ed1717', '#1743ed', '#1743ed']:
            frame = av.VideoFrame.from_image(Image.new('RGB', (320, 180), color))
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)
    cover = tmp_path / 'video-cover.png'
    result = run(cover, source=('--video', str(video), '--time', '1', '--crop', '0', '0', '300', '170'))
    assert result.returncode == 0, result.stderr
    r, g, b = Image.open(cover).getpixel((500, 800))
    assert b > r + 100  # the frame at 1 s is blue, not the earlier red frame
    meta = json.loads(cover.with_suffix('.json').read_text(encoding='utf8'))
    assert meta['screenshot_source'] == {'type': 'video', 'path': str(video),
                                         'time_seconds': 1.0, 'crop_ltrb': [0, 0, 300, 170]}
    out = tmp_path / 'late.png'
    result = run(out, source=('--video', str(video), '--time', '99'))
    assert result.returncode != 0 and '超出视频时长' in result.stderr and not out.exists()


def test_editor_screenshot_interaction():
    import shutil
    if not shutil.which('node'):
        pytest.skip('Node.js not installed')
    result = subprocess.run([shutil.which('node'), str(ROOT / 'production/tests/mystery_cover_editor_check.js'),
                             str(TOOL_DIR / '封面模板_可编辑.html')], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'export gating passed' in result.stdout

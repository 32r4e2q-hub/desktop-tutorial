#!/usr/bin/env python3
"""Generate a series cover from an agent-written title; no network or AI calls."""
import argparse
import json
import math
from pathlib import Path
import sys

from fontTools.ttLib import TTFont
from PIL import Image, ImageOps

from build_template import FOOTER, HERE, LABEL, cover

DEFAULT_FONT = HERE / 'NotoSerifCJKsc-Common.otf'
PLATE = HERE / 'plate.jpg'


def episode_text(number):
    if not 1 <= number <= 9999:
        raise ValueError('期数必须是 1 到 9999 的整数')
    digits = '零一二三四五六七八九'
    result = ''
    zero_pending = False
    for divisor, unit in ((1000, '千'), (100, '百'), (10, '十'), (1, '')):
        digit, number = divmod(number, divisor)
        if digit:
            if zero_pending:
                result += '零'
                zero_pending = False
            if not (divisor == 10 and digit == 1 and not result):
                result += digits[digit]
            result += unit
        elif result and number:
            zero_pending = True
    return f'第{result}期'


def validate_line(value, name):
    if value != value.strip() or not value or len(value) > 18 or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(f'{name}须为 1–18 字的单行文字，首尾不能有空格')


def validate_glyphs(font_path, text):
    with TTFont(font_path, fontNumber=0, lazy=True) as font:
        cmap = font.getBestCmap() or {}
    missing = sorted({char for char in text if not char.isspace() and ord(char) not in cmap})
    if missing:
        raise ValueError('字体缺字：' + ' '.join(missing) + '；可用 --font 指定包含这些字的 OTF/TTF 字体')


def load_screenshot(image_path, video_path, time_seconds, crop):
    if image_path:
        if time_seconds is not None:
            raise ValueError('--time 只能与 --video 一起使用')
        with Image.open(image_path) as image:
            shot = ImageOps.exif_transpose(image).convert('RGB')
    else:
        if time_seconds is None or not math.isfinite(time_seconds) or time_seconds < 0:
            raise ValueError('从视频取帧时必须用 --time 指定非负秒数')
        try:
            import av
        except ImportError as exc:
            raise ValueError('视频取帧需要安装 PyAV：python3 -m pip install "av>=12,<19"') from exc
        with av.open(str(video_path)) as container:
            if not container.streams.video:
                raise ValueError('视频文件没有视频流')
            stream = container.streams.video[0]
            start = float(stream.start_time * stream.time_base) if stream.start_time is not None else 0.0
            duration = float(stream.duration * stream.time_base) if stream.duration is not None else (container.duration / av.time_base if container.duration is not None else None)
            if duration is not None and time_seconds >= duration:
                raise ValueError('取帧时间超出视频时长')
            target = start + time_seconds
            container.seek(int(target / stream.time_base), stream=stream, backward=True)
            frame = next((f for f in container.decode(stream) if f.time is not None and f.time >= target - 1e-6), None)
            if frame is None:
                raise ValueError('无法在指定时间找到视频帧')
            shot = frame.to_image().convert('RGB')
    if crop:
        left, top, right, bottom = crop
        if not (0 <= left < right <= shot.width and 0 <= top < bottom <= shot.height):
            raise ValueError(f'裁剪区域越界：图像大小为 {shot.width}×{shot.height}')
        shot = shot.crop(crop)
    if shot.width < 100 or shot.height < 50:
        raise ValueError('截图太小，请提供至少 100×50 像素的画面')
    return shot


def main(argv=None):
    parser = argparse.ArgumentParser(description='迷案解码人封面：输入期数与已经核实、由 Agent 拟好的两行标题。')
    parser.add_argument('--episode', required=True, type=int, help='期数，1–9999')
    parser.add_argument('--line1', required=True, help='封面标题第一行，1–18 字')
    parser.add_argument('--line2', required=True, help='封面标题第二行，1–18 字')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--screenshot', type=Path, help='本期视频截图图片')
    source.add_argument('--video', type=Path, help='本期视频文件；需同时指定 --time')
    parser.add_argument('--time', type=float, help='取帧时间（从视频开头起的秒数）')
    parser.add_argument('--crop', nargs=4, type=int, metavar=('LEFT','TOP','RIGHT','BOTTOM'), help='可选：视频帧或图片的像素裁剪边界')
    parser.add_argument('--output', required=True, type=Path, help='输出 PNG；同名 JSON 保存期数与标题')
    parser.add_argument('--release-title', help='发布标题；不填则以逗号连接封面两行')
    parser.add_argument('--fact-basis', default='', help='事实依据路径或来源说明，由 Agent 提供')
    parser.add_argument('--font', type=Path, default=DEFAULT_FONT, help='缺字时指定高覆盖的 OTF/TTF 字体')
    parser.add_argument('--force', action='store_true', help='允许覆盖已有的 PNG 和 JSON')
    args = parser.parse_args(argv)
    metadata = args.output.with_suffix('.json')
    try:
        period = episode_text(args.episode)
        validate_line(args.line1, '第一行')
        validate_line(args.line2, '第二行')
        if args.output.suffix.lower() != '.png':
            raise ValueError('输出文件须以 .png 结尾')
        if args.release_title is not None and not args.release_title.strip():
            raise ValueError('发布标题不能为空')
        if not args.force and (args.output.exists() or metadata.exists()):
            raise ValueError(f'输出或同名 JSON 已存在（{args.output} / {metadata}）；请换路径或明确使用 --force')
        if not args.font.is_file():
            raise ValueError(f'字体文件不存在：{args.font}')
        validate_glyphs(args.font, LABEL + period + args.line1 + args.line2 + FOOTER + '真实案件真相，藏在细节里本片画面CASE FILE / TRUE STORYMYSTERY DECODER0123456789')
        shot = load_screenshot(args.screenshot, args.video, args.time, args.crop)
        with Image.open(PLATE) as image:
            result = cover(args.font, period, args.line1, args.line2, plate_image=image, screenshot=shot, episode=args.episode)
        record = {
            'series': LABEL,
            'episode': args.episode,
            'episode_label': period,
            'cover_title_lines': [args.line1, args.line2],
            'release_title': args.release_title or f'{args.line1}，{args.line2}',
            'fact_basis': args.fact_basis,
            'screenshot_source': {
                'type': 'image' if args.screenshot else 'video',
                'path': str(args.screenshot or args.video),
                'time_seconds': args.time,
                'crop_ltrb': args.crop,
            },
            'cover_file': args.output.name,
            'size': [1080, 1440],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.save(args.output, format='PNG', optimize=True)
        metadata.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    except (ValueError, OSError) as exc:
        print(f'无法生成封面：{exc}', file=sys.stderr)
        return 1
    print(f'封面：{args.output}\n标题记录：{metadata}\n发布标题：{record["release_title"]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

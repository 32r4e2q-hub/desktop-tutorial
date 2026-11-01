#!/usr/bin/env python3
"""Generate a series cover from an agent-written title; no network or AI calls."""
import argparse
import json
from pathlib import Path
import sys

from fontTools.ttLib import TTFont
from PIL import Image

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


def main(argv=None):
    parser = argparse.ArgumentParser(description='迷案解码人封面：输入期数与已经核实、由 Agent 拟好的两行标题。')
    parser.add_argument('--episode', required=True, type=int, help='期数，1–9999')
    parser.add_argument('--line1', required=True, help='封面标题第一行，1–18 字')
    parser.add_argument('--line2', required=True, help='封面标题第二行，1–18 字')
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
        validate_glyphs(args.font, LABEL + period + args.line1 + args.line2 + FOOTER + '真实案件真相，藏在细节里CASE FILE / TRUE STORYMYSTERY DECODER')
        with Image.open(PLATE) as image:
            result = cover(args.font, period, args.line1, args.line2, plate_image=image)
        record = {
            'series': LABEL,
            'episode': args.episode,
            'episode_label': period,
            'cover_title_lines': [args.line1, args.line2],
            'release_title': args.release_title or f'{args.line1}，{args.line2}',
            'fact_basis': args.fact_basis,
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

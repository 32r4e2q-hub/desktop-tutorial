#!/usr/bin/env python3
"""Generate a series cover from an agent-written title; no network or AI calls."""
import argparse
import json
from pathlib import Path
import sys

from PIL import Image

import template
from template import DEFAULT_FONT, FOOTER, H, HERE, LABEL, W, cover


def episode_text(number):
    return template.episode_text(number)


def validate_line(value, name):
    template.validate_line(value, name)


def validate_glyphs(font_path, text):
    template.validate_glyphs(font_path, text)


def main(argv=None):
    parser = argparse.ArgumentParser(description='迷案解码人封面：输入期数与已经核实、由 Agent 拟好的两行标题。')
    parser.add_argument('--episode', required=True, type=int, help='期数，1–9999')
    parser.add_argument('--line1', required=True, help='封面标题第一行，1–18 字')
    parser.add_argument('--line2', required=True, help='封面标题第二行，1–18 字')
    parser.add_argument('--output', required=True, type=Path, help='输出 PNG；同名 JSON 保存期数与标题')
    parser.add_argument('--release-title', help='发布标题；不填则以逗号连接封面两行')
    parser.add_argument('--fact-basis', default='', help='事实依据路径或来源说明，由 Agent 提供')
    parser.add_argument('--shot', type=Path, help='窗口里的截图：本片的一帧（建议用不带字幕的时间点）')
    parser.add_argument('--shot-y-bias', type=float, default=0.5,
                        help='截图竖向取景，0 取顶部、1 取底部，默认居中')
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
        if args.shot is not None and not args.shot.is_file():
            raise ValueError(f'截图文件不存在：{args.shot}')
        if not 0.0 <= args.shot_y_bias <= 1.0:
            raise ValueError('截图取景比例须在 0 到 1 之间')
        result = cover(args.font, args.episode, args.line1, args.line2,
                       shot=args.shot, shot_y_bias=args.shot_y_bias)
        record = {
            'series': LABEL,
            'episode': args.episode,
            'episode_label': period,
            'cover_title_lines': [args.line1, args.line2],
            'release_title': args.release_title or f'{args.line1}，{args.line2}',
            'fact_basis': args.fact_basis,
            'cover_file': args.output.name,
            'cover_template': 'production/mystery-cover-template/template.py',
            'size': [W, H],
            'shot': str(args.shot) if args.shot else '',
            'shot_y_bias': args.shot_y_bias,
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

#!/usr/bin/env python3
"""第七轮（终轮）换构图：把「会长字」的布景直接删掉。

用法::  python3 production/unterweger/tools/apply_redo_r7.py

第六轮复查结论：S13 干净；S30 只剩黑形（再加取景窗）；仍然长字的是五镜——
  S05 门柱上的小牌（门柱是字源）；S23 远处楼墙上的字母；S26 警戒带上清清楚楚印着 POLIZEI（最严重）；
  S41 木墙上的小铭牌；S43 书架色带与墙上的证书框。
第七轮不再描述「没有字的墙」——**干脆不给墙**：
  · 背景只留雾、天光、或近黑（不给任何可挂东西的面）；
  · S26 把警戒带整个删掉（带子本身就是字源），靠雨夜的灯光与巡逻灯的光晕说话；
  · S41 改成只打亮脸的近黑法庭；S43 改成背景沉入黑暗的书房。
另外 S01（门楣编号）与 S30（肩章）用 render.py 的 TIGHTER_CROPS 推近裁掉，不重生。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build_story.py"

HOLD = ('no cut, no scene change, no camera relocation, no second location, no extra people, '
        'no readable text anywhere in frame; hold on this single view for the full clip.')

REDO = {
    "S05": (
        "A man in a dark coat, seen strictly from behind at a middle distance, walking away from the camera across "
        "an empty wet forecourt on a bright winter morning: his back fills the centre of the frame, face never "
        "visible, one hand carrying a plain cardboard folder with no marking; nothing stands between the camera and "
        "him but wet asphalt reflecting the pale sky, and beyond him the scene dissolves into empty morning haze - "
        "no structures, no gate, no piers, no walls, no buildings, no vehicles, no people and nothing legible of any "
        "kind anywhere in the frame. Slow tracking shot following his back, " + HOLD),
    "S23": (
        "A man in a light summer coat, seen strictly from behind at a middle distance, walking away from the camera "
        "across a dry empty road in the early sun: his back fills the centre of the frame, face never visible, one "
        "hand carrying a plain cardboard folder with no marking; beyond him there is only flat sunlit haze and a low "
        "horizon of empty pale sky - no buildings, no windows, no walls, no fences, no vehicles, no people and "
        "nothing legible of any kind anywhere in the frame; long soft shadows running toward the camera on blank "
        "pavement. Slow pull back and up as he walks away, " + HOLD),
    "S26": (
        "An empty city street at night in heavy rain, nobody and nothing else in frame: a wet road running away from "
        "the camera toward a vanishing point of darkness, one sodium street lamp high above throwing a hard cone of "
        "light into the rain, the asphalt mirror-bright with long smeared reflections, and the alternating red and "
        "blue wash of patrol lights sweeping across the road surface from a source just outside the frame; beyond "
        "the lamp everything falls into deep blue-black night with no structures and nothing legible of any kind in "
        "the darkness; no vehicles, no people, no tape, no barriers, no signs. Slow pan across the wet asphalt and "
        "the light cone, " + HOLD),
    "S41": (
        "A medium close-up in a darkened courtroom at night in June 1994: {C1} only to the chest, standing behind a "
        "plain polished wooden rail in the dock with both hands resting flat on it, looking directly toward the "
        "camera with a flat composed expression, lit only by a single hard overhead lamp while everything behind and "
        "around him falls away into near-blackness - no visible wall, no panelling, no plaques, no emblems and "
        "nothing legible anywhere; at the very bottom edge of the frame the public gallery appears only as unlit "
        "dark shapes with no identifiable faces; no other people and no objects in the foreground. Slow push in on "
        "him, " + HOLD),
    "S43": (
        "A medium close-up in a dim study in Vienna in 1994: {C3}, seated in his leather armchair with a thick closed "
        "cloth-bound book resting on his knees, one hand flat on its blank cover, his head lowered under the reading "
        "lamp, his face and hands the only lit parts of the frame; the room behind him dissolves into soft darkness "
        "where the shelves survive only as faint out-of-focus bands of muted colour with nothing on them - no titles, "
        "no lettering, no numbers, no frames, no certificates, no plaques and nothing legible of any kind; no other "
        "people. Slow push in on him, " + HOLD),
}


def main() -> int:
    text = BUILD.read_text(encoding="utf-8")
    changed = []
    for sid, prompt in REDO.items():
        start = text.index(f'("{sid}", "agnes"')
        end = text.find("\n    (", start)
        if end == -1:
            end = text.index("\n]", start)
        block = text[start:end]
        stop = block.index(" + HOLD,")
        idx = block.rindex('",\n     "', 0, stop) + len('",\n     "')
        if prompt.endswith(" + HOLD"):
            prompt = prompt[: -len(" + HOLD")]
        wrapped, line = [], ""
        for word in prompt.split(" "):
            if len(line) + len(word) + 1 > 108:
                wrapped.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        wrapped.append(line)
        new_prompt = '"\n     "'.join(wrapped) + '"'
        text = text[:start] + block[:idx] + new_prompt + block[stop:] + text[end:]
        changed.append(sid)
    BUILD.write_text(text, encoding="utf-8")
    print("第七轮已改写提示词：" + ", ".join(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())

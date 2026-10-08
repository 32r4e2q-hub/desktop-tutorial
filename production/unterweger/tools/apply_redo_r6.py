#!/usr/bin/env python3
"""第六轮复审后的换构图（第六轮 = 第五轮重做之后的放大复查）。

用法::  python3 production/unterweger/tools/apply_redo_r6.py

第五轮重做的 17 镜里，9 镜已干净（S14 S15 S20 S27 S32 S33 S36 S38 S39），7 镜仍有伪文字：
  S05 门柱上的小牌与远处车辆；S13 走廊墙上的告示牌；S23 穹顶下的门牌与车辆；
  S26 警戒带上的字；S30 制服与臂章上的 POLIZEI（红线）；S41 木墙上的铭牌；S43 书脊与墙上图表。
第六轮不再靠否定词，改用三种「不可能长字」的构图：
  ① 背景换成**弥散失焦的纯色/雾/暗部**（near-blackness / morning mist / soft dark blur）；
  ② 主体**填满画面**，把有字的墙推到画框外；
  ③ 需要道具的地方只给**空白无印刷**的物件。
S01 的伪文字在画框顶部（门楣），不重生：用 render.py 的 TIGHTER_CROPS 裁掉（手册第 7 步的第二种解法）。
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
        "visible, one hand carrying a plain cardboard folder with no marking; the background beyond him is empty "
        "morning haze and pale blank sky, and the gate structures are reduced to two plain out-of-focus stone piers "
        "at the extreme left and right edges of the frame, cut stone with nothing mounted on them and no fixtures, no "
        "plaques, no plates and no lettering; wet asphalt reflecting the pale sky in the foreground, no vehicles, no "
        "people, no windows, no signage. Slow tracking shot following his back away from the gate, " + HOLD),
    "S13": (
        "A medium close-up in a high-ceilinged courthouse corridor in 1976: {C4} seen chest-up in the centre of the "
        "frame, holding an open folder of blank pages in both hands, his gaze down toward it, cold daylight from a "
        "tall window on the right modelling one side of his face; the background behind him is a smooth out-of-focus "
        "dark wall with absolutely nothing mounted on it - no frames, no notices, no plaques, no boards, no doors - "
        "and the far end of the corridor dissolves into a soft blur of shadow with no figures; no other people, no "
        "lettering, no numbers anywhere in frame. Slow push in on him, " + HOLD),
    "S23": (
        "A man in a light summer coat, seen strictly from behind at a middle distance, walking away from the camera "
        "across an empty sunlit street: his back fills the centre of the frame, face never visible, one hand carrying "
        "a plain cardboard folder with no marking; the background is morning haze and a flat sunlit wall of plain "
        "plaster in soft focus behind him, with no windows, no doors, no numbers, no plates, no notices and no "
        "lettering on it, and no vehicles and no people anywhere; long soft shadows on dry pavement, plain blank sky "
        "above. Slow pull back and up as he walks away, " + HOLD),
    "S26": (
        "An empty city street at night in the rain: a wet road running away toward a vanishing point of darkness, one "
        "sodium street lamp high above throwing a cone of light, and in the foreground a length of plain single-colour "
        "white barrier tape strung between two bare metal posts, the tape carrying no printing, no pattern and no "
        "marking of any kind; everything beyond the lamp is a deep blue night with a blank dark wall in shadow that "
        "carries nothing on it - no notices, no posters, no graffiti, no lettering; heavy rain visible in the light "
        "cone, mirror reflections on the asphalt, no vehicles, no people. Slow pan across the tape and the wet "
        "asphalt, " + HOLD),
    "S30": (
        "A medium shot in a dark corridor at night: {C1}, walking slowly toward the camera in the centre of the "
        "frame with his hands held together in front of his waist, a dark jacket over his shoulders, his face lit "
        "only by a single overhead lamp while everything around him falls away into near-blackness; two escorts walk "
        "at his sides and appear only as unlit black shapes at the very edges of the frame, their silhouettes "
        "featureless with no uniform detail, no badges, no patches, no insignia, no numbers and no lettering catching "
        "any light at all; the wall behind him is in deep shadow with nothing legible on it; slow tracking shot ahead "
        "of him, " + HOLD),
    "S41": (
        "A medium close-up inside an Austrian courtroom in June 1994: {C1} only to the chest, standing behind a plain "
        "polished wooden rail in the dock with both hands resting flat on it, looking directly toward the camera with "
        "a flat composed expression; the background behind him is a single continuous panel of plain dark wood "
        "filling the frame in soft focus, with absolutely nothing mounted on it - no plaques, no name plates, no "
        "numbers, no handles, no crests and no emblems - and the public gallery is a dark blur at the very bottom of "
        "the frame with no identifiable faces; no other people in the foreground. Slow push in on him, " + HOLD),
    "S43": (
        "A medium close-up in a book-lined study in Vienna in 1994: {C3}, seated in his leather armchair with a thick "
        "closed cloth-bound book resting on his knees, one hand flat on the blank cover, his head lowered under the "
        "reading lamp; the shelves behind him fall far out of focus so that the books read only as soft dark bands of "
        "muted colour, with nothing legible on any spine, no titles, no lettering, no numbers and no gold tooling; the "
        "room is otherwise empty and dim, no signage, no charts, no frames on the walls; no other people. Slow push "
        "in on him, " + HOLD),
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
    print("第六轮已改写提示词：" + ", ".join(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())

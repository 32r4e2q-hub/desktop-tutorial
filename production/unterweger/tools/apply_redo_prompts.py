#!/usr/bin/env python3
"""把提示词里"会长出伪文字"的构图换成没有文字的构图（lamkorwan §5 的解法：换构图，不是加否定词）。

用法::  python3 production/unterweger/tools/apply_redo_prompts.py

只改这几个镜头的 prompt，其它字段（运镜 / 职责 / 衔接 / 音效）保持原样；
改完必须重跑 build_story.py 与 face_cast.py check-prompts，然后只重做这些镜头。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build_story.py"

HOLD = ('no cut, no scene change, no camera relocation, no second location, no extra people, '
        'no readable text anywhere in frame; hold on this single view for the full clip.')

REDO = {
    "S01": (
        "The pavement outside a plain stone prison gate on an overcast May morning in 1990: a tight cluster of press "
        "photographers seen strictly from behind and from the side, dark bulky 1980s coats and hats, held-up flash "
        "units firing, chrome and glass of their lenses catching the pale daylight, one heavy shoulder-mounted "
        "television camera on the right; the gate and the wall are bare wet stone carrying no plaque, no number, no "
        "lettering and no notice, and no camera, bag or case in frame carries any marking, label or lettering of any "
        "kind; no faces visible at all, no other people, no vehicles, no signage. Slow push into the cluster of "
        "photographers toward the gate, " + HOLD),
    "S04": (
        "A medium shot inside a 1980s television studio in Vienna: {C2}, seated facing a microphone on a stand, "
        "leaning slightly forward with a notebook open in one hand, the striped fabric of an empty guest armchair "
        "visible at the edge of frame beside her; the background is a seamless featureless dark grey studio wall, "
        "thrown far out of focus by shallow depth of field, carrying no lettering, no numbers, no marks and no "
        "objects of any kind, the blurred shoulder of a camera operator seen strictly from behind at the edge of "
        "frame with no face visible; no other people, no signage, no posters. Slow push in on her, " + HOLD),
    "S09": (
        "A narrow cobbled street between plain plastered house fronts in a small Austrian town at dusk in December "
        "1974: frost on the cobblestones and a thin crust of snow along the kerb, one bare tree, one lit curtained "
        "window on the upper floor, a single black bicycle leaning against a wall; the plaster walls are completely "
        "bare and anonymous with no house numbers, no name plates, no plaques, no signs and no lettering in any "
        "form, the camera is low and tight so that only the street level and the one lit window are in frame, no "
        "vehicles, no people, no sky. Slow push down the street toward the lit window, " + HOLD),
    "S13": (
        "A high-ceilinged Austrian courthouse corridor in 1976, entirely empty of people: tall bare windows "
        "throwing cold daylight across a worn stone floor, dark wooden benches along the wall, a heavy double door "
        "standing closed at the far end; photographed from a low angle so the walls above the bench line are bare "
        "and featureless, with no notice boards, no framed documents, no plaques, no signs, no lettering and no "
        "numbers anywhere in frame. Slow lateral drift along the corridor, " + HOLD),
    "S14": (
        "A long prison wing corridor in 1976 filmed from a low angle, empty of people: a receding row of heavy "
        "steel cell doors on the left, framed close along the wall so that nothing is legible anywhere, every door "
        "a plain unmarked slab carrying no number, no plate, no lettering and no figure on any fitting, a bare bulb "
        "and a high narrow window at the far end throwing a dusty shaft of light down the corridor, worn grey stone "
        "floor; no people, no furniture, no markings. Slow pull back down the corridor, " + HOLD),
    "S16": (
        "A medium shot inside a dim prison cell at night in 1985: {C1}, seated at a small table with his forearms "
        "resting on a stack of blank pages, a cigarette burning in a tin ashtray beside a glass of water, a bare "
        "bulb overhead modelling his face from above while the cell behind him falls into near blackness; the wall "
        "behind him is featureless bare plaster with no numerals, no marks, no plates and no writing of any kind, "
        "and the window edge in frame is plain and unmarked; no other people. Slow push in on his face, " + HOLD),
    "S22": (
        "A medium shot behind the counter of a small Viennese night bar in 1990: {C6}, leaning with both hands on "
        "the counter, a damp cloth in one hand, a towel over her shoulder, looking off toward the door with a tired "
        "level gaze; behind her only plain dark shelving holding rows of completely unmarked bottles with blank "
        "labels and a warm pendant lamp; the wall she stands against is plain dark panelling with no poster, no "
        "notice, no picture, no lettering and no numbers anywhere, no other people in frame. Slow push in on her, " + HOLD),
    "S23": (
        "A man in a light summer coat, seen strictly from behind at a long distance, walking away from a plain "
        "stone prison gate toward a waiting empty street on a bright May morning in 1990: his figure small in the "
        "frame, one hand carrying a plain cardboard folder; the gate and the wall are blank stone with no "
        "inscription, no plate, no number and no notice, photographed from a low distance so that the wall above "
        "the gate stays out of frame; no vehicles, no people, no signage. Slow pull back and up as he walks away, " + HOLD),
    "S26": (
        "An empty side street in Los Angeles at night in 1991 under light rain: wet asphalt mirroring a single "
        "sodium street light and the alternating red and blue wash of patrol lights from off-screen, a length of "
        "plain barrier tape strung between two posts, weeds cracking the kerb, a blank featureless concrete wall "
        "behind, bare from edge to edge; no graffiti, no posters, no bills, no signs, no lettering and no numbers "
        "anywhere, no vehicles, no people, no bodies. Slow pan across the tape and the wet asphalt, " + HOLD),
    "S27": (
        "A medium shot in a bright airport departure lounge in 1991: {C1}, seated in a moulded plastic chair with "
        "a plain unmarked notebook open on his knee and a small flight bag at his feet, twisting his upper body to "
        "look back over his shoulder toward the camera with a flat appraising expression; behind him only a long "
        "row of empty chairs and a floor-to-ceiling window of pale grey light, no counters, no desks, no screens, "
        "no monitors, no panels, no lettering, no numbers and no other people in frame. Slow push in on him, " + HOLD),
    "S32": (
        "A medium shot in a records room in Vienna at night in 1992: {C4}, standing at an open steel drawer with "
        "one hand lifting out a thick folder of blank pages, dust hanging in the beam of a work lamp, his overcoat "
        "still on; the drawer and the cabinet fronts are plain steel with no label holders, no plates, no numbers "
        "and no lettering of any kind, the papers in his hand are blank, the wall behind is bare grey with nothing "
        "mounted on it; no other people, no windows. Slow descent toward the drawer, " + HOLD),
    "S33": (
        "A medium shot in a Los Angeles police office at night in 1992: {C5}, seated at a heavy manual typewriter "
        "with both hands on the keys and a blank sheet in the machine, a telephone handset lying off the hook "
        "beside it, two folded paper evidence bags and a desk lamp on the table; the wall behind her is plain and "
        "empty with no framed notices, no plates, no numbers, no clock and no lettering anywhere, and the machine "
        "and every page are blank; no other people, no signage. Slow push in on her, " + HOLD),
    "S34": (
        "A medium shot in a modest hotel room at night in 1992: {C1}, seated on the edge of the bed with a "
        "telephone handset held against his ear, a small suitcase lying open on the luggage rack beside him, his "
        "jacket hung over the chair, the bedside lamp the only light source; the wallpaper, the curtains and the "
        "bed frame are plain and unpatterned with no numerals, no floral ornament, no lettering and no printed "
        "marks anywhere, no other people in frame. Slow push in on him, " + HOLD),
    "S36": (
        "A medium shot in a plain bright holding room in Florida in February 1992: {C1}, seated on a fixed steel "
        "chair leaning slightly forward with his elbows on his knees, wearing a plain grey sweatshirt, lit by hard "
        "even daylight from a high window; the walls behind him are blank painted concrete with no numerals, no "
        "markings, no notices, no plates and no lettering of any kind, there is no table in frame and no other "
        "people. Slow push in on him, " + HOLD),
    "S39": (
        "The stone steps and heavy wooden entrance doors of a plain Austrian public building at grey dawn in 1994: "
        "wet steps, iron handrails, one lamp still burning above the door, thick mist hiding the upper storeys and "
        "the neighbouring buildings; the facade is bare stone with no notice boards, no plaques, no name plates, "
        "no numbers and no lettering of any kind anywhere, no people, no vehicles, no signage. Slow push up the "
        "steps toward the doors, " + HOLD),
    "S41": (
        "A medium shot inside an Austrian courtroom in June 1994: {C1}, standing behind a plain wooden rail in the "
        "dock with his hands resting on it, wearing a dark suit and open white shirt, his expression flat and "
        "composed as he looks directly toward the camera; he is lit tightly against a plain panelled wall with no "
        "plaques, no framed documents, no crests, no emblems, no lettering and no numbers, and the courtroom "
        "beyond falls away into shadow and out of focus with nobody visible; no other people in frame. Slow push "
        "in on him, " + HOLD),
    "S42": (
        "A single bare cell in an Austrian prison at grey dawn in June 1994, empty of people: a steel table with a "
        "closed notebook, a pen laid precisely parallel to its edge, a tin mug and a folded grey blanket on the "
        "narrow bed, one high window with cold flat light and long shadows; the walls are blank smooth plaster "
        "with no numerals, no marks, no writing and no fittings, and the window in the lit part of the frame is "
        "plain; no people in frame, no other objects. Slow descent toward the table, " + HOLD),
    "S45": (
        "The end of a bare prison corridor at night in 1994, empty of people: one heavy steel cell door standing "
        "slightly open at the far end with a blade of warm light escaping across the worn stone floor, the wall "
        "lamp above it the only light; the walls and doors are blank and unmarked with no numbers, no plates, no "
        "lettering and no fixtures, the corridor photographed wide and dim; no people, no furniture. Very slow "
        "pull back down the corridor as the door settles shut, " + HOLD),
}


def main() -> int:
    text = BUILD.read_text(encoding="utf-8")
    changed = []
    for sid, prompt in REDO.items():
        start = text.index(f'("{sid}", "agnes"')
        end = text.index("\n    (", start) if "\n    (" in text[start:] else len(text)
        end = text.find("\n    (", start)
        if end == -1:
            end = text.index("\n]", start)
        block = text[start:end]
        # 提示词（第 6 个字段）从它前面最后一个 '",\n     "' 之后开始，到 ' + HOLD,' 之前结束；
        # 提示词内部的换行是 '"\n     "'（没有逗号），不会误匹配。
        stop = block.index(" + HOLD,")
        idx = block.rindex('",\n     "', 0, stop) + len('",\n     "')
        # 文件里 ' + HOLD,' 已经在插入点之后，这里把提示词末尾的 ' + HOLD' 去掉，避免重复
        if prompt.endswith(" + HOLD"):
            prompt = prompt[: -len(" + HOLD")]
        # 新提示词按 108 字符折行，保持文件可读
        wrapped, line = [], ""
        for word in prompt.split(" "):
            if len(line) + len(word) + 1 > 108:
                wrapped.append(line)
                line = word
            else:
                line = f"{line} {word}".strip()
        wrapped.append(line)
        new_prompt = '"\n     "'.join(wrapped) + '"'      # 开头那个引号在 block[:idx] 里，这里补收尾引号
        text = text[:start] + block[:idx] + new_prompt + block[stop:] + text[end:]
        changed.append(sid)
    BUILD.write_text(text, encoding="utf-8")
    print("已改写提示词：" + ", ".join(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())

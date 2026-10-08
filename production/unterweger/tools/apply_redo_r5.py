#!/usr/bin/env python3
"""第五轮复审后的换构图（把「会长出伪文字」的墙面/制服/纸页换成不可能长字的构图）。

用法::  python3 production/unterweger/tools/apply_redo_r5.py

第五轮（2026-10-08，人眼逐张放大到原始像素）判死的镜头与理由：
  S01 监狱门楣/围墙上的编号牌（179900 / 35 / 围栏编号）
  S05 大门两侧的门牌与围墙标牌
  S13 走廊墙上的指示牌与门框标牌
  S14 牢门上的编号牌
  S15 墙面 stencil 数字与刻字
  S20 讲台与水杯上的文字
  S23 空地上印的数字
  S26 墙上的告示牌（两张）+ 路灯上的标志牌 + 墙上涂鸦
  S27 候机厅墙上的牌子（1308 等）
  S30 制服上的 POLICE 字样（红线：服装不许有字母）
  S32 墙面指示牌与抽屉编号
  S33 墙上的科室牌、时钟、告示
  S36 墙上成排的门牌与插孔
  S38 墙上的挂钟与制度牌
  S39 台阶两侧的门牌与门牌号
  S41 木墙上的铭牌与编号
  S43 书页上可读的正文（改：把书合上）

同时把 S13 / S36 改成露脸镜头（{C4} / {C5}），让「人物动画多些」这个要求再多两镜，
减少纯环境空镜；cast.json 的 shots 映射同步更新。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build_story.py"

HOLD = ('no cut, no scene change, no camera relocation, no second location, no extra people, '
        'no readable text anywhere in frame; hold on this single view for the full clip.')

NO_MARKS = ("the surface is completely bare and featureless with no plates, no numbers, no notices, no labels, "
            "no fixtures and no lettering of any kind")

REDO = {
    "S01": (
        "The pavement outside a plain stone prison gate on an overcast May morning in 1990: a tight cluster of press "
        "photographers seen strictly from behind and from the side filling the lower half of the frame, dark bulky "
        "1980s coats and hats, held-up flash units firing, chrome and glass of their lenses catching the pale "
        "daylight, one heavy shoulder-mounted television camera on the right with a completely blank body carrying "
        "no brand marks, no labels and no lettering; above them the gate and the wall rise as plain undressed stone "
        "and steel with " + NO_MARKS + ", the gate bars bare; no faces visible at all, no other people, no vehicles, "
        "no signage. Slow push into the cluster of photographers, " + HOLD),
    "S05": (
        "A man in a dark coat, seen strictly from behind at a long distance, walking out through an open steel gate "
        "between plain stone piers on an overcast winter morning: his figure small in the centre of the frame, face "
        "never visible, one hand carrying a plain cardboard folder with no marking; the stone piers, the steel gate "
        "and the long boundary wall are entirely plain with " + NO_MARKS + ", wet asphalt in the foreground "
        "reflecting the pale sky, an empty paved forecourt beyond; no vehicles, no people, no signage, no guard "
        "booth lettering. Slow tracking shot following his back away from the gate, " + HOLD),
    "S13": (
        "A high-ceilinged Austrian courthouse corridor in 1976: {C4}, standing in the middle distance with an open "
        "folder held in both hands, his gaze down toward the pages, three paces from the camera and lit by cold "
        "daylight from tall windows on the right; far down the corridor two figures are seen strictly from behind, a "
        "uniformed usher beside the closed double doors and a man in a plain dark suit walking away from the camera, "
        "their faces never visible, their clothing completely blank with no badges, no insignia, no lettering and no "
        "numbers; the stone walls, window reveals, benches and door frames are " + NO_MARKS + "; no other people, no "
        "vehicles. Slow lateral drift along the corridor, " + HOLD),
    "S14": (
        "A long prison wing corridor at night filmed from a low angle: a receding row of heavy steel cell doors on "
        "the left, every door closed and completely blank and unmarked with no numbers, no plates, no keyholes with "
        "lettering and no fixtures of any kind on them, a bare bulb and a high narrow window at the far end throwing "
        "a dusty shaft of light down the corridor, and one prison officer standing with his back to the camera at the "
        "far end, face never visible, his uniform completely plain with no badges, no insignia, no patches and no "
        "lettering; worn grey stone floor with no markings of any kind, bare walls with no signs, no notices and no "
        "plates; no other people, no furniture. Slow pull back down the corridor, " + HOLD),
    "S15": (
        "A single bare prison cell seen from the doorway on a grey afternoon, empty of people: a small steel table "
        "pushed against the far wall with a battered manual typewriter, a stack of blank pages, two pencils, a tin "
        "mug and an ashtray, a narrow iron bed with a folded grey blanket behind it, one high barred window with flat "
        "daylight; the plaster walls, the floor and the door frame are entirely blank and freshly painted with " + NO_MARKS +
        " and no stencilled figures, no scratched marks, no posters and no photographs anywhere; no people in frame. "
        "Slow push in toward the table, " + HOLD),
    "S20": (
        "A medium shot in a small theatre hall at night in 1989: {C1} to the chest, seated on a plain wooden chair at "
        "the centre of a bare stage with both hands resting on his knees, a closed unmarked book on a small stand "
        "beside him, warm stage light from directly above modelling his face while the hall falls away into darkness "
        "behind him; the back wall of the stage is a seamless dark curtain and the floorboards are bare, " + NO_MARKS + ", "
        "there is no lectern, no microphone, no banner and no stand signage; the first rows of the audience are "
        "visible only as dark blurred shapes at the very bottom of the frame, no identifiable faces, no other people "
        "in the foreground. Slow push in on him, " + HOLD),
    "S23": (
        "A man in a light summer coat, seen strictly from behind at a middle distance, walking away from a plain "
        "stone gatehouse toward a waiting empty street on a bright May morning in 1990: his figure centred, face "
        "never visible, one hand carrying a plain cardboard folder with no marking; the gatehouse, the wall and the "
        "pavement are " + NO_MARKS + " and the ground carries no painted figures, no lane markings and no writing; "
        "no vehicles, no people, no signage, no house numbers on the plain facades beyond. Slow pull back and up as "
        "he walks away, " + HOLD),
    "S26": (
        "An empty side street in Los Angeles at night in 1991 under light rain: wet asphalt mirroring a single "
        "sodium street light and the alternating red and blue wash of patrol lights from off-screen, a length of "
        "plain barrier tape strung between two bare posts, weeds cracking the kerb, and a long blank concrete wall "
        "filling the right of the frame with " + NO_MARKS + " and no graffiti, no posters, no notices and no painted "
        "signs on it, the street lamp itself a plain unadorned pole with nothing attached to it; no lettering, no "
        "numbers, no vehicles, no people, no bodies. Slow pan across the tape and the wet asphalt, " + HOLD),
    "S27": (
        "A medium shot in an airport departure hall in 1991: {C1}, seated in a moulded plastic chair with a plain "
        "unmarked notebook closed on his knee and a small flight bag at his feet, twisting his upper body to look "
        "back over his shoulder toward the camera with a flat appraising expression; behind him only a long row of "
        "empty chairs against a seamless floor-to-ceiling window of pale grey light, the glass carrying no "
        "lettering, no numbers and no reflections of any signage, the wall panels bare with " + NO_MARKS + "; no "
        "other people in frame, no screens, no boards, no luggage trolleys. Slow push in on him, " + HOLD),
    "S30": (
        "A medium shot in a plain corridor in 1992: {C1}, walking toward the camera with his hands held together in "
        "front of his waist, a dark jacket over his shoulders, his expression level and composed; two uniformed "
        "officers flank him and are visible only from behind as dark blurred silhouettes at the edge of frame, their "
        "uniforms completely plain and anonymous with no badges, no patches, no epaulettes, no insignia, no numbers "
        "and no lettering whatsoever; the corridor walls are bare painted plaster with " + NO_MARKS + "; slow tracking "
        "shot ahead of him, " + HOLD),
    "S32": (
        "A medium shot in a records room in Vienna at night in 1992: {C4}, standing at an open steel drawer of a card "
        "cabinet with one hand lifting out a thick folder of blank pages, dust hanging in the beam of a work lamp on "
        "the desk beside him; every card, tab and file in the cabinet is entirely blank with no writing, no numbers "
        "and no labels, the cabinet and the desk are plain with no plates and no markings, and the wall behind him is "
        "bare painted plaster with " + NO_MARKS + "; no other people, no windows, no clocks. Slow descent toward the "
        "drawer, " + HOLD),
    "S33": (
        "A medium shot in a police office at night in 1992: {C5}, seated at a heavy manual typewriter with both hands "
        "on the keys, a telephone handset lying off the hook beside it, two folded paper evidence bags and a desk "
        "lamp on the desk; the typewriter body and the papers are entirely blank with no lettering, no numbers and no "
        "printed text, the papers are all blank, and the wall behind her is bare and plain with " + NO_MARKS + " and "
        "no clocks, no charts and no posters; only her face and hands are lit while the room behind falls into "
        "darkness; no other people. Slow push in on her, " + HOLD),
    "S36": (
        "A medium shot in a plain holding room in Florida in February 1992: {C5}, seated on a fixed steel chair with "
        "a folded blank folder in her lap and her forearms resting on her thighs, lit by hard even daylight from a "
        "high window; the wall behind her is bare painted blockwork, " + NO_MARKS + " and no sockets, no panels, no "
        "number plates and no door frames visible, there is no table in frame and no other people. Slow push in on "
        "her, " + HOLD),
    "S38": (
        "A medium shot in a night newsroom in Vienna in 1992: {C2}, seated at a cluttered desk with a black telephone "
        "handset pressed to her ear and a pen in her other hand, the sleeves of her blouse pushed up, a bare desk "
        "lamp beside her and a dark window behind; the papers on the desk are all blank with no writing, no numbers, "
        "no printed text and no letterheads, the screen on the desk is switched off and dark, and the wall behind is "
        "bare painted plaster with " + NO_MARKS + " and no clocks, no notice boards and no posters; no other people "
        "in frame. Slow push in on her, " + HOLD),
    "S39": (
        "The stone stairway and heavy wooden entrance doors of a plain Austrian public building at grey dawn in 1994: "
        "wet steps, iron handrails, one bare lamp burning above the door, thick mist beyond the rooflines on either "
        "side, and a loose row of press photographers standing on the lower steps seen strictly from behind with "
        "cameras lowered at their sides; the stone, the doors and the steps are " + NO_MARKS + " and carry no "
        "inscription, no plaques, no numbers and no name plates, no faces visible, no vehicles. Slow push up the "
        "steps past their backs toward the doors, " + HOLD),
    "S41": (
        "A medium shot inside an Austrian courtroom in June 1994: {C1} only to the chest, standing behind a plain "
        "polished wooden rail in the dock with both hands resting flat on it, looking directly toward the camera with "
        "a flat composed expression; the panelled wall behind him is bare and unbroken with " + NO_MARKS + " and no "
        "plaques, no crests, no emblems and no numbers, the rows of the public gallery are visible only as dark "
        "blurred shapes far behind, no identifiable faces, no other people in the foreground. Slow push in on him, " + HOLD),
    "S43": (
        "A medium shot in a book-lined publishing office in Vienna in 1994: {C3}, seated in his leather armchair with "
        "a thick cloth-bound book closed on his knees and one hand resting flat on the cover, his head lowered, the "
        "reading lamp still burning behind him; the spines on the shelves behind him are entirely blank and unlettered "
        "with no titles, no names, no numbers and no gold tooling of any kind, and the wall behind is plain with " + NO_MARKS + "; "
        "the room is otherwise empty, no windows in frame, no signage. Slow push in on him, " + HOLD),
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
    print("第五轮已改写提示词：" + ", ".join(changed))
    return 0


if __name__ == "__main__":
    sys.exit(main())

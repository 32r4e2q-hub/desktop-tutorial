#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把用户上传的《金大斗案》脚本（30 镜 × 6 秒）转成 story.json 与 cast.json。

设计原则（照搬 金大斗案模板，但把“严格提示词”做成可检查的产物）：

1. **上传的脚本是内容唯一来源**：每一镜的原始中文旁白、英文提示词、运镜、音效
   都从 `source-script.txt` 解析出来，保存为 `source_narration` / `source_prompt`，
   改稿不手改 story.json。
2. **成片严格 180 秒**：原稿 30 × 6 秒 = 180 秒，但原旁白共 1438 字，按中文口播
   4.5–5.5 字/秒需要 260–320 秒，和 180 秒物理矛盾（JMS 模板也遇到过，最后成片
   变成了 4–5 分钟）。本片走“抖音 180 秒版”：把每镜旁白压到 16–30 字，30 镜共
   约 660 字，按 3.7–4.5 字/秒正好每镜 4.5–5.8 秒；完整原稿仍留在
   `source_narration` 与 `source-script.txt`，不丢信息。
3. **提示词是生产稿，不是原稿的复制品**：原稿有些镜头一镜里塞了多个场景
   （日历 + 乡村 + 案卷、乡村 + 城市 + 车站），Agnes 6 秒做不出来。这里把每一镜
   收敛成“一个场景 + 一个连续运镜 + 一个动作”，并统一追加：
   - 1975 年韩国年代细节（无现代设备）
   - 人物面容 token（同一人物跨镜头逐字节一致）
   - 红线（无血、无遗体、无性侵、无可读文字、无真实人物肖像）
   原始英文提示词逐镜保存在 `source_prompt`，方便对照“改了哪些、为什么改”。
4. **不虚构真实对白**：所有 prompt 里不写台词，只有环境、动作、光影。

用法：
    python3 production/kimdaedoo/build_story.py production/kimdaedoo/source-script.txt
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source-script.txt"
STORY = HERE / "story.json"
CAST = HERE / "cast.json"

# 全片统一画风。Agnes 2.5-flash 只收文本提示词；负面词不能作为独立字段传，
# 只能压进正文（见 production/kimdaedoo/model_policy.py 的 PROMPT_GUARDRAILS）。
STYLE_PREFIX = (
    "Cinematic realistic 3D animation, 1975 South Korea, true-crime documentary reconstruction, "
    "physically based rendering, natural skin texture and fabric weave, muted cold gray-green palette, "
    "soft 35mm film grain, overcast or practical period lighting, shallow depth of field, "
    "16:9 widescreen composition, "
)

# 同一人物跨镜头逐字节复用的“面容 token”。脸型/眉眼/鼻口/发型/年龄/服装各写一句，
# 只描述一个虚构重建形象，不对应任何真实人物的照片。
FACE_C1 = (
    "a lean 26-year-old Korean man with a gaunt angular face, sunken cheeks, narrow tired eyes, "
    "thin lips, short black side-parted hair, a small scar through his left eyebrow, wearing a worn "
    "dark-brown jacket over a faded white shirt and dark trousers"
)
FACE_C2 = (
    "a 50-year-old Korean woman with a round weathered face, deep laugh lines, short tightly permed "
    "grey-black hair, thin arched eyebrows, wearing a faded floral apron over a grey work dress"
)
# 侦探是配角，不做跨镜头锁脸；只用固定服装描述，避免和主角抢脸。
DETECTIVE = (
    "a 35-year-old Korean detective wearing a rumpled brown 1970s suit, a dark tie and a felt fedora"
)

CHARACTERS = [
    {
        "id": "C1",
        "name": "金大斗（虚构重建形象，非真实肖像）",
        "role": "suspect",
        "seed": 19750813,
        "face": FACE_C1,
    },
    {
        "id": "C2",
        "name": "洗衣店老板娘（普通市民）",
        "role": "witness",
        "seed": 19751008,
        "face": FACE_C2,
    },
]

# ---------------------------------------------------------------------------
# 30 镜生产稿。
#   narration = 180 秒版旁白（16–30 字，按 3.7–4.5 字/秒落在 6 秒镜头内）
#   prompt    = 生产提示词（不含 style prefix / 红线，二者由 generate.py 统一追加）
#   cast      = 需要在画面里露脸、且必须逐字节复用 face token 的角色
# 原稿的运镜/音效从 source-script.txt 逐镜解析，不在这里重复。
# ---------------------------------------------------------------------------
ROWS = [
    # 第一幕：55 天，17 条生命
    dict(
        narration="1975年，首尔雨夜。洗衣店柜台上，一条牛仔裤膝盖处有块暗红。",
        prompt=(
            "Night, heavy rain sliding down the window of a small 1975 Korean laundry shop. A pair of worn "
            "blue denim jeans lies on the wooden counter, a faint dark reddish smudge near one knee. "
            "{{C2}} stands behind the counter, drying her hands, looking down at the jeans with quiet "
            "suspicion. A single bare bulb, stacks of folded clothes, blank paper slips, deep shadows. "
            "Slow cinematic push-in from the rain-streaked window to the jeans, then to her eyes."
        ),
        cast=["C2"],
    ),
    dict(
        narration="天亮前的乡下，稻田和土路，几户人家散得很开，四面没有邻居。",
        prompt=(
            "Wide aerial view of rural South Korea in 1975 at dawn: isolated tile-roof farmhouses among "
            "brown rice fields, narrow dirt roads, distant blue hills, one 1970s Korean bus moving along a road, "
            "thin mist. Slow crane descent toward a single remote house, no people, no modern buildings, "
            "muted earthy colors."
        ),
        cast=[],
    ),
    dict(
        narration="8月13日清晨，全罗南道。这扇木门半掩着，院子里没有人。",
        prompt=(
            "Dawn exterior of a modest 1975 Korean rural home: weathered wooden gate half open, packed-earth "
            "yard, worn stone step, a faded door curtain moving in the wind, an empty wooden bench. No people, "
            "no blood. Slow push-in toward the dark doorway, cold blue-gray light, quiet and ominous."
        ),
        cast=[],
    ),
    dict(
        narration="赶来的警探蹲在门口做记录，只当它是一起孤立的入室案。",
        prompt=(
            "Overcast morning outside the same rural house. " + DETECTIVE + " crouches by the wooden doorway, "
            "writing in a small notebook; a period camera and blank paper evidence tags rest on the ground. "
            "Another investigator in a dark coat examines the yard in the background. No bodies, no blood. "
            "Slow lateral tracking from the notebook to the open door, realistic 1975 Korean police procedure."
        ),
        cast=[],
    ),
    dict(
        narration="可没过多久，附近村子接连出事，人们开始压低声音说话。",
        prompt=(
            "Dusk in a small 1975 South Korean village: a narrow dirt lane, low tile-roof houses, a family-run "
            "shop with a bare wooden shutter, no signboards, no banners, no posters, no paper notices; a few "
            "residents in period clothing speak in low voices outside, faces kept in soft shadow. Slow dolly "
            "forward, cold gray light, growing unease."
        ),
        cast=[],
    ),
    # 第二幕：跨地区，调查失去方向
    dict(
        narration="逃亡路上，他在火车上遇到一个旧识，两人就搭上了话。",
        prompt=(
            "Interior of a crowded 1975 South Korean passenger train, late afternoon. {{C1}} sits by the "
            "vibrating window, a worn cloth bundle on his lap, eyes fixed outside; a second man in a patched "
            "coat sits across the aisle, seen from behind. Wooden luggage racks, cigarette haze, muted "
            "daylight. The camera makes a slow tracking move down the aisle and stops on the suspect's guarded face, "
            "subtle tension, no dialogue."
        ),
        cast=["C1"],
    ),
    dict(
        narration="下车后两人分开，一个往村里走，一个沿铁路继续往北。",
        prompt=(
            "High-angle view of a cinder path beside a railway line in 1975 South Korea, just after a train has "
            "passed; two men in worn coats walk away from each other along the path, one toward a distant cluster "
            "of low houses, the other toward a bare wooden fence. Steam drifts over the rails, dry grass and "
            "gravel, no buildings with signs, no lettering anywhere. Slow crane rise until only the lean man in "
            "the dark-brown jacket remains in frame, seen from behind."
        ),
        cast=[],
    ),
    dict(
        narration="首尔也出了事。警车停在巷口，老人扫着门前一层落叶。",
        prompt=(
            "Late afternoon in a 1975 Seoul residential neighborhood: narrow unpaved alley, low brick-and-wood "
            "houses, laundry hanging under eaves, a child's bicycle against a wall, a distant period police jeep at "
            "the alley mouth, an old woman sweeping. Gray autumn light, slow street-level tracking toward a "
            "closed wooden gate, quiet dread, no modern technology."
        ),
        cast=[],
    ),
    dict(
        narration="各地的案卷堆在档案柜里，两个警探对着卷宗皱着眉。",
        prompt=(
            "Interior of a 1975 South Korean police office at night: tall wooden filing cabinets, stacks of "
            "closed paper case folders on desks, black rotary telephones, green desk lamps. " + DETECTIVE +
            " stands with a colleague, the two of them comparing open files held at an angle, faces lit from below. Slow lateral "
            "camera move past the cabinets, no readable text, cigarette smoke, warm pools of light in a dark room."
        ),
        cast=[],
    ),
    dict(
        narration="他闯进去的，都是这样的人家：老人、孩子，还有一桌热饭。",
        prompt=(
            "Warm late afternoon in a modest 1975 Korean family home: an elderly woman in a grey hanbok-style "
            "jacket, seen from behind, ladles soup at a low table; children's schoolbooks and a pencil case on "
            "a bench, worn shoes by the door, honey-colored sunlight through paper windows. Slow pull-back "
            "from the table to the quiet room, ordinary domestic life, no faces, no foreshadowing."
        ),
        cast=[],
    ),
    # 第三幕：55 天的犯罪浪潮
    dict(
        narration="短短55天，9起案件，17人死亡，还有3人重伤。",
        prompt=(
            "Extreme close-up of a thick 1975 Korean desk calendar seen from the side on a wooden police desk, "
            "loose pages lifting in a draft, dates out of focus, a stack of closed case folders beside it, an ink "
            "stamp and a fountain pen, cold autumn light from a window. Slow lateral slide across the page edges, "
            "shallow depth of field, the sense of days slipping away."
        ),
        cast=[],
    ),
    dict(
        narration="门锁老旧，窗户一捅就破，这样的屋子他进了不止一次。",
        prompt=(
            "Interior of a ransacked 1975 Korean rural home after a burglary: an open wooden storage chest, a "
            "few coins and a folded banknote on the floor, an overturned stool, a torn paper window with no "
            "lettering, an empty doorway, investigators' long shadows at the threshold. Bare plaster walls with "
            "no wall hangings, no posters, no calligraphy, no framed pictures. No bodies, no blood, no victims. "
            "Slow pan from the chest to the door, cold gray light, silence."
        ),
        cast=[],
    ),
    dict(
        narration="屋里剩下一只小书包，和一件叠好的开衫，再没人来拿。",
        prompt=(
            "Quiet, respectful view of a 1975 Korean rural home after a violent crime: a small child's canvas "
            "schoolbag beside an empty wooden chair, a grandmother's folded cardigan on the seat, pale winter "
            "light through paper windows, a detective's gloved hand entering frame to lift a blank evidence tag. "
            "No bodies, no blood, no faces. Slow push-in on the schoolbag, mournful stillness."
        ),
        cast=[],
    ),
    dict(
        narration="警探把案发地点一个个标在地图上，问：会是同一个人吗？",
        prompt=(
            "Overhead shot of a 1975 South Korean police investigation room: a large paper map of southern Korea "
            "and Seoul on a wooden table, several case folders spread open, loose papers held at an angle, a black rotary "
            "phone. " + DETECTIVE + " leans over the map, pencil in hand, moving between marked locations; "
            "another detective holds a file. No readable text, warm lamp light, slow top-down drift, the tension "
            "of a pattern emerging."
        ),
        cast=[],
    ),
    dict(
        narration="10月，他走进首尔一条窄巷，在一家洗衣店门口停下。",
        prompt=(
            "Autumn 1975, Seoul. " + DETECTIVE + " walks along a narrow alley of low tile-roof houses with plain "
            "plaster walls, closed wooden doors and bare brick gateposts, fallen leaves underfoot, hands in "
            "pockets. The camera follows from behind at shoulder height; he slows and stops in front of a small "
            "laundry with a bare wooden shutter and a few shirts hanging under the eaves, no signboards, no glass "
            "storefronts, no air-conditioning units. Overcast light, distant traffic, slow cinematic tracking."
        ),
        cast=[],
    ),
    # 第四幕：一条牛仔裤改变调查方向
    dict(
        narration="10月8日，一条沾着暗红印子的牛仔裤，被送进了这家店。",
        prompt=(
            "Interior of a small 1975 Seoul laundry shop near Cheongnyangni Station: steam, hanging shirts, an "
            "old drum washing machine. {{C2}} stands at the wooden counter, holding up a pair of blue jeans to "
            "the window light, her thumb rubbing a dark reddish smudge near the knee, her expression shifting "
            "from confusion to alarm. Warm bulb light, slow push-in from the jeans to her face, no gore."
        ),
        cast=["C2"],
    ),
    dict(
        narration="老板娘越看越不对，把裤子叠好包起来，拿起电话报了警。",
        prompt=(
            "Same 1975 Seoul laundry shop, closer: {{C2}} presses a black rotary telephone to her ear, the "
            "stained jeans folded in plain paper on the counter, her free hand flat on the paper, eyes toward "
            "the street door. Warm lamp light, steam in the background, slow focus pull from the rotary dial "
            "to her tense face, no readable text, quiet urgency."
        ),
        cast=["C2"],
    ),
    dict(
        narration="便衣守在巷子对面，从清晨等到下午，等送衣的人回来。",
        prompt=(
            "Alley outside the laundry, autumn afternoon 1975. " + DETECTIVE + " waits with a second plainclothes "
            "detective under the eave of a closed wooden shopfront, collars turned up, watching the laundry door "
            "across the alley; plain plaster walls, no signboards, no posters, no glass shopfronts, no "
            "air-conditioning units; passersby in period clothing, an old bicycle, fallen leaves. No tactical "
            "poses, no weapons. Slow lateral camera move behind them, muted gray light, patient tension."
        ),
        cast=[],
    ),
    dict(
        narration="下午他拿着取衣单进门，还没开口就被按住，没有反抗。",
        prompt=(
            "Late afternoon inside the 1975 Seoul laundry shop: {{C1}} steps through the door, a blank paper "
            "claim ticket in his hand, worn dark-brown jacket damp at the shoulders; two plainclothes detectives "
            "close in calmly from either side, the shopkeeper frozen behind a plain wooden counter, blank frosted "
            "glass panels behind them with no lettering or gold characters. No weapons, no struggle. "
            "The camera follows his feet, then tilts up to his face as he realizes, warm dim light, restrained "
            "cinematic tension."
        ),
        cast=["C1"],
    ),
    dict(
        narration="他先说那是打架蹭上的血，可这句话很快就站不住脚。",
        prompt=(
            "1975 South Korean police interview room at night: {{C1}} sits at a scarred wooden table, hands "
            "folded, a paper evidence bag with the blue jeans sealed on the table between him and " + DETECTIVE +
            ", who is seen from behind, shoulders only. A single overhead lamp, cigarette smoke, a stack of blank forms turned face down. Slow push-in on the suspect's tired, guarded face, no violence, no intimidation theatrics."
        ),
        cast=["C1"],
    ),
    # 第五幕：口供、审判与结局
    dict(
        narration="审讯越问越深，他一桩一桩交代，前后整整跨了55天。",
        prompt=(
            "Overhead view of a 1975 Korean police desk: several paper case files laid side by side, a hand-drawn "
            "map of South Jeolla, Gyeonggi and Seoul, a pencil moving from one location to the next, a black "
            "rotary phone at the edge, a detective's hand smoothing a folded report. Warm desk lamp, slow top-down "
            "drift, no readable text, the shape of a series emerging."
        ),
        cast=[],
    ),
    dict(
        narration="报纸开始登这件事，人们围在报摊前，沉默地看完标题。",
        prompt=(
            "1975 Seoul, a wide sidewalk at midday: low-rise Korean brick buildings and a tiled roof behind, a "
            "wooden newsstand stacked with papers folded face-down so no print is visible, a Korean seller in a "
            "flat cap arranging them, Korean commuters in 1970s Korean coats and hats walking past. The image has "
            "the grain and contrast of 1970s black-and-white press photography but is rendered in realistic 3D. "
            "No readable headlines, no shop signs, cold daylight, slow push-in past the seller's shoulder."
        ),
        cast=[],
    ),
    dict(
        narration="他说是出狱后活不下去。可活不下去，不是杀人的理由。",
        prompt=(
            "1975 Korean police holding room, late night: {{C1}} sits alone on a wooden bench, elbows on knees, "
            "worn dark-brown jacket open, his face tired and guarded, neutral gray-green walls, a bare bulb, a tin "
            "cup and a blank form on the table. No dramatic villain lighting, no imagined dialogue. Slow push-in "
            "to a medium portrait, restrained and human, uncomfortable silence."
        ),
        cast=["C1"],
    ),
    dict(
        narration="1976年3月，二审维持死刑。他放弃上诉，判决就此确定。",
        prompt=(
            "1976 South Korean courtroom: judges in dark robes seated at an elevated wooden bench, a defendant "
            "in a plain dark suit standing with his back to camera, lawyers and court staff in period clothing, "
            "tall windows with gray winter light, no readable text, no cameras. Solemn stillness, slow push-in "
            "from the back of the room toward the bench, no exaggerated reactions."
        ),
        cast=[],
    ),
    dict(
        narration="同年12月28日，金大斗被执行死刑，年仅27岁。",
        prompt=(
            "A 1976 South Korean prison corridor at dawn: heavy iron doors on both sides, pale winter light "
            "falling through high barred windows, a guard's footsteps receding, an empty chair and a folded "
            "blanket at the far end. No execution shown, no prisoner close-up, muted gray palette. Slow pull-back "
            "until the closed iron gate fills the frame, respectful and somber."
        ),
        cast=[],
    ),
    # 第六幕：真正应该留下的记忆
    dict(
        narration="可对这个家来说，判决不是结束，那把空着的椅子一直都在。",
        prompt=(
            "Quiet 1975 Korean family dining room in winter: an empty wooden chair at a low table, untouched bowls "
            "and chopsticks, a faded family photograph face-down on a shelf, a child's sock on the floor, soft gray "
            "daylight through paper windows, dust in the air. Slow dolly from the bowls to the empty chair, no "
            "people, respectful memorial atmosphere."
        ),
        cast=[],
    ),
    dict(
        narration="案卷会归档，物证会装箱，那条裤子还封在证物袋里。",
        prompt=(
            "Cinematic still life on a 1975 Korean police desk: a pair of blue jeans sealed in a plain brown "
            "paper evidence bag with a blank label, a black rotary telephone, a hand-drawn map folded so no "
            "marking shows, a stack of closed case files with blank covers, a capped fountain pen, warm desk lamp "
            "against a dark room. Every paper surface is blank or folded face-down, no handwriting, no printed "
            "labels, no lettering anywhere. Slow pull-back to reveal the full investigation table, no gore, the "
            "quiet weight of evidence."
        ),
        cast=[],
    ),
    dict(
        narration="真正让案子转向的，不是神探，是一个普通人打的电话。",
        prompt=(
            "View through the window of a moving 1975 Korean train: rural rice fields and low hills slide past, "
            "then fade into the reflection of a dense Seoul street with low buildings and pedestrians. The "
            "transition happens inside the glass reflection in one continuous shot, no cut, muted autumn colors, "
            "slow push-in on the glass, realistic period detail, no modern buildings."
        ),
        cast=[],
    ),
    dict(
        narration="这样的清晨本该一直继续下去，报案早一点，就够了。",
        prompt=(
            "Morning in a 1975 Seoul neighborhood: an elderly woman waters a small vegetable garden, two children "
            "in school uniforms walk away down the lane, seen from behind, a shopkeeper opens wooden shutters, "
            "laundry moves in the breeze, warm pale sunlight. Slow dolly down the lane, ordinary peaceful life, "
            "no identifiable faces, no text, gentle hope."
        ),
        cast=[],
    ),
    dict(
        narration="请记住那17个人。他们被害之前，也都有自己的明天。",
        prompt=(
            "Dawn after rain in 1975 Seoul: an empty alley of low tile-roof houses and shut wooden shopfronts, "
            "plain plaster and brick walls with no signs or banners, an old woman in a grey work dress pulls down "
            "a bare wooden shutter at the end of the lane, mist lifting over the cobblestones, a single bicycle "
            "leans against the wall, pale amber light. Slow pull-back until the alley becomes small, fade to "
            "black, restrained and somber."
        ),
        cast=[],
    ),
]

CHAPTERS = [
    ("N01", "55天，17条生命", 0, 30, ["S01", "S02", "S03", "S04", "S05"]),
    ("N02", "犯罪跨越地区，调查失去方向", 30, 30, ["S06", "S07", "S08", "S09", "S10"]),
    ("N03", "55天的犯罪浪潮", 60, 30, ["S11", "S12", "S13", "S14", "S15"]),
    ("N04", "一条牛仔裤改变方向", 90, 30, ["S16", "S17", "S18", "S19", "S20"]),
    ("N05", "口供、审判与结局", 120, 30, ["S21", "S22", "S23", "S24", "S25"]),
    ("N06", "真正应该留下的记忆", 150, 30, ["S26", "S27", "S28", "S29", "S30"]),
]

PRINCIPLES = [
    "不虚构真实对白：画面里不写台词，只呈现环境、动作、光影与物件",
    "不展示血腥与遗体：受害者不出现在暴力画面里，只用空椅、书包、衣物与调查现场暗示",
    "不做真实人物肖像还原：金大斗只是虚构重建形象，用固定面容 token 保持跨镜头一致，不冒充真人照片",
    "不美化犯罪：不展示作案过程、不展示武器使用、不把贫困或前科写成犯罪的必然原因",
    "文字一律后期添加：画面本身不出现可读文字、标语、水印或字幕",
]


def field(block: str, label: str) -> str:
    pattern = re.compile(r"\*\*" + re.escape(label) + r"[：:]\*\*\s*(.+?)(?=\n\*\*|\Z)", re.S)
    match = pattern.search(block)
    return " ".join(match.group(1).split()) if match else ""


def parse_source(text: str) -> dict[str, dict]:
    marks = list(re.finditer(r"^### 镜头(\d+)｜(?P<start>\d{2}:\d{2})—(?P<end>\d{2}:\d{2})", text, re.M))
    if len(marks) != 30:
        raise SystemExit(f"source-script.txt 里找到 {len(marks)} 个镜头，不是 30 个")
    parsed: dict[str, dict] = {}
    for index, mark in enumerate(marks):
        end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
        block = text[mark.end():end]
        num = int(mark.group(1))
        narration_match = re.search(r"\*\*中文旁白：\*\*\s*“(.+?)”", block, re.S)
        prompt_match = re.search(r"\*\*英文画面提示词：\*\*\s*`(.+?)`", block, re.S)
        if not narration_match or not prompt_match:
            raise SystemExit(f"镜头 {num:02d} 缺中文旁白或英文画面提示词")
        parsed[f"S{num:02d}"] = {
            "num": num,
            "narration": " ".join(narration_match.group(1).split()),
            "prompt": " ".join(prompt_match.group(1).split()),
            "camera": field(block, "运镜"),
            "sfx": field(block, "音效"),
            "start": mark.group("start"),
            "end": mark.group("end"),
        }
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("script", nargs="?", default=str(SOURCE))
    parser.add_argument("--out", default=str(STORY))
    args = parser.parse_args()

    text = Path(args.script).read_text(encoding="utf-8")
    source = parse_source(text)
    if len(ROWS) != 30:
        raise SystemExit(f"ROWS 有 {len(ROWS)} 行，不是 30")

    shots = []
    for index, row in enumerate(ROWS, start=1):
        sid = f"S{index:02d}"
        src = source[sid]
        prompt = row["prompt"].replace("{{C1}}", FACE_C1).replace("{{C2}}", FACE_C2)
        # 侦探不是 face token，可以正常大写；主角/老板娘 token 必须逐字节保留，不能动。
        prompt = prompt.replace(". a 35-year-old Korean detective", ". A 35-year-old Korean detective")
        if "{{" in prompt:
            raise SystemExit(f"{sid} 还有没替换的人物占位符")
        shots.append({
            "id": sid,
            "kind": "agnes",
            "start": (index - 1) * 6,
            "duration": 6,
            "narration": row["narration"],
            "source_narration": src["narration"],
            "prompt": prompt,
            "source_prompt": src["prompt"],
            "purpose": src["camera"],
            "camera": src["camera"],
            "sfx_note": src["sfx"],
            "seed": 19751008 + index,
            "seconds": 6,
            "aspect": "16:9",
            "resolution": "720p",
            "frame_rate": 24,
            "cast": row["cast"],
        })

    chapters = []
    by_id = {shot["id"]: shot for shot in shots}
    for cid, title, start, duration, ids in CHAPTERS:
        chapters.append({
            "id": cid,
            "title": title,
            "start": start,
            "duration": duration,
            "text": "".join(by_id[sid]["narration"] for sid in ids),
            "shots": ids,
        })

    story = {
        "title": "金大斗案｜55天，17条人命，一条牛仔裤揭开真相",
        "target_duration": 180,
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "model": "agnes-video-2.5-flash",
        "style_prefix": STYLE_PREFIX,
        "principles": PRINCIPLES,
        "chapters": chapters,
        "shots": shots,
        "source_script": Path(args.script).name,
        "narration_mode": "180s_condensed",
        "narration_note": (
            "原稿 1438 字，按 180 秒 × 4.5–5.5 字/秒只能容纳约 810–990 字；本片采用 180 秒抖音版，"
            "每镜旁白压到 16–30 字，共约 660 字，完整原稿逐镜保存在 source_narration。"
        ),
    }
    Path(args.out).write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    cast = {
        "mode": "face",
        "characters": CHARACTERS,
        "shots": {shot["id"]: shot["cast"] for shot in shots if shot["cast"]},
        "notes": (
            "C1 是虚构重建形象，不对应真实照片；C2 是普通市民。"
            "face token 逐字节复用于每一个露脸镜头，未登记的镜头只拍背影/远景/手。"
        ),
    }
    CAST.write_text(json.dumps(cast, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    chars = sum(len(re.sub(r"[，。、；：“”《》（）\s]", "", s["narration"])) for s in shots)
    print(f"story.json 已写出：{len(shots)} 镜 × 6 秒 = {len(shots) * 6} 秒；"
          f"180 秒版旁白 {chars} 字（{chars / 180 * 60:.0f} 字/分钟）")
    print(f"cast.json 已写出：{len(CAST.read_text(encoding='utf-8').splitlines())} 行；"
          f"露脸镜头 {len(cast['shots'])} 个")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

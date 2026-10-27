#!/usr/bin/env python3
"""唯一内容源：《铅面具事件：山顶上的神秘字条》三分钟横屏动画短片。

运行 ``python3 production/leadmask1966/build_story.py`` 会写出 story.json、screenplay.md、
audio/manifest.json、抖音脚本.md 与抖音发布文案.md。29 个镜头全部是 Agnes Video 2.5 Flash
（免费档，720P 源片后期放大到 1920×1080）生成的连续运动片段；旁白一镜一句，字幕与配音同起止。

事实边界：1966 年 8 月，巴西尼泰罗伊文廷山（Morro do Vintém）发现两名电子技师身亡，
死因至今未定。「外星人 / 药物 / 团体」三类说法只作传闻插画呈现，不写成事实。
逝者只以远景剪影、草地上的人形轮廓出现，不出现遗体、血腥或伤口。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
TITLE = "铅面具事件：山顶上的神秘字条"
FILM_NAME = "铅面具事件_山顶上的神秘字条_三分钟_成片.mp4"
BRANCH = "arena/1cf9df35-desktop-tutorial"

# ---------------------------------------------------------------- 全局 STYLE / NEGATIVE
STYLE_PREFIX = (
    "【STYLE】Cinematic-quality 3D animated short film, 1960s Brazil, tropical coastal city and a bleak "
    "grassy hill, cold cyan-gray and warm orange-red complementary palette, mysterious red-orange light "
    "beams at night, finely detailed metal materials, volumetric fog, strong chiaroscuro, rich visual "
    "detail, horizontal 16:9 widescreen composition, cinematic lens language, shallow depth of field, "
    "subtle film grain. Every clip is real continuous animation with visible natural movement (wind, "
    "grass, waves, hands, people, particles, light or camera parallax); never a still image with a "
    "push-in. Period-correct 1960s Brazilian objects and clothing. Put the subject on a third line, "
    "use the full horizontal width, and keep the lower 15 percent visually quiet for subtitles. "
    "Stylized characters, never the likeness of a real person. "
)

# 传闻画面单独一套风格：同样以【STYLE】开头，自动拼接，但刻意做成泛黄手绘，
# 让观众一眼分得清「现实重现」与「传闻想象」。
STYLE_RUMOR_PREFIX = (
    "【STYLE｜传闻想象｜泛黄手绘】Aged sepia hand-drawn 2D illustration with visible paper grain, ink "
    "linework and watercolor washes, gently animated like a living drawing (paper fibers drift, ink "
    "lines shimmer, candlelight flickers); deliberately different from the realistic 3D scenes and "
    "clearly an imagined rumor, not a documentary image. Horizontal 16:9 widescreen composition, "
    "subject on a third line, full horizontal width, lower 15 percent kept quiet for subtitles, "
    "subtle film grain, muted gold and worn brown palette with one red-orange accent. "
)

NEGATIVE_PROMPT = (
    "【NEGATIVE】readable text, subtitles, captions, watermark, logo, blood, gore, wound, corpse, body "
    "detail, exposed remains, violence, nudity, deformed hands, extra fingers, extra limbs, facial "
    "collapse, distorted anatomy, modern objects in a 1960s scene, modern clothing, cars, phones, "
    "low resolution, flicker, style drift, vertical framing, black bars, frozen frame, slideshow, "
    "still image with artificial zoom, sudden scene change, jump scare, ghost, supernatural creature, "
    "realistic likeness of a real person, UFO cliché with grey aliens on screen, lens flare overload."
)

# ---------------------------------------------------------------- 角色设定（跨镜逐字复用）
CHARACTERS = {
    "miguel": (
        "【角色设定｜米格尔】Miguel, a fictionalized stylized Brazilian man of 34, medium build, short "
        "dark hair combed to the side, clean-shaven, calm earnest eyes; wearing a 1960s dark charcoal "
        "suit with a white shirt and narrow tie, sleeves often rolled up when working. He is an "
        "electronics technician who loves repairing things; his hands are precise and his expression "
        "serious. Not a portrait or likeness of any real person. "
    ),
    "manuel": (
        "【角色设定｜曼努埃尔】Manuel, a fictionalized stylized Brazilian man of 32, slimmer than Miguel, "
        "short dark wavy hair, light stubble, warm open face with an infectious smile; wearing the same "
        "period 1960s dark suit and white shirt, tie sometimes loosened. He is cheerful and curious, "
        "often the first to look up at the sky. Not a portrait or likeness of any real person. "
    ),
    "boy": (
        "【角色设定｜少年】A fictionalized stylized Brazilian boy of 18, lean and sun-tanned, very short "
        "dark hair, wearing a short-sleeve cotton shirt and knee-length shorts with worn canvas shoes, "
        "a spool of kite string in one hand. Innocent, curious, quick to smile and quick to fear. "
        "Not a portrait or likeness of any real person. "
    ),
    "wives": (
        "【角色设定｜妻子们】Two fictionalized 1960s Brazilian housewives in their early thirties, plain "
        "cotton dresses with small floral prints, hair pinned back, no jewelry except a wedding ring; "
        "gentle, tired, worried faces, one holding an old photograph. Not portraits of real people. "
    ),
    "police": (
        "【角色设定｜警察与探员】Fictionalized 1966 Brazilian civil police: field officers in dark "
        "period uniforms with peaked caps, detectives in light short-sleeve shirts, ties and suspenders "
        "with holstered sidearms kept out of frame; focused, procedural, hats held in hand at the "
        "hilltop. Not portraits of real people. "
    ),
    "doctor": (
        "【角色设定｜医生】A fictionalized 1966 Brazilian coroner of about 50, gray at the temples, "
        "round wire-frame glasses, white coat over a shirt and tie, a typed report in his hand; stern, "
        "careful, seen in profile or half-shadow. No body or examination table is ever shown. "
    ),
    "fishermen": (
        "【角色设定｜渔民】Fictionalized Brazilian fishermen of the Niterói coast, dark sun-weathered "
        "skin, simple 1960s work shirts and rolled trousers, barefoot or in rubber sandals, holding nets "
        "beside a wooden boat; startled, looking up at the sky. Not portraits of real people. "
    ),
    "shopkeeper": (
        "【角色设定｜店主】A fictionalized middle-aged Brazilian shopkeeper in a worn apron over a "
        "short-sleeve shirt, reading glasses pushed up on his forehead, friendly and a little curious. "
        "Not a portrait of a real person. "
    ),
    "stranger": (
        "【角色设定｜传闻中的陌生人】An anonymous 1960s man in a long coat and fedora, face completely "
        "lost in shadow, hands only; he exists solely inside the hand-drawn rumor illustrations and is "
        "not a claim about any real person. "
    ),
}
CHARACTER_SEEDS = {
    "miguel": 19660817,
    "manuel": 19660818,
    "boy": 19660820,
    "wives": 19660821,
    "police": 19660822,
    "doctor": 19660823,
    "fishermen": 19660824,
    "shopkeeper": 19660825,
    "stranger": 19660826,
}

# ---------------------------------------------------------------- 29 镜（4–9 秒／镜，合计 180 秒）
# (镜号, 起始, 时长, 运镜, 角色, 风格变体, 提示词)
SHOT_ROWS = [
    ("S01", 0, 5, "航拍从海面缓慢上升到山顶", [], "real",
     "Night aerial view over Niterói, Brazil, 1966: dark Atlantic water in the left third with scattered "
     "warm city lights reflected in it, a black mountain ridge silhouetted across the right two-thirds, "
     "thin clouds sliding past. A single red-orange beam of light glides slowly through the clouds above "
     "the summit and its glow ripples on the sea. Camera: one continuous low aerial glide rising from the "
     "water toward the hilltop, slow and steady, ending small and distant. Real motion: waves, drifting "
     "cloud, travelling light. Hold on this single view for the full clip; no readable text."),
    ("S02", 5, 5, "远景缓慢推近，不进入特写", [], "real",
     "Late night on a bare grassy hilltop outside Niterói, 1966: two male silhouettes lie side by side "
     "in tall grass across the middle third, dark raincoats, faces covered by flat gray metal eye-masks "
     "that catch a cold sheen. Grass sways in the wind; a red-orange light sweeps across the sky above "
     "them and briefly glints on the metal, then fades. Camera: slow dolly-in from a respectful distance, "
     "staying wide, never entering a close-up. Real motion: wind, grass, drifting mist, passing light. "
     "No body detail, no injury, no text."),
    ("S03", 10, 7, "中景，缓慢横移展示工作台", ["miguel"], "real",
     "Interior of a small 1960s Brazilian television repair shop in Campos dos Goytacazes, daylight: "
     "shelves crowded with radios and glass vacuum tubes on the left third, a long workbench across the "
     "right two-thirds. Miguel leans over an open television chassis and turns a screwdriver; a vacuum "
     "tube glows warm orange beside his hand. Real motion: fingers working, dust drifting in the sunbeam, "
     "a small fan turning. Camera: medium shot, slow lateral track across the bench. No signage, no "
     "readable text, hold on this single interior view for the full clip."),
    ("S04", 17, 7, "低角度仰拍，环绕", ["manuel"], "real",
     "Rooftop of a low house in Campos dos Goytacazes, 1966, bright blue sky with white clouds: Manuel "
     "stands on the roof adjusting a tall television antenna, its metal elements flashing in the sun. "
     "He turns his head, smiles and waves toward the camera. Green fields and low houses recede across "
     "the right third. Real motion: wind moving his jacket, antenna wobbling, clouds drifting. Camera: "
     "low-angle wide shot, gentle continuous orbit around him. No readable text."),
    ("S05", 24, 6, "中景侧面，暖色光", ["miguel", "manuel", "wives"], "real",
     "Warm evening interior of a modest Brazilian home, 1966: a dining table on the left third with a "
     "folded paper list, Miguel and Manuel in dark suits holding an old leather bag, a wife in a plain "
     "dress and a small child at the table. The men lean in to say goodbye; her hand rests on the bag; "
     "the child waves. Camera: medium side-on shot, warm tungsten light, soft shadows. Real motion: small "
     "gestures, steam from a cup, a curtain moving. Faces soft and stylized, no readable text."),
    ("S06", 30, 5, "跟拍，逐渐拉远", ["miguel", "manuel"], "real",
     "Late afternoon at the long-distance bus station in Niterói, 1966: a bus with its door open on the "
     "left third, a concrete platform and a few travellers crossing the right two-thirds. Miguel and "
     "Manuel step down with the old leather bag, look around, excited but serious. The warm afternoon "
     "light slowly cools to gray-blue. Real motion: passengers walking, exhaust drifting, cloth moving. "
     "Camera: gentle tracking shot that gradually pulls back. No signage, no readable text."),
    ("S07", 35, 7, "航拍缓慢推向山脊", [], "real",
     "Wide establishing shot of a bare grassy hill outside Niterói, 1966, at dusk: the empty summit "
     "sits in the middle third, a thin gravel path climbs through dry grass and scattered rocks, low "
     "shrubs tilt in the wind, and the bay with the hazy city lies far below on the left. Cold "
     "blue-gray sky, one faint red-orange glow left on the horizon, thin fog drifting across the "
     "slope. Camera: slow high aerial drift toward the hilltop, one continuous move. Real motion: "
     "long grass waves, drifting fog, two distant birds. No people, no text."),
    ("S08", 42, 7, "中景跟拍少年上山", ["boy"], "real",
     "Bright afternoon on a stony dirt path climbing the bare grassy hill outside Niterói, 1966: an "
     "eighteen-year-old Brazilian boy in a short-sleeved shirt and shorts walks up the path toward the "
     "summit, a small diamond kite under one arm and a wooden spool of string in his hand, seen from "
     "behind and slightly to the side. The bay is small and hazy on the left horizon; grass and dust "
     "move in the breeze, the kite tail flutters. Camera: medium-wide tracking shot following him "
     "uphill at shoulder height, one continuous move. Real motion: walking, grass, dust, fluttering "
     "kite tail. No text."),
    ("S09", 49, 6, "中景，少年视角缓慢前移", ["boy"], "real",
     "Bright afternoon on the grassy summit of Vintém Hill, 1966: the boy stands in the left third "
     "holding a taut kite string, a simple diamond kite swaying in the blue sky on the right. He steps "
     "forward through tall grass and stops: two dark shapes lie side by side in the grass ahead, partly "
     "hidden, with a cold metallic glint where their faces are. Camera: medium wide shot drifting slowly "
     "forward from his point of view. Real motion: kite, grass, taut string. No body detail, no text."),
    ("S10", 55, 5, "特写，慢动作", ["boy"], "real",
     "Close-up of the boy's face on the hilltop, 1966: excitement drains into fear, eyes widening, mouth "
     "opening; the kite string slips through his fingers in slow motion and the thin line whips away "
     "toward the bright sky. Wind lifts his hair and the grass behind him. Camera: tight close-up, "
     "shallow depth of field, slow motion, then a slight tilt up to follow the escaping line. Stylized "
     "realistic 3D face, no text. Hold on him for the full clip."),
    ("S11", 60, 7, "航拍缓慢拉升", ["police"], "real",
     "Aerial view of the grassy hilltop at dusk, 1966: a police cordon of rope and wooden stakes circled "
     "in the middle third, four officers in period Brazilian uniforms standing with caps in hand, heads "
     "bowed. On the ground, two white chalk outlines of human figures side by side in the grass, empty. "
     "Wind bends the grass; a police photographer raises an old camera. Camera: slow aerial rise, "
     "restrained and distant. No bodies, nothing inside the outlines but grass, no text."),
    ("S12", 67, 6, "俯拍，依次特写", ["police"], "real",
     "Low overhead view of the grass beside the cordon, 1966: a dark raincoat folded once, a glass water "
     "bottle lying on its side, a folded white towel and a flat gray metal eye-mask laid out in a row "
     "across the frame, each separated by grass. A gloved hand enters and lifts the edge of the raincoat. "
     "Camera: top-down, slow lateral drift, shallow focus. Real motion: grass, cloth, gloved fingers. "
     "No readable labels, no text."),
    ("S13", 73, 4, "大特写，缓慢旋转", [], "real",
     "Extreme macro of a handmade lead eye-mask resting on grass at dusk, 1966: a roughly rectangular "
     "sheet of dull gray lead with hammer marks and a rough cut edge, two shallow U-shaped notches, no "
     "eyeholes and no straps. The red-orange light of the sky slides across the metal and reflects in a "
     "slow travelling sheen. Camera: slow arc around the mask, very shallow focus. Real motion: "
     "reflection travelling, grass trembling. No text, hold on the mask for the full clip."),
    ("S14", 77, 8, "大特写，图标依次亮起", [], "real",
     "Extreme close-up of an open pocket notebook on dark cloth, 1966: the pencil handwriting on the page "
     "is deliberately blurred and unreadable. Five small hand-drawn icons along the page light up one "
     "after another with a warm red-orange glow — a clock, a capsule, a metal ingot, a lightning bolt, a "
     "mask — like embers breathing in the dark. Camera: macro, nearly locked with a very slow push. Real "
     "motion: glowing icons, dust, faint page flutter. No readable letters or numbers."),
    ("S15", 85, 7, "中景环绕", ["police"], "real",
     "Interior of a 1966 Brazilian police office at night: a large map spread on a wooden table in the "
     "middle third, three detectives in shirt sleeves and ties leaning over it, one holding a pencil, one "
     "shaking his head, one pointing. A red pencil circle marks a hill drawn on the map. Desk lamp light, "
     "cigarette smoke drifting. Camera: medium shot, slow continuous orbit around the table. Real motion: "
     "hands, smoke, lamp flicker. The map carries no readable place names or text."),
    ("S16", 92, 7, "缓慢推近，冷灰调", ["doctor"], "real",
     "Restrained interior of a 1966 coroner's office at dusk: the doctor in a white coat and round "
     "glasses stands at a window in the left third, reading a typed report, his face in profile and "
     "half-shadow. On the desk: glass test tubes, a folder, a lamp. Outside the window the sky is dim "
     "gray. No body, no examination table. Camera: slow push-in past the desk toward the window; a faint "
     "curling wisp of steam rises from a test tube. Real motion: page turning, steam, curtain. No "
     "readable text."),
    ("S17", 99, 6, "低机位跟拍", ["police"], "real",
     "Low-angle view across the grassy hilltop at dusk, 1966: a technician in a light shirt crouches in "
     "the right third sweeping a Geiger counter over the grass, its analog needle barely moving; two "
     "detectives stand behind him, then exchange a look and shake their heads. The red-orange afterglow "
     "sits on the horizon. Camera: low tracking shot moving with the instrument, grass blades passing "
     "close to the lens. Real motion: sweeping arm, grass, needle. No text."),
    ("S18", 105, 5, "俯拍地图，问号放大", ["police"], "real",
     "Top-down view of a paper map on a dark table, 1966: two pencil routes converge at the foot of a "
     "hill drawn on the map, and at the summit a small red question mark pulses and grows, casting a "
     "faint red glow across the paper fibers. A detective's finger rests at the crossing point. Camera: "
     "overhead, nearly locked, with a slow continuous zoom toward the mark. Real motion: pulsing glow, "
     "dust, the shifting paper texture. No readable place names or text."),
    ("S19", 110, 7, "低机位，仰拍天空", ["fishermen"], "real",
     "Night on a Brazilian beach near Niterói, 1966: dark-skinned fishermen in simple clothes stand "
     "beside a wooden boat in the lower third, nets in hand, all looking up. Above them a red-orange orb "
     "of light drifts slowly across the starry sky and starts to descend toward the dark hill on the "
     "right; its glow ripples on the water. Camera: low angle, wide, slowly tilting up. Real motion: "
     "waves, net, drifting light. No text."),
    ("S20", 117, 7, "广角缓慢推近", ["miguel", "manuel"], "rumor",
     "Night on a bare hilltop: two men in suits sit on the grass with their backs to us, flat metal "
     "eye-masks over their faces, facing the sky. A red-orange beam descends slowly from the clouds; the "
     "grass bends as if in a wind, yet the two figures stay perfectly still. Ink outlines, watercolor "
     "washes, dust in the beam. Camera: wide shot, slow push-in, one continuous imagined illustration. "
     "No text."),
    ("S21", 124, 6, "横移特写", [], "real",
     "Interior of a cluttered 1960s electronics workbench at night: antenna blueprints with abstract "
     "unreadable diagrams pinned on the wall, semiconductor parts, coils and soldering tools across the "
     "bench, three old books with abstract symbol covers stacked at the right. A single warm bulb sways "
     "slightly above. Camera: slow lateral macro glide across the bench, one continuous move. Real "
     "motion: swaying light, dust, a faint coil spring. No readable text."),
    ("S22", 130, 5, "横向滑动", [], "rumor",
     "Aged hand-drawn ink-and-watercolor illustration filling the whole frame edge to edge, drawn "
     "directly on the paper with no inner picture frame, no painted border and no dark surround: a "
     "childish flying saucer hovers above a bare hill under a red-orange glow, and one large red "
     "question mark is brushed across the sky beside it. Camera: slow lateral slide while the glow "
     "breathes and paper fibers drift. Every corner stays covered with drawing; never letterboxed. "
     "Clearly a hand-drawn rumor illustration, not a photograph. No readable letters."),
    ("S23", 135, 7, "缓慢推近胶囊", [], "rumor",
     "A dim small room lit by a single candle: four blurred figures sit in a circle on the floor, faces "
     "indistinct, and on a low table a glass of water and three small white capsules catch the "
     "candlelight. Shadows lengthen and shrink on the wall as the flame moves. Camera: slow push-in "
     "toward the capsules, one continuous hand-drawn illustration coming alive. No text."),
    ("S24", 142, 7, "中景缓慢推近", ["stranger", "miguel", "manuel"], "rumor",
     "At a doorway, a stranger in a long coat and fedora, face completely lost in shadow, hands a folded "
     "map to two men in suits; a hill on the map is circled in red. The two men lean in with hopeful "
     "faces while the light around them dims. Ink linework, watercolor, paper grain. Camera: medium "
     "shot, slow push-in. Clearly a rumor illustration, no readable text."),
    ("S25", 149, 6, "横向滑动，依次擦除", [], "rumor",
     "Three ornate aged frames hang side by side on a dark wall; each holds a subtly animated hand-drawn "
     "scene: a saucer over a hill, a circle of seated figures, a stranger handing over a map. A red "
     "question mark appears over each frame in turn, then a sweep of pale light erases all three marks "
     "and leaves only empty glass. Camera: smooth lateral slide from left to right. Paper grain, ink "
     "lines. No readable text."),
    ("S26", 155, 6, "低机位，缓慢拉远", [], "real",
     "Dusk on the empty grassy hilltop outside Niterói, 1966: a snapped kite string trembles in the grass "
     "in the middle third, and two shallow flattened patches in the grass where two people lay catch the "
     "last red-orange light. Wind moves the grass in long waves; a single bird crosses the sky. Camera: "
     "low angle, very slow pullback revealing the empty summit and the darkening bay. No people, no body "
     "detail, no text."),
    ("S27", 161, 6, "中景缓慢推近", ["wives"], "real",
     "Interior of a modest Brazilian home at night, 1966: two women in plain dresses stand at a window in "
     "the left third, one holding an old photograph against her chest, both looking out at the dark "
     "street. Beside them an old valve radio glows faintly, static crackling, its dial needle drifting "
     "between stations. Warm lamp light, long shadows. Camera: medium shot, slow push-in. Real motion: "
     "curtain, glowing dial, hands. Soft stylized faces, no readable text."),
    ("S28", 167, 5, "静态居中，依次亮起", [], "real",
     "A near-black background with a subtle drifting haze: five small hand-drawn icons glow into "
     "existence one after another — a clock, a capsule, a metal ingot, a lightning bolt, a mask. The last "
     "mask glows brighter, flickers, and is replaced by a large red-orange question mark pulsing in the "
     "center. Camera: locked-off and symmetrical, with real breathing glow and drifting particles. No "
     "readable letters or numbers."),
    ("S29", 172, 8, "缓慢旋转，淡入淡出", [], "real",
     "Near-black cinematic background: a single handmade lead eye-mask slowly rotates in mid-air in the "
     "center-right, its rough gray surface catching a red-orange light that slides across it; fine dust "
     "and embers drift in the air. Leave clean negative space on the left and center for a "
     "post-production Chinese title that is added later. Camera: very slow orbit around the mask, stable "
     "and elegant. The generated clip itself contains no lettering."),
]

# ---------------------------------------------------------------- 一镜一句旁白（29 条）
# 每条都写进分镜：旁白 = 字幕，起止与镜头一致；只允许加速，不允许慢放。
NARRATION = {
    "S01": "一九六六年，巴西，山顶上亮起一道红光。",
    "S02": "两个男人戴着铅面具并排躺着，身边一张字条。",
    "S03": "他们叫米格尔和曼努埃尔，是坎普斯市的电子技师。",
    "S04": "专门给电视台安装信号设备，也修电视和收音机。",
    "S05": "八月十七日，他们对家人说，要去圣保罗买车和仪器。",
    "S06": "可当天下午，他们出现在另一座城市：尼泰罗伊。",
    "S07": "尼泰罗伊郊外，有一座荒凉的小山，叫文廷山。",
    "S08": "八月二十日，一个十八岁的少年上山放风筝。",
    "S09": "爬到山顶，他看见两个人并排躺着，一动不动。",
    "S10": "风筝线从他手里滑落，风筝飘向远处的天空。",
    "S11": "警方赶到现场，拉起警戒线，草地上只有两个人形轮廓。",
    "S12": "他们穿着西装，套着雨衣，身边放着水瓶和毛巾。",
    "S13": "铅灰色的眼罩，倒映着天边的红光。",
    "S14": "笔记写着：十六点三十到达，十八点三十服下胶囊，然后等待信号。",
    "S15": "警局里，探员围着地图争论：是谁把他们叫上山的？",
    "S16": "验尸报告写着：没有枪伤，没有刀伤，没有打斗痕迹。",
    "S17": "常见毒物查不出来，铅板上也没有放射性。",
    "S18": "死因，成了第一个说不清的谜。",
    "S19": "有渔民说，那晚山顶上空，出现过红橙色的光。",
    "S20": "于是有人说：这是外星人。铅面具，是为了挡住强光。",
    "S21": "两位技师痴迷实验和神秘学，桌上堆满图纸和旧书。",
    "S22": "他们在等一个信号——可这只是传闻。",
    "S23": "也有人说，他们在某个团体的指引下，吞下了药物。",
    "S24": "还有人利用他们对飞碟的兴趣，把他们骗上了山。",
    "S25": "可这些说法，一个也没有被证实。",
    "S26": "案件至今没有定论，红橙色的夕阳照在空山上。",
    "S27": "两位妻子一直在窗前等，再也没等到他们回家。",
    "S28": "字条上的「信号」和「金属」，没有人知道答案。",
    "S29": "你觉得，他们到底在等什么信号？评论区告诉我。",
}

# ---------------------------------------------------------------- 九段（由镜头推导，只用于章节统计）
CHAPTER_TITLES = [
    ("N01", "黄金三秒钩子"),
    ("N02", "两个电子技师"),
    ("N03", "山顶发现"),
    ("N04", "现场与字条"),
    ("N05", "无解的调查"),
    ("N06", "传闻一：外星人"),
    ("N07", "传闻二：被骗与服药"),
    ("N08", "至今未解"),
    ("N09", "互动结尾"),
]

SOURCES = [
    {
        "id": "wiki-lead-masks",
        "title": "Wikipedia: Lead masks case",
        "url": "https://en.wikipedia.org/wiki/Lead_masks_case",
        "supports": "1966年8月17日两名电子技师最后一次被家人看到、8月20日文廷山发现遗体、"
                    "西装与雨衣与铅眼罩、空水瓶与毛巾、笔记上的时间与胶囊指令、死因未定。",
    },
    {
        "id": "globo-linha-direta",
        "title": "Rede Globo · Linha Direta Justiça: Máscaras de Chumbo",
        "url": "https://redeglobo.globo.com/Linhadireta/0,26665,GIJ0-5257-215829,00.html",
        "supports": "姓名米格尔·若泽·维亚纳（34岁）与曼努埃尔·佩雷拉·达克鲁斯（32岁）、"
                    "电视发射机与中继设备技师、对家人称去圣保罗买车与电子设备、"
                    "尼泰罗伊长途汽车站、购买雨衣与水瓶的路线。",
    },
    {
        "id": "oglobo-60anos",
        "title": "O Globo (2026-08-16): Máscaras de chumbo — 60 anos de mistério",
        "url": "https://oglobo.globo.com/rio/bairros/niteroi/noticia/2026/08/16/mascaras-de-chumbo-apos-60-anos-misterio-envolvendo-corpos-e-luzes-no-ceu-ainda-intriga-niteroi.ghtml",
        "supports": "笔记内容「16h30 estar no local determinado / 18h30 ingerir cápsulas / "
                    "aguardar o sinal」的近年复核；案件六十年后仍未定论；夜空中「光」的传闻。",
    },
    {
        "id": "coldfile-1966",
        "title": "The Cold File: The Masks on Vintém Hill (1966)",
        "url": "https://thecoldfile.com/articles/1966-lead-masks/",
        "supports": "现场物品清单（空水瓶、两条毛巾、小笔记本）、正式尸检未确定死因、"
                    "毒理检测因遗体腐败未能可靠完成、笔记转写版本之间的差异。",
    },
    {
        "id": "strangehappen-masks",
        "title": "StrangeHappen: Lead Masks Case — the 1967 examination report",
        "url": "https://strangehappen.com/lead-masks-case/",
        "supports": "1967年8月3日第31,485号检验报告：两片约225/240克、2毫米厚、20厘米长的铅板，"
                    "中央U形剪口，有锤痕，无眼孔、无系带；另有报告称铅板未检出放射性物质。",
    },
    {
        "id": "mentalfloss-1966",
        "title": "Mental Floss: The Bizarre Lead Mask Deaths of 1966",
        "url": "https://www.mentalfloss.com/article/70161/bizarre-lead-mask-deaths-1966",
        "supports": "1966年8月20日下午一名18岁男子在文廷山放风筝时发现两人；"
                    "死因未定；当年未做可靠毒理检测。",
    },
    {
        "id": "pmig96-archive",
        "title": "pmig96 case archive: The Lead Masks Case",
        "url": "https://pmig96.wordpress.com/2021/05/10/the-lead-masks-case/",
        "supports": "笔记原文缺标点造成的歧义；「protect metals」与戒指、手表被收进衣内的关联；"
                    "外星接触、药物与团体等说法均属未证实传闻。",
    },
]

PRINCIPLES = [
    "全片29个镜头全部由 Agnes Video 2.5 Flash 免费档生成连续运动片段（720P 源片，后期放大到 1920×1080），"
    "禁止静态图加推拉代替；每个镜头只出现一次。",
    "每条提示词自动以【STYLE】开头、以【NEGATIVE】结尾；出现人物时自动在其前面拼接对应【角色设定】；"
    "2.5 Flash 不接受独立 negative_prompt 字段，红线因此写在提示词正文里。",
    "逝者只以远景剪影、草地上的人形轮廓表现；不出现遗体、伤口、血腥或任何遗体特写；"
    "现场镜头保持在警戒线外。",
    "所有『UFO／药物／团体』画面使用泛黄手绘风格（STYLE_RUMOR），与现实重现画面明确区分，"
    "并在字幕与旁白里点明是传闻。",
    "外星人、药物、被团体欺骗三种说法都只作传闻呈现，不写成事实；案件至今没有定论。",
    "中文标题、字幕与片尾字卡全部由后期叠加；仅 S29 允许出现标题文字，模型本身不生成任何可读文字。",
    "旁白一镜一句：每镜一条独立配音与一条同起止字幕，保留自然语速，必要时最多加速 1.55 倍，禁止慢放填满时长。",
    "『红橙色的光』与『铅灰色的金属眼罩』是全片两个视觉母题，在钩子、字条、传闻与结尾反复出现。",
]

PRESENTATION = {
    "cover": {
        "layout": "16:9；左三分之一铅灰色眼罩特写，右三分之二夜空中的红橙色光与文廷山剪影；大字在左侧",
        "text": "铅面具",
        "subtext": "巴西 · 1966 · 至今未解",
        "style": "金色粗体字、黑色描边；由 S13 眼罩与 S01 山顶夜景两帧合成，不是静态图替代视频",
    },
    "end_title": "铅面具事件",
    "end_subtitle": "巴西 · 1966 · 至今未解",
    "highlight_keywords": [
        "铅面具", "一九六六年", "红橙色", "字条", "米格尔", "曼努埃尔", "尼泰罗伊",
        "文廷山", "雨衣", "铅灰色", "十六点三十", "十八点三十", "等待信号",
        "没有枪伤", "没有刀伤", "没有打斗痕迹", "放射性", "说不清", "外星人", "传闻",
        "胶囊", "骗上了山", "没有一个被证实", "至今没有定论", "评论区",
    ],
    "subtitle_style": {
        "font_size_px": 58,
        "outline_px": 3,
        "safe_bottom_margin_px": 72,
        "alignment": "bottom-center",
        "normal_color": "white",
        "highlight_color": "gold",
        "highlight_scale": 1.2,
    },
    "sound_events": [
        {"at": 0, "name": "低沉大提琴单音渐强 + 电子嗡鸣 + 远处海风", "kind": "music_sfx"},
        {"at": 10, "name": "轻快巴西尼龙吉他分解和弦 + 沙锤", "kind": "music_sfx"},
        {"at": 30, "name": "长途汽车进站的气刹与人群声", "kind": "sfx"},
        {"at": 35, "name": "小店门铃、玻璃瓶放上柜台", "kind": "sfx"},
        {"at": 42, "name": "山风渐强、紧张弦乐渐入", "kind": "music_sfx"},
        {"at": 49, "name": "风筝线嗖嗖、少年脚步", "kind": "sfx"},
        {"at": 55, "name": "风筝线脱手的慢动作抽离声", "kind": "sfx"},
        {"at": 60, "name": "警戒线绳索拍打、相机快门", "kind": "sfx"},
        {"at": 73, "name": "金属眼罩轻碰声与低频金属余响", "kind": "sfx"},
        {"at": 77, "name": "铅笔摩擦纸面、五个图标依次亮起的电子点音", "kind": "sfx_music"},
        {"at": 85, "name": "悬疑钢琴点奏、秒针般的节拍", "kind": "music_sfx"},
        {"at": 99, "name": "盖革计数器咔嗒声", "kind": "sfx"},
        {"at": 110, "name": "空灵合成器、海潮与神秘回声", "kind": "music_sfx"},
        {"at": 117, "name": "红橙色光束的低频嗡鸣", "kind": "sfx"},
        {"at": 135, "name": "阴郁弦乐、蜡烛摇曳、胶囊落在桌面", "kind": "music_sfx"},
        {"at": 149, "name": "三下擦除的纸面沙沙声", "kind": "sfx"},
        {"at": 155, "name": "大提琴缓慢下行、山风", "kind": "music_sfx"},
        {"at": 161, "name": "老收音机静电声", "kind": "sfx"},
        {"at": 172, "name": "大提琴单音收尾，最后一秒静音", "kind": "music_sfx"},
    ],
    "douyin_title": "两个人戴着铅面具死在山头，身边只留下一张没人看懂的字条",
    "hashtags": ["#未解之谜", "#铅面具事件", "#巴西", "#悬疑", "#3D动画", "#真实事件"],
    "release_intro": (
        "1966年8月，巴西尼泰罗伊的文廷山上，两名电子技师并排躺在草丛里。"
        "他们穿着西装和雨衣，脸上盖着手工剪出来的铅眼罩，身边只有一只空水瓶、一条毛巾，"
        "和一页写着时间的笔记：十六点三十到达，十八点三十服下胶囊，然后等待信号。\n\n"
        "没有枪伤，没有刀伤，没有打斗痕迹。尸检没能确定死因，毒理检测也没能可靠完成。\n"
        "外星人、药物、被团体欺骗——传说越传越多，但没有一种被证实。\n"
        "六十年过去，这座山仍然没有给出答案。\n\n"
        "画面为AI生成的情景重现，不是历史影像。传闻部分为手绘风格演绎。\n\n"
        "你觉得，他们到底在等什么信号？"
    ),
}

REFERENCE_IMAGES = [
    {"file": "reference/01-miguel-character.png",
     "description": "米格尔角色定稿：1960年代深色西装、卷袖修电视，风格化形象，非真实肖像"},
    {"file": "reference/02-manuel-character.png",
     "description": "曼努埃尔角色定稿：同款西装、屋顶调天线回头笑，风格化形象，非真实肖像"},
    {"file": "reference/03-vintem-hill.png",
     "description": "文廷山场景定稿：荒草坡、碎石小径、山顶空旷、夜里红橙色光与云"},
    {"file": "reference/04-lead-mask-note.png",
     "description": "核心道具定稿：两片铅灰色手工眼罩（无眼孔无系带）与一页抽象符号笔记"},
    {"file": "reference/05-1960s-campos-shop.png",
     "description": "坎普斯市电视修理铺与街道年代质感定稿"},
    {"file": "reference/06-rumor-handdrawn.png",
     "description": "传闻画面风格定稿：泛黄手绘、纸纹、墨线与水彩，和现实画面明确区分"},
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def visible(text: str) -> int:
    return sum(1 for ch in text if ch.isalnum() or "\u3400" <= ch <= "\u9fff")


def build() -> dict:
    shots = []
    for index, (sid, start, duration, camera, characters, variant, prompt) in enumerate(SHOT_ROWS):
        narration = NARRATION[sid]
        characters = list(characters)
        # 单角色镜头用该角色的固定 seed，双人/无人镜头用镜头 seed：同一张脸跨镜更稳。
        seed = CHARACTER_SEEDS[characters[0]] if len(characters) == 1 else 19660801 + index
        shots.append({
            "id": sid,
            "kind": "agnes",
            "start": start,
            "duration": duration,
            "narration_id": None,  # filled below from chapters
            "narration": narration,
            "camera": camera,
            "characters": characters,
            "style_variant": variant,
            "prompt": prompt,
            "purpose": prompt.split(":")[0].split(".")[0].strip()[:120],
            "seed": seed,
            "seconds": duration,
            "aspect": "16:9",
            "source_size": "720P",
            "transition_out": "同段内硬切或轻叠化；现实与传闻之间用0.3秒红橙色光晕转场；"
                              "不改动旁白时间轴。",
        })

    chapter_bounds = [
        ("N01", 0, 10), ("N02", 10, 35), ("N03", 35, 60), ("N04", 60, 85), ("N05", 85, 110),
        ("N06", 110, 135), ("N07", 135, 155), ("N08", 155, 172), ("N09", 172, 180),
    ]
    title_by_id = dict(CHAPTER_TITLES)
    chapters = []
    for cid, start, end in chapter_bounds:
        members = [shot for shot in shots if start <= shot["start"] < end]
        if not members:
            raise ValueError(f"Chapter {cid} has no shots")
        for shot in members:
            shot["narration_id"] = cid
        chapters.append({
            "id": cid,
            "title": title_by_id[cid],
            "start": start,
            "duration": end - start,
            "shot_ids": [shot["id"] for shot in members],
            "text": "".join(shot["narration"] for shot in members),
        })

    return {
        "title": TITLE,
        "film_name": FILM_NAME,
        "target_duration": 180,
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "model": "agnes-video-2.5-flash",
        "source_size": "720P",
        "branch": BRANCH,
        "style_prefix": STYLE_PREFIX,
        "style_rumor_prefix": STYLE_RUMOR_PREFIX,
        "negative_prompt": NEGATIVE_PROMPT,
        "characters": CHARACTERS,
        "character_seeds": CHARACTER_SEEDS,
        "principles": PRINCIPLES,
        "chapters": chapters,
        "shots": shots,
        "narration_spec": {
            "voice_id": "voice-00",
            "language": "zh-CN",
            "alignment": "one-independently-generated-voice-clip-and-one-caption-cue-per-shot",
            "max_speedup_factor": 1.55,
            "slowdown_allowed": False,
            "dramatic_pause_after": {"S25": 0.5},
        },
        "sources": SOURCES,
        "presentation": PRESENTATION,
        "reference_images": REFERENCE_IMAGES,
        "fact_boundary": [
            "1966年8月17日，米格尔·若泽·维亚纳与曼努埃尔·佩雷拉·达克鲁斯离开坎普斯市；"
            "家人称他们要去圣保罗买车与电子设备，实际当天下午出现在尼泰罗伊。",
            "1966年8月20日下午，一名18岁少年在文廷山放风筝时发现两人；"
            "山路难走，警方与消防次日才抵达现场。",
            "现场物品：空水瓶、两条毛巾、深色西装、雨衣、手工铅眼罩、写有时间的笔记本。",
            "笔记（转写版本存在差异）大意：16:30 到达指定地点；18:30 服下胶囊；"
            "药效发作后保护金属，等待信号，戴上面具。",
            "没有枪伤、刀伤或打斗痕迹；正式尸检未能确定死因；"
            "因遗体腐败，毒理检测未能可靠完成。",
            "1967年检验报告描述铅板约225/240克、2毫米厚、20厘米长，有锤痕、无眼孔无系带；"
            "另有报告称未检出放射性物质。",
            "『外星人／红橙色光／团体指引服药／被骗上山』全部属于公开流传的传闻，"
            "没有任何一种被证实，片中一律标注为传闻。",
            "六十年后案件仍未定论。",
        ],
    }


def write_screenplay(story: dict) -> None:
    lines = [
        f"# {story['title']}",
        "",
        "三分钟横屏悬疑动画短片 · 1920×1080 · 30fps · 180秒 · 29 个 Agnes Video 2.5 Flash 动态镜头",
        "",
        "> 画面为 AI 动画情景重现，不是历史影像；逝者只以远景剪影与草地人形轮廓出现。",
        "> 传闻画面使用泛黄手绘风格，与现实重现明确区分。",
        "",
        "## 角色与场景定稿参考图",
        "",
    ]
    for ref in story["reference_images"]:
        lines.append(f"- `{ref['file']}`：{ref['description']}")
    lines += ["", "## 事实边界", ""]
    lines += [f"- {item}" for item in story["fact_boundary"]]
    lines += ["", "## 九段旁白（一镜一句，字幕与配音同起止）", ""]
    for chapter in story["chapters"]:
        start, end = chapter["start"], chapter["start"] + chapter["duration"]
        lines += [
            f"### {start//60:02d}:{start%60:02d}—{end//60:02d}:{end%60:02d}　{chapter['title']}"
            f"（{chapter['id']}）",
            "",
            chapter["text"],
            "",
        ]
        for shot in story["shots"]:
            if shot["narration_id"] == chapter["id"]:
                lines.append(f"- **{shot['id']}**（{shot['start']}–{shot['start']+shot['duration']}秒，"
                             f"{shot['duration']}秒／{shot['camera']}）：{shot['narration']}")
        lines.append("")
    lines += ["## 29 镜分镜表", "", "| 镜号 | 时间 | 秒数 | 段 | 运镜 | 角色 | 画面职责 |",
              "|---|---:|---:|---|---|---|---|"]
    for shot in story["shots"]:
        start, end = shot["start"], shot["start"] + shot["duration"]
        times = f"{start//60:02d}:{start%60:02d}—{end//60:02d}:{end%60:02d}"
        roles = "、".join(shot["characters"]) or "—"
        lines.append(f"| {shot['id']} | {times} | {shot['duration']} | {shot['narration_id']} | "
                     f"{shot['camera']} | {roles} | {shot['purpose']} |")
    lines += ["", "## 来源", ""]
    for source in story["sources"]:
        lines.append(f"- [{source['title']}]({source['url']})：{source['supports']}")
    lines += [
        "",
        "## 后期规范",
        "",
        "- 生成：Agnes Video 2.5 Flash 免费档，720P 源片，62 秒共享节流，断点续跑；后期放大到 1920×1080。",
        "- 配音：用户试听选定的中文悬疑男声；一镜一句、字幕同起止；只加速（≤1.55×），不慢放。",
        "- 字幕：白色黑边、底部安全区、关键词金色放大；『十六点三十』『十八点三十』『等待信号』逐字高亮。",
        "- 音乐：原创程序合成（大提琴、弦乐、巴西吉他、沙锤、电子嗡鸣、秒针、空灵合成器）；旁白下压约 −18dB。",
        "- 音效：风声、风筝线、门铃、相机快门、金属轻碰、铅笔摩擦、盖革计数器、老收音机静电。",
        "- 片尾：S29 铅面具旋转，后期叠加金色片名『铅面具事件』与副题『巴西 · 1966 · 至今未解』，最后一秒静音。",
        "- 封面：左侧 S13 眼罩、右侧 S01 山顶红橙色光，金色大字『铅面具』加黑边。",
        "",
    ]
    (HERE / "screenplay.md").write_text("\n".join(lines), encoding="utf-8")


def write_manifest(story: dict) -> None:
    AUDIO.mkdir(parents=True, exist_ok=True)
    existing = {}
    manifest_path = AUDIO / "manifest.json"
    if manifest_path.exists():
        try:
            existing = {row["id"]: row for row in
                        json.loads(manifest_path.read_text(encoding="utf-8")).get("clips", [])}
        except (ValueError, KeyError, TypeError):
            existing = {}
    clips = []
    for shot in story["shots"]:
        clip_path = AUDIO / f"{shot['id']}.mp3"
        previous = existing.get(shot["id"], {})
        same_text = previous.get("text") == shot["narration"]
        sha = sha256(clip_path) if clip_path.is_file() and same_text else None
        clips.append({
            "id": shot["id"],
            "file": clip_path.name,
            "text": shot["narration"],
            "sha256": sha,
            "voice_id": story["narration_spec"]["voice_id"],
            "voice_description": "用户试听选定的中文男声；悬疑叙事，沉稳有磁性",
            "narration_id": shot["narration_id"],
            "target_start": shot["start"],
            "target_duration": shot["duration"],
            "alignment": "shot-locked",
        })
    manifest = {
        "language": "zh-CN",
        "voice": story["narration_spec"]["voice_id"],
        "generation": "Arena TTS selected voice; one independent clip per shot",
        "alignment": "one-clip-one-shot-one-caption",
        "max_speedup_factor": story["narration_spec"]["max_speedup_factor"],
        "slowdown_allowed": False,
        "clips": clips,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_release_copy(story: dict) -> None:
    pres = story["presentation"]
    (HERE / "抖音发布文案.md").write_text(
        f"# {pres['douyin_title']}\n\n"
        f"{pres['release_intro']}\n\n"
        + " ".join(pres["hashtags"]) + "\n",
        encoding="utf-8",
    )
    rows = []
    for shot in story["shots"]:
        start, end = shot["start"], shot["start"] + shot["duration"]
        rows.append(f"| {shot['id']} | {start//60:02d}:{start%60:02d}—{end//60:02d}:{end%60:02d} "
                    f"| {shot['narration']} | {shot['purpose']} | {shot['camera']} |")
    events = "\n".join(
        f"| {e['at']//60:02d}:{e['at']%60:02d} | {e['name']} |" for e in pres["sound_events"]
    )
    (HERE / "抖音脚本.md").write_text(
        f"# {TITLE}\n\n"
        f"**标题：** {pres['douyin_title']}\n\n"
        "**规格：** 1920×1080 · 16:9 横屏 · 30fps · 180 秒 · 29 个 Agnes Video 2.5 Flash 动态镜头\n\n"
        "**核心钩子：** 两个男人戴着铅面具躺在山顶，身边只有一张没人看懂的字条\n\n"
        "## 四列分镜表\n\n"
        "| 镜号 | 时间 | 口播（=字幕） | 画面 | 运镜 |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## 声音设计\n\n| 时间 | 声音 |\n|---|---|\n" + events
        + "\n\n## 事实边界\n\n"
        "- 两名技师的身份、行程、现场物品与笔记内容有公开来源；死因至今未确定。\n"
        "- 外星人、药物、团体指引、被骗上山四类说法全部是传闻，没有任何一种被证实。\n"
        "- 逝者只以剪影与草地人形轮廓表现；不出现遗体、伤口或血腥。\n"
        "- 铅眼罩按1967年检验报告呈现：无眼孔、无系带，不是影视化的『开缝面具』。\n"
        "- 画面为AI动画情景重现，不是历史影像。\n\n"
        "## 发布文案\n\n" + pres["release_intro"] + "\n\n" + " ".join(pres["hashtags"]) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    story = build()
    (HERE / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n",
                                     encoding="utf-8")
    write_screenplay(story)
    write_manifest(story)
    write_release_copy(story)
    total = sum(visible(s["narration"]) for s in story["shots"])
    print(f"WROTE {HERE/'story.json'} — {len(story['shots'])} shots, "
          f"{story['shots'][-1]['start']+story['shots'][-1]['duration']}s, "
          f"{total} visible narration characters ({total/180:.2f}/s)")


if __name__ == "__main__":
    main()

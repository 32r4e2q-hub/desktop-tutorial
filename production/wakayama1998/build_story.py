#!/usr/bin/env python3
"""唯一内容源：《和歌山毒咖喱事件：一锅咖喱，四条人命》

运行 ``python3 production/wakayama1998/build_story.py`` 会写出 story.json、screenplay.md、
audio/manifest.json、抖音脚本.md 与抖音发布文案.md。29 个镜头全部是 Agnes Video 2.5 Flash
（720P 源片，后期放大到 1920×1080 · 24fps）生成的连续运动片段；旁白一镜一句，字幕与配音同起止。

事实边界：1998 年 7 月 25 日傍晚，和歌山市园部地区的自治会夏祭上，现场提供的咖喱被混入亚砷酸
（砒霜），67 人急性砷中毒，4 人死亡（自治会长 64 岁、副会长 53 岁、小学四年级男生 10 岁、
高一女生 16 岁）。1998 年 10 月 4 日林真须美与丈夫因保险金诈骗嫌疑被捕，12 月 9 日因咖喱事件
再逮捕；2002 年 12 月 11 日和歌山地裁判死刑，2005 年 6 月 28 日大阪高裁维持，2009 年 4 月 21 日
最高裁驳回上告、5 月死刑确定。她始终主张无罪；再審请求仍在继续（第 3 次请求 2024 年 2 月提出，
和歌山地裁审理中；第 2 次请求 2025 年 11 月 11 日被最高裁驳回）。

片中不出现遗体、伤口、血腥、呕吐特写或受害儿童本人；受害过程只用打翻的桌椅、救护车灯光、
一双小鞋等间接画面表现。真实人物一律为风格化形象，非真实肖像。案件争议一律中立表述。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
TITLE = "和歌山毒咖喱事件：一锅咖喱，四条人命"
FILM_NAME = "和歌山毒咖喱事件_一锅咖喱四条人命_三分钟_带声音.mp4"
BRANCH = "arena/3412a846-desktop-tutorial"
FPS = 24

# ---------------------------------------------------------------- 全局 STYLE / NEGATIVE
STYLE_PREFIX = (
    "【STYLE】Cinematic-quality 3D animated documentary reenactment of Japan, summer 1998, "
    "Wakayama City, Kansai: a hillside neighbourhood of narrow lanes, two-storey Japanese houses, "
    "utility poles with tangled wires, and a community summer festival with strings of red paper "
    "lanterns, folding tables, plastic stools, coloured bunting and cotton yukata. Warm nostalgic "
    "amber-orange dusk with cicada haze, drifting cooking steam and big soft practical lantern "
    "light at first, then cooling into deep cyan-grey and blue-black suspense with hard pools of "
    "light, volumetric beams, fine film grain, realistic aluminium, wood, glass, cloth and asphalt "
    "materials, strong chiaroscuro and shallow cinematic depth of field. Horizontal 16:9 "
    "widescreen composition, subject near a third line, full use of the left and right width, "
    "lower sixth kept visually quiet for subtitles. Every clip is true continuous 3D animation "
    "with visible natural movement - walking, turning heads, blinking, hands at work, steam and "
    "cloth drifting, lanterns swaying, light and camera parallax - never a still image with a "
    "push-in. Period-correct 1998 Japanese objects and clothing, no later technology. All people "
    "are stylized characters, never the likeness of a real person. "
)

# 抽象示意图单独一套风格：同样以【STYLE】开头，自动拼接；刻意做成干净的信息可视化，
# 与写实复原镜头明确区分，避免把概念图误读成现场照片或警方鉴识文书。
STYLE_DIAGRAM_PREFIX = (
    "【STYLE｜概念示意｜抽象可视化】Clean cinematic 3D information graphic in a dark charcoal "
    "space, restrained cyan-grey, cold white and muted gold palette with one deep blood-red "
    "accent, fine volumetric haze, soft edges, elegant shallow depth of field and subtle film "
    "grain; deliberately abstract and clearly a conceptual diagram, not a photograph of police "
    "material. Horizontal 16:9 widescreen composition with generous negative space and the lower "
    "sixth kept quiet for subtitles. Everything breathes with real continuous motion - lines draw "
    "themselves, nodes pulse, particles drift, a red thread travels, the camera moves through "
    "depth - never a flat static slide. Absolutely no readable letters, numbers, names or logos "
    "anywhere in frame. "
)

NEGATIVE_PROMPT = (
    "【NEGATIVE】readable text, subtitles, captions, watermark, logo, gibberish lettering, blood, "
    "gore, wound, corpse, dead body, bodies, remains, vomit, vomiting close-up, a person collapsing "
    "on the ground, sick child close-up, children in distress, violence in progress, weapon striking "
    "a person, fighting, nudity, deformed hands, extra fingers, extra limbs, facial collapse, "
    "distorted anatomy, plastic skin, mannequin faces, wrong building structure, modern smartphones, "
    "modern electric cars, technology later than 1998, low resolution, flicker, style drift, "
    "vertical framing, letterbox black bars inside the frame, frozen frame, slideshow, still image "
    "with artificial zoom, jump scare, ghost, supernatural effect, realistic likeness of a real "
    "person, oversaturated colours, heavy lens flare."
)

# ---------------------------------------------------------------- 角色设定（跨镜逐字复用）
CHARACTERS = {
    "masumi": (
        "【角色设定｜林真须美·风格化形象，非真实肖像】Masumi, a fictionalized stylized Japanese "
        "woman of 37, petite, short tightly permed curly hair, strong angular brows, a sharp capable "
        "face that can swing from bright laughter to stubborn silence; wearing a plain summer home "
        "blouse with a small floral print and a simple skirt, an apron in the kitchen, sandals in the "
        "yard. Confident, brisk, guarded when watched. Keep the same hairstyle, build and facial "
        "proportions in every shot; never a portrait or likeness of the real person. "
    ),
    "kenji": (
        "【角色设定｜林健治·风格化形象】Kenji, a fictionalized stylized Japanese man in his early "
        "fifties, thin and slightly stooped, short greying hair, weathered tired face, a cigarette "
        "between his fingers; wearing a plain work shirt and an old faded jacket, work trousers and "
        "worn boots. Silent, uneasy, avoids other people's eyes. Keep his build, hairstyle and "
        "clothing identical in every shot; never a portrait or likeness of the real person. "
    ),
    "housewives": (
        "【角色设定｜主妇们】Three or four fictionalized Japanese neighbourhood women aged 30 to 55, "
        "striped and floral aprons over short-sleeved summer blouses, hair tied up with clips and "
        "towels around their necks, faces shiny with sweat; brisk, cheerful, practical hands used to "
        "cooking for a crowd. Warm and lively before the turning point, frightened and shaking "
        "afterwards. Not portraits of real residents. "
    ),
    "residents": (
        "【角色设定｜居民们】Ordinary residents of a 1998 Japanese neighbourhood: women in cotton "
        "yukata with obi sashes, children in yukata chasing each other with paper fans, older men in "
        "vests and shorts, young fathers in polo shirts carrying plastic plates. Friendly, noisy, "
        "relaxed summer-festival body language; in later shots the same people are alarmed, "
        "supporting each other, holding their stomachs. Stylized never-caricatured faces, no real "
        "individuals. "
    ),
    "medics": (
        "【角色设定｜医生与护士】Japanese medics of 1998: a doctor in a white coat over a shirt and "
        "tie, a nurse in a pale uniform with a soft cap, both tired and urgent, stethoscopes and "
        "clipboards, no readable name tags. They move fast and quietly, hands steady. Not portraits "
        "of real medical staff. "
    ),
    "detectives": (
        "【角色设定｜警探】Japanese criminal investigators of 1998, men and women aged 30 to 55, in "
        "dark suits and open collars with loosened ties, tired eyes and rolled-up sleeves, notebooks, "
        "pens, paper files and clear evidence bags with blank white labels. Methodical and heavy with "
        "fatigue; they write, compare, point and think. No readable badges or insignia, not portraits "
        "of real officers. "
    ),
    "reporters": (
        "【角色设定｜记者与摄像师】A pack of 1998 Japanese press: reporters in short-sleeved shirts "
        "with lanyards, photographers with flashguns, television crews hefting large shoulder-mounted "
        "cameras, microphones with blank windscreens. Aggressive, jostling, hungry for a frame; "
        "everything period-correct to 1998, no modern phones. Not portraits of real journalists. "
    ),
    "lab": (
        "【角色设定｜鉴识研究员】A fictionalized Japanese forensic researcher of about 40 in a white "
        "lab coat over a shirt, thin-rimmed glasses, short hair, latex gloves; calm and precise, then "
        "shocked into stillness when the result appears. Works in a cool grey laboratory with steel "
        "benches and old CRT instruments with unreadable blank screens. Not a portrait of any real "
        "scientist. "
    ),
    "court": (
        "【角色设定｜法庭】A Japanese courtroom of 2002: a judge in a black robe on a raised bench, a "
        "clerk at a side desk, plain dark wooden fittings, no readable signs or docket numbers. "
        "Cold, still, formal; everyone speaks quietly. Not portraits of real court officials. "
    ),
    "neighbours": (
        "【角色设定｜街坊】Neighbours of the same street - two women and one older man, seen half "
        "hidden behind lace curtains or over a garden wall, whispering with hands near their mouths, "
        "curious and uneasy. Faces partly in shadow; no clear portrait, never a real person. "
    ),
}
CHARACTER_SEEDS = {
    "masumi": 19980721,
    "kenji": 19980722,
    "housewives": 19980723,
    "residents": 19980724,
    "medics": 19980725,
    "detectives": 19980726,
    "reporters": 19980727,
    "lab": 19980728,
    "court": 19980729,
    "neighbours": 19980730,
}

# ---------------------------------------------------------------- 29 镜（4–9 秒／镜，合计 180 秒）
# (镜号, 起始, 时长, 运镜, 角色, 风格变体, 提示词)
SHOT_ROWS = [
    ("S01", 0, 5, "航拍下降并推近街道", ["residents"], "real",
     "A summer evening in a hillside neighbourhood of Wakayama City, 1998. Camera: the lens looks almost "
     "straight down from high above a narrow residential lane and descends in one continuous smooth glide. A "
     "dense river of round red paper lanterns fills the upper two thirds of the frame, strung in long lines "
     "between wooden utility poles, glowing warm amber, the nearest ones swelling as they pass close to the "
     "lens. Through the gaps you see only the tops of heads, shoulders in cotton yukata and a few straw hats "
     "moving along the lane, plus folding tables and one serving table with steam rising. The whole frame is "
     "lanterns, dusk sky and people seen from above - no walls, no building facades, no shopfronts, no "
     "banners, no flags, no signage anywhere in frame. Photoreal live-action documentary look with fine "
     "natural grain, not an illustration. Real motion: lanterns swaying on their strings, people walking "
     "below, steam drifting, cloth moving. No readable text."),

    ("S02", 5, 5, "锅面特写缓慢推近", [], "real",
     "A garage in the same neighbourhood, early evening. A huge brushed-aluminium pot, wide as a bathtub, sits "
     "on a gas burner; thick steam curls off the dark red curry inside, and the red lantern light from the "
     "street is mirrored and distorted on the polished metal wall of the pot. A sudden cool gust sweeps "
     "through the garage: every lantern reflected on the aluminium shivers at once, the steam bends sideways "
     "and is torn apart. The bottles, jars, boxes and crates beside the burner are plain and unlabelled, and "
     "the pot itself carries no marks or lettering. Camera: slow push toward the curved metal surface until "
     "only the reflections and the trembling steam fill the frame. Real motion: steam rolling, reflections "
     "wobbling, a single drop sliding down the pot. No people in this shot, no readable text."),

    ("S03", 10, 7, "中景环绕主妇与大锅", ["housewives"], "real",
     "Inside the garage on the morning of the festival, sunlight striping the concrete floor. Three housewives "
     "in aprons work around the enormous pot: one chops potatoes and onions on a wooden board with quick even "
     "strokes, one stirs the curry with a long ladle, one wipes her forehead with the towel around her neck "
     "and laughs at something the others said. A radio, boxes of spices, plastic buckets and stacked plates "
     "crowd the shelves. Camera: a slow medium orbit around the pot, moving from the chopping board past the "
     "steam to the laughing faces. Real motion: knife work, ladle circling, steam, shoulders shaking with "
     "laughter. No readable text."),

    ("S04", 17, 7, "横向滑轨逐一展示排队的居民", ["residents", "housewives"], "real",
     "The street outside the garage at midday: a long row of folding tables and plastic stools under strings "
     "of red lanterns and colourful bunting. Residents queue with plastic plates - a woman in yukata holding "
     "her daughter's hand, an old man in a vest fanning himself, a young father in a work shirt just back from "
     "his shift. Behind the table a housewife ladles curry onto rice, steam rising between them. Every "
     "lantern, tent cloth, apron and banner is plain, with no printed characters and no shop signs anywhere. "
     "Camera: a smooth lateral dolly along the queue, one continuous move that reveals each person in turn. "
     "Real motion: queue shuffling forward, ladle serving, fans moving, lanterns swinging in the breeze. No "
     "readable text."),

    ("S05", 24, 6, "中景浅景深，母亲递勺子", ["residents"], "real",
     "A folding table in the shade, shallow focus. A young mother in a cotton blouse leans in and hands a "
     "spoon to her small son in a yukata; he takes it with both hands, scoops the curry, eats, and grins with "
     "full cheeks while she laughs and wipes a grain of rice from his chin. Plastic cups of barley tea, paper "
     "napkins and a paper fan lie on the table; the background melts into warm lantern bokeh. Camera: medium "
     "shot with very shallow depth of field, a slow gentle drift around the table. Real motion: chewing, "
     "blinking, the mother's hand moving, steam rising. No readable text, no distress."),

    ("S06", 30, 5, "航拍，云影缓慢覆盖", ["residents"], "real",
     "High aerial view of the whole festival at sunset: the lane filled with tables, red lanterns glowing, "
     "people sitting in small groups and chatting, children chasing each other between the legs of folding "
     "tables, smoke from a grill drifting sideways. The warm orange light is at its richest, and then a long "
     "shadow slides across the neighbourhood as a single dark cloud crosses the sun; the red lanterns dim and "
     "the colour drains toward grey. Camera: slow aerial drift with a gentle push in, the cloud shadow moving "
     "over the rooftops. Real motion: people, lanterns, drifting smoke, sweeping cloud shadow. No readable "
     "text."),

    ("S07", 35, 7, "中景，轻微手持晃动", ["residents"], "real",
     "Back at the folding table, twenty minutes later, the light gone flat. An elderly man in a vest carefully "
     "sets his spoon down, presses the heel of his hand to his forehead and closes his eyes, swaying slightly; "
     "his bowl of curry trembles on the plastic table. Across from him a woman half rises from her stool, "
     "alarmed, and reaches for his shoulder; other heads turn. Camera: medium shot with a faint handheld "
     "tremor, slowly tightening on his hand against his forehead. Real motion: trembling hands, a rocking "
     "bowl, heads turning, a stool scraping. No vomit, no blood, no one collapsing on the ground, no readable "
     "text."),

    ("S08", 42, 7, "广角快速横移，人群慌乱", ["residents", "housewives"], "real",
     "The festival street in chaos, seen wide and at eye level: plastic stools knocked over, a folding table "
     "tipped, plates sliding and curry spilling in a dark puddle on the asphalt, a housewife crouching beside "
     "a fallen chair with a hand pressed to her stomach while neighbours hurry past carrying water and towels, "
     "someone waving others away from the food table. Lanterns swing wildly. Camera: fast lateral tracking "
     "move through the crowd, the spilled table sweeping through the foreground. Real motion: running, "
     "swinging lanterns, spilling liquid, hands reaching. No vomit, no blood, no close-up of suffering faces, "
     "no readable text."),

    ("S09", 49, 6, "航拍俯拍，救护车驶入街区", ["medics", "residents"], "real",
     "Night, blue hour gone. From high above the narrow lane, the roofs and wires dark, red emergency lights "
     "pulsing against the walls: one ambulance has stopped in the street with its rear doors open, a second "
     "turns slowly in from the corner, its beacon washing the houses in red, and a third waits further back. "
     "Medics in pale uniforms push a folded stretcher toward a doorway; residents stand in a loose circle, "
     "hands over mouths, kept back by an officer's raised arm. Camera: top-down aerial, slow rotation "
     "following the turning ambulance. Real motion: rotating beacons, walking medics, stretcher wheels, "
     "swaying lanterns. No bodies, no blood, no readable text."),

    ("S10", 55, 5, "长走廊缓慢推进", ["medics"], "real",
     "A Japanese hospital emergency corridor at night: pale green walls, cold fluorescent tubes, a polished "
     "floor reflecting the light, curtained bays along one side. In the foreground a doctor in a white coat "
     "pulls down his surgical mask and frowns at a clipboard whose page is completely blank, then glances up "
     "as a stretcher is wheeled past the far end of the corridor by two nurses. A wall clock with a plain face "
     "and no numerals reads deep night. No lettering on the walls, doors or badges. Camera: slow steady push "
     "down the length of the corridor, the doctor passing out of frame at the side. Real motion: walking, "
     "wheels, curtain sway, a fluorescent tube flickering, breathing. No blood, no bodies, no readable text."),

    ("S11", 60, 7, "中景缓慢推近一双小鞋", ["residents"], "real",
     "The same hospital corridor, quieter now: a row of blue plastic waiting chairs, a folded blanket, a paper "
     "cup on the floor. In a close medium shot a mother in a plain summer blouse stands with her back against "
     "the wall, head bowed, holding a pair of small children's shoes against her chest with both hands; the "
     "shoes are clearly readable, two little buckle straps, faint scuffs on the toes, and they fill the lower "
     "third of the frame. Soft cool key light falls on her shoulders and on the shoes while the corridor "
     "behind melts into blue-grey bokeh. Her shoulders shake once. No child and no body appears anywhere in "
     "the shot. Camera: very slow push in toward the shoes. Real motion: breathing, a trembling hand, a "
     "curtain moving, one flicker of the tubes. No blood, no readable text."),

    ("S12", 67, 7, "实验室，样本进仪器，曲线飙升", ["lab"], "real",
     "A cool grey forensic laboratory: steel benches, glassware, an old analytical instrument with a small CRT "
     "screen and physical dials. A researcher in a white lab coat and glasses slides a sealed sample vial into "
     "the instrument's port, turns a knurled knob, and watches the screen; the trace on the display climbs in "
     "a sharp spike, holds, and keeps climbing. His pupils widen, his breath catches, and he snaps his head up "
     "toward a colleague off-frame. Camera: slow push from the hands on the dial to the rising trace, then to "
     "his face. Real motion: gloved fingers, dial turning, phosphor glow breathing, a blink. No readable "
     "characters or numbers on screen, no readable text."),

    ("S13", 74, 6, "概念示意，毒瓶图标放大", ["lab"], "diagram",
     "Abstract conceptual visualisation in cold darkness: a three-dimensional bottle-shaped icon with a "
     "skull-free, unmarked label slowly rotates and grows in the centre of the frame, its glass catching a "
     "deep blood-red light that pulses and flickers like a warning lamp; thin concentric rings expand outward "
     "from it and dissolve, dust drifting through the beam. On the right third the blurred silhouette of the "
     "researcher's face and glasses is lit only by that red glow. Camera: slow push toward the icon while the "
     "rings pass the lens. Real motion: rotation, pulsing light, expanding rings, drifting particles. Purely "
     "symbolic; no readable letters, no numbers, no readable text."),

    ("S14", 80, 5, "快速拉远，锅与警戒线", ["detectives"], "real",
     "Return to the garage, late at night: the aluminium pot stands open, lid set aside, the curry inside gone "
     "flat and cold, no steam left, one ladle resting across the rim. The camera pulls back fast and high "
     "through the garage door and out over the street, revealing the whole block wrapped in yellow-and-black "
     "police tape strung between the utility poles and the garden fences, and white-and-blue patrol cars at "
     "both ends of the lane, their bodies plain with no lettering and no number plates, roof lights turning. "
     "Two detectives in dark suits stand under the tape looking in. Camera: one continuous rapid pull-back and "
     "rise, the foreground pot shrinking to a point. Real motion: tape trembling, beacons turning, a coat "
     "flapping. No bodies, no blood, no readable text."),

    ("S15", 85, 7, "中景环绕白板", ["detectives"], "real",
     "A police incident room at night, lit by one overhead tube and a desk lamp. A detective in a dark suit "
     "with the tie pulled loose stands at a large whiteboard, marking abstract unreadable diagram strokes: a "
     "rough plan of a garage, a pot, a clock, and a cluster of small blank name cards, some circled, some "
     "crossed out with a single hard line. A second detective sits smoking at the table, ash dropping into a "
     "tin, a third leans on the back of a chair reading a folder. Haze drifts through the lamplight. Camera: "
     "slow medium orbit around the whiteboard, from the hand drawing to the watching faces. Real motion: "
     "marker moving, smoke curling, papers turning, breathing. No readable writing, no names, no logos."),

    ("S16", 92, 7, "固定机位慢动作，泛黄回忆", ["residents", "masumi"], "real",
     "A memory image, deliberately faded and slightly sepia like old film: the festival garage on the "
     "afternoon of the event, shot from a fixed position across the street. Residents come and go through the "
     "open garage door carrying boxes and plates; among them a woman with short curly hair in a floral blouse "
     "stands beside the big pot for a long stretch of time, her back half to the camera, face never clear. "
     "Dust and steam turn slowly in the light; the other figures blur past in slow motion. Every banner, "
     "curtain and sign on the street is plain, with no printed characters and no calligraphy. Camera: "
     "locked-off wide shot, subtle slow motion, no zoom. Real motion: people crossing, steam, dust, a hand "
     "testing the pot's lid. No readable text, no clear face."),

    ("S17", 99, 6, "大特写，红线连线", ["detectives"], "real",
     "Extreme close-up over a detective's shoulder at a whiteboard. His hand places a blank card on the board "
     "and draws a heavy circle around it with a marker, then a second hand pins a deep red thread to that "
     "circle and pulls it taut across the board to another blank card. The board carries only arrows, boxes "
     "and circles - no handwriting-like marks, no printed characters, no letters or numbers anywhere. The "
     "focus racks from the marker tip to a small photographic print pinned at the end, on which a woman with "
     "short permed curly hair is visible only as an out-of-focus shape. Camera: very close, slow drift along "
     "the red thread as it is pulled tight. Real motion: marker stroke, thread snapping straight, a card "
     "settling, breathing. No readable text."),

    ("S18", 105, 5, "偷拍视角，缓慢推近二层小楼", ["neighbours"], "real",
     "From behind lace curtains in a neighbouring house, at eye level: two neighbours are seen from behind in "
     "three-quarter back view, shoulders close together, faces turned away toward the street, warm rim light "
     "along their hair and shoulders - real bodies in real cloth, never flat cut-out silhouettes. Across the "
     "lane a two-storey Japanese house stands behind a low wall, one upstairs window lit a dim amber, a small "
     "garden hose coiled by the gate. All signs and house fronts are plain, with no printed characters. "
     "Camera: voyeuristic telephoto view over their shoulders, very slow push toward the lit window; the "
     "curtain edge drifts through the foreground. Real motion: a whispered turn of the head, curtain sway, the "
     "light flickering in the window. No readable text, no clear faces."),

    ("S19", 110, 7, "中景侧光，客厅里的保险单", ["masumi", "kenji"], "real",
     "The living room of the Hayashi house on a hot afternoon: sliding paper screens half closed, yellow light "
     "cutting through the gap, an electric fan turning slowly, a low table buried under a fanned-out stack of "
     "insurance documents whose pages are completely blank. There is no hanging scroll, no wall calendar and "
     "no writing of any kind in the room. Masumi sits across from the lens in a floral blouse, chin slightly "
     "raised, watching the camera with a flat half-smile that does not reach her eyes; beside her Kenji leans "
     "back in his chair, cigarette smoke rising past his tired face as he looks away. Camera: medium two-shot "
     "lit from one side, very slow drift to the right. Real motion: fan blades, smoke curling, a blink, a page "
     "lifting in the draught. No readable text on any surface."),

    ("S20", 117, 7, "特写柜门打开，慢动作", ["detectives"], "real",
     "Inside the same house during a search, in the narrow kitchen: two detectives in latex gloves crouch at a "
     "low cabinet under the sink. One pulls the door open in slow motion - buckets, bottles, a folded cloth - "
     "and a torch beam swings across the interior, stopping on a plain plastic packet of white powder wedged "
     "at the back. They look at each other, then back at the packet; one holds a clear evidence bag open. "
     "Camera: close-up on the cabinet door and the torch beam, slow motion, slight handheld drift. Real "
     "motion: the door swinging, torch beam sweeping, breathing, a gloved hand steadying. No readable labels, "
     "no blood."),

    ("S21", 124, 6, "俯拍，红线连起剪影", ["masumi"], "diagram",
     "Overhead conceptual shot in dark space: a dozen completely blank paper sheets spread across a matte "
     "black surface, with no printed lines, no ruled boxes and no writing on them at all. Around the sheets "
     "float five dim human silhouettes, faceless, each one tied to a sheet by a thin deep-red thread. A sixth "
     "silhouette at the centre - a woman with short curly hair - stands slightly apart, and the red threads "
     "converge toward her without quite touching. Camera: slow push down through the threads, dust drifting. "
     "Real motion: threads tightening and trembling, silhouettes breathing, sheets sliding a few millimetres. "
     "Symbolic only; no readable letters, no numbers, no readable text."),

    ("S22", 130, 5, "特写，两条曲线重合", ["lab"], "diagram",
     "One continuous shot inside a dark analytical laboratory at night, no cuts. In the foreground a "
     "glass-fronted CRT monitor shows two glowing spectral traces drawing themselves from left to right, one "
     "pale gold and one cold white, rising and falling in almost the same shape. As the camera eases past the "
     "monitor and racks focus into the room, the white trace slides down and settles precisely onto the gold "
     "one behind the glass. Beyond it a researcher in a white lab coat stands watching, half in shadow, her "
     "face lit only by the green-white glow of the screen. The whole clip stays in this one room in one style. "
     "Camera: slow lateral drift from the screen glass to her watching face, shallow focus. Real motion: lines "
     "drawing themselves, a pulse travelling along the curve, phosphor breathing, a blink. Conceptual forensic "
     "illustration; no axes, no numbers, no readable letters, no readable text."),

    ("S23", 135, 7, "低机位慢动作，水管喷水", ["reporters", "masumi"], "real",
     "Outside the Hayashi house in late afternoon: a wall of reporters, photographers and television crews "
     "presses against the low garden wall, shoulder-mounted cameras raised, flashguns firing in clusters, "
     "microphones pushed forward. Every camera body, microphone and jacket is blank and unbranded, and no "
     "banner or sign carries writing. Inside the yard Masumi stands with her jaw set, both hands on a green "
     "garden hose, and sweeps a hard jet of water across the lenses; spray bursts into the air and the front "
     "rank flinches back, shielding their cameras, one hat knocked sideways. Camera: low angle from inside the "
     "yard, slow motion, the water crossing the frame in sheets. Real motion: water jet and spray, flashing "
     "strobes, recoiling bodies, hair and cloth whipping. No readable text, no logos."),

    ("S24", 142, 7, "中景，全家围着电视机", ["residents"], "real",
     "A different Japanese living room that evening: a family of four sits around a low table facing a CRT "
     "television, its pale flickering light washing their faces. On the screen only an unreadable blurred "
     "image of a garden and a hose. The two children sit forward, curious; the parents frown, the father's "
     "hand flat on the table, the mother's fingers pressed to her mouth. Tea and a plate of watermelon are "
     "forgotten in front of them. Camera: medium shot from the side of the television, slow drift around the "
     "family, the screen glow moving across their faces. Real motion: flickering light, blinking, a child "
     "shifting, steam from tea. No readable text on the screen."),

    ("S25", 149, 6, "中景缓慢推近，回头一看", ["masumi", "detectives"], "real",
     "The front gate of the Hayashi house, dusk, patrol-car beacons painting the wall red and blue. Two "
     "detectives in dark suits stand on either side of Masumi; one holds up a folded document whose page is "
     "blank. Behind them the patrol car is plain, with no lettering and no number plate. She is led out toward "
     "the lane, then stops and looks back over her shoulder at the house - chin up, expression stubborn and "
     "eerily calm - and her lips move once, silently, as if repeating a short sentence. The camera stays on "
     "her face as the others blur. Camera: medium shot, slow push in, shallow focus. Real motion: walking, "
     "turning the head, lips moving, coat and hair in the wind, beacons turning. No readable text."),

    ("S26", 155, 6, "缓慢环绕法庭", ["court", "masumi"], "real",
     "A Japanese district courtroom in winter 2002, everything cold grey and dark wood. The judge in a black "
     "robe sits on the raised bench, head slightly bowed over a document, reading in a low even voice; the "
     "clerk beside the bench keeps still. In the well of the court Masumi stands with her hands folded, head "
     "down, short curly hair catching the flat overhead light; the gallery behind is a row of motionless "
     "shoulders. Camera: slow orbit from the bench across the empty floor to her lowered head. Real motion: a "
     "page turning, a slow blink, shoulders breathing, dust in the light. No readable text, no gavel strike in "
     "this shot."),

    ("S27", 161, 6, "中景，天平摆动", ["court"], "diagram",
     "A monumental three-dimensional balance scale in cold dark space. On the left pan rest a glowing spectral "
     "curve and three small faceless witness silhouettes; on the right pan lie several empty blank frames and "
     "a hollow outline of a question-shaped void. The beam tilts one way, then the other, the pans trembling, "
     "never settling level; dust drifts through a single beam of light. Camera: medium shot at eye level with "
     "the beam, slowly orbiting as it swings. Real motion: swinging beam, trembling chains, drifting dust, "
     "pulsing curves. Symbolic only; no readable letters, no numbers, no readable text."),

    ("S28", 167, 5, "航拍转特写，判决书与红印", ["court"], "real",
     "The Supreme Court building in Tokyo under a flat overcast sky: a tall pale modernist slab with long "
     "vertical fins, wet paving in front, bare trees, a few suited figures tiny at the steps. Camera: aerial "
     "descent toward the facade, then a rapid move to a close-up of a single sheet of paper - blank and "
     "unreadable - lifted and turned by the wind on an outdoor ledge. A heavy circular red seal descends onto "
     "the paper in slow motion, pressing flat, leaving only a solid red disc with no characters. Real motion: "
     "clouds sliding, paper fluttering, the seal pressing down. No readable text, no letters, no numbers."),

    ("S29", 172, 8, "缓慢推近，淡入淡出", [], "real",
     "A death-row cell interior at dusk: bare concrete wall, a narrow barred window high up, one thin shaft of "
     "warm sunset light falling across the bars and the floor. On the narrow sill stands a single white flower "
     "in a small cup, its petals moving slightly in the draught. The light slowly brightens until the frame "
     "begins to wash out toward white at the edges. Camera: very slow push toward the window and the flower, "
     "settling into a stable final frame with clean negative space in the upper half for a title added later. "
     "Real motion: dust in the beam, petals trembling, the light breathing and blooming toward white. The "
     "generated clip contains no lettering at all; every title is added in post."),
]

# ---------------------------------------------------------------- 一镜一句旁白（29 条）
# 每条都写进分镜：旁白 = 字幕，起止与镜头一致；只允许加速，不允许慢放。
NARRATION = {
    "S01": "1998年夏，日本和歌山，一场社区夏祭。",
    "S02": "一锅咖喱，让四个人再也没有回家。",
    "S03": "7月25日，园部地区的主妇们，在车库里架起大锅。",
    "S04": "切土豆、搅咖喱、说说笑笑，汗顺着额头一直往下流。",
    "S05": "中午，孩子、老人、刚下班的邻居，排队来领饭。",
    "S06": "夕阳很好，蝉声很响，没有人察觉任何异常。",
    "S07": "没过多久，一位老人放下勺子，捂着额头说，头晕。",
    "S08": "紧接着，人们一个接一个蹲下，有人大喊：咖喱，停！",
    "S09": "救护车一辆接一辆开进窄街，红灯在墙上打转。",
    "S10": "医生起初以为，这只是夏天的食物中毒。",
    "S11": "可症状越来越重：六十七人中毒，四个人没能救回来。",
    "S12": "检验结果出来了：让所有人中毒的，是砒霜，也就是砷。",
    "S13": "所以这不是食物中毒，这是一次蓄意的投毒。",
    "S14": "全城震惊。警方在那口锅周围拉起警戒线。",
    "S15": "警方要查清楚：谁靠近过那口锅？谁有机会一个人留下？",
    "S16": "那天进过车库的每一个人，都被重新排查一遍。",
    "S17": "法院后来认定：有一位主妇，曾独自看管过一段时间。",
    "S18": "她叫林真须美，那年37岁，就住在这条街上。",
    "S19": "她和丈夫健治，做过保险推销和灭白蚁，都碰过砷。",
    "S20": "警方在她家搜出一包白色粉末；检验之后，是同样的砷。",
    "S21": "案发之前那十年，夫妻俩多次靠保险诈骗拿到钱。",
    "S22": "检方说：家里的砷，和锅里的砷，成分相同。",
    "S23": "记者围住她家；她举起水管朝镜头喷水，水花溅在镜片上。",
    "S24": "这一幕传遍全国。很多人看完，心里已经先判了她。",
    "S25": "同年12月，她因这锅咖喱被捕；她说：我没有做。",
    "S26": "2002年，和歌山地方法院，判处她死刑。",
    "S27": "没有动机，没有直接证据；法院靠的是鉴定和证词。",
    "S28": "2009年，最高法院维持死刑；辩方质疑证据。",
    "S29": "她至今在狱中喊冤；第三度再审还在审理。你觉得，凶手是她吗？",
}

# ---------------------------------------------------------------- 九段（由镜头推导，只用于章节统计）
CHAPTER_TITLES = [
    ("N01", "黄金3秒钩子"),
    ("N02", "祭典"),
    ("N03", "突变"),
    ("N04", "砒霜"),
    ("N05", "谁靠近过那口锅"),
    ("N06", "家中的砒霜与保险单"),
    ("N07", "水管与逮捕"),
    ("N08", "判决与争议"),
    ("N09", "余音"),
]

SOURCES = [
    {
        "id": "ja-wikipedia",
        "title": "Wikipedia（日文）「和歌山毒物カレー事件」",
        "url": "https://ja.wikipedia.org/wiki/%E5%92%8C%E6%AD%8C%E5%B1%B1%E6%AF%92%E7%89%A9%E3%82%AB%E3%83%AC%E3%83%BC%E4%BA%8B%E4%BB%B6",
        "supports": "1998年7月25日午后、和歌山市园部第14自治会夏祭；67人急性砷中毒、4人死亡"
                    "（自治会长64岁、副会长53岁、小学四年级男生10岁、高一女生16岁）；"
                    "1998年10月4日以保险金诈骗等嫌疑逮捕、12月9日以咖喱事件杀人嫌疑再逮捕、12月29日起诉；"
                    "第一审2002年12月11日和歌山地裁死刑、2005年6月28日大阪高裁控诉驳回、"
                    "2009年4月21日最高裁上告驳回、5月死刑确定。",
    },
    {
        "id": "jiji-photo",
        "title": "时事通信「和歌山毒物カレー事件（1998年7月）」写真特集",
        "url": "https://www.jiji.com/jc/d4?p=wcj725&d=d4_topics",
        "supports": "1998年7月25日、和歌山市园部的空地举办自治会夏祭，咖喱锅被混入剧毒砷，"
                    "包括一名小学四年级男生在内的4人急性砷中毒死亡、63人出现中毒症状；"
                    "1998年10月以保险金诈骗嫌疑逮捕林真须美与丈夫、12月以咖喱事件杀人嫌疑再逮捕；"
                    "2009年最高裁死刑确定，此后持续请求再审。",
    },
    {
        "id": "ntv-2025",
        "title": "日本テレビNEWS NNN（2025-11-13）「林真須美死刑囚の再審請求 最高裁が裁判のやり直しを認めない決定」",
        "url": "https://news.ntv.co.jp/category/society/26229e58ba844f1cb3b10f867901b347",
        "supports": "2025年11月11日付最高裁决定驳回特别抗告，第2次再审请求不被认可；"
                    "此前2021年、2022年两次提出再审请求，和歌山地裁与大阪高裁均未准许。",
    },
    {
        "id": "nhk-2025",
        "title": "NHK NEWS（2025-11-13）「和歌山毒物カレー事件 林真須美死刑囚の再審認めず 最高裁」",
        "url": "https://news.web.nhk/newsweb/na/na-k10014975771000",
        "supports": "再次确认二审维持死刑、最高裁未准许再审的事实性结论。",
    },
    {
        "id": "kyodo-2025",
        "title": "共同通信（2025-01-29，秋田魁新报等转载）「林真須美死刑囚の再審再び認めず　毒物カレー事件、大阪高裁」",
        "url": "https://www.sakigake.jp/news/article/20250129CO0059/",
        "supports": "大阪高裁2025年1月27日决定驳回第2次再审请求的即时抗告。",
    },
    {
        "id": "tbs-2025",
        "title": "TBS NEWS DIG（2025-11-14）「林真須美死刑囚の2回目の再審請求 最高裁が特別抗告を棄却」",
        "url": "https://newsdig.tbs.co.jp/articles/-/2288768?display=1",
        "supports": "第2次再审请求在2023年1月和歌山地裁驳回、2025年1月大阪高裁驳回、"
                    "2025年11月最高裁特别抗告弃却；第3次再审请求于2024年2月向和歌山地裁提出、仍在审理。",
    },
    {
        "id": "jiken-db",
        "title": "事件データベース「和歌山毒物カレー事件」判決ポイント整理",
        "url": "https://jiken-db.com/%E3%80%90%E6%A6%82%E8%A6%81%E3%80%91%E5%92%8C%E6%AD%8C%E5%B1%B1%E6%AF%92%E7%89%A9%E3%82%AB%E3%83%AC%E3%83%BC%E4%BA%8B%E4%BB%B6%E3%81%A8%E3%81%AF%E4%BD%95%E3%81%A0%E3%81%A3%E3%81%9F%E3%81%AE%E3%81%8B/",
        "supports": "确定判决的依据为：家中发现同种亚砷酸、毛发检出砷、独占锅边的机会与目击证词；"
                    "动机到最后未查明，最高裁认为动机未查明不影响犯人性认定。"
                    "保险金诈骗相关事件在同一裁判中一并审理。",
    },
    {
        "id": "lgcj-2016",
        "title": "「99.9」影评与判决整理（律师视野的事实梳理）",
        "url": "https://lgcj.tokyo/%E3%80%8E99-9-%E5%88%91%E4%BA%8B%E5%B0%82%E9%96%80%E5%BC%81%E8%AD%B7%E5%A3%AB-the-movie%E3%80%8F%E3%82%92%E8%A6%B3%E3%81%A6%E3%82%82%E3%81%86%E4%B8%80%E5%BA%A6%E8%80%83%E3%81%88%E3%82%8B%E5%92%8C/",
        "supports": "四名死者构成（自治会长64岁、副会长53岁、高一女生16岁、小学四年级男生10岁）；"
                    "无目击咖喱投毒过程、无直接证据、被告一贯否认的审判事实；第2次再审请求的核心主张。",
    },
]

PRINCIPLES = [
    "全片29个镜头全部由 Agnes Video 2.5 Flash 生成连续运动片段（720P 源片，后期放大到 "
    "1920×1080 · 24fps），禁止静态图加推拉代替；每个镜头只出现一次。",
    "每条提示词自动以【STYLE】开头、以【NEGATIVE】结尾；出现人物时自动拼接对应【角色设定】；"
    "2.5 Flash 不接受独立 negative_prompt 字段，约束因此写在提示词正文里。",
    "不出现遗体、伤口、血腥、呕吐特写或受害儿童本人；受害过程只用打翻的桌椅、救护车灯光、"
    "一双小鞋等间接画面表现（S08、S09、S11）。",
    "真实人物一律为风格化形象，不复制任何真实肖像；林真须美只在 S16、S19、S23、S25、S26 出现，"
    "且不给出可辨认的真人相貌。",
    "案件争议一律中立：判决写『法院认定』『检方说』『辩方质疑』，不替任何一方下结论，"
    "不对凶手身份作肯定陈述。",
    "『那口大锅』与『红色灯笼』是全片贯穿的视觉母题：S01–S06 温暖，S14 回到冷掉的锅，"
    "后半段红转为警戒与血色，S29 只剩一线夕阳。",
    "色彩随时间转冷：前半段暖橙灯笼光，后半段冷蓝灰；抽象示意图（S13、S21、S22、S27）"
    "使用独立 STYLE 变体，与写实复原镜头明确区分，不呈现任何比对结果或身份结论。",
    "旁白一镜一句：每镜一条独立配音与一条同起止字幕；保留自然语速，必要时最多加速 1.55 倍，"
    "禁止慢放填满时长。",
    "所有画面为 AI 动画情景重现；片中出现的文书、屏幕、证物均无可读文字，标题与字幕全部后期叠加。",
]

PRESENTATION = {
    "cover": {
        "layout": "16:9；左侧冒热气的大锅特写（S02 帧），右侧红色灯笼与黄色警戒线（S01 / S14 帧），"
                  "中央竖排金色大字；标题左下、副题其下",
        "text": "一锅咖喱",
        "subtext": "四条人命 · 1998 和歌山",
        "style": "金色粗体字、黑色描边；由 S02 大锅与 S14 警戒线两帧合成，字为后期绘制，"
                 "不是静态图替代视频",
    },
    "end_title": "和歌山毒咖喱事件",
    "end_subtitle": "和歌山 · 1998 · 至今争议",
    "end_note": "真实案件改编 · AI动画情景复原",
    "end_question": "你觉得，凶手是她吗？",
    "highlight_keywords": [
        "1998年", "和歌山", "夏祭", "一锅咖喱", "四个人", "7月25日", "园部", "大锅", "咖喱",
        "汗", "排队", "夕阳", "异常", "头晕", "一个接一个", "咖喱，停", "救护车", "红灯",
        "食物中毒", "六十七人", "中毒", "砒霜", "砷", "蓄意的投毒", "全城震惊", "警戒线",
        "那口锅", "机会", "重新排查", "主妇", "看管", "林真须美", "37岁", "保险推销", "灭白蚁",
        "白色粉末", "保险诈骗", "成分相同", "记者", "水管", "喷水", "全国", "先判了她",
        "12月", "被捕", "我没有做", "2002年", "和歌山地方法院", "死刑", "动机", "直接证据",
        "鉴定", "证词", "2009年", "最高法院", "辩方", "狱中", "再审", "凶手",
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
        {"at": 0, "name": "蝉鸣、远处祭典鼓声与笛声、灯笼纸摩擦，温暖", "kind": "music_sfx"},
        {"at": 5, "name": "锅里的咕嘟声、蒸汽、一阵突入的冷风（灯笼同时摇晃）", "kind": "sfx"},
        {"at": 10, "name": "祭典鼓点与笛声、切菜与搅拌、笑声", "kind": "music_sfx"},
        {"at": 30, "name": "鼓声渐弱，蝉声被拉长，低频弦乐第一次进入", "kind": "music_sfx"},
        {"at": 35, "name": "勺子碰碗、人群骚动、椅子刮地", "kind": "sfx"},
        {"at": 49, "name": "救护车警笛由远及近、无线电、奔跑脚步", "kind": "music_sfx"},
        {"at": 60, "name": "医院空调低鸣、心电监护提示音、极轻的耳鸣", "kind": "sfx"},
        {"at": 67, "name": "仪器自检声、打印机、曲线飙升的高频提示", "kind": "sfx"},
        {"at": 85, "name": "悬疑钢琴与低频脉冲、白板马克笔、翻页", "kind": "music_sfx"},
        {"at": 110, "name": "风扇、蝉声、纸张翻动、火柴与香烟", "kind": "music_sfx"},
        {"at": 135, "name": "快门连拍、闪光灯充电、水管喷水、水花落地", "kind": "sfx"},
        {"at": 155, "name": "庄严大提琴、木槌轻响、法庭的安静", "kind": "music_sfx"},
        {"at": 172, "name": "大提琴单音收尾，最后 0.8 秒淡出至静音", "kind": "music_sfx"},
    ],
    "douyin_title": "一场夏日祭典，一锅咖喱，四个人再也没回家",
    "hashtags": ["#真实事件", "#和歌山毒咖喱", "#日本", "#悬疑", "#未解之谜", "#3D动画"],
    "release_intro": (
        "1998年7月25日，日本和歌山市园部，自治会的夏祭。\n\n"
        "主妇们一早在车库里架起大锅煮咖喱，中午，孩子、老人、刚下班的邻居排队来领饭。"
        "几个小时后，67人急性砷中毒，4人死亡，其中有一个10岁的男孩和一个16岁的女生。\n\n"
        "警方查的不是「谁恨谁」，而是「谁靠近过那口锅」。1998年12月，住在同一条街的主妇林真须美被捕；"
        "2002年和歌山地裁判她死刑，2009年最高裁维持。\n\n"
        "她没有认罪。法院没有查明动机，也没有直接证据，靠的是「家里的砷与锅里的砷成分相同」、"
        "毛发检出砷，以及「她曾独自看管锅」的证词。辩方一直质疑鉴定方法与证词可靠性。\n\n"
        "2024年2月，第三次再审请求提出，目前仍在和歌山地裁审理。她至今在狱中喊冤。\n\n"
        "画面为AI动画情景重现，不出现遗体、血腥与受害儿童；真实人物均为风格化形象。"
        "案件争议部分只陈述各方主张，不代表本片结论。"
    ),
}

REFERENCE_IMAGES = [
    {"file": "reference/01-hayashi-masumi.png",
     "description": "林真须美定稿（风格化形象，非真实肖像）：37岁、烫过的短卷发、棱角分明的眉、"
                    "碎花短袖家居上衣；表情从爽朗到倔强的两种状态"},
    {"file": "reference/02-hayashi-kenji.png",
     "description": "林健治定稿（风格化形象）：五十出头、偏瘦微驼、旧夹克与工作衬衫、指间夹烟、"
                    "神情疲惫回避"},
    {"file": "reference/03-sonobe-street-festival.png",
     "description": "园部街区与夏祭定稿：窄街、二层小楼、电线杆与电线、红色灯笼串、彩旗、"
                    "折叠桌与塑料凳、暖橙夕阳"},
    {"file": "reference/04-garage-big-pot.png",
     "description": "核心场景与母题定稿：车库里的巨大铝锅、红色灯笼倒影、蒸汽、"
                    "围裙主妇与切菜板"},
    {"file": "reference/05-hospital-night.png",
     "description": "医院急诊定稿：冷白日光灯长走廊、绿色墙面、担架、值班医生与护士、"
                    "无文字的挂钟"},
    {"file": "reference/06-lab-and-report.png",
     "description": "实验室定稿：冷灰钢制台面、老式分析仪与CRT屏幕、白大褂研究员、"
                    "屏幕上的抽象曲线（无可读文字）"},
    {"file": "reference/07-press-and-court.png",
     "description": "记者与法庭定稿：1998年肩扛大摄像机与闪光灯的记者群、水管喷水；"
                    "2002年冷灰木质法庭、黑袍法官与被告席"},
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
        seed = CHARACTER_SEEDS[characters[0]] if len(characters) == 1 else 19980701 + index
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
            "purpose": prompt.split(".")[0].strip()[:110],
            "seed": seed,
            "seconds": duration,
            "aspect": "16:9",
            "source_size": "720P",
            "transition_out": "同段内硬切；段与段之间 0.3 秒叠化——前半段收在红灯笼的暖光里，"
                              "后半段收在冷蓝雾气里；不改动旁白时间轴。",
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
        "fps": FPS,
        "model": "agnes-video-2.5-flash",
        "source_size": "720P",
        "branch": BRANCH,
        "style_prefix": STYLE_PREFIX,
        "style_rumor_prefix": STYLE_DIAGRAM_PREFIX,
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
            "dramatic_pause_after": {"S02": 0.4, "S25": 0.4},
        },
        "sources": SOURCES,
        "presentation": PRESENTATION,
        "reference_images": REFERENCE_IMAGES,
        "fact_boundary": [
            "1998年7月25日，和歌山市园部地区第14自治会举办夏祭，现场提供的咖喱被混入亚砷酸"
            "（三氧化二砷，即砒霜的主要成分）；67人急性砷中毒，4人死亡。",
            "四名死者为：自治会长（64岁）、副会长（53岁）、小学四年级男生（10岁）、"
            "高一女生（16岁）；片中不出现姓名、不出现儿童本人，只用间接画面与数字表述。",
            "1998年10月4日，林真须美与丈夫林健治因保险金诈骗等嫌疑被逮捕；12月9日，她因咖喱事件"
            "的杀人、杀人未遂嫌疑被再逮捕，12月29日被起诉。",
            "2002年12月11日和歌山地裁判处死刑；2005年6月28日大阪高裁驳回控诉；"
            "2009年4月21日最高裁驳回上告，同年5月死刑确定。",
            "确定判决的主要依据是：家中发现同种亚砷酸、毛发检出砷、以及她曾独自看管咖喱锅的"
            "机会与目击证词；动机到最后没有被查明。检方与法院的认定写在『法院认定』『检方说』里，"
            "不代表本片结论。",
            "辩方与部分研究者质疑砷的鉴定方法与纸杯样本的可靠性，主张可能存在第三人；"
            "第2次再审请求于2023年1月被和歌山地裁驳回、2025年1月被大阪高裁驳回、"
            "2025年11月11日最高裁驳回特别抗告。",
            "第3次再审请求于2024年2月向和歌山地裁提出，截至本片制作时仍在审理；"
            "她至今在押于大阪拘置所，死刑未执行。",
            "保险金诈骗事件中，丈夫林健治另案被判处有期徒刑6年（2000年，2005年出狱）；"
            "片中只作事实陈述，不对其人格作评价。",
            "所有画面为AI动画情景重现，不是历史影像、不是新闻画面、不是警方证物照片；"
            "真实人物均为风格化形象，非真实肖像。",
        ],
    }


def write_screenplay(story: dict) -> None:
    lines = [
        f"# {story['title']}",
        "",
        f"三分钟横屏悬疑动画短片 · 1920×1080 · {story['fps']}fps · 180秒 · "
        "29 个 Agnes Video 2.5 Flash 动态镜头 · 一镜一句中文旁白",
        "",
        "> 画面为 AI 动画情景重现，不是历史影像；文书与屏幕为 3D 示意性复原，不是警方原始材料。",
        "> 不出现遗体、伤口、血腥、呕吐或受害儿童本人；真实人物均为风格化形象。",
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
        "- 生成：Agnes Video 2.5 Flash，720P 源片，61 秒共享节流，断点续跑；后期放大到 1920×1080。",
        "- 配音：沉稳磁性成熟男声（voice-00）；一镜一句、字幕同起止；只加速（≤1.55×），不慢放。",
        "- 字幕：白色黑边、底部安全区、关键词金色放大；日期与案件信息与公开资料一致。",
        "- 音乐：原创程序合成（祭典鼓点与笛声 → 低音弦乐 → 悬疑钢琴 → 庄严大提琴）；旁白下压约 −18dB。",
        "- 音效：蝉鸣、祭典鼓、锅里的咕嘟声、救护车警笛、仪器提示音、快门与水花、法庭木槌。",
        "- 片尾：S29 狱中窗口的白花，后期叠加金色片名『和歌山毒咖喱事件』与副题"
        "『和歌山 · 1998 · 至今争议』，最后 0.8 秒淡出至静音。",
        "- 封面：左侧 S02 大锅、右侧 S14 警戒线与灯笼；主标题『一锅咖喱』，副题『四条人命 · 1998 和歌山』。",
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
            "voice_description": "沉稳磁性成熟男声；讲故事语气，句尾收得轻，像真实案件纪录片",
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
        f"**规格：** 1920×1080 · 16:9 横屏 · {story['fps']}fps · 180 秒 · "
        "29 个 Agnes Video 2.5 Flash 动态镜头\n\n"
        "**核心钩子：** 一场社区夏祭，一锅咖喱，四个人再也没回家；一锅咖喱的位置，"
        "把一位主妇送上死刑台\n\n"
        "## 四列分镜表\n\n"
        "| 镜号 | 时间 | 口播（=字幕） | 画面 | 运镜 |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## 声音设计\n\n| 时间 | 声音 |\n|---|---|\n" + events
        + "\n\n## 事实边界\n\n"
        "- 时间、地点、中毒人数、四名死者构成、逮捕与审判时间线均以公开资料为准。\n"
        "- 确定判决的认定用『法院认定』『检方说』转述；再审进展标注日期与裁决机关。\n"
        "- 不对凶手身份、动机下结论；不对任何一方作人格评价。\n"
        "- 不出现遗体、伤口、血腥、呕吐或受害儿童本人；画面为AI动画情景重现。\n\n"
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
    worst = max(story["shots"], key=lambda s: visible(s["narration"]) / (s["duration"] - 0.08))
    print(f"densest line: {worst['id']} "
          f"{visible(worst['narration'])/(worst['duration']-0.08):.2f} chars/s")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""唯一内容源：《汽车旅馆连环命案：AI警告过她》

运行 ``python3 production/motel2026/build_story.py`` 会写出 story.json、screenplay.md、
audio/manifest.json、抖音脚本.md 与抖音发布文案.md。30 个镜头全部是 Agnes Video 2.5 Flash
（720P 源片，后期放大到 1920×1080 · 24fps）生成的连续运动片段；旁白一镜一句，字幕与配音同起止。

事实口径（按用户脚本）：案件一审已判，双方均已上诉；嫌疑人称“金某”；法院认定写“法院认为”；
检方口径写“检方要求”。片中不出现药物名称、药片、剂量、调配细节，不出现遗体、血腥；
受害者只以背影、剪影与白菊花出现；手机界面一律抽象线条，不出现可读文字。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
TITLE = "汽车旅馆连环命案：AI警告过她"
FILM_NAME = "汽车旅馆连环命案_AI警告过她_三分钟_带声音.mp4"
BRANCH = "arena/4d042fa6-desktop-tutorial"
FPS = 24

# ---------------------------------------------------------------- 全局 STYLE / NEGATIVE
STYLE_PREFIX = (
    "【STYLE】Cinematic-quality 3D animated documentary reenactment, Seoul, South Korea, "
    "2025-2026: a neon-lit motel district in Gangbuk-gu at night, purple-red neon signs "
    "reflecting on wet asphalt, cold blue smartphone screen light contrasting warm amber "
    "practical light, low saturation, heavy shadows, gentle film grain, shallow depth of "
    "field, long-lens compression. Realistic building proportions, finely detailed concrete, "
    "glass, metal, fabric and skin materials, volumetric haze, soft ambient occlusion. "
    "Horizontal 16:9 widescreen composition, subject near a third line, full horizontal "
    "width, lower sixth kept visually quiet for subtitles. Every clip is true continuous 3D "
    "animation with visible natural movement - walking, turning heads, blinking, breathing, "
    "hands at work, curtains swaying, neon flickering, rain dripping, camera parallax - never "
    "a still image with a push-in. All characters are stylized fictional actors, never the "
    "likeness of a real person. "
)

STYLE_DIAGRAM_PREFIX = (
    "【STYLE｜概念示意｜抽象可视化】Clean cinematic 3D information graphic on a deep charcoal "
    "background, restrained cold blue and muted gold palette with a single red accent, fine "
    "volumetric haze, soft edges, elegant shallow depth of field and subtle film grain; "
    "deliberately abstract and clearly a conceptual diagram, not a photograph of any device. "
    "Horizontal 16:9 widescreen composition with generous negative space and the lower sixth "
    "kept quiet for subtitles. Everything breathes with real continuous motion - lines draw "
    "themselves, nodes pulse slowly, particles drift, the camera moves through depth - never "
    "a flat static slide. Absolutely no readable letters, numbers, names or logos anywhere "
    "in frame. "
)

NEGATIVE_PROMPT = (
    "【NEGATIVE】cartoon, chibi, anime, exaggerated expressions, oversaturated colours, "
    "readable text, subtitles, captions, watermark, logo, gibberish lettering, drug names, "
    "pills, medicine bottles, syringes, blood, gore, wound, corpse, dead body, violence in "
    "progress, nudity, deformed hands, extra fingers, extra limbs, facial collapse, distorted "
    "anatomy, plastic skin, mannequin faces, wrong building structure, low resolution, "
    "flicker, style drift, vertical framing, letterbox black bars inside the frame, frozen "
    "frame, slideshow, still image with artificial zoom, jump scare, realistic likeness of a "
    "real person, heavy lens flare."
)

# ---------------------------------------------------------------- 角色设定（跨镜逐字复用）
CHARACTERS = {
    "kim": (
        "【角色设定｜金某】Kim, a fictionalized stylized Korean woman in her early twenties, "
        "black straight medium-length hair, plain ordinary face, calm and slightly empty "
        "expression, eyes rarely meeting others; wearing a grey hooded jacket and jeans. "
        "Keep her hairstyle, build, clothing colours and facial proportions identical in "
        "every shot. Never beautified, never glamorous, never a portrait or likeness of any "
        "real person. "
    ),
    "boyfriend": (
        "【角色设定｜男友】A fictionalized stylized Korean man in his twenties, short hair, "
        "dark jacket over a white T-shirt, relaxed and easygoing presence. Keep his "
        "hairstyle, build and clothing identical in every shot. Never a portrait or likeness "
        "of any real person. "
    ),
    "victimA": (
        "【角色设定｜受害者甲】A fictionalized stylized Korean man in his twenties, black "
        "short hair, black jacket and jeans, easy smile; seen only from behind, in silhouette "
        "or in three-quarter back view, face never clearly visible. Keep his build and "
        "clothing identical in every shot. Never a portrait or likeness of any real person. "
    ),
    "victimB": (
        "【角色设定｜受害者乙】A fictionalized stylized Korean man in his twenties, brown "
        "short hair, grey sweatshirt and track pants, friendly presence; seen only from "
        "behind, in silhouette or in three-quarter back view, face never clearly visible. "
        "Keep his build and clothing identical in every shot. Never a portrait or likeness "
        "of any real person. "
    ),
    "cleaner": (
        "【角色设定｜旅馆清洁工】A fictionalized stylized Korean woman of 55, short hair, "
        "motel uniform with an apron, pushing a cleaning cart, tired and plain presence. "
        "Keep her hairstyle, build and uniform identical in every shot. Never a portrait or "
        "likeness of any real person. "
    ),
    "detective": (
        "【角色设定｜江北警察署刑警】Fictionalized Korean detectives in their forties, dark "
        "jackets over shirts, sharp yet tired eyes, restrained and professional; no readable "
        "insignia or badge numbers. Keep their clothing and presence identical in every "
        "shot. Not portraits of real officers. "
    ),
    "forensic": (
        "【角色设定｜数字取证员】A fictionalized stylized Korean man in his thirties, thin "
        "rimless glasses, white shirt with a dark vest, focused and calm, with a laptop and "
        "cables beside him. Keep his glasses, hairstyle and clothing identical in every "
        "shot. Never a portrait or likeness of any real person. "
    ),
    "court": (
        "【角色设定｜法官检察官律师】Fictionalized Korean court figures aged 40 to 60: a "
        "judge in a black robe with a stern expression, a prosecutor in a dark suit with a "
        "firm gaze, a defence lawyer in a dark suit with a focused expression. Keep their "
        "robes, suits and presence identical in every shot. Not portraits of real people. "
    ),
    "family": (
        "【角色设定｜家属】Several fictionalized Korean family members in black clothing, "
        "grieving but restrained, seen in medium shots and from behind. Keep their black "
        "clothing and restrained presence identical in every shot. Not portraits of real "
        "people. "
    ),
    "cafe": (
        "【角色设定｜咖啡馆年轻人】Several fictionalized Korean young people in their "
        "twenties sitting in a cafe, holding smartphones, varied expressions. Keep their "
        "age range and casual clothing identical in every shot. Not portraits of real "
        "people. "
    ),
}
CHARACTER_SEEDS = {
    "kim": 20260101,
    "boyfriend": 20260102,
    "victimA": 20260103,
    "victimB": 20260104,
    "cleaner": 20260105,
    "detective": 20260106,
    "forensic": 20260107,
    "court": 20260108,
    "family": 20260109,
    "cafe": 20260110,
}

# ---------------------------------------------------------------- 30 镜（4–9 秒／镜，合计 180 秒）
# (镜号, 起始, 时长, 运镜, 角色, 风格变体, 提示词)
SHOT_ROWS = [
    ("S01", 0, 5, "长焦推近", [], "real",
     "Night in the motel district of Gangbuk-gu, Seoul, after rain. The camera pushes in "
     "slowly with a long lens from across the street toward a motel entrance: wet asphalt "
     "reflects purple-red neon, a vacancy sign flickers with abstract glowing shapes and no "
     "letters, a fabric curtain sways in the wind, distant headlights slide past. Camera: "
     "one continuous long-lens push-in, slow and steady. Real motion: curtain swaying, "
     "neon flickering, water dripping, travelling headlights. No people, no readable text."),

    ("S02", 5, 5, "大特写，缓慢推近", ["kim"], "real",
     "Extreme close-up of a smartphone screen in a dark room: an abstract chat interface "
     "made of soft lines and bubbles with no readable words, a single red exclamation "
     "warning icon lights up, then a young woman's fingertip swipes it away; cold blue "
     "screen light falls on half of her calm face, her eyes show no reaction. Camera: "
     "extreme close-up with a slow push-in. Real motion: icon pulsing, fingertip sliding, "
     "blinking, breathing. No readable text, no letters, no numbers."),

    ("S03", 10, 7, "中景，缓慢推近杯子", ["kim", "boyfriend"], "real",
     "December 2025, a small apartment in Gangbuk-gu at night: a young couple sit at a "
     "small dining table talking, two clean glass cups on the table, warm lamplight, night "
     "city outside the window; the woman smiles and hands over a glass, the camera settles "
     "on fine bubbles rising in the glass. Camera: medium shot with a slow push toward the "
     "glass. Real motion: talking, smiling, hand passing the glass, bubbles rising, "
     "breathing. No medicine, no readable text."),

    ("S04", 17, 7, "低机位，缓慢推近", ["kim"], "real",
     "The same apartment, quiet and still: a man lies slumped on a sofa seen only from the "
     "side and behind with his face never shown, a glass has rolled onto the carpet, the "
     "table lamp still glows; the woman stands beside him with a calm expression, lowers "
     "her head and picks up her phone. Camera: low angle with a slow push-in. Real motion: "
     "lamp glow breathing, curtain moving, the woman shifting weight and lifting the phone, "
     "breathing. Restrained, no violence shown, no readable text; any background lights are heavily blurred abstract glows with no letters."),

    ("S05", 24, 6, "长走廊，缓慢推近", ["kim"], "real",
     "A hospital emergency corridor under cold white light: a stretcher trolley rushes past "
     "in the foreground, an emergency room door opens and closes; the woman sits alone on a "
     "long bench, head lowered over her phone, cold screen light on her face, no visible "
     "grief. Camera: slow push along the long corridor. Real motion: trolley wheels, door "
     "moving, footsteps, blinking, breathing. Interior corridor only, no street, no storefronts; no readable text, no signage letters, no Korean characters."),

    ("S06", 30, 5, "大特写", ["kim"], "diagram",
     "Abstract smartphone screen in darkness: soft chat lines and bubbles with no readable "
     "words, a fingertip types a short line shown only as abstract strokes, sends it, and "
     "a single red question icon pops above the bubbles; the palette cools toward blue. "
     "Camera: extreme close-up, locked with a very slow push. Real motion: strokes drawing "
     "themselves, bubbles appearing, icon pulsing, light cooling. No readable text, no "
     "readable letters, no numbers."),

    ("S07", 35, 7, "中景，缓慢推近", ["kim", "victimA"], "real",
     "28 January 2026, 9:30 pm, a motel entrance in Suyu-dong: a fabric curtain parts, a "
     "man and a woman walk in side by side, the man seen from behind and in three-quarter "
     "back view talking with an easy smile, the woman with her head lowered; warm light "
     "from the front desk window, a key card is handed out. Camera: medium shot with a "
     "slow push-in. Real motion: curtain parting, walking, head turning, card passing "
     "hands. No clear faces of the man, no readable text."),

    ("S08", 42, 7, "走廊对称构图，缓慢推近门", ["kim", "victimA"], "real",
     "A long motel corridor under purple-red light, carpeted, doors on both sides in "
     "symmetrical composition: two figures seen only from behind walk to a door, a key "
     "card beeps, a small green light glows, the door opens and then closes softly; the "
     "camera holds on the closed door. Camera: symmetrical corridor with a slow push "
     "toward the door. Real motion: walking, card tapping, light changing, door closing. "
     "No clear faces, no readable text."),

    ("S09", 49, 6, "固定机位，延时", [], "real",
     "Inside an empty motel room: purple-red neon seeps through a curtain gap, two clean "
     "glasses on a table, a neatly made bed, cold and warm light contrasting; a wall clock "
     "with an unmarked face spins quickly through two hours in time-lapse while only light "
     "and shadow change, no people in frame. Camera: locked-off wide shot. Real motion: "
     "clock hands spinning, neon flickering, curtain breathing, light shifting. No "
     "readable text, no numbers."),

    ("S10", 55, 5, "低机位，背影跟拍", ["kim"], "real",
     "Deep night at the motel entrance: a fabric curtain is lifted, a woman walks out "
     "alone, pulls up her hood, walks at an unhurried pace and disappears into the wet "
     "street; neon reflections break into pieces on the ground. Camera: low tracking shot "
     "from behind. Real motion: curtain lifting, walking, hood settling, puddle ripples, "
     "neon shimmering. All signs are heavily blurred abstract glowing shapes with no letters, no Korean characters, no text."),

    ("S11", 60, 7, "中景，手持", ["cleaner"], "real",
     "The next day, a motel corridor: a cleaner pushes a small cart, knocks on a door with "
     "no answer, opens it with a master card, freezes in the doorway as a towel slips from "
     "her hand, then turns and runs; the picture cuts to black before any interior is "
     "shown. Camera: handheld medium shot. Real motion: cart rolling, knocking, towel "
     "falling, turning and running. Interior corridor only, no exterior, no neon signs; no interior shown, no readable text, no Korean characters."),

    ("S12", 67, 7, "广角，缓慢推近", ["detective"], "real",
     "Police lights flash at a motel entrance at night: officers stretch a yellow cordon "
     "tape, passers-by stop and watch, a detective in a dark jacket walks into the motel; "
     "the scene stays restrained and procedural. Camera: wide shot with a slow push-in. "
     "Real motion: flashing lights, tape sagging, walking, coat movement. All signs are heavily blurred abstract glows with no letters, no Korean characters; no readable text, no insignia numbers."),

    ("S13", 74, 6, "同S07构图，缓慢推近", ["kim", "victimB"], "real",
     "9 February at night, another motel on the same street: purple-red neon flickers, a "
     "man and a woman walk in side by side in almost the same composition as an earlier "
     "night, but light rain falls and the man's clothing is different; the repetition "
     "feels uneasy. Camera: same composition as the earlier entrance, slow push-in. Real "
     "motion: rain falling, curtain parting, walking, neon flickering. All signs are heavily blurred abstract glowing shapes with no letters, no Korean characters, no subtitles, no captions; no clear faces of the man, no readable text."),

    ("S14", 80, 5, "中景，慢动作", ["kim", "detective"], "real",
     "11 February at dawn, below an apartment block in morning mist: plain-clothes "
     "detectives approach a young woman, she stops, does not run, and calmly raises both "
     "hands; cold morning light, breath vapour in the air. Camera: medium shot in slow "
     "motion. Real motion: walking, stopping, hands rising, breath vapour, mist drifting. "
     "No readable text."),

    ("S15", 85, 6, "过肩，缓慢推近", ["kim", "detective"], "real",
     "An interrogation room at Gangbuk police station, cold grey light: a young woman sits "
     "at a metal table facing two detectives, her lips move as if saying she only wanted "
     "him to sleep, the detectives stay expressionless, a paper file rests on the table. "
     "Camera: over-the-shoulder with a slow push-in. Real motion: lips moving, blinking, "
     "breathing, paper edge lifting. Interrogation room only, no street, no storefronts; no readable text, no names, no Korean characters."),

    ("S16", 91, 6, "手持，长焦", ["kim"], "real",
     "Early morning outside Seoul Northern District Court: the woman is led from a police "
     "car with her head lowered, hair covering her face, camera flashes burst, reporters "
     "form a ring around her. Camera: handheld long-lens shot. Real motion: walking, "
     "flashes firing, hair moving, crowd shifting. No readable text, no logos."),

    ("S17", 97, 6, "近景，缓慢推近", ["forensic"], "real",
     "A digital forensics laboratory under blue screen light: a young forensic specialist "
     "with glasses connects a smartphone to a device, rows of abstract chat blocks scroll "
     "on the monitor, he stops his finger, looks up, eyes widening. Camera: close shot "
     "with a slow push-in. Real motion: cable connecting, blocks scrolling, finger "
     "stopping, head lifting. No readable text, no letters, no numbers."),

    ("S18", 103, 5, "大特写，屏幕缓慢上卷", [], "diagram",
     "Extreme close-up of an abstract chat screen: question and answer blocks alternate "
     "and scroll slowly upward, a red warning icon pulses inside the answers again and "
     "again, each pulse deepening the darkness behind the screen. Camera: extreme "
     "close-up with the screen scrolling slowly upward. Real motion: blocks scrolling, "
     "icon pulsing, light deepening. No readable text, no readable letters, no numbers."),

    ("S19", 108, 6, "特写，缓慢推近", [], "real",
     "An apartment kitchen at night under a desk lamp: several clean empty glasses stand "
     "on the table, a hand pauses above a glass rim and withdraws; only fine bubbles "
     "rising in the glass and a streak of cold light are visible, nothing else on the "
     "table. Camera: close-up with a slow push-in. Real motion: hand hovering, bubbles "
     "rising, lamp glow breathing, dust in the light. Kitchen interior only, no street, no storefronts, no vehicles; no medicine, no readable text, no Korean characters."),

    ("S20", 114, 6, "中景，缓慢推近屏幕", [], "real",
     "A white laboratory at the National Forensic Service: instrument lights blink, a "
     "researcher seen from behind stares at a monitor showing a long abstract spectrum "
     "with several peaks rising together, a pen taps the desk lightly, expression "
     "serious. Camera: medium shot with a slow push toward the screen. Real motion: "
     "blinking lights, pen tapping, spectrum lines growing, breathing. Laboratory interior only, no street, no storefronts; no readable text, no numbers, no charts with labels, no Korean characters."),

    ("S21", 120, 5, "俯拍，红线延伸", ["detective"], "real",
     "A police meeting room: detectives gather around a table, on the wall an abstract "
     "word shape is crossed out with a red line and replaced by another abstract shape, "
     "the red line extends across the board; papers turn on the table. Camera: overhead "
     "shot following the extending red line. Real motion: marker drawing, line extending, "
     "pages turning, breathing. Abstract shapes only on the board, no handwriting, no letters, no Korean characters; no readable text, no names."),

    ("S22", 125, 5, "特写，印章落下，慢动作", ["court"], "real",
     "A prosecutor's office corridor and desk under overcast light: a prosecutor in a dark "
     "suit carries case files into the office, an indictment rests on the desk, a red seal "
     "falls in slow motion and lifts; grey daylight from the window. Camera: close-up on "
     "the falling seal in slow motion. Real motion: walking, files settling, seal falling "
     "and lifting, curtain moving. No readable text, no letters."),

    ("S23", 130, 7, "大特写，缓慢推近", [], "diagram",
     "A smartphone screen showing an abstract social account page made of lines only: a "
     "cluster of light dots rises like a slot machine into tall glowing bars, blue light "
     "flickering continuously, background blurred. Camera: extreme close-up with a slow "
     "push-in. Real motion: bars rising, dots pulsing, light flickering. No readable "
     "text, no readable letters, no numbers."),

    ("S24", 137, 7, "中景，缓慢推近", ["cafe"], "real",
     "Inside a Seoul cafe in warm light: young people sit around a table with smartphones, "
     "abstract comment bubbles pop up on the screens, someone taps like, someone frowns; "
     "the camera holds on the frowning face. Camera: medium shot with a slow push-in. "
     "Real motion: tapping, bubbles popping, heads turning, steam rising. No readable "
     "text, no letters."),

    ("S25", 144, 6, "近景，缓慢推近", ["family"], "real",
     "At the same time, a dim memorial hall: two bouquets of white chrysanthemums stand "
     "before a blurred photograph, candlelight flickers, phone light from the side falls "
     "on the petals; a hand slowly places a phone face-down on the table. Camera: close "
     "shot with a slow push-in. Real motion: candle flame, petals trembling, hand placing "
     "the phone. No clear portrait, no readable text."),

    ("S26", 150, 6, "横向环绕，缓慢", ["kim", "court", "family"], "real",
     "A courtroom in summer 2026 under cold grey light: the defendant sits with her head "
     "lowered in the dock, the judge holds the judgment at the bench, several family "
     "members in black sit in the gallery, tense and still. Camera: slow lateral orbit. "
     "Real motion: breathing, paper shifting, heads lowering, curtain moving. No readable "
     "text, no names."),

    ("S27", 156, 6, "中景，慢动作", ["kim", "court", "family"], "real",
     "A courtroom exchange in montage: the defendant speaks with moving lips, the judge "
     "shakes his head slightly, the judge's lips form a long sentence, a family member "
     "in the gallery grips both hands tightly; half the frame stays cold grey. Camera: "
     "medium shot in slow motion. Real motion: lips moving, head shaking, hands gripping, "
     "breathing. No readable text, no dialogue captions."),

    ("S28", 162, 6, "特写，慢动作", ["kim", "family"], "real",
     "27 August: a gavel falls in slow motion, the defendant's body stiffens slightly in "
     "the dock, in the family gallery one person bows his head and another closes his "
     "eyes; low clouds press outside the window. Camera: close-up in slow motion. Real "
     "motion: gavel falling, shoulders stiffening, heads bowing, clouds drifting. Courtroom interior only, no street, no storefronts; no readable text, no Korean characters."),

    ("S29", 168, 6, "缓慢拉远，淡入", [], "real",
     "A smartphone rests on a black table: the cursor blinks in an abstract chat "
     "interface, a red warning icon lights up and then fades, the camera pulls back "
     "slowly and the silhouette of a judgment document appears beside the phone. Camera: "
     "slow pull-back with a fade-in. Real motion: cursor blinking, icon lighting and "
     "fading, light breathing. No readable text, no letters."),

    ("S30", 174, 6, "缓慢推近，淡入淡出", [], "real",
     "The picture darkens to black: a single red warning icon slowly lights up in the "
     "black field and holds, faint dust drifting through the darkness; the frame is kept "
     "deliberately clear for a title added later. Camera: very slow push-in with fade-in "
     "and fade-out. Real motion: icon brightening, dust drifting, light breathing. The "
     "generated clip contains no lettering at all; black field only, no street, no storefronts, no vehicles; every title is added in post."),
]

# ---------------------------------------------------------------- 一镜一句旁白（30 条）
NARRATION = {
    "S01": "她问AI：安眠药加酒，会不会死？",
    "S02": "AI说：可能致命。她看完，继续加大了药量。",
    "S03": "2025年12月，首尔江北区，金某让男友喝下掺了药的饮料。",
    "S04": "他昏迷了两天才醒来，当时，她没有被追责。",
    "S05": "她没有收手，转头又问AI：药检，能查出来吗？",
    "S06": "她把AI的回答，记在了心里。",
    "S07": "2026年1月28日晚九点半，江北区水踰洞的一家汽车旅馆。",
    "S08": "她陪着一位二十多岁的男子走了进去，前台递出一张门卡。",
    "S09": "两个小时后，有人看到她一个人走了出来。",
    "S10": "第二天，男子被发现死在了房间的床上。",
    "S11": "仅仅十二天后，2月9日，同样的旅馆街，另一名男子也再没有醒来。",
    "S12": "2月11日清晨，警察在公寓楼下抓到了她，她没有逃跑。",
    "S13": "她说：我们吵了一架，我只是想让他睡着。",
    "S14": "直到警察联系我，我才知道他死了。",
    "S15": "起初，她面对的只是伤害致死，她以为就这样了。",
    "S16": "可第二天，警察打开了她的手机，里面有一长串聊天记录。",
    "S17": "她反复问AI：过量会不会致死，药和酒一起会怎样？",
    "S18": "AI明确回答：可能致命。而她后来，加大了药量。",
    "S19": "警方还发现，她在作案前，已在家里提前调好了饮料。",
    "S20": "国立科学搜查研究院，检出了死者体内的药物成分。",
    "S21": "伤害致死，变成了杀人，罪名彻底反转。",
    "S22": "2026年3月，她被提起公诉，等待审判。",
    "S23": "案发后，她的社交账号十天涨粉，从两百涨到一万多。",
    "S24": "评论区里，不少人在写：颜值即正义，点赞数暴涨。",
    "S25": "一半在为受害者哀悼，另一半，却在为凶手点赞。",
    "S26": "法庭上，她说自己不记得那些对话，语气平静。",
    "S27": "法官不信：你记得每个细节，却唯独忘了这些？",
    "S28": "8月27日，她被判无期徒刑，检方要求死刑，双方都已上诉。",
    "S29": "AI警告过她，她没有听。",
    "S30": "你觉得，当一个人铁了心，一句警告，拦得住吗？",
}

# ---------------------------------------------------------------- 九段（由镜头推导，只用于章节统计）
CHAPTER_TITLES = [
    ("N01", "开头钩子"),
    ("N02", "第一次得手"),
    ("N03", "1月28日"),
    ("N04", "十二天后"),
    ("N05", "手机里的聊天记录"),
    ("N06", "罪名反转"),
    ("N07", "网络狂欢"),
    ("N08", "法庭"),
    ("N09", "结尾提问"),
]

SOURCES = [
    {
        "id": "user-script",
        "title": "用户脚本《汽车旅馆连环命案：AI警告过她》（30镜分镜）",
        "url": "",
        "supports": "全片时间轴、人物关系、案件节点（2025年12月、2026年1月28日、2月9日、"
                    "2月11日被捕、2月12日手机取证、3月起诉、8月27日一审判决）与事实口径"
                    "（被判、检方要求、金某、法院认为、双方上诉）均以该脚本为准。",
    },
    {
        "id": "fact-boundary",
        "title": "事实边界（脚本口径）",
        "url": "",
        "supports": "一审已判、双方均已上诉；不写未定论的动机与细节；不出现药物名称与调配过程；"
                    "受害者只以背影、剪影与白菊花出现；手机界面一律抽象。",
    },
]

PRINCIPLES = [
    "全片30个镜头全部由 Agnes Video 2.5 Flash 生成连续运动片段（720P 源片，后期放大到 "
    "1920×1080 · 24fps），禁止静态图加推拉代替；每个镜头只出现一次。",
    "每条提示词自动以【STYLE】开头、以【NEGATIVE】结尾；出现人物时自动拼接对应【角色设定】；"
    "2.5 Flash 不接受独立 negative_prompt 字段，红线因此写在提示词正文里。",
    "不出现药物名称、药片、剂量、调配过程；厨房镜头只允许玻璃杯与光影；不出现遗体、血腥；"
    "受害者只以背影、剪影与白菊花出现；嫌疑人以平静空洞形象呈现，不美化。",
    "手机聊天界面一律用抽象线条与图标表示，不出现可读文字；片中文字全部由后期叠加。",
    "旁白一镜一句：每镜一条独立配音与一条同起止字幕；保留自然语速，必要时最多加速 1.55 倍，禁止慢放填满时长。",
    "视觉主线：手机屏幕上的红色警告图标贯穿全片（S02被划走 → S18反复出现 → S29再次亮起 → S30黑场亮起）；"
    "紫红色汽车旅馆霓虹为第二条色彩线索。",
]

PRESENTATION = {
    "cover": {
        "layout": "16:9；中央手机屏幕红色警告图标，四周紫红霓虹汽车旅馆夜景",
        "text": "AI警告过她",
        "subtext": "汽车旅馆连环命案",
        "style": "金色粗体字、黑色描边；由 S02 手机帧与 S01 街景帧合成，红色警告图标为后期绘制，"
                 "不是静态图替代视频",
    },
    "end_title": "汽车旅馆连环命案",
    "end_subtitle": "首尔江北区 · 2025—2026 · AI警告过她",
    "end_note": "真实案件改编 · 部分画面为3D复原",
    "end_question": "一句警告，拦得住吗？",
    "highlight_keywords": [
        "AI", "可能致命", "加大了药量", "2025年12月", "江北区", "金某", "掺了药",
        "昏迷", "没有被追责", "没有收手", "药检", "1月28日", "水踰洞", "汽车旅馆",
        "门卡", "2月9日", "再没有醒来", "2月11日", "抓到了她", "只是想让他睡着",
        "伤害致死", "手机", "聊天记录", "ChatGPT", "过量", "提前调好了饮料",
        "药物成分", "杀人", "罪名", "提起公诉", "粉丝", "两百", "一万多",
        "颜值即正义", "哀悼", "点赞", "法庭", "不记得", "无期徒刑", "检方要求死刑",
        "上诉", "警告", "拦得住吗",
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
        {"at": 0, "name": "雨后水滴声、霓虹灯管嗡鸣、远处车流声", "kind": "sfx"},
        {"at": 10, "name": "轻声交谈、杯子碰桌面声", "kind": "sfx"},
        {"at": 30, "name": "键盘敲击声、发送提示音", "kind": "sfx"},
        {"at": 35, "name": "车帘摩擦声、前台窗口对话声", "kind": "sfx"},
        {"at": 49, "name": "时钟加速声、霓虹灯管嗡鸣", "kind": "sfx"},
        {"at": 55, "name": "脚步踩水声、远处车流声", "kind": "sfx"},
        {"at": 60, "name": "敲门声、毛巾落地声、急促脚步声", "kind": "sfx"},
        {"at": 67, "name": "警笛声、对讲机嘈杂", "kind": "sfx"},
        {"at": 74, "name": "雨声、车帘摩擦声（与S07呼应）", "kind": "sfx"},
        {"at": 80, "name": "晨风、警察低声喊话", "kind": "sfx"},
        {"at": 85, "name": "椅子摩擦声、日光灯嗡鸣", "kind": "sfx"},
        {"at": 91, "name": "快门声、记者喊话、警车关门声", "kind": "sfx"},
        {"at": 97, "name": "设备读取嘀嗒声、键盘敲击声", "kind": "sfx"},
        {"at": 103, "name": "提示音反复响起、逐渐沉入低频", "kind": "sfx"},
        {"at": 108, "name": "玻璃碰撞声、水龙头滴水声", "kind": "sfx"},
        {"at": 114, "name": "仪器运行声、笔敲桌面声", "kind": "sfx"},
        {"at": 120, "name": "马克笔划线声、纸张翻动声", "kind": "sfx"},
        {"at": 125, "name": "印章落下的闷响", "kind": "sfx"},
        {"at": 130, "name": "数字滚动声、提示音连续响起", "kind": "sfx"},
        {"at": 137, "name": "咖啡馆环境声、手机提示音", "kind": "sfx"},
        {"at": 144, "name": "烛火轻响、手机被扣下的闷响", "kind": "sfx"},
        {"at": 150, "name": "法庭环境声、纸张声", "kind": "sfx"},
        {"at": 156, "name": "压低的呼吸声、一声咳嗽", "kind": "sfx"},
        {"at": 162, "name": "法槌落下的回响、随后一片寂静", "kind": "sfx"},
        {"at": 168, "name": "提示音、红色图标亮起的滴声", "kind": "sfx"},
        {"at": 174, "name": "最后一秒静音", "kind": "sfx"},
    ],
    "douyin_title": "AI明确警告过她：可能致命。她看完，继续加大药量：汽车旅馆连环命案",
    "hashtags": ["#真实事件", "#汽车旅馆命案", "#韩国", "#ChatGPT", "#悬疑", "#电影感"],
    "release_intro": (
        "她问AI：安眠药加酒，会不会死？AI说：可能致命。她看完，继续加大了药量。\n\n"
        "2025年12月，首尔江北区，金某让男友喝下掺了药的饮料。他昏迷两天才醒来，当时她没有被追责。\n"
        "2026年1月28日晚九点半，她陪着一名男子走进水踰洞的汽车旅馆；十二天后，另一名男子也再没有醒来。\n"
        "2月11日她被捕。警察打开她的手机，里面有一长串和ChatGPT的聊天记录：她反复问过量会不会致死，"
        "AI明确回答可能致命，而她后来加大了药量。伤害致死，变成了杀人。\n\n"
        "8月27日，她被判无期徒刑，检方要求死刑，双方都已上诉。\n\n"
        "画面为AI生成的3D动画情景重现，不是新闻影像。手机界面为抽象示意，不出现可读文字。"
    ),
}

REFERENCE_IMAGES = [
    {"file": "reference/01-kim.png",
     "description": "C01 金某定稿：20岁出头韩国年轻女子，黑色中长直发，灰色连帽外套牛仔裤，"
                    "神情平静空洞，风格化形象，非真实肖像"},
    {"file": "reference/02-motel-street.png",
     "description": "S01 江北区水踰洞夜街定稿：紫红霓虹、雨后路面反光、抽象空房招牌、车帘"},
    {"file": "reference/03-motel-corridor.png",
     "description": "S02 汽车旅馆走廊定稿：紫红色灯光、长走廊对称构图、地毯与房门"},
    {"file": "reference/04-motel-room.png",
     "description": "S03 汽车旅馆房间定稿：整齐床铺、窗帘缝紫红霓虹、两只玻璃杯"},
    {"file": "reference/05-phone-warning.png",
     "description": "P01 手机警告定稿：抽象聊天线条、红色感叹号警告图标、冷蓝屏幕光"},
    {"file": "reference/06-forensic-lab.png",
     "description": "S08 数字取证实验室定稿：蓝色屏幕光、设备与线缆、冷蓝色调"},
    {"file": "reference/07-courtroom.png",
     "description": "S10 法庭定稿：木质法官席、被告席、旁听席、冷灰色光线"},
    {"file": "reference/08-memorial.png",
     "description": "S12 灵堂定稿：两束白菊花、模糊照片、烛光、冷青与暖黄对比"},
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
        seed = CHARACTER_SEEDS[characters[0]] if len(characters) == 1 else 20260101 + index
        shots.append({
            "id": sid,
            "kind": "agnes",
            "start": start,
            "duration": duration,
            "narration_id": None,
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
            "transition_out": "同段内硬切或轻叠化；前半段用霓虹闪烁转场，S07与S13同构图硬切；"
                              "S17–S22用冷蓝屏幕光转场；结尾黑场淡入0.3秒；不改动旁白时间轴。",
        })

    chapter_bounds = [
        ("N01", 0, 10), ("N02", 10, 35), ("N03", 35, 60), ("N04", 60, 85), ("N05", 85, 108),
        ("N06", 108, 130), ("N07", 130, 150), ("N08", 150, 168), ("N09", 168, 180),
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
            "voice_id": "voice-01",
            "language": "zh-CN",
            "alignment": "one-independently-generated-voice-clip-and-one-caption-cue-per-shot",
            "max_speedup_factor": 1.55,
            "slowdown_allowed": False,
            "dramatic_pause_after": {"S29": 0.4},
        },
        "sources": SOURCES,
        "presentation": PRESENTATION,
        "reference_images": REFERENCE_IMAGES,
        "fact_boundary": [
            "案件一审已判，双方均已上诉；片中一律使用“被判”“检方要求”口径，嫌疑人称“金某”，"
            "法院认定写“法院认为”。",
            "时间节点：2025年12月第一次；2026年1月28日晚九点半水踰洞汽车旅馆；2月9日十二天后；"
            "2月11日被捕；2月12日手机取证；2026年3月提起公诉；8月27日一审被判无期徒刑。",
            "片中不出现药物名称、药片、剂量、调配过程；厨房镜头只允许玻璃杯与光影；"
            "不出现遗体、血腥；受害者只以背影、剪影与白菊花出现。",
            "手机聊天界面一律用抽象线条与图标表示，不出现可读文字；片中文字全部由后期叠加。",
            "所有画面为AI 3D动画情景重现，不是新闻影像；真实人物均为风格化虚构形象，非真实肖像。",
        ],
    }


def write_screenplay(story: dict) -> None:
    lines = [
        f"# {story['title']}",
        "",
        f"三分钟横屏悬疑3D动画短片 · 1920×1080 · {story['fps']}fps · 180秒 · "
        "30 个 Agnes Video 2.5 Flash 动态镜头 · 一镜一句中文旁白",
        "",
        "> 画面为 AI 3D动画情景重现，不是新闻影像；手机界面为抽象示意，不出现可读文字。",
        "> 不出现药物细节、遗体、血腥；受害者只以背影、剪影与白菊花出现。",
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
    lines += ["## 30 镜分镜表", "", "| 镜号 | 时间 | 秒数 | 段 | 运镜 | 角色 | 画面职责 |",
              "|---|---:|---:|---|---|---|---:|"]
    for shot in story["shots"]:
        start, end = shot["start"], shot["start"] + shot["duration"]
        times = f"{start//60:02d}:{start%60:02d}—{end//60:02d}:{end%60:02d}"
        roles = "、".join(shot["characters"]) or "—"
        lines.append(f"| {shot['id']} | {times} | {shot['duration']} | {shot['narration_id']} | "
                     f"{shot['camera']} | {roles} | {shot['purpose']} |")
    lines += ["", "## 来源", ""]
    for source in story["sources"]:
        lines.append(f"- {source['title']}：{source['supports']}")
    lines += [
        "",
        "## 后期规范",
        "",
        "- 生成：Agnes Video 2.5 Flash，720P 源片，12 秒共享节流（月卡每分钟最多五次），断点续跑；后期放大到 1920×1080。",
        "- 配音：悬疑低沉男声；一镜一句、字幕同起止；只加速（≤1.55×），不慢放。",
        "- 字幕：白色黑边、底部安全区、关键词金色放大；日期与案件信息与脚本口径一致。",
        "- 音乐：原创程序合成（低沉弦乐、钢琴、低频脉冲、金属提示音）；旁白下压约 −18dB。",
        "- 音效：霓虹嗡鸣、雨声、车帘、门卡、时钟、警笛、快门、键盘、印章、法槌（见 sound_events）。",
        "- 片尾：S30 黑场红色警告图标，后期叠加金色片名『汽车旅馆连环命案』与副题"
        "『首尔江北区 · 2025—2026 · AI警告过她』，最后 1 秒静音。",
        "- 封面：中央手机红色警告图标、四周紫红霓虹旅馆夜景；主标题『AI警告过她』。",
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
            "voice_description": "悬疑低沉男声；语速沉稳、句尾收得轻，像真实犯罪纪录片",
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
        "30 个 Agnes Video 2.5 Flash 动态镜头\n\n"
        "**核心钩子：** AI明确警告过她：可能致命。她看完，继续加大药量\n\n"
        "## 四列分镜表\n\n"
        "| 镜号 | 时间 | 口播（=字幕） | 画面 | 运镜 |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## 声音设计\n\n| 时间 | 声音 |\n|---|---|\n" + events
        + "\n\n## 事实边界\n\n"
        "- 一审已判、双方均已上诉；嫌疑人称“金某”；检方口径写“检方要求”。\n"
        "- 不出现药物名称、药片、剂量、调配过程；不出现遗体、血腥；受害者只以背影、剪影与白菊花出现。\n"
        "- 手机界面一律抽象，不出现可读文字；画面为AI 3D动画情景重现。\n\n"
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

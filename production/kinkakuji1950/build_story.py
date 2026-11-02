#!/usr/bin/env python3
"""唯一内容源：《金阁寺纵火案：美，为何被烧成灰》

运行 ``python3 production/kinkakuji1950/build_story.py`` 会写出 story.json、screenplay.md、
audio/manifest.json、抖音脚本.md 与抖音发布文案.md。30 个镜头全部是 Agnes Video 2.5 Flash
（720P 源片，后期放大到 1920×1080 · 24fps）生成的连续运动片段；旁白一镜一句，字幕与配音同起止。

事实边界：1950 年 7 月 2 日凌晨三点前后，京都市上京区（今北区）鹿苑寺（通称金阁寺）的舍利殿
被见习僧林养贤纵火烧毁，国宝建筑与足利义满木像等六件文物一同烧失；火灾报警器当时失效。
当天傍晚，林在寺后左大文字山被发现并逮捕；1950 年 12 月 28 日京都地方法院判处有期徒刑七年；
狱中结核与精神疾病恶化，1956 年 3 月 7 日病死，年仅 26 岁。金阁于 1955 年重建。
片中出现其母结局时只用空镜、物件与环境表现，不表现任何自伤的方法或过程；
不出现遗体、伤口、血腥；所有真实人物一律为风格化形象，非真实肖像。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
TITLE = "金阁寺纵火案：美，为何被烧成灰"
FILM_NAME = "金阁寺纵火案_美为何被烧成灰_三分钟_带声音.mp4"
BRANCH = "arena/98ae98a6-desktop-tutorial"
FPS = 24
SHOT_COUNT = 30

# ---------------------------------------------------------------- 全局 STYLE / NEGATIVE
STYLE_PREFIX = (
    "【STYLE】Cinematic-quality 3D animated film, Kyoto classical aesthetics with an ukiyo-e "
    "colour sensibility: Kinkaku-ji, the three-storey golden pavilion of Rokuon-ji, standing at "
    "the edge of the mirror-still Kyoko-chi pond, ringed by black pines, moss, stone lanterns and "
    "a gravel path. Palette of warm leaf-gold and deep indigo, with thin mist, spring sakura, "
    "summer fireflies, autumn maple and winter snow. Real gold-leaf texture with visible seams, "
    "aged cypress bark roofing, lacquer, bronze Phoenix, moss and wet stone materials, volumetric "
    "light shafts, soft ambient occlusion, shallow cinematic depth of field, gentle film grain, "
    "rich foreground-midground-background layering, and the pond reflection treated as the film's "
    "main visual motif. Horizontal 16:9 widescreen composition, the subject placed near a third "
    "line, the full width of the frame used, and the lower sixth kept visually quiet for subtitles. "
    "Every clip is true continuous 3D animation with observable natural movement - water lapping "
    "and rippling, petals and snow falling, fireflies drifting, flames and sparks climbing, "
    "candlelight breathing, wind in pines, cloth and sleeves settling, heads turning, blinking, "
    "hands at work, and steady camera parallax - never a still image with a push-in or a slideshow. "
    "Period-correct Japanese architecture, clothing and objects of 1397-1955. All characters are "
    "stylized, never the likeness of a real person. No lettering anywhere inside generated frames. "
)

# 抽象示意图单独一套风格：同样以【STYLE】开头，自动拼接；刻意做成干净的信息可视化，
# 与本片的写实复原镜头明确区分，避免把概念图误读成史料。
STYLE_DIAGRAM_PREFIX = (
    "【STYLE｜概念示意｜抽象可视化】Clean cinematic 3D information graphic on a deep charcoal "
    "background, restrained indigo and muted-gold palette, fine volumetric haze, soft edges, "
    "elegant shallow depth of field and subtle film grain; deliberately abstract and clearly a "
    "conceptual diagram, not a historical document. Horizontal 16:9 widescreen composition with "
    "generous negative space and the lower sixth kept quiet for subtitles. Everything breathes "
    "with real continuous motion - lines draw themselves, icons materialise and drift, cracks "
    "propagate slowly, particles rise - never a flat static slide. Absolutely no readable "
    "letters, numbers, names or logos anywhere in frame. "
)

NEGATIVE_PROMPT = (
    "【NEGATIVE】readable text, subtitles, captions, watermark, logo, gibberish lettering, "
    "blood, gore, wound, corpse, dead body, human remains, funeral portrait, suicide method, "
    "self-harm, hanging, jumping from a train, overdose, weapon striking a person, violence in "
    "progress, nudity, deformed hands, extra fingers, extra limbs, facial collapse, distorted "
    "anatomy, plastic skin, mannequin faces, realistic likeness of a real person, wrong building "
    "structure, modern objects, modern clothing, cars, smartphones, drones, tourists in modern "
    "clothes, low resolution, flicker, style drift, vertical framing, letterbox black bars inside "
    "the frame, frozen frame, slideshow, still image with artificial zoom, oversaturated colours, "
    "heavy lens flare, jump scare."
)

# ---------------------------------------------------------------- 角色设定（跨镜逐字复用）
CHARACTERS = {
    "ryozen": (
        "【角色设定｜林养贤】Ryozen, a stylized 21-year-old Japanese novice monk of 1950: thin and "
        "slight, narrow shoulders, freshly shaved head, plain grey cotton work robe (samue) with a "
        "simple sash, straw sandals, sensitive guarded eyes, head always slightly lowered; when he "
        "speaks his lips tremble a little. Quiet, withdrawn, never aggressive. Keep his head shape, "
        "build, robe colour and facial proportions identical in every shot. Never a portrait or "
        "likeness of any real person. "
    ),
    "boy": (
        "【角色设定｜少年林养贤】Young Ryozen, a stylized Japanese boy of thirteen to sixteen: "
        "small and thin, close-cropped black hair, worn dark old-style school uniform and a cloth "
        "bundle, lonely watchful eyes, same face shape as the adult Ryozen. Keep him identical in "
        "every shot. Never a portrait or likeness of any real person. "
    ),
    "father": (
        "【角色设定｜父亲】Ryozen's father, a stylized Japanese Buddhist priest in his late "
        "forties: gaunt and ill, thin face, short dark hair, pale grey robe, lying on a futon on "
        "tatami under a thin quilt, breathing slowly. Never a portrait or likeness of any real "
        "person. "
    ),
    "mother": (
        "【角色设定｜母亲】Ryozen's mother, a stylized Japanese woman of forty-nine: small and "
        "sturdy, hair in a low bun, plain dark kimono with a woven obi, a small cloth bundle held "
        "in both hands, a face that is determined and worried at once. Keep her identical in every "
        "shot. Never a portrait or likeness of any real person. "
    ),
    "abbot": (
        "【角色设定｜住持】The abbot of Rokuon-ji, a stylized Japanese Zen priest in his sixties: "
        "shaved head, formal black robe, severe composed face, sitting upright with a folding fan. "
        "Keep him identical in every shot. Never a portrait or likeness of any real person. "
    ),
    "yoshimitsu": (
        "【角色设定｜足利义满·剪影】Ashikaga Yoshimitsu as a silhouette only: a Muromachi-era "
        "shogun in layered courtly robes and a tall eboshi cap, rendered as a dark shadow with a "
        "thin rim of gold light and no facial features at all. "
    ),
    "police": (
        "【角色设定｜1950年日本警察与消防员】Stylized 1950 Japanese police officers in dark navy "
        "uniforms with peaked caps and long coats, and firefighters in thick quilted fire coats, "
        "steel helmets and canvas hose slung over the shoulder; no readable insignia, badges or "
        "numbers. Calm, methodical, never excited. Not portraits of real officers. "
    ),
    "tourists": (
        "【角色设定｜1950年游客】Stylized 1950 Japanese visitors: plain kimono and hakama, simple "
        "dresses, hats and parasols, small bundles and paper tickets, moving in a loose queue. No "
        "readable text on any ticket or sign. Not portraits of real people. "
    ),
    "monks": (
        "【角色设定｜僧众】Stylized young Japanese novice monks in plain grey work robes, shaved "
        "heads, sweeping the stone path and walking in a line, heads slightly bowed. Not portraits "
        "of real people. "
    ),
    "doctor": (
        "【角色设定｜医护人员】Stylized 1950s Japanese nurse in a white apron and cap and a ward "
        "doctor in a white coat, quiet and unhurried, no readable text on any chart. Not portraits "
        "of real people. "
    ),
}

CHARACTER_SEEDS = {
    "ryozen": 19500702,
    "boy": 19290319,
    "father": 19400101,
    "mother": 19490102,
    "abbot": 19500303,
    "yoshimitsu": 13970404,
    "police": 19500705,
    "tourists": 19500606,
    "monks": 19500707,
    "doctor": 19560308,
}

# ---------------------------------------------------------------- 30 镜（4–9 秒／镜，合计 180 秒）
# (镜号, 时长, 运镜, 角色, 风格变体, 提示词)
SHOT_ROWS = [
    ("S01", 5, "航拍缓慢下降，贴向水面", [], "real",
     "Dawn at Kinkaku-ji in Kyoto, thin mist lying over the mirror pond. The camera descends "
     "slowly and steadily from above the pines until it almost touches the water, so the golden "
     "pavilion stands on the right third and its perfect reflection fills the left two thirds. "
     "Morning light slides across the gold-leaf walls, sakura petals drift down and touch the "
     "surface in widening rings, mist breathes between the trees. Real motion: petals falling, "
     "rings spreading, mist drifting, continuous downward parallax. No people, no readable text."),

    ("S02", 6, "低机位，从水面倒影推向楼阁", [], "real",
     "The same pavilion at night under a hazy moon, the pond reflection calm and perfect. The "
     "camera glides low across the water straight toward the pavilion, then a thin orange-red "
     "glow tears open behind an upper window, sparks spill out and drift upward, and the "
     "reflection slowly reddens while the cicada sound of a summer night cuts out. Real motion: "
     "ripples, drifting sparks, the glow swelling and flickering, slow forward glide. No flames "
     "touching any person, no readable text."),

    ("S03", 6, "广角航拍，缓慢环绕山坡", ["yoshimitsu"], "real",
     "Kyoto, 1397, hazy gold afternoon. High wide aerial shot circling slowly around a wooded "
     "hillside above a pond: the silhouetted shogun stands on the slope with an open fan, looking "
     "down while carpenters raise the timber frame of a three-storey pavilion, men carry planks, "
     "and a line of craftsmen lay squares of gold leaf along a new eave so the roof glitters in "
     "the sun. Everything carries an aged, slightly yellowed historical patina. Real motion: "
     "sawing, hammering, gold leaf fluttering, robes moving, slow orbital camera. No readable text."),

    ("S04", 6, "水面平视，缓慢横移", [], "real",
     "Spring at Kinkaku-ji: the pavilion stands in a cloud of fully opened sakura, the pond is a "
     "pink-gold mirror. The camera tracks slowly sideways at water level; petals land and float "
     "past, koi turn beneath the surface, the reflection ripples gently and reassembles. Real "
     "motion: falling petals, koi moving, water rings, drifting blossom on the lens, slow lateral "
     "track. No people, no readable text."),

    ("S05", 7, "缓慢推近，飘雪粒子", [], "real",
     "Winter at Kinkaku-ji: heavy snow covers the pines and the roofs, the gold pavilion glows "
     "warmly against a white world, snowflakes settle on the golden eaves and slide off. Bluish "
     "winter light, breath of mist over the pond. The camera pushes in slowly and evenly. Real "
     "motion: steady snowfall, snow sliding from the eaves, wind shifting pine branches, soft "
     "parallax. No people, no readable text."),

    ("S06", 7, "中景背影，缓慢推近", ["ryozen"], "real",
     "Summer night at the pond: fireflies drift in slow golden points over the water, a full moon "
     "rises behind the pavilion, its reflection laid across the pond. A lone novice monk stands "
     "with his back to the camera at the pond's edge, perfectly still except for breathing, then "
     "his shoulders settle as he exhales. The camera eases in behind him. Real motion: fireflies "
     "drifting, moonlit ripples, fabric stirring, slow breathing. No readable text."),

    ("S07", 6, "中景侧面，海风吹动", ["boy"], "real",
     "A small fishing town on the Japan Sea coast, Maizuru, 1940s: a modest wooden temple gate "
     "with a weathered roof, prayer banners snapping in the sea wind, grey water beyond the roofs "
     "and gulls turning. A thin boy stands at the gate in a worn school uniform, hands at his "
     "sides, looking out to sea with a lonely, guarded expression. The camera holds a medium "
     "profile and drifts slightly. Real motion: wind in the banners, hair and collar moving, gulls "
     "turning, sea shimmer. No readable text."),

    ("S08", 7, "少年特写，周围同学虚化", ["boy"], "real",
     "A 1940s Japanese classroom in cold blue light: wooden desks, a blackboard with only blurred "
     "smudges, a tall window. A boy stands beside his desk asked to read aloud; his lips tremble, "
     "the words jam in his throat, his hands grip the desk edge. Around him, out-of-focus "
     "classmates turn their heads and exchange smirks. The camera pushes in slowly on his face "
     "while the room drains to a cold blue. Real motion: trembling lips, swallowing, turning "
     "heads, dust motes in the window light. No readable text."),

    ("S09", 6, "中景，轻微推近", ["father", "boy"], "real",
     "The interior of a small temple house, dim amber afternoon light, tatami, a low shelf, a "
     "sliding screen half open onto a green garden. His father lies on a futon under a thin "
     "quilt, thin and pale, coughing shallowly; the boy kneels beside him holding his hand, eyes "
     "reddening, breathing carefully so as not to cry. Cicadas pulse outside. The camera pushes "
     "in very slightly. Real motion: the father's chest and hand, the boy's breathing and blink, "
     "the screen swaying in the breeze. No medical detail, no readable text."),

    ("S10", 5, "低角度仰拍，缓慢推近", ["boy"], "real",
     "The main gate of Rokuon-ji, Kyoto, 1946: a great wooden gate, raked gravel, moss, pines. A "
     "sixteen-year-old boy with a cloth bundle over his shoulder steps through and stops, tipping "
     "his head back to look at the golden roof ridge beyond the trees, gold light falling into his "
     "eyes, the hem of his jacket lifting in the wind. The camera sits low and pushes in slowly. "
     "Real motion: walking, stopping, wind in cloth, leaves turning, slow upward look. No readable "
     "text."),

    ("S11", 5, "中景侧移", ["monks", "ryozen"], "real",
     "Early morning at Kinkaku-ji: a line of novice monks sweeps the stone path, brooms scraping, "
     "dry leaves tumbling, mist still hanging in the pines, the gold pavilion soft in the "
     "background. Ryozen walks at the end of the line, head down, sweeping in rhythm. The camera "
     "tracks sideways with the line. Real motion: sweeping arms, leaves scattering, breath and "
     "mist, footsteps, slow lateral track. No readable text."),

    ("S12", 4, "中景，浅景深", ["ryozen"], "real",
     "A cold grey university classroom, 1948: wooden desks in rows, tall windows, Kyoto rooftops "
     "and a thread of sakura visible outside. Ryozen sits alone at the window seat, an open book "
     "in front of him, turning a page; two students in the soft background talk and laugh. He does "
     "not look up. Shallow depth of field, the camera holds a steady medium and breathes. Real "
     "motion: page turning, pen tapping, distant laughter, curtain moving, blinking. No readable "
     "text, no legible book covers."),

    ("S13", 7, "广角，缓慢横移", ["tourists", "ryozen"], "real",
     "Postwar Kinkaku-ji, early 1950s: a long queue of visitors in plain kimono and simple dresses "
     "waits at a small wooden ticket window, coins dropping into a lacquered box, hands exchanging "
     "paper tickets, a turnstile clicking as people pass, chatter and parasols. Ryozen stands far "
     "to the right, half in shadow at the edge of the path, watching the queue with a complicated "
     "expression. The camera tracks slowly wide across the scene. Real motion: the queue shuffling "
     "forward, coins falling, turnstile turning, parasols tilting. No readable text on signs or "
     "tickets."),

    ("S14", 6, "中景过肩，缓慢推近", ["abbot", "ryozen"], "real",
     "The abbot's study: dark timber, a scroll with only an unreadable brush mark, a low table, "
     "the garden and the distant gold pavilion framed in the open shoji. The abbot sits upright "
     "and speaks sternly, one hand lifting in reproof; across from him, seen over the abbot's "
     "shoulder, Ryozen keeps his head down and his fist slowly closes against his knee. The "
     "camera pushes in gently on that fist and the averted face. Real motion: the abbot's gesture, "
     "Ryozen's knuckles tightening, sleeve shifting, light on the garden. No readable text."),

    ("S15", 6, "背影跟拍，缓慢推近", ["ryozen"], "real",
     "Late night, 1 July 1950: a wooden covered corridor at Kinkaku-ji, moonlight lying in pale "
     "squares on the floorboards, a stone lantern glowing in the garden. Ryozen walks away from "
     "the camera carrying a small old cloth bundle, his sandals sounding on the wood; the moonlit "
     "eaves of the pavilion glimmer at the end of the corridor. The camera follows his back and "
     "closes in slowly. Real motion: walking, bundle swinging, shadow sliding, dust in the "
     "moonlight. No readable text."),

    ("S16", 5, "内景缓慢推进", ["ryozen"], "real",
     "Inside the golden pavilion at night, before anything happens: a small Buddha statue sits in "
     "deep shadow on an altar, a single candle flame breathes and steadies, and the wooden statue "
     "of Ashikaga Yoshimitsu shows only a faint gold outline in the dark. Ryozen kneels at the "
     "threshold, perfectly still, hands on his knees, then slowly bows. The camera pushes in "
     "smoothly. Real motion: candle flame, slow bow, dust motes, gold shimmer. Serene and sacred, "
     "no violence, no readable text."),

    ("S17", 7, "低机位仰拍，火星升腾", [], "real",
     "Three in the morning, 2 July 1950: a single point of fire opens at an upper window of the "
     "golden pavilion, spreads along the balcony, then the gold eaves are swallowed by churning "
     "orange light. Sparks pour upward in a dense column, like a river of stars flowing backwards "
     "into the night sky, and the pines around the pond are rimmed in red. The camera tilts up "
     "from low beside the pond. Real motion: flame growth, rolling smoke, rising sparks, "
     "flickering light on water. No people, no readable text."),

    ("S18", 6, "水面平视，缓慢后拉", [], "real",
     "The mirror pond during the fire: the whole burning pavilion is reflected in the water, "
     "liquid gold and fire meeting at the surface, ash falling onto the pond in soft flakes, koi "
     "scattering away from the heat, rings spreading everywhere. The camera pulls back slowly at "
     "water level so the reflection fills the lower half and the real fire the upper half. Real "
     "motion: flames reflected and rippling, ash landing, koi darting, slow backward dolly. No "
     "people, no readable text."),

    ("S19", 5, "广角快速横移", ["police"], "real",
     "The main gate of Rokuon-ji during the fire: a 1950 fire truck with its bell ringing pushes "
     "through the gate, firefighters in quilted coats drag canvas hoses across the gravel, water "
     "arcs into the flames and bursts into white steam, and a fire alarm bell on a wooden post "
     "hangs silent and still. The camera tracks fast and wide across the scene. Real motion: "
     "running men, hoses snaking, water arcing, steam billowing, embers drifting. No readable "
     "text."),

    ("S20", 7, "仰拍，慢动作", ["police", "tourists"], "real",
     "Slow motion: the roof of the pavilion tilts, holds, and collapses inward, gold fragments and "
     "sparks bursting upward into the dark sky. In the foreground, out of focus, onlookers in "
     "1950 clothing press their hands to their mouths, faces lit orange, and a firefighter lowers "
     "his hose. The camera looks up from below and holds steady. Real motion: the collapse, gold "
     "fragments spinning, embers rising, hands moving. Nothing injured is shown, no bodies, no "
     "readable text."),

    ("S21", 6, "低机位，缓慢推近", [], "real",
     "Dawn after the fire: the ruined pavilion is a black skeleton of charred beams standing in "
     "grey mist, thin smoke still rising from the rubble, the charred stone base of a Buddha "
     "statue visible under fallen ash, the pond absolutely still. Pale morning light cuts through "
     "the smoke in shafts. The camera creeps forward low and slow. Real motion: smoke drifting, "
     "ash settling, light shifting, water barely moving. No people, no remains, no readable text."),

    ("S22", 7, "航拍俯拍，缓慢下降", ["ryozen", "police", "monks"], "real",
     "Morning mist on the wooded slope of Mount Daimonji behind the temple. Seen from a high "
     "descending aerial, a hunched figure in a grey robe sits on the ground among the trees, head "
     "bowed, motionless; further down the slope, police officers and two monks climb quickly "
     "through the undergrowth toward him, torchlight bobbing in the mist. The camera descends "
     "steadily. Restrained, distant and non-explicit: only the approach is shown. Real motion: "
     "mist, branches, climbing figures, slow aerial descent. No self-harm, no method, no blood, no "
     "readable text."),

    ("S23", 5, "中景，缓慢推近", ["ryozen", "police"], "real",
     "A Kyoto police interrogation room, 1950: bare wooden table, a single desk lamp, a chair, a "
     "door with frosted glass. Ryozen sits with his head low, hands folded, lips trembling as he "
     "forces out a few words; a detective leans back, waiting patiently, notebook open, and the "
     "lamp lights one half of the young monk's face. The camera pushes in slowly. Real motion: "
     "trembling lips, pen moving, lamp flicker, breathing. Cold grey palette. No readable text."),

    ("S24", 6, "漂浮式滑动", [], "diagram",
     "An abstract cinematic diagram in dark space: four floating icons appear one after another - "
     "a small golden pavilion, a coin dropping into a collection box, a clenched fist, and a single "
     "sakura petal caught in wind - and a fine crack runs between each of them, slowly "
     "propagating, joining them into one broken line. Particles drift, the icons turn slowly and "
     "breathe with light. The camera floats laterally through the gaps. Symbolic, no readable text or numbers."),

    ("S25", 6, "中景背影，缓慢推近", ["mother"], "real",
     "A rural railway platform in Kyoto prefecture, summer 1950: a wooden shelter, a timetable "
     "board with only blurred marks, hills beyond the tracks, cicadas ringing. Ryozen's mother "
     "stands alone facing away, a small cloth bundle held tightly in both hands, looking at the "
     "distant mountains; wind lifts the loose hair at her temple and the hem of her kimono. The "
     "camera pushes in slowly on her back and hands. Real motion: wind, fabric, her shoulders "
     "rising once as she breathes. No train arriving, no incident, no readable text."),

    ("S26", 6, "车厢内长镜头，缓慢推向空座位", ["mother"], "real",
     "Inside a 1950 train carriage: worn green seats, wooden window frames, a hanging strap swaying, "
     "afternoon light sliding across the aisle. The camera moves slowly down the carriage and comes "
     "to rest on one empty seat where a small cloth bundle lies alone, a folded paper beside it. "
     "Outside the window, the misty Hozukyo gorge and the river slide past. Real motion: the "
     "swaying strap, rattle, sliding light, the gorge moving outside. No person falling, no "
     "incident, no readable text."),

    ("S27", 5, "中景环绕", ["ryozen", "police"], "real",
     "The Kyoto District Court, December 1950: a cold grey courtroom, high windows, bare wooden "
     "benches, a judge's raised dais. The judge reads the verdict, the gavel lifts and falls; in "
     "the defendant's box Ryozen stands with his head down, shoulders trembling very slightly, and "
     "the public gallery behind sits in complete silence. The camera arcs slowly around the room. "
     "Real motion: the gavel, turning heads, a curtain of light, trembling shoulders. No readable "
     "text."),

    ("S28", 7, "中景，缓慢推向窗外", ["ryozen", "doctor"], "real",
     "A hospital ward in early spring 1956, soft white light, an iron bed, a thin blanket, a "
     "bedside table with a glass of water. In the bed Ryozen lies very still, thin and pale, "
     "looking toward the tall window where spring snow and sakura petals fall together; a nurse "
     "in the soft background writes at a desk. A shaft of sunlight moves across his hand on the "
     "blanket. The camera pushes slowly toward the window. Real motion: snowfall, petals, the "
     "curtain lifting, breathing, sunlight moving. Restrained, no medical detail, no readable text."),

    ("S29", 7, "航拍缓慢拉升", ["tourists"], "real",
     "Kinkaku-ji in 1955, rebuilt: craftsmen on bamboo scaffolding press new squares of gold leaf "
     "onto the fresh eaves with flat brushes, and the restored gold pours its light across the "
     "mirror pond again. Visitors in the foreground look up, hands shading their eyes. The camera "
     "rises slowly and evenly. Real motion: brushes moving, gold leaf fluttering, scaffolding "
     "creaking, visitors turning, light on water. No readable text."),

    ("S30", 6, "缓慢推近，淡入淡出", [], "real",
     "The mirror pond at Kinkaku-ji, still and perfect: the pavilion's reflection rests unbroken on "
     "the water, a single sakura petal lands and rings spread outward, mist drifts, the sky pales "
     "toward white. The camera pushes in very slowly until the reflection fills the frame, then "
     "the image fades toward white, leaving clean empty space in the centre for a title added in "
     "post. Real motion: ripples, drifting petal, mist, slow push in, gradual fade. The generated "
     "clip contains no lettering at all. No readable text."),
]

# ---------------------------------------------------------------- 一镜一句旁白（30 条）
# 每条都写进分镜：旁白 = 字幕，起止与镜头一致；只允许加速，不允许慢放。
NARRATION = {
    "S01": "它在这里站了五百多年，美得让人不敢呼吸。",
    "S02": "1950年夏夜，一个二十一岁的僧人，把它烧成了灰。",
    "S03": "金阁寺本名鹿苑寺，1397年由足利义满建造。",
    "S04": "三层楼阁贴满金箔，整座建筑倒映在镜湖池里。",
    "S05": "春天樱花，冬天白雪，人们说，这就是日本的美。",
    "S06": "夏夜，萤火点点，僧人站在池边，久久望着金阁。",
    "S07": "他叫林养贤，1929年生在京都北边的舞鹤。",
    "S08": "家里是一座小寺院。他从小就口吃，一开口就被嘲笑。",
    "S09": "父亲病逝后，十六岁的他被送进金阁寺，成了见习僧。",
    "S10": "他仰头看着金阁的屋脊，眼睛里全是金光。",
    "S11": "他一边在寺里修行，一边在大谷大学读书。",
    "S12": "可口吃让他在人群里越来越沉默。",
    "S13": "战后的金阁寺，游客排队买票，寺院靠门票赚钱。",
    "S14": "他看不惯这些。他和住持之间，也慢慢有了隔阂。",
    "S15": "1950年7月1日深夜，他提着旧布包，走过回廊。",
    "S16": "金阁里面，佛像静静坐着，烛火轻轻摇晃。",
    "S17": "凌晨三点，窗口亮起一点火，接着，整座楼阁烧了起来。",
    "S18": "镜湖池里，燃烧的金阁倒映在水中，像另一片星空。",
    "S19": "没有人员伤亡。可是火起的时候，警报器没有响。",
    "S20": "屋顶塌了，五百年的国宝和足利义满的木像，全成了灰。",
    "S21": "天亮以后，废墟还在冒烟，焦黑的木头立在晨光里。",
    "S22": "那天傍晚，警方在后山找到了他。他也曾想过结束自己的生命。",
    "S23": "审讯室里，他低着头说，他嫉妒金阁的美。",
    "S24": "有时又说，他厌恶寺院里的钱味。供词前后不一。",
    "S25": "事发后，母亲被叫到京都。她一直盼着儿子当住持。",
    "S26": "她没能见到儿子。回程的火车上，她走了。",
    "S27": "1950年12月，京都地方法院判他七年。",
    "S28": "狱中，他的肺结核和精神疾病越来越重，后来提前获释。",
    "S29": "1955年，金阁重建，金光又一次洒满镜湖池。",
    "S30": "三岛由纪夫写下了《金阁寺》。美，究竟该如何守护？",
}

# ---------------------------------------------------------------- 九段（由镜头推导，只用于章节统计）
CHAPTER_TITLES = [
    ("N01", "黄金三秒钩子"),
    ("N02", "金阁之美"),
    ("N03", "口吃的少年"),
    ("N04", "孤独的修行"),
    ("N05", "起火的夜晚"),
    ("N06", "黎明与废墟"),
    ("N07", "母亲"),
    ("N08", "判决与结局"),
    ("N09", "重生与追问"),
]

CHAPTER_SHOTS = [
    ("N01", ["S01", "S02"]),
    ("N02", ["S03", "S04", "S05", "S06"]),
    ("N03", ["S07", "S08", "S09", "S10"]),
    ("N04", ["S11", "S12", "S13", "S14"]),
    ("N05", ["S15", "S16", "S17", "S18"]),
    ("N06", ["S19", "S20", "S21", "S22"]),
    ("N07", ["S23", "S24", "S25"]),
    ("N08", ["S26", "S27", "S28"]),
    ("N09", ["S29", "S30"]),
]

SOURCES = [
    {
        "id": "japanesewiki",
        "title": "Japanese Wiki Corpus「金閣寺放火事件」",
        "url": "https://www.japanesewiki.com/jp/history/%E9%87%91%E9%96%A3%E5%AF%BA%E6%94%BE"
               "%E7%81%AB%E4%BA%8B%E4%BB%B6.html",
        "supports": "1950年7月2日未明、鹿苑寺（金閣寺）舎利殿から出火し全焼、46坪が焼失；"
                    "同日夕方に寺の裏の左大文字山で林を発見し放火容疑で逮捕；"
                    "逮捕当初の動機供述、母親が京都府警の事情聴取後に帰途の山陰本線の列車から"
                    "保津峡に身を投じたこと；1950年12月28日京都地裁で懲役7年。",
    },
    {
        "id": "kinkakuji-wiki",
        "title": "百科事典「金閣寺放火事件」",
        "url": "https://ja.wikid.org/%E9%87%91%E9%96%A3%E5%AF%BA%E6%94%BE%E7%81%AB%E4%BA%8B%E4%BB%B6",
        "supports": "1950年7月2日午前3時出火、逮捕は午後5時；死傷者0；舎利殿全焼、"
                    "足利義満木像・観音菩薩像・阿弥陀如来像・仏教経巻など文化財6点焼失；"
                    "火災報知機7箇所は6月30日にバッテリーが焦げ付いて使えなくなっていた；"
                    "林承賢（本名・林養賢）は1929年3月19日生まれ、舞鶴市成生出身、大谷大学学生；"
                    "服役中に結核と統合失調症が悪化し、1956年3月7日に26歳で病死。",
    },
    {
        "id": "note-2025",
        "title": "「今日は何の日：7/2 金閣寺放火事件」（2025-07-01）",
        "url": "https://note.com/nt_univ/n/n03f12e9e8887",
        "supports": "応永4年（1397年）足利義満建立の金閣；動機として「美への嫉妬」「世間を"
                    "騒がせたかった」「金閣など残しておくのは無意味」；母親は息子が面会を拒否した後、"
                    "帰郷の電車で保津峡に身を投じた（49歳）；三島由紀夫『金閣寺』と水上勉"
                    "『金閣炎上』の位置づけ。",
    },
    {
        "id": "nhk-another-stories",
        "title": "NHK「アナザーストーリーズ 運命の分岐点 金閣炎上」（2023-10-20）",
        "url": "https://plaza.rakuten.co.jp/sinoblog/diary/202111240000/",
        "supports": "event 前に所持品を売って金を用意していたこと、左大文字山に逃げ込んだこと、"
                    "動機として美への嫉妬・世間への示威・寺の関係者への怨恨が挙げられるが"
                    "真意は不明であること、母親が息子の面会を拒否されたこと。",
    },
    {
        "id": "kinkakuji-official",
        "title": "鹿苑寺（金閣寺）公式サイト「金閣」",
        "url": "https://www.shokoku-ji.jp/kinkakuji/",
        "supports": "金閣（舎利殿）は1397年（応永4年）足利義満による北山殿を起源とし、"
                    "1950年の焼失後に1955年に再建されたこと；鏡湖池に映る姿が象徴とされること。",
    },
    {
        "id": "mishima-1956",
        "title": "三島由紀夫『金閣寺』（新潮社、1956年）",
        "url": "https://www.shinchosha.co.jp/book/105002/",
        "supports": "1950年の金閣寺放火事件を素材に書かれた小説であること（本片只提及书名，"
                    "不复述小说情节）。",
    },
]

PRINCIPLES = [
    "全片30个镜头全部由 Agnes Video 2.5 Flash 生成连续运动片段（720P 源片，后期放大到 "
    "1920×1080 · 24fps），禁止静态图加推拉代替；每个镜头只出现一次。",
    "每条提示词自动以【STYLE】开头、以【NEGATIVE】结尾；出现人物时自动拼接对应【角色设定】；"
    "2.5 Flash 不接受独立 negative_prompt 字段，红线因此写在提示词正文里。",
    "全片不出现自杀、自残的方法与过程，不出现遗体、伤口或血腥；林养贤与其母亲的结局只用"
    "空镜、物件与环境表现（S22 只拍到有人赶来、S26 只拍空座位与小布包）。",
    "真实人物一律为风格化形象，非真实肖像；足利义满只以剪影出现，不给面部。",
    "镜湖池的水面倒影是全片视觉主线：S01 完美倒影 → S02 火光撕开 → S18 燃烧倒影 → S30 重生倒影。",
    "旁白一镜一句：每镜一条独立配音与一条同起止字幕；保留自然语速，必要时最多加速 1.55 倍，"
    "禁止慢放填满时长。",
    "前半段（1–4 段）以唯美、静谧为主；S17–S18 起火为全片视觉高潮；后半段转冷转静并逐渐收束。",
    "转场：前半段用樱花花瓣飘落，火灾段用火星，后半段用雾气叠化（0.3 秒）。",
    "片尾标题由后期叠加，S30 的生成画面里没有任何文字；全片唯一允许出现文字的是 S30 的片尾卡。",
]

PRESENTATION = {
    "cover": {
        "layout": "16:9；左侧一座金色楼阁，右侧是同一座楼阁的燃烧倒影，中间一条水面分界线；"
                  "主标题压在左侧水面之上，副标题在下方，关键词金色加黑边",
        "text": "最美的建筑",
        "subtext": "被一个21岁的僧人烧成了灰",
        "style": "金色粗体字、黑色描边；左半取自 S01 金阁与倒影，右半取自 S18 燃烧倒影，"
                 "水面分界线为后期绘制，不是静态图替代视频",
    },
    "end_title": "金阁寺纵火案",
    "end_subtitle": "京都 · 1950 · 美与毁灭",
    "end_note": "AI动画情景复原 · 非真实影像",
    "end_question": "美，究竟该如何守护？",
    "highlight_keywords": [
        "五百多年", "1950年", "僧人", "灰", "鹿苑寺", "1397", "足利义满", "金箔", "镜湖池",
        "樱花", "白雪", "萤火", "林养贤", "1929", "舞鹤", "口吃", "嘲笑", "父亲", "十六岁",
        "见习僧", "大谷大学", "沉默", "游客", "门票", "住持", "隔阂", "7月1日", "布包", "回廊",
        "佛像", "烛火", "凌晨三点", "火", "倒影", "警报器", "没有响", "国宝", "后山", "供词",
        "嫉妒", "母亲", "七年", "肺结核", "1956年", "二十六岁", "1955年", "重建", "三岛由纪夫",
        "金阁寺", "美", "守护",
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
        {"at": 0, "name": "空灵尺八与古筝、晨雾与风铃；第6秒低沉大太鼓一记打断", "kind": "music_sfx"},
        {"at": 11, "name": "古筝与竹笛、风铃轻响；樱花段加入水波与鸟鸣", "kind": "music_sfx"},
        {"at": 35, "name": "悲伤二胡与钢琴、海浪与海风、蝉鸣", "kind": "music_sfx"},
        {"at": 59, "name": "压抑低音弦乐、心跳般低频、扫帚与石板声", "kind": "music_sfx"},
        {"at": 85, "name": "太鼓与尺八渐强、木头燃烧爆裂声、火星与风声", "kind": "music_sfx"},
        {"at": 107, "name": "消防车钟声、水柱冲击与蒸汽、木头坍塌的低频轰鸣", "kind": "music_sfx"},
        {"at": 130, "name": "安静的钢琴与低吟尺八、台灯与纸笔声", "kind": "music_sfx"},
        {"at": 150, "name": "火车行进与铁轨声、雾气般的弦乐、法槌一记", "kind": "music_sfx"},
        {"at": 168, "name": "空灵古筝与金箔声、游客的低语、水面回声", "kind": "music_sfx"},
        {"at": 176, "name": "古筝最后一个音在水面上消散，最后0.8秒淡出至静音", "kind": "music_sfx"},
    ],
    "douyin_title": "日本最美的建筑，被一个21岁的僧人烧成了灰",
    "hashtags": ["#金阁寺", "#真实事件", "#日本", "#三岛由纪夫", "#京都", "#3D动画", "#历史"],
    "release_intro": (
        "1950年7月2日凌晨三点，京都金阁寺起火了。\\n\\n"
        "这座贴满金箔的三层楼阁，从1397年足利义满建造起，在镜湖池边站了五百多年。"
        "那一夜，寺里的火灾警报器没有响；一个小时后，国宝舍利殿和里面的足利义满木像，"
        "都成了灰。\\n\\n"
        "放火的人，是寺里21岁的见习僧林养贤。他从小严重口吃，一开口就被嘲笑；"
        "父亲早逝，母亲盼着他有朝一日当上住持。战后的金阁寺游客不断，寺院靠门票赚钱，"
        "他越来越看不惯，也和住持渐渐有了隔阂。\\n\\n"
        "他供述的动机前后不一：有时说嫉妒金阁的美，有时说厌恶寺院里的钱味。\\n\\n"
        "1950年12月，京都地方法院判他有期徒刑七年。狱中结核与精神疾病恶化，他提前获释，"
        "1956年3月7日去世，年仅26岁。他的母亲在事发后从京都返乡的路上离开了人世，"
        "本片对此只以空镜与物件表现。\\n\\n"
        "金阁在1955年重建，金光依旧。三岛由纪夫以这起事件写成了小说《金阁寺》。\\n\\n"
        "画面为AI动画情景复原，不是历史影像；真实人物均为风格化形象。"
    ),
}

REFERENCE_IMAGES = [
    {"file": "reference/01-kinkaku-spring.png",
     "description": "金阁寺与镜湖池定稿（春）：三层金色楼阁、松树、石径、满开樱花与水面倒影"},
    {"file": "reference/02-kinkaku-winter.png",
     "description": "金阁寺冬景定稿：屋顶与松枝积雪、金箔在雪光中发亮、池面薄冰与倒影"},
    {"file": "reference/03-ryozen-novice.png",
     "description": "林养贤定稿：21岁见习僧，瘦弱、剃光头、灰色作务衣，低头（风格化形象，非真实肖像）"},
    {"file": "reference/04-young-ryozen.png",
     "description": "少年林养贤定稿：十几岁、旧式学生服、布包、孤独的眼神（风格化形象）"},
    {"file": "reference/05-mother.png",
     "description": "母亲定稿：49岁、朴素和服、低发髻、手里攥着小布包（风格化形象）"},
    {"file": "reference/06-maizuru-temple.png",
     "description": "舞鹤定稿：海边小寺院的山门、经幡、灰蓝海面与渔村屋顶"},
    {"file": "reference/07-interior-buddha.png",
     "description": "金阁内部定稿：佛像、烛火、足利义满木像的金色轮廓、暗部木构"},
    {"file": "reference/08-fire-night.png",
     "description": "起火之夜定稿：金阁被橙红火光吞没、火星逆流升空、池面倒影燃烧"},
]


def chapter_bounds(shots: list[dict]) -> list[tuple[str, int, int]]:
    by_id = {shot["id"]: shot for shot in shots}
    bounds = []
    for cid, ids in CHAPTER_SHOTS:
        members = [by_id[sid] for sid in ids]
        start = min(shot["start"] for shot in members)
        end = max(shot["start"] + shot["duration"] for shot in members)
        if any(not (start <= shot["start"] < end) for shot in members):
            raise ValueError(f"Chapter {cid} shot range is not contiguous")
        bounds.append((cid, start, end))
    return bounds


def build() -> dict:
    shots = []
    cursor = 0
    for index, (sid, duration, camera, characters, variant, prompt) in enumerate(SHOT_ROWS):
        characters = [role for role in characters if role in CHARACTERS]
        # 单角色镜头用该角色的固定 seed，双人/无人镜头用镜头 seed：同一张脸跨镜更稳。
        seed = CHARACTER_SEEDS[characters[0]] if len(characters) == 1 else 19500702 + index
        shots.append({
            "id": sid,
            "kind": "agnes",
            "start": cursor,
            "duration": duration,
            "narration_id": None,  # filled below from chapters
            "narration": NARRATION[sid],
            "camera": camera,
            "characters": characters,
            "style_variant": variant,
            "prompt": prompt,
            "purpose": prompt.split(".")[0].strip()[:110],
            "seed": seed,
            "seconds": duration,
            "aspect": "16:9",
            "source_size": "720P",
            "transition_out": (
                "第1–14镜之间用樱花花瓣飘落叠化；第15–22镜之间用火星转场；"
                "第23镜之后用雾气叠化（0.3秒）；不改动旁白时间轴。"
            ),
        })
        cursor += duration

    title_by_id = dict(CHAPTER_TITLES)
    chapters = []
    for cid, start, end in chapter_bounds(shots):
        members = [shot for shot in shots if start <= shot["start"] < end]
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
            "dramatic_pause_after": {"S19": 0.5, "S26": 0.5},
        },
        "sources": SOURCES,
        "presentation": PRESENTATION,
        "reference_images": REFERENCE_IMAGES,
        "fact_boundary": [
            "事件发生于1950年7月2日凌晨三点前后，地点为京都市上京区（今北区）金阁寺町的"
            "鹿苑寺（通称金阁寺）；起火的是舍利殿（金阁），全烧，无人死亡。",
            "当时寺内七处火灾报警器在6月30日因电池失效而不能工作，片中S19只用『警报器没有响』"
            "这一句，不虚构任何人的操作。",
            "烧失文物包括足利义满木像、观音菩萨像、阿弥陀如来像与佛教经卷等六件；"
            "片中只提到足利义满木像，不逐一列出未核实清单。",
            "林养贤（本名林承贤）1929年3月19日生于京都府舞鹤市成生，是大谷大学学生、"
            "鹿苑寺见习僧，事件时21岁；父亲是僧侣，已因结核去世。",
            "当天傍晚，他在寺后的左大文字山被发现并因放火嫌疑被逮捕，送医后保住性命；"
            "片中S22只拍到警方与僧人上山，不表现任何自伤方法与过程。",
            "关于动机，公开记录为他曾供述『对美的嫉妒』『想轰动世间』『对寺方的不满』等，"
            "前后并不一致，真意不明；片中保留『供词前后不一』这一表述，不给单一结论。",
            "其母在京都接受警方问询后，于返回途中在保津峡附近身亡；片中只用站台、"
            "空座位与布包表现，不出现任何方式或过程，也不表现遗体。",
            "1950年12月28日京都地方法院判处有期徒刑七年；狱中结核与精神疾病恶化，"
            "后提前获释，1956年3月7日病死，年仅26岁。",
            "金阁于1955年重建；三岛由纪夫1956年出版小说《金阁寺》，本片只提及书名，"
            "不复述小说情节，也不把小说当作史实。",
            "所有画面为AI动画情景重现，不是历史影像；真实人物均为风格化形象，非真实肖像。",
        ],
    }


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def visible(text: str) -> int:
    return sum(1 for ch in text if ch.isalnum() or "\u3400" <= ch <= "\u9fff")


def write_screenplay(story: dict) -> None:
    lines = [
        f"# {story['title']}",
        "",
        f"三分钟横屏悬疑动画短片 · 1920×1080 · {story['fps']}fps · 180秒 · "
        f"{len(story['shots'])} 个 Agnes Video 2.5 Flash 动态镜头 · 一镜一句中文旁白",
        "",
        "> 画面为 AI 动画情景重现，不是历史影像；真实人物均为风格化形象，非真实肖像。",
        "> 不出现自杀、自残的方法与过程，不出现遗体、伤口或血腥；结局只用空镜、物件与环境表现。",
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
            f"### {start//60:02d}:{start%60:02d}—{end//60:02d}:{end%60:02d}　{chapter['title']}",
            "",
            f"> {chapter['text']}",
            "",
            "| 镜号 | 时长 | 旁白（=字幕） | 画面与运镜 |",
            "|---|---|---|---|",
        ]
        for shot in story["shots"]:
            if shot["id"] in chapter["shot_ids"]:
                lines.append(
                    f"| {shot['id']} | {shot['duration']}s | {shot['narration']} | "
                    f"{shot['camera']} · {shot['prompt'][:150]}… |"
                )
        lines.append("")
    lines += ["## 来源", ""]
    lines += [f"- [{s['title']}]({s['url']})：{s['supports']}" for s in story["sources"]]
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
            "voice_description": "低沉悬疑男声；语速沉稳、句尾收得轻，像真实犯罪纪录片",
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
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                             encoding="utf-8")


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
        f"{len(story['shots'])} 个 Agnes Video 2.5 Flash 动态镜头\n\n"
        "**核心钩子：** 日本最美的建筑，被一个21岁的见习僧烧成了灰；警报器那天没有响\n\n"
        "## 四列分镜表\n\n"
        "| 镜号 | 时间 | 口播（=字幕） | 画面 | 运镜 |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## 声音设计\n\n| 时间 | 声音 |\n|---|---|\n" + events
        + "\n\n## 事实边界\n\n"
        "- 时间、地点、烧失文物、判决与身后事，均以日文公开资料与寺院公开沿革为准。\n"
        "- 动机部分只保留公开供词中『前后不一』的事实，不给单一结论。\n"
        "- 不出现自杀、自残的方法与过程，不出现遗体、伤口或血腥；结局只用空镜、物件与环境表现。\n"
        "- 真实人物一律为风格化形象；画面为AI动画情景重现，不是历史影像。\n\n"
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
    seconds = story["shots"][-1]["start"] + story["shots"][-1]["duration"]
    print(f"WROTE {HERE/'story.json'} — {len(story['shots'])} shots, {seconds}s, "
          f"{total} visible narration characters ({total/seconds:.2f}/s)")


if __name__ == "__main__":
    main()

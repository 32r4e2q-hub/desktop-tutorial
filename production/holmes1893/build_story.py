#!/usr/bin/env python3
"""唯一内容源：《H·H·霍姆斯：传说里的杀人城堡》

运行 ``python3 production/holmes1893/build_story.py`` 会写出 story.json、screenplay.md、
audio/manifest.json、抖音脚本.md 与抖音发布文案.md。30 个镜头全部是 Agnes Video 2.5 Flash
（720P 源片，后期放大到 1920×1080 · 24fps）生成的连续运动片段；旁白一镜一句，字幕与配音同起止。

双层画面：传说想象（S09/S12/S13/S14）用「泛黄旧报纸版画」STYLE，其余为写实 3D 情景复原；
S14 是两层之间的「撕裂转场」。

事实边界：赫尔曼·韦伯斯特·马吉特（Herman Webster Mudgett，即 H·H·霍姆斯）1861 年生于
新罕布什尔州吉尔曼顿，1884 年毕业于密歇根大学医学系；1893 年芝加哥世博会期间他在英格尔伍德
经营药店并建起三层大楼；1894 年他与本杰明·皮泰泽尔合谋骗保一万美元，皮泰泽尔死亡、三个孩子
（艾丽斯 15、内莉 11、霍华德 8）失踪；费城侦探弗兰克·盖耶追查到多伦多与印第安纳波利斯；
1895 年霍姆斯因谋杀皮泰泽尔受审并被判死刑，1896 年 5 月 7 日在莫亚门辛监狱被处以绞刑。
片中不出现遗体、伤口、血腥、武器与任何暴力过程；孩子只以剪影、背影和遗物出现；
人物一律为风格化形象，不复制任何真实肖像。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
TITLE = "H·H·霍姆斯：传说里的杀人城堡"
FILM_NAME = "H·H·霍姆斯_传说里的杀人城堡_三分钟_带声音.mp4"
BRANCH = "arena/534c25c4-desktop-tutorial"
FPS = 24

# ---------------------------------------------------------------- 全局 STYLE / NEGATIVE
STYLE_PREFIX = (
    "【STYLE】Cinematic-quality 3D animated documentary reenactment, Chicago and Philadelphia, "
    "1890s America, Victorian era: the blazing electric light of the 1893 World's Columbian "
    "Exposition's White City set against the gaslit gloom of old brick streets - steam, coal "
    "smoke, lake fog; a warm amber and cold cyan-blue palette, volumetric light, finely detailed "
    "brick, stone, cast iron, brass, glass, wool and leather materials, soft ambient occlusion, "
    "cinematic depth of field, gentle film grain, rich foreground-midground-background layering, "
    "gothic suspense atmosphere. Horizontal 16:9 widescreen composition, the subject on a third "
    "line, the full horizontal width used, the lower sixth kept visually quiet for subtitles. "
    "Every clip is true continuous 3D animation with visible natural movement - breathing, "
    "walking, turning heads, blinking, hands at work, cloth and coats settling, wheels turning, "
    "steam drifting, light changing, camera parallax - never a still image with a push-in. "
    "Period-correct 1890s objects and clothing, nothing modern. All characters are stylized, "
    "never the likeness of a real person. "
)

# 传说想象画面：泛黄旧报纸版画，与写实 3D 一眼可分辨。
STYLE_PRINT_PREFIX = (
    "【STYLE｜传说想象画面｜泛黄旧报纸版画】Aged 1890s newspaper engraving brought to life as "
    "moving paper: sepia and brown-ochre palette, dense black ink hatching and cross-hatching, "
    "exaggerated gothic Victorian illustration, woodcut line work, folded and stained newsprint "
    "texture with creases, foxing and a torn edge, the sheet itself fluttering slightly, ink "
    "registration wobble, dust and paper fibre grain. The image is CLEARLY a period newspaper "
    "illustration - never photoreal, never a photograph, never a 3D render. Horizontal 16:9 "
    "widescreen framing, the lower sixth kept quiet for subtitles, and the drawing itself pulses "
    "with life: hatching shimmers, ink lines crawl, figures move in stepped engraving animation, "
    "paper edges curl, dust drifts. Absolutely no readable letters, words, headlines or numbers "
    "anywhere in the frame. Stylized Victorian figures, never the likeness of a real person. "
)

NEGATIVE_PROMPT = (
    "【NEGATIVE】readable text, letters, numbers, headlines, signage lettering, subtitles, "
    "captions, watermark, logo, gibberish writing, blood, gore, wound, corpse, dead body, body "
    "parts, human skeleton posed as a body, funeral portrait, weapon pointed at a person, gun, "
    "knife in use, violence in progress, hanging, gallows, noose, execution device, fire "
    "consuming a person, nudity, deformed hands, extra fingers, extra limbs, facial collapse, "
    "distorted anatomy, plastic skin, mannequin faces, wrong architecture, modern clothing, "
    "modern cars, smartphones, electric light fixtures later than 1893, low resolution, "
    "flicker, style drift, vertical framing, letterbox black bars inside the frame, frozen "
    "frame, slideshow, still image with artificial zoom, jump scare, ghost, supernatural glow, "
    "realistic likeness of a real person, oversaturated colours, heavy lens flare."
)

# ---------------------------------------------------------------- 角色设定（跨镜逐字复用）
CHARACTERS = {
    "holmes": (
        "【角色设定｜H·H·霍姆斯】Holmes, a fictionalized stylized gentleman in his early "
        "thirties in 1890s America: golden-brown hair neatly parted, a trim moustache, clear "
        "blue eyes, an easy confident smile; a dark three-piece suit with a crisp white collar, "
        "a dark silk tie and a gold pocket-watch chain. Charming, composed, a shade too smooth; "
        "he speaks calmly and wins people over. Keep his hairstyle, build, suit colour and "
        "facial proportions identical in every shot. A stylized period figure, never a portrait "
        "or likeness of any real person. "
    ),
    "boy": (
        "【角色设定｜少年赫尔曼】Herman as a bright fourteen-year-old New Hampshire boy in the "
        "early 1870s: short sandy-brown hair, quick clever eyes, a faint knowing smile; a worn "
        "brown student jacket over a white shirt with a stiff collar. Keep his face, hair and "
        "clothing identical in every shot. Stylized, never a likeness of any real person. "
    ),
    "student": (
        "【角色设定｜青年赫尔曼】Herman as a medical student of about twenty-two in 1884: "
        "sandy-brown hair, a thin moustache, sharp watchful eyes; a charcoal frock coat over a "
        "dark waistcoat and a high collar, an anatomy notebook under one arm. Keep his face, "
        "hair and clothing identical in every shot. Stylized, never a likeness of any real "
        "person. "
    ),
    "pitezel": (
        "【角色设定｜本杰明·皮泰泽尔】Benjamin Pitezel, a fictionalized stylized man of about "
        "forty: heavyset, round-shouldered, a full moustache, small tired eyes behind round "
        "spectacles; a brown sack suit, a bowler hat and a plain collar. Earnest, trusting, a "
        "little worn down. Keep his build, moustache and clothing identical in every shot. "
        "Stylized, never a likeness of any real person. "
    ),
    "wife": (
        "【角色设定｜皮泰泽尔夫人】Mrs Pitezel, a fictionalized stylized woman of about "
        "thirty-eight: small and upright, dark hair pinned back, a plain dark-blue 1890s day "
        "dress with a high collar and a wool shawl, a plain hat and a worn leather bag. Anxious "
        "but composed; seen mostly from behind or in three-quarter back view. Keep her silhouette "
        "and clothing identical in every shot. Stylized, never a likeness of any real person. "
    ),
    "children": (
        "【角色设定｜皮泰泽尔的三个孩子】Three children shown ONLY as soft backlit silhouettes "
        "or from behind: a tall girl of fifteen, a smaller girl of eleven with braided hair, and "
        "a small boy of eight in short trousers and a flat cap, all in plain 1894 travelling "
        "clothes with small bags. Their faces are never shown, they are never in distress and "
        "never injured; they walk, look out of windows, sleep against the glass. Keep the "
        "silhouettes' heights and clothing shapes consistent. Not portraits of real children. "
    ),
    "geyer": (
        "【角色设定｜弗兰克·盖耶】Frank Geyer, a fictionalized stylized Philadelphia detective "
        "of about forty-five: lean and weathered, a thick moustache, tired sharp eyes; a long "
        "grey trench coat over a waistcoat, a soft felt hat, a leather notebook and a pencil. "
        "Tenacious, quiet, methodical. Keep his build, moustache and coat identical in every "
        "shot. Stylized, never a likeness of any real person. "
    ),
    "crowd": (
        "【角色设定｜游客与记者】1893 fairgoers and reporters: women in dark skirts, white "
        "shirtwaists and boat-shaped straw hats, men in sack suits with bowlers and boaters, "
        "pressmen with pencils, notepads and a folding bellows camera. Period-correct 1893 "
        "American clothing, lively natural crowd behaviour, no readable insignia. Generic "
        "period figures, not portraits of real people. "
    ),
    "officials": (
        "【角色设定｜法庭与监狱人员】1890s Philadelphia court and prison staff: a judge and "
        "lawyers in black robes and high collars, jurors in dark suits, uniformed guards in navy "
        "coats with brass buttons and peaked caps, reporters with notepads. Period-correct, faces "
        "generic and unremarkable. Not portraits of real people. "
    ),
    "workers": (
        "【角色设定｜建筑工人】1890s Chicago building workers: flat caps, suspenders, rough "
        "shirts, canvas aprons, brick hods, wooden scaffolding and hand tools, soot and plaster "
        "dust on their clothes. Generic period figures, faces never prominent. "
    ),
}
CHARACTER_SEEDS = {
    "holmes": 18930501,
    "boy": 18610502,
    "student": 18840503,
    "pitezel": 18940504,
    "wife": 18940505,
    "children": 18940506,
    "geyer": 18940507,
    "crowd": 18930508,
    "officials": 18950509,
    "workers": 18930510,
}

# ---------------------------------------------------------------- 30 镜（5–7 秒／镜，合计 180 秒）
# (镜号, 起始, 时长, 运镜, 角色, 风格变体, 提示词)
SHOT_ROWS = [
    ("S01", 0, 5, "航拍从摩天轮下降，穿过人群", [], "real",
     "Night at the 1893 World's Columbian Exposition in Chicago: the White City's white classical "
     "palaces glow under tens of thousands of electric bulbs, strings of light tracing every "
     "cornice and dome, the great Ferris wheel turning slowly on the right with every cabin lit, "
     "fireworks bursting high above the lagoon and drifting smoke catching the light, dense "
     "crowds strolling the promenades in 1893 dress, electric launches gliding on the black water "
     "below. Camera: one continuous aerial descent from high above the Ferris wheel, gliding down "
     "and forward over the crowd, the wheel's spokes sliding past the frame edge. Real motion: "
     "rotating wheel, rising fireworks with falling sparks, drifting smoke, walking crowds, "
     "rippling reflections, flickering bulbs. Luxurious, dreamlike, alive. No readable text."),

    ("S02", 5, 5, "低机位缓慢推近，直到大门自掩", [], "real",
     "The same night, four blocks from the fair: a narrow gaslit Chicago street corner, and the "
     "three-storey dark brick building that fills the left two thirds of the frame. Every window "
     "on the upper floors is black except one on the second floor, where a single lamp gutters "
     "and brightens at irregular intervals; three street lamps burn warm amber and clearly light "
     "the brickwork, the iron fire escape and the wet cobbles, with a soft cone of fog around "
     "each flame. A horse-drawn cab has just turned the corner, its lamps shrinking away. As the "
     "camera nears, the heavy front door swings shut by itself with a soft click, and a curtain "
     "twitches in the lit window. Camera: very low angle, one slow continuous dolly forward along "
     "the wet cobbles toward the door. Real motion: swaying lamp light, flickering window, "
     "drifting fog, a loose shutter, the closing door. Clearly legible shadows, never crushed to "
     "black. No people, no readable text."),

    ("S03", 10, 7, "中景，缓慢推近书桌与男孩", ["boy"], "real",
     "A New Hampshire farmhouse room in the early 1870s, late afternoon: low sun through a small "
     "window lays an amber parallelogram across a scarred wooden desk; on it a thick medical "
     "textbook, a hand-drawn anatomy leaflet, a slate and a stub of pencil. The boy Herman sits "
     "at the desk, reading hard, lips moving silently, one finger tracing a line; he glances up "
     "at the window with a quick clever smile, then back down and writes. Camera: medium shot, "
     "slow continuous push in over his shoulder toward the open book. Real motion: breathing, "
     "blinking, page turning, pencil moving, dust in the sunbeam, curtain stirring. No readable "
     "text, no letters on the pages."),

    ("S04", 17, 7, "中景，过肩镜头，缓缓横移", ["student"], "real",
     "A university anatomy lecture room in 1884, restrained and non-graphic: tiers of wooden "
     "benches, tall shelves of leather-bound books, a blackboard covered in rubbed-out abstract "
     "chalk smudges, and in a corner a lacquered anatomical model of a torso under a glass dome. "
     "The young Herman, in a charcoal frock coat, leans toward a fellow student and speaks low, "
     "his eyes flicking sideways; the other student nods and writes. Camera: over-the-shoulder "
     "medium shot that drifts slowly sideways past the bookshelves. Real motion: whispering "
     "heads turning, pen moving, a book being pulled from a shelf, dust in the window light. "
     "Nothing graphic is shown; no readable text."),

    ("S05", 24, 6, "大特写，慢动作，红章落下", ["holmes"], "real",
    "Extreme close-up on a desk under a warm desk lamp: a printed insurance form lies on green "
    "baize beside a brass inkwell and a pen. A man's hand - a gold signet ring, a clean cuff - "
    "sets down the pen, picks up a heavy rubber stamp, presses it onto a red ink pad and brings "
    "it down on the paper; the stamp lifts and a red blot blooms on the page. His fingertips tap "
    "the desk twice, satisfied, and one corner of the form lifts in a draught. Camera: locked "
    "extreme close-up that eases in during the stamp's fall, half-speed. Real motion: stamp "
    "descending, ink bloom spreading, fingers tapping, paper flexing, lamp glow breathing. No "
    "readable text - the form's lines stay abstract and unreadable."),

    ("S06", 30, 5, "俯拍，名片依次翻转", ["holmes"], "real",
     "Overhead close shot of a polished walnut desk under a single warm lamp: three calling "
     "cards lie face up in a neat row, each one a cream card with a thin dark border and, "
     "standing up in raised relief from the middle of the card, a small dark metal-stamped head "
     "and shoulders in profile - the same sharp-nosed, high-collared profile on all three. Each "
     "card is visibly different in age and tone: one crisp white, one yellowed, one"
     " smoke-stained, the same face on every one, as though one man wore many names. A fourth "
     "card slides into the row face up, showing the profile again, then a hand rests over the row "
     "for a beat and draws the cards away out of frame. The relief profile is in sharp focus, "
     "the desk falling off into warm shadow. Camera: top down, steady, a slow drift and a small "
     "push as the cards are drawn away. Real motion: cards sliding, the relief's shadow moving as "
     "the lamp flickers, fingers, dust through the lamplight. No blank white cards, no text, no "
     "letters or numbers."),

    ("S07", 35, 7, "中景环绕，药店柜台", ["holmes", "crowd"], "real",
     "An Englewood street-corner drugstore in 1886, warm and busy: shelves of coloured glass "
     "bottles - cobalt, amber, emerald - catching the afternoon sun, a marble soda counter, "
     "brass scales, a ceiling fan turning slowly. Holmes, in a neat dark suit and white apron, "
     "serves two customers behind the counter: he measures powder onto a brass scale, smiles, "
     "wraps a parcel, and hands it over with a small bow; customers laugh, a boy counts coins. "
     "Camera: a continuous medium orbit around the counter, keeping Holmes on the left third. "
     "Real motion: weighing, wrapping, coins, ceiling fan, customers shifting, sunlight moving. "
     "No readable text on labels - bottles and boxes are lettered abstractly. Photoreal cinematic rendering with natural human proportions and real skin texture, matching the rest of the film - no cartoon or toy-like faces, no exaggerated features."),

    ("S08", 42, 7, "航拍俯拍，缓慢下降，脚手架交错", ["holmes", "workers"], "real",
     "The empty lot across the street from the drugstore, 1887: a three-storey brick building "
     "rising inside a lattice of wooden scaffolding, scaffold planks stacked, a hand-cranked "
     "hoist lifting a pallet of bricks, mortar tubs, ladders, and eight or nine workers - some "
     "laying brick, some carrying hods, one coiling rope. Below, Holmes stands on the pavement "
     "with a rolled blueprint under his arm, pointing up at the facade; a worker nods, and a "
     "group of newly hired men walks in from the street while another small crew is paid off and "
     "leaves with their bundles. Camera: aerial descent from above the roofline, drifting down "
     "and across the scaffolding to the street. Real motion: hoist rising, bricks passing hand "
     "to hand, dust, scaffolding creaking, workers walking. No readable text anywhere."),

    ("S09", 49, 6, "剖面视角缓慢移动，走廊像迷宫", [], "print",
     "Cutaway view of the three-storey building, drawn as an 1890s newspaper illustration: the "
     "front wall removed so the interior shows as a maze of corridors that double back on "
     "themselves; doors open into windowless rooms; a staircase climbs to a dead end; on the "
     "floor of one room a trapdoor stands open onto darkness, and a chute runs down through the "
     "walls to the cellar; on the top floor a sealed shaft and a dark iron closet with no "
     "windows. Ink hatching moves across the walls like breath, a hatched figure walks a "
     "corridor and disappears around the corner. Camera: slow lateral glide along the cutaway, "
     "from the ground floor to the attic, one continuous move. Real motion: crawling hatching, "
     "dust motes, the paper edge curling at the top of frame. No readable letters, words or labels."),

    ("S10", 55, 5, "低机位，逐渐推近，招牌亮起", ["holmes"], "real",
     "Night, the finished building seen from the pavement opposite: three storeys of dark red "
     "brick, some windows shuttered, one ground-floor shopfront blazing with warm light. On the "
     "facade a sign made of painted panels and gas jets glows and shimmers into brightness - the "
     "lettering is abstract, ornamental and unreadable. Holmes steps out of the lit doorway in "
     "his dark suit, spreads one hand in welcome toward a passing couple, and gives a small "
     "theatrical bow as they hesitate and then step inside. Camera: low angle, slow push in "
     "across the street toward the entrance. Real motion: gas jets pulsing, welcoming gesture, "
     "coat moving, couple walking, smoke drifting. No readable text on the sign."),

    ("S11", 60, 7, "广角横移，人潮与车站", ["crowd"], "real",
     "Daytime at the 1893 fair, in one continuous wide lateral move: first the crowded lagoon "
     "promenade with parasols, straw boaters, children riding on their fathers' shoulders "
     "watching fireworks smoke drift; then the move carries past a railway platform crowded with "
     "arrivals - young women with carpet bags, families with trunks, a conductor with a raised "
     "hand - while a black steam locomotive breathes at the buffers and a porter wheels a cart. "
     "Camera: wide lateral travelling shot at chest height, the crowd passing close to the lens. "
     "Real motion: walking, steam, waving, head turns, a train's wheels creeping, flags snapping. "
     "Joyful and overwhelming. No readable text."),

    ("S12", 67, 7, "中景背影跟拍，门缓缓关上", ["holmes"], "print",
     "Newspaper-illustration scene, engraved in black ink on brown paper: a young woman in a "
     "travelling coat, a small hat and a carpet bag walks down a patterned hotel corridor, "
     "glancing back over her shoulder once; ahead of her a gentleman in a dark suit and top hat "
     "holds a door open with an inviting gesture, his face a shadowed hatched oval. She steps "
     "through; the door swings and closes; the corridor is suddenly empty, ink hatching rising "
     "like smoke along the walls, one gas bracket flickering. Camera: medium tracking shot "
     "behind her, following to the door and holding on the closed door. Real motion: walking, "
     "the bag swinging, the door closing, hatching crawling, paper grain shifting. Nothing "
     "violent happens; no readable letters or words."),

    ("S13", 74, 6, "缓慢横移，墙上贴满失踪启事", [], "print",
     "Newspaper-illustration scene: a brick wall on a wet street corner, pasted edge to edge "
     "with missing-person notices - each engraved portrait is only an abstract ink silhouette in "
     "an oval frame, and every line of type below is unreadable hatching. Wind lifts the "
     "corners; one sheet tears free and tumbles across the cobbles into a puddle; a woman's "
     "shadow passes across the wall and stops. Camera: slow lateral glide along the wall, "
     "shallow focus, ending on the fluttering sheet. Real motion: paper lifting, ink hatching "
     "shimmering, rain beading, one sheet tumbling. No readable letters, words or names."),

    ("S14", 80, 5, "特写，撕裂慢动作，白光", ["holmes"], "real",
     "The tear: a large sheet of aged newsprint fills the frame, its engraved scene printed in "
     "brown ink. Two hands take the sheet and tear it straight down the middle in slow motion - "
     "fibres snapping, a jagged white rip opening wider - and through the tear a cold, "
     "photoreal 1890s interior glows with true colour: a gaslit office, a wooden desk, the edge "
     "of a ledger. The torn halves curl back out of frame and the photographic image floods the "
     "whole width; a single bright flash fires along the tear and fades. Camera: locked "
     "close-up, the tear travelling down the centre of frame. Real motion: tearing paper, "
     "curling halves, dust, the flash's afterglow. No people's faces, no readable text."),

    ("S15", 85, 6, "中景，过肩切换，费城办公室", ["holmes", "pitezel"], "real",
     "A dim Philadelphia office in 1894, overcast light through a tall dirty window: a heavy "
     "wooden desk under a green glass lamp, an inkstand, a rubber stamp, a wall safe, and a "
     "printed policy document spread flat between two men. Holmes sits with his back to the "
     "window, tracing a line on the document with a pencil, calm and persuasive; Pitezel sits "
     "across from him, bowler on his knee, leaning in, nodding. Camera: holds over Pitezel's shoulder, "
     "then glides to Holmes's side of the desk. Real motion: pencil moving, heads "
     "nodding, a page lifting, the lamp smoking slightly, rain on the glass. The document stays "
     "unreadable. No readable text."),

    ("S16", 91, 6, "中景，缓慢推近水杯", ["holmes", "pitezel"], "real",
     "The same office, dusk: a wall clock reads a quarter to six (hands only, no numerals), the "
     "window grey-blue, a single lamp lit. Pitezel sits upright, hopeful, patting the pocket "
     "where the policy sits; Holmes smiles warmly, lifts a glass of water from the tray, and "
     "offers it across the desk. Pitezel takes it with both hands. Camera: pushes slowly "
     "past Pitezel's shoulder until the glass and Holmes's steady hand fill the right third, the "
     "light on the water trembling. Real motion: glass passing hands, water surface shaking, "
     "clock ticking, breathing, smile. Nothing violent; no readable text. Photoreal "
     "cinematic rendering with natural human proportions, real skin texture, subtle pores "
     "and fine wrinkles, matte wool and linen fabrics, matching the rest of the film - no "
     "cartoon, toy-like or caricatured faces, no oversized eyes or noses, no plastic skin."),

    ("S17", 97, 6, "低机位，缓慢推近，门外一双皮鞋", ["holmes"], "real",
     "Night, a narrow Philadelphia boarding-house third-floor corridor: patterned wallpaper, a "
     "turned wooden banister, one gas bracket. At the end, a door stands ajar; the lamplight "
     "inside dims, gutters, and goes out. From the darkness a man's silhouette - dark suit, "
     "shoulders squared - steps out, pulls the door quietly shut, and walks toward the camera "
     "past a pair of men's boots set neatly outside the neighbouring door; his face stays in "
     "shadow as he passes out of frame. Camera: low angle, motionless apart from a slow creep "
     "forward. Real motion: gas bracket dimming, door closing, silhouette walking, a coat "
     "brushing the frame. No body, no violence, no blood, no readable text."),

    ("S18", 103, 5, "中景，慢动作，钞票推过来", ["holmes", "officials"], "real",
     "An insurance company counter in 1894: dark wood, brass grilles, tall ledgers, a clerk with "
     "green eyeshade and sleeve garters. Holmes stands at the counter in his dark suit and lays "
     "a folded certificate flat; the clerk presses a brass stamp, writes an entry in the ledger, "
     "and slides a thick stack of banknotes across the polished wood. Holmes gathers it with one "
     "hand, tips his hat, and his easy smile widens as he turns away. Camera: medium shot, "
     "half-speed, easing from the stamp to the banknotes to his face. Real motion: stamp, pen "
     "scratching, notes sliding and fanning, hat tipping, shoulders turning. No readable text on "
     "certificates, ledgers or notes."),

    ("S19", 108, 6, "中景侧面，火车站台上的告别", ["holmes", "children", "wife"], "real",
     "A steam railway platform in the autumn of 1894: iron columns, a soot-darkened glass roof, "
     "porter's barrows, steam rolling along the platform under a grey sky. Holmes waits at the "
     "carriage door with a small case; three children stand before him in travelling coats, "
     "their figures backlit as soft silhouettes - the tallest girl, the middle girl with braids, "
     "the small boy with a cap - each with a little bag. They turn and wave toward their mother, "
     "who stands further back, holding her shawl, and nods, then lifts a hand. Camera: medium "
     "side-on shot, slowly tracking with the group. Real motion: steam, waving arms, coats in "
     "the wind, the train breathing, the mother's nod. Faces of the children never shown; no "
     "distress; no readable text."),

    ("S20", 114, 6, "车厢内横移，窗外灯掠过", ["holmes", "children"], "real",
     "Inside a night train carriage in 1894: a warm lamp in a frosted ceiling globe, buttoned "
     "plush seats, a rack of bags, rain streaks on the black window. The three children are "
     "asleep against the glass as silhouettes, the boy's cheek on the pane, the girls' heads "
     "tipped together; the sleeping car sways gently. Across the aisle Holmes sits with his hat "
     "on his knee, unfolding a sheet of paper covered in abstract unreadable addresses, "
     "studying it, his eyes lifting to the children and back down. Camera: slow lateral move "
     "along the carriage, city lights sweeping past outside and striping the interior. Real "
     "motion: train sway, passing lights, breathing, paper unfolding, smoke. No readable text."),

    ("S21", 120, 5, "低角度，缓慢推近地窖门", ["workers"], "real",
     "A shabby brick house on a Toronto back lane, grey afternoon: a wooden cellar door in the "
     "yard stands ajar, one leaf propped open, a lit lantern left on the top step with dust "
     "turning in its glow; wind moves a sheet of newspaper across the yard, a bare lilac bush "
     "trembles, the cellar doorway is only a wedge of darkness. A workman's shadow crosses the "
     "fence and is gone. Camera: low angle at ground level, one slow continuous push toward the "
     "open cellar door. Real motion: lantern flame, drifting dust, moving paper, branch "
     "trembling, the door leaf shifting a little in the wind. Nothing inside the cellar is "
     "shown; no people, no readable text."),

    ("S22", 125, 5, "特写，缓慢拉远，窗台小鞋", ["workers"], "real",
     "A small room in an Indianapolis cottage, 1894: rain running down a dark window pane, the "
     "hearth fire burning down to embers, an empty wooden chair. On the windowsill stands one "
     "child's worn button boot, small and scuffed, one loose lace trailing. Camera: begins tight "
     "on the boot, the rain-streaked glass behind it, and pulls slowly back across the room as "
     "the firelight dims and the shadows take the walls. Real motion: rain sliding, ember glow "
     "pulsing, lace swaying, curtains breathing. No people, no body, no distress, no readable "
     "text."),

    ("S23", 130, 7, "中景环绕，警局与地图", ["geyer", "officials"], "real",
     "A Philadelphia police office in 1894: a wall map of the eastern United States, pins and "
     "threads across it, a coal stove, filing pigeonholes, gas lamps. Geyer stands at the map in "
     "his grey trench coat, hat pushed back, a sheet of paper in his hand; he sets his finger on "
     "a city, then another, and drives a pin into a third while a senior officer beside him "
     "nods, arms folded. Camera: medium orbit around the two men, the map filling the right "
     "third. Real motion: pin pressing in, heads turning, coat moving, lamp flicker, thread "
     "tightening. No readable text on the map or paper."),

    ("S24", 137, 7, "蒙太奇快速切换，火车站与码头", ["geyer", "crowd"], "real",
     "A continuing pursuit played as one flowing montage inside a single moving shot: Geyer "
     "strides along a station platform as a steam train pulls out and steam swallows the frame; "
     "the steam clears on a hotel lobby where he unfolds a small portrait for a clerk, who "
     "shakes his head; the lobby dissolves into a harbour quay with crates and rope, where he "
     "asks a docker, and the man points along the wharf. He keeps walking through each space, "
     "coat swinging, never stopping. Camera: continuous tracking shot following him through the "
     "three spaces. Real motion: steam, walking, shaking heads, pointing, gulls, water. No "
     "readable text on signs or the portrait."),

    ("S25", 144, 6, "低机位，提灯光束，慢动作摘帽", ["geyer"], "real",
     "A Toronto cellar in 1894, non-graphic and restrained: rough brick walls, a dirt floor, "
     "cobwebs, a low beam. Geyer comes down the wooden steps with a lantern raised; its beam "
     "sweeps the wall, over an old crate and a folded child's coat, and comes to rest on a small "
     "wooden trunk in the corner, its strap unbuckled, dust thick on the lid. He stops, lowers "
     "the lantern, and slowly takes off his hat, holding it against his chest, his head bowed, "
     "his face in shadow. Camera: low angle at the foot of the steps, slow push in, half-speed "
     "for the hat. Real motion: lantern sway, beam sweeping, dust in the light, coat fabric "
     "settling. Nothing of any body is shown; no gore, no readable text."),

    ("S26", 150, 6, "中景环绕，牢房与记者剪影", ["holmes", "officials"], "real",
     "A stone prison cell in 1895: a narrow iron bed, a stool, a tin cup, a barred window high "
     "up, a candle and a stack of pages on a small table. Holmes sits at the table in shirt "
     "sleeves and waistcoat, writing steadily with a pen, calm, a faint smile; beyond the bars "
     "in the corridor, the shadows of reporters with notebooks press close, pencils moving, a "
     "guard keeping them back. Camera: medium orbit inside the cell, from his hands to his face "
     "to the corridor. Real motion: pen scratching, page turning, candle flame, shadows moving "
     "in the corridor, breathing. No readable text on the pages."),

    ("S27", 156, 6, "横向环绕全景，冷灰色调", ["holmes", "officials"], "real",
     "A Philadelphia courtroom in 1895, cold grey light: tall windows, dark panelled walls, a "
     "raised bench, the jury box with twelve seated men in dark suits, rows of spectators packed "
     "shoulder to shoulder, reporters scribbling. Holmes stands in the defendant's box in a dark "
     "suit, hands folded on the rail, composed and faintly smiling as he looks toward the bench. "
     "The judge lifts the gavel and brings it down; the room stills. Camera: a wide horizontal "
     "arc around the room, from the jury box to the defendant's box to the bench. Real motion: "
     "gavel falling, heads turning, pens moving, dust in the window shafts, coat shifting. No "
     "readable text, no violence, no restraints emphasised."),

    ("S28", 162, 6, "长走廊对称构图，缓慢推近", ["officials"], "real",
     "A prison corridor at dawn, 1896, austere and symmetrical: a long stone hall, a row of "
     "glass lamps along the wall, a heavy door at the far end with a small barred window, and a "
     "white-faced clock above it whose hands come to rest at ten minutes past ten. One by one "
     "the lamps dim and die from the near end toward the far door, each leaving a thread of "
     "smoke; the door at the end swings slowly shut, and the last lamp goes out, leaving only a "
     "pale dawn light through a high window. Camera: perfectly symmetrical long-corridor "
     "composition, one slow continuous push down the hall. Real motion: lamps dying in sequence, "
     "smoke threads, the door closing, dust. Nothing of any execution is shown; no gallows, no "
     "noose, no people; no readable text."),

    ("S29", 168, 6, "俯拍，水泥流动慢动作", ["workers"], "real",
     "A grave plot in October 1896, shot from directly above in soft grey daylight: a plain "
     "wooden coffin - pine boards, iron handles, a simple lid with no lettering - already set in "
     "the earth. Two workmen in aprons tip a wooden bucket and pour wet concrete over the lid; "
     "the grey slurry spreads, thick and slow, filling the seams, and a trowel smooths it flat "
     "in one long stroke while the second bucket is lifted into frame. A fine drizzle dimples "
     "the surface. Camera: locked overhead shot, slow-motion pour, a slight drift to the right. "
     "Real motion: pouring concrete, spreading, trowel stroke, drizzle, bucket swinging. Only "
     "the coffin lid and concrete are seen; no body, no grave ceremony, no readable text."),

    ("S30", 174, 6, "航拍缓慢上升，淡入淡出", [], "real",
     "Modern Chicago, present day: a low brick post office on the corner of a wide south-side "
     "street, delivery trucks at the kerb, a few pedestrians, plane trees. Camera: rises "
     "steadily from street level, revealing the grid of the city, then the lake haze and, far "
     "off on the horizon, the faint glitter of lights where the White City once stood. The "
     "picture gradually whitens at the edges, leaving clean empty sky in the upper third for a "
     "title added in post. Camera: one continuous aerial rise, gentle drift. Real motion: "
     "walking pedestrians, moving traffic, drifting cloud shadow, light changing, haze. No "
     "readable signage, no generated lettering - every title is added later."),
]

# ---------------------------------------------------------------- 一镜一句旁白（30 条）
# 每条都写进分镜：旁白 = 字幕，起止与镜头一致；只允许加速，不允许慢放。
NARRATION = {
    "S01": "传说，1893年芝加哥世博会旁，有一栋旅馆。",
    "S02": "住进去的人，很多再也没有走出来，也没人问起。",
    "S03": "他本名赫尔曼·马吉特，1861年生在新罕布什尔州。",
    "S04": "聪明、善谈，在密歇根大学学医；据说那时就开始用尸体骗保险。",
    "S05": "一份保险单，一枚红印章，他靠这套把戏骗过钱。",
    "S06": "后来他改名霍姆斯，搬到芝加哥，准备大干一场。",
    "S07": "1886年，他来到芝加哥，接手了英格尔伍德街角的一家药店。",
    "S08": "又在对面盖起一栋三层大楼，取名“世界博览会旅馆”。",
    "S09": "传说，楼里有暗道、活板门，还有没有窗户的房间。",
    "S10": "他不断换工人，一批走了又来，没人知道大楼全貌。",
    "S11": "1893年世博会期间，全城挤满外地游客，失踪几个人没人注意。",
    "S12": "传说，独自来游览的年轻女子，进了那栋楼，再没消息。",
    "S13": "报纸一篇接一篇地渲染，数字越写越大，两百、三百。",
    "S14": "杀人城堡的传说，就这样诞生了。",
    "S15": "但真相比传说更冷：他杀的多不是游客。",
    "S16": "1894年，他和皮泰泽尔假死骗保，一万美元。",
    "S17": "可他半路改了主意：皮泰泽尔死了，保险金归了他。",
    "S18": "让他败露的不是那座楼，而是保险诈骗。",
    "S19": "他骗皮泰泽尔的妻子，说带孩子去见父亲。",
    "S20": "艾丽斯十五，内莉十一，霍华德八岁。",
    "S21": "在多伦多，内莉和霍华德跟着他进了地窖门。",
    "S22": "印第安纳波利斯，艾丽斯只留下一只小鞋。",
    "S23": "费城侦探弗兰克·盖耶盯着地图，一个城市一个城市地划线。",
    "S24": "他沿着铁路追下去，车站、旅馆、码头，一路问过去。",
    "S25": "在多伦多的地窖，他撬开箱子，认出两个孩子的衣物。",
    "S26": "1895年，他承认杀了二十七个人，可其中有人还活着。",
    "S27": "法庭只以谋杀皮泰泽尔一案，判他死刑。",
    "S28": "1896年5月7日，他在莫亚门辛监狱被执行死刑。",
    "S29": "他要了一口木棺，还要求用水泥把它封死。",
    "S30": "能确认的只有九个人；传说和真相，哪个更可怕？",
}

# ---------------------------------------------------------------- 九段（由镜头推导，只用于章节统计与配乐）
CHAPTER_TITLES = [
    ("N01", "黄金3秒钩子"),
    ("N02", "他是谁"),
    ("N03", "传说中的城堡"),
    ("N04", "传说如何诞生"),
    ("N05", "真相更让人不安"),
    ("N06", "三个孩子"),
    ("N07", "侦探追踪"),
    ("N08", "审判"),
    ("N09", "传说与真相"),
]

SOURCES = [
    {
        "id": "wiki-holmes",
        "title": "Wikipedia: H. H. Holmes（含出生、卒日、审判、二十七人供述与八至九人可确认的说明）",
        "url": "https://en.wikipedia.org/wiki/H._H._Holmes",
        "supports": "1861-05-16 生于新罕布什尔州吉尔曼顿；1896-05-07 于费城莫亚门辛监狱被绞死；"
                    "1895 年 10 月因谋杀皮泰泽尔受审并被判死刑；供述二十七人，其中数人可证仍活着；"
                    "可确认者八人、另有一人高度可能；要求以水泥封棺并深埋。",
    },
    {
        "id": "wiki-ccp",
        "title": "Wikipedia: Moyamensing Prison / Philadelphia County Prison",
        "url": "https://en.wikipedia.org/wiki/Moyamensing_Prison",
        "supports": "莫亚门辛监狱为费城县监狱，1896 年 5 月 7 日的绞刑在此执行。",
    },
    {
        "id": "wiki-pitezel",
        "title": "Wikipedia: Benjamin Pitezel / Holmes insurance fraud",
        "url": "https://en.wikipedia.org/wiki/H._H._Holmes#Pitezel_killings",
        "supports": "1894 年霍姆斯与皮泰泽尔合谋以一万美元寿险假死骗保；皮泰泽尔于费城 Callowhill 街"
                    "身故；霍姆斯随后以事故证明向 Fidelity Mutual 领取一万美元；三个孩子艾丽斯（15）、"
                    "内莉（11）、霍华德（8）在辗转多伦多、印第安纳波利斯途中失踪。",
    },
    {
        "id": "wiki-geyer",
        "title": "Wikipedia: Frank Geyer（费城警探，追踪皮泰泽尔三个孩子）",
        "url": "https://en.wikipedia.org/wiki/Frank_Geyer",
        "supports": "费城警探弗兰克·盖耶受命追查失踪的三个孩子，在多伦多与印第安纳波利斯查获遗物与遗骸。",
    },
    {
        "id": "selzer",
        "title": "Adam Selzer, H. H. Holmes: The True History of the White City Devil（2017）",
        "url": "https://www.simonandschuster.com/books/H-H-Holmes/Adam-Selzer/9781510713447",
        "supports": "现代史学对“杀人城堡”传说的考据：世博期间大量“失踪游客”的说法缺乏证据；"
                    "报纸夸张渲染；可确认的受害者约为九人。",
    },
    {
        "id": "npr-2017",
        "title": "NPR / 多家媒体对 Selzer 研究的报道（2017）",
        "url": "https://www.npr.org/2017/04/09/523027310/the-man-who-was-h-h-holmes",
        "supports": "“两百人”一类的数字主要源于当时的报纸与后来的通俗读物，缺乏档案支持。",
    },
    {
        "id": "cook-county",
        "title": "Chicago Public Library / Englewood 地方史料：世博旅馆旧址今为邮局",
        "url": "https://www.chipublib.org/",
        "supports": "英格尔伍德 63 街与 Wallace 街一带的三层大楼 1895 年失火后拆除，旧址现为美国邮政建筑。",
    },
]

PRINCIPLES = [
    "全片30个镜头全部由 Agnes Video 2.5 Flash 生成连续运动片段（720P 源片，后期放大到 "
    "1920×1080 · 24fps），禁止静态图加推拉代替；每个镜头只出现一次。",
    "每条提示词自动以【STYLE】开头、以【NEGATIVE】结尾；出现人物时自动拼接对应【角色设定】；"
    "2.5 Flash 不接受独立 negative_prompt 字段，红线因此写在提示词正文里。",
    "双层画面：传说想象（S09/S12/S13/S14）用泛黄旧报纸版画的独立 STYLE，其余为写实 3D 情景复原；"
    "S14 是两层之间的撕裂转场，撕裂后画面转为写实色。",
    "不出现遗体、伤口、血腥、武器、暴力过程或绞刑场面；S17 只拍走廊与一双皮鞋，S28 只拍走廊灯灭与关门，"
    "S29 只拍棺盖与水泥。",
    "孩子只以剪影、背影与遗物出现（S19/S20/S22），不给正脸、不置于危险画面。",
    "真实人物一律风格化形象，不复制任何真实肖像；姓名、日期与公开资料一致。",
    "旁白一镜一句：每镜一条独立配音与一条同起止字幕；保留自然语速，必要时最多加速 1.55 倍，禁止慢放。",
    "『白城的灯』『漆黑的窗』『泛黄的报纸』『水泥』四个视觉母题贯穿全片，开头与结尾互相呼应。",
    "片中所有文字（标题、字幕、招牌、编号）一律后期叠加；模型提示词明确要求画面内无可读文字。",
]

PRESENTATION = {
    # 系列封面：全系列唯一版式（迷案解码人 1080×1440）。每期只换期数、两行标题和窗口截图。
    # 出封面统一走 production/series_cover.py，读的就是下面这些键；别再写回已经废弃的 16:9 版式。
    "cover": {
        "series": "谜案解码人",
        "series_episode": 2,
        "template": "production/mystery-cover-template/template.py（竖版 1080×1440，全系列唯一版式）",
        "line1": "传说里两百人失踪",
        "line2": "他只承认九个人",
        "window_shot": "S12",
        "window_at": 3.8,
        "window_y_bias": 0.5,
        "layout": "谜案解码人竖版模板：期数角标 + 两行标题 + 中间窗口放本片 S12（独自走进旅馆的年轻女子）的帧",
        "candidates": ["S12", "S07", "S10", "S11", "S09"],
    },
    "end_title": "H·H·霍姆斯",
    "end_subtitle": "芝加哥 · 1893 · 传说与真相",
    "end_note": "真实案件改编 · 部分画面为3D复原",
    # 片尾只提问，不指认、不夸大。四个字符串 = 左边数字 + 左边注 + 右边数字 + 右边注。
    "end_question": "两个数字，哪个更可怕？",
    "end_numbers": ["200", "传说里的数字", "9", "能确认的受害者"],
    "highlight_keywords": [
        "1893年", "芝加哥", "世博会", "白城", "摩天轮", "旅馆", "没有走出来", "赫尔曼·马吉特",
        "1861年", "新罕布什尔州", "密歇根大学", "骗保险", "改名", "霍姆斯", "1886年", "英格尔伍德",
        "药店", "三层大楼", "世界博览会旅馆", "暗道", "活板门", "没有窗户", "更换工人", "全貌",
        "游客", "失踪", "报纸", "杀人城堡", "传说", "真相", "1894年", "皮泰泽尔", "假死", "一万美元",
        "败露", "保险诈骗", "孩子们", "艾丽斯", "内莉", "霍华德", "十五岁", "十一岁", "八岁",
        "多伦多", "印第安纳波利斯", "侦探", "盖耶", "地图", "追踪", "地窖", "箱子", "1895年",
        "二十七个人", "死刑", "1896年5月7日", "莫亚门辛监狱", "水泥", "九个人", "哪个更可怕",
    ],
    "subtitle_style": {
        "font_size_px": 62,
        "outline_px": 3.2,
        "safe_bottom_margin_px": 76,
        "alignment": "bottom-center",
        "normal_color": "white",
        "highlight_color": "gold",
        "highlight_scale": 1.22,
    },
    "sound_events": [
        {"at": 0, "name": "摩天轮机械转动、人群喧哗、烟花炸响，管弦乐骤然变调", "kind": "music_sfx"},
        {"at": 5, "name": "煤气灯嘶鸣、风穿过窄巷、远处马车驶过、低音大提琴单音", "kind": "music_sfx"},
        {"at": 10, "name": "庄园里的座钟、翻书声、铅笔声，轻快小提琴与钢琴带一丝阴影", "kind": "music_sfx"},
        {"at": 35, "name": "药店门铃、玻璃瓶碰撞、秤砣落下、街市人声", "kind": "sfx"},
        {"at": 42, "name": "脚手架吱呀、砖块传递、吊索摩擦、远处蒸汽", "kind": "sfx"},
        {"at": 49, "name": "纸张翻页、墨线沙沙、低频脉动（传说版画）", "kind": "music_sfx"},
        {"at": 60, "name": "车站人潮、蒸汽机车汽笛、烟花余响", "kind": "sfx"},
        {"at": 67, "name": "走廊脚步声、门轴轻响、纸页翻动", "kind": "sfx"},
        {"at": 80, "name": "纸张撕裂声、白光嗡鸣，配乐戛然而止", "kind": "music_sfx"},
        {"at": 85, "name": "雨点打在窗上、煤气灯低鸣、低沉钢琴单音与心跳般节拍", "kind": "music_sfx"},
        {"at": 108, "name": "火车汽笛、车厢衔接声、车轮节奏，温柔而悲伤的钢琴", "kind": "music_sfx"},
        {"at": 130, "name": "地图图钉、纸张摩擦、紧张弦乐与鼓点", "kind": "music_sfx"},
        {"at": 150, "name": "钟声、铁门回响、庄严大提琴与法槌声", "kind": "music_sfx"},
        {"at": 174, "name": "城市环境音渐起、大提琴单音收尾，最后1秒静音", "kind": "music_sfx"},
    ],
    "douyin_title": "传说中杀了200人的“杀人城堡”，真相比传说更让人不安",
    "hashtags": ["#真实事件", "#HH霍姆斯", "#芝加哥", "#杀人城堡", "#悬疑", "#3D动画", "#历史真相"],
    "release_intro": (
        "1893年，芝加哥世博会的白城灯火通明，四公里外，一栋三层大楼的窗户全是黑的。\n\n"
        "传说里，那栋楼有暗道、活板门、没有窗户的房间，还有毒气管和焚尸炉；"
        "住进去的人，很多再也没有走出来。报纸说他杀了两百人，“杀人城堡”的名字就这样传开。\n\n"
        "但真正让他落网的，不是那栋楼，而是一场保险诈骗：1894年，他与同伙本杰明·皮泰泽尔"
        "合谋假死骗保一万美元，随后皮泰泽尔死亡，三个孩子——艾丽斯15岁、内莉11岁、霍华德8岁——"
        "在多伦多和印第安纳波利斯失踪。费城警探弗兰克·盖耶沿铁路一路追查，找到了他们的遗物。\n\n"
        "1895年，霍姆斯受审并被判死刑；他供述杀了二十七人，其中有人后来被证实还活着。"
        "1896年5月7日，他在费城莫亚门辛监狱被处以绞刑。\n\n"
        "历史学家今天更谨慎：两百人的数字多半来自报纸，能确认的受害者约为九人。"
        "传说和真相，哪个更可怕？\n\n"
        "画面为AI生成的三维情景复原，不是历史影像；人物为风格化形象，不对应任何真人相貌。"
        "全片不出现遗体、血腥与暴力过程。"
    ),
}

REFERENCE_IMAGES = [
    {"file": "reference/01-holmes.png",
     "description": "霍姆斯定稿：30多岁，金棕发、八字胡、蓝眼、深色三件套与怀表链，笑容亲切自信；"
                    "风格化形象，非真实肖像"},
    {"file": "reference/02-pitezel-family.png",
     "description": "皮泰泽尔一家定稿：皮泰泽尔（中年偏胖、八字胡、圆顶礼帽）、夫人（朴素长裙、披肩）、"
                    "三个孩子的剪影（15/11/8 岁）"},
    {"file": "reference/03-geyer.png",
     "description": "侦探盖耶定稿：40多岁、八字胡、风衣、软呢帽、笔记本；风格化形象"},
    {"file": "reference/04-white-city-night.png",
     "description": "白城定稿：洁白新古典主义建筑、万盏电灯、巨大摩天轮、烟花、人潮"},
    {"file": "reference/05-castle-facade.png",
     "description": "大楼定稿：英格尔伍德街角三层黑砖楼，漆黑窗户、底部一盏暖黄窗光、潮湿街道"},
    {"file": "reference/06-print-style.png",
     "description": "传说版画风格定稿：泛黄旧报纸版画、墨线排线、楼梯剖面与活板门"},
    {"file": "reference/07-drugstore.png",
     "description": "药店定稿：街角药店、五彩药瓶货架、大理石柜台、黄铜天平"},
    {"file": "reference/08-railway-1894.png",
     "description": "1894 火车与站台定稿：黑色蒸汽机车、烟尘、铁柱与玻璃顶棚、行李车"},
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
        seed = CHARACTER_SEEDS[characters[0]] if len(characters) == 1 else 18930000 + index
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
            "transition_out": "同段内硬切或轻叠化；传说版画之间用0.35秒纸张翻页擦除；"
                              "写实段落之间用0.3秒雾气叠化；S14 为撕裂转场；"
                              "不改动旁白时间轴。",
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
        "style_rumor_prefix": STYLE_PRINT_PREFIX,
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
            "dramatic_pause_after": {"S02": 0.5, "S15": 0.5},
        },
        "sources": SOURCES,
        "presentation": PRESENTATION,
        "reference_images": REFERENCE_IMAGES,
        "fact_boundary": [
            "赫尔曼·韦伯斯特·马吉特 1861 年 5 月 16 日生于新罕布什尔州吉尔曼顿，1884 年毕业于"
            "密歇根大学医学系；片中“改名亨利·霍华德·霍姆斯、迁往芝加哥”的表述与公开资料一致。",
            "1886 年起他在芝加哥英格尔伍德区经营街角药店，并在对面建起三层大楼，"
            "后被称为 World's Fair Hotel；大楼于 1895 年失火后拆除，旧址一带现为美国邮政建筑。",
            "1894 年他与本杰明·皮泰泽尔合谋以一万美元寿险假死骗保；皮泰泽尔身故，霍姆斯领取了保险金，"
            "并在案发后带走皮泰泽尔的三个孩子艾丽斯（15）、内莉（11）、霍华德（8）。",
            "费城警探弗兰克·盖耶受命追查三个孩子，在多伦多与印第安纳波利斯查获遗物与遗骸；"
            "片中以提灯与箱子表现，不呈现任何遗体。",
            "1895 年 10 月霍姆斯因谋杀皮泰泽尔受审，被判处死刑；他供述杀了二十七人，"
            "其中数人被证实当时仍然活着。1896 年 5 月 7 日他在费城莫亚门辛监狱被处以绞刑，"
            "并要求以水泥封棺、深埋。",
            "“两百人”的说法主要来自当时的报纸与后来的通俗读物，缺乏档案支持；现代研究认为可确认的受害者"
            "约为九人（含皮泰泽尔与三个孩子）。片中以“传说 vs 真相”并列呈现，不把传说当作事实。",
            "“毒气管、焚尸炉、活板门、没有窗户的房间”等细节属于当时的报纸与后世传说，片中用泛黄版画"
            "明确标注为传说想象，不作为史实叙述。",
            "所有画面为 AI 动画情景重现，人物为风格化形象，不对应任何真人相貌；"
            "不出现遗体、伤口、血腥、武器、暴力过程或绞刑场面；孩子只以剪影、背影与遗物出现。",
        ],
    }


def write_screenplay(story: dict) -> None:
    lines = [
        f"# {story['title']}",
        "",
        f"三分钟横屏悬疑动画短片 · 1920×1080 · {story['fps']}fps · 180秒 · "
        "30 个 Agnes Video 2.5 Flash 动态镜头 · 一镜一句中文旁白",
        "",
        "> 画面为 AI 动画情景重现，不是历史影像；传说部分以泛黄旧报纸版画呈现，明确标注为传说想象。",
        "> 不出现遗体、伤口、血腥、武器、暴力过程或绞刑场面；孩子只以剪影、背影与遗物出现。",
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
    lines += ["## 30 镜分镜表", "", "| 镜号 | 时间 | 秒数 | 段 | 运镜 | 风格 | 角色 | 画面职责 |",
              "|---|---:|---:|---|---|---|---|---|"]
    for shot in story["shots"]:
        start, end = shot["start"], shot["start"] + shot["duration"]
        times = f"{start//60:02d}:{start%60:02d}—{end//60:02d}:{end%60:02d}"
        roles = "、".join(shot["characters"]) or "—"
        variant = "泛黄版画" if shot["style_variant"] != "real" else "写实3D"
        lines.append(f"| {shot['id']} | {times} | {shot['duration']} | {shot['narration_id']} | "
                     f"{shot['camera']} | {variant} | {roles} | {shot['purpose']} |")
    lines += ["", "## 来源", ""]
    for source in story["sources"]:
        lines.append(f"- [{source['title']}]({source['url']})：{source['supports']}")
    lines += [
        "",
        "## 后期规范",
        "",
        "- 生成：Agnes Video 2.5 Flash，720P 源片，61 秒共享节流，断点续跑；后期放大到 1920×1080。",
        "- 配音：沉稳磁性男声；一镜一句、字幕同起止；只加速（≤1.55×），不慢放。",
        "- 字幕：白色黑边、底部安全区、关键词金色放大；左上角常驻『传说/史实』双层标签。",
        "- 转场：传说版画之间用 0.35 秒纸张翻页擦除；写实段落之间用 0.3 秒雾气叠化；"
        "S14 撕裂转场（版画被撕开，露出写实冷色画面）。",
        "- 音乐：原创程序合成（低音弦乐、大提琴、钢琴、管风琴、摩天轮机械脉冲）；旁白下压约 −18dB。",
        "- 音效：摩天轮机械声、煤气灯嘶鸣、火车汽笛、钟声、法槌、纸张撕裂。",
        "- 片尾：S30 现代芝加哥邮局，画面渐白，后期叠加金色片名『H·H·霍姆斯』与副题"
        "『芝加哥 · 1893 · 传说与真相』，最后 1 秒静音。",
        "- 封面：左侧 S02 夜色大楼、右侧 S01 白城电灯与摩天轮，中间白色撕裂裂缝，"
        "金色大字『传说 vs 真相』。",
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
            "voice_description": "沉稳磁性男声；讲故事语气，句尾收得轻，像真实犯罪纪录片",
            "narration_id": shot["narration_id"],
            "target_start": shot["start"],
            "target_duration": shot["duration"],
            "alignment": "shot-locked",
        })
    manifest = {
        "language": "zh-CN",
        "voice": story["narration_spec"]["voice_id"],
        "generation": "Arena TTS selected voice; shot lines split from nine chapter takes",
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
        "**核心钩子：** 世博会灯火通明，四公里外那栋楼的所有窗户都是黑的；"
        "传说他杀了两百人，真正让他落网的却是一场保险诈骗\n\n"
        "## 四列分镜表\n\n"
        "| 镜号 | 时间 | 口播（=字幕） | 画面 | 运镜 |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## 声音设计\n\n| 时间 | 声音 |\n|---|---|\n" + events
        + "\n\n## 事实边界\n\n"
        "- 出生、学历、迁居芝加哥、大楼与药店、保险诈骗与皮泰泽尔一家、供述二十七人、"
        "1896 年 5 月 7 日绞刑，均有公开资料可查。\n"
        "- “两百人”“毒气管”“焚尸炉”属于报纸与后世传说，片中以泛黄版画明确标注为传说想象。\n"
        "- 可确认的受害者约为九人；具体数字各资料存在差异，片中只给这一稳妥表述。\n"
        "- 不出现遗体、伤口、血腥、武器、暴力过程或绞刑场面；孩子只以剪影、背影与遗物出现。\n\n"
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

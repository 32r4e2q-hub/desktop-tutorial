#!/usr/bin/env python3
"""唯一内容源：《世田谷一家四口杀人案：留下无数线索，凶手为何仍未找到？》

运行 ``python3 production/setagaya2000/build_story.py`` 会写出 story.json、screenplay.md、
audio/manifest.json、抖音脚本.md 与抖音发布文案.md。29 个镜头全部是 Agnes Video 2.5 Flash
（720P 源片，后期放大到 1920×1080 · 24fps）生成的连续运动片段；旁白一镜一句，字幕与配音同起止。

事实边界：2000 年 12 月 30 日深夜至 31 日凌晨，东京都世田谷区上祖师谷三丁目宫泽家的
一家四口在家中遇害，案件至今未侦破。片中不出现遗体、伤口、血腥或作案过程；凶手始终只以
远景剪影出现，不复制任何真实人物的相貌。所有物证画面都是 3D 示意性复原，不冒充警方原始证物照片。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
TITLE = "世田谷一家四口杀人案：留下无数线索，凶手为何仍未找到？"
FILM_NAME = "世田谷一家四口杀人案_留下无数线索的悬案_三分钟_带声音.mp4"
BRANCH = "arena/fed820f6-desktop-tutorial"
FPS = 24

# ---------------------------------------------------------------- 全局 STYLE / NEGATIVE
STYLE_PREFIX = (
    "【STYLE】Cinematic-quality 3D animated documentary reenactment, Setagaya, Tokyo, Japan, "
    "winter in the year 2000: a quiet low-rise residential neighbourhood of narrow lanes, "
    "overhead utility poles, bare winter trees and single-family houses, with a spacious "
    "two-storey Japanese home in warm cream cladding, dark timber, frosted glass and a tidy "
    "front gate. Cold cyan-grey and deep blue-black palette with low-saturation warm amber "
    "practical light; warm amber interior lamps contrasted against cold blue-grey winter "
    "streetlight. Real building proportions, finely detailed wood, glass, metal, concrete and "
    "knitted fabric materials, volumetric light, soft ambient occlusion, cinematic depth of "
    "field, gentle film grain, rich foreground-midground-background layering. Horizontal 16:9 "
    "widescreen composition, subject near a third line, full horizontal width, lower sixth kept "
    "visually quiet for subtitles. Every clip is true continuous 3D animation with visible "
    "natural movement - breathing, walking, turning heads, blinking, hands at work, cloth "
    "settling, wind in branches, drifting steam, light or camera parallax - never a still image "
    "with a push-in. Period-correct Japanese objects and clothing of 2000, no later technology. "
    "All characters are stylized, never the likeness of a real person. "
)

# 抽象示意图单独一套风格：同样以【STYLE】开头，自动拼接；刻意做成干净的信息可视化，
# 与写实复原镜头明确区分，避免把概念图误读成现场照片。
STYLE_DIAGRAM_PREFIX = (
    "【STYLE｜概念示意｜抽象可视化】Clean cinematic 3D information graphic on a deep charcoal "
    "background, restrained cold cyan-grey and muted gold palette, fine volumetric haze, soft "
    "edges, elegant shallow depth of field and subtle film grain; deliberately abstract and "
    "clearly a conceptual diagram, not a photograph of police material. Horizontal 16:9 "
    "widescreen composition with generous negative space and the lower sixth kept quiet for "
    "subtitles. Everything breathes with real continuous motion - lines draw themselves, nodes "
    "pulse slowly, particles drift, the camera moves through depth - never a flat static "
    "slide. Absolutely no readable letters, numbers, names or logos anywhere in frame. "
)

NEGATIVE_PROMPT = (
    "【NEGATIVE】readable text, subtitles, captions, watermark, logo, gibberish lettering, "
    "blood, gore, wound, corpse, dead body, body parts, remains, funeral portrait, violence in "
    "progress, weapon striking a person, fighting, nudity, deformed hands, extra fingers, extra "
    "limbs, facial collapse, distorted anatomy, plastic skin, mannequin faces, wrong building "
    "structure, modern smartphones, modern electric cars, technology later than 2000, "
    "low resolution, flicker, style drift, vertical framing, letterbox black bars inside the "
    "frame, frozen frame, slideshow, still image with artificial zoom, jump scare, ghost, "
    "supernatural effect, clear face of an unidentified suspect, realistic likeness of a real "
    "person, oversaturated colours, heavy lens flare."
)

# ---------------------------------------------------------------- 角色设定（跨镜逐字复用）
CHARACTERS = {
    "mikio": (
        "【角色设定｜宫泽干男】Mikio, a fictionalized stylized Japanese man of 44, average build, "
        "short black hair with a soft side part, plain honest face, faint smile lines, calm and "
        "gentle presence; wearing a dark charcoal knit sweater over a collared shirt and dark "
        "trousers, the ordinary loungewear of a Japanese office worker in 2000. He works for a "
        "foreign company, loves animation, and once did puppetry and stage work. Keep his "
        "hairstyle, build, clothing colours and facial proportions identical in every shot. "
        "Never a portrait or likeness of any real person. "
    ),
    "yasuko": (
        "【角色设定｜宫泽泰子】Yasuko, a fictionalized stylized Japanese woman of 41, medium build, "
        "black medium-length hair loosely tied back, warm careful eyes, quiet and composed; "
        "wearing a beige or light-brown knit cardigan over a soft cream top and a plain long "
        "skirt. She runs a small tutoring class at home and keeps the house in gentle order. "
        "Keep her hairstyle, clothing and facial features identical in every shot. Never a "
        "portrait or likeness of any real person. "
    ),
    "niina": (
        "【角色设定｜长女妮娜】Niina, a fictionalized stylized Japanese girl of 8, small and "
        "slight, black shoulder-length bob with a straight fringe, ordinary winter children's "
        "clothes - a soft oatmeal knit and a pleated skirt. Lively but composed, she studies "
        "ballet and piano and plays with careful concentration. Never frightened, never injured, "
        "never in distress. Keep her hairstyle, clothing and face identical in every shot. "
        "Never a portrait or likeness of any real person. "
    ),
    "rei": (
        "【角色设定｜长子礼】Rei, a fictionalized stylized Japanese boy of 6, round face, short "
        "black hair, ordinary children's loungewear - a small navy sweatshirt and grey trousers. "
        "Natural child movement: short steps, quick hands, curious glances. Never injured, never "
        "in distress. Keep his hairstyle, clothing and face identical in every shot. Never a "
        "portrait or likeness of any real person. "
    ),
    "police": (
        "【角色设定｜调查警察】Fictionalized Japanese police officers of 2000: dark navy winter "
        "uniforms with plain duty belts, peaked caps and reflective outer jackets, no readable "
        "insignia or badge numbers, carrying clipboards, evidence bags and film cameras. "
        "Restrained, methodical and professional; they work outside the cordon and never show "
        "distress or excitement. Not portraits of real officers. "
    ),
    "detective": (
        "【角色设定｜刑事调查人员】Fictionalized Japanese criminal investigators, men and women "
        "aged 30 to 55, in plain 2000-era clothing - light shirts, dark sweaters, wool coats and "
        "mufflers - with notebooks, pens, paper folders, film cameras and clear evidence bags "
        "with white labels that carry no readable marks. Tired but focused; they read, compare, "
        "photograph and write. Not portraits of real investigators. "
    ),
    "relative": (
        "【角色设定｜家属】A fictionalized Japanese woman in her sixties, the family's neighbour "
        "and relative, small and stooped, short grey-black hair, in an ordinary dark navy winter "
        "coat with a wool scarf and a plain handbag; a single house key in her hand. Seen from "
        "behind, in three-quarter back view or in medium-long shot only; acting through posture, "
        "shoulders and hands. Worried and hesitant, never a clear portrait, never a likeness of "
        "a real person. "
    ),
    "silhouette": (
        "【角色设定｜未知人物剪影】An anonymous adult male figure seen only far away at night - a "
        "plain 2000-era winter coat, a dark scarf, ordinary boots and a small shoulder bag - "
        "rendered as a deep silhouette with no visible face, no features and no identifiable "
        "details. A visual concept of an unidentified person, not a claim about any real "
        "individual, never a portrait. "
    ),
}
CHARACTER_SEEDS = {
    "mikio": 20001230,
    "yasuko": 20001231,
    "niina": 20001232,
    "rei": 20001233,
    "police": 20001234,
    "detective": 20001235,
    "relative": 20001236,
    "silhouette": 20001237,
}

# ---------------------------------------------------------------- 29 镜（4–9 秒／镜，合计 180 秒）
# (镜号, 起始, 时长, 运镜, 角色, 风格变体, 提示词)
SHOT_ROWS = [
    ("S01", 0, 5, "高空缓慢下降，推向住宅", [], "real",
     "Late night in a quiet Setagaya residential lane, Tokyo, December 2000. The camera descends "
     "steadily from above the road: dark bare branches cross the top of the frame, a row of low "
     "Japanese houses with tiled roofs recedes into blue-grey haze, and the lane narrows toward "
     "one two-storey house with cream cladding on the right third. Weak amber lamplight glows "
     "behind a frosted window; the street lamp lays a long thin reflection on the asphalt; a "
     "distant pair of headlights slides past, a thread of chimney steam drifts. Camera: one "
     "continuous aerial glide downward and slightly forward, slow and steady. Real motion: "
     "swaying branches, drifting steam, travelling headlights. No people, no readable text."),

    ("S02", 5, 5, "沿围栏侧向轨道横移", [], "real",
     "Same house, same winter night, ground level. Camera: a slow lateral track along a low "
     "garden fence, past bare shrubs rimmed with frost, and through a large front window reveals "
     "the calm outline of a family living room: a low sofa, a television casting a shifting blue "
     "flicker across the wall, a dining table, a warm amber standing lamp. A sheer curtain lifts "
     "and settles in the draught; the television glow slides over the ceiling. The camera comes "
     "to rest framing only the quiet window. Real motion: curtain breathing, television light "
     "changing, thin mist passing the lens. No people visible, no crime, no readable text."),

    ("S03", 10, 7, "餐桌侧向横移，依次带出四人", ["mikio", "yasuko", "niina", "rei"], "real",
     "Warm evening interior of a Japanese family living room, December 2000: tatami-adjacent "
     "wooden floor, a low dining table with ordinary dishes, a silver CRT television and a "
     "shelf of animation tapes and books. Mikio sits at the table sorting papers and small "
     "household items; Yasuko stands beside him folding laundry on the table; Niina and Rei "
     "move through the room, the girl carrying sheet music, the boy pushing a small toy car. "
     "The window behind them is turning from pale dusk to deep blue. Camera: slow lateral "
     "trolley from the dining table toward the sofa, one continuous move. Real motion: folding "
     "hands, turning heads, blinking, cloth shifting, the boy's quick steps. No readable text."),

    ("S04", 17, 7, "由琴键向上摇至侧脸，再平移到男孩", ["niina", "rei"], "real",
     "Same living room at night: an upright piano against the wall, a warm floor lamp beside it, "
     "sheet music open on the stand with abstract unreadable notation, a low shelf of picture "
     "books and a small toy basket. Niina sits at the piano and touches a few keys softly; Rei "
     "kneels on the floor nearby arranging toy blocks, glances up and grins. She turns her head "
     "toward him with a small natural smile, then returns to playing. Camera: rise from the keys "
     "to her profile, then a smooth lateral glide to the boy, one continuous take. Real motion: "
     "breathing, blinking, small fingers on keys, block wobbling. No readable text."),

    ("S05", 24, 7, "由走廊进入客厅，最后转向时钟", ["mikio", "yasuko", "niina", "rei"], "real",
     "Same house, later that evening. Camera: a slow drift in from the dim hallway, past a wooden "
     "shoe cabinet and a hanging winter coat, and frames the living room through the open door: "
     "all four family members move about the dining table - Mikio standing with a cup, Yasuko "
     "carrying plates, the two children settling at the table with a picture book. The "
     "television shows a soft blurred glow; no readable text appears anywhere. The camera "
     "finishes on a plain wall clock with unmarked face and the darkening window beside it. "
     "Real motion: footsteps, shifting plates, a coat settling, clock pendulum. No readable text."),

    ("S06", 31, 7, "道路低机位缓慢前移", [], "real",
     "The same Setagaya lane, now fully dark, around eleven at night. The camera creeps forward "
     "at knee height along the empty asphalt: wet patches reflecting a single street lamp, "
     "overhead wires sagging against a deep blue-black sky, a parked bicycle, a garden gate "
     "standing ajar, bare branches trembling. The house windows still hold a faint amber glow "
     "that slowly dims as clouds slide over. No traffic, no people, no police lights. Camera: "
     "one continuous low dolly forward, very slow. Real motion: branch sway, drifting litter, "
     "flickering lamp glow, faint mist. No readable text."),

    ("S07", 38, 6, "室内连续移动，由一楼转向二楼", [], "real",
     "Interior of the same Japanese house, deep night, lit only by a spill of amber light from "
     "below. The camera travels along the ground-floor hallway - wooden floorboards, a closed "
     "sliding door, a telephone on a small table, shoes lined up by the entrance - then tilts up "
     "the narrow staircase toward the dark second-floor landing. Dust turns slowly in the "
     "lamplight, a curtain at the stair window breathes, a wall clock ticks. The frame stays "
     "composed and empty; nothing violent and no bodies are ever shown. Camera: one continuous "
     "handheld-steady move up the stairs. Real motion: dust, curtain, ticking pendulum. "
     "No readable text."),

    ("S08", 44, 7, "跟拍家属，随后切至警车与警察", ["relative", "police"], "real",
     "Morning of 31 December 2000, cold pale light, thin frost on the lane. A woman in her "
     "sixties in a dark winter coat walks up to the front gate of the house, hesitates, takes a "
     "single key from her handbag and steps toward the entrance; her shoulders tighten, she "
     "stops, then turns back toward the road with one hand at her mouth. In the same clip a "
     "police patrol car rolls quietly to a stop further down the lane, its roof light turning "
     "slowly without glare, and two officers in dark winter uniforms step out and walk toward "
     "the gate with measured strides. Camera: gentle tracking behind the woman, then a low "
     "angle on the arriving officers. Real motion: walking, breath vapour, coat movement, "
     "turning light. No bodies, no blood, no readable text."),

    ("S09", 51, 7, "沿警戒线低机位横移后推向入口", ["police", "detective"], "real",
     "Same house, mid-morning: a police cordon of white-and-yellow tape is tied between a garden "
     "fence and a utility pole, sagging gently in the wind. Two officers stand near the gate, "
     "one writing on a clipboard; a plain-clothes investigator crouches to place a numbered "
     "marker board face-down and photograph the ground, another talks quietly with a colleague. "
     "Behind them, the cream house, bare trees and a neighbour's wall. Camera: low lateral track "
     "past the tape so the tape sweeps the foreground, then a slow push toward the entrance. "
     "Real motion: tape trembling, breathing, pen moving, coat flaps. No readable text, no "
     "badges, no bodies, no blood."),

    ("S10", 58, 7, "由侧面移到物证台，连续三个工作动作", ["detective"], "real",
     "Interior of the house, non-graphic evidence work: a plain hallway and the corner of a "
     "living room, soft daylight through frosted glass. Three investigators in gloves work in "
     "sequence - one kneels to set down a scale card and a folded paper evidence bag beside a "
     "scuff on the floorboards, one raises a film camera and fires the shutter with a small "
     "flash, one writes steadily in a notebook with a pen. A clear plastic bag is sealed and "
     "labelled with a blank white label. Camera: one continuous move from the side to the "
     "evidence table, steady and procedural. Real motion: gloved fingers, shutter, pen, "
     "breathing, paper flexing. Nothing violent is shown; no readable writing, no blood."),

    ("S11", 65, 7, "绕衣物缓慢环绕，最后推进袖部", [], "real",
     "Studio evidence display on a matte charcoal table under soft top light: a grey raglan "
     "sweatshirt laid flat, its body pale grey and washed to a creamy tone by many washes, its "
     "sleeves and round collar a faded light purple, size L, with a faint crease across the "
     "chest. Camera: a slow arc around the garment, the light sliding over the knit so the "
     "ribbing and the raglan seams read clearly, then eases in toward the cuff and sleeve "
     "junction where the fabric is pilled and slightly stretched. A thin shadow of the sleeve "
     "moves as the light sweeps. This is a 3D illustrative reconstruction of a published "
     "description, not a photograph of police evidence. Real motion: shifting sheen, drifting "
     "dust, cloth settling. No labels, no brand marks, no readable text, no blood."),

    ("S12", 72, 7, "从证物袋横移到手帕，再近距离环绕", [], "real",
     "Same studio table, cooler side light: two folded black cotton handkerchiefs resting on a "
     "matte grey board. One is still partly inside a clear evidence bag; the other lies open, "
     "the weave visible, both ends twisted hard into tight cords, and a small clean three-"
     "centimetre slit near its centre. A blunt practice shape of a kitchen knife handle lies "
     "beside them, wrapped the way the folded cloth would wrap it, with no blade edge visible. "
     "Camera: slow lateral glide from the bag to the cloth, then a close orbit that keeps the "
     "texture in shallow focus. Real motion: fabric fibres catching light, plastic bag breathing, "
     "dust. Illustrative reconstruction; no blood, no stains emphasised, no readable text."),

    ("S13", 79, 7, "微观纹理连续移动，最后拉远", [], "diagram",
     "Abstract forensic visualisation: a pale fingerprint ridge pattern rises out of darkness "
     "like a landscape, the ridges lit from one side and slowly rotating; Camera: glide "
     "along the ridges and the pattern dissolves into a slowly turning double helix of soft "
     "cyan light, then into a bundle of textile fibres crossing each other under raking light, "
     "then pulls back to three small floating sample vials in a row. Everything is smooth "
     "scientific imagery, not a claim about any result, with no labels and no numbers. Real "
     "motion: rotation, drifting particles, light sweeping the ridges. No readable "
     "text, no readable letters, no numbers, no charts of matches, no violent imagery."),

    ("S14", 86, 7, "围绕桌面缓慢移动，最后停留在地图", ["detective"], "real",
     "Investigation office of 2000 in Tokyo, late evening: a long wooden desk covered with paper "
     "folders, a printed street map with abstract unreadable markings, small photographs laid "
     "face up in rows, a green-shaded desk lamp, a rotary telephone and two cups. Two "
     "investigators work standing: one flips through a folder page by page, the other sorts "
     "papers into three stacks and marks one with a pencil. A third crosses behind with a mug. "
     "Camera: slow orbit around the desk that settles looking down at the map, the lamp light "
     "raking the paper texture. Real motion: turning pages, pencil, steam, shifting weight. "
     "No readable text, no suspect names, no conclusions."),

    ("S15", 93, 7, "从桌面平滑推进至电脑屏幕", [], "real",
     "The same house at night, a small ground-floor study: a beige 2000-era desktop tower and a "
     "deep CRT monitor stand on a wooden desk, with a chunky keyboard, a beige mouse on a cloth "
     "pad, a rotary telephone, a stack of blank CD cases and a closed notebook. The screen glows "
     "cold blue, its interface deliberately blurred and illegible; the light spills across the "
     "keys and the desk edge. A curtain stirs; the monitor's flicker changes the shadows very "
     "slightly. Camera: slow push from the desk edge to the screen, one continuous move. Real "
     "motion: screen breathing, dust in the beam, curtain. No readable text, no chat windows, "
     "no search terms, no personal data."),

    ("S16", 100, 7, "低机位横移，依次经过电话、键盘和文件", [], "real",
     "Same study, detail sequence in one continuous low lateral move: past the rotary telephone "
     "with its coiled cord, past the keyboard and a small pad of paper with abstract unreadable "
     "marks, past a plain first-aid tin standing open with a strip of plasters pulled loose, and "
     "past a kitchen counter where four empty ice-cream cups stand in a row, spoons untouched in "
     "the drawer. Beyond the window the winter Tokyo sky is flat blue-grey. Camera: low, slow "
     "lateral glide with shallow focus pulling between objects. Real motion: cord sway, paper "
     "edge lifting in a draught, faint steam, dust. No bodies, no blood, no readable text."),

    ("S17", 107, 7, "远距离侧向跟拍", ["silhouette"], "real",
     "A narrow Tokyo street at night, seen from far away across the road: a lone adult male "
     "figure in a dark winter coat and scarf walks slowly along the pavement, hands in pockets, "
     "shoulders hunched, face completely unreadable in silhouette. A passing car's headlights "
     "sweep across him and for a moment his outline sharpens against the fence and the bare "
     "trees, then he sinks back into shadow and continues away from the camera. Camera: distant "
     "lateral tracking shot, the figure small in the frame, foreground branch passing close to "
     "the lens. This is a conceptual image of an unidentified person, not surveillance footage. "
     "Real motion: walking, coat and scarf moving, headlight sweep. No face, no readable text."),

    ("S18", 114, 7, "从档案柜向调查桌推进", ["detective"], "real",
     "The investigation office, years later but the same room: tall rows of grey filing cabinets "
     "line the left wall, drawers open at different heights, cardboard archive boxes stacked on "
     "the floor; a long table holds neat paper piles, a map, a desk lamp and an old desktop "
     "computer. Two investigators work - one pulls a thick folder from a drawer and sets it on "
     "the growing stack, one sits comparing two documents side by side, a third enters with a "
     "box and sets it down. Camera: push forward from the cabinets to the table, one continuous "
     "move. Real motion: drawer sliding, pages turning, box settling, breathing. No readable "
     "text, no names, no invented counts."),

    ("S19", 121, 7, "沿关系图平滑移动，最后拉远", [], "diagram",
     "Abstract 3D investigation graph in a dark space: at the centre a simple wireframe outline "
     "of a two-storey house; around it float small matte objects - a folded garment, a square "
     "cloth, a fingerprint whorl, a shoe sole, a clock face with no numbers. Thin filaments draw "
     "themselves slowly between some objects while others remain unconnected; a few nodes pulse "
     "with faint gold light and then dim. Camera: glide along one filament, past the "
     "garment node, and pulls back so the gaps in the network become the subject. Conceptual "
     "diagram only, no identity, no resolution. Real motion: filament growth, drifting "
     "particles, slow rotation. No readable text, no readable letters, no numbers, no names, "
     "no match results."),

    ("S20", 128, 7, "固定机位季节流转，缓慢推近", [], "real",
     "The same Setagaya lane and the same cream house, one locked-off wide view through a full "
     "year of seasons: bare winter branches, then pale spring blossom drifting, dense green "
     "summer shade with a bicycle passing, red autumn leaves scattering across the asphalt, "
     "then first snow settling on the roof and fence again. Light shifts from cold blue-grey to "
     "warm afternoon and back; a low lamp comes on in the upstairs window each evening like a "
     "breath. Camera: locked wide shot with a very slow continuous push toward the house. Real "
     "motion: leaves, blossom, snow, swaying trees, passing bicycle, changing light. No people "
     "in close view, no readable text."),

    ("S21", 135, 7, "桌面横移后缓慢拉远", ["police", "detective"], "real",
     "The investigation office: a table holding a colour reference sheet of the grey-and-purple "
     "sweatshirt outline, a printed map with abstract unreadable markings, and several clear "
     "evidence bags; two people work - a police officer in shirt sleeves slides a folder into a "
     "filing cabinet drawer and pushes it closed, an investigator leans over the reference sheet "
     "with a magnifier and turns it slightly. A desk lamp glows; the room is quiet. Camera: "
     "lateral move across the table, then a slow pull back so both figures and the cabinets "
     "share the frame. Real motion: drawer, magnifier, page turning, breathing. No readable "
     "text, no phone numbers, no reward figures on screen."),

    ("S22", 142, 7, "缓慢穿过抽象问号，逐渐拉远", [], "diagram",
     "Abstract dark space: four large brushed-metal question marks hang at different depths, "
     "each faintly lit and slowly rotating, standing for identity, motive, route and evidence. "
     "Beams of low haze pass between them; beneath them the blurred outlines of paper folders "
     "and a folded garment float like unread documents. One by one the question marks dim and "
     "fade, leaving only the empty haze. Camera: glides forward between the marks, then pulls "
     "back and up until they are small points of light. Conceptual only; no suspect, no names, "
     "no conspiracy imagery. Real motion: rotation, haze, dimming glow. No readable text, "
     "no readable letters, no numbers."),

    ("S23", 149, 7, "缓慢推进后升高拉远", [], "real",
     "Winter night on the same street, years later: the lane is empty, frost glittering on the "
     "kerb, the cream house lit only by a street lamp, its windows dark, bare branches casting "
     "long thin shadows that move as the wind shifts. Camera: a slow push toward the gate, "
     "then rises and pulls back so the house shrinks into the surrounding grid of streets, "
     "rooftops and dark trees, the city ambient hum implied by distant glows. Real motion: "
     "branch shadows, drifting mist, a single car passing far away. No people, no police lights, "
     "no readable text."),

    ("S24", 156, 4, "缓慢横移，依次照亮物证", [], "real",
     "Studio evidence display in darkness: on a long matte table the grey raglan sweatshirt with "
     "faded purple sleeves lies folded, a black handkerchief beside it, and three small abstract "
     "evidence icons glow at the far end. A soft white light travels from left to right, "
     "revealing each object in turn and sliding off into shadow; fibres catch the light and "
     "glisten. Camera: slow lateral move with shallow focus. Illustrative reconstruction only, "
     "no claim about any individual. Real motion: travelling light, settling cloth, dust. "
     "No readable text, no blood."),

    ("S25", 160, 4, "沿关系图移动，停留在空白节点", [], "diagram",
     "The abstract investigation graph returns in darkness: the wireframe house at the centre, "
     "evidence nodes around it, a few filaments brightening with pale gold light while one node "
     "at the edge stays dark and empty. Camera: drift from the house outline along a lit "
     "filament toward that empty node and stops there, the void filling the right third. Real "
     "motion: filaments pulsing, particles drifting, slow parallax. Conceptual diagram only. "
     "No readable text, no readable letters, no numbers, no identity, no outcome."),

    ("S26", 164, 4, "升高、拉远、淡出", [], "real",
     "The neighbourhood at deep night from a high angle: the same house small in the middle "
     "third, cold blue rooftops and bare trees stretching away, one street lamp flickering "
     "gently in the wind as mist crosses the beam. Camera: rise and pull back steadily "
     "until the streets become a dark grid, then the image begins to sink toward black at the "
     "edges. Real motion: flickering lamp, drifting mist, swaying branches. No people, no "
     "supernatural effect, no readable text."),

    ("S27", 168, 4, "缓慢旋转后稳定", [], "real",
     "Pure black background: a single large gold question mark made of softly brushed metal "
     "rotates slowly in the centre, catching a narrow travelling highlight along its curve; fine "
     "dust drifts through the darkness and a faint outline of a house breathes behind it before "
     "sinking away. Camera: very slow orbit that settles as the mark faces the lens. The clip "
     "itself contains no lettering other than the mark's shape. Elegant, restrained, cinematic. "
     "No other text, no watermark, no supernatural glow."),

    ("S28", 172, 4, "极缓慢推进", [], "real",
     "Deep blue-grey cinematic background with soft volumetric haze: the dark three-dimensional "
     "silhouette of a small two-storey Japanese house slowly emerges at the right third, its "
     "windows unlit, snow settling on the roof edge. A thin line of gold light grows horizontally "
     "across the empty left half, gradually brightening the haze without forming any letters. "
     "Camera: extremely slow push forward. Real motion: drifting snow, growing light, mist. "
     "The frame is deliberately kept clear for a title added later; no text is generated."),

    ("S29", 176, 4, "缓慢推进，最后定格", [], "real",
     "Nearly black cinematic background for an end card: at the centre-left the folded outline of "
     "a grey raglan sweatshirt rests in shallow light, at the right a small dark house silhouette "
     "stands in faint blue haze, and between them a gold question mark turns slowly, its polished "
     "surface throwing one thin highlight. Snow dust drifts; the light breathes. Camera: very "
     "slow push in, settling to a stable final frame with clean negative space in the upper half. "
     "Real motion: drifting snow dust, breathing light, the gold mark turning slowly. "
     "The generated clip contains no lettering at all; every title is added in post. No "
     "watermark, no readable text."),
]

# ---------------------------------------------------------------- 一镜一句旁白（29 条）
# 每条都写进分镜：旁白 = 字幕，起止与镜头一致；只允许加速，不允许慢放。
NARRATION = {
    "S01": "2000年年底，东京世田谷，一家四口在家中被杀。",
    "S02": "现场留下了大量线索，可这起案件，至今没有侦破。",
    "S03": "父亲宫泽干男44岁，在外资企业做CI开发；学生时代演过话剧，喜欢动画。",
    "S04": "母亲泰子41岁，在家开补习班；女儿妮娜八岁，学芭蕾和钢琴；儿子礼六岁。",
    "S05": "12月30日傍晚，一家人在千岁乌山买完东西，回家吃饭、看电视。",
    "S06": "那天深夜十一点多，邻居听见一声闷响；之后，那栋房子安静得出奇。",
    "S07": "凶手是从二楼浴室的窗户进去的，离开时，走的是玄关。",
    "S08": "31日上午，住在隔壁的母亲过来查看，才发现出了事；警方随即赶到。",
    "S09": "警方把这里定为重大案件现场，拉起警戒线，开始一寸一寸地勘查。",
    "S10": "调查人员戴着手套，逐件记录物品的位置：拍照、装袋、编号、封存。",
    "S11": "一件浅灰身、浅紫袖的拉格伦运动衫，被凶手脱下来，留在现场。",
    "S12": "还有两块黑色手帕：其中一块，中间割开三厘米，用来裹住刀柄。",
    "S13": "刀柄、血迹、指纹，还有吃剩的冰淇淋，证据一件件被送进实验室。",
    "S14": "可证据本身不等于答案；每一件东西，都要和别的线索互相印证。",
    "S15": "调查人员发现，案发之后，有人用过这台电脑：上网、建文件夹。",
    "S16": "冰箱里的四个冰淇淋被吃掉，厕所被使用过，急救箱也被翻动。",
    "S17": "现场留下了他的血、他的鞋印，甚至他的指纹，可这个人始终没有名字。",
    "S18": "二十多年里，警方投入近三十万人次，一遍遍重查物证、翻旧档案。",
    "S19": "找到一件衣服，和证明它是谁的，是两件完全不同的事。",
    "S20": "时间一年年过去，房子还在，街边的树绿了又黄，答案却一直没有来。",
    "S21": "警方从未放弃，一遍遍公开物证，悬赏最高两千万日元，征集线索。",
    "S22": "关于凶手是谁、为什么动手，外面猜测很多，可猜测不能当证据。",
    "S23": "那座房子里，那一夜发生的全部真相，至今没有被揭开。",
    "S24": "运动衫、手帕，还有那些没解开的线索。",
    "S25": "到底哪一条线索，才能真的接近答案？",
    "S26": "真相，仍然在黑暗里，等着被揭开。",
    "S27": "你怎么看？",
    "S28": "欢迎在评论区，理性讨论。",
    "S29": "真实案件改编，部分画面为3D复原。",
}

# ---------------------------------------------------------------- 九段（由镜头推导，只用于章节统计）
CHAPTER_TITLES = [
    ("N01", "黄金三秒钩子"),
    ("N02", "一家四口"),
    ("N03", "那一夜"),
    ("N04", "现场与封锁"),
    ("N05", "更多遗留物"),
    ("N06", "现场留下的行为痕迹"),
    ("N07", "为什么长期未破"),
    ("N08", "仍未揭开的谜团"),
    ("N09", "物证回顾与互动"),
]

SOURCES = [
    {
        "id": "keishicho-poster",
        "title": "警视庁「世田谷一家４人強盗殺人事件」公開資料（PDF）",
        "url": "https://www.keishicho.metro.tokyo.lg.jp/jiken_jiko/ichiran/ichiran_11-20/seijo.files/Ja_2601.pdf",
        "supports": "事件发生于平成12年12月30日深夜、上祖师谷三丁目23番26号；四名遇害者姓名与年龄"
                    "（宫泽干男44岁、泰子41岁、长女妮娜8岁、长子礼6岁）；父亲在外资企业负责CI开发、"
                    "爱好动画、学生时代演人偶剧；母亲在家经营补习班；30日傍晚一家在千岁乌山站附近"
                    "商店街购物后回家；凶手像（较年轻、170cm前后、L码、27.5cm/韩国280鞋码、A型、"
                    "瘦、可能右手持刀）；遗留衣物与物品清单（拉格伦运动衫浅灰身浅紫袖L码130件、"
                    "黑色无印良品手帕2块、黑色腰包、优衣库黑色夹克、绿色格纹围巾、黑色褶皱帽、"
                    "Edwin手套、Slazenger韩国制运动鞋、「関孫六 銀寿」柳刃包丁刃体21cm全长34cm、"
                    "Drakkar Noir香水）；悬赏金公的300万、私的1700万、合计上限2000万日元；"
                    "特搜本部联系方式；现场在都立祖师谷公园一角、案发时周边仅剩4户。",
    },
    {
        "id": "keishicho-page",
        "title": "警视庁「上祖師谷三丁目一家4人強盗殺人事件」事件ページ",
        "url": "https://www.keishicho.metro.tokyo.lg.jp/jiken_jiko/ichiran/ichiran_11-20/seijo.html",
        "supports": "遗留运动衫的公开说明：身干部分浅灰、两袖浅紫的拉格伦袖L码；全国仅130件、"
                    "都内仅10件（八王子、圣迹樱丘、荻窪、青户），其中1件购买者已查明。",
    },
    {
        "id": "nikkei-2011",
        "title": "日本经济新闻（2011-12-19）「遺留品のトレーナー、4割が静岡で販売」",
        "url": "https://www.nikkei.com/article/DGXNASDG1903J_Z11C11A2CC1000/",
        "supports": "拉格伦运动衫为袖与领口紫色、身干浅灰的L码；14都道府县41家店铺共售130件，"
                    "其中静冈52件；销售商2009年10月解散，仅12件购买者查明。",
    },
    {
        "id": "mainichi-2022",
        "title": "每日新闻「事件がわかる：世田谷一家殺害事件」（2022-04-18）",
        "url": "https://mainichi.jp/articles/20220418/osg/00m/040/001000d",
        "supports": "电脑在31日凌晨1时18分与上午10时各有操作痕迹；凶手吃掉冰箱中4个杯装冰淇淋且"
                    "不用勺子、使用厕所；DNA型与约130万件比对仍无一致；悬赏金合计上限2000万日元；"
                    "情报提供至成城署特搜本部。",
    },
    {
        "id": "yomiuri-2025",
        "title": "读卖新闻（2025-12-31）「世田谷一家殺害から四半世紀」",
        "url": "https://www.yomiuri.co.jp/national/20251231-GYT1T00014/",
        "supports": "案件在四分之一世纪后仍未解决，四名遇害者与年龄；科学侦查持续进行。",
    },
    {
        "id": "jprime-2020",
        "title": "週刊女性PRIME（2020-12-30）世田谷一家殺害事件・元成城署署长访谈",
        "url": "https://www.jprime.jp/articles/-/19751?page=3",
        "supports": "累计投入搜查员28万人次；凶手像为A型、身高170cm前后的较年轻男性；"
                    "遗留衣物与柳刃包丁等物证数量异常之多；都内仅10件运动衫中1件购买者已查明。",
    },
    {
        "id": "huffpost-2015",
        "title": "HuffPost Japan（2015-03-22）「世田谷一家殺害事件とは 現場に残された膨大な遺留品」",
        "url": "https://www.huffingtonpost.jp/2015/03/22/setagaya-murder_n_6918156.html",
        "supports": "案发时间为30日23时前后至31日凌晨；31日上午发现四名遇害者；"
                    "现场遗留指纹、血迹、运动衫、夹克、手套、帽子等，以及日本未销售的鞋码足迹与腰包。",
    },
]

PRINCIPLES = [
    "全片29个镜头全部由 Agnes Video 2.5 Flash 生成连续运动片段（720P 源片，后期放大到 "
    "1920×1080 · 24fps），禁止静态图加推拉代替；每个镜头只出现一次。",
    "每条提示词自动以【STYLE】开头、以【NEGATIVE】结尾；出现人物时自动拼接对应【角色设定】；"
    "2.5 Flash 不接受独立 negative_prompt 字段，红线因此写在提示词正文里。",
    "不出现遗体、伤口、血腥或作案过程；现场镜头全部停在警戒线外，室内勘查只拍物证与动作。",
    "凶手只以远景剪影出现（S17），不给正脸、不指认任何真实人物；家属（S08）以背影与手部动作表现。",
    "四名家庭成员全部使用风格化形象，不复制真实肖像；姓名、年龄与公开资料一致。",
    "所有物证画面（S11、S12、S24）都是 3D 示意性复原，画面风格明确为展示台复原，"
    "不冒充警方原始证物照片；片中文字全部由后期叠加。",
    "抽象示意图（S13、S19、S22、S25）使用独立 STYLE 变体，与写实复原镜头明确区分，"
    "不呈现任何比对结果或嫌疑人身份。",
    "旁白一镜一句：每镜一条独立配音与一条同起止字幕；保留自然语速，必要时最多加速 1.55 倍，禁止慢放填满时长。",
    "『灰色拼接运动衫』『黑色手帕』『电脑使用痕迹』是全片三个反复出现的视觉母题，"
    "在钩子、物证、调查与结尾互相呼应。",
]

PRESENTATION = {
    "cover": {
        "layout": "16:9；左侧灰色拼接运动衫的3D复原特写，右侧冬夜日本住宅剪影与微弱暖黄窗光，"
                  "中央一枚金色问号；主标题在左侧，副标题在下方",
        "text": "世田谷一家四口",
        "subtext": "留下无数线索，凶手为何仍未找到？",
        "style": "金色粗体字、黑色描边；由 S11 运动衫与 S01 冬夜住宅两帧合成，问号为后期绘制，"
                 "不是静态图替代视频",
    },
    "end_title": "世田谷一家四口杀人案",
    "end_subtitle": "日本 · 2000 · 至今未破",
    "end_note": "真实案件改编 · 部分画面为3D复原",
    # 片尾卡上的一句引导提问：只问，不给任何暗示，也不指认任何人。
    "end_question": "你觉得凶手是熟人，还是陌生人？",
    "highlight_keywords": [
        "2000年", "世田谷", "一家四口", "线索", "没有侦破", "宫泽干男", "44岁", "外资企业",
        "动画", "泰子", "41岁", "补习班", "八岁", "六岁", "12月30日", "千岁乌山", "深夜十一点",
        "闷响", "二楼浴室", "玄关", "31日", "警方", "警戒线", "勘查", "运动衫", "浅灰", "浅紫",
        "黑色手帕", "三厘米", "刀柄", "指纹", "血迹", "冰淇淋", "实验室", "证据", "彼此印证",
        "电脑", "厕所", "急救箱", "鞋印", "没有名字", "二十多年", "档案", "两千万日元", "猜测",
        "不是证据", "真相", "3D复原",
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
        {"at": 0, "name": "低沉大提琴单音渐强、冬夜风声、远处车辆", "kind": "music_sfx"},
        {"at": 10, "name": "温暖钢琴与餐具轻响、电视环境音，随后逐渐转冷", "kind": "music_sfx"},
        {"at": 31, "name": "空荡街道的风、远处车声、低频弦乐渐入", "kind": "music_sfx"},
        {"at": 51, "name": "警戒线抖动、相机快门、脚步声、无线电环境音", "kind": "sfx"},
        {"at": 65, "name": "布料摩擦、低沉金属音；物证台细节声", "kind": "sfx"},
        {"at": 79, "name": "实验室电子提示音、低音脉冲、纸张翻动", "kind": "music_sfx"},
        {"at": 93, "name": "电脑风扇声、键盘声、低沉弦乐", "kind": "music_sfx"},
        {"at": 114, "name": "档案柜滑轨、翻页、钢笔书写、办公室环境音", "kind": "music_sfx"},
        {"at": 135, "name": "悬疑钢琴与大提琴交替、台灯轻响", "kind": "music_sfx"},
        {"at": 156, "name": "低沉钢琴渐强、金属提示音、冬夜风声", "kind": "music_sfx"},
        {"at": 176, "name": "大提琴单音收尾，最后0.8秒淡出至静音", "kind": "music_sfx"},
    ],
    "douyin_title": "一家四口在自家遇害，凶手在现场吃了四个冰淇淋，还上了半小时网",
    "hashtags": ["#世田谷一家四口", "#未解悬案", "#真实案件", "#3D动画", "#悬疑", "#东京"],
    "release_intro": (
        "2000年12月30日深夜，东京世田谷区上祖师谷，一家四口在自家遇害。\n\n"
        "凶手在现场留下了几乎可以开一场展览的东西：一件浅灰身浅紫袖的拉格伦运动衫，"
        "两块黑色手帕，一顶帽子，一副手套，一条围巾，一只腰包，一双日本没有卖过的鞋，"
        "一把卷着布条的柳刃包丁，还有他自己的血、指纹和鞋印。\n\n"
        "他还在那栋房子里待了几个小时：用被害人的电脑上网，吃掉冰箱里四个冰淇淋，"
        "用厕所，翻急救箱，然后从玄关走出去，把门锁上。\n\n"
        "二十多年过去，警方把 DNA 比对过上百万份，物证公开了一遍又一遍，凶手仍然没有名字。\n\n"
        "画面为AI生成的情景重现，物证为3D示意性复原，不是警方原始影像。"
        "关于凶手身份与动机的一切说法，目前都只是猜测。"
    ),
}

REFERENCE_IMAGES = [
    {"file": "reference/01-miyazawa-family.png",
     "description": "一家四口定稿：宫泽干男（深色针织衫）、泰子（米色开衫）、妮娜（8岁，齐肩短发）、"
                    "礼（6岁，居家服），风格化形象，非真实肖像"},
    {"file": "reference/02-setagaya-house.png",
     "description": "宫泽家住宅定稿：浅色外墙二层独栋、深色木门廊、围栏、窄路、电线杆、冬季枯树"},
    {"file": "reference/03-setagaya-street-night.png",
     "description": "世田谷冬夜街道定稿：冷蓝灰路灯、暖黄窗光、湿沥青反光、远处车灯"},
    {"file": "reference/04-sweatshirt-evidence.png",
     "description": "核心物证定稿：浅灰身、浅紫袖的拉格伦运动衫（3D示意复原，非警方照片）"},
    {"file": "reference/05-black-handkerchief-knife.png",
     "description": "核心物证定稿：两块黑色手帕与裹着布条的柳刃包丁（无刃口、无血迹）"},
    {"file": "reference/06-2000-study-computer.png",
     "description": "2000年书房定稿：米色台式机、CRT显示器、键盘、转盘电话、证物袋"},
    {"file": "reference/07-police-investigation.png",
     "description": "警方现场与调查办公室定稿：2000年 Japan 警服、警戒线、纸质档案、台灯、地图"},
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
        seed = CHARACTER_SEEDS[characters[0]] if len(characters) == 1 else 20001201 + index
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
            "transition_out": "同段内硬切或轻叠化；现实场景与抽象示意图之间用0.3秒冷色柔化转场；"
                              "不改动旁白时间轴。",
        })

    chapter_bounds = [
        ("N01", 0, 10), ("N02", 10, 31), ("N03", 31, 51), ("N04", 51, 72), ("N05", 72, 93),
        ("N06", 93, 114), ("N07", 114, 135), ("N08", 135, 156), ("N09", 156, 180),
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
            "dramatic_pause_after": {"S23": 0.4},
        },
        "sources": SOURCES,
        "presentation": PRESENTATION,
        "reference_images": REFERENCE_IMAGES,
        "fact_boundary": [
            "事件发生于2000年12月30日深夜至31日凌晨，地点是东京都世田谷区上祖师谷三丁目；"
            "30日傍晚一家四口在千岁乌山站附近商店街购物后回家。",
            "四名遇害者为宫泽干男（44岁，外资企业CI开发）、妻泰子（41岁，在家经营补习班）、"
            "长女妮娜（8岁，小学二年级，学芭蕾与钢琴）、长子礼（6岁，保育园年长班）。",
            "31日上午由住在旁边的泰子的母亲发现异常并报警，警方随即设立特别搜查本部。",
            "凶手被判断为从二楼（中层）浴室窗户侵入、从玄关离开；现场留有大量遗留物，"
            "包括浅灰身浅紫袖的拉格伦运动衫、两块无印良品黑色手帕、黑色腰包、夹克、围巾、"
            "帽子、手套、韩国制运动鞋足迹与柳刃包丁。",
            "调查显示案发后有人使用过被害人家的电脑（媒体报道31日凌晨1时18分等时间点）、"
            "吃掉冰箱中的四个杯装冰淇淋、使用厕所；这些是公开报道过的行为痕迹。",
            "警方公开的凶手像：可能较年轻、身高约170厘米、A型血、体形偏瘦、L码衣物、"
            "鞋码27.5厘米（韩国280）、可能右手持械；DNA比对累计上百万件仍无一致。",
            "案件至今未侦破，日本在2010年修法后此类案件不再有公诉时效；悬赏金公的300万、"
            "私的1700万，合计上限2000万日元。",
            "片中关于凶手身份、动机、行动路线的任何叙述都未写入事实；S17 的剪影只是"
            "『身份未确认』的概念化表达，不代表警方已确认嫌疑人外貌。",
            "所有画面为AI动画情景重现，物证画面为3D示意性复原，不冒充警方原始证据影像；"
            "不出现遗体、伤口、血腥或作案过程。",
        ],
    }


def write_screenplay(story: dict) -> None:
    lines = [
        f"# {story['title']}",
        "",
        f"三分钟横屏悬疑动画短片 · 1920×1080 · {story['fps']}fps · 180秒 · "
        "29 个 Agnes Video 2.5 Flash 动态镜头 · 一镜一句中文旁白",
        "",
        "> 画面为 AI 动画情景重现，不是历史影像；物证画面为 3D 示意性复原，不是警方原始照片。",
        "> 不出现遗体、伤口、血腥或作案过程；凶手只以远景剪影出现。",
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
        "- 生成：Agnes Video 2.5 Flash，720P 源片，62 秒共享节流，断点续跑；后期放大到 1920×1080。",
        "- 配音：低沉悬疑男声（voice-01）；一镜一句、字幕同起止；只加速（≤1.55×），不慢放。",
        "- 字幕：白色黑边、底部安全区、关键词金色放大；日期与案件信息与官方资料一致。",
        "- 音乐：原创程序合成（大提琴、低音弦乐、钢琴、低频脉冲、金属提示音）；旁白下压约 −18dB。",
        "- 音效：冬夜风、远处车声、警戒线、相机快门、布料摩擦、键盘与电脑风扇、翻页与钢笔。",
        "- 片尾：S29 物证与住宅剪影，后期叠加金色片名『世田谷一家四口杀人案』与副题"
        "『日本 · 2000 · 至今未破』，最后 0.8 秒淡出至静音。",
        "- 封面：左侧 S11 运动衫、右侧 S01 冬夜住宅、中央金色问号；主标题『世田谷一家四口』。",
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
        "**核心钩子：** 凶手在现场吃了四个冰淇淋、上了半小时网，还留下一件只卖出130件的运动衫\n\n"
        "## 四列分镜表\n\n"
        "| 镜号 | 时间 | 口播（=字幕） | 画面 | 运镜 |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## 声音设计\n\n| 时间 | 声音 |\n|---|---|\n" + events
        + "\n\n## 事实边界\n\n"
        "- 时间、地点、四名遇害者的姓名年龄、遗留物特征、凶手像与悬赏金额均以警视厅公开资料为准。\n"
        "- 电脑使用、冰淇淋、厕所等行为痕迹来自公开报道，片中只作行为描述，不作动机推断。\n"
        "- 凶手身份、动机、行动路线一律不写入事实；S17 剪影只是概念化表达。\n"
        "- 不出现遗体、伤口、血腥或作案过程；画面为AI动画情景重现，物证为3D示意性复原。\n\n"
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

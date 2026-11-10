#!/usr/bin/env python3
"""唯一内容源：《汽车旅馆连环命案：金素英为什么带他们去旅馆？》

运行 ``python3 production/motel2026/build_story.py`` 会写出 story.json、screenplay.md、
audio/manifest.json、抖音脚本.md 与抖音发布文案.md。30 个镜头全部是 Agnes Video 2.5 Flash
（720P 源片，后期放大到 1920×1080 · 24fps）生成的连续运动片段；旁白一镜一句，字幕与配音同起止。

事实口径（已按公开检方、法院与主流媒体资料核验至 2026-11-10）：被告金素英的姓名、年龄与照片已由
首尔北部地方检察厅依法公开；一审已判、控辩双方均已上诉。片中对侦查、检方与一审法院的判断均保留
“警方认为”“检方认为”“一审法院认为”的归属，不把被告辩解或网络猜测剪成事实。片中不出现药物名称、
药片、剂量、调配细节，不出现遗体、血腥；受害者只以背影、剪影与白菊花出现；手机界面一律抽象线条，
不出现可读文字。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
TITLE = "汽车旅馆连环命案：金素英为什么带他们去旅馆？"
# 修订版绝不覆盖已交付的旧叙事成片和其配套文件。
FILM_NAME = "汽车旅馆连环命案_人物关系与动机修订版_三分钟_带声音.mp4"
DELIVERY_BASENAME = "Motel_Case_Revised_V2"
BRANCH = "arena/4d042fa6-desktop-tutorial"
FPS = 24
REVISION_FILE = HERE / "revised-narration-v2.json"

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
     "Strict framing priority: a photorealistic Korean crime-thriller 3D reenactment with "
     "physically based wet concrete, glass and fabric, never cartoon or illustrated. After "
     "rain at night, a long-lens camera pushes in from across a mostly empty wet service lane "
     "toward an unmarked recessed motel side entrance: only a plain blank facade, a frosted "
     "glass doorway and a fabric curtain are visible. The frame deliberately crops out the "
     "roofline, fascia, commercial street, storefronts, every signboard, billboard and "
     "illuminated panel. Purple-red colour appears solely as a soft reflected ambient glow on "
     "wet asphalt from unseen diffuse light, never as a neon sign. Camera: one continuous "
     "long-lens push-in, slow and steady. Real motion: curtain swaying, water dripping, "
     "reflections rippling and distant defocused headlights sliding past. No people. "
     "Absolutely no writing in any language: no letters, numbers, logos, Korean Hangul, "
     "glyph-like shapes, subtitles or captions anywhere in the generated frame."),

    ("S02", 5, 5, "大特写，缓慢推近", ["kim"], "real",
     "Extreme close-up of a smartphone screen in a dark room: an abstract chat interface "
     "made of soft lines and bubbles with no readable words, a single red exclamation "
     "warning icon lights up, then a young woman's fingertip swipes it away; cold blue "
     "screen light falls on half of her calm face, her eyes show no reaction. Camera: "
     "extreme close-up with a slow push-in. Real motion: icon pulsing, fingertip sliding, "
     "blinking, breathing. No readable text, no letters, no numbers."),

    ("S03", 10, 7, "中景，缓慢推近", ["kim", "boyfriend"], "real",
     "Strict visual priority: a photorealistic Korean crime-thriller 3D reenactment with "
     "normal-proportioned adult people and physically based winter pavement, fabric and glass, "
     "never cartoon or illustrated. 14 December 2025, outside an unmarked cafe in Namyangju at "
     "night: a young adult couple walks slowly through a quiet wet parking area toward a compact "
     "car, both seen in three-quarter back view. The woman offers an ordinary sealed takeaway cup; "
     "the man accepts it casually. Keep the cafe facade blurred and completely unmarked, with no "
     "legible signage. Camera: medium shot with a slow push toward the passing hands. Real motion: "
     "walking, breath vapour, wet reflections trembling, cup changing hands, coat fabric moving. "
     "No medicine, no danger depiction, no readable text, no letters, no numbers."),

    ("S04", 17, 7, "低机位，缓慢推近", ["kim"], "real",
     "Strict visual priority: photorealistic Korean crime-thriller 3D reenactment with "
     "physically based wet asphalt, glass and fabric, never cartoon, toy-like or illustrated. "
     "The same unmarked Namyangju cafe parking area later that winter night: frame a plain service "
     "alcove looking only toward blank frosted glass and rain-dark pavement, never toward a lobby, "
     "street, storefront, window display, exit sign, neon sign or illuminated panel. Cold blue-white "
     "ambulance reflections sweep across the pavement while one unmistakably empty wheelchair crosses "
     "behind the frosted glass. Kim appears only small and distant at the far edge in three-quarter "
     "back view, phone lowered, with no other interior silhouettes. No person is shown injured, "
     "unconscious, restrained or on a bed. Camera: low angle with a slow push-in. Real motion: "
     "reflections sweeping, raindrops falling, wheelchair wheels passing, Kim shifting weight, breath "
     "vapour drifting. Absolutely no readable writing: no letters, numbers, logos, Korean Hangul, "
     "glyph-like illuminated shapes, signage or captions."),

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
     "Strict framing priority: photorealistic Korean crime-thriller 3D reenactment with "
     "normal-proportioned adult people, realistic rain, fabric, concrete and skin, never "
     "cartoon, toy-like or illustrated. 28 January 2026, 9:30 pm: inside an enclosed, "
     "completely unmarked motel vestibule, a plain fabric curtain parts and a man and woman "
     "walk in side by side. The man is seen only from behind and in three-quarter back view; "
     "the woman keeps her head lowered. Warm light spills from an unlabelled front desk behind "
     "frosted glass; an unmarked blank key card is handed out. The camera remains inside the "
     "vestibule and deliberately excludes the outer street, upper facade, storefronts, every "
     "signboard, billboard and illuminated panel. Purple-red colour is only a diffuse "
     "reflection on blank walls and wet floor, never a neon sign. Camera: medium shot with a "
     "slow push-in. Real motion: curtain parting, adult walking, head turning, card passing "
     "hands and fabric moving. No clear faces. Absolutely no writing in any language: no "
     "letters, numbers, logos, Korean Hangul, glyph-like shapes, subtitles or captions."),

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
     "Strict visual priority: a photorealistic Korean crime-thriller 3D reenactment with "
     "physically based real-world materials, normal-proportioned adult anatomy and a serious "
     "live-action-film look, never cartoon, toy-like or illustrated. Deep night at an "
     "unmarked motel side exit: this is a narrow wet service passage, not a commercial street. "
     "The camera deliberately crops out every upper facade, shopfront, signboard and illuminated "
     "panel. A fabric curtain lifts; Kim is seen only from behind as she walks out, pulls up "
     "her hood, crosses the wet concrete passage at an unhurried pace and disappears into "
     "shadow. Purple-red colour appears only as diffuse reflected ambient light from an unseen "
     "source, never as a neon sign. Camera: low tracking shot from behind. Real motion: curtain "
     "lifting, walking, hood settling, puddle ripples and coloured reflections shimmering. "
     "Absolutely no writing in any language: no letters, numbers, logos, Korean Hangul, "
     "glyph-like shapes, subtitles or captions anywhere in frame."),

    ("S11", 60, 7, "中景，手持", ["kim", "victimB"], "real",
     "Strict visual priority: photorealistic Korean crime-thriller 3D reenactment with natural adult "
     "proportions, rain-wet concrete and fabric, never cartoon or illustrated. 9 February at night: "
     "inside a different completely unmarked inner motel vestibule in Gangbuk-gu, Kim and another young "
     "adult man walk through an opaque plain fabric divider side by side. The camera looks inward at a "
     "blank matte wall and unlabelled frosted desk, never toward an exterior entrance or street. He is "
     "seen only from behind and in three-quarter back view; no face is visible. A blank key card passes "
     "at the desk. Camera: handheld medium shot with a restrained slow approach. Real motion: divider "
     "parting, adults walking, card passing, fabric moving and soft indirect rain light shifting. No "
     "exterior view, red neon, exit sign, lightbox, signboard, storefront, poster, window advertisement "
     "or glowing glyph-like shape. Absolutely no readable writing: no letters, numbers, logos, Korean "
     "Hangul, captions or signage."),

    ("S12", 67, 7, "广角，缓慢推近", ["detective"], "real",
     "Strict visual priority: photorealistic Korean crime-thriller 3D reenactment with "
     "physically based concrete, wet fabric and realistic full-size adult people, never "
     "cartoon, chibi, toy-like or illustrated. At night, officers secure an unmarked recessed "
     "motel entrance with yellow cordon tape: the entrance is plain blank concrete and an "
     "opaque unlabelled door. The wide frame is intentionally held below the roofline and "
     "fascia, so it contains no building name, shopfront, window advertisement, vehicle or "
     "signboard. A few passers-by stop behind the tape while a detective in a dark jacket walks "
     "through the blank doorway; the scene remains restrained and procedural. Camera: wide shot "
     "with a slow push-in. Real motion: blue and red emergency light reflections sweep over "
     "bare walls, tape sags, adults walk and coats move. The coloured light is only reflection, "
     "not a sign. Absolutely no readable writing of any kind: no letters, numbers, logos, "
     "Korean Hangul, glyphs or insignia numbers."),

    ("S13", 74, 6, "中景，缓慢环绕", ["kim", "victimB"], "real",
     "Strict visual priority: photorealistic Korean crime-thriller 3D reenactment with serious "
     "live-action-film realism and normal full-size adults, never cute, doll-like, chibi or "
     "illustrated. At a small Seoul restaurant table isolated against a soft dark blank wall, Kim sits "
     "opposite a young man filmed only from behind. The defocused background contains only neutral wall "
     "and soft pendant light: no shopfront, poster, menu board, window, wall decal, red sign or hanging "
     "lettering. A server leaves a plain unmarked card tray near his side of the table; Kim watches "
     "quietly while he reaches toward it. The scene remains an ordinary short date, not a romance "
     "montage and not a transaction demonstration. Camera: medium shot with a slow restrained orbit. "
     "Real motion: hands settling, steam rising, chairs shifting, eyes blinking. Absolutely no readable "
     "writing: no letters, numbers, logos, Korean Hangul, glyph-like shapes, receipt details or harm."),

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

    ("S17", 97, 6, "近景，缓慢推近", ["kim", "detective"], "real",
     "A cold-grey police interview room under flat winter light: Kim sits at one side of a metal "
     "table, a detective sits opposite, both shown in restrained three-quarter profile rather than "
     "clear portrait. Kim makes a small defensive hand gesture and then folds her hands; the detective "
     "listens without reaction. A closed case folder lies face down, with no visible words. Camera: "
     "close shot with a slow push-in. Real motion: hands moving, blinking, breathing, the paper edge "
     "lifting in ventilation. No readable text, no violence, no glamour."),

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

    ("S23", 130, 7, "抽象关系图，缓慢推近", [], "diagram",
     "An abstract cinematic 3D relationship diagram on a deep charcoal background: two warm gold "
     "restaurant-table symbols and a small blank hotel-door icon drift in depth around a single cold "
     "blue human silhouette; a muted red thread draws between them and then tightens into a closed "
     "loop. All forms remain symbolic and unlabeled, with no readable letters, money amounts, names, "
     "words or numbers. Camera: slow push through layered depth. Real motion: icons drifting, red thread "
     "drawing itself, particles floating, light pulsing. Clearly conceptual, not a phone screen, not "
     "a real document and not a how-to diagram."),

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
def load_revised_narration() -> tuple[dict[str, str], str, dict[str, str]]:
    """Load approved V2 lines, narrator, and the per-shot visual-sync audit anchors."""
    payload = json.loads(REVISION_FILE.read_text(encoding="utf-8"))
    rows = payload.get("revisions", [])
    expected = [f"S{index:02d}" for index in range(1, 31)]
    ids = [row.get("id") for row in rows]
    if ids != expected:
        raise ValueError("revised-narration-v2.json must contain S01–S30 in order")
    if sum(int(row.get("duration", 0)) for row in rows) != 180:
        raise ValueError("revised narration must remain exactly 180 seconds")
    lines = {str(row["id"]): str(row["text"]).strip() for row in rows}
    anchors = {str(row["id"]): str(row.get("visual_anchor", "")).strip() for row in rows}
    if any(not value for value in lines.values()):
        raise ValueError("every revised narration shot needs text")
    if any(not value for value in anchors.values()):
        raise ValueError("every revised narration shot needs a visual-sync anchor")
    voice_id = str(payload.get("voice", "")).strip()
    if not voice_id.startswith("voice-"):
        raise ValueError("revised narration must name the user-selected Arena voice")
    return lines, voice_id, anchors


NARRATION, SELECTED_VOICE_ID, VISUAL_ANCHORS = load_revised_narration()

# ---------------------------------------------------------------- 九段（由镜头推导，只用于章节统计）
CHAPTER_TITLES = [
    ("N01", "姓名与关系"),
    ("N02", "前男友为何幸存"),
    ("N03", "第一名死者"),
    ("N04", "第二名死者"),
    ("N05", "关系与动机"),
    ("N06", "证据与法律认定"),
    ("N07", "一审动机"),
    ("N08", "判决与上诉"),
    ("N09", "完整案件"),
]

SOURCES = [
    {
        "id": "yna-timeline-2026-02-12",
        "title": "韩联社：早期受害者与前男友关系、南杨州事件及两起旅馆死亡时间线（2026-02-12）",
        "url": "https://www.yna.co.kr/view/AKR20260212061452004",
        "supports": "前男友在 2025 年 12 月南杨州事件后幸存、分手报案；1 月 28 日与 2 月 9 日两起旅馆死亡的基本时间线。",
    },
    {
        "id": "koreaherald-relationship-2026-02-13",
        "title": "Korea Herald：第一名死者为案发前不久认识的男子及早期辩解（2026-02-13）",
        "url": "https://www.koreaherald.com/article/10676420",
        "supports": "两名死者不是前男友；第一名死者为金素英在案发前不久认识的 20 多岁男性。",
    },
    {
        "id": "yna-motive-2026-03-04",
        "title": "韩联社：警方送检材料中的消费利用、冲突回避与风险判断（2026-03-04）",
        "url": "https://www.yna.co.kr/view/AKR20260304181600004",
        "supports": "警方对消费利用、约会支出、冲突回避及明知风险的调查结论。",
    },
    {
        "id": "yna-indictment-2026-03-10",
        "title": "韩联社：检方依法公开金素英姓名、年龄与照片并起诉（2026-03-10）",
        "url": "https://www.yna.co.kr/view/AKR20260310181751004",
        "supports": "姓名公开、检方对计划性和消费/经济动机的调查口径。",
    },
    {
        "id": "koreaherald-motel-2026-03-05",
        "title": "Korea Herald：旅馆由金素英提出、消费利用的警方调查报道（2026-03-05）",
        "url": "https://www.koreaherald.com/article/10687755",
        "supports": "旅馆并非偶遇地点，而是被调查认为由金素英主动推进的约会场所。",
    },
    {
        "id": "lawtimes-verdict-2026-08-27",
        "title": "法律新闻：一审无期徒刑、30 年电子定位监管与未必故意认定（2026-08-27）",
        "url": "https://www.lawtimes.co.kr/news/articleView.html?idxno=225477",
        "supports": "一审判决、电子定位监管和未必故意的法律结论。",
    },
    {
        "id": "seoul-appeal-2026-09-02",
        "title": "首尔新闻：金素英与检方均已上诉（2026-09-02）",
        "url": "https://www.seoul.co.kr/news/society/2026/09/02/20260902500158",
        "supports": "控辩双方均上诉，判决尚未生效。",
    },
]

PRINCIPLES = [
    "全片30个镜头全部由 Agnes Video 2.5 Flash 生成连续运动片段（720P 源片，后期放大到 "
    "1920×1080 · 24fps），禁止静态图加推拉代替；每个镜头只出现一次。",
    "每条提示词自动以【STYLE】开头、以【NEGATIVE】结尾；出现人物时自动拼接对应【角色设定】；"
    "2.5 Flash 不接受独立 negative_prompt 字段，红线因此写在提示词正文里。",
    "不出现药物名称、药片、剂量、调配过程；厨房镜头只允许玻璃杯与光影；不出现遗体、血腥；"
    "受害者只以背影、剪影与白菊花出现；金素英以克制的虚构形象呈现，不美化、不贴“蛇蝎美女”等标签。",
    "手机聊天界面一律用抽象线条与图标表示，不出现可读文字；片中文字全部由后期叠加。",
    "旁白一镜一句：每镜一条独立配音与一条同起止字幕；保留自然语速，必要时最多加速 1.55 倍，禁止慢放填满时长。",
    "视觉主线：手机屏幕上的红色警告图标贯穿全片（S02被划走 → S18反复出现 → S29再次亮起 → S30黑场亮起）；"
    "紫红色汽车旅馆霓虹为第二条色彩线索。",
]

PRESENTATION = {
    "cover": {
        "layout": "16:9；中央手机屏幕红色警告图标，四周紫红霓虹汽车旅馆夜景",
        "text": "她为什么带他们去旅馆？",
        "subtext": "金素英案 · 关系与动机",
        "hook_lines": ["金素英，20岁。一个幸存者，两名死者。", "两扇旅馆门，先后合上。"],
        "style": "金色粗体字、黑色描边；由 S02 手机帧与 S01 街景帧合成，红色警告图标为后期绘制，"
                 "不是静态图替代视频",
    },
    "end_title": "汽车旅馆连环命案",
    "end_subtitle": "首尔江北区 · 2025—2026 · 关系与动机补全",
    "end_note": "真实案件改编 · 部分画面为3D复原",
    "end_question": "关系一旦变成利用，谁来阻止下一步？",
    "highlight_keywords": [
        "金素英", "20岁", "前男友", "幸存", "南杨州", "水踰洞", "第一名死者", "第二名死者",
        "不是恋人", "汽车旅馆", "封闭空间", "消费", "主动选择", "警方认为", "检方认为",
        "聊天记录", "证据链", "一审法院认为", "明知可能死亡", "未必故意", "经济", "消费贪欲",
        "没有采信", "无期徒刑", "30年", "检方要求死刑", "双方都提起上诉", "完整案件",
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
    "douyin_title": "金素英为什么带他们去旅馆？两名死者与她的关系，终于说清",
    "hook": "雨落在南杨州。二十岁的金素英坐在男友对面；一个人醒来、报案，两名并非恋人的男子，先后走进水踰洞的旅馆。",
    "cover_title": "她为什么带他们去旅馆？",
    "hashtags": ["#真实事件", "#汽车旅馆命案", "#韩国", "#ChatGPT", "#悬疑", "#电影感"],
    "release_intro": (
        "雨落在南杨州的玻璃窗上。二十岁的金素英坐在男友对面；两天后，他醒来、分手、报案。"
        "一个月后，水踰洞的两扇旅馆门，先后在两名并非恋人的二十多岁男子身后合上。\n\n"
        "警方与检方调查认为，她把接触到的男性当成消费的承担者，并主动推进约会后的旅馆安排；"
        "一审法院认为，她已经知道风险却仍继续，主因是经济和消费贪欲，而非爱情纠纷。\n\n"
        "2026年8月27日，金素英一审被判无期徒刑并被命令接受30年电子定位监管；"
        "检方曾要求死刑。她于8月28日、检方于9月2日分别上诉，案件仍在二审中。\n\n"
        "画面为AI生成的3D动画情景复原，不是新闻影像；人物均为虚构演员形象。"
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
            "narration_visual_anchor": VISUAL_ANCHORS[sid],
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
        "delivery_basename": DELIVERY_BASENAME,
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
            "voice_id": SELECTED_VOICE_ID,
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
            "姓名：首尔北部地方检察厅已依法公开被告金素英的姓名、年龄和照片；片中直接称“金素英”，不再以“金某”代替。",
            "关系：2025年12月南杨州事件中的男性是她当时的男友，后幸存并报案；1月28日和2月9日死亡的两名20多岁男性均非其男友，公开资料未披露其姓名、职业和完整私交。",
            "动机与地点：对消费利用、旅馆由金素英主动推进、冲突回避等内容，使用“警方认为”或“检方认为”；不把未公开细节和网络猜测写成事实。",
            "法律状态：一审法院认定存在未必故意，判处无期徒刑并命令30年电子定位监管；检方曾要求死刑，控辩双方均已上诉，因此一律写“一审法院认为”“被判”“检方要求”。",
            "片中不出现药物名称、药片、剂量、调配过程；厨房镜头只允许玻璃杯与光影；不出现遗体、血腥；受害者只以背影、剪影与白菊花出现。",
            "手机聊天界面一律用抽象线条与图标表示，不出现可读文字；片中文字全部由后期叠加。",
            "所有画面为AI 3D动画情景重现，不是新闻影像；人物均为风格化虚构演员，非真实肖像。",
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
        f"- 片尾：S30 黑场红色警告图标，后期叠加金色片名『{story['presentation'].get('end_title', TITLE)}』与副题"
        f"『{story['presentation'].get('end_subtitle', '')}』，最后 1 秒静音。",
        f"- 封面：沿用《迷案解码人》固定竖版模板；配套主标题『{story['presentation'].get('cover_title', story['presentation'].get('end_title', TITLE))}』。",
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
        text_sha = hashlib.sha256(shot["narration"].encode("utf-8")).hexdigest()
        # Never trust a same-looking manifest row alone: when a script is rebuilt before the
        # new TTS file exists, the old MP3 is still on disk.  Only an audio row explicitly
        # stamped with the current text hash is allowed to retain its audio SHA-256.
        same_audio_text = previous.get("audio_text_sha256") == text_sha
        sha = sha256(clip_path) if clip_path.is_file() and same_audio_text else None
        clips.append({
            "id": shot["id"],
            "file": clip_path.name,
            "text": shot["narration"],
            "text_sha256": text_sha,
            "audio_text_sha256": text_sha if sha else None,
            "sha256": sha,
            "voice_id": story["narration_spec"]["voice_id"],
            "voice_description": "用户选定的低沉克制男声；像电影旁白一样直接进入现场，句间留白，不使用解说式元叙事",
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
        f"**核心钩子：** {pres.get('hook', pres['release_intro'])}\n\n"
        "## 四列分镜表\n\n"
        "| 镜号 | 时间 | 口播（=字幕） | 画面 | 运镜 |\n|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## 事实边界\n\n"
        + "\n".join(f"- {item}" for item in story["fact_boundary"])
        + "\n\n## 发布文案\n\n" + pres["release_intro"] + "\n\n" + " ".join(pres["hashtags"]) + "\n",
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

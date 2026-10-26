#!/usr/bin/env python3
"""唯一内容源：索马顿海滩无名男子三分钟动画短片。

运行 ``python3 production/somerton/build_story.py`` 会生成 story.json、screenplay.md、
音频清单、抖音脚本与发布文案。每镜通过 generate.py 自动拼接 STYLE、对应角色设定与
NEGATIVE；29 镜均调用 Agnes Video 2.5 Flash 动态生成，720P 源片后期放大到 1080P。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
TITLE = "塔玛姆·舒德：索马顿海滩无名男尸"
FILM_NAME = "塔玛姆·舒德_索马顿海滩无名男尸_三分钟_QC修订版.mp4"

# 供每条 Agnes 提示词自动置顶的全局 STYLE。保留用户要求的 1940 年代黑色电影调性；
# 现代实验室镜头只把器材与服装换为当代，其余胶片色彩与镜头语言保持连续。
STYLE_PREFIX = (
    "【STYLE】Cinematic-quality 3D animated short film, restrained film-noir atmosphere, "
    "1940s vintage 35mm film texture, dark amber and deep teal contrast, strong chiaroscuro "
    "with volumetric light, coastal dawn mist, richly detailed realistic CGI materials, "
    "horizontal 16:9 widescreen composition, cinematic lens and shallow depth of field, "
    "subtle film grain, quiet investigative suspense rather than horror. Every clip is real "
    "continuous animation with visible natural movement (waves, wind, hands, people, particles "
    "or camera parallax); never a still image with a push-in. Period-correct 1940s Adelaide "
    "objects unless the shot explicitly takes place in 2022. Subject placed on a third line, "
    "use the full horizontal width, keep the lower 15 percent visually quiet for subtitles. "
)

NEGATIVE_PROMPT = (
    "【NEGATIVE】readable text, subtitles, captions, watermark, logo, blood, gore, wound, "
    "corpse close-up, body detail, exposed remains, deformed hands, extra fingers, extra limbs, "
    "facial collapse, distorted anatomy, modern object in a 1940s scene, modern clothing in a "
    "1940s scene, low resolution, flicker, style drift, vertical framing, portrait composition, "
    "black bars, frozen frame, slideshow, still image with artificial zoom, sudden scene change, "
    "unmotivated cut, jump scare, ghost, supernatural imagery, exaggerated violence."
)

CHARACTERS = {
    "somerton_man": (
        "【角色设定｜索马顿男子】A fictionalized, non-identifiable European-Australian man, "
        "about 40–45, strong build, short brown hair combed back; light-brown double-breasted "
        "suit, white shirt, tie, knitted sweater, polished shoes, no hat, an unlit cigarette "
        "tucked behind the right ear. The deceased is shown ONLY seated upright as a distant "
        "silhouette, from behind, or in half-shadow; calm and dignified, never a face reveal, "
        "never a body close-up, no injury. "
    ),
    "police_detective": (
        "【角色设定｜警察与探员】Australian police officers and detectives in historically "
        "plausible 1940s uniforms or wool overcoats with soft felt hats; restrained, procedural "
        "gestures, faces kept in profile, shadow, or background, no modern equipment. "
    ),
    "coroner": (
        "【角色设定｜验尸官】A focused middle-aged coroner in a period-appropriate white coat, "
        "round glasses and gloves; show only a side silhouette or gloved hands, never a corpse "
        "or any bodily detail. "
    ),
    "bystanders": (
        "【角色设定｜路人与车站旅客】Australian men and women in modest 1940s casual clothes, "
        "walking naturally at dawn or crossing the station concourse; no modern accessories, "
        "faces indistinct and not individually recognizable. "
    ),
    "station_clerk": (
        "【角色设定｜车站工作人员】A 1940s Adelaide railway cloakroom clerk in a plain "
        "waistcoat and shirtsleeves, seen from the side or hands only; calm procedural gestures, "
        "no modern uniform or equipment. "
    ),
    "nurse": (
        "【角色设定｜护士】A fictionalized woman about 30, shown only as a wary silhouette, "
        "curled hair and a light-colored 1940s nurse uniform; face remains unreadable and in "
        "half-shadow. "
    ),
    "modern_researcher": (
        "【角色设定｜现代研究者】2022-era forensic researchers in clean white lab coats, "
        "cool-white laboratory lighting, calm careful movements, anonymous and non-identifiable "
        "faces; contemporary scientific equipment only in this modern scene. "
    ),
    "anonymous_theorists": (
        "【角色设定｜传闻中的匿名人物】Anonymous 1940s silhouettes in period coats and hats, "
        "faces fully obscured; they are visual metaphors for unproven theories, not portraits or "
        "claims about real people. "
    ),
    "fictional_engineer": (
        "【角色设定｜虚构工程师意象】A wholly fictional, non-likeness young Melbourne electrical "
        "engineer in 1930s clothing, glasses, seen in profile or half-shadow at a workbench; not a "
        "verified portrait of Carl Webb and not a reconstruction of a known photograph. "
    ),
}

# 时间边界逐字沿用用户的 29 镜脚本；所有镜头均交给 Agnes 生成动态视频，
# 即使末镜有标题，也是在动画金色粒子背景上后期叠加，不以静态卡片冒充视频。
SHOT_ROWS = [
    ("S01", 0, 5, "N01", "低空航拍缓慢前推", ["somerton_man"],
     "Before sunrise on Somerton Beach, Adelaide, 1948. A vast empty beach, gray stone seawall on the left third, open dark sea and low stars across the right two-thirds. A small seated man silhouette against the wall slowly emerges through moving coastal fog; waves advance and retreat. Camera: one low aerial glide forward, very slow, ending with the seated silhouette still small and distant. No body detail, no readable text."),
    ("S02", 5, 5, "N01", "中近景侧面缓慢横移", ["somerton_man"],
     "At pre-dawn blue hour, a dignified side-rear medium view of the same seated man at the seawall: neat light-brown double-breasted suit, tie, knitted sweater, polished shoes, an unlit cigarette behind his right ear. Sea wind gently moves his jacket hem; first warm light creeps across one shoulder while his face stays entirely in half-shadow. Camera: slow lateral track, subtle breathing-like steadiness. No face reveal."),
    ("S03", 10, 7, "N02", "全景横向跟随路人", ["bystanders", "somerton_man"],
     "Golden sunrise on Somerton Beach, 1948. A few distant walkers in period clothes stroll along the waterline, notice the seated silhouette by the seawall, stop, exchange a worried glance, and one slowly approaches while the others remain back. Camera: wide shot, gentle lateral follow, then a small measured drift closer. Keep the man small and seated, no body detail."),
    ("S04", 17, 7, "斜俯拍跟随探员脚步", ["police_detective", "bystanders"],
     "An unmarked 1940s police car and a second period Ford stand at the edge of Somerton Beach. Their license plates are completely blank, with no letters or numbers; the vehicles carry no logos, insignia or writing. Australian detectives in period wool coats walk down the sand toward the seawall; footprints form a clear line, seabirds lift and wheel across the mist. Camera: high diagonal overhead tracking shot following the officers' measured steps. All signs, plates and surfaces remain blank; no text anywhere."),
    ("S05", 24, 6, "远景缓慢推进，回忆式轻晃", ["somerton_man", "bystanders"],
     "Flashback to the previous night: cold blue light under a 1940s streetlamp beside the seawall. The same man is only a distant half-shadow, seated and leaning against the wall; one arm slowly lifts and settles. A couple in period clothes glance over from far away, assume he is asleep, then turn and walk out of frame. Soft memory-like diffusion and a restrained handheld drift; no face, no injury, no body close-up."),
    ("S06", 30, 5, "俯拍定位，逐件跟随手部动作", ["police_detective"],
     "Top-down view of a worn wooden evidence table in a 1940s police room. Gloved hands place three completely unprinted objects on the table one at a time: a blank cream ticket-shaped paper slip, a plain narrow black comb, and a solid-color cigarette packet with no brand mark. The paper and packet are featureless and clean, without lines, labels, stamps or markings; each item lands with a small natural bounce. Camera holds overhead with a slight tracking adjustment. No letters, numbers, logos, symbols, pseudo-writing or text anywhere."),
    ("S07", 35, 7, "微距慢动作，缓慢下移", ["police_detective"],
     "Extreme close-up of gloved hands and vintage scissors cutting away a tiny, completely blank white cloth tab from a 1940s shirt collar; it has a featureless surface with no print, stitching, lines or marks. Loose fabric threads drift down in slow motion. The image gradually drains from muted color to monochrome, leaving only the collar seam and cut stitches. Camera: controlled macro tilt downward; no face or body. Absolutely no lettering, numbers, symbols or text on the garment."),
    ("S08", 42, 7, "横向滑轨穿过档案柜", ["police_detective"],
     "Inside a cold 1940s Australian police archive, tall steel filing cabinets recede into depth. A detective flips through old fingerprint cards at a desk; a rubber stamp marks each blank card with a red X shape, with no legible words or names. Camera: smooth lateral dolly past cabinets, ending on the unanswered stack. Period paper and desk lamp, no modern objects."),
    ("S09", 49, 6, "缓慢推近试管，冷白光", ["coroner"],
     "Restrained 1940s examination room, no remains visible. A soft, featureless white beam from an entirely off-camera surgical light falls across a steel table; do not show any part of the lamp. A coroner appears only as a side silhouette beside a table holding a magnifying glass, a plain clear flask and several unmarked test tubes. A gloved hand lifts one tube as the clear liquid briefly shifts to pale amber and then returns clear, a restrained physical change in the sample only. Camera: slow push toward the tube and glass, no bodily detail. All props and surfaces stay plain and unmarked: absolutely no text or lettering anywhere; no question marks, punctuation forms, symbols, logos, labels, writing, letters, numbers or pseudo-text; no graphic overlays or mystery icons."),
    ("S10", 55, 7, "从拱顶下降到柜台", ["bystanders", "police_detective"],
     "A 1949 Adelaide railway concourse framed only on its high glass-and-iron vaulted roof, bare stone pillars, drifting steam and travelers in period coats crossing in both directions. A detective walks toward a featureless wooden luggage counter. Every visible wall, pillar, desk and object is plain, smooth and completely unmarked; compose the camera away from wall-mounted objects and crop out all sign-shaped boards. No text or lettering at all: no station signs, black or green signboards, direction boards, panels, placards, plaques, posters, shopfronts, advertisements, clocks with numerals, printed tickets, labels, letters, numbers, logos, symbols, pseudo-writing or markings of any kind. If a rectangular panel appears, it is a uniform blank surface with absolutely no graphics. Camera: symmetrical slow crane-down from the empty vaulted roof to the detective and blank counter, one continuous move."),
    ("S11", 62, 7, "特写俯拍，逐件显露", ["police_detective", "station_clerk"],
     "Behind the wooden station counter, a clerk hands a detective a worn dark-brown leather suitcase. The detective sets it down and opens it; inside, a brush, a spool of orange thread and neatly folded clothing are revealed in sequence. Camera: close overhead arc around the opening case, smooth continuous movement. No logos, no readable tags."),
    ("S12", 69, 6, "缓慢推近衣物标签处", ["police_detective"],
     "Macro view of folded 1940s clothing inside an open suitcase. The labels have been completely removed; a detective's hand lifts one collar edge to reveal only plain empty stitch holes, with no tag or remnant attached. All fabric is unmarked and unprinted. Camera: slow macro push, shallow depth of field. No letters, numbers, label shapes, logos, symbols or pseudo-writing anywhere."),
    ("S13", 75, 7, "微距缓慢推进，慢动作展开", ["coroner"],
     "In the softly lit examination room, the coroner's gloved hand carefully opens a hidden watch pocket sewn inside folded trousers and lifts out a tiny rolled paper scrap with tweezers. The paper slowly unfurls beneath a warm lamp; no human body is shown. Camera: macro close-up, gentle push and shallow focus, paper fibers moving naturally."),
    ("S14", 82, 7, "缓慢推近纸面，金色显影", [],
     "Extreme close-up of aged cream paper against a nearly black background. A blank center area is illuminated by a warm golden beam; delicate antique Persian-style border motifs slowly bloom outward along the paper edges as fine dust drifts. Leave the center clean and flat for a precise post-production overlay of the only permitted readable phrase, Tamam Shud. Camera: very slow macro push; no other letters."),
    ("S15", 89, 6, "从书页特写缓慢拉远", [],
     "An old, unmarked poetry volume lies open on a dark desk; the final leaf is missing and its ragged torn edge is clearly visible. Every visible page is completely blank ivory paper, with no printed rows, handwriting, lines or marks; the leather cover has no title or embossing. Blank pages flutter in a gentle draft and fine gold dust rises; behind the book, a subtle Persian-inspired starfield and faint goblet-shaped light reflection appear as visual metaphor. Camera: slow pullback, one continuous move. No letters, numbers, symbols or pseudo-text."),
    ("S16", 95, 5, "桌面特写，纸片贴合慢动作", ["police_detective", "bystanders"],
     "At a 1940s police counter, a concerned man in a period suit places an old poetry book on the desk. A detective aligns the small paper fragment against the torn final page; the irregular edges fit exactly, and a brief warm glint travels across the seam. Camera: close tabletop shot with a gentle rack focus from hands to matching tear, no readable writing."),
    ("S17", 100, 7, "微距缓慢横移", [],
     "Extreme close-up of the completely blank, unmarked back cover of an old poetry book; there is no writing, ink, pencil, engraving or printed texture. A narrow beam of light sweeps across the empty cover. Separate pinpricks of gold dust rise above the book into the air, briefly forming a sparse, unconnected constellation of dots, then fade; no dots or lines are drawn on the cover. Camera: macro lateral drift. No letters, numbers, glyphs, symbols or pseudo-writing."),
    ("S18", 107, 7, "围绕黑板缓慢环绕，延时", ["police_detective"],
     "A dim 1940s analysis room. Several detectives appear only as silhouettes around a large, completely clean and empty blackboard; its dark surface has no chalk, writing, lines, symbols or marks. The detectives quietly compare a single blank sheet beneath a desk lamp while a wall clock's hands move rapidly in a time-lapse. Dust crosses the light and their shadows drift across the empty board. Camera: slow circular orbit, steady and continuous. Do not show notes, diagrams or any written material; no letters, numbers, glyphs or pseudo-text."),
    ("S19", 114, 6, "穿越式镜头：书页到电话线再到房屋", [],
     "Begin on a completely blank, unmarked ivory page beside an old rotary telephone. The camera glides down toward the phone; its cord becomes a thin amber light trail that flows across a stylized 1940s Adelaide street-map model made only of simple unlabeled street lines and coast contours, then reaches a small period house where one window lamp turns on. The page and map have no labels, print, names or symbols. Seamless forward travel; no lettering, numbers, glyphs or pseudo-writing."),
    ("S20", 120, 5, "低角度中景缓慢推近", ["nurse", "police_detective"],
     "At the entrance of a modest 1940s Adelaide house, a wary nurse with curled hair in a light uniform faces a detective in a wool coat and soft felt hat. She gently shakes her head; porch light stretches both shadows across the path, then the wooden door slowly closes between them. Camera: low medium shot, controlled slow push; faces stay in shadow."),
    ("S21", 125, 8, "旧报纸拼贴式快速推进", ["anonymous_theorists"],
     "A dynamic 1940s newsroom with anonymous shadow profiles moving behind a fast stream of completely blank, unprinted newsprint sheets. Every sheet is clean empty paper: no headlines, columns, paragraphs, captions, photographs, logos or marks; a single plain red folder adds a restrained Cold War color accent. The sheets sweep past the lens as the camera makes a brisk, smooth forward move. Keep every page featureless and text-free throughout: no letters, numbers, symbols or pseudo-writing."),
    ("S22", 133, 8, "低机位摇镜", ["anonymous_theorists"],
     "Night harbor under dense sea fog. Two anonymous men in period coats and hats quietly pass a closed briefcase between them; faces remain hidden. A distant warship silhouette shifts slowly beyond the mist as waves ripple across the foreground. Camera: low-angle pan from the passing case toward the ship. Clearly an imagined rumor illustration, not a documented event; no weapons, no readable text."),
    ("S23", 141, 9, "横向滑动，逐幅擦除", ["anonymous_theorists"],
     "Three ornate sepia picture frames stand side by side on a dark gallery wall, each a subtly animated illustrated hypothesis: an anonymous spy silhouette, a solitary figure beside a letter, and a sealed glass vial on a desk. An abstract red brushstroke appears on each frame's glass, then a passing light erases all three marks until only empty frames remain. Camera: smooth lateral slide; no corpse, no injury, no readable words."),
    ("S24", 150, 7, "浅景深缓慢环绕", ["modern_researcher"],
     "A 2022 university genetics laboratory under cool white light. An anonymous researcher in a white coat carefully places a tiny hair sample recovered from a plaster death mask into a scientific instrument; on a monitor, a luminous DNA double helix rotates slowly with no labels or readable data. Camera: shallow-focus slow orbit around the gloved hands and instrument, contemporary equipment only."),
    ("S25", 157, 6, "从树根拉升至树冠", [],
     "In a dark abstract visualization space, an immense illuminated family tree grows from a single root into hundreds of branching nodes. The camera cranes upward from the trunk through glowing branches; one final distant node lights softly, suggesting a genealogical lead rather than a definitive legal finding. Continuous particle motion, dark teal and muted gold, no readable names or text."),
    ("S26", 163, 5, "中景缓慢推近", ["fictional_engineer"],
     "A fictional, non-photographic 1930s Melbourne workroom, framed entirely from inside. A young engineer with glasses sits in profile and half-shadow at a desk among unmarked electrical instruments, plain wire coils and small components. Beyond a softly frosted window are only indistinct rooftops and blurred tram silhouettes; no shopfronts, street signs, advertisements or plaques are visible. No labels, diagrams, writing or markings on the desk, tools or windows. Camera: restrained medium push; illustrative composite, not a real portrait. No letters, numbers or pseudo-text."),
    ("S27", 168, 4, "分屏双向缓慢推近", ["police_detective", "modern_researcher"],
     "One clean vertical split-screen, divided exactly down the center and held continuously from the first frame through the last; both halves must remain visible at the same time, with no cut, alternating full-screen scene, wipe, dissolve or transition. Left half: a plain, completely unmarked 1940s police file folder rests on a desk as a small abstract red glow pulses beside it; the cover has no writing or marks. Right half: an anonymous modern researcher in a white coat stands by the Somerton seawall, looking at the sea as wind moves the coat and waves move behind. Both panels have independent subtle motion and a gentle synchronized push-in. Never show either half full-screen. No letters, numbers, labels, symbols or pseudo-text anywhere."),
    ("S28", 172, 4, "低机位缓慢拉远", [],
     "At golden-red dusk on Somerton Beach, the gray stone seawall is empty. An old poetry book lies open on the sand and its pages turn softly in the sea breeze; small waves shimmer in the background. Camera: low-angle slow pullback, revealing more of the empty shoreline and fading light. No person, no readable text."),
    ("S29", 176, 4, "固定机位，金色粒子持续流动", [],
     "A near-black cinematic end background with a subtle cloud of fine gold particles swirling and drifting continuously from left to right; a faint amber glow breathes in and out at the center. Camera remains locked and stable while the particles keep real motion. Leave clean central negative space for post-production Chinese title and subtitle; no generated letters or symbols."),
]

CHAPTERS = [
    ("N01", "黄金钩子", 0, 10,
     "一九四八年，澳大利亚索马顿海滩，一个男人靠着海堤坐着。他死了，却无人知道他是谁。"),
    ("N02", "清晨发现", 10, 25,
     "十二月一日清晨，路人在索马顿海滩发现了他。他西装笔挺，领带整齐，身上没有证件，也没有明显外伤。前一晚，有人看见他靠在海堤边一动不动，以为他只是睡着了。警方想查清他的身份，却找不到入口。"),
    ("N03", "身份被抹去", 35, 20,
     "所有衣物标签几乎都被剪掉。警方把指纹和牙齿记录送去比对，仍没有匹配。验尸官发现内脏充血，怀疑可能中毒；常见毒物却查不出来。死因从此成了问号。"),
    ("N04", "火车站行李箱", 55, 20,
     "一九四九年一月，阿德莱德火车站发现一只旧皮箱，警方怀疑属于他。箱里有衣物、剃须用品和橙线，线头与裤子的修补处相合。衣物上只剩下“基恩”这个姓氏，却无人报失踪。"),
    ("N05", "Tamam Shud", 75, 25,
     "随后复查时，验尸官在他裤子的暗袋里发现一张卷起的小纸片。上面印着两个波斯语词：Tamam Shud，意思是“结束了”。纸片来自诗集《鲁拜集》的末页。警方后来找到那本缺页的书，撕痕严丝合缝。"),
    ("N06", "密码与护士", 100, 25,
     "诗集封底还有一串潦草字母，几十年来无人能可靠破解。旁边的电话号码，指向附近一位护士。她对警方说，不认识这个人，也不知道自己的号码为何会出现在诗集里。线索似乎指向某个人，却没有结论。"),
    ("N07", "种种猜想", 125, 25,
     "于是，间谍、情杀、毒杀后抛尸的猜想越传越远。冷战刚刚开始，纸条像暗号，毒物又查不出来，故事不断长出新版本。但传闻不是证据；没有公开证据能证明其中任何一种。"),
    ("N08", "DNA线索", 150, 22,
     "二〇二二年，教授德里克·艾伯特与家谱专家科琳·菲茨帕特里克，用石膏面模里的头发做DNA家谱比对，指向一九〇五年出生的墨尔本工程师卡尔·查尔斯·韦伯。研究者称把握超九成九；警方仍未正式确认。"),
    ("N09", "回响", 172, 8,
     "死因和密码，依旧没有答案。你觉得，他是谁？在评论区说说看。"),
]

SOURCES = [
    {
        "id": "SRSA-archive",
        "title": "South Australian State Records: ‘But what poison?’ Mystery of the Somerton Man",
        "url": "https://archives.sa.gov.au/finding-information/discover-our-collection/stories-from-the-archive/but-what-poison-mystery-of-the-somerton-man",
        "supports": "1948发现与调查、衣物标记、指纹与毒物检查、尸检/验尸庭审、Tamam/Taman Shud纸片。",
    },
    {
        "id": "ABC-2018",
        "title": "ABC News: Unlocking the secrets of the Somerton Man",
        "url": "https://www.abc.net.au/news/2018-12-01/will-the-mystery-of-the-somerton-man-ever-be-solved/10420794",
        "supports": "1949年1月阿德莱德火车站发现被认为与男子有关的皮箱；Rubaiyat与‘Tamam Shud’线索。",
    },
    {
        "id": "ABC-2022-claim",
        "title": "ABC News: Somerton Man identified as Melbourne electrical engineer, researcher says",
        "url": "https://www.abc.net.au/news/2022-07-26/somerton-man-identified-melbourne-born-engineer-researcher-says/101272182",
        "supports": "研究者Derek Abbott与Colleen Fitzpatrick于2022年提出身份为Carl ‘Charles’ Webb；出生年份、墨尔本与工程师身份。",
    },
    {
        "id": "ABC-2022-police",
        "title": "ABC News: Somerton Man Charles Webb's true identity revealed in family photographs and divorce papers",
        "url": "https://www.abc.net.au/news/2022-11-21/somerton-manfamily-photographs-revealed-/101643524",
        "supports": "研究者使用石膏死亡面模中保存的头发做DNA家谱研究；警方当时表示仍需独立DNA工作并由Coroner最终确认。",
    },
    {
        "id": "ABC-2026-status",
        "title": "ABC News: SA Police report to coroner into Somerton Man case complete ‘very soon’",
        "url": "https://www.abc.net.au/news/2026-07-06/sa-police-report-coroner-into-somerton-man-case-very-soon/106869302",
        "supports": "截至2026年7月，研究者称DNA线索高度指向Webb；南澳警方回应称验尸官调查复杂且仍在进行，尚未正式确认。",
    },
    {
        "id": "Abbott-inquest",
        "title": "Derek Abbott: The Taman Shud Case Coronial Inquest (transcription of 1949 inquest materials)",
        "url": "https://www.eleceng.adelaide.edu.au/personal/dabbott/wiki/index.php/The_Taman_Shud_Case_Coronial_Inquest",
        "supports": "1949年验尸庭材料转录，包含衣物标签、检验常见毒物与证物描述；该页面为研究者整理的档案转录。",
    },
]

HIGHLIGHTS = [
    "他是谁", "没有证件", "没有匹配", "标签", "中毒", "橙线", "基恩",
    "Tamam Shud", "结束了", "无人能可靠破解", "护士", "传闻不是证据",
    "卡尔·查尔斯·韦伯", "超九成九", "警方仍未正式确认", "死因", "密码", "无解",
]

PRESENTATION = {
    "cover": {
        "layout": "16:9; man silhouette on right; left side reserved for title",
        "text": "他是谁?",
        "subtext": "塔玛姆·舒德 · 索马顿海滩无名男尸",
        "style": "金色粗体字、深色描边；画面由S01海滩动态镜头抽帧并水平翻转，非静态图替代视频",
    },
    "end_title": "塔玛姆·舒德",
    "end_subtitle": "索马顿海滩无名男尸",
    "voice_pauses": {
        "N03": {"after_text": "所有衣物标签几乎都被剪掉。", "seconds": 0.5},
        "N09": {"after_text": "死因和密码，依旧没有答案。", "seconds": 0.5},
    },
    "highlight_keywords": HIGHLIGHTS,
    "subtitle_style": {
        "font_size_px": 58,
        "outline_px": 3,
        "safe_bottom_margin_px": 72,
        "alignment": "bottom-center",
        "normal_color": "white",
        "highlight_color": "gold",
        "highlight_scale": 1.20,
    },
    "sound_events": [
        {"at": 0, "name": "低沉大提琴单音渐强 + 海浪", "kind": "music_sfx"},
        {"at": 8, "name": "远处钟响", "kind": "sfx"},
        {"at": 10, "name": "晨风与海鸥", "kind": "sfx"},
        {"at": 24, "name": "冷蓝夜风与回忆氛围", "kind": "sfx"},
        {"at": 30, "name": "物品轻放与清脆金属叮声", "kind": "sfx"},
        {"at": 35, "name": "剪刀声、低音钢琴与秒针节拍", "kind": "sfx_music"},
        {"at": 55, "name": "蒸汽火车与钢琴点奏", "kind": "sfx_music"},
        {"at": 75, "name": "波斯弦乐与手鼓式脉冲", "kind": "music_sfx"},
        {"at": 100, "name": "老式电话拨号与电子点奏", "kind": "sfx_music"},
        {"at": 125, "name": "冷战铜管和低鼓，段尾留白", "kind": "music_sfx"},
        {"at": 150, "name": "冷峻电子脉冲渐亮", "kind": "music_sfx"},
        {"at": 172, "name": "大提琴单音收尾，海浪渐弱，最后一秒静音", "kind": "music_sfx"},
    ],
    "douyin_title": "一个没人认识的男人，口袋里只有两个字：结束了",
    "hashtags": ["#未解之谜", "#索马顿海滩", "#塔玛姆舒德", "#悬疑", "#3D动画"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build() -> dict:
    chapters = [
        {"id": cid, "title": title, "start": start, "duration": duration, "text": text}
        for cid, title, start, duration, text in CHAPTERS
    ]
    shots = []
    for index, row in enumerate(SHOT_ROWS):
        if len(row) == 7:
            sid, start, duration, narration_id, camera, character_ids, prompt = row
        elif len(row) == 6:
            sid, start, duration, camera, character_ids, prompt = row
            narration_id = next(
                chapter[0] for chapter in CHAPTERS
                if chapter[2] <= start < chapter[2] + chapter[3]
            )
        else:
            raise ValueError(f"Invalid shot row: {row!r}")
        shots.append({
            "id": sid,
            "kind": "agnes",
            "start": start,
            "duration": duration,
            "narration_id": narration_id,
            "camera": camera,
            "characters": character_ids,
            "prompt": prompt,
            "purpose": prompt.split(".")[0].strip(),
            "seed": 19481201 + index,
            "seconds": duration,
            "aspect": "16:9",
            "source_size": "720P",
            "transition_out": "同段硬切或轻叠化；章间0.3秒海雾/黑场，不改变旁白时间轴。",
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
        "branch": "arena/dc7c8423-desktop-tutorial",
        "style_prefix": STYLE_PREFIX,
        "negative_prompt": NEGATIVE_PROMPT,
        "characters": CHARACTERS,
        "principles": [
            "全片29个镜头均由Agnes Video 2.5 Flash生成连续运动的3D动画片段，禁止静态图加推拉代替；生成源片720P，后期放大到1920×1080。",
            "人物出现时生成器先拼接对应角色设定；所有提示词以STYLE开头、以NEGATIVE结尾；2.5 Flash不接受negative_prompt独立字段，因此红线嵌入提示词正文。",
            "不出现尸体特写、血腥或伤口；逝者只以坐姿剪影、背影或半阴影表现。",
            "所有字幕均由后期准确叠加；仅S14纸面显示Tamam Shud，片尾叠加中文片名；封面单独叠加‘他是谁?’，片内镜头不加开场字卡。",
            "每镜4至9秒，16:9；主体放在三分线上，充分利用横向宽度，底部15%留给字幕。",
            "研究者身份说法明确标注为2022年研究团队主张；截至2026年10月22日复核，能找到的最新直接警方状态为2026年7月：调查复杂且仍在进行，不称为官方确认。",
            "毒杀、间谍、情杀、护士关联等只作为未经证实的猜想呈现，不能包装成事实。",
            "研究者使用的是石膏面模中保存的头发；不可写成从尸体/头皮直接取发。",
        ],
        "chapters": chapters,
        "shots": shots,
        "sources": SOURCES,
        "presentation": PRESENTATION,
        "reference_images": [
            {"file": "reference/01-somerton-man-character.png", "description": "虚构角色造型定稿；非真实肖像"},
            {"file": "reference/02-somerton-beach-environment.png", "description": "海滩场景定稿；无名男子仅为远景坐姿剪影"},
            {"file": "reference/03-evidence-world.png", "description": "证物室与道具色彩定稿；非原始证物照片"},
        ],
    }


def write_screenplay(story: dict) -> None:
    lines = [
        f"# {story['title']}",
        "",
        "三分钟横屏悬疑短片 · Agnes Video 2.5 Flash 720P源片后期放大至1920×1080 · 30fps · 180秒 · 29个动态镜头",
        "",
        "> 画面为AI动画情景重现，不是历史影像或真实证物；人物与场景先定稿参考图，再按镜头逐条生成。",
        "",
        "## 角色与场景定稿参考图",
        "",
        "- `reference/01-somerton-man-character.png`：索马顿男子虚构造型（坐姿背影/半阴影，不是肖像）。",
        "- `reference/02-somerton-beach-environment.png`：1948索马顿海滩宽幅构图参考。",
        "- `reference/03-evidence-world.png`：档案桌、皮箱与证物道具参考（不是原始证物）。",
        "",
        "## 事实边界与更新",
        "",
        "- 1948年12月1日清晨，男子在阿德莱德索马顿海滩被发现；没有证件，衣物标签被剪除，身份调查未能当时确认。",
        "- 1949年1月，阿德莱德火车站寄存处发现一只被认为与男子有关的皮箱；橙色缝线与衣物修补线索相合。",
        "- 纸片上的Tamam Shud来自《鲁拜集》末页；该波斯语短语常译为“结束了/已完结”。护士电话号码与密码线索并未给出确定解释。",
        "- 2022年，Derek Abbott与Colleen Fitzpatrick提出研究者身份判断为Carl“Charles”Webb；所用DNA来自石膏死亡面模中保存的头发。",
        "- 研究者称基因家谱线索高度支持Webb；ABC于2026年7月6日引述警方称验尸官调查复杂且仍在进行。项目于2026年10月22日再次检索，未找到此后新的直接警方/验尸官公开结论；发布前仍应复查。",
        "- 死因与密码依然没有官方结论；间谍、情杀和毒杀等均作为未证实猜想，不替观众下结论。",
        "",
        "## 旁白（每秒约3.7字）",
        "",
    ]
    for chapter in story["chapters"]:
        start = chapter["start"]
        end = start + chapter["duration"]
        lines += [f"### {start//60:02d}:{start%60:02d}—{end//60:02d}:{end%60:02d}　{chapter['title']}（{chapter['id']}）", "", chapter["text"], ""]
    lines += ["## 29镜分镜表", "", "| 镜号 | 时间 | 秒数 | 章节 | 运镜 | 叙事职责 |", "|---|---:|---:|---|---|---|"]
    for shot in story["shots"]:
        start, end = shot["start"], shot["start"] + shot["duration"]
        times = f"{start//60:02d}:{start%60:02d}—{end//60:02d}:{end%60:02d}"
        lines.append(f"| {shot['id']} | {times} | {shot['duration']} | {shot['narration_id']} | {shot['camera']} | {shot['purpose']} |")
    lines += ["", "## 来源", ""]
    for source in story["sources"]:
        lines.append(f"- [{source['title']}]({source['url']})：{source['supports']}")
    lines += ["", "## 后期规范", "", "- 配音：用户试听选择的低沉成熟男声（voice-00），悬疑讲述语气；N03第一句后和N09“没有答案”后各留约0.5秒停顿。", "- 字幕：逐句同步，白字黑边，底部安全区；关键词放大并用金色高亮。", "- 音乐/音效：海浪、钟声、海鸥、剪刀、蒸汽火车、拨号、低频心跳/弦乐；BGM在人声时压低约18dB。", "- 片尾：最后一秒音频静音，画面保留金色粒子运动；片名与副标题由后期叠字。", "- 封面：从S01海滩视频抽帧并水平翻转，男子剪影位于右侧，左侧叠加金色“他是谁?”。", ""]
    (HERE / "screenplay.md").write_text("\n".join(lines), encoding="utf-8")


def write_manifest(story: dict) -> None:
    AUDIO.mkdir(parents=True, exist_ok=True)
    existing = {}
    manifest_path = AUDIO / "manifest.json"
    if manifest_path.exists():
        try:
            existing = {row["id"]: row for row in json.loads(manifest_path.read_text(encoding="utf-8")).get("clips", [])}
        except (ValueError, KeyError, TypeError):
            existing = {}
    clips = []
    for chapter in story["chapters"]:
        clip_path = AUDIO / f"{chapter['id']}.mp3"
        sha = sha256(clip_path) if clip_path.is_file() else existing.get(chapter["id"], {}).get("sha256")
        clips.append({
            "id": chapter["id"],
            "file": clip_path.name,
            "text": chapter["text"],
            "sha256": sha,
            "voice_id": "voice-00",
            "voice_description": "用户试听选定：成熟、低沉、悬疑叙事男声",
            "target_start": chapter["start"],
            "target_duration": chapter["duration"],
        })
    manifest = {"language": "zh-CN", "voice": "voice-00", "generation": "Arena TTS selected voice", "clips": clips}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_release_copy(story: dict) -> None:
    pres = story["presentation"]
    (HERE / "抖音发布文案.md").write_text(
        f"# {pres['douyin_title']}\n\n"
        "1948年，一个西装笔挺的男人被发现坐在索马顿海滩。他没有身份，口袋里却藏着一句“结束了”。\n\n"
        "2022年，研究者把DNA线索指向卡尔·查尔斯·韦伯；但截至2026年7月，警方仍未正式确认。\n"
        "死因、纸条上的密码、以及那些流传多年的猜想，仍没有最终答案。\n\n"
        "画面为AI生成的情景复原，不是历史影像或真实证物。\n\n"
        "你觉得，他是谁？\n\n"
        + " ".join(pres["hashtags"]) + "\n",
        encoding="utf-8",
    )
    (HERE / "抖音脚本.md").write_text(
        f"# {TITLE}\n\n"
        f"**核心钩子：** {pres['cover']['text']}\n\n"
        f"**发布标题：** {pres['douyin_title']}\n\n"
        "**时长：** 180秒；横屏16:9；29条Agnes Video 2.5 Flash动态片段（720P源片后期放大至1920×1080）。\n\n"
        "| 镜头 | 时间 | 旁白/章节 | 画面提示词 | 运镜 | 音效 |\n|---|---|---|---|---|---|\n"
        + "\n".join(
            f"| {s['id']} | {s['start']}–{s['start']+s['duration']}秒 | {s['narration_id']} | {s['purpose']} | {s['camera']} | 依章节声音设计 |"
            for s in story["shots"]
        )
        + "\n\n**事实边界：** 研究者的身份认定不是南澳警方/验尸官的正式结论；任何间谍、情杀或毒杀说法都只是猜测。\n",
        encoding="utf-8",
    )


def main() -> None:
    story = build()
    (HERE / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_screenplay(story)
    write_manifest(story)
    write_release_copy(story)
    print(f"WROTE {HERE/'story.json'} — {len(story['shots'])} Agnes Video 2.5 Flash shots, 720P sources, 180s, 16:9")


if __name__ == "__main__":
    main()

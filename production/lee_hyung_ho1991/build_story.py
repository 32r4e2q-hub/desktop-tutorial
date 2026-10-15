#!/usr/bin/env python3
"""Build the fact-checked 3-minute Lee Hyung-ho case plan from one source of truth."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "cogvideox-flash"
BRANCH = "arena/1f36798e-desktop-tutorial"

STYLE_PREFIX = (
    "3D CGI documentary reenactment, Seoul winter 1991; period-correct Korean streets, phones and interiors, "
    "cinematic 16:9, cold blue-grey with restrained tungsten and film grain; one slow continuous move, no cuts. "
    "Fictional cast only: use each reference to keep repeated IDs' face, hair and wardrobe identical; different IDs "
    "must look distinct. No real-person likeness, text, logos or graphic violence. "
)

CHAPTERS = [
    {
        "id": "N01",
        "title": "失踪：电话在深夜响起",
        "text": (
            "一九九一年一月二十九日，首尔狎鸥亭。九岁的李亨浩在公寓旁的游乐场玩耍，傍晚却没有回家。"
            "深夜十一点，父亲接到电话，来电者声称孩子在他手上，并索要七千万韩元，还要求一辆装有车载电话的车。"
            "没有镜头能替这家人把时间倒回去；从这个夜晚开始，电话铃声成了他们唯一的线索。"
        ),
    },
    {
        "id": "N02",
        "title": "勒索：每次来电都像一线希望",
        "text": (
            "赎金并没有换来一次清楚的交接。来电者不断更换地点，也曾要求家人把钱汇进指定账户。"
            "父亲在首尔街头往返，记下每个地址、每句指令；家人不知道下一通电话会带来希望，还是另一个陷阱。"
            "多家媒体回顾，案件中出现了六十多通勒索电话；但每个号码背后，都没有一个能被确认的姓名。"
        ),
    },
    {
        "id": "N03",
        "title": "布控：一次联络错位",
        "text": (
            "警方与家属尝试布控，盯守交钱地点，核查账户与银行线索。一次交接中，警员因联络错位守错位置，取钱者脱身。"
            "后来，存款记录与柜员描述仍没能确认身份。每次行动结束，父亲回到家，等待的仍只有下一次铃响；"
            "希望一次次被递来，又一次次被抽走。"
        ),
    },
    {
        "id": "N04",
        "title": "发现：失踪后的第四十四天",
        "text": (
            "一九九一年三月十三日，失踪后的第四十四天，工人在蚕室一带的排水沟发现亨浩。画面停在警戒线外，不展示遗体。"
            "法医确认他死于窒息；胃里的内容物与失踪当天吃过的午餐相符。有报道据此推测，他可能在失踪当天遇害；"
            "具体死亡时间，公开资料无法精确确定。"
        ),
    },
    {
        "id": "N05",
        "title": "悬案：追诉时效届满",
        "text": (
            "警方公开嫌疑人画像，重新检查电话录音、汇款记录和旧卷宗；调查始终没能把一个具体的人和所有线索连在一起。"
            "二〇〇六年，韩国当时适用的追诉时效届满，凶手仍未确认，案件因此无法起诉。"
            "四十多天的等待结束了，但追查没有给家人一个可以告别的答案。"
        ),
    },
    {
        "id": "N06",
        "title": "回声：录音被重新听见",
        "text": (
            "二〇〇七年，案件被拍成电影《那家伙的声音》，让那段来电再次进入公众记忆。二〇一九年，警方将旧录音带数字化并重新分析声纹，希望找到新线索。"
            "多年过去，声纹仍没有指向已确认的凶手。截至二〇二六年，案件依旧未侦破。今天留下的不是凶手的传奇，"
            "而是一个九岁孩子被夺走的日常，以及仍在等待真相的家人。三十五年后，真相还可能从哪里出现？"
        ),
    },
]

CHARACTERS = {
    "father": {
        "name": "FATHER-01",
        "role": "父亲（虚构情景演员）",
        "reference_image": "references/father-lee.jpg",
        "prompt": "FATHER-01: same fictional late-30s Korean man; narrow oval face, straight brows, tiny mole below left eye, neat side-parted black hair, navy coat and pale-blue shirt. Keep this exact face and outfit.",
    },
    "mother": {
        "name": "MOTHER-01",
        "role": "母亲（虚构情景演员）",
        "reference_image": "references/mother-lee.jpg",
        "prompt": "MOTHER-01: same fictional late-30s Korean woman; heart-shaped face, almond eyes, tiny mark by right jaw, shoulder-length wavy black hair, burgundy cardigan. Keep this exact face and outfit.",
    },
    "child": {
        "name": "CHILD-01",
        "role": "儿童（虚构动画角色，非真人复原）",
        "reference_image": "references/child-lee-stylized.png",
        "prompt": "CHILD-01: a wholly fictional, clearly animated Korean boy, about nine; round cheeks, short side-parted black hair, a small right-cheek dimple, blue-and-white 1991 tracksuit. Match this reference face and outfit; no real-person likeness.",
    },
    "detective_park": {
        "name": "DETECTIVE-PARK-01",
        "role": "朴警探（虚构情景演员）",
        "reference_image": "references/detectives-park-choi.jpg",
        "prompt": "DETECTIVE-PARK-01: same fictional late-40s Korean man; broad square jaw, thick brows, swept-back black hair grey at the temples, charcoal coat. Preserve his distinct face.",
    },
    "detective_choi": {
        "name": "DETECTIVE-CHOI-01",
        "role": "崔警探（虚构情景演员）",
        "reference_image": "references/detectives-park-choi.jpg",
        "prompt": "DETECTIVE-CHOI-01: same fictional late-30s Korean woman; slim oval face, glasses, chin-length black bob, olive trench. Clearly different from Park; preserve her face.",
    },
    "caller_unknown": {
        "name": "CALLER-UNKNOWN",
        "role": "身份未明的来电者（面容不呈现）",
        "reference_image": "",
        "prompt": "CALLER-UNKNOWN: an unidentified adult shown only as the same distant, hooded silhouette; keep the face fully hidden and do not imply an identified suspect.",
    },
    "bank_visitor_unknown": {
        "name": "BANK-VISITOR-UNKNOWN",
        "role": "身份未明的取款者（面容不呈现）",
        "reference_image": "",
        "prompt": "BANK-VISITOR-UNKNOWN: a separate unidentified adult, seen only from behind with face fully hidden; do not equate this person with the caller.",
    },
}

# id, chapter, visual, purpose, camera, optional post-production card
SHOTS = [
    ("S01", "N01", "A 1991 Korean rotary telephone trembling on a wooden table in a dim family living room, its indicator lamp glows softly; slow push toward the handset.", "深夜电话响起", "slow push-in", None),
    ("S02", "N01", "A winter 1991 Seoul apartment playground at dusk, an empty metal swing moving gently under a yellow streetlamp; wide lateral pan through thin fog.", "狎鸥亭冬夜空荡的游乐场", "slow lateral pan", None),
    ("S03", "N01", "案件资料卡：日期与地点", "失踪日期与地点", "post-production card", "graphic"),
    ("S04", "N01", "CHILD-01 plays quietly beside an empty playground swing in a blue-and-white period tracksuit; briefly show his same fictional reference face in a calm side profile, then slowly pull back. Peaceful scene, no danger or harm.", "虚构儿童侧影与空荡游乐场", "slow pull-back", None),
    ("S05", "N01", "FATHER-01 searches the empty apartment playground beneath winter trees, his navy coat and the same side-profile face visible as he turns toward the empty swing; gentle tracking shot.", "父亲在游乐场寻找孩子", "gentle tracking", None),
    ("S06", "N01", "A beige 1990s telephone beside a small desk clock in a dark Seoul apartment at night; the phone begins to ring, warm lamp against cold window light.", "家中电话再次响起", "slow push-in", None),
    ("S07", "N01", "FATHER-01 lifts a beige telephone receiver in a dim 1991 living room; medium over-shoulder framing includes his same three-quarter reference face, navy sleeve and the warm lamp, with one restrained camera drift.", "父亲接起勒索电话", "slow drift", None),
    ("S08", "N01", "MOTHER-01 stands in the child's quiet 1991 bedroom, holding his folded blue jacket beside the empty bed; her same reference face is seen in soft profile as the curtain moves in the winter draft, quiet slow pan.", "母亲在空荡的儿童房守候", "slow pan", None),

    ("S09", "N02", "A 1991 Seoul street telephone booth in light rain at night, reflections passing across the glass while the booth remains empty; slow dolly toward it.", "不断变换的街头来电", "slow dolly", None),
    ("S10", "N02", "案件资料卡：首轮赎金与车载电话要求", "七千万韩元与车载电话", "post-production card", "graphic"),
    ("S11", "N02", "MOTHER-01 writes the changing instructions on a deliberately blank note beside the landline; show her same reference face, burgundy sleeve and tense writing hand in one close, slow push, no legible text.", "母亲记录不断变化的交接指令", "slow push-in", None),
    ("S12", "N02", "FATHER-01 waits at the wheel of a parked period-correct 1991 Seoul sedan at night, one hand near a car telephone; his canonical reference face stays clearly visible in three-quarter view, same navy coat and pale-blue shirt. Streetlights reflect softly across the window; one slow passenger-seat push-in.", "父亲深夜在车中等待下一通电话", "slow passenger-seat push-in", None),
    ("S13", "N02", "A quiet Seoul intersection with a public phone booth, wet pavement and distant headlights reflected in shop windows; one continuous slow pan, no readable signs.", "反复变化的地点", "slow pan", None),
    ("S14", "N02", "CALLER-UNKNOWN appears only as the same distant hooded silhouette behind rain-streaked phone-booth glass, face fully hidden, one gloved hand holding the receiver; slow, subtle push.", "身份未明来电者的匿名背影", "slow push-in", None),
    ("S15", "N02", "A plain sealed envelope resting on a wet stone ledge beneath a streetlamp, no money or writing visible; slow close-up with winter rain in the background.", "赎金交接留下的空白", "slow close-up", None),

    ("S16", "N03", "The two reference detectives sit in a 1991 unmarked sedan listening to a cassette recorder; their distinct faces catch sliding streetlight through the windshield.", "两名警探监听与布控", "slow windshield drift", None),
    ("S17", "N03", "案件资料卡：六十多通勒索电话", "来电数量", "post-production card", "graphic"),
    ("S18", "N03", "FATHER-01 carries a closed plain bag toward a distant empty meeting point at night; begin on his same reference profile before following him from behind across a rain-dark street; no handover shown.", "父亲按指令前往交接地点", "slow tracking", None),
    ("S19", "N03", "The same two reference detectives wait in their unmarked police car behind rain-speckled glass; their different profiles catch streetlight in a restrained slow push.", "警方等待交接信号", "slow push-in", None),
    ("S20", "N03", "A quiet empty curb at the opposite side of a 1991 Seoul intersection, an unmarked sedan waits in the distance while headlights pass; slow pan suggests a missed position.", "联络错位后的空守地点", "slow pan", None),
    ("S21", "N03", "BANK-VISITOR-UNKNOWN, a separate unidentified adult, leaves the dim bank lobby seen only from behind with a small paper envelope; face hidden, blank forms, never imply this is the caller; slow lateral track.", "取款者身份仍无法确认", "slow lateral track", None),
    ("S22", "N03", "A detective's hands align an unmarked cassette, blank bank slips and a paper city map beneath a green desk lamp; charcoal sleeves, slow overhead drift, no face shown.", "警探整理录音、账户与地图线索", "slow overhead drift", None),
    ("S23", "N03", "FATHER-01 sits alone beside the silent telephone, shoulders lowered; his same three-quarter reference face and navy coat are visible in the dim family living room as the camera slowly pushes in.", "一次次等待后的沉默", "slow push-in", None),

    ("S24", "N04", "案件资料卡：发现日期与排水沟", "发现日期", "post-production card", "graphic"),
    ("S25", "N04", "Dawn beside a drainage channel in the Jamsil area, distant municipal workers stop and call for help; no body or graphic detail, cold mist and a slow pull back.", "发现地点的远景，不展示遗体", "slow pull-back", None),
    ("S26", "N04", "The same two reference detectives stand beside police tape, their different faces softly lit and heads bowed; respectful distance, no body shown, slow sideways drift.", "两名警探在警戒线外", "slow sideways drift", None),
    ("S27", "N04", "FATHER-01 waits in a quiet police-station corridor beneath fluorescent lights, hands clasped; show his same reference face in a tired three-quarter profile as the camera slowly approaches.", "父亲等待消息", "slow approach", None),
    ("S28", "N04", "Gloved hands review a closed, unmarked medical file on a desk, a small diagram is completely blurred and non-graphic; restrained overhead camera drift.", "法医材料以非图像化方式呈现", "slow overhead drift", None),
    ("S29", "N04", "A small untouched lunch bowl on a family table beside a child's folded sleeve, soft winter window light, no person or readable text; slow close-up.", "以日常物件呈现失去的日常", "slow close-up", None),
    ("S30", "N04", "案件资料卡：死因与死亡时间的不确定性", "法医结论", "post-production card", "graphic"),

    ("S31", "N05", "A police artist's blank suspect-sketch sheet on a desk, only an indistinct empty outline with no facial features; a hand turns the page slowly.", "警方公开画像线索", "slow page turn", None),
    ("S32", "N05", "A detective's hand places an old cassette beside a blank evidence folder in the 1990s archive room; only the charcoal sleeve and hand are visible in a narrow beam of dust-lit light, slow push-in.", "重新检查旧录音与卷宗", "slow push-in", None),
    ("S33", "N05", "Close view of a detective's charcoal-sleeved hands comparing blank bank slips and a ledger; all writing is out of focus, no face, names or numbers.", "核对汇款记录", "slow close-up", None),
    ("S34", "N05", "FATHER-01 sits across from an older detective in a quiet interview room; the father's same reference face is visible while the detective is seen only from behind, a closed folder between them, quiet respectful framing.", "父亲与警探多年后仍未确认身份", "slow drift", None),
    ("S35", "N05", "A dusty archive shelf with a single closed case box and analog cassette, thin sunlight across the labels which remain unreadable; slow dolly past.", "未能破解的旧案卷宗", "slow dolly", None),
    ("S36", "N05", "Blank calendar pages turn slowly beside an old analog clock, visual passage from early 1990s to mid-2000s without legible dates; cinematic time-lapse kept within one view.", "时间走向追诉时效届满", "slow time-lapse", None),
    ("S37", "N05", "案件资料卡：追诉时效届满", "二〇〇六年追诉时效", "post-production card", "graphic"),

    ("S38", "N06", "A dark Seoul cinema auditorium in 2007, projector beam crossing rows of anonymous audience silhouettes, the screen shows only soft abstract light, no film footage or text.", "案件进入公众记忆", "slow aisle push", None),
    ("S39", "N06", "An old analog cassette being digitized on a modern audio workstation, reels turning beside a plain computer monitor with no readable interface; slow close-up.", "二〇一九年旧录音数字化", "slow close-up", None),
    ("S40", "N06", "A neutral green audio waveform moving across a dark monitor in a quiet police lab, no voice or text is shown; slow camera drift through reflected light.", "重新分析声纹", "slow drift", None),
    ("S41", "N06", "FATHER-01's hands in the same navy wool sleeves hold a small family photograph turned away from camera; the image is out of focus, his face is not shown, warm window light in a quiet room.", "家属仍在等待真相", "slow close-up", None),
    ("S42", "N06", "A modern Seoul evening crowd passes through a subway plaza, no single person singled out, anonymous figures blurred by gentle motion; slow elevated pan.", "凶手身份仍未确认", "slow elevated pan", None),
    ("S43", "N06", "An empty metal swing at a Seoul playground at dawn with one small white flower resting on the seat, pale winter light and a gentle breeze; slow pull back.", "以空秋千纪念亨浩", "slow pull-back", None),
    ("S44", "N06", "MOTHER-01 sits by the silent old telephone at blue hour; her exact reference face and burgundy cardigan appear in profile beside a turned-away, out-of-focus family photograph as the lamp dims, long restrained push.", "母亲与电话留下的回声", "slow push-in", None),
    ("S45", "N06", "案件资料卡：未侦破状态与后续录音调查", "案件仍未侦破", "post-production card", "graphic"),
]

SHOT_CHARACTERS = {
    "S04": ["child"],
    "S05": ["father"], "S07": ["father"], "S08": ["mother"], "S11": ["mother"],
    "S12": ["father"], "S14": ["caller_unknown"],
    "S16": ["detective_park", "detective_choi"], "S18": ["father"],
    "S19": ["detective_park", "detective_choi"], "S21": ["bank_visitor_unknown"],
    "S23": ["father"],
    "S26": ["detective_park", "detective_choi"], "S27": ["father"],
    "S34": ["father"], "S41": ["father"], "S44": ["mother"],
}

SHOT_REFERENCE_OVERRIDES = {
    "S16": "references/detectives-park-choi.jpg",
    "S19": "references/detectives-park-choi.jpg",
    "S26": "references/detectives-park-choi.jpg",
    "S41": "",  # hands/photograph only; intentionally no face-reference frame
}

SHOT_FACE_VISIBLE = {
    "S04": True, "S05": True, "S07": True, "S08": True, "S11": True,
    "S12": True, "S14": False, "S16": True, "S18": True, "S19": True,
    "S21": False, "S23": True, "S26": True, "S27": True, "S34": True,
    "S41": False, "S44": True,
}

CARD_COPY = {
    "S03": ["一九九一年一月二十九日", "首尔狎鸥亭 · 九岁李亨浩失踪", "深夜来电索要七千万韩元"],
    "S10": ["七千万韩元", "来电者另要求一辆装有车载电话的车", "勒索指令随后多次改变"],
    "S17": ["六十多通电话", "多家媒体对勒索来电的报道口径", "每一次响铃，家人都在等待孩子"],
    "S24": ["一九九一年三月十三日", "失踪后的第四十四天 · 蚕室一带", "排水沟中发现亨浩"],
    "S30": ["法医结论", "死因为窒息 · 胃内容物与失踪日午餐相符", "可能很早遇害 · 精确时点不明"],
    "S37": ["二〇〇六年", "当时适用的追诉时效届满", "案件未侦破 · 无法起诉"],
    "S45": ["声音被数字化，案件仍未侦破", "二〇〇七年电影《那家伙的声音》", "二〇一九年旧录音数字化 · 截至二〇二六年无结论"],
}

SOURCES = [
    {
        "publisher": "Korea JoongAng Daily",
        "title": "Ransom calls, a runaround and a cold case: The kidnapping and murder of a 9-year-old boy",
        "url": "https://www.koreajoongangdaily.com/korea/ransom-calls-a-runaround-and-a-cold-case-the-kidnapping-and-murder-of-a-9-year-old-boy/12363163",
        "supports": "1991-01-29 disappearance in Apgujeong; first ransom demand and car-phone detail; changing instructions; investigation and 1991-03-13 discovery; still unsolved.",
    },
    {
        "publisher": "KBS News",
        "title": "李亨浩绑架杀害案录音数字化与案件复查报道",
        "url": "https://news.kbs.co.kr/news/view.do?ncd=4304846",
        "supports": "More than 60 ransom calls; the 2006 limitation period; renewed review of recordings and case files.",
    },
    {
        "publisher": "Donga Ilbo",
        "title": "警方委托分析李亨浩案绑匪录音",
        "url": "https://www.donga.com/news/article/all/20191016/97895463/1",
        "supports": "2019 voice analysis; analog tape digitization; offender remained unidentified.",
    },
    {
        "publisher": "Kookmin Ilbo",
        "title": "李亨浩失踪与发现经过及法医推断报道",
        "url": "https://www.kmib.co.kr/article/view.asp?arcid=0013825216",
        "supports": "1991-01-29 disappearance; 1991-03-13 discovery; 44-day inclusive count; autopsy inference was not a precisely established time of death.",
    },
    {
        "publisher": "Money Today",
        "title": "2026年李亨浩案回顾",
        "url": "https://www.mt.co.kr/society/2026/01/29/2026012815581698422",
        "supports": "Current 2026 case status and the reported 60-plus-call count; reports vary between 43/44 elapsed days, so narration uses dates and the conventional 44th-day phrasing.",
    },
]

PRESENTATION = {
    "card_header": "案件档案  /  韩国 · 一九九一",
    "card_footer": "公开报道摘要 · AI情景重现 · 并非原始档案影像",
    "disclosure_label": "AI动画情景重现 · 非新闻影像",
    "cards": CARD_COPY,
    "title_card": ["四十四天的电话", "李亨浩失踪案 · 首尔 · 一九九一"],
    "end_card": [
        "李亨浩案｜四十四天的电话",
        "截至二〇二六年仍未侦破 · 旧录音曾于二〇一九年数字化",
        "史料：KBS News · Korea JoongAng Daily · Donga Ilbo",
        "AI动画情景重现 · 非新闻影像",
    ],
    "caption_keywords": ["七千万韩元", "六十多通", "第四十四天", "追诉时效", "二〇〇六年", "二〇一九年", "未侦破"],
    "sfx_events": [
        ["S01", "phone"], ["S06", "phone"], ["S09", "phone"], ["S14", "phone"],
        ["S16", "machine"], ["S18", "paper"], ["S20", "machine"], ["S22", "paper"],
        ["S26", "paper"], ["S28", "paper"], ["S32", "machine"], ["S33", "paper"],
        ["S39", "machine"], ["S40", "machine"], ["S41", "paper"],
    ],
}

PRINCIPLES = [
    "本片是三分钟、1920×1080、16:9 的3D CGI情景重现；AI生成画面不是案件原始影像。",
    "所有视频镜头只由智谱 CogVideoX-Flash 生成；旁白使用独立的 Microsoft Edge TTS（zh-CN-YunyangNeural），不使用 GLM-TTS，也不调用 Agnes。",
    "李亨浩是儿童受害者：不还原真人面容、不呈现绑架或死亡过程，不展示遗体、血腥或可复制的犯罪方法。",
    "来电者身份不明：不猜测嫌疑人、不模拟其真实声音、不把推测写成定论；所有人物均为匿名化虚构情景演员。",
    "上传稿中的1.5亿韩元、57次电话、失踪第46天等与主要报道口径不符；本片按来源修正为首轮7000万韩元、60多通、3月13日发现（常见口径为第44天）。",
    "不使用上传稿中的未经证实引语、警力/嫌疑人数统计、具体死亡日定论或‘最后一通电话’说法；尸检推断以限定语表达。",
    "2006年只表述为追诉时效届满，不写媒体报道有差异的精确日期；2026年案件状态按近期回顾核对。",
    "所有片中文字、数字、字幕及信息卡由后期排版，不要求视频模型生成文字；片中常驻标注‘AI动画情景重现 · 非新闻影像’。",
    "每个动态镜头只用智谱 CogVideoX-Flash 生成；results.json 保存任务、请求哈希、源片 SHA-256；缺源片或校验不符即拒绝出片。",
]


def build() -> dict:
    chapter_counts = {"N01": 8, "N02": 7, "N03": 8, "N04": 7, "N05": 7, "N06": 8}
    shots = []
    chapter_index = {row["id"]: i for i, row in enumerate(CHAPTERS)}
    for i, (sid, narration_id, prompt, purpose, camera, graphic) in enumerate(SHOTS):
        character_ids = SHOT_CHARACTERS.get(sid, []) if not graphic else []
        continuity = " ".join(CHARACTERS[cid]["prompt"] for cid in character_ids)
        visual_prompt = "" if graphic else " ".join(part for part in (continuity, prompt, f"Camera: {camera}.") if part)
        if sid in SHOT_REFERENCE_OVERRIDES:
            reference_image = SHOT_REFERENCE_OVERRIDES[sid]
        elif len(character_ids) == 1:
            reference_image = CHARACTERS[character_ids[0]]["reference_image"]
        else:
            reference_image = ""
        row = {
            "id": sid,
            "kind": "graphic" if graphic else "cogvideo",
            "start": i * 4,
            "duration": 4,
            "narration_id": narration_id,
            "prompt": visual_prompt,
            "character_ids": character_ids,
            "face_visible": SHOT_FACE_VISIBLE.get(sid, False) if not graphic else False,
            "reference_image": reference_image,
            "purpose": purpose,
            "transition_out": "以缓慢运动转入下一镜",
            "graphic": graphic or "",
            "seed": 19910129 + i,
            "seconds": 6,
            "aspect": "16:9",
            "resolution": "1080p",
            "frame_rate": 30,
            "camera": camera,
        }
        shots.append(row)

    chapters = []
    offset = 0
    for chapter in CHAPTERS:
        count = chapter_counts[chapter["id"]]
        chapters.append({
            "id": chapter["id"],
            "title": chapter["title"],
            "start": offset * 4,
            "duration": count * 4,
            "text": chapter["text"],
        })
        offset += count

    story = {
        "title": "李亨浩案：四十四天的电话",
        "target_duration": 180,
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "model": MODEL,
        "branch": BRANCH,
        "style_prefix": STYLE_PREFIX,
        "negative_prompt": (
            "readable text, letters, numbers, Korean characters, logos, subtitles, watermarks, "
            "real-person likeness, identity drift, face morphing, merged identities, duplicated faces, "
            "inconsistent hair or wardrobe for a repeated character, blood, gore, corpse, injury, assault, "
            "weapon, perpetrator identification, extra limbs, malformed hands, flicker, jump cut, scene change, "
            "split screen, collage, anime, cartoon, plastic toy, vertical video"
        ),
        "characters": CHARACTERS,
        "principles": PRINCIPLES,
        "chapters": chapters,
        "shots": shots,
        "sources": SOURCES,
        "presentation": PRESENTATION,
        "_scaffold": {
            "note": "Adapted from the verified Zheng Dooyoung production workflow; all Lee Hyung-ho facts researched independently.",
            "timeline": "45 shots / 180 seconds; 38 CogVideoX-Flash clips + 7 post-production graphics; six narration chapters.",
            "voice": "Microsoft Edge TTS neural voice zh-CN-YunyangNeural; chapter audio kept in audio/ with SHA-256 checksums.",
        },
    }
    return story


def validate(story: dict) -> None:
    shots = story["shots"]
    assert len(shots) == 45
    assert [shot["id"] for shot in shots] == [f"S{i:02d}" for i in range(1, 46)]
    assert sum(s["kind"] == "cogvideo" for s in shots) == 38
    assert sum(s["kind"] == "graphic" for s in shots) == 7
    assert [c["id"] for c in story["chapters"]] == [f"N{i:02d}" for i in range(1, 7)]
    assert all(len(c["text"]) <= 1024 for c in story["chapters"])
    assert set(story["presentation"]["cards"]) == {"S03", "S10", "S17", "S24", "S30", "S37", "S45"}
    assert all("TODO" not in s["prompt"] for s in shots)
    assert all(len(story["style_prefix"] + s["prompt"]) <= 1000 for s in shots if s["kind"] == "cogvideo")
    for character in story["characters"].values():
        image = character.get("reference_image")
        if image:
            assert (HERE / image).is_file(), f"missing character reference: {image}"
    for shot in shots:
        if shot["kind"] != "cogvideo":
            continue
        assert set(shot["character_ids"]) <= set(story["characters"]), shot["id"]
        image = shot.get("reference_image")
        if image:
            assert (HERE / image).is_file(), f"{shot['id']}: missing shot reference {image}"
            expected_images = {story["characters"][cid].get("reference_image") for cid in shot["character_ids"]}
            expected_images.discard("")
            assert not expected_images or expected_images == {image}, f"{shot['id']}: identity reference does not match the cast bible"
        if shot["face_visible"] and shot["character_ids"]:
            assert image, f"{shot['id']}: face-visible recurring character requires the canonical reference"
        if len(shot["character_ids"]) > 1:
            assert image, f"{shot['id']}: multi-person shot needs a shared reference image"
    assert len(story["presentation"]["end_card"]) == 4


def main() -> None:
    story = build()
    validate(story)
    out = HERE / "story.json"
    out.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {out} | {len(story['shots'])} shots | {sum(len(c['text']) for c in story['chapters'])} narration characters")
    for chapter in story["chapters"]:
        print(f"{chapter['id']} {len(chapter['text'])} chars: {chapter['title']}")


if __name__ == "__main__":
    main()

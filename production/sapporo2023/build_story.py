#!/usr/bin/env python3
"""《札幌薄野酒店无头男尸案：二十九岁女子与精神科医生父亲的诡异共谋》—— 唯一内容源。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "札幌薄野酒店无头男尸案：二十九岁女子与精神科医生父亲的诡异共谋"
BRANCH = "arena/07b30353-desktop-tutorial"
FILM_NAME = "札幌薄野酒店无头男尸案_二十九岁女子与精神科医生父亲的诡异共谋_三分钟_带声音.mp4"

STYLE = (
    "【STYLE】日系冷峻悬疑纪录片质感电影动画，二零二三年七月日本北海道札幌薄野红灯区与雨夜住宅区，"
    "冷青灰与霓虹暗红明暗对立，浅景深镜头语言与克制推拉运镜，人物均为虚构演员式背影侧脸与局部剪影，"
    "不还原任何真实人物肖像，画面内无任何可读文字或招牌，连续运动，16:9，底部预留字幕安全区。"
)
NEGATIVE = (
    "【NEGATIVE】no readable text, no subtitles, no watermark, no gore, no blood, no corpse, "
    "no severed head, no nudity, no weapon closeup, no anime style, no deformed hands"
)

CHARACTERS = {
    "田村瑠奈": "二十九岁日本女性，深色连帽风衣或大衣，背影与低头侧脸剪影，拖着黑色拉杆箱，不露正脸",
    "田村修": "六十岁日本男性，深色西装与眼镜轮廓，医院或住宅暗影中的背影侧脸，不露正脸",
    "刑警": "四十岁日本男刑警，深灰风衣，冷峻侧脸剪影",
}

CHARACTER_SEEDS = {"田村瑠奈": 2601, "田村修": 2602, "刑警": 2603}
CHARACTER_REFERENCE_IDS = {"田村瑠奈": ["C01"], "田村修": ["C02"], "刑警": ["C03"]}

HIGHLIGHT_PHRASES = [
    "二零二三年七月",
    "札幌薄野",
    "浦仁志",
    "田村瑠奈",
    "田村修",
    "精神科医生",
    "田村浩子",
    "札幌高等法院",
]

HOOKS = [
    {"id": "H1", "start": 0.5, "end": 2.5, "text": "札幌酒店客房，发现一具失去头部的男尸"},
    {"id": "H2", "start": 24.0, "end": 26.0, "text": "凌晨两点，神秘女子拖着行李箱独自离开"},
    {"id": "H3", "start": 48.0, "end": 50.0, "text": "警方顺着监控追查，锁定一家三口"},
    {"id": "H4", "start": 72.0, "end": 74.0, "text": "父亲竟是当地知名的精神科医生"},
    {"id": "H5", "start": 96.0, "end": 98.0, "text": "父母不仅没报警，反而帮女儿隐瞒真相"},
    {"id": "H6", "start": 120.0, "end": 122.0, "text": "二零二六年二审宣判，父母双双获刑"},
    {"id": "H7", "start": 150.0, "end": 152.0, "text": "主犯二十九岁女儿至今仍在等待公审"},
    {"id": "H8", "start": 162.0, "end": 164.0, "text": "医生家庭的畸形顺从，最终毁掉底线"},
    {"id": "H9", "start": 170.0, "end": 172.0, "text": "薄野霓虹闪烁，却照不亮门后人性"},
]

EXPLAINERS = [
    {"id": "E1", "start": 12.0, "end": 16.0, "text": "2023年7月2日，日本北海道札幌市薄野地区"},
    {"id": "E2", "start": 84.0, "end": 88.0, "text": "嫌疑人田村瑠奈，其父田村修为精神科医生"},
    {"id": "E3", "start": 138.0, "end": 142.0, "text": "2026年1-2月，札幌高裁二审维持父母有罪认定"},
]

CHAPTERS = [
    ("第一章 薄野酒店的异常", 0, 30),
    ("第二章 凌晨离开的黑箱", 30, 60),
    ("第三章 医生家庭的秘密", 60, 90),
    ("第四章 畸形的顺从与共谋", 90, 120),
    ("第五章 二零二六年二审落槌", 120, 150),
    ("第六章 未完的公审", 150, 180),
]

ROWS = [
    (6, "二零二三年七月，日本北海道札幌最繁华的薄野红灯区，发生了一起轰动全国的酒店命案。",
     "二零二三年七月雨夜札幌薄野街头远景，霓虹灯在湿润沥青路面反射出冷青与暗红光影，行人撑伞。",
     ["S01"], [], "缓慢航拍推进街景", "雨夜城市远景风声", "冷青与暗红对比"),
    (6, "七月二日下午，酒店工作人员走进一间迟迟未退房的客房，眼前景象令人窒息。",
     "昏暗酒店走廊尽头，一扇半掩的房门透出微弱冷光，门外地毯阴影深沉。",
     ["S02"], [], "缓慢推近房门", "走廊空调低鸣", "极暗冷调"),
    (6, "六十二岁男子浦仁志倒在浴室内遇害，而房间里却找不到他随身携带的物品。",
     "酒店客房玄关空镜，地上散落一只黑色皮鞋边缘与微弱水渍反光，不出现任何遗体。",
     ["S02"], [], "浅景深缓慢平移", "水滴轻响", "冷灰压抑"),
    (6, "更令人毛骨悚然的是，监控显示前一天深夜，曾有一名陌生人陪他走进房间。",
     "酒店大堂暗角监控视角俯拍，一男一女模糊背影走进电梯门，画质冷峻。",
     ["S03"], ["田村瑠奈"], "俯拍定镜微推", "电梯提示音", "监控冷青调"),
    (6, "凌晨两点左右，那名女子独自走出酒店，手里拖着一只沉重的黑色拉杆箱。",
     "凌晨酒店后门小巷，穿深色风衣的女子背影拖着黑色拉杆箱快步走入夜色。",
     ["S01"], ["田村瑠奈"], "中景跟拍背影", "拉杆箱轮子滚动声", "极暗冷调"),
    (6, "警方调取沿途数百个监控探头，一路追踪，最终锁定了一处安静的独栋住宅。",
     "札幌郊区清晨住宅区外景，一栋两层独栋民宅在阴云下静默立着。",
     ["S04"], ["刑警"], "远景缓慢横摇", "清晨微风声", "冷灰蓝"),
    (6, "令人意想不到的是，这户人家表面体面，男主人田村修竟是当地一名精神科医生。",
     "医院或诊所走廊，穿深色西装戴眼镜的男性背影独自走过冷白灯光下。",
     ["S05"], ["田村修"], "中景跟拍背影", "医院走廊脚步声", "冷白高对比"),
    (6, "七月下旬，警方先后逮捕了二十九岁的女儿田村瑠奈，以及她的父母田村修与田村浩子。",
     "警车停在独栋住宅门前，警示灯在阴天墙面投下微弱红蓝反光。",
     ["S04"], ["刑警"], "远景定镜", "对讲机杂音", "冷硬纪实"),
    (6, "警方在住宅内搜出关键物证，并发现了一段记录案发后经过的家庭录像。",
     "昏暗书房桌面，一只老式黑色数码摄像机静静摆在冷光下，镜头反光。",
     ["S06"], [], "浅景深推进桌面", "电流微嗡", "强明暗对比"),
    (6, "调查显示，田村瑠奈早前在夜店与浦仁志相识，随后一同前往薄野酒店。",
     "夜店门外雨夜霓虹街景，模糊人影在门廊下停留。",
     ["S01"], ["田村瑠奈"], "缓慢平移街景", "远处低沉街声", "霓虹暗红"),
    (6, "两人因琐事产生激烈矛盾后，田村瑠奈怀恨在心，提前准备工具将对方约出。",
     "昏暗房间内，一只黑色大旅行包拉链半开，阴影笼罩桌面。",
     ["S06"], ["田村瑠奈"], "局部特写推进", "拉链轻响", "冷暗压抑"),
    (6, "案发后，她不仅没有逃亡外地，反而把关键物证直接带回了父母居住的家中。",
     "深夜住宅玄关门内，一只黑色拉杆箱被推进昏暗过道，门缓缓关上。",
     ["S04"], ["田村瑠奈"], "低角度定镜", "关门沉闷声", "极暗冷调"),
    (6, "更让日本社会震惊的，是身为精神科医生的父亲田村修接下来的反应。",
     "昏暗客厅内，田村修背影站在窗前低头沉默，窗外夜色深沉。",
     ["S06"], ["田村修"], "侧逆光定镜", "室内钟表滴答声", "冷灰压抑"),
    (6, "面对女儿的极端行为，他既没有选择报警，也没有阻止，反而开车接应女儿。",
     "雨夜高架桥下，一辆深色轿车车灯划破黑暗驶过。",
     ["S01"], ["田村修"], "远景跟拍车灯", "雨刷器摆动声", "冷青夜色"),
    (6, "他甚至在妻子田村浩子的要求下，拿起摄像机拍下了女儿在家中的异常举动。",
     "住宅走廊暗影里，一名男性侧影手持摄像机微弱亮光静立不动。",
     ["S06"], ["田村修"], "隔门框偷窥视角", "摄像机按键轻响", "强明暗对比"),
    (6, "庭审中，田村修辩称女儿长期情绪失控，自己害怕被责骂才一步步妥协顺从。",
     "日本法院庄严灰石建筑外景，阴天冷光下台阶空旷。",
     ["S07"], [], "远景仰拍推进", "城市风声", "冷灰庄重"),
    (6, "但检方指出，作为专业精神科医生，他明知后果却一再配合，早已越过伦理底线。",
     "法庭木质旁听席与栏杆空镜，冷白光线从高窗斜射而下。",
     ["S08"], ["刑警"], "缓慢平移栏杆", "木椅轻响", "冷硬纪实"),
    (6, "二零二五年三月与五月，札幌地方法院一审分别判处父母两人有期徒刑并予缓刑。",
     "法院门口几名记者背影在台阶前驻足，阴天微风吹动大衣。",
     ["S07"], [], "中景横摇", "快门轻响", "冷灰调"),
    (6, "父母双方随后提起上诉，主张自己并非共谋，只是在畸形家庭环境下被迫配合。",
     "审讯室或律师会见室玻璃隔断，冷白灯光照亮空荡桌面。",
     ["S08"], ["田村修"], "隔玻璃推进", "室内寂静风声", "冷青调"),
    (6, "二零二六年一月，札幌高等法院对父亲田村修作出二审宣判。",
     "札幌高等法院外景特写，冬季微雪飘落在大门石柱前。",
     ["S07"], [], "缓慢推近石阶", "冬日微风声", "冷白高对比"),
    (6, "高院认为，遗弃行为由女儿主导，但父亲持续拍摄的行为客观上助长了犯意。",
     "昏暗房间内，一台摄像机屏幕微光熄灭，镜头缓缓拉远。",
     ["S06"], [], "缓慢拉远", "低频环境沉音", "极暗冷调"),
    (6, "最终，法院撤消一审部分认定，改判田村修有期徒刑一年、缓刑三年。",
     "法院走廊长镜头，深色西装男性背影独自走过空荡长廊。",
     ["S08"], ["田村修"], "长跟拍背影", "走廊脚步声", "冷灰压抑"),
    (6, "同年二月，札幌高等法院对母亲田村浩子二审宣判，同样认定损坏帮助罪名成立。",
     "法院大门外，一名穿深色外套的年长女性低头走下石阶的背影。",
     ["S07"], ["田村修"], "远景侧拍", "街头风声", "冷灰调"),
    (6, "至此，这对父母虽然都留下了有罪判决，却因缓刑而暂时无需入狱服刑。",
     "独栋住宅外景在黄昏冷光中静默立着，窗帘紧闭。",
     ["S04"], [], "缓慢拉远", "黄昏风声", "冷暖交界"),
    (6, "而本案真正的核心——二十九岁的女儿田村瑠奈，至今仍未迎来最终宣判。",
     "拘留所高墙与铁丝网剪影，阴云在天空缓慢移动。",
     ["S09"], ["田村瑠奈"], "仰拍定镜", "风声渐强", "冷青压抑"),
    (6, "由于法院多次对她进行精神鉴定以确认刑事责任能力，公审程序一再延后。",
     "医院鉴定室门外走廊，一盏冷白指示灯静静亮着。",
     ["S05"], [], "缓慢推进门灯", "日光灯微嗡", "冷白调"),
    (6, "一个本该救死扶伤的医生家庭，却在畸形的溺爱与顺从中一起坠入深渊。",
     "曾经整洁的独栋住宅玄关如今空荡昏暗，灰尘在微光中浮动。",
     ["S04"], [], "缓慢平移空镜", "室内死寂", "冷灰绝望"),
    (6, "薄野的霓虹每晚依旧闪烁，却再也照不亮那扇门后扭曲的人性。",
     "札幌薄野街头夜色航拍拉远，霓虹灯火逐渐融入寒冷夜空。",
     ["S01"], [], "缓慢升格拉远", "城市夜风声", "冷青暗红"),
    (6, "当亲情失去边界、专业变成纵容，最终毁掉的，往往是整个家庭的底线。",
     "法院石阶在晨光中静默立着，镜头缓慢拉远。",
     ["S07"], [], "缓慢拉远", "环境音渐息", "冷暖交替"),
    (6, "如果是你，面对至亲犯下不可挽回的大错，你会选择报警还是隐瞒到底？",
     "深色房门渐暗入黑，片尾留白等待字幕落版。",
     ["S02"], [], "缓慢推暗渐黑", "关门轻响", "极简暗调"),
]

assert len(ROWS) == 30, f"Expected 30 shots, got {len(ROWS)}"
assert sum(r[0] for r in ROWS) == 180, f"Expected 180s total, got {sum(r[0] for r in ROWS)}"


def build() -> dict:
    revision_path = HERE / "reference" / "revision.txt"
    revision = revision_path.read_text(encoding="utf-8").strip() if revision_path.exists() else ""
    approvals_path = HERE / "reference" / "approvals.json"
    approvals_raw = json.loads(approvals_path.read_text(encoding="utf-8")) if approvals_path.exists() else {}
    approvals = approvals_raw.get("assets", {}) if isinstance(approvals_raw, dict) else {}

    ref_images = []
    for key, meta in sorted(approvals.items()):
        if isinstance(meta, dict) and meta.get("status") == "approved":
            ref_images.append({
                "id": key,
                "file": meta["file"],
                "sha256": meta["sha256"],
                "status": "approved",
                "dimensions": meta.get("dimensions"),
                "note": meta.get("note", ""),
            })

    shots = []
    cursor = 0
    for idx, row in enumerate(ROWS, start=1):
        duration, narration, visual, refs, roles, camera, sound, grade = row
        sid = f"S{idx:02d}"
        role_anchors = "；".join(f"{r}：{CHARACTERS[r]}" for r in roles if r in CHARACTERS)
        prompt = f"{STYLE} 唯一场景：{visual} 运镜：{camera}。影调：{grade}。"
        if role_anchors:
            prompt += f" 人物锚点：{role_anchors}。"
        prompt += f" {NEGATIVE}"

        shots.append({
            "id": sid,
            "narration_id": sid,
            "kind": "agnes",
            "start": cursor,
            "duration": duration,
            "seconds": duration,
            "aspect": "16:9",
            "source_size": "720P",
            "seed": 2600 + idx,
            "narration": narration,
            "visual": visual,
            "camera": camera,
            "sound_design": sound,
            "grade": grade,
            "reference_ids": "+".join(refs),
            "roles": roles,
            "prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        })
        cursor += duration

    chapters = []
    for shot in shots:
        ch_title = next(t for t, st, en in CHAPTERS if st <= shot["start"] < en)
        chapters.append({
            "id": shot["id"],
            "title": ch_title,
            "start": shot["start"],
            "duration": shot["duration"],
            "text": shot["narration"],
        })

    voice_path = HERE / "audio" / "voice.json"
    voice = json.loads(voice_path.read_text(encoding="utf-8")) if voice_path.exists() else {}
    voice_id = voice.get("voice_id") or "pending_voice_selection"

    presentation = {
        "onscreen_label": "AI动画情景重现 · 非真实影像",
        "highlight_phrases": HIGHLIGHT_PHRASES,
        "hooks": HOOKS,
        "explainers": EXPLAINERS,
        "end_title": "札幌薄野酒店无头男尸案",
        "end_subtitle": "2023 – 2026 · 畸形的顺从与共谋",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "医生父亲竟帮女儿藏头",
        "cover_concept": "封面只用本片已生成视频截图；禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "札幌薄野酒店无头男尸案：二十九岁女子与精神科医生父亲的诡异共谋",
        "hashtags": ["#札幌无头男尸案", "#日本真实案件", "#田村瑠奈", "#案件解说", "#悬疑"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），单排56号大字一个逗号出一句；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已通过2025-2026年日本经济新闻、信浓毎日新闻公开报道核实；主犯田村瑠奈仍在公审程序中，见 FACT_CHECK.md",
        "as_of": "2026-11-22",
        "legal_note": "2026年1-2月札幌高等法院二审分别认定田村修、田村浩子有罪并予缓刑；田村瑠奈仍在公审中。",
        "sources": [
            {"publisher": "日本经济新闻", "date": "2026-01-27", "url": "https://www.nikkei.com/article/DGXZQOUD27C6U0X20C26A1000000/", "supports": "田村修二审改判有期徒刑1年、缓刑3年"},
        ],
        "editorial_cautions": [
            "严禁具象化呈现砍头、刀具、血腥或遗体画面",
            "主犯田村瑠奈仍在公审程序中，不做超前定罪表述",
        ],
    }

    project = {
        "title": TITLE,
        "film_name": FILM_NAME,
        "target_duration": 180, "width": 1920, "height": 1080, "fps": 24,
        "model": "agnes-video-2.5-flash", "source_size": "720P", "branch": BRANCH,
        "style_prefix": STYLE, "negative_prompt": NEGATIVE, "style_rumor_prefix": STYLE,
        "characters": CHARACTERS, "character_seeds": CHARACTER_SEEDS,
        "character_reference_ids": CHARACTER_REFERENCE_IDS,
        "narration_spec": {
            "voice_id": voice_id,
            "description": voice.get("description", "悬疑纪录片向低沉普通话男声，克制压抑"),
            "language": "zh-CN", "target_characters_per_second": 4.2,
            "alignment": "一镜一句，一镜一条TTS与一条字幕；只在确有必要时加速，不慢放",
        },
        "chapters": chapters, "shots": shots,
        "reference_images": ref_images,
        "reference_revision": revision,
        "reference_designs": {
            "characters": ["C01", "C02", "C03"],
            "scenes": ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09"],
            "props": [],
        },
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期高质量放大到1080P。",
            "全片无BGM；旁白与单排大字字幕逐句锁定，音效/环境声只做轻量辅助，不盖住解说。",
        ],
    }
    (HERE / "story.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [
        f"# {TITLE}", "",
        "抖音横屏｜1920×1080｜16:9｜24fps｜180秒｜30个Agnes Video 2.5 Flash动画片段｜无BGM。",
        "", "| 镜头 / 时间 | 旁白 | 画面与运镜 | 参考图 | 音效/环境声备注 |", "|---|---|---|---|---|",
    ]
    for shot, row in zip(shots, ROWS):
        _, narration, visual, refs, roles, camera, sound, grade = row
        end = shot["start"] + shot["duration"]
        ts = lambda sec: f"{int(sec) // 60:02d}:{int(sec) % 60:02d}"
        rows.append(f"| {shot['id']} / {ts(shot['start'])}–{ts(end)} | {narration} | {visual}（{camera}；{grade}） | {refs} + {','.join(roles) or '无角色'} | {sound} |")
    screenplay = "\n".join(rows) + "\n"
    (HERE / "screenplay.md").write_text(screenplay, encoding="utf-8")
    (HERE / "抖音脚本.md").write_text(screenplay, encoding="utf-8")

    publish = "\n".join([
        f"# {presentation['publish_title']}", "",
        "## 抖音标题", "", presentation["publish_title"], "",
        "## 简短介绍", "",
        "二零二三年七月，日本札幌薄野一家酒店客房内发现一具失去头部的男尸。警方追踪监控后，逮捕了二十九岁女子田村瑠奈，以及她的精神科医生父亲田村修、母亲田村浩子。",
        "",
        "二零二六年一月至二月，札幌高等法院二审分别认定父母二人有罪并予缓刑，而主犯田村瑠奈的公审程序仍在进行中。",
        "",
        "AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md。",
        "", "## 提问读者一句话", "",
        "如果是你，面对至亲犯下不可挽回的大错，你会选择报警还是隐瞒到底？",
        "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

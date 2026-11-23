#!/usr/bin/env python3
"""《韩国最年轻死刑犯：从大学社长到死囚，只因一句分手》—— 唯一内容源。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "韩国最年轻死刑犯：从大学社长到死囚，只因一句分手"
BRANCH = "arena/f9f847e0-desktop-tutorial"
FILM_NAME = "韩国最年轻死刑犯_从大学社长到死囚，只因一句分手_三分钟_带声音.mp4"

STYLE = (
    "【STYLE】韩式写实悬疑纪录片质感电影动画，二零一四年春季韩国大邱大学校园与公寓楼道，"
    "冷青灰与室内暗暖钨丝灯明暗对立，浅景深镜头语言与克制推拉运镜，人物均为虚构演员式背影侧脸与局部剪影，"
    "不还原任何真实人物肖像，画面内无任何可读文字或招牌，连续运动，16:9，底部预留字幕安全区。"
)
NEGATIVE = (
    "【NEGATIVE】no readable text, no subtitles, no watermark, no gore, no blood, no corpse, "
    "no weapon violence depiction, no anime style, no bright idyllic scenery, no deformed hands"
)

CHARACTERS = {
    "张载振": "二十五岁韩国男大学生，深色连帽外套或深蓝维修工服，背影或暗影侧脸，不露正脸",
    "权某": "二十多岁韩国女大学生，浅灰针织外套，背影或四分之三侧脸，不露正脸",
    "刑警": "四十岁韩国男刑警，深灰夹克，目光锐利，侧脸与手部细节",
}

CHARACTER_SEEDS = {"张载振": 2401, "权某": 2402, "刑警": 2403}

CHARACTER_REFERENCE_IDS = {
    "张载振": ["C01"],
    "权某": ["C02"],
    "刑警": ["C03"],
}

HIGHLIGHT_PHRASES = [
    "二零一四年五月",
    "大邱",
    "大学社长",
    "张载振",
    "权某",
    "修理工",
    "分手",
    "死刑",
    "最年轻的死刑犯",
]

HOOKS = [
    {"id": "H1", "start": 0.5, "end": 2.5, "text": "前途光明的大学社长，成了韩国最年轻死刑犯"},
    {"id": "H2", "start": 24.0, "end": 26.0, "text": "一句分手，彻底撕下了他的伪装"},
    {"id": "H3", "start": 48.0, "end": 50.0, "text": "他提着工具箱，冒充修理工敲开了门"},
    {"id": "H4", "start": 72.0, "end": 74.0, "text": "他没有离开，而是留在屋里等她回家"},
    {"id": "H5", "start": 96.0, "end": 98.0, "text": "权某拼命逃出求救，惊动了整栋公寓"},
    {"id": "H6", "start": 114.0, "end": 116.0, "text": "警方火速封锁现场，将张载振抓获"},
    {"id": "H7", "start": 132.0, "end": 134.0, "text": "法庭上，他竟然还想用精神问题脱罪"},
    {"id": "H8", "start": 150.0, "end": 152.0, "text": "大法院终审：判处死刑"},
    {"id": "H9", "start": 168.0, "end": 170.0, "text": "二十五岁，从大学社长到死囚牢房"},
]

EXPLAINERS = [
    {"id": "E1", "start": 12.0, "end": 16.0, "text": "2014年5月，韩国大邱广域市达西区"},
    {"id": "E2", "start": 102.0, "end": 106.0, "text": "受害者为权某父母，权某侥幸逃生报警"},
    {"id": "E3", "start": 156.0, "end": 160.0, "text": "2015年韩国大法院终审维持死刑判决"},
]

CHAPTERS = [
    ("第一章 校园里的优等生", 0, 30),
    ("第二章 失控的分手", 30, 60),
    ("第三章 冒充修理工", 60, 90),
    ("第四章 惊魂逃生夜", 90, 120),
    ("第五章 终审死刑", 120, 150),
    ("第六章 铁窗余生", 150, 180),
]

ROWS = [
    (6, "二零一四年五月，韩国大邱一名二十五岁大学生，站上了终审死刑的被告席。",
     "韩国大邱地方法院庄严的灰石立柱与阴天冷光，一道年轻男性背影站在庭外阴影里。",
     ["S01"], ["张载振"], "缓慢推近背影", "法院走廊低沉环境风声", "冷青灰强明暗对比"),
    (6, "他叫张载振，曾经是大学里风光无限的社团社长，也是同学们眼中的优等生。",
     "韩国大学校园林荫道与教学楼远景，春季阴天冷光，学生背影零星走过。",
     ["S02"], ["张载振"], "缓慢横摇校园", "校园远景风声", "冷暖交界"),
    (6, "在学校里，他认识了性格温和的女生权某，两人很快发展成恋人关系。",
     "大学图书馆走廊窗边，一男一女两名大学生背影并肩走过。",
     ["S02"], ["张载振", "权某"], "浅景深侧跟拍", "走廊轻微脚步声", "暗暖转冷"),
    (6, "可相处久了，权某发现张载振控制欲极强，稍有不顺就会情绪失控。",
     "昏暗咖啡馆角落桌面，两只水杯隔着阴影相对，气氛凝滞。",
     ["S03"], [], "浅景深推进水杯", "室内低沉环境音", "冷灰蓝"),
    (6, "权某鼓起勇气提出分手，她的父母也坚决反对女儿继续和张载振来往。",
     "公寓楼下傍晚路灯亮起，女生背影快步走进单元门禁。",
     ["S04"], ["权某"], "缓慢跟拍背影", "单元门禁滴声与关门声", "冷暗压抑"),
    (6, "谁也没想到，这一句再正常不过的分手，竟点燃了张载振心底的杀机。",
     "昏暗出租屋窗边，男性背影站在阴影里盯着窗外夜色，空气凝固。",
     ["S05"], ["张载振"], "侧逆光推进", "低频环境沉音", "极暗冷调"),
    (6, "他开始疯狂跟踪权某，甚至摸清了她父母每天出门和下班的精确时间。",
     "大邱居民区傍晚街道，路灯下行人稀疏，一道深色连帽衫背影停在街角。",
     ["S04"], ["张载振"], "远景长焦定镜", "街道远景车流声", "冷青调"),
    (6, "几天后，张载振穿上一身深蓝色工服，拎着一只沉甸甸的黑色工具箱。",
     "公寓楼道电梯口，一名穿深蓝工服的男性拎着工具箱背影走入电梯。",
     ["S06"], ["张载振"], "缓慢跟拍背影", "电梯门关闭金属声", "冷硬纪实"),
    (6, "他冒充成上门检修管道的修理工，平静地敲响了权某父母家的防盗门。",
     "公寓七楼走廊，深色防盗门前一只戴着白手套的手抬起敲门。",
     ["S06"], ["张载振"], "局部特写推进", "沉闷敲门声", "强明暗对比"),
    (6, "毫不知情的权某父母打开了门，把这名曾经的准女婿迎进了客厅。",
     "防盗门缓缓打开一条缝，室内暖黄灯光透出，与走廊冷光形成强烈对立。",
     ["S06"], [], "门外向门内推进", "门轴开启声", "冷暖强烈对立"),
    (6, "进屋之后，张载振撕下伪装，在客厅里残忍杀害了手无寸铁的权某父母。",
     "空旷昏暗客厅地面光影与翻倒的木椅局部特写，不出现任何血迹与遗体画面。",
     ["S07"], [], "缓慢仰摇过桌面", "低频沉重闷响", "极暗冷调"),
    (6, "更令人毛骨悚然的是，作案后他没有逃跑，而是冷静地把房间清理了一遍。",
     "厨房水池边水龙头滴水特写，室内一片死寂，灯光昏暗。",
     ["S07"], [], "浅景深微距", "水滴声回荡", "冷灰压抑"),
    (6, "他反锁好防盗门，独自坐在黑暗的客厅里，安静地等待权某下班回家。",
     "漆黑客厅沙发剪影，一道男性背影坐在暗影里面向玄关方向。",
     ["S07"], ["张载振"], "广角缓慢拉远", "室内钟表走动声", "极暗剪影"),
    (6, "深夜时分，权某像往常一样用钥匙打开家门，迎面却撞上了黑暗中的他。",
     "玄关门锁转动，门缝透进走廊冷光，女生背影刚踏进门厅突然僵住。",
     ["S06"], ["权某"], "门内向外反打", "钥匙转动声", "高对比剪影"),
    (6, "面对早已失去理智的张载振，权某在生死关头拼尽全力挣脱控制。",
     "走廊楼梯间扶手与急促晃动的灯光，脚步声在楼道里回响。",
     ["S06"], ["权某"], "希区柯克式微变焦", "急促脚步声", "强明暗对比"),
    (6, "她一路狂奔冲出单元门大声呼救，惊醒了整栋公寓的邻居并立刻报警。",
     "深夜公寓楼外景，几扇窗户灯光骤然亮起，远处警灯红蓝微光闪烁。",
     ["S04"], [], "缓慢拉远外景", "远处警笛声渐近", "冷蓝红蓝光"),
    (6, "韩国警方火速赶到现场封锁楼道，很快将还没来得及逃远的张载振抓获。",
     "公寓楼下警车停靠，刑警背影快步走进单元门。",
     ["S04"], ["刑警"], "中景跟拍背影", "警车无线电杂音", "冷硬纪实"),
    (6, "消息传回大学校园，所有认识张载振的老师和同学都觉得难以置信。",
     "大学社团活动室空镜，桌椅整齐摆放，窗户透进阴天冷光。",
     ["S02"], [], "缓慢横摇空室", "室内死寂环境音", "冷灰蓝"),
    (6, "那个平时看起来彬彬有礼的大学社长，背地里竟然藏着如此极端的偏执。",
     "审讯室玻璃外，刑警盯着桌面上黑色工具箱物证袋的侧脸。",
     ["S08"], ["刑警"], "隔玻璃缓慢推进", "日光灯微嗡", "冷青调"),
    (6, "面对铁证，张载振在法庭上竟然试图用饮酒和精神恍惚来替自己脱罪。",
     "审讯室暗影里男性低头垂肩的剪影，窗外夜色深沉。",
     ["S08"], ["张载振"], "缓慢拉远", "低沉环境风声", "冷灰绝望"),
    (6, "但检方调取了他提前购买工具、伪装修理工的监控，彻底戳穿了他的谎言。",
     "警局物证桌面，黑色工具箱与工服叠放在冷白聚光灯下。",
     ["S08"], [], "俯拍推进", "低频沉重余音", "强明暗对比"),
    (6, "一审法庭认为他犯罪手段极其残忍、毫无悔意，直接判处张载振死刑。",
     "空旷法庭木质席位与庄严法槌特写，冷白顶灯照亮桌面。",
     ["S01"], [], "特写推进法槌", "法槌清脆一响", "高对比"),
    (6, "张载振不服判决提起上诉，然而二审法院毫不犹豫地驳回上诉维持原判。",
     "高等法院高大石柱外景，阴天冷光下石阶冷峻。",
     ["S01"], [], "仰拍缓慢推进", "城市风声", "冷灰庄重"),
    (6, "二零一五年，韩国大法院终审维持死刑判决，张载振彻底失去了翻盘机会。",
     "韩国大法院外景全景，冬日冷光下建筑肃穆。",
     ["S09"], [], "广角缓慢推进", "法槌定音", "冷灰调"),
    (6, "当时年仅二十五岁的他，就此成为韩国最年轻的死刑犯。",
     "看守所高墙铁丝网远景，灰暗天空下铁门紧闭。",
     ["S09"], [], "缓慢仰摇铁网", "寒风呼啸声", "冷灰绝望"),
    (6, "由于韩国自一九九七年底后再未实际执行过死刑，他至今仍被关在死囚牢房。",
     "昏暗走廊尽头一扇厚重铁门特写，门上小窗透出一丝冷光。",
     ["S09"], [], "特写推近铁门", "沉重铁门锁声", "极暗冷调"),
    (6, "一次失控的分手，毁掉了一个原本幸福的家庭，也葬送了他自己的人生。",
     "春季大学校园空镜，风吹过空荡的操场与长椅。",
     ["S02"], [], "缓慢升格拉远", "微弱风声", "冷暖交替"),
    (6, "真正的爱从来不是占有，当一个人把分手当成背叛，悲剧就已经注定。",
     "大邱公寓楼外景黎明微光，天际泛起一丝冷白亮色。",
     ["S04"], [], "缓慢拉远", "清晨微风声", "冷暖交界"),
    (6, "从受人尊敬的大学社长到终身囚禁的死刑犯，中间隔着的只是一念之差。",
     "法院石阶在晨光中逐渐拉远，空镜静默。",
     ["S01"], [], "缓慢升格拉远", "环境风声渐弱", "极简冷调"),
    (6, "面对这种极端的控制欲，你觉得身边人最早应该从哪些细节开始警惕？",
     "深色走廊尽头铁门渐暗入黑，片尾留白等待字幕落版。",
     ["S09"], [], "缓慢推暗渐黑", "铁门灯光熄灭轻响", "极简暗调"),
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
            "seed": 2400 + idx,
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
        "end_title": "张载振案",
        "end_subtitle": "2014 · 韩国大邱 · 从大学社长到死囚",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "从大学社长到死囚",
        "cover_concept": "封面只用本片已生成视频截图；禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "韩国最年轻死刑犯张载振：从大学社长到死囚，只因一句分手",
        "hashtags": ["#张载振案", "#韩国真实案件", "#韩国最年轻死刑犯", "#案件解说", "#悬疑"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），单排56号大字逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已通过公开资料核实核心时间线与2015年大法院终生死刑判决；不具象化呈现暴力细节，见 FACT_CHECK.md",
        "as_of": "2026-11-22",
        "legal_note": "一审、二审及2015年韩国大法院终审均判处张载振死刑。",
        "sources": [
            {"publisher": "Korea JoongAng Daily", "date": "2014–2015", "url": "https://www.koreajoongangdaily.com/korea/7-more-korean-true-crime-cases-that-will-live-rent-free-in-your-head/12200621", "supports": "案发经过与最年轻死刑犯判决"},
        ],
        "editorial_cautions": [
            "受害者统一使用权某、权某父母，不使用真实全名与肖像",
            "严禁具象化呈现刺杀、血迹或遗体画面",
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
        "二零一四年五月，韩国大邱一名二十五岁大学生张载振，曾是大学社团社长、同学们眼中的优等生。因女友权某及家人提出分手，他竟然冒充管道修理工进入权某家中行凶，并留在屋内等待权某回家。",
        "",
        "权某拼死逃出报警，张载振最终被一审、二审及韩国大法院终审判处死刑，成为韩国最年轻的死刑犯。",
        "",
        "AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md。",
        "", "## 提问读者一句话", "",
        "面对这种极端的控制欲，你觉得身边人最早应该从哪些细节开始警惕？",
        "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

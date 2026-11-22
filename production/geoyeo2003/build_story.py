#!/usr/bin/env python3
"""《巨余洞密室案：门从里面反锁，钥匙却在窗缝的包里》—— 唯一内容源：解说词、30 镜分镜、参考图、钩子/注释、发布文案。

用法::

    python3 production/geoyeo2003/build_story.py            # 写 story.json + screenplay.md + 抖音脚本.md + 抖音发布文案.md
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "巨余洞密室案：门从里面反锁，钥匙却在窗缝的包里"
BRANCH = "arena/f9f847e0-desktop-tutorial"
FILM_NAME = "巨余洞密室案_门从里面反锁，钥匙却在窗缝的包里_三分钟_带声音.mp4"

STYLE = (
    "韩式写实悬疑纪录片质感电影动画，二零零三年冬季韩国首尔公寓内景与走廊，冷青灰与室内暗暖钨丝灯明暗对立，"
    "浅景深镜头语言与克制推拉运镜，人物均为虚构演员式背影侧脸与局部剪影，不还原任何真实人物肖像，"
    "画面内无任何可读文字或招牌，连续运动，16:9，底部预留字幕安全区。"
)
NEGATIVE = (
    "no readable text, no subtitles, no watermark, no gore, no blood, no corpse, "
    "no child harm depiction, no anime style, no bright idyllic scenery, no deformed hands"
)

CHARACTERS = {
    "丈夫": "三十多岁韩国男性，深色冬装外套，疲惫背影或侧脸，不露正脸",
    "女同学": "三十一岁韩国女性，深色长羽绒服，低头掩饰右手，侧脸或背影剪影",
    "刑警": "四十岁韩国男刑警，深灰夹克，目光锐利，侧脸与手部细节",
}

CHARACTER_SEEDS = {"丈夫": 2201, "女同学": 2202, "刑警": 2203}

CHARACTER_REFERENCE_IDS = {
    "丈夫": ["C01"],
    "女同学": ["C02"],
    "刑警": ["C03"],
}

HIGHLIGHT_PHRASES = [
    "二零零三年十二月二十九日",
    "巨余洞",
    "七楼",
    "密室",
    "钥匙",
    "窗缝",
    "小纸片",
    "绳索勒痕",
    "切开的塑料瓶",
    "无期徒刑",
]

HOOKS = [
    {"id": "H1", "start": 0.5, "end": 2.5, "text": "门从里面反锁，钥匙却在窗缝的包里"},
    {"id": "H2", "start": 48.0, "end": 50.0, "text": "七楼密室，为什么没有遗书？"},
    {"id": "H3", "start": 102.0, "end": 104.0, "text": "她一直藏着自己的右手"},
    {"id": "H4", "start": 168.0, "end": 170.0, "text": "最可怕的不是密室，是熟人"},
]

EXPLAINERS = [
    {"id": "E1", "start": 12.0, "end": 16.0, "text": "首尔市松坡区巨余洞某公寓七楼"},
    {"id": "E2", "start": 66.0, "end": 70.0, "text": "现场无遗书，死者生前亦无抑郁症病史"},
    {"id": "E3", "start": 144.0, "end": 148.0, "text": "韩国大法院终审维持无期徒刑判决"},
]

CHAPTERS = [
    ("第一章 门外的寒夜", 0, 30),
    ("第二章 窗缝里的钥匙", 30, 60),
    ("第三章 矛盾的密室", 60, 90),
    ("第四章 藏起来的右手", 90, 120),
    ("第五章 塑料瓶与真相", 120, 150),
    ("第六章 终审与余音", 150, 180),
]

# 每条 ROWS: (duration, narration, visual, refs, roles, camera, sound, grade)
ROWS = [
    (6, "二零零三年十二月二十九日傍晚，首尔七楼一扇防盗门从里面反锁。",
     "冬夜首尔旧式公寓走廊，冷白顶灯下紧闭的深色防盗门与门锁特写，空气凝滞。",
     ["S01"], ["丈夫"], "缓慢推近门锁", "冬季走廊风声与门锁金属声", "冷青灰强明暗对比"),
    (6, "丈夫金某下班回家敲了很久的门，屋里却连一点脚步声都没有。",
     "丈夫背影站在门前抬手敲门，走廊感应灯微弱闪烁，门缝下完全漆黑。",
     ["S01"], ["丈夫"], "中景跟拍背影", "沉闷敲门声回荡", "冷色调低照度"),
    (6, "明明妻子平时都在家带两个年幼的孩子，今天却反常地毫无回应。",
     "客厅空镜门厅玄关，儿童小鞋整齐摆在鞋柜旁，灯光未开一片冷清。",
     ["S02"], [], "浅景深缓慢横摇", "室内死寂环境音", "冷灰蓝欠曝"),
    (6, "无奈之下，金某打电话叫来了常来家里走动的妻子高中同学李某。",
     "走廊角落丈夫低头拨通电话的侧影，走廊尽头电梯门缓缓打开。",
     ["S01"], ["丈夫"], "侧逆光中景", "电话拨号等待音", "冷暖交界"),
    (6, "很快李某赶到门外，一边安慰金某，一边在走廊里来回张望。",
     "穿深色长羽绒服的女同学走进走廊，脚步停在门前，视线扫向走廊侧窗。",
     ["S01"], ["丈夫", "女同学"], "缓慢跟拍", "冬季羽绒服摩擦与脚步声", "冷灰压抑"),
    (6, "就在这时，李某突然注意到走廊一侧的小窗并没有完全锁死。",
     "走廊墙面窄小窗户特写，窗框留着一条刚好能伸进手臂的缝隙。",
     ["S03"], ["女同学"], "局部特写推进", "金属窗框轻响", "强明暗对比"),
    (6, "她顺着窗缝伸手进去摸索，竟然直接掏出了妻子的随身手提包。",
     "一只戴着袖口的手从窗缝探入暗处，摸出深色女式手提包的局部镜头。",
     ["S03"], ["女同学"], "浅景深手部特写", "布料摩擦与拉链声", "暗部高反差"),
    (6, "打开手提包，门锁钥匙果然就安静地躺在里面，让人松了口气。",
     "手提包拉链拉开，一串金属门钥匙在走廊微光下反光。",
     ["S03"], ["女同学"], "俯拍微距", "钥匙清脆碰撞声", "冷金属反光"),
    (6, "可当房门终于被拧开的那一刻，门外两人的呼吸瞬间凝固了。",
     "钥匙插进锁孔转动，防盗门缓缓推开一条缝，室内冷暗空气涌出。",
     ["S01"], ["丈夫", "女同学"], "门内向外反打推进", "门轴沉重开启声", "高对比剪影"),
    (6, "三十一岁的妻子朴某倒在卧室门边，三岁儿子和十个月女儿也已遇难。",
     "空旷昏暗的卧室门口地面光影与紧闭的衣柜门，不出现任何遗体画面。",
     ["S04"], [], "缓慢仰摇过门框", "低频环境沉音", "极暗冷调"),
    (6, "警方第一时间封锁七楼现场，却发现所有门窗和防盗栏都完好无损。",
     "公寓七楼窗台与完好无损的金属防盗栏特写，窗外是首尔冬夜楼群。",
     ["S05"], [], "窗内向窗外推镜", "远景城市风声", "冷蓝夜色"),
    (6, "外部攀爬几乎不可能，厨房里甚至还留着准备做晚饭的新鲜食材。",
     "厨房料理台特写，切到一半的蔬菜与未开火的锅具静静摆在台面。",
     ["S06"], [], "浅景深平移", "厨房水龙头滴水声", "暗暖转冷"),
    (6, "表面上看，这像是一起母亲带着孩子轻生的密室悲剧，几乎无懈可击。",
     "空荡客厅拉远镜头，窗帘半掩，整套公寓如同一座封闭的盒子。",
     ["S02"], [], "广角缓慢拉远", "低沉环境风声", "冷灰调"),
    (6, "但负责现场的刑警越看越不对劲，因为屋里根本找不到任何遗书。",
     "刑警蹲在书桌旁戴手套翻看桌面纸张的背影与手部细节，桌面干干净净。",
     ["S04"], ["刑警"], "侧景深推进", "纸张翻动轻响", "冷硬纪实"),
    (6, "而且朴某性格开朗，生前没有任何抑郁症或轻生倾向，线索断了。",
     "阳台边一盆照顾得很好的绿植在微风里轻轻晃动，与冷清房间形成反差。",
     ["S05"], [], "浅景深定镜微动", "窗外细微风声", "冷暖对比"),
    (6, "更反常的是，法医在朴某紧握的手心里，发现了一张来源不明的小纸片。",
     "物证袋特写，里面装着一小片带着胶带痕迹的白色碎纸片。",
     ["S07"], ["刑警"], "微距推近", "物证袋塑料轻响", "强光聚点"),
    (6, "两个年幼的孩子身上也留有异常压迫伤痕，绝不是轻生该有的样子。",
     "刑警站在昏暗走廊里低头看记录本的侧脸，眉头紧锁，眼神锐利。",
     ["S04"], ["刑警"], "特写推近侧脸", "笔尖划过纸面声", "高对比冷调"),
    (6, "警方立刻推翻自杀判断，把侦查方向锁定在熟人作案的密室谋杀上。",
     "警局夜间办公室玻璃反光，刑警在白板前移动线索卡片的剪影。",
     ["S08"], ["刑警"], "隔玻璃缓慢横摇", "室内日光灯微嗡", "冷青调"),
    (6, "所有近期进出过这间公寓的熟人被逐一传唤，高中同学李某也在其中。",
     "审讯室走廊长镜头，女同学低着头走进门内的背影。",
     ["S08"], ["女同学"], "长跟拍背影", "走廊皮鞋脚步声", "冷暗压抑"),
    (6, "坐在刑警面前时，李某神情镇定，却总是不自觉地把右手藏在袖口里。",
     "审讯桌一角，女同学双手放在桌下，右手被深色衣袖遮住一半。",
     ["S08"], ["女同学", "刑警"], "浅景深局部特写", "衣料摩擦声", "明暗对比"),
    (6, "经验老到的刑警一眼盯住了她手背上那道像被细绳勒出来的伤痕。",
     "刑警目光锐利地看向桌面，女同学手腕不自觉往回缩的瞬间。",
     ["S08"], ["刑警", "女同学"], "希区柯克式微变焦", "心跳般低沉闷响", "强对比"),
    (6, "警方随即搜查了李某的住处，果然在屋里翻出了被切开的塑料瓶。",
     "另一间公寓桌面物证特写，一只被剪去底部的透明塑料瓶静静立在桌上。",
     ["S07"], ["刑警"], "俯拍推近", "塑料瓶轻碰桌面声", "冷白光"),
    (6, "原来她作案时用塑料瓶垫在门框上防留痕，又贴了纸片方便事后撕掉。",
     "门框上方边缘光影示意特写，没有人物，只见冷硬木框与细微反光。",
     ["S04"], [], "仰拍门框缓慢横移", "胶带撕扯轻响", "暗调特写"),
    (6, "可她万万没想到，那片不起眼的小纸片最终粘在了朴某的手心里。",
     "物证袋里的小纸片再次特写，成为打破完美密室的第一道裂口。",
     ["S07"], [], "微距定镜推近", "低频沉重余音", "强明暗对比"),
    (6, "面对铁证，李某终于交代自己因嫉妒朴某婚姻美满，还与金某有染而动了杀机。",
     "审讯室暗影里女同学低头垂肩的剪影，窗外夜色深沉。",
     ["S08"], ["女同学"], "缓慢拉远", "室内钟表走动声", "冷灰绝望"),
    (6, "她先在屋里制造出母子轻生的假象，最后用钥匙从外面反锁了防盗门。",
     "防盗门外侧锁孔在暗夜里被钥匙拧紧的局部特写。",
     ["S01"], [], "特写推进锁孔", "金属锁舌落锁声", "高对比"),
    (6, "随后她把装钥匙的手提包顺着走廊窗缝扔回小房间，完成了整场密室骗局。",
     "走廊小窗缝隙特写，一只深色手提包被从窗外塞进昏暗室内。",
     ["S03"], [], "窗缝内外推拉", "布包落地闷响", "冷暗调"),
    (6, "这起震惊韩国的巨余洞密室案，最终以李某被判处无期徒刑画上句号。",
     "首尔法院庄严肃穆的石阶与高大立柱远景，冬日阴天冷光。",
     ["S09"], [], "仰拍缓慢推进", "法槌清脆一响", "冷灰庄重"),
    (6, "没有无懈可击的完美犯罪，再精密的密室，也藏不住人心留下的破绽。",
     "七楼公寓窗户在黎明微光中逐渐亮起冷白晨色，空镜静静拉远。",
     ["S05"], [], "缓慢升格拉远", "清晨微弱风声", "冷暖交替"),
    (6, "如果当时刑警没有盯住她藏起来的右手，这起案件还会被当成自杀吗？",
     "深色走廊尽头防盗门渐暗入黑，片尾留白等待字幕落版。",
     ["S01"], [], "缓慢推暗渐黑", "走廊灯光熄灭轻响", "极简暗调"),
]

assert len(ROWS) == 30, f"Expected 30 shots, got {len(ROWS)}"
assert sum(r[0] for r in ROWS) == 180, f"Expected 180s total, got {sum(r[0] for r in ROWS)}"


def build() -> dict:
    revision_path = HERE / "reference" / "revision.txt"
    revision = revision_path.read_text(encoding="utf-8").strip() if revision_path.exists() else ""
    approvals_path = HERE / "reference" / "approvals.json"
    approvals = json.loads(approvals_path.read_text(encoding="utf-8")) if approvals_path.exists() else {}

    ref_images = {}
    for key, meta in sorted(approvals.items()):
        if isinstance(meta, dict) and meta.get("approved"):
            ref_images[key] = {
                "path": meta["path"],
                "sha256": meta["sha256"],
                "approved": True,
                "note": meta.get("note", ""),
            }

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
            "start": cursor,
            "duration": duration,
            "narration": narration,
            "visual": visual,
            "camera": camera,
            "sound": sound,
            "grade": grade,
            "reference_ids": refs,
            "roles": roles,
            "prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        })
        cursor += duration

    chapters = [
        {"title": title, "start": start, "end": end}
        for title, start, end in CHAPTERS
    ]

    voice_path = HERE / "audio" / "voice.json"
    voice = json.loads(voice_path.read_text(encoding="utf-8")) if voice_path.exists() else {}
    voice_id = voice.get("voice_id") or "pending_voice_selection"

    presentation = {
        "onscreen_label": "AI动画情景重现 · 非真实影像",
        "highlight_phrases": HIGHLIGHT_PHRASES,
        "hooks": HOOKS,
        "explainers": EXPLAINERS,
        "end_title": "巨余洞密室案",
        "end_subtitle": "2003 · 首尔七楼 · 窗缝里的钥匙",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "门从里面反锁",
        "cover_concept": "封面只用本片已生成视频截图：镜头01或06走廊窗缝与门锁帧；禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "门从里面反锁，钥匙却在窗缝的包里：韩国巨余洞密室案",
        "hashtags": ["#巨余洞密室案", "#韩国真实案件", "#密室杀人", "#案件解说", "#悬疑"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已通过公开资料核实核心时间线与无期徒刑终审判决；不具象化呈现暴力与儿童受害细节，见 FACT_CHECK.md",
        "as_of": "2026-11-22",
        "legal_note": "首尔东部地方法院一审判处李某无期徒刑，首尔高等法院二审与大法院终审均驳回上诉维持原判。",
        "sources": [
            {"publisher": "Namuwiki《거여동 밀실 살인 사건》", "date": "2003–2004 判决汇总", "url": "https://namu.wiki/w/%EA%B1%B0%EC%97%AC%EB%8F%99%20%EB%B0%80%EC%8B%A4%20%EC%82%B4%EC%9D%B8%20%EC%82%AC%EA%B1%B4", "supports": "案发经过、物证与无期徒刑判决"},
        ],
        "editorial_cautions": [
            "受害者与当事人统一使用朴某、金某、李某，不使用真实全名与肖像",
            "严禁具象化呈现勒颈、塑料袋、踩踏或儿童遗体画面",
            "不得编造灵异或判决书之外的细节",
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
            "description": voice.get("description", "TODO 试音选定后的音色描述"),
            "language": "zh-CN", "target_characters_per_second": 4.2,
            "alignment": "一镜一句，一镜一条TTS与一条字幕；只在确有必要时加速，不慢放",
        },
        "chapters": chapters, "shots": shots,
        "reference_images": ref_images,
        "reference_revision": revision,
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期高质量放大到1080P。",
            "所有Agnes提示词由generate.py自动组合：STYLE在最前，角色锚点逐字插入，NEGATIVE在末尾；文字全部禁止AI自绘，由后期烧录。",
            "全片无BGM；旁白与字幕逐句锁定，音效/环境声只做轻量辅助，不盖住解说。",
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
        "二零零三年十二月二十九日傍晚，韩国首尔松坡区巨余洞一处七楼公寓防盗门从内部反锁，屋主妻子与两名年幼孩子遇难，最初几乎被当成轻生密室。",
        "",
        "刑警在死者手中发现不明小纸片，又在常来走动的高中同学李某手上发现绳索勒痕。最终法院一审、二审及大法院均判处李某无期徒刑。",
        "",
        "AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md。",
        "", "## 提问读者一句话", "",
        "如果当时刑警没有盯住她藏起来的右手，这起案件还会被当成自杀吗？",
        "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

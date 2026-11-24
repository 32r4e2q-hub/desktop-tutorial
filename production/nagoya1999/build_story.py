#!/usr/bin/env python3
"""《名古屋主妇杀害事件：丈夫守着血迹公寓二十六年，终于等来凶手落网》—— 唯一内容源。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "名古屋主妇杀害事件：丈夫守着血迹公寓二十六年，终于等来凶手落网"
BRANCH = "arena/f9f847e0-desktop-tutorial"
FILM_NAME = "名古屋主妇杀害事件_丈夫守着血迹公寓二十六年，终于等来凶手落网_三分钟_带声音.mp4"

STYLE = (
    "【STYLE】日系写实悬疑纪录片质感电影动画，一九九九年十一月至二零二五年日本名古屋市西区公寓与警署，"
    "冷青灰与室内暗暖钨丝灯明暗对立，浅景深镜头语言与克制推拉运镜，人物均为虚构演员式背影侧脸与局部剪影，"
    "不还原任何真实人物肖像，画面内无任何可读文字或招牌，连续运动，16:9，底部预留字幕安全区。"
)
NEGATIVE = (
    "【NEGATIVE】no readable text, no subtitles, no watermark, no gore, no blood pool, no corpse, "
    "no child harm depiction, no anime style, no bright idyllic scenery, no deformed hands"
)

CHARACTERS = {
    "高羽悟": "三十多岁到五十多岁日本男性，深色大衣或西装，疲惫却坚毅的背影与侧脸，不露正脸",
    "安福": "六十九岁日本女性，深色朴素外套，低头掩面背影或暗影侧脸，不露正脸",
    "刑警": "四十岁日本男刑警，深灰风衣，目光锐利，侧脸与手部细节",
}

CHARACTER_SEEDS = {"高羽悟": 2501, "安福": 2502, "刑警": 2503}

CHARACTER_REFERENCE_IDS = {
    "高羽悟": ["C01"],
    "安福": ["C02"],
    "刑警": ["C03"],
}

HIGHLIGHT_PHRASES = [
    "一九九九年十一月十三日",
    "名古屋",
    "高羽奈美子",
    "二十六年",
    "两千两百万日元",
    "二零二五年十月",
    "安福久美子",
    "高中同学",
    "DNA",
]

HOOKS = [
    {"id": "H1", "start": 0.5, "end": 2.5, "text": "他租下血迹公寓二十六年，只为等一个名字"},
    {"id": "H2", "start": 24.0, "end": 26.0, "text": "三十一岁主妇家中遇害，两岁幼子就在身旁"},
    {"id": "H3", "start": 48.0, "end": 50.0, "text": "玄关留下的血脚印，并不属于受害者"},
    {"id": "H4", "start": 72.0, "end": 74.0, "text": "墙上的月历，永远停在一九九九年十一月"},
    {"id": "H5", "start": 96.0, "end": 98.0, "text": "二十六年，累计房租超过两千两百万日元"},
    {"id": "H6", "start": 114.0, "end": 116.0, "text": "二零二五年十月，六十九岁女子独自走进警署"},
    {"id": "H7", "start": 132.0, "end": 134.0, "text": "她竟然是丈夫当年的高中同学"},
    {"id": "H8", "start": 150.0, "end": 152.0, "text": "DNA比对一致，二十六年悬案终于告破"},
    {"id": "H9", "start": 168.0, "end": 170.0, "text": "二十六年的执着，终于等来了真相"},
]

EXPLAINERS = [
    {"id": "E1", "start": 12.0, "end": 16.0, "text": "1999年11月13日，日本名古屋市西区"},
    {"id": "E2", "start": 84.0, "end": 88.0, "text": "高羽悟自费续租26年，花费超2200万日元"},
    {"id": "E3", "start": 156.0, "end": 160.0, "text": "2025年10月31日，69岁安福久美子被警方逮捕"},
]

CHAPTERS = [
    ("第一章 凝结在一九九九", 0, 30),
    ("第二章 玄关的秘密", 30, 60),
    ("第三章 二十六年的房租", 60, 90),
    ("第四章 十万警力的排查", 90, 120),
    ("第五章 走进警署的女人", 120, 150),
    ("第六章 迟到二十六年的答案", 150, 180),
]

ROWS = [
    (6, "一间空无一人的日本公寓，丈夫自费租了整整二十六年，只为守住玄关的痕迹。",
     "昏暗日本旧式公寓玄关空镜，地面铺着深色保护垫，空气凝滞，门外透进冷光。",
     ["S01"], ["高羽悟"], "缓慢推近玄关地面", "室内死寂环境风声", "冷青灰强明暗对比"),
    (6, "时间回到一九九九年十一月十三日，名古屋市西区发生了一起震惊日本的命案。",
     "一九九九年十一月阴天名古屋市区老旧公寓外景，电线交错，街道冷清。",
     ["S02"], [], "缓慢横摇公寓外景", "城市远景风声", "冷灰蓝"),
    (6, "当天下午，三十二岁的主妇高羽奈美子在家中遇害，两岁儿子就在身旁。",
     "昏暗客厅空镜，茶几旁散落着儿童玩具积木与未收拾的橘子皮，不出现任何遗体。",
     ["S03"], [], "浅景深推进桌面", "室内钟表滴答声", "冷暖交界"),
    (6, "警方勘查发现，一向爱干净的奈美子桌上还放着泡面，说明来客完全出乎意料。",
     "厨房与餐桌一角特写，一只未吃完的泡面碗静静摆在台面，灯光昏暗。",
     ["S03"], [], "浅景深缓慢平移", "水龙头滴水声", "暗暖转冷"),
    (6, "更关键的是，警方在玄关处发现了约二十四公分的鞋印和B型血迹。",
     "玄关门厅地面局部光影特写，门框边缘冷硬反光，不见血腥画面。",
     ["S01"], ["刑警"], "俯拍局部推进", "相机快门轻响", "强明暗对比"),
    (6, "警方判断凶手在搏斗中受了伤，捂着伤口逃离，却没能查出对方身份。",
     "公寓楼外夜间楼梯间，一道模糊背影迅速走下台阶消失在夜色里。",
     ["S02"], ["安福"], "远景侧跟拍", "急促下楼脚步声", "极暗冷调"),
    (6, "案发三年后，一名专家提醒丈夫高羽悟，玄关留下的痕迹很可能属于凶手。",
     "昏暗公寓内，高羽悟背影站在玄关前低头看着地面保护垫，久久不动。",
     ["S01"], ["高羽悟"], "侧逆光中景", "低频环境沉音", "冷灰压抑"),
    (6, "从那以后，高羽悟下定决心，无论搬去哪里，这间案发公寓绝不退租。",
     "公寓墙面特写，一本泛黄的老式月历安静挂在暗影里，页面静止。",
     ["S04"], [], "定镜缓慢推进", "纸张微动轻响", "冷硬纪实"),
    (6, "为了防止线索被破坏，他用保护垫盖住玄关地面，墙上月历永远停在十一月。",
     "高羽悟戴着手套轻轻铺平玄关保护垫的局部手部特写。",
     ["S01"], ["高羽悟"], "局部手部特写", "布料摩擦声", "暗调高反差"),
    (6, "整整二十六年，他累计支付房租超过两千两百万日元，头发也渐渐花白。",
     "名古屋街头冬日风中，鬓角斑白的高羽悟背影独自走过斑马线。",
     ["S05"], ["高羽悟"], "中景跟拍背影", "冬季街头风声与车流", "冷蓝夜色"),
    (6, "每年案发周年，他都会走上街头分发传单，只求有人能提供哪怕一条线索。",
     "人流稀少的名古屋车站外，高羽悟弯腰递出空白纸页传单的侧影。",
     ["S05"], ["高羽悟"], "缓慢横摇街景", "街头脚步声", "冷灰调"),
    (6, "与此同时，爱知县警方二十六年来累计动员十万警力，排查了五千多人。",
     "警局夜间档案室，一排排厚重卷宗在冷白日光灯下静静立在铁架上。",
     ["S06"], ["刑警"], "缓慢平移档案架", "日光灯微嗡", "冷青调"),
    (6, "直到二零二四年，警方重新梳理旧案资料，将重点对象缩小到几百人。",
     "刑警坐在办公桌前翻看旧案卷宗的侧脸剪影，桌面台灯亮着。",
     ["S06"], ["刑警"], "隔玻璃缓慢推进", "纸张翻动声", "高对比冷调"),
    (6, "二零二五年八月，警方开始多次约谈一名住在名古屋港区的六十九岁女性。",
     "审讯室外走廊，一名穿深色朴素外套的年长女性低头走过的背影。",
     ["S07"], ["安福"], "长跟拍背影", "走廊脚步声", "冷暗压抑"),
    (6, "她叫安福久美子，起初多次拒绝提供DNA样本，直到十月底态度突然松动。",
     "审讯室桌面，一只透明样本管与白色棉签盒静静摆在冷光下。",
     ["S07"], ["刑警"], "俯拍微距", "桌面轻响", "冷白聚光"),
    (6, "十月三十日，安福久美子竟然独自走进警署自首，并在次日被警方正式逮捕。",
     "日本警署大门外景，阴天冷光下一名年长女性背影独自走上台阶。",
     ["S08"], ["安福"], "远景仰拍推进", "城市风声", "冷灰庄重"),
    (6, "经检测，她与当年现场留下的DNA完全一致，二十六年的悬案终于迎来突破。",
     "实验室玻璃反光后，检验仪器微光闪烁，镜头缓慢推进。",
     ["S06"], [], "隔玻璃推近", "仪器轻微提示音", "冷青调"),
    (6, "而当警方公布嫌疑人身份时，守候了二十六年的高羽悟却感到无比震惊。",
     "高羽悟站在公寓窗边接听电话的背影剪影，窗外是名古屋阴天。",
     ["S04"], ["高羽悟"], "侧逆光定镜", "电话听筒微响", "强明暗对比"),
    (6, "因为这名六十九岁的嫌疑人，竟然是他当年高中软式网球社的同班同学。",
     "泛黄旧校园网球场空镜，铁丝网外冷风吹过空荡球场。",
     ["S09"], [], "广角缓慢横摇", "球网风声", "冷暖交替"),
    (6, "高羽悟回忆，高中时曾收到过她的告白信，自己拒绝后两人几乎再无往来。",
     "昏暗书桌一角，一封未拆封的旧信纸在微风中轻轻晃动。",
     ["S04"], [], "浅景深微距", "纸页轻响", "暗暖转冷"),
    (6, "谁也没想到，这段几十年前的旧事，竟会演变成二十六年前那场无妄之灾。",
     "名古屋老旧公寓楼外景拉远，天色阴沉。",
     ["S02"], [], "缓慢拉远", "低频环境沉音", "冷灰绝望"),
    (6, "安福久美子交代，这二十六年来自己每天都活在恐惧中，生怕给家人添麻烦。",
     "审讯室暗影里年长女性低头垂肩的剪影，窗外夜色深沉。",
     ["S07"], ["安福"], "缓慢拉远", "室内钟表走动声", "冷灰压抑"),
    (6, "为了躲避怀疑，她几乎不与邻居深交，在超市打工度日，像透明人一样生活。",
     "昏暗居民区小巷，一名穿深色外套的女性背影独自快步走入暗处。",
     ["S05"], ["安福"], "远景跟拍背影", "小巷脚步声", "极暗冷调"),
    (6, "二十六年后，警方带着她重返那间从未改变的公寓进行现场勘验。",
     "公寓门口警车停靠，几名刑警背影走进保存完好的楼道。",
     ["S02"], ["刑警"], "中景跟拍背影", "对讲机杂音", "冷硬纪实"),
    (6, "掀开保护垫，二十六年前的痕迹依然清晰，仿佛时间从未在这里流走。",
     "玄关地面保护垫被轻轻掀开一角的局部特写，冷光照亮木地板边缘。",
     ["S01"], ["刑警"], "局部特写推进", "布垫摩擦声", "强明暗对比"),
    (6, "高羽悟说，二十六年付出的房租都值得，只对妻子感到深深的抱歉。",
     "高羽悟背影站在玄关前微微低头，室内透进一丝清晨冷白微光。",
     ["S01"], ["高羽悟"], "缓慢推近背影", "清晨微弱风声", "冷暖交界"),
    (6, "他终于可以在亡妻的牌位前，亲口说出那个迟到了四分之一世纪的答案。",
     "昏暗房间窗台前，一束冷白晨光落在空荡的木桌上。",
     ["S04"], [], "缓慢升格推进", "环境风声渐弱", "冷暖交替"),
    (6, "两千两百万日元换不回逝去的生命，却守住了唯一没有被时间抹去的证据。",
     "名古屋公寓楼外景在晨光中逐渐拉远，天际泛亮。",
     ["S02"], [], "缓慢升格拉远", "清晨微风声", "极简冷调"),
    (6, "再漫长的黑夜也有尽头，只要有人不肯忘记，真相就总有一天会被等来。",
     "警署石阶在晨光中静默立着，镜头缓慢拉远。",
     ["S08"], [], "缓慢拉远", "环境音渐息", "冷暖交替"),
    (6, "如果是你，你会像高羽悟一样，用二十六年去守一间空房等一个答案吗？",
     "深色玄关防盗门渐暗入黑，片尾留白等待字幕落版。",
     ["S01"], [], "缓慢推暗渐黑", "关门轻响", "极简暗调"),
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
            "seed": 2500 + idx,
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
        "end_title": "名古屋主妇杀害事件",
        "end_subtitle": "1999 – 2025 · 二十六年的守候",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "守着血迹公寓26年",
        "cover_concept": "封面只用本片已生成视频截图；禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "丈夫守着血迹公寓二十六年，终于等来凶手自首：名古屋主妇杀害事件",
        "hashtags": ["#名古屋主妇杀害事件", "#日本真实案件", "#高羽奈美子", "#案件解说", "#悬疑"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），单排56号大字一个逗号出一句；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已通过2025年10-11月公开报道核实时间线与逮捕进展；案件仍在司法程序中，不提前定罪，见 FACT_CHECK.md",
        "as_of": "2026-11-22",
        "legal_note": "2025年10月31日，69岁嫌疑人安福久美子因DNA比对一致被日本警方以杀人嫌疑逮捕。",
        "sources": [
            {"publisher": "中央社", "date": "2025-10-31 / 2025-11-03", "url": "https://www.cna.com.tw/news/aopl/202511030244.aspx", "supports": "案发经过、26年租房保存现场与2025年自首被捕"},
        ],
        "editorial_cautions": [
            "严禁具象化呈现刺杀、大量出血或遗体画面",
            "嫌疑人刚被逮捕，不得提前写已被判死刑/无期",
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
        "一九九九年十一月十三日，日本名古屋三十二岁主妇高羽奈美子在家中遇害，两岁幼子就在身旁。丈夫高羽悟为了保存玄关血迹，自费续租这间空公寓二十六年，累计花费超过两千两百万日元。",
        "",
        "二零二五年十月底，六十九岁女子安福久美子独自走进警署自首，DNA比对与现场血迹一致，她竟是高羽悟当年的高中同学。",
        "",
        "AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md。",
        "", "## 提问读者一句话", "",
        "如果是你，你会像高羽悟一样，用二十六年去守一间空房等一个答案吗？",
        "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

#!/usr/bin/env python3
"""《六本木洞窟迷案：英国空姐在东京消失，七个月后现身海蚀洞》—— 唯一内容源。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "六本木洞窟迷案：英国空姐在东京消失，七个月后现身海蚀洞"
BRANCH = "arena/f9f847e0-desktop-tutorial"
FILM_NAME = "六本木洞窟迷案_英国空姐在东京消失，七个月后现身海蚀洞_三分钟_带声音.mp4"

STYLE = (
    "【STYLE】日系写实悬疑纪录片质感电影动画，二零零零年夏季东京六本木夜色与神奈川三浦海岸海蚀洞，"
    "冷青灰与霓虹暗暖明暗对立，浅景深镜头语言与克制推拉运镜，人物均为虚构演员式背影侧脸与局部剪影，"
    "不还原任何真实人物肖像，画面内无任何可读文字或招牌，连续运动，16:9，底部预留字幕安全区。"
)
NEGATIVE = (
    "【NEGATIVE】no readable text, no subtitles, no watermark, no gore, no blood, no corpse, "
    "no sexual violence depiction, no anime style, no bright idyllic scenery, no deformed hands"
)

CHARACTERS = {
    "露西": "二十一岁金发英国年轻女性，深色夏装外套，背影或四分之三侧脸，不露正脸",
    "织原": "四十多岁东亚男性，深色高档西装，背影或暗影侧脸，不露正脸",
    "刑警": "四十岁日本男刑警，深灰风衣，目光锐利，侧脸与手部细节",
}

CHARACTER_SEEDS = {"露西": 2301, "织原": 2302, "刑警": 2303}

CHARACTER_REFERENCE_IDS = {
    "露西": ["C01"],
    "织原": ["C02"],
    "刑警": ["C03"],
}

HIGHLIGHT_PHRASES = [
    "二零零零年七月一日",
    "六本木",
    "露西",
    "七个月",
    "海蚀洞",
    "七小时",
    "二三百米",
    "织原城二",
    "无期徒刑",
]

HOOKS = [
    {"id": "H1", "start": 0.5, "end": 2.5, "text": "英国空姐东京失踪，七个月后现身海蚀洞"},
    {"id": "H2", "start": 24.0, "end": 26.0, "text": "她用客人送的新手机，打了最后一通电话"},
    {"id": "H3", "start": 48.0, "end": 50.0, "text": "三个月后，警局收到一封“她的来信”"},
    {"id": "H4", "start": 72.0, "end": 74.0, "text": "通话记录里，消失了整整七小时"},
    {"id": "H5", "start": 96.0, "end": 98.0, "text": "海边别墅两百米外，藏着一处海蚀洞"},
    {"id": "H6", "start": 114.0, "end": 116.0, "text": "二零零一年二月九日，真相浮出水面"},
    {"id": "H7", "start": 132.0, "end": 134.0, "text": "一审竟因证据不足，判他部分无罪"},
    {"id": "H8", "start": 150.0, "end": 152.0, "text": "最高法院终审：维持无期徒刑"},
    {"id": "H9", "start": 168.0, "end": 170.0, "text": "一部新手机，成了她留下的最后坐标"},
]

EXPLAINERS = [
    {"id": "E1", "start": 12.0, "end": 16.0, "text": "露西·布莱克曼，21岁，原英国航空空姐"},
    {"id": "E2", "start": 78.0, "end": 82.0, "text": "神奈川县三浦市诸矶湾，距嫌疑人别墅约二三百米"},
    {"id": "E3", "start": 156.0, "end": 160.0, "text": "2010年12月日本最高法院终审维持无期徒刑"},
]

CHAPTERS = [
    ("第一章 消失在六本木", 0, 30),
    ("第二章 最后一通电话", 30, 60),
    ("第三章 空白的七小时", 60, 90),
    ("第四章 诸矶湾海蚀洞", 90, 120),
    ("第五章 漫长的拉锯", 120, 150),
    ("第六章 终审与余音", 150, 180),
]

ROWS = [
    (6, "二零零零年七月一日，二十一岁英国空姐露西在东京六本木彻底失踪。",
     "二零零零年夏夜东京六本木湿润街道，霓虹倒映在积水路面，金发年轻女性背影走入夜色。",
     ["S01"], ["露西"], "缓慢跟拍背影", "东京夜街车流与雨夜环境音", "冷青灰与霓虹暗暖对比"),
    (6, "几个月前她刚辞去英航工作，来东京打工攒旅费，却误入高级夜店。",
     "六本木酒吧门口暗沉金属门框与微弱暖灯，门内人影晃动。",
     ["S01"], [], "缓慢推近门框", "隐约低沉室内人声", "暗暖对比"),
    (6, "失踪当晚，露西兴奋地告诉朋友，有位熟客要买一部新手机送给她。",
     "昏暗公寓窗边，年轻女性背影低头看手中新款翻盖手机，窗外是东京夜色。",
     ["S02"], ["露西"], "浅景深侧背影", "手机按键轻响", "冷暖交界"),
    (6, "随后她独自跟着这名男子前往海边，谁也没想到这是她最后一次露面。",
     "夜间海边公路空镜，黑色轿车尾灯消失在沿海弯道尽头。",
     ["S03"], [], "定镜长焦拉远", "海风与远去引擎声", "冷蓝夜色"),
    (6, "当晚露西曾用那部新手机打回电话，只说自己在海边，很快就会回来。",
     "海浪拍打暗礁的海岸线远景，手机信号微弱闪烁。",
     ["S03"], [], "缓慢横摇海面", "海浪拍岸声", "极暗冷调"),
    (6, "可第二天、第三天过去，露西再也没有出现，手机也彻底关机。",
     "空荡东京合租公寓桌面，日历翻页停在七月初，房间一片冷清。",
     ["S02"], [], "浅景深缓慢推进", "室内钟表滴答声", "冷灰蓝"),
    (6, "焦急的家人从英国赶到东京，甚至惊动了英国首相出面敦促日方调查。",
     "东京警视厅大楼外景，阴天冷光下警车静静停在门前。",
     ["S04"], [], "仰拍缓慢推进", "城市风声", "冷硬纪实"),
    (6, "可起初警方进展缓慢，直到十月，警署突然收到一封署名露西的信。",
     "警局办公桌暗影，一封白色信封静静躺在金属托盘里，无任何可读字迹。",
     ["S05"], ["刑警"], "俯拍微距", "纸张轻响", "强明暗对比"),
    (6, "信里附着一万美金，声称自己已经离开日本，但这反而暴露了破绽。",
     "刑警戴着白手套拿起信封端详的侧脸剪影，神情凝重。",
     ["S05"], ["刑警"], "侧逆光推进", "低沉环境音", "冷青调"),
    (6, "警方认定这是凶手自导自演的障眼法，视线立刻锁定了富商织原城二。",
     "神奈川海边一栋冷清的现代混凝土别墅外景，铁门紧闭。",
     ["S06"], ["织原"], "缓慢推近铁门", "海风呼啸声", "冷灰压抑"),
    (6, "织原城二常混迹六本木，而露西失踪当晚那部新手机，正是他出面买下的。",
     "昏暗档案室桌面，手机通话记录与基站地图剪影铺在台面。",
     ["S05"], ["刑警"], "俯拍缓慢平移", "纸张翻动声", "冷白聚光"),
    (6, "警方调取了织原全部通话记录，终于在七月三日发现一段致命空白。",
     "刑警站在夜色办公室玻璃前盯着地图标记的侧影，窗外灯火稀疏。",
     ["S05"], ["刑警"], "隔玻璃缓慢横摇", "室内日光灯微嗡", "高对比冷调"),
    (6, "那天他在神奈川三浦市诸矶湾一带，整整七个小时没有打过一通电话。",
     "三浦市诸矶湾阴天海岸线远景，灰暗海面与崎岖礁石。",
     ["S07"], [], "广角缓慢横移", "海浪与海风声", "冷灰蓝"),
    (6, "更可疑的是，他名下一栋海边别墅平时从不住人，当时却突然现身。",
     "海边别墅侧面围墙与生锈铁门特写，杂草在风中晃动。",
     ["S06"], [], "浅景深推进", "铁门微响", "冷暗调"),
    (6, "管理员还曾目击他浑身是土，深夜里手里提着一把铁锹在附近走动。",
     "暗夜别墅外小路，一道提着长柄工具的男性背影剪影迅速隐入树影。",
     ["S06"], ["织原"], "远景侧跟拍", "脚步踩碎石声", "极暗剪影"),
    (6, "警方立刻把搜索重心，压向这栋海边别墅方圆两三百米的海岸线。",
     "海岸礁石滩，几名刑警背影沿着潮湿岩壁仔细搜寻。",
     ["S07"], ["刑警"], "中景跟拍背影", "海浪拍石声", "冷硬纪实"),
    (6, "二零零一年二月九日，距离露西失踪整整七个月，搜查终于有了结果。",
     "海蚀洞漆黑洞口外景，洞口堆着废弃渔网与海草，潮水退去。",
     ["S08"], [], "缓慢推近洞口", "洞内风声回响", "强明暗对比"),
    (6, "就在距离织原别墅不到三百米的海蚀洞深处，警方找到了被藏匿的遗骸。",
     "海蚀洞内手电筒光束扫过潮湿岩壁的局部光影，不出现任何遗骸画面。",
     ["S08"], ["刑警"], "手电光束横摇", "滴水与海浪声", "极暗冷调"),
    (6, "次日法医确认，这正是失踪七个月的英国空姐露西·布莱克曼。",
     "警视厅发布会外景走廊，阴沉天色下镜头静静拉远。",
     ["S04"], [], "缓慢拉远", "低频沉重余音", "冷灰庄重"),
    (6, "警方查明，织原长期利用药物侵害女性，并在别墅里偷拍犯罪过程。",
     "别墅二楼拉上厚重窗帘的窗户特写，室内透出一丝冷白微光。",
     ["S06"], [], "定镜仰拍", "低沉环境音", "暗调压抑"),
    (6, "然而进入法庭审理后，这起铁案却因为直接物证损毁而陷入漫长拉锯。",
     "东京地方法院庄严的石阶与玻璃幕墙外景，阴天冷光。",
     ["S09"], [], "缓慢推进石阶", "城市风声", "冷灰调"),
    (6, "织原城二矢口否认杀害露西，甚至在庭审前向露西父亲支付巨额赔款。",
     "法庭走廊深色木门紧闭，门外光影冷清。",
     ["S09"], [], "浅景深推进", "沉闷关门声", "冷硬纪实"),
    (6, "二零零七年一审宣判，法院竟以缺乏直接死因证据判他露西案部分无罪。",
     "空旷法庭内木质旁听席一角，冷白顶灯照在空椅子上。",
     ["S09"], [], "缓慢横摇", "法槌清脆一响", "高对比"),
    (6, "判决一出英日舆论哗然，检方当庭上诉，绝不接受这样的结果。",
     "法院外阴雨绵绵的广场空镜，积水倒映着灰色建筑。",
     ["S09"], [], "广角缓慢拉远", "细雨声", "冷灰绝望"),
    (6, "二零零八年十二月二审终于改判，认定他对露西犯有强奸未遂与弃尸罪。",
     "东京高等法院大楼立柱仰拍，厚重石墙在阴天中显得冷峻。",
     ["S09"], [], "仰拍缓慢推进", "低沉风声", "冷灰庄重"),
    (6, "二零一零年十二月，日本最高法院终审驳回上诉，维持无期徒刑判决。",
     "最高法院外景全景，冬日冷光下石阶静默无声。",
     ["S09"], [], "缓慢升格拉远", "法槌定音", "冷暖交替"),
    (6, "迟到十年的终审判决，虽然判处了无期徒刑，却再也换不回那个二十一岁女孩。",
     "东京六本木清晨微光中的空街，霓虹熄灭，路面只剩冷白晨色。",
     ["S01"], [], "缓慢拉远", "清晨微弱风声", "冷暖交界"),
    (6, "如果不是警方死盯那七小时的通话空白，海蚀洞里的秘密或许永远无人知晓。",
     "三浦诸矶湾海蚀洞外景，潮水缓缓涌向礁石。",
     ["S08"], [], "缓慢推近海浪", "海浪声渐弱", "极简冷调"),
    (6, "一部新手机成了最后的坐标，也让再精密的伪装最终暴露在阳光下。",
     "海边海岸线黎明微光，天际泛起一丝冷白亮色。",
     ["S07"], [], "缓慢横摇海面", "海风轻声", "冷暖交替"),
    (6, "面对一审的无罪争议和十年后的终审无期，你觉得正义真的来得及吗？",
     "东京夜色街道渐暗入黑，片尾留白等待字幕落版。",
     ["S01"], [], "缓慢推暗渐黑", "夜风渐息", "极简暗调"),
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
            "seed": 2300 + idx,
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
        "end_title": "六本木洞窟迷案",
        "end_subtitle": "2000 · 东京六本木 · 诸矶湾海蚀洞",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "七个月后现身海蚀洞",
        "cover_concept": "封面只用本片已生成视频截图；禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "英国空姐在东京六本木消失，七个月后现身海蚀洞：六本木洞窟迷案",
        "hashtags": ["#六本木洞窟迷案", "#日本真实案件", "#露西布莱克曼", "#案件解说", "#悬疑"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已通过公开资料核实核心时间线与日本最高法院无期徒刑终审判决；不具象化呈现暴力与遗骸细节，见 FACT_CHECK.md",
        "as_of": "2026-11-22",
        "legal_note": "2010年12月日本最高法院终审维持无期徒刑判决。",
        "sources": [
            {"publisher": "日本最高法院/东京高等法院公开判决报道汇总", "date": "2007–2010", "url": "https://www.163.com/news/article/DHV35FNV00019A2S.html", "supports": "案发经过、通联记录与终审无期徒刑"},
        ],
        "editorial_cautions": [
            "严禁具象化呈现药物侵害、肢解、电锯、水泥封头或遗骸画面",
            "不得编造判决书之外的细节",
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
        "二零零零年七月一日，二十一岁前英国航空空姐露西·布莱克曼在东京六本木打工期间失踪。七个月后，日本警方根据嫌疑人织原城二手机通话记录中长达七小时的空白，在其海边别墅附近的海蚀洞内发现她的遗骸。",
        "",
        "历经一审部分无罪争议后，二零一零年十二月日本最高法院终审维持无期徒刑判决。",
        "",
        "AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md。",
        "", "## 提问读者一句话", "",
        "面对一审的无罪争议和十年后的终审无期，你觉得正义真的来得及吗？",
        "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

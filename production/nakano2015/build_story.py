#!/usr/bin/env python3
"""《东京中野女演员尾随案：一句搭讪之后的致命跟踪》—— 唯一内容源：解说词、30 镜分镜、参考图、钩子/注释、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
流水线出处是 production/shanghai_freezer_case/build_story.py —— 一部出片、换声、重渲都跑完的成片）。

用法::

    python3 production/nakano2015/build_story.py            # 写 story.json + screenplay.md + 抖音脚本.md + 抖音发布文案.md

写法规则（都是前作踩出来的，别省）：

- 30 镜 × 6 秒规划网格，时间轴由本文件的 ROWS 顺序自动累加，合计必须正好 180 秒（结尾校验会卡）；
  时长只能是 2–13 秒的整数。每镜一句解说，TTS 一镜一条，字幕与音频逐字一致。
- 解说要有电影感：前 3 秒 = 反常事实 + 强视觉画面（禁静态 UI/波形/纯文字开场、禁绕弯设问）；
  中段每 20–30 秒一个信息钩子；结尾 8 秒 = 金句 → 互动提问 → 落版；记忆锚点数字 ≥ 5 次强调；
  单句 ≤ 屏显一行（≤16 字），关键词加粗放大。详见 `新题目开工手册.md` §3.1 / §10。
- 数字一律写成中文读法（"二零一六年十月十七日""年仅三十二岁"），TTS 和字幕才一致。
- 不写血腥/侵害过程的具体描写（TTS 审核会拒，红线也不允许）。
- STYLE 在每个提示词最前、NEGATIVE 在最后，generate.py 自动拼接；角色锚点原文插入对应镜头。
  提示词钉死"唯一场景"（去 AI 味：纪实感场景/背影侧脸/无唯美空镜），否定词对视频模型基本没用，
  想去掉某样东西就别给它出现的空间。画面按纪实感写法补手法：强明暗对比/浅景深/升格/暖冷对立。
- 参考图：每镜 __ 张（Agnes 2.5 Flash reference 模式 1–5 张），按 reference/approvals.json 登记；
  没有批准参考图，--validate 直接报错（这是设计：先开造型/场景参考，再烧视频额度）。
- 钩子 H1..Hn：白字黑边、居中偏下（MarginV=275）、每条严格 2 秒；金色注释 MarginV=200，只补可核实事实。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "东京中野女演员尾随案：一句搭讪之后的致命跟踪"
BRANCH = "arena/0dca6842-desktop-tutorial"
FILM_NAME = "东京中野女演员尾随案_一句搭讪之后的致命跟踪_三分钟_带声音.mp4"

# 全片统一的画面风格前缀（第 1 位拼接）。TODO：把「世界描述」换成本片的地点/年代/道具；
# 后半句（人物只给虚构演员形象、无可读文字、连续运动、16:9、底部字幕安全区）是流水线规则，别删。
# 注意：style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 30 镜全部重做。
STYLE = (
    "【STYLE】二零一五年至二零一九年日本东京的纪录片式写实电影画面，中野区街巷、旧公寓走廊、便利店、"
    "练功房与法院外景；深夜冷蓝街灯、室内暖黄台灯、清晨低饱和日光交替，35毫米胶片质感，浅景深，"
    "轻微手持与缓慢推轨的连续运动。人物一律虚构演员式背影或侧脸，不还原任何真实人物肖像；"
    "画面不出现可读文字与招牌，16:9横屏，底部预留干净字幕安全区。"
)
NEGATIVE = (
    "【NEGATIVE】卡通，Q版，动漫，夸张表情，过度饱和，文字，水印，字幕，可读文字，真实姓名，真实肖像，"
    "血腥，伤口，遗体，尸体，绑缚，窒息过程，性相关内容，暴力过程，武器，畸形手指，多余肢体，"
    "人物面部崩坏，低清晰度，画面闪烁，风格突变，竖屏构图，黑边，静态图加推拉，幻灯片，拼版，伪招牌。"
)

# 角色锚点：generate.py 会把锚点原文拼到对应镜头的提示词中。TODO：按本片实际角色增删。
# 命名建议：ROLE / ROLE_BACK / ROLE_SIDE…… 每个角色一个 seed（character_seeds）。
CHARACTERS: dict[str, str] = {
    "VICTIM_BACK": "【C01锚点】虚构演员式年轻女性背影，深色齐肩发、浅色薄外套与长裙，独自走在夜街，不还原真实人物肖像",
    "VICTIM_SIDE": "【C02锚点】同一虚构演员式年轻女性的侧脸与半身，练功房把杆前的安静侧影，五官与C01保持一致，不还原真实人物肖像",
    "SUSPECT_BACK": "【C03锚点】虚构演员式中年男性背影，深灰夹克、略驼背、棒球帽压低，夜间独行，不还原真实人物肖像",
}
CHARACTER_SEEDS: dict[str, int] = {
    "VICTIM_BACK": 20150826,
    "VICTIM_SIDE": 20150827,
    "SUSPECT_BACK": 20160312,
}

# 角色代号 → 已批准参考图资产编号（与 reference/approvals.json 的键一致）。
# generate.py 按它解析每镜的 characters[] → 参考图 URL；参与全部 request_hash——
# 一旦与已烧掉的批次不一致，渲染会拒绝使用已签收片段。开工后不要随意改动。
CHARACTER_REFERENCE_IDS: dict[str, str] = {
    "VICTIM_BACK": "C01",
    "VICTIM_SIDE": "C02",
    "SUSPECT_BACK": "C03",
}

# duration, narration, visual beat, design references, character roles, camera, sound, color
# TODO：把下面 30 行改成本片内容。reference ids 对应 reference/approvals.json 里 approved 的条目；
# characters[] 里的角色名必须在 CHARACTERS 里登记；duration 为整数秒、2–13、合计必须正好 180。
ROWS = [
    # ---------------- N01（5 镜）----------------
    (6, "二零一五年八月二十六日，东京中野区一扇门后，无人应答。",
     "深夜中野区旧公寓外景，楼道口的灯忽明忽暗，门牌模糊不可读，门缝里透出一线冷光。",
     ["S03"], [], "缓慢推近楼门", "远处警笛与雨滴", "冷蓝压抑"),
    (6, "同事赶到时，二十五岁的剧团成员加贺谷理沙再没有开门。",
     "公寓走廊尽头两名同事的模糊背影停在门前，一人抬手敲门，气氛凝固。",
     ["S02"], ["VICTIM_BACK"], "过肩镜头缓慢前移", "敲门声与走廊回声", "低饱和冷灰"),
    (6, "前一天深夜，她下班回家，身后多了一个沉默的影子。",
     "雨夜街边，年轻女性背影独自沿便利店方向走远，远处一名男性背影保持距离跟随。",
     ["S01"], ["VICTIM_BACK", "SUSPECT_BACK"], "低机位跟拍推进", "雨声与远处车轮", "霓虹冷青"),
    (6, "现场没有拍到凶手的画面，只留下不属于熟人的生物痕迹。",
     "公寓玄关空镜，物证人员戴手套用棉签取样，手电光柱扫过门把手，不出现任何遗体。",
     ["S03"], [], "特写轻微横移", "胶带撕开声", "冷白法医光"),
    (6, "一串数据，把这个案子引向了附近的居民。",
     "实验室里一排排样本管被放入检测架，冷白灯下技术人员侧影低头记录。",
     ["S05"], [], "轨道缓慢横移", "仪器低鸣与键盘声", "冷白实验室调"),
    # ---------------- N02（5 镜）----------------
    (6, "警视厅逐人比对，一千五百份样本被送进实验室。",
     "宽长走廊里警员抱着样本箱快步通过，门缝下透出冷白灯光。",
     ["S05"], [], "手持跟拍微晃", "脚步声与纸张翻动", "冷青灰"),
    (6, "符合条件的那个人，就住在离她不远的地方。",
     "中野区狭窄街巷的清晨俯拍，公寓与便利店相邻，一名男性背影走入巷口。",
     ["S01"], ["SUSPECT_BACK"], "高处缓慢摇移", "清晨车流与鸟鸣", "灰蓝晨光"),
    (6, "他叫户仓高广，案发时刚刚失业，正准备返回福岛。",
     "简陋单间里行李袋靠墙放着，男性背影坐在床沿，窗帘缝隙漏进灰光。",
     ["S03"], ["SUSPECT_BACK"], "固定镜头微推", "行李拉链轻响", "灰黄褪色"),
    (6, "检测结果显示生物痕迹一致。二零一六年三月十二日，他在福岛落网。",
     "福岛街边警车旁，便衣警员一前一后带走男性背影，周围行人模糊。",
     ["S07"], ["SUSPECT_BACK"], "侧方平移跟拍", "车门闭合声", "阴天冷灰"),
    (6, "从那晚算起，追查已经过去了大约两百天。",
     "日历纸被一张张翻过的桌面特写，窗外夜色渐深，无可读数字。",
     ["S05"], [], "俯拍缓慢推近", "纸页翻动声", "暗黄台灯"),
    # ---------------- N03（5 镜）----------------
    (6, "法庭上，他承认杀人，却说只想交换联系方式。",
     "法院走廊里一名戴帽男性背影被法警带过，旁人自动让出通道。",
     ["S08"], ["SUSPECT_BACK"], "长焦侧拍缓推", "远处低语与脚步", "冷灰法庭"),
    (6, "他后来声称，自己那晚听到了恶魔的声音。",
     "被告席空镜，木质栏杆与桌面上的水杯，旁听区只留下模糊轮廓。",
     ["S08"], [], "固定机位浅景深", "椅子轻微吱呀", "低饱和冷灰"),
    (6, "可案发前，并没有能支持这种说法的鉴定记录。",
     "案卷纸页在灯下被逐页翻开，检方手指停在一段文字处，字不可读。",
     ["S05"], [], "俯拍缓慢横移", "纸页摩擦声", "冷白"),
    (6, "检方指出，跟随持续了很长一段路，并非临时起意。",
     "夜间街道监控视角，两个模糊身影前后走过路口，路面反射冷光。",
     ["S01"], ["VICTIM_BACK", "SUSPECT_BACK"], "监控定镜微推", "路灯电流声", "监控冷青"),
    (6, "二零一八年三月七日，东京地裁做出判决。",
     "东京地裁建筑外立面与阶梯，陌生人影匆匆上下，天气阴沉。",
     ["S07"], [], "低机位缓慢上摇", "远处车流", "冬日灰白"),
    # ---------------- N04（5 镜）----------------
    (6, "裁判员法庭认定的结果是：无期徒刑。",
     "法庭空镜，正中央的审判席与旁听席在冷光中安静下来，无人说话。",
     ["S08"], [], "缓慢推近空席", "空气凝滞的低频", "深灰金"),
    (6, "法官说，被夺走的是她曾经的梦想和希望。",
     "练功房里把杆与木地板空镜，晨光斜照，一双舞鞋整齐摆在角落。",
     ["S02"], ["VICTIM_SIDE"], "缓慢环绕推轨", "远处钢琴单音", "暖冷交替"),
    (6, "所谓幻听，挡不住一步步跟随的客观事实。",
     "街头灯柱下光影分界，一个人影走出光亮进入暗处。",
     ["S01"], ["SUSPECT_BACK"], "固定镜头轻微推近", "风声渐强", "明暗分割"),
    (6, "他上诉，主张自己的精神状态应当减刑。",
     "上诉材料被装进文件袋，法警在走廊尽头的门边停下。",
     ["S08"], [], "浅景深跟拍", "纸张与脚步", "阴冷灰"),
    (6, "二零一八年十二月六日，二审维持原判。",
     "高级法院外的台阶空镜，落日被云层遮住，行人稀疏。",
     ["S07"], [], "缓慢后拉", "风声与远处车流", "黄昏冷灰"),
    # ---------------- N05（5 镜）----------------
    (6, "二零一九年四月十五日，最高裁驳回上告。",
     "最高裁建筑外景，樱花树枝在风中轻晃，石阶上只有零星人影。",
     ["S07"], [], "缓慢横移", "风铃与远处车流", "淡粉灰"),
    (6, "无期徒刑，成为这起案件的最终结论。",
     "法院门厅空镜，玻璃门映出模糊人影，光线平静。",
     ["S08"], [], "静止后轻微推近", "门厅回声", "冷白"),
    (6, "从那扇没被打开的门，到这份判决，用了三年多。",
     "时间流逝蒙太奇：公寓门廊灯光从夜到晨，一个人影始终没有出现。",
     ["S03"], [], "固定延时感推轨", "时钟滴答", "冷蓝转晨灰"),
    (6, "夜路、便利店和门厅，拼出她最后一段归途。",
     "便利店玻璃门外街景，年轻女性背影从门口走过，路灯拉长影子。",
     ["S01"], ["VICTIM_BACK"], "玻璃反射跟拍", "便利店门铃轻响", "暖冷对立"),
    (6, "她的舞台梦停在二十五岁，案卷却留下一个追问。",
     "空荡排练厅里聚光灯渐暗，把杆前的身影只剩模糊轮廓。",
     ["S02"], ["VICTIM_SIDE"], "极缓慢推近", "灯光电流声", "暖黄转深蓝"),
    # ---------------- N06（5 镜）----------------
    (6, "为什么一句搭讪被拒之后，跟随会升级成侵害？",
     "夜街拐角空镜，一盏路灯忽明忽暗，行人影子被拉向不同方向。",
     ["S01"], [], "缓慢摇镜", "远处警笛渐弱", "冷蓝"),
    (6, "法院给出的答案是：这不是一时冲动，而是持续的选择。",
     "长街监控视角，两个模糊人影一前一后越走越近，画面克制无冲突。",
     ["S01"], ["VICTIM_BACK", "SUSPECT_BACK"], "监控定镜微推", "低频环境声", "监控冷青"),
    (6, "划清陌生人的边界，也是在保护每个人的归途。",
     "清晨地铁口人流，年轻人背影汇入人群，光线逐渐明亮。",
     ["S05"], ["VICTIM_BACK"], "高处缓慢俯拍", "人群低语", "清晨暖灰"),
    (6, "如果你深夜回家，发现有人一直跟在身后呢？",
     "公寓楼下仰拍镜头，年轻女性背影停下脚步回头望向空街。",
     ["S03"], ["VICTIM_BACK"], "缓慢上摇后定", "雨声与脚步停住", "冷蓝"),
    (6, "迷案解码人：看清事实，也看清安全的距离。",
     "雨后的中野街口远景，街灯渐次亮起，画面安静收束。",
     ["S01"], [], "极缓慢后拉", "环境声渐柔", "深蓝暖点"),
]

# 章节边界（start 秒, end 秒, 章名）。TODO：按解说节奏重切；章内镜头自动归章。
CHAPTER_BOUNDS = [
    (0, 30, "第一章 没有打开的门"),
    (30, 60, "第二章 一千五百份样本"),
    (60, 90, "第三章 恶魔声音之说"),
    (90, 120, "第四章 无期落槌"),
    (120, 150, "第五章 三年多的判决路"),
    (150, 180, "第六章 归途的边界"),
]

SEED_OVERRIDES: dict[int, int] = {
    # 个别镜头对种子重新抽样时登记：3: 20261020,
}

# 钩子大字（白字黑边、居中偏下 MarginV=275、每条严格 2 秒）。TODO：按本片填写；没有钩子就留 []。
HOOKS = [
    {"id": "H1", "start": 0.5, "end": 2.5, "text": "一扇没有打开的门", "style": "big_white_black_outline"},
    {"id": "H2", "start": 6.5, "end": 8.5, "text": "二十五岁舞台剧演员", "style": "big_white_black_outline"},
    {"id": "H3", "start": 30.5, "end": 32.5, "text": "一千五百份DNA样本", "style": "big_white_black_outline"},
    {"id": "H4", "start": 48.5, "end": 50.5, "text": "追查两百天后在福岛落网", "style": "big_white_black_outline"},
    {"id": "H5", "start": 66.5, "end": 68.5, "text": "他说听见恶魔的声音", "style": "big_white_black_outline"},
    {"id": "H6", "start": 90.5, "end": 92.5, "text": "裁判员法庭判无期", "style": "big_white_black_outline"},
    {"id": "H7", "start": 120.5, "end": 122.5, "text": "最高裁驳回上告", "style": "big_white_black_outline"},
    {"id": "H8", "start": 150.5, "end": 152.5, "text": "跟随不是一时冲动", "style": "big_white_black_outline"},
]

# 金色注释（MarginV=200，只补可核实事实/时间线/术语）。TODO：按本片填写；没有注释就留 []。
EXPLAINERS = [
    {"id": "E1", "start": 12.0, "end": 16.0, "text": "案发地：东京都中野区弥生町的公寓", "color": "gold"},
    {"id": "E2", "start": 42.0, "end": 46.0, "text": "2016年3月12日，嫌疑人在福岛县被捕", "color": "gold"},
    {"id": "E3", "start": 96.0, "end": 100.0, "text": "2018年3月7日，东京地裁裁判员裁判", "color": "gold"},
    {"id": "E4", "start": 132.0, "end": 136.0, "text": "2019年4月15日，最高裁驳回上告", "color": "gold"},
]

HIGHLIGHT_PHRASES = [
    "二零一五年八月二十六日", "二十五岁", "一千五百份", "二零一六年三月十二日",
    "无期徒刑", "二零一九年四月十五日", "持续的选择",
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> dict:
    cursor = 0.0
    shots = []
    for index, row in enumerate(ROWS, 1):
        duration, narration, visual, refs, roles, camera, sound, grade = row
        sid = f"S{index:02d}"
        start = cursor
        cursor += duration
        chapter = next(
            f"N{i:02d}" for i, (lo, hi, _) in enumerate(CHAPTER_BOUNDS, 1)
            if lo <= start < hi
        )
        prompt = (
            f"{visual} 真实连续运动贯穿全镜，镜头运镜：{camera}；构图保持16:9横屏，"
            "主体置于三分线，底部字幕安全区保持低干扰；不要任何文字、标签、时间戳或招牌。"
        )
        shots.append({
            "id": sid, "kind": "agnes", "start": start, "duration": duration,
            "seconds": duration, "aspect": "16:9", "source_size": "720P",
            "narration_id": chapter, "narration": narration,
            "prompt": prompt, "purpose": visual, "characters": roles,
            "seed": SEED_OVERRIDES.get(index, 20260101 + index),
            "camera": camera, "sound_design": sound,
            "color_grade": grade, "reference_ids": refs,
            "transition_in": "按本片色调方案执行的短促电影转场，不改变事实内容",
            "transition_out": "以悬念句与短暂停顿收束，环境保持微动",
        })
    if len(shots) != 30 or abs(cursor - 180) > 1e-6:
        raise AssertionError(f"Expected 30 shots / 180s, got {len(shots)} / {cursor}s")

    chapters = []
    for i, (start, end, name) in enumerate(CHAPTER_BOUNDS, 1):
        text = "".join(s["narration"] for s in shots if start <= s["start"] < end)
        chapters.append({"id": f"N{i:02d}", "title": name, "start": start,
                         "duration": end - start, "text": text})

    approvals_path = HERE / "reference" / "approvals.json"
    approvals = json.loads(approvals_path.read_text(encoding="utf-8")) if approvals_path.exists() else {"assets": {}}
    ref_images = []
    for asset_id, record in approvals.get("assets", {}).items():
        path = HERE / record.get("file", "")
        if record.get("status") == "approved" and path.is_file() and digest(path) == record.get("sha256"):
            ref_images.append({"id": asset_id, **record})
    revision_path = HERE / "reference" / "revision.txt"
    revision = revision_path.read_text(encoding="utf-8").strip() if revision_path.exists() else ""
    voice_path = HERE / "audio" / "voice.json"
    voice = json.loads(voice_path.read_text(encoding="utf-8")) if voice_path.exists() else {}
    voice_id = voice.get("voice_id") or "pending_voice_selection"

    presentation = {
        "onscreen_label": "AI动画情景重现 · 非真实影像",
        "highlight_phrases": HIGHLIGHT_PHRASES,
        "hooks": HOOKS,
        "explainers": EXPLAINERS,
        "end_title": "东京中野女演员尾随案",
        "end_subtitle": "2015 – 2019 · 从归途到判决",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "跟踪者就在身后",
        "cover_concept": "封面只从本片已生成的视频帧截取，禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "东京中野女演员尾随案：一句搭讪之后，跟踪者跟到了家门口",
        "hashtags": ["#东京中野女演员尾随案", "#日本真实案件", "#真实案件", "#案件解说", "#悬疑", "#迷案解码人"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已按公开报道交叉核实（2026-11-25）；不展示遗体、伤口与侵害过程。",
        "as_of": "2026-11-25",
        "legal_note": "一审2018-03-07东京地裁无期徒刑；二审2018-12-06维持；2019-04-15最高裁驳回上告确定。被告供述与辩护主张均标注为被告说法。",
        "sources": [
            {"publisher": "产经新闻", "date": "2015-09-10", "url": "https://www.sankei.com/article/20150910-JGJZUB25NFO2JBSVMV6YBONF54/", "supports": "案发时间地点、被害人剧团成员身份与发现经过"},
            {"publisher": "每日新闻", "date": "2018-03-07", "url": "https://mainichi.jp/articles/20180307/k00/00e/040/277000c", "supports": "一审判决与被告人身份"},
            {"publisher": "东京体育", "date": "2018-03-07", "url": "https://www.tokyo-sports.co.jp/articles/-/34025", "supports": "被告供述、幻听主张与法院否定"},
            {"publisher": "日本经济新闻", "date": "2018-03-07", "url": "https://www.nikkei.com/article/DGKKZO27814500X00C18A3CC1000/", "supports": "裁判员裁判无期与法官评语"},
            {"publisher": "产经新闻", "date": "2019-04-16", "url": "https://www.sankei.com/article/20190416-KMSRAAVETNNFDLCO3SVA4TYSN4/", "supports": "最高裁2019-04-15驳回上告、无期确定"},
        ],
        "editorial_cautions": [
            "被害人为二十五岁剧团成员、以舞台女演员为目标；片中不夸大为知名女演员。",
            "AI人物一律虚构演员式背影或侧脸，不使用真实照片，也不还原真实肖像。",
            "不展示遗体、伤口、作案工具与侵害过程；以门厅、走廊、实验室与法院空镜代替。",
            "交换联系方式与恶魔声音均为被告供述/辩护主张，必须表述为他声称。",
            "完整核查依据见 production/nakano2015/FACT_CHECK.md。",
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
            "characters": [],
            "scenes": [],
            "props": [],
            "note": "角色C01/C02/C03与场景S01/S02/S03/S05/S07/S08均由仓库既有写实风格参考图裁切复用，已登记approvals.json；人物仅为虚构演员式形象。",
        },
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期高质量放大到1080P。",
            "所有Agnes提示词由generate.py自动组合：STYLE在最前，角色锚点逐字插入，NEGATIVE在末尾；文字全部禁止AI自绘，由后期烧录。",
            "镜头每5条抽查一次人物脸和服装漂移；出现漂移则以同一批准参考图只重生成对应镜头。",
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
        "二零一五年八月二十六日，东京中野区一间公寓，二十五岁的剧团成员加贺谷理沙再也没有开门。前一天深夜，她下班回家，身后多了一个跟随者。警视厅比对约一千五百份DNA样本锁定嫌疑人；二零一八年东京地裁判无期徒刑，二零一九年最高裁驳回上告。AI动画情景重现，非真实影像；事实依据见 production/nakano2015/FACT_CHECK.md。",
        "", "## 提问读者一句话", "", "深夜回家时，如果你发现有人一直跟在身后，会第一时间怎么做？", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

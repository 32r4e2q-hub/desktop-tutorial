#!/usr/bin/env python3
"""《韩国黑寡妇案：尹相烨的四米悬崖与八亿保单》—— 唯一内容源：解说词、30 镜分镜、参考图、钩子/注释、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
流水线出处是 production/shanghai_freezer_case/build_story.py —— 一部出片、换声、重渲都跑完的成片）。

用法::

    python3 production/gapyeong2019/build_story.py            # 写 story.json + screenplay.md + 抖音脚本.md + 抖音发布文案.md

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
TITLE = "韩国黑寡妇案：尹相烨的四米悬崖与八亿保单"
BRANCH = "arena/0dca6842-desktop-tutorial"
FILM_NAME = "韩国黑寡妇案_尹相烨的四米悬崖与八亿保单_三分钟_带声音.mp4"

# 全片统一的画面风格前缀（第 1 位拼接）。TODO：把「世界描述」换成本片的地点/年代/道具；
# 后半句（人物只给虚构演员形象、无可读文字、连续运动、16:9、底部字幕安全区）是流水线规则，别删。
# 注意：style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 30 镜全部重做。
STYLE = (
    "【STYLE】照片级写实真人电影画面，二零一九年韩国京畿道加平溪谷、民宿、钓鱼场、警局与法院；"
    "35毫米胶片质感、变形宽银幕浅景深、自然皮肤与织物纹理、纪录片式克制推轨与轻微手持，"
    "冷蓝夜色与暖黄台灯交替，真实电影摄影曝光与色彩，单一连续镜头，"
    "photorealistic live-action cinematic film, 35mm anamorphic, natural skin texture, "
    "documentary crime thriller grade. 人物一律虚构演员式背影或侧脸，不还原任何真实人物肖像；"
    "画面内无任何可读文字或招牌，16:9横屏，底部预留干净字幕安全区。"
)
NEGATIVE = (
    "【NEGATIVE】anime, cartoon, animation, illustration, painting, 3D render, CG render, game engine, "
    "stylized, comic book, doll-like skin, plastic skin, oversaturated, no readable text, no subtitles, "
    "no watermark, no gore, no blood, no corpse, no body in water, no drowning struggle, no violence, "
    "no weapon closeup, no deformed hands, no extra limbs, no face distortion, no flicker, no collage, "
    "no split screen, no tiled frames, no montage, no static image"
)

# 角色锚点：generate.py 会把锚点原文拼到对应镜头的提示词中。TODO：按本片实际角色增删。
# 命名建议：ROLE / ROLE_BACK / ROLE_SIDE…… 每个角色一个 seed（character_seeds）。
CHARACTERS: dict[str, str] = {
    "WIFE_BACK": "【C01锚点】虚构演员式韩国女性背影与四分之三侧脸三十岁出头，深色及肩发与深色外套，站在溪谷边，不还原真实人物肖像",
    "LOVER_BACK": "【C02锚点】虚构演员式韩国男性背影与低垂侧脸三十岁出头，深色夹克与压低棒球帽，夜间独行，不还原真实人物肖像",
    "VICTIM_BACK": "【C03锚点】虚构演员式韩国男性背影与柔和侧影近四十岁，浅色衬衫深色长裤，站在溪流木台上，不还原真实人物肖像",
}
CHARACTER_SEEDS: dict[str, int] = {
    "WIFE_BACK": 20190630,
    "LOVER_BACK": 20220416,
    "VICTIM_BACK": 20190629,
}

# 角色代号 → 已批准参考图资产编号（与 reference/approvals.json 的键一致）。
# generate.py 按它解析每镜的 characters[] → 参考图 URL；参与全部 request_hash——
# 一旦与已烧掉的批次不一致，渲染会拒绝使用已签收片段。开工后不要随意改动。
CHARACTER_REFERENCE_IDS: dict[str, str] = {
    "WIFE_BACK": "C01",
    "LOVER_BACK": "C02",
    "VICTIM_BACK": "C03",
}

# duration, narration, visual beat, design references, character roles, camera, sound, color
# TODO：把下面 30 行改成本片内容。reference ids 对应 reference/approvals.json 里 approved 的条目；
# characters[] 里的角色名必须在 CHARACTERS 里登记；duration 为整数秒、2–13、合计必须正好 180。
ROWS = [
    # ---------------- N01（5 镜）----------------
    (6, "二零一九年六月三十日，韩国加平一处知名溪谷。",
     "黄昏的龙沼溪谷，岩壁与狭长瀑布包围一汪深潭，崖边石面残留野餐痕，冷蓝空气里飘着薄雾。",
     ["S01"], [], "缓慢推近崖边", "远处水声与风声", "冷蓝暮色"),
    (6, "晚上八点，一名三十九岁男子从崖边跃下，再没上岸。",
     "夜色中的四米岩台空镜，一盏应急灯照亮湿滑石面，崖下水潭保持安静，不出现落水者。",
     ["S01"], ["VICTIM_BACK"], "高处缓慢下摇", "远处人声被风压低", "冷蓝强对比"),
    (6, "妻子说没听见呼救，同行的朋友也这么说。",
     "岸边空地两人背影并肩站立，背对镜头望向水面，手边是收好的野餐垫。",
     ["S02"], ["WIFE_BACK", "LOVER_BACK"], "过肩镜头微推", "远处车轮声", "低饱和灰蓝"),
    (6, "警方现场勘查后，把它写成意外溺水。",
     "警员戴手套在岸边记录，手电光扫过岩石与救生圈边缘，不出现任何遗体。",
     ["S02"], [], "低机位横移", "纸笔摩擦与无线电杂音", "冷白法医光"),
    (6, "保险公司的电话，却让这页结论再也翻不过去。",
     "安静办公室里一部座机响着，桌上一叠保单文件被台灯照亮。",
     ["S03"], [], "固定镜头缓慢推近", "电话铃声与低频", "暖黄与冷蓝"),
    # ---------------- N02（5 镜）----------------
    (6, "死者身上有四份保单，死亡赔付合计约八亿韩元。",
     "桌面俯拍四份文件夹整齐排开，纸张边缘可见，具体内容不可读。",
     ["S03"], [], "俯拍缓慢横移", "纸张翻动声", "冷白档案光"),
    (6, "受益人，正是他的妻子李恩海。",
     "女性背影独自坐在夜晚窗边，玻璃映出城市灯点，她低头不说话。",
     ["S01"], ["WIFE_BACK"], "侧后方缓慢推轨", "雨打玻璃声", "暗蓝暖点"),
    (6, "更巧的是，事发时离一份保单到期只剩几个小时。",
     "保单特写被台灯照亮一页页翻过，时钟指针的剪影落在纸面上，数字不可读。",
     ["S03"], [], "浅景深横移", "时钟滴答", "暖黄压抑"),
    (6, "她却上节目哭诉，指责保险公司拒赔。",
     "电视演播室空镜，一盏聚光灯打在空着的访谈椅上，背景屏幕无可读内容。",
     ["S03"], [], "缓慢推近空椅", "摄影机低鸣", "冷白演播室"),
    (6, "拒赔的理由，是死亡时间太像被安排好的。",
     "调查员在办公桌前把时间线卡片排成一列，指尖停在其中一张。",
     ["S03"], [], "侧方缓慢跟拍", "卡片落桌轻响", "冷灰"),
    # ---------------- N03（5 镜）----------------
    (6, "重新调查后，第一件事是翻出两年前的旧账。",
     "档案室冷白灯下，一摞旧卷宗被抱到桌面，灰尘在光柱里浮动。",
     ["S03"], [], "缓慢推轨", "卷宗落桌声", "冷白档案调"),
    (6, "二零一九年二月，民宿里一顿掺了河豚毒的饭。",
     "冬季民宿房间空镜，低桌上两盒未动过的外卖餐盒与一杯水，窗帘半掩。",
     ["S06"], [], "浅景深缓慢推近", "远处取暖器嗡鸣", "冷灰黄"),
    (6, "她在聊天里问：放了这么多毒，他怎么还不死？",
     "手机屏幕朝下放在桌面，一只手停在旁边，屏幕内容不可见。",
     ["S06"], ["WIFE_BACK"], "俯拍定镜微推", "手机震动声", "暗蓝台灯"),
    (6, "五月，钓鱼场边他又被推下水，被朋友拉了回来。",
     "黄昏钓鱼场木台空镜，水面平静，几根钓竿靠在栏杆上，无人落水。",
     ["S05"], ["VICTIM_BACK"], "低机位横移", "水波与远处鸟鸣", "灰蓝暮色"),
    (6, "两次都没成功，第三次他们换了地点。",
     "车窗内视角望向山路，前方是通往溪谷的狭窄弯道，雨刷轻摆。",
     ["S01"], ["WIFE_BACK", "LOVER_BACK"], "车内固定镜头微推", "雨刷与轮胎声", "阴冷灰"),
    # ---------------- N04（5 镜）----------------
    (6, "六月底，他们来到以跳崖闻名的龙沼溪谷。",
     "白天溪谷远景，游客在浅滩驻足，峭壁投下大片阴影，画面克制无冲突。",
     ["S01"], [], "缓慢航拍推进", "溪水与人群低语", "自然冷绿"),
    (6, "同行的人里，有妻子的情人赵贤洙。",
     "男性背影站在队伍外侧，压低棒球帽，与女性背影隔着两步距离。",
     ["S01"], ["LOVER_BACK", "WIFE_BACK"], "长焦侧拍", "风声与远处笑声", "冷绿灰"),
    (6, "不会游泳的尹相烨，被反复劝上四米高的岩台。",
     "岩台边缘鞋尖与岩石纹理特写，另两人的影子落在石面上，不出现推搡动作。",
     ["S01"], ["VICTIM_BACK"], "低机位缓慢上摇", "风声渐强", "强烈明暗"),
    (6, "崖下水面，只剩一只空着的救生圈。",
     "夜色水面上橙色素色救生圈静静漂流，岸上灯光在水里碎成几条线。",
     ["S02"], [], "缓慢推近水面", "水波轻拍石岸", "冷蓝橙点"),
    (6, "法院后来认定：明知危险却没有施救，就是杀人。",
     "法庭旁听席空镜，木质长椅与栏杆在冷光中安静下来，无人说话。",
     ["S04"], [], "极缓慢推镜", "空气低频", "深灰金"),
    # ---------------- N05（5 镜）----------------
    (6, "二零二一年底，检方传唤后两人失联。",
     "夜晚公寓楼道空镜，一盏灯忽明忽暗，电梯数字屏不显示可读内容。",
     ["S03"], ["WIFE_BACK", "LOVER_BACK"], "固定镜头微推", "电梯提示音", "冷灰"),
    (6, "公开通缉十七天，他们在高阳被捕。",
     "首尔近郊车站外警车旁，便衣带走两个模糊背影，路人自动让开通道。",
     ["S04"], ["WIFE_BACK", "LOVER_BACK"], "侧方平移跟拍", "车门闭合声", "阴天冷灰"),
    (6, "二零二二年十月，一审认定不作为杀人。",
     "法院走廊里法警走过空长椅，旁听区只剩模糊轮廓。",
     ["S04"], [], "长焦侧拍缓推", "脚步回声", "冷灰法庭"),
    (6, "李恩海无期徒刑，赵贤洙有期徒刑三十年。",
     "审判席空镜，桌面木纹与水面反光，旁听席在浅景深里虚化。",
     ["S04"], [], "静止后轻微推近", "空气凝滞", "低饱和深灰"),
    (6, "检方主张的精神控制直接杀人，法院没有采纳。",
     "案卷在桌上被合上，封面文字不可读，窗外天光平静。",
     ["S03"], [], "俯拍缓慢推近", "纸页合拢声", "冷白"),
    # ---------------- N06（5 镜）----------------
    (6, "二零二三年九月二十一日，大法院驳回上告。",
     "大法院石阶与廊柱在秋日晨光中空旷安静，零星人影上下台阶。",
     ["S04"], [], "低机位缓慢上摇", "远处车流", "暖灰晨光"),
    (6, "无期与三十年成为终审结论，附加二十年电子脚镣。",
     "法院门厅玻璃门映出模糊人影，光线平静，无人停留。",
     ["S04"], [], "极缓慢后拉", "门厅回声", "冷白"),
    (6, "八亿保单没有兑现，几条命却被彻底改写。",
     "清晨溪谷空镜，水面平静，岸边野餐痕迹已被雨水冲淡。",
     ["S01"], [], "缓慢横移", "水流声渐柔", "清晨冷灰"),
    (6, "如果有人反复劝你去做害怕的事，你会听吗？",
     "岩台边缘空镜，风把一件外套吹向栏杆，画面克制无人物冲突。",
     ["S01"], [], "固定镜头轻微推近", "风声与远处水声", "冷蓝"),
    (6, "迷案解码人：看清每一次沉默的代价。",
     "雨后的溪谷远景，天光渐暗，水面映出最后一线暖色。",
     ["S01"], [], "极缓慢后拉", "环境声渐柔", "深蓝暖点"),
]

# 章节边界（start 秒, end 秒, 章名）。TODO：按解说节奏重切；章内镜头自动归章。
CHAPTER_BOUNDS = [
    (0, 30, "第一章 没被听见的呼救"),
    (30, 60, "第二章 八亿保单的倒计时"),
    (60, 90, "第三章 两次未遂"),
    (90, 120, "第四章 四米岩台"),
    (120, 150, "第五章 通缉与一审"),
    (150, 180, "第六章 终审之后"),
]

SEED_OVERRIDES: dict[int, int] = {
    # 个别镜头对种子重新抽样时登记：3: 20261020,
}

# 钩子大字（白字黑边、居中偏下 MarginV=275、每条严格 2 秒）。TODO：按本片填写；没有钩子就留 []。
HOOKS = [
    {"id": "H1", "start": 0.5, "end": 2.5, "text": "四米悬崖下的溺水迷案", "style": "big_white_black_outline"},
    {"id": "H2", "start": 6.5, "end": 8.5, "text": "妻子说没听见呼救", "style": "big_white_black_outline"},
    {"id": "H3", "start": 18.5, "end": 20.5, "text": "保险公司拒绝赔付", "style": "big_white_black_outline"},
    {"id": "H4", "start": 30.5, "end": 32.5, "text": "四份保单八亿韩元", "style": "big_white_black_outline"},
    {"id": "H5", "start": 42.5, "end": 44.5, "text": "受益人竟是妻子", "style": "big_white_black_outline"},
    {"id": "H6", "start": 60.5, "end": 62.5, "text": "两年前已有预谋", "style": "big_white_black_outline"},
    {"id": "H7", "start": 72.5, "end": 74.5, "text": "河豚毒的聊天记录", "style": "big_white_black_outline"},
    {"id": "H8", "start": 90.5, "end": 92.5, "text": "龙沼溪谷的最后一跳", "style": "big_white_black_outline"},
    {"id": "H9", "start": 102.5, "end": 104.5, "text": "空着的救生圈", "style": "big_white_black_outline"},
    {"id": "H10", "start": 120.5, "end": 122.5, "text": "传唤后人间蒸发", "style": "big_white_black_outline"},
    {"id": "H11", "start": 132.5, "end": 134.5, "text": "一审无期徒刑", "style": "big_white_black_outline"},
    {"id": "H12", "start": 150.5, "end": 152.5, "text": "最高法院终审落槌", "style": "big_white_black_outline"},
    {"id": "H13", "start": 168.5, "end": 170.5, "text": "别忽视那句激将法", "style": "big_white_black_outline"},
]

# 金色注释（MarginV=200，只补可核实事实/时间线/术语）。TODO：按本片填写；没有注释就留 []。
EXPLAINERS = [
    {"id": "E1", "start": 12.0, "end": 16.0, "text": "案发地：韩国京畿道加平郡龙沼溪谷", "color": "gold"},
    {"id": "E2", "start": 36.0, "end": 40.0, "text": "死亡保额约8亿韩元，案发时距保单到期仅数小时", "color": "gold"},
    {"id": "E3", "start": 96.0, "end": 100.0, "text": "2019年2月与5月两次杀人未遂获法院认定", "color": "gold"},
    {"id": "E4", "start": 144.0, "end": 148.0, "text": "2023年9月21日大法院终审确定", "color": "gold"},
]

HIGHLIGHT_PHRASES = [
    "二零一九年六月三十日", "八亿韩元", "四份保单", "二零一九年二月", "二零一九年五月",
    "四米高的岩台", "二零二一年底", "无期徒刑", "二零二三年九月二十一日", "沉默的代价",
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
            "color_grade": grade, "reference_ids": "+".join(refs),
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
        "end_title": "韩国黑寡妇案",
        "end_subtitle": "2019 – 2023 · 沉默的代价",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "八亿保单与四米悬崖",
        "cover_concept": "封面只从本片已生成的视频帧截取，禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "韩国黑寡妇案：尹相烨的四米悬崖与八亿保单",
        "hashtags": ["#韩国黑寡妇案", "#韩国真实案件", "#真实案件", "#案件解说", "#悬疑", "#迷案解码人"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已按韩媒、韩文百科与中文报道交叉核实（2026-11-26）；判决口径以大法院2023-09-21公开报道为准。",
        "as_of": "2026-11-26",
        "legal_note": "2023-09-21大法院驳回上告，李恩海无期徒刑、赵贤洙有期徒刑30年确定；检方主张的精神控制直接杀人未被法院采纳，法院认定的是不作为杀人。",
        "sources": [
            {"publisher": "KBS", "date": "2023-09-21", "url": "https://news.kbs.co.kr/news/pc/view/view.do?ncd=7779380", "supports": "大法院终审：无期与30年确定、直接杀人未认定"},
            {"publisher": "天地日报", "date": "2023-09-21", "url": "https://www.newscj.com/news/articleView.html?idxno=3065629", "supports": "两次杀人未遂、电子脚镣20年与不作为杀人"},
            {"publisher": "法学时报", "date": "2024-11-22", "url": "https://www.lawtimes.co.kr/news/203158", "supports": "教唆逃亡无罪与帮助犯10年确定"},
            {"publisher": "韩文维基百科", "date": "2026-11", "url": "https://ko.wikipedia.org/wiki/%EA%B0%80%ED%8F%89_%EC%9A%A9%EC%86%8C%EA%B3%84%EA%B3%A1_%EC%82%B4%EC%9D%B8_%EC%82%AC%EA%B1%B4", "supports": "案发时间地点、逮捕时间与两次未遂"},
        ],
        "editorial_cautions": [
            "片名沿用媒体标签黑寡妇，正文以公开姓名与妻子/情人表述，不渲染私生活。",
            "AI人物一律虚构演员式背影或侧脸，不使用真实照片，也不还原真实肖像。",
            "不展示遗体、伤口、溺水挣扎与推搡过程；以悬崖、水面、救生圈、保单与法庭空镜替代。",
            "精神控制直接杀人为检方主张且未被法院采纳，必须明确区分。",
            "完整核查依据见 production/gapyeong2019/FACT_CHECK.md。",
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
            "scenes": ["S01", "S02", "S03", "S04", "S05", "S06"],
            "props": [],
            "note": "C01/C02/C03为虚构演员式人物参考，S01-S06为本片AI生成的照片级写实场景参考，已登记approvals.json。",
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
        "二零一九年六月三十日晚，韩国加平龙沼溪谷，三十九岁的尹相烨从四米岩台跃下后再没上岸。最初被写成意外的溺水，直到保险公司拒赔、家属与调查节目追问，另两次杀人未遂才浮出水面。法院最终认定妻子李恩海与情人赵贤洙明知危险却不施救，构成杀人；二零二三年大法院终审分别判无期徒刑与有期徒刑三十年。AI动画情景重现，非真实影像；事实依据见 production/gapyeong2019/FACT_CHECK.md。",
        "", "## 提问读者一句话", "", "如果有人一次次劝你去做害怕的事，你会坚持说“不”吗？", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

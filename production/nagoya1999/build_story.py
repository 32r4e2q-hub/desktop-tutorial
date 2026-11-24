#!/usr/bin/env python3
"""《名古屋主妇杀害事件：丈夫守着血迹公寓二十六年，终于等来凶手落网》—— 唯一内容源。

口径时点：2026-11-24。案件已于 2026-03-05 由名古屋地检以杀人罪起诉，刑事裁判尚未开始，
因此全片对安福久美子只用「被告」或「因杀人嫌疑被逮捕并起诉」，不写判决、不写动机结论。
事实依据与来源见 FACT_CHECK.md；每一镜的旁白都要能对上该表里的条目。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "名古屋主妇杀害事件：丈夫守着血迹公寓二十六年，终于等来凶手落网"
BRANCH = "arena/dcfb6db3-desktop-tutorial"
FILM_NAME = "名古屋主妇杀害事件_丈夫守着血迹公寓二十六年，终于等来凶手落网_三分钟_带声音.mp4"

STYLE = (
    "【STYLE】日系写实悬疑纪录片质感电影动画，一九九九年日本名古屋市西区老式木造公寓与名古屋街头、警署走廊，"
    "冷青灰现实与室内暗暖钨丝灯形成暖冷对立，浅景深、强明暗对比与克制推拉运镜，"
    "人物一律以虚构演员式背影、侧脸、手部局部或剪影出现，不还原任何真实人物肖像，"
    "画面内无任何可读文字、招牌或字幕，镜头连续运动，16:9，画面底部预留字幕安全区。"
)
NEGATIVE = (
    "【NEGATIVE】no readable text, no letters, no subtitles, no watermark, no glossy advertisement look, "
    "no gore, no blood pool, no corpse, no weapon close-up, no stabbing motion, no child distress, "
    "no anime style, no idol-drama faces, no bright idyllic scenery, no deformed hands"
)

CHARACTERS = {
    "高羽悟": "四十岁上下的日本男性，短发，深色大衣或旧夹克，肩背略驼，始终以背影、侧脸或低头的手部出现，不露正脸",
    "安福": "六十多岁的日本女性，身形清瘦，深色朴素外套，低头的背影或暗处剪影，始终不露正脸",
    "刑警": "四十多岁的日本男刑警，深灰风衣，手里常拿着记事本，只出现侧脸与手部",
}

CHARACTER_SEEDS = {"高羽悟": 2501, "安福": 2502, "刑警": 2503}

CHARACTER_REFERENCE_IDS = {
    "高羽悟": ["C01"],
    "安福": ["C02"],
    "刑警": ["C03"],
}

# 记忆锚点《二十六年》在旁白里出现 9 次；下面这些词在字幕里金色加亮。
HIGHLIGHT_PHRASES = [
    "二十六年",
    "二〇二五年",
    "高羽奈美子",
    "高羽悟",
    "两千两百万日元",
    "DNA",
    "高中同班同学",
    "名古屋",
]

# 每条钩子严格 2 秒（gwangju_style.write_ass 会硬校验）。钩子在 MarginV=275，
# 与底部字幕（MarginV=62）、金色注解（MarginV=200）分层显示，必须彼此错开时间。
HOOKS = [
    {"id": "H1", "start": 0.4, "end": 2.4, "text": "一间空房，他交了二十六年房租"},
    {"id": "H2", "start": 24.4, "end": 26.4, "text": "玄关的血，不是妻子的"},
    {"id": "H3", "start": 48.4, "end": 50.4, "text": "他把月历停在一九九九年十一月"},
    {"id": "H4", "start": 72.4, "end": 74.4, "text": "十万人次警力，找了二十六年"},
    {"id": "H5", "start": 96.4, "end": 98.4, "text": "六十九岁的她，独自走进警署"},
    {"id": "H6", "start": 120.4, "end": 122.4, "text": "DNA对上了，她是丈夫的同班同学"},
    {"id": "H7", "start": 144.4, "end": 146.4, "text": "他要的不是赔偿，是一个说法"},
    {"id": "H8", "start": 162.4, "end": 164.4, "text": "二十六年，只为等一个说法"},
    {"id": "H9", "start": 168.4, "end": 170.4, "text": "血还在，人已经老了"},
]

# 金色注解只写可核实的时间线与数字，不写推测。
# 金色注解的时间段都避开钩子的 2 秒窗口，避免同一位置叠字。
EXPLAINERS = [
    {"id": "E1", "start": 40.8, "end": 44.6, "text": "2003年，专家指出：玄关血迹可能是凶手的"},
    {"id": "E2", "start": 82.0, "end": 85.8, "text": "26年房租累计约2200万日元（约合人民币100余万元）"},
    {"id": "E3", "start": 145.0, "end": 148.6, "text": "2025年10月31日，安福久美子因杀人嫌疑被逮捕"},
    {"id": "E4", "start": 169.0, "end": 172.4, "text": "2026年3月5日，名古屋地检以杀人罪起诉，尚未开庭"},
]

CHAPTERS = [
    ("第一章 停住的房间", 0, 30),
    ("第二章 玄关的秘密", 30, 60),
    ("第三章 几年之后", 60, 90),
    ("第四章 房租与传单", 90, 120),
    ("第五章 走进警署的人", 120, 150),
    ("第六章 二十六年之后", 150, 180),
]

# duration, narration, visual(唯一场景), refs, roles, camera, sound, grade
# 写法按《新题目开工手册》§3.2：一镜推进一个动作或一个判断，句首用衔接词；
# 目标口播 5.0–6.3 秒（约 20–26 个汉字，目标音色实测约 4.1 字/秒），保留半拍停顿。
ROWS = [
    (6, "这间公寓空了二十六年，房租却一个月都没断过。",
     "昏暗老式日式公寓玄关，木地板上一块深色地垫，门缝透进一线冷光，空气里浮着细尘。",
     ["S01"], [], "从门缝向玄关地面缓慢推近", "空房间的低频回响与远处车声", "冷青灰强明暗对比"),
    (6, "而一直替这间空房交房租的，是她的丈夫高羽悟。",
     "同一个玄关的另一角度，一双男式皮鞋停在垫子边缘，裤脚沾着雨水。",
     ["S01"], ["高羽悟"], "低机位横移跟拍脚步", "皮鞋踩在旧木地板上的轻响", "暗部压深、门光过曝"),
    (6, "一九九九年十一月十三日，这里还是三个人的家。",
     "名古屋市西区阴天的老式公寓外景，电线低垂，二楼走廊挂着几件没干的衣服。",
     ["S02"], [], "缓慢横摇整栋公寓外立面", "风穿过电线的呜声", "冷灰蓝、阴天低照度"),
    (6, "三十二岁的主妇高羽奈美子，在自己家里遇害。",
     "二楼走廊尽头半开的房门，门内一片暗，走廊灯管忽明忽暗。",
     ["S02"], [], "沿走廊向门口缓推", "灯管电流声与沉闷脚步", "强明暗对比"),
    (6, "她才两岁的儿子就坐在她旁边，浑身没有一处伤。",
     "昏暗室内地板一角，散落着几块彩色积木和一只小拖鞋，窗帘半掩。",
     ["S03"], [], "浅景深贴地慢慢平移", "钟表滴答与室外远处人声", "暖色残光与冷影交界"),
    (6, "桌上还摆着泡面碗和橘子皮，她原本正准备吃午饭。",
     "餐桌上的一只泡面碗与几片橘子皮，筷子搁在碗沿，椅背挂着围裙。",
     ["S03"], [], "桌面高度侧向缓慢推近", "瓷碗轻碰声", "钨丝灯暗暖"),
    (6, "玄关的血迹是B型，鞋印二十四厘米，都不是奈美子的。",
     "玄关地面局部，刑警戴手套的手把标尺放上地垫边缘，手电光柱扫过污痕。",
     ["S01"], ["刑警"], "俯拍贴地极近推进，手部特写随手电光移动", "相机快门与手套摩擦声", "冷白高反差"),
    (6, "沿着血迹，警员在洗手池和附近公园找到冲洗的痕迹。",
     "公寓外铁架楼梯与公共洗手台，水龙头还在滴水，天色已暗，路灯刚亮。",
     ["S05"], [], "沿楼梯扶手向下缓慢跟拍", "金属楼梯的回声与滴水声", "冷蓝夜色"),
    (6, "所以他们推断，凶手在打斗里受了伤，却还是逃掉了。",
     "公寓停车场的水泥地，一滩被水冲淡的印子，路灯下反着光。",
     ["S05"], [], "低角度缓慢升起", "远处汽车驶过与夜风", "冷调、局部过曝"),
    (6, "案发几年后，到访现场的专家指出：这摊血不是她的。",
     "夜晚的书房，桌上摊着放大镜与几张照片，台灯只照亮桌面一角。",
     ["S04"], [], "隔台灯光晕缓慢推近", "翻纸声与室内静默", "暗暖强对比"),
    (6, "高羽悟这才明白，凶手把自己的血留在了玄关。",
     "公寓玄关里，一道男性背影蹲下身，手悬在地面上方没有落下。",
     ["S01"], ["高羽悟"], "侧逆光中景缓缓下降", "低沉环境音与呼吸声", "暖冷交界"),
    (6, "于是他做了一个别人不理解的决定：这间房子，一直租下去。",
     "老式公寓的租房合同摊在桌上，一支笔停在纸页边缘，窗外是阴天。",
     ["S04"], ["高羽悟"], "俯拍手部缓慢平移", "笔尖轻响与远处雨声", "钨丝灯暖光压暗"),
    (6, "搬走以后，他每月照付房租，只为把现场原样留住。",
     "信箱里塞进一只信封，一只手把它抽出，背景是斑驳的公寓墙面。",
     ["S02"], ["高羽悟"], "手部特写缓慢拉开", "信箱金属摩擦声", "冷灰"),
    (6, "这样一付，就是二十六年，累计超过两千两百万日元。",
     "书桌上一叠厚厚的缴费单据，边角已经卷起，台灯照着最上面一张。",
     ["S04"], [], "俯拍纸堆缓慢推近并轻摇", "纸张摩擦声", "暗暖、浅景深"),
    (6, "二十六年来，屋里的东西几乎没动，月历停在当年十一月。",
     "墙面上一本泛黄月历，纸角卷起，旁边贴着一张褪色便签，光线偏斜。",
     ["S04"], [], "从侧面缓慢横移到月历", "纸张轻响与室内静默", "强明暗对比"),
    (6, "每年将近命日，他就在街头发传单，请路人提供线索。",
     "名古屋车站前的阴天街口，一个中年男人背影向行人递出纸页。",
     ["S05"], ["高羽悟"], "中景跟拍背影横穿人群", "街头人声与车流", "冷灰、低饱和"),
    (6, "二十六年，他把自己的脸放进每一次报道，等凶手看见。",
     "寒冷的街角，男人背影站在便利店灯箱前，雨丝斜落。",
     ["S05"], ["高羽悟"], "背身缓慢拉远", "雨声与霓虹电流声", "冷蓝夜色"),
    (6, "二〇一〇年，日本取消了杀人罪的公诉时效。",
     "警署档案室，一排排标着编号的纸箱沿着铁架延伸到暗处。",
     ["S06"], [], "沿货架缓慢推轨", "铁架轻响与脚步回声", "冷青、灯管泛白"),
    (6, "二十六年里，警方投入约十万人次警力，问过五千多人。",
     "档案室长桌，摊开的卷宗层层叠叠，一盏台灯照着密密麻麻的手写字。",
     ["S06"], ["刑警"], "俯拍缓慢下摇", "翻页声与笔尖声", "暗暖冷调混光"),
    (6, "二〇二四年，专案组把当年问过的人重新梳理，筛到几百人。",
     "白板上贴满卡片与连线，一支手把其中一张轻轻扶正，画面里没有可读文字。",
     ["S06"], ["刑警"], "侧后方浅景深推近白板", "卡片摩擦与马克笔轻响", "冷白高对比"),
    (6, "二〇二五年八月起，警方多次约谈一名六十九岁的女性。",
     "审讯室外走廊，一名年长女性低头走过的背影，墙壁是旧瓷砖。",
     ["S07"], ["安福"], "长跟拍背影", "走廊脚步回响", "冷暗压抑"),
    (6, "她起初拒绝提供DNA，只说自己什么都不知道。",
     "审讯桌上一只空水杯和一叠纸巾，对面椅子空着，冷白灯从头顶压下。",
     ["S07"], [], "桌面高度缓缓推近空椅", "日光灯嗡鸣", "冷白、高反差"),
    (6, "可到了十月三十日下午，她一个人走进了警署。",
     "警署门口的石阶，阴天，一名年长女性背影独自往上走。",
     ["S08"], ["安福"], "远景仰拍缓慢跟移", "风声与远处车流", "冷灰、阴天"),
    (6, "第二天，现场血迹的DNA比对一致，她被以杀人嫌疑逮捕。",
     "实验室玻璃后，检验台上的样本架与指示灯，冷光在玻璃上折出反光。",
     ["S08"], [], "隔玻璃浅景深推近", "仪器轻提示音", "冷青"),
    (6, "消息传开时，高羽悟等这一刻，已经整整二十六年。",
     "窗前的背影贴着玻璃，窗外是名古屋阴沉的天空。",
     ["S04"], ["高羽悟"], "侧逆光定镜缓慢推近", "电话挂断的轻响", "强明暗对比"),
    (6, "真正让他愣在原地的，是警方后来告诉他的身份。",
     "泛黄的旧校园网球场，铁丝网下空无一人，风把落叶扫过场地。",
     ["S09"], [], "广角缓慢横摇", "铁丝网在风里轻响", "冷暖交替"),
    (6, "她是他高中同班的同学，还是同一个软式网球社的队友。",
     "旧社团活动室的角落，一张褪色的合影斜靠在柜子上，画面里没有任何可读文字。",
     ["S09"], [], "浅景深微距缓缓推近", "木柜轻响与风声", "暗暖转冷"),
    (6, "学生时代，她写过一封告白信，他礼貌地拒绝了。",
     "旧书桌抽屉被拉开，一叠泛黄信纸压在最下面，窗外光线很淡。",
     ["S04"], ["高羽悟"], "俯拍抽屉缓慢推近", "木抽屉摩擦声与纸响", "暗暖"),
    (6, "二〇二六年三月，她被以杀人罪起诉，却再没有开口。",
     "名古屋地检门前的石阶，阴天里空无一人，玻璃门反着灰白的天，台阶上留着未干的水痕。",
     ["S08"], [], "广角缓慢推近石阶", "风声与远处脚步", "冷青灰"),
    (6, "如果换成你，会用二十六年守一间空房，等一个答案吗？",
     "玄关木门在暗处缓缓合上，门缝的光线收成一条线。",
     ["S01"], [], "缓慢推暗至渐黑", "关门轻响与静默", "极简暗调"),
]

assert len(ROWS) == 30, f"Expected 30 shots, got {len(ROWS)}"
assert sum(r[0] for r in ROWS) == 180, f"Expected 180s total, got {sum(r[0] for r in ROWS)}"

TITLE_START = 176.6
TITLE_END = 179.5


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
        "end_subtitle": "1999 – 2026 · 二十六年，只为等一个说法",
        "title_start": TITLE_START,
        "title_end": TITLE_END,
        "cover_text": "守着血迹的公寓",
        "cover_concept": "封面只用本片已生成视频截图；禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "丈夫租下血迹公寓二十六年，凶手竟是他的高中同班同学｜名古屋主妇杀害事件",
        "hashtags": ["#名古屋主妇杀害事件", "#真实案件", "#日本悬案", "#案件解说", "#高羽奈美子"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），单排56号大字一个逗号出一句；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已按2025年10月至2026年3月公开报道核对时间线；2026年3月5日已起诉，刑事裁判未开庭，全片不写判决与动机结论",
        "as_of": "2026-11-24",
        "legal_note": "2025年10月31日，安福久美子因现场血迹DNA型一致被爱知县警以杀人嫌疑逮捕；2026年3月5日名古屋地检以杀人罪起诉，首次公判尚未进行，依法推定无罪。",
        "sources": [
            {"publisher": "共同通信（47NEWS）", "date": "2025-11-01 前后", "url": "https://www.47news.jp/13685713.html",
             "supports": "事件经过、26年续租现场保存、房租超过2200万日元、家属表述"},
            {"publisher": "时事通信", "date": "2025-11-01", "url": "https://www.jiji.com/jc/article?k=2025110100258",
             "supports": "累计约10万人次警力、5000余人询问、DNA鉴定与10月30日出头、10月31日逮捕"},
            {"publisher": "朝日新闻", "date": "2026-03-05 / 2026-03-30", "url": "https://www.asahi.com/articles/ASV341G5QV34OIPE01MM.html",
             "supports": "鉴定留置与杀人罪起诉、家属与长男提起民事赔偿诉讼"},
            {"publisher": "读卖新闻", "date": "2026-03-05", "url": "https://www.yomiuri.co.jp/national/20260305-GYT1T00201/",
             "supports": "起诉事实与刑事责任的司法判断"},
            {"publisher": "产经新闻", "date": "2021-12-25", "url": "https://www.sankei.com/article/20211225-56ZBEHR6SBIVJCLGBYAJXXZS34/",
             "supports": "玄关血迹与24厘米鞋印、B型、受害者家属现场保存的做法"},
            {"publisher": "中日新闻", "date": "2025-11", "url": "https://www.chunichi.co.jp/article/1158842",
             "supports": "被告与被害者丈夫为高中同班同学、同属软式网球社、学生时代曾寄信送巧克力"},
        ],
        "editorial_cautions": [
            "严禁具象化呈现刺杀、大量出血或遗体画面（剧本与提示词层面已排除）",
            "2026年3月已起诉但尚未开庭：不得写判决结果，不得写动机已被证实；片中只写“警方未公布动机”",
            "不展示现场真实照片、不描摹真实人脸；AI画面一律为虚构演员式背影与局部",
            "“两千两百万日元”采用逮捕时的公开口径；后续报道出现“2300万日元以上”，片内只取较早的保守数字",
            "被告姓名与年龄用于事实叙述；其家人、邻居不作任何指名叙述",
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
            "language": "zh-CN", "target_characters_per_second": 4.1,
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
            "钩子（MarginV=275）、金色注解（MarginV=200）、底部字幕（MarginV=62）三层时间必须错开，片尾标题只在最后一镜末尾出现。",
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
        "一九九九年十一月十三日，日本名古屋市西区的一间小公寓里，三十二岁的主妇高羽奈美子在家中遇害，"
        "两岁的儿子就在旁边，没有受伤。玄关留下一处不属于她的血迹和一枚二十四厘米的鞋印。", "",
        "案发几年后，一位专家提醒她的丈夫高羽悟：那处血迹，可能是凶手留下的。从那一天起，"
        "他没有退掉这间房子。二十六年间，他照常付租、照常保存现场，累计超过两千两百万日元，"
        "墙上的月历一直停在当年十一月。", "",
        "二零二五年十月三十日，一名六十九岁的女性独自走进爱知县的警署。现场血迹的DNA比对一致，"
        "她因杀人嫌疑被逮捕——她是高羽悟高中同班的同学。二零二六年三月五日，名古屋地检以杀人罪起诉，"
        "首次开庭尚未进行，动机至今没有公布。", "",
        "AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md。", "",
        "## 提问读者一句话", "",
        "如果是你，会用二十六年守一间空房，等一个答案吗？", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

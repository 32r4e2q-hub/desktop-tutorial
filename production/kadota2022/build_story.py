#!/usr/bin/env python3
"""《门田典子案：她帮着埋了一个女人，三年后，她自己被埋进另一片土里》—— 唯一内容源。

口径时点：2026-11-24。两起案件的诉讼状态完全不同，全片必须分级表述：
  · 2019 犬饲幸子案 —— 已确定（2020-07-13 一审、2020-07-28 确定）：伤害致死无罪，弃尸与盗窃有罪。
  · 2022 门田典子案 —— 天池由佳理一、二审均懲役16年、仍在最高裁上告中；山下克己控诉已被驳回（维持28年）。
事实依据与来源见 FACT_CHECK.md；每一镜的旁白都要能对上该表里的条目。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "门田典子案：她帮着埋了一个女人，三年后，她自己被埋进另一片土里"
BRANCH = "arena/dcfb6db3-desktop-tutorial"
FILM_NAME = "门田典子案_她帮着埋了一个女人，三年后，她自己被埋进另一片土里_三分钟_带声音.mp4"

STYLE = (
    "【STYLE】日系写实悬疑纪录片质感电影动画，二〇一九至二〇二四年的日本爱知县——名古屋中区的旧公寓、"
    "荣町的深夜小巷、丰田市的山林公路、东浦町的早春农田与地方法院法庭，"
    "冷青灰现实与钨丝灯、霓虹的暗暖形成冷暖对立，浅景深、强明暗对比与克制推拉运镜，"
    "人物一律以虚构演员式背影、侧脸、手部局部或剪影出现，不还原任何真实人物肖像，"
    "画面内无任何可读文字、招牌或字幕，镜头连续运动，16:9，画面底部预留字幕安全区。"
)
NEGATIVE = (
    "【NEGATIVE】no readable text, no letters, no subtitles, no watermark, no shop signage, no kanji on signs, "
    "no gore, no blood, no corpse, no body, no plastic bag, no cord, no restraint, no strangulation, "
    "no digging, no shallow grave, no exposed skin, no sexual content, no weapon close-up, "
    "no anime style, no idol-drama faces, no deformed hands, no extra limbs, no black bars"
)

CHARACTERS = {
    "门田典子": "三十五六岁的日本女性，齐肩深色头发、发根已长出黑色，深色绗缝外套罩灰色连帽衫，肩背微驼，"
                "始终以背影或侧后方出现，不露正脸",
    "石川一代": "三十四五岁的日本女性，黑色长直发，深色素面上衣，站在门框的暗处，只有下颌边缘被逆光勾出，面部隐在阴影里",
    "天池由佳理": "三十七八岁的日本女性，头发凌乱、发梢打结，过大的深灰连帽衫，身形清瘦，坐在讯问室的金属椅上低头，不露正脸",
}

CHARACTER_SEEDS = {"门田典子": 2601, "石川一代": 2602, "天池由佳理": 2603}

CHARACTER_REFERENCE_IDS = {
    "门田典子": ["C01"],
    "石川一代": ["C02"],
    "天池由佳理": ["C03"],
}

# 记忆锚点《同一间屋子》与《三年后》各出现数次；下面这些词在字幕里金色加亮。
HIGHLIGHT_PHRASES = [
    "同一间屋子",
    "三年后",
    "伤害致死",
    "无罪",
    "缓刑四年",
    "东浦町",
    "十六年",
    "二十八年",
    "因果",
]

# 每条钩子严格 2 秒（gwangju_style.write_ass 会硬校验）。钩子在 MarginV=275，
# 与底部字幕（MarginV=62）、金色注解（MarginV=200）分层显示，必须彼此错开时间。
HOOKS = [
    {"id": "H1", "start": 0.4, "end": 2.4, "text": "三个女人，一个男人"},
    {"id": "H2", "start": 24.4, "end": 26.4, "text": "她帮着埋了朋友"},
    {"id": "H3", "start": 48.4, "end": 50.4, "text": "一句想逃，人没了"},
    {"id": "H4", "start": 72.4, "end": 74.4, "text": "伤害致死，判了无罪"},
    {"id": "H5", "start": 96.4, "end": 98.4, "text": "三年后，她也不见了"},
    {"id": "H6", "start": 120.4, "end": 122.4, "text": "十六年，二十八年"},
    {"id": "H7", "start": 144.4, "end": 146.4, "text": "同一件事，第二次"},
    {"id": "H8", "start": 156.4, "end": 158.4, "text": "她埋过人，也被人埋"},
    {"id": "H9", "start": 168.4, "end": 170.4, "text": "是因果，还是巧合？"},
]

# 金色注解只写可核实的时间线与数字，不写推测；时间段避开钩子的 2 秒窗口。
EXPLAINERS = [
    {"id": "E1", "start": 40.8, "end": 44.6, "text": "2019年2月24日清晨5:40，一名熟人拨打110"},
    {"id": "E2", "start": 82.0, "end": 85.8, "text": "2020年7月28日，该判决确定"},
    {"id": "E3", "start": 108.0, "end": 111.8, "text": "2022年4月4日，遗体在东浦町的农田中被发现"},
    {"id": "E4", "start": 150.0, "end": 153.8, "text": "一审：天池16年、山下28年；二审均维持"},
    {"id": "E5", "start": 160.0, "end": 163.8, "text": "截至2026年11月，天池仍在最高法院审理中"},
]

CHAPTERS = [
    ("第一章 同一间屋子", 0, 30),
    ("第二章 二〇一九年的冬天", 30, 60),
    ("第三章 无罪的判决", 60, 90),
    ("第四章 三年后的春天", 90, 120),
    ("第五章 两场判决", 120, 150),
    ("第六章 因果，还是巧合", 150, 180),
]

# duration, narration, visual(唯一场景), refs, roles, camera, sound, grade
# 一镜推进一个动作或一个判断，目标口播 5.0–6.3 秒（约 20–26 个汉字）。
ROWS = [
    (6, "二〇一九年，名古屋有三个女人住在同一间屋里。",
     "和室内部，低桌上并排放着三只坐垫，一只已经空了很久，旧衣柜与行李箱在背景阴影里。",
     ["S03"], ["门田典子"], "从空坐垫缓缓升起到门框", "室内低频静默与远处车声", "暗暖钨丝灯压深阴影"),
    (6, "她们在同一个夜里上班，也追着同一个男公关。",
     "深夜的荣町小巷，两侧只有发亮的空白灯箱，湿路面反着紫与琥珀的光，尽头没有人。",
     ["S04"], [], "沿巷道向纵深缓慢推轨", "远处人声与霓虹电流声", "冷青底、暖霓虹过曝"),
    (6, "其中两个早就认识，第三个是后来才搬进来的。",
     "公寓二楼走廊，晾衣杆上挂着一排衣服，日光灯管亮着，尽头一扇门半开。",
     ["S02"], ["石川一代"], "沿走廊向半开的门横移", "风穿过栏杆与灯管电流声", "冷灰蓝、单点暖光"),
    (6, "一间屋子住三个人，谁说了算，很快就分出来。",
     "和室里三只坐垫围着一张低桌，桌上一只玻璃杯与烟灰缸，衣柜边的行李箱上堆着外套。",
     ["S03"], ["门田典子"], "贴桌面高度缓慢推近低桌", "坐垫布料摩擦与钟表声", "钨丝灯暗暖"),
    (6, "后来搬进来的那个，慢慢成了被使唤的人。",
     "走廊尽头那扇门的门缝里透出一条冷白的光，地面上一双女式拖鞋朝向门内。",
     ["S02"], ["石川一代"], "低机位向门缝缓慢推近", "拖鞋轻擦地面的声音", "冷白与深黑强反差"),

    (6, "二〇一九年二月，她死在了三个人同住的屋子里。",
     "同一间和室，一只坐垫被翻倒，桌上的玻璃杯倒了，水在桌面摊开一小片。",
     ["S03"], [], "从翻倒的坐垫缓慢横移到桌面", "水滴滴落的空响", "冷调、钨丝灯忽明"),
    (6, "法医说，她是头部遭重击，造成颅内损伤。",
     "桌面上摊着一只摊开的空文件夹与一支笔，纸页是空白的，台灯只照亮这一角。",
     ["S03"], [], "俯拍文件与笔缓慢推近", "纸张摩擦与笔尖轻响", "暗暖浅景深"),
    (6, "二月四日前后，她的遗体被车运进丰田市的山里。",
     "丰田市山林里的一条窄柏油路，两侧是冬天落尽叶子的杉木，护栏与落叶，雾在树间。",
     ["S01"], [], "贴路面缓慢向前推进", "山风与远处树叶声", "冷蓝灰、低饱和"),
    (6, "二月二十四日清晨五点四十分，一个熟人报了警。",
     "公寓走廊的另一个角度，天刚亮，日光灯已经关掉，混凝土墙面泛着冷灰。",
     ["S02"], [], "固定机位缓缓横摇过墙面", "清晨鸟叫与远处广播声", "冷灰、晨光微弱"),
    (6, "第二天警方在山中找到她，两人因弃尸被捕。",
     "山林路边的路肩，落叶被压出一小片痕迹，雾气还没散，远处树影一层层淡下去。",
     ["S01"], [], "从路肩缓慢拉远至整条林道", "山风与警笛极远地掠过", "冷青、雾中过曝"),

    (6, "二〇二〇年七月，案子在名古屋地方法院宣判。",
     "法庭旁听席，一排排空着的木椅，高窗透进平板的阴天光，走廊尽头是关着的门。",
     ["S05"], [], "沿空椅背缓慢推轨向审判席", "空旷大厅的混响与翻页声", "冷中性灰蓝"),
    (6, "伤害致死这一项，法院最终判了无罪。",
     "被告席的木栏与一只立式麦克风，木面被日光灯照得发白，栏内没有人。",
     ["S05"], [], "从木栏下缘缓慢抬升到麦克风", "麦克风轻微的电流声", "冷白高反差"),
    (6, "因为唯一的直接证据，是门田自己的供述。",
     "证人席前的麦克风特写，金属杆上有一道旧划痕，背景整片虚化成灰白。",
     ["S05"], [], "浅景深贴麦克风缓慢推近", "静默中一声喉咙的清响", "冷白、浅景深"),
    (6, "可这段供述的核心部分前后不一，没被采信。",
     "旁听席最后排，一只空椅子对着空空的审判席，光从高窗斜切进来。",
     ["S05"], [], "从空椅背越过缓慢推向审判席", "木椅轻响与远处脚步", "冷灰、斜光切影"),
    (6, "成立的只有弃尸和盗窃，两人获刑，缓刑四年。",
     "法院门前的宽台阶，阴天，玻璃幕墙反着灰白的天，台阶上有未干的水痕。",
     ["S08"], [], "仰拍台阶缓慢上摇到玻璃立面", "风声与远处城市的钝响", "冷青灰、平光"),

    (6, "两年多以后的春天，门田典子自己也不见了。",
     "公寓走廊，晾衣杆上只剩两只空衣架，风把它们吹得轻轻相碰。",
     ["S02"], ["门田典子"], "背身远景缓慢拉远", "衣架相碰的金属轻响", "冷灰、阴天"),
    (6, "带走她的，是天池由佳理和山下克己。",
     "深夜巷道里，一辆深色轿车的车尾停在路灯下，尾灯熄着，路面反着湿光。",
     ["S04"], [], "从车尾缓慢横移到空无一人的巷口", "引擎冷却的滴答声", "冷青、暗部压深"),
    (6, "检方说，他们以讨债为名要钱，她拿不出来。",
     "和室低桌，桌面上一叠纸币与一部合着的手机，纸币边缘被压得整齐。",
     ["S03"], [], "俯拍纸币与手机缓慢推近", "纸币摩擦与室内静默", "暗暖、浅景深"),
    (6, "三月十五日前后，她在停放着的车里被杀害。",
     "清晨的停车场，一辆深色轿车停在最里侧，车窗蒙着一层薄雾，四周没有人。",
     ["S09"], [], "从远处缓慢推向车窗，不进入车内", "清晨的风与远处鸟叫", "冷灰蓝、车窗反光"),
    (6, "第二天，她的遗体被埋进东浦町的一片农田。",
     "早春的农田，翻过的黑土一直铺到雾里的电线杆，田间水沟结着薄水，地面平整如常。",
     ["S06"], [], "贴地面缓慢横移过整片田垄", "寒风与水沟的细响", "冷灰、低饱和"),

    (6, "案子能浮出水面，是因为两人先因别的事被捕。",
     "夜间的小警署门口，檐下的灯箱面板是空白的，玻璃门内透出冷白的光。",
     ["S07"], [], "从街对面缓慢推向玻璃门", "夜风与门内广播的模糊人声", "冷白与纯黑"),
    (6, "审讯中天池说出她的下落，四月四日遗体被找到。",
     "讯问室里，一把金属椅斜对着空桌，头顶日光灯管亮着，墙面上什么都没有。",
     ["S07"], ["天池由佳理"], "从椅背后方缓慢推近空桌", "日光灯嗡鸣与笔录纸的翻动", "冷白高反差"),
    (6, "二〇二四年三月，天池由佳理被判十六年。",
     "法庭旁听席前区，木椅被坐过又空下，扶手上搭着一件深色外套。",
     ["S05"], [], "沿椅背缓慢平移到扶手外套", "衣物布料摩擦与庭内低语", "冷灰中性"),
    (6, "同年七月，山下克己被判处有期徒刑二十八年。",
     "审判席的木质台面，上面只有一只水杯与一副眼镜，木纹在灯下显得很旧。",
     ["S05"], [], "俯拍台面缓慢推近水杯", "杯底落桌的钝响", "冷白、浅景深"),
    (6, "两人都上诉，二审维持，天池仍在上告。",
     "法院台阶，阴天的风把一张落叶推上台阶，玻璃门里空无一人。",
     ["S08"], [], "从台阶底部缓慢上摇并停住", "风声与落叶擦过石面的声音", "冷青灰"),

    (6, "把两起案子并排放，会看到一个让人不安的对称。",
     "早春农田的全景，翻过的土与远处的农舍，雾把地平线抹成一条淡线。",
     ["S06"], [], "广角固定机位缓慢横摇", "开阔田野的风声", "冷灰、极低饱和"),
    (6, "二〇一九年她帮着埋人，三年后她自己被埋。",
     "山林林道与落叶，雾从树间穿过，路面弯进看不见的地方。",
     ["S01"], [], "沿弯道缓慢向雾里推进", "山风与远处的树叶声", "冷蓝灰"),
    (6, "网上很多人说，这就是因果报应，躲不掉的。",
     "低桌上那部合着的手机，屏幕朝下，旁边是倒扣的玻璃杯。",
     ["S03"], [], "俯拍手机缓慢推近到屏幕边缘", "手机震动两声后归于安静", "暗暖、极浅景深"),
    (6, "但法庭只认证据：前案没认定致死，后案未结。",
     "法庭空景，审判席、被告席、旁听席三处都空着，高窗的光落在中央地板上。",
     ["S05"], [], "对称构图缓慢推近中央地板的光", "庭内空调的低鸣", "冷白、对称"),
    (6, "是因果，还是巧合？这一次，答案留给你。",
     "山林林道的尽头，雾把路完全吞掉，画面只剩一条灰白的去向。",
     ["S01"], [], "缓慢推入雾中直到渐黑", "风声逐渐退成静默", "冷青、渐黑"),

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
        "end_title": "东浦町女性杀人弃尸事件",
        "end_subtitle": "2019 – 2024 · 是因果，还是巧合",
        "title_start": TITLE_START,
        "title_end": TITLE_END,
        "cover_text": "她埋过人，也被人埋",
        "cover_concept": "封面只用本片已生成视频截图；禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "她帮着埋了一个女人，三年后，她自己被埋进另一片土里｜门田典子案",
        "hashtags": ["#门田典子案", "#真实案件", "#日本案件", "#案件解说", "#因果"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），单排56号大字一个逗号出一句；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已按2020年7月至2024年11月公开报道与判决报道核对；2019年案已确定，2022年案仍在上告中",
        "as_of": "2026-11-24",
        "legal_note": (
            "2019年犬饲幸子案：2020年7月13日名古屋地裁判决，伤害致死无罪，仅弃尸与盗窃成立，"
            "石川一代懲役2年8月、门田典子懲役2年，均保护观察付执行犹予4年；2020年7月28日确定。"
            "2022年门田典子案：天池由佳理一审懲役16年、二审维持、仍在最高裁上告中；"
            "山下克己一审懲役28年，控诉已被名古屋高裁驳回。两案均应表述为法院认定的事实，不作动机推断。"
        ),
        "sources": [
            {"publisher": "Reuters Japan", "date": "2020-07-28", "url": "https://jp.reuters.com/article/idJP2020072801001274",
             "supports": "伤害致死无罪确定、检方放弃上诉、判决理由（供述核心部分有变迁）"},
            {"publisher": "日本经济新闻", "date": "2020-07-28", "url": "https://www.nikkei.com/article/DGKKZO61982160Y0A720C2CE0000/",
             "supports": "同上，判决确定"},
            {"publisher": "中日新闻", "date": "2024-03-15", "url": "https://www.chunichi.co.jp/article/868913",
             "supports": "天池由佳理一审懲役16年、完全责任能力认定"},
            {"publisher": "产经新闻", "date": "2024-07-12", "url": "https://www.sankei.com/article/20240712-JQT6JXJVKJMSDK4YH7GFZ2RJ7M/",
             "supports": "山下克己一审懲役28年、天池已控诉"},
            {"publisher": "中日新闻", "date": "2024-11-25", "url": "https://www.chunichi.co.jp/article/991168",
             "supports": "山下控诉驳回、维持28年；天池一、二审均16年、上告中"},
            {"publisher": "TBS/CBC", "date": "2024-02-29", "url": "https://newsdig.tbs.co.jp/articles/cbc/1025527",
             "supports": "初公判认罪、检方主张（怕暴行败露而决定杀害）、辩方心神耗弱"},
            {"publisher": "中日新闻", "date": "2024-02-29", "url": "https://www.chunichi.co.jp/article/861083",
             "supports": "两人以讨债为名索要钱财未果"},
            {"publisher": "周刊文春", "date": "2024-07-12", "url": "https://bunshun.jp/articles/-/71839",
             "supports": "案件背景与庭审细节（其中暴力细节全片不采用）"},
        ],
        "editorial_cautions": [
            "2019年案：伤害致死判无罪是确定的判决事实，片中不得出现「她杀过人」这类表述",
            "2022年案：天池仍在最高裁上告中，只能写「一审16年、二审维持、仍在审理」，不得写「已定案」",
            "不得把2019年的逮捕写成「自首」：当时是一名熟人报警后，两人被查获",
            "不展示勒颈、塑料袋、延长线、裸体、浅埋等作案细节；一律用事后静态空镜",
            "不出现任何被害者肖像或遗体画面；犬饲幸子全程不出现形象",
            "「因果报应」只作为网络舆论现象转述，解说词不作结论，片尾把判断交回观众",
            "12万日元与7.5万日元的金额口径仅见于二手聚合站，未采用；片中不写具体欠款数额",
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
        "二〇一九年，名古屋有三个女人住在同一间屋子里，在同一个夜里上班，追着同一个男公关。"
        "那年二月，最晚搬进来的犬饲幸子死在了屋里，遗体被车运进丰田市的山中。", "",
        "二〇二〇年七月，名古屋地方法院宣判：伤害致死这一项，石川一代和门田典子都被判无罪，"
        "成立的只有弃尸和盗窃，两人获刑、缓刑四年。判决在七月二十八日确定。", "",
        "三年后，门田典子自己也不见了。二〇二二年三月，她被天池由佳理和山下克己带走；"
        "四月四日，遗体在东浦町的一片农田里被发现。这起案子之所以曝光，是因为两人先因另一起案件被捕。", "",
        "二〇二四年，天池由佳理被判有期徒刑十六年，山下克己被判二十八年；二审都维持了原判，"
        "天池至今仍在最高法院审理中。", "",
        "两起案子摆在一起，像一个让人不安的对称。网上很多人说这是因果报应——"
        "但法庭只认证据：前一起案子，她没有被认定致死；后一起案子，现在还没有结束。", "",
        "AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md。", "",
        "## 提问读者一句话", "",
        "如果因果真的存在，为什么它总是恰好落在最没有力气反抗的那个人身上？", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

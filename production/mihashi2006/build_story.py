#!/usr/bin/env python3
"""《东京街头分尸案：三桥歌织的四小时电梯》—— 唯一内容源：解说词、30 镜分镜、参考图、钩子/注释、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
流水线出处是 production/shanghai_freezer_case/build_story.py —— 一部出片、换声、重渲都跑完的成片）。

用法::

    python3 production/mihashi2006/build_story.py

写作纪律（2026-11-25 主创追加要求：去 AI 味，参照 GitHub 太上老君·AI炼丹炉）::

- 不说「不是X而是Y」「你以为X其实Y」「不只是X更是Y」这类假对比句壳；
- 不用本质上/归根结底/真正的核心是/值得注意的是/令人唏嘘这类空转词；
- 每条解说里必须有可核实的专名、时间、地点或物件（全部来自 FACT_CHECK.md）；
- 动机只写法院认定的部分（长期家暴、PTSD 影响杀意形成），不写成单一原因；
- 不展示遗体、尸块、分尸过程、凶器击打；画面只用走廊、电梯、行李箱、手推车、公园土坑空镜、法院；
- 人物一律虚构演员背影或侧脸，不还原真实肖像。
- 30 镜 × 6 秒 = 180 秒；时长只能 2–13 秒的整数；每镜一句解说，TTS 一镜一条。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "东京街头分尸案：三桥歌织的四小时电梯"
BRANCH = "arena/0dca6842-desktop-tutorial"
FILM_NAME = "东京街头分尸案_三桥歌织的四小时电梯_三分钟_带声音.mp4"

# 全片统一画面风格前缀（第 1 位拼接）。后半句（虚构演员、无可读文字、连续运动、16:9、字幕安全区）是流水线规则，别删。
# 注意：style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 30 镜全部重做。
STYLE = (
    "【STYLE】照片级写实真人电影画面，二零零六年东京涩谷与西新宿；"
    "35毫米胶片质感与轻微颗粒、变形宽银幕浅景深、自然皮肤与化纤地毯的旧纹理、"
    "纪录片式克制推轨与手持微晃，室内暖黄钨丝灯对室外冷青夜色，"
    "真实电影摄影曝光与低饱和色彩，单一连续镜头，"
    "photorealistic live-action cinematic film, 35mm anamorphic, natural skin texture, "
    "documentary crime thriller grade. 人物一律虚构演员式背影或侧脸，不还原任何真实人物肖像；"
    "画面内无任何可读文字或招牌，16:9横屏，底部预留干净字幕安全区。"
)
NEGATIVE = (
    "【NEGATIVE】anime, cartoon, animation, illustration, painting, 3D render, CG render, game engine, "
    "stylized, comic book, doll-like skin, plastic skin, oversaturated, no readable text, no subtitles, "
    "no watermark, no gore, no blood, no corpse, no body parts, no saw, no knife, no weapon closeup, "
    "no violence, no struggle, no deformed hands, no extra limbs, no face distortion, no flicker, "
    "no collage, no split screen, no tiled frames, no montage, no static image"
)

# 角色锚点：generate.py 会把锚点原文拼到对应镜头的提示词中，并按 character_reference_ids 解析参考图。
CHARACTERS: dict[str, str] = {
    "WIFE_BACK": "【C01锚点】虚构演员式日本女性背影与四分之三侧脸三十二岁，及肩深棕发、米色针织衫与深色长裤，站在公寓走廊，不还原真实人物肖像",
    "HUSBAND_BACK": "【C02锚点】虚构演员式日本男性背影与柔和侧影三十岁，短黑发、深灰西装外套，走在夜归街道，不还原真实人物肖像",
    "WIFE_FRONT": "【C03锚点】虚构演员式日本女性坐姿侧脸三十二岁，低马尾、浅灰家居服，低头看手中纸张，不还原真实人物肖像",
}
CHARACTER_SEEDS: dict[str, int] = {
    "WIFE_BACK": 20061215,
    "HUSBAND_BACK": 20061212,
    "WIFE_FRONT": 20080428,
}

CHARACTER_REFERENCE_IDS: dict[str, str] = {
    "WIFE_BACK": "C01",
    "HUSBAND_BACK": "C02",
    "WIFE_FRONT": "C03",
}

# duration, narration, visual beat, design references, character roles, camera, sound, color
ROWS = [
    # ---------------- N01 缘石上的黑袋子（0–28s）----------------
    (6, "二零零六年十二月十六日，早上八点，东京西新宿。",
     "冬日清晨的公寓外墙与山手线高架桥，路边植栽的缘石上放着一只黑色塑料袋，袋口收紧，镜头不上前，路人背影匆匆经过。",
     ["S01"], [], "低机位缓慢右移", " JR 高架列车底噪与远处清扫声", "冷青晨光"),
    (4, "有人报警：路边躺着一个假人。",
     "隔着车流长焦拍向缘石，塑料袋被风吹动一角，前景车灯拉出细长光带，路面潮湿反光。",
     ["S01"], [], "长焦压缩景深，固定微推", "车流与刹车声", "冷青与路灯暖点"),
    (6, "警察一到，警戒带围了起来。那不是假人。",
     "警戒带在风里绷紧又松弛，制服人影在不远处低身查看，镜头始终在半掩的车门后。",
     ["S01"], [], "手持轻晃，缓慢平移", "警戒带抖动与对讲机电流声", "低饱和灰蓝"),
    (6, "十二天后，涩谷一处空宅的院子里，挖出了下半身。",
     "神山町的旧木宅院门半开，院内杂草与晾衣杆，门牌字迹被刻意打虚，光线从屋檐缝隙落下。",
     ["S02"], [], "从门缝向内缓慢推进", "木门吱呀与远处犬吠", "阴天灰绿"),
    (6, "两处遗体一比对，是同一个男人。",
     "警视厅鉴定室外的走廊，磨砂玻璃后有人影晃动，实验台一角与证物袋远景虚焦。",
     ["S03"], [], "静止后轻微后拉", "荧光灯电流声", "冷白"),
    # ---------------- N02 没有手术疤的报告（28–58s）----------------
    (6, "他三十岁，在外资投行做分析师。",
     "深夜写字楼的一整排窗，只有一格还亮着，百叶窗缝隙露出办公桌与电脑的轮廓。",
     ["S05"], [], "缓慢上摇至窗面", "空调低鸣与键盘残响", "深蓝夜色"),
    (6, "去警署报失踪的，是他妻子。",
     "代代木警察署的受理窗口，木质柜台与排号机，玻璃上映出一个坐着的女性轮廓。",
     ["S04"], ["WIFE_FRONT"], "过肩固定镜头", "排号提示音与翻纸声", "日光灯冷白"),
    (6, "她写：身高一米六六，胸口有一道手术疤。",
     "报案笔录纸特写，纸面文字全部虚化成墨迹，指尖按在纸角，指节发白。",
     ["S06"], [], "俯拍微距缓慢平移", "纸张摩擦与笔尖停顿", "暖白台灯"),
    (6, "可找到的遗体上，没有那道疤。",
     "解剖室外的白瓷走廊，无影灯关闭，器械车盖着布，地面反着一条冷光。",
     ["S03"], [], "沿走廊极缓慢直推", "橡胶鞋底与通风口风声", "冷白强对比"),
    (6, "监控里，他最后一次回家，是十二月十二日清晨。",
     "公寓入口的监控画面质感走廊，深灰西装背影刷卡进门，时间是虚焦的角落，看不清脸。",
     ["S07"], ["HUSBAND_BACK"], "从他身后跟拍到电梯门合上", "刷卡提示音与门轴声", "冷灰绿"),
    # ---------------- N03 四小时电梯（58–88s）----------------
    (6, "从那天起，这栋楼再没拍到他出来。",
     "电梯轿厢内空镜，楼层数字不显示，镜面墙映出摄影机的影子，轻微抖动。",
     ["S07"], [], "轿厢内固定镜头，轻微手持", "电梯钢缆与通风声", "金属冷灰"),
    (9, "两天后，夜里十点，她拖着一只大行李箱下楼。",
     "公寓电梯口，虚构女性背影拖着行李箱进入轿厢，箱轮在地砖上留下细响。",
     ["S07"], ["WIFE_BACK"], "侧后方跟拍，随电梯门合拢收住", "箱轮滚动与门铃", "暖黄走廊灯"),
    (3, "四个小时后，她空着手回来。",
     "深夜公寓大堂，玻璃门外雨丝斜落，同一个背影推门进来，两手空空，头发被雨打湿。",
     ["S07"], ["WIFE_BACK"], "从大堂内侧向她缓慢平移", "雨声与自动门滑轨声", "冷蓝夜色"),
    (6, "十五分钟后，她又推了一辆手推车出门。",
     "地下车库坡道口，一辆折叠手推车的金属把手压下来，车轮在水泥地上压出湿痕。",
     ["S08"], [], "低机位贴着地面横移", "金属碰撞与轮胎压水", "昏黄车库灯"),
    (6, "二十分钟后，车没回来，她两手空空。",
     "车库卷帘门外，雨幕里空荡的街道，卷帘门缓缓落下一半，光被切成一条线。",
     ["S08"], [], "固定镜头，卷帘门落下", "卷帘门链条与雨声", "冷灰"),
    # ---------------- N04 铺土的新柜子（88–118s）----------------
    (6, "警方把这四个小时，一秒一秒看完。",
     "物业值班室，几台老式监视器叠着放，屏幕上只有噪点与移形换影的走廊，一只手在记录本上划线。",
     ["S08"], [], "过肩俯拍缓慢推近监视器", "录像带转动与对讲机底噪", "荧光绿屏幕光"),
    (6, "她家刚装修过。地板是新的。",
     "公寓客厅，浅色新地板反着窗光，墙角一处颜色略深，家具被推到一边，空气里有细灰。",
     ["S09"], [], "蹲低机位缓慢横移", "空房间的回声", "冷白窗光"),
    (6, "倒放的衣柜里，铺了二十袋种植土。",
     "倒放的木质衣柜，柜门拆掉，里面填满深褐种植土，土面被整片压实，边缘露出一角塑料包装。",
     ["S09"], [], "垂直俯拍缓缓下降", "布料摩擦与土的闷响", "昏暗暖褐"),
    (6, "土，和他身上的一样。",
     "证物照片摊在桌上，照片内容是土样与标签，字迹打虚，窗外天光压在纸面。",
     ["S06"], [], "微距横移掠过照片", "纸页翻动", "冷白"),
    (6, "被捕后，她把那几天全交代了。",
     "审讯室，桌面一盏台灯，虚构女性侧脸低垂，双手放在桌上，镜头只拍到她下巴以下与桌面。",
     ["S06"], ["WIFE_FRONT"], "隔着桌子固定长焦", "台灯电流与远处脚步", "低照度暖黄"),
    # ---------------- N05 十五年的判决（118–148s）----------------
    (6, "她说，那天早上他喝醉了回家。",
     "玄关，男式皮鞋一只倒着一只正着，西装外套搭在椅背，晨光从门缝切进来。",
     ["S09"], [], "低角度微距缓慢推近皮鞋", "钥匙落桌与冰箱低鸣", "冷白晨光"),
    (6, "她拿出离婚申请书。他当场撕了。",
     "餐桌上一堆撕碎的纸片，字迹不可读，一只手把碎纸往桌边推。",
     ["S06"], [], "俯拍静止后轻微推近", "纸撕裂的干脆声", "暖黄顶灯"),
    (6, "律师说，她被打了很多年，早就病了。",
     "律师会见室的隔断玻璃，虚构女性侧脸与对面模糊的西装轮廓，中间一道金属网。",
     ["S03"], ["WIFE_FRONT"], "侧面固定，玻璃反光叠影", "通风口低鸣", "冷绿"),
    (6, "二零零五年，她的鼻骨被打断，进过庇护所。",
     "庇护所走廊，一排相同的房门与塑料椅，墙角放着纸巾盒，光从高窗斜落。",
     ["S03"], [], "沿走廊缓慢前推", "门后收音机杂音", "暖灰"),
    (6, "辩方说，她当时心智丧失，应该无罪。",
     "法庭，辩护席上一叠文件被翻开，木质围栏与麦克风，背景旁听席虚化。",
     ["S10"], [], "长焦从旁听席越过人群", "翻页与咳嗽声", "冷灰法庭"),
    # ---------------- N06 重新刷过的墙（148–180s）----------------
    (6, "二零零八年四月二十八日，东京地裁宣判。",
     "法院外立面，石阶上一名背影登上台阶，天空是阴沉的均匀白。",
     ["S10"], [], "低机位缓慢上摇", "远处车流与脚步", "阴天冷白"),
    (6, "她确实幻听，看见过丈夫的影子。",
     "庭审笔录的横线纸特写，纸上只有空白的横线与装订孔，没有一处字形，台灯光从左上压下。",
     ["S11"], [], "俯拍微距缓推", "纸页与法槌落下的闷响", "冷白"),
    (6, "但法院认定：动手和善后，她全都清楚。",
     "法庭门口的走廊，法警背影推开门，走廊尽头的窗透进冬日白光。",
     ["S10"], [], "固定镜头，门开合", "门轴与脚步回声", "冷白"),
    (6, "求刑二十年，判十五年。上诉驳回，她放弃上告。",
     "高等法院外墙与围栏，风把树影吹动在石墙上，路人背影快速走过。",
     ["S10"], [], "隔着围栏长焦横移", "风声与远处广播", "阴天灰"),
    (8, "二零零五年她报过一次警。如果那次有人跟到底，会怎样？",
     "西新宿的清晨街景，高架桥下的路缘石空着，垃圾车驶过，画面渐暗。",
     ["S01"], [], "极缓慢上摇至天空", "垃圾车液压声与市声", "冷青晨光"),
]

CHAPTER_BOUNDS = [
    (0, 28, "第一章 缘石上的黑袋子"),
    (28, 58, "第二章 没有手术疤的报告"),
    (58, 88, "第三章 四小时电梯"),
    (88, 118, "第四章 铺土的新柜子"),
    (118, 148, "第五章 十五年的判决"),
    (148, 180, "第六章 重新刷过的墙"),
]

SEED_OVERRIDES: dict[int, int] = {
    # 个别镜头对种子重新抽样时登记：3: 20261020,
}

HOOKS = [
    {"id": "H1", "start": 0.4, "end": 2.4, "text": "路边躺着一个人", "style": "big_white_black_outline"},
    {"id": "H2", "start": 6.4, "end": 8.4, "text": "报警的说像个假人", "style": "big_white_black_outline"},
    {"id": "H3", "start": 10.4, "end": 12.4, "text": "少了下半身", "style": "big_white_black_outline"},
    {"id": "H4", "start": 16.4, "end": 18.4, "text": "涩谷空宅又挖出下半身", "style": "big_white_black_outline"},
    {"id": "H5", "start": 28.4, "end": 30.4, "text": "三十岁，投行分析师", "style": "big_white_black_outline"},
    {"id": "H6", "start": 34.4, "end": 36.4, "text": "报案的是他妻子", "style": "big_white_black_outline"},
    {"id": "H7", "start": 52.4, "end": 54.4, "text": "他进了电梯，再没出来", "style": "big_white_black_outline"},
    {"id": "H8", "start": 64.4, "end": 66.4, "text": "深夜十点，一只行李箱", "style": "big_white_black_outline"},
    {"id": "H9", "start": 73.4, "end": 75.4, "text": "四小时后，空手回来", "style": "big_white_black_outline"},
    {"id": "H10", "start": 76.4, "end": 78.4, "text": "又推出手推车", "style": "big_white_black_outline"},
    {"id": "H11", "start": 88.4, "end": 90.4, "text": "四个小时一秒一秒看", "style": "big_white_black_outline"},
    {"id": "H12", "start": 100.4, "end": 102.4, "text": "柜子里二十袋土", "style": "big_white_black_outline"},
    {"id": "H13", "start": 118.4, "end": 120.4, "text": "那天他喝醉了", "style": "big_white_black_outline"},
    {"id": "H14", "start": 124.4, "end": 126.4, "text": "他当场撕了离婚书", "style": "big_white_black_outline"},
    {"id": "H15", "start": 136.4, "end": 138.4, "text": "鼻骨断在二零零五年", "style": "big_white_black_outline"},
    {"id": "H16", "start": 148.4, "end": 150.4, "text": "东京地裁宣判", "style": "big_white_black_outline"},
    {"id": "H17", "start": 154.4, "end": 156.4, "text": "她确实幻听", "style": "big_white_black_outline"},
    {"id": "H18", "start": 166.4, "end": 168.4, "text": "判了十五年", "style": "big_white_black_outline"},
    {"id": "H19", "start": 172.4, "end": 174.4, "text": "那次报警，没人跟到底", "style": "big_white_black_outline"},
]

EXPLAINERS = [
    {"id": "E1", "start": 2.6, "end": 5.8, "text": "遗体发现地：新宿区西新宿七丁目，山手线高架旁", "color": "gold"},
    {"id": "E2", "start": 30.5, "end": 33.5, "text": "死者三桥祐辅，30岁，外资不动产投资公司分析师", "color": "gold"},
    {"id": "E3", "start": 58.5, "end": 62.5, "text": "2007年1月10日以死体遗弃嫌疑逮捕，同月31日再以杀人嫌疑逮捕", "color": "gold"},
    {"id": "E4", "start": 142.5, "end": 146.5, "text": "辩方以心神丧失主张无罪，一、二审均未采纳", "color": "gold"},
    {"id": "E5", "start": 166.5, "end": 170.5, "text": "2010年6月22日东京高裁驳回控诉，辩方放弃上告，刑期确定", "color": "gold"},
]

HIGHLIGHT_PHRASES = [
    "二零零六年十二月十六日", "假人", "三桥祐辅", "一米六六", "十二月十二日",
    "四个小时", "二十袋种植土", "二零零八年四月二十八日", "十五年", "二零一零年六月",
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
        "end_title": "东京街头分尸案",
        "end_subtitle": "2006 – 2010 · 四小时的空白",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "四个小时，她拖走了什么",
        "cover_concept": "封面只从本片已生成的视频帧截取，禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "东京街头分尸案：三桥歌织的四小时电梯",
        "hashtags": ["#东京街头分尸案", "#日本真实案件", "#真实案件", "#案件解说", "#悬疑", "#迷案解码人"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "已按日媒判决报道、判决旁听记与中文报道交叉核实（2026-11-25）；一审二审判决日期与刑期口径一致。",
        "as_of": "2026-11-25",
        "legal_note": "2008-04-28东京地裁判有期徒刑15年（求刑20年），认定完全责任能力；2010-06-22东京高裁驳回控诉，辩方放弃上告，刑期确定。",
        "sources": [
            {"publisher": "J-CAST新闻", "date": "2008-04-28", "url": "https://www.j-cast.com/2008/04/28019585.html", "supports": "一审15年、求刑20年与责任能力认定"},
            {"publisher": "中国日报网", "date": "2008-04-29", "url": "https://www.chinadaily.com.cn/hqbl/2008-04/29/content_6650702.htm", "supports": "一审判决与审判长表述"},
            {"publisher": "判决旁听记（一审/二审）", "date": "2010-06-22", "url": "https://blog.goo.ne.jp/xdr123/e/6bd35f21767ac88bc5fe603b1b66cbce", "supports": "二审驳回控诉、放弃上告、判决理由原文"},
            {"publisher": "事件年表", "date": "2012-08-26", "url": "https://takashun.doorblog.jp/archives/12092.html", "supports": "案发、逮捕、再逮捕与审判时间线"},
            {"publisher": "遗体发现与弃尸路线整理", "date": "2023-03-17", "url": "https://ameblo.jp/2750-0405/entry-12794019213.html", "supports": "发现地点、DNA比对与弃尸路线"},
        ],
        "editorial_cautions": [
            "年收入有三种日媒口径（1.5亿/数千万/1000万以上），成片不写具体收入。",
            "凶器报道不一，统一写「酒瓶」，不写品牌与击打次数。",
            "不展示遗体、尸块、分尸过程与凶器击打；以走廊、电梯、行李箱、手推车、土坑空镜替代。",
            "动机只写法院认定部分：长期家暴与PTSD影响杀意形成，不写成单一原因，也不写成杀人的正当理由。",
            "不使用「蛇蝎美人」「黑寡妇」类媒体标签；不使用真实照片，人物为虚构演员背影或侧脸。",
            "完整核查依据见 production/mihashi2006/FACT_CHECK.md。",
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
            "scenes": ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10", "S11"],
            "props": [],
            "note": "C01/C02/C03为虚构演员式人物参考，S01-S10为二零零六年东京的照片级写实场景参考，已登记approvals.json。",
        },
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期高质量放大到1080P。",
            "所有Agnes提示词由generate.py自动组合：STYLE在最前，角色锚点逐字插入，NEGATIVE在末尾；文字全部禁止AI自绘，由后期烧录。",
            "镜头每5条抽查一次人物脸和服装漂移；出现漂移则以同一批准参考图只重生成对应镜头。",
            "全片无BGM；旁白与字幕逐句锁定，音效/环境声只做轻量辅助，不盖住解说。",
            "解说与文案须过 editorial/check_narration.py 的去AI味预检（硬拦截为零）才能提交。",
        ],
    }
    (HERE / "story.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [
        f"# {TITLE}", "",
        "抖音横屏｜1920×1080｜16:9｜24fps｜180秒｜30个Agnes Video 2.5 Flash片段｜无BGM。",
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
        "二零零六年十二月，东京西新宿的路边发现一只黑袋子，里面是半具男尸；十二天后，涩谷一处空宅的院子里又找到下半身。DNA 比对出一条线：两处遗体属于三十岁的三桥祐辅，外资投行的分析师。报案说丈夫失踪的是他的妻子三桥歌织，可她在报告里写的身体特征，和遗体对不上。警方调出公寓监控，圈出了十二月十四日夜里那四个小时。二零零八年四月二十八日，东京地裁判她十五年；二零一零年六月，东京高裁驳回上诉，刑期确定。AI动画情景重现，非真实影像；事实依据见 production/mihashi2006/FACT_CHECK.md。",
        "", "## 提问读者一句话", "", "二零零五年她被打断鼻骨时，如果那次报警之后有人一直跟到底，二零零六年那四个小时还会发生吗？", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

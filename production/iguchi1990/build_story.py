#!/usr/bin/env python3
"""Single source of truth for the 180-second Iguchi Mariko short.

Builds story.json, screenplay.md, narration manifest and release copy. The generator
adds STYLE, the original role anchors, reference-image placeholders and NEGATIVE inline
for Agnes Video 2.5 Flash reference-mode requests.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
AUDIO = HERE / "audio"
REFERENCE = HERE / "reference"
TITLE = "井口真理子命案：她没能回家"
FILM_NAME = "井口真理子命案_她没能回家_三分钟_初剪.mp4"
BRANCH = "arena/36f9cd13-desktop-tutorial"
REPOSITORY = "32r4e2q-hub/desktop-tutorial"

# Preserve the user's requested photographic realism while making clear that these
# are fictionalized 3D reenactments, not historical footage or real-person portraits.
STYLE_PREFIX = (
    "【STYLE】Cinematic realistic 3D animation, photoreal live-action cinematography, "
    "physically based skin, cloth, wood, metal and wet-street materials; fictionalized "
    "non-identifiable actor portrayals, never real-person likenesses; Taiwanese/Japanese "
    "1990s social-crime film atmosphere, humid southern Taiwan afternoons, cold teal night, "
    "warm amber gradually shifting to deep blue, 35mm film grain, shallow depth of field, "
    "long-lens compression, restrained and humane, never sensational. Horizontal 16:9 "
    "widescreen, subject on a third line, clean lower 15 percent for subtitles. Every clip "
    "is real continuous animated footage with visible natural movement in people, cloth, "
    "wind, light, traffic, water, steam or machinery; never a still image with a fake zoom. "
    "One coherent scene from first frame to last, period-correct 1990–1993 Taiwan/Japan "
    "when applicable. No generated titles or readable text; all Chinese text is added in post. "
)

NEGATIVE_PROMPT = (
    "【NEGATIVE】cartoon, chibi, anime, exaggerated expressions, glamorized suspect, oversaturation, "
    "readable text, fake letters, subtitles, watermark, logo, blood, wound, corpse, body, "
    "human remains, bones, weapon, crossbow, knife, assault, sexual violence, nudity, "
    "dismemberment, violence process, deformed fingers, extra fingers, extra limbs, facial "
    "collapse, identity drift, modern objects in period scenes, low resolution, flicker, "
    "style drift, vertical framing, black bars, frozen frame, slideshow, still image with "
    "artificial zoom, jump scare, supernatural imagery."
)

# Exact anchor wording from the supplied brief. The additional sentence explicitly says
# that generated actors must not reproduce actual people's appearances.
CHARACTERS = {
    "C01": {
        "anchor": "【C01锚点】23岁日本女大学生,黑色及肩直发,清秀明亮,浅色短袖衬衫牛仔裤,深蓝色大旅行背包,笑容温暖",
        "identity": "A wholly fictional, non-identifiable actor; never reproduce a real photograph or person's likeness.",
        "seed": 19900401,
        "reference": "C01-mariko.png",
        "label": "井口真理子（虚构演员式形象）",
    },
    "C02": {
        "anchor": "【C02锚点】50岁台湾中年男子,黝黑圆脸,短袖衬衫,笑容朴实热情",
        "identity": "A fictionalized, non-identifiable Taiwanese man; no real-person likeness.",
        "seed": 19900402,
        "reference": "C02-lee-driver.png",
        "label": "李姓司机（虚构演员式形象）",
    },
    "C03": {
        "anchor": "【C03锚点】35岁台湾瘦削男子,短发,深色夹克,眼神游移,半脸隐于阴影,表情看似亲切",
        "identity": "A fictionalized, non-identifiable actor; keep him mostly in profile, shadow or rear view, never glamourize him, no real-person likeness.",
        "seed": 19900403,
        "reference": "C03-liu-suspect.png",
        "label": "刘学强（虚构演员式形象）",
    },
    "C04": {
        "anchor": "【C04锚点】50多岁日本中年女性,盘起短发,深色外套长裙,神情憔悴坚毅",
        "identity": "A wholly fictional, non-identifiable Japanese mother; grief remains restrained and dignified, never a real-person likeness.",
        "seed": 19900404,
        "reference": "C04-hisako.png",
        "label": "井口久子（虚构演员式形象）",
    },
    "C05": {
        "anchor": "【C05锚点】45岁台湾刑警组长,短发,深色夹克衬衫,眼神沉稳锐利",
        "identity": "A wholly fictional, non-identifiable Taiwanese detective; no real-person likeness.",
        "seed": 19910305,
        "reference": "C05-detective-leader.png",
        "label": "刑事局组长王家儒（虚构演员式形象）",
    },
    "C06": {
        "anchor": "【C06锚点】白发圆框眼镜老法医白大褂;中年华裔刑事专家深色西装",
        "identity": "Two fictionalized, non-identifiable forensic professionals; neither resembles any real person.",
        "seed": 19910306,
        "reference": "C06-forensic-team.png",
        "label": "法医与刑事专家（虚构演员式形象）",
    },
    "C07": {
        "anchor": "【C07锚点】1990至1991年台湾警察制服与便衣夹克,神情严肃",
        "identity": "Fictional Taiwanese police and civilians in period clothing; no identifiable real person and no readable badges.",
        "seed": 19910307,
        "reference": "C07-police-crowd.png",
        "label": "警察与群像（虚构演员式形象）",
    },
}

# Each reference is a single image. S02b is an additional standalone night-market reference
# because the supplied S02 requested two different locations; we do not create a collage.
REFERENCE_FILES = {
    "C01": ("character", "C01-mariko.png", "23岁日本大学生虚构形象"),
    "C02": ("character", "C02-lee-driver.png", "台南李姓司机虚构形象"),
    "C03": ("character", "C03-liu-suspect.png", "刘学强虚构侧影形象"),
    "C04": ("character", "C04-hisako.png", "母亲井口久子虚构形象"),
    "C05": ("character", "C05-detective-leader.png", "王家儒虚构形象"),
    "C06": ("character", "C06-forensic-team.png", "法医与刑事专家虚构形象"),
    "C07": ("character", "C07-police-crowd.png", "台湾警察与群像虚构形象"),
    "S01": ("scene", "S01-kaohsiung-station.png", "1990年高雄火车站大厅与出口"),
    "S02": ("scene", "S02-taoyuan-airport.png", "1990年桃园机场到达大厅"),
    "S02b": ("scene", "S02b-taipei-night-market.png", "1990年台北夜市补充场景"),
    "S03": ("scene", "S03-tainan-old-street.png", "台南老街与街角"),
    "S04": ("scene", "S04-lee-family-living-room.png", "台南司机家客厅"),
    "S05": ("scene", "S05-tainan-platform.png", "台南火车站月台"),
    "S06": ("scene", "S06-police-office-map.png", "警政署办公室与台湾地图"),
    "S07": ("scene", "S07-cemetery-cane-field.png", "夜晚公墓与甘蔗田相邻地带"),
    "S08": ("scene", "S08-xiaogang-house.png", "高雄小港老式矮房"),
    "S09": ("scene", "S09-chengqing-lake.png", "澄清湖黄昏"),
    "S10": ("scene", "S10-night-house-window.png", "夜晚台湾矮房窗口"),
    "S11": ("scene", "S11-night-road-alley.png", "凌晨公路与台南小巷"),
    "S12": ("scene", "S12-interrogation-room.png", "1991年看守所审讯室"),
    "S13": ("scene", "S13-tainan-excavation-site.png", "台南空地与树根挖掘现场"),
    "S14": ("scene", "S14-landfill.png", "垃圾掩埋场"),
    "S15": ("scene", "S15-airport-1993.png", "1993年台湾机场出口"),
    "S16": ("scene", "S16-tokyo-windowsill.png", "东京黄昏窗台"),
    "P01": ("prop", "P01-navy-backpack.png", "深蓝色大旅行背包"),
    "P02": ("prop", "P02-yellow-taxi.png", "1990年台湾黄色出租车"),
    "P03": ("prop", "P03-postcard.png", "明信片与圆珠笔"),
    "P04": ("prop", "P04-red-line-map.png", "台湾地图与红线"),
    "P05": ("prop", "P05-umbrella-flashlight.png", "雨伞与手电筒"),
}

# Review is fail-closed: a file existing is not enough to authorize an Agnes request.
# C01–C07, S01–S16 and P01–P05 were individually inspected and approved.
REFERENCE_REVIEW = {
    **{key: {"status": "approved", "note": "角色参考图已逐张检查；虚构演员式形象可用。"}
       for key in ("C01", "C02", "C03", "C04", "C05", "C06", "C07")},
    "S01": {"status": "approved", "note": "高雄车站环境图已检查；按大厅/出口使用，不宣称图中可见检票闸门。"},
    "S02": {"status": "approved", "note": "替换后为1990年代机场到达大厅：行李转盘、混凝土柱与老式时钟，无铁路/列车；背景标牌文字不清晰，生成视频仍须避免可读文字。"},
    "S02b": {"status": "approved", "note": "台北夜市环境明确、无近景可识别人脸；图片招牌有AI伪文字，视频提示已要求招牌不可读，不复现文字。"},
    "S03": {"status": "approved", "note": "台南老街建筑与年代氛围可用；出租车牌含AI伪数字，仅作为环境概念，不复现牌照；车辆连续性由独立P02道具图控制。"},
    "S04": {"status": "approved", "note": "台南家庭客厅环境合适；画框与时钟细字不作为内容，视频提示要求所有文字不可读。"},
    "S05": {"status": "approved", "note": "台南月台与旧式客车场景合适；看板不可读，生成视频不复现文字。"},
    "S06": {"status": "approved", "note": "1990年代办公室、旋转电话与台湾地图场景合适；地图标记抽象、无可读人名。"},
    "S07": {"status": "approved", "note": "墓园与甘蔗田边界明确、克制且无遗体细节；可用于环境搜索镜头。"},
    "S08": {"status": "approved", "note": "高雄小港旧式低层民宅、狭巷与生活物件符合年代氛围；无可读门牌。"},
    "S09": {"status": "approved", "note": "澄清湖水域、拱桥与南台湾植被可用；无现代天际线或可读文字。"},
    "S10": {"status": "approved", "note": "夜间旧式民宅外景及暖窗光合适；无人物或暴力内容。"},
    "S11": {"status": "approved", "note": "台南旧式夜巷空景、时代氛围合适；不复现墙面痕迹或任何可读标记。"},
    "S12": {"status": "approved", "note": "1991年空置审讯室、磁带录音机与冷色灯光合适；时钟数字与纸张内容不复现。"},
    "S13": {"status": "approved", "note": "树桩、空地与封闭工作帐篷可用；画面无遗体或遗骸，生成片段继续保持非图像化。"},
    "S14": {"status": "approved", "note": "垃圾掩埋场规模与阴沉天气可用；无遗体、遗骸或可辨识遗物。"},
    "S15": {"status": "approved", "note": "重生成后的1993机场空景无标牌和文字，作为送别环境可用。"},
    "S16": {"status": "approved", "note": "东京旧式居室窗台、花、素面陶罐与深蓝背包合适；无书写或标签。"},
    "P01": {"status": "approved", "note": "深蓝帆布旅行背包轮廓与年代合适；参考以背包本体为准，背景海报和文字不复现。"},
    "P02": {"status": "approved", "note": "1990年前后黄色轿车型出租车可用；车牌为空白，背景招牌不复现，镜头以车辆为主体。"},
    "P03": {"status": "approved", "note": "1990年代明信片与蓝色圆珠笔可用；卡片留白，无地址、邮戳或可读文字。"},
    "P04": {"status": "approved", "note": "台湾岛轮廓可辨认；红线只作抽象调查示意，不代表真实路线或具体地点。"},
    "P05": {"status": "approved", "note": "素面折伞与旧式金属手电筒年代合适；无标签、品牌或敏感内容。"},
}

SOURCES = [
    {
        "id": "SRC01",
        "title": "聯合報報時光：魂斷異鄉的日本女學生——1990年井口真理子離奇命案",
        "url": "https://time.udn.com/udntime/story/122833/6958821",
        "claims": "李姓司机送她到台南车站、1990-04-07在高雄站失踪、刘学强逮捕与供述、1991判决、1993骨灰返日；页面含联合报档案资料。",
    },
    {
        "id": "SRC02",
        "title": "NOWnews：重案回顧1／井口真理子遭分屍「頭顱」下落成謎",
        "url": "https://www.nownews.com/news/6414054",
        "claims": "1990-04-02抵台、1990-04-18返日航班未出现、1990-04-25母亲抵台、悬赏一百万、1991-03-04逮捕、3月7日供出弃尸地、3月9日挖掘、头颅搜索中止、骨骸与遗物鉴定。",
    },
    {
        "id": "SRC03",
        "title": "The News Lens：井口真理子命案（三）——警方搏感情突破心防",
        "url": "https://www.thenewslens.com/article/177730",
        "claims": "1991-03-07深夜王家儒单独长谈；刘学强承认曾编造弃尸地点；其提及唯一儿子；后续供词与垃圾车线索。",
    },
    {
        "id": "SRC04",
        "title": "The News Lens：井口真理子命案（四）——兇嫌成為台灣史上關最久的無期徒刑殺人犯",
        "url": "https://www.thenewslens.com/article/177731",
        "claims": "头颅寻找线索与掩埋场搜寻、判决与假释申请记录；申请次数按报道时间点表述。",
    },
    {
        "id": "SRC05",
        "title": "ETtoday／CTWANT：井口真理子案回顧（2022）",
        "url": "https://www.ettoday.net/news/20221021/2362785.htm",
        "claims": "旅行路线、失踪、刘学强落网与判决、头颅未寻获。画面不重现暴力过程。",
    },
    {
        "id": "SRC06",
        "title": "星岛头条：日女井口真理子游台命案，头颅36年未寻回（2026-01-03）",
        "url": "https://www.singtao.ca/7378317/2026-01-03/news-%E5%A5%87%E6%A1%88%E8%A7%A3%E5%AF%86%EF%B8%B1%E6%97%A5%E5%A5%B3%E4%BA%95%E5%8F%A3%E7%9C%9F%E7%90%86%E5%AD%90%E6%B8%B8%E5%8F%B0%E9%81%AD%E5%88%86%E5%B1%8D+%E9%A0%AD%E9%A1%B1+36%E5%B9%B4%E6%9C%AA%E5%B0%8B%E5%9B%9E++%E5%85%87%E6%89%8B%E6%88%90%E9%97%9C%E6%8A%BC%E6%9C%80%E9%95%B7%E6%AE%BA%E4%BA%BA%E7%8A%AF/?variant=zh-cn&appedition=vancouver",
        "claims": "截至2026年初，头颅仍未寻获；刘学强仍服刑。发布前应再次确认是否有新报道。",
    },
    {
        "id": "SRC07",
        "title": "The News Lens：井口真理子命案（一）——独自来台旅游却就此渺无音讯",
        "url": "https://www.thenewslens.com/article/177728",
        "claims": "1990年旅程与李姓司机接待等案件背景。与其他来源时间不一致处不写具体日。",
    },
    {
        "id": "SRC08",
        "title": "Yahoo新闻：井口真理子命案（二）一碗面一个证人（2026-02-12）",
        "url": "https://tw.news.yahoo.com/%E4%BA%95%E5%8F%A3%E7%9C%9F%E7%90%86%E5%AD%90%E5%91%BD%E6%A1%88-2-%E4%B8%80%E7%A2%97%E9%9D%A2-%E4%B8%80%E5%80%8B%E8%AD%89%E4%BA%BA-%E8%AE%93%E6%B2%89%E5%AF%82-010600042.html",
        "claims": "报道3月7日供述、3月9日挖掘与假释申请；将供述和报道口径明确归因，不把申请次数当作2026年最新统计。",
    },
]

CHAPTERS = [
    ("N01", "车站的背影", 0, 10, ["S01", "S02"]),
    ("N02", "独自旅行", 10, 25, ["S03", "S04", "S05", "S06"]),
    ("N03", "人间蒸发", 35, 25, ["S07", "S08", "S09", "S10"]),
    ("N04", "母亲与搜寻", 60, 25, ["S11", "S12", "S13", "S14"]),
    ("N05", "嫌犯落网", 85, 23, ["S15", "S16", "S17", "S18"]),
    ("N06", "反复供词与核查", 108, 22, ["S19", "S20", "S21", "S22"]),
    ("N07", "审讯突破", 130, 20, ["S23", "S24", "S25"]),
    ("N08", "挖掘与遗憾", 150, 18, ["S26", "S27", "S28"]),
    ("N09", "她没能回家", 168, 12, ["S29", "S30"]),
]

# Each shot has a single spoken sentence, a distinct camera move, tangible continuous
# motion, and only the reference images explicitly listed for that shot.
SHOTS = [
    {
        "id": "S01", "start": 0, "duration": 5, "narration_id": "N01",
        "camera": "长焦背影跟拍，末秒停在空荡的车站大厅",
        "characters": ["C01"], "references": ["S01", "C01", "P01"],
        "narration": "她走出高雄车站，随后失去行踪，亲友再无音讯。",
        "prompt": "At noon on 7 April 1990, inside the Kaohsiung railway station concourse. A fictional young Japanese woman wearing a pale blouse, jeans and a large deep navy backpack walks from the busy hall toward the street-side exit, briefly glancing over her shoulder. Commuters flow past until her back disappears beyond the exit and the camera holds on the now-empty concourse. Camera: long-lens tracking from behind at walking speed, ending in a gentle hold. Real motion: crowd streams naturally, backpack straps swing, sunlight and dust drift. No gate or train is required; no readable signs.",
        "sfx": ["车站广播", "人群与脚步", "末拍抽离"],
    },
    {
        "id": "S02", "start": 5, "duration": 5, "narration_id": "N01",
        "camera": "雨中缓慢推近母亲手里的照片",
        "characters": ["C04", "C07"], "references": ["S06", "C04", "C07"],
        "narration": "离开车站后，她去了哪里？这个疑问，至今未解。",
        "prompt": "Outside a Taiwanese police-station entrance on a rainy 1990 afternoon. A fictional Japanese mother in a dark coat holds a blurred photograph of her daughter, bows deeply toward officers just inside the doorway, then slowly raises her face with reddened but controlled eyes. Camera: restrained slow push-in from medium shot to the photograph and her hands. Real motion: steady rain, coat fabric, water running down the doorway. No dialogue text, no visible tears exaggerated for drama.",
        "sfx": ["雨声", "警局内模糊电话铃"],
    },
    {
        "id": "S03", "start": 10, "duration": 7, "narration_id": "N02",
        "camera": "手持中景跟拍，轻微横移",
        "characters": ["C01"], "references": ["S02", "C01", "P01"],
        "narration": "一九九〇年四月，她带着期待独自飞来台湾，展开一段毕业旅行。",
        "prompt": "A single scene in the 1990 Taoyuan airport arrivals hall. A fictional 23-year-old Japanese university student pulls a modest suitcase, wears a large navy travel backpack and looks curiously across the glass-roofed terminal while other travelers pass. Camera: gentle handheld medium follow from her left, with natural human pace. Real motion: luggage wheels roll, travelers cross, sunlight shifts through the glass roof. Keep every sign blank and unreadable; no modern phone or screen.",
        "sfx": ["机场广播", "行李滚轮声"],
    },
    {
        "id": "S04", "start": 17, "duration": 7, "narration_id": "N02",
        "camera": "夜市中景手持横移",
        "characters": ["C01"], "references": ["S02b", "C01"],
        "narration": "夜市灯火暖，人声渐远，她把旅途见闻写进明信片，记下此刻心情。",
        "prompt": "One continuous 1990 Taipei night-market alley. The young traveler tastes a small snack, gestures politely with a vendor and smiles, then writes in a tiny travel notebook at a stall counter. Camera: natural handheld medium lateral move, settling on her writing hand while keeping her face on a third line. Real motion: steam rises, vendors move, crowd flows behind her, neon reflections shimmer. All stall lettering remains abstract and unreadable.",
        "sfx": ["夜市叫卖", "油锅滋滋声", "笔尖划纸"],
    },
    {
        "id": "S05", "start": 24, "duration": 6, "narration_id": "N02",
        "camera": "台南街角侧向中景",
        "characters": ["C01", "C02"], "references": ["S03", "C01", "C02", "P02"],
        "narration": "来到台南后，李姓司机热心接待她，也邀请她到家中借宿。",
        "prompt": "A single late-afternoon street corner in old Tainan, 1990. Red brick and a temple lantern frame the street. A yellow taxi is parked at the curb; a fictional middle-aged local driver steps out, smiles kindly and gestures toward the old street as the young traveler listens. He offers to help with her backpack without pulling or grabbing her. Camera: lateral medium two-shot, keep the two people separated by comfortable space. Real motion: lantern sways, taxi idles, warm humid light flickers through leaves. No readable signs or license text.",
        "sfx": ["出租车发动机", "远处庙钟"],
    },
    {
        "id": "S06", "start": 30, "duration": 5, "narration_id": "N02",
        "camera": "缓慢移向明信片特写",
        "characters": ["C01", "C02"], "references": ["S04", "C01", "C02", "P03"],
        "narration": "在台南，她提笔写下旅途见闻，向家人报平安。",
        "prompt": "Inside a modest Tainan family living room at golden dusk. A small electric fan turns slowly, fruit rests on a low table, and a fictional local family member sets down a plate. The student sits at the wooden table and writes a postcard with a ballpoint pen while the kind driver listens nearby. Camera: calm medium shot that glides toward the postcard, whose writing is only abstract marks. Real motion: fan blades turn, curtain breathes, pen moves. No legible writing.",
        "sfx": ["电风扇声", "笔尖划纸声"],
    },
    {
        "id": "S07", "start": 35, "duration": 7, "narration_id": "N03",
        "camera": "月台长焦跟拍后缓慢拉远",
        "characters": ["C01", "C02"], "references": ["S05", "C01", "C02", "P01"],
        "narration": "四月七日清晨，李先生送她上车，她挥手道谢，车站一切如常。",
        "prompt": "On the 1990 Tainan station platform in bright morning sun, the fictional driver carefully helps lift the navy backpack onto the train step. The young woman bows in thanks and boards; he waves as the period passenger train begins to roll away. Camera: long platform view, slowly pulling back as the train leaves the frame. Real motion: train wheels move, clothing and hair stir in the breeze, steam drifts. No readable station signs.",
        "sfx": ["列车汽笛", "月台广播", "车轮渐远"],
    },
    {
        "id": "S08", "start": 42, "duration": 7, "narration_id": "N03",
        "camera": "车窗内近景，稻田光影流动",
        "characters": ["C01"], "references": ["S05", "C01", "P03"],
        "narration": "车窗外稻田不断后退，她手里仍握着明信片，沿途光影掠过窗边。",
        "prompt": "Inside a moving 1990 passenger train, a close three-quarter view of the fictional young traveler seated beside the window. She holds a postcard in one hand and watches rice fields and palm trees slide past outside. Camera: gentle interior tracking move parallel to the window, no zoom-only movement. Real motion: landscape parallax, window reflections travel across her face, paper corner flutters in the air from the vent. No readable text on the postcard.",
        "sfx": ["列车行驶声", "铁轨节奏"],
    },
    {
        "id": "S09", "start": 49, "duration": 6, "narration_id": "N03",
        "camera": "中景缓慢推近，转头时硬切黑",
        "characters": ["C01"], "references": ["S01", "C01", "P02"],
        "narration": "中午，她离开高雄车站；此后行踪，公开资料难以确认。",
        "prompt": "At noon outside the 1990 Kaohsiung railway station exit, the young traveler steps out, stops and looks around as if searching for a familiar face. A yellow taxi passes slowly in the far background but does not stop or approach her. Camera: measured medium push-in, ending on her turning profile and a clean hard cut to black. Real motion: crowd and distant traffic move naturally. Do not show what happens after she turns; no readable signs.",
        "sfx": ["车站嘈杂", "切黑时声音骤停"],
    },
    {
        "id": "S10", "start": 55, "duration": 5, "narration_id": "N03",
        "camera": "柜台名单特写缓慢下移",
        "characters": [], "references": ["S02"],
        "narration": "原定四月十八日返日，她没有登上那班飞机。",
        "prompt": "A single 1990 airport check-in counter in cool gray light. A blank boarding pass lies beside a clerk's paper passenger list; the clerk checks the page, pauses and looks toward the quiet arrivals hall as no traveler appears. Keep every mark abstract and unreadable; do not imply a cancellation or give an airline name. Camera: close overhead move slowly down toward the unmarked passenger list. Real motion: paper edges lift in air from a fan. No legible text, dates, logos or modern screens.",
        "sfx": ["柜台键盘声", "低声交谈"],
    },
    {
        "id": "S11", "start": 60, "duration": 7, "narration_id": "N04",
        "camera": "机场手持中景跟拍",
        "characters": ["C04", "C07"], "references": ["S02", "C04", "C07"],
        "narration": "四月二十五日，母亲久子飞抵台湾，带着照片四处寻找女儿下落。",
        "prompt": "At a 1990 Taiwanese airport arrival hall, a fictional Japanese mother steps out carrying a small suitcase and a blurred photograph. A liaison worker and a police officer approach; she bows deeply, then raises her head and scans the crowd. Camera: restrained handheld medium follow. Real motion: travelers pass behind her, suitcase wheels roll, sunlight shifts across the floor. No identifiable faces, no readable signage.",
        "sfx": ["机场广播", "行李脚步声"],
    },
    {
        "id": "S12", "start": 67, "duration": 7, "narration_id": "N04",
        "camera": "办公室中景缓慢推向地图",
        "characters": ["C04", "C07"], "references": ["S06", "C04", "C07", "P04"],
        "narration": "久等不到女儿返日的消息，警方成立专案；她把希望交给警方。",
        "prompt": "Inside a 1990 police investigation office, the mother hands a blurred photograph to two fictional officers. One officer pins an unlabelled Taiwan map with small red markers around Tainan and Kaohsiung; an old rotary telephone rings on the desk. Camera: slow push from the mother's hands to the map. Real motion: paper turns, telephone cord trembles, a desk fan moves smoke. All labels and photo details stay unreadable.",
        "sfx": ["电话铃声", "翻纸声"],
    },
    {
        "id": "S13", "start": 74, "duration": 6, "narration_id": "N04",
        "camera": "过肩缓慢推近，笔记本合上",
        "characters": ["C02", "C07"], "references": ["S12", "C02", "C07"],
        "narration": "据报道，最后见过她的李姓司机被反复询问，核实后获释。",
        "prompt": "In a cool gray 1990 police interview room, the fictional Tainan driver sits tired but composed across from a detective. A blank map and abstract itinerary sheets lie between them; he answers with measured gestures. The officer finally closes a notebook and motions toward the door, releasing him. Camera: over-the-shoulder slow push, then hold on the closed notebook. Real motion: hands move, chair shifts, fluorescent light softly hums. No legible writing.",
        "sfx": ["椅子摩擦", "笔记本合上"],
    },
    {
        "id": "S14", "start": 80, "duration": 5, "narration_id": "N04",
        "camera": "快速蒙太奇，手持搜索后定格空地",
        "characters": ["C04", "C07"], "references": ["S07", "C04", "C07"],
        "narration": "墓园与甘蔗田一次次搜过，仍没有她的消息。",
        "prompt": "A fast but readable montage of three non-graphic search images, all at night in southern Taiwan: flashlight beams sweep along a cemetery path, police search a sugarcane-field edge with a dog, then a fictional mother waits at a distant cordon and lowers her gaze. Never show a body, covered shape or remains. Camera: short handheld pans with clean match cuts, ending on a still, empty path. Real motion: cane leaves wave, flashlight beams move, dog walks naturally.",
        "sfx": ["铁锹与脚步", "远处犬吠", "夜风"],
    },
    {
        "id": "S15", "start": 85, "duration": 6, "narration_id": "N05",
        "camera": "清晨中景，包围后缓慢横移",
        "characters": ["C03", "C07"], "references": ["S08", "C03", "C07", "P02"],
        "narration": "一九九一年三月四日，警方在高雄将刘学强逮捕归案。",
        "prompt": "At dawn on 4 March 1991 outside a modest Xiaogang house, fictional police quietly form a perimeter. A yellow taxi is parked by the gate. A lean fictional man steps out, notices the officers and stops; his expression shifts from surprise to guarded stillness. Camera: medium lateral move, no physical struggle and no weapon. Real motion: laundry and branches move, birds lift from the roofline. Keep the suspect in side view and half-shadow.",
        "sfx": ["脚步声", "短促警哨", "晨鸟惊飞"],
    },
    {
        "id": "S16", "start": 91, "duration": 6, "narration_id": "N05",
        "camera": "车站街角中景缓慢推近",
        "characters": ["C03", "C01"], "references": ["S01", "C03", "C01", "P02"],
        "narration": "供述称，他在车站看见独自一人的她，随后主动上前搭话。",
        "prompt": "A carefully fictionalized flashback on a 1990 street outside Kaohsiung station. A lean man in a dark jacket approaches the young traveler at a respectful distance and gestures toward a blank note, while a yellow taxi remains parked far behind as a recurring motif, not a ride. Camera: medium two-shot, slow push that stops before their personal space closes. Real motion: pedestrians pass, taxi lights flicker softly, paper moves in the breeze. No readable writing, no coercion, no touch.",
        "sfx": ["车窗轻响", "远处街声"],
    },
    {
        "id": "S17", "start": 97, "duration": 6, "narration_id": "N05",
        "camera": "澄清湖长焦缓慢横移",
        "characters": ["C03", "C01"], "references": ["S09", "C03", "C01"],
        "narration": "据刘学强供述，白天他带她游览景点，逐渐取得她的信任。",
        "prompt": "At Chengcing Lake near sunset, the fictional young traveler takes a photograph of the water and smiles. The lean man walks beside her but keeps glancing away toward the path. Camera: long-lens slow lateral track, hold both figures on separate thirds. Real motion: lake ripples, leaves move in the breeze, camera shutter flashes once. The warm gold light gradually cools toward teal. No romantic framing.",
        "sfx": ["湖面微风", "相机快门", "远处蝉鸣"],
    },
    {
        "id": "S18", "start": 103, "duration": 5, "narration_id": "N05",
        "camera": "低机位缓推窗口，灯灭后停住",
        "characters": [], "references": ["S10"],
        "narration": "据供述，那一夜屋里灯光熄灭；镜头只停在门外。",
        "prompt": "Exterior of a modest Taiwanese low house at night. A single warm window glows; the light slowly goes out and the curtain closes. A stray dog stands far outside and gives one low bark. Camera: low, slow move toward the window, stopping outside the wall. Real motion: curtain, leaves, dog and dim light. No person is visible and the camera never enters the house.",
        "sfx": ["野狗低吠", "灯熄啪声", "随后静寂"],
    },
    {
        "id": "S19", "start": 108, "duration": 6, "narration_id": "N06",
        "camera": "门缝视角，剪影与背包缓慢移入",
        "characters": ["C03"], "references": ["S10", "C03", "P01"],
        "narration": "那只深蓝色大背包，也在此后失去踪影，镜头停在空房间。",
        "prompt": "From outside a half-closed doorway before dawn, a fictional male silhouette moves across a dim room. A deep navy travel backpack is lifted briefly, set down beside a chair and then carried out of view; no person or body is seen inside. Camera: narrow door-gap point of view, slow restrained creep forward. Real motion: silhouette crosses, bag straps sway, a weak bulb trembles. Keep the scene non-graphic and ambiguous; no forced action.",
        "sfx": ["轻微脚步", "背带摩擦"],
    },
    {
        "id": "S20", "start": 114, "duration": 6, "narration_id": "N06",
        "camera": "车内视角缓慢推向后视镜",
        "characters": ["C03"], "references": ["S11", "C03", "P02"],
        "narration": "黄色出租车驶过空巷，警方仍在追查反复变化的供词。",
        "prompt": "A symbolic, empty 1991 southern Taiwan road before dawn. A yellow taxi rolls slowly through wet streets with no passenger and nothing visible in the back seat. In the rear-view mirror only the fictional driver's guarded eyes appear briefly. Camera: fixed interior view with a slow move toward the mirror. Real motion: road lights slide across glass, windshield reflections move, taxi travels at a steady pace. Do not imply a specific transport route or show any bags or body.",
        "sfx": ["引擎声", "车窗外风声"],
    },
    {
        "id": "S21", "start": 120, "duration": 5, "narration_id": "N06",
        "camera": "凌晨小巷远景缓慢推近",
        "characters": ["C03"], "references": ["S11", "C03"],
        "narration": "他反复改口，警车驶向错误地点，搜寻仍无结果。",
        "prompt": "A quiet Tainan alley at 3 a.m. A lean fictional man steps out beneath one amber streetlamp, looks left and right, then turns away and disappears into the cool blue darkness. Keep the alley empty, no object is left behind. Camera: distant slow push, ending on the empty pool of light. Real motion: damp pavement glints, a hanging cable moves, thin night mist crosses frame. No grin or threatening gesture.",
        "sfx": ["车门远声", "夜风"],
    },
    {
        "id": "S22", "start": 125, "duration": 5, "narration_id": "N06",
        "camera": "快速闪回三切，红线绷紧后定格",
        "characters": ["C07"], "references": ["S06", "C07", "P04"],
        "narration": "供词指向多个地点，警方只能逐一核对线索。",
        "prompt": "A restrained three-beat investigation montage: fictional officers compare two blank, unlabelled paper maps; a detective traces a route with a pencil, then pauses to compare it with a neutral evidence folder. A thin red string is moved from one anonymous point to another and finally laid flat, not aimed at any named person. Camera: clean match cuts ending in a steady overhead view of the map and notebook. Real motion: pencil moves, paper turns, the red string settles. No readable text, no accusation of an innocent person.",
        "sfx": ["倒带般低鸣", "红线轻绷声"],
    },
    {
        "id": "S23", "start": 130, "duration": 7, "narration_id": "N07",
        "camera": "审讯室中景缓慢环绕",
        "characters": ["C03", "C07"], "references": ["S12", "C03", "C07"],
        "narration": "三月七日深夜，组长王家儒独自留下，准备换一种方式谈，静待突破。",
        "prompt": "Inside a 1991 detention-center interview room, the fictional suspect sits at a metal table with a detective and a quiet note-taker. He shifts his gaze between several blank location cards; the recorder's reel turns while the note-taker's pen stops, then resumes. Camera: slow partial orbit at seated eye level, never an aggressive angle. Real motion: hands, paper edge, recorder reel and breathing. Cool gray practical light; no legible writing.",
        "sfx": ["录音机转动", "纸笔声", "手铐轻碰桌面"],
    },
    {
        "id": "S24", "start": 137, "duration": 7, "narration_id": "N07",
        "camera": "车内延时，雨刷与路灯快速掠过",
        "characters": ["C07"], "references": ["S11", "C07"],
        "narration": "据报道，警车在台南与高雄之间奔波一夜，天色渐亮仍屡屡扑空。",
        "prompt": "A continuous interior view from a period police car traveling between Kaohsiung and Tainan at night. Tired fictional officers sit in front; headlights, wet road and streetlamps pass by the windows. Use a restrained in-camera time-lapse effect as the windshield wipers sweep and the sky slowly lightens, without changing location abruptly. Real motion: wipers, road reflections, subtle breathing. No readable dashboard text or modern equipment.",
        "sfx": ["雨刷声", "引擎声", "时钟加速"],
    },
    {
        "id": "S25", "start": 144, "duration": 6, "narration_id": "N07",
        "camera": "两人近景缓慢推近，天色渐亮",
        "characters": ["C05", "C03"], "references": ["S12", "C05", "C03"],
        "narration": "据报道，谈到唯一的儿子，他沉默许久，终于说出地点。",
        "prompt": "Late night in the same fully described 1991 interrogation room, with only the fictional detective leader and suspect present. A cup of cold tea sits between them. The detective speaks calmly, then waits; the suspect lowers his eyes and his shoulders slowly loosen. Camera: close two-shot, gradual push toward the table, then hold as the first pale dawn appears through a high window. Real motion: clock hand advances, tea surface stills, subtle breathing. No visible child, no readable writing, no coercion.",
        "sfx": ["低声交谈", "钟摆声", "第一声晨鸟"],
    },
    {
        "id": "S26", "start": 150, "duration": 6, "narration_id": "N08",
        "camera": "地面低机位推向树根与铁锹",
        "characters": ["C07"], "references": ["S13", "C07"],
        "narration": "三月九日清晨，警方在树根下挖出一百多块骨骸。",
        "prompt": "At a Tainan vacant lot on 9 March 1991, fictional investigators and workers carefully dig around an old cut tree stump. Keep the camera at ground level on moving shovels, soil and wind-blown cordon tape; never show what is uncovered. A white evidence tent remains distant and closed. Camera: slow low push toward exposed roots, end before the soil is opened. Real motion: hands work, loose soil falls, tape moves. Absolutely no body, bone or remains visible.",
        "sfx": ["铁锹入土", "风声"],
    },
    {
        "id": "S27", "start": 156, "duration": 6, "narration_id": "N08",
        "camera": "帐篷中景缓推至遗物与雨伞",
        "characters": ["C06", "C04"], "references": ["C06", "C04", "P05", "P01"],
        "narration": "鉴定确认了身份；母亲的目光，缓缓落在女儿的遗物上。",
        "prompt": "Under a plain forensic tent after identification, two fictional experts exchange a restrained confirming glance beside empty, covered evidence trays. The mother is gently supported as she approaches a table with only a closed, unmarked evidence envelope, a folded umbrella, a flashlight and the deep navy backpack. She looks at the belongings, tears held back. Camera: medium push toward the umbrella and worn backpack, faces remain natural and dignified. Real motion: tent fabric lifts in wind, hands tremble slightly. No remains, body, bones, weapons or readable labels.",
        "sfx": ["帐篷布声", "压抑呼吸"],
    },
    {
        "id": "S28", "start": 162, "duration": 6, "narration_id": "N08",
        "camera": "远景航拍缓慢拉升",
        "characters": ["C07"], "references": ["S14", "C07"],
        "narration": "据供述，头颅被垃圾车运走；掩埋场的搜寻最终停止。",
        "prompt": "A vast municipal landfill outside Tainan beneath a gray sky. A distant bulldozer and excavator move slowly through ordinary refuse while a few fictional police silhouettes stand at the edge, unable to search the entire area. Camera: slow aerial rise and pullback to reveal the immense scale. Real motion: machinery moves, seabirds circle, wind lifts dust. No body, remains or sensational imagery.",
        "sfx": ["机械轰鸣", "海鸥叫声", "风声"],
    },
    {
        "id": "S29", "start": 168, "duration": 6, "narration_id": "N09",
        "camera": "长焦背影跟拍，机场人流掠过",
        "characters": ["C04"], "references": ["S15", "C04"],
        "narration": "一九九三年，母亲带着女儿的骨灰离开台湾，踏上归乡之路。",
        "prompt": "A 1993 Taiwan airport departure hall seen from behind. The fictional mother, wearing the same dark coat and long skirt, holds a small plain urn wrapped in cloth close to her chest and walks slowly through moving travelers. She pauses once and looks back toward the island through tall windows. Camera: compressed long-lens follow from behind. Real motion: crowd passes in both directions, sunlight moves across the floor. No readable airport signage, no logo.",
        "sfx": ["机场广播", "缓慢脚步"],
    },
    {
        "id": "S30", "start": 174, "duration": 6, "narration_id": "N09",
        "camera": "窗台缓慢推近，白光叠化",
        "characters": ["C04"], "references": ["S16", "C04", "P01"],
        "narration": "刘学强被判无期；近年报道中，假释申请未获准，她没能回家。",
        "prompt": "In a quiet Tokyo room years later at dusk, the fictional mother sits in three-quarter back view beside a small plain urn and white flowers on a wooden windowsill. A framed, indistinct photograph of a young woman and the worn deep navy backpack stand nearby. She rests one hand beside the urn, then looks out at the rooftops as a sheer curtain moves in the evening breeze. Camera: very slow push toward the photograph and backpack; warm light blooms gently to white in the final third. Real motion: curtain and flowers move naturally. In the final 0.3 seconds, the moving image freezes for a beat and abruptly flashes to white, then black; no generated text.",
        "sfx": ["晚风渐弱", "最后一秒静音"],
    },
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def timecode(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    minutes, rest = divmod(total_ms, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{minutes:02d}:{secs:02d}.{ms:03d}"


def reference_url(ref_id: str) -> str:
    row = REFERENCE_FILES[ref_id]
    return f"https://raw.githubusercontent.com/{REPOSITORY}/{BRANCH}/production/iguchi1990/reference/{row[1]}"


def build() -> dict:
    shot_map = {shot["id"]: shot for shot in SHOTS}
    chapters = []
    for cid, title, start, duration, shot_ids in CHAPTERS:
        text = "".join(shot_map[sid]["narration"] for sid in shot_ids)
        chapters.append({"id": cid, "title": title, "start": start, "duration": duration,
                         "shot_ids": shot_ids, "text": text})

    story_shots = []
    for index, source in enumerate(SHOTS):
        shot = dict(source)
        shot.update({
            "kind": "agnes",
            "purpose": shot["narration"],
            "seconds": shot["duration"],
            "aspect": "16:9",
            "source_size": "720P",
            "seed": 19900407 + index,
            "reference_images": [
                {"id": ref_id, "file": REFERENCE_FILES[ref_id][1], "url": reference_url(ref_id)}
                for ref_id in source["references"]
            ],
        })
        story_shots.append(shot)

    narration_hanzi_count = sum(
        len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", shot["narration"]))
        for shot in story_shots
    )
    narration_hanzi_rate = narration_hanzi_count / sum(shot["duration"] for shot in story_shots)

    voice_id_file = AUDIO / "voice_id.txt"
    voice_id = voice_id_file.read_text(encoding="utf-8").strip() if voice_id_file.is_file() else "pending-selection"
    story = {
        "title": TITLE,
        "film_name": FILM_NAME,
        "target_duration": 180,
        "width": 1920,
        "height": 1080,
        "fps": 24,
        "model": "agnes-video-2.5-flash",
        "source_size": "720P",
        "branch": BRANCH,
        "repository": REPOSITORY,
        "style_prefix": STYLE_PREFIX,
        "negative_prompt": NEGATIVE_PROMPT,
        "characters": CHARACTERS,
        "character_seeds": {key: value["seed"] for key, value in CHARACTERS.items()},
        "chapters": chapters,
        "shots": story_shots,
        "reference_images": [
            {"id": ref_id, "category": row[0], "file": row[1], "description": row[2],
             "url": reference_url(ref_id),
             "review_status": REFERENCE_REVIEW.get(ref_id, {}).get("status", "pending"),
             "approved": REFERENCE_REVIEW.get(ref_id, {}).get("status") == "approved"}
            for ref_id, row in REFERENCE_FILES.items()
        ],
        "reference_gate": {
            "status": "complete" if all(REFERENCE_REVIEW.get(ref_id, {}).get("status") == "approved"
                                          and (REFERENCE / row[1]).is_file()
                                          for ref_id, row in REFERENCE_FILES.items()) else "incomplete",
            "approved_count": sum(1 for ref_id, row in REFERENCE_FILES.items()
                                  if REFERENCE_REVIEW.get(ref_id, {}).get("status") == "approved"
                                  and (REFERENCE / row[1]).is_file()),
            "required_count": len(REFERENCE_FILES),
            "generation_blocked_until_all_refs_approved": True,
        },
        "sources": SOURCES,
        "fact_boundary": [
            "画面均为AI生成的写实3D动画情景复原，不是历史影像、照片或警方证物照。",
            "井口真理子、井口久子、李姓司机、刘学强、王家儒、杨日松、李昌钰均不使用真实肖像；角色是虚构演员式形象。",
            "全片不展示遗体、人体残骸、凶器、行凶过程、性侵画面或分尸画面；挖掘镜头只拍动作与封闭现场，不拍挖出物。",
            "对犯罪经过的说明以公开报道和供述为依据，不把未经证实的传闻写成事实；动机仅按警方移送书/报道归因，不作夸张渲染。",
            "4月4日至4月7日部分行程报道细节存在差异，旁白只说她在台南受李姓司机接待、后于4月7日从台南乘车前往高雄。",
            "1991年3月9日挖掘时不安排母亲在场；相关报道指母亲于3月14日再度抵台，故她只出现在后续身份确认与遗物镜头。",
            "假释次数按报道时间点理解；旁白不用‘二十次’作为截至2026年的最新统计，只说多次申请未获准。",
            "最新状态目前只核对到2026年2月的公开报道；本片发布前必须再查截至2026年11月的司法、服刑与头颅搜寻进展。",
            "截至2026年2月收录的公开报道仍称头颅未寻获、刘学强仍在服刑；正式发布前应复核有无新进展。",
            "不把黄色出租车镜头说成确切的弃置遗体交通工具；它是‘计程车司机’身份的视觉线索。",
        ],
        "narration_stats": {
            "hanzi_count": narration_hanzi_count,
            "duration_seconds": sum(shot["duration"] for shot in story_shots),
            "hanzi_per_second": round(narration_hanzi_rate, 3),
            "counting_basis": "CJK ideographs; punctuation excluded.",
        },
        "narration_spec": {
            "voice_id": voice_id,
            "style": "沉稳、克制、低沉的成熟男声；悬疑叙述但不煽情。",
            "target_characters_per_second": 3.7,
            "alignment": "one-sentence-per-shot; shot-locked; total 180 seconds",
            "max_speedup_factor": 1.55,
        },
        "presentation": {
            "title": TITLE,
            "subtitle": "台湾 · 1990—1993 · 她没能回家",
            "hook_caption": "她走出高雄车站，从此人间蒸发",
            "cover": {
                "text": "她没能回家",
                "subtitle": "井口真理子命案",
                "layout": "use S01 station-hall image: bright exit and anonymous backpacked silhouette on left; empty concourse and navy backpack on right; gold title with dark stroke",
            },
            "highlight_keywords": ["井口真理子", "高雄车站", "人间蒸发", "三十六年", "四月七日", "四月二十五日", "一百万", "刘学强", "李姓司机", "三月四日", "深蓝色大背包", "三月九日", "头颅", "一九九三年", "没能回家"],
            "subtitle_style": "白字黑边，底部安全区居中，关键词金色放大；字幕逐句与各镜旁白同步。",
            "audio_style": "严格无BGM、无音乐、无旋律性氛围铺底；仅使用旁白、镜头对应的环境音与原创拟音，旁白优先，结尾静音。",
            "transitions": "以硬切为主；S14、S22、S24使用快速蒙太奇/闪回；章节边界轻叠化；S30最后0.3秒由定格突变至白光/黑场。",
            "color_arc": "S01–S17暖黄；S18转深蓝与黑；S19–S28冷青；S29–S30恢复柔和暖光。",
            "shot_review_ids": ["S05", "S10", "S15", "S20", "S25", "S30"],
            "sound_events": [{"shot_id": shot["id"], "cues": shot["sfx"]} for shot in SHOTS],
            "hashtags": ["#真实事件", "#井口真理子", "#台湾", "#悬疑", "#案件回顾", "#电影感"],
            "release_title": "她走出高雄火车站后，从此人间蒸发：井口真理子命案",
        },
    }

    AUDIO.mkdir(parents=True, exist_ok=True)
    (HERE / "qa").mkdir(parents=True, exist_ok=True)
    (HERE / "workflows").mkdir(parents=True, exist_ok=True)
    (REFERENCE / "approvals").mkdir(parents=True, exist_ok=True)
    (HERE / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_clips = []
    for shot in story_shots:
        audio = AUDIO / f"{shot['id']}.mp3"
        manifest_clips.append({
            "id": shot["id"], "file": f"{shot['id']}.mp3", "text": shot["narration"],
            "voice_id": voice_id, "sha256": sha256(audio) if audio.is_file() else None,
            "target_start": shot["start"], "target_duration": shot["duration"],
            "alignment": "shot-locked", "status": "ready" if audio.is_file() else "pending",
        })
    manifest = {"project": TITLE, "voice_id": voice_id, "clips": manifest_clips,
                "target_duration": 180, "alignment": "one sentence per Agnes clip"}
    (AUDIO / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    screen = [
        f"# {TITLE}", "", "三分钟横屏悬疑动画 · 1920×1080 · 24fps · 180秒 · 30条Agnes Video 2.5 Flash动态片段", "",
        "> AI写实3D动画情景复原，不是历史影像。所有人物均为非真实肖像的虚构演员式形象；全片不出现遗体、人体残骸、凶器或暴力过程。", "",
        "## 事实边界与制作说明", "",
        f"旁白按每镜一句编排，单镜字幕、语音和画面共享同一时间窗；按CJK汉字计数{narration_hanzi_count}字，180秒约{narration_hanzi_rate:.2f}字/秒。原脚本里镜头时码连续覆盖180秒，但段落标题有约2秒起点偏差；本版以30条镜头时码为准重新分章。", "",
        "1991年3月9日挖掘时不安排母亲在场；相关报道记载她于3月14日再度抵台。对刘学强的动机与供述使用谨慎归因，不渲染性暴力和分尸细节。黄色出租车只作为‘计程车司机’视觉线索，不宣称它是弃置遗体的车辆。", "",
        "## 旁白与分章", "",
    ]
    for chapter in chapters:
        screen += [f"### {timecode(chapter['start'])}—{timecode(chapter['start'] + chapter['duration'])}　{chapter['title']}（{chapter['id']}）", "", chapter["text"], ""]
    screen += ["## 30镜时间轴", "", "| 镜号 | 时间 | 秒数 | 章节 | 运镜 | 解说 |", "|---|---:|---:|---|---|---|"]
    for shot in story_shots:
        screen.append(f"| {shot['id']} | {timecode(shot['start'])}–{timecode(shot['start'] + shot['duration'])} | {shot['duration']} | {shot['narration_id']} | {shot['camera']} | {shot['narration']} |")
    screen += ["", "## 参考图目录", "", "角色参考为虚构设定图；场景与道具为AI概念图。S02原要求同时包含机场和夜市，本项目拆成S02机场与S02b夜市两张独立图，避免把不同场景拼成参考图拼贴。", ""]
    for ref_id, (category, filename, description) in REFERENCE_FILES.items():
        screen.append(f"- `{ref_id}`（{category}）：`reference/{filename}` — {description}。")
    screen += ["", "## 来源", ""]
    for source in SOURCES:
        screen.append(f"- [{source['title']}]({source['url']}) — {source['claims']}")
    screen += ["", "## 后期", "", "旁白：低沉克制成熟男声，约3.7字/秒；白字黑边、底部安全区字幕，关键词金色强调。严格无BGM、无音乐、无旋律性氛围铺底，仅使用逐镜环境音与拟音。片尾标题由后期叠加，视频模型不负责生成中文文字。", ""]
    (HERE / "screenplay.md").write_text("\n".join(screen), encoding="utf-8")

    prompt_lines = [f"# {TITLE} · 镜头提示词与参考图", "", "每条提示词由 `generate.py` 自动按 STYLE → 指定`<Picture N>`参考图 → 原文角色锚点 → 镜头画面 → NEGATIVE 拼接。Agnes Video 2.5 Flash 使用 `mode=reference`、720P、16:9，参考图最多5张。", ""]
    for shot in story_shots:
        prompt_lines += [f"## {shot['id']} · {shot['start']}–{shot['start'] + shot['duration']}秒", "",
                         f"- 参考图：{', '.join(shot['references'])}",
                         f"- 角色锚点：{'; '.join(CHARACTERS[c]['anchor'] for c in shot['characters']) or '无'}",
                         f"- 运镜：{shot['camera']}", f"- 旁白：{shot['narration']}",
                         f"- 画面：{shot['prompt']}", ""]
    (HERE / "镜头提示词与生成记录.md").write_text("\n".join(prompt_lines), encoding="utf-8")

    release = [
        f"# {story['presentation']['release_title']}", "",
        "## 简介", "", "她走出高雄车站后，行踪成谜。母亲跨海寻女，线索几度指向错误方向；一年后，嫌犯落网，却留下一个至今没有找回的遗憾。", "",
        "本片为公开资料基础上的AI写实3D动画情景复原，并非历史影像。人物均为非真实肖像的虚构演员式形象，不展示遗体、凶器或暴力过程。案件细节与供述以文末资料为准。", "",
        "话题：" + " ".join(story["presentation"]["hashtags"]), "",
        "发布前核查：目前收录至2026年2月；确认2026年11月前是否出现新的头颅搜寻、司法或服刑状态报道。", "",
    ]
    (HERE / "抖音发布文案.md").write_text("\n".join(release), encoding="utf-8")

    ref_rows = []
    for ref_id, row in REFERENCE_FILES.items():
        image_path = REFERENCE / row[1]
        review = REFERENCE_REVIEW.get(ref_id, {"status": "pending", "note": "尚未生成并逐张复核。"})
        ref_rows.append({
            "id": ref_id, "category": row[0], "file": row[1], "description": row[2],
            "exists": image_path.is_file(), "sha256": sha256(image_path) if image_path.is_file() else None,
            "review_status": review["status"],
            "approved": review["status"] == "approved" and image_path.is_file(),
            "review_note": review.get("note", ""),
        })
    ref_manifest = {
        "project": TITLE,
        "required_reference_count": len(REFERENCE_FILES),
        "approved_reference_count": sum(1 for row in ref_rows if row["approved"]),
        "references": ref_rows,
        "status": "complete" if all(row["approved"] for row in ref_rows) else "incomplete",
        "generation_blocked_until_all_refs_approved": True,
        "note": "Every reference must exist and pass individual visual review before GEN_REQUEST. Presence alone never approves an image.",
    }
    (REFERENCE / "manifest.json").write_text(json.dumps(ref_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return story


if __name__ == "__main__":
    story = build()
    print(f"Built {len(story['shots'])} shots / {sum(s['duration'] for s in story['shots'])}s; reference package: {story['reference_images'] and 'check reference/manifest.json'}")

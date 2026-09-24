#!/usr/bin/env python3
"""《大卫·史密斯：无罪之后》的唯一内容源。

从这里生成 story.json、audio/manifest.json 的逐字文本、抖音脚本和发布文案。
镜头按长岛吉尔戈项目的制作方法设计：45 镜 × 4 秒规划网格，38 个 Agnes
Video V2.0 动画镜头 + 7 张可控信息卡；所有中文文字都由后期渲染，避免视频
模型生成伪文字。真实人物只用背影、剪影、手和道具，不用 AI 生成人脸。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
TITLE = "大卫·史密斯：无罪之后"

STYLE_PREFIX = (
    "Stylized 2D animated documentary illustration with hand-painted graphic-novel textures, soft cel "
    "shading and restrained analog print misregistration; Britain from the late 1970s to 2023, west London "
    "flats and terraced streets, Surrey woodland lanes, lorry cabs, Old Bailey-like crown court interiors, "
    "prison corridors and forensic archive rooms; horizontal 16:9 cinematic composition, muted slate blue, "
    "charcoal, dirty cream and sodium-orange practical light, cool overcast British daylight, fast investigative "
    "true-crime explainer mood with a subtle warped documentary lens at transitions but no anatomical distortion; "
    "every person appears only from behind, in silhouette, or as hands and props, never a clear frontal face; "
    "no readable text, letters, numbers, logos, license plates or brand marks inside the generated frame; one "
    "single continuous smooth camera move per shot exactly as directed. "
)

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, invented headlines, logos, brand marks, "
    "watermark, subtitles, on-screen caption, photorealistic face, recognizable real person likeness, "
    "frontal face close-up, visible eyes in detail, blood, gore, wound, corpse, body bag, body parts, "
    "autopsy, violence, assault, strangling, weapon attack, gun, firearm, nudity, erotic content, horror "
    "monster, ghost, jump scare, 3D render look, plastic CGI, grotesque anatomy, distorted anatomy, "
    "deformed hands, extra fingers, extra limbs, duplicated people, changing face, morphing objects, "
    "teleportation, jitter, flicker, fast zoom, whip pan, jump cut, split screen, collage"
)

PRINCIPLES = [
    "全部 Agnes 镜头为风格化 2D 动画情景重现，画面常驻「AI动画情景重现 · 非新闻影像」，不冒充庭审、监控或证物照片",
    "不展示遗体、血腥或侵害过程；作案手法只讲公开报道能支持的接触、室内暴力和藏匿/弃置，不重现过程",
    "史密斯只以背影、剪影、手部出现，不用 AI 生成的人脸冒充本人；受害者不以人像出现",
    "「大脚怪」是公开资料中的外号，本片不把它写成警方正式称谓；不写没有证据支持的暗网经历或更多未定案命案",
    "每一句事实都能指到 sources 里的一条公开报道；法律部分区分二零零三年立法、二零零五年生效、二零二二年准许重审和二零二三年定罪",
    "一罪不二审并非被完全抹去：本案适用的是出现新的、令人信服的证据后的窄门例外",
    "中文姓名、日期、字幕和信息卡全部后期添加，不交给视频模型拼写；信息卡为动画资料图，不是原始档案",
    "人工检视 qa/ 接触表，脸部、手部、物体、伪文字、换场或明显畸变的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

SOURCES = [
    {
        "id": 1,
        "url": "https://en.wikipedia.org/wiki/David_Smith_(murderer)",
        "usage": "案件总览、Sarah Crump 与 Amanda Walker 两案、1993 无罪、1999 定罪、2022 重审、2023 判决及外号资料。",
    },
    {
        "id": 2,
        "url": "https://www.bbc.com/news/uk-england-london-65682975",
        "usage": "2023 年重审定罪；1991 年案件、1993 年无罪、1999 年 Amanda Walker 案、狱中吹嘘 got away with it。",
    },
    {
        "id": 3,
        "url": "https://www.bbc.co.uk/news/uk-england-london-65721383",
        "usage": "2023 年五月终身监禁、最低二十七年、重审前旧案状态及上诉法院在 2022 年下令重审。",
    },
    {
        "id": 4,
        "url": "https://news.sky.com/story/david-smith-honey-monster-killer-handed-life-sentence-for-double-jeopardy-murder-12890023",
        "usage": "假名 Duncan、第一次审判后再次作案、狱中吹嘘、法律改变后重审及最低刑期。",
    },
    {
        "id": 5,
        "url": "https://www.independent.co.uk/news/uk/crime/david-smith-old-bailey-southall-london-police-b2345032.html",
        "usage": "Southall 公寓、1991 年案件细节、现场指纹与前屋主关联、史密斯向陪审团道谢的报道。",
    },
    {
        "id": 6,
        "url": "https://www.itv.com/news/london/2023-05-26/perverted-killer-jailed-for-sex-workers-murder-30-years-after-he-was-cleared",
        "usage": "卡车司机、身材与外号、两起案件的相似性、1993 年无罪与 2023 年终身监禁。",
    },
    {
        "id": 7,
        "url": "https://www.legislation.gov.uk/ukpga/2003/44/contents",
        "usage": "英国《刑事司法法二零零三》及一罪不二审例外的法律依据；片中不把它简化为完全废除。",
    },
    {
        "id": 8,
        "url": "https://www.irishnews.com/news/uknews/2023/05/26/news/life_sentence_for_sadistic_sexual_killer_for_double_jeopardy_murder-3306198/",
        "usage": "判决日期、最低刑期折抵、狱中向同仓犯人吹嘘及证据链重新组合的公开报道。",
    },
]

# 六段逐字口播，共 773 字（含标点），刻意控制为约三分钟可用长度。
CHAPTERS = [
    (
        "N01",
        "黄金开头：无罪之后还道谢",
        "一个男人，刚在法庭上被判无罪，竟然还向陪审团道谢。六年后，他再次杀人；三十年后，一条改过的「一罪不二审」法律，加上一句狱中吹嘘，把他重新送上被告席。他就是英国的大卫·史密斯。今天，一口气看懂这场迟到三十年的翻案。关键，是旧证据被重新读懂。", 
    ),
    (
        "N02",
        "双面人生：卡车司机与前科",
        "史密斯是英国卡车司机，身材高大，外号「大脚怪」；同事眼里，他只是个沉默的普通人。但在这层外表下面，是从年轻时就不断升级的性暴力前科。九十年代，他用假名「邓肯」接近三十三岁的萨拉·克拉姆。表面是付费见面，背后却是一场没人能及时阻止的危险。",
    ),
    (
        "N03",
        "作案模式：假名、密闭空间与藏匿",
        "一九九一年八月，克拉姆在伦敦南豪尔的公寓遇害。警方发现，现场留下的伤害方式，后来被认为与另一宗案件高度相似。六年后，二十一岁的阿曼达·沃克失踪，遗体在萨里郡威斯利附近被发现。两案都指向同一个模式：用假名接触，在相对封闭的空间里实施暴力，再把受害者带离现场、藏匿或弃置。可真正可怕的，是第一次审判之后。",
    ),
    (
        "N04",
        "第一次审判：证据链瑕疵",
        "一九九三年，史密斯因克拉姆案受审。辩方抓住了现场指纹没有及时解释这一证据链瑕疵，陪审团最终判他无罪。史密斯走出法庭时，甚至向陪审团道谢。受害者母亲当庭警告：他还会再杀人。六年后，沃克案让这句警告成了事实——史密斯被判谋杀，终身监禁。",
    ),
    (
        "N05",
        "翻案关键：狱中吹嘘与法律窄门",
        "但他在狱中又犯了一个致命错误：向同仓犯人吹嘘，自己当年「已经逃过了」。英国后来通过二零零三年《刑事司法法》，给「一罪不二审」开出极窄的例外：只有出现新的、令人信服的证据，才可能重审。二零二二年，上诉法院推翻旧判决；旧指纹被查明属于前屋主，加上狱中吹嘘和沃克案的相似性，三十年前的证据链终于闭合。",
    ),
    (
        "N06",
        "结局：三十年后的定罪",
        "二零二三年五月，重审陪审团不到三小时就裁定史密斯谋杀克拉姆罪名成立。他被判终身监禁，最低刑期二十七年；而沃克案的无期刑，他早已在服。迟到三十年的正义，靠的不是一句传闻，而是法律给证据留下的窄门，以及凶手亲口留下的回声。你觉得，「一罪不二审」的例外，应该更严格，还是更勇敢？",
    ),
]


def A(sid: str, camera: str, purpose: str, transition: str, prompt: str, sfx: str):
    return (sid, "agnes", camera, purpose, transition, prompt, sfx)


def G(sid: str, purpose: str, transition: str, graphic: str, sfx: str):
    return (sid, "graphic", "后期卡片轻微推近", purpose, transition, graphic, sfx)


# 45 镜按叙事顺序排列；7 张信息卡 + 38 个 Agnes 动画镜头。
SHOTS = [
    # N01
    A("S01", "低机位缓慢推向法庭门口", "无罪宣判后的反常开场：只拍法庭门、长椅和不露脸的人影", "法槌声切入下一镜",
      "Stylized 2D animated documentary scene inside a dim British crown court corridor, an oversized male silhouette in a dark coat walks away from a closed courtroom door while a few jury silhouettes remain seated behind frosted glass, hands and shoes only, no faces. Camera: one slow low dolly toward the door, hold on the empty threshold for the full clip, no cut, no scene change, no readable text.", "低沉法槌 + 低频脉冲"),
    A("S02", "固定中景，人物停在门外", "史密斯无罪离场的荒诞感：背影停住，向身后抬手致意", "抬手动作匹配下一镜的回声",
      "Stylized 2D animated documentary scene outside a British courthouse on a grey afternoon, a very tall broad-shouldered man seen only from behind pauses on stone steps and lifts one hand toward the unseen courtroom, no face, no signage, no readable text. Camera: locked-off medium-wide shot with only the coat and distant umbrellas moving, hold on the raised hand, no cut, no scene change.", "鞋跟回声 + 短促吸气"),
    A("S03", "走廊横移", "把时间一下拉到六年后：监狱走廊的铁门和高大剪影", "铁门声做时间跳切",
      "Stylized 2D animated documentary scene in a cold British prison corridor, a tall heavy male silhouette passes behind vertical bars carrying a small bedding bundle, only back and hands visible, no face and no text. Camera: one slow sideways tracking move parallel to the bars, hold the same corridor for the full clip, no cut, no scene change.", "铁门滑轨声 + 低沉撞击"),
    G("S04", "案件名片：把地点、年代、翻案钩子一次打出", "卡片右下角压入下一镜的纸张声", "大卫·史密斯案\n一九九一年—二零二三年 · 英国\n无罪之后，三十年后重审", "纸张展开 + 一记心跳"),
    A("S05", "法官手部特写，微微下摇", "用法槌、卷宗和空椅子建立“法庭判过一次”的主题", "卷宗合上切到下一张卡片",
      "Stylized 2D animated documentary close scene of a judge's hands placing a plain case file beside a wooden gavel on a crown court bench, only hands and objects, no readable writing, no faces. Camera: one slow downward tilt from the empty witness box to the gavel, hold on the closed file, no cut, no scene change.", "纸页翻动 + 法槌轻放"),
    A("S06", "狭窄室内缓慢推近门锁", "把“同一个人再次作案”变成一个关不上的门意象", "门锁咔哒声接入口播悬念",
      "Stylized 2D animated documentary scene in a narrow institutional hallway, a gloved hand turns an old metal door latch and the door opens only a few centimetres onto darkness, no face, no body, no violence, no readable text. Camera: one slow push toward the latch, hold on the thin line of light, no cut, no scene change.", "金属门锁咔哒 + 环境嗡鸣"),
    A("S07", "俯拍时钟与两份空白文件的缓慢环绕", "表现六年、三十年的时间差，不让模型生成日期文字", "秒针声硬切下一镜",
      "Stylized 2D animated documentary still life on a dark wooden desk: two blank cream case folders, a pocket watch and a long shadow from a desk lamp, no writing or numbers anywhere. Camera: one slow overhead clockwise drift, paper edges lift slightly in a draft, hold on the empty space between the folders, no cut, no scene change.", "秒针放大 + 胶片噪点"),
    A("S08", "背影跟拍后停在黑暗门口", "片头末尾留悬念：案件名字出现过，真正的问题是他是谁", "黑场一拍，进入人物背景",
      "Stylized 2D animated documentary scene of a tall man seen from behind entering a shadowed British prison doorway, a strip of cold light catches one shoulder and the metal frame, no face, no text. Camera: one slow follow shot from behind that stops before the doorway, hold on the empty threshold, no cut, no scene change.", "低频持续音 + 黑场停顿"),
    # N02
    G("S09", "人物档案卡：普通职业与危险外号并置", "卡片上的“外号”作为字幕高亮，切到卡车轮胎", "双面人生\n卡车司机 · 外号「大脚怪」\n前科升级 · 两起谋杀定罪", "打字机三连 + 远处柴油机"),
    A("S10", "卡车驾驶室内由后视镜向下摇", "只用卡车司机背影和大手表现体格，不生成脸", "柴油机声贯穿",
      "Stylized 2D animated documentary scene inside an old British lorry cab at dawn, a very large driver shown only from behind grips the steering wheel, shoulders filling the frame, rain streaks on the windscreen, no face, no logos, no readable text. Camera: one slow tilt from the rain-streaked mirror to the hands on the wheel, hold in this single cab, no cut, no scene change.", "柴油机怠速 + 雨刷"),
    A("S11", "公路侧面平行跟拍", "表面普通的卡车生活：把“普通人”与危险并置", "车轮声匹配下一镜的家庭门锁",
      "Stylized 2D animated documentary scene of a plain lorry moving along a wet two-lane British road between hedges, seen from the side with the driver only a dark silhouette through frosted glass, no signs, no plates, no text. Camera: one smooth lateral tracking move at the same speed, hold on the vehicle and hedgerow, no cut, no scene change.", "轮胎压水 + 远雷"),
    A("S12", "郊区房门固定大全景，人物走出画面", "普通外表的生活场景，不暗示未经证实的暗网经历", "房门合上，声音切入手机",
      "Stylized 2D animated documentary scene outside a modest west London terraced house on an overcast morning, a tall male silhouette carries a work bag from the front door to a parked lorry, only back visible, no faces, no house numbers or signage. Camera: locked wide shot from across the quiet street, only the figure and a tree branch move, no cut, no scene change.", "远处公交车 + 门锁"),
    A("S13", "手机屏幕不入镜，手部沿桌面横移", "假名接近受害者：只画一次性手机和手，屏幕保持无字", "手机振动切封闭空间",
      "Stylized 2D animated documentary close-up on a cheap disposable phone beside coins and a plain paper envelope on a dark table, a large hand slides the phone toward the edge, the screen is turned away and contains no readable symbols, no face. Camera: one slow horizontal tabletop move, hold on the phone and hand, no cut, no scene change.", "一次性手机振动 + 纸袋摩擦"),
    A("S14", "走廊向公寓门缓慢推近", "萨拉·克拉姆案的地点意象：公寓门前，不展示受害者", "门内灯光切下一镜",
      "Stylized 2D animated documentary scene in a quiet west London apartment hallway at night, a closed bedroom door at the end, a man's large shadow stops outside the door, no face, no people visible, no number plate or readable sign. Camera: one slow push down the corridor toward the closed door, hold on the gap beneath it, no cut, no scene change.", "走廊电流声 + 远处钟声"),
    A("S15", "桌面卷宗与空椅子的缓慢俯拍", "把双面人生落到“前科不是传闻，而是记录”", "纸张合上进入作案模式",
      "Stylized 2D animated documentary still life in a police archive room, a plain brown file folder, a blank interview chair and a gloved hand placing a small evidence bag on the desk, no readable writing, no weapon, no body. Camera: one slow overhead drift toward the evidence bag, hold on the empty chair, no cut, no scene change.", "档案柜滑轨 + 铅笔划线"),
    # N03
    G("S16", "两名受害者只以姓名、年龄、年份出现，避免人像化", "卡片收尾留白，尊重受害者而非消费画面", "两起命案\n萨拉·克拉姆 · 一九九一年\n阿曼达·沃克 · 一九九九年", "单音钢琴 + 纸张轻响"),
    A("S17", "公寓楼门外缓慢下摇到门把手", "一九九一年南豪尔：到访地点和密闭空间", "门把手特写匹配指纹线索",
      "Stylized 2D animated documentary scene at the entrance of a west London apartment block at night, a large hand reaches toward a plain door handle while the corridor walls fill the background, no face, no door number, no readable text. Camera: one slow downward tilt from the empty landing to the handle, hold on the metal, no cut, no scene change.", "楼道脚步 + 门把手金属响"),
    A("S18", "卧室空镜，窗帘轻动，镜头缓慢横移", "只让观众感到密闭与失去，不画暴力过程", "窗帘声切到地图公路",
      "Stylized 2D animated documentary scene inside an empty modest bedroom, a closed curtain moves in a draft, a bedside lamp pools warm light on a blank table, no people, no blood, no violence, no readable text. Camera: one slow lateral move from the curtain to the empty chair, hold on the vacant room, no cut, no scene change.", "窗帘摩擦 + 房间底噪"),
    A("S19", "林道高位缓慢前移", "阿曼达·沃克案的地点：萨里郡威斯利附近，只画路和树", "轮胎声接到时间轴",
      "Stylized 2D animated documentary aerial illustration of a quiet leafy lane near Surrey woodland, a single plain vehicle disappears around a bend, wet leaves and tall trees fill the frame, no people, no signs, no readable text. Camera: one slow forward drift above the road, hold on the bend, no cut, no scene change.", "湿地风声 + 远处车轮"),
    A("S20", "车窗内向外的固定视角", "“带离、藏匿、弃置”只用路线意象表达，不展示遗体", "车灯掠过切证物袋",
      "Stylized 2D animated documentary scene from inside a dark vehicle looking through a rain-streaked side window at a narrow Surrey road and black hedges, no driver face, no body, no violence, no signs. Camera: locked-off view while rain and roadside lights move past, hold on the same window for the full clip, no cut, no scene change.", "雨声 + 低沉引擎"),
    A("S21", "警员手部从纸袋移向空白地图", "调查者面对的不是视觉奇观，而是物证与路线", "证物袋封口声切地图",
      "Stylized 2D animated documentary scene in a dim police evidence room, gloved hands seal a plain transparent evidence bag and place it beside a blank paper map with no markings, no body, no blood, no readable text. Camera: one slow tabletop slide from the bag to the blank map, hold on the sealed edge, no cut, no scene change.", "证物袋封口 + 纸面摩擦"),
    A("S22", "两条无字线绳在桌面上缓慢靠拢", "两案相似性：视觉化“同一模式”，不把图示当证据照片", "两条线交汇进入第一次审判",
      "Stylized 2D animated documentary scene on a forensic desk: two cream folders without writing, two strands of red and blue thread slowly drawn together by gloved hands, no readable text, no face, no graphic violence. Camera: one slow overhead push toward the point where the threads meet, hold on the crossing, no cut, no scene change.", "细线绷紧 + 低频上扬"),
    A("S23", "档案室人物背影向两份卷宗走近", "一句悬念：相似模式却不等于法庭已经认定", "卷宗翻页切到法庭",
      "Stylized 2D animated documentary scene in a long archive room, a solitary investigator shown from behind walks between shelves toward two blank case folders on a table, no face, no labels or readable text. Camera: one slow forward tracking move down the aisle, hold when the figure reaches the desk, no cut, no scene change.", "档案室混响 + 翻页"),
    # N04
    A("S24", "法院外墙向台阶缓慢下摇", "一九九三年第一次审判正式开始", "石阶脚步切指纹证据",
      "Stylized 2D animated documentary illustration of a grand historic London criminal court exterior in grey rain, people are only distant silhouettes crossing stone steps, no readable signage, no faces. Camera: one slow crane down from the upper stone facade to the empty steps, hold on the doorway, no cut, no scene change.", "雨点 + 法庭门重响"),
    A("S25", "放大镜沿指纹示意图缓慢横移", "指纹证据链瑕疵：后期再解释，而非伪造原始证物", "放大镜停住，接陪审团静音",
      "Stylized 2D animated documentary close-up in a forensic archive, a magnifying glass moves over a generic fingerprint diagram beside a plain old key and a blank evidence card, no real biometric data, no readable text, no face. Camera: one slow lateral tabletop move, hold when the lens stops over the diagram, no cut, no scene change.", "放大镜轻响 + 突然静音"),
    A("S26", "陪审团背影固定中景，空白证物板在前景", "陪审团只能依据当时被完整呈现的证据", "纸张落桌进入无罪卡",
      "Stylized 2D animated documentary scene inside a British jury box, several jury silhouettes seen from behind face a blank evidence board, a prosecutor's hand lowers a plain folder in the foreground, no faces, no readable text. Camera: locked-off medium-wide shot with only paper and hands moving, hold on the blank board, no cut, no scene change.", "纸张落桌 + 心跳停半拍"),
    G("S27", "把“无罪释放”做成强记忆点，避免伪造真实庭审画面", "卡片最后一秒压黑，回到法院台阶", "一九九三年\n陪审团裁定：无罪\n证据链瑕疵 · 当庭脱身", "法槌回声 + 低频下坠"),
    A("S28", "法院台阶侧后方跟拍", "史密斯走出法庭并向陪审团道谢，只拍背影和手", "抬手动作与片头呼应",
      "Stylized 2D animated documentary scene on wet courthouse steps, a very tall broad man seen only from behind walks into the grey street and briefly raises one hand toward the doorway, no face, no signage, no readable text. Camera: one slow rear three-quarter tracking move that stops as the hand lowers, no cut, no scene change.", "脚步 + 一声短促回声"),
    A("S29", "空椅子和一束不具象的人物花束，缓慢推近", "受害者家属的警告与等待：不消费脸部情绪", "花束轻响切监狱登记",
      "Stylized 2D animated documentary scene in a quiet courthouse waiting room, an empty wooden chair beside a small unmarked bouquet, late afternoon light across the floor, no people, no readable text. Camera: one slow push toward the empty chair, hold on the space where someone should be, no cut, no scene change.", "室内空响 + 很轻的呼吸"),
    A("S30", "监狱登记桌横移到铁门", "一九九九年第二起命案后，他终于被判无期", "铁门闭合进入狱中吹嘘",
      "Stylized 2D animated documentary scene in a British prison reception room, gloved hands take a plain fingerprint impression beside a heavy key ring, then the frame settles on a closed steel door, no readable text, no face. Camera: one slow lateral move from the hands to the door, hold on the key turning, no cut, no scene change.", "钥匙串 + 铁门落锁"),
    # N05
    G("S31", "第二起命案卡：强调六年后的再度作案和既有无期刑", "卡片落版后让狱门声先进入下一镜", "二十一岁的阿曼达·沃克\n一九九九年 · 萨里郡\n史密斯因谋杀罪被判终身监禁", "单音钢琴 + 铁门远响"),
    A("S32", "监狱牢房内由墙面横移到两层床", "同仓犯人场景只画牢房和背影，不伪造录音或监控", "低声说话声做桥",
      "Stylized 2D animated documentary scene inside a stark British prison cell, two men are separated by a metal bunk and shown only as silhouettes from behind, one leans toward the other while the other remains still, no faces, no text. Camera: one slow sideways move along the cell wall, hold on the distance between them, no cut, no scene change.", "压低的人声纹理 + 电流声"),
    A("S33", "嘴部不入镜，只拍手指敲床沿与另一只手停住", "把“吹嘘”变成可审查的证人回忆，而不是戏剧化 confession", "敲击声切信息卡",
      "Stylized 2D animated documentary close-up in a prison cell, one large hand taps a metal bunk rail with arrogant rhythm while another hand stops turning a playing card, no faces, no readable text, no violence. Camera: one slow push toward the tapping hand, hold on the stopped card, no cut, no scene change.", "金属敲击三次 + 突然收音"),
    A("S34", "墙面阴影与敲床手部缓慢推近", "让狱中吹嘘成为回声意象，准确文字由后期字幕呈现", "敲击回声切旧案档案盒",
      "Stylized 2D animated documentary scene inside a stark prison cell, a large hand rests on a metal bunk rail while the shadow of a second unseen figure stretches across the wall, no faces, no readable text, no violence. Camera: one slow push toward the hand and its shadow, hold on the empty wall, no cut, no scene change.", "磁带倒转 + 一声回声"),
    A("S35", "档案盒从货架上取下，镜头慢慢压到封条", "旧案重新打开，不展示真实卷宗敏感内容", "封条撕开切法律卡",
      "Stylized 2D animated documentary scene in a dusty police archive, gloved hands pull an old plain case box from a shelf and place it under a desk lamp, the label area is completely blank, no readable text, no face. Camera: one slow push from the dark shelves to the box, hold on the unopened lid, no cut, no scene change.", "档案盒落桌 + 胶带撕裂"),
    G("S36", "解释法律不是完全废除，而是给新证据留窄门", "“新而有力”成为下一个证据镜头的门槛", "法律的窄门\n二零零三年《刑事司法法》\n新的、令人信服的证据，才可重审", "铅笔划线 + 法槌远声"),
    A("S37", "法律文件的手部翻页，镜头不展示可读文字", "二零二二年上诉法院准许重审", "翻页动作匹配指纹证据",
      "Stylized 2D animated documentary scene in a clean appellate court office, a pair of hands turns through blank legal pages and places a plain court seal beside them, no readable text, no faces, no logos. Camera: one slow overhead drift following the page turn, hold on the seal and paper edge, no cut, no scene change.", "纸页快速翻动 + 低频上扬"),
    A("S38", "实验室台面从旧指纹图示移到前屋主资料夹", "指纹归属被重新解释，旧证据因此获得新方向", "扫描仪提示音切最后一章",
      "Stylized 2D animated documentary scene in a forensic laboratory, a gloved technician aligns a generic fingerprint diagram with two blank comparison cards, then slides a plain folder marked by no readable text into frame, no real biometric data, no face. Camera: one slow lateral tabletop move, hold on the aligned cards, no cut, no scene change.", "扫描仪蜂鸣 + 纸面吸附声"),
    # N06
    A("S39", "两份卷宗和一条线绳在桌面上缓慢合拢", "新证据、狱中吹嘘、第二起命案共同闭合证据链", "线绳拉直切重审法庭",
      "Stylized 2D animated documentary scene on a dark legal review table, three plain folders without writing are arranged by gloved hands into a single line, a thin thread is pulled taut between them, no faces, no readable text. Camera: one slow overhead push toward the joined thread, hold on the closed chain, no cut, no scene change.", "线绳拉紧 + 心跳渐强"),
    A("S40", "桌面三份证据由手部依次推成一条线", "新证据三点合拢：卡片字幕稍后叠加，画面不生成文字", "线绳拉直切重审法庭",
      "Stylized 2D animated documentary scene on a dark legal review table, three plain evidence folders, a generic fingerprint diagram and a small audio recorder are pushed into one straight row by gloved hands, no readable text, no faces, no real evidence imagery. Camera: one slow overhead push toward the joined objects, hold on the straight line, no cut, no scene change.", "三次敲击 + 静音半拍"),
    A("S41", "重审法庭内的陪审团背影向前景压近", "二零二三年五月重审，仍不伪造真实庭审镜头", "法槌落下进入判决卡",
      "Stylized 2D animated documentary scene inside a British crown court during a retrial, jury silhouettes are seen from behind while a judge's hands rest above a plain bench, no faces, no readable text, no real courtroom footage. Camera: one slow push from the back of the jury box toward the bench, hold on the hands, no cut, no scene change.", "法庭空气声 + 低频脉冲"),
    A("S42", "法官手部与合上的卷宗特写", "不到三小时裁决成立，用节奏完成高潮", "卷宗合上切刑期卡",
      "Stylized 2D animated documentary close scene of a judge's hands closing a thick plain file and placing a gavel beside it, empty bench in the background, no readable writing, no face. Camera: one slow downward move toward the closed file, hold on the gavel, no cut, no scene change.", "法槌一声 + 长混响"),
    G("S43", "结局卡：终身监禁与最低刑期清楚大字", "卡片停留给观众读完，字幕不抢卡片", "二零二三年五月\n重审定罪 · 终身监禁\n最低刑期二十七年", "低沉钟声 + 音乐转暖"),
    A("S44", "监狱走廊向远处门口慢慢拉远", "两起案件最终都对应到他正在服的无期刑", "走廊回声给金句留空间",
      "Stylized 2D animated documentary scene in a long British prison corridor, a tall figure seen only from behind stands far away as an automatic door closes between him and the camera, cold blue light, no face, no signs, no readable text. Camera: one slow backward dolly away from the door, hold on the narrowing light, no cut, no scene change.", "脚步远去 + 门锁回响"),
    A("S45", "门缝光线缓慢收窄，最后停在黑场前", "把“凶手亲口留下的回声”落到空门和沉默", "最后一句后留一秒，再进片尾卡",
      "Stylized 2D animated documentary scene of a heavy prison door seen from the empty corridor, a narrow strip of warm light under the door slowly disappears, no people, no text, no violence. Camera: locked-off close wide shot with only the light changing, hold on the dark door for the full clip, no cut, no scene change.", "门轴低响 + 一秒无声"),
]

CARD_HEADER = "案件档案  /  英国 · 一九九一—二零二三"
CARD_FOOTER = "资料摘要与示意图 · 并非原始档案影像"
CARDS = {
    "S04": ("大卫·史密斯案", "一九九一年—二零二三年 · 英国", "无罪之后，三十年后重审"),
    "S09": ("双面人生", "卡车司机 · 外号「大脚怪」", "前科升级 · 两起谋杀定罪"),
    "S16": ("两起命案", "萨拉·克拉姆 · 一九九一年", "阿曼达·沃克 · 一九九九年"),
    "S25": ("证据链瑕疵", "一九九三年：现场指纹未被及时解释", "后来查明：指纹属于前屋主"),
    "S27": ("一九九三年", "陪审团裁定：无罪", "证据链瑕疵 · 当庭脱身"),
    "S31": ("二十一岁的阿曼达·沃克", "一九九九年 · 萨里郡", "史密斯因谋杀罪被判终身监禁"),
    "S34": ("狱中一句话", "「我已经逃过了」", "吹嘘，成了三十年后的新证据"),
    "S36": ("法律的窄门", "二零零三年《刑事司法法》", "新的、令人信服的证据，才可重审"),
    "S40": ("三十年后的证据链", "旧指纹归属 · 狱中吹嘘 · 两案相似性", "一罪不二审例外，终于被满足"),
    "S43": ("二零二三年五月", "重审定罪 · 终身监禁", "最低刑期二十七年"),
}
# 仅 S04/S09/S16/S27/S31/S36/S43 作为信息卡进入剪辑；其余卡文案保留为资料库不可用，
# 下面 build() 会检查 kind=graphic 的镜头必须出现在这个子集里。
ACTIVE_CARD_IDS = {"S04", "S09", "S16", "S27", "S31", "S36", "S43"}

TITLE_CARD = ["无罪之后", "大卫·史密斯案 · 三十年翻案"]
END_CARD = [
    "你觉得这扇窄门应该更严格，还是更勇敢？",
    "大卫·史密斯案 · 英国 · 一九九一—二零二三",
    "正义可以迟到，但证据不会替谎言沉默。",
    "资料：BBC / Sky News / Metropolitan Police · 原创解说 · AI动画情景重现",
]
CAPTION_KEYWORDS = [
    "三十年", "大卫·史密斯", "一罪不二审", "假名", "一九九三年", "无罪", "二零零三年", "新证据", "二零二三年五月", "终身监禁",
]
LABEL_OVERRIDES = {
    "S01": "AI动画示意 · 非真实庭审影像",
    "S24": "AI动画示意 · 非真实法院外景",
    "S26": "AI动画示意 · 非真实庭审影像",
    "S28": "AI动画示意 · 非真实庭审影像",
    "S32": "AI动画示意 · 非真实监狱影像",
    "S33": "AI动画示意 · 非真实监狱影像",
    "S37": "AI动画示意 · 非真实上诉文件",
    "S41": "AI动画示意 · 非真实重审影像",
}
SFX_EVENTS = [
    ("S04", "paper"), ("S13", "phone"), ("S21", "machine"), ("S25", "keys"),
    ("S31", "press"), ("S34", "machine"), ("S43", "press"),
]

TITLES = [
    "他被判无罪还向陪审团道谢，30年后却被一句狱中吹嘘钉死",
    "英国最离奇翻案：凶手逃过一次审判，六年后再杀人",
    "“一罪不二审”也能重审？大卫·史密斯案三分钟看懂",
]
HOOK = "他第一次杀人后当庭无罪、道谢离场，六年后再犯案入狱；三十年后，法律修改与一句“我已经逃过了”，让旧案终于翻盘。"
GOLDEN_LINES = [
    "迟到三十年的正义，靠的不是传闻，而是证据留下的回声。",
    "一罪不二审不是给真相关死门，而是只留一扇极窄的证据之门。",
    "你觉得这扇门应该更严格，还是更勇敢？评论区聊聊。",
]
DESCRIPTION = "他曾在英国法庭上被判无罪，走出门时还向陪审团道谢。六年后，他因另一宗谋杀入狱，并在狱中吹嘘自己“已经逃过了”。三十年后，英国一罪不二审规则的例外被启动，旧指纹、狱中吹嘘和两案相似性，让这宗旧案重新回到法庭。三分钟看懂大卫·史密斯案。画面为 AI 动画情景重现，非新闻影像。"
QUESTION = "一罪不二审的例外，你认为应该更严格，还是更勇敢？"
HASHTAGS = ["#悬疑科普", "#真实案件", "#英国刑案", "#法律科普", "#AI动画情景重现"]

GRID = 4
AGNES_SECONDS = 7
SEED_BASE = 20260924


def presentation():
    return {
        "card_header": CARD_HEADER,
        "card_footer": CARD_FOOTER,
        "cards": {sid: list(lines) for sid, lines in CARDS.items() if sid in ACTIVE_CARD_IDS},
        "title_card": TITLE_CARD,
        "end_card": END_CARD,
        "caption_keywords": CAPTION_KEYWORDS,
        "label_overrides": LABEL_OVERRIDES,
        "sfx_events": [list(e) for e in SFX_EVENTS],
    }


def build():
    story = json.loads(PLAN.read_text(encoding="utf-8"))
    if len(SHOTS) != 45 or len(SHOTS) * GRID != 180:
        raise AssertionError(f"需要 45 镜 × 4 秒，当前是 {len(SHOTS)} 镜")
    if len({sid for sid, *_ in SHOTS}) != len(SHOTS):
        raise AssertionError("镜头号重复")
    if len(CHAPTERS) != 6 or len(story["chapters"]) != 6:
        raise AssertionError("需要六段解说")
    cards_needed = {sid for sid, kind, *_ in SHOTS if kind == "graphic"}
    if cards_needed != ACTIVE_CARD_IDS:
        raise AssertionError(f"信息卡集合不一致：镜头是 {sorted(cards_needed)}，配置是 {sorted(ACTIVE_CARD_IDS)}")
    for sid in cards_needed:
        if sid not in CARDS:
            raise AssertionError(f"信息卡缺文案：{sid}")

    story["title"] = TITLE
    story["style_prefix"] = STYLE_PREFIX
    story["negative_prompt"] = NEGATIVE_PROMPT
    story["principles"] = PRINCIPLES
    story["sources"] = SOURCES
    for chapter, (cid, title, text) in zip(story["chapters"], CHAPTERS):
        if chapter["id"] != cid:
            raise AssertionError(f"章节编号不匹配：{chapter['id']} / {cid}")
        chapter.update(title=title, text=text)

    shots = []
    for index, (sid, kind, camera, purpose, transition, body, sfx) in enumerate(SHOTS):
        expected = f"S{index + 1:02d}"
        if sid != expected:
            raise AssertionError(f"镜头必须连续：期望 {expected}，得到 {sid}")
        if kind not in ("agnes", "graphic"):
            raise AssertionError(f"{sid}: kind 只能是 agnes / graphic")
        if kind == "agnes" and not body.strip():
            raise AssertionError(f"{sid}: Agnes prompt 为空")
        if kind == "graphic" and not body.strip():
            raise AssertionError(f"{sid}: graphic cue 为空")
        start = index * GRID
        shots.append({
            "id": sid,
            "kind": kind,
            "start": start,
            "duration": GRID,
            "narration_id": f"N{min(6, start // 30 + 1):02d}",
            "prompt": body if kind == "agnes" else "",
            "purpose": purpose,
            "transition_out": transition,
            "graphic": body if kind == "graphic" else "",
            "seed": SEED_BASE + index + 1,
            "seconds": AGNES_SECONDS,
            "aspect": "16:9",
            "resolution": "1080p",
            "frame_rate": 24,
            "camera": camera,
            "sfx_note": sfx,
        })
    story["shots"] = shots
    story["presentation"] = presentation()
    story.setdefault("_scaffold", {})["note"] = (
        "内容由 build_story.py 一次性写入；45 镜 × 4 秒规划网格（38 Agnes + 7 信息卡，每镜只用一次）；"
        "解说词与 screenplay.md、audio/manifest.json 三处逐字一致由 generate.py --validate 守着。"
    )
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["language"] = "zh-CN"
    manifest["voice_id"] = "voice-00"
    manifest["selection"] = "用户试听选定的教育/解说音色 voice-00"
    manifest["post_processing"] = "raw TTS → tighten_pauses.py：只剪停顿，不改字；audio/N0x.mp3 为成片绑定文件。"
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        if clip["id"] != chapter["id"]:
            raise AssertionError(f"音频章节不匹配：{clip['id']} / {chapter['id']}")
        clip["text"] = chapter["text"]
        clip["file"] = f"{chapter['id']}.mp3"
        clip["sha256"] = ""
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    kind_counts = {kind: sum(s["kind"] == kind for s in shots) for kind in ("agnes", "graphic")}
    print(f"story.json 已写入：45 镜 = {kind_counts['agnes']} agnes + {kind_counts['graphic']} graphic，解说 {sum(len(c['text']) for c in story['chapters'])} 字（含标点）")


if __name__ == "__main__":
    if "--script" in sys.argv:
        from script_table import render_document
        out = HERE / "抖音脚本.md"
        out.write_text(render_document(), encoding="utf-8")
        print(f"抖音脚本.md 已写入（{len(out.read_text(encoding='utf-8'))} 字符）")
    elif "--publish" in sys.argv:
        from script_table import publish_document
        out = HERE / "抖音发布文案.md"
        out.write_text(publish_document(), encoding="utf-8")
        print(f"抖音发布文案.md 已写入（{len(out.read_text(encoding='utf-8'))} 字符）")
    else:
        build()

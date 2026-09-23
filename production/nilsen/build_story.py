#!/usr/bin/env python3
"""《克兰利花园23号：下水道里的十五个人》的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

内容依据：用户 2026-09-23 通过上传台提交的 Word 需求表（`incoming_uploads/1790075507040.docx`，
七段四列分镜 + 三个备选标题 + 金句结尾）+ 公开报道核查。与原表不一致的地方全部记在
`制作过程.md` 的「与需求表的差异」一节，核心一条：**他在就业中心是保安，不是给失业者办业务的职员**，
所以「白天帮人找工作」这句改写成「白天给来找工作的人开门」。

用法::

    python3 production/nilsen/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/nilsen/build_story.py --script   # 生成 抖音脚本.md（3 标题 / 核心爆点 / 四列分镜表 / 金句）
    python3 production/nilsen/build_story.py --publish  # 生成 抖音发布文案.md（标题 / 介绍 / 提问读者一句话 / 话题）

写法规则（都是吉尔戈那部踩出来的，别省）：

- 六段解说合计 ≈ 760–800 字（含标点），TTS 收紧停顿后 ≈ 176 秒；每段末尾留一个钩子；
  数字一律写成中文读法（"二月八号""百分之九十九"），TTS 和字幕才一致；
  不写血腥/侵害过程的具体描写（TTS 审核会拒，红线也不允许）。
- 45 镜 = 38 个 Agnes 动画镜头 + 7 张信息卡，按成片顺序编号，**每个镜头只出现一次**。
- 提示词先钉死“唯一场景”，再排除别的场景，最后加 HOLD 句；想去掉天际线就别给地平线。
- 人只能是背影、剪影、手；画面里不许有可读文字；不出现遗体、暴力动作。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"

TITLE = "克兰利花园23号：下水道里的十五个人"

# 全片统一的画面风格前缀（英文）。注意：style_prefix 参与全部 Agnes 镜头的 request_hash，
# 开工后改一个字 = 38 镜全部重做。
STYLE_PREFIX = (
    "Stylized 2D animated documentary illustration with hand-painted graphic-novel textures and soft "
    "cel shading, north London 1978 to 1983 and a Scottish fishing town in the 1950s: damp Victorian "
    "brick conversions with narrow stairwells, brown-painted woodwork and patterned wallpaper, cast-iron "
    "drain pipes and a bricked manhole at the kerb, Soho pub frontages glowing amber on wet pavement, "
    "council-garden brick sheds and coal braziers, harbour cottages with nets and rope; wool overcoats, "
    "flared trousers, enamel mugs, boxy televisions. Horizontal 16:9 cinematic composition, muted palette "
    "of slate blue, wet asphalt grey and sodium-orange practical light, restrained procedural true-crime "
    "mood, film grain, no horror excess; every character is shown only from behind, in silhouette, or as "
    "hands and props - never a clear frontal face; absolutely no readable text, letters, numbers, logos, "
    "license plates, posters or brand marks anywhere inside the frame; one single continuous smooth slow "
    "camera move per shot exactly as directed. "
)

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, invented headlines, logos, brand marks, "
    "watermark, subtitles, on-screen caption, photorealistic face, recognizable real person likeness, "
    "frontal face close-up, eyes visible in detail, blood, gore, wound, corpse, body bag, body parts, "
    "autopsy, violence, assault, strangling, weapon attack, gun, firearm, nudity, erotic content, horror "
    "monster, ghost, jump scare, 3D render look, plastic CGI, distorted anatomy, deformed hands, extra "
    "fingers, extra limbs, duplicated people, changing face, morphing objects, teleportation, jitter, "
    "flicker, whip pan, fast zoom, jump cut, split screen, collage"
)

# 事实边界与红线：每一条都会印在 抖音脚本.md 的「发布前自查」里。
PRINCIPLES = [
    "全部 Agnes 镜头为风格化 2D 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，不冒充庭审、监控或证物照片",
    "不展示遗体、血腥或侵害过程；侵害与毁尸都不做画面重现，镜头只停在门、管道、空床、喷过的杀虫剂这些「之后」的东西上",
    "真实人物只以背影、剪影、手部出现，不用 AI 生成的脸冒充本人；尼尔森的照片有出处但不能当画面主体",
    "受害者不以任何人像出现（包括背影），只用遗物、空位与信息卡致意",
    "每一句事实都能指到 sources 里的一条公开报道；口径不一致的地方（受害者人数、衣柜里遗骸的数量）在片子里只用「他说」和「法庭审理查明」两种说法，不下自己的结论",
    "未起诉的事不写成判决：第一个受害者斯蒂芬·霍姆斯一案，皇家检控署决定不起诉，片里只说「对上名字」",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写",
    "同一地点保留光线、道具、运动方向；跨地点通过水声、门声与物件匹配衔接",
    "人工检视 qa/ 接触表，露脸、畸变、伪文字、中途换场的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

# 每条事实的公开来源。
SOURCES = [
    {"id": 1, "url": "https://en.wikipedia.org/wiki/Dennis_Nilsen",
     "usage": "生卒与地点（1945-11-23 弗拉伯勒 / 2018-05-12 约克医院）、定罪六项谋杀+两项谋杀未遂、"
              "1983-11-04 判终身并建议最低25年、1994年12月改为 whole life、晚年关 HMP Full Sutton、"
              "受害者12—15人、杀害方式为勒扼（有时伴随溺水）、事后洗净穿衣长期留置、"
              "祖父是渔民且1951-10-31死于北海船上、灵柩抬回家中、母亲让他看最后一眼"},
    {"id": 2, "url": "http://news.bbc.co.uk/onthisday/hi/dates/stories/october/24/newsid_3184000/3184987.stm",
     "usage": "1983-10-24 中央刑事法院开庭、开庭年龄37岁、被告自称杀了15或16人、"
              "八名受害者身份未识别、在酒吧物色对象（多为无家可归者、男妓）、以酒与住处为饵、"
              "用领带勒颈、藏地板下或冲入厕所、军队食堂服役学过屠宰、1974年起在人力委员会做保安、"
              "梅尔罗斯大街住所起出至少八具遗骸的骨头"},
    {"id": 3, "url": "https://www.crimeandinvestigation.co.uk/crime-files/dennis-nilsen",
     "usage": "1981年迁入克兰利花园23号顶楼（无花园、无地板可藏）、每天两次喷杀虫剂压味、"
              "对邻居说是房子结构问题、租客报堵后疏通工在检查井发现遗骸、他当晚自行清理管道被楼下租客看见、"
              "1983-02-09 晚 DCI Jay 上门、他平静指认衣柜里的黑色袋子（含两颗头颅）、"
              "供词在庭上被逐字宣读四个多小时、三名幸存者出庭作证、辩方精神鉴定被检方反驳、"
              "1983-11-03 陪审团未能一致、次日多数裁定、判至少25年"},
    {"id": 4, "url": "https://www.mirror.co.uk/tv/tv-news/dennis-nilsen-plumber-pulled-lumps-22695556",
     "usage": "疏通工 Michael Cattran 第一现场口述：1983年2月8日夜里下井、闻到恶臭、"
              "掏出拳头大小的肉块与像从手臂上切下来的条状物、次日返回时证据已被冲走、"
              "只剩一小块带毛的肉与几根小骨、1983-02-09 被捕"},
    {"id": 5, "url": "https://www.esquire.com/entertainment/tv/a37331971/memories-of-a-murderer-dennis-nilsen-now/",
     "usage": "Netflix 纪录片《Memories of a Murderer》背景：1978—1983 在伦敦街头物色弱势男性、"
              "最终因住所管道堵塞案发，而非因失踪者报案"},
    {"id": 6, "url": "https://www.telegraph.co.uk/news/uknews/1533738/Nilsen-describes-how-he-murdered-his-first-victim.html",
     "usage": "第一个受害者身份：14岁的 Stephen Dean Holmes，1978年底在 Cricklewood Arms 被带走、"
              "身上无身份证件、2006年1月家人提供更清晰照片后尼尔森当面指认、"
              "2006年11月从 Full Sutton 监狱致信《伦敦晚旗报》"},
    {"id": 7, "url": "https://www.crimelibrary.org/serial_killers/predators/nilsen/15.html",
     "usage": "1990年警方曾拿一张模糊照片给他，未能指认；2006年仍有7名受害者未识别；"
              "该起杀害霍姆斯的罪名未被起诉（检方认为起诉不符合公共利益）"},
    {"id": 8, "url": "https://murderpedia.org/male.N/n/nilsen-dennis.htm",
     "usage": "被捕押送途中被问「一具还是两具」，答「十五或十六个，从1978年起」；"
              "为记不清确切人数向警方道歉；前住所花园起出大量碎骨；"
              "1979年把首名死者移出自家地板下在花园焚化，尸体八个月未被发现"},
    {"id": 9, "url": "https://razs-midnight-macabre.com/2013-12-04/real-life-horror-dennis-nilsen/",
     "usage": "1979-10 香港留学生 Andrew Ho 被勒后逃脱报警、未起诉；"
              "1980-11-10 Douglas Stewart 报案，警方视为同性情侣纠纷、只做了记录；"
              "焚尸时加入橡胶遮盖气味；1983-02-05 前后 Dyno-Rod 到场经过（与来源4互补，日期口径以来源3/4为准）"},
    {"id": 10, "url": "https://www.factualamerica.com/behind-the-screenplay/des-unmasking-the-real-dennis-nilsen",
     "usage": "DCI Peter Jay 带队、1983-02-09 晚在寓所门口被三人等候、进屋闻到气味后当场坦白、"
              " ITV 剧集《Des》所据的真实细节（作背景印证用）"},
    {"id": 11, "url": "https://history.scot/serial-killer-dennis-nilsens-first-killing/",
     "usage": "首个受害者为 1978-12-30 在弗拉伯勒出生的苏格兰少年一案的时间线、"
              "1979-08-11 焚尸、《爱尔兰时报》2006-01-13 关于卷宗复查后才把失踪案与尼尔森对上的报道、"
              "利物浦回声报记载陪审团以10比2多数裁定"},
    {"id": 12, "url": "https://www.ladbible.com/news/uk-serial-killer-dennis-nilsen-dies-in-prison-aged-72-20180513",
     "usage": "2018-05-13 报道其死于狱中，终年72岁；1983年量刑与1994年改判终身不得假释的表述"},
    {"id": 13, "url": "https://www.murdermap.co.uk/historical-murders/the-serial-killer-next-door-dennis-nilsen/",
     "usage": "克兰利花园五个同住租客、无人了解他；顶楼阁楼间、长期留置遗体后再处理；"
              "「邻居眼里的普通人」这一叙事背景"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。
CHAPTERS = [
    ("N01", "黄金开头：一条堵住的下水道",
     "一九八三年二月，伦敦北部一栋老公寓，下水道堵了。疏通工钻进屋外的检查井，从管壁上掏下一大团泡白的东西，还有几截像手指的。他先把工头叫下来一起看，再报警。当晚警察上了顶楼，开门的男人只说了一句：东西都在衣柜里。路上有人问他，是一具还是两具，他说，十五个，或者十六个。"),
    ("N02", "他是谁",
     "他叫丹尼斯·尼尔森，一九四五年生在苏格兰渔港弗拉伯勒。父亲是挪威兵，父母一九四八年离婚，他等于没了父亲。他唯一亲近的人是当渔民的祖父；一九五一年，祖父死在北海的渔船上，母亲让他看最后一眼，说祖父睡着了。他在军队食堂学过屠宰，退伍后在就业中心当保安：白天给找工作的人开门，晚上去酒吧找人。"),
    ("N03", "他挑的都是没人找的人",
     "动手是从一九七八年冬天开始的。他挑的，大多是没人会去找的人：离家出走的、睡车站的、出来卖的男人。他把人带回自己家，给饭、给酒、给一张床；凌晨趁人睡着，用领带。之后他把人洗干净、换上衣服摆在床上，跟他们说话，一起看电视，一放就是几个星期。房子有花园，他就架火，往火里扔橡胶盖味道。"),
    ("N04", "把邻居逼疯的味道",
     "一九八一年十月，他搬到克兰利花园二十三号的顶楼，没有花园，也没有地板可以藏。他改成把东西煮散、冲下去。整栋楼五户人，厕所一天比一天慢；邻居投诉有味道，他每天喷两遍杀虫剂，说房子结构有问题。二月八号疏通公司来了人，第二天他再来时，井盖被挪过位，管壁上只剩一小块刮不干净的东西。这一次，警察没有被劝回去。"),
    ("N05", "四个半小时的供词",
     "他配合得让办案的人心里发毛：说不准确切的人数，还为此道歉；整晚的供词在法庭上被逐字念了四个多小时。一九八三年十月二十四日，中央刑事法院开庭，辩方说他有精神疾病。活下来的人出庭作证：有人被掐醒后逃出来报过警，警方当成情侣纠纷，做了记录就再没下文。十一月四日，六项谋杀、两项未遂成立，至少服满二十五年。"),
    ("N06", "二十八年，才对上一个名字",
     "一九九四年十二月，内政大臣把那二十五年改成永远不用出去。二〇一八年五月，他在监狱医院死于手术后并发症，七十二岁。开庭那年，八个死者连名字都没有；第一个死的是个十四岁男孩，一九九〇年拿照片去问，他没认出来，二〇〇六年才靠家人换的照片对上名字：斯蒂芬·霍姆斯。有些人失踪，不会有人报案。"),
]

# 每一镜：(id, kind, 运镜, 叙事职责, 衔接方式, 英文提示词 或 信息卡说明, 音效/备注)
SHOTS = [
    # ---------------- N01 黄金开头（8 镜）----------------
    ("S01", "agnes", "缓慢推近 slow push-in",
     "0—5 秒钩子前的“日常”：冬夜，北伦敦一栋维多利亚式改造公寓的正立面，顶楼一扇窗亮着黄光，湿街反光",
     "推近到门廊，硬切检查井口",
     "Winter night on a quiet north London residential street, a three-storey Victorian brick conversion converted into flats, "
     "sash windows, a damp-blue front step, one top-floor window glowing warm yellow, wet asphalt reflecting it, a lone bin and a "
     "bicycle against the wall; the brick facade and a tall hedge fill the frame from edge to edge so no sky, no horizon and no "
     "distant buildings are visible; no people. Camera: one slow push-in from the kerb toward the glowing top-floor window. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "远处交通声、水滴；低频垫底进"),
    ("S02", "agnes", "下摇入井 tilt down",
     "检查井内部：手电光柱扫过砖砌管壁，管壁上挂着灰白的絮状堵塞物（不给可辨认的东西），戴手套的手拿着钩子",
     "光柱停在堵塞物上，切井口两个背影",
     "Inside a brick Victorian sewer manhole at night, torch beam cutting through mist: curved soot-blackened brickwork, "
     "grey saturated sludge and clinging fibrous blockage smeared along the crown of the pipe, a small pool of water at the invert, "
     "a workman's gloved hand holding a hooked steel rod entering from the top of frame; only the hand and forearm are visible. "
     "Confined brick tunnel fills the entire background: no street, no sky, no second location. "
     "Camera: one slow tilt down the brick wall into the water. The entire clip stays in this single framing: no cut, "
     "no scene change, no camera relocation.",
     "水滴回声、金属钩刮到管壁一声；解说「掏下来一大团」处给这一镜"),
    ("S03", "agnes", "低角度固定 static low angle",
     "工头到场：井口两个戴工帽的男人俯身往下看（只给背影与肩），路灯把他们的影子投到墙上",
     "其中一人转身走向路边电话，接 S04",
     "Night-time kerbside view looking up at the open manhole cover of a north London street: two workmen in flat caps and "
     "heavy coats crouch at the rim, seen only from behind and above the shoulders, torch beams crossing inside the pit, "
     "their breath visible in cold air, a lamp-post throwing long shadows onto the brick wall of the house behind them; "
     "no faces, no readable text anywhere. Camera: locked-off low angle from the drain cover upward. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "呼吸声、井壁滴水；「先把工头叫下来一起看」"),
    ("S04", "agnes", "手持微晃 hand-held drift",
     "报警：夜里的公用电话亭/路边电话，一只手握着听筒，另一只手在笔记本上按着（纸面空白不可读）",
     "听筒挂回去的回音接顶楼楼道",
     "A 1980s British street telephone box at night, camera inside the box looking out through the"
      "open doorway: the black receiver hangs on its cord near the top left, and only one gloved hand"
      "and short forearm enters from the bottom edge of the frame to hold it - the forearm stays"
      "attached to the lower frame edge and never grows longer, dark wool sleeve; a folded blank paper"
      "and an enamel mug sit on the small metal shelf, rain and one lit terraced street are visible"
      "beyond the glass, a single warm lamp inside the box. Nothing else is visible: no faces, no"
      "numerals, no lettering, no signage, no second location, and no new object enters the frame after"
      "the first second. Camera: nearly locked-off with a faint drift toward the receiver. The entire"
      "clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "投币、拨盘、远处警笛渐入；「再报警」"),
    ("S05", "graphic", "信息卡 static card",
     "案件名片：案名、地点、年代、规模（不依赖 AI 拼字）",
     "卡片入场「咔」一声，硬切顶楼楼道",
     "本案第一张卡：用一张干净的资料卡交代案名、地点、年代、受害者规模，替观众建立坐标",
     "卡片入场「咔」"),
    ("S06", "agnes", "跟拍背影 follow from behind",
     "警察上顶楼：一条窄楼道，壁纸剥落，三个穿大衣的背影站在半开的门前，门缝里漏出暖光",
     "门被推开，镜头留在门缝的光上，切衣柜",
     "A narrow first-floor landing inside a Victorian London flat conversion, peeling floral wallpaper, brown painted woodwork, "
     "a bare ceiling bulb, three men in long overcoats standing with their backs to camera outside a part-open door, warm light "
     "spilling through the gap onto the scuffed floorboards; the corridor walls fill the frame from edge to edge, no windows, "
     "no view outside; no faces. Camera: one slow dolly forward along the landing toward the open door. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "木楼梯吱呀、大衣摩擦；「当晚，警察上了顶楼」"),
    ("S07", "agnes", "焦点转移 rack focus",
     "衣柜里的黑色袋子：老式木衣柜半开，里面两三个用绳子扎口的黑色塑料垃圾袋，旁边挂着大衣",
     "手电光扫过袋口，切警车雨窗",
     "Interior of a sparsely furnished 1980s attic bedroom lit by a torch beam: a tall wooden wardrobe standing open against a "
     "slanted plaster wall, inside it two or three black plastic refuse sacks tied with string stacked on the shelf, coats "
     "hanging on a rail in the foreground, a bare light bulb and a folded blanket on a bed at the edge of frame; "
     "camera never reveals anything inside the sacks and no body is shown; the slanted ceiling and wardrobe fill the background, "
     "no window and no skyline. Camera: one slow rack focus from the coats to the open wardrobe. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "塑料袋窸窣、手电开关；「东西都在衣柜里」落点后停半秒"),
    ("S08", "agnes", "车内固定 static interior",
     "「十五个，或者十六个」：雨夜警车后座视角，前挡风湿扇摆动，窗外公寓门廊的灯还亮着，前排副驾一个瘦高男人的侧后剪影",
     "雨刷把街灯扫成一条光，接第二章档案卡",
     "Back-seat point of view inside a 1980s British police car at night: through the rain-streaked"
      "windscreen a blurred amber residential street and one lit doorway slide past, wipers mid-sweep;"
      "in the front seats a uniformed driver with a peaked cap on the left and, to the right, a thin"
      "man in a damp dark overcoat seen from behind and slightly to one side, head turned toward the"
      "window, collar up, no face visible; interior roof light off, only dashboard glow; no legible"
      "markings, badges or numbers on the doors or the dashboard. Camera: locked-off static from the"
      "rear seat. The entire clip stays in this single framing: no cut, no scene change, no camera"
      "relocation.",
     "雨刷、引擎怠速；「十五个，或者十六个」这句落在这一镜尾音"),
    # ---------------- N02 他是谁（7 镜）----------------
    ("S09", "graphic", "档案卡 static card",
     "人物档案卡：姓名、生卒、职业、两处地址、定罪范围（全部公开报道）",
     "卡片硬切 1950 年代海港",
     "第二张卡：人物档案，交代他是谁、在哪儿长大、做什么工作、被定了什么罪",
     "打字机式逐行出现；不放本人照片（红线）"),
    ("S10", "agnes", "缓慢横移 slow lateral track",
     "弗拉伯勒的童年：五十年代苏格兰渔村海堤，一个小男孩坐在祖父肩头，两人沿堤走向沙丘（全背影）",
     "横移到沙丘边缘，切风暴后的港口",
     "A 1950s Scottish fishing harbour on a pale cold morning: a weathered stone sea wall, wooden fishing boats, nets drying on "
     "frames, whitewashed cottages with slate roofs, a small boy sitting on an old fisherman's shoulders seen only from behind, "
     "the man's hands on the child's boots, gulls above; low dunes and sea grass fill the horizon so no modern buildings appear. "
     "Camera: one slow lateral tracking move along the sea wall keeping the pair in the middle distance. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "海鸥、缆绳吱响；悲伤钢琴第一次进"),
    ("S11", "agnes", "推近 slow push-in",
     "1951 年 10 月，风暴后的港口：翻扣的渔船、湿缆绳，岸上一排妇女的背影聚着，没有人动",
     "一个背影转身往村里走，镜头留在空荡的海面",
     "The morning after a storm on a 1950s Scottish fishing quay: an upturned wooden boat with a split hull on shingle, "
     "soaked coils of rope, scattered creels, grey flat sea under a low cloud; a line of women in headscarves and long dark "
     "coats stand with their backs to camera at the edge of the quay, motionless, nobody's face visible; "
     "the harbour wall and cottages fill the frame's far edge. Camera: one slow push-in toward the standing figures. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "浪、旗绳敲桅杆；音乐抽掉只剩浪"),
    ("S12", "agnes", "门框固定 static doorway",
     "灵柩抬回家：客厅门框视角，拉上的窗帘、桌上一个花圈、一把空椅子，一个小男孩的背影站在门槛",
     "焦点从花圈转到孩子背影，切军队厨房",
     "A 1951 Scottish parlour seen from the doorway: heavy curtains drawn, a wreath of white flowers and green ferns on a "
     "wooden table beside an empty upholstered chair, a clock on the sideboard, a gas fire low, thin daylight at the curtain "
     "edge; a small boy in a too-big coat stands just inside the threshold with his back to camera, hands at his sides; "
     "no coffin in frame, no faces, no readable text. Camera: static from the doorway with one slow rack focus from the wreath "
     "to the child's back. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "挂钟摆、极轻的抽泣（远）；「说祖父睡着了」"),
    ("S13", "agnes", "横摇 slow pan",
     "军队食堂学的手艺：六十年代英军伙房，白搪瓷、铜锅、长条木工作台、墙上一排干净的厨具，一个白围裙背影在擦台面",
     "围裙带子在画面里被拉紧，切就业中心大厅",
     "Interior only, four tiled walls: a 1960s British Army kitchen at the end of service, white-tiled"
      "walls and a pale green dado filling the frame from edge to edge, long scrubbed steel tables"
      "stacked with enamel mess trays, copper pots hanging on a rail, a row of plain wooden chopping"
      "boards on hooks, an apron on a nail, flour dust floating in the light from one high window; a"
      "cook in a white jacket and cap stands at the far table with his back to camera, wiping the"
      "surface with a cloth; no courtyard, no open sky, no exterior stair, no television, no food, no"
      "meat, no blade raised, no faces. Camera: one slow lateral track along the row of tables. The"
      "entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "搪瓷磕碰、擦台面的布声"),
    ("S14", "agnes", "大全景固定 static wide",
     "就业中心的一把椅子：七十年代末劳工交易所大厅，木柜台、等号牌、长椅上背影排队，门边一个小保安亭里坐着一个人",
     "大厅灯一排排熄灭，切夜晚酒吧门口",
     "Interior of a late-1970s British employment exchange hall seen from the far end: rows of men in"
      "flat caps and anoraks sitting on wooden benches with their backs to camera, a long glazed"
      "partition of blank frosted panels, polished terrazzo floor reflecting high windows, and a"
      "uniformed security guard standing inside a small open booth beside the entrance doors, seen from"
      "behind with one hand resting on the door-release button; every panel, board and frame in the"
      "hall is empty - no letters, no numbers, no notices, no signage of any kind; no faces. Camera:"
      "locked-off wide from the far end, only the seated crowd shifts slightly. The entire clip stays"
      "in this single framing: no cut, no scene change, no camera relocation.",
     "人声嗡嗡、门铃一声；字幕高亮「保安」"),
    ("S15", "agnes", "缓慢跟拍 slow follow",
     "苏荷的夜晚：湿石板上霓虹反光，两个男人背影推开一家酒吧的门，门里暖光溢出到街上",
     "门合上，画面暗下去，进第三章",
     "Night, early 1980s Soho: a tight shot framed only on an open doorway and the backs of two men in"
      "long dark coats walking through it, so close that the surrounding brick wall is outside the"
      "frame on both sides. Inside the doorway: warm bare bulbs, painted wood doorframe, a hallway"
      "beyond with a coat hook and nothing else. The frame contains no wall surface at all - therefore"
      "no house number, no nameplate, no brass plate, no letterbox, no poster, no sign, no numeral, no"
      "letter, no written word anywhere in the picture. Only the backs of heads and shoulders of the"
      "two men, no faces, no ground, no pavement, no street, no vehicles. Camera: held close behind"
      "them, ending as the door edge sweeps across the lens and the frame goes dark. The entire clip"
      "stays in this single framing: no cut, no scene change, no camera relocation, nothing new"
      "appears.",
     "门轴、室内笑声一瞬即断；「晚上，他去苏荷的酒吧找人」"),
    # ---------------- N03 手法与留置（8 镜）----------------
    ("S16", "agnes", "吧台特写推近 bar-top push-in",
     "把人带回家的那套：吧台上一只推过来的啤酒杯、一枚硬币、一只手把另一只空杯转过去（只拍手与杯子）",
     "杯壁的泡沫下沉，切公寓厨房的炉子",
     "Close-up across a polished Victorian pub bar top in warm low light: a half-full beer glass pushed slowly toward the far "
     "end of the bar by a hand in a dark cardigan sleeve, an old brass coin and a folded bar mat beside it, condensation on the "
     "wood, bottles blurred on the back bar; only hands are visible; no faces, no legible labels, no signage. "
     "Camera: one slow push-in along the bar top following the glass. The entire clip stays in this single framing: no cut, "
     "no scene change, no camera relocation.",
     "玻璃滑过木面的声音、杯垫落地；「给饭、给酒、给一张床」"),
    ("S17", "agnes", "炉火前固定 static stove",
     "深夜的厨房：煤气炉上两只杯子在烧，水汽顶起壶盖，桌上一块面包、一把钥匙",
     "水汽糊满镜头，切卧室门缝",
     "A small 1980s council flat kitchen just after midnight: a green enamel gas cooker with one ring lit, a dented steel kettle "
     "lifting its lid with steam, two chipped mugs on a oilcloth table, a bread bin, a set of keys and a folded coat on a chair; "
     "cream lino floor and a half-closed back door with a strip of streetlight under it; no people in frame; "
     "the tiled kitchen wall fills the background. Camera: static medium shot with steam slowly fogging the lens. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "水壶、燃气嗡鸣；音乐降一层"),
    ("S18", "agnes", "门缝视角 doorframe peep",
     "凌晨之后：卧室门缝里，台灯还亮，一个瘦高男人背对镜头坐在床沿，床上被子隆着一个人形，一动不动",
     "门缝被光填满，切客厅电视机",
     "A dim 1980s bedroom seen through a half-open door: a narrow gap of warm lamp light, a single man in a white shirt sitting "
     "on the edge of a double bed with his back to camera, elbows on knees, utterly still; the bedclothes beside him rise in a "
     "long shape under a patterned blanket, no body part or skin visible, nothing suggestive; a wardrobe, a lampshade, "
     "and a slanted ceiling fill the frame; no faces, no readable text. Camera: static, framed tight in the door gap. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "只留台灯的电流声；静 1.5 秒"),
    ("S19", "agnes", "缓慢推近 slow push-in",
     "「跟他们说话，一起看电视」：客厅里电视机雪花光闪在拉上的窗帘上，沙发和扶手椅之间地板上整齐摆着一双年轻人的鞋",
     "雪花光闪到最亮处硬切",
     "A 1980s living room at night with the curtains drawn: a boxy television throwing flickering blue-white snow-light across "
     "a patterned carpet, a settee and an armchair angled toward it, a cigarette burn in the carpet, a tea cup on a side table; "
     "on the floor between the two seats a pair of young man's trainers are placed neatly side by side, nobody wearing them; "
     "no people, no faces, no readable text on screen. Camera: one slow push-in toward the pair of shoes. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "电视雪花、极远处的狗叫；「跟他们说话」"),
    ("S20", "graphic", "时间线卡 static card",
     "时间跨度卡：1978年12月30日 → 1983年2月9日、两处地址、五个年份里发生什么",
     "卡片右下角的时间线划到尽头，切花园",
     "第三张卡：把五年时间轴和两个作案住址摆在一张卡上，替观众记住「不是一个人一夜之间变坏的」",
     "纸面翻动声"),
    ("S21", "agnes", "缓慢横移 slow lateral track",
     "后花园的傍晚：砖墙、铁皮棚、一个烧着的金属火盆冒白烟，晾衣绳上的床单被风吹起，一个人影在烟后面弯腰（无脸）",
     "床单落下来挡住画面，掀开时已是地板",
     "A north London back garden at dusk in winter: high brick wall, a corrugated shed, a washing line with a white sheet "
     "lifting in the wind, a round metal coal brazier sending up thick pale smoke among bare fruit trees, a crouching silhouette "
     "behind the smoke with its back turned, only shoulders and arms visible; nothing is being burned that the viewer can "
     "identify; the brick wall fills the entire background, no skyline; no faces. Camera: one slow lateral track along the "
     "wall. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "铁皮被风敲、炭爆一声；「往火里扔橡胶」"),
    ("S22", "agnes", "俯视固定 static top-down",
     "地板：掀开的几条旧木地板，一根撬棍斜放着，手电光扫过空荡的地板槽（什么都不露）",
     "光扫到尽头熄灭，切挂着的大衣",
     "Top-down view of a Victorian flat's floor where several boards have been levered up: bare joists and dark air gap, "
     "a rolled carpet, a crowbar resting across the gap, a torch beam sweeping slowly across the empty space, dust motes in the "
     "light; the space under the floor is shown empty and shadowed, nothing is revealed inside it; no people, no faces. "
     "Camera: locked-off overhead with the torch beam as the only movement. The entire clip stays in this single framing: "
     "no cut, no scene change, no camera relocation.",
     "木板回位一声闷响；此处不加音乐"),
    ("S23", "agnes", "静物缓推 still-life push-in",
     "「一放就是几个星期」：玄关的一根衣帽架，一件旧大衣和一顶帽子，旁边一只扣好的旅行包，光在墙上慢慢移动",
     "光移尽，第四章开头从窗户的雨接进来",
     "A narrow hall of an attic flat on a grey afternoon: a wooden hat stand holding a damp dark overcoat and a flat cap, "
     "a closed holdall on the floor beneath it, a coat button catching light, the stair door at the end of the passage slightly "
     "open onto darkness, dust drifting in a shaft of clouded daylight from a high window; no people, no readable labels. "
     "Camera: one very slow push-in down the passage toward the coat. The entire clip stays in this single framing: no cut, "
     "no scene change, no camera relocation.",
     "挂钟、楼下门铃很远；「第一个死的人，十四岁」在此镜尾"),
    # ---------------- N04 搬家与管道（7 镜）----------------
    ("S24", "graphic", "搬家卡 static card",
     "第四张卡：1981年10月搬进克兰利花园23号顶楼——没有花园、没有地板，只剩厕所",
     "卡片消失时留一行「于是有了第二条路」的字幕感（文字后期加，AI 不写字）",
     "这张卡解释「为什么改成冲下去」，是全片因果的铰链，必须清晰",
     "「咔」一声；接水管的水声"),
    ("S25", "agnes", "缓慢下摇 tilt down",
     "顶楼房间：斜天花板、老虎窗、一盏吊灯、空房间，只有雨点打在窗上",
     "摇到地板上的水管穿楼板处，切水槽下",
     "An empty top-floor attic room in a London conversion, 1981: a sloped plaster ceiling, a single bare pendant bulb, "
     "a small dormer window with rain running down the old glass, a bare floorboard with a short length of lead pipe and its "
     "iron collar where it passes through the ceiling rose, a radiator with a bleeding key resting on it; no furniture of "
     "value, no people; rain on the glass is the only movement. Camera: one slow tilt from the dormer window down to the pipe "
     "collar. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "雨点、老房子木头响；「没有花园，也没有地板」"),
    ("S26", "agnes", "低位穿行 low crawl-in",
     "水槽下的管道：锈迹、接缝处渗水，一只扳手搁在桶上，一滴水滴进桶里荡开",
     "水滴荡开的同时切走廊光柱",
     "Under a stainless-free 1980s kitchen sink: a tangle of rusted iron waste pipe and rubber flex joints, a slow drip "
     "falling into a chipped plastic bucket which rings, a pipe wrench lying on the bucket's rim, cabinet doors open on either "
     "side framing the shot, the cupboard's dark interior filling the background; no people, nothing but plumbing in frame. "
     "Camera: one slow crawl-in along the pipe toward the dripping joint. The entire clip stays in this single framing: "
     "no cut, no scene change, no camera relocation.",
     "滴水、桶壁共鸣；「煮散、冲下去」"),
    ("S27", "agnes", "光柱固定 static shaft",
     "每天两遍的杀虫剂：窗台上一罐气雾剂，午后光柱里飘着细雾，纱帘微微动",
     "雾落定，切楼下门铃",
     "A narrow 1980s hallway window on an afternoon of pale sun: on the sill an unmarked aerosol spray can lying on its side, "
     "a fine mist still hanging in the shaft of light, dust on the painted sill, a lace curtain stirring as air moves through "
     "the gap, the glass showing only blurred brick of the neighbour's wall (no street, no skyline); no people, "
     "no legible label on the can. Camera: locked-off on the mist. The entire clip stays in this single framing: no cut, "
     "no scene change, no camera relocation.",
     "呲——一声很长的喷雾；「每天喷两遍」"),
    ("S28", "agnes", "门外固定 static outside door",
     "邻居投诉：一楼共用的前门，一只按在门铃上的手，门缝里递出一张折起来的纸（不可读），没人应门",
     "纸片被风吹落到台阶，切清晨货车",
     "The shared front door of a London Victorian conversion on a grey morning: a brass bell push and a row of blank letter "
     "slots, a neighbour's hand in a woollen sleeve pressing the bell and sliding a folded sheet of paper through the gap, "
     "the door slightly ajar with warm hall light behind it, nobody answering, wet stone steps and a cracked iron railing in the "
     "foreground; the brick wall and doorway fill the frame; no faces, no readable writing on the paper. "
     "Camera: static on the door with a slight drift closer. The entire clip stays in this single framing: no cut, "
     "no scene change, no camera relocation.",
     "门铃哑响、风；「邻居投诉有味道」"),
    ("S29", "agnes", "低机位横移 low track",
     "二月八号：一辆方头小货车停在路边，一个人从车厢里抽出长软管往人行道走（背影），排气管冒白烟",
     "软管拖过井盖的声音接井口",
     "A cold February evening outside a north London terraced street: a small boxy drain-clearing van parked at the kerb with "
     "its rear doors open, coiled black hose and a petrol engine on the load bed breathing white exhaust into the air, "
     "a workman in a thick jacket and flat cap walking away from camera carrying a length of hose toward the manhole at the "
     "kerb, the van and the brick houses filling the background from edge to edge; no faces, no legible company markings "
     "anywhere on the van. Camera: one low slow track along the kerb behind him. The entire clip stays in this single framing: "
     "no cut, no scene change, no camera relocation.",
     "发动机突突、软管抽过车厢板；「疏通公司来了人」"),
    ("S30", "agnes", "大远景固定 static wide",
     "当晚他自己下去清管道：路灯下顶楼那扇窗黑着，井口一个弯腰的人影，手电咬在嘴里，另一个影子从楼道门口看着",
     "井口的盖子被推回，画面黑，第五章从警局的灯开始",
     "A shared back courtyard of a north London conversion in the small hours, filmed at eye level"
      "from one end of the yard: a single row of brick tenement fronts with a door and a short flight"
      "of stone steps to each door, wet asphalt under one sodium lamp, one manhole lid propped upright"
      "in the middle of the yard, a lone workman crouched at the open pit with a torch beam raking down"
      "into it, his back to camera, and a second figure standing in one lit doorway further along the"
      "row, also facing away. The yard has one ground level only: no stacked or mirrored second row of"
      "houses above or below, no elevated terrace, no reflection repeating the facades, no second"
      "courtyard; no plaques, no numbers, no lettering on the brickwork, no faces. Camera: a slow"
      "straight dolly along the yard. The entire clip stays in this single framing: no cut, no scene"
      "change, no camera relocation.",
     "井盖摩擦一声、远处夜铃；「当晚他自己下去」"),
    # ---------------- N05 供词与庭审（8 镜）----------------
    ("S31", "agnes", "缓慢推近 slow push-in",
     "第二天清晨：同一个井口，蹲着的人用钩子从砖缝里刮下一小块东西，站起来望向镜头方向（无脸），另一人已在过马路去打电话",
     "他举起的背影切警局电话",
     "Grey dawn at the same manhole: a workman crouched at the rim scraping the brick joint with a hooked rod, one gloved hand "
     "lifting a small dark fragment toward the second man standing at the kerb; a supervisor in a overcoat watching with his "
     "back three-quarters to camera, the street quiet, milk bottles on doorsteps blurred behind; both figures' faces out of "
     "frame or turned away; the brickwork of the houses fills the background. Camera: one slow push-in toward the raised hand. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "钩子刮砖一声；音乐第一次给出「确定」的音型"),
    ("S32", "agnes", "桌面平移 desk track",
     "警局：一九八〇年代刑警办公室的木桌，一只手把一叠空白表格按上印章，旁边座机、搪瓷杯、烟灰缸",
     "印章落下那一声接审讯室的录音机",
     "Interior only: a 1983 CID incident room corner, a scarred wooden desk filling the lower half of"
      "the frame, neat stacks of completely blank paper forms, a heavy metal date stamp being pressed"
      "down by one hand in a shirt sleeve, a black rotary telephone with a coiled cord, a chipped"
      "enamel mug, a full glass ashtray and a grey steel filing cabinet behind. Bare painted brick and"
      "a wooden dado, with no plaques, no room numbers, no pinned notices and no wall signage of any"
      "kind; venetian blinds cut grey light into strips on the right wall only; every sheet of paper is"
      "blank and illegible. No faces. Camera: one slow push-in along the desk toward the stamp. The"
      "entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "印章「咚」、纸张翻动"),
    ("S33", "agnes", "缓慢环绕 slow arc",
     "整晚的审讯：小房间，金属桌，一台盘式录音机在转，两把椅子，一个背影双手抱着后颈，烟灰缸堆满",
     "录音机转盘的转动接法院石阶",
     "Interior only, four panelled walls filling the frame edge to edge: a bare 1983 police interview"
      "room under a single ceiling light, a bolted metal table with a reel-to-reel tape recorder"
      "turning slowly, a glass ashtray heaped with cigarette ends, a metal chair holding the back of a"
      "man in an open-collar shirt with both hands clasped behind his neck and his head down, and a"
      "second empty chair opposite. The room is windowless and sealed - no corridor, no street, no"
      "exterior wall, no second room. No readable text on any surface. No faces. Camera: locked-off"
      "wide from the corner, only the tape reels turning. The entire clip stays in this single framing:"
      "no cut, no scene change, no camera relocation.",
     "磁带转动的沙沙声；「说不准确切的人数」"),
    ("S34", "agnes", "仰视前飞 low forward glide",
     "开庭那天的人群：机位贴在人群背后，画幅被后脑勺与湿大衣肩线占满，法院的门只剩远处一团暖光——没有墙可刻字",
     "跨过最高一级台阶时硬切庭内",
     "A 1983 courthouse crowd seen from directly behind at the foot of shallow stone steps: the frame"
      "is filled edge to edge from the bottom to the top only by their wet dark coats, shoulders and"
      "flat caps, a handbag strap and one umbrella held slightly off-vertical; the crowd shifts forward"
      "half a step, shoulders rising and falling, and a soft warm glow from a doorway that stays"
      "outside the frame lights the tops of their caps; there is no building, no facade, no doorway"
      "shape, no street, no harbour, no sky, no signage, no plaque, no carved band, no lettering and no"
      "numerals anywhere in frame; no faces. Camera: locked-off close behind the crowd, the framing"
      "only tightens and never widens, so no wall can enter the shot. The entire clip stays in this"
      "single framing: no cut, no scene change, no camera relocation.",
     "石阶脚步、大衣摆动；字幕高亮「中央刑事法院」"),
    ("S35", "agnes", "缓慢推近 slow push-in",
     "庭内：木质护墙板、旁听席的空椅、被告席的木栏杆后面一个瘦高背影坐着，法官席只给袍角",
     "袍子摆动走出画面，切证人席剪影",
     "Interior of a 1983 Old Bailey courtroom seen from behind the public gallery: dark oak panelling, empty bench seats, "
     "the ornate rail of the dock with a tall thin man in a dark suit sitting with his back to camera, hands flat on the rail, "
     "a barrister's gown and horse-hair wig passing in the near foreground, high windows with grey light and no view out; "
     "no faces, no readable text on any surface. Camera: one slow push-in over the gallery rail toward the dock. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "木椅响、低语；「辩方说他有精神疾病」"),
    ("S36", "agnes", "焦点转移 rack focus",
     "活下来的人出庭：证人是三个依次站起的男性剪影（逆光、只有轮廓），前景是辩护席的后脑与肩",
     "第三个人站起时切「报过警的人」卡",
     "Backlit view across a 1983 courtroom toward the witness box: three men in turn rising from the gallery into a shaft of "
     "grey window light, shown only as dark silhouettes with no facial detail, one in a coat with a bandage at his throat "
     "implied by the collar, the blurred back of a defence lawyer's head and shoulder framing the near foreground; wood panelling "
     "and drapes fill the rest; no faces, no readable text. Camera: static with one slow rack focus between the silhouettes and "
     "the foreground shoulder. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "椅子刮地、吸气声；「有人报过警」"),
    ("S37", "graphic", "被忽视卡 static card",
     "第五张卡：1979 与 1980，两条报过案的记录——一条没人起诉，一条被当成情侣吵架",
     "卡片停在「情侣纠纷」那一行，直接压到判决卡",
     "这张卡是全片主题的证据，措辞要平、不要喊；只写公开报道里有的年份与结果",
     "纸面压过的声音；此处静音"),
    ("S38", "graphic", "判决卡 static card",
     "第六张卡：1983 年 11 月 4 日的裁定与量刑，以及 1994 年 12 月改成永远不出狱",
     "卡片最后一行压住，直接接监狱铁门",
     "把「定了什么罪」和「没定什么罪」分清：六项谋杀、两项谋杀未遂成立；其余是他承认但未被起诉的，不写成判决",
     "「咚」一声木槌；音乐收干净"),
    # ---------------- N06 结局与金句（7 镜）----------------
    ("S39", "agnes", "纵深跟拍 corridor follow",
     "「永远不用出去」：维多利亚式监狱长外廊，狱警推钥匙车走远，尽头天窗的光",
     "走到光里，切牢房",
     "Interior of a Victorian prison landing, late afternoon: a long balcony of painted iron railings facing rows of cell doors, "
     "grey light falling from a distant skylight at the far end, a uniformed officer walking away from camera pushing a trolley "
     "with a ring of keys, his shadow long on the concrete, dust in the light beam; the rows of closed doors fill both sides of "
     "the frame, no inmates, no faces. Camera: one slow follow down the landing. The entire clip stays in this single framing: "
     "no cut, no scene change, no camera relocation.",
     "钥匙串、铁门回声；音乐换成单音钢琴"),
    ("S40", "agnes", "缓慢横摇 slow pan",
     "二十多年牢里：单人牢房窄床、小桌上一台老式打字机，纸是空白的，高窗一小块天",
     "摇到窗，风把纸吹起一角，切医院走廊",
     "Interior only, one small cell: a 1990s maximum-security prison cell with a narrow made bed"
      "against a painted wall, a bolted wooden desk holding an old portable typewriter with a blank"
      "sheet feeding out, a chair pushed back, and one high barred window with a small square of grey"
      "sky. Four walls and a concrete floor fill the entire frame from edge to edge - no corridor, no"
      "exterior, no street, no harbour, no second room and no view of any other place. No writing"
      "legible anywhere, nobody in frame, no faces. Camera: one very slow push-in from the door end"
      "toward the desk. The entire clip stays in this single framing: no cut, no scene change, no"
      "camera relocation.",
     "纸响、窗外风；「二〇一八年五月」"),
    ("S41", "agnes", "缓慢下摇 tilt down",
     "约克的监狱医院：清晨病房走廊，百叶窗把光切成一条条，一张空推床停在墙边——不写死亡，只给「空」",
     "光条变宽，切数字卡",
     "An empty prison hospital corridor in early morning: pale green painted walls, venetian blinds throwing striped light "
     "across a polished floor, an unused trolley parked against the wall with a folded blanket on it, a closed door at the far "
     "end with light under it, a curtain rail and an infusion stand soft in the near foreground; no people, no faces, "
     "no readable signage. Camera: one slow tilt from the light under the door down to the empty trolley. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "走廊通风声、极远处推车一轮；不配音乐"),
    ("S42", "graphic", "数字卡 static card",
     "第七张卡：受害者规模的三种口径——定罪的、他自己认的、至今没名字的",
     "卡片比别的卡多停 0.4 秒",
     "这张卡是全片最容易被质疑的一张，所以把口径写清楚；不写「共杀15人」这种我们自己没核实的说法",
     "「咔」；音乐停"),
    ("S43", "agnes", "静物缓推 still-life push-in",
     "第一个死者：一九七八年冬夜公交站台，一只落下的手套和一张被风掀起的票根（不可读），路灯照亮湿地",
     "风把票根吹出画面，切档案室",
     "A 1978 bus stop at night in sleet: a shelter of curved glass and green paint lit by a single amber lamp, wet road "
     "reflecting it, one lost youth's glove lying on the bench and a folded ticket stub caught under the bench leg flapping in "
     "the wind, the shelter's glass showing only blurred falling sleet beyond it; no people, no legible text on either object, "
     "the ticket deliberately worn and blank to camera. Camera: one very slow push-in on the glove. "
     "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "风、雪打玻璃；「第一个死的是个十四岁男孩」"),
    ("S44", "agnes", "横移档案柜 lateral track",
     "二十八年才对上名字：失踪人口档案室，一排排纸箱卷宗，一只手从架上抽出一册，翻开的是空白页；桌上一张失焦的老照片",
     "照片被灯影盖住，切现在的街道",
     "A windowless police records room: tall steel shelving stacked with plain cardboard archive boxes"
      "lines both sides of a narrow aisle, a single desk lamp is clamped to a metal table, and the"
      "aisle ends in a solid concrete wall; a hand in a dark sleeve draws one slim folder from the"
      "shelf and opens it to blank pages, with a small out-of-focus black-and-white photograph lying"
      "face-up on the table. The room is closed and grey - no windows, no street outside, no houses, no"
      "lamps, no second room and no view of anywhere else; the shelving and the concrete wall fill the"
      "frame from edge to edge. No legible labels, numbers or lettering on any box, page or photograph;"
      "no faces. Camera: locked-off at the end of the aisle with a slight push toward the open folder."
      "The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "纸板抽出的一声、纸页翻动；字幕高亮「二〇〇六年」"),
    ("S45", "agnes", "缓慢后拉 slow pull-back",
     "现在的克兰利花园：夏末傍晚，普通住宅，孩子在楼下骑车，顶楼那扇窗没亮灯——日常得让人不舒服",
     "后拉到整条街，收在窗上，接片尾卡",
     "A north London street on a late summer evening, present day with nothing modern or branded,"
      "framed from first-floor height so that the pavement, the front doors and any parked car lie"
      "outside the bottom edge of frame: two Victorian brick conversions with bay windows and curtained"
      "sash windows filling the frame left and right, one plane tree between them catching the low sun,"
      "a washing line with sheets in a back garden below, and one dark unlit top-floor window behind a"
      "curtain near the centre; the brickwork carries no house numbers, no plaques, no lettering and no"
      "signage of any kind; no people at street level, no faces. Camera: one very slow pull-back so the"
      "dark top-floor window drifts toward the centre of frame. The entire clip stays in this single"
      "framing: no cut, no scene change, no camera relocation.",
     "孩子笑声、远处割草机；最后 0.6 秒全部声音收干净"),
]

# ---------------------------------------------------------------------------
# 画面上的文字（render.py 从 story.json 的 presentation 块读，不在 render.py 里写死）
# ---------------------------------------------------------------------------
CARD_HEADER = "案件档案  /  伦敦 · 1978—1983"
CARD_FOOTER = "资料摘要与示意图 · 并非原始档案影像"
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S05": ("克兰利花园 23 号连环案",
            "英国伦敦北部 · Muswell Hill / Cricklewood · 1978—1983",
            "法庭审理查明 6 起谋杀 · 他本人承认 15 至 16 人 · 开庭时 8 人无名"),
    "S09": ("丹尼斯·尼尔森  Dennis A. Nilsen",
            "1945.11.23 生于苏格兰弗拉伯勒 · 2018.5.12 死于约克 · 终年 72 岁",
            "英军食堂出身 · 退伍后在伦敦一家就业中心做保安 · 无犯罪记录直到被捕"),
    "S20": ("五年 · 两个地址",
            "1978.12.30 — 1983.2.9　Cricklewood 梅尔罗斯大街 195 号（有花园）",
            "1981.10 — 1983.2　克兰利花园 23 号顶楼（无花园 · 无地板）"),
    "S24": ("一九八一年十月，他搬了家",
            "顶楼小屋：没有后院，没有地板下可以放东西",
            "他把「处理」从火堆改成了下水道——这条路最后通到了他自己门口"),
    "S37": ("报过警的人",
            "1979.10　一名被勒醒后逃脱的学生报案　未起诉",
            "1980.11　一名被打断脖子的酒保报案　记录为「情侣纠纷」，没有下文"),
    "S38": ("一九八三年十一月四日 · 中央刑事法院",
            "6 项谋杀 + 2 项谋杀未遂 成立 · 法官建议至少服满 25 年",
            "1994.12　内政大臣改判为终身不得假释（whole life）· 他没有上诉"),
    "S42": ("多少人，多少名字",
            "定罪：6 人　承认：15 至 16 人　现代研究至少确认 12 人",
            "1983 年开庭时 8 人至今无名；2006 年 1 月，第一个死者才对上名字"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["下水道堵了，警察上了顶楼“, ”克兰利花园 23 号 · 一九八三年二月"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "如果那些报案被认真处理，能少死几个人？",
    "丹尼斯·尼尔森 · 1978—1983 · 伦敦",
    "每一场持续多年的连环犯罪背后，往往都有系统性的缺位与纵容。",
    "资料：BBC / Wikipedia / Crime & Investigation / Telegraph / Mirror 等公开报道 · 原创解说 · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词）
CAPTION_KEYWORDS = [
    "丹尼斯·尼尔森“, ”十五个，或者十六个“, ”斯蒂芬·霍姆斯",
    "一九八三年二月八号“, ”衣柜里的两个黑色塑料袋“, ”领带",
    "就业中心当保安“, ”情侣纠纷",
    "一九九四年十二月“, ”永远不用出去“, ”二〇〇六年",
    "一具还是两具“, ”没人会去找的人“, ”十四岁“, ”对上号",
]
# 逐镜标签覆盖：默认 agnes 镜头标「AI动画情景重现 · 非新闻影像」，法庭/监狱/取证/搜查镜头写得更具体
LABEL_OVERRIDES = {
    "S06": "AI动画情景重现 · 非警方影像",
    "S07": "AI动画情景重现 · 非证物照片",
    "S22": "AI动画情景重现 · 非现场勘查照片",
    "S32": "AI动画示意 · 非真实案卷",
    "S33": "AI动画示意 · 非真实审讯记录",
    "S34": "AI动画示意 · 非庭审影像",
    "S35": "AI动画示意 · 非庭审影像",
    "S36": "AI动画示意 · 非庭审影像",
    "S39": "AI动画示意 · 非监狱实景",
    "S40": "AI动画示意 · 非监狱实景",
    "S41": "AI动画示意 · 非医疗影像",
    "S44": "AI动画示意 · 非真实案卷照片",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S04", "phone"),
    ("S05", "press"),
    ("S09", "press"),
    ("S14", "keys"),
    ("S20", "paper"),
    ("S24", "press"),
    ("S29", "machine"),
    ("S30", "machine"),
    ("S32", "press"),
    ("S37", "paper"),
    ("S38", "press"),
    ("S42", "paper"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "水管工捅开下水道，掏出一堆人肉：英国「好邻居」连环杀手案",
    "白天给找工作的人开门，晚上送人进下水道：丹尼斯·尼尔森五年的杀戮",
    "他说「孤独比死亡更可怕」，然后杀了15个人陪他",
]
HOOK = "一个戴金丝眼镜、在就业中心当保安的「体面人」，五年里至少带走十二个人，把遗骸留在床上几个星期，\n最后抓他的不是刑警，是一根堵住的下水管。"
GOLDEN_LINES = [
    "每一场持续多年的连环犯罪背后，往往都有系统性的缺位与纵容。对生命的尊重，从来不该分身份、不分群体。",
    "他挑人的标准不是谁弱，是谁丢了不会有人报案。",
    "你觉得，如果当初有人认真对待那两份报警，悲剧能不能少几起？评论区聊聊。",
]
DESCRIPTION = (
    "1983年2月，伦敦一栋普通公寓的下水道堵了。疏通工从管壁上掏出来的东西，让他在井口直接打了报警电话。\n"
    "顶楼那个安静、整洁、上班从不迟到的邻居，只说了一句「都在衣柜里」。\n"
    "本期讲丹尼斯·尼尔森案：他怎么挑人、警察为什么找了他五年、以及两个报过警的人是怎么被劝回去的。\n"
    "全片为 AI 动画情景重现，不冒充新闻影像；事实以公开报道为准，未定论的不写成结论。\n"
    "你觉得，那些报案如果被人认真对待，能少几个人？"
)
QUESTION = "如果当初有人认真对待那两份报警，悲剧能不能少几起？"
HASHTAGS = ["#真实案件", "#悬疑", "#科普", "#英国", "#连环杀手档案", "#正义不会缺席"]

GRID = 4           # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 7  # 每个 Agnes 镜头实际请求的时长（169 帧 @ 24 fps）
SEED_BASE = 20260923  # 需求表提交那天，让 seed 可追溯

# 逐镜种子微调。2026-09-23 实测教训：S15 连着三版提示词都改了（禁门牌、禁海报、把地面框出去），
# 生成回来**构图一模一样**、连它自己加的那块「147388 4X)61S」门牌都没变——因为 seed 是按镜头序号
# 定死的，同一起点等于让模型把同一张画重画一遍。要"换个构图"就得动 seed，而不是再堆否定句。
# 用法：某镜复审时如果发现"缺陷没跟着提示词变"，给它加个 bump（几十即可），别改 SEED_BASE 本身，
# 那会把全部 38 镜推倒重做。
SEED_BUMP = {"S15": 41, "S34": 217, "S45": 41}


def presentation():
    return {
        "card_header": CARD_HEADER, "card_footer": CARD_FOOTER,
        "cards": {sid: list(lines) for sid, lines in CARDS.items()},
        "title_card": TITLE_CARD, "end_card": END_CARD,
        "caption_keywords": CAPTION_KEYWORDS, "label_overrides": LABEL_OVERRIDES,
        "sfx_events": [list(e) for e in SFX_EVENTS],
    }


def build():
    story = json.loads(PLAN.read_text())
    assert len(SHOTS) * GRID == 180, f"{len(SHOTS)} 镜 × {GRID} 秒 ≠ 180 秒"
    assert len(story["chapters"]) == len(CHAPTERS) == 6
    assert len({sid for sid, *_ in SHOTS}) == len(SHOTS), "镜头号重复"
    cards_needed = {sid for sid, kind, *_ in SHOTS if kind == "graphic"}
    missing = sorted(cards_needed - set(CARDS))
    assert not missing, f"这些信息卡镜头在 CARDS 里没有文案：{missing}"
    story["title"] = TITLE
    story["style_prefix"] = STYLE_PREFIX
    story["negative_prompt"] = NEGATIVE_PROMPT
    story["principles"] = PRINCIPLES
    story["sources"] = SOURCES
    for chapter, (cid, title, text) in zip(story["chapters"], CHAPTERS):
        assert chapter["id"] == cid
        chapter["title"] = title
        chapter["text"] = text
    shots = []
    for i, (sid, kind, camera, purpose, transition, body, sfx) in enumerate(SHOTS):
        assert sid == f"S{i + 1:02d}", sid
        assert kind in ("agnes", "graphic"), f"{sid}: kind 只能是 agnes / graphic"
        start = i * GRID
        shots.append({
            "id": sid, "kind": kind, "start": start, "duration": GRID,
            "narration_id": f"N{min(6, start // 30 + 1):02d}",
            "prompt": body if kind == "agnes" else "",
            "purpose": purpose, "transition_out": transition,
            "graphic": body if kind == "graphic" else "",
            "seed": SEED_BASE + i + 1 + SEED_BUMP.get(sid, 0),
            "seconds": AGNES_SECONDS, "aspect": "16:9", "resolution": "1080p", "frame_rate": 24,
            "camera": camera, "sfx_note": sfx,
        })
    story["shots"] = shots
    story["presentation"] = presentation()
    story.setdefault("_scaffold", {})["note"] = (
        "内容由 build_story.py 一次性写入；45 镜 × 4 秒规划网格（每镜只用一次）；"
        "解说词与 screenplay.md、audio/manifest.json 三处逐字一致由 generate.py --validate 守着。")
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")

    manifest = json.loads(MANIFEST.read_text())
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        assert clip["id"] == chapter["id"]
        clip["text"] = chapter["text"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    kinds = [s["kind"] for s in story["shots"]]
    print(f"story.json 已写入：{len(shots)} 镜 = {kinds.count('agnes')} agnes + {kinds.count('graphic')} graphic，"
          f"解说 {sum(len(c['text']) for c in story['chapters'])} 字（含标点）")
    todo = json.dumps(story, ensure_ascii=False).count("TODO") + json.dumps(presentation(), ensure_ascii=False).count("TODO")
    if todo:
        print(f"注意：还有 {todo} 处 TODO 没填，generate.py --validate 不会放行", file=sys.stderr)


if __name__ == "__main__":
    if "--script" in sys.argv:
        from script_table import render_document  # noqa: E402  (同目录)
        out = HERE / "抖音脚本.md"
        out.write_text(render_document())
        print(f"抖音脚本.md 已写入（{len(out.read_text())} 字符）")
    elif "--publish" in sys.argv:
        from script_table import publish_document  # noqa: E402  (同目录)
        out = HERE / "抖音发布文案.md"
        out.write_text(publish_document())
        print(f"抖音发布文案.md 已写入（{len(out.read_text())} 字符）")
    else:
        build()

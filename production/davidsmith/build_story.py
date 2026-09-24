#!/usr/bin/env python3
"""《大卫·史密斯：无罪之后》的唯一内容源。

把事实核查过的解说、45 镜分镜、信息卡、字幕高亮与发布文案一次性写入
story.json / audio/manifest.json。Agnes 只生成无文字、无脸、非血腥的 2D 动画
情景重现；中文标题、日期、数字、字幕全部由后期控制，避免模型生成伪文字。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
TITLE = "大卫·史密斯：无罪之后"

STYLE_PREFIX = (
    "Stylized 2D animated documentary illustration with hand-painted graphic-novel textures, soft cel shading, "
    "subtle controlled analog barrel-lens distortion, slight chromatic fringe on hard edges, offset shadow layers "
    "only as a graphic transition motif, anatomically stable subjects; west London and Surrey in 1991-2023, "
    "old Bailey-style courtroom, lorry yards, ordinary suburban streets, a small Southall flat, prison corridors, "
    "forensic labs and appeal court interiors; horizontal 16:9 cinematic composition, muted slate blue, nicotine "
    "paper beige, steel grey and sodium-orange practical light, restrained procedural true-crime mood, tense but "
    "not horror; every person is shown only from behind, in silhouette, or as hands and props, never a clear "
    "frontal face; absolutely no readable text, letters, numbers, logos, license plates or brand marks anywhere "
    "inside the generated frame; one single continuous smooth camera move per shot exactly as directed, hold the "
    "single location for the full clip. "
)

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, invented headlines, logos, brand marks, watermark, "
    "subtitles, on-screen caption, photorealistic face, recognizable real person likeness, frontal face close-up, "
    "visible eyes in detail, blood, gore, wound, corpse, body bag, body parts, autopsy, explicit violence, assault "
    "in progress, strangling, stabbing action, gun, firearm, nudity, erotic content, horror monster, ghost, jump "
    "scare, 3D render look, plastic CGI, anatomical distortion, deformed hands, extra fingers, extra limbs, "
    "duplicated people, changing face, morphing objects, teleportation, jitter, flicker, whip pan, fast zoom, "
    "jump cut, split screen, collage, scene change, second location, camera relocation"
)

PRINCIPLES = [
    "全部 Agnes 镜头为风格化 2D 动画情景重现，常驻「AI动画情景重现 · 非新闻影像」标签，不冒充庭审、监控或证物照片",
    "不展示遗体、血腥、侵害过程或性行为；作案手法只讲到假名、密闭空间、袭击与毁尸这一层",
    "史密斯只以背影、剪影、手部出现，不用 AI 生成的脸冒充本人；受害者不以人像出现",
    "“暗网涉猎者”等未被公开证据支持的说法不写入成片；只保留可由公开报道和判决报道支持的暴力史",
    "关于双重危险规则，准确表述为英国《刑事司法法二零零三》建立“新的且有说服力的证据”例外，二零零五年前后开始适用；不是所有案件都能重审",
    "二零二三年本次重审定罪的是萨拉·克拉姆案；史密斯当时已经因阿曼达·沃克案服终身刑，最低刑期数字按公开报道表述",
    "中文姓名、日期、数字和字幕全部后期添加，不交给视频模型拼写；生成画面出现伪文字、露脸、换场、严重畸变就重做",
    "每个镜头只使用一次；生成片段先看接触表，再做黑帧、冻结帧、畸变、构图与字幕/音频同步复检",
]

SOURCES = [
    {"id": 1, "url": "https://www.bbc.com/news/uk-england-london-65682975", "usage": "BBC：1991 年萨拉·克拉姆案、1993 年无罪、1999 年阿曼达·沃克案、狱中吹嘘与 2023 年定罪"},
    {"id": 2, "url": "https://www.bbc.co.uk/news/uk-england-london-65721383", "usage": "BBC：三十年后按双重危险法律重审，终身监禁最低 27 年，二零二二年上诉法院准许重审"},
    {"id": 3, "url": "https://news.sky.com/story/david-smith-honey-monster-killer-handed-life-sentence-for-double-jeopardy-murder-12890023", "usage": "Sky News：绰号、卡车司机、两案相似性、最低刑期及双重危险规则变化"},
    {"id": 4, "url": "https://www.independent.co.uk/news/uk/crime/david-smith-old-bailey-southall-london-police-b2345032.html", "usage": "The Independent：假名 Duncan、指纹后来确认属于前房主、狱中“got away with it”吹嘘"},
    {"id": 5, "url": "https://www.irishnews.com/news/uknews/2023/05/26/news/life_sentence_for_sadistic_sexual_killer_for_double_jeopardy_murder-3306198/", "usage": "PA/Irish News：案发地点、前科背景、法官量刑与“二十七年扣除羁押”细节"},
    {"id": 6, "url": "https://www.legislation.gov.uk/ukpga/2003/44/contents", "usage": "英国官方立法文本：《刑事司法法二零零三》及双重危险例外的法律依据"},
    {"id": 7, "url": "https://en.wikipedia.org/wiki/David_Smith_(murderer)", "usage": "时间线交叉核对；仅作索引，成片关键事实以 BBC、Sky、PA 与判决报道为准"},
]

# 六段合计约 760—800 字；保留标点与中文数字写法，便于 TTS、字幕和逐字听检共用一份文本。
CHAPTERS = [
    ("N01", "黄金开头：无罪之后又杀人",
     "他第一次被控杀人，陪审团却给了他无罪。走出法庭，他还向陪审团道谢；六年后，他再杀一人；三十年后，英国修改“一罪不二审”规则，他又站回被告席。这就是卡车司机大卫·史密斯案。今天讲清：他怎样从无罪里走出，又怎样被自己的一句话绊倒。"),
    ("N02", "双面人生：普通外表，升级的暴力史",
     "大卫·史密斯是英国卡车司机，身材高大，绰号“蜂蜜怪兽”或“Lurch”。表面上，他只是伦敦西部一个普通男人；但法庭资料显示，他年轻时就有针对女性的暴力和性犯罪记录：一九七六年持刀强奸，上世纪八十年代非法拘禁女性。九十年代，他用假名接近性工作者。最危险的，往往不是长得像怪物，而是看起来太普通。"),
    ("N03", "两起命案：假名与密闭空间",
     "一九九一年八月，三十三岁的萨拉·克拉姆在伦敦南奥尔公寓遇害。史密斯承认用假名“邓肯”付钱去见她，却说离开时她还活着。检方认为，他把约见带进密闭空间，再发动袭击并毁尸。六年后，二十一岁的阿曼达·沃克失踪，遗体在萨里郡浅墓中被发现。两案出现相似特征，但第一案的证据链断了。"),
    ("N04", "第一次审判：无罪释放",
     "一九九三年，史密斯在老贝利受审。门把手、抽屉和床下的几枚不明指纹，被辩方解释成“还有另一个人”，警方也被指未披露证据。陪审团判他无罪；他走出法庭，还向陪审团道谢。按当时的“一罪不二审”，同一罪名不能再审，这桩命案像被法律锁死。可史密斯没有停手。"),
    ("N05", "神转折：一句吹嘘变成新证据",
     "一九九九年，阿曼达案把他送进监狱。她衣物上的血迹 DNA 指向史密斯，陪审团不信他的辩解。候审期间，他还向同仓犯人吹嘘：“上一桩谋杀我走掉了，他们没有证据。”二零零三年英国修改法律，允许新且有说服力的证据触发重审；二零二二年，上诉法院准许重审。狱中吹嘘、两案相似性，以及指纹属于前房主，拼成新证据链。"),
    ("N06", "三十年后：法律终于追上他",
     "二零二三年五月，萨拉遇害三十二年、史密斯无罪三十年后，陪审团用不到三小时判他有罪。法官判终身监禁，最低二十七年，扣除九十年代羁押时间；他本来已因阿曼达案服终身刑。判决还不回生命，却把“无罪”改写成“有罪”。你觉得，击穿他的到底是法律改变，还是那句狱中吹嘘？评论区聊聊。"),
]

# 45 镜 = 38 个 Agnes 动画 + 7 张后期信息卡。每镜只出现一次。
SHOTS = [
    # ---------------- N01 黄金开头（8 镜）----------------
    ("S01", "agnes", "低机位缓慢后移 slow pull-back",
     "零到五秒黄金开头：一九九三年老贝利外，巨大木门打开，高大男人背影走出，门内陪审团只留下暗色剪影",
     "背影经过镜头时硬切到空法庭",
     "Old Bailey-inspired London courthouse exterior at grey winter dusk, framed low on massive wooden doors as they open; a very tall heavyset lorry driver in a dark coat walks out seen only from behind, a row of jury silhouettes remains in the warm doorway, no faces, no readable signs. Camera: one slow pull-back as the man walks toward the empty pavement. Hold this single exterior for the full clip, no cut, no scene change.",
     "门轴低响 + 法槌远响；开头 0.3 秒立刻入画"),
    ("S02", "agnes", "缓慢横移 slow lateral slide",
     "“陪审团给了他无罪”：空法庭，木质陪审席与一张空被告席，纸张被风轻轻掀动",
     "纸张翻页声接案件名片",
     "Empty wood-paneled London courtroom after a verdict, viewed from the gallery: vacant jury box, an empty defendant table, a single loose sheet of paper moving in a draught, hard side light and long shadows, no people, no text. Camera: one slow lateral slide from the jury box to the empty defendant table. Hold one room for the full clip, no cut.",
     "纸张翻动；“无罪”字幕后期大字压屏"),
    ("S03", "graphic", "后期信息卡 static graphic",
     "案件名片：大卫·史密斯、两起命案、三十年后重审",
     "卡片轻微纸张漂移，下一镜接卡车轮胎",
     "案件名片\n大卫·史密斯：无罪之后\n一九九一年命案 · 一九九九年再犯 · 二零二三年重审定罪",
     "低频脉冲 + 纸张擦过；文字只由后期渲染"),
    ("S04", "agnes", "车轮旁低角度跟拍 low tracking",
     "双面人生：夜雨中的英国卡车停车场，巨大的卡车驶过，高大司机只见背影",
     "车轮水花匹配切普通住宅",
     "Rainy 1990s British lorry yard at night, low camera beside a large articulated truck rolling slowly through sodium-orange puddle reflections; the driver is only a tall dark silhouette behind the cab window, no face, no logos or plates, warehouse walls fill the background. Camera: one smooth low tracking move alongside the rear wheels. Hold this single yard for the full clip, no cut.",
     "柴油引擎 + 雨声；画面做轻微镜头桶形畸变"),
    ("S05", "agnes", "固定大全景 locked wide",
     "“看起来太普通”：伦敦西部普通住宅夜晚，楼上暖灯、车道一辆卡车，窗上掠过异常长的影子",
     "影子掠过时音效抽空",
     "Ordinary west London suburban semi-detached house at night, warm upstairs windows, a plain lorry parked on the driveway, rain on the pavement; a very tall human shadow passes briefly across a frosted ground-floor window but no person is visible. Camera: locked-off wide view from across the quiet street for the whole clip. No readable house numbers, no faces, no scene change.",
     "远处公交驶过；影子出现时 0.2 秒静音"),
    ("S06", "agnes", "缓慢推近 slow push-in",
     "“被自己的一句话绊倒”：监狱桌面，两个囚犯背影隔桌坐着，其中一人靠近耳语，灯光把影子拉长",
     "耳语不可辨字，切时间线卡",
     "Dim 1990s prison cell interview room, two men shown only as dark silhouettes from behind seated across a small metal table, one leans toward the other as if boasting, a single overhead lamp casts a long distorted shadow on the wall, no faces, no readable writing. Camera: one slow push-in toward the gap between them. Hold this single room, no cut or change of location.",
     "低沉耳语质感但不含可识别语句；磁带 hiss"),
    ("S07", "graphic", "时间线卡 static graphic",
     "时间线：一九九一年萨拉、一九九三年无罪、一九九九年阿曼达、二零二三年重审",
     "四个年份依次亮起，二零二三年停住",
     "时间线\n一九九一年  萨拉·克拉姆\n一九九三年  无罪释放　→　一九九九年  阿曼达·沃克　→　二零二三年  重审定罪",
     "四次金属卡点；最后一次留半秒低频"),
    ("S08", "agnes", "门缝缓慢推近 slow dolly",
     "悬念收束：法庭档案室一扇铁柜门缓缓关上，门缝里露出一叠旧案卷",
     "铁柜合拢接人物背景章",
     "Narrow evidence archive room in London, one tall metal filing cabinet already open with a thick anonymous case file inside, no readable labels; the cabinet door slowly swings shut until only a thin line of warm light remains, dust motes in the beam, no people. Camera: one slow push toward the narrowing gap. One room, one action, no cut.",
     "铁柜门合拢；章间留 1.08 秒呼吸"),

    # ---------------- N02 双面人生（7 镜）----------------
    ("S09", "agnes", "背后跟拍 follow from behind",
     "大卫·史密斯的外形：高大的卡车司机从停车场走向驾驶室，身高差只用环境比例表现",
     "车门关上接人物信息卡",
     "1990s British lorry depot at overcast morning, an unusually tall broad-shouldered lorry driver in work jacket seen only from behind walking toward a large cab, stacked pallets and the cab door make his scale clear, no face, no logos or plates. Camera: one steady follow from behind at walking pace. Single depot location, no cut or scene change.",
     "车门沉重关闭 + 柴油启动"),
    ("S10", "graphic", "人物档案卡 static graphic",
     "人物档案：卡车司机、伦敦西部、绰号与前科警示",
     "“普通外表”与“暴力史”两行对照后轻微错位",
     "人物档案\n大卫·史密斯 · 英国卡车司机 · 绰号“蜂蜜怪兽”/“Lurch”\n公开庭审资料：长期针对女性的暴力与性犯罪记录",
     "纸张压平声；关键词“卡车司机”“暴力史”描黄"),
    ("S11", "agnes", "缓慢横移 lateral slide",
     "白天普通生活：伦敦西部街道，卡车从低矮住宅前驶过，一个高大背影拎午餐袋回家",
     "车影从左到右匹配下一镜公路",
     "Quiet west London residential street in the early 1990s, low brick houses and clipped hedges fill the frame, a lorry passes slowly beyond the hedge while a very tall man seen from behind carries a plain lunch bag toward one doorway, no faces, no house numbers. Camera: one slow lateral slide parallel to the hedge. Hold one street, no cut.",
     "街道底噪 + 车轮压水"),
    ("S12", "agnes", "车内固定中景 locked medium",
     "长途驾驶：卡车驾驶室内，方向盘、后视镜、手套和雨刷，驾驶员只露肩背",
     "雨刷节奏接暴力史档案",
     "Interior of a 1990s British lorry cab in rain, framed from behind the driver's seat: gloved hands on a plain steering wheel, shoulder and back of a very tall driver, windshield wipers and blurred motorway lights ahead, no face, no brands, no readable dashboard text. Camera: locked-off medium shot; only hands and wipers move. One cab throughout, no cut.",
     "雨刷 + 发动机低频；轻微边缘色差"),
    ("S13", "agnes", "纸档案上方俯拍 slow overhead drift",
     "满身前科但不提前定罪：旧纸档案、指纹卡、法院印章和一支铅笔，文字全部不可读",
     "铅笔停住接普通外表",
     "Overhead view of a dark wooden legal archive desk: anonymous blank case folders, generic fingerprint cards with no readable markings, a closed court stamp and a pencil, only a pair of hands in brown sleeves enters to align the papers; no faces, no actual evidence. Camera: one slow overhead drift along the desk. Hold the single desk, no cut.",
     "纸张摩擦 + 铅笔停笔"),
    ("S14", "agnes", "剪影缓慢推近 silhouette push-in",
     "九十年代夜晚：高大男人从街角电话亭附近走入暗处，只表现“用假名接近”的前奏，不出现受害者",
     "电话亭灯光切空公寓门",
     "1990s west London night street, a tall heavyset man seen only as a backlit silhouette stands beside a public telephone booth holding a small handset, wet pavement and a single amber streetlamp, no other person, no readable signage, no face. Camera: one slow push-in toward the silhouette's hand and receiver. Single street, no cut, no violence.",
     "电话拨号音三下；不出现真实通话内容"),
    ("S15", "agnes", "镜面反射缓慢平移 slow slide",
     "双面人生的视觉隐喻：卡车后视镜里只是普通背影，镜外影子却被拉长变形",
     "反射畸变停住，进入两起命案",
     "Close side view of a lorry's rectangular side mirror at dusk, the mirror shows only the back of a tall driver in an ordinary work coat while the reflected streetlight stretches the silhouette into a long abstract shadow; stable anatomy, no face, no logos. Camera: one slow slide along the metal mirror. Hold this single optical reflection, no cut or location change.",
     "玻璃嗡鸣 + 一记反向磁带倒放；受控光学畸变，不做人体变形"),

    # ---------------- N03 两起命案（8 镜）----------------
    ("S16", "agnes", "街对面缓慢推近 slow push-in",
     "一九九一年八月：伦敦南奥尔一套普通公寓的夜景，楼下警灯反光，镜头不展示现场内部",
     "警灯反射匹配公寓门把手",
     "West London Southall apartment block on a rainy late-summer night in 1991, seen from across the road; one upstairs window is dark, a distant police light washes blue and red across wet brick, no people, no body, no readable address. Camera: one very slow push-in toward the dark window. Hold the single exterior, no cut or interior reveal.",
     "雨声 + 远处警笛；画面标签“AI动画情景重现 · 非现场影像”"),
    ("S17", "agnes", "门把手微距推近 macro push-in",
     "假名“邓肯”与密闭空间：一只戴手套的手把普通公寓门轻轻合上，门外光线被切断",
     "门锁咔哒声切信息卡",
     "Macro interior shot of a plain Southall apartment door in 1991, a man's hand in a dark sleeve gently closes the door from the inside, the corridor light narrows to a line and disappears; no face, no other person, no readable number, no violence. Camera: one slow macro push-in toward the latch. One doorway, one action, no cut.",
     "门锁咔哒；低频瞬间压低"),
    ("S18", "graphic", "案件信息卡 static graphic",
     "后期准确呈现假名、日期与事实边界，不让 Agnes 生成文字",
     "“邓肯”落下时纸张压住下一镜",
     "一九九一年八月二十九日\n萨拉·克拉姆 · 伦敦南奥尔公寓\n史密斯承认用假名“邓肯”付钱去见她；其余经过由法庭证据判断",
     "打字机逐行出现；关键词“假名”“密闭空间”描黄"),
    ("S19", "agnes", "固定室内大全景 locked interior wide",
     "密闭空间的非血腥示意：小公寓客厅，门、关上的窗帘、桌上一盏灯，只有墙上钟在走",
     "钟声从近变远，切证物桌",
     "Small anonymous Southall flat interior at night, shown as a still empty room: closed curtains, a locked-looking front door, one table lamp, a wall clock and two untouched cups, no people, no body, no blood, no readable writing. Camera: locked-off wide shot; only the clock hand and lamp flicker slightly. One room for the entire clip, no cut.",
     "墙钟滴答；不重现侵害过程"),
    ("S20", "agnes", "证物桌缓慢横移 slow lateral move",
     "“随后用刀袭击、遗体严重损毁”只用封存证物、拉上的黑布和空房间表达，不展示过程",
     "证物袋拉链声切荒地",
     "Forensic evidence table in a cool London lab, framed on a sealed opaque evidence bag, a folded dark cloth and a closed generic case box; gloved hands place the items down without opening anything, no weapon action, no body, no blood, no readable tags. Camera: one slow lateral move across the sealed objects. Hold one lab bench, no cut.",
     "证物袋拉链 + 低沉脉冲；画面标签“AI动画示意 · 非证物照片”"),
    ("S21", "agnes", "荒地上方缓慢升镜 crane up",
     "阿曼达案：萨里郡 Wisley 附近的树篱与浅土痕迹，警戒带远处晃动，不出现遗体",
     "风吹草接空公寓手机",
     "Leafy Surrey countryside near Wisley in 1999, an empty shallow disturbed patch of earth beside hedges and a narrow path, a distant police cordon seen only as blurred strips, no people close by, no body, no blood, overcast light. Camera: one slow crane up from the ground texture to the empty path. Single location, no cut.",
     "风吹树叶 + 远处警笛；严禁尸体/血腥"),
    ("S22", "agnes", "桌面缓慢拉远 slow pull-back",
     "阿曼达·沃克失踪：一间空房的桌面，一次性手机、钥匙和没喝完的水，手机屏幕不可读",
     "手机最后一次闪烁切两案对照卡",
     "Anonymous small room in west London in 1999, a disposable mobile phone and a set of keys on a bare table beside a glass of water, no person, no readable screen, no photographs, no violence. Camera: one slow pull-back from the phone to the empty chair. Hold the single room for the full clip, no cut.",
     "一次性手机短促震动后断掉"),
    ("S23", "graphic", "两案对照卡 static graphic",
     "用后期卡说明两案相似，不把推测当事实",
     "两列线条轻微错位后重合",
     "两起命案的相似点\n一九九一年：萨拉·克拉姆 · 公寓内遇害\n一九九九年：阿曼达·沃克 · 失踪后被发现；均出现性暴力与毁尸特征",
     "两次低音落点；字幕注明“根据庭审报道”"),

    # ---------------- N04 第一次审判（7 镜）----------------
    ("S24", "agnes", "法庭后排缓慢横移 slow lateral slide",
     "一九九三年第一次审判：老贝利法庭后排，史密斯只见背影，律师在桌上翻证据",
     "律师翻页匹配指纹特写",
     "1993 London criminal courtroom seen from the back row, a very tall defendant shown only from behind at the defense table, two lawyers turn blank papers, judge's bench in the distance, no readable text, no faces, no spectators turning around. Camera: one slow lateral slide behind the last row. Hold this one courtroom, no cut.",
     "法庭木椅轻响 + 纸张翻页；标签“AI动画示意 · 非庭审影像”"),
    ("S25", "agnes", "门把手微距焦点转移 macro focus pull",
     "不明指纹：普通门把手、抽屉拉手与床下地面上的泛白粉末印记，用图形化示意，不冒充原始证物",
     "焦点从指纹转到证据袋",
     "Controlled forensic illustration on a plain apartment door handle and a wooden drawer pull, generic fingerprint powder marks shown as abstract swirls with no biometric identity, a gloved hand holds a magnifier, no readable evidence label, no blood. Camera: one slow macro focus pull from the handle to the drawer. One evidence demonstration, no cut.",
     "放大镜金属声 + 细微电流噪声；受控镜头畸变"),
    ("S26", "agnes", "纸张上方缓慢推近 overhead push-in",
     "辩方抓住证据链瑕疵：辩护律师手指停在几枚指纹示意上，法官席在背景虚化",
     "手指停顿接信息流失",
     "Overhead view of a 1993 defense table: a lawyer's hand points to three abstract fingerprint diagrams on blank paper while a courtroom bench blurs in the background, no readable text, no faces, no real evidence photography. Camera: one slow push-in toward the stopped finger. Hold the single table, no cut or scene change.",
     "铅笔划线停住；一记纸张撕裂音作为转折"),
    ("S27", "agnes", "固定中景 locked medium",
     "“还有另一个人”：空法庭里，辩方椅子与检方椅子分处画面两端，中间留出巨大空白",
     "空白拉开，切走出法庭",
     "Symbolic empty courtroom composition: defense table on the left, prosecution table on the right, a broad strip of empty polished floor between them, high windows out of frame, no people and no readable text. Camera: locked-off medium-wide shot; only dust moves through a shaft of light. One room, no cut.",
     "低频空拍感 + 回声；字幕“证据链断了”"),
    ("S28", "agnes", "背后跟拍 follow behind",
     "无罪释放后的狂妄细节：高大男人背影穿过法庭出口，回头方向只用肩膀动作暗示，手向陪审席抬起致意",
     "致意动作定格，切无罪卡",
     "1993 courthouse corridor, a very tall heavyset man in a dark suit seen only from behind walks toward the exit after a trial, then lifts one hand in a brief thank-you gesture toward the unseen jury behind him; no face, no readable signs, no celebration. Camera: one slow follow from behind. Hold this single corridor, no cut.",
     "脚步声突然变轻 + 一声短促笑意质感但不夸张"),
    ("S29", "agnes", "铁门缓慢闭合 slow close",
     "“无罪释放”：法院出口铁栅门合拢，门外阳光留在地上，人物已经离开",
     "门闩声切法律铁律",
     "Empty courthouse side gate in 1993, a tall iron gate slowly closes after a person has already left, late sunlight makes a long bar across the pavement, no people, no signage, no face. Camera: locked-off low wide shot focused on the closing gate. One exterior, one movement, no cut.",
     "铁门闩落下；字幕大字“无罪释放”"),
    ("S30", "agnes", "法律文件上方缓慢拉远 slow pull-back",
     "“一罪不二审”：黑色法律书合上，桌边的第二把椅子空着，阴影像锁一样落下",
     "书合上接下一章监狱门",
     "Dark legal book with no readable cover on a wooden desk, a blank court seal and an empty second chair beside it, a hard rectangular shadow falls across the desk like a lock; no people, no text. Camera: one slow pull-back from the closed book to the empty chair. Hold one desk, no cut or location change.",
     "厚书合拢 + 金属锁扣；“一罪不二审”由字幕后期添加"),

    # ---------------- N05 神转折（8 镜）----------------
    ("S31", "agnes", "监狱走廊缓慢推进 slow dolly",
     "一九九九年阿曼达案：史密斯走进监狱，门在背后关上，画面只拍背影与铁门",
     "铁门重响接DNA实验室",
     "1999 British prison corridor, a very tall man seen only from behind in a dark prison jacket walks toward a cell door while another heavy door closes behind him, cold fluorescent light, no faces, no readable signs. Camera: one slow dolly forward down the corridor. Single corridor, no cut, no violence.",
     "铁门重响；底鼓节奏开始"),
    ("S32", "graphic", "关键证据卡 static graphic",
     "阿曼达案与 DNA：后期准确呈现年份、姓名和证据来源",
     "DNA 双螺旋线条轻微错位后对齐",
     "一九九九年 · 阿曼达·沃克案\n衣物上的血迹 DNA 与史密斯匹配\n他被定罪并开始服终身刑；后来狱中吹嘘第一案“走掉了”",
     "DNA 电子脉冲 + 低音落点；关键词“DNA”“终身刑”描黄"),
    ("S33", "agnes", "实验室工作台缓慢横移 lateral slide",
     "DNA证据的动画示意：移液器、样本管、封存衣物袋，屏幕数据不可读",
     "样本管光泽接狱中桌面",
     "Forensic laboratory in 1999, close on gloved hands moving a pipette between sample tubes beside a sealed opaque clothing evidence bag, cool blue light, a monitor shows only abstract glowing bars with no readable data, no faces, no blood. Camera: one slow lateral slide across the bench. Hold one lab, no cut.",
     "离心机嗡鸣 + 电子提示音；标签“AI动画示意 · 非证物照片”"),
    ("S34", "agnes", "桌面周围缓慢环绕 slow arc",
     "狱中吹嘘：两个同仓犯人背影隔着金属桌，一人靠近耳语，另一人抬头警觉",
     "警觉抬头接吹嘘卡",
     "1999 prison cell common room, two prisoners shown only from behind at a small metal table, one leans close to whisper while the other slowly raises his head, a barred light pattern on the wall, no faces, no readable writing, no violence. Camera: one restrained slow arc around the table. Hold one room, no cut or change of location.",
     "低声耳语质感 + 金属桌轻响；不合成可辨对白"),
    ("S35", "agnes", "狱窗光线缓慢推近 slow push-in",
     "吹嘘的心理反转：一条狱窗光带越过空桌，留下“以为没人会信”的压迫感",
     "光带像扫描线掠过，切法律书",
     "Empty prison cell table beneath a narrow barred window, a strip of white daylight slowly travels across the tabletop and stops on a blank metal cup, no people, no text, no body. Camera: one very slow push-in toward the cup. Single cell, no cut. Subtle analog chromatic fringe only along the light edge.",
     "磁带倒放 + 心跳低频；引语由字幕后期打出"),
    ("S36", "agnes", "法律书翻页缓慢俯拍 overhead drift",
     "英国法律修改：厚重法典翻页，镜头只见手与纸，不让模型生成法条文字",
     "翻页声接上诉法院走廊",
     "Overhead view of a thick British statute book on a dark desk, only gloved hands turn several blank or deliberately unreadable pages, a brass scale and a closed case file sit beside it, no logos or readable text. Camera: one slow overhead drift following the page turn. Single desk, no cut.",
     "翻页逐渐加速后突然停；字幕“新的且有说服力的证据”"),
    ("S37", "agnes", "指纹图示缓慢横移 lateral move",
     "新证据补上缺口：实验室把抽象指纹卡与一张老租客资料夹并排，手把连线画上",
     "连线落下接证据汇总卡",
     "Controlled forensic diagram on a lab desk: two generic fingerprint cards without readable marks are placed beside an old anonymous tenancy file, a gloved hand draws one clean connecting line between them, no real biometric data, no faces, no text. Camera: one slow lateral move along the line. One desk, no cut.",
     "笔尖划线 + 证据卡扣合声；清楚标记“示意”"),
    ("S38", "agnes", "档案柜之间缓慢后移 slow pull-back",
     "证据链拼成：狱中吹嘘、阿曼达案相似性、指纹属于前房主，三组文件夹在架上形成一条线",
     "三组文件夹对齐后切上诉法院",
     "Dim evidence archive aisle, three anonymous folders and three sealed evidence envelopes arranged in a straight line on one shelf, each separated by a soft pool of light, no readable labels, no people. Camera: one slow pull-back revealing the full line of evidence. Hold one archive aisle, no cut, no second location.",
     "三次卡扣声逐一落点；音乐进入高潮"),

    # ---------------- N06 三十年后（7 镜）----------------
    ("S39", "agnes", "法院台阶缓慢上摇 slow tilt up",
     "二零二二年上诉法院：阴雨中的英国法院台阶，黑色文件袋被双手抱上台阶，不拍脸",
     "台阶上摇匹配二零二三年法庭",
     "Rainy English appellate court steps in 2022, a pair of hands carries a sealed black case folder up broad stone steps, only backs and hands, no face, no readable court sign, no logos. Camera: one slow tilt up following the folder from the wet pavement to the courthouse doors. One exterior, no cut.",
     "雨声 + 远处新闻车底噪；标签“AI动画示意 · 非法院实拍”"),
    ("S40", "agnes", "法庭后排缓慢横移 slow lateral slide",
     "二零二三年五月重审：被告席背影、法官席和陪审团背影，画面不冒充庭审记录",
     "陪审团轻微移动后定住",
     "2023 courtroom reconstruction viewed from the very back: a tall heavyset defendant shown only from behind at the defense table, a jury seen only as backs, the judge's bench and warm wood panels ahead, no recognizable faces, no readable text or flags. Camera: one slow lateral slide behind the gallery. Hold one courtroom, no cut. Clearly an animation reconstruction, not news footage.",
     "法槌两下 + 音乐骤停半秒；标签“AI动画示意 · 非庭审影像”"),
    ("S41", "graphic", "终局卡 static graphic",
     "判决卡：二零二三年五月、萨拉案重审定罪、终身监禁、最低二十七年（扣除羁押）",
     "数字二零二三年与二十七年先后放大",
     "二零二三年五月\n重审定罪：萨拉·克拉姆案\n终身监禁 · 最低二十七年（扣除九十年代羁押时间）",
     "法槌回声 + 一记低音；字幕关键词“重审定罪”“终身监禁”描黄"),
    ("S42", "agnes", "监狱走廊固定大全景 locked wide",
     "结局：空监狱走廊尽头厚重铁门缓缓关上，不把刑罚拍成爽文",
     "铁门合拢，声音留白",
     "Long empty British prison corridor with solid walls and cold fluorescent tubes, no people, a heavy grey steel door at the far end slowly swings shut, no windows and no readable signs. Camera: locked-off wide shot down the corridor for the full clip. One corridor, one door, no cut.",
     "铁门关闭重响后留 0.4 秒静音"),
    ("S43", "agnes", "日历纸张缓慢拉远 slow pull-back",
     "三十年时间感：桌上一叠旧日历页被风吹起，页角从一九九三翻到二零二三，数字不交给模型生成",
     "日历页翻飞接空公寓窗",
     "Close tabletop still life: a stack of blank calendar-like sheets with no readable dates, one sheet after another lifts in a slow breeze, a small hourglass beside them, warm light fading to slate blue, no people, no text. Camera: one slow pull-back as the sheets settle. Hold one table, no cut; dates are added later as subtitles.",
     "纸张翻飞由快到慢；配音念“三十年”时停一拍"),
    ("S44", "agnes", "窗外缓慢推近 slow push-in",
     "向萨拉致意：空公寓窗外清晨，桌上只有一束花的剪影，不出现受害者人像",
     "花影切到最后的海边公路",
     "Quiet west London apartment interior at dawn, shown only through an empty window and a small vase with a simple flower silhouette on the sill, pale light on a vacant chair, no person, no photographs, no readable text. Camera: one very slow push-in from the room toward the flower silhouette. Single room, no cut.",
     "钢琴单音 + 远处城市苏醒；不出现受害者肖像"),
    ("S45", "agnes", "黎明升镜 crane up",
     "金句结尾与评论引导：清晨空旷英国公路，路边证物袋剪影随风，镜头升高看见道路延伸",
     "升到全景后进入片尾卡，最后 0.8 秒渐隐",
     "Dawn on an empty Surrey roadside, a small cluster of sealed evidence-bag silhouettes tied to a fence beside long grass, no labels, no people, pale sun on a straight road receding into mist. Camera: one slow crane up from the anonymous objects to the road and sky. Hold one landscape, no cut, no readable text.",
     "风声 + 单音钢琴；金句逐字出现，最后 0.8 秒音画渐隐"),
]

CARD_HEADER = "案件档案  /  英国 · 1991—2023"
CARD_FOOTER = "资料摘要与示意图 · 非原始证物/庭审影像"
CARDS = {
    "S03": ("大卫·史密斯：无罪之后", "一九九一年命案 · 一九九九年再犯", "二零二三年重审定罪"),
    "S07": ("四个年份", "无罪、再犯、重审", "三十年后，旧案重新打开"),
    "S10": ("人物档案", "英国卡车司机 · 绰号“蜂蜜怪兽”", "普通外表背后，是长期暴力史"),
    "S18": ("假名与密闭空间", "萨拉·克拉姆 · 南奥尔公寓", "“邓肯”是他承认使用的假名"),
    "S23": ("两起命案的相似点", "一九九一年：萨拉 · 一九九九年：阿曼达", "性暴力与毁尸特征，被法庭并置审视"),
    "S32": ("一九九九年转折", "阿曼达·沃克案：DNA 把史密斯送进监狱", "狱中一句“我走掉了”，后来成了新证据"),
    "S41": ("迟到三十年的判决", "二零二三年五月 · 重审定罪", "终身监禁 · 最低二十七年（扣除羁押）"),
}
TITLE_CARD = ["无罪之后，他又杀了人", "大卫·史密斯案 · 三十年后的重审"]
END_CARD = [
    "你觉得，击穿他的到底是什么？",
    "大卫·史密斯 · 1991—2023",
    "法律追上了他，但时间追不回失去的人。",
    "资料：BBC / Sky News / PA · 原创解说 · AI动画情景重现",
]
CAPTION_KEYWORDS = ["无罪", "六年后", "三十年", "假名", "DNA", "狱中吹嘘", "重审定罪", "终身监禁"]
LABEL_OVERRIDES = {
    "S16": "AI动画情景重现 · 非现场影像",
    "S20": "AI动画示意 · 非证物照片",
    "S24": "AI动画示意 · 非庭审影像",
    "S25": "AI动画示意 · 非指纹证物图像",
    "S31": "AI动画情景重现 · 非监狱影像",
    "S33": "AI动画示意 · 非DNA实验室影像",
    "S40": "AI动画示意 · 非庭审影像",
    "S45": "AI动画情景重现 · 非新闻影像",
}
SFX_EVENTS = [
    ("S02", "paper"), ("S04", "machine"), ("S06", "phone"), ("S08", "keys"),
    ("S17", "press"), ("S20", "paper"), ("S24", "paper"), ("S29", "press"),
    ("S31", "press"), ("S33", "machine"), ("S36", "paper"), ("S39", "paper"),
    ("S40", "press"), ("S42", "press"), ("S45", "paper"),
]

TITLES = [
    "他被判无罪，还向陪审团道谢：30年后，一句狱中吹嘘让他终身入狱",
    "无罪释放6年后再杀人｜英国大卫·史密斯案，30年后被“一罪不二审”翻盘",
    "“我已经逃掉了”——英国连环杀手大卫·史密斯，如何被自己说过的话定罪？",
]
HOOK = "他曾因杀人罪无罪释放，走出法庭还向陪审团道谢；六年后再犯，三十年后却被一条法律新例和一句狱中吹嘘翻盘定罪。"
GOLDEN_LINES = [
    "法律可以迟到，但它必须记得自己曾经放走过谁。",
    "真正击穿“完美犯罪”的，常常不是天才侦探，而是凶手以为没人会信的一句话。",
    "你觉得，击穿他的到底是法律的改变，还是他自己的吹嘘？评论区聊聊。",
]
DESCRIPTION = "他第一次被控杀人时被判无罪，走出法庭还向陪审团道谢；六年后，他又因另一桩命案入狱。三十年后，英国双重危险规则出现新的、严格的重审例外，加上狱中吹嘘和新证据，这桩旧案终于重审定罪。全片为 AI 动画情景重现，不是新闻影像，不展示遗体或侵害过程。你觉得真正击穿他的，是法律，还是那句“我走掉了”？"
QUESTION = "你觉得，击穿大卫·史密斯的到底是法律改变，还是他自己的狱中吹嘘？"
HASHTAGS = ["#悬疑科普", "#真实案件", "#英国刑案", "#双重危险", "#动画情景重现"]
GRID = 4
AGNES_SECONDS = 7
SEED_BASE = 20230924


def presentation():
    return {
        "card_header": CARD_HEADER,
        "card_footer": CARD_FOOTER,
        "cards": {sid: list(lines) for sid, lines in CARDS.items()},
        "title_card": TITLE_CARD,
        "end_card": END_CARD,
        "caption_keywords": CAPTION_KEYWORDS,
        "label_overrides": LABEL_OVERRIDES,
        "sfx_events": [list(e) for e in SFX_EVENTS],
    }


def build():
    story = json.loads(PLAN.read_text())
    assert len(SHOTS) * GRID == 180, f"{len(SHOTS)} 镜 × {GRID} 秒 ≠ 180 秒"
    assert len(story["chapters"]) == len(CHAPTERS) == 6
    assert len({sid for sid, *_ in SHOTS}) == len(SHOTS), "镜头号重复"
    cards_needed = {sid for sid, kind, *_ in SHOTS if kind == "graphic"}
    assert cards_needed == set(CARDS), f"信息卡集合不一致：需要 {cards_needed}，已有 {set(CARDS)}"
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
            "seed": SEED_BASE + i + 1,
            "seconds": AGNES_SECONDS, "aspect": "16:9", "resolution": "1080p", "frame_rate": 24,
            "camera": camera, "sfx_note": sfx,
        })
    story["shots"] = shots
    story["presentation"] = presentation()
    story["_scaffold"]["note"] = (
        "内容由 build_story.py 一次性写入；45 镜 × 4 秒规划网格（38 Agnes + 7 信息卡，每镜只用一次）；"
        "解说词与 screenplay.md、audio/manifest.json 三处逐字一致由 generate.py --validate 守着。"
    )
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")
    manifest = json.loads(MANIFEST.read_text())
    manifest["voice_id"] = "voice-00"
    manifest["language"] = "zh-CN"
    manifest["selection"] = "用户试听选择 voice-00；教育/悬疑科普旁白"
    manifest["post_processing"] = "voice-00 TTS → tighten_pauses.py 只收紧静音 → clause_times.py 分句对轨"
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        assert clip["id"] == chapter["id"]
        clip["text"] = chapter["text"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    kinds = [s["kind"] for s in story["shots"]]
    total = sum(len(c["text"]) for c in story["chapters"])
    print(f"story.json 已写入：{len(shots)} 镜 = {kinds.count('agnes')} agnes + {kinds.count('graphic')} graphic，解说 {total} 字（含标点）")


if __name__ == "__main__":
    if "--script" in sys.argv:
        from script_table import render_document
        out = HERE / "抖音脚本.md"
        out.write_text(render_document())
        print(f"抖音脚本.md 已写入（{len(out.read_text())} 字符）")
    elif "--publish" in sys.argv:
        from script_table import publish_document
        out = HERE / "抖音发布文案.md"
        out.write_text(publish_document())
        print(f"抖音发布文案.md 已写入（{len(out.read_text())} 字符）")
    else:
        build()

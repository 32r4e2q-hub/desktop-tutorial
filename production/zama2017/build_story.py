#!/usr/bin/env python3
"""《日本座间九人案：一间公寓里的九条人命》的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
参考实现 production/raincoat2004/ —— 露脸模式的上一部片子；内容按用户上传的 40 镜文案稿改写，
事实按 10 条公开来源核对，见 SOURCES 与 史实核对.md）。

用法::

    python3 production/zama2017/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/zama2017/build_story.py --script   # 生成 抖音脚本.md（3 标题 / 核心爆点 / 四列分镜表 / 金句）
    python3 production/zama2017/build_story.py --publish  # 生成 抖音发布文案.md（标题 / 介绍 / 提问读者一句话 / 话题）

本片是**露脸模式**：四个角色各一张不同的脸，同一角色跨镜头逐字节复用同一条面容 token
（token 只在 cast.json 里写一份，本文件用 {C1}/{C2}/{C3}/{C4} 占位符注入，保证逐字节一致），
并复用同一个 seed；由 production/face_cast.py 的 check-prompts / check-frames 两道闸门守着。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "日本座间九人案：一间公寓里的九条人命"

# 全片统一的画面风格前缀（英文）。写实 3D CGI 情景重现（不是 2D、不是图片轮播）——
# 用户明确要求「3D 动画视频，不是图片视频」。后半句（匿名角色、无真人肖像、无文字、单一运镜）是流水线规则，别删。
# 注意：style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 38 镜全部重做。
STYLE_PREFIX = (
    "Photorealistic cinematic 3D animated reenactment, high-end CGI feature-film render with volumetric light, "
    "physically based materials, shallow depth of field and subtle 35mm film grain, of Japan in the autumn of 2017: "
    "quiet Kanagawa suburban residential streets, ageing low-rise apartment blocks with exterior staircases and steel "
    "railings, modest single rooms with plain tatami and white walls, dim stairwells, commuter railway stations and "
    "platforms, overcast daylight and sodium night lamps, restrained desaturated teal-and-grey colour grading, "
    "slow-burn true-crime documentary mood, "
    "never stylised, never a drawing, never a cartoon; horizontal 16:9 widescreen cinematic composition; the people "
    "are anonymous period characters performed by computer-generated figures - a face is shown only where a shot "
    "explicitly names one of the cast characters, and never as a recognisable real person or a likeness of anybody "
    "living or dead; absolutely no readable text, letters, numbers, logos, license plates or brand marks anywhere "
    "inside the frame; one single continuous smooth slow camera move per shot exactly as directed. "
)

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, invented headlines, neon lettering, logos, brand marks, "
    "watermark, subtitles, on-screen caption, recognisable real person likeness, celebrity likeness, portrait of a real "
    "public figure, blood, gore, wound, corpse, body bag, body parts, dismemberment, autopsy, weapon attack, strangling, "
    "assault, violence on screen, nudity, erotic content, horror monster, ghost, jump scare, flat 2D cartoon, cel-shaded "
    "illustration, hand-drawn sketch, watercolour, comic panel, low-poly, waxy plastic skin, doll-like figure, every "
    "character with the same face, duplicated identical faces, changing face, morphing objects, teleportation, jitter, "
    "flicker, whip pan, fast zoom, jump cut, split screen, collage"
)

# 事实边界与红线：每一条都会印在 抖音脚本.md 的「发布前自查」里。
PRINCIPLES = [
    "全部 Agnes 镜头为写实 3D CGI 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，不冒充搜查、审讯、监控或证物照片",
    "不展示遗体、血腥或作案过程；杀害方式与遗体处理方式一律不写不拍；公寓搜查只出现箱子外观、工作人员背影与取证空镜",
    "凶手由一名虚构的年代角色扮演，是 AI 生成的匿名人物，**不是白石隆浩本人的容貌**，不做任何真实人物的肖像还原",
    "四名露脸角色（年轻男子 / 老刑警 / 年轻女警 / 哥哥）各有一张不同的脸；同一角色跨镜头逐字节复用同一条面容 token 并共用同一个 seed，",
    "由 production/face_cast.py 的 check-prompts（静态闸门）与 check-frames（画面闸门）检查，人眼对照接触表判决",
    "受害者不以具备可辨识面容的人像出现：年轻女性角色一律背影、剪影或远景，未成年人只以远景背影出现，不出现遗体、遗物特写之外的私密画面",
    "每一句事实都能指到 sources 里的一条公开报道；口径冲突处（失踪女孩的具体日期）只写「十月下旬」，不挑一个当结论",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写；画面内不出现任何可读文字、门牌或招牌（AI 街景必编字，靠构图排除）",
    "人工检视 qa/ 接触表与 delivery/face-cast/ 人脸接触表；换脸、畸变、伪文字、中途换场的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

# 每条事实的公开来源。
SOURCES = [
    {"id": 1, "url": "https://www.bbc.com/japanese/55312799",
     "usage": "支撑：二〇二〇年十二月十五日东京地方法院立川支部判处死刑；九名被害人（八女一男，含十五岁）；"
              "以「帮忙死 / 一起死」诱约；九人均无承诺杀害的认定；被告认下检方全部指控"},
    {"id": 2, "url": "https://www.nytimes.com/2017/11/01/world/asia/japan-serial-killer-takahiro-shiraishi.html",
     "usage": "支撑：八王子二十三岁女性（母六月去世后流露轻生意愿，十月二十三日从集体之家失踪）；"
              "哥哥报案并发现 Twitter 往来；警方设局在车站相认、跟踪回家，十月三十日敲门并看到箱子；邻居称两个月异味未报案"},
    {"id": 3, "url": "https://www.telegraph.co.uk/news/2017/10/31/nine-bodies-severed-heads-found-house-tokyo-man-arrested/",
     "usage": "支撑：十月三十一日逮捕；哥哥发现 Twitter 消息后报警；监控拍到女孩与白石在八王子附近车站及座间公寓附近同行；"
              "八月下旬搬入安静住宅街的二层木造小楼"},
    {"id": 4, "url": "https://www.sankei.com/article/20250627-77DVRU25BVK7LB77TGCMG34ITY/",
     "usage": "支撑：十五至二十六岁九人；八月下旬至十月下旬作案；劫财数百至数万日元；辩方上诉后本人撤回、"
              "二〇二一年一月死刑确定；二〇二五年六月二十七日在东京拘置所执行（时隔两年十一个月，石破内阁首次）"},
    {"id": 5, "url": "https://global.udn.com/global_vision/story/8662/8835312",
     "usage": "支撑：案发前做风俗星探，二〇一七年二月因违反职业安定法被捕，保释后回座间老家与父亲同住、在仓库打工；"
              "以「一起自杀」诱约；二〇二五年六月二十七日执行，年三十五"},
    {"id": 6, "url": "https://www.straitstimes.com/asia/east-asia/japan-to-boost-online-regulation-after-grisly-serial-murders",
     "usage": "支撑：公寓仅十三点五平方米；靠遗留银行卡与手机定位初判、家属脱氧核糖核酸确认身份；"
              "含三名高中生与一名年轻母亲；哥哥破解 Twitter 促成埋伏逮捕"},
    {"id": 7, "url": "https://newsmatomedia.com/shiraishi-takahiro",
     "usage": "支撑（一手为搜查一课 / 朝日 / 每日等当时报道）：一九九〇年生于座间；八月十八日看房、八月二十二日入居"
              "（要求「马上入住」）；Twitter 账号「首吊り士」；八月二十二日至十月三十日约两个月九人"},
    {"id": 8, "url": "https://kailnokankaku.com/archives/1599",
     "usage": "支撑：现场为座间市绿丘六丁目旧公寓二楼，月租一万九千日元；案发时二十七岁"},
    {"id": 9, "url": "https://www.bizilabe.elhuyar.eus/Renji-Amano-Yamaguchi/7176132/",
     "usage": "支撑：八女一男构成；十代四名、二十代五名；其中男性系寻找交际女友途中被卷入；"
              "作案期二〇一七年八月二十二日至十月下旬"},
    {"id": 10, "url": "https://ameblo.jp/poohta8/entry-12922979478.html",
     "usage": "支撑（转引每日新闻当时报道）：「为杀害目的入居」——租下公寓就是为了作案；八月中旬起购买工具、"
              "网上搜索遗体处理方法；供述「第二名之后记不清脸」"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。六段合计 ≈ 780 字（含标点）。
CHAPTERS = [
    ("N01", "黄金开头：一扇门后面的九个人",
     "二零一七年十月三十日，日本神奈川县座间市，警察敲开了一间普通公寓的门。"
     "门一开，警察就意识到：这间十几平方米的小屋里，藏着九名失踪者的下落。"
     "而把警察带到这里的，是一名二十三岁女孩失踪前，留在社交媒体上的一条消息。"),
    ("N02", "人物档案：搬进公寓的二十七岁星探",
     "这间公寓的主人叫白石隆浩，一九九零年出生在座间，案发时二十七岁。"
     "他之前在东京街头做过拉人的星探，还因为这份工作被警察抓过。"
     "二零一七年八月二十二日，他搬进这间公寓：绿丘一栋旧公寓的二楼，月租只要一万九千日元。"
     "邻居们说，这个年轻人看起来普普通通。"),
    ("N03", "猎手：两个月，九个人",
     "搬进来之后，他在社交媒体上注册了好几个账号，专门找那些说自己活不下去的年轻人。"
     "他假装自己也一样绝望，说要陪对方一起走，把对方约到自己的公寓。"
     "从八月下旬到十月下旬，短短两个月，九个人走进这间公寓，再也没有出来："
     "八名女性，一名男性，年龄从十五岁到二十六岁。其中那名男性，是来找女友的。"),
    ("N04", "转机：哥哥翻开的聊天记录",
     "转机来自八王子一名二十三岁的女孩。十月下旬她突然失踪，"
     "哥哥翻看她的社交账号，发现她失踪前一直在和一个陌生账号聊天。"
     "车站的监控还拍到，女孩曾和一名男子一起出现在车站。"
     "警方顺着这个账号设下埋伏，约对方在车站见面。"
     "十月三十日，警察一路跟着他，回到了座间市的那间公寓门口。"),
    ("N05", "开门：箱子、逮捕与认罪",
     "门一打开，警察就看到了堆在屋里的几个箱子。"
     "搜查很快确认，此前失踪的九个人，都在这间公寓里找到了下落。"
     "第二天，白石隆浩被警方逮捕。面对审讯，他承认了全部罪行，"
     "还承认这间公寓就是为了作案才租下的。"
     "警方靠遗留的银行卡和手机定位，再比对家属的脱氧核糖核酸，逐一确认了九人的身份。"
     "案件震惊了整个日本。"),
    ("N06", "结局：死刑、执行，和一句警告",
     "二零二零年十二月十五日，东京地方法院立川支部判处他死刑。"
     "他在法庭上认下全部罪名，又撤回上诉，死刑在二零二一年一月确定。"
     "二零二五年六月二十七日，死刑执行，这是日本时隔两年十一个月再次执行死刑。"
     "九条人命，两个月，一间公寓。网络对面的一句我陪你，可能是世上最危险的话。"
     "如果它发给了你，你能分辨出来吗？"),
]

# 每一镜：(id, kind, 运镜, 叙事职责, 衔接方式, 英文提示词 或 信息卡说明, 音效/备注)
# kind = "agnes"（AI 动画）或 "graphic"（信息卡；文案写在下面的 CARDS 里）。
# {C1}/{C2}/{C3}/{C4} 是 cast.json 里的面容 token 占位符（build() 注入，保证逐字节一致）。
HOLD = ("no cut, no scene change, no camera relocation, no second location, no extra people, "
        "no readable text anywhere in frame; hold on this single view for the full clip.")
SHOTS = [
    # ---------------- N01（8 镜：7 agnes + 1 信息卡）----------------
    ("S01", "agnes", "缓慢前推", "开场：座间市的旧公寓楼，秋日阴天，警灯光扫过墙面",
     "接信息卡：案件名片",
     "The exterior of an ageing two-storey wooden apartment block on a quiet residential street in Zama, Kanagawa, on "
     "an overcast autumn morning in 2017: weathered beige walls, an exterior steel staircase, small curtained windows, "
     "wet asphalt and fallen leaves in the foreground, the slow alternating wash of red and blue patrol light sweeping "
     "across the wall from an unseen source; no vehicle, no people, no signage, no lettering, no numbers anywhere. "
     "Slow push toward the staircase, " + HOLD,
     "远处警笛 + 低频悬念音"),
    ("S02", "graphic", "信息卡（静帧）", "名片：案件、时间、规模",
     "接 AGNES：走廊里的警察背影",
     "案件名片：案名 / 地点与年代 / 规模",
     "低音撞击"),
    ("S03", "agnes", "缓慢跟拍（背影）", "两名警察走向那扇门",
     "接 AGNES：门内的箱子",
     "A dim exterior corridor of the same apartment block in daytime: two detectives in plain dark casual jackets with "
     "completely blank solid backs, seen strictly from behind, walking toward a closed flat door at the far end, no "
     "uniforms, no caps, no badges, no insignia, no lettering or emblem on any piece of clothing, one holding a "
     "folded paper folder, worn concrete floor, metal railing on the open side, the door completely plain with no "
     "number plate and no lettering, neighbouring doors equally unmarked, no faces visible, no other people. Slow "
     "tracking shot following their backs toward the door, " + HOLD,
     "脚步 + 走廊回声"),
    ("S04", "agnes", "缓慢前推", "门一开：玄关里堆着的箱子",
     "接 AGNES：露脸镜头（C1 首次出现）",
     "Just inside the entrance of a small dim Japanese flat in daytime: three plain unmarked storage boxes stacked "
     "beside the entranceway, a pair of worn slippers on the concrete step, a bare bulb above, the narrow room beyond "
     "falling into shadow; the boxes are blank plastic with no labels, no printing and no lettering of any kind, no "
     "people, no blood, no other objects. Slow push from the doorway toward the stacked boxes, " + HOLD,
     "门轴声 + 静默"),
    ("S05", "agnes", "缓慢前推（中景）", "屋主首次露面：站在昏暗屋里的年轻男子",
     "接 AGNES：老刑警到场",
     "A medium shot inside the dim flat in daytime: {C1}, standing motionless in the narrow room behind the stacked "
     "boxes, half-turned toward the doorway, arms hanging at his sides, flat daylight from the open door cutting "
     "across one side of his face while the other stays in shadow; behind him only a bare white wall and the dark "
     "rectangle of an inner doorway, no furniture with markings, no lettering, no numbers, no other person. Slow push "
     "in on him, " + HOLD,
     "静默 + 主题动机首次出现"),
    ("S06", "agnes", "缓慢前推（中景）", "老刑警到场：案子被认真写下的一刻",
     "接 AGNES：取证空镜",
     "A medium shot on the apartment exterior corridor in daytime: {C2}, standing at the railing with a folded paper "
     "folder held against his chest with both hands, rain-flecked shoulders, jaw set, gaze angled down the corridor "
     "away from the camera; the background is thrown far out of focus, only soft grey daylight, wet concrete and "
     "blurred railing, a smooth clean backdrop with not a single mark, notice, plate, letter or number anywhere; no "
     "vehicle, no other person in frame. Slow push in on him, " + HOLD,
     "纸张摩擦（SFX paper）"),
    ("S07", "agnes", "俯视缓慢下移", "取证：白手套、证物袋、镊子",
     "接 AGNES：住宅区黄昏",
     "A top-down close view of a plain evidence table under a work lamp: two white cotton gloves laid flat, two "
     "folded paper evidence bags, a small torch, a pair of tweezers, a measuring ruler lying face-down with no "
     "markings visible, all on a bare grey surface; no writing, no numbers, no labels, no photographs, no people, no "
     "blood. Slow overhead descent toward the table, " + HOLD,
     "手套与纸张摩擦（SFX paper）"),
    ("S08", "agnes", "缓慢横摇（高空）", "城市：亮着灯的住宅区，明天还会有",
     "接 N02：座间的旧房子",
     "A high wide view over a quiet suburban residential district in Zama at dusk in autumn 2017: rows of low houses "
     "and small apartment blocks with lit windows under low cloud, wet rooftops, telephone poles and wires crossing "
     "the middle distance, fallen leaves drifting in the air; no illuminated signage, no letters, no numbers, no "
     "vehicles, no people. Slow lateral pan across the rooftops, " + HOLD,
     "风声 + 低频过渡"),

    # ---------------- N02（7 镜：6 agnes + 1 信息卡）----------------
    ("S09", "agnes", "缓慢前推", "出身：座间市的旧房子",
     "接 AGNES：车站通道人流",
     "A small ageing detached house with weathered wooden walls in a quiet Zama neighbourhood in daytime: a low "
     "concrete-block wall, a rusted sliding gate half open, overgrown weeds along the fence, a laundry pole without "
     "laundry, a bare persimmon tree in the yard, soft overcast light; no nameplate, no lettering, no numbers, no "
     "vehicles, no people. Slow push toward the gate, " + HOLD,
     "清晨鸟声 + 低音铺底"),
    ("S10", "agnes", "缓慢跟拍（背影）", "星探：在车站人流里逆流站立的背影",
     "接信息卡：凶手档案",
     "A crowded underground passage of a Tokyo railway station at night in 2017: streams of commuters walking past in "
     "both directions, seen from behind and blurred by motion, a single young man in a dark hoodie standing still "
     "against the flow with his back to the camera, fluorescent light from above, tiled walls swept out of focus with "
     "no posters, no signs, no lettering and no numbers anywhere; no face visible. Slow tracking shot toward his still "
     "back through the crowd, " + HOLD,
     "人流脚步 + 远处广播闷响（无可辨话语）"),
    ("S11", "graphic", "信息卡（静帧）", "档案：出生 / 年龄 / 星探前科",
     "接 AGNES：拘留走廊",
     "凶手档案：出生地与年龄 / 星探前科",
     "纸张翻动（SFX paper）"),
    ("S12", "agnes", "缓慢前推", "前科：拘留走廊与铁门",
     "接 AGNES：搬家纸箱",
     "A bare police detention corridor in Tokyo in 2017: grey painted walls, a heavy steel door with a small barred "
     "hatch, harsh fluorescent light, damp concrete floor, a wooden bench; every wall surface completely bare, no "
     "signs, no plates, no numbers, no notices and no lettering of any kind anywhere in the corridor, no people. Slow "
     "forward dolly down the empty corridor, " + HOLD,
     "铁门回声（SFX keys）"),
    ("S13", "agnes", "缓慢前推", "搬家：八月二十二日，空房间里的纸箱",
     "接 AGNES：十几平米的小屋",
     "An empty six-tatami room of a cheap Japanese flat in daylight: three sealed cardboard boxes, a rolled futon "
     "leaning on the bare white wall, a coiled rope, dusty sunlight through a curtainless window, scuffed wooden "
     "floor; the boxes are plain brown with no printing, no tape lettering and no labels, no people, no furniture. "
     "Slow push across the empty room toward the window, " + HOLD,
     "纸箱轻响 + 窗外蝉鸣"),
    ("S14", "agnes", "缓慢横移", "小屋内：十几平方米的全部家当",
     "接 AGNES：走廊里的邻居",
     "The interior of a cramped single-room flat in Zama in daylight: a low wooden table, a folded mattress, a small "
     "television with a dark blank screen, a plastic laundry basket, thin curtains half drawn over one window, pale "
     "afternoon light; every surface plain, the television screen empty black glass with no logo, no lettering, no "
     "numbers anywhere, no people. Slow lateral track across the room, " + HOLD,
     "环境静默 + 远处生活声"),
    ("S15", "agnes", "缓慢跟拍（背影）", "邻居视角：走廊日常，谁也没多想",
     "接 N03：黑暗中亮起的手机",
     "A quiet exterior corridor of the apartment block in late afternoon: an elderly resident with a shopping bag "
     "walking away from the camera, seen strictly from behind, plain identical doors on one side with no number "
     "plates and no lettering, potted plants by a railing, long soft shadows; no faces visible, no other people, no "
     "signage. Slow tracking shot following the resident's back, " + HOLD,
     "脚步 + 塑料袋轻响"),

    # ---------------- N03（8 镜：7 agnes + 1 信息卡）----------------
    ("S16", "agnes", "缓慢前推（特写）", "猎场（一）：黑暗中亮起的手机",
     "接 AGNES：屏幕光下的脸（C1）",
     "A close view of a smartphone lying on a dark wooden desk at night, nobody in frame: the glowing screen shows "
     "only soft blurred blobs of pale light, no legible text, no icons with letters, no numbers, the phone shell plain "
     "black, a desk lamp pooling warm light on the wood beside it, the rest of the room in darkness; no hands, no "
     "people. Slow push in on the glowing screen, " + HOLD,
     "手机震动（SFX phone）"),
    ("S17", "agnes", "缓慢前推（中景）", "猎场（二）：屏幕光照着的那张脸",
     "接信息卡：猎手的手法",
     "A medium shot in a dark room at night: {C1}, seated at a small desk before a glowing monitor, the cold "
     "screen-light modelling his face from below, fingers resting on a plain black keyboard, eyes lowered toward the "
     "keys; the monitor faces away from the camera so nothing on it is visible, the wall behind bare and dark, no "
     "lettering, no numbers, no other person. Slow push in on his lit face, " + HOLD,
     "键盘轻响 + 低频下潜"),
    ("S18", "graphic", "信息卡（静帧）", "口径：多个账号 / 两个月 / 九人",
     "接 AGNES：月台上的背影",
     "猎手的手法：账号与规模（公开报道口径）",
     "低音撞击"),
    ("S19", "agnes", "缓慢跟拍（远景背影）", "走进公寓的人：只给背影，不给脸",
     "接 AGNES：亮着一扇窗的公寓楼",
     "A young woman in a plain beige coat, seen strictly from behind at a long distance on a railway platform at "
     "dusk: her figure small in the frame, her face never visible, one hand holding a small bag, the empty tracks "
     "ahead, a bench, soft evening light; the platform signs are turned away and out of focus with no legible letters "
     "and no numbers, no vehicles, no other people. Slow tracking shot following her back along the platform, " + HOLD,
     "风声 + 远处电车声"),
    ("S20", "agnes", "缓慢前推", "那栋楼：夜里只有一扇窗亮着",
     "接 AGNES：半开的门",
     "A distant view of the low-rise apartment block in Zama at night: a single window lit warm among dark ones, thin "
     "curtains drawn, rain falling through the cone of a wall lamp, wet ground and fallen leaves in the foreground; "
     "the windows are plain rectangles of light with nothing written or numbered on them, no signage, no lettering "
     "anywhere, no vehicles, no people. Slow push toward the single lit window, " + HOLD,
     "雨声 + 低频"),
    ("S21", "agnes", "缓慢前推", "半开的门：光从门缝里漏出来",
     "接 AGNES：玄关的鞋",
     "A dim apartment corridor at night: one flat door standing slightly ajar with a blade of warm light falling "
     "across the concrete floor, neighbouring doors closed and unmarked, a wall lamp humming above, deep shadow at "
     "both ends; no number plates, no lettering, no numbers, no people. Slow push toward the half-open door, " + HOLD,
     "灯管电流声 + 静默"),
    ("S22", "agnes", "缓慢下移（特写）", "遗物：玄关处散着的鞋（不出现人）",
     "接 AGNES：秋雨中的住宅街",
     "A close view of a narrow flat entranceway at night: several pairs of plain shoes scattered on the concrete "
     "step, indoor slippers, a folded umbrella, a single bare bulb above, the inner room dark beyond; no people, no "
     "blood, no lettering, no labels. Slow downward move across the scattered shoes, " + HOLD,
     "静默 + 低音"),
    ("S23", "agnes", "缓慢前推（低机位）", "秋雨：空无一人的住宅街",
     "接 N04：深夜家中的哥哥",
     "A quiet suburban street in Zama in autumn rain in daytime: wet asphalt, low hedges, telephone poles, rain "
     "streaking the air, fallen leaves plastered on the pavement, grey sky; no shopfront, no signboard, no vehicle, "
     "no person, no lettering anywhere. Slow low-angle push forward along the empty road, " + HOLD,
     "雨声 + 低频过渡"),

    # ---------------- N04（7 镜：6 agnes + 1 信息卡）----------------
    ("S24", "agnes", "缓慢前推（中景）", "转机（一）：深夜里翻看手机的哥哥",
     "接信息卡：转机",
     "A medium shot in a small dark living room late at night: {C4}, seated on the edge of a sofa, hunched over a "
     "smartphone held in both hands, the pale screen-light on his worried face, eyes fixed downward; behind him only "
     "a dark bookshelf and a curtained window, the phone screen angled away so nothing on it is legible, no "
     "lettering, no numbers, no other person. Slow push in on him, " + HOLD,
     "静默 + 时钟滴答"),
    ("S25", "graphic", "信息卡（静帧）", "转机：八王子 / 二十三岁 / 社交账号",
     "接 AGNES：聊天记录特写",
     "转机：失踪与聊天记录（公开报道口径）",
     "低音铺底"),
    ("S26", "agnes", "缓慢前推（特写）", "证据：那段不能细看的聊天记录",
     "接 AGNES：网络搜查的女警",
     "A close view of a hand holding a smartphone at night: the screen angled half away from the camera shows only "
     "blurred pale message bubbles with no legible text, no names, no numbers, the thumb resting beside the screen, "
     "lamplight on the hand, dark background; no face, no other person, no readable text anywhere. Slow push in on "
     "the hand and the glowing screen, " + HOLD,
     "手机滑动声（SFX phone）"),
    ("S27", "agnes", "缓慢前推（中景）", "转机（二）：顺着账号追下去的人",
     "接 AGNES：搜查会议桌",
     "A medium shot in a police cyber-crime office at night: {C3}, seated before two monitors, the cool screen-light "
     "on her face, one hand on a plain keyboard, head turned slightly as she studies the screens; the monitors face "
     "away from the camera so nothing on them is visible, desks and binders behind thrown out of focus with no "
     "labels, no lettering, no numbers, no other person. Slow push in on her, " + HOLD,
     "键盘声 + 机房低鸣"),
    ("S28", "agnes", "缓慢前推（特写）", "部署：会议桌上空白的资料",
     "接 AGNES：车站设伏",
     "A close view of a meeting table in a police office at night: several documents lying face-down with blank backs "
     "to the camera, a man's hand resting on the pile, cold paper cups, a desk lamp, blurred grey wall behind; no "
     "readable text, no stamps, no labels, no faces, no other person. Slow push toward the hand and the blank papers, "
     + HOLD,
     "纸页轻响（SFX paper）"),
    ("S29", "agnes", "缓慢横移（背影）", "设伏：月台上保持距离的两个人",
     "接 AGNES：车站外的老刑警",
     "A railway platform in Zama in the daytime: two figures standing apart, both seen strictly from behind - a "
     "plain-clothed officer with his hands in his coat pockets and a young woman in a light coat holding a phone - an "
     "empty bench between them, the tracks stretching ahead, soft daylight; the platform signs are out of focus with "
     "no legible letters and no numbers, no train in frame, no faces visible, no other people. Slow lateral move "
     "across their backs, " + HOLD,
     "风声 + 远处电车进站"),
    ("S30", "agnes", "缓慢前推（中景）", "跟踪：车站外假装看报的老刑警",
     "接 N05：敲门的手",
     "A medium shot outside a suburban railway station in daytime: {C2}, in plain clothes with his coat collar up, "
     "standing by a concrete pillar, pretending to read a folded blank newspaper while watching off to one side of "
     "the frame, commuters passing behind him, all seen from behind and thrown out of focus; the newspaper shows no "
     "headlines and no photographs, the station wall behind is out of focus with no signage and no lettering, no "
     "vehicle, no other face in frame. Slow push in on him, " + HOLD,
     "人流声 + 低频"),

    # ---------------- N05（8 镜：7 agnes + 1 信息卡）----------------
    ("S31", "agnes", "缓慢前推（特写）", "敲门：落在门板上的手",
     "接 AGNES：审讯室（C1 露脸）",
     "A close view of a plain flat door in an apartment corridor in daytime: a man's hand raised to knock, knuckles "
     "touching the wood, the door completely bare with no number plate and no lettering, worn concrete floor below, "
     "the corridor stretching out of focus behind; no face, no other person. Slow push toward the hand and the door, "
     + HOLD,
     "敲门声（SFX press）+ 静默"),
    ("S32", "agnes", "缓慢前推（中景）", "审讯：他承认了全部罪行",
     "接 AGNES：搬出的箱子",
     "A medium shot inside a plain interrogation room at night: {C1}, seated at a metal table, a dark hoodie folded "
     "on the chair behind him, hands flat on the table in front of him, head lifted and turned a little away from the "
     "lamp, a desk lamp behind the table throwing hard light across one side of his face, a cassette recorder and a "
     "paper cup on the table; grey concrete walls, no lettering, no numbers, no files with readable text, no other "
     "person. Slow push in on him, " + HOLD,
     "录音机按键 + 低频"),
    ("S33", "agnes", "缓慢横移", "搜查：从门口搬出的箱子",
     "接 AGNES：记者群",
     "An apartment corridor in daytime: three investigators in dark work wear and white gloves carrying plain "
     "unmarked storage boxes out of an open flat door, all seen strictly from behind, the boxes blank with no labels "
     "and no lettering, camera flash blinking in the doorway, concrete floor and railing; no faces visible, no body, "
     "no blood, no numbers. Slow lateral move across the doorway and the workers, " + HOLD,
     "快门 + 脚步"),
    ("S34", "agnes", "缓慢前推（背影）", "舆论：围着的记者群（构图中不出现建筑）",
     "接 AGNES：审讯对质",
     "A tight crowd of reporters in Zama in 2017, photographed from behind: only the backs of heads and shoulders, "
     "raised microphones held low and one shoulder-mounted camera stripped of every marking, its body plain dark "
     "plastic with no logo, no channel number and no lettering anywhere, dry asphalt underfoot; beyond the crowd the "
     "frame holds only soft grey overcast daylight and the blurred emptiness of an open square - no building, no "
     "windows, no door, no glass, no reflection, no signage and no lettering anywhere; no faces visible. Slow push in "
     "over the shoulders, " + HOLD,
     "快门连响（SFX press）+ 嘈杂人声"),
    ("S35", "agnes", "缓慢前推（双人中景）", "对质：审讯桌的两边",
     "接信息卡：关键日期",
     "A two-shot at a metal table in a bare interrogation room at night: an older detective sits on the left, leaning "
     "forward with both hands flat on the table and his back and shoulders toward the camera so that his face is "
     "never visible; {C1} sits on the right with his forearms on the table and his head raised, lit hard by the desk "
     "lamp; between them several photographs lie face-down and unreadable, the wall behind is bare concrete, no "
     "lettering, no numbers, no readable text, no third person. Slow push in between the two of them, " + HOLD,
     "椅子挪动 + 低频"),
    ("S36", "graphic", "信息卡（静帧）", "关键日期：十月三十日搜查 / 十月三十一日逮捕",
     "接 AGNES：留置走廊",
     "关键日期卡：搜查与逮捕",
     "低音撞击"),
    ("S37", "agnes", "缓慢跟拍（背影）", "带走：留置走廊里的三个背影",
     "接 AGNES：街头的人群",
     "A police detention corridor at night: three figures walking away from the camera toward a heavy steel door - a "
     "young man in a dark hoodie flanked by two uniformed officers, all seen strictly from behind, the uniforms plain "
     "dark fabric with no badges, no lettering and no numbers, cold fluorescent light, wet-look concrete floor; the "
     "walls are completely bare with no notices and no lettering, no faces visible. Slow tracking shot following "
     "their backs down the corridor, " + HOLD,
     "脚步 + 铁门（SFX keys）"),
    ("S38", "agnes", "缓慢前推（背影）", "震惊：街头驻足的人群（构图中不出现店面）",
     "接 N06：法院外的清晨",
     "A crowd of pedestrians waiting at a wide Tokyo crossing at dusk, all seen strictly from behind: heads and "
     "shoulders filling the lower frame, all gazing toward a large glowing screen far ahead that dissolves into soft "
     "unfocused light with no legible image and no lettering; on both sides only blurred trees and lamp posts, no "
     "shopfront, no signboard, no neon, no vehicles. Slow push in over the crowd toward the light, " + HOLD,
     "人声嘈杂 + 低频"),

    # ---------------- N06（7 镜：5 agnes + 2 信息卡）----------------
    ("S39", "agnes", "缓慢前推", "审判：法院外的清晨",
     "接 AGNES：法庭内",
     "The exterior of a Japanese district courthouse on a cold grey morning in December: broad stone steps, a row of "
     "people whose backs are turned to the camera, a police officer's shoulder in the foreground, flagstones in soft "
     "flat light, the building's columns rising out of frame; the entrance is deep shadow with no emblem, no signage, "
     "no lettering, no numbers anywhere, no faces visible. Slow push in up the steps, " + HOLD,
     "脚步 + 人群低语"),
    ("S40", "agnes", "缓慢前推（手部近景）", "判决：木槌落在没有字的判决书上",
     "接信息卡：判决时间线",
     "A close side view of a courtroom bench in Japan in December: a judge's hands, seen without the face, resting on "
     "a blank document on the bench, a wooden gavel standing upright beside them, a fountain pen, a thick closed law "
     "book, dark wood panelling behind, warm light from above, no readable text anywhere, no insignia, no other "
     "person. Slow push in on the hands and the gavel, " + HOLD,
     "木槌轻落（SFX press）+ 纸张"),
    ("S41", "graphic", "信息卡（静帧）", "判决：二〇二〇年十二月十五日死刑 / 二〇二一年一月确定",
     "接 AGNES：监狱外墙",
     "判决时间线：死刑与确定",
     "低音撞击"),
    ("S42", "agnes", "缓慢后拉", "执行：监狱的墙与暮色",
     "接信息卡：执行",
     "The outer wall of a detention centre in Japan on a grey evening: long grey concrete wall with coils of razor "
     "wire along the top, a tall steel gate, a single lamp on a pole, wet asphalt in the foreground, low cloud "
     "above, cold blue-grey light; the concrete wall is completely bare - smooth panels with no plates, no markings, "
     "no numbers and no lettering of any kind, the gate plain, no vehicles, no people. Slow pull back from the wall "
     "and the gate, " + HOLD,
     "风声 + 远处铁门"),
    ("S43", "graphic", "信息卡（静帧）", "执行：二〇二五年六月二十七日 / 时隔两年十一个月",
     "接 AGNES：空房间",
     "执行卡：死刑执行（公开报道口径）",
     "低音铺底"),
    ("S44", "agnes", "缓慢前推", "空了的房间：退租后的小屋，窗帘飘动",
     "接 AGNES：黑暗中亮起的手机",
     "An empty single-room flat in Zama in daylight, stripped after the tenant left: bare white walls, scuffed wooden "
     "floor, a curtainless window with thin curtains drifting in the draught, pale sunlight lying across the "
     "floorboards, nothing else in the room, no people, no lettering, no numbers. Slow push across the empty sunlit "
     "room toward the window, " + HOLD,
     "风声 + 窗帘轻响"),
    ("S45", "agnes", "缓慢前推（特写，微光）", "金句画面：黑暗中，一只手拿起亮起的手机",
     "片尾卡叠在最后一秒上",
     "A close view in darkness: a young person's hand reaching for a smartphone lying on a bedside table, the screen "
     "lighting up with soft blurred light that shows no legible text, no names and no numbers, the fingers closing "
     "around the phone, the room around nearly black except a faint cold wash of moonlight from a curtained window "
     "outlining the table; no face, no other person, no readable text anywhere. Slow push in on the hand and the "
     "glowing phone, " + HOLD,
     "手机亮起 + 片尾音乐"),
]

# ---------------------------------------------------------------------------
# 画面上的文字（render.py 从 story.json 的 presentation 块读，不在 render.py 里写死）
# ---------------------------------------------------------------------------
CARD_HEADER = "案件档案  /  座间 · 二〇一七"              # 每张信息卡左上角的小字
CARD_FOOTER = "公开报道口径 · 并非原始档案影像"                    # 每张信息卡左下角的小字
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S02": ("座间九人案", "日本 · 神奈川县座间市 二〇一七", "一间公寓 · 九人遇害"),
    "S11": ("凶手档案", "一九九〇年生 · 座间 二十七岁", "街头星探 · 有前科"),
    "S18": ("他把猎场搬到了网上", "多个社交账号 · 两个月", "九人走进公寓 · 没有出来"),
    "S25": ("转机：一条聊天记录", "八王子 · 二十三岁女孩失踪", "哥哥翻看了她的社交账号"),
    "S36": ("二〇一七年十月", "三十日 搜查 · 三十一日 逮捕", "九名失踪者 · 全部找到下落"),
    "S41": ("判决", "二〇二〇年十二月十五日 死刑", "二〇二一年一月 死刑确定"),
    "S43": ("执行", "二〇二五年六月二十七日 死刑执行", "时隔两年十一个月 · 九条人命"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["日本座间九人案", "一间公寓里的九条人命 · 二〇一七 座间"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "你能分辨出来吗？",
    "座间九人案 · 二〇一七 · 九人遇害",
    "那句我陪你，可能是世上最危险的话。",
    "资料：BBC / 纽约时报 / 产经新闻 · 原创解说 · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词）
CAPTION_KEYWORDS = [
    "十月三十日", "九名失踪者", "社交媒体",
    "白石隆浩", "星探", "八月二十二日",
    "陪对方一起走", "八名女性", "十五岁到二十六岁",
    "八王子", "陌生账号", "车站见面",
    "几个箱子", "承认了全部罪行", "为了作案才租下",
    "死刑", "两年十一个月", "我陪你",
]
# 逐镜标签覆盖：默认 agnes 镜头标「AI动画情景重现 · 非新闻影像」，搜查/审讯/法院镜头写得更具体
LABEL_OVERRIDES = {
    "S03": "AI动画情景重现 · 非搜查现场影像",
    "S04": "AI动画情景重现 · 非搜查现场影像",
    "S06": "AI动画情景重现 · 非搜查现场影像",
    "S07": "AI动画情景重现 · 非警方取证影像",
    "S27": "AI动画情景重现 · 非警方办案影像",
    "S28": "AI动画情景重现 · 非警方办案影像",
    "S29": "AI动画情景重现 · 非抓捕现场影像",
    "S30": "AI动画情景重现 · 非抓捕现场影像",
    "S31": "AI动画情景重现 · 非搜查现场影像",
    "S32": "AI动画情景重现 · 非审讯影像",
    "S33": "AI动画情景重现 · 非搜查现场影像",
    "S34": "AI动画情景重现 · 非新闻采访影像",
    "S35": "AI动画情景重现 · 非审讯影像",
    "S37": "AI动画情景重现 · 非警方拘留影像",
    "S38": "AI动画情景重现 · 非新闻采访影像",
    "S39": "AI动画情景重现 · 非法院实景",
    "S40": "AI动画示意 · 非庭审影像",
    "S42": "AI动画情景重现 · 非监狱实景",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S06", "paper"),
    ("S07", "paper"),
    ("S11", "paper"),
    ("S12", "keys"),
    ("S16", "phone"),
    ("S26", "phone"),
    ("S28", "paper"),
    ("S31", "press"),
    ("S34", "press"),
    ("S37", "keys"),
    ("S40", "press"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "9个人走进同一间公寓再也没出来，破案的是一条社交媒体消息｜日本座间九人案",
    "日本座间九人案：他说我陪你，两个月里9人遇害，最小的才15岁",
    "哥哥翻开妹妹的聊天记录，顺藤摸瓜找到一间藏着9条人命的公寓",
]
HOOK = "二〇一七年，日本座间市一间十几平方米的公寓里找到九名失踪者的下落；凶手用社交媒体把人约上门，破案的线索来自一名失踪女孩的哥哥翻开的聊天记录。"
GOLDEN_LINES = [
    "网络对面的一句我陪你，可能是世上最危险的话。",
    "九条人命，两个月，一间公寓。",
    "如果它发给了你，你能分辨出来吗？评论区聊聊。",
]
DESCRIPTION = (
    "二〇一七年十月三十日，日本神奈川县座间市，警察敲开一间普通公寓的门，找到了此前失踪的九个人。"
    "公寓的主人叫白石隆浩，二十七岁；他在社交媒体上假装温柔，把年轻人约到自己的公寓，两个月里九人遇害。"
    "破案的转机，是一名失踪女孩的哥哥翻开的聊天记录。本片画面为 AI 生成的情景重现（非新闻影像），"
    "事实依据公开报道整理。你能分辨出来吗？"
)
QUESTION = "如果那句我陪你发给了你，你能分辨出来吗？"
HASHTAGS = ["#悬疑", "#真实案件", "#日本", "#座间九人案", "#案件解说"]

GRID = 4           # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 7  # 每个 Agnes 镜头实际请求的时长（169 帧 @ 24 fps）
SEED_BASE = 20170822  # 搬进公寓的日子（二〇一七年八月二十二日），让 seed 可追溯

# 露脸镜头登记（镜头号 -> 角色 id）：只有这里登记的镜头允许出现面容 token，
# 与 cast.json 的 shots 映射一一对应（face_cast.py check-prompts 两边都查）。
FACE_SHOTS = {
    "S05": ["C1"],
    "S06": ["C2"],
    "S17": ["C1"],
    "S24": ["C4"],
    "S27": ["C3"],
    "S30": ["C2"],
    "S32": ["C1"],
    "S35": ["C1"],
}
# 用定妆照做首帧（图生视频）的镜头：每个角色的首次露脸镜头，把这张脸钉在观众第一眼里。
# 定妆照提交在仓库里，URL 取 cast.json 的 portrait_url（Agnes 只在服务器侧取图）。
REFERENCE_SHOTS = {"S05": "C1", "S06": "C2", "S24": "C4", "S27": "C3"}


def faces():
    """从 cast.json 读面容 token（唯一来源），保证提示词里逐字节一致。"""
    cast = json.loads(CAST.read_text(encoding="utf-8"))
    return {c["id"]: (c.get("face") or "").strip() for c in cast.get("characters", [])}


def portrait_urls():
    cast = json.loads(CAST.read_text(encoding="utf-8"))
    return {c["id"]: (c.get("portrait_url") or "") for c in cast.get("characters", [])}


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
    face = faces()
    url = portrait_urls()
    for cid in {cid for ids in FACE_SHOTS.values() for cid in ids}:
        assert face.get(cid), f"cast.json 里没有角色 {cid} 的面容 token"
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
        prompt = body
        if kind == "agnes":
            for cid, token in face.items():
                prompt = prompt.replace("{" + cid + "}", token)
            assert "{" not in prompt and "}" not in prompt, f"{sid} 提示词里还有没替换的占位符"
        shot = {
            "id": sid, "kind": kind, "start": start, "duration": GRID,
            "narration_id": f"N{min(6, start // 30 + 1):02d}",
            "prompt": prompt if kind == "agnes" else "",
            "purpose": purpose, "transition_out": transition,
            "graphic": body if kind == "graphic" else "",
            "seed": SEED_BASE + i + 1,
            "seconds": AGNES_SECONDS, "aspect": "16:9", "resolution": "1080p", "frame_rate": 24,
            "camera": camera, "sfx_note": sfx,
        }
        if sid in FACE_SHOTS:
            shot["cast"] = FACE_SHOTS[sid]
        if sid in REFERENCE_SHOTS:
            shot["reference_image"] = url[REFERENCE_SHOTS[sid]]
        shots.append(shot)
    story["shots"] = shots
    story["presentation"] = presentation()
    story.setdefault("_scaffold", {})["note"] = (
        "内容由 build_story.py 一次性写入；45 镜 × 4 秒规划网格（每镜只用一次）；"
        "露脸模式：面容 token 只在 cast.json 里写一份，build_story.py 用占位符注入，保证逐字节一致；"
        "解说词与 screenplay.md、audio/manifest.json 三处逐字一致由 generate.py --validate 守着。")
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")

    manifest = json.loads(MANIFEST.read_text())
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        assert clip["id"] == chapter["id"]
        clip["text"] = chapter["text"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    kinds = [s["kind"] for s in story["shots"]]
    chars = sum(len(c["text"]) for c in story["chapters"])
    print(f"story.json 已写入：{len(shots)} 镜 = {kinds.count('agnes')} agnes + {kinds.count('graphic')} graphic，"
          f"解说 {chars} 字（含标点）")
    print("逐章字数：" + " / ".join(f"{c['id']} {len(c['text'])}" for c in story["chapters"]))
    print(f"露脸镜头：{len(FACE_SHOTS)} 镜；定妆照首帧：{len(REFERENCE_SHOTS)} 镜")
    todo = json.dumps(story, ensure_ascii=False).count("TODO")
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

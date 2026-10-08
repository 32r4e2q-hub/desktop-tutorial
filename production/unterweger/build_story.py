#!/usr/bin/env python3
"""《杰克·翁特维格：最成功的一次伪装》的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

本文件由 production/new_topic.py 从模板开出，内容按用户上传的 40 镜文案稿
（抖音文案/20261008-075847_粘贴的文案_20261008-075847.txt）改写，
事实按 9 条公开来源核对（见 SOURCES 与 史实核对.md）。

用户的硬要求：① 3D 动画（不是图片轮播）；② 人物要多、人物镜头要多（不是一路场景空镜）；
③ 可以露脸，但每个人物一张不同的脸、同一人物跨镜头同一张脸；④ 按上传稿的「反转」结构写——
前半段先让观众相信「一个杀人犯成功改造、成了作家」，到一分二十秒左右才第一次出现新的命案。

用法::

    python3 production/unterweger/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/unterweger/build_story.py --script   # 生成 抖音脚本.md
    python3 production/unterweger/build_story.py --publish  # 生成 抖音发布文案.md

本片是**露脸模式**：六个角色各一张不同的脸，同一角色跨镜头逐字节复用同一条面容 token
（token 只在 cast.json 里写一份，本文件用 {C1}…{C6} 占位符注入，保证逐字节一致），
并复用同一个 seed；由 production/face_cast.py 的 check-prompts / check-frames 两道闸门守着。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "杰克·翁特维格：最成功的一次伪装"

# 全片统一的画面风格前缀（英文）。写实 3D CGI 情景重现（不是 2D、不是图片轮播）——
# 用户明确要求「3D 动画视频，不是图片视频」。后半句（匿名角色、无真人肖像、无文字、单一运镜）是流水线规则，别删。
# 注意：style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 38 镜全部重做。
STYLE_PREFIX = (
    "Photorealistic cinematic 3D animated reenactment, high-end CGI feature-film render with volumetric light, "
    "physically based materials, shallow depth of field and subtle 35mm film grain, of Austria and the United States "
    "between 1974 and 1994: Viennese stone facades and narrow shopping streets, wood-panelled courtrooms and "
    "publishing offices, a dark prison wing and a writer's cell, television studios with heavy 1980s cameras, "
    "rain-wet Los Angeles boulevards and a Florida holding room, alpine woodland at grey dawn, overcast daylight and "
    "warm tungsten practical lamps, restrained desaturated teal-and-amber colour grading, slow-burn true-crime "
    "documentary mood, "
    "never stylised, never a drawing, never a cartoon; horizontal 16:9 widescreen cinematic composition; the people "
    "are anonymous period characters performed by computer-generated figures - a face is shown only where a shot "
    "explicitly names one of the cast characters, and never as a recognisable real person or a likeness of anybody "
    "living or dead; absolutely no readable text, letters, numbers, logos, license plates or brand marks anywhere "
    "inside the frame; one single continuous smooth slow camera move per shot exactly as directed. "
)

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, invented headlines, neon lettering, logos, brand marks, "
    "watermark, subtitles, on-screen caption, recognisable real person likeness, celebrity likeness, portrait of a real "
    "public figure, blood, gore, wound, corpse, body bag, body parts, ligature marks, autopsy, weapon attack, "
    "strangling on screen, sexual violence, assault, violence on screen, nudity, erotic content, horror monster, ghost, "
    "jump scare, flat 2D cartoon, cel-shaded illustration, hand-drawn sketch, watercolour, comic panel, low-poly, "
    "waxy plastic skin, doll-like figure, every character with the same face, duplicated identical faces, changing "
    "face, morphing objects, teleportation, jitter, flicker, whip pan, fast zoom, jump cut, split screen, collage"
)

# 事实边界与红线：每一条都会印在 抖音脚本.md 的「发布前自查」里。
PRINCIPLES = [
    "全部 Agnes 镜头为写实 3D CGI 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，不冒充新闻、庭审、监控或证物影像",
    "不展示遗体、血腥、性暴力与作案过程；六名已知受害者的行踪只写到「失踪」「在城郊林地被发现」这一层，不做任何作案动作的重现",
    "片名侧的人物是一名虚构的年代角色，是 AI 生成的匿名人物，**不是杰克·翁特维格本人的容貌**，不做任何真实人物的肖像还原",
    "六个露脸角色（作家 / 女记者 / 出版社编辑 / 维也纳刑警 / 洛杉矶女警探 / 夜场女招待）各有一张不同的脸；同一角色跨镜头逐字节复用同一条面容 token 并共用同一个 seed",
    "由 production/face_cast.py 的 check-prompts（静态闸门）与 check-frames（画面闸门）检查，人眼对照接触表判决",
    "受害者不以具备可辨识面容的人像出现：女性角色（女记者、女警探、女招待）均为虚构的从业者，不是任何受害者；受害者只以空镜、物件与信息卡出现",
    "每一句事实都能指到 sources 里的一条公开来源；说法冲突处（1974 年被害人遇害的日子、被捕的部门与确切日期）只写不会写错的口径，不挑一个当结论",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写；画面内不出现任何可读文字、门牌或招牌（AI 街景必编字，靠构图排除）",
    "人工检视 qa/ 接触表与 delivery/face-cast/ 人脸接触表；换脸、畸变、伪文字、中途换场的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

# 每条事实的公开来源。
SOURCES = [
    {"id": 1, "url": "https://en.wikipedia.org/wiki/Jack_Unterweger",
     "usage": "支撑：一九五〇年八月十六日生于施泰尔马克州尤登堡；一九七六年六月一日因一九七四年十二月十一日玛格丽特·舍费尔案被判终身监禁；"
              "狱中写作出书；一九九〇年五月二十三日服刑满十五年（实际约十五年四个月）后假释；出狱后为公共广播 ORF 工作；"
              "一九九二年二月二十七日在迈阿密被美国法警逮捕；一九九二年五月二十七日引渡回奥地利，被控十一项谋杀；"
              "陪审团以六比二认定九项谋杀成立；一九九四年六月二十九日判处终身监禁且不得假释；当日自杀"},
    {"id": 2, "url": "https://www.theguardian.com/world/2007/nov/10/1",
     "usage": "支撑（约翰·里克《维也纳森林杀手》书摘）：一九九〇年五月二十三日出狱当天媒体口径「畅销书作者、七本书、想把《炼狱》再拍成电影」；"
              "作家与艺术家联署请愿；一九九一年五月二十二日维也纳红灯火街区四名女性失踪、首具遗体五月二十日在维也纳森林被发现；"
              "一九九四年四月二十日开庭、被称为「世纪审判」；六月二十八日深夜至二十九日凌晨在格拉茨监狱用金属丝与运动裤抽绳自缢"},
    {"id": 3, "url": "https://murderpedia.org/male.U/u/unterweger-jack.htm",
     "usage": "支撑：一九九一年六月至七月在洛杉矶期间三名女性（香农·埃克斯利、艾琳·罗德里格斯、雪莉·安·朗）遇害、作案手法相同；"
              "一九九一年由奥地利杂志派往洛杉矶写红灯区报道、并随当地警方巡逻；一九九二年二月在迈阿密被捕；同年五月被引渡；"
              "一九九四年六月在格拉茨受审、认定九项谋杀成立、判处终身监禁;当晚在格拉茨-卡尔劳监狱自缢"},
    {"id": 4, "url": "https://jimshelley.com/crime/jack-unterweher/",
     "usage": "支撑：一九九〇年十月至一九九一年五月维也纳与格拉茨至少七名女性遇害、均为性工作者、均被勒死并弃于林地；"
              "一九九一年与洛杉矶三案手法一致（用被害人自己的内衣做勒具、弃于灌木地）；两名泰勒警探比对两地案卷；"
              "一九九二年二月十三日发出逮捕令时人已潜逃，其女友比安卡·姆拉克全程同行；一九九一年六月十一日至七月十六日在洛杉矶"},
    {"id": 5, "url": "https://www.wikiwand.com/de/Jack_Unterweger",
     "usage": "支撑（德语维基，与奥方口径一致）：一九七四年十二月十二日与熟人芭芭拉·朔尔茨同行时遇到十八岁的玛格丽特·舍费尔，两人将其带入住宅捆绑、劫财后带离；"
              "一九七六年判终身监禁；一九九〇年五月二十三日依刑法第四十六条第五款经司法部长同意假释、无附加条件；"
              "一九九四年六月陪审团认定九项谋杀成立（两案因证据不足判无罪）、判处终身监禁且不得假释；当夜自杀于格拉茨"},
    {"id": 6, "url": "https://www.nytimes.com/1994/06/30/obituaries/jack-unterweger-44-austrian-writer-convicted-of-murder.html",
     "usage": "支撑：出狱后成为维也纳文化界的名人、被当作「改造成功」的范例；一九九四年六月二十九日在宣判当夜自杀，终年四十三岁"},
    {"id": 7, "url": "https://www.serialkillercalendar.com/Jack%20UNTERWEGER.php",
     "usage": "支撑：年轻时多次因盗窃、性侵入狱（一九六六年至一九七五年间十六次定罪）；狱中写诗、短篇、剧本与自传《炼狱》；"
              "出狱后主持电视节目、为杂志写稿，并被派往洛杉矶采访红灯区；被捕后引渡回奥地利"},
    {"id": 8, "url": "https://theskeletonkeychronicles.com/2019/10/15/jack-unterweger-the-silver-tongued-devil/",
     "usage": "支撑：一九九〇年九月布拉格一案；随后维也纳与格拉茨多案；三名洛杉矶女性遇害；勒具来自被害人自己的衣物成为作案标记（本片只写到「相同的手法」）"},
    {"id": 9, "url": "https://www.imdb.com/name/nm0881373/news/",
     "usage": "支撑：他被媒体称作「跨大西洋连环杀手」；一九七四年首案、服刑十五年、出狱后案件延续至洛杉矶与迈阿密；"
              "奥地利法院认定九个谋杀罪名成立（本片只使用与法院认定一致的口径）"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。六段合计 ≈ 780 字（含标点），
# 结构按用户上传稿的反转设计：前两章要让观众相信「改造成功」，第三章末才第一次出现新的命案。
CHAPTERS = [
    ("N01", "黄金开头：一个杀过人的人，出了名",
     "一九九〇年五月二十三日，奥地利一家监狱的门口，记者们等了整整一上午。他们等的不是政客，是一个刚出狱的杀人犯：杰克·翁特维格，三十九岁，服刑满十五年，今天被假释。出书、写剧本、上电视，很多人把他当成一个奇迹。三年后，警方给出的答案，让整个奥地利都沉默了。"),
    ("N02", "第一次杀人（一九七四）",
     "时间倒回一九七四年十二月。十八岁的玛格丽特·舍费尔在夜里失踪，警方很快锁定了一个二十四岁的年轻人：他之前十六次进出监狱，罪名大多是盗窃和性侵。一九七六年六月，他因这起谋杀被判处终身监禁。所有人都以为，他的人生会在监狱里结束。但他在牢房里拿起了笔。"),
    ("N03", "监狱里的作家，和替他请愿的人",
     "他在狱中写诗、写小说、写剧本，还写了一本自传《炼狱》。书出版了，甚至有学校把它当教材。作家、艺术家、诺贝尔文学奖得主联名替他请愿：一个能把自己的罪行写成文学的人，应该是真的悔改了。一九九〇年五月，他走出监狱，没有附加条件。但就在那之后的五个月里，维也纳的夜里开始有人失踪。"),
    ("N04", "第二次杀人（一九九〇至一九九一）",
     "一九九〇年十月起，维也纳和格拉茨的性工作者接连消失，遗体被弃在城外林地，至少七个人。警方查了很久，没能找到凶手。一九九一年六月，这名作家受奥地利一家杂志委托飞到洛杉矶，写红灯区系列报道。更离奇的是，他跟着洛杉矶警方出勤，坐在警车里看警方查案。他停留的这几周里，洛杉矶也有三名女性以几乎相同的方式死去。"),
    ("N05", "拼图：两条线索合上了",
     "格拉茨的刑警盯上了他，证据却总差一截；洛杉矶查的案子，手法和奥地利如出一辙。两地警方把资料并在一起：勒具来自被害人自己的衣物，弃尸环境、手法、时间线都能对上。一九九二年二月，逮捕令发出时，他已经带着女友离开奥地利，一路到了美国。二月二十七日，他在迈阿密被捕。"),
    ("N06", "结局：九项谋杀，和最后一次伪装",
     "一九九四年，格拉茨。经过两个月审理，陪审团以六比二认定他九项谋杀罪成立，判处终身监禁、不得假释。审判当夜，他在牢房里结束了自己的生命。他在书里写自己的罪，又用书洗白自己的罪；他让整个社会相信，一个人可以被改造成另一个人。如果那场改变是真的，他为什么还要再杀人？"),
]

# 每一镜：(id, kind, 运镜, 叙事职责, 衔接方式, 英文提示词 或 信息卡说明, 音效/备注)
# kind = "agnes"（AI 动画）或 "graphic"（信息卡；文案写在下面的 CARDS 里）。
# {C1}…{C6} 是 cast.json 里的面容 token 占位符（build() 注入，保证逐字节一致）。
HOLD = ("no cut, no scene change, no camera relocation, no second location, no extra people, "
        "no readable text anywhere in frame; hold on this single view for the full clip.")
SHOTS = [
    # ---------------- N01（8 镜：7 agnes + 1 信息卡）----------------
    ("S01", "agnes", "缓慢前推", "开场：监狱门口的记者与闪光灯",
     "接信息卡：案件名片",
     "The pavement outside a plain stone prison gate on an overcast May morning in 1990: a tight cluster of press"
     "photographers seen strictly from behind and from the side, dark bulky 1980s coats and hats, held-up flash"
     "units firing, chrome and glass of their lenses catching the pale daylight, one heavy shoulder-mounted"
     "television camera on the right; the gate and the wall are bare wet stone carrying no plaque, no number, no"
     "lettering and no notice, and no camera, bag or case in frame carries any marking, label or lettering of any"
     "kind; no faces visible at all, no other people, no vehicles, no signage. Slow push into the cluster of"
     "photographers toward the gate, no cut, no scene change, no camera relocation, no second location, no extra"
     "people, no readable text anywhere in frame; hold on this single view for the full clip." + HOLD,
     "快门声 + 低频冲击"),
    ("S02", "graphic", "信息卡（静帧）", "名片：案件、时间、规模",
     "接 AGNES：书桌与采访话筒",
     "案件名片：案名 / 地点与年代 / 九个谋杀罪名的结局",
     "低音撞击"),
    ("S03", "agnes", "缓慢横移", "名人现场：签书会的一角",
     "接 AGNES：女记者出场（C2 首次出现）",
     "A close view across a café table in Vienna in 1990: a small stack of plain hardback books with completely "
     "blank covers, a fountain pen, a half-empty wine glass, an ashtray with a smoking cigarette, a folded pair "
     "of reading glasses, scattered loose pages lying face down so no writing is legible; warm tungsten light from "
     "an unseen lamp, dark wood table, the room beyond falling away out of focus; no people, no hands, no readable "
     "text, no numbers, no logos anywhere. Slow lateral drift across the table, " + HOLD,
     "纸张与杯碟轻响"),
    ("S04", "agnes", "缓慢前推（中景）", "媒体在追捧他：女记者提问",
     "接 AGNES：监狱大门与走出的人",
     "A tight medium shot inside a 1980s television studio in Vienna, the frame filled corner to corner by the "
     "subject and the equipment: {C2}, seated on a low stool facing a microphone on a stand, leaning slightly "
     "forward with a notebook open in one hand; immediately behind her hangs a heavy dark charcoal wool curtain "
     "whose deep folds fill the whole upper background and every edge of the frame, the fabric perfectly plain "
     "in tone and texture, and a dark blurred boom microphone arm crosses the top corner; there is no wall, no "
     "panel, no board, no paper and no surface carrying any mark, line or number anywhere in frame, and no other "
     "person. Slow push in on her, " + HOLD,
     "演播室底噪 + 提问"),
    ("S05", "agnes", "缓慢跟拍（背影）", "监狱大门打开，一个人走向阳光",
     "接 AGNES：书桌与旧照片",
     "A man in a dark coat, seen strictly from behind at a long distance, walking out through the open steel door "
     "of a plain stone prison into pale overcast daylight: his figure small in the frame, face never visible, one "
     "hand carrying a plain cardboard folder; the gate and the wall are bare with no inscription, no plate and no "
     "lettering, wet asphalt in the foreground, an empty paved forecourt beyond, no people, no vehicles, no "
     "signage. Slow tracking shot following his back away from the gate, " + HOLD,
     "铁门轴声 + 脚步"),
    ("S06", "agnes", "缓慢下移（俯视特写）", "档案：旧照片与放大镜",
     "接 AGNES：屋主本人首次露面（C1）",
     "A top-down close view of a worn desk in a small office: a manila folder open with several old black-and-white "
     "photographs lying face down beside a magnifying glass, a cold cup of coffee and a plain pocket watch without "
     "visible markings, all on bare scratched wood under a single warm desk lamp; no writing, no numbers, no "
     "labels, no people, no hands. Slow overhead descent toward the photographs, " + HOLD,
     "纸张摩擦（SFX paper）"),
    ("S07", "agnes", "缓慢前推（中景）", "主角首次露面：酒吧桌前的作家",
     "接 AGNES：调查室的线索板",
     "A medium shot at a corner table in a dim Viennese bar in 1990: {C1}, seated alone with one elbow on the "
     "table, a glass of white wine and a smoking cigarette in front of him, a plain unmarked notebook closed "
     "under his hand, his gaze lifted calmly toward the camera; behind him only dark panelled wall and the soft "
     "blurred glow of the bar, the room holding no signs, no posters, no lettering, no numbers and no other "
     "people. Slow push in on him, " + HOLD,
     "酒吧人声 + 主题动机首次出现"),
    ("S08", "agnes", "缓慢横摇", "警方在拼图：线索板与红色串线",
     "接 N02：一九七四年的冬天",
     "A slow lateral view of an investigation room wall at night in Vienna: a large cork pinboard covered with "
     "dozens of completely blank white cards joined by lengths of red string, a plain desk lamp on the right "
     "throwing warm light and a long shadow across the board, a half-empty coffee cup on the shelf below; the "
     "cards are entirely blank with no writing, no numbers, no photographs and no printing anywhere, no people "
     "in frame, the rest of the room in darkness. Slow pan across the board, " + HOLD,
     "低频悬念音"),

    # ---------------- N02（7 镜：6 agnes + 1 信息卡）----------------
    ("S09", "agnes", "缓慢前推", "一九七四年冬：一条安静的街",
     "接 AGNES：亮着一盏灯的房间",
     "A narrow cobbled street between plain plastered house fronts in a small Austrian town at dusk in December"
     "1974: frost on the cobblestones and a thin crust of snow along the kerb, one bare tree, one lit curtained"
     "window on the upper floor, a single black bicycle leaning against a wall; the plaster walls are completely"
     "bare and anonymous with no house numbers, no name plates, no plaques, no signs and no lettering in any form,"
     "the camera is low and tight so that only the street level and the one lit window are in frame, no vehicles,"
     "no people, no sky. Slow push down the street toward the lit window, no cut, no scene change, no camera"
     "relocation, no second location, no extra people, no readable text anywhere in frame; hold on this single"
     "view for the full clip." + HOLD,
     "冬夜的风 + 远处狗吠"),
    ("S10", "agnes", "缓慢下移", "空房间：一个再没有回来的夜晚",
     "接信息卡：第一条人命",
     "A small modest living room in 1974 at night, empty of people: a worn upholstered armchair with a woman's "
     "woollen coat laid over its back, a low table with a black rotary telephone and a cold cup of tea, a standing "
     "lamp switched on and a wall clock with no readable numerals, dark floral wallpaper, one curtained window "
     "reflecting the lamp; no writing, no photographs, no letters, no numbers, no people anywhere. Slow descent "
     "toward the armchair and the coat, " + HOLD,
     "钟摆声 + 静默"),
    ("S11", "graphic", "信息卡（静帧）", "口径：一九七四年十二月 / 十八岁 / 终身监禁",
     "接 AGNES：刑警与卷宗",
     "第一条人命：一九七四年十二月 · 一条街的尽头（公开报道口径）",
     "低音撞击"),
    ("S12", "agnes", "缓慢前推（中景）", "维也纳刑警办案（C4 首次出现）",
     "接 AGNES：法院走廊",
     "A tight medium shot in a small Austrian police office at night in 1976, framed so that only the desk, the "
     "lamp and the investigator are in view: {C4}, seated at a steel desk with a ballpoint pen in his hand, an "
     "open file of blank lined pages in front of him, his coat still on the back of his chair, a green-shaded "
     "desk lamp pooling light across the desk; behind him the room falls away into complete darkness with no "
     "wall surface, no cabinet, no shelf and no object visible at all, and nothing in the frame carries any "
     "lettering, tag or number; no other people. Slow push in on him, " + HOLD,
     "钢笔划纸（SFX paper）"),
    ("S13", "agnes", "缓慢横移", "判决：法院的走廊与空着的被告席",
     "接 AGNES：监狱走廊",
     "An Austrian courthouse corridor in 1976, entirely empty of people, photographed from a very low angle "
     "close to the floor so that the frame is filled edge to edge by the receding row of dark wooden benches "
     "and the worn stone floor: the bench backs and their plank shadow lines lead away toward a closed heavy "
     "door at the far end, cold daylight falling across the floor; the upper walls, windows and doors are "
     "completely outside the frame, and no surface in view carries any notice, plaque, lettering or number; "
     "no people, no furniture other than the benches. Slow lateral drift low along the benches, " + HOLD,
     "法槌回响 + 走廊回声"),
    ("S14", "agnes", "缓慢后拉", "牢门一扇扇关上",
     "接 AGNES：牢房里的写字台",
     "A long prison wing corridor in 1976 filmed from a low angle, empty of people: a receding row of heavy steel"
     "cell doors on the left, framed close along the wall so that nothing is legible anywhere, every door a plain"
     "unmarked slab carrying no number, no plate, no lettering and no figure on any fitting, a bare bulb and a"
     "high narrow window at the far end throwing a dusty shaft of light down the corridor, worn grey stone floor;"
     "no people, no furniture, no markings. Slow pull back down the corridor, no cut, no scene change, no camera"
     "relocation, no second location, no extra people, no readable text anywhere in frame; hold on this single"
     "view for the full clip." + HOLD,
     "铁门连环关闭 + 低沉低频"),
    ("S15", "agnes", "缓慢前推（特写）", "牢房里的写字台：一支笔和一摞稿纸",
     "接 N03：他开始写作",
     "A single bare prison cell in 1980 seen from the doorway, empty of people: a small steel table pushed against "
     "the wall with a battered manual typewriter, a stack of blank pages, two pencils, a tin mug and an ashtray, "
     "a narrow iron bed with a folded grey blanket behind it, one high barred window with flat daylight; the walls "
     "are bare with no posters, no photographs, no scratches, no writing and no numbers anywhere; no people in "
     "frame. Slow push in toward the table, " + HOLD,
     "打字机键声（SFX machine）"),

    # ---------------- N03（8 镜：7 agnes + 1 信息卡）----------------
    ("S16", "agnes", "缓慢前推（特写）", "写作的人：牢房夜灯下的那张脸",
     "接 AGNES：稿纸与钢笔",
     "An intimate close shot inside a dim prison cell at night in 1985, framed so that only four things are in "
     "view: {C1}, seated at a small table with his forearms resting on a stack of blank pages, a cigarette "
     "burning in a tin ashtray beside a glass of water, and the corner of the rough wooden tabletop; the whole "
     "background behind him is out of focus and out of frame, falling into unlit darkness with no wall, no "
     "plaster, no window and no surface visible at all, and nothing in the frame carries any lettering, mark, "
     "plate or number; no other people. Slow push in on his face, " + HOLD,
     "笔尖与纸 + 低频"),
    ("S17", "agnes", "缓慢横移（特写）", "书是怎么写出来的：桌上一摞稿纸",
     "接 AGNES：编辑读稿（C3 首次出现）",
     "A close view across a worn table in a prison cell at night: a thick stack of manuscript pages lying at a low "
     "oblique angle so that every line on them is blurred beyond reading, a fountain pen laid across the top "
     "sheet, a pair of reading glasses and a glass of water; warm tungsten light from one side, deep shadow "
     "behind; no legible writing, no numbers, no printed text, no hands, no people. Slow lateral drift across the "
     "pages, " + HOLD,
     "翻页声（SFX paper）"),
    ("S18", "graphic", "信息卡（静帧）", "口径：出书 / 请愿 / 被当成改造成功的样本",
     "接 AGNES：电视演播室里的采访",
     "他成了改造成功的样本：狱中出书 · 剧本 · 自传《炼狱》（公开报道口径）",
     "低音撞击"),
    ("S19", "agnes", "缓慢前推（中景）", "他也上了电视：演播室里的女记者",
     "接 AGNES：讲座现场",
     "A medium shot inside a television studio in Vienna in 1989: {C2}, standing beside a heavy studio camera whose "
     "operator is visible only as a dark shoulder and back in the extreme foreground, her notebook raised as she "
     "turns slightly toward an off-screen guest; the backdrop is a seamless dark grey cyclorama with no logos, no "
     "lettering, no numbers, and the studio is otherwise empty. Slow push in on her, " + HOLD,
     "演播室空调底噪"),
    ("S20", "agnes", "缓慢横移（中景）", "讲座现场：被当成\"改造成功\"的样本",
     "接 AGNES：图书馆",
     "A medium shot at a literary evening in a Vienna lecture hall in 1989: {C1}, standing behind a plain wooden "
     "lectern with one hand resting flat on an open book, lit by a warm stage light while the first rows of the "
     "audience below the lectern are visible only as dark blurred shoulders and the backs of heads, no faces; the "
     "back wall is bare with no banners, no lettering, no numbers and no signage of any kind. Slow lateral drift "
     "around him, " + HOLD,
     "会场呼吸声 + 掌声余音"),
    ("S21", "agnes", "缓慢前推（中景）", "文学界替他背书：老编辑读完那本书",
     "接 AGNES：夜场酒吧与女招待（C6 首次出现）",
     "A medium shot in a book-lined publishing office in Vienna in 1988: {C3}, seated in a leather armchair with a "
     "thick manuscript open on his knees, his spectacles pushed up on his forehead, a reading lamp behind his "
     "shoulder and a glass on the side table; the book spines on the shelves behind him are entirely blank with no "
     "titles, no names, no numbers and no lettering of any kind; no other people, no windows, no signage. Slow push "
     "in on him, " + HOLD,
     "翻稿声 + 老式挂钟"),
    ("S22", "agnes", "缓慢前推（中景）", "夜的另一面：酒吧里的女招待",
     "接 AGNES：监狱大门再次打开",
     "A tight medium shot behind the counter of a small Viennese night bar in 1990, framed so that the counter "
     "and her upper body fill the frame: {C6}, leaning with both hands on the counter, a damp cloth in one hand, "
     "a towel over her shoulder, looking off toward the door with a tired level gaze; a single warm pendant "
     "lamp hangs just above her, and everything behind her is thrown far out of focus into soft warm bokeh with "
     "no shelf, no bottle, no cabinet and no wall surface readable anywhere; no labels, no lettering, no numbers, "
     "no other people in frame. Slow push in on her, " + HOLD,
     "夜场音乐低沉 + 玻璃杯轻碰"),
    ("S23", "agnes", "缓慢后拉（背影）", "一九九〇年五月：他走出监狱",
     "接 N04：黑色轿车与司机",
     "A man in a light summer coat, seen strictly from behind at a distance, walking away through the open "
     "gateway of a plain stone prison on a bright May morning in 1990: the camera is low and inside the "
     "gateway, so the frame is filled by the two stone doorposts on either side, the sunlit cobbled street "
     "beyond and his back small in the bright opening with a plain cardboard folder in one hand; the lintel "
     "above the gate and every wall surface are completely outside the frame, and nothing in view carries any "
     "inscription, plate or number; no vehicles, no people, no signage. Slow pull back and up as he walks away, "
     + HOLD,
     "铁门关闭 + 城市底噪"),
    ("S24", "graphic", "信息卡（静帧）", "口径：假释之后 / 同年十月起开始有人失踪",
     "接 AGNES：洛杉矶警探的桌子（C5 首次出现）",
     "一九九〇年五月：假释出狱 · 无附加条件；同年十月起，维也纳开始有人失踪（公开报道口径）",
     "低音撞击"),
    ("S25", "agnes", "缓慢下移（中景）", "跨洲的案子：洛杉矶女警探的办公桌",
     "接 AGNES：雨夜的洛杉矶街道",
     "A medium shot in a Los Angeles police office at night in 1991: {C5}, seated at a cluttered desk with a "
     "telephone handset pressed to her ear, her blazer slung over the chair back, an open notebook of blank pages "
     "and a half-eaten takeaway carton in front of her, blinds behind her throwing slatted shadow across the wall; "
     "every object on the desk is unmarked with no writing, no numbers, no labels and no printed text, no other "
     "people, no signage. Slow descent toward her, " + HOLD,
     "电话拨号 + 打字机远响"),
    ("S26", "agnes", "缓慢横摇", "洛杉矶：雨夜里的警戒带",
     "接 AGNES：机场里的采访笔记",
     "An empty side street in Los Angeles at night in 1991 under light rain: wet asphalt mirroring a single sodium"
     "street light and the alternating red and blue wash of patrol lights from off-screen, a length of plain"
     "barrier tape strung between two posts, weeds cracking the kerb, a blank featureless concrete wall behind,"
     "bare from edge to edge; no graffiti, no posters, no bills, no signs, no lettering and no numbers anywhere,"
     "no vehicles, no people, no bodies. Slow pan across the tape and the wet asphalt, no cut, no scene change, no"
     "camera relocation, no second location, no extra people, no readable text anywhere in frame; hold on this"
     "single view for the full clip." + HOLD,
     "雨声 + 远处警笛"),
    ("S27", "agnes", "缓慢前推（中景）", "他就在现场：机场候机厅里的回头",
     "接 AGNES：洛杉矶警探的线索板",
     "A medium shot in a bright airport departure lounge in 1991: {C1}, seated in a moulded plastic chair with a"
     "plain unmarked notebook open on his knee and a small flight bag at his feet, twisting his upper body to look"
     "back over his shoulder toward the camera with a flat appraising expression; behind him only a long row of"
     "empty chairs and a floor-to-ceiling window of pale grey light, no counters, no desks, no screens, no"
     "monitors, no panels, no lettering, no numbers and no other people in frame. Slow push in on him, no cut, no"
     "scene change, no camera relocation, no second location, no extra people, no readable text anywhere in frame;"
     "hold on this single view for the full clip." + HOLD,
     "机场广播低鸣（含糊） + 低频"),
    ("S28", "agnes", "缓慢前推（中景）", "另一头：证据板前站着的人",
     "接 AGNES：舷窗外的机身",
     "A medium shot in a Los Angeles police briefing room at night in 1991: {C5}, standing sideways on to a large "
     "pinboard, one hand pinning a completely blank white card to it, her head turned down toward a folder held in "
     "the other arm; the cards already on the board are all blank with no writing, no photographs, no numbers and "
     "no printing, a single overhead lamp lighting her from the front; no other people, no signage, no lettering "
     "anywhere in frame. Slow push in on her, " + HOLD,
     "图钉声（SFX press）"),
    ("S29", "agnes", "缓慢横摇", "飞越大西洋：停机坪上的机身",
     "接 AGNES：押送与手铐",
     "A wide view of an aircraft on an airport apron at dusk in 1992: the fuselage completely plain and white with "
     "no airline name, no logo, no lettering and no registration number anywhere on it, one jet bridge in shadow, "
     "wet concrete reflecting the last cold daylight, heat shimmer along the tarmac; no people, no vehicles, no "
     "signage, no flight information boards. Slow lateral pan along the fuselage, " + HOLD,
     "喷气引擎低鸣 + 风声"),
    ("S30", "agnes", "缓慢跟拍（背影）", "八月：他被押送着走出门",
     "接 N05：并案的桌面",
     "A medium shot in a plain corridor in 1992: {C1}, walking toward the camera in the middle of the corridor "
     "with his hands held together in front of his waist, a dark jacket over his shoulders, his expression level "
     "and composed; two uniformed officers flank him and are visible only from behind as dark blurred silhouettes "
     "at the edge of frame with completely blank uniforms carrying no badges, no insignia, no numbers and no "
     "lettering; the corridor walls are bare, no signage, no posters. Slow tracking shot ahead of him, " + HOLD,
     "脚步回声 + 低频"),
]
SHOTS += [
    # ---------------- N05（8 镜：7 agnes + 1 信息卡）----------------
    ("S31", "graphic", "信息卡（静帧）", "口径：两次杀人之间的空档与并案",
     "接 AGNES：档案柜前的维也纳刑警",
     "并案：一九九〇至一九九一 · 维也纳与格拉茨（公开报道口径）",
     "低音撞击"),
    ("S32", "agnes", "缓慢下移（中景）", "维也纳刑警重新翻旧卷",
     "接 AGNES：洛杉矶的打字机",
     "A medium shot in a records room in Vienna at night in 1992: {C4}, standing at an open steel drawer with one"
     "hand lifting out a thick folder of blank pages, dust hanging in the beam of a work lamp, his overcoat still"
     "on; the drawer and the cabinet fronts are plain steel with no label holders, no plates, no numbers and no"
     "lettering of any kind, the papers in his hand are blank, the wall behind is bare grey with nothing mounted"
     "on it; no other people, no windows. Slow descent toward the drawer, no cut, no scene change, no camera"
     "relocation, no second location, no extra people, no readable text anywhere in frame; hold on this single"
     "view for the full clip." + HOLD,
     "抽屉滑轨 + 纸张（SFX paper）"),
    ("S33", "agnes", "缓慢前推（中景）", "跨洲并案的现场：打字机与证物袋",
     "接 AGNES：夜里的酒店书桌",
     "A medium shot in a Los Angeles police office at night in 1992: {C5}, seated at a heavy manual typewriter"
     "with both hands on the keys and a blank sheet in the machine, a telephone handset lying off the hook beside"
     "it, two folded paper evidence bags and a desk lamp on the table; the wall behind her is plain and empty with"
     "no framed notices, no plates, no numbers, no clock and no lettering anywhere, and the machine and every page"
     "are blank; no other people, no signage. Slow push in on her, no cut, no scene change, no camera relocation,"
     "no second location, no extra people, no readable text anywhere in frame; hold on this single view for the"
     "full clip." + HOLD,
     "打字机键声（SFX machine）"),
    ("S34", "agnes", "缓慢前推（特写）", "逃亡途中：酒店房间里的那盏台灯",
     "接 AGNES：林地的清晨",
     "An intimate close shot in a modest hotel room at night in 1992, framed so that only his head and shoulders, "
     "the telephone and the edge of a plain unpatterned curtain are in view: {C1}, seated with a telephone "
     "handset held against his ear, lit from one side by a bedside lamp that stands just outside the frame; the "
     "wallpaper, the bed, the luggage rack and the far side of the room are all outside the frame, and the "
     "curtain fabric is smooth, plain and free of any pattern, figure or mark; nothing in the frame carries "
     "lettering, numbers or printed marks, and no other person is present. Slow push in on him, " + HOLD,
     "拨号音 + 窗外雨"),
    ("S35", "agnes", "缓慢横移（远景）", "林地的清晨：没有人的现场",
     "接 AGNES：迈阿密的羁押室",
     "A wide view of a bare deciduous woodland path outside Vienna at grey dawn in 1992, empty of people: wet brown "
     "leaves and thin mist between tall bare trunks, a length of plain unmarked barrier tape strung between two "
     "trees, a narrow trodden path leading away into the fog, soft cold light with no sun; no lettering, no "
     "numbers, no signage, no vehicles, no people, no bodies, no blood. Slow lateral drift along the treeline, " +
     HOLD,
     "风穿过树林 + 低频"),
    ("S36", "agnes", "缓慢前推（中景）", "迈阿密：羁押室里的那张脸",
     "接信息卡：一九九二年二月",
     "A medium shot in a plain bright holding room in Florida in February 1992: {C1}, seated on a fixed steel"
     "chair leaning slightly forward with his elbows on his knees, wearing a plain grey sweatshirt, lit by hard"
     "even daylight from a high window; the walls behind him are blank painted concrete with no numerals, no"
     "markings, no notices, no plates and no lettering of any kind, there is no table in frame and no other"
     "people. Slow push in on him, no cut, no scene change, no camera relocation, no second location, no extra"
     "people, no readable text anywhere in frame; hold on this single view for the full clip." + HOLD,
     "空调低鸣 + 静默"),
    ("S37", "graphic", "信息卡（静帧）", "口径：一九九二年二月二十七日 · 迈阿密",
     "接 AGNES：夜班新闻编辑部",
     "被捕：一九九二年二月二十七日 · 迈阿密（跨洲追捕的终点）",
     "低音撞击"),
    ("S38", "agnes", "缓慢前推（中景）", "夜里的编辑部：女记者打电话",
     "接 N06：格拉茨的法院",
     "A medium shot in a night newsroom in Vienna in 1992: {C2}, seated at a cluttered desk with a black telephone "
     "handset pressed to her ear and a pen in her other hand, the sleeves of her blouse pushed up, a desk lamp and "
     "a wall of dark windows behind her; the papers on the desk are all blank with no writing, no numbers, no "
     "printed text, the computer screen behind her is dark and switched off, no other people in frame, no signage, "
     "no lettering. Slow push in on her, " + HOLD,
     "电话铃声（SFX phone）"),

    # ---------------- N06（7 镜：6 agnes + 1 信息卡）----------------
    ("S39", "agnes", "缓慢前推", "格拉茨：开庭前的石头台阶",
     "接信息卡：九项谋杀",
     "The stone steps and heavy wooden entrance doors of a plain Austrian public building at grey dawn in 1994:"
     "wet steps, iron handrails, one lamp still burning above the door, thick mist hiding the upper storeys and"
     "the neighbouring buildings; the facade is bare stone with no notice boards, no plaques, no name plates, no"
     "numbers and no lettering of any kind anywhere, no people, no vehicles, no signage. Slow push up the steps"
     "toward the doors, no cut, no scene change, no camera relocation, no second location, no extra people, no"
     "readable text anywhere in frame; hold on this single view for the full clip." + HOLD,
     "低频弦乐 + 远处快门"),
    ("S40", "graphic", "信息卡（静帧）", "口径：九项谋杀成立 · 六比二",
     "接 AGNES：被告席上的那张脸",
     "判决：一九九四年六月二十八日 · 九项谋杀罪成立（六比二）",
     "法槌（SFX press）"),
    ("S41", "agnes", "缓慢前推（中景）", "被告席上：最后一次露出的那张脸",
     "接 AGNES：清晨的空牢房",
     "A medium shot inside an Austrian courtroom in June 1994: {C1}, standing behind a plain wooden rail in the"
     "dock with his hands resting on it, wearing a dark suit and open white shirt, his expression flat and"
     "composed as he looks directly toward the camera; he is lit tightly against a plain panelled wall with no"
     "plaques, no framed documents, no crests, no emblems, no lettering and no numbers, and the courtroom beyond"
     "falls away into shadow and out of focus with nobody visible; no other people in frame. Slow push in on him,"
     "no cut, no scene change, no camera relocation, no second location, no extra people, no readable text"
     "anywhere in frame; hold on this single view for the full clip." + HOLD,
     "法庭静默 + 低频"),
    ("S42", "agnes", "缓慢下移", "宣判后的清晨：空牢房里的写字台",
     "接 AGNES：编辑部里合上的那本书",
     "A single bare cell in an Austrian prison at grey dawn in June 1994, empty of people: a steel table with a"
     "closed notebook, a pen laid precisely parallel to its edge, a tin mug and a folded grey blanket on the"
     "narrow bed, one high window with cold flat light and long shadows; the walls are blank smooth plaster with"
     "no numerals, no marks, no writing and no fittings, and the window in the lit part of the frame is plain; no"
     "people in frame, no other objects. Slow descent toward the table, no cut, no scene change, no camera"
     "relocation, no second location, no extra people, no readable text anywhere in frame; hold on this single"
     "view for the full clip." + HOLD,
     "铁窗风 + 静默"),
    ("S43", "agnes", "缓慢前推（中景）", "文学界的沉默：编辑部里合上的书",
     "接 AGNES：桌上合起的书",
     "A medium shot in a book-lined publishing office in Vienna in 1994: {C3}, seated in his leather armchair with "
     "a thick book closed on his knees and one hand resting flat on the cover, his head lowered, the reading lamp "
     "still burning behind him; the spines on the shelves are all blank with no titles, no names, no numbers and "
     "no lettering of any kind, the room is otherwise empty, no windows in frame, no signage. Slow push in on him, "
     + HOLD,
     "合书声（SFX paper） + 挂钟"),
    ("S44", "agnes", "缓慢前推（特写）", "桌上合起的书：一段被写出来的历史",
     "接 AGNES：关上的牢门",
     "A close view of a plain deep-red cloth-bound book lying closed on a dark wooden desk in a dim room, no dust "
     "jacket, no title, no lettering, no embossing and no printed marks on the cover or the spine, a reading lamp "
     "just out of frame throwing warm light across the cloth texture, everything beyond the book falling into "
     "black; no hands, no people, no other objects. Very slow push in on the closed book, " + HOLD,
     "翻书声渐渐消失 + 低频"),
    ("S45", "agnes", "缓慢后拉（远景）", "结尾：一扇终于关上的牢门",
     "接片尾卡",
     "The end of a bare prison corridor at night in 1994, empty of people: one heavy steel cell door standing"
     "slightly open at the far end with a blade of warm light escaping across the worn stone floor, the wall lamp"
     "above it the only light; the walls and doors are blank and unmarked with no numbers, no plates, no lettering"
     "and no fixtures, the corridor photographed wide and dim; no people, no furniture. Very slow pull back down"
     "the corridor as the door settles shut, no cut, no scene change, no camera relocation, no second location, no"
     "extra people, no readable text anywhere in frame; hold on this single view for the full clip." + HOLD,
     "铁门关闭声 + 黑场"),
]

# ---------------------------------------------------------------------------
# 画面上的文字（render.py 从 story.json 的 presentation 块读，不在 render.py 里写死）
# ---------------------------------------------------------------------------
CARD_HEADER = "案件档案  /  奥地利 · 一九七四至一九九四"        # 每张信息卡左上角的小字
CARD_FOOTER = "公开报道口径 · 并非原始档案影像"                  # 每张信息卡左下角的小字
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S02": ("最成功的一次伪装", "奥地利 · 一九七四至一九九四", "九年写出名声 · 九项谋杀罪名"),
    "S11": ("第一条人命", "一九七四年十二月 · 奥地利", "一条街的尽头 · 十八岁"),
    "S18": ("他成了\"改造成功\"的样本", "狱中出书 · 剧本 · 自传《炼狱》", "作家与艺术家联名请愿"),
    "S24": ("一九九〇年五月", "假释出狱 · 无附加条件", "同年十月起 · 维也纳开始有人失踪"),
    "S31": ("并案", "一九九〇至一九九一 · 维也纳 与 格拉茨", "相同的手法 · 相同的弃尸环境"),
    "S37": ("被捕", "一九九二年二月二十七日 · 迈阿密", "跨洲追捕 · 终点在一间公寓"),
    "S40": ("判决", "一九九四年六月二十八日 · 格拉茨", "九项谋杀罪成立 · 六比二"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["杰克·翁特维格", "最成功的一次伪装 · 一九七四至一九九四 奥地利"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "那场改变，是真的吗？",
    "杰克·翁特维格 · 一九七四至一九九四 · 九项谋杀罪成立",
    "他让人相信一个人可以被改造成另一个人。",
    "资料：卫报 / 纽约时报 / 奥地利公开报道 · 原创解说 · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词）
CAPTION_KEYWORDS = [
    "一九九〇年五月二十三日", "杀人犯", "假释",
    "一九七四年十二月", "十六次", "终身监禁",
    "《炼狱》", "联名替他请愿", "五个月",
    "至少七个人", "洛杉矶", "三名女性",
    "并在一起", "一九九二年二月", "迈阿密",
    "九项谋杀罪", "六比二", "改造成另一个人",
]
# 逐镜标签覆盖：默认 agnes 镜头标「AI动画情景重现 · 非新闻影像」，庭审/监狱/警方镜头写得更具体
LABEL_OVERRIDES = {
    "S01": "AI动画情景重现 · 非新闻采访影像",
    "S04": "AI动画情景重现 · 非新闻采访影像",
    "S05": "AI动画情景重现 · 非监狱实景",
    "S08": "AI动画情景重现 · 非警方办案影像",
    "S12": "AI动画情景重现 · 非警方办案影像",
    "S13": "AI动画情景重现 · 非法院实景",
    "S14": "AI动画情景重现 · 非监狱实景",
    "S15": "AI动画情景重现 · 非监狱实景",
    "S16": "AI动画情景重现 · 非监狱实景",
    "S19": "AI动画情景重现 · 非新闻采访影像",
    "S20": "AI动画情景重现 · 非新闻影像",
    "S22": "AI动画情景重现 · 非新闻影像",
    "S23": "AI动画情景重现 · 非监狱实景",
    "S25": "AI动画情景重现 · 非警方办案影像",
    "S26": "AI动画情景重现 · 非现场影像",
    "S28": "AI动画情景重现 · 非警方办案影像",
    "S30": "AI动画情景重现 · 非抓捕现场影像",
    "S32": "AI动画情景重现 · 非警方取证影像",
    "S33": "AI动画情景重现 · 非警方办案影像",
    "S35": "AI动画示意 · 非现场影像",
    "S36": "AI动画情景重现 · 非羁押实景",
    "S38": "AI动画情景重现 · 非新闻采访影像",
    "S39": "AI动画情景重现 · 非法院实景",
    "S41": "AI动画示意 · 非庭审影像",
    "S42": "AI动画情景重现 · 非监狱实景",
    "S43": "AI动画情景重现 · 非新闻影像",
    "S45": "AI动画情景重现 · 非监狱实景",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S06", "paper"),
    ("S08", "press"),
    ("S11", "paper"),
    ("S12", "paper"),
    ("S15", "machine"),
    ("S17", "paper"),
    ("S18", "paper"),
    ("S21", "keys"),
    ("S25", "phone"),
    ("S28", "press"),
    ("S32", "paper"),
    ("S33", "machine"),
    ("S38", "phone"),
    ("S40", "press"),
    ("S43", "paper"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "他坐牢时写的书成了教材，出狱三年后被判九个谋杀罪｜杰克·翁特维格案",
    "奥地利最出名的\"改造成功\"案例：作家、电视名人，和九条人命",
    "他一边写报道一边杀人：跟着警察出勤的连环杀手｜杰克·翁特维格",
]
HOOK = "一九九〇年五月，奥地利杀人犯杰克·翁特维格假释出狱，出书、上电视，被当成\"改造成功\"的样本；三年后，他因九项谋杀罪被判处终身监禁。"
GOLDEN_LINES = [
    "他让人相信一个人可以被改造成另一个人；可那场改变，也许从一开始就是伪装。",
    "他在书里写自己的罪，又用书洗白自己的罪。",
    "如果那场改变是真的，他为什么还要再杀人？评论区聊聊。",
]
DESCRIPTION = (
    "一九七四年，奥地利一名十八岁女孩被勒死；凶手被判终身监禁，却在狱中出书成名，被当成\"改造成功\"的样本，一九九〇年假释。"
    "出狱后五个月起，维也纳与格拉茨接连有人失踪；一九九一年他受杂志委托去洛杉矶写红灯区报道，还随当地警方出勤，"
    "那几周洛杉矶也有三名女性遇害。一九九二年他在迈阿密被捕，一九九四年六月九项谋杀罪成立，判决当夜自杀。"
    "本片画面为 AI 生成的情景重现（非新闻影像），事实依据公开报道整理。"
)
QUESTION = "你相信有\"改造成功\"这回事吗？"
HASHTAGS = ["#悬疑", "#真实案件", "#奥地利", "#翁特维格", "#案件解说"]

GRID = 4           # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 7  # 每个 Agnes 镜头实际请求的时长（169 帧 @ 24 fps）
SEED_BASE = 19900523  # 假释出狱的日子（一九九〇年五月二十三日），让 seed 可追溯

# 露脸镜头登记（镜头号 -> 角色 id）：只有这里登记的镜头允许出现面容 token，
# 与 cast.json 的 shots 映射一一对应（face_cast.py check-prompts 两边都查）。
FACE_SHOTS = {
    "S04": ["C2"],
    "S07": ["C1"],
    "S12": ["C4"],
    "S16": ["C1"],
    "S19": ["C2"],
    "S21": ["C3"],
    "S20": ["C1"],
    "S22": ["C6"],
    "S25": ["C5"],
    "S27": ["C1"],
    "S28": ["C5"],
    "S30": ["C1"],
    "S32": ["C4"],
    "S33": ["C5"],
    "S34": ["C1"],
    "S36": ["C1"],
    "S38": ["C2"],
    "S41": ["C1"],
    "S43": ["C3"],
}
# 用定妆照做首帧（图生视频）的镜头：每个角色的首次露脸镜头，把这张脸钉在观众第一眼里。
# 定妆照提交在仓库里，URL 取 cast.json 的 portrait_url（Agnes 只在服务器侧取图）。
REFERENCE_SHOTS = {"S04": "C2", "S07": "C1", "S12": "C4", "S21": "C3", "S22": "C6", "S25": "C5"}


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

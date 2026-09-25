#!/usr/bin/env python3
"""《金州杀手：家谱里的名字》的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
样板是 production/gilgo/build_story.py 与 production/btk/build_story.py）。

用法::

    python3 production/gsk/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/gsk/build_story.py --script   # 生成 抖音脚本.md
    python3 production/gsk/build_story.py --publish  # 生成 抖音发布文案.md
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"

TITLE = "金州杀手：家谱里的名字"

STYLE_PREFIX = (
    "Stylized 2D animated documentary illustration with hand-painted graphic-novel textures and soft "
    "cel shading; California from the mid-1970s to 2020: flat Sacramento suburbs with ranch houses and "
    "porch lights, orange groves at night, small-town police station, cold-case evidence room, DNA lab "
    "bench, university auditorium and prison wall at dusk; horizontal 16:9 cinematic composition, muted "
    "palette of dusty gold, slate blue and sodium-orange practical light, restrained procedural "
    "true-crime mood, no horror excess; every character is shown only from behind, in silhouette, or as "
    "hands and props - never a clear frontal face; absolutely no readable text, letters, numbers, logos, "
    "license plates or brand marks anywhere inside the frame; one single continuous smooth slow camera move "
    "per shot exactly as directed. "
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

PRINCIPLES = [
    "全部 Agnes 镜头为风格化 2D 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，不冒充庭审、监控或证物照片",
    "不展示遗体、血腥或侵害过程；不重现可模仿的作案步骤（踩点、断线、入室、捆绑），犯案之夜只用空场景与象征物表达",
    "真实人物只以背影、剪影、手部出现，不用 AI 生成的脸冒充本人；真实人物只允许使用有出处的档案照片",
    "受害者不以任何人像出现，只用信息卡与象征物致意（咖啡杯、打字机、空椅）",
    "每一句事实都能指到 sources 里的一条公开报道；未定论的事只写「指控/承认」不写「判决」",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写；家谱图只画空白框线，不画名字",
    "同一地点保留光线、道具、运动方向；跨地点通过声音桥与物件匹配衔接",
    "人工检视 qa/ 接触表，露脸、畸变、伪文字、中途换场的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

SOURCES = [
    {"id": 1, "url": "https://abcnews.com/US/inside-timeline-crimes-golden-state-killer/story?id=54744307",
     "usage": "时间线：2018-04 逮捕（首个遗传家谱学公开逮捕）、纸巾丢弃DNA、审讯室自语、2020-06-29 认罪13项一级谋杀、2020-08-21 终身监禁。"},
    {"id": 2, "url": "https://abc7.com/post/golden-state-killer-joseph-deangelo-timeline-caught/7515045/",
     "usage": "丢弃DNA回填家谱数据库比对命中；认罪换取免死；无假释终身监禁。"},
    {"id": 3, "url": "https://www.biography.com/crime/golden-state-killer",
     "usage": "背景：1945年生、前加州警员；2001年DNA并案；Michelle McNamara 命名「Golden State Killer」；强奸罪过追诉期未起诉；26项指控认罪。"},
    {"id": 4, "url": "https://people.com/where-is-the-golden-state-killer-now-joseph-james-deangelo-11719681",
     "usage": "规模：13名已知谋杀受害者、至少45名强奸受害者、120+起入室；受害者姓名与年龄；最后已知受害者 Janelle Cruz（1986）；North Kern 监狱服刑。"},
    {"id": 5, "url": "https://www.bbc.com/news/election-us-2020-53828154",
     "usage": "量刑：11个连续无假释终身+15个可假释终身+加刑8年；大学礼堂量刑庭；家谱追溯到1800年代；87名受害者53个现场11个县；受害人陈述。"},
]

CHAPTERS = [
    ("N01", "四十年的冷案", "一个当过警察的人，用自己熟悉的反侦查手法犯案、躲避侦查十多年。上世纪七十年代的加州，五十多户人家、十三条人命，先后系在同一人身上。案件冷了三十年，最终指认他的，既不是指纹也不是口供，而是一棵远亲画出来的家谱树，和他随手丢掉的一张纸巾。金州杀手案，今天从那棵家谱讲起。"),
    ("N02", "警察的两面", "他叫约瑟夫·德安杰洛，一九四五年生，越战退伍军人，七十年代中期当上加州小镇警察，早先在埃克塞特任警。同事眼里他守规矩、爱摆弄机器；可夜里他会提前踩点，趁一家人熟睡潜入，几乎不留指纹，只拿走小物件当「战利品」。一九七六年起，萨克拉门托周边几十户人家接连受害，媒体叫他东区强奸犯，警方却迟迟没有嫌疑人。"),
    ("N03", "从北到南", "一九七八年起，案件升级成命案，最先丧命的是马焦雷夫妇。年轻情侣、护女心切的父亲、作家夫妇，接连遇害。凶手南下，在南加州又多了一个名字：原始夜行者。最后一名已知受害者，是一九八六年十八岁的贾内尔·克鲁兹。案子都集中在安静街区，手法如出一辙。然后他突然沉默，调查陷入漫长冷案。"),
    ("N04", "名字与冷案", "二零零一年，DNA比对确认南北两串案子是同一人所为。犯罪写作人米歇尔·麦克纳马拉在书里给他命名金州杀手，逐字追查这起冷案，直到她去世。书名《我在黑暗中》，二零一八年出版即成畅销书，让冷案重新回到公众视野，警方也把悬赏提高到五万美元，重新大规模复查。"),
    ("N05", "家谱长出来了", "二零一七年底，调查员把凶手DNA上传到公开家谱数据库。家谱专家芭芭拉·雷文特画出追溯到十九世纪的庞大家谱，按年龄和居住地一层层收窄。德安杰洛浮出水面。这是全球头一回靠公开家谱数据锁定嫌疑人。警察跟踪他几天，捡起他丢掉的一张纸巾，DNA对上了。二零一八年四月二十四日，七十二岁的德安杰洛被捕。他在审讯室自语：是我，我毁了那些人生。"),
    ("N06", "认罪与终身", "二零二零年六月，德安杰洛为免死刑，承认十三项一级谋杀，死刑由此退出选项。八月量刑那天，幸存者和受害者家属坐满大学礼堂，逐一讲述一生的伤疤。法庭判他十一个连续无假释终身监禁，他那年七十四岁。答案不是天才顿悟：是家谱、纸巾，和四十年不放弃的人。你觉得最致命的，是数据库里的家谱，还是那张纸巾？评论区说说。"),
]

# 45 镜 = 38 agnes + 7 graphic（S04/S08/S13/S20/S27/S33/S41）
SHOTS = [
    # ---------------- N01 ----------------
    ("S01", "agnes", "航拍缓慢前移 aerial drift", "钩子：七十年代加州郊区夜街，一盏门廊灯，安静得反常", "门廊灯溶到家谱纸",
     "Wide night view over a flat 1970s Sacramento suburb: low ranch houses, one porch light glowing, dark tree-lined street, overcast slate sky. No people, no cars, no signs. Slow steady forward aerial drift, one continuous shot.",
     "夜虫声，低频脉冲起"),
    ("S02", "agnes", "微距横移 macro slide", "象征：空白家谱树（只有框线没有名字），一支铅笔", "铅笔尖切纸巾",
     "Macro view of a hand-drawn genealogy chart on aged paper: only empty rectangular boxes connected by thin ink lines, absolutely no names, letters or numbers; a plain pencil rests beside it under a warm desk lamp. Slow lateral slide across the blank boxes, one tabletop only.",
     "纸面摩擦声"),
    ("S03", "agnes", "低机位推近 low dolly", "象征：凌晨路缘的垃圾桶旁一张被丢弃的纸巾", "纸巾白切警徽金属光",
     "Low-angle night view of a suburban curb: one unmarked metal trash can and a single crumpled white tissue on the pavement under a sodium street light, wet asphalt reflections. No people, no text. Slow low dolly toward the tissue, one continuous street.",
     "远处风声，一声金属轻响"),
    ("S04", "graphic", "信息卡 static card", "案件名片：案名、地点年代、规模", "卡片落点切警局",
     "案件名片：金州杀手 / 加州 1976-1986 / 规模三行", "卡片低音敲击"),
    ("S05", "agnes", "缓慢横移 slow pan", "双面人生：黄昏小镇警局门口，一名警员背影走入", "背影过门切工作台",
     "Dusk exterior of a small 1970s California police station: a uniformed officer seen only from behind walks through the doorway, one plain unmarked patrol car parked, flat parking lot, no readable signs or plates. Slow pan holding the doorway, one location.",
     "门簧声，无线电低噪"),
    ("S06", "agnes", "固定微距 macro static", "象征：工作台上擦手电与无线电的手（只拍手部）", "手电光切暗窗",
     "Macro still life on a workbench: gloved-free hands of a man seen from behind the shoulder polishing an old metal flashlight beside a portable radio, tools neatly arranged, warm garage light. Hands only, no face. Locked macro frame, only the flashlight lens glints.",
     "金属擦拭声"),
    ("S07", "agnes", "缓慢拉远 slow pull-back", "犯案之夜只用空场景：一户人家窗灯依次熄灭", "最后一盏灯切时间卡",
     "Night view of one modest ranch house from across the quiet street: window lights turn off one by one until only the porch light remains, bare hedges fill the background, no people, no movement outside. Slow pull-back from the windows to the whole dark facade.",
     "灯开关轻响三下，音乐压暗"),
    ("S08", "graphic", "信息卡 static card", "人物档案：德安杰洛身份三行", "卡片硬切郊区航拍",
     "人物档案：约瑟夫·德安杰洛 / 1945年生 · 越战退伍军人 / 前加州警员", "打字机轻响，姓名处重音"),
    # ---------------- N02 ----------------
    ("S09", "agnes", "航拍下降 descending aerial", "萨克拉门托郊区平面网格，清晨薄雾", "航拍落到门廊报纸",
     "High aerial descending slowly over flat Sacramento suburban grids at misty dawn: identical roofs, quiet streets, a water tower on the horizon, muted gold and slate palette. No people, no readable signs. One continuous descending drift.",
     "风声渐入，远处钟声"),
    ("S10", "agnes", "微距推近 macro push", "象征：门廊上一摞报纸，头版全空白", "报纸边缘切咖啡杯",
     "Macro view of a stack of old newspapers on a wooden porch bench at morning light: every front page completely blank, no headlines, no letters, no photos, only paper grain and folds. Slow push toward the blank top page, one porch only.",
     "纸张翻动声"),
    ("S11", "agnes", "缓慢横移 slow pan", "受害家庭的象征：餐桌上两只咖啡杯与空椅，无人", "杯沿切打字机",
     "A quiet 1970s family dining room: two coffee cups, an empty chair, a folded blanket on the sofa, warm ceiling light, lace curtain moving slightly. No people, no legible writing. Slow pan across the table, one room throughout.",
     "餐具轻碰，音乐转冷"),
    ("S12", "agnes", "固定中景 static medium", "象征：受害者只以物件致意——合上的空白相册", "相册黑封切南加州橘林",
     "Medium still life on a sideboard: one closed photo album with a plain dark cover and no writing, beside a small vase with dried flowers, soft window light. No photos visible, no faces, no text. Locked frame, only dust motes drift in the light.",
     "一声低弦"),
    ("S13", "graphic", "信息卡 static card", "时间线卡：1976-1986 东区→原始夜行者→2001并案", "时间线末端切橘林夜",
     "时间线：1976-1986 / 东区强奸犯 → 原始夜行者 / 2001 DNA并案", "时间轴两端敲击"),
    ("S14", "agnes", "缓慢横移 slow pan", "南加州橘林夜风，树影摇晃，无人", "树影切开窗",
     "Night view inside a Southern California orange grove: rows of dark orange trees swaying in wind, moonlight on leaves, flat horizon, no people, no buildings, no signs. Slow lateral slide along one row, one continuous grove.",
     "树叶风声，夜虫"),
    ("S15", "agnes", "缓慢推近 slow push", "犯案之夜只用空场景：黑暗中一扇开着的窗与摆动窗帘", "窗帘白切书桌",
     "Dark interior of a hallway at night: one open window with a sheer curtain swaying, moonlight stripe on the floor, everything else in shadow. No people, no objects moving besides the curtain. Slow push toward the window, one continuous room.",
     "窗框轻响，低频持续"),
    # ---------------- N03 ----------------
    ("S16", "agnes", "微距横移 macro slide", "象征：作家夫妇的书桌——打字机与空白稿纸", "稿纸白切书页",
     "Macro view of a 1980s writer's desk: a manual typewriter with a completely blank sheet loaded, stacked plain paper, a desk lamp, no letters on the page or machine. Slow slide from the typewriter keys to the blank page, one desk only.",
     "打字机两下轻敲后停"),
    ("S17", "agnes", "缓慢升镜 crane up", "象征：冷案书架上成摞卷宗与未拆封证物盒，标签全空白", "卷宗切实验室",
     "Overhead-to-crane view of a cold-case evidence shelf: stacked old folders and sealed cardboard boxes with completely blank tabs, dust in fluorescent light. No readable labels, no people. Slow crane rise along the shelf, one room.",
     "档案箱落桌声"),
    ("S18", "agnes", "固定远景 static wide", "冷案室长桌：两摞卷宗（北/南）之间拉着一根红线", "红线切DNA移液",
     "Wide locked view of a long cold-case table at night: two neat stacks of blank-tabbed folders joined by a single red string pinned across, one green desk lamp, empty chairs. No people, no text. Only the lamp light subtly breathes.",
     "图钉轻按两声"),
    ("S19", "agnes", "微距推近 macro push", "DNA实验室：移液器滴入样孔排，冷蓝光", "样孔光切屏幕峰线",
     "Macro view of a forensic lab bench in cool blue light: a pipette tip depositing clear drops into a blank well plate, gloved hands only, no labels, no readouts, no text anywhere. Slow push across the plate, one bench only.",
     "滴液轻响，仪器低鸣"),
    ("S20", "graphic", "信息卡 static card", "命名卡：金州杀手 / 麦克纳马拉命名 / 2018出版", "卡片切抽象峰线",
     "命名：Golden State Killer / 米歇尔·麦克纳马拉 命名 / 《我在黑暗中》2018 出版", "书页翻动+卡片敲击"),
    ("S21", "agnes", "固定微距 macro static", "抽象电泳峰线在旧显示器上缓缓滚动，无字无刻度", "峰线溶到家谱纸",
     "Locked macro on an old CRT monitor showing only abstract glowing peak waves scrolling slowly on a dark grid: no letters, no numbers, no scale, no interface text. Nothing else changes in the dim lab.",
     "电子嗡鸣，键盘无声"),
    ("S22", "agnes", "缓慢横移 slow slide", "象征：合上的书与台灯（致麦克纳马拉），书脊无字", "书脊黑切电脑树光",
     "Still life on a home desk at night: one closed hardcover book with a completely blank spine and cover beside a warm reading lamp and a pair of glasses, no writing anywhere. Slow lateral slide across the desk, one room.",
     "一声轻叹式弦乐"),
    ("S23", "agnes", "低机位推近 low dolly", "调查员桌面：旧电脑屏幕只泛抽象树状光斑", "光斑切礼堂空椅？不，切S24监控车",
     "Low dolly toward a detective's desk at night: an old computer monitor glowing with only abstract branching light shapes, no text, a blank notepad and cold coffee beside it, office in shadow. No people. One continuous approach.",
     "硬盘轻响"),
    # ---------------- N04 ----------------
    ("S24", "agnes", "固定远景 static wide", "监视：夜色里一辆无标记轿车停在对街，车内只拍肩背剪影", "车窗反光切垃圾桶",
     "Wide locked view from across a quiet street at night: one unmarked sedan parked under a tree, two silhouette shoulders visible through the windshield, house lights dim, no plates, no signs. Only leaves move.",
     "引擎极低怠速声"),
    ("S25", "agnes", "微距推近 macro push", "象征：戴手套的手从垃圾桶沿夹起一张纸巾", "纸巾白切实验室双管",
     "Macro night view: a gloved hand lifts one crumpled white tissue from the rim of an unmarked trash can with tweezers, sodium light, shallow depth of field. Hand and tissue only, no face. Slow push-in, one continuous motion.",
     "塑料镊轻响"),
    ("S26", "agnes", "缓慢横移 slow pan", "实验室长凳：两支样本管并排，冷光，无标签", "双管反光切黎明屋",
     "Cool lab bench at dawn light: two clear unlabeled sample tubes standing side by side in a plain rack, one blank evidence envelope behind, no markings, no people. Slow pan across the two tubes, one bench.",
     "仪器提示音一声"),
    ("S27", "graphic", "信息卡 static card", "转机卡：2017底上传数据库 / 家谱追到19世纪 / 层层收窄", "卡片切黎明排车",
     "转机：2017年底 / 凶手DNA上传公开家谱数据库 / 家谱追溯到19世纪", "上行弦乐+卡片敲击"),
    ("S28", "agnes", "航拍缓慢前移 aerial drift", "逮捕清晨：郊区独栋屋前停着三辆无标记车，无人下车画面", "车顶反光切门开逆光",
     "Dawn aerial drift over one modest suburban house: three unmarked cars parked at the curb, officers as distant silhouettes seen only from behind on the lawn, soft fog, no plates or signs. One continuous slow approach.",
     "车门轻响两下，无线电"),
    ("S29", "agnes", "固定中景 static medium", "门开逆光：老年男子背影，双手在背后戴铐（只拍背与手）", "铐光切审讯桌",
     "Medium view of an open front door in backlight: an elderly man seen strictly from behind with hands cuffed behind his back, two officer silhouettes at the sides, no faces anywhere, no text. Locked frame, only the door light shifts.",
     "手铐一声轻咔"),
    ("S30", "agnes", "微距横移 macro slide", "审讯室：空椅、一份空白笔录、一杯水，顶光", "空白笔录切签字手",
     "Macro slide across an interrogation table under a single ceiling light: one empty chair, a blank transcript page with no writing, a paper cup of water, no people in frame. One continuous room.",
     "空调低噪，纸张轻响"),
    # ---------------- N05 ----------------
    ("S31", "agnes", "固定微距 macro static", "象征：一只手在空白认罪书上签字（只拍手与笔）", "笔尖黑切礼堂",
     "Locked macro on a table: a man's hand signs a completely blank document with a plain pen, only the motion of writing visible, no letters appear, no face, cool office light. One continuous shot.",
     "笔尖沙沙声"),
    ("S32", "agnes", "缓慢升镜 crane up", "大学礼堂：成排空椅在暖光里，麦克风孤立在台上", "麦克风切空法庭",
     "Slow crane rise inside a large university auditorium before the hearing: rows of empty seats in warm light, one microphone on a small stage, no people, no banners, no text. One continuous rise.",
     "空旷房间混响，低语渐起"),
    ("S33", "graphic", "信息卡 static card", "量刑卡：2020-08 / 11个连续无假释终身 / 幸存者陈述", "卡片切监狱墙",
     "量刑：2020年8月 / 11个连续无假释终身监禁 / 幸存者与家属当庭陈述", "法槌一声（克制）"),
    ("S34", "agnes", "缓慢拉远 slow pull-back", "黄昏监狱高墙与铁门，无看守画面，天空钠橙", "墙影切家谱纸",
     "Dusk view of a plain prison perimeter wall and closed steel gate in sodium-orange sky, no guards, no people, no signs or lettering on the wall. Slow pull-back from the gate to the long empty wall.",
     "远处铁门低鸣"),
    ("S35", "agnes", "微距横移 macro slide", "回收意象：空白家谱纸上，一支铅笔圈出一个空框", "空框切路缘垃圾桶",
     "Macro slide over the same aged genealogy chart from the opening: a pencil now circles one empty box among the blank boxes, no names anywhere, warm lamp light. One tabletop, one continuous shot.",
     "铅笔圈画声"),
    ("S36", "agnes", "低机位推近 low dolly", "回收意象：黎明路缘垃圾桶，纸巾已不在，天空转亮", "空路缘切航拍",
     "Low dolly at dawn along the same suburban curb from the opening: the unmarked trash can stands empty, the tissue gone, pale gold morning light replacing sodium orange, no people. One continuous street.",
     "晨风，一声远处车鸣"),
    ("S37", "agnes", "航拍缓慢前移 aerial drift", "收束：清晨同一条郊区街，门廊灯熄了，生活继续", "航拍淡出接END",
     "Wide aerial drift over the same flat suburb at clear morning: ranch houses, school-bus yellow light on roofs, one porch light switching off, no people, no signs. One continuous forward drift, hold the final composition.",
     "音乐收束，留白"),
    ("S38", "agnes", "固定远景 static wide", "备忘画面：冷案桌灯下，红线连接的两摞卷宗已合为一摞", "合摞切END卡",
     "Wide locked view of the cold-case table at night: the two folder stacks now merged into one neat pile, the red string coiled beside it, green lamp light steady, no people, no text. Only dust motes drift.",
     "纸张轻落一声"),
    # ---------------- N06 ----------------
    ("S39", "agnes", "缓慢横移 slow pan", "片尾余韵：证物架上软盘？不——本案象征：贴着空白标签的纸巾证物袋", "证物袋切END",
     "Slow pan across an evidence shelf at night: one sealed transparent evidence bag containing a crumpled white tissue with a completely blank label, beside blank-tabbed boxes, cool light. No people, no writing. One continuous shelf.",
     "低频收束音"),
    ("S40", "agnes", "微距推近 macro push", "片尾余韵：家谱纸角被台灯照亮，其余没入黑暗", "光角切END卡",
     "Macro push toward the corner of the aged genealogy chart lit by a warm desk lamp, the rest of the page falling into darkness, blank boxes only, no names. One tabletop, one continuous shot.",
     "灯丝轻响"),
    ("S41", "graphic", "信息卡 static card", "结语卡：规模与服刑：13谋杀 / 87受害者53现场 / North Kern服刑", "卡片切END",
     "结语：13名谋杀受害者 / 87名受害者 · 53个现场 / 北克恩监狱服刑中", "卡片低音"),
    ("S42", "agnes", "缓慢拉远 slow pull-back", "END前静帧：清晨郊区全景，雾散", "淡出",
     "Slow pull-back from one porch to the whole flat suburb at clear morning, mist lifting, roofs in dusty gold light, no people, no signs. One continuous retreat, hold the final wide composition.",
     "音乐留白"),
    ("S43", "agnes", "固定微距 macro static", "END前静帧：空白笔录纸角与一杯水，顶光稳定", "淡出",
     "Locked macro of the interrogation table corner: the blank transcript page edge and the paper cup of water under steady ceiling light, no people, no writing. Only a faint light breath.",
     "安静底噪"),
    ("S44", "agnes", "缓慢横移 slow slide", "END前静帧：礼堂空椅一排，暖光不变", "淡出",
     "Slow lateral slide along one row of empty auditorium seats in steady warm light, no people, no text. One continuous row, hold the final composition.",
     "空旷混响收尾"),
    ("S45", "agnes", "航拍缓慢前移 aerial drift", "END前静帧：橘林晨雾，叶子反光", "淡出接END卡",
     "Slow aerial drift over the orange grove at misty morning: leaves catching pale gold light, rows fading into fog, no people, no buildings. One continuous drift, hold the final composition.",
     "风声渐隐"),
]

CARD_HEADER = "案件档案 · 加州 1976-1986"
CARD_FOOTER = "资料摘要与示意图 · 并非原始档案影像"
CARDS = {
    "S04": ("金州杀手", "加州 · 1976-1986", "13名谋杀受害者 · 至少45名强奸受害者 · 120+起入室"),
    "S08": ("约瑟夫·德安杰洛", "1945年生 · 越战退伍军人", "前加州警员 · 2018年被捕"),
    "S13": ("案件时间线", "1976-1986 · 萨克拉门托到南加州", "东区强奸犯 → 原始夜行者 · 2001年DNA并案"),
    "S20": ("金州杀手 · 命名", "犯罪写作人 米歇尔·麦克纳马拉", "《我在黑暗中》2018年出版"),
    "S27": ("转机", "2017年底 · 凶手DNA上传公开家谱数据库", "家谱追溯到19世纪 · 按年龄与居住地收窄"),
    "S33": ("量刑", "2020年8月 · 大学礼堂", "11个连续无假释终身监禁 · 幸存者当庭陈述"),
    "S41": ("结语", "13名谋杀受害者 · 87名受害者 · 53个现场", "北克恩监狱服刑中"),
}
TITLE_CARD = ["金州杀手：家谱里的名字", "四十年的冷案，与一张被丢弃的纸巾"]
END_CARD = [
    "最致命的，是数据库里的家谱，还是那张纸巾？",
    "金州杀手案 · 加州 1976-1986 · 13名谋杀受害者",
    "出卖他的不是顿悟，是四十年不放弃的人。",
    "资料：ABC News / BBC / Biography · 原创解说 · AI动画情景重现",
]
CAPTION_KEYWORDS = ["家谱", "纸巾", "13项一级谋杀", "十一个连续无假释终身", "2018", "DNA"]
LABEL_OVERRIDES = {
    "S24": "AI动画示意 · 非监视影像",
    "S25": "AI动画示意 · 非取证影像",
    "S28": "AI动画示意 · 非逮捕影像",
    "S29": "AI动画示意 · 非逮捕影像",
    "S32": "AI动画示意 · 非庭审现场",
    "S34": "AI动画示意 · 非监狱影像",
}
SFX_EVENTS = [("S04", "press"), ("S13", "press"), ("S16", "keys"), ("S19", "machine"),
              ("S20", "paper"), ("S27", "machine"), ("S31", "keys"), ("S33", "press")]

TITLES = [
    "金州杀手：逃了40年，最后出卖他的是一棵家谱树",
    "当过警察的杀手：反侦查十多年，败给一张丢掉的纸巾",
    "13起命案冷案30年：数据库里的远亲家谱，指认了金州杀手",
]
HOOK = "他反侦查了四十年，却败给了远亲上传的家谱数据和一张丢掉的纸巾。"
GOLDEN_LINES = [
    "出卖他的不是天才警探，是一棵长到十九世纪的家谱树。",
    "冷案不怕冷，怕的是没人再翻它。",
    "你觉得最致命的，是数据库里的家谱，还是那张纸巾？评论区聊聊。",
]
DESCRIPTION = "加州1976到1986年，13名谋杀受害者、至少45名强奸受害者、120多起入室，凶手当过警察，反侦查十多年，案件冷了三十年。2017年底调查员把凶手DNA上传公开家谱数据库，家谱专家画出追溯到19世纪的家族树，层层收窄到德安杰洛；警察捡起他丢掉的一张纸巾，DNA对上了。2020年他认罪13项一级谋杀，被判11个连续无假释终身监禁。AI动画情景重现，非新闻影像；评论区聊聊：最致命的是家谱还是纸巾？"
QUESTION = "你觉得最致命的，是数据库里的家谱，还是那张纸巾？"
HASHTAGS = ["#真实案件", "#金州杀手", "#DNA", "#冷案", "#悬疑"]

GRID = 4           # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 7  # 每个 Agnes 镜头实际请求的时长（169 帧 @ 24 fps）
SEED_BASE = 19451108  # DeAngelo 生日，seed 可追溯


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
            "seed": SEED_BASE + i + 1,
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

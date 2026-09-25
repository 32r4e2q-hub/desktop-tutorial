#!/usr/bin/env python3
"""《声墙与一滴血》（菲尔·斯佩克特案）的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
样板是 production/gilgo/build_story.py —— 一部已经出片、已经过三轮复审的成片）。

用法::

    python3 production/spector/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/spector/build_story.py --script   # 生成 抖音脚本.md（3 标题 / 核心爆点 / 四列分镜表 / 金句）
    python3 production/spector/build_story.py --publish  # 生成 抖音发布文案.md（标题 / 介绍 / 提问读者一句话 / 话题）

案件：2003-02-03 洛杉矶阿尔汉布拉山庄宅，女演员拉娜·克拉克森死于门厅一声枪响；
音乐制作人菲尔·斯佩克特称其「意外自杀」。两次审判的核心争议是血迹形态学：
辩方主张「白夹克上只有至多 18 点不足一毫米的血点 → 他站得远 → 不是开枪者」；
2007 年一审陪审团十比二僵持、流审；2009 年重审裁定二级谋杀成立，判十九年监禁至终身；
2021 年他在狱中去世同年，流体动力学论文（Li, Michael & Yarin, Physics of Fluids）
用枪口燃气涡环解释了「开枪者衣物可以几乎无血」——物理给这场争论补上了答案。

写法规则（都是吉尔戈那部踩出来的，别省）：

- 六段解说合计 ≈ 760–800 字（含标点），TTS 收紧停顿后 ≈ 176 秒；每段末尾留一个钩子；
  数字一律写成中文读法（「二零二一年」「十八个点」），TTS 和字幕才一致；
  不写血腥/侵害过程的具体描写（TTS 审核会拒，红线也不允许）。
- 45 镜 = 38 个 Agnes 动画镜头 + 7 张信息卡，按成片顺序编号，**每个镜头只出现一次**；
  规划网格 4 秒/镜，Agnes 每镜实际请求 7 秒，真正的时长由 render.py 的 CUTS 按配音停顿决定。
- 提示词先钉死"唯一场景"（framed on … from the first frame to the last），再明确排除别的场景
  （no windows / no view outside / no skyline），最后加 HOLD 句（no cut, no scene change, no camera relocation）。
  否定词对这个模型基本没用，想去掉天际线就别给它地平线（低机位、让墙/树篱/门廊填满背景）。
- 人只能是背影、剪影、手；画面里不许有可读文字；不出现遗体、暴力动作、开枪瞬间；
  血只以「深红墨滴示意图」和克制的取证微距（布面细小深红点）出现，枪械不直接出镜。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"

TITLE = "声墙与一滴血"

# 与 production/gilgo 同一画风：风格化 2D 动画纪录片、手绘图像小说质感、软赛璐璐 shading。
# 世界描述换成本片的地点与年代（洛杉矶 1960s 录音室 / 2003 山庄宅 / 法庭 / 物证实验室）。
# 注意：**不要**把「血滴示意图」写进世界描述——吉尔戈的教训是世界描述里的元素会被模型
# 塞进一切不相干的场景（曼哈顿塔楼长在郊区屋顶）。示意图只写在需要它的那几镜里。
# style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 38 镜全部重做。
STYLE_PREFIX = (
    "Stylized 2D animated documentary illustration with hand-painted graphic-novel textures and soft "
    "cel shading, Los Angeles across six decades: warm wood-and-tungsten 1960s recording studios with "
    "analog mixing consoles and walls of gold records, a Spanish colonial revival castle-like mansion "
    "on a dark Alhambra hillside with arched windows and a grand foyer staircase, neon-lit Hollywood "
    "nightclubs, wood-paneled county courtrooms, steel-bench forensic laboratories and prison "
    "corridors; horizontal 16:9 cinematic composition, muted palette of slate blue, steel grey, warm "
    "tungsten amber and sodium-orange practical light, cool California night exteriors, restrained "
    "procedural true-crime mood, no horror excess; every character is shown only from behind, in "
    "silhouette, or as hands and props - never a clear frontal face; absolutely no readable text, "
    "letters, numbers, logos, license plates or brand marks anywhere inside the frame; one single "
    "continuous smooth slow camera move per shot exactly as directed. "
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
    "全部 Agnes 镜头为风格化 2D 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，法庭/监狱/取证/示意镜头另有更具体标签，不冒充庭审、监控或证物照片",
    "不重现开枪瞬间，不展示遗体与血腥；受害者拉娜·克拉克森不以任何人像出现，只用地面上的手袋、门前的白花等象征物致意",
    "血在画面里只以两种形式出现：抽象物理示意图（深红墨滴轨迹、蓝色辉光反应）与克制的取证微距（白布与夹克上不足一毫米的细小深红点），以「墨滴实验」呈现，不做血腥化表达",
    "枪械不直接出镜：「擦枪」一镜用阴影中的小型金属物体示意，凶器只存在于解说与信息卡里",
    "真实人物（斯佩克特、克拉克森、司机、警员、陪审员）只以背影、剪影、手部出现，不用 AI 生成的脸冒充本人",
    "每一句事实都能指到 sources 里的一条公开报道；2021 年流体动力学研究如实表述为「多年后物理给出答案」，不冒充当年定罪的庭审证据；血迹形态学作为学科的可争议性在脚本「事实边界」注明",
    "所有中文姓名、日期、字幕一律后期添加，不交给视频模型拼写",
    "同一地点保留光线、道具、运动方向；跨地点通过声音桥与物件（白夹克、白布、证物袋、录音台）匹配衔接",
    "人工检视 qa/ 接触表，露脸、畸变、伪文字、中途换场的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

# 每条事实的公开来源。usage 写清"这条来源支撑了哪几句话"。
SOURCES = [
    {"id": 1, "url": "https://www.bbc.com/news/world-us-canada-55697979",
     "usage": "2021-01-16 死于狱中、享年八十一岁；「声墙」革新流行乐；1961–1965 二十首 Top 40 热单；与披头士、Righteous Brothers、Ike & Tina 合作；2009 年二级谋杀罪成、十九年至终身；「亲了枪」说法；多名女性指证曾被持枪相向"},
    {"id": 2, "url": "https://en.wikipedia.org/wiki/Phil_Spector",
     "usage": "生于 1939-12-26 布朗克斯；制作披头士告别专辑《Let It Be》与列侬《Imagine》；阿尔汉布拉山金字塔城堡式宅邸；2003-11 被控谋杀；2007 一审流审、2009-04-13 罪成、2009-05-29 宣判；上诉均被驳回"},
    {"id": 3, "url": "https://www.washingtonpost.com/wp-dyn/content/story/2009-04-13/ST2009041302068.html",
     "usage": "2009-04-13 洛杉矶高等法院陪审团裁定二级谋杀罪成立（AP 现场报道）"},
    {"id": 4, "url": "https://www.euronews.com/2021-01-17/beatles-producer-and-convicted-murderer-phil-spector-dies-aged-81",
     "usage": "至死坚称是「意外自杀」；城堡式宅邸位于洛杉矶边缘；在斯托克顿以东的监狱医院度过晚年"},
    {"id": 5, "url": "https://news.pollstar.com/2021-01-17/wall-of-sound-producer-phil-spector-dies-in-california-prison/",
     "usage": "克拉克森死于俯瞰阿尔汉布拉的山庄宅门厅；隐士生活、邻居不知宅主其人；2021-01-16（周六）在外部医院被宣告死亡、享年八十一岁（AP 讣告）"},
    {"id": 6, "url": "https://www.oxygen.com/accident-suicide-or-murder/crime-news/music-producer-phil-spector-shot-lana-clarkson-case-breakdown",
     "usage": "司机报警；斯佩克特出门第一句「我想我杀了人」；克拉克森四十岁、曾在《开放的美国学府》出演小角色；牙齿碎片在楼梯处被发现（后坐力）；法医路易·佩纳判定他杀、手腕瘀伤提示挣扎；枪上无其指纹；衣柜里起获皱褶血渍白夹克；浴室白布浸有受害者血；浴室/楼梯扶手/后门框多处血迹提示清理现场；2003-11-28 被控二级谋杀；五名女性出庭指证持枪威胁；一审陪审团商议十二天僵持"},
    {"id": 7, "url": "https://www.moviemaker.com/phil-spector-murder-lana-clarkson-details/",
     "usage": "凶案组探长 Rich Tomlin：弹道呈下行角度——「自杀会平着甚至朝上，不会朝下」；检方主张现场被布置成自杀；辩方称其事业受挫、情绪低落"},
    {"id": 8, "url": "https://www.cnn.com/2007-12-11/court.archive.spector8/index.html",
     "usage": "2007 年一审流审：陪审团十比二倾向定罪、商议十二天；有陪审员称「大家期待看到更多血」；辩方主张若在三英尺内开枪白夹克应被浸透；检方将重审"},
    {"id": 9, "url": "https://www.latimes.com/archives/la-xpm-2007-aug-02-me-science2-story.html",
     "usage": "辩方防线以血迹形态学为中心：白夹克上至多十八个点、部分直径不足一毫米，主张他站在远至六英尺外；血迹形态学奠基人 Herbert MacDonell 出庭作证：站在血雾直射路径侧面的开枪者不一定被血覆盖；一毫米级的点飞不了远距"},
    {"id": 10, "url": "https://www.latimes.com/archives/la-xpm-2007-aug-13-me-spector13-story.html",
     "usage": "枪身涂抹状血迹=检方称擦拭灭纹；浴室地面浸血白布尿布=检方称清理现场；西裤口袋内克拉克森血=或曾把枪插进口袋；裙装带血而伸展的双腿无血=血雾飞行不超过约三英尺、持夹克的他在射击距离内；辩方逐项反驳"},
    {"id": 11, "url": "https://phys.org/news/2021-06-case-physics.html",
     "usage": "枪口燃气以湍流涡环形式喷出；近距射击时干扰反向血雾、使液滴偏转甚至完全掉头落在受害者身后；Yarin：「这基本证明开枪者可以是有罪的——衣物近乎干净存在物理上成立的解释」"},
    {"id": 12, "url": "https://mie.uic.edu/news-stories/solving-a-murder-case-with-physics/",
     "usage": "庭审中辩护主张：白夹克上只有少量血点→不可能是开枪者；Yarin 因该案庭审影像产生研究动机，与爱荷华州立大学 James Michael、Daniel Attinger 合作，系列论文说明斯佩克特可能是开枪者而衣物相对无血"},
    {"id": 13, "url": "https://doi.org/10.1063/5.0045214",
     "usage": "Gen Li, James B. Michael, Alexander L. Yarin《Blood backspatter interaction with propellant gases》Physics of Fluids (2021)：反向血雾与推进剂燃气涡环相互作用的理论与实验"},
    {"id": 14, "url": "https://nij.ojp.gov/library/publications/effect-firearm-muzzle-gases-backspatter-blood",
     "usage": "Taylor, Laber, Epstein, Zamzow & Baldwin, Int J Legal Med 125:617–628 (2010)：枪口燃气/气流与反向溅血相互作用的系统实验（NIJ 资助）"},
    {"id": 15, "url": "https://www.ojp.gov/library/publications/self-similar-turbulent-vortex-rings-interaction-propellant-gases-blood",
     "usage": "Comiskey & Yarin (2019)：枪口推进剂燃气形成自相似湍流涡环、速度量级约一百米每秒；可把血滴推得更远、甚至反向；同时输运射击残留物"},
    {"id": 16, "url": "https://www.criminallegalnews.org/news/2022/may/1/pseudoscientific-practice-blood-spatter-analysis-how-desire-convictions-drives-flawed-prosecutions/",
     "usage": "MacDonell 获司法部资助、1971 年出版《Flight Characteristics and Stain Patterns of Human Blood》（血滴飞行特征与斑迹形态的奠基报告）；1954 年 Sheppard 案 Paul Kirk 首次血迹出庭作证；同时记录学界对血迹形态分析主观性的质疑（写入脚本事实边界）"},
    {"id": 17, "url": "https://www.hollywoodreporter.com/business/business-news/spector-lawyer-testifies-missing-evidence-142923/",
     "usage": "案发日 2003-02-03；短管点三八口径左轮手枪；辩方专家被指从现场取走一枚小物件（疑为断裂指甲片）未移交检方——证据争议是双向的"},
    {"id": 18, "url": "https://www.truecrimezone.com/phil-spector/",
     "usage": "凶器为 Colt Cobra 左轮手枪；夹克十八个点血迹；最初对警方称「意外」；重审 2008-10-20 开庭；2009-05-29 宣判：十五年监禁至终身 + 涉枪加刑四年（合计十九年至终身）；获令支付受害者母亲丧葬费用"},
]

# 六段解说。措辞刻意用新闻语体（「身亡」「枪响」「血迹」），
# 一是抖音审核，二是配音 TTS 的内容审核（吉尔戈那部「他怎么杀」直接被拦）。
# 数字全部写成中文读法；合计 ≈790 字（含标点）。
CHAPTERS = [
    ("N01", "黄金开头：擦掉的枪，擦不掉的物理",
     "十八个不到一毫米的血点，怎么给人定罪？二零零三年凌晨，洛杉矶山上的城堡宅邸一声枪响。女演员死在门厅，左轮手枪落在脚边，枪上没有指纹。宅子里的另一个人，是乐坛活着的传奇，他说：是她自己把枪放进嘴里的。他把枪擦干净，门厅擦得一尘不染。可这些血点，早已按流体力学的方程写好了真相。这就是菲尔·斯佩克特案。"),
    ("N02", "他是谁：声墙之父",
     "这个男人是谁？菲尔·斯佩克特，「声墙」发明人：把乐器一层层叠录，砌成一面声音的墙。五年二十首热单；披头士告别专辑、列侬的《想象》，都出自他手。另一边，女演员拉娜·克拉克森，四十岁，当时在俱乐部工作。当晚两人相识，他提出送她回家。"),
    ("N03", "他的版本：意外自杀",
     "汽车开进宅邸。他的版本是：克拉克森自己开了枪——她「亲了枪」，一场意外自杀。可司机已经报了警：宅门打开时，第一句话是「我想我杀了人」。警方在浴室找到浸血的白布，他手上检出射击残留物。多名女性还指证，曾被他持枪相向。"),
    ("N04", "法医先撕开一道口子",
     "法医撕开了「自杀」的说法：弹道向下倾斜——自己开枪，枪口该是平的甚至朝上；被后坐力崩落的牙齿，在楼梯脚被发现。验尸官结论：他杀。但辩护手里也有牌：夹克上只有十八个血点——这么近的距离，人该被血雾糊满才对。二零零七年一审，陪审团十比二，流审。全案卡在一个问题上：血滴到底往哪儿飞？"),
    ("N05", "流体力学进场",
     "硬核的部分来了。血滴砸在表面，宽除以长，就是撞击角的正弦值；多条轨迹连线，汇聚到空中一点——开枪的位置。后来流体力学算出：枪口燃气卷成约一百米每秒的涡环，迎面撞上反向飞出的血雾，把它推回去、甚至掉头——开枪的人可以干干净净。底牌「血太少」，被这组方程撕碎。袖口那十八个点，恰好落在物理认定的开枪者身上。二零零九年重审，陪审团裁定：有罪。"),
    ("N06", "结局与金句",
     "二级谋杀，十九年监禁至终身。二零二一年，八十一岁的斯佩克特在狱中去世；四个月后，那篇涡环论文发表——人不在了，物理替这个案子写完了最后一页。他一生砌起声音的墙，最后却挡不住一滴血说出真相。你相信有完美的犯罪，还是只有还没追上的科学？评论区聊聊。"),
]

# 每一镜：(id, kind, 运镜, 叙事职责, 衔接方式, 英文提示词或信息卡说明, 音效/备注)
# 45 镜 = 38 个 Agnes 动画镜头 + 7 张信息卡（S04 案件名片、S10/S13 人物档案、S25 法医结论、
# S32 撞击角公式、S35 涡环数字、S39 判决），按成片顺序编号，每个镜头只出现一次，不复用。
SHOTS = [
    # ---------------- N01 黄金开头（7 镜）----------------
    ("S01", "agnes", "缓推 slow push-in",
     "0–5 秒钩子：夜里山上的城堡宅邸，只有一扇窗亮着",
     "亮窗硬切室内擦枪特写",
     "A Spanish colonial revival castle-like mansion on a dark Los Angeles hillside at night, seen from the front driveway: heavy stone walls, arched windows, one single warm-lit window on the ground floor, tall palm silhouettes and low hedges filling the foreground, hillside chaparral darkness behind, no city skyline, no other buildings. Camera: one smooth slow push-in toward the lit window. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "低频环境声起；远处一声闷响后死寂"),
    ("S02", "agnes", "微推 very slow push-in",
     "钩子第二拍：阴影里的手用白布仔细擦拭一个小型金属物体——他擦掉了枪",
     "擦拭动作接墨滴示意图，「擦得掉表面，擦不掉轨迹」",
     "Extreme close-up in a dim mansion interior at night: a man's hands in white shirt cuffs and a dark suit (hands and wrists only, nothing else of the person) carefully wiping a small dark metal object with a folded white cloth on a polished wooden table, the object's shape kept vague and mostly in shadow, one warm lamp glowing at the edge of frame. Camera: one very slow push-in on the hands. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "布料摩擦声，极轻；钟表滴答"),
    ("S03", "agnes", "横移 slow lateral drift",
     "钩子第三拍：深红墨滴沿抛物线飞行、轨迹线在空中汇聚——血点在「说话」",
     "汇聚点亮成案件名片卡",
     "Abstract scientific visualization on a dark navy blueprint grid background: a handful of crimson ink droplets flying in slow graceful parabolic arcs from left to right, thin white trajectory lines tracing each path, all lines converging toward one small glowing point at the right, subtle streak motion blur, like a physics textbook diagram come to life; no room, no people, no objects, pure diagram. Camera: one slow lateral drift following the arcs. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "纸面书写般的沙沙声；汇聚点亮起时一记轻音"),
    ("S04", "graphic", "静帧信息卡",
     "案件名片：菲尔·斯佩克特案（2003 · 洛杉矶）",
     "名片收束钩子，转入 1960 年代录音室",
     "案件名片卡：大标题「菲尔·斯佩克特案」，第一行「2003 · 洛杉矶 阿尔汉布拉山宅邸」，第二行「『声墙』缔造者被控枪杀女演员」",
     "档案纸翻动声"),
    ("S05", "agnes", "缓推 slight push-in",
     "案发后的空门厅：大楼梯、黑白格地面，只有两支警用手电的光柱缓缓扫过",
     "手电光扫过接夜里盘山路车灯",
     "The grand foyer of a Spanish colonial mansion at night, completely empty: wide stone staircase with dark wooden banister, checkerboard marble floor, wrought-iron chandelier above; two police flashlight beams sweep slowly across the floor and banister from off-frame, no people visible, only the moving beams and hard shadows. Camera: one slow slight push-in on the empty staircase. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "对讲机电流声（远、轻）"),
    ("S06", "agnes", "跟拍 tracking from behind",
     "时间回拨的转场意象：深夜盘山公路，一辆黑色轿车尾灯驶向山上",
     "车灯驶向宅邸接司机挡风玻璃视角",
     "A dark sedan seen from behind climbing a winding empty hillside road at night, red taillights glowing, headlight beams sweeping the curves ahead, chaparral and palm silhouettes crowding both sides of the road, no other traffic, no skyline. Camera: one smooth tracking shot following the car from behind. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "引擎低鸣、轮胎碾过沙石"),
    ("S07", "agnes", "缓推 push-in through windshield",
     "司机视角：挡风玻璃外，宅邸墙上已经亮起红蓝警灯——911 已经打过了",
     "红蓝闪烁淡出，接 1960 年代录音室暖光（冷暖对切）",
     "View through the windshield of a parked car at night from the driver's perspective: the stone facade of a hillside mansion ahead, red and blue emergency lights already pulsing silently against the walls and palms, faint light haze, the dark dashboard silhouette along the bottom of frame, no people visible. Camera: one very slow push-in through the windshield. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "电话拨号音（911 意象）"),
    # ---------------- N02 案件背景：他是谁（7 镜）----------------
    ("S08", "agnes", "过肩缓推 push-in over shoulder",
     "1960 年代录音室控制间：模拟调音台，制作人背影，烟雾与钨丝灯暖光——声墙诞生的地方",
     "调音台暖光叠化成声波墙抽象动画",
     "A 1960s recording studio control room at night in warm tungsten light: a large analog mixing console with rows of glowing knobs and faders, a producer in a suit seen from behind seated at the console, through the glass behind him a dark live room with faint microphone silhouettes, thin smoke haze curling in the lamplight, framed gold records on the side wall with no readable text. Camera: one slow push-in over his shoulder toward the console. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "磁带机走带声；远处隐约的鼓组"),
    ("S09", "agnes", "上摇 slow upward tilt",
     "「声墙」可视化：几十条琥珀色声波线自底部层层升起，砌成一面发光的墙",
     "声波墙淡出到人物档案卡",
     "Abstract music visualization on a dark warm-brown background: dozens of thin glowing amber sound-wave lines rise one after another from the bottom of frame and stack densely into a tall luminous wall that fills the screen, like layers of instruments piling into a wall of sound, soft film grain, gentle pulsing glow; no people, no instruments, no room. Camera: one slow upward tilt along the growing wall. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "弦乐群渐强（配乐层）"),
    ("S10", "graphic", "静帧信息卡",
     "人物档案：菲尔·斯佩克特（声墙之父）",
     "档案卡切金唱片手部特写",
     "人物档案卡：大标题「菲尔·斯佩克特」，第一行「1939—2021 · 音乐制作人」，第二行「发明『声墙』，五年二十首热单」",
     "档案纸翻动声"),
    ("S11", "agnes", "横移 lateral with the disc",
     "档案室暖光里，一双手从成摞黑胶中抽出一张金色唱片——他的黄金年代",
     "抽出唱片动作接夜店霓虹外景（年代跳切）",
     "Close-up in a dim archive room: a pair of hands (hands only, no faces, no people) in warm practical lamp light pulling one gold-toned record disc from a tall stack of vinyl records on a wooden shelf, dust motes floating in the light, shelf edges filling the frame, no readable labels anywhere. Camera: one slow lateral move following the pulled disc. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "纸套摩擦黑胶的沙沙声"),
    ("S12", "agnes", "缓推 push-in toward entrance",
     "2003 年的好莱坞夜店门口：空白霓虹、湿地反光，一个深色连衣裙的背影走向大门——克拉克森（不露脸）",
     "门口背影接卡座内两人剪影",
     "A Hollywood nightclub entrance at night seen from across the street: a glowing blank marquee and soft pink and blue neon tubes with abstract unreadable shapes, a lone woman in a dark dress seen from behind walking toward the door, a doorman silhouette standing aside, wet asphalt reflecting the colored lights, no faces visible. Camera: one smooth slow push-in toward the entrance. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "夜店低频隔墙传出"),
    ("S13", "graphic", "静帧信息卡",
     "人物档案：拉娜·克拉克森（受害者，不以人像出现）",
     "档案卡切卡座两人剪影",
     "人物档案卡：大标题「拉娜·克拉克森」，第一行「40 岁 · 电影演员」，第二行「出演过《开放的美国学府》，事发时在俱乐部工作」",
     "档案纸翻动声（轻）"),
    ("S14", "agnes", "缓推 push-in from behind",
     "夜店卡座：两个背影隔着小圆桌对坐，烛光与酒杯——当晚相识",
     "烛光暖点叠化到宅邸铁门夜色",
     "Inside a dim nightclub VIP booth at night: two figures seated across a small round table seen only from behind and in deep silhouette, a man in a dark suit and a woman with dark hair, two drink glasses and a small candle glowing on the table, warm amber stage light bokeh far in the background, no faces visible anywhere. Camera: one very slow push-in toward the table from behind. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "冰块碰杯、低语环境声"),
    # ---------------- N03 作案手法与伪装（8 镜）----------------
    ("S15", "agnes", "横移 lateral track",
     "深夜，轿车穿过打开的锻铁大门驶向宅邸——只有两个人进去了",
     "大门合拢意象接空门厅",
     "Night, from inside a driveway looking toward the gate: a dark sedan passes through the open wrought-iron gate of a hillside Spanish colonial estate, headlight beams crossing the stone pillars, the mansion's warm-lit facade looming beyond, palm shadows stretching on the ground, no people visible. Camera: one slow lateral track following the car through the gate. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "铁门滚动声；碎石路"),
    ("S16", "agnes", "缓推 push-in toward handbag",
     "凌晨的空门厅：一只女式手袋倾倒在黑白格地面上——她在场过，但人绝不入画",
     "手袋特写拉出到司机等待的车内",
     "The mansion foyer at night, empty and silent: checkerboard marble floor, grand staircase, wrought-iron chandelier; in the middle of the floor lies a small dark women's handbag tipped on its side under a single overhead light, hard shadows around it, no people, no other objects. Camera: one slow push-in toward the handbag. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "死寂；一根灯丝的嗡鸣"),
    ("S17", "agnes", "座椅间缓移 slow drift forward",
     "车里的司机背影：一动不动望着山上那扇亮着的窗——时间被拉长",
     "窗光闪烁接宅门打开",
     "Night, from the back seat of a parked car: a chauffeur in a dark suit sitting motionless in the driver's seat, seen from behind, his head turned slightly toward the dark mansion facade on the hill through the windshield, one faint warm-lit window up there, dim dashboard glow along the bottom, no face visible. Camera: one very slow drift forward between the seats. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "车内钟表滴答；远处隐约一声闷响"),
    ("S18", "agnes", "缓推 push-in toward doorway",
     "宅门打开：深色西装背影立在门内光里，司机剪影奔上前——「我想我杀了人」的瞬间（枪不入画）",
     "奔跑动作急停接取证静物",
     "Night exterior at the mansion's front door: the heavy wooden door stands open with warm light spilling out, a man in a dark suit standing motionless on the top step seen entirely from behind; in the foreground a chauffeur silhouette hurries toward him across the driveway, red and blue emergency lights beginning to pulse on the stone wall, no faces visible, no weapons visible. Camera: one slow push-in toward the doorway. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "急促脚步在碎石上；喘息（远）"),
    ("S19", "agnes", "俯拍横移 overhead drift",
     "证物袋里的白布：浸着暗红褐色痕迹的折叠棉布——清理现场的那块布",
     "证物袋横移接衣柜里的白夹克",
     "Forensic still-life close-up on a steel evidence table under cool white light: a sealed transparent plastic evidence bag containing a folded white cotton cloth with faint dark reddish-brown marks, lying on brushed metal, a plain grey laboratory wall filling the background, no readable labels, numbers or logos on the bag, no people. Camera: one slow overhead drift across the bag. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "塑料袋窸窣（取证质感）"),
    ("S20", "agnes", "缓推 push-in toward jacket",
     "夜里的步入式衣柜：一件白礼服夹克独自挂在深色西装中间，门缝光斜切过袖口",
     "袖口特写叠化到证物台俯拍",
     "A dim walk-in closet at night: a white dinner jacket with dark satin lapels hanging alone on a wooden hanger among dark suits, one shaft of hallway light from the doorway raking across the white fabric, the left cuff slightly turned, no people, no readable tags or labels. Camera: one slow push-in toward the white jacket. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "衣架轻碰木杆的一声"),
    ("S21", "agnes", "俯拍横移 lateral overhead drift",
     "证物台俯拍：三只证物袋排成一行（白布、阴影中的小物件、白色布料）——被登记的一切",
     "证物袋排结束接门口与警察对话的背影",
     "Top-down forensic photograph style on a steel table under cool light: three sealed transparent evidence bags arranged in a neat row, containing a folded white cloth, a small dark object kept in deep shadow, and a swatch of white fabric; blank evidence tags with no readable text attached to each bag; plain grey wall and table filling the frame, no people. Camera: one slow lateral overhead drift along the row. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "标签纸轻响；钢笔搁下"),
    ("S22", "agnes", "远距离横移 slow lateral track",
     "宅邸门口：西装背影对着两名警察（同样只给背影/侧影）说话——他的「版本」开始了",
     "红蓝灯光渐弱，接实验室冷光",
     "Night exterior at the mansion entrance: a man in a dark suit seen from behind speaking with two uniformed police officers who are also shown from behind or in profile silhouette, red and blue lights pulsing across the stone facade, a patrol car light bar glowing at the edge of frame, palm shadows swaying slightly, no faces visible anywhere. Camera: one smooth slow lateral track around the group at a distance. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "对讲机杂音；夜风"),
    # ---------------- N04 破案关键（上）：法医与流审（8 镜）----------------
    ("S23", "agnes", "缓推 push-in under lamp",
     "物证实验室：放大灯臂悬在证物袋与玻片上方，白大褂背影在画面边缘",
     "灯臂冷光切到弹道示意图",
     "A forensic laboratory bench at night under cool task lighting: a large illuminated magnifier lamp arm hovering over small sealed evidence bags and glass slides on a steel bench, a technician in a white coat seen from behind at the far edge of the frame, blurred shelves of plain laboratory equipment filling the background, no screens, no readable text, no faces. Camera: one slow push-in under the magnifier lamp. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "通风柜低鸣；玻璃片轻碰"),
    ("S24", "agnes", "沿线缓移 drift along the line",
     "弹道几何示意：一条白色直线以陡峭的下倾角穿过蓝图网格，末端标出角度弧——「自杀不该朝下」",
     "下倾线收束进法医结论卡",
     "Abstract ballistics diagram on a dark navy blueprint grid: a thin white straight line descending across the frame at a steep downward angle, ending in a small angle arc with tick marks, ghostly dashed extension lines and a faint horizontal reference line, like a textbook figure of trajectory geometry; no people, no room, no weapon, pure geometry on dark background. Camera: one slow drift along the descending line. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "铅笔划线声（示意感）"),
    ("S25", "graphic", "静帧信息卡",
     "法医结论卡：弹道向下 · 手腕挣扎痕迹 · 他杀",
     "结论卡切楼梯扶手上的痕迹特写",
     "法医结论卡：大标题「法医结论」，第一行「弹道向下倾斜 · 手腕有挣扎痕迹」，第二行「验尸官判定：他杀，而非自杀」",
     "印章落纸的一声"),
    ("S26", "agnes", "横移 lateral along banister",
     "手电侧光扫过楼梯木扶手：漆面上显现出一道淡淡拖痕与几个细小深色点——擦过，但没擦干净",
     "光点特写拉出到鲁米诺发光全景",
     "Extreme close-up at night: a forensic investigator's gloved hand holding a bright flashlight, the beam raking along a dark polished wooden banister of a staircase, revealing a faint smear and a few tiny dark specks on the wood grain, the rest of the frame in deep shadow, only the gloved hand visible, no faces, no people. Camera: one slow lateral move following the beam along the banister. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "手电开关咔哒；极轻的电流声"),
    ("S27", "agnes", "缓推 push-in toward glow",
     "黑暗门厅里的鲁米诺时刻：白防护服背影喷出的细雾落下，地砖与门框底泛起一片片蓝紫色冷光",
     "蓝紫冷光叠化到法庭暖光",
     "A dark mansion foyer at night: a forensic technician in a white protective suit seen from behind, crouching and spraying a fine mist from a small bottle onto the marble floor; where the mist lands, faint eerie blue-purple chemiluminescent glows bloom in small scattered patches on the tiles and along the bottom of a doorframe, like cold little stars, no other light source, no faces visible. Camera: one slow push-in toward the glowing patches. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "喷雾瓶气压声；光斑亮起时的空灵单音"),
    ("S28", "agnes", "缓推 push-in toward easel",
     "2007 一审法庭：展示架上放着「多线汇聚一点」的抽象示意图，检察官剪影指着它，陪审员一排背影",
     "示意图定格切深夜空法庭",
     "A wood-paneled county courtroom interior with no windows: at the front a large display easel holds an abstract dark diagram of thin white lines converging to one point (no text, no numbers), a prosecutor's silhouette gesturing toward it from behind, rows of jurors seen from behind in soft shadow, warm ceiling light, no faces visible anywhere. Camera: one slow push-in toward the easel. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "法庭低语；木椅轻响"),
    ("S29", "agnes", "缓移 lateral drift",
     "流审之夜的空法庭：只剩辩方桌上一盏台灯，陪审席空着——十比二，差两个人",
     "空法庭切法院外记者离场",
     "An empty county courtroom at night with no people: rows of dark wooden benches and an empty jury box sunk in shadow, a single desk lamp glowing on the defense table, the tall judge's bench looming above, dust hanging still in the lamplight, wood-paneled walls, no windows. Camera: one very slow lateral drift across the empty room. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "台灯电流声；空旷混响"),
    ("S30", "agnes", "上摇 tilt up from steps",
     "法院外夜景：记者剪影提着器材走下石阶——流审的消息传出去，悬念留到重审",
     "台阶尽头叠化到墨滴慢镜",
     "Night exterior of a large downtown courthouse: broad stone steps and tall classical columns, a few reporter silhouettes with camera bags walking away down the steps, street lamps and a lone parked van at the bottom of frame, distant buildings kept as dark featureless shapes, no faces visible. Camera: one slow upward tilt from the steps to the columns. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "零星快门声；城市夜底噪"),
    # ---------------- N05 破案关键（下）：流体力学（8 镜）----------------
    ("S31", "agnes", "锁定微距 slow push-in",
     "物理课开始：一滴深红墨滴慢镜坠落、在浅色表面砸出椭圆斑，旁边淡入白色量角辅助线",
     "椭圆斑叠化进撞击角公式卡",
     "Extreme macro scientific shot on a black background: a single crimson ink droplet falls in ultra slow motion onto a smooth pale surface, splashing into a tiny crown and settling into an elongated elliptical stain; thin white measurement guides and a small angle arc fade in beside the stain like a physics figure, no numbers, no text, no people, no room. Camera: locked macro framing with one very slow push-in. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "液滴入水的轻响（放大）；心跳般的低频"),
    ("S32", "graphic", "静帧信息卡",
     "撞击角公式卡：正弦值 = 血迹宽 ÷ 血迹长",
     "公式卡切暗室激光汇聚",
     "公式卡：大标题「撞击角」，第一行「正弦值 = 血迹宽度 ÷ 血迹长度」，第二行「多条轨迹在三维中延长，汇聚出开枪位置」",
     "粉笔/白板笔一声"),
    ("S33", "agnes", "横移 lateral toward convergence",
     "经典再现：暗室里几十条红色激光线从墙面地面的小点拉出，精确汇聚到空中一点；取证人员背影站在边缘",
     "汇聚亮点爆开成涡环示意图",
     "A dark room at night: dozens of thin red laser beams stretched taut through faint haze, each starting from a small mark on the walls and floor and all converging precisely at one glowing point suspended in mid-air; a forensic investigator's silhouette seen from behind stands at the edge of frame watching the convergence, no faces, no readable text. Camera: one slow lateral move toward the convergence point. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "激光电源的细微高频；空间混响"),
    ("S34", "agnes", "顺流横移 drift with the flow",
     "全片物理高潮：淡蓝色燃气涡环自左向右滚过黑暗，迎面撞上右飞而来的深红液滴群——液滴被推开、减速、掉头",
     "涡环示意图收束进数字卡",
     "Abstract fluid-dynamics visualization on a pure dark background: a glowing pale-blue ring vortex of gas rolls rapidly from left to right, rendered like scientific schlieren photography with delicate internal swirls; a cloud of tiny crimson droplets flying from right to left meets the ring and is visibly deflected, slowed, some droplets turned around and swept backward; thin white streamline arrows trace the flow, textbook-figure style; no people, no room, no weapon. Camera: one slow lateral drift with the flow. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "呼啸的风洞感低频；液滴转向时的细碎音"),
    ("S35", "graphic", "静帧信息卡",
     "涡环数字卡：约一百米每秒 · 血雾可被整个掉头",
     "数字卡切实验室光学台",
     "数字卡：大标题「枪口涡环」，第一行「燃气速度约一百米每秒」，第二行「可把反向血雾推回、甚至让液滴完全掉头」",
     "重音一记（数字落定）"),
    ("S36", "agnes", "沿台缓推 push-in along bench",
     "大学流体力学实验室：注射泵逐滴释放深红墨滴，高速相机环形灯记录，激光片光切开液滴路径，研究员背影",
     "实验台冷光叠化到白夹克袖口微距",
     "A university fluid-mechanics laboratory in a darkened room: on an optical bench a small syringe-pump apparatus releases single dark-red ink droplets one by one into mid-air, a high-speed camera on a tripod with a bright ring light records them, a faint laser sheet cuts through the droplet path, a researcher in a lab coat seen from behind adjusts the rig at the edge of frame, no faces, no readable screens or text. Camera: one slow push-in along the optical bench. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "泵机节拍声；相机快门连拍（轻）"),
    ("S37", "agnes", "微距缓移 drift across cuff",
     "决定性物证：白夹克袖口的微距——十几个不足一毫米的深红小点散布在织物纹理上，三个被白色圆线圈出",
     "圆圈高亮叠化到重审法庭",
     "Extreme macro forensic photograph style: the white wool sleeve cuff of a formal dinner jacket under raking cool light, a scattering of a dozen tiny dark-red ink-like specks, each smaller than a millimeter, across the fabric weave; thin white circle outlines (plain geometry, no text) highlight three of the specks; the rest of the frame is soft white fabric texture, no people, no room visible. Camera: one very slow drift across the cuff. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "织物纤维的极轻摩擦；一记定音"),
    ("S38", "agnes", "缓推 push-in toward his back",
     "2009 重审宣判：被告背影肩膀僵直，法官剪影落槌——有罪",
     "槌声定格接判决卡",
     "A wood-paneled county courtroom with no windows: a defendant in a dark suit seen from behind at the defense table, shoulders rigid, a judge's silhouette high on the bench bringing a gavel down, rows of the jury box in soft shadow behind, warm ceiling light, no faces visible anywhere, no readable papers or text. Camera: one slow push-in toward the defendant's back. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "法槌一记（全片最重音）；随后绝对安静"),
    # ---------------- N06 结局与金句（7 镜）----------------
    ("S39", "graphic", "静帧信息卡",
     "判决卡：二级谋杀 + 涉枪四年 = 十九年监禁至终身",
     "判决卡切夜晚法院台阶押解背影",
     "判决卡：大标题「2009 年重审判决」，第一行「二级谋杀罪 + 涉枪加刑四年」，第二行「十九年监禁至终身」",
     "档案合上的闷响"),
    ("S40", "agnes", "跟拍下阶 tracking descent",
     "夜晚的法院台阶：戴手铐的背影被两名警察带下台阶，人群剪影里闪光灯连成一片",
     "闪光灯白闪叠化到监狱走廊",
     "Night exterior of a courthouse: a man in a dark suit and handcuffs seen entirely from behind, walked between two officers also seen from behind down broad stone steps, camera flashes popping among a crowd of faceless press silhouettes kept at the bottom of the steps, faint red and blue light on the walls, no faces visible anywhere. Camera: one slow steady tracking descent behind the group. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "快门连响；脚镣般的沉重步伐"),
    ("S41", "agnes", "缓推 follow from behind",
     "监狱走廊：实心煤渣砖墙、无窗，深色囚服的背影走向尽头的铁栅门",
     "走廊尽头叠化到积灰的录音室",
     "A long prison corridor with solid cinder-block walls on both sides, no windows, no view outside: a lone inmate in dark clothing seen from behind walking slowly away down the corridor toward a barred gate at the far end, cold fluorescent light repeating overhead, faint shadows on the floor, no faces visible. Camera: one slow push-in following him from behind. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "铁门远处合拢的回声"),
    ("S42", "agnes", "缓推 toward console",
     "废弃的录音室：蒙尘的调音台、歪挂的金唱片，一束侧窗光切开浮尘，椅子空着——声墙死了",
     "光束浮尘叠化到冬日清晨监狱墙外",
     "An abandoned 1960s recording studio control room: the large analog mixing console draped in a white dust sheet half slipped off, framed gold records hanging crooked on the faded wall with no readable text, one shaft of daylight from a high side window cutting through floating dust, an empty producer's chair turned away, no people. Camera: one very slow push-in toward the dusty console. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "尘埃般的极弱底噪；一根琴弦的残响"),
    ("S43", "agnes", "上摇 tilt up to the bird",
     "2021 年冬晨：监狱高墙外枯枝上，一只鸟起飞——他在监狱医院去世，八十一岁",
     "飞鸟升空接洛杉矶夜景俯瞰",
     "Early winter morning outside a high prison wall: bare tree branches against a pale grey sky, a single bird taking flight from the lowest branch, the concrete wall and a guard tower silhouette cropped at the edge of frame, frost glinting on the ground, quiet and cold, no people, no readable signs. Camera: one slow upward tilt from the frost to the bird. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "翅膀扑动一声；晨风"),
    ("S44", "agnes", "高空缓移 aerial drift",
     "尾声意象：洛杉矶夜景灯海之上，一道深红弧线缓缓划过天际、坠向远山——一滴血的轨迹还在飞",
     "弧线消失点叠化到大门前的花",
     "High above Los Angeles at night: the vast grid of city lights stretching to dark hills under subtle stars, and a single thin crimson light-arc traces a slow graceful parabola across the sky like a droplet's trajectory, fading toward a tiny point over the hills; no text, no landmarks, no aircraft. Camera: one slow aerial drift forward. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "配乐主题句最后一次完整出现"),
    ("S45", "agnes", "缓推 toward flowers",
     "清晨的宅邸铁门：石沿上一小束白玫瑰与几段蜡烛——致意克拉克森；提问留在片尾卡",
     "花束定格，片尾卡压上",
     "Dawn at the wrought-iron gate of a hillside estate: a small bouquet of white roses and a few candle stubs placed on the stone ledge beside the gate, soft morning light and dew on the petals, the dark mansion facade blurred far behind, no people, no readable notes or cards. Camera: one slow push-in toward the flowers. The entire clip stays in this single framing: no cut, no scene change, no camera relocation.",
     "清晨鸟鸣一两声；风声渐弱"),
]

# ---------------------------------------------------------------------------
# 画面上的文字（render.py 从 story.json 的 presentation 块读，不在 render.py 里写死）
# ---------------------------------------------------------------------------
CARD_HEADER = "案件档案 · 洛杉矶 2003—2021"
CARD_FOOTER = "公开资料摘要与示意图 · 并非原始档案影像"
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S04": ("菲尔·斯佩克特案", "2003 · 洛杉矶 阿尔汉布拉山宅邸", "「声墙」缔造者被控枪杀女演员"),
    "S10": ("菲尔·斯佩克特", "1939—2021 · 音乐制作人", "发明「声墙」，五年二十首热单"),
    "S13": ("拉娜·克拉克森", "40 岁 · 电影演员", "出演过《开放的美国学府》，事发时在俱乐部工作"),
    "S25": ("法医结论", "弹道向下倾斜 · 手腕有挣扎痕迹", "验尸官判定：他杀，而非自杀"),
    "S32": ("撞击角", "正弦值 = 血迹宽度 ÷ 血迹长度", "多条轨迹在三维中延长，汇聚出开枪位置"),
    "S35": ("枪口涡环", "燃气速度约一百米每秒", "可把反向血雾推回、甚至让液滴完全掉头"),
    "S39": ("2009 年重审判决", "二级谋杀罪 + 涉枪加刑四年", "十九年监禁至终身"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["声墙与一滴血", "菲尔·斯佩克特案 · 物理如何撕开完美伪装"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "你相信有完美的犯罪，还是只有还没追上的科学？",
    "菲尔·斯佩克特案 · 2003—2021 · 洛杉矶",
    "他一生砌起声音的墙，却挡不住一滴血说出真相",
    "资料：AP / BBC / 洛杉矶时报 / CNN / Physics of Fluids · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词），每章两三个
CAPTION_KEYWORDS = [
    "声墙", "十八个血点", "意外自杀", "我想我杀了人", "他杀",
    "十比二", "流审", "撞击角", "涡环", "一百米每秒",
    "有罪", "十九年监禁至终身", "说出真相",
]
# 逐镜标签覆盖：默认 agnes 镜头标「AI动画情景重现 · 非新闻影像」
LABEL_OVERRIDES = {
    "S03": "物理示意动画 · 教学可视化",
    "S24": "物理示意动画 · 教学可视化",
    "S31": "物理示意动画 · 教学可视化",
    "S34": "物理示意动画 · 教学可视化",
    "S44": "物理示意动画 · 教学可视化",
    "S19": "AI动画示意 · 非证物实拍",
    "S21": "AI动画示意 · 非证物实拍",
    "S23": "AI动画示意 · 取证演示",
    "S26": "AI动画示意 · 取证演示",
    "S27": "AI动画示意 · 取证演示",
    "S33": "AI动画示意 · 取证演示",
    "S36": "AI动画示意 · 取证演示",
    "S37": "AI动画示意 · 取证演示",
    "S28": "AI动画示意 · 非庭审影像",
    "S29": "AI动画示意 · 非庭审影像",
    "S38": "AI动画示意 · 非庭审影像",
    "S40": "AI动画重现 · 非新闻影像",
    "S41": "AI动画示意 · 非监狱影像",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S07", "phone"),
    ("S12", "machine"),
    ("S19", "paper"),
    ("S21", "paper"),
    ("S23", "machine"),
    ("S26", "keys"),
    ("S27", "machine"),
    ("S28", "paper"),
    ("S33", "machine"),
    ("S34", "machine"),
    ("S36", "machine"),
    ("S38", "press"),
    ("S40", "press"),
    ("S42", "keys"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "音乐天才在城堡宅邸杀人，枪擦得干干净净——栽在十八个血点上",
    "他对警察说「是她自己开的枪」：六年后，流体力学替他定了罪",
    "「声墙」之父的完美谎言，被一组物理方程撕碎｜菲尔·斯佩克特案",
]
HOOK = ("他把现场擦得越干净，物理就把他记得越清楚：十八个不足一毫米的血点，"
        "用流体力学方程算出了那一夜开枪的位置。")
GOLDEN_LINES = [
    "他一生砌起声音的墙，最后却挡不住一滴血说出真相。",
    "没有完美的现场，只有还没算完的方程。",
    "你相信有完美的犯罪，还是只有还没追上的科学？评论区聊聊。",
]
DESCRIPTION = ("2003年2月3日，洛杉矶山上的城堡宅邸，传奇音乐制作人与四十岁的女演员，一声枪响。"
               "他把枪擦干净、把现场擦洗得一尘不染，还准备了最无懈可击的证词——唯独没有算过物理。"
               "撞击角方程、一百米每秒的枪口涡环、十八个不足一毫米的血点：科学把「完美伪装」一层层撕开。"
               "本片画面均为AI动画情景重现，不针对真实人物影像。"
               "你觉得在绝对的硬核科学面前，谎言还能撑多久？")
QUESTION = "你相信有完美的犯罪，还是只有还没追上的科学？"
HASHTAGS = ["#菲尔斯佩克特案", "#法医科学", "#血迹形态分析", "#流体力学",
            "#悬疑", "#科普", "#真实案件", "#声墙"]

GRID = 4           # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 7  # 每个 Agnes 镜头实际请求的时长（169 帧 @ 24 fps）
SEED_BASE = 20260925  # 开工日 2026-09-25，seed 可追溯


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
    story.setdefault("_scaffold", {})[
        "note"] = (
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
    for cid, title, text in CHAPTERS:
        print(f"  {cid}《{title}》{len(text)} 字")
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

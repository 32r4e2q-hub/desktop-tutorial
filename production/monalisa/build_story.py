#!/usr/bin/env python3
"""《蒙娜丽莎失窃案：一枚左手拇指印》的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
样板是 production/gilgo/build_story.py —— 一部已经出片、已经过三轮复审的成片）。

用法::

    python3 production/monalisa/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/monalisa/build_story.py --script   # 生成 抖音脚本.md（3 标题 / 核心爆点 / 四列分镜表 / 金句）
    python3 production/monalisa/build_story.py --publish  # 生成 抖音发布文案.md（标题 / 介绍 / 提问读者一句话 / 话题）

本片的事实修正（用户在开工时确认「按史实改写」，2026-09-26）：
用户提纲里的「工作服口袋里的白杨木纤维与画板比对」在任何史料中都查不到（1913 年《纽约时报》《华盛顿晚星报》
原始报道、Hoobler《巴黎罪案》、维基百科均无此记载），不写成事实。片中的「微观物证」换成有据可查的两样：
① 玻璃罩上的**左手拇指印**——警方档案里早有他的指纹，但贝蒂荣的档案只按右手拇指分类，28 个月没对上，被捕后一比即中；
② **白杨木画板**本身——背面的卢浮宫印章与编号、顶端的裂缝、四百年形成的细密裂纹网，让乌菲兹馆长确认真迹。
用户提纲里的「死不认账」也按史实改成「爱国说辞」：他承认拿了画，却辩称是替意大利讨回被拿破仑抢走的国宝。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"

TITLE = "蒙娜丽莎失窃案：一枚左手拇指印"

# 画风与吉尔戈（长岛连环案）逐字同一套：手绘 2D 动画纪录片、图像小说质感、柔和赛璐璐阴影、压暗的冷色调；
# 只把「世界描述」换成 1911—1914 年的巴黎与佛罗伦萨，并且**刻意写得很短、不列具体地点**——
# 吉尔戈三轮复审的教训：世界描述里写到的地点/道具会被塞进任何不相干的镜头（郊区长出摩天楼）。
# 地点一律在每镜提示词里钉死。蒙娜丽莎本身的正脸从不交给模型画（AI 版名画必然走样），只出现背面、红布包、
# 反光的玻璃、远处小而模糊的画框、或局部裂纹微距。
STYLE_PREFIX = (
    "Stylized 2D animated documentary illustration with hand-painted graphic-novel textures and soft "
    "cel shading, Belle Epoque Paris and Florence between 1911 and 1914 with period-accurate clothing and "
    "interiors, gas lamps and early electric light; horizontal 16:9 cinematic composition, muted palette of "
    "slate blue, steel grey, parquet ochre and warm gas-lamp amber practical light, overcast Paris daylight or "
    "cool interior practical light, restrained procedural true-crime mood, no horror excess; every character is "
    "shown only from behind, in silhouette, or as hands and props - never a clear frontal face; absolutely no "
    "readable text, letters, numbers, logos or signage anywhere inside the frame; one single continuous smooth "
    "slow camera move per shot exactly as directed. "
)

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, invented headlines, logos, brand marks, "
    "watermark, subtitles, on-screen caption, photorealistic face, recognizable real person likeness, "
    "frontal face close-up, eyes visible in detail, distorted portrait face inside a painting, melting painted "
    "face, blood, gore, wound, corpse, violence, assault, weapon attack, gun, firearm, nudity, horror monster, "
    "ghost, jump scare, 3D render look, plastic CGI, distorted anatomy, deformed hands, extra fingers, extra "
    "limbs, duplicated people, changing face, morphing objects, teleportation, jitter, flicker, whip pan, fast "
    "zoom, jump cut, split screen, collage, modern clothing, modern cars, glass pyramid, smartphone, neon"
)

# 事实边界与红线：每一条都会印在 抖音脚本.md 的「发布前自查」里。
PRINCIPLES = [
    "全部 Agnes 镜头为风格化 2D 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，不冒充历史照片、档案或原作影像",
    "《蒙娜丽莎》原作不交给 AI 重画：只出现画板背面、红布包、反光的玻璃罩、远处小而模糊的画框、局部裂纹微距，避免 AI 版名画走样",
    "真实人物（佩鲁贾、贝蒂荣、杰里、波吉、毕加索、达芬奇）只以背影、剪影、手部出现，不用 AI 生成的脸冒充本人",
    "每一句事实都能指到 sources 里的一条公开来源；用户提纲中查无出处的「白杨木纤维比对」不写成事实，改为史料可证的左手拇指印与画板裂纹鉴定",
    "史料有分歧处不写死：他是前一晚藏进库房还是当天清早混进来、写信时人在巴黎还是意大利、被捕是 12 月 11 日还是 12 日——解说一律用不矛盾的说法",
    "「爱国」是佩鲁贾本人的说辞，片中明确用史实反驳（达芬奇本人带画入法、他索价五十万里拉、写信给父亲说要发大财），不替他美化",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写",
    "人工检视 qa/ 接触表与逐帧指标，露脸、畸变、伪文字、中途换场的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

# 每条事实的公开来源（usage 写清支撑了哪几句）。
SOURCES = [
    {"id": 1, "url": "https://www.nytimes.com/1913/12/15/archives/reading-mona-lisas-riddle-london-recalls-various-attempts-to.html",
     "usage": "1913 年原始报道：贝蒂荣手里有佩鲁贾 1908、1909 年两套指纹；部门共 75 万份犯罪档案；分类只用右手拇指，玻璃上唯一清晰的是左手拇指印；被捕后比对「每一处都吻合」"},
    {"id": 2, "url": "https://chroniclingamerica.loc.gov/lccn/sn83045462/1913-12-13/ed-1/seq-4/ocr.txt",
     "usage": "《华盛顿晚星报》1913-12-13：画上有卢浮宫印章、背面有修补痕迹；他坚称是为拿破仑掠夺意大利而「爱国复仇」；指纹与画框和玻璃上的指纹「完全相同」"},
    {"id": 3, "url": "https://www.vanityfair.com/culture/2009/05/mona-lisa-excerpt200905",
     "usage": "Hoobler《巴黎罪案》节选：周一闭馆只剩工人、员工穿白大褂、四个挂钩、木板无法卷起、楼梯间拆框、门锁住、水管工索维用钳子开门、次日画家发现、毕加索被盘问、边境查箱"},
    {"id": 4, "url": "https://en.wikipedia.org/wiki/Vincenzo_Peruggia",
     "usage": "1881 年生、玻璃工；参与制作蒙娜丽莎的玻璃箱；周一早上约 7 点穿白罩衫进馆；四个铁钩、服务楼梯、水管工开门；警探两次上门，趴在藏画的桌子上写完报告；给父亲写信说要发大财；判一年零十五天、上诉后服刑七个月"},
    {"id": 5, "url": "https://it.wikipedia.org/wiki/Vincenzo_Peruggia",
     "usage": "油漆工（imbianchino）出身；受雇清洁名画并加装玻璃；1914-06-05 判一年零十五天，07-29 上诉减为七个月八天；由宪兵在旅馆房间带走；要求画留在意大利；达芬奇把画卖给弗朗索瓦一世"},
    {"id": 6, "url": "https://en.wikipedia.org/wiki/Mona_Lisa",
     "usage": "画家贝鲁次日报失；卢浮宫闭馆一周调查；毕加索被传讯；佩鲁贾参与制作玻璃箱；乌菲兹展出两周余，1914-01-04 回到卢浮宫"},
    {"id": 7, "url": "https://slate.com/human-interest/2011/08/who-stole-the-mona-lisa-the-world-s-most-famous-art-heist-100-years-on.html",
     "usage": "他做过蒙娜丽莎的玻璃框；警探上门没发现画；有两次前科、警方存有指纹；贝蒂荣被称为「现实中的法国福尔摩斯」，只登记右手指纹"},
    {"id": 8, "url": "https://www.latimes.com/entertainment/la-xpm-2011-aug-17-la-et-mona-lisa-20110817-story.html",
     "usage": "意大利油漆工；化名 Leonard V. 写信给佛罗伦萨画商；毕加索与阿波利奈尔被盘问；警方有他的左手拇指印、档案按右手分类；白木箱假底，箱内有工具、衣服和一把曼陀林；Valfierno 主谋说是编造"},
    {"id": 9, "url": "https://www.history.com/articles/the-heist-that-made-the-mona-lisa-famous",
     "usage": "他参与制作画的保护框；卢浮宫一周后才重新开放；开价五十万里拉；在旅馆被捕；达芬奇 1516 年把画带到法国、弗朗索瓦一世合法买下；爱国辩护；1914 年 1 月画回卢浮宫"},
    {"id": 10, "url": "https://theweek.com/articles/481790/stealing-mona-lisa",
     "usage": "信署名「Leonardo」；要五十万里拉「费用」；Tripoli-Italia 旅馆三楼 20 号房；床下拖出箱子；波吉根据裂纹图案确认真迹"},
    {"id": 11, "url": "https://www.theguardian.com/theguardian/2011/dec/15/archive-leonardo-da-vinci-mona-lisa-1913",
     "usage": "《曼彻斯特卫报》1913-12-15 档案：杰里的叙述、红布包着画、带到乌菲兹验明真迹"},
    {"id": 12, "url": "https://www.washingtonpost.com/history/2019/10/20/how-theft-mona-lisa-made-it-worlds-most-famous-painting/",
     "usage": "周一闭馆、白色工作服、方形大厅、木板画、玻璃罩，藏在罩衫下走出卢浮宫"},
    {"id": 13, "url": "https://www.encyclopedia.com/social-sciences-and-law/law/crime-and-law-enforcement/fingerprint",
     "usage": "玻璃上清晰的指纹；贝蒂荣数月比对无果；被捕后指纹吻合；他的右手拇指指纹一直在档案里"},
    {"id": 14, "url": "https://www.artchive.com/artwork/mona-lisa-leonardo-da-vinci-1503-1506/",
     "usage": "白杨木板油画 77×53 厘米；木板对湿度敏感、会拱起开裂；顶部一道约 11 厘米的裂缝，背面曾用蝴蝶形木楔加固；画框限制木板活动造成龟裂"},
    {"id": 15, "url": "https://www.noiser.com/short-history-of/how-a-daring-heist-made-the-mona-lisa-the-most-famous-painting-in-the-world",
     "usage": "边境封锁、搜查船与火车；玻璃框在楼梯间找到、指纹无匹配；画背面有正确的卢浮宫编号"},
    {"id": 16, "url": "https://www.aljazeera.com/news/2025/10/21/mona-lisa-to-the-nazis-robbed-often-why-latest-louvre-theft-is-different",
     "usage": "29 岁；水管工把他当同事帮忙开门；在佛罗伦萨旅馆被捕；1914-01-04 画回卢浮宫；画是达芬奇在法国完成并卖给法国王室"},
    {"id": 17, "url": "https://www.britannica.com/today-in-history/August-21-The-Mona-Lisa-Theft",
     "usage": "周一闭馆；装扮成工人；把画藏在罩衫下；水管工开门；一整天后才有人注意到四个空挂钩；佩鲁贾是油漆工、参与安装玻璃罩"},
    {"id": 18, "url": "https://www.historyhit.com/culture/theft-mona-lisa/",
     "usage": "卢浮宫零工；罩衫；楼梯底门锁住、钥匙打不开、拧下门把手；水管工索维用钳子开门；杰里带乌菲兹馆长波吉会面，劝他把画留下鉴定，当天被捕"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。合计 773 字（不含标点）/ 875 字（含标点），收紧停顿后 177.59 秒，变速 1.057。
CHAPTERS = [
    ("N01", "黄金开头：名画蒸发",
     "一九一一年，如今全世界最有名的那幅画，在卢浮宫里凭空消失了。偷走它的不是国际大盗，而是一个意大利油漆工：他把画往白大褂里一裹，大摇大摆走出了大门。更离谱的是，他的指纹早就在警察档案里，却让他逍遥了二十八个月。今天一口气讲清楚，蒙娜丽莎失窃案。"),
    ("N02", "潜伏计划：老实零工",
     "先说这个人。文森佐·佩鲁贾，油漆工出身，在巴黎打零工，还在卢浮宫干过一阵：给名画装玻璃罩，蒙娜丽莎那个罩子，他也参与过。他看上去老实巴交，可这份活让他摸清了三件事：画只挂在四个铁钩上；周一闭馆，馆里只剩工人；而工人，人人都穿白大褂。"),
    ("N03", "作案手法：闭馆日",
     "一九一一年八月二十一日，星期一清早，佩鲁贾穿着白大褂混进馆里。方形大厅四下无人，他把画从铁钩上摘下，躲进员工楼梯间，拆掉玻璃罩和画框，只剩一块白杨木板。可楼梯底下的门锁着！一个水管工路过，把他当成同事，顺手帮他开了门。直到第二天，来写生的画家才发现：墙上只剩四个铁钩。"),
    ("N04", "破案关键（上）：左手与右手",
     "卢浮宫闭馆一周，边境封锁，连毕加索都被叫去问话。现场最硬的线索：玻璃罩上一枚清晰的拇指印。人称法国福尔摩斯的贝蒂荣，手握七十五万份档案，佩鲁贾有前科，指纹就在里面，可就是没对上。因为档案只按右手拇指分类，而玻璃上的，偏偏是左手。更讽刺的是，警探上门问话时，就趴在藏画的那张桌子上写完了笔录。"),
    ("N05", "破案关键（下）：画板上的裂纹",
     "两年后，他憋不住了，化名莱昂纳多，联系佛罗伦萨的画商，开价五十万里拉，把画带回了意大利。画商拉上乌菲兹美术馆馆长，来到他住的旅馆。他从箱子夹层里捧出一个红布包。馆长把画翻过来：白杨木画板背面，卢浮宫的印章和编号全对得上。再比对照片：顶上那道裂缝、细密的裂纹网，全部吻合。这是四百年里油彩干缩、木板胀缩撑出来的，没人造得出第二张。很快，警察敲开了他的房门。"),
    ("N06", "狡辩、结局与金句",
     "被捕后，他理直气壮：我是爱国！这画是拿破仑从意大利抢走的！可历史当场打脸：这幅画是达芬奇自己带去法国的，比拿破仑出生早了两百多年。何况他开口就要五十万，还写信跟父亲说要发大财。而那枚左手拇指印一比，分毫不差。一九一四年一月，蒙娜丽莎回到卢浮宫，佩鲁贾只坐了七个月牢。他骗过了警察，骗过了档案，却骗不过一枚指纹，和画上的裂纹。你觉得，他是爱国，还是爱钱？评论区聊聊。"),
]
HOLD = " The entire clip stays in this single framing: no cut, no scene change, no camera relocation."

# 每一镜：(id, kind, 运镜, 叙事职责, 衔接方式, 英文提示词 或 信息卡说明, 音效/备注)
# 45 镜 = 38 个 Agnes 动画镜头 + 7 张信息卡，按成片顺序编号，**每个镜头只出现一次**。
# 每条提示词：先钉死唯一场景（from the very first frame to the last）→ 单一运镜 → HOLD 句；
# 人只给背影/剪影/手；画面里没有可读文字；《蒙娜丽莎》正面从不清楚出现（玻璃反光、背面、红布包、远景小画框）。
SHOTS = [
    # ---------------- N01 黄金开头（7 镜）----------------
    ("S01", "agnes", "缓慢推近 slow push-in",
     "0–5 秒钩子：卢浮宫大厅墙上，名画原位只剩四个铁钩和一块颜色略浅的长方形印子",
     "推到铁钩近景，硬切白大褂背影",
     "Interior of a grand museum gallery in 1911, framed on one section of dark red damask wall from the very first frame to the last: between two large gilded frames holding dark, shadowy landscape paintings there is an empty gap - only four bare black iron hooks and a slightly paler rectangle on the fabric where a small painting used to hang, soft skylight from above, dust motes drifting in the light; no people. Camera: one slow push-in toward the four empty hooks." + HOLD,
     "开口前 0.3 秒一声空旷回响；低频心跳垫底；字幕高亮无"),
    ("S02", "agnes", "背后跟拍 follow from behind",
     "「偷走它的不是国际大盗，而是一个意大利油漆工」：白大褂、鸭舌帽的矮个子背影，走在空荡的长廊里",
     "背影走远，接塞纳河畔出门",
     "A long museum gallery with a polished parquet floor and tall arched windows in early morning light, 1911, framed down the middle of the gallery from the very first frame to the last: a short, wiry workman in a loose white smock and a flat cap, a small paint-stained canvas bag over his shoulder, walks away from camera, back to camera the whole time; no other people, no faces. Camera: one slow steady follow from behind at walking pace." + HOLD,
     "皮鞋踩木地板的回声；字幕高亮「油漆工」"),
    ("S03", "agnes", "固定中景 static medium",
     "「他把画往白大褂里一裹，大摇大摆走出了大门」：清晨塞纳河畔，白大褂背影腋下夹着白布包走出侧门",
     "背影走出画面，接档案室",
     "Early morning on a quiet cobbled Paris quay beside the long classical stone facade of an old palace, 1911, framed on one small side doorway in the stone wall from the very first frame to the last: a short workman in a white smock, seen from behind, steps out of the doorway carrying a flat rectangular bundle wrapped in white cloth under his arm and strolls away unhurried along the pavement, pale mist over the river, a horse-drawn cab waiting far down the street; no faces. Camera: locked-off medium wide from behind; only the figure moves away." + HOLD,
     "街头马蹄声、远处汽笛；音乐第一次进"),
    ("S04", "agnes", "推轨横移 lateral dolly",
     "「他的指纹早就在警察档案里」：警察局档案室成墙的木制卡片抽屉，一只手拉开抽屉，卡片上只有指纹墨印",
     "抽屉拉开的一刻切出租屋窗口",
     "A police identification archive in 1911 Paris, framed on a wall of small wooden card-catalogue drawers from floor to ceiling under a green-shaded lamp from the very first frame to the last: a clerk's hand in a black sleeve garter pulls one drawer open, revealing tightly packed pale index cards that carry only smudged inked fingerprints and no writing; no faces, no readable labels. Camera: one slow lateral dolly along the drawers, ending on the open drawer." + HOLD,
     "抽屉木轨摩擦 + 卡片沙沙声（sfx paper）"),
    ("S05", "agnes", "缓慢推近 slow push-in",
     "「却让他逍遥了二十八个月」：黄昏，巴黎出租屋小窗前的男人剪影，抽着烟望向屋顶与烟囱",
     "烟雾散开，接塞纳河航拍",
     "Dusk inside a cramped rented room in working-class Paris, 1911, framed on one small open window from the very first frame to the last: a short man seen from behind in silhouette sits at the window sill smoking a cigarette, the grey zinc rooftops and chimney pots of Paris stretching beyond under a violet sky, a single oil lamp glowing beside him; no faces. Camera: one slow push-in toward the window over his shoulder." + HOLD,
     "远处手风琴、城市暮色底噪；字幕高亮「二十八个月」"),
    ("S06", "agnes", "低空航拍前飞 low aerial drift",
     "「今天一口气讲清楚」：1911 年清晨的塞纳河与卢浮宫沿河长廊，石桥、马车、驳船",
     "推向宫殿，接案件名片卡",
     "Low aerial view skimming above the river Seine at dawn in 1911, framed along the water from the very first frame to the last: the long grey stone riverside wing of an old palace runs along the left bank of the frame, a stone bridge with horse-drawn cabs crossing ahead, a barge gliding on the water, soft mist and pale gold light, chimney smoke over mansard roofs; no modern buildings. Camera: one slow forward drift along the river." + HOLD,
     "河风 + 低音鼓点；「讲清楚」落点后留半拍"),
    ("S07", "graphic", "信息卡 static card",
     "案件名片：案名、时间地点、失踪时长（不依赖 AI 拼字）",
     "卡片硬切人物档案",
     "案件名片（文案见 CARDS）",
     "卡片入场「咔」一声；解说念到「蒙娜丽莎失窃案」时出现"),
    # ---------------- N02 潜伏计划（7 镜）----------------
    ("S08", "graphic", "档案卡 static card",
     "人物档案卡：姓名、出身、年龄、在卢浮宫做过的活（公开史料）",
     "卡片硬切巴黎工人街",
     "人物档案（文案见 CARDS）",
     "打字机式逐行出现；不放本人照片"),
    ("S09", "agnes", "横向跟拍 lateral track",
     "「在巴黎打零工」：清晨巴黎工人街区，扛着木梯、拎着油漆桶的背影",
     "背影转过街角，接玻璃工作台",
     "Early morning on a narrow working-class street in Paris, 1911, framed on the wet cobbled pavement from the very first frame to the last: a short workman in a paint-spattered smock and flat cap, seen from behind, carries a wooden ladder on his shoulder and a paint bucket in one hand, walking past shuttered shopfronts with blank signboards and a gas lamp; no faces, no readable signs. Camera: one smooth lateral tracking move keeping pace with him from behind and slightly to the side." + HOLD,
     "油漆桶把手吱呀、清晨鸽子"),
    ("S10", "agnes", "微距焦点转移 macro rack focus",
     "「给名画装玻璃罩」：工作台上两双手把一整块玻璃嵌进木制箱框",
     "玻璃反光接墙上的玻璃罩",
     "Close-up on a glazier's wooden workbench in a museum workshop lit by a tall window, 1911, framed on the bench top from the very first frame to the last: two pairs of hands in rolled-up white sleeves lower a large clean pane of glass into the front of a heavy wooden shadow-box frame, a putty knife and small brass screws on the bench, soft reflections sliding across the glass; no faces. Camera: locked-off macro with a gentle rack focus from the tools to the glass." + HOLD,
     "玻璃轻碰木框的清脆声；字幕高亮「玻璃罩」"),
    ("S11", "agnes", "缓慢横移 slow lateral slide",
     "「蒙娜丽莎那个罩子，他也参与过」：墙上一只沉重的玻璃罩，玻璃满是天窗白光看不清里面，一只白袖子的手用布擦玻璃",
     "白光一闪接员工走廊",
     "A museum gallery wall in 1911, framed on one heavy glass-fronted wooden case hanging on dark red damask from the very first frame to the last, seen at a steep oblique angle so the glass is filled with a bright white reflection of the skylight and nothing inside is visible; a workman's hand in a white sleeve wipes the glass with a folded cloth in slow circles; no faces. Camera: one slow lateral slide along the wall toward the case." + HOLD,
     "布擦玻璃的吱吱声"),
    ("S12", "agnes", "缓慢上摇 slow tilt up",
     "「他看上去老实巴交，可这份活让他摸清了三件事」：昏暗的员工走廊，白大褂背影坐在木箱上啃面包，慢慢抬头望向尽头亮着的画廊门口",
     "抬头的视线接铁钩特写",
     "A dim back-of-house service corridor inside a museum, 1911, plain plaster walls and stacked wooden crates, framed down the corridor from the very first frame to the last: a short workman in a white smock, seen from behind, sits on a crate eating bread from a paper wrapper, then slowly lifts his head toward a bright doorway at the far end that opens onto a gallery; no faces. Camera: one slow tilt up from his boots to the lit doorway beyond him." + HOLD,
     "音乐转暗，只剩低音；「三件事」处停半拍"),
    ("S13", "agnes", "微距横移 macro slide",
     "「画只挂在四个铁钩上」：微距，墙上的黑色铁钩托住镀金画框的底边，再滑到下一个铁钩",
     "滑到第二个铁钩切闭馆长廊",
     "Extreme close-up on a museum wall in 1911, framed on the bottom edge of a heavy carved gilded frame from the very first frame to the last: a simple black iron hook driven into the wall holds the frame, and a second identical hook sits a little further along, old damask fabric texture behind, warm skylight; the painting itself stays out of frame above. Camera: one slow macro slide along the bottom edge of the frame from one hook to the next." + HOLD,
     "金属轻响；字幕高亮「四个铁钩」"),
    ("S14", "agnes", "固定大全景 static wide",
     "「周一闭馆，馆里只剩工人；而工人，人人都穿白大褂」：空荡的长廊，几个一模一样的白大褂背影扛梯子、提水桶、拖地",
     "工人走远，硬切黎明的工人入口",
     "Wide view down a long, empty museum gallery on a closed Monday morning in 1911, parquet floor, dust sheets over a bench, tall windows with pale light, framed from one end of the gallery from the very first frame to the last: four workmen in identical white smocks, all seen from behind and small in the frame, carry a ladder and buckets away along the gallery while one mops the floor; no visitors, no faces. Camera: locked-off wide; only the workmen move." + HOLD,
     "水桶、拖把、远处回声；字幕高亮「白大褂」"),
    # ---------------- N03 作案手法（7 镜）----------------
    ("S15", "agnes", "固定中景 static medium",
     "「1911 年 8 月 21 日，星期一清早，佩鲁贾穿着白大褂混进馆里」：黎明，宫殿侧面的工人入口，几个白大褂背影鱼贯而入，最后一个是矮小的身影",
     "门里的灯光接方形大厅",
     "Dawn at a plain side entrance of a vast classical stone palace on a quiet Paris street, 1911, framed on one heavy wooden service door standing open with lamplight inside from the very first frame to the last: a few workmen in white smocks and caps walk in one after another, all seen from behind, the last one a short, slight man; wet cobbles, blue morning shadow; no faces. Camera: locked-off medium wide from behind the workers." + HOLD,
     "清晨钟声一下；日期字幕「1911.08.21」由后期添加"),
    ("S16", "agnes", "缓慢横摇 slow pan",
     "「方形大厅四下无人」：1911 年的方形大厅，画作从腰线挂到檐口，天窗倾泻晨光，空无一人",
     "横摇停在墙中段，接摘画",
     "The square grand salon of a museum in 1911, framed from its doorway from the very first frame to the last: walls of dark red damask hung densely with gilded-frame old-master paintings from waist height up to the cornice, a glass skylight ceiling pouring soft morning light onto an empty parquet floor, a single velvet bench in the middle; the paintings are dim, darkened landscapes too small to make out; no people. Camera: one slow pan across the room from left to right." + HOLD,
     "空旷房间的嗡鸣"),
    ("S17", "agnes", "低角度固定 low-angle static",
     "「他把画从铁钩上摘下」：侧面低角度，一双白袖子的手把沉重的玻璃罩画框从墙上抬下，玻璃满是白光看不见画面",
     "画框落下，接楼梯间俯拍",
     "Low-angle side view in a museum salon in 1911, framed on one section of damask wall from the very first frame to the last: two hands in white smock sleeves lift a heavy glass-fronted framed case off four iron hooks and lower it toward the floor; the glass front catches the white glare of the skylight so no image is visible, only reflections; the workman is cropped at the shoulders; no faces. Camera: locked-off low angle; only the hands and the case move." + HOLD,
     "铁钩刮过的金属声"),
    ("S18", "agnes", "俯拍固定 overhead static",
     "「躲进员工楼梯间，拆掉玻璃罩和画框」：昏暗的石砌楼梯间平台，画框背面朝上，双手拧螺丝，玻璃罩靠在墙边",
     "拆下的画框接白杨木板信息卡",
     "Overhead view into a narrow, dim stone service stairwell in 1911, a single slit window of grey light, framed on the landing from the very first frame to the last: a pair of hands in white sleeves works a screwdriver around the back of a heavy gilded frame lying face-down on the stone floor, an empty glass case already leaning against the wall beside it; no faces, the front of any painting is never visible. Camera: locked-off overhead; only the hands move." + HOLD,
     "螺丝刀吱嘎、呼吸声；节奏加快"),
    ("S19", "graphic", "信息卡 static card",
     "白杨木板卡：蒙娜丽莎是画在白杨木板上的油画，77×53 厘米，卷不起来",
     "卡片硬切锁住的门",
     "白杨木板（文案见 CARDS）",
     "木头敲击声「咚」；字幕高亮「白杨木板」"),
    ("S20", "agnes", "固定中景 static medium",
     "「可楼梯底下的门锁着！一个水管工路过，把他当成同事，顺手帮他开了门」：石楼梯底部没了门把手的木门，背着工具袋的水管工用钳子把门打开",
     "门外的日光接画家发现空墙",
     "The bottom of a narrow stone service staircase in 1911, framed on a plain wooden door with a missing doorknob from the very first frame to the last: a man in a white smock hugging a flat white-wrapped bundle to his chest waits beside the door as an older plumber with a leather tool bag, seen from behind, fits a pair of pliers into the empty knob hole and swings the door open onto a bright courtyard; no faces. Camera: locked-off medium shot from behind both men." + HOLD,
     "门锁咔哒（sfx keys）；字幕高亮「水管工」"),
    ("S21", "agnes", "缓慢推近 slow push-in",
     "「直到第二天，来写生的画家才发现：墙上只剩四个铁钩」：前景画家的画架，背影放下画笔，远处墙上两幅暗画之间一块空当，四个铁钩",
     "推到空当，章节停顿",
     "A museum salon the next morning in 1911, framed past a painter's easel toward the far wall from the very first frame to the last: the wooden easel with a half-finished canvas stands in the foreground, a painter in a long coat seen from behind lowers his brush, and beyond him on the damask wall between two dark gilded frames there is an empty gap with four bare iron hooks; soft skylight; no faces. Camera: one slow push-in past the easel toward the empty hooks." + HOLD,
     "画笔落地一声，音乐骤停"),
    # ---------------- N04 破案关键（上）：左手与右手（7 镜）----------------
    ("S22", "agnes", "横移 lateral dolly",
     "「卢浮宫闭馆一周，边境封锁」：1911 年边境火车站台，戴军帽的海关人员翻检旅客的箱子",
     "箱盖合上，接问询室",
     "A steam-filled railway platform at a French border station in 1911, framed along a long wooden inspection table from the very first frame to the last: customs officers in dark uniforms and kepis, seen from behind, open travellers' trunks and suitcases and lift out folded clothes and picture-sized parcels, a steam locomotive waiting behind; no faces, no readable signs. Camera: one slow lateral dolly along the inspection table." + HOLD,
     "蒸汽机车泄气声、箱扣弹开"),
    ("S23", "agnes", "过肩固定 over-the-shoulder static",
     "「连毕加索都被叫去问话」：警局问询室，一个黑发年轻人的背影坐在桌前，对面警探的脸隐在台灯后的阴影里",
     "烟雾接指纹微距",
     "A 1911 Paris police interview office, framed over the shoulder of a seated young man from the very first frame to the last: the young man with short dark hair in a painter's jacket sits with his back to camera at a plain wooden desk, facing a detective whose face is lost in shadow behind a green-shaded lamp, cigarette smoke curling, a filing cabinet and a barred window; no visible faces. Camera: locked-off medium shot over the young man's shoulder." + HOLD,
     "钢笔敲桌、低声问话（不可辨）"),
    ("S24", "agnes", "微距焦点转移 macro rack focus",
     "「现场最硬的线索：玻璃罩上一枚清晰的拇指印」：戴手套的手把玻璃片斜对台灯，撒了粉的拇指印显出螺旋纹路",
     "指纹纹路接档案大厅",
     "Macro close-up in a 1911 forensic office, framed on a pane of glass under a brass desk lamp from the very first frame to the last: a gloved hand tilts the glass and a single clear thumbprint dusted with grey powder appears on it, its whorl ridges catching the light; a soft brush and a magnifying glass lie blurred on the desk below; no faces. Camera: one slow macro rack focus from the brush to the thumbprint." + HOLD,
     "细刷扫粉的沙沙声；字幕高亮「拇指印」"),
    ("S25", "agnes", "缓慢后拉 slow pull-back",
     "「人称法国福尔摩斯的贝蒂荣，手握七十五万份档案」：巨大的档案大厅，顶到天花板的卡片柜，前景一个大胡子的背影",
     "后拉到全景，接翻指纹卡",
     "A vast 1911 police identification bureau in Paris, framed down one long aisle from the very first frame to the last: tall wooden cabinets of card drawers rise to the ceiling on both sides, clerks on rolling ladders in the distance, and in the foreground a stout bearded man in a dark frock coat stands with his back to camera, hands clasped behind him, surveying the files; warm electric lamps; no faces, no readable labels. Camera: one slow pull-back revealing the scale of the archive." + HOLD,
     "大厅回声、远处抽屉开合；字幕高亮「七十五万份」"),
    ("S26", "agnes", "俯拍固定 overhead static",
     "「佩鲁贾有前科，指纹就在里面，可就是没对上」：灯下双手一张张翻看指纹卡，放大镜扫过，又放到一边",
     "卡片越堆越高，接左右手信息卡",
     "Overhead view of a desk under a lamp in a 1911 identification bureau, framed on the desk top from the very first frame to the last: a clerk's hands leaf through a tall stack of pale cards bearing only inked fingerprints, holding a magnifying glass over each one and then setting it aside, the discarded cards piling up; no writing on the cards, no faces. Camera: locked-off overhead; only the hands and cards move." + HOLD,
     "卡片翻动（sfx paper）"),
    ("S27", "graphic", "对比卡 static card",
     "左右手对比卡：玻璃上是左手拇指印，档案只按右手拇指分类",
     "卡片硬切出租屋",
     "左手与右手（文案见 CARDS）",
     "「偏偏是左手」处低音「咚」；字幕高亮「右手拇指」「左手」"),
    ("S28", "agnes", "固定大全景 static wide",
     "「更讽刺的是，警探上门问话时，就趴在藏画的那张桌子上写完了笔录」：巴黎出租屋，戴圆顶礼帽的警探背影伏在小木桌上写字，桌下一块深深的暗格阴影",
     "章节停顿后切烛光下写信",
     "A cramped single rented room in working-class Paris, 1911, lit by one window, framed from the doorway from the very first frame to the last: a detective in a bowler hat and overcoat, seen from behind, leans over a small plain wooden table writing in a notebook, while the short tenant stands by a washbasin with his back to camera; under the table a deep shadow hides a boxed-in space; an iron bed and a trunk; no faces. Camera: locked-off wide from the doorway." + HOLD,
     "铅笔沙沙声，音乐只剩一个持续低音"),
    # ---------------- N05 破案关键（下）：画板上的裂纹（9 镜）----------------
    ("S29", "agnes", "微距推近 macro push-in",
     "「两年后，他憋不住了，化名莱昂纳多，联系佛罗伦萨的画商」：烛光下一只手用蘸水笔写信，纸上只有看不清的笔画",
     "笔尖停住，接开价卡",
     "Close-up at night in a small rented room, framed on a sheet of paper on a wooden table from the very first frame to the last: a man's hand writes a letter with a dip pen by the light of a single candle, the lines on the paper are only loose illegible flourishes, an envelope and an inkwell beside it, the flame flickering gently; no faces, no readable words. Camera: one slow macro push-in toward the moving pen nib." + HOLD,
     "笔尖划纸（sfx paper）"),
    ("S30", "graphic", "信息卡 static card",
     "开价卡：化名「莱昂纳多」，开价 50 万里拉，条件是画要留在意大利",
     "卡片硬切火车车厢",
     "开价（文案见 CARDS）",
     "数字「50万里拉」放大跳出；字幕高亮「五十万里拉」"),
    ("S31", "agnes", "固定 static",
     "「把画带回了意大利」：1913 年的三等车厢，行李架上一只白色木箱，窗外阿尔卑斯雪山掠过，男人背影靠窗",
     "车窗外的雪光接佛罗伦萨街头",
     "Inside a wooden third-class railway compartment in 1913, framed from the compartment door from the very first frame to the last: a plain white-painted wooden trunk sits on the luggage rack above, a short man in a dark coat and cap sits by the window with his back to camera, and snowy Alpine peaks and pine forests slide past outside in bright winter light; no other passengers, no faces. Camera: locked-off; only the landscape moves outside the window." + HOLD,
     "铁轨哐当的节奏"),
    ("S32", "agnes", "背后跟拍 follow from behind",
     "「画商拉上乌菲兹美术馆馆长，来到他住的旅馆」：佛罗伦萨黄昏的窄街，两个大衣礼帽的背影走向旅馆门口，街尾是大教堂的红色穹顶",
     "走进门洞，接开箱俯拍",
     "Dusk on a narrow stone street in Florence, December 1913, framed down the street from the very first frame to the last: two gentlemen in dark overcoats and hats walk side by side away from camera toward the arched doorway of a modest hotel, warm lamplight from shopfronts with blank signboards, and the great terracotta dome of the cathedral rises softly at the end of the street; no faces, no readable signs. Camera: one slow follow from behind at walking pace." + HOLD,
     "石板路脚步、远处教堂钟声"),
    ("S33", "agnes", "俯拍固定 overhead static",
     "「他从箱子夹层里捧出一个红布包」：旅馆房间里打开的白木箱，上层是工具、衬衫和一把曼陀林，双手掀起假底，捧出红绸包着的扁平物件",
     "红布一角接画板背面",
     "Overhead view in a small hotel room in 1913, framed on an open white-painted wooden trunk on the floor beside an iron bed from the very first frame to the last: the trunk's top compartment holds tools, shirts and a mandolin; a man's hands lift out a thin false-bottom board, revealing a flat rectangular package wrapped in deep red silk, and raise it out carefully; no faces. Camera: locked-off overhead; only the hands move." + HOLD,
     "木板掀开的咯吱声、绸布摩擦（sfx paper）；字幕高亮「红布包」"),
    ("S34", "agnes", "缓慢推近 slow push-in",
     "「馆长把画翻过来：白杨木画板背面，卢浮宫的印章和编号全对得上」：窗边红绸上，古旧白杨木板的背面：木纹、顶端一道裂缝和蝴蝶形木楔、几枚模糊的圆形印记，戴手套的指尖点在印记上",
     "指尖停在印记上，接放大镜看裂纹",
     "Close-up by a hotel window in 1913, framed on the back of an old wooden painting panel lying face-down on red silk from the very first frame to the last: pale, aged poplar wood with long fine grain, a thin crack running down from the top edge bridged by one dark butterfly-shaped wooden insert, and several faded circular wax seals and stamped marks worn into illegible smudges; a gentleman's gloved fingertip touches one seal; no faces, no readable text. Camera: one slow push-in toward the seals." + HOLD,
     "木头轻叩声；字幕高亮「白杨木」「印章和编号」"),
    ("S35", "agnes", "微距横移 macro slide",
     "「再比对照片：顶上那道裂缝、细密的裂纹网，全部吻合」：放大镜滑过古画暗色背景上细密的裂纹，旁边压着一张同样裂纹的黑白老照片",
     "放大镜停住，接裂纹科普卡",
     "Macro view on a desk in a Florence gallery office in 1913, framed on the surface of an old oil painting from the very first frame to the last: a large magnifying glass glides slowly over an area of dark, softly painted background landscape, revealing a fine net of tiny cracks in the golden varnish, and beside it an old black-and-white photograph of the same cracked surface lies flat under a brass weight; no faces, no figures, no readable text. Camera: one slow macro slide following the magnifying glass." + HOLD,
     "放大镜玻璃反光的「叮」；字幕高亮「裂纹网」"),
    ("S36", "graphic", "科普卡 static card",
     "裂纹科普卡：背面印章编号 + 顶端裂缝 + 四百年形成的裂纹网 = 画自己的「指纹」，无法伪造",
     "卡片硬切旅馆走廊",
     "画的指纹（文案见 CARDS）",
     "裂纹线条一根根亮起的细响"),
    ("S37", "agnes", "固定 static",
     "「很快，警察敲开了他的房门」：佛罗伦萨旅馆昏暗的走廊，两名披斗篷、戴双角帽的宪兵背影敲门",
     "敲门声落，章节停顿后切警局",
     "A dim corridor of a modest hotel in Florence, 1913, patterned wallpaper and a worn runner carpet, framed from the far end of the corridor from the very first frame to the last: two uniformed Italian carabinieri in dark caped coats and bicorne hats, seen from behind, stand at a closed wooden door and one raps on it with his knuckles, gas-lamp light; no faces. Camera: locked-off; only the officers move." + HOLD,
     "三下敲门声（sfx keys）；音乐骤停"),
    # ---------------- N06 狡辩、结局与金句（8 镜）----------------
    ("S38", "agnes", "固定中景 static medium",
     "「被捕后，他理直气壮：我是爱国！」：佛罗伦萨警局，矮个子背影站在长桌前扬手慷慨陈词，桌后两名警官逆光成剪影",
     "扬起的手接拿破仑车队",
     "A high-ceilinged police office in Florence in 1913 with a tall shuttered window, framed from behind a standing man from the very first frame to the last: a short man in a dark jacket stands with his back to camera in front of a wide desk, gesturing emphatically with one raised hand as if proudly proclaiming something, while two officers sit behind the desk as dark silhouettes against the window light; no faces. Camera: locked-off medium wide from behind the man." + HOLD,
     "他的声音不出现，只有回声般的低音"),
    ("S39", "agnes", "高角度跟拍 high-angle follow",
     "「这画是拿破仑从意大利抢走的！」（佩鲁贾的说法）：1790 年代，意大利山路上满载木箱的马车队，骑兵护送",
     "车队远去，接达芬奇翻越阿尔卑斯",
     "A dusty mountain road in northern Italy in the late 1790s, framed on the winding road from the very first frame to the last: a long convoy of horse-drawn wagons loaded with large wooden crates rolls away from camera escorted by cavalry in Napoleonic-era uniforms seen from behind, cypress trees and hills in hazy golden light; no faces. Camera: one slow high-angle drift following the convoy." + HOLD,
     "马蹄、车轮碾石；标签「佩鲁贾的说法」由后期添加"),
    ("S40", "agnes", "侧向跟拍 lateral track",
     "「可历史当场打脸：这幅画是达芬奇自己带去法国的，比拿破仑出生早了两百多年」：16 世纪初的阿尔卑斯山口，白发长须的老人背影骑骡前行，助手牵着驮着画板的骡子",
     "山风接信与钱币",
     "A high Alpine mountain pass in the early sixteenth century, snow patches and pale sky, framed on a narrow trail from the very first frame to the last: an old man with long white hair and a long beard in a dark Renaissance cloak and cap rides a mule away from camera, followed by two young assistants on foot leading a pack mule with flat wrapped panels strapped to its side; all seen from behind; no faces. Camera: one slow lateral tracking move alongside the small caravan." + HOLD,
     "山风、骡铃；字幕高亮「达芬奇」「拿破仑」"),
    ("S41", "agnes", "俯拍推近 overhead push-in",
     "「何况他开口就要五十万，还写信跟父亲说要发大财」：粗木桌上写了一半的信、蘸水笔和一小堆旧金银币，一只手把钱币推向信纸",
     "钱币叮当接指纹比对",
     "Overhead close-up on a rough wooden table in a small rented room in 1913, framed on the table top from the very first frame to the last: a half-written letter covered in illegible looping handwriting, a dip pen, and a small pile of old gold and silver coins, a man's hand slowly sliding the coins toward the letter; no faces, no readable text or numbers. Camera: one slow overhead push-in." + HOLD,
     "钱币叮当"),
    ("S42", "agnes", "微距横移 macro slide",
     "「而那枚左手拇指印一比，分毫不差」：台灯下两张并排的指纹卡，放大镜从一张滑到另一张，手指沿着一模一样的纹路比划",
     "纹路重合，接判决卡",
     "Macro view on a desk in a 1913 identification bureau, framed on two cards lying side by side from the very first frame to the last: each card bears a single inked thumbprint with an identical whorl pattern, and a large magnifying glass slides from one to the other while a fingertip traces along matching ridge lines; warm lamp light; no writing on the cards, no faces. Camera: one slow macro slide across both prints." + HOLD,
     "放大镜落桌一声（sfx paper）；字幕高亮「分毫不差」"),
    ("S43", "graphic", "判决卡 static card",
     "结局卡：1914 年 1 月 4 日回到卢浮宫；判一年零十五天、上诉后服刑七个月；指纹与档案一致",
     "卡片硬切指纹与裂纹叠影",
     "结局（文案见 CARDS）",
     "法槌一声；字幕高亮「七个月」"),
    ("S44", "agnes", "微距焦点转移 macro focus pull",
     "「他骗过了警察，骗过了档案，却骗不过一枚指纹，和画上的裂纹」：前景玻璃上一枚拇指印，后景是满布细密裂纹的古画表面，焦点从指纹移到裂纹",
     "焦点落在裂纹上，接人群背影",
     "Macro shot framed through a clear pane of glass from the very first frame to the last: in the foreground a single thumbprint glows faintly on the glass, and behind it lies the surface of an old oil painting covered in a fine network of tiny cracks in dark golden varnish, lit by a low raking lamp; the painted area shows only soft dark background, no figure; no faces, no readable text. Camera: one slow focus pull from the thumbprint on the glass to the crackled paint behind it." + HOLD,
     "钢琴单音；金句字幕，字幕高亮「一枚指纹」"),
    ("S45", "agnes", "缓慢后拉 slow pull-back",
     "「你觉得，他是爱国，还是爱钱？评论区聊聊」：1914 年 1 月卢浮宫方形大厅，人群背影涌向远处墙上那幅小小的画（远、模糊），镜头缓缓后退",
     "后退到门口，画面渐隐接片尾卡",
     "The museum's square grand salon in January 1914 under winter skylight, framed from the middle of the room toward the far wall from the very first frame to the last: a dense crowd of visitors in hats and long coats, all seen from behind, presses toward the far wall where a small dark portrait in a gilded frame hangs again between larger paintings, too distant to show any detail, a uniformed guard standing beside it; no faces visible. Camera: one very slow pull-back away from the crowd toward the doorway." + HOLD,
     "人群低语、音乐回升；结尾停 1 秒引导评论，最后 0.8 秒音画渐隐"),
]

# ---------------------------------------------------------------------------
# 画面上的文字（render.py 从 story.json 的 presentation 块读，不在 render.py 里写死）
# ---------------------------------------------------------------------------
CARD_HEADER = "案件档案  /  巴黎 · 佛罗伦萨 · 1911—1914"
CARD_FOOTER = "资料摘要与示意图 · 并非原始档案影像"
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开来源里的事实。
CARDS = {
    "S07": ("蒙娜丽莎失窃案", "1911.8.21 巴黎卢浮宫失窃  →  1913.12 佛罗伦萨追回",
            "失踪 28 个月 · 跨国追回 · 窃贼是卢浮宫的前零工"),
    "S08": ("文森佐·佩鲁贾", "意大利人 · 1881 年生 · 油漆工出身，在巴黎打零工",
            "受雇在卢浮宫给名画装玻璃罩 · 案发时 29 岁"),
    "S19": ("只剩一块白杨木板", "《蒙娜丽莎》是画在白杨木板上的油画 · 77 × 53 厘米",
            "不是画布，卷不起来——他只能整块带走"),
    "S27": ("左手 ≠ 右手", "玻璃罩上：一枚清晰的左手拇指印",
            "档案 75 万份，只按右手拇指分类——不知道名字就查不到"),
    "S30": ("开价 50 万里拉", "化名「莱昂纳多」，写信给佛罗伦萨画商杰里",
            "1913 年冬 · 条件：画要留在意大利"),
    "S36": ("画自己的「指纹」", "背面：卢浮宫印章与编号 · 正面：顶端裂缝与细密裂纹网",
            "四百年油彩干缩、木板胀缩撑出的裂纹，无法复制"),
    "S43": ("1914 年 1 月 4 日 · 回到卢浮宫", "佩鲁贾：判刑一年零十五天，上诉后服刑七个月",
            "玻璃罩上的左手拇指印，与警方留档指纹完全一致"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["蒙娜丽莎失窃案", "一枚左手拇指印，和画板上的裂纹"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "他是爱国，还是爱钱？",
    "蒙娜丽莎失窃案 · 1911—1913 · 巴黎 → 佛罗伦萨",
    "他骗过了警察和档案，却骗不过一枚指纹和画上的裂纹",
    "资料：《纽约时报》1913 / 《华盛顿晚星报》1913 / Hoobler《巴黎罪案》/ 维基百科 · 原创解说 · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词），每章两三个
CAPTION_KEYWORDS = [
    "油漆工", "二十八个月",
    "玻璃罩", "四个铁钩", "白大褂",
    "白杨木板", "水管工",
    "拇指印", "七十五万份", "右手拇指", "左手",
    "五十万里拉", "红布包", "印章和编号", "裂纹网",
    "达芬奇", "分毫不差", "七个月", "一枚指纹",
]
# 逐镜标签覆盖：默认 agnes 镜头标「AI动画情景重现 · 非新闻影像」
LABEL_OVERRIDES = {
    "S04": "AI动画示意 · 非原始档案",
    "S23": "AI动画示意 · 非真实问询影像",
    "S24": "AI动画示意 · 非原始物证",
    "S25": "AI动画示意 · 非原始档案",
    "S26": "AI动画示意 · 非原始档案",
    "S34": "AI动画示意 · 非原作影像",
    "S35": "AI动画示意 · 非原作影像",
    "S37": "AI动画示意 · 非真实执法影像",
    "S38": "AI动画示意 · 非真实执法影像",
    "S39": "AI动画示意 · 这是佩鲁贾的说法",
    "S40": "AI动画示意 · 1516年，达芬奇赴法",
    "S42": "AI动画示意 · 非原始指纹卡",
    "S44": "AI动画示意 · 非原作影像",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S04", "paper"), ("S20", "keys"), ("S26", "paper"), ("S29", "paper"),
    ("S33", "paper"), ("S37", "keys"), ("S42", "paper"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "旷世名画凭空蒸发！偷走《蒙娜丽莎》的油漆工，被一枚左手拇指印彻底出卖",
    "指纹早就躺在警察档案里，他却逍遥了28个月｜蒙娜丽莎失窃案",
    "一口气看懂：蒙娜丽莎是怎么被偷走、又怎么靠画板上的裂纹认出来的？",
]
HOOK = ("一个在卢浮宫装过玻璃罩的意大利油漆工，裹着白大褂把《蒙娜丽莎》带出了卢浮宫；他留在玻璃罩上的左手拇指印，"
        "警方档案里其实早就有——只因档案只按右手拇指分类，让他逍遥了 28 个月；最后揭穿一切的，"
        "是白杨木画板背面的卢浮宫印章，和一张谁也伪造不了的裂纹网。")
GOLDEN_LINES = [
    "他骗过了警察，骗过了档案，却骗不过一枚指纹，和画上的裂纹。",
    "所谓完美犯罪，不过是还没被比对的证据。",
    "你觉得，他是爱国，还是爱钱？评论区聊聊。",
]
DESCRIPTION = ("1911年8月21日，卢浮宫闭馆日，一个穿白大褂的意大利油漆工把《蒙娜丽莎》带出了大门。"
               "他留在玻璃罩上的左手拇指印，警方档案里早就有，却因为档案只按右手拇指分类，让他逍遥了28个月。"
               "直到他化名“莱昂纳多”在佛罗伦萨兜售——白杨木画板背面的卢浮宫印章，和一张独一无二的裂纹网，揭穿了一切。"
               "全片为AI动画情景重现，史实均有公开来源。")
QUESTION = "他偷蒙娜丽莎，到底是爱国，还是爱钱？"
HASHTAGS = ["#蒙娜丽莎", "#卢浮宫", "#艺术品盗窃", "#刑侦科普", "#指纹", "#悬疑", "#真实案件", "#一口气看懂"]

GRID = 4           # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 7  # 每个 Agnes 镜头实际请求的时长（169 帧 @ 24 fps）
SEED_BASE = 19110821  # 失窃日 1911-08-21，seed 可追溯


def presentation():
    return {
        "card_header": CARD_HEADER, "card_footer": CARD_FOOTER,
        "cards": {sid: list(lines) for sid, lines in CARDS.items()},
        "title_card": TITLE_CARD, "end_card": END_CARD,
        "caption_keywords": CAPTION_KEYWORDS, "label_overrides": LABEL_OVERRIDES,
        "default_labels": {"agnes": "AI动画情景重现 · 非历史影像"},
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

#!/usr/bin/env python3
"""《狂犬病疫苗：一百四十年前那场赌局》的全部内容源。

这是这部片子**唯一需要动脑写的文件**：解说词、45 镜分镜、信息卡文案、字幕高亮词、
发布文案、事实来源，全都在这里；跑一次写进 story.json 与 audio/manifest.json。

用法::

    python3 production/rabies1885/build_story.py            # 写 story.json + audio/manifest.json 文本
    python3 production/rabies1885/build_story.py --script   # 生成 抖音脚本.md
    python3 production/rabies1885/build_story.py --publish  # 生成 抖音发布文案.md

内容从哪儿来：

* 解说词 782 字 / 六章，由用户上传的文案改编——改编处全部记在
  `production/docs_lab/workspaces/rabies1885/` 的事实底稿里（"与上传文案的对照"一节）；
* 45 镜 = 38 个 Agnes 镜头 + 7 张信息卡，画面风格 = 用户上传的参考片量出来的调子
  （暖褐 / 橄榄 / 羊皮纸、暗调强反差、明显胶片颗粒），渲染成超写实 3D；
* 每条事实的出处在下面的 SOURCES，2026-10-04 联网核对（WHO / 美国 CDC / 巴斯德研究所 /
  《柳叶刀》/ 国家疾控局《狂犬病暴露预防处置工作规范（2023年版）》）。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"

TITLE = "狂犬病疫苗：一百四十年前那场赌局"

# ---------------------------------------------------------------------------
# 画面风格：参考片（用户上传的 monalisa_180_web.mp4）量出来的调子 + 超写实 3D
#
# 调色/光线/颗粒/运动这些词来自 production/style_lab 的实测值：
#   主色 近黑 #1a160d / 棕褐 #554e32 / 橄榄 #87805e · 平均亮度 92/255（暗调）
#   色温 R−B +28（暖）· 帧内反差 68（强反差）· 颗粒残差 13.21（明显颗粒）
#   帧间差 0.079（明显运动/手持感）
# 唯一改动：参考片的景深指标是 0.44（边缘比中心锐），style_lab 自己判定为
# "主体靠边或素材偏平"，不是真实的景深读数，所以这里换成自然的电影景深，
# 不照抄 "flat even focus"。
# 注意：style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 38 镜全部重做。
# ---------------------------------------------------------------------------
STYLE_PREFIX = (
    "Photorealistic 3D CGI cinematic recreation that reads like live-action photography, with "
    "physically plausible materials, global illumination and true-to-life scale, France between 1880 "
    "and 1895 and present-day China: a cramped Paris laboratory at the Ecole Normale Superieure with "
    "brass microscopes, glass flasks, jars of dried rabbit spinal cords, oil lamps and window light, an "
    "Alsatian half-timbered village street, a Paris institutional stone gateway, a small hospital ward "
    "with an iron bed, the 1888 Institut Pasteur stone facade, and a clean modern community clinic with "
    # 曝光是这一部最容易翻车的地方：第一版写 "near-black, sepia brown, olive, dim, moody exposure"，
    # Agnes 把整帧压成接近全黑（实测亮度 15；已出片的吉尔戈 84、参考片 93）。所以不再写「暗」，
    # 改成可执行的曝光口径：中间调 35–45%、暗部压深但留细节、每个内景至少两处光源。
    "stainless steel and vaccine vials: correctly exposed like a film scan, mid-tones sitting around 35 to "
    "45 percent luma, deep near-black shadows that still hold visible detail, sepia-brown and olive "
    "midtones with cream highlights, punchy but never crushed contrast, warm but natural colour "
    # 第一版写 "warm amber-tungsten"，配上正确曝光后整片偏橙：实测色温 42–68，参考片只有 28。
    "temperature with amber highlights on lit surfaces, neutral-to-warm midtones, no overall "
    "orange cast, every interior lit by at least two practical sources so the room stays readable, "
    "clean crisp optics, visible fine 35mm film grain, natural cinematic depth with a softly "
    "falling-off background, handheld, energetic "
    "camera movement; horizontal 16:9 cinematic composition, one single continuous smooth slow camera "
    "move per shot exactly as directed; "
    # 人物政策第一版写 "only from behind, in silhouette, or as hands - never a clear frontal face"，
    # 自动检验在 11 镜里有 5 镜检出了正脸（S05 十四格全中、置信度 0.91），说明这句约束力不够。
    # 改成把「背对镜头」写成唯一选项，并把五官逐项排除。
    "every human figure is turned away from the camera: back of the head, shoulders, hands and props "
    "only, no facial features anywhere in frame, no eyes, no nose, no mouth, no head turned toward the "
    "lens, any visible head is an unlit silhouette or seen strictly from behind; "
    "no likeness of any real person; absolutely no "
    "readable text, letters, numbers, logos, license plates or brand marks anywhere inside the frame; "
    "no gore, no blood, no corpse, no violence, no nudity. "
)

# 与 production/gilgo 的关键差别：那部是 2D 动画，负面词里有 "3D render look, plastic CGI"，
# 照抄过来会把这次要的超写实 3D 自己否掉——换成挡住 2D 手绘的词。
NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, invented headlines, logos, brand marks, "
    "watermark, subtitles, on-screen caption, photorealistic face, recognizable real person likeness, "
    "frontal face close-up, eyes visible in detail, face turned toward camera, profile of a face, "
    "visible facial features, visible eyes, nose, mouth, teeth, smiling face, looking at camera, "
    "blood, gore, wound, corpse, body bag, body parts, "
    "autopsy, violence, assault, strangling, weapon attack, gun, firearm, nudity, erotic content, horror "
    "monster, ghost, jump scare, distorted anatomy, deformed hands, extra fingers, extra limbs, "
    "duplicated people, changing face, morphing objects, teleportation, jitter, flicker, whip pan, fast "
    "zoom, jump cut, split screen, collage, flat 2D illustration, hand-drawn cel shading, comic-book ink "
    # 曝光两端一起挡：第一版压成了黑屏，所以「欠曝 / 死黑」必须进负面词
    "lines, graphic-novel texture, watercolour paper texture, underexposed, crushed black shadows, "
    "almost entirely black frame, black screen, silhouette-only objects, flat low contrast, "
    "overexposed, washed out, static locked-off shot"
)

# 事实边界与红线：每一条都会印在 抖音脚本.md 的「发布前自查」里。
PRINCIPLES = [
    "全部 Agnes 镜头为超写实 3D 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，不冒充历史照片、新闻影像或档案影像",
    "不展示遗体、血腥与伤口；被咬这件事只用狗的剪影、绷带与事后场景交代，不重现撕咬过程",
    "真实人物（巴斯德、约瑟夫、母亲、医生）只以背影、剪影、手部出现，不用 AI 生成的脸冒充本人",
    "患病的人不出现清晰面容，只用剪影、床、椅子、灯与门窗光暗示，不渲染痛苦表情",
    "每一句事实都能指到 SOURCES 里的一条公开来源；针数（十三针/十四剂）两份权威来源有出入，成片只说「十天、十几针」",
    "不写无法核实的心理活动与场景（如「整个巴黎都在盯着」）；巴斯德的犹豫用他自己有出处的原话",
    "TTS 内容审核会拦「孩子必死 / 杀人犯」这一层措辞（2026-10-04 实测，N03 第一版被拦）；片中改写为「几乎没有生路」「所有的责难都会落在他一个人身上」——意思不变，不碰红线",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写",
    "同一地点保留光线、道具、运动方向；跨时空通过物件（注射器、玻璃罐、脊髓制剂）匹配衔接",
    "人工检视 qa/ 接触表，露脸、畸变、伪文字、中途换场的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

SOURCES = [
    {"id": 1, "url": "https://www.cdc.gov/mmwr/preview/mmwrhtml/00000572.htm",
     "usage": "美国 CDC MMWR：1885-07-06 巴斯德与同事给 9 岁 Joseph Meister 注射第一剂，共 14 天逐日注射兔脊髓悬液；男孩两天前被疯狗咬伤；巴斯德原话（acute and harrowing anxiety）"},
    {"id": 2, "url": "https://www.pasteur.fr/en/about-us/our-dna/history",
     "usage": "巴斯德研究所官方史料：男孩来自阿尔萨斯、被咬十四处、十天内十三针毒力递增；1887 募捐、1888-11-14 研究所落成"},
    {"id": 3, "url": "https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(02)09363-7/abstract",
     "usage": "《柳叶刀》：疫苗取自病兔脊髓、用钾碱干燥减毒、传代三十九次以上；五个月后病人从英俄匈意德涌来"},
    {"id": 4, "url": "https://www.who.int/news-room/fact-sheets/detail/rabies",
     "usage": "WHO 实况报道：出现临床症状后病死率 100%；潜伏期通常 2–3 个月（1 周至 1 年）；恐水、怕风、狂躁型与麻痹型；全球每年数万人死亡、约四成为 15 岁以下儿童"},
    {"id": 5, "url": "https://journals.sagepub.com/doi/pdf/10.1177/014107688908200813",
     "usage": "《Pasteur and rabies: the British connection》：1886-11 约 2500 人接受治疗；到 1895 年巴斯德去世时近 2 万人，死亡率低于 0.5%"},
    {"id": 6, "url": "https://a-z-animals.com/articles/this-deadly-disease-shaped-history-for-4000-yearsand-still-kills-today/",
     "usage": "1884 年巴斯德团队报告原型疫苗已在狗身上成功；19 世纪处置手段（烧灼、Saint-Tügen 礼拜堂把病人闷在两张褥子之间）"},
    {"id": 7, "url": "https://www.cambridge.org/core/services/aop-cambridge-core/content/view/F205B6F02CD8C7E9BD15F120B2977308/S0025727300040783a.pdf",
     "usage": "《Medical History》1982 综述：19 世纪《柳叶刀》记载的狂犬病处置——烧灼、气管切开、箭毒、汞剂等"},
    {"id": 8, "url": "https://www.ndcpa.gov.cn/jbkzzx/c100013/common/content/content_1706557615154524160.html",
     "usage": "国家疾控局《狂犬病暴露预防处置工作规范（2023年版）》解读：5 针程序（0/3/7/14/28 天）与「2-1-1」4 针程序（当天 2 剂、第 7 与 21 天各 1 剂）；病死率几乎 100%、暴露后接种无禁忌症"},
    {"id": 9, "url": "https://markloveshistory.com/tag/joseph-meister/",
     "usage": "巴斯德不是执业医生，给人注射未经验证的制剂一旦失败可能面临起诉——支撑「连行医资格都没有」与「牢狱之灾」两句"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。782 字，估时 175.7 秒（预算 176.1 秒）。
CHAPTERS = [
    ("N01", "黄金开头（0–5 秒：被咬一口就进入倒计时 → 病死率百分之百 → 改写它的是个化学家）",
     "只要被疯狗咬上一口，哪怕只是一道血痕，你就已经进入了倒计时。恐水、痉挛、窒息，人会在清醒里走向终点。"
     "在疫苗出现之前，狂犬病一旦发病，病死率几乎就是百分之百。史料里的抢救办法，是烧灼伤口，甚至把病人闷死。"
     "而改写这个数字的，不是救世主，是一个连行医资格都没有的化学家。"),
    ("N02", "巴斯德与减毒（一八八零年起 · 兔脊髓干燥传代三十九次 → 狗身上成功 → 同行质疑与牢狱风险）",
     "他叫路易·巴斯德。从一八八零年起，他在巴黎的实验室里跟这种病较劲：把患病兔子的脊髓取出来、干燥，再接种到下一只兔子体内，"
     "这样传了三十九次以上，毒性一点一点减弱。四年后，这个办法在狗身上成了。可同行质问他：病原体都看不见，你凭什么？"
     "更麻烦的是，他不是医生。给人打一种没验证过的东西，一旦出事，等着他的就是身败名裂和牢狱之灾。"),
    ("N03", "一八八五年七月六日（九岁男孩 · 十几处伤 · 母亲的恳求 · 巴斯德的原话与抉择）",
     "一八八五年七月六日清晨，一个九岁的男孩被母亲从阿尔萨斯带到他面前。孩子叫约瑟夫，两天前被疯狗咬伤十几处。"
     "母亲只求他救一救。巴斯德后来写下：孩子的结局看起来无法避免，我极度焦虑，还是决定用在狗身上从未失败过的办法试一次。"
     "不治，孩子几乎没有生路；治，一旦失败，所有的责难都会落在他一个人身上。这位老人的手，抖着拿起了注射器。"),
    ("N04", "最难熬的十天（每天一针 · 毒力递增 · 守着病床 → 孩子没有发病）",
     "接下来的十天，是这个实验室最难熬的十天。每天一针，一针比一针毒——按记载，后面用的是毒性更强的制剂。"
     "他是在拿一个孩子的命跟死神抢时间，夜夜守着病床。最后一针打完，他等着最坏的消息。"
     "可约瑟夫没有发病，一天天好起来，成了人类历史上第一个被狂犬病疫苗救下来的人。"),
    ("N05", "从巴黎到世界（病人涌来 → 两千五百人到近两万人 → 研究所落成 → 今天仍在）",
     "消息传开，病人从英国、俄国、意大利、德国涌向巴黎。到一八八六年十一月，已有大约两千五百人接受这种治疗；"
     "到一八九五年巴斯德去世时，接受过的人接近两万，死亡率不到千分之五。一八八八年十一月十四日，巴斯德研究所在巴黎落成。"
     "而直到今天，全球每年仍有数万人死于狂犬病，其中约四成是十五岁以下的孩子。"),
    ("N06", "结尾（今天打完疫苗就回家的平常 → 金句 → 提问读者）",
     "今天，我们被猫狗抓伤，能淡定地去疾控中心，按五针法或者四针法打完疫苗回家——平常得像顺手关灯。"
     "可一百四十年前，这是有人拿名声和一个孩子的命换来的。科学从来不是从天而降的幸运，而是有人敢在深渊面前不退。"
     "那管针剂，到今天还在护着每一个被抓伤的人。你上一次被小动物弄伤，是什么时候？"),
]

# 每一镜：(id, kind, 运镜, 叙事职责, 衔接方式, 英文提示词 或 信息卡说明, 音效/备注)
# 45 镜按成片顺序编号 S01–S45，每镜只用一次；其中 7 张信息卡（S07 S13 S21 S28 S34 S38 S42）。
SHOTS = [
    # ---------------- N01 钩子与绝望（S01–S08，8 镜：7 动画 + 1 信息卡） ----------------
    ('S01', 'agnes', '低机位缓慢横移 low lateral drift',
     '0–5 秒钩子：黄昏村口石板路上一条狗的黑色剪影，只用剪影，不展示撕咬',
     '狗的剪影化进黑暗，硬切挂钟',
     'A large dog standing alone on a wet cobblestone village street at dusk, seen from behind '
     'as a completely black silhouette, low camera at pavement height, one warm window light '
     'far behind, damp air and long shadows. Camera: one slow lateral drift to the right at '
     'knee height. The background holds only a stone wall and darkness. The dog never '
     'approaches the lens and shows no aggression or teeth. Hold this single view: no cut, no '
     'scene change, no camera relocation.',
     '一声远处低沉的狗吠（合成）垫底；无音乐，只有环境声'),
    ('S02', 'agnes', '缓慢横移 slow lateral drift',
     '「你就已经进入了倒计时」：墙上老式挂钟，钟摆在动，指针缓慢移动',
     '钟摆声桥，硬切烛光下的手',
     'Close on a nineteenth century wall clock in a dim farmhouse hallway, the pendulum '
     'swinging, the hands just past six, warm lamplight on the wooden case and the pale dial, '
     'dust in the beam. Camera: one slow lateral drift across the clock face. The dial carries '
     'no readable numbers and no lettering of any kind. Hold this single view: no cut, no '
     'scene change, no camera relocation.',
     '钟摆滴答（合成）垫底；低频嗡鸣起'),
    ('S03', 'agnes', '极缓推近 very slow push in',
     '「恐水、痉挛、窒息」：烛光下一只颤抖的手把一杯水推开，烛火将熄',
     '水杯碰桌声，硬切空床',
     'Close on a trembling adult hand pushing a glass of water away across a wooden kitchen '
     'table at night, a single candle beside it, the water surface shaking, the sleeve rolled '
     'back. Camera: one very slow push in toward the glass. No face, no wound, no blood. Hold '
     'this single view: no cut, no scene change, no camera relocation.',
     '烛火与呼吸声；音乐进入低沉弦乐'),
    ('S04', 'agnes', '缓慢下摇 slow tilt down',
     '「在疫苗出现之前，狂犬病一旦发病」：昏暗房间里一张空床，晨光从窗缝进来，人已经不在',
     '光斑不动，硬切火盆',
     'Interior of a small dark bedroom at first light, an iron bed with a smooth undisturbed '
     'blanket, a wooden chair beside it, a narrow wedge of daylight falling across the empty '
     'pillow from a shuttered window. Camera: one slow tilt down from the window to the bed. '
     'No person in frame at any point. Hold this single view: no cut, no scene change, no '
     'camera relocation.',
     '呼吸声收住；弦乐压低'),
    ('S05', 'agnes', '缓慢下摇 slow tilt down',
     '「史料里的抢救办法：烧灼伤口」：火盆里烧红的铁钳',
     '火星上升，硬切阁楼',
     'Close on a pair of long iron tongs resting in glowing embers inside a stone hearth, '
     'sparks rising, the tong tips bright orange, a dark kitchen behind. Camera: one slow tilt '
     'down from the rising sparks to the embers. No hands, no skin, no wound, no blood. Hold '
     'this single view: no cut, no scene change, no camera relocation.',
     '炭火噼啪声；无音乐'),
    ('S06', 'agnes', '缓慢拉远 slow pull back',
     '「甚至把病人闷死」：阁楼里两张叠着的褥子，一束灰白的光（不出现人）',
     '光斑淡出，硬切信息卡',
     'Pale daylight from a small window filling an attic under a sloping roof so two folded '
     'straw mattresses stacked against a rough stone wall stay readable, dust in the light, '
     'wooden roof beams overhead. Camera: one slow pull back from the mattresses revealing the '
     'empty room. No people anywhere in frame. Hold this single view: no cut, no scene change, '
     'no camera relocation.',
     '低频嗡鸣，音乐收住'),
    ('S07', 'graphic', '静帧',
     '信息卡①：发病后病死率——把「百分之百」钉死在屏幕上',
     '硬切巴黎屋顶',
     '信息卡：病死率（画面文字见 CARDS）',
     ''),
    ('S08', 'agnes', '缓慢横移 slow lateral drift',
     '「一个连行医资格都没有的化学家」：学院高窗前一个穿深色外套的背影，手里拿着一份卷起的文件',
     '背影出画，硬切巴黎屋顶',
     'A lone figure seen strictly from behind in a long dark frock coat standing at a tall '
     'window at the end of a Paris school corridor, shoulders and back only, a rolled document '
     'held at his side, grey daylight through the glass, dust in the air. Camera: one slow '
     'lateral drift along the corridor past the figure. The figure never turns and no face is '
     'ever visible. Hold this single view: no cut, no scene change, no camera relocation.',
     '环境声：远处马车与脚步'),

    # ---------------- N02 巴斯德与减毒（S09–S15，7 镜：6 动画 + 1 信息卡） ----------------
    ('S09', 'agnes', '缓慢下摇 slow tilt down',
     '「他叫路易·巴斯德」：一八八零年代巴黎的屋顶与烟囱轮廓，其中一间阁楼亮着灯',
     '下摇到亮灯的窗，硬切实验室工作台',
     'Exterior rooftops of eighteen eighties Paris at dusk, a long row of chimneys and slate '
     'roofs receding into haze, one attic window glowing warm amber among the dark roofs. '
     'Camera: one slow tilt down from the sky to that single lit window. No readable shop '
     'signs, no advertising, no people. Hold this single view: no cut, no scene change, no '
     'camera relocation.',
     '城市远声；钢琴单音进入'),
    ('S10', 'agnes', '缓慢推近 slow push in',
     '「他在巴黎的实验室里跟这种病较劲」：锌台面、黄铜显微镜、玻璃烧瓶、一盏油灯，无人',
     '灯焰轻晃，硬切兔笼',
     'Interior of a cramped nineteenth century Paris laboratory, a long zinc workbench crowded '
     'with a brass microscope, glass flasks and a lit oil lamp, warm light on the metal, no '
     'people in frame. Camera: one slow push in along the bench toward the microscope. No '
     'readable labels, no papers with writing, no charts. Hold this single view: no cut, no '
     'scene change, no camera relocation.',
     '环境声：液体轻响与火焰'),
    ('S11', 'agnes', '横向移动 lateral dolly',
     '「干燥，再接种到下一只兔子体内」：院子石墙下一排木框兔笼，一只白兔坐在干草上',
     '兔子耳朵一动，硬切玻璃罐',
     'A row of wooden rabbit hutches along a rough stone wall in a small courtyard, one white '
     'rabbit sitting on clean straw in the open doorway of its hutch, morning light across the '
     'yard. Camera: one slow lateral dolly along the row of hutches. The animals are calm and '
     'unharmed; no procedures, no instruments, no blood. Hold this single view: no cut, no '
     'scene change, no camera relocation.',
     '院子环境声：鸟与远处车马'),
    ('S12', 'agnes', '缓慢拉远 slow pull back',
     '「毒性一点一点减弱」：储藏室木架上一排玻璃罐，罐里是干燥处理的脊髓，一头暗一头亮',
     '罐子反光，硬切信息卡',
     'Close on a wooden shelf in a small storeroom holding a row of tall glass jars, each jar '
     'containing a pale dried cord coiled in clear fluid, the row fading from shadow at one '
     'end to warm lamp light at the other. Camera: one slow pull back from a single jar to '
     'reveal the whole row of jars. No readable labels or numbers on the jars. Hold this '
     'single view: no cut, no scene change, no camera relocation.',
     '低频环境声；弦乐渐起'),
    ('S13', 'graphic', '静帧',
     '信息卡②：路易·巴斯德 · 化学家，不是执业医生',
     '硬切学院石廊',
     '信息卡：路易·巴斯德（画面文字见 CARDS）',
     ''),
    ('S14', 'agnes', '缓慢跟拍 backward dolly',
     '「更麻烦的是，他不是医生」：巴黎机构的石阶与木门前，一个穿深色外套的背影拿着卷起的文件走上去',
     '脚步声桥，硬切铁栅阴影',
     'A figure seen only from behind in a long dark frock coat climbing a flight of worn stone '
     'steps toward a heavy wooden door of a Paris institution, a rolled document in one hand, '
     'daylight from one side, the door blank and unmarked. Camera: one slow backward dolly '
     'tracking in front of the figure as it climbs. No face at any point; no readable notices '
     'or plaques. Hold this single view: no cut, no scene change, no camera relocation.',
     '脚步声与远处人声；音乐收住'),
    ('S15', 'agnes', '缓慢横移 slow lateral drift',
     '「一旦出事，等着他的就是身败名裂和牢狱之灾」：石墙上铁栅的阴影缓缓移动，无人',
     '阴影移过墙面，硬切村庄清晨',
     'A stone corridor wall clearly lit by a wall lamp, the hard shadow of an iron bar gate '
     'sliding slowly across it, every stone and the mortar lines readable, dust in the beam. '
     'Camera: one slow lateral drift following the moving bars of shadow. No people, no prison '
     'uniform, no readable text. Hold this single view: no cut, no scene change, no camera '
     'relocation.',
     '低频嗡鸣；一声闷响（合成）'),

    # ---------------- N03 约瑟夫（S16–S23，8 镜：7 动画 + 1 信息卡） ----------------
    ('S16', 'agnes', '向前推进 forward dolly',
     '「一八八五年七月六日清晨」：夏日清晨的阿尔萨斯半木结构村庄街道，空无一人',
     '推进到街道尽头，硬切乡路',
     'An Alsatian half-timbered village street early on a summer morning, shutters closed, the '
     'cobblestones still damp, nobody about, pale light and long shadows across the timbered '
     'facades. Camera: one slow forward dolly down the empty street. No readable shop signs or '
     'house numbers. Hold this single view: no cut, no scene change, no camera relocation.',
     '清晨鸟声与远处牛铃'),
    ('S17', 'agnes', '缓慢跟拍 follow behind',
     '「一个九岁的男孩被母亲从阿尔萨斯带到他面前」：黎明乡路上，一大一小两个背影走远',
     '背影走远，硬切门槛上的孩子',
     'A rural road at dawn, a woman in a long dark skirt and a small boy in short trousers '
     'walking away from the camera side by side, seen only from behind, hedgerows and fields '
     'either side, pale morning mist. Camera: one slow dolly following behind the two figures. '
     'Neither turns around and no face is ever visible. Hold this single view: no cut, no '
     'scene change, no camera relocation.',
     '脚步声与鸟声；钢琴单音'),
    ('S18', 'agnes', '缓慢下摇 slow tilt down',
     '「两天前被疯狗咬伤十几处。母亲只求他救一救」：门槛上的孩子背影，一只大人的手搭在他肩上，小腿缠着布条',
     '手收紧，硬切书桌',
     'A small boy seated on a wooden doorstep seen strictly from behind in bright morning '
     'daylight, the hand of an adult resting on his shoulder, a clean cloth bandage wrapped '
     'around one lower leg, a sunlit farmhouse yard behind. Camera: one slow tilt down from '
     'the shoulder to the bandaged leg. No faces, no wounds, no blood, no torn cloth. Hold '
     'this single view: no cut, no scene change, no camera relocation.',
     '环境声：远处犬吠渐弱；弦乐低入'),
    ('S19', 'agnes', '缓慢横移 slow lateral drift',
     '「巴斯德后来写下：孩子的结局看起来无法避免」：夜里书桌上一只握着羽毛笔的手，纸上墨迹未干',
     '笔尖停住，硬切趴着的狗',
     "Close on an older man's hand holding a quill pen above a sheet of paper on a wooden desk "
     'at night, an inkwell and a single oil lamp beside it, fresh ink glistening on the page. '
     'Camera: one slow lateral drift beside the writing hand. The paper shows only illegible '
     'strokes - no readable words, letters or numbers. Hold this single view: no cut, no scene '
     'change, no camera relocation.',
     '笔尖沙沙与火焰；音乐收住'),
    ('S20', 'agnes', '缓慢下摇 slow tilt down',
     '「还是决定用在狗身上从未失败过的办法试一次」：动物房地板上一只安静趴着的狗，活着、无伤',
     '狗抬起头，硬切信息卡',
     'A calm brown dog lying on the wooden floor of a small animal room, awake and unharmed, a '
     'low window casting daylight across the boards, a water bowl beside it. Camera: one slow '
     'tilt down from the window to the dog. The dog is healthy and still; no procedure, no '
     'instruments, no blood. Hold this single view: no cut, no scene change, no camera '
     'relocation.',
     '狗的呼吸声；一声轻吠（远）'),
    ('S21', 'graphic', '静帧',
     '信息卡③：一八八五年七月六日',
     '硬切深夜窗前的背影',
     '信息卡：一八八五年七月六日（画面文字见 CARDS）',
     ''),
    ('S22', 'agnes', '缓慢拉远 slow pull back',
     '「治，一旦失败，所有的责难都会落在他一个人身上」：深夜窗前一个独自站立的背影，窗外全黑',
     '背影不动，硬切取注射器的手',
     'A lone figure seen strictly from behind standing at a tall dark window at night, '
     'shoulders and back only, the glass reflecting nothing but blackness outside, one candle '
     'burning on a table behind. Camera: one slow pull back from the figure into the room. The '
     'figure never turns and no face is ever visible. Hold this single view: no cut, no scene '
     'change, no camera relocation.',
     '一声心跳（合成）；弦乐压低至无'),
    ('S23', 'agnes', '极缓推近 very slow push in',
     '「这位老人的手，抖着拿起了注射器」：一只手从木盒里取出一支玻璃注射器',
     '玻璃反光，硬切倒计时卡片',
     'Close on an older hand lifting a long glass syringe with a thin metal needle out of an '
     'open dark wooden case, lamp light glinting along the glass barrel, the fingers trembling '
     'slightly. Camera: one very slow push in along the syringe. No face, no ampoule labels, '
     'no text, no blood. Hold this single view: no cut, no scene change, no camera relocation.',
     '玻璃轻碰声；心跳继续'),

    # ---------------- N04 十天（S24–S30，7 镜：6 动画 + 1 信息卡） ----------------
    ('S24', 'agnes', '极缓横移 very slow lateral drift',
     '「接下来的十天，是这个实验室最难熬的十天」：木桌上一张卡片，手指一道道划过划痕',
     '手指划过最后一道，硬切药瓶架',
     'Close on a plain card on a wooden table in a plainly lit treatment room, a forefinger '
     'tracing a row of short abstract pencil scratches one by one, an oil lamp plus daylight '
     'from a window, soft shadow with visible detail. Camera: one very slow lateral drift '
     'alongside the moving finger. The marks are abstract scratches only - no legible numbers, '
     'digits or letters. Hold this single view: no cut, no scene change, no camera relocation.',
     '纸面摩擦声；低频脉动'),
    ('S25', 'agnes', '缓慢上摇 slow tilt up',
     '「每天一针，一针比一针毒」：储藏室木架上排开的小玻璃瓶，从暗到亮',
     '上摇到架子顶端，硬切推活塞的手',
     'Close on a row of small glass vials standing on a deep stone window ledge in a plainly '
     'lit room, bright daylight from the window behind them, the row running from shadow at '
     'one end to strong light at the other, a wet cobblestone courtyard visible through the '
     'window below. Camera: one slow tilt up from the row of vials to the window. No hands, no '
     'people, no readable text, no labels. Hold this single view: no cut, no scene change, no '
     'camera relocation.',
     '玻璃轻响；弦乐渐紧'),
    ('S26', 'agnes', '极缓推近 very slow push in',
     '「后面用的是毒性更强的制剂」：前臂上方，一只手缓缓推下玻璃针管的活塞（不见脸、不见入针）',
     '活塞推到底，硬切病房',
     'Close on an adult forearm in a dark sleeve lying on clean linen, a hand slowly pressing '
     'the plunger of a small glass syringe held just above the forearm, no skin penetration '
     'shown, warm lamp light on the glass. Camera: one very slow push in toward the plunger. '
     'No face, no needle entering skin, no blood. Hold this single view: no cut, no scene '
     'change, no camera relocation.',
     '衣料摩擦与呼吸；音乐悬停'),
    ('S27', 'agnes', '缓慢横移 slow lateral drift',
     '「他是在拿一个孩子的命跟死神抢时间，夜夜守着病床」：夜里的小病房，铁床、木椅、一盏油灯',
     '灯焰轻晃，硬切信息卡',
     'Interior of a small hospital room at night, an iron bed with a still blanket, a wooden '
     'chair beside it, three oil lamps burning on the side table and the wall plus pale '
     'moonlight through a window, the whole room evenly lit and clearly readable, every object '
     'holding visible detail, warm but never dark, the only movement the lamp flame. Camera: '
     'one slow lateral drift from the bed to the chair. No people in frame. Hold this single '
     'view: no cut, no scene change, no camera relocation.',
     '火焰与夜虫声；无音乐'),
    ('S28', 'graphic', '静帧',
     '信息卡④：十天 · 十几针（两份来源针数略有出入，成片不写死）',
     '硬切晨光里的病房',
     '信息卡：十天 · 十几针（画面文字见 CARDS）',
     ''),
    ('S29', 'agnes', '缓慢拉远 slow dolly back',
     '「可约瑟夫没有发病，一天天好起来」：晨光里，床上小小的人影慢慢坐起来',
     '坐起来，硬切厨房喝水',
     'Interior of a small hospital room at morning, a small figure sitting up slowly in an '
     'iron bed, seen only as a backlit silhouette from behind, pale light through the window '
     'behind. Camera: one slow dolly back from the bed. No face, no features, no readable '
     'text. Hold this single view: no cut, no scene change, no camera relocation.',
     '晨光里的鸟声；钢琴进入'),
    ('S30', 'agnes', '缓慢推近 slow push in',
     '「成了人类历史上第一个被狂犬病疫苗救下来的人」：农舍厨房里，一只小手端起木桌上的杯子喝水（呼应第三镜被推开的那杯水）',
     '杯子放下，硬切庭院人群',
     "Close on a small child's hand lifting a glass of water from a wooden farmhouse kitchen "
     'table in morning light and drinking from it, a plain mug beside, the same table where a '
     'candle burned in an earlier shot. Camera: one slow push in toward the glass. Only the '
     'hand and the glass are in frame - no face, no features. Hold this single view: no cut, '
     'no scene change, no camera relocation.',
     '喝水声；音乐第一次完整地起来'),

    # ---------------- N05 扩散（S31–S38，8 镜：6 动画 + 2 信息卡） ----------------
    ('S31', 'agnes', '缓慢下摇 slow tilt down',
     '「消息传开，病人从英国、俄国、意大利…」：巴黎一处庭院，穿深色外套的人群背影朝一个门口走去',
     '人群进门，硬切火车站台',
     'Exterior of a Paris courtyard in the eighteen eighties, a crowd of people in dark coats '
     'and hats walking away from the camera toward a single doorway, seen only from behind, '
     'stone paving wet with rain. Camera: one slow tilt down from the facade to the moving '
     'crowd. No faces, no readable signs or plaques. Hold this single view: no cut, no scene '
     'change, no camera relocation.',
     '人群脚步声与低语；弦乐渐强'),
    ('S32', 'agnes', '缓慢上摇 slow tilt up',
     '「德国涌向巴黎」：蒸汽机车进站，月台边缘的人影',
     '蒸汽散开，硬切长队',
     'A steam locomotive arriving at a nineteenth century railway platform, thick steam '
     'filling the frame, dark silhouettes of waiting people along the platform edge, low pale '
     'morning sunlight cutting through the steam. Camera: one slow tilt up from the wheels to '
     'the steam. No faces, no legible text on the train or signs. Hold this single view: no '
     'cut, no scene change, no camera relocation.',
     '汽笛与蒸汽声；节奏加快'),
    ('S33', 'agnes', '向前推进 forward dolly',
     '「到一八八六年十一月，已有大约两千五百人接受这种治疗」：石廊里一排坐在长凳上的人，尽头一盏灯',
     '推到走廊中段，硬切信息卡',
     'Interior of a long stone corridor in a Paris institution, a queue of people seated along '
     'a wooden bench on one side, seen strictly from behind, oil lamps spaced along the wall '
     'plus pale daylight from a high window, the whole corridor evenly readable from end to '
     'end. Camera: one slow forward dolly down the corridor. No faces, no readable notices on '
     'the walls. Hold this single view: no cut, no scene change, no camera relocation.',
     '低沉人声与脚步；音乐托住'),
    ('S34', 'graphic', '静帧',
     '信息卡⑤：两千五百人 → 近两万人 · 死亡率低于千分之五',
     '硬切登记簿',
     '信息卡：两千五百 → 近两万（画面文字见 CARDS）',
     ''),
    ('S35', 'agnes', '缓慢下摇 slow tilt down',
     '「死亡率不到千分之五」：木桌上一本摊开的登记簿，纸页上是一道道对勾（不可读），旁边一支笔',
     '笔放下，硬切研究所门楼',
     'Close on a long sheet of pale paper pinned flat to a plaster wall in a plainly lit '
     'office, column after column of short abstract tick marks running down it, the corner of '
     'a wooden table visible at the bottom of the frame, nothing readable. Camera: one slow '
     'tilt down the columns of marks. No people, no faces, no hands, no readable writing. Hold '
     'this single view: no cut, no scene change, no camera relocation.',
     '纸页翻动声；音乐渐收'),
    ('S36', 'agnes', '缓慢上摇 slow tilt up',
     '「一八八八年十一月十四日，巴斯德研究所在巴黎落成」：新落成的石砌门楼',
     '上摇到门楣，硬切生产线',
     'Exterior of the newly finished stone gateway of the Institut Pasteur in Paris in '
     'eighteen eighty eight, clean pale limestone, an open carriage entrance, a few figures in '
     'dark coats passing by seen only from behind. Camera: one slow tilt up from the '
     'flagstones to the top of the arch. No readable inscription, no plaque lettering, no '
     'faces. Hold this single view: no cut, no scene change, no camera relocation.',
     '城市环境声；一记轻鼓（合成）'),
    ('S37', 'agnes', '横向移动 lateral track',
     '「而直到今天，全球每年仍有数万人死于狂犬病」：现代疫苗生产线，不锈钢与传送带上排开的玻璃瓶',
     '传送带移动，硬切信息卡',
     'Interior of a clean modern vaccine filling line, stainless steel and a conveyor carrying '
     'a row of small glass vials under bright neutral light, no workers visible in frame. '
     'Camera: one slow lateral track alongside the moving conveyor. No readable labels or '
     'brand marks on the vials or machinery. Hold this single view: no cut, no scene change, '
     'no camera relocation.',
     '机械轻响；音乐转冷'),
    ('S38', 'graphic', '静帧',
     '信息卡⑥：今天仍在——全球每年数万人死于狂犬病，约四成是十五岁以下的孩子',
     '硬切家猫',
     '信息卡：今天仍在（画面文字见 CARDS）',
     ''),

    # ---------------- N06 今天（S39–S45，7 镜：6 动画 + 1 信息卡） ----------------
    ('S39', 'agnes', '低机位缓慢移动 low slow dolly',
     '「今天，我们被猫狗抓伤」：一只家猫走过木地板，尾巴轻摆（不出现抓挠动作）',
     '猫走出画，硬切接种台',
     'Close on a domestic cat walking across a warm wooden floor away from the camera, its '
     'tail swaying, neutral afternoon daylight through a window making long shadows, dust in '
     'the air, low camera near the floor. Camera: one slow low dolly following the cat. The '
     'cat is calm; no scratching, no wound, no blood. Hold this single view: no cut, no scene '
     'change, no camera relocation.',
     '室内安静的环境声；一声猫叫（远）'),
    ('S40', 'agnes', '俯拍缓慢横移 slow overhead lateral drift',
     '「能淡定地去疾控中心，按五针法或者四针法打完疫苗」：接种台面上一排现代疫苗瓶与一支一次性注射器，无人',
     '硬切居民楼',
     'Top-down close on a modern clinic treatment tray, a row of small vaccine vials and a '
     'single sealed disposable syringe laid out on pale paper, cool neutral clinic light, '
     'stainless steel edge of the tray. Camera: one slow overhead lateral drift along the '
     'tray. No readable labels, no brand marks, no people. Hold this single view: no cut, no '
     'scene change, no camera relocation.',
     '空调低频与远处人声'),
    ('S41', 'agnes', '缓慢上摇 slow tilt up',
     '「平常得像顺手关灯」：傍晚居民楼，一盏盏窗灯亮起',
     '灯亮满，硬切信息卡',
     'Exterior of a modern residential neighbourhood at dusk, warm window lights switching on '
     'one by one across a row of apartment buildings, cool blue sky above, a few bare trees. '
     'Camera: one slow tilt up the facade as the lights come on. No readable signage, no '
     'advertising, no people. Hold this single view: no cut, no scene change, no camera '
     'relocation.',
     '街区环境声；音乐温暖起来'),
    ('S42', 'graphic', '静帧',
     '信息卡⑦：暴露后接种——五针法与四针法（二零二三年版规范）',
     '硬切昏暗石廊',
     '信息卡：暴露后接种（画面文字见 CARDS）',
     ''),
    ('S43', 'agnes', '缓慢跟拍 backward dolly',
     '「而是有人敢在深渊面前不退」：昏暗的石廊尽头，一个背影独自向前走，尽头有微光',
     '微光渐亮，硬切接种的手',
     'Interior of a long stone corridor lit by a row of warm wall lamps along its whole '
     'length, the stone walls and floor clearly readable from end to end, the far end '
     'brightest, a single figure in a long dark coat seen only from behind walking away from '
     'the camera toward that light, dust in the beam. Camera: one slow backward dolly tracking '
     'in front of the figure. The figure never turns and no face is ever visible. Hold this '
     'single view: no cut, no scene change, no camera relocation.',
     '脚步声与低频弦乐；一记心跳（合成）'),
    ('S44', 'agnes', '极缓推近 very slow push in',
     '「那管针剂，到今天还在护着每一个被抓伤的人」：上臂三角肌上方，一只戴手套的手持针管（不见脸、不见入针）',
     '针管移开，硬切旧注射器',
     'Close on an adult upper arm in a short sleeve, a gloved hand holding a small modern '
     'syringe just above the shoulder, clean neutral clinic light, shallow focus. Camera: one '
     'very slow push in toward the shoulder. No faces, no blood, no needle penetration detail, '
     'no readable labels on the syringe. Hold this single view: no cut, no scene change, no '
     'camera relocation.',
     '轻呼吸声；音乐收成单音'),
    ('S45', 'agnes', '缓慢拉远 slow pull back',
     '「你上一次被小动物弄伤，是什么时候？」：现代诊室木桌上，一支旧玻璃注射器与一支现代疫苗瓶并排',
     '拉远到整间诊室，淡出',
     'Close on an old long glass syringe with a thin metal needle lying beside a sealed modern '
     'vaccine vial on a clean light wooden clinic desk, soft neutral window light from the '
     'left, soft shadow between them, fine film grain. Camera: one slow pull back from the two '
     'objects to reveal the quiet room. No readable labels, no text, no people. Hold this '
     'single view: no cut, no scene change, no camera relocation.',
     '环境声淡出；最后一个钢琴音'),
]

# ---------------------------------------------------------------------------
# 画面上的文字（render.py 从 story.json 的 presentation 块读，不在 render.py 里写死）
# ---------------------------------------------------------------------------
CARD_HEADER = "狂犬病疫苗 · 一八八五"                                   # 每张信息卡左上角的小字
CARD_FOOTER = "资料摘要与示意图 · 并非原始档案影像"                       # 每张信息卡左下角的小字

CARDS = {
    "S07": ("发病之后", "狂犬病 · 病死率", "出现临床症状后，病死率接近百分之百"),
    "S13": ("路易·巴斯德", "化学家 · 不是执业医生", "一八八零年起研究狂犬病"),
    "S21": ("一八八五年七月六日", "巴黎 · 高等师范学校实验室", "九岁的约瑟夫，被疯狗咬伤后第二天"),
    "S28": ("十天 · 十几针", "每天一剂兔脊髓制剂", "毒力逐针增强（两份来源针数略有出入）"),
    "S34": ("两千五百 → 近两万", "一八八六年十一月约两千五百人接受治疗", "到一八九五年近两万人 · 死亡率低于千分之五"),
    "S38": ("今天仍在", "全球每年数万人死于狂犬病", "其中约四成是十五岁以下的孩子"),
    "S42": ("暴露后接种", "五针法：第零、三、七、十四、二十八天", "四针法（二之一一）：当天两剂 · 第七、二十一天各一剂"),
}

TITLE_CARD = ["狂犬病疫苗", "一百四十年前那场赌局"]

END_CARD = [
    "你上一次被小动物弄伤，是什么时候？",
    "狂犬病疫苗 · 一八八五年七月六日 · 巴黎",
    "科学从来不是从天而降的幸运，而是有人敢在深渊面前不退。",
    "资料：WHO / 美国CDC / 巴斯德研究所 / 国家疾控局 · 原创解说 · AI动画情景重现",
]

CAPTION_KEYWORDS = [
    "百分之百", "闷死", "化学家", "巴斯德", "三十九次", "狗身上", "牢狱之灾",
    "一八八五年", "约瑟夫", "十几处", "杀人犯", "十天", "毒性更强", "第一个",
    "两千五百", "两万", "千分之五", "数万人", "四成", "五针法", "四针法", "一百四十年前",
]

# 医疗/接种镜头换更具体的标签，避免被当成真实医疗教学影像
LABEL_OVERRIDES = {
    "S22": "AI动画情景重现 · 非历史影像",
    "S23": "AI动画情景重现 · 非历史影像",
    "S26": "AI动画示意 · 非医疗教学影像",
    "S27": "AI动画情景重现 · 非历史影像",
    "S29": "AI动画情景重现 · 非历史影像",
    "S35": "AI动画情景重现 · 非历史影像",
    "S36": "AI动画情景重现 · 非历史影像",
    "S40": "AI动画示意 · 非医疗教学影像",
    "S41": "AI动画示意 · 非医疗教学影像",
    "S43": "AI动画示意 · 非医疗教学影像",
}

# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S08", "paper"),
    ("S12", "machine"),
    ("S14", "keys"),
    ("S23", "keys"),
    ("S26", "press"),
    ("S32", "machine"),
    ("S37", "machine"),
    ("S45", "keys"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "被狗咬一口就必死：一百四十年前，有人拿一个孩子的命赌赢了",
    "狂犬病发病后病死率百分之百，改写它的却是个没有行医证的化学家",
    "他不是医生，却给九岁男孩打了人类第一针疫苗：十天，十几针",
]

HOOK = ("狂犬病一旦发病，病死率几乎百分之百。一八八五年，一个没有行医资格的化学家，"
        "用十天、十几针，和一个九岁男孩的命，把人类从这百分之百里拽了出来。")

GOLDEN_LINES = [
    "科学从来不是从天而降的幸运，而是有人敢在深渊面前不退。",
    "一百四十年前那管针剂，到今天还在护着每一个被猫狗抓伤的人。",
    "你上一次被小动物弄伤，是什么时候？评论区聊聊。",
]

DESCRIPTION = ("被疯狗咬一口，在疫苗出现之前几乎等于被判了死刑：狂犬病一旦发病，病死率接近百分之百。"
               "一八八五年七月六日，化学家巴斯德做了一个没有先例的决定——把只在狗身上验证过的制剂，"
               "打进一个九岁男孩的体内。十天、十几针，他赌上的是自己的名声和一个孩子的命。"
               "今天我们去疾控中心打的那几针，就是从这里开始的。"
               "画面全部为 AI 动画情景重现，非历史影像；事实来自 WHO、美国 CDC、巴斯德研究所、"
               "《柳叶刀》与国家疾控局公开资料。")

QUESTION = "你上一次被小动物弄伤，是什么时候？去打疫苗了吗？"

HASHTAGS = ["#狂犬病", "#巴斯德", "#疫苗", "#科普", "#真实历史", "#冷知识", "#医学史"]

# 曝光收尾：挂在每一镜的描述**之后**。全局 STYLE_PREFIX 在前面，会被逐镜描述里
# 的 "single oil lamp" / "at night" / "dark room" 顶掉（S27 病房实测亮度只有 25.5，
# 提示词自己写死了一盏油灯）。所以逐镜提示词的最后一句必须再压一次曝光口径。
LIGHTING_SUFFIX = (
    "Lit so the subject stays clearly readable: at least two practical light sources in the scene "
    "(an oil lamp or candle plus a window, or a second lamp), visible detail in the shadows, "
    "mid-tones around 35 to 45 percent luma, nothing crushed to black, no shot dominated by darkness."
)

GRID = 4           # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 7  # 每个 Agnes 镜头实际请求的时长（169 帧 @ 24 fps）
SEED_BASE = 18850706  # 用第一针的日期，seed 可追溯


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
            "prompt": (body.strip() + " " + LIGHTING_SUFFIX) if kind == "agnes" else "",
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


def render_screenplay() -> str:
    """从 story.json 渲染 screenplay.md。

    手工抄录解说词迟早会对不上，所以解说词、分镜表、事实边界一律由 story.json 生成：
    三处逐字一致是 generate.py --validate 的硬要求，靠人抄是靠不住的。
    """
    story = json.loads(PLAN.read_text())
    lines = [
        f"# {story['title']}",
        "",
        "三分钟横屏解说 · 成片目标 1920×1080 / 30 fps / 180 秒",
        "",
        "## 事实边界",
        "",
        "这一段是这部片子的底线，比任何画面都重要：",
        "",
    ]
    lines += [f"- {p}" for p in story["principles"]]
    lines += [
        "",
        "**关键取舍**（与用户上传文案对照后的改动，核对过程见 "
        "`production/docs_lab/workspaces/rabies1885/`）：",
        "",
        "- 删掉「血肉模糊的伤口特写」——画面踩血腥红线，TTS 也会拦，改成狗的剪影与事后绷带；",
        "- 「活活烧死或闷死」改成「史料里记载的抢救办法，是烧灼伤口，甚至把病人闷死」——"
        "烧死没有可靠出处，闷死有（《柳叶刀》十九世纪综述、Saint-Tügen 礼拜堂的记载）；",
        "- 删掉「整个医学界都在嘲笑他」「整个巴黎都在盯着」这类无出处的渲染；",
        "- 巴斯德的犹豫改用他自己有出处的原话（美国 CDC 转引），不编心理活动；",
        "- 针数两份权威来源不一致（美国 CDC 十四剂 / 巴斯德研究所十三针），"
        "成片只说「十天、十几针」，不写死数字。",
        "",
        "## 解说稿与时间线",
        "",
    ]
    for i, ch in enumerate(story["chapters"]):
        start, end = i * 30, (i + 1) * 30
        lines += [
            f"### {start // 60:02d}:{start % 60:02d}—{end // 60:02d}:{end % 60:02d}　{ch['title']}（{ch['id']}）",
            "",
            ch["text"],
            "",
        ]
    lines += ["## 分镜与衔接", "",
              "| 镜头 | 规划时间 | 类型 | 叙事职责 | 运镜 | 衔接方式 |",
              "|---|---|---|---|---|---|"]
    for sh in story["shots"]:
        lines.append(
            "| {id} | {s:03d}—{e:03d}s | {kind} | {purpose} | {camera} | {trans} |".format(
                id=sh["id"], s=sh["start"], e=sh["start"] + sh["duration"],
                kind={"agnes": "Agnes 动画", "graphic": "信息卡"}[sh["kind"]],
                purpose=sh["purpose"], camera=sh["camera"], trans=sh["transition_out"]))
        if sh["start"] + sh["duration"] in (32, 60, 92, 120, 152) or sh["id"] == story["shots"][-1]["id"]:
            lines.append(f"| — | — | 解说 {sh['narration_id']} 结束 | — | — | — |")
    lines += ["", "## 资料来源", ""]
    for src in story["sources"]:
        lines.append(f"- [{src['id']}] {src['url']} —— {src['usage']}")
    return "\n".join(lines) + "\n"


def _screenplay():
    out = HERE / "screenplay.md"
    out.write_text(render_screenplay(), encoding="utf-8")
    print(f"screenplay.md 已写入（{len(out.read_text(encoding='utf-8'))} 字符）")


if __name__ == "__main__":
    if "--script" in sys.argv:
        from script_table import render_document  # noqa: E402  (同目录)
        out = HERE / "抖音脚本.md"
        out.write_text(render_document())
        print(f"抖音脚本.md 已写入（{len(out.read_text())} 字符）")
    elif "--screenplay" in sys.argv:
        _screenplay()
    elif "--publish" in sys.argv:
        from script_table import publish_document  # noqa: E402  (同目录)
        out = HERE / "抖音发布文案.md"
        out.write_text(publish_document())
        print(f"抖音发布文案.md 已写入（{len(out.read_text())} 字符）")
    else:
        build()

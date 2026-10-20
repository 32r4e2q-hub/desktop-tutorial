#!/usr/bin/env python3
"""《周克华案：逃亡八年，最后四天》的全部内容源。

这是这部片子**唯一需要动脑写的文件**。引擎（render / build_audio / generate_cogvideox /
QC 工具链）从 production/kitakyushu2002 的模板移植而来，内容按用户上传的 30 镜文案稿
（抖音文案/20261020-000310_粘贴的脚本_20261020-000310.txt）重写为 45 镜 × 4 秒规划网格，
事实按 SOURCES 里的公开来源核对，逐句对照见 史实核对.md。

用法::

    python3 production/zhoukehua2012/build_story.py            # 写 story.json + audio/manifest.json 的逐字文本
    python3 production/zhoukehua2012/build_story.py --script   # 生成 抖音脚本.md
    python3 production/zhoukehua2012/build_story.py --publish  # 生成 抖音发布文案.md

视频模型走**智谱 CogVideoX-Flash 免费档**（generate_cogvideox.py，不调 Agnes、不产生费用）。

内容边界（重要）：周克华是真实人物，**不做肖像还原**——全片只以背影、剪影、手、远处轮廓出现，
没有一张可辨识的脸；办案民警同样只给背影与侧后方。受害者只以空座位、翻扣的相框、白花与
聚合数字致意。所有枪击只用远景、声音、闪光与地面反射表现，不出现伤口、遗体与血腥。

分镜与解说逐句咬合的章法（45 镜 = 38 动态 + 7 信息卡，每章镜头只服务本章解说词）：
  N01 钩子：最后四天的清晨（S01-S08）· N02 起点：二〇〇四（S09-S15）
  N03 跨省流线：长沙与南京（S16-S23）· N04 八月十日与全城搜捕（S24-S30）
  N05 收网：童家桥的六分钟（S31-S38）· N06 代价与落点（S39-S45）
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "周克华案：逃亡八年，最后四天"

# 全片统一的画面风格前缀（英文）。写实 3D CGI 情景重现（不是 2D、不是图片轮播）。
# 注意：style_prefix 参与全部镜头的 request_hash，开工后改一个字 = 38 镜全部重做。
STYLE_PREFIX = (
    "Photorealistic cinematic 3D animated shot, high-end CGI feature-film render with volumetric light, "
    "shallow depth of field and subtle 35mm film grain, set in Chinese cities across the 2000s and the "
    "early 2010s: steep hillside streets and light-rail viaducts in a humid riverside city, old commercial "
    "lanes with roll-up shutters, winter boulevards with bare plane trees, plain bank branches with tiled "
    "facades, cramped residential alleys, railway sidings and level crossings, plain municipal offices "
    "with paper wall maps and stacked folders, overcast summer mornings, rain-wet nights and cold grey "
    "winters, restrained desaturated blue-grey grading, sober documentary mood, never stylised, never a "
    "drawing, never a cartoon; horizontal 16:9 widescreen composition; people act with clear full-body "
    "movement in medium and wide shots rather than close-ups - every face stays turned away, in shadow, "
    "out of focus or seen only from behind, never a recognisable likeness of any real person; absolutely "
    "no readable text, letters, numbers, logos or brand marks anywhere in frame; one single continuous "
    "smooth camera move per shot exactly as directed. "
)

# 桌面 / 室内微距镜头专用前缀：全局前缀里全是街景，模型会照着先画一段外景再切室内
# （kitakyushu 的实测教训）。这些镜头只描述室内，payload 只在它们身上变。
DESK_STYLE = (
    "Photorealistic cinematic 3D animated interior shot, high-end CGI feature-film render with volumetric "
    "light, shallow depth of field and subtle 35mm film grain, inside a plain municipal office room with "
    "plaster walls and a single desk lamp, warm pool of lamplight against cold fill, restrained "
    "desaturated blue-grey grading, sober documentary mood, never stylised, never a drawing, never a "
    "cartoon; horizontal 16:9 widescreen composition; absolutely no readable text, letters, numbers, "
    "logos or brand marks anywhere in frame; one single continuous smooth camera move exactly as directed. "
)
# 2026-10-20 复审：S36/S37 是室外巷子，套 DESK_STYLE（「室内办公室」前缀）会把墙画成室内白墙、
# 把空巷画成走廊 —— 移出覆盖表，回到全局的街景前缀。
# 贴地近景专用前缀。2026-10-20 实测：S36 用全局街景前缀会被画成「屋顶俯瞰的雾中街道」，
# 因为前缀里全是山城街景与轻轨高架，模型会先铺一个大景。这镜要的是墙脚与湿地，
# 所以单独给它一段「画面被墙与地面填满、没有天空、没有街区远景」的前缀。
GROUND_STYLE = (
    "Photorealistic cinematic 3D animated extreme close-up, high-end CGI feature-film render with "
    "volumetric light, shallow depth of field and subtle 35mm film grain, shot at knee height in a narrow "
    "rain-soaked alley before dawn: the frame is filled entirely by the base of a plastered wall and the "
    "wet concrete paving in front of it - no sky, no rooftops, no skyline, no street view, no wide shot; "
    "restrained desaturated blue-grey grading, sober documentary mood, never stylised, never a drawing, "
    "never a cartoon; horizontal 16:9 widescreen composition; absolutely no readable text, letters, "
    "numbers, logos or brand marks anywhere in frame; one single continuous smooth camera move exactly "
    "as directed. "
)

STYLE_OVERRIDES = {"S01": DESK_STYLE, "S07": DESK_STYLE, "S08": DESK_STYLE, "S12": DESK_STYLE,
                   "S20": DESK_STYLE, "S21": DESK_STYLE, "S29": DESK_STYLE, "S36": GROUND_STYLE,
                   "S38": DESK_STYLE, "S41": DESK_STYLE, "S42": DESK_STYLE, "S45": DESK_STYLE}

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, invented headlines, neon lettering, logos, "
    "brand marks, watermark, subtitles, on-screen caption, recognisable real person likeness, celebrity "
    "likeness, portrait of a real public figure, blood, gore, wound, corpse, body bag, body parts, "
    "dismemberment, autopsy, weapon attack, muzzle flash close-up, assault, violence on screen, dead body, "
    "police brutality, children in danger, nudity, horror monster, ghost, jump scare, flat 2D cartoon, "
    "cel-shaded illustration, hand-drawn sketch, watercolour, comic panel, low-poly, waxy plastic skin, "
    "doll-like figure, duplicated identical faces, changing face, morphing objects, teleportation, jitter, "
    "flicker, whip pan, fast zoom, jump cut, split screen, collage"
)

# 事实边界与红线：每一条都会印在 抖音脚本.md 的「发布前自查」里。
PRINCIPLES = [
    "全部动态镜头为写实 3D CGI 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，"
    "不冒充监控、通缉令、庭审、勘查或证物照片",
    "周克华是真实人物，**不做肖像还原**：全片只以背影、剪影、手、远处轮廓出现，没有一张可辨识的脸；"
    "办案民警同样只给背影与侧后方，不虚构对白、不虚构审讯细节",
    "不展示遗体、血腥与枪击伤害：枪击只用远景、声音、墙面闪光与地面反射表现；"
    "现场镜头只出现警戒线、勘查背影与编号标记，不出现伤口、血迹与尸体",
    "受害者不出现可辨识面容与真实姓名：只以空座位、翻扣的相框、一只白花、停住的日常致意",
    "牺牲民警朱彦超只以背影与沿铁路线行走的中远景出现，镜头停在他的脚印与轨道，不做英雄化慢镜",
    "不提供任何可模仿的作案细节：不展示枪支构造、装弹、路线踩点与反侦查手法",
    "每一句事实都能指到 SOURCES 里的一条公开来源；口径冲突处（案发 8 起/10 起、死亡 9 人/10 人）"
    "统一采用警方通报口径「十起案件、十人死亡、六人受伤」，并在画面里写清是警方公布的统计",
    "所有中文姓名、日期、数字、字幕后期添加，不交给视频模型拼写；画面内不出现任何可读文字与招牌",
    "人工检视 qa/ 接触表与全帧 QC 候选帧；畸变、伪文字、中途换场、出现人脸的镜头用 "
    "{\"only\":\"Sxx\"} 重生成，不直接进成片",
    "落点不是猎奇，也不是「悍匪传奇」：不美化、不神化，记住的是受害者、牺牲的民警与那些年普通人的恐惧",
]

# 每条事实的公开来源。
SOURCES = [
    {"id": 1, "url": "https://www.chinanews.com.cn/fz/2012/08-14/4107691.shtml",
     "usage": "支撑：二〇一二年八月十四日凌晨六时五十分，公安部A级通缉犯周克华在重庆沙坪坝区童家桥"
              "被民警击毙；二〇〇四年以来流窜重庆、湖南、江苏等地，持枪作案十起，打死十人、打伤六人，"
              "抢劫巨额财物和一支八一式自动步枪；现场缴获仿五四式手枪、九毫米手枪各一支，弹夹三个，"
              "子弹六十二发"},
    {"id": 2, "url": "https://www.chinanews.com.cn/fz/2012/08-14/4107482.shtml",
     "usage": "支撑：警方新闻发布会通报「苏湘渝系列持枪抢劫杀人案」为公安部挂牌督办案件，"
              "十起案件、十人死亡、六人受伤的官方统计口径"},
    {"id": 3, "url": "https://www.mps.gov.cn/n2253534/n2253535/c4143314/content.html",
     "usage": "支撑：连续四天昼夜奋战，八月十四日凌晨六时五十分在沙坪坝区覃家港镇童家桥村莴笋沟背后"
              "将嫌疑人当场击毙；长沙警方获取其体貌特征、江苏警方进一步确定DNA，为破案奠定基础"},
    {"id": 4, "url": "https://news.sina.com.cn/o/2012-08-15/035924968685.shtml",
     "usage": "支撑：八月十日九时三十四分（另有九时三十七分的表述）在沙坪坝区凤鸣山康居苑中国银行"
              "储蓄所门前持枪抢劫，打死一人、打伤两人，抢走挎包（内有现金七万余元）；"
              "八月十四日六时四十分左右便衣民警王晓渝、周缙在童家桥附近发现踪迹，嫌疑人突然掏枪"
              "转身射击，两民警还击将其击毙"},
    {"id": 5, "url": "https://zh.wikipedia.org/zh-hans/%E8%8B%8F%E6%B9%98%E6%B8%9D%E7%B3%BB%E5%88%97%E6%8C%81%E6%9E%AA%E6%8A%A2%E5%8A%AB%E6%A1%88",
     "usage": "支撑（逐案时间线交叉核对）：二〇〇四年四月二十二日重庆两女性取款后被枪击，一死一伤，"
              "劫走现金七万元；二〇〇五年五月十六日重庆一对取款夫妻被枪击、一名路人中枪，两死一伤；"
              "二〇〇九年三月十九日重庆高新区石桥铺营区执勤士兵遇害、步枪被抢；二〇〇九年十月十四日"
              "长沙南郊公园枪击；二〇〇九年十二月四日长沙天心区取款人被抢四点五万元；二〇一〇年"
              "十月二十五日长沙雨花区一人被抢手提电脑；二〇一一年六月二十八日长沙一男子中枪；"
              "二〇一二年一月六日南京下关区和燕路农行支行附近一人死亡、二十万现金被抢"},
    {"id": 6, "url": "https://www.bbc.com/zhongwen/simp/chinese_news/2012/08/120814_chongqing_manhunt",
     "usage": "支撑：重庆出动警察和武警在内过万警力，连续数天在歌乐山一带搜捕；悬赏总额超过五百四十万元；"
              "官方口径八年间作案多起、至少九人死于其枪下（与十人统计口径的差异已在旁白中统一为警方通报）"},
    {"id": 7, "url": "https://zqb.cyol.com/html/2012-08/15/nw.D110000zgqnb_20120815_1-06.htm",
     "usage": "支撑：八月十四日下午公安部和重庆市政府联合召开新闻通报会，通报「苏湘渝系列抢劫杀人案件"
              "成功告破」；追凶八年、决战四天的叙事框架"},
    {"id": 8, "url": "https://www.chinanews.com.cn/fz/2012/08-14/4105547.shtml",
     "usage": "支撑：二〇一二年八月十四日周克华被击毙当日，苏湘渝系列持枪抢劫杀人案件告破，"
              "公安部签发嘉奖令，重庆市公安局集体荣立一等功"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。六段合计 ≈ 七百六十字（含标点）。
CHAPTERS = [
    ("N01", "黄金开头：最后四天的清晨",
     "二〇一二年八月十四日，清晨六点四十，重庆沙坪坝，童家桥。"
     "两名便衣民警在巷口发现了一个人——一个被追了八年的名字：周克华。"
     "十分钟后，枪声响起。八年里，这个名字反复出现在三座城市的案卷上。八年追捕，为什么会在最后四天突然收网？"),
    ("N02", "案件起点：二〇〇四年的银行门口",
     "故事要从二〇〇四年四月二十二日说起。重庆，两名女子刚从银行取完钱，枪声突然响起，一死一伤，"
     "七万元被抢走。一年后，又一对夫妻在银行门口遇袭，一名路人中枪。"
     "二〇〇五年，他因非法持枪入狱，二〇〇八年出狱。二〇〇九年三月，重庆石桥铺，"
     "执勤哨兵遇害，一支自动步枪被抢走。这就是系列案的起点。"),
    ("N03", "跨省流窜：长沙与南京",
     "专案组发现，这些案子不像临时起意：只挑刚从银行取款的人，只走人流密集的老街，作案后立刻消失。"
     "二〇〇九年到二〇一一年，长沙接连发生枪击；二〇一二年一月六日，南京下关区一家银行门口，"
     "一名提款人当场身亡，二十万现金被抢。三座城市，第一次连成一条线。"),
    ("N04", "八月十日：枪声再起，全城搜捕",
     "二〇一二年八月十日，上午九点三十七分，重庆沙坪坝凤鸣山，中国银行储蓄所门前再次响起枪声："
     "一人不幸身亡，两人受伤。逃往途中，铁路民警朱彦超上前盘查，遭到袭击，不幸牺牲。"
     "当天，重庆全城布控，通往山外的每一条路都被设卡，上万警力进山搜捕——这一次，他没能走远。"),
    ("N05", "收网：童家桥的六分钟",
     "转机来自两座城市：长沙警方拿到了他的体貌特征，江苏警方比中了他的DNA。"
     "八月十四日清晨，便衣民警王晓渝、周缙在童家桥发现了他。察觉被跟踪后，他突然转身，"
     "两名民警随即上前处置——六点五十分，周克华当场身亡，随身的物品全部被起获。"),
    ("N06", "落点：代价，而不是传奇",
     "八年，十起案件，十人死亡、六人受伤。数字背后，是一个个原本普通的日子："
     "有人只是去取一笔钱，有人只是站在哨位上，有人只是路过。追捕结束了，但那些没能回家的人不会回来。"
     "十年之后再看，这仍然是一道关于公共安全的伤口。这不是传奇，是一段必须被记住的代价。"),
]

HOLD = ("no cut, no scene change, no camera relocation, no extra people, "
        "no readable text in frame; hold on this single view for the full clip.")

SHOTS = [
    # ---------------- N01 钩子：最后四天的清晨（S01-S08：7 动态 + 1 信息卡）----------------
    ("S01", "agnes", "高空俯拍缓慢下压，最后落到卷宗",
     "钩子：一张地图，三座城市依次亮起",
     "接信息卡：案件名片",
     "An overhead view of a dark wooden desk at night in a plain office: an old folded street map lies "
     "open under a single desk lamp, three small areas of it circled faintly in pencil while the rest "
     "stays in deep shadow, beside it a stack of paper folders, a pair of reading glasses and a cold "
     "cup of tea; dust drifts in the single desk-lamp beam and the room beyond the light is almost "
     "black. Very slow overhead push-in that drifts down toward the open map and settles on the "
     "folders, " + HOLD,
     "低沉鼓点 + 纸张翻动 + 远处心跳"),

    ("S02", "graphic", "信息卡（静帧）", "名片：案名 / 三座城市 / 八年",
     "接动态镜：清晨的山城",
     "案件名片：案名 / 三座城市 / 八年",
     "低音撞击"),

    ("S03", "agnes", "高空航拍缓慢横移并下降",
     "清晨：山城还没完全醒来",
     "接动态镜：银行门口的寻常早晨",
     "A hazy summer dawn over a steep hillside city on a river in southwest China: terraces of "
     "residential blocks climb the slopes in layers, a light-rail viaduct curves between them, the river "
     "lies flat and pale under a white sky, air-conditioning units and shop awnings crowd the lower "
     "streets, laundry hangs from window grilles and a few early buses move with headlights on through "
     "the mist; the city looks ordinary and calm. Slow aerial lateral drift down and across the rooftops "
     "toward the street canyon below, " + HOLD,
     "夏日蝉鸣 + 远处车流 + 低频铺底"),

    ("S04", "agnes", "街道中景缓慢推进，人群自然流动",
     "银行门口：一个再普通不过的上午",
     "接动态镜：街面突然的骚动",
     "Street level outside a bank branch on a summer morning: the wall above the entrance is bare pale "
     "tile with a plain blue panel and a blank white fascia board, the plate-glass doors are clean and "
     "empty of any marking, and the whole facade carries no writing at all. Commuters walk past carrying "
     "bags, a woman waits with a shopping trolley, a man in a short-sleeve shirt counts change at a "
     "roadside stall, scooters idle at the kerb and an air-conditioner drips onto the pavement; awnings "
     "and shopfronts further down the street are angled away from the lens and softly out of focus, "
     "everybody ordinary, nobody looking at the camera. Slow forward dolly at walking pace along the "
     "pavement toward the entrance, " + HOLD,
     "市声 + 摩托怠速 + 蝉鸣"),

    ("S05", "agnes", "轻微手持，中远景突然静止",
     "骚动：人群四散，不见伤害",
     "接动态镜：傍晚的绳栏与灯",
     "The same stretch of pavement a heartbeat later, seen from across the road in a wide handheld shot: "
     "distant pedestrians suddenly break apart and duck behind parked scooters and a bus shelter, a woman "
     "pulls a child behind a pillar, shopping bags tumble and roll across the tiles, and a security guard "
     "in a dark uniform stumbles backward through the glass door; no injuries and no threatening object "
     "anywhere in view, only panic and empty space opening in the middle of the street. Slight handheld shake that settles into stillness as the street empties, " + HOLD,
     "短促闷响两三下 + 人群脚步 + 低频冲击"),

    ("S06", "agnes", "低机位跟随背影，缓慢推进",
     "童家桥：两名便衣走进巷口，远处一个人影",
     "接动态镜：墙上的照片与地图",
     "Just after dawn in an old hillside neighbourhood: two men in plain dark jackets walk side by side "
     "into a narrow stone-paved lane, seen from behind and slightly below, their shoulders squared, one "
     "of them half-turning to look ahead; far down the lane a lone figure in a dark coat stands still, "
     "small in the mist, and low morning light comes over the tiled roofs behind them; potted plants, a "
     "bicycle and a coiled hose sit against the walls, and the lane is otherwise empty. Slow low tracking "
     "move behind the two men as they walk in, " + HOLD,
     "清晨鸟鸣 + 两人的脚步 + 远处市声"),

    ("S07", "agnes", "沿照片墙缓慢横移，最后停在一张照片前",
     "专案组：一面墙，把三座城市钉在一起",
     "接动态镜：三城地图",
     "Inside a plain municipal office at night: a cork wall covered with pinned photographs of streets and "
     "bank fronts, printed city maps with hand-drawn circles, and newspaper clippings whose columns are "
     "blurred beyond reading, connected by taut lengths of red thread; a desk below holds stacked folders, "
     "a desk lamp and an ashtray, and two investigators stand in the foreground with their backs to the "
     "camera, one raising a hand to pin another sheet. Slow lateral move along the wall that ends on a "
     "single pinned photograph, " + HOLD,
     "图钉轻响 + 笔尖划纸 + 弦乐渐强"),

    ("S08", "agnes", "地图俯拍，镜头沿连线快速移动",
     "三座城市：一条线把案卷连起来",
     "接 N02：二〇〇四年的老街",
     "A dim briefing room seen from directly above: a large printed city map is spread across a table under "
     "a low hanging lamp, three small red pins joined by thin red thread, a ruler, a magnifier and a "
     "closed notebook resting at the edges of the map; the corners of the room "
     "fall away into shadow and the paper texture is visible under the light. Slow aerial glide along the "
     "thread from the western pin eastward to the last pin, then a gentle settle, " + HOLD,
     "地图标记声 + 低频脉冲 + 节奏加快"),

    # ---------------- N02 起点：二〇〇四（S09-S15：6 动态 + 1 信息卡）----------------
    ("S09", "graphic", "信息卡（静帧）", "档案：二〇〇四年四月二十二日",
     "接动态镜：取款的两位女性",
     "案件档案：二〇〇四年四月二十二日",
     "低音撞击"),

    ("S10", "agnes", "老街横移，跟着两个背影走向银行",
     "二〇〇四年：两个背影走向银行",
     "接动态镜：一年后的银行门口",
     "An older commercial street in a Chinese city in spring 2004: low buildings with roll-up shutters, a "
     "barber's pole, bicycles leaning against the kerb and a public telephone booth, the pavement damp from "
     "a morning shower; two young women walk away from the camera along the street toward a small bank "
     "branch with a tiled front, one carrying a handbag close to her body, their faces never visible, "
     "their pace unhurried and ordinary. Slow lateral tracking move that follows them along the shopfronts "
     "toward the branch, " + HOLD,
     "老式车辆引擎 + 卷帘门 + 轻微胶片颗粒"),

    ("S11", "agnes", "长焦远景，隔着街道观察",
     "二〇〇五年：又一对夫妻在银行门口",
     "接动态镜：桌面上的封袋与手套",
     "A wide, cool, overcast view across a road in spring 2005: a middle-aged couple walk out of a bank "
     "branch with a bag between them, seen small and from behind at a distance, while a passer-by crosses "
     "the frame in the foreground; a bus shelter, a parked taxi and a row of street trees fill the middle "
     "distance, everything grey and quiet. Very slow long-lens push-in across the traffic toward the bank "
     "entrance, staying at a distance the whole time, " + HOLD,
     "公交车驶过 + 风声 + 低沉鼓点"),

    ("S12", "agnes", "俯拍桌面，缓慢推近",
     "证物：被抢走的钱，封进一只纸袋",
     "接动态镜：走廊尽头",
     "Directly above a plain wooden table in a small office: a sealed brown paper envelope tied with string "
     "lies beside a pair of white cotton gloves, an open ledger with unreadable entries, an ink pad and a "
     "folder tied with tape; two pairs of hands in dark cuffs arrange the items and one finger rests on the "
     "envelope's seal, the room lit by a single fluorescent tube. Slow overhead push-in that ends close on "
     "the sealed envelope, " + HOLD,
     "纸袋轻响 + 盖章声 + 低音持续"),

    ("S13", "agnes", "走廊纵深构图，人影走远",
     "服刑：走廊、铁门、一个背影",
     "接动态镜：夜色里的街",
     "A long, bare institutional corridor: pale green painted walls, a row of closed steel doors along one "
     "side, a caged ceiling light every few metres throwing hard pools of light on the concrete floor, a "
     "barred window at the far end; a single figure in a loose uniform walks away from the camera down the "
     "corridor, seen only from behind, his shadow lengthening toward the lens. Very slow push-in along the "
     "corridor following the figure, " + HOLD,
     "铁门关闭 + 脚步回声 + 低音铺底"),

    ("S14", "agnes", "夜色中跟随背影走进人群",
     "二〇〇八年：他重新走进人群",
     "接动态镜：雨夜的岗亭",
     "A busy night street in a Chinese city in 2008: food stalls under bare bulbs, steam rising from a "
     "noodle pot, a crowd waiting at a bus stop, scooters weaving past, shuttered shops with unlit signs "
     "and a flyover overhead carrying traffic; a man in a dark jacket walks away from the camera into the "
     "middle of the crowd, his face never visible, and the crowd closes around him until he is hard to "
     "pick out. Slow tracking shot at shoulder height following him into the crowd and then holding on the "
     "moving street, " + HOLD,
     "夜市长街声 + 摩托车 + 弦乐低回"),

    ("S15", "agnes", "雨夜固定机位，缓慢推近岗亭",
     "二〇〇九年三月：营区门口的岗亭",
     "接 N03：老街与银行",
     "A rain-soaked entrance road outside a walled compound at night in March 2009: an empty guard booth "
     "stands at the gate, its light still on, rain falling in visible streaks through the cone of "
     "lamplight, a coat hook and a thermos visible inside the booth, wet asphalt reflecting the gate lamps "
     "in long broken lines, and behind the wall the dark shapes of low buildings; no people in frame at "
     "all. Slow push-in along the wet road toward the empty booth, " + HOLD,
     "雨声 + 铁门轻响 + 极低持续音"),

    # ---------------- N03 跨省流线（S16-S23：6 动态 + 2 信息卡）----------------
    ("S16", "graphic", "信息卡（静帧）", "档案：并案侦查",
     "接动态镜：老街的银行",
     "案件档案：并案侦查",
     "低音撞击"),

    ("S17", "agnes", "老街横移，市声嘈杂",
     "老街：人流密集的银行门口",
     "接动态镜：夜里的坡道",
     "An old commercial street in a central Chinese city around 2010: three-storey buildings with "
     "air-conditioners and laundry poles overhead, a bank branch with a queue at the cash machines, "
     "bicycles and electric scooters parked at an angle, a woman selling roasted chestnuts from a drum "
     "cart, pedestrians shoulder to shoulder under the awning line, the light flat and grey. Slow lateral "
     "tracking move along the busy pavement past the branch entrance, " + HOLD,
     "街市人声 + 自行车铃 + 鼓点"),

    ("S18", "agnes", "坡道仰拍，远处路灯一盏盏亮起",
     "夜里的一段上坡路",
     "接动态镜：冬天的银行门口",
     "A sloping path inside a city park at night: stone steps climbing between dense trees, lamps along the "
     "path throwing small pools of warm light that fade into blackness higher up, leaves and litter on the "
     "wet ground, a low retaining wall with moss, the city glow faint above the treeline; the path is "
     "completely empty of people. Slow upward tilt and push along the steps toward the dark top of the "
     "slope, " + HOLD,
     "夜风 + 树叶摩擦 + 极低弦乐"),

    ("S19", "agnes", "冬日街景缓慢推进，薄雾",
     "冬天：宽阔的林荫道与银行",
     "接动态镜：桌面上的地图",
     "A winter morning on a wide boulevard in an eastern Chinese city: bare plane trees line the road, thin "
     "fog softens the far end of the street, commuters in padded coats wait at a crossing with their backs "
     "to the camera, a bank branch with stone cladding sits behind the trees, an unmarked van is parked at "
     "a distance with its lights off, and the asphalt is patched with damp. Slow forward dolly along the "
     "pavement toward the bank corner in the fog, " + HOLD,
     "冬日风声 + 人行横道提示音 + 低沉鼓点"),

    ("S20", "agnes", "俯拍会议桌，缓慢环绕",
     "专案组：三地案卷摊在同一张桌上",
     "接动态镜：桌面上的封袋",
     "Directly above a long conference table in a plain meeting room: city maps, paper folders, "
     "photocopied reports and a row of sealed paper envelopes are laid out in overlapping layers, a "
     "thermos and several enamel cups sit among them, and six pairs of hands in shirt sleeves point at "
     "different documents while the owners' faces stay out of frame above; a wall map hangs blurred in the "
     "background. Very slow overhead orbital move around the table, " + HOLD,
     "纸张翻动 + 低声讨论 + 笔尖标注"),

    ("S21", "agnes", "微距横移，扫过物品编号",
     "证物：封袋、放大镜与检验记录",
     "接信息卡：物证比对",
     "Extreme close-up across a white laboratory bench: several small sealed paper envelopes stand in a row "
     "on a sheet of white paper beside a pair of tweezers, a magnifier lamp tilted over a glass slide, an "
     "open logbook with blurred handwriting, and a flat folder holding a card; gloved fingers enter the "
     "frame at the edge and turn an envelope under the light. Slow macro lateral move that passes each "
     "item in turn, " + HOLD,
     "封袋轻响 + 仪器提示音 + 低音"),

    ("S22", "graphic", "信息卡（静帧）", "档案：南京 · 二〇一二年一月六日",
     "接动态镜：长途车站",
     "案件档案：物证比对",
     "低音撞击"),

    ("S23", "agnes", "站厅纵深，便衣背影观察人流",
     "布控：车站与出城路口",
     "接 N04：八月十日，街面再起骚动",
     "The concourse of a long-distance bus station in the early 2010s: rows of plastic seats, departure "
     "gateways with queues of passengers carrying bundles, a timetable board whose columns are blurred "
     "beyond reading, fluorescent lights reflecting on the polished floor, and a car visible through the "
     "glass front; two investigators in plain dark jackets stand at the edge of the concourse with their "
     "backs to the camera, quietly watching the crowd. Slow dolly past them into the flow of passengers, "
     + HOLD,
     "广播混响 + 行李轮声 + 低频脉冲"),

    # ---------------- N04 八月十日与全城搜捕（S24-S30：6 动态 + 1 信息卡）----------------
    ("S24", "agnes", "街道远景缓慢横移，突然停住",
     "八月十日，上午九点三十七分",
     "接信息卡：八·一〇案",
     "A bright, humid morning on a hillside street in southwest China in August: a bank branch with a "
     "tiled front and a glass door stands beside a steep side road, a motorcycle is parked at the kerb, a "
     "delivery man lifts a crate from a tricycle, pedestrians move past a row of shops whose signs are "
     "blank, and the concrete is dazzling under the summer sun; everything is completely ordinary. Slow "
     "lateral tracking move along the street that comes to an abrupt stop in front of the branch, " + HOLD,
     "蝉鸣突然压低 + 低频冲击 + 一声闷响"),

    ("S25", "graphic", "信息卡（静帧）", "档案：八月十日",
     "接动态镜：布控的车灯",
     "案件档案：八月十日",
     "低音撞击"),

    ("S26", "agnes", "跟车镜头，穿过窄坡街道",
     "布控：车灯穿过山城的窄坡",
     "接动态镜：铁路边的巡查",
     "An unmarked car with a rooftop light bar flashing moves up a steep, narrow street in a hillside city, "
     "seen from a following low angle: hillside apartment blocks press in on both sides with laundry "
     "hanging over the road, a corner shop's awning juts into the street, scooters pull over to let the "
     "car pass, and the humid air carries a haze that softens the far bend; the driver is visible only as "
     "a shoulder from behind. Slow tracking shot behind and slightly below the car as it climbs the slope, "
     + HOLD,
     "警笛由远及近 + 对讲机 + 节奏加快"),

    ("S27", "agnes", "沿铁路线跟随背影，缓慢推进",
     "铁路边：朱彦超正沿线路巡查",
     "接动态镜：夜里的山林",
     "Morning beside a railway line on the edge of a Chinese city in August: ballast, sleepers and a "
     "single track run away from the camera toward industrial sheds and a distant freight yard, tall weeds "
     "push through the fence, and overhead wires hum; a railway worker in a dark blue uniform walks away "
     "from the camera along the maintenance path beside the track, seen only from behind, his cap and "
     "shoulders small against the wide bright morning. Slow push-in following him along the path, " + HOLD,
     "铁轨环境声 + 远处列车 + 音乐降至低音"),

    ("S28", "agnes", "林间仰拍，手电光束扫过树梢",
     "夜里：山林中的搜索",
     "接动态镜：桌面上的地图与红圈",
     "A wooded hillside on the edge of a Chinese city at night during a search: dense trees and ferns catch "
     "the sweep of torches from below, mist hangs between the trunks, a narrow trail of disturbed "
     "undergrowth leads up the slope, and the torch beams of several searchers cross and separate high in "
     "the canopy while the searchers themselves stay out of frame; the tone is tense but disciplined, never "
     "militarised. Slow upward tilt from the trail into the moving torch beams, " + HOLD,
     "树叶摩擦 + 对讲机呼叫声 + 低频鼓点"),

    ("S29", "agnes", "俯拍地图，笔尖画下红圈",
     "指挥部：红圈越画越小",
     "接动态镜：八月十四日，天亮之前",
     "Inside a temporary command post in a schoolroom at night: a large printed district map is pinned "
     "across desks pushed together, a hand draws a red circle around a hillside block with a marker, "
     "several enamel cups and a walkie-talkie sit at the map's edge, a desk lamp throws hard light across "
     "the paper and the rest of the room falls into shadow; only hands and forearms are in frame. Slow "
     "overhead push-in toward the circled block, " + HOLD,
     "笔尖划纸 + 对讲机杂音 + 音乐短暂停顿"),

    ("S30", "agnes", "巷口固定机位，缓慢推入晨雾",
     "八月十四日，清晨六点四十",
     "接 N05：两座城市送来的线索",
     "A narrow alley in a hillside neighbourhood at first light in August: old residential buildings four "
     "storeys high press in on both sides, a single street lamp still burns at the alley mouth while the "
     "sky above turns from grey to pale, damp concrete and a low step, potted plants along a windowsill, a "
     "bicycle leaning against the wall, and thin morning mist drifting between the buildings; the alley is "
     "empty. Very slow push-in from the alley mouth into the mist, " + HOLD,
     "清晨鸟鸣 + 脚步 + 克制低音"),

    # ---------------- N05 收网（S31-S38：7 动态 + 1 信息卡）----------------
    ("S31", "agnes", "俯拍桌面，缓慢横移",
     "转机：两座城市送来的物证",
     "接动态镜：实验室里的比对",
     "Directly above a grey steel table in a plain evidence room: three sealed kraft-paper evidence "
     "envelopes of different sizes lie in a neat row on a large sheet of clean white paper, each tied with "
     "thin twine and slipped under a small blank card; a folded white cotton cloth and a glass slide rest "
     "beside them, and the rest of the table is bare, matte and unmarked. The light comes from a single "
     "diffused overhead fixture, soft and even, with no blown highlights and no glare on the paper. Slow "
     "overhead lateral move across the row of envelopes, " + HOLD,
     "纸张轻响 + 封袋摩擦 + 低音"),

    ("S32", "agnes", "实验室侧拍，缓慢推近记录",
     "比对：体貌特征与DNA",
     "接信息卡：收网时间",
     "Inside a laboratory office in the early 2010s: a technician in a white coat sits at a bench with her "
     "back and shoulder to the camera, comparing a card under a magnifier lamp while a monitor glows with "
     "blurred charts and a printed report lies open beside the keyboard; a sealed cabinet stands against "
     "the wall and the room is quiet and orderly. Slow push-in from the doorway toward the lit bench, "
     + HOLD,
     "仪器风扇 + 键盘轻响 + 低音铺底"),

    ("S33", "graphic", "信息卡（静帧）", "档案：六时四十分 / 六时五十分",
     "接动态镜：巷口的身影",
     "案件档案：六时四十分 / 六时五十分",
     "低音撞击"),

    ("S34", "agnes", "长焦远观，缓慢横移",
     "巷口：远处出现一个身影",
     "接动态镜：巷内跟拍",
     "A long-lens view down an alley at dawn: in the far distance a lone man in a dark jacket walks away "
     "along the lane, small and slightly out of focus, while in the near foreground two investigators in "
     "plain dark jackets stand at a corner with their backs to the camera, one of them raising a hand "
     "slightly; doorways, gas meters and air-conditioning units line the alley walls, and the pale morning "
     "light comes from behind the distant figure. Very slow lateral move at a distance, keeping both the "
     "foreground pair and the distant figure in frame, " + HOLD,
     "轻微脚步 + 衣料摩擦 + 心跳般低频"),

    ("S35", "agnes", "巷内跟拍，拐角处突然停住",
     "跟上去：他们加快脚步",
     "接动态镜：墙面的闪光",
     "Inside a narrow alley at dawn: two investigators in plain dark jackets move along the wall toward a "
     "corner, seen from behind and from the side, their steps quickening; ahead of them, at the corner "
     "where the lane turns, a dark silhouette stops and turns abruptly, framed against the pale end of the "
     "alley so only a black shape is visible, one arm rising. Handheld follow that stops dead as the "
     "silhouette turns, " + HOLD,
     "急促脚步 + 布料摩擦 + 音乐骤然压低"),

    ("S36", "agnes", "低机位贴墙，只拍墙面与地面",
     "交火：只有墙上的闪光与地面的反光",
     "接动态镜：空巷与绳栏",
     "Knee-height close-up in a narrow alley, the lens almost touching the wall: the left half of the "
     "frame is the grey plaster wall with a rusted iron drainpipe, peeling paint and hairline cracks, "
     "the right half is wet concrete paving with a shallow puddle reflecting the dawn sky; thin mist "
     "drifts low across the ground. Two brief flashes of light sweep across the wall and flare in the "
     "puddle, hard-edged and momentary, then the alley returns to grey with dust drifting. Static low "
     "camera, only the light moving across the frame, "
     + HOLD,
     "短促闷响 + 墙面回声 + 突然静音"),

    ("S37", "agnes", "空巷缓慢拉远，灯光映在湿地面",
     "结束后：空巷、绳栏、湿地面",
     "接动态镜：通报会",
     "A wide, respectful view of a sealed alley minutes after the confrontation: a simple rope barrier "
     "crosses the foreground, two cars stand at the far end with their rooftop light bars turning, blue and "
     "red washing over the wet asphalt and the alley walls, uniformed officials in the middle distance turn "
     "their backs and secure the area, and pale dawn light rises above the rooftops; the alley is clear "
     "apart from the barrier and the officials. Very slow pull-back along the barrier cord, " + HOLD,
     "远处警笛 + 无线电杂音 + 低沉收束"),

    ("S38", "agnes", "从记者席缓慢推向发布台",
     "通报：案件告破",
     "接 N06：黄昏的山城",
     "A formal briefing room in August: three officials in light shirts sit behind a long desk with "
     "microphones and name cards whose text is blurred beyond reading, a plain backdrop behind them, and "
     "journalists in the foreground taking notes with their backs to the camera; camera flashes fire in "
     "ones and twos, the lighting is flat and institutional, and the atmosphere is grave. Slow push-in over "
     "the shoulders of the seated reporters toward the desk, " + HOLD,
     "相机快门 + 记者席杂音 + 庄重低音"),

    # ---------------- N06 代价与落点（S39-S45：6 动态 + 1 信息卡）----------------
    ("S39", "agnes", "高空航拍缓慢后拉",
     "黄昏：城市继续运转",
     "接信息卡：八年 · 十起案件",
     "A wide aerial view of a hillside city at dusk: layered hills covered with residential towers, a river "
     "bend catching the last light, bridges strung with lamps, traffic moving in slow ribbons along the "
     "elevated roads, and haze thickening toward the horizon; the city is vast, indifferent and still "
     "busy. Very slow aerial pull-back and rise from the nearest ridgeline to the whole basin, " + HOLD,
     "城市环境声 + 柔和低音弦乐"),

    ("S40", "graphic", "信息卡（静帧）", "档案：八年 · 十起案件 · 十死六伤",
     "接动态镜：空椅子与白花",
     "案件档案：八年 · 十起案件",
     "低音撞击"),

    ("S41", "agnes", "缓慢推近空椅与翻扣的相框",
     "代价：一把空椅子，一只扣着的相框",
     "接动态镜：空桌与帽子",
     "The corner of a quiet family living room in soft window light: a wooden chair stands empty beside a "
     "table with a single white flower in a glass, and a framed photograph lies face-down beside a folded "
     "cloth; a thermos, a tin of tea and a wall calendar with blurred dates sit on the sideboard, dust "
     "visible in the light beam, and the room is completely still. Very slow push-in from the doorway "
     "toward the empty chair, " + HOLD,
     "室内钟摆 + 微弱风声 + 沉静钢琴"),

    ("S42", "agnes", "静物横移，停在帽子上",
     "牺牲的人：一张空桌，一顶叠好的帽子",
     "接动态镜：清晨的街道",
     "A small office in the morning: a metal desk under a barred window, a folded dark blue uniform cap with "
     "its badge turned away from the light, a duty roster with blurred columns pinned to the wall, a "
     "telephone, a thermos and a chipped enamel mug; the chair is pushed in and the desk is painfully tidy, "
     "the sunlight falling in a clean stripe across the wood. Slow lateral move along the desk that settles "
     "on the folded cap, " + HOLD,
     "安静室内环境声 + 远处火车 + 柔和低音"),

    ("S43", "agnes", "街道中景，跟随人流缓慢前移",
     "生活继续：清晨的街道",
     "接动态镜：山城日出",
     "An ordinary morning street in a Chinese city in autumn: commuters cross at a signal, a bus pulls up "
     "and passengers step down, a shopkeeper raises a roller shutter, a grandmother walks a child to school "
     "holding hands, bicycles wait at the kerb, and the light is warm and low; everyone is seen from behind "
     "or at a distance and nobody looks at the camera. Slow forward dolly at walking pace along the flowing "
     "pavement, " + HOLD,
     "脚步 + 公交车进站 + 轻柔钢琴"),

    ("S44", "agnes", "远山日出，缓慢抬升",
     "日出：雾一层层退下去",
     "接动态镜：窗台上的白花",
     "A hillside above a Chinese city at sunrise: terraced rooftops and narrow lanes descend toward the "
     "river while mist lies in bands between the ridges, the first warm light touching the highest windows "
     "and the curve of a bridge, a single bird crossing the pale sky, the whole city quiet and breathing. "
     "Very slow rise from the nearest rooftops toward the sunlit ridge line, " + HOLD,
     "晨风 + 远处鸟鸣 + 弦乐渐强"),

    ("S45", "agnes", "静物缓慢横移，停在白花上",
     "最后的致意：一枝白花，一束晨光",
     "接片尾卡",
     "A plain windowsill in a bare room in clear morning light: a single white flower stands in a simple "
     "glass of water, a folded newspaper and a pair of reading glasses rest beside it, and the curtain "
     "moves slightly in a draught that also stirs the flower; outside the window the roofs of the city fade "
     "into bright haze and the room is otherwise empty and swept. Slow lateral move along the windowsill "
     "from the glasses to the white flower, " + HOLD,
     "微弱晨风 + 一声远处车流 + 弦乐收束"),
]

CARD_HEADER = "案件档案  /  中国 · 二〇〇四至二〇一二"          # 每张信息卡左上角的小字
CARD_FOOTER = "公开报道口径 · 并非原始档案影像"                # 每张信息卡左下角的小字
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S02": ("苏湘渝系列持枪抢劫杀人案", "重庆 · 长沙 · 南京 · 二〇〇四至二〇一二", "十起案件 · 十人死亡 · 六人受伤"),
    "S09": ("二〇〇四年四月二十二日", "重庆 · 银行门口 · 一死一伤", "七万元现金被抢走 · 系列案的起点"),
    "S16": ("并案侦查", "苏 · 湘 · 渝 三地案件串并", "公安部挂牌督办 · A级通缉令"),
    "S22": ("二〇一二年一月六日 · 南京", "下关区 · 银行门口 · 一名提款人", "二十万现金被抢走 · 跨省流窜"),
    "S25": ("二〇一二年八月十日", "重庆沙坪坝凤鸣山 · 一死两伤", "铁路民警朱彦超在盘查中牺牲"),
    "S33": ("比对：两个城市，一条线索", "长沙警方 · 体貌特征", "江苏警方 · DNA 比中"),
    "S40": ("八年 · 十起案件", "十人死亡 · 六人受伤", "二〇〇四至二〇一二 · 重庆 长沙 南京"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["苏湘渝系列持枪抢劫杀人案", "八年追捕 · 最后四天 · 中国 2004—2012"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "八年追捕落幕，什么才最该被记住？",
    "苏湘渝系列持枪抢劫杀人案 · 二〇〇四至二〇一二 · 十人死亡、六人受伤",
    "真正该记住的不是猎奇，而是那些没能回家的人。",
    "资料：中新网 / 公安部网站 / 中国青年报 / 新华社报道 · 原创解说 · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词）
CAPTION_KEYWORDS = [
    "周克华", "童家桥", "沙坪坝", "便衣", "八年", "最后四天", "六点四十", "六点五十", "十分钟",
    "二〇〇四年", "银行", "七万元", "一死一伤", "哨兵", "自动步枪", "石桥铺", "长沙", "南京",
    "下关区", "二十万", "三座城市", "二〇一二年八月十日", "凤鸣山", "朱彦超", "铁路民警",
    "上万警力", "歌乐山", "体貌特征", "DNA", "王晓渝", "周缙", "当场击毙", "两支手枪", "六十二发",
    "十起案件", "十人死亡", "六人受伤", "代价", "不是传奇", "没能回家",
]
# 逐镜标签覆盖：默认镜头标「AI动画情景重现 · 非新闻影像」，办案/现场/通报镜头写得更具体
LABEL_OVERRIDES = {
    "S01": "AI动画情景重现 · 非新闻影像",
    "S03": "AI动画情景重现 · 非实景航拍",
    "S04": "AI动画情景重现 · 非案发影像",
    "S05": "AI动画情景重现 · 非案发影像 · 无伤害细节",
    "S06": "AI动画情景重现 · 非案发现场影像",
    "S07": "AI动画情景重现 · 非警方办案影像",
    "S08": "AI动画示意 · 非侦查地图原件",
    "S10": "AI动画情景重现 · 非当事人影像",
    "S11": "AI动画情景重现 · 非案发影像",
    "S12": "AI动画示意 · 非证物原件",
    "S13": "AI动画情景重现 · 非监所实景",
    "S14": "AI动画情景重现 · 非本人容貌",
    "S15": "AI动画情景重现 · 非案发影像",
    "S17": "AI动画情景重现 · 非案发影像",
    "S18": "AI动画情景重现 · 非案发影像",
    "S19": "AI动画情景重现 · 非案发影像",
    "S20": "AI动画情景重现 · 非警方办案影像",
    "S21": "AI动画示意 · 非证物原件",
    "S23": "AI动画情景重现 · 非警方办案影像",
    "S24": "AI动画情景重现 · 非案发影像",
    "S26": "AI动画情景重现 · 非牺牲民警本人影像",
    "S27": "AI动画情景重现 · 非警方行动影像",
    "S28": "AI动画情景重现 · 非搜捕实景",
    "S29": "AI动画情景重现 · 非指挥现场原件",
    "S30": "AI动画情景重现 · 非案发影像",
    "S31": "AI动画示意 · 非证物原件",
    "S32": "AI动画示意 · 非鉴定文书原件",
    "S34": "AI动画情景重现 · 非本人容貌",
    "S35": "AI动画情景重现 · 非现场影像",
    "S36": "AI动画示意 · 非现场影像 · 无伤害细节",
    "S37": "AI动画情景重现 · 非现场影像",
    "S38": "AI动画示意 · 非发布会实况",
    "S41": "AI动画情景重现 · 非受害家庭影像",
    "S42": "AI动画情景重现 · 非牺牲民警本人影像",
    "S43": "AI动画情景重现 · 非实景影像",
    "S44": "AI动画情景重现 · 非实景航拍",
    "S45": "AI动画情景重现 · 非实景影像",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S07", "paper"),
    ("S12", "keys"),
    ("S20", "paper"),
    ("S23", "phone"),
    ("S28", "phone"),
    ("S29", "paper"),
    ("S31", "keys"),
    ("S32", "machine"),
    ("S38", "press"),
    ("S42", "press"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "逃亡8年，最后4天：周克华案到底是怎么收网的？",
    "三座城市，十起案件，八年追捕：周克华案全程复盘",
    "从2004到2012：一个名字，和一条横跨苏湘渝的追捕线",
]
HOOK = ("二〇〇四年到二〇一二年，重庆、长沙、南京三座城市之间，十起持枪抢劫杀人案件，"
        "十人死亡、六人受伤。二〇一二年八月十日，重庆沙坪坝的枪声再次响起；"
        "四天之后，八月十四日清晨六点五十分，周克华在童家桥被民警当场击毙。"
        "八年追捕，为什么会在这四天里突然收网？")
GOLDEN_LINES = [
    "八年追捕落幕，真正该记住的不是猎奇，而是那些没能回家的人。",
    "数字背后，是一个个原本普通的日子：取一笔钱、站一班哨、路过一条街。",
    "十年之后再看，这仍然是一道关于公共安全的伤口。这不是传奇，是一段必须被记住的代价。",
]
DESCRIPTION = (
    "二〇〇四年至二〇一二年，重庆、湖南、江苏多地发生系列持枪抢劫杀人案件。"
    "二〇一二年八月十日，重庆沙坪坝区凤鸣山一家银行储蓄所门前再次发生持枪抢劫，"
    "一死两伤，铁路民警朱彦超在盘查中牺牲。警方随后全城布控、进山搜捕。"
    "八月十四日清晨六时五十分，周克华在沙坪坝童家桥被民警当场击毙，苏湘渝系列案件告破。"
    "本片画面为AI生成的情景重现（非新闻影像、非本人容貌），事实依据公开报道与警方通报整理，"
    "不展示血腥细节，不美化犯罪。"
)
QUESTION = "八年、十起案件、十条人命——你觉得这类案件最该被记住的是什么？评论区聊聊。"
HASHTAGS = ["#悬疑", "#真实案件", "#案件解说", "#周克华案", "#法治"]

GRID = 4            # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 6   # 每个镜头实际请求的时长（CogVideoX-Flash 单条约 5–6 秒，render 按需裁切）
SEED_BASE = 20120814  # 击毙日，让 seed 可追溯

# 露脸镜头登记：本片**不做任何真实人物的肖像还原**，因此为空。
FACE_SHOTS = {}
REFERENCE_SHOTS = {}   # 不走定妆照图生视频（免费档 image_url 队列拥堵）
FIRST_FRAME = {}       # 同上


def first_frame_urls():
    base = "https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/arena/a2b4456e-desktop-tutorial/production/zhoukehua2012/"
    return {sid: base + rel for sid, rel in FIRST_FRAME.items()}


def faces():
    """从 cast.json 读面容 token（唯一来源）。本片没有 cast.json，返回空表。"""
    if not CAST.is_file():
        return {}
    cast = json.loads(CAST.read_text(encoding="utf-8"))
    return {c["id"]: (c.get("face") or "").strip() for c in cast.get("characters", [])}


def portrait_urls():
    if not CAST.is_file():
        return {}
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
    extra_frames = first_frame_urls()
    missing_frames = [sid for sid in FIRST_FRAME if not (HERE / FIRST_FRAME[sid]).is_file()]
    assert not missing_frames, f"这些自定义首帧图不存在：{missing_frames}"
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
        if kind != "graphic":
            for cid, token in face.items():
                prompt = prompt.replace("{" + cid + "}", token)
            assert "{" not in prompt and "}" not in prompt, f"{sid} 提示词里还有没替换的占位符"
        shot = {
            "id": sid, "kind": kind, "start": start, "duration": GRID,
            "narration_id": f"N{min(6, start // 30 + 1):02d}",
            "prompt": prompt if kind != "graphic" else "",
            "purpose": purpose, "transition_out": transition,
            "graphic": body if kind == "graphic" else "",
            "seed": SEED_BASE + i + 1,
            "seconds": AGNES_SECONDS, "aspect": "16:9", "resolution": "1080p", "frame_rate": 24,
            "camera": camera, "sfx_note": sfx,
        }
        if sid in STYLE_OVERRIDES:
            shot["style_prefix"] = STYLE_OVERRIDES[sid]
        if sid in FACE_SHOTS:
            shot["cast"] = FACE_SHOTS[sid]
        if sid in REFERENCE_SHOTS:
            shot["reference_image"] = url[REFERENCE_SHOTS[sid]]
        if sid in extra_frames:
            shot["reference_image"] = extra_frames[sid]
        shots.append(shot)
    story["shots"] = shots
    story["presentation"] = presentation()
    story.setdefault("_scaffold", {})["note"] = (
        "内容由 build_story.py 一次性写入；45 镜 × 4 秒规划网格（每镜只用一次）；"
        "本片不做真实人物肖像还原（没有 cast.json，FACE_SHOTS 为空）；"
        "视频模型走智谱 CogVideoX-Flash 免费档（generate_cogvideox.py）；"
        "解说词与 screenplay.md、audio/manifest.json 三处逐字一致由 generate.py --validate 守着。")
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")

    manifest = json.loads(MANIFEST.read_text())
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        assert clip["id"] == chapter["id"]
        clip["text"] = chapter["text"]
    manifest["voice_id"] = manifest.get("voice_id", "voice-00")
    manifest["selection"] = "悬疑低沉男声（本片解说统一使用）"
    for clip in manifest["clips"]:
        clip["voice_id"] = manifest["voice_id"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    kinds = [s["kind"] for s in story["shots"]]
    chars = sum(len(c["text"]) for c in story["chapters"])
    print(f"story.json 已写入：{len(shots)} 镜 = {kinds.count('agnes')} cogvideo + {kinds.count('graphic')} graphic，"
          f"解说 {chars} 字（含标点）")
    print("逐章字数：" + " / ".join(f"{c['id']} {len(c['text'])}" for c in story["chapters"]))
    print(f"露脸镜头：{len(FACE_SHOTS)} 镜；首帧图钉脸：{len(FIRST_FRAME)} 镜")
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
        from script_table import publish_document  # noqa: E402
        out = HERE / "抖音发布文案.md"
        out.write_text(publish_document())
        print(f"抖音发布文案.md 已写入（{len(out.read_text())} 字符）")
    else:
        build()

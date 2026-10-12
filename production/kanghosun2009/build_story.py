#!/usr/bin/env python3
"""《姜浩顺：一滴袖口的血，十名女人》的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

这是这部片子**唯一需要动脑写的文件**（引擎由 production/hwaseong1986 的模板移植而来，
内容按用户上传的 40 镜文案稿（抖音文案/20261012-004930_粘贴的文案_20261012-004930.txt）重写，
事实按 SOURCES 里的 10 条公开来源核对，见 史实核对.md）。

用法::

    python3 production/kanghosun2009/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/kanghosun2009/build_story.py --script   # 生成 抖音脚本.md（3 标题 / 核心爆点 / 四列分镜表 / 金句）
    python3 production/kanghosun2009/build_story.py --publish  # 生成 抖音发布文案.md（标题 / 介绍 / 提问读者一句话 / 话题）

本片是**露脸模式**：五个角色各一张不同的脸，同一角色跨镜头逐字节复用同一条面容 token
（token 只在 cast.json 里写一份，本文件用 {C1}…{C5} 占位符注入，保证逐字节一致），
并复用同一个 seed；由 production/face_cast.py 的 check-prompts / check-frames 两道闸门守着。

视频模型走**智谱 CogVideoX-Flash 免费档**（generate_cogvideox.py，不调 Agnes、不产生费用）。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "姜浩顺：一滴袖口的血，十名女人"

# 全片统一的画面风格前缀（英文）。写实 3D CGI 情景重现（不是 2D、不是图片轮播）。
# 人物动作给足（full-body movement / expressive gesture / medium and wide shots）。
# 注意：style_prefix 参与全部镜头的 request_hash，开工后改一个字 = 38 镜全部重做。
STYLE_PREFIX = (
    "Photorealistic cinematic 3D animated reenactment, high-end CGI feature-film render with volumetric light, "
    "shallow depth of field and subtle 35mm film grain, set in South Korea between 2005 and 2009: Gyeonggi-do "
    "suburbs of low-rise apartment blocks, wet rural roads and small-town bus stops under cold sodium lamps, "
    "plain 2000s Korean police stations, forensic laboratories and courtrooms, wooded hills and farm sheds in "
    "Gangwon province, overcast winter daylight and rainy nights, restrained desaturated blue-grey colour "
    "grading, slow-burn true-crime documentary mood, never stylised, never a drawing, never a cartoon; horizontal "
    "16:9 widescreen cinematic composition; characters act with clear full-body movement and expressive gesture, "
    "staged in medium and wide shots rather than close-ups - a face is shown only where a shot explicitly names "
    "one of the cast characters, and never as a recognisable real person or a likeness of anybody living or "
    "dead; absolutely no readable text, letters, numbers, logos, license plates or brand marks anywhere inside "
    "the frame; one single continuous smooth camera move per shot exactly as directed. "
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
    "全部动态镜头为写实 3D CGI 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，"
    "不冒充搜查、审讯、庭审、监控或证物照片",
    "不展示遗体、血腥或作案过程：作案手法与受害者私密画面一律不写不拍；现场镜头只出现警戒线、"
    "编号标记、远处勘查背影与取证空镜",
    "姜浩顺本人不做肖像还原：情景重现由虚构匿名角色 C1 扮演，片尾卡与标签都写明「非本人容貌」；"
    "服刑、押解等镜头只给背影",
    "受害者全程不给可辨识面容：只以背影、剪影、物件（通勤包、购物袋、站牌）或聚合数字出现，"
    "不出现遗体，不出现真实姓名与照片",
    "五个露脸角色（姜浩顺替身 / 老刑警 / 女鉴定员 / 检察官 / 法官）各有一张不同的脸；"
    "同一角色跨镜头逐字节复用同一条面容 token 并共用同一个 seed",
    "由 production/face_cast.py 的 check-prompts（静态闸门）与 check-frames（画面闸门）检查，"
    "人眼对照接触表判决",
    "每一句事实都能指到 sources 里的一条公开来源；口径冲突处（검거 日期一月二十四日 / 二十七日、"
    "被害者年龄十九岁 / 二十一岁）只写多源一致的写法，不挑一个当结论",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写；画面内不出现任何可读文字、门牌或招牌",
    "人工检视 qa/ 接触表与 delivery/face-cast/ 人脸接触表；换脸、畸变、伪文字、中途换场的镜头用 "
    "{\"only\":\"Sxx\"} 重生成，不直接进成片",
    "画面与解说都不把犯罪者写成传奇：不美化、不猎奇，落点是十名受害者与失踪调查的空白",
]

# 每条事实的公开来源。
SOURCES = [
    {"id": 1, "url": "https://en.wikipedia.org/wiki/Kang_Ho-sun",
     "usage": "支撑：강호순（姜浩顺）生于一九六九年十月十日；被判十项谋杀、性侵与纵火；"
              "二〇〇九年四月二十二日安山地方法院判死刑；受害者为十名女性，包括妻子与岳母"},
    {"id": 2, "url": "https://www.koreatimes.co.kr/southkorea/20090422/serial-killer-kang-given-death-sentence",
     "usage": "支撑：法院认定他在二〇〇六年九月至二〇〇八年十二月间绑架并杀害八名女性；"
              "另认定他在二〇〇五年的火灾中杀害妻子与岳母（他否认纵火）；一月被捕；"
              "审讯中供出另外七名女性；事前为家人买了大额人寿保险"},
    {"id": 3, "url": "https://www.smh.com.au/world/korean-serial-killer-sentenced-to-death-20090422-aeuz.html",
     "usage": "支撑：火灾发生在他为妻子购买多份保险一周之后；他从火里逃出并获得约四亿八千万韩元理赔；"
              "他称火灾是意外；受害者多为在孤立公交站或歌厅被搭话的女性；韩国民事法院另判他赔偿受害者家属"},
    {"id": 4, "url": "https://news.kbs.co.kr/news/view.do?ncd=1762998",
     "usage": "支撑：二〇〇九年四月二十二日水枝（水原）地方法院安山支院一审宣判死刑，检方指控的十名女性全部认定；"
              "纵火虽无直接证据，但综合现场勘查与证人证言，认定是被告纵火且不存在第三人介入的可能"},
    {"id": 5, "url": "https://news.sbs.co.kr/news/endPage.do?news_id=N1000548686",
     "usage": "支撑（事件日志）：二〇〇七年一月七日在水原市权善区金谷洞公交站绑架并杀害女大学生；"
              "二〇〇八年十二月十九日在军浦市大夜美洞保健所前公交站绑架并杀害女大学生；"
              "二〇〇九年一月二十二日，涉案黑色轿车（EQUUS）被监控拍到，警方第一次调查他"},
    {"id": 6, "url": "https://ko.wikipedia.org/wiki/경기_서남부_부녀자_연쇄살인_사건",
     "usage": "支撑：二〇〇八年十二月十九日下午三时许，女大学生在军浦保健所站下车后失踪；"
              "警方注意到黑色 EQUUS 轿车在预期路线上多次出现，驾驶者不是车主（六十三岁女性）而是她三十九岁的儿子；"
              "一月二十三日取得搜查令，一月二十四日凌晨五时十分左右烧毁 EQUUS 并格式化家中硬盘，当天傍晚被紧急逮捕；"
              "在他的货车里发现夹克，国科搜从夹克上检出与另一名失踪主妇相同的DNA；受害女性年龄自十九岁至五十二岁"},
    {"id": 7, "url": "https://news.kbs.co.kr/news/pc/view/view.do?ncd=1725176",
     "usage": "支撑：二〇〇六年九月，江原道旌善郡政府一名二十余岁女职员失踪，后被确认是姜浩顺所为；"
              "他在其家门前进行的现场勘查中平静重演了诱骗并在车内绑缚杀害的过程；"
              "此案物证极少，是他自行供出的"},
    {"id": 8, "url": "https://www.khan.co.kr/issue/articles/ah006",
     "usage": "支撑：二〇〇六年九月七日早上七时五十分左右，在旌善邑绑架上班路上的郡政府职员윤某（时年二十三岁），"
              "当晚用绳（手）杀害并弃于宁越三玉岭附近的崖下；遗骸于二〇〇九年四月确认为该女性"},
    {"id": 9, "url": "https://www.asiae.co.kr/article/2009042210395329021",
     "usage": "支撑（事件日志）：二〇〇九年一月二十四日警方将姜浩顺列为重大嫌疑人并紧急逮捕；"
              "三月六日首次公审；四月八日结审庭上，检方以杀人、现住建筑物放火致死、杀害直系尊属、"
              "性暴力犯罪处罚法违反等罪名请求死刑"},
    {"id": 10, "url": "https://en.sedaily.com/society/2026/08/04/serial-killer-kang-ho-suns-death-sentence-finalized-17",
     "usage": "支撑：二〇〇九年七月二十三日首尔高等法院二审维持死刑；他放弃上告，上告期届满后死刑确定；"
              "至今仍在首尔拘留所，韩国自一九九七年十二月三十日后再未执行死刑；检方称他「毫无悔意，甚至开玩笑」"},
    {"id": 11, "url": "https://v.daum.net/v/20260605103315256",
     "usage": "支撑：他二〇〇九年在面谈中先说「我藏了一件」并主动供出江原道旌善的命案；"
              "国科搜从夹克右侧袖口检出极微量血痕（约一滴），与另一名失踪女性的DNA相符，成为锁定他的关键；"
              "他曾在牛棚（农场畜舍）中的一把镐头上留下两名女性的DNA，至今与任何已确认受害者都不相符"},
    {"id": 12, "url": "https://www.etoday.co.kr/news/view/2484737",
     "usage": "支撑：检方在他牛棚搜出一把疑似作案工具的镐头，镐刃上检出两名女性的DNA；"
              "国科搜表示这两份女性DNA画像仍在，只要有比对对象即可比对；"
              "韩国没有收集保管成年失踪者DNA的法制度，因此至今没有比对对象"},
    {"id": 13, "url": "https://www.donga.com/news/Society/article/all/20091207/24623819/1",
     "usage": "支撑：二〇〇六年十二月至二〇〇八年十二月，他在京畿道西南部一带绑架杀害八名女性；"
              "最后一名受害者是二〇〇八年十二月十九日在军浦保健所前公交站被绑架的女大学生；"
              "事发前他被邻里视为「和气的邻居」"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。六段合计 ≈ 810 字（含标点）。
CHAPTERS = [
    ("N01", "黄金开头：保健所前的那班车",
     "二〇〇八年十二月十九日下午，京畿道军浦市，一名女大学生在保健所前下了公交车，再也没有出来。"
     "二十多天后，警方发现一辆黑色轿车反复出现在她回家的那条路上。"
     "而先把警方目光拽过去的，是一台自动取款机的摄像头：有人用她的信用卡取钱，戴着假发，手指上套着避孕套，"
     "怕留下指纹。这个人，正是车主三十九岁的儿子。"),
    ("N02", "案件起点：一场没有报警的火灾",
     "要读懂这条线，得回到三年前。二〇〇五年十月三十日夜里，京畿道安山一栋住宅起火，他的妻子和岳母死在火里，"
     "他从火里逃了出来。起火前一周，他刚给妻子买了大额人寿保险；事后，约四亿八千万韩元理赔金进了他的账户。"
     "他说，这是一场意外。三年后，法院认定：这是纵火，是谋杀。"),
    ("N03", "三十个月：公交站、夜路、家门口",
     "放火之后的第十一个月，二〇〇六年九月七日清晨，江原道旌善，一位二十三岁的郡政府女职员在上班路上上了他的车，"
     "当晚没有回家。此后两年多，京畿道西南部的一个个公交站、夜路和家门口，女人们接连消失。"
     "她们年纪从十九岁到五十二岁，职业各不相同——唯一的共同点，是独自走在回家的路上，而没有人把她们连成一条线。"),
    ("N04", "破局：他提前一步，和一滴血",
     "警方把车辆、银行和监控拼在一起。他提前一步动手：一月二十四日凌晨，他烧掉那辆黑色轿车，格式化了家里的硬盘。"
     "当天傍晚，警方把他紧急逮捕。而在国科搜的实验室里，一件夹克右侧的袖口上，检出一点几乎看不见的血痕——"
     "只有一滴，DNA 却与另一名失踪女性完全相同。这一点血，成了整条证据链的锁扣。"),
    ("N05", "开口：从七起，到「我还藏了一件」",
     "一开始，他只反问一句：证据呢。第六天，他开口了，供出七起杀人。"
     "几周之后，他又主动补上一句——我藏了一件：二〇〇六年旌善那位女职员，也是我。"
     "那是物证最少的一起，是他自己交出来的。二〇〇九年二月，他被以杀人、纵火、保险诈骗等罪名起诉；"
     "四月八日，检方在结审庭上请求死刑。"),
    ("N06", "判决：十个人，和一把镐头",
     "二〇〇九年四月二十二日，水原地方法院安山支院认定他杀害十名女性，包括妻子和岳母，判处死刑；"
     "七月二十三日，首尔高等法院维持判决；他放弃上告，死刑确定。十七年过去，韩国没有再执行过一次死刑，"
     "他还关在拘留所里。而在他的牛棚里，一把镐头的镐刃上检出两名女性的 DNA，至今没有对上任何人。"
     "十个人是被认定的数字；不确定的，还在那里。"),
]

HOLD = ("no cut, no scene change, no camera relocation, no extra people, "
        "no readable text in frame; hold on this single view for the full clip.")

SHOTS = [
    # ---------------- N01（8 镜：7 动态 + 1 信息卡）----------------
    ("S01", "agnes", "雨夜中远景缓慢前推", "钩子：保健所前的公交站，她在等车",
     "接信息卡：案件名片",
     "A rainy evening in mid-December 2008 on the outskirts of Gunpo, South Korea: a small bus shelter with a "
     "steel frame stands at the kerb of a two-lane road, its single overhead lamp casting a pale cone of light "
     "on wet asphalt, and a young woman in a dark winter coat with a shoulder bag stands waiting with her back "
     "and side to the camera, scarf pulled up against the cold; a low public health centre building with lit "
     "windows and dark low-rise blocks fade into the rain behind the shelter, the timetable panel is completely "
     "blank, no vehicles in frame. Slow medium-wide push toward the shelter, " + HOLD,
     "冬夜雨声 + 低频悬念音"),
    ("S02", "graphic", "信息卡（静帧）", "名片：案名 / 地点与年代 / 规模",
     "接动态镜：空掉的站台与远去的尾灯",
     "案件名片：案名 / 地点与年代 / 规模",
     "低音撞击"),
    ("S03", "agnes", "从站牌缓慢横移", "她上了车；站台空掉",
     "接动态镜：深夜警局的地图",
     "The same rainy bus shelter seconds later, now completely empty: the road glistens under the lamp, a wet "
     "newspaper is crushed against the kerb, and far away at the edge of frame the red tail lights of a large "
     "dark sedan shrink into the rain haze; the timetable panel stays blank, no people, no other vehicles. "
     "Slow lateral move along the kerb from the empty shelter toward the receding tail lights, " + HOLD,
     "雨声 + 远处引擎"),
    ("S04", "agnes", "俯拍桌面缓慢下摇", "一个多月后：地图与八份卷宗",
     "接动态镜：监控室里的那辆车",
     "A night-time South Korean police investigation room in January 2009 lit by a single desk lamp: a large "
     "hand-drawn regional map is spread flat on the table and pinned with a dozen small red headed pins, "
     "surrounded by eight buff case folders fanned in a row, a mug and a ruler; a middle-aged male detective {C2} "
     "leans in from the left with both hands on the table edge, studying the map. All paper is blank. "
     "Slow overhead push down toward the map and the fanned folders, " + HOLD,
     "纸张翻动 + 低频悬念音"),
    ("S05", "agnes", "从监控屏幕缓慢拉出", "取款机前的假发与避孕套手指",
     "接动态镜：被烧毁的黑色轿车",
     "A dim convenience-store cash point alcove at night in January 2009 seen from the security-camera side: a "
     "young forensic technician in a navy police vest {C3} stands at a small monitor rack with her back half to "
     "camera, one hand raised toward a grainy grey screen showing the blurred back of a person in a hooded coat "
     "and a short dark wig at an ATM, the screen carrying no readable digits or lettering; a mop bucket and a "
     "closed shutter frame the alcove. Slow pull-back from the screen to reveal the technician, " + HOLD,
     "录像带运转 + 低频鼓点"),
    ("S06", "agnes", "俯拍桌面缓慢横移", "她们不是数字：一排随身物件",
     "接动态镜：深夜乡道上的车灯",
     "A plain white table in a police evidence room in 2009 under flat overhead light: six women's everyday "
     "belongings are laid out in a neat row - a canvas tote bag, a small leather handbag, a knitted scarf, a "
     "folded umbrella, a pair of flat shoes and a paperback book with a blank cover - each item alone on the "
     "white surface with no people in frame, no faces, no photographs; the room is bare and the edge of a metal "
     "shelf is just visible at the top of frame. Slow overhead lateral move along the row of belongings from the "
     "tote bag to the paperback, " + HOLD,
     "仪器提示音"),
    ("S07", "agnes", "低机位沿路面缓慢跟移", "同一条路，另一辆车，另一个夜",
     "接动态镜：电线杆上的那张纸",
     "A two-lane rural road at night in Gyeonggi province, 2006: wet asphalt recedes into darkness between flat "
     "fields, a single sodium street lamp stands far off at a junction, and the headlights of one dark car sweep "
     "past the camera in the right-hand lane and shrink away into the black distance; no other traffic, no "
     "buildings, no signage, no lettering on the road or the poles, no people in frame. Low tracking move along "
     "the road surface following the receding tail lights, " + HOLD,
     "余烬 + 低沉鼓点"),
    ("S08", "agnes", "从纸面缓慢拉出", "家里人还在等她：一张寻人启事",
     "接 N02：三年前的那场火灾",
     "A cold street corner at dusk in Gyeonggi province: two hands in worn winter sleeves press a single sheet "
     "of blank white paper flat against a concrete utility pole and smooth it down with the palm, a roll of tape "
     "hooked over one thumb, the hands and forearms the only people in frame, the pole surface otherwise bare "
     "with no lettering, no posters, no numbers; a dim shop window glows out of focus behind. Slow pull-back "
     "from the paper to reveal the empty pavement and the pole, " + HOLD,
     "脚步声 + 铁门声"),

    # ---------------- N02（7 镜：6 动态 + 1 信息卡）----------------
    ("S09", "agnes", "从消防车缓慢推进至住宅外墙", "二〇〇五年十月三十日，安山的火灾",
     "接信息卡：二〇〇五 · 安山",
     "A residential street in Ansan, South Korea, on the night of 30 October 2005: a fire engine with its "
     "beacon flashing stands at the kerb, hoses snake across the wet pavement toward a two-storey brick house "
     "whose upper windows are blackened and whose wall is streaked with soot; fire crews in bulky yellow coats "
     "work with their backs to camera and an officer unrolls a tape line. Smoke hangs in the sodium light, no "
     "readable text or signage. Slow push from the fire engine along the hoses to the scorched wall, " + HOLD,
     "消防车警报 + 远处人声"),
    ("S10", "graphic", "信息卡（静帧）", "名片：二〇〇五 · 安山 · 一场火灾",
     "接动态镜：餐桌上的两副碗筷",
     "案件名片：时间 · 地点 · 发生了什么",
     "低音撞击"),
    ("S11", "agnes", "从餐桌横移到墙上的相框", "两个女人的日常，停在那一夜",
     "接动态镜：保险文件与侧影",
     "The quiet interior of an ordinary South Korean home in 2005: a small laminated dining table set for two "
     "with two bowls of rice under inverted plates, two pairs of chopsticks laid straight, a folded woman's "
     "cardigan over the back of one chair, and on the far wall a framed family photograph turned face to the "
     "wall; morning light through a lace curtain, a wall clock without numbers. No readable text anywhere. "
     "Slow lateral move from the laid table across to the turned picture frame, " + HOLD,
     "时钟滴答 + 低频弦乐"),
    ("S12", "agnes", "从文件特写缓慢拉焦到侧影", "起火前一周的保单",
     "接动态镜：理赔金入账",
     "A small South Korean insurance office in 2005: a thick stack of blank policy papers lies open on a "
     "melamine desk beside a ballpoint pen, a desk calculator and a round stamp, and a man in a dark grey jacket "
     "{C1} sits at the desk in three-quarter profile, one hand flat on the papers, his expression calm and "
     "ordinary, a clerk's empty chair opposite; a frosted partition and a filing cabinet behind. Every document "
     "is blank. Slow rack focus from the blank policy papers up to the seated man's profile, " + HOLD,
     "计算器按键声 + 低频鼓点"),
    ("S13", "agnes", "从柜台缓慢横移", "四亿八千万韩元的人寿理赔",
     "接动态镜：三年后的法庭",
     "A South Korean bank counter area in 2005: a clerk's hands slide a thick bundle of banded banknotes and a "
     "slim closed passbook across the counter toward a man in a dark grey jacket whose torso and hands are "
     "in frame while his head is cropped above the frame edge; a receipt spike, a stamp pad and a chained "
     "customer pen sit on the counter, the wall behind the clerk is plain. No readable text, numbers or "
     "currency marks anywhere. Slow lateral move across the counter from the clerk's hands to the notes and the "
     "closed passbook, " + HOLD,
     "纸张摩擦 + 低沉鼓点"),
    ("S14", "agnes", "从被告席缓慢横移至法官席", "三年后：法院认定，火是他放的",
     "接动态镜：放火之后的第十一个月",
     "A plain South Korean district courtroom in 2008: a middle-aged male prosecutor in a dark suit {C4} stands "
     "at a bare lectern holding a thin folder and turning to address the bench, a wooden railing and empty "
     "public benches behind him, and above at the bench an empty high-backed chair and a single stack of blank "
     "documents; cold overhead fluorescents, bare walls, every paper and plaque blank. Slow lateral move along "
     "the railing from the standing prosecutor toward the empty bench, " + HOLD,
     "法庭环境声 + 翻页声"),
    ("S15", "agnes", "沿街缓慢跟拍", "她的上班路：二〇〇六年九月七日",
     "接 N03：旌善的清晨",
     "A quiet South Korean small-town street in early September 2006 at dawn: shuttered shops with blank "
     "signboards line one side, a single street lamp is still burning, and a young woman in a light summer coat "
     "with a canvas tote bag walks away from camera along the pavement, her back to the lens; a parked bicycle "
     "leans against a pole, a bus shelter stands thirty metres ahead, the road is empty, every shop sign and "
     "poster blank. Slow tracking move along the pavement behind the walking woman, " + HOLD,
     "清晨环境音 + 远处巴士"),

    # ---------------- N03（8 镜：6 动态 + 2 信息卡）----------------
    ("S16", "agnes", "乡间公路远景缓慢前推", "江原道旌善：二十三岁的郡政府职员",
     "接动态镜：办公室的下午",
     "A narrow mountain road in Jeongseon, Gangwon province, on a clear September morning in 2006: steep "
     "pine-covered slopes rise on both sides, a low guard rail runs along the outer edge above a shallow valley "
     "mist, and a young woman in office-casual clothes with a shoulder bag walks along the verge away from "
     "camera toward a distant bus shelter; a utility pole and a blank roadside marker stand in the foreground "
     "grass, the asphalt is empty of traffic. Slow distant push along the road toward the walking figure, " + HOLD,
     "山风 + 脚步碎石声"),
    ("S17", "agnes", "办公室内中景缓慢推进", "她有工作、同事、窗和一杯水",
     "接信息卡：失踪档案",
     "A small South Korean county government office in 2006 in late afternoon: a young woman in a plain blouse "
     "and cardigan stands at her desk with her back to camera, packing a slim stack of blank documents and a "
     "pencil case into a canvas tote bag, while two colleagues work at desks further along the row with their "
     "backs to the lens; a water cooler, a coat stand and a wall calendar with no numbers fill the background, "
     "fluorescent tubes overhead, every paper blank. Slow medium push from the office door toward her desk, " + HOLD,
     "键盘声 + 翻纸声"),
    ("S18", "graphic", "信息卡（静帧）", "档案：三十个月里的失踪者",
     "接动态镜：夜晚的商业街",
     "案件档案：时间跨度 · 年龄区间 · 职业",
     "低音撞击"),
    ("S19", "agnes", "从街角缓慢横移", "歌厅服务员、公司职员、主妇、学生",
     "接动态镜：斑马线上的购物袋",
     "A South Korean commercial side street at night in 2007: low-rise buildings with lit windows and blank "
     "glowing signboards, a woman in a short coat and heels stepping out of a glass doorway with a small "
     "handbag, seen from behind and in silhouette against the light, and further along the pavement two other "
     "women in ordinary work clothes walking away from camera at different distances, each with a different "
     "build, coat and hairstyle; every sign and awning blank. Slow lateral tracking move along the street past "
     "the doorway, " + HOLD,
     "店铺关门声 + 街道环境音"),
    ("S20", "agnes", "斑马线低机位缓慢跟移", "四十八岁的主妇，买完菜回家",
     "接动态镜：公交站里的女大学生",
     "A South Korean residential crossroads on a grey November afternoon in 2008: a woman in her late forties in "
     "a quilted vest carries two full grocery bags in both hands across a zebra crossing at a measured pace, "
     "seen from a low angle behind and to the side so her face is not visible; a bicycle and a parked delivery "
     "scooter wait at the kerb, low-rise apartment blocks with drying laundry on the balconies behind, every "
     "shop front and packet blank. Slow low tracking move across the crossing with the walking woman, " + HOLD,
     "车辆驶过 + 风声"),
    ("S21", "agnes", "公交站中景缓慢推进", "二十一岁的女大学生，在等车",
     "接动态镜：派出所里的登记表",
     "A suburban South Korean bus stop on a cold grey morning in November 2008: a young woman in a university "
     "duffel coat with a backpack stands beside the shelter post reading a folded leaflet, seen from behind and "
     "slightly to the side so her face is not visible; a single bench, a rusted litter bin and a bare tree on "
     "the wet verge, a village lane and low hills behind, the timetable panel and leaflet completely blank. "
     "Slow medium push from across the road toward the waiting figure, " + HOLD,
     "冬风 + 远处公交车"),
    ("S22", "agnes", "俯拍登记表缓慢横移", "派出所里，七张失踪登记表",
     "接信息卡：没有并案",
     "A small South Korean police station counter in 2008: seven buff missing-person forms lie side by side in a "
     "row on the counter, each with a blank photograph frame clipped to the corner, and a middle-aged male "
     "detective {C2} leans over them in his shirt sleeves with one palm flat on the counter, looking along the "
     "row with a tired set expression; a rotary phone, an ink pad and a pen cup at the edge, every form and "
     "notice blank. Slow overhead push across the row of forms toward the detective's hands, " + HOLD,
     "电话铃声 + 纸张翻动"),
    ("S23", "graphic", "信息卡（静帧）", "档案：八起失踪，没有并案",
     "接 N04：二〇〇九年一月的破局",
     "案件档案：分属不同辖区 · 没有并案 · 一条线三年后才连上",
     "低音撞击"),

    # ---------------- N04（7 镜：6 动态 + 1 信息卡）----------------
    ("S24", "agnes", "从警局远景缓慢推进", "二〇〇九年一月：监控把车拉了回来",
     "接动态镜：深夜的监控室",
     "A South Korean police station at night in January 2009 seen from across a wet forecourt: a row of parked "
     "white patrol cars with their lights off, two officers in plain coats walking toward the entrance with "
     "their backs to camera, and above them lit office windows where several figures lean over desks; rain "
     "films the asphalt, a bare tree stands at the gate, the building facade carries no signage or lettering. "
     "Slow wide push from the forecourt toward the lit windows of the building, " + HOLD,
     "夜雨 + 低频悬念音"),
    ("S25", "graphic", "信息卡（静帧）", "名片：二〇〇九年一月 · 一辆黑色轿车",
     "接动态镜：那辆车，和车主",
     "案件名片：时间 · 转机 · 线索",
     "低音撞击"),
    ("S26", "agnes", "从屏幕缓慢下摇到记录纸", "监控反复拍到那辆黑色轿车",
     "接动态镜：车主不是开车的人",
     "A dark 2009 Korean CCTV review room at night: a large CRT monitor on a metal trolley shows grainy "
     "monochrome footage of a wide dark sedan crossing an empty junction, marked on screen by a hand-drawn "
     "rectangle in grease pencil and no readable digits; a middle-aged male detective {C2} stands just behind "
     "the trolley with his back half to camera, one hand raised toward the screen, its reflection lying across "
     "his face; a desk fan and a cold cup of coffee beside him. Slow tilt down from the glowing screen to the "
     "desk and a stack of blank printouts, " + HOLD,
     "录像带运转 + 低频鼓点"),
    ("S27", "agnes", "文件特写缓慢拉焦到警员脸", "车主是位母亲，开车的是她儿子",
     "接动态镜：凌晨的焦黑车壳",
     "A South Korean police office desk in January 2009 under a green-shaded lamp: three blank vehicle "
     "registration cards lie side by side next to a magnifier and a pen, and a middle-aged male detective {C2} "
     "leans in from the right with one finger resting on the middle card, his brows drawn together in "
     "concentration, his eyes lifting slowly from the cards toward the lens; the wall behind is bare and "
     "everything on the desk is blank with no readable numbers. Slow rack focus from the blank cards up to the "
     "detective's focused face, " + HOLD,
     "笔尖划纸 + 低频鼓点"),
    ("S28", "agnes", "低机位绕行至焦黑车壳", "那天凌晨五点，他把车烧了",
     "接动态镜：烧掉的车与硬盘",
     "A cold pre-dawn dirt lot behind a South Korean workshop on 24 January 2009: the charred remains of a large "
     "sedan stand in the middle distance with embers glowing faintly inside the engine bay and smoke rising into "
     "the lamp light, while in the foreground a second burnt car body lies on its rims with its doors gone; two "
     "investigators in dark coats stand with their backs to camera behind a line of yellow tape, one holding a "
     "torch beam on the wreck. Nothing in frame carries readable text. Low tracking move past both burnt cars "
     "toward the investigators, " + HOLD,
     "余烬 + 低沉鼓点"),
    ("S29", "agnes", "从走廊远端缓慢推近", "同一天傍晚：紧急逮捕",
     "接动态镜：国科搜的那一点血",
     "A bare police station corridor in January 2009 with a terrazzo floor and doors along one side: a man of "
     "thirty-nine in a plain dark anorak {C1} walks toward the camera flanked and slightly trailed by two "
     "uniformed officers, his head level and his expression ordinary and unremarkable, hands empty and visible "
     "at his sides, his eyes meeting the lens steadily; the corridor is otherwise empty and its walls, doors and "
     "notice boards are blank. Slow tracking push backwards ahead of the walking trio along the corridor, " + HOLD,
     "脚步声 + 铁门声"),
    ("S30", "agnes", "微距缓慢推近袖口", "一滴血，锁住整条证据链",
     "接 N05：六天的沉默",
     "A forensic laboratory in January 2009 under a hard inspection lamp: a dark blue quilted jacket lies on "
     "white paper with its right cuff folded back and pinned open, a small dry dark stain visible on the fabric, "
     "and a gloved hand holds a fine stainless swab directly over the stain while a second hand positions a "
     "clear sample tube below; a magnifier lamp and a rack of sealed tubes sit in soft focus above the bench, "
     "every label blank. Extremely slow macro push toward the stain and the swab tip, " + HOLD,
     "仪器提示音 + 呼吸声"),

    # ---------------- N05（8 镜：7 动态 + 1 信息卡）----------------
    ("S31", "agnes", "固定中景缓慢推近录音机", "六天，他只反问：证据呢",
     "接信息卡：供述",
     "A plain South Korean interrogation room in January 2009: a metal table with a water bottle, a paper cup, "
     "an ashtray, a thin stack of blank forms and a cassette recorder sits between two chairs, one occupied by "
     "a man of thirty-nine in a dark anorak {C1} leaning back with arms crossed and a level unreadable gaze, "
     "the other by a middle-aged detective seen from behind, shoulders only; bare grey "
     "walls, a single high vent, a wall clock without numerals. Fixed "
     "medium shot with a very slow push toward the cassette recorder, " + HOLD,
     "时钟声 + 录音机轻响"),
    ("S32", "graphic", "信息卡（静帧）", "档案：第六天，他开口了",
     "接动态镜：他抬头的那一夜",
     "案件档案：七起供述 · 追加旌善一起 · 物证最少的那起是他说出来的",
     "低音撞击"),
    ("S33", "agnes", "从桌面缓慢上摇到他的脸", "第六天，他开口供述",
     "接动态镜：旌善山区的警车",
     "The same plain South Korean interrogation room at night in January 2009: the man of thirty-nine in the "
     "dark anorak {C1} sits upright at the metal table with both forearms on the surface and hands loosely "
     "clasped, his head raised and his eyes open and calm as he speaks with an unhurried, matter-of-fact "
     "manner, mouth slightly open mid-sentence; a cassette recorder turns between them, bare plaster walls "
     "with no numerals. Slow tilt up from "
     "the table surface to his face and hold on his unhurried expression, " + HOLD,
     "录音机转动 + 低频弦乐"),
    ("S34", "agnes", "乡道上缓慢前推到警戒线", "他补上的那一件：旌善，二〇〇六年",
     "接动态镜：三玉岭的崖边",
     "A narrow mountain road in the Jeongseon and Yeongwol highlands of Gangwon province on a cold grey morning "
     "in 2009: two white police vehicles stand on the verge with their doors open, uniformed officers with their "
     "backs to camera walk a shallow gully beside the tarmac with a folded evidence board and metal stakes, "
     "yellow tape runs between two pine trunks, mist sits low in the valley below; no signage or lettering "
     "anywhere. Slow dolly forward down the road toward the tape and the working officers, " + HOLD,
     "山风 + 对讲机杂音"),
    ("S35", "agnes", "从崖边缓慢横移俯瞰山谷", "三玉岭：她被找到的地方",
     "接动态镜：林地里的勘查",
     "A high rocky ledge above a deep wooded valley in Gangwon province in 2009: three investigators in plain "
     "outdoor coats stand well back from the edge on the gravel shoulder with their backs to camera, one "
     "crouching to plant a small numbered marker stake while another holds a folded site map; loose rocks and "
     "dry grass at the lip of the drop, the valley below filled with mist and dark pine, the map and stake "
     "blank. Slow lateral move along the lip of the ledge from the standing pair to the crouching "
     "investigator, " + HOLD,
     "风声 + 相机快门"),
    ("S36", "agnes", "低机位缓慢横移过编号标记", "她终于被找到：二〇〇九年四月",
     "接动态镜：检察官办公室",
     "A wooded hillside search site in Gangwon province in the spring of 2009 photographed respectfully from a "
     "low angle: a line of small blank numbered markers is set into the leaf litter along a taped grid, two "
     "investigators in plain overalls and gloves work on their knees with a fine sieve and a folded blue "
     "tarpaulin, seen from behind and in silhouette so nothing of the remains is visible; bare branches, wet "
     "earth and drifted leaves, every marker and tag blank. Slow low lateral move along the row of markers "
     "toward the kneeling investigators, " + HOLD,
     "铁锹轻响 + 低沉弦乐"),
    ("S37", "agnes", "从地图缓慢横移到卷宗", "不是一宗案，是跨了三年的一串",
     "接动态镜：押解进法院",
     "A South Korean prosecutor's office in February 2009 in the afternoon: a middle-aged male prosecutor in a "
     "dark suit and tie {C4} stands behind his desk reading a thick bound file held open in both hands, while "
     "two detectives sit opposite him going through separate stacks of buff folders spread across the desk; a "
     "large wall map of the central Korean peninsula hangs behind him with eleven unmarked pins stuck into it, "
     "a desk lamp and a cold cup of tea on the blotter, every file and map label blank. Slow lateral move across "
     "the desk from the wall map to the prosecutor's hands and the open file, " + HOLD,
     "翻页声 + 低频弦乐"),
    ("S38", "agnes", "背后跟拍缓慢推进", "二〇〇九年二月：杀人、纵火、保险诈骗",
     "接 N06：判决",
     "The exterior steps of a South Korean courthouse in February 2009 in cold flat daylight: a man of "
     "thirty-nine in a dark anorak walks up the steps between two escorting officers, seen from behind so "
     "only the back of his head and shoulders are visible, while a loose crowd of journalists with cameras and "
     "recorders presses in from both sides and a van with its doors open waits at the kerb; the building facade "
     "is plain with no signage or lettering. Slow tracking push behind the walking group up the steps, " + HOLD,
     "人群嘈杂 + 快门声"),

    # ---------------- N06（7 镜：6 动态 + 1 信息卡）----------------
    ("S39", "agnes", "从法官席缓慢横移到被告席", "二〇〇九年四月二十二日：死刑",
     "接动态镜：法院外的等待",
     "A South Korean district courtroom on the morning of 22 April 2009: a judge of around fifty in dark robes "
     "{C5} stands at the high bench reading from a single sheet held in both hands with his head slightly "
     "bowed, a clerk at attention to his left and a seated defence lawyer in a dark suit looking down at a "
     "closed folder to his right; the wooden panelling and public benches are bare and every document, seal and "
     "wall plaque is blank. Slow lateral move along the bench from the judge to the empty defendant's rail "
     "below, " + HOLD,
     "法庭环境声 + 低沉重音"),
    ("S40", "agnes", "人群外缓慢横移", "七月二十三日：二审维持；他放弃上告",
     "接动态镜：拘留所的高墙",
     "The forecourt of a South Korean courthouse on a summer afternoon in July 2009: a loose crowd of about "
     "twenty people stands behind a line of plain metal barriers, all seen from behind or in silhouette with no "
     "faces discernible, some holding blank placards and thin banners with no writing, a row of journalists' "
     "cameras raised at the front, plain stone steps beyond them; a hazy sky and dense green trees complete the "
     "frame, every banner blank. Slow lateral move along the barrier line from the back of the crowd toward the "
     "courthouse steps, " + HOLD,
     "人群低语 + 蝉声"),
    ("S41", "graphic", "信息卡（静帧）", "档案：判决时间线",
     "接动态镜：拘留所的高墙",
     "判决时间线：一审四月二十二日死刑 / 七月二十三日二审维持 / 放弃上告 · 死刑确定",
     "低音撞击"),
    ("S42", "agnes", "低机位沿高墙缓慢横移", "十七年，他还在等执行",
     "接动态镜：牛棚里的镐头",
     "The outer perimeter of a South Korean detention facility at first light: a long high concrete wall topped "
     "with coiled wire runs across the frame, a single unlit watchtower stands at the far corner, and a narrow "
     "drainage channel with bare weeds borders it in the foreground; frost covers the ground, low cloud sits "
     "behind the wall, no signage, number or emblem anywhere on the wall or the tower. Very slow low lateral "
     "move along the base of the wall from the weeds to the watchtower, " + HOLD,
     "风声 + 远处金属门"),
    ("S43", "agnes", "微距缓慢横移到镐头", "牛棚里：不属于任何人的两份 DNA",
     "接动态镜：清晨的街道",
     "A dim farm shed interior in South Korea photographed years after the fact: on a rough wooden pallet lie a "
     "rusted pickaxe with a weathered handle, a coil of stiff rope and a folded tarpaulin under a single shaft "
     "of light from a high vent, dust suspended in the beam; the packed-earth floor is scattered with straw and "
     "a metal bucket stands at the edge of frame, cobwebs hang from the rafters, no surface carries readable "
     "text or numbers. Slow macro dolly sideways from the coil of rope to the head of the pickaxe, " + HOLD,
     "谷仓回声 + 低频弦乐"),
    ("S44", "agnes", "清晨街道缓慢横移", "生活继续，名字不该被抹掉",
     "接动态镜：结尾的城镇远景",
     "An ordinary South Korean neighbourhood street at seven in the morning: women of different ages in work "
     "coats walk away from camera along both pavements toward a bus stop and a subway entrance, one carrying a "
     "lunch bag, another a folded umbrella, their faces not visible; a shopkeeper in an apron rolls up a "
     "shutter, a delivery scooter waits at the kerb, morning light falls between low-rise blocks, every shop "
     "sign and shutter blank. Slow gentle lateral move along the pavement following the walking women, " + HOLD,
     "清晨环境音 + 温和弦乐"),
    ("S45", "agnes", "远景缓慢拉远", "结尾：十个人，和一个还没关上的问号",
     "接片尾卡",
     "A wide early-morning view of a South Korean provincial town from a low hill on the edge of it: low-rise "
     "blocks and tiled roofs spread below under a pale winter sky, a river and a highway bridge at the far "
     "edge, thin mist lying in the streets, a single street lamp still lit on the nearest road; the frame is "
     "empty of people and vehicles and holds no signage, lettering or logos anywhere. Very slow aerial pull-back "
     "and rise from the nearest rooftops to the whole town and the hills beyond, " + HOLD,
     "弦乐渐强后收束"),
]

CARD_HEADER = "案件档案  /  京畿道西南部 · 二〇〇五至二〇〇九"      # 每张信息卡左上角的小字
CARD_FOOTER = "公开报道口径 · 并非原始档案影像"                    # 每张信息卡左下角的小字
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S02": ("姜浩顺连环杀人案", "韩国京畿道 · 二〇〇五至二〇〇八", "十名女性遇害 · 一滴血锁定"),
    "S10": ("二〇〇五年十月三十日", "京畿道安山 · 住宅火灾", "妻子与岳母死亡 · 他从火里逃出"),
    "S18": ("失踪档案", "二〇〇六年九月 — 二〇〇八年十二月", "八名女性失踪 · 年龄十九至五十二岁"),
    "S23": ("三年，没有并案", "八起失踪 · 分属不同辖区", "没有一条线，把她们连起来"),
    "S25": ("二〇〇九年一月", "一辆黑色轿车 · 被监控反复拍到", "车主六十三岁 · 开车的是她儿子"),
    "S32": ("第六天，他开口了", "七起杀人 · 追加旌善一起", "最缺物证的那起，是他自己交出来的"),
    "S41": ("判决时间线", "二〇〇九年四月二十二日 一审死刑", "七月二十三日二审维持 · 他放弃上告"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["姜浩顺连环杀人案", "一滴袖口的血 · 十名女人 · 韩国 2005—2009"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "她们的名字，记住了吗？",
    "姜浩顺连环杀人案 · 二〇〇五至二〇〇九 · 十人遇害",
    "十个人是认定的数字；不确定的，还在那里。",
    "资料：维基百科 / KBS / SBS / 朝鲜日报 / 首尔新闻 · 原创解说 · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词）
CAPTION_KEYWORDS = [
    "姜浩顺", "军浦", "保健所", "二〇〇八年十二月十九日", "女大学生", "黑色轿车",
    "取款机", "假发", "避孕套", "火", "二〇〇五年十月三十日", "安山", "妻子", "岳母",
    "四亿八千万韩元", "纵火", "旌善", "二十三岁", "二〇〇六年九月七日",
    "十九岁", "五十二岁", "七起", "第六天", "袖口", "一滴", "DNA", "国科搜",
    "一月二十四日", "紧急逮捕", "死刑", "四月二十二日", "七月二十三日", "十名女性",
    "放弃上告", "十七年", "牛棚", "镐头", "十个人",
]
# 逐镜标签覆盖：默认镜头标「AI动画情景重现 · 非新闻影像」，办案/审讯/庭审/鉴定镜头写得更具体
LABEL_OVERRIDES = {
    "S01": "AI动画情景重现 · 非监控影像",
    "S03": "AI动画情景重现 · 非监控影像",
    "S04": "AI动画情景重现 · 非警方办案影像",
    "S05": "AI动画情景重现 · 非监控影像",
    "S06": "AI动画情景重现 · 非鉴定影像",
    "S07": "AI动画情景重现 · 非现场影像",
    "S08": "AI动画情景重现 · 非抓捕影像 · 非本人容貌",
    "S09": "AI动画情景重现 · 非火灾现场影像",
    "S11": "AI动画情景重现 · 非受害家庭影像",
    "S12": "AI动画情景重现 · 非档案影像 · 非本人容貌",
    "S13": "AI动画情景重现 · 非银行业务影像",
    "S14": "AI动画示意 · 非庭审影像",
    "S16": "AI动画情景重现 · 非失踪者影像",
    "S17": "AI动画情景重现 · 非办公影像",
    "S19": "AI动画情景重现 · 非街头实拍",
    "S20": "AI动画情景重现 · 非街头实拍",
    "S21": "AI动画情景重现 · 非街头实拍",
    "S22": "AI动画情景重现 · 非警方办案影像",
    "S24": "AI动画情景重现 · 非警方办案影像",
    "S26": "AI动画情景重现 · 非监控影像",
    "S27": "AI动画情景重现 · 非警方办案影像",
    "S28": "AI动画情景重现 · 非现场影像",
    "S29": "AI动画情景重现 · 非抓捕影像 · 非本人容貌",
    "S30": "AI动画情景重现 · 非鉴定影像",
    "S31": "AI动画情景重现 · 非审讯影像 · 非本人容貌",
    "S33": "AI动画情景重现 · 非审讯影像 · 非本人容貌",
    "S34": "AI动画情景重现 · 非搜查现场影像",
    "S35": "AI动画情景重现 · 非搜查现场影像",
    "S36": "AI动画情景重现 · 非搜查现场影像",
    "S37": "AI动画情景重现 · 非检方办案影像",
    "S38": "AI动画情景重现 · 非押解影像 · 非本人容貌",
    "S39": "AI动画示意 · 非庭审影像",
    "S40": "AI动画示意 · 非庭审影像",
    "S42": "AI动画情景重现 · 非监狱实景",
    "S43": "AI动画情景重现 · 非证物影像",
    "S45": "AI动画情景重现 · 非实景航拍",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S04", "paper"),
    ("S06", "machine"),
    ("S08", "press"),
    ("S11", "keys"),
    ("S14", "press"),
    ("S22", "phone"),
    ("S26", "machine"),
    ("S30", "machine"),
    ("S32", "paper"),
    ("S34", "press"),
    ("S37", "paper"),
    ("S42", "machine"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "他烧了车、格式化了硬盘，却败在一件夹克袖口上的一滴血",
    "韩国京畿道连环杀人案：十名女性，三年失踪，没有人把它们连成一条线",
    "取款机前的假发和避孕套手指：警方靠这一幕锁定了姜浩顺",
]
HOOK = ("二〇〇六到二〇〇八年，韩国京畿道西南部八名女性接连失踪遇害，年龄从十九岁到五十二岁，"
        "警方始终没有并案；二〇〇八年十二月十九日军浦保健所前一名女大学生被绑架，"
        "一台自动取款机的摄像头、一件夹克袖口上的一滴血，才把这条线连起来——凶手是姜浩顺，"
        "他早在一九九五年就为保险金烧死过自己的妻子和岳母。")
GOLDEN_LINES = [
    "十个人是认定的数字；不确定的，还在那里。",
    "他提前烧掉了车，格式化了硬盘，却留下一滴不到一克的血。",
    "她们唯一的共同点，是独自走在回家的路上。",
]
DESCRIPTION = (
    "一九六九年出生的姜浩顺，二〇〇五年十月三十日为保险金在安山放火，妻子与岳母死亡，他拿到约四亿八千万韩元理赔；"
    "二〇〇六年九月七日起，他在京畿道西南部与江原道旌善绑架杀害多名女性，年龄从十九岁到五十二岁。"
    "二〇〇八年十二月十九日，一名女大学生在军浦保健所前公交站被绑架，警方顺着一辆黑色轿车、"
    "她用信用卡取款时的监控、以及国科搜从夹克右侧袖口检出的一滴血锁定了他。"
    "二〇〇九年四月二十二日一审死刑，七月二十三日二审维持，他放弃上告，死刑确定；"
    "他至今仍在首尔拘留所，韩国自一九九七年起未再执行死刑。"
    "本片画面为AI生成的情景重现（非新闻影像、非本人容貌），事实依据公开报道整理。"
)
QUESTION = "如果当年有一套跨辖区的失踪人口并案机制，这条线会不会早两年连上？评论区聊聊。"
HASHTAGS = ["#悬疑", "#真实案件", "#韩国", "#案件解说", "#犯罪心理"]

GRID = 4            # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 6   # 每个镜头实际请求的时长（智谱 CogVideoX-Flash 免费档单条约 5–6 秒，render 按需裁切）
SEED_BASE = 20051030  # 安山火灾日（二〇〇五年十月三十日），让 seed 可追溯

# 露脸镜头登记（镜头号 -> 角色 id）：只有这里登记的镜头允许出现面容 token，
# 与 cast.json 的 shots 映射一一对应（face_cast.py check-prompts 两边都查）。
FACE_SHOTS = {
    "S04": ["C2"],
    "S05": ["C3"],
    "S12": ["C1"],
    "S14": ["C4"],
    "S22": ["C2"],
    "S26": ["C2"],
    "S27": ["C2"],
    "S29": ["C1"],
    "S31": ["C1"],
    "S33": ["C1"],
    "S37": ["C4"],
    "S39": ["C5"],
}
# 用定妆照做首帧（图生视频）的镜头：每个角色的首次露脸镜头，把这张脸钉在观众第一眼里。
# 定妆照提交在仓库里，URL 取 cast.json 的 portrait_url。
REFERENCE_SHOTS = {"S04": "C2", "S05": "C3", "S12": "C1", "S14": "C4", "S39": "C5"}


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
        assert kind in ("agnes", "agnes", "graphic"), f"{sid}: kind 只能是 cogvideo / graphic"
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
        "视频模型走智谱 CogVideoX-Flash 免费档（generate_cogvideox.py）；"
        "解说词与 screenplay.md、audio/manifest.json 三处逐字一致由 generate.py --validate 守着。")
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")

    manifest = json.loads(MANIFEST.read_text())
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        assert clip["id"] == chapter["id"]
        clip["text"] = chapter["text"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    kinds = [s["kind"] for s in story["shots"]]
    chars = sum(len(c["text"]) for c in story["chapters"])
    print(f"story.json 已写入：{len(shots)} 镜 = {kinds.count('agnes')} cogvideo + {kinds.count('graphic')} graphic，"
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
        from script_table import publish_document  # noqa: E402
        out = HERE / "抖音发布文案.md"
        out.write_text(publish_document())
        print(f"抖音发布文案.md 已写入（{len(out.read_text())} 字符）")
    else:
        build()

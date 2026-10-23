#!/usr/bin/env python3
"""《玛丽·赛勒斯特号：海上最大的未解之谜》的全部内容源。

这是这部片子**唯一需要动脑写的文件**（引擎由 production/kitakyushu2002 北九州案模板移植而来，
内容按用户提供的 29 镜脚本逐镜落实，见本目录《史实核对.md》）。

用法::

    python3 production/maryceleste1872/build_story.py            # 写 story.json + audio/manifest.json 的逐字文本
    python3 production/maryceleste1872/build_story.py --script   # 生成 抖音脚本.md
    python3 production/maryceleste1872/build_story.py --publish  # 生成 抖音发布文案.md

本片是**露脸模式**：四个角色各一张不同的脸（布里格斯船长 / 莎拉 / 苏菲亚 / 摩尔豪斯船长），
同一角色跨镜头逐字节复用同一条面容 token（token 只在 cast.json 里写一份，本文件用 {C1}…{C4}
占位符注入），由 production/face_cast.py 的 check-prompts / check-frames 两道闸门守着；
七名船员与上帝的恩典号水手全程背影或剪影（用户脚本规定）。

视频模型走**智谱 CogVideoX-Flash 免费档**（generate_cogvideox.py，不产生费用）。

分镜与解说逐句咬合的章法（用户 29 镜脚本 = 28 个叙事镜头 + 片尾标题卡；其中镜头 5 / 7 / 18
各含一次内部硬切，按“每个镜头一段真实运动的动画”拆成 5A/5B、7A/7B、18A/18B，合计 31 个
CogVideoX 动态镜头 + 片尾卡，每镜只出现一次）：

  N01 黄金钩子（S01-S02）· N02 启航（S03-S05B）· N03 发现幽灵船（S06-S09）
  N04 诡异细节（S10-S15）· N05 猜想一：海盗与叛变（S16-S18B）
  N06 猜想二：海怪与天灾（S19-S21）· N07 最合理的解释（S22-S26）· N08 结尾反转（S27-S28）
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "玛丽·赛勒斯特号：海上最大的未解之谜"
FILM_NAME = "玛丽赛勒斯特号_海上最大的未解之谜_三分钟_带声音.mp4"

# 全片统一的画面风格前缀（英文；用户【STYLE】逐条落实：皮克斯级 3D 渲染 × 暗黑童话氛围、
# 体积雾、真实水体、冷蓝海水与暖金油灯强对比、16:9 宽银幕、三分线构图、景深虚化）。
# 注意：style_prefix 参与全部镜头的 request_hash，开工后改一个字 = 全部镜头重做。
# 「16 帧动态」按“filmic motion”落实（模型输出实测 37 fps，渲染端统一到 30 fps）。
STYLE_PREFIX = (
    "Cinematic 3D animation with Pixar-grade feature-animation rendering blended with a dark "
    "fairy-tale mood: realistic lighting, volumetric fog and haze, physically simulated open-ocean "
    "water, cold blue seas and skies in strong contrast with the warm golden glow of oil lamps, high "
    "contrast, richly detailed frames with layered saturated colour, 16:9 widescreen compositions "
    "with the main subject on the rule-of-thirds lines and the full width of frame used, cinematic "
    "lens language, shallow depth of field and filmic motion with natural motion blur. Photorealistic "
    "CGI historical reenactment at sea in 1872: wooden sailing ships, rope rigging, canvas sails, "
    "oil lamps, weathered wood and brass; period clothing only; never a drawing, never a flat cartoon, "
    "never a still image with a zoom; real movement in every shot, one single continuous smooth camera "
    "move per shot exactly as directed; absolutely no readable text, letters, numbers, logos or brand "
    "marks anywhere in frame. "
)

# 用户【NEGATIVE】逐条落实（模型基本无视独立负面字段，红线压进提示词正文，见 model_policy）。
NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, subtitles, captions, watermarks, logos, "
    "brand marks, modern objects, modern ships, motorboats, cars, electricity pylons, low resolution, "
    "blurriness, flicker, sudden style changes, vertical framing, letterboxing, pillarboxing, black "
    "bars, malformed fingers, extra limbs, duplicated limbs, deformed faces, face morphing mid-shot, "
    "the likeness of any identifiable real person, blood, gore, wounds, corpses, flat 2D cartoon, "
    "cel-shaded illustration, comic panel, morphing objects, jitter, whip pans, jump cuts, split "
    "screen, slideshow, ken-burns still"
)

# 事实边界与红线：每一条都会印在 抖音脚本.md 的「发布前自查」里。
PRINCIPLES = [
    "全部动态镜头为写实 3D CGI 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，"
    "不冒充新闻、档案、证物或现场影像",
    "一八七二年的历史人物（布里格斯船长一家、摩尔豪斯船长与船员）由符合年代的虚构匿名角色扮演，"
    "不做真实人物肖像还原；片内标签写明「虚构角色 · 非本人容貌」",
    "七名船员与上帝的恩典号水手全程只以背影、剪影出现，不给可辨识面容",
    "不展示遗体、血腥或伤害过程：十人消失只通过空镜头、物件与气氛表现（空荡甲板、停摆的船舵、"
    "倒扣的小鞋、断裂的绳头）；海盗与海怪只出现在「猜想」段落并标注「AI动画猜想示意」",
    "四个露脸角色各有一张不同的脸；同一角色跨镜头逐字节复用同一条面容 token 并共用同一个 seed，"
    "由 production/face_cast.py 两道闸门检查，人眼对照接触表判决",
    "每一句事实都能指到 sources 里的公开来源；口径冲突处（日志最后日期的两种记法、爆燃实验的"
    "具体人名等）只写多源一致的写法，不挑一个当结论",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写；画面内不出现任何可读文字",
    "人工检视 qa/ 接触表；换脸、畸变、伪文字、中途换场的镜头用 {\"only\":\"Sxx\"} 重生成，"
    "不直接进成片",
    "「酒精蒸汽爆燃」只写作最合理的猜想之一，成片明确说「没有人能证明」，不写成定论",
]

# 每条事实的公开来源。
SOURCES = [
    {"id": 1, "url": "https://en.wikipedia.org/wiki/Mary_Celeste",
     "usage": "支撑：一八七二年十一月七日自纽约启航前往意大利热那亚；船长本杰明·布里格斯与妻子、"
              "两岁女儿及七名船员共十人；载约一千七百桶变性酒精；十二月四日被发现时人去船空，"
              "货物、给养与船员私人物品基本原样；救生艇失踪；日志最后条目停在十天前"},
    {"id": 2, "url": "https://en.wikipedia.org/wiki/Dei_Gratia_(brigantine)",
     "usage": "支撑：发现者为双桅船「上帝的恩典号」（Dei Gratia），摩尔豪斯船长指挥；"
              "在亚速尔群岛附近发现漂航的玛丽·赛勒斯特号；水手乘小艇靠帮登船查看"},
    {"id": 3, "url": "https://www.britannica.com/topic/Mary-Celeste",
     "usage": "支撑：案件作为『海上最大未解之谜』的通行表述；船体当时几乎完好、无明显打斗痕迹；"
              "船货（工业酒精）与给养俱在"},
    {"id": 4, "url": "https://www.smithsonianmag.com/history/mary-celeste-ghost-ship-180976734/",
     "usage": "支撑：酒精蒸汽假说——现代实验演示密闭货舱内酒精蒸汽可发生几乎没有火光的爆燃、"
              "冲开舱盖而几乎不留痕迹；该假说是目前最广为接受的解释但无直接证据"},
    {"id": 5, "url": "https://zh.wikipedia.org/wiki/%E7%8E%9B%E4%B8%BD%C2%B7%E5%A1%9E%E5%8B%92%E6%96%AF%E7%89%B9%E5%8F%B7",
     "usage": "支撑（中文通行译名）：玛丽·赛勒斯特号、上帝的恩典号、亚速尔群岛等译名口径；"
              "『幽灵船』叙事在中文世界的通行说法"},
]

# 八段解说：(章节 id, 章节标题, 逐字解说词)。数字按中文读法写，TTS 才不会念错。
# 2026-10-23 v3 重写（用户反馈「解说词平淡、比画面短很多」）：按画面逐镜写满，
# 史实口径不变（日志停在十天前 / 爆燃实验不点名 / 上帝的恩典号），关键台词
# 锚点（全都消失了 / 一个人都没有 / 绳子断了 / 你觉得）与金色关键词全部保留。
CHAPTERS = [
    ("N01", "黄金钩子：十个人，全都消失了",
     "一八七二年，大西洋上漂着一艘船。灯火未熄，早餐未凉，可是十个人，全都消失了。"),
    ("N02", "启航：纽约到热那亚",
     "十一月七日，纽约天刚亮。玛丽·赛勒斯特号启航，驶向意大利热那亚。"
     "船长布里格斯，带上妻子和两岁的女儿。七名船员各就各位，帆索绷紧。"
     "货舱里，一千七百多桶工业酒精静静堆着。"),
    ("N03", "发现幽灵船",
     "一个月后，十二月四日，亚速尔群岛附近。另一艘船「上帝的恩典号」发现了它。"
     "可它的帆破破烂烂，航向歪歪扭扭，像喝醉了酒。摩尔豪斯船长连喊几声，海上一片死寂。"
     "水手们放下小艇，贴着船舷爬上去。甲板上，一个人都没有。"),
    ("N04", "船上的诡异细节",
     "船体几乎完好，食物和淡水够吃半年。船员的行李都在，小女孩的红外套和布偶兔子，"
     "还留在小床上。可是救生艇不见了，航海仪器也不见了，只留下拆开的抽水泵和敞开的工具箱。"
     "最后一篇日志，停在十天前，笔迹平平稳稳，断在半页。没有打斗痕迹，没有求救信号。"
     "他们是自己离开的，还是被什么带走的？"),
    ("N05", "猜想一：海盗与叛变",
     "有人说是海盗干的。黑旗升起，刀光映着火把。可值钱的货物，一件没少。"
     "有人说是船员叛变。可船长威望极高，水手们都服他，现场也没有半点争斗的痕迹。"
     "两个猜想，两处说不通。"),
    ("N06", "猜想二：海怪与天灾",
     "有人说是巨型乌贼，从深海伸出触手，把船拖进地狱。有人说是海上龙卷风，"
     "或者海底地震，一夜之间掀翻了它。听起来够刺激。可是，船本身几乎完好，"
     "桅杆还在，船帆还在，不像遭遇过任何毁灭性的灾难。"),
    ("N07", "最合理的解释",
     "近年来，科学家做过实验。密闭舱室里，酒精蒸汽能引发一次几乎没有火光的爆燃，"
     "冲开舱盖，却不留下多少痕迹。这或许能解释一切：船长以为大船随时会再炸，"
     "命令所有人立刻登上救生艇，再用一根长绳，把小艇拴在大船后面。"
     "可是，一阵风浪袭来，绳子断了。"),
    ("N08", "结尾：没有人能证明",
     "大船张满帆继续前行，而救生艇，再也没人见到。这解释最合理，却没有人能证明。"
     "你觉得，他们到底遇到了什么？"),
]

# 每章在成片里的窗口（用户脚本的八段时间轴；片尾卡 177–180 秒单列）。
CHAPTER_WINDOWS = {
    "N01": (0.0, 10.0), "N02": (10.0, 30.0), "N03": (30.0, 55.0), "N04": (55.0, 90.0),
    "N05": (90.0, 110.0), "N06": (110.0, 135.0), "N07": (135.0, 164.0), "N08": (164.0, 177.0),
}

HOLD = ("no cut, no scene change, no camera relocation, no extra people, no modern objects, "
        "no readable text in frame; hold on this single view for the full clip.")

# 船体设定（用户【船体设定】逐条落实；出现船的镜头一律拼接对应 token）。
SHIP_INTACT = (
    "the Mary Celeste, an 1870s two-masted brigantine about thirty metres long with a bright "
    "well-kept white hull, a dark red sheer line along the gunwale, a dark brown wooden deck, "
    "a brass ship's bell and two tall masts carrying full clean white sails bellying with wind"
)
SHIP_GHOST = (
    "the Mary Celeste ghost ship, an 1870s two-masted brigantine about thirty metres long with a "
    "weathered white hull streaked by salt and sea corrosion, a dark red sheer line along the "
    "gunwale, a dark brown wooden deck, a brass ship's bell and two tall masts; several sails torn "
    "and fluttering, ropes slack and trailing, the ship looking aged and eerie, one oil lamp swinging"
)
SHIP_DEI = (
    "the Dei Gratia, an 1870s merchant sailing ship slightly larger than a brigantine with a plain "
    "black hull, two masts with full white sails and a working merchant deck of rope coils and a "
    "wooden helm"
)

SHOTS = [
    # ---------------- N01 黄金钩子（S01-S02）----------------
    ("S01", "远景快推，末尾减速", "钩子：黑夜浓雾中，幽灵船剪影漂来，镜头高速冲向它",
     "接镜头2：越过船舷滑入甲板",
     "On the open Atlantic at night, a vast dark blue-black ocean under heavy fog: the huge ghostly "
     "silhouette of " + SHIP_GHOST + " drifts slowly into view from the far right depth of frame, her "
     "torn sails flickering in the wind; the camera rushes in fast from a great distance low over the "
     "water straight toward the ship, parting the fog as it goes, decelerating at the end to hang just "
     "off the bow; the deck above is visibly empty except for one swinging oil lamp. Fast forward "
     "dolly-in over the water toward the drifting ship, easing to a stop at the end, " + HOLD,
     "海浪声 + 远处一声船钟 + 低沉大提琴渐强"),
    ("S02", "低角度横向跟移，轻微手持晃动", "甲板长镜头：油灯、倾倒木桶、孤零零转动的船舵",
     "接镜头3：一八七二年纽约港清晨",
     "On the deck of " + SHIP_GHOST + " at night, the whole shot staying on this one deck from the "
     "first frame to the last with no exterior and no transition: the camera slides in low over the "
     "rail and tracks left along the long empty deck, past a swinging oil lamp casting warm golden "
     "pools, past a toppled wooden barrel rolling slightly with the roll of the ship, to a lone wooden "
     "ship's wheel slowly turning by itself; cold blue moonlight filters through the fog and waves "
     "slap the hull below. Low-angle handheld-feeling lateral tracking shot along the deck, moving "
     "left with a slight sway, " + HOLD,
     "海浪拍打 + 木头吱呀 + 幽蓝月光氛围"),

    # ---------------- N02 启航（S03-S05B）----------------
    ("S03", "航拍左→右缓慢横摇并下降", "一八七二年纽约港清晨全景，定在白色船身",
     "接镜头4：船长一家登船",
     "The New York harbour at sunrise in November 1872 seen from high above: golden dawn light cuts "
     "through thin mist over a forest of wooden masts, steam drifts from a distant paddle steamer, "
     "wooden piers run into the water, and dock workers in period clothes use hand cranes to hoist "
     "large wooden barrels; berthed at the centre-right pier, " + SHIP_INTACT + ", her white hull "
     "glowing in the low sun. Aerial shot slowly panning left to right while descending, settling "
     "toward the gleaming ship, " + HOLD,
     "海鸥 + 码头嘈杂 + 温暖弦乐"),
    ("S04", "中景侧面跟拍，逐渐推近至小女孩", "船长携妻女登舷梯，小女孩回头挥手，布偶兔子晃动",
     "接镜头5a：货舱里的酒精桶",
     "On a wooden pier and gangway in the New York harbour at sunrise in 1872, warm golden dawn light "
     "and thin mist, the wide harbour behind: {C1} walks slowly up the gangway onto the ship with {C2} "
     "on his arm and {C3} a step ahead; the little girl turns back toward the camera and waves happily, "
     "her old cloth bunny swinging from her other hand, while {C1} rests one proud hand on her small "
     "shoulder; all three act in continuous natural movement. Medium side-tracking shot following the "
     "family up the gangway, then pushing slowly in toward the smiling little girl, " + HOLD,
     "舷梯脚步 + 港口环境声 + 温暖弦乐"),
    ("S05A", "货舱内低角度前移", "镜头5前半：货舱一排排酒精桶，油灯照亮木桶",
     "接镜头5b：甲板升帆",
     "Below decks in the cargo hold of an 1870s sailing ship, the whole shot staying inside this one "
     "hold from the first frame to the last: rows upon rows of neatly stacked wooden barrels stretch "
     "into the depth of the hold, one hanging oil lamp sways gently and lights the curved barrel "
     "staves, which carry only blank painted bands with no letters or numbers; the ship's roll makes "
     "the lamplight drift across the rows. Low-angle camera moving slowly forward between the rows of "
     "barrels toward the depth of the hold, " + HOLD,
     "船体吱呀 + 油灯轻响 + 低频弦乐"),
    ("S05B", "升降镜头仰拍帆面升起", "镜头5后半：七名船员拉缆绳，帆布缓缓升起",
     "接镜头6：望远镜视野里的幽灵船",
     "On the open deck of " + SHIP_INTACT + " in bright morning light: seven rough merchant seamen in "
     "coarse wool sweaters and waterproof canvas jackets, shown mostly as backs and silhouettes, haul "
     "in unison on the rigging lines along both sides of the deck, and a great clean white canvas "
     "sail slowly rises and fills with wind above them against a pale blue sky. Rising crane shot "
     "from deck level tilting up along the lines to the swelling sail, " + HOLD,
     "缆绳摩擦 + 海鸥 + 弦乐渐起"),

    # ---------------- N03 发现幽灵船（S06-S09）----------------
    ("S06", "望远镜视角，轻微抖动缓慢变焦", "镜头6：圆视野里歪歪扭扭的幽灵船",
     "接镜头7a：摩尔豪斯船长喊话",
     "Point of view through a brass ship's telescope held at sea: the circular field of view shows a "
     "wide grey horizon of choppy cold water where a lone sailing ship wallows far away, her sails "
     "torn and her heading confused as she drifts in a slow circle, under a heavy grey overcast sky; "
     "the telescope view shakes slightly in the observer's hands and zooms in a little. Handheld "
     "telescope point-of-view with a slow zoom toward the distant distressed ship, " + HOLD,
     "风声 + 海浪变冷 + 紧张低音弦乐"),
    ("S07A", "中景横移", "镜头7前半：摩尔豪斯船长举手喊话，水手望向幽灵船",
     "接镜头7b：放下小艇",
     "On the deck of " + SHIP_DEI + " under a grey windy sky, the whole shot staying on this deck from "
     "the first frame to the last with no exterior and no transition: {C4} stands at the left of "
     "frame raising one hand to call out toward the far distance, his black canvas coat flapping hard "
     "in the wind, while four tense curious sailors in black waterproof canvas suits crowd at the rail "
     "all looking toward a small distant wallowing ship at the right edge of the horizon; everyone "
     "holds their gaze in the same direction. Medium shot drifting slowly sideways along the rail "
     "from the calling captain to the staring sailors, " + HOLD,
     "风声 + 喊话回声 + 低音弦乐"),
    ("S07B", "海面低机位", "镜头7后半：两个水手把小艇放入海中",
     "接镜头8：小艇靠帮仰拍",
     "Beside the black hull of an 1870s merchant sailing ship on open grey sea: two sailors in black "
     "canvas gear manhandle a small wooden clinker boat over the side, ropes paying out through a "
     "block, the little boat dropping toward the choppy water with a splash of spray, all against "
     "the dark planked hull and grey swell. Low camera at sea level looking slightly up at the hull "
     "as the small boat is lowered into the water, " + HOLD,
     "绳索滑轮 + 落水水花 + 海浪"),
    ("S08", "低机位仰拍，海浪溅到镜头", "镜头8：小艇贴着船舷，水手抓绳梯仰望高高的船身",
     "接镜头9：登船环顾空甲板",
     "At sea level right beside the towering hull of " + SHIP_GHOST + " in grey afternoon swell: a "
     "small wooden boat rides the waves below, a sailor in black canvas gear stands and grips the "
     "rope ladder over the rail, looking up at the huge salt-streaked hull rising and falling above "
     "him with the swell, and a burst of spray flies across the low lens; the empty rail high above "
     "has nobody looking back. Extreme low-angle shot looking up the hull from the small boat, "
     "rocking with the waves, " + HOLD,
     "木头呻吟 + 海浪溅射 + 心跳低频"),
    ("S09", "第一人称缓慢转头360度", "镜头9：空荡甲板、垂落绳索、轻响的船钟、滚动的水桶",
     "接镜头10：船长室",
     "On the deck of " + SHIP_GHOST + " in cold blue-grey daylight at first-person height: the camera "
     "stands at the centre of the long empty deck and turns slowly around: slack ropes hang from the "
     "pin rails, the brass ship's bell swings silently in the wind, a wooden barrel rolls slowly "
     "across the planks and bumps against the rail, and not one person is anywhere on deck. Slow "
     "first-person pan turning all the way around the empty deck, " + HOLD,
     "船钟轻响 + 风声 + 极静氛围"),

    # ---------------- N04 诡异细节（S10-S15）----------------
    ("S10", "缓慢前推，聚焦桌上地图", "镜头10：船长室，凌乱床铺、封窗、摇晃油灯、航海图、全家小画像",
     "接镜头11：厨房",
     "Inside the captain's cabin of an 1870s sailing ship at night, the whole shot staying indoors "
     "from the first frame to the last with no exterior and no transition: a narrow bunk lies rumpled "
     "and unmade, the stern window is boarded over with planks, one oil lamp swings on its chain from "
     "the ceiling and sweeps its warm light across the room, a nautical chart lies spread on the "
     "table with only blank inked coastlines and no lettering, and a small blurred framed family "
     "portrait hangs on the wood-panelled wall. Slow push from the doorway across the cabin, ending "
     "focused on the chart on the table, " + HOLD,
     "油灯摇晃 + 一声『叮』 + 诡异单音钢琴"),
    ("S11", "缓慢环绕一圈", "镜头11：厨房，冷灶、整齐锅碗、没动过的食物",
     "接镜头12：小女孩的小床",
     "Inside the ship's galley of an 1870s sailing ship by day, the whole shot staying in this one "
     "room from the first frame to the last: a black iron stove has gone cold, a stack of tin plates "
     "and pans sits neatly on a shelf, and on the scrubbed table one full bowl of stew stands "
     "untouched with a spoon beside it while pale sea light shimmers through the small window onto "
     "the table. Slow camera orbit around the table and the stove through the small galley, " + HOLD,
     "锅碗轻响 + 一声『叮』 + 心跳低频"),
    ("S12", "特写缓慢下移至布偶，浅景深", "镜头12：小床、红外套、布偶兔子、一只小鞋、舷窗斜光",
     "接镜头13：被拆散的抽水泵",
     "Inside a small sleeping berth of an 1870s sailing ship, pale daylight slanting through a round "
     "porthole, dust motes drifting in the beam: a child's narrow bunk is neatly made, a little red "
     "woollen coat hangs folded over the bed rail, a worn old cloth bunny rabbit lies on the pillow, "
     "and one tiny leather shoe sits alone on the wooden floor; the blade of light moves slowly with "
     "the ship's roll. Close-up shot slowly tilting down from the red coat to the cloth bunny on the "
     "pillow, shallow depth of field, " + HOLD,
     "极静 + 一声『叮』 + 钢琴单音"),
    ("S13", "俯拍转平视，缓慢推近", "镜头13：甲板上拆成零件的抽水泵、打开的工具箱、滚到舷边的木桶",
     "接镜头14：空掉的救生艇绳架",
     "On the deck of " + SHIP_GHOST + " on a grey-blue open sea, seen from above: a brass bilge pump "
     "has been taken apart into its pieces and laid out across the planks, an open wooden toolbox "
     "spills hand tools with plain unmarked handles, and one wooden barrel has rolled against the "
     "bulwark rail; nothing else moves but the slow roll of the deck. Overhead shot descending "
     "slowly to deck level and pushing toward the dismantled pump parts, " + HOLD,
     "工具轻响 + 一声『叮』 + 低频脉冲"),
    ("S14", "低角度仰拍，风吹绳子", "镜头14：船尾空绳架、断绳头垂向海面、空无一物的海平线",
     "接镜头15：航海日志特写",
     "At the stern of " + SHIP_GHOST + " under a pale windy sky, seen from the deck: the empty wooden "
     "davit cranes where a lifeboat once hung stand bare, frayed snapped rope ends sway and tap in "
     "the wind above the rail, and beyond the taffrail the grey horizon is completely empty. "
     "Low-angle shot looking up at the swaying broken ropes against the sky, the ship's roll swaying "
     "the frame, " + HOLD,
     "风声 + 绳头敲击 + 一声『叮』"),
    ("S15", "大特写，镜头轻微下压", "镜头15：航海日志最后一页（停在十一月二十五日），纸张翻动",
     "接镜头16：猜想一的海盗幻象",
     "Extreme close-up of a ship's logbook lying open on a wooden table under a warm swaying oil "
     "lamp: the last pages carry lines of faded brown ink handwriting in an old cursive hand, far too "
     "small and blurred to read, and the writing simply stops halfway down a page with the dry pen "
     "lying beside it; the page corners lift slightly in a draught. Macro shot drifting slowly down "
     "the open page to where the writing stops, slight tilt of the lens downward, " + HOLD,
     "纸张翻动 + 一声『叮』 + 骤停"),

    # ---------------- N05 猜想一：海盗与叛变（S16-S18B）----------------
    ("S16", "快速推近，抖动，红色危险滤镜", "镜头16：猜想幻象——黑旗海盗船逼近，火把影子晃动",
     "接镜头17：幻象冷却打叉",
     "A nightmare imagining at night on the deck of " + SHIP_GHOST + ", lit like a fever dream with a "
     "deep red danger glow: out of the fog at the left of frame a shadowy pirate sailing ship bears "
     "down with a dark flag at its mast, and three gaunt pirate silhouettes with raised curved "
     "cutlasses lean over the rail, their torchlight throwing huge shaking shadows across the sails; "
     "no contact and no violence resolved, everything smoky and half-seen. Fast shaky push-in toward "
     "the looming pirate ship, " + HOLD,
     "鼓点加快 + 铜管短促 + 火焰噼啪"),
    ("S17", "慢速拉远，红色×从中心放大", "镜头17：幻象冷却成灰，货物与金银原封不动，红色大叉盖上",
     "接镜头18a：船员争吵剪影",
     "On the deck of " + SHIP_GHOST + " at dawn, the whole image cooling to pale grey like a myth "
     "dissolving: the shadowy pirate ship fades away into the mist and is gone, while the cargo "
     "stays perfectly untouched — closed wooden crates, tied kegs, and a small open chest of gold "
     "coins and silver plate sitting in plain view on the planks; pale grey light grows across the "
     "deck. Slow pull-back from the untouched chest to the wide quiet deck as the last shadow "
     "dissolves, " + HOLD,
     "『嘭』一声后骤静 + 低频余音"),
    ("S18A", "中景，烛光影子晃动", "镜头18前半：船员围着船长争吵的剪影，影子投在舱壁",
     "接镜头18b：握手缓和再打叉",
     "Inside a dark ship's stateroom at night lit only by one guttering candle on the table: the black "
     "silhouettes of a captain and several crewmen lean at each other around the table in tense "
     "argument, their huge shadows jumping and sliding across the wood-panelled bulkhead behind them, "
     "faces never visible, hands jabbing the air. Static medium shot watching the arguing silhouettes "
     "and their jumping wall shadows, " + HOLD,
     "低沉鼓点 + 影子晃动氛围"),
    ("S18B", "中景稳定镜头", "镜头18后半：气氛缓和，船长与船员冷静握手，再度打上叉",
     "接镜头19：猜想二的海怪幻象",
     "Inside a dark wooden ship's stateroom at night, lit by warm steady candlelight: two men in sea "
     "clothes calmly shake hands across the table while the crewmen behind them stand relaxed with "
     "shoulders dropping, all faces kept soft-focused and turned into the warm shadow; the candle "
     "flame steadies. Stable medium shot holding on the calm handshake as the group settles, " + HOLD,
     "骤静 + 一声低沉打击"),

    # ---------------- N06 猜想二：海怪与天灾（S19-S21）----------------
    ("S19", "大幅度俯冲，配合海浪晃动，泛黄传说质感", "镜头19：巨型乌贼触手缠船（传说插画感）",
     "接镜头20：水龙卷",
     "A legendary imagining on the open Atlantic in heavy swell, treated like a yellowed antique "
     "sea-monster illustration come alive: colossal deep-sea squid tentacles erupt from the water at "
     "both sides of frame and curl around the hull and masts of " + SHIP_GHOST + ", the planks "
     "groaning, spray exploding upward in slow sheets, the whole ship canted in the waves; dramatic "
     "and monstrous but nothing bloody. Big sweeping camera diving and swaying with the waves around "
     "the stricken ship, " + HOLD,
     "宏大管弦乐 + 海怪低吼 + 木板吱呀"),
    ("S20", "航拍广角缓慢拉远，末尾像古画卷褪色", "镜头20：黑色水龙卷、风暴云、雷电、巨浪中的船",
     "接镜头21：风平浪静的幽灵船",
     "On a wide stormy sea under black rotating storm clouds: a huge black water spout tornado rises "
     "from the ocean surface and leans across the horizon, lightning flickering inside the clouds, "
     "and far below at the foot of the storm a small sailing ship rides enormous waves, pitching "
     "hard; rain streaks the whole frame; the scene slowly loses colour like an antique scroll "
     "painting fading. Wide high aerial shot slowly pulling back and up from the storm and the tiny "
     "ship, " + HOLD,
     "雷声 + 风暴呼啸 + 骤然安静"),
    ("S21", "缓慢推近，安静而压抑", "镜头21：回到平静幽灵船，晨光穿过云层照在船帆上",
     "接镜头22：货舱剖面蒸汽",
     "On the open Atlantic at dawn after the storm, calm and quiet: " + SHIP_GHOST + " lies almost "
     "motionless on a glassy windless sea, her hull nearly intact and her torn sails hanging slack, "
     "and one wide ray of morning sun breaks through the clouds and falls on the pale sails; the "
     "water is quiet, the sky pale blue-grey, nothing moves but the slow swell. Slow quiet push-in "
     "toward the still ship across the mirrored water, " + HOLD,
     "风平浪静 + 骤然安静 + 压抑低频"),

    # ---------------- N07 最合理的解释（S22-S26）----------------
    ("S22", "横向剖面缓慢移动，体积雾", "镜头22：货舱剖面——酒精渗出、淡蓝蒸汽弥漫（科学可视化）",
     "接镜头23：舱盖被气浪掀开",
     "A clean scientific cutaway side view of the cargo hold of an 1870s sailing ship in motion, as "
     "if the hull were sliced open like a museum model: inside the rows of wooden barrels, clear "
     "alcohol seeps from loosened barrel seams and dribbles onto the planking, pale blue-white vapour "
     "spreads and pools among the barrels, glowing particles drifting in the volumetric haze while "
     "the ship's roll sloshes the liquid. Slow lateral move along the cross-section through the "
     "vapour-filled hold, " + HOLD,
     "悬疑钢琴 + 低频脉冲渐强 + 液体滴落"),
    ("S23", "瞬间慢动作，环绕镜头，冲击波扩散", "镜头23：舱盖被白色气浪掀开（无火焰），人被震退",
     "接镜头24：放救生艇",
     "On the deck of " + SHIP_GHOST + " in grey daylight at the moment of a silent pressure blast: "
     "the heavy cargo hatch cover bursts open and flies upward on a blast of white vapour and "
     "shockwave air — no flame and no fireball at all — dust and grit blast outward, three distant "
     "crew figures stagger back from the hatch with arms raised, and the brass bilge pump topples "
     "over across the planks. Dramatic slow-motion orbiting shot around the erupting hatch as the "
     "white shockwave expands, " + HOLD,
     "一声沉闷『咚』+ 耳鸣 + 气浪"),
    ("S24", "甲板手持跟拍转海面低机位", "镜头24：船长指挥、家人登救生艇、长绳系住小艇",
     "接镜头25：绳子断开",
     "On the deck of " + SHIP_GHOST + " in rising wind and grey light: {C1} stands near the rail "
     "shouting urgent commands and pointing seaward with a firm arm while crewmen in wool sweaters "
     "heave on the falls to lower a small wooden boat; {C2} hurries past clutching {C3} tight "
     "against her shoulder, the little girl's face buried against her mother's shawl, and a long "
     "rope is knotted from the ship's rail to the bow of the boat as it swings down toward the "
     "water. Handheld deck tracking shot following the captain's commands and the mother and child "
     "to the rail, ending low at the boat in the water, " + HOLD,
     "喊话 + 海浪 + 缆绳绷紧"),
    ("S25", "慢动作特写绳断，随后拉远", "镜头25：巨浪中绳子绷到极限『啪』地断开，两船分离",
     "接镜头26：小艇在巨浪间远去",
     "Open sea in a black squall: a small wooden boat and a larger sailing ship strain apart at "
     "opposite edges of frame, a long rope stretched taut between them skimming the wave tops — then "
     "the rope snaps at the middle, the broken end whips back spraying water droplets in slow "
     "motion, and the wind shoulders the big ship away across the waves. Slow-motion close view on "
     "the snapping rope, then pulling back wide to the separating ships, " + HOLD,
     "绳断脆响 + 风暴 + 音乐骤停"),
    ("S26", "航拍缓慢拉升，海面一片黑暗", "镜头26：小艇越来越小，母亲用披肩裹紧女儿，浪吞没画面",
     "接镜头27：黎明金红海平线",
     "High above a dark stormy sea at dusk, looking down: a tiny open wooden boat with a handful of "
     "blurred bundled figures rides between enormous grey waves, a woman's shawl-wrapped silhouette "
     "hunching over a small bundle; a final huge wave rises and slides across the frame, swallowing "
     "the view of the boat entirely as darkness falls. Slow aerial crane rising higher as the small "
     "boat shrinks and the last wave rolls over the frame, " + HOLD,
     "海浪渐弱 + 大提琴单音 + 风声"),

    # ---------------- N08 结尾反转（S27-S28）+ 片尾卡 ----------------
    ("S27", "远景缓慢拉远，海鸥飞过", "镜头27：黎明，幽灵船独自航行在金红色海平线上，油灯微亮",
     "接镜头28：水面的布偶兔子",
     "On the open Atlantic at sunrise, wide and calm: " + SHIP_GHOST + " sails alone along a gold-and-"
     "red glowing horizon, some sails refilled with wind, her deck completely empty, one small oil "
     "lamp still burning faintly at the stern rail; three seagulls cross the warm sky and the sea "
     "lies like hammered copper. Very wide shot slowly pulling back and away from the sailing ship, "
     + HOLD,
     "海鸥 + 海浪渐弱 + 大提琴收尾"),
    ("S28", "水面平视特写，缓慢下沉", "镜头28：布偶兔子漂在水面缓缓旋转，下沉前被朝阳照亮",
     "接片尾卡",
     "At the surface of the open sea at sunrise, camera almost in the water: a worn old cloth bunny "
     "rabbit toy floats on the gentle swell, slowly turning in a small ring of ripples, wet and "
     "heavy; the rising sun breaks over the horizon and lights the toy's face in gold just as it "
     "begins to slip under the surface. Water-level close-up of the floating toy, the camera sinking "
     "slowly with it, " + HOLD,
     "水声 + 最后一秒静音 + 大提琴余音"),
]

CARD_HEADER = "海上未解之谜  /  大西洋 · 一八七二"        # 信息卡左上角小字（本片无信息卡，保留机制）
CARD_FOOTER = "公开资料整理 · 并非原始档案影像"
CARDS = {}   # 用户脚本规定「所有镜头必须是真实运动的动画片段」：本片不用静帧信息卡

# 片头大字卡（0.35–4.7 秒叠在第一镜上）：用户脚本第 1 段「字幕大字」
TITLE_CARD = ["十个人，凭空消失", "1872 · 大西洋 · 玛丽·赛勒斯特号"]
# 片尾卡（177–180 秒）：用户脚本镜头29 —— 黑场金色标题；第一行 = 标题，第二行 = 副题小字，
# 第三行 = 互动提问（用户脚本第 8 段「字幕大字」），第四行 = 资料来源
END_CARD = [
    "玛丽·赛勒斯特号",
    "海上最大的未解之谜",
    "你觉得是什么？评论区告诉我",
    "资料：维基百科 / 大英百科 / 史密森尼 · 原创解说 · AI动画情景重现",
]
# 分段大字字幕（用户脚本各段「字幕大字」；N01 由片头卡承担、N08 由片尾卡承担）
CHAPTER_BANNERS = {
    "N02": "1872年11月7日 · 纽约 → 热那亚",
    "N03": "12月4日 · 亚速尔群岛附近",
    "N04": "食物够吃半年 · 财物都在 · 人不见了",
    "N05": "猜想一：海盗？× 叛变？×",
    "N06": "猜想二：海怪？龙卷风？地震？",
    "N07": "最合理的猜想：酒精蒸汽爆燃",
}
# 画面内大标记（用户脚本镜头17/18 的红色大叉；后期叠加，不交给视频模型拼符号）
BIG_MARKS = [
    {"shot": "S17", "text": "×", "at": 1.4, "dur": 2.6, "style": "xred"},
    {"shot": "S18B", "text": "×", "at": 1.6, "dur": 2.4, "style": "xred"},
]
# 字幕里描金放大的关键词（人名、数字、结论词）
CAPTION_KEYWORDS = [
    "一八七二年", "十个人", "全都消失", "十一月七日", "纽约", "热那亚", "布里格斯", "两岁",
    "七名船员", "一千七百多桶", "工业酒精", "一个月后", "十二月四日", "亚速尔群岛",
    "上帝的恩典号", "一个人都没有", "完好", "半年", "救生艇", "航海仪器", "十天前",
    "打斗痕迹", "求救信号", "海盗", "叛变", "威望", "巨型乌贼", "龙卷风", "地震",
    "酒精蒸汽", "爆燃", "长绳", "绳子断了", "再也没人见到", "没有人能证明",
    "摩尔豪斯", "黑旗", "触手", "红外套", "布偶兔子", "抽水泵", "说不通",
]
# 逐镜标签覆盖：默认「AI动画情景重现 · 非新闻影像」；猜想/科学示意/日志特写写得更具体
LABEL_OVERRIDES = {
    "S01": "AI动画情景重现 · 非新闻影像",
    "S02": "AI动画情景重现 · 非新闻影像",
    "S03": "AI动画情景重现 · 非实景影像",
    "S04": "AI动画情景重现 · 虚构角色 · 非本人容貌",
    "S05A": "AI动画情景重现 · 非档案影像",
    "S05B": "AI动画情景重现 · 非实景影像",
    "S06": "AI动画情景重现 · 望远镜视角示意",
    "S07A": "AI动画情景重现 · 虚构角色 · 非本人容貌",
    "S07B": "AI动画情景重现 · 非现场影像",
    "S08": "AI动画情景重现 · 非现场影像",
    "S09": "AI动画情景重现 · 非新闻影像",
    "S10": "AI动画情景重现 · 非案发房间影像",
    "S11": "AI动画情景重现 · 非案发房间影像",
    "S12": "AI动画情景重现 · 非遗物影像",
    "S13": "AI动画情景重现 · 非证物影像",
    "S14": "AI动画情景重现 · 非现场影像",
    "S15": "AI动画情景重现 · 日志最后一页 1872年11月25日",
    "S16": "AI动画猜想示意 · 非史实影像",
    "S17": "AI动画猜想示意 · 非史实影像",
    "S18A": "AI动画猜想示意 · 非史实影像",
    "S18B": "AI动画猜想示意 · 非史实影像",
    "S19": "AI动画猜想示意 · 非史实影像",
    "S20": "AI动画猜想示意 · 非史实影像",
    "S21": "AI动画情景重现 · 非新闻影像",
    "S22": "AI动画科学示意 · 非史实影像",
    "S23": "AI动画科学示意 · 非史实影像",
    "S24": "AI动画情景重现 · 虚构角色 · 非本人容貌",
    "S25": "AI动画情景重现 · 非现场影像",
    "S26": "AI动画情景重现 · 非现场影像",
    "S27": "AI动画情景重现 · 非新闻影像",
    "S28": "AI动画情景重现 · 非新闻影像",
}
# 合成音效事件：(镜头号, 类型)，落在该镜开始前 0.18 秒
# 可用：paper / machine / press / phone / keys / bell / wave / creak / wind / boom / snap / ding / gull
SFX_EVENTS = [
    ("S01", "bell"), ("S02", "creak"), ("S03", "gull"), ("S05B", "creak"), ("S06", "wind"),
    ("S08", "wave"), ("S09", "bell"), ("S10", "ding"), ("S11", "ding"), ("S12", "ding"),
    ("S13", "ding"), ("S14", "ding"), ("S15", "ding"), ("S16", "wind"), ("S17", "boom"),
    ("S23", "boom"), ("S25", "snap"), ("S27", "gull"), ("S28", "wave"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "它漂了一个月，船上却一个人都没有",
    "十个人凭空消失：玛丽·赛勒斯特号，海上最大的未解之谜",
    "货物原封不动、救生艇不见了：1872年那艘幽灵船到底经历了什么？",
]
HOOK = ("一八七二年，大西洋上漂着一艘船。船上的东西几乎原封不动——食物够吃半年，行李都还在——"
        "可是十个人，全都消失了。一个月后它被另一艘船发现，帆破破烂烂，救生艇不见了，"
        "航海日志停在十天前。这就是海上最大的未解之谜：玛丽·赛勒斯特号。")
GOLDEN_LINES = [
    "它漂了一个月，船上却一个人都没有。",
    "船上的一切几乎原封不动，消失的只有人。",
    "最合理的解释，从来都不等于真相——因为没有人能证明。",
]
DESCRIPTION = (
    "一八七二年十一月七日，玛丽·赛勒斯特号从纽约启航前往意大利热那亚，船上是布里格斯船长、"
    "他的妻子、两岁的女儿和七名船员，还有一千七百多桶工业酒精。十二月四日，它在亚速尔群岛附近"
    "被「上帝的恩典号」发现：船体几乎完好，食物和淡水够吃半年，可是一个人都没有——救生艇不见了，"
    "日志停在十天前。海盗、叛变、海怪、天灾、酒精蒸汽爆燃……哪个才是真相？"
    "本片画面为AI生成的3D动画情景重现（非新闻影像），事实依据公开资料整理。"
)
QUESTION = "你觉得，他们到底遇到了什么？评论区告诉我。"
HASHTAGS = ["#幽灵船", "#玛丽赛勒斯特号", "#未解之谜", "#海洋之谜", "#3D动画"]
COVER_NOTE = ("封面：幽灵船在浓雾中偏画面右侧，左侧留白放大字「十个人，凭空消失」，金色加黑边。")

GRID = None           # 本片按用户脚本的逐镜时长规划（不用等距网格）
END_CARD_SECONDS = 3.0    # 片尾卡 177–180 秒
SEED_BASE = 18721204      # 发现日（一八七二年十二月四日），让 seed 可追溯

# 露脸镜头登记（镜头号 -> 角色 id）：只有这里登记的镜头允许出现面容 token。
FACE_SHOTS = {
    "S04": ["C1", "C2", "C3"],
    "S07A": ["C4"],
    "S24": ["C1", "C2", "C3"],
}
REFERENCE_SHOTS = {}   # 本片不走定妆照图生视频（智谱免费档 flash 实测拒收 image_url，见北九州收据）
FIRST_FRAME = {}       # 跨镜脸一致性靠面容 token + seed，最终由 face_cast 画面闸门和人眼复核


def first_frame_urls():
    base = ("https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/"
            "arena/63ceeca2-desktop-tutorial/production/maryceleste1872/")
    return {sid: base + rel for sid, rel in FIRST_FRAME.items()}


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
        "chapter_banners": CHAPTER_BANNERS, "big_marks": BIG_MARKS,
        "caption_keywords": CAPTION_KEYWORDS, "label_overrides": LABEL_OVERRIDES,
        "sfx_events": [list(e) for e in SFX_EVENTS],
    }


def build():
    assert abs(sum(b - a for a, b in CHAPTER_WINDOWS.values()) + END_CARD_SECONDS - 180) < 1e-6, \
        "章窗口 + 片尾卡 ≠ 180 秒"
    assert len({sid for sid, *_ in SHOTS}) == len(SHOTS), "镜头号重复"
    face = faces()
    for cid in {cid for ids in FACE_SHOTS.values() for cid in ids}:
        assert face.get(cid), f"cast.json 里没有角色 {cid} 的面容 token"
    extra_frames = first_frame_urls()
    missing_frames = [sid for sid in FIRST_FRAME if not (HERE / FIRST_FRAME[sid]).is_file()]
    assert not missing_frames, f"这些自定义首帧图不存在：{missing_frames}"

    # 规划时间轴：逐镜落在本章窗口内（用户脚本时长；镜头5/7/18 的内部硬切拆成 A/B 两镜）
    plan_slots = {
        "N01": [("S01", 5.0), ("S02", 5.0)],
        "N02": [("S03", 6.0), ("S04", 6.0), ("S05A", 4.0), ("S05B", 4.0)],
        "N03": [("S06", 6.0), ("S07A", 3.5), ("S07B", 3.5), ("S08", 6.0), ("S09", 6.0)],
        "N04": [("S10", 6.0), ("S11", 6.0), ("S12", 6.0), ("S13", 7.0), ("S14", 6.0), ("S15", 4.0)],
        "N05": [("S16", 7.0), ("S17", 6.0), ("S18A", 3.5), ("S18B", 3.5)],
        "N06": [("S19", 8.0), ("S20", 9.0), ("S21", 8.0)],
        "N07": [("S22", 6.0), ("S23", 6.0), ("S24", 7.0), ("S25", 5.5), ("S26", 4.5)],
        "N08": [("S27", 6.5), ("S28", 6.5)],
    }
    by_id = {sid: (camera, purpose, transition, body, sfx) for sid, camera, purpose, transition, body, sfx in SHOTS}
    expected = [sid for cid in sorted(plan_slots) for sid, _ in plan_slots[cid]]
    assert expected == [s[0] for s in SHOTS], "plan_slots 与 SHOTS 顺序不一致"

    shots = []
    i = 0
    for cid, _title, _text in CHAPTERS:
        w_start, w_end = CHAPTER_WINDOWS[cid]
        assert abs(sum(d for _, d in plan_slots[cid]) - (w_end - w_start)) < 1e-6, f"{cid} 逐镜时长与窗口不符"
        cursor = w_start
        for sid, dur in plan_slots[cid]:
            camera, purpose, transition, body, sfx = by_id[sid]
            prompt = body
            for fid, token in face.items():
                prompt = prompt.replace("{" + fid + "}", token)
            assert "{" not in prompt and "}" not in prompt, f"{sid} 提示词里还有没替换的占位符"
            shot = {
                "id": sid, "kind": "agnes", "start": cursor, "duration": dur,
                "narration_id": cid, "prompt": prompt,
                "purpose": purpose, "transition_out": transition,
                "graphic": "", "seed": SEED_BASE + i + 1,
                "seconds": 6, "aspect": "16:9", "resolution": "1080p", "frame_rate": 24,
                "camera": camera, "sfx_note": sfx,
            }
            if sid in FACE_SHOTS:
                shot["cast"] = FACE_SHOTS[sid]
            if sid in REFERENCE_SHOTS:
                shot["reference_image"] = portrait_urls()[REFERENCE_SHOTS[sid]]
            if sid in extra_frames:
                shot["reference_image"] = extra_frames[sid]
            shots.append(shot)
            cursor += dur
            i += 1

    story = {
        "title": TITLE, "film_name": FILM_NAME,
        "target_duration": 180, "width": 1920, "height": 1080, "fps": 30,
        "model": "cogvideox-flash", "branch": "arena/63ceeca2-desktop-tutorial",
        "style_prefix": STYLE_PREFIX, "negative_prompt": NEGATIVE_PROMPT,
        "principles": PRINCIPLES, "sources": SOURCES,
        "chapter_windows": {cid: list(w) for cid, w in CHAPTER_WINDOWS.items()},
        "end_card_seconds": END_CARD_SECONDS,
        "chapters": [
            {"id": cid, "title": title, "start": CHAPTER_WINDOWS[cid][0],
             "duration": CHAPTER_WINDOWS[cid][1] - CHAPTER_WINDOWS[cid][0], "text": text}
            for cid, title, text in CHAPTERS
        ],
        "shots": shots,
        "presentation": presentation(),
    }
    story["_scaffold"] = {"note": (
        "内容由 build_story.py 一次性写入；29 镜用户脚本 = 31 个 CogVideoX 动态镜头（镜头5/7/18 内部硬切拆分）"
        "+ 片尾标题卡 3 秒；每镜只用一次；露脸模式：面容 token 只在 cast.json 写一份，"
        "build_story.py 用占位符注入；视频模型走智谱 CogVideoX-Flash 免费档（generate_cogvideox.py）；"
        "解说词与 screenplay.md、audio/manifest.json 三处逐字一致由 generate.py --validate 守着。")}
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {
        "voice_id": "", "language": "zh-CN", "selection": "", "clips": []}
    clips = {c["id"]: c for c in manifest.get("clips", [])}
    new_clips = []
    for cid, title, text in CHAPTERS:
        row = clips.get(cid, {})
        row.update({"id": cid, "file": cid + ".mp3", "text": text})
        row.setdefault("sha256", "")
        row.setdefault("voice_id", manifest.get("voice_id", ""))
        new_clips.append(row)
    manifest["clips"] = new_clips
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    kinds = [s["kind"] for s in shots]
    chars = sum(len(c["text"]) for c in story["chapters"])
    print(f"story.json 已写入：{len(shots)} 镜 = {kinds.count('agnes')} cogvideo 动态镜 + 片尾卡，"
          f"解说 {chars} 字（含标点）")
    print("逐章字数：" + " / ".join(f"{c['id']} {len(c['text'])}" for c in story["chapters"]))
    print(f"露脸镜头：{len(FACE_SHOTS)} 镜（S04/S07A/S24）；首帧图钉脸：{len(FIRST_FRAME)} 镜")
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

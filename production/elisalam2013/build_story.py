#!/usr/bin/env python3
"""《蓝可儿案：她把电梯所有按钮都按亮了》—— 唯一内容源：解说词、30 镜分镜、参考图、钩子/注释、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
流水线出处是 production/shanghai_freezer_case/build_story.py —— 一部出片、换声、重渲都跑完的成片）。

用法::

    python3 production/elisalam2013/build_story.py            # 写 story.json + screenplay.md + 抖音脚本.md + 抖音发布文案.md

写法规则（都是前作踩出来的，别省）：

- 30 镜 × 6 秒规划网格，时间轴由本文件的 ROWS 顺序自动累加，合计必须正好 180 秒（结尾校验会卡）；
  时长只能是 2–13 秒的整数。每镜一句解说，TTS 一镜一条，字幕与音频逐字一致。
- 解说要有电影感：前 3 秒 = 反常事实 + 强视觉画面（禁静态 UI/波形/纯文字开场、禁绕弯设问）；
  中段每 20–30 秒一个信息钩子；结尾 8 秒 = 金句 → 互动提问 → 落版；记忆锚点数字 ≥ 5 次强调；
  单句 ≤ 屏显一行（≤16 字），关键词加粗放大。详见 `新题目开工手册.md` §3.1 / §10。
- 数字一律写成中文读法（"二零一六年十月十七日""年仅三十二岁"），TTS 和字幕才一致。
- 不写血腥/侵害过程的具体描写（TTS 审核会拒，红线也不允许）。
- STYLE 在每个提示词最前、NEGATIVE 在最后，generate.py 自动拼接；角色锚点原文插入对应镜头。
  提示词钉死"唯一场景"（去 AI 味：纪实感场景/背影侧脸/无唯美空镜），否定词对视频模型基本没用，
  想去掉某样东西就别给它出现的空间。画面按纪实感写法补手法：强明暗对比/浅景深/升格/暖冷对立。
- 参考图：每镜 __ 张（Agnes 2.5 Flash reference 模式 1–5 张），按 reference/approvals.json 登记；
  没有批准参考图，--validate 直接报错（这是设计：先开造型/场景参考，再烧视频额度）。
- 钩子 H1..Hn：白字黑边、居中偏下（MarginV=275）、每条严格 2 秒；金色注释 MarginV=200，只补可核实事实。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "蓝可儿案：她把电梯所有按钮都按亮了"
BRANCH = "arena/f9f847e0-desktop-tutorial"
FILM_NAME = "蓝可儿案_她把电梯所有按钮都按亮了_三分钟_带声音.mp4"

# 全片统一的画面风格前缀（第 1 位拼接）。
# 注意：style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 30 镜全部重做。
STYLE = (
    "【STYLE】电影级写实3D动画情景重现，明确标注为非真实历史影像；35mm胶片摄影质感，浅景深，长焦压缩，"
    "冷峻悬疑犯罪片的克制、冷静、低照度氛围；2013年洛杉矶市中心西塞尔酒店——1920年代装饰艺术风格立面、"
    "昏暗长廊、复古客房与大堂家具、屋顶金属水箱；蓝黄混光，霓虹与白炽交错，暖黄仅属于回忆段（镜头7至8），"
    "此后全程冷青、冷灰主导；16:9横屏宽银幕，主体三分线附近，画面底部六分之一留作字幕安全区；"
    "所有镜头必须是真实连续运动的3D影像，镜头本身平稳移动，绝不以静态图加推拉冒充；"
    "所有人物均为虚构演员式形象，不还原任何真实人物肖像；全程无任何可读文字、伪招牌或屏幕上的字。"
)
NEGATIVE = (
    "【NEGATIVE】卡通，Q版，动漫，夸张表情，过度饱和，文字，水印，字幕，可读文字，真实姓名，真实肖像，"
    "血腥，伤口，遗体，尸体，水中人形，绑缚，窒息过程，性相关内容，暴力过程，武器，畸形手指，多余肢体，"
    "人物面部崩坏，低清晰度，画面闪烁，风格突变，竖屏构图，黑边，静态图加推拉，幻灯片，拼版，伪招牌，鬼怪，闹鬼符号。"
)

# 角色锚点：generate.py 会把锚点原文拼到对应镜头的提示词中。
# 每镜只给虚构演员式形象；蓝可儿本人绝不出现可识别面容。
CHARACTERS: dict[str, str] = {
    "ELISA": "【C01锚点】约二十一岁华裔女性，及肩黑色直发，鹅蛋脸，身材纤细，休闲旅行装束（深色风衣、牛仔裤），神情敏感疲惫，普通长相，自然皮肤纹理，虚构演员式形象",
    "ELISA_SIDE": "【C02锚点】同一人侧影，黑色及肩直发，深色风衣，面部大部分隐于暗处，轮廓模糊，神情紧绷，虚构演员式形象",
    "ELISA_FRONT": "【C03锚点】同一人正面半身，及肩黑色直发自然垂落，深色风衣，面对镜头，神情拘谨疲惫，普通长相，自然皮肤纹理，虚构演员式形象",
    "ELISA_THREEQUARTER": "【C04锚点】同一人三分之四侧面，黑色及肩直发，深色风衣立领，看向窗外，神情放空疲惫，虚构演员式形象",
    "ELISA_HANDS": "【C05锚点】同一人双手近景，纤细手指，深色风衣袖口，指尖按下电梯按钮，虚构演员式形象，无可识别面容",
    "MAINT_BACK": "【C06锚点】四十岁左右男性维修工背影，工装夹克，屋顶清晨逆光，面部完全不可见，普通背影",
}

CHARACTER_SEEDS: dict[str, int] = {
    "ELISA": 20130131,
    "ELISA_SIDE": 20130131,
    "ELISA_FRONT": 20130131,
    "ELISA_THREEQUARTER": 20130131,
    "ELISA_HANDS": 20130131,
    "MAINT_BACK": 20130201,
}

# 角色代号 → 已批准参考图资产编号（与 reference/approvals.json 的键一致）。
CHARACTER_REFERENCE_IDS: dict[str, str] = {
    "ELISA": "C01",
    "ELISA_SIDE": "C02",
    "ELISA_FRONT": "C03",
    "ELISA_THREEQUARTER": "C04",
    "ELISA_HANDS": "C05",
    "MAINT_BACK": "C06",
}

# duration, narration, visual beat, design references, character roles, camera, sound, color
# refs 对应 reference/approvals.json 里 approved 的条目；roles 必须登记在 CHARACTERS。
ROWS = [
    # ---------------- N01 · 电梯里的按钮（S01–S05）----------------
    (6, "二零一三年一月三十一日凌晨，电梯按钮全亮了。",
     "电梯轿厢内景，金属面板与整排发光按钮特写，一只手依次按下每一个楼层键，按钮逐一亮起，冷白荧光灯微微闪烁，镜头近景极缓推进，画面轻微噪点",
     "P03", [], "近景缓推", "电流嗡声+按钮清脆声", "冷青"),
    (6, "西塞尔酒店的电梯，停了一下——又停了一下。",
     "电梯按钮板特写转轿厢内景，轿厢空无一人，镜面反射出走廊一线冷光，地面轻微震动，镜头固定后极慢后拉",
     "S02", [], "固定+极慢后拉", "电梯蜂鸣+钢索摩擦", "冷青"),
    (6, "她躲在门后，一遍遍向走廊里张望。",
     "电梯内景，一个年轻女人背影/侧影蜷在门边，半身被门缝遮住，她一次次伸头向门外走廊探视，走廊尽头一线暖光，镜头长焦定格剪影",
     "C02+S02", ["ELISA_SIDE"], "长焦剪影固定", "门开合的反复声+远处钢琴声", "冷蓝压暖"),
    (6, "像是在躲什么——又好像觉得自己正在被追。",
     "电梯门反复开合，她忽而贴近门框凝视走廊，忽而缩回暗处，动作紧张而毫无节奏，镜头手持微微晃动，景深虚实强烈",
     "C02+S02", ["ELISA_SIDE"], "手持微晃", "呼吸+门导轨异响", "冷暗"),
    (6, "这是洛杉矶市中心的西塞尔酒店——“死亡之屋”。",
     "洛杉矶市中心雨夜航拍缓慢下降，1920年代装饰艺术风格的旅馆立面，锈色墙面与湿润人行道，街角霓虹倒影在积水里，画面冷峻而古老，无可读招牌文字",
     "S01", [], "航拍缓降", "雨声+远处警笛", "冷青青橙"),

    # ---------------- N02 · 她是谁（S06–S10）----------------
    (6, "蓝可儿，华裔加拿大人，在温哥华上大学。",
     "复古大堂晨光里，一个年轻女人拖着旅行箱走进门内，背影轮廓清晰，大厅挑高空间、碎金般的尘光，镜头远景缓慢平移跟拍",
     "C01+S04", ["ELISA"], "远景平移跟拍", "行李轮声+大堂脚步回声", "暖黄渐冷"),
    (6, "那年一月，她跟朋友们一起来到洛杉矶。",
     "大堂角落，她低头看手机露出浅浅的笑，手机屏幕光映在脸颊上半边，朋友们的背影推开玻璃门离开，色调偏暖，镜头缓缓推向她的侧脸",
     "C01+S04", ["ELISA"], "缓推侧脸", "大堂人群低语+玻璃门风铃", "暖黄"),
    (6, "朋友先离开后，她说再玩几天，一个人留在旅馆。",
     "她独自站在大堂空旷处，行李箱停在脚边，身后门外阳光，她转身望向复古前台，画面突然抽走暖色，镜头固定沉默数秒",
     "C01+S05", ["ELISA"], "固定沉默", "大堂空镜回声", "暖冷交界"),
    (6, "后来，再也没有人见过她。",
     "昏暗长廊尽头，客房门整齐列开，镜头沿走廊缓慢推进，门缝下一线黑暗，全程无人，光线一盏盏变暗，像被什么抽走",
     "S03", [], "沿廊缓推", "深夜空调低鸣+远处关门声", "冷灰"),
    (6, "她最后一次出现在监控里，是一月三十一日凌晨。",
     "电梯内景门即将合上的瞬间，镜头从轿厢内向外拍，门缝收窄，最后她的轮廓从外面掠过，什么也抓不住，画面瞬间黑",
     "S02", [], "内向外视角", "电梯关门的" + "咚", "冷黑"),

    # ---------------- N03 · 电梯录像（S11–S15）----------------
    (6, "警方向媒体公布了这段电梯录像。",
     "新闻演播室与报纸版面的抽象光斑、倒影、噪点，屏幕上闪烁着无法辨认的播报画面，镜头在虚焦的电梯钢门影像上反复切换，无可读文字",
     "P04", [], "快切光斑蒙太奇", "新闻播报隐约音+底噪", "冷灰"),
    (6, "短短录像里，她按亮了每一层，往走廊望了又望。",
     "监控风格的昏黄半影画面：她在轿厢里贴近门框凝视走廊，走廊空无一人，她按下按钮、又贴回去，门缝冷光反复闪烁，镜头颗粒感强烈",
     "C02+S02", ["ELISA_SIDE"], "监控视角固定", "电子底噪+呼吸", "监控黄"),
    (6, "警方把她当失踪人口立案排查。",
     "酒店大堂空无一人，前台椅子斜放，一名警官背影站在复古电话前拿起话筒，镜头从背后推近，窗外霓虹冷光扫过肩膀",
     "S04", [], "背后推近", "老式电话拨号声+空调声", "冷蓝"),
    (6, "她的房间里，护照、手机、现金全都在。",
     "2147号客房（无可读号牌），床铺凌乱却完整，桌上摊着护照、手机、钱包和未收拾的衣物，没有打斗痕迹，镜头缓缓环视，冷白台灯",
     "P02+S05", [], "环视缓移", "冰箱嗡鸣+树叶拂窗", "冷白"),
    (6, "十九天里没人再见过她——直到有人报修水压。",
     "白天走廊，阳光从天窗斜下，酒店维修工推着梯子穿过长廊，走廊深处一名住客在打电话投诉，镜头缓推过他们之间的距离",
     "S03", [], "缓推过空间", "对讲机杂音+水管敲击", "冷亮"),

    # ---------------- N04 · 水箱（S16–S20）----------------
    (6, "二月十九日，酒店维修工接到投诉：没了水压。",
     "屋顶平台，清晨天光，四个巨大的圆柱形金属水箱矗立在平台中央，维修工抬头看其中一个，塔体锈迹斑斑，镜头低角度仰拍，云层快速掠过",
     "S06", [], "低角度仰拍", "风声+金属风箱嗡鸣", "冷亮"),
    (6, "他们爬上屋顶，打开水箱盖——然后就没了声音。",
     "屋顶水箱近景，维修工伸手掀开箱盖，盖子缓缓抬起，缝隙溢出冷白光与水汽，光扫过他的后背，他的动作突然停住，镜头定住不动",
     "S06", [], "定格不动", "金属盖摩擦+水汽+突然的静默", "冷白"),
    (6, "她在里面——十九天，泡在冰冷的水里。",
     "水箱缝隙中的冷白光与蒸汽特写，水面纹波、金属边缘、天空方向，不出现任何人形；镜头只给光、水与金属",
     "S06", [], "光与水纹特写", "水滴声+远处警笛逼近", "冷白"),
    (6, "警方封锁屋顶，全球媒体涌了过来。",
     "酒店外景夜，警车红蓝灯在湿润立面上一闪一闪，话筒竹竿伸进镜头前，伞群在人行道上晃动，镜头从地面仰拍人群与高楼",
     "S01+S07", [], "地面仰拍人群", "记者嘈杂+警报", "冷青红"),
    (6, "尸检：溺水。没有挣扎，没有暴力，没有嫌疑人。",
     "报纸头版与电视屏幕的抽象光斑、翻页、扫描线，警官剪影在案卷前低头沉默，画面不出现尸体与水箱内部",
     "P04", [], "光斑翻页蒙太奇", "纸张翻动+复印机", "冷灰"),

    # ---------------- N05 · 风声（S21–S25）----------------
    (6, "所有人盯上了那段录像——躲的是人，还是幻觉。",
     "电视屏幕里的电梯录像被无限循环播放，光斑忽明忽暗，观众剪影们一排排坐在电视机前，镜头在人群剪影与屏幕光之间切换",
     "P04+S02", [], "屏幕/人群交替切换", "电视静音+空调声", "冷蓝"),
    (6, "网上疯传：西塞尔有鬼，电梯会自己开。",
     "抽象的手机屏幕光斑、键盘敲击特写、阴影里的电梯缝隙，" + "，无可读文字，无鬼怪形象",
     "P04", [], "手机光斑特写", "键盘声+社交App提示音", "冷暗"),
    (6, "警方面对的现实只有一句：除了录像，什么都没有。",
     "警探背影站在屋顶水箱前，警徽与警徽光斑模糊，风很大，水箱金属表面映出天空与城市天际线，镜头慢慢拉远",
     "S06", [], "慢慢拉远", "风声+对讲机", "冷亮"),
    (6, "她患有双相情感障碍，官方结论是溺水。",
     "客房桌面特写，虚化的白色药瓶与小药板，旁边一本摊开的旅行手帐，镜头缓旋过桌面，浅景深，冷白台灯下阴影拉长",
     "P01+S05", [], "缓旋过桌面", "翻书声+空调声", "冷白"),
    (6, "停药还是没停药，没有人能说清楚。",
     "她独自坐在床沿，背对镜头，风从窗外灌进来吹动窗帘，暖黄台灯与冷蓝窗外光在她身上交界，镜头定住，不推进",
     "C01+S05", ["ELISA"], "固定沉默", "窗帘拍打+远处火车", "暖冷交界"),

    # ---------------- N06 · 回响（S26–S30）----------------
    (6, "西塞尔后来歇了业，改作平价住房，电梯仍在运行。",
     "西塞尔立面纪实感空镜，数年前后无区别：霓虹招牌已暗，门口停着搬家货车，一名住客抱着盒子走进大门，镜头固定，无对白",
     "S01", [], "固定空镜", "街道车流+门铃声", "冷灰"),
    (6, "不久，一部纪录片把西塞尔再次推回聚光灯下。",
     "纪录片摄影机在走廊与屋顶的镜头光斑，摩天楼夜景车流，城市象一张摊开的地图，镜头无人物特写，纯环境推进",
     "S01+S07", [], "环境推进", "城市底噪+摄影机运转", "冷暗"),
    (6, "而她的家人只想要一个答案。",
     "客厅剪影，长辈的背影坐在沙发里，窗外雨落在玻璃上，镜头从背后缓慢上移，不拍脸，只拍肩背与窗外冷光",
     "S05", [], "背后缓上移", "雨声+墙钟滴答", "冷蓝"),
    (6, "她本该早点回家——她没有回来。",
     "机场/车站候检厅空镜，行李传送带无人认领，灯光一格一格灭掉，镜头沿传送带缓缓拉远，画面只剩空和光",
     "S07", [], "缓拉远", "广播静电+轮带嗡鸣", "冷蓝"),
    (6, "她不是死在一栋凶宅里——只是独自病倒在那里。",
     "纯黑空间中央，一条冷白光带渐渐亮起又慢慢收束，空气中只有微尘，结尾标题留给后期；全程无文字，无人形",
     "S02", [], "纯黑光带", "低频嗡声渐止", "纯黑"),
]

# 章节边界（start 秒, end 秒, 章名）
CHAPTER_BOUNDS = [
    (0, 30, "按亮的按钮"),
    (30, 60, "她是谁"),
    (60, 90, "电梯录像"),
    (90, 120, "水箱"),
    (120, 150, "风声"),
    (150, 180, "回响"),
]

SEED_OVERRIDES: dict[int, int] = {
    # 如某镜种子出图不理想，在此登记重抽样
}

# 钩子大字（白字黑边、居中偏下 MarginV=275、每条严格 2 秒）
HOOKS = [
    {"id": "H1", "start": 0.0, "end": 2.0, "text": "她按亮了所有按钮", "style": "big_white_black_outline"},
    {"id": "H2", "start": 24.5, "end": 26.5, "text": "死亡之屋", "style": "big_white_black_outline"},
    {"id": "H3", "start": 60.5, "end": 62.5, "text": "录像传遍全球", "style": "big_white_black_outline"},
    {"id": "H4", "start": 84.5, "end": 86.5, "text": "十九天后有人发现了她", "style": "big_white_black_outline"},
    {"id": "H5", "start": 114.4, "end": 116.4, "text": "尸检：溺水", "style": "big_white_black_outline"},
    {"id": "H6", "start": 132.4, "end": 134.4, "text": "除了录像，什么都没有", "style": "big_white_black_outline"},
    {"id": "H7", "start": 168.4, "end": 170.4, "text": "她本该早点回家", "style": "big_white_black_outline"},
    {"id": "H8", "start": 138.4, "end": 140.4, "text": "调查没有结论", "style": "big_white_black_outline"},
    {"id": "H9", "start": 154.4, "end": 156.4, "text": "酒店仍在营业", "style": "big_white_black_outline"},
]

# 金色注释（MarginV=200，只补可核实事实）
EXPLAINERS = [
    {"start": 0.8, "end": 4.6, "text": "二零一三年一月三十一日 · 凌晨", "color": "gold"},
    {"start": 24.8, "end": 28.8, "text": "洛杉矶市中心 · 西塞尔酒店", "color": "gold"},
    {"start": 54.4, "end": 58.2, "text": "坦最后影像 · 一月三十一日凌晨", "color": "gold"},
    {"start": 90.6, "end": 94.2, "text": "二月十九日 · 失踪第十九天", "color": "gold"},
    {"start": 114.8, "end": 118.4, "text": "官方结论：溺水", "color": "gold"},
    {"start": 132.6, "end": 136.2, "text": "无他杀指控 · 无嫌疑人", "color": "gold"},
    {"start": 144.6, "end": 148.2, "text": "官方结论：与双相情感障碍相关", "color": "gold"},
    {"start": 156.6, "end": 160.2, "text": "西塞尔今日 · 电梯仍在运行", "color": "gold"},
]

HIGHLIGHT_PHRASES = [
    "按钮全亮", "十九天", "死亡之屋", "电梯录像", "溺水", "双相情感障碍", "西塞尔",
]

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> dict:
    cursor = 0.0
    shots = []
    for index, row in enumerate(ROWS, 1):
        duration, narration, visual, refs, roles, camera, sound, grade = row
        sid = f"S{index:02d}"
        start = cursor
        cursor += duration
        chapter = next(
            f"N{i:02d}" for i, (lo, hi, _) in enumerate(CHAPTER_BOUNDS, 1)
            if lo <= start < hi
        )
        prompt = (
            f"{visual} 真实连续运动贯穿全镜，镜头运镜：{camera}；构图保持16:9横屏，"
            "主体置于三分线，底部字幕安全区保持低干扰；不要任何文字、标签、时间戳或招牌。"
        )
        shots.append({
            "id": sid, "kind": "agnes", "start": start, "duration": duration,
            "seconds": duration, "aspect": "16:9", "source_size": "720P",
            "narration_id": chapter, "narration": narration,
            "prompt": prompt, "purpose": visual, "characters": roles,
            "seed": SEED_OVERRIDES.get(index, 20260101 + index),
            "camera": camera, "sound_design": sound,
            "color_grade": grade, "reference_ids": refs,
            "transition_in": "按本片色调方案执行的短促电影转场，不改变事实内容",
            "transition_out": "以悬念句与短暂停顿收束，环境保持微动",
        })
    if len(shots) != 30 or abs(cursor - 180) > 1e-6:
        raise AssertionError(f"Expected 30 shots / 180s, got {len(shots)} / {cursor}s")

    chapters = []
    for i, (start, end, name) in enumerate(CHAPTER_BOUNDS, 1):
        text = "".join(s["narration"] for s in shots if start <= s["start"] < end)
        chapters.append({"id": f"N{i:02d}", "title": name, "start": start,
                         "duration": end - start, "text": text})

    approvals_path = HERE / "reference" / "approvals.json"
    approvals = json.loads(approvals_path.read_text(encoding="utf-8")) if approvals_path.exists() else {"assets": {}}
    ref_images = []
    for asset_id, record in approvals.get("assets", {}).items():
        path = HERE / record.get("file", "")
        if record.get("status") == "approved" and path.is_file() and digest(path) == record.get("sha256"):
            ref_images.append({"id": asset_id, **record})
    revision_path = HERE / "reference" / "revision.txt"
    revision = revision_path.read_text(encoding="utf-8").strip() if revision_path.exists() else ""
    voice_path = HERE / "audio" / "voice.json"
    voice = json.loads(voice_path.read_text(encoding="utf-8")) if voice_path.exists() else {}
    voice_id = voice.get("voice_id") or "pending_voice_selection"

    presentation = {
        "onscreen_label": "AI动画情景重现 · 非真实影像",
        "highlight_phrases": HIGHLIGHT_PHRASES,
        "hooks": HOOKS,
        "explainers": EXPLAINERS,
        "end_title": "蓝可儿案",
        "end_subtitle": "2013 · 西塞尔酒店 · 十九天",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "她按亮了所有按钮",
        "cover_concept": "封面只用本片已生成视频截图：镜头01电梯按钮亮起的帧；禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "她按亮了电梯所有按钮，十九天后在西塞尔酒店水箱里被发现｜蓝可儿案",
        "hashtags": ["#蓝可儿案", "#西塞尔酒店", "#真实案件", "#案件解说", "#悬疑"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在最后一镜由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "未联网复核（离线编制，2026-11-21）。所有 B 级条目发布前必须由主创依据权威来源逐条确认，见 FACT_CHECK.md",
        "as_of": "2026-11-21（编制日期；未联网）",
        "legal_note": "本案无他杀指控、无嫌疑人；官方结论：溺水，与双相情感障碍相关。禁止一切超自然定性与在世者嫌疑指向。",
        "sources": [
            {"publisher": "LAPD 失踪人通报及随后新闻发布会", "date": "2013-02（未联网复核）", "url": "TODO 主创补充原始链接", "supports": "电梯录像公布、失踪人口调查"},
            {"publisher": "LA County Department of Coroner 报告", "date": "2013（未联网复核）", "url": "TODO 主创补充原始链接", "supports": "死因：溺水，与精神健康状况相关"},
            {"publisher": "美联社/路透社/LA Times 同期报道", "date": "2013-02-19 至 2013-03（未联网复核）", "url": "TODO 主创补充原始链接", "supports": "水箱发现尸体、事件经过、时间线"},
        ],
        "editorial_cautions": [
            "电梯录像时长与精确钟点口径不一（媒体从十几秒到一分钟不等），片中只说“凌晨”、不报时长",
            "死因用词：统一说“官方结论：溺水，与双相情感障碍相关”；不写 undetermined/accidental 分类名",
            "受害者仅用“蓝可儿”称谓；AI 形象仅示意、不还原真实肖像；不出现真实照片",
            "水箱、尸检、死亡场景一律不具象化再现（光、水汽、金属、空镜）",
            "坊间传言（鬼怪/超自然）只以“网上疯传”归属呈现，不作事实；禁止指向任何在世者",
            "“十九天”为全片唯一精确天数；日期只保留 1月31日凌晨、2月19日两个锚点",
        ],
    }

    project = {
        "title": TITLE,
        "film_name": FILM_NAME,
        "target_duration": 180, "width": 1920, "height": 1080, "fps": 24,
        "model": "agnes-video-2.5-flash", "source_size": "720P", "branch": BRANCH,
        "style_prefix": STYLE, "negative_prompt": NEGATIVE, "style_rumor_prefix": STYLE,
        "characters": CHARACTERS, "character_seeds": CHARACTER_SEEDS,
        "character_reference_ids": CHARACTER_REFERENCE_IDS,
        "narration_spec": {
            "voice_id": voice_id,
            "description": voice.get("description", "TODO 试音选定后的音色描述"),
            "language": "zh-CN", "target_characters_per_second": 4.2,
            "alignment": "一镜一句，一镜一条TTS与一条字幕；只在确有必要时加速，不慢放",
        },
        "chapters": chapters, "shots": shots,
        "reference_images": ref_images,
        "reference_revision": revision,
        "reference_designs": {
            "characters": ["C01", "C02", "C03", "C04", "C05", "C06"],
            "scenes": ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09"],
            "props": ["P01", "P02", "P03", "P04", "P05", "P06"],
            "note": "主创已定调：参考图要丰富——人物给正/侧/背/四分之三/手部特写，场景含外景/电梯/长廊/大堂/客房/屋顶水箱（日·黎明）/街道/空房门；未登记批准前 --validate 报错（设计如此）。详见 reference/REFERENCE_PACK.md",
        },
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期高质量放大到1080P。",
            "所有Agnes提示词由generate.py自动组合：STYLE在最前，角色锚点逐字插入，NEGATIVE在末尾；文字全部禁止AI自绘，由后期烧录。",
            "镜头每5条抽查一次人物脸和服装漂移；出现漂移则以同一批准参考图只重生成对应镜头。",
            "全片无BGM；旁白与字幕逐句锁定，音效/环境声只做轻量辅助，不盖住解说。",
        ],
    }
    (HERE / "story.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [
        f"# {TITLE}", "",
        "抖音横屏｜1920×1080｜16:9｜24fps｜180秒｜30个Agnes Video 2.5 Flash动画片段｜无BGM。",
        "", "| 镜头 / 时间 | 旁白 | 画面与运镜 | 参考图 | 音效/环境声备注 |", "|---|---|---|---|---|",
    ]
    for shot, row in zip(shots, ROWS):
        _, narration, visual, refs, roles, camera, sound, grade = row
        end = shot["start"] + shot["duration"]
        ts = lambda sec: f"{int(sec) // 60:02d}:{int(sec) % 60:02d}"
        rows.append(f"| {shot['id']} / {ts(shot['start'])}–{ts(end)} | {narration} | {visual}（{camera}；{grade}） | {refs} + {','.join(roles) or '无角色'} | {sound} |")
    screenplay = "\n".join(rows) + "\n"
    (HERE / "screenplay.md").write_text(screenplay, encoding="utf-8")
    (HERE / "抖音脚本.md").write_text(screenplay, encoding="utf-8")

    publish = "\n".join([
        f"# {presentation['publish_title']}", "",
        "## 抖音标题", "", presentation["publish_title"], "",
        "## 简短介绍", "",
        "TODO：两三句话讲清案件与判决口径，末尾注明“AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md”。",
        "", "## 提问读者一句话", "", "TODO：一句把读者拽进评论区的提问。", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

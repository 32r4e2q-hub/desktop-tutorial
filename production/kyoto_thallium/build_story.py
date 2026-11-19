#!/usr/bin/env python3
"""唯一内容源：京都铊中毒案《一顿饭，三天后》30 镜 / 180 秒 / Agnes Video 2.5 Flash reference mode。

事实口径：案件处于审理前阶段，被告被推定无罪；全篇使用“据报道、检方称、辩方主张”等限定，
不定性、不推断动机、不评论被告是否有罪；结尾只讨论毒物管控。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "京都铊中毒案：一顿饭，三天后"
BRANCH = "arena/817c7917-desktop-tutorial"

STYLE = (
    "【STYLE】电影级写实3D动画，35mm胶片质感，浅景深，长焦压缩，日本社会派悬疑电影风格，"
    "京都秋日街巷、立命馆大学校园、住宅区夜晚，暖黄秋光与冷蓝夜色、冷白荧光灯对比，低饱和，暗部厚重，"
    "胶片颗粒，真实的皮肤、服装与建筑材质，克制冷静而压抑的情绪，16:9宽银幕横屏构图；"
    "所有镜头必须是连续运动的电影镜头，镜头平稳移动，人物有自然呼吸、眨眼、手部动作与衣物飘动，"
    "禁止以静态图加推拉冒充视频；所有人物均为非真实肖像的写实演员式形象，不丑化、不暗示结论。"
)
NEGATIVE = (
    "【NEGATIVE】卡通，Q版，动漫，夸张表情，过度饱和，文字，水印，字幕，可读文字，药片，药瓶，粉末，针剂，"
    "血腥，伤口，遗体，尸体，中毒症状，挣扎，暴力过程，裸露，畸形手指，多余肢体，人物面部崩坏，"
    "低清晰度，画面闪烁，风格突变，竖屏构图，黑边，真实姓名，真实肖像，招牌文字，伪标题。"
)

# 角色锚点逐字采用脚本定稿口径；generate.py 会将其原文拼到对应镜头提示词中。
CHARACTERS = {
    "HAMANO": "【C01锚点】21岁日本女大学生,黑色及肩直发,清秀明亮,浅色针织衫长裙,双肩包,笑容温暖朝气",
    "MIYAMOTO": "【C02锚点】37岁日本男子,整洁短发,深色西装衬衫,举止礼貌,神情平静,眼神温和",
    "PARENTS": "【C03锚点】日本中年夫妇,父亲夹克,母亲素色外套,神情不安焦急",
    "AUNT": "【C04锚点】老年女性,仅露出被子轮廓与被面上的手,不出现面部",
    "DOCTOR": "【C05锚点】45岁日本男医生,白大褂,细框眼镜,神情专注冷静",
    "DETECTIVE": "【C06锚点】40多岁日本刑警两人,深色西装外套,神情严肃克制,眼神锐利",
    "EXPERT": "【C07锚点】35岁日本检验员,白大褂,口罩防护眼镜,神情专注",
    "COURT": "【C08锚点】日本检察官深色西装冷静;辩护律师深色西装专注;法官黑色法袍肃穆;六名市民裁判员便服认真",
    "OFFICIAL": "【C09锚点】日本政府官员深色西装神情严肃,面前记者举着话筒摄像机",
}

CHARACTER_SEEDS = {
    "HAMANO": 1101, "MIYAMOTO": 2202, "PARENTS": 3303, "AUNT": 4404, "DOCTOR": 5505,
    "DETECTIVE": 6606, "EXPERT": 7707, "COURT": 8808, "OFFICIAL": 9909,
}

# duration, narration, visual beat, design references (S/P), character roles, camera, sound, grade
ROWS = [
    (5, "一顿饭，三天后，她去世了。",
     "深夜，京都北区一栋公寓楼，三楼一扇窗口亮着暖黄灯光，窗帘缝隙里透出两个杯子的剪影，镜头从街对面缓缓推近，冷蓝夜色里只有这一扇窗亮着，画面静得出奇",
     "S01+P01", [], "长焦，缓慢推近", "夜风，远处一声电车驶过", "冷蓝夜色"),
    (5, "体内检出一种被遗忘的毒：铊。",
     "医院夜晚走廊，冷白灯光，尽头一扇病房门虚掩，窗外天色由黑转灰，监护仪的微光闪了一下，画面克制，不出现任何病人",
     "S06+P03", [], "长走廊，缓慢推近", "监护仪的嘀嗒，走廊空调低鸣", "冷白"),
    (7, "2022年10月，京都。立命馆大学三年级，21岁。",
     "京都立命馆大学校园，秋天，银杏金黄，21岁的日菜子背着双肩包，和同学笑着走过，阳光穿过树叶落在她的脸上，画面明亮温暖",
     "S02", ["HAMANO"], "中景，缓慢跟拍", "树叶沙沙声，学生们的说笑声", "秋日暖黄"),
    (7, "十月的一个晚上，她与宫本一起吃了一顿饭。",
     "京都夜晚的小巷，居酒屋的灯笼与暖黄窗光，石板路被雨润湿，日菜子与一名穿深色西装的男子并肩走过，男子礼貌地为她拉开店门，画面温暖，看似平常",
     "S03", ["HAMANO", "MIYAMOTO"], "中景，侧面跟拍", "雨后水滴声，居酒屋的低声喧闹", "秋日暖黄"),
    (6, "饭后，两人回到她在京都的公寓。",
     "居酒屋内，两人对坐，桌上两只玻璃杯，日菜子笑着说话，男子安静倾听，偶尔点头，暖黄灯光，背景里是其他客人的剪影，画面平静",
     "S04+P01", ["HAMANO", "MIYAMOTO"], "中景，缓慢推近玻璃杯", "杯子轻碰声，居酒屋低语", "秋日暖黄"),
    (5, "那天夜里，她的身体急剧变化。",
     "夜晚，公寓楼下，日菜子与男子一同走进楼道，电梯门缓缓合上，楼道的声控灯亮了又灭，电梯上方的指示光点模糊发亮，没有任何可读数字",
     "S01", ["HAMANO", "MIYAMOTO"], "低机位，缓慢推近", "电梯运行声，声控灯啪的亮起", "夜色转冷蓝"),
    (7, "据报道，10月12日，她的身体突然不适。",
     "公寓内部，夜晚，桌上两只玻璃杯，台灯亮着，窗帘半掩，男子的剪影坐在沙发上，手里拿着手机，神情平静，画面克制，不出现任何其他人物",
     "S05+P01", ["MIYAMOTO"], "固定机位，缓慢推近", "挂钟滴答，窗外风声", "夜晚冷蓝"),
    (7, "据报道，宫本没有叫救护车，而是联系了父母。",
     "一户普通人家，清晨，室内光线冷蓝，母亲拿着手机，神情由平静变为紧张，父亲站在身旁，两人对视，手机屏幕只发出冷蓝色的光，屏幕内没有任何界面或文字，画面中没有任何字幕",
     "P02", ["PARENTS"], "近景，缓慢推近", "电话铃声，压低的对话声", "冷蓝"),
    (6, "三天后，她在医院去世。",
     "医院走廊，父母匆忙赶到，医生拿着病历夹迎上去，低声说着什么，父亲握紧母亲的手，三人的身影在冷白灯光下拉长",
     "S06", ["PARENTS", "DOCTOR"], "中景，缓慢推近", "急促的脚步声，走廊回声", "冷白"),
    (5, "那一刻，病房里只剩下监护仪的声音。",
     "病房窗外，10月15日清晨，窗帘被风吹起一角，监护仪的曲线缓缓拉成一条直线，画面克制，不出现任何病人，只有窗外一缕光慢慢移走",
     "S06", [], "固定机位，缓慢推近", "监护仪长鸣，窗外风声", "冷白"),
    (7, "转折出现在检验报告里：她的体内，检出了铊。",
     "实验室，检验员戴着口罩与护目镜，把一排试管放进仪器，屏幕上一条曲线缓缓上升，一个红色的抽象原子图标突然亮起，检验员停下手，抬头，眼睛睁大",
     "S07+P03", ["EXPERT"], "近景，缓慢推近屏幕", "仪器运行声，嘀的提示音", "冷白"),
    (7, "铊是一种剧毒金属，历史上曾被用于灭鼠。",
     "检验报告被打印出来，红色原子图标被一个红圈圈住，旁边日历翻到2022年10月的一页，日历数字模糊不可读，红圈闪烁，背景是冷白的实验室灯光",
     "P03+P04", [], "大特写，缓慢推近", "打印机的嘶嘶声，日历翻页声", "冷白"),
    (6, "中毒的线索，往往藏在看似平常的病情里。",
     "警察署会议室，刑警们围着桌子，白板上只有抽象线条与地图轮廓，一名刑警拿起检验报告，与同伴对视，神情凝重，画面冷灰",
     "S08", ["DETECTIVE"], "中景，缓慢环绕", "纸张翻动声，日光灯嗡鸣", "冷灰"),
    (5, "警方因此，把案子定为命案。",
     "白板上只有抽象的红色圈线，红线从医院连到公寓，再连到居酒屋，三条线交汇在一个点上，刑警把一支红笔扣在桌上",
     "S08", ["DETECTIVE"], "俯拍，缓慢推近", "红笔划线声，一拍沉默", "冷灰"),
    (6, "2023年3月，警方逮捕了宫本。",
     "2023年3月清晨，一条住宅小巷，一名穿深色西装的男子独自从木门内走出，停在门口，神情平静，缓慢转身，身边无他人，人物之间保持距离，没有任何肢体接触，画面克制",
     "S03", ["MIYAMOTO"], "中景，慢动作", "晨风，脚步声，一声压低的招呼", "冷灰"),
    (6, "2020年7月，他的叔母病倒住院。",
     "2020年7月的医院病房，仅露出被子的轮廓与放在被面上的手，监护仪的光映在被面上，窗外是夏日清晨，画面克制，不出现任何面部",
     "S06", ["AUNT"], "固定机位，缓慢推近", "监护仪嘀嗒，窗外蝉鸣", "冷灰"),
    (6, "起诉书称，叔母病倒后长期昏迷。",
     "检验室，桌上一份检验报告，封面有红章，镜头推近，窗外天色暗淡，没有任何人物的面部",
     "S07+P03", ["EXPERT"], "近景，缓慢推近", "仪器运行声，嘀的提示音", "冷灰"),
    (5, "检方认为，两起事件之间存在关联。",
     "日历翻到2020年7月，一个红圈圈住，旁边是另一页2022年10月，另一个红圈圈住，两个红圈之间，一条细线缓缓连接，日历数字模糊不可读",
     "P04+P05", [], "俯拍，缓慢推近", "日历翻页声，红线绷紧的轻响", "冷灰"),
    (6, "据报道，三个月后，宫本任叔母房地产公司代表。",
     "一间不动产公司办公室，门口的公司名牌换上了新的名牌（抽象，不出现可读文字），穿深色西装的男子站在门前，整理领带，神情平静，画面冷灰",
     "S12", ["MIYAMOTO"], "中景，缓慢推近", "办公室环境声，名牌被挂上的轻响", "冷灰"),
    (6, "2023年6月，他又因叔母一案，被追加起诉。",
     "日历从2020年7月一页页翻到2020年10月，一条细线从医院的病床轮廓延伸到公司的名牌，线的末端微微发光，象征时间的先后，不下任何结论，日历数字模糊不可读",
     "P04", [], "俯拍，延时", "日历翻页声加速，细线绷紧的轻响", "冷灰"),
    (5, "检方的罪名是：杀人未遂。",
     "检察厅办公室，检察官在桌上摊开起诉书与证据目录，抬头望向窗外，窗外是阴天，神情冷静，画面冷灰",
     "S08", ["COURT"], "近景，缓慢推近", "纸张翻动声，钟摆声", "冷灰"),
    (5, "目前为止，这些都只是检方的指控。",
     "2023年6月，一份追加起诉书被盖上红章，红章落下的瞬间，画面一半被阴影吞没",
     "P05", ["COURT"], "特写，慢动作", "印章落下的闷响", "冷灰"),
    (7, "宫本在侦查阶段一直保持沉默。",
     "拘置所会见室，中间一块玻璃，穿深色西装的男子坐在玻璃另一侧，双手放在膝上，神情平静，轻轻垂下目光，画面冷灰",
     "S09", ["MIYAMOTO"], "近景，缓慢推近", "玻璃对话的低沉回声，钟摆声", "冷灰"),
    (7, "他的辩护方已表示，将主张无罪。",
     "辩护律师走出会见室，被几名记者围住，他停下脚步，对着话筒神情冷静地说话，闪光灯闪烁",
     "", ["COURT"], "手持，中景", "快门声，记者提问声", "冷灰"),
    (6, "在日本，判决确定之前，被告被推定无罪。",
     "黑色背景，一座黄铜天平缓缓摇摆，最终静止在水平位置，画面冷白，只有天平本身，没有图标、标识或文字",
     "P06", [], "特写，缓慢推近", "天平摆动声，一声清脆的金属轻响", "冷白"),
    (6, "2026年11月26日，大阪地方法院开庭。",
     "大阪地方法院外观，灰色石质建筑，清晨，台阶上有几名记者与工作人员走过，天空阴沉，画面庄严",
     "S10", [], "低机位，缓慢推近", "晨风，脚步声", "冷灰法庭"),
    (6, "一共三十二次庭审，2027年3月19日宣判。",
     "法庭内景，六名普通市民裁判员与法官依次入席，他们神情认真，有人低头翻阅资料，窗外一缕光落在法官席上，画面庄严安静",
     "S10", ["COURT"], "横向环绕，缓慢", "法庭环境声，椅子推开声", "冷灰法庭"),
    (6, "法庭将审查的，是控方的证据。",
     "一张老式挂历的近景特写，固定机位，缓慢推近，画面中只有挂历本身，日期数字全部模糊不可辨，只有两个红圈相继亮起，背景是暗色墙面与暖色窗光；没有人物、没有街道、没有招牌、没有任何文字",
     "P04", [], "俯拍，延时", "日历翻页声，红圈亮起的叮声", "冷灰法庭"),
    (6, "案件之外：铊这类毒物，该如何管控？",
     "日本政府官邸的会议室，官员站在讲台前，面前是举着话筒与摄像机的记者，他神情严肃，面向记者，窗外是黄昏",
     "S11", ["OFFICIAL"], "中景，缓慢推近", "记者提问声，快门声", "黄昏冷暖交界"),
    (6, "日本政府曾表示，正在研究加强管控。你怎么看？",
     "黑场中，京都北区公寓楼三楼那扇窗口的灯缓缓亮起，窗帘缝隙里两个杯子的剪影被一道光缓缓抹去，画面中不出现任何文字",
     "S01+P01", [], "缓慢推近，淡入淡出", "夜风渐弱，最后一秒静音", "结尾黑场"),
]

CHAPTER_BOUNDS = [
    (0, 10, "一顿饭与三天"),
    (10, 35, "十月的京都"),
    (35, 60, "滨野倒下"),
    (60, 85, "血液里的铊"),
    (85, 108, "逮捕与叔母"),
    (108, 130, "公司与时间线"),
    (130, 150, "只是指控"),
    (150, 168, "即将开庭"),
    (168, 180, "结尾提问"),
]

# 钩子大字：每条 2 秒，居中偏下。按脚本镜头范围放在该范围第一镜的开始处。
# H1→3–10, H2→11–14, H3→7–10, H4→8(+起诉), H5→11–14(第二个), H6→16–18, H7→19–22, H8→23–25, H9→29–30
HOOKS = [
    {"id": "H1", "shot": "S03", "text": "一顿饭，三天后，她去世了"},
    {"id": "H2", "shot": "S11", "text": "体内检出的，是一种几乎被遗忘的毒"},
    {"id": "H3", "shot": "S07", "text": "饭后，她的身体开始不适"},
    {"id": "H4", "shot": "S08", "text": "据报道：没有叫救护车，联系了父母"},
    {"id": "H5", "shot": "S13", "text": "警方为什么认定这是命案？"},
    {"id": "H6", "shot": "S16", "text": "2020年，叔母也曾突然病倒"},
    {"id": "H7", "shot": "S19", "text": "据报道：病倒三个月后，他任公司代表"},
    {"id": "H8", "shot": "S23", "text": "他保持沉默，辩方主张无罪"},
    {"id": "H9", "shot": "S29", "text": "铊这样的毒物，该怎样管控？"},
]

# 金色小字注释：画面中间偏下，放在无钩子的镜头内，错开钩子出现的前2秒。只补充可核实事实。
EXPLAINERS = [
    {"shot": "S03", "text": "据报道：2022年10月，立命馆大学三年级学生，21岁"},
    {"shot": "S08", "text": "据报道：警方报告称，宫本没有叫救护车，而是联系了她的父母"},
    {"shot": "S09", "text": "据报道：发病后三天，在医院去世"},
    {"shot": "S12", "text": "据报道：检验结果显示体内检出铊"},
    {"shot": "S14", "text": "2023年3月24日：宫本以杀人罪起诉（据报道）"},
    {"shot": "S15", "text": "2023年3月3日：宫本被逮捕（据报道，当时37岁）"},
    {"shot": "S16", "text": "起诉书称：叔母2020年7月病倒，此后长期昏迷"},
    {"shot": "S19", "text": "据报道：叔母病倒约三个月后，宫本任公司代表"},
    {"shot": "S20", "text": "2023年6月14日：被追加起诉，罪名杀人未遂"},
    {"shot": "S21", "text": "目前只是指控，尚未经法院认定"},
    {"shot": "S22", "text": "判决确定之前，被告被推定无罪"},
    {"shot": "S24", "text": "辩方主张无罪 · 尚未开庭"},
    {"shot": "S26", "text": "2026年11月26日一审开庭 · 大阪地方法院"},
    {"shot": "S27", "text": "庭审共32次 · 2027年3月19日宣判（据报道）"},
    {"shot": "S30", "text": "日本政府曾表示，正在研究加强铊的管控（2023年3月）"},
]

# 转场：按脚本原文分段；“切黑 7–10”按镜头 7–10 理解（待用户确认）。
TRANSITIONS = {}
for _i in range(1, 7): TRANSITIONS[f"S{_i:02d}"] = "秋光闪烁"
for _i in range(7, 11): TRANSITIONS[f"S{_i:02d}"] = "切黑"
for _i in range(11, 15): TRANSITIONS[f"S{_i:02d}"] = "冷白闪烁"
for _i in range(15, 23): TRANSITIONS[f"S{_i:02d}"] = "日历翻页"
for _i in range(26, 29): TRANSITIONS[f"S{_i:02d}"] = "天平摆动"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# 解说词重写（2026-11-18）：电影解说口吻，片段之间有因果链，以人名叙述，少用代词。
# 每镜字数上限 = 镜头秒数 × 3.7（一镜一句，对齐镜头窗口）。
NARRATION = {
 "S01": "一顿饭，三天后，滨野日菜子去世了。",
 "S02": "这顿饭，究竟为什么会走到法庭上？",
 "S03": "2022年10月，立命馆大学的校园里，银杏金黄。",
 "S04": "21岁的滨野日菜子，与宫本一希并肩走过小巷。",
 "S05": "十月的一个晚上，两人在居酒屋吃了一顿饭。",
 "S06": "饭后，两人一同回到滨野的公寓。",
 "S07": "10月12日，滨野的身体突然不适，父母赶来接她。",
 "S08": "检方称，宫本没有叫救护车，而是联系了滨野的父母。",
 "S09": "距离那顿饭，仅仅过去三天，滨野在医院去世。",
 "S10": "那一刻，病房里只剩下监护仪的声音。",
 "S11": "转折出现了。据报道，滨野的体内检出了铊这种毒。",
 "S12": "铊是一种剧毒金属，它的名字，离大多数人很远。",
 "S13": "这份报告，让刑警们重新审视整个案子。",
 "S14": "警方因此，把这起事件定为命案。",
 "S15": "命案后，2023年3月，警方逮捕了宫本一希。",
 "S16": "2020年7月，宫本的叔母也病倒住院。",
 "S17": "叔母自2020年病倒后，长期处于昏迷。",
 "S18": "检方认为，这两起事件之间存在关联。",
 "S19": "被指控：叔母病倒三个月后，被告成了公司代表。",
 "S20": "2023年6月，被告因叔母一案被追加起诉。",
 "S21": "检方的罪名是：对叔母的杀人未遂。",
 "S22": "目前为止，这些都只是检方的指控。",
 "S23": "面对侦查，宫本始终保持沉默，关键答案仍悬而未决。",
 "S24": "辩护方表示：被告主张无罪。案件，还远未结束。",
 "S25": "在日本，判决确定之前，被告被推定无罪。",
 "S26": "这场审判，将于2026年11月26日开庭。",
 "S27": "全案三十二次庭审，2027年3月19日宣判。",
 "S28": "法庭审的是证据，而案件背后，还有一个问题。",
 "S29": "这个问题是：铊这类毒物，到底该如何管控？",
 "S30": "日本政府曾表示，正在研究加强管控。你怎么看？",
}


# 把新旁白写回 ROWS，使 story.json / 剧本 / 抖音脚本 三处一致。
ROWS = [(row[0], NARRATION[f"S{i:02d}"]) + tuple(row[2:]) for i, row in enumerate(ROWS, 1)]

def build() -> dict:
    cursor = 0
    shots = []
    for index, row in enumerate(ROWS, 1):
        duration, narration, visual, refs, roles, camera, sound, grade = row
        sid = f"S{index:02d}"
        narration = NARRATION[sid]
        start = cursor
        cursor += duration
        chapter = next(
            f"N{i:02d}" for i, (lo, hi, _) in enumerate(CHAPTER_BOUNDS, 1) if lo <= start < hi
        )
        prompt = (
            f"{visual}。真实连续运动贯穿全镜，镜头运镜：{camera}；构图保持16:9横屏，"
            "主体置于三分线，底部字幕安全区保持低干扰；不要任何文字、标签、时间戳或招牌。"
        )
        shots.append({
            "id": sid, "kind": "agnes", "start": start, "duration": duration,
            "seconds": duration, "aspect": "16:9", "source_size": "720P",
            "narration_id": chapter, "narration": narration,
            "prompt": prompt, "purpose": visual, "characters": roles,
            "seed": 20221015 + index,
            "camera": camera, "sound_design": sound, "color_grade": grade,
            "reference_ids": refs,
            "transition_in": TRANSITIONS.get(sid, "常规切换"),
            "transition_out": "以悬念句与短暂停顿收束，环境保持微动",
        })
    if len(shots) != 30 or cursor != 180:
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

    shot_start = {s_["id"]: s_["start"] for s_ in shots}
    hooks = []
    for h in HOOKS:
        t0 = shot_start[h["shot"]]
        hooks.append({"id": h["id"], "start": t0, "end": t0 + 2.0, "text": h["text"], "style": "big_white_black_outline", "shot": h["shot"]})
    explainers = []
    for e in EXPLAINERS:
        t0 = shot_start[e["shot"]] + 2.5
        explainers.append({"start": t0, "end": t0 + 3.5, "text": e["text"], "color": "gold", "shot": e["shot"]})
    presentation = {
        "onscreen_label": "AI动画情景重现 · 非真实影像",
        "highlight_phrases": [
            "一顿饭", "三天后", "她去世了", "铊", "2022年10月", "立命馆大学", "据报道", "没有叫救护车",
            "命案", "2023年3月", "叔母", "2020年7月", "脑炎", "检出", "追加起诉", "杀人未遂", "指控",
            "推定无罪", "无罪", "2026年11月26日", "三十二次", "2027年3月19日", "管控",
        ],
        "hooks": hooks,
        "explainers": explainers,
        "end_title": "京都铊中毒案",
        "end_subtitle": "京都 · 2022—2027 · 尚待判决",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "一顿饭，三天后",
        "cover_concept": "封面只用本片已生成视频的真实帧：左半为夜晚公寓三楼亮灯的窗与窗帘间的杯影，右半为实验室屏幕上红色高亮的抽象原子图标，中间一道光；后期加大字“一顿饭，三天后”金色加黑边。",
        "publish_title": "一顿饭，三天后她去世了：京都女大学生铊中毒案，即将开庭",
        "hashtags": ["#真实事件", "#京都铊中毒案", "#日本", "#悬疑", "#电影感", "#法律"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在镜头30由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "checked_against_japanese_press_reports_2023_and_2026-09-10",
        "as_of": "2026-11-18",
        "legal_note": "案件处于审理前阶段；被告被推定无罪。全片只使用据报道、检方称、辩方主张等限定表述，不定性、不推断动机，结尾只讨论毒物管控。",
        "sources": "见 FACT_CHECK.md",
    }

    project = {
        "title": TITLE,
        "film_name": "京都铊中毒案_一顿饭三天后_三分钟_带声音.mp4",
        "target_duration": 180, "width": 1920, "height": 1080, "fps": 24,
        "model": "agnes-video-2.5-flash", "source_size": "720P", "branch": BRANCH,
        "style_prefix": STYLE, "negative_prompt": NEGATIVE, "style_rumor_prefix": STYLE,
        "characters": CHARACTERS, "character_seeds": CHARACTER_SEEDS,
        "narration_spec": {
            "voice_id": voice_id,
            "description": voice.get("description", "悬疑低沉、克制的成熟普通话男声；逐镜独立配音"),
            "language": "zh-CN", "target_characters_per_second": 3.7,
            "alignment": "一镜一句，一镜一条TTS与一条字幕；只在确有必要时加速，不慢放",
        },
        "chapters": chapters, "shots": shots,
        "reference_images": ref_images,
        "reference_revision": revision,
        "reference_designs": {
            "characters": [f"C{i:02d}" for i in range(1, 10)],
            "scenes": [f"S{i:02d}" for i in range(1, 13)],
            "props": [f"P{i:02d}" for i in range(1, 7)],
            "note": "27张逐张审核的PNG：9张角色参考、12张16:9环境概念、6张16:9道具图；Agnes调用使用不可变raw链接。",
        },
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期放大到1080P。",
            "所有Agnes提示词由generate.py自动组合：STYLE在最前，角色锚点逐字插入，NEGATIVE在末尾；仅镜头30允许后期标题，AI源片不画字。",
            "全片无BGM；旁白与字幕逐句锁定，音效/环境声只做轻量辅助，不盖住解说。",
            "真实人物一律以非真实肖像的写实演员式形象呈现；病房只以被子、手部、监护仪与窗光表现。",
        ],
    }
    (HERE / "story.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [
        f"# {TITLE}", "",
        "抖音横屏｜1920×1080｜16:9｜24fps｜180秒｜30个Agnes Video 2.5 Flash写实影像片段｜无BGM。",
        "", "| 镜头 / 时间 | 旁白 | 画面与运镜 | 参考图 | 音效/环境声备注 |", "|---|---|---|---|---|",
    ]
    ts = lambda sec: f"{sec // 60:02d}:{sec % 60:02d}"
    for shot, row in zip(shots, ROWS):
        _, narration, visual, refs, roles, camera, sound, grade = row
        end = shot["start"] + shot["duration"]
        rows.append(f"| {shot['id']} / {ts(shot['start'])}–{ts(end)} | {narration} | {visual}（{camera}；{grade}） | {refs or '-'} + {','.join(roles) or '无角色'} | {sound} |")
    rows += ["", "## H1–H9 钩子", "", "| 钩子 | 时间 | 大字字幕 |", "|---|---:|---|"]
    for hook in hooks:
        rows.append(f"| {hook['id']} | {hook['start']:.0f}–{hook['end']:.0f}s（{hook['shot']}） | {hook['text']} |")
    screenplay = "\n".join(rows) + "\n"
    (HERE / "screenplay.md").write_text(screenplay, encoding="utf-8")
    (HERE / "抖音脚本.md").write_text(screenplay, encoding="utf-8")

    publish = "\n".join([
        f"# {presentation['publish_title']}", "",
        "## 抖音标题", "", presentation["publish_title"], "",
        "## 简短介绍", "",
        "2022年10月，京都。立命馆大学三年级学生滨野日菜子的一顿饭之后，三天后在医院去世。据报道，警方在她体内检出铊，并以命案立案；2023年3月，宫本被逮捕，此后被追加起诉，涉及其叔母2020年的病倒一案。案件目前处于审理前阶段，被告被推定无罪。大阪地方法院定于2026年11月26日开庭。写实3D动画情景重现，非真实影像。",
        "", "## 提问读者一句话", "", "铊这样的毒物，该怎样管控？你觉得应该怎么做？", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", "", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

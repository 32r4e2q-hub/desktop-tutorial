#!/usr/bin/env python3
"""唯一内容源：济州岛敞篷车命案 30 镜 / 180 秒 / Agnes Video 2.5 Flash reference mode。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "济州岛敞篷车命案：19秒"
BRANCH = "arena/5375d891-desktop-tutorial"

STYLE = (
    "【STYLE】电影级写实3D动画情景重现，明确标注为非真实历史影像；35mm胶片摄影质感，浅景深，"
    "长焦压缩，韩国悬疑公路电影风格，济州岛海边公路、黑色玄武岩石墙、橘子田；2019年韩国济州，"
    "准确呈现当年普通租车行、民宿、餐厅、警用装备与法庭陈设的材质；真实人体比例、自然皮肤纹理、"
    "可信布料、车辆与建筑表面，低饱和、暗部厚重、细腻胶片颗粒，克制冷静而压抑的情绪；"
    "镜头3至5济州阳光明亮暖色，镜头6转暮色蓝调，镜头7至12夜晚深蓝冷调与红色尾灯，"
    "镜头13至14警灯冷青，镜头15至18医院与公寓冷白灰，镜头19至22深夜台灯暖黄与手机冷光，"
    "镜头23至29冷灰法庭，镜头30黑场与声波的一抹红；"
    "16:9横屏宽银幕，主体放在三分线附近，画面底部六分之一留作字幕安全区；所有镜头必须是真实连续运动的3D影像，"
    "有自然呼吸、眨眼、手部动作、脚步、海风吹动、灯光变化或车辆行驶，镜头本身平稳移动，绝不以静态图加推拉冒充视频；"
    "录音声波与0:19计时器是贯穿全片的视觉母题，红色野马敞篷车与安全带警示灯是第二、第三条线索；"
    "事故只用声波图形、黑场、路缘与石墙空镜、事后现场表现，绝不出现撞击瞬间、遗体、血腥或伤口；"
    "每个镜头末端只做一瞬克制的悬念停顿，环境仍保持细微运动；所有人物均为虚构演员式形象，不还原任何真实人物肖像。"
)
NEGATIVE = (
    "【NEGATIVE】卡通，Q版，动漫，夸张表情，过度饱和，文字，水印，字幕，可读文字，真实姓名，真实肖像，"
    "血腥，伤口，遗体，尸体，撞击瞬间，车祸现场写实画面，暴力过程，武器，畸形手指，多余肢体，"
    "人物面部崩坏，低清晰度，画面闪烁，风格突变，竖屏构图，黑边，静态图加推拉，幻灯片，拼版，伪招牌。"
)

# 角色锚点逐字采用本期定稿口径；generate.py 会将其原文拼到每个对应镜头的提示词中。
CHARACTERS = {
    "EUNAE": "【C01锚点】29岁韩国女性,黑色及肩长发,清秀明亮,米色针织外套牛仔裤,笑容温暖爽朗",
    "CHOI": "【C02锚点】34岁韩国男子,瘦高,短发,黑色夹克白T恤,外表体面,神情淡漠,眼神游离",
    "SISTER": "【C03锚点】30岁出头韩国女性,齐肩短发,深色外套,神情沉稳坚定,眼神锐利",
    "MOTHER": "【C04锚点】58岁韩国女性,短烫发,素色外套,神情憔悴温和",
    "POLICE": "【C05锚点】30至40岁韩国警察,制服夜光背心,神情严肃克制",
    "MANAGER": "【C06锚点】60岁韩国男子,深色工作服帽子,神情朴实",
    "PROSECUTOR": "【C07A锚点】45岁韩国检察官,深色西装,神情坚定",
    "JUDGE": "【C07B锚点】55岁韩国法官,黑色法袍,神情肃穆",
    "EXPERT": "【C07C锚点】45岁韩国法律专家,戴眼镜,衬衫,神情冷静",
    "LAWYER": "【C08锚点】50岁韩国男律师,深色西装,神情冷静克制,手拿卷宗",
}

CHARACTER_SEEDS = {
    "EUNAE": 291110,
    "CHOI": 341110,
    "SISTER": 301110,
    "MOTHER": 581110,
    "POLICE": 501110,
    "MANAGER": 601110,
    "PROSECUTOR": 451110,
    "JUDGE": 551110,
    "EXPERT": 451111,
    "LAWYER": 501111,
}

# duration, narration, visual beat, design references, character roles, camera, sound, color
ROWS = [
    (5, "听这段十九秒的录音。你没系安全带？",
     "黑场中一部手机屏幕亮起，录音声波一格格跳动，右下角计时器停在0:19，一盏红色安全带警示灯在黑暗里闪烁，画面静得出奇，声波与灯光持续细微跳动。",
     "P01+P03", [], "大特写缓慢推近", "一声清脆的安全带警报叮声，随后一片死寂", "黑场与一抹红"),
    (5, "随即引擎轰鸣，三级法院给了同一个答案。",
     "夜晚济州海边公路，一辆红色野马敞篷车从远处驶来，车灯切开黑暗，车内人影模糊，红色尾灯在冷蓝夜色中拉出光线，海风吹动路边草叶。",
     "S06+P02", [], "低机位长焦跟拍", "引擎声由低到高，海风", "夜晚冷蓝与红色尾灯"),
    (7, "2019年11月，济州岛。赵恩爱和男友崔某，来庆祝交往三百天。",
     "2019年11月济州机场到达大厅，赵恩爱推着行李箱，笑着挽着男友崔某的手臂走出，窗外阳光明媚，她手里拿着一本旅行手册，身后旅客缓缓走动，画面明亮温暖。",
     "S01", ["EUNAE", "CHOI"], "中景缓慢推近", "机场广播，行李滚轮声", "明亮暖色"),
    (7, "恩爱不想租敞篷车，崔某却坚持，要租一辆野马敞篷。",
     "济州租车行柜台，店员递出一把车钥匙，崔某接过笑着晃了晃，恩爱在旁边摇头，指着旁边的普通轿车似乎在劝他换一辆，他不为所动，门外阳光洒进，红色敞篷车停在店外。",
     "S02+P02", ["EUNAE", "CHOI"], "中景侧面", "钥匙碰撞声，轻声争论", "明亮暖色"),
    (6, "拍照时恩爱笑得很甜，没察觉崔某早已心不在焉。",
     "济州海边黑色玄武岩石墙边，两人并肩坐在岩石上拍照，恩爱笑得灿烂，崔某对着镜头摆姿势，画面温暖，海浪轻拍礁石，却在崔某游离的眼神里有一丝心不在焉。",
     "S03", ["EUNAE", "CHOI"], "长焦缓慢推近", "海浪声，快门声", "明亮暖色"),
    (5, "谁想到纪念之旅中，崔某向恩爱提出分手。",
     "民宿阳台黄昏，崔某手撑栏杆望着远处海面，恩爱在他身后，脸上的笑容渐渐凝固，手里的纪念礼物被攥得变形，他低声说了什么，她的肩膀微微一抖，远处余晖渐暗。",
     "S04", ["CHOI", "EUNAE"], "中景缓慢推近恩爱的背影", "海风，一声轻微的吸气", "暮色蓝调"),
    (7, "11月10日凌晨，餐厅里，两人相对无言，桌上还有没喝完的酒。",
     "夜晚济州小餐厅暖黄灯光下，两人对坐，桌上摆着一瓶酒与酒杯，崔某举杯，恩爱沉默低头擦着眼眶，一个酒杯被轻轻推开，邻桌人影虚焦晃动，气氛压抑。",
     "S05", ["EUNAE", "CHOI"], "中景缓慢推近", "餐厅低语，杯子碰桌声", "夜晚冷蓝与暖黄灯光"),
    (7, "一点钟，车开上翰林邑的海边公路，车里的空气，降到了冰点。",
     "11月10日凌晨济州翰林邑海边公路，红色野马敞篷车缓缓驶出，海风吹起她的头发，车内她看着窗外，崔某握着方向盘目视前方，仪表盘冷光映在他脸上，路灯向后掠去。",
     "S06+S07+P02", ["EUNAE", "CHOI"], "车内缓慢推近", "海风，引擎低鸣", "夜晚冷蓝与红色尾灯"),
    (6, "安全带警报响了，崔某问：“你没系安全带？”恩爱说：“嗯。”",
     "深夜敞篷车驾驶室特写一镜到底，红色安全带警示灯亮起，他瞥了一眼副驾，嘴型是问话，她点头应声，他的目光回到前方，手指在方向盘上收紧，警示灯持续闪烁。全镜只发生在这个深夜车厢内，不切换到白天、警车、办公室或其他任何场景，不叠加声波线。",
     "S07+P03", ["CHOI", "EUNAE"], "近景缓慢推近", "安全带警报叮叮叮", "夜晚冷蓝与红色警示灯"),
    (5, "紧接着轰鸣，车速从五十，飙到一百一十四公里。",
     "汽车仪表盘上指针猛地上扬，车外路灯化作一条条光线向后飞逝，引擎轰鸣，红色尾灯拉线，车内没有任何人声，只有风声灌入，画面快速切换充满速度感。",
     "P04+S06", [], "快速切换，动态模糊", "引擎轰鸣，风声", "夜晚冷蓝与红色尾灯"),
    (7, "十九秒后，车撞上路缘、石墙，和一台耕耘机。",
     "手机录音界面大特写，声波剧烈起伏，计时器从0:00走到0:19，警示音、引擎、尖叫的声波依次爆发然后戛然而止，画面只用图形化声波表现，不出现任何撞击画面。",
     "P01", [], "大特写缓慢推近", "警示音、引擎、尖叫的声波依次爆发，然后戛然而止", "黑场与一抹红"),
    (7, "恩爱被抛出车外没再醒来，崔某却几乎毫发无伤。",
     "夜晚公路旁，画面切黑后是一片宁静的黑暗，只有一缕车灯光照亮石墙与一台耕耘机的轮廓，烟雾从远处升起，海浪声隐约，画面克制，不出现任何人与车辆细节。",
     "S08", [], "低机位缓慢推近", "引擎余音，远处海浪", "夜晚冷蓝"),
    (6, "警察赶到时，崔某站在路边，平静地和警察交谈。",
     "警察赶到现场，红蓝警灯在石墙上稳定闪烁，崔某站在路边神情平静地和警察交谈，衣服上几乎没有任何污迹，警车灯光扫过路面，画面克制。",
     "S08", ["POLICE", "CHOI"], "中景缓慢推近", "警笛声，对讲机杂音", "警灯冷青"),
    (5, "崔某血液酒精超标，达到吊销驾照水平。",
     "警察将一台酒精测试仪递到他面前，他吹气，测试仪屏幕只显示抽象光点，警察皱眉记录，他的表情依旧淡漠，警灯在远处闪烁，画面压抑。",
     "S08", ["POLICE", "CHOI"], "近景缓慢推近", "吹气声，测试仪嘀的一声", "警灯冷青"),
    (6, "恩爱躺在重症监护室里，崔某，一次也没来过。",
     "济州医院夜晚走廊冷白灯光，急救床匆匆推过，ICU的双开门合上，恩爱的姐姐扶着母亲站在走廊，脸色苍白，医护身影匆匆掠过，长椅空着。",
     "S09", ["SISTER", "MOTHER"], "中景缓慢推近", "急救床滚轮声，医护急促脚步", "冷白灰"),
    (6, "恩爱母亲求崔某探望，换来的只有沉默。",
     "ICU外，母亲对着手机拨打电话，神情恳求，电话另一头沉默，电话被挂断，母亲慢慢蹲下身，姐姐扶住她，走廊的灯光闪了一下，画面压抑。",
     "S09", ["MOTHER", "SISTER"], "近景缓慢推近", "拨号音，挂断的嘟声", "冷白灰"),
    (6, "诡异的是，事发三天后，恩爱出租屋密码被换了。",
     "三天后恩爱租住的公寓楼，家人站在门前输入密码，门锁亮起红灯错误，他们对视，姐姐转身去找管理员，走廊声控灯亮起又熄灭，气氛凝重。",
     "S10+P05", ["SISTER"], "中景缓慢推近门锁", "按键声，错误提示音", "冷白灰"),
    (5, "监控里，崔某两次进出，拿走电脑换掉密码。",
     "管理员室监控视角，黑白监控画面里一个男子提着笔记本电脑走出公寓，过一会儿又回来，在门锁面板前按了几下，管理员站在旁边观看，时间戳以抽象光点闪烁。",
     "S10+P06", ["MANAGER", "CHOI"], "监控视角缓慢推近", "监控电流声，按键声", "冷白灰"),
    (6, "姐姐翻遍妹妹手机，点开11月10日的录音。",
     "深夜房间台灯暖黄，姐姐翻看妹妹的手机，照片、短信、通话记录一页页划过，她的手指停在一个录音文件上，盯着看了很久，按下播放，窗外夜色深沉。",
     "S11+P06", ["SISTER"], "近景缓慢推近手机屏幕", "屏幕划动声，按键声", "台灯暖黄与手机冷光"),
    (6, "那十九秒里：警报、问话、轰鸣，还有恩爱尖叫。",
     "录音声波在手机屏幕上跳动，姐姐戴着耳机聆听，眼睛越睁越大，手捂住嘴，台灯暖黄与屏幕冷光交映在她脸上，窗帘被夜风吹动，空气凝固。",
     "S11+P01", ["SISTER"], "近景缓慢推近她的眼睛", "压抑的呼吸，警示音，引擎声", "台灯暖黄与手机冷光"),
    (5, "没有崔某声音，姐姐浑身发抖：这是谋杀。",
     "姐姐浑身发抖，摘下耳机，把手机放在桌上，猛地站起拿起外套走向门口，门被重重关上，台灯晃了一下，房间只剩手机屏幕的冷光。",
     "S11", ["SISTER"], "中景缓慢推近", "椅子推开声，门关上的闷响", "台灯暖黄与手机冷光"),
    (5, "姐姐把手机交给警察，案件重新被点燃。",
     "警察署办公室冷灰日光灯下，姐姐把手机推到警察面前，警察戴上耳机听完神情复杂，桌上的卷宗被翻开，窗外天色微明。",
     "S12", ["SISTER", "POLICE"], "过肩缓慢推近", "耳机里漏出的轻微声响，纸张翻动声", "冷灰"),
    (7, "2020年8月，昏迷近十个月后，恩爱去世了。",
     "2020年8月医院病房，窗帘半掩，监护仪的曲线最终拉成一条直线，画面克制不出现病人，只有窗外一缕光慢慢移走，输液管轻晃。",
     "S13", [], "固定机位缓慢推近监护仪", "监护仪长鸣，窗外风声", "冷灰"),
    (7, "案发一年五个月后，检方以杀人罪起诉崔某，求刑十五年。",
     "检察厅办公室冷灰台灯下，一位检察官翻阅案卷，桌上摆着录音图表与打印件，他写下字样后抬头目光坚定，窗外夜色深沉，案卷堆叠。",
     "S14+P01", ["PROSECUTOR"], "中景缓慢推近", "笔尖划纸声，纸张翻动声", "冷灰"),
    (6, "专家称，明知恩爱没系带仍加速，或属“未必故意”。",
     "电视演播室冷蓝灯光下，专家站在大屏幕前讲解，大屏幕只显示抽象图形，观众席一片沉默，镜头缓缓靠近，气氛凝重。",
     "S15", ["EXPERT"], "中景缓慢推近", "演播室低沉的环境声，一声咳嗽", "冷灰"),
    (6, "2021年12月，一审判决：杀人罪，无罪。",
     "2021年12月济州地方法院法庭，法官宣读判决，崔某站在被告席神情平静，姐姐与母亲坐在旁听席脸色铁青，法槌落下，全场寂静。",
     "S16", ["CHOI", "SISTER", "MOTHER", "JUDGE"], "横向环绕缓慢", "法官宣读声，法槌落下回响", "冷灰"),
    (6, "法官说：提醒系安全带，与杀人故意，恰恰相矛盾。",
     "法官特写缓缓说出判词，画面分屏：左边是0:19的计时器，右边是一根安全带被拉出又扣上的动作，象征足够系上，天平在中间摇晃，冷蓝光笼罩。",
     "P08", ["JUDGE"], "分屏缓慢推近", "天平摆动声，安全带扣上的咔哒声", "冷灰与冷蓝光"),
    (6, "十九秒够系带，崔某也在车上，酒驾判一年缓两年。",
     "旁听席上母亲低下头，姐姐握紧拳头，另一侧崔某的律师低头整理文件，画面冷灰，窗外下起了雨，雨点滑落玻璃。",
     "S16", ["MOTHER", "SISTER", "LAWYER"], "中景缓慢横移", "雨声，压抑的呼吸", "冷灰"),
    (6, "检方追加危险驾驶致死。二审改判四年，最高法院维持。",
     "2022年9月光州高等法院济州分院法庭，法官宣读二审判决，崔某被两名法警带走，他回头看了一眼旁听席又被带出，法庭大门缓缓合上。",
     "S17", ["CHOI", "JUDGE"], "中景缓慢推近", "法官宣读声，门合上的闷响", "冷灰"),
    (6, "杀人始终没有成立。那十九秒里，崔某想的究竟是什么？",
     "黑场中一条录音声波从0:00走到0:19，走完后化作一条平线，声波边缘留一抹红，镜头缓慢推近，最后淡入黑场，标题由后期叠加。",
     "P01+P07", [], "缓慢推近，淡入淡出", "声波的嗡声，平线的长鸣，最后一秒静音", "黑场与声波的一抹红"),
]

CHAPTER_BOUNDS = [
    (0, 10, "黄金钩子"),
    (10, 35, "300天纪念之旅"),
    (35, 60, "那一夜"),
    (60, 85, "事故与酒精"),
    (85, 108, "被换掉的密码"),
    (108, 130, "手机里的录音"),
    (130, 150, "起诉杀人"),
    (150, 168, "一审无罪"),
    (168, 180, "改判四年与结尾提问"),
]

HOOKS = [
    {"id": "H1", "start": 0.0, "end": 2.0, "text": "19秒录音：你没系安全带？", "style": "big_white_black_outline"},
    {"id": "H2", "start": 8.0, "end": 10.0, "text": "意外，还是谋杀？", "style": "big_white_black_outline"},
    {"id": "H3", "start": 30.0, "end": 32.0, "text": "崔某在纪念之旅里，提了分手", "style": "big_white_black_outline"},
    {"id": "H4", "start": 55.0, "end": 57.0, "text": "车速：从50，冲到114公里", "style": "big_white_black_outline"},
    {"id": "H5", "start": 103.0, "end": 105.0, "text": "事发三天后，密码被换了", "style": "big_white_black_outline"},
    {"id": "H6", "start": 125.0, "end": 127.0, "text": "姐姐说：这是谋杀", "style": "big_white_black_outline"},
    {"id": "H7", "start": 144.0, "end": 146.0, "text": "明知没系安全带，仍然加速", "style": "big_white_black_outline"},
    {"id": "H8", "start": 156.0, "end": 158.0, "text": "真想杀人，为何提醒系安全带？", "style": "big_white_black_outline"},
    {"id": "H9", "start": 168.0, "end": 170.0, "text": "杀人无罪，危险驾驶致死四年", "style": "big_white_black_outline"},
]

EXPLAINERS = [
    {"start": 2.1, "end": 4.8, "text": "19秒：从加速到撞击 · 行车记录与车辆数据", "color": "gold"},
    {"start": 10.1, "end": 14.8, "text": "2019年11月 · 济州岛 · 交往300天", "color": "gold"},
    {"start": 32.1, "end": 34.8, "text": "检方称：旅途中提分手，被拒", "color": "gold"},
    {"start": 57.1, "end": 59.8, "text": "检方：明知未系安全带仍加速；法院：不足以认定杀人故意", "color": "gold"},
    {"start": 80.1, "end": 84.8, "text": "血液酒精浓度0.118% · 吊销驾照水平", "color": "gold"},
    {"start": 105.1, "end": 107.8, "text": "崔某称：怕有人进屋拿走东西", "color": "gold"},
    {"start": 127.1, "end": 129.8, "text": "家属的判断；法院认为证据不足以认定杀人故意", "color": "gold"},
    {"start": 146.1, "end": 149.8, "text": "未必故意：明知可能致死，仍放任发生", "color": "gold"},
    {"start": 158.1, "end": 161.8, "text": "法院：19秒足以系好；崔某自己也处危险中", "color": "gold"},
    {"start": 170.1, "end": 173.8, "text": "2022年9月二审 · 2023年1月最高法院确定", "color": "gold"},
]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> dict:
    cursor = 0
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
        wave_shots = {1, 11, 20, 27, 30}
        if index in wave_shots:
            motif = (
                "本镜头允许手机录音声波与0:19计时器作为真实画面元素出现，"
                "声波跳动自然，数字清晰稳定、无闪烁无变形；"
            )
        elif index == 10:
            motif = (
                "本镜头允许抽象的汽车仪表盘与上扬指针出现，但不得有任何可读数字、字母或标识；"
            )
        else:
            motif = (
                "本镜头不出现声波图形、计时器数字、悬浮界面、文字、标签、时间戳或招牌；"
            )
        prompt = (
            f"{visual} {motif}真实连续运动贯穿全镜，镜头运镜：{camera}；构图保持16:9横屏，"
            "主体置于三分线，底部字幕安全区保持低干扰；不要任何文字、标签、时间戳或招牌。"
        )
        shots.append({
            "id": sid, "kind": "agnes", "start": start, "duration": duration,
            "seconds": duration, "aspect": "16:9", "source_size": "720P",
            "narration_id": chapter, "narration": narration,
            "prompt": prompt, "purpose": visual, "characters": roles,
            "seed": 20191110 + index,
            "camera": camera, "sound_design": sound,
            "color_grade": grade, "reference_ids": refs,
            "transition_in": "按本片色调方案执行的短促电影转场，不改变事实内容",
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

    presentation = {
        "onscreen_label": "AI动画情景重现 · 非真实影像",
        "highlight_phrases": [
            "19秒", "十九秒", "你没系安全带", "三百天", "300天", "野马敞篷", "分手",
            "一百一十四公里", "114公里", "50", "0.118%", "吊销驾照", "密码被换了",
            "这是谋杀", "谋杀", "未必故意", "求刑十五年", "无罪", "四年", "缓刑两年",
            "危险驾驶致死", "2020年8月", "2021年12月", "三级法院",
        ],
        "hooks": HOOKS,
        "explainers": EXPLAINERS,
        "end_title": "济州岛敞篷车命案",
        "end_subtitle": "韩国济州 · 2019—2023 · 19秒",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "19秒",
        "cover_concept": "封面只用本片已生成视频截图：夜晚海边公路上的红色敞篷车与录音声波；后期加大字“19秒”金色黑边，禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "一句“你没系安全带？”，然后是19秒的引擎轰鸣：济州岛敞篷车命案",
        "hashtags": ["#真实事件", "#济州岛敞篷车", "#韩国", "#悬案", "#法律", "#电影感"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在镜头30由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "cross_checked_against_Korean_court_reports_and_Chinese_reports",
        "as_of": "2026-11-17; facts below are pinned to the cited reports; the film states disputed points only as 检方称/家属称/法院认为",
        "legal_note": "一审（2021-12-16济州地方法院）：杀人无罪，酒驾有罪判1年缓2年；二审（2022-09-28光州高法济州分院）：杀人仍无罪，追加危险驾驶致死判4年并法庭拘束；终审（2023-01-12最高法院）：驳回上诉，4年确定。法院三级一致认定杀人故意证据不足。",
        "sources": [
            {"publisher": "Newsjeju", "date": "2021-08-09", "url": "https://www.newsjeju.net/news/articleView.html?idxno=366125", "supports": "2019-11-09抵济州租野马敞篷；500米路段平均50km、最高114km；撞路缘石墙耕耘机；黑匣子录像与现场音；血醇0.118%；警方初以危险驾驶致伤+酒驾送检，检方改为杀人"},
            {"publisher": "edaily", "date": "2021-12-16", "url": "https://www.edaily.co.kr/news/read?mediaCodeNo=257&newsId=02505926629279176", "supports": "一审杀人无罪；19秒前问安全带、答嗯、加速至114km；2020年8月去世；血醇0.118%吊销水平"},
            {"publisher": "Herald Business", "date": "2023-01-12", "url": "https://biz.heraldcorp.com/article/3040057", "supports": "最高法院4年确定、杀人无罪确定；问安全带反而不自然；司机自己也有翻车死亡风险；求刑背景与检方分手动机主张"},
            {"publisher": "Kyunghyang Shinmun", "date": "2022-09-28", "url": "https://www.khan.co.kr/article/202209281755001", "supports": "二审杀人无罪、危险驾驶致死4年；一审1年缓2年被撤销；检方求刑15年；未系安全带被抛出车外"},
            {"publisher": "Segye Ilbo", "date": "2022-09-28", "url": "https://www.segye.com/newsView/20220928510541", "supports": "二审法庭拘束；预备诉因危险驾驶致死；未获家属谅解从重、初犯反省酌情"},
            {"publisher": "etoday", "date": "2023-01-12", "url": "https://www.etoday.co.kr/news/view/2212084", "supports": "2019-11-10凌晨1点翰林邑；终审维持；主审法官与三级裁判脉络"},
            {"publisher": "KBS News", "date": "2023-01-12", "url": "https://news.kbs.co.kr/news/pc/view/view.do?ncd=7298983", "supports": "终审4年确定；确认未系安全带后加速的检方指控口径；2020年8月去世"},
            {"publisher": "网易号 脑洞乌托邦小乌", "date": "2021-09-29", "url": "https://www.163.com/dy/article/GL36NTT505522XPA.html", "supports": "300天纪念、租车争议、分手经过、姐姐发现手机长录音、密码被换与笔记本、闺蜜事实婚姻证人电话、2020-08-23去世、2021-04以杀人重新起诉（中文自媒体，转述口径，见FACT_CHECK.md保留项）"},
            {"publisher": "网易号", "date": "2023-06-21", "url": "https://www.163.com/dy/article/I7P0FRIG0553RJ3L.html", "supports": "1小时1分24秒录音梗概、方向盘操作争议梗概（转述口径，仅作结构参考，不作事实依据）"},
        ],
        "editorial_cautions": [
            "受害者赵恩爱、姐姐为中文报道中的称呼，韩媒作匿名处理；崔某为媒体假名；片中人物均为虚构演员式形象。",
            "车辆只确定为福特野马敞篷租车；有中文自媒体称白色，本片按脚本用红色，属情景重现艺术处理，不影响法律事实。",
            "录音载体：韩媒明确法庭公开了车载黑匣子录像与现场音；中文自媒体称姐姐在手机备忘录发现长录音；本片按脚本采用手机录音说法。",
            "年龄：中文自媒体称28岁，本片按脚本取29岁（疑为韩国年龄口径），属次要细节，已在FACT_CHECK.md注明。",
            "密码与笔记本情节只见于中文自媒体单源转述，片中以监控画面情景重现呈现，并配崔某说法字幕，不下结论。",
            "全片涉及动机的表述一律用检方称/家属认为/法院认为；终审结论为杀人罪不成立、危险驾驶致死4年，不作反转暗示。",
            "不展示撞击瞬间、遗体、血腥、伤口；事故只用声波、黑场、空镜与事后现场表现。",
        ],
    }

    project = {
        "title": TITLE,
        "film_name": "济州岛敞篷车命案_19秒_三分钟_带声音.mp4",
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
            "characters": ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08"],
            "scenes": [f"S{i:02d}" for i in range(1, 18)],
            "props": [f"P{i:02d}" for i in range(1, 9)],
            "note": "33张逐张审核的PNG：8张角色参考、17张16:9环境概念、8张道具特写；Agnes调用使用不可变raw链接。",
        },
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期高质量放大到1080P。",
            "所有Agnes提示词由generate.py自动组合：STYLE在最前，角色锚点逐字插入，NEGATIVE在末尾；仅镜头30允许后期标题，不让模型画字。",
            "镜头每5条抽查一次人物脸和服装漂移；出现漂移则以同一批准参考图只重生成对应镜头。",
            "全片无BGM；旁白与字幕逐句锁定，音效/环境声只做轻量辅助，不盖住解说。",
            "转场按脚本章节使用海风光线、红色尾灯拉线、监控闪烁、手机屏幕光、天平摆动和0.3秒黑场淡入。",
        ],
    }
    (HERE / "story.json").write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    rows = [
        f"# {TITLE}", "",
        "抖音横屏｜1920×1080｜16:9｜24fps｜180秒｜30个Agnes Video 2.5 Flash写实3D动画片段｜无BGM。",
        "", "| 镜头 / 时间 | 旁白 | 画面与运镜 | 参考图 | 音效/环境声备注 |", "|---|---|---|---|---|",
    ]
    for shot, row in zip(shots, ROWS):
        _, narration, visual, refs, roles, camera, sound, grade = row
        end = shot["start"] + shot["duration"]
        ts = lambda sec: f"{sec // 60:02d}:{sec % 60:02d}"
        rows.append(f"| {shot['id']} / {ts(shot['start'])}–{ts(end)} | {narration} | {visual}（{camera}；{grade}） | {refs} + {','.join(roles) or '无角色'} | {sound} |")
    rows += [
        "", "## H1–H9 钩子与解释字幕", "",
        "钩子字幕：白字黑边、大字、居中偏下（MarginV=275）、每条严格 2 秒；关键词金色高亮。解释字幕：金色小字，置于画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂，不遮挡主体。",
        "", "| 钩子 | 时间 | 大字字幕 | 对应解释时间 / 金字 |", "|---|---:|---|---|",
    ]
    def stamp(seconds: float) -> str:
        minutes, rest = divmod(float(seconds), 60)
        return f"{int(minutes):02d}:{rest:05.2f}"
    for hook in HOOKS:
        explainer = min(EXPLAINERS, key=lambda item: abs(float(item["start"]) - float(hook["end"])))
        explanation = f"{stamp(explainer['start'])}–{stamp(explainer['end'])} / {explainer['text']}"
        rows.append(f"| {hook['id']} | {stamp(hook['start'])}–{stamp(hook['end'])} | {hook['text']} | {explanation} |")
    rows += [
        "", "## 事实与安全口径", "",
        "- 赵恩爱与家人为中文报道中的称呼，韩媒匿名；崔某为媒体假名；人物均为虚构演员式形象。片头与全片常驻“AI动画情景重现 · 非真实影像”。",
        "- 事故只用声波图、黑场、路缘与石墙空镜、事后现场表现；不展示撞击瞬间、遗体、血腥、伤口。",
        "- 终审：杀人罪不成立，危险驾驶致死判4年；全片用检方称/家属认为/法院认为，不下结论。",
        "- 每个钩子有对应解释字幕；常规字幕白色黑边、关键词金色放大，均后期制作。",
    ]
    screenplay = "\n".join(rows) + "\n"
    (HERE / "screenplay.md").write_text(screenplay, encoding="utf-8")
    (HERE / "抖音脚本.md").write_text(screenplay, encoding="utf-8")

    publish = "\n".join([
        f"# {presentation['publish_title']}", "",
        "## 抖音标题", "", presentation["publish_title"], "",
        "## 简短介绍", "",
        "2019年11月济州岛，交往300天的情侣租了一辆野马敞篷。19秒录音里，先是一句“你没系安全带？”，然后是引擎轰鸣。杀人始终没有成立，危险驾驶致死判四年。写实3D动画情景重现，非真实影像。",
        "", "## 提问读者一句话", "", "你觉得，那十九秒里，他想的是什么？", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 系列封面", "",
        "取自本片真实视频帧（夜晚敞篷车或录音声波镜头），裁去字幕，大字“19秒”金色黑边",
        "", "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

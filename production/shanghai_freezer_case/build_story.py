#!/usr/bin/env python3
"""唯一内容源：上海“冰柜藏尸105天”案 30 镜 / 180 秒 / Agnes Video 2.5 Flash reference mode。

旁白文本 = 《案件解说视频_30镜Agent任务指令包_补全版.md》13.1 定稿逐字（偏离仅 S01、S08，均见注释）。
时间码按配音实测可行性微调（见补全版文档 20.2 方案B 授权），总长保持 180.000s。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "上海冰柜藏尸案：她死了105天，丈夫用她的微信聊了105天"
BRANCH = "arena/f9f847e0-desktop-tutorial"

STYLE = (
    "【STYLE】电影级写实3D动画情景重现，明确标注为非真实历史影像；35mm胶片摄影质感，浅景深，"
    "长焦压缩，类似冷峻悬疑犯罪片的克制、冷静、压抑氛围；2016–2019年上海的普通居民小区、室内与城市街道，"
    "准确呈现当年普通家具、立式冰柜、手机与日常物件的材质；真实人体比例、自然皮肤纹理、可信布料与建筑表面，"
    "低饱和、暗部厚重、细腻胶片颗粒；暖黄色彩只属于镜头4回忆段，镜头5（卧室暖转冷）完成冷暖转折，"
    "此后镜头6–30全程冷青/冷灰主导，结尾黑场金句；16:9横屏宽银幕，主体放在三分线附近，画面底部六分之一留作字幕安全区；"
    "所有镜头必须是真实连续运动的3D影像，有自然呼吸、眨眼、手部动作、脚步、飘动、灯光变化或物体转动，"
    "镜头本身平稳移动，绝不以静态图加推拉冒充视频；冰柜与结霜是贯穿全片的视觉母题：只在镜头5/10/18/25/28真实出现，"
    "其余镜头以画面边缘的冷光、门缝光或结霜纹理延续母题，不暗示人物真实存在于冰柜前；"
    "每个镜头末端只做一瞬克制的悬念停顿，环境仍保持细微运动；所有人物均为虚构演员式形象，不还原任何真实人物肖像。"
)
NEGATIVE = (
    "【NEGATIVE】卡通，Q版，动漫，夸张表情，过度饱和，文字，水印，字幕，可读文字，真实姓名，真实肖像，"
    "血腥，伤口，遗体，尸体，冰柜内部内容，绑缚，窒息过程，性相关内容，暴力过程，武器，畸形手指，多余肢体，"
    "人物面部崩坏，低清晰度，画面闪烁，风格突变，竖屏构图，黑边，静态图加推拉，幻灯片，拼版，伪招牌。"
)

# 角色锚点逐字采用本案定稿口径；generate.py 会将其原文拼到对应镜头的提示词中。
CHARACTERS = {
    "LIYINGPING": "【C01锚点】约30岁东亚女性,黑色及肩直发,鹅蛋脸,身形纤细,浅色针织衫,小学教师气质,神情温和,普通长相,自然皮肤纹理",
    "LIYINGPING_SIDE": "【C02锚点】与C01同一名虚构女性,约30岁,黑色及肩直发,浅色针织衫,鹅蛋脸侧面轮廓,神情平静克制",
    "LIYINGPING_BACK": "【C03锚点】同一人背影,黑色及肩直发,浅色针织衫,身形纤细",
    "ZHUXIAODONG": "【C04锚点】约30岁东亚男性,黑色短发,偏瘦,中等脸型,深色夹克配衬衫,商场职员气质,神情斯文冷静疏离,普通长相",
    "ZHUXIAODONG_BACK": "【C05锚点】同一人背影,黑色短发,偏瘦,深色夹克与衬衫",
    "YANGMU": "【C06锚点】58岁左右东亚女性,中年发型,便装上衣,神情牵挂哀伤,普通长相,自然皱纹",
    "YANGFU": "【C07锚点】60岁左右东亚男性,短灰发,发际线后移,便装,神情焦急坚毅",
    "YANGFU_BACK": "【C08锚点】同一人背影,短灰发,便装",
    "EXTRA_BACK": "【C09锚点】25-35岁东亚女性路人背影,普通身形,深色外套,面部完全不可见（与受害者无关的路人）",
    "POLICE_BACK": "【C10锚点】30岁左右男性警察背影,深色制服,面部完全不可见",
}

CHARACTER_SEEDS = {
    "LIYINGPING": 301010,
    "LIYINGPING_SIDE": 301010,
    "LIYINGPING_BACK": 301010,
    "ZHUXIAODONG": 301011,
    "ZHUXIAODONG_BACK": 301011,
    "YANGMU": 580010,
    "YANGFU": 600010,
    "YANGFU_BACK": 600010,
    "EXTRA_BACK": 250010,
    "POLICE_BACK": 300010,
}
# 角色代号 → 已批准参考图资产编号（与 reference/approvals.json 的键一致）。
# generate.py 按它解析每镜的 characters[] → 参考图 URL；参与全部 request_hash，
# 一旦与运行中的批次不一致，渲染会拒绝使用已签收片段。增删前先与主创确认额度。
CHARACTER_REFERENCE_IDS = {
    "LIYINGPING": "C01", "LIYINGPING_SIDE": "C02", "LIYINGPING_BACK": "C03",
    "ZHUXIAODONG": "C04", "ZHUXIAODONG_BACK": "C05",
    "YANGMU": "C06", "YANGFU": "C07", "YANGFU_BACK": "C08",
    "EXTRA_BACK": "C09", "POLICE_BACK": "C10",
}


# duration, narration, visual beat, design references, character roles, camera, sound, color
# 时间码（0/2/7/9/14/24/30/34/38/42/47/56/62/68/74/78/82/87/92/98/103/110/114/119/125/129/137/144/151/160/173/180）
# 旁白 = 13.1 定稿逐字；主动偏离仅 S01（“一百零五天”）与 S08（“妻子在家中遇害。”）。
# 2026-11-19 合规重做：S03/S16/S19/S25/S27/S28 换种子重新抽样；S19/S27 首轮仍出可读字符，二轮改"完全空白纸页/整面失焦白纸"并再换种子（20163036/20163044）
SEED_OVERRIDES = {3: 20162020, 16: 20162033, 19: 20163036, 25: 20163042, 27: 20163044, 28: 20162045}

ROWS = [
    (2, "一百零五天。",
     "纯黑空间，一条冷白光带从画面中心短暂炸开后缓慢收束，空气微尘漂浮，镜头极缓推进；全程纯黑与冷白光，绝不出现任何文字、数字或案件符号。",
     "P01", [], "极缓推进", "一声低沉心跳“咚”，随后静音", "纯黑冷白"),
    (7, "一个女人死了105天，她的丈夫，却用她的微信，陪她妈妈聊了105天。",
     "夜晚普通居民楼里，一只手握住智能手机，屏幕亮起冷蓝微光照亮半张侧脸，手机界面只呈现柔和抽象的绿灰圆角气泡光斑，绝无可读文字；背景霓虹光斑虚化。",
     "S14+C04", ["ZHUXIAODONG"], "冷蓝屏光极缓推近", "极细高频弦乐进，心跳渐强", "冷蓝"),
    (5, "这是2017年震惊上海的冰柜藏尸案。",
     "蓝调时刻的城市天际线航拍缓降：远处江面与楼群剪影，高空镜头缓缓下降穿过密集楼宇，一扇扇窗户向后流去，下方街道空无一人、没有车辆，右下角远处某一扇窗透着暖黄灯光。画面中只允许出现建筑、灯光、江面与天空；绝对禁止出现任何人物、手、面部、身体轮廓、冰柜、箱体、血迹、伤口、任何可读文字或数字；镜头不得推向任何物体特写。",
     "S01", [], "航拍缓降", "低频氛围+远处风声", "蓝调时刻"),
    (10, "朱晓东和杨俪萍，曾是让人羡慕的一对——他做商场职员，她是小学老师，朋友圈里全是旅行和甜蜜合影。",
     "一组温暖的回忆影像：年轻夫妻在街边相视而笑、在旅行地并肩合影、在家中举杯（画面以柔焦与侧影表达，禁止出现可识别真实面孔的清晰正脸特写），暖黄过曝、褪色、颗粒加重；三组影像间缓慢匹配剪辑式切换。",
     "S02+C01+C04", ["LIYINGPING", "ZHUXIAODONG"], "暖色影像匹配剪辑", "轻微快门声，暖调钢琴远去", "暖黄过曝"),
    (6, "可谁都没想到，这段婚姻走到最后，只剩下一台冰柜。",
     "同一间卧室，暖黄灯光骤然熄灭转为青冷月光，空荡荡的双人床缓缓显现，床尾一台卧式冷冻冰柜的门缝透出一线冷光，压缩机轻微震动。",
     "S03+P01", [], "冷暖色彩蒙太奇+缓推", "冰柜压缩机嗡声", "暖→冷"),
    (4, "时间回到2016年10月17日。",
     "纯黑空间，空气微尘缓慢漂浮，中央一束极弱冷青光柱垂直而下，像档案库深处的光；无人、无物、无文字。",
     "P01", [], "微距缓慢推近光柱", "时钟翻页+低频咚", "黑场冷青"),
    (4, "那天晚上，两人发生争执，",
     "夜晚普通居民小区楼栋外景，树枝与栏杆做前景遮挡，框架构图，大部分画面隐没在暗部，只有一扇窗透出暖黄光，窗光下隐约两个模糊人影相对而立（仅剪影，绝不展示肢体冲突）。",
     "S04", [], "固定+极缓推", "低频持续+远处关门声", "冷青"),
    (4, "妻子在家中遇害。",
     "客厅内，两个模糊人影背对镜头（男性与女性剪影），百叶窗光影条纹投在墙面与人影上，侧逆光剪影；人影静止，百叶窗光影缓慢移动；绝无暴力动作与伤害细节。",
     "S05+C03+C05", ["LIYINGPING_BACK", "ZHUXIAODONG_BACK"], "固定+极缓推", "一声闷响后寂静", "冷青剪影"),
    (5, "面对突如其来的尸体，他没报警，也没逃跑——",
     "空无一人的客厅：餐桌上两杯已凉的水，一把椅子斜靠，桌边掉落一只相框（不展示相框内容），窗光穿透浮尘形成丁达尔光柱，微尘缓慢漂浮。",
     "S05", [], "极缓横移", "单音钢琴，一下一下", "冷青丁达尔"),
    (9, "他做了一个正常人无法理解的决定：把妻子藏进冰柜，然后，假装她还活着。",
     "冰柜门缓缓合上，画面渐暗，定格在结霜的金属表面，霜花结晶缓慢蔓延扩大，压缩机微弱震动，冷光从门缝缓慢渗出又熄灭。",
     "P01", [], "微距缓推+暗角加深", "冰柜压缩机嗡声", "冷青"),
    (6, "接下来的105天，是这起案件最让人脊背发凉的部分。",
     "昏暗卧室里，一只手拿起手机，屏幕亮起照亮半张侧脸（背影视角），手机界面只呈柔和抽象绿灰气泡光斑，无可读文字，指腹划过屏幕。",
     "S05+C05+S14", ["ZHUXIAODONG_BACK"], "屏幕冷光缓推", "滴答钟声渐强", "冷青"),
    (6, "朱晓东拿着妻子的手机，冒充她发朋友圈、回微信，",
     "POV主观视角：双手拇指悬停手机屏幕上方，屏幕冷暖交替微光，抽象绿灰气泡逐行浮现又消隐，手指微微颤抖；无可读文字。",
     "S14", [], "手持微晃", "打字声", "冷青微暖"),
    (6, "和她的父母、朋友、同事聊天，语气温柔，滴水不漏。",
     "手机屏幕特写，抽象头像圆点从暖色缓缓切换为冷色，绿色气泡向外浮现如连续发送，屏幕辉光映在周围的黑暗里；无可读文字。",
     "S14", [], "缓慢推近屏幕", "连续消息叮声", "冷青"),
    (4, "母亲问“怎么不接电话”，",
     "约58岁的母亲坐在沙发上紧盯手机，反复点按，眉头紧锁，伦勃朗光侧打出半张脸的三角光斑，另半张隐没在阴影中；手持微晃。",
     "S09+C06", ["YANGMU"], "伦勃朗特写+微晃", "急促弦乐", "冷青"),
    (4, "他回“在忙，别担心”。",
     "手机屏幕微距：一个绿色抽象气泡单独浮现并定格，屏幕冷光微微扩散，背景完全虚化；无可读文字。",
     "S14", [], "微距固定", "发送嗖声", "冷青微绿"),
    (5, "与此同时，他拿妻子的身份证开房、",
     "酒店前台台面特写：一张房卡与一张完全空白素白色的长方形证件平放在冷白色大理石台面上——两张卡必须全素白，无照片、无字符、无数字、无印章、无logo、无任何图形，姓名与照片区域被纯白柔光彻底抹去；顶光硬光在台面投下长阴影；画面里没有任何人物、没有手、没有身体部位；不要任何可读字符或抽象伪字。",
     "S07+P03", [], "顶光固定+缓推", "房卡放下+低频鼓点", "冷白"),
    (5, "和别的女人约会，把日子过得风生水起。",
     "夜晚湿漉漉的都市街道，霓虹红蓝拉丝光晕，两个人并肩的背影保持克制距离行走（一男一女，女性背影为无关路人），斯坦尼康跟拍，地面雨水反光。",
     "S08+C05+C09", ["ZHUXIAODONG_BACK", "EXTRA_BACK"], "斯坦尼康跟拍", "立体声脚步", "青橙霓虹"),
    (6, "妻子就躺在冰柜里，而他在演一场没人看穿的独角戏。",
     "严格对称分屏：左半冰柜结霜门缝（冷青），右半手机抽象气泡光（暖橙），两半画面缓慢拉远制造疏离感；无可读文字。",
     "P01+S14", [], "分屏缓慢拉远", "声音全收，只剩心跳", "左冷右暖"),
    (5, "可再完美的表演，也有穿帮的一天。",
     "微距特写：暖黄台灯下一本横翻的纸质日历放在木质桌面，纸页被一缕空气缓缓掀起（画面中不出现人物与手），纸页必须完全空白——除纸张纤维纹理与阴影外，页面上绝对不得出现任何数字、字符、字母、符号或墨迹；如有日历网格线也必须无任何数字与记号；浅景深；画面中只允许出现日历、桌面与台灯；绝对禁止出现任何人物、手、身体部位、遗体、血迹、伤口、冰柜、结霜、白色絮状绒毛物。",
     "S12", [], "微距+快切递增", "翻页声加快", "暖黄"),
    (7, "杨俪萍的母亲一个多月联系不上女儿，发微信总回得莫名其妙。",
     "同一位母亲，更疲惫的版本（同一人日常连续），夜里独坐沙发反复上划屏幕，窗光从侧面切割（split lighting），半张脸陷入阴影，长焦压缩；手持微晃。",
     "S09+C06", ["YANGMU"], "分割光特写+微晃", "低频压迫音", "冷青"),
    (4, "父亲越想越不对劲：",
     "约60岁父亲的面部特写，眼神从疑惑缓缓转为惊觉，鼻梁以上的皱纹轻轻收紧，背景完全虚化，85mm长焦dolly in缓慢推近。",
     "S10+C07", ["YANGFU"], "85mm缓推", "一声弦乐拨奏", "冷青"),
    (5, "女儿头像换了，说话口气也不像她。",
     "分屏对比：同一块手机屏幕里两个抽象圆形头像并列，左旧右新，中间一枚抽象红色圆圈缓慢呼吸般收缩放大；无可读文字。",
     "S14", [], "分屏固定", "警示叮声", "冷青橙"),
    (6, "2017年2月1日，大年初五，父亲报了警。",
     "暖橙与冷蓝并置：春节街道，红灯笼bokeh绵延，穿便装的父亲背影怀揣手机快步走向远处派出所方向，人群虚化，手持跟拍。",
     "S11+C08", ["YANGFU_BACK"], "手持跟拍", "人群远音+快节奏心跳", "暖橙对比"),
    (4, "当警察跟着朱晓东回家，",
     "楼道入口夜景，警察背影跟随朱晓东背影走进楼道，门框形成框架构图，光线由亮入暗（曝光递减），纵深感强，脚步声立体回响。",
     "S15+C10+C05", ["POLICE_BACK", "ZHUXIAODONG_BACK"], "斯坦尼康跟拍进门", "脚步声+开门声", "亮→暗"),
    (8, "拉开那台冰柜时，在场所有人都愣住了。",
     "一台老式卧式冷冻冰柜的盖子被缓缓抬起，缝隙溢出冷白光，希区柯克变焦（背景空间扭曲），升格慢动作；冰柜内部必须完全空无一物——只有干净结霜的内壁与冷气流动，没有任何物件、人体或织物；镜头推近到最深处时画面切为纯黑并停留约一秒的死寂。绝对禁止出现任何人物、肢体、面部、遗体、血迹、红色液体、伤口、绑带或布料人形；绝对禁止任何数字与文字。",
     "P01", [], "希区柯克变焦+升格", "一切声音全收→沉重低音", "冷光→黑"),
    (7, "真相大白。法庭上，朱晓东一度辩解说是冲动，但铁证如山。",
     "法庭场景：审判席与法槌特写，中心对称构图，低饱和冷灰，顶光庄严；画面不出现可读文字与判决书内容。",
     "S13", [], "中心对称+缓推", "低沉大调回归+法槌落下", "冷灰"),
    (7, "一审被判死刑，二审维持原判，最高人民法院核准。",
     "判决书局部微距侧光：一张完全空白的白纸，整体深度失焦，纸面只能是一片平滑均匀的灰色模糊色带——不得出现任何笔画、行列、字距差异、字符、字母、印章或签名；纸张纤维在侧光下若有若无，像一张抽象质感样本；画面中仅一道抽象的红色荧光矩形高亮块平放在纸面一角（像马克笔笔触，纯色几何矩形，无血溅喷雾、无滴落、无褐色边缘）。绝对禁止出现任何汉字、数字、字母、印章或签名的可辨认形状。",
     "P02", [], "微距侧光", "法槌落槌“咚”", "冷灰"),
    (9, "2019年1月，朱晓东被执行死刑，年仅32岁。那台冰柜，成了最刺眼的注脚。",
     "抽象新闻印象多图快切：一组完全失焦的彩色光斑块与蓝色电视屏幕色块一闪而过（全部虚焦、不可辨认任何内容），一本日历快速翻页定格在某一页，最终画面停在一片纯黑底。画面中只允许出现光斑块、屏幕色块、日历与纯黑底；绝对禁止出现任何人物、身体、面部、遗体、血迹、冰柜内部、任何汉字、数字、字母、水印、乱码或伪文字。",
     "S12", [], "匹配剪辑快切", "低频渐弱收束", "冷灰"),
    (13, "这个案子最恐怖的，不是手段，而是那105天——他能把最亲密的爱人当成“不存在”，一边藏尸，一边笑着说“我很好”。",
     "纯黑空间，极简，一束极微弱的冷光从画面顶端缓缓落下又熄灭，空气微尘缓慢下沉；全程纯黑，画面不出现任何文字（金句由后期逐行叠加）。",
     "P01", [], "固定极慢推", "极简钢琴单音", "纯黑"),
    (7, "如果你是她父母，第几天会发现不对劲？评论区聊聊。",
     "回到手机抽象界面：绿灰气泡光缓慢呼吸，最后定格在一片柔和的冷蓝光里，画面右下角留出评论引导区（引导框由后期叠加）。",
     "S14", [], "缓慢推近+淡出", "消息提示音+淡出", "冷蓝"),
]

CHAPTER_BOUNDS = [
    (0, 9, "黄金钩子"),
    (9, 30, "那天晚上"),
    (30, 47, "只剩一台冰柜"),
    (47, 74, "105天的伪装"),
    (74, 98, "假装她还活着"),
    (98, 125, "破绽"),
    (125, 144, "拉开冰柜"),
    (144, 160, "死刑判决"),
    (160, 180, "金句与余味"),
]

HOOKS = [
    {"id": "H1", "start": 0.0, "end": 2.0, "text": "她死了105天", "style": "big_white_black_outline"},
    {"id": "H2", "start": 9.0, "end": 11.0, "text": "2016年10月17日，她被害", "style": "big_white_black_outline"},
    {"id": "H3", "start": 24.0, "end": 26.0, "text": "暖→冷的那一瞬", "style": "big_white_black_outline"},
    {"id": "H4", "start": 47.0, "end": 49.0, "text": "接下来的105天", "style": "big_white_black_outline"},
    {"id": "H5", "start": 92.0, "end": 94.0, "text": "她在冰柜里，他在演戏", "style": "big_white_black_outline"},
    {"id": "H6", "start": 119.0, "end": 121.0, "text": "大年初五，父亲报警", "style": "big_white_black_outline"},
    {"id": "H7", "start": 129.0, "end": 131.0, "text": "拉开冰柜的瞬间", "style": "big_white_black_outline"},
    {"id": "H8", "start": 144.0, "end": 146.0, "text": "一审死刑，二审维持", "style": "big_white_black_outline"},
    {"id": "H9", "start": 160.0, "end": 162.0, "text": "年仅32岁", "style": "big_white_black_outline", "accent": "red"},
    {"id": "CTA", "start": 173.0, "end": 175.0, "text": "第几天会露馅？评论区聊聊", "style": "big_white_black_outline"},
]

EXPLAINERS = [
    {"start": 2.1, "end": 4.8, "text": "2016年10月17日 · 案发于上海家中", "color": "gold"},
    {"start": 14.1, "end": 17.8, "text": "他：商场职员｜她：小学老师", "color": "gold"},
    {"start": 30.1, "end": 33.8, "text": "2016年10月17日 · 上海", "color": "gold"},
    {"start": 47.1, "end": 50.8, "text": "冒充她的微信 · 陪父母聊了105天", "color": "gold"},
    {"start": 82.1, "end": 84.8, "text": "用她的身份证 · 开房与其他女性交往", "color": "gold"},
    {"start": 103.1, "end": 106.8, "text": "联系不上女儿 · 回复莫名其妙", "color": "gold"},
    {"start": 114.1, "end": 116.8, "text": "头像换了 · 口气也不像她", "color": "gold"},
    {"start": 119.1, "end": 122.8, "text": "2017年2月1日 · 大年初五 · 报警", "color": "gold"},
    {"start": 144.1, "end": 147.8, "text": "一审死刑 · 二审维持 · 最高人民法院核准", "color": "gold"},
    {"start": 151.1, "end": 154.8, "text": "2019年1月 · 执行死刑 · 年仅32岁", "color": "red", "accent": "red"},
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
        # 冰柜母题：真实出现的镜头列入 motif_real，其余禁止把冰柜画成日常道具
        motif_real = {10, 18, 25, 28}
        if index in motif_real:
            motif = "本镜头以真实冰柜/结霜作为叙事核心道具，清晰呈现但不展示任何伤害细节；"
        elif index in {5, 6}:
            motif = "本镜头仅以门缝的一线冷光/纯黑光柱延续冰柜母题，不展示冰柜内部；"
        else:
            motif = "本镜头禁止出现冰柜、结霜或案件道具，只以冷青色调延续母题；"
        prompt = (
            f"{visual} {motif}真实连续运动贯穿全镜，镜头运镜：{camera}；构图保持16:9横屏，"
            "主体置于三分线，底部字幕安全区保持低干扰；不要任何文字、标签、时间戳或招牌。"
        )
        shots.append({
            "id": sid, "kind": "agnes", "start": start, "duration": duration,
            "seconds": duration, "aspect": "16:9", "source_size": "720P",
            "narration_id": chapter, "narration": narration,
            "prompt": prompt, "purpose": visual, "characters": roles,
            "seed": SEED_OVERRIDES.get(
                index, 20261119 if index == 30 else 20161017 + index + (1000 if index in {8, 18, 25, 29} else 0)),
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
        "highlight_phrases": [
            "105天", "年仅32岁", "32岁", "2016年10月17日", "2017年2月1日", "2019年1月",
            "冰柜", "死刑", "大年初五", "最高人民法院", "杨俪萍", "朱晓东", "一百零五天",
        ],
        "hooks": HOOKS,
        "explainers": EXPLAINERS,
        "end_title": "上海冰柜藏尸案",
        "end_subtitle": "2016 – 2019 · 105天的伪装",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "她死了105天",
        "cover_concept": "封面只用本片已生成视频截图：镜头02屏幕冷蓝光半张脸、或镜头06冷青光柱、或镜头10结霜冰柜门；后期大字“她死了105天”+金色黑边，禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "她死了105天，丈夫用她的微信和妈妈聊了105天",
        "hashtags": ["#真实案件", "#案件解说", "#悬疑", "#普法", "#真实事件", "#细思极恐"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
            "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
            "end_title": "只在镜头30由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "aligned_with_upstream_task_doc_section3_and_section10; public court info + CCTV News/The Paper口径；未实时联网复核，发布前须再核",
        "as_of": "2026-11-19; 未发现本案在2019年执行后新的公开程序性进展（执行完毕的案件不再改判）",
        "legal_note": "一审死刑 -> 二审维持原判 -> 最高人民法院核准 -> 2019年1月执行死刑。罪犯已被执行死刑，禁止“服刑中/均已服刑”类表述。全片不渲染血腥，以剪影/切黑处理施害过程；AI动画情景重现，非真实影像。",
        "sources": [
            {"publisher": "上海市第二中级人民法院（一审公开信息）", "date": "2017", "url": "以法院官网公开信息为准（本轮未实时复核）", "supports": "一审死刑判决、案情认定（见 FACT_CHECK.md 第一节）"},
            {"publisher": "上海市高级人民法院（二审公开信息）", "date": "2017-2018", "url": "以法院官网公开信息为准（本轮未实时复核）", "supports": "二审维持死刑"},
            {"publisher": "最高人民法院（死刑核准裁定）", "date": "2018-2019", "url": "以法院公开信息为准（本轮未实时复核）", "supports": "最高法核准、2019年1月执行"},
            {"publisher": "央视新闻 / 澎湃新闻等权威报道", "date": "2017-2019", "url": "以媒体官网为准（本轮未实时复核）", "supports": "案发经过、105天、杨父报警、执行年份与年龄、两人关系与职业"},
        ],
        "editorial_cautions": [
            "媒体口径“105天”与日历口径（约107天）不一致，片中全程采用“105天”（公众认知锚点），不改写。",
            "受害者与被告仅用角色称谓与新闻公认知名的全名（公开报道已公开）；不使用其真实肖像，AI形象仅作示意。",
            "不杜撰动机、作案工具与现场物品位置；画面只以冰柜门缝冷光、空房间、相框、手机气泡暗示。",
            "施害过程不展示：镜08剪影、镜25切黑。",
            "身份证、判决书关键信息一律打码/抽象红框高亮，无可读文字。",
            "“年仅32岁”等年龄/年份表述与公开报道一致；任何超出 FACT_CHECK.md 的细节一律不写入。",
        ],
    }

    project = {
        "title": TITLE,
        "film_name": "上海冰柜藏尸案_105天_三分钟_带声音.mp4",
        "target_duration": 180, "width": 1920, "height": 1080, "fps": 24,
        "model": "agnes-video-2.5-flash", "source_size": "720P", "branch": BRANCH,
        "style_prefix": STYLE, "negative_prompt": NEGATIVE, "style_rumor_prefix": STYLE,
        "characters": CHARACTERS, "character_seeds": CHARACTER_SEEDS,
        "character_reference_ids": CHARACTER_REFERENCE_IDS,
        "narration_spec": {
            "voice_id": voice_id,
            "description": voice.get("description", "悬疑低沉、克制的成熟普通话男声；逐镜独立配音"),
            "language": "zh-CN", "target_characters_per_second": 4.2,
            "alignment": "一镜一句，一镜一条TTS与一条字幕；只在确有必要时加速，不慢放；S01、S08 为主动偏离（TTS审核/口播节奏），字幕与音频逐字一致",
        },
        "chapters": chapters, "shots": shots,
        "reference_images": ref_images,
        "reference_revision": revision,
        "reference_designs": {
            "characters": ["C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10"],
            "scenes": [f"S{i:02d}" for i in range(1, 16)],
            "props": [f"P{i:02d}" for i in range(1, 4)],
            "note": "28张逐张审核的PNG：10张角色参考、15张16:9环境概念、3张道具特写；Agnes调用使用不可变raw链接。",
        },
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期高质量放大到1080P。",
            "所有Agnes提示词由generate.py自动组合：STYLE在最前，角色锚点逐字插入，NEGATIVE在末尾；文字全部禁止AI自绘，由后期烧录。",
            "镜头每5条抽查一次人物脸和服装漂移；出现漂移则以同一批准参考图只重生成对应镜头。",
            "全片无BGM；旁白与字幕逐句锁定，音效/环境声只做轻量辅助，不盖住解说。",
            "冷暖转折在镜头05完成（暖→冷），此后冷青主导；镜头18/25声音全收作为情绪引爆点。",
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
        ts = lambda sec: f"{int(sec) // 60:02d}:{int(sec) % 60:02d}"
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
        if hook["id"] == "CTA":
            explanation = "互动提问，不另加事实解释"
        rows.append(f"| {hook['id']} | {stamp(hook['start'])}–{stamp(hook['end'])} | {hook['text']} | {explanation} |")
    rows += [
        "", "## 事实与安全口径", "",
        "- 人物均为虚构演员式形象；片头与全片常驻“AI动画情景重现 · 非真实影像”。",
        "- 施害过程不展示：镜08剪影、镜25切黑；不展示遗体、血迹、绑缚、窒息过程或性相关细节。",
        "- 身份证、判决书关键信息一律打码/红框（抽象高亮，无可读文字）。",
        "- 105天为媒体口径（自2016-10-17至2017-02-01约107日）；全片统一用“105天”。",
        "- 判决口径：一审死刑 → 二审维持 → 最高人民法院核准 → 2019年1月执行死刑；罪犯已被执行死刑。",
        "- 每个钩子有对应解释字幕；常规字幕白色黑边、关键词金色放大，均后期制作。",
    ]
    screenplay = "\n".join(rows) + "\n"
    (HERE / "screenplay.md").write_text(screenplay, encoding="utf-8")
    (HERE / "抖音脚本.md").write_text(screenplay, encoding="utf-8")

    publish = "\n".join([
        f"# {presentation['publish_title']}", "",
        "## 抖音标题", "", presentation["publish_title"], "",
        "## 简短介绍", "",
        "2016年10月17日，上海。朱晓东杀害妻子杨俪萍（化名秩序与报道一致，本片仅用角色称谓），尸体藏于冰柜，冒充她发朋友圈、回微信、陪她父母聊天105天；2017年2月1日大年初五，杨父报警，警方拉开冰柜。一审死刑，二审维持，最高人民法院核准；2019年1月执行。AI动画情景重现，非真实影像；事实依据见 FACT_CHECK.md。",
        "", "## 提问读者一句话", "", "如果你是她的父母，第几天会发现不对劲？", "",
        "## 话题", "", " ".join(presentation["hashtags"]), "",
        "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

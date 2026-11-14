#!/usr/bin/env python3
"""唯一内容源：光州胶带案 30 镜 / 180 秒 / Agnes Video 2.5 Flash reference mode。"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = "光州胶带案：22米胶带，封住了谁的真相？"
BRANCH = "arena/ebfe4b76-desktop-tutorial"

STYLE = (
    "【STYLE】电影级写实3D动画情景重现，明确标注为非真实历史影像；35mm胶片摄影质感，浅景深，"
    "长焦压缩，类似韩国犯罪惊悚片的克制、冷静、压抑氛围；2004年韩国光州北区龙凤洞老式公寓住宅区，"
    "准确呈现当年普通公寓建筑、衣料、家具与电话材质；真实人体比例、自然皮肤纹理、可信布料与建筑表面，"
    "低饱和、暗部厚重、细腻胶片颗粒；镜头1与3至6为清晨暖黄，镜头7至10傍晚转冷青，镜头11至18冷白与冷灰，"
    "镜头19至22冷蓝，镜头23至25实验室冷白，镜头26至28冷灰，镜头29黄昏暖金，镜头30黑场中仅一点黄色；"
    "16:9横屏宽银幕，主体放在三分线附近，画面底部六分之一留作字幕安全区；所有镜头必须是真实连续运动的3D影像，"
    "有自然呼吸、眨眼、手部动作、脚步、飘动、灯光变化或物体转动，镜头本身平稳移动，绝不以静态图加推拉冒充视频；"
    "黄色箱封胶带是贯穿全片的象征性视觉母题：只有证物镜头中作为真实物品出现，其余镜头仅以画面边缘的虚焦黄色反光或后期抽象细线转场短暂出现，不暗示它当时真实存在于日常场景；"
    "每个镜头末端只做一瞬克制的悬念停顿，环境仍保持细微运动；所有人物均为虚构演员式形象，不还原任何真实人物肖像。"
)
NEGATIVE = (
    "【NEGATIVE】卡通，Q版，动漫，夸张表情，过度饱和，文字，水印，字幕，可读文字，真实姓名，真实肖像，"
    "血腥，伤口，遗体，尸体，绑缚，捆绑，窒息过程，性相关内容，暴力过程，武器，畸形手指，多余肢体，"
    "人物面部崩坏，低清晰度，画面闪烁，风格突变，竖屏构图，黑边，静态图加推拉，幻灯片，拼版，伪招牌。"
)

# 角色锚点逐字采用本期定稿口径；generate.py 会将其原文拼到每个对应镜头的提示词中。
CHARACTERS = {
    "SANA": "【C01锚点】22岁韩国女大学生,黑色马尾,清秀明亮,浅色针织衫牛仔裤,双肩包与便当盒,笑容干净",
    "MOTHER": "【C02锚点】50岁出头韩国女性,烫发,运动外套长裤,网球拍包,神情温和爽朗",
    "MOTHER_NEUTRAL": "【C02N锚点】与C02同一名虚构女性,50岁出头,短卷烫发,深蓝运动外套与白色领口,嘴唇闭合,神情克制警觉,不带微笑",
    "MOTHER_OLD": "【C02B锚点】与C02同一人,六十多岁,头发全白,神情憔悴平静,素色上衣",
    "FATHER": "【C03锚点】50多岁韩国男子,短发,西装领带,公文包,神情沉稳",
    "DETECTIVE": "【C04锚点】40多岁韩国刑警,深色夹克衬衫,眼神锐利疲惫,下巴胡茬",
    "EX": "【C05锚点】23岁韩国男大学生,短发,连帽卫衣牛仔裤,神情紧张坦然",
    "FAMILIAR": "【C06锚点】50多岁韩国男子,深色夹克休闲裤,神情亲切坦然",
    "EXPERT": "【C07锚点】40岁韩国男性专家,戴眼镜,衬衫西裤,神情冷静专注",
    "TEAM_2024": "【C08锚点】30岁韩国年轻刑警便装夹克神情坚定;DNA研究员白大褂口罩神情专注",
    "SHADOW": "【C09锚点】中等身材男性黑影,深色外套,面部隐在阴影中,只见手部轮廓",
}

CHARACTER_SEEDS = {
    "SANA": 220914,
    "MOTHER": 520914,
    "MOTHER_NEUTRAL": 520914,
    "MOTHER_OLD": 520914,
    "FATHER": 500914,
    "DETECTIVE": 400914,
    "EX": 230914,
    "FAMILIAR": 500915,
    "EXPERT": 400924,
    "TEAM_2024": 300924,
    "SHADOW": 900914,
}

# duration, narration, visual beat, design references, character roles, camera, sound, color
ROWS = [
    (5, "二十二米胶带，留下了谁也解不开的疑问？",
     "2004年光州普通公寓玄关，双肩包与便当盒安静地放在地砖边，门缝透出一线暖黄光；一条象征性的黄色细线掠过画面边缘（后期视觉母题，不是现场物品），空气微尘在光束里漂浮，镜头贴地从楼道连续滑近门口，现场无人、无伤害画面。",
     "S01+S02+P04", [], "贴地缓慢滑近门缝", "清晨鸟鸣、远处汽车声、一声轻微低频嗡鸣", "暖黄晨光"),
    (5, "2024年节目公开时，这起案件仍未告破。",
     "黑色空间里，一卷黄色箱封胶带持续缓慢旋转，胶带长条被真实拉出并延伸向远处，末端消失在深暗中；一道人形黑影只在远处掠过一瞬，面部完全不可见。",
     "P01", ["SHADOW"], "缓慢拉远，沿黄色胶带线移动", "胶带被拉出的轻微嘶声，尾音沉入寂静", "黑场与黄色强调"),
    (7, "2004年9月14日，光州北区，父亲七点四十出门。",
     "普通韩国公寓客厅的晨光中，父亲提起公文包走向玄关，母亲仍在厨房准备便当，卧室门半掩，女儿还在睡觉；水壶轻冒热气，窗帘被风吹动，气氛温暖平常。",
     "S02", ["FATHER", "MOTHER"], "中景缓慢横移跟随父亲至门口", "锅铲轻响、晨间电台声、门锁声", "暖黄晨光"),
    (7, "八点五十五分，母亲留下便当，轻轻关门离开。",
     "清晨普通韩国公寓玄关，连续镜头只跟拍唯一一名五十岁左右的母亲（与C02角色锚点一致）的背影和双手：她把素色便当盒放在空餐桌上，背起网球拍包，独自从玄关走出并轻轻关上门。镜头始终朝向玄关与空餐桌，卧室及其他房间不入镜；全程除这位母亲外绝无其他人，不出现年轻女性、女儿、孩子、第二个人、人物剪影、倒影或照片中的人，餐桌椅始终空无一人。",
     "S02", ["MOTHER"], "中景轻推至门锁后缓慢拉远", "门锁声、脚步声渐远", "暖黄晨光"),
    (6, "母亲离开后，善雅起床，准备去学校上课。",
     "善雅从卧室醒来，扎起马尾，穿上外套，拿起双肩包与餐桌上的便当，动作平常自然；镜头从窗边暖光缓慢移向玄关，黄色胶带只以非现场的边缘反光母题一闪而过。",
     "S02+P04", ["SANA"], "镜中近景转为缓慢跟拍", "窗外鸟鸣、衣料摩擦、拉链声", "暖黄晨光"),
    (5, "案发公寓当时没有监控，也没有可确认凶手的痕迹。",
     "老式公寓楼梯间与公共走廊的普通墙角，没有摄像头、没有支架、没有安装痕迹；风从楼道穿过，树影轻轻晃动，镜头连续缓慢横移扫过空荡的墙面。",
     "S03", [], "缓慢横移扫过空墙与楼道", "风穿过楼道、远处关门声", "冷青晨光"),
    (7, "晚上八点左右，母亲结束聚会，朝公寓走回家。",
     "夜色将临，母亲提着网球拍包和购物袋走回同一栋公寓，街灯与楼影拉长；她抬头看向自家窗户，步伐从轻快逐渐放慢，门厅的光色由暖转冷。",
     "S01", ["MOTHER"], "中景缓慢推近", "脚步声、远处孩子玩耍、晚风", "傍晚暖转冷青"),
    (7, "晚上八点左右，母亲回家，玄关却一片凌乱。",
     "单一连续的肩部以上侧面中景：母亲刚推开公寓门，看到画外异样后立即停住；表情清晰地从平静转为惊愕和不安，眼睛微微睁大、眉心收紧、下颌轻绷，嘴唇保持闭合，视线固定在画外。全镜表情严肃克制，绝不微笑、露齿或显得轻松愉悦；镜头缓慢靠近侧脸。背景只有虚焦门框与空白墙面，不展示地面、桌面、房间内部或任何物品特写。全镜没有第二人；绝不出现背包、肩带、便当盒、购物袋、厨具、刀具、剪刀、工具、武器、红色液体、血迹、伤口或暴力痕迹；不出现可读文字。",
     "S02", ["MOTHER_NEUTRAL"], "肩部以上侧面缓慢推近", "门锁轻响、脚步停住、随后一拍寂静", "傍晚冷青"),
    (6, "她沿着走廊走向小房间，脚步忽然停住。",
     "走廊里母亲扶墙缓缓向关闭的小房间门口靠近，画面只见她的背影、门框与一道长长的门缝光；她的肩膀突然僵住，房间内部始终不可见。",
     "S04", ["MOTHER"], "背后跟拍缓慢推近", "轻脚步、压抑呼吸、远处钟声", "冷青"),
    (5, "她想拨112报警，却慌乱中按成119。",
     "小房间门外，母亲剪影捂住嘴，另一只手颤抖着拿起按键座机听筒；她按下按键，听筒传来接线声，她怔住后垂下手，镜头只拍手与电话，不出现可读数字。",
     "S04+P05", ["MOTHER"], "电话与手部大特写", "按键声、接线音、听筒轻碰桌面", "冷青渐暗"),
    (7, "警方赶到公寓，楼道里只有警灯在墙上闪动。",
     "夜色中，几名刑警快步走进老公寓楼道，红蓝警灯在水泥墙面来回扫过，邻居只以模糊背影站在门边，刑警的脚步声在楼梯间连续回响。",
     "S01", ["DETECTIVE"], "低机位跟拍上楼", "远处警笛、楼梯脚步回响", "冷白与警灯反射"),
    (7, "调查人员守在门口，镜头不进入房间。",
     "关闭的小房间门外，一名戴手套的刑警低头查看玄关与门槛，另一名同事递来空白记录板；地面边缘放着一卷黄色箱封胶带，门缝光清晰，房内绝不露出。",
     "S04+P01", ["DETECTIVE"], "中景缓慢推近门槛", "对讲机低声、纸张摩擦、远处脚步", "冷白冷灰"),
    (6, "那卷黄色胶带长约二十二米，围巾也来自家中。",
     "冷白证物台上，一卷黄色胶带和折叠整齐的深色围巾分开摆放；戴手套的技术人员用镊子轻轻提起一小段胶带，反光随手部移动，不展示任何现场伤害。",
     "S09+P01+P03", [], "微距缓慢推近证物台", "镊子轻碰、证物袋沙沙声", "冷白"),
    (5, "四十二段胶带证物，被分别封存保存。",
     "冷白桌面上，透明证物袋被技术人员逐个摆开，每袋内只有一小段黄色胶带；镜头俯拍连续掠过一排排封存袋，最后停在最后一只袋子封口上，画面无标签文字。",
     "P02", [], "俯拍横移，末端短暂停留", "塑料袋封口声逐渐加快，最后一声轻落", "冷白"),
    (6, "警方调阅五百余人的通话记录，重点排查熟人。",
     "2004年警察署办公室，刑警在光州城区地图前翻阅厚厚通话记录，桌上纸张不断传递，墙上只有抽象路线、没有真实姓名或可读内容，人物神情专注而疲惫。",
     "S05", ["DETECTIVE"], "俯拍缓慢推近地图与卷宗", "纸张翻动、电话铃声交错", "冷灰"),
    (6, "前男友案发时在大学社团，证人证明他不在场。",
     "大学社团办公室里，年轻男子安静坐在桌边接受询问，几名社团成员在旁点头作证，墙上挂钟持续走动；镜头保持克制，不将任何人拍成罪犯。",
     "S06", ["EX", "DETECTIVE"], "过肩缓慢推近", "挂钟滴答、低声交谈", "冷白冷灰"),
    (5, "熟悉门锁的另一位重点对象，也有不在场证明。",
     "一位五十多岁男子平静站在公寓数字门锁旁，手指示意自己熟悉日常门锁操作，绿灯亮起后他收回手；神情亲切坦然，画面没有阴森或定罪暗示。",
     "S07+P06", ["FAMILIAR"], "低机位缓慢推近门锁与侧影", "轻微按键声、绿灯提示音", "冷青"),
    (6, "警方查三十名性犯罪前科者、比对五十五名类似胶带前科者，仍无结果。",
     "冷灰档案室里，刑警沿一排排档案柜抽出、翻阅并归还卷宗，空白文件夹接连合上；红色抽象标记只作为后期图形叠加，画面本身不出现可读文字。",
     "S08", [], "横向滑轨穿过档案柜", "卷宗翻动、文件柜滑轨声", "冷灰"),
    (6, "警方曾把调查重点放在熟人，推测凶手知道她独自在家。",
     "冷蓝色画面被分成两种抽象调查方向：一侧是熟人关系线，另一侧是陌生访客路径；两组虚化线条缓缓靠近又分开，中间黄色胶带线轻微摆动，无文字标签。",
     "P01", [], "分屏缓慢推近并轻微错位", "低频电流嗡鸣、缓慢滴答", "冷蓝"),
    (6, "胶带和围巾都是家中物品，专家提出临时取用的可能。",
     "四十岁左右的专家站在白板前，将胶带卷与折叠围巾放在证物盘边比对；他转头向同事解释，白板保持空白，动作冷静克制，不给出确定结论。",
     "P01+P03", ["EXPERT"], "中景缓慢推近", "白板笔轻触、胶带放下的声音", "冷蓝"),
    (5, "陌生人入室后临时取物，也只是专家提出的一种推测。",
     "回到案发公寓的虚构情景重现：一道人形黑影停在玄关，目光扫过鞋柜、书包和客厅，手在桌边短暂停留又收回，脸始终藏在阴影中，不出现任何伤害动作。",
     "S02", ["SHADOW"], "低机位缓慢跟随影子", "极轻脚步声、室内风声", "冷蓝"),
    (5, "“胶带案”的名字，会不会让调查方向变窄？",
     "单一不间断的冷蓝微距镜头，全程无人、无手、无皮肤或人体部位。黑蓝桌面上独立放着一卷黄色箱封胶带，旁边是一张完全空白的证物卡；胶带卷缓慢转动，仅一小段胶带从卷边展开并平铺在桌面上，始终不接触人体。两条柔焦冷蓝线在背景中轻微分开，随后停在空白处，象征调查方向仍未确定。背景与主体始终可见，冷蓝柔光稳定、不闪烁；不切换场景或机位，不淡入全黑、不闪黑；绝不出现胶带缠绕或束缚人体、文字、数字、标签、伤痕或武器。",
     "P01", [], "缓慢推近胶带卷与空白证物卡", "胶带卷轻微转动声、低频悬念音缓缓收束", "冷蓝柔光"),
    (7, "2016年，警方重新检验封存多年的证物。",
     "2024年的证据保管室，年轻刑警打开沉重铁门，研究员在旁照亮最深处的透明证物箱；架上标签全部模糊不可读，箱内只见封存的围巾与胶带片。",
     "S09", ["TEAM_2024"], "长走廊缓慢推近", "铁门开启、脚步回响", "实验室冷白"),
    (7, "胶带与围巾上，检出极微量男性Y染色体信息。",
     "单一不间断的 DNA 实验室近景，只拍一双蓝色手套的手与一台白色小型分析仪：手将无标签样本管放入仪器，黑色屏幕只显示两条极简淡蓝曲线，没有任何其他界面元素。机身、屏幕、手套与衣袖均无标志、字母、数字、铭牌、标签或水印；不出现人物脸、室外、城市、胶带、警戒线或其他道具。镜头平稳缓慢推近，手部与曲线连续轻微运动，画面始终保持在同一实验室桌面。",
     "S10", [], "近景推近仪器屏幕", "设备运行声、一声提示音", "实验室冷白"),
    (6, "2024年公开时，父系分析指向两个姓氏，仍未找到匹配者。",
     "黑暗背景上，一段抽象DNA曲线向两条细细的父系线索分支，终点是两个没有文字的圆形标记；圆点轻轻闪动后停在空白，没有指向任何个人。",
     "P07", [], "俯拍缓慢推近分支终点", "低频脉冲、轻微电子提示音", "实验室冷白"),
    (6, "2015年修法：适用死刑的杀人罪不再受追诉时效限制。",
     "空无一人的韩国立法会议厅，以2015年冷灰色调作克制的象征性情景重现。镜头从干净空桌上的一把木质法槌缓慢移向墙上的简洁模拟时钟，指针缓慢运行后停下，象征修法取消适用死刑杀人罪的追诉时效。画面中绝不出现纸张、法案、书本、表单、印章、屏幕、牌匾、标牌、徽章或任何文字、字母、数字、图案；桌面与背景全程保持空净，法律年份和关键词只由后期字幕呈现。",
     "S11", [], "法槌特写后缓慢移向时钟", "木质法槌轻落、钟表滴答后停止", "冷灰"),
    (6, "新法适用于当时尚未过期的旧案，这起案件仍可追诉。",
     "证据保管室里，透明封存箱被稳稳放回货架，锁扣合上，值班灯在箱面留下一点冷白反光；一名研究员从画面边缘走过，灯光不熄。",
     "S09+P02", [], "缓慢拉远", "锁扣咔哒、远处空调低鸣", "冷灰"),
    (6, "公开报道说，公寓后来才装上监控，证物仍被保存。",
     "黄昏中的同类型公寓外墙，楼道口新装监控摄像头的红色状态灯规律闪烁，镜头贴近镜头玻璃，里面映出空荡楼道与远去的街灯。",
     "S13", [], "缓慢推近摄像头", "设备轻鸣、晚风", "冷灰转黄昏"),
    (6, "母亲曾说，那一天，她仿佛也跟女儿一起死去。",
     "六十多岁的母亲独自坐在客厅沙发上，手里捧着一张完全模糊的家庭照片，茶几上是一杯凉掉的茶；她抬头望向窗外黄昏，神情平静而疲惫，不作哭喊。",
     "S12", ["MOTHER_OLD"], "中景缓慢推近", "晚风、挂钟滴答", "黄昏暖金"),
    (6, "截至2024年节目播出时仍未匹配。你觉得凶手是熟人，还是陌生人？",
     "极简单镜头：纯黑背景中只有一卷无标签的黄色箱封胶带和一条拉出的胶带，胶带卷缓慢匀速旋转，胶带条轻轻摆动，边缘留一点暖金反光；镜头缓慢推近。全程一镜到底，背景始终纯黑，画面只能出现胶带；绝不出现其他场景、人物、手、玻璃、液体、容器、瓶子、桌面、电话、器材或文字，不切镜、不叠化、不闪黑；最后0.6秒仅胶带渐暗入黑场，标题由后期叠加。",
     "P01", [], "缓慢推近", "胶带轻微嘶声，最后一秒完全静音", "黑场与一点黄色"),
]

CHAPTER_BOUNDS = [
    (0, 10, "黄金钩子"),
    (10, 35, "那天早晨"),
    (35, 60, "母亲回家"),
    (60, 85, "22米与42段"),
    (85, 108, "熟人线索"),
    (108, 130, "警方也许想错了"),
    (130, 150, "旧证物的新线索"),
    (150, 168, "追诉时效"),
    (168, 180, "母亲与结尾提问"),
]

HOOKS = [
    {"id": "H1", "start": 0.0, "end": 2.0, "text": "22米胶带，留下未解疑问", "style": "big_white_black_outline"},
    {"id": "H2", "start": 8.0, "end": 10.0, "text": "二十年后，旧证物带来新问题", "style": "big_white_black_outline"},
    {"id": "H3", "start": 30.0, "end": 32.0, "text": "案发公寓，当时没有监控", "style": "big_white_black_outline"},
    {"id": "H4", "start": 55.0, "end": 57.0, "text": "母亲想拨112，却误拨119", "style": "big_white_black_outline"},
    {"id": "H5", "start": 80.0, "end": 82.0, "text": "22米胶带，留下42段证物", "style": "big_white_black_outline"},
    {"id": "H6", "start": 103.0, "end": 105.0, "text": "两名重点熟人，都有不在场证明", "style": "big_white_black_outline"},
    {"id": "H7", "start": 125.0, "end": 127.0, "text": "警方最初的方向，可能错了吗？", "style": "big_white_black_outline"},
    {"id": "H8", "start": 144.0, "end": 146.0, "text": "旧证物检出男性Y染色体信息", "style": "big_white_black_outline"},
    {"id": "H9", "start": 160.0, "end": 162.0, "text": "这起旧案，仍可依法追诉", "style": "big_white_black_outline"},
    {"id": "CTA", "start": 168.0, "end": 170.0, "text": "熟人，还是陌生人？", "style": "big_white_black_outline"},
]

EXPLAINERS = [
    {"start": 2.1, "end": 4.8, "text": "案发于2004年9月14日 · 胶带约22米", "color": "gold"},
    {"start": 10.1, "end": 14.8, "text": "2016年旧证物复检发现线索 · 2024年公开", "color": "gold"},
    {"start": 32.1, "end": 34.8, "text": "无监控 · 无可识别凶手的指纹或足迹", "color": "gold"},
    {"start": 57.1, "end": 59.8, "text": "母亲慌乱中把112误拨成119", "color": "gold"},
    {"start": 82.1, "end": 84.8, "text": "42段胶带证物仍保存", "color": "gold"},
    {"start": 105.1, "end": 107.8, "text": "公开报道中的两名重点对象有不在场证明", "color": "gold"},
    {"start": 127.1, "end": 129.8, "text": "“临时取用”是专家推测，并非定论", "color": "gold"},
    {"start": 146.1, "end": 149.8, "text": "2016年复检检出 · 2024年节目公开 · 当时未匹配", "color": "gold"},
    {"start": 162.1, "end": 167.8, "text": "仅限适用死刑的杀人罪（排除从犯），且旧案当时尚未届满", "color": "gold"},
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
        physical_tape_shots = {2, 13, 14, 19, 20, 22, 23, 27, 30}
        tape_motif = (
            "本镜头不出现黄色胶带、警戒带、黄色线条或其他案件道具；"
            if index == 24 else
            "本镜头允许真实黄色箱封胶带作为证物或明确的抽象象征出现，但绝不接触人体、不展示施害方式；"
            if index in physical_tape_shots else
            "本镜头以画面边缘一闪而过的虚焦黄色反光或后期抽象细线延续胶带母题，不把胶带画成当时真实存在的现场道具；"
        )
        prompt = (
            f"{visual} {tape_motif}真实连续运动贯穿全镜，镜头运镜：{camera}；构图保持16:9横屏，"
            "主体置于三分线，底部字幕安全区保持低干扰；不要任何文字、标签、时间戳或招牌。"
        )
        shots.append({
            "id": sid, "kind": "agnes", "start": start, "duration": duration,
            "seconds": duration, "aspect": "16:9", "source_size": "720P",
            "narration_id": chapter, "narration": narration,
            "prompt": prompt, "purpose": visual, "characters": roles,
            "seed": 20261114 if index == 30 else 20040914 + index,
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
    c02n_revision = approvals.get("assets", {}).get("C02N", {}).get("revision")
    if c02n_revision:
        # Keep S08's two input URLs on the same immutable snapshot without changing the
        # default reference revision (and therefore request hashes) for the other 29 shots.
        next(shot for shot in shots if shot["id"] == "S08")["reference_revision_override"] = c02n_revision
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
            "22米胶带", "22岁", "2004年9月14日", "七点四十", "八点五十五分", "八点二十分", "善雅",
            "112", "119", "没有监控", "42段", "前男友", "重点对象", "不在场证明", "五百余人",
            "三十名", "五十五名", "临时取用", "专家推测", "陌生人", "2016年", "男性Y染色体信息",
            "两个姓氏", "2024年", "2015年", "追诉时效", "母亲还在等", "熟人", "陌生人",
        ],
        "hooks": HOOKS,
        "explainers": EXPLAINERS,
        "end_title": "光州胶带案",
        "end_subtitle": "韩国光州 · 2004 · 2024年公开新线索",
        "title_start": 174.6,
        "title_end": 179.5,
        "cover_text": "22米胶带",
        "cover_concept": "封面只用本片已生成视频截图：玄关的书包与便当盒、画面中央的象征性黄色胶带母题；后期加大字“22米胶带”及金色黑边，禁止用参考图或另造图冒充本期视频帧。",
        "publish_title": "22米胶带与42段证物：光州悬案的旧证物，带来什么新线索？",
        "hashtags": ["#真实事件", "#光州胶带案", "#韩国", "#悬案", "#未解之谜", "#电影感"],
        "caption_policy": {
            "regular": "白字黑边，底部居中安全区，逐镜与旁白逐句同步；关键词金色高亮并放大",
            "hook": "白字黑边，大号字幕，居中偏下，每条停留2秒，不挡主体",
            "explainer": "金色小字，置于字幕安全区上方，只补充可核实事实",
            "end_title": "只在镜头30由后期添加标题文字，AI源片禁止自绘文字",
        },
    }

    fact_check = {
        "status": "cross_checked_against_SBS_broadcast_two_credible_news_reports_and_official_law_search_results",
        "as_of": "2026-11-14; this production pass found no reliable later public case update than the 2024 SBS reports; that is not proof that no later update exists",
        "legal_note": "2004年适用的刑事诉讼法对可判死刑犯罪规定15年公诉时效；2007年延长期限对该日前犯罪仍适用旧规定。2015年《刑事诉讼法》第253条之2取消适用死刑的杀人罪（排除从犯）的公诉时效，并依过渡条款适用于当时尚未届满的旧案。该案于2004-09-14发生，到2015-07-31修法施行时尚不足15年；法律表述只限于相应罪名和未届满案件，不等同所有杀人罪无条件适用。",
        "sources": [
            {"publisher": "SBS (official program page, episode 1409)", "date": "2024-08-24", "url": "https://programs.sbs.co.kr/culture/unansweredquestions/vod/55075/22000541391", "supports": "2004年9月14日、22岁大学生、母亲晚间回家、玄关书包与便当、无CCTV、无可识别凶手的指纹/足迹、42段胶带与案件仍未破"},
            {"publisher": "Kyunghyang Shinmun", "date": "2016-05-10", "url": "https://www.khan.co.kr/article/201605101404001", "supports": "父亲约7:40出门、母亲约8:55离家并于晚间约8点回家、误拨119、两名重点熟人有不在场证明、500余人通话记录、30名性犯罪前科者及55名相似胶带手法前科者调查"},
            {"publisher": "Hankyoreh", "date": "2018-06-28", "url": "https://www.hani.co.kr/arti/specialsection/esc_section/850935.html", "supports": "无可识别的指纹/足迹、家中胶带与围巾、无CCTV、案发后安装CCTV、调查与目击信息"},
            {"publisher": "SBS News / SBS Entertainment News", "date": "2024-08-25", "url": "https://news.sbs.co.kr/news/endPage.do?news_id=N1007774346", "supports": "2016年旧证物复检发现微量男性Y染色体信息；节目报道父系分析指向两个姓氏范围，播出时没有找到匹配者"},
            {"publisher": "National Law Information Center (official 2015 amendment)", "date": "2015-07-31", "url": "https://www.law.go.kr/LSW/lsRvsDocListP.do?lsId=001671&chrClsCd=010102", "supports": "《刑事诉讼法》第253条之2：适用死刑的杀人罪（排除从犯）不适用公诉时效；过渡条款将其适用于施行前尚未届满的案件。网站于本轮访问时显示维护页，条文由官方搜索结果核对"},
            {"publisher": "National Law Information Center (official law effective 2004-07-22)", "date": "2004-07-22", "url": "https://www.law.go.kr/LSW/lsLinkProc.do?lsNm=%ED%98%95%EC%82%AC%EC%86%8C%EC%86%A1%EB%B2%95&efYd=20040722&lsId=prec20040722&lsClsCd=L&joNo=024900&mode=11&lnkJoNo=undefined", "supports": "第249条：可判死刑犯罪的公诉时效为15年"},
            {"publisher": "Supreme Court of Korea (2007 amendment transitional rule, official case bulletin)", "date": "2022-08-19", "url": "https://www.scourt.go.kr/portal/news/NewsViewAction.work?pageIndex=1&searchWord=&searchOption=&seqnum=8725&gubun=4&type=0", "supports": "2007年延长公诉时效的修法对修法前犯罪适用旧规定；本案2015年修法前仍未满当时15年期限"},
        ],
        "editorial_cautions": [
            "受害者只称善雅（化名）；所有嫌疑人和相关者只用角色称谓，不出现真实姓名或可识别肖像。",
            "两名公开报道中的重点对象均有不在场证明；这不等于公开资料证明警方逐一排除了所有熟人。",
            "男性Y染色体痕迹于2016年旧证物复检时发现，2024年节目公开报道；父系姓氏范围只是线索，不是身份确认；“播出时未匹配”不能写成2026年实时结论。",
            "追诉时效口径严格限定为适用死刑的杀人罪、排除从犯及修法时尚未届满的旧案；不声称所有杀人罪无条件适用。",
            "母亲回家时间在不同报道中约为晚上8点至8点20分，旁白只说“晚上八点左右”。",
            "不展示遗体、血迹、绑缚、窒息过程或性相关细节；以玄关物件、胶带、证物袋、门缝光和空房间暗示。",
        ],
    }

    project = {
        "title": TITLE,
        "film_name": "光州胶带案_22米胶带_三分钟_带声音.mp4",
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
            "characters": ["C01", "C02", "C02N", "C02B", "C03", "C04", "C05", "C06", "C07", "C08", "C09"],
            "scenes": [f"S{i:02d}" for i in range(1, 14)],
            "props": [f"P{i:02d}" for i in range(1, 8)],
            "note": "31张逐张审核的PNG：11张角色参考、13张16:9环境概念、7张道具特写；Agnes调用使用不可变raw链接。",
        },
        "presentation": presentation,
        "sfx_only": True,
        "fact_check": fact_check,
        "production_rules": [
            "全片1920x1080、16:9、24fps、180秒，30段连续运动视频；源片720P，后期高质量放大到1080P。",
            "所有Agnes提示词由generate.py自动组合：STYLE在最前，角色锚点逐字插入，NEGATIVE在末尾；仅镜头30允许后期标题，不让模型画字。",
            "镜头每5条抽查一次人物脸和服装漂移；出现漂移则以同一批准参考图只重生成对应镜头。",
            "全片无BGM；旁白与字幕逐句锁定，音效/环境声只做轻量辅助，不盖住解说。",
            "转场按脚本章节使用晨光闪烁、切黑、警灯反射、黄色胶带拉伸和0.3秒黑场淡入。",
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
        "钩子字幕：白字黑边、大字、居中偏下、每条严格 2 秒；关键词金色高亮。解释字幕：金色小字，置于底部常规字幕上方，不遮挡主体。",
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
        "- 受害者只称善雅（化名）；人物均为虚构演员式形象。片头与全片常驻“AI动画情景重现 · 非真实影像”。",
        "- 案发画面只用书包、便当盒、胶带卷、证物袋、门缝光暗示；不展示遗体、血迹、绑缚、窒息过程或性相关细节。",
        "- DNA线索在2016年前后复检发现，2024年公开报道；两个姓氏只属推断，尚无匹配者。",
        "- 2015年追诉时效改革有法定适用范围，脚本仅说符合条件且当时未届满的案件可继续追诉。",
        "- 每个钩子有对应解释字幕；常规字幕白色黑边、关键词金色放大，均后期制作。",
    ]
    screenplay = "\n".join(rows) + "\n"
    (HERE / "screenplay.md").write_text(screenplay, encoding="utf-8")
    (HERE / "抖音脚本.md").write_text(screenplay, encoding="utf-8")

    publish = "\n".join([
        f"# {presentation['publish_title']}", "",
        "## 发布简介", "",
        "2004年9月14日，光州北区龙凤洞。玄关的书包和便当盒，门口没有监控，42段黄色胶带被封存在证物室。",
        "二十年后，旧证物里出现男性Y染色体线索，但父系范围仍未找到匹配者。熟人，还是陌生人？",
        "本片为写实3D动画情景重现，非真实影像；受害者称善雅（化名），不呈现遗体或施害过程。",
        "", "## 互动问题", "", "你认为，警方最初把重点放在熟人身上，是否可能漏掉了陌生访客？欢迎理性讨论。", "",
        " ".join(presentation["hashtags"]), "",
        f"封面标题候选（尚未生成）：{presentation['cover_text']}",
        "", "## 片尾", f"{presentation['end_title']}｜{presentation['end_subtitle']}",
    ]) + "\n"
    (HERE / "抖音发布文案.md").write_text(publish, encoding="utf-8")
    print(f"WROTE {len(shots)} shots / {cursor}s / {len(chapters)} chapters / narration chars={sum(len(s['narration']) for s in shots)}")
    return project


if __name__ == "__main__":
    build()

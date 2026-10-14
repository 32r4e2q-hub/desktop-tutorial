#!/usr/bin/env python3
"""《新亭洞连环杀人案：凶手找到了，却已死去十年》唯一内容源。

与以往 38 镜动画 + 信息卡不同：本片完全按用户上传的参考片做——
写实真人年代剧情景重现、连续剧情镜头、旁白贯穿、中英双语字幕、
片头大标题压在实景上；30 镜 × 6 秒 = 180 秒，0 张信息卡，
只在最后一句旁白后留 6 秒空镜收尾（不做片尾卡）。

生成通道：智谱 CogVideoX-Flash（仓库 secrets.ZHIPUAI_API_KEY），不用 Agnes。
智谱提示词上限 512 字，所以每镜提示词都短：STYLE（全片统一）+ 单镜一句。

用法：
    python3 production/sinjeong2005/build_story.py            # 写 story.json + manifest 文案
    python3 production/sinjeong2005/build_story.py --script   # 生成 抖音脚本.md
    python3 production/sinjeong2005/build_story.py --publish  # 生成 抖音发布文案.md
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "新亭洞连环杀人案：凶手找到了，却已死去十年"
MODEL = "cogvideox-flash"

# 全片统一风格（智谱每镜最终提示词 = STYLE + 单镜描述，必须 ≤512 字）
STYLE = (
    "2005年前后韩国首尔新亭洞老住宅区，写实真人剧情片情景重现，电影质感，"
    "阴冷潮湿，低饱和灰蓝色调，真实演员表演，人物丰富、面部清晰、表情生动鲜活，"
    "单一场景连续镜头缓缓移动，画面干净，无任何文字、字幕、水印和标志，氛围克制含蓄。"
)

NEGATIVE_PROMPT = (
    "readable text, subtitles, watermark, logo, corpse, blood, gore, violence, "
    "assault, nudity, frontal face of killer or victim, deformed hands, extra fingers, "
    "morphing, jump cut, split screen, cartoon, animation, 3D render look"
)

PRINCIPLES = [
    "全部镜头为智谱 CogVideoX-Flash 生成的 AI 真人情景重现，画面常驻标注「AI真人情景重现 · 非新闻影像」，不冒充监控、庭审或证物照片",
    "风格跟随用户上传的参考片：真人年代剧表演、连续剧情场景、旁白贯穿、中英双语字幕、片头大标题压实景；不使用信息卡与片尾卡",
    "不展示遗体、血腥或侵害过程；不重演作案经过",
    "露脸模式（按用户要求，模仿参考片）：人物丰富、人人有脸、表情生动；每个人物一张不同的脸，同一人物跨镜头同一张脸——靠 cast.json 的面容描述逐字节复用 + face_cast.py 两道闸门（提示词静态检查、出片后逐镜裁脸比对）守着，换脸/撞脸的镜头只重做那一镜",
    "全部角色为虚构匿名演员，不还原任何真实人物容貌：管理员角色不是真实嫌疑人的长相，受害者只以生前日常形象出现、不冒充本人",
    "侦探、居民、科研人员等虚构表演者可以露脸，但不冒充任何真实人物本人",
    "结局按 2025 年 11 月 21 日首尔警方公布的真实进展写：DNA 特定当年大楼管理员为凶手，其人已于 2015 年去世；不沿用上传文案里「至今未破」的旧说法",
    "2006 年「流氓兔」逃脱事件与本案凶手无关（警方已澄清），片中按假线索处理，不写成同一凶手",
    "每一句事实都能指到 sources；中文姓名、日期、字幕一律后期添加，不交给视频模型拼写",
]

SOURCES = [
    {"id": 1, "url": "https://www.hankookilbo.com/News/Read/A2025112018310000336",
     "usage": "支撑：2025-11-21 首尔警方 DNA 特定大楼管理员 A 某；2013 列为悬案、2016 悬案组重启、2016/2020 两次再鉴定确认同一人；筛查约 23 万人、采集 1514 人 DNA；扩大到已故者 56 人；跑遍京畿南部 40 家医疗机构找到留存检体后比对一致；凶手 2015 年去世火化，案件将以无公诉权结案；2006 年 5 月流氓兔事件时 A 某已因另案入狱、非同一人"},
    {"id": 2, "url": "https://koreajoongangdaily.joins.com/news/2025-12-08/national/socialAffairs/A-bizarre-rabbit-sows-chaos-in-Sinjeongdong-serial-killing-investigation/2462842",
     "usage": "支撑：2005-06-07 清晨环卫工在巷口发现米袋与露出的人手；第二名受害者 2005-11-20 被发现、裹在席垫里以绳索捆绑、前一晚出现在新亭站监控；38 人专案组；第二名受害者衣物上的霉菌指向地下空间；流氓兔贴纸来自 2006 年 5 月逃脱女子的证词"},
    {"id": 3, "url": "https://www.khan.co.kr/en/article/202511211953337",
     "usage": "支撑：两名受害者均为勒颈窒息、头部套黑色塑料袋、分别裹米袋与席垫并以绳索捆绑；初期未检出可锁定身份的 DNA；2020 年从受害者衣物与绳索检出同一男性 DNA；凶手为受害者到访大楼的管理员、2006 年 2 月在同一大楼地下室另案被捕并服刑至 2009 年；警方名言「追到阴间也要查」"},
    {"id": 4, "url": "https://world.kbs.co.kr/service/news_view.htm?lang=e&Seq_Code=197599",
     "usage": "支撑：2025-11-21 首尔警方简报确认凶手为案发时 60 多岁的大楼管理员、已于 2015 年去世；走访 40 家医疗机构取得 DNA 样本；以无公诉权结案"},
]

# 六段解说（分句都短，方便双语字幕逐句对齐；合计约 790 字）
CHAPTERS = [
    ("N01", "钩子：找了二十年的人，就守在那栋楼里",
     "首尔最普通的一个住宅区，藏着一个找了二十年的凶手。他就守在受害者走进的那栋楼里，每天看着人群从眼前走过。二零二五年，警方终于叫出了他的身份。可那时，他已经死了整整十年。这就是新亭洞连环杀人案。"),
    ("N02", "第一起案件：巷口的米袋（2005 年 6 月）",
     "二零零五年六月七日清晨，新亭洞住宅区的巷口，环卫工看见两只米袋绑在一起，袋口露出一只苍白的手。袋子里，是第一名受害者，一名二十多岁的女子。没有目击者，也没有拍下凶手的监控。第一起命案，就这样摆在首尔警方眼前。"),
    ("N03", "第二起案件：同一个人第二次出手（2005 年 11 月）",
     "五个月后，十一月二十日，同一个社区又出现一个包裹，席垫裹着死者，绳索捆得死紧。死者是四十多岁的女子，前一晚还出现在新亭站的监控里，再也没有回家。两名受害者素不相识，死因相同，捆绑的手法也相同。警方终于意识到，这不是两起命案，是一个人第二次伸出了手。"),
    ("N04", "八年无果与流氓兔假线索（2006–2013）",
     "三十八人的专案组，一查就是八年。可现场没留下能认出他的基因，模糊的画面也拼不出一张脸。二零零六年，另一名女子被挟持后逃生，只记得藏身处有一张流氓兔贴纸。所有人都以为，她逃出的是同一双手。直到多年以后警方才确认，那是另一个人留下的假线索。二零一三年，案件被列为悬案。"),
    ("N05", "转机：旧证物里的 DNA（2016–2020）",
     "转机，来自二十年前的旧证物。二零一六年，悬案专案组重新接手。二零二零年，新的鉴定技术，从第一名受害者的衣物上，从第二起案件的绳索上，检出了同一个男人的基因。警方筛查二十三万多人，采集一千五百一十四人的样本，甚至远赴海外协查比对，活人里依然没有一个对得上。于是，他们把名单转向了死者。"),
    ("N06", "真凶：找到了，却等不到开庭（2025）",
     "五十六名已故候选人中，浮出当年那栋楼的管理员A某。两名受害者都曾走进他看守的楼，二零零六年他又因另一起侵害被捕，却没人把他和两起命案连在一起。他已在二零一五年病逝火化，警方跑遍四十家医疗机构，才找到一份留存至今的检体。二零二五年十一月二十一日，基因比对的结果只有一个，对上了。凶手找到了，却等不到开庭那一天。警方说，杀人犯，要追到阴间为止。这句迟到二十年的回答，留给家属的，只有真相，没有审判。"),
]

# 每章英文分句（与中文分句一一对应，逐句校验数量）
CAPTIONS_EN = {
    "N01": ["In an ordinary Seoul neighborhood", "hid a killer sought for twenty years",
            "He worked in the very building his victims entered", "watching crowds pass every day",
            "In 2025", "police finally named him", "But by then", "he had been dead for ten years",
            "This is the Sinjeong-dong serial murder case."],
    "N02": ["On the morning of June 7, 2005", "in an alley in Sinjeong-dong",
            "a street sweeper saw two rice sacks tied together", "a pale hand showing at the opening",
            "Inside", "was the first victim", "a woman in her twenties",
            "There were no witnesses",
            "and no camera had caught the killer", "The first murder",
            "was now before the Seoul police."],
    "N03": ["Five months later", "on November 20", "another bundle appeared in the same neighborhood",
            "the body wrapped in a mat", "bound tightly with rope",
            "The victim was a woman in her forties", "last seen on station cameras the night before",
            "who never made it home", "The two victims had never met", "yet the cause of death was the same",
            "and so was the binding", "Police finally realized", "this was not two separate cases",
            "the same man had struck a second time."],
    "N04": ["A 38-officer task force", "investigated for eight years",
            "But the scene left no DNA that could name him", "and grainy footage drew no face",
            "In 2006", "another woman escaped an abduction",
            "remembering only a cartoon-rabbit sticker where she hid", "Everyone believed",
            "she had escaped the same hands", "Only years later did police confirm",
            "it was a false lead left by a different man", "In 2013", "the case went cold."],
    "N05": ["The break", "came from twenty-year-old evidence", "In 2016",
            "a cold-case team took over the file", "In 2020", "new forensic technology",
            "from the first victim's clothing", "and from the rope in the second case",
            "recovered one man's DNA", "Police screened more than 230,000 people",
            "collected samples from 1,514 of them", "and even compared databases overseas",
            "yet no living person matched", "So", "they turned their list to the dead."],
    "N06": ["Among 56 deceased candidates", "emerged the building caretaker, Mr. A",
            "Both victims had entered the building he kept",
            "and in 2006 he was arrested for another assault",
            "yet no one linked him to the two murders", "He had died in 2015 and been cremated",
            "so police searched forty medical facilities", "until one stored sample was found",
            "On November 21, 2025", "the DNA result gave one answer", "a match",
            "The killer was found", "but he will never stand trial", "Police said",
            "a murderer", "must be tracked even into the afterlife",
            "This answer, twenty years late", "left the families", "only the truth", "and no trial."],
}

# 30 镜 × 6 秒：(id, 运镜, 叙事职责, 衔接, 单镜提示词, 音效备注)
# 提示词只写本镜场景（全片风格在 STYLE 里统一加），凶手/受害者不露脸。
SHOTS = [
    # ---- N01 钩子（5 镜）----
    ("S01", "缓慢前推", "钩子：最普通的小区白天日常（居民群像，人脸各异）", "硬切夜巷",
     "清晨的首尔老住宅区小巷，买菜的老人、上班的夫妻、背书包的孩子走过，每张脸各不相同、表情自然，镜头缓缓前推", "市声底噪"),
    ("S02", "缓慢横移", "钩子：同一条巷子的夜晚（空镜）", "切管理员室",
     "深夜同一条住宅区小巷，路灯昏黄，空无一人，只有野猫穿过，镜头缓慢横移", "夜风"),
    ("S03", "固定缓推", "钩子：守楼人望着人群（C7 管理员露脸）", "切现代冷案室",
     "老式大楼管理员室，{C7}坐在窗边桌前，望着窗外来往人群，镜头缓缓推近他的脸", "挂钟声"),
    ("S04", "缓慢横移", "钩子：2025 年卷宗被重新打开（C8 冷案组长露脸）", "切夜巷收束",
     "现代办公楼的旧资料保管室，{C8}从铁柜深处抽出一盒落灰的旧档案，神情一凝，镜头缓慢横移", "纸张声"),
    ("S05", "缓慢拉远", "钩子收束：灯火渐熄的住宅区（片头标题压此镜）", "切 2005 大楼大堂",
     "夜色中的住宅区全景，窗灯一盏盏熄灭，只剩巷口一盏路灯，镜头缓慢拉远", "低音持续"),
    # ---- N02 第一案（8 镜）----
    ("S06", "缓慢横移", "第一案前：年轻女子走进大楼（C4 与 C7 同框）", "切清晨巷口",
     "2005年一栋老大楼的大堂，{C4}抱着手提包走进来，柜台后的{C7}抬头看了她一眼，镜头缓慢横移", "大堂环境声"),
    ("S07", "缓慢前推", "第一案：环卫工清晨巡巷（C3 露脸）", "切发现特写",
     "清晨住宅区巷口，{C3}推着清洁车缓缓走过垃圾站，镜头缓缓前推", "清晨市声"),
    ("S08", "固定缓推", "第一案：环卫工停住（C3 露脸特写）", "切警戒线",
     "{C3}忽然停住脚步望向墙边，脸色慢慢发白，手扶住清洁车，镜头缓缓推近她的脸，不拍墙边近景", "清晨市声"),
    ("S09", "缓慢横移", "第一案：专案组长到场（C1 露脸）", "切证物封存",
     "黄色隔离带外的老巷子，{C1}带着同事快步走来，环视四周后低声交代，镜头缓慢横移", "人群低语"),
    ("S10", "缓慢前推", "第一案：证物克制封存（警员群像远景）", "切会议室",
     "巷子远景，数名戴手套的警员把封好的证物箱搬上面包车，每张脸神情严肃、彼此不同，动作克制，镜头缓缓前推", "车门声"),
    ("S11", "缓慢前推", "第一案：会议室里拼不出凶手（C1+C2 露脸）", "切监控室",
     "老式警局会议室，{C1}指着摊开的地图说话，旁边的{C2}皱眉摇头，镜头缓缓前推，纸面内容模糊不可读", "纸张声"),
    ("S12", "固定缓推", "第一案：监控什么都没拍到（C2 露脸）", "切组长望楼",
     "昏暗的影像室里，{C2}盯着满是雪花的老式电视屏幕，屏幕微光映在他脸上，他揉了揉眉心，镜头缓缓推近", "电流底噪"),
    ("S13", "缓慢拉远", "第一案收束：组长望着居民楼（C1 露脸）", "切第二案车站夜景",
     "隔离带撤去后的巷子，{C1}独自站在巷口望着居民楼，久久没有离开，镜头缓慢拉远", "低音"),
    # ---- N03 第二案（6 镜）----
    ("S14", "缓慢横移", "第二案前：中年女子夜里出站（C5 露脸）", "切清晨巷口发现",
     "2005年的首尔地铁站出口夜景，{C5}随人流走出车站，拢了拢外套往小巷走去，镜头缓慢横移", "车站人声"),
    ("S15", "缓慢前推", "第二案：店主清晨发现异常（C6 露脸）", "切第二现场封锁",
     "清晨住宅区停车场边，{C6}望见墙边的大包裹，停步后退，掏出老式手机报警，镜头缓缓前推，不拍包裹近景", "清晨市声"),
    ("S16", "缓慢横移", "第二案：同一社区再次封锁（C1 露脸）", "切居民窗",
     "第二次拉起黄色隔离带的住宅区巷子，{C1}站在隔离带内望着居民楼，神情比五个月前更沉，镜头缓慢横移", "人群低语"),
    ("S17", "固定缓推", "第二案：居民楼窗后的眼睛（群像）", "切证物台绳结",
     "居民楼一排窗户后，居民们隔着玻璃往下张望，每张脸都带着不安、彼此各不相同，镜头缓缓推近", "低语声"),
    ("S18", "固定缓推", "第二案：绳结成为共同签名（手部特写，无脸空镜）", "切双案对照",
     "证物室台面上，戴手套的手缓缓转动一截打着繁复绳结的旧绳索，旁边放着席垫边角，镜头缓缓推近", "手套摩擦声"),
    ("S19", "缓慢前推", "第二案：两案并作一案（C1+C2 露脸）", "切专案组全景",
     "办公室里，墙上两张模糊的旧照片之间被拉起一根红线，{C1}与身旁的{C2}对视一眼，都意识到了什么，镜头缓缓前推", "低音"),
    # ---- N04 僵局（6 镜）----
    ("S20", "固定缓推", "僵局：专案组的长夜（C1+C2 露脸）", "切监控室",
     "深夜的办公室，台灯下旧文件堆积如山，{C1}揉着眼睛继续翻页，对面的{C2}趴在桌上睡着了，镜头缓缓推近", "翻页声"),
    ("S21", "缓慢前推", "僵局：模糊监控拼不出脸（C2 露脸）", "切楼梯间逃脱",
     "老式放映机旁，{C2}按下播放键，盯着雪花屏上模糊的身影，越看眉头越紧，镜头缓缓推近", "磁带杂音"),
    ("S22", "缓慢横移", "流氓兔：逃脱者躲进楼梯间（C10 露脸）", "切巷口走访",
     "老式住宅楼楼梯间，{C10}仓皇跑上楼，躲到鞋柜后面屏住呼吸，鞋柜旁贴着一张白色卡通贴纸，镜头缓慢横移", "急促呼吸"),
    ("S23", "缓慢横移", "流氓兔：走访居民（C2 露脸）", "切居民议论",
     "住宅区巷口，{C2}拿着笔记本挨个询问居民，居民们纷纷摇头，他在本子上划掉一行，镜头缓慢横移，纸面不可读", "人群低语"),
    ("S24", "缓慢前推", "流氓兔：众口一词的方向（居民群像+C2）", "切档案封存",
     "巷口围着一圈居民七嘴八舌地比划，{C2}站在中间认真记录，每张脸表情各异，镜头缓缓前推", "人群声"),
    ("S25", "缓慢前推", "僵局收束：卷宗封存进铁柜（C1 露脸，2013）", "切 2016 重启",
     "昏暗的资料室，{C1}把贴好封条的旧文件盒推入铁柜深处，手在柜门上停了几秒，才缓缓合上，镜头缓缓前推", "铁柜声"),
    # ---- N05 转机（7 镜）----
    ("S26", "缓慢横移", "转机：2016 年卷宗重见天日（C8 露脸）", "切冷案会议",
     "白天的办公室，{C8}重新打开落灰的旧文件盒，阳光从百叶窗照在文件上，她抬头看向窗外，镜头缓慢横移", "纸张声"),
    ("S27", "缓慢前推", "转机：冷案组围着旧证物开会（C8 露脸+团队群像）", "切实验室取样",
     "会议室里，{C8}站在桌前讲述，围坐的同事们神情专注、每张脸各不相同，桌上放着封好的文件袋，镜头缓缓前推，纸面不可读", "低声讨论"),
    ("S28", "固定缓推", "转机：旧衣物重新取样（C9 露脸）", "切测序仪",
     "法医实验室，{C9}戴着手套，用镊子从旧衣物上夹取纤维样本放进试管，动作极轻，镜头缓缓推近", "仪器轻响"),
    ("S29", "缓慢横移", "转机：仪器里的答案（C9 露脸）", "切全国走访",
     "实验室里离心机与测序仪运转，试管在蓝光下旋转，{C9}在旁盯着仪器记录，镜头缓慢横移，屏幕无文字数字", "仪器嗡鸣"),
    ("S30", "缓慢前推", "转机：二十三万人里找一个人（C8 露脸）", "切第二家医院",
     "医院走廊，{C8}向护士站说明来意询问，抱着一摞文件继续走向下一间诊室，镜头缓缓前推，纸面不可读", "脚步声"),
    ("S31", "缓慢横移", "转机：一家家问过去（C8 露脸）", "切深夜名单",
     "另一家医院的资料窗口前，{C8}递上文件与工作人员交谈，对方摇头，她道谢后转身赶往下一处，镜头缓慢横移，纸面不可读", "脚步声"),
    ("S32", "固定缓推", "转机：活人名单划到尽头（C8 露脸）", "切地下室走廊",
     "深夜办公室，{C8}在一页页名单上逐行划过，划到最后一行停住笔，抬头望向窗外，镜头缓缓推近，纸面不可读", "笔尖声"),
    # ---- N06 真凶（8 镜）----
    ("S33", "缓慢前推", "真凶：那栋楼的地下室（C7 露脸）", "切大堂柜台",
     "老大楼地下储藏室走廊，{C7}提着工具箱缓缓走过，昏黄灯光打在他脸上，镜头缓缓前推", "脚步回声"),
    ("S34", "固定缓推", "真凶：受害者都走进过这栋楼（C7 露脸）", "切 2006 走廊",
     "老大楼大堂柜台后，{C7}低头擦着柜台，余光扫过走进大门的住户，镜头缓缓推近他的侧脸", "大堂环境声"),
    ("S35", "缓慢横移", "真凶：2006 年他曾被带走（C7 露脸）", "切冷案回望",
     "老式警局走廊，两名警员带着{C7}走过，他低着头，脸半隐在阴影里，镜头缓慢横移", "脚步声"),
    ("S36", "缓慢前推", "真凶：没人把两件事连起来（C8 露脸）", "切医院档案室",
     "办公室里，{C8}把一份旧记录放在两张旧照片旁边，盯着看了很久，忽然坐直了身子，镜头缓缓前推，纸面不可读", "纸张声"),
    ("S37", "缓慢前推", "真凶：跑遍四十家医疗机构（C8 露脸）", "切实验室交接",
     "医院资料保管室，{C8}戴着手套从抽屉中取出一小管封存的样本，在场的人都屏住呼吸，镜头缓缓推近", "抽屉声"),
    ("S38", "缓慢横移", "真凶：检体送进实验室（C9 露脸）", "切比对结果",
     "法医实验室门口，{C9}双手接过密封的检体样本管，郑重地点头，转身走进实验室，镜头缓慢横移", "脚步声"),
    ("S39", "固定缓推", "真凶：DNA 对上了（C8+C9 露脸）", "切清晨巷子收尾",
     "实验室屏幕上两条曲线缓缓重合，画面无文字数字，{C8}眼眶泛红长出一口气，身旁的{C9}轻轻点头，镜头缓缓推近", "仪器提示音"),
    ("S40", "缓慢拉远", "收尾：巷子恢复日常，问题留给观众（C8 露脸）", "淡出",
     "清晨阳光照进新亭洞小巷，居民买菜遛狗如常生活，{C8}望着那栋大楼片刻，转身走出巷子，镜头缓缓拉远", "清晨市声"),
]

TITLE_CARD = ["新亭洞连环杀人案", "凶手找到了 · 却已死去十年"]
CAPTION_KEYWORDS = ["二十年", "新亭洞连环杀人案", "流氓兔", "悬案", "基因", "二十三万多人",
                    "一千五百一十四人", "死者", "管理员A某", "对上了", "没有审判"]
SFX_EVENTS = [("S04", "paper"), ("S09", "paper"), ("S14", "keys"), ("S16", "paper"),
              ("S20", "keys"), ("S28", "paper")]

TITLES = [
    "新亭洞连环杀人案：凶手找到了，却已死去十年｜韩国悬案的迟到答案",
    "首尔新亭洞连环杀人案：找了二十年的人，就守在那栋楼里",
    "他死了十年后，DNA 才叫出他的名字：新亭洞连环杀人案全记录",
]
HOOK = "凶手就守在受害者走进的那栋楼里，警方找了二十年；等 DNA 叫出他的名字时，他已经死了十年。"
GOLDEN_LINES = [
    "凶手找到了，却等不到开庭那一天。",
    "警方说，杀人犯，要追到阴间为止。",
    "这句迟到二十年的回答，留给家属的，只有真相，没有审判。",
]
DESCRIPTION = ("首尔新亭洞，2005 年两名女子相继遇害，专案组查了八年无果，案件沉入悬案柜。"
               "2020 年旧证物里检出的 DNA、23 万人筛查、40 家医疗机构的追寻，终于在 2025 年叫出一个名字——"
               "可他已经死了十年。本片为 AI 真人情景重现，非新闻影像，案件事实来自韩国警方 2025 年 11 月公布与公开报道。")
QUESTION = "迟到二十年的真相，对家属来说还算正义吗？评论区聊聊。"
HASHTAGS = ["#真实案件", "#悬疑", "#韩国", "#悬案", "#纪录片"]

GRID = 6            # 规划网格（story 里的 start/duration 名义值；真实切点由 render.py 的 CUTS 按旁白分句决定）
CLIP_SECONDS = 10   # 智谱每镜请求 10 秒，剪辑取其中约 6 秒
SEED_BASE = 20050607


def presentation():
    return {
        "card_header": "", "card_footer": "",
        "cards": {},
        "title_card": TITLE_CARD,
        "end_card": [],
        "caption_keywords": CAPTION_KEYWORDS,
        "label_overrides": {},
        "sfx_events": [list(e) for e in SFX_EVENTS],
        "captions_en": CAPTIONS_EN,
        "model": MODEL,
        "style_note": "参考片式：真人实拍感年代剧情景重现 + 连续旁白 + 中英双语字幕；0 信息卡、0 片尾卡",
    }


def load_cast():
    """cast.json 是面容描述的唯一来源；{Cx} 占位符在这里逐字节注入提示词。"""
    cast = json.loads(CAST.read_text(encoding="utf-8"))
    assert cast.get("mode") == "face", "cast.json 必须是露脸模式 mode=face"
    faces = {c["id"]: c["face"].strip() for c in cast["characters"]}
    return cast, faces


def _expand(body, sid, faces, declared):
    """把 {Cx} 占位符换成 cast.json 的面容描述（逐字节），并核对与 cast.json 的 shots 登记一致。"""
    import re as _re
    used = _re.findall(r"\{(C\d+)\}", body)
    want = list(declared.get(sid, []))
    assert used == want, f"{sid} 占位符 {used} 与 cast.json 登记 {want} 不一致"
    out = body
    for cid in used:
        assert cid in faces, f"{sid} 引用了不存在的角色 {cid}"
        out = out.replace("{" + cid + "}", faces[cid])
    assert "{" not in out and "}" not in out, f"{sid} 还有未替换的占位符"
    return out


CHAPTER_SHOT_COUNTS = [5, 8, 6, 6, 7, 8]  # N01..N06 每章镜数，合计 40


def _chapter_of(index):
    acc = 0
    for n, count in enumerate(CHAPTER_SHOT_COUNTS, start=1):
        acc += count
        if index < acc:
            return f"N{n:02d}"
    raise AssertionError(index)


def build():
    cast, faces = load_cast()
    declared = cast.get("shots") or {}
    # 双语分句数量必须逐章对齐（clause_times 按标点切分中文）
    import re
    for cid, _t, text in CHAPTERS:
        zh = [c for c in re.split(r"[，。！？；：、—]+", text) if c]
        en = CAPTIONS_EN[cid]
        assert len(zh) == len(en), f"{cid} 中英分句数不一致：{len(zh)} vs {len(en)}"
    assert len(SHOTS) == 40, f"应为 40 镜，实际 {len(SHOTS)} 镜"

    story = {
        "title": TITLE, "target_duration": 180, "width": 1920, "height": 1080, "fps": 30,
        "model": MODEL, "branch": "arena/f3e80641-desktop-tutorial",
        "style_prefix": STYLE, "negative_prompt": NEGATIVE_PROMPT,
        "principles": PRINCIPLES, "sources": SOURCES, "cast_mode": "face",
        "chapters": [
            {"id": cid, "title": t, "start": i * 30, "duration": 30, "text": text}
            for i, (cid, t, text) in enumerate(CHAPTERS)
        ],
        "shots": [
            {"id": sid, "kind": "zhipu", "start": i * GRID, "duration": GRID,
             "narration_id": _chapter_of(i),
             "prompt": _expand(body, sid, faces, declared), "purpose": purpose,
             "transition_out": trans, "graphic": "",
             "cast": list(declared.get(sid, [])),
             "seed": SEED_BASE + i + 1, "seconds": CLIP_SECONDS, "aspect": "16:9",
             "resolution": "1920x1080", "frame_rate": 30, "camera": camera, "sfx_note": sfx}
            for i, (sid, camera, purpose, trans, body, sfx) in enumerate(SHOTS)
        ],
        "presentation": presentation(),
    }
    # 智谱提示词长度闸门：STYLE + 单镜 ≤ 512 字
    for s in story["shots"]:
        full = STYLE + s["prompt"]
        assert len(full) <= 512, f"{s['id']} 提示词 {len(full)} 字超 512：{full}"
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")

    manifest = json.loads(MANIFEST.read_text())
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        assert clip["id"] == chapter["id"]
        clip["text"] = chapter["text"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    total = sum(len(c["text"]) for c in story["chapters"])
    print(f"story.json 已写入：{len(SHOTS)} 镜（全部智谱真人镜头，0 信息卡），解说 {total} 字（含标点）")


if __name__ == "__main__":
    if "--script" in sys.argv:
        from script_table import render_document
        out = HERE / "抖音脚本.md"
        out.write_text(render_document())
        print(f"抖音脚本.md 已写入（{len(out.read_text())} 字符）")
    elif "--publish" in sys.argv:
        from script_table import publish_document
        out = HERE / "抖音发布文案.md"
        out.write_text(publish_document())
        print(f"抖音发布文案.md 已写入（{len(out.read_text())} 字符）")
    else:
        build()

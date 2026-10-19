#!/usr/bin/env python3
"""《呼格吉勒图案：18岁报案人被判死刑，18年后还他清白》的全部内容源。

这是这部片子**唯一需要动脑写的文件**：解说词 / 45 镜提示词 / 7 张信息卡 /
字幕高亮 / 发布文案都在这里。引擎从 production/kitakyushu2002 移植。

用法::

    python3 production/hugejiletu/build_story.py            # 写 story.json + audio/manifest.json 的逐字文本
    python3 production/hugejiletu/build_story.py --script   # 生成 抖音脚本.md
    python3 production/hugejiletu/build_story.py --publish  # 生成 抖音发布文案.md

内容边界（红线）：
  * 呼格吉勒图本人不做肖像还原：全片只给背影、剪影、手；
  * 父母只给背影、侧影、手，不给清晰正脸；赵志红同样只给背影；
  * 不展示遗体、血腥、刑讯与行刑过程；
  * 赵志红的供述不等于法院认定，2019 年最高法死刑复核对其供称的这起事实不予确认；
  * 呼格吉勒图无罪的依据是原判事实不清、证据不足。

分镜结构（45 镜 = 38 动态 + 7 信息卡，每章 30 秒）：
  N01 报案的人（S01-S08）· N02 六十二天（S09-S15）· N03 九年后（S16-S23）
  N04 证据重新审查（S24-S30）· N05 十八年后无罪（S31-S38）· N06 真正的反转（S39-S45）
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "呼格吉勒图案：18岁报案人被判死刑，18年后还他清白"

STYLE_PREFIX = (
    "Photorealistic cinematic 3D animated reenactment, high-end CGI feature-film render with volumetric "
    "light, shallow depth of field and subtle 35mm film grain, set in Hohhot, Inner Mongolia, China, "
    "between 1996 and 2019: a grey 1990s textile-mill workers' residential compound with brick dormitory "
    "blocks, bicycle sheds and a small brick public toilet building, cold northern streets under sodium "
    "lamps, a plain 1990s Chinese police security booth and police station with paper files and CRT "
    "monitors, an austere Chinese courtroom with wooden benches and a high judge's bench, modest family "
    "flats with enamel cups, floral curtains and framed photographs, overcast northern daylight, dry snow "
    "and thin coal-smoke haze, restrained desaturated blue-grey grading with warm lamplight only in family "
    "scenes, slow-burn true-crime documentary mood, never stylised, never a drawing, never a cartoon; "
    "horizontal 16:9 widescreen composition; characters act with clear full-body movement in medium and "
    "wide shots rather than close-ups - a face is shown only where a shot names one of the cast "
    "characters, never a recognisable real person, and the young man at the centre of the story is never "
    "shown frontally; absolutely no readable text, letters, numbers, Chinese characters, logos or brand "
    "marks anywhere in frame; one single continuous smooth camera move per shot exactly as directed. "
)

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, Chinese characters, words, signage writing, invented headlines, "
    "neon lettering, logos, brand marks, watermark, subtitles, on-screen caption, recognisable real person "
    "likeness, celebrity likeness, portrait of a real public figure, blood, gore, wound, corpse, body bag, "
    "body parts, autopsy, bruise, torture, beating, handcuffs torture, execution, gallows, firing squad, "
    "nudity, erotic content, horror monster, ghost, jump scare, flat 2D cartoon, cel-shaded illustration, "
    "hand-drawn sketch, watercolour, comic panel, low-poly, waxy plastic skin, doll-like figure, every "
    "character with the same face, duplicated identical faces, changing face, morphing objects, "
    "teleportation, jitter, flicker, whip pan, fast zoom, jump cut, split screen, collage"
)

PRINCIPLES = [
    "全部动态镜头为写实 3D CGI 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，"
    "不冒充搜查、审讯、庭审、监控或证物影像",
    "不展示遗体、血腥、刑讯逼供与行刑过程：现场镜头只出现警戒线、手电与勘查背影；"
    "看守所只拍空走廊与铁门；执行只以一句旁白与黑场带过",
    "呼格吉勒图本人不做肖像还原：全片只以背影、剪影、手和物件出现，不给可辨识正脸；"
    "父母只给背影、侧影与手；赵志红只给背影与手，不给面容",
    "不虚构人物对白：全片没有一句台词，只有旁白与字幕；不把推测包装成事实",
    "赵志红的供述不等于法院认定：片中明确二〇一九年最高人民法院死刑复核对包括该起在内的"
    "四起事实不予确认，并明确呼格吉勒图案改判无罪是因为证据不足，不是因为赵志红自认真凶",
    "所有中文姓名、日期、金额、罪名一律由字幕与信息卡后期添加，不交给视频模型拼写；"
    "画面内不出现任何可读文字、门牌、招牌或卷宗字样",
    "每一句事实都指到 sources 里的一条公开来源；口径冲突处只写多源一致的写法",
    "人工检视 qa/ 接触表与 delivery/ 人脸接触表：畸变、伪文字、换脸、中途换场的镜头用 "
    "{\"only\":\"Sxx\"} 重生成，不直接进成片",
    "不猎奇、不消费苦难：落点是证据规则与一个家庭十八年的代价，不是血腥细节",
]

SOURCES = [
    {"id": 1, "url": "https://www.court.gov.cn/fabu/xiangqing/7111.html",
     "usage": "最高人民法院：1996-05-17 一审（1996）呼刑初字第37号，故意杀人罪死刑、流氓罪五年；"
              "1996-06-05 二审（1996）内刑终字第199号驳回上诉、维持原判并核准死刑；1996-06-10 执行；"
              "2014-11-19 作出（2014）内刑监字第00094号再审决定，11-20 李三仁收到再审决定书；"
              "2014-12-15 再审以事实不清、证据不足宣告无罪；原判流氓罪除供述外无其他证据"},
    {"id": 2, "url": "http://paper.people.com.cn/rmrbhwb/html/2014-12/16/content_1510657.htm",
     "usage": "人民日报海外版：上诉理由（没有杀人动机、请求从轻）、二审维持并核准、6月10日执行"},
    {"id": 3, "url": "https://www.rmzxw.com.cn/c/2014-12-15/418797.shtml",
     "usage": "人民政协网：一审罪名与刑期（故意杀人罪死刑、流氓罪五年，决定执行死刑）"},
    {"id": 4, "url": "https://baike.baidu.com/item/%E5%91%BC%E6%A0%BC%E5%90%89%E5%8B%92%E5%9B%BE%E6%A1%88/9877190",
     "usage": "国家赔偿：2014-12-30 决定，合计 2,059,621.40 元（死亡赔偿金与丧葬费 1,047,580 元、"
              "羁押 60 日限制人身自由赔偿 12,041.40 元、精神损害抚慰金 100 万元）"},
    {"id": 5, "url": "https://www.court.gov.cn/zixun/xiangqing/174012.html",
     "usage": "最高人民法院刑五庭负责人答记者问（2019-07-30）：最高法核准赵志红死刑，"
              "但对包括呼格案在内的 4 起事实不予确认；呼格案改判无罪是因证据不足，不是因为赵志红自认真凶"},
    {"id": 6, "url": "https://m.bjnews.com.cn/detail/156452858114028.html",
     "usage": "新京报：最高法未确认赵志红是呼格案真凶；赵志红 2019-07-30 被执行死刑"},
    {"id": 7, "url": "https://www.thepaper.cn/newsDetail_forward_1302105",
     "usage": "澎湃新闻：2015-02-09 呼和浩特中院一审认定赵志红系「4·9」案真凶并判死刑；"
              "2015-04-30 内蒙古高院二审维持"},
    {"id": 8, "url": "https://zh.wikipedia.org/wiki/%E5%91%BC%E6%A0%BC%E5%90%89%E5%8B%92%E5%9B%BE%E6%A1%88",
     "usage": "交叉核对：报案人呼格吉勒图（18岁）与同事闫峰；记者汤计持续追踪；"
              "2014-12-15 新闻发布会宣布无罪"},
]

CHAPTERS = [
    ("N01", "报案的人，为什么成了凶手",
     "一九九六年四月九日，内蒙古呼和浩特，第一毛纺厂家属区。十八岁的呼格吉勒图在夜里发现"
     "女厕所里的异常，拉着同事闫峰跑向治安岗亭报案。可谁也没想到，短短六十二天后，"
     "被押上刑场的，正是这个报案的人。那一晚，他只是想帮忙；他以为，报警就能救下那个陌生女人。"),
    ("N02", "六十二天，一条无法挽回的生命线",
     "当晚，一名二十四岁的女子在公共女厕所内遇害。报警之后，呼格吉勒图没有回家，"
     "他被留在警局，一遍遍接受询问。案件以惊人的速度推进：五月十七日，呼和浩特市中级人民法院"
     "一审以故意杀人罪、流氓罪判处他死刑；六月五日，上诉被驳回；六月十日，死刑执行。这六十二天，成了一条生命线。"),
    ("N03", "九年后，另一个嫌疑人出现",
     "故事本该到此结束。可九年后的二〇〇五年十月，内蒙古警方抓获了连环案嫌疑人赵志红。"
     "审讯中，他主动供称：一九九六年四月九日，毛纺厂家属区女厕所里的那起命案，也是他做的。"
     "这句话，让一桩已经尘封的旧案重新被翻开。而这时，距离呼格吉勒图被执行死刑，已经过去九年。"),
    ("N04", "证据重新接受审查",
     "一桩已经执行死刑的案子，忽然多了一个自称凶手的人。记者汤计开始追踪，"
     "呼格吉勒图的父母也一次次申诉。可再审要面对的不是一份供述，而是当年的全部证据："
     "供述与尸检报告对不上，指甲缝里的O型血只能证明血型，不能锁定凶手；"
     "原判认定的流氓罪，除口供外没有别的证据。"),
    ("N05", "十八年后，无罪判决",
     "二〇一四年十一月，内蒙古自治区高级人民法院决定再审。十二月十五日，再审判决："
     "原判事实不清、证据不足，撤销原判，宣告呼格吉勒图无罪。十八年，一纸迟到的清白。"
     "十二月三十日，国家赔偿决定作出，共计二百零五万余元。可钱能补偿损失，却补不回一个人。"),
    ("N06", "真正的反转",
     "但真正的反转，不是真凶出现。二〇一九年，最高人民法院复核赵志红案时，"
     "对包括这起在内的四起事实不予确认，并明确：呼格吉勒图案改判无罪，是因为证据不足，"
     "不是因为赵志红自认真凶。怀疑不能代替证据，供述不能代替核实。"
     "一个人的清白，必须经得起证据的检验。这也是这起案件，留给所有人的问题。"),
]

HOLD = ("no cut, no scene change, no camera relocation, no extra people, "
        "no readable text in frame; hold on this single view for the full clip.")

SHOTS = [
    # ---------------- N01 报案的人（S01-S08：7 动态 + 1 信息卡）----------------
    ("S01", "agnes", "低机位跟拍，自后向前推进", "钩子：1996 年深夜，十八岁的青年跑向岗亭报案",
     "接信息卡：案件名片",
     "A cold night in April 1996 outside a grey workers' residential compound in Hohhot: a slim eighteen-"
     "year-old Chinese man in a cheap dark zip jacket and cloth shoes runs along a narrow lane between "
     "brick dormitory blocks toward a small lit police security booth, seen only from behind, his breath "
     "visible in the cold air, bare poplar branches overhead, one sodium lamp buzzing above a bicycle "
     "shed, the lane otherwise empty. Low camera at knee height tracking his hurried steps from behind as "
     "the booth's light grows larger, " + HOLD,
     "急促脚步 + 风声 + 低沉心跳"),
    ("S02", "graphic", "信息卡（静帧）", "名片：案名 / 地点与年代 / 一句话结局",
     "接动态镜：案发的公共厕所外",
     "案件名片：案名 / 地点与年代 / 一句话结局",
     "低音撞击"),
    ("S03", "agnes", "从暗处缓慢推向警戒线", "案发现场外围：手电、警戒线、没有遗体",
     "接动态镜：岗亭内报案",
     "Night outside a small brick public toilet building at the edge of the residential compound: two "
     "police officers in dark 1990s Chinese uniforms stand behind a rope barrier with flashlights, their "
     "beams sweeping the brick wall and the concrete path, a few residents in padded coats keep a "
     "respectful distance at the far end of the lane, the doorway itself is dark and empty and no body is "
     "visible anywhere; frost on the ground, cold blue shadows. Slow push in from the dark courtyard "
     "toward the barrier, stopping outside it, " + HOLD,
     "手电开关 + 远处警笛 + 低声交谈"),
    ("S04", "agnes", "越过报案人肩头，缓推民警面部", "岗亭里：他主动报案，登记本摊开",
     "接动态镜：询问室",
     "Inside a small 1990s Chinese neighborhood police security booth at night: a fifty-year-old officer "
     "({C1}) sits behind a worn wooden desk with a thick handwritten logbook open in front of him, a green "
     "enamel tea mug and a black rotary telephone beside it; the eighteen-year-old young man stands with "
     "his back to the camera, shoulders tense, one hand on the desk edge; fluorescent tube light, a wall "
     "clock, no readable text on any paper. Slow push from the doorway over the young man's shoulder "
     "toward the officer's face, " + HOLD,
     "翻页声 + 门响 + 急促呼吸"),
    ("S05", "agnes", "沿墙极慢横移，始终只给背影", "询问室：他被留下，一遍遍问话",
     "接动态镜：卷宗与日历",
     "A dim interview room in a 1990s Chinese police station: the eighteen-year-old young man sits on a "
     "plain wooden stool at a scarred table, seen from behind and slightly to the side so his face stays "
     "invisible, both hands clasped on the table, a single bare bulb hanging above, the rest of the room "
     "falling into shadow, a door with a small window behind him; cold grey walls, no objects with "
     "lettering. Very slow lateral creeping move around the room, keeping him in the corner of frame, "
     + HOLD,
     "时钟滴答 + 低频弦乐"),
    ("S06", "agnes", "快速横移扫过卷宗，收在日历", "案件以惊人的速度推进",
     "接动态镜：1996 年法庭",
     "A cluttered 1990s Chinese police office desk in harsh fluorescent light: a thick stack of paper case "
     "files, a heavy manual typewriter, a brass date stamp, and a wall calendar whose pages turn from "
     "April to May 1996 in a slow breeze from a window; an officer's hand rests on the file, a cigarette "
     "smoulders in a tin ashtray. Rapid but smooth lateral sweep across the desk ending on the calendar, "
     + HOLD,
     "打字机声 + 翻页声 + 音乐骤紧"),
    ("S07", "agnes", "自法官席缓慢下移，收在被告背影", "1996 年一审：他被判死刑",
     "接动态镜：落章",
     "A Chinese courtroom in 1996: a young man in a plain dark jacket stands alone in the defendant's dock "
     "seen from behind, two bailiffs in dark uniforms stand at a distance, the judge's bench rises at the "
     "far end under a high ceiling, wooden benches empty in the foreground, cold daylight through tall "
     "windows; solemn, still, no readable text anywhere. Slow move from the high bench down toward the "
     "empty benches, ending on the defendant's back, " + HOLD,
     "低沉钟声 + 法庭回声"),
    ("S08", "agnes", "极近特写，印章落下", "判决落下：五月十七日",
     "接动态镜：法院外景",
     "Extreme close-up of a heavy red official stamp coming down onto a document on a wooden desk in "
     "1996, a hand in a dark sleeve pressing it firmly, dust motes in a shaft of cold window light, the "
     "paper deliberately blank of any readable characters, the stamp itself plain and unmarked. Slow push "
     "in as the stamp lands, " + HOLD,
     "落章闷响 + 静默一拍"),

    # ---------------- N02 六十二天（S09-S15：6 动态 + 1 信息卡）----------------
    ("S09", "agnes", "自台阶缓慢上移", "二审：维持原判",
     "接信息卡：62 天时间线",
     "Exterior of a plain 1990s Chinese intermediate people's court building in Hohhot on an overcast "
     "spring morning: grey stone steps, tall glass doors, a bare flagpole, a few people in dark coats "
     "walking up the steps, leafless trees along the pavement; no signage or lettering anywhere. Slow "
     "rise from the steps toward the entrance doors, " + HOLD,
     "风声 + 脚步声 + 沉稳弦乐"),
    ("S10", "graphic", "信息卡（静帧）", "时间线：4·9 到 6·10，只有 62 天",
     "接动态镜：翻动上诉状",
     "时间线：案发 / 一审 / 二审 / 执行，共 62 天",
     "低音鼓点"),
    ("S11", "agnes", "自纸面缓慢推向台灯", "上诉：他说自己没有杀人动机",
     "接动态镜：高院走廊",
     "Close-up of hands turning the pages of a typed legal appeal document at a wooden desk, a fountain "
     "pen resting beside it, a green shaded desk lamp casting a warm pool of light, the typed characters "
     "deliberately blurred and unreadable; the hands are those of the young man's mother, sleeves of a "
     "plain grey cardigan. Slow push in across the paper toward the pen, " + HOLD,
     "纸张摩擦 + 轻微叹息"),
    ("S12", "agnes", "跟随书记员背影，缓慢推进", "卷宗合上：维持原判",
     "接动态镜：看守所走廊",
     "A long empty corridor in a 1990s Chinese high court building: polished terrazzo floor, closed wooden "
     "doors along one side, a clerk in a dark uniform walking away from camera carrying a thick file "
     "folder, cold daylight from tall windows, dust in the air. Slow tracking move following the clerk "
     "from behind, " + HOLD,
     "文件夹合拢 + 脚步回声"),
    ("S13", "agnes", "极慢后退，走廊沉入阴影", "6 月 10 日：执行（不展示过程）",
     "接动态镜：父母家中",
     "A cold concrete corridor inside a Chinese detention facility in 1996, seen from a distance: heavy "
     "steel doors along the wall, a single overhead bulb, the far end sinking into shadow, absolutely no "
     "people and nothing happening; the shot is restrained and symbolic, no execution, no violence, no "
     "gore. Very slow pull back as the corridor darkens, " + HOLD,
     "沉重脚步 + 门锁声 + 静默"),
    ("S14", "agnes", "自照片缓慢拉远", "父母：他们不相信儿子是凶手",
     "接动态镜：申诉材料",
     "A modest 1990s Chinese family flat in the evening: an elderly couple sit at a worn wooden table, seen "
     "from behind and three-quarter angles so their faces stay in shadow, a framed black-and-white "
     "photograph of a young man stands on the table between them, two enamel cups, a wall clock, floral "
     "curtains drawn; cold blue evening light through the window, a single warm bulb above. Slow pull back "
     "from the photograph to the silent room, " + HOLD,
     "时钟滴答 + 低沉钢琴"),
    ("S15", "agnes", "自手心缓慢横移过材料堆", "申诉：一年又一年",
     "接动态镜：2005 年警局",
     "Close-up of an elderly woman's hands stacking handwritten appeal letters and official documents on a "
     "wooden table, the paper edges worn soft, a pair of reading glasses and a ballpoint pen nearby, thin "
     "winter daylight, a clock ticking somewhere off frame; the documents carry no readable characters. "
     "Slow lateral move across the growing stack of paper, " + HOLD,
     "纸张轻响 + 钟摆声"),

    # ---------------- N03 九年后（S16-S23：7 动态 + 1 信息卡）----------------
    ("S16", "agnes", "自门口缓推向桌面", "2005 年：系列案件侦破",
     "接信息卡：赵志红落网",
     "A busy Chinese police investigation office in 2005: several detectives in plain clothes stand around "
     "a large table covered with case files and photographs, a wall map of the Inner Mongolia region behind "
     "them, two bulky CRT monitors on side desks, fluorescent lights, cigarette smoke in the air, blinds "
     "half drawn; no readable text on any document, screen or map label. Slow push in from the doorway "
     "toward the table, " + HOLD,
     "电话铃 + 文件翻动 + 低音鼓点"),
    ("S17", "graphic", "信息卡（静帧）", "2005 年 10 月：赵志红落网",
     "接动态镜：押解",
     "名片：时间 / 人物 / 一句供述",
     "门锁声"),
    ("S18", "agnes", "肩后跟拍，推向询问室门", "押解：只给背影",
     "接动态镜：询问室",
     "A corridor in a Chinese police station in 2005: two plainclothes officers walk beside a handcuffed "
     "adult male suspect seen only from behind, his head lowered, his face never visible, passing a row of "
     "closed doors toward an interview room at the far end; cold fluorescent light, worn green paint on "
     "the walls, no lettering. Slow tracking shot from behind at shoulder height, " + HOLD,
     "脚步声 + 门锁声 + 室内低鸣"),
    ("S19", "agnes", "越过嫌疑人肩头，推至刑警面部", "审讯：他说那起命案是他做的",
     "接动态镜：两份卷宗",
     "Inside a Chinese police interview room in 2005: a middle-aged detective ({C2}) sits across a scarred "
     "table writing in a notebook, his face lit from above, while the suspect's handcuffed hands rest on "
     "the table in the foreground with his face out of frame; an old cardboard case file lies open beside "
     "the notebook, an ashtray, a cup of tea; grey walls, no readable text. Slow push in past the "
     "suspect's shoulder toward the detective's face as his pen stops moving, " + HOLD,
     "笔尖划纸 + 音乐骤停"),
    ("S20", "agnes", "俯拍，两份卷宗之间缓慢移动", "1996 与 2005：两本案卷并排",
     "接动态镜：记者办公室",
     "Overhead close-up of a metal desk in a Chinese police office: two thick case folders lie side by "
     "side, one faded and worn with a plain tab, the other newer with a plain tab, a detective's hand "
     "places a third sheet between them, a desk lamp throws warm light, the tabs and pages deliberately "
     "blank of any lettering. Slow top-down push in and slight rotation between the two folders, " + HOLD,
     "纸张摩擦 + 低沉鼓点"),
    ("S21", "agnes", "自桌面缓慢抬升至记者面部", "记者汤计：持续追踪",
     "接动态镜：深夜打电话",
     "A small Chinese newsroom at night in the mid-2000s: a journalist in his forties ({C3}) sits at a "
     "cluttered desk under a green desk lamp, a black rotary telephone at his elbow, stacks of old "
     "newspapers and handwritten notes around him, a computer monitor glowing softly with no readable "
     "content, blinds closed behind him. Slow push in from the desk surface toward his tired, focused "
     "face, " + HOLD,
     "键盘声 + 夜晚环境声"),
    ("S22", "agnes", " notebooks 到面部缓慢横移", "一个个电话，一次次追问",
     "接动态镜：日历翻过九年",
     "The same Chinese newsroom later that night: the journalist ({C3}) holds the telephone receiver to his "
     "ear, pen in his other hand hovering over a notebook, a wall behind him covered with newspaper "
     "clippings whose headlines are all unreadable, a cold cup of tea, the desk lamp the only warm light "
     "in the room. Slow lateral move from the notebook to his face, " + HOLD,
     "电话听筒声 + 笔尖声"),
    ("S23", "agnes", "固定机位拍日历，末段推向积灰卷宗", "九年过去：2005 → 2014",
     "接动态镜：父母整理材料",
     "A wall calendar in a Chinese office turning from 2005 to 2014 as seasons pass in a slow time-lapse: "
     "the pages lift and fall, sunlight and shadow sweep across the wall, dust hangs in the beam, a stack "
     "of old case files sits on the desk below growing visibly dustier; no readable numerals or characters "
     "on the calendar or files. Static camera with slow push in on the dusty stack at the end, " + HOLD,
     "翻页声 + 时间流逝的低鸣"),

    # ---------------- N04 证据重新审查（S24-S30：6 动态 + 1 信息卡）----------------
    ("S24", "agnes", "自双手缓慢拉远至整间屋子", "父母还在等",
     "接信息卡：再审核对证据",
     "A modest Chinese family flat in 2014: an elderly couple sit side by side at a wooden table covered "
     "with appeal letters and legal documents, seen from behind and the side so their faces are not clearly "
     "visible, the woman's hand resting on the man's arm, a framed photograph of a young man on the "
     "sideboard, weak winter daylight through net curtains. Slow pull back from their hands to the whole "
     "quiet room, " + HOLD,
     "纸张摩擦 + 轻微抽泣"),
    ("S25", "graphic", "信息卡（静帧）", "再审核对：四处对不上",
     "接动态镜：两份材料并置",
     "信息卡：供述与尸检矛盾 / 血型不能锁定 / 供述不稳定 / 另一罪名无其他证据",
     "低音鼓点"),
    ("S26", "agnes", "自一份文件缓慢横移到另一份", "供述与尸检报告对不上",
     "接动态镜：显微镜",
     "A close-up of two documents laid side by side on a grey table in a Chinese judicial review office: a "
     "typed forensic report and an old handwritten interrogation record, both marked with plain coloured "
     "sticky tabs, a reviewer's hands in white cotton gloves turning one page toward the other, a "
     "magnifying glass resting nearby, all characters deliberately blurred and unreadable. Slow lateral "
     "move from one document to the other, " + HOLD,
     "翻页声 + 低沉弦乐"),
    ("S27", "agnes", "自显微镜推向手持玻片", "血型：只能证明类型，不能锁定凶手",
     "接动态镜：审查人员",
     "A clean forensic laboratory bench in a Chinese judicial facility: a binocular microscope, a sealed "
     "paper evidence envelope, a glass slide held up to the light by a gloved hand, a laboratory report "
     "folder lying closed, cold white light, no biological material visible, no readable text. Slow push "
     "in from the microscope to the slide in the gloved hand, " + HOLD,
     "仪器轻鸣 + 纸张声"),
    ("S28", "agnes", "从审查人员身后缓慢绕行", "证据之间无法相互印证",
     "接动态镜：检察官阅卷",
     "Two middle-aged Chinese legal reviewers in plain shirts stand at a long table covered with case files, "
     "one pointing at a page while the other leans in, both seen from behind and the side so their faces "
     "stay unclear; grey daylight through a tall window, a thermos and enamel cups at the edge of the "
     "table, no readable text on the documents. Slow arc around the table from behind them, " + HOLD,
     "低语声 + 纸张翻动"),
    ("S29", "agnes", "自卷宗推至检察官面部", "检察机关：原判事实不清、证据不足",
     "接动态镜：高院外景",
     "A Chinese prosecutor's office in 2014: a prosecutor in his forties ({C4}) sits behind a desk with a "
     "very thick historical case file open before him, reading carefully, a green shaded lamp, bookshelves "
     "behind him, cold winter light at the window; no readable text on the file or the shelves. Slow push "
     "in from the file across the desk to his thoughtful face, " + HOLD,
     "翻页声 + 室内钟表"),
    ("S30", "agnes", "自台阶缓慢上移", "2014 年 11 月：决定再审",
     "接动态镜：送达到家",
     "Exterior of a Chinese high court building in Hohhot in late autumn 2014: grey stone facade, wide "
     "steps, a few officials in dark coats carrying document folders walking toward the entrance, leafless "
     "trees, cold pale sunlight, no signage or lettering. Slow rise from the steps toward the doors, "
     + HOLD,
     "风声 + 脚步声 + 沉稳弦乐"),

    # ---------------- N05 十八年后无罪（S31-S38：6 动态 + 2 信息卡）----------------
    ("S31", "agnes", "双手特写，缓慢推近", "再审决定书送达",
     "接信息卡：宣判无罪",
     "A doorway of a modest Chinese family flat in winter 2014: a court official's gloved hands hand a "
     "sealed document envelope to an elderly man's hands, both pairs of hands in the foreground, the "
     "corridor behind in soft focus, cold daylight; no faces, no readable text on the envelope. Slow push "
     "in on the hands as the envelope changes hands, " + HOLD,
     "门铃 + 纸张轻响"),
    ("S32", "graphic", "信息卡（静帧）", "2014-12-15：宣告无罪",
     "接动态镜：法庭内",
     "信息卡：日期 / 法院 / 结论",
     "低沉钟声"),
    ("S33", "agnes", "沿审判席缓慢推向法官侧脸", "法庭：宣读再审判决",
     "接动态镜：空被告席",
     "A Chinese courtroom in December 2014: a judge in black robes ({C5}) stands at the high bench reading "
     "from a written judgment, seen from the side and slightly below, the court clerk and two lawyers "
     "seated at their tables in the foreground, wooden panelling, cold daylight from high windows, all "
     "documents face down or blank. Slow push in along the bench toward the judge's profile, " + HOLD,
     "翻页声 + 法庭静默"),
    ("S34", "agnes", "极慢推近空椅子", "空着的被告席",
     "接动态镜：父母听到结果",
     "An empty defendant's chair in a Chinese courtroom, a single pale beam of daylight falling across the "
     "wooden seat, the courtroom around it in deep shadow, dust motes drifting in the light, no people "
     "anywhere, no readable text. Very slow push in on the empty chair, " + HOLD,
     "一秒静默 + 低频弦乐"),
    ("S35", "agnes", "自文件推向照片", "十八年，一纸迟到的清白",
     "接动态镜：赔偿决定书",
     "An elderly Chinese couple sitting on a worn sofa in a modest flat, seen from behind and three-quarter "
     "angles so their faces are not clear: the woman's hand pressed to her mouth, the man holding a folded "
     "document in both hands, a framed photograph of a young man on the table before them, cold winter "
     "light through the window. Slow push in from the document in the man's hands toward the photograph, "
     + HOLD,
     "轻微抽泣 + 低沉钢琴"),
    ("S36", "agnes", "自文件缓慢拉远到照片", "国家赔偿：205 万余元",
     "接动态镜：照片与白花",
     "Close-up of a legal compensation decision document lying open on a wooden table in a Chinese home, an "
     "official seal visible but no readable characters, an elderly woman's hand resting at the edge of the "
     "paper, a cup of tea and a framed photograph nearby, soft winter daylight. Slow pull back from the "
     "document to the photograph, " + HOLD,
     "纸张轻响 + 钢琴延续"),
    ("S37", "agnes", "缓慢推近白花与相框边缘", "失去的十八岁，无法补偿",
     "接信息卡：赔偿构成",
     "A quiet Chinese home in winter: a framed photograph of a young man stands on a wooden sideboard beside "
     "a single white chrysanthemum in a glass, the photograph angled slightly away from the camera so the "
     "face is soft and not clearly recognisable, warm afternoon light through the window, dust in the air. "
     "Slow push in until the flower and the edge of the frame fill the shot, " + HOLD,
     "室内安静 + 柔和钢琴"),
    ("S38", "graphic", "信息卡（静帧）", "赔偿构成：三笔钱",
     "接动态镜：2019 年最高法",
     "信息卡：死亡赔偿金与丧葬费 / 羁押 60 日 / 精神损害抚慰金",
     "低音收束"),

    # ---------------- N06 真正的反转（S39-S45：6 动态 + 1 信息卡）----------------
    ("S39", "agnes", "自台阶缓慢上移到立柱", "2019 年：最高人民法院复核",
     "接信息卡：一条边界",
     "A cold winter morning outside a solemn Chinese supreme court building in Beijing: grey stone columns, "
     "wide steps, bare trees, a single flagpole, a few figures in dark coats walking past at a distance; no "
     "signage or lettering, overcast sky. Slow rise from the steps to the columns, " + HOLD,
     "寒风 + 低沉弦乐"),
    ("S40", "graphic", "信息卡（静帧）", "边界：无罪依据是证据不足，不是「真凶认罪」",
     "接动态镜：两份独立卷宗",
     "信息卡：最高法复核未确认赵志红为该案真凶 / 无罪依据是原判事实不清、证据不足",
     "低音撞击"),
    ("S41", "agnes", "俯拍绕行，两份卷宗互不接触", "两起案件，两份结论",
     "接动态镜：记者回望",
     "Top-down close-up of a large desk in a Chinese legal office: two thick case folders lie apart from "
     "each other with a clear gap between them, one closed and tied with string, the other open with blank "
     "pages, a judge's hand rests beside them without touching, a desk lamp throws a pool of warm light, "
     "everything else in shadow; no readable text. Slow circular move around the two folders, " + HOLD,
     "纸张轻放 + 低沉弦乐"),
    ("S42", "agnes", "自窗上倒影缓慢拉远到桌面", "十年追踪：案件没有被时间掩埋",
     "接动态镜：空法庭",
     "A Chinese newsroom at dawn in 2019: a journalist now in his fifties ({C3}) stands at a window looking "
     "out at a pale winter sky, his desk behind him covered with old newspaper clippings and notebooks, the "
     "room lit only by the cold dawn light and one desk lamp, no readable text. Slow pull back from his "
     "reflection in the window to the cluttered desk, " + HOLD,
     "清晨环境声 + 钢琴"),
    ("S43", "agnes", "极慢沿过道后退", "结尾：一把空椅子",
     "接动态镜：城市远景",
     "An empty Chinese courtroom at the end of the day: rows of wooden benches, the judge's high bench, and "
     "a single beam of natural light falling across an empty defendant's chair, dust drifting in the beam, "
     "everything else sinking into shadow; no people, no readable text. Very slow pull back down the aisle, "
     + HOLD,
     "静默 + 一声低音"),
    ("S44", "agnes", "极慢航拍拉升", "呼和浩特的清晨",
     "接动态镜：白花静物",
     "A wide aerial view of Hohhot at dawn in winter: low grey residential blocks, bare trees, a few "
     "chimneys with thin smoke, distant hills under a pale sky, streets almost empty, a thin layer of snow "
     "on the rooftops; no readable text or signage. Very slow aerial pull back and rise, " + HOLD,
     "弦乐渐强后收束"),
    ("S45", "agnes", "静物横移，从白花到相框", "最后的致意：一枝白花",
     "接片尾卡",
     "A plain wooden shelf in a quiet Chinese room in clear morning light: a single white chrysanthemum "
     "stands in a simple glass of water, a small framed photograph beside it turned slightly away so the "
     "face is not distinguishable, the room otherwise empty and swept, curtain drawn wide, stillness and "
     "dignity, no people anywhere. Slow lateral move along the shelf from the flower to the photograph, "
     + HOLD,
     "微弱晨风 + 一声远处鸟鸣"),
]

CARD_HEADER = "案件档案  /  中国内蒙古 · 一九九六至二〇一九"
CARD_FOOTER = "公开报道口径 · 并非原始档案影像"
CARDS = {
    "S02": ("呼格吉勒图案", "内蒙古呼和浩特 · 一九九六年", "报案人 · 十八岁 · 六十二天后被执行死刑"),
    "S10": ("六十二天", "四月九日 案发 · 五月十七日 一审死刑", "六月五日 二审维持 · 六月十日 执行"),
    "S17": ("二〇〇五年十月", "连环案嫌疑人赵志红落网", "审讯中供称：一九九六年那起命案也是他所为"),
    "S25": ("再审重新核对证据", "供述与尸检矛盾 · 血型不能唯一锁定", "供述不稳定 · 另一罪名无其他证据"),
    "S32": ("二〇一四年十二月十五日", "内蒙古自治区高级人民法院再审宣判", "原判事实不清、证据不足 · 宣告无罪"),
    "S38": ("国家赔偿", "二〇一四年十二月三十日", "死亡赔偿金、丧葬费、精神损害抚慰金等共二百零五万余元"),
    "S40": ("一条必须说清的边界", "无罪依据：原判事实不清、证据不足", "最高法复核未确认赵志红为该案真凶"),
}
TITLE_CARD = ["呼格吉勒图案", "18岁报案人 · 62天死刑 · 18年后无罪 · 内蒙古 1996—2014"]
END_CARD = [
    "报案的人，为什么成了凶手？",
    "呼格吉勒图案 · 一九九六至二〇一四 · 一条生命与十八年",
    "怀疑不能代替证据，供述不能代替核实。",
    "资料：最高人民法院 / 人民日报 / 新华社 / 新京报 / 央视网 · 原创解说 · AI动画情景重现",
]
CAPTION_KEYWORDS = [
    "一九九六年", "十八岁", "呼格吉勒图", "闫峰", "报案", "六十二天", "死刑", "五月十七日",
    "六月五日", "六月十日", "赵志红", "二〇〇五年", "供述", "汤计", "申诉", "再审",
    "证据", "尸检", "O型血", "流氓罪", "二〇一四年", "十二月十五日", "无罪", "国家赔偿",
    "二百零五万", "二〇一九年", "最高人民法院", "不予确认", "证据不足", "清白",
]
LABEL_OVERRIDES = {
    "S01": "AI动画情景重现 · 非新闻影像 · 非本人容貌",
    "S03": "AI动画情景重现 · 非案发现场影像",
    "S04": "AI动画情景重现 · 非报案影像 · 非本人容貌",
    "S05": "AI动画情景重现 · 非询问影像 · 非本人容貌",
    "S06": "AI动画情景重现 · 非档案影像",
    "S07": "AI动画示意 · 非庭审影像 · 非本人容貌",
    "S08": "AI动画情景重现 · 非判决文书影像",
    "S09": "AI动画情景重现 · 非实景影像",
    "S11": "AI动画情景重现 · 非申诉材料影像",
    "S12": "AI动画情景重现 · 非法院实景",
    "S13": "AI动画情景重现 · 非监管场所实景 · 不展示执行",
    "S14": "AI动画情景重现 · 非本人容貌",
    "S15": "AI动画情景重现 · 非申诉材料影像",
    "S16": "AI动画情景重现 · 非警方办案影像",
    "S18": "AI动画情景重现 · 非押解影像 · 非本人容貌",
    "S19": "AI动画情景重现 · 非审讯影像 · 非本人容貌",
    "S20": "AI动画情景重现 · 非案卷影像",
    "S21": "AI动画情景重现 · 非本人容貌",
    "S22": "AI动画情景重现 · 非本人容貌",
    "S23": "AI动画情景重现 · 非档案影像",
    "S24": "AI动画情景重现 · 非本人容貌",
    "S26": "AI动画情景重现 · 非鉴定文书影像",
    "S27": "AI动画情景重现 · 非鉴定实景",
    "S28": "AI动画情景重现 · 非办案实景",
    "S29": "AI动画情景重现 · 非本人容貌",
    "S30": "AI动画情景重现 · 非实景影像",
    "S31": "AI动画情景重现 · 非送达影像",
    "S33": "AI动画示意 · 非庭审影像 · 非本人容貌",
    "S34": "AI动画示意 · 非庭审实景",
    "S35": "AI动画情景重现 · 非本人容貌",
    "S36": "AI动画情景重现 · 非赔偿文书影像",
    "S37": "AI动画情景重现 · 非本人容貌",
    "S39": "AI动画情景重现 · 非实景影像",
    "S41": "AI动画情景重现 · 非案卷影像",
    "S42": "AI动画情景重现 · 非本人容貌",
    "S43": "AI动画示意 · 非庭审实景",
    "S44": "AI动画情景重现 · 非实景航拍",
    "S45": "AI动画情景重现 · 非本人容貌",
}
SFX_EVENTS = [
    ("S04", "paper"),
    ("S08", "press"),
    ("S11", "paper"),
    ("S12", "keys"),
    ("S19", "paper"),
    ("S26", "paper"),
    ("S28", "paper"),
    ("S31", "keys"),
    ("S33", "paper"),
    ("S36", "press"),
]

TITLES = [
    "18岁报案人被判死刑，18年后法院还他清白",
    "62天走向死刑，18年后改判无罪：呼格吉勒图案",
    "报案的人，为什么成了凶手？｜呼格吉勒图案全解",
]
HOOK = ("一九九六年四月，内蒙古呼和浩特，十八岁的呼格吉勒图发现女厕所里的异常，主动跑去报案。"
        "六十二天后，被押上刑场的正是这个报案的人。十八年后，法院再审宣告他无罪——"
        "而真正的反转，不是「真凶出现」，是证据本身经不起检验。")
GOLDEN_LINES = [
    "怀疑不能代替证据，供述不能代替核实。",
    "报案的人成了凶手，用了六十二天；还他清白，用了十八年。",
    "这起案件最大的反转，不是另一名嫌疑人出现，而是原判的证据根本立不住。",
]
DESCRIPTION = (
    "一九九六年四月九日，内蒙古呼和浩特第一毛纺厂家属区，一名二十四岁女子在公共女厕所内遇害。"
    "十八岁的呼格吉勒图与同事闫峰报案，随后被认定为凶手；五月十七日一审死刑，六月五日二审维持，"
    "六月十日执行，距离案发只有六十二天。二〇〇五年，连环案嫌疑人赵志红落网并供称该案系其所为；"
    "二〇一四年十二月十五日，内蒙古自治区高级人民法院再审以事实不清、证据不足宣告呼格吉勒图无罪；"
    "十二月三十日作出国家赔偿决定。二〇一九年，最高人民法院复核赵志红案时对该起事实不予确认。"
    "本片画面为AI生成的情景重现（非新闻影像、非本人容貌），事实依据公开报道整理。"
)
QUESTION = "如果当年那份供述被认真核对一次，这个家庭的十八年会不会不一样？评论区聊聊。"
HASHTAGS = ["#悬疑", "#真实案件", "#呼格吉勒图案", "#案件解说", "#法治"]

GRID = 4
AGNES_SECONDS = 6
SEED_BASE = 19960409

FACE_SHOTS = {
    "S04": ["C1"],
    "S19": ["C2"],
    "S21": ["C3"],
    "S22": ["C3"],
    "S29": ["C4"],
    "S33": ["C5"],
    "S42": ["C3"],
}
REFERENCE_SHOTS = {}
FIRST_FRAME = {}


def first_frame_urls():
    base = ("https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/"
            "arena/ba89b9ff-desktop-tutorial/production/hugejiletu/")
    return {sid: base + rel for sid, rel in FIRST_FRAME.items()}


def faces():
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
    story["branch"] = "arena/ba89b9ff-desktop-tutorial"
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
        if sid in FACE_SHOTS:
            shot["cast"] = FACE_SHOTS[sid]
        if sid in REFERENCE_SHOTS:
            shot["reference_image"] = portrait_urls()[REFERENCE_SHOTS[sid]]
        shots.append(shot)
    story["shots"] = shots
    story["presentation"] = presentation()
    story.setdefault("_scaffold", {})["note"] = (
        "内容由 build_story.py 一次性写入；45 镜 × 4 秒规划网格（每镜只用一次）；"
        "视频模型走智谱 CogVideoX-Flash 免费档（generate_cogvideox.py）。")
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
    print(f"露脸镜头：{len(FACE_SHOTS)} 镜")


if __name__ == "__main__":
    if "--script" in sys.argv:
        from script_table import render_document  # noqa: E402
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

#!/usr/bin/env python3
"""《青蛙少年失踪案：一个没有回家的春天》的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

这是这部片子**唯一需要动脑写的文件**（引擎由 production/kanghosun2009 的模板移植而来，
内容按用户上传的 40 镜脚本（抖音文案/20261012-123314_粘贴的文案_20261012-123314.txt）改写，
史实按 SOURCES 里的公开来源核对，见 史实核对.md）。

用法::

    python3 production/frogboy1991/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/frogboy1991/build_story.py --script   # 生成 抖音脚本.md
    python3 production/frogboy1991/build_story.py --publish  # 生成 抖音发布文案.md

本片是**露脸模式**，但有一条写死的红线：五名失踪儿童（金永奎、赵浩延、金钟植、朴灿仁、禹哲元）
**全片不露正脸**，只以背影、剪影、远景和物件出现（服装与书包是区分他们的标记）；
大人（母亲、父亲、刑警、法医、邻居）全部以虚构匿名角色正脸出现，标注「非真人容貌」。
面容 token 只在 cast.json 里写一份，本文件用 {C1}…{C5} 占位符注入，保证逐字节一致。

视频模型走**智谱 CogVideoX-Flash 免费档**（generate_cogvideox.py，不调 Agnes、不产生费用）。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "青蛙少年失踪案：一个没有回家的春天"

# 全片统一的画面风格前缀（英文）。写实 3D CGI 情景重现（不是 2D、不是图片轮播）。
# 注意：style_prefix 参与全部镜头的 request_hash，开工后改一个字 = 全部镜头重做。
STYLE_PREFIX = (
    "Photorealistic cinematic 3D animated reenactment, high-end CGI feature-film render with soft volumetric light, "
    "shallow depth of field and subtle 35mm film grain, set in Daegu, South Korea in 1991 and 2002: low-rise "
    "neighbourhoods of the early 1990s, narrow alleys with corner shops and laundry lines, hillside pine forest of "
    "Mount Waryong in spring and autumn, 1990s elementary school uniforms and classrooms, period-accurate small cars "
    "and buses, a rural shooting-range fence at the forest edge in 2002, warm nostalgic colour grading in childhood "
    "scenes and cooler desaturated tones in police scenes, respectful true-story documentary mood, never stylised, "
    "never a drawing, never a cartoon; horizontal 16:9 widescreen cinematic composition; the children are shown only "
    "from behind, in silhouette or from a distance, never with a readable face; adults act with clear body movement "
    "and expressive gesture, staged in medium and wide shots; a face is shown only where a shot explicitly names one of "
    "the cast characters, and never as a recognisable real person or a likeness of anybody living or dead; absolutely "
    "no readable text, letters, numbers, logos, banners with writing, licence plates or brand marks anywhere inside "
    "the frame; no blood, no bodies, no remains visible; one single continuous smooth camera move per shot exactly as "
    "directed. "
)

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, handwritten posters, newspaper headlines, banners with "
    "writing, watermark, subtitles, on-screen caption, recognisable real person likeness, celebrity likeness, portrait "
    "of a real public figure, child with a readable face, close-up of a child's face, blood, gore, wound, corpse, "
    "skeleton, bones, remains visible, body bag, dismemberment, violence on screen, weapon attack, abduction scene, "
    "nudity, horror monster, ghost, jump scare, flat 2D cartoon, cel-shaded illustration, hand-drawn sketch, "
    "watercolour, comic panel, low-poly, waxy plastic skin, doll-like figure, every character with the same face, "
    "duplicated identical faces, changing face, morphing objects, teleportation, jitter, flicker, whip pan, fast zoom, "
    "jump cut, split screen, collage"
)

# 事实边界与红线：每一条都会印在 抖音脚本.md 的「发布前自查」里。
PRINCIPLES = [
    "全部动态镜头为写实 3D CGI 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，不冒充新闻、档案、现场或证物照片",
    "五名失踪儿童全程不露正脸：只以背影、剪影、远景和物件（服装、书包、帽子）出现；不出现他们的可辨识面容，不出现遗骸、血腥或作案过程",
    "大人（母亲、父亲、刑警、法医、邻居）全部为虚构匿名角色，正脸出现，标注「非真人容貌」；同一角色跨镜头逐字节复用同一条面容 token",
    "所有中文姓名、日期、数字与结论都在字幕和信息卡里以文字呈现，不交给视频模型拼写；画面内不出现任何可读文字",
    "遗骸发现、法医与警方结论一律按公开报道写成「两种说法并列」：警方当年倾向失温，法医团队认定为他杀；不替任何一方下结论",
    "每一句事实都能指到 SOURCES 里的一条公开报道；来源冲突处（具体地点、搜寻人数的口径）写成多源一致的写法",
    "未破案即未破案：片中写明案件至今没有找到凶手，不做任何推测性指认，不渲染凶手视角",
    "人工检视 qa/ 接触表与 delivery/face-cast/ 人脸接触表；换脸、畸变、伪文字、孩子露出可辨识面容的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

# 每条事实的公开来源。
SOURCES = [
    {"id": 1, "url": "https://ko.wikipedia.org/wiki/%EA%B0%9C%EA%B5%AC%EB%A6%AC_%EC%86%8C%EB%85%84_%EC%82%AC%EA%B1%B4",
     "usage": "支撑：一九九一年三月二十六日失踪、五名成员（金永奎、赵浩延、金钟植、朴灿仁、禹哲元）、"
              "二〇〇二年九月二十六日于卧龙山发现遗骸、经庆北大学法医团队认定他杀的分歧、二〇〇六年三月二十五日公诉时效届满、"
              "一九九三年九月家长宣布放弃亲自寻找"},
    {"id": 2, "url": "https://www.koreajoongangdaily.com/korea/frog-boys-case-five-students-vanished-in-1991-found-dead-years-later-still-no-answers/11926967",
     "usage": "支撑：失踪当日为选举日、五名学生的年龄与同校背景、去找蝾螈卵（媒体误报为青蛙）、"
              "二〇〇二年九月二十六日一名采橡子的人发现遗骸、遗骸附近的鞋物与衣物、警方与法医的结论分歧"},
    {"id": 3, "url": "https://en.sedaily.com/society/2026/09/26/five-boys-vanished-in-1991-found-as-remains-11-years-later",
     "usage": "支撑：卧龙山、遗骸发现地为旧军队靶场、警方当年以失温解释、遗骸为五名孩子、二〇〇三年专案组解散、"
              "发现者等待寻找的父亲仍在纪念活动中出现（不写具体人名）"},
    {"id": 4, "url": "https://www.donga.com/news/Society/article/all/20191007/97768691/1",
     "usage": "支撑：全国单一失踪案件最大规模的搜索（年度搜索人力约三十五万人次）、二〇一九年为遗留衣物送交国立科学搜查研究院做 DNA 检测、"
              "失踪地点与村落的距离"},
    {"id": 5, "url": "https://www.mk.co.kr/news/society/9805810",
     "usage": "支撑：一九九一年三月二十六日五名六年级至三年级学生同时失踪、警方与军队投入三十五万人搜山、"
              "遗骸为失踪十一年后的二〇〇二年九月发现、失踪地点与住所约三点五公里"},
    {"id": 6, "url": "https://www.idaegu.com/news/articleView.html?idxno=381061",
     "usage": "支撑：二〇〇二年遗骸发现地为旧陆军第五十师靶场，该师已于一九九四年迁出；二〇一九年警方重启调查并征集新线索"},
    {"id": 7, "url": "https://infoloop.co.kr/life/article/79761/",
     "usage": "支撑：法医鉴定认定为他杀，但十余年过去现场已被风雨破坏；二〇〇六年时效届满、二〇一五年「太完法」（取消杀人罪公诉时效）不溯及既往；至今无人被定罪"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。六段合计约 800–860 字（含标点）。
CHAPTERS = [
    ("N01", "黄金开头：一个没有回家的春天",
     "一九九一年三月二十六日，韩国大邱。五个孩子像往常一样，背起书包走出了家门。"
     "那一天，没有人知道，这会成为韩国历史上最令人痛心的失踪案件之一。"
     "那时的大邱，春天的下午，街道上到处是放学回家的孩子，巷口的老人还在晾晒衣服。"
     "他们只是普通的小学生，有自己的兴趣，也有等着他们回家吃饭的父母。"
     "孩子们约好，天黑之前一定回来。"),
    ("N02", "人物与下午：卧龙山和一群孩子",
     "放学后，五个孩子决定一起去附近的卧龙山玩。金钟植最喜欢找小虫子和小东西，朴灿仁爱笑、爱运动，"
     "金永奎是孩子们的小领头，赵浩延比同伴们沉稳，禹哲元则常跟着哥哥们一起玩。"
     "他们最后一次被人看到，就是在那片山脚下。后来，媒体误把他们说成是去找青蛙，于是他们被叫作青蛙少年。"
     "其实，他们是去找蝾螈卵。那天傍晚，他们本该像往常一样回家吃饭。"),
    ("N03", "全国寻找：三十五万人次，和一间没有人的房间",
     "他们没有回来。夜里，家长开始意识到事情不对。警察和军队进入卧龙山搜索，许多志愿者也加入其中。"
     "这场搜索一共动用了约三十五万人次。电视和报纸一遍遍播出这件事。父母们每天都在希望和绝望之间来回。"
     "房间保持原样，仿佛孩子随时会推门回来。这个案子成了韩国最著名的未解失踪事件之一，而山上的答案，始终没有出现。"),
    ("N04", "十一年后的发现：一个采橡子的人",
     "一九九三年九月，部分家长宣布暂时放弃亲自寻找，回到了各自的生活。时间一年年过去。"
     "直到二〇〇二年九月二十六日，一个上山采橡子的人，在卧龙山的一处荒地上发现了人体遗骸。那里，是旧军队靶场的旧址。"
     "警方当年一度认为，孩子们可能是迷路后在寒冷中死去；但负责鉴定的法医团队，在颅骨上发现了外力造成的损伤，认定他们是被杀害的。"),
    ("N05", "遗骸的真相：他杀与失温，两种说法",
     "遗骸经过 DNA 鉴定，确认属于失踪的五名孩子。他们已经消失了十一年半。"
     "法医团队的鉴定，让这起案件从失踪变成了一桩命案。而警方当年的判断，则是另一种说法。"
     "可是，风雨和时间已经改写了现场，凶手是谁、事发经过如何，始终没有查清。"
     "二〇〇六年三月二十五日，法定追诉期届满，这起案件仍然没有找到凶手。"),
    ("N06", "未解的谜团：一个关于等待的故事",
     "二〇一九年，警方重新启动调查，把遗留的衣物送去国立科学搜查研究院做 DNA 检测。"
     "新的技术，让人们期待找到更多线索。但直到今天，真正发生了什么，仍然没有完整的答案。"
     "五个孩子离开的那个下午，成了一个社会永远的记忆。他们留下的，不只是一个案件，还有一个关于寻找、等待和希望的故事。"),
]

HOLD = ("no cut, no scene change, no camera relocation, no extra people beyond those named, "
        "no readable text in frame; hold on this single view for the full clip.")

# 45 镜 × 4 秒。kind: agnes = CogVideoX 动态镜头（38 镜）；graphic = 信息卡（7 镜）。
# 元组：(镜头号, 类型, 运镜, 用途, 接镜, 提示词/卡面描述, 音效备注)
SHOTS = [
    # ---------------- N01 黄金开头（S01–S08）----------------
    ("S01", "agnes", "航拍下降", "开场：一九九一年的大邱晨景",
     "接信息卡：案件名片",
     "Aerial establishing shot of Daegu, South Korea at dawn in spring 1991: low-rise tiled-roof houses and small "
     "apartment blocks along a river valley, soft morning mist over Mount Waryong in the distance, a primary school "
     "courtyard coming into view below with a flagpole and early pupils crossing the yard in small groups seen from far "
     "above; the camera glides down slowly toward the school, no people's faces visible. " + HOLD,
     "清晨鸟鸣 + 远处市声"),
    ("S02", "graphic", "信息卡（静帧）", "片名卡：案件名片",
     "接动态镜：校园里奔跑的背影",
     "案件名片：案名 / 地点与年代 / 规模",
     "低音铺垫"),
    ("S03", "agnes", "低机位跟随", "五个孩子的背影：校园里奔跑",
     "接动态镜：街道上的自行车",
     "Five elementary school boys seen only from behind, running across a sunlit school playground in spring 1991: one "
     "in a bright yellow sports jacket with a small school backpack leads the run, one in a blue jacket with a backpack "
     "strap over his shoulder follows, one in a red cap jogs with a net, one in a green sports top kicks a pebble, one "
     "small boy in a white knitted sweater trails behind; the children's faces are never visible, they are seen from the "
     "back and side only; joyful movement, dust in the sun. Low tracking shot following them from behind, " + HOLD,
     "孩子们的笑声（远景）+ 校园铃声"),
    ("S04", "agnes", "横移", "老街道与自行车",
     "接动态镜：家门口的老邻居",
     "A narrow 1990s residential street in Daegu on a spring morning, low concrete houses with tiled roofs, a parked "
     "small car of the period, and children riding bicycles away from the camera in the distance, seen only from behind; "
     "a shopkeeper's shutter half open with empty crates, no signs with text. Slow lateral move along the street, " + HOLD,
     "自行车铃声 + 早市环境音"),
    ("S05", "agnes", "慢推", "家门口：老邻居晒衣服，孩子背起书包",
     "接动态镜：校门口放学",
     "Morning in a Daegu neighbourhood alley in 1991: an elderly Korean woman {C5} with a grey perm and a plain cardigan "
     "stands at her front gate hanging white laundry on a line, she looks up and smiles warmly toward the children; "
     "in the foreground five children seen from behind pass by her gate one after another, shouldering school backpacks, "
     "the yellow jacket and the red cap are clearly visible. Slow push-in toward the elderly woman's kind face, " + HOLD,
     "晾衣架木棍声 + 远处犬吠"),
    ("S06", "agnes", "中景固定", "放学铃响：孩子们冲出校门",
     "接动态镜：林间小路",
     "A 1990s Korean elementary school gate at afternoon, pupils in navy uniforms rushing out in a stream, all seen from "
     "behind or from far away; a teacher stands out of focus in the gateway, back turned; the iron gate is open, the "
     "playground empty behind them, no readable signs. Static medium-wide shot, slight handheld drift, " + HOLD,
     "放学铃声 + 孩子们的喧闹"),
    ("S07", "agnes", "低机位前推", "卧龙山脚下：春天的树林",
     "接动态镜：山林里找东西的孩子",
     "The foot of Mount Waryong in spring 1991: a sunlit path through young pine and oak trees, bright new leaves, "
     "wildflowers at the roadside, a wooden trail sign with no writing; five small figures seen from behind walk up the "
     "path in a loose line, growing smaller into the forest. Low camera pushing slowly up the path, " + HOLD,
     "树林里的鸟叫 + 风声"),
    ("S08", "agnes", "特写 → 拉远", "金钟植在石头边找小东西（背影）",
     "接信息卡：一九九一年的失踪人数与搜索",
     "A young boy seen from behind, wearing a red cap, crouches beside a mossy rock by a stream in a spring forest, his "
     "small plastic net held low, he is carefully lifting a stone to look underneath; his face is never visible; the other "
     "children stand a few metres behind, backs to the camera, looking down at the stream. Slow pull-back from the crouching "
     "boy, " + HOLD,
     "小溪流水声 + 轻柔的悬念音乐"),

    # ---------------- N02 人物与下午（S09–S15）----------------
    ("S09", "agnes", "环绕", "山坡草地：五个孩子坐在一起（背影）",
     "接动态镜：傍晚的草地",
     "Five children seen only from behind sit together on a grassy slope in the late afternoon of spring 1991, chatting "
     "and pointing toward the mountain; the yellow jacket, the blue jacket, the red cap, the green top and the white "
     "sweater are clearly distinct, faces never visible. A slow orbit around the group at a respectful distance, " + HOLD,
     "孩子们的说笑声（远景）+ 温暖的钢琴"),
    ("S10", "agnes", "远景固定", "夕阳下，孩子们收拾东西走向山林",
     "接动态镜：厨房里母亲的侧影",
     "Sunset over Mount Waryong: five small figures seen from far behind gather their bags and walk up a narrow forest "
     "path toward the dark trees, the orange sun low on the horizon, the figures growing smaller; no faces, no readable "
     "signs. Static wide shot, the children diminish into the forest, " + HOLD,
     "渐弱的说笑声 + 晚风"),
    ("S11", "agnes", "慢推", "厨房：母亲看着挂钟，饭菜放凉",
     "接动态镜：街灯下的父亲",
     "A modest 1990s Korean kitchen at night, a plain wooden table set with rice bowls and side dishes that have gone "
     "cold, a wall clock showing a late hour; a middle-aged Korean woman {C1} with a short permed hairstyle and a "
     "flowered apron stands at the window, turning to look at the clock with worried eyes, her face fully visible and "
     "calm but anxious. Slow push-in toward her face, " + HOLD,
     "挂钟滴答 + 远处狗叫"),
    ("S12", "agnes", "中景跟随", "街灯下：父亲奔跑，打电话找孩子",
     "接信息卡：三十五万人次",
     "A 1990s Daegu residential street at night under sodium street lamps, wet from light rain; a middle-aged Korean man "
     "{C2} in a dark zip jacket runs under the lamp, holding a public payphone receiver to his ear, his face fully "
     "visible, anxious and determined, shouting into the phone; no signs with readable text. Medium tracking shot as he runs, "
     + HOLD,
     "奔跑的脚步声 + 电话忙音"),
    ("S13", "graphic", "信息卡（静帧）", "数字卡：三十五万人次",
     "接动态镜：警局办公室",
     "搜索规模卡：三十五万人次 / 一九九一年三月 — 春天的山林 / 警察、军队与志愿者同时入山",
     "低音撞击"),
    ("S14", "graphic", "信息卡（静帧）", "卡片：其实，他们是去找蝾螈卵",
     "接动态镜：空荡的操场秋千",
     "其实，他们是去找蝾螈卵",
     "轻微的水声"),
    ("S15", "agnes", "慢速摇镜", "空荡的操场：秋千在晃动",
     "接动态镜：夜里的山林搜索",
     "An empty elementary school playground at dusk in spring 1991: a pair of swings still moving gently in the wind, "
     "a basketball lying on the ground, the school building with a few lit windows in the background, no people. Slow "
     "pan across the empty playground, " + HOLD,
     "风吹秋千的吱呀声"),

    # ---------------- N03 全国寻找（S16–S23）----------------
    ("S16", "agnes", "俯拍下摇", "夜里：直升机与搜山的手电",
     "接动态镜：父亲拿着传单",
     "A night search operation on the wooded hills of Mount Waryong: a helicopter's searchlight sweeps across the dark "
     "pine trees far away, dozens of small torch beams move through the undergrowth, figures seen only from a distance "
     "with their backs to the camera; no readable text on uniforms or vehicles. Slow high-angle push down over the forest, "
     + HOLD,
     "直升机轰鸣 + 风声"),
    ("S17", "agnes", "中景固定", "山口：父亲举着传单等待消息",
     "接动态镜：母亲整理房间",
     "At the foot of a hill in Daegu in 1991, a middle-aged Korean man {C2} with a tired face and rumpled clothes stands "
     "at a roadside police post, holding a folded flyer at his chest, eyes looking up toward the mountain, his face "
     "fully visible; the flyer is blank white, no readable text. Static medium shot, " + HOLD,
     "远处搜索的人声 + 风声"),
    ("S18", "agnes", "慢速推进", "搜山：手电光扫过松林，无人入镜",
     "接动态镜：时间流逝的城市",
     "Night search in a dense pine forest on a hillside: beams of handheld flashlights sweep slowly through the dark trunks "
     "and undergrowth, leaves stirring in the light; no people visible, only the moving beams and the forest. Slow push "
     "forward along the beams, " + HOLD,
     "风声 + 远处的呼喊（不可辨识）"),
    ("S19", "agnes", "延时摄影", "时间流逝：城市与季节变换",
     "接动态镜：电视新闻前的人群",
     "Time-lapse of Daegu across several seasons: the sun rising and setting over low-rise houses, the trees changing from "
     "bare winter to green summer to red autumn, traffic passing on a 1990s road, no people's faces; the sequence "
     "shows the passing of years. Time-lapse, steady wide framing, " + HOLD,
     "钟表滴答 + 季节流逝的氛围音"),
    ("S20", "agnes", "中景固定", "电视新闻：一家人围坐看报道",
     "接动态镜：卧龙山的四季",
     "A 1990s Korean living room at night, a family of three seen from behind sits in front of an old CRT television "
     "screen which shows a blurred news broadcast with no readable text; a middle-aged Korean woman {C1} sits beside them "
     "on the sofa, her face fully visible, watching the screen with a tense expression. Static medium shot, " + HOLD,
     "电视新闻的播报声（不可辨识）+ 低沉氛围音"),
    ("S21", "agnes", "慢推", "房间保持原样：书桌、校服、玩具",
     "接动态镜：卧龙山的四季",
     "Slow push-in through a quiet child's bedroom in a Korean house in 1991, soft morning light through a window: a small "
     "wooden desk with a pencil case, a school uniform folded on a chair, a toy car on a tatami mat; the room is empty and "
     "tidy, no people, no readable text. " + HOLD,
     "钟表滴答"),
    ("S22", "agnes", "慢推", "志愿者搜山：父亲走进树林，拨开草丛",
     "接动态镜：卧龙山的四季",
     "A front-facing medium shot in a dense pine forest on a hillside in autumn: {C2}, a middle-aged Korean man in a plain "
     "dark jacket and cap, walks slowly toward the camera, searching the undergrowth with a long wooden stick; his face is "
     "clearly visible, calm and focused, looking down at the ground ahead. Soft background of tall pines and fallen leaves, "
     "no other people, no readable text on clothing. Slow push-in toward him, " + HOLD,
     "落叶与脚步声 + 风声"),
    ("S23", "agnes", "慢推", "卧龙山的四季：春夏秋冬",
     "接动态镜：二〇〇二年的采橡子人",
     "Mount Waryong through the four seasons in a single continuous wide shot: spring blossoms, summer green, autumn red "
     "leaves, winter frost on the hillside pines, the same forest slope throughout; no people, no readable signs. Slow "
     "push across the seasonal forest, " + HOLD,
     "风声 + 远处鸟鸣"),

    # ---------------- N04 十一年后的发现（S24–S30）----------------
    ("S24", "agnes", "中景固定", "一九九三年以后：母亲在家中厨房等待",
     "接信息卡：二〇〇二年九月二十六日",
     "Medium shot inside a quiet family kitchen in Daegu in the years after 1993: {C1} sits at a kitchen table, hands folded, "
     "looking toward a window with a calm, tired expression; a wall calendar and an empty chair are visible; no children, "
     "no readable text. Static shot, " + HOLD,
     "钟表滴答 + 远处的街声"),
    ("S25", "agnes", "中景跟随", "警车驶入山路，警员走向荒地（背影）",
     "接动态镜：警戒线与现场勘查",
     "A dirt forest road on a hillside in autumn 2002: a plain white police car and a van park at the edge of a clearing, "
     "two uniformed officers seen only from behind walk toward the rough ground with their caps on; no readable text on "
     "the vehicles, no remains visible. Medium tracking shot from behind, " + HOLD,
     "汽车引擎熄火 + 脚步声"),
    ("S26", "agnes", "中景跟随", "二〇〇二年：采橡子的村民正面站在荒地边",
     "接信息卡：两种结论",
     "Front view, the camera faces the man directly: {C6}, a middle-aged Korean man in a faded olive work jacket and knitted "
     "cap, stands at the edge of a rough clearing on a hillside in autumn 2002, a cloth bag of acorns on his shoulder; he "
     "looks down toward the ground in front of him with a grave expression. No remains visible, no other people, no "
     "readable text. Medium shot, " + HOLD,
     "风声 + 枯叶声"),
    ("S27", "graphic", "信息卡（静帧）", "结论卡：警方与法医的两种说法",
     "接动态镜：法医实验室",
     "两种说法：警方一度认为是失温 / 法医团队在颅骨上发现外力损伤，认定为他杀 / 十一年后，现场已被风雨破坏",
     "纸张翻动"),
    ("S28", "agnes", "中景固定", "法医实验室：法医正脸看着资料",
     "接动态镜：旧靶场的铁丝网",
     "A forensic laboratory in Daegu in 2002, plain white walls and steel shelving, a middle-aged female forensic scientist "
     "{C4} with shoulder-length black hair in a tidy bun and a white lab coat stands at a steel table covered with paper "
     "folders, her face fully visible, serious and thoughtful, she flips through a report; no readable text on folders. "
     "Medium shot, slow push-in, " + HOLD,
     "纸张翻动 + 实验室的嗡嗡声"),
    ("S29", "agnes", "中景固定", "法医团队：灯箱前研读报告",
     "接动态镜：刑警在旧档案前",
     "Medium shot inside a quiet forensic analysis room: {C4}, a forensic analyst in a white lab coat, stands at a desk studying "
     "printed reports under a lightbox showing an abstract grey film with no readable text; calm, focused expression; no remains, "
     "no other people, no readable text. Static medium shot, " + HOLD,
     "室内安静的环境音"),
    ("S30", "agnes", "中景固定", "刑警重新翻看旧档案",
     "接动态镜：一排搜索人员走进树林",
     "Medium shot in a dim archive office in 1990s Daegu: {C3}, a middle-aged Korean detective in a dark suit, sits at a wooden "
     "desk reviewing a stack of old paper case files under a desk lamp; thoughtful expression; no readable text, no other "
     "people. Static shot, " + HOLD,
     "纸张翻动声"),
    ("S31", "agnes", "近景静物", "DNA 鉴定：试管架",
     "接动态镜：五张剪影排成一排",
     "Close-up still life on a clean laboratory bench: a row of small sealed test tubes in a wooden rack under soft clean light, "
     "shallow depth of field; no people, no remains, no readable text. Slow push-in along the rack, " + HOLD,
     "实验室环境音"),
    ("S32", "agnes", "中景固定", "五个孩子的剪影站成一排",
     "接动态镜：空房间里的父母",
     "Five small children rendered only as dark silhouettes against a soft pale sky, standing in a row on a hilltop at "
     "sunset, each silhouette distinguished by its shape only: one with a backpack, one wearing a cap, one holding a small "
     "net; no faces, no details beyond outlines. Static medium-wide shot, " + HOLD,
     "轻柔的钢琴"),
    ("S33", "agnes", "慢推", "空房间：父母坐在孩子的床边",
     "接信息卡：二〇〇六年三月二十五日",
     "A quiet Korean family room at dusk, a middle-aged father {C2} sits on the edge of a child's bed, the bed neatly made, "
     "a small school backpack hanging on a hook on the wall; the father's face is fully visible, tired and grieving, he "
     "rests his hands on his knees; a woman seen only from behind sits beside him, her face never visible. Slow push-in, " + HOLD,
     "极轻的钢琴 + 远处的钟声"),
    ("S34", "graphic", "信息卡（静帧）", "时效卡：二〇〇六年三月二十五日",
     "接动态镜：DNA 实验室",
     "时效卡：二〇〇六年三月二十五日 / 公诉时效届满 / 案件仍未找到凶手",
     "纸张翻动"),
    ("S35", "agnes", "中景固定", "国立科学搜查研究院：DNA 实验室",
     "接动态镜：夕阳下的卧龙山",
     "A modern forensic DNA laboratory in Seoul, clean white benches, a row of sealed sample tubes in racks and a computer "
     "screen showing abstract blue graphs with no readable text; a female analyst in a white coat {C4} works at the "
     "bench, her face fully visible and focused, carefully pipetting a sample. Medium shot, slow push-in, " + HOLD,
     "仪器的低鸣声"),
    ("S36", "agnes", "远景固定", "夕阳下的卧龙山",
     "接动态镜：孩子们背影慢慢消失",
     "A golden sunset over Mount Waryong, the pine ridges silhouetted against the orange sky, a few birds crossing, no "
     "people, no readable signs. Static wide shot, " + HOLD,
     "风声 + 远处的鸟鸣"),
    ("S37", "agnes", "低机位跟随", "孩子们的背影，慢慢消失在树林",
     "接动态镜：秋天的空校园",
     "Five children seen only from behind, walking slowly away along a forest path at dusk, their outlines growing smaller "
     "and disappearing into the dark trees; the yellow jacket, the blue jacket, the red cap, the green top and the white "
     "sweater are distinguishable only by silhouette and clothing colour; no faces. Low camera following from behind, "
     + HOLD,
     "渐远的脚步声 + 钢琴尾音"),
    ("S38", "agnes", "中景固定", "二〇一九年：刑警手持证物袋重启调查",
     "接信息卡：五个名字",
     "Medium shot in a bright office in 2019: {C3}, a middle-aged Korean detective in a dark suit, stands at a table holding a "
     "sealed clear evidence bag with a folded child's sweater, looking down at it with a serious expression; no blood, no "
     "readable text. Static medium shot, " + HOLD,
     "轻微的办公室环境音"),
    ("S39", "agnes", "中景固定", "老邻居在纪念碑前，低头默哀",
     "接动态镜：春天的树林，孩子们的背影",
     "An elderly Korean woman {C5} with a grey perm and a dark cardigan stands before a small stone memorial in a quiet "
     "pine forest, her hands folded at her waist, her head bowed, her face fully visible and sorrowful; the memorial "
     "has no readable text. Medium shot, slow push-in, " + HOLD,
     "极轻的钢琴 + 林中的风声"),
    ("S40", "graphic", "信息卡（静帧）", "名字卡：五个名字",
     "接动态镜：春天的树林",
     "五个名字：金永奎 · 赵浩延 · 金钟植 · 朴灿仁 · 禹哲元 / 失踪时年龄九至十三岁 / 愿每一个失踪者，都有被记住的名字",
     "钢琴单音"),
    ("S41", "agnes", "低机位跟随", "春天的树林，孩子们在林间奔跑（背影）",
     "接动态镜：母亲独自站在窗前",
     "A bright spring forest of young pine and oak trees, sunlight streaming through, five children seen only from behind "
     "running and laughing along a sunlit forest path, their jackets and caps in colour; joyful and warm, faces never "
     "visible. Low tracking shot from behind, " + HOLD,
     "孩子们的笑声（远景）+ 温暖的钢琴"),
    ("S42", "agnes", "中景固定", "母亲独自站在窗前，等待",
     "接动态镜：孩子们在林间奔跑",
     "A middle-aged Korean woman {C1} stands alone at a bedroom window in the evening, the glass reflecting faint light, "
     "her face fully visible, calm and steady, quietly looking out toward distant hills; the room behind her is empty and "
     "tidy, no readable text. Static medium shot, slow push-in, " + HOLD,
     "远处的风声 + 极轻的钢琴"),
    ("S43", "agnes", "慢推", "春天的树林，孩子们的身影走入林间小路",
     "接信息卡：案件至今未找到凶手",
     "A spring forest path at dawn, dew on the grass, a few small figures seen only from far behind walking together "
     "into the trees, backpacks on their shoulders; no faces, no readable signs. Slow push along the path, " + HOLD,
     "晨鸟鸣叫 + 轻柔的环境音"),
    ("S44", "graphic", "信息卡（静帧）", "结论卡：案件至今未找到凶手",
     "接动态镜：晨光中的林间",
     "结论卡：一九九一年三月二十六日失踪 / 二〇〇二年九月发现遗骸 / 案件至今未找到凶手",
     "低音收尾"),
    ("S45", "agnes", "远景固定", "晨光中的卧龙山，鸟飞过树林",
     "片尾：淡出",
     "Dawn light over Mount Waryong in spring, the pine ridges rising out of soft mist, a flock of small birds flying "
     "across the sky above the trees, no people, no readable signs. Static wide shot, the image slowly fades to black, "
     + HOLD,
     "鸟鸣 + 渐弱的钢琴"),
]

# 信息卡页眉/页脚
CARD_HEADER = "案件档案  /  韩国大邱 · 一九九一至二〇〇二"       # 每张信息卡左上角的小字
CARD_FOOTER = "公开报道口径 · 并非原始档案影像"                   # 每张信息卡左下角的小字
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S02": ("青蛙少年失踪案", "韩国大邱 · 一九九一年三月二十六日", "五名儿童失踪 · 十一年后遗骸被发现"),
    "S13": ("媒体的误读", "他们被说成是去找青蛙", "“青蛙少年”的名字由此而来"),
    "S14": ("蝾螈卵", "其实，他们是去找蝾螈卵", "“青蛙少年”是一个误会"),
    "S27": ("两种说法", "警方一度认为是失温", "法医团队在颅骨上发现外力损伤，认定为他杀"),
    "S34": ("风雨改写了现场", "警方当年的判断与法医的结论并不相同", "案件仍未找到凶手"),
    "S40": ("五个名字", "金永奎 · 赵浩延 · 金钟植 · 朴灿仁 · 禹哲元", "失踪时年龄九至十三岁"),
    "S44": ("结论", "一九九一年三月二十六日失踪", "二〇〇二年九月发现遗骸 · 案件至今未找到凶手"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["青蛙少年失踪案", "一个没有回家的春天 · 大邱 1991"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "他们，还在等我们记住。",
    "青蛙少年失踪案 · 一九九一至二〇〇二 · 五名儿童失踪",
    "有些故事结束于答案，有些故事结束于人们永远不会忘记。",
    "资料：韩国中央日报 / 首尔经济新闻 / 东亚日报 / 每日经济 / iDaegu / 维基百科 · 原创解说 · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词）
CAPTION_KEYWORDS = [
    "青蛙少年", "大邱", "卧龙山", "一九九一年三月二十六日", "金永奎", "赵浩延", "金钟植", "朴灿仁", "禹哲元",
    "蝾螈卵", "三十五万", "十一年", "二〇〇二年九月二十六日", "遗骸", "失温", "他杀", "颅骨", "DNA",
    "二〇〇六年三月二十五日", "追诉期", "没有找到凶手", "一个没有回家的春天",
]
# 逐镜标签覆盖：默认镜头标「AI动画情景重现 · 非新闻影像」，办案/鉴定/纪念镜头写得更具体
LABEL_OVERRIDES = {
    "S01": "AI动画情景重现 · 非新闻影像",
    "S05": "AI动画情景重现 · 非本人容貌",
    "S12": "AI动画情景重现 · 非档案影像 · 非本人容貌",
    "S14": "AI动画情景重现 · 非警方档案影像",
    "S17": "AI动画情景重现 · 非新闻影像 · 非本人容貌",
    "S20": "AI动画情景重现 · 非电视实拍",
    "S24": "AI动画情景重现 · 非现场实拍",
    "S26": "AI动画情景重现 · 非现场影像",
    "S28": "AI动画情景重现 · 非鉴定影像 · 非本人容貌",
    "S30": "AI动画情景重现 · 非档案影像 · 非本人容貌",
    "S33": "AI动画情景重现 · 非家属影像 · 非本人容貌",
    "S35": "AI动画情景重现 · 非鉴定影像 · 非本人容貌",
    "S39": "AI动画情景重现 · 非纪念活动实拍 · 非本人容貌",
    "S42": "AI动画情景重现 · 非家属影像 · 非本人容貌",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S12", "phone"),
    ("S14", "paper"),
    ("S17", "paper"),
    ("S28", "paper"),
    ("S30", "paper"),
    ("S35", "machine"),
    ("S11", "keys"),
    ("S24", "press"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "一九九一年的一个春天，五个孩子去山里找蝾螈卵，再也没有回家",
    "韩国大邱青蛙少年失踪案：三十五万人次搜山，十一年后才找到他们",
    "他们还在等我们记住：青蛙少年失踪案，案件至今没有找到凶手",
]
HOOK = ("一九九一年三月二十六日，韩国大邱五个小学生放学后去附近的卧龙山找蝾螈卵，再也没有回家。"
        "警方与军队动用了约三十五万人次搜山，十一年后，一个上山采橡子的人发现了他们的遗骸。"
        "法医认定他们是被杀害的，可案件至今没有找到凶手。")
GOLDEN_LINES = [
    "他们只是普通的小学生，有自己的兴趣，也有等着他们回家吃饭的父母。",
    "媒体误把他们说成是去找青蛙，于是他们被叫作青蛙少年。",
    "有些故事结束于答案，有些故事结束于人们永远不会忘记。",
]
DESCRIPTION = (
    "一九九一年三月二十六日，韩国大邱成西小学的五名学生（金永奎、赵浩延、金钟植、朴灿仁、禹哲元）放学后去卧龙山，"
    "他们是去找蝾螈卵，媒体误报为青蛙，于是被叫作青蛙少年。"
    "失踪之后，警方与军队动用约三十五万人次搜山，家长们坚持寻找了多年。"
    "二〇〇二年九月二十六日，一名采橡子的人在卧龙山的一处荒地发现了遗骸，经 DNA 鉴定确认为这五名孩子。"
    "警方当年一度认为是失温，法医团队则在颅骨上发现外力损伤，认定为他杀。"
    "二〇〇六年三月二十五日公诉时效届满，案件至今没有找到凶手。"
    "本片画面为AI生成的情景重现（非新闻影像、非本人容貌），五名孩子全程不露正脸，事实依据公开报道整理。"
)
QUESTION = "如果当年的搜索能再细一点，那五个孩子会不会早一点回家？评论区聊聊。"
HASHTAGS = ["#悬疑", "#真实案件", "#韩国", "#青蛙少年", "#未解之谜"]

GRID = 4            # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 6   # 每个镜头实际请求的时长（智谱 CogVideoX-Flash 免费档单条约 5–6 秒，render 按需裁切）
SEED_BASE = 19910326  # 失踪日（一九九一年三月二十六日），让 seed 可追溯

# 露脸镜头登记（镜头号 -> 角色 id）：只有这里登记的镜头允许出现面容 token，
# 与 cast.json 的 shots 映射一一对应（face_cast.py check-prompts 两边都查）。
# 注意：五名儿童不在 cast.json 里，全片不给任何孩子面容 token。
FACE_SHOTS = {
    "S05": ["C5"],
    "S11": ["C1"],
    "S12": ["C2"],
    "S17": ["C2"],
    "S20": ["C1"],
    "S22": ["C2"],
    "S24": ["C1"],
    "S26": ["C6"],
    "S28": ["C4"],
    "S30": ["C3"],
    "S29": ["C4"],
    "S38": ["C3"],
    "S33": ["C2"],
    "S35": ["C4"],
    "S39": ["C5"],
    "S42": ["C1"],
}
# 用定妆照做首帧（图生视频）的镜头：免费档 image_url 队列实测拥堵，本片不挂任何首帧图。
REFERENCE_SHOTS = {}
FIRST_FRAME = {}


def first_frame_urls():
    base = "https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/arena/8de8f931-desktop-tutorial/production/frogboy1991/"
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
    story["branch"] = "arena/8de8f931-desktop-tutorial"
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
        "露脸模式：大人正脸、五名儿童全程不露正脸（不给任何面容 token）；"
        "面容 token 只在 cast.json 里写一份，build_story.py 用占位符注入，保证逐字节一致；"
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

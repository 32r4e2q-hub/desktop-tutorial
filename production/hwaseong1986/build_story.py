#!/usr/bin/env python3
"""《李春才：华城连环杀人案，DNA揭开了33年的秘密》的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

这是这部片子**唯一需要动脑写的文件**（模板来自 production/templates/build_story.py，
参考实现 production/zama2017/ —— 露脸模式的上一部片子；内容按用户上传的 40 镜文案稿改写，
事实按 10 条公开来源核对，见 SOURCES 与 史实核对.md）。

用法::

    python3 production/hwaseong1986/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/hwaseong1986/build_story.py --script   # 生成 抖音脚本.md（3 标题 / 核心爆点 / 四列分镜表 / 金句）
    python3 production/hwaseong1986/build_story.py --publish  # 生成 抖音发布文案.md（标题 / 介绍 / 提问读者一句话 / 话题）

本片是**露脸模式**：五个角色各一张不同的脸，同一角色跨镜头逐字节复用同一条面容 token
（token 只在 cast.json 里写一份，本文件用 {C1}/{C2}/{C3}/{C4}/{C5} 占位符注入，保证逐字节一致），
并复用同一个 seed；由 production/face_cast.py 的 check-prompts / check-frames 两道闸门守着。
用户的三条硬要求：**3D 动画视频（不是图片视频）、人物鲜活（不同人物不同脸、同一人物同一张脸）、
动作幅度大（中景/全景 + 明确动作 + 运动镜头，不要人脸特写糊弄）**。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "李春才：华城连环杀人案，DNA揭开了33年的秘密"

# 全片统一的画面风格前缀（英文）。写实 3D CGI 情景重现（不是 2D、不是图片轮播）——
# 用户明确要求「3D 动画视频，不是图片视频」。人物动作给足（full-body movement /
# expressive gesture / medium and wide shots），呼应「动作幅度大一些、不要只是人脸特写」。
# 注意：style_prefix 参与全部 Agnes 镜头的 request_hash，开工后改一个字 = 38 镜全部重做。
STYLE_PREFIX = (
    "Photorealistic cinematic 3D animated reenactment, high-end CGI feature-film render with volumetric light, "
    "physically based materials, shallow depth of field and subtle 35mm film grain, of South Korea between 1986 "
    "and 2020: quiet Gyeonggi-do countryside of rice paddies, narrow dirt roads and low tile-roofed houses, "
    "ageing small-town streets with dim sodium lamps, plain 1980s Korean police stations, laboratories and "
    "courtrooms, modern forensic laboratories and news conference rooms, overcast daylight and cold winter sun, "
    "restrained desaturated teal-and-grey colour grading, slow-burn true-crime documentary mood, "
    "never stylised, never a drawing, never a cartoon; horizontal 16:9 widescreen cinematic composition; "
    "characters act with clear full-body movement and expressive gesture, staged in medium and wide shots "
    "rather than close-ups - a face is shown only where a shot explicitly names one of the cast characters, "
    "and never as a recognisable real person or a likeness of anybody living or dead; absolutely no readable "
    "text, letters, numbers, logos, license plates or brand marks anywhere inside the frame; one single "
    "continuous smooth camera move per shot exactly as directed. "
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
    "全部 Agnes 镜头为写实 3D CGI 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，不冒充搜查、审讯、庭审、监控或证物照片",
    "不展示遗体、血腥或作案过程；作案手法与受害者私密画面一律不写不拍；现场镜头只出现警戒线、远处勘查背影与取证空镜",
    "李春才、尹成汝等真实人物均不做肖像还原：一九八六至一九九四年的情景重现由虚构匿名角色 C1（年轻时期）扮演，二〇一九年后的李春才只给背影；尹成汝的二〇二〇年镜头只给背影，一九八八年镜头由 C2 扮演",
    "五个露脸角色（年轻男子 / 年轻嫌犯 / 老刑警 / 重查组警官 / 女法医）各有一张不同的脸；同一角色跨镜头逐字节复用同一条面容 token 并共用同一个 seed",
    "由 production/face_cast.py 的 check-prompts（静态闸门）与 check-frames（画面闸门）检查，人眼对照接触表判决",
    "受害者不以具备可辨识面容的人像出现：只以远景背影、剪影或聚合数字出现，不出现遗体、不出现可辨识面容",
    "每一句事实都能指到 sources 里的一条公开来源；口径冲突处（尹成汝假释年份）只写「坐了二十年牢」，不挑一个当结论",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写；画面内不出现任何可读文字、门牌或招牌（AI 街景必编字，靠构图排除）",
    "人工检视 qa/ 接触表与 delivery/face-cast/ 人脸接触表；换脸、畸变、伪文字、中途换场的镜头用 {\"only\":\"Sxx\"} 重生成，不直接进成片",
]

# 每条事实的公开来源。
SOURCES = [
    {"id": 1, "url": "https://zh.wikipedia.org/wiki/%E8%8F%AF%E5%9F%8E%E9%80%A3%E7%92%B0%E6%AE%BA%E4%BA%BA%E6%A1%88",
     "usage": "支撑：一九八六年九月十五日至一九九一年四月三日十起奸杀；首案七十一岁女性；动员两百零五万人次、排查两万一千二百八十名嫌疑人、鉴定五百七十组DNA/一百八十根毛发/四万零一百一十六枚指纹；"
              "二〇一九年九月十九日警方宣布DNA比中第五、七、九案，组织五十七人独立调查组；十月一日承认九起、十月四日承认第八起；共承认十四起谋杀与约三十起性犯罪；"
              "二〇〇六年四月三日最后一起追诉时效届满；第八案当年被认定为模仿作案；李春在一九六三年一月三十一日生于华城郡"},
    {"id": 2, "url": "https://www.cnn.com/2020/11/02/asia/hwaseong-serial-killer-guilt-intl-hnk",
     "usage": "支撑：二〇二〇年十一月二日水原地方法院重审中李春才以证人身份承认谋杀十四名女性与女孩、说出「我是真凶」；称当年被问询时身上带着受害者手表却因未带身份证被放走；"
              "对没早点被抓感到意外； authorities concluded Lee was responsible for all 10 killings between 1986 and 1991"},
    {"id": 3, "url": "https://www.cnn.com/2020/07/03/asia/south-korea-hwaseong-apology-intl-hnk",
     "usage": "支撑：二〇二〇年七月二日京畿南部地方警察厅厅长 Bae Yong-ju 宣布李春才对一九八六至一九九一年十起命案负责；警方为调查失误公开致歉；"
              "李春才供认华城十起、另外四起谋杀与三十四起强奸；七名警察与一名检察官因滥权与非法拘留被正式调查（追诉时效已过无法起诉）；一九九四年因强奸并杀害妻妹（小姨子）服无期徒刑"},
    {"id": 4, "url": "https://edition.cnn.com/2020/12/17/asia/hwaseong-south-korea-not-guilty-intl-hnk",
     "usage": "支撑：二〇二〇年十二月十七日水原地方法院法官 Park Jeong-je 裁定尹成汝无罪；认定警方以包括睡眠剥夺在内的刑求与非法拘禁取得其一九八八年命案口供"},
    {"id": 5, "url": "https://www.scmp.com/week-asia/people/article/3108241/south-koreas-hwaseong-murders-culprit-admits-14-killings",
     "usage": "支撑：李春才在法庭承认十四起杀人并向蒙冤入狱二十年的尹成汝道歉；二〇〇六年追诉时效届满无法起诉；韩国二〇一五年废除谋杀追诉时效但不溯及既往；"
              "案件是二〇〇三年奉俊昊电影《杀人回忆》的原型"},
    {"id": 6, "url": "https://www.businessinsider.com/south-korea-hwaseong-murders-lee-chun-jae-confession-2019-10",
     "usage": "支撑（转引联合通讯社）：二〇一九年十月一日李春才承认华城十起中的九起及另外五起谋杀，同时承认约三十起强奸或强奸未遂；"
              "九次入狱会面的犯罪侧写专家建立信任后他改变态度；因一九九四年强奸并杀害妻妹在狱中服无期徒刑"},
    {"id": 7, "url": "https://www.chinanews.com/gj/2020/12-17/9364410.shtml",
     "usage": "支撑：二〇二〇年十二月十七日水原地方法院重审宣判尹成汝无罪，裁判部为调查机关不实行为致歉；第八案当年被认定为模仿犯罪；"
              "尹成汝服刑二十年后于二〇〇九年假释；李春才承认的十四起杀人罪行与三十多起性犯罪公诉时效均已过期"},
    {"id": 8, "url": "http://china.hani.co.kr/arti/politics/8920.html",
     "usage": "支撑：水原地方法院刑事十二庭（审判长朴正济）以证人身份传讯李春才；尹某服刑二十年后于二〇〇九年假释、二〇一九年十一月声请再审；"
              "一九八七年十二月华西站女高中生、一九九一年一月清州女高中生、一九九三年三月清州主妇命案亦被断定是李春才所为"},
    {"id": 9, "url": "https://www.hankookilbo.com/news/article/201910161220048558",
     "usage": "支撑：锁定李春才的关键是暴力罪犯DNA采集与国家DNA数据库比对；案件直接推动韩国《DNA鉴定信息利用与保护法》（DNA法）修订讨论，"
              "国会以防止「第二个李春才」为由立法延续强力犯罪人DNA采集"},
    {"id": 10, "url": "https://en.wikipedia.org/wiki/Hwaseong_serial_murders",
     "usage": "支撑（英文框架）：十起受害者均为夜归女性；李春才自一九九四年起在釜山教导所服无期徒刑；案件促使韩国扩张DNA数据库"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。六段合计 ≈ 760 字（含标点）。
CHAPTERS = [
    ("N01", "黄金开头：真凶已经在监狱里",
     "二零一九年九月，韩国警方宣布，一桩尘封三十三年的连环杀人案，终于出现了DNA线索。"
     "可线索指向的那个人，已经在监狱里服刑了二十五年。他叫李春才。"
     "这起案件，就是华城连环杀人案。DNA，这项当年的弱项技术，三十三年后开了口。而真相浮出水面的时候，另一个坐了二十年冤狱的人，也终于等到了被看见的一天。"),
    ("N02", "黑暗年代：四年零七个月的恐惧",
     "时间回到一九八六年九月，京畿道华城郡，还是一片安静的乡村，住着二十多万人。"
     "九月十五日，一位七十一岁的老人遇害。此后，类似的命案接连出现。"
     "从一九八六年到一九九一年，四年零七个月，十位女性接连遇害，最小的只有十三岁。"
     "天黑了，村民们早早关紧门窗。"),
    ("N03", "调查走入歧途：一次不实的调查",
     "警方投入两百多万人次，排查了两万多名嫌疑人，鉴定了五百七十组DNA，却始终没能锁定真凶。"
     "一九八八年九月，一名十三岁女孩遇害，警方认定这是模仿作案。"
     "二十出头的尹成汝被判处无期徒刑。调查记录堆成了山，真凶却始终藏在人海里。一次不实的调查，让无辜的人失去了二十年自由。"),
    ("N04", "真相浮现：九次入狱会面之后",
     "原来，真凶早就关在监狱里。一九九四年一月，李春才因杀害妻子的妹妹被捕，随后被判终身监禁。"
     "警方先后九次到监狱见他。二零一九年十月一日，他承认了华城十起命案中的九起，四天后，又承认了剩下那起。"
     "他也在证物上留下了DNA，只是当年比对不了。他还供认了另外四起谋杀，和三十多起性犯罪。"),
    ("N05", "第二个真相：迟到了二十年的清白",
     "二零二零年十一月，李春才以证人身份站上法庭，只说了一句：我就是真凶。"
     "同年十二月十七日，水原地方法院宣判尹成汝无罪。法官当庭致歉，说当年的调查机关用不实行为，做出了错误的判决。"
     "判决书可以改写，人生却改不回来。二十年牢狱，一句道歉，换不回一个人最好的年华。"),
    ("N06", "结尾：三十三年后的答案",
     "可是，李春才无法被起诉。二零零六年四月，追诉时效已经届满；"
     "韩国二零一五年废除了谋杀案的追诉时效，却来不及保护三十三年前的受害者。"
     "这起案件推动了韩国的DNA立法，也被拍成电影《杀人回忆》，警醒一代人。每一份没丢的证物，都可能在某天开口。"
     "真相可以迟到，但不该让无辜者买单。"),
]

HOLD = ("no cut, no scene change, no camera relocation, no second location, no extra people, "
        "no readable text anywhere in frame; hold on this single view for the full clip.")

SHOTS = [
    # ---------------- N01（8 镜：7 agnes + 1 信息卡）----------------
    ("S01", "agnes", "缓慢前推", "钩子：2019年警察局深夜重启旧案",
     "接信息卡：案件名片",
     "A night-time modern South Korean police investigation office in 2019 lit only by desk lamps: four "
     "investigators in plain dark clothes seen from behind and in silhouette leaning over a large table stacked "
     "with yellowed old case files, one of them gesturing with a pen over a spread file while another slides "
     "papers across the table, hand-drawn maps pinned to a board on the wall behind them, coffee cups and a "
     "desk telephone at the edge of the table; the room is otherwise plain with grey walls, no windows, no "
     "signage, no lettering anywhere. Slow push toward the table, " + HOLD,
     "纸张翻动 + 低频悬念音"),
    ("S02", "graphic", "信息卡（静帧）", "名片：案名 / 地点与年代 / 规模",
     "接 AGNES：监狱走廊里的背影",
     "案件名片：案名 / 地点与年代 / 规模",
     "低音撞击"),
    ("S03", "agnes", "从走廊向牢房缓慢推进", "嫌疑人：铁门后的背影",
     "接 AGNES：旧案卷宗特写",
     "A dim prison corridor in 2019 seen at chest height: a barred cell door slowly swinging shut in the "
     "foreground, and deeper along the corridor a middle-aged man in a grey prison uniform sitting alone on the "
     "edge of a cot with his back to the camera, head slightly bowed, one hand resting on his knee; bare "
     "concrete walls, a single caged bulb overhead, no windows, no signage, no lettering, no other people. "
     "Slow push from the corridor toward the cell, " + HOLD,
     "铁门碰撞 + 低频悬疑音"),
    ("S04", "agnes", "卷宗特写缓慢拉焦", "旧案卷宗与打字机",
     "接 AGNES：1980年代乡间警戒线",
     "A close view of an old Korean police case file on a dark wooden desk: a thick buff-coloured dossier with a "
     "faded photograph tucked under a rubber band, a small unmarked paper evidence bag, a vintage black "
     "typewriter with a sheet half rolled into it, an ashtray and a desk lamp throwing a warm pool of light; "
     "all paper is blank with no readable writing anywhere, no people in frame. Slow rack focus from the "
     "typewriter to the dossier, " + HOLD,
     "一声沉重鼓点"),
    ("S05", "agnes", "低机位沿道路前移", "回闪：1980年代乡间警戒线",
     "接 AGNES：冤狱者牢房（露脸 C2）",
     "A low tracking view along a deserted 1980s South Korean rural road under a flat overcast sky: tall dry "
     "grass and a rice paddy on one side, a weathered concrete utility pole, and a length of yellow-and-black "
     "police tape strung between two wooden posts trembling in the middle distance, the red and blue glow of an "
     "unseen police light washing faintly across the wet asphalt; no vehicles, no people, no signage. Low "
     "camera moving slowly forward along the road, " + HOLD,
     "风声 + 远处警笛"),
    ("S06", "agnes", "从铁栏外缓慢推近", "无辜者：铁窗后的年轻人（C2 首次露脸）",
     "接 AGNES：现代法医实验室",
     "A narrow prison cell in the early 1990s seen from outside the bars: {C2}, sitting on the edge of a thin "
     "bed with his back against the wall, knees drawn up, gazing out through a small barred window at a pale "
     "strip of daylight, his face tired and drawn, one hand hanging beside the bed; bare grey walls, a folded "
     "blanket, a metal cup, no signage, no lettering, no other people. Slow push in from outside the bars, " + HOLD,
     "低沉弦乐渐起"),
    ("S07", "agnes", "证物特写切到DNA屏幕", "关键技术：DNA比对",
     "接 AGNES：2019年审讯室",
     "A modern forensic laboratory in 2019: a pair of gloved hands lowering a small unmarked plastic evidence "
     "tube into a silver analysis instrument, and behind them a large flat monitor glowing with an abstract "
     "blue-green DNA sequence trace, work lamps, reagent bottles and a keyboard on the bench; no lettering on "
     "any label or screen, no faces in frame, no other people. Slow move from the gloved hands to the monitor, " + HOLD,
     "仪器提示音 + 音乐短暂停顿"),
    ("S08", "agnes", "固定中景缓慢推进", "审讯：背对镜头的服刑人员",
     "接 N02：1986年的华城乡村",
     "A plain modern interrogation room in 2019: a middle-aged man in a grey prison uniform sitting with his "
     "back three-quarters to the camera on one side of a metal table, shoulders stiff, hands flat on the "
     "tabletop, facing two investigators in dark jackets seen only from behind on the far side, one of them "
     "sliding a thin file folder across the table; white walls, a ceiling camera, a glass of water, no signage, "
     "no lettering. Fixed medium shot with a slow push in, " + HOLD,
     "空调低鸣 + 时钟滴答"),

    # ---------------- N02（7 镜：6 agnes + 1 信息卡）----------------
    ("S09", "agnes", "横向缓慢扫过乡间", "1986年的华城郡乡村",
     "接 AGNES：田埂警戒线",
     "A wide daylight view of the South Korean countryside in Hwaseong County, September 1986: terraced rice "
     "paddies heavy with ripe heads, low whitewashed houses with grey tile roofs, a narrow dirt road winding "
     "between them, a lone cyclist far away in the middle distance, low cloud and soft morning haze; no "
     "signage, no vehicles in the foreground, no lettering anywhere. Slow lateral pan across the farmland, " + HOLD,
     "蝉鸣 + 汽车驶过声"),
    ("S10", "agnes", "远景缓慢推进", "命案现场：被封锁的田埂",
     "接信息卡：案件开端",
     "A distant view of a paddy dike in autumn 1986 cordoned off with yellow-and-black police tape: three "
     "investigators in dark clothing crouched far away at the edge of the field examining the ground, hats off, "
     "tall rice swaying in the wind, flat grey light; no readable lettering on any object, no body visible, no "
     "other people. Slow push toward the cordon from far away, " + HOLD,
     "风吹稻叶 + 压抑弦乐"),
    ("S11", "graphic", "信息卡（静帧）", "案件开端：第一起命案",
     "接 AGNES：1986年秋夜小路（露脸 C1）",
     "案件开端：日期 / 首位受害者 / 后续",
     "低沉鼓点"),
    ("S12", "agnes", "缓慢横移跟拍", "凶手第一次出现：夜路上的年轻人（C1 首次露脸）",
     "接 AGNES：警察局地图墙",
     "A night view of a narrow dirt path along the edge of rice paddies in Hwaseong in the late 1980s: {C1}, "
     "walking slowly along the path in full frame from head to toe, hands in his jacket pockets, shoulders "
     "relaxed, his face calm and unremarkable, half-lit by a single distant sodium streetlamp, fireflies "
     "glinting over the paddy water behind him, no houses close by, no signage, no other people. Slow lateral "
     "tracking shot moving with him, " + HOLD,
     "虫鸣 + 低频动机首次出现"),
    ("S13", "agnes", "从地图标记横移至档案", "调查：钉满图钉的地图墙",
     "接 AGNES：小镇夜景",
     "The interior of a 1980s South Korean police investigation office at night: a large wall map of the "
     "district studded with coloured pins and knotted string, a long table beneath it piled with paper files, a "
     "detective in shirtsleeves standing at the map with a pencil raised, another figure writing at the table, "
     "green glass-shaded lamps, cigarette smoke in the lamplight; no readable lettering on any map or file, no "
     "faces turned to camera. Slow lateral move from the pinned map across to the files, " + HOLD,
     "铅笔划图 + 低沉鼓点"),
    ("S14", "agnes", "街道远景缓慢推进", "小镇夜景：人人自危",
     "接 AGNES：紧闭门窗的人家",
     "A small South Korean town street at night in the late 1980s: dim sodium streetlamps pooling light on wet "
     "pavement, low shophouses with closed shutters on one side, two or three pedestrians in period coats "
     "hurrying away from camera in the middle distance, and far off the red-and-blue glow of an unseen police "
     "light pulsing on the road surface; no vehicles in frame, no signage, no lettering anywhere. Slow push down "
     "the empty street, " + HOLD,
     "脚步声 + 远处警笛"),
    ("S15", "agnes", "从窗外移向室内", "恐惧：一家人关紧门窗",
     "接 N03：1980年代警察局",
     "The interior of a modest 1980s South Korean home at night seen through a rain-streaked window: a family of "
     "three in period clothing with their backs to camera, a father pushing a wooden bolt across the front "
     "door, a mother drawing a curtain, a child hugging a school bag, one warm tungsten lamp lighting the room, "
     "a wall clock and a plain calendar on the wall; no readable lettering anywhere, no faces turned to camera. "
     "Slow move from outside the window toward the interior, " + HOLD,
     "门锁声 + 时钟滴答"),

    # ---------------- N03（8 镜：7 agnes + 1 信息卡）----------------
    ("S16", "agnes", "缓慢推近他的脸", "老刑警：地图墙前的本部长（C3 首次露脸）",
     "接 AGNES：1988年公交站（露脸 C2）",
     "A crowded 1980s South Korean police investigation office late at night: {C3}, standing square to a large "
     "district map with both palms flat against the wall, a pencil tucked behind his ear, coat over a chair "
     "back, ashtray and coffee cups on a desk beside him, two junior officers bent over files in the "
     "background, harsh overhead fluorescent light, smoke hanging in the air; no readable lettering on the map, "
     "no other people facing camera. Slow push in from the room toward his face over the map, " + HOLD,
     "电话铃 + 打字机声"),
    ("S17", "agnes", "缓慢推近", "1988年：公交站被带走的年轻人（C2）",
     "接 AGNES：老式警察实验室",
     "A rural bus stop at night in 1988 under a single buzzing lamp: {C2}, standing at the edge of the shelter "
     "with a paper ticket clutched in one hand, shoulders tense, glancing sideways as two policemen in 1980s "
     "Korean uniforms with their backs to camera approach from the road, an empty dirt road and dark fields "
     "beyond, a plain wooden shelter post with no signage; no readable lettering, no other people. Slow push in "
     "on the young man, " + HOLD,
     "夜风 + 低频弦乐"),
    ("S18", "agnes", "证物特写缓慢拉远", "当年的技术：显微镜与胶片相机",
     "接信息卡：调查规模",
     "A close view of a 1980s South Korean police laboratory bench: a vintage brass microscope, a film camera "
     "with a leather case, ruled handwritten forms clipped to a board, several small unmarked paper evidence "
     "bags, glass slides in a wooden tray and a desk lamp; hands in white gloves arranging the items from the "
     "edge of frame, no lettering visible anywhere, no faces. Slow pull back from the bench to reveal the whole "
     "desk, " + HOLD,
     "机械运转声 + 音乐渐沉"),
    ("S19", "graphic", "信息卡（静帧）", "调查规模：前所未有的人力",
     "接 AGNES：烟雾缭绕的会议室",
     "调查规模：人力 / 嫌疑人 / 物证鉴定",
     "低音撞击"),
    ("S20", "agnes", "缓慢环绕会议桌", "高压：烟雾缭绕的案情室",
     "接 AGNES：1988年路边警戒线",
     "A cramped 1980s South Korean police meeting room at night: six or seven investigators in shirtsleeves and "
     "ties crowded around a table littered with case files and photographs, one standing with arms folded, "
     "another pointing at a map on the wall, cigarette smoke curling under a bare ceiling light, wall calendar "
     "and corkboard behind them; no readable lettering on any paper, no faces turned fully to camera. Slow "
     "orbit around the meeting table, " + HOLD,
     "低频鼓点 + 翻阅文件声"),
    ("S21", "agnes", "固定远景缓慢推近警戒线", "1988年：路边的警戒线",
     "接 AGNES：法庭被告席（露脸 C2）",
     "A cold overcast afternoon on a 1980s South Korean rural roadside: a length of yellow-and-black police "
     "tape strung across a dirt track between two posts, trembling in the wind, tyre marks and disturbed grass "
     "beside it, three investigators far away in a field examining the ground, bare trees and low hills under a "
     "leaden sky; no body visible, no readable lettering, no other people. Fixed wide shot with a slow push "
     "toward the tape, " + HOLD,
     "风声 + 低沉弦乐"),
    ("S22", "agnes", "从法庭全景缓慢推向被告席", "判决：被告席上的年轻人（C2）",
     "接 AGNES：牢房里流逝的光",
     "A 1980s South Korean courtroom seen from the back of the public gallery: {C2}, sitting upright in the "
     "defendant's dock in a borrowed white shirt, hands clasped on the rail, staring straight ahead, a judge's "
     "raised bench and wooden witness stand in the middle distance, two lawyers in black robes standing, tall "
     "windows with thin daylight; no readable lettering, no other faces turned to camera. Slow push from the "
     "wide courtroom toward the dock, " + HOLD,
     "法庭环境声 + 沉重落槌声"),
    ("S23", "agnes", "固定机位利用光影变化", "岁月：牢房里移动的光",
     "接 N04：1994年审讯室（露脸 C1）",
     "A bare prison cell in the 1990s held in one fixed position: a young man in a grey prison uniform sitting "
     "alone on the edge of the bed with his head bowed, wall paint peeling behind him, a narrow barred window "
     "high on the wall through which a hard bar of daylight creeps slowly across the floor and up the bed, a "
     "folded blanket and a metal cup the only objects; no signage, no lettering, no other people. Static camera "
     "while the light slowly moves, " + HOLD,
     "时钟声 + 低沉钢琴"),

    # ---------------- N04（7 镜：6 agnes + 1 信息卡）----------------
    ("S24", "agnes", "缓慢推进", "1994年：另一起命案被捕（C1）",
     "接 AGNES：监狱外景",
     "A plain 1994 South Korean police interrogation room: {C1}, sitting on a hard chair with his head lowered, "
     "elbows on the table, hands clasped, a plain shirt buttoned to the collar, while a detective's hands in "
     "the foreground slide a thin file folder across the metal table toward him and set down a plastic cup of "
     "water; grey walls, a wall clock, a one-way mirror, no signage, no lettering. Slow push in on the seated "
     "young man, " + HOLD,
     "纸张翻动 + 低沉弦乐"),
    ("S25", "agnes", "缓慢推向监狱大门", "终身监禁：高墙与铁门",
     "接信息卡：李春才档案",
     "The exterior of a heavy South Korean prison under a flat overcast sky in the 1990s: tall grey concrete "
     "walls topped with coiled wire, a closed steel gate in the middle of the frame with a guard post beside "
     "it, bare ground and a single leafless tree, a flagpole with a furled flag; no signage, no lettering, no "
     "people, no vehicles. Slow push toward the prison gate, " + HOLD,
     "铁门声 + 沉重鼓点"),
    ("S26", "graphic", "信息卡（静帧）", "人物档案：李春才",
     "接 AGNES：2019年重查组（露脸 C4）",
     "人物档案：出生 / 罪名 / 服刑",
     "低音撞击"),
    ("S27", "agnes", "从检测报告缓慢推向神情", "2019年：DNA报告对旧档（C4 首次露脸）",
     "接 AGNES：俯拍调查桌",
     "A modern South Korean police office in 2019 at night: {C4}, in a dark navy uniform jacket, standing at a "
     "desk with a printed DNA report held in both hands, comparing it line by line against a stack of yellowed "
     "1980s case files spread beside a glowing monitor, his face lit from below by the screen light, jaw tight, "
     "a second officer blurred behind him; no readable lettering on any document, no other faces to camera. "
     "Slow push from the report up to his face, " + HOLD,
     "仪器提示音 + 悬疑音乐渐强"),
    ("S28", "agnes", "俯拍桌面缓慢扫过", "汇合：DNA、时间线与物证",
     "接 AGNES：2019年新闻发布会（露脸 C4）",
     "A top-down view of a wide investigation table in 2019: a printed DNA comparison report, a long paper "
     "timeline of the 1986-1991 cases with dated tabs, small unmarked evidence bags, a magnifying glass and a "
     "district map with three locations ringed in red pencil, all arranged in neat rows, two pairs of hands in "
     "white gloves moving items into place; no readable lettering anywhere, no faces. Slow overhead pan across "
     "the materials, " + HOLD,
     "翻页声 + 音乐节奏加快"),
    ("S29", "agnes", "从记者席切向发布会讲台", "2019年10月：警方宣布（C4）",
     "接 AGNES：拉远呈现调查桌面",
     "A police press conference room in Seoul in 2019: {C4}, standing at a plain lectern facing camera with "
     "both hands on its edge, expression grave, camera flashes blooming across the frame, rows of reporters "
     "seen from behind with cameras and recorders raised in the foreground, a blue backdrop banner behind him "
     "with no readable lettering; no other identifiable faces. Slow push from the press rows toward the "
     "lectern, " + HOLD,
     "相机快门声 + 新闻现场环境声"),
    ("S30", "agnes", "缓慢拉远呈现完整桌面", "十四起：摊开的全部卷宗",
     "接 N05：空荡的法庭",
     "A wide view of an investigation table in 2019 holding a dozen old case files fanned out beside a district "
     "map of Gyeonggi and North Chungcheong with several locations circled, a wall of pinned photographs and "
     "string behind it going out of focus, one investigator standing at the far end with arms folded; no "
     "readable lettering on any document, no faces turned to camera. Slow pull back to reveal the full table, " + HOLD,
     "低音持续 + 沉重鼓点"),

    # ---------------- N05（8 镜：7 agnes + 1 信息卡）----------------
    ("S31", "agnes", "缓慢推进被告席", "空荡的法庭：程序结束之后",
     "接 AGNES：走出监狱的背影",
     "An empty South Korean courtroom in 2020 in cold flat light: the defendant's dock and the raised judge's "
     "bench facing each other across a polished wooden floor, microphones, water jugs and a stack of white "
     "court files on the bench, tall windows with thin winter daylight, not a person in the room; no readable "
     "lettering anywhere. Slow push toward the empty dock, " + HOLD,
     "空旷回声 + 低音弦乐"),
    ("S32", "agnes", "从背后跟拍逐渐拉远", "出狱：走向阳光的背影",
     "接信息卡：平反",
     "The gate yard of a South Korean prison on a bright morning in 2020: a middle-aged man in a plain dark "
     "coat walking slowly away from camera toward the open gate with a small cloth bag in one hand, morning sun "
     "breaking across the concrete in hard stripes, high walls and wire above him, his figure small against the "
     "light; no readable lettering, no other people in frame. Tracking shot from behind him, slowly pulling "
     "back, " + HOLD,
     "脚步声 + 音乐略微转暖"),
    ("S33", "graphic", "信息卡（静帧）", "平反：无罪宣判",
     "接 AGNES：律师桌面的旧判决",
     "平反：日期 / 法院 / 结论",
     "相机快门声"),
    ("S34", "agnes", "俯拍文件缓慢推近", "重审：旧判决与新调查",
     "接 AGNES：2020年法庭证人席",
     "A top-down view of a lawyer's desk in a modern Seoul law office in 2020: a stack of legal documents with "
     "a yellowed 1989 judgment on top, a newer printed investigation report beside it, reading glasses, a "
     "fountain pen and a highlighter, a pair of hands in a dark sleeve turning the old judgment page by careful "
     "page; no readable lettering anywhere, no faces. Slow overhead push toward the key page, " + HOLD,
     "翻页声 + 轻微钢琴"),
    ("S35", "agnes", "从法庭全景缓慢推进证人席", "2020年：证人席上的真凶",
     "接 AGNES：法院台阶",
     "A South Korean courtroom in 2020 seen from the back of the gallery: a middle-aged man in a grey prison "
     "uniform sitting upright in the witness stand with his back to camera, hands folded on the rail, facing "
     "the judge's bench and two lawyers in black robes standing at their desks, cold daylight from tall "
     "windows, a court clerk seated to one side; no readable lettering, no faces turned to camera. Slow push "
     "from the wide courtroom toward the witness stand, " + HOLD,
     "法庭环境声 + 低沉鼓点"),
    ("S36", "agnes", "从法院台阶缓慢拉远", "宣判之后：法院门口的沉默",
     "接 AGNES：牢房里流逝的光",
     "The front steps of the Suwon District Court building in December 2020 in flat winter light: a middle-aged "
     "man in a dark coat standing still at the top of the steps with his back to camera, a cluster of reporters "
     "with cameras and boom microphones waiting at the bottom of the steps, grey stone columns and a flag on "
     "the roof; no readable lettering anywhere, no faces turned to camera. Slow pull back from the steps, " + HOLD,
     "相机快门声 + 音乐缓慢释放"),
    ("S37", "agnes", "缓慢叠化最后停在空床铺", "代价：翻过的日历与空床铺",
     "接 AGNES：旧判决与DNA报告",
     "A bare prison cell held in one slow move: a hard bed with a folded grey blanket, a metal cup, a barred "
     "window high on the wall, and a hard bar of winter daylight creeping slowly across the floor and up the "
     "empty bed as if hours are passing, peeling paint and a scratched wall; no signage, no lettering, no "
     "people. Slow drift ending on the empty bed, " + HOLD,
     "翻页声 + 缓慢钢琴"),
    ("S38", "agnes", "从旧判决书缓慢移到DNA报告", "并置：冤案卷宗与迟来的证据",
     "接 N06：三十三年信息卡",
     "A dark archive table in 2020 lit by a single lamp: a yellowed 1980s court judgment document on the left, a "
     "modern printed DNA laboratory report on the right, and old case files stacked between them, the lamp "
     "light rising slowly as the scene brightens from shadow to clarity, dust motes in the beam; no readable "
     "lettering on any document, no people. Slow lateral move from the old judgment to the DNA report, " + HOLD,
     "低沉弦乐逐渐舒展"),

    # ---------------- N06（7 镜：5 agnes + 2 信息卡）----------------
    ("S39", "graphic", "信息卡（静帧）", "时间轴：一九八六到二〇一九",
     "接 AGNES：法医实验室（露脸 C5）",
     "时间轴：三十三年 / 起止 / DNA的意义",
     "时钟声逐渐转为电子提示音"),
    ("S40", "agnes", "从证物特写推向检测屏幕", "现代法医：证物再次开口（C5 首次露脸）",
     "接信息卡：追诉时效",
     "A modern forensic laboratory in 2019: {C5}, in a white lab coat and thin glasses, holding a small sealed "
     "evidence tube up to the light with gloved hands, then lowering it into a silver analyser, a monitor "
     "beside her glowing with an abstract blue DNA sequence trace, reagent bottles and a keyboard on the bench; "
     "no readable lettering anywhere, no other people in frame. Slow push from the evidence tube toward the "
     "screen, " + HOLD,
     "仪器提示音 + 音乐渐强"),
    ("S41", "graphic", "信息卡（静帧）", "追诉时效：无法起诉",
     "接 AGNES：关闭的监狱铁门",
     "追诉时效：届满日期 / 后果 / 反思",
     "铁门声 + 低沉长音"),
    ("S42", "agnes", "缓慢拉远留下沉重空镜", "沉重的空镜：关闭的铁门",
     "接 AGNES：档案室的长廊",
     "A heavy closed steel prison gate in flat overcast light, its bars and rivets filling the frame, a cold "
     "empty yard beyond with wet concrete and a single bare tree, the gate immovable and silent; no signage, no "
     "lettering, no people, no vehicles. Slow pull back from the gate, " + HOLD,
     "铁门声 + 低沉长音"),
    ("S43", "agnes", "平稳缓慢拉远", "档案室：整齐排列的旧案",
     "接 AGNES：清晨的乡间道路",
     "A quiet records room in a South Korean police building: rows of grey steel archive shelves holding dozens "
     "of identical buff-coloured case file boxes with blank spines, a narrow aisle running to a lit doorway at "
     "the far end, a bar of daylight sliding slowly along the shelves; no readable lettering on any box, no "
     "people. Slow pull back down the aisle, " + HOLD,
     "庄重弦乐"),
    ("S44", "agnes", "缓慢向前推进", "清晨：薄雾散去的乡间道路",
     "接 AGNES：日出下的田野（最后一镜）",
     "An early morning view of a South Korean rural road in Hwaseong in late autumn: thin ground mist lifting "
     "off the rice paddies, low morning sun burning through the haze in long golden shafts, a narrow road "
     "running straight ahead between the fields, a utility pole and a line of poplars far away; no signage, no "
     "vehicles, no people. Slow forward push into the light, " + HOLD,
     "音乐渐弱"),
    ("S45", "agnes", "缓慢推进最后淡出", "结尾：阳光照进田野",
     "接片尾卡",
     "A wide sunrise view over the South Korean countryside in Hwaseong: golden light flooding across ripe rice "
     "paddies, mist burning off, low houses with tile roofs on the horizon and a single narrow path running "
     "toward them, birds rising over the field, everything calm and open; no signage, no vehicles, no people. "
     "Slow forward push as the light grows, " + HOLD,
     "音乐渐弱，留一秒安静"),
]

# ---------------------------------------------------------------------------
# 画面上的文字（render.py 从 story.json 的 presentation 块读，不在 render.py 里写死）
# ---------------------------------------------------------------------------
CARD_HEADER = "案件档案  /  华城 · 一九八六至二〇一九"      # 每张信息卡左上角的小字
CARD_FOOTER = "公开报道口径 · 并非原始档案影像"                # 每张信息卡左下角的小字
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S02": ("华城连环杀人案", "韩国京畿道 · 一九八六至一九九一", "十起命案 · 三十三年未破"),
    "S11": ("案件开端", "一九八六年九月十五日", "七十一岁女性遇害 · 此后命案接连出现"),
    "S19": ("史上最大规模排查", "两百多万人次 · 两万多名嫌疑人", "五百七十组DNA · 四万多枚指纹"),
    "S26": ("李春才", "一九六三年生 · 华城郡人", "一九九四年因杀害妻妹被判终身监禁"),
    "S33": ("平反", "二〇二〇年十二月十七日", "水原地方法院宣判尹成汝无罪"),
    "S39": ("三十三年", "一九八六 — 二〇一九", "DNA让沉睡的证物重新开口"),
    "S41": ("追诉时效", "二〇〇六年四月三日届满", "无法起诉 · 不等于没有真相"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["华城连环杀人案", "真凶已在狱中 · DNA揭开33年的秘密"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "你能想象吗？",
    "华城连环杀人案 · 一九八六至二〇一九 · 十人遇害",
    "真相可以迟到，但不该让无辜者买单。",
    "资料：维基百科 / CNN / 联合通讯社 · 原创解说 · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词）
CAPTION_KEYWORDS = [
    "三十三年", "DNA", "李春才", "华城连环杀人案",
    "一九八六年九月十五日", "七十一岁", "四年零七个月", "十三岁",
    "两百多万人次", "五百七十组", "模仿作案", "尹成汝", "无期徒刑",
    "终身监禁", "二十五年", "九次", "二零一九年十月一日", "十四起",
    "三十多起性犯罪", "我就是真凶", "二〇二〇年十二月十七日", "无罪",
    "追诉时效", "二零零六年", "杀人回忆", "无辜者买单",
]
# 逐镜标签覆盖：默认 agnes 镜头标「AI动画情景重现 · 非新闻影像」，办案/审讯/庭审/鉴定镜头写得更具体
LABEL_OVERRIDES = {
    "S01": "AI动画情景重现 · 非警方办案影像",
    "S03": "AI动画情景重现 · 非监狱实景",
    "S04": "AI动画情景重现 · 非证物影像",
    "S07": "AI动画情景重现 · 非鉴定影像",
    "S08": "AI动画情景重现 · 非审讯影像",
    "S10": "AI动画情景重现 · 非搜查现场影像",
    "S13": "AI动画情景重现 · 非警方办案影像",
    "S16": "AI动画情景重现 · 非警方办案影像",
    "S17": "AI动画情景重现 · 非抓捕现场影像",
    "S18": "AI动画情景重现 · 非鉴定影像",
    "S20": "AI动画情景重现 · 非警方办案影像",
    "S21": "AI动画情景重现 · 非搜查现场影像",
    "S22": "AI动画示意 · 非庭审影像",
    "S23": "AI动画情景重现 · 非监狱实景",
    "S24": "AI动画情景重现 · 非审讯影像",
    "S25": "AI动画情景重现 · 非监狱实景",
    "S27": "AI动画情景重现 · 非警方办案影像",
    "S28": "AI动画情景重现 · 非鉴定影像",
    "S29": "AI动画情景重现 · 非新闻采访影像",
    "S31": "AI动画示意 · 非庭审影像",
    "S32": "AI动画情景重现 · 非监狱实景",
    "S34": "AI动画情景重现 · 非司法文书影像",
    "S35": "AI动画示意 · 非庭审影像",
    "S36": "AI动画情景重现 · 非新闻采访影像",
    "S40": "AI动画情景重现 · 非鉴定影像",
    "S42": "AI动画情景重现 · 非监狱实景",
    "S43": "AI动画情景重现 · 非档案室实景",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S01", "paper"),
    ("S04", "paper"),
    ("S08", "keys"),
    ("S13", "paper"),
    ("S16", "phone"),
    ("S18", "machine"),
    ("S24", "keys"),
    ("S28", "paper"),
    ("S29", "press"),
    ("S34", "paper"),
    ("S40", "machine"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "真凶在监狱里服刑25年，DNA揭开33年前的韩国华城连环杀人案",
    "韩国华城连环杀人案：10条人命，1人蒙冤20年，真凶早就在狱中",
    "《杀人回忆》原型案件：排查2万嫌疑人，真凶却在监狱里服刑",
]
HOOK = ("一九八六到一九九一年，韩国华城郡四年零七个月发生十起命案；排查两万多名嫌疑人、鉴定五百七十组DNA都扑了空，"
        "真凶李春才其实一直在监狱里服刑，直到DNA比对锁定了第五、七、九案。")
GOLDEN_LINES = [
    "真相可以迟到，但不该让无辜者买单。",
    "十起命案，三十三年，一个坐了二十年冤狱的人。",
    "让证据说话，是这起案件留给韩国刑侦的一课。",
]
DESCRIPTION = (
    "二零一九年九月，韩国警方通过DNA比对锁定了一名正在狱中服刑二十五年的男子李春才，"
    "他就是一九八六至一九九一年华城连环杀人案的真凶。他承认了十起华城命案、另外四起谋杀和三十多起性犯罪，"
    "却因追诉时效届满无法被起诉；当年被误判无期徒刑的尹成汝，在坐了二十年冤狱后于二〇二〇年十二月十七日被判无罪。"
    "本片画面为AI生成的情景重现（非新闻影像），事实依据公开报道整理。"
)
QUESTION = "如果你是当年的调查员，会先查哪一条线索？评论区聊聊。"
HASHTAGS = ["#悬疑", "#真实案件", "#韩国", "#华城连环杀人案", "#案件解说"]

GRID = 4           # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 7  # 每个 Agnes 镜头实际请求的时长（169 帧 @ 24 fps）
SEED_BASE = 19860915  # 首案发日（一九八六年九月十五日），让 seed 可追溯

# 露脸镜头登记（镜头号 -> 角色 id）：只有这里登记的镜头允许出现面容 token，
# 与 cast.json 的 shots 映射一一对应（face_cast.py check-prompts 两边都查）。
FACE_SHOTS = {
    "S06": ["C2"],
    "S12": ["C1"],
    "S16": ["C3"],
    "S17": ["C2"],
    "S22": ["C2"],
    "S24": ["C1"],
    "S27": ["C4"],
    "S29": ["C4"],
    "S40": ["C5"],
}
# 用定妆照做首帧（图生视频）的镜头：每个角色的首次露脸镜头，把这张脸钉在观众第一眼里。
# 定妆照提交在仓库里，URL 取 cast.json 的 portrait_url（Agnes 只在服务器侧取图）。
REFERENCE_SHOTS = {"S06": "C2", "S12": "C1", "S16": "C3", "S27": "C4", "S40": "C5"}


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
        assert kind in ("agnes", "graphic"), f"{sid}: kind 只能是 agnes / graphic"
        start = i * GRID
        prompt = body
        if kind == "agnes":
            for cid, token in face.items():
                prompt = prompt.replace("{" + cid + "}", token)
            assert "{" not in prompt and "}" not in prompt, f"{sid} 提示词里还有没替换的占位符"
        shot = {
            "id": sid, "kind": kind, "start": start, "duration": GRID,
            "narration_id": f"N{min(6, start // 30 + 1):02d}",
            "prompt": prompt if kind == "agnes" else "",
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
        "解说词与 screenplay.md、audio/manifest.json 三处逐字一致由 generate.py --validate 守着。")
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")

    manifest = json.loads(MANIFEST.read_text())
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        assert clip["id"] == chapter["id"]
        clip["text"] = chapter["text"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    kinds = [s["kind"] for s in story["shots"]]
    chars = sum(len(c["text"]) for c in story["chapters"])
    print(f"story.json 已写入：{len(shots)} 镜 = {kinds.count('agnes')} agnes + {kinds.count('graphic')} graphic，"
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
        from script_table import publish_document  # noqa: E402  (同目录)
        out = HERE / "抖音发布文案.md"
        out.write_text(publish_document())
        print(f"抖音发布文案.md 已写入（{len(out.read_text())} 字符）")
    else:
        build()

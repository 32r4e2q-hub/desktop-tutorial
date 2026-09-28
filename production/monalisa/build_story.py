#!/usr/bin/env python3
"""《蒙娜丽莎：行李箱里的779号》的全部内容源：解说词、45 镜分镜、信息卡文案、字幕高亮词、发布文案。

模板来自 production/templates/build_story.py，样板是 production/gilgo/build_story.py
（《吉尔戈海滩：披萨盒里的凶手》，已成片、已过三轮复审）。画风、镜头纪律、信息卡密度、
解说语速全部对齐那部长岛连环案，只换年代与地点。

用法：

    python3 production/monalisa/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/monalisa/build_story.py --script   # 生成 抖音脚本.md（3 标题 / 核心爆点 / 四列分镜表 / 金句）
    python3 production/monalisa/build_story.py --publish  # 生成 抖音发布文案.md（标题 / 介绍 / 提问 / 话题）

本片的三条硬规则（写在 PRINCIPLES 里，也写在每一镜的提示词里）：

- 六段解说合计 890 字上下（含标点），与长岛那部同速：TTS 收紧停顿后约 176 秒，成片整体变速 ≤1.10；
- 数字在解说里一律写中文读法，在信息卡与字幕里可以用阿拉伯数字（卡片是本地渲染的，不经过视频模型）；
- 《蒙娜丽莎》正面永不出现在画面里——只画它的背面、空画框和墙上那四颗钉子。
  这既是红线（AI 复刻名画必然畸变），也是叙事：整部片子讲的就是「缺席」。
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"

TITLE = "蒙娜丽莎：行李箱里的779号"

# 全片统一的画面风格前缀（英文）。前半句是本片的地点/年代/道具，后半句是流水线规则，别删。
# 注意：style_prefix 参与全部 38 个 Agnes 镜头的 request_hash，开工后改一个字 = 38 镜全部重做。
STYLE_PREFIX = (
    "Stylized 2D animated documentary illustration with hand-painted graphic-novel textures and soft "
    "cel shading, Belle Époque Paris and Florence between 1908 and 1914: the Louvre's Salon Carré with "
    "gilded walls hung floor to ceiling with old-master paintings, service stairways of worn stone steps "
    "with black iron balustrades, a glazier's workshop with lead came and putty, cobblestone quays in river "
    "mist, gas lamps, horse carts, wooden travel trunks, a police records room and a Florentine hotel "
    "corridor; horizontal 16:9 cinematic composition, muted palette of slate blue, wet limestone grey, "
    "varnished umber and gaslight amber, overcast August morning daylight or warm gaslit interior, "
    "restrained procedural true-crime mood, no horror excess; every character is shown only from behind, "
    "in silhouette, or as hands and props - never a clear frontal face; the portrait painting itself is "
    "never shown face-on, only its blank wooden back, its empty frame or the bare wall behind it; "
    "absolutely no readable text, letters, numbers, logos, license plates or brand marks anywhere inside "
    "the frame; one single continuous smooth slow camera move per shot exactly as directed. "
)

HOLD = " The entire clip stays in this single framing: no cut, no scene change, no camera relocation."

NEGATIVE_PROMPT = (
    "readable text, letters, numbers, words, signage writing, invented headlines, logos, brand marks, "
    "watermark, subtitles, on-screen caption, photorealistic face, recognizable real person likeness, "
    "frontal face close-up, eyes visible in detail, Mona Lisa face, painted portrait front, mona lisa "
    "reproduction, blood, gore, wound, corpse, autopsy, violence, assault, weapon, gun, firearm, nudity, "
    "modern era, 21st century, contemporary clothing, cars, asphalt road, power lines, neon, smartphone, "
    "electric signage, skyscraper skyline, horror monster, ghost, jump scare, 3D render look, plastic CGI, "
    "distorted anatomy, deformed hands, extra fingers, extra limbs, duplicated people, changing face, "
    "morphing objects, teleportation, jitter, flicker, whip pan, fast zoom, jump cut, split screen, collage"
)

PRINCIPLES = [
    "全部 Agnes 镜头为风格化 2D 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」；"
    "警局、取证、庭审、运输类镜头单独写明「非档案影像 / 非庭审影像」，不冒充历史照片",
    "《蒙娜丽莎》正面不进入任何一镜：只画空墙上的四颗铁钉、被卸下的画框与玻璃罩、画板背面。"
    "一层是避免 AI 复刻名画的畸变与冒用，一层是本案的视觉母题本来就是「缺席」",
    "网络流传的「一根白杨木纤维比对成功、把他钉死」查无档案依据，本片把它作为「流传版本」明确打假；"
    "真实的定案依据只写成有来源的「画板背面的卢浮宫馆藏编号 INV 779」",
    "不美化犯罪：不写「高智商犯罪」「绅士大盗」；佩鲁贾是无名油漆工，作案过程写成「简单到离谱」而不是「精妙」",
    "不指认同伙：瓦尔费尼奥幕后说只存在于报刊传闻，本片不提；搜家、指纹、审判只写有来源的部分",
    "每一句事实都能指到 sources 里的一条公开报道；数字与刑期记载不一致时用「约」或「一说」",
    "所有中文姓名、日期、编号、字幕一律后期添加，不交给视频模型拼写（提示词里同时禁止画面出现可读文字）",
    "同一地点保留光线、道具、运动方向；跨地点用物件（四颗钉子、白色工作服、木箱、空画框）做匹配衔接",
    "人工检视 qa/ 接触表：换场、露脸、伪文字、画出名画正面、木箱形状变样的镜头，"
    "用 only=Sxx 重新生成或改 render.py 的 WINDOWS / TIGHTER_CROPS，不直接进成片",
]

SOURCES = [
    {"id": 1, "url": "https://en.wikipedia.org/wiki/Vincenzo_Peruggia",
     "usage": "支撑：1911-08-21 约 07:00 穿白工作服走员工通道；画从四颗铁钉上取下；在七米楼梯间卸掉玻璃罩与画框；"
              "水管工替他开门；藏在自己公寓两年；1913-12 与杰里、波吉接头后在旅馆被捕；身高 160cm；"
              "他留下拇指指纹、卢浮宫员工都采了指纹却漏掉他、名字没进待查清单"},
    {"id": 2, "url": "https://www.smithsonianmag.com/arts-culture/stolen-how-the-mona-lisa-became-the-worlds-most-famous-painting-16406234/",
     "usage": "支撑：1910 年来自维也纳的威胁信让卢浮宫给珍品加玻璃罩，工程包给科比尔（Cobier）玻璃公司，佩鲁贾是其工人；"
              "藏在寄宿房间木箱的假底板里；1911-11 被警方问话时称前一晚喝多了，警方采信；"
              "警员把报告写完时正靠在那张桌子边；转而逮捕毕加索与阿波利奈尔；1913-12 提箱去佛罗伦萨被捕；"
              "盗窃把它抬成世界最出名的画"},
    {"id": 3, "url": "https://www.thoughtco.com/mona-lisa-stolen-1779626",
     "usage": "支撑：次日才被准备临摹的画家发现；60 名警察搜查卢浮宫；请来指纹专家阿尔方斯·贝尔蒂永；"
              "他在画框上找到一枚拇指指纹但对不上任何档案；案发时间被压缩在 07:00–08:30；"
              "当值保安因孩子出疹在家、替班者 8 点离岗抽烟；画框与玻璃在楼梯间被发现"},
    {"id": 4, "url": "https://www.bbc.com/news/magazine-25241576",
     "usage": "支撑：1913-12-10 交还时被杰里与警方当场控制；卢浮宫闭馆一周；画面尺寸 53×77cm；"
              "劣质油漆与铅中毒让他做不动装修工；判一年零十五天、减到七个月零九天；动机至今有争议"},
    {"id": 5, "url": "https://www.guinnessworldrecords.com/news/2023/5/the-curious-story-of-the-man-who-stole-the-mona-lisa-749918",
     "usage": "支撑：他星期天傍晚溜进馆、藏在储物间过夜；周一开馆前动手；两年后想把画变现，联系佛罗伦萨画商；"
              "波吉鉴定后报警，在旅馆逮捕；判决后仅短期服刑"},
    {"id": 6, "url": "https://www.noiser.com/short-history-of/how-a-daring-heist-made-the-mona-lisa-the-most-famous-painting-in-the-world",
     "usage": "支撑：1913-11-29 杰里收到署名 Leonardo Vincenzo 的信，索要 50 万里拉；杰里约来乌菲兹馆长乔瓦尼·波吉；"
              "旅馆房间里他从木箱里取出画；两人把画对着光看背面，确认是卢浮宫的馆藏编号，才认定不是赝品"},
    {"id": 7, "url": "https://www.thehistoryofart.org/leonardo-da-vinci/mona-lisa/",
     "usage": "支撑：卢浮宫馆藏编号 INV 779（MR 316）；油彩、白杨木画板，79.4×53.4cm；现陈列于 Denon 翼 711 展室"},
    {"id": 8, "url": "https://www.walksinrome.com/italy-florence-return-of-the-mona-lisa.html",
     "usage": "支撑：1913-12-10 抵佛罗伦萨，住潘扎尼街 Tripoli-Italia 旅馆；在 20 号房当众掀开木箱假底板；"
              "名画先在意大利巡展，1914-01-04 回到卢浮宫"},
    {"id": 9, "url": "https://www.auxtroiscrayons.com/home/2019/7/7/the-theft-of-the-mona-lisa",
     "usage": "支撑：科比尔玻璃公司 1910–1911 为数千幅画加装护罩，佩鲁贾参与；画藏在木箱假底板里，一直没离开巴黎；"
              "被捕前先试图卖给伦敦经销商（杜维恩）；巴黎警方当年只采集了他的右手，而现场留下的是左手拇指印；"
              "多项证词与审讯材料都指向单独作案，无同伙证据"},
    {"id": 10, "url": "https://www.jiemian.com/article/3480878.html",
     "usage": "支撑（中文报道）：当时最前沿的指纹鉴定；从相框上取得一枚嫌犯拇指指纹，与 256 名卢浮宫工作人员比对全部落空；"
              "警方后来召集所有外包工人来按手印，佩鲁贾是唯一没来的那个"},
    {"id": 11, "url": "https://www.thepaper.cn/newsDetail_forward_23105614",
     "usage": "支撑（中文报道）：《蒙娜丽莎》的保护框与玻璃罩就是他做的，所以能几分钟卸开、并把罩子整齐丢弃在楼梯口；"
              "巴黎警方搜查他公寓一无所获，画就在他们眼皮底下藏了近两年"},
    {"id": 12, "url": "https://www.history.com/this-day-in-history/august-22/theft-of-mona-lisa-is-discovered",
     "usage": "支撑：8 月 22 日被发现；举国震动、德国人偷画的传闻；轮船与乘客被查；他自称替拿破仑复仇、把画还给意大利；"
              "随身日记里有美国收藏家的名单，说明他考虑过出售；服刑七个月"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。合计 ≈ 890 字（含标点），与长岛那部同速。
CHAPTERS = [
    ("N01", "黄金开头：墙上只剩四颗钉子",
     "一九一一年八月二十一日，星期一，卢浮宫闭馆。早上七点，一个穿白色工作服的油漆工从员工通道走进去，没人多看他一眼。七点一刻，他把全世界最有名的一幅画，从四颗铁钉上取下来，抱着它走下员工楼梯，走出了大门。卢浮宫过了一整天才发现画没了。没有枪，没有人质，没有警报。他怎么做到的，又是怎么栽的，今天一口气讲清楚。"),
    ("N02", "案件背景：给名画装玻璃的人",
     "先说他是谁。文森佐·佩鲁贾，意大利移民，一八八一年生，身高一米六，在巴黎靠刷漆和镶玻璃为生。一九零八年，卢浮宫给最贵重的几幅画加装防碎玻璃罩，工程包给一家玻璃公司，他就是其中一个工人。《蒙娜丽莎》那个罩子，很可能就是他装的：他知道钉子怎么卸，知道周一闭馆，知道保安几点抽烟。而他之前两次被捕，指纹早就在警局档案里。"),
    ("N03", "作案手法：一晚上加十五分钟",
     "他的计划简单到让人无语。星期天傍晚，他混在收工的维修工里进门，躲进展厅旁边的储物间，在一堆画框中间过了一夜。星期一早上，他把白工作服扣到最上面一颗，等展厅空了，把画从钉子上取下，抱到隔壁楼梯间，卸下玻璃罩和画框，丢在拐角。然后把画裹进工作服，夹在胳膊底下。一个水管工以为他是同事，顺手替他开了门。"),
    ("N04", "破案关键（上）：那枚对不上的指纹",
     "第二天，一个准备临摹的画家支好画架，一抬头，墙上只剩四颗钉子。六十名警察翻遍了卢浮宫，还请来当时最出名的指纹专家贝尔蒂永。他在画框上提到一枚左手拇指指纹，跟两百多名馆员挨个比对：一个都对不上——因为当年佩鲁贾被捕，警方只采了右手。接下来两周，警方封路、搜船，把毕加索和诗人阿波利奈尔抓去问话。而搜到他家的警员，就靠在那张藏画的桌子上写完报告。"),
    ("N05", "破案关键（下）：一封信与背面那行编号",
     "画就在巴黎一间出租屋里，藏在一口木箱的假底板下面，躺了两年。一九一三年十一月，佛罗伦萨的古董商杰里收到一封信，署名「列奥纳多·V」：画在佛罗伦萨，愿意交还意大利，要五十万里拉。杰里拉上乌菲兹馆长波吉去旅馆。房间里，佩鲁贾掀开假底板。波吉什么也没说，只把画板翻过来，对着窗光看背面——卢浮宫的馆藏编号，七百七十九。"),
    ("N06", "结局与金句：档案里没有那根纤维",
     "网上还流传着一个更戏剧化的版本：一根藏在他工作服里的白杨木纤维，和画板材质比对上了，把他钉死。档案里没有这根纤维。真正出卖他的，是博物馆自己的登记本。名画一九一四年一月回到卢浮宫；同年佛洛伦萨开庭，他说自己只是把画还给祖国，被判一年零十五天，实际坐了七个月。而这桩案子，把一幅四百年没人回头看的画，抬成了全世界最有名的画。你觉得，是他太大意，还是卢浮宫太自信？"),
]

# 每一镜：(id, kind, 运镜, 叙事职责, 衔接方式, 英文提示词 或 信息卡大标题, 音效/备注)
# 45 镜 = 38 个 Agnes 动画镜头 + 7 张信息卡，按成片顺序编号，每个镜头只出现一次、不复用。
SHOTS = [
    (
        "S01",
        "agnes",
        "极缓推近",
        "0–5 秒钩子：方形展厅空无一人，墙上只剩四颗铁钉与一块浅色的「画在"
        "这里挂过」的痕迹",
        "推到极近时硬切案发当天早上",
        "The Louvre's Salon Carré at dawn, completely empty, framed from the "
        "first frame on a bare stretch of ochre gallery wall between two huge "
        "gilt frames: four small iron pegs and a pale rectangular ghost-mark "
        "where a picture hung, herringbone parquet, dust drifting in a slanted "
        "shaft of morning light from a high window, no people anywhere, no "
        "painted surface visible. Camera: one extremely slow push-in toward the "
        "four pegs." + HOLD,
        "低频垫底 + 展厅脚步回声；开口第一句无音乐",
    ),
    (
        "S02",
        "agnes",
        "横向跟拍",
        "案发当天 07:00：四名维修工的白色背影从临河员工门进去，谁都没多"
        "看一眼",
        "背影进门，硬切展厅里的四颗钉子",
        "The Louvre's quayside service entrance on a grey early morning in"
        "1911, framed from the first frame on wet cobblestones and a plain "
        "wooden door set in tall pale limestone: four workmen seen only from "
        "behind in long white smocks and flat caps walk toward the doorway "
        "carrying a glazier's wooden sash, a canvas tool roll and a putty tin,"
        "river mist low along the ground, a horse cart blurred at the frame "
        "edge, the blank limestone wall filling the background so that no "
        "horizon and no skyline are visible, no faces, no readable signage."
        "Camera: one slow lateral track keeping pace with them." + HOLD,
        "马蹄、河水、远处汽笛；音乐第一次进",
    ),
    (
        "S03",
        "agnes",
        "背影跟拍",
        "钩子：没人多看他一眼——空展厅里，一个白色背影在两排名画中间的木地板"
        "上走过去",
        "走到墙前停住，接楼梯间",
        "The empty Salon Carré at seven in the morning, framed down the long "
        "axis of the gallery from the first frame: a single workman in a white "
        "smock walks away from camera down the centre of the parquet between "
        "walls stacked with gilt frames, tall windows throwing long light "
        "panels across the floor, dust motes, no visitors, no faces, nothing "
        "readable. Camera: one steady follow behind him at walking pace." + HOLD,
        "脚步回声放大；这一步是全片的节奏点",
    ),
    (
        "S04",
        "agnes",
        "画廊远端固定",
        "七点一刻：从画廊另一端看，他伸手把那块小画板从四颗钉子上取下来（钩子"
        "只给远景，不剧透细节）",
        "画板离墙的一刻切信息卡",
        "A distant static frame down the length of a huge empty picture "
        "gallery, framed on the far wall from the first frame: four iron pegs "
        "and a pale ghost-mark in an ochre wall between two enormous gilt "
        "frames, a small figure in a white smock stepping up to the wall and "
        "lifting a plain wooden panel clear of the pegs, parquet floor and "
        "skylight, dust in the cold morning light, the figure only a fraction "
        "of the frame, no face, nothing readable. Camera: locked-off wide from "
        "the far end of the hall, only the small figure and the panel move." + HOLD,
        "音乐留一层低垫；远景里没有脚步，只有一声画板离钉的轻响",
    ),
    (
        "S05",
        "graphic",
        "信息卡 static card",
        "案件名片卡：解说正说到「抱着它走出大门」，卡片给出 1911.8.2"
        "1 / 28 小时才发现 / 失踪两年",
        "卡片硬切出门那一镜",
        "案件名片",
        "「28 小时」单独放大跳出；卡片末尾留 0.3 秒静场",
    ),
    (
        "S06",
        "agnes",
        "街对面固定",
        "卢浮宫过了一整天才发现：从街对面看那扇侧门，白色背影已经走进晨雾",
        "门在画面里合上，切第二天的空墙",
        "A street-level view across a wet cobbled lane toward a side door in a "
        "tall limestone museum wall, framed on the door from the first frame:"
        "one workman in a cap stands holding the door open while a shorter "
        "workman in a white smock seen from behind walks out past him carrying "
        "a cloth-wrapped bundle under his arm, river mist, a passing cart "
        "blurred at the frame edge, no faces, no readable plaque. Camera:"
        "locked-off medium-wide from across the lane; only the two figures and "
        "the closing door move." + HOLD,
        "门轴「吱」一声后立刻安静；字幕高亮「替他开了门」",
    ),
    (
        "S07",
        "agnes",
        "升镜头",
        "画已经在巴黎城里：卢浮宫屋脊在晨雾里拉长，观众第一次看见这座建筑有多"
        "大",
        "升起后叠到「没人发现」的展厅",
        "Above the Louvre on an August morning, framed from the first frame on "
        "slate roofs, chimney pots and the museum's long limestone façades "
        "receding toward the Seine: laundry lines, a sweep's ladder, thin "
        "chimney smoke, river mist flattening the far bank, no crowds and no "
        "close figures, no modern buildings, nothing readable. Camera: one slow "
        "crane up revealing the museum's full length and the grey river behind "
        "it." + HOLD,
        "城市醒来：鸽子、汽笛；音乐抽掉一层",
    ),
    (
        "S08",
        "agnes",
        "极缓拉镜头",
        "同一天下午：游客照常看别的画，那块空墙就在他们头顶",
        "拉远后切出租屋楼梯",
        "The Salon Carré in afternoon light filled with Belle Époque visitors "
        "in bowler hats and long dresses, framed from behind the crowd at the "
        "far end of the gallery from the first frame: every figure seen from "
        "the back, everyone looking at other paintings, a small bare patch of "
        "wall with four pegs visible in the middle distance above their heads,"
        "warm dusty light, gilded frames floor to ceiling, no faces, nothing "
        "readable. Camera: one very slow pull-back along the parquet behind the "
        "crowd." + HOLD,
        "人群低语；说到「过了一整天」时全片第一次静音 0.4 秒",
    ),
    (
        "S09",
        "agnes",
        "手持跟随",
        "「先说他是谁」：蒙马特出租屋的楼梯，矮壮背影扛着梯子、拎工具卷",
        "上楼接玻璃工坊",
        "A narrow working-class boarding-house stairwell in Montmartre, framed "
        "from the first floor looking up the flight from the first frame: a "
        "short heavyset man in a flat cap and paint-dusted coat seen from "
        "behind carries a step-ladder on his shoulder and a canvas tool roll,"
        "peeling floral wallpaper, a brass gas jet at each landing, a "
        "landlady's silhouette turned away in a doorway above, no faces,"
        "nothing readable. Camera: one handheld follow two steps behind him." + HOLD,
        "木楼梯吱呀、楼下手风琴很远",
    ),
    (
        "S10",
        "agnes",
        "微距焦点转移",
        "职业：玻璃工坊——铅条、油灰、钻石刀，一双手在压窗框",
        "焦点移到手上，切卢浮宫脚手架",
        "A glazier's workbench in a 1911 workshop, framed on the bench top from "
        "the first frame to the last: calloused hands in a leather apron lay "
        "lead came around a pane of glass and press the joint with a putty "
        "knife, a diamond cutter, a stiff brush, an open tin of linseed oil and "
        "a coil of cord at the frame edge, cold north light through a tall pane "
        "behind, wood shavings on the floor, no faces. Camera: one slow macro "
        "focus pull from the putty knife to the hands." + HOLD,
        "油灰刀刮木头的声音；工坊环境声",
    ),
    (
        "S11",
        "graphic",
        "信息卡 static card",
        "人物档案卡：生年、身高、职业、「给名画装罩子的人」、两次前科",
        "卡片硬切卢浮宫脚手架",
        "人物档案",
        "读到「罩子是他装的」时，卡片上那行字描黄",
    ),
    (
        "S12",
        "agnes",
        "缓慢横摇",
        "一九零八年：卢浮宫给珍品加装防碎玻璃罩，脚手架上的三个工人背影",
        "横摇停在他常站的那面墙",
        "The Salon Carré during the museum's glazing works, framed on tall "
        "wooden scaffolding erected under the hanging pictures from the first "
        "frame: three workmen's backs in white smocks on the planks fitting "
        "glass shadow boxes over gilt frames, ropes and a pulley, a ladder,"
        "canvas tarps on the parquet, cold daylight from high windows, the "
        "whole wall of paintings soft behind them, no faces, nothing readable."
        "Camera: one slow horizontal pan along the scaffolding." + HOLD,
        "绳子摩擦、木梯挪动",
    ),
    (
        "S13",
        "agnes",
        "高角度固定",
        "从阳台俯看：他一个人在那面墙前用折尺比划位置——他知道钉子在哪",
        "俯视接他的房间（同一栋楼的两副面孔）",
        "High angle from a gallery balcony looking down into the Salon Carré,"
        "framed on the parquet from the first frame: a single workman in a "
        "white smock seen from above stands before one wall holding a folding "
        "ruler, his shadow long across the floor, a step-ladder and tool box "
        "beside him, a few visitors far away with their backs turned, no "
        "painted surface facing camera, no faces, nothing readable. Camera:"
        "locked-off high angle; only the man and his shadow move." + HOLD,
        "只有脚步声；这一镜不留音乐",
    ),
    (
        "S14",
        "agnes",
        "缓慢推近",
        "他的全部家当：窄床、曼陀林、一只旧木箱——这只箱子后面还会出现两次",
        "推到箱子边缘切警局档案室",
        "A small rented room at night under a shaded gas mantle, framed from "
        "the doorway on the room's far wall from the first frame: a narrow iron "
        "bed with a folded blanket, a wooden travel trunk with its lid slightly "
        "ajar, a washstand with a chipped bowl, a mandolin leaning against the "
        "wall, pinned papers soft out of focus by the window, a single chair in "
        "the foreground, no people, nothing readable. Camera: one slow push-in "
        "past the chair toward the trunk." + HOLD,
        "煤气灯嘶嘶；木箱一声轻响",
    ),
    (
        "S15",
        "agnes",
        "定格转焦",
        "「指纹和照片早就在档案里」：警局档案室，一双手把卡片插进抽屉（只出现"
        "形状，不出现文字）",
        "抽屉合上的声音接到储物间",
        "A police records room, framed on a long desk from the first frame: a "
        "clerk's sleeves sort a stack of blank record cards and photograph "
        "mounts into drawers, an ink pad, a brass stamp, one fingerprint card "
        "set at an angle that shows only its shape, a row of tall cabinets "
        "behind, grey window light, no faces, absolutely no legible handwriting "
        "or print anywhere. Camera: locked-off medium shot with one slow rack "
        "focus from the ink pad to the cabinets." + HOLD,
        "卡片摩擦、抽屉滑轨；字幕高亮「指纹」",
    ),
    (
        "S16",
        "agnes",
        "门缝低角度固定",
        "星期天傍晚：他最后一个离开展厅，闪身躲进储物间（门外视角，光被门缝切窄）",
        "门缝收窄到黑，接夜里的储物间",
        "A museum storeroom behind the Salon Carré at dusk, framed low on the "
        "doorway from the first frame: a workman in a white smock slips in "
        "sideways and pulls the door almost closed after him, stacks of "
        "unframed canvases, a rolled rug, a step-ladder and packing crates "
        "filling the room, the last bar of window light falling across his "
        "boots before the door shuts, no faces, nothing readable. Camera:"
        "locked-off low angle through the narrowing gap." + HOLD,
        "门闩轻响；环境声突然被吸干",
    ),
    (
        "S17",
        "graphic",
        "信息卡 static card",
        "作案时间线卡：星期天傍晚混进收工的人流——卡上三行时间点与解说同拍",
        "卡片上的时间点跳到「早上」那一镜",
        "作案时间线",
        "逐行出现；最后一行停最长",
    ),
    (
        "S18",
        "agnes",
        "门内低角度固定",
        "他闪进展厅旁边的储物间，从里面把那扇木门闩拉上——门缝里最后漏进来一"
        "线走廊的光",
        "门缝的光被切断后切过夜那一镜",
        "Inside a dark museum storeroom framed on a tall wooden door from the "
        "first frame: a hand slides an iron bolt shut from the inside, a single "
        "blade of corridor light between the planks narrowing to nothing,"
        "stacks of unframed canvases and gilt frames in silhouette, a gas lamp "
        "burning low on a shelf, dust motes, no face, nothing readable. Camera:"
        "locked-off low angle inside the storeroom; only the bolt, the "
        "narrowing light and the dust move." + HOLD,
        "门闩一声金属摩擦；走廊光被切掉的同时把环境声也切掉半格",
    ),
    (
        "S19",
        "agnes",
        "低位侧移",
        "在一堆待修画框中间过了一夜：毯子、熄灭的煤气灯、半块面包",
        "侧移到他坐起，切扣扣子",
        "The same storeroom at night, framed low on the floor between crates "
        "and stacked canvases from the first frame: a man in a white smock "
        "asleep on a folded blanket with his arm under his head, a dead gas "
        "mantle, one high window throwing a bar of moonlight across his shoes,"
        "dust suspended, a bread crust on paper beside him, his face turned "
        "away in shadow, nothing readable. Camera: one slow lateral move past "
        "the canvases toward the sleeping figure." + HOLD,
        "只有呼吸与远处的滴水；无音乐",
    ),
    (
        "S20",
        "agnes",
        "微距固定",
        "星期一早上：他把白工作服扣到最上面一颗——这件工作服就是他的全部伪装",
        "手抚平布料，接空走廊",
        "Extreme close-up on a workman's chest and hands in a stone corridor,"
        "framed from the first frame on the buttons of a long white smock: the "
        "fingers fasten the top button and smooth the cloth flat, the fabric "
        "creased and paint-flecked, a brass museum key on a cord at his wrist,"
        "soft grey morning light, no face, no badge, nothing readable. Camera:"
        "locked-off macro; only the hands move." + HOLD,
        "布料摩擦；音乐进单音提琴",
    ),
    (
        "S21",
        "agnes",
        "低角度固定",
        "等展厅空了：一双手把画从四颗铁钉上取下——只拍手、袖口和画板背面",
        "画板抬出画面时切楼梯间",
        "A gallery corner framed tight from the first frame on four iron pegs "
        "set in an ochre wall beside the edge of a heavy gilt frame: a "
        "workman's forearms in white smock sleeves reach in, unhook a small "
        "plain wooden panel and lift it clear, its blank varnished back and "
        "bare edges facing camera, a screwdriver and a folded cloth on the "
        "parquet below, motes in the cold light, no face, no painted surface "
        "visible, nothing readable. Camera: locked-off low angle, only the "
        "hands and the panel move." + HOLD,
        "金属钉刮墙的短响；这一声做全片的第一记拍点",
    ),
    (
        "S22",
        "agnes",
        "缓慢横移",
        "隔壁「七米」楼梯间：卸下玻璃罩与画框，随手丢在学生习作中间",
        "玻璃反光延到信息卡",
        "A narrow museum service stairway of worn stone steps and a black iron "
        "balustrade, framed on the landing from the first frame: a figure in a "
        "white smock crouches as he levers a heavy gilt frame and a "
        "glass-covered shadow box off a wooden panel, the emptied frame and "
        "glass already leaning against stacked student canvases in the corner,"
        "pale high window light, plaster dust on the steps, no faces, no "
        "plaques, nothing readable. Camera: one slow lateral slide along the "
        "landing." + HOLD,
        "木头刮地 + 玻璃轻碰一声",
    ),
    (
        "S23",
        "agnes",
        "过肩跟随",
        "他把画夹在胳膊底下，一个水管工顺手替他开了门——从门里看出去的那三秒",
        "门外的亮块接屋顶升镜",
        "View from inside a stone service passage looking out through an open "
        "door onto a misty quay, framed on the doorway from the first frame: a "
        "short heavyset workman in a white smock seen from behind walks past "
        "camera carrying a cloth-wrapped rectangular bundle tucked under his "
        "arm, while another workman in a cap holds the door ajar for him, unlit "
        "gas lamps outside, barrels and a cart blurred beyond, damp limestone "
        "walls filling both sides, no faces, nothing readable. Camera: one slow "
        "over-the-shoulder follow toward the light." + HOLD,
        "门轴一声、街道环境声涌进来",
    ),
    (
        "S24",
        "agnes",
        "缓慢横摇",
        "第二天：临摹的画家支好画架，一抬头——横摇到那堵空墙",
        "摇到空墙定住 0.4 秒",
        "The Salon Carré mid-morning, framed from the far end of the gallery "
        "from the first frame: a man in a paint-stained smock stands before an "
        "easel with his back to camera, brush raised, staring at a bare patch "
        "of wall with four pegs, a second visitor stopped beside him, gilded "
        "frames all around and dust in the light, no faces, nothing readable."
        "Camera: one slow horizontal pan from the easel to the empty wall." + HOLD,
        "画笔掉在地板上；音乐停半拍",
    ),
    (
        "S25",
        "graphic",
        "信息卡 static card",
        "勘查卡：画框上一枚左手拇指指纹 / 比对两百多名馆员，无一匹配",
        "卡片硬切取证台",
        "勘查与失手",
        "「左手」两个字单独放大；这张卡是全片的信息爆点",
    ),
    (
        "S26",
        "agnes",
        "微距转焦",
        "贝尔蒂永在拆下的画框上撒碳粉、用明胶取走那枚拇指印",
        "取下的指印片接查封",
        "A criminology bench in a 1911 laboratory, framed on the bench from the "
        "first frame to the last: gloved fingers dust the corner of a detached "
        "gilt frame with carbon powder using a camel-hair puff, a magnifying "
        "hood on a stand, a sheet of clear gelatin lifting a single thumb "
        "impression, blank cards stacked face-down, a brass lamp, no faces,"
        "absolutely no legible writing. Camera: one slow macro focus pull from "
        "the brush to the lifted print." + HOLD,
        "碳粉刷子的沙沙声",
    ),
    (
        "S27",
        "agnes",
        "手持跟随",
        "卢浮宫闭馆一周：员工排成一列按手印，警察在长桌后挨个登记",
        "沿队列跟移到一处空位——那本该是他的位置",
        "The Louvre's entrance hall in the week after the theft, framed on the "
        "closed inner doors from the first frame: a line of museum staff seen "
        "from behind waits along the wall while two officers in kepi caps take "
        "fingerprints at a trestle table, notice boards turned to the wall,"
        "ropes and a wooden bench, grey daylight through the glass vault, no "
        "faces, nothing readable. Camera: one slow handheld follow along the "
        "queue." + HOLD,
        "队列低语、印台拍击声，一下比一下慢",
    ),
    (
        "S28",
        "agnes",
        "横摇",
        "「接下来两周，警方封路、搜船」：勒阿弗尔港，箱子在码头上一件件被撬开",
        "摇到一只与那口木箱同形状的箱子，切预审室",
        "A Norman dockside at dawn, framed on a gangway and stacked luggage "
        "from the first frame: sailors and police in caps prying open trunks "
        "and hatboxes on the quay, passengers queued with their backs turned, a "
        "liner's hull and funnels in mist behind, ropes, crates and a swaying "
        "derrick, wet planks, no faces, no readable ship name. Camera: one slow "
        "pan across the opened luggage." + HOLD,
        "海鸥、撬棍、风",
    ),
    (
        "S29",
        "agnes",
        "缓慢横移",
        "「把毕加索和诗人阿波利奈尔抓去问话」：预审室里两个只成剪影的男人，警"
        "察在桌后写记录",
        "横移到门，切回那间出租屋",
        "A prefecture interrogation room at night, framed from the far end of "
        "the room on two seated men in bohemian jackets seen only as "
        "silhouettes under a hanging lamp, an officer's back at a desk writing,"
        "a third figure standing in shadow at the wall, cigarette smoke in the "
        "cone of light, bare plaster walls, no faces, nothing readable. Camera:"
        "one slow lateral slide behind the desk." + HOLD,
        "笔尖划纸；这一镜不留音乐",
    ),
    (
        "S30",
        "agnes",
        "微距固定",
        "最荒诞的一幕：警员就靠在那张桌子上写完报告，画就在他脚下的阴影里",
        "镜头微微滑向阴影，切两年后",
        "A bedroom interior framed from floor level on the underside of a small "
        "wooden table from the first frame: a policeman's hand rests on the "
        "tabletop edge while he writes in a notebook, his knee and uniform "
        "sleeve in the foreground, and in the deep shadow beneath the table one "
        "corner of a cloth-wrapped panel just visible at the frame edge, a "
        "chair leg, a candle flame, no faces, nothing readable. Camera:"
        "locked-off low macro with a slight drift toward the shadow." + HOLD,
        "笔尖声；说到「写完了报告」时全部静音 0.3 秒",
    ),
    (
        "S31",
        "agnes",
        "极缓推近",
        "两年：同一个房间，画立在墙边，他坐在床沿上看它（只有背影）",
        "推近到包裹，切车站",
        "The same rented room two years later in winter afternoon light, framed "
        "on the far wall from the first frame: a bare cloth-wrapped panel leans "
        "against the wall behind a chair, a man in braces sits on the bed edge "
        "with his back to camera and head slightly bowed, hands loose between "
        "his knees, frost on the window, an unlit gas mantle, no face, no "
        "painted surface shown, nothing readable. Camera: one very slow push-in "
        "past the chair." + HOLD,
        "窗缝的风；钢琴第一次进",
    ),
    (
        "S32",
        "agnes",
        "横移跟拍",
        "一九一三年十一月：他拎着同一只旧木箱上火车，去佛罗伦萨",
        "车厢门合上，切信件卡",
        "A Paris station platform in late November, framed along the side of a "
        "wooden carriage from the first frame: a short man in a flat cap and "
        "overcoat seen from behind carries an old travel trunk up a van step,"
        "steam coiling around his boots, porters with their backs turned, lamp "
        "light spilling on the planks, a signal box in fog, no faces, nothing "
        "readable. Camera: one slow lateral track along the carriage as he "
        "boards." + HOLD,
        "汽笛、车厢铁链",
    ),
    (
        "S33",
        "graphic",
        "信息卡 static card",
        "信件卡：1913.11.29 署名 Leonardo V / 交还意"
        "大利 / 五十万里拉",
        "卡片硬切读信的手",
        "一封信",
        "「五十万里拉」单独跳出",
    ),
    (
        "S34",
        "agnes",
        "微距转焦",
        "古董商杰里在事务所读那封署名「列奥纳多·V」的信，焦点从信纸拉到窗外"
        "的旅馆招牌",
        "焦点移到窗外，切旅馆走廊；这一镜同时承接下一句「拉上馆长去旅馆」",
        "An antique dealer's office in Florence, framed on a desktop under a "
        "shaded lamp from the first frame: a man's hands in a dark waistcoat "
        "unfold a folded letter, a paper knife, a stub of sealing wax, a pocket "
        "watch chain and a photograph of a gallery room at the edge, the sheet "
        "kept blank-facing and out of focus wherever writing would be, no "
        "readable characters anywhere, no faces. Camera: locked-off macro with "
        "one slow focus pull from the hands to the window behind." + HOLD,
        "纸张展开；座钟摆声",
    ),
    (
        "S35",
        "agnes",
        "过肩跟随",
        "三个人影的背影走向 20 号房：古董商、馆长、便衣警察",
        "停在门前，接开箱",
        "A Florentine hotel corridor in December 1913, framed from behind three "
        "men walking toward a door at the far end from the first frame: a "
        "dealer, an older director in a fur collar and a plainclothes "
        "inspector, all seen from the back and shoulder only, plaster walls, a "
        "wall gas bracket, a patterned runner carpet, a maid's silhouette "
        "facing away at the near end, no faces, no readable door plate. Camera:"
        "one steady over-the-shoulder follow." + HOLD,
        "三种脚步错开；到门口全部停下",
    ),
    (
        "S36",
        "agnes",
        "极缓推近",
        "房间里，他掀开木箱的假底板——观众第一次看到「夹层」这件事被证实",
        "底板掀起，接翻面对光",
        "Inside a modest hotel room, framed low on an open travel trunk on a "
        "bed from the first frame: two hands lift out a false wooden bottom and "
        "reach beneath it toward a cloth-wrapped rectangular panel lying in the "
        "cavity, a suitcase lining, hats and shirts piled to one side, winter "
        "light through a shuttered window, no faces, no painted surface "
        "revealed, nothing readable. Camera: one very slow push-in toward the "
        "cavity." + HOLD,
        "底板木声；这一段只留呼吸",
    ),
    (
        "S37",
        "agnes",
        "定格转焦",
        "波吉把画板翻过来对着窗光：干裂、虫道、旧标签的胶痕，和一处磨损的印记"
        "（只给形状，不给数字）",
        "焦点移到印记，接真假对比卡",
        "Close on the reverse of a small aged poplar wood panel held up by two "
        "pairs of hands against a shuttered window, framed on the wood from the "
        "first frame to the last: pale dry cracks, worm channels, the glue "
        "ghosts of removed labels at the corners, one worn stamped impression "
        "legible only as an abstract shape in the raking light, a director's "
        "sleeve and a dealer's waistcoat edge at the frame, no painted face "
        "anywhere, absolutely no readable characters or numbers. Camera:"
        "locked-off close shot with one slow focus pull along the wood grain." + HOLD,
        "钢琴单音一次；这里绝不给编号的画面文字",
    ),
    (
        "S38",
        "graphic",
        "信息卡 static card",
        "真假之辨：流传版本「一根白杨木纤维」对档案记录「馆藏编号 INV 7"
        "79」",
        "卡片末尾的静场接逮捕那一镜",
        "流传与档案",
        "两行并排；第二行出现时全部静音半秒",
    ),
    (
        "S39",
        "agnes",
        "手持跟拍",
        "开场先把「传说」摆出来：逮捕现场——两名便衣从两侧架住他带下楼梯，帽"
        "子留在柱子上",
        "下楼接纤维示意",
        "A hotel stairwell landing framed on the turn of the stairs from the "
        "first frame: two plainclothes officers in caps take a short workman by "
        "the arms from either side and lead him down, all three seen from "
        "behind and above, his flat cap left on the newel post, a housekeeper's "
        "silhouette turned away in a doorway, lamplight on worn stone, no "
        "faces, no readable text, no violence beyond the grip. Camera: one "
        "handheld follow down the flight." + HOLD,
        "三双脚步下楼；音乐骤停",
    ),
    (
        "S40",
        "agnes",
        "微距缓推",
        "「一根藏在工作服里的白杨木纤维」：放大镜下的粗布纤维与几粒木屑——这"
        "是流传版本，画面必须标「示意图」",
        "放大镜头摇焦到布纹，接登记本",
        "A macro still life under a brass magnifier on a dark wooden table,"
        "framed from the first frame: coarse woven cotton threads of a "
        "workman's smock spread on blotting paper beside a few pale wood "
        "shavings, the round lens hovering above them, raking lamp light,"
        "shallow depth of field, an evidence tray out of focus at the edge, no "
        "faces, no readable characters. Camera: one slow macro push-in through "
        "the magnifier with a slight focus drift." + HOLD,
        "只留低频嗡鸣；这一镜是「传说」，不是物证",
    ),
    (
        "S41",
        "agnes",
        "缓慢横摇",
        "「真正出卖他的，是博物馆自己的登记本」：库房木架上一排排登记册，一双"
        "手翻开其中一本（纸面失焦）",
        "横摇到合上的册子，切月台",
        "A museum storeroom aisle between tall wooden shelving stacked with "
        "bound ledgers and flat portfolio cases, framed down the aisle from the "
        "first frame: an archivist's hands pull one ledger down and open it on "
        "a shelf edge, the pages out of focus and blank-facing, a rolling "
        "ladder, dust in a shaft of cold window light, no faces, absolutely no "
        "legible writing. Camera: one slow lateral pan along the shelves." + HOLD,
        "纸页翻动；钢琴进两个音",
    ),
    (
        "S42",
        "agnes",
        "横移",
        "「名画一九一四年一月回到卢浮宫」：清晨月台，稻草箱被抬上货车，箱上只"
        "挂空白标签",
        "箱子上车，切法庭",
        "A goods van at a station platform at dawn, framed on its open doors "
        "from the first frame: two officials in overcoats and a porter seen "
        "from behind lift a straw-packed wooden crate with blank unmarked tags "
        "up the van step, a lantern, frost on the planks, steam from locomotive "
        "wheels, low winter light, no faces, no readable marks. Camera: one "
        "slow lateral track past the van doors." + HOLD,
        "蒸汽、木箱上踏板的记重音",
    ),
    (
        "S43",
        "agnes",
        "缓慢横移",
        "「同年佛洛伦萨开庭，他说自己只是把画还给祖国」：法庭后排视角，被告席"
        "上一个矮壮的背影",
        "横移到旁听席，接判决卡",
        "Wide shot from the back of a wood-panelled Florentine courtroom with "
        "no windows, framed from the first frame: rows of spectators' backs in "
        "the foreground, a short heavyset man in a dark suit seen from behind "
        "standing at the defence table between two advocates, the judges'"
        "raised bench and two draped flags ahead, warm ceiling globes, dusty "
        "light, no recognisable faces, nobody turns toward camera. Camera: one "
        "very slow lateral slide behind the last row." + HOLD,
        "法槌一声；日期由字幕给",
    ),
    (
        "S44",
        "graphic",
        "信息卡 static card",
        "判决卡：一年零十五天、实际服刑约七个月；名画一九一四年一月回卢浮宫",
        "卡片切今天的展厅",
        "判决与归还",
        "「一年零十五天」与「七个月」并排，数字差做视觉钩子",
    ),
    (
        "S45",
        "agnes",
        "升镜头",
        "「抬成了全世界最有名的画」+ 提问：今天的展厅，几百个人排着队看同一"
        "堵墙的方向——镜头升起，最后停在人群上",
        "升到全景后画面渐隐，接片尾卡",
        "The modern Louvre gallery where the painting hangs, framed low behind "
        "a dense queue of visitors' backs from the first frame: hundreds of "
        "heads and raised phones seen only from behind, barrier lanes, cold "
        "reflections on protective glass, a lone guard's back beside it, the "
        "artwork's face never entering the frame, nothing readable. Camera: one "
        "slow crane up from the barrier to reveal the whole hall from above." + HOLD,
        "人声 + 钢琴尾音；结尾停 1 秒引导评论，最后 0.8 秒音画渐隐",
    ),
]



# ---------------------------------------------------------------------------
# 画面上的文字（render.py 从 story.json 的 presentation 块读，不在 render.py 里写死）
# ---------------------------------------------------------------------------
CARD_HEADER = "案件档案  /  卢浮宫 · 1911–1914"
CARD_FOOTER = "资料摘要与示意图 · 并非原始档案影像"

# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S05": ("案件名片",
            "1911年8月21日（周一闭馆）· 巴黎卢浮宫方形展厅",
            "失窃：达·芬奇《蒙娜丽莎》· 白杨木画板 53×77cm · 约28小时后才被发现 · 失踪两年"),
    "S11": ("人物档案",
            "文森佐·佩鲁贾 · 1881年生 · 意大利移民 · 身高约1.6米",
            "职业：油漆工 / 镶玻璃工；1908年起为卢浮宫加装画作防碎罩；此前两次被捕，指纹已在警局档案"),
    "S17": ("作案时间线",
            "8月20日（周日）傍晚混入，藏进展厅旁储物间过夜",
            "8月21日 07:00 进入空展厅 → 隔壁楼梯间卸下玻璃罩与画框 → 07:15–08:30 从员工侧门离开"),
    "S25": ("勘查与失手",
            "画框上提取到一枚左手拇指指纹（指纹专家阿尔方斯·贝尔蒂永）",
            "与两百多名卢浮宫员工逐一比对：无一匹配。佩鲁贾当年被捕时警方只采了右手，名字也没进待查清单"),
    "S33": ("一封信",
            "1913年11月29日 · 佛罗伦萨古董商阿尔弗雷多·杰里收到",
            "署名「Leonardo V」：画在佛罗伦萨，愿交还意大利，索要 50 万里拉"),
    "S38": ("流传与档案",
            "流传版本：工作服里一根白杨木纤维，与画板材质比对成功 —— 查无档案依据",
            "档案记录：乌菲兹馆长乔瓦尼·波吉核对画板背面的卢浮宫馆藏编号 INV 779，确认不是赝品"),
    "S44": ("判决与归还",
            "1914年 · 佛洛伦萨审判：判一年零十五天，实际服刑约七个月",
            "名画先在意大利巡展，1914年1月4日回到卢浮宫；此后它成为全球最有名的画"),
}

TITLE_CARD = ["蒙娜丽莎：行李箱里的779号",
              "卢浮宫 1911 · 一桩把名画抬上神坛的盗窃"]

END_CARD = [
    "你觉得，是他太大意，还是卢浮宫太自信？",
    "《蒙娜丽莎》失窃案 · 1911.8.21 – 1913.12 · 单独作案",
    "档案里没有那根纤维，只有博物馆自己的登记本。",
    "资料：Wikipedia / Smithsonian / BBC / History / 界面新闻 / 澎湃 等公开报道 · 原创解说 · AI动画情景重现",
]

CAPTION_KEYWORDS = [
    "四颗铁钉", "白色工作服", "闭馆", "左手拇指", "两百多名", "只采了右手", "假底板",
    "五十万里拉", "馆藏编号", "白杨木", "纤维", "一年零十五天", "登记本",
]

# 默认标「AI动画情景重现 · 非新闻影像」；警局 / 取证 / 庭审 / 运输 / 今日展厅要写得更具体。
LABEL_OVERRIDES = {
    "S15": "AI动画示意 · 非档案影像",
    "S26": "AI动画示意 · 非取证照片",
    "S27": "AI动画示意 · 非现场影像",
    "S29": "AI动画示意 · 非审讯影像",
    "S39": "AI动画示意 · 非逮捕照片",
    "S40": "流传版本的示意图 · 非物证照片",
    "S41": "AI动画示意 · 非档案影像",
    "S43": "AI动画示意 · 非庭审影像",
    "S45": "AI动画示意 · 今日展厅情景重现",
}

# 合成音效事件：(镜头号, 类型)，类型 paper / phone / keys / machine / press
SFX_EVENTS = [
    ("S03", "keys"),
    ("S04", "press"),
    ("S15", "press"),
    ("S19", "paper"),
    ("S23", "paper"),
    ("S34", "paper"),
    ("S36", "keys"),
    ("S42", "keys"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "世界第一名画，被一个临时工抱走了：卢浮宫花了一整天才发现",
    "他给《蒙娜丽莎》装过玻璃罩，三年后把画偷走｜档案里没有那根纤维",
    "偷画两年没被发现，栽在一行馆藏编号上：蒙娜丽莎失窃案一口气看懂",
]
HOOK = ("1911 年 8 月 21 日，一个身高一米六、给卢浮宫装过玻璃罩的意大利油漆工，在闭馆日躲在储物间过了一夜，"
        "第二天早上把《蒙娜丽莎》从墙上四颗铁钉上取下、裹进白工作服、从员工通道抱了出去；卢浮宫过了一整天"
        "才发现。画在他床脚的木箱夹层里躺了两年——最后钉死他的，不是网络流传的那根白杨木纤维，"
        "而是博物馆自己的登记本：画板背面的馆藏编号 779。")
GOLDEN_LINES = [
    "档案里没有那根传奇的纤维，只有博物馆自己的登记本。",
    "他用两只手偷走了全世界最有名的画，却被一行编号出卖。",
    "这场盗窃没有毁掉那幅画，它把一幅四百年没人回头看的画，抬成了全世界最有名的画。",
    "你觉得，是他太大意，还是卢浮宫太自信？评论区聊聊。",
]
DESCRIPTION = (
    "1911年8月21日，星期一，卢浮宫闭馆。一个穿白色工作服的油漆工从员工通道走进去，"
    "把《蒙娜丽莎》从墙上四颗铁钉上取下来，裹进工作服，抱出了大门——而博物馆过了一整天才发现。\n"
    "他叫文森佐·佩鲁贾，意大利移民，一米六，1908年参与过给卢浮宫珍品加装防碎玻璃罩的工程："
    "那幅画的罩子，很可能就是他亲手装的。\n"
    "画在他床脚的木箱假底板下面躺了两年。1913年11月，他给佛罗伦萨的古董商写了一封信，署名「列奥纳多·V」，"
    "要五十万里拉。乌菲兹馆长在旅馆房间里把画板翻过来，对着窗光看了背面那行馆藏编号——779。案子就此告破。\n"
    "顺便说：网上流传的「一根白杨木纤维比对成功」，档案里查不到。\n"
    "三分钟，讲清楚这桩二十世纪最离谱的盗窃案。\n"
    "※ 画面为 AI 动画情景重现，非历史影像；《蒙娜丽莎》正面不出现在片中任何一镜，"
    "所有事实都能指到脚本里列出的公开报道来源。"
)
QUESTION = "你觉得，是他太大意，还是卢浮宫太自信？"
HASHTAGS = ["#蒙娜丽莎", "#卢浮宫", "#真实案件", "#艺术史", "#悬案", "#刑侦", "#案件解说", "#AI动画"]

GRID = 4           # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 7  # 每个 Agnes 镜头实际请求的时长（169 帧 @ 24 fps）
SEED_BASE = 19110821  # 案发日 1911-08-21，让 seed 可追溯

# screenplay.md 的「事实边界」三段。解说稿 / 分镜表 / 信息卡 / 来源由 build() 从同一份数据生成，
# 所以 screenplay.md 永远不会和 story.json 说不一样的话。
FACT_BOUNDARY = {
    "可证的事实（每条都能指到文末的来源编号）": [
        "文森佐·佩鲁贾（Vincenzo Peruggia），1881 年生，意大利移民，身高约 160cm，在巴黎做油漆工与镶玻璃工；"
        "1910 年卢浮宫因收到威胁信给珍品加防碎玻璃罩，工程包给科比尔（Cobier）玻璃公司，他是其中一名工人，"
        "《蒙娜丽莎》的罩子很可能由他安装。〔1〕〔2〕〔9〕",
        "1911 年 8 月 21 日（周一闭馆）约 07:00 穿白色工作服走员工通道进入卢浮宫，把画从墙上四颗铁钉上取下，"
        "在旁边的楼梯间卸掉玻璃罩与画框并丢在拐角，随后把画裹进工作服带出侧门（一名水管工替他开了门）。"
        "〔1〕〔2〕〔5〕",
        "次日（8 月 22 日）才由准备临摹的画家发现；卢浮宫闭馆一周；约 60 名警察勘查现场，"
        "当值保安的孩子出疹请假、替班者 8 点离岗抽烟，案发窗口被压缩在 07:00–08:30。〔3〕〔4〕",
        "指纹专家阿尔方斯·贝尔蒂永在画框（玻璃罩）上取到一枚拇指指纹，比对未能命中："
        "一说与 256 名卢浮宫员工逐一比对全部落空；另有记载指出警方当年只采集了佩鲁贾的右手指纹，"
        "而现场留下的是左手，且他的名字没有被列入待查清单。〔1〕〔3〕〔9〕〔10〕",
        "1911 年 11 月警方按惯例问话全体馆内员工，佩鲁贾称前一晚喝多而迟到，警方采信；"
        "警方搜查他的住所无果（写报告的警员正靠在那张藏画的桌边）；调查期间毕加索与诗人阿波利奈尔被捕问话后获释；"
        "警方还封锁道路、在勒阿弗尔搜查轮船与行李。〔2〕〔3〕〔11〕〔12〕",
        "画被藏在他巴黎住所一只木箱的假底板下近两年，从未离开巴黎；1913 年 11 月 29 日他写信给佛罗伦萨"
        "古董商阿尔弗雷多·杰里，署名 Leonardo Vincenzo，索要 50 万里拉「交还意大利」；"
        "12 月 10 日在旅馆房间当众掀开假底板，乌菲兹馆长乔瓦尼·波吉核对画板背面的卢浮宫馆藏编号（INV 779）"
        "确认是真迹后报警，他当天被捕。〔2〕〔6〕〔7〕〔8〕〔9〕",
        "名画先在意大利巡展，1914 年 1 月 4 日回到卢浮宫；1914 年在佛洛伦萨受审，他主张是为把画还给祖国，"
        "被判一年零十五天，实际服刑约七个月（一说七个月零九天）。〔4〕〔8〕〔12〕",
        "这场盗窃是《蒙娜丽莎》成为「全世界最有名的画」的直接推手：报道、明信片、模仿与全国性的搜寻"
        "在两年里把一幅原本少有人驻足的画抬成了图标。〔2〕〔4〕〔12〕",
    ],
    "情景重现（全部是 Agnes 生成的 2D 动画，常驻标注「AI动画情景重现 · 非新闻影像」）": [
        "所有人物只有背影、剪影与手；佩鲁贾不出现 AI 生成的正脸，也不做「神探 vs 大盗」的正面表演。",
        "《蒙娜丽莎》的画面正面不进入任何一镜：只出现空墙与四颗铁钉、被卸下的空画框与玻璃罩、"
        "画板的背面（木纹、干裂、虫道、旧标签胶痕）。",
        "警局档案室、取证台、预审室、法庭、监狱、月台、印刷厂是「示意」镜头，标签分别写明"
        "「非档案影像 / 非取证照片 / 非庭审影像 / 非历史照片」。",
        "1913 年旅馆房间里的编号核对只画「对着窗光看木板背面」这个动作，"
        "编号 779 由信息卡与字幕给出——画面里不出现任何可读数字。",
    ],
    "坚决不写": [
        "不把「一根白杨木纤维比对成功把他钉死」当事实：这是网络流传的戏剧化版本，检索得到的档案与主流报道"
        "都没有这一条。片中只在信息卡 S38 与 N06 开头把它作为「流传版本」明确打假。〔6〕〔7〕〔9〕",
        "不提 Valfierno（瓦尔费尼奥）与赝品阴谋论，不提「德国人偷的」传闻——都无实证；"
        "他随身有美国收藏家名单这一条只作为报道事实引用，不据此推断同伙。〔9〕〔12〕",
        "不美化犯罪、不写血腥或侵害细节（平台审核与 TTS 内容审核都会拦）；不指认任何同案者。",
        "不把刑期写成整数年：判决与实际服刑的差（一年零十五天 / 约七个月）是本案最有传播力的事实之一，照实写。",
    ],
}


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
    story["title"] = TITLE
    story["style_prefix"] = STYLE_PREFIX
    story["negative_prompt"] = NEGATIVE_PROMPT
    story["principles"] = PRINCIPLES
    story["sources"] = SOURCES
    for chapter, (cid, title, text) in zip(story["chapters"], CHAPTERS):
        assert chapter["id"] == cid
        chapter["title"] = title
        chapter["text"] = text
    seen = set()
    shots = []
    for i, (sid, kind, camera, purpose, transition, body, sfx) in enumerate(SHOTS):
        assert sid == f"S{i + 1:02d}", sid
        assert sid not in seen, f"镜头 {sid} 重复"
        seen.add(sid)
        if kind == "agnes":
            assert "Camera:" in body and len(body.split()) > 45, f"{sid} 提示词不够具体"
        start = i * GRID
        shots.append({
            "id": sid, "kind": kind, "start": start, "duration": GRID,
            "narration_id": f"N{min(6, start // 30 + 1):02d}",
            "prompt": body if kind == "agnes" else "",
            "purpose": purpose, "transition_out": transition,
            "graphic": body if kind == "graphic" else "",
            "seed": SEED_BASE + i + 1,
            "seconds": AGNES_SECONDS, "aspect": "16:9", "resolution": "1080p", "frame_rate": 24,
            "camera": camera, "sfx_note": sfx,
        })
    story["shots"] = shots
    story["presentation"] = presentation()
    story["_scaffold"]["note"] = (
        "内容由 build_story.py 一次性写入；45 镜 × 4 秒规划网格（38 Agnes + 7 信息卡，每镜只用一次）；"
        "解说词与 screenplay.md、audio/manifest.json 三处逐字一致由 generate.py --validate 守着。")
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")

    manifest = json.loads(MANIFEST.read_text())
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        assert clip["id"] == chapter["id"]
        clip["text"] = chapter["text"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    kinds = [s["kind"] for s in story["shots"]]
    total = sum(len(c["text"]) for c in story["chapters"])
    print(f"story.json 已写入：{len(shots)} 镜 = {kinds.count('agnes')} agnes + {kinds.count('graphic')} graphic，"
          f"解说 {total} 字（含标点）")
    for (cid, _t, text) in CHAPTERS:
        print(f"  {cid} {len(text)} 字 · TTS 约 {len(text)/4.41:.1f}s → 收紧后约 {len(text)/5.05:.1f}s")
    for s in story["shots"]:
        assert s["kind"] != "graphic" or s["id"] in CARDS, f"信息卡 {s['id']} 缺 CARDS 文案"
    write_screenplay(story)
    cams = [s["camera"] for s in story["shots"] if s["kind"] == "agnes"]
    print(f"  Agnes 运镜种类：{len(set(cams))} 种（长岛那部是 19 种，别退回单一飞入）")


def write_screenplay(story: dict):
    """从同一份数据生成 screenplay.md（解说稿逐字来自 CHAPTERS，不手抄，所以不会和 story.json 漂移）。"""
    lines = [f"# {TITLE}", "",
             f"三分钟横屏解说 · 成片目标 1920×1080 / 30 fps / 180 秒 · {len(story['shots'])} 镜"
             f"（{sum(s['kind']=='agnes' for s in story['shots'])} 个 Agnes Video V2.0 二维动画镜头 + "
             f"{sum(s['kind']=='graphic' for s in story['shots'])} 张信息卡，每镜只用一次）· "
             "画风沿用《吉尔戈海滩：披萨盒里的凶手》（长岛连环案）那一部。", "",
             "## 事实边界", ""]
    for heading, bullets in FACT_BOUNDARY.items():
        lines += [f"**{heading}**", ""]
        lines += [f"- {b}" for b in bullets]
        lines += [""]
    lines += ["## 解说稿与时间线", "",
              "> 下面每段文字与 `story.json` 的 `chapters[].text`、`audio/manifest.json` 的 `clips[].text` "
              "**逐字一致**（由 `build_story.py` 一次性写入，三处同源）；分镜时间先按 45 × 4 秒规划网格给出，"
              "配音落地后由 `render.py` 的 CUTS 按真实停顿重对，成片以 `delivery/edit-decision-list.json` 为准。", ""]
    for i, ch in enumerate(story["chapters"]):
        a, b = i * 30, i * 30 + 30
        f = lambda s: f"{s // 60:02d}:{s % 60:02d}.0"
        lines += [f"### {f(a)}—{f(b)}　{ch['title']}（{ch['id']}）", "", ch["text"], ""]
    lines += ["## 分镜与衔接", "", "| 镜头 | 规划时间 | 类型 | 叙事职责 | 衔接方式 |", "|---|---|---|---|---|"]
    for s in story["shots"]:
        lines.append(f"| {s['id']} | {s['start']:03d}—{s['start']+s['duration']:03d}s | {s['kind']} | "
                     f"{s['purpose']} | {s['transition_out']} |")
    lines += ["", "## 信息卡文案（后期用 Noto CJK 本地渲染，不交给视频模型拼字）", ""]
    for sid, (head, l1, l2) in story["presentation"]["cards"].items():
        lines += [f"- **{sid} · {head}**", f"  - {l1}", f"  - {l2}", ""]
    lines += ["## 资料来源", ""]
    lines += [f"{s['id']}. {s['url']} —— {s['usage']}" for s in story["sources"]]
    lines.append("")
    (HERE / "screenplay.md").write_text("\n".join(lines) + "\n")
    print(f"screenplay.md 已写入（与 story.json / audio/manifest.json 同源）")


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

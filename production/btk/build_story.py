#!/usr/bin/env python3
"""BTK：软盘里的名字 — 内容唯一来源（吉尔戈模式）。"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
TITLE = "BTK：软盘里的名字"

STYLE_PREFIX = (
    "Stylized hand-painted 2D animated documentary, graphic-novel ink lines, soft cel shading and subtle paper grain; "
    "Wichita, Kansas and Park City from the 1970s through 2005, modest Midwestern ranch houses, quiet tree-lined streets, "
    "church interiors, municipal offices, old newsroom and forensic lab; horizontal 16:9 cinematic composition, "
    "muted slate blue, dusty ochre, tobacco brown and restrained sodium-orange practical light, sober investigative "
    "true-crime mood, never horror spectacle; human figures only as distant silhouettes, backs or hands, never a clear "
    "frontal face or recognizable likeness; no readable text, letters, numbers, logos, license plates or signs inside "
    "generated footage; one continuous restrained camera movement per shot, stable anatomy and props. "
)
NEGATIVE_PROMPT = (
    "readable text, words, letters, numbers, signage, logos, watermark, subtitles, photorealistic face, recognizable "
    "real person, frontal face, blood, gore, corpse, body, body bag, body parts, wound, weapon, assault, strangling, "
    "violence, crime reenactment, child in danger, horror monster, 3D CGI, distorted anatomy, deformed hands, extra "
    "fingers, extra limbs, duplicated people, morphing, jitter, flicker, teleportation, jump cut, rapid zoom, split screen"
)
PRINCIPLES = [
    "全部 Agnes 镜头为风格化二维动画情景重现，常驻标注「AI动画情景重现 · 非新闻影像」，不冒充真实监控、庭审或档案画面。",
    "不展示遗体、血腥、侵害过程或可模仿的作案步骤；以空场景、物件、调查流程表达。",
    "雷德与其他真实人物只用背影、剪影或手部，不生成可辨认的人脸；受害者不以人像呈现。",
    "案件事实以公开报道与法庭记录为准；已知十名受害者，1974—1991；不把未经证实的其他案件算入本案。",
    "软盘线索是已删除Word文档残留的元数据指向Dennis与Christ Lutheran Church；教会网页上的Dennis Rader信息帮助警方锁定嫌疑人。",
    "女儿的医学样本只提供亲缘DNA线索，不是与凶手身份的直接、完美匹配；样本依法令调取，表述克制。",
    "Rader于2005年认罪并被判十个连续终身监禁（最低175年）；不把当庭陈述夸写成无悔或悔罪结论。",
    "中文姓名、数字、标题、标签和字幕全部后期添加；逐镜审阅接触表，畸变、伪字、中途换场等问题不得进成片。",
]
SOURCES = [
    {"id": 1, "url": "https://www.britannica.com/biography/Dennis-Rader", "usage": "10名受害者、BTK含义、职业（Park City法规执行员）、教会及社区活动、2005逮捕认罪与刑期。"},
    {"id": 2, "url": "https://www.nbcnews.com/id/wbna8929452", "usage": "双面生活：教会委员会主席、童子军领队、社区合规执法员；10名受害者、渴望被承认、2005年回顾。"},
    {"id": 3, "url": "https://www.nbcnews.com/id/wbna8367581", "usage": "2005年6月认罪十项一级谋杀；1974—1991年威奇托地区十名受害者；BTK名称由来；法庭认罪陈述。"},
    {"id": 4, "url": "https://www.nbcnews.com/id/wbna6988048", "usage": "软盘、DNA、监控及信件成为线索；Christ Lutheran Church教会电脑、教会委员会主席身份。"},
    {"id": 5, "url": "https://abcnews.com/US/btk-serial-killers-daughter-living-normal-life-upended/story?id=60428529", "usage": "警方调取女儿大学健康中心医学记录与Pap smear样本进行DNA比对，作为亲缘线索。"},
    {"id": 6, "url": "https://www.nbcnews.com/id/wbna8367581", "usage": "2005年认罪后于同年8月被判十个连续终身监禁。"},
    {"id": 7, "url": "https://apnews.com/article/829a18809b06467eae4c10337885c079", "usage": "1974—1991年在威奇托杀害十人；2005年逮捕；十个连续终身监禁。"},
    {"id": 8, "url": "https://www.kansas.com/news/special-reports/btk/article225082655.html", "usage": "威奇托鹰报对BTK身份、教会委员会主席、Park City法规执行员、案件时间线与DNA线索的整理。"},
]

CHAPTERS = [
    ("N01", "黄金开头：软盘里的名字", "一个教会领袖，亲手把自己的名字塞进证据里。二零零五年，BTK杀手寄给电视台一张三点五英寸软盘，还先问警察：这东西能追到寄件人吗？他等来的不是答案，是九天后的手铐。更离谱的是，出卖他的线索，藏在他以为已经删掉的文件信息里。BTK案，今天从这张软盘讲起。"),
    ("N02", "模范邻居的另一面", "他叫丹尼斯·雷德，住在堪萨斯州威奇托附近，有妻子和孩子。教会会众委员会主席、童子军领队、帕克城法规执行员——邻居看到的是一个讲规矩、管社区的人。可一九七四年至一九九一年间，威奇托地区有十人遭他杀害，其中包括奥特罗一家四口。整齐的日常与连环暴行，竟装在同一个人身上。"),
    ("N03", "BTK三个字母", "BTK不是警方起的名字，而是雷德自己取的缩写：Bind，捆绑；Torture，折磨；Kill，杀害。案件细节很残酷，我们不复现。警方后来确认，他会预先挑选目标、踩点，趁人独自在家时下手；作案后还留下信件和线索，向媒体、警方炫耀。案件始于一九七四年，最后一起已知命案发生在一九九一年。然后，他突然沉默，调查也陷入漫长冷案。"),
    ("N04", "重新出现的挑衅者", "十三年后，他在二零零四年重新写信挑衅，想让人们记起BTK。他向警方问：把文件放进软盘，能查到是哪台电脑吗？警方通过报纸广告给了他模糊保证。二零零五年二月，他把软盘寄到威奇托一家电视台。取证人员恢复被删的Word文件，元数据里出现两条线索：Christ Lutheran Church，和修改者Dennis。教会网页上的一个名字，让冷案第一次有了明确嫌疑人。"),
    ("N05", "DNA把线索串起来", "但软盘指向嫌疑人，不等于足以定罪。调查员继续找独立证据：警方依法调取雷德女儿在大学诊所留下的医学样本，进行亲缘比对。结果显示，案发现场DNA与她有亲缘关联，指向她的父亲。注意，这不是女儿样本与凶手“完美匹配”，而是帮助警方锁定雷德。二月二十五日，丹尼斯·雷德被捕。数字取证给出名字，DNA提供关键支撑。"),
    ("N06", "认罪、判决与反思", "六月，雷德在法庭上承认十项一级谋杀罪，并平静、细节化地陈述案情；同年八月，法院判处十个连续终身监禁，最低服刑一百七十五年。答案不是天才警探瞬间破案：数十年证物、数字取证和DNA，最后被他对关注的渴望串在一起。你觉得最致命的，是软盘元数据，还是他停不下来的炫耀？评论区说说。"),
]

# 每镜：(id, kind, camera, purpose, transition, prompt_or_card, sfx)。共45镜：38个Agnes动画 + 7张后期信息卡。
SHOTS = [
    ("S01", "agnes", "缓慢推近 slow push-in", "0—5秒黄金钩子：黑暗取证桌上，一张旧软盘滑进冷光，软盘标签不可读", "软盘边缘匹配切取证工作站", "A vintage 3.5-inch computer floppy disk is unmistakably visible: a small, nearly square black hard-plastic cartridge about 9 cm by 9 cm, with straight edges and a tiny silver sliding shutter in one corner. Show its complete square outline flat on a dark forensic evidence desk under a cool desk lamp as a gloved hand slides it into the light and withdraws. No optical media: no circle, no center hole, no reflective ring, no CD or DVD. No label or writing. Slow macro push-in, one unchanged tabletop and one continuous shot.", "开场0.3秒留白后软盘滑桌声，低频脉冲起"),
    ("S02", "agnes", "微距焦点转移 rack focus", "调查员翻转软盘，屏幕冷光里出现文件属性窗口的抽象色块（不可读）", "屏幕光溶到教堂窗户", "Locked macro view of gloved fingertips holding a real 3.5-inch floppy disk: its full nearly-square black plastic cartridge and small silver corner shutter are clearly visible, about 9 cm square. Turn the square cartridge once beside an old beige desktop computer; a CRT glow reflects only as soft abstract blocks. No circular optical disk, no center hole, no shiny ring, no letters, numbers, logos or text. The beige computer case and CRT bezel are completely blank molded plastic: no printed model numbers, no brand names, no letters or digits anywhere in the frame, and the screen shows only soft abstract blocks of light, never characters. One gentle rack focus from the square disk's shutter to the screen glow; hands anatomically natural, one continuous shot.", "软盘咔嗒声；屏幕电子嗡鸣"),
    ("S03", "agnes", "缓慢横移 slow lateral slide", "年代提示：二零零五年的小型地方电视台收件台，信封和软盘静置，无可读信件", "桌面横移接教会走廊", "Interior of a modest Wichita local television newsroom in 2005. On a reception counter is an unmarked padded envelope beside one unmistakable 3.5-inch floppy disk: small, nearly square black plastic cartridge with straight edges and a tiny silver shutter at one corner, full square outline visible. CRT monitor glows softly in the background. No round optical discs, no CD/DVD, no center hole, no labels, logos, letters or numbers, no people. Slow lateral slide, one continuous room and composition.", "纸信封落桌声，新闻编辑室低底噪"),
    ("S04", "graphic", "信息卡 static card", "悬念信息卡：BTK · 软盘 · 元数据", "卡片咔声切威奇托街区", "悬念：一张软盘，暴露一个名字", "卡片低音敲击，字卡依旁白出现"),
    ("S05", "agnes", "航拍缓慢前移 aerial drift", "威奇托小城全景：中西部平坦街道、低矮屋顶与水塔，清晨阴天", "航拍下降至郊区住宅", "Wide aerial view over 2000s Wichita, Kansas at overcast dawn: flat horizon, low residential roofs, modest church steeple and distant water tower, muted slate and ochre palette, no readable signs or people. Slow, steady forward aerial drift, no scene change.", "风声渐入，远处钟声"),
    ("S06", "agnes", "低机位推近 low dolly", "教会领袖的象征：空教会礼堂，讲台旁放着一本合上的圣经与木椅", "讲台暗部切人物档案卡", "Quiet Midwestern Lutheran church sanctuary before service, empty wooden pews, simple pulpit and one closed plain book with no visible writing, cool morning light through stained glass; absolutely no people. Low, slow dolly toward the pulpit, hold a single interior.", "极轻教堂钟声，音乐留悬念"),
    ("S07", "agnes", "固定远景 static wide", "安静住宅街上的一名中年男性背影，提公文包走向独栋房屋，不露脸", "背影过门廊硬切人物卡", "A middle-aged man seen only from behind walks along a quiet Park City, Kansas residential sidewalk carrying a plain briefcase toward a modest ranch house; tree-lined flat suburb, no other figures, no signs or license plates. Locked wide shot, only the man walks slowly, face never visible.", "脚步声、树叶风声"),
    ("S08", "graphic", "档案卡 static card", "人物档案信息卡：丹尼斯·雷德、教会与社区职务、威奇托地区", "卡片硬切家庭街景", "丹尼斯·雷德\n教会会众委员会主席 · 童子军领队\n帕克城法规执行员 · 堪萨斯州威奇托地区", "打字机轻响，姓名处重音"),
    ("S09", "agnes", "缓慢升镜 crane up", "普通家庭的抽象日常：郊区餐桌上两只咖啡杯、儿童作业本、空椅子", "儿童作业本翻页接社区办公室", "A quiet family dining table in a modest Kansas home, two coffee cups, a closed school notebook with blank pages, an empty chair and warm ceiling light; no people, no legible writing. Slow crane rise from tabletop to the softly lit empty room, single location.", "餐具轻碰，音乐温暖后转冷"),
    ("S10", "agnes", "固定中景 static medium", "公园城合规执法办公室：卷尺、房屋图纸、文件夹，执法员只见背影", "文件夹合上切街区", "Small Park City municipal code office in the 1990s, a code officer seen from behind studying house plans at a desk with measuring tape and blank folders; no readable labels, no faces. Static medium framing, a single page turns, hold the same office.", "纸张翻动，墙钟滴答"),
    ("S11", "agnes", "缓慢横移 slow pan", "童子军活动的远景示意：树林空地与整齐摆放的帐篷，不出现儿童面孔", "帐篷布纹匹配到案件时间轴", "A calm Kansas scout camp clearing in soft afternoon light, empty canvas tents, a small campfire ring with no fire, trees moving slightly in the wind; no people, no badges or readable marks. Slow pan across the empty campsite, documentary illustration, no scene change.", "林间鸟鸣，旋律压暗"),
    ("S12", "agnes", "缓慢拉远 slow pull-back", "邻居视角：整齐草坪、门廊与停着的普通轿车，强调寻常表象", "车库暗部接时间线卡", "Eye-level view of an ordinary 1970s-1990s Park City ranch house, neat lawn, simple porch, one unmarked sedan in the drive, flat Midwestern neighborhood; no visible people, no signs. Slow pull-back from porch details to the full quiet facade, one continuous shot.", "洒水器、远处狗叫"),
    ("S13", "graphic", "时间轴卡 static card", "案件时间卡：1974—1991年、十名已确认受害者", "时间线末端切空街道", "案件时间线\n1974—1991年 · 威奇托地区\n十名已确认受害者，包括奥特罗一家四口", "时间轴两端敲击，避免血腥音效"),
    ("S14", "agnes", "缓慢前推 slow push", "一九七四年冬日，奥特罗家住宅外景，仅拍空房屋与冷清门廊", "门廊阴影切家庭日常象征", "A modest Wichita family ranch house in winter 1974, viewed from across the empty street, bare trees, quiet porch and pale grey sky; no people, no police, no violence, no readable address. Slow push-in from sidewalk, restrained documentary illustration, hold the same exterior.", "冬风吹过，音乐断半拍"),
    ("S15", "agnes", "微距横移 macro slide", "家庭相框的纯色背板与四把空椅子的隐喻，绝不露出照片", "空椅子边缘切匿名信件", "A plain opaque wooden picture frame lies face down beside four empty dining chairs in a quiet room. Show only its solid blank backboard: never reveal the front, glass, reflection, photograph, image, face or person. Slow macro slide along the chair backs in soft winter window light; one continuous view, no scene change.", "低沉木质音，克制留白"),
    ("S16", "agnes", "缓慢俯拍 overhead drift", "冷案档案室里成摞旧卷宗与未拆封证物盒，标签全空白", "卷宗纸张翻动切旧报纸", "Overhead view of a cold-case evidence room table with neatly stacked old folders and sealed plain cardboard boxes, blank tabs, dust in fluorescent light; no readable labels, no people. One slow overhead drift across the files, no cut or changing props.", "档案箱落桌、纸页声"),
    ("S17", "agnes", "固定长焦 static telephoto", "威奇托报社旧式编辑台，打字机、空白稿纸和电话，无文字", "电话线匹配到夜间街景", "A 1970s Wichita newspaper desk with a typewriter, blank sheets, rotary telephone and a desk lamp, no readable writing, no people. Locked telephoto frame, only the lamp filament gently flickers, one period-correct room.", "打字机敲键两下后停"),
    ("S18", "agnes", "缓慢横移 slow pan", "街角公用电话亭空置，夜色中霓虹只作模糊光斑，表现警方长期追查", "电话听筒切警方白板", "An empty public telephone booth on a quiet Wichita street at night, rain on glass, distant storefront lights as unreadable bokeh, no person and no readable signs. Slow pan from wet pavement to the silent receiver, a single continuous shot.", "雨声、电话忙音一声"),
    ("S19", "agnes", "缓慢拉远 pull-back", "一排住宅窗户逐渐熄灯，暗示案件在多年间断续发生，不表现作案", "窗灯最后一点光切冷案卡", "Quiet Midwestern residential street at dusk, several modest house windows glow softly as evening settles, no people or vehicles, no signs. Slow pull-back from one lit window to the row of homes, still and nonviolent, no scene change.", "风声，低频持续音"),
    ("S20", "graphic", "冷案卡 static card", "信息卡：已知案件发生于1974—1991；1991后长期沉默", "卡片落点接2004年信件", "案件沉寂\n最后一起已知案件：1991年\n此后沉默十三年，直到2004年重新联系媒体", "卡片音效从脉冲变成纸张落下"),
    ("S21", "agnes", "微距推近 macro push", "二零零四年地方报纸折叠背面、咖啡杯与无字信封的年代暗示", "纸面边缘匹配信封", "A quiet 2004-era Kansas home kitchen table with only a plain unmarked tan envelope and a simple unprinted ceramic coffee cup under a warm lamp. No newspaper, magazine, book, paper sheet, calendar, screen, writing, letters, glyphs, numbers, logos or labels anywhere. No people, hands or faces. Slow macro push toward the envelope's blank surface, one stable composition.", "报纸展开声，短促低音"),
    ("S22", "agnes", "俯拍缓推 overhead push", "神秘来信的象征：无字信封、复印纸与一支铅笔，桌面静物", "铅笔尖指向旧电脑", "Overhead still life of an unmarked envelope, blank photocopy sheets and a plain pencil on a newsroom desk, no writing or handwriting visible. Slow overhead push-in toward envelope flap, no visible people, stable objects.", "信封撕开声，配乐加入节拍"),
    ("S23", "agnes", "固定中景 static medium", "只拍背后键盘与老式电脑，不入人物头脸", "CRT光切报纸广告卡", "Object-only shot in an empty modest 2004 Kansas home office: a beige CRT computer, keyboard and external floppy drive on a wooden desk. A small, nearly-square black 3.5-inch floppy cartridge with a silver corner shutter rests beside the drive; show its square outline clearly. Absolutely no people, body, head, face, profile, hands or reflections. CRT screen blank gray, no text, letters, numbers, glyphs, logos, labels or other readable marks. Locked medium close framing, only the screen glow subtly changes, one room throughout.", "键盘轻敲、老电脑风扇声"),
    ("S24", "agnes", "固定微距 macro static", "旧驱动器与平放桌面的方形软盘静物，读取设备的象征，悬念动作", "软盘金属滑门匹配下一镜电视台", "Macro close-up of a beige 1980s/1990s computer floppy drive gently ejecting one unmistakable 3.5-inch floppy disk. A beige 1980s/1990s external floppy drive sits at the back of a wooden desk; in front of it one vintage 3.5-inch computer floppy disk lies flat on the wood, shutter side up: a small, nearly square black hard-plastic cartridge about 9 cm by 9 cm, straight edges, a shallow square recess in the middle of its face and a tiny silver sliding shutter in one corner. No circle of any color on the disk, no round hub, no white dot, no center hole, no ring; the disk is not inside the drive and nothing is ejected. No hands or people. Locked macro frame, slow push-in, no labels or text, one continuous shot.", "驱动器弹出声，音乐短暂静音"),
    ("S25", "agnes", "缓慢横移 slow dolly", "软盘被装进信封并放入邮寄槽，手只出现到袖口", "信封滑出画面切取证员", "Close-up of a plain padded envelope with no writing being placed into a blue postal drop slot on a quiet Kansas street, only a sleeve and hand visible, no readable marks or logos. Slow lateral move follows envelope into slot, one continuous shot.", "投递箱金属回响，心跳加速"),
    ("S26", "agnes", "手持长焦 telephoto", "电视台收件区，工作人员只见肩背，接过包裹", "包裹落桌切磁盘取证", "Inside a small Wichita TV station mailroom in 2005, a staff member seen only from behind sets one padded envelope on a sorting table beside old broadcast equipment; no logos, no readable text, no face. Gentle telephoto push-in, one room and single action.", "室内广播底噪、包裹落桌"),
    ("S27", "graphic", "破案转折卡 static card", "转折卡：2005年2月软盘送达电视台；元数据出现Dennis与教会线索", "Dennis字样后期出现，切数码取证动画", "破案转折\n2005年2月 · 一张软盘寄到威奇托电视台\n删除文件残留：Dennis · Christ Lutheran Church", "三条线索依次落下，最后一条重音"),
    ("S28", "agnes", "缓慢俯拍 overhead drift", "取证员戴手套将软盘接入取证电脑，手与设备特写，屏幕不可读", "屏幕色块切文件属性", "Forensic workstation in a modest 2005 police lab, gloved hands connect a plain floppy disk to an external drive beside a beige monitor, screen contains only abstract unreadable grey interface blocks. Slow overhead drift, no faces, single desk and movement.", "软盘插入声，设备启动"),
    ("S29", "agnes", "屏幕微距 slow macro push", "数字取证示意：屏幕上文件属性面板的抽象层叠方块，不出现伪文字", "画面淡出到便笺", "Extreme close-up of a CRT monitor showing layered abstract file-property panels represented only by blurred grey rectangles and colored pixels, absolutely no legible letters or numbers; dark forensic lab reflections. Very slow push-in, no interface changes or cut.", "电子扫描音逐渐上升"),
    ("S30", "agnes", "缓慢横移 slow pan", "大学诊所走廊空镜：亲缘比对样本的来源以中性、非侵入方式示意", "走廊冷光切实验室样本", "A quiet university health clinic hallway in Kansas, late afternoon, a closed blank consultation-room door and empty chairs, no people, no medical procedure, no signs or readable text. Slow lateral pan toward a frosted glass door, restrained documentary animation, one continuous hallway.", "鼠标点击两声，音乐留白"),
    ("S31", "agnes", "宏观俯拍 slow overhead", "实验室准备匿名DNA样本管，不出现人体或可读标签", "样本管反光切亲缘关系卡", "Forensic laboratory bench with two sealed clear sample tubes, gloved hands placing them side by side beside a simple microscope; no visible biological material, no readable labels, no faces. Slow overhead move, cool clean lab light, one stable workbench.", "教堂钟声一次，风声"),
    ("S32", "agnes", "微距焦点转移 rack focus", "抽象亲缘关系示意图：两代轮廓线连线，无姓名与可读文字", "连线落点切住宅监视视角", "A forensic analyst's hand places two plain blank family-tree cards side by side on a desk and draws one thin connecting line between them; no names, letters, numbers or identifiable people. Macro rack focus from the pencil tip to the connection, one continuous tabletop shot.", "纸张轻响，悬念鼓点"),
    ("S33", "agnes", "长焦固定 telephoto static", "调查员从车内远距离观察普通住宅，窗帘与树枝遮挡，不出现正脸", "住宅窗格切DNA卡", "View from inside an unmarked parked car across a quiet Park City street toward an ordinary ranch house, seen through a few soft-focus branches; no occupants, no readable address, no license plates. Locked telephoto view with subtle natural breathing, no pan or cut.", "车内转向灯轻响，远处鸟鸣"),
    ("S34", "graphic", "逮捕信息卡 static card", "软盘与亲缘DNA调查线索汇合，丹尼斯·雷德于2005年2月25日被捕", "日期落版切实验室证据复核", "丹尼斯·雷德被捕\n2005年2月25日\n软盘与亲缘DNA线索汇合", "心跳声转成稳定节拍；强调“亲缘关联”"),
    ("S35", "agnes", "宏观俯拍 slow overhead", "实验室样本管与封存证物并列，标签空白，示意DNA复核", "玻璃样本管反光切抓捕街景", "A clean forensic laboratory bench in cool blue light, close overhead composition on one plain sealed evidence envelope with a completely blank face beside an empty clear glass beaker and one shallow clear petri dish. No sample tubes, no vials, no caps, no biological material, no hands, no people, no labels, no white bands, no barcodes, no writing, no numbers, no symbols, no screens or instrument readouts. Keep all surfaces unmarked. Slow overhead drift across the beaker and envelope, one lab only.", "实验仪器提示音，低音稳定"),
    ("S36", "agnes", "缓慢推近 slow push-in", "2005年六月法庭外景：空走廊尽头的木门与法庭标识空白", "闭合木门切庭内背影", "A quiet Kansas courthouse interior in June 2005, empty wood-paneled hallway leading to closed courtroom doors, a plain wooden bench, no people and no readable signage. Slow push toward the closed door, soft daylight, sober documentary illustration.", "车辆关门声、脚步声，音乐重落"),
    ("S37", "agnes", "固定远景 static wide", "法庭远景：被告席上一名高大背影静立，法官席与旁听席模糊，无正脸", "木质法庭切宣判走廊", "Distant rear view inside a modest Kansas courtroom: one tall male defendant silhouette seen only from behind at the defense table, wooden judge's bench and blurred empty gallery, no identifiable faces, no readable text. Locked wide composition with a slight slow camera drift, restrained and non-sensational.", "日光灯轻嗡，音乐放缓"),
    ("S38", "agnes", "缓慢前推 slow push-in", "法庭外走廊空镜，长椅与木门，不出现真实庭审人物", "木门暗部切认罪卡", "Quiet Kansas courthouse hallway in 2005, polished wood doors, empty benches and a shaft of daylight, no people or signage. Slow push-in toward closed courtroom door, no text, no logos, one continuous location.", "脚步回声由远至近"),
    ("S39", "agnes", "微距拉远 macro pull-back", "法庭桌上合上的记录本与无字证物袋，表达认罪陈述后证据收束", "证物袋边缘切判决卡", "Close-up of a closed court transcript binder with blank cover and a sealed plain evidence pouch on a wooden courtroom table, no writing, no person. Slow pull-back to reveal empty judge's bench in soft focus, no scene change.", "纸页合拢、木槌轻敲一次"),
    ("S40", "agnes", "静态剪影 static silhouette", "监狱走廊尽头铁门关闭，非真实监狱影像", "铁门黑场切片尾卡", "A long Kansas prison corridor in muted blue-grey, solid concrete walls and one heavy barred door slowly closing at the far end; no people, no signage, no readable text. Locked symmetrical shot, gentle door movement only, hold at closed door.", "铁门缓慢合拢，尾音延长"),
    ("S41", "agnes", "缓慢横移 slow slide", "软盘重新放回证物盒，与旧信件并列，象征破案的关键物证", "软盘标签区域淡出切最终卡", "An unmarked evidence tray on a dark forensic table holds one vintage 3.5-inch computer floppy disk beside a plain envelope: a small, nearly square black hard-plastic cartridge about 9 cm by 9 cm, with straight edges and a tiny silver sliding shutter in one corner. Show its complete square outline under a warm desk lamp. No optical media: no circle, no center hole, no reflective ring, no CD or DVD. No label or writing. Slow lateral slide across the evidence, one continuous composition.", "开头的软盘音效轻微回响"),
    ("S42", "graphic", "证据链卡 static card", "总结破案关键：软盘元数据、教会线索、亲缘DNA与长期调查", "卡片暗下来接空荡街道", "破案证据链\n软盘元数据 · 教会线索\n亲缘DNA · 长期侦查", "木槌声后音乐释压"),
    ("S43", "agnes", "缓慢拉远 slow pull-back", "空荡的威奇托住宅街在暮色中，象征冷案告终与社区余波", "路灯光点转入软盘画面", "A quiet Wichita residential street at blue-hour dusk, ordinary ranch houses, trees and one streetlamp turning on, no people, no cars, no readable signs. Slow pull-back toward the empty intersection, restrained muted palette, one continuous shot.", "夜虫声渐起"),
    ("S44", "agnes", "微距固定 macro static", "旧软盘在抽屉里被缓缓推回，保留技术证据的象征性收束", "抽屉合上时音乐停", "Close view inside an open wooden evidence drawer: one unmistakable 3.5-inch floppy disk lies flat, its small nearly-square black plastic cartridge and tiny silver corner shutter fully visible. The disk has straight square edges, not a circle; no CD/DVD, vinyl record, hole or reflective ring. A gloved hand grips only the drawer handle and pulls the drawer slowly closed; the hand never touches the disk, the rigid disk stays perfectly flat on the wood and disappears behind the drawer front; the clip ends holding on the closed dark wood front. No labels, papers, text or faces. Locked macro frame, slow controlled drawer movement, hold on dark wood after closing.", "抽屉滑轨声，短暂停顿"),
    ("S45", "agnes", "缓慢推近 slow push-in", "空无一人的教堂长椅与窗上晨光，回到双面人生的反思", "推近至窗光淡出片尾问题卡", "Empty Lutheran church sanctuary at first morning light, rows of wooden pews, muted stained-glass reflections and a quiet pulpit, no people, no readable inscriptions. Very slow push-in from the back aisle, warm light fades gently, hold final composition.", "钟声微弱一响，片尾音乐渐隐"),
]

CARD_HEADER = "BTK案件档案  /  堪萨斯州威奇托"
CARD_FOOTER = "依据公开报道与法庭资料整理 · AI动画情景重现"
CARDS = {
    "S04": ("一张软盘", "一个问题：能追到哪台电脑？", "答案藏在被删文件的元数据里"),
    "S08": ("丹尼斯·雷德", "教会会众委员会主席 · 童子军领队", "帕克城法规执行员 · 威奇托地区"),
    "S13": ("1974—1991", "十名已确认受害者", "包括奥特罗一家四口"),
    "S20": ("沉默十三年", "最后一起已知命案：1991年", "2004年重新联系媒体"),
    "S27": ("软盘里的线索", "Dennis", "Christ Lutheran Church"),
    "S34": ("锁定与逮捕", "2005年2月25日 · 丹尼斯·雷德被捕", "软盘与亲缘DNA线索汇合"),
    "S42": ("破案证据链", "软盘元数据 · 教会线索", "亲缘DNA · 长期侦查"),
}
TITLE_CARD = ["BTK：软盘里的名字", "一个连环杀手，栽在自己寄出的元数据"]
END_CARD = ["最致命的是软盘，还是他停不下来的炫耀？", "BTK案 · 威奇托 · 1974—1991", "你删掉的文件，也许还在替你说话。", "资料：NBC News · ABC News · Britannica · AI动画情景重现"]
CAPTION_KEYWORDS = ["丹尼斯·雷德", "十名", "Bind", "元数据", "Dennis", "Christ Lutheran Church", "亲缘DNA", "175年"]
LABEL_OVERRIDES = {
    "S28": "AI动画示意 · 非真实取证影像", "S29": "AI动画示意 · 非真实屏幕画面",
    "S35": "AI动画示意 · 非真实实验室影像", "S36": "AI动画示意 · 非抓捕影像",
    "S38": "AI动画示意 · 非庭审影像", "S40": "AI动画示意 · 非监狱实拍",
}
SFX_EVENTS = [("S24", "machine"), ("S27", "press"), ("S35", "machine"), ("S39", "press"), ("S40", "keys")]
TITLES = [
    "BTK杀手栽了：一张软盘，暴露隐藏30年的名字",
    "他问警方软盘能不能追踪，结果元数据出卖了他｜BTK案",
    "教会领袖、社区执法员，竟是BTK杀手？破案关键藏在软盘里",
]
HOOK = "一个渴望被关注的连环杀手，主动寄出软盘，却忘了被删除文件的元数据仍能指向他的教会和名字。"
GOLDEN_LINES = ["文件可以删，痕迹未必会消失。", "他以为自己在操控警方，最后却把线索亲手寄了出去。", "你觉得最致命的是软盘元数据，还是他停不下来的炫耀？"]
DESCRIPTION = "三十年的冷案，最后被一张软盘撬开。丹尼斯·雷德一面是教会领袖、社区法规执行员，一面是BTK杀手。被删掉的Word文档留下元数据，警方再以亲缘DNA线索核实嫌疑人。片中画面均为AI动画情景重现，不是新闻或庭审影像。你认为真正的转折是什么？"
QUESTION = "你觉得最致命的，是软盘元数据，还是他停不下来的炫耀？"
HASHTAGS = ["#BTK", "#真实案件", "#悬疑科普", "#数字取证", "#冷案"]
GRID = 4
AGNES_SECONDS = 7
SEED_BASE = 20050225


def presentation():
    return {"card_header": CARD_HEADER, "card_footer": CARD_FOOTER,
            "cards": {sid: list(lines) for sid, lines in CARDS.items()},
            "title_card": TITLE_CARD, "end_card": END_CARD,
            "caption_keywords": CAPTION_KEYWORDS, "label_overrides": LABEL_OVERRIDES,
            "sfx_events": [list(e) for e in SFX_EVENTS]}


def build():
    story = json.loads(PLAN.read_text(encoding="utf-8"))
    assert len(SHOTS) == 45 and len(CHAPTERS) == 6
    assert len({s[0] for s in SHOTS}) == 45
    assert sum(s[1] == "agnes" for s in SHOTS) == 38
    assert sum(s[1] == "graphic" for s in SHOTS) == 7
    assert {s[0] for s in SHOTS if s[1] == "graphic"} == set(CARDS)
    story.update(title=TITLE, style_prefix=STYLE_PREFIX, negative_prompt=NEGATIVE_PROMPT,
                 principles=PRINCIPLES, sources=SOURCES)
    for target, (cid, chapter_title, text) in zip(story["chapters"], CHAPTERS):
        assert target["id"] == cid
        target["title"], target["text"] = chapter_title, text
    shots = []
    for i, (sid, kind, camera, purpose, transition, body, sfx) in enumerate(SHOTS):
        assert sid == f"S{i+1:02d}" and kind in ("agnes", "graphic")
        start = i * GRID
        shots.append({"id": sid, "kind": kind, "start": start, "duration": GRID,
                      "narration_id": ("N01" if i < 6 else "N02" if i < 13 else "N03" if i < 20 else "N04" if i < 27 else "N05" if i < 35 else "N06"),
                      "prompt": (body + " The entire clip remains in this single location and framing: one continuous shot, no cut, no scene change, no camera relocation; hold the final composition.") if kind == "agnes" else "",
                      "purpose": purpose, "transition_out": transition,
                      "graphic": "\n".join(CARDS[sid]) if kind == "graphic" else "", "seed": SEED_BASE + i,
                      "seconds": AGNES_SECONDS, "aspect": "16:9", "resolution": "1080p",
                      "frame_rate": 24, "camera": camera, "sfx_note": sfx})
    story["shots"] = shots
    story["presentation"] = presentation()
    story["_scaffold"]["note"] = "45镜×4秒规划网格；38个Agnes动画镜头+7张信息卡；口播必须与manifest逐字一致。"
    PLAN.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for clip, chapter in zip(manifest["clips"], story["chapters"]):
        clip["text"] = chapter["text"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chars = sum(len(ch["text"]) for ch in story["chapters"])
    print(f"story.json 已写入：45镜（38 Agnes + 7卡）；口播 {chars} 字（含标点）")


if __name__ == "__main__":
    if "--script" in sys.argv:
        from script_table import render_document
        out = HERE / "抖音脚本.md"
        out.write_text(render_document(), encoding="utf-8")
        print(f"抖音脚本.md 已写入：{out}")
    elif "--publish" in sys.argv:
        from script_table import publish_document
        out = HERE / "抖音发布文案.md"
        out.write_text(publish_document(), encoding="utf-8")
        print(f"抖音发布文案.md 已写入：{out}")
    else:
        build()

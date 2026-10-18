#!/usr/bin/env python3
"""《红衣杀手杨树明：14年，9名女性遇害，警方如何撕开他的伪装？》的全部内容源。

这是这部片子**唯一需要动脑写的文件**（引擎由 production/kitakyushu2002 北九州模板移植而来，
内容按用户上传的 30 镜文案稿（抖音文案/20261018-005748_粘贴的文案_20261018-005748.txt）改写，
事实按 SOURCES 里的公开来源核对，见 史实核对.md；用户稿 1642 字口播超出 180 秒容量，
按模板六章结构压缩到 ≈780 字，剧情骨架与关键事实全部保留）。

用法::

    python3 production/yangshuming/build_story.py            # 写 story.json（含 presentation 块）+ audio/manifest.json 的逐字文本
    python3 production/yangshuming/build_story.py --script   # 生成 抖音脚本.md（3 标题 / 核心爆点 / 四列分镜表 / 金句）
    python3 production/yangshuming/build_story.py --publish  # 生成 抖音发布文案.md（标题 / 介绍 / 提问读者一句话 / 话题）

本片是**露脸模式**：三个角色各一张不同的脸，同一角色跨镜头逐字节复用同一条面容 token
（token 只在 cast.json 里写一份，本文件用 {C1}…{C3} 占位符注入，保证逐字节一致），
并复用同一个 seed；由 production/face_cast.py 的 check-prompts / check-frames 两道闸门守着。
受害者全程只以背影、剪影、物件出现；杨树明本人不做肖像还原，由虚构匿名角色 C1 扮演。

视频模型走**智谱 CogVideoX-Flash 免费档**（generate_cogvideox.py，仓库 secret ZHIPUAI_API_KEY，
不调 Agnes、不产生费用）。

分镜与解说逐句咬合的章法（45 镜 = 38 动态 + 7 信息卡，每章镜头只服务本章解说词）：
  N01 红衣之下（S01-S08）· N02 凶手没有消失（S09-S15）· N03 线索收拢（S16-S23）
  N04 沉默被打破（S24-S30）· N05 判决与代价（S31-S38）· N06 留下来的（S39-S45）
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
CAST = HERE / "cast.json"

TITLE = "红衣杀手杨树明：14年，9名女性遇害，警方如何撕开他的伪装？"

# 全片统一的画面风格前缀（英文）。写实 3D CGI 情景重现（不是 2D、不是图片轮播）。
# 注意：style_prefix 参与全部镜头的 request_hash，开工后改一个字 = 38 镜全部重做。
STYLE_PREFIX = (
    "Photorealistic cinematic 3D animated shot, high-end CGI feature-film render with volumetric "
    "light, shallow depth of field and subtle 35mm film grain, set in a northern Chinese coal-mining "
    "town across the 1990s and early 2000s: soot-dark brick apartment blocks and concrete lanes in a "
    "mining compound, a plain communal hall, dim sodium street lamps, coal haze and distant headframes "
    "and slag heaps, cramped period offices with enamel mugs and paper ledgers, plain government "
    "offices and a solemn wood-panelled hall, early-spring snow residue, cold autumn dusk and harsh "
    "northern winters, overcast afternoons and long blue nights, restrained desaturated cold blue-grey "
    "grading with strong chiaroscuro, sober documentary mood, never stylised, never a drawing, never "
    "a cartoon; horizontal 16:9 widescreen composition; characters act with clear full-body movement "
    "in medium and wide shots rather than close-ups; absolutely no readable text, letters, numbers, "
    "logos or brand marks anywhere in frame; one single continuous smooth camera move per shot "
    "exactly as directed. "
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
    "全部动态镜头为写实 3D CGI 动画情景重现，画面常驻标注「AI动画情景重现 · 非新闻影像」，"
    "不冒充搜查、审讯、庭审、发布会或证物影像",
    "不展示遗体、血腥或作案过程：袭击只通过警戒线、勘查标记、背影与物件暗示；"
    "案发现场镜头只出现警方远景勘查，受害者不以任何人像出现",
    "杨树明本人不做肖像还原：情景重现由虚构匿名角色 C1 扮演，片内标签写明「非本人容貌」；"
    "押解、行刑等镜头只给背影或空镜",
    "九名受害者一律不给可辨识面容、不写真实姓名：只以空椅子、折叠的衣物、翻扣的相框、"
    "聚合数字与信息卡致意；「红衣」只作为报道口径的符号出现，不做猎奇渲染",
    "三个露脸角色（嫌疑人替身 / 老刑警 / 法官）各有一张不同的脸；同一角色跨镜头逐字节复用"
    "同一条面容 token 并共用同一个 seed",
    "由 production/face_cast.py 的 check-prompts（静态闸门）与 check-frames（画面闸门）检查，"
    "人眼对照接触表判决；纯文生视频对「同一张脸」不作数，按「同形象」口径诚实记录",
    "每一句事实都能指到 sources 里的公开来源；来源冲突处（首案受害者年龄十六 / 二十六、"
    "末案日期）只写不会写错的写法（「一名下夜班的女工」「二〇〇四年冬天」），不挑一个当结论",
    "测谎（心理测试）只写作侦查措施之一，不当作定罪依据；不编造真实人物对白、供述词与庭审原声",
    "所有中文姓名、日期、字幕后期添加，不交给视频模型拼写；画面内不出现任何可读文字、门牌或招牌",
    "人工检视 qa/ 接触表与 delivery/face-cast/ 人脸接触表；换脸、畸变、伪文字、中途换场的镜头用 "
    "{\"only\":\"Sxx\"} 重生成，不直接进成片",
    "画面与解说都不把犯罪者写成传奇：不美化、不猎奇，落点是九名受害者与「不放弃的排查」",
]

# 每条事实的公开来源。
SOURCES = [
    {"id": 1, "url": "http://news.sina.com.cn/c/l/2006-08-10/19279714701s.shtml",
     "usage": "支撑（新华网 2006-08-10）：阳泉市中级人民法院一审判决——十四年间行凶致 9 死 3 伤，"
              "杨树明因故意杀人罪、抢劫罪分别被判处死刑和有期徒刑十三年，二罪合并执行死刑、"
              "剥夺政治权利终身"},
    {"id": 2, "url": "https://news.sina.com.cn/c/2006-11-22/135210569223s.shtml",
     "usage": "支撑（2006-11-22 报道）：二〇〇六年十一月二十一日九时五十分，阳泉市中级人民法院"
              "宣读判决与山西省高院核准的执行死刑命令，杨树明当日被执行死刑（枪决）"},
    {"id": 3, "url": "https://news.sina.com.cn/c/2006-04-08/02478642970s.shtml",
     "usage": "支撑（海峡都市报转《人民公安报》《山西晚报》 2006-04-08）：山西「红衣杀手」案侦破"
              "——数百名民警十四年奋战，先后杀死 9 人、伤 3 人、作案 12 起；案发集中于阳泉市"
              "矿区马家坪一带；「红衣杀手」为当年媒体称呼"},
    {"id": 4, "url": "https://news.sina.com.cn/c/2006-04-04/04028604693s.shtml",
     "usage": "支撑（新华社太原 2006-04-03 电）：阳泉矿区马家坪地区系列杀人案于 2006 年 4 月 3 日"
              "凌晨告破；被公安部列入重点督办大案；自 1992 年至今作案 12 起、杀死杀伤 12 人"},
    {"id": 5, "url": "https://news.sina.com.cn/s/2006-05-22/09358990868s.shtml",
     "usage": "支撑（2006-05-22）：2006-03-23 杨树明接受中国人民公安大学心理测试中心专家测谎；"
              "03-27 因涉嫌故意杀人被刑事拘留；04-28 经检察机关批准逮捕；经审讯交代十四年间"
              "残害妇女 12 人、致 9 死 3 伤"},
    {"id": 6, "url": "https://en.wikipedia.org/wiki/Yang_Shuming",
     "usage": "支撑（English Wikipedia）：受害者为九名 16 至 42 岁女性；案发集中于阳泉矿区"
              "马家坪（Majiaping, Kuangqu, Yangquan）；犯罪时间跨度 1992—2006；"
              "杨树明 1966 年生，2006-11-21 被执行死刑"},
    {"id": 7, "url": "https://zhuanlan.zhihu.com/p/144903026",
     "usage": "交叉核对（案情梳理，可信度低于通讯社稿，只用于时间线交叉）：1992-03-02 首案；"
              "2005 年专案组重新梳理；2006 年 3 月测谎锁定嫌疑、4 月 3 日宣布告破；"
              "作案 12 起 9 死 3 伤；首案受害者年龄各源不一（十六 / 二十六），片中不写死"},
]

# 六段解说：(章节 id, 章节标题, 逐字解说词)。六段合计 ≈ 780 字（含标点）。
# 内容改写自用户上传的 30 镜文案稿（1642 字），保留全部关键事实与跌宕节奏：
# 钩子 → 恐惧蔓延 → 线索收拢 → 防线崩溃 → 判决 → 受害者落点。
CHAPTERS = [
    ("N01", "红衣之下，谁在黑暗中行走",
     "一九九二年，山西阳泉马家坪。一名下夜班的女工倒在回家的路上。"
     "此后十四年，矿区接连发生针对女性的袭击——凶手，就藏在人群之中。"
     "多起案件里，有报道称多名受害者穿着红色衣物，「红衣杀手」的称呼不胫而走。"
     "可比颜色更重要的，是案件之间的联系。一年又一年过去，案子始终没破。"),
    ("N02", "凶手没有消失",
     "凶手没有消失。工人照常上班，孩子照常上学；可夜色一降，脚步声就让人发怵。"
     "杨树明，山西寿阳人，在当地企业上班——有工作，也有家庭。"
     "没有人能从表象里看清他的罪行。二〇〇一年，一名女工下班后失踪，几天后被发现遇害。"
     "二〇〇四年冬天，悲剧再次上演。一次次排查走访，案件迟迟没有突破。"),
    ("N03", "十四年，线索开始收拢",
     "二〇〇五年警方重新组建专案力量。这一次不再只盯单起案件——"
     "而是把十四年来的案发地点、时间、受害者情况放在一起比对。"
     "地图上的标记逐渐连成一片，嫌疑范围一轮轮缩小。"
     "杨树明进入重点视野：他住在案发区域附近。"
     "询问、比对资料、心理测试……多种线索逐渐汇合，调查，逼近关键节点。"),
    ("N04", "沉默终于被打破",
     "二〇〇六年三月，杨树明与其他重点对象接受调查。面对询问，他一度相当镇定。"
     "可随着线索一寸寸拼合，他的从容开始出现裂缝。"
     "据当年媒体报道，三月底前后，他开始交代犯罪事实。"
     "调查最终确认：十二起案件，九名女性死亡、三人受伤——"
     "十四年的恐惧，终于有了责任人。"),
    ("N05", "判决与代价",
     "二〇〇六年四月，阳泉警方宣布案件告破。同年，杨树明被依法逮捕，案件进入司法程序。"
     "庭审中，他对主要犯罪事实供认不讳。"
     "八月十日，一审判决：故意杀人罪死刑，另因抢劫罪判处有期徒刑，数罪并罚，执行死刑。"
     "十一月二十一日，杨树明被执行死刑。十四年的系列案件，至此终结。"),
    ("N06", "真正留下来的",
     "案件终结，矿区的生活还要继续。可对家属来说，痛不会随判决消失。"
     "九名遇害女性，从十六岁到四十二岁——她们原本都有自己的生活和未来。"
     "侦查从来没有戏剧性的瞬间：它来自一遍遍的走访、档案，和对旧线索的不放弃。"
     "「红衣杀手」让人记住了案子，却不该盖住事实——受害者不是符号，是真实的人。"),
]

HOLD = ("no cut, no scene change, no camera relocation, no extra people, "
        "no readable text in frame; hold on this single view for the full clip.")

SHOTS = [
    # ---------------- N01 红衣之下（S01-S08：7 动态 + 1 信息卡）----------------
    ("S01", "agnes", "高空俯冲推进至俱乐部门口街道", "钩子：一九九二年，阳泉矿区之夜",
     "接信息卡：案件名片",
     "A wide cinematic establishing shot of a northern Chinese coal-mining district at night in the "
     "early 1990s: soot-dark brick apartment blocks and a plain concrete communal hall with a bare "
     "entrance, dim sodium street lamps, light snow residue on the ground, coal headframes and slag "
     "heaps silhouetted against a cold sky, one small red cloth caught by the wind tumbling across the "
     "empty street, no people visible anywhere; the camera starts high above the district and slowly "
     "swoops down and forward toward the empty hall entrance, " + HOLD,
     "寒风、远处工业机器低鸣、沉重低音"),
    ("S02", "graphic", "—", "信息卡：案件名片（时间/地点/规模）", "接第一案勘查",
     "案件档案卡", "低沉鼓点"),
    ("S03", "agnes", "远景推近至地面标记", "第一案：警方清晨勘查（尊重性、非血腥）",
     "接恐惧蔓延",
     "A wide restrained dawn investigation view on a cold early-spring morning in the early 1990s at "
     "a corner of a bare concrete square in a northern Chinese mining compound marked off by a plain "
     "rope barrier, no shopfronts and no vehicles anywhere: two Chinese officers in plain green-grey "
     "uniforms work at a respectful distance from the camera, one officer crouching to place small "
     "numbered markers on the ground, another writing on a clipboard, their faces turned away from "
     "the camera the whole time, bare trees and snow residue around; a slow steady push-in from the "
     "wide view that settles on the officer's hands placing the markers, " + HOLD,
     "脚步声、翻动记录本、低沉弦乐"),
    ("S04", "agnes", "横向跟拍下班人群，逐渐拉远", "恐惧扩散：马家坪居民的不安",
     "接红衣意象",
     "A residential compound in a northern Chinese mining district at dusk in the early 1990s: a "
     "narrow concrete path between two rows of soot-dark brick apartment blocks, three women in plain "
     "padded coats walking home from a shift seen only from behind, a bicycle leaning on a wall, coal "
     "dust in the cold air, warm dim light in a few windows, no shops, no vehicles and no signs "
     "anywhere; a slow lateral tracking move following the walking figures from behind and gradually "
     "widening to reveal the grey sprawling compound, " + HOLD,
     "自行车铃声、远处谈话声、压迫感渐强的音乐"),
    ("S05", "agnes", "红衣特写，缓慢横移", "红衣传闻：符号而非猎奇",
     "接地图案头",
     "Close view of a plain red cotton-padded coat hanging on a wire clothesline outside a modest "
     "brick apartment window, wind gently moving the fabric, soot-dark brick wall and a cold overcast "
     "sky behind, a coal-mining headframe far in the misty background, no people and no text anywhere; "
     "the camera drifts slowly sideways past the coat then eases back to frame it alone against the "
     "bleak skyline, " + HOLD,
     "风吹布料声、铅笔划过纸面"),
    ("S06", "agnes", "俯拍案头地图，缓慢推近标记簇", "案头资料：地图与图钉（调查伏笔）",
     "接时间跳跃",
     "Directly overhead view of a wooden desk in a plain Chinese investigation office at night in the "
     "1990s: a large hand-drawn district map pinned flat with small coloured map pins, blank paper "
     "file folders fanned open, a pencil, reading glasses and an enamel mug, one desk lamp casting a "
     "warm pool of light in the dark room, a pair of hands entering frame to move one pin, no faces "
     "visible and no readable writing on any paper; a slow top-down drift across the map toward the "
     "cluster of pins, " + HOLD,
     "纸张摩擦、铅笔划线声"),
    ("S07", "agnes", "固定机位时间流逝", "时间跳跃：季节轮换，案子未破",
     "接旧日历",
     "A fixed wide shot of one soot-dark brick apartment building and its bare concrete courtyard in a "
     "northern Chinese mining compound passing slowly through the seasons: light snow on the ground "
     "melting into wet spring pavement, then dry autumn dust, then snow again, weak sunlight sliding "
     "across the brick facade, two tiny anonymous residents passing far below, no close faces, no "
     "signs; the camera stays completely still in one wide composition while the light and weather "
     "slowly change across the courtyard, " + HOLD,
     "钟表滴答、风声渐强"),
    ("S08", "agnes", "缓慢推近翻动的日历", "章末悬念：翻过去的，是一页页时间",
     "接第二章日常",
     "Close view of a cheap paper wall calendar hanging on a whitewashed wall in a plain home in the "
     "1990s, its blank grid pages flipping softly one after another in a draught, a small enamel "
     "clock beside it, warm dim indoor lamp light from one side, no people and no readable printing; "
     "a very slow push toward the flipping calendar pages and the clock, " + HOLD,
     "翻页声、时钟滴答"),

    # ---------------- N02 凶手没有消失（S09-S15：6 动态 + 1 信息卡）----------------
    ("S09", "agnes", "跟随下班工人，转向幽暗巷口", "日常表象：平静之下的不安",
     "接红衣传闻卡",
     "Early evening in a northern Chinese mining compound in the early 2000s: workers in plain padded "
     "jackets walking home through a concrete courtyard, old bicycles parked in a row, a woman "
     "pausing at the mouth of a dim narrow alley between two brick blocks and glancing down it, all "
     "faces away from camera or in shadow, no shops, no vehicles and no signage anywhere; a slow "
     "follow move behind the walking workers that drifts toward the dark alley mouth, " + HOLD,
     "自行车链条声、远处犬吠、微弱风声"),
    ("S10", "graphic", "—", "信息卡：「红衣杀手」称呼的由来与事实边界", "接凶手另一面",
     "红衣传闻卡", "风吹布料声"),
    ("S11", "agnes", "从工装细节缓慢抬升至侧脸", "凶手的另一面：表象平静的 C1（替身）",
     "接二〇〇一年案件",
     "Inside a modest northern Chinese mining apartment at evening in the 1990s — a small plain room "
     "with a square table, an enamel mug, a folded work jacket on a chair, patterned curtains and a "
     "wall lamp casting warm light, the whole shot staying indoors from the first frame to the last "
     "with no exterior, no building facade and no transition: the Chinese man {C1}, wearing a plain "
     "grey-blue work jacket, stands by the table shown from the waist up, calmly folding the jacket, "
     "his ordinary face visible in soft lamplight; a slow tilt up from his hands on the jacket to his "
     "calm impassive face, " + HOLD,
     "室内钟表声、远处工业机器声"),
    ("S12", "agnes", "从背后跟拍女工走远", "二〇〇一年：女工下班后失踪",
     "接警戒线远景",
     "A cold overcast afternoon at a plain roadside bus stop pole on the edge of a northern Chinese "
     "mining district in the early 2000s: an ordinary woman in a dark winter coat and shoulder bag "
     "walks away from camera down a wet concrete road, a plain grey bus receding far into the distance "
     "behind her, industrial silhouettes and slag heaps on the horizon, no readable lettering anywhere "
     "and her face never visible; the camera follows her from behind for a few slow steps, then holds "
     "as the bus shrinks down the road, " + HOLD,
     "公交车远去声、刹车声，随后低沉静默"),
    ("S13", "agnes", "沿警戒绳横移", "非血腥现场：只有界绳与背影",
     "接警方压力",
     "A wide respectful view of a residential corner in a northern Chinese mining compound at dusk: a "
     "plain rope barrier strung between two poles across a concrete path, two officers in dark "
     "uniforms standing beyond it seen only as distant silhouettes from behind, an empty courtyard, "
     "bare trees and distant brick blocks, no bodies, no close faces and no readable text; a slow "
     "lateral drift along the barrier line that keeps the figures small and distant, " + HOLD,
     "风声、远处对讲机杂音"),
    ("S14", "agnes", "俯拍资料桌，拉远至满墙资料", "警方压力：C2 与堆积如山的旧案",
     "接最后一次袭击",
     "Inside a cramped Chinese investigation office in the mid-2000s — fluorescent tubes overhead, a "
     "wall map with pins, stacked blank paper folders and ledgers covering two desks, enamel mugs, an "
     "old telephone, the whole shot staying indoors from the first frame to the last with no exterior, "
     "no building facade and no transition: the veteran detective {C2} stands over a desk in a plain "
     "dark jacket shown chest-up, his tired weathered face clearly visible as he studies the papers, a "
     "second officer's turned back in the background; a slow push across the cluttered desk toward the "
     "detective's tired face, " + HOLD,
     "翻页声、电话铃声、笔尖敲桌"),
    ("S15", "agnes", "跟随夜巡队前行", "二〇〇四年冬天：巡防加压",
     "接第三章专案组",
     "A cold wet November night on a narrow residential lane in a northern Chinese mining compound in "
     "the mid-2000s: two uniformed patrol officers in dark winter coats walking slowly away from "
     "camera along the wet concrete lane, street-lamp reflections shimmering in puddles, soot-dark "
     "brick blocks on both sides and coal silhouettes beyond, no signage anywhere; a slow steady "
     "tracking move following the patrol from behind as their torch beams sweep the walls, " + HOLD,
     "靴子踩过湿地、对讲机杂音、低音弦乐"),

    # ---------------- N03 线索收拢（S16-S23：7 动态 + 1 信息卡）----------------
    ("S16", "agnes", "从门口推进办公室，停在长桌", "专案组重新集结（二〇〇五）",
     "接十四年卡",
     "Inside a plain shared working room in a Chinese government building in the mid-2000s — a long table covered with blank folders and pinned papers, a large district map on the wall with coloured pins, a thermos and enamel mugs, daylight from tall windows, the whole shot staying indoors from the first frame to the last with no exterior, no building facade and no transition: four men in plain clothes gather around the table sorting papers and passing folders, seen mostly from behind or in profile, one figure pointing at the map; a slow push from the doorway toward the map wall,  " + HOLD,
     "椅子移动声、纸张声、低沉鼓点"),
    ("S17", "graphic", "—", "信息卡：一年又一年（十四年悬案）", "接地图红点",
     "十四年卡", "时钟滴答"),
    ("S18", "agnes", "俯拍缓慢推近标记密集区", "地图上的红点：空间关联浮现",
     "接档案海",
     "Directly overhead flat-lay view of a large hand-drawn district map spread on a wooden table in a "
     "Chinese investigation office, small red and black map pins clustered in one area, thin string "
     "connecting several pins, blank paper slips with pencil ticks, two hands entering frame with a "
     "pencil tracing a line between the pins, no faces and no readable writing; a very slow top-down "
     "creep toward the densest cluster of pins, " + HOLD,
     "铅笔划线声、纸张摩擦声"),
    ("S19", "agnes", "横移档案堆至核对的双手", "海量排查：一轮轮缩小的范围",
     "接重点对象远观",
     "A Chinese records room in the mid-2000s: towering stacks of blank paper folders and ledgers on "
     "a wooden desk and against a wall of filing cabinets, a desk lamp, a pair of hands leafing "
     "quickly through blank pages, another pair of hands comparing two small paper slips, no faces in "
     "frame and no readable writing; a slow lateral slide across the mountains of folders toward the "
     "working hands, " + HOLD,
     "文件翻动声、钢笔书写声、时钟滴答"),
    ("S20", "agnes", "长焦隔街观察，缓慢收紧", "普通人中的嫌疑人：C1 被远远注视",
     "接走访敲门",
     "Across a quiet concrete courtyard in a northern Chinese mining compound in the mid-2000s, seen "
     "through a long lens: the Chinese man {C1} in a plain grey-blue work jacket walks slowly home "
     "alone between two soot-dark brick blocks, ordinary and unremarkable, his calm face briefly "
     "visible in three-quarter view; in the foreground shadows at the far side of the courtyard, two "
     "men in dark coats stand partially hidden by a wall, watching him from a distance with their "
     "backs to the camera; a steady long-lens shot that slowly tightens on the walking man, " + HOLD,
     "远处车辆声、脚步声、轻微低频"),
    ("S21", "agnes", "沿走廊推向敲门的走访员", "排查走访：一遍遍的敲门",
     "接心理测试",
     "A narrow corridor inside a soot-dark brick apartment block in a mining compound in the "
     "mid-2000s: two plain-clothes investigators stand at a closed wooden door, one holding a "
     "notebook, the other raising a hand to knock, closed doors stretching down the dim corridor, one "
     "bare bulb overhead, all faces away or in profile shadow, no readable notices on any door; a slow "
     "push down the corridor toward the two figures at the door, " + HOLD,
     "敲门声、走廊回声"),
    ("S22", "agnes", "横移仪器刻度至走纸", "心理测试：侦查措施之一（不作定罪依据）",
     "接线索汇聚",
     "Inside a plain Chinese testing room in the mid-2000s — a small table with an old instrument "
     "with dials and coiled rubber tubes, blank chart paper feeding from a roller, a desk lamp, an "
     "empty chair with a jacket hung on it, the whole shot staying indoors with no exterior and no "
     "transition: a pair of hands adjusts a dial and guides the chart paper while the operator and "
     "the seated figure appear only as hands and torsos, no faces; a slow close drift across the "
     "instrument's dials toward the chart roller, " + HOLD,
     "仪器低鸣、纸带走动声"),
    ("S23", "agnes", "推近线索板中心", "章末悬念：线索在灯下汇合",
     "接第四章传唤",
     "A dark Chinese investigation office late at night lit only by one desk lamp: a corkboard on the "
     "wall hung with blank paper slips and small photographs covered by blank sleeves, pinned in a "
     "web of connecting string, one hand pinning one more slip at the centre, dust drifting through "
     "the lamp beam, no faces and no readable writing; a slow push toward the centre of the board as "
     "the shadows deepen, " + HOLD,
     "图钉按入声、低音鼓点渐快"),

    # ---------------- N04 沉默被打破（S24-S30：6 动态 + 1 信息卡）----------------
    ("S24", "agnes", "走廊侧向跟拍，停在开启的门", "二〇〇六年三月：传唤到案",
     "接对峙",
     "A plain corridor inside a Chinese government office building in the mid-2000s — grey-green "
     "walls, closed wooden office doors, a row of empty chairs, weak daylight from high windows, the "
     "whole shot staying indoors from the first frame to the last with no exterior, no building "
     "facade and no transition: two middle-aged Chinese men in ordinary jackets walk separately down the corridor walked along by two tall men in dark jackets, all faces turned away or in shadow, one door opening at the far end; a slow lateral tracking move along the corridor that settles on the "
     "opening door, " + HOLD,
     "脚步声、门锁声、空调低鸣"),
    ("S25", "agnes", "固定中景缓慢推进", "漫长的对峙：C1 的镇定",
     "接裂缝（手部）",
     "Inside a small plain Chinese interview room in the mid-2000s — a simple table, two chairs, pale "
     "green walls, one overhead lamp, a blank paper file on the table, the whole shot staying indoors "
     "from the first frame to the last with no exterior, no building facade and no transition: the "
     "Chinese man {C1} in a plain grey-blue work jacket sits upright at the table shown chest-up, "
     "hands resting calmly on the surface, his ordinary face composed and unreadable, two "
     "investigators seen only from behind across from him; a very slow push toward his calm face, " + HOLD,
     "钟表滴答声、纸张翻动声"),
    ("S26", "agnes", "文件落桌与手指特写交替", "防线的裂缝：手先出卖了镇定",
     "接供述",
     "Inside a Chinese interview room in the mid-2000s — close view of a plain table under harsh "
     "overhead light: an investigator's hand places a thick blank paper file squarely on the table, "
     "and across it the seated man's hands slowly tighten against each other, one thumb pressing "
     "white, a jacket sleeve trembling slightly, only hands and forearms in frame, no faces and no "
     "readable writing; a slow drift between the resting file and the tense interlocked fingers, " + HOLD,
     "纸张落桌声、低音鼓点渐快"),
    ("S27", "agnes", "笔尖特写抬升至凝重神情", "供述开始：C2 记录，音乐短暂停顿",
     "接交代细节",
     "Inside a Chinese interview room in the mid-2000s at night — a plain table under one hanging "
     "lamp, an open blank notebook and a pen in the foreground, the whole shot staying indoors from "
     "the first frame to the last with no exterior, no building facade and no transition: across the "
     "table the veteran detective {C2} listens with his head slightly bowed, his tired weathered face "
     "clearly visible in the lamplight, writing slowly in the notebook; the seated man sits opposite "
     "as a dark out-of-focus shoulder silhouette at the edge of frame, no face visible on him; a slow "
     "tilt up from the pen nib to the detective's grave listening face, " + HOLD,
     "笔尖划纸声、室内钟表声"),
    ("S28", "agnes", "俯视交代记录，缓慢漂移", "案情逐一厘清（不呈现具体供述内容）",
     "接时间线板",
     "Inside a Chinese interview room in the mid-2000s: overhead view of a plain wooden table where a "
     "pair of hands writes steadily in a blank notebook, another pair of hands rests open and still on "
     "the table beside a cup of tea, a tape-recorder-style device with turning spools sits at the "
     "table edge, only hands and forearms visible, no faces and no readable writing; a slow overhead "
     "drift that ends framing the still open hands, " + HOLD,
     "磁带转动声、时钟滴答"),
    ("S29", "agnes", "拉远呈现完整时间线", "案件规模浮现：十二个标记",
     "接案件规模卡",
     "A wide view of a completed investigation board in a Chinese government office in the "
     "mid-2000s: a long wall board carrying a horizontal timeline strip with twelve small blank paper markers pinned along it and thin string linking several points, three men in plain clothes standing before it seen only from behind, silent and still, soft daylight from side windows, no readable writing anywhere; a slow pull back from one marker that reveals the full line of twelve, " + HOLD,
     "沉重鼓点、短暂静默"),
    ("S30", "graphic", "—", "信息卡：十二起案件 · 九死三伤", "接第五章告破",
     "案件规模卡", "低音收束"),

    # ---------------- N05 判决与代价（S31-S38：6 动态 + 2 信息卡）----------------
    ("S31", "agnes", "从记者席推进至发布台", "警方宣布告破（背影与远景）",
     "接二〇〇六年卡",
     "A plain Chinese briefing room in the mid-2000s — a simple wooden podium against a blank pale "
     "wall with no emblem or lettering, two uniformed officers standing behind it seen chest-up with "
     "their faces kept in shallow shadow and slightly turned away, rows of seated reporters seen only "
     "from behind, period-appropriate shoulder cameras and notebooks raised; a slow push from the "
     "reporters' backs toward the podium, " + HOLD,
     "相机快门声、纸张声、人群低语"),
    ("S32", "graphic", "—", "信息卡：二〇〇六年 · 告破与逮捕", "接押解",
     "二〇〇六年卡", "快门声余韵"),
    ("S33", "agnes", "侧后方跟拍押解队伍", "进入司法程序（只给背影）",
     "接法庭",
     "A secure interior corridor of a concrete facility in the mid-2000s — grey walls, a heavy steel "
     "door at the far end, weak overhead light, the whole shot staying indoors from the first frame "
     "to the last with no exterior and no transition: a man in a plain dark jacket walks away from "
     "camera down the corridor with his hands held low, escorted by two tall officers in dark "
     "uniforms seen from behind, no faces visible at any moment and no readable text; a slow steady "
     "tracking shot following the three figures toward the heavy steel door, " + HOLD,
     "脚步声、铁门声、沉稳弦乐"),
    ("S34", "agnes", "沿审判台横移至法官", "庭审：C3（法官，虚构角色）",
     "接证据文件",
     "Inside a wood-panelled Chinese courtroom in the mid-2000s — the high judge's bench under a "
     "solemn backdrop kept completely blank with no emblem and no lettering, the whole shot staying "
     "indoors from the first frame to the last with no exterior, no building facade and no "
     "transition: the judge {C3} in black robes sits behind the bench shown chest-up, his dignified "
     "face clearly visible and grave, flanked by two assessors seen only as dark blurred shoulders; "
     "far below, the defendant sits in a wooden dock as a small out-of-focus back-of-head silhouette; "
     "a slow lateral drift along the bench toward the judge's grave face, " + HOLD,
     "法庭回声、衣料摩擦"),
    ("S35", "agnes", "横移证据卷宗至静置的双手", "法庭上的证据（无可读文字）",
     "接法院外景",
     "Close view inside a Chinese courtroom in the mid-2000s: a row of neatly stacked blank paper "
     "case files and a pair of white cotton gloves on a polished wooden desk, a microphone stem "
     "rising at the edge, warm wood grain and solemn light, a lawyer's hands resting silently beside "
     "the files, no faces and no readable writing; a slow lateral glide along the row of files toward "
     "the resting hands, " + HOLD,
     "纸张翻动声、寂静"),
    ("S36", "agnes", "法院台阶拉远至外景", "一审判决：死刑（八月十日）",
     "接冬日广场",
     "Wide exterior of a solemn stone government building with wide steps under a flat grey sky in "
     "the mid-2000s: plain stone steps, square columns, a wide empty forecourt, two officials in dark "
     "coats carrying blank paper folders walking down the steps seen small in frame, bare winter "
     "trees at the edges, no readable inscriptions or signage anywhere; a very slow pull-back and "
     "slight downward tilt from the steps until the building fills the top of frame, " + HOLD,
     "低沉钟声、风声"),
    ("S37", "agnes", "缓慢升高拉远空旷广场", "十一月二十一日：一个时代的终点（空镜）",
     "接判决时间线卡",
     "A quiet wide view of a stone forecourt on a cold late-autumn morning in the mid-2000s — empty "
     "stone plaza, bare trees moving in the wind, one street lamp, flat white sky, a single distant "
     "figure walking away, no faces and no readable text; an extremely slow crane rise that widens "
     "the empty plaza until the walking figure becomes tiny, " + HOLD,
     "冷风声、音乐低沉收束"),
    ("S38", "graphic", "—", "信息卡：判决时间线（一审死刑 / 执行死刑）", "接第六章矿区日常",
     "判决时间线卡", "钟声余韵"),

    # ---------------- N06 留下来的（S39-S45：6 动态 + 1 信息卡）----------------
    ("S39", "agnes", "平稳横移街道，停在亮灯的窗户", "矿区恢复日常",
     "接受害者致意卡",
     "Dawn on a quiet residential street in a northern Chinese mining compound in the years that "
     "followed: a worker raising a plain metal shutter with no lettering, an old bicycle passing, "
     "soft cold morning light on wet concrete, soot-dark brick blocks and a distant headframe, a few "
     "anonymous residents far away and no signage anywhere; a slow lateral drift along the street "
     "that ends on one window glowing warm in a brick facade, " + HOLD,
     "清晨城市声、远处工厂声"),
    ("S40", "graphic", "—", "信息卡：九名遇害女性致意（不出现人像）", "接遗物静物",
     "受害者致意卡", "轻柔钢琴音"),
    ("S41", "agnes", "缓慢扫过遗物，停在空椅", "受害者不只是数字",
     "接侦查档案",
     "A quiet reverent still-life in soft natural window light inside a modest northern Chinese home: "
     "a neatly folded dark padded coat on a wooden chair, a small cheap hair clip beside it, a framed "
     "family photograph standing on a sideboard with the photo turned away from camera, a half-"
     "finished ball of dark knitting wool, an empty wooden chair pulled slightly back, no people and "
     "no readable writing; a slow slide across the objects that finally rests on the empty chair, " + HOLD,
     "轻柔钢琴音、微弱风声"),
    ("S42", "agnes", "从满桌档案缓慢拉远", "十四年的调查：走访与档案",
     "接红衣与窗",
     "A now-empty Chinese investigation office at night: an old desk covered with closed blank case "
     "folders and tied paper bundles, a green-shaded desk lamp still lit, a half-drunk cup of tea, "
     "chairs pushed in, a dim pin map on the background wall, no people and no readable writing; a "
     "slow pull-back from the lamp-lit desk into the quiet dark room, " + HOLD,
     "纸张摩擦声、时钟滴答"),
    ("S43", "agnes", "推近红衣，拉焦至窗外", "回到红衣：符号之下是真实的人",
     "接矿区夜灯",
     "A plain red cotton-padded coat hanging quietly beside a curtained window in a modest northern "
     "Chinese home in winter, warm low sun touching the fabric while outside the window the blurred "
     "industrial skyline and grey brick blocks stay distant and cold, no people and no readable text; "
     "a very slow push toward the red fabric, then a gentle rack focus from the coat to the cold "
     "street beyond the window, " + HOLD,
     "风吹窗帘声、音乐渐弱"),
    ("S44", "agnes", "缓慢升高，锁定一扇亮窗", "夜色中的一盏灯（情绪缓冲）",
     "接结尾航拍",
     "Night over a northern Chinese mining compound: a wide view of soot-dark brick apartment blocks, "
     "most windows dark, one single window glowing warm yellow, faint smoke drifting from a chimney, "
     "a distant headframe silhouette, light snow beginning to fall, no people and no readable text; a "
     "slow rising drift that keeps the one lit window centred while the compound darkens around it, " + HOLD,
     "风声、远处汽笛"),
    ("S45", "agnes", "航拍缓慢升高拉远，淡出", "结尾钩子：追凶留下的应该是记忆",
     "接片尾卡",
     "A desaturated dusk aerial view of a northern Chinese mining district: grey brick blocks and "
     "concrete lanes shrinking below, one street lamp glowing amber over an empty road, slag heaps "
     "and headframes fading into blue haze on the horizon, no people and no readable text; one "
     "extremely slow smooth rise and pull-back as the district grows small and quiet, holding the "
     "single amber streetlight, " + HOLD,
     "一声低沉鼓点，随后渐静"),
]

CARD_HEADER = "案件档案  /  山西阳泉 · 一九九二至二〇〇六"      # 每张信息卡左上角的小字
CARD_FOOTER = "公开报道口径 · AI动画情景重现 · 非新闻影像"      # 每张信息卡左下角的小字
# 信息卡文案：镜头号 -> (大标题, 第一行, 第二行)。只写公开报道里的事实，不写推测。
CARDS = {
    "S02": ("红衣杀手杨树明案", "山西阳泉矿区马家坪 · 一九九二—二〇〇六", "十四年 · 十二起案件 · 九死三伤"),
    "S10": ("媒体口中的红衣杀手", "多起案件的受害者被报道穿着红色衣物", "真正重要的是案件之间越来越明显的联系"),
    "S17": ("一年，又一年", "警方持续调查 · 案件仍未告破", "恐惧在矿区延续了十四年"),
    "S30": ("十四年，十二起案件", "一九九二年三月起 · 阳泉矿区马家坪一带", "九名女性死亡 · 三人受伤"),
    "S32": ("二〇〇六年", "四月 · 案件告破 · 同年依法逮捕", "十四年旧案进入司法程序"),
    "S38": ("判决时间线", "二〇〇六年八月十日 一审 死刑", "十一月二十一日 执行死刑"),
    "S40": ("九名遇害女性", "从十六岁到四十二岁", "她们不是数字，是一个个无法重来的生命"),
}
# 片头字幕卡（0.35–4.7 秒叠在第一镜上）：两行，第二行小字
TITLE_CARD = ["红衣杀手杨树明案", "十四年追凶 · 九名女性遇害 · 山西阳泉 1992—2006"]
# 片尾卡（最后 3.8 秒）：大字提问 / 一行案件信息 / 一行金句 / 一行资料来源
END_CARD = [
    "如果是你，会放过哪一条旧线索？",
    "红衣杀手杨树明案 · 一九九二—二〇〇六 · 九人遇害",
    "追凶最该留下的，不是凶手的名字，是对每一个受害者的记忆。",
    "资料：新华社 / 人民公安报 / 山西晚报 / 公开报道 · 原创解说 · AI动画情景重现",
]
# 字幕里描黄的关键词（人名、数字、结论词）——必须是解说词的子串
CAPTION_KEYWORDS = [
    "阳泉", "马家坪", "女工", "十四年", "红衣杀手", "始终没破", "杨树明", "寿阳",
    "表象", "罪行", "二〇〇一年", "失踪", "二〇〇四年冬天", "排查", "走访",
    "二〇〇五年", "专案力量", "比对", "地图", "重点视野", "心理测试", "关键节点",
    "二〇〇六年三月", "镇定", "裂缝", "三月底", "交代", "十二起案件", "九名女性死亡",
    "三人受伤", "责任人", "告破", "逮捕", "供认不讳", "八月十日", "一审判决",
    "死刑", "数罪并罚", "十一月二十一日", "终结", "十六岁到四十二岁", "家属",
    "档案", "不放弃", "受害者不是符号", "真实的人",
]
# 逐镜标签覆盖：默认镜头标「AI动画情景重现 · 非新闻影像」，办案/审讯/庭审镜头写得更具体
LABEL_OVERRIDES = {
    "S03": "AI动画情景重现 · 非案发影像",
    "S06": "AI动画情景重现 · 非警方档案影像",
    "S11": "AI动画情景重现 · 非本人容貌",
    "S12": "AI动画情景重现 · 非案发影像",
    "S13": "AI动画情景重现 · 非案发影像",
    "S14": "AI动画情景重现 · 非警方办案影像",
    "S15": "AI动画情景重现 · 非警方巡逻影像",
    "S16": "AI动画情景重现 · 非警方办案影像",
    "S18": "AI动画情景重现 · 非警方档案影像",
    "S19": "AI动画情景重现 · 非警方档案影像",
    "S20": "AI动画情景重现 · 非本人容貌",
    "S21": "AI动画情景重现 · 非走访实录影像",
    "S22": "AI动画情景重现 · 非测谎实录影像",
    "S23": "AI动画情景重现 · 非警方办案影像",
    "S24": "AI动画情景重现 · 非传唤实录影像",
    "S25": "AI动画情景重现 · 非询问影像 · 非本人容貌",
    "S26": "AI动画情景重现 · 非询问影像",
    "S27": "AI动画情景重现 · 非询问影像 · 非本人容貌",
    "S28": "AI动画情景重现 · 非询问影像",
    "S29": "AI动画情景重现 · 非警方办案影像",
    "S31": "AI动画情景重现 · 非发布会实况",
    "S33": "AI动画情景重现 · 非押解影像",
    "S34": "AI动画示意 · 非庭审影像 · 非本人容貌",
    "S35": "AI动画示意 · 非庭审影像",
    "S36": "AI动画示意 · 非法院实景",
    "S37": "AI动画情景重现 · 非实景影像",
    "S41": "AI动画情景重现 · 非受害者遗物影像",
    "S42": "AI动画情景重现 · 非警方档案影像",
}
# 合成音效事件：(镜头号, 类型)，类型可选 paper / phone / keys / machine / press，落在该镜开始前 0.18 秒
SFX_EVENTS = [
    ("S06", "paper"),
    ("S14", "phone"),
    ("S19", "paper"),
    ("S22", "machine"),
    ("S27", "paper"),
    ("S29", "press"),
    ("S31", "press"),
    ("S33", "keys"),
]

# ---------------------------------------------------------------------------
# 发布文案（抖音脚本.md / 抖音发布文案.md 用）
# ---------------------------------------------------------------------------
TITLES = [
    "红衣杀手杨树明：14年，9名女性遇害，警方如何撕开他的伪装？",
    "1992年阳泉矿区，女性接连遇害：“红衣杀手”藏了14年，败给一轮轮排查",
    "9条人命、12起案件、14年追凶：没有戏剧性的破案瞬间，只有对旧线索的不放弃",
]
HOOK = ("一九九二年起的十四年里，山西阳泉矿区马家坪一带，十二起针对女性的袭击接连发生，"
        "九人死亡、三人受伤。凶手就藏在人群里——有工作，也有家庭。二〇〇六年春天，"
        "在一轮轮排查、走访和心理测试之后，这桩悬案终于告破。")
GOLDEN_LINES = [
    "追凶最该留下的，不是凶手的名字，是对每一个受害者的记忆。",
    "「红衣杀手」让人记住了案子，却不该盖住事实：受害者不是符号，是真实的人。",
    "侦查从来没有戏剧性的瞬间——它来自一遍遍的走访、档案，和对旧线索的不放弃。",
]
DESCRIPTION = (
    "一九九二年至二〇〇〇年代中期，山西阳泉矿区马家坪一带接连发生针对女性的袭击，"
    "十二起案件造成九人死亡、三人受伤，媒体称之为「红衣杀手」。二〇〇五年警方重组专案力量，"
    "把十四年来的案发地点、时间和受害者情况放在一起比对；二〇〇六年三月起对重点对象展开核查，"
    "四月案件告破，杨树明归案。同年八月十日一审判决死刑，十一月二十一日被执行死刑。"
    "本片画面为AI生成的情景重现（非新闻影像、非本人容貌），事实依据公开报道整理，"
    "受害者均以匿名方式致敬。"
)
QUESTION = "如果你是当年的办案人，会放过哪一条旧线索？评论区聊聊。"
HASHTAGS = ["#悬疑", "#真实案件", "#大案纪实", "#案件解说", "#山西阳泉"]

GRID = 4            # 规划网格：每镜 4 秒，45 镜 = 180 秒
AGNES_SECONDS = 6   # 每个镜头实际请求的时长（智谱 CogVideoX-Flash 免费档单条约 5–6 秒，render 按需裁切）
SEED_BASE = 19920302  # 首案日期（一九九二年三月二日），让 seed 可追溯

# 露脸镜头登记（镜头号 -> 角色 id）：只有这里登记的镜头允许出现面容 token，
# 与 cast.json 的 shots 映射一一对应（face_cast.py check-prompts 两边都查）。
FACE_SHOTS = {
    "S11": ["C1"],
    "S20": ["C1"],
    "S25": ["C1"],
    "S14": ["C2"],
    "S27": ["C2"],
    "S34": ["C3"],
}
REFERENCE_SHOTS = {}   # 本片不走定妆照图生视频（免费档 image_url 队列拥堵，模板实测一条收据磨一小时）
FIRST_FRAME = {}       # 同上：跨镜脸一致性靠面容 token + seed，最终由 face_cast 画面闸门和人眼复核


def first_frame_urls():
    base = ("https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/"
            "arena/aa1e6b84-desktop-tutorial/production/yangshuming/")
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
        "露脸模式：面容 token 只在 cast.json 里写一份，build_story.py 用占位符注入，保证逐字节一致；"
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
        print(render_document(HERE, kind="script"))
    elif "--publish" in sys.argv:
        from script_table import render_document  # noqa: E402
        print(render_document(HERE, kind="publish"))
    else:
        build()

#!/usr/bin/env python3
"""《郑斗英：十个月，九条人命》唯一内容源。

按座间九人案的 45 镜/6 章/7 信息卡模板制作，但云端动画供应商改为
智谱 CogVideoX-Flash；不调用 Agnes。运行本文件会同步 story.json 与配音清单。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN = HERE / "story.json"
MANIFEST = HERE / "audio" / "manifest.json"
TITLE = "郑斗英：十个月，九条人命"

STYLE_PREFIX = (
    "Photorealistic cinematic 3D animated true-crime reenactment, high-end CGI feature-film render, "
    "South Korea between 1999 and 2000 unless another year is explicitly stated, authentic late-1990s Korean "
    "residential interiors, police offices and period props, physically based materials, volumetric practical light, "
    "subtle 35mm grain, restrained desaturated blue-grey and tungsten palette, respectful investigative documentary "
    "tone, horizontal 16:9 composition. Every person is anonymous and shown only from behind, in distant silhouette, "
    "or as hands; never show a clear face or imitate a real person. No readable text, letters, numbers, logos, signs, "
    "license plates, subtitles or watermarks inside the generated frame. No blood, corpse, injury, attack or violence. "
    "One location and one continuous slow camera move only. "
)
NEGATIVE_PROMPT = (
    "readable text, writing, letters, numbers, Korean characters, logo, watermark, subtitle, news chyron, license plate, "
    "recognizable face, frontal portrait, blood, gore, wound, corpse, body, attack, weapon use, violence, tutorial, "
    "escape instructions, duplicated person, extra limbs, deformed hands, morphing, flicker, jump cut, scene change, "
    "split screen, collage, 2D drawing, anime, cartoon, low-poly, plastic toy, vertical video"
)
PRINCIPLES = [
    "全部动态镜头由智谱 CogVideoX-Flash 生成，为写实 3D CGI 情景重现；全片常驻「AI动画情景重现 · 非新闻影像」",
    "不调用 Agnes；results.json 必须记录模型、任务号、下载地址、SHA-256 与请求哈希，缺镜头或校验不符拒绝出片",
    "不展示遗体、血腥、伤口、行凶过程或可复制的入室与越狱方法；只表现调查、空间、物件和事后场景",
    "郑斗英、受害者和相关人员均不做真人肖像还原；人物只以背影、远景剪影或手部出现，受害者不以可辨识人像出现",
    "用户稿中的四十镜扩展为座间案模板的四十五镜：三十八段动态 3D 动画加七张后期信息卡，每镜只使用一次",
    "一九九九年六月至二零零零年四月、九人死亡、十人受伤、二十三起强盗与杀人相关犯罪采用韩国主流媒体口径",
    "判决日期采用法院报道：二零零零年七月二十一日一审死刑、十一月三十日二审维持，放弃上诉后确定；不笼统误写为十二月首次判刑",
    "二零一六年事件仅写越狱未遂及三重围墙中越过两道后被发现；不展示工具制作和具体翻越步骤",
    "画面内中文姓名、年份、数字和字幕全部后期添加，不让视频模型生成文字；公开报道有差异的细节不做无来源扩写",
]
SOURCES = [
    {"id": 1, "url": "https://www.donga.com/news/article/all/20000416/7525729/1", "usage": "二〇〇〇年同期报道：十个月、九人死亡、警方此前未能串并案件"},
    {"id": 2, "url": "https://www.donga.com/news/article/all/20000416/7525825/1", "usage": "同期人物与动机报道；另载一九八六年前案，成片仅作背景概述"},
    {"id": 3, "url": "https://news.kbs.co.kr/news/pc/view/view.do?ncd=99686", "usage": "二〇〇〇年七月二十一日釜山地方法院一审判处死刑"},
    {"id": 4, "url": "https://news.sbs.co.kr/news/endPage.do?news_id=N1003810160", "usage": "二十三起强盗、杀人相关犯罪；九人死亡、十人受伤；二零一六年越狱未遂"},
    {"id": 5, "url": "https://www.yna.co.kr/view/AKR20170320095200063", "usage": "越狱未遂后追加十个月刑期；死刑犯身份与大田监狱"},
    {"id": 6, "url": "https://www.donga.com/news/Society/article/all/20170320/83410084/2", "usage": "二零一六年八月越狱未遂及三道围墙口径"},
    {"id": 7, "url": "https://www.yna.co.kr/view/AKR20040813005100004", "usage": "柳永哲供述曾从郑斗英案报道获得犯罪念头；用于结尾社会影响"},
    {"id": 8, "url": "https://www.sisajournal.com/news/articleView.html?idxno=193798", "usage": "一九九九年六月至二零零零年四月时间线、住宅目标与被捕背景"},
]

CHAPTERS = [
    ("N01", "报警：一次抢劫抓住连环凶手",
     "二零零零年四月十二日，韩国天安警方接到紧急报警：一户住宅遭到抢劫，屋内女子可能被控制。警员赶到后，抓住了试图离开的三十一岁男子郑斗英。起初，这只像一次入室抢劫；可当釜山警方赶来核对旧案，真相迅速失控。他们抓到的，是十个月里连续夺走九条生命的人。"),
    ("N02", "旧案：为何没有被及时串并",
     "郑斗英并非第一次因暴力犯罪入狱。一九八六年，十八岁的他杀害一名巡逻人员，服刑多年后又因盗窃反复进出监狱。一九九九年三月再次获释后，他把目标对准釜山、蔚山等地的富裕住宅。六月起，不同城市陆续出现抢劫和命案；地点分散、现场各异，警方最初没有认定它们来自同一个人。"),
    ("N03", "十个月：为钱而来的连续犯罪",
     "公开报道显示，他的目的主要是钱财。他常在白天寻找住宅，进入后搜掠现金和贵重物品；一旦被发现，犯罪便升级为致命暴力。受害者既有屋主，也有在住宅里工作的人员。到二零零零年春，相关案件已造成九人死亡、十人受伤。警方掌握了幸存者描述与公开通缉线索，却仍缺少把所有现场连成一线的关键证据。"),
    ("N04", "落网：屋主的报警与现场围捕",
     "四月十二日，郑斗英进入天安一处住宅，要求屋内女子联系丈夫送钱。丈夫从电话中察觉异常，没有独自回家，而是立即报警。警方在住宅周围布控，并安排人员带着准备好的钱进入。郑斗英拿到钱、走出房门时，被守候的警员控制。这场看似偶然的现场处置，终于给持续十个月的调查打开突破口。"),
    ("N05", "供述与判决：九名受害者背后",
     "后续审讯和核查中，郑斗英供述了多起案件。韩国媒体统计，从一九九九年六月到二零零零年四月，他在多地涉及二十三起强盗、杀人相关犯罪，九人死亡，十人受伤。二零零零年七月二十一日，釜山地方法院一审判处死刑；十一月三十日，二审维持原判。他放弃继续上诉，死刑判决随后确定。"),
    ("N06", "十六年后：第二次警报",
     "案件并未从公众记忆中消失。二零一六年八月，关押在大田监狱的郑斗英试图逃脱。他越过三重围墙中的两道后触发警报，在最后一道围墙前被控制，后来又因逃跑未遂被加刑十个月。九条生命，不是凶手传奇的注脚，而是九个再也无法回家的普通人。真正该记住的，是报警者的警觉、幸存者的勇气，以及那些不该被名字遮住的受害者。"),
]

HOLD = "No cut, no scene change, no camera relocation, no new person, hold this single view for the full clip."
# id, kind, camera, purpose, transition, prompt/card cue, sfx
_RAW = [
("S01","cogvideo","快速推近","报警电话突然响起","接警员背影","A late-1990s Korean police dispatch desk at night, beige landline phone ringing beside blank folders, no writing; quick controlled push toward the phone.","电话铃"),
("S02","cogvideo","侧后方跟拍","接警员迅速行动","接警车灯","A Korean police dispatcher seen strictly from behind rises from a desk and reaches for a plain radio, dim fluorescent office, blank walls; slow side tracking.","椅子移动"),
("S03","graphic","信息卡","案件名片","接住宅外景","案件名片","低频撞击"),
("S04","cogvideo","低机位前推","警车抵达住宅区","接警员下车","A quiet upscale Cheonan residential lane at night in April 2000, wet pavement washed by unseen patrol lights, no visible signs or plates, no people; low slow push.","远处警笛"),
("S05","cogvideo","背后跟拍","警员向住宅推进","接门厅","Two anonymous Korean police officers seen only from behind walking toward a plain detached-house entrance at night, no insignia or lettering; steady tracking.","脚步"),
("S06","cogvideo","缓慢推近","嫌疑人试图离开","接控制现场","A fixed night view of an open residential garden gate and wet path, three separate human shadows cast across the ground from outside the frame, no visible people, no doorway crossing; very subtle push.","急促脚步"),
("S07","cogvideo","俯拍下移","抓捕后的随身物品","接旧案卷宗","Top-down evidence table with plain gloves, keys, an unmarked wallet and sealed blank bags, no weapons, no writing; slow overhead descent.","证物袋"),
("S08","cogvideo","缓慢拉远","一次抢劫牵出多案","接第二章铁门","A top-down police desk holding exactly five closed plain kraft case folders arranged in one row under a single lamp, no photographs, no board, no paper surface visible, no people, no hands, no writing or marks; slow overhead pull back.","低沉鼓点"),
("S09","cogvideo","缓慢前推","早年入狱背景","接档案卡","An empty 1980s Korean detention corridor with a heavy unmarked steel door, fluorescent light and bare concrete, no people; slow forward dolly.","铁门回声"),
("S10","graphic","信息卡","人物与时间档案","接出狱走廊","人物档案","翻页"),
("S11","cogvideo","背后跟拍","多年后走出监狱","接普通街道","An empty bare institutional corridor leading to an already open outer gate and daylight, no people, no human silhouettes, no signs; slow forward dolly.","脚步"),
("S12","cogvideo","缓慢横移","一九九九年的釜山住宅","接门锁","A wealthy Busan residential interior in 1999, polished wood cabinet, beige curtains and period furniture, no people or readable objects; slow lateral track.","时钟"),
("S13","cogvideo","微距推近","目标是现金财物","接空房","Close view of one plain empty wooden drawer already fully open in a late-1990s room, no people, no hands, no tools, no objects; gentle macro push.","抽屉声"),
("S14","cogvideo","缓慢环绕","现场事后勘查","接地图","A non-graphic ransacked living room after an incident, open drawers and overturned chair, forensic officers only as distant backs, no bodies or blood; slow orbit.","相机快门"),
("S15","cogvideo","俯拍横移","各地案件彼此分散","接第三章街区","A bare dark-grey police table holding four small red evidence markers spaced far apart and three closed plain kraft folders, no map, no paper, no people, no hands, no writing; overhead lateral slide.","纸张翻动"),
("S16","cogvideo","高位横摇","富裕住宅成为目标","接数字卡","Daytime aerial-style wide view of late-1990s Korean detached homes, no signage, no people, no vehicles, restrained overcast atmosphere; slow pan.","环境底噪"),
("S17","graphic","信息卡","十个月案件规模","接门厅空镜","案件规模","重音"),
("S18","cogvideo","缓慢前推","白天住宅门厅","接现金抽屉","A sunlit but empty upscale Korean home entrance in 1999, plain shoes and polished floor, all doors closed, no labels; slow cautious push.","钟表滴答"),
("S19","cogvideo","俯拍推近","搜掠现金与贵重物品","接倒椅","Top-down still life of one open wooden compartment box containing a few smooth stones and plain blank cards, all objects already arranged, no people, no hands, no writing; slow push.","金属轻响"),
("S20","cogvideo","缓慢横移","犯罪升级后的空现场","接幸存者陈述","An empty quiet dining room after police arrival, one chair tipped over, curtains still, no person, no blood, no weapon; slow lateral move.","音乐骤停"),
("S21","cogvideo","背后中景","幸存者提供描述","接画板","An anonymous survivor seen only from behind speaking to a seated detective in a neutral interview room, faces fully hidden, blank walls; slow dolly.","铅笔声"),
("S22","cogvideo","俯拍下移","通缉画像和线索","接多份卷宗","A completely blank sketch sheet, a plain shoe-outline card and three sealed evidence envelopes already arranged on an otherwise empty dark desk, no people, no hands, no readable marks; overhead descent.","纸张"),
("S23","cogvideo","缓慢拉远","仍未串并所有案件","接报警日期卡","A late-night police office with several investigators seen from behind at separate desks under fluorescent pools of light, all papers blank; slow pull back.","电话远响"),
("S24","graphic","信息卡","四月十二日关键报警","接屋内电话","关键日期","电话铃"),
("S25","cogvideo","微距推近","女子拨打丈夫电话","接丈夫察觉","A beige corded telephone receiver resting off the hook beside its base inside a quiet Korean home, no people, no hands, no papers, no writing; slow macro push.","电话杂音"),
("S26","cogvideo","侧后方推近","丈夫察觉异常","接警局","A single beige corded telephone receiver lying off the hook on a plain wooden office desk, no people, no hands, no papers, no writing; slow macro push toward the receiver.","心跳低频"),
("S27","cogvideo","缓慢横移","警方快速布控","接住宅外","A top-down close view of exactly four plain wooden marker blocks placed around one miniature unmarked house on an otherwise completely bare grey table, no telephones, no radios, no paper, no map, no people, no hands, no writing; slow lateral slide.","无线电"),
("S28","cogvideo","低位跟拍","便衣人员带钱进入","接门口等待","A sealed unmarked paper bag resting on a low stone ledge beside a detached-house garden gate at night, distant patrol-light reflections on wet ground, no people, no hands, no doorway; low slow push.","脚步"),
("S29","cogvideo","固定微推","警员在暗处守候","接嫌疑人出来","A plain garden wall and closed metal gate at night with two clearly separated stationary officer shadows cast on the wall from outside the frame, no visible people, no doorway, soft patrol light; subtle push.","风声"),
("S30","cogvideo","快速后拉","出门即被控制","接审讯档案","A small rigid black briefcase lying closed and upright on wet paving stones at night, surrounded only by the lower legs and plain black shoes of three officers cropped below the knees, the briefcase clearly suitcase-sized with a hard handle, no bag, no wrapped object, no person on ground, no uniforms visible, no faces, no writing; controlled pull back.","警员呼喊"),
("S31","graphic","信息卡","调查结果数字","接审讯桌","调查结论","低音撞击"),
("S32","cogvideo","缓慢前推","审讯开始","接地点核对","A police interview room viewed through frosted glass, one seated male back and two detective silhouettes, no faces, no text; slow push.","门锁"),
("S33","cogvideo","俯拍横移","逐案核对供述","接路线图","Multiple closed blank case folders and sealed evidence bags laid out in neat separate rows on a long table, no people, no hands, no photographs, no writing; overhead lateral move.","翻页"),
("S34","cogvideo","俯拍拉远","二十三起案件范围","接法院","An unlabeled relief map of southeastern Korea with many small neutral markers, investigators' hands at edges, no text; overhead pull back.","标记声"),
("S35","cogvideo","缓慢推近","法庭判决示意","接铁门","An empty restrained Korean courtroom viewed from the rear gallery after proceedings, orderly benches and an unoccupied judge desk, no people, no seal, no text; slow push.","法庭静默"),
("S36","cogvideo","缓慢前推","死刑确定后羁押","接受害者纪念","An empty prison corridor in 2000 ending at a closed steel gate, cool daylight, no signs, numbers or people; slow forward dolly.","铁门关闭"),
("S37","cogvideo","静缓推近","九个空位象征受害者","接二零一六年卡","Nine simple empty wooden chairs in a quiet neutral room, soft morning light, no photographs or text; very slow push.","轻柔钢琴"),
("S38","graphic","信息卡","二零一六年越狱未遂","接监狱围墙","十六年后","警报"),
("S39","cogvideo","向上摇摄","大田监狱三重防线","接作业间","Close low-angle view of three parallel layers of plain prison security fencing and razor wire silhouetted against an overcast sky, frame contains only fence and sky, no walls, no buildings, no signs, no people, no writing; slow tilt upward.","远处警报"),
("S40","cogvideo","缓慢横移","监狱作业场所","接警戒灯","A prison workshop table with coils of ordinary automotive wire material and generic hand tools, no assembled device, no instructions, no people; slow lateral track.","金属环境声"),
("S41","cogvideo","缓慢推近","传感器触发警报","接狱警赶往","Close view of an abstract red warning lamp glowing on a plain concrete wall, no control labels or readable text; slow push.","警报"),
("S42","cogvideo","远景横摇","最后一道墙前被发现","接事件结局卡","Distant prison yard with officers moving toward a lone kneeling silhouette near the final wall, no climbing action or tool shown, faces hidden; slow pan.","急促脚步"),
("S43","graphic","信息卡","判决与后续状态","接受害者象征","司法结局","落槌"),
("S44","cogvideo","缓慢前推","住宅中留下的空椅","接清晨街区","A quiet Korean home at dawn, sunlight falling on one unused chair beside a closed window, no photos, no text, no people; slow push.","钢琴"),
("S45","cogvideo","缓慢升起","回到普通人的生活","接片尾卡","A peaceful Korean residential neighbourhood at sunrise viewed above rooftops, warm light after rain, no signs, vehicles or visible faces; slow crane upward.","音乐渐弱"),
]
SHOTS = [(a,b,c,d,e,(f+" "+HOLD if b=="cogvideo" else f),g) for a,b,c,d,e,f,g in _RAW]

CARD_HEADER = "案件档案  /  韩国 · 一九九九至二零一六"
CARD_FOOTER = "公开报道摘要 · 并非原始档案影像"
CARDS = {
    "S03": ("十个月，九条人命", "韩国 · 一九九九年六月至二零零零年四月", "一次住宅报警，让连环案件浮出水面"),
    "S10": ("郑斗英", "一九六八年出生 · 落网时三十一岁", "曾因杀人服刑，出狱后再次犯罪"),
    "S17": ("十个月", "九人死亡 · 十人受伤", "住宅抢劫，是这一系列案件的起点"),
    "S24": ("二零零零年四月十二日", "韩国天安 · 住宅报警", "屋主察觉异常，警方现场布控"),
    "S31": ("调查结果", "二十三起强盗、杀人相关犯罪", "供述、幸存者陈述与现场证据逐案核对"),
    "S38": ("二零一六年八月", "大田监狱 · 越狱未遂", "越过两道围墙后，警报响起"),
    "S43": ("死刑判决", "二零零零年七月一审 · 十一月二审维持", "放弃继续上诉 · 目前仍在押"),
}
TITLE_CARD = ["郑斗英", "十个月，九条人命 · 韩国真实案件"]
END_CARD = ["一次及时报警，能阻止多少悲剧？", "郑斗英案 · 一九九九至二零零零", "该被记住的，是九名受害者，不是凶手传奇", "资料：韩国 KBS / SBS / 韩联社 / 东亚日报 · AI动画情景重现"]
CAPTION_KEYWORDS = ["四月十二日","九条生命","郑斗英","一九九九年六月","住宅","钱财","九人死亡","十人受伤","立即报警","现场布控","二十三起","死刑","二零一六年八月","越狱未遂","受害者"]
LABEL_OVERRIDES = {"S32":"AI动画示意 · 非审讯影像","S35":"AI动画示意 · 非庭审影像","S36":"AI动画示意 · 非监控影像","S39":"AI动画示意 · 非监控影像","S40":"AI动画示意 · 不展示逃脱方法","S42":"AI动画示意 · 非监控影像"}
SFX_EVENTS = [("S01","phone"),("S07","keys"),("S10","paper"),("S21","paper"),("S24","phone"),("S27","keys"),("S31","paper"),("S35","press"),("S38","machine"),("S41","machine")]
TITLES = [
    "十个月九条人命：一次住宅报警，意外抓住韩国连环杀手",
    "郑斗英案：警方以为抓到抢劫犯，审讯后才发现九起命案",
    "二零零零年天安报警：一个电话，终结十个月连续犯罪",
]
HOOK = "警方赶到住宅时，以为只是一次抢劫；他们抓住的却是十个月里杀害九人的连环凶手。"
GOLDEN_LINES = ["九条生命，不是凶手传奇的注脚。","一次及时报警和一次规范处置，截断了下一场可能发生的悲剧。","一次及时报警，能阻止多少悲剧？"]
DESCRIPTION = "二零零零年四月十二日，韩国天安警方处理一起住宅报警，抓住了试图离开的郑斗英。随着旧案核对，这次普通抓捕牵出十个月、九名受害者和二十三起相关犯罪。二零一六年，他又因越狱未遂进入公众视线。本片依据韩国公开报道制作，画面均为 AI 动画情景重现，不是新闻或监控影像；不展示暴力过程。一次及时报警，能阻止多少悲剧？"
QUESTION = "一次及时报警，能阻止多少悲剧？"
HASHTAGS = ["#郑斗英案","#韩国真实案件","#悬疑","#法治","#AI动画情景重现"]
GRID = 4
COG_SECONDS = 6
SEED_BASE = 20000412


def presentation():
    return {"card_header":CARD_HEADER,"card_footer":CARD_FOOTER,"cards":{k:list(v) for k,v in CARDS.items()},"title_card":TITLE_CARD,"end_card":END_CARD,"caption_keywords":CAPTION_KEYWORDS,"label_overrides":LABEL_OVERRIDES,"sfx_events":[list(x) for x in SFX_EVENTS]}


def build():
    story=json.loads(PLAN.read_text())
    assert len(SHOTS)==45 and len(CHAPTERS)==6
    assert sum(kind=="cogvideo" for _,kind,*_ in SHOTS)==38
    assert sum(kind=="graphic" for _,kind,*_ in SHOTS)==7
    story.update({"title":TITLE,"model":"cogvideox-flash","style_prefix":STYLE_PREFIX,"negative_prompt":NEGATIVE_PROMPT,"principles":PRINCIPLES,"sources":SOURCES})
    for row,data in zip(story["chapters"],CHAPTERS):
        cid,title,text=data; assert row["id"]==cid; row.update(title=title,text=text)
    shots=[]
    for i,(sid,kind,camera,purpose,transition,body,sfx) in enumerate(SHOTS):
        assert sid==f"S{i+1:02d}"
        start=i*GRID
        shots.append({"id":sid,"kind":kind,"start":start,"duration":GRID,"narration_id":f"N{min(6,start//30+1):02d}","prompt":body if kind=="cogvideo" else "","purpose":purpose,"transition_out":transition,"graphic":body if kind=="graphic" else "","seed":SEED_BASE+i+1,"seconds":COG_SECONDS,"aspect":"16:9","resolution":"1080p","frame_rate":30,"camera":camera,"sfx_note":sfx})
    story["shots"]=shots; story["presentation"]=presentation(); story["_scaffold"]={"note":"座间九人案模板；45镜=38段CogVideoX-Flash动画+7张信息卡；每镜只用一次。"}
    PLAN.write_text(json.dumps(story,ensure_ascii=False,indent=2)+"\n")
    manifest=json.loads(MANIFEST.read_text())
    for clip,(_,_,text) in zip(manifest["clips"],CHAPTERS): clip["text"]=text; clip["voice_id"]="voice-00"
    MANIFEST.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print(f"story.json 已写入：45 镜 = 38 cogvideo + 7 graphic；解说 {sum(len(x[2]) for x in CHAPTERS)} 字（含标点）")

if __name__=="__main__":
    if "--script" in sys.argv:
        from script_table import render_document
        out=HERE/"抖音脚本.md"; out.write_text(render_document()); print(out)
    elif "--publish" in sys.argv:
        from script_table import publish_document
        out=HERE/"抖音发布文案.md"; out.write_text(publish_document()); print(out)
    else: build()

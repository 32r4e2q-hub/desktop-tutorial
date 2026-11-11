#!/usr/bin/env python3
"""Build the 180-second, 30-shot Agnes Video 2.5 Flash production plan.
All visuals are fictionalized animated reenactments, not real footage or portraits.
"""
from __future__ import annotations
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
TITLE="蜜月尼古丁命案：新婚第十一天"
STYLE=("【STYLE】电影级写实3D动画情景重现，非历史影像，35mm胶片摄影质感，浅景深，长焦压缩，克制的韩国犯罪惊悚片氛围；2017年韩国世宗市与日本大阪，真实的人体比例、自然皮肤与服装材质、可信建筑和道具，低饱和色彩、细腻胶片颗粒；前半段春日暖黄明亮，随后由暖黄转冷青、深蓝与冷白荧光灯，居酒屋暖黄但边缘渐冷，法庭冷灰，结尾黑场；16:9横屏宽银幕，主体置于三分线附近，底部六分之一保持低干扰供字幕；每条必须是真实连续的3D运动影像，人物自然呼吸、眨眼、行走、转头、手部动作，雨水、窗帘、灯光与环境持续真实运动，单镜连续运镜，禁止静态图推拉；所有人物为虚构演员式形象，不还原真实人物。")
NEG=("【NEGATIVE】卡通，Q版，动漫，夸张表情，过度饱和，文字，水印，字幕，可读文字，注射器，针头，药剂，瓶身标签，血腥，伤口，遗体，尸体，暴力过程，裸露，畸形手指，多余肢体，人物面部崩坏，低清晰度，画面闪烁，风格突变，竖屏构图，黑边，静态图加推拉，幻灯片，霓虹伪文字。")
# Exact character anchor strings from the brief. These are included verbatim in every relevant prompt.
CHARACTERS={
 "A":"【C01锚点】22岁韩国男子,偏瘦圆脸,黑色短发,浅色夹克白T恤,笑容温和,眼神冷静克制",
 "BRIDE":"【C02锚点】19岁韩国女孩,娇小,黑色长发,白色连衣裙浅粉开衫,笑容天真明亮",
 "EX":"【C03锚点】22岁韩国女子,齐肩短发,米色针织衫牛仔裤,神情警觉敏锐",
 "CLAIMS":"【C04锚点】40多岁韩国女性理赔员,中等短发,深色西装套裙,细框眼镜,神情细致专注",
 "POLICE":"【C05锚点】35至45岁韩国刑警,深色夹克衬衫,眼神锐利克制",
 "JP":"【C06锚点】日本警察制服警帽神情沉稳;日本法医白大褂口罩神情专注",
 "COURT":"【C07锚点】韩国女法官黑色法袍神情肃穆;检察官深色西装神情冷峻",
 "FAMILY":"【C08锚点】几位黑衣韩国家属,神情悲伤克制",
}
# start, duration, narration, visual beat, environment/reference IDs, roles, camera, sound
ROWS=[
(0,5,"大阪雨夜，旅馆三楼只有一扇窗亮着。","雨后大阪经济型酒店外景，三楼一扇窗亮着，霓虹倒映湿路；窗帘微动，长焦缓慢推进。","S01",[],"长焦缓慢推近","雨滴、电车远声、灯管嗡鸣"),
(5,5,"新婚第十一天，丈夫冲出房门，说妻子想要自杀。","昏暗酒店走廊，电子钟以无字光段暗示深夜，一名年轻男子猛然推门冲出，慌乱呼喊，表情克制僵硬。","S01+P01",["A"],"手持中景跟随","急促脚步、走廊回响"),
(10,7,"镜头倒回十一天前，两人刚在世宗登记结婚。","春日政府办公楼外樱花飘落，年轻男女牵手走出，女孩笑着靠近男子，手中只见不可读的文件。","S02",["A","BRIDE"],"中景缓慢横移","春风、远处人声"),
(17,7,"婚后，他们开始计划这趟大阪蜜月。","温暖咖啡馆窗边，女孩翻旅行手册，男子垂眼看手机；蓝色屏幕反光与暖黄灯形成反差，镜头中没有可读界面。","S03",["A","BRIDE"],"缓慢推近后转焦","咖啡机、轻声哼歌"),
(24,6,"出发前，他在机场办妥旅行保险，妻子就在身后。","仁川机场保险柜台，男子填写抽象线条表格，笔尖停顿后落下；理赔单受益人位置以醒目的红色圆圈示意，女孩在后方微笑。","S04+P02",["A","BRIDE"],"俯拍转中景","笔尖划纸、机场广播"),
(30,5,"保单把丈夫列作受益人。随后，两人飞往大阪。","飞机客舱夕阳穿过舷窗，女孩安睡，男子望向云海，面容平静；真实引擎震动和机舱微动。","S04",["A","BRIDE"],"侧脸缓慢推近","引擎低鸣"),
(35,7,"蜜月第一晚，他们在大阪运河边留下合影。","大阪夜景与运河倒影，一对年轻夫妻在街边拍照，女孩笑得明亮，男子举手机，街面雨后反光，镜头横移。","S05",["A","BRIDE"],"中景横移","街头人声、运河水声"),
(42,7,"入住旅馆后，她把外套挂起；丈夫坐在床边。","狭小双床商务酒店，女孩挂起衣物轻声哼歌，男子坐床边；画面边缘暗处只有模糊绿色玻璃轮廓，绝无标签或细节。","S06+P03",["A","BRIDE"],"缓慢横移，剪影不特写","衣架轻响、哼歌渐弱"),
(49,6,"不久，浴室门缝透出白光。水声停了，画面转黑。","酒店房间静物，浴室门紧闭，门缝下一线冷白光；床头电子钟的数字不清晰、只见光点；水声持续后骤停，瞬间切黑，不展示任何人或过程。","S06+P01",[],"固定机位后切黑","流水骤停、静寂"),
(55,5,"警方赶到时，丈夫坐在走廊，身旁站着警员。","走廊窗面映出红蓝警灯，男子背对镜头坐长椅，警察克制询问；不出现浴室内部、遗体或任何伤害过程。","S01",["A","JP"],"中景慢推","警笛渐远、低声询问"),
(60,7,"几天后，家属送别新娘。回到韩国，丈夫开始申请理赔。","日本火葬场白色长廊，黑衣家属肃穆同行，男子低头站在一侧；以空长廊和窗外落樱转场至韩国保险办公室。","S07",["A","FAMILY"],"缓慢推近后转场","长廊回声、压抑啜泣"),
(67,7,"他申请的一亿五千万韩元理赔，让经办人停下翻页。","冷白保险办公室，男子递交文件，理赔员翻页后目光停在抽象线条上；纸上没有可读文字。","S08",["A","CLAIMS"],"中景缓慢推近","纸张翻动、键盘声"),
(74,6,"结婚、投保、死亡，三个日期被画上红圈。","俯拍桌面，保单上的三个日期位置被红圈和红线连接，理赔员拿起电话，背景灰冷克制。","S08+P02",["CLAIMS"],"俯拍向前滑动","钢笔划纸、电话拨号"),
(80,5,"理赔员把文件交给警方，调查就此重新展开。","警署会议室，理赔员把文件推向两名刑警，墙上时钟走动，刑警交换眼神后起身。","S09",["CLAIMS","POLICE"],"中景缓慢推近","挂钟滴答、纸张轻响"),
(85,6,"警方跨海调取大阪的尸检资料，线索回到案发地。","桌面地图上大阪与世宗之间出现一条抽象红线，文件跨桌传递，印章落下；不显示可读文字。","P06",["POLICE"],"俯拍跟随红线延伸","传真声、纸张落桌"),
(91,6,"接近一年后，法医报告指向尼古丁中毒。","冷白实验室，法医查看抽象曲线，在屏幕峰值处轻轻标记；不展示样本细节、数值或任何可模仿步骤。","S10",["JP"],"缓慢推近屏幕后移向法医","仪器低鸣"),
(97,6,"报告送回警署，办案人员重新审视最初的说法。","世宗警署，刑警打开传真，读完后递给同事，两人沉默对视，背景声骤停。","S09",["POLICE"],"近景推近","纸张展开、环境声骤停"),
(103,5,"警方再次搜查住处，从抽屉里找出一本日记。","冷灰公寓内景，刑警打开抽屉，戴手套取出旧日记；只拍封面、手和纸页，不显示可读内容。","S11+P04",["POLICE"],"低机位移至桌面","抽屉拉开、纸页摩擦"),
(108,6,"翻到最后一页，一个红圈让调查人员停下。","日记摊在木桌上，字迹是抽象线条，最后一页红圈醒目；刑警的手停在页边，灯光冷硬。","S11+P04",["POLICE"],"微距缓推","翻页声、低沉室内底噪"),
(114,6,"2018年3月28日，警方上门将A某逮捕。","清晨公寓门口，刑警出示证件，男子开门后从惊讶变得僵硬，缓缓举起双手，不发生肢体冲突。","S11",["A","POLICE"],"手持中景跟进","敲门、晨鸟、脚步"),
(120,5,"审讯中，他仍坚称妻子是自杀身亡。","冷灰审讯室，男子平静说话，刑警沉默聆听，桌面上并排放着日记与红圈保单，所有文字不可读。","S12+P02+P04",["A","POLICE"],"过肩慢推","椅子摩擦、灯管嗡鸣"),
(125,5,"调查没有停在这里，线索指向他两年前的前女友。","暖黄大阪居酒屋，年轻男子与前女友对坐，杯子置于桌面，女子察觉异样而停下；边缘色温悄悄转冷，不展示添加过程。","S13",["A","EX"],"中景推向两人之间","居酒屋环境声、杯子轻响"),
(130,7,"2016年12月，前女友觉得味道不对，没把饮料喝完。","前女友放下杯子、微微摇头，男子的笑容僵住一瞬又恢复；镜头克制停留在她清醒警觉的表情，液体无特写。","S13",["EX","A"],"面部近景缓慢推近","杯子落桌、一拍沉默"),
(137,7,"警方还查到，他曾为前女友投保，受益人也是自己。","两份抽象保险单并排，受益人栏分别被红圈标注，红线汇向同一人物剪影；不含可读姓名或金额。","P02+S09",["POLICE"],"俯拍横移，红线连接","纸张摩擦、纸张摩擦与低沉环境音"),
(144,6,"在询问室里，她向警方讲述那次约会，补上另一段证词。","前女友在警局做笔录，手握水杯，窗外大雨；刑警安静倾听，镜头尊重、不过度煽情。","S09",["EX","POLICE"],"近景缓推","雨声、杯子轻响"),
(150,6,"被拘留后，他坐在铁窗下，等待法庭审理。","拘留室冷灰色调，男子坐床沿，铁栏阴影横过墙面与侧脸，远处铁门关闭；不渲染其心理。","S14",["A"],"缓慢推近","铁门回响、时钟滴答"),
(156,6,"2018年8月，法院判处他无期徒刑。","大田地方法院，虚构演员式被告站在被告席，女法官宣读判决，旁听席黑衣家属克制悲伤。","S15",["A","COURT","FAMILY"],"横向缓慢移动","法庭环境声、轻微啜泣"),
(162,6,"次年10月，最高法院维持原判。","冷灰法院外景，秋叶掠过台阶；判决纸上抽象红色印章落下，光穿过云层照亮石阶。","S16+P05",["COURT"],"低机位缓慢升起","风声、落叶、印章落下"),
(168,6,"最初那份理赔申请，最终让案件疑点浮出水面。","理赔员合上档案柜，抬头望向暮色窗外；镜头停在她平静而专注的侧脸，环境慢慢变暗。","S08",["CLAIMS"],"中景缓慢推近","抽屉关闭、窗外风声"),
(174,6,"如果那份申请没有被重新审视，真相会被错过吗？","黑场中，绿色小瓶只以极淡剪影浮现，门缝白光横扫后将其抹去；金色标题后期添加，不让模型写字。","P01+P03",[],"缓慢推进，白光叠化","最后一秒静音"),
]

def build():
    assert sum(r[1] for r in ROWS)==180 and len(ROWS)==30
    approved_assets=json.loads((HERE/"reference"/"approvals.json").read_text(encoding="utf-8"))["assets"]
    reference_revision=(HERE/"reference"/"revision.txt").read_text(encoding="utf-8").strip()
    chapters=[]
    # Nine structural chapters follow the brief's section boundaries.
    bounds=[(0,10,"开头钩子"),(10,35,"新婚与保险"),(35,60,"大阪的凌晨"),(60,85,"火化与理赔"),(85,108,"尸检与日记"),(108,130,"被捕与前女友"),(130,150,"同样的保险"),(150,168,"判决"),(168,180,"结尾提问")]
    for i,(start,end,title) in enumerate(bounds):
        text="".join(row[2] for row in ROWS if start<=row[0]<end)
        chapters.append({"id":f"N{i+1:02d}","title":title,"start":start,"duration":end-start,"text":text})
    shots=[]
    for i,(start,dur,narration,visual,refs,roles,camera,sound) in enumerate(ROWS,1):
        sid=f"S{i:02d}"
        role_prompts=[]
        for role in roles:
            role_prompts.append(CHARACTERS[role])
        prompt=(f"Cinematic 3D animated reenactment shot {sid}. {visual} "
                f"Continuous natural motion; camera: {camera}. Keep the subject on a third line, "
                f"bottom subtitle-safe zone quiet. No legible signage, no text. Reference design IDs: {refs}. "
                + " ".join(role_prompts))
        shots.append({"id":sid,"kind":"agnes","start":start,"duration":dur,"narration_id":next(c['id'] for c in chapters if c['start']<=start<c['start']+c['duration']),"narration":narration,"prompt":prompt,"purpose":visual,"transition_out":"依分段使用切黑、樱花飘落、红线延伸或白光叠化；段落尾以悬念句和短暂停顿收束","characters":roles,"style_variant":"real","seed":20260425+i,"seconds":dur,"aspect":"16:9","source_size":"720P","camera":camera,"sound_design":sound,"reference_ids":refs})
    project={"title":TITLE,"film_name":"蜜月尼古丁命案_新婚第十一天_三分钟_带声音.mp4","target_duration":180,"width":1920,"height":1080,"fps":24,"model":"agnes-video-2.5-flash","source_size":"720P","branch":"arena/31d27a2a-desktop-tutorial","style_prefix":STYLE,"negative_prompt":NEG,"style_rumor_prefix":STYLE,"characters":CHARACTERS,"character_seeds":{"A":22017,"BRIDE":19017,"EX":22016,"CLAIMS":40017,"POLICE":35018,"JP":2017,"COURT":2018,"FAMILY":2017},"narration_spec":{"voice_id":"voice-02","description":"用户试听后改选的低沉悬疑男声，中文普通话，克制、不煽情；逐镜独立配音，旁白与字幕同步"},"chapters":chapters,"shots":shots,"reference_images":[{"id":key,**value} for key,value in approved_assets.items()],"reference_revision":reference_revision,"reference_designs":{"characters":CHARACTERS,"scene_prop_ids":["S01-S16","P01-P06"],"note":"31张逐张审核通过的PNG按shot.reference_ids及characters映射为Agnes Video 2.5 Flash reference-mode images；不可变修订号见reference_revision。"},"caption_policy":{"style":"统一36px字幕；普通文字白色，重点词金黄色，细黑描边，底部居中安全区；重点仅改颜色、不放大或加粗","alignment":"逐镜与旁白同步","titles":"仅片尾镜头后期添加标题文字"},"presentation":{"onscreen_label":"AI动画情景重现 · 非真实影像","highlight_phrases":["新婚第十一天","十一天前","大阪","登记结婚","自杀","旅行保险","受益人","一亿五千万韩元","理赔申请","理赔","浴室门缝","警方","尸检资料","尼古丁中毒","警署","日记","红圈","逮捕","审讯","前女友","无期徒刑","最高法院","真相"],"end_title":"蜜月尼古丁命案","end_subtitle":"韩国世宗 · 日本大阪 · 2017—2019","cover_text":"新婚第十一天","cover_concept":"左半春日樱花下的年轻夫妻背影，右半商务酒店浴室门缝透出一线冷白光，中间一道裂缝；金色标题配黑边，画幅16:9。封面最终截图需来自本期已生成视频，不可用AI图冒充视频帧。","publish_title":"新婚第十一天，新娘死在蜜月第一夜：一份保险理赔，揭开了他的第二次作案","hashtags":["#真实事件","#蜜月命案","#韩国","#保险","#悬疑","#电影感"]},"sfx_only":True,"fact_check":{"status":"source-backed initial check","sources":["https://www.koreaherald.com/view.php?ud=20180328000729","https://www.insurancebusinessmag.com/asia/news/breaking-news/man-accused-of-killing-wife-for-insurance-money-96371.aspx","https://tvm.edaily.co.kr/News/NewsRead?NewsId=01102086638992568&Kind=E"],"note":"登记时丈夫的准确年龄和保险理赔日期暂不口播；判决日期在剪辑前二次核对；口播不讲述任何可复制的致害步骤。"},"principles":["全片注明AI动画情景重现，不冒充历史影像；人物为写实演员式虚构形象，不还原真人肖像。","不出现注射器、针头、药剂、剂量、获取方式或可模仿的致害细节；绿色小瓶仅暗处剪影且不特写、不带标签。","死亡过程仅以浴室门缝白光、停掉的水声、切黑暗示；不出现遗体、血腥。","女性角色以尊重方式呈现；不美化凶手、不渲染其心理。","画面连续动态、镜头平均6秒、严格16:9；字幕安全区不挡主体。"]}
    (HERE/"story.json").write_text(json.dumps(project,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    rows_md=["# 蜜月尼古丁命案：新婚第十一天 · 逐镜脚本","","横屏 16:9｜1920×1080 母版｜180 秒｜30 个真实连续运动的写实 3D 动画镜头｜旁白逐镜对齐｜无 BGM，仅环境声/音效参考。","","| 镜头 / 时间 | 旁白 | 画面 / 运镜 | 参考 ID | 音效 |","|---|---|---|---|---|"]
    for shot, row in zip(shots, ROWS):
        start,dur,narration,visual,refs,roles,camera,sound=row
        mmss=f"{start//60:02d}:{start%60:02d}–{(start+dur)//60:02d}:{(start+dur)%60:02d}"
        rows_md.append(f"| {shot['id']} / {mmss} | {narration} | {visual}（{camera}） | {refs} | {sound} |")
    rows_md += ["","## 统一安全与后期规范","","- 所有角色为虚构演员式形象；画面标注“AI动画情景重现 · 非真实影像”。不出现遗体、血腥或任何致害过程。","- 绿色小瓶只可作为暗处、不可辨细节的剪影；保险单、日记、地图均不得生成可读文字，中文标题与字幕后期制作。","- 旁白采用用户改选的低沉悬疑男声 `voice-02`；字幕统一36px；普通字白色、重点字金黄色、底部安全区，关键词不放大或加粗；逐镜做语速适配，不能删掉台词。","- 镜头 S01 与 S09 以酒店、深夜与门缝白光形成开头钩子/回溯呼应；段落转场依次使用樱花、切黑、红线延伸、冷暖变化和片尾白光叠化。","- 最终交付前逐 5 镜抽检人物与风格漂移，逐条复核真实连续运动、字幕、音画同步和来源事实。"]
    (HERE/"screenplay.md").write_text("\n".join(rows_md)+"\n",encoding="utf-8")
    (HERE/"抖音脚本.md").write_text("\n".join(rows_md)+"\n",encoding="utf-8")
    print(f"Wrote {len(shots)} shots / {sum(s['duration'] for s in shots)} seconds")
if __name__=="__main__":build()

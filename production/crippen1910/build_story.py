#!/usr/bin/env python3
"""Crippen content source; Setagaya engine, strict 30-shot 180s requested timeline."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
BRANCH = 'arena/f38dd103-desktop-tutorial'
STYLE = '【STYLE】电影级3D动画，1910年爱德华时代英国，伦敦雾气与煤气灯，蒸汽轮船与海上航行，青铜与靛蓝色调，海上段偏暖黄，追捕段偏冷青蓝，蓝色无线电电弧作为视觉强调色，体积光，细腻写实材质，画面丰富，16:9宽银幕横屏构图，电影镜头感，景深虚化，轻微胶片颗粒。所有人物为风格化虚构演绎，非真实肖像。主体在三分线上，底部六分之一留给后期字幕。必须真实连续动画：人物呼吸眨眼走动、衣料随风、海浪烟雾自然运动，不能静态图推拉。'
NEGATIVE = '【NEGATIVE】文字，水印，字幕，血腥，伤口，遗骸，遗体，尸体，人体组织，暴力过程，绞刑，裸露，畸形手指，多余肢体，人物面部崩坏，现代物体，现代服装，低清晰度，画面闪烁，风格突变，竖屏构图，黑边，静止画面，幻灯片。'
ROLES = {
'C01': '【C01锚点】瘦小中年男子,圆框金边眼镜,浓密八字胡,深灰三件套西装,神情温顺',
'C01B': '【C01B锚点】与C01同一男子,无胡子无眼镜,鼻梁有压痕,灰色软呢帽,浅褐色旅行西装',
'C02': '【C02锚点】金色卷发盘高,浓妆红唇,紫红色舞台长裙,羽毛披肩,夸张大宽边帽',
'C03': '【C03锚点】黑发盘起的清瘦年轻女子,米色衬衫,深色长裙,神情拘谨',
'C03B': '【C03B锚点】与C03同一人物,短发塞进鸭舌帽,偏大的深色男式西装,裤脚别着别针,神情紧张',
'C04': '【C04锚点】高个中年探长,浓密八字胡,深色长大衣,圆顶礼帽,目光锐利',
'C04B': '【C04B锚点】与C04同一探长,深蓝色引航员制服,带徽章的制帽,帽檐压低',
'C05': '【C05锚点】白色制服船长,金色肩章,花白络腮胡,船长帽,目光敏锐',
'C06': '【C06锚点】戴老式耳机的年轻电报员,衬衫袖口卷起,神情专注',
'C07': '【C07锚点】三位戴宽边装饰帽的爱德华时代女士,束腰长裙,神情关切',
'C08': '【C08锚点】戴细框眼镜的法医,白大褂,手持放大镜',
'C09': '【C09锚点】爱德华时代的法官、陪审员与旁听者,神情肃穆',
}
# duration, chapter, references, roles, narration, visible motion / camera.
ROWS = [
(5,1,'S06','', '他逃上大西洋邮轮，以为这片海，能藏住自己。','1910年7月，大西洋晨雾，黑烟囱远洋客轮破浪航行，乘客走动、海鸥盘旋、烟雾漂移。航拍下降靠近船舷，暖金色调。'),
(5,1,'S07 P01 C06','C06','可一道电波，已经跑在了他的前面。','沿桅杆上摇，天线随风微颤，蓝色电弧闪亮；匹配切到电报室，电报员猛抬头，耳机线轻晃。'),
(7,2,'S01 S02','','一九一零年一月三十一日，伦敦的小楼里，聚会正热闹。','夜雾流过伦敦希尔德罗普新月街，煤气灯照亮湿鹅卵石，窗内客人举杯走动，留声机唱片转动；街头低机位推近窗口。'),
(7,2,'C01 C02 S02','C02 C01','女歌手科拉放声高歌，丈夫克里平，却安静地坐在角落。','暖灯客厅，科拉挥动羽毛披肩唱歌，朋友鼓掌，克里平微驼低头捏住怀表链。中景环绕，以拉焦对比两人，不生成对白文字。'),
(6,2,'S01 P04','','可聚会之后，科拉再没露面，只留下了她的舞台帽。','不出现人物。走廊门缓缓自行合上，煤气灯焰轻颤，紫红羽毛宽边帽在楼梯台阶，羽毛被门缝气流带动，低机位缓缓接近。'),
(5,2,'C03 S02','C03','几周后，情人伊瑟尔住了进来，戴上科拉的首饰。','伊瑟尔在梳妆台镜前扣好项链，手指轻轻扣下女人的相框，镜中神情拘谨。镜面正确反射，特写缓推。'),
(7,3,'C07 S14','C07','丈夫先说科拉回了美国，后来又说她病死，朋友们起了疑心。','音乐厅后台，三位女士对照信封与报纸，摇头、交换担忧目光，一人起身拿手袋。中景环绕，无可读文字。'),
(7,3,'C04 S04','C04','她们报了警，苏格兰场的杜探长，开始调查这场失踪。','雾蒙蒙的苏格兰场外，杜探长持卷宗快步走过马车，进入大楼；冷青蓝光、衣摆随步伐摆动，侧面跟拍。'),
(6,3,'C04 C01 S02','C04 C01','探长上门，克里平温和应答，第一次搜查，一无所获。','客厅过肩切换，探长环顾柜子，克里平交叠双手温和回答，挂钟摆动。轻微推近，避免夸张嘴部。'),
(5,3,'C04 S01 S02','C04','可调查之后，这对情人突然不见了。','探长敲门无人应，推门走入安静客厅，桌上杯子已经冷了，窗帘随风动。低机位跟随入门，冷青蓝。'),
(7,4,'C04 S03 P03','C04','两人的消失，让探长折返回去，这次，他走向地下煤窖。','探长在门前停步拉开木门，举起铜提灯，火焰照亮松动砖缝。跟随提灯进入地窖，冷色阴影与暖灯对比。'),
(7,4,'C04 S03 P03','C04','他撬开松动的砖地，看到地下的东西，脸色变得凝重。','只拍手、铁撬棍与砖块移动，探长蹲下撬开一块砖，抬眼神情凝重。坑内保持全黑，绝不出现人体、人体组织或遗骸，尘埃飘动。'),
(6,4,'C09 S01','C09','地下发现了遗骸，警方封锁现场，消息很快传遍伦敦。','安全替代画面：警察搬运完全封闭的不透明证物箱走出屋门，围观者在外围低语，报童挥报。无担架、无蒙布人形、无人体组织；广角横移。参考群像仅提取1910平民服装，不在街道出现法官。'),
(5,4,'C08 S12','C08','检验发现了剧毒药物，警方随即发出通缉令。','法医用放大镜检查封闭无标本可见的证物容器，试剂滴入玻璃试管，液体逐渐变深。特写移焦到泛黄通缉纸，无人体组织无可读标签。'),
(6,5,'C01B C03B S05','C01B C03B','七月二十日，两人化名罗宾逊父子，登上蒙特罗斯号。','安特卫普港蒸汽升腾，中年男子和伪装男孩的成年伊瑟尔并排走上舷梯，帽檐压低，行李随步伐摆动。中景侧跟，暖金色。'),
(6,5,'C05 S06','C05','船长肯德尔，却留意上了这对举止奇怪的父子。','船长在木甲板上转头注视远处乘客，眯眼，手中黄铜望远镜轻轻放下，海风吹衣摆，眼神特写缓推。'),
(6,5,'C01B C03B C05 S06 P05','C01B C03B C05','男孩的裤脚靠别针固定，两人牵手的动作，又过分亲密。','暖色餐厅，特写过大的裤脚别针闪光，递面包时两人轻握手；船长在远景转头观察。自然手指动作，浅景深，缓推。'),
(5,5,'C05 S06 P02','C05','船长翻开通缉报纸，认出了这对逃亡者。','船长舱室，摊开旧报纸上的男女抽象肖像，对照窗外那对旅客，抬眉握紧报纸。拉焦切换，无可读新闻文字。'),
(6,6,'C06 S07 P01','C06','他让电报员向英国发报，一道电波，越过了大西洋。','电报员戴耳机连续敲击电键，铜线圈振颤，镜头跟随蓝色电弧从天线扩散为同心光环，穿过海上薄雾。真实动态特效非静图。'),
(6,6,'C04 S04','C04','无线电，把海上的线索送到警方手里，杜探长立即出发。','值班室纸条被递给探长，他迅速读完，拿起帽子冲向门，衣摆和纸张被带起，冷青光，快速跟拍。'),
(5,6,'C04 S08','C04','他登上更快的劳伦蒂克号，要赶在两人前面。','港口蒸汽笛声，探长跨上舷梯，接切全速航行船尾白浪，他在甲板眺望海平线。冷青蓝航拍后拉。'),
(5,6,'C01B C04 S06 S08 P01','C01B C04','一边还在悠闲看海，另一边，已经抢先抵达加拿大。','唯一分屏镜头：左暖黄蒙特罗斯甲板，克里平翻报微笑；右冷青劳伦蒂克破浪，探长踱步；下方无字海图航线光点靠近，蓝色光环连接两边，不生成数字距离。'),
(7,7,'C04B S09','C04B','七月三十一日清晨，探长换上引航员制服，在父亲角等候。','圣劳伦斯河口晨雾，小引航船在波浪上起伏靠近大船，探长压低制帽，扶栏站稳。低机位海面跟拍，衣角随风动。'),
(7,7,'C01B C04B S06 S09','C01B C04B','小船靠上蒙特罗斯号，探长登船，走到毫无防备的克里平身后。','大船甲板上克里平扶栏看海，探长从身后稳步走近，海风吹动两人衣摆，晨雾缓流。中景跟随探长背影。'),
(6,7,'C01B C04B S09','C01B C04B','帽子摘下，身份揭晓。这场跨海逃亡，终于结束了。','探长在甲板克里平面前摘下制帽，克里平转身惊愕后肩膀松弛，轻叹，不呈现未经核实的历史原话。双方面部特写移焦，雾被阳光穿透。'),
(6,8,'C01 C09 S10','C01 C09','十月，克里平在老贝利受审，陪审团开始商议判决。','木质法庭全景，克里平站被告席，法官与十二名陪审员肃穆，陪审员起身走出。此为克里平单独审判，伊瑟尔不出现在同一被告席。冷灰横向环绕。'),
(6,8,'C01 C09 S10','C01 C09','仅二十七分钟，他被裁定有罪。伊瑟尔另案受审，获判无罪。','陪审员返回，首席站起口头宣告，克里平缓缓低头，法官稳坐。无伊瑟尔同庭宣判，不拍英式法庭并不存在的法槌。中景轻推。'),
(6,8,'S11','','十一月二十三日，克里平被处决，故事似乎画上了句号。','空监狱走廊，石墙与铁门，一盏盏灯依次熄灭，铁门缓慢关上，镜头沿长廊对称推进。无人，无刑场无绞刑无人体轮廓。'),
(6,9,'S13 P01','','可二〇〇七年的DNA研究提出：地窖里的人，可能不是科拉。','明确2007年现代生物实验室，冷白灯，研究员戴手套将封闭样本管送入仪器，无可见人体组织。屏幕两条抽象DNA曲线错开，蓝色同心电波从曲线扩散。微距跟随手部移焦。'),
(6,9,'S03 S01','','结论仍有争议，未能推翻原判。科拉，究竟在哪？','煤窖砖地平整，尘埃缓流，镜头上升经过地下门和街道雾气到伦敦屋顶，逐渐淡白。金色标题由后期叠加，画内不生成文字。最后一秒静音。'),
]
REF_DESCRIPTIONS = {
'S01':'1910伦敦联排小楼街道，夜雾，煤气灯，湿鹅卵石，三层亮窗，无人，16:9。',
'S02':'爱德华客厅与相邻梳妆台，红天鹅绒沙发、留声机、舞台相框、煤气壁灯，暖黄，无人，16:9。',
'S03':'地下煤窖，砖地、半掩木门、墙角煤块、铜提灯，冷青阴影，无人体，无人，16:9。',
'S04':'苏格兰场雾中外景，爱德华建筑，入口可见木桌电报值班室，冷青蓝，无人，16:9单一环境。',
'S05':'1910安特卫普码头，黑烟囱蒙特罗斯客轮停泊、舷梯、蒸汽、携行李乘客远景，清晨暖黄，16:9。',
'S06':'蒙特罗斯号黑烟囱蒸汽客轮，暖黄海上阳光，木质甲板栏杆，背景可见餐厅玻璃门及船长室，16:9单一环境。',
'S07':'1910无线电报室，铜电键、线圈、老式耳机、纸带、窗外桅杆蓝电弧，无人，16:9。',
'S08':'劳伦蒂克号白星蒸汽客轮全速破浪，比蒙特罗斯大，烟囱浓烟、宽甲板、白浪，冷青蓝，16:9。',
'S09':'加拿大圣劳伦斯河口父亲角晨雾，小领航船靠近大客轮，远处小灯塔，冷青，16:9。',
'S10':'伦敦老贝利法庭，木质被告席、法官席、十二陪审席、玻璃穹顶冷灰光，无人，无美式法槌，16:9。',
'S11':'1910监狱石墙长走廊，铁门、吊灯、反光地面，冷灰，对称构图，无人，16:9。',
'S12':'1910法医实验室，木桌、玻璃试管、放大镜、显微镜、煤气灯、密封不透明证物瓶，无人体组织，冷青，无人，16:9。',
'S13':'2007现代生物实验室，冷白灯、DNA分析仪、抽象两条DNA曲线显示器、不锈钢台面，无人，无可见人体组织，16:9。',
'S14':'1910音乐厅后台，化妆镜灯泡、戏服衣架、无可读文字海报，暖黄杂乱，无人，16:9。',
'P01':'黑背景蓝色同心电弧光环，中心蓝白闪光，细腻发光边缘，无文字。',
'P02':'黑背景1910泛黄卷边通缉报纸，一男一女抽象肖像，抽象线条代替文字，无可读标题。',
'P03':'黑背景爱德华铜提灯发暖光，旁边铁撬棍，电影材质，无文字。',
'P04':'黑背景紫红夸张羽毛花饰舞台宽边帽，暖黄侧光，电影材质。',
'P05':'黑背景银色大号别针，别在深色男裤裤脚，微距金属质感。',
}


def build():
    shots=[]; cursor=0
    for i,(duration,chapter,refs,roles,text,prompt) in enumerate(ROWS,1):
        sid=f'S{i:02d}'
        shots.append(dict(id=sid,start=cursor,duration=duration,seconds=duration,aspect='16:9',source_size='720P',kind='agnes',style_variant='real',seed=191000+i,characters=roles.split(),references=refs.split(),narration=text,narration_id=f'N{chapter:02d}',prompt=prompt))
        cursor+=duration
    chapters=[]
    for i in range(1,10):
        group=[s for s in shots if s['narration_id']==f'N{i:02d}']
        chapters.append(dict(id=f'N{i:02d}',title=['黄金三秒钩子','消失的科拉','探长上门','煤窖','海上的父子','电波追捕','抓捕','审判','反转'][i-1],start=group[0]['start'],duration=sum(s['duration'] for s in group),shot_ids=[s['id'] for s in group],text=''.join(s['narration'] for s in group)))
    reference_ids=list(ROLES)+list(REF_DESCRIPTIONS)
    voice_path=HERE/'audio/voice.json'
    voice_id=json.loads(voice_path.read_text()).get('voice_id') if voice_path.exists() else None
    story=dict(title='克里平医生案：一道追上凶手的电波',film_name='克里平医生案_一道追上凶手的电波_三分钟_带声音.mp4',episode=3,target_duration=180,width=1920,height=1080,fps=24,model='agnes-video-2.5-flash',source_size='720P',branch=BRANCH,style_prefix=STYLE,style_rumor_prefix=STYLE,negative_prompt=NEGATIVE,characters=ROLES,character_seeds={key:191010+i for i,key in enumerate(ROLES)},shots=shots,chapters=chapters,narration_spec={'voice_id':voice_id,'description':'悬疑低沉成熟男声，逐镜自然叙述','max_speedup_factor':1.15},reference_images=[{'id':key,'file':f'reference/{key}.png'} for key in reference_ids],presentation={'highlight_keywords':['一道电波','科拉','二十七分钟','终于结束','仍有争议','无线电','罗宾逊父子'],'end_question':'地窖里的人，究竟是谁？','cover':{'text':'一道电波'},'title':'凶手逃上大西洋邮轮，却被一道电波追上','hashtags':'#真实事件 #克里平医生 #伦敦 #悬疑 #历史 #3D动画 #无线电'})
    (HERE/'story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2)+'\n')
    (HERE/'audio').mkdir(exist_ok=True)
    manifest_path=HERE/'audio/manifest.json'
    previous=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    old={r['id']:r for r in previous.get('clips',[])}
    clips=[]
    for s in shots:
        p=HERE/'audio'/f"{s['id']}.mp3"
        valid=old.get(s['id'],{}).get('text')==s['narration'] and p.is_file()
        clips.append(dict(id=s['id'],file=p.name,text=s['narration'],voice_id=story['narration_spec']['voice_id'],narration_id=s['narration_id'],target_start=s['start'],target_duration=s['duration'],alignment='shot-locked',sha256=hashlib.sha256(p.read_bytes()).hexdigest() if valid else None))
    manifest_path.write_text(json.dumps(dict(voice=story['narration_spec']['voice_id'],alignment='one-clip-one-shot-one-caption',slowdown_allowed=False,clips=clips),ensure_ascii=False,indent=2)+'\n')
    refs=[dict(id=key,file=f'reference/{key}.png',description=ROLES.get(key,REF_DESCRIPTIONS.get(key)),status='candidate' if (HERE/f'reference/{key}.png').exists() else 'pending') for key in reference_ids]
    (HERE/'reference/manifest.json').write_text(json.dumps({'assets':refs,'all_approved':False,'note':'Single-view candidates are not the complete three-view plus close-up character package.'},ensure_ascii=False,indent=2)+'\n')
    lines=['# 克里平医生案 · 第三期 · 制作分镜（未出片）','', '|镜头|时间|参考图|旁白|动画动作|','|---|---|---|---|---|']
    for s in shots:
        lines.append(f"|{s['id']}|{s['start']}–{s['start']+s['duration']}秒|{', '.join(s['references'])}|{s['narration']}|{s['prompt']}|")
    (HERE/'screenplay.md').write_text('\n'.join(lines)+'\n')
    assert cursor==180 and len(shots)==30
    return story

if __name__=='__main__':
    story=build()
    print('Built 30 shots / 180 seconds; media and references remain gated.')

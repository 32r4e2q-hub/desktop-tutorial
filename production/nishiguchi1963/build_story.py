#!/usr/bin/env python3
"""西口彰事件：唯一分镜源。绝不以参考图替代视频。"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
STYLE = '''【STYLE】Cinematic 3D animation, stylized fictional reconstructions of 1963-1964 Showa Japan, never real likenesses. Warm faded vintage film colors; black-and-white TV static, old newspapers, steam trains and ferries; blue winter nights against warm yellow lamps, volumetric fog, detailed realistic materials, shallow depth of field, fine film grain, cinematic 16:9 composition, subjects on thirds with clean lower safe area. Every shot is a real continuous animation: moving people, cloth, wind, steam, light, water or meaningful environmental action; never a still image with camera zoom. Historically appropriate costumes and objects. No legible writing anywhere; title will be added in post. Respectful non-graphic reenactment. Children only in completely safe, calm scenes.'''
NEGATIVE = '''【NEGATIVE】text, subtitles, watermarks, logos, readable writing, blood, wounds, corpses, remains, weapons, violence, attack, peril to children, nudity, deformed hands, extra limbs, facial collapse, modern objects or clothes, low resolution, flicker, style drift, vertical framing, black borders, static slideshow, fake still-image zoom, real-person likeness.'''
ROLES = {
'nishiguchi':'【角色设定｜西口彰】Fictional stylized Japanese man, slim, short dark side-parted hair, kind unremarkable face, calm eyes, age around 37, dark suit and fedora, black briefcase. At different times a modest scholar jacket or lawyer suit and abstract badge. Consistent face; never a real likeness.',
'priest':'【角色设定｜古川泰龙】Fictional stylized Japanese priest in his forties, round kind face, simple black Buddhist robe, gentle, composed, not a real likeness.',
'girl':'【角色设定｜女孩】Fictional Japanese primary-school girl, about ten, bobbed hair, modest sweater, alert and quietly observant. Safe, peaceful scenes only; no likeness of a real person.',
'family':'【角色设定｜古川家人】Fictional welcoming Japanese family in simple period kimono and aprons, kind and composed, no likeness of real people.',
'police':'【角色设定｜警察】Fictional 1960s Japanese officers in period navy uniforms or dark overcoats, tired but focused, no visible weapons or real likenesses.',
'local':'【角色设定｜路人】Fictional ordinary Showa-era Japanese innkeepers, elders and travelers in period clothing, no real likenesses.'}
# Every line is assigned to the pictured action, not merely the surrounding chapter.
rows = [
(5,'这场逃亡跨越七十八天，五条生命在途中消逝。',[], 'In a dark living room an old monochrome television flickers with static and reveals a blurred drawn wanted portrait; a red warning light slowly passes across the glass. Real changing TV static, rotating warning light and drifting dust; close view slowly approaches.'),
(5,'最终识破他的，竟是一名小学五年级的女孩。',['nishiguchi','local'],'Move through the television glow to a 1963 railway platform: steam flows, travelers cross and a hatted man with briefcase walks away and disappears into the crowd. Follow his back; distant loudspeaker, no legible signage.'),
(7,'一九六三年十月十八日，福冈县接连传来噩耗，两名男子先后遇害。',[], 'At dawn on a misty rural Fukuoka road a parked vintage 1963 rounded-cab delivery truck stands completely still at the roadside, its headlights on and its cabin visibly empty. The camera descends as leaves stir and fog rolls. No people, no bodies, no road debris, no modern truck.'),
(7,'警方反复核查目击者提供的线索，终于锁定一名有前科的嫌疑人。',['police'],'Outside a misty crime scene police carefully unroll a plain cordon while a detective examines an abandoned shoe and closed file folder. Slow lateral track, no legible markings; these objects are illustrative, not verified evidence.'),
(6,'他叫西口彰，当时三十七岁，曾因诈骗和盗窃获罪。',['police'],'An officer pins a fictional hand-drawn portrait of a thin man on a police-office wall, then adds four unlabelled red markers to symbolize previous convictions; paper flutters, close camera. No readable writing.'),
(5,'福冈警方随即发出全国通缉，寻找他的踪迹。',['police'],'Overhead 1960s police desk: telegraph keys move, phone rings, an unlettered paper map of Japan fills with animated red dots as dispatch papers slide across it.'),
(7,'逃亡途中，他从报纸得知，自己的脸已出现在全国通缉令上。',['nishiguchi','local'],'In a small 1963 Showa diner with completely blank walls and windows, the man notices his fictional portrait printed on a folded, entirely blank paper, pauses mid-meal and slowly lowers his chopsticks as a server walks in the background. No readable or invented marks on the paper, walls or windows. Medium shot.'),
(7,'在濑户内海渡轮的甲板上，他留下鞋子和书信，布置了一场假死。',[], 'Night ferry deck in the Seto Inland Sea: wind buffets a folded blank letter beside two neatly placed leather shoes, dark sea swells and boat lights shimmer. Low-angle gentle move, no person or jump.'),
(6,'这场假死只是障眼法，他已经换了身份继续逃亡。',['nishiguchi','local'],'At a ferry harbor the man in changed clothes, hat and spectacles calmly walks with disembarking passengers; wind tugs coats and he glances back. Camera follows from behind to three-quarter view.'),
(5,'搜寻没有结果，警方判断，所谓自杀只是伪装。',['police'],'Cold grey sea: a search boat rocks and officers pull up an empty net, look at one another and continue searching; wide shot slowly retreats. No victims or remains.'),
(7,'他辗转各地，时而自称教授，用体面外表赢得信任。',['nishiguchi','local'],'Inside a period inn the man in a modest professor-like dark jacket bows and presents an unlettered card; the innkeeper bows back. Both move naturally as curtains sway. No academic cap.'),
(7,'之后他又冒充律师，凭着体面的谈吐与外表，继续在各地行骗。',['nishiguchi','local'],'A 1960s Kyoto tea room, cinematic 3D CGI. Close side view of two adult hands: a neatly dressed guest in a dark wool suit receives a plain, unmarked envelope across a low wooden table from an elderly visitor. Faces stay outside the frame, no caricature. The hands and steam move naturally. Warm practical light and cool blue window light.'),
(6,'从神户到京都、名古屋，他不断更换衣着和说辞。',['nishiguchi','local'],'Cinema-quality three-dimensional computer animated scene in a quiet 1963 dressing room. Three period outfits, scholar jacket, plain dark lawyer suit and businessman coat, move one after another past the camera on a rotating wooden clothes rack. A black briefcase and one pair of shoes sit below. The garments sway as the rack rotates. No people, no faces, no signs, no text; realistic wool, wood and warm-cool lighting.'),
(5,'据公开资料，他诈骗所得合计约八十万日元。',[], 'On a wooden desk envelopes and period banknotes slide into orderly stacks; an abstract red bar grows, no numbers, no readable marks. Overhead camera.'),
(6,'十一月，静冈滨松一家旅馆的经营者母女遇害。',[], 'A Showa Hamamatsu inn at night, curtains moving in wind and warm window lights turning off one after another. Aerial descent; entirely empty of victims and violence.'),
(6,'两条生命消逝，旅馆里只剩下寂静。',[], 'A quiet inn corridor with tatami and shoes left at the threshold, a paper door slowly closes in a breeze and lantern light fades. Respectful symbolic imagery, no person, no violence.'),
(6,'到了十二月末，东京的一位律师也成了受害者，案件仍在扩大。',[], 'Winter Tokyo 1963, vacant period law office, cooled tea on wooden desk, empty chair gently rotating, curtains stir in grey daylight. Slow approach, no people.'),
(5,'福冈、滨松、东京，前前后后，已经有五人失去了生命。',[], 'An unlettered vintage map of Japan: five soft red lights appear one by one, two close together in Fukuoka, two close together in Hamamatsu, one in Tokyo; thin threads connect them. Respectful symbolic graphic.'),
(6,'一九六四年一月二日，新年刚过，他来到熊本县的玉名市。',['priest'],'A mountain temple in winter Kumamoto mist, wind moves leaves on stone steps, a priest in black quietly sweeps the courtyard; aerial descent.'),
(6,'他冒充川村律师，拜访教诲师古川泰龙。',['nishiguchi','priest'],'At the temple gate, the man in a period lawyer suit and briefcase bows; the priest returns his bow. Side medium shot; leaves and robes move gently.'),
(5,'他声称愿意帮助古川，为冤案奔走的活动。',['nishiguchi','priest','family','girl'],'A calm tatami room: the priest explains papers to the attentive guest, family offers tea, the girl quietly observes from a safe corner. Gentle orbit, no readable documents.'),
(5,'一家人热情接待，女儿却觉得这张脸十分眼熟。',['nishiguchi','girl'],'In a peaceful room the guest calmly lifts tea to drink; the girl watches thoughtfully from across the table, in safe medium composition. Warm lamp and cool window light.'),
(7,'女孩想起路边的通缉照片，发现客人与照片很像。',['girl','nishiguchi'],'Safe and calm Japanese primary-school girl seen FROM BEHIND in a 1960s temple room. She gently holds a single completely blank white card featuring only a small blurred charcoal sketch of a dark-haired adult male in a suit; no letters, numbers, other drawings, face of a child, or extra papers anywhere. In the far background, a dark-haired adult male guest in a suit sits softly out of focus. The girl turns the card toward the light then glances up; tea steam drifts. Volumetric 3D CGI, realistic wood and fabric, not an illustration.'),
(7,'她把疑虑告诉家人；起初，父亲并没有相信。',['girl','priest','family'],'In a peaceful temple corridor the daughter speaks quietly to her family; the father first gently shakes his head, then listens attentively. No fear or danger, soft lateral camera.'),
(6,'家人再三核对，古川最终决定悄悄向警方求助。',['priest','family'],'The family compares an unlettered portrait away from the guest, then an adult discreetly uses a 1960s telephone; moonlight shifts and hands move. No suggestion of verified exact caller.'),
(6,'警方核实身份，发现这名来客并非真正的律师。',['police'],'At a police office an investigator studies unlettered paperwork, exchanges a look with a colleague and rises; telephone cord swings, brisk camera move.'),
(6,'夜色中，警员赶到寺院附近，静静等待天亮。',['police'],'On a misty mountain road, officers approach the distant temple quietly on foot, flashlights sweeping through fog and branches moving. Wide aerial, no weapons.'),
(6,'一月三日，警方确认身份，西口终于被捕。',['nishiguchi','police'],'In a simple empty temple courtyard with plain wood walls and NO signs or banners, a few 1960s uniformed officers approach the adult guest calmly in morning light; he stops and speaks with them, no struggle or weapons. Gentle 3D CGI movement and drifting morning mist. The exact arrest action is a reconstruction.'),
(6,'从十月十八日算起，七十八天的逃亡画上句号。',[], 'A blank calendar with absolutely no numbers or text flips its clean paper pages in a gentle wind on a wooden desk; behind it four clean little toy models of an empty vintage truck, ferry, inn and temple slowly rotate on a display stand. No people, no objects on the ground, no debris, no bodies. Motion comes from turning pages and rotating miniatures.'),
(6,'他后来被判处死刑，一九七零年执行。',[], 'A solemn detention center wall in soft morning light, bright beam across a barred window and gently drifting clouds; image gradually brightens. No readable text; final title will be composited in post.')]
chap_ranges = [(0,2,'黄金钩子'),(2,6,'通缉令'),(6,10,'假死'),(10,14,'千面诈骗犯'),(14,18,'五条人命'),(18,22,'古川家的客人'),(22,25,'女孩的眼睛'),(25,28,'逃亡的终点'),(28,30,'尾声')]
shots=[]; cursor=0
for i,(dur,narration,roles,prompt) in enumerate(rows):
 # A first visual review found these shots looked 2D and/or contained AI writing.
 # Only their prompts change; all other verified request hashes remain valid.
 if i+1 in {2,3,7,12,13,22,23,24,28,29}:
  prompt += " Visual medium is fully three-dimensional rendered CGI with physically volumetric, rounded characters, textured skin, fabric, wood and dynamic cinematic lighting. No 2D illustration, no cel shading, no hand-drawn anime, no cartoon outlines. Absolutely no signs, labels, writing, glyphs, newspapers with text or lettering in the entire frame."
 chapter=next(j+1 for j,(a,b,_) in enumerate(chap_ranges) if a<=i<b)
 shots.append(dict(id=f'S{i+1:02}',kind='agnes',start=cursor,duration=dur,seconds=dur,narration_id=f'N{chapter:02}',narration=narration,characters=roles,style_variant='real',prompt=prompt,seed=19631018+i,aspect='16:9',source_size='720P'))
 cursor+=dur
chapters=[]
for j,(a,b,title) in enumerate(chap_ranges,1):
 chapters.append(dict(id=f'N{j:02}',title=title,start=shots[a]['start'],duration=sum(x['duration'] for x in shots[a:b]),shot_ids=[x['id'] for x in shots[a:b]],text=''.join(x['narration'] for x in shots[a:b])))
project=dict(title='西口彰事件：78天的逃亡',film_name='西口彰事件_78天的逃亡_三分钟.mp4',target_duration=180,width=1920,height=1080,fps=24,model='agnes-video-2.5-flash',source_size='720P',branch='arena/eef99fcf-desktop-tutorial',style_prefix=STYLE,style_rumor_prefix=STYLE,negative_prompt=NEGATIVE,characters=ROLES,character_seeds={'nishiguchi':19631018,'priest':19640102,'girl':19640103,'family':19640104,'police':19631019,'local':19631020},shots=shots,chapters=chapters,narration_spec={'voice_id':'voice-00','max_speedup_factor':1.55},reference_images=[{'file':'reference/nishiguchi.png'},{'file':'reference/temple.png'},{'file':'reference/characters.png'}],presentation={'highlight_keywords':['七十八天','五个人','全国通缉','一双鞋','八十万日元','五人','女孩','一月三日','死刑'],'title':'他骗过了全日本，却被一个小学生一眼认出','hashtags':'#真实事件 #西口彰 #日本 #昭和 #悬疑 #3D动画 #复仇在我'})
assert cursor==180 and len(shots)==30
(HERE/'story.json').write_text(json.dumps(project,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# 西口彰事件：78天的逃亡','', 'AI动画情景复原，非真实影像。详细事实边界见 README。','', '| 镜头 | 时间 | 秒 | 旁白 | 画面提示 |','|---|---:|---:|---|---|']
for s in shots:
 lines.append(f"| {s['id']} | {s['start']:03}–{s['start']+s['duration']:03} | {s['duration']} | {s['narration']} | {s['prompt']} |")
(HERE/'screenplay.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

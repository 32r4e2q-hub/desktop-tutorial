#!/usr/bin/env python3
"""本片唯一内容源。引擎移植自production/kitakyushu2002，45镜=38动态+7卡。
只继承模板结构，不继承配音、时码、影片、收据、角色或QC结论。
--script须在新配音对齐后生成正式时间表；--publish生成发布文案草稿。
"""
import json
import sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
PLAN = HERE / 'story.json'
MANIFEST = HERE / 'audio/manifest.json'
CAST = HERE / 'cast.json'

TITLE = '小丑背后的真相：约翰·韦恩·盖西'

STYLE_PREFIX = ('Cinematic stylized three-dimensional animated documentary reenactment, physically modelled 3D CGI sets '
 'and adult fictional actors, 1970s American Midwest suburban architecture, wood panelling, walnut '
 'furniture, period wool clothing and unmarked cars; restrained cold blue and warm tungsten palette, soft '
 'volumetric side lighting, realistic cloth and object movement, horizontal 16:9 thirds composition, clean '
 'lower subtitle safety area. Visible faces belong only to explicitly registered fictional adult actors, '
 'not likenesses of real people; teenage figures are anonymous fully clothed back silhouettes only. Plain '
 'unlettered props, one coherent scene and one slow camera move per shot. ')

NEGATIVE_PROMPT = ('gore, violence, recognizable real-person likeness, frontal teenage faces, readable text, static image '
 'slideshow, flat 2D comic, duplicate people, facial morphing, extra limbs, jitter, scene cuts')

PRINCIPLES = ['全片为3D AI动画情景重现，常驻标注非新闻影像；虚构演员不是盖西、家属、警探或法官本人的容貌',
 '不展示遗骸、血腥、侵害、执行过程；不把受害者当猎奇道具',
 '少年仅背影或剪影，绝不正面露脸；所有可辨认面容必须登记于cast.json',
 '33名遇害者中29人发现于住宅内外、4人发现于河中，不能说33人全在地板下',
 '波戈小丑是社会身份的一部分，不推断小丑妆容导致犯罪；不宣称他穿戏服实施犯罪',
 '场景、动作、物品是示意重现，不冒充真实证据或逐分钟现场记录；不编造受害者最后一句话',
 '所有中文和数字由后期排字；智谱只生成无可读文字的连续动态镜头',
 '模型只允许cogvideox-flash；1301保留真实拒绝原因后合规改写，不自动混淆词语或循环重试',
 '同脸token逐字复用只是生成约束，不等于已通过画面同脸复审；实际片段须做check-frames和人工复核']

SOURCES = [{'id': 1,
  'url': 'https://www.britannica.com/biography/John-Wayne-Gacy',
  'usage': 'N01人物/波戈/承包商；N02一九六八年前科与假释；N03十五岁失踪者；N05住宅29与河中4；N06一九八零年定罪、死刑、一九九四年五月十日执行',
  'verification': 'article chunks 0–2 retrieved 2026-10-24',
  'citation': '[1](https://www.britannica.com/biography/John-Wayne-Gacy)'},
 {'id': 2,
  'url': 'https://www.upi.com/Archives/1994/05/10/The-events-leading-to-Gacys-execution/7264768542400/',
  'usage': 'N04十二月十三日首次搜查、查前科及监视；十二月二十一日第二次搜查',
  'verification': 'search excerpt retrieved 2026-10-24',
  'citation': '[4](https://www.upi.com/Archives/1994/05/10/The-events-leading-to-Gacys-execution/7264768542400/)'},
 {'id': 3,
  'url': 'https://graphics.chicagotribune.com/john-wayne-gacy-murders-40-years-later/index.html',
  'usage': 'N03皮斯特15岁、药店工作、十二月十一日告诉母亲谈建筑工作及失踪',
  'verification': 'search excerpt retrieved 2026-10-24',
  'citation': '[14](https://graphics.chicagotribune.com/john-wayne-gacy-murders-40-years-later/index.html)'},
 {'id': 4,
  'url': 'https://cookcountysheriffil.gov/john-wayne-gacy-victim-identified/',
  'usage': 'N05多年后仍继续确认身份；二零二一年确认Francis Wayne Alexander，片中不声称全部已经确认',
  'verification': 'official release search excerpt retrieved 2026-10-24',
  'citation': '[1](https://cookcountysheriffil.gov/john-wayne-gacy-victim-identified/)'}]

CHAPTERS = [('N01',
  '地板下的秘密',
  '一个能在聚会上逗人发笑的小丑，为什么会和三十三条生命联系在一起？一九七八年，芝加哥郊外，一栋普通住宅被警方封锁。令人不安的秘密，就在地板下。房主盖西，是承包商，也是邻里熟悉的面孔。他的舞台名字叫波戈。但揭开妆容的，不是一场表演，而是一名少年没有回家。'),
 ('N02',
  '熟人的另一面',
  '白天，盖西经营建筑生意，参加社区活动；换上戏服，他又成了派对上的小丑。人们容易把熟悉误认为可靠。可他的过去，并非没有警报。一九六八年，他曾因性侵被判刑，后来获假释，回到社区。旧案没让危险永远消失。当一个人看起来正常，谁会留意那些已经出现的异常？'),
 ('N03',
  '没有回家的少年',
  '一九七八年十二月十一日，十五岁的罗伯特·皮斯特，在一家药店工作后失踪。他曾告诉母亲，要去和一位承包商谈工作。那个人，就是盖西。工作机会，本该通向新的生活；这一次，却成为调查线索。母亲等不到儿子，警方开始寻找他。一个家庭的报案，留下了必须回答的问题：少年最后见了谁？'),
 ('N04',
  '追到住宅的线索',
  '警探循着线索找到盖西，核对说法，也查到了前科。十二月十三日，警方第一次搜查他的住宅，带走多件物品；监视和调查继续推进。盖西的日常还在上演，证据却正一点点靠近。十二月二十一日，警方再次搜查。镜头停在关闭的地板入口。有些事实，不需要猎奇的画面，也足以说明事情的重量。'),
 ('N05',
  '三十三个人生',
  '调查最终指向三十三名遇害者。警方在盖西住宅内外发现二十九人的遗骸，另有四人在河中找到。不是三十三人都埋在地板下面，也不能把他们缩成一个数字。他们是少年和年轻男子，有名字、家人与未来。有的身份，直到多年后才逐步确认。我们不再看小丑的笑脸。镜头留给空椅子，和等待答案的人。'),
 ('N06',
  '妆容之外的责任',
  '一九八零年，盖西被裁定三十三项谋杀罪成立，并被判处死刑。一九九四年五月十日，死刑执行。但判决不能替家人补回失去的岁月。妆容和真相，形成了刺眼的反差；可妆容不是罪恶的原因，证据和行为才是判断依据。我们需要记住的，不是一个怪物有多出名，而是每条生命都不该被遗忘。')]

SHOTS = [('S01',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '小丑半影与关闭入口，提出反差',
  '物件/色彩匹配；声音桥',
  'Framed inside one modest 1978 Midwestern wood-panelled living room. {C1} wears a red-and-white party '
  'clown costume with a small round red nose, simple white makeup and the identical underlying facial '
  'geometry. He occupies the left third in half shadow; a closed wooden floor access hatch remains on the '
  'right third. He slowly turns his head toward a warm lamp; cloth folds settle physically. Camera slowly '
  'pushes forward, both subjects remaining in the same room. All surfaces and props remain unlettered; '
  'action stays within this single framed space from first frame to last. HOLD: one continuous shot, no '
  'cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S02', 'graphic', '静态信息卡；后期排字', '案件名片', '沿用音桥', '案件名片', '轻纸张声；不盖旁白'),
 ('S03',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '卸妆只作身份隐喻，不演绎侵害',
  '物件/色彩匹配；声音桥',
  'Framed on one walnut dressing table in a modest Midwestern home. {C1} sits at the left third wearing a '
  'plain navy shirt, with a red clown nose resting on the table. He slowly folds a clean white '
  'handkerchief beside an unlettered mirror angled toward the wall. The camera makes a slow lateral slide; '
  'only his fictional face is visible, the mirror reflects no person. All surfaces and props remain '
  'unlettered; action stays within this single framed space from first frame to last. HOLD: one continuous '
  'shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S04',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '普通街区外观',
  '物件/色彩匹配；声音桥',
  'Framed outside one low single-storey brick Midwestern suburban house on an overcast winter evening. '
  'Leafless branches fill the top of frame and bare hedges fill the background. An unmarked parked sedan '
  'sits at the curb. A porch lamp brightens and a hanging wind chime sways. Camera slowly tracks parallel '
  'to the hedge; the house remains the only location. All surfaces and props remain unlettered; action '
  'stays within this single framed space from first frame to last. HOLD: one continuous shot, no cuts, no '
  'scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S05',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '搜查边界，不冒充证物影像',
  '物件/色彩匹配；声音桥',
  'Framed on a single fenced suburban driveway at dusk. Two anonymous fully clothed adult officers are '
  'shown from the shoulders down, setting a plain rope barrier between two posts. A flashlight beam moves '
  'across the damp driveway. Camera slowly pushes toward the rope, brick wall and hedge filling the '
  'background. All surfaces and props remain unlettered; action stays within this single framed space from '
  'first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S06',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '封闭的地板入口',
  '物件/色彩匹配；声音桥',
  'Framed downwards on one closed square wooden floor access panel in an otherwise empty wood-panelled '
  'room. An adult gloved hand moves a flashlight beam over the edges without opening the panel. Dust motes '
  'drift in the warm beam. Camera slowly tilts toward the brass pull ring, keeping the panel fully closed. '
  'All surfaces and props remain unlettered; action stays within this single framed space from first frame '
  'to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S07',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '聚会留下的面具',
  '物件/色彩匹配；声音桥',
  'Framed on one unlettered red clown nose and folded red-and-white costume on an empty chair in a modest '
  'living room. A gloved adult hand gently puts a plain evidence envelope beside the chair. The lamp cord '
  'sways slightly. Camera slowly slides right, keeping the cloth and chair physically stable. All surfaces '
  'and props remain unlettered; action stays within this single framed space from first frame to last. '
  'HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S08',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '空门与无人归来',
  '物件/色彩匹配；声音桥',
  'Framed inside one small 1978 family hallway. A closed blue front door stands on the right third; a '
  'plain coat hangs on a wooden hook. A fully clothed adult mother is a back silhouette at the left third, '
  'walking one step toward the door and stopping. Camera slowly approaches the still-closed door. All '
  'surfaces and props remain unlettered; action stays within this single framed space from first frame to '
  'last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S09',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '承包商的日常形象',
  '物件/色彩匹配；声音桥',
  'Framed in one small 1970s construction office with wooden walls. {C1} in a navy work shirt sits at a '
  'desk, slowly rolls up an unlettered building plan and rests it beside a carpenter pencil. His '
  'distinctive fictional face stays stable in warm side light. Camera slowly slides along the desk at eye '
  'level. All surfaces and props remain unlettered; action stays within this single framed space from '
  'first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S10', 'graphic', '静态信息卡；后期排字', '双重社会身份提示', '沿用音桥', '双重社会身份提示', '轻纸张声；不盖旁白'),
 ('S11',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '社区派对上的波戈',
  '物件/色彩匹配；声音桥',
  'Framed in one modest community hall with plain paper streamers and a wood-panelled wall. {C1} in a '
  'red-and-white clown outfit and simple white makeup folds a red balloon between both gloved hands, then '
  'looks up calmly. Identical underlying facial proportions to his unpainted role. Background adult guests '
  'are soft back silhouettes. Camera slowly tracks left. All surfaces and props remain unlettered; action '
  'stays within this single framed space from first frame to last. HOLD: one continuous shot, no cuts, no '
  'scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S12',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '邻里交往只作象征',
  '物件/色彩匹配；声音桥',
  'Framed at one brick-house front porch. Two fully clothed anonymous adults shown from behind exchange a '
  'plain cardboard parcel at the doorway. One briefly raises an open hand in greeting. Hedge and porch '
  'wall fill the background. Camera slowly slides parallel to the porch. All surfaces and props remain '
  'unlettered; action stays within this single framed space from first frame to last. HOLD: one continuous '
  'shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S13',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '旧案档案，不展示侵害',
  '物件/色彩匹配；声音桥',
  'Framed downwards on one walnut archive desk. A fully clothed adult clerk is visible only by sleeves and '
  'gloved hands, opening a plain closed folder and turning one unlettered page. Bundled unmarked files '
  'remain stationary along the rear edge. Camera slowly pushes toward the folder. All surfaces and props '
  'remain unlettered; action stays within this single framed space from first frame to last. HOLD: one '
  'continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S14',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '获释与返回社区，象征镜头',
  '物件/色彩匹配；声音桥',
  'Framed on one institutional corridor with plain cream walls and a single closed grey door. An anonymous '
  'fully clothed adult man shown only from behind walks slowly away from the camera carrying a small brown '
  'bag. His shoes and coat move naturally. Camera slowly follows without overtaking him. All surfaces and '
  'props remain unlettered; action stays within this single framed space from first frame to last. HOLD: '
  'one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S15',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '正常外观不等于安全',
  '物件/色彩匹配；声音桥',
  'Framed on one quiet suburban porch in blue winter light. An anonymous fully clothed adult man shown '
  'only from behind straightens an empty chair and walks one step into the doorway. A warm lamp stays on. '
  'Camera slowly withdraws along the porch rail, never entering the house. All surfaces and props remain '
  'unlettered; action stays within this single framed space from first frame to last. HOLD: one continuous '
  'shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S16',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '药店打烊后的岗位',
  '物件/色彩匹配；声音桥',
  'Framed inside one small 1978 American pharmacy with unlettered opaque medicine boxes, shelves filling '
  'the background. A fully clothed anonymous teenage worker is shown only from behind at the right third, '
  'placing a plain paper bag on a counter and taking his jacket. Camera slowly tracks sideways; no other '
  'person or face enters. All surfaces and props remain unlettered; action stays within this single framed '
  'space from first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera '
  'relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S17', 'graphic', '静态信息卡；后期排字', '失踪日期与年龄', '沿用音桥', '失踪日期与年龄', '轻纸张声；不盖旁白'),
 ('S18',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '谈工作的线索，少年只给背影',
  '物件/色彩匹配；声音桥',
  'Framed on one pharmacy doorway beneath a plain unlettered awning. A fully clothed anonymous teenage boy '
  'is a back silhouette at the left third, briefly pausing beside an anonymous adult male back silhouette '
  'at the right third. The adult points once toward a plain rolled building plan. Camera slowly slides '
  'along the storefront brick wall; both remain facing away. All surfaces and props remain unlettered; '
  'action stays within this single framed space from first frame to last. HOLD: one continuous shot, no '
  'cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S19',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '母亲等不到孩子',
  '物件/色彩匹配；声音桥',
  'Framed in one modest 1978 family kitchen. {C2} wears a muted blue wool cardigan and sits beside a plain '
  'wall clock with an unmarked face. She looks toward a closed hallway door, lowers an untouched cup to '
  'the table and pauses. Camera slowly pushes toward her fictional adult face in restrained warm '
  'lamplight. All surfaces and props remain unlettered; action stays within this single framed space from '
  'first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S20',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '本该通向未来的工作机会',
  '物件/色彩匹配；声音桥',
  'Framed on one teenage bedroom desk with a plain folded work apron, blank notebook and closed school '
  'bag. A curtain shifts gently in a cold draught and an adult hand sets a small warm desk lamp upright. '
  'Camera slowly slides across the unused objects, keeping the bedroom the only setting. All surfaces and '
  'props remain unlettered; action stays within this single framed space from first frame to last. HOLD: '
  'one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S21',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '报案电话，不编造对白',
  '物件/色彩匹配；声音桥',
  'Framed closely on one beige rotary telephone on a family kitchen table. Only a fully clothed adult '
  "woman's sleeve and hand are visible as she lifts the receiver and holds it still. The coiled cable "
  'moves naturally. Camera slowly approaches the telephone, kitchen wallpaper filling the background. All '
  'surfaces and props remain unlettered; action stays within this single framed space from first frame to '
  'last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S22',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '记录最后见面信息',
  '物件/色彩匹配；声音桥',
  "Framed downwards on one police-station desk. A detective's fully clothed sleeves and hands lay an "
  'unlettered pharmacy paper bag next to a plain notebook and point once between the two. No writing '
  'appears. Camera slowly slides parallel to the desk edge in cool overhead light. All surfaces and props '
  'remain unlettered; action stays within this single framed space from first frame to last. HOLD: one '
  'continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S23',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '街口寻找，接入调查',
  '物件/色彩匹配；声音桥',
  'Framed on one pharmacy side street in cold evening light. Two anonymous fully clothed adult officers '
  'shown only from behind walk slowly along the brick wall, their flashlights moving over the empty '
  'pavement. A low hedge blocks the far background. Camera slowly follows from waist height, never '
  'overtaking them. All surfaces and props remain unlettered; action stays within this single framed space '
  'from first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S24',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '警探核对说法',
  '物件/色彩匹配；声音桥',
  'Framed in one modest 1978 interview office. {C3} wears a brown wool suit and dark tie, sitting alone at '
  'the left third of a plain desk. He turns a blank folder page and raises his eyes thoughtfully. Camera '
  'slowly pushes toward his stable fictional adult face; a plain cream wall fills the background. All '
  'surfaces and props remain unlettered; action stays within this single framed space from first frame to '
  'last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S25',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '家属等待，保持角色一致',
  '物件/色彩匹配；声音桥',
  'Framed in one modest police waiting room with a plain wooden bench. {C2} in the identical muted blue '
  'cardigan sits at the left third, slowly folds her hands around an untouched cup and looks toward the '
  'closed office door. Camera slowly tracks right without changing location; soft cold light remains '
  'constant. All surfaces and props remain unlettered; action stays within this single framed space from '
  'first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S26',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '第一次搜查住宅',
  '物件/色彩匹配；声音桥',
  'Framed inside one wood-panelled suburban entrance hall. Two fully clothed anonymous adult officers '
  'shown only from behind gently open an empty coat cupboard and aim a flashlight at its shelves. Loose '
  'coat fabric sways. Camera slowly moves forward behind their shoulders, never revealing a face. All '
  'surfaces and props remain unlettered; action stays within this single framed space from first frame to '
  'last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S27',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '带走物品，不伪造真实证物',
  '物件/色彩匹配；声音桥',
  'Framed on one empty suburban dining-room table. An adult officer visible only as sleeves and gloved '
  'hands places a plain sealed paper bag next to a closed cardboard box. The paper flexes naturally as the '
  'hand withdraws. Camera slowly slides left with the tabletop and plain wall filling the frame. All '
  'surfaces and props remain unlettered; action stays within this single framed space from first frame to '
  'last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S28',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '继续核对线索的警探',
  '物件/色彩匹配；声音桥',
  'Framed inside one police archive office. {C3} in the identical brown wool suit and dark tie stands at '
  'the right third of a desk, slowly aligns two unlettered folders and looks down thoughtfully. Camera '
  'slowly tracks left; shelves of blank-spined files fill the background and his fictional facial geometry '
  'remains stable. All surfaces and props remain unlettered; action stays within this single framed space '
  'from first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S29',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '监视持续，住宅外保持空间一致',
  '物件/色彩匹配；声音桥',
  'Framed from beside one unmarked parked sedan outside a single-storey brick suburban house at night. Two '
  'anonymous fully clothed adult investigators are back silhouettes seated inside the car. One lowers a '
  'pair of binoculars. Raindrops slide down the side window. Camera slowly pushes toward the window, '
  'keeping the porch visible at the right third. All surfaces and props remain unlettered; action stays '
  'within this single framed space from first frame to last. HOLD: one continuous shot, no cuts, no scene '
  'change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S30', 'graphic', '静态信息卡；后期排字', '搜查时间线', '沿用音桥', '搜查时间线', '轻纸张声；不盖旁白'),
 ('S31',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '再搜查只停在关闭的入口',
  '物件/色彩匹配；声音桥',
  'Framed downwards on one closed wooden floor access panel in a wood-panelled suburban room. Only a fully '
  "clothed adult investigator's sleeves and gloved hands enter, setting a flashlight beside the panel "
  'without opening it. The beam slowly settles on the brass ring. Camera slowly pushes downward; the '
  'closed wooden surface fills the composition. All surfaces and props remain unlettered; action stays '
  'within this single framed space from first frame to last. HOLD: one continuous shot, no cuts, no scene '
  'change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S32', 'graphic', '静态信息卡；后期排字', '严谨区分三十三人的发现地点', '沿用音桥', '严谨区分三十三人的发现地点', '轻纸张声；不盖旁白'),
 ('S33',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '住宅外的调查，不展示挖掘或遗骸',
  '物件/色彩匹配；声音桥',
  'Framed at one fenced suburban garden in overcast winter light. Two fully clothed anonymous adult '
  'investigators shown only from behind carefully stretch a measuring cord between two wooden markers on '
  'undisturbed ground. A bush sways slightly. Camera slowly tracks parallel to the fence; no excavation is '
  'shown. All surfaces and props remain unlettered; action stays within this single framed space from '
  'first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S34',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '河中发现的四人以空景表达',
  '物件/色彩匹配；声音桥',
  'Framed on one quiet Midwestern riverbank in winter. Water ripples around bare reeds while an anonymous '
  'fully clothed adult investigator shown only from behind stands far away beside a plain rope barrier. '
  'Camera slowly pans along the reeds without showing the riverbed or any recovered object. All surfaces '
  'and props remain unlettered; action stays within this single framed space from first frame to last. '
  'HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S35',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '受害者留下的人生空位',
  '物件/色彩匹配；声音桥',
  'Framed in one empty modest family dining room. A single vacant wooden chair sits at the left third '
  'beside a clean folded work apron on the table. A curtain moves slowly and warm lamplight falls over the '
  'chair. Camera slowly pushes toward the empty place; no human image or photograph is visible. All '
  'surfaces and props remain unlettered; action stays within this single framed space from first frame to '
  'last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S36',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '多年辨认身份只作程序示意',
  '物件/色彩匹配；声音桥',
  'Framed closely on one modern identification laboratory workbench. A fully clothed adult lab worker is '
  'visible only as blue sleeves and gloves, sliding a plain closed sample rack toward an unlettered sealed '
  'envelope. No biological material is visible. Camera slowly slides sideways in neutral white light; this '
  'is a separate modern symbolic scene. All surfaces and props remain unlettered; action stays within this '
  'single framed space from first frame to last. HOLD: one continuous shot, no cuts, no scene change, no '
  'camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S37',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '把视线还给等待的人',
  '物件/色彩匹配；声音桥',
  'Framed in one quiet family kitchen. {C2} in the identical blue cardigan closes a blank photo album '
  'without showing any photograph and rests one hand on its cover. She exhales slowly and looks toward the '
  'empty chair at the right third. Camera slowly withdraws; her fictional adult face remains geometrically '
  'stable. All surfaces and props remain unlettered; action stays within this single framed space from '
  'first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S38', 'graphic', '静态信息卡；后期排字', '受害者不是猎奇数字', '沿用音桥', '受害者不是猎奇数字', '轻纸张声；不盖旁白'),
 ('S39',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '法院裁决，以虚构演员示意',
  '物件/色彩匹配；声音桥',
  'Framed inside one plain 1980 American courtroom. {C4} wears a simple black judicial robe, seated alone '
  'at a walnut bench. He closes an unlettered folder and looks forward solemnly, keeping both hands still '
  'afterward. Camera slowly pushes toward the bench; the plain wooden wall fills the background. All '
  'surfaces and props remain unlettered; action stays within this single framed space from first frame to '
  'last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S40', 'graphic', '静态信息卡；后期排字', '判决和执行时间线', '沿用音桥', '判决和执行时间线', '轻纸张声；不盖旁白'),
 ('S41',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '终结的是司法程序，不是家人的痛',
  '物件/色彩匹配；声音桥',
  'Framed on one silent institutional corridor with cream walls and a single closed grey door. An '
  'anonymous fully clothed adult officer is a back silhouette walking slowly away from the camera, then '
  'stopping outside the door. Camera slowly withdraws. No medical equipment, prisoner or execution process '
  'is shown. All surfaces and props remain unlettered; action stays within this single framed space from '
  'first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S42',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '卸下妆容的道具，拒绝神化凶手',
  '物件/色彩匹配；声音桥',
  'Framed on one walnut dressing table in the modest wood-panelled room. A red clown nose and folded '
  'red-and-white fabric lie beside an empty unlettered mirror angled toward the wall. An anonymous adult '
  'gloved hand gently closes a plain wooden box over the nose. Camera slowly tracks right; no person is '
  'reflected. All surfaces and props remain unlettered; action stays within this single framed space from '
  'first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S43',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '以证据而非外表判断',
  '物件/色彩匹配；声音桥',
  'Framed downwards on one plain archive desk. Fully clothed adult sleeves and hands slowly arrange three '
  'blank folders into a neat row and close a desk lamp shade slightly. The folders remain stable and '
  'unlettered. Camera slowly pushes toward the row under neutral warm light. All surfaces and props remain '
  'unlettered; action stays within this single framed space from first frame to last. HOLD: one continuous '
  'shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S44',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '空椅与白花，尊重每条生命',
  '物件/色彩匹配；声音桥',
  'Framed inside one quiet empty community room. One empty wooden chair occupies the left third; a simple '
  'vase of white flowers stands at the right third. A curtain breathes slightly and flower petals move '
  'naturally in a draught. Camera slowly slides toward the chair, with plain wood panelling filling the '
  'background. All surfaces and props remain unlettered; action stays within this single framed space from '
  'first frame to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白'),
 ('S45',
  'agnes',
  '单一连续慢移；镜内有真实动作',
  '结尾回到住宅，不再猎奇',
  '物件/色彩匹配；声音桥',
  'Framed outside one low single-storey brick Midwestern house at blue dawn. The closed front door remains '
  'at the right third; a porch lamp slowly dims as a bare hedge sways. Camera slowly retreats along the '
  'empty garden path. The house remains closed and the background is fully contained by trees and hedges. '
  'All surfaces and props remain unlettered; action stays within this single framed space from first frame '
  'to last. HOLD: one continuous shot, no cuts, no scene change, no camera relocation.',
  '环境底噪与物件同步轻音效；不盖旁白')]

CARD_HEADER = '盖西案 · 资料摘要'

CARD_FOOTER = '公开资料整理 · AI动画情景重现 · 非原始档案影像'

CARDS = {'S02': ('约翰·韦恩·盖西案', '美国 · 芝加哥郊外 · 1978 年案发曝光', '33 名遇害者 · 本片不展示侵害过程'),
 'S10': ('熟悉不等于可靠', '建筑承包商 · 社区活动 · 波戈小丑', '戏服不是犯罪原因 · 行为与证据才是判断依据'),
 'S17': ('1978 年 12 月 11 日', '15 岁的罗伯特·皮斯特失踪', '一次关于工作的谈话 · 成为调查线索'),
 'S30': ('两次搜查之间', '12 月 13 日首次搜查 → 持续调查', '12 月 21 日再次搜查 · 真相逐步显现'),
 'S32': ('33 名遇害者', '29 人：住宅内外发现 · 4 人：河中找到', '并非所有人都在地板下 · 不展示遗骸'),
 'S38': ('记住每一个人', '他们有自己的名字、家人和未来', '受害者不是故事里的道具'),
 'S40': ('判决与执行', '1980 年：33 项谋杀罪成立 · 判处死刑', '1994 年 5 月 10 日：死刑执行')}

TITLE_CARD = ['小丑背后的真相', '约翰·韦恩·盖西案 · 美国 · 1978']

END_CARD = ['熟悉的面孔，就一定可靠吗？',
 '约翰·韦恩·盖西案 · 33 名遇害者',
 '每条生命都不该被遗忘。',
 '资料：Britannica / UPI / Chicago Tribune / Cook County Sheriff · AI动画情景重现']

CAPTION_KEYWORDS = ['三十三',
 '二十九',
 '四人',
 '盖西',
 '波戈',
 '地板下',
 '罗伯特·皮斯特',
 '十五岁',
 '十二月十一日',
 '十二月十三日',
 '十二月二十一日',
 '一九八零年',
 '一九九四年',
 '死刑',
 '每条生命']

LABEL_OVERRIDES = {'S01': 'AI动画情景重现 · 非新闻影像 · 非本人容貌',
 'S03': 'AI动画情景重现 · 非新闻影像 · 非本人容貌',
 'S09': 'AI动画情景重现 · 非新闻影像 · 非本人容貌',
 'S11': 'AI动画情景重现 · 非新闻影像 · 非本人容貌',
 'S19': 'AI动画情景重现 · 非新闻影像 · 非本人容貌',
 'S24': 'AI动画情景重现 · 非新闻影像 · 非本人容貌',
 'S25': 'AI动画情景重现 · 非新闻影像 · 非本人容貌',
 'S28': 'AI动画情景重现 · 非新闻影像 · 非本人容貌',
 'S37': 'AI动画情景重现 · 非新闻影像 · 非本人容貌',
 'S39': 'AI动画情景重现 · 非新闻影像 · 非本人容貌'}

SFX_EVENTS = [('S06', 'keys'),
 ('S07', 'paper'),
 ('S13', 'paper'),
 ('S21', 'phone'),
 ('S22', 'paper'),
 ('S26', 'keys'),
 ('S27', 'paper'),
 ('S28', 'paper'),
 ('S31', 'keys'),
 ('S36', 'paper'),
 ('S39', 'paper'),
 ('S42', 'keys'),
 ('S43', 'paper')]

TITLES = ['小丑背后的真相：约翰·韦恩·盖西案，33条生命不该只剩一个数字', '一名少年没有回家，揭开了盖西普通住宅后的真相', '熟悉的面孔就可靠吗？三分钟看懂约翰·韦恩·盖西案']

HOOK = '一个能在聚会上逗人发笑的小丑，为什么会和三十三条生命联系在一起？一九七八年，芝加哥郊外，一栋普通住宅被警方封锁。真正令人不安的，不是墙上的装饰，而是地板下。房主约翰·韦恩·盖西，是承包商，也是邻里熟悉的面孔。他给自己取了一个舞台名字，波戈。但揭开这层妆容的，并不是一场表演，而是一名少年没有回家。'

GOLDEN_LINES = ['每条生命都不该被遗忘。', '熟悉不等于可靠，行为与证据才是判断的依据。', '受害者不是故事里的道具。']

DESCRIPTION = ('一九七八年，十五岁的罗伯特·皮斯特失踪，警方的调查指向约翰·韦恩·盖西。一栋普通住宅与三十三名遇害者，让波戈小丑的另一面浮出水面。本片梳理失踪、调查、发现与判决，不展示遗骸或侵害过程。画面为3D '
 'AI动画情景重现，虚构演员非本人容貌，不是新闻或原始证物影像。每条生命都不该被遗忘。')

QUESTION = '熟悉的面孔，就一定可靠吗？你认为判断一个人最该看什么？'

HASHTAGS = ['#案件解说', '#真实案件', '#盖西案', '#纪实', '#AI动画情景重现']

GRID = 4

AGNES_SECONDS = 6

SEED_BASE = 19781211

FACE_SHOTS = {'S01': ['C1'],
 'S03': ['C1'],
 'S09': ['C1'],
 'S11': ['C1'],
 'S19': ['C2'],
 'S24': ['C3'],
 'S25': ['C2'],
 'S28': ['C3'],
 'S37': ['C2'],
 'S39': ['C4']}

REFERENCE_SHOTS = {}

# Immutable revision: references are current-film assets, never old identity experiments.
REFERENCE_REVISION = "b5be38f39679925ca5ae29fb972145cb77b33eaa"
FIRST_FRAME = {
    "S01": "first_frames/S01.jpg", "S09": "first_frames/S09.jpg",
    "S11": "first_frames/S11.jpg", "S25": "qa/retake-references/C2.jpg",
    "S28": "qa/retake-references/C3.jpg", "S37": "qa/retake-references/C2.jpg",
    "S04": "qa/retake-references/C0.jpg",
    "S29": "qa/retake-references/C0.jpg", "S45": "qa/retake-references/C0.jpg",
}

FRAME_REVISIONS = {"S04": "06cd2bfb9c44c4dc7bb63b977856930a4c159653", "S29": '06cd2bfb9c44c4dc7bb63b977856930a4c159653', "S45": '06cd2bfb9c44c4dc7bb63b977856930a4c159653'}

# Targeted content corrections after inspecting the actual 2 fps source contact sheets.
# These new prompts/first-frame URLs change request hashes; the other 19 clips must be reused.
RETAKE_BODIES = {
    "S01": "In the supplied first frame, {C1} is the same fictional actor wearing the red-and-white clown costume and small red nose. Preserve his exact face, costume and this room. He slowly turns his head toward the warm lamp and breathes gently; fabric settles naturally. The flush square floor access panel at right stays completely CLOSED and level with the floor for the entire shot. No one touches it. Gentle camera push, one continuous shot, no cuts or new people.",
    "S04": "Continue the supplied first frame of the SAME established brick house, keeping exactly its roof, windows, door, hedge and parked car. The camera is LOCKED OFF. The small anonymous fully clothed adult back silhouettes already along the lower foreground slowly walk to the left and partly out of frame; none turns toward camera. Bare branches visibly sway in the breeze and hedge tips bend independently. Blue-hour exterior with warm windows, one continuous shot, no new faces, no pan or zoom, no cut or building change.",
    "S07": "Fixed-camera colour 3D CGI close shot of a red-and-white clown costume draped on a wooden chair beside a tungsten lamp in a plain 1978 wood-panelled room. Two anonymous adult white-gloved hands enter from the side and slowly fold ONE loose red sleeve over the costume, then move away. A small round red nose stays stationary on the seat, unchanged. No face or body in frame. The camera does not move: the folding cloth and hands provide the clearly visible motion. Stable anatomy, single continuous shot, no text or scene changes.",
    "S09": "Continue the supplied first frame with exactly the same fictional actor {C1}, navy shirt, face and home-office desk. He slowly slides the blank building plan a few centimetres across the desk with both hands, then lowers his gaze. Keep the paper flat and fingers anatomically stable. Gentle lateral camera move. One uninterrupted shot, no makeup, no mirror, no additional people or scene change.",
    "S11": "Continue the supplied first frame. {C1} wears the identical red-and-white clown costume, white collar, white gloves and small red nose. Preserve his exact underlying face and the single community room. He slowly opens his palms in a small friendly party gesture, then relaxes them; the tethered red balloon gently sways independently. No other people. Restrained expression, no horror. Single continuous slow camera slide, no costume change or cuts.",
    "S13": "Colour 3D CGI animation, physically modelled walnut archive desk in a plain 1970s office. Tight downward close-up of one unlettered buff paper folder lying FLAT on the desk. One anonymous adult hand in a dark wool sleeve slowly closes the folder, rests on it briefly, then withdraws out of frame. All faces and bodies remain outside frame. Stable paper geometry, natural hand motion, soft tungsten light and cool blue fill. One continuous slight camera move. No people in background, no shadows shaped like people, no writing, no floating props or scene cuts.",
    "S16": "COLOUR three-dimensional CGI animated reenactment, NOT black-and-white archive footage and NOT live action. Fixed camera directly BEHIND one fully clothed anonymous teenage back silhouette at a plain 1978 pharmacy counter. Only the BACK of his head, shoulders and grey jacket are seen throughout. His face NEVER turns toward camera, no side profile. He gently puts a plain paper bag on the counter with his back still toward camera. Unlettered shelves, muted blue and tungsten colours, physically modelled objects and cloth. One continuous shot, no additional people, no text, no progress bars or scene cuts.",
    "S20": "Fixed-camera colour 3D CGI medium close shot of a plain 1978 wooden work desk with ONE closed unlettered cream application folder. From the FIRST frame one anonymous adult hand in a plain dark long sleeve is ALREADY resting on the folder at the right side of the desk. The hand slowly SLIDES the rigid folder across the tabletop into the centre, completing the placement just before the shot ends. Wrist connected to sleeve, stable fingers and thumb. No late hand entrance or reach from outside frame, no face, other people, text, new objects or scene changes. Fixed tripod: hand and folder supply clear continuous physical motion.",
    "S21": "Colour 3D CGI close-up of one intact cream-coloured 1970s rotary telephone on a plain walnut side table. The NORMAL CURVED HANDSET rests HORIZONTALLY on its cradle throughout; it is never lifted or changed. One anonymous adult index finger slowly rotates the circular dial and lets it return. Only a hand and a dark sleeve are visible, no face or body. The phone body, cradle, handset and coiled cord retain their separate rigid shapes throughout. Soft tungsten and blue light. One continuous small camera move, no lettering, no cuts or transformation.",
    "S25": "Continue the supplied first frame with the exact same fictional adult actress {C2}, the same blue cardigan, hair, face and modest home interior. She pauses, gently nods once and slowly lowers her gaze toward the table as if recalling a detail. Her shoulders move with a natural breath. Hands remain below the frame; no new props. Quiet respectful family-impact reenactment. A slight continuous camera slide, no facial morphing, new people or cuts.",
    "S28": "Continue the supplied first frame with exactly the same fictional detective actor {C3}, preserving his GREY MOUSTACHE, square glasses, swept-back grey hair, brown tweed jacket and face. In the same plain office he slowly lays the blank folder flat on the desk and briefly looks up toward the left, then back down. Stable hands, no writing. One continuous slight camera push, no additional people, facial changes or scene cuts.",
    "S29": "Continue the supplied first frame outside the SAME brick house, preserving its roof, windows, front door, hedge and parked unmarked car. The camera remains OUTSIDE for the entire shot. In the low foreground the existing anonymous adult back silhouettes gently shift weight without revealing any faces; wind bends the hedge and bare twigs independently. The parked car stays the same rigid car in the same place. Cool evening surveillance atmosphere with warm window light. One continuous shot, no interior view, no dissolves, double exposure, new objects or scene change.",
    "S31": "Colour 3D CGI close shot of a square wooden floor access panel lying completely CLOSED, flush and LEVEL with the surrounding wooden floor in a modest 1978 wood-panelled room. The panel is a flat square seam with a small recessed pull, NOT an upright door. A soft flashlight beam slowly sweeps across the closed panel from left to right; the camera slides gently at low height. No person, hand or face is visible anywhere. The lid remains closed and untouched from first frame to last. No opening, dark hole, contents, bodies, remains, violence or scene cuts.",
    "S45": "Continue the supplied first frame of the SAME established brick house, preserving exactly its roofline, windows, door and hedge. Cool blue dawn atmosphere. The small anonymous adult back silhouettes already low in the foreground slowly walk away beyond the bottom edge without turning toward camera; the entrance stays shut. Wind gently sways the bare branches and hedge independently as the camera slowly retreats. The porch lamp gradually dims. Leave the house quiet, no new people, no face close-ups, no new buildings, interior view, dissolves or scene changes.",
    "S34": "Fixed-camera colour 3D CGI riverbank exterior in a cold Midwestern winter. Open flowing water is clearly visible across the middle of the frame. One EMPTY plain wooden rowboat is tied securely to a short wooden piling at right, gently bobbing UP AND DOWN with the water; the rope remains taut and the boat keeps its rigid shape. Wind sways tall reeds at left and small ripples flow across the river. No people, bodies, remains, contents, writing or discoveries. The camera remains completely still so the independent boat, water and reed motion is obvious. One continuous quiet respectful shot.",
    "S35": "Fixed-camera colour 3D CGI medium-wide shot of ONE EMPTY wooden chair beside a tall window in a modest 1978 walnut-panelled room. A thin white curtain visibly billows a hand-width INTO the room, then settles and billows again in a continuous draught. The chair stays empty and rigid. Soft tungsten lamp, restrained cold blue window light. No people, hands, portraits, writing or new objects. The camera does NOT move, pan or zoom: the physically simulated curtain supplies the continuous motion. One uninterrupted shot.",
    "S41": "Fixed-camera colour 3D CGI institutional corridor. From the VERY FIRST frame one anonymous fully clothed adult officer is ALREADY standing fully visible in the RIGHT foreground with his BACK to the camera. He walks slowly AWAY down the clear right side of the corridor throughout the shot, never stopping or turning. A closed grey door is on the LEFT wall, well away from his walking path; it stays shut and nobody interacts with or emerges from it. Cream walls, warm ceiling light, plain dark uniform with no readable badge. Back silhouette only, no front face or reflection. The camera remains locked off. One continuous physical walk with stable two legs and arms, no sudden appearance, doorway crossing, zoom or cut.",
    "S44": "Fixed-camera colour 3D CGI community-room interior: an EMPTY wooden chair at left, a plain vase of white flowers at right and a thin white curtain behind the vase. A steady draught makes the curtain visibly billow into the room twice and the flower stems nod gently without changing shape. One loose white petal slowly drifts down beside the vase. No people or faces, no text or new objects. Soft tungsten and blue light, respectful quiet atmosphere. The camera is completely still throughout; cloth, flowers and petal move independently. One continuous shot, no zoom or cuts.",
    "S37": "Continue the supplied first frame with the exact same fictional adult actress {C2}, identical face, chestnut waved hair, blue cardigan and home interior. She slowly turns her gaze from the closed door toward the camera's left, then rests her eyes downward; one shoulder relaxes with a slow natural breath. Restrained grief, no melodrama. Hands stay below frame, no new objects or people. One continuous gently moving camera shot, no face or age changes and no cuts.",
}
MOTION_STYLE = ('Colour physically modelled 3D CGI animated reenactment, 1970s American Midwest, '
 'walnut and period clothing, cool blue fill and warm tungsten light. FIXED tripod camera, no pan or zoom. '
 'Only the specified character, cloth, light or object moves; make that independent motion clearly visible. '
 'One continuous shot, horizontal thirds, uncluttered lower subtitle area. No readable text or real portraits. ')
MOTION_STYLE_SHOTS = {'S04','S07','S13','S16','S20','S21','S31','S34','S35','S41','S44'}
SHOTS = [row[:5] + ((RETAKE_BODIES[row[0]] + " HOLD: one continuous shot, no cuts, no scene change, no camera relocation.") if row[0] in RETAKE_BODIES else row[5],) + row[6:] for row in SHOTS]

def first_frame_urls():
    base = f"https://raw.githubusercontent.com/32r4e2q-hub/desktop-tutorial/{REFERENCE_REVISION}/production/gacy1978/"
    return {sid: (base if sid not in FRAME_REVISIONS else base.replace(REFERENCE_REVISION, FRAME_REVISIONS[sid])) + rel
            for sid, rel in FIRST_FRAME.items()}


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
    assert 760 <= sum(len(text) for _, _, text in CHAPTERS) <= 800
    assert sum(row[1] == "agnes" for row in SHOTS) == 38
    assert sum(row[1] == "graphic" for row in SHOTS) == 7
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
    story["model"] = "cogvideox-flash"
    story["branch"] = "arena/3c0c229a-desktop-tutorial"
    story["_scaffold"] = {"reference": "production/kitakyushu2002"}
    story["publication"] = {"titles": TITLES, "description": DESCRIPTION, "question": QUESTION, "hashtags": HASHTAGS}
    story["cover_brief"] = {"layout": "左侧小丑半影与红鼻，右侧关闭的地板入口；单一3D室内场景", "text": "小丑的秘密", "text_color": "gold", "status": "generated_pending_final_film_consistency", "file": "delivery/封面_小丑的秘密.jpg"}
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
        if sid in MOTION_STYLE_SHOTS:
            shot["style_prefix_override"] = MOTION_STYLE
            shot["camera"] = "固定机位；镜内有明确独立动作"
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
    print(f"露脸镜头：{len(FACE_SHOTS)} 镜；首帧参照：{len(FIRST_FRAME)} 镜（非同脸验收结论）")
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

#!/usr/bin/env python3
"""金大斗案的唯一内容源；时间为规划网格，需配音后重对CUTS。
参考：production/zama2017（座间九人案，源commit见template-origin.json）。
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TITLE = '金大斗：一条牛仔裤，牵出十七条人命'
MODEL = 'agnes-video-2.5-flash'
STYLE_PREFIX = (
    'Photorealistic cinematic 3D animated reenactment, physically based materials, volumetric light, '
    'subtle film grain, realistic fabric and wood; South Korea in 1975, modest Seoul laundromat with '
    'wood counter and rotary telephone, rural South Jeolla homes, period railway stations, police offices '
    'with paper files, winter 1976 prison exterior; horizontal 16:9 composition, restrained teal-grey and '
    'warm tungsten lighting. This is CGI animation, not live-action footage or 2D illustration. '
    'Anonymous fictional period figures, not likenesses of real people; show figures from behind or hands '
    'only. The slim suspect wears a brown jacket and short black hair, the shopkeeper a beige shirt and '
    'dark apron, investigator a charcoal coat. Maintain these clothes and body silhouettes across shots. '
    'No visible victims, no violence, no injuries, no corpses. Blank props and sign-free framing, no readable '
    'letters, digits, logos or captions. One scene and one slow camera move with natural object movement. '
)
NEGATIVE_PROMPT = 'gore, blood, corpse, violence, modern smartphone, modern CCTV, 2D, cartoon, waxy skin, distorted anatomy, readable text, watermarks, scene cuts'
PRINCIPLES = [
    '写实3D CGI情景重现，常驻AI动画情景重现·非新闻影像；绝不冒充证物或原始庭审影像。',
    '视频生成仅Agnes；不调用智谱或任何其他供应商；费用未证实为零前不批量生成。',
    '角色背影与手部采用统一衣着，不将合成面孔说成真人；受害者不出镜。',
    '不重演作案或行刑，不展示血腥；裤子只呈现克制的暗色斑痕。',
    '时间轴与数字均后期排字，视频模型不生成中文招牌、地图标签或判决文字。',
    '原稿中的警察守候细节、具体初次案发日、老板年龄、赃款数额、嫌疑人的内心独白证据不足，删去。',
    '六章旁白以公开报道的可核对事实为主；布景与动作是艺术示意，不当作现场纪录。',
    '人工复审画面、字幕、配音后才能交付；工作流成功不等于成片通过QC。',
]
SOURCES = [
    {'id':1,'url':'https://koreaherald.com/view.php?ud=20170526000521','usage':'韩国先驱报2017-05-26：1975年8至10月、55天17人、包括老人和幼儿、洗衣工报警、1976年12月执行；主来源。'},
    {'id':2,'url':'https://www.thereviewgeek.com/where-is-kim-dae-doo-now/','usage':'2023-11-10二手报道：1976-12-28、西大门监狱、审判经过；日与地点需进一步一手史料核验，口播仅用1976年12月。'},
    {'id':3,'url':'https://horizonmag.org/the-killer-got-caught-in-the-net-because-of-his-blood-stained-pants/','usage':'2022-07-27二手报道：打架解释、洗衣店报警、共同被告只涉及部分犯罪。与原稿对照，未采用等待取衣等未证实细节。'},
]
CHAPTERS = [
    ('N01','洗得掉污迹，洗不掉线索',
     '他把一条牛仔裤送进洗衣店，却把十七条人命的线索，送到了警方手里。一九七五年，韩国。洗衣工接过裤子，注意到不寻常的斑痕。男人解释，是打架留下的。老板做了一件事：报警。这个男人叫金大斗。此时，那条裤子背后，不是一次冲突，而是多地的连续命案。故事要从那个夏天说起。'),
    ('N02','分散的命案',
     '那年八月至十月，金大斗接连犯下抢劫杀人案。乡间住宅，普通家庭，五十五天里，许多人失去生命。遇害者中有老人，甚至有年幼的孩子。他们留下的不是一个数字，而是一张再也等不到人坐下的餐桌。案件分散发生，线索也分散。没有今天的监控网络，调查人员要从纸质案卷中寻找联系。'),
    ('N03','一个普通人的警觉',
     '可最重要的突破，不在地图上，而在一间普通洗衣店里。一条需要清洗的裤子，一个关于打架的解释，一名觉得不对劲的店主。老板不知道自己面对的是谁。他没有冒险追问，只把异常交给警方。可能被洗掉的痕迹，就这样留下了。金大斗随后被捕，警方开始调查。分散的案卷，终于有了一个共同的名字。'),
    ('N04','供述不是终点',
     '被捕之后，金大斗承认了自己的犯罪。但供述不是调查的终点。警方还要把供述，与不同地区的案件逐项核对。原本分开的线索，开始拼成同一段时间：一九七五年八月至十月，五十五天，十七人遇害。这不是神奇推理的故事。真正改变方向的，是有人报告异常，而调查人员继续把异常追查到底。'),
    ('N05','责任不能被背景遮住',
     '案件进入司法程序，金大斗被判处死刑。一九七六年十二月，他被执行死刑。一个人的犯罪到此终结，十七个家庭的伤痛，却不会跟着判决结束。有关报道也提到，他曾把自己的处境归结为贫困和被冷落。但受挫不能成为伤害他人的理由，更不能抹去受害者。我们记住这个案件，不是为了替凶手制造传奇。'),
    ('N06','回到那条牛仔裤',
     '再看那间洗衣店，柜台、电话、普通的顾客，都没有什么特别。特别的是，老板没有把眼前的不合理，当成与自己无关。一条裤子可以被洗干净，留下的线索，却让警方追到了真相。五十五天，十七条生命。最值得记住的，不是凶手有多可怕，而是那些本不该空下来的座位。如果你遇到可疑情况，别独自冒险，交给警方处理。'),
]
# 每章8/7/8/7/8/7镜；每个模型镜头请求6秒720P，最终1080p为合成放大，不宣称原生1080p。
# 英文提示词只描述单场景，不要求生成文字或在一个请求里做多个转场。
SHOT_ROWS = [
 ('柜台上的裤子','缓慢推近','Close view of folded faded blue jeans with a small muted dark stain on a wood counter. A hand places the jeans down; fabric settles; shop interior fills background.'),
 ('普通洗衣店','沿柜台横移','Interior of a modest laundromat. Blank hanging garments sway gently behind a wooden counter; a period washing drum turns slowly.'),
 ('老板停下手中的活','侧后方推进','Back view of the shopkeeper in beige shirt and dark apron inspecting folded jeans on the counter, pausing with one hand on the fabric.'),
 ('嫌疑人保持普通外表','固定中景','Rear three-quarter view of the slim brown-jacketed man at the counter, shifting weight slightly; his head remains turned away.'),
 ('拨出一个电话','电话近景推进','Close-up of a hand lifting the handset of a black rotary telephone on a wooden shelf; the rotary dial returns slowly.'),
 ('警员接警','肩后缓慢推近','Rear view of an investigator in charcoal coat answering a period desk telephone, picking up a pencil beside a blank paper pad.'),
 ('警方开始记录','俯拍横移','Hands carefully placing a blank evidence envelope beside folded jeans on an office desk, with a pencil resting on an unmarked pad.'),
 ('案件名片','graphic',['一条牛仔裤','韩国 · 一九七五年','五十五天，十七人遇害']),
 ('乡村清晨','低机位推进','Exterior of a modest South Jeolla rural home. Wind moves laundry in a quiet courtyard; the doorway remains empty.'),
 ('生活被打断后的房间','室内横移','Empty period household room with a slightly open drawer, plain wood furniture and a lamp shade swaying gently. No people or harm.'),
 ('调查住宅环境','背后跟拍','Rear view of a charcoal-coated investigator walking slowly through a quiet rural courtyard, stopping at an empty doorway.'),
 ('小店生活','货架横移','Inside a modest 1970s village shop, blank unlabeled tins on wooden shelves. Sunlight shifts softly, with no people and no signs.'),
 ('不同地方的路途','月台固定广角','A period passenger train slowly leaves a modest railway platform. Back-view commuters wait at a safe distance, sign-free framing.'),
 ('首尔普通住宅街','缓慢前移','A modest Seoul residential lane with period parked cars and muted winter coats on distant back-view pedestrians; only walls and doorways visible.'),
 ('时间与规模','graphic',['五十五天','一九七五年八月至十月','多地命案 · 十七人遇害']),
 ('纸质档案时代','案卷俯拍','An investigator opens blank brown file folders across an office desk. A period typewriter and rotary phone remain still in the background.'),
 ('有限的调查工具','桌面滑轨','Close view of a film camera, pencil and plain folders on a period police desk. A hand moves the camera aside.'),
 ('寻找联系','肩后推进','Rear view of an investigator comparing two blank folders under a tungsten desk lamp, slowly turning one page.'),
 ('回到洗衣店','柜台侧向推近','The folded blue jeans rest on the same wood counter; the shopkeeper rear silhouette enters frame and stops short of touching them.'),
 ('观察而非冒险','侧后方中景','Rear view of the shopkeeper in beige shirt and dark apron setting down his work and turning towards the telephone shelf.'),
 ('让专业人员处理','手部固定近景','A shopkeeper hand rests on the black telephone receiver; he lifts it once and holds it, no dialing text visible.'),
 ('物证被保存','俯拍推进','An investigator with gloves places folded denim into a plain brown evidence envelope on a wooden table. Hands move slowly and carefully.'),
 ('转折不是神迹','graphic',['普通人的警觉','发现异常 → 报告警方','不是独自侦查，也不是冒险追问']),
 ('嫌疑人被带走的示意','中远景缓慢拉远','Back view of a brown-jacketed man walking beside an investigator towards a parked 1970s police car, calm escorted movement, no struggle.'),
 ('询问室','肩后固定镜头','Period interview room, the brown-jacketed man sits facing away at a wood table, investigator seen only from behind with a folder.'),
 ('笔录与案卷','笔尖近景推进','Close view of an investigator hand turning a blank page and placing a pencil beside it; anonymous shoulders in the background.'),
 ('逐案核对','俯拍横移','Two gloved hands arrange blank evidence folders in a tidy row on the police desk, one folder per motion.'),
 ('不同地区的卷宗','桌面缓慢拉远','A desk filled with separate blank brown folders under a warm lamp, a hand bringing one more folder into the row.'),
 ('不能只凭供述','侧后方推进','Two investigators seen from behind compare plain files at one wooden desk, one points to a page without visible writing.'),
 ('调查结论','graphic',['线索终于串联','五十五天 · 十七人遇害','不是数字，是失去亲人的家庭']),
 ('司法程序','法庭后方慢推','Wide rear view of a 1970s Korean courtroom, officials behind wooden desks and a defendant rear silhouette. Restrained, no visible writing.'),
 ('审阅材料','桌面推进','Hands of a court official open a plain folder beside a wood desk lamp, slowly turning one page, no legible documents.'),
 ('严肃的裁判空间','固定广角','Empty wooden courtroom benches and the judge desk in soft daylight, gentle dust particles drifting in a light beam.'),
 ('被告席的背影','远景缓慢拉远','Brown-jacketed man seated facing away in the defendant area of a period courtroom, shoulders still, no dramatic expression.'),
 ('监狱外墙','缓慢前移','Exterior of a period Seoul prison wall in winter, snow drifting softly beside a heavy closed iron gate. No execution imagery.'),
 ('刑罚结局','graphic',['司法结局','金大斗被判死刑','一九七六年十二月被执行']),
 ('一扇门关闭','固定镜头','An empty prison corridor ending in a heavy iron door slowly closing. No prisoners or harm; plain walls fill the background.'),
 ('困境不等于免责','graphic',['背景不能免责','贫困与挫折不是伤害他人的理由','不为犯罪者制造传奇']),
 ('空下来的餐桌','室内温和横移','Empty modest Korean household dining table set with plain ceramic bowls; curtains shift gently, warm daylight on an unused chair.'),
 ('没有等到归人的门口','门槛缓慢推进','Two pairs of plain shoes at the threshold of a quiet rural home, a soft breeze stirs a hanging cloth, no people.'),
 ('回到普通柜台','柜台缓慢拉远','Same modest laundromat counter after closing time, dark apron folded on a stool, hanging shirts moving slightly.'),
 ('一个电话的重量','电话近景','Black rotary telephone rests on a plain wood shelf, soft morning light moving across the receiver; only the shelf in view.'),
 ('案卷合上','俯拍推进','An investigator hand closes a plain brown folder gently on the wooden office desk, and removes the hand from frame.'),
 ('生活应当继续','低机位前移','A quiet Korean residential courtyard in warm morning light, distant adults seen only from behind walking normally, leaves moving gently.'),
 ('尊重与提醒','graphic',['记住那些空下来的座位','金大斗案 · 韩国，一九七五年','遇到可疑情况，别冒险，交给警方']),
]
TITLES = [TITLE,'他想洗掉裤子上的痕迹，却留下了十七条人命的线索','五十五天、十七人：破案转折藏在一家洗衣店']
HOOK = '他想洗掉的，恰恰是警方需要的线索。'
QUESTION = '你遇到可疑情况，会怎么安全地处理？'
GOLDEN_LINES = ['一条裤子可以洗干净，责任却不能被洗掉。','每个数字背后，都有一个本不该空下来的座位。']
DESCRIPTION = '一间普通洗衣店、一条牛仔裤、一名没有忽略异常的店主。金大斗案的突破，不是神奇推理，而是报警之后持续的追查。依据公开报道改编，画面为AI动画情景重现，非真实案件影像；不展示暴力，不美化犯罪。'
HASHTAGS = ['#真实案件','#悬疑解说','#3D动画','#金大斗案']


def build():
    assert len(SHOT_ROWS) == 45
    shots, cards = [], {}
    for i, (purpose, camera, prompt) in enumerate(SHOT_ROWS):
        sid = f'S{i+1:02d}'
        kind = 'graphic' if camera == 'graphic' else 'agnes'
        if kind == 'graphic':
            cards[sid] = prompt
        shots.append({'id':sid,'kind':kind,'start':i*4,'duration':4,
                      'narration_id':f'N{min(6,i*4//30+1):02d}',
                      'purpose':purpose,'camera':camera,'transition_out':'物件匹配或环境声音桥',
                      'prompt':(prompt + ' Hold this exact scene from first frame to last; no cut, no location change.') if kind=='agnes' else '',
                      'graphic':purpose if kind=='graphic' else '',
                      'seconds':6,'aspect':'16:9','resolution':'720p','frame_rate':24,
                      'seed':19750813+i,'sfx_note':'电话/纸张/列车/环境声按语义使用，配乐压低于旁白'})
    chapters = [{'id':cid,'title':title,'start':i*30,'duration':30,'text':text}
                for i,(cid,title,text) in enumerate(CHAPTERS)]
    story = {'title':TITLE,'target_duration':180,'width':1920,'height':1080,'fps':30,
             'model':MODEL,'branch':'arena/09864331-desktop-tutorial',
             'source_resolution_note':'Agnes 2.5-flash计划720P；成片1080p合成，不声称原生1080p',
             'style_prefix':STYLE_PREFIX,'negative_prompt':NEGATIVE_PROMPT,'principles':PRINCIPLES,
             'sources':SOURCES,'chapters':chapters,'shots':shots,
             'presentation':{'card_header':'案件档案 / 韩国 · 一九七五年','card_footer':'资料摘要与示意图 · 非原始档案',
              'cards':cards,'title_card':['一条牛仔裤','牵出十七条人命'],
              'end_card':['记住那些空下来的座位','金大斗案 · 一九七五年 · 十七人遇害',
                          '发现异常，别独自冒险','资料：韩国先驱报 / AI动画情景重现'],
              'caption_keywords':['牛仔裤','十七','五十五','报警','金大斗','不能'],
              'label_overrides':{'S31':'AI动画示意 · 非庭审影像','S34':'AI动画示意 · 非庭审影像'},
              'sfx_events':[['S05','phone'],['S16','paper'],['S26','paper'],['S43','paper']]}}
    (HERE/'audio').mkdir(exist_ok=True)
    (HERE/'story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2)+'\n')
    old = json.loads((HERE/'audio/manifest.json').read_text()) if (HERE/'audio/manifest.json').exists() else {}
    existing = {x['id']:x for x in old.get('clips',[])}
    manifest = {'voice_id':old.get('voice_id'), 'language':'zh-CN','selection':old.get('selection','尚未试听选定'),
                'clips':[{**(existing.get(c['id'],{}) if existing.get(c['id'],{}).get('text')==c['text'] else {}),
                          'id':c['id'],'file':c['id']+'.mp3','text':c['text']} for c in chapters]}
    (HERE/'audio/manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    lines = [f'# {TITLE}', '\n制作稿 v1；不是已完成成片。45镜规划网格需配音后重对，原稿中的超长旁白已压缩。',
             '\n## 六章逐字旁白']
    for c in chapters:
        lines += [f'\n### {c["id"]} {c["title"]}',c['text']]
    lines += ['\n## 分镜规划（不是配音后实际切点）','|镜号|计划时间|画面叙事|运镜|','|---|---|---|---|']
    for s in shots:
        lines.append(f'|{s["id"]}|{s["start"]}–{s["start"]+4}秒|{s["purpose"]}|{s["camera"]}|')
    lines += ['\n## 事实边界'] + ['- '+s for s in PRINCIPLES]
    lines += ['\n## 资料'] + [f'- [{s["id"]}]({s["url"]})：{s["usage"]}' for s in SOURCES]
    (HERE/'screenplay.md').write_text('\n'.join(lines)+'\n')
    (HERE/'抖音脚本.md').write_text('\n'.join(lines)+'\n')
    (HERE/'抖音发布文案.md').write_text('# 标题备选\n'+'\n'.join('- '+s for s in TITLES)+'\n\n'+DESCRIPTION+'\n\n'+' '.join(HASHTAGS)+'\n')
    print(f'45镜：{sum(s["kind"]=="agnes" for s in shots)} Agnes + {len(cards)}信息卡；旁白{sum(len(c["text"]) for c in chapters)}字（含标点）')

if __name__ == '__main__':
    build()

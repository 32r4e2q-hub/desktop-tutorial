#!/usr/bin/env python3
"""Build the Teigin project in the same data contract used by production/setagaya2000."""
import json, re, hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
SRC=HERE/'story.json'
NARRATION=[
'一九四八年冬天，东京在战后的寒夜里飘着雪。',
'帝国银行大堂灯火未熄，职员们仍在整理账目。',
'门外，一个自称防疫官的男人递来名片，还自称叫山口二郎。',
'他声称附近发生痢疾疫情，奉命送来预防药，请众人立刻服下。',
'窗外，美军吉普车驶过废墟街道，忙碌的身影映进玻璃。',
'他打开药箱，取出两瓶透明液体，解释要分两次服用。',
'十六名银行职员依次站成一排，每个人面前的桌上，都放着一只小杯。',
'来人先举杯示范，职员们相互观望，最后还是照他说的喝下。',
'整座银行陷入沉静，职员们无声地等着秒针走过一分钟。',
'随后，第二种药水倒入杯中，职员再次服下。',
'几分钟后，大堂传来杯子碎裂声，散落的算盘珠滚进柜台底下。',
'来人趁着混乱取走现金和支票，拎起药箱，从后门匆匆离开。',
'警车与救护车相继赶到，医护人员进入银行，街边围起人群。',
'报社印刷机彻夜轰鸣，帝银案很快登上全国报纸头版。',
'调查人员后来发现，案发前，另外两家银行也遇到过相似的防疫说辞。',
'安田银行的职员当时拒绝服药，那个男人只好转身离开现场。',
'侦查人员循线追查，一张名片，成为确认身份的重要线索。',
'名片属于松井蔚医生；他却称，自己并不认识这个来人。',
'警方沿着名片上的身份继续调查，线索逐渐指向远在北海道。',
'在北海道的小樽，警方最终找到一位画家，他名叫平泽贞通。',
'当时五十七岁的平泽正在画室作画，生活与银行相距遥远。',
'一九四八年八月二十一日，平泽在北海道被警方逮捕。',
'审讯记录留下他的认罪供述；后来，他对这份供述提出异议。',
'到了法庭，平泽翻供，称先前的供述是在压力之下被迫作出的。',
'法槌落下，判决没有平息争议，关于证据的质疑仍在。',
'一九五〇年，东京地方法院一审判处画家平泽贞通死刑。',
'不同目击者对嫌疑人的辨认结果并不一致，案件因此留下诸多疑点。',
'关于731部队涉案，至今仍只是未经证实的传闻。',
'死刑未执行，平泽喊冤近四十年，直到一九八七年病逝狱中——真凶是谁？',
]
SOURCES=[
 {'publisher':'コトバンク（日本大百科全書・世界大百科事典等）','topic':'事件概要、16人が服用し12人死亡、1948年逮捕、1950年一審死刑判決、1987年獄中死','url':'https://kotobank.jp/word/%E5%B8%9D%E9%8A%80%E4%BA%8B%E4%BB%B6-99951'},
 {'publisher':'明治大学平和教育登戸研究所資料館','topic':'帝銀事件と関連未遂事件の目撃証言・再審をめぐる研究記録','url':'https://www.meiji.ac.jp/noborito/event/6t5h7p00003ciwgr-att/reright.pdf'},
 {'publisher':'最高裁判例を引用する帝銀事件第17次再審請求決定書解説','topic':'1948年8月21日逮捕、1950年東京地裁判決、1955年最高裁上告棄却、目撃証言の区分','url':'https://ezaki-law.com/archives/1244'}
]
# Story plan is authored in story.json; this function applies the same shared prompt contract as Setagaya.
def build():
    d=json.loads(SRC.read_text())
    real='【STYLE】'+d['style_prefix'].replace('【STYLE】','').strip()
    neg='【NEGATIVE】'+d['negative_prompt'].replace('【NEGATIVE】','').strip()
    chars=d['characters']
    variant='【STYLE】传闻疑点专用：泛黄纸张上的手绘动画重现，铅笔与水彩笔触，档案式构图，明确是未经证实的传闻想象，不是真实档案或史料；16:9横屏，缓慢连续运动。'
    cuts=[10,35,60,85,110,135,155,172,180]
    titles=['黄金钩子','假防疫员登场','一排十六个杯子','案发与追查','名片线索','画家被捕','口供与翻供','疑点','余音']
    chapters=[]; left=0; sid=0
    for i,end in enumerate(cuts):
        members=[]
        while sid<len(d['shots']) and d['shots'][sid]['start']<end:
            members.append(d['shots'][sid]); sid+=1
        chapters.append({'id':f'N{i+1:02}','title':titles[i],'start':left,'duration':end-left,'shot_ids':[s['id'] for s in members],'text':' '.join(NARRATION[int(s['id'][1:])-1] for s in members)})
        left=end
    shots=[]
    for i,s in enumerate(d['shots']):
        prompt=s['prompt']; body=(prompt.split('【画面】',1)[1].split('【NEGATIVE】',1)[0].strip() if '【画面】' in prompt else prompt.strip())
        start=s['start']; duration=s['duration']; ch=next(c for c in chapters if c['start']<=start<c['start']+c['duration'])
        shots.append({'id':s['id'],'kind':'agnes','start':start,'duration':duration,'narration_id':ch['id'],'narration':NARRATION[i], 'camera':body,'characters':s['characters'],'style_variant':'diagram' if s['id']=='S28' else 'real','prompt':body,'purpose':body[:120],'seed':19480126+i,'seconds':duration,'aspect':'16:9','source_size':'720P','transition_out':'段落间雪花柔化叠化0.3秒；同段硬切。'})
    out={'title':'帝银事件：一杯“预防药”','film_name':'帝银事件_一杯预防药_三分钟_带声音.mp4','target_duration':180,'width':1920,'height':1080,'fps':24,'model':'agnes-video-2.5-flash','source_size':'720P','branch':'arena/ef27a350-desktop-tutorial','style_prefix':real,'style_rumor_prefix':variant,'negative_prompt':neg,'characters':chars,'character_seeds':{'C1':19480126,'C2':19480127,'C3':19480821,'C4':19480128,'C5':19480129},'principles':['先审核定稿参考图，再生成29个Agnes Video 2.5 Flash连续运动视频镜头。','每条提示自动拼接STYLE、人物角色设定与NEGATIVE；传闻疑点镜头使用泛黄手绘STYLE。','不出现遗体、血腥、伤口、中毒倒地或暴力过程，受害过程仅用物件和环境间接表现。','所有人物均为风格化非真实肖像；片内不出现生成文字，字幕标题后期添加。','731部队涉案只作为未经证实的传闻疑点呈现，不作事实断言。'],'chapters':chapters,'shots':shots,'narration_spec':{'voice_id':'voice-01','language':'zh-CN','alignment':'one-independently-generated-voice-clip-and-one-caption-cue-per-shot','max_speedup_factor':1.35,'min_tempo_factor':0.80,'slowdown_allowed':True,'target_spoken_fraction':0.94,'target_characters_per_second':3.7,'final_silence_seconds':1.0,'dramatic_pause_after':{'S09':0.5,'S26':0.5}},'reference_images':[{'file':'reference/C1_false_health_officer.png','description':'风格化假防疫员定稿，非真实肖像'},{'file':'reference/C3_hirasawa_character.png','description':'风格化画家定稿，非真实肖像'},{'file':'reference/L2_bank_hall.png','description':'帝银大堂场景定稿'},{'file':'reference/hero_sixteen_cups.png','description':'十六只杯子的连续性定稿'},{'file':'reference/C2_bank_clerks.png','description':'1948年职员群像定稿'},{'file':'reference/C4_matsui_doctor.png','description':'松井医生定稿，虚构形象'},{'file':'reference/C5_detective.png','description':'警探定稿，虚构形象'},{'file':'reference/L1_bank_exterior.png','description':'帝银雪夜外景定稿'},{'file':'reference/L3_interrogation_room.png','description':'警局审讯室定稿'},{'file':'reference/L4_otaru_artist_studio.png','description':'小樽画室定稿'},{'file':'reference/L5_court_cell.png','description':'法庭与牢房定稿'}],'presentation':{'cover':{'layout':'银行大堂中景，一排十六只杯子横贯画面，末只杯子一点红光，后期标题置上方','text':'十六个杯子','subtext':'一个自称防疫官的男人，让十六个人喝下了同一杯药','style':'金色粗体黑边，所有字后期合成'},'end_title':'帝银事件','end_subtitle':'东京 · 1948 · 至今存疑','end_note':'AI动画情景重现 · 非真实影像','end_question':'真凶是谁？','highlight_keywords':['十六个人','预防药','1948年1月26日','名片','12人死亡','16万日元','一分钟后','平泽贞通','1948年8月21日','认罪','翻供','死刑','疑点','真凶是谁'],'subtitle_style':{'font_size_px':58,'outline_px':3,'safe_bottom_margin_px':72,'alignment':'bottom-center','normal_color':'white','highlight_color':'gold','highlight_scale':1.2},'sound_events':[{'at':0,'name':'低沉大提琴单音渐强、冬夜风与远钟','kind':'music_sfx'},{'at':10,'name':'紧张钢琴点奏、秒针节拍','kind':'music_sfx'},{'at':35,'name':'压抑弦乐渐入，杯子轻碰','kind':'music_sfx'},{'at':60,'name':'声音骤然抽离，微弱钢琴与耳鸣感','kind':'sfx'},{'at':85,'name':'悬疑钢琴与低频脉冲','kind':'music_sfx'},{'at':110,'name':'短促铜管、雪地脚步','kind':'music_sfx'},{'at':135,'name':'压抑弦乐与心跳般低频','kind':'music_sfx'},{'at':155,'name':'冷峻低音弦乐、金属质感点奏','kind':'music_sfx'},{'at':172,'name':'大提琴单音，最后一秒静音','kind':'music_sfx'}]},'sources':SOURCES,'fact_boundary':['1948年1月26日，帝国银行椎名町分行发生事件，16人服药，最终12人死亡。','平泽贞通于1948年8月21日被捕，1950年东京地方法院一审判处死刑，1955年最高法院维持死刑判决；其始终否认，1987年在狱中去世。','关于731部队涉案的说法仅为传闻与疑点，未经证实。'],'fact_boundary_note':'目击证词及争议按来源谨慎表述；未核实的金额不写入旁白；731部队涉案不作为事实断言.'}
    SRC.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    def stamp(sec): return f"{sec//60:02d}:{sec%60:02d}"
    lines=['# 帝银事件：一杯“预防药”','', '三分钟横版｜1920×1080｜24fps｜180秒｜29个Agnes连续动画镜头。旁白逐镜一句，字幕按实际语音活动区间对齐。', '', '## 逐镜旁白与时间码', '', '| 镜头 | 时间 | 秒数 | 中文旁白 |', '|---|---:|---:|---|']
    for shot in shots:
        lines.append(f"| {shot['id']} | {stamp(shot['start'])}–{stamp(shot['start']+shot['duration'])} | {shot['duration']} | {shot['narration']} |")
    lines += ['', '## 制作提示', '', '先检查 `reference/` 定稿图，再逐镜生成连续动态视频。字幕逐句同步，白字黑边，关键词金色放大，底部安全区。BGM压于旁白下约18dB；不展示遗体、血腥或中毒倒地。S28为未经证实的传闻手绘意象；S29片尾标题后期叠加。', '']
    (HERE/'screenplay.md').write_text('\n'.join(lines),encoding='utf-8')
    return out
if __name__=='__main__':
    d=build(); print(f"built {len(d['shots'])} shots / {sum(s['duration'] for s in d['shots'])} seconds")

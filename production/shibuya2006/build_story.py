#!/usr/bin/env python3
"""Episode 17: deterministic plan. No network calls; no approvals manufactured."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent
BRANCH = 'arena/8d7fb4aa-desktop-tutorial'
STYLE = ('【STYLE】电影级写实3D动画情景重现，非真实历史影像；35mm胶片摄影质感，浅景深，长焦压缩，日本社会派家庭悲剧风格，'
         '2006至2009年东京涩谷幡谷，冬日冷白与屋内暖黄对比，低饱和，暗部厚重，真实人体比例、皮肤、布料与建筑材质；'
         '所有人物均为虚构演员式形象，不还原真实肖像。16:9横屏，主体在三分线，底部字幕安全区留空。'
         '必须是真实连续运动的写实3D影像，有人物动作、呼吸、布料或自然环境运动；禁止静态图片加推拉。'
         '一扇门与时钟是贯穿视觉线索；镜头9至14冷青深蓝，19至28冷灰，29至30暖金转黑。')
NEGATIVE = ('【NEGATIVE】卡通,Q版,动漫,夸张表情,过度饱和,文字,水印,字幕,可读文字,伪文字,血腥,伤口,遗体,尸体,'
            '分尸,凶器,刀具,暴力过程,裸露,畸形手指,多余肢体,人物面部崩坏,智能手机,现代电动车,低清晰度,画面闪烁,'
            '风格突变,竖屏构图,黑边,静态图片推拉,法槌,真实人物肖像')
BOUNDS = [(0,10,'父亲送他集训'),(10,35,'精英家庭'),(35,60,'一句话与供述边界'),(60,85,'他选择隐瞒'),
          (85,108,'照常集训'),(108,130,'母亲发现'),(130,150,'另一个人格的主张'),(150,168,'七年与十二年'),(168,180,'一个家')]
HOOK_TEXT = [
 (0,'妹妹遇害第二天，他去了集训'),(8,'一句“你没有梦想”，为何被反复提起？'),
 (55,'那天下午，家里只剩两个人'),(80,'他选择了隐瞒'),(125,'谁先察觉到异味？'),
 (130,'他先否认、后承认，争议却未结束'),(144,'律师提出：“另一个人”？'),
 (156,'七年变十二年：为何差五年？'),(168,'一个家，怎样对待“不成器”的孩子？')]
EXPLAIN_TEXT = [
 (10,17,'时间倒回：2006年12月30日'),(24,30,'升学经历不是施暴的免责理由'),
 (49,55,'争执内容来自被告供述，不代表受害者应担责'),(85,91,'案发次日仍参加集训；不是被发现的日期'),
 (114,120,'1月2日返家；3日晚母亲察觉异常'),(137,144,'争点：不同阶段的刑事责任能力'),
 (144,150,'解离性身份障碍：辩方主张，非既定诊断'),
 (162,168,'二审不采相关鉴定判断，认定两罪成立'),(168,174,'家庭反思不能替代施暴者的个人责任')]

def build():
    data=json.loads((HERE/'plan.json').read_text())
    shots=[]; cursor=0
    for i,(duration,text,visual,refs) in enumerate(zip(data['durations'],data['narrations'],data['visuals'],data['refs']),1):
        roles=[x for x in refs.split('+') if x.startswith('C')]
        chapter=next(f'N{j:02}' for j,(a,b,_) in enumerate(BOUNDS,1) if a<=cursor<b)
        grade=('冷青深蓝' if 9<=i<=14 else '冷灰' if 19<=i<=28 else '黄昏暖金与黑场灯光' if i>=29 else '冬日冷白与暖黄')
        shots.append(dict(id=f'S{i:02}',kind='agnes',start=cursor,duration=duration,seconds=duration,aspect='16:9',source_size='720P',
                          narration_id=chapter,narration=text,prompt=visual+' 全程环境保持微动；源片不生成任何文字。',purpose=visual,
                          characters=roles,seed=20061230+i,camera='连续平稳中景或近景，按动作跟随，不用静帧推拉',
                          sound_design='克制环境声与动作拟音，不配乐，不复原暴力声',color_grade=grade,reference_ids=refs,
                          transition_in='后期短转场，保持时间线',transition_out='环境微动中停顿，不冻帧'))
        cursor+=duration
    assert len(shots)==30 and cursor==180
    approvals=json.loads((HERE/'reference/approvals.json').read_text())
    voice_path=HERE/'audio/voice.json'
    voice=json.loads(voice_path.read_text()) if voice_path.exists() else {}
    story=dict(title='涩谷短大生惨案：一句话的代价',film_name='涩谷短大生惨案_一句话的代价_三分钟_带声音.mp4',
               target_duration=180,width=1920,height=1080,fps=24,model='agnes-video-2.5-flash',source_size='720P',branch=BRANCH,
               style_prefix=STYLE,style_rumor_prefix=STYLE,negative_prompt=NEGATIVE,
               characters={f'C{i:02}':f'【C{i:02}锚点】'+a for i,a in enumerate(data['anchors'],1)},
               character_seeds={f'C{i:02}':20061230+i for i in range(1,len(data['anchors'])+1)},
               narration_spec=dict(voice_id=voice.get('voice_id','pending_voice_selection'),description='悬疑低沉、克制的成熟普通话男声；短句、有停顿、不煽情',
                                   language='zh-CN',target_characters_per_second=3.7,alignment='shot-locked; final alignment requires measured TTS'),
               chapters=[dict(id=f'N{i:02}',title=t,start=a,duration=b-a,text=''.join(s['narration'] for s in shots if a<=s['start']<b)) for i,(a,b,t) in enumerate(BOUNDS,1)],
               shots=shots,reference_images=[dict(id=k,**v) for k,v in approvals['assets'].items() if v['status']=='approved'],
               reference_revision=(HERE/'reference/revision.txt').read_text().strip(),
               reference_designs=dict(characters=[f'C{i:02}' for i in range(1,len(data['anchors'])+1)],scenes=[f'S{i:02}' for i in range(1,14)],props=[f'P{i:02}' for i in range(1,8)]),
               sfx_only=True,fact_check=dict(status='pending_primary_source_verification',sources_file='FACT_CHECK.md'),
               presentation=dict(onscreen_label='AI动画情景重现 · 非真实影像',highlight_phrases=['父亲','集训','梦想','隐瞒','另一个人','七年','十二年','一个家'],
                                 hooks=[dict(id=f'H{i:01}',start=t,end=t+2,text=x) for i,(t,x) in enumerate(HOOK_TEXT,1)],
                                 explainers=[dict(start=a,end=b,text=t) for a,b,t in EXPLAIN_TEXT],
                                 end_title='涩谷短大生惨案',end_subtitle='东京涩谷 · 2006—2009 · 一句话的代价',title_start=174.6,title_end=179.5,
                                 cover_text='第二天',cover_concept='本片生成视频父子背影与住宅暗窗取帧，横版裂缝构图；不可用参考图冒充视频帧',
                                 publish_title='妹妹遇害后的第二天，他仍去集训，父亲开车送他：涩谷短大生惨案',
                                 hashtags=['#真实事件','#涩谷短大生惨案','#日本','#家庭悲剧','#悬疑','#电影感']))
    (HERE/'story.json').write_text(json.dumps(story,ensure_ascii=False,indent=2)+'\n')
    lines=['# 第十七期｜涩谷短大生惨案：一句话的代价','',
           '制作草案；180秒／30镜／1920×1080／24fps／写实3D动画／无BGM。公开来源核查与参考图未签收，禁止开视频生成。','',
           '|镜头|时间|逐镜旁白|画面|参考图|','|---|---|---|---|---|']
    for s in shots:
        lines.append(f"|{s['id']}|{s['start']}–{s['start']+s['duration']}秒|{s['narration']}|{s['purpose']}|{s['reference_ids']}|")
    lines+=['','## 钩子：每条严格2秒','']+[f'- H{i}｜{t}–{t+2}秒｜{x}' for i,(t,x) in enumerate(HOOK_TEXT,1)]
    lines+=['','## 后期与配音边界','- 普通字幕白字黑边，关键词金色；金色解释字幕与钩子复用光州文字层。',
            '- 每镜独立配音，但前后句语义连续；实测TTS后再做逐句同步，不把文字估时当成已对齐。',
            '- “父亲开车送他”“隐瞒”“另一个人”“一个家”前预留0.5秒，须以实测语音窗口复核。',
            '- 片尾标题后期添加；源片全部禁字。不得以静态参考图加推拉替代视频。',
            '- 镜头27是法律对比意象，非庭审实录；镜头25是辩方主张示意，非医学诊断。']
    (HERE/'screenplay.md').write_text('\n'.join(lines)+'\n')
    print(f'WROTE {len(shots)} shots / {cursor}s; narration {sum(len(s["narration"]) for s in shots)} chars')
    return story
if __name__=='__main__': build()

#!/usr/bin/env python3
"""开出一套智谱 CogVideoX-Flash 三分钟横版解说项目。

这是 ``new_topic.py`` 的 CogVideoX 供应商版：先生成干净的 45 镜内容骨架，
再覆盖郑斗英项目已经跑通的 CogVideoX 生成、回填、渲染、听检和全帧 QC 引擎。
新项目不会继承郑斗英的故事内容、配音、镜头素材或检查报告。

示例：
  python3 production/new_cogvideox_topic.py \\
    --slug newcase --title "新案件标题" \\
    --branch arena/f5c619e4-desktop-tutorial
"""
from __future__ import annotations
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REFERENCE=HERE/'jeong2000'
sys.path.insert(0,str(HERE))
import new_topic

COG_ENGINE=(
    'media.py','throttle.py','align_audio.py','build_audio.py','generate.py','fetch_sources.py','watch_run.py',
    'tighten_pauses.py','clause_times.py','qc_shots.py','audit_frame_distortions.py',
    'compose_all_frame_sheets.py','export_visual_review_candidates.py','publish_visual_review_bundle.py',
    'review_app.py','progress_app.py','render.py','script_table.py',
)
WORKFLOWS=('gen','render','verbatim','visual-qc')
GRAPHIC_IDS={'S03','S10','S17','S24','S31','S38','S43'}
CUTS_RE=re.compile(r'^CUTS = \{.*?^\}',re.M|re.S)

def safe_film(title:str)->str:
    return new_topic.film_name(title)

def replacements(slug:str,title:str,branch:str):
    old_title='郑斗英：十个月，九条人命'
    old_film='郑斗英_十个月，九条人命_三分钟_带声音.mp4'
    return (("arena/f5c619e4-desktop-tutorial",branch),(old_film,safe_film(title)),(old_title,title),('郑斗英案',title),('jeong2000',slug))

def patch(text:str,slug:str,title:str,branch:str)->str:
    for old,new in replacements(slug,title,branch):text=text.replace(old,new)
    return text

def cogify_scaffold(dest:Path,slug:str,title:str,branch:str)->None:
    # Blank content skeleton produced by new_topic; only provider vocabulary changes.
    p=dest/'story.json'; story=json.loads(p.read_text())
    story['model']='cogvideox-flash'
    story['_scaffold']['reference']='validated CogVideoX engine (content blank)'
    for shot in story['shots']:
        shot['kind']='graphic' if shot['id'] in GRAPHIC_IDS else 'cogvideo'
        shot['seconds']=6; shot['resolution']='1080p'; shot['frame_rate']=30
    p.write_text(json.dumps(story,ensure_ascii=False,indent=2)+'\n')

    p=dest/'build_story.py'; text=p.read_text()
    text=text.replace('Agnes Video V2.0','CogVideoX-Flash').replace('Agnes 动画','CogVideoX-Flash 动画')
    text=text.replace('Agnes 镜头','CogVideoX 镜头').replace('Agnes','CogVideoX-Flash').replace('agnes','cogvideo')
    text=text.replace('"agnes"','"cogvideo"').replace("'agnes'","'cogvideo'")
    text=text.replace('AGNES_SECONDS','COGVIDEO_SECONDS')
    text=text.replace('kind = "cogvideo"（AI 动画，7 秒 24 fps）','kind = "cogvideo"（智谱 AI 动画，通常约 6 秒）')
    text=text.replace('Stylized 2D animated documentary illustration with hand-painted graphic-novel textures and soft ',
                      'Realistic 3D animated documentary with physically based materials, natural proportions and subtle ')
    text=text.replace('cel shading, TODO world description (places, era, props, weather); horizontal 16:9 cinematic composition, ',
                      'cinematic lighting, TODO world description (places, era, props, weather); horizontal 16:9 cinematic composition, ')
    text=text.replace('3D render look, plastic CGI, ', 'plastic CGI, waxy skin, ')
    text=re.sub(r'COGVIDEO_SECONDS = 7[^\n]*', 'COGVIDEO_SECONDS = 6  # CogVideoX-Flash 返回素材的计划时长', text)
    text=text.replace('"resolution": "1080p", "frame_rate": 24', '"resolution": "1080p", "frame_rate": 30')
    text=text.replace('kind 只能是 agnes / graphic', 'kind 只能是 cogvideo / graphic')
    for sid in GRAPHIC_IDS:
        text=text.replace(f'("{sid}", "cogvideo",', f'("{sid}", "graphic",')
    p.write_text(text)

    p=dest/'screenplay.md'; text=p.read_text().replace('| agnes |','| cogvideo |')
    for sid in GRAPHIC_IDS:
        text=re.sub(rf'(\| {sid} \|) cogvideo (\|)',rf'\1 graphic \2',text)
    p.write_text(text)

    # Keep the generic 45-shot CUTS skeleton, but use the proven CogVideoX renderer.
    old_render=(dest/'render.py').read_text(); m=CUTS_RE.search(old_render)
    if not m:raise RuntimeError('new_topic render template has no CUTS block')
    cuts=m.group(0)
    for name in COG_ENGINE:
        source=REFERENCE/name
        if not source.is_file():raise RuntimeError(f'CogVideoX reference missing {source}')
        text=patch(source.read_text(),slug,title,branch)
        if name=='render.py':
            text,hits=CUTS_RE.subn(cuts,text,count=1)
            if hits!=1:raise RuntimeError('CogVideoX render reference has no CUTS block')
        (dest/name).write_text(text)

    # Existing QA/review helpers copied by new_topic know an old kind name; make them provider-neutral.
    for p in dest.glob('*.py'):
        if p.name in COG_ENGINE or p.name=='build_story.py':continue
        text=p.read_text().replace('"agnes"','"cogvideo"').replace("'agnes'","'cogvideo'")
        text=text.replace('Agnes','CogVideoX-Flash').replace('agnes','cogvideo')
        p.write_text(text)

    # Copy all four proven workflows and rewrite fixed identifiers.
    shutil.rmtree(dest/'workflows');(dest/'workflows').mkdir()
    for suffix in WORKFLOWS:
        src=REFERENCE/'workflows'/f'jeong2000-{suffix}.yml'
        out=dest/'workflows'/f'{slug}-{suffix}.yml'
        out.write_text(patch(src.read_text(),slug,title,branch))

    # Fresh receipts only; no source URLs, task ids, QA evidence or marker triggers are inherited.
    (dest/'results.json').write_text(json.dumps({'project':title,'model':'cogvideox-flash','provider':'Zhipu AI','phase':'scaffold','shots':{}},ensure_ascii=False,indent=2)+'\n')
    for marker in ('GEN_REQUEST','RENDER_REQUEST','VERBATIM_REQUEST','VISUAL_QC_REQUEST','RELEASE_UPLOAD_REQUEST'):
        (dest/marker).unlink(missing_ok=True)
    for generated in ('qa','delivery','cast'):
        shutil.rmtree(dest/generated,ignore_errors=True)

    readme=f'''# {title}\n\n由 `production/new_cogvideox_topic.py` 开出的 CogVideoX-Flash 三分钟横版项目。\n\n- slug：`{slug}`\n- 分支：`{branch}`\n- 成片：`交付/{safe_film(title)}`\n- 计划：45 镜 × 4 秒 = 180 秒；目标比例为 38 个 CogVideoX-Flash 动画镜头 + 7 张后期信息卡。\n- Secret：`ZHIPUAI_API_KEY`；本项目不调用 Agnes。\n\n项目现在故意无法通过 `generate.py --validate`：请先完成 `build_story.py`、六段配音与 SHA-256。\n完整步骤见仓库根目录 `CogVideoX三分钟短片开工手册.md`。\n'''
    (dest/'README.md').write_text(readme)

def scaffold(slug:str,title:str,branch:str,dest:Path|None=None)->Path:
    if not REFERENCE.is_dir():raise SystemExit('缺少已跑通参考项目 production/jeong2000')
    dest=dest or HERE/slug
    created=new_topic.scaffold(slug,title,branch,dest,new_topic.REFERENCE,new_topic.TEMPLATES)
    cogify_scaffold(created,slug,title,branch)
    return created

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--slug',required=True);ap.add_argument('--title',required=True);ap.add_argument('--branch',default='');ap.add_argument('--dest',type=Path)
    args=ap.parse_args(argv)
    if not re.fullmatch(r'[a-z][a-z0-9_]{1,31}',args.slug):raise SystemExit('slug 只能是小写字母、数字、下划线，且以字母开头')
    branch=args.branch or subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()
    if not branch:raise SystemExit('取不到当前分支，请用 --branch 指定')
    dest=scaffold(args.slug,args.title,branch,args.dest)
    shown=dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest
    print(f'已创建 CogVideoX 项目：{shown}')
    print(f'下一步：填写 {dest}/build_story.py，然后按 CogVideoX三分钟短片开工手册.md 执行。')
    return 0
if __name__=='__main__':sys.exit(main())

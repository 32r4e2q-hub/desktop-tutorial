# 装依赖 + 用 edge-tts 重生 6 段解说（免费、不需要任何 key）+ 按实测时长重排切点
import os, subprocess
PIP = ['pillow', 'numpy', 'av', 'pyyaml', 'imageio-ffmpeg', 'pymupdf', 'edge-tts']
for flags in ((), ('--user',), ('--break-system-packages',)):
    if subprocess.run(['python3', '-m', 'pip', 'install', '-q', *flags, *PIP]).returncode == 0:
        break
os.environ['PATH'] = '/content/proj/bin:' + os.environ['PATH']
for step in (['python3', 'production/monalisa/make_voice.py'],
             ['python3', 'production/monalisa/clause_times.py'],
             ['python3', 'production/monalisa/make_cuts.py'],
             ['python3', 'production/monalisa/generate.py', '--validate']):
    print('$', ' '.join(step))
    r = subprocess.run(step, cwd='/content/proj', capture_output=True, text=True)
    print((r.stdout or r.stderr).strip()[-900:])
    if r.returncode:
        raise SystemExit(f"这一步失败：{' '.join(step)} —— 把上面输出发我")
print('配音就位、切点已按实测重排 → 下一格推到你的仓库')

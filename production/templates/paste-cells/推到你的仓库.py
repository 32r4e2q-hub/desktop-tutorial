# 推到 GitHub：推完 Actions 会自己点火（这次 push 自带 GEN_REQUEST 触发文件）
import getpass, os, pathlib, subprocess
MYREPO, BRANCH, PROJ = 'ozzy282576/monalisa-film', 'main', '/content/proj'
os.environ['GIT_TERMINAL_PROMPT'] = '0'

def git(*a):
    r = subprocess.run(('git',) + tuple(a), cwd=PROJ, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"git {' '.join(a)} 失败：\n{(r.stderr or r.stdout).strip()[-500:]}")
    return (r.stdout or '').strip()

if not os.path.isdir(PROJ + '/.git'):
    git('init', '-q', '-b', BRANCH)
git('config', 'user.name', 'monalisa-colab')
git('config', 'user.email', 'arena@local')
# 只把源文件推上去：跑格子会留下 __pycache__ / .cache/字体 / venv，别让它们进你的仓库
pathlib.Path(PROJ + '/.gitignore').write_text('__pycache__/\n*.pyc\n.cache/\n.venv*/\nwork/\n')
git('add', '-A')
git('commit', '-q', '-m', '蒙娜丽莎：行李箱里的779号 —— 配音 + 45 镜计划 + 引擎 + 三份流水线')
try:
    tok = getpass.getpass('fine-grained PAT（只要 Contents: Read and write）: ').strip()
except Exception:
    tok = input('贴 PAT: ').strip()
print(git('-c', 'credential.helper=', 'push',
          f'https://x-access-token:{tok}@github.com/{MYREPO}.git', f'HEAD:{BRANCH}') or 'pushed')
print('去 Actions 页看「Agnes生成」是否在跑；没跑就手点 Run workflow，payload 填 {"workers":2}')

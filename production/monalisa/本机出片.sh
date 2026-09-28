#!/usr/bin/env bash
# 在**自己的电脑**上把这三部片子缺的那一步跑完：Agnes 生成 → 剪辑渲染 → 推回分支。
#
#   为什么需要它：GitHub Actions 那边没 runner 接单（或分钟数用完/账号被标记），
#   而沙箱这边 DNS 直接解析不到 api.agnes.ai —— 只有"能上网 + 有 API key"的机器能生成。
#   你的机器两条都满足。整个脚本不要求 sudo、不动仓库以外的目录。
#
# 用法（在仓库根目录或任意位置都行，脚本自己 cd）：
#   bash production/monalisa/本机出片.sh              # 全流程：生成 + 渲染 + 推回
#   bash production/monalisa/本机出片.sh --dry        # 只体检环境，不联网、不消耗额度
#   bash production/monalisa/本机出片.sh --gen-only   # 只生成素材（渲染留到以后）
#   bash production/monalisa/本机出片.sh --render-only# 素材已在本地，只渲染
#   bash production/monalisa/本机出片.sh --only S07,S12    # 只重做指定镜头（QC 打回时用）
#   bash production/monalisa/本机出片.sh --status          # 只看还剩几镜（不联网、随时可跑）
#
# 中断不要紧：results.json 记着每镜的 task_id 与 SHA-256，重跑本脚本会跳过已完成的镜头。
set -uo pipefail

BRANCH="arena/01a0aa24-desktop-tutorial"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO" || { echo "进不去仓库目录"; exit 1; }
LOG="work/monalisa/本机出片.log"
mkdir -p work/monalisa
exec > >(tee -a "$LOG") 2>&1

MODE="all"; ONLY=""
while [ $# -gt 0 ]; do
  case "$1" in
    --dry) MODE="dry" ;;
    --gen-only) MODE="gen" ;;
    --render-only) MODE="render" ;;
    --only) shift; ONLY="$1" ;;
    --status) python3 production/monalisa/gen_status.py; exit 0 ;;
    *) echo "不认识参数 $1（可用：--dry --gen-only --render-only --status --only S07,S12）"; exit 1 ;;
  esac
  shift
done

# Google Colab 的 /content 会在断线时被清空。这里把「素材 + 收据 + 成片」同步到
# Google Drive，重连后原地续跑，不会白烧已经花掉的额度；本地电脑跑时这段自动跳过。
DRIVE_STATE=""
if [ -d /content/drive/MyDrive ]; then
  DRIVE_STATE="/content/drive/MyDrive/monalisa-出片状态"
  mkdir -p "$DRIVE_STATE/sources" "$DRIVE_STATE/qa"
  [ -f production/monalisa/results.json ] || cp -n "$DRIVE_STATE/results.json" production/monalisa/ 2>/dev/null
  mkdir -p work/monalisa/sources production/monalisa/qa
  cp -u "$DRIVE_STATE"/sources/*.mp4 work/monalisa/sources/ 2>/dev/null
  cp -u "$DRIVE_STATE"/qa/* production/monalisa/qa/ 2>/dev/null
  sync_state() {
    cp -f production/monalisa/results.json "$DRIVE_STATE/" 2>/dev/null
    cp -fu work/monalisa/sources/*.mp4 "$DRIVE_STATE/sources/" 2>/dev/null
    cp -fu production/monalisa/qa/* "$DRIVE_STATE/qa/" 2>/dev/null
    cp -fu 交付/*.mp4 "$DRIVE_STATE/" 2>/dev/null
    echo "（状态已同步到 Google Drive/monalisa-出片状态，断线不丢）"
  }
  trap sync_state EXIT
  echo "检测到 Colab：已启用 Google Drive 状态同步"
fi

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
die() { printf '\n\033[31m✗ %s\033[0m\n' "$*"; exit 1; }

say "0/5 体检环境（$REPO）"
NOGIT=0
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  # 搬家包（无 .git）也能跑：素材与成片都留在本地，渲染直接调 render.py
  NOGIT=1
  echo "没有 git 仓库：进入离线模式（不 commit、不 push，成片留在 work/ 下自取）"
fi

# 分支必须对齐，否则渲染那一步会把成片 commit 到别处
if [ "$MODE" != "dry" ] && [ "$NOGIT" = "0" ]; then
  git fetch origin "$BRANCH" >/dev/null 2>&1 || die "拉不动分支（网络或仓库权限）：origin/$BRANCH"
  CUR="$(git rev-parse --abbrev-ref HEAD)"
  if [ "$CUR" != "${BRANCH##*/}" ] && [ "$CUR" != "$BRANCH" ]; then
    git checkout -B "$BRANCH" "origin/$BRANCH" >/dev/null || die "切到 $BRANCH 失败，手动执行：git checkout -B $BRANCH origin/$BRANCH"
    echo "已从 $CUR 切到 $BRANCH"
  fi
fi

PY=python3
command -v python3 >/dev/null || die "没有 python3。Ubuntu/WSL 里执行：sudo apt install -y python3 python3-pip"

# Python 依赖：pip 三种装法挨个试，最后再退到 venv（都不需要 sudo）
DEPS=(pillow numpy av pyyaml imageio-ffmpeg pymupdf)
$PY -c 'import PIL, numpy, av, yaml' >/dev/null 2>&1 || {
  say "1/5 装 Python 依赖（约 1-2 分钟）"
  for flags in "--user" "--break-system-packages" ""; do
    if $PY -m pip install -q $flags "${DEPS[@]}" >/dev/null 2>&1; then break; fi
  done
  if ! $PY -c 'import PIL, numpy, av, yaml' >/dev/null 2>&1; then
    if $PY -m venv .venv-monalisa >/dev/null 2>&1 && . .venv-monalisa/bin/activate && PY=python3 \
       && pip install -q "${DEPS[@]}" >/dev/null 2>&1; then
      echo "已改用 .venv-monalisa 这个独立环境"
    fi
  fi
  $PY -c 'import PIL, numpy, av, yaml' >/dev/null 2>&1 \
    || die "依赖装不上。把这行敲进去，把报错最后 10 行发我：
  python3 -m pip install --break-system-packages pillow numpy av pyyaml imageio-ffmpeg pymupdf"
}
echo "Python 依赖 OK（$($PY -V 2>&1)）"

# ffmpeg：优先用系统的，没有就用 imageio-ffmpeg 自带的静态二进制软链到 ./bin
mkdir -p bin
if ! command -v ffmpeg >/dev/null 2>&1; then
  FF="$($PY -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())' 2>/dev/null)"
  [ -n "$FF" ] && ln -sf "$FF" bin/ffmpeg
  export PATH="$PWD/bin:$PATH"
fi
command -v ffmpeg >/dev/null 2>&1 || die "没有 ffmpeg。二选一：
  sudo apt install -y ffmpeg        （推荐）
  或 python3 -m pip install --break-system-packages imageio-ffmpeg"
echo "ffmpeg OK（$(ffmpeg -version 2>&1 | head -1 | cut -c1-46)）"

# 中文字体：字幕必须有 Noto CJK，否则 render.py 会拒绝渲染豆腐块
FONT_OK=$($PY - <<'PY'
from pathlib import Path
import sys
cands=[Path('.cache/fonts/NotoSansCJKsc-Regular.otf'),
       Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')]
print('yes' if any(c.exists() for c in cands) else 'no')
PY
)
if [ "$FONT_OK" != "yes" ]; then
  say "中文字体（字幕要用，约 5 秒）"
  $PY - <<'PY' || die "字体准备失败：手动执行 sudo apt install -y fonts-noto-cjk"
from pathlib import Path
import pymupdf
d = Path('.cache/fonts'); d.mkdir(parents=True, exist_ok=True)
for name in ('NotoSansCJKsc-Regular.otf', 'NotoSerifCJKsc-Regular.otf'):
    p = d / name
    if not p.exists():
        p.write_bytes(pymupdf.Font('china-s').buffer)
        print('写入', p, p.stat().st_size // 1024, 'KB')
PY
fi
echo "字体 OK"

if [ "$MODE" = "dry" ]; then
  say "体检通过 ✓ 这台机器可以出片。正式跑请去掉 --dry"
  exit 0
fi

# 渲染与推回都要用 git 身份，先在本地设好（不碰全局配置）
[ "$NOGIT" = "1" ] || git config user.name  >/dev/null 2>&1 || git config user.name  "arena-local"
git config user.email >/dev/null 2>&1 || git config user.email "arena@local"

if [ "$MODE" = "all" ] || [ "$MODE" = "gen" ]; then
  if [ -z "${AGNES_API_KEY:-}" ]; then
    say "需要 Agnes API key"
    echo "（在 <https://platform.agnes.ai> 或你当初拿到 key 的地方复制；输入不回显，也不会写进文件）"
    if [ ! -t 0 ]; then
      die "这里不是交互终端（Colab 就是这样，读不到你敲的 key）。请在前一个 python 格子里执行：
  import os
  os.environ['AGNES_API_KEY'] = 'sk-……'
然后重跑本格。key 只活在这个运行时环境里，不写进任何文件、不进 git。"
    fi
    read -rsp "AGNES_API_KEY= " AGNES_API_KEY; export AGNES_API_KEY; echo
    [ -n "$AGNES_API_KEY" ] || die "没输 key，退出。也可以先 export AGNES_API_KEY=... 再跑本脚本。"
  fi
  say "2/5 生成 38 个 Agnes 镜头（限速 1 次/75 秒，光排队 ≈48 分钟，别关终端）"
  PAYLOAD='{"workers":2}'
  [ -n "$ONLY" ] && PAYLOAD="{\"workers\":1,\"only\":\"$ONLY\"}"
  echo "payload = $PAYLOAD   （中断后重跑本脚本会按 results.json 续跑，已完成镜头不重复消耗额度）"
  $PY -u production/monalisa/generate.py --payload "$PAYLOAD" || die "生成阶段报错。把上面最后 20 行发我，我按镜头号定点重做。"
  # 生成产物落在 work/monalisa/sources，run_project 的取素材步骤看 work/monalisa/clips：
  # 先按同名拷过去，让它命中 SHA-256 校验直接复用，不再从 CDN 下一遍。
  mkdir -p work/monalisa/clips
  cp -n work/monalisa/sources/*.mp4 work/monalisa/clips/ 2>/dev/null || true
  [ "$MODE" = "gen" ] && { say "只生成模式：素材与 results.json 已就位（work/monalisa/sources、production/monalisa/results.json）"; exit 0; }
fi

if [ "$MODE" = "all" ] || [ "$MODE" = "render" ]; then
  say "3/5 剪辑 + 混音 + 成品复测（闸门二、三）+ 4/5 把成片推回分支"
  BRANCH="$BRANCH" $PY -c "import json;d=json.load(open('production/monalisa/results.json'));print('已登记的镜头数：',len(d.get('shots',{})))" 2>/dev/null || true
  if [ "$NOGIT" = "1" ]; then
    export PATH="$PWD/bin:$PATH"
    $PY -u production/monalisa/render.py \
      --sources work/monalisa/sources --work work/monalisa \
      --output "work/monalisa/蒙娜丽莎_行李箱里的779号_三分钟_带声音.mp4" \
      --results production/monalisa/results.json --skip-asr \
      || die "渲染失败：把最后 20 行报错发我。"
    FILM="work/monalisa/蒙娜丽莎_行李箱里的779号_三分钟_带声音.mp4"
    $PY production/review_film.py --film "$FILM" --project production/monalisa --work work/monalisa/review || true
    echo "成片在 $FILM（Colab 里从左侧「文件」面板下载即可）"
  else
    BRANCH="$BRANCH" bash production/run_project.sh monalisa true || die "渲染或推回失败。成片可能已经生成在 work/monalisa/ 下，把报错最后 20 行发我。"
  fi
fi

say "5/5 跑完了：请回来说一句「本机跑完了」"
cat <<'EOM'
我会立刻在这边接着做：逐格看 38 张 QA 表（人脸/伪文字/中途换场/画幅）、
比对成片与字幕、必要时打回个别镜头，然后写发布包。
产物位置：
  成片          交付/蒙娜丽莎_行李箱里的779号_三分钟_带声音.mp4
  QA 逐镜表     production/monalisa/qa/Sxx.jpg
  生成收据      production/monalisa/results.json
  实测报告      production/monalisa/delivery/
EOM

#!/usr/bin/env bash
# 一键安装 FaceFusion 到本目录（虚拟环境 + 自动选择 CUDA / CPU 版）
# 用法：bash install_facefusion.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FF_DIR="${FF_DIR:-$HERE/facefusion}"
VENV_DIR="${VENV_DIR:-$HERE/.venv}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

say() { printf '\033[1;36m[换脸工具包]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[错误]\033[0m %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null 2>&1 || die "没装 git。先装 git 再来。"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "找不到 $PYTHON_BIN，请装 Python 3.10–3.12。"

PY_VER="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
say "Python 版本：$PY_VER"
case "$PY_VER" in
  3.10|3.11|3.12) ;;
  *) die "FaceFusion 需要 Python 3.10 / 3.11 / 3.12，当前是 $PY_VER。
  建议：conda create -n facefusion python=3.12 && conda activate facefusion
  然后 PYTHON_BIN=\$(which python) bash install_facefusion.sh" ;;
esac

# ---------- 1. 拉源码 ----------
if [ -d "$FF_DIR/.git" ]; then
  say "已存在 $FF_DIR，更新到最新版…"
  git -C "$FF_DIR" pull --ff-only || say "更新失败，继续用当前版本。"
else
  say "克隆 FaceFusion…"
  git clone --depth 1 https://github.com/facefusion/facefusion.git "$FF_DIR"
fi

# ---------- 2. 虚拟环境 ----------
if [ ! -x "$VENV_DIR/bin/python" ]; then
  say "创建虚拟环境 $VENV_DIR…"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip >/dev/null

# ---------- 3. 选加速后端 ----------
PROFILE="default"          # default = CPU / macOS CoreML
LABEL="CPU（慢，但能跑）"

if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
  PROFILE="cuda@12"
  LABEL="CUDA 12（NVIDIA 显卡加速）"
elif [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
  LABEL="CoreML（Apple 芯片加速）"
fi

say "安装后端：$LABEL —— 这一步要下几 GB，慢是正常的。"
cd "$FF_DIR"
python install.py "$PROFILE"

# ---------- 4. 预热模型 ----------
say "预下载模型（约 1–2 GB，可跳过）…"
python facefusion.py force-download || say "模型下载没完成，首次运行时还会再下。"

say "完成。接下来："
cat <<EOF

  cd $HERE
  bash swap_face.sh 你的照片.jpg 参考视频.mp4 输出_换脸.mp4

  想用图形界面的：
  cd $FF_DIR && source $VENV_DIR/bin/activate && python facefusion.py run --open-browser
  然后浏览器打开 http://127.0.0.1:7860

  视频项目目录：$FF_DIR
  Python 环境：$VENV_DIR
EOF

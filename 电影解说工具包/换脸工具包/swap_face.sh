#!/usr/bin/env bash
# 一条命令换脸：照片 + 视频 → 换好脸的视频（原片动作/口型/音轨不动）
#
# 用法：
#   bash swap_face.sh <照片> <视频> <输出>
#
# 可调（环境变量）：
#   PIXEL_BOOST=1024x1024   人脸处理分辨率，默认 512x512
#   ALL_FACES=1             换画面里所有脸（默认只换选中的那张）
#   ONE_FACE=1              强制单人模式（画面里只有一个人才用）
#   PROVIDER=cpu|cuda       推理后端，默认自动判断
#   QUALITY=95              输出画质 0–100，默认 90
#   SWAP_MODEL=inswapper_128  换脸模型，默认 hyperswap_1a_256
#   EXTRA="--xxx yyy"       追加任意 FaceFusion 原生参数
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FF_DIR="${FF_DIR:-$HERE/facefusion}"
VENV_DIR="${VENV_DIR:-$HERE/.venv}"

say() { printf '\033[1;36m[换脸]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[错误]\033[0m %s\n' "$*" >&2; exit 1; }

[ $# -ge 3 ] || die "用法：bash swap_face.sh <照片> <视频> <输出.mp4>"
PHOTO="$1"; VIDEO="$2"; OUTPUT="$3"
[ -f "$PHOTO" ] || die "找不到照片：$PHOTO"
[ -f "$VIDEO" ] || die "找不到视频：$VIDEO"

[ -x "$VENV_DIR/bin/python" ] || die "还没装环境，先跑：bash install_facefusion.sh"
[ -f "$FF_DIR/facefusion.py" ] || die "找不到 $FF_DIR/facefusion.py，重跑 install_facefusion.sh"

# ---------- 后端 ----------
if [ -z "${PROVIDER:-}" ]; then
  if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi -L >/dev/null 2>&1; then
    PROVIDER="cuda"
  elif [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" = "arm64" ]; then
    PROVIDER="coreml"
  else
    PROVIDER="cpu"
  fi
fi

# ---------- 选脸模式 ----------
if [ "${ALL_FACES:-0}" = "1" ]; then
  SELECTOR=(--face-selector-mode many)
elif [ "${ONE_FACE:-0}" = "1" ]; then
  SELECTOR=(--face-selector-mode one)
else
  SELECTOR=(--face-selector-mode reference --reference-face-position 0)
fi

ARGS=(
  headless-run
  --processors face_swapper face_enhancer
  -s "$PHOTO"
  -t "$VIDEO"
  -o "$OUTPUT"
  --execution-providers "$PROVIDER"
  --face-swapper-model "${SWAP_MODEL:-hyperswap_1a_256}"
  --face-swapper-pixel-boost "${PIXEL_BOOST:-512x512}"
  --face-enhancer-model "${ENHANCER_MODEL:-gfpgan_1.4}"
  --face-enhancer-blend "${ENHANCER_BLEND:-80}"
  --face-mask-types box occlusion
  --output-video-encoder "${VIDEO_ENCODER:-libx264}"
  --output-video-quality "${QUALITY:-90}"
  "${SELECTOR[@]}"
)

if [ -n "${EXTRA:-}" ]; then
  # shellcheck disable=SC2206
  ARGS+=($EXTRA)
fi

say "照片：$PHOTO"
say "视频：$VIDEO"
say "后端：$PROVIDER ｜ 模型：${SWAP_MODEL:-hyperswap_1a_256} ｜ 分辨率：${PIXEL_BOOST:-512x512}"
say "输出：$OUTPUT"
say "开始。CPU 跑长视频会很慢，Ctrl+C 可以中断。"

mkdir -p "$(dirname "$OUTPUT")"
cd "$FF_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python facefusion.py "${ARGS[@]}"

say "完成：$OUTPUT"

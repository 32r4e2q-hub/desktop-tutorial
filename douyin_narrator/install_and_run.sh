#!/bin/bash
# ============================================================
# 《阴曹使者》抖音解说视频 一键安装 & 运行脚本
# 适用：macOS / Linux（Windows 请用 WSL 或 Git Bash）
# ============================================================

set -e

echo "=============================="
echo " 环境检查 & 安装依赖"
echo "=============================="

# 检查 Python
python3 --version || { echo "❌ 请先安装 Python 3.8+"; exit 1; }

# 安装 Python 依赖
pip3 install -q \
    edge-tts \
    "scenedetect[opencv]" \
    openai-whisper \
    pysrt \
    pillow \
    numpy \
    tqdm \
    imageio-ffmpeg

echo "✅ 依赖安装完成"

# 检查 ffmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  系统未找到 ffmpeg，将使用 imageio-ffmpeg 内置版本"
fi

echo ""
echo "=============================="
echo " 开始生成解说视频"
echo "=============================="
echo ""
echo "📁 请确认以下文件存在："
echo "   - 原版电影.mp4    （重命名为 movie.mp4）"
echo "   - 抖音解说.mp4    （重命名为 ref.mp4）"
echo "   - script_template.txt （可按需修改）"
echo ""

# 方案A：使用手动编写的 script_template.txt（推荐，效果最好）
python3 make_douyin_video.py \
    --movie  movie.mp4 \
    --script script_template.txt \
    --output 成品_阴曹使者解说.mp4 \
    --voice  zh-CN-YunxiNeural \
    --rate   "+8%" \
    --width  1280 \
    --height 720 \
    --fps    30.0

# 方案B：从抖音解说视频自动提取文案（Whisper识别，效果依赖音质）
# python3 make_douyin_video.py \
#     --movie  movie.mp4 \
#     --ref    ref.mp4 \
#     --output 成品_阴曹使者解说.mp4 \
#     --voice  zh-CN-YunxiNeural \
#     --rate   "+8%"

echo ""
echo "🎬 完成！请查看 成品_阴曹使者解说.mp4"

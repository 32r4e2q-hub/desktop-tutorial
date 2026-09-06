# 《1518 · 没有音乐的舞蹈》— 斯特拉斯堡跳舞瘟疫 · 2.5D 程序化动画纪录短片

约 2 分 50 秒、1280×720@24fps、2.39:1 遮幅、中文旁白 + 内嵌字幕。
**不是图片轮播**：每一帧都由自研的程序化 2.5D 动画引擎实时计算 —
FK 骨骼角色（行走 / 抽搐舞蹈 / 倒地 / 跪拜 / 颤抖等动作循环）、3D 针孔摄像机（推拉 / 横移 / 升降 / 手持抖动）、
透视地面与多层视差场景、粒子特效（雨 / 雪 / 烟 / 火星 / 尘埃 / 雾 / 火焰 / 丁达尔光）、电影级后期（调色 / 泛光 / 暗角 / 胶片颗粒）。

## 目录
```
script/screenplay.md      主题 · 完整旁白稿 · 12 镜分镜表 · 技术方案
engine/                   动画引擎（common / fx / characters / world / text / scenes_a / scenes_b / timeline / render / audio / mix / check）
audio/vo/N01..N10.mp3     旁白配音
assets/fonts/             Noto CJK 字体（字幕 / 字卡）
make_film.py              一键流水线 CLI
output/                   成片 + QC 报告（git 忽略）
```

## 复现
```bash
python3 -m venv ~/.venv-anim && ~/.venv-anim/bin/pip install numpy pillow opencv-python-headless scipy imageio-ffmpeg
cd dancing_plague
# 字体（未入库，约 35 MB）：从 mplfonts 轮子里取 NotoSansCJKsc-Regular.otf / NotoSerifCJKsc-Regular.otf 放到 assets/fonts/
#   pip download mplfonts --no-deps -d /tmp/fontpkg && cd /tmp/fontpkg && unzip -o mplfonts*.whl 'mplfonts/fonts/*' && cp mplfonts/fonts/Noto*CJKsc-Regular.otf <repo>/dancing_plague/assets/fonts/
~/.venv-anim/bin/python make_film.py plan                      # 时间线（镜头 = 旁白长度 + 前后留白）
~/.venv-anim/bin/python make_film.py preview 6 26 55 84 137    # 任意时间点 QA 静帧 → build/preview
~/.venv-anim/bin/python make_film.py render --workers 2        # 分段并行渲染 + 合成音轨 + 封装 + 自动 QC
~/.venv-anim/bin/python make_film.py check                     # 单独跑 QC → output/qc_report.json
```
2 核 CPU 约 10 分钟渲染完成。`--reuse` 可复用已渲染完成的分段。

## 自动 QC 项
容器/流参数（h264 1280×720 24fps yuv420p + AAC 48k 立体声）、全片解码无错、帧数、黑场 / 冻结帧检测、
A/V 时长一致、旁白起点与时间线对齐（≤0.35 s）、音频峰值 / 响度 / 无意外静音。

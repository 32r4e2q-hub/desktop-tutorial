# 1518 · 没有音乐的舞蹈 —— 斯特拉斯堡跳舞瘟疫（程序化 2.5D 动画纪录短片）

约 2 分 50 秒、1280×720@24fps、2.39:1 遮幅、中文旁白 + 字幕、立体声混音。
**全部帧均为逐帧程序化动画**（骨骼角色、3D 针孔相机推拉摇移、粒子特效、光影变化），不是静态图片轮播。

## 复现
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install numpy pillow opencv-python-headless scipy imageio-ffmpeg
# 字体：把 NotoSansCJKsc-Regular.otf / NotoSerifCJKsc-Regular.otf 放到 assets/fonts/
python make_film.py plan                 # 时间线（按旁白时长自动排片）
python make_film.py preview 6 26 55 84   # 任意时间点的 QA 静帧 → build/preview/
python make_film.py render --workers 2   # 全片渲染 + 混音 + 封装 + QC → output/
python make_film.py check                # 只跑 QC（qc_report.json）
```

## 结构
- `script/screenplay.md` —— 主题、旁白稿（N01–N10）、12 个镜头的分镜设计
- `engine/common.py` —— 相机 / 图层 / 透视地面 / 缓动 / 噪声 / 调色 / 辉光
- `engine/characters.py` —— FK 骨骼角色：行走、抽搐舞蹈（4 种）、倒地、跪拜、颤抖、卧病；正面特写
- `engine/world.py` —— 半木结构房屋、教堂、山脉、松林、月亮等程序纹理与图层
- `engine/fx.py` —— 雨 / 雪 / 烟 / 火星 / 尘埃 / 雾 / 火焰 / 火把 / 鸟群 / 云
- `engine/scenes_a.py`, `engine/scenes_b.py` —— 12 个镜头（S1–S12）的场景与运镜
- `engine/timeline.py` —— 依据旁白音频长度生成时间线
- `engine/render.py` —— 逐帧合成（叠化、字幕、字幕条、后期）→ ffmpeg 分段编码
- `engine/audio.py`, `engine/mix.py` —— numpy 合成的环境声 / 音效 / 配乐 + 旁白闪避混音
- `engine/check.py` —— QC：解码完整性、黑场 / 冻结帧检测、音画时长、旁白互相关对齐、响度
- `audio/vo/N01–N10.mp3` —— 旁白配音

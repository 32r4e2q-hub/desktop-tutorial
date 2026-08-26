# 《阴曹使者》抖音解说视频制作工具

> 完整自动化流程：PySceneDetect → Whisper → Edge-TTS 云希声 → 音频反驱动剪辑 → 逐句字幕 → 720p MP4

---

## 📦 文件说明

| 文件 | 用途 |
|------|------|
| `make_douyin_video.py` | 主程序（完整流程） |
| `script_template.txt` | 《阴曹使者》解说文案模板（可直接使用或修改） |
| `install_and_run.sh` | 一键安装依赖 + 运行（macOS/Linux） |
| `README.md` | 本说明文档 |

---

## 🚀 快速开始

### 第一步：安装依赖

```bash
pip install edge-tts "scenedetect[opencv]" openai-whisper pysrt pillow numpy tqdm imageio-ffmpeg
```

> ffmpeg 会由 `imageio-ffmpeg` 自动提供，无需手动安装。  
> 如果系统已有 ffmpeg，优先使用系统版本。

### 第二步：准备文件

把两个视频放到脚本同目录：
- `movie.mp4` — 原版电影《阴曹使者》
- `ref.mp4` — 抖音解说参考视频（可选）

### 第三步：运行

**方案 A（推荐）：使用提供的解说文案**
```bash
python make_douyin_video.py \
    --movie  movie.mp4 \
    --script script_template.txt \
    --output 成品_阴曹使者解说.mp4
```

**方案 B：从抖音解说视频自动识别文案（需要 Whisper）**
```bash
python make_douyin_video.py \
    --movie  movie.mp4 \
    --ref    ref.mp4 \
    --output 成品_阴曹使者解说.mp4
```

---

## ⚙️ 完整参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--movie` | 必填 | 原版电影路径 |
| `--ref` | 可选 | 抖音解说参考视频（自动提取文案） |
| `--script` | 可选 | 手动文案 TXT（每行一句，# 注释） |
| `--output` | `成品解说.mp4` | 输出路径 |
| `--voice` | `zh-CN-YunxiNeural` | TTS 声音（云希） |
| `--rate` | `+8%` | 语速（-50%~+100%） |
| `--width` | `1280` | 输出宽度（720p） |
| `--height` | `720` | 输出高度 |
| `--fps` | `30.0` | 帧率 |
| `--threshold` | `27.0` | 镜头检测灵敏度（越小越敏感） |
| `--work-dir` | `work_tmp` | 临时文件目录 |

---

## 🔄 制作流程详解

```
原版电影.mp4
    │
    ├── [Step 1] PySceneDetect 检测镜头切点
    │       ↓ scenes = [(0.0, 3.2), (3.2, 8.5), ...]
    │
    ├── [Step 2] Whisper 转录原片台词（辅助参考）
    │       ↓ subtitles = [{start, end, text}, ...]
    │
解说文案.txt ──→ [Step 3] 加载/提取解说文案（90-120句）
    │
    ├── [Step 4] Edge-TTS zh-CN-YunxiNeural 逐句生成音频
    │       ↓ tts_results = [(text, mp3_path, duration), ...]
    │
    ├── [Step 5] 构建 EDL 剪辑单
    │       每句 TTS 时长 → 从原片取等长画面
    │       ↓ edl = [{movie_start, movie_end, text, audio}, ...]
    │
    ├── [Step 6] 逐段处理
    │       ├── ffmpeg 裁切原片片段 → 720p
    │       ├── ffmpeg 遮盖原字幕（底部15%黑色遮罩）
    │       ├── ffmpeg drawtext 渲染新字幕（白字黑描边）
    │       └── ffmpeg 合并画面 + TTS 音频
    │
    ├── [Step 7] concat 拼接所有片段
    │
    └── [Step 8] 质检报告
            ↓
        成品_阴曹使者解说.mp4 (720p, ~10min)
```

---

## 📝 自定义解说文案

编辑 `script_template.txt`，每行一句话（# 开头为注释）：

```text
# 这是注释，不会被读出
一个阴间差役，奉命来到人间抓捕一个逃魂。
没想到，这才是噩梦的开始。
今天我们来聊聊《阴曹使者》。
```

**建议：**
- 每句 15-40 字，对应约 2-5 秒音频
- 总句数 100-150 句，对应约 10 分钟
- 句子结尾加标点（。！？）有助于 TTS 断句自然

---

## ❓ 常见问题

**Q: 字幕显示乱码/方块？**  
A: 缺少中文字体。Linux 安装：`sudo apt install fonts-noto-cjk`；macOS 自带。

**Q: Whisper 模型下载很慢？**  
A: 可以手动指定模型大小：代码中 `whisper.load_model("base")` 改为 `"small"` 或 `"medium"`。

**Q: 生成视频比预期短/长？**  
A: 检查 `script_template.txt` 的句子数量。每句约 3-5 秒，100 句 ≈ 8-10 分钟。

**Q: TTS 语速太快/慢？**  
A: 调整 `--rate` 参数：`+20%` 更快，`-10%` 更慢。

---

## 🎵 可选 TTS 声音

| 声音 ID | 特点 |
|---------|------|
| `zh-CN-YunxiNeural` | 云希（男声，活泼，适合解说）★ 推荐 |
| `zh-CN-YunyangNeural` | 云扬（男声，新闻腔，稳重） |
| `zh-CN-XiaoxiaoNeural` | 晓晓（女声，温柔） |
| `zh-CN-XiaohanNeural` | 晓涵（女声，情感丰富） |

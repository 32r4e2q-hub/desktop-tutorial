# 换脸工具包（一张照片 → 视频里的人换成你）

给一条视频 + 一张照片，**原片一帧不动**，只把画面里的人脸换成照片里的人：动作、口型、剪辑、字幕、背景全保留。

适用：把别人的爆款口播视频「换成我出镜」；同一套动作批量出一批账号；给已有素材换演员。

> ⚠️ 只换**你本人**的脸，或已拿到书面授权的人。参考视频要有使用权；发布时按平台要求标注 AI 生成。
> 冒充他人、伪造名人、用于诈骗或误导性带货，在国内平台是直接封号 + 可能担责的。

---

## 一、先选路线

| 路线 | 适合 | 硬件 | 花钱 | 像不像 |
|---|---|---|---|---|
| **A1. FaceFusion 本地**（本工具包） | 要批量、要反复调、素材不外流 | NVIDIA 显卡最好；Apple 芯片可用；纯 CPU 能跑但慢 | **￥0**（开源） | ★★★★☆ |
| **A2. 云端 GPU 租用** | 没显卡，只想跑一两条 | 无 | 约 ￥2–8/小时 | ★★★★☆ |
| **A3. 在线换脸产品**（Viggle / 即梦 / 可灵等） | 完全不想碰命令行 | 无 | 按条/按积分 | ★★★☆☆（不可控） |
| **B. Hypit 重演式** | 要「用我的形象拍一条同款」而不是换脸 | 无（走 API） | 约 $1.1/条 + Agent | 生成的脸，非精确复制 |

本工具包做的是 **A1**：本地、免费、可批量、可复现。

**耗时量级**（1080p，hyperswap + GFPGAN 增强，仅供参考）：

| 硬件 | 1 分钟视频 |
|---|---|
| RTX 3060 12G | 8–15 分钟 |
| RTX 4090 | 3–6 分钟 |
| Apple M 系列（CoreML） | 20–40 分钟 |
| 纯 CPU（8 核） | 1–3 小时（建议先跑 5 秒试片） |

---

## 二、三步跑通

```bash
cd 电影解说工具包/换脸工具包

# ① 预检：照片行不行、视频里有几张脸（先跑这个，省得白等）
python3 precheck.py --photo 我.jpg --video 参考视频.mp4

# ② 装 FaceFusion（一次性，约 3–8 GB 依赖 + 模型）
bash install_facefusion.sh

# ③ 换脸
bash swap_face.sh 我.jpg 参考视频.mp4 输出_换脸.mp4
```

想要图形界面（拖拽、实时预览、逐帧调）：

```bash
cd facefusion && source ../.venv/bin/activate && python facefusion.py run --open-browser
```

浏览器打开 `http://127.0.0.1:7860`，左边 Source 放照片、右边 Target 放视频，Processors 勾 `face_swapper` + `face_enhancer`，Start。

---

## 三、照片怎么给（决定 80% 的效果）

| 要 | 不要 |
|---|---|
| 正脸、双眼睁开、无遮挡 | 墨镜、口罩、手挡脸、侧脸 45° 以上 |
| 光线均匀，脸上没有硬阴影 | 逆光、闪光灯油光、重滤镜/美颜磨皮 |
| 长边 ≥ 1024 px，脸占画面 1/3 以上 | 全身远景截图、微信压缩过的小图 |
| 中性表情、嘴巴闭合 | 大笑露牙、夸张表情（会被带到每一帧） |
| 和视频里人物**性别/年龄/脸型接近** | 差太多（会像戴面具） |

有 3–5 张不同角度/光线的更好：FaceFusion 一次只能用一张，但可以先用它生成多角度参考，再挑最像的。

---

## 四、调参：从「能用」到「看不出」

`swap_face.sh` 已经给了一套稳的默认值，需要时用环境变量覆盖：

```bash
# 高清一点（慢 2–3 倍，4K/特写素材才需要）
PIXEL_BOOST=1024x1024 bash swap_face.sh 我.jpg 参考.mp4 out.mp4

# 多人视频：换所有人
ALL_FACES=1 bash swap_face.sh 我.jpg 参考.mp4 out.mp4

# 只想换画面里左边那个 / 某个人
EXTRA="--face-selector-mode reference --reference-face-position 0 --reference-frame-number 120" \
  bash swap_face.sh 我.jpg 参考.mp4 out.mp4

# 换完脸发糊、五官糊成一团 → 开增强器（默认已开），或换模型
EXTRA="--processors face_swapper face_enhancer --face-enhancer-model codeformer --face-enhancer-blend 60" \
  bash swap_face.sh 我.jpg 参考.mp4 out.mp4

# 换完「不像我」→ 降低融合权重，让原片表情保留更多
EXTRA="--face-swapper-weight 0.8" bash swap_face.sh 我.jpg 参考.mp4 out.mp4
```

关键参数速查：

| 参数 | 默认 | 什么时候改 |
|---|---|---|
| `--face-swapper-model` | `hyperswap_1a_256` | 想要最稳的老牌效果可试 `inswapper_128`（见下方许可证说明） |
| `--face-swapper-pixel-boost` | `512x512` | 特写/4K 提到 `768x768`/`1024x1024`；慢机器降到 `256x256` |
| `--face-enhancer-model` | `gfpgan_1.4` | `codeformer` 更「还原」，`gpen_bfr_512` 更锐 |
| `--face-enhancer-blend` | `80` | 太高会「塑料脸」，60–80 之间调 |
| `--face-selector-mode` | `reference` | 单人用 `one`；多人全换用 `many` |
| `--face-mask-types` | `box,occlusion` | 边缘有硬圈时加上 `region` |
| `--output-video-quality` | `90` | 交付级用 `95`–`100`，会明显变大 |

---

## 五、常见问题

**侧脸、低头、手挡脸时脸会崩。**
模型只认 128/256 像素的人脸块。解决办法：把这类镜头先剪掉，或用 `face_editor` 处理器（预处理）+ 提高 pixel boost；实在不行在原片剪辑阶段规避。

**整段视频脸在「漂」，一会儿像一会儿不像。**
多半是视频里有多个人，selector 抓错了人。用 `--face-selector-mode reference --reference-frame-number <选一帧明确的脸>` 锁定。

**换完颜色和脖子不匹配。**
开 `--face-mask-types box,occlusion,region`，并把 `--face-enhancer-blend` 降到 60–70；原片是暖光/夜景时尤其明显。

**口型对不上。**
换脸不改口型。需要改台词时：换脸 → 再跑 `lip_syncer` 处理器（或外部对口型工具），最后再合成。

**视频很长（>5 分钟）。**
按段落切片跑，再合并，省内存也方便重跑单个镜头：

```bash
ffmpeg -i long.mp4 -c copy -f segment -segment_time 60 part_%03d.mp4
for f in part_*.mp4; do bash swap_face.sh 我.jpg "$f" "out_$f"; done
```

**能不能顺便换成我的声音？**
换脸不动音轨。声音要另外做：自己录，或用 TTS/声音克隆（需本人授权）。这也是「像不像你」的第二半——很多片子脸换了但一开口就露馅。

**商业使用可以吗？**
FaceFusion 代码是 **OpenRAIL-AS** 许可（带使用限制的责任型开源许可）；`inswapper_128` 这个具体模型来自 InsightFace，历史上只授权**非商业研究**，FaceFusion 3.x 已默认换成自家的 `hyperswap` 系列。**要商用，先读 `facefusion/LICENSE.md` 和所选模型的条款**，别默认「开源=随便卖」。

---

## 六、文件说明

| 文件 | 用途 |
|---|---|
| `install_facefusion.sh` | 建 venv、clone FaceFusion、按显卡自动装 CUDA/CPU 版 |
| `swap_face.sh` | 命令行换脸封装：一条命令出片，参数可用环境变量覆盖 |
| `precheck.py` | 跑之前的体检：照片清晰度/人脸数、视频帧率/时长/多人脸帧占比，并打印建议命令 |
| `requirements.txt` | `precheck.py` 的依赖（只需要 OpenCV） |

## 七、和仓库其它流程的关系

- 想**复刻整条爆款的结构**（换人 + 换台词 + 换 B-roll + 批量变体），用 Hypit 的 B 路线，不是这里；
- 想给**已有的电影解说成片**加出镜口播，可以先用本工具包把人脸换掉，再进 `render_commentary.py` 的时间线；
- 本工具包只处理人脸，**不处理声音和口型**。

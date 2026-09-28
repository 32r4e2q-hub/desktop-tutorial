# 照这个顺序贴（一次配好，之后都不用再贴）

前提：你现在看的是 Arena 沙箱的**文件面板**，`dist/payload/` 下面这些都是文本文件，
点开就能全选复制 —— 复制走的是文件本身，不经过聊天转述，所以不会抄错字符。

1. 开 Colab：<https://colab.research.google.com/#create=new> → New notebook
2. 逐格来（每格两次复制）：

   - 面板打开 `dist/payload/01-贴第1段.py` → 全选复制 → 粘成 Colab 第 1 格；
     再把 `dist/payload/p1.b64` 全选复制 → 粘进该格的三引号之间（替换那行提示）→ 运行该格
   - 面板打开 `dist/payload/02-贴第2段.py` → 全选复制 → 粘成 Colab 第 2 格；
     再把 `dist/payload/p2.b64` 全选复制 → 粘进该格的三引号之间（替换那行提示）→ 运行该格
   - 面板打开 `dist/payload/03-贴第3段.py` → 全选复制 → 粘成 Colab 第 3 格；
     再把 `dist/payload/p3.b64` 全选复制 → 粘进该格的三引号之间（替换那行提示）→ 运行该格
   - 面板打开 `dist/payload/04-贴第4段.py` → 全选复制 → 粘成 Colab 第 4 格；
     再把 `dist/payload/p4.b64` 全选复制 → 粘进该格的三引号之间（替换那行提示）→ 运行该格
   - 每格自己会报 `✓ 对上了`；报 ✗ 就回面板把那一段整个重复制一次（防手滑漏尾巴）
3. 4 段全绿 → 运行 `05-组装并自检.py`（整包 sha256 + 解出项目 + `--validate`）
4. 运行 `06-配音重生.py`：edge-tts 合成 6 段解说、自动配速、按实测重排切点
5. 运行 `07-推到你的仓库.py`：贴一次 PAT → 推上去 → Actions 自动点火跑 38 镜

**为什么绕这一圈**：沙箱出口只放行 GitHub 一类域名，预览端口又只认浏览器会话，
所以任何「下载文件」的按钮都是死的；唯一稳的通道是**文本 + 你在面板里复制**。
6 MB 的配音 mp3 过不来，于是改成到你那边用免费的 edge-tts 重生 —— 音色和原先试听选定的
那个会不同，但节奏由脚本按 `render.py` 的实测判据（0.86 ≤ tempo ≤ 1.10）自动配回去；
批准的成片 tempo 是 1.0662，重生后一般落在 1.00~1.07。

载荷：4 段 / 共 112336 字符 base64；整包 xz sha256 前 12 位 `e414459776d6`；
文件 29 个：

- `.github/workflows/monalisa-gen.yml`
- `.github/workflows/monalisa-render.yml`
- `.github/workflows/monalisa-verbatim.yml`
- `production/agnes_video.py`
- `production/monalisa/GEN_REQUEST`
- `production/monalisa/QA_REPORT.md`
- `production/monalisa/build_audio.py`
- `production/monalisa/clause_times.py`
- `production/monalisa/gen_status.py`
- `production/monalisa/generate.py`
- `production/monalisa/make_cuts.py`
- `production/monalisa/make_voice.py`
- `production/monalisa/media.py`
- `production/monalisa/plan_cuts.py`
- `production/monalisa/qa_rejects.py`
- `production/monalisa/render.py`
- `production/monalisa/scan_qa.py`
- `production/monalisa/screenplay.md`
- `production/monalisa/slate_render.py`
- `production/monalisa/story.json`
- `production/monalisa/throttle.py`
- `production/monalisa/tighten_pauses.py`
- `production/monalisa/watch_gen.py`
- `production/monalisa/watch_run.py`
- `production/monalisa/本机出片.sh`
- `production/requirements.txt`
- `production/review_film.py`
- `production/run_project.sh`
- `production/verbatim_check.py`

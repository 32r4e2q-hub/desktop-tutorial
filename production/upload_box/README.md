# 上传台（把需求表格交进来）

**它解决的问题**：你要做片子，需求写在 Word 表格里；但你手上只有聊天窗口和手机浏览器，
没有一个能把文件塞进工作区的地方。这个页面就是那个"塞文件的地方"——
浏览器里拖进去 → 落到仓库根的 `incoming_uploads/` → **同时自动把 docx/xlsx 表格解析成 Markdown 正文**，
我（Agent）不用你复述一遍就能直接读原文。

```
浏览器（拖放 / 选文件 / 顺手写两条补充要求）
   │  POST multipart（HTTP 上传，纯标准库，零依赖）
   ▼
incoming_uploads/                ← 原件，已在 .gitignore 里，不进 git
incoming_uploads/parsed/*.md     ← 表格转成的正文（我读这个）
incoming_uploads/parsed/*.json   ← 结构化结果（表格数 / 行数 / 失败原因）
incoming_uploads/notes.md        ← 你顺手写的补充要求
incoming_uploads/events.log      ← 谁什么时候交了什么，出问题时看这个
```

## 打开

```bash
python3 production/upload_box/server.py --port 8765 --host 0.0.0.0
```

- 在 Codespaces / 沙箱里跑：去端口面板点 **8765** 的"在浏览器中打开"（预览域名会替你转发）；
- 在自己电脑上跑：`http://localhost:8765/`；
- 服务是 `ThreadingHTTPServer` + 手写 multipart 解析，**不校验 Host / 不过滤 Origin**，
  所以代理域名能直接用；不装 Flask，装不上第三方包的地方也能跑。

## 支持什么

| 文件 | 处理 |
|---|---|
| `.docx` `.docm` | 按文档顺序把段落 + 表格抽出来，表格变 Markdown（`|` 转义，单元格内换行变 `<br>`） |
| `.xlsx` `.xlsm` | 逐个工作表转 Markdown，共享字符串、稀疏列（只填了 B/D 列）都对得齐 |
| `.txt` `.md` `.csv` | 原样当正文 |
| `.pdf` | 只存原件，不自动解析（会明确告诉你原因，别白等） |
| `.doc` `.xls` | 只存原件并提示"另存为 .docx / .xlsx"——97-2003 二进制格式不解析 |
| 图片 `.png` `.jpg` `.webp` `.gif` | 存下来当参考图（海报、截图、分镜草图都行），不解析 |

单文件上限 80 MB，超了会回一句人话而不是 500。重名不覆盖（自动 `xxx-1.docx`），
文件名里的 `../`、奇怪符号会被拍平（中文保留）。

## 接口

| 路由 | 用途 |
|---|---|
| `GET /` | 拖放页（手机端改成点按钮选文件，一样能用） |
| `GET /files` | 已收到文件的清单（页面每 3 秒轮询，所以我这边一落盘你就看得见） |
| `POST /upload` | multipart 上传 + 自动解析 |
| `GET /view/<名>` | 在浏览器里看解析出来的正文 |
| `POST /note` | 追加一条补充要求到 `notes.md`（"要三个备选标题"这种，不用回头改 Word） |
| `POST /delete?name=` | 删掉某个投递文件，连同它的解析结果 |
| `GET /healthz` | 起没起来 |

## 命令行（不想开网页）

```bash
python3 production/upload_box/extract_tables.py 需求.docx            # 打到终端
python3 production/upload_box/extract_tables.py 需求.docx -o 需求.md  # 存成 md
python3 production/upload_box/extract_tables.py 需求.xlsx --json     # 结构化
```

## 交完之后

我读 `incoming_uploads/parsed/*.md` 拿到硬性要求（题目 / 时长 / 横竖版 / 分镜 / 字幕 / 禁区），
然后照 [`../../新题目开工手册.md`](../../新题目开工手册.md) 走：

```bash
python3 production/new_topic.py --slug <slug> --title "<片名>" --branch <分支>
```

自检：`python3 -m unittest production.tests.test_upload_box`（11 条，覆盖解析、上传、重名、
穿越、超限、删除；不联网、不装包）。

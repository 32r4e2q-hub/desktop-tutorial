# CogVideoX-Flash 工具链说明

本工具链把 `production/jeong2000/` 已跑通的供应商与质量控制机制复用到新题目，同时保持每个项目内容隔离。

## 入口

```bash
python3 production/new_cogvideox_topic.py \
  --slug <英文slug> \
  --title "<中文片名>" \
  --branch <当前Arena固定分支>
```

完整操作见根目录 [`CogVideoX三分钟短片开工手册.md`](../CogVideoX三分钟短片开工手册.md)。

## 新项目内的工具

| 文件 | 职责 |
|---|---|
| `build_story.py` | 唯一内容源：六章口播、45 镜、信息卡、标题、字幕关键词与发布文案 |
| `generate.py` | 智谱 CogVideoX-Flash 请求、1305/429 退避、断点续跑、请求哈希与素材收据 |
| `fetch_sources.py` | 从供应商 CDN 恢复素材并核验 SHA-256 |
| `media.py` | ffprobe 检查、完整解码、逐镜接触表 |
| `tighten_pauses.py` | 只收紧长停顿，不改字 |
| `clause_times.py` | 分句时间动态规划与 CUTS 停顿窗闸门 |
| `render.py` | EDL、字幕、信息卡、角标安全裁切、混音、最终成片复测 |
| `qc_shots.py` | 生成素材的逐镜数字分诊 |
| `audit_frame_distortions.py` | 最终成片 5400 帧扫描 |
| `compose_all_frame_sheets.py` | 把每个输出帧写入逐镜全帧表 |
| `export_visual_review_candidates.py` | 导出时序/人脸/手部候选原帧 |
| `publish_visual_review_bundle.py` | 将人工审片证据写回项目目录 |
| `script_table.py` | 从同一内容源生成抖音四列表与发布文案 |

## 四条项目工作流

- `<slug>-gen.yml`：读取 `ZHIPUAI_API_KEY`，生成 38 个动态镜头；
- `<slug>-render.yml`：恢复已验证素材并渲染 180 秒成片；
- `<slug>-verbatim.yml`：对最终 MP4 做六章逐字听检；
- `<slug>-visual-qc.yml`：解码并审计全部 5400 帧。

安装方式：

```bash
cp production/<slug>/workflows/<slug>-*.yml .github/workflows/
```

## 不会复用的内容

脚手架不会复制参考片的：

- 口播与事实来源；
- 视频 URL、task id、SHA-256；
- 配音文件；
- QA 接触表与签收报告；
- marker 触发文件。

因此新项目创建后必须从事实核查和内容填写开始，`generate.py --validate` 默认失败是正确行为。

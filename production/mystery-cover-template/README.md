# 迷案解码人｜系列封面工具

这是用户已认可的竖版系列封面：1080×1440，固定背景、栏目、排版及红色期数角标；每期只换**期数、两行封面标题，以及截图窗口里的那张本片画面**。版式只有一份实现：`template.py` 里的 `cover()`；`generate_cover.py`、`build_template.py` 生成的样张、以及各案件 `render.py` 出片时的封面全部调用它，所以「所有封面都用这一个模板」是代码约束，不是约定。各案件出片时统一调用仓库根目录的 `production/series_cover.py`（它读 `story.json` 的 `presentation.cover`：`series_episode` / `line1` / `line2` / `window_shot` / `window_at` / `window_y_bias`），封面尺寸固定 1080×1440，`qc.py` 会按这个尺寸卡。仓库的 `NotoSerifCJKsc-Common.otf` 是编辑器内嵌字体的相同常用字子集，字体许可见 `OFL.txt`。`plate.jpg` 是预处理过的固定背景，运行时不依赖 `work/`、下载或浏览器。编辑器见 `封面模板_可编辑.html`，可离线手动修改；该 CLI 和编辑器是各自独立的生成途径，细微渲染差异需视觉复核。

## Agent 自动流程（只说期数）

用户只说第几期时，先结合当前对话和项目材料识别案件、核实事实，自拟发布标题和封面两行；拿不准是哪一案要先问，不要根据期数猜测。固定文案「真实案件」「动画情景复原」不适用于当前内容时先确认。完整约定见仓库根目录 `AGENTS.md` 和 `新题目开工手册.md`。


### 一句话出封面

```bash
# 1) 先看候选帧样张，自己挑一格
python3 -m production.series_cover --episode 2 --story production/holmes1893/story.json \
  --film 交付/H·H·霍姆斯_传说里的杀人城堡_三分钟_带声音.mp4 --contacts /tmp/候选.jpg
# 2) 把选中的镜头+镜内秒数写回 story.json 的 presentation.cover（window_shot / window_at）
# 3) 出封面：JPEG + PNG + 标题记录
python3 -m production.series_cover --episode 2 --story production/holmes1893/story.json \
  --film 交付/H·H·霍姆斯_传说里的杀人城堡_三分钟_带声音.mp4 \
  --output 交付/H·H·霍姆斯_传说里的杀人城堡_封面.png
```

`--line1/--line2` 覆盖自动标题，`--shot/--at`（绝对秒）跳过选帧。自动标题来自
`auto_title()`，自动选帧来自 `pick_frame()`（人物占比/对比/细节/字幕压制/镜头优先级打分，
但「代表性」仍需看图判断）。

首次安装本工具的最小依赖（安装可能需要联网，安装后生成离线运行）：

```bash
python3 -m pip install 'pillow>=10,<13' 'fonttools>=4.50,<5'
```

或安装完整工具链 `python3 -m pip install -r production/requirements.txt`。以下仅用已核实的第一期事实演示；每期须替换成**该期案件**的标题和来源，期数不是案件名称。

```bash
python3 production/mystery-cover-template/generate_cover.py \
  --episode 1 \
  --line1 '逃亡78天的西口彰' --line2 '却被女孩一眼认出' \
  --release-title '逃亡78天的西口彰，却被女孩一眼认出' \
  --fact-basis 'production/nishiguchi1963/screenplay.md 和 qa/review_round5.md' \
  --shot work/nishiguchi1963/edit/帧_通缉照.jpg --shot-y-bias 0.5 \
  --output production/nishiguchi1963/delivery/系列封面_第1期.png
```

`--episode` 为 1–9999 的整数，输出角标如「第二期」；两行各 1–18 个字符，超长报错、较长行自动缩字号。输出除 PNG 外还有同名 JSON，包含期数、两行封面标题、发布标题与传入的事实依据；省略 `--release-title` 时以逗号连接两行。`--fact-basis` 由 Agent 填写来源或项目文件，并自行核实，程序不会做事实核查或自主拟题。

CLI 默认拒绝覆盖 PNG **或**同名 JSON；需要明确更新时可用 `--force`。字体通过 cmap 检查所需字符；遇到缺字将报错，不会静默画方框。若标题必须包含生僻字，可用 `--font /路径/高覆盖字体.otf` 指定合规且覆盖所需字符的 OTF/TTF；该替代字体应人工查看样式，手动编辑器则仍使用内嵌字库。用户只指定期数时，Agent 应自动完成标题编写和命令参数，不要求用户填写两行。

生成后打开 PNG，核对期数、标题和字形、没有越界或遮挡，并按实际交付状态告诉用户；不要把自动化通过说成人工视觉验收。原始背景是按参考氛围重新创作，不是去除水印后的原图。

## 测试

```bash
python3 -m pytest production/tests/test_mystery_cover.py -q
```

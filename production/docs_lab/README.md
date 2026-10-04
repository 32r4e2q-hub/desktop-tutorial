# 资料与剧本工作台（docs_lab）

**用途**：开一部新片之前，把「资料」和「解说词」放进同一个工作区，让它们互相指着说话。

```
资料（PDF / Word / Markdown / TXT / 网页存档）
  └─ extract.py      拆成带出处的段落：文件 + 页码 + 段号
       └─ factbase.py    候选事实句 / 时间线 / 待标注的不确定句 → 事实底稿.md + sources.json
解说词（md / txt）
  └─ script_qa.py    章数 / 字数 / 时长 / TTS 风险词 / 数字读法
                     + 逐句回指资料段落（对得上 / 弱 / 没出处）→ 剧本体检.md + script-qa.json
```

它对应 [`新题目开工手册.md`](../../新题目开工手册.md) 的第 1、2 步，但**只出底稿不出结论**：
`build_story.py` 里的 `SOURCES` / `PRINCIPLES` 仍然由人核完再填。

---

## 起服务

```bash
python3 -m pip install --break-system-packages -r production/docs_lab/requirements.txt
python3 production/docs_lab/app.py --port 8010      # 跟风格实验室（8000）分开跑
```

也可以不开网页：

```bash
python3 production/docs_lab/extract.py --file ~/资料.pdf --out work/extracted
python3 production/docs_lab/factbase.py --extracted-dir work/extracted --out work/gilgo
python3 production/docs_lab/script_qa.py --script ~/解说词.md --extracted-dir work/extracted --out work/gilgo
```

**工作区（workspace）**是组织单位：资料和解说词放在同一个工作区里，出处映射才指着同一批资料说话。
网页右上角可以新建 / 切换，默认 `default`。

---

## 三个数字是从哪来的

不是拍脑袋定的阈值，全部来自手册与吉尔戈成片的实测值：

| 指标 | 值 | 出处 |
|---|---|---|
| 六章、总字数 760–800 | — | 手册第 2 步：「超过 800 字就塞不进去」 |
| 时长预算 176.1 s | — | 吉尔戈成片：785 字收紧停顿后 176.1 s |
| 语速 4.45 字/秒 | 784 ÷ 176.1 | 同上 |
| 字数口径 | 一个汉字一个、一个英文字母/数字一个、标点不算 | 用 `production/gilgo/story.json` 的六章正文反算：得 784 字（手册记 785），除以语速正好 176.1 s |
| 预计镜头数 | 该章估时 ÷ 4 秒 | 手册 45 镜 × 4 秒网格 |

口径一变，整个时长预算就跟着错，所以 `production/tests/test_docs_lab.py` 里有一条用例
直接拿 `production/gilgo/story.json` 当基准钉着它。

---

## 逐句出处映射怎么算的

字符二元组召回率：句子的二元组有多少出现在资料段落里（数字命中另加 0.15）。

* ≥ **0.34** → 「强」：句子基本能从那段资料里找到；
* 0.18–0.34 → 「弱」：可能改写了说法，去核一下；
* < **0.18** → 「无」：资料里没找到相似段落。

**相似不等于事实成立**，也不等于没有来源——解说词改写过说法时分数会偏低。
它只是告诉你去哪一段核，判定真假仍然是人的活。

---

## 产物

放在 `production/docs_lab/workspaces/<工作区>/`（**整个目录不进 git**：资料可能是私有的、有版权的）：

| 文件 | 内容 |
|---|---|
| `docs/`、`extracted/` | 原文件与拆好的段落（含 SHA-256、页码、段号） |
| `sources.json` | 资料清单 + 时间线 + 候选事实句 + 待标注的不确定句 |
| `事实底稿.md` | 上面那些的人读版本，含已知误差一节 |
| `scripts/`、`script-qa.json` | 解说词与体检结果 |
| `剧本体检.md` | 体检的人读版本：结论 / 分章表 / 风险词 / 数字 / 逐句出处表 |

---

## 已知误差

* 「候选事实句」靠信号打分（日期 +2 / 数字 +1 / 司法词 +1）：**会漏也会误报**——
  没有这些信号的事实句不入选，有这些信号的废话会入选；
* 时间线按年份归并，同年最多留 3 条；
* PDF 页码来自 PDF 自身分页；**Word 没有稳定页码**，按每 30 段估算一页，出处照样指得回去；
* 扫描件 PDF（只有图、没有文字层）抽不出内容，会如实报错，不假装抽到了；
* 风险词表是关键词匹配，会漏（同义改写）也会误报（「砍价」「刺骨」这类正常词）；
* 语速基准取自吉尔戈那一个音色，换音色或换语速档要重算。

---

## 测试

```bash
python3 -m pytest production/tests/test_docs_lab.py -q     # 16 个离线用例
```

PDF 那条用例需要 `pypdf`，没装就跳过；Word 那条用标准库 `zipfile` 直接读 `document.xml`，不引第三方库。

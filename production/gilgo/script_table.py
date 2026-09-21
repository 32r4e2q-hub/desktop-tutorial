#!/usr/bin/env python3
"""把 story.json + render.py 的 CUTS + 配音分句时间，拼成抖音脚本的四列分镜表。

四列：时间轴 / 口播文案 / 画面描述（动画建议）/ 音效备注。
- 时间轴：按 render.py 的排版常数（INTRO/GAP/OUTRO）和收紧后配音的实际时长算出的成片时间；
- 口播文案：CHAPTERS 里的原句，按 CUTS 切点分到每个镜头下（分句时间来自 audio/clause-times.json）；
- 画面描述：story.json 里每镜的 purpose + camera（中文），不重复抄英文提示词；
- 音效备注：story.json 的 sfx_note。

这样《抖音脚本.md》《screenplay.md》《story.json》《render.py》说的是同一份数据。
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def load():
    import render  # noqa: E402  (同目录；只取常数与 CUTS)
    story = json.loads((HERE / "story.json").read_text())
    clause_times = json.loads((HERE / "audio" / "clause-times.json").read_text())
    report = json.loads((HERE / "audio" / "tighten-report.json").read_text())
    durations = {row["id"]: row["tight_seconds"] for row in report["clips"]}
    usable = render.DURATION - render.INTRO - render.OUTRO - render.GAP * (len(story["chapters"]) - 1)
    tempo = sum(durations.values()) / usable
    return render, story, clause_times, durations, tempo


def segments():
    render, story, clause_times, durations, tempo = load()
    by_id = {s["id"]: s for s in story["shots"]}
    rows = []
    start = render.INTRO
    chapters = story["chapters"]
    for i, ch in enumerate(chapters):
        cid = ch["id"]
        cuts = render.CUTS[cid]
        clauses = clause_times[cid]["clauses"]
        chapter_end = (start + durations[cid] / tempo + render.GAP) if i + 1 < len(chapters) else 176.2
        for j, (raw, sid, _variant) in enumerate(cuts):
            seg_start = 0.0 if (i == 0 and j == 0) else start + raw / tempo
            seg_end = (start + cuts[j + 1][0] / tempo) if j + 1 < len(cuts) else chapter_end
            next_raw = cuts[j + 1][0] if j + 1 < len(cuts) else 1e9
            text = "".join(c["text"] + punct_after(ch["text"], c["text"])
                           for c in clauses if raw <= c["start"] + 0.05 < next_raw)
            shot = by_id[sid]
            rows.append({"id": sid, "kind": shot["kind"], "chapter": cid, "start": seg_start, "end": seg_end,
                         "text": text, "purpose": shot["purpose"], "camera": shot["camera"],
                         "sfx": shot["sfx_note"], "graphic": shot.get("graphic", "")})
        start += durations[cid] / tempo + render.GAP
    rows.append({"id": "END", "kind": "graphic", "chapter": "N06", "start": 176.2, "end": 180.0, "text": "",
                 "purpose": "片尾卡：把互动问题「是他太蠢，还是警察太耐心？」留在屏幕上，附资料来源",
                 "camera": "静态卡 + 淡出", "sfx": "音乐尾音，最后 0.8 秒渐隐", "graphic": ""})
    return rows, tempo


def punct_after(full, clause):
    """把分句后面紧跟的标点找回来（clause-times 里的分句是去掉标点的）。"""
    i = full.find(clause)
    if i < 0:
        return ""
    j = i + len(clause)
    m = re.match(r"[，。！？；：、—]+", full[j:])
    return m.group(0) if m else ""


def clock(t):
    return f"{int(t // 60):02d}:{t % 60:04.1f}"


def render_table():
    rows, tempo = segments()
    out = ["| 时间轴 | 口播文案 | 画面描述（动画建议） | 音效备注 |", "|---|---|---|---|"]
    chapter_names = {"N01": "0–5秒黄金开头 → 案件名片", "N02": "案件背景：双面人生", "N03": "作案手法",
                     "N04": "破案关键（上）：一辆皮卡", "N05": "破案关键（下）：披萨盒 · 作案清单", "N06": "结局与金句"}
    seen = set()
    for r in rows:
        if r["chapter"] not in seen and r["id"] != "END":
            seen.add(r["chapter"])
            out.append(f"| **{chapter_names[r['chapter']]}** | | | |")
        kind = "信息卡" if r["kind"] == "graphic" else "AI动画"
        picture = f"【{r['id']} · {kind}】{r['purpose']}（运镜：{r['camera']}）"
        text = r["text"] if r["text"] else "（无口播，画面收尾）"
        out.append(f"| {clock(r['start'])}–{clock(r['end'])} | {text} | {picture} | {r['sfx']} |")
    return "\n".join(out)


TITLES = [
    "他是模范爸爸，也是连环杀手：30年悬案，栽在一个披萨盒上",
    "警察跟了他一年半，只为等他扔垃圾｜长岛吉尔戈海滩连环案",
    "电脑里藏着一份「作案清单」：写于2000年，2026年当庭认罪",
]
HOOK = ("一个在曼哈顿写字楼上班、有妻有孩子的建筑咨询师，用一份写于 2000 年的「作案清单」，"
        "在自家地下室作案 17 年、至少 8 名受害者，让警方一无所获 30 年——最后暴露他的，"
        "是他随手扔进街头垃圾桶的一个披萨盒。")
GOLDEN_LINES = [
    "三十年的悬案，最后输给了一块没吃完的披萨边。",
    "所以，别再迷信什么完美犯罪。你扔掉的每一样东西，都在替你说话。",
    "你觉得，是他太蠢，还是警察太耐心？评论区聊聊。",
]


def render_document():
    rows, tempo = segments()
    story = json.loads((HERE / "story.json").read_text())
    total_chars = sum(len(re.sub(r"[，。！？；：、—]", "", c["text"])) for c in story["chapters"])
    agnes = sum(s["kind"] == "agnes" for s in story["shots"])
    cards = sum(s["kind"] == "graphic" for s in story["shots"])
    doc = [f"# 抖音脚本 · {story['title']}", "",
           "> 横版 16:9 · 1920×1080 · 30fps · 成片 180 秒（口播 ≈ 176 秒、"
           f"{total_chars} 字）· {len(story['shots'])} 个镜头（{agnes} 个 Agnes AI 动画镜头 + {cards} 张信息卡，"
           "每个镜头只出现一次）· 风格：无限科学式快节奏悬疑科普解说 + 2D 动画纪录片画面", "",
           "## 一、视频标题（三选一）", ""]
    doc += [f"{i}. {t}" for i, t in enumerate(TITLES, 1)]
    doc += ["", "## 二、核心爆点（一句话）", "", HOOK, "",
            "## 三、详细脚本（时间轴 / 口播文案 / 画面描述 / 音效备注）", "",
            "口播文案与成片配音**逐字一致**（`audio/manifest.json` 里有 SHA-256 收据）；"
            "时间轴按收紧停顿后的真实配音时长算出，成片以 `production/gilgo/delivery/edit-decision-list.json` 为准。", "",
            render_table(), "",
            "## 四、金句结尾（引导评论）", ""]
    doc += [f"- {line}" for line in GOLDEN_LINES]
    doc += ["", "片尾卡停留 3.8 秒：**「是他太蠢，还是警察太耐心？」** + 「你扔掉的每一样东西，都在替你说话。」+ 资料来源。", "",
            "## 五、事实边界（发布前自查）", ""]
    doc += [f"- {p}" for p in story["principles"]]
    doc += ["", "## 六、资料来源", ""]
    doc += [f"{src['id']}. {src['url']} —— {src['usage']}" for src in story["sources"]]
    doc.append("")
    return "\n".join(doc)


if __name__ == "__main__":
    if "--write" in sys.argv:
        out = HERE / "抖音脚本.md"
        out.write_text(render_document())
        print("written", out)
    else:
        print(render_table())

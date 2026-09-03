#!/usr/bin/env python3
"""将 154 句解说按长度均分成 8 段配音块，生成 spoken.json 与逐块文本。

输出目录：<ROOT>/work/tts_src/（chunk_XX.txt 供 generate_speech 使用；
spoken.json 供 tts_align.py 使用）。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # 工作目录（仓库根）
NARR = ROOT / "production" / "narration.json"

# 触发语音审核的 7 句原稿 -> 温和改写（字幕仍用原稿，仅旁白用词变化）
SOFTEN = {
    107: "两人被按住时还在冷笑，说自己绝不会伤害这么有用的天使",
    109: "为了让她回想起来，桑蒂尼盯上了迪娅",
    110: "怀有身孕的迪娅从楼梯上摔了下来，情况万分危急",
    111: "安吉拉隔着铁门，听见母亲痛苦地喊她的名字",
    112: "那一夜，她在阁楼里，独自迎接了新生命的到来",
    113: "她一个人承受着一切，不敢发出一点声音",
    116: "逃出地窖后，她告诉警察：害了她母亲的，是一群邪教徒",
}


def spoken(idx, text):
    if idx in SOFTEN:
        text = SOFTEN[idx]
    text = text.strip()
    if not re.search(r"[。！？…]$", text):
        text += "。"
    return text


def main():
    narr = json.load(open(NARR, encoding="utf-8"))
    flat = [(si, ci, c["text"]) for si, s in enumerate(narr, 1)
            for ci, c in enumerate(s["cues"], 1)]
    assert len(flat) == 154

    N = 8
    items = [(i, spoken(i, t)) for i, (si, ci, t) in enumerate(flat)]
    total = sum(len(t) for _, t in items)
    target = total / N
    chunks, cur, cur_len = [], [], 0
    for idx, t in items:
        if cur and cur_len + len(t) > target and len(chunks) < N - 1:
            chunks.append(cur)
            cur, cur_len = [], 0
        cur.append((idx, t))
        cur_len += len(t)
    if cur:
        chunks.append(cur)

    outdir = ROOT / "work" / "tts_src"
    outdir.mkdir(parents=True, exist_ok=True)
    manifest = {"chunks": []}
    for k, ch in enumerate(chunks):
        manifest["chunks"].append({
            "id": k,
            "wav": f"chunk_{k:02d}.wav",
            "sentences": [[t, i] for i, t in ch],
        })
        (outdir / f"chunk_{k:02d}.txt").write_text(
            "\n".join(t for _, t in ch) + "\n", encoding="utf-8")
    json.dump(manifest, open(outdir / "spoken.json", "w"),
              ensure_ascii=False, indent=1)
    seen = [i for ch in chunks for i, _ in ch]
    print("chunks:", len(chunks), "coverage:", sorted(seen) == list(range(154)))


if __name__ == "__main__":
    main()

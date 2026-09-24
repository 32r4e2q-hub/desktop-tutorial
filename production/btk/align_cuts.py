#!/usr/bin/env python3
"""Place every visual cut near a clause onset; use duration-balanced monotone DP.

TTS voices do not necessarily leave a measurable pause after every punctuation mark.
clause_times.py therefore uses observed silences where sufficient and explicitly
labels its weighted-time fallback otherwise. This helper picks cut positions at
clause onsets (never repeated, no shot reused), balances shot lengths, and writes
an audit receipt. Final caption timing is independently ASR-aligned during render.
"""
import importlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def choose_boundaries(duration, starts, count, minimum=1.5, maximum=6.65):
    """Choose count-1 increasing cut points from starts, close to equal spacing."""
    targets = [duration * j / count for j in range(1, count)]
    candidates = sorted({round(float(x) - 0.10, 3) for x in starts
                         if 0.45 < float(x) - 0.10 < duration - minimum})
    states = {}
    for k, point in enumerate(candidates):
        if minimum <= point <= maximum:
            states[(1, k)] = ((point - targets[0]) ** 2, [k])
    for j in range(2, count):
        for k, point in enumerate(candidates):
            best = None
            for h in range(k):
                previous = candidates[h]
                prior = states.get((j - 1, h))
                if prior is None or not minimum <= point - previous <= maximum:
                    continue
                cost = prior[0] + (point - targets[j - 1]) ** 2
                if best is None or cost < best[0]:
                    best = (cost, prior[1] + [k])
            if best is not None:
                states[(j, k)] = best
    need = count - 1
    finalists = []
    for k, point in enumerate(candidates):
        state = states.get((need, k))
        if state and minimum <= duration - point <= maximum:
            finalists.append(state)
    if not finalists:
        # Relax the lower bound slightly for a fast chapter, but never exceed the
        # Agnes usable window. The script fails loudly if even that is impossible.
        return choose_boundaries(duration, starts, count, minimum=1.0, maximum=6.65) if minimum > 1.0 else None
    best = min(finalists, key=lambda row: row[0])
    return [candidates[k] for k in best[1]]


def main():
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    timing = json.loads((HERE / "audio" / "clause-times.json").read_text(encoding="utf-8"))
    render = importlib.import_module("render")
    groups = {}
    for shot in story["shots"]:
        groups.setdefault(shot["narration_id"], []).append(shot["id"])
    report = {}
    lines = ["CUTS = {"]
    for chapter in story["chapters"]:
        cid = chapter["id"]
        row = timing[cid]
        ids = groups[cid]
        cuts = choose_boundaries(row["duration"], [c["start"] for c in row["clauses"]], len(ids))
        if cuts is None:
            raise SystemExit(f"{cid}: 无法将 {len(ids)} 个镜头安排到 {row['duration']:.2f}s 内")
        points = [0.0, *cuts]
        points = [round(p, 2) for p in points]
        entries = [(point, sid, "") for point, sid in zip(points, ids)]
        # Ensure each selected cut is at most 0.35s before its nearest estimated
        # clause start; clause_times.py --check-cuts is the final hard gate.
        report[cid] = {"duration": row["duration"], "shots": ids, "cuts": [
            {"at": point, "shot": sid, "nearest_clause": min(row["clauses"], key=lambda c: abs(c["start"] - point))["text"]}
            for point, sid, _ in entries], "segment_seconds": [
                round((points[i + 1] if i + 1 < len(points) else row["duration"]) - point, 2)
                for i, point in enumerate(points)]}
        encoded = ", ".join(f"({point:g},'{sid}','')" for point, sid, _ in entries)
        lines.append(f"    '{cid}': [{encoded}],")
    lines.append("}")
    source = (HERE / "render.py").read_text(encoding="utf-8")
    source = re.sub(r"CUTS = \{.*?\n\}", "\n".join(lines), source, count=1, flags=re.S)
    (HERE / "render.py").write_text(source, encoding="utf-8")
    (HERE / "audio" / "cut-alignment.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for cid, row in report.items():
        print(f"{cid}: {len(row['shots'])}镜，片长{row['duration']:.2f}s，镜头时长 {row['segment_seconds']}")
    print("CUTS written to render.py and audio/cut-alignment.json")


if __name__ == "__main__":
    main()

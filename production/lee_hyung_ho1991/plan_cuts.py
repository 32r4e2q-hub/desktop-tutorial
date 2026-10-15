#!/usr/bin/env python3
"""Place editorial cuts on measured or pause-aware estimated clause boundaries."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
MIN_SHOT_SECONDS = 1.55


def plan() -> dict[str, list[list[object]]]:
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    timing = json.loads((HERE / "audio" / "clause-times.json").read_text(encoding="utf-8"))
    shots_by_chapter: dict[str, list[dict]] = {}
    for shot in story["shots"]:
        shots_by_chapter.setdefault(shot["narration_id"], []).append(shot)

    cuts: dict[str, list[list[object]]] = {}
    for chapter in story["chapters"]:
        cid = chapter["id"]
        shots = shots_by_chapter[cid]
        clauses = timing[cid]["clauses"]
        duration = float(timing[cid]["duration"])
        starts = [float(row["start"]) for row in clauses[1:]]
        chapter_cuts: list[list[object]] = [[0.0, shots[0]["id"], ""]]
        previous = 0.0
        for boundary_i in range(1, len(shots)):
            target = duration * boundary_i / len(shots)
            low = previous + MIN_SHOT_SECONDS
            high = duration - (len(shots) - boundary_i) * MIN_SHOT_SECONDS
            candidates = [value for value in starts if low + 0.04 <= value <= high]
            if not candidates:
                raise RuntimeError(
                    f"{cid}: no measured clause pause can fit cut {boundary_i}/{len(shots)} "
                    f"inside {low:.2f}-{high:.2f}s; inspect audio/clause-times.json and revise the narration."
                )
            clause_start = min(candidates, key=lambda value: abs(value - target))
            # Place the visual cut just before the next utterance, inside its measured quiet interval.
            cut = max(previous + MIN_SHOT_SECONDS, clause_start - 0.04)
            if cut > high:
                raise RuntimeError(f"{cid}: cut exceeds the remaining chapter time ({cut:.2f}>{high:.2f})")
            chapter_cuts.append([round(cut, 2), shots[boundary_i]["id"], ""])
            previous = cut
        cuts[cid] = chapter_cuts
        print(f"{cid}: {len(shots)} shots, {duration:.2f}s narration, "
              f"cuts=" + ", ".join(f"{row[0]:.2f}" for row in chapter_cuts))

    expected = {shot["id"] for shot in story["shots"]}
    used = [row[1] for rows in cuts.values() for row in rows]
    if set(used) != expected or len(used) != len(expected):
        raise RuntimeError("CUTS do not use every planned shot exactly once")
    return cuts


def main() -> None:
    result = plan()
    out = HERE / "audio" / "cuts.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE {out}")


if __name__ == "__main__":
    main()

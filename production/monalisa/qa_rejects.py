#!/usr/bin/env python3
"""把「哪些镜头必须重做」压成机器可读的一行，供工作流的自愈循环吃。

判据只有一个来源：`scan_qa.py` 的逐格扫描。这里只补两件 scan 看不见的事——
- 该生成却连联络表都没有（Agnes 任务挂了 / 被跳过 / 只写了 results.json）；
- 应生成清单本身（story.json 里 `kind=="agnes"` 的那 38 个镜头），
  没有它就没法区分「合格」和「压根没跑」。

用法：
    python3 production/monalisa/qa_rejects.py                      # 第一行=逗号分隔镜头号
    python3 production/monalisa/qa_rejects.py --include-warn       # warn 也一起重做
    python3 production/monalisa/qa_rejects.py --json 报告.json     # 明细，给外部读
退出码：0 = 全部放行；1 = 还有待重做的镜头。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def expected_ids(plan_path: Path) -> list[str]:
    plan = json.loads(plan_path.read_text())
    return [s["id"] for s in plan["shots"] if s.get("kind") == "agnes"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--qa", type=Path, default=HERE / "qa")
    ap.add_argument("--plan", type=Path, default=HERE / "story.json")
    ap.add_argument("--json", type=Path, default=None, help="把明细写成 JSON，方便 commit 回分支")
    ap.add_argument("--include-warn", action="store_true",
                    help="把 warn 也算进待重做（默认只算 fail：warn 是人眼确认项）")
    args = ap.parse_args()

    ids = expected_ids(args.plan)
    want = set(ids)
    have = {p.stem for p in args.qa.glob("S??.jpg")} if args.qa.is_dir() else set()

    rows: list[dict] = []
    detail: dict[str, str] = {}
    if have:
        sys.path.insert(0, str(HERE))
        import scan_qa  # numpy/PIL 只有真扫的时候才需要
        rows = [r for r in scan_qa.scan(args.qa) if r["id"] in want]
        for r in rows:
            bad = r["verdict"] == "fail" or (args.include_warn and r["verdict"] == "warn")
            if bad:
                detail[r["id"]] = "；".join(r.get("reasons") or []) or r["verdict"]
    for missing in want - have:
        detail[missing] = "没有联络表（未生成或生成失败）"

    rejects = sorted(set(detail))
    payload = {
        "expected": len(ids),
        "sheets": len(have & want),
        "verdicts": {r["id"]: r["verdict"] for r in rows},
        "rejects": rejects,
        "detail": detail,
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(",".join(rejects))
    if rejects:
        print(f"REJECTS {len(rejects)}/{len(ids)} 需重做：" + "；".join(f"{k} {detail[k]}" for k in rejects))
    else:
        print(f"REJECTS 0/{len(ids)} 全部放行（联络表 {payload['sheets']} 张）")
    return 1 if rejects else 0


if __name__ == "__main__":
    sys.exit(main())

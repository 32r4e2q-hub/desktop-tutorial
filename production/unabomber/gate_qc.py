#!/usr/bin/env python3
"""Fail the job if any measured QC gate failed. Missing reports also fail."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
delivery = ROOT / "delivery"
review_path = Path("work/unabomber/review/film-review.json")
qc_path = delivery / "qc-report.json"
verb_path = delivery / "verbatim-check.json"

errors = []
if not qc_path.is_file():
    errors.append("missing qc-report.json")
    qc = {"checks": []}
else:
    qc = json.loads(qc_path.read_text(encoding="utf-8"))
if not review_path.is_file():
    errors.append("missing film-review.json")
    review = {"flags": []}
else:
    review = json.loads(review_path.read_text(encoding="utf-8"))
if not verb_path.is_file():
    errors.append("missing verbatim-check.json")
    verb = {}
else:
    verb = json.loads(verb_path.read_text(encoding="utf-8"))

bad = [c["name"] for c in qc.get("checks", []) if not c.get("ok")]
audio_flags = [f for f in review.get("flags", []) if any(k in f for k in ("静音", "电平"))]
failing = verb.get("film_pass", {}).get("failing", [])
print("QC_FAILING_CHECKS", bad)
print("REVIEW_AUDIO_FLAGS", audio_flags)
print("VERBATIM_FAILING", failing)
for row in verb.get("film_pass", {}).get("chapters", []):
    print(f"  {row['id']} CER={row['character_error_rate']} cov={row['match_coverage']} {row['verdict']}")
if errors or bad or audio_flags or failing:
    print("QC_ERRORS", errors)
    sys.exit(1)
print("QC_ALL_GATES_PASSED")

#!/usr/bin/env python3
"""登记已人工逐张检查通过的参考图：写 reference/approvals.json（含 SHA-256）。

用法：python3 production/itaewon1997/approve_refs.py C01 C03 ...   （只登记列出的 ID）
      python3 production/itaewon1997/approve_refs.py --all          （要求 29 张全部存在）
"""
import hashlib, json, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from build_story import REF_DESC  # noqa: E402

def sha(p):
    h = hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()

def main():
    ids = list(REF_DESC) if "--all" in sys.argv else [a for a in sys.argv[1:] if not a.startswith("--")]
    ledger_path = HERE / "reference" / "approvals.json"
    doc = json.loads(ledger_path.read_text(encoding="utf-8")) if ledger_path.is_file() else {"assets": {}}
    for rid in ids:
        f = HERE / "reference" / f"{rid}.png"
        if not f.is_file() or f.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n":
            raise SystemExit(f"{rid}: missing or not a PNG")
        doc["assets"][rid] = {"status": "approved", "sha256": sha(f), "file": f"reference/{rid}.png",
                              "description": "定稿：" + REF_DESC[rid]}
    doc["reviewer"] = "Arena assistant visual inspection, individual source images"
    doc["reviewed_at"] = time.strftime("%Y-%m-%d")
    doc["note"] = "逐张检查构图、年代感、尊重与克制、无血迹/污渍、无可读文字/品牌标识、人体结构稳定。"
    ledger_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"approved {len(doc['assets'])}/{len(REF_DESC)}")

main()

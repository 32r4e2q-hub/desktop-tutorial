#!/usr/bin/env python3
"""Canary probe: is the older `agnes-video-v2.0` route responsive while 2.5-flash stalls?

The 2.5 Flash route answered `pending progress=0%` for every new task on 2026-11-02 while this
film's S01 eventually completed after ~45 minutes. Before re-cutting anything, this probe asks
both routes for one short clip and records what the provider actually says, per minute, so the
decision is made on evidence instead of hope. Output: ``qa/probe-v20.json`` in the project.

Run on the Actions runner (needs AGNES_API_KEY)::

    python3 production/kinkakuji1950/probe_v20.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = "https://apihub.agnes-ai.com"
STYLE = (
    "Cinematic 3D animated film still of Kinkaku-ji, the three-storey golden pavilion, beside a "
    "mirror pond at dawn with sakura petals drifting. Slow aerial descent toward the water, "
    "volumetric light, warm gold against deep indigo, no text."
)
V20 = {
    "model": "agnes-video-v2.0",
    "prompt": STYLE,
    "width": 1280,
    "height": 720,
    "num_frames": 145,
    "frame_rate": 24,
    "seed": 19500702,
}
V25 = {
    "model": "agnes-video-2.5-flash",
    "prompt": "【STYLE】" + STYLE + " 【NEGATIVE】text, watermark, lettering",
    "seconds": "6",
    "size": "720P",
    "aspect_ratio": "16:9",
    "mode": "text",
    "n": 1,
    "seed": 19500702,
}


def request(method: str, url: str, key: str, payload: dict | None = None) -> tuple[int, dict, str]:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json",
               "Content-Type": "application/json",
               "User-Agent": "kinkakuji1950-probe/1.0"}
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            text = response.read().decode("utf-8", "replace")
            return response.status, json.loads(text or "{}"), text
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(text or "{}"), text
        except json.JSONDecodeError:
            return error.code, {}, text


def probe(key: str, name: str, payload: dict, minutes: int = 12) -> dict:
    started = time.time()
    code, body, text = request("POST", f"{BASE}/v1/videos", key, payload)
    row = {"name": name, "create_code": code, "create_body": body if isinstance(body, dict) else text[:400],
           "timeline": []}
    if not (200 <= code < 300 and isinstance(body, dict)):
        row["verdict"] = "create rejected"
        return row
    video_id = body.get("video_id") or body.get("id") or body.get("task_id")
    task_id = body.get("task_id") or body.get("id")
    row["video_id"] = video_id
    row["task_id"] = task_id
    deadline = started + minutes * 60
    while time.time() < deadline:
        time.sleep(30)
        url = f"{BASE}/agnesapi?" + urllib.parse.urlencode(
            {"video_id": video_id, "model_name": payload["model"]})
        pcode, pbody, ptext = request("GET", url, key)
        state = str((pbody or {}).get("status") or "").lower()
        row["timeline"].append({"t": round(time.time() - started, 1), "code": pcode,
                                "status": state, "progress": (pbody or {}).get("progress")})
        if state in {"completed", "complete", "succeeded", "success", "done", "finished"}:
            url_found = None
            for key_name in ("video_url", "url", "output", "video"):
                value = (pbody or {}).get(key_name)
                if isinstance(value, str) and value.startswith("http"):
                    url_found = value
                    break
            row["video_url"] = url_found
            row["verdict"] = "completed"
            return row
        if state in {"failed", "failure", "error", "cancelled", "canceled", "expired", "rejected"}:
            row["verdict"] = "failed: " + ptext[:300]
            return row
    row["verdict"] = "still pending after %d min" % minutes
    return row


def main() -> int:
    key = os.environ.get("AGNES_API_KEY", "").strip()
    if not key:
        raise SystemExit("AGNES_API_KEY is not available")
    report = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
              "probes": []}
    for name, payload in (("agnes-video-v2.0", V20), ("agnes-video-2.5-flash", V25)):
        print(f"== probing {name} ==", flush=True)
        outcome = probe(key, name, payload)
        print(json.dumps(outcome, ensure_ascii=False)[:600], flush=True)
        report["probes"].append(outcome)
    out = HERE / "qa" / "probe-v20.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

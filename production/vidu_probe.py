#!/usr/bin/env python3
"""Vidu 可用性探针：在 Actions runner 上回答「仓库里到底有没有可用的 Vidu key，能不能免费出片」。

为什么要跑在 Actions：沙箱连不上外网 API，GitHub secret 也读不到名字（API 403）。
workflow 里把若干个常见 secret 名映射成环境变量（不存在的会解析成空字符串），
本脚本只报告「有没有值 + 指纹」，**永远不会打印 key 本身**。

两个动作：
  --credits  只查积分（GET /ent/v2/credits），零成本、不消耗额度
  --spend    真提交一条最小任务（4 秒 / 360p），验证能不能出片，会消耗积分

判定口径：
  200 + 剩余积分 > 0  → 这把 key 能用，且知道还能生成多少秒
  200 + 剩余积分 = 0  → key 有效但没额度
  401/403             → key 无效或没权限
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "vidu-probe/1.0 (+https://github.com/32r4e2q-hub/desktop-tutorial)"
# 国内站与国际站是两个域名，同一把 key 通常只认其中一个，所以两个都探。
HOSTS = ("https://api.vidu.cn", "https://api.vidu.com")
# workflow 会把候选 secret 名映射成 VPROBE_<NAME> 环境变量
CANDIDATES = (
    ("VIDU_API_KEY", "VPROBE_VIDU_API_KEY"),
    ("VIDU_KEY", "VPROBE_VIDU_KEY"),
    ("VIDU_TOKEN", "VPROBE_VIDU_TOKEN"),
    ("VIDU_APIKEY", "VPROBE_VIDU_APIKEY"),
    ("VIDU_CN_API_KEY", "VPROBE_VIDU_CN_API_KEY"),
    ("VIDU_AI_API_KEY", "VPROBE_VIDU_AI_API_KEY"),
)
MINIMAL_PROMPT = ("A locked-off shot of an empty quiet room at dawn, soft daylight through a window, "
                  "no people, no text, no logos.")


def fingerprint(value: str) -> dict:
    """只留指纹：换过 key 之后要能一眼看出跑的是哪一把，但看不回原文。"""
    return {
        "sha256_12": hashlib.sha256(value.encode()).hexdigest()[:12],
        "last4": value[-4:],
        "length": len(value),
    }


def request(method: str, url: str, key: str, payload: dict | None = None, timeout: float = 60) -> dict:
    headers = {
        # Vidu 用的是 "Token xxx"，不是 Bearer —— 抄错这里会一律 401
        "Authorization": f"Token {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            code, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        code, raw = exc.code, exc.read()
    except Exception as exc:  # noqa: BLE001 - 网络问题如实记下
        return {"ok": False, "status": None, "error": f"{type(exc).__name__}: {exc}",
                "elapsed_s": round(time.monotonic() - started, 2)}
    text = raw.decode("utf-8", "replace")
    try:
        body = json.loads(text) if text.strip() else None
    except ValueError:
        body = None
    return {"ok": 200 <= code < 300, "status": code, "body": body,
            "raw": " ".join(text.split())[:600],
            "elapsed_s": round(time.monotonic() - started, 2)}


def total_credits(body: Any) -> tuple[float | None, list[dict]]:
    """把 /ent/v2/credits 的返回折算成「还剩多少积分」。"""
    if not isinstance(body, dict):
        return None, []
    rows = []
    total = 0.0
    found = False
    for item in body.get("remains") or []:
        if isinstance(item, dict) and isinstance(item.get("credit_remain"), (int, float)):
            rows.append({"type": item.get("type"), "credit_remain": item["credit_remain"],
                         "concurrency_limit": item.get("concurrency_limit"),
                         "queue_count": item.get("queue_count")})
            total += float(item["credit_remain"])
            found = True
    if not found:
        for item in body.get("packages") or []:
            if isinstance(item, dict):
                rows.append({"name": item.get("name"), "type": item.get("type"),
                             "credit_amount": item.get("credit_amount"),
                             "credit_remain": item.get("credit_remain"),
                             "valid_to": item.get("valid_to")})
    return (total if found else None), rows


def check_credits(host: str, key: str) -> dict:
    record = request("GET", f"{host}/ent/v2/credits", key)
    remaining, rows = total_credits(record.get("body"))
    record.update(host=host, credits_remaining=remaining, packages=rows)
    record.pop("body", None)
    return record


def submit_minimal(host: str, key: str) -> dict:
    payload = {
        "model": "viduq1",
        "style": "general",
        "prompt": MINIMAL_PROMPT,
        "duration": "4",
        "seed": "0",
        "aspect_ratio": "16:9",
        "resolution": "360p",
        "movement_amplitude": "auto",
    }
    record = request("POST", f"{host}/ent/v2/text2video", key, payload)
    task_id = None
    if isinstance(record.get("body"), dict):
        task_id = record["body"].get("task_id") or record["body"].get("id")
    record.update(host=host, task_id=task_id, payload=payload)
    record.pop("body", None)
    if not task_id:
        return record
    # 轮询到出片（4 秒 360p 通常 10–60 秒）
    deadline = time.monotonic() + 240
    while time.monotonic() < deadline:
        poll = request("GET", f"{host}/ent/v2/tasks/{urllib.parse.quote(str(task_id))}/creations", key)
        body = poll.get("body") or {}
        state = str(body.get("state") or "")
        record["final_state"] = state or record.get("final_state")
        record["poll_status"] = poll.get("status")
        if state in ("success", "failed"):
            record["credits_used"] = body.get("credits")
            creations = body.get("creations") or []
            if creations and isinstance(creations, list):
                record["video_url"] = creations[0].get("url")
            record["err_code"] = body.get("err_code")
            break
        time.sleep(5)
    record.pop("body", None)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="production/vidu-probe")
    parser.add_argument("--spend", action="store_true")
    parser.add_argument("--host", default="", help="只探这个域名（默认两个都探）")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "spend": bool(args.spend),
        "found_keys": [],
        "missing": [],
        "probes": [],
    }

    keys: list[tuple[str, str]] = []
    for name, env in CANDIDATES:
        value = (os.environ.get(env) or "").strip()
        if value:
            keys.append((name, value))
            report["found_keys"].append({"secret_name": name, **fingerprint(value)})
        else:
            report["missing"].append(name)

    if not keys:
        report["verdict"] = "NO_KEY"
        (outdir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        (outdir / "report.md").write_text(
            "# Vidu 探针结果\n\n仓库 secret 里**没有找到任何 Vidu key**。\n\n"
            "已尝试的名字：" + "、".join(f"`{n}`" for n, _ in CANDIDATES) + "\n\n"
            "如果你确实加过，请确认它用的是以上某个名字（GitHub 的 secret 名大小写敏感），"
            "或者告诉我实际名字，我把它加进候选清单再跑一次。\n")
        print("NO Vidu key found among:", ", ".join(n for n, _ in CANDIDATES))
        return 0

    hosts = [args.host] if args.host else list(HOSTS)
    for name, value in keys:
        row: dict[str, Any] = {"secret_name": name, "fingerprint": fingerprint(value), "hosts": {}}
        for host in hosts:
            credits = check_credits(host, value)
            entry = {
                "credits_http": credits.get("status"),
                "credits_remaining": credits.get("credits_remaining"),
                "packages": credits.get("packages"),
                "raw": credits.get("raw"),
                "error": credits.get("error"),
            }
            if credits.get("status") == 200:
                entry["verdict"] = "KEY_OK"
                if not args.spend:
                    entry["spend"] = "skipped (加 --spend 才会真提交一条 4 秒 360p 任务)"
                else:
                    spent = submit_minimal(host, value)
                    entry["spend"] = {k: v for k, v in spent.items() if k != "payload"}
            elif credits.get("status") in (401, 403):
                entry["verdict"] = "KEY_INVALID_OR_FORBIDDEN"
            elif credits.get("status") is None:
                entry["verdict"] = "HOST_UNREACHABLE"
            else:
                entry["verdict"] = "UNKNOWN"
            row["hosts"][host] = entry
        report["probes"].append(row)

    ok = [p for p in report["probes"] if any(h.get("verdict") == "KEY_OK" for h in p["hosts"].values())]
    report["verdict"] = "KEY_OK" if ok else "KEY_PRESENT_BUT_UNUSABLE"

    (outdir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    lines = ["# Vidu 探针结果", "", f"- 时间（UTC）：`{report['generated_at']}`",
             f"- 真提交任务：`{'是' if args.spend else '否（只查积分）'}`", "",
             "| secret 名 | 域名 | 积分查询 | 剩余积分 | 结论 |", "| --- | --- | --- | --- | --- |"]
    for probe in report["probes"]:
        for host, entry in probe["hosts"].items():
            lines.append("| `{}` | {} | HTTP {} | {} | {} |".format(
                probe["secret_name"], host, entry.get("credits_http"),
                entry.get("credits_remaining"), entry.get("verdict")))
    for probe in report["probes"]:
        for host, entry in probe["hosts"].items():
            spend = entry.get("spend")
            if isinstance(spend, dict):
                lines += ["", f"### {probe['secret_name']} @ {host} 真提交结果", "",
                          f"- POST: HTTP {spend.get('status')}　task_id: `{spend.get('task_id')}`",
                          f"- 最终状态: `{spend.get('final_state')}`　消耗积分: `{spend.get('credits_used')}`",
                          f"- 视频: {spend.get('video_url') or '（无）'}",
                          f"- 原始响应: `{str(spend.get('raw'))[:300]}`"]
    (outdir / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

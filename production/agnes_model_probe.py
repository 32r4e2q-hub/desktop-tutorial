#!/usr/bin/env python3
"""Zero-cost availability probe for Agnes text and video models.

The sandbox that drives this repository cannot reach apihub.agnes-ai.com, so the
probe runs on a GitHub Actions runner (which has both outbound network access and
the AGNES_API_KEY secret) and commits its report back to the branch.

Cost control
------------
Probing by generating a video would burn credits on four model names, so the
default mode is a *validation probe*: every other field is valid and only the
prompt / frame count is left invalid. A model whose name is rejected answers with
"model not found / unsupported / deprecated"; a model whose name is accepted gets
far enough to complain about the prompt or the frame count. Neither branch queues
a rendering job, so the probe is free.

``--spend`` turns on the paid path (one minimal clip per model) for cases where
"is it free for my account?" can only be answered by actually submitting a task.

Standard library only, so it runs on a bare runner without pip.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

DEFAULT_BASE_URL = "https://apihub.agnes-ai.com"
USER_AGENT = "agnes-model-probe/1.0 (+https://github.com/32r4e2q-hub/desktop-tutorial)"

VIDEO_MODELS = [
    "agnes-video-v2.0",
    "agnes-video-2.5",
    "agnes-video-v2.0-flash",
    "agnes-video-2.5-flash",
]
TEXT_MODELS = [
    "agnes-2.0-flash",
    "agnes-2.5-flash",
]

MODEL_LIST_PATHS = ["/v1/models", "/v1/model/list", "/openapi.json"]
CHAT_PATHS = ["/v1/chat/completions"]

# Words that mean "the model name itself was refused".
MODEL_REFUSED = (
    "model not found", "unknown model", "unsupported model", "model unsupported",
    "model does not exist", "invalid model", "illegal model", "no such model",
    "model_not_found", "model is not available", "model unavailable",
    "not support model", "unsupported model_name", "model_name is invalid",
    "deprecated", "no longer available", "has been retired", "offline",
    "下线", "已下线", "不存在",
)
# Words that mean "the model name was fine, something else in my payload is wrong".
PAST_MODEL_CHECK = (
    "prompt", "num_frames", "num frames", "seconds", "frames", "resolution",
    "required", "must be", "cannot be empty", "empty", "invalid", "size",
    "aspect", "parameter",
)
PAYMENT_WORDS = (
    "insufficient", "balance", "quota", "credit", "payment", "not enough",
    "arrears", "top up", "top-up", "余额", "额度", "付费", "充值",
)

VERDICT_LABEL = {
    "ACCEPTED": "可用（请求被受理）",
    "MODEL_ACCEPTED": "模型存在（通过了模型名校验）",
    "MODEL_REFUSED": "模型不可用（被拒绝/已下线）",
    "NEEDS_PAYMENT": "需要付费或余额/配额不足",
    "RATE_LIMITED": "被限流（模型存在）",
    "AUTH_FAILED": "鉴权失败（key 无效）",
    "ENDPOINT_MISSING": "接口不存在（404）",
    "NETWORK_ERROR": "网络错误",
    "UNKNOWN": "无法判定（需人工看原文）",
}


# --------------------------------------------------------------------------- HTTP
def request(
    method: str,
    url: str,
    api_key: str,
    payload: Optional[dict] = None,
    timeout: float = 60,
) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    started = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            code, raw = response.status, response.read()
    except urllib.error.HTTPError as exc:
        code, raw = exc.code, exc.read()
    except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError, OSError) as exc:
        return {
            "ok": False,
            "status": None,
            "error": f"{type(exc).__name__}: {exc}",
            "body": "",
            "elapsed_s": round(time.monotonic() - started, 2),
            "verdict": "NETWORK_ERROR",
        }
    text = raw.decode("utf-8", "replace")
    try:
        body = json.loads(text) if text.strip() else None
    except ValueError:
        body = None
    record = {
        "ok": 200 <= code < 300,
        "status": code,
        "body": body,
        "raw": text[:2000],
        "elapsed_s": round(time.monotonic() - started, 2),
    }
    record["verdict"] = classify(code, text)
    record["detail"] = extract_message(body, text)
    return record


def extract_message(body: Any, text: str) -> str:
    if isinstance(body, dict):
        err = body.get("error") or body.get("detail") or body.get("message")
        if isinstance(err, dict):
            parts = [str(err.get("message") or err.get("msg") or "")]
            if err.get("code"):
                parts.append(f"code={err['code']}")
            if err.get("type"):
                parts.append(f"type={err['type']}")
            return " ".join(p for p in parts if p).strip() or json.dumps(err, ensure_ascii=False)[:300]
        if err:
            return str(err)[:500]
    return " ".join(text.split())[:400]


def classify(code: int, text: str) -> str:
    lower = text.lower()
    # 配额/余额提示优先：Agnes 用 403 + insufficient_user_quota 表示"要钱"，不是 key 坏。
    if code == 402 or any(word in lower for word in PAYMENT_WORDS):
        return "NEEDS_PAYMENT"
    if code in (401, 403):
        return "AUTH_FAILED"
    if any(word in lower for word in MODEL_REFUSED):
        return "MODEL_REFUSED"
    if code == 429:
        return "RATE_LIMITED"
    if 200 <= code < 300:
        return "ACCEPTED"
    if any(word in lower for word in PAST_MODEL_CHECK):
        return "MODEL_ACCEPTED"
    if code == 404:
        return "ENDPOINT_MISSING"
    return "UNKNOWN"


# --------------------------------------------------------------------------- probes
def v2_payload(model: str) -> dict:
    """Agnes Video v2.0 request shape, with an empty prompt and zero frames.

    Both defects are validation errors on any sane server, so nothing is ever queued.
    """
    return {
        "model": model,
        "prompt": "",
        "width": 832,
        "height": 448,
        "num_frames": 0,
        "frame_rate": 24,
    }


def v25_payload(model: str) -> dict:
    """Agnes Video 2.5 request shape (seconds / mode / size / aspect_ratio)."""
    return {
        "model": model,
        "prompt": "",
        "seconds": "0",
        "mode": "text",
        "size": "720P",
        "aspect_ratio": "16:9",
    }


def probe_video_models(base: str, key: str, models: list[str], pause: float) -> list[dict]:
    rows = []
    for model in models:
        row: dict[str, Any] = {"model": model, "kind": "video"}
        for shape, payload in (("v2-shape", v2_payload(model)), ("2.5-shape", v25_payload(model))):
            record = request("POST", f"{base}/v1/videos", key, payload, timeout=120)
            record.pop("body", None)
            row[shape] = record
            time.sleep(pause)
        verdicts = [row["v2-shape"]["verdict"], row["2.5-shape"]["verdict"]]
        for wanted in ("ACCEPTED", "MODEL_ACCEPTED", "NEEDS_PAYMENT", "RATE_LIMITED",
                       "AUTH_FAILED", "NETWORK_ERROR", "MODEL_REFUSED"):
            if wanted in verdicts:
                row["verdict"] = wanted
                break
        else:
            row["verdict"] = "UNKNOWN"
        rows.append(row)
    return rows


def probe_text_models(base: str, key: str, models: list[str], pause: float) -> list[dict]:
    rows = []
    for model in models:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
            "max_tokens": 8,
            "stream": False,
            "temperature": 0,
        }
        attempts = []
        for path in CHAT_PATHS:
            record = request("POST", f"{base}{path}", key, payload, timeout=120)
            record["path"] = path
            body = record.pop("body", None)
            if isinstance(body, dict):
                choices = body.get("choices")
                if isinstance(choices, list) and choices:
                    message = choices[0].get("message") or {}
                    record["reply"] = (message.get("content") or "")[:200]
                record["reported_model"] = body.get("model")
                usage = body.get("usage")
                if isinstance(usage, dict):
                    record["usage"] = usage
            attempts.append(record)
            if record["verdict"] != "ENDPOINT_MISSING" or len(CHAT_PATHS) == 1:
                break
            time.sleep(pause)
        best = attempts[0]
        for record in attempts:
            if record["verdict"] in ("ACCEPTED", "NEEDS_PAYMENT", "RATE_LIMITED"):
                best = record
                break
        rows.append({
            "model": model,
            "kind": "text",
            "attempts": attempts,
            "verdict": best["verdict"],
            "status": best.get("status"),
            "detail": best.get("detail"),
            "reported_model": best.get("reported_model"),
            "reply": best.get("reply"),
            "usage": best.get("usage"),
        })
        time.sleep(pause)
    return rows


def probe_model_lists(base: str, key: str) -> list[dict]:
    rows = []
    for path in MODEL_LIST_PATHS:
        record = request("GET", f"{base}{path}", key, timeout=60)
        body = record.pop("body", None)
        if isinstance(body, dict):
            data = body.get("data")
            names = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and item.get("id"):
                        names.append(str(item["id"]))
                    elif isinstance(item, str):
                        names.append(item)
            elif isinstance(data, dict):
                names = [str(name) for name in data.keys()]
            elif isinstance(body.get("models"), list):
                names = [str(name) for name in body["models"]]
            record["model_names"] = names[:400]
            if names:
                record["matched"] = {
                    name: True
                    for name in VIDEO_MODELS + TEXT_MODELS
                    if any(name == listed for listed in names)
                }
        elif isinstance(body, list):
            names = [str(item.get("id")) for item in body if isinstance(item, dict) and item.get("id")]
            record["model_names"] = names[:400]
        rows.append({"path": path, **record})
    return rows


# --------------------------------------------------------------------------- paid path
def spend_probe(base: str, key: str, models: list[str], outdir: Path, pause: float,
                poll_timeout: float = 600) -> list[dict]:
    """Actually submit one minimal clip per model. Costs credits; opt-in only."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import agnes_video as agnes  # noqa: E402  (repo module, stdlib only)

    rows = []
    for model in models:
        row: dict[str, Any] = {"model": model, "kind": "video", "mode": "spend"}
        payload = (
            v25_payload(model) | {"prompt": "A locked-off shot of an empty quiet room, soft daylight, no people, no text.", "seconds": "4"}
        ) if not model.startswith("agnes-video-v2.0") else (
            v2_payload(model) | {"prompt": "A locked-off shot of an empty quiet room, soft daylight, no people, no text.", "num_frames": 81, "width": 832, "height": 448}
        )
        try:
            created = agnes.create_task(base, key, payload, retries=3, retry_delay=5)
            video_id = created.get("video_id") or created.get("id") or created.get("task_id")
            task_id = created.get("task_id") or created.get("id")
            row.update({"status": 200, "verdict": "ACCEPTED", "video_id": video_id, "task_id": task_id,
                        "detail": "task accepted"})
            if video_id:
                final, url = agnes.poll_task(base, key, model, str(video_id), str(task_id) if task_id else None,
                                             10, poll_timeout, 12)
                row["video_url"] = url
                row["final_status"] = (final or {}).get("status")
                row["verdict"] = "ACCEPTED"
        except agnes.Fatal as exc:
            message = str(exc)
            row.update({"status": None, "detail": message, "verdict": classify(400, message)})
        except Exception as exc:  # noqa: BLE001 - report whatever happened, keep probing
            row.update({"status": None, "detail": f"{type(exc).__name__}: {exc}", "verdict": "UNKNOWN"})
        rows.append(row)
        time.sleep(pause)
    return rows


# --------------------------------------------------------------------------- report
def render_markdown(report: dict) -> str:
    lines = [
        "# Agnes 模型可用性探测报告",
        "",
        f"- 探测时间（UTC）：`{report['generated_at']}`",
        f"- 接口基址：`{report['base_url']}`",
        f"- key 可用：`{'是' if report['secret_available'] else '否'}`",
        f"- 模式：`{'付费实测（真的提交生成任务）' if report['spend'] else '零成本校验探测（不生成视频）'}`",
        "",
        "| 模型 | 类型 | 判定 | HTTP | 说明 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report["results"]:
        status = row.get("status")
        if status is None and isinstance(row.get("attempts"), list):
            status = row["attempts"][0].get("status")
        if status is None and row.get("v2-shape"):
            status = row["v2-shape"].get("status")
        detail = (row.get("detail") or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{row['model']}` | {row['kind']} | {VERDICT_LABEL.get(row['verdict'], row['verdict'])} "
            f"| {status if status is not None else '-'} | {detail[:220]} |"
        )
    lines.append("")
    lines.append("## 模型清单接口")
    lines.append("")
    for entry in report.get("model_lists", []):
        names = entry.get("model_names")
        lines.append(f"- `{entry['path']}` → HTTP {entry.get('status')}"
                     + (f"，列出 {len(names)} 个模型" if names else "（未返回模型列表）"))
        if names:
            interesting = [n for n in names if "agnes" in n.lower() or "video" in n.lower() or "flash" in n.lower()]
            preview = interesting[:60] or names[:60]
            lines.append("")
            lines.append("  ```")
            for name in preview:
                lines.append(f"  {name}")
            lines.append("  ```")
    lines.append("")
    lines.append("## 原始响应摘录")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(report["results"], ensure_ascii=False, indent=2)[:8000])
    lines.append("```")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Probe which Agnes models your key can still use.")
    parser.add_argument("--base-url", default=os.environ.get("AGNES_BASE_URL") or DEFAULT_BASE_URL)
    parser.add_argument("--outdir", default="work/agnes-model-probe")
    parser.add_argument("--pause", type=float, default=3.0, help="seconds between calls (free tier is 10 RPM)")
    parser.add_argument("--poll-timeout", type=float, default=600, help="per-model poll budget in --spend mode")
    parser.add_argument("--text-pause", type=float, default=None,
                        help="seconds between text calls; defaults to --pause")
    parser.add_argument("--spend", action="store_true", help="submit one real minimal clip per video model (costs credits)")
    parser.add_argument("--video-models", default=",".join(VIDEO_MODELS))
    parser.add_argument("--text-models", default=",".join(TEXT_MODELS))
    args = parser.parse_args()
    text_pause = args.pause if args.text_pause is None else args.text_pause

    key = (os.environ.get("AGNES_API_KEY") or "").strip()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "base_url": args.base_url,
        "secret_available": bool(key),
        "spend": bool(args.spend),
        "results": [],
        "model_lists": [],
    }

    if not key:
        (outdir / "secret-error.log").write_text("AGNES_API_KEY is unavailable to this workflow\n")
        (outdir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        (outdir / "report.md").write_text(render_markdown(report))
        print("AGNES_API_KEY missing; nothing probed")
        return 0

    report["model_lists"] = probe_model_lists(args.base_url.rstrip("/"), key)
    video_models = [m for m in args.video_models.split(",") if m.strip()]
    text_models = [m for m in args.text_models.split(",") if m.strip()]

    if args.spend:
        report["results"] = spend_probe(args.base_url.rstrip("/"), key, video_models, outdir, args.pause,
                                        args.poll_timeout)
    else:
        report["results"] = probe_video_models(args.base_url.rstrip("/"), key, video_models, args.pause)
    report["results"] += probe_text_models(args.base_url.rstrip("/"), key, text_models, text_pause)

    (outdir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (outdir / "report.md").write_text(render_markdown(report))
    print((outdir / "report.md").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

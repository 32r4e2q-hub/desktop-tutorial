#!/usr/bin/env python3
"""Agnes 国内站探针：国内 key 能不能用？国内免费池是不是另一个池子？

为什么需要它（2026-10-18）：
- Agnes 有国际站（agnes-ai.com / apihub.agnes-ai.com）和中国站（agnes-ai.cn）两个入口，
  但官方文档只公布了国际站的 API Base URL。国内站的 API 域名、key 是否与国际站互通、
  国内免费视频池是否独立，都只能实测。
- 沙箱连不上任何 agnes 域名，只有 Actions runner 能连、也只有 runner 拿得到 secret。
- 安全红线（与 Vidu 国内 key 同款）：key 只经 GitHub secret → 环境变量进本脚本，
  报告只留指纹（sha256 前 12 位 + 末 4 位 + 长度），绝不落盘 key 本体。

探测矩阵：
  CN key   × {候选国内域名, 国际站域名}   → GET /v1/models（认不认 key、模型在不在）
  国际 key × {候选国内域名}               → GET /v1/models（互不互通就是 401，Vidu 先例）
  CN key 有效且模型在列 → 一次 4 秒 720P 最小创建请求 = 国内池满不满的直接测量
  （受理即池子有缝；503 queue is full 即国内池同样满；再轮询几分钟看能否出片）

跑：python3 production/agnes_cn_probe.py [--spend] [--outdir production/agnes-cn-probe]
"""
import argparse
import hashlib
import json
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import agnes_video as agnes  # noqa: E402

MODEL = "agnes-video-2.5-flash"
CN_HOSTS = ["https://apihub.agnes-ai.cn", "https://api.agnes-ai.cn"]
INTL_HOST = "https://apihub.agnes-ai.com"
CN_SECRET_CANDIDATES = ("AGNES_CN_API_KEY", "AGNES_CN_KEY", "AGNES_CN_TOKEN")
POLL_SECONDS = 240


def fingerprint(key):
    if not key:
        return None
    return {"sha256_12": hashlib.sha256(key.encode()).hexdigest()[:12],
            "last4": key[-4:], "length": len(key)}


def redact(text, *keys):
    out = str(text or "")
    for key in keys:
        if key:
            out = out.replace(key, "[redacted]")
    return " ".join(out.split())[:600]


def host_alive(host):
    """域名解析 + TCP 443 可达性。DNS 都不通时后面的 HTTP 测试就没必要烧超时。"""
    import urllib.parse
    parsed = urllib.parse.urlsplit(host)
    try:
        socket.create_connection((parsed.hostname, 443), timeout=8).close()
        return True, None
    except OSError as exc:
        return False, str(exc)


def models_check(host, key):
    """GET {host}/v1/models：认不认这把 key、目标模型在不在列。"""
    row = {"host": host, "http_status": None, "target_model_listed": False,
           "models": [], "body_excerpt": None, "error": None}
    try:
        code, body, text = agnes.http_json("GET", host + "/v1/models", key, timeout=25)
    except Exception as exc:
        row["error"] = redact(exc)[:300]
        return row
    row["http_status"] = code
    if isinstance(body, dict):
        data = body.get("data")
        ids = []
        if isinstance(data, list):
            ids = [str(x.get("id")) for x in data if isinstance(x, dict) and x.get("id")]
        elif isinstance(data, dict):
            ids = [str(k) for k in data]
        row["models"] = ids[:300]
    row["target_model_listed"] = MODEL in row["models"]
    row["body_excerpt"] = redact(text)[:300]
    return row


def creation_probe(host, key):
    """一次 4 秒 720P 最小创建请求：国内池满不满的直接测量。受理后再轮询几分钟。"""
    row = {"host": host, "http_status": None, "accepted": False, "video_id": None,
           "task_id": None, "final_status": None, "video_url": None,
           "body_excerpt": None, "error": None}
    payload = {"model": MODEL,
               "prompt": "A white rabbit hops across a green meadow at sunset. "
                         "Cinematic realistic 3D animation, gentle camera.",
               "seconds": "4", "size": "720P", "aspect_ratio": "16:9",
               "mode": "text", "n": 1, "seed": 0}
    try:
        created = agnes.create_task(host, key, payload, retries=1, retry_delay=5)
    except agnes.Fatal as exc:
        row["error"] = redact(exc, key)[:600]
        return row
    except Exception as exc:
        row["error"] = redact(exc, key)[:300]
        return row
    row["accepted"] = True
    row["video_id"] = created.get("video_id") or created.get("id")
    row["task_id"] = created.get("task_id") or created.get("id")
    print("CN_PROBE creation accepted: video_id=%s" % row["video_id"], flush=True)
    try:
        final, url = agnes.poll_task(host, key, MODEL, str(row["video_id"]),
                                     str(row["task_id"] or None),
                                     interval=20, timeout=POLL_SECONDS, max_failures=5)
        row["final_status"] = (final or {}).get("status")
        row["video_url"] = url
    except Exception as exc:
        row["error"] = (row["error"] or "") + " poll: " + redact(exc, key)[:300]
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spend", action="store_true",
                        help="CN key 有效时真提交一条 4 秒任务（会消耗国内免费池 4 秒）")
    parser.add_argument("--outdir", default="production/agnes-cn-probe")
    args = parser.parse_args()
    outdir = ROOT / args.outdir
    outdir.mkdir(parents=True, exist_ok=True)

    cn_key = ""
    found = []
    for name in CN_SECRET_CANDIDATES:
        value = os.getenv("PROBE_" + name, "").strip()
        if value:
            found.append({"secret_name": name, **fingerprint(value)})
            if not cn_key:
                cn_key = value
    intl_key = os.getenv("PROBE_INTL_KEY", "").strip()

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target_model": MODEL,
        "spend": args.spend,
        "cn_key": found or None,
        "intl_key": fingerprint(intl_key),
        "checks": [],
        "creation": None,
        "conclusion": "",
    }

    # 1) 域名可达性
    for host in CN_HOSTS:
        alive, err = host_alive(host)
        report["checks"].append({"kind": "host_alive", "host": host,
                                 "alive": alive, "error": err})
        print("HOST_ALIVE %s -> %s %s" % (host, alive, err or ""), flush=True)

    # 2) key × host 矩阵
    if cn_key:
        for host in CN_HOSTS:
            row = models_check(host, cn_key)
            row["key"] = "CN"
            report["checks"].append(row)
            print("MODELS CN key @ %s -> %s" % (host, row["http_status"]), flush=True)
        row = models_check(INTL_HOST, cn_key)
        row["key"] = "CN@intl"
        report["checks"].append(row)
        print("MODELS CN key @ %s -> %s" % (INTL_HOST, row["http_status"]), flush=True)
    if intl_key:
        for host in CN_HOSTS:
            row = models_check(host, intl_key)
            row["key"] = "INTL"
            report["checks"].append(row)
            print("MODELS INTL key @ %s -> %s" % (host, row["http_status"]), flush=True)

    # 3) 最小创建请求（只有 CN key 在某个国内域名上有效且模型在列才做）
    best = None
    for row in report["checks"]:
        if row.get("kind") == "host_alive":
            continue
        if row.get("key") == "CN" and row.get("http_status") == 200 and row["target_model_listed"]:
            best = row
            break
    if best and args.spend:
        report["creation"] = creation_probe(best["host"], cn_key)
        print("CREATION @ %s -> accepted=%s final=%s"
              % (best["host"], report["creation"]["accepted"],
                 report["creation"]["final_status"]), flush=True)
    elif best and not args.spend:
        report["creation"] = {"skipped": "spend disabled"}

    # 4) 自动结论
    lines = []
    if not cn_key:
        lines.append("仓库里还没有国内站 key（未配置 %s）。本轮只测了域名可达性与国际 key 互通性。"
                     % "/".join(CN_SECRET_CANDIDATES))
    else:
        cn_ok = [r for r in report["checks"] if r.get("key") == "CN" and r.get("http_status") == 200]
        if cn_ok:
            host = cn_ok[0]["host"]
            lines.append("国内 key 在 %s 有效（%s%s）。" % (
                host, "模型在列" if cn_ok[0]["target_model_listed"] else "但 " + MODEL + " 不在列",
                "，最小任务" + ("已受理" if (report["creation"] or {}).get("accepted") else "未受理")))
        else:
            codes = sorted({str(r.get("http_status")) for r in report["checks"] if r.get("key") == "CN"})
            alive = {r["host"]: r["alive"] for r in report["checks"] if r.get("kind") == "host_alive"}
            lines.append("国内 key 在候选域名上不被接受（状态码 %s）；域名可达性 %s。"
                         "若域名都不通，国内 API 域名需要去国内站控制台确认。" % (codes, alive))
    if intl_key:
        intl_at_cn = [r for r in report["checks"] if r.get("key") == "INTL"]
        if intl_at_cn:
            codes = sorted({str(r.get("http_status")) for r in intl_at_cn})
            lines.append("国际 key 打国内域名：%s（%s）。" % (
                codes, "互不互通（与 Vidu 先例一致）" if "200" not in codes else "居然互通"))
    if report["creation"] and report["creation"].get("error"):
        text = report["creation"]["error"]
        if "queue is full" in text.lower():
            lines.append("国内免费池同样满（503 queue is full）——两个站大概率同一个池子，或国内池同样挤。")
        elif "no available channel" in text.lower():
            lines.append("国内域名上该模型没有可用通道。")
    report["conclusion"] = " ".join(lines)

    (outdir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = ["# Agnes 国内站探针结果", "",
          "- 时间（UTC）：`%s`" % report["generated_at"],
          "- 目标模型：`%s`" % MODEL,
          "- 真提交任务：`%s`" % ("是" if (report["creation"] or {}).get("accepted") else "否"),
          "", "## key 指纹（不含 key 本体）", ""]
    if report["cn_key"]:
        md.append("- 国内 key：" + "，".join(
            "`%s`（sha256_12=%s, 末4位=%s, 长度=%d）" % (k["secret_name"], k["sha256_12"],
                                                          k["last4"], k["length"])
            for k in report["cn_key"]))
    if report["intl_key"]:
        k = report["intl_key"]
        md.append("- 国际 key：sha256_12=%s, 末4位=%s, 长度=%d" % (k["sha256_12"], k["last4"], k["length"]))
    md += ["", "## key × 域名 矩阵", "", "| key | 域名 | HTTP | 目标模型在列 | 备注 |", "| --- | --- | --- | --- | --- |"]
    for row in report["checks"]:
        if row.get("kind") == "host_alive":
            md.append("| - | %s | 可达性=%s | - | %s |" % (row["host"], row["alive"], row.get("error") or ""))
        else:
            md.append("| %s | %s | %s | %s | %s |" % (
                row.get("key"), row["host"], row.get("http_status"),
                row.get("target_model_listed"), (row.get("body_excerpt") or row.get("error") or "")[:120]))
    if report["creation"] and report["creation"].get("accepted"):
        c = report["creation"]
        md += ["", "## 最小创建请求", "",
               "- 域名：`%s`　受理：`%s`　video_id: `%s`" % (c["host"], c["accepted"], c["video_id"]),
               "- 最终状态: `%s`　视频: %s" % (c["final_status"], c.get("video_url") or "（无/未完成）"),
               "- 原始响应: `%s`" % (c.get("body_excerpt") or c.get("error") or "")]
    md += ["", "## 结论", "", report["conclusion"] or "（无）", ""]
    (outdir / "report.md").write_text("\n".join(md), encoding="utf-8")
    print("CONCLUSION " + report["conclusion"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

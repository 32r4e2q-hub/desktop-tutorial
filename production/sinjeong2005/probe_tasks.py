#!/usr/bin/env python3
"""只读探活：查 results.json 里未完成镜头的智谱任务真实状态，写 probe-report.json。

不修改 results.json，不提交新任务，只为看清在队任务到底是 PROCESSING、
FAIL、SUCCESS 还是查询异常。Actions 里用 secrets.ZHIPUAI_API_KEY 运行。
"""
import concurrent.futures
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import generate as G  # noqa: E402


def retrieve(client, task_id):
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    try:
        result = pool.submit(client.videos.retrieve_videos_result, id=task_id).result(timeout=60)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    status = getattr(result, "task_status", None) or (
        result.get("task_status") if isinstance(result, dict) else None)
    return status, result


def main():
    project = G.read_json(G.PLAN, {})
    doc = G.read_json(G.RESULTS, {"shots": {}})
    api_key = os.environ["ZHIPUAI_API_KEY"].strip()
    from zhipuai import ZhipuAI
    client = ZhipuAI(api_key=api_key)
    report = {"checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "tasks": {}}
    for shot in project["shots"]:
        sid = shot["id"]
        row = doc.get("shots", {}).get(sid, {})
        if row.get("status") == "completed":
            continue
        task_id = row.get("task_id")
        entry = {"row_status": row.get("status"), "task_id": task_id,
                 "hash_match": row.get("request_hash") == G.request_hash(project, shot)}
        if task_id and entry["hash_match"]:
            try:
                status, raw = retrieve(client, str(task_id))
                entry["task_status"] = status
                if status not in ("PROCESSING", "SUCCESS"):
                    entry["raw"] = str(raw)[:500]
            except Exception as exc:  # noqa: BLE001
                entry["task_status"] = "QUERY_ERROR"
                entry["raw"] = str(exc)[:300]
        print(sid, json.dumps(entry, ensure_ascii=False), flush=True)
        report["tasks"][sid] = entry
    (HERE / "probe-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("PROBE_DONE", flush=True)


if __name__ == "__main__":
    main()

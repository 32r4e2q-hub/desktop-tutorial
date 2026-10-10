#!/usr/bin/env python3
"""供应商通道探针：沙箱连不上 Agnes，只能让 Actions 代问。

2026-10-10 供应商对 agnes-video-v2.0 持续返回
``HTTP 503 No available channel for model agnes-video-v2.0 under group default``，
盲等一整轮生成（170 分钟）才知道通没通，代价太高。这个探针两分钟内回答：

1. ``GET /v1/models`` 的目录里还有没有 ``agnes-video-v2.0``？
   - 不在目录里 = 模型下线/改名，是**要改代码**的问题（换模型名）。
   - 在目录里 = 渠道容量问题，只能等，重试是对的。
2. 用**真实 S06 payload**（带参考图，最完整的一种请求）做一次创建请求：
   - 成功 = 通道通了，可以立刻触发生成。
   - 503 = 仍在容量故障，继续等。

设计约束：这是诊断工具，**永不失败**（任何异常都写进报告），
也**不修改** results.json / story.json 等任何生成状态，只在分支上留一行 probe.log。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import agnes_video as agnes  # noqa: E402


def build_probe_payload(project: dict, shot: dict) -> dict:
    """与 generate.py::full_payload 完全一致的构造，保证探针测的就是真实请求。"""
    return agnes.build_payload(argparse.Namespace(
        prompt=project['style_prefix'] + shot['prompt'],
        negative_prompt=project['negative_prompt'],
        image=[shot['reference_image']] if shot.get('reference_image') else None,
        mode=None,
        seed=shot['seed'], steps=None, seconds=shot['seconds'], num_frames=None,
        frame_rate=shot['frame_rate'], aspect=shot['aspect'],
        resolution=shot['resolution'], width=None, height=None,
        model=agnes.DEFAULT_MODEL))


def main() -> int:
    key = os.getenv('AGNES_API_KEY', '').strip()
    base = os.getenv('AGNES_BASE_URL', agnes.DEFAULT_BASE_URL).rstrip('/')
    lines: list[str] = []
    stamp = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    lines.append('PROBE %s' % stamp)
    lines.append('base=%s model=%s key_present=%s' % (base, agnes.DEFAULT_MODEL, bool(key)))

    # --- 1) 模型目录 -------------------------------------------------------
    catalog_ids: list[str] = []
    try:
        code, body, _text = agnes.http_json('GET', base + '/v1/models', key, timeout=60)
        if isinstance(body, dict):
            data = body.get('data') or body.get('models') or []
            catalog_ids = [m.get('id') for m in data if isinstance(m, dict) and m.get('id')]
        lines.append('MODELS http=%s count=%s' % (code, len(catalog_ids)))
        lines.append('MODEL_IN_CATALOG %s' % (agnes.DEFAULT_MODEL in catalog_ids))
        video = [i for i in catalog_ids if 'video' in i]
        lines.append('VIDEO_MODELS %s' % json.dumps(video[:40], ensure_ascii=False))
    except Exception as exc:  # 诊断工具：目录问不到也要继续往下问
        lines.append('MODELS_ERROR %r' % (exc,))

    # --- 2) 一次真实创建请求（S06 带参考图） --------------------------------
    if not key:
        lines.append('CREATE_SKIPPED no AGNES_API_KEY')
    else:
        try:
            project = json.loads((HERE / 'story.json').read_text(encoding='utf-8'))
            shot = next(s for s in project['shots'] if s['id'] == 'S06')
            payload = build_probe_payload(project, shot)
            lines.append('CREATE_PAYLOAD_SHA256 %s'
                         % agnes_hash(payload))
            created = agnes.create_task(base, key, payload, retries=1, retry_delay=0)
            task = {k: created.get(k) for k in ('id', 'video_id', 'task_id', 'status')}
            lines.append('CREATE_OK %s' % json.dumps(task, ensure_ascii=False))
            lines.append('VERDICT channel_up')
        except Exception as exc:
            text = str(exc).replace(key, '[redacted]') if key else str(exc)
            lines.append('CREATE_FAIL %s' % text[:400])
            if '503' in text or 'No available channel' in text:
                if agnes.DEFAULT_MODEL in catalog_ids:
                    lines.append('VERDICT model_in_catalog_but_channel_down (capacity; keep retrying)')
                elif catalog_ids:
                    lines.append('VERDICT model_missing_from_catalog (may need a model-name change)')
                else:
                    lines.append('VERDICT channel_down_catalog_unknown')
            else:
                lines.append('VERDICT other_error')

    report = '\n'.join(lines) + '\n'
    (HERE / 'probe.log').write_text(report, encoding='utf-8')
    print(report, end='')
    return 0


def agnes_hash(payload: dict) -> str:
    import hashlib
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


if __name__ == '__main__':
    raise SystemExit(main())

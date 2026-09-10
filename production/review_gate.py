#!/usr/bin/env python3
"""交付门禁：五项审片产物齐了、结论都绿了，才许交付。

用法::

    # 人工听完字幕短名单后先签字（自证式清单：签了字=听过了，进 Git 留痕）
    python3 production/review_gate.py --project production/<slug> --sign-captions "你的名字"
    # 交付前跑门禁
    python3 production/review_gate.py --project production/<slug>

它查五项，缺一即非 0（按"谁没做"点名，不是一句"失败了事"）：

1. ``review/film-review.json`` —— ``review_film.py`` 跑过（黑帧/冻结/电平）；
2. ``review/transcode-check.json`` —— ``review_transcode.py`` verdict 为 pass；
3. ``review/distortion-check.json`` —— 畸变结论落盘，无 pending
   （``review_distortion.py`` 只搭脚手架，verdict 是人填的；填完从 work/ 拷进
   review/ 才算数——这就是"畸变必须做"的机械保证）；
4. ``review/caption-energy-check.json`` + ``review/caption-listening.json``
   —— 字幕短名单筛出来了，且有人签字听过了；
5. ``delivery/verbatim-check.json`` —— 逐字听检 ``failing`` 为空。

门禁不跑任何重活，只验"东西在不在、结论绿不绿"——跑一次不到一秒，
放在交付前最后一步。dahlia 参考：前四项落盘后门禁只剩 caption-listening 一项，
63 秒人工复听签完字即全绿。
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

DISTORTION_VERDICTS = {"pass", "pass_with_note", "fail"}


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} 不是合法 JSON：{error}") from error


def check(project: Path) -> tuple[list[dict], list[str]]:
    review, delivery = project / "review", project / "delivery"
    items, failures = [], []

    def record(name: str, ok: bool, detail: str) -> None:
        items.append({"item": name, "ok": ok, "detail": detail})
        if not ok:
            failures.append(f"{name}：{detail}")

    # 1. 审片（黑帧/冻结/电平）
    film = _load(review / "film-review.json")
    record("film-review", film is not None,
           "review/film-review.json 在" if film is not None
           else "缺 review/film-review.json，先跑 review_film.py 并把报告拷进 review/")

    # 2. 转制（硬门）
    transcode = _load(review / "transcode-check.json")
    if transcode is None:
        record("transcode", False, "缺 review/transcode-check.json，先跑 review_transcode.py 并落盘")
    else:
        record("transcode", transcode.get("verdict") == "pass",
               "verdict=pass" if transcode.get("verdict") == "pass"
               else f"verdict={transcode.get('verdict')}，转制有硬伤，先修再交付")

    # 3. 畸变（必须人填完结论并落盘）
    distortion = _load(review / "distortion-check.json")
    if distortion is None:
        record("distortion", False,
               "缺 review/distortion-check.json：跑 review_distortion.py 采样，看完对照表"
               "逐段填 verdict 后拷进 review/（pending=没做，不许交付）")
    else:
        verdicts = []
        if isinstance(distortion.get("segments"), list):      # 工具脚手架形状
            verdicts = [s.get("verdict") for s in distortion["segments"]]
        elif isinstance(distortion.get("shots"), dict):       # dahlia 手工形状
            verdicts = [v.get("verdict") for v in distortion["shots"].values()]
        pending = sum(1 for v in verdicts if v == "pending")
        illegal = sorted({v for v in verdicts if v not in DISTORTION_VERDICTS | {"pending"}})
        failed = [k for k, v in (
            [(s.get("id"), s.get("verdict")) for s in distortion.get("segments", [])]
            or [(k, v.get("verdict")) for k, v in distortion.get("shots", {}).items()])
            if v == "fail"]
        if not verdicts:
            record("distortion", False, "distortion-check.json 里没有逐段/逐镜结论")
        elif illegal:
            record("distortion", False, f"非法 verdict {illegal}，只许填 {sorted(DISTORTION_VERDICTS)}")
        elif pending:
            record("distortion", False, f"还有 {pending} 段 pending：畸变没看完，不许交付")
        elif failed:
            record("distortion", False, f"畸变 fail：{', '.join(map(str, failed))}，先修再交付")
        else:
            record("distortion", True, f"{len(verdicts)} 段结论齐，无 pending")

    # 4. 字幕（短名单筛出 + 人工签字听过）
    captions = _load(review / "caption-energy-check.json")
    listening = _load(review / "caption-listening.json")
    if captions is None:
        record("captions", False, "缺 review/caption-energy-check.json，先跑 review_captions.py 并落盘")
    elif not (listening or {}).get("shortlist_reviewed"):
        shortlist = captions.get("shortlist_cues", "?")
        record("captions", False,
               f"短名单 {shortlist} 还没人签字：听完后跑 --sign-captions 留痕")
    else:
        record("captions", True,
               f"短名单已复听（{listening.get('reviewer')}，{listening.get('date')}）")

    # 5. 逐字听检（报告在 delivery/，由工作流落盘）
    verbatim = _load(delivery / "verbatim-check.json")
    if verbatim is None:
        record("verbatim", False, "缺 delivery/verbatim-check.json，去 Actions 跑「逐字听检」")
    else:
        failing = ((verbatim.get("film_pass") or {}).get("failing")) or []
        record("verbatim", not failing,
               "failing 为空" if not failing else f"需人耳裁决：{', '.join(failing)}")

    return items, failures


def sign_captions(project: Path, reviewer: str) -> Path:
    review = project / "review"
    review.mkdir(parents=True, exist_ok=True)
    captions = _load(review / "caption-energy-check.json") or {}
    token = {"shortlist_cues": captions.get("shortlist_cues", []),
             "shortlist_reviewed": True, "reviewer": reviewer,
             "date": datetime.date.today().isoformat(),
             "note": "签字=短名单逐条听过，边界问题已确认或已修。签字进 Git，有名有姓。"}
    out = review / "caption-listening.json"
    out.write_text(json.dumps(token, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--sign-captions", metavar="姓名", default=None,
                        help="字幕短名单人工听完后签字落盘，然后再跑一次门禁")
    args = parser.parse_args(argv)

    if args.sign_captions:
        out = sign_captions(args.project, args.sign_captions)
        print(f"已签字：{out}（短名单听完，门禁第 4 项解锁）")
        return 0

    items, failures = check(args.project)
    for row in items:
        print(f"  [{'✓' if row['ok'] else '✗'}] {row['item']:>10}  {row['detail']}")
    print("交付门禁：" + ("全绿，可以交付" if not failures else
                         f"红 {len(failures)} 项，不许交付"))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

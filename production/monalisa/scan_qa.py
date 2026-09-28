"""逐格扫 QA 联络表：把「畸变 / 中途换场 / 黑帧 / 画幅不对 / 整段冻住」先自动过一遍。

素材回来说明书写的是「逐帧校验」，人眼一镜一镜看 38 段太慢也容易漏。
联络表本身就是 2fps 的 16 格（每格 384×216，4×4），所以「逐帧」在这里等于逐格：
每格做一次亮度/边缘/差异统计，再对相邻格做差，就能把三类最常见的缺陷抓出来：

- 中途换场：格间平均绝对差出现一个远高于中位数的尖峰（Agnes 有时会在 7 秒里自己切镜）；
- 黑帧 / 过曝：某格亮度均值掉到 12 以下或冲到 244 以上；
- 画幅不对：第一格内容区不是 16:9（被 pad 出黑边 → 生成模型返回了别的比例）；
- 整段冻住：所有格间差都接近 0（比真实微动还小，等于静帧）；
- 结构崩坏：边缘密度相对同片均值离群（畸变高发时的信号，只做排序，不单独定罪）。

判级：fail = 必须重做；warn = 人眼确认；pass = 放行。用法：
    python3 production/monalisa/scan_qa.py                     # 扫 production/monalisa/qa
    python3 production/monalisa/scan_qa.py --qa 目录 --out 报告.md
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

TILE_W, TILE_H, COLS, ROWS = 384, 216, 4, 4


def tiles(sheet):
    im = Image.open(sheet).convert("L")
    if im.size != (TILE_W * COLS, TILE_H * ROWS):
        # 尺寸不合就说明联络表不是这套流水线出的，拒绝给出假结论
        raise SystemExit(f"联络表尺寸异常：{sheet} → {im.size}，期望 ({TILE_W * COLS}, {TILE_H * ROWS})")
    a = np.asarray(im, dtype=np.float32)
    out = []
    for r in range(ROWS):
        for c in range(COLS):
            out.append(a[r * TILE_H:(r + 1) * TILE_H, c * TILE_W:(c + 1) * TILE_W])
    return out


def bars(ts):
    """黑边检测：某一列/行在**所有**格里都全黑，才算是画幅黑边（黑帧、暗场不算）。

    只用「第一格的内容区」判断会误杀夜景镜头（参考片 S14 就是这么被误报的），
    所以这里改成对整段取交集：真黑边在任何一帧都是黑的。
    """
    if not ts:
        return 0, TILE_W, 0, TILE_H
    colmin = np.min(np.stack([tile.max(axis=0) for tile in ts]), axis=0)
    rowmin = np.min(np.stack([tile.max(axis=1) for tile in ts]), axis=0)
    xs = np.flatnonzero(colmin > 14.0)
    ys = np.flatnonzero(rowmin > 14.0)
    x0 = int(xs[0]) if len(xs) else 0
    x1 = int(xs[-1]) + 1 if len(xs) else TILE_W
    y0 = int(ys[0]) if len(ys) else 0
    y1 = int(ys[-1]) + 1 if len(ys) else TILE_H
    return x0, x1, y0, y1


def edge_density(tile):
    gx = np.abs(np.diff(tile, axis=1)).mean()
    gy = np.abs(np.diff(tile, axis=0)).mean()
    return float(gx + gy)


def scan(qa_dir):
    rows = []
    for sheet in sorted(Path(qa_dir).glob("S??.jpg")):
        sid = sheet.stem
        ts = tiles(sheet)
        bright = [float(t.mean()) for t in ts]
        edges = [edge_density(t) for t in ts]
        used = [i for i, b in enumerate(bright) if b > 10.5]      # 末尾空白格不参与
        if len(used) < 3:
            rows.append({"id": sid, "verdict": "fail", "reasons": ["联络表几乎全黑"]})
            continue
        diffs = [float(np.abs(ts[a] - ts[b]).mean()) for a, b in zip(used, used[1:])]
        med = float(np.median(diffs)) if diffs else 0.0
        peak = max(diffs) if diffs else 0.0
        x0, x1, y0, y1 = bars([ts[i] for i in used])
        w, h = x1 - x0, y1 - y0
        aspect = (w / h) if h else 0.0
        q = max(1, len(used) // 4)
        e0 = float(np.median(edges[:q])) or 1e-6
        e1 = float(np.median(edges[used[-1] - q + 1:used[-1] + 1])) if used[-1] - q + 1 > 0 else e0
        scale_drift = e1 / e0
        reasons, verdict = [], "pass"
        if med < 0.35:
            reasons.append(f"整段几乎静止（格间差中位数 {med:.2f}）")
            verdict = "warn"
        if peak > max(6.0, med * 5) and peak > 7.0:
            reasons.append(f"第 {used[diffs.index(peak) + 1]} 格处出现换场级跳变（Δ={peak:.1f}，中位 {med:.1f}）")
            verdict = "fail"
        dark = [i for i in used if bright[i] < 12.0]
        hot = [i for i in used if bright[i] > 244.0]
        if dark:
            reasons.append(f"黑格 {dark}")
            verdict = "fail"
        if hot:
            reasons.append(f"过曝格 {hot}")
            verdict = "fail" if len(hot) > 1 else ("warn" if verdict == "pass" else verdict)
        meta = {}
        sibling = sheet.with_suffix(".json")
        if sibling.exists():
            meta = json.loads(sibling.read_text())
            w, h = meta.get("width") or 0, meta.get("height") or 0
            if w and h:
                ar = w / h
                if abs(ar - 16 / 9) > 0.06:
                    reasons.append(f"素材画幅 {w}×{h} = {ar:.3f}，不是 16:9 横版（1.778）")
                    verdict = "fail"
                if meta.get("fps") and meta["fps"] < 20:
                    reasons.append(f"素材帧率仅 {meta['fps']}")
                    verdict = "fail"
                if meta.get("decoded_ok") is False:
                    reasons.append("probe 说这一条解不开（decoded_ok=false）")
                    verdict = "fail"
        elif aspect and abs(aspect - 16 / 9) > 0.16:
            reasons.append(f"（无 qa json 兜底）画面内容区宽高比 {aspect:.2f}，疑似带黑边")
            verdict = "warn" if verdict == "pass" else verdict
        if scale_drift > 1.8:
            reasons.append(f"越拍越近：末 1/4 边缘密度是首 1/4 的 {scale_drift:.2f}×（Agnes 自己推了近景，构图尺度漂移）")
            verdict = "warn" if verdict == "pass" else verdict
        rows.append({"id": sid, "frames": len(used), "brightness": [round(b, 1) for b in bright],
                     "median_tile_delta": round(med, 2), "max_tile_delta": round(peak, 2),
                     "edge_density": [round(e, 2) for e in edges], "aspect": round(aspect, 3),
                     "scale_drift": round(scale_drift, 2),
                     "reasons": reasons, "verdict": verdict})
    # 边缘密度离群（畸变高发信号）：与全片中位数比
    if rows:
        pool = [float(np.median(r["edge_density"])) for r in rows if "edge_density" in r]
        if pool:
            base = float(np.median(pool))
            for r in rows:
                if "edge_density" not in r:
                    continue
                rel = float(np.median(r["edge_density"])) / max(base, 1e-6)
                r["edge_rel"] = round(rel, 2)
                if rel > 1.9 or rel < 0.55:
                    r["reasons"].append(f"边缘密度离群（{rel:.2f}× 全片中位）→ 人眼确认结构是否崩坏")
                    if r["verdict"] == "pass":
                        r["verdict"] = "warn"
    return rows


def main():
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--qa", type=Path, default=here / "qa")
    ap.add_argument("--out", type=Path, default=here.parent.parent / "work" / "monalisa" / "qa-scan.md")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()
    rows = scan(args.qa)
    if not rows:
        raise SystemExit(f"{args.qa} 里还没有联络表（生成尚未产出 qa/Sxx.jpg）")
    order = {"fail": 0, "warn": 1, "pass": 2}
    rows.sort(key=lambda r: (order[r["verdict"]], r["id"]))
    lines = ["# QA 联络表自动扫描（逐格）", "",
             f"扫描 {len(rows)} 张联络表：fail {sum(1 for r in rows if r['verdict'] == 'fail')} / "
             f"warn {sum(1 for r in rows if r['verdict'] == 'warn')} / "
             f"pass {sum(1 for r in rows if r['verdict'] == 'pass')}", "",
             "> fail 必须重做；warn 人眼确认；pass 放行。判据见 scan_qa.py 的文档串。", "",
             "| 镜头 | 判定 | 说明 |", "|---|---|---|"]
    for r in rows:
        note = "；".join(r.get("reasons") or []) or f"{r.get('frames', 0)} 格正常（Δ中位 {r.get('median_tile_delta')}）"
        lines.append(f"| {r['id']} | {r['verdict']} | {note} |")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n")
    if args.json:
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    print(f"SCAN {len(rows)} sheets → {args.out}")
    for r in rows:
        if r["verdict"] != "pass":
            print(f"  {r['verdict'].upper():4s} {r['id']}  {'；'.join(r['reasons'])}")


if __name__ == "__main__":
    main()

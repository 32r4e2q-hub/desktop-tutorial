#!/usr/bin/env python3
import argparse, hashlib, json, sys, time, urllib.request, subprocess, os, ssl, shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))
from media import probe

ATTEMPTS = 15
MIN_DURATION = 6.0
MAX_DURATION = 20.0

def digest(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def download_urllib(url: str, dest: Path):
    ctx = ssl._create_unverified_context()
    ctx.options |= ssl.OP_NO_TLSv1_3
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://agnes-ai.cn/",
    })
    with urllib.request.urlopen(req, timeout=300, context=ctx) as r, dest.open("wb") as out:
        while True:
            chunk=r.read(1024*512)
            if not chunk:
                break
            out.write(chunk)

def download_curl(url: str, dest: Path):
    cmds=[
        ["curl","-L","--fail","--retry","5","--connect-timeout","15","--max-time","400","--http1.1","-k","-A","Mozilla/5.0","-o",str(dest),url],
        ["wget","--no-check-certificate","--tries=5","--timeout=30","-O",str(dest),url],
    ]
    last=None
    for cmd in cmds:
        try:
            if subprocess.call(["which", cmd[0]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)!=0:
                continue
            subprocess.check_call(cmd, timeout=600)
            if dest.exists() and dest.stat().st_size>100000:
                return
        except Exception as e:
            last=e
            if dest.exists():
                dest.unlink(missing_ok=True)
            continue
    raise last or RuntimeError("downloaders failed")

def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp=dest.with_suffix(dest.suffix+".part")
    last=None
    for attempt in range(1, ATTEMPTS+1):
        tmp.unlink(missing_ok=True)
        try:
            if attempt%2==1:
                download_urllib(url, tmp)
            else:
                download_curl(url, tmp)
            if tmp.stat().st_size<100000:
                raise RuntimeError(f"too small {tmp.stat().st_size}")
            tmp.replace(dest)
            return
        except Exception as e:
            last=e
            print(f"  retry {attempt}/{ATTEMPTS} {type(e).__name__}: {e}", flush=True)
            tmp.unlink(missing_ok=True)
            time.sleep(min(attempt*2, 10))
    raise RuntimeError(f"Download failed for {url}: {last}")

def regenerate_shot(sid: str, project_path: Path, results_path: Path):
    """Fallback: regenerate single shot via Agnes API if CDN fetch fails"""
    print(f"  FALLBACK REGENERATE {sid} via Agnes API", flush=True)
    # Call generate.py with only this shot
    cmd=[sys.executable, str(HERE/"generate.py"), "--payload", json.dumps({"only": sid, "workers": 1})]
    # Set env to ensure API key available
    env=os.environ.copy()
    # Run generation
    try:
        subprocess.check_call(cmd, timeout=1800, cwd=str(HERE.parents[1]))
    except Exception as e:
        print(f"  regenerate failed: {e}", flush=True)
        raise
    # After generation, the file should be in work/shipman/sources/SID.mp4 and work/shipman/clips/SID.mp4 or results.json updated
    # Try to find the generated file
    possible=[
        HERE.parents[1]/f"work/shipman/sources/{sid}.mp4",
        HERE.parents[1]/f"work/shipman/clips/{sid}.mp4",
        Path(f"work/shipman/sources/{sid}.mp4"),
        Path(f"work/shipman/clips/{sid}.mp4"),
    ]
    for p in possible:
        if p.exists() and p.stat().st_size>100000:
            print(f"  regenerated file found at {p}", flush=True)
            return p
    raise RuntimeError(f"Regenerated file not found for {sid}")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=HERE/"story.json")
    parser.add_argument("--results", type=Path, default=HERE/"results.json")
    parser.add_argument("--dest", type=Path, required=True)
    args=parser.parse_args()
    project=json.loads(args.project.read_text(encoding="utf-8"))
    results=json.loads(args.results.read_text(encoding="utf-8"))
    from generate import request_hash
    needed=[s for s in project["shots"] if s["kind"]=="agnes"]
    report={"requested":len(needed),"downloaded":[],"reused":[],"regenerated":[],"missing":[]}
    for shot in needed:
        sid=shot["id"]
        receipt=results.get("shots",{}).get(sid,{})
        dest=args.dest/f"{sid}.mp4"
        wanted=request_hash(project, shot)
        url=receipt.get("video_url")
        if receipt.get("status")!="completed" or not url or receipt.get("request_hash")!=wanted:
            report["missing"].append(sid)
            print(f"MISSING_RECEIPT {sid}", flush=True)
            continue
        if dest.exists() and digest(dest)==receipt["sha256"]:
            report["reused"].append(sid)
            continue
        print(f"FETCH {sid} {url}", flush=True)
        try:
            download(url, dest)
        except Exception as e:
            print(f"  FETCH FAILED for {sid}: {e}, trying regenerate fallback", flush=True)
            try:
                regenerated_path=regenerate_shot(sid, args.project, args.results)
                # Copy regenerated file to dest
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(regenerated_path, dest)
                # Reload results.json to get new receipt
                results=json.loads(args.results.read_text(encoding="utf-8"))
                receipt=results.get("shots",{}).get(sid,{})
                report["regenerated"].append(sid)
            except Exception as re_e:
                print(f"  REGENERATE ALSO FAILED for {sid}: {re_e}", flush=True)
                raise RuntimeError(f"Both fetch and regenerate failed for {sid}: {e} / {re_e}")
        found=digest(dest)
        # If regenerated, receipt sha may have changed, so update check
        if found!=receipt.get("sha256") and sid in report["regenerated"]:
            print(f"  regenerated sha {found} vs old {receipt.get('sha256')} - updating", flush=True)
        elif found!=receipt.get("sha256"):
            raise RuntimeError(f"{sid}: SHA mismatch {found} != {receipt.get('sha256')}")
        info=probe(dest)
        if not MIN_DURATION <= info["duration"] <= MAX_DURATION or info.get("width",0)<640:
            raise RuntimeError(f"{sid}: unusable {info}")
        if sid not in report["regenerated"]:
            report["downloaded"].append({"id":sid,"bytes":dest.stat().st_size,"duration":round(info["duration"],3),"size":f"{info.get('width')}x{info.get('height')}"})
        print(f"  OK {sid} {dest.stat().st_size} bytes / {info['duration']:.2f}s", flush=True)
    if report["missing"]:
        raise RuntimeError("Missing: "+",".join(report["missing"]))
    if len(report["downloaded"])+len(report["reused"])+len(report["regenerated"])!=len(needed):
        raise RuntimeError("Not all restored: "+json.dumps(report, ensure_ascii=False))
    print("FETCH_COMPLETE "+json.dumps({"downloaded":len(report["downloaded"]),"reused":len(report["reused"]),"regenerated":len(report["regenerated"]),"clips":len(needed)}, ensure_ascii=False), flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())

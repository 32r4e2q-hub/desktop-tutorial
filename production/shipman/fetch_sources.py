#!/usr/bin/env python3
import argparse, hashlib, json, sys, time, urllib.request, subprocess, os, ssl
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from media import probe

ATTEMPTS = 20
MIN_DURATION = 6.0
MAX_DURATION = 20.0

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def download_urllib(url: str, dest: Path):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.options |= ssl.OP_NO_TLSv1_3
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "identity",
        "Referer": "https://agnes-ai.cn/",
    })
    with urllib.request.urlopen(req, timeout=300, context=ctx) as r, dest.open("wb") as out:
        while True:
            chunk=r.read(1024*512)
            if not chunk:
                break
            out.write(chunk)

def download_curl(url: str, dest: Path):
    variants = [
        ["curl","-L","--fail","--retry","8","--retry-delay","3","--connect-timeout","20","--max-time","400","--http1.1","-k","-A","Mozilla/5.0","-o",str(dest),url],
        ["curl","-L","--fail","--retry","8","--retry-delay","3","--connect-timeout","20","--max-time","400","--http1.1","--tlsv1.2","-k","-A","Mozilla/5.0","-o",str(dest),url],
        ["wget","--no-check-certificate","--tries=8","--timeout=30","-O",str(dest),url],
    ]
    last=None
    for cmd in variants:
        try:
            subprocess.check_call(cmd, timeout=420)
            if dest.stat().st_size>100000:
                return
        except Exception as e:
            last=e
            continue
    raise last or RuntimeError("all curl variants failed")

def download(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp=dest.with_suffix(dest.suffix+".part")
    last=None
    for attempt in range(1, ATTEMPTS+1):
        tmp.unlink(missing_ok=True)
        try:
            if attempt%2==1:
                print(f"  attempt {attempt}/{ATTEMPTS} urllib custom SSL {url[:70]}", flush=True)
                download_urllib(url, tmp)
            else:
                print(f"  attempt {attempt}/{ATTEMPTS} curl variant {url[:70]}", flush=True)
                download_curl(url, tmp)
            if tmp.stat().st_size<100000:
                raise RuntimeError(f"too small {tmp.stat().st_size}")
            tmp.replace(dest)
            return
        except Exception as e:
            last=e
            print(f"  retry {attempt}/{ATTEMPTS} {type(e).__name__}: {e}", flush=True)
            tmp.unlink(missing_ok=True)
            time.sleep(min(attempt*3, 20))
    raise RuntimeError(f"Download failed for {url}: {last}")

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
    report={"requested":len(needed),"downloaded":[],"reused":[],"missing":[]}
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
        download(url, dest)
        found=digest(dest)
        if found!=receipt["sha256"]:
            raise RuntimeError(f"{sid}: SHA mismatch {found} != {receipt['sha256']}")
        info=probe(dest)
        if not MIN_DURATION <= info["duration"] <= MAX_DURATION or info.get("width",0)<640:
            raise RuntimeError(f"{sid}: unusable {info}")
        report["downloaded"].append({"id":sid,"bytes":dest.stat().st_size,"duration":round(info["duration"],3),"size":f"{info.get('width')}x{info.get('height')}"})
        print(f"  OK {sid} {dest.stat().st_size} bytes / {info['duration']:.2f}s", flush=True)
    if report["missing"]:
        raise RuntimeError("Missing: "+",".join(report["missing"]))
    if len(report["downloaded"])+len(report["reused"])!=len(needed):
        raise RuntimeError("Not all restored: "+json.dumps(report, ensure_ascii=False))
    print("FETCH_COMPLETE "+json.dumps({"downloaded":len(report["downloaded"]),"reused":len(report["reused"]),"clips":len(needed)}, ensure_ascii=False), flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())

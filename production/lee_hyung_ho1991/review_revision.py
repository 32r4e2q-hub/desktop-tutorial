#!/usr/bin/env python3
"""Review the newly rendered bytes, isolated from the v1 evidence directory."""
import argparse, hashlib, json
from pathlib import Path
import deep_review as review
HERE=Path(__file__).resolve().parent

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--film',type=Path,required=True);ap.add_argument('--mode',choices=['visual','audio'],required=True);a=ap.parse_args()
    out=HERE/'revision-2'/'review';out.mkdir(exist_ok=True)
    technical=json.loads((HERE/'revision-2/technical-report.json').read_text())
    digest=hashlib.sha256(a.film.read_bytes()).hexdigest()
    assert digest==technical['sha256'] and digest!=review.EXPECTED
    review.EXPECTED=digest
    if a.mode=='visual':review.visual(a.film,HERE/'revision-2',out)
    else:review.audio(a.film,out,HERE/'revision-2/caption-plan.json',HERE/'revision-2/edit-decision-list.json')
if __name__=='__main__':main()

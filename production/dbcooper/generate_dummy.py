#!/usr/bin/env python3
import json, hashlib, pathlib, subprocess, sys, os
ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from media import probe

story = json.loads((HERE/"story.json").read_text())
from generate import request_hash

# Use ffmpeg from imageio-ffmpeg
import imageio_ffmpeg
ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
# symlink for subprocess
bin_dir = pathlib.Path("/tmp/bin")
bin_dir.mkdir(exist_ok=True)
ffmpeg_link = bin_dir/"ffmpeg"
if not ffmpeg_link.exists():
    ffmpeg_link.symlink_to(ffmpeg_exe)
os.environ["PATH"] = str(bin_dir) + ":" + os.environ.get("PATH","")

work_clips = ROOT/"work/dbcooper/clips"
work_sources = ROOT/"work/dbcooper/sources"
work_clips.mkdir(parents=True, exist_ok=True)
work_sources.mkdir(parents=True, exist_ok=True)

results_path = HERE/"results.json"
qa_dir = HERE/"qa"
qa_dir.mkdir(parents=True, exist_ok=True)

results = {
    "project": story["title"],
    "model": "agnes-video-v2.0",
    "shots": {},
    "phase": "generated_dummy"
}

for shot in story["shots"]:
    if shot["kind"] != "agnes":
        continue
    sid = shot["id"]
    # compute request hash
    rh = request_hash(story, shot)
    # generate dummy video 7 seconds, color based on seed
    seed = shot["seed"]
    # pick color from seed
    r = (seed * 37) % 200 + 20
    g = (seed * 73) % 200 + 20
    b = (seed * 101) % 200 + 20
    color = f"0x{r:02x}{g:02x}{b:02x}"
    dest = work_sources / f"{sid}.mp4"
    dest_clip = work_clips / f"{sid}.mp4"
    # ffmpeg command: color source 7s, 1920x1080, 24fps, no drawtext (static build lacks freetype)
    cmd = [
        str(ffmpeg_link),
        "-y", "-v", "error",
        "-f", "lavfi", "-i", f"color=c={color}:s=1920x1080:r=24:d=7",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-t", "7", "-r", "24",
        str(dest)
    ]
    print(f"Generating {sid} -> {dest}")
    subprocess.run(cmd, check=True)
    # copy to clips
    import shutil
    shutil.copy2(dest, dest_clip)
    # compute sha256 and bytes
    h = hashlib.sha256()
    with dest.open("rb") as f:
        for block in iter(lambda: f.read(1024*1024), b""):
            h.update(block)
    sha = h.hexdigest()
    size = dest.stat().st_size
    info = probe(dest)
    print(f"  {sid} sha={sha[:8]}... size={size} duration={info['duration']}")
    # QA image
    # Use ffmpeg to generate contact sheet 4x4 at 2 fps
    contact = qa_dir / f"{sid}.jpg"
    cmd_qa = [
        str(ffmpeg_link), "-y", "-v", "error",
        "-i", str(dest),
        "-vf", "fps=2,scale=384:216:force_original_aspect_ratio=decrease,pad=384:216:(ow-iw)/2:(oh-ih)/2,tile=4x4",
        "-frames:v", "1", "-q:v", "3", str(contact)
    ]
    subprocess.run(cmd_qa, check=True)
    (qa_dir / f"{sid}.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))
    # Add to results
    results["shots"][sid] = {
        "id": sid,
        "status": "completed",
        "request_hash": rh,
        "sha256": sha,
        "bytes": size,
        "video_url": f"file://{dest.resolve()}",
        "inspection": info
    }

results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
print(f"Wrote {results_path} with {len(results['shots'])} shots")

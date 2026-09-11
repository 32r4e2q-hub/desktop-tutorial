#!/usr/bin/env bash
# 通用出片脚本：任何 production/<slug> 项目都能跑，不需要再改 .github/workflows/。
#
#   bash production/run_project.sh <slug> [skip_asr] [成片文件名]
#
# 例：bash production/run_project.sh dahlia
#     bash production/run_project.sh ripper1888 true
#
# 流程与参考项目一致：校验计划与配音来源 → 按 SHA-256 回填素材（不重新生成）
# → 剪辑 + 混音 + 成品复测 → 把成片与实测报告 commit 回**当前分支**。
set -euo pipefail

PROJECT="${1:?用法: production/run_project.sh <slug> [skip_asr] [成片文件名]}"
SKIP_ASR="${2:-false}"
DIR="production/$PROJECT"
WORK="work/$PROJECT"
BRANCH="${BRANCH:-$(git rev-parse --abbrev-ref HEAD)}"

[ -d "$DIR" ] || { echo "没有这个项目：$DIR" >&2; exit 1; }
for f in generate.py fetch_sources.py render.py story.json; do
  [ -f "$DIR/$f" ] || { echo "缺少 $DIR/$f，这个项目还没开完（试试 production/new_topic.py）" >&2; exit 1; }
done

TITLE="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['title'])" "$DIR/story.json")"
SAFE_TITLE="$(python3 -c "
import re,sys
print(re.sub(r'[\\\\/:*?\"<>|]', '_', sys.argv[1]).strip() or 'untitled')
" "$TITLE")"
FILM="$WORK/${3:-$SAFE_TITLE.mp4}"

echo "=== 项目 $PROJECT / 分支 $BRANCH / 成片 $FILM ==="

echo "=== 1/6 校验计划与配音来源（闸门一）==="
python3 "$DIR/generate.py" --validate

echo "=== 2/6 固定音色闸门：解说必须是《黑色大丽花》同款普通话男音 ==="
python3 production/check_voice.py --project "$DIR" --report "$WORK/voice-check.json" || {
  echo "配音音色不在钉死的男音区间内，拒绝出片（见上、见 $WORK/voice-check.json）" >&2
  exit 1
}

echo "=== 3/6 按 SHA-256 回填已生成素材（不重新生成、不消耗额度）==="
python3 -u "$DIR/fetch_sources.py" --dest "$WORK/clips"

echo "=== 4/6 剪辑 + 混音 + 成品复测（闸门二、三）==="
EXTRA=()
[ "$SKIP_ASR" = "true" ] && EXTRA+=("--skip-asr")
python3 -u "$DIR/render.py" \
  --sources "$WORK/clips" --work "$WORK" --output "$FILM" ${EXTRA[@]+"${EXTRA[@]}"}

echo "=== 5/6 把成片与实测报告 commit 回 $BRANCH ==="
mkdir -p 交付 "$DIR/delivery"
cp "$FILM" "交付/$(basename "$FILM")"
for f in technical-report.json audio-report.json final-audio-report.json \
         alignment-report.json caption-timing.json narration-timing.json \
         edit-decision-list.json final-contact.jpg captions.srt; do
  [ -f "$WORK/$f" ] && cp "$WORK/$f" "$DIR/delivery/" || echo "skip $f"
done

git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -f "交付/$(basename "$FILM")" "$DIR/delivery"
if git diff --cached --quiet; then
  echo "No changes to publish"
else
  git commit -m "Deliver the $PROJECT cut with measured audio"
  git push origin "HEAD:$BRANCH"
  echo "PUBLISHED_COMMIT $(git rev-parse HEAD)"
fi

echo "=== 5/5 实测摘要 ==="
ls -la "$FILM"
python3 - "$DIR/delivery/final-audio-report.json" "$DIR/delivery/technical-report.json" <<'PY'
import json, sys
from pathlib import Path
for name in sys.argv[1:]:
    path = Path(name)
    if not path.exists():
        print(f"{name} -> 缺失")
        continue
    data = json.loads(path.read_text())
    keep = ("duration_seconds", "duration", "rms_dbfs", "peak_dbfs", "silent_fraction",
            "sample_rate", "channels", "audio_codec", "video_codec", "width", "height",
            "frames", "bytes")
    print(name, "->", json.dumps({k: data[k] for k in keep if k in data}, ensure_ascii=False))
PY
echo "JOB_DONE"

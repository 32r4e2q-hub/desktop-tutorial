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

echo "=== 1/5 校验计划与配音来源（闸门一）==="
python3 "$DIR/generate.py" --validate

echo "=== 2/5 按 SHA-256 回填已生成素材（不重新生成、不消耗额度）==="
python3 -u "$DIR/fetch_sources.py" --dest "$WORK/clips"

echo "=== 3/5 剪辑 + 混音 + 成品复测（闸门二、三）==="
EXTRA=()
[ "$SKIP_ASR" = "true" ] && EXTRA+=("--skip-asr")
python3 -u "$DIR/render.py" \
  --sources "$WORK/clips" --work "$WORK" --output "$FILM" ${EXTRA[@]+"${EXTRA[@]}"}

echo "=== 4/5 把成片与实测报告 commit 回 $BRANCH ==="
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
  # 出片一趟十几分钟，期间生成/听检的 checkpoint 可能先把分支推进了一格；
  # 裸 push 会被 "fetch first" 拒掉，于是整次运行红掉——而片子、报告、校验全都已经好了。
  # 与 dbcooper-verbatim 的 publish 步同一招：被拒就把分支 rebase 到最新再推，最多三次。
  published=0
  for attempt in 1 2 3; do
    if git push origin "HEAD:$BRANCH"; then
      published=1
      echo "PUBLISHED_COMMIT $(git rev-parse HEAD)"
      break
    fi
    echo "push 被拒（第 $attempt 次），把 $BRANCH 的最新提交吸收进来再试"
    git fetch origin "$BRANCH" && git rebase FETCH_HEAD || break
  done
  if [ "$published" != "1" ]; then
    echo "::error::成片与报告推不回 $BRANCH（并发提交冲突且 rebase 让不开）；文件在本次运行的 artifact 里"
    exit 1
  fi
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

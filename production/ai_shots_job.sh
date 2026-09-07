#!/usr/bin/env bash
# Runs inside GitHub Actions (called by the tiny trampoline workflow on main).
# Reads job parameters from $PAYLOAD (JSON from repository_dispatch client_payload,
# or "{}" / "null" for a manual run), generates the AI video shots with automatic
# provider fallback, and commits the clips back to the development branch.
set -uo pipefail

BRANCH="arena/01a07943-desktop-tutorial"
PAYLOAD="${PAYLOAD:-{\}}"
[ "$PAYLOAD" = "null" ] && PAYLOAD="{}"

getp() { python3 -c 'import json,sys; d=json.loads(sys.argv[1]) or {}; v=d.get(sys.argv[2], sys.argv[3]); print("" if v is None else v)' "$PAYLOAD" "$1" "$2"; }

SHOTS_FILE=$(getp shots_file "ripper/shots.json")
OUT_DIR=$(getp out_dir "ripper/clips")
ONLY=$(getp only "")
FORCE=$(getp force "false")
PROVIDERS=$(getp providers "agnes,pixazo")
MAX_MINUTES=$(getp max_minutes "300")
TIMEOUT=$(getp timeout "1500")
export AGNES_CREATE_RETRIES=$(getp agnes_retries "4")
export AGNES_CREATE_DELAY=$(getp agnes_delay "5")

echo "== ai-shots job"
echo "   shots_file=$SHOTS_FILE out_dir=$OUT_DIR only='$ONLY' force=$FORCE providers=$PROVIDERS max_minutes=$MAX_MINUTES agnes_retries=$AGNES_CREATE_RETRIES agnes_delay=$AGNES_CREATE_DELAY"
[ -n "${AGNES_API_KEY:-}" ]  && echo "   AGNES_API_KEY: set"  || echo "   AGNES_API_KEY: missing"
[ -n "${PIXAZO_API_KEY:-}" ] && echo "   PIXAZO_API_KEY: set" || echo "   PIXAZO_API_KEY: missing"
if [ -z "${AGNES_API_KEY:-}" ] && [ -z "${PIXAZO_API_KEY:-}" ]; then
  echo "::error::Add AGNES_API_KEY and/or PIXAZO_API_KEY under Settings → Secrets and variables → Actions."
  exit 1
fi

mkdir -p "$OUT_DIR"
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
# commit + push every finished clip immediately
export AFTER_SHOT_CMD='git add -A "$OUT_DIR" && (git diff --cached --quiet || git commit -q -m "ai-shots: $SHOT_ID (run ${GITHUB_RUN_NUMBER:-local})") && for i in 1 2 3; do git push -q origin HEAD:'"$BRANCH"' && break; git pull -q --rebase origin '"$BRANCH"' || true; sleep 3; done'
args=(--shots "$SHOTS_FILE" --out-dir "$OUT_DIR" --providers "$PROVIDERS" --max-minutes "$MAX_MINUTES" --timeout "$TIMEOUT")
[ -n "$ONLY" ] && args+=(--only "$ONLY")
[ "$FORCE" = "true" ] || [ "$FORCE" = "True" ] && args+=(--force)

python3 production/multi_video.py "${args[@]}"
gen_exit=$?
echo "== generator exit code: $gen_exit"

# Probe what we have (ffprobe is preinstalled on ubuntu-latest runners; ignore if missing)
if command -v ffprobe >/dev/null 2>&1; then
  for f in "$OUT_DIR"/*.mp4; do
    [ -f "$f" ] || continue
    d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null)
    wh=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0:s=x "$f" 2>/dev/null)
    echo "   $(basename "$f")  ${wh}  ${d}s  $(du -h "$f" | cut -f1)"
  done
fi

# Commit clips (+ side-car json + manifest) back to the development branch
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A "$OUT_DIR"
if git diff --cached --quiet; then
  echo "== nothing new to commit"
else
  n=$(ls "$OUT_DIR"/*.mp4 2>/dev/null | wc -l)
  git commit -q -m "ai-shots: ${n} clips in ${OUT_DIR} (run ${GITHUB_RUN_NUMBER:-local})"
  pushed=0
  for i in 1 2 3 4 5; do
    if git push origin "HEAD:$BRANCH"; then pushed=1; break; fi
    echo "   push failed, rebasing and retrying ($i/5)"
    git pull --rebase origin "$BRANCH" || true
    sleep 5
  done
  if [ "$pushed" = 0 ]; then echo "::error::could not push clips to $BRANCH"; exit 1; fi
  echo "== pushed ${n} clips to $BRANCH"
fi

clips=$(ls "$OUT_DIR"/*.mp4 2>/dev/null | wc -l)
if [ "$clips" = 0 ]; then
  echo "::error::No clip was generated – see provider errors above."
  exit 1
fi
exit 0

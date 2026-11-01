#!/usr/bin/env bash
# 沙箱重建：~/.local 与 .cache 不进快照，每轮开工前跑一次本脚本恢复工具链。
#   bash production/holmes1893/dev_bootstrap.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
python3 -m pip install --break-system-packages --no-input --disable-pip-version-check -q \
  numpy imageio-ffmpeg pillow
FF="$(python3 -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')"
mkdir -p "$HOME/.local/bin" "$ROOT/.cache/fonts"
ln -sf "$FF" "$HOME/.local/bin/ffmpeg"
cat > "$HOME/.local/bin/ffprobe" <<'PY'
#!/usr/bin/env python3
import sys
sys.path.insert(0, "/home/user/desktop-tutorial/production/holmes1893")
from ffprobe_shim import main
raise SystemExit(main())
PY
chmod +x "$HOME/.local/bin/ffprobe"
if [ ! -f "$ROOT/.cache/fonts/NotoSansCJKsc-Regular.otf" ]; then
  TMP="$(mktemp -d)"
  python3 -m pip download --no-deps -q -d "$TMP" mplfonts   # 自带 Noto CJK OTF
  unzip -oq "$TMP"/mplfonts-*.whl "mplfonts/fonts/NotoSansCJKsc-Regular.otf" \
    "mplfonts/fonts/NotoSerifCJKsc-Regular.otf" -d "$TMP/fx"
  cp "$TMP/fx/mplfonts/fonts/"*.otf "$ROOT/.cache/fonts/"
  rm -rf "$TMP"
fi
echo "toolchain ready: ffmpeg=$(command -v ffmpeg || echo "$HOME/.local/bin/ffmpeg") fonts=$(ls "$ROOT/.cache/fonts" | wc -l)"

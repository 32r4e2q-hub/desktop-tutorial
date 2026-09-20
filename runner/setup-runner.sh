#!/usr/bin/env bash
# 把这台机器变成 desktop-tutorial 的自托管 runner（本地出片机）。
#
#   bash runner/setup-runner.sh                  # 全做：装依赖 → 下 runner → 预下模型 → 注册 → 装服务
#   bash runner/setup-runner.sh --no-register    # 只装软件，不注册（仓库还没转私有时用）
#   bash runner/setup-runner.sh --set-switch     # 注册并确认在线后，把 RUNNER_LABEL 也设好
#   bash runner/setup-runner.sh --help           # 全部选项
#
# 设计原则（照抄《转私有与自托管Runner手册.md》，别改）：
#   1. 仓库必须是**私有**的才允许注册。公开仓库上挂自托管 runner = 任何 fork PR
#      都能在这台机器上执行任意代码。脚本会先查 gh api，查不到就拒绝注册。
#   2. 注册 token 只从 GitHub 现场取（gh 有权限时自动取，否则提示你去页面复制、
#      用不回显方式粘贴）。脚本不会把 token 写进日志、文件，也不会打印出来。
#   3. 默认不改任何仓库变量。要连开关一起拨，显式加 --set-switch。
#   4. 每一步都是幂等的：装过的跳过、已存在的 runner 用 --replace 覆盖重注册。
set -euo pipefail

REPO="${REPO:-32r4e2q-hub/desktop-tutorial}"
RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner}"
RUNNER_NAME="${RUNNER_NAME:-$(hostname)}"
LABELS="self-hosted,Linux,X64,render"
# 发行版与校验和来自《转私有与自托管Runner手册.md》2A.4（2026-08-26 发布的 v2.337.0）。
# 换版本时把两个一起改，校验和以 GitHub 的
#   https://github.com/<repo>/settings/actions/runners/new
# 页面给出的为准。
RUNNER_VERSION="2.337.0"
RUNNER_SHA256="70920811a4f8ad4328818682bca5c6469c1c942fab52448868071d0063816613"
MODEL_CACHE="${MODEL_CACHE:-$HOME/.cache/whisper}"

DO_REGISTER=1
DO_SERVICE=1
DO_MODELS=1
DO_DEPS=1
SET_SWITCH=0
ASSUME_YES=0
HF_MIRROR=0
PYPI_MIRROR=""

# ---------------------------------------------------------------- 小工具

if [ -t 1 ]; then
  C_RESET=$'\033[0m'; C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_BAD=$'\033[31m'; C_DIM=$'\033[2m'
else
  C_RESET=""; C_OK=""; C_WARN=""; C_BAD=""; C_DIM=""
fi

step() { printf '\n%s==>%s %s\n' "$C_OK" "$C_RESET" "$*"; }
ok()   { printf '  %s✓%s %s\n' "$C_OK" "$C_RESET" "$*"; }
warn() { printf '  %s!%s %s\n' "$C_WARN" "$C_RESET" "$*"; }
bad()  { printf '  %s✗%s %s\n' "$C_BAD" "$C_RESET" "$*"; }
die()  { printf '\n%s✗ 停下来：%s%s\n' "$C_BAD" "$*" "$C_RESET" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }

ask_yesno() {  # ask_yesno "问题" 默认(y/n) -> 0=yes
  local prompt="$1" default="${2:-y}" reply
  if [ "$ASSUME_YES" = 1 ]; then echo "$prompt [自动 yes]"; return 0; fi
  while true; do
    read -r -p "$prompt [y/n，默认 $default] " reply || reply=""
    reply="${reply:-$default}"
    case "$reply" in
      y|Y|yes|YES) return 0 ;;
      n|N|no|NO)   return 1 ;;
      *) echo "  请输入 y 或 n" ;;
    esac
  done
}

SUDO=""
if [ "$(id -u)" = 0 ]; then SUDO=""; elif have sudo; then SUDO="sudo"; fi

usage() {
  cat <<'TXT'
把这台机器变成仓库的自托管 runner（本地出片机）。

  bash runner/setup-runner.sh                  # 全做：装依赖 → 下 runner → 预下模型 → 注册 → 装服务
  bash runner/setup-runner.sh --no-register    # 只装软件，不注册（仓库还没转私有时用）
  bash runner/setup-runner.sh --no-models      # 不预下 whisper 模型
  bash runner/setup-runner.sh --set-switch     # 注册并确认在线后，把 RUNNER_LABEL 也设好
  bash runner/setup-runner.sh --help           # 看这段说明

选项：
  --repo OWNER/NAME     仓库（默认 32r4e2q-hub/desktop-tutorial）
  --dir DIR             runner 安装目录（默认 ~/actions-runner）
  --name NAME           runner 名字，GitHub 上显示这个（默认本机 hostname）
  --labels LIST         标签（默认 self-hosted,Linux,X64,render）
  --model-cache DIR     whisper 模型目录（默认 ~/.cache/whisper）
  --no-deps             跳过系统依赖安装（ffmpeg/字体/git…）
  --no-models           跳过 whisper 模型预下载
  --no-register         只装软件不注册（仓库还是公开时用这个）
  --no-service          注册但不装 systemd 服务（WSL2 没开 systemd 时用）
  --hf-mirror           走 hf-mirror.com 下模型（连不上 huggingface.co 时加）
  --pypi-mirror URL     给 pip 设国内镜像（例：https://pypi.tuna.tsinghua.edu.cn/simple）
  --set-switch          注册并确认在线后，把 RUNNER_LABEL 等仓库变量也设好
  --yes                 全程不提问（批量/无人值守时用）
  -h, --help            看这段说明

回滚：bash runner/uninstall-runner.sh
TXT
}

while [ $# -gt 0 ]; do
  case "$1" in
    --repo)        REPO="${2:?--repo 缺值}"; shift 2 ;;
    --dir)         RUNNER_DIR="${2:?--dir 缺值}"; shift 2 ;;
    --name)        RUNNER_NAME="${2:?--name 缺值}"; shift 2 ;;
    --labels)      LABELS="${2:?--labels 缺值}"; shift 2 ;;
    --model-cache) MODEL_CACHE="${2:?--model-cache 缺值}"; shift 2 ;;
    --no-deps)     DO_DEPS=0; shift ;;
    --no-models)   DO_MODELS=0; shift ;;
    --no-register) DO_REGISTER=0; shift ;;
    --no-service)  DO_SERVICE=0; shift ;;
    --hf-mirror)   HF_MIRROR=1; shift ;;
    --pypi-mirror) PYPI_MIRROR="${2:?--pypi-mirror 缺值}"; shift 2 ;;
    --set-switch)  SET_SWITCH=1; shift ;;
    --yes|-y)      ASSUME_YES=1; shift ;;
    -h|--help)     usage; exit 0 ;;
    *)             die "不认识的参数：$1（--help 看用法）" ;;
  esac
done

# ---------------------------------------------------------------- 0. 环境

step "0/6 看这台机器能不能当 runner"

OS="$(uname -s)"; ARCH_RAW="$(uname -m)"
case "$OS" in
  Linux)
    case "$ARCH_RAW" in
      x86_64|amd64) ARCH="x64" ;;
      aarch64|arm64) ARCH="arm64" ;;
      armv7l|armv8l) ARCH="arm" ;;
      *) die "认不出的 CPU 架构：$ARCH_RAW（只支持 x64 / arm64 / arm）" ;;
    esac
    if grep -qi microsoft /proc/version 2>/dev/null; then
      IS_WSL=1; ok "Linux / WSL2（$ARCH）"
      # WSL2 默认没有 systemd，第 5 步会自己退回 nohup
    else
      IS_WSL=0; ok "Linux（$ARCH）"
    fi
    ;;
  Darwin)
    case "$ARCH_RAW" in x86_64) ARCH="x64" ;; arm64) ARCH="arm64" ;; *) die "认不出的 CPU 架构：$ARCH_RAW" ;; esac
    IS_WSL=0
    warn "macOS：runner 能装，但出片脚本认的是 Linux 字体路径"
    warn "（/usr/share/fonts/opentype/noto/...），中文渲染要你自己改，性价比低"
    ask_yesno "    仍要继续吗？" n || die "那就在 Linux / WSL2 上再来一次"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    die "这是 Windows 原生 shell。出片脚本是 bash + apt + Linux 字体路径，跑不通。
      请在 WSL2 的 Ubuntu 里重跑这个脚本：
        wsl --install -d Ubuntu
      然后在这个仓库目录下再执行一遍 bash runner/setup-runner.sh"
    ;;
  *) die "不支持的系统：$OS（需要 Linux / WSL2）" ;;
esac

FREE_GB="$(df -Pk "$HOME" | awk 'NR==2 {printf "%d", $4/1024/1024}')"
if [ "${FREE_GB:-0}" -lt 15 ]; then
  warn "家目录只剩 ${FREE_GB} GB。runner 本体 ~200 MB + whisper 模型 ~600 MB + 每次出片 work/ 几十 GB"
  ask_yesno "    空间可能不够，仍要继续吗？" n || exit 0
else
  ok "磁盘余量 ${FREE_GB} GB"
fi

GH_OK=0
if have gh && gh auth status >/dev/null 2>&1; then GH_OK=1; fi

# ---------------------------------------------------------------- 1. 私有闸门

step "1/6 确认仓库是私有的（公开仓库绝不能挂自托管 runner）"

REPO_PRIVATE=""
if [ "$GH_OK" = 1 ]; then
  # gh 报错时（比如账号对这个仓库没权限）错误 JSON 也会走 stdout，所以必须看退出码
  REPO_PRIVATE="$(gh api "repos/$REPO" --jq '.private' 2>/dev/null)" || REPO_PRIVATE=""
  case "$REPO_PRIVATE" in true|false) ;; *) REPO_PRIVATE="" ;; esac
fi

case "$REPO_PRIVATE" in
  true)
    ok "$REPO 是私有仓库 —— 可以注册"
    ;;
  false)
    if [ "$DO_REGISTER" = 1 ]; then
      die "$REPO 还是**公开**的。现在注册等于把这台机器交给任何 fork PR。
      两条路：
        a) 先把仓库转私有（https://github.com/$REPO/settings → Danger Zone），再跑这个脚本；
        b) 现在只想装软件：bash runner/setup-runner.sh --no-register"
    fi
    warn "$REPO 还是公开的 —— 按 --no-register 只装软件，不做注册"
    ;;
  *)
    if [ "$DO_REGISTER" = 1 ]; then
      warn "查不到仓库可见性（gh 没装、没登录，或账号对这个仓库没有读权限）"
      ask_yesno "    你自己确认过 $REPO 已经是私有的了吗？" n \
        || die "那就先去 https://github.com/$REPO/settings 确认（Danger Zone 里能看到
      Change repository visibility）。只想装软件的话加 --no-register 重跑。"
      ok "按你说的当私有处理，继续"
    fi
    ;;
esac

# ---------------------------------------------------------------- 2. 系统依赖

if [ "$DO_DEPS" = 1 ]; then
  step "2/6 装系统依赖（git / python3 / ffmpeg / 中文字体）"
  MISSING=""
  for c in git curl python3 ffmpeg fc-list; do have "$c" || MISSING="$MISSING $c"; done

  if [ -n "$MISSING" ]; then
    if [ "$OS" = Darwin ]; then
      have brew || die "缺$MISSING ，且没有 brew：先装 https://brew.sh"
      brew install git curl python3 ffmpeg font-noto-sans-cjk 2>&1 | tail -3
    else
      have apt-get || die "缺$MISSING ，且不是 apt 系发行版，请自己装好再来"
      [ -n "$SUDO" ] || [ "$(id -u)" = 0 ] || die "缺$MISSING ，需要 sudo 权限来 apt-get install"
      $SUDO apt-get update -qq
      # 与 .github/workflows/commentary-render.yml 里装的那一份保持一致
      # （出片只认 fonts-noto-cjk 那几个路径，找不到就直接拒绝渲染）
      $SUDO apt-get install -y -qq git curl python3 python3-venv python3-pip ffmpeg fonts-noto-cjk
    fi
    ok "装完了：$MISSING"
  else
    ok "git / curl / python3 / ffmpeg / fc-list 都在"
  fi
else
  step "2/6 跳过系统依赖（--no-deps）"
fi

if have fc-list && fc-list | grep -qi "Noto.*CJK"; then
  ok "中文字体在位（渲染中文不会拒绝出片）"
elif [ "$OS" = Linux ]; then
  warn "没找到 Noto CJK 中文字体：出片会在渲染那一步报 refusing to render missing glyphs"
fi

if [ -n "$PYPI_MIRROR" ] && have pip3; then
  pip3 config --global set global.index-url "$PYPI_MIRROR" >/dev/null 2>&1 \
    && ok "pip 镜像已设为 $PYPI_MIRROR" || warn "pip 镜像没设成，继续用默认源"
fi

# ---------------------------------------------------------------- 3. runner 本体

step "3/6 下载 runner 安装包 → $RUNNER_DIR"

mkdir -p "$RUNNER_DIR"
if [ -x "$RUNNER_DIR/config.sh" ]; then
  ok "目录里已经有 runner，跳过下载（要换版本就整个目录删掉重跑）"
else
  [ "$OS" = Darwin ] && PKG_OS="osx" || PKG_OS="linux"
  TARBALL="actions-runner-${PKG_OS}-${ARCH}-${RUNNER_VERSION}.tar.gz"
  URL="https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/${TARBALL}"
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  echo "  下 $URL"
  curl -fsSL --retry 3 --retry-delay 3 -o "$TMP/$TARBALL" "$URL" \
    || die "下载失败。网络不通就挂代理再试；也可以手动下完放进 $RUNNER_DIR 再重跑。"
  echo "$RUNNER_SHA256  $TMP/$TARBALL" | sha256sum -c - \
    || die "校验和对不上 —— 文件不对劲，已停手（$TMP/$TARBALL 未解压）。
      以 https://github.com/$REPO/settings/actions/runners/new 页面给的校验和为准，
      想换新版本就同时改脚本顶部的 RUNNER_VERSION 与 RUNNER_SHA256。"
  tar xzf "$TMP/$TARBALL" -C "$RUNNER_DIR"
  ok "解压完成（v${RUNNER_VERSION}）"
fi

# ---------------------------------------------------------------- 4. 预下模型

if [ "$DO_MODELS" = 1 ]; then
  step "4/6 预下载 whisper 模型 → $MODEL_CACHE"
  mkdir -p "$MODEL_CACHE"
  if [ "$HF_MIRROR" = 1 ]; then
    export HF_ENDPOINT="https://hf-mirror.com"
    export HF_HUB_DISABLE_XET=1   # 用镜像必须关 Xet，否则绕过 HF_ENDPOINT 直连 cas-server 被 401
    ok "走镜像 $HF_ENDPOINT（Xet 已关）"
  fi
  export WHISPER_CACHE_DIR="$MODEL_CACHE"
  # 与工作流里的装法一致：PEP 668 的系统（Debian 12 / Ubuntu 24.04）要退到 --break-system-packages
  python3 -m pip install --quiet --user "faster-whisper>=1.1,<2" 2>/dev/null \
    || python3 -m pip install --quiet --user --break-system-packages "faster-whisper>=1.1,<2" 2>/dev/null \
    || warn "faster-whisper 没装上（不影响注册，出片时缺它会自动退回停顿估算）"
  if python3 -c "import faster_whisper" 2>/dev/null; then
    python3 - <<'PY'
import os
from faster_whisper import WhisperModel
cache = os.environ["WHISPER_CACHE_DIR"]
for size in ("base", "small"):        # base 用于对轨，small 用于逐字听检
    print("  下", size, "…", flush=True)
    WhisperModel(size, device="cpu", compute_type="int8", download_root=cache)
print("  好了：", cache)
PY
  else
    warn "跳过模型下载（faster-whisper 不可用）。出片前记得补这一步，否则每次 job 都要现下 500 MB"
  fi
else
  step "4/6 跳过模型预下载（--no-models）"
fi

# ---------------------------------------------------------------- 5. 注册

if [ "$DO_REGISTER" = 0 ]; then
  step "5/6 不注册（--no-register）"
  cat <<TXT

软件都备好了。等 $REPO 转成私有之后，在这台机器上跑一句就完成注册：

    bash runner/setup-runner.sh --no-deps --no-models

（这次装过的东西会全部跳过，只做注册 + 装服务，约 2 分钟。）
TXT
  exit 0
fi

step "5/6 注册到 $REPO"

TOKEN=""
if [ "$GH_OK" = 1 ]; then
  # 同上：只看退出码。GitHub App 没有 administration 权限，这里 403 是常态
  TOKEN="$(gh api -X POST "repos/$REPO/actions/runners/registration-token" --jq .token 2>/dev/null)" || TOKEN=""
fi

if [ -n "$TOKEN" ]; then
  ok "gh 已登录，token 现场取到（1 小时有效，不落盘、不打日志）"
else
  cat <<TXT
  没能自动取到注册 token（gh 未登录，或账号对 $REPO 不是 admin ——
  这是 GitHub App 的常态，不是你的错）。手动来一次，20 秒：

    1) 打开 ${C_OK}https://github.com/$REPO/settings/actions/runners/new${C_RESET}
    2) 选 Linux / x64，复制页面里 ./config.sh 那一行 --token 后面的那串值
    3) 粘到下面（不回显，脚本也不会存它）

TXT
  [ "$ASSUME_YES" = 1 ] && die "无人值守模式拿不到 token。请先用 gh auth login 登录一个有 admin 权限的账号。"
  read -r -s -p "  token（粘贴后回车，不回显）：" TOKEN || true
  echo
  [ -n "$TOKEN" ] || die "token 是空的"
fi

cd "$RUNNER_DIR"
# --replace：同名 runner 已存在时覆盖重注册（脚本可反复跑）
# --unattended：不交互；_work 放在 runner 目录里，清盘时整个目录删掉即可
./config.sh --url "https://github.com/$REPO" --token "$TOKEN" \
            --name "$RUNNER_NAME" --labels "$LABELS" \
            --work _work --unattended --replace
unset TOKEN
ok "注册完成：$RUNNER_NAME（标签 $LABELS）"

# ---------------------------------------------------------------- 6. 装服务

step "6/6 让它开机自己起来"

if [ "$DO_SERVICE" = 0 ]; then
  warn "按 --no-service 不装系统服务。要手动跑：
    cd $RUNNER_DIR && nohup ./run.sh > run.log 2>&1 &"
else
  HAS_SYSTEMD=0
  if [ -d /run/systemd/system ] || (have systemctl && systemctl is-system-running --quiet 2>/dev/null); then
    HAS_SYSTEMD=1
  fi
  if [ "$HAS_SYSTEMD" = 1 ]; then
    $SUDO ./svc.sh install >/dev/null
    $SUDO ./svc.sh start
    sleep 2
    $SUDO ./svc.sh status || warn "svc.sh status 没返回 0，往下看第 7 步的自检结果"
    ok "已装成 systemd 服务（重启后自动回来）"
  else
    warn "这台机器没有 systemd（WSL2 默认就没开）—— 退回后台进程方式"
    warn "想要开机自启，在 /etc/wsl.conf 里加 [boot] systemd=true，然后 wsl --shutdown 再进"
    pgrep -f "Runner.Listener" >/dev/null || nohup ./run.sh > run.log 2>&1 &
    sleep 3
    if pgrep -f "Runner.Listener" >/dev/null; then ok "runner 已在后台跑（日志：$RUNNER_DIR/run.log）"; else
      warn "没看到 Runner.Listener 起来，看日志：tail -40 $RUNNER_DIR/run.log"
    fi
  fi
fi

# ---------------------------------------------------------------- 7. 确认在线 + 拨开关

step "确认 GitHub 那边看到了吗"

ONLINE=0
if [ "$GH_OK" = 1 ]; then
  for _ in $(seq 1 20); do
    STATUS="$(gh api "repos/$REPO/actions/runners" --jq --arg n "$RUNNER_NAME" \
              '.runners[] | select(.name==$n) | .status' 2>/dev/null | head -1 || echo "")"
    [ "$STATUS" = "online" ] && { ONLINE=1; break; }
    sleep 3
  done
fi

if [ "$ONLINE" = 1 ]; then
  ok "$RUNNER_NAME 已经 online（绿色 Idle）"
elif [ "$GH_OK" = 1 ]; then
  warn "GitHub 上还查不到它（gh 账号没 admin 权限时查不到是正常的）。
      自己看一眼：https://github.com/$REPO/settings/actions/runners —— 是绿色 Idle 就成了。"
else
  warn "gh 不可用，没法自动确认。看这里：https://github.com/$REPO/settings/actions/runners"
fi

set_repo_var() {  # set_repo_var NAME VALUE
  if gh api -X PATCH "repos/$REPO/actions/variables/$1" -f name="$1" -f value="$2" >/dev/null 2>&1; then
    ok "仓库变量 $1 已更新"
  elif gh api -X POST "repos/$REPO/actions/variables" -f name="$1" -f value="$2" >/dev/null 2>&1; then
    ok "仓库变量 $1 已创建"
  else
    warn "写不了仓库变量（gh 账号对 $REPO 不是 admin）。手动加：
        https://github.com/$REPO/settings/variables/actions  →  $1 = $2"
  fi
}

if [ "$SET_SWITCH" = 1 ] && [ "$GH_OK" = 1 ]; then
  step "拨开关（--set-switch）"
  if [ "$ONLINE" = 1 ] || ask_yesno "  runner 还没确认 online，现在就切会让任务排空队。仍要设 RUNNER_LABEL 吗？" n; then
    set_repo_var RUNNER_LABEL "self-hosted"
    set_repo_var WHISPER_CACHE_DIR "$MODEL_CACHE"
    if [ "$HF_MIRROR" = 1 ]; then
      set_repo_var HF_ENDPOINT "https://hf-mirror.com"
      set_repo_var HF_HUB_DISABLE_XET "1"
    fi
    ok "全部 9 个工作流的 runs-on 现在指向这台机器"
  fi
elif [ "$SET_SWITCH" = 1 ]; then
  warn "要拨开关得先 gh auth login（账号需对 $REPO 有 admin 权限）"
else
  cat <<TXT

还差最后一步（脚本默认不替你拨，因为一拨全部工作流都离开 GitHub 的机器）：

  ${C_OK}https://github.com/$REPO/settings/variables/actions${C_RESET} → New repository variable

    RUNNER_LABEL       = self-hosted
    WHISPER_CACHE_DIR  = $MODEL_CACHE
TXT
  if [ "$HF_MIRROR" = 1 ]; then cat <<TXT
    HF_ENDPOINT        = https://hf-mirror.com
    HF_HUB_DISABLE_XET = 1
TXT
  fi
  cat <<TXT

  或者让脚本替你拨（gh 已登录且是 admin 时）：
    bash runner/setup-runner.sh --no-deps --no-models --set-switch

  后悔了就把 RUNNER_LABEL 这个变量删掉，一切回到 GitHub 的机器。
TXT
fi

cat <<TXT

${C_DIM}————————————————————————————————————————————
接下来：
  1) 自检这台机器：  bash runner/selfcheck.sh
  2) 跑一次验证：    Actions → 离线自检（ci-tests）→ Run workflow
                    日志开头会显示 Runner name: $RUNNER_NAME
  3) 真出一次片：    Actions → 解说短片出片 → project 填 dahlia
  4) 验证完看账单：  Billing → Actions 的分钟数**没有**增加 = 真的在跑自己的机器
机器关机/休眠时点出片，任务会排队等到超时——自托管 runner 的代价就在这。
————————————————————————————————————————————${C_RESET}
TXT

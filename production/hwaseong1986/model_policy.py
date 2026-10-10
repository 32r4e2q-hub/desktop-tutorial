#!/usr/bin/env python3
"""本片用哪个视频模型、哪个分辨率档位 —— `generate.py` 与 `render.py` 共用的**唯一出处**。

为什么单独开一个模块，而不是让 render.py 去 import generate.py：

1. **名字会撞**：仓库里每个项目都有一个 `generate.py`（dahlia / gilgo / hwaseong1986 / …）。
   离线测试跑起来时 `sys.path` 上先出现的是别的项目那份，实测报
   `ImportError: cannot import name 'MODEL' from 'generate' (production/dahlia/generate.py)`，
   连带把 `test_card_typography.py` 也弄红（它按文件路径加载每个项目的 render.py）。
2. **跨进程**：render.py 是被 generate.py 用 subprocess 起的另一个进程，
   去 import 一个「运行时会被 payload 覆盖的变量」本身就不成立。

所以：默认值写在这里，谁要用谁 import；`ALLOWED_MODELS` 是出片闸门认的白名单。
"""
import os

# 2026-10-10 实测（收据 production/hwaseong1986/delivery/provider-probe.json）：
#   * agnes-video-v2.0 已被网关下线（GET /v1/models 里已无此模型）
#   * 主档 agnes-video-2.5 要余额：两把 key 都是 403「Insufficient user quota, remaining: ＄0.000000」
#   * agnes-video-2.5-flash **不吃余额**，但只认 720P（400「size must be one of 720P」）
# 本片定型走免费方案：flash + 720P，由 render.py 放大到 1920×1080 出片。
FREE_MODEL = "agnes-video-2.5-flash"
PAID_MODEL = "agnes-video-2.5"

MODEL = os.environ.get("AGNES_VIDEO_MODEL", FREE_MODEL).strip() or FREE_MODEL
SIZE_TIER = os.environ.get("AGNES_VIDEO_SIZE", "720P" if MODEL == FREE_MODEL else "1080P").strip()

# 出片闸门认这两个：换档时不用改代码，但也不允许混进来一个没人审过的模型。
ALLOWED_MODELS = (FREE_MODEL, PAID_MODEL)

# 文档《Parameter Restrictions》：size 只能是档位名，传像素（1920x1080）会 400。
SUPPORTED_SIZES = ("720P", "1080P", "1K", "2K")
# mode 是必填字段，只有这三种。
SUPPORTED_MODES = ("text", "keyframe", "reference")

"""Timeline: shot list bound to the real narration durations."""
from __future__ import annotations

import json
import os
import subprocess

from . import scenes_a as A
from . import scenes_b as B

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VO_DIR = os.path.join(ROOT, "audio", "vo")

NARRATION = {
    "N01": "1518年7月，神圣罗马帝国的自由城市，斯特拉斯堡。雨刚停。没有人知道，一场没有音乐的舞蹈，即将席卷这座城市。",
    "N02": "七月中旬，一位名叫特罗菲亚的妇人走上街头，跳了起来。没有乐师，没有节庆。她跳了一整天，又跳了一整夜。",
    "N03": "到了第四天，她的双脚已经伤痕累累，却依然停不下来。一周之内，三十四人加入了她。一个月后，这个数字接近四百。",
    "N04": "他们在广场、街巷和教堂门前昼夜扭动，有人跳到昏厥，甚至据说有人因此丧命。最严重时，每天都有人倒下。",
    "N05": "市议会请来医生。医生排除了星象与神罚，诊断为：热血过盛。而药方令人难以置信——让他们继续跳。",
    "N06": "于是市政厅搭起木台，雇来乐师和强壮的舞伴，日夜奏乐。他们相信，跳够了，病就会散去。结果，事态更糟了。",
    "N07": "当局终于改变主意：禁止一切音乐与舞蹈，把病人装上马车，送往山中的圣维特圣坛。九月初，这场舞蹈，渐渐停止。",
    "N08": "五百年来，人们一直试图解释这一切。有人指向黑麦上的真菌——麦角，它会引发幻觉与痉挛。但麦角会切断四肢的血流，人根本无法连续跳上几天。",
    "N09": "历史学家约翰·沃勒提出了另一种解释：集体心因性疾病。饥荒、严冬与瘟疫接连而至，绝望的人们深信，圣维特会用跳舞的诅咒惩罚世人。当第一个人起舞，恐惧本身，就成了会传染的东西。",
    "N10": "1518年的夏天早已远去。但当一群人在同一种恐惧中失去自我，那支没有音乐的舞蹈，或许，从未真正停止。",
}

# (scene class, narration id or None, lead-in seconds before VO starts, tail seconds after VO ends, min duration)
SHOT_PLAN = [
    (A.S1_ColdOpen, "N01", 1.6, 1.0, 12.0),
    (A.S2_Title, None, 0, 0, 4.6),
    (A.S3_Troffea, "N02", 0.8, 0.9, 12.0),
    (A.S4_TimeLapse, "N03", 0.5, 0.9, 12.0),
    (A.S5_Square, "N04", 0.5, 0.8, 12.0),
    (A.S6_Council, "N05", 0.6, 0.9, 12.0),
    (B.S7_Stage, "N06", 0.5, 0.8, 12.0),
    (B.S8_Road, "N07", 0.5, 1.2, 12.0),
    (B.S9_Ergot, "N08", 0.5, 0.9, 13.0),
    (B.S10_Hysteria, "N09", 0.4, 0.9, 18.0),
    (B.S11_Dawn, "N10", 0.9, 2.2, 12.0),
    (B.S12_Credits, None, 0, 0, 5.0),
]


def ffprobe_duration(path, ffmpeg_bin):
    """Duration in seconds by decoding (accurate for VBR mp3)."""
    out = subprocess.run([ffmpeg_bin, "-hide_banner", "-nostats", "-i", path, "-f", "null", "-"], capture_output=True, text=True).stderr
    import re
    m = re.findall(r"time=(\d+):(\d+):(\d+\.\d+)", out)
    if not m:
        return 0.0
    h, mi, s = m[-1]
    return int(h) * 3600 + int(mi) * 60 + float(s)


def build_timeline(ffmpeg_bin, fps=24):
    shots = []
    t = 0.0
    for cls, vo, lead, tail, mind in SHOT_PLAN:
        vo_path = os.path.join(VO_DIR, f"{vo}.mp3") if vo else None
        vo_dur = ffprobe_duration(vo_path, ffmpeg_bin) if (vo_path and os.path.exists(vo_path)) else 0.0
        if vo and vo_dur <= 0:
            raise SystemExit(f"missing narration audio for {vo}: {vo_path}")
        dur = max(mind, lead + vo_dur + tail) if vo else mind
        # snap to whole frames
        frames = int(round(dur * fps))
        dur = frames / fps
        shots.append(dict(cls=cls, name=cls.name, vo=vo, vo_path=vo_path, vo_dur=vo_dur, lead=lead, start=t, dur=dur, frames=frames,
                          text=NARRATION.get(vo, "") if vo else ""))
        t += dur
    return shots, t


def describe(shots, total):
    lines = [f"{'shot':5} {'start':>7} {'dur':>6} {'frames':>6}  vo   vo_dur"]
    for s in shots:
        lines.append(f"{s['name']:5} {s['start']:7.2f} {s['dur']:6.2f} {s['frames']:6d}  {s['vo'] or '-':4} {s['vo_dur']:6.2f}")
    lines.append(f"total {total:.2f}s  ({int(total * 24)} frames)")
    return "\n".join(lines)

#!/usr/bin/env python3
"""《梨泰院杀人事件：两个少年，都说不是我》180 秒成片合成。

30 个 Agnes 2.5 Flash 运动镜头（按 results.json 的 SHA-256 校验）→ 逐镜裁到脚本时长 → 24 fps / 1920x1080，
逐镜旁白按语音活动窗口锁定在各自镜头内（只快不慢），字幕与配音同起止、关键词金色放大，
程序合成悬疑低频配乐与环境/拟音，片尾淡出至静音。不使用静态图顶替任何镜头。
"""
from __future__ import annotations
import argparse, hashlib, json, math, shutil, subprocess, sys, time, urllib.request, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RATE = 48000
FPS = 24
DURATION = 180.0
PROJECT = "梨泰院杀人事件：两个少年，都说不是我"
FILM = "Itaewon1997_Final.mp4"
GOLD = r"&H003CC9FF"   # ASS 颜色是 BBGGRR：金色 #FFC93C
LEAD, TAIL, MAX_TEMPO = 0.25, 0.20, 1.18
FADE_SHOTS = {f"S{i:02d}" for i in range(15, 26)}      # 中段：淡入淡出
FLASH_SHOTS = {"S11", "S12", "S13", "S14"}             # 镜头 11–14：快速闪切
WARM = {"S23": .02, "S24": .03, "S25": .04, "S26": .04, "S27": .04, "S28": .05, "S29": .09, "S30": .03}


def run(cmd, capture=False):
    return subprocess.run([str(x) for x in cmd], check=True, capture_output=capture, text=capture)


def sha(path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def probe(path) -> dict:
    import av
    c = av.open(str(path)); s = next(x for x in c.streams if x.type == "video")
    d = float(c.duration / av.time_base) if c.duration else float(s.duration * s.time_base)
    info = {"width": int(s.width), "height": int(s.height), "fps": str(s.average_rate), "duration": d}
    c.close()
    return info


def download(url, dest: Path, expected_sha, expected_bytes):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.is_file() and dest.stat().st_size == expected_bytes and sha(dest) == expected_sha:
        return
    err = None
    for attempt in range(4):
        part = dest.with_suffix(".part")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "itaewon1997-film-render/1.0"})
            with urllib.request.urlopen(req, timeout=300) as r, part.open("wb") as f:
                shutil.copyfileobj(r, f, 1 << 18)
            if part.stat().st_size != expected_bytes or sha(part) != expected_sha:
                raise RuntimeError("clip checksum/byte count mismatch")
            part.replace(dest); return
        except Exception as e:  # noqa: BLE001
            err = e; part.unlink(missing_ok=True)
            if attempt < 3:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"could not fetch verified clip {dest.name}: {err}")


# ---------------------------------------------------------------- captions
def esc_ass(s): return s.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def ass_time(t):
    cs = max(0, round(t * 100)); h, r = divmod(cs, 360000); m, r = divmod(r, 6000); s, cs = divmod(r, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def srt_time(t):
    ms = max(0, round(t * 1000)); h, r = divmod(ms, 3600000); m, r = divmod(r, 60000); s, ms = divmod(r, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def wrap_cn(text, limit=17):
    text = text.strip()
    if len(text) <= limit:
        return text
    marks = [i + 1 for i, c in enumerate(text) if c in "，；：、。？！"]
    marks = [i for i in marks if 6 <= i <= len(text) - 5]
    cut = min(marks, key=lambda i: abs(i - len(text) / 2)) if marks else len(text) // 2
    return text[:cut] + "\\N" + text[cut:]


def highlight(text, keywords, big=False):
    body = wrap_cn(text, 14 if big else 17)
    body = esc_ass(body).replace("\\\\N", "\\N")
    size = 78 if big else 60
    for w in sorted(keywords, key=len, reverse=True):
        if w:
            body = body.replace(esc_ass(w), "{\\c" + GOLD + f"\\fs{size}\\b1" + "}" + esc_ass(w) + "{\\rDefault}")
    return body


HEADER = """[Script Info]
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Noto Sans CJK SC,50,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,3.2,1.2,2,120,120,86,1
Style: Big,Noto Sans CJK SC,64,&H00FFFFFF,&H000000FF,&H00000000,&H64000000,1,0,0,0,100,100,1,0,1,4,1.5,2,120,120,96,1
Style: Title,Noto Sans CJK SC,120,&H0037C8F5,&H000000FF,&H00000000,&H64000000,1,0,0,0,100,100,6,0,1,5,2,5,120,120,0,1
Style: Sub,Noto Sans CJK SC,42,&H00F0F0F0,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,3,0,1,2.5,1,5,120,120,0,1
Style: Tag,Noto Sans CJK SC,28,&HB0FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,2,0,9,0,60,44,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
BIG_SHOTS = {"S02", "S30"}   # 用户脚本：开头与结尾使用大字字幕


def speech_plan(story, manifest):
    by = {x["id"]: x for x in manifest["clips"]}
    if set(by) != {f"S{i:02d}" for i in range(1, 31)}:
        raise RuntimeError("need all 30 narration clips")
    rows, srt, ass = [], [], []
    for shot in story["shots"]:
        sid = shot["id"]; e = by[sid]; p = HERE / e["file"]
        if not p.is_file() or sha(p) != e["sha256"]:
            raise RuntimeError(f"{sid}: narration hash mismatch")
        if e["text"] != shot["narration"] or e["tts_text"] != shot["tts_text"]:
            raise RuntimeError(f"{sid}: narration text changed after recording")
        length = e["active_end"] - e["active_start"]
        avail = shot["duration"] - LEAD - TAIL
        tempo = max(1.0, length / avail)
        if tempo > MAX_TEMPO:
            raise RuntimeError(f"{sid}: speech needs {tempo:.2f}x (> {MAX_TEMPO}x) — shorten the sentence")
        start = shot["start"] + LEAD; end = start + length / tempo
        if end > shot["start"] + shot["duration"] - TAIL + 1e-3:
            raise RuntimeError(f"{sid}: speech does not fit its slot")
        rows.append({"id": sid, "file": str(p), "start": start, "end": end, "a": e["active_start"], "b": e["active_end"],
                     "tempo": tempo, "text": shot["narration"]})
        # 字幕与配音同起止（略提前 0.05s 出现，随语音结束 0.15s 消失）
        cs, ce = max(shot["start"], start - 0.05), min(shot["start"] + shot["duration"], end + 0.15)
        big = sid in BIG_SHOTS
        srt.append(f"{len(srt)+1}\n{srt_time(cs)} --> {srt_time(ce)}\n{wrap_cn(shot['narration']).replace(chr(92)+'N', chr(10))}\n")
        ass.append(f"Dialogue: 0,{ass_time(cs)},{ass_time(ce)},{'Big' if big else 'Default'},,0,0,0,,{highlight(shot['narration'], shot['highlight_keywords'], big)}")
    ass.append(f"Dialogue: 2,{ass_time(0)},{ass_time(DURATION)},Tag,,0,0,0,,AI动画情景重现 · 非真实影像")
    # 片尾标题（镜头 30 允许出现文字）：门打开、光涌出之后浮现
    t0 = 174 + 2.4
    ass.append(f"Dialogue: 3,{ass_time(t0)},{ass_time(179.4)},Title,,0,0,0,,{{\\an5\\pos(960,470)\\fad(700,500)}}梨泰院杀人事件")
    ass.append(f"Dialogue: 3,{ass_time(t0+0.5)},{ass_time(179.4)},Sub,,0,0,0,,{{\\an5\\pos(960,590)\\fad(700,500)}}首尔 · 1997—2017 · 19年")
    return rows, HEADER + "\n".join(ass) + "\n", "\n".join(srt) + "\n"


# ---------------------------------------------------------------- audio
def make_score(path, rate=RATE, duration=DURATION):
    """低频悬疑铺底：D 小调长音 + 不和谐小二度 + 缓慢心跳；镜头 11–14 张力上升，结尾转为暖色大三度。"""
    n_total = int(rate * duration); t = np.arange(n_total, dtype=np.float64) / rate
    x = np.zeros(n_total)
    for f, a in ((36.71, .55), (73.42, .35), (110.0, .14)):
        x += a * np.sin(2 * np.pi * f * t + .3 * np.sin(2 * np.pi * .05 * t))
    dis = np.sin(2 * np.pi * 116.54 * t) * (.05 + .05 * np.sin(2 * np.pi * .03 * t))   # 小二度摩擦
    tension = np.clip((t - 60) / 25, 0, 1) * np.clip((88 - t) / 3, 0, 1)             # 60–88s 上升
    x += dis * (1 + 2.5 * tension)
    warm = np.clip((t - 150) / 20, 0, 1)                                              # 150s 起转暖
    x += warm * .10 * (np.sin(2 * np.pi * 146.83 * t) + .8 * np.sin(2 * np.pi * 185.0 * t) + .6 * np.sin(2 * np.pi * 220.0 * t))
    rng = np.random.default_rng(1997)
    beat = 1.6 - .5 * tension
    phase = (t % beat)
    heart = np.exp(-phase * 14) * np.sin(2 * np.pi * 52 * phase) * (.28 + .5 * tension) * np.clip((t - 6) / 4, 0, 1)
    heart *= np.where(t < 150, 1.0, np.clip((170 - t) / 20, 0, 1))
    x += heart
    x += rng.normal(0, 1, n_total) * .004 * (1 + 2 * tension)
    x *= .16 * np.minimum(1, np.minimum(t / 4, (duration - t) / 3))
    st = np.column_stack((x * .97, x * 1.03))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(np.int16(np.clip(st, -.98, .98) * 32767).tobytes())


def make_sfx(path, story, rate=RATE, duration=DURATION):
    rng = np.random.default_rng(19970403); total = int(rate * duration)
    data = np.zeros((total, 2), dtype=np.float64)

    def add(at, sig, pan=.0, gain=1.0):
        i = int(at * rate)
        if i < 0 or i >= total:
            return
        sig = sig[: total - i] * gain
        data[i:i + len(sig), 0] += sig * (1 - max(0, pan)); data[i:i + len(sig), 1] += sig * (1 + min(0, pan))

    def tone(f, dur, decay, amp):
        q = np.arange(int(dur * rate)) / rate; return amp * np.sin(2 * np.pi * f * q) * np.exp(-decay * q)

    def noise(dur, amp, lp=0.0):
        z = rng.normal(0, 1, int(dur * rate))
        if lp:
            k = max(1, int(lp)); z = np.convolve(z, np.ones(k) / k, "same") * (k ** .5)
        env = np.sin(np.pi * np.linspace(0, 1, len(z))) ** 2
        return z * env * amp

    def drip(at, pan=0): add(at, tone(1750, .09, 55, .05) + tone(1100, .12, 40, .03), pan)
    def thud(at, f=58, amp=.14): add(at, tone(f, .45, 11, amp))
    def hum(s, d, amp=.012):
        q = np.arange(int(d * rate)) / rate
        add(s, amp * (np.sin(2 * np.pi * 100 * q) + .5 * np.sin(2 * np.pi * 200 * q)) * np.minimum(1, np.minimum(q / .5, (d - q) / .5)))
    def rain(s, d, amp=.02): add(s, noise(d, amp, 6) * 1.0 + noise(d, amp * .6))
    def chatter(s, d, amp=.012):
        for at in np.arange(0, d, .17):
            add(s + at, noise(.14, amp * rng.uniform(.5, 1.2), 14), pan=rng.uniform(-.5, .5))
    def step(at, amp=.05): add(at, tone(70, .12, 30, amp) + noise(.07, amp * .3, 20))

    for sh in story["shots"]:
        sid, s0, d = sh["id"], float(sh["start"]), float(sh["duration"])
        if sid in {"S01", "S03", "S07", "S08"}: rain(s0, d, .018)
        if sid == "S01":
            for k in (1.2, 2.9, 4.1): drip(s0 + k, .3)
        if sid == "S02":
            chatter(s0, 2.4, .016); hum(s0 + 2.5, d - 2.5, .02)      # 喧闹被抽离，只剩灯管嗡鸣
        if sid in {"S03", "S04"}: chatter(s0, d, .006) if sid == "S04" else None
        if sid == "S04":
            for k in (4.5, 5.2): step(s0 + k)
        if sid in {"S05", "S06", "S14"}:
            hum(s0, d, .015 if sid != "S06" else .008)
            gap = {"S05": 1.15, "S06": 1.25, "S14": 1.6}[sid]
            for k in np.arange(.5, d - (.5 if sid == "S06" else 0), gap): drip(s0 + float(k), -.2)
        if sid == "S06": data[int((s0 + d - .35) * rate):int((s0 + d) * rate)] *= 0   # 最后一拍静音
        if sid in {"S07"}:
            for k, f in ((0.3, 760), (0.9, 980), (1.5, 760), (2.1, 980), (2.7, 760), (3.3, 980)): add(s0 + k, tone(f, .2, 9, .012), .5)
        if sid == "S08":
            for k in np.arange(.3, d, .85): add(s0 + float(k), noise(.3, .012, 20), .6)
        if sid == "S09":
            thud(s0 + d - 1.6, 62, .22); thud(s0 + d - 1.55, 74, .18)
        if sid == "S10":
            for k in np.arange(.3, d - .5, .55): add(s0 + float(k), noise(.35, .02, 40), -.7)
        if sid in {"S11", "S12"}:
            for k in np.arange(.3, d - .3, 1.0): drip(s0 + float(k), -.7); drip(s0 + float(k) + .37, .7)
            hum(s0, d, .01)
        if sid == "S12":
            for k in np.arange(.4, d, .5): add(s0 + float(k), noise(.06, .03, 3), rng.choice([-.8, .8]))
        if sid == "S13":
            for k in np.arange(.5, d - .3, .9): add(s0 + float(k), noise(.4, .012, 30))
            thud(s0 + 1.0, 90, .05)
        if sid == "S14":
            data[int((s0 + 3.1) * rate):int((s0 + d) * rate)] *= .15
            add(s0 + 3.1, noise(.25, .30, 2) + tone(120, .35, 12, .2)); thud(s0 + 3.15, 45, .25)
        if sid in {"S15", "S16"}: add(s0 + 2.2, noise(.35, .01, 30)); [step(s0 + k) for k in ((1.0, 1.6, 2.2, 2.8, 3.4) if sid == "S16" else ())]
        if sid in {"S17", "S18"}:
            add(s0 + 1.0, tone(48, 1.2, 4, .12) + noise(1.0, .04, 30)); add(s0 + 1.2, tone(2100, .6, 7, .006))
        if sid == "S19":
            chatter(s0, d, .008)
            for k in np.arange(.4, d, .6): add(s0 + float(k), noise(.15, .012, 30) * 1.0)
        if sid == "S20": add(s0, noise(d, .035, 80))
        if sid in {"S21", "S22"}: rain(s0, d, .012)
        if sid == "S22":
            for k in np.arange(.2, d - .5, .22): add(s0 + float(k), tone(1500, .04, 90, .01))
        if sid in {"S23", "S24"}: hum(s0, d, .006)
        if sid == "S24":
            for k in (2.0, 4.2): add(s0 + k, tone(1900, .18, 22, .02))
        if sid == "S25": thud(s0 + 2.6, 60, .26)
        if sid == "S26":
            for k in np.arange(.2, d - .3, .13): add(s0 + float(k), noise(.03, .09, 2), rng.uniform(-.8, .8))
        if sid == "S27": chatter(s0, d, .003)
        if sid == "S28": thud(s0 + 1.8, 70, .30); add(s0 + 1.8, noise(.18, .08, 6))
        if sid in {"S29", "S30"}:
            q = np.arange(int(d * rate)) / rate; add(s0, noise(d, .014, 120))
        if sid == "S29":
            for at, f in ((2.2, 1800), (4.4, 2100)):
                q = np.arange(int(.35 * rate)) / rate
                add(s0 + at, .004 * np.sin(2 * np.pi * (f - 300 * q) * q) * np.sin(np.pi * q / .35) ** 2)
        if sid == "S30":
            add(s0 + 1.2, noise(.5, .025, 60) + tone(180, .5, 9, .02))   # 门开启的轻响
    data = np.clip(data, -.95, .95)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate); w.writeframes(np.int16(data * 32767).tobytes())


def decode_voice(row, rate=RATE):
    af = (f"atrim=start={row['a']:.3f}:end={row['b']:.3f},asetpts=PTS-STARTPTS,"
          f"atempo={row['tempo']:.6f},aresample={rate},apad=pad_dur=0.05")
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", row["file"], "-af", af, "-ac", "2", "-ar", str(rate), "-f", "f32le", "pipe:1"],
                         check=True, stdout=subprocess.PIPE).stdout
    return np.frombuffer(raw, dtype="<f4").reshape(-1, 2).copy()


def build_mix(rows, bgm_path, sfx_path, out_path, voice_path, rate=RATE, duration=DURATION):
    total = int(rate * duration); voice = np.zeros((total, 2), dtype=np.float32); segs = []
    for row in rows:
        s = decode_voice(row, rate); a = int(row["start"] * rate); b = min(total, a + len(s)); s = s[:b - a]
        f = min(int(.02 * rate), len(s) // 2)
        if f:
            s[:f] *= np.linspace(0, 1, f, dtype=np.float32)[:, None]; s[-f:] *= np.linspace(1, 0, f, dtype=np.float32)[:, None]
        voice[a:b] += s; segs.append((a, b))

    def rd(p):
        with wave.open(str(p), "rb") as f:
            return np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").astype(np.float32).reshape(-1, 2) / 32768

    score, fx = rd(bgm_path)[:total], rd(sfx_path)[:total]
    if len(score) < total or len(fx) < total:
        raise RuntimeError("audio stems too short")
    active = np.zeros(total, dtype=np.float32)
    for a, b in segs: active[a:b] = 1
    hop = rate // 100; sm = np.convolve(active[: total // hop * hop].reshape(-1, hop).max(axis=1), np.ones(19) / 19, "same")
    duck = 1 - .55 * np.repeat(sm, hop)[:total]
    # 旁白单独做目标响度：RMS（仅语音活动处）≈ -18 dBFS
    vr = float(np.sqrt(np.mean(voice[active > 0] ** 2))) if active.any() else 1e-6
    voice *= 10 ** ((-18 - 20 * math.log10(max(vr, 1e-6))) / 20)
    mix = voice + score * (1.0 * duck[:, None]) + fx * (.85 * (1 - .35 * np.repeat(sm, hop)[:total])[:, None])
    peak = float(np.max(np.abs(mix))); ceiling = 10 ** (-1.5 / 20)
    if peak > ceiling: mix *= ceiling / peak
    # 末秒静音：最后 2.2 秒线性淡出，最后 1 秒归零
    f = int(2.2 * rate); mix[-f:] *= np.linspace(1, 0, f, dtype=np.float32)[:, None]; mix[-rate:] = 0
    for p, arr in ((out_path, mix), (voice_path, np.clip(voice, -.99, .99))):
        with wave.open(str(p), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate); w.writeframes(np.int16(np.clip(arr, -.99, .99) * 32767).tobytes())
    db = lambda v: round(20 * math.log10(max(float(v), 1e-9)), 2)
    last = mix[-rate:]
    return {"rms_dbfs": db(np.sqrt(np.mean(mix.astype(np.float64) ** 2))), "peak_dbfs": db(np.max(np.abs(mix))),
            "last_second_peak_dbfs": db(np.max(np.abs(last))), "voice_rms_active_dbfs": db(np.sqrt(np.mean(voice[active > 0].astype(np.float64) ** 2))),
            "duration_seconds": duration}


# ---------------------------------------------------------------- video
def segment_filter(shot):
    sid, d = shot["id"], shot["duration"]
    f = [f"trim=duration={d}", "setpts=PTS-STARTPTS", f"fps={FPS}",
         "scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos", "crop=1920:1080", "setsar=1",
         "eq=gamma=1.06:saturation=0.96:contrast=1.03"]
    w = WARM.get(sid)
    if w: f.append(f"colorbalance=rs={w}:gs={w/3:.3f}:bs={-w}:rm={w}:bm={-w}")
    if sid in FADE_SHOTS:
        f += ["fade=t=in:st=0:d=0.25", f"fade=t=out:st={d-0.25:.2f}:d=0.25"]
    if sid in FLASH_SHOTS:
        f += ["fade=t=in:st=0:d=0.08:color=white"]
    if sid == "S29": f += [f"fade=t=out:st={d-0.3:.2f}:d=0.3:color=white"]
    if sid == "S30": f += ["fade=t=in:st=0:d=0.3:color=white", f"fade=t=out:st={d-0.8:.2f}:d=0.8"]
    f.append("format=yuv420p")
    return ",".join(f)


def font_path():
    for p in ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
              "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"):
        if Path(p).exists(): return p
    raise RuntimeError("Noto CJK fonts are required for the cover")


def grab(clip, t, dest):
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t}", "-i", clip, "-frames:v", "1", dest])
    return Image.open(dest).convert("RGB").resize((1920, 1080), Image.LANCZOS)


def make_cover(segments: Path, cover: Path):
    """左半：昏暗洗手间的门与门缝白光（S14）；右半：两个少年并排的剪影（S08）；中间一道裂缝；金色大字「都说不是我」。"""
    left = grab(segments / "S14.mp4", 1.0, cover.with_suffix(".l.jpg")).crop((330, 0, 1290, 1080))
    right = grab(segments / "S08.mp4", 2.0, cover.with_suffix(".r.jpg")).crop((330, 0, 1290, 1080))
    # 右半压成蓝黑剪影
    arr = np.asarray(right).astype(np.float32); lum = arr.mean(axis=2, keepdims=True) / 255
    sil = np.clip(lum ** 1.6 * 130, 0, 255) * np.array([.55, .75, 1.0]); right = Image.fromarray(sil.astype(np.uint8))
    im = Image.new("RGB", (1920, 1080)); im.paste(left, (0, 0)); im.paste(right, (960, 0))
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(7); x = 960.0; pts = []
    for y in range(0, 1081, 24):
        x = 960 + float(np.clip(x - 960 + rng.uniform(-16, 16), -26, 26)); pts.append((x, y))
    d.line(pts, fill=(250, 250, 245), width=9); d.line(pts, fill=(255, 215, 120), width=3)
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); od = ImageDraw.Draw(ov)
    for y in range(1080): od.line((0, y, 1920, y), fill=(0, 0, 0, int(150 * max(0, (y - 520) / 560))))
    im = Image.alpha_composite(im.convert("RGBA"), ov); d = ImageDraw.Draw(im)
    big = ImageFont.truetype(font_path(), 250); mid = ImageFont.truetype(font_path(), 54)
    d.text((960, 720), "都说不是我", font=big, fill=(255, 201, 60, 255), stroke_width=12, stroke_fill=(0, 0, 0, 255), anchor="mm")
    d.text((960, 940), "梨泰院杀人事件 · 两个少年，一个凶手", font=mid, fill=(240, 240, 240, 255), stroke_width=4, stroke_fill=(0, 0, 0, 255), anchor="mm")
    cover.parent.mkdir(parents=True, exist_ok=True); im.convert("RGB").save(cover, quality=93)
    for s in (".l.jpg", ".r.jpg"): cover.with_suffix(s).unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", default="work/itaewon1997/render"); ap.add_argument("--out", default="work/itaewon1997/delivery")
    ap.add_argument("--plan-only", action="store_true"); ap.add_argument("--audio-only", action="store_true")
    args = ap.parse_args()
    work, out = ROOT / args.work, ROOT / args.out
    work.mkdir(parents=True, exist_ok=True); out.mkdir(parents=True, exist_ok=True)
    story = json.loads((HERE / "story.json").read_text(encoding="utf-8"))
    manifest = json.loads((HERE / "audio" / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("completed") != 30:
        raise RuntimeError("all 30 voiceover tracks are required")
    rows, ass, srt = speech_plan(story, manifest)
    if args.plan_only:
        print(json.dumps({"shots": 30, "voiceovers": 30, "duration": 180, "max_tempo": round(max(r["tempo"] for r in rows), 3)}, ensure_ascii=False)); return 0
    (out / "captions.ass").write_text(ass, encoding="utf-8-sig"); (out / "captions.srt").write_text(srt, encoding="utf-8")
    bgm, sfx, mix, voice = work / "bgm.wav", work / "sfx.wav", work / "mix.wav", out / "Itaewon1997_Narration.wav"
    make_score(bgm); make_sfx(sfx, story); report = build_mix(rows, bgm, sfx, mix, voice)
    (out / "audio_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.audio_only:
        print(json.dumps(report)); return 0
    results = json.loads((HERE / "results.json").read_text(encoding="utf-8"))
    bad = [s["id"] for s in story["shots"] if results.get("shots", {}).get(s["id"], {}).get("status") != "completed"]
    if bad:
        raise RuntimeError("clips not completed: " + ", ".join(bad))
    rawdir, segdir = work / "raw", work / "segments"; rawdir.mkdir(exist_ok=True); segdir.mkdir(exist_ok=True)
    concat = []
    for shot in story["shots"]:
        sid = shot["id"]; row = results["shots"][sid]; raw = rawdir / f"{sid}.mp4"
        download(row["video_url"], raw, row["sha256"], int(row["bytes"]))
        meta = probe(raw)
        if meta["width"] < 640 or meta["height"] < 360 or meta["duration"] < shot["duration"] - .05:
            raise RuntimeError(f"{sid}: invalid source {meta}")
        seg = segdir / f"{sid}.mp4"
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-an", "-vf", segment_filter(shot), "-frames:v", str(shot["duration"] * FPS),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p", seg])
        concat.append(seg)
    lst = work / "concat.txt"; lst.write_text("".join(f"file '{p.as_posix()}'\n" for p in concat), encoding="utf-8")
    silent = work / "silent.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-an", "-c", "copy", silent])
    result = out / FILM
    fonts = next((d for d in ("/usr/share/fonts/opentype/noto", "/usr/share/fonts/truetype/noto") if Path(d).exists()), "/usr/share/fonts")
    run(["ffmpeg", "-v", "error", "-y", "-i", silent, "-i", mix, "-vf", f"subtitles={(out/'captions.ass').as_posix()}:fontsdir={fonts}",
         "-map", "0:v:0", "-map", "1:a:0", "-t", str(DURATION), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
         "-r", str(FPS), "-c:a", "aac", "-b:a", "256k", "-ar", str(RATE), "-movflags", "+faststart", result])
    final = probe(result)
    if final["width"] != 1920 or final["height"] != 1080 or abs(final["duration"] - DURATION) > .1:
        raise RuntimeError(f"final master failed spec: {final}")
    make_cover(segdir, out / "Itaewon1997_Cover.png")
    rep = {"project": PROJECT, "video": final, "shots": 30, "narrations": 30, "audio_mix": report,
           "max_tempo": round(max(r["tempo"] for r in rows), 3),
           "source_sha256": {s["id"]: results["shots"][s["id"]]["sha256"] for s in story["shots"]}}
    (out / "render_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rep, ensure_ascii=False)); return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""光州胶带案默认画面文字层（今后新片默认模板）。

固定三层：
1. Caption：画面内解说词字幕，底部居中安全区，逐镜/逐句与旁白同步；
2. Explainer：画面中间偏下（MarginV=200）的金色注释，只补充可核实事实、时间线、术语或法律边界；
3. Hook：居中偏下（MarginV=275）的大字钩子，每条严格 2 秒。

可选 `accent: "red"`：单条 Hook/Explainer 改用警句红色（HookRed/ExplainerRed）；
默认仍为金色/白底黑边模板，不影响既有片子。

所有文字必须后期烧录，AI 源片禁止自绘文字。修改此文件会影响新片默认字幕样式；
已交付母版不重渲，除非明确重新出片。
"""
from __future__ import annotations

from pathlib import Path

DEFAULT_CAPTION_POLICY = {
    "regular": "白字黑边，底部居中安全区（MarginV=62），逐镜与旁白逐句同步；关键词金色高亮并放大",
    "hook": "白字黑边，大号字幕，居中偏下（MarginV=275），每条停留2秒，不挡主体",
    "explainer": "金色小字，画面中间偏下（MarginV=200），只补充可核实事实，帮助读者看懂",
    "end_title": "只在片尾由后期添加标题文字，AI源片禁止自绘文字",
}


def ass_time(seconds: float) -> str:
    centiseconds = round(seconds * 100)
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"


def ass_escape(text: str) -> str:
    return text.replace("\\", "／").replace("{", "（").replace("}", "）").replace("\n", " ")


def caption_lines(text: str, limit: int = 20) -> list[str]:
    """Keep Chinese captions compact and centered, using a consistent small type size."""
    if len(text) <= limit:
        return [text]
    split_at = len(text) // 2
    punctuation = set("，。；：！？、")
    candidates = [i + 1 for i, char in enumerate(text) if char in punctuation and 6 <= i + 1 <= limit]
    if candidates:
        split_at = min(candidates, key=lambda i: abs(i - len(text) / 2))
    else:
        split_at = min(limit, split_at)
    left, right = text[:split_at].strip(), text[split_at:].strip()
    if len(right) > limit:
        return [left] + caption_lines(right, limit)
    return [left, right]


def ass_caption(text: str, phrases: list[str], highlight_size: int = 50) -> str:
    """Apply gold to selected phrases, restoring the active base style after each hit."""
    text = ass_escape(text)
    ordered = sorted(set(phrases), key=len, reverse=True)
    out = []
    i = 0
    while i < len(text):
        hit = next((phrase for phrase in ordered if text.startswith(phrase, i)), None)
        if hit:
            out.append(r"{\c&H0000C8FF&\fs" + str(highlight_size) + "}" + hit + r"{\r}")
            i += len(hit)
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def write_ass(path: Path, cues: list[tuple[float, float, str]], phrases: list[str],
              end_card: tuple[str, str, float, float] | None = None,
              onscreen_label: str = "", hooks: list[dict] | None = None,
              explainers: list[dict] | None = None) -> None:
    rows = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080",
        "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,Noto Sans CJK SC,56,&H00FFFFFF,&H00FFFFFF,&H00111110,&H99000000,0,0,0,0,100,100,0,0,1,2.8,0.8,2,120,120,62,1",
        "Style: Label,Noto Sans CJK SC,26,&H60FFFFFF,&H00FFFFFF,&H00101010,&H00000000,0,0,0,0,100,100,0,0,1,1.4,0.0,7,52,52,34,1",
        "Style: Hook,Noto Sans CJK SC,78,&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4.0,1.0,2,100,100,275,1",
"Style: HookRed,Noto Sans CJK SC,78,&H001414E8,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4.0,1.0,2,100,100,275,1",
"Style: ExplainerRed,Noto Sans CJK SC,32,&H001414E8,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,1,2.2,0.5,2,120,120,200,1",
        "Style: Explainer,Noto Sans CJK SC,32,&H0000C8FF,&H00FFFFFF,&H00000000,&H70000000,0,0,0,0,100,100,0,0,1,2.2,0.5,2,120,120,200,1",
        "Style: Title,Noto Sans CJK SC,104,&H0000C8FF,&H00FFFFFF,&H00101010,&H80000000,-1,0,0,0,100,100,2,0,1,3.0,1.0,2,120,120,330,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for start, end, text in cues:
        rendered = r"\N".join(ass_caption(line, phrases) for line in caption_lines(text))
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{{\\q2\\fad(60,70)}}{rendered}")
    for hook in hooks or []:
        start, end = float(hook["start"]), float(hook["end"])
        if abs((end - start) - 2.0) > 1e-6:
            raise ValueError(f"{hook.get('id')}: hook overlay must be exactly 2 seconds")
        rendered = r"\N".join(
            ass_caption(line, phrases, highlight_size=86)
            for line in caption_lines(str(hook["text"]), limit=18)
        )
        hook_style_name = "HookRed" if str(hook.get("accent", "")).lower() == "red" else "Hook"
        rows.append(f"Dialogue: 2,{ass_time(start)},{ass_time(end)},{hook_style_name},,0,0,0,,{{\\q2\\fad(90,100)}}{rendered}")
    for explainer in explainers or []:
        start, end = float(explainer["start"]), float(explainer["end"])
        if end <= start:
            raise ValueError("Explainer overlay has a non-positive duration")
        rendered = r"\N".join(caption_lines(str(explainer["text"]), limit=28))
        explainer_style = "ExplainerRed" if str(explainer.get("accent", "")).lower() == "red" else "Explainer"
        rows.append(f"Dialogue: 1,{ass_time(start)},{ass_time(end)},{explainer_style},,0,0,0,,{{\\q2\\fad(90,120)}}{rendered}")
    if onscreen_label:
        rows.append(f"Dialogue: 0,{ass_time(0.8)},{ass_time(176.0)},Label,,0,0,0,,{{\\q2\\fad(300,300)}}{ass_escape(onscreen_label)}")
    if end_card:
        title, subtitle, start, end = end_card
        card = (ass_escape(title) + r"\N" +
                r"{\fs38\c&H00FFFFFF&}" + ass_escape(subtitle))
        rows.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Title,,0,0,0,,{{\\q2\\fad(200,400)}}{card}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")

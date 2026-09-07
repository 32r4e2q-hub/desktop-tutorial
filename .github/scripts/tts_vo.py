#!/usr/bin/env python3
"""Generate the 10 narration blocks (N01..N10) for 《白教堂的雾》 with edge-tts (zh-CN-YunxiNeural).

Texts mirror ripper/assemble.py NARRATION (each block's lines joined verbatim),
so vo_align.py can measure pauses and align subtitles.
Writes ripper/audio/vo/N01.mp3 ... N10.mp3 with retries.
"""
import asyncio
import os
import sys

import edge_tts

VOICE = "zh-CN-YunxiNeural"
RATE = "+0%"
PITCH = "-8Hz"
VOLUME = "+0%"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "ripper", "audio", "vo")

TEXTS = {
    "N01": [
        "1888年秋天，伦敦东区，白教堂。",
        "十一周之内，五个女人在夜里遇害。",
        "凶手写信嘲笑警察，还给自己起了个名字。",
        "一百多年过去了，没有人知道，他到底是谁。",
    ],
    "N02": [
        "8月31日凌晨三点四十分。",
        "马车夫查尔斯·克罗斯走过巴克斯街，",
        "看见墙边躺着一个人。",
        "他以为是醉倒的女人，凑近才发现——",
        "她叫玛丽·安·尼科尔斯，四十三岁。",
        "这是第一个。",
    ],
    "N03": [
        "八天后，汉伯里街29号的后院，第二个。",
        "警督弗雷德里克·阿伯莱恩赶到时，",
        "围观的人已经挤满了巷子。",
        "凶手下手极快，没有人听见任何声音。",
    ],
    "N04": [
        "9月27日，中央新闻社收到一封红墨水写的信。",
        "信里嘲笑警察，预告下一次动手。",
        "落款是一个从未有人见过的名字：",
        "Jack the Ripper，开膛手杰克。",
        "这个名字，第二天登上了所有报纸。",
    ],
    "N05": [
        "9月30日，一夜之间两起。",
        "伯纳街，一位小贩的马突然惊立不前；",
        "四十五分钟后，一英里外的主教广场，",
        "巡警的灯光照见了第四个。",
        "凶手在两地之间，穿过了整个警戒区。",
    ],
    "N06": [
        "就在那晚，古尔斯顿街的门洞里出现一行粉笔字，",
        "旁边是一块染了血的围裙碎片。",
        "警察总监沃伦亲自下令：天亮之前，擦掉。",
        "这是全案唯一可能由凶手留下的文字，",
        "就这样消失了。",
    ],
    "N07": [
        "11月9日，米勒庭院13号。",
        "房东的助手来收房租，敲门没人应，",
        "他从窗帘缝往里看了一眼。",
        "那一眼，成了整个案件最不可言说的部分。",
        "此后，杰克再没有出现。",
    ],
    "N08": [
        "一百多年来，嫌疑人名单越拉越长：",
        "波兰理发师科斯明斯基、律师德鲁伊特、",
        "医生塔姆布蒂、画家西克特，甚至王室成员。",
        "每一个都有证据，每一个都不够。",
    ],
    "N09": [
        "2014年，有人用一条据称来自现场的披肩",
        "做DNA检测，指向科斯明斯基。",
        "但披肩来历不明，检测方法也遭到质疑。",
        "答案似乎近在眼前，又再一次滑走。",
    ],
    "N10": [
        "白教堂的雾早就散了。",
        "可只要那五个名字还被人提起，",
        "那个没有脸的男人，",
        "就还站在灯光照不到的地方。",
        "他是谁？评论区，说出你的推理。",
    ],
}


async def synth(key: str, text: str) -> None:
    path = os.path.join(OUT, f"{key}.mp3")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"skip {key} (exists)", flush=True)
        return
    last = None
    for attempt in range(5):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=RATE, pitch=PITCH, volume=VOLUME)
            await comm.save(path)
            if os.path.getsize(path) > 0:
                print(f"ok {key} ({os.path.getsize(path)} bytes)", flush=True)
                return
            last = RuntimeError("empty file")
        except Exception as exc:  # network hiccups
            last = exc
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f"{key} failed after retries: {last}")


async def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    total = len(TEXTS)
    done = 0
    for key, lines in TEXTS.items():
        text = "".join(lines)
        await synth(key, text)
        done += 1
        print(f"{done}/{total} {key}", flush=True)
        await asyncio.sleep(0.1)
    print("ALL_VO_DONE", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"VO_FAILED: {exc}", flush=True)
        sys.exit(1)

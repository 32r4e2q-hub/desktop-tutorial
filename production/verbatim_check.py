#!/usr/bin/env python3
"""成片逐字听检：把成片里的解说转写成文字，与剧本逐字比对。

为什么要有这个工具
------------------
《制作过程.md》里一直挂着一条"没做完"：**逐字听检**。静音闸门能证明"有声、电平正常、
每段都有声、没中途丢声"，但证明不了"配音念的字和剧本一字不差"——而中文 TTS 念错字、
吞字、把「二十二岁」念成「二十三岁」这类事故，恰恰是出片后才看得出来的。

仓库里已有的 ``align_audio.py`` 不能拿来当这个证据，有两个原因：

1. 它把剧本文字当 ``initial_prompt`` 喂给了模型（``initial_prompt=row['text']``）。
   用"先告诉模型答案、再让模型复述答案"来证明音频与剧本一致，是循环论证；
2. 它转写的是分段的配音 wav，不是成片。段落有没有放错位置，它管不着。

所以这个工具刻意做得更硬：

* **不给 initial_prompt**，模型没被暗示过答案；
* 转写对象是**最终成片**按章节时间切出来的音频——验的是"成片第 N 章里念的字，
  是不是剧本第 N 章的字"，顺带把"段落放错位置"也验了；
* 可选再跑一遍**干净的配音文件**（``--narration``）做对照：如果成片里字错率高、
  配音文件里很低，那是音乐/混音干扰 ASR；如果两边都高，那才是真有问题。

它报告**字错率（CER，编辑距离 / 剧本字数）**与**覆盖率**（匹配上的字占剧本字数的比例），
超阈值就要求人工听那一段，并且以非 0 退出。转写器装不上时**直接失败**，不静默通过——
静默通过正是第一版成片"没声音却出片"的病根。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import wave
from difflib import SequenceMatcher
from pathlib import Path

import numpy as np

RATE = 48000
DIGITS = "零一二三四五六七八九"
DEFAULT_MODEL = "small"
DEFAULT_MAX_CER = 0.15
DEFAULT_LANGUAGE = "zh"
PAD_SECONDS = 0.25          # 章节前后多留一点，避免把第一个字/最后一个字切掉


class VerdictError(RuntimeError):
    """转写器不可用或字错率超阈值。"""


def chinese_number(value: int) -> str:
    """把阿拉伯数字换成汉字，好跟 ASR 转出来的读法对齐（22 -> 二十二）。"""
    if value < 10:
        return DIGITS[value]
    if value < 100:
        tens, ones = divmod(value, 10)
        return ("" if tens == 1 else DIGITS[tens]) + "十" + (DIGITS[ones] if ones else "")
    return "".join(DIGITS[int(character)] for character in str(value))


# whisper 的中文转写大量输出繁体（small 尤其明显），而剧本是简体——
# 不做简繁折叠的话，字错率会被字形差异刷爆（v2 听检 N01/N03/N04/N06 的
# "失败"几乎全是 纪→紀、术→術 这类假差异）。两侧同表折叠：繁体入表折向
# 简体，简体字符不在表中原样保留，所以对剧本侧是无操作。表只收单字高置信
# 对；表外字符原样参与比对——真念错仍然会亮红，闸门不被稀释。
_TRADITIONAL, _SIMPLIFIED = zip(*[
    ("愛","爱"),("礙","碍"),("襖","袄"),("罷","罢"),("擺","摆"),("敗","败"),("辦","办"),("幫","帮"),
    ("寶","宝"),("報","报"),("幣","币"),("邊","边"),("變","变"),("標","标"),("賓","宾"),("補","补"),
    ("參","参"),("慘","惨"),("燦","灿"),("蒼","苍"),("層","层"),("纏","缠"),("嘗","尝"),("償","偿"),
    ("長","长"),("場","场"),("廠","厂"),("車","车"),("徹","彻"),("塵","尘"),("陳","陈"),("襯","衬"),
    ("稱","称"),("懲","惩"),("遲","迟"),("齒","齿"),("衝","冲"),("醜","丑"),("礎","础"),("處","处"),
    ("觸","触"),("傳","传"),("瘡","疮"),("闖","闯"),("創","创"),("純","纯"),("詞","词"),("辭","辞"),
    ("從","从"),("叢","丛"),("湊","凑"),("竄","窜"),("錯","错"),("達","达"),("帶","带"),("貸","贷"),
    ("單","单"),("擔","担"),("膽","胆"),("彈","弹"),("當","当"),("黨","党"),("擋","挡"),("導","导"),
    ("島","岛"),("禱","祷"),("燈","灯"),("鄧","邓"),("敵","敌"),("滌","涤"),("遞","递"),("點","点"),
    ("電","电"),("東","东"),("動","动"),("凍","冻"),("鬥","斗"),("獨","独"),("讀","读"),("斷","断"),
    ("隊","队"),("對","对"),("噸","吨"),("頓","顿"),("奪","夺"),("墮","堕"),("訛","讹"),("額","额"),
    ("惡","恶"),("兒","儿"),("爾","尔"),("餓","饿"),("發","发"),("髮","发"),("罰","罚"),("範","范"),
    ("紡","纺"),("飛","飞"),("廢","废"),("費","费"),("墳","坟"),("奮","奋"),("糞","粪"),("豐","丰"),
    ("風","风"),("瘋","疯"),("馮","冯"),("縫","缝"),("諷","讽"),("鳳","凤"),("婦","妇"),("復","复"),
    ("複","复"),("該","该"),("蓋","盖"),("乾","干"),("幹","干"),("趕","赶"),("剛","刚"),("鋼","钢"),
    ("岡","岗"),("綱","纲"),("鎬","镐"),("個","个"),("給","给"),("鞏","巩"),("貢","贡"),("溝","沟"),
    ("構","构"),("購","购"),("夠","够"),("蠱","蛊"),("顧","顾"),("颳","刮"),("關","关"),("觀","观"),
    ("館","馆"),("慣","惯"),("廣","广"),("歸","归"),("龜","龟"),("規","规"),("貴","贵"),("劊","刽"),
    ("國","国"),("過","过"),("韓","韩"),("漢","汉"),("號","号"),("閡","阂"),("鶴","鹤"),("賀","贺"),
    ("轟","轰"),("紅","红"),("後","后"),("壺","壶"),("護","护"),("滸","浒"),("華","华"),("劃","划"),
    ("畫","画"),("話","话"),("懷","怀"),("壞","坏"),("歡","欢"),("環","环"),("還","还"),("緩","缓"),
    ("換","换"),("喚","唤"),("謊","谎"),("揮","挥"),("輝","辉"),("匯","汇"),("彙","汇"),("會","会"),
    ("諱","讳"),("賄","贿"),("穢","秽"),("渾","浑"),("諢","诨"),("銅","铜"),("禍","祸"),("擊","击"),
    ("機","机"),("積","积"),("饑","饥"),("譏","讥"),("極","极"),("級","级"),("擠","挤"),("幾","几"),
    ("計","计"),("記","记"),("際","际"),("劑","剂"),("濟","济"),("繼","继"),("價","价"),("駕","驾"),
    ("殲","歼"),("艱","艰"),("監","监"),("堅","坚"),("簡","简"),("見","见"),("艦","舰"),("劍","剑"),
    ("鍵","键"),("漸","渐"),("踐","践"),("鑒","鉴"),("鑑","鉴"),("將","将"),("薑","姜"),("漿","浆"),
    ("講","讲"),("獎","奖"),("醬","酱"),("膠","胶"),("階","阶"),("潔","洁"),("結","结"),("節","节"),
    ("誡","诫"),("屆","届"),("緊","紧"),("謹","谨"),("進","进"),("盡","尽"),("儘","尽"),("勁","劲"),
    ("驚","惊"),("經","经"),("競","竞"),("淨","净"),("徑","径"),("舊","旧"),("劇","剧"),("懼","惧"),
    ("據","据"),("覺","觉"),("絕","绝"),("軍","军"),("駿","骏"),("開","开"),("凱","凯"),("顆","颗"),
    ("殼","壳"),("課","课"),("墾","垦"),("懇","恳"),("誇","夸"),("塊","块"),("虧","亏"),("擴","扩"),
    ("闊","阔"),("蠟","蜡"),("臘","腊"),("來","来"),("蘭","兰"),("攔","拦"),("欄","栏"),("爛","烂"),
    ("勞","劳"),("澇","涝"),("樂","乐"),("類","类"),("淚","泪"),("籬","篱"),("離","离"),("裡","里"),
    ("裏","里"),("禮","礼"),("麗","丽"),("勵","励"),("歷","历"),("曆","历"),("厲","厉"),("聯","联"),
    ("憐","怜"),("簾","帘"),("蓮","莲"),("連","连"),("練","练"),("煉","炼"),("糧","粮"),("兩","两"),
    ("輛","辆"),("療","疗"),("獵","猎"),("臨","临"),("鄰","邻"),("鱗","鳞"),("靈","灵"),("嶺","岭"),
    ("領","领"),("劉","刘"),("龍","龙"),("樓","楼"),("婁","娄"),("蘆","芦"),("盧","卢"),("爐","炉"),
    ("魯","鲁"),("陸","陆"),("錄","录"),("慮","虑"),("亂","乱"),("論","论"),("羅","罗"),("絡","络"),
    ("駱","骆"),("媽","妈"),("馬","马"),("罵","骂"),("嗎","吗"),("買","买"),("賣","卖"),("邁","迈"),
    ("麥","麦"),("脈","脉"),("瞞","瞒"),("滿","满"),("謾","谩"),("貓","猫"),("麼","么"),("門","门"),
    ("悶","闷"),("們","们"),("夢","梦"),("彌","弥"),("謎","谜"),("綿","绵"),("緬","缅"),("廟","庙"),
    ("滅","灭"),("憫","悯"),("鳴","鸣"),("謀","谋"),("畝","亩"),("納","纳"),("難","难"),("惱","恼"),
    ("腦","脑"),("鬧","闹"),("內","内"),("擬","拟"),("膩","腻"),("釀","酿"),("鳥","鸟"),("聶","聂"),
    ("寧","宁"),("農","农"),("濃","浓"),("瘧","疟"),("盤","盘"),("賠","赔"),("噴","喷"),("鵬","鹏"),
    ("騙","骗"),("飄","飘"),("頻","频"),("貧","贫"),("蘋","苹"),("憑","凭"),("評","评"),("潑","泼"),
    ("鋪","铺"),("僕","仆"),("樸","朴"),("譜","谱"),("齊","齐"),("騎","骑"),("豈","岂"),("啓","启"),
    ("棄","弃"),("氣","气"),("遷","迁"),("簽","签"),("謙","谦"),("錢","钱"),("潛","潜"),("淺","浅"),
    ("譴","谴"),("槍","枪"),("強","强"),("搶","抢"),("橋","桥"),("僑","侨"),("竅","窍"),("親","亲"),
    ("輕","轻"),("傾","倾"),("請","请"),("慶","庆"),("瓊","琼"),("窮","穷"),("區","区"),("驅","驱"),
    ("齲","龋"),("權","权"),("勸","劝"),("確","确"),("讓","让"),("擾","扰"),("熱","热"),("認","认"),
    ("韌","韧"),("榮","荣"),("絨","绒"),("軟","软"),("銳","锐"),("潤","润"),("灑","洒"),("薩","萨"),
    ("賽","赛"),("傘","伞"),("喪","丧"),("騷","骚"),("澀","涩"),("殺","杀"),("紗","纱"),("篩","筛"),
    ("曬","晒"),("刪","删"),("陝","陕"),("傷","伤"),("賞","赏"),("燒","烧"),("紹","绍"),("攝","摄"),
    ("設","设"),("紳","绅"),("審","审"),("腎","肾"),("聲","声"),("勝","胜"),("聖","圣"),("師","师"),
    ("時","时"),("濕","湿"),("實","实"),("詩","诗"),("試","试"),("勢","势"),("視","视"),("適","适"),
    ("釋","释"),("飾","饰"),("壽","寿"),("獸","兽"),("書","书"),("屬","属"),("術","术"),("樹","树"),
    ("帥","帅"),("雙","双"),("誰","谁"),("稅","税"),("順","顺"),("說","说"),("碩","硕"),("絲","丝"),
    ("飼","饲"),("鬆","松"),("訟","讼"),("頌","颂"),("蘇","苏"),("訴","诉"),("雖","虽"),("隨","随"),
    ("歲","岁"),("孫","孙"),("損","损"),("縮","缩"),("鎖","锁"),("臺","台"),("颱","台"),("檯","台"),
    ("態","态"),("攤","摊"),("談","谈"),("壇","坛"),("嘆","叹"),("湯","汤"),("燙","烫"),("濤","涛"),
    ("討","讨"),("騰","腾"),("題","题"),("體","体"),("條","条"),("鐵","铁"),("廳","厅"),("聽","听"),
    ("統","统"),("頭","头"),("圖","图"),("塗","涂"),("團","团"),("託","托"),("脫","脱"),("駝","驼"),
    ("窪","洼"),("襪","袜"),("彎","弯"),("萬","万"),("網","网"),("韋","韦"),("違","违"),("圍","围"),
    ("為","为"),("爲","为"),("維","维"),("偉","伟"),("緯","纬"),("衛","卫"),("溫","温"),("聞","闻"),
    ("穩","稳"),("問","问"),("渦","涡"),("無","无"),("務","务"),("霧","雾"),("誤","误"),("犧","牺"),
    ("習","习"),("戲","戏"),("細","细"),("蝦","虾"),("嚇","吓"),("峽","峡"),("俠","侠"),("狹","狭"),
    ("廈","厦"),("鮮","鲜"),("纖","纤"),("鹹","咸"),("顯","显"),("險","险"),("現","现"),("獻","献"),
    ("縣","县"),("憲","宪"),("線","线"),("綫","线"),("鄉","乡"),("詳","详"),("響","响"),("項","项"),
    ("蕭","萧"),("銷","销"),("曉","晓"),("嘯","啸"),("脅","胁"),("諧","谐"),("寫","写"),("瀉","泻"),
    ("謝","谢"),("鋅","锌"),("興","兴"),("須","须"),("許","许"),("緒","绪"),("續","续"),("懸","悬"),
    ("選","选"),("詢","询"),("訓","训"),("訊","讯"),("遜","逊"),("壓","压"),("啞","哑"),("嚴","严"),
    ("巖","岩"),("鹽","盐"),("顏","颜"),("閻","阎"),("艷","艳"),("驗","验"),("陽","阳"),("楊","杨"),
    ("養","养"),("樣","样"),("癢","痒"),("謠","谣"),("藥","药"),("爺","爷"),("頁","页"),("業","业"),
    ("葉","叶"),("醫","医"),("儀","仪"),("義","义"),("議","议"),("億","亿"),("憶","忆"),("陰","阴"),
    ("銀","银"),("隱","隐"),("應","应"),("嬰","婴"),("櫻","樱"),("鷹","鹰"),("營","营"),("蠅","蝇"),
    ("贏","赢"),("擁","拥"),("傭","佣"),("踴","踊"),("優","优"),("憂","忧"),("郵","邮"),("猶","犹"),
    ("誘","诱"),("與","与"),("嶼","屿"),("語","语"),("譽","誉"),("預","预"),("馭","驭"),("鬱","郁"),
    ("園","园"),("員","员"),("圓","圆"),("緣","缘"),("遠","远"),("願","愿"),("約","约"),("躍","跃"),
    ("鑰","钥"),("雲","云"),("勻","匀"),("運","运"),("韻","韵"),("雜","杂"),("災","灾"),("載","载"),
    ("讚","赞"),("贊","赞"),("臟","脏"),("髒","脏"),("鑿","凿"),("棗","枣"),("責","责"),("擇","择"),
    ("則","则"),("澤","泽"),("賊","贼"),("贈","赠"),("鍘","铡"),("詐","诈"),("齋","斋"),("債","债"),
    ("戰","战"),("張","张"),("漲","涨"),("帳","帐"),("賬","账"),("貞","贞"),("針","针"),("偵","侦"),
    ("診","诊"),("陣","阵"),("掙","挣"),("爭","争"),("繩","绳"),("證","证"),("鄭","郑"),("織","织"),
    ("職","职"),("執","执"),("紙","纸"),("摯","挚"),("擲","掷"),("幟","帜"),("質","质"),("鐘","钟"),
    ("鍾","钟"),("種","种"),("眾","众"),("晝","昼"),("驟","骤"),("豬","猪"),("諸","诸"),("燭","烛"),
    ("囑","嘱"),("築","筑"),("鑄","铸"),("專","专"),("轉","转"),("賺","赚"),("莊","庄"),("裝","装"),
    ("壯","壮"),("狀","状"),("錐","锥"),("諄","谆"),("濁","浊"),("茲","兹"),("資","资"),("漬","渍"),
    ("蹤","踪"),("綜","综"),("總","总"),("縱","纵"),("鄒","邹"),("詛","诅"),("組","组"),("鑽","钻"),
    ("籠","笼"),("檔","档"),("沒","没"),("跡","迹"),("決","决"),("數","数"),("膚","肤"),("偽","伪"),
    ("亞","亚"),("紀","纪"),("調","调"),("這","这"),("遺","遗"),("終","终"),("庫","库"),("碼","码"),
    ("檢","检"),("尋","寻"),("閉","闭"),("丟","丢"),("於","于"),("傑","杰"),("徵","征"),("準","准"),
    ("學","学"),
    ("灣","湾"),("舉","举"),("測","测"),("嚇","吓"),
])
T2S = str.maketrans("".join(_TRADITIONAL), "".join(_SIMPLIFIED))


def normalize(text: str) -> str:
    """只保留汉字与字母、数字转汉字、统一小写、简繁折叠：比对的是"念出来的字"。"""
    import re

    text = re.sub(r"(\d{4})(?=年)", lambda m: "".join(DIGITS[int(c)] for c in m.group(1)), text)
    text = re.sub(r"\d+", lambda m: chinese_number(int(m.group(0))), text)
    text = text.translate(T2S)
    return "".join(re.findall(r"[\u3400-\u9fffA-Za-z]", text)).lower()


def levenshtein(left: str, right: str) -> int:
    """编辑距离。章节文本百来个字，O(n*m) 的 DP 足够。"""
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    for i, character in enumerate(left, start=1):
        current = [i]
        for j, other in enumerate(right, start=1):
            current.append(min(previous[j] + 1,                      # 删
                               current[j - 1] + 1,                   # 插
                               previous[j - 1] + (character != other)))  # 替
        previous = current
    return previous[-1]


def character_error_rate(expected: str, recognized: str) -> float:
    """CER = 编辑距离 / 剧本字数。0 表示逐字一致。"""
    if not expected:
        return 0.0 if not recognized else 1.0
    return round(levenshtein(expected, recognized) / len(expected), 4)


def match_coverage(expected: str, recognized: str) -> float:
    """剧本里有多少比例的字在转写结果里找到了连续匹配（与 align_audio.py 同口径）。"""
    if not expected:
        return 1.0
    matcher = SequenceMatcher(None, expected, recognized, autojunk=False)
    matched = sum(block.size for block in matcher.get_matching_blocks())
    return round(matched / len(expected), 4)


def diff_spans(expected: str, recognized: str, limit: int = 6) -> list[dict]:
    """把不一致的地方列出来交给人看：工具说"有差异"，人要知道差在哪。"""
    spans = []
    matcher = SequenceMatcher(None, expected, recognized, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal" or len(spans) >= limit:
            continue
        spans.append({"at": i1, "kind": tag,
                      "script": expected[i1:i2], "heard": recognized[j1:j2]})
    return spans


def decode_audio(film: Path, work: Path) -> np.ndarray:
    """把成片解码成 48 kHz 单声道 float，区间 [-1, 1]。"""
    raw = work / "film.pcm"
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-hide_banner", "-y", "-i", str(film),
         "-ac", "1", "-ar", str(RATE), "-f", "s16le", str(raw)],
        check=True,
    )
    samples = np.frombuffer(raw.read_bytes(), dtype="<i2").astype(np.float32) / 32768.0
    raw.unlink(missing_ok=True)
    return samples


def write_wav(path: Path, samples: np.ndarray) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(samples, -1.0, 1.0)
    with wave.open(str(path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(RATE)
        writer.writeframes((clipped * 32767.0).astype("<i2").tobytes())
    return path


def load_chapters(project: Path, timing: Path | None) -> list[dict]:
    """章节文本来自 story.json，时间轴来自出片时的实测报告——两者都不是猜的。"""
    story = json.loads((project / "story.json").read_text(encoding="utf-8"))
    texts = {row["id"]: row["text"] for row in story["chapters"]}

    manifest = project / "audio" / "manifest.json"
    if manifest.is_file():
        for row in json.loads(manifest.read_text(encoding="utf-8"))["clips"]:
            if texts.get(row["id"]) != row["text"]:
                raise VerdictError(f"{row['id']}: 剧本与配音清单的文字不一致，先修再听检")

    timing_path = timing
    if timing_path is None:
        for candidate in (project / "delivery" / "narration-timing.json",
                          project / "delivery" / "final-audio-report.json"):
            if candidate.is_file():
                timing_path = candidate
                break
    if timing_path is None or not timing_path.is_file():
        raise VerdictError(f"找不到章节时间轴（{project}/delivery/ 下应有 "
                           "narration-timing.json 或 final-audio-report.json）")

    rows = json.loads(timing_path.read_text(encoding="utf-8"))
    if isinstance(rows, dict):          # final-audio-report.json 的形状
        rows = rows.get("chapters", [])

    chapters = []
    for row in rows:
        cid = row["id"]
        if cid not in texts:
            continue
        chapters.append({"id": cid, "text": texts[cid],
                         "start": float(row["start"]), "end": float(row["end"])})
    if not chapters:
        raise VerdictError("时间轴里没有任何可用章节")
    return chapters


def transcribe(paths: dict[str, Path], model_size: str, language: str,
               work: Path) -> dict[str, str]:
    """转写。**刻意不给 initial_prompt**：模型不该事先知道剧本写了什么。"""
    work.mkdir(parents=True, exist_ok=True)
    # 模型缓存必须放在 work 的**外面**：工作流把整个 work 目录上传为 artifact，
    # 2026-09-15 之前缓存落在 work/model-cache 里，每次听检白传 ~864MB，
    # 七个旧项目的听检 artifact 把仓库配额打满（6GB/7.17GB）。
    model_cache = work.parent / "model-cache"
    model_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(model_cache))
    os.environ.setdefault("HF_HUB_ETAG_TIMEOUT", "15")
    os.environ.setdefault("HF_HUB_DOWNLOAD_TIMEOUT", "90")
    try:
        from faster_whisper import WhisperModel
    except ImportError as error:      # 装不上就明说，不许"没做检查却说通过了"
        raise VerdictError(f"faster-whisper 不可用，逐字听检没做成（不是通过）：{error}") from error

    # Hugging Face 偶发抽风（TLS 被掐、限流）时重试，而不是让整次听检白跑；
    # 三次都失败才认输——错误会随失败报告一起发布，供人工定位。
    model = None
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=4,
                                 download_root=str(model_cache))
            break
        except Exception as error:
            if attempt == attempts:
                raise VerdictError(
                    f"whisper 模型 {model_size} 下载/加载连续 {attempts} 次失败：{error}") from error
            wait = 10 * attempt
            print(f"MODEL_DOWNLOAD_RETRY attempt={attempt} error={error}；{wait}s 后重试", flush=True)
            time.sleep(wait)
    transcripts: dict[str, str] = {}
    for cid, path in paths.items():
        segments, info = model.transcribe(str(path), language=language, beam_size=5,
                                          vad_filter=True)
        text = "".join(segment.text for segment in segments)
        transcripts[cid] = text
        print(f"TRANSCRIBED {cid}: {len(text)} chars / "
              f"lang={getattr(info, 'language', '?')}", flush=True)
    return transcripts


def compare(chapters: list[dict], transcripts: dict[str, str], max_cer: float) -> dict:
    rows = []
    for chapter in chapters:
        cid = chapter["id"]
        expected = normalize(chapter["text"])
        heard = normalize(transcripts.get(cid, ""))
        rate = character_error_rate(expected, heard)
        rows.append({
            "id": cid,
            "start": round(chapter["start"], 3),
            "end": round(chapter["end"], 3),
            "script_chars": len(expected),
            "heard_chars": len(heard),
            "character_error_rate": rate,
            "match_coverage": match_coverage(expected, heard),
            "verdict": "ok" if rate <= max_cer else "needs_human_listen",
            "diff": diff_spans(expected, heard),
            "transcript": transcripts.get(cid, ""),
        })
    failing = [row["id"] for row in rows if row["verdict"] != "ok"]
    return {"chapters": rows,
            "max_cer": max((row["character_error_rate"] for row in rows), default=0.0),
            "failing": failing}


def publish_report(report_path, project_dir, reason: str) -> None:
    """把听检报告（成功结论或失败现场）commit 回当前分支——尽力而为。

    运行环境（沙箱）拉不到 Actions 的日志 CDN，失败时唯一能带回来的证据就是
    分支上的文件。这里所有 git 步骤都吞异常：发布失败绝不掩盖原始检查结论。
    """
    if not report_path or not Path(report_path).is_file():
        print("REPORT_PUBLISH_SKIP 没有可发布的报告文件", flush=True)
        return
    try:
        repo = subprocess.check_output(["git", "rev-parse", "--show-toplevel"],
                                       text=True, stderr=subprocess.DEVNULL).strip()
    except Exception as error:
        print(f"REPORT_PUBLISH_SKIP 不在 git 仓库里：{error}", flush=True)
        return
    branch = os.environ.get("GITHUB_REF_NAME") or ""
    if not branch:
        # 只允许在 Actions 运行时发布（GITHUB_REF_NAME 必然存在）；
        # 本地/沙箱里跑听检绝不碰 git，防止冒烟测试污染真实分支。
        print("REPORT_PUBLISH_SKIP 本地运行，不发布（仅 Actions 内自发布）", flush=True)
        return
    target = Path(repo) / project_dir / "delivery" / Path(report_path).name
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(report_path, target)
        subprocess.run(["git", "config", "user.name", "arena-verbatim"],
                       cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "arena@local"],
                       cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "add", "-f", str(target.relative_to(repo))],
                       cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"听检: 发布逐字听检报告（{reason}）"],
                       cwd=repo, check=True, capture_output=True)
    except Exception as error:
        print(f"REPORT_PUBLISH_SKIP 发布未完成：{error}", flush=True)
        return
    for attempt in range(1, 4):
        try:
            subprocess.run(["git", "push", "origin", f"HEAD:{branch}"],
                           cwd=repo, check=True, capture_output=True)
            print(f"REPORT_PUBLISHED {target.relative_to(repo)} -> {branch}", flush=True)
            return
        except Exception as error:
            if attempt == 3:
                print(f"REPORT_PUBLISH_SKIP push 三次被拒：{error}", flush=True)
                return
            try:
                subprocess.run(["git", "fetch", "origin", branch],
                               cwd=repo, check=True, capture_output=True)
                subprocess.run(["git", "rebase", "FETCH_HEAD"],
                               cwd=repo, check=True, capture_output=True)
            except Exception:
                pass
            time.sleep(5)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--film", type=Path, required=True, help="成片路径")
    parser.add_argument("--project", type=Path, required=True, help="项目目录 production/<slug>")
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--timing", type=Path, default=None, help="章节时间轴（默认自动找）")
    parser.add_argument("--narration", type=Path, default=None,
                        help="干净的配音目录；给了就顺带跑一遍对照组")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="whisper 模型，默认 small")
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--max-cer", type=float, default=DEFAULT_MAX_CER,
                        help=f"字错率上限，超过就要求人工听（默认 {DEFAULT_MAX_CER}）")
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    if not args.film.is_file():
        raise SystemExit(f"找不到成片：{args.film}")
    args.work.mkdir(parents=True, exist_ok=True)
    try:
        return _run(args)
    except SystemExit:
        raise
    except Exception as error:
        # 运行环境拉不到 Actions 日志时，git 是唯一能把失败现场带回分支的通道：
        # 把错误写进报告并 commit/push（尽力而为），然后仍以非零退出——闸门不许变绿。
        digest = None
        try:
            with args.film.open("rb") as handle:
                digest = hashlib.file_digest(handle, "sha256").hexdigest()
        except OSError:
            pass
        report = {
            "status": "error",
            "film": args.film.name,
            "film_sha256": digest,
            "project": str(args.project),
            "model": args.model,
            "error": f"{type(error).__name__}: {error}",
            "note": "本次逐字听检没有完成（不是通过）。此报告由失败路径自动发布，供人工定位。",
        }
        out = args.report or args.work / "verbatim-check.json"
        try:
            out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        except OSError:
            pass
        publish_report(out, args.project, f"听检未完成：{type(error).__name__}")
        raise SystemExit(f"逐字听检失败：{type(error).__name__}: {error}") from error


def _run(args):  # noqa: C901
    chapters = load_chapters(args.project, args.timing)
    print(f"DECODE {args.film}", flush=True)
    samples = decode_audio(args.film, args.work)

    film_paths: dict[str, Path] = {}
    for chapter in chapters:
        start = max(0.0, chapter["start"] - PAD_SECONDS)
        end = min(len(samples) / RATE, chapter["end"] + PAD_SECONDS)
        film_paths[chapter["id"]] = write_wav(
            args.work / f"{chapter['id']}-film.wav",
            samples[int(start * RATE):int(end * RATE)],
        )
    print(f"SLICES {len(film_paths)} 段，开始转写（模型 {args.model}，不给提示词）", flush=True)
    film_result = compare(chapters, transcribe(film_paths, args.model, args.language,
                                               args.work), args.max_cer)

    control = None
    if args.narration:
        control_paths = {}
        for chapter in chapters:
            for suffix in (".wav", ".mp3"):
                candidate = args.narration / f"{chapter['id']}{suffix}"
                if candidate.is_file():
                    control_paths[chapter["id"]] = candidate
                    break
        if control_paths:
            control = compare(chapters, transcribe(control_paths, args.model, args.language,
                                                   args.work), args.max_cer)

    # 报告必须说清它量的是哪一版成片：dbcooper 一天里出片四次，而交付的
    # delivery/verbatim-check.json 只有文件名没有指纹，"CER 全过"就成了可以跨版本沿用的空话。
    # 顺带这也是唯一能发现"两次结果一模一样"的办法——音频真的一致时它是巧合，
    # 不一致时它是 bug。
    with args.film.open("rb") as handle:
        film_digest = hashlib.file_digest(handle, "sha256").hexdigest()
    report = {
        "film": args.film.name,
        "film_sha256": film_digest,
        "film_bytes": args.film.stat().st_size,
        "decoded_audio_seconds": round(len(samples) / RATE, 3),
        "project": str(args.project),
        "method": f"faster-whisper {args.model}，无 initial_prompt；转写对象为最终成片按章节切出的音频",
        "max_cer_allowed": args.max_cer,
        "film_pass": film_result,
        "narration_control": control,
        "note": ("CER = 编辑距离 / 剧本字数。ASR 本身也会错，所以 'needs_human_listen' 的意思是"
                 "\"这一段的差异需要人耳裁决\"，不等于\"配音一定错了\"；"
                 "对照组（干净配音）字错率明显低于成片时，差异多半来自音乐干扰 ASR。"
                 "本报告按 film_sha256 绑定被检成片：换一版成片必须重跑，结论不跨版本沿用。"),
    }
    out = args.report or args.work / "verbatim-check.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"听检结果：{out}")
    for row in film_result["chapters"]:
        control_row = None
        if control:
            control_row = next((r for r in control["chapters"] if r["id"] == row["id"]), None)
        extra = f"，对照组 CER {control_row['character_error_rate']}" if control_row else ""
        print(f"    {row['id']}  CER {row['character_error_rate']:.3f} / "
              f"覆盖率 {row['match_coverage']:.2f} / {row['verdict']}{extra}")
    print(f"  最大字错率 {film_result['max_cer']:.3f}（上限 {args.max_cer}）")
    if film_result["failing"]:
        print("  需人工听：" + "、".join(film_result["failing"]), flush=True)
        publish_report(out, args.project, "CER 超上限，报告随失败发布供人耳裁决")
        return 1
    print("  六段全部落在字错率上限内")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""screenplay.md 生成器：解说六段抄自 story.json（与 audio/manifest.json 逐字一致），分镜时间取自
render.py 的 CUTS 算出的真实 EDL（不是 4 秒规划网格），信息卡文案取自 presentation.cards，
资料来源取自 story.json.sources。只有「事实边界」一节是手写的（FACT_BOUNDARY）。
改了 CUTS / 解说 / 信息卡后重跑：python3 production/monalisa/screenplay_gen.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render  # noqa: E402

FACT_BOUNDARY = """\
**可证的事实（每条都能指到下面「资料来源」的编号）**

- 1911 年 8 月 21 日是星期一、卢浮宫闭馆日；清早，意大利人文森佐·佩鲁贾（Vincenzo Peruggia，1881 年 10 月 8 日生，案发时 29 岁）穿着馆内工人的白大褂混进馆里，把《蒙娜丽莎》从方形大厅墙上的四个铁钩上摘下，躲进员工楼梯间拆掉玻璃罩和画框；楼梯底下的门锁着（门把手已被拆掉），路过的水管工把他当成同事，用钳子帮他开了门。第二天（星期二）来写生的画家发现墙上只剩铁钩。〔3〕〔4〕〔12〕〔17〕〔18〕
- 佩鲁贾油漆工出身，在巴黎打零工，曾受雇在卢浮宫给名画装玻璃罩，很可能参与过《蒙娜丽莎》玻璃罩的制作；有前科。〔4〕〔5〕〔7〕〔8〕〔17〕
- 《蒙娜丽莎》是画在白杨木板上的油画，77 × 53 厘米，卷不起来；木板顶端有一道裂缝，背面有蝴蝶形木楔。〔3〕〔14〕
- 卢浮宫闭馆一周；边境与港口检查；诗人阿波利奈尔被拘押，毕加索被叫去问话。〔3〕〔6〕〔8〕〔9〕〔15〕
- 玻璃罩上唯一清晰的指纹是一枚左手拇指印；「法国福尔摩斯」贝蒂荣的部门有约 75 万份档案，其中有佩鲁贾 1908、1909 年的两套指纹，但分类只按右手拇指，不知道名字就查不到。〔1〕〔7〕〔8〕〔13〕
- 警探两次上门问话，据记载其中一次就伏在藏着画的桌子上写完了报告。〔4〕〔7〕
- 1913 年 11 月底，他化名「莱昂纳多」写信给佛罗伦萨画商杰里（Alfredo Geri），开价 50 万里拉，条件是画要留在意大利；12 月带画到佛罗伦萨，住进旅馆；杰里和乌菲兹美术馆馆长波吉（Giovanni Poggi）到旅馆，他从白木箱的假底下捧出红绸包着的画；背面的卢浮宫印章与编号吻合，顶端裂缝与细密的裂纹网与照片吻合。〔3〕〔8〕〔9〕〔10〕〔11〕〔15〕〔18〕
- 12 月 11 日下午在旅馆房间被捕。被捕后他自称出于爱国、为拿破仑掠夺意大利艺术品报仇；但这幅画是达芬奇 1516 年自己带到法国、后由弗朗索瓦一世购得的，比拿破仑出生（1769 年）早两百多年。〔2〕〔5〕〔9〕〔16〕
- 1911 年 12 月 22 日他写信给父亲，说自己要发大财。被捕后，他的指纹与档案比对「每一处都吻合」。〔1〕〔2〕〔4〕〔13〕
- 1914 年 1 月 4 日画作回到卢浮宫；1914 年 6 月判一年零十五天，上诉后减为七个月零八天，实际坐了约七个月牢。〔4〕〔5〕〔6〕〔16〕

**情景重现（全部是 Agnes Video V2.0 生成的 2D 动画，常驻标注「AI动画情景重现 · 非历史影像」或更具体的「AI动画示意 · 非原始物证 / 非原始档案 / 非原作影像 …」）**

- 所有人物只有背影、剪影和手：佩鲁贾、贝蒂荣、毕加索、达芬奇都不出现 AI 生成的脸。
- 《蒙娜丽莎》的正面永远不画清楚：只出现玻璃反光、画板背面、红布包、远处一幅小小的画、裂纹微距——既不让 AI 伪造名画，也避开最容易畸变的人脸。
- 指纹卡、档案柜、问询室、宪兵敲门都是示意镜头；AI 画面里不出现可读文字，所有文字都在信息卡里由后期用 Noto CJK 绘制。

**坚决不写**

- 不写「工作服上的白杨木纤维与画板比对」这类「微观画布纤维破案」情节：选题简报里有，但查无任何史料（用户已确认按史实改写）。本片的「微观证据」换成两样有据可查的：玻璃上的左手拇指印，和画板本身（背面印章编号 + 顶端裂缝 + 裂纹网）。
- 不写「瓦尔菲耶诺侯爵策划、先卖六幅伪作」的传说：出自 1932 年的一篇杂志文章，普遍被认为是编造的。〔8〕
- 不替他下结论：「爱国」说法与史实不符、开价 50 万、给父亲的信都摆出来，「爱国还是爱钱」留给观众在评论区回答。
"""


def film_rows(story):
    ct = json.loads((HERE / 'audio' / 'clause-times.json').read_text())
    durations = [ct[c['id']]['duration'] for c in story['chapters']]
    usable = render.DURATION - render.INTRO - render.OUTRO - render.GAP * (len(durations) - 1)
    tempo = sum(durations) / usable
    start, rows = render.INTRO, []
    for c, d in zip(story['chapters'], durations):
        rows.append({'id': c['id'], 'start': start, 'end': start + d / tempo, 'raw_duration': d,
                     'tempo': tempo, 'text': c['text'], 'title': c.get('title', '')})
        start += d / tempo + render.GAP
    return rows, tempo, sum(durations)


def mmss(seconds):
    m, s = divmod(seconds, 60)
    return f'{int(m):02d}:{s:04.1f}'


def main():
    story = json.loads((HERE / 'story.json').read_text())
    manifest = json.loads((HERE / 'audio' / 'manifest.json').read_text())
    rows, tempo, total = film_rows(story)
    edl = render.make_edl(story, rows)
    shots = {s['id']: s for s in story['shots']}
    pres = story['presentation']
    agnes = sum(1 for s in story['shots'] if s['kind'] == 'agnes')
    lens = [(e['end_frame'] - e['start_frame']) / render.FPS for e in edl if e['kind'] == 'agnes']
    out = [f"# {story['title']}", '',
           f"三分钟横屏解说 · 成片 1920×1080 / 30 fps / 180 秒 · {len(story['shots'])} 镜（{agnes} 个 Agnes Video V2.0 "
           f"二维动画镜头 + {len(story['shots']) - agnes} 张信息卡，每镜只用一次）· 配音 {manifest['voice_id']}"
           f"（用户试听选定的男声），六段合计 {total:.1f} 秒（收紧停顿后），整体变速 {tempo:.3f}×。", '',
           '## 事实边界', '', FACT_BOUNDARY, '## 解说稿与时间线', '',
           '以下六段与 `story.json` 的 `chapters[].text`、`audio/manifest.json` 的 `clips[].text` **逐字一致**'
           '（`generate.py --validate` 守着前两处，`screenplay_gen.py` 直接从 story.json 抄，改一个字三处一起改）。', '']
    for i, r in enumerate(rows):
        a = 0.0 if i == 0 else r['start']
        b = rows[i + 1]['start'] if i + 1 < len(rows) else render.DURATION - render.OUTRO
        out += [f"### {mmss(a)}—{mmss(b)}　{r['title']}（{r['id']}）", '', r['text'], '']
    out += ['## 分镜与衔接', '',
            '每镜的时间是成片里的真实时间（由 `render.py` 的 CUTS 按配音分句停顿切出，不是 4 秒规划网格）。'
            f'Agnes 每镜请求 7 秒（169 帧 @ 24 fps），成片里用 {min(lens):.1f}–{max(lens):.1f} 秒，全片没有慢放。', '',
            '| 镜头 | 成片时间 | 类型 | 运镜 | 叙事职责 | 衔接方式 |', '|---|---|---|---|---|---|']
    kind_name = {'agnes': 'agnes 动画', 'graphic': '信息卡'}
    for e in edl:
        a, b = e['start_frame'] / render.FPS, e['end_frame'] / render.FPS
        if e['id'] == 'END':
            out.append(f"| END | {mmss(a)}—{mmss(b)} | 片尾卡 | 静态 + 淡出 | {e['purpose']}"
                       f"：「{pres['end_card'][0]}」 | 全黑 |")
            continue
        s = shots[e['id']]
        camera = s.get('camera') or ('纸面缓慢漂移' if s['kind'] == 'graphic' else '')
        out.append(f"| {e['id']} | {mmss(a)}—{mmss(b)} | {kind_name.get(s['kind'], s['kind'])} | {camera} | "
                   f"{s['purpose']} | {s.get('transition_out', '')} |")
    out += ['', '## 信息卡文案（后期用 Noto CJK 直接画，不交给视频模型拼字）', '']
    for sid, lines in pres['cards'].items():
        out.append(f"- **{sid}**：{' ／ '.join(lines)}")
    out.append(f"- **片头卡**：{' ／ '.join(pres['title_card'])}")
    out.append(f"- **片尾卡**：{' ／ '.join(pres['end_card'])}")
    out += ['', '## 资料来源', '']
    for src in story['sources']:
        out.append(f"{src['id']}. {src['url']} —— {src['usage']}")
    text = '\n'.join(out) + '\n'
    for ch in story['chapters']:
        assert ch['text'] in text
    (HERE / 'screenplay.md').write_text(text, encoding='utf-8')
    print('screenplay.md written:', len(text), 'chars')


if __name__ == '__main__':
    main()

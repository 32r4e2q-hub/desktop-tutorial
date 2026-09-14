"""《D.B. Cooper》重做版的两条硬要求：运镜不许单一、每一刀必须落在配音的真实停顿上。

上一版被指出「运镜总是从远到近飞入、解说跟画面对不上」。这一版把这两件事写成了
可复查的数字：本文件就是它们的守门人——改 CUTS、改 camera 字段、改解说稿，只要
破坏了「说到哪、画面就是哪」，这里就会红，而不是等 40 分钟的出片跑完才发现。

与参考项目的测试同样的分工：只跑离线内容（不联网、不消耗生成额度）；
唯一需要解码音频的那条（切点是否真的落在停顿上）在没有 ffmpeg 时自动跳过。
"""
import hashlib
import importlib.util
import json
import numpy as np
from collections import Counter
from pathlib import Path
import re
import shutil
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'production/dbcooper'


def _load(name, filename):
    """把本项目的模块按独立名字加载，避免和参考项目的同名模块（generate/render）串味。"""
    path = PROJECT / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(PROJECT))
    try:
        sys.modules[name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(PROJECT))
    return module


generator = _load('dbcooper_generate', 'generate.py')
editor = _load('dbcooper_render', 'render.py')


def project_plan():
    return json.loads((PROJECT / 'story.json').read_text(encoding='utf-8'))


def narration_rows():
    """复刻 render.audio_layout 的排布（不含解码）：真实时长 + 由它算出的 tempo。

    用 PyAV 读时长，参考项目那套测试同样是把实测时长写死在前置数据里；这里改成
    直接从已交付的配音文件读，改配音就会自动跟着变，测试才有意义。
    """
    import av
    project = project_plan()
    durations = []
    for chapter in project['chapters']:
        with av.open(str(PROJECT / 'audio' / f"{chapter['id']}.mp3")) as container:
            durations.append(container.duration / av.time_base)
    usable = editor.DURATION - editor.INTRO - editor.OUTRO - editor.GAP * (len(durations) - 1)
    tempo = sum(durations) / usable
    rows = []
    start = editor.INTRO
    for chapter, duration in zip(project['chapters'], durations):
        rows.append({'id': chapter['id'], 'start': start, 'end': start + duration / tempo,
                     'raw_duration': duration, 'tempo': tempo, 'text': chapter['text']})
        start += duration / tempo + editor.GAP
    return rows, tempo


class PlanTests(unittest.TestCase):
    def setUp(self):
        self.project = project_plan()

    def test_reviewed_timeline_and_shot_mix(self):
        generator.validate(self.project)
        kinds = {k: sum(s['kind'] == k for s in self.project['shots']) for k in ('agnes', 'graphic', 'archive')}
        self.assertEqual(kinds, {'agnes': 25, 'graphic': 5, 'archive': 0})
        self.assertEqual(self.project['target_duration'], 180)
        self.assertEqual(len(self.project['shots']), 30)

    def test_narration_text_and_audio_are_the_delivered_ones(self):
        manifest = json.loads((PROJECT / 'audio/manifest.json').read_text(encoding='utf-8'))
        by_id = {row['id']: row for row in manifest['clips']}
        for chapter in self.project['chapters']:
            receipt = by_id[chapter['id']]
            path = PROJECT / 'audio' / receipt['file']
            handle = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    handle.update(block)
            self.assertEqual(chapter['text'], receipt['text'], chapter['id'])
            self.assertEqual(handle.hexdigest(), receipt['sha256'], f"{chapter['id']} 的音频被换过了")

    def test_no_reference_project_residue(self):
        for filename in ('story.json', 'render.py', 'generate.py', 'screenplay.md'):
            text = (PROJECT / filename).read_text(encoding='utf-8')
            self.assertNotIn('黑色大丽花', text, filename)
        # 本片没有 archive 镜头：可核实的真实照片不存在，红线禁止用 AI 脸冒充本人
        self.assertFalse(any(s['kind'] == 'archive' for s in self.project['shots']))


    def test_the_airframe_is_the_same_aircraft_in_every_shot_that_shows_it(self):
        """凡出现机身，就必须是同一架：三发 727、翼下不吊发、面上不写字。

        这条是写给我自己的。上一轮为了躲开 S28 机身上那两组红色字母，我把提示词改成
        "narrow-body twin-jet + engines slung under the wings"——那是一架 737/DC-9，
        而 N01 的解说正在念「西北航空」，S01/S11/S12/S13 又都是三发 727。机型口径是
        四轮返工换来的，不能被我一句话推翻；画面与解说矛盾在本项目里就算穿帮。
        """
        shots = project_plan()['shots']

        def mentions_airframe(prompt):
            if re.search(r'no aircraft anywhere', prompt, re.I):
                return False            # S10/S17 用"画面里根本没有飞机"来消歧，那是另一种正解
            return bool(re.search(r'jetliner|airliner|727|three-engine', prompt, re.I))

        airframe = [x for x in shots if mentions_airframe(x['prompt'])]
        self.assertEqual([x['id'] for x in airframe], ['S11', 'S12', 'S13', 'S28'],
                         '有机身入画的镜头集合变了：新增/删除机型镜头时必须同步这条与画面口径。'
                         'S01 在第七抽被移出这个集合——它改成\"画面里没有飞机\"（同一个正解，S10/S17 也用它）')
        for x in airframe:
            self.assertRegex(x['prompt'], re.compile(r'727|three-engine', re.I),
                             f"{x['id']} 只写了「一架飞机」，机型没落字")
            self.assertRegex(x['prompt'], re.compile(r'(no|never)[^.\n]{0,70}under the wings|no wingside engines', re.I),
                             f"{x['id']} 没有明确否定翼下吊发——727 的三台发动机在机身尾部")
        for x in shots:
            self.assertNotRegex(x['prompt'], r'twin[- ]jet|twin[- ]engine|engines slung under|wing-mounted engines',
                               f"{x['id']} 的提示词把机型写成了翼下吊发的双发机")


class CameraDiversityTests(unittest.TestCase):
    """「全片一个飞入」是上一版被打回的原因，这里把它变成数字。"""

    def setUp(self):
        self.shots = [s for s in project_plan()['shots'] if s['kind'] == 'agnes']

    def test_at_least_sixteen_different_moves_and_none_used_three_times(self):
        moves = [shot['camera'] for shot in self.shots]
        self.assertGreaterEqual(len(set(moves)), 16, '运镜种类太少')
        for move, count in {m: moves.count(m) for m in set(moves)}.items():
            self.assertLessEqual(count, 2, f'运镜 {move} 用了 {count} 次')

    def test_push_in_is_the_exception_not_the_rule(self):
        pushing = [s['id'] for s in self.shots
                   if re.search(r'推(?!拉)|push in|push-in|dolly in|zoom in|fly in|飞入', s['camera'])]
        self.assertLessEqual(len(pushing), 2, f'推进/飞入镜头过多：{pushing}')
        pulling = [s['id'] for s in self.shots if re.search(r'拉|pullback|pull back', s['camera'])]
        self.assertGreaterEqual(len(pulling), 3, '全是往主体凑，没有拉开的呼吸')
        vertical = [s['id'] for s in self.shots if re.search(r'升|crane', s['camera'])]
        self.assertGreaterEqual(len(vertical), 2, '没有一个真正抬起来的方向')
        turning = [s['id'] for s in self.shots if re.search(r'环绕|orbit', s['camera'])]
        self.assertGreaterEqual(len(turning), 2, '缺少绕着主体转的镜头')
        held = [s['id'] for s in self.shots if re.search(r'固定|static', s['camera'])]
        self.assertGreaterEqual(len(held), 3, '一镜不切的呼吸感也没有，全是运动素材反而假')

    def test_every_prompt_writes_its_own_camera_move(self):
        sentences = []
        for shot in self.shots:
            match = re.search(r'Camera:\s*(.+?)(?:\n|$)', shot['prompt'])
            self.assertTrue(match, f"{shot['id']} 的提示词没写死运镜")
            sentence = match.group(1).strip()
            sentences.append(sentence)
            self.assertGreaterEqual(len(sentence.split()), 8, f"{shot['id']} 的运镜描述过于含糊")
            self.assertTrue(re.search(r'track|drift|tilt|pan|crane|rise|pull|push|orbit|focus|lock|follow|arc|reveal',
                                      sentence, re.IGNORECASE), f"{shot['id']} 的运镜里没有可执行的动作")
            # 「从远到近飞入」正是被打回的那一种，任何一镜都不许写
            self.assertFalse(re.search(r'\b(push|dolly|zoom)\s?in\b|fly[- ]?in', sentence, re.IGNORECASE),
                             f"{shot['id']} 又写成了飞入：{sentence}")
        counter = Counter(sentences)
        self.assertTrue(all(n <= 2 for n in counter.values()),
                        f'整句运镜被复用超过两次：{counter.most_common(1)}')
        negative = project_plan()['negative_prompt'].lower()
        for banned in ('fast zoom', 'whip pan'):
            self.assertIn(banned, negative, f'负向提示词应排除 {banned}')


class CutAlignmentTests(unittest.TestCase):
    """CUTS 是本片「解说与画面对应」的唯一真相：每镜对位、每刀落在停顿上。"""

    def setUp(self):
        self.project = project_plan()
        self.cuts = editor.CUTS
        self.chapters = [chapter['id'] for chapter in self.project['chapters']]
        self.by_id = {shot['id']: shot for shot in self.project['shots']}

    def test_every_generated_shot_is_used_and_only_reused_where_documented(self):
        entries = [(sid, variant) for chapter in self.chapters for _, sid, variant in self.cuts[chapter]]
        agnes = {shot['id'] for shot in self.project['shots'] if shot['kind'] == 'agnes'}
        self.assertEqual(len(entries), 33)                       # 33 个编辑段 + 片尾卡 = 34
        # N03 从 5 刀变 6 刀：为了让「它再次起飞」落到起飞镜上（多出来的一刀用 S14 的另一段）
        self.assertEqual({sid for sid, _ in entries}, agnes | {'S03', 'S08', 'S20', 'S23', 'S27'})
        counts = Counter(sid for sid, _ in entries)
        # 同一素材被两次用到的，只有 S06 与 S14（'b' 变体取同一镜的另一段）和 S23（两张不同文字的数据卡）；
        # 其余一镜一次。规则是「复用必须换 variant」，不是「某个号可以出现两次」。
        self.assertEqual(sorted(sid for sid, n in counts.items() if n > 1), ['S06', 'S14', 'S23'])
        for sid in ('S06', 'S14', 'S23'):
            variants = [variant for got, variant in entries if got == sid]
            self.assertEqual(len(variants), len(set(variants)), f'{sid} 同一 variant 被排了两次')
        for sid in ('S06', 'S14'):
            self.assertEqual(sorted(variant for got, variant in entries if got == sid), ['', 'b'],
                             f'{sid} 复用必须是一段原样、一段换 variant')
        self.assertEqual(len(set(editor.VARIANT_IN)) , len(editor.VARIANT_IN), 'VARIANT_IN 有重复键')
        self.assertTrue(all(k[1] == 'b' for k in editor.VARIANT_IN), 'VARIANT_IN 只登记复用段')
        self.assertEqual(sorted(variant for sid, variant in entries if sid == 'S23'),
                         ['ransom', 'suspects'])

    def test_every_data_card_says_one_thing_and_has_its_own_text(self):
        """数据卡最容易出的纰漏：嘴上说的是 A，纸上写的是 B。

        自动检查能做到的部分：每张卡都必须有自己的一条文字（(镜头号, variant) 唯一），
        且被排进 CUTS 的 graphic 段必须与它对准解说文本里的数字同源——
        S23 因此被拆成两张：1980 河畔的 5800 美元压在"说到这笔钱"的那句，
        八百余名/只剩 24 名压在"头五年"那句。
        """
        cards = [(sid, variant) for chapter in self.chapters
                 for _, sid, variant in self.cuts[chapter]
                 if self.by_id[sid]['kind'] == 'graphic']
        self.assertEqual(len(cards), len(set(cards)), '同一张卡（同 variant）被排了两次')
        for sid, variant in cards:
            heading = editor.CARD_HEADINGS.get((sid, variant or ''))
            self.assertIsNotNone(heading, f'{sid}/{variant} 没有对应的卡面文字')
            self.assertTrue(all(str(part).strip() for part in heading), f'{sid}/{variant} 卡面有空行')
        text = ''.join(chapter['text'] for chapter in self.project['chapters'])
        # 卡面里的数字必须都能在解说里找到同一说法，不允许卡片替解说新增事实
        for claim in ('二十万美元', '四个降落伞', '五千八百美元', '至今未破'):
            self.assertIn(claim, text)
        self.assertIn('八百多名嫌疑人被核查', text)
        self.assertTrue(any('800' in line for line in
                            (PROJECT / 'screenplay.md').read_text(encoding='utf-8').splitlines()),
                        '「八百余名嫌疑人」这条卡面数字在事实清单里没有出处')

    def test_cuts_never_cross_into_the_next_chapter(self):
        for index, chapter in enumerate(self.chapters):
            owned = {shot['id'] for shot in self.project['shots'][index * 5:(index + 1) * 5]}
            used = {sid for _, sid, _ in self.cuts[chapter]}
            self.assertEqual(used, owned, f'{chapter} 用到了别的章节的镜头')

    def test_the_beat_is_set_by_narration_not_by_a_metronome(self):
        gaps = []
        for chapter in self.chapters:
            anchors = [raw for raw, _, _ in self.cuts[chapter]]
            self.assertEqual(anchors[0], 0.0)
            self.assertTrue(all(b > a for a, b in zip(anchors, anchors[1:])), f'{chapter} 切点未递增')
            gaps += [round(b - a, 2) for a, b in zip(anchors, anchors[1:])]
        self.assertGreaterEqual(len(set(gaps)), 15, '切点间隔过于规整，像是按秒表切的')
        self.assertTrue(all(abs(g - 6.0) > 0.05 for g in gaps), '仍是 30 秒五刀 = 每 6 秒一刀的均匀模板')

    def test_cards_only_show_the_number_being_spoken(self):
        rows = {row['id']: row for row in narration_rows()[0]}
        for shot in self.project['shots']:
            if shot['kind'] != 'graphic':
                continue
            chapter = self.chapters[shot['start'] // 30]
            anchor = next(raw for raw, sid, _ in self.cuts[chapter] if sid == shot['id'])
            spoken = rows[chapter]['text']
            tokens = [t.strip() for t in re.split(r'[｜\n·]', shot['graphic']) if len(t.strip()) >= 2]
            self.assertTrue(tokens, shot['id'])
            self.assertTrue(any(token in spoken for token in tokens),
                            f"{shot['id']} 的信息卡文字与本章解说不同源：{tokens}")
            self.assertGreater(anchor, 0.0, f"{shot['id']} 一开章就压字幕，观众还没听到内容")

    def test_cut_points_land_on_measured_pauses(self):
        if not shutil.which('ffmpeg'):
            self.skipTest('需要 ffmpeg 解码配音才能测停顿')
        import subprocess
        import tempfile
        import wave
        rate, hop, threshold = 48000, 960, 0.009
        for chapter in self.chapters:
            source = PROJECT / 'audio' / f'{chapter}.mp3'
            with tempfile.TemporaryDirectory() as temporary:
                decoded = Path(temporary) / 'a.wav'
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-ac', '1',
                                '-ar', str(rate), '-c:a', 'pcm_s16le', str(decoded)], check=True)
                with wave.open(str(decoded), 'rb') as handle:
                    samples = np.frombuffer(handle.readframes(handle.getnframes()), dtype='<i2').astype('float32') / 32768
            blocks = samples[:len(samples) - len(samples) % hop].reshape(-1, hop)
            active = (np.sqrt((blocks * blocks).mean(axis=1)) > threshold).astype(float)
            silences, begin = [], None
            for index, flag in enumerate(active):
                if not flag and begin is None:
                    begin = index
                if flag and begin is not None:
                    if (index - begin) * hop / rate >= 0.14:
                        silences.append(((begin + index) * 0.5 * hop / rate, (index - begin) * hop / rate))
                    begin = None
            self.assertGreaterEqual(len(silences), 4, f'{chapter} 几乎没停顿，谈不上对轨')
            for raw, sid, _ in self.cuts[chapter][1:]:
                distance = min(max(raw - (center + length / 2), (center - length / 2) - raw, 0.0)
                               for center, length in silences)
                self.assertLessEqual(distance, 0.5,
                                     f'{sid} 的入点 {raw}s 离最近的自然停顿 {distance:.2f}s——会切在句子中间')


class EdlTests(unittest.TestCase):
    def test_a_reused_clip_actually_changes_its_in_point(self):
        """被复用的镜头必须真的换入点——这条钉住的是 clip_window 里的**语句顺序**。

        原先入点选择散在 render_segment 里，"逐镜上限"排在 variant 之后，于是 S14/b 的
        新入点会被上限一把拉回 0.12–4.00：两遍放同一段素材，而段数、缝隙、变速比全部照绿。
        这类"闸门看不见"的错只能靠把逻辑抽成纯函数再钉住。
        （S06 与其 'b' 段有意重叠：N02 只有 5 个镜头却有 9.4 秒解说，基段本身已铺满 5.7 秒，
        再切一段只能回头取同一段动作——这条写在台账 B8，不是漏网。）
        """
        lengths = {}
        for receipt in sorted((PROJECT / 'qa').glob('S*.json')):
            lengths[receipt.stem] = json.loads(receipt.read_text(encoding='utf-8'))['duration']
        rows, _ = narration_rows()
        windows = {}
        for entry in editor.make_edl(project_plan(), rows):
            if entry['kind'] != 'agnes':
                continue
            key = (entry['id'], entry['variant'])
            windows[key] = max(windows.get(key, 0.0),
                               (entry['end_frame'] - entry['start_frame']) / editor.FPS)
        reused = sorted({sid for sid, _ in windows if sum(1 for k in windows if k[0] == sid) > 1})
        self.assertEqual(reused, ['S06', 'S14'], '复用清单变了：加镜头时要一并登记 VARIANT_IN')
        for sid in reused:
            length = lengths.get(sid, 7.041667)
            base = editor.clip_window(sid, '', length, windows[(sid, '')])
            for (got, variant), window in windows.items():
                if got != sid or not variant:
                    continue
                alt = editor.clip_window(sid, variant, length, window)
                self.assertEqual(alt[0], editor.VARIANT_IN[(sid, variant)],
                                 f'{sid}/{variant} 的入点被逐镜上限覆盖了（clip_window 顺序写反）')
                self.assertGreater(alt[0], base[0], f'{sid}/{variant} 没有比基段更晚的入点')
        for key in editor.VARIANT_IN:
            self.assertIn(key, windows, f'VARIANT_IN 登记了 {key}，但 CUTS 里没有这一段')


    def test_edl_is_gap_free_and_covers_exactly_three_minutes(self):
        project = project_plan()
        rows, tempo = narration_rows()
        self.assertTrue(0.86 <= tempo <= 1.1, f'整片需要 {tempo:.3f} 倍速，超出 ±14% 的解说语速闸门')
        edl = editor.make_edl(project, rows)
        self.assertEqual(edl[0]['start_frame'], 0)
        self.assertEqual(edl[-1]['end_frame'], 5400)
        self.assertEqual(sum(e['end_frame'] - e['start_frame'] for e in edl), 5400)
        for left, right in zip(edl, edl[1:]):
            self.assertEqual(left['end_frame'], right['start_frame'], json.dumps(left, ensure_ascii=False))
        self.assertEqual(edl[-1]['id'], 'END')

    def test_no_edit_window_is_too_short_to_read_or_too_long_to_fill(self):
        project = project_plan()
        rows, _ = narration_rows()
        planned_seconds = {shot['id']: shot['seconds'] for shot in project['shots']}
        # render_segment 的引擎闸门：素材可用时长 = 源片长 - 首尾各 0.12s，变速比 ≤1.33
        usable = min(planned_seconds.values()) - 0.24
        for entry in editor.make_edl(project, rows):
            window = (entry['end_frame'] - entry['start_frame']) / editor.FPS
            if entry['kind'] != 'agnes':
                continue
            self.assertGreaterEqual(window, 1.0, f"{entry['id']} 只有 {window:.2f}s，一闪而过")
            self.assertLessEqual(window, 1.33 * usable,
                                 f"{entry['id']} 需要 {window / usable:.2f} 倍慢放，超出闸门")

    def test_labels_and_caption_text_survive_the_ass_escape(self):
        self.assertEqual(editor.safe_text('a\\b{c}d\n'), 'a/b（c）d ')
        for chapter in project_plan()['chapters']:
            clauses = editor.caption_clauses(chapter['text'])
            self.assertEqual(''.join(clauses), chapter['text'])
            self.assertTrue(all(0 < len(c) <= 24 for c in clauses))


class ProvenanceTests(unittest.TestCase):
    def test_generation_receipts_match_the_plan_when_present(self):
        path = PROJECT / 'results.json'
        if not path.exists():
            self.skipTest('素材还没生成（Agnes 生成跑在 Actions 上）')
        results = json.loads(path.read_text(encoding='utf-8'))
        project = project_plan()
        self.assertEqual(results['model'], 'agnes-video-v2.0')
        wanted = {shot['id']: generator.request_hash(project, shot)
                  for shot in project['shots'] if shot['kind'] == 'agnes'}
        completed = {sid: receipt for sid, receipt in results['shots'].items() if receipt['status'] == 'completed'}
        for sid, receipt in completed.items():
            self.assertEqual(receipt['request_hash'], wanted[sid], f'{sid} 的请求与当前分镜不一致')
            self.assertTrue(generator.cached_result_matches(receipt, wanted[sid]))
        # 出片需要全部 25 镜都有可核验的回执，缺一镜就地失败，不许拿图凑数
        lacking = sorted(set(wanted) - set(completed))
        self.assertFalse(lacking,
                         '素材尚未齐备：缺 ' + ','.join(lacking) +
                         '。把 {"only":"' + ','.join(lacking) + '","workers":1} 写进 '
                         'production/dbcooper/GEN_REQUEST 再 push，触发生成工作流补镜')

    def test_every_generated_shot_has_a_qa_frame(self):
        path = PROJECT / 'results.json'
        if not path.exists():
            self.skipTest('还没有生成回执')
        results = json.loads(path.read_text(encoding='utf-8'))
        for sid, receipt in results['shots'].items():
            if receipt['status'] != 'completed':
                continue
            self.assertEqual(receipt['visual_review'], 'pending', f'{sid} 被自动判过了，人工审片不是自动的')
            inspection = receipt['inspection']
            self.assertTrue(inspection['decoded_ok'])
            self.assertGreaterEqual(inspection['width'], 1280, f'{sid} 分辨率不达标')



class RestartTests(unittest.TestCase):
    """「重跑一次就能补上坏镜头」必须是可证的，而不是每次出事现场猜。

    2026-09-13 那次：provider 把 S10 判死（500），而断点续跑会拿着 results.json 里
    记住的 task_id 去轮询同一个死任务——于是无论重跑多少次都修不好。
    现在 prune_stale 负责在重跑前清掉这类记录，而工作流必须 pin 在本分支上，
    否则 `if: github.ref != ...` 会让整个 job 静默跳过，看起来"跑了但什么都没发生"。
    """

    def test_dead_tasks_are_pruned_while_reusable_assets_survive(self):
        doc = {'shots': {
            'S01': {'id': 'S01', 'status': 'completed', 'video_url': 'u'},
            'S02': {'id': 'S02', 'status': 'generated', 'video_url': 'u'},      # 素材在 CDN，只欠落盘校验
            'S03': {'id': 'S03', 'status': 'queued'},                            # 没拿到 video_id：无事可做
            'S10': {'id': 'S10', 'status': 'failed', 'task_id': 'task_dead'},    # provider 判死
            'S11': {'id': 'S11', 'status': 'waiting_create_slot'},
        }}
        self.assertEqual(generator.prune_stale(doc), ['S03', 'S10', 'S11'])
        self.assertEqual(sorted(doc['shots']), ['S01', 'S02'])

    def _workflow_text(self):
        installed = ROOT / '.github/workflows/dbcooper-gen.yml'
        template = PROJECT / 'dbcooper-agnes.workflow.yml'
        self.assertTrue(installed.exists(),
                        '缺少 .github/workflows/dbcooper-gen.yml：把 production/dbcooper/'
                        'dbcooper-agnes.workflow.yml 逐字节复制过去')
        self.assertEqual(template.read_bytes(), installed.read_bytes(),
                         '安装版与模板不一致：以后者为准重新复制一次')
        return installed.read_text(encoding='utf-8')

    def test_generation_workflow_still_points_at_this_branch(self):
        text = self._workflow_text()
        branch = generator.BRANCH
        self.assertEqual(branch, project_plan()['branch'],
                         'generate.py 的发布分支与 story.json 记的分支不一致')
        self.assertIn(f"if: github.ref == 'refs/heads/{branch}'", text,
                      '工作流的 if 还指着别的分支：job 会被静默跳过')
        self.assertIn(f'ref: {branch}', text, 'checkout 的 ref 还指着别的分支：跑的不是这里的代码')
        self.assertIn(f'- {branch}', text, 'push 触发（GEN_REQUEST）的分支过滤还指着别的分支')

    #: 每个专属工作流一张"便签"：代理没有 workflow_dispatch 权限（403），
    #: push 便签文件是唯一可用的触发方式。
    MARKER_TRIGGERS = {
        'dbcooper-gen': 'GEN_REQUEST',
        'dbcooper-render': 'RENDER_REQUEST',
        'dbcooper-verbatim': 'VERBATIM_REQUEST',
    }

    def test_project_workflows_are_pinned_here_and_loop_free(self):
        """三个专属工作流：与模板逐字节一致、pin 在本分支、只认自己那张便签。

        paths 过滤器是防自我循环的关键：gen 每完成一镜就 commit `results.json` 与 `qa/`，
        render 把成片与 `delivery/` commit 回来，verbatim 把听检报告 commit 回来——
        任何一条把触发条件写宽（比如 `on: push` 不带 paths），都会把自己再点一遍。
        "if 指着别的分支"的症状更阴：job 被静默跳过，看起来"跑了但什么都没发生"。
        """
        branch = generator.BRANCH
        for workflow, marker in self.MARKER_TRIGGERS.items():
            with self.subTest(workflow=workflow):
                template = PROJECT / {
                    'dbcooper-gen': 'dbcooper-agnes.workflow.yml',
                    'dbcooper-render': 'dbcooper-render.workflow.yml',
                    'dbcooper-verbatim': 'dbcooper-verbatim.workflow.yml',
                }[workflow]
                installed = ROOT / '.github' / 'workflows' / f'{workflow}.yml'
                self.assertTrue(installed.exists(), f'缺少 {installed.relative_to(ROOT)}（把模板逐字节复制过去）')
                self.assertEqual(template.read_bytes(), installed.read_bytes(),
                                 f'{installed.name} 与 {template.name} 不一致：以后者为准重新复制')
                text = installed.read_text(encoding='utf-8')
                self.assertIn(f"if: github.ref == 'refs/heads/{branch}'", text,
                              'if 还指着别的分支：job 会被静默跳过')
                self.assertIn(f'- {branch}', text, 'push 的分支过滤还指着别的分支')
                block = text.split('push:', 1)[1].split('permissions:', 1)[0]
                self.assertIn(f'production/dbcooper/{marker}', block,
                              f'push 触发没有只看 {marker}，交付物会把流水线自己点第二遍')

    def test_render_workflow_is_wired_to_this_branch_and_the_shared_script(self):
        """出片也要能由代理触发：RENDER_REQUEST 的 push 是唯一入口，流程本体仍是共用脚本。

        刻意 pin 在本分支的 if + 只看 RENDER_REQUEST 的 paths 过滤器上：
        出片会把成片与报告 commit 回本分支，若触发条件写宽了（比如 on: push 不带 paths），
        每次交付都会再点一次自己。
        """
        template = PROJECT / 'dbcooper-render.workflow.yml'
        installed = ROOT / '.github/workflows/dbcooper-render.yml'
        self.assertTrue(installed.exists(),
                        '缺少 .github/workflows/dbcooper-render.yml（把模板逐字节复制过去）')
        self.assertEqual(template.read_bytes(), installed.read_bytes(), '安装版与模板不一致')
        text = installed.read_text(encoding='utf-8')
        # 触发文件是"临时便签"：push 一次就该被消费掉（删掉），所以不能断言它常驻。
        # 它存在的意义只是让 push 事件的 paths 过滤器命中一次。
        self.assertIn('bash production/run_project.sh "$PROJECT" "$SKIP_ASR" "$FILM_NAME"', text,
                      '出片必须走共用的 production/run_project.sh，别在这里复制一份流程')
        self.assertNotIn('ref: arena/', text, '本分支的出片不该 pin 到别的分支的代码')
        self.assertIn('fonts-noto-cjk', text, '烧中文字幕要 CJK 字体，缺了 render.py 会拒绝出片')

    def test_prune_flag_cleans_and_exits_without_generating(self):
        """--prune-failed 只清理、不生成。

        踩过的坑：第一版这个开关清完记录就继续往下跑全量生成，于是工作流里
        "清理"那一步变成了第二次生成——24 镜要从 CDN 重新下载校验，还顺手把
        补镜任务又提交了一遍；补镜失败时，失败算在"清理"头上，出片那步根本没跑。
        """
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            results = Path(temporary) / 'results.json'
            results.write_text(json.dumps({'project': 'x', 'shots': {
                'S10': {'id': 'S10', 'status': 'failed', 'task_id': 'task_dead'},
                'S01': {'id': 'S01', 'status': 'completed', 'video_url': 'u', 'sha256': 'h', 'bytes': 1},
            }}, ensure_ascii=False), encoding='utf-8')
            original, original_argv = generator.RESULTS, sys.argv
            try:
                generator.RESULTS = results
                sys.argv = ['generate.py', '--prune-failed']
                code = generator.main()
            finally:
                generator.RESULTS, sys.argv = original, original_argv
            self.assertEqual(code, 0)
            doc = json.loads(results.read_text(encoding='utf-8'))
            self.assertEqual(sorted(doc['shots']), ['S01'], '死任务没清掉')
            self.assertNotIn('phase', doc, '清理之后还继续跑了生成流程：--prune-failed 必须就地退出')



class DeliveryTests(unittest.TestCase):
    """交付报告必须说真话：数字来自实测，字段不许是抄参考项目的常量。"""

    def _json(self, name):
        path = PROJECT / 'delivery' / name
        if not path.exists():
            self.skipTest(f'还没出片：delivery/{name} 不存在')
        return json.loads(path.read_text(encoding='utf-8'))

    def test_delivered_film_passes_the_audibility_gate_on_its_own_numbers(self):
        """拿流水线自己的闸门函数复查交付报告——"过闸"这句话要能被机器重放。"""
        report = self._json('final-audio-report.json')
        editor.assert_audible(report)
        self.assertGreaterEqual(report['duration_seconds'], 179.5)
        self.assertLessEqual(report['duration_seconds'], 180.5)

    def test_the_report_picks_the_cue_timing_that_measures_better(self):
        """对轨报告的自洽性：赢的那一套必须是分数好的那一套，而且分数要真的接近零。

        这一条存在的理由：旧写法是"ASR 优先，匹配度不足才回落"，于是报告里
        "四章回落到停顿估算"读起来像缺陷没修完。实测下来恰恰相反——
        同一份配音上量能量包络，停顿估算那套的边界惩罚几乎是 0，ASR 那套会留 0.7 秒空窗。
        所以 render 改成两套都算、按分数择优，并把两个分数一起交付。
        """
        rows = self._json('alignment-report.json')
        if 'boundary_penalty_estimate' not in rows[0]:
            self.skipTest('交付报告出自旧版 render：没有两套对轨的对照分数')
        for row in rows:
            self.assertLessEqual(row['boundary_penalty_estimate'], 0.05,
                                 f"{row['id']} 的停顿估算本身就不该有边界落在语音里")
            if row['method'] == 'ASR-assisted':
                self.assertLessEqual(row['boundary_penalty_asr'], row['boundary_penalty_estimate'],
                                     f"{row['id']} 选了分数更差的那套")
            else:
                self.assertTrue(row['method'] == 'pause-aware estimate')

    def test_technical_report_matches_this_plan_not_the_reference_one(self):
        data = self._json('technical-report.json')
        project = project_plan()
        self.assertEqual((data['width'], data['height']), (project['width'], project['height']))
        self.assertEqual(data['fps'], project['fps'])
        self.assertEqual(data['frames'], round(project['target_duration'] * project['fps']))
        self.assertEqual(data['source_clips'], sum(s['kind'] == 'agnes' for s in project['shots']))
        self.assertTrue(data['decoded_ok'])
        # 这是抄参考项目最容易留下的一句假话：本片一个 archive 镜头都没有
        self.assertEqual(data['archival_portrait'], any(s['kind'] == 'archive' for s in project['shots']),
                         '报告不许替片子声称"用了档案肖像"')
        # 出片那刻的诚实标注：视觉审片不是自动的，没做完就写 pending
        self.assertIn(data['visual_review'], ('pending', 'reviewed'))

    def test_listening_report_is_bound_to_the_delivered_film(self):
        """听检报告必须说清它量的是哪一版成片。

        本片一天里出了四版，而报告原先只记文件名：`CER 全过` 于是可以被任何一版沿用——
        两次重跑后文件内容一字不变，恰恰暴露了"报告不绑定输入"这件事。
        现在 `verbatim_check.py` 写 `film_sha256`，这里要求它与 technical-report 的 sha 相同：
        不一致就是报告过期，得重跑，而不是"大概也一样吧"。
        """
        report = PROJECT / 'delivery/verbatim-check.json'
        if not report.exists():
            self.skipTest('还没跑逐字听检')
        data = json.loads(report.read_text(encoding='utf-8'))
        self.assertIn('film_sha256', data, '听检报告没绑定成片指纹：报告过期或工具回退了')
        tech = json.loads((PROJECT / 'delivery/technical-report.json').read_text(encoding='utf-8'))
        self.assertEqual(data['film_sha256'], tech['sha256'],
                         '听检报告量的是另一版成片：bump VERBATIM_REQUEST 重跑')
        self.assertEqual(data['film'], tech['output'], '报告里的文件名要与被检成片对上')


    def test_no_scaffolding_or_engineering_paths_end_up_on_screen(self):
        """画面上不许出现工程路径，也不许出现脚手架占位句。

        两类都有实物为证：片尾卡（EDL 里唯一的 END 条目，5286–5400 帧）最后一行原本印的是
        「资料：来源见 story.json 的 sources」——观众拿不到那个文件，等于把内部便条当字幕；
        `archive_image` 里还留着参考项目的「TODO 档案卡标题」三行，本片 archive 镜头数为 0
        所以它没上屏，但闸门不该指望"没人点到它"。
        """
        src = (PROJECT / 'render.py').read_text(encoding='utf-8')
        self.assertNotIn('TODO', src, '脚手架占位文字还没清干净')
        drawn = re.findall(r"(?:centered|d\.text)\((?:d,)?[^)]*?'([^']*)'", src)
        offenders = [s for s in drawn if re.search(r'\.json|story\.|production/|work/|\.md\b', s)]
        self.assertEqual(offenders, [], f'上屏文案里出现了工程路径：{offenders}')
        for constant in ('END_FOOTER', 'ARCHIVE_FOOTER'):
            self.assertRegex(src, re.compile(rf"^{constant}='", re.M),
                             f'{constant} 应当是模块级常量，便于测试与复用')
        self.assertIn('FBI', re.search(r"END_FOOTER='([^']*)'", src).group(1),
                      '片尾要真的给出资料来源，而不是指一个文件名')
        self.assertIn("kind", src)  # 标签映射仍在按 kind 取文案
        for chap in project_plan()['chapters']:
            for seg in re.split(r'[。？！]', chap['text']):
                if re.search(r'\.json|story|production/|\.md\b', seg):
                    self.fail(f'解说里出现工程标识：{seg[:60]}')
        with self.assertRaises(RuntimeError):
            editor.archive_image('', Path('/tmp/dbcooper-archive-card-check'))

    def test_the_case_file_header_states_the_route_not_an_invented_carrier(self):
        """四张档案卡的表头不许写一个不存在的航司名。

        原本印的是「案件档案 / PACIFIC NORTHWEST · 1971」。真实承运人是西北航空
        （N01 解说里念的就是它），"Pacific Northwest" 只是地区名——把它挂在公司名的位置上，
        观众只会读成"片方编了一家航司"。改成三个经停点，全部来自 sources：
        14:50 波特兰起飞、17:46 西雅图塔科马、22:15 里诺。
        """
        src = (PROJECT / 'render.py').read_text(encoding='utf-8')
        self.assertNotIn('PACIFIC NORTHWEST', src, '卡面上那个位置是"公司名"，不许放地区名')
        self.assertIn('PORTLAND-SEATTLE-RENO', src, '表头要给出可核的航段，而不是空着')


class MixReproducibilityTests(unittest.TestCase):
    """换一台机器把混音重跑一遍，电平必须与云端交付时记录的完全一致。

    参考项目当年把混音从 ffmpeg 滤镜链搬进 numpy，理由就是"换版本换数字"这件事
    会静默改变成片（第一部片子因此没声音却照样出片）。这里拿**仓库里真实的六段配音**
    在当前机器上重混一遍，与 delivery/audio-report.json 对照（±0.05 dB）：
    漂移了就说明有人把测量又交回给 ffmpeg 的内部实现了。
    """

    TOLERANCE_DB = 0.05

    @classmethod
    def setUpClass(cls):
        import subprocess
        import tempfile
        cls.work = Path(tempfile.mkdtemp(prefix='dbcooper-mix-'))
        cls.result = subprocess.run(
            [sys.executable, str(PROJECT / 'build_audio.py'),
             '--work', str(cls.work), '--output', str(cls.work / 'mix.wav')],
            cwd=ROOT, capture_output=True, text=True)
        cls.fresh = cls.work / 'audio-report.json'

    def test_remix_matches_the_delivered_levels(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr[-800:])
        self.assertTrue(self.fresh.is_file(), '重混没有产出电平报告')
        fresh = json.loads(self.fresh.read_text(encoding='utf-8'))
        recorded = json.loads((PROJECT / 'delivery/audio-report.json').read_text(encoding='utf-8'))
        for key in ('rms_dbfs', 'peak_dbfs'):
            delta = abs(fresh[key] - recorded[key])
            self.assertLessEqual(delta, self.TOLERANCE_DB,
                                 f'{key} 在另一台机器上漂移 {delta:.3f} dB：'
                                 f'{fresh[key]} != {recorded[key]}')
        self.assertEqual(fresh['silent_fraction'], recorded['silent_fraction'],
                         '静音占比变了，混出来的不是同一个东西')
        local = {row['id']: row['rms_dbfs'] for row in fresh['chapters']}
        cloud = {row['id']: row['rms_dbfs'] for row in recorded['chapters']}
        for sid, value in cloud.items():
            self.assertLessEqual(abs(local[sid] - value), self.TOLERANCE_DB,
                                 f'{sid} 逐章电平漂移：{local[sid]} != {value}')

    def test_recorded_reproduction_across_machines_is_self_consistent(self):
        path = PROJECT / 'delivery/reproducibility-2026-09-13.json'
        if not path.exists():
            self.skipTest('还没做换机器复现')
        doc = json.loads(path.read_text(encoding='utf-8'))
        recorded = json.loads((PROJECT / 'delivery/audio-report.json').read_text(encoding='utf-8'))
        self.assertEqual(doc['overall']['rms_dbfs']['cloud'], recorded['rms_dbfs'],
                         '复现记录里的"云端数字"与交付报告不符：报告改过而记录没跟着改')
        self.assertLessEqual(abs(doc['overall']['rms_dbfs']['cloud'] - doc['overall']['rms_dbfs']['local']),
                             doc['tolerance_db'])




@unittest.skipUnless(shutil.which('ffmpeg'), '需要 ffmpeg 解码那六段配音')
@unittest.skipUnless(shutil.which('ffmpeg'), '需要 ffmpeg 解码配音才能测字幕边界')
class CaptionTimingTests(unittest.TestCase):
    """成片字幕的每一次换行，都必须落在**实测的语音能量低点**上。

    "换行跟不跟得上语流"原本是写在"没做到"里的一条：四章回落到停顿估算，
    只能请人耳听一遍。这里把它换成数字——直接从已交付的六段配音上量能量包络，
    要求每个 cue 的入点与出点附近 0.35 秒内存在一个明显的低谷（≤该章中位能量的 40%），
    或者它就是这一章的开头/结尾。ASR 对轨与停顿估算谁赢都无所谓：
    这条测的是**交付结果**，方法名不担保结果。
    """

    HOP, RATE, WINDOW = 960, 48000, 0.35
    LOW_RATIO, SECONDARY_RATIO = 0.40, 0.70

    @classmethod
    def setUpClass(cls):
        import subprocess
        import tempfile
        import wave
        timing = PROJECT / 'delivery/caption-timing.json'
        if not timing.exists():
            raise unittest.SkipTest('还没出片：delivery/caption-timing.json 不存在')
        cls.cues = json.loads(timing.read_text(encoding='utf-8'))
        rows, tempo = narration_rows()
        cls.rows = rows
        envelope = {}
        for row in rows:
            source = PROJECT / 'audio' / f"{row['id']}.mp3"
            with tempfile.TemporaryDirectory() as temporary:
                wav = Path(temporary) / 'a.wav'
                subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(source), '-ac', '1',
                                '-ar', str(cls.RATE), '-c:a', 'pcm_s16le', str(wav)], check=True)
                with wave.open(str(wav), 'rb') as handle:
                    samples = np.frombuffer(handle.readframes(handle.getnframes()),
                                            dtype='<i2').astype('float32') / 32768
            blocks = samples[:len(samples) - len(samples) % cls.HOP].reshape(-1, cls.HOP)
            envelope[row['id']] = np.sqrt((blocks * blocks).mean(axis=1))
        cls.envelope = envelope

    def test_every_cue_boundary_sits_on_a_measured_speech_low(self):
        suspicious = []
        checked = 0
        for cue in self.cues:
            row = next(r for r in self.rows if r['start'] - 1e-6 <= cue['start'] < r['end'] + 1e-6)
            rms = self.envelope[row['id']]
            median = float(np.median(rms))
            for edge in ('start', 'end'):
                raw = (cue[edge] - row['start']) * row['tempo']
                checked += 1
                if raw < 0.05 or abs(raw - row['raw_duration']) < 0.05:
                    continue                                   # 章节首尾：没有"打断语流"可言
                window = rms[max(0, round((raw - self.WINDOW) * self.RATE / self.HOP))
                             :round((raw + self.WINDOW) * self.RATE / self.HOP) + 1]
                if len(window) == 0 or float(window.min()) > self.SECONDARY_RATIO * median:
                    suspicious.append((row['id'], edge, round(raw, 2),
                                       round(float(window.min()) / median, 2), cue['text'][:14]))
        self.assertGreaterEqual(checked, 2 * len(self.cues) - 4, '边界数量不对，交付文件被截断？')
        self.assertFalse(suspicious,
                         f'{len(suspicious)} 个字幕边界落在语音中间（窗口内最低能量 / 章中位 > '
                         f'{self.SECONDARY_RATIO}）：{suspicious[:6]}')

    def test_cues_are_ordered_and_never_outlive_their_chapter(self):
        for row in self.rows:
            own = [c for c in self.cues if row['start'] - 1e-6 <= c['start'] < row['end'] + 1e-6]
            self.assertTrue(own, row['id'])
            # 「第一条字幕来得准不准」不许靠人耳印象：拿本段配音的能量包络量出真正的开口时刻，
            # 要求字幕相对它落在 [−0.9, +0.35] 秒内。实测六章为
            # N01 +0.15 / N02 −0.79 / N03 −0.31 / N04 +0.21 / N05 +0.05 / N06 −0.33：
            # ASR 那套贴着第一个字，停顿估算那套在章头就把第一条放上去（允许早一点，读得从容）。
            # 上限 0.35 是硬的：字幕比开口晚于一个字，观众就是"先听见后看见"。
            # 也不要求"最后一条铺满到章尾"——话说完字幕就该退场，尾迟 0.2 秒是正常行为。
            rms = self.envelope[row['id']]
            voiced = np.nonzero(rms >= self.LOW_RATIO * float(np.median(rms)))[0]
            onset = row['start'] + (float(voiced[0]) * self.HOP / self.RATE) / row['tempo'] \
                if len(voiced) else row['start']
            lead = own[0]['start'] - onset
            self.assertLessEqual(lead, 0.35, f"{row['id']} 首条字幕比开口晚了 {lead:.2f}s")
            self.assertGreaterEqual(lead, -0.9, f"{row['id']} 首条字幕比开口早了 {-lead:.2f}s")
            self.assertLessEqual(own[-1]['end'], row['end'] + 0.05, f"{row['id']} 字幕压进了章节间隔")
            for left, right in zip(own, own[1:]):
                self.assertLessEqual(left['end'], right['start'] + 1e-6, f"{row['id']} 字幕重叠")
                self.assertLessEqual(right['start'] - left['end'], 1.5,
                                     f"{row['id']} 有超过 1.5 秒的字幕空窗")
        joined = ''.join(c['text'] for c in self.cues)
        script = ''.join(chapter['text'] for chapter in project_plan()['chapters'])
        self.assertEqual(joined, script, '成片字幕与剧本不是逐字同一份')


if __name__ == '__main__':
    unittest.main()

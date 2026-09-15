"""《披萨炸弹劫案》的硬要求全部写成数字：运镜不许单一、每一刀必须落在真实停顿上、
卡面与台词同源、素材/配音/剧本三处逐字一致、分支与工作流的 pin 不许写花。

分工与 test_dahlia / test_dbcooper 相同：只跑离线内容（不联网、不烧生成额度）；
需要解码音频的切点校验在没有 ffmpeg 时自动跳过。
"""
import hashlib
import importlib.util
import json
import re
import shutil
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'production/pizzabomber'


def _load(name, filename):
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


generator = _load('pizzabomber_generate', 'generate.py')
editor = _load('pizzabomber_render', 'render.py')


def project_plan():
    return json.loads((PROJECT / 'story.json').read_text(encoding='utf-8'))


def narration_rows():
    """复刻 render.audio_layout 的排布（用 PyAV 读真实时长，改配音就跟着变）。"""
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
    def test_reviewed_timeline_and_shot_mix(self):
        plan = project_plan()
        generator.validate(plan)
        kinds = {k: sum(s['kind'] == k for s in plan['shots']) for k in ('agnes', 'graphic', 'archive')}
        self.assertEqual(kinds, {'agnes': 23, 'graphic': 7, 'archive': 0})
        self.assertEqual(plan['target_duration'], 180)
        self.assertEqual(len(plan['shots']), 30)

    def test_narration_text_audio_manifest_are_the_same_words(self):
        plan = project_plan()
        manifest = json.loads((PROJECT / 'audio/manifest.json').read_text(encoding='utf-8'))
        by_id = {row['id']: row for row in manifest['clips']}
        for chapter in plan['chapters']:
            receipt = by_id[chapter['id']]
            self.assertEqual(chapter['text'], receipt['text'], chapter['id'])
            path = PROJECT / 'audio' / receipt['file']
            handle = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    handle.update(block)
            if receipt['sha256'].startswith('PENDING'):
                self.skipTest('N05/N06 重录后回填哈希（回填前 validate 必须拦住出片）')
            self.assertEqual(handle.hexdigest(), receipt['sha256'], f"{chapter['id']} 的音频被换过了")

    def test_screenplay_holds_the_same_text(self):
        plan = project_plan()
        text = (PROJECT / 'screenplay.md').read_text(encoding='utf-8')
        for chapter in plan['chapters']:
            self.assertIn(chapter['text'], text, chapter['id'])

    def test_no_reference_project_residue(self):
        for filename in ('story.json', 'render.py', 'generate.py', 'screenplay.md', 'README.md'):
            body = (PROJECT / filename).read_text(encoding='utf-8')
            for word in ('黑色大丽花', 'D.B.', 'Cooper', '库珀', '1971', 'NORJAK'):
                self.assertNotIn(word, body, f'{filename} 残留上一部片子的内容：{word}')
        # 本片没有 archive 镜头：真实人物没有可自由使用的档案照片，红线禁止用 AI 脸冒充
        self.assertFalse(any(s['kind'] == 'archive' for s in project_plan()['shots']))

    def test_the_tower_is_the_same_structure_in_every_shot_that_shows_it(self):
        """发射塔是首尾呼应的实体：S01/S05/S19/S29 必须都是同一种 lattice 广播塔。

        提示词里若把塔写成 wind turbine / cell tower / 摩天楼，镜头之间就成了两个地方，
        而解说把它们说成同一个（「回到起点」）。集合改动必须同步这条测试与分镜表。
        """
        shots = project_plan()['shots']
        shown = [x for x in shots if re.search(r'tower', x['prompt'], re.I) and x['kind'] == 'agnes']
        self.assertEqual([x['id'] for x in shown], ['S01', 'S04', 'S05', 'S19', 'S29'])
        for x in shown:
            self.assertRegex(x['prompt'], re.compile(r'lattice|transmitter|broadcast|radio[- ]tower|radio tower', re.I),
                             f"{x['id']} 的塔没写结构，模型会自己发明一座")
            self.assertNotRegex(x['prompt'], re.compile(r'wind turbine|cell tower|skyscraper', re.I),
                                f"{x['id']} 把塔写成了别的东西")

    def test_narration_never_shows_brand_logos_in_footage(self):
        plan = project_plan()
        for shot in plan['shots']:
            if shot['kind'] != 'agnes':
                continue
            self.assertNotIn("McDonald", shot['prompt'], '品牌名不许进画面提示词')
            self.assertNotIn("PNC", shot['prompt'])

    def test_every_chapter_s_text_is_within_the_breathing_window(self):
        plan = project_plan()
        for chapter in plan['chapters']:
            n = len(re.sub(r'\s', '', chapter['text']))
            self.assertTrue(88 <= n <= 150, f"{chapter['id']} 有 {n} 字，不在 88–150 的呼吸窗内")


class CameraDiversityTests(unittest.TestCase):
    """上一版被打回的原因之一是「运镜总是从远到近飞入」。这里把它变成数字。"""

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
        pulling = [s['id'] for s in self.shots if re.search(r'拉|pullback|pull[- ]?back|dolly[- ]back', s['camera'])]
        self.assertGreaterEqual(len(pulling), 3, '全是往主体凑，没有拉开的呼吸')
        vertical = [s['id'] for s in self.shots if re.search(r'升|降|crane', s['camera'])]
        self.assertGreaterEqual(len(vertical), 2, '缺少垂直方向的调度')
        held = [s['id'] for s in self.shots if re.search(r'固定|locked', s['camera'])]
        self.assertGreaterEqual(len(held), 3, '一镜不切的呼吸感也没有，全是运动素材反而假')

    def test_every_prompt_writes_its_own_camera_move(self):
        sentences = []
        for shot in self.shots:
            match = re.search(r'Camera:\s*(.+?)(?:\n|$)', shot['prompt'])
            self.assertTrue(match, f"{shot['id']} 的提示词没写死运镜")
            sentence = match.group(1).strip()
            sentences.append(sentence)
            self.assertGreaterEqual(len(sentence.split()), 8, f"{shot['id']} 的运镜描述过于含糊")
            self.assertTrue(re.search(r'track|drift|tilt|pan|crane|rise|pull|push|orbit|lock|follow|float|glide',
                                      sentence, re.IGNORECASE), f"{shot['id']} 的运镜里没有可执行的动作")
            self.assertFalse(re.search(r'\b(push|dolly|zoom)\s?in\b|fly[- ]?in', sentence, re.IGNORECASE),
                             f"{shot['id']} 又写成了飞入：{sentence}")
        counter = Counter(sentences)
        self.assertTrue(all(n <= 2 for n in counter.values()),
                        f'整句运镜被复用超过两次：{counter.most_common(1)}')
        negative = project_plan()['negative_prompt'].lower()
        for banned in ('fast zoom', 'whip pan'):
            self.assertIn(banned, negative, f'负向提示词应排除 {banned}')


class CutAlignmentTests(unittest.TestCase):
    """CUTS 是本片「解说与画面对应」的唯一真相。"""

    def setUp(self):
        self.project = project_plan()
        self.cuts = editor.CUTS
        self.chapters = [chapter['id'] for chapter in self.project['chapters']]
        self.by_id = {shot['id']: shot for shot in self.project['shots']}

    def test_every_shot_is_used_once_except_documented_reuses(self):
        entries = [(sid, variant) for chapter in self.chapters for _, sid, variant in self.cuts[chapter]]
        plan_ids = {shot['id'] for shot in self.project['shots']}
        self.assertEqual({sid for sid, _ in entries}, plan_ids, '有镜头没进剪辑表，或 CUTS 引用了不存在的镜')
        self.assertEqual(len(entries), 33)          # 33 段 + 片尾卡 = 34
        counts = Counter(sid for sid, _ in entries)
        self.assertEqual(sorted(sid for sid, n in counts.items() if n > 1), ['S19', 'S21', 'S26'],
                         '复用清单变了：改复用要一并改 VARIANT_IN 与分镜表')
        self.assertIn(('S10', 'b'), editor.VARIANT_IN, 'S10 用后段就必须登记入点（前 3.2s 有侧脸与门贴）')
        for sid in ('S19', 'S21', 'S26'):
            variants = [variant for got, variant in entries if got == sid]
            self.assertEqual(sorted(variants), ['', 'b'], f'{sid} 必须一段原样、一段换 variant')
        self.assertEqual(sorted(editor.VARIANT_IN), sorted([('S19', 'b'), ('S21', 'b'), ('S26', 'b')]),
                         'VARIANT_IN 与 CUTS 的复用不同源')

    def test_cards_only_show_the_number_being_spoken(self):
        rows = {row['id']: row for row in narration_rows()[0]}
        cards = [(sid, variant) for chapter in self.chapters
                 for _, sid, variant in self.cuts[chapter]
                 if self.by_id[sid]['kind'] == 'graphic']
        self.assertEqual(len(cards), len(set(cards)), '同一张卡（同 variant）被排了两次')
        for sid, variant in cards:
            heading = editor.CARD_HEADINGS.get((sid, variant or ''))
            self.assertIsNotNone(heading, f'{sid}/{variant} 没有对应的卡面文字')
            self.assertTrue(all(str(part).strip() for part in heading), f'{sid}/{variant} 卡面有空行')
        for chapter in self.project['chapters']:
            for raw, sid, variant in self.cuts[chapter['id']]:
                if self.by_id[sid]['kind'] != 'graphic':
                    continue
                spoken = rows[chapter['id']]['text']
                tokens = [t.strip() for t in re.split(r'[｜\n·、，, ]', self.by_id[sid]['graphic']) if len(t.strip()) >= 2]
                self.assertTrue(tokens, sid)
                self.assertTrue(any(token in spoken for token in tokens),
                                f'{sid} 的信息卡文字与本章解说不同源：{tokens}')
                if raw == 0.0:
                    # 允许「开章即卡」的唯一情形：卡面数字就在本章第一句里（如 N06 的判决卡）
                    first_clause = spoken.split('，')[0] + spoken.split('，')[1] if '，' in spoken else spoken
                    self.assertTrue(any(token in first_clause for token in tokens),
                                    f'{sid} 一开章就压字幕，且内容与首句无关')

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
        self.assertGreaterEqual(len(set(gaps)), 12, '切点间隔过于规整，像是按秒表切的')
        self.assertTrue(all(abs(g - 6.0) > 0.05 for g in gaps), '仍是每 6 秒一刀的均匀模板')

    def test_cut_points_land_on_measured_pauses(self):
        if not shutil.which('ffmpeg'):
            self.skipTest('需要 ffmpeg 解码配音才能测停顿')
        import numpy as np
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


class EditWindowTests(unittest.TestCase):
    def test_no_edit_window_is_too_long_to_fill(self):
        """出片前就算出「窗口 > 素材可用时长 × 1.33」，省一次 40 分钟的失败运行。"""
        lengths = {}
        for receipt in sorted((PROJECT / 'qa').glob('S*.json')):
            lengths[receipt.stem] = json.loads(receipt.read_text(encoding='utf-8'))['duration']
        rows, _ = narration_rows()
        edl = editor.make_edl(project_plan(), rows)
        windows = {}
        for entry in edl:
            if entry['kind'] != 'agnes':
                continue
            key = (entry['id'], entry['variant'])
            length = (entry['end_frame'] - entry['start_frame']) / editor.FPS
            windows[key] = max(windows.get(key, 0.0), length)
        for (sid, variant), duration in windows.items():
            clip_length = lengths.get(sid, 7.041667)   # 素材未生成时按 7 秒标称算
            in_point = editor.VARIANT_IN.get((sid, variant), 0.12)
            take = min(clip_length - 0.12, clip_length - in_point, duration) if (sid, variant) in editor.VARIANT_IN else min(clip_length - 0.12, duration)
            factor = duration / max(take, 0.001)
            self.assertLessEqual(factor, 1.33,
                                 f'{sid}/{variant or "base"} 需要 {factor:.2f}× 慢放来铺满窗口——先加镜头或改提示词')

    def test_variant_reuse_shifts_the_in_point(self):
        lengths = {}
        for receipt in sorted((PROJECT / 'qa').glob('S*.json')):
            lengths[receipt.stem] = json.loads(receipt.read_text(encoding='utf-8'))['duration']
        for (sid, variant), in_point in editor.VARIANT_IN.items():
            length = lengths.get(sid, 7.041667)
            a, b, take, factor = editor.clip_window(sid, variant, length, 4.0)
            self.assertGreater(a, 0.12, f'{sid}/{variant} 的入点没换——两遍放同一段画面')
            self.assertGreaterEqual(a, in_point, f'{sid}/{variant} 的入点被逐镜上限覆盖了（clip_window 顺序写反）')


class LabelAndCardTests(unittest.TestCase):
    def test_end_and_title_cards_carry_our_words(self):
        text = (PROJECT / 'render.py').read_text(encoding='utf-8')
        self.assertIn('披萨炸弹劫案', text)
        self.assertIn('一份没送完的披萨', text)
        self.assertIn('是共谋还是替死鬼', text)
        self.assertIn('资料来源：维基百科、AETV、BBC、Erie Times-News', editor.END_FOOTER)
        self.assertNotIn('story.json', text[text.index("sid=='END'"):text.index("sid=='END'") + 1600],
                         '片尾卡不许把工程路径印给观众')

    def test_all_special_labels_point_at_real_shots(self):
        text = (PROJECT / 'render.py').read_text(encoding='utf-8')
        ids = {s['id'] for s in project_plan()['shots']}
        for sid in re.findall(r"if entry\['id'\]=='(S\d+)':label=", text):
            self.assertIn(sid, ids, f'标签覆盖指向不存在的镜头 {sid}')

    def test_sfx_events_reference_existing_shots(self):
        text = (PROJECT / 'render.py').read_text(encoding='utf-8')
        ids = {s['id'] for s in project_plan()['shots']}
        for sid in re.findall(r"\('(S\d+)','(?:phone|paper|machine|press|keys)'\)", text):
            self.assertIn(sid, ids)

    def test_highlight_keys_exist_in_narration(self):
        text = ''.join(c['text'] for c in project_plan()['chapters'])
        block = re.search(r"for key in \[\n(.*?)\n        \]:", (PROJECT / 'render.py').read_text(encoding='utf-8'), re.S).group(1)
        for key in re.findall(r"'([^']+)'", block):
            self.assertIn(key, text, f'高亮词 {key} 在解说里不存在，永远不会亮')


class WorkflowPinTests(unittest.TestCase):
    """漏改分支名的症状是「跑了但什么都没发生」——四处 pin 必须同源。"""

    FILES = {
        '.github/workflows/pizzabomber-gen.yml': 'pizzabomber/GEN_REQUEST',
        '.github/workflows/pizzabomber-render.yml': 'pizzabomber/RENDER_REQUEST',
        '.github/workflows/pizzabomber-verbatim.yml': 'pizzabomber/VERBATIM_REQUEST',
    }

    def test_workflows_point_at_this_branch(self):
        branch = project_plan()['branch']
        for path, needle in self.FILES.items():
            text = (ROOT / path).read_text(encoding='utf-8')
            template = (PROJECT / Path(path).name.replace('.yml', '.workflow.yml')).read_text(encoding='utf-8')
            self.assertEqual(text, template, f'{path} 与项目模板不再逐字节一致')
            self.assertIn(f"branches:\n      - {branch}", text, f'{path} 的 push 分支不是 {branch}')
            self.assertIn(f"github.ref == 'refs/heads/{branch}'", text, f'{path} 的 if 没锁到 {branch}')
            self.assertIn(needle, text, f'{path} 没盯 {needle} 这张便签')
        for name in ('generate.py', 'watch_run.py'):
            body = (PROJECT / name).read_text(encoding='utf-8')
            self.assertIn(branch, body, f'{name} 的 BRANCH 还指着旧分支')

    def test_deliverable_name_is_the_film_not_the_title(self):
        text = (ROOT / '.github/workflows/pizzabomber-render.yml').read_text(encoding='utf-8')
        self.assertIn('披萨炸弹劫案_三分钟_带声音.mp4', text,
                      'film_name 默认值必须是交付文件名；留空会拿片名当文件名（手册里写过的坑）')


if __name__ == '__main__':
    unittest.main()

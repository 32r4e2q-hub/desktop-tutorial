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
        self.assertEqual(len(entries), 31)                       # 31 个编辑段 + 片尾卡 = 32
        self.assertEqual({sid for sid, _ in entries}, agnes | {'S03', 'S08', 'S20', 'S23', 'S27'})
        counts = Counter(sid for sid, _ in entries)
        # 只有 S06 允许回到同一素材（'b' 变体取同一镜的后半段），其余一镜一次
        self.assertEqual(sorted(sid for sid, n in counts.items() if n > 1), ['S06'])
        self.assertEqual(counts['S06'], 2)
        self.assertEqual(sorted({variant for sid, variant in entries if sid == 'S06'}), ['', 'b'])

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


class EdlTests(unittest.TestCase):
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

    def test_marker_file_is_the_agent_side_trigger(self):
        text = self._workflow_text()
        block = text.split('push:', 1)[1]
        self.assertIn('production/dbcooper/GEN_REQUEST', block.split('permissions:', 1)[0],
                      'push 触发没有只看 GEN_REQUEST，逐镜 checkpoint 会把出片循环点着')

    def test_prune_step_runs_before_generation(self):
        text = self._workflow_text()
        self.assertIn('--prune-failed', text)
        self.assertLess(text.index('--prune-failed'), text.index('--publish'),
                        '清理死任务必须发生在生成之前')

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
        self.assertIn(f"if: github.ref == 'refs/heads/{generator.BRANCH}'", text,
                      '出片工作流的 if 还指着别的分支')
        block = text.split('push:', 1)[1].split('permissions:', 1)[0]
        self.assertIn('production/dbcooper/RENDER_REQUEST', block,
                      'push 触发没有只看 RENDER_REQUEST')
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


if __name__ == '__main__':
    unittest.main()

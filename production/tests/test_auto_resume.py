"""auto_resume.decide() 的行为：循环直到全部生成，但连续零进展要停。"""
import importlib.util
import json
import pathlib
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    'hwaseong1986_auto_resume', HERE.parent / 'hwaseong1986' / 'auto_resume.py')
auto_resume = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(auto_resume)


def write_pair(tmp, phase='provider_capacity', done=3, payload=None):
    req = pathlib.Path(tmp) / 'GEN_REQUEST'
    res = pathlib.Path(tmp) / 'results.json'
    payload = dict(payload or {'round': 2})
    req.write_text(json.dumps(payload, ensure_ascii=False))
    shots = {}
    for i in range(done):
        shots['S%02d' % (i + 1)] = {'status': 'completed'}
    shots['S99'] = {'status': 'waiting_create_slot'}
    res.write_text(json.dumps({'phase': phase, 'shots': shots}))
    return req, res


class AutoResumeTests(unittest.TestCase):
    def test_resumes_and_bumps_the_round_when_still_capacity(self):
        with tempfile.TemporaryDirectory() as tmp:
            req, res = write_pair(tmp)
            verdict, msg = auto_resume.decide(req, res)
            self.assertEqual(verdict, 'resume', msg)
            payload = json.loads(req.read_text())
            self.assertEqual(payload['round'], 3)
            self.assertEqual(payload['round_started_completed'], 3)
            self.assertEqual(payload['stale_rounds'], 0)

    def test_progress_resets_the_stale_counter(self):
        with tempfile.TemporaryDirectory() as tmp:
            req, res = write_pair(tmp, done=5,
                                  payload={'round': 3, 'round_started_completed': 3,
                                           'stale_rounds': 2})
            verdict, _ = auto_resume.decide(req, res)
            self.assertEqual(verdict, 'resume')
            payload = json.loads(req.read_text())
            self.assertEqual(payload['stale_rounds'], 0, '有产出就要把连零计数清零')

    def test_no_progress_increments_and_eventually_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            req, res = write_pair(tmp, done=3,
                                  payload={'round': 3, 'round_started_completed': 3,
                                           'stale_rounds': 0})
            for want in (1, 2):
                verdict, _ = auto_resume.decide(req, res)
                self.assertEqual(verdict, 'resume')
                self.assertEqual(json.loads(req.read_text())['stale_rounds'], want)
            verdict, msg = auto_resume.decide(req, res)
            self.assertEqual(verdict, 'stop', '第 3 轮连零必须停：' + msg)

    def test_does_not_resume_when_the_film_is_done(self):
        with tempfile.TemporaryDirectory() as tmp:
            req, res = write_pair(tmp, phase='first_cut_ready')
            verdict, _ = auto_resume.decide(req, res)
            self.assertEqual(verdict, 'skip')

    def test_does_not_resume_on_a_real_failure_like_quota(self):
        with tempfile.TemporaryDirectory() as tmp:
            req, res = write_pair(tmp, phase='quota_exhausted')
            verdict, _ = auto_resume.decide(req, res)
            self.assertEqual(verdict, 'skip')

    def test_hard_cap_stops_even_with_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            req, res = write_pair(tmp, done=9, payload={'round': 40,
                                                        'round_started_completed': 3})
            verdict, _ = auto_resume.decide(req, res)
            self.assertEqual(verdict, 'stop')


if __name__ == '__main__':
    unittest.main()

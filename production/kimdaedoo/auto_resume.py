"""自动续投：免费池排队满时，要不要再投一轮，直到镜头全部生成。

为什么需要它：`agnes-video-2.5-flash` 是免费的，代价是**排队靠抽签**。
2026-10-17 11:45–12:45Z 实测连续 21 次 `video queue is full`、一个都没开闸；
一轮 job 的排队预算是 110 分钟，抽完就结束，靠人盯着重新点一遍不现实。

设计（与模板 production/kitakyushu2002/auto_resume.py 同构）：
- 已生成的镜头按 SHA-256 断点复用，剩下的镜头下一轮接着抽；
- 保护闸：连续 STALE_STOP 轮一个镜头都没多 → 大概率供应商停摆，停下来等人看，
  避免空烧 runner；硬上限 CAP_ROUNDS 轮双保险。

判定「这一轮是不是排队满收工」看两路证据：
- results.json 的 phase == provider_capacity；
- generate.py 的退出码 42（容量满）。退出码写在 runner 本地文件里，git push 失败也误不了事。
  43（额度耗尽）/ 1（真 bug）不接力。
"""
import json
import os
import pathlib
import sys

CAP_ROUNDS = 40      # 绝对硬上限
# 连续这么多轮零进展就停（每轮约 110 分钟排队预算）。
# 2026-10-21 21:02Z 实测：3 轮 ≈5.5 小时零产出就自动停了，可当时只差 S15/S18/S19/S22/S27/S30
# 六镜，免费池在凌晨又开闸——流水线白白空转了 4 个多小时没人接手。改成 6 轮（≈11 小时），
# 宁可多抽几轮（公共仓库 runner 不额外计费），也不要让整条线在半夜里静默停摆。
STALE_STOP = 6


def decide(req_path, res_path, rc=None, cap_rounds=CAP_ROUNDS, stale_stop=STALE_STOP):
    """返回 (verdict, msg)：verdict ∈ {resume, skip, stop}。"""
    req = pathlib.Path(req_path)
    res = pathlib.Path(res_path)
    if not req.is_file() or not res.is_file():
        return 'skip', '缺 GEN_REQUEST 或 results.json'
    if rc == 43:
        return 'skip', '退出码 43：额度耗尽，接力也没用，等人处理'
    if rc == 1:
        return 'skip', '退出码 1：流水线真故障，等人修，不接力'
    doc = json.loads(res.read_text(encoding='utf-8'))
    capacity = doc.get('phase') == 'provider_capacity' or rc == 42
    if not capacity:
        return 'skip', 'phase=%s rc=%s（不是排队满，不续投）' % (doc.get('phase'), rc)
    payload = json.loads(req.read_text(encoding='utf-8'))

    rounds = int(payload.get('round', 1))
    if rounds >= cap_rounds:
        return 'stop', '已到硬上限 %d 轮，人工看一眼再继续' % cap_rounds

    done = sum(1 for v in doc.get('shots', {}).values() if v.get('status') == 'completed')
    started_with = int(payload.get('round_started_completed', 0))
    stale = int(payload.get('stale_rounds', 0))
    if done > started_with:
        stale = 0                      # 这轮有产出，连零计数清零
    else:
        stale += 1                     # 这轮一个都没多
    if stale >= stale_stop:
        return 'stop', '连续 %d 轮零进展（约 %d 小时无产出），疑似供应商停摆，等人来看' % (
            stale, stale * 110 // 60)

    payload['round'] = rounds + 1
    payload['round_started_completed'] = done
    payload['stale_rounds'] = stale
    req.write_text(json.dumps(payload, ensure_ascii=False) + '\n', encoding='utf-8')
    return 'resume', 'round=%d 已完成=%d 连零=%d' % (rounds + 1, done, stale)


def main(argv):
    rc = None
    if '--rc' in argv:
        idx = argv.index('--rc') + 1
        raw = argv[idx] if idx < len(argv) else ''
        try:
            rc = int(raw)
        except ValueError:
            rc = None
    verdict, msg = decide('production/kimdaedoo/GEN_REQUEST',
                          'production/kimdaedoo/results.json', rc=rc)
    print('AUTO_RESUME %s: %s' % (verdict, msg))
    out = os.environ.get('GITHUB_OUTPUT')
    if out:
        with open(out, 'a') as handle:
            handle.write('verdict=%s\n' % verdict)
            handle.write('resume=%s\n' % ('true' if verdict == 'resume' else 'false'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))

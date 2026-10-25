"""Receipt-based bounded relay, following kitakyushu2002/auto_resume.py and official workflow dispatch.
No paid provider, no moderation retries, no implicit claim of final visual approval.
"""
import argparse
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_ROUNDS = 40


def decide(project, results, options, rc, stopped=False):
    if stopped or not options.get('auto_resume', False):
        return 'stop', options, 'loop disabled/stopped'
    if options.get('only') or options.get('force'):
        return 'stop', options, 'partial/forced requests never auto-chain'
    import generate_cogvideox as engine
    required = [s for s in project['shots'] if s['kind'] in ('agnes', 'cogvideo')]
    if len(required) != 38:
        return 'stop', options, 'invalid dynamic shot count'
    def verified(shot):
        row = results.get('shots', {}).get(shot['id'], {})
        return (engine.usable_receipt(row, engine.request_hash(project, shot))
                and len(row.get('sha256', '')) == 64 and row.get('bytes', 0) > 0
                and row.get('media', {}).get('decoded_ok') is True)
    # The generator and relay are separate Python processes. Reconstruct its image
    # mode rather than silently hashing I2V receipts as plain text-to-video.
    saved_mode = engine.REF_IMAGE_OK
    requested_mode = engine.parse_ref_image(options.get('ref_image'))
    modes = (False, True) if requested_mode is None else (requested_mode,)
    try:
        ready = True
        for shot in required:
            matches = False
            for mode in modes:
                engine.REF_IMAGE_OK = mode
                if verified(shot):
                    matches = True
                    break
            if not matches:
                ready = False
                break
    finally:
        engine.REF_IMAGE_OK = saved_mode
    if rc == 0 and ready:
        return 'render', options, 'all 38 current-request media receipts verified; first cut still needs QC'
    if rc != 42 or results.get('phase') not in ('provider_capacity', 'generation_incomplete'):
        return 'stop', options, 'not a retryable capacity/pending-task exit; inspect diagnostic'
    round_no = int(options.get('round', 1))
    if round_no >= MAX_ROUNDS:
        return 'stop', options, '40-round safety budget reached; manual inspection required'
    next_options = dict(options, round=round_no + 1)
    return 'resume', next_options, 'retry missing shots only; preserve accepted tasks and completed receipts'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--rc', type=int, required=True)
    p.add_argument('--payload', default='{}')
    args = p.parse_args()
    project = json.loads((HERE/'story.json').read_text())
    results = json.loads((HERE/'results.json').read_text())
    options = json.loads(args.payload)
    action, payload, reason = decide(project, results, options, args.rc, (HERE/'LOOP_STOP').exists())
    state = {'action': action, 'reason': reason, 'round': options.get('round', 1),
             'next_payload': payload, 'exit_code': args.rc,
             'completed': sum(r.get('status') == 'completed' for r in results.get('shots', {}).values()),
             'source_run_id': os.getenv('GITHUB_RUN_ID'), 'dispatch_status': 'intent only; confirm with dispatch step and next workflow run'}
    (HERE/'loop-state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n')
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write('action='+action+'\npayload='+json.dumps(payload, separators=(',', ':'))+'\n')
    print(json.dumps(state, ensure_ascii=False))


if __name__ == '__main__':
    main()

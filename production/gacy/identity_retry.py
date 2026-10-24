"""At most three reference-identity experiment rounds with 10-minute capacity cooldowns.
Only known transient service/capacity rejections qualify. Never retry moderation/auth/schema
errors or unknown POST outcomes; never replace reference conditioning with text-only output.
"""
import time
from pathlib import Path


def run_with_cooldown(engine, rounds=3, cooldown=600):
    from identity_probe import run_probe
    return run_rounds(engine, run_probe, rounds, cooldown)


def run_rounds(engine, experiment, rounds=3, cooldown=600):
    record = engine.HERE/'identity-probe/retry-status.json'
    for round_index in range(rounds):
        engine.save(record, {'round':round_index+1,'max_rounds':rounds,'status':'running',
            'capacity_cooldown_seconds':cooldown,'reference_input_required':True})
        try:
            result=experiment(engine)
            engine.save(record, {'round':round_index+1,'max_rounds':rounds,
                'status':'experiment_finished_requires_visual_review','same_actor_verified':False})
            return result
        except engine.VideoPendingError as exc:
            last = round_index+1==rounds
            engine.save(record, {'round':round_index+1,'max_rounds':rounds,
                'status':'awaiting_provider' if last else 'pending_task_cooldown',
                'task_id':exc.task_id,'last_provider_status':exc.last_status,
                'new_submission_allowed':False,'same_actor_verified':False})
            if last: raise
            print('Still processing: next round resumes the exact task ID; no replacement submission',flush=True)
            time.sleep(min(cooldown,60))
        except engine.ProviderError as exc:
            if not exc.transient or round_index+1==rounds:
                engine.save(record, {'round':round_index+1,'max_rounds':rounds,
                    'status':'stopped','http_status':exc.status,'code':exc.code,
                    'same_actor_verified':False})
                raise
            engine.save(record, {'round':round_index+1,'max_rounds':rounds,
                'status':'capacity_cooldown','http_status':exc.status,'code':exc.code,
                'next_attempt_unix':int(time.time()+cooldown),'same_actor_verified':False})
            print(f'Reference identity probe: transient {exc.status}/{exc.code}; cooldown {cooldown}s before bounded round {round_index+2}/{rounds}',flush=True)
            time.sleep(cooldown)
        except Exception as exc:
            engine.save(record, {'round':round_index+1,'max_rounds':rounds,
                'status':'stopped_error','error_type':type(exc).__name__,
                'automatic_retry_allowed':False,'same_actor_verified':False})
            raise

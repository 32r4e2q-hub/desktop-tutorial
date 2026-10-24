"""Evidence-bound release gate, NOT a face-recognition algorithm or an identity guarantee.
A missing detector or absent review is never PASS. Gray-pixel similarity is not identity.
"""
import hashlib
import json
from pathlib import Path

APPEARANCES = {
    'C1': {'name':'adult man', 'reference':'references/盖西.jpg', 'shots':['S05','S06','S08','S09','S13','S20']},
    'C1-makeup': {'name':'same character in entertainer makeup', 'reference':'references/波戈.jpg', 'shots':['S03','S04']},
    'C2': {'name':'mother', 'reference':'references/母亲.jpg', 'shots':['S12','S14','S15','S17']},
    'C3': {'name':'principal investigator', 'reference':'references/警探.jpg', 'shots':['S17','S18','S20']},
    'C4': {'name':'judge', 'reference':'references/法官与陪审团.jpg', 'shots':['S07','S25']},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate(project, receipts, review):
    project=Path(project).resolve()
    issues=[]
    checked=[]
    for cid,appearance in APPEARANCES.items():
        reference=project/appearance['reference']
        reference_hash=digest(reference) if reference.exists() else None
        accepted_sources=[]
        for sid in appearance['shots']:
            clip=receipts.get('shots',{}).get(sid,{})
            decision=review.get('appearances',{}).get(cid,{}).get(sid,{})
            reasons=[]
            if clip.get('status')!='downloaded' or not clip.get('sha256'):
                reasons.append('missing downloaded clip receipt')
            if not reference_hash:
                reasons.append('canonical reference missing')
            if not reference_hash or decision.get('reference_sha256')!=reference_hash:
                reasons.append('canonical reference not reviewed or has changed')
            if not clip.get('sha256') or decision.get('source_sha256')!=clip.get('sha256'):
                reasons.append('clip not reviewed or has changed')
            if decision.get('decision')!='same_identity' or decision.get('face_visibility')!='clear':
                reasons.append('clear visible identity has not been accepted')
            if decision.get('reviewer_type') not in ('human_visual_review','agent_visual_review') or not decision.get('reviewer'):
                reasons.append('no accountable visual reviewer')
            evidence=decision.get('evidence',[])
            hashes=set()
            for item in evidence:
                path=(project/item.get('path','')).resolve()
                if not path.is_relative_to(project) or not path.is_file():
                    reasons.append('missing or invalid evidence path');continue
                value=digest(path)
                if value!=item.get('sha256'):
                    reasons.append('evidence changed');continue
                hashes.add(value)
            if len(hashes)<3:
                reasons.append('requires three distinct beginning/middle/end evidence frames')
            checked.append({'appearance':cid,'shot':sid,'accepted':not reasons,'issues':reasons})
            if reasons:issues.append(f'{cid}/{sid}: '+ '; '.join(reasons))
            else:accepted_sources.append(clip['sha256'])
        if len(set(accepted_sources))<2:
            issues.append(cid+': fewer than two distinct reviewed source clips; cross-shot identity unproven')
    link=review.get('makeup_identity_link',{})
    ref_main=project/APPEARANCES['C1']['reference'];ref_makeup=project/APPEARANCES['C1-makeup']['reference']
    if (not ref_main.exists() or not ref_makeup.exists() or
        link.get('main_reference_sha256')!=(digest(ref_main) if ref_main.exists() else None) or
        link.get('makeup_reference_sha256')!=(digest(ref_makeup) if ref_makeup.exists() else None) or
        link.get('decision')!='same_underlying_character' or not link.get('reviewer')):
        issues.append('the unpainted and made-up character have not been reviewed as the same underlying character')
    return {'status':'PASS' if not issues else 'NEEDS_IDENTITY_REVIEW',
            'publishable':not issues,'checked':checked,'issues':issues,
            'note':'This is an accountable evidence gate, not automatic biometric proof. Actor-level consistency requires actual visual comparison; identical text, seed or a queued reference request is not proof.'}


def write_report(project):
    project=Path(project)
    receipts=json.loads((project/'receipts.json').read_text()) if (project/'receipts.json').exists() else {}
    review=json.loads((project/'identity-review.json').read_text()) if (project/'identity-review.json').exists() else {}
    result=evaluate(project,receipts,review)
    (project/'identity-gate-report.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    result=write_report(Path(__file__).resolve().parent)
    print(result['status'])
    raise SystemExit(0 if result['publishable'] else 1)

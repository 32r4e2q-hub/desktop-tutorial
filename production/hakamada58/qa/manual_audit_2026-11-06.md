# Hakamada 58 motion re-review — 2026-11-06

Status: in progress. This is a second-pass review after the user's continuity/warping report. The earlier nine-frame review is not sufficient as final acceptance.

## Confirmed failures in the previous cut

- **S03 → S04 continuity:** the old S03 sheet showed the red fire engine and villagers carrying buckets before the narrated arrival. Old S04 repeated the house and villagers, violating shot order and duplicating the cast.
- **S20 logic:** the old shot began with Shuko handing out leaflets at the station, then switched to a household clothesline and laundry unrelated to the narration.

## Retake status — dense all-frame review in progress

- **S03:** all 144 labeled frames (0–5.96 s) reviewed. The empty-street fire remains in the same location throughout; no vehicle, people, hose, or crowd appears, and no obvious shape/continuity defect was seen. Pass for this shot's visual/logical criteria.
- **S04:** the prior 144-frame version and a prompt-only retry are rejected: both showed prominent yellow cross emblems, and neither had a clear water stream. The newest reference-conditioned retake's nine-frame sheet shows a plain red engine without crosses, three firefighters, and a visible water stream. It remains a preliminary pass until all 144 frames are audited.
- **S12:** the old 144-frame version is rejected: it is an oblique room/table view and does not preserve the exact five clean garments. The reference-conditioned retake now has a nine-frame sheet showing a true overhead view of exactly five clean garments, with no people, fire, stains, or pseudo-text. Preliminary pass only; full 144-frame audit remains mandatory.
- **S20:** both the old 144-frame version and the reference-conditioned retake (workflow `42244655816`, task `task_8JVWYkr9v8JHiIJhLJWvo8jftml0rB43`) are rejected: the new nine-frame sheet still cuts from a wide station view to repeated hand/paper close-ups. A further prompt now keeps both people full-body at a fixed distance and makes the handoff small and waist-level; third retake queued in workflow pending.
- **S23:** the original 144 frames show the appeal stamp action until 3.25 seconds, then hard-cut to an unrelated window-side desk shot. Rejected. The new retake (workflow `42245032106`, task `task_0JdcYMj6BoTfYSYvTAL0guHjInp2qwro`) has a nine-frame sheet of one coherent stamp-and-blank-paper table scene with no unrelated cut. Preliminary pass only; full 144-frame audit remains required.
- **S22:** the original 144 frames and first retake (workflow `42246557334`) both reveal an unrequested sequence of exterior, gate, escort, and isolated close-ups; the first retake's nine-frame sheet still ends on the sister alone. Rejected for continuity and character-presence drift. The second retake (workflow `42290123978`, task `task_7l0Pv4qj7ZtWJPbLjUqpYtZ6nEO8CRC1`) now has a nine-frame sheet of both siblings stationary/full-body in one wide frame outside the open gate, with no cuts or solo close-ups. Preliminary pass only; full 144-frame audit remains mandatory.
- **S27:** all 144 frames drift through judge, prosecutor, and foreground character inserts/overlays rather than keeping the acquittal moment legible. Rejected for layered inserts and continuity. A single wide courtroom master reference `P27` and no-cut prompt are pinned; it is queued with S28–S29 in workflow `42290702425`.
- **S28:** all 144 frames show an initial black interval, a bundle beside a barrel that can read as a body-like form, and unrelated hard transitions among clothing and writing materials. Rejected on continuity/readability and non-graphic safety grounds. A clean, human-free evidence-table reference `P28` is pinned; the retake prompt requests one readable, continuous tabletop shot without bodies, marks, black frames, or cuts. It is queued with S27/S29 in workflow `42290702425`.
- **S29:** all 144 frames use a conspicuous split-screen/paired-portrait composition instead of one shared garden scene. Rejected. An approved single-frame sibling-garden reference `P29` and a stable wide two-shot prompt are pinned; it is queued with S27–S28 in workflow `42290702425`.

## Required constraints

- S03 remains an empty-street fire establishing view: no fire engine, emergency lights, firefighters, hose, crowd, or bucket line.
- S04 continues at that house and night, with one period-appropriate fire engine arriving after S03 and exactly three clearly distinct firefighters in period uniforms deploying a hose. No villagers or repeated cast from S03.
- S20 remains one continuous outdoor station-square shot of Shuko handing small paper leaflets and bowing. No cutaway, home, clothesline, laundry, or paper-to-fabric transformation.
- All 30 final shots require dense frame-level motion/continuity review before the revised MP4 is called final.

## Additional first-pass findings

- **S07, S21, S24, S25, S26, and S30:** all 144 frames reviewed. No clear major continuity, anatomy, text, or non-graphic presentation issue found; retain provisionally pending final consolidated QA.
- **S22, S23, S27, S28, and S29:** rejected for the specific continuity/composition defects recorded above and require retakes.

## Frame audit

The all-frame audit workflow produced four time-labelled sheets per shot (144 frames at 24 fps). Human review of all original-shot sheets is now complete; existing automated checks report no black frames or large changes except the issues described above (S23/S28 transitions and S28 opening black interval). New retakes for S04, S12, S20, S23, S22, and S27–S29 must be regenerated and audited again across all 144 frames. Nine-frame sheets remain preliminary only; no revised retake is finally accepted yet.

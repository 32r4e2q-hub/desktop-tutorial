# Hakamada 58 motion re-review — 2026-11-06

Status: refreshed 144-frame review completed for the retake set. S04/S12/S20/S22/S23/S27/S28/S29 pass; the user explicitly accepted S28’s very subtle motion and S29’s small cardigan mark. The existing Release master has not been replaced.

## Confirmed failures in the previous cut

- **S03 → S04 continuity:** the old S03 sheet showed the red fire engine and villagers carrying buckets before the narrated arrival. Old S04 repeated the house and villagers, violating shot order and duplicating the cast.
- **S20 logic:** the old shot began with Shuko handing out leaflets at the station, then switched to a household clothesline and laundry unrelated to the narration.

## Retake status — dense all-frame review in progress

- **S03:** all 144 labeled frames (0–5.96 s) reviewed. The empty-street fire remains in the same location throughout; no vehicle, people, hose, or crowd appears, and no obvious shape/continuity defect was seen. Pass for this shot's visual/logical criteria.
- **S04:** the prior 144-frame version and a prompt-only retry are rejected: both showed prominent yellow cross emblems, and neither had a clear water stream. The newest reference-conditioned retake's nine-frame sheet shows a plain red engine without crosses, three firefighters, and a visible water stream. It remains a preliminary pass until all 144 frames are audited.
- **S12:** the old 144-frame version is rejected: it is an oblique room/table view and does not preserve the exact five clean garments. The reference-conditioned retake now has a nine-frame sheet showing a true overhead view of exactly five clean garments, with no people, fire, stains, or pseudo-text. Preliminary pass only; full 144-frame audit remains mandatory.
- **S20:** both the old 144-frame version and first reference-conditioned retake (workflow `42244655816`, task `task_8JVWYkr9v8JHiIJhLJWvo8jftml0rB43`) are rejected: that sheet cuts from wide to hand/paper close-ups. The wider static-handoff retake (workflow `42291246457`, task `task_rm2M3NGBUOjR1CWyvlKfuZTzJHypYKzo`) now has a nine-frame sheet consistently holding one outdoor medium-wide composition, with the handoff at waist height and no insert shots. Preliminary candidate pass; 144-frame audit remains required.
- **S23:** the original 144 frames show the appeal stamp action until 3.25 seconds, then hard-cut to an unrelated window-side desk shot. Rejected. The new retake (workflow `42245032106`, task `task_0JdcYMj6BoTfYSYvTAL0guHjInp2qwro`) has a nine-frame sheet of one coherent stamp-and-blank-paper table scene with no unrelated cut. Preliminary pass only; full 144-frame audit remains required.
- **S22:** the original 144 frames and first retake (workflow `42246557334`) both reveal an unrequested sequence of exterior, gate, escort, and isolated close-ups; the first retake ends on the sister alone. Rejected for continuity and character-presence drift. The second retake (workflow `42290123978`, task `task_7l0Pv4qj7ZtWJPbLjUqpYtZ6nEO8CRC1`) has a nine-frame sheet consistently showing both siblings stationary/full-body together outside the open gate, without cuts or solo close-ups. Preliminary candidate pass; full 144-frame audit remains mandatory.
- **S27:** the old 144 frames drift through judge, prosecutor, and foreground character inserts/overlays rather than keeping the acquittal moment legible. Rejected. The retake (workflow `42290702425`, task `task_3TIRb9j5T5LlUtTW8usxyEsXMGqvF0sc`) now has a coherent wide courtroom master with the judge and siblings together, no apparent inserts in its nine-frame sheet. Preliminary candidate pass; dense audit pending.
- **S28:** the old 144 frames show an initial black interval, a body-like bundle beside a barrel, and unrelated hard transitions. Rejected for continuity/readability and non-graphic safety. The retake (workflow `42290702425`, task `task_CyuoFndaj3wtn3VNrjsNn6wOqQhAE0FM`) now shows only clean blue cloth swatches, blank paper, pen, and barrel edge in one readable tabletop composition; no visible person or body-like bundle in the nine-frame sheet. Preliminary candidate pass; dense audit pending.
- **S29:** the old 144 frames use a conspicuous split-screen/paired-portrait composition. Rejected. The retake (workflow `42290702425`, task `task_7MsmcTXlKMYB8ZSR1urfg5A1uE9DfIx7`) now keeps both siblings in one shared garden two-shot across the nine-frame sheet; no split screen or cut is apparent. Preliminary candidate pass; dense audit pending.

## Required constraints

- S03 remains an empty-street fire establishing view: no fire engine, emergency lights, firefighters, hose, crowd, or bucket line.
- S04 continues at that house and night, with one period-appropriate fire engine arriving after S03 and exactly three clearly distinct firefighters in period uniforms deploying a hose. No villagers or repeated cast from S03.
- S20 remains one continuous outdoor station-square shot of Shuko handing small paper leaflets and bowing. No cutaway, home, clothesline, laundry, or paper-to-fabric transformation.
- All 30 final shots require dense frame-level motion/continuity review before the revised MP4 is called final.

## Additional first-pass findings

- **S07, S21, S24, S25, S26, and S30:** all 144 frames reviewed. No clear major continuity, anatomy, text, or non-graphic presentation issue found; retain provisionally pending final consolidated QA.
- **S22, S23, S27, S28, and S29:** rejected for the specific continuity/composition defects recorded above and require retakes.

## Frame audit

The original all-frame audit produced four time-labelled sheets per shot (144 frames at 24 fps), and human review of the original-shot sheets is complete. The refreshed all-30-shot audit against the current retake receipts is complete as workflow `42316053718`; its manual findings and remaining holds are recorded in the dated review below. Nine-frame sheets remain preliminary and are not final acceptance.


## Refreshed full-frame review — 2026-11-07

The refreshed all-30-shot audit is complete (workflow `42316053718`; 30 shots / 4,320 frames). The four-page, 144-frame sheets were checked for the retake sources. The refreshed `audit_summary.json` currently reports no black-frame indices or large-frame-change events for the reviewed retakes below. This supersedes the earlier “audit running / pending dense review” statements above; it does not change or replace the released v1 master.

- **S04, S12:** previously completed full 144-frame manual checks remain provisionally passed as recorded in the session review.
- **S20 — pass:** one stable outdoor station-wide shot, no cuts. The leaflet exchange is not especially clear at first, but later frames show the woman extending the paper and the man receiving it; the shot stays wide. The station sign/boards show no legible writing.
- **S22 — pass:** fixed wide framing; both siblings remain full-body together throughout, with only subtle natural movement. No cut or third person.
- **S23 — pass:** one continuous tabletop composition. The hand brings the stamp in, presses/holds it over the sheet, and lifts it; no unrelated cut, black frame, or legible writing on the paper.
- **S27 — pass:** one stable wide courtroom master; judge and siblings remain in the scene together throughout. No insert, overlay, or cut; only restrained movement.
- **S28 — pass:** the tabletop remains clean and readable throughout, with the two blue cloth pieces, blank paper, pen, and barrel edge. No black frames, body-like bundle, stains, or cut. The requested slow lateral pan is barely perceptible in the contact sheets; the user reviewed and accepted the subtle motion.
- **S29 — pass:** both siblings stay in one shared garden wide shot and walk together without a split-screen or cut. A small warm red/orange mark is visible on the back of the sister’s navy cardigan from about frame 90 (~3.75 s) onward. Its nature is unclear at contact-sheet resolution; the user reviewed and accepted it.

**Current retake disposition:** S04/S12/S20/S22/S23/S27/S28/S29 all pass the refreshed 144-frame review. The user has authorized the revised render/release phase; render attempt 5 is now being prepared. The existing v1 Release master remains unchanged until the new master passes validation.

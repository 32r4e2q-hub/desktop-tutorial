# Contact-sheet visual QC — 2026-11-11

Scope: human-reviewed 30 high-density contact sheets sampled at 4 fps from decoded source clips. This is substantially denser than the first 3×3 sheets, but still not full-motion sign-off; brief defects between samples and audio/sync issues can remain.

## Shot decisions

| Shot | Decision | Visual observations / disposition |
|---|---|---|
| S01–S08 | PASS at sampled-frame level | Scenes are broadly coherent and no definite anatomical distortion is visible. S05 replacement shows the circled insurance form, male lead, and woman in pink at the airport. Continue full-motion QC for faces/hands. |
| S09 | PASS WITH POST-EDIT | New source shows a closed bathroom door, narrow threshold light, and fade to dark; no open doorway. The render will use 5.5 seconds picture plus 0.5 seconds black for a deterministic cut-to-black. |
| S10–S21 | PASS at sampled-frame level, with S11 HOLD | Scenes are broadly coherent, and no clear face/hand deformation appears at 4-fps sampling. S11's group-to-empty-corridor dissolve should be checked in continuous playback; it may be intentional. S18/S19 hand close-ups need ordinary full-resolution confirmation. |
| S22 | REJECT (second attempt) | The first retry had distracting speckle-like particles. The second retry removed those, but it starts with the woman alone and dissolves to an unrelated blank blue studio background, dropping the male lead and izakaya. That is a clear continuity/content mismatch. | Regenerate as one uninterrupted two-shot: both people stay seated in the same izakaya for the entire clip; no dissolve, blank background, or scene change. |
| S23–S25 | PASS at sampled-frame level | Face close-up remains consistent in S23; S24's red-line/policy graphic resolves into an office meeting; S25 conversation is coherent. Full-resolution inspection still required. |
| S26 | HOLD | The defendant fades into the detention cell through a deliberate double-exposure. Samples do not establish whether this is the intended transition or a distracting ghosting artifact; verify full playback. |
| S27–S30 | PASS at sampled-frame level | Courtroom and exterior images are coherent. S29's adjuster/files/window match the story broadly, though cabinet-closing action needs playback. New S30 shows the green bottle in a dark room with a narrow light area and no full-frame whiteout. |

## Automated source technical QC

The media-enabled Actions run `43003857202` downloaded and decoded **30/30** source clips. Its committed `qa/qc-report.json` reports `TECHNICAL_PASS_VISUAL_REVIEW_PENDING`, scope `sources_only`, no hard failures, and no sampled near-white or freeze windows. S09's near-black samples are consistent with its intended dark ending. This check confirms decoding, receipt hashes/sizes, source dimensions, and sampled exposure/motion metrics; it cannot detect anatomy/scene errors by itself.

## Remaining gates

- **Hard reject:** S22 current source; replacement request is being prepared. Superseded S09/S30 source versions remain rejected in `results.json.previous_results` and must not be cut in.
- **Full-motion visual sign-off:** still pending for all 30 sources, especially S01 motion, S11 dissolve, S22 after regeneration, S26 ghosting, S29 cabinet action, and hand/face close-ups.
- No final film exists yet. Do not mark the project complete until replacement contact-sheet review, rendering, final-film QC, subtitle/audio checks, and full playback are complete.

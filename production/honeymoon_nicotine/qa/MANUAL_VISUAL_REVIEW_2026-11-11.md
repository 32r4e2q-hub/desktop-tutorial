# Contact-sheet visual QC — 2026-11-11

Scope: human-reviewed 30 high-density contact sheets sampled at 4 fps from decoded source clips. This is substantially denser than the first 3×3 sheets, but still not full-motion sign-off; brief defects between samples and audio/sync issues can remain.

## Shot decisions

| Shot | Decision | Visual observations / disposition |
|---|---|---|
| S01–S08 | PASS at sampled-frame level | Scenes are broadly coherent and no definite anatomical distortion is visible. S05 replacement shows the circled insurance form, male lead, and woman in pink at the airport. Continue full-motion QC for faces/hands. |
| S09 | PASS WITH POST-EDIT | New source shows a closed bathroom door, narrow threshold light, and fade to dark; no open doorway. The render will use 5.5 seconds picture plus 0.5 seconds black for a deterministic cut-to-black. |
| S10–S21 | PASS at sampled-frame level | Scenes are broadly coherent, and no clear face/hand deformation appears at 4-fps sampling. S11's group-to-empty-corridor transition resolves into the Korean insurance office as storyboarded; sampled transition is coherent, though continuous playback remains required. S18/S19 hand close-ups need ordinary full-resolution confirmation. |
| S22 | PASS WITH CAVEAT at sampled-frame level | Latest retry is an uninterrupted izakaya two-shot with both characters visible and stable throughout; the earlier blank-background dissolve is gone. Bright points remain in the window/background and read as urban lamp reflections/bokeh rather than facial/hand distortion, though they are busier than ideal. Keep provisionally; full playback must confirm no particle flicker. |
| S23–S25 | PASS at sampled-frame level | Face close-up remains consistent in S23; S24's red-line/policy graphic resolves into an office meeting; S25 conversation is coherent. Full-resolution inspection still required. |
| S26 | PASS at sampled-frame level (replacement) | Latest replacement shows one fully present seated man from the opening through the end, with a steady push-in and no apparition, ghosting, or anatomy discontinuity visible at 4-fps sampling. Provisionally retain; continuous playback and face/hand inspection remain pending. |
| S27–S30 | PASS at sampled-frame level | Courtroom and exterior images are coherent. S29's adjuster/files/window match the story broadly, though cabinet-closing action needs playback. New S30 shows the green bottle in a dark room with a narrow light area and no full-frame whiteout. |

## Automated source technical QC

The media-enabled Actions run `43011217402` decoded and checked **30/30** sources plus the rendered 180-second first cut. `qa/qc-report.json` reports `TECHNICAL_PASS_VISUAL_REVIEW_PENDING`, scope `sources_and_final`, no hard failures, 1920×1080 at 24 fps, exactly 4,320 frames, H.264/AAC, 48 kHz audio; every source is checksum/size-verified and 4-fps sampled. S09's near-black samples are intentional. Narration fit passed all 30 shots (maximum required speed 1.384×, below the 1.55× cap). This is technical and sampled-frame QC, not full-motion visual/audio synchronization sign-off.

## Remaining gates

- **Superseded rejects:** old S09/S30 whiteout/open-door versions and earlier S22 particle/scene-change versions remain rejected in `results.json.previous_results` and must not be cut in. Current S22 is provisionally acceptable only from sampled frames.
- **Full-motion visual sign-off:** still pending for all 30 sources, especially S01 motion, S11 dissolve timing, S22 and S26 replacements, S29 cabinet action, and hand/face close-ups.
- **First cut exists:** `Honeymoon_Nicotine_Final.mp4` is in the Actions artifact for run `43011217402` (artifact `honeymoon-nicotine-agnes-20`); small deliverables and checksums are in `交付/` and `results.json`. It is not approved as a final master yet.
- **Remaining approval:** full-length playback of the first cut, including subtitle readability/timing, narration intelligibility and A/V synchronization, plus continuous review of all 30 shots (particularly S01 motion, S11 dissolve timing, S22 background highlights, S26 face/hands, and S29 cabinet action). Do not describe technical/sample QC as complete visual sign-off.

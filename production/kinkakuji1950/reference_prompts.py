#!/usr/bin/env python3
"""Compose the reference-image prompts for 《金阁寺纵火案》 strictly by the global rule.

Rule 1: every picture prompt starts with the 【STYLE】 block; when a character appears, that
character's 【角色设定】 block is spliced in verbatim; every prompt ends with 【NEGATIVE】.
The exact strings printed here are the strings handed to the image generator, and they are
written to ``reference/prompts.md`` so the定稿参考图 stay reproducible.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_story_module():
    spec = importlib.util.spec_from_file_location("kinkakuji1950_build_story", HERE / "build_story.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


REFERENCES = [
    {
        "file": "reference/01-kinkaku-spring.png",
        "characters": [],
        "scene": "Kinkaku-ji in late spring, the establishing reference for the whole film. The "
                 "three-storey golden pavilion stands at the right third at the edge of the mirror "
                 "pond, its reflection unbroken on the left two thirds of the water; black pines, "
                 "moss, a stone lantern and a raked gravel path frame it, full sakura in bloom "
                 "behind, petals drifting onto the surface. Dawn mist, warm gold against deep "
                 "indigo, morning light travelling across the gold leaf. One still reference frame, "
                 "not a moving shot.",
    },
    {
        "file": "reference/02-kinkaku-winter.png",
        "characters": [],
        "scene": "The same pavilion in deep winter: snow lying thick on the cypress-bark roofs and "
                 "on the pine branches, snowflakes settling on the golden eaves, the pond rimmed "
                 "with thin ice and holding a pale reflection, cold blue-white light with the gold "
                 "glowing warm inside it. Same building proportions, same pond and stone lantern "
                 "positions as the spring reference so the two can be cut together.",
    },
    {
        "file": "reference/03-ryozen-novice.png",
        "characters": ["ryozen"],
        "scene": "Character reference sheet, three-quarter view: the 21-year-old novice monk stands "
                 "on the stone path of the temple in the early morning, head slightly lowered, hands "
                 "folded in front of him, a broom leaning against the wall, mist and the golden "
                 "pavilion soft in the background. Neutral, quiet, guarded. Full upper body in "
                 "frame, sharp detail on face, robe and shaved head.",
    },
    {
        "file": "reference/04-young-ryozen.png",
        "characters": ["boy"],
        "scene": "Character reference: the boy stands at the wooden gate of a small seaside temple "
                 "in Maizuru, a cloth bundle over one shoulder, looking out toward the grey Japan "
                 "Sea beyond the fishing-town roofs, prayer banners moving in the wind. Same face "
                 "shape as the adult monk so the two ages match.",
    },
    {
        "file": "reference/05-mother.png",
        "characters": ["mother"],
        "scene": "Character reference: the mother stands on a rural railway platform in summer, "
                 "seen three-quarter from behind so her face stays indistinct, a small cloth bundle "
                 "held in both hands, wind lifting the loose hair at her temple and the hem of her "
                 "dark kimono, wooden shelter and hills behind. Quiet, restrained, dignified.",
    },
    {
        "file": "reference/06-maizuru-temple.png",
        "characters": [],
        "scene": "Location reference: a modest wooden temple in a small fishing town on the Japan "
                 "Sea coast in the 1940s - weathered gate, tiled roof, prayer banners, raked gravel, "
                 "a low stone wall, fishing boats and grey water beyond the roofs, overcast sea "
                 "light, wind moving everything. No people.",
    },
    {
        "file": "reference/07-interior-buddha.png",
        "characters": [],
        "scene": "Interior reference of the golden pavilion's altar room at night: a small gilded "
                 "Buddha statue on a dark lacquered altar, one candle flame breathing and lighting "
                 "the gold flake of the wall panels, and the wooden statue of Ashikaga Yoshimitsu "
                 "showing only a faint golden outline in the dark behind. Sacred, still, dim; dust "
                 "motes in the candle light. No people.",
    },
    {
        "file": "reference/08-fire-night.png",
        "characters": [],
        "scene": "The film's visual climax reference: the golden pavilion at three in the morning "
                 "with fire breaking from an upper window and running along the balcony, the gold "
                 "eaves swallowed by churning orange light, a dense column of sparks rising like a "
                 "river of stars flowing backwards into the night sky, and the mirror pond below "
                 "holding the burning reflection, ash falling onto the water. No people, no bodies.",
    },
]


def main() -> None:
    story_module = load_story_module()
    story = story_module.build()
    rows = []
    for ref in REFERENCES:
        parts = [story["style_prefix"].strip()]
        for role in ref["characters"]:
            parts.append(story["characters"][role].strip())
        parts.append(ref["scene"].strip())
        parts.append(story["negative_prompt"].strip())
        rows.append({"file": ref["file"], "characters": ref["characters"],
                     "prompt": "\n\n".join(parts)})
    out = HERE / "reference" / "prompts.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = ["# 定稿参考图提示词（自动拼接 STYLE / 角色设定 / NEGATIVE）", ""]
    for row in rows:
        md += [f"## `{row['file']}`", "", f"角色：{row['characters'] or '无'}", "", "```",
               row["prompt"], "```", ""]
    (HERE / "reference" / "prompts.md").write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} prompts)")
    for row in rows:
        print(f"--- {row['file']} [{len(row['prompt'])} chars]")


if __name__ == "__main__":
    main()

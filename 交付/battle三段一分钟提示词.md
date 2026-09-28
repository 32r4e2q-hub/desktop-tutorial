# Battle 模式三段式：3 × 60 秒 → 拼成 3 分钟（蒙娜丽莎：行李箱里的 779 号）

切点正好落在成片章节边界上（`story.json` 里六章都是 30 秒）：
Part 1 = N01+N02（黄金开头 + 给名画装玻璃的人）｜Part 2 = N03+N04（一晚上加十五分钟 + 对不上的指纹）｜Part 3 = N05+N06（一封信与背面编号 + 档案里没有那根纤维）。
所以三段拼起来不需要重新对时：60 + 60 + 60 = 180 秒。

用法：
1. 三段提示词各自独立，可以并行提交；**STYLE 段和 AVOID 段必须逐字照抄同一段**，三段画风才不会跑偏。
2. 每段是 8 个镜头 × 7.5 秒 = 60 秒。如果你的 battle 模式一次只能出 8~10 秒，就把每个 SHOT 单独发一次，STYLE / AVOID 每次照抄。
3. 三段之间用 `HOLD END` 那帧去接（我把它标出来了），拼接时不要加转场，硬切才对得上节奏。
4. 一律要求"画面里不许有可读文字"，标题/数字/编号后期贴字（本片的 7 张信息卡在 16/40/64/96/128/148/172 秒）。
5. 配音单独录，别丢给模型：解说密度是 5.4 字/秒（964 字 ÷ 179 秒），每段口播约 320 字 = 正好 60 秒。
6. 若模型会自己加音乐，注明 ambient only / no music / no voiceover，否则三段声音接不起来。

---

## PART 1 / 3 — 0:00–1:00 「four pegs on an empty wall」

```
60 second 2D animated true-crime documentary sequence, horizontal 16:9, 1920x1080, 30fps, 8 shots of 7.5 seconds each, cut in order, no on-screen text, no voiceover.

STYLE (identical for all three parts): Stylized 2D animated documentary illustration, hand-painted graphic-novel textures, soft cel shading, ink linework with light paper grain. Belle Epoque Europe, 1908 to 1914: the Louvre's Salon Carre with gilded walls hung floor to ceiling with old-master paintings, service stairways of worn stone steps with black iron balustrades, a glazier's workshop with lead came and putty, cobblestone quays in river mist, gas lamps, horse carts, a police records room. Muted palette of slate blue, wet limestone grey, varnished umber and gaslight amber; overcast August morning daylight or warm gaslit interior; restrained procedural mood, no horror excess. Every human is shown only from behind, in silhouette, or as hands and props - never a clear frontal face. The stolen portrait is never shown face-on: only its blank wooden back, its empty gilt frame, or the bare wall behind it. One single continuous slow camera move per shot.

SHOT 1 (0-7.5s): The Salon Carre at dawn, empty, framed from the first frame on a bare stretch of ochre gallery wall between two huge gilt frames: four small iron pegs and a pale rectangular ghost-mark where a picture hung, herringbone parquet, dust drifting in a slanted shaft of light. Camera: one extremely slow push-in toward the four pegs.
SHOT 2 (7.5-15s): A quayside service entrance on a grey early morning, framed on wet cobblestones and a plain wooden door in tall pale limestone: four workmen seen only from behind in long white smocks and flat caps, tool bags, a horse cart in mist. Camera: slow lateral tracking alongside them.
SHOT 3 (15-22.5s): The empty gallery down its long axis: one workman in a white smock walks away from camera across the parquet between walls stacked with gilt frames, small in the frame, the light shafts moving with him. Camera: steady follow from behind.
SHOT 4 (22.5-30s): Distant locked-off frame down the length of the huge empty gallery, four pegs and the ghost-mark on the far wall: the workman reaches up with both hands, tilts a panel loose, turns it so only its blank wooden back faces camera, and carries it out of shot. Camera: static.
SHOT 5 (30-37.5s): HOLD END on the bare wall with the four pegs and the ghost-mark, light shaft slowly sliding off it, no people. Camera: static, single held composition.
SHOT 6 (37.5-45s): A glazier's workshop, gaslit: hands cutting glass into a gilt frame with lead came and putty, a half-covered old-master canvas face-down on trestles, offcuts and a chalk line. Camera: slow slide left across the bench.
SHOT 7 (45-52.5s): 1908, the Salon Carre again: two workmen on low scaffolding seen from behind fitting a heavy protective glass cover over a large framed painting, gilded frame, assistants holding candles, no face visible. Camera: slow rise.
SHOT 8 (52.5-60s): A police records room at night: wooden filing drawers open, a hand riffles through index cards, one card shows a blurred thumb print impression under a lamp; a ledger lies closed. Camera: slow push-in onto the card tray. HOLD END on the closed tray.

HARD RULES: no readable text, letters or numbers anywhere; no Mona Lisa face; no frontal faces; no cuts inside a shot; no costume or prop change inside a shot; faces of crowd never visible; the painting surface never visible.
```

口播（自己配音，别贴给模型）：N01 一九一一年八月二十一日…今天一口气讲清楚。 + N02 先说他是谁…指纹早就在警局档案里。（309 字）

---

## PART 2 / 3 — 1:00–2:00 「hide overnight, walk out, and one print that matched nobody」

```
60 second 2D animated true-crime documentary sequence, horizontal 16:9, 1920x1080, 30fps, 8 shots of 7.5 seconds each, cut in order, no on-screen text, no voiceover.

STYLE (identical for all three parts): Stylized 2D animated documentary illustration, hand-painted graphic-novel textures, soft cel shading, ink linework with light paper grain. Belle Epoque Europe, 1908 to 1914: the Louvre's Salon Carre with gilded walls hung floor to ceiling with old-master paintings, service stairways of worn stone steps with black iron balustrades, a glazier's workshop with lead came and putty, cobblestone quays in river mist, gas lamps, horse carts, a police records room. Muted palette of slate blue, wet limestone grey, varnished umber and gaslight amber; overcast August morning daylight or warm gaslit interior; restrained procedural mood, no horror excess. Every human is shown only from behind, in silhouette, or as hands and props - never a clear frontal face. The stolen portrait is never shown face-on: only its blank wooden back, its empty gilt frame, or the bare wall behind it. One single continuous slow camera move per shot.

SHOT 1 (0-7.5s): Sunday evening at a museum service corridor, dusk: a line of workmen in white smocks filing out toward a lit doorway, one of them stepping sideways out of the row into shadow between stacked picture frames. Camera: slow dolly toward the shadow.
SHOT 2 (7.5-15s): Night, a storeroom beside the gallery: narrow space between oversized frames and packing crates, a seated human shape in a white smock barely visible, moonlight in slats across the floor, dust. Camera: static, held.
SHOT 3 (15-22.5s): Monday early morning in a stone stairwell: close on hands buttoning a white smock up to the throat, tucking a cap low, then the figure walking down worn steps away from camera. Camera: steady follow from behind.
SHOT 4 (22.5-30s): An empty gallery at 7:15: the workman takes the panel from its four iron pegs and lifts it clear, only his back and arms visible, gilded frames on either wall. Camera: slow push-in past his shoulder.
SHOT 5 (30-37.5s): A service stairwell corner: a discarded heavy glass case and an empty gilt frame leaning against the wall, putty scraps on the step; in the background a short figure in a white smock passes with a bundled cloth under his arm. Camera: static, deep frame.
SHOT 6 (37.5-45s): A museum doorway onto the quay: another workman holds the plain wooden door open while the bundled figure steps out into mist; a plumber's toolbox at the threshold. Camera: slow pull-back through the doorway.
SHOT 7 (45-52.5s): Next morning: an artist's easel being set up in the gallery; the copyist's hand stops mid-adjustment; beyond him, the bare ochre wall with four pegs and a ghost-mark. Camera: slow rack from the easel to the wall, then push in.
SHOT 8 (52.5-60s): A police records room, hundreds of index cards spread across long tables under hanging lamps: two examiners seen from behind compare a thumb-print card against a ledger, one lifts a magnifier. Camera: slow overhead drift across the tables. HOLD END on the magnifier resting on an unmatched card.

HARD RULES: no readable text, letters or numbers anywhere; no Mona Lisa face; no frontal faces; no cuts inside a shot; no costume or prop change inside a shot; no weapons, no violence; the panel is only ever seen blank-backed or as a bundled cloth.
```

口播：N03 他的计划简单到让人无语…顺手替他开了门。 + N04 第二天…写完报告。（319 字）

---

## PART 3 / 3 — 2:00–3:00 「a letter, a false bottom, and the number on the back」

```
60 second 2D animated true-crime documentary sequence, horizontal 16:9, 1920x1080, 30fps, 8 shots of 7.5 seconds each, cut in order, no on-screen text, no voiceover.

STYLE (identical for all three parts): Stylized 2D animated documentary illustration, hand-painted graphic-novel textures, soft cel shading, ink linework with light paper grain. Belle Epoque Europe, 1908 to 1914: the Louvre's Salon Carre with gilded walls hung floor to ceiling with old-master paintings, service stairways of worn stone steps with black iron balustrades, a glazier's workshop with lead came and putty, cobblestone quays in river mist, gas lamps, horse carts, a police records room, a Paris rented room, a Florentine hotel corridor. Muted palette of slate blue, wet limestone grey, varnished umber and gaslight amber; overcast morning daylight or warm gaslit interior; restrained procedural mood, no horror excess. Every human shown only from behind, in silhouette, or as hands and props - never a clear frontal face. The portrait is never shown face-on: only its blank wooden back, its empty frame, or the bare wall. One single continuous slow camera move per shot.

SHOT 1 (0-7.5s): A dim Paris rented room, two years later: a plain wooden travel trunk under a window, a hand slides a panel of the lid, a false bottom lifts an inch and pale wood shows underneath; a chair, a washstand, no people's faces. Camera: slow push-in on the trunk seam.
SHOT 2 (7.5-15s): Florence, November 1913, an antique dealer's office: an unaddressed envelope slides across a desk into lamplight, a hand stops it; ledgers, a wax seal pot, a picture rail behind. Camera: slow lateral track with the envelope.
SHOT 3 (15-22.5s): A hotel corridor at night: two men in overcoats and hats walk away from camera toward a room door, gas lamps receding, patterned carpet, a chambermaid's tray left outside. Camera: steady follow from behind.
SHOT 4 (22.5-30s): Inside the hotel room: hands lift a blank wooden panel out of the trunk and turn it toward the tall window; grey daylight rakes across its bare reverse; a small faded museum label sits on the wood, deliberately out of focus and unreadable. Camera: extreme slow push-in toward the label.
SHOT 5 (30-37.5s): Same room, held: the panel propped against the chair, the open trunk with its false bottom raised, a second shadow in the doorway; no face, no painted surface visible. Camera: static, then a very slow 10 percent pull-back.
SHOT 6 (37.5-45s): A museum archive room, daylight: a magnifying glass rests on a glass slide holding a few wood fibres; a hand closes the drawer over it, and the drawer is otherwise empty; a card catalogue behind. Camera: slow pull-back out of the drawer.
SHOT 7 (45-52.5s): January 1914, the Louvre at night: four men in caps carry a crated panel on padded stretchers through a lamp-lit corridor, seen from behind, gilded walls blurring past. Camera: lateral tracking with the stretcher.
SHOT 8 (52.5-60s): The Salon Carre, daytime: a dense crowd of visitors photographed from behind, hats and coats, all facing the wall where a picture now hangs in a heavy frame seen only from an oblique angle and never face-on; then the camera pulls back through the doorway until the crowd and the wall grow small. HOLD END on the doorway.

HARD RULES: no readable text, letters or numbers anywhere (the inventory label must stay blurred and cropped); no Mona Lisa face; no frontal faces; no courtroom violence; no cuts or prop changes inside a shot; the panel is only ever its blank wooden back.
```

口播：N05 画就在巴黎一间出租屋里…七百七十九。 + N06 网上还流传着一个更戏剧化的版本…还是卢浮宫太自信？（336 字）

---

## 后期必须自己补的 7 张卡（模型的假文字一律不能用）

| 成片时间 | 卡 | 内容要点 |
|---|---|---|
| 0:16 | S05 案件名片 | 1911-08-21 · 卢浮宫 · 失窃 2 年 |
| 0:40 | S11 人物档案 | Vincenzo Peruggia，1881 年生，160 cm，油漆工/镶玻璃工 |
| 1:04 | S17 作案时间线 | 周日入场 → 储物间过夜 → 周一 7:15 摘画 → 8:30 前出门 |
| 1:36 | S25 勘查与失手 | 左手拇指印 vs 只采右手的档案；256 名馆员无匹配 |
| 2:08 | S33 一封信 | 1913-11-29，署名「列奥纳多·V」，五十万里拉 |
| 2:28 | S38 流传与档案 | 白杨木纤维＝**流传版本，档案无此记录** |
| 2:52 | S44 判决与归还 | 1914-01-04 回卢浮宫；判 1 年 15 天，实刑 7 个月 |

拼接（本地或 Colab 都行，`list.txt` 按 1/2/3 顺序写文件路径）：

```bash
ffmpeg -f concat -safe 0 -i list.txt -c copy 蒙娜丽莎_battle三段.mp4
```

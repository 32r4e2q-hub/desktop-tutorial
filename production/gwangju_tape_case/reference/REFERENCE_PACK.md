# 光州胶带案参考图包

所有图都是生成式参考资产，不是真实案发照片或真实人物肖像。C 图用于人物外观锚定；S 图用于环境；P 图用于道具。最终 Agnes 视频提示词仍由 `generate.py` 自动拼接 STYLE、逐字角色锚点、镜头描述和 NEGATIVE。

**生成顺序：** C → S → P。每张图片单独生成、逐张读回目视检查；不符合设计或有伪字/多余肢体/不当内容时，针对同一编号重生成。仅经过检查并登记 SHA-256 的定稿可改为 `approved`。当前 C 图已通过视觉检查；S01–S13、P01–P07 均已生成、逐张检查并登记哈希。P07 首张因类条码标记被拒绝，按修订提示重生成后通过。

## C｜角色参考（10 张）

| 编号 | 角色锚点 | 参考图检查摘要 | 文件 / 状态 |
|---|---|---|---|
| C01 | 22 岁女大学生善雅（化名），马尾、浅色针织衫、背包与便当 | 生成式东亚年轻女性肖像，画面带背包与饭盒；作为角色设计，不是受害者真实影像。 | `C01.png` · approved |
| C02 | 50 岁出头母亲，运动外套、网球拍包 | 成熟东亚女性，深蓝运动服与网球包。 | `C02.png` · approved |
| C02B | 同一母亲的年长版本，白发、素色上衣 | 白发年长东亚女性，平静而疲惫；对应多年后的象征性角色。 | `C02B.png` · approved |
| C03 | 50 多岁父亲，西装、领带、公文包 | 成熟东亚男性西装形象。 | `C03.png` · approved |
| C04 | 40 多岁刑警，深色夹克、疲惫锐利 | 成熟东亚男性侦查员形象。 | `C04.png` · approved |
| C05 | 23 岁前男友，连帽衫 | 年轻东亚男性中性肖像；不暗示有罪。 | `C05.png` · approved |
| C06 | 熟悉门锁的男性重点对象，深色夹克 | 成熟东亚男性中性肖像；不暗示有罪。 | `C06.png` · approved |
| C07 | 40 岁专家，眼镜、衬衫 | 东亚男性专家形象，原图手持胶带卷；叙事中仅作为虚构专家角色参考。 | `C07.png` · approved |
| C08 | 2024 年调查组与 DNA 研究员 | 同一张横构图中有男性刑警与白大褂研究员。 | `C08.png` · approved |
| C09 | 凶手黑影 | 全身深色剪影，面部完全隐藏；只在远景或手部镜头使用。 | `C09.png` · approved |

## S｜场景参考（13 张）

统一要求：单张 16:9 横图、写实 3D 环境概念图、2004 年韩国光州普通公寓/办公室物件（现代场景例外）、无人物、无可读文字/标识/水印、无人身伤害与遗体。S 图不代替视频，Agnes 镜头仍必须有真实连续运动。

| 编号 | 环境设计 | 单图生成提示词 | 状态 |
|---|---|---|---|
| S01 | 2004 年光州北区普通公寓外观 | A single standalone 16:9 landscape environment reference image for a restrained photorealistic 3D animated Korean crime documentary reconstruction. Exterior of an ordinary modest apartment block in Buk-gu, Gwangju, South Korea, circa 2004, low-rise concrete building, simple entrance, narrow quiet street, early September dusk and warm-to-cool street lighting, realistic 2000s Korean details, no readable signs or text, no people, no police, no violence, no blood, no body, cinematic 35mm composition, no collage, no border, no watermark. | approved · 2026-11-14 visual review |
| S02 | 普通家庭客厅、厨房与玄关 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Interior of a modest 2004 South Korean family apartment living room opening to a small kitchen and entryway: simple sofa, shoe cabinet, beige walls, modest furniture, a school backpack and plain lunchbox near the entry, faint warm morning window light, ordinary lived-in household, no people, no readable text or logos, no crime scene, no violence, no blood, no body, cinematic 35mm, no collage, no watermark. | approved · 2026-11-14 visual review |
| S03 | 没有监控的旧式公寓楼道 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Empty corner of a 2004 South Korean apartment stairwell and public corridor, ordinary bare concrete wall with absolutely no CCTV camera, no mounting bracket and no installation marks, stairs receding softly into focus, cool morning daylight, no people, no readable text or logos, no violence, no blood, no body, cinematic realism, no collage, no watermark. | approved · 2026-11-14 visual review |
| S04 | 关闭的小房间门与门缝光 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Narrow corridor inside an ordinary 2004 South Korean apartment, viewed toward a closed small bedroom door at the far end, thin line of warm light under the door, muted blue-gray evening light, worn floor and modest walls, no people, absolutely no view into the room, no readable text, no violence, no blood, no body, restrained cinematic suspense, no collage, no watermark. | approved · 2026-11-14 visual review |
| S05 | 2004 年警察署调查室 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Generic Gwangju police-station investigation office in 2004, period-correct desks, bulky CRT computer, paper case files, landline telephone, wall map without legible labels, cool fluorescent light, subdued and orderly, no identifiable badges, no readable text, no people, no case names, no violence, cinematic 35mm environment concept, no collage, no watermark. | approved · 2026-11-14 visual review |
| S06 | 大学社团活动室 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. University student club room in Gwangju, circa 2004: worn tables and chairs, old desktop computer and analog wall clock, daylight through blinds, quiet neutral atmosphere, papers contain no readable text, no people, no logos, no violence, cinematic 35mm realistic 3D environment, no collage, no watermark. | approved · 2026-11-14 visual review |
| S07 | 早期 2000 年代公寓数字门锁 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Plain mechanical-digital apartment door keypad lock typical of early-2000s South Korea, mounted on a modest apartment door and wood trim, small green indicator light, shallow depth of field, no hands, no people, no readable digits or labels, no logos, no crime scene, cinematic macro realism, no collage, no watermark. | approved · 2026-11-14 visual review |
| S08 | 冷灰档案室 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Quiet archival records room in a Korean police station, long rows of metal file shelves and neutral cardboard binders, cool gray fluorescent ambience, one desk lamp illuminating an open file with blank pages, no labels or readable text, no people, no logos, no disturbing items, cinematic 35mm composition, no collage, no watermark. | approved · 2026-11-14 visual review |
| S09 | 证物保管室 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Secure evidence storage room in South Korea circa 2024, neat metal shelves with sealed transparent evidence containers, one small plain roll of yellow packing tape and a folded dark scarf visible in separate clear bags, cool white overhead light, no labels or readable text, no people, no bodily evidence, no violence, no blood, no body, sober forensic realism, no collage, no watermark. | approved · 2026-11-14 visual review |
| S10 | 2024 年 DNA 实验室 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Modern South Korean forensic DNA laboratory in 2024, sterile white bench, gloves, small sample tube, compact lab instrument and softly glowing monitor with abstract unlabeled shapes only, cool white lighting, no readable text, letters or numbers, no logos, no people, no crime scene imagery, no violence, cinematic 35mm documentary composition, no collage, no watermark. | approved · 2026-11-14 visual review |
| S11 | 2015 年韩国立法场景 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. A neutral Korean legislative chamber in 2015, empty desks, paper document and stamp in foreground, a wall clock, cool gray daylight, no actual elected officials, no readable Korean text or labels, no political party logos, no violence, cinematic 35mm documentary environment concept, no collage, no watermark. | approved · 2026-11-14 visual review |
| S12 | 多年后的母亲客厅 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Quiet modest South Korean apartment living room in the mid-2020s, warm dusk light, a plain sofa, small table with a cup of tea and a completely blurred family photograph, no people, no readable text, no logos, restrained respectful mood, cinematic 35mm, no collage, no watermark. | approved · 2026-11-14 visual review |
| S13 | 后来安装监控的公寓入口 | A single standalone 16:9 landscape photorealistic 3D animation environment reference. Exterior entry of an ordinary South Korean apartment building in the mid-2020s, a small installed CCTV camera above a quiet entrance, dusk reflections, empty corridor visible in lens glass, no people, no readable signs or text, no logos, no crime scene, cinematic 35mm, no collage, no watermark. | approved · 2026-11-14 visual review |

## P｜道具参考（7 张）

统一要求：单张 16:9 横图、深色或中性背景的写实 3D 静物特写、无可读文字/标签/水印、无血迹和身体部位。仅在证物镜头把胶带画为物理证物；其余片段的黄色胶带只作为象征性后期母题。

| 编号 | 道具设计 | 单图生成提示词 | 状态 |
|---|---|---|---|
| P01 | 黄色箱封胶带卷及被拉出的长条 | A single standalone 16:9 landscape photorealistic 3D still-life reference, one plain roll of yellow cardboard packing tape with a short strip unwinding into darkness, close macro detail, black neutral background, restrained Korean crime documentary mood, no hands, no body, no injury, no blood, no readable text, no logo, no watermark, no collage. | approved · 2026-11-14 visual review |
| P02 | 42 段胶带证物袋 | A single standalone 16:9 landscape photorealistic 3D still-life reference, an orderly array of clear sealed evidence bags each holding only a tiny yellow packing-tape fragment, on a cool white evidence table, labels completely blank with no text, no body, no blood, no violence, no logo, no collage, no watermark. | approved · 2026-11-14 visual review |
| P03 | 深色围巾证物 | A single standalone 16:9 landscape photorealistic 3D still-life reference, a folded dark scarf inside a clear unmarked evidence sleeve on a cool neutral surface, respectful forensic presentation, no person, no body, no injury, no blood, no text, no logo, no collage, no watermark. | approved · 2026-11-14 visual review |
| P04 | 深色大学生双肩包与素色便当盒 | A single standalone 16:9 landscape photorealistic 3D still-life reference, a simple dark student backpack and a plain light-colored lunchbox placed near each other on a modest apartment entryway floor, soft warm morning light, no person, no labels, no logos, no text, no violence, no blood, no body, restrained cinematic realism, no collage, no watermark. | approved · 2026-11-14 visual review |
| P05 | 2004 年按键式座机 | A single standalone 16:9 landscape photorealistic 3D still-life reference, an early-2000s South Korean beige push-button landline phone on a small apartment table, receiver slightly lifted, buttons present but no legible numerals or labels, cool dim evening light, no hands, no people, no text, no logos, no violence, no collage, no watermark. | approved · 2026-11-14 visual review |
| P06 | 早期 2000 年代数字门锁 | A single standalone 16:9 landscape photorealistic 3D still-life reference, an early-2000s South Korean apartment digital keypad lock with a small green indicator, mounted on a section of simple wooden door, key digits blurred and unreadable, no hands or people, no logos, no text, no violence, macro 35mm realism, no collage, no watermark. | approved · 2026-11-14 visual review |
| P07 | DNA 样本与抽象父系线索 | A single standalone 16:9 landscape photorealistic 3D still-life reference for a restrained forensic documentary. On a clean cool-white laboratory bench, one tiny clear forensic sample tube with a completely blank, unmarked surface: absolutely no sticker, barcode, label, writing or numbers. Beside it, a dark monitor displays only a simple abstract Y-shaped branching genetic tree with a few unlabeled nodes; no charts, grid, interface, text or letters. Clinical white lighting, sober and minimal, no people, no bodily material, no blood, no logos, no collage, no watermark. | approved · 2026-11-14 visual review |

## 固定 ID 与视频提示词限制

- 角色锚点原文见 `build_story.py` 的 `CHARACTERS`，生成时 `generate.py` 会逐字插入，不要手动改写成真实人物特征。
- 每个 Agnes 镜头引用 1–5 张经审批的参考图；每张图在 `approvals.json` 中必须有准确文件路径与 SHA-256。
- 参考图全部定稿并推送后，`revision.txt` 必须指向包含这些图的 40 位不可变 commit；当前值仍为 `PENDING`。

# 生图提示词模板

本模板用于正文和目录图。日期首图使用 `date-header.md` 的场景层提示词，不拼接本文件的装置、迷你工作人员或 3–5 个短词要求。

每张图单独生成。整篇文章共用固定视觉 DNA，每张图只替换内容块与构图块。`{…}` 为占位，色值和角色描述从 IP 档案读取。

## 固定视觉 DNA

```text
Generate one standalone 16:9 horizontal Chinese article illustration.

Use a perfectly clean solid pure white #FFFFFF background with no beige or cream cast, no visible paper grain, no vignette, floor, or cast shadow. Draw with warm dark-brown hand-drawn contours: slightly uneven pressure, occasional tiny gaps, and tapered ends. Use a clear color hierarchy: auxiliary light {辅助浅色} on large quiet panels, rails, tray interiors, and supports; main device color {装置主色} on primary structural faces and medium-sized surfaces; dark structural {结构深色} on handles, separators, selected edges, and deep-value details; near-white {近白} on page cards, label plates, and neutral device faces. Use {锚点色} as the anchor on key nodes, the default main directional path, selected states, and small heading accents; use it fully on character clothing and identity parts, and sparingly on device accents. At least three value/chroma levels must remain visibly distinct and read as clean, never grayish, dusty, or muddy. Never flood a full-width rail, large title block, or large panel with the anchor color. Preserve original colors of supplied product logos and genuine brand assets. Avoid clean vector outlines, hard pixel edges, glossy anime rendering, gradients, colored glow, and heavy shadows.

The recurring IP is a miniature work team. Use the exact target instance counts stated in the current content block. Never exceed the stated count, duplicate, clone, mirror, repeat, or add an unlisted character.

{对每个出场角色，粘贴档案中的英文“提示词描述”，并附该角色的禁止项}

Draw every human character at a target {头身比}-head proportion, excluding head ornaments. When several human characters appear, match their head pixel height and hair-top-to-shoe height within 10%. Each human character is about {人物/伙伴高度比} times the height of its partner. {逐个写出档案中的眼睛规格，例如 "Character A's eyes: ... no highlight dot, no reflection."} Their actions actively change the core device, oversized object, or scene structure.

The oversized core device, structure, or object is the first visual subject and the characters are secondary miniature workers. The primary scale test is relational: make every dominant functional module or container 1.4–2.2 full character-heights tall; secondary cards, levers, and controls are 0.8–1.5 character-head heights. Use canvas percentages only as a guardrail: in an ordinary illustration, each human character occupies 24%–32% of total canvas height excluding head ornaments; in a directory or low-wide-device illustration, 22%–32%; never above 35%. Show each character as a complete unobstructed full body, standing in front of or beside the device; never hide the waist, legs, or feet behind a workbench. For a tall-device composition, the core device occupies 70%–78% of canvas height and is at least 2.2 times a character's height. For a low-wide workbench, rail, or tool-belt composition, make the continuous device span 75%–85% of canvas width and at least five character-heights in width. Do not enlarge characters to fill empty space and do not reuse a reference image's layout.

Use 3–5 short Chinese hand-drawn labels. Red marks a key point and blue marks feedback. The main path uses the anchor color by default; use a small amount of orange only when the paragraph explicitly requires a second semantic contrast.
```

## 普通正文图内容块

```text
Theme:
{当前段落主题}

Core idea:
{读者需要理解的一个核心意思}

Physical metaphor:
{物理动作} + {1–2 个核心物件}

Character actions:
{每个出场角色一行：角色名 + 动作}

Chinese labels:
{标注1} / {标注2} / {标注3} / {标注4} / {可选标注5}

Target character instances:
{角色A exactly one / 伙伴A exactly one / 角色B none …}
Avoid: duplicate character, {每个角色的身份标志重复，例如 "second crown flower"}.

Eye state exceptions:
{none by default / 仅当 shot list 预先指定}
```

## 普通正文图构图块

```text
Composition specifications:
- Main silhouette: {横向 / 近方形 / 环形 / 左右对照}
- Complete subject-group width: {65%–78% of canvas}
- Subject-group horizontal center: {45%–55% of canvas}
- Device scale mode: {tall device / low-wide device}
- Character height guardrail: {24%–32% of canvas; or 22%–32% for a directory or low-wide device; never above 35%; full body unobstructed}
- Device dominance check: {70%–78% canvas height and at least 2.2 character-heights / 75%–85% canvas width and at least 5 character-heights wide}
- Oversized object anchor: {dominant module at 1.4–2.2 full character-heights; secondary control at 0.8–1.5 head heights}
- Reading direction: {静态聚焦 / 左到右 / 环形回流}
- White-space purpose: {环绕主体 / 主流向 / 对比 / 反馈}
```

## 目录图内容块

```text
Create a horizontal reading-directory illustration for a long Chinese article.

Build one low, wide, continuous device with 3–5 connected stages arranged from left to right. Use a horizontal workbench, sorting table, bookmark belt, rail, long desk, or horizontal drawers as the physical metaphor.

Article stages:
{阶段1} / {阶段2} / {阶段3} / {阶段4} / {可选阶段5}

Assign the characters to opening, delivering, pushing, sorting, or guiding the reading sequence: {按档案动作职责分配}.

Keep every character visibly miniature and fully unobstructed: each human character stays within the 22%–32% canvas-height guardrail and may not be enlarged to fill the white space above the low device.
```

## 目录图构图块

```text
Composition specifications:
- Core-device aspect ratio: at least 2:1
- Complete subject-group width: 75%–85% of canvas
- Continuous device width: at least five times one character's height
- Character height guardrail: 22%–32% of canvas, never above 35%, full body unobstructed
- Oversized object anchor: every stage's dominant module is at least 1.4 full character-heights
- Subject-group horizontal center: 48%–52% of canvas
- Stage order: left to right; one short Chinese label per stage
- Overall silhouette: low, continuous, and clearly horizontal
```

## 参考图说明

传入档案参考图时，在提示词中加入：

```text
Use the supplied character reference images only for recurring character identity, proportions, stroke quality, hand-drawn feel, and color calibration. Do not copy their sheet layout, poses, or background into the article illustration. The final background remains solid textureless pure white. The current article theme, physical metaphor, and composition specifications fully determine objects, layout, and narrative.
```

## 局部编辑模板

```text
Edit the provided image while preserving the approved theme, characters, hand-drawn style, colors, and aspect ratio.

Target adjustment:
{文字修正 / 主体居中 / 尺度调整 / 局部清理 / 身份规则修正}

Final composition:
{主体宽度、视觉中心、尺度模式、人物占画布高度、装置尺度指标、留白用途}
```

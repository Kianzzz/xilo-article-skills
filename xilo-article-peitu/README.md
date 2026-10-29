# xilo-article-peitu

给中文文章自动规划、生成、审校并插入配图的 Agent Skill（Codex / Claude Code 等支持 `SKILL.md` 的 Agent 均可用）：

- **日期首图 GIF**：3:1 横版，日期 + 一句话金句 + 你的 IP 角色轻浮动，可加自己的印章
- **正文配图**：16:9 纯白纸面手绘风，“小人 + 超大装置”的物理隐喻，3–5 个中文短标注
- **目录图**：长文自动加横向阅读地图
- 逐图角色计数 / 比例 / 构图 QA，通过后才插入 Markdown 或 Obsidian 文章

## 用你自己的 IP

Skill 不内置任何角色。第一次运行时它会请你提供：

1. 每个角色一张参考图（三视图最好，单张全身图也行），1–4 个角色
2. 每个角色一句话介绍（名字、人物还是伙伴、和谁搭档）
3. 可选：首图刊头文字、印章图片、色板、默认配图目录

Agent 会从参考图提炼出角色档案，给你确认后保存到 `~/.config/xilo-article-peitu/`（可用 `XILO_ARTICLE_PEITU_IP_DIR` 改位置）。之后每次配图都读取这份档案。没有现成 IP？可以让它先帮你设计一个。

## 依赖

- 一个能生成图片的工具（如 Codex 内置 `image_gen`）
- 首图合成：Python 3 + Pillow、FFmpeg、任意浏览器（用于加载字体排版）

## 安装

把 `xilo-article-peitu/` 复制到你的 Agent skills 目录，例如 `~/.codex/skills/` 或 `~/.claude/skills/`。

## 许可

代码与文档：MIT。`assets/fonts/WenKai.ttf` 为 [霞鹜文楷](https://github.com/lxgw/LxgwWenKai)，按 SIL Open Font License 1.1 随附（见 `WenKai-OFL.txt`）。

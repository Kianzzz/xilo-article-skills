# xilo-article-skills

两个给中文文章做图的 Agent Skill（支持 `SKILL.md` 的 Agent 均可用，如 Codex、Claude Code）。

| Skill | 做什么 |
|---|---|
| [xilo-article-peitu](xilo-article-peitu/) | 用**你自己的 IP 角色**生成日期首图 GIF 与纯白手绘风正文配图，逐图审校后插入文章。**需自行提供 IP 角色**，首次运行时引导你登记。 |
| [xilo-article-jietu](xilo-article-jietu/) | 按文章上下文批量美化真实截图：标注、马赛克、渐变背景、可选自定义水印，本地网页编辑后一键回填文章。 |

## 配图效果（演示 IP）

![日期首图](docs/images/peitu-header.gif)

![正文配图](docs/images/peitu-body-sorting.jpg)

> 配图需自行提供 IP 角色；上图使用的是演示用角色。

## 截图美化效果

![截图美化示例](docs/images/jietu-after.jpg)

## 安装

把需要的目录复制到 Agent 的 skills 目录，例如：

```bash
cp -r xilo-article-peitu xilo-article-jietu ~/.codex/skills/    # 或 ~/.claude/skills/
```

## 许可

MIT。`xilo-article-peitu/assets/fonts/WenKai.ttf`（霞鹜文楷）按 SIL OFL 1.1 随附。

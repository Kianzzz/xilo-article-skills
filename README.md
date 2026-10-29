# xilo-article-skills

两个给中文文章做图的 Agent Skill（支持 `SKILL.md` 的 Agent 均可用，如 Codex、Claude Code）。

| Skill | 做什么 |
|---|---|
| [xilo-article-peitu](xilo-article-peitu/) | 用**你自己的 IP 角色**生成日期首图 GIF 与纯白手绘风正文配图，逐图审校后插入文章。首次运行时引导你登记 IP。 |
| [xilo-article-jietu](xilo-article-jietu/) | 按文章上下文批量美化真实截图：标注、马赛克、渐变背景、可选自定义水印，本地网页编辑后一键回填文章。 |

## 安装

把需要的目录复制到 Agent 的 skills 目录，例如：

```bash
cp -r xilo-article-peitu xilo-article-jietu ~/.codex/skills/    # 或 ~/.claude/skills/
```

## 许可

MIT。`xilo-article-peitu/assets/fonts/WenKai.ttf`（霞鹜文楷）按 SIL OFL 1.1 随附。

# 方法与上游参考

本仓库将公开方法整理为适合中文仓库交接的原创技能、模板与辅助工具。下列链接用于说明设计来源；本包没有镜像完整上游技能，也不声称获得上游项目背书。

## 技能参考

| 来源 | 采用的方法 | 本包的具体取舍 |
| --- | --- | --- |
| [GitHub doc-and-modernize](https://github.com/github/awesome-copilot/blob/main/skills/doc-and-modernize/SKILL.md) | 本地代码调查、命令来源、架构证据 | 覆盖全部约定模块；仅文档任务，不自行启动代码改造 |
| [GitHub architecture-blueprint-generator](https://github.com/github/awesome-copilot/blob/main/skills/architecture-blueprint-generator/SKILL.md) | 根据真实依赖解释组件边界、数据变换和错误处理 | 沿一个输入同时检查生产者与消费者，把架构责任落实到可观察的结果 |
| [Anthropic doc-coauthoring](https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md) | 结构化正文、独立读者测试 | 只给新读者文档和未演示的场景；审查者另存有源码或运行依据的预期，核对读者的推理过程 |
| [Softaworks mermaid-diagrams](https://github.com/softaworks/agent-toolkit/blob/main/skills/mermaid-diagrams/SKILL.md) | 根据问题选择图种、保存文本图源 | 增加每模块流程要求与代码语义核对 |
| [Visual Explainer](https://github.com/nicobailon/visual-explainer) | 用局部图解说明机制与步骤 | 完整正文保留；独立图解迁入站点需组件适配 |
| [Anthropic webapp-testing](https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md) | 浏览器操作、截图和日志 | 页面测试与事实审查分别进行 |

## 文档方法

- [Diátaxis](https://diataxis.fr/)：按教程、任务指南、参考和解释区分读者需求。
- [arc42 模块视图](https://docs.arc42.org/section-5/)与[运行视图](https://docs.arc42.org/section-6/)：模块责任和具体运行场景。
- [C4 diagrams](https://c4model.com/diagrams) 与[标注约定](https://c4model.com/diagrams/notation)：按读者需要选择架构层级，标明组件职责、关系方向和交互目的。
- [Write the Docs — Docs as Code](https://www.writethedocs.org/guide/docs-as-code/)：文档版本、评审与自动检查。
- [Architecture Decision Records](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)：保留有依据的决策背景与后果。
- [Google 技术写作](https://developers.google.com/style/tone)：直接、自然、具体的表达。

## 工具与格式

- [Agent Skills](https://agentskills.io/)与[Vercel skills CLI](https://github.com/vercel-labs/skills)。
- [Starlight](https://starlight.astro.build/)、[组件](https://starlight.astro.build/components/using-components/)、[搜索](https://starlight.astro.build/guides/site-search/)、[集成目录](https://starlight.astro.build/resources/plugins/)。
- [Mermaid CLI](https://github.com/mermaid-js/mermaid-cli)与[可访问图形](https://mermaid.js.org/config/accessibility)。
- [GitHub 文件永久链接](https://docs.github.com/en/repositories/working-with-files/using-files/getting-permanent-links-to-files)。
- [Playwright 可访问性检查](https://playwright.dev/docs/accessibility-testing)：自动检查范围有限，仍需实际阅读操作。

业务词典中的证券示例另附 HKEX 和 Investor.gov 来源，仅用于演示市场语境差异，不代表使用此技能的仓库包含证券业务。

本包不使用安装量或 stars 作为质量保证。实施时核查所选工具的当前官方文档并固定版本；不要把本文作为任何软件版本永久有效的承诺。

## 公开技能库如何帮助读者上手

2026-11-15 对照了以下三个 GitHub 仓库的 README 和技能内容。表中链接固定到查阅版本；星数为 GitHub 页面显示的约数。

| 仓库与关注度 | README 与技能组织 | 示例如何展示 | 对 Docs Skills 的取舍 |
| --- | --- | --- | --- |
| Anthropic Skills，约 19.5 万星 | README 分开介绍技能实例、规范、模板和各平台用法；每个技能独立成目录。 | Web 应用测试技能在入口指向随包的元素发现、静态页面和控制台日志脚本。 | 可独立阅读的审查案例放进审查技能；跨技能的可运行项目保留在仓库级 `examples/`。[README](https://github.com/anthropics/skills/blob/1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064/README.md) · [Web 应用测试技能](https://github.com/anthropics/skills/blob/1780c5e5a552fd4d1c9d6a7b0cab26b0c2bef064/skills/webapp-testing/SKILL.md) |
| Vercel Agent Skills，约 3.4 万星 | 技能目录逐项写明适用任务，React 性能技能将细则拆到单独文件。 | 并发请求规则用同一组读操作并列演示顺序执行和并发执行。 | 首页用任务、提示词和产物导航；审查案例用同一组输入区分两种边界规则。[README](https://github.com/vercel-labs/agent-skills/blob/1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62/README.md) · [并发请求规则](https://github.com/vercel-labs/agent-skills/blob/1a2c79d4e6c4a2283dc2c614b6538cbe1ed5ca62/skills/react-best-practices/rules/async-parallel.md) |
| Superpowers，约 31.8 万星 | README 按开发阶段说明技能何时接手，安装说明按宿主拆分。 | 测试驱动开发技能沿同一个行为演示失败测试、最小实现和再次验证。 | 首页说明模块清单如何供绘图、词典、站点和审查使用；同一个导出案例贯穿文档与命令。[README](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/README.md) · [测试驱动开发技能](https://github.com/obra/superpowers/blob/22f0b463e7a5e579904dd6211a520321035526f7/skills/test-driven-development/SKILL.md) |

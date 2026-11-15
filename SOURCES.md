# 方法与上游参考

本仓库将公开方法整理为适合中文仓库交接的原创技能、模板与辅助工具。下列链接用于说明设计来源；本包没有镜像完整上游技能，也不声称获得上游项目背书。

## 技能参考

| 来源 | 采用的方法 | 本包的具体取舍 |
| --- | --- | --- |
| [GitHub doc-and-modernize](https://github.com/github/awesome-copilot/blob/main/skills/doc-and-modernize/SKILL.md) | 本地代码调查、命令来源、架构证据 | 覆盖全部约定模块；仅文档任务，不自行启动代码改造 |
| [Anthropic doc-coauthoring](https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md) | 结构化正文、独立读者测试 | 先读仓库，集中处理真实业务缺口 |
| [Softaworks mermaid-diagrams](https://github.com/softaworks/agent-toolkit/blob/main/skills/mermaid-diagrams/SKILL.md) | 根据问题选择图种、保存文本图源 | 增加每模块流程要求与代码语义核对 |
| [Visual Explainer](https://github.com/nicobailon/visual-explainer) | 用局部图解说明机制与步骤 | 完整正文保留；独立图解迁入站点需组件适配 |
| [Anthropic webapp-testing](https://github.com/anthropics/skills/blob/main/skills/webapp-testing/SKILL.md) | 浏览器操作、截图和日志 | 页面测试与事实审查分别进行 |

## 文档方法

- [Diátaxis](https://diataxis.fr/)：按教程、任务指南、参考和解释区分读者需求。
- [arc42 模块视图](https://docs.arc42.org/section-5/)与[运行视图](https://docs.arc42.org/section-6/)：模块责任和具体运行场景。
- [C4 diagrams](https://c4model.com/diagrams)：按需要选择架构层级。
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

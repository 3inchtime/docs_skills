# Docs Skills

让新同事看懂当前代码，并能继续开发的中文技术文档技能包。

工作流程：读取真实代码与配置 → 建立模块和证据清单 → 写清业务行为 → 为每模块画流程 → 构建可视化文档 → 独立审查 → 随 PR 维护。

## 五个技能

| 技能 | 工作 | 入口 |
| --- | --- | --- |
| `repo-docs` | 总控、仓库调查、完整模块正文、新人上手与开发指南 | [SKILL.md](skills/repo-docs/SKILL.md) |
| `repo-diagrams` | 真实模块流程、时序、状态和数据关系；Mermaid 构建 SVG | [SKILL.md](skills/repo-diagrams/SKILL.md) |
| `repo-docs-site` | 将已核验内容做成文档站，提供可复用流程说明组件 | [SKILL.md](skills/repo-docs-site/SKILL.md) |
| `business-glossary` | 业务专有名词、适用语境、本系统口径、例子和代码映射 | [SKILL.md](skills/business-glossary/SKILL.md) |
| `repo-docs-review` | 模块覆盖、事实审查、独立读者测试、变更影响与持续维护 | [SKILL.md](skills/repo-docs-review/SKILL.md) |

总控按阶段调用其他技能，避免一次加载所有指令。专用技能也可单独使用。内容为本仓库原创编排，参考的上游技能和方法见 [SOURCES.md](SOURCES.md)，不需要安装全部上游技能才能使用本包。

## 安装与使用

在支持 Agent Skills 的代码助手中安装。以本地 Codex 为例，当前 Vercel skills CLI 要求 Node.js 22.20+：

```bash
npx skills add 3inchtime/docs_skills -a codex
```

按安装器提示选择技能。保留安装生成的版本锁文件；私有仓库需要本机 Git 已具有对应读取权限。

然后在**需要编写文档的业务仓库**中发出任务：

```text
使用 $repo-docs，为当前仓库创建面向新同事接手和持续开发的中文技术文档。
以当前工作区为基线，优先复用现有文档站；没有时使用 Starlight + MDX。
覆盖全部业务模块，每模块提供具体 Mermaid 流程图，按需要补时序图和状态图。
解释真实条件、错误、状态与数据变化，提供具体修改位置和验证方法。
最后添加业务专有名词词典，普通技术名词不计入。
按技能完成调查、正文、可视化、独立审查和维护规则，不要只交大纲。
```

只更新一部分时直接指定范围，例如“使用 `$repo-diagrams` 核对并更新订单模块流程”或“使用 `$repo-docs-review` 检查本次变更影响的文档”。

## 明确而准确的写法

已确认行为直接说明主体、条件、动作和结果。把“必要时重试”改成执行者、触发错误、次数、间隔和终态。将未知项列为具体问题，不在每句话里重复“可能、通常、视情况”。

分别标明当前实现、已记录的历史理由、解释性推断和未来建议。代码证据与命令执行记录分开；测试文件存在不代表测试运行通过。业务词必须说明适用范围和项目口径。

## 包含的可运行工具

Python 工具仅使用标准库，运行环境为 Python 3.10+。辅助工具不自动安装系统或 npm 依赖。

| 工具 | 用途与边界 |
| --- | --- |
| [inventory.py](skills/repo-docs/scripts/inventory.py) | 只读文件名和 Git 元数据，输出技术线索、入口候选和快照；不自动识别业务模块 |
| [render_diagrams.py](skills/repo-diagrams/scripts/render_diagrams.py) | 调用已安装的 `mmdc`，全部图成功后发布 SVG；失败保留之前生成物 |
| [build_offline.py](skills/repo-docs-site/scripts/build_offline.py) | 将随包 HTML 模板的 CSS/JS 内联为单文件；不生成或推断业务内容 |
| [validate_docs.py](skills/repo-docs-review/scripts/validate_docs.py) | 检查文档映射、路径、覆盖、引用和核验状态；不证明业务语义正确 |
| [impact_docs.py](skills/repo-docs-review/scripts/impact_docs.py) | 根据 diff 和模块依赖生成候选复核列表，保留未映射变更 |

每个工具提供 `--help`。具体参数、失败行为和输出约定见对应技能。将下面变量替换为实际技能目录后，从业务仓库运行：

```bash
DOCS_SKILLS_ROOT=/absolute/path/to/docs_skills/skills
python3 "$DOCS_SKILLS_ROOT/repo-docs/scripts/inventory.py" --repo . --output docs/.meta/inventory.json
python3 "$DOCS_SKILLS_ROOT/repo-docs-review/scripts/validate_docs.py" --repo . --manifest docs-map.json
```

示例 JSON 中的路径和占位内容需要用真实调查结果替换。通过宽松结构检查后，再按项目交付条件使用 `--strict`。关键 pending 信息阻断严格检查；非关键解释性推断可保留警告，未知维护人不会被伪造为已确认人员。

## 约定与交付

- 统一维护 [docs-map 数据约定](skills/repo-docs/references/data-contract.md)。模块词条字段为 `modules[].terms`，值为词条 ID；`glossary.json` 的顶层 `terms` 保存完整词条。
- 每个模块有具体执行流程，关键节点关联源码证据；图源与生成的 SVG 不分别手工维护。
- 默认使用已有文档站。新建时采用 Starlight + Markdown/MDX + 构建生成的 SVG；Mermaid 不是 Starlight 无配置即用的内置能力。
- HTML 组件始终保留完整图与步骤说明。随包组件只突出当前说明卡片，不声称重放真实运行轨迹或自动高亮 SVG。
- 新人教程包含初始化、最小数据、真实业务操作和可观察结果；开发指南写清修改位置与测试。
- 完整交付包括正文、图源、站点源码与构建方式、词典、证据、维护索引和实际验证记录。

## 验证技能包

在本仓库运行：

```bash
python3 scripts/check_skills.py
python3 -m unittest discover -s tests -v
node --check skills/repo-docs-site/assets/flow-reader.js
```

GitHub Actions 执行同样的静态检查和工具测试。工具测试包含专门标注的模拟 Mermaid 编译器，验证失败回滚和输出保护；它们不代表真实 Mermaid 渲染、Astro 站点构建或业务语义已经通过。使用本包编写具体仓库文档时，还要运行对应项目构建并实际检查页面。

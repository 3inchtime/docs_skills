# 审查工具的数据合约

## 目录

- 路径与输出约定
- docs-map.json
- 证据与审查状态
- 业务词典
- 严格模式与能力边界

## 路径与输出约定

`--repo` 是仓库根目录。`--manifest`、映射中的路径、`--changed-files` 文件及其列出的改动都使用仓库相对 POSIX 路径，例如 `src/export.py`。不允许绝对路径、`..`、反斜杠、NUL 或解析后越出仓库的符号链接。

`source_paths` 可以引用目录或文件；页面、图源、生成图、入口和证据要求文件。影响分析允许已经删除的路径，避免漏掉删除和重命名；结构检查会报告不存在的引用。

工具把 JSON 写到 stdout。`validate_docs.py` 退出码：`0` 结构检查通过，`1` 存在检查错误，`2` 输入无法读取。`impact_docs.py`：`0` 候选集生成成功，`2` 输入、Git refs 或映射无效。参数错误返回 `2`。JSON 路径定位具体字段，例如 `$.modules[0].diagrams`。

## docs-map.json

`schema_version` 必须是整数 `1`；允许附加项目需要的字段。

| 字段 | 类型及含义 |
| --- | --- |
| `snapshot` | 代码快照对象。 |
| `snapshot.commit` | 完整 40 或 64 位十六进制 SHA；未确认时填 `null`，不能伪造。 |
| `snapshot.worktree` | `clean`、`dirty` 或 `unknown`。 |
| `snapshot.captured_at` | 实际记录时间字符串，建议 ISO 8601。 |
| `snapshot.changes` | dirty 时描述纳入文档的未提交变化，可用摘要或记录路径。 |
| `glossary` | 词典 JSON 路径；无领域词时使用空 `terms` 数组并说明调查结论。 |
| `modules` | 非空模块数组；范围仍由入口调查和人工审查确定。 |
| `excluded` | 可选数组，元素包含 `path` 和具体 `reason`。 |
| `open_questions` | 可选数组，元素包含 `question` 和显式布尔值 `blocking`。 |

每个模块记录：

| 字段 | 类型及含义 |
| --- | --- |
| `id` / `title` | 非空字符串；模块 ID 全局唯一且稳定。 |
| `page` | 主页面相对路径。 |
| `source_paths` | 至少一个源码或配置路径；目录映射用于较粗的影响提示。 |
| `entrypoints` | `{path, symbol, trigger}` 数组，包括业务入口或公共模块实际调用/使用入口。 |
| `diagrams` | `{source, kind, generated?, node_ids?}` 数组。 |
| `evidence` | 下节定义的非空证据数组。 |
| `terms` | 已存在词条 ID 数组，无相关词时可为空。 |
| `depends_on` | 依赖模块 ID 数组。A 使用 B，则 A 列 B；B 变化提示检查 A。 |
| `owner` | 维护者或团队字符串，未确认可填 `null`。 |
| `review` | `{code, reader, site}`，每项为 `pending`、`passed` 或 `failed`。 |

图形 `kind` 支持 `flowchart`、`sequence`、`state`、`er`、`data-flow`。每模块至少一张 `flowchart` 或真实 `data-flow`。`node_ids` 在单张图中不可重复；工具不会解析 Mermaid 核验这些 ID，渲染和映射检查另行执行。

`generated` 可选，填写时必须指向已生成文件。交付检查通常放在图形和站点构建之后；不能删除已承诺的输出引用来掩盖缺图。

## 证据与审查状态

证据包含 `id`、`kind`、`path`、`statement`、`status`、`method`，可另含 `symbol` 和 `critical`。证据 ID 全局唯一。

| `kind` | `method` | 支持的陈述范围 |
| --- | --- | --- |
| `source` | `read` | 读取了指定实现、配置或约束，不代表已经运行。 |
| `test` | `read` | 读取了测试与断言，不代表测试通过。 |
| `test` | `executed` | 确实执行测试，另保存命令、环境和结果。 |
| `runtime` | `observed` / `executed` | 指定环境和输入下的观察或运行记录。 |
| `business` | `read` / `confirmed` | 读取业务资料或取得明确确认。 |

证据 `path` 指向仓库里保留的来源文件或核验记录。外部资料的 URL、范围和摘录放入记录，不把 URL 填进本地路径。脚本只检查枚举配对，无法证明资料读过、命令执行过或结论确认过。

`status` 使用 `verified`、`inferred`、`pending`。`critical` 可选，默认 `true`。状态迁移、金额/数量计算、资格、事务、副作用、重试和最终结果通常属于关键行为证据。

历史动机没有记录但可提出解释时，放在独立推断段；不影响当前行为理解的解释可用 `inferred`、`critical: false`。未来建议标为提案，不能作为现状获取 `verified`。

`review.*: passed` 由实际结果支撑，不由脚本自动写入。`site` 对应承诺的交付形式；静态 Markdown 和交互网站的实际检查不同，记录范围。

## 业务词典

根对象为 `{ "schema_version": 1, "terms": [...] }`。

每条词记录 `id`、`name`、`definition`、`scope`、`project_meaning`、`example`，以上均为非空字符串；另含：

- `aliases`：字符串数组。
- `code_refs`：`{path, symbol?}` 数组，路径指向真实代码或配置。
- `sources`：`{title, url?, path?}` 数组，至少有 URL 或本地文件路径；URL 仅接受 HTTP(S)，脚本不会联网核验内容。
- `status`：`verified`、`inferred` 或 `pending`。
- `critical`：可选布尔值，默认 `true`。

已核验词条至少有一个来源和一个本系统代码映射。尚未映射的词保留 `pending`。行业资料支持行业定义，项目口径仍需实现和业务资料支持。

工具不能判断词是否真正属于业务领域。审查者删除通用技术词，保留在本系统中有特殊业务含义的普通词。

## 严格模式与能力边界

两种模式都拒绝缺文件、越界路径、错误类型、重复 ID、未知引用和已声明模块的覆盖缺口。关键未确认、未完成审查与阻断问题在普通模式警告，`--strict` 升为错误。

`critical: false` 推断仍显示警告，可以保留；`owner: null` 不阻断。含占位文字的 `verified` 项是错误，防止待填写内容被包装成完成结果。

漏掉整个模块时，清单自身可能仍然通过；必须与真实入口清单交叉核验。SHA、存在的路径、合法状态和 `passed` 字样都不能证明语义正确。

影响分析读取当前映射，以路径匹配和反向模块依赖生成候选。重命名按删除与新增处理；Git commit diff 不含未提交变化，应另收集到 `--changed-files`。

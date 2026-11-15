# 文档数据约定

## 路径

维护 UTF-8 `docs-map.json`。所有 `path`、`page`、`source`、`generated`、`glossary` 和 `source_paths` 值使用仓库根目录相对 POSIX 路径。拒绝绝对路径、`..` 和越界符号链接。外部 URL 放来源字段或带来源的证据记录文件。

`source_paths` 可为文件或目录，其他具体引用指向文件。目录映射便于影响提示，不证明目录里全部内容都读过。

## docs-map.json

从 [../assets/docs-map.example.json](../assets/docs-map.example.json) 填入实际索引。示例路径不代表当前仓库。

顶层字段：`schema_version: 1`；`snapshot` 记录 commit、worktree（clean/dirty/unknown）和 captured_at；`glossary` 指向词典 JSON；`modules` 为模块清单；`excluded` 记录路径和理由；`open_questions` 中阻塞问题使用 `blocking: true`。

commit 使用完整 SHA，未取得时为 null；dirty 时在 `snapshot.changes` 记录纳入文档的未提交变化摘要或记录路径。`generated` 仅在 SVG 已生成时填写，交付检查会核对文件是否存在。

模块字段：

- `id`、`title`、`page`、`source_paths`。
- `entrypoints`：`path`、`symbol`、`trigger`。
- `diagrams`：`source`、`kind`、可选 `generated` 和 `node_ids`；至少有 flowchart 或 data-flow。其他种类为 sequence、state、er。
- `evidence`：`id`、`kind`、`path`、可选 `symbol`、`statement`、`status`、`method` 和可选 `critical`。
- `terms`：词条 ID；`depends_on`：依赖模块 ID。
- `owner`：确认的归属或 null，不虚构人员。
- `review`：code、reader、site，各为 pending、passed 或 failed。

证据 kind：source、test、runtime、business。method：read、executed、observed、confirmed。status：verified、inferred、pending。

`verified` 必须结合 kind 和 method 理解。source/read 仅代表读过实现；检查器不能证明测试运行或生产行为。

`critical` 默认 true。只有不阻碍当前行为解释的补充信息才设为 false；严格模式允许这类推断留下警告，关键规则未查清则不通过验收。

## glossary.json

结构为 `{ "schema_version": 1, "terms": [...] }`。词条记录 id、name、aliases、definition、scope、project_meaning、example、code_refs、sources、status，以及可选 critical。

code_refs 使用真实 path 与可选 symbol。sources 记录 title 和 url，或本地业务资料 path。公司内部术语无需强行找公共定义，行业含义与项目口径分别说明。

## 版本与图源

正文和图源为维护入口，HTML/SVG 为生成物。节点说明通过稳定 ID 连接，不重复手工维护拓扑。选结构化模型时由模型同时生成图和交互数据。

永久链接固定当时依据，增量检查提示后续变化。未提交改动记录为工作区状态，不冒充 HEAD 内容。

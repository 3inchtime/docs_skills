---
name: repo-docs-review
description: 审查仓库交接文档的模块边界、运行与数据流、关键实现和异常处理。用于文档 review、codebase handover audit、独立读者测试、词典与图形核对、变更影响分析及文档 CI。
---

# 仓库文档审查与持续维护

分别回答三个问题：说明是否符合代码，新同事是否能独立理解，交付页面是否能正常使用。把每类结果写到具体问题和证据，不合成没有依据的评分。

## 开始工作

1. 确认仓库、代码快照、文档入口、工作区改动和审查范围，复用项目规则与已授权操作。
2. 读取模块清单、正文、图源、词典和核验记录。使用映射前读 [数据合约](references/data-contract.md)。没有映射时从实际文件整理，不能制造“全部通过”的清单。
3. 全量交接审查覆盖全部约定模块；PR 审查先定位影响，再检查改变的路径和上下游。
4. 记录具体缺口及影响，继续完成其他检查。只集中询问资料中无法回答且影响业务判断的问题。

## 执行结构检查

把 `review_skill_dir` 设置为本技能实际所在目录。仓库路径和 refs 必须来自当前任务。

```bash
python3 "$review_skill_dir/scripts/validate_docs.py" \
  --repo /path/to/repository --manifest docs-map.json

python3 "$review_skill_dir/scripts/validate_docs.py" \
  --repo /path/to/repository --manifest docs-map.json --strict
```

标准库脚本检查声明模块的页面、源码路径、图源、词典引用、ID、状态和路径边界。它不自动发现全部模块，不检查符号语义，也不执行 Mermaid、项目测试或浏览器。

- 普通模式把待确认证据和未完成审查列为警告，结构错误返回非零。
- `--strict` 阻断关键待确认/推断、未完成审查和 `blocking: true` 的问题。
- 证据和词条的 `critical` 默认为 `true`。不影响行为理解的解释性推断可用 `critical: false`，保留依据和推断标签。
- 不为通过 CI 删除真实不确定性，也不将 `pending` 改成没有证据的 `verified`。
- 维护者姓名未知可保留 `null`，不会阻断；它不等于业务行为未知。

遇到“按日期筛选”这类看似完整的说明时，可参考[报告期间的边界审查示例](references/date-boundary-example.md)，从一句待审文字追到代码、测试输入和修订结果。

## 核对业务事实与图

按[审查协议的五项语义检查](references/review-protocol.md#五项语义检查)审阅同一条场景。先从入口正向追到完成，再从最终字段或副作用反查生产者；将缺失的交接定位到正文或图上的具体位置。重点检查：

- 同步返回与最终完成是否区别，异步过程的完成条件是什么。
- 重试次数是否包含首次尝试，谁触发，哪些错误会重试。
- 消息与外部调用在事务前、内或后发生，失败后实际留下什么状态。
- 图中关键分支能否定位代码或测试，图和正文是否一致。
- “测试通过”是否有执行记录。读测试文件只能证明读过测试。
- 当前实现、历史决策、解释性推断和新建议是否区分。

有依据的行为直接陈述，未知项写出具体缺口及影响。把“必要时重试”“合理配置”“完善机制”展开成条件、执行者、参数与结果。

## 做独立读者测试

使用 [读者任务模板](assets/reader-task-template.md)。新读者只得到文档和任务，不得到作者上下文、源码或预期答案。

在复述主线之外，从实际实现选一个正文未直接作答的新情形，让读者预测下游结果、留下的状态或应改的位置，给出推理和页内依据。审查者单独用源码或运行核对；关键一步只能靠猜时标记该模块的读者审查失败，修正文档后用等价的新情形复测。

无法取得独立读者或全新上下文时记录未完成；作者自查单独标识。

## 定位代码变更影响

```bash
python3 "$review_skill_dir/scripts/impact_docs.py" \
  --repo /path/to/repository --manifest docs-map.json \
  --base BASE_COMMIT --head HEAD_COMMIT

python3 "$review_skill_dir/scripts/impact_docs.py" \
  --repo /path/to/repository --manifest docs-map.json \
  --changed-files docs/changed-files.json
```

`--changed-files` 输入是仓库相对路径的 JSON 数组，适合非 Git 环境或已收集的工作区变化，与 `--base/--head` 互斥。

工具按当前映射匹配来源、入口、证据、正文与图源，再沿 `depends_on` 反向找使用方，输出候选页面、图源、词条、原因和未映射改动。检查未映射文件、新增入口、删除模块和契约使用方；不能将候选集称为穷尽的影响分析。

## 完成维护与交付

按 [维护流程](references/maintenance.md) 更新受影响内容，执行项目实际的文档构建、图形、链接与浏览器检查。命令存在或已列出不等于执行成功。

使用 [审查记录模板](assets/review-report-template.md) 交付：范围与快照、具体问题和依据、实际修正、各项独立检查结果、仍阻断接手的缺口、不阻断正文的解释性推断、增量更新入口与维护归属。

用户已授权修改时直接修复能确定的问题。提交、推送或发布沿用本次任务的授权范围，不增加重复确认。

# 按报告期间导出 CSV

这是一个可运行的合成业务仓库。登记表有三条报告记录。读完本页，你可以导出其中两条、找到日期判断的位置，并用技能包检查文档与代码的对应关系。以下命令均在技能包根目录执行，使用 Python 3.10+。

## 导出两天的报告

```bash
python3 examples/report-export/export_report.py 2026-11-01 2026-11-02
```

终端应输出：

```csv
date,report_id
2026-11-01,R-001
2026-11-02,R-002
```

“报告期间”包含开始日和结束日。筛选依据是登记表中的 `date` 字段，记录顺序与登记表相同。把结束日改为 11 月 1 日，只会得到第一条报告。日期无效或开始日晚于结束日时，命令向标准错误输出参数错误，以状态码 2 退出。合法区间内没有记录时，输出仍含 CSV 表头。[示例登记表](reports.csv) · [模块流程图源](flow.mmd) · [业务词典](glossary.json)

## 修改日期筛选规则

打开 `export_report.py` 的 `main`。参数解析和起止日校验在输出表头之前执行；逐条读取登记表时，两个比较运算符决定是否包含边界日期。修改边界时，同步核对图中的“记录日期在闭区间内”、词典的“报告期间”和边界测试。[模块源码](export_report.py) · [示例测试](../../tests/test_report_export_example.py)

```bash
python3 -m unittest discover -s tests -p test_report_export_example.py -v
```

## 用技能包检查交付物

```bash
python3 skills/repo-docs/scripts/inventory.py --repo examples/report-export
python3 skills/repo-docs-review/scripts/validate_docs.py --repo examples/report-export
```

第一条命令列出代码调查线索。第二条会读取本示例的文档映射，找到一个模块和一个词条，并检查模块页、源码、图源及词条引用。预期结果为 `ok: true`、零个错误，并提示读者审查和站点审查待办。加上 `--strict` 可观察这两项待办如何阻断交付。[文档映射](docs-map.json)

在支持 Agent Skills 的助手中，可以用这个任务练习独立审查：

> 使用 $repo-docs-review 审查 examples/report-export。请仅凭模块文档说明同一天能否作为起止日、日期顺序颠倒时会输出什么，以及调整边界条件要改哪一处。再运行命令，对照源码核验三个答案。

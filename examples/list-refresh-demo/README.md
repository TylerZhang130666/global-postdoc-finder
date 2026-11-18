# 清单更新演示（合成数据）

本目录全部为**合成的虚构记录**，使用保留的 `.example` 示例域名，仅用于展示和测试差异规则。它不是本次新搜到的岗位，也不能证明任何真实雇主变更了招聘条件。

- [previous.json](previous.json)：旧快照，4条。
- [current.json](current.json)：新快照，5条，其中一条批内重复。
- [expected-diff.json](expected-diff.json)：保存前后证据与变化解释的预期输出。

在仓库根目录运行：

```text
python scripts/diff_records.py examples/list-refresh-demo/previous.json examples/list-refresh-demo/current.json --as-of 2026-11-18 --out changes.json
```

| 对比结果 | 数量 | 应如何理解 |
|---|---|---|
| 新增 | 1 | 在这两份输入中首次出现；不宣称是刚发布的职位 |
| 同一机会再次找到、条件未变 | 1 | 本次ID或跟踪参数不同不代表新岗位 |
| 条件变化 | 1 | 保留旧值、新值与证据日期 |
| 输入中有已核实关闭证据 | 1 | 只依据给定证据判断，不是脚本访问了网站 |
| 旧记录未再次出现 | 1 | `missing_unverified`，需要重访，不能自动认定关闭 |
| 新批次内部重复组 | 1 | 单独记录重复，不把它算成两个新机会 |

前五行是变化条目，最后一行是另列的重复组。评分和行动等级变化会单列为`decision_changes`，不算官方招聘条件变化。身份冲突或新证据比旧证据还早时，脚本输出待人工确认。

脚本只比较JSON；`verified`等字段由输入者提供，不验证这些标签是否真实。正式更新仍需按[清单更新流程](../../references/task-workflows.md#saved-list-refresh)重新核验网页并检查候选人、搜索范围与规则版本是否可比。

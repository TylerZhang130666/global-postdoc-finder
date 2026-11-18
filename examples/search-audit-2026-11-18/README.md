# 正文检索与翻页遗漏核查

检查日期：2026-11-18。此处是固定快照，在线岗位库会继续更新。

## 结果

- 13 个来源均启用正文索引；480 条收录记录中，434 条正文成功读取，46 条暂不可读（香港大学 44 条访问验证，jobs.ac.uk 2 条无可解析正文）。
- 补收列表记录 100 条：Yale 从 28 条补至 111 条，Max Planck 从首批 3 条补至完整可读列表 20 条。旧公告也包括在内，不能据此认定均在招聘。
- 同一批原有 380 条记录，28 组测试词新增 1128 个“查询—岗位”命中，涉及 304 条不同公告；它们是关键词漏检记录，不是新增职位或确认相关职位。
- AcademicTransfer 首屏显示 10 / 182 个搜索结果；后续公开 API 被 robots 禁止采集，另有 172 个搜索结果未覆盖，尚未逐项核实、去重或确认为博后岗位。
- 其余来源按已实现的公开分页读到末尾；多个来源仍只保留标题明确标为博后的条目。Research Associate / Research Fellow 等相邻职位可能被排除，此次没有把未核实的相邻职位计入补收数量。

## 固定样本对比

前后使用相同标题、摘要、机构、地点，仅替换正文词项；使用网页实际匹配函数，不隐藏过期记录，避免截止日期变化影响比较。原版已有德国部分正文索引，因此“之前”含该证据。多关键词按空格交集匹配，并非短语精确搜索。全文中 “environment” 可能只是工作环境，“materials” 可能是申请材料，命中数不代表学科相关性。

| 查询词 | 之前 | 正文索引后 | 新增命中 |
| --- | ---: | ---: | ---: |
| soil | 2 | 4 | 2 |
| carbon | 5 | 12 | 7 |
| ecology | 9 | 15 | 6 |
| remote sensing | 2 | 8 | 6 |
| GIS | 0 | 6 | 6 |
| machine learning | 3 | 69 | 66 |
| bioinformatics | 5 | 30 | 25 |
| plant | 10 | 20 | 10 |
| climate | 10 | 50 | 40 |
| hydrology | 0 | 0 | 0 |
| agriculture | 0 | 2 | 2 |
| environment | 29 | 220 | 191 |
| statistics | 8 | 40 | 32 |
| biology | 41 | 109 | 68 |
| chemistry | 26 | 78 | 52 |
| physics | 37 | 83 | 46 |
| materials | 36 | 168 | 132 |
| genetics | 5 | 36 | 31 |
| neuroscience | 17 | 46 | 29 |
| economics | 6 | 22 | 16 |
| psychology | 5 | 29 | 24 |
| robotics | 6 | 16 | 10 |
| imaging | 6 | 56 | 50 |
| geography | 2 | 8 | 6 |
| modelling | 7 | 31 | 24 |
| Python | 6 | 72 | 66 |
| data science | 20 | 195 | 175 |
| satellite | 1 | 7 | 6 |

## 各来源正文覆盖

| 来源 | 已收录 | 正文已索引 | 暂不可读 |
| --- | ---: | ---: | ---: |
| academictransfer | 10 | 10 | 0 |
| hku | 50 | 6 | 44 |
| csiro | 5 | 5 | 0 |
| yale | 111 | 111 | 0 |
| stanford | 83 | 83 | 0 |
| leibniz | 16 | 16 | 0 |
| mpg | 20 | 20 | 0 |
| eth | 28 | 28 | 0 |
| copenhagen | 14 | 14 | 0 |
| kth | 13 | 13 | 0 |
| ubc | 7 | 7 | 0 |
| jrec | 102 | 102 | 0 |
| jobsuk | 21 | 19 | 2 |

## 复核

基线：提交 `f7feee4ee92193e342fd59029c137fdfe8e6f1b4` 的 `web/data/jobs.json`（生成时间 2026-11-18T12:23:00+00:00）。对比快照：提交 `9ee37d414909c30cf80180ce28588273eee5a774` 的 `web/data/jobs.json`；后续版本已扩充，不能直接代替本次固定快照。原始网页正文留在本地，不提交联系人或全文。

```sh
git show f7feee4ee92193e342fd59029c137fdfe8e6f1b4:web/data/jobs.json > baseline.json
git show 9ee37d414909c30cf80180ce28588273eee5a774:web/data/jobs.json > current.json
node scripts/audit_fulltext.mjs baseline.json current.json examples/search-audit-2026-11-18/queries.json comparison.json
```

逐条新增命中的公告 ID 和覆盖数量见 [comparison.json](comparison.json)，可对应岗位库中的原始 URL。

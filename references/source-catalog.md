# 结构化来源目录

维护数据见 [source-catalog.json](source-catalog.json)。它帮助按地区、研究方向和路线选择来源；更广的地区入口与本地检索词仍见 [全球来源指南](global-postdoc-resources.md)。本目录是经过一次入口核查的精选起点，不代表完整覆盖全球或所有学科。

## 使用方式

1. 根据用户地区和研究方向选渠道，分开搜现有招聘、个人/接收机构基金、潜在团队。香港和澳洲现有条目分别是HKU与CSIRO雇主入口，不能代表两地全部岗位。
2. 每次搜索另建 [覆盖记录](../assets/search-coverage-template.json)，记录实际关键词、检查范围、访问日期和保留结果。目录的`checked_on`是维护日期，不能抄作这次用户搜索的核查日期。
3. 当目录入口受限，可用官方域名限定搜索寻找公告或在正常浏览器中查看；仍打不开就记录受限及待办。搜索摘要只支持发现，不替代官方公告核验。不要绕过登录或访问控制。
4. 找到候选项后回到逐条核验：雇主、官方公告、是否开放、截止时区、申请入口、资格和下一步。网站可访问不说明某一招聘或基金开放。

## 数据字段

| 字段 | 含义 |
|---|---|
| `source_id` | 维护中的稳定来源标识，可用于关联一次搜索的覆盖记录 |
| `name` / `url` | 来源名称与可用入口；保留有意义的查询参数 |
| `regions` / `disciplines` | 来源适用范围及限制；不是候选人资格承诺 |
| `opportunity_types` | 可支持的发现路线：`advertised_job`、`fellowship`、`potential_host` |
| `source_role` | 入口用途：`job_portal`、`employer_careers`、`fellowship_programme`、`funding_portal`、`hosting_portal`、`project_database` |
| `search_method` | 推荐检索方法、分类与需注意的路线差异；不是已执行搜索的声明 |
| `login_requirement` | 分别记录`browsing`、`search`、`application`和说明`note` |
| `checked_on` | 本条入口核查日期，ISO `YYYY-MM-DD` |
| `access_status` / `access_note` | 本次工具可访问程度和实际观察 |
| `evidence_url` | 支持用途或访问判断的官方页面；必要时有`additional_evidence_urls` |

`login_requirement`各阶段值为`not_required_observed`（只对本次已公开读取的页面）、`required_observed`（实际见到强制登录）、`unknown`（未测试或受限）、`not_applicable`（例如项目库的岗位申请）。同站有登录按钮不能证明浏览需要登录；HTTP 403、超时或JavaScript页面也不能证明登录要求。

`access_status`值：

- `accessible`：本次可读入口的主要内容。筛选提交、具体岗位和申请系统可能尚未测试，限制写入`access_note`。
- `limited`：介绍可读但目标搜索受限，或只返回JavaScript壳。按说明继续核查，不能写成已完成站内检索。
- `inaccessible`：本次直读入口失败。保留错误与官方索引提供的线索，不能从失败推断零岗位。

## 2026-11-18核查发现

- [EURAXESS官方Jobs & Opportunities页](https://euraxess.ec.europa.eu/jobs)给出独立的Jobs和Hosting搜索入口。本次两类搜索端点均403，目录保留官方链接并标记`limited`。Hosting表明接收意向，应先进入`potential_host`路线；须继续确认合作申请方式和经费，不能直接当成已资助岗位。
- [GEPRIS](https://gepris.dfg.de/about/recherche?lang=en)和[RePORTER](https://reporter.nih.gov/)在本次文本访问中只显示JavaScript要求。其用途分别由[DFG官方说明](https://www.dfg.de/en/funded-projects/information-systems)和[NIH官方FAQ](https://report.nih.gov/faqs)支持；未完成库内查询。二者只用于发现项目、PI及机构，项目经费不证明正在招博后。
- [RGC JRFS](https://www.ugc.edu.hk/eng/rgc/funding_opport/jrfs/)和[HKU Careers](https://jobs.hku.hk/en/listing/)直读超时；[jobs.ac.uk](https://www.jobs.ac.uk/)直读403。官方页面搜索索引提供了入口线索，但状态仍按直读限制记录，不能宣称实时岗位已核验。JRFS应单独核对大学提名流程、当轮call和明确日期，不能凭长期保留的“Open”横幅判断可申请。
- [FAPESP旧机会入口](https://fapesp.br/oportunidades/)跳转到[新的机会目录](https://oportunidades.fapesp.br/)。该页说明选拔公告内容由相应项目PI负责，不能把它们当成FAPESP机构性call或统一资格规则。
- [MSCA PF](https://marie-sklodowska-curie-actions.ec.europa.eu/actions/postdoctoral-fellowships)是与host共同申请的基金路线；[UKRI Funding finder](https://www.ukri.org/opportunity/)混有fellowship、grant等类型，需先筛选再检查个人和机构资格。二者都不等同于现成招聘。

## 与一次运行覆盖记录的区别

目录条目的访问状态仅用于选择检索路径。每次用户报告要另行区分：实际查过并保留结果、查过但没有保留结果、部分查过、访问受限、尚未搜索。没有保留结果可能是没有匹配项、已过期、资格不符或搜索范围有限，应写清原因；不能宣称该地区或学科不存在机会。

每次维护只更新实际复查的条目日期和证据。新增来源应说明它补充的地区、学科或路线，先检查是否只是重复已有内容。入口可以长期存在，轮次规则、地址、可用性和具体机会状态仍需在下一次使用时重新核验。

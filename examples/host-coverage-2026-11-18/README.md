# 导师名录覆盖：2026年11月18日

本轮从89条扩充到705条，涵盖15所机构、12个地区。89条旧数据中78条来自斯坦福招聘公告，来源偏集中。本轮新增机构名录抓取，并保留公告关联和人工核对资料。

这不是全球导师全集，也没有测量全球召回率。东京大学266条、UBC182条仍占多数；更多条目不能直接解释成更全面。

| 官方来源 | 原始记录数 | 本轮范围 |
| --- | ---: | --- |
| [东京大学农业与生命科学](https://www.a.u-tokyo.ac.jp/english/researchers_e/profile_e/) | 266 | 公开教师卡片；实验室/学科字段，未逐一阅读论文 |
| [ETH World Food System Center](https://worldfoodsystem.ethz.ch/people/members.html) | 40 | 成员及研究组；排除荣休栏目 |
| [剑桥植物科学](https://www.plantsci.cam.ac.uk/people/academic-staff) | 20 | Academic staff 两页；排除荣休人员 |
| [圣保罗大学土壤科学](https://lso.esalq.usp.br/pt-br/equipe/docentes) | 22 | 教师职称及研究兴趣 |
| [UBC森林与环境](https://www.grad.ubc.ca/prospective-students/faculties/faculty-forestry-environmental-stewardship) | 57 | Research Supervisors 三页 |
| [UBC土地与食品](https://www.grad.ubc.ca/prospective-students/faculties/faculty-land-food-systems) | 25 | Research Supervisors 一页 |
| [UBC理学院](https://www.grad.ubc.ca/prospective-students/faculties/faculty-science) | 100 | 前四页；未读完整个名录 |
| [南京农业大学资源与环境科学](https://re.njau.edu.cn/jsfc2.jsp?urltype=tree.TreeTempUrl&wbtreeid=1325) | 85 | 官网六个院系公开查询；教授/研究员且标注博士生导师，排除退休标识；跨系重复合并 |
| [波恩大学地理学研究组](https://www.geographie.uni-bonn.de/en/research/research-groups) | 14 | 团队记录，不推断未核实的负责人姓名 |

原始名录共629条，经相同姓名与机构、明确个人主页去重，再与旧数据合并得705条。原始计数含跨院系重复及与人工种子重合的记录，因此不能直接相加。UBC部分页面仅提供表格姓名，无单独个人链接，保留该表格作为依据；同一页面不同姓名可分别收藏。

NUS候选目录返回浏览器验证页；WUR候选目录证书校验失败；墨尔本和斯泰伦博斯候选目录拒绝访问。本轮没有批量加入这些目录，也没有关闭TLS校验或将挑战页当成教师资料。既有人工种子独立保留。

## 字段与更新

- 新记录统一标注招聘未核实；博士生导师名录不证明有博后岗位或经费。
- `research_scope=directory_fields` 表示只有名录中的实验室、学科或研究兴趣，不代表已完整阅读个人研究。南京农业大学简介多为个人经历；没有独立研究方向句时只保留院系名称，不将个人经历作为研究方向。
- `evidence_url`、`evidence_locator`、`checked_at`记录依据与读取时间。个人主页链接来自名录，不等于逐个检查过个人页面。
- `directory_hosts`保存允许公开的原始结构化记录，`hosts`供界面使用。小时岗位同步不会擦除名录证据；名录按七天缓存重读，失败保留旧记录和旧证据日期。失败来源次日可重试。
- 读取遵守来源robots规则、同域HTTPS分页、请求间隔和页数上限；结构不匹配时保留旧记录，不把空列表当成删除。
- 不保存邮箱、电话、出生日期、性别等API额外字段；原始HTML和API响应不加入公开仓库。
- 本地画像只按共同研究词匹配，不判断资格、资助或录取可能。

验证：99项Python测试、31项JavaScript测试通过；新增回归覆盖名录边界、共享目录链接、荣休排除、API字段最小化、失败日期与小时重建缓存保留。另做浏览器筛选及收藏检查。

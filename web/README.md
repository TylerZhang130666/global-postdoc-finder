# 博后搜索

[在线使用](https://tylerzhang130666.github.io/global-postdoc-finder/)

网页直接搜索已收录岗位，按地区、来源和截止时间筛选，查看详情、一键收藏。参考招聘网站的搜索栏、结果列表和侧边详情结构，保留白底、简单排版。无需模型 API、注册或安装依赖。

## 招聘数据

`scripts/sync_jobs.py` 同步五个公开招聘列表：

| 来源 | 本版范围 |
| --- | --- |
| AcademicTransfer | postdoc 关键词，结果第一页 |
| 香港大学 | 博后类别，最多五页；只保留含博后名称的标题 |
| CSIRO | postdoctoral 关键词，最多两页 |
| 耶鲁大学 | Open Positions，最多四页；排除单独的 postgraduate 职位 |
| 斯坦福大学 | 公开博后列表，最多两页；保留院系、导师与原始详情链接 |

这是有限来源的岗位索引，不声称完整覆盖全球。只收录来源列表中实际出现的字段；未知截止日期留空。摘要为来源列表短摘录，不生成申请资格或匹配分。收录时间不等于招聘状态或个人资格核验时间。

采集器遵守公开 robots 规则和访问间隔，不使用登录、绕过验证或代理。只跟随同域分页，按原链接去重。有来源失败时保留其旧记录和原收录日期，页面注明“上次记录”；来源说明显示部分更新。无法识别的 HTML 视为失败，不当作零岗位。

GitHub Actions 每天在 UTC 07:23、19:23 尝试刷新并部署；调度可能延迟。定时任务会先读取本站上次发布的缓存，读取失败才回退仓库快照。刷新不需要写回 GitHub 仓库或新凭据。

## 搜索与收藏

- 直接在索引中检索标题、机构、院系与短摘要；关键词按空格交集匹配。少量中文方向词对应英文词，例如“遥感”“机器学习”，不使用语义模型。
- 默认隐藏截止已过的记录，已注明时区的时刻按该时区计算；未注明截止时间的记录继续显示，是否招聘以原公告为准。
- 保留原站 `global-postdoc-finder:workbench:v1` 本地存储与 JSON 格式，旧收藏仍可编辑。搜索结果一键收藏不自动填写人工核验日期或确认资格。
- 收藏只在当前浏览器保存，可导出 JSON 备份或 CSV 查看；支持导入 Skill 的规范化记录。换浏览器、清除网站数据前请先备份。

## 开发

```sh
python scripts/sync_jobs.py
node --test web/tests/*.test.mjs
python -m unittest discover -s tests -v
python -m http.server 8769 --bind localhost --directory web
```

打开 http://localhost:8769 。Windows 沙箱不允许测试启动子进程时，可使用 `node --test --test-isolation=none web/tests/core.test.mjs web/tests/jobs.test.mjs`。

`.github/workflows/pages.yml` 在 PR 中运行离线测试；推送 `main`、手动运行或定时触发时，同步公开岗位后发布 GitHub Pages。发布物只包含页面、模块、图标、公开来源和岗位索引，不包含测试、试用候选人或个人 CV。

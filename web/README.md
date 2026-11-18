# 博后搜索工作台（无模型 API 版）

在线入口：https://TylerZhang130666.github.io/global-postdoc-finder/

原生 HTML / CSS / JavaScript，无安装依赖。`web/` 与博后搜索 Skill 位于同一仓库，由 `.github/workflows/pages.yml` 测试并发布到 GitHub Pages。

## 功能与边界

- 官方来源目录按地区、机会类型筛选；英文关键词可通过 Google 做限定域名检索，原入口也可直接打开。目录维护日期不等于本次已搜索。
- 链接识别只看 URL 和所属域名，不抓取正文、不确认有效岗位；用户打开公告后手动记录证据、资格条件与核验日期。
- 岗位、基金、潜在导师分开记录。没有匹配分或自动资格判断；日期已过只提示复查，不把尚未核实的机会认定关闭。
- 清单使用当前网站源下的浏览器 localStorage；不上传、不跨设备同步。更换浏览器或域名、清理网站数据可能丢失记录，请导出备份。
- JSON 备份可再导入；兼容 Skill 的规范化记录数组。导入保留原始 Skill 记录，不自动更新证据。CSV 供查看，不作为完整往返备份。
- 导入只接受不超过 5 MB、1000 条的记录；整批校验成功后合并，相同 URL/标题/机构/截止轮次不覆盖本机备注。导入文本以纯文本渲染，链接限不含凭据的 HTTP(S)，CSV 中和公式单元格。

## 本地预览与检查

在仓库根目录运行：

```sh
python scripts/build_web_catalog.py
node --test web/tests/core.test.mjs
python -m http.server 8769 --bind 127.0.0.1 --directory web
```

打开 http://127.0.0.1:8769 。请通过 HTTP(S) 预览，直接双击 HTML 会受模块与数据加载限制。

## 维护与部署

官方来源在 `references/source-catalog.json` 维护。区域路由与页面简介在 `scripts/build_web_catalog.py` 维护；生成器只读公开来源目录，不读取试用记录、个人资料或 CV。

GitHub 仓库 Settings → Pages → Source 设为 GitHub Actions。推送 `web/` 或来源目录到 `main` 后，检查通过即部署。PR 只运行检查，不部署。无需环境变量、API Key 或付费模型。网站发布产物只含静态网页文件与公开目录，不上传测试、Skill 示例或私有申请资料。

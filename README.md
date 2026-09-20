# C Hive Sage｜指标顾问 Web

C Hive Sage｜指标顾问是一个独立的、可本地运行的 ChatGPT 式指标知识问答工作台。V1.0 Web 版以原生 HTML、CSS 和 JavaScript 提供报表路由、模拟问答、知识依据、推荐追问及反馈交互，面向本地演示与后续产品化验证。

## 本地运行

在仓库根目录执行：

```bash
python3 -m http.server 8765
```

然后访问 <http://127.0.0.1:8765/>。

## 文件

- `index.html`：Web 版交互原型（后续任务创建）。
- `web版report_ai需求文档.md`：需求、验收标准和行为映射（后续任务创建）。
- `verify_web_prototype.py`：Web 交互契约校验（后续任务创建）。
- `verify_requirements_sync.py`：需求与实现一致性校验（后续任务创建）。
- `CHANGELOG.md`：版本变更记录。
- `docs/2026-09-20-c-hive-sage-web-design.md`：批准的设计规格。

## V1.0 原型边界

首版不包含 Power BI 截图、iframe 或筛选自动同步；不接入企业登录、真实大模型、向量检索、数据库、真实工单、反馈落库或历史会话持久化。Product、Member Tier、Binding、NPS 不输出确定性业务答案，相关工单和反馈均标注为模拟效果。页面不依赖外部前端库、字体、图片或网络资源。

原 Power BI 浮窗版本继续维护在 `jelenajy/crm_report_ai`；本仓库仅维护独立 Web 版交付物。

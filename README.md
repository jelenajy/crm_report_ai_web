# C Hive Sage｜指标顾问 Web

C Hive Sage｜指标顾问是一个独立的、可本地运行的 ChatGPT 式指标知识问答工作台。V1.0 Web 版以原生 HTML、CSS 和 JavaScript 提供报表路由、模拟问答、知识依据、推荐追问及反馈交互，面向本地演示与后续产品化验证。

## 本地运行

在仓库根目录执行以下命令。它会创建只含公开入口的临时目录，并仅监听本机回环地址；不要直接把仓库根目录作为服务目录，否则 `.git`、审查材料和开发文件可能被访问。

```bash
PUBLIC_DIR="$(mktemp -d)"
cp index.html "$PUBLIC_DIR/"
python3 -m http.server 8765 --bind 127.0.0.1 --directory "$PUBLIC_DIR"
```

然后访问 <http://127.0.0.1:8765/>。结束服务后可执行 `rm -r -- "$PUBLIC_DIR"` 删除临时目录。

## 文件

- `index.html`：Web 版交互原型与页面内静态知识配置。
- `web版report_ai需求文档.md`：需求、验收标准和 HTML 行为映射。
- `verify_web_prototype.py`：页面入口、DOM 与核心交互契约校验。
- `verify_requirements_sync.py`：结构化需求、映射表和实现证据的一致性校验。
- `verify_final_review_regressions.py`：最终审查修复项的静态与发布边界回归校验。
- `verify_web_runtime.html`：同源 iframe 浏览器行为回归页。
- `verify_web_runtime.py`：使用系统 Chrome/Chromium 运行浏览器回归，并验证临时服务不会暴露仓库文件。
- `CHANGELOG.md`：版本变更记录。
- `docs/2026-09-20-c-hive-sage-web-design.md`：批准的设计规格。

## V1.0 原型边界

首版不包含 Power BI 截图、iframe 或筛选自动同步；不接入企业登录、真实大模型、向量检索、数据库、真实工单、反馈落库或历史会话持久化。所有工单、反馈、历史会话和导航均为模拟效果，不代表真实后台处理或持久化记录。Product、Member Tier、Binding、NPS 不输出确定性业务答案。页面不依赖外部前端库、字体、图片或网络资源。

原 Power BI 浮窗版本继续维护在 `jelenajy/crm_report_ai`；本仓库仅维护独立 Web 版交付物。

## 验证

在仓库根目录运行：

```bash
python3 verify_web_prototype.py
python3 verify_requirements_sync.py
python3 verify_final_review_regressions.py
python3 verify_web_runtime.py
```

最后一项会自动查找 Chrome/Chromium，也可通过 `CHROME_BIN` 指定浏览器可执行文件。它只在 `127.0.0.1` 的随机端口启动临时服务，公开目录仅包含 `index.html` 和浏览器回归页；测试结束后目录与服务会自动清理。

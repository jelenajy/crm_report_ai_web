# Consumer Hive · C Hive Sage｜指标顾问

Consumer Hive 是报表系统全称；C Hive Sage｜指标顾问是其独立的指标知识问答工作台。V1.1 Web 页面采用深石墨侧栏、暖象牙内容区和香槟金交互元素，以原生 HTML、CSS 和 JavaScript 提供五报表切换、页面内知识回答、可展开知识依据、推荐追问及反馈交互。

当前实现的知识内容来自 `index.html` 内的静态配置。Customer Type 可展示已有口径；Product、Member Tier、Binding、NPS 的知识包待接入，暂不提供确定性业务答案。报表选择器采用定制圆角 listbox，鼠标与键盘均可操作；跨报表推荐卡使用相同的切换入口，历史回答保留提问时的报表快照。

## 本地运行

在仓库根目录执行以下命令。它会创建只含公开入口的临时目录，并仅监听本机回环地址；不要直接把仓库根目录作为服务目录，否则 `.git`、审查材料和开发文件可能被访问。

```bash
PUBLIC_DIR="$(mktemp -d)"
cp index.html "$PUBLIC_DIR/"
python3 -m http.server 8765 --bind 127.0.0.1 --directory "$PUBLIC_DIR"
```

然后访问 <http://127.0.0.1:8765/>。结束服务后可执行 `rm -r -- "$PUBLIC_DIR"` 删除临时目录。

## 文件

- `index.html`：Consumer Hive Web 入口、定制报表菜单、知识依据交互与页面内静态知识配置。
- `web版report_ai需求文档.md`：需求、验收标准和 HTML 行为映射。
- `verify_web_prototype.py`：页面入口、DOM 与核心交互契约校验。
- `verify_requirements_sync.py`：结构化需求、映射表和实现证据的一致性校验。
- `verify_final_review_regressions.py`：最终审查修复项的静态与发布边界回归校验。
- `verify_web_runtime.html`：同源 iframe 浏览器行为回归页。
- `verify_web_runtime.py`：使用系统 Chrome/Chromium 运行浏览器回归，并验证临时服务不会暴露仓库文件。
- `CHANGELOG.md`：版本变更记录。
- `docs/2026-09-20-c-hive-sage-web-design.md`：Web 版设计说明；详细 V1.1 规格见 `docs/superpowers/specs/2026-09-21-consumer-hive-premium-ui-design.md`。

## 当前技术边界

当前版本不包含嵌入式报表、筛选自动同步、企业登录、真实 AI 模型、向量检索、数据库、真实工单、反馈落库或历史会话持久化。`createTicket` 生成的编号、反馈选择和最近会话标题只存在于当前页面，刷新后不保留，也不会自动发送给报表负责人。页面中的知识回答来自静态配置，不代表实时查询。投入正式使用前需要接入受控的知识、记录和反馈服务，并完善权限与审计。页面不依赖外部前端库、字体、图片或网络资源。

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

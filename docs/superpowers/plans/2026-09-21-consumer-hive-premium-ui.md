# Consumer Hive Premium Web UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 C Hive Sage 独立 Web 工作台升级为已批准的 Consumer Hive 高级黑金 UI，同时保留现有知识路由、回答快照、响应式侧栏和安全边界。

**Architecture:** 继续使用无依赖单文件 `index.html`，在既有 `reportConfigs` 与回答路由之上替换页面外壳、视觉变量和报表选择控件。定制 listbox 只负责报表选择，仍通过统一的 `applyReportSelection(reportKey)` 驱动既有上下文更新；回答知识依据继续由 `renderAnswer` 生成唯一 ID，并由 `toggleCitation` 管理状态。Python 静态契约与同源浏览器回归共同验证代码、文档和运行行为。

**Tech Stack:** HTML5、CSS3、原生 JavaScript、Python 3 标准库、无外部运行时依赖。

## Global Constraints

- 企业报表系统全称固定为 `Consumer Hive`。
- AI 产品名称固定为 `C Hive Sage`，中文功能名称固定为`指标顾问`。
- 页面使用深石墨、暖象牙和克制香槟金，不引入外部字体、图片或前端依赖。
- 用户可见 HTML 不得出现`原型`、`原型演示`、`模拟效果`、`模拟提交`或`模拟导航`。
- 不接入真实模型、检索、数据库、工单、反馈落库或会话持久化；README 和需求文档必须如实声明边界。
- 保持五报表路由、问题快照、知识依据、追问、反馈、Toast、最近对话和移动侧栏行为。
- 定制报表菜单支持鼠标、上下方向键、Escape、外部点击关闭与焦点返回。
- 八角北极星动画周期为 `3.6s`，并响应 `prefers-reduced-motion: reduce`。
- 完成后推送到 `git@github.com:jelenajy/crm_report_ai_web.git` 的 `main` 分支。

---

### Task 1: 锁定新版静态契约并重构品牌外壳

**Files:**
- Modify: `verify_web_prototype.py`
- Modify: `verify_final_review_regressions.py`
- Modify: `index.html`

**Interfaces:**
- Consumes: 现有 DOM ID `newChatBtn`、`questionInput`、`sendBtn`、`sidebar`。
- Produces: `.consumer-hive-brand`、`.hive-mark`、`.north-star`、`.report-trigger`、`#reportMenu`、`[data-report-option]`、`.welcome-copy` 和新版文案契约。

- [ ] **Step 1: 写入失败的品牌、禁用词和控件结构测试**

在 `verify_web_prototype.py` 增加：

```python
VISIBLE_BANNED_COPY = ("原型演示", "模拟效果", "模拟提交", "模拟导航")

for token in ("Consumer Hive", "C Hive Sage", "指标顾问", "CONSUMER HIVE INTELLIGENCE"):
    if token not in source:
        return fail(f"missing premium brand token: {token}")

for token in VISIBLE_BANNED_COPY:
    if token in source:
        return fail(f"visible prototype copy remains: {token}")

for token in ('class="hive-mark"', 'class="north-star"', 'id="reportMenu"', 'data-report-option'):
    if token not in source:
        return fail(f"missing premium UI contract: {token}")
```

在 `verify_final_review_regressions.py` 增加 CSS 结构断言：

```python
check("3.6s" in css_rule(index, ".north-star"), "north-star twinkle duration must be 3.6s")
check("prefers-reduced-motion: reduce" in index, "logo motion must honor reduced-motion")
check("border-radius: 16px" in css_rule(index, ".report-menu"), "report menu must be rounded")
check("border: 0" in css_rule(index, ".report-menu"), "report menu must not have an edge line")
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
python3 verify_web_prototype.py
python3 verify_final_review_regressions.py
```

Expected: FAIL，分别提示缺少 Consumer Hive 高级品牌结构、八角北极星或定制菜单。

- [ ] **Step 3: 重构 `index.html` 页面外壳和视觉系统**

替换现有侧栏和欢迎区，保留核心 ID。品牌结构使用：

```html
<div class="consumer-hive-brand">
  <div class="hive-mark" aria-label="Consumer Hive 北极星标识">
    <svg viewBox="0 0 48 52" role="img" aria-hidden="true">
      <circle class="star-halo" cx="24" cy="26" r="10.5"></circle>
      <path class="north-star" d="M24 1L27.4 19.4L36.5 13.5L30.4 22.4L45 26L30.4 29.6L36.5 38.5L27.4 32.6L24 49L20.6 32.6L11.5 38.5L17.6 29.6L3 26L17.6 22.4L11.5 13.5L20.6 19.4Z"></path>
      <circle class="star-core" cx="24" cy="26" r="2.7"></circle>
    </svg>
  </div>
  <div><span>CONSUMER HIVE</span><strong>C Hive Sage</strong><small>指标顾问</small></div>
</div>
```

欢迎文案使用：

```html
<div class="welcome-kicker">CONSUMER HIVE INTELLIGENCE</div>
<h1>让每个指标，<span>都有据可循。</span></h1>
<p class="welcome-copy">请基于所选的报表类型进行对应报表相关指标的询问。</p>
```

CSS 必须包含：

```css
.north-star { animation: northStarTwinkle 3.6s ease-in-out infinite; }
.new-chat { border-radius: 15px; }
.report-control { border-radius: 18px; }
.composer { border-radius: 17px; }
@media (prefers-reduced-motion: reduce) {
  .north-star, .star-halo, .spark-rays { animation: none; }
}
```

删除所有用户可见的 `prototype-*`、`simulation-note` 和相关文案，使用中性边界提示：`回答基于已审核知识内容，请结合正式业务口径使用`。

- [ ] **Step 4: 运行静态测试并确认通过**

Run:

```bash
python3 verify_web_prototype.py
python3 verify_final_review_regressions.py
```

Expected: 两项均输出 `PASS`。

- [ ] **Step 5: 提交品牌外壳**

```bash
git add index.html verify_web_prototype.py verify_final_review_regressions.py
git commit -m "feat: redesign Consumer Hive premium workspace"
```

---

### Task 2: 实现定制报表菜单和知识依据交互

**Files:**
- Modify: `verify_web_runtime.html`
- Modify: `verify_requirements_sync.py`
- Modify: `index.html`

**Interfaces:**
- Consumes: `reportConfigs`, `currentSnapshot()`, `renderAnswer(response, snapshot)`, `toggleCitation(button)`。
- Produces: `openReportMenu() -> void`、`closeReportMenu({restoreFocus?: boolean}) -> void`、`applyReportSelection(reportKey: string) -> void`、`handleReportMenuKeydown(event: KeyboardEvent) -> void`。

- [ ] **Step 1: 添加失败的浏览器与需求同步测试**

在 `verify_web_runtime.html` 新增：

```javascript
test('custom report menu and context synchronization', async (win, doc) => {
  const trigger = doc.getElementById('reportTrigger');
  trigger.click();
  assert(trigger.getAttribute('aria-expanded') === 'true' && !doc.getElementById('reportMenu').hidden, 'menu did not open');
  doc.querySelector('[data-report-option="product"]').click();
  assert(doc.getElementById('reportTitle').textContent === 'Product', 'report title did not update');
  assert(doc.getElementById('knowledgeLabel').textContent.includes('Product'), 'knowledge label did not update');
  assert(doc.getElementById('reportMenu').hidden, 'menu did not close after selection');
});
```

扩充现有 citation 测试，继续验证 `aria-controls`、唯一 ID、默认收起、两次点击开关和 snapshot 标题不漂移。

在 `verify_requirements_sync.py` 的 FR-RPT-01 映射中，将 `reportSelector` 替换为 `reportTrigger`、`reportMenu`，并要求函数：

```python
("openReportMenu", "closeReportMenu", "applyReportSelection", "handleReportMenuKeydown")
```

- [ ] **Step 2: 运行测试并确认失败**

Run:

```bash
python3 verify_requirements_sync.py
python3 verify_web_runtime.py
```

Expected: FAIL，提示定制菜单 DOM 或行为缺失。

- [ ] **Step 3: 实现定制 listbox 和统一报表切换入口**

HTML 使用：

```html
<button id="reportTrigger" type="button" aria-haspopup="listbox" aria-controls="reportMenu" aria-expanded="false">
  <span id="reportTriggerValue">Customer Type</span><span aria-hidden="true">⌄</span>
</button>
<div id="reportMenu" class="report-menu" role="listbox" aria-label="选择报表" hidden>
  <button type="button" role="option" aria-selected="true" data-report-option="customerType">Customer Type</button>
  <button type="button" role="option" aria-selected="false" data-report-option="product">Product</button>
  <button type="button" role="option" aria-selected="false" data-report-option="memberTier">Member Tier</button>
  <button type="button" role="option" aria-selected="false" data-report-option="binding">Binding</button>
  <button type="button" role="option" aria-selected="false" data-report-option="nps">NPS</button>
</div>
```

JavaScript 统一使用：

```javascript
function applyReportSelection(reportKey) {
  if (!reportConfigs[reportKey]) return;
  appState.reportKey = reportKey;
  updateReportContext();
  renderQuickQuestions();
  closeReportMenu({ restoreFocus: true });
}

function handleReportMenuKeydown(event) {
  if (event.key === 'Escape') closeReportMenu({ restoreFocus: true });
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') moveReportOptionFocus(event.key === 'ArrowDown' ? 1 : -1);
}
```

跨报表推荐卡也必须调用 `applyReportSelection(reportKey)`，不能再写入原生 select 的 `.value`。

- [ ] **Step 4: 保留并美化知识依据开关**

正常回答输出：

```html
<button class="citation-toggle" type="button" aria-expanded="false" aria-controls="${citationId}">
  查看知识依据 <span class="citation-chevron" aria-hidden="true">⌄</span>
</button>
<div class="citations" id="${citationId}" hidden>...</div>
```

`toggleCitation(button)` 继续同步 `.open`、`hidden` 和 `aria-expanded`，并让 `.citation-chevron` 通过父按钮状态旋转。

- [ ] **Step 5: 运行需求与浏览器测试并确认通过**

Run:

```bash
python3 verify_requirements_sync.py
python3 verify_web_runtime.py
```

Expected: 两项均输出 `PASS`，浏览器用例全部通过。

- [ ] **Step 6: 提交交互变更**

```bash
git add index.html verify_web_runtime.html verify_requirements_sync.py
git commit -m "feat: add governed report picker and evidence disclosure"
```

---

### Task 3: 同步需求、设计、README 和变更记录

**Files:**
- Modify: `web版report_ai需求文档.md`
- Modify: `docs/2026-09-20-c-hive-sage-web-design.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `verify_requirements_sync.py`

**Interfaces:**
- Consumes: Task 1 与 Task 2 的最终 DOM、函数名和用户文案。
- Produces: 完整的 requirement-to-code mapping 和 V1.1 变更记录。

- [ ] **Step 1: 添加失败的文档同步断言**

在 `verify_requirements_sync.py` 要求需求文档包含：

```python
for token in (
    "Consumer Hive",
    "八角北极星",
    "定制报表菜单",
    "openReportMenu",
    "applyReportSelection",
    "查看知识依据",
    "用户可见页面不得出现",
):
    if token not in requirements:
        return fail(f"requirements missing premium UI contract: {token}")
```

- [ ] **Step 2: 运行同步测试并确认失败**

Run: `python3 verify_requirements_sync.py`  
Expected: FAIL，提示需求文档缺少新版 UI 合同。

- [ ] **Step 3: 更新正式文档**

`web版report_ai需求文档.md` 增加 V1.1 章节，明确品牌、布局、Logo、定制菜单、文案、知识依据和响应式验收；保留“未接入真实后台”的技术边界，但不把该边界作为用户界面标签。

`docs/2026-09-20-c-hive-sage-web-design.md` 更新为已批准视觉方向，并链接：

```markdown
详细设计决策见 `docs/superpowers/specs/2026-09-21-consumer-hive-premium-ui-design.md`。
```

`README.md` 将产品描述改为 Consumer Hive 的独立指标知识工作台，更新 DOM 与本地验证说明。

`CHANGELOG.md` 新增：

```markdown
## 2026-09-21 · Premium Web UI

- 建立 Consumer Hive / C Hive Sage / 指标顾问三级品牌层级。
- 上线深石墨与暖象牙的高端黑金工作台、八角北极星及低频动效。
- 使用定制圆角 listbox 替换原生报表下拉弹层。
- 将知识依据升级为可访问的展开与收起交互。
- 清理用户可见的“原型”和“模拟”类文案，并保留真实技术边界说明。
```

- [ ] **Step 4: 运行同步测试并确认通过**

Run:

```bash
python3 verify_requirements_sync.py
python3 verify_web_prototype.py
```

Expected: 两项均输出 `PASS`。

- [ ] **Step 5: 提交文档同步**

```bash
git add web版report_ai需求文档.md docs/2026-09-20-c-hive-sage-web-design.md README.md CHANGELOG.md verify_requirements_sync.py
git commit -m "docs: synchronize premium web UI requirements"
```

---

### Task 4: 完整验证、输出同步与 GitHub 发布

**Files:**
- Modify: `verify_final_review_regressions.py`
- Modify: `verify_web_runtime.html`
- Modify: `verify_web_runtime.py`
- Copy after verification: `index.html` to `/Users/yanjia/Documents/AI_2026/report_ai/crm_report_ai_web/index.html`（仓库内即正式交付文件）

**Interfaces:**
- Consumes: 全部静态与运行时契约。
- Produces: 可复现的 PASS 结果、最终 release commit 和与 `origin/main` 一致的 GitHub 状态。

- [ ] **Step 1: 补齐最终回归覆盖**

静态回归检查：

```python
check("data-report-option" in index, "custom report options are missing")
check("handleReportMenuKeydown" in index, "report menu keyboard support is missing")
check(not any(token in visible_html for token in VISIBLE_BANNED_COPY), "banned visible copy remains")
check("prefers-reduced-motion: reduce" in index, "reduced motion contract is missing")
```

浏览器回归检查：菜单打开、选择 Product、上下文同步、Escape 关闭、外部点击关闭、知识依据展开收起、新建对话恢复、移动侧栏焦点链和隔离服务 `.git` 404。

- [ ] **Step 2: 执行完整验证**

Run:

```bash
python3 verify_web_prototype.py
python3 verify_requirements_sync.py
python3 verify_final_review_regressions.py
python3 verify_web_runtime.py
python3 -m py_compile verify_web_prototype.py verify_requirements_sync.py verify_final_review_regressions.py verify_web_runtime.py
git diff --check
```

Expected: 四类校验均 `PASS`，`py_compile` 和 `git diff --check` 无输出。

- [ ] **Step 3: 执行人工视觉验收**

通过本地同源服务检查：

- 桌面默认视口：深色侧栏、暖象牙主区、品牌层级与八角北极星。
- `842×837`：定制菜单不与后续内容串层，展开菜单为圆角无边线。
- `659×837`：欢迎说明保持单行，输入框不溢出；移动侧栏按设计工作。
- 点击推荐问题后，“查看知识依据”可展开和收起。
- 控制台无 error。

- [ ] **Step 4: 创建最终发布提交**

```bash
git add index.html verify_web_runtime.html verify_web_runtime.py verify_final_review_regressions.py
git commit -m "test: validate premium Consumer Hive web release"
```

- [ ] **Step 5: 设置 GitHub 远端并推送**

```bash
git remote set-url origin git@github.com:jelenajy/crm_report_ai_web.git
git push origin main
git fetch origin main
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)"
git status --short --branch
```

Expected: push 成功；HEAD 与 `origin/main` 相同；工作树 clean。

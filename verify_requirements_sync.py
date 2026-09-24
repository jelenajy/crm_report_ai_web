#!/usr/bin/env python3
"""Validate the web requirement-to-code contract, including premium UI scope."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
REQUIREMENTS = ROOT / "web版report_ai需求文档.md"

FORBIDDEN_REQUIREMENT_TERMS = (
    "C Hive Lens", "Power BI 浮窗", "截图", "iframe",
)

PREMIUM_REQUIREMENT_TOKENS = (
    "Consumer Hive",
    "八角北极星",
    "定制报表菜单",
    "openReportMenu",
    "applyReportSelection",
    "查看知识依据",
    "用户可见页面不得出现",
)

REQUIREMENT_CONTRACTS = {
    "FR-RPT-01": {
        "functions": (
            "handleReportChange", "renderQuickQuestions", "openReportMenu", "closeReportMenu",
            "applyReportSelection", "handleReportMenuKeydown",
        ),
        "dom_ids": ("reportTrigger", "reportMenu", "reportTitle", "knowledgeLabel", "knowledgeStatus", "quickQuestions"),
        "behavior": "five reports and ready/pending route updates",
    },
    "FR-RTE-01": {
        "functions": ("pickResponse", "findCrossReportRoute"), "dom_ids": (),
        "behavior": "pending reports route first and cross-report routes stay configuration-driven",
    },
    "FR-ANS-01": {
        "functions": ("renderAnswer", "toggleCitation"), "dom_ids": (),
        "behavior": "four response routes and collapsible citations",
    },
    "FR-SNP-01": {
        "functions": ("currentSnapshot", "citationLabel"), "dom_ids": (),
        "behavior": "question-time snapshot is retained in every citation label",
    },
    "FR-INP-01": {
        "functions": ("sendQuestion", "showToast"),
        "dom_ids": ("questionInput", "sendBtn", "newChatBtn", "toast"),
        "events": ("#questionInput keydown: IME/Enter",),
        "behavior": "IME-safe keyboard input, 500-character guard, explicit loading state, and timed toast",
    },
    "FR-ERR-01": {
        "functions": ("renderError", "setInteractionBusy"), "dom_ids": (),
        "behavior": "answer failures render an alert and finally restore all interaction state",
    },
    "FR-SES-01": {
        "functions": ("startNewChat",), "dom_ids": ("welcomeState",),
        "behavior": "new chat restores the welcome state without changing the route",
    },
    "FR-SIM-01": {
        "functions": ("submitFeedback", "setConversationTitle", "createTicket"),
        "dom_ids": ("recentConversation",),
        "behavior": "ticket, feedback, history, and navigation remain simulated",
    },
    "FR-A11Y-01": {
        "functions": (
            "openSidebar", "closeSidebar", "syncSidebarAccessibility",
            "syncSidebarOverlay", "renderFeedback",
        ),
        "dom_ids": ("mobileMenuBtn", "sidebarOverlay"),
        "events": ("document keydown: Escape", "#sidebarOverlay click"),
        "behavior": "mobile sidebar keeps aria-expanded, aria-hidden, and inert synchronized",
    },
}

FUNCTION_REQUIREMENT_IDS = {
    function_name: requirement_id
    for requirement_id, contract in REQUIREMENT_CONTRACTS.items()
    for function_name in contract["functions"]
}
DOM_REQUIREMENT_IDS = {
    element_id: requirement_id
    for requirement_id, contract in REQUIREMENT_CONTRACTS.items()
    for element_id in contract["dom_ids"]
}
EVENT_REQUIREMENT_IDS = {
    event_name: requirement_id
    for requirement_id, contract in REQUIREMENT_CONTRACTS.items()
    for event_name in contract.get("events", ())
}


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def script_from(index: str) -> str:
    match = re.search(r"<script>(?P<script>.*?)</script>", index, re.DOTALL)
    if not match:
        raise ValueError("inline script is missing")
    return match.group("script")


def function_body(script: str, name: str) -> str:
    declaration = re.search(rf"\bfunction\s+{re.escape(name)}\b", script)
    if not declaration:
        raise ValueError(f"function {name} is missing")
    opening_brace = script.find("{", declaration.end())
    if opening_brace == -1:
        raise ValueError(f"function {name} has no body")
    depth = 0
    for position in range(opening_brace, len(script)):
        if script[position] == "{":
            depth += 1
        elif script[position] == "}":
            depth -= 1
            if depth == 0:
                return script[declaration.start() : position + 1]
    raise ValueError(f"function {name} has an unclosed body")


def contains_all(value: str, *needles: str) -> bool:
    return all(needle in value for needle in needles)


def has_report_config(script: str, key: str, name: str, status: str) -> bool:
    config = re.search(
        rf"^\s*{re.escape(key)}\s*:\s*\{{(?P<body>.*?)^\s*\}}(?:,|;)",
        script,
        re.DOTALL | re.MULTILINE,
    )
    return bool(config and contains_all(
        config.group("body"),
        f"name: '{name}'",
        f"status: '{status}'",
        "knowledgePackageName:",
        "owner:",
        "routePatterns:",
        "questions:",
    ))


def documented_mapping(requirements: str, evidence: str, requirement_id: str) -> bool:
    return bool(re.search(
        rf"^\|\s*`?{re.escape(evidence)}`?\s*\|\s*{re.escape(requirement_id)}\s*\|",
        requirements, re.MULTILINE,
    ))


def branch_body(source: str, start: str, end: str) -> str:
    start_at = source.find(start)
    end_at = source.find(end, start_at + len(start))
    if start_at == -1 or end_at == -1:
        raise ValueError(f"cannot isolate response branch: {start}")
    return source[start_at:end_at]


def check_source_contracts(index: str, script: str) -> str | None:
    report_states = (
        ("customer_type", "Customer Type", "ready"), ("product", "Product", "pending"),
        ("member_tier", "Member Tier", "pending"), ("binding", "Binding", "pending"),
        ("nps", "NPS", "pending"),
    )
    if not all(has_report_config(script, *state) for state in report_states):
        return "five report configurations must declare the ready/pending contract"

    apply_selection = function_body(script, "applyReportSelection")
    if not contains_all(
        apply_selection,
        "if (!reportConfigs[reportKey]) return",
        "appState.reportKey = reportKey",
        "updateReportContext()",
        "renderQuickQuestions()",
        "closeReportMenu({ restoreFocus: true })",
    ):
        return "applyReportSelection must be the unified report switching entry point"

    close_menu = function_body(script, "closeReportMenu")
    if not contains_all(close_menu, "reportMenu.hidden = true", "aria-expanded', 'false'", "restoreFocus"):
        return "closeReportMenu must synchronize visibility and optionally restore trigger focus"

    report_change = function_body(script, "updateReportContext")
    if not contains_all(
        report_change,
        "config.status === 'pending'",
        "document.getElementById('reportTitle').textContent",
        "document.getElementById('knowledgeLabel').textContent",
        "document.getElementById('knowledgeStatus')",
        "历史回答保持原报表快照",
    ):
        return "updateReportContext must update route state while preserving historical snapshots"

    routing = function_body(script, "pickResponse")
    pending_guard = routing.find("if (config.status === 'pending')")
    deterministic_answer = routing.find("knowledgeResponses.purchaseFrequency")
    if pending_guard == -1 or deterministic_answer == -1 or pending_guard > deterministic_answer:
        return "pickResponse must route pending reports before deterministic answers"
    pending_block = routing[pending_guard:deterministic_answer]
    if not contains_all(pending_block, "status: 'no-answer'", "relevanceStatus: 'in_scope_unanswered'"):
        return "pending reports must return the knowledge-missing response shape"

    cross_route = function_body(script, "findCrossReportRoute")
    if not contains_all(
        cross_route,
        "Object.entries(reportConfigs)",
        "config.questions.includes(question)",
        "config.routePatterns.some",
        "targetReport: config.name",
        "targetKey",
    ):
        return "cross-report routing must use each report's questions and routePatterns"
    if "findCrossReportRoute(question, reportKey)" not in routing:
        return "pickResponse must delegate cross-report matching to the report configuration"

    answer = function_body(script, "renderAnswer")
    no_answer = branch_body(
        answer,
        "if (response.relevanceStatus === 'in_scope_unanswered') {",
        "} else if (response.relevanceStatus === 'cross_report') {",
    )
    cross_report = branch_body(
        answer,
        "} else if (response.relevanceStatus === 'cross_report') {",
        "} else if (response.relevanceStatus === 'out_of_scope') {",
    )
    out_of_scope = branch_body(
        answer,
        "} else if (response.relevanceStatus === 'out_of_scope') {",
        "} else {",
    )
    normal_answer = answer[answer.find("} else {", answer.find("out_of_scope")) :]
    if not contains_all(
        normal_answer,
        '<div class="answer-title">结论</div>',
        "<h3>计算口径</h3>",
        "<h3>说明</h3>",
        "提问时所选报表：",
        "citation-toggle",
        "citation-chevron",
        'aria-controls="${citationId}"',
        'id="${citationId}"',
        "renderSuggestions(response.suggestions)",
        "renderFeedback()",
    ):
        return "normal answers must render conclusion, formula, rules, snapshot, citation, follow-ups, and feedback"
    if not contains_all(no_answer, "知识待补充", "已生成待补充问题记录", "问题编号 ${ticket}"):
        return "knowledge-missing answers must render submission confirmation and ticket"
    if not contains_all(cross_report, "跨报表提示", "report-recommendation", "推荐报表：", "data-report-target"):
        return "cross-report answers must render a report recommendation card"
    if not contains_all(out_of_scope, "当前知识范围", "问题范围提示", "scope-guide", "可以这样问我"):
        return "out-of-scope answers must render the scope guide without a ticket"

    snapshot = function_body(script, "currentSnapshot")
    send = function_body(script, "sendQuestion")
    citation = function_body(script, "citationLabel")
    if not contains_all(snapshot, "key: appState.reportKey", "name: config.name", "knowledgePackageName"):
        return "currentSnapshot must capture the report route at question time"
    if not re.search(r"const snapshot = currentSnapshot\(\);.*?renderAnswer\(pickResponse\(text, snapshot\.key\), snapshot\);", send, re.DOTALL):
        return "sendQuestion must pass one captured snapshot to routing and rendering"
    if not re.search(r"return\s+`\$\{snapshot\.name\}\s*·\s*\$\{String\(response\.citation\)\}`", citation):
        return "citationLabel must prefix every citation with the captured report name"

    if not re.search(r"<textarea[^>]+id=\"questionInput\"[^>]+maxlength=\"500\"", index):
        return "questionInput must be a 500-character textarea"
    if not contains_all(send, ".trim().slice(0, 500)", "appState.isTyping", "setInteractionBusy(true)", "}, 650);"):
        return "sendQuestion must enforce 500 characters, prevent duplicates, and use the 650ms demo delay"
    if not re.search(
        r"event\.isComposing\s*\|\|\s*event\.keyCode\s*===\s*229.*?"
        r"event\.key\s*===\s*'Enter'.*?!event\.shiftKey.*?!isComposing",
        script,
        re.DOTALL,
    ):
        return "Enter must send while Shift+Enter and IME composition remain available for input"
    if not re.search(r"setTimeout\([^;]+,\s*1800\);", function_body(script, "showToast")):
        return "showToast must clear after 1800ms"

    render_error = function_body(script, "renderError")
    busy_state = function_body(script, "setInteractionBusy")
    if not contains_all(send, "try {", "catch (error)", "renderError(error, snapshot)", "finally {", "setInteractionBusy(false)"):
        return "sendQuestion must render failures and restore interaction from finally"
    if not contains_all(render_error, "error-message", "setAttribute('role', 'alert')", "暂时无法生成回答"):
        return "renderError must add a visible accessible failure message"
    if not contains_all(busy_state, "appState.isTyping = isBusy", "sendBtn.disabled = isBusy", "newChatBtn.disabled = isBusy"):
        return "setInteractionBusy must synchronize typing, send, and new-chat state"

    open_sidebar = function_body(script, "openSidebar")
    close_sidebar = function_body(script, "closeSidebar")
    sync_sidebar = function_body(script, "syncSidebarAccessibility")
    sync_overlay = function_body(script, "syncSidebarOverlay")
    if not contains_all(open_sidebar, "aria-expanded', 'true'", "aria-hidden', 'false'", "removeAttribute('inert')"):
        return "openSidebar must expose the mobile sidebar to assistive technology"
    if not contains_all(close_sidebar, "aria-expanded', 'false'", "aria-hidden', 'true'", "setAttribute('inert', '')"):
        return "closeSidebar must hide and inert the mobile sidebar"
    if not contains_all(sync_sidebar, "max-width: 767px", "setAttribute('inert', '')", "removeAttribute('inert')"):
        return "syncSidebarAccessibility must keep narrow-screen sidebar state synchronized"
    if not contains_all(open_sidebar, "appState.lastSidebarTrigger = document.activeElement", "newChatBtn.focus()"):
        return "openSidebar must move focus into the mobile sidebar"
    if not contains_all(close_sidebar, "appState.lastSidebarTrigger.focus()", "clearTimeout(appState.sidebarFocusTimer)", "syncSidebarOverlay()"):
        return "closeSidebar must cancel delayed focus, restore focus, and hide the overlay"
    if not contains_all(sync_overlay, "overlay.hidden", "aria-hidden", "overlay.tabIndex"):
        return "syncSidebarOverlay must update visual, accessibility, and tab-order state together"
    if not re.search(r'id="sidebarOverlay"[^>]+aria-hidden="true"[^>]+hidden', index):
        return "the closed sidebar overlay must start hidden from assistive technology"
    if not re.search(r"document\.getElementById\('sidebarOverlay'\)\.addEventListener\('click',\s*closeSidebar\)", script):
        return "sidebar overlay must be bound to closeSidebar"
    if not re.search(r"document\.addEventListener\('keydown'.*?event\.key !== 'Escape'.*?appState\.sidebarOpen.*?closeSidebar\(\)", script, re.DOTALL):
        return "Escape keydown must close an open mobile sidebar"

    feedback = function_body(script, "submitFeedback")
    feedback_markup = function_body(script, "renderFeedback")
    title = function_body(script, "setConversationTitle")
    ticket = function_body(script, "createTicket")
    if not contains_all(feedback, "感谢反馈", "反馈已记录"):
        return "feedback must confirm both available choices"
    if not contains_all(feedback_markup, 'aria-pressed="false"', 'role="group"') or "setAttribute('aria-pressed'" not in feedback:
        return "feedback buttons must expose an exclusive aria-pressed state"
    if "当前会话 · 刷新后重置" not in title or "KQ-20260920-" not in ticket:
        return "history and ticket behavior must remain page-local"
    if any(term in index for term in ("原型", "演示", "模拟效果", "模拟提交", "模拟导航")):
        return "visible HTML must not contain prototype or simulation wording"
    if "applyReportSelection(reportButton.dataset.reportTarget)" not in script or "reportSelector.value" in script:
        return "cross-report recommendations must use the unified report switching entry point"

    function_evidence = {
        "renderQuickQuestions": ("config.questions.map", "quickQuestions').innerHTML"),
        "toggleCitation": ("button.getAttribute('aria-controls')", "citation.hidden", "button.setAttribute('aria-expanded'"),
        "startNewChat": ("messageList.replaceChildren()", "welcomeState.hidden = false", "当前报表选择保持不变"),
    }
    for function_name, expected_evidence in function_evidence.items():
        if not contains_all(function_body(script, function_name), *expected_evidence):
            return f"{function_name} is mapped but does not implement its requirement behavior"
    return None


def main() -> int:
    if not REQUIREMENTS.exists():
        return fail("web版report_ai需求文档.md does not exist")
    if not INDEX.exists():
        return fail("index.html does not exist")
    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    try:
        script = script_from(index)
        source_failure = check_source_contracts(index, script)
    except ValueError as error:
        return fail(str(error))
    if source_failure:
        return fail(source_failure)

    if "C Hive Sage｜指标顾问" not in requirements or "V1.0 Web" not in requirements:
        return fail("requirements are missing the product and version identity")
    for token in PREMIUM_REQUIREMENT_TOKENS:
        if token not in requirements:
            return fail(f"requirements missing premium UI contract: {token}")
    forbidden_terms = [item for item in FORBIDDEN_REQUIREMENT_TERMS if item in requirements]
    if forbidden_terms:
        return fail("requirements contain forbidden legacy or production wording: " + ", ".join(forbidden_terms))
    for requirement_id, contract in REQUIREMENT_CONTRACTS.items():
        if not re.search(rf"^###\s+{re.escape(requirement_id)}\b", requirements, re.MULTILINE):
            return fail(f"requirements missing structured requirement: {requirement_id}")
    for function_name, requirement_id in FUNCTION_REQUIREMENT_IDS.items():
        if not documented_mapping(requirements, function_name, requirement_id):
            return fail(f"requirements mapping missing {function_name} ↔ {requirement_id}")
    for element_id, requirement_id in DOM_REQUIREMENT_IDS.items():
        if not re.search(rf"\bid\s*=\s*['\"]{re.escape(element_id)}['\"]", index):
            return fail(f"index.html missing mapped DOM id: {element_id}")
        if not documented_mapping(requirements, f"#{element_id}", requirement_id):
            return fail(f"requirements mapping missing #{element_id} ↔ {requirement_id}")
    for event_name, requirement_id in EVENT_REQUIREMENT_IDS.items():
        if not documented_mapping(requirements, event_name, requirement_id):
            return fail(f"requirements mapping missing {event_name} ↔ {requirement_id}")
    print("PASS: Web requirements and prototype behavior are structurally synchronized")
    return 0


if __name__ == "__main__":
    sys.exit(main())

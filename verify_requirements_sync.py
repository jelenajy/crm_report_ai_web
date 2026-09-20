#!/usr/bin/env python3
"""Validate the V1.0 requirement-to-prototype contract, not just keywords."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
REQUIREMENTS = ROOT / "web版report_ai需求文档.md"

FORBIDDEN_REQUIREMENT_TERMS = (
    "C Hive Lens", "Power BI 浮窗", "截图", "iframe", "真实后台",
)

REQUIREMENT_CONTRACTS = {
    "FR-RPT-01": {
        "functions": ("handleReportChange", "renderQuickQuestions"),
        "dom_ids": ("reportSelector", "knowledgeLabel"),
        "behavior": "five reports and ready/pending route updates",
    },
    "FR-RTE-01": {
        "functions": ("pickResponse",), "dom_ids": (),
        "behavior": "pending reports route before deterministic answers",
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
        "dom_ids": ("questionInput", "sendBtn", "toast"),
        "behavior": "keyboard input, 500-character guard, loading, and timed toast",
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
        "functions": ("openSidebar", "closeSidebar", "syncSidebarAccessibility"),
        "dom_ids": ("mobileMenuBtn", "sidebarOverlay"),
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
    ))


def documented_mapping(requirements: str, evidence: str, requirement_id: str) -> bool:
    return bool(re.search(
        rf"^\|\s*`?{re.escape(evidence)}`?\s*\|\s*{re.escape(requirement_id)}\s*\|",
        requirements, re.MULTILINE,
    ))


def check_source_contracts(index: str, script: str) -> str | None:
    report_states = (
        ("customer_type", "Customer Type", "ready"), ("product", "Product", "pending"),
        ("member_tier", "Member Tier", "pending"), ("binding", "Binding", "pending"),
        ("nps", "NPS", "pending"),
    )
    if not all(has_report_config(script, *state) for state in report_states):
        return "five report configurations must declare the ready/pending contract"

    report_change = function_body(script, "handleReportChange")
    if not contains_all(report_change, "config.status === 'pending'", "knowledgeLabel').textContent = config.knowledgePackageName", "renderQuickQuestions()", "历史回答保持原报表快照"):
        return "handleReportChange must update route state while preserving historical snapshots"

    routing = function_body(script, "pickResponse")
    pending_guard = routing.find("if (config.status === 'pending')")
    deterministic_answer = routing.find("knowledgeResponses.purchaseFrequency")
    if pending_guard == -1 or deterministic_answer == -1 or pending_guard > deterministic_answer:
        return "pickResponse must route pending reports before deterministic answers"
    pending_block = routing[pending_guard:deterministic_answer]
    if not contains_all(pending_block, "status: 'no-answer'", "relevanceStatus: 'in_scope_unanswered'"):
        return "pending reports must return the knowledge-missing response shape"

    answer = function_body(script, "renderAnswer")
    if not contains_all(answer, "response.relevanceStatus === 'in_scope_unanswered'", "response.relevanceStatus === 'cross_report'", "response.relevanceStatus === 'out_of_scope'", "else {"):
        return "renderAnswer must render all four response routes"

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
    if not contains_all(send, ".trim().slice(0, 500)", "appState.isTyping", "sendBtn.disabled = true", "}, 650);"):
        return "sendQuestion must enforce 500 characters, prevent duplicates, and use the 650ms demo delay"
    if not re.search(r"event\.key === 'Enter'\s*&&\s*!event\.shiftKey", script):
        return "Enter must send while Shift+Enter remains available for multiline input"
    if not re.search(r"setTimeout\([^;]+,\s*1800\);", function_body(script, "showToast")):
        return "showToast must clear after 1800ms"

    open_sidebar = function_body(script, "openSidebar")
    close_sidebar = function_body(script, "closeSidebar")
    sync_sidebar = function_body(script, "syncSidebarAccessibility")
    if not contains_all(open_sidebar, "aria-expanded', 'true'", "aria-hidden', 'false'", "removeAttribute('inert')"):
        return "openSidebar must expose the mobile sidebar to assistive technology"
    if not contains_all(close_sidebar, "aria-expanded', 'false'", "aria-hidden', 'true'", "setAttribute('inert', '')"):
        return "closeSidebar must hide and inert the mobile sidebar"
    if not contains_all(sync_sidebar, "max-width: 767px", "setAttribute('inert', '')", "removeAttribute('inert')"):
        return "syncSidebarAccessibility must keep narrow-screen sidebar state synchronized"

    feedback = function_body(script, "submitFeedback")
    title = function_body(script, "setConversationTitle")
    ticket = function_body(script, "createTicket")
    if not contains_all(feedback, "模拟标记", "模拟记录"):
        return "feedback must remain explicitly simulated"
    if "当前会话 · 模拟效果" not in title or "KQ-20260920-" not in ticket:
        return "history and ticket behavior must remain explicitly simulated"
    if "模拟导航完成" not in script or "历史会话、导航、问题提交与反馈均为模拟效果" not in index:
        return "navigation, tickets, history, and feedback must all be marked simulated"

    function_evidence = {
        "renderQuickQuestions": ("config.questions.map", "quickQuestions').innerHTML"),
        "toggleCitation": ("citation.classList.toggle", "button.setAttribute('aria-expanded'"),
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
    print("PASS: Web requirements and prototype behavior are structurally synchronized")
    return 0


if __name__ == "__main__":
    sys.exit(main())

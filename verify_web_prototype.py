#!/usr/bin/env python3
"""Dependency-free structural checks for the C Hive Sage Web prototype."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"

REQUIRED_IDS = (
    "appShell",
    "sidebar",
    "newChatBtn",
    "reportTrigger",
    "reportMenu",
    "knowledgeLabel",
    "conversation",
    "welcomeState",
    "quickQuestions",
    "questionInput",
    "sendBtn",
    "mobileMenuBtn",
    "sidebarOverlay",
)

REQUIRED_FUNCTIONS = (
    "handleReportChange",
    "renderQuickQuestions",
    "sendQuestion",
    "setInteractionBusy",
    "pickResponse",
    "findCrossReportRoute",
    "renderAnswer",
    "renderError",
    "renderFeedback",
    "citationLabel",
    "toggleCitation",
    "submitFeedback",
    "startNewChat",
    "openSidebar",
    "closeSidebar",
    "syncSidebarOverlay",
    "openReportMenu",
    "closeReportMenu",
    "applyReportSelection",
    "handleReportMenuKeydown",
    "handleViewportResize",
    "showToast",
)

VISIBLE_BANNED_COPY = ("原型演示", "模拟效果", "模拟提交", "模拟导航")


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def has_function(source: str, function_name: str) -> bool:
    """Return whether source declares the name as a function or arrow function."""
    escaped_name = re.escape(function_name)
    patterns = (
        rf"\bfunction\s*\*?\s+{escaped_name}\s*\(",
        rf"\b(?:const|let|var)\s+{escaped_name}\s*=\s*"
        rf"(?:async\s+)?function\s*\*?\s*\(",
        rf"\b(?:const|let|var)\s+{escaped_name}\s*=\s*"
        rf"(?:async\s+)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>",
    )
    return any(re.search(pattern, source) for pattern in patterns)


def function_body(source: str, function_name: str) -> str:
    declaration = re.search(rf"\bfunction\s+{re.escape(function_name)}\b", source)
    if not declaration:
        return ""
    opening_brace = source.find("{", declaration.end())
    depth = 0
    for position in range(opening_brace, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[declaration.start() : position + 1]
    return ""


def main() -> int:
    if not INDEX.exists():
        return fail("index.html does not exist")

    source = INDEX.read_text(encoding="utf-8")
    missing_ids = [
        element_id
        for element_id in REQUIRED_IDS
        if not re.search(rf"\bid\s*=\s*['\"]{re.escape(element_id)}['\"]", source)
    ]
    if missing_ids:
        return fail("missing DOM ids: " + ", ".join(missing_ids))

    missing_functions = [
        function_name
        for function_name in REQUIRED_FUNCTIONS
        if not has_function(source, function_name)
    ]
    if missing_functions:
        return fail("missing functions: " + ", ".join(missing_functions))

    if "C Hive Sage｜指标顾问" not in source:
        return fail("missing product name: C Hive Sage｜指标顾问")

    for token in VISIBLE_BANNED_COPY:
        if token in source:
            return fail(f"visible prototype copy remains: {token}")

    if "原型" in source:
        return fail("visible prototype copy remains: 原型")

    for token in ("Consumer Hive", "C Hive Sage", "指标顾问", "CONSUMER HIVE INTELLIGENCE"):
        if token not in source:
            return fail(f"missing premium brand token: {token}")

    for token in ('class="hive-mark"', 'class="north-star"', 'id="reportMenu"', 'data-report-option'):
        if token not in source:
            return fail(f"missing premium UI contract: {token}")

    report_options = re.findall(r"<button\b[^>]*\bdata-report-option\s*=\s*['\"][^'\"]+['\"][^>]*>", source)
    if len(report_options) != 5 or any(not re.search(r"\btabindex\s*=\s*['\"]-1['\"]", option) for option in report_options):
        return fail("custom report options must be programmatically focusable, not independent tab stops")

    open_report_menu = function_body(source, "openReportMenu")
    if '[aria-selected="true"]' not in open_report_menu or ".focus()" not in open_report_menu:
        return fail("opening the report menu must focus the selected option")

    menu_keydown = function_body(source, "handleReportMenuKeydown")
    if not all(key in menu_keydown for key in ("ArrowDown", "ArrowUp", "Home", "End", "Enter", "' '", "Escape", "Tab")):
        return fail("custom report listbox must implement the complete keyboard model")
    if "closeReportMenu({ restoreFocus: true })" not in menu_keydown:
        return fail("Escape must close the report menu and restore trigger focus")
    tab_branch = re.search(r"event\.key\s*===\s*['\"]Tab['\"](?P<body>.*?)(?:return|\})", menu_keydown, re.DOTALL)
    if not tab_branch or "closeReportMenu()" not in tab_branch.group("body") or "preventDefault" in tab_branch.group("body"):
        return fail("Tab must close the report menu without trapping focus")

    viewport_resize = function_body(source, "handleViewportResize")
    if "closeReportMenu()" not in viewport_resize:
        return fail("responsive resize must close the custom report menu")

    if not re.search(
        r"return\s+`\$\{snapshot\.name\}\s*·\s*\$\{String\(response\.citation\)\}`",
        source,
    ):
        return fail("citation labels must include the question-time report snapshot")

    if source.count("routePatterns:") < 4 or "findCrossReportRoute(question, reportKey)" not in source:
        return fail("cross-report routing must be driven by every non-default report configuration")

    if not re.search(
        r"event\.isComposing\s*\|\|\s*event\.keyCode\s*===\s*229.*?"
        r"event\.key\s*===\s*'Enter'.*?!event\.shiftKey.*?!isComposing",
        source,
        re.DOTALL,
    ):
        return fail("Enter handling must protect active and legacy IME composition")

    if ".composer-box:focus-within" in source or not re.search(
        r"\.composer\s+textarea:focus-visible\s*\{[^}]*\boutline\s*:\s*none",
        source,
        re.DOTALL,
    ):
        return fail("the composer must not add stacked focus borders or textarea outlines")

    if not all(token in source for token in (
        "catch (error)", "finally {", "renderError(error, snapshot)", "setInteractionBusy(false)",
    )):
        return fail("answer failures must render an error and restore interaction from finally")

    if not all(token in source for token in (
        'aria-controls="${citationId}"', 'id="${citationId}"', 'aria-pressed="false"',
        "setAttribute('aria-pressed'", "overlay.hidden", "aria-hidden=\"true\"",
    )):
        return fail("citation, feedback, and overlay dynamic accessibility states are incomplete")

    report_option_handler = re.search(
        r"if\s*\(reportOption\)\s*\{(?P<body>.*?)\}\s*else\s+if",
        source,
        re.DOTALL,
    )
    report_option_body = report_option_handler.group("body") if report_option_handler else ""
    apply_report_selection = function_body(source, "applyReportSelection")
    if (
        "applyReportSelection(reportOption.dataset.reportOption)" not in report_option_body
        or "appState.reportKey = reportKey" not in apply_report_selection
        or "updateReportContext()" not in apply_report_selection
        or "renderQuickQuestions()" not in apply_report_selection
        or "closeReportMenu({ restoreFocus: true })" not in apply_report_selection
        or "reportSelector.value" in source
    ):
        return fail("custom report selection must use the unified report entry point")

    print("PASS: web prototype interaction contract exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())

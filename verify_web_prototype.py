#!/usr/bin/env python3
"""Contract checks for the C Hive Sage Web prototype.

The page is intentionally not part of Task 2.  Running this checker before the
page is implemented must fail, providing the red test for the next task.
"""

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
    "reportSelector",
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
    "pickResponse",
    "renderAnswer",
    "citationLabel",
    "toggleCitation",
    "submitFeedback",
    "startNewChat",
    "openSidebar",
    "closeSidebar",
    "showToast",
)


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

    if not re.search(
        r"return\s+`\$\{snapshot\.name\}\s*·\s*\$\{String\(response\.citation\)\}`",
        source,
    ):
        return fail("citation labels must include the question-time report snapshot")

    print("PASS: web prototype interaction contract exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())

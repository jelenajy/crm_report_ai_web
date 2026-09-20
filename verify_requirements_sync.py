#!/usr/bin/env python3
"""Two-way contract checks between the V1.0 Web requirements and prototype."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
REQUIREMENTS = ROOT / "web版report_ai需求文档.md"

CORE_FUNCTIONS = (
    "handleReportChange",
    "renderQuickQuestions",
    "sendQuestion",
    "pickResponse",
    "renderAnswer",
    "toggleCitation",
    "submitFeedback",
    "startNewChat",
    "openSidebar",
    "closeSidebar",
    "showToast",
)

DOCUMENT_CONTRACTS = (
    "C Hive Sage｜指标顾问",
    "V1.0 Web",
    "单一 Web 工作台",
    "Customer Type",
    "Product",
    "Member Tier",
    "Binding",
    "NPS",
    "四类分流",
    "正常回答",
    "知识缺失",
    "跨报表",
    "范围外",
    "Enter",
    "Shift+Enter",
    "500 字",
    "650ms",
    "响应式侧栏",
    "768px",
    "Escape",
    "模拟效果",
    "不输出确定性业务答案",
    "生产演进",
    "验收标准",
    "HTML 行为—需求映射",
)

SOURCE_CONTRACTS = (
    "const reportConfigs",
    "customer_type",
    "product",
    "member_tier",
    "binding",
    "nps",
    "maxlength=\"500\"",
    "window.setTimeout",
    "}, 650);",
    "max-width: 767px",
    "event.key === 'Escape'",
    "原型演示",
    "模拟效果",
)

FORBIDDEN_REQUIREMENT_TERMS = (
    "C Hive Lens",
    "Power BI 浮窗",
    "截图",
    "iframe",
    "真实后台",
)


def fail(message: str) -> int:
    print(f"FAIL: {message}")
    return 1


def has_function(source: str, function_name: str) -> bool:
    return bool(re.search(rf"\bfunction\s+{re.escape(function_name)}\s*\(", source))


def main() -> int:
    if not REQUIREMENTS.exists():
        return fail("web版report_ai需求文档.md does not exist")
    if not INDEX.exists():
        return fail("index.html does not exist")

    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    source = INDEX.read_text(encoding="utf-8")

    missing_document_contracts = [item for item in DOCUMENT_CONTRACTS if item not in requirements]
    if missing_document_contracts:
        return fail("requirements missing: " + ", ".join(missing_document_contracts))

    missing_mappings = [name for name in CORE_FUNCTIONS if name not in requirements]
    if missing_mappings:
        return fail("requirements mapping missing functions: " + ", ".join(missing_mappings))

    forbidden_terms = [item for item in FORBIDDEN_REQUIREMENT_TERMS if item in requirements]
    if forbidden_terms:
        return fail("requirements contain forbidden legacy or production wording: " + ", ".join(forbidden_terms))

    missing_source_contracts = [item for item in SOURCE_CONTRACTS if item not in source]
    if missing_source_contracts:
        return fail("index.html missing documented behavior: " + ", ".join(missing_source_contracts))

    missing_source_functions = [name for name in CORE_FUNCTIONS if not has_function(source, name)]
    if missing_source_functions:
        return fail("index.html missing mapped functions: " + ", ".join(missing_source_functions))

    print("PASS: Web requirements and prototype behavior are synchronized")
    return 0


if __name__ == "__main__":
    sys.exit(main())

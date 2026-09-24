#!/usr/bin/env python3
"""Regression contracts for the V1.0 final-review findings.

These checks deliberately complement, rather than replace, the browser runner in
``verify_web_runtime.html``.  They keep security/documentation guarantees and
critical implementation hooks reviewable from a dependency-free CLI command.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
OUTPUT_INDEX = ROOT / "outputs/crm_report_ai_web/index.html"
REQUIREMENTS = ROOT / "web版report_ai需求文档.md"
README = ROOT / "README.md"
RUNTIME_RUNNER = ROOT / "verify_web_runtime.html"
RUNTIME_DRIVER = ROOT / "verify_web_runtime.py"
VISIBLE_BANNED_COPY = ("原型演示", "原型", "模拟效果", "模拟提交", "模拟导航")


def function_body(source: str, name: str) -> str:
    declaration = re.search(rf"\bfunction\s+{re.escape(name)}\b", source)
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


def css_rule(source: str, selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>[^}}]+)\}}", source)
    return match.group("body") if match else ""


def block_body(source: str, header_pattern: str) -> str:
    header = re.search(header_pattern, source)
    if not header:
        return ""
    opening_brace = source.find("{", header.end())
    depth = 0
    for position in range(opening_brace, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[opening_brace + 1 : position]
    return ""


def selector_has_declaration(source: str, selector: str, declaration: str) -> bool:
    for match in re.finditer(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]*)\}", source):
        selectors = (item.strip() for item in match.group("selectors").split(","))
        if selector in selectors and declaration in re.sub(r"\s+", " ", match.group("body")):
            return True
    return False


def color_value(rule: str) -> str | None:
    match = re.search(r"\bcolor\s*:\s*(#[0-9a-fA-F]{6})\b", rule)
    return match.group(1) if match else None


def relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def main() -> int:
    files = (INDEX, OUTPUT_INDEX, REQUIREMENTS, README, RUNTIME_RUNNER, RUNTIME_DRIVER)
    missing = [str(path.relative_to(ROOT)) for path in files if not path.exists()]
    if missing:
        print("FAIL: missing regression inputs: " + ", ".join(missing))
        return 1

    index = INDEX.read_text(encoding="utf-8")
    requirements = REQUIREMENTS.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    runtime = RUNTIME_RUNNER.read_text(encoding="utf-8")
    runtime_driver = RUNTIME_DRIVER.read_text(encoding="utf-8")
    failures: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    routing = function_body(index, "findCrossReportRoute")
    pick_response = function_body(index, "pickResponse")
    check(index.count("routePatterns:") >= 4, "non-default reports need configured route patterns")
    check(
        all(token in routing for token in ("config.questions.includes(question)", "config.routePatterns.some", "targetKey")),
        "cross-report routing must be driven by each report's questions and patterns",
    )
    check("findCrossReportRoute(question, reportKey)" in pick_response, "pickResponse must use the configured cross-report router")

    keyboard_handler = re.search(
        r"questionInput\.addEventListener\('keydown',\s*\(event\)\s*=>\s*\{(?P<body>.*?)\n\s*\}\);",
        index,
        re.DOTALL,
    )
    keyboard_body = keyboard_handler.group("body") if keyboard_handler else ""
    check("event.isComposing" in keyboard_body, "Enter handler must ignore active IME composition")
    check("event.keyCode === 229" in keyboard_body, "Enter handler must include the legacy IME 229 guard")

    focus_rule = css_rule(index, ".composer-box:focus-within")
    textarea_rule = css_rule(index, ".composer textarea")
    check("outline:" in focus_rule and "outline: 0" not in focus_rule, "composer needs a visible focus-within outline")
    check("outline: 0" not in textarea_rule, "textarea rule must not erase its visible focus")

    check("3.6s" in css_rule(index, ".north-star"), "north-star twinkle duration must be 3.6s")
    check("border-radius: 50%" in css_rule(index, ".send-button") and "linear-gradient" in css_rule(index, ".send-button"), "send button must be circular with a warm gold gradient")
    check("fill: #171714" in css_rule(index, ".star-core") and "stroke: var(--gold-strong)" in css_rule(index, ".star-core"), "north-star core must be dark with a fine gold stroke")
    check(".star-rays" in index and "class=\"star-rays\"" in index, "north-star needs distinct short-lived glint rays")
    twinkle = block_body(index, r"@keyframes\s+northStarTwinkle")
    halo = block_body(index, r"@keyframes\s+starHalo")
    check("84%" in twinkle and "92%" in twinkle and "84%" in halo and "92%" in halo, "north-star and halo must rest until near the end of each cycle")
    check(all(token in index for token in ("Knowledge Governance", "Consumer Hive · CRM Analytics", "已审核指标知识体系")), "sidebar governance footer is incomplete")
    check(OUTPUT_INDEX.read_bytes() == INDEX.read_bytes(), "user-accessible output index must match root index byte for byte")
    check("outputs/crm_report_ai_web/index.html" in readme, "README must explain the synchronized output copy")
    check("本页标记为待补充" in index and "本页临时编号" in index, "unanswered copy must state the page-local boundary")
    check(not any(token in index for token in ("反馈给报表负责人", "反馈给负责人", "已生成待补充问题记录", "反馈已记录")), "visible copy must not imply external submission or persistent feedback")
    check("data-report-option" in index, "custom report options are missing")
    check("handleReportMenuKeydown" in index, "report menu keyboard support is missing")
    check(not any(token in index for token in VISIBLE_BANNED_COPY), "banned visible copy remains")
    check("prefers-reduced-motion: reduce" in index, "reduced motion contract is missing")
    reduced_motion = block_body(index, r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)")
    check(
        selector_has_declaration(reduced_motion, ".north-star", "animation: none"),
        "reduced-motion rule must explicitly disable north-star animation",
    )
    check("border-radius: 16px" in css_rule(index, ".report-menu"), "report menu must be rounded")
    check("border: 0" in css_rule(index, ".report-menu"), "report menu must not have an edge line")

    send_question = function_body(index, "sendQuestion")
    render_error = function_body(index, "renderError")
    busy_state = function_body(index, "setInteractionBusy")
    check(
        all(token in send_question for token in ("try {", "catch (error)", "finally {", "renderError(error, snapshot)", "setInteractionBusy(false)")),
        "sendQuestion must render an error and restore controls from finally",
    )
    has_alert_role = 'role="alert"' in render_error or "setAttribute('role', 'alert')" in render_error
    check(has_alert_role and "暂时无法" in render_error, "renderError must create an accessible visible error message")
    check("newChatBtn.disabled = isBusy" in busy_state, "new chat must be explicitly disabled while an answer is loading")

    answer = function_body(index, "renderAnswer")
    feedback = function_body(index, "renderFeedback")
    submit_feedback = function_body(index, "submitFeedback")
    check(
        all(token in answer for token in ("citationId", 'aria-controls="${citationId}"', 'id="${citationId}"')),
        "every citation toggle must control a unique citation region id",
    )
    check('aria-pressed="false"' in feedback, "feedback buttons must declare their initial pressed state")
    check("setAttribute('aria-pressed'" in submit_feedback, "feedback selection must update aria-pressed")
    check(
        bool(re.search(r'id="sidebarOverlay"[^>]+aria-hidden="true"[^>]+hidden', index)),
        "the closed sidebar overlay must start hidden and outside the accessibility tree",
    )
    sync_overlay = function_body(index, "syncSidebarOverlay")
    check(
        all(token in sync_overlay for token in ("overlay.hidden", "aria-hidden", "tabIndex")),
        "sidebar overlay visibility, ARIA state, and tab order must update together",
    )

    conversation_note_color = color_value(css_rule(index, ".conversation-note"))
    composer_color = color_value(css_rule(index, ".composer-meta"))
    check(
        bool(conversation_note_color) and contrast_ratio(conversation_note_color or "#000000", "#171714") >= 4.5,
        "10px sidebar conversation note must reach 4.5:1 contrast",
    )
    check(
        bool(composer_color) and contrast_ratio(composer_color or "#000000", "#f5f1e9") >= 4.5,
        "10px composer metadata must reach 4.5:1 contrast",
    )

    check("### FR-ERR-01" in requirements, "requirements need a structured error/recovery contract")
    check(
        all(marker in requirements for marker in ("| `renderError` | FR-ERR-01 |", "| `setInteractionBusy` | FR-ERR-01 |")),
        "requirements mapping must cover error rendering and state restoration",
    )

    check('PUBLIC_DIR="$(mktemp -d)"' in readme, "README must create a clean temporary public directory")
    check('cp index.html "$PUBLIC_DIR/"' in readme, "README must copy only the public entry point")
    check("--bind 127.0.0.1" in readme and '--directory "$PUBLIC_DIR"' in readme, "README server must bind loopback and serve the clean directory")
    check(not re.search(r"(?m)^python3 -m http\.server 8765\s*$", readme), "README must not recommend the unsafe repository-root server command")
    check("后续任务创建" not in readme, "README must not retain release placeholders")

    runtime_cases = (
        "configured cross-report questions",
        "IME composition Enter",
        "visible composer focus",
        "fault recovery finally",
        "citation and feedback ARIA",
        "overlay accessibility state",
        "report menu dismissal and keyboard selection",
        "new chat restores welcome and retains report",
        "runtime page errors",
    )
    check(all(case in runtime for case in runtime_cases), "browser runner must cover every dynamic final-review regression")
    check(
        all(marker in runtime_driver for marker in ('("127.0.0.1", 0)', "TemporaryDirectory", '"/.git/config"', "!= 404")),
        "browser driver must serve only a temporary loopback public root and probe repository paths",
    )

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("PASS: final-review regressions are covered by static and browser contracts")
    return 0


if __name__ == "__main__":
    sys.exit(main())

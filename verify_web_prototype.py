#!/usr/bin/env python3
"""Current UI contract after server-side knowledge routing replaced static answers."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
page = (root / 'index.html').read_text()
required = ('id="reportMenu"', 'id="knowledgeStatus"', 'id="questionInput"',
            'function applyReportSelection(', 'async function sendQuestion(',
            "fetch('/api/reports')", "fetch('/api/answer'", "知识包未接入",
            "setKnowledgeIndicator(packageStatus !== 'ready', packageStatus)", 'function renderError(')
for token in required:
    if token not in page:
        print(f'FAIL: missing current UI contract: {token}')
        sys.exit(1)
for token in ('const knowledgeResponses', '查看知识依据', 'routePatterns:', 'citation-toggle'):
    if token in page:
        print(f'FAIL: obsolete client-side knowledge content remains: {token}')
        sys.exit(1)
print('PASS: current web UI contract')

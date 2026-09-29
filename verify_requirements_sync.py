#!/usr/bin/env python3
"""Check the active V1.2 knowledge requirements against their implementation."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
requirements = (root / 'web版report_ai需求文档.md').read_text()
service = (root / 'knowledge_service.py').read_text()
server = (root / 'server.py').read_text()
page = (root / 'index.html').read_text()
checks = {
    'requirements addendum': '知识包维护补充（2026-09-26）' in requirements,
    'two search scopes': 'matched_rows(specialized, question)' in service and 'matched_rows(self.general, question)' in service,
    'no cross-package lookup': 'self.specialized.get(report_key, [])' in service,
    'private package directory': 'KNOWLEDGE_DIR' in server,
    'unconnected state': '知识包未接入' in page,
    'no document citation': '查看知识依据' not in page,
    'explicit no-answer': 'NO_ANSWER' in service,
}
failed = [name for name, passed in checks.items() if not passed]
if failed:
    print('FAIL: ' + ', '.join(failed))
    sys.exit(1)
print('PASS: active knowledge requirements synchronized')

#!/usr/bin/env python3
"""Release checks for the current private-knowledge implementation."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
page = (root / 'index.html').read_bytes()
copy = (root / 'outputs/crm_report_ai_web/index.html').read_bytes()
server = (root / 'server.py').read_text()
errors = []
if page != copy:
    errors.append('published page copy differs from source')
if b'const knowledgeResponses' in page or b'citation-toggle' in page:
    errors.append('source knowledge or citation UI is exposed')
if 'if self.path in ("/", "/index.html"):' not in server or 'self.send_bytes(404' not in server:
    errors.append('server allowlist is missing')
if errors:
    print('FAIL: ' + ', '.join(errors))
    sys.exit(1)
print('PASS: current release boundary checks')

#!/usr/bin/env python3
"""Fail when implementation files changed without refreshing the design record."""

import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent
DOC = ROOT / "docs/knowledge-system-design.md"
BEGIN = "<!-- SOURCE_HASHES_BEGIN -->"
END = "<!-- SOURCE_HASHES_END -->"


def sources():
    files = list(ROOT.glob("*.py")) + list((ROOT / "tests").glob("*.py"))
    files += list((ROOT / ".github/workflows").glob("*.yml"))
    files += [ROOT / "index.html", ROOT / "outputs/crm_report_ai_web/index.html"]
    return sorted(path for path in files if path.is_file())


def manifest():
    return "\n".join(f"{path.relative_to(ROOT)} {hashlib.sha256(path.read_bytes()).hexdigest()}"
                     for path in sources())


def main():
    content = DOC.read_text(encoding="utf-8")
    expected = f"{BEGIN}\n```text\n{manifest()}\n```\n{END}"
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if not pattern.search(content):
        raise SystemExit("Missing source hash section in design document")
    if "--update" in sys.argv[1:]:
        DOC.write_text(pattern.sub(expected, content), encoding="utf-8")
        print("Updated design source hashes; review the prose for semantic changes.")
    elif expected not in content:
        raise SystemExit("Design document is out of sync; update its explanations and run verify_design_sync.py --update")
    else:
        print("PASS: design source hashes match implementation")


if __name__ == "__main__":
    main()

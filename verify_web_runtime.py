#!/usr/bin/env python3
"""Run dependency-free browser regressions in an isolated local public root."""

from __future__ import annotations

import http.server
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PUBLIC_FILES = (ROOT / "index.html", ROOT / "verify_web_runtime.html")
FORBIDDEN_PATHS = ("/.git/config", "/README.md", "/docs/2026-09-20-c-hive-sage-web-design.md", "/verify_requirements_sync.py")


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        del format, args


def find_chrome() -> str | None:
    candidates = (
        os.environ.get("CHROME_BIN"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    )
    return next((candidate for candidate in candidates if candidate and Path(candidate).is_file()), None)


def request_status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def main() -> int:
    missing = [path.name for path in PUBLIC_FILES if not path.exists()]
    if missing:
        print("FAIL: missing browser regression inputs: " + ", ".join(missing))
        return 1

    chrome = find_chrome()
    if not chrome:
        print("FAIL: Chrome/Chromium not found; install it or set CHROME_BIN")
        return 1

    with tempfile.TemporaryDirectory(prefix="c-hive-sage-public-") as public_dir:
        for source in PUBLIC_FILES:
            shutil.copy2(source, Path(public_dir) / source.name)

        handler = lambda *args, **kwargs: QuietHandler(*args, directory=public_dir, **kwargs)
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            if request_status(base_url + "/") != 200:
                print("FAIL: isolated public root did not serve index.html")
                return 1
            exposed = [path for path in FORBIDDEN_PATHS if request_status(base_url + path) != 404]
            if exposed:
                print("FAIL: isolated public root exposed repository files: " + ", ".join(exposed))
                return 1

            command = [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--disable-background-networking",
                "--disable-extensions",
                "--incognito",
                "--no-first-run",
                "--no-default-browser-check",
                "--virtual-time-budget=5000",
                "--dump-dom",
                base_url + "/verify_web_runtime.html",
            ]
            result = subprocess.run(command, capture_output=True, text=True, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f"FAIL: browser regression runner could not complete: {error}")
            return 1
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    expected_markers = ('data-status="pass"', "PASS: 7/7 browser regressions")
    if result.returncode != 0 or not all(marker in result.stdout for marker in expected_markers):
        print(f"FAIL: browser regressions did not pass (Chrome exit {result.returncode})")
        summary_start = result.stdout.find('<p id="summary"')
        if summary_start != -1:
            print(result.stdout[summary_start : summary_start + 500])
        if result.stderr.strip():
            print(result.stderr.strip().splitlines()[-1])
        return 1
    print("PASS: 7/7 browser regressions and isolated-server boundary")
    return 0


if __name__ == "__main__":
    sys.exit(main())

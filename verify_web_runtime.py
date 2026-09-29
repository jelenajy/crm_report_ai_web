#!/usr/bin/env python3
"""Run the current page, API and private-file boundary in a local browser."""
import json
import shutil
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from server import make_handler

ROOT = Path(__file__).resolve().parent


def main():
    chrome = shutil.which('google-chrome') or shutil.which('chromium') or '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
    if not Path(chrome).is_file():
        print('FAIL: Chrome/Chromium not found')
        return 1
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(ROOT))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(base + '/api/reports', timeout=5) as response:
            statuses = json.load(response)
        if statuses['customer_type'] != 'ready' or statuses['member_tier'] != 'pending':
            raise AssertionError('report package states are wrong')
        request = Request(base + '/api/answer', method='POST',
                          data=json.dumps({'reportKey': 'customer_type', 'question': '购买频次如何计算？'}).encode(),
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=5) as response:
            answer = json.load(response)
        if answer.get('scope') != 'specialized':
            raise AssertionError('specialized package did not win')
        try:
            urlopen(base + '/README.md', timeout=5)
            raise AssertionError('repository file was exposed')
        except HTTPError as error:
            if error.code != 404:
                raise
        result = subprocess.run([chrome, '--headless=new', '--disable-gpu', '--no-first-run',
                                 '--disable-background-networking', '--virtual-time-budget=3000',
                                 '--dump-dom', base + '/'], capture_output=True, text=True, timeout=15)
        if result.returncode or 'id="knowledgeStatus">已接入</span>' not in result.stdout:
            raise AssertionError('browser did not display connected package state')
        if '查看知识依据' in result.stdout:
            raise AssertionError('citation UI was exposed')
    except (AssertionError, OSError, TimeoutError, URLError, subprocess.TimeoutExpired) as error:
        print(f'FAIL: {error}')
        return 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
    print('PASS: browser, API and private-file boundary')
    return 0


if __name__ == '__main__':
    sys.exit(main())

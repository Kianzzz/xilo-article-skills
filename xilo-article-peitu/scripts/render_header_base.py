#!/usr/bin/env python3
"""Render the date-header base PNG from assets/date-header.html with headless Chrome."""

import argparse
import base64
import functools
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "msedge", "chrome",
]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def find_browser():
    for name in [os.environ.get("CHROME")] + CANDIDATES:
        if name and (Path(name).is_file() or shutil.which(name)):
            return shutil.which(name) or name
    raise ValueError("No Chrome/Chromium/Edge found. Install one or set CHROME=/path/to/browser.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--lines", nargs=2, required=True, metavar=("LINE1", "LINE2"))
    parser.add_argument("--note", default="")
    parser.add_argument("--timezone", default="Asia/Shanghai")
    parser.add_argument("--masthead", help="Masthead text, if the template supports it.")
    parser.add_argument("--colors", help='JSON, e.g. {"main":"#14532D","accent":"#23834A","rule":"#B7E2C8"}')
    parser.add_argument("--scale", type=int, default=2)
    parser.add_argument("--template", type=Path, default=ROOT / "assets/date-header.html")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError("Output exists. Choose a new filename.")
        browser = find_browser()
        overrides = {"date": args.date, "timezone": args.timezone, "lines": args.lines,
                     "note": args.note, "scale": args.scale}
        if args.masthead is not None:
            overrides["masthead"] = args.masthead
        if args.colors:
            overrides["colors"] = json.loads(args.colors)
        html = args.template.read_text(encoding="utf-8")
        html, count = re.subn(r"const HEADER = (\{.*?\});",
                              lambda m: f"const HEADER = Object.assign({m.group(1)}, "
                                        f"{json.dumps(overrides, ensure_ascii=False)});",
                              html, count=1, flags=re.S)
        if count != 1:
            raise ValueError("Template has no `const HEADER = {...};` block.")
        with tempfile.TemporaryDirectory() as work:
            work = Path(work)
            (work / "index.html").write_text(html, encoding="utf-8")
            shutil.copytree(args.template.parent / "fonts", work / "fonts")
            handler = functools.partial(QuietHandler, directory=str(work))
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            try:
                url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
                dom = subprocess.run(
                    [browser, "--headless=new", "--disable-gpu", "--no-first-run",
                     f"--user-data-dir={work / 'profile'}", "--virtual-time-budget=15000",
                     "--dump-dom", url],
                    capture_output=True, text=True, timeout=120).stdout
            finally:
                server.shutdown()
        status = re.search(r'<p id="status">(.*?)</p>', dom, re.S)
        status = status.group(1).strip() if status else "(no status)"
        match = re.search(r'<a id="download"[^>]*href="data:image/png;base64,([^"]+)"', dom)
        if not match or "未导出" in status:
            raise ValueError(f"Template did not export: {status}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(base64.b64decode(match.group(1)))
        print(json.dumps({"output": str(args.output), "status": status}, ensure_ascii=False))
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()

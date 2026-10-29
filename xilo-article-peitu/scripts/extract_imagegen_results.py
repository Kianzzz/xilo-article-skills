#!/usr/bin/env python3
"""Recover PNG data URLs from a Codex JSONL session."""

import argparse
import base64
import json
import re
from pathlib import Path


def walk(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk(item)
    elif isinstance(value, str):
        yield value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    found = []
    for line in args.session.read_text(errors="ignore").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        for value in walk(record):
            for match in re.finditer(r"data:image/png;base64,([A-Za-z0-9+/=]+)", value):
                data = base64.b64decode(match.group(1))
                if data not in found:
                    found.append(data)
    for index, data in enumerate(found, 1):
        (args.output_dir / f"recovered-{index:02d}.png").write_bytes(data)
    print(f"recovered={len(found)} output_dir={args.output_dir}")


if __name__ == "__main__":
    main()

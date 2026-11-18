#!/usr/bin/env python3
"""Validate a generated cover ratio and optionally resize an already-valid image."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image


PRESETS = {
    "wechat-main": (2350, 1000),
    "wechat-square": (1200, 1200),
    "x-article": (2500, 1000),
    "video-vertical": (1080, 1440),
    "video-wide": (1920, 1080),
    "video-landscape": (1440, 1080),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--preset", choices=sorted(PRESETS), required=True)
    parser.add_argument("--resize-out", type=Path)
    parser.add_argument("--ratio-tolerance", type=float, default=0.005)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    target_width, target_height = PRESETS[args.preset]
    target_ratio = target_width / target_height

    with Image.open(args.input) as source:
        source_ratio = source.width / source.height
        relative_error = abs(source_ratio - target_ratio) / target_ratio
        if relative_error > args.ratio_tolerance:
            print(
                "aspect ratio mismatch: "
                f"source={source.width}x{source.height} ratio={source_ratio:.5f}, "
                f"preset={args.preset} target={target_width}x{target_height} "
                f"ratio={target_ratio:.5f}, relative_error={relative_error:.2%}. "
                "Regenerate natively; do not crop, pad, outpaint, or expand canvas.",
                file=sys.stderr,
            )
            raise SystemExit(2)

        print(
            f"PASS preset={args.preset} source={source.width}x{source.height} "
            f"target_ratio={target_ratio:.5f} error={relative_error:.2%}"
        )

        if args.resize_out:
            output = source.convert("RGB").resize(
                (target_width, target_height), Image.Resampling.LANCZOS
            )
            args.resize_out.parent.mkdir(parents=True, exist_ok=True)
            output.save(args.resize_out, quality=95)
            print(f"WROTE {args.resize_out} {target_width}x{target_height}")


if __name__ == "__main__":
    main()

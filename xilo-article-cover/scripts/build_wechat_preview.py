#!/usr/bin/env python3
"""Build a review-only side-by-side preview from valid WeChat main and square covers."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("main", type=Path)
    parser.add_argument("square", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--gutter", type=int, default=8)
    return parser.parse_args()


def assert_ratio(image: Image.Image, target: float, label: str) -> None:
    error = abs(image.width / image.height - target) / target
    if error > 0.005:
        raise SystemExit(
            f"{label} ratio mismatch: {image.width}x{image.height}; "
            "regenerate the final cover instead of cropping it for preview"
        )


def main() -> None:
    args = parse_args()
    with Image.open(args.main) as main_source, Image.open(args.square) as square_source:
        assert_ratio(main_source, 2.35, "main")
        assert_ratio(square_source, 1.0, "square")
        main_width = round(args.height * 2.35)
        main_image = main_source.convert("RGB").resize(
            (main_width, args.height), Image.Resampling.LANCZOS
        )
        square_image = square_source.convert("RGB").resize(
            (args.height, args.height), Image.Resampling.LANCZOS
        )

    canvas = Image.new(
        "RGB", (main_width + args.gutter + args.height, args.height), "white"
    )
    canvas.paste(main_image, (0, 0))
    canvas.paste(square_image, (main_width + args.gutter, 0))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(args.output, quality=95)
    print(f"WROTE {args.output} {canvas.width}x{canvas.height} review-only")


if __name__ == "__main__":
    main()

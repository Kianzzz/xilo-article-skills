#!/usr/bin/env python3
"""Size a transparent scene by character head height, then compose a GIF with FFmpeg."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageChops


def plan(args):
    with Image.open(args.base) as base, Image.open(args.scene) as scene:
        width, height = base.size
        if width != height * 3:
            raise ValueError("The base must have a 3:1 aspect ratio.")
        if "A" not in scene.getbands():
            raise ValueError("The scene needs real alpha transparency.")
        alpha = scene.getchannel("A")
        if alpha.getextrema()[0] > 16:
            raise ValueError("The scene has no transparent outer background.")
        crop = alpha.point(lambda value: 255 if value > 16 else 0).getbbox()
        if not crop:
            raise ValueError("The scene has no visible content.")
        left, top, right, bottom = args.head_box
        if not (0 <= left < right <= scene.width and 0 <= top < bottom <= scene.height):
            raise ValueError("Head box must be inside the source scene.")
        factor = width / 2400
        target = args.head_target * factor
        if not 280 <= args.head_target <= 340:
            raise ValueError("Head target must be 280–340 at 2400px canvas width.")
        scale = target / (bottom - top)
        scene_width = round((crop[2] - crop[0]) * scale)
        scene_height = round((crop[3] - crop[1]) * scale)
        actual_head = (bottom - top) * scene_height / (crop[3] - crop[1])
        x = round(args.x * factor)
        y = round(args.center_y * factor - scene_height / 2)
        amplitude = 8 * factor
        margin = 24 * factor
        if x < margin or x + scene_width > width - margin:
            raise ValueError("Scene overflows horizontally. Move it or simplify props; keep head scale.")
        if y - amplitude < margin or y + scene_height + amplitude > height - margin:
            raise ValueError("Scene overflows vertically. Move it or simplify props; keep head scale.")
        return {
            "canvas": [width, height], "alpha_threshold": 16, "source_crop": crop,
            "source_head_box": args.head_box, "head_box_basis": args.head_basis,
            "scale_factor": scale,
            "head_target_px": target, "head_actual_px": round(actual_head, 2),
            "scene_size": [scene_width, scene_height], "scene_x": x, "scene_y": y,
            "amplitude_px": amplitude, "duration_seconds": 4, "fps": 20,
            "stamp_rect": [round(v * factor) for v in [2187, 564, 174, 174]] if args.stamp else None,
            "visual_review": "待用户判断；几何与文件参数检查不代表视觉通过",
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--head-box", type=int, nargs=4, required=True,
                        metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
                        help="Source hair-top-to-chin box; exclude crown plant, not the whole scene.")
    parser.add_argument("--head-basis", required=True,
                        help="How the source head box was identified; record approximate measurements honestly.")
    parser.add_argument("--head-target", type=float, default=310,
                        help="Head height at 2400px canvas width; allowed 280–340.")
    parser.add_argument("--x", type=float, default=1240)
    parser.add_argument("--center-y", type=float, default=400)
    parser.add_argument("--stamp", type=Path,
                        help="Optional stamp image from the IP profile; omit for no stamp.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    try:
        layout = plan(args)
        if args.plan_only:
            print(json.dumps(layout, ensure_ascii=False, indent=2))
            return
        if args.output.suffix.lower() != ".gif":
            raise ValueError("Output must end in .gif.")
        outputs = [args.output, args.output.with_suffix(".png"), args.output.with_suffix(".json")]
        if any(p.exists() for p in outputs):
            raise ValueError("Output exists. Choose a new version filename.")
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise ValueError("FFmpeg is unavailable.")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        cx, cy, cr, cb = layout["source_crop"]
        sw, sh = layout["scene_size"]
        moving = (
            f"[1:v]format=rgba,crop={cr-cx}:{cb-cy}:{cx}:{cy},scale={sw}:{sh}[scene];"
            f"[0:v][scene]overlay=x={layout['scene_x']}:"
            f"y='{layout['scene_y']}+{layout['amplitude_px']}*sin(2*PI*t/4)':"
            "eval=frame:format=rgb"
        )
        if args.stamp:
            sx, sy, stamp_width, stamp_height = layout["stamp_rect"]
            filters = (
                moving + "[moving];"
                f"[2:v]format=rgba,colorkey=0xFFFFFF:0.18:0.12,scale={stamp_width}:{stamp_height}[stamp];"
                f"[moving][stamp]overlay=x={sx}:y={sy}:format=rgb,"
            )
        else:
            filters = moving + ","
        filters += "trim=duration=4,split[a][b];[a]palettegen=reserve_transparent=0[p];[b][p]paletteuse=dither=none"
        command = [ffmpeg, "-v", "error", "-n"]
        for source in [args.base, args.scene] + ([args.stamp] if args.stamp else []):
            command += ["-loop", "1", "-framerate", "20", "-i", str(source)]
        command += ["-filter_complex", filters, "-t", "4", "-loop", "0", str(args.output)]
        subprocess.run(command, check=True)
        subprocess.run([ffmpeg, "-v", "error", "-n", "-i", str(args.output),
                        "-frames:v", "1", "-update", "1", str(outputs[1])], check=True)
        with Image.open(args.output) as gif, Image.open(outputs[1]) as png:
            gif.seek(0)
            first = gif.convert("RGB")
            matches = ImageChops.difference(first, png.convert("RGB")).getbbox() is None
            durations = []
            for n in range(gif.n_frames):
                gif.seek(n)
                durations.append(gif.info.get("duration", 0))
            gif.seek(min(20, gif.n_frames - 1))
            motion = ImageChops.difference(first, gif.convert("RGB")).getbbox()
            layout["encoding"] = {"format": gif.format, "size": gif.size,
                "frames": gif.n_frames, "duration_ms": sum(durations),
                "frame_durations_ms": sorted(set(durations)), "loop": gif.info.get("loop"),
                "png_matches_first_frame": matches, "motion_diff_bbox": motion}
            if sum(durations) != 4000 or gif.info.get("loop") != 0 or not matches or not motion:
                raise ValueError("GIF technical validation failed; preserve outputs for diagnosis.")
        outputs[2].write_text(json.dumps(layout, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"gif": str(outputs[0]), "png": str(outputs[1]), "layout": layout},
                         ensure_ascii=False, indent=2))
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()

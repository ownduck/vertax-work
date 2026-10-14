"""Hard-cut concatenate segment videos (ffmpeg). Unifies resolution when needed."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


def require_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise SystemExit("未找到 ffmpeg，请先安装并加入 PATH")
    return path


def ffprobe_wh(ffprobe: str, video: Path) -> tuple[int, int]:
    raw = subprocess.check_output(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(video),
        ],
        text=True,
    )
    streams = json.loads(raw).get("streams") or []
    if not streams:
        raise RuntimeError(f"无法读取视频流: {video}")
    w, h = int(streams[0]["width"]), int(streams[0]["height"])
    if w < 1 or h < 1:
        raise RuntimeError(f"非法分辨率 {w}x{h}: {video}")
    return w, h


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"命令失败 ({proc.returncode}): {' '.join(cmd)}\n{err}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--list", type=Path, required=True, help="文本文件：每行一个段视频绝对路径，按时间序")
    p.add_argument("--output", type=Path, required=True, help="输出长片路径")
    a = p.parse_args()

    ffmpeg = require_ffmpeg()
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        sibling = Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix.lower() == ".exe" else "ffprobe")
        ffprobe = str(sibling) if sibling.is_file() else ""
    if not ffprobe:
        raise SystemExit("未找到 ffprobe")

    if not a.list.is_file():
        p.error(f"列表不存在: {a.list}")
    lines = [ln.strip() for ln in a.list.read_text(encoding="utf-8-sig").splitlines() if ln.strip() and not ln.strip().startswith("#")]
    if len(lines) < 1:
        p.error("列表为空")
    videos = [Path(ln) for ln in lines]
    for v in videos:
        if not v.is_file():
            p.error(f"视频不存在: {v}")

    sizes = [ffprobe_wh(ffprobe, v) for v in videos]
    target = sizes[0]
    need_scale = any(s != target for s in sizes)

    a.output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="long_concat_") as tmp:
        tmp_dir = Path(tmp)
        work: list[Path] = []
        if need_scale:
            tw, th = target
            for i, v in enumerate(videos):
                out = tmp_dir / f"scaled_{i:02d}.mp4"
                run(
                    [
                        ffmpeg,
                        "-y",
                        "-i",
                        str(v),
                        "-vf",
                        f"scale={tw}:{th}:force_original_aspect_ratio=decrease,pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2",
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-movflags",
                        "+faststart",
                        str(out),
                    ]
                )
                work.append(out)
        else:
            work = videos

        # Prefer stream copy when already same size; else files are already re-encoded.
        list_file = tmp_dir / "concat.txt"
        # concat demuxer needs forward-slash or escaped paths; use absolute resolved paths.
        list_file.write_text(
            "".join(f"file '{w.resolve().as_posix()}'\n" for w in work),
            encoding="utf-8",
        )
        if need_scale:
            run(
                [
                    ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_file),
                    "-c",
                    "copy",
                    str(a.output),
                ]
            )
        else:
            # Try copy first; on failure re-encode for codec mismatch.
            try:
                run(
                    [
                        ffmpeg,
                        "-y",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        str(list_file),
                        "-c",
                        "copy",
                        str(a.output),
                    ]
                )
            except RuntimeError:
                run(
                    [
                        ffmpeg,
                        "-y",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        str(list_file),
                        "-c:v",
                        "libx264",
                        "-pix_fmt",
                        "yuv420p",
                        "-c:a",
                        "aac",
                        "-movflags",
                        "+faststart",
                        str(a.output),
                    ]
                )

    print(a.output.resolve())


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as e:
        raise SystemExit(f"拼接失败: {e}") from e

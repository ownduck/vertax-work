"""提交 MiniMax H3 参考生视频任务，并仅输出 prompt_id。"""

import argparse
import json
import math
import os
from pathlib import Path
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[1]
IMAGE_NODES = ("23", "24", "30")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for i, node in enumerate(IMAGE_NODES, 1):
        parser.add_argument(f"--image{i}", required=i == 1, type=Path, help=f"参考图{i} → 节点{node}")
    parser.add_argument("--video1", type=Path, help="可选参考视频1 → 节点26")
    parser.add_argument("--prompt", help="短提示词；与 --prompt-file 二选一")
    parser.add_argument("--prompt-file", type=Path, help="提示词 TXT；与 --prompt 二选一 → 节点29")
    parser.add_argument("--duration", type=float, default=10, help="视频时长秒数（默认10）→ 节点18")
    parser.add_argument("--comfyui-endpoint", help="ComfyUI 地址；其次读取 VERTAX_COMFYUI_ENDPOINT")
    args = parser.parse_args()
    endpoint = (args.comfyui_endpoint or os.getenv("VERTAX_COMFYUI_ENDPOINT") or "http://127.0.0.1:8188").rstrip("/")

    if not math.isfinite(args.duration) or args.duration <= 0:
        parser.error("--duration 必须是大于0的有限秒数")
    if bool(args.prompt) == bool(args.prompt_file):
        parser.error("--prompt 与 --prompt-file 必须二选一")
    if args.image3 and not args.image2:
        parser.error("--image3 需要同时传入 --image2")

    images = [p for p in (args.image1, args.image2, args.image3) if p]
    media = [(node, "image", path) for node, path in zip(IMAGE_NODES, images)]
    if args.video1:
        media.append(("26", "video", args.video1))
    for path in [args.prompt_file, *(item[2] for item in media)]:
        if path and not path.is_file():
            parser.error(f"文件不存在: {path}")
    names = [path.name.casefold() for _, _, path in media]
    if len(names) != len(set(names)):
        parser.error("参考素材的文件名不能重复")

    if args.prompt is not None:
        prompt = args.prompt.strip()
    else:
        prompt = args.prompt_file.read_text(encoding="utf-8-sig").strip()
    if not prompt:
        parser.error("正向提示词不能为空")

    variant = f"{len(images)}i" + ("1v" if args.video1 else "")
    workflow = json.loads((ROOT / "assets" / f"workflow-r2v-minimax-h3-{variant}.json").read_text(encoding="utf-8-sig"))
    workflow["18"]["inputs"]["value"] = args.duration  # 工作流会换算并对齐帧数。
    workflow["29"]["inputs"]["prompt"] = prompt
    workflow["16"]["inputs"]["save_output"] = True

    def post(path, **kwargs):
        response = requests.post(endpoint + path, timeout=120, **kwargs)
        if not response.ok:
            raise RuntimeError(f"{path}: HTTP {response.status_code} {response.text}")
        return response.json()

    # /upload/image 同时接收图片和视频，multipart 字段名均为 image。
    for node, field, source in media:
        with source.open("rb") as file:
            uploaded = post("/upload/image", files={"image": (source.name, file)}, data={"overwrite": "true"})
        workflow[node]["inputs"][field] = "/".join(filter(None, [uploaded.get("subfolder"), uploaded["name"]]))

    submitted = post("/prompt", json={"prompt": workflow, "client_id": str(uuid4())})
    if submitted.get("node_errors"):
        raise RuntimeError(f"节点错误: {submitted['node_errors']}")
    print(f"prompt_id: {submitted['prompt_id']}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, requests.RequestException) as error:
        raise SystemExit(f"提交失败: {error}")

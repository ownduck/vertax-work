"""提交 ComfyUI MiniMax H3 生视频任务，并仅输出 prompt_id。"""

import argparse
import copy
import json
import os
from pathlib import Path
from uuid import uuid4

import requests

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / "assets" / "workflow-minimax-h3.json"

# (cli attr, LoadImage node id, conditioning input key on node 8)
MEDIA_SLOTS = (
    ("image1", "23", "ref_images.ref_image_0"),
    ("image2", "24", "ref_images.ref_image_1"),
    ("image3", "30", "ref_images.ref_image_2"),
    ("first_image", "32", "first_frame"),
    ("last_image", "33", "last_frame"),
)

RATIO_MAP = {
    "16:9": "16:9 (Landscape Widescreen)",
    "9:16": "9:16 (Portrait Widescreen)",
    "1:1": "1:1 (Square)",
    "4:3": "4:3 (Standard)",
    "3:4": "3:4 (Portrait)",
}


def resolve_task_type(has_first: bool, has_last: bool, has_ref: bool) -> str:
    if not has_first and not has_last and not has_ref:
        return "T2VA"
    if has_first and not has_last and not has_ref:
        return "I2VA"
    if has_last and not has_first and not has_ref:
        return "L2VA"
    if has_first and has_last and not has_ref:
        return "FL2VA"
    if has_ref and not has_first and not has_last:
        return "Ref2VA"
    return "Hybrid"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prompt", help="短提示词；与 --prompt-file 二选一")
    p.add_argument("--prompt-file", type=Path, help="提示词 TXT；与 --prompt 二选一 → 节点29")
    p.add_argument("--duration", type=int, default=10, help="时长秒数；最小4，最大15，默认10 → 节点18")
    p.add_argument(
        "--ratio",
        choices=tuple(RATIO_MAP),
        default="9:16",
        help="画幅；默认 9:16 → 节点22",
    )
    p.add_argument("--image1", type=Path, help="参考图1 → 节点23")
    p.add_argument("--image2", type=Path, help="参考图2 → 节点24")
    p.add_argument("--image3", type=Path, help="参考图3 → 节点30")
    p.add_argument("--first-image", type=Path, dest="first_image", help="首帧 → 节点32")
    p.add_argument("--last-image", type=Path, dest="last_image", help="尾帧 → 节点33")
    p.add_argument("--comfyui-endpoint", help="ComfyUI 地址；其次读取 VERTAX_COMFYUI_ENDPOINT")
    p.add_argument("--seed", type=int, default=20827583377142, help="噪波种子；默认 20827583377142 → 节点13 noise_seed，改动即出不同版本")
    a = p.parse_args()
    endpoint = (a.comfyui_endpoint or os.getenv("VERTAX_COMFYUI_ENDPOINT") or "http://127.0.0.1:8188").rstrip("/")

    if bool(a.prompt) == bool(a.prompt_file):
        p.error("--prompt 与 --prompt-file 必须二选一")
    if not 4 <= a.duration <= 15:
        p.error("--duration 须为 4～15 的整数")
    if a.image3 and not a.image2:
        p.error("--image3 需要同时传入 --image2")
    if (a.image2 or a.image3) and not a.image1:
        p.error("传 --image2/--image3 时必须同时传 --image1")

    if a.prompt is not None:
        prompt = a.prompt.strip()
    else:
        if not a.prompt_file.is_file():
            p.error(f"文件不存在: {a.prompt_file}")
        prompt = a.prompt_file.read_text(encoding="utf-8-sig").strip()
    if not prompt:
        p.error("正向提示词不能为空")

    provided = []
    for attr, node_id, cond_key in MEDIA_SLOTS:
        path = getattr(a, attr)
        if path is None:
            continue
        if not path.is_file():
            p.error(f"文件不存在: {path}")
        provided.append((attr, node_id, cond_key, path))

    names = [path.name.casefold() for *_, path in provided]
    if len(names) != len(set(names)):
        p.error("参考素材的文件名不能重复")

    if not WORKFLOW_PATH.is_file():
        raise RuntimeError(f"工作流模板不存在: {WORKFLOW_PATH}")
    workflow = copy.deepcopy(json.loads(WORKFLOW_PATH.read_text(encoding="utf-8-sig")))

    has_first = a.first_image is not None
    has_last = a.last_image is not None
    has_ref = a.image1 is not None
    task_type = resolve_task_type(has_first, has_last, has_ref)

    workflow["18"]["inputs"]["value"] = a.duration
    workflow["13"]["inputs"]["noise_seed"] = a.seed
    workflow["22"]["inputs"]["aspect_ratio"] = RATIO_MAP[a.ratio]
    workflow["29"]["inputs"]["prompt"] = prompt
    workflow["16"]["inputs"]["save_output"] = True
    workflow["8"]["inputs"]["task_type"] = task_type

    cond_inputs = workflow["8"]["inputs"]
    provided_nodes = {node_id for _, node_id, _, _ in provided}
    for attr, node_id, cond_key in MEDIA_SLOTS:
        if node_id in provided_nodes:
            continue
        workflow.pop(node_id, None)
        cond_inputs.pop(cond_key, None)

    def post(path, **kwargs):
        token = (os.getenv("VERTAX_COMFYUI_TOKEN") or "").strip()
        headers = {"X-Token": token} if token else {}
        response = requests.post(endpoint + path, headers=headers, timeout=120, **kwargs)
        if not response.ok:
            raise RuntimeError(f"{path}: HTTP {response.status_code} {response.text}")
        return response.json()

    for _, node_id, _, source in provided:
        with source.open("rb") as file:
            uploaded = post("/upload/image", files={"image": (source.name, file)}, data={"overwrite": "true"})
        workflow[node_id]["inputs"]["image"] = "/".join(filter(None, [uploaded.get("subfolder"), uploaded["name"]]))

    submitted = post("/prompt", json={"prompt": workflow, "client_id": str(uuid4())})
    if submitted.get("node_errors"):
        raise RuntimeError(f"节点错误: {submitted['node_errors']}")
    prompt_id = submitted.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"响应无 prompt_id: {submitted}")
    print(f"prompt_id: {prompt_id}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, requests.RequestException) as error:
        raise SystemExit(f"提交失败: {error}")

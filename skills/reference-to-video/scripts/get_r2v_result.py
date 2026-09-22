"""轮询已有 R2V 任务，并在完成后下载视频；不会提交新任务。"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

NODE_VIDEO = "16"
PREVIEWS = {".png", ".jpg", ".jpeg", ".webp"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-id", required=True, help="run_r2v.py 输出的 prompt_id")
    parser.add_argument("--output-dir", type=Path, default=Path("output"), help="下载目录（默认 ./output）")
    parser.add_argument("--comfyui-endpoint", help="ComfyUI 地址；其次读取 VERTAX_COMFYUI_ENDPOINT")
    args = parser.parse_args()
    endpoint = (args.comfyui_endpoint or os.getenv("VERTAX_COMFYUI_ENDPOINT") or "http://127.0.0.1:8188").rstrip("/")

    def get(path, **kwargs):
        response = requests.get(endpoint + path, timeout=120, **kwargs)
        if not response.ok:
            raise RuntimeError(f"{path}: HTTP {response.status_code} {response.text}")
        return response

    # 每5秒查询一次；状态写入 stderr，stdout 留给最终文件路径。
    started, last_state = time.monotonic(), None
    while True:
        try:
            entry = get(f"/history/{args.prompt_id}").json().get(args.prompt_id)
            if entry:
                break
            queue = get("/queue").json()
            pending = [item[1] for item in queue.get("queue_pending", [])]
            if any(item[1] == args.prompt_id for item in queue.get("queue_running", [])):
                state = "执行中"
            elif args.prompt_id in pending:
                state = f"排队#{pending.index(args.prompt_id) + 1}"
            else:
                raise RuntimeError("历史和队列中均未找到该任务")
        except requests.RequestException as error:
            state = f"连接失败，继续重试: {error}"
        if state != last_state:
            print(f"[{int(time.monotonic() - started)}s] {state}", file=sys.stderr, flush=True)
            last_state = state
        time.sleep(5)

    if entry.get("status", {}).get("status_str") == "error":
        raise RuntimeError(f"任务执行失败: {entry['status'].get('messages')}")
    output = entry.get("outputs", {}).get(NODE_VIDEO, {})
    files = output.get("gifs") or output.get("videos") or output.get("images") or []
    videos = [f for f in files if Path(f["filename"]).suffix.lower() not in PREVIEWS]
    if not videos:
        raise RuntimeError(f"节点 {NODE_VIDEO} 无视频输出")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%y%m%d_%H%M%S")
    for item in videos:
        params = {"filename": item["filename"], "subfolder": item.get("subfolder", ""), "type": item.get("type", "output")}
        source = Path(item["filename"])
        dest = args.output_dir.resolve() / f"{source.stem}_{stamp}{source.suffix}"
        index = 2
        while dest.exists():
            dest = dest.with_stem(f"{source.stem}_{stamp}_{index}")
            index += 1
        dest.write_bytes(get("/view", params=params).content)
        print(dest)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit("已停止轮询")
    except (OSError, KeyError, RuntimeError, ValueError, requests.RequestException) as error:
        raise SystemExit(f"获取失败: {error}")

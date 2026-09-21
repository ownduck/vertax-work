"""检查 ComfyUI /system_stats；成功退出0，失败退出1。"""

import argparse
import os

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comfyui-endpoint", help="ComfyUI 地址（优先于 COMFYUI_ENDPOINT，兜底 http://127.0.0.1:8188）")
    endpoint = (parser.parse_args().comfyui_endpoint or os.getenv("COMFYUI_ENDPOINT") or "http://127.0.0.1:8188").rstrip("/")

    # 去掉地址末尾斜杠，避免拼出 //system_stats；限制等待时间。
    try:
        response = requests.get(f"{endpoint}/system_stats", timeout=10)
        response.raise_for_status()
        stats = response.json()
        if not isinstance(stats, dict) or not isinstance(stats.get("system"), dict):
            raise ValueError("响应缺少 ComfyUI system 信息")
    except (requests.RequestException, ValueError) as error:
        raise SystemExit(f"ComfyUI 不可用: {endpoint} — {error}")
    print(f"ComfyUI 可用: {endpoint}")


if __name__ == "__main__":
    main()

"""调用千问图像生成与编辑 3.0 文生图/图生图，并下载结果。"""

import argparse, base64, mimetypes, os, sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

TIMEOUT = 600  # DashScope 同步建议 ≥600s
MIME = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif", "bmp": "image/bmp", "tif": "image/tiff", "tiff": "image/tiff"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--image1")  # 本地路径或 http(s) URL；非必填；无图=T2I
    p.add_argument("--image2")
    p.add_argument("--image3")
    p.add_argument("--prompt")  # 与 --prompt-file 二选一
    p.add_argument("--prompt-file", type=Path)
    p.add_argument("--negative-prompt")
    p.add_argument("--negative-prompt-file", type=Path)
    p.add_argument("--model", choices=("qwen-image-3.0-pro", "qwen-image-3.0"), default="qwen-image-3.0")
    p.add_argument("--output-dir", type=Path, default=Path("output"))
    p.add_argument("--endpoint")  # 或环境变量 DASHSCOPE_HTTP_BASE_URL
    a = p.parse_args()

    key = (os.getenv("VERTAX_DASHSCOPE_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or "").strip()
    if not key:
        p.error("未设置 VERTAX_DASHSCOPE_API_KEY 或 DASHSCOPE_API_KEY")
    if bool(a.prompt) == bool(a.prompt_file):
        p.error("--prompt 与 --prompt-file 必须二选一")
    if a.negative_prompt and a.negative_prompt_file:
        p.error("--negative-prompt 与 --negative-prompt-file 不能同时传")
    if a.image3 and not a.image2:
        p.error("--image3 需要同时传入 --image2")
    if (a.image2 or a.image3) and not a.image1:
        p.error("传 --image2/--image3 时必须同时传 --image1")

    def is_url(s):
        return urlparse(s).scheme in ("http", "https")

    def read(path):
        s = path.read_text(encoding="utf-8-sig").strip()
        if not s:
            raise ValueError(f"文件内容为空: {path}")
        return s

    # URL 原样传；本地转 data URI
    def img_in(src):
        if is_url(src):
            return src
        path = Path(src)
        mime, _ = mimetypes.guess_type(path.name)
        if not mime or not mime.startswith("image/"):
            mime = MIME.get(path.suffix.lower().lstrip("."))
        if not mime:
            raise ValueError(f"无法识别图像格式: {path}")
        return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"

    images = [x for x in (a.image1, a.image2, a.image3) if x]
    for path in (a.prompt_file, a.negative_prompt_file):
        if path and not path.is_file():
            p.error(f"文件不存在: {path}")
    names = []
    for src in images:
        if is_url(src):
            continue
        path = Path(src)
        if not path.is_file():
            p.error(f"文件不存在: {path}")
        names.append(path.name.casefold())
    if len(names) != len(set(names)):
        p.error("参考图文件名不能重复")

    prompt = (a.prompt or "").strip() if a.prompt is not None else read(a.prompt_file)
    if not prompt:
        p.error("正向提示词不能为空")
    neg = (a.negative_prompt.strip() or None) if a.negative_prompt is not None else (read(a.negative_prompt_file) if a.negative_prompt_file else None)

    content = [{"image": img_in(x)} for x in images] + [{"text": prompt}]
    # 不传 size（传 auto 会 InvalidParameter）；n/watermark 固定
    params = {"n": 1, "watermark": False, "prompt_extend": True}
    if neg:
        params["negative_prompt"] = neg

    base = (a.endpoint or os.getenv("DASHSCOPE_HTTP_BASE_URL") or "https://dashscope.aliyuncs.com/api/v1").rstrip("/")
    r = requests.post(
        f"{base}/services/aigc/multimodal-generation/generation",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": a.model, "input": {"messages": [{"role": "user", "content": content}]}, "parameters": params},
        timeout=TIMEOUT,
    )
    try:
        data = r.json()
    except ValueError as e:
        raise RuntimeError(f"响应非 JSON: HTTP {r.status_code} {r.text}") from e
    if not r.ok or data.get("code"):
        raise RuntimeError(f"调用失败 [{data.get('code') or r.status_code}] {data.get('message') or r.text}" + (f" request_id={data['request_id']}" if data.get("request_id") else ""))

    urls = [i["image"] for c in (data.get("output") or {}).get("choices") or [] for i in (c.get("message") or {}).get("content") or [] if i.get("image")]
    if not urls:
        raise RuntimeError(f"响应无图像 URL: {data}")

    # 结果 URL 仅 24h，立即落盘；stdout 输出本地路径
    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%y%m%d_%H%M%S")
    for i, u in enumerate(urls, 1):
        suffix = Path(urlparse(u).path).suffix or ".png"
        stem = "qwen_image" if len(urls) == 1 else f"qwen_image_{i}"
        dest, n = out / f"{stem}_{stamp}{suffix.lower()}", 2
        while dest.exists():
            dest = out / f"{stem}_{stamp}_{n}{suffix.lower()}"
            n += 1
        img = requests.get(u, timeout=120)
        if not img.ok:
            raise RuntimeError(f"下载失败 HTTP {img.status_code}: {u}")
        dest.write_bytes(img.content)
        print(dest)
    if data.get("request_id"):
        print(f"request_id: {data['request_id']}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, requests.RequestException) as e:
        raise SystemExit(f"生成失败: {e}")

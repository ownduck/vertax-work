"""调用百炼 MiniMax 视频生成（文生/首尾帧/多模态参考），轮询并下载结果。"""

import argparse, os, sys, time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

POLL_INTERVAL, POLL_TIMEOUT = 15, 2400
HTTP_TIMEOUT, DOWNLOAD_TIMEOUT = 120, 300
DEFAULT_MODEL, DEFAULT_SIZE, DEFAULT_RATIO, DEFAULT_DURATION = "MiniMax/MiniMax-H3", "768P", "9:16", 10
DEFAULT_BASE = "https://dashscope.aliyuncs.com/api/v1"


def is_url(s):
    return urlparse(s).scheme in ("http", "https")


def api_err(prefix, r, data=None):
    data = data if data is not None else {}
    rid = f" request_id={data['request_id']}" if data.get("request_id") else ""
    return RuntimeError(f"{prefix} [{data.get('code') or r.status_code}] {data.get('message') or r.text}{rid}")


def read_json(r):
    try:
        return r.json()
    except ValueError as e:
        raise RuntimeError(f"响应非 JSON: HTTP {r.status_code} {r.text}") from e


def resolve_base(cli):
    if cli:
        return cli.rstrip("/")
    if ep := (os.getenv("DASHSCOPE_HTTP_BASE_URL") or "").strip():
        return ep.rstrip("/")
    if ws := (os.getenv("VERTAX_BAILIAN_WORKSPACE_ID") or os.getenv("BAILIAN_WORKSPACE_ID") or "").strip():
        return f"https://{ws}.cn-beijing.maas.aliyuncs.com/api/v1"
    return DEFAULT_BASE


def upload_local(key, model, path, upload_base):
    r = requests.get(
        f"{upload_base}/uploads",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        params={"action": "getPolicy", "model": model},
        timeout=HTTP_TIMEOUT,
    )
    data = read_json(r)
    if not r.ok or data.get("code"):
        raise api_err("获取上传凭证失败", r, data)
    pol = data["data"]
    oss_key = f"{pol['upload_dir']}/{path.name}"
    with path.open("rb") as f:
        files = {
            "OSSAccessKeyId": (None, pol["oss_access_key_id"]),
            "Signature": (None, pol["signature"]),
            "policy": (None, pol["policy"]),
            "x-oss-object-acl": (None, pol["x_oss_object_acl"]),
            "x-oss-forbid-overwrite": (None, pol["x_oss_forbid_overwrite"]),
            "key": (None, oss_key),
            "success_action_status": (None, "200"),
            "file": (path.name, f),
        }
        up = requests.post(pol["upload_host"], files=files, timeout=DOWNLOAD_TIMEOUT)
    if not up.ok:
        raise RuntimeError(f"上传失败 HTTP {up.status_code}: {path} {up.text}")
    return f"oss://{oss_key}"


def to_url(key, model, src, upload_base):
    if is_url(src):
        return src, False
    path = Path(src)
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")
    return upload_local(key, model, path, upload_base), True


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prompt")
    p.add_argument("--prompt-file", type=Path)
    p.add_argument("--image1")
    p.add_argument("--image2")
    p.add_argument("--image3")
    p.add_argument("--first-image")
    p.add_argument("--last-image")
    p.add_argument("--video1")
    p.add_argument("--audio1")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--size", choices=("768P", "2K"), default=DEFAULT_SIZE)
    p.add_argument("--ratio", choices=("adaptive", "16:9", "9:16", "1:1", "4:3", "3:4", "21:9"), default=DEFAULT_RATIO)
    p.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="时长秒数；最小4，最大15，默认10")
    p.add_argument("--output-dir", type=Path, default=Path("output"))
    p.add_argument("--endpoint")
    a = p.parse_args()

    key = (os.getenv("VERTAX_DASHSCOPE_API_KEY") or os.getenv("DASHSCOPE_API_KEY") or "").strip()
    if not key:
        p.error("未设置 VERTAX_DASHSCOPE_API_KEY 或 DASHSCOPE_API_KEY")
    if bool(a.prompt) == bool(a.prompt_file):
        p.error("--prompt 与 --prompt-file 必须二选一")
    if a.prompt_file and not a.prompt_file.is_file():
        p.error(f"文件不存在: {a.prompt_file}")
    if not 4 <= a.duration <= 15:
        p.error("--duration 须为 4～15 的整数")
    if a.image3 and not a.image2:
        p.error("--image3 需要同时传入 --image2")
    if (a.image2 or a.image3) and not a.image1:
        p.error("传 --image2/--image3 时必须同时传 --image1")

    refs = [x for x in (a.image1, a.image2, a.image3) if x]
    multi, frame = bool(refs or a.video1 or a.audio1), bool(a.first_image or a.last_image)
    if multi and frame:
        p.error("首尾帧与多模态参考不可混用")
    if not multi and not frame and a.ratio == "adaptive":
        p.error("纯文生视频时 --ratio 不能为 adaptive")

    prompt = (a.prompt or "").strip() if a.prompt is not None else a.prompt_file.read_text(encoding="utf-8-sig").strip()
    if not prompt:
        p.error("正向提示词不能为空")
    if len(prompt) > 7000:
        p.error("提示词不超过 7000 字符")

    names = []
    for src in (*refs, a.first_image, a.last_image, a.video1, a.audio1):
        if not src or is_url(src):
            continue
        path = Path(src)
        if not path.is_file():
            p.error(f"文件不存在: {path}")
        names.append(path.name.casefold())
    if len(names) != len(set(names)):
        p.error("参考素材文件名不能重复")

    base = resolve_base(a.endpoint)
    upload_base = (os.getenv("DASHSCOPE_UPLOAD_BASE_URL") or DEFAULT_BASE).rstrip("/")
    media, used_oss = [], False

    def add(typ, src):
        nonlocal used_oss
        url, oss = to_url(key, a.model, src, upload_base)
        used_oss = used_oss or oss
        media.append({"type": typ, "url": url})

    if frame:
        if a.first_image:
            add("first_frame", a.first_image)
        if a.last_image:
            add("last_frame", a.last_image)
    else:
        for src in refs:
            add("image_url", src)
        if a.video1:
            add("feature", a.video1)
        if a.audio1:
            add("driving_audio", a.audio1)

    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "X-DashScope-Async": "enable"}
    if used_oss:
        headers["X-DashScope-OssResourceResolve"] = "enable"
    body = {
        "model": a.model,
        "input": {"prompt": prompt, **({"media": media} if media else {})},
        "parameters": {"resolution": a.size, "ratio": a.ratio, "duration": a.duration, "watermark": False},
    }
    r = requests.post(f"{base}/services/aigc/video-generation/video-synthesis", headers=headers, json=body, timeout=HTTP_TIMEOUT)
    data = read_json(r)
    if not r.ok or data.get("code"):
        raise api_err("提交失败", r, data)
    task_id = (data.get("output") or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"响应无 task_id: {data}")
    if data.get("request_id"):
        print(f"request_id: {data['request_id']}", file=sys.stderr)
    print(f"task_id: {task_id}", file=sys.stderr)

    deadline, video_url = time.monotonic() + POLL_TIMEOUT, None
    while time.monotonic() < deadline:
        q = requests.get(f"{base}/tasks/{task_id}", headers={"Authorization": f"Bearer {key}"}, timeout=HTTP_TIMEOUT)
        qd = read_json(q)
        out = qd.get("output") or {}
        status = out.get("task_status")
        if status == "SUCCEEDED":
            video_url = out.get("video_url")
            break
        if status in ("FAILED", "CANCELED", "UNKNOWN") or ((not q.ok or qd.get("code")) and status != "FAILED"):
            if status in ("FAILED", "CANCELED", "UNKNOWN"):
                raise RuntimeError(
                    f"任务失败 status={status} code={out.get('code')} message={out.get('message')}"
                    + (f" request_id={qd['request_id']}" if qd.get("request_id") else "")
                )
            raise api_err("查询失败", q, qd)
        time.sleep(POLL_INTERVAL)
    else:
        raise RuntimeError(f"轮询超时（{POLL_TIMEOUT}s），可稍后查询 task_id={task_id}")
    if not video_url:
        raise RuntimeError(f"成功响应无 video_url: task_id={task_id}")

    out_dir = a.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%y%m%d_%H%M%S")
    suffix = Path(urlparse(video_url).path).suffix or ".mp4"
    dest, n = out_dir / f"minimax_video_{stamp}{suffix.lower()}", 2
    while dest.exists():
        dest = out_dir / f"minimax_video_{stamp}_{n}{suffix.lower()}"
        n += 1
    dl = requests.get(video_url, timeout=DOWNLOAD_TIMEOUT)
    if not dl.ok:
        raise RuntimeError(f"下载失败 HTTP {dl.status_code}: {video_url}")
    dest.write_bytes(dl.content)
    print(dest)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, requests.RequestException) as e:
        raise SystemExit(f"生成失败: {e}")

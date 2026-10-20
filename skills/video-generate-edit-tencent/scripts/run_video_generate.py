"""调用腾讯云 VOD Vega-Video Lite（文生/首尾帧/多模态参考），轮询并下载结果。"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from qcloud_cos import CosConfig, CosS3Client
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.vod.v20180717 import models, vod_client

POLL_INTERVAL, POLL_TIMEOUT = 5, 2400
DOWNLOAD_TIMEOUT = 300
DEFAULT_MODEL = "wand-vega-video"
DEFAULT_VERSION = "1.0-lite"
DEFAULT_SIZE, DEFAULT_RATIO, DEFAULT_DURATION = "768P", "9:16", 10
DEFAULT_SUB_APP_ID = 1442456629
ENDPOINT = "vod.tencentcloudapi.com"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}
AUDIO_EXTS = {".wav", ".mp3", ".aac", ".m4a"}


def is_url(s: str) -> bool:
    return urlparse(s).scheme in ("http", "https")


def media_type_of(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in IMAGE_EXTS:
        return "Image"
    if ext in VIDEO_EXTS:
        return "Video"
    if ext in AUDIO_EXTS:
        return "Audio"
    raise ValueError(f"无法从扩展名判断素材类型: {path}")


def media_type_from_url(url: str, hint: str) -> str:
    path = Path(urlparse(url).path)
    try:
        return media_type_of(path)
    except ValueError:
        return hint


def get_secrets() -> tuple[str, str, int]:
    sid = (
        os.getenv("VERTAX_TENCENTCLOUD_SECRET_ID")
        or os.getenv("TENCENTCLOUD_SECRET_ID")
        or ""
    ).strip()
    sk = (
        os.getenv("VERTAX_TENCENTCLOUD_SECRET_KEY")
        or os.getenv("TENCENTCLOUD_SECRET_KEY")
        or ""
    ).strip()
    if not sid or not sk:
        raise RuntimeError(
            "未设置 VERTAX_TENCENTCLOUD_SECRET_ID/TENCENTCLOUD_SECRET_ID "
            "与 VERTAX_TENCENTCLOUD_SECRET_KEY/TENCENTCLOUD_SECRET_KEY"
        )
    raw = (
        os.getenv("VERTAX_TENCENTCLOUD_VOD_SUB_APP_ID")
        or os.getenv("TENCENTCLOUD_VOD_SUB_APP_ID")
        or str(DEFAULT_SUB_APP_ID)
    ).strip()
    try:
        sub_app_id = int(raw)
    except ValueError as e:
        raise RuntimeError(f"VOD SubAppId 非法: {raw}") from e
    return sid, sk, sub_app_id


def get_client(sid: str, sk: str) -> vod_client.VodClient:
    http = HttpProfile()
    http.endpoint = ENDPOINT
    profile = ClientProfile()
    profile.httpProfile = http
    return vod_client.VodClient(credential.Credential(sid, sk), "", profile)


def build_ext_info(enhance: str, generate_mode: str | None, quality_mode: str | None) -> str:
    params: dict[str, object] = {"EnhancePromptMode": enhance}
    if generate_mode:
        params["GenerateMode"] = generate_mode
    if quality_mode:
        params["VideoQualityMode"] = quality_mode
    return json.dumps(
        {"WandVegaParameters": json.dumps(params, ensure_ascii=False)},
        ensure_ascii=False,
    )


def upload_local(client: vod_client.VodClient, sub_app_id: int, path: Path) -> str:
    """ApplyUpload → COS PUT → CommitUpload，返回 FileId。"""
    category = media_type_of(path)
    media_type = path.suffix.lstrip(".").lower()
    if media_type == "jpeg":
        media_type = "jpg"
    req = models.ApplyUploadRequest()
    req.from_json_string(
        json.dumps(
            {
                "SubAppId": sub_app_id,
                "MediaType": media_type,
                "MediaName": path.name,
            },
            ensure_ascii=False,
        )
    )
    applied = json.loads(client.ApplyUpload(req).to_json_string())
    cert = applied.get("TempCertificate") or {}
    bucket = applied["StorageBucket"]
    region = applied["StorageRegion"]
    key = (applied.get("MediaStoragePath") or "").lstrip("/")
    session_key = applied["VodSessionKey"]
    if not cert.get("SecretId") or not key:
        raise RuntimeError(f"ApplyUpload 响应不完整: {applied}")

    cos = CosS3Client(
        CosConfig(
            Region=region,
            SecretId=cert["SecretId"],
            SecretKey=cert["SecretKey"],
            Token=cert.get("Token"),
            Scheme="https",
        )
    )
    with path.open("rb") as f:
        cos.put_object(Bucket=bucket, Body=f, Key=key)

    commit = models.CommitUploadRequest()
    commit.from_json_string(
        json.dumps({"SubAppId": sub_app_id, "VodSessionKey": session_key}, ensure_ascii=False)
    )
    committed = json.loads(client.CommitUpload(commit).to_json_string())
    file_id = committed.get("FileId")
    if not file_id:
        raise RuntimeError(f"CommitUpload 无 FileId: {committed}")
    print(f"uploaded {path.name} -> FileId={file_id} ({category})", file=sys.stderr)
    return file_id


def to_file_info(
    client: vod_client.VodClient,
    sub_app_id: int,
    src: str,
    usage: str,
    category_hint: str,
) -> dict:
    if is_url(src):
        return {
            "Type": "Url",
            "Category": media_type_from_url(src, category_hint),
            "Url": src,
            "Usage": usage,
        }
    path = Path(src)
    if not path.is_file():
        raise FileNotFoundError(f"文件不存在: {path}")
    file_id = upload_local(client, sub_app_id, path)
    return {
        "Type": "File",
        "Category": media_type_of(path),
        "FileId": file_id,
        "Usage": usage,
    }


def pick_urls(task: dict) -> list[str]:
    output = task.get("Output") or {}
    urls: list[str] = []
    for f in output.get("FileInfos") or []:
        if f.get("FileUrl"):
            urls.append(f["FileUrl"])
    for key in ("FileUrl", "MediaUrl", "Url"):
        if output.get(key):
            urls.append(output[key])
    seen, unique = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique.append(u)
    return unique


def main() -> None:
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
    p.add_argument("--model-version", default=DEFAULT_VERSION)
    p.add_argument(
        "--size",
        choices=("480P", "768P", "1080P", "2K", "4K"),
        default=DEFAULT_SIZE,
    )
    p.add_argument(
        "--ratio",
        choices=("adaptive", "16:9", "9:16", "1:1", "4:3", "3:4", "21:9"),
        default=DEFAULT_RATIO,
    )
    p.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="时长秒数；最小4，最大15，默认10")
    p.add_argument("--output-dir", type=Path, default=Path("output"))
    p.add_argument("--sub-app-id", type=int, default=None)
    p.add_argument(
        "--enhance-prompt",
        choices=("enable", "disable"),
        default="enable",
        help="ExtInfo EnhancePromptMode；默认 enable",
    )
    p.add_argument("--generate-mode", choices=("Standard", "Fast", "StandardMovie"), default=None)
    p.add_argument("--quality-mode", choices=("Standard", "Fast", "SuperFast"), default=None)
    p.add_argument(
        "--audio-generation",
        choices=("Enabled", "Disabled"),
        default="Enabled",
    )
    p.add_argument("--input-region", choices=("Mainland", "Oversea", "OverseaUSWest"), default="Mainland")
    a = p.parse_args()

    sid, sk, env_sub = get_secrets()
    sub_app_id = a.sub_app_id if a.sub_app_id is not None else env_sub
    client = get_client(sid, sk)

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
    if a.last_image and not a.first_image and not (a.image1 or a.video1 or a.audio1):
        # 官方：可单独首帧，不可单独尾帧（首尾帧模式下）
        p.error("首尾帧模式下不可单独传 --last-image，须同时传 --first-image")

    refs = [x for x in (a.image1, a.image2, a.image3) if x]
    multi = bool(refs or a.video1 or a.audio1)
    frame = bool(a.first_image or a.last_image)
    if multi and frame:
        p.error("首尾帧与多模态参考不可混用")
    if a.audio1 and not (refs or a.video1 or frame):
        p.error("音频须配合参考图/视频或首尾帧，不能单独输入")
    if not multi and not frame and a.ratio == "adaptive":
        p.error("纯文生视频时 --ratio 不能为 adaptive")

    prompt = (a.prompt or "").strip() if a.prompt is not None else a.prompt_file.read_text(encoding="utf-8-sig").strip()
    if not prompt:
        p.error("正向提示词不能为空")
    if len(prompt) > 7000:
        p.error("提示词不超过 7000 字符")

    names: list[str] = []
    for src in (*refs, a.first_image, a.last_image, a.video1, a.audio1):
        if not src or is_url(src):
            continue
        path = Path(src)
        if not path.is_file():
            p.error(f"文件不存在: {path}")
        names.append(path.name.casefold())
    if len(names) != len(set(names)):
        p.error("参考素材文件名不能重复")

    file_infos: list[dict] = []
    if frame:
        if a.first_image:
            file_infos.append(
                to_file_info(client, sub_app_id, a.first_image, "FirstFrame", "Image")
            )
        if a.last_image:
            file_infos.append(
                to_file_info(client, sub_app_id, a.last_image, "LastFrame", "Image")
            )
    else:
        for src in refs:
            file_infos.append(to_file_info(client, sub_app_id, src, "Reference", "Image"))
        if a.video1:
            file_infos.append(to_file_info(client, sub_app_id, a.video1, "Reference", "Video"))
        if a.audio1:
            file_infos.append(to_file_info(client, sub_app_id, a.audio1, "Reference", "Audio"))

    params: dict = {
        "SubAppId": sub_app_id,
        "ModelName": a.model,
        "ModelVersion": a.model_version,
        "Prompt": prompt,
        "OutputConfig": {
            "StorageMode": "Temporary",
            "Duration": a.duration,
            "Resolution": a.size,
            "AspectRatio": a.ratio,
            "AudioGeneration": a.audio_generation,
        },
        "ExtInfo": build_ext_info(a.enhance_prompt, a.generate_mode, a.quality_mode),
        "InputRegion": a.input_region,
    }
    if file_infos:
        params["FileInfos"] = file_infos

    req = models.CreateAigcVideoTaskRequest()
    req.from_json_string(json.dumps(params, ensure_ascii=False))
    try:
        data = json.loads(client.CreateAigcVideoTask(req).to_json_string())
    except TencentCloudSDKException as e:
        raise RuntimeError(f"提交失败: {e}") from e

    task_id = data.get("TaskId")
    if not task_id:
        raise RuntimeError(f"响应无 TaskId: {data}")
    if data.get("RequestId"):
        print(f"request_id: {data['RequestId']}", file=sys.stderr)
    print(f"task_id: {task_id}", file=sys.stderr)

    deadline = time.monotonic() + POLL_TIMEOUT
    task: dict = {}
    while time.monotonic() < deadline:
        detail_req = models.DescribeTaskDetailRequest()
        detail_req.from_json_string(
            json.dumps({"TaskId": task_id, "SubAppId": sub_app_id}, ensure_ascii=False)
        )
        try:
            detail = json.loads(client.DescribeTaskDetail(detail_req).to_json_string())
        except TencentCloudSDKException as e:
            raise RuntimeError(f"查询失败: {e}") from e

        task = detail.get("AigcVideoTask") or {}
        status = task.get("Status") or detail.get("Status") or ""
        err_code, message = task.get("ErrCode"), task.get("Message") or ""
        print(
            f"status={status} progress={task.get('Progress')} err={err_code} msg={message}",
            file=sys.stderr,
        )

        if status in ("FINISH", "FAIL"):
            if status == "FAIL" or err_code not in (None, 0):
                raise RuntimeError(
                    f"任务失败 status={status} ErrCode={err_code} Message={message} task_id={task_id}"
                    + (f" request_id={detail.get('RequestId')}" if detail.get("RequestId") else "")
                )
            break
        time.sleep(POLL_INTERVAL)
    else:
        raise RuntimeError(f"轮询超时（{POLL_TIMEOUT}s），可稍后查询 task_id={task_id}")

    urls = pick_urls(task)
    if not urls:
        raise RuntimeError(f"成功响应无视频 URL: task_id={task_id}")

    out_dir = a.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%y%m%d_%H%M%S")
    dest = None
    for i, url in enumerate(urls, 1):
        path_suffix = Path(urlparse(url).path).suffix.lower()
        suffix = path_suffix if path_suffix in VIDEO_EXTS else ".mp4"
        name = f"vega_video_{stamp}{suffix}" if i == 1 else f"vega_video_{stamp}_{i}{suffix}"
        candidate = out_dir / name
        n = 2
        while candidate.exists():
            stem = f"vega_video_{stamp}_{n}" if i == 1 else f"vega_video_{stamp}_{i}_{n}"
            candidate = out_dir / f"{stem}{suffix}"
            n += 1
        dl = requests.get(url, timeout=DOWNLOAD_TIMEOUT, allow_redirects=True)
        if not dl.ok:
            raise RuntimeError(f"下载失败 HTTP {dl.status_code}: {url}")
        candidate.write_bytes(dl.content)
        if dest is None:
            dest = candidate
        print(f"downloaded[{i}]: {candidate} ({len(dl.content)} bytes)", file=sys.stderr)

    print(dest)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, RuntimeError, requests.RequestException, TencentCloudSDKException) as e:
        raise SystemExit(f"生成失败: {e}")

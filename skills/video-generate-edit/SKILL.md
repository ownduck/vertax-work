---
name: video-generate-edit
description: >-
  百炼单脚本出片：通过 scripts/run_video_generate.py 调用阿里云百炼 MiniMax-H3
  做文生视频、首尾帧图生视频或多模态参考生视频（一次提交轮询出本地路径）。
  VERTAX_VIDEO_GENERATER=default（或未设）时由 social-video-generate / social-long-video-generate 选用；
  与 video-generate-edit-comfyui（ComfyUI 双脚本）勿混用。
  在用户要求生视频、改视频、首尾帧、参考图/视频/音频生视频、MiniMax H3、Bailian 出片时使用。
  接收已就绪的提示词并提交；文案改写由上游完成。
---

# Video Generate Edit

只用本目录脚本调用 API，不要手写 curl/SDK。模型默认 `MiniMax/MiniMax-H3`。异步：脚本内提交一次并轮询下载，勿重复提交。

本 skill **不做** MiniMax H3 指南文案改写；`--prompt` / `--prompt-file` 视为已定稿（社媒向导场景下应由 `social-video-generate` 产出英文最终分镜）。

固定 API 根地址：`https://dashscope.aliyuncs.com/api/v1`（提交、轮询、本地素材上传均用此地址；不接受 endpoint / 工作空间 ID / 自定义 Base URL）。

## 流程

1. 缺依赖时安装：`python -m pip install -r "<技能目录>/scripts/requirements.txt"`
2. 确认 Key：`VERTAX_DASHSCOPE_API_KEY`（优先）或 `DASHSCOPE_API_KEY`
3. 按用户意图组素材参数（见下），传入已定稿提示词，执行 `run_video_generate.py`
4. 读取 stdout 的本地视频绝对路径交付；stderr 可能有 `task_id` / `request_id`

## 模式选择（以百炼入参为准）

| 百炼场景 | CLI / `media.type` |
|---|---|
| 文生视频 | 不传素材；`--ratio` 须具体比例（默认 `9:16`） |
| 图生-首帧 | `--first-image` → `first_frame` |
| 图生-尾帧 | `--last-image` → `last_frame` |
| 图生-首尾帧 | `--first-image` + `--last-image` |
| 多模态参考生视频 | `--image1`～`--image3` → `image_url`；`--video1` → `feature`；`--audio1` → `driving_audio` |

**互斥**：`first_frame`/`last_frame` 与 `image_url`/`feature`/`driving_audio` 不可混用。

## 参数规则（必须遵守）

- `--prompt` 与 `--prompt-file`：**二选一必填**。
- `--image1`～`--image3`：可选参考图；本地路径或 http(s) URL。图序须连续。
- `--first-image`、`--last-image`：可选首/尾帧；本地路径或 http(s) URL。
- `--video1`、`--audio1`：可选参考视频 / 音频；本地路径或 http(s) URL。
- 本地素材文件名不能重复；本地文件脚本会上传为临时 `oss://` URL（须与模型同 Key）。
- `--model`：默认 `MiniMax/MiniMax-H3`；非必要勿改。
- `--size`：默认 `768P`；可选 `2K`（对应 API `resolution`）。
- `--ratio`：默认 `9:16`；可选 `adaptive` / `16:9` / `9:16` / `1:1` / `4:3` / `3:4` / `21:9`。
- `--duration`：默认 `10`；整数，**最小 4、最大 15**（秒）；超过 15 须拒绝并请用户改为 ≤15。
- `--output-dir`：默认 `./output`；建议绝对路径。
- 脚本固定：`watermark=false`。提示词不超过 7000 字符。

## 命令示例

```sh
python "<技能目录>/scripts/run_video_generate.py" --prompt-file "prompt.txt" --output-dir "F:/data/out"
```

```sh
python "<技能目录>/scripts/run_video_generate.py" --first-image "F:/refs/start.png" --last-image "F:/refs/end.png" --prompt-file "prompt.txt" --duration 8 --output-dir "F:/data/out"
```

```sh
python "<技能目录>/scripts/run_video_generate.py" --image1 "a.png" --image2 "https://example.com/b.png" --video1 "ref.mp4" --prompt-file "prompt.txt" --size 768P --ratio 9:16 --output-dir "./output"
```

## 交付与失败

- **成功**：把 stdout 本地视频路径交给用户（远端 `video_url` 约 30 天，勿当长期存储）。
- **失败**：返回完整报错（含 `task_id` / `request_id`）；检查 Key、素材、互斥与 duration。
- 不要为等待而重跑同一任务。

API 说明见：[MiniMax 视频生成](https://docs.bailian.console.aliyun.com/zh/model-studio/minimax-video-generation-api-reference)

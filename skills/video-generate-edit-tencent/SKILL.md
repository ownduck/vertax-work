---
name: video-generate-edit-tencent
description: >-
  腾讯云 VOD 单脚本出片：通过 scripts/run_video_generate.py 调用 Vega-Video Lite
  （wand-vega-video / 1.0-lite）做文生视频、首尾帧图生视频或多模态参考生视频
  （一次提交轮询出本地路径）。
  VERTAX_VIDEO_GENERATER=tencent 时可作 social-video-generate / social-long-video-generate 出片后端；
  与 video-generate-edit（百炼）、video-generate-edit-comfyui（ComfyUI）勿混用。
  在用户要求腾讯云/VOD/Vega 生视频、改视频、首尾帧、参考图/视频/音频生视频时使用。
  接收已就绪的提示词并提交；文案改写由上游完成。
---

# Video Generate Edit Tencent

只用本目录脚本调用腾讯云点播 API，不要手写 curl/SDK。模型默认 `wand-vega-video` / `1.0-lite`。异步：脚本内提交一次并轮询下载，勿重复提交。

本 skill **不做** 提示词/分镜文案改写；`--prompt` / `--prompt-file` 视为已定稿。

固定接口域名：`vod.tencentcloudapi.com`（`CreateAigcVideoTask` + `DescribeTaskDetail`；本地素材经 `ApplyUpload` / COS / `CommitUpload`）。

## 流程

1. 缺依赖时安装：`python -m pip install -r "<技能目录>/scripts/requirements.txt"`
2. 确认凭证：
   - `VERTAX_TENCENTCLOUD_SECRET_ID`（优先）或 `TENCENTCLOUD_SECRET_ID`
   - `VERTAX_TENCENTCLOUD_SECRET_KEY`（优先）或 `TENCENTCLOUD_SECRET_KEY`
   - `VERTAX_TENCENTCLOUD_VOD_SUB_APP_ID`（优先）或 `TENCENTCLOUD_VOD_SUB_APP_ID`（默认 `1442456629`）
3. 按用户意图组素材参数（见下），传入已定稿提示词，执行 `run_video_generate.py`
4. 读取 stdout 的本地视频绝对路径交付；stderr 可能有 `task_id` / `request_id` / 进度

## 模式选择（以 VOD FileInfos.Usage 为准）

| 场景 | CLI / `Usage` |
|---|---|
| 文生视频 | 不传素材；`--ratio` 须具体比例（默认 `9:16`，不能 `adaptive`） |
| 图生-首帧 | `--first-image` → `FirstFrame` |
| 图生-尾帧 | 不可单独尾帧；须 `--first-image` + `--last-image` |
| 图生-首尾帧 | `--first-image` + `--last-image` |
| 多模态参考生视频 | `--image1`～`--image3` / `--video1` / `--audio1` → `Reference` |

**互斥**：首尾帧（`FirstFrame`/`LastFrame`）与参考素材（`Reference`）不可混用。  
**音频**：`--audio1` 须配合参考图/视频，不能单独输入。

## 参数规则（必须遵守）

- `--prompt` 与 `--prompt-file`：**二选一必填**。
- `--image1`～`--image3`：可选参考图；本地路径或 http(s) URL。图序须连续。
- `--first-image`、`--last-image`：可选首/尾帧；本地路径或 http(s) URL。
- `--video1`、`--audio1`：可选参考视频 / 音频；本地路径或 http(s) URL。
- 本地素材文件名不能重复；本地文件脚本会上传到 VOD 得到 `FileId`（须与同一套 AK/SK、`SubAppId`）。
- `--model`：默认 `wand-vega-video`；非必要勿改。
- `--model-version`：默认 `1.0-lite`。
- `--size`：默认 `768P`；可选 `480P` / `768P` / `1080P` / `2K` / `4K`（对应 `OutputConfig.Resolution`）。
- `--ratio`：默认 `9:16`；可选 `adaptive` / `16:9` / `9:16` / `1:1` / `4:3` / `3:4` / `21:9`。
- `--duration`：默认 `10`；整数，**最小 4、最大 15**（秒）；超过 15 须拒绝并请用户改为 ≤15。
- `--output-dir`：默认 `./output`；建议绝对路径。
- `--enhance-prompt`：默认 `enable`（`ExtInfo.EnhancePromptMode`）；可选 `disable`。
- `--generate-mode`：可选 `Standard` / `Fast` / `StandardMovie`。
- `--quality-mode`：可选 `Standard` / `Fast` / `SuperFast`。
- `--audio-generation`：默认 `Enabled`。
- 提示词不超过 7000 字符。输出 `StorageMode=Temporary`。

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

- **成功**：把 stdout 本地视频路径交给用户（临时存储 URL 勿当长期存储）。
- **失败**：返回完整报错（含 `task_id` / `request_id`）；检查 AK/SK、`SubAppId`、素材、互斥与 duration。
- 不要为等待而重跑同一任务。

API 说明见：[创建 AIGC 生视频任务](https://cloud.tencent.com/document/product/266/126239)、[查询任务详情](https://cloud.tencent.com/document/product/266/34129)。

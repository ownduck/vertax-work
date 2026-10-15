---
name: video-generate-edit-comfyui
description: >-
  ComfyUI 双脚本出片：healthcheck → run.py（prompt_id）→ get_result.py（本地路径）；
  单一工作流模板按参数动态删减空媒体节点，做文生/首尾帧/参考图生视频。
  VERTAX_VIDEO_GENERATER=comfyui 时由 social-video-generate / social-long-video-generate 选用；
  勿与百炼单脚本 video-generate-edit（run_video_generate.py）混用。
  在用户要求 ComfyUI 出片、MiniMax H3 本地/远程网关、不走百炼时使用。
  接收已就绪的提示词并提交；文案改写由上游完成。
---

# Video Generate Edit ComfyUI

只用本目录脚本调用 ComfyUI，不要手写 curl。本 skill **不做** MiniMax H3 指南文案改写；`--prompt` / `--prompt-file` 视为已定稿。

工作流模板：`assets/workflow-minimax-h3.json`。提交与取结果拆开：`run.py` 只提交一次并输出 `prompt_id`；`get_result.py` 轮询下载。勿因等待重复提交。

`run.py` 按传入媒体组合写入节点 8 的 `task_type`（不用模板默认 `auto`）：

| 条件 | task_type |
|---|---|
| 无首帧、无尾帧、无参考图 | `T2VA` |
| 仅首帧 | `I2VA` |
| 仅尾帧 | `L2VA` |
| 首帧+尾帧（无参考） | `FL2VA` |
| 仅参考图 | `Ref2VA` |
| 有参考图，且有首帧和/或尾帧 | `Hybrid` |

服务地址：`--comfyui-endpoint` → `VERTAX_COMFYUI_ENDPOINT` → `http://127.0.0.1:8188`。网关鉴权 Header `X-Token` 读自 `VERTAX_COMFYUI_TOKEN`（未设则不发送）。显式指定服务时各命令用同一地址。

## 流程

严格按「健康检查 → 提交 → 获取结果」。

### 1. 依赖与健康检查

```sh
python -m pip install -r "<技能目录>/scripts/requirements.txt"
python "<技能目录>/scripts/comfyui_healthcheck.py"
```

检查 `/system_stats`，退出码 0 才继续。接口可用不代表模型/节点齐全。

### 2. 提交任务（run.py）

```sh
python "<技能目录>/scripts/run.py" --prompt-file "提示词.txt" --duration 10 --ratio 9:16
python "<技能目录>/scripts/run.py" --first-image "首帧.png" --prompt-file "提示词.txt" --duration 8
python "<技能目录>/scripts/run.py" --image1 "a.png" --image2 "b.png" --prompt "短提示词" --duration 12 --ratio 16:9
```

成功时 stdout 最后一行为 `prompt_id: <任务ID>`。保存 ID，进入下一步。

### 3. 轮询并下载（get_result.py）

```sh
python "<技能目录>/scripts/get_result.py" --prompt-id "任务ID" --output-dir "F:/data/out"
```

按需加 `--comfyui-endpoint`。每 5 秒查 `/history` 与 `/queue`，完成后从节点 16 `/view` 下载；stdout 打印本地绝对路径。可中断后用同一 `prompt_id` 续跑。

交付：把 stdout 本地视频路径交给用户。

## 参数规则（必须遵守）

- `--prompt` 与 `--prompt-file`：**二选一必填**。
- `--duration`：默认 `10`；整数 **4～15**；超过 15 须拒绝。写入工作流 Float (Duration)；内部按 24fps 对齐帧，成片可能略长于整数秒。
- `--ratio`：默认 `9:16`；可选 `16:9` / `9:16` / `1:1` / `4:3` / `3:4`。
- `--image1`～`--image3`：可选参考图，**本地路径**；图序须连续（有 `--image3` 须有 `--image2`，有 `--image2` 须有 `--image1`）。
- `--first-image`、`--last-image`：可选首/尾帧，本地路径。
- 素材文件名须互不相同。未传入的首帧 / 尾帧 / 参考图对应节点会从工作流中删除（空值会报错）。
- 允许任意组合（含纯文生、仅首帧、仅参考图、首尾帧+参考图混用）；不做百炼式互斥。
- `--output-dir`：仅 `get_result.py`；默认 `./output`；建议绝对路径。
- `--comfyui-endpoint`：可选；见上文解析顺序。

## 工作流节点

| 用途 | 节点 |
|---|---|
| 参考图 1 / 2 / 3 | 23 / 24 / 30 |
| 首帧 / 尾帧 | 32 / 33 |
| 提示词 | 29 |
| 时长 | 18 |
| 画幅 | 22 |
| 输出视频 | 16 |

## 交付与失败

- **成功**：`get_result.py` stdout 本地视频路径。
- **失败**：返回完整报错；检查 ComfyUI 是否可用、素材路径、图序、duration、节点是否安装。
- 不要为等待而重跑 `run.py`。

---
name: reference-to-video
description: 使用 ComfyUI MiniMax H3 将用户想法整理成英文提示词，并结合 1～3 张参考图与可选的 1 段参考视频生成或修改音视频。适用于参考生视频、视频修改、R2V。
---

# Reference to Video

需要 Python 3、`requests` 以及已安装对应模型和节点的 ComfyUI。缺少依赖时运行：

```sh
python -m pip install -r "<技能目录>/scripts/requirements.txt"
```

## 流程

严格按“健康检查 → 提交 → 获取结果”执行。三个脚本的服务地址优先级一致：`--comfyui-endpoint` → `COMFYUI_ENDPOINT` → `http://127.0.0.1:8188`。显式指定服务时，每条命令都传入同一地址。

### 1. 健康检查

```sh
python "<技能目录>/scripts/comfyui_healthcheck.py"
```

脚本检查 `/system_stats`，退出码为 0 才继续。接口可用不代表工作流所需模型和节点齐全。

### 2. 准备提示词

每次提交前完整阅读 [提示词指南](references/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)，查看所有参考素材，再把用户想法整理成适合视频生成的提示词：

- 用户要求修改已有视频时，优先将原视频通过 `--video1` 作为参考，保留其所需内容并描述修改目标；不要优先依靠文字反推原视频后从头生成。工作流仍需 `--image1`，用户未提供参考图时可从原视频提取合适的一帧。
- 提示词全文使用英文，包括对白、歌词和画面文字；自然翻译用户原意并保留笑点。
- 开头说明实际输入的 `Image 1`～`Image 3`、`Video 1` 的用途和参考范围，不引用缺失素材。
- 使用指南规定的 `integrated_multimodal_description`、`overall_soundscape`、`non_diegetic_music`；无配乐写 `N/A`。
- 按时长安排镜头、动作、运镜、说话人与 `<d>[English] Dialogue.</d>`。用户未要求对白时不要擅加。
- 保留用户指定的主体、风格和限制，只补充相容细节。检查英文、素材对应、时间与音画一致性，保存为 UTF-8 TXT。

指南[原文来源](https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)。

### 3. 提交任务

```sh
python "<技能目录>/scripts/run_r2v.py" --image1 "图1路径" --prompt "提示词.txt路径"
```

按需添加 `--image2`、`--image3`、`--video1`、`--duration`、`--comfyui-endpoint`。图一必填；传图三时必须同时传图二。当前支持一段参考视频，使用 `--video1`；参考素材必须使用不同文件名。

`--duration` 默认 **8 秒**，支持正小数。工作流按 24 fps 对齐帧数，实际输出可能略长，例如 15 秒会生成 362 帧，约 15.083 秒。

`run_r2v.py` 只上传素材并提交一次任务，成功时最后输出 `prompt_id: <任务ID>`，不查询状态、不下载结果。保存这个 ID，不要因等待较久而重复提交。

### 4. 轮询并下载

```sh
python "<技能目录>/scripts/get_r2v_result.py" --prompt-id "任务ID"
```

按需添加 `--output-dir "下载目录"` 和 `--comfyui-endpoint "服务地址"`。脚本每 5 秒查询 `/history` 和 `/queue`，完成后从 `/view` 下载节点 16 的视频；默认保存到当前目录的 `output/`，避免覆盖已有文件，并输出保存文件的绝对路径。它不会上传素材或调用 `/prompt`，中断后可用同一 `prompt_id` 再次运行。

根据 15 秒视频的历史经验，生成通常至少需要约 5 分钟，也可能持续 20 分钟。只有工作流明确报错、任务不存在或服务不可恢复时才报告失败。

直接交付 ComfyUI 原始输出和提示词文件。即使帧数对齐导致视频略长，也不要自行裁剪或改变时长；用户明确要求后处理时才执行，并保留原始文件。

## 工作流对应

脚本按素材数量自动选择工作流：

| 工作流 | 图片 | 视频 | 输入节点 |
|---|---:|---:|---|
| `workflow-r2v-minimax-h3-1i.json` | 1 | 0 | 图 23 |
| `workflow-r2v-minimax-h3-2i.json` | 2 | 0 | 图 23、24 |
| `workflow-r2v-minimax-h3-3i.json` | 3 | 0 | 图 23、24、30 |
| `workflow-r2v-minimax-h3-1i1v.json` | 1 | 1 | 图 23；视频 26 |
| `workflow-r2v-minimax-h3-2i1v.json` | 2 | 1 | 图 23、24；视频 26 |
| `workflow-r2v-minimax-h3-3i1v.json` | 3 | 1 | 图 23、24、30；视频 26 |

固定节点：时长 18、提示词 29、输出 16。模板为 9:16、24 fps、8 步采样和固定种子。参考视频的画面与音频参与条件控制，不会直接拼接原音轨。

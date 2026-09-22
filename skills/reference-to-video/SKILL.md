---
name: reference-to-video
description: 使用 ComfyUI MiniMax H3 将用户想法整理成英文提示词，并结合 1～3 张参考图与可选的 1 段参考视频生成或修改音视频。适用于参考生视频、视频修改、R2V。
---

# Reference to Video

需要 Python 3、`requests` 以及已安装对应模型和节点的 ComfyUI。缺少依赖时运行：

```sh
python -m pip install -r "<技能目录>/scripts/requirements.txt"
```

## 执行前确认（HITL）

提交前按序确认；缺项则停住询问，勿猜测继续。

### 1. 参考图

- 已提供：按用户顺序用作 `Image 1`～`Image 3`（至少 1 张，最多 3 张）。
- 未提供：先问选项「提供一张 / 两张 / 三张」（至少一张）；选定后按顺序索要图片。
- 改已有视频仍需 `--image1`；用户坚持不给图时，才可从 `--video1` 原视频抽一帧顶替。

### 2. 时长

- 用户未提时长 → 默认 **10 秒**。
- 上限 **15 秒**；若要求 >15 秒，拒绝并请改为 ≤15。

### 3. 提示词 / 剧本

- 已提供剧本或完整提示词 → 直接采用。
- 未提供：先问「指定剧本 / 自行生成有趣的段子」。
  - 自行生成 → 先写出有趣短段子，再进入分镜提示词。
  - 指定剧本 → 等用户给出剧本后再写分镜提示词。
- 写提示词前完整阅读 [MiniMax H3 指南](references/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)。
- 用指定/自编剧本生成符合指南的英文分镜提示词；分镜数：
  - 时长 ≤5s → ≥3 镜
  - 5s < 时长 ≤10s → ≥5 镜
  - 10s < 时长 ≤15s → ≥5 镜

## 流程

严格按「健康检查 → 提交 → 获取结果」。服务地址：`--comfyui-endpoint` → `VERTAX_COMFYUI_ENDPOINT` → `http://127.0.0.1:8188`。显式指定时三条命令用同一地址。

### 1. 健康检查

```sh
python "<技能目录>/scripts/comfyui_healthcheck.py"
```

检查 `/system_stats`，退出码 0 才继续。接口可用不代表模型/节点齐全。

### 2. 准备提示词

- 改已有视频：优先 `--video1`，描述修改目标；勿仅靠文字反推后从头生成。
- 全文英文（含对白、歌词、画面文字）；翻译原意并保留笑点。
- 开头说明实际输入的 `Image 1`～`Image 3`、`Video 1` 用途；不引用缺失素材。
- 含 `integrated_multimodal_description`、`overall_soundscape`、`non_diegetic_music`（无配乐写 `N/A`）。
- 按时长写镜头、动作、运镜、说话人与 `<d>[English] Dialogue.</d>`；用户未要求对白则不加。
- 保留用户指定主体/风格/限制；检查英文、素材对应、时间与音画一致性；存 UTF-8 TXT。

指南[原文来源](https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)。

### 3. 提交任务

```sh
python "<技能目录>/scripts/run_r2v.py" --image1 "图1路径" --prompt-file "提示词.txt路径"
python "<技能目录>/scripts/run_r2v.py" --image1 "图1路径" --prompt "短提示词"
```

按需加 `--image2`、`--image3`、`--video1`、`--duration`、`--comfyui-endpoint`。图一必填；传图三须同时传图二。参考视频用 `--video1`。素材文件名须互不相同。`--prompt` 与 `--prompt-file` **二选一必填**（短文本用前者，长文本用文件）。

`--duration` 默认 10，上限 15；按 24 fps 对齐，实际可能略长（如 15s → 362 帧 ≈ 15.083s）。

`run_r2v.py` 只上传并提交一次，成功时最后输出 `prompt_id: <任务ID>`。保存 ID，勿因等待重复提交。

### 4. 轮询并下载

```sh
python "<技能目录>/scripts/get_r2v_result.py" --prompt-id "任务ID"
```

按需加 `--output-dir`、`--comfyui-endpoint`。每 5 秒查 `/history` 与 `/queue`，完成后从 `/view` 下载节点 16；默认存当前目录 `output/`，避免覆盖并输出绝对路径。可中断后用同一 `prompt_id` 续跑。

15 秒片常见约 5–20 分钟。仅工作流报错、任务不存在或服务不可恢复时判失败。

直接交付原始输出与提示词文件；勿擅自裁剪时长。

## 工作流对应

| 工作流 | 图片 | 视频 | 输入节点 |
|---|---:|---:|---|
| `workflow-r2v-minimax-h3-1i.json` | 1 | 0 | 图 23 |
| `workflow-r2v-minimax-h3-2i.json` | 2 | 0 | 图 23、24 |
| `workflow-r2v-minimax-h3-3i.json` | 3 | 0 | 图 23、24、30 |
| `workflow-r2v-minimax-h3-1i1v.json` | 1 | 1 | 图 23；视频 26 |
| `workflow-r2v-minimax-h3-2i1v.json` | 2 | 1 | 图 23、24；视频 26 |
| `workflow-r2v-minimax-h3-3i1v.json` | 3 | 1 | 图 23、24、30；视频 26 |

固定节点：时长 18、提示词 29、输出 16。模板 9:16、24 fps、8 步、固定种子。参考视频音画仅作条件控制，不直接拼原音轨。

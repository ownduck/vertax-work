---
name: image-generate-edit
description: >-
  通过 scripts/run_image_generate.py 调用阿里云百炼千问图像 3.0 做文生图（T2I）或图生图/编辑（I2I）。
  在用户要求画图、生图、改图、换装、换背景、参考图生成、Qwen Image、DashScope 出图时使用。
---

# Image Generate Edit

只用本目录脚本调用 API，不要手写 curl/SDK。同步接口，耗时可能数分钟，超时已设 600s，勿重复提交。

## 流程

1. 缺依赖时安装：`python -m pip install -r "<技能目录>/scripts/requirements.txt"`
2. 确认 Key 可用：`VERTAX_DASHSCOPE_API_KEY`（优先）或 `DASHSCOPE_API_KEY`
3. 根据用户意图组参数（见下），执行 `run_image_generate.py`
4. 读取 stdout 的本地图片绝对路径，交付给用户；stderr 可能有 `request_id`

## 模式选择

| 场景 | 做法 |
|---|---|
| 纯文生图 | 只传 `--prompt` 或 `--prompt-file`，不传图 |
| 参考图编辑 / 图生图 | `--image1`（可选 `--image2`、`--image3`）+ 编辑/生成说明 |
| 短提示词 | `--prompt "..."` |
| 长提示词 | 写入 UTF-8 TXT，用 `--prompt-file` |
| 日常出图 | 默认即可（`qwen-image-3.0`） |
| 更高质量 / 更复杂版面 | `--model qwen-image-3.0-pro` |

## 参数规则（必须遵守）

- `--prompt` 与 `--prompt-file`：**二选一必填**，不能同时传，也不能都不传。
- `--negative-prompt` 与 `--negative-prompt-file`：可选，互斥。
- `--image1`～`--image3`：均非必填；值为**本地路径**或 **http(s) 公网 URL**。URL 原样上传，本地文件脚本会转 Base64。
- 图序须连续：有 `--image2` 必须有 `--image1`；有 `--image3` 必须有 `--image1` 和 `--image2`。
- 多张本地参考图文件名不能重复。
- `--model`：默认 `qwen-image-3.0`（日常使用）；`qwen-image-3.0-pro` 用于更高质量要求、更复杂版面。
- `--output-dir`：默认 `./output`；建议写成绝对路径，避免工作目录混乱。
- `--endpoint` 或环境变量 `DASHSCOPE_HTTP_BASE_URL`：默认 `https://dashscope.aliyuncs.com/api/v1`；须与 API Key **同地域**。

脚本固定：`n=1`、`watermark=false`，分辨率由模型自荐；开启 `prompt_extend`。

## 命令示例

文生图：

```sh
python "<技能目录>/scripts/run_image_generate.py" --prompt "一只橘猫坐在窗台上看雨" --output-dir "F:/data/out"
```

图生图 / 编辑：

```sh
python "<技能目录>/scripts/run_image_generate.py" --image1 "F:/refs/person.png" --prompt "保持面部特征，换成黑色西装，站在现代办公室" --model qwen-image-3.0-pro --output-dir "F:/data/out"
```

多参考图 + 文件提示词：

```sh
python "<技能目录>/scripts/run_image_generate.py" --image1 "a.png" --image2 "https://example.com/b.png" --prompt-file "prompt.txt" --negative-prompt "模糊, 低质量" --output-dir "./output"
```

## 写提示词时

- 直接把用户意图写成清晰的中文或英文提示词；用户已给完整 prompt 则原样使用。
- I2I：写明**保留什么**（脸、服装、构图）和**改什么**（场景、动作、风格）。
- 多图时在 prompt 里说明各图用途（如「图1人物身份，图2服装样式」），与传入顺序一致。
- 需要规避的内容用 `--negative-prompt`，不要塞进正向 prompt。

## 交付与失败

- **成功**：把 stdout 打印的本地路径交给用户（脚本已下载；远端 URL 仅约 24h）。
- **失败**：把完整报错（含 `request_id`）返回；检查 Key、地域/endpoint、图是否公网可达、参数是否违反二选一/图序。
- 不要为「等太久」而重跑同一任务；一次失败修好参数后再提交。

API 说明见：[千问图像生成与编辑 3.0](https://docs.bailian.console.aliyun.com/zh/model-studio/qwen-image-generation-and-editing-api-reference)

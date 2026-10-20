---
name: social-long-video-generate
description: >-
  社媒长视频向导（总时长 16～60s，未指定时默认 30s）：按分镜在明确切镜/换场处切成多段 ≤15s，
  每段用 image-generate-edit 生成独立首帧（统一 1024x1680，不做尾帧），
  再按 VERTAX_VIDEO_GENERATER 选择出片后端后 ffmpeg 硬切拼接
  （comfyui → video-generate-edit-comfyui；tencent → video-generate-edit-tencent；default/未设 → video-generate-edit）。
  未说明的参数一律用默认；主题/商品可自行随机；尽量不 HITL。
  默认英文（含口播）与美国人设；>15s 用本技能，≤15s 用 social-video-generate。
---

# Social Long Video Generate

编排向导。刻意采用**剪辑式**长片：段边界是分镜切镜点，相邻段首帧构图不同；**不做**「上一段末帧 → 下一段首帧」链式续写。

## 默认与 HITL（统一总则）

用户未明确说明时，**全部用默认值，尽量不 HITL、不停问**，自行选定后直接往下跑：

| 项 | 默认 / 行为 |
|---|---|
| 方向 | 未提商品/带货/开箱/卖点 → **故事向**；用户明确商品向才走 product |
| 主题（故事） | **自行随机**一个具体、可拍完的创意；勿追问主题 |
| 商品（商品向） | **自行随机**一个具体虚构商品（品类+外观+2～3个可演示卖点），按假设概念稿写，勿因缺商品资料 HITL |
| 时长 T | **30s**（用户指定则取 16～60） |
| 语言 | 英文（含口播 `<d>[English]`） |
| 人物 | 美国人 |
| 画幅 | 首帧 `1024x1680`；出片 `--ratio 9:16`；`--size 768P` **仅 default（百炼）/ tencent** |

**仅在这些情况 HITL/停住**：下游 skill / ffmpeg 缺失；用户明确锁定了互相冲突且无法自行裁决的硬约束；目标时长 **>60**（请缩短或拆条）；≤15 改指 **social-video-generate**；`VERTAX_VIDEO_GENERATER` 为非法值。其余缺口一律用默认或自拟，不追问。

## 出片后端选择

读取环境变量 `VERTAX_VIDEO_GENERATER`（忽略大小写与首尾空白）：

| 值 | 出片 skill |
|---|---|
| `comfyui` | `video-generate-edit-comfyui` |
| `tencent` | `video-generate-edit-tencent` |
| `default` | `video-generate-edit` |
| 未设置 / 空 | 按 **`default`** |
| 其它 | HITL 停住，说明合法值仅为 `comfyui` / `tencent` / `default` |

差异摘要：`default` / `tencent` 均为单脚本出本地路径且可传 `--size`；`comfyui` 为 healthcheck → `run.py`（`prompt_id`）→ `get_result.py`（`--output-dir` 仅在此），无 `--size`，媒体仅本地路径。细节以所选 skill 为准。

下游：

| 步骤 | Skill / 脚本 |
|---|---|
| 剧情 | `social-video-script-story` 或 `social-video-script-product` |
| 分镜 | `social-video-storyboard` |
| 每段首帧 | `image-generate-edit`（仅首帧，统一尺寸） |
| 每段出片 | 由 `VERTAX_VIDEO_GENERATER` 选择（仅 `--first-image`，无 `--last-image`） |
| 拼接 | 本目录 `scripts/concat_videos.py` |

文案改写摘要：[references/h3-prompt-copywriting.md](references/h3-prompt-copywriting.md)。

## 画幅硬约束

| 侧 | 锁定 |
|---|---|
| 出图 | 全片所有首帧 `--size 1024x1680`（段段相同） |
| 出片 | 全片 `--ratio 9:16`；**default** / **tencent** 另传 `--size 768P`（可全片统一改 `2K`，不得段间混用）；**comfyui** 不传 `--size` |
| 首尾帧 | **只传首帧**；禁止为本向导生成或传入尾帧；禁止抽上一段视频末帧当下一段首帧 |

用户参考图尺寸不一：用 `image-generate-edit` 以 `1024x1680` 重绘后再作首帧。无参考图则纯文生首帧，勿追问。

## 流程（严格按序）

### 1. 定方向与时长（无 HITL）

- 方向与 T 按上表默认；用户已说明则从其指定。
- **不要**为故事/商品、主题、商品型号、时长再问用户。
- 同时按上文选定出片后端。

### 2. 剧情与全片分镜

1. 按方向调用剧本 skill（英文默认）。调用时**必须传入目标时长 T**，并要求：
   - **故事**：自由创作；主题自行随机；直接成稿。
   - **商品**：无用户商品时自行随机虚构商品并成稿；**覆盖**该 skill「资料不足则 HITL」——本向导场景优先自拟，不暂停。
   - 信息量与节拍按 **约 T 秒可演完** 来写（遵循该 skill 的时长预算检查）。
   - **T 偏长（如 30～60s）**：要有足够事件/演示节拍与切镜空间，能支撑多镜短镜拆分；**禁止**只写够 10s 的短故事却标成 30s。
   - **T 偏短（如 16～20s）**：控制事件与对白密度，**禁止**写成明显超时、无法在 T 内演完的长剧本。
   - 交付前按时长可行自检；硬性台词与 T 冲突时说明。
2. 调用 `social-video-storyboard` 时明确要求：**按视觉任务拆成多镜短镜**，覆盖 **0～T**；**禁止**整片写成一两段「一镜到底」的长镜头表。分镜总时长必须贴合 T，不故意缩短或拉超时码。
   - 单镜时长宜短、可剪：社媒节奏下多数镜约 **2～8 秒**；单镜一般 **不超过 15 秒**（否则本向导无法在切镜点切开，也无法合法切段）。
   - 每镜一个主要视觉任务；换景别 / 换主体关注点 / 换场 / 新信息揭示处必须切镜。
   - 每镜标清切镜理由与时间范围，保证全片有**足够切镜点**供下一步打包。

### 3. 按切镜点切段（生成段 ≠ 单镜）

- **分镜镜** = 剪辑上的短镜头；**生成段** = 一次所选后端的出片调用（4～15s），可由 **1 镜或多镜相邻短镜** 打包而成。
- 只在分镜**切镜/换场**边界划分生成段 `S1…Sk`；每段 `d_i ∈ [4, 15]`，各段之和接近 T。
- **`d_i` 由该段打包的分镜内容量决定**（动作节拍、对白长度、换场需要），再取整到合法秒数；`--duration` 必须等于该 `d_i`。
- **禁止**把「T ÷ N 等分」（如 40÷5=全 8s）当作默认切段策略。仅当各段内容量确实接近时，才允许多段同秒；内容疏密不同时，`d_i` **应有长短差异**（例如有的 6～7s、有的 10～12s）。
- 相邻**生成段**的开场构图必须可区分（不同景别/机位/场景）；禁止「同一构图假连续」。
- 对白/口播不跨生成段切断。
- 若分镜几乎无切镜点（一整段长镜）：退回 storyboard **重拆多镜**，勿硬切长镜中段。

写出切段表（含：打包了哪些镜号、时间、**各段 d_i**、开场构图一句话）后再往下。切段表里的秒数必须与后续 `--duration` 一致，勿事后统一改成同一秒数。

### 4. 每段首帧（image-generate-edit）

对每一段：

1. 完整阅读并遵循 **image-generate-edit**。
2. `--size 1024x1680`；竖屏；人物/服装与全片设定一致。
3. prompt 描述**该段开场静帧**（与上一段首帧构图不同）。
4. 保存路径写入切段表；确认全部首帧尺寸一致。

**不**生成尾帧图。

### 5. 每段 H3 英文定稿

1. 读 [references/h3-prompt-copywriting.md](references/h3-prompt-copywriting.md)。
2. 每段独立文件：首帧对齐句（I2VA）+ `integrated_multimodal_description` / `overall_soundscape` / `non_diegetic_music`。
3. 该段时间线从 `0.00` 到 `d_i`；口播 `<d>[English] ...</d>`。
4. 只做文案改写；忽略 API 技术细节。

### 6. 逐段出片（串行）

**禁止** `--last-image`。一段成功后再下一段；保存各段 mp4 绝对路径。完整阅读并遵循所选出片 skill。

#### 6a. `default` → video-generate-edit

对每一段调用 `scripts/run_video_generate.py`：

```text
--first-image <该段首帧PNG>
--prompt-file <该段英文定稿>
--duration <d_i>
--ratio 9:16
--size 768P
--output-dir <段输出目录>
```

#### 6b. `tencent` → video-generate-edit-tencent

对每一段调用 `scripts/run_video_generate.py`（参数同 6a：`--first-image` / `--prompt-file` / `--duration` / `--ratio 9:16` / `--size 768P` / `--output-dir`）。

#### 6c. `comfyui` → video-generate-edit-comfyui

1. 全片出片开始前跑一次 `scripts/comfyui_healthcheck.py`（退出码 0 才继续）。
2. 对每一段：
   - `scripts/run.py --first-image … --prompt-file … --duration <d_i> --ratio 9:16`（**勿传** `--size`；图仅本地路径）→ 保存 `prompt_id`
   - `scripts/get_result.py --prompt-id … --output-dir <段输出目录>` → 保存本地 mp4 路径

### 7. 硬切拼接

```sh
python "<本技能目录>/scripts/concat_videos.py" --list segments.txt --output "long.mp4"
```

`segments.txt`：每行一个段视频绝对路径，按时间顺序。脚本硬切拼接；若段间分辨率不一致会先统一 scale。系统需已安装 **ffmpeg**。

### 8. 交付

1. 长片本地绝对路径。
2. 切段表、各段首帧图、各段 prompt、各段 mp4 路径（便于重跑单段）。

## 注意

- 本向导是剪辑语法，不是末帧续写；接缝应读作正常切镜。
- 无切段表 / 无齐套首帧 / 无各段英文定稿前，不出片、不拼接。
- 下游 skill 缺失时停住告知，勿发明替代规范。

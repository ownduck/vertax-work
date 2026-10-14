---
name: social-video-generate
description: >-
  社媒短视频创建核心向导（总时长 ≤15s，未指定默认 10s）：先用 social-video-script-story 或 social-video-script-product 出剧情，
  再用 social-video-storyboard 出分镜，按 MiniMax H3 指南做英文文案改写后，调用 video-generate-edit 出片。
  未说明的参数一律用默认；主题/商品可自行随机；尽量不 HITL。全链路默认英文（含口播）与美国人设。
  目标时长 >15s 时改用 social-long-video-generate。
  在用户要做社媒短视频、TikTok/Reels/Shorts、带货/故事向竖屏成片向导时使用。
---

# Social Video Generate

编排向导。自身不直接调百炼；按序调用下游 skill。

**时长**：本技能仅 **≤15s**。用户未指定时长时 **默认 10 秒**。目标总时长 **>15s**（至 60s）改用 **social-long-video-generate**。

## 默认与 HITL（统一总则）

用户未明确说明时，**全部用默认值，尽量不 HITL、不停问**，自行选定后直接往下跑：

| 项 | 默认 / 行为 |
|---|---|
| 方向 | 未提商品/带货/开箱/卖点 → **故事向**；用户明确商品向才走 product |
| 主题（故事） | **自行随机**一个具体、可拍完的创意；勿追问主题 |
| 商品（商品向） | **自行随机**一个具体虚构商品（品类+外观+2～3个可演示卖点），按假设概念稿写，勿因缺商品资料 HITL |
| 时长 T | **10s**（用户指定则取 4～15） |
| 语言 | 英文（含口播 `<d>[English]`） |
| 人物 | 美国人 |
| 画幅 | `--ratio 9:16` |

**仅在这些情况 HITL/停住**：下游 skill 缺失；用户明确锁定了互相冲突且无法自行裁决的硬约束；目标时长 >15s（改指 long 向导）。其余缺口一律用默认或自拟，不追问。

下游：

| 步骤 | Skill |
|---|---|
| 剧情 | `social-video-script-story` 或 `social-video-script-product` |
| 分镜 | `social-video-storyboard` |
| 出片 | `video-generate-edit` |

文案改写参考：[MiniMax H3 Video Prompt Writing Guide](https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)（**仅文案结构与写法**；忽略接口/模型技术细节）。本地摘要见 [references/h3-prompt-copywriting.md](references/h3-prompt-copywriting.md)。

## 流程（严格按序）

### 1. 生成短视频剧情

确定 T 与方向（见上表），**不要**为方向/主题/商品/时长再问用户。

| 方向 | 调用 |
|---|---|
| 故事（默认） | 完整阅读并遵循 **social-video-script-story**：自由创作；主题自行随机；直接成稿 |
| 商品 | 完整阅读并遵循 **social-video-script-product**：无用户商品时自行随机虚构商品并成稿；**覆盖**该 skill「资料不足则 HITL」——本向导场景优先自拟，不暂停 |

调用剧本 skill 时**必须传入目标时长 T**，并要求：

- 故事信息量、事件节拍、对白/旁白长度按 **约 T 秒可演完** 来写（遵循该 skill 的时长预算检查）。
- **T 较短（如 4～8s）**：情节要更紧，少事件、少对白，宁可留反应停顿，**禁止**塞满会超时的信息。
- **T 接近上限（如 10～15s）**：要有足够可见推进与收束，**禁止**写成只有一两拍、撑不满 T 的空壳（也不要为凑满而注水重复）。
- 交付前按该 skill「时长可行」自检；台词与 T 冲突时说明，不 silently 删锁定内容。

产出：该 skill 规定的剧情文本（保留原文供下一步）。未完成勿进入第 2 步。

### 2. 生成分镜

把第 1 步剧情交给 **social-video-storyboard**（完整阅读并遵循该 skill）。  
产出：分镜稿。未完成勿进入第 3 步。

### 3. 按 H3 指南改写最终分镜（仅文案）

1. 打开指南（优先读本地 [references/h3-prompt-copywriting.md](references/h3-prompt-copywriting.md)；细节不够再读 HF 原文文案章节）。
2. **只做文案改写**：结构、镜号叙述、动作、运镜自然语言、声画与对白标记、三核心字段等。  
   **忽略**：API、endpoint、分辨率、上传、计费、节点、工作流等技术特性。
3. 按实际素材决定是否写首/尾帧对齐句（有首帧/尾帧/首尾帧时用指南对应模板；纯文生或普通参考图不写关键帧对齐套话）。
4. 改写结果必须含：
   - `integrated_multimodal_description`（含 `[Shot n]` 时间线）
   - `overall_soundscape`
   - `non_diegetic_music`（无配乐写 `N/A`）
5. 写入 UTF-8 TXT，作为「最终分镜 / 最终 prompt」。

### 4. 最终输出默认英文（含口播音频）

本步定稿即交给出片模型的最终内容，**必须全部为英文**，并保证成片语音也是英文：

- **文本**：叙述、镜头说明、声画描述、三核心字段内容均为英文（字段名用指南英文标签）。
- **口播 / 对白 / 旁白（成片音频）**：默认英文，写成 `<d>[English] ...</d>`。模型据此合成/表演的说话声即为英文口播；**禁止**在未获用户锁定时提交中文或其它语种口播。
- 上游若仍出现非英文：定稿前全部译成自然英文，保留语气、笑点与卖点；不要指望出片阶段再改语言。
- 仅当用户**明确锁定**非英文台词（或明确要求保留某语种口播）时，才用对应语言标签并原样保留，不擅自改词。
- 画内招牌等需显示的原文可放在英文双引号内保留字符——**这不等于口播可以非英文**。

### 5. 调用 video-generate-edit 出片

1. 完整阅读并遵循 **video-generate-edit**（参数、互斥、Key、落盘等以其为准）。
2. 将第 4 步定稿的英文最终分镜作为 `--prompt-file`（推荐）传入；按用户素材传 `--image*` / `--first-image` / `--last-image` / `--video1` / `--audio1` 等（无素材则纯文生，勿追问）。
3. 提交前再扫一眼：所有 `<d>` 块在默认情况下均为 `[English]`；勿再在 `video-generate-edit` 侧做文案改写。
4. 交付：视频本地绝对路径；可附最终 prompt 文件路径。交付物中的说话声默认应为英文口播。

## 注意

- 无剧情、无分镜、无英文定稿（含英文口播）前，不调用 `video-generate-edit`。
- 下游 skill 缺失时：停住告知用户，勿自行发明整套剧本/分镜规范替代。
- 竖屏社媒默认：`video-generate-edit` 的 `--ratio 9:16`；时长未指定用 **10s**，用户指定则取其值（须在 4～15s）。
- 目标时长 >15s：停用本技能流程，改读并遵循 **social-long-video-generate**。
- 下游 `social-video-script-*` / `social-video-storyboard` 亦默认英文、人物默认美国人；向导与下游约定一致，避免上游交中文/非默认人物、末端再补救。

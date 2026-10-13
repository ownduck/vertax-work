---
name: social-video-generate
description: >-
  社媒短视频创建核心向导：先用 social-video-script-story 或 social-video-script-product 出剧情，
  再用 social-video-storyboard 出分镜，按 MiniMax H3 指南做英文文案改写后，调用 video-generate-edit 出片。
  全链路默认英文（含剧情、分镜、最终 prompt，以及成片口播/对白/旁白音频）；出镜人物默认美国人。
  在用户要做社媒短视频、TikTok/Reels/Shorts、带货/故事向竖屏成片向导时使用。
---

# Social Video Generate

编排向导。自身不直接调百炼；按序调用下游 skill。缺依赖 skill 或关键输入时 HITL 停问，勿跳步。

**默认总则**：

- **语言**：最终成片相关输出 **默认英文**——含剧情正文、分镜、H3 定稿 prompt，以及 **口播 / 对白 / 旁白音频**（`<d>[English] ...</d>`）。仅用户明确锁定其它语种时例外。
- **人物**：未指定国籍/外观且无人物参考时，出镜人物 **默认美国人**；用户指定或提供参考时从其指定。下游 script/storyboard skill 同样遵守。

下游：

| 步骤 | Skill |
|---|---|
| 剧情 | `social-video-script-story` 或 `social-video-script-product` |
| 分镜 | `social-video-storyboard` |
| 出片 | `video-generate-edit` |

文案改写参考：[MiniMax H3 Video Prompt Writing Guide](https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)（**仅文案结构与写法**；忽略接口/模型技术细节）。本地摘要见 [references/h3-prompt-copywriting.md](references/h3-prompt-copywriting.md)。

## 流程（严格按序）

### 1. 生成短视频剧情

HITL：故事向 or 带货/产品向（未选则停住）：

| 选择 | 调用 |
|---|---|
| 故事 / 剧情 / 段子 / POV / 日常叙事 | 完整阅读并遵循 **social-video-script-story** |
| 商品 / 带货 / 种草 / 开箱 / 卖点 | 完整阅读并遵循 **social-video-script-product** |

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
2. 将第 4 步定稿的英文最终分镜作为 `--prompt-file`（推荐）传入；按用户素材传 `--image*` / `--first-image` / `--last-image` / `--video1` / `--audio1` 等。
3. 提交前再扫一眼：所有 `<d>` 块在默认情况下均为 `[English]`；勿再在 `video-generate-edit` 侧做文案改写。
4. 交付：视频本地绝对路径；可附最终 prompt 文件路径。交付物中的说话声默认应为英文口播。

## 注意

- 无剧情、无分镜、无英文定稿（含英文口播）前，不调用 `video-generate-edit`。
- 下游 skill 缺失时：停住告知用户，勿自行发明整套剧本/分镜规范替代。
- 竖屏社媒默认：`video-generate-edit` 的 `--ratio 9:16`、时长按其默认或用户指定（4～15s）。
- 下游 `social-video-script-*` / `social-video-storyboard` 亦默认英文、人物默认美国人；向导与下游约定一致，避免上游交中文/非默认人物、末端再补救。

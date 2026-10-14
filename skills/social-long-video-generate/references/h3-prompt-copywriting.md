# H3 提示词文案改写摘要（非技术）

来源：[VIDEO_PROMPT_WRITING_GUIDE_base_en.md](https://huggingface.co/MiniMaxAI/MiniMax-H3/raw/main/docs/VIDEO_PROMPT_WRITING_GUIDE_base_en.md)。  
本摘要只保留文案结构与写法；忽略接口、分辨率、上传等技术内容。改写有疑义时以原文案章节为准。

## 最终结构

### 可选：关键帧对齐（仅首/尾/首尾帧任务）

- **首帧**：第一行  
  `For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.`  
  空一行后再写三字段。
- **首尾帧**：第一行说明 Picture 1 对齐 0.00s、Picture 2 对齐片尾 `S.SS` 秒（两位小数），空一行后三字段。宜单镜插值。
- **仅尾帧**：第一行说明 `<Picture 1>` 对齐片尾 `S.SS` 秒所在镜头，空一行后三字段；正文从合理前置状态收敛到尾帧。
- **纯文生 / 普通参考图（非关键帧）**：不要写上述对齐套话；直接三字段。开头可用自然语言说明各参考素材用途。

### 必填三字段（英文）

```text
integrated_multimodal_description: [Shot 1] ...

overall_soundscape: ...

non_diegetic_music: ...
```

- **integrated_multimodal_description**：时间线上的画面、动作、镜头、说话人、对白、歌声、有源音效。
- **overall_soundscape**：全片环境声、动作声、非言语人声（1～4 句）；完全静音才写 `N/A`。
- **non_diegetic_music**：观众能听见、角色听不见的配乐（乐器/节奏/力度）；无配乐写 `N/A`。有源音乐写进 description，不写这里。

## 正文写法要点

- Shot 1 开头交代风格与初始构图（如 live-action, cinematic）；后续镜：`[Shot 2] At 00:03.500, the camera cuts to...`（时间递增且在片长内）。
- 运镜写成句内自然语言（push in / pan / static 等 + 需要时的 amplitude/speed），勿堆标签。
- 说话人用稳定 `(S1)`；对白仅在 `<d>[English] ...</d>` 内；画外音用 `says in an off-screen voiceover` 并写明嘴唇闭合。
- 画内文字：英文双引号包裹，原文不擅自翻译。
- 全文默认英文叙述；社媒向导下口播默认 `<d>[English] ...</d>`（中文台词先翻译）。仅用户明确锁定其它语种时才保留原文。

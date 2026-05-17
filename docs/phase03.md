# Phase 03 — Skill Package

## 目标
将视频摘要工具打包为 Claude Code Skill，让用户在 Claude Code 中直接通过自然语言或斜杠命令触发视频摘要。

## 技术选型
- 项目级 Skill，安装到 `.claude/skills/video-summarizer/`
- SKILL.md 定义触发规则和工作流
- Bash wrapper scripts 处理服务检测、API 调用、结果格式化
- 依赖：curl, jq (或 python3 -c 替代 json 解析)

## 文件结构

```
.claude/skills/video-summarizer/
├── SKILL.md              # Skill 定义（触发、工作流、输出格式）
└── scripts/
    ├── summarize.sh      # 主脚本：提交任务 + 轮询 + 输出结果
    └── status.sh         # 服务状态检查
```

## 模块设计

### 1. SKILL.md

#### Frontmatter
```yaml
---
name: video-summarizer
description: >-
  Summarize videos from Bilibili URLs using ASR + LLM. Triggers when user
  shares a video URL, asks to summarize a video, or types /summarize.
  Supports Chinese/English/Japanese, Claude/OpenAI providers.
---
```

#### Body 内容
- 使用说明：如何触发（URL 或 `/summarize <url>`）
- 参数说明：language, provider, detail
- 工作流指令：调用 `scripts/summarize.sh`
- 输出格式模板

### 2. scripts/summarize.sh

#### 输入参数
| 参数 | 必需 | 默认值 | 说明 |
|------|------|--------|------|
| url | 是 | - | 视频 URL |
| --lang | 否 | zh | 语言 (zh/en/ja) |
| --provider | 否 | claude | LLM provider (claude/openai) |
| --detail | 否 | normal | 详细程度 (brief/normal/detailed) |
| --no-poll | 否 | false | 提交后不轮询，直接返回 task_id |

#### 流程
```
1. 检查服务健康 (GET /health)
   ├─ 不可用 → 提示启动命令，exit 1
   └─ 可用 → 继续

2. 提交任务 (POST /api/summarize)
   └─ 返回 task_id

3. 轮询状态 (GET /api/tasks/{task_id})
   ├─ 每 3 秒查询一次
   ├─ 显示当前状态 (downloading/transcribing/summarizing)
   ├─ done → 输出结果，exit 0
   ├─ failed → 输出错误，exit 1
   └─ 超时 (5 分钟) → 提示手动查询，exit 1

4. 格式化输出
```

#### 输出格式
```
✅ 视频摘要完成

标题: Linux网络命名空间核心
时长: 6分0秒 | 平台: bilibili

摘要:
本视频详细讲解了Linux网络命名空间的核心概念...

---
转录原文 (前 500 字):
这是一段关于Linux网络命名空间的详细讲解...

任务ID: b94ce3df-... | 完整转录: /api/tasks/{task_id}
```

### 3. scripts/status.sh

#### 功能
- 无参数：检查服务健康 + 显示存储占用 + 最近 5 个任务
- `--task <id>`：查询指定任务详情
- `--cleanup`：清理存储（带确认）

#### 输出格式
```
=== Video Summarizer Status ===
服务: ✅ 运行中 (v0.1.0)
存储: 12 个任务 | 45.2 MB

最近任务:
  [done]     05-13 22:30  Linux网络命名空间核心
  [failed]   05-13 22:15  https://bilibili.com/...
  [done]     05-13 21:00  Docker容器网络详解
```

## 验收标准

### 功能验收

| # | 场景 | 预期结果 |
|---|------|---------|
| 1 | 在 Claude Code 中输入 `/summarize https://bilibili.com/video/BVxxx` | Skill 触发，调用 summarize.sh |
| 2 | 在对话中提到 "帮我总结这个视频 https://bilibili.com/video/BVxxx" | Skill 自动触发 |
| 3 | 服务未运行时触发 | 提示 "服务未运行，请先启动"，给出启动命令 |
| 4 | 正常提交 + 轮询 | 状态实时更新，完成后输出格式化摘要 |
| 5 | 任务失败 | 输出错误信息，exit code 1 |
| 6 | `scripts/status.sh` | 显示服务状态、存储占用、最近任务 |
| 7 | `scripts/status.sh --cleanup` | 确认后清理，显示清理结果 |
| 8 | 无效 URL | 前端校验拒绝，不发请求 |

### 非功能验收

| 维度 | 要求 |
|------|------|
| 脚本可独立运行 | `bash scripts/summarize.sh <url>` 可脱离 Claude Code 使用 |
| 错误处理 | 所有错误路径有明确输出，exit code 正确 |
| 无额外依赖 | 仅依赖 curl + python3 (json 解析)，不引入 jq 等 |
| 幂等 | 重复提交相同 URL 创建新任务，不冲突 |

### 验收命令

```bash
# 1. 脚本可独立运行
bash .claude/skills/video-summarizer/scripts/status.sh
bash .claude/skills/video-summarizer/scripts/summarize.sh https://bilibili.com/video/BVxxx

# 2. Skill 安装验证
ls .claude/skills/video-summarizer/SKILL.md

# 3. 在 Claude Code 中测试
# 输入: /summarize https://bilibili.com/video/BVxxx
# 或: 帮我总结这个视频 https://bilibili.com/video/BVxxx
```

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `.claude/skills/video-summarizer/SKILL.md` | 新建 | Skill 定义 |
| `.claude/skills/video-summarizer/scripts/summarize.sh` | 新建 | 主脚本 |
| `.claude/skills/video-summarizer/scripts/status.sh` | 新建 | 状态脚本 |
| `tests/test_skill.py` | 新建 | 脚本单元测试 |

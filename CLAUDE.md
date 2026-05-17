# CLAUDE.md

本项目是一个基于 LLM 的视频总结工具。

## 开发规范

所有开发工作必须严格遵守 `docs/spec.md` 中定义的迭代闭环流程：

1. 单元测试全通过
2. 集成测试覆盖完整业务流（mock 外部依赖，真实 HTTP 请求）
3. 环境问题记录不阻塞
4. 验收交付物齐全

## 技术栈

- Python 3.12+, uv, FastAPI
- Whisper (ASR), yt-dlp (下载), ffmpeg (音频提取)
- LLM: Claude / OpenAI 协议，支持自定义端点

## 文档结构

- `docs/roadmap.md` — 项目大纲和迭代流程
- `docs/spec.md` — 开发规范（本文件引用）
- `docs/phaseNN.md` — 各阶段实现文档

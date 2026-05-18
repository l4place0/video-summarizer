# Phase 05 — YouTube 支持

## 目标
扩展平台抽象层，支持 YouTube 视频下载和总结。

## 实现

### 新增文件
- `core/platforms/youtube.py` — YouTubePlatform 类

### 修改文件
- `core/pipeline.py` — 注册 YouTubePlatform 到 PLATFORMS 列表
- `core/web/index.html` — placeholder 更新为 "Bilibili / YouTube"
- `skill/SKILL.md` — 描述更新，包含 YouTube
- `skill/scripts/summarize.sh` — usage 文本更新
- `tests/test_platforms.py` — YouTube URL 匹配/解析测试
- `tests/test_integration.py` — YouTube 集成测试

### URL 支持
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/embed/VIDEO_ID`

## 验收标准

| # | 场景 | 预期结果 |
|---|------|---------|
| 1 | YouTube 标准 URL | 匹配成功，正确提取 video_id |
| 2 | YouTube 短链接 (youtu.be) | 匹配成功 |
| 3 | YouTube embed URL | 匹配成功 |
| 4 | 非 YouTube URL | 不匹配 |
| 5 | 完整 pipeline (mock) | 下载→转录→分类→总结→done |
| 6 | 无效 YouTube URL | 返回 400 |

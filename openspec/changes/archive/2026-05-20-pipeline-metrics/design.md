## Context

Pipeline 运行过程中没有任何资源消耗记录。无法知道下载花了多久、LLM 用了多少 token、转录了多少字符。

## Goals / Non-Goals

**Goals:**
- 记录每个阶段的开始时间、结束时间、耗时
- 记录 LLM API 调用次数和 token 用量（如可用）
- 记录下载文件大小、转录文本长度
- 在 WebUI 展示 metrics 详情

**Non-Goals:**
- 不做外部监控系统集成（Prometheus/Grafana）
- 不做跨任务统计分析
- 不持久化到独立数据库（存储在 task metadata 中）

## Decisions

### 1. 数据结构

在 task metadata 中添加 `metrics` 字段：
```json
{
  "metrics": {
    "download": {"duration_ms": 3200, "file_size_bytes": 94000000},
    "transcribe": {"duration_ms": 85000, "text_length": 12000},
    "extract_frames": {"duration_ms": 15000, "frame_count": 10},
    "classify": {"duration_ms": 3200, "api_calls": 1},
    "summarize": {"duration_ms": 25000, "api_calls": 1},
    "total_duration_ms": 131200
  }
}
```

### 2. 埋点方式

使用 `time.monotonic()` 计时，在每个阶段开始/结束时记录。Metrics 对象在 pipeline 开始时创建，各阶段写入对应字段，结束时写入 metadata。

### 3. WebUI 展示

在任务详情页（result-section）添加一个可折叠的 "Metrics" 区域，显示：
- 各阶段耗时条形图（纯 CSS）
- 总耗时
- 文件大小、文本长度等指标

## Risks / Trade-offs

- [metadata 膨胀] metrics 数据量小（~500 bytes），可接受
- [计时精度] monotonic 适合测量间隔，不受系统时间调整影响

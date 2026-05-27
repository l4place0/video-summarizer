## ADDED Requirements

### Requirement: Claude uses timestamp-based frame extraction
Claude LLM 的帧提取 SHALL 使用 timestamp seeking 方式，与 OpenAI LLM 行为一致。

#### Scenario: Extract frames from long video
- **WHEN** Claude LLM 对长视频（>30min）进行多模态总结
- **THEN** 帧提取使用 ffmpeg `-ss` 参数直接跳转到目标时间戳
- **AND** 不解码整个视频文件
- **AND** 每帧提取有 30 秒超时保护

#### Scenario: Duration detection fallback
- **WHEN** ffprobe 无法获取视频时长
- **THEN** 回退到 fps filter 方式提取帧

#### Scenario: Frame extraction timeout
- **WHEN** 单帧提取超过 30 秒
- **THEN** 跳过该帧，继续提取下一帧

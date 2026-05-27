## ADDED Requirements

### Requirement: Transcription with segment timestamps
系统 SHALL 在转录输出中包含段落级时间戳。

#### Scenario: Transcribe a 10-minute video
- **WHEN** Whisper 转录一个 10 分钟视频
- **THEN** 输出格式为每行 `[MM:SS] 文本`
- **AND** 时间戳对应每个语音段落的起始时间

#### Scenario: Timestamp format
- **WHEN** 一个段落从 65.3 秒开始，文本为 "大家好"
- **THEN** 输出为 `[01:05] 大家好`

#### Scenario: Empty segments
- **WHEN** 某个段落文本为空
- **THEN** 跳过该段落，不输出

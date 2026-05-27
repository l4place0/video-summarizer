## ADDED Requirements

### Requirement: Detail level affects summary output
系统 SHALL 根据 detail 参数调整摘要的详细程度。

#### Scenario: Brief summary
- **WHEN** 用户请求 detail="brief"
- **THEN** prompt 包含"请用 2-3 句话概括核心内容"指令
- **AND** max_tokens 设为 1024

#### Scenario: Normal summary
- **WHEN** 用户请求 detail="normal"
- **THEN** 使用默认 prompt，max_tokens=4096

#### Scenario: Detailed summary
- **WHEN** 用户请求 detail="detailed"
- **THEN** prompt 包含"请提供详尽分析，包含具体例子、数据引用、关键时间点"指令
- **AND** max_tokens 设为 8192

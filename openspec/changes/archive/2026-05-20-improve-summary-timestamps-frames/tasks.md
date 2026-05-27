## 1. 帧提取修复

- [x] 1.1 在 `base.py` 的 `_download_video_stream` 中应用 `_filename` 空值检查修复

## 2. 时间戳转录

- [x] 2.1 修改 `whisper.py` 的 `_transcribe_once`，faster-whisper 路径格式化为 `[MM:SS] 文本`
- [x] 2.2 修改 `whisper.py` 的 openai-whisper 路径，使用 `result["segments"]` 获取时间戳
- [x] 2.3 验证时间戳格式正确

## 3. Detail 级别生效

- [x] 3.1 在 `prompts.py` 中修改 `get_summary_prompt` 接受 `detail` 参数
- [x] 3.2 在 prompt 模板中根据 detail 追加指令（brief/normal/detailed）
- [x] 3.3 在 `openai_proto.py` 中根据 detail 调整 max_tokens
- [x] 3.4 在 `base.py` (LLM) 的 `summarize` 和 `summarize_stream` 中传递 detail 到 prompt
- [x] 3.5 验证 detail 级别影响输出

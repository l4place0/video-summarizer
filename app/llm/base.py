from abc import ABC, abstractmethod


class BaseLLM(ABC):
    @abstractmethod
    def summarize(self, transcript: str, lang: str = "zh", detail: str = "normal") -> str:
        """Summarize a transcript. Returns summary text."""
        ...


SUMMARY_PROMPTS = {
    "normal": {
        "zh": "请对以下视频转录内容进行总结，提取核心观点和关键信息，用中文输出：\n\n{transcript}",
        "en": "Summarize the following video transcript, extract key points and information:\n\n{transcript}",
    },
    "detailed": {
        "zh": "请对以下视频转录内容进行详细总结，按主题分段，保留重要细节和数据，用中文输出：\n\n{transcript}",
        "en": "Provide a detailed summary of the following video transcript, organized by topics with important details preserved:\n\n{transcript}",
    },
}

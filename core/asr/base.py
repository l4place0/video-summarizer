"""Abstract base class for ASR (Automatic Speech Recognition) providers."""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseASR(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path, language: str = "zh") -> str:
        """Transcribe audio file to text with timestamps.

        Returns:
            Text with [MM:SS] timestamp prefixes per segment.
        """
        ...

"""Persistent prompt store — allows runtime customization of prompts.

Custom prompts are saved to data/prompts.json. On load, they override
the built-in defaults. The JSON structure mirrors the in-memory dicts:
{
    "classify": {"zh": "...", "en": "..."},
    "classify_multimodal": {"zh": "...", "en": "..."},
    "summary": {
        "tutorial": {"zh": "...", "en": "..."},
        "tech_talk": {"zh": "...", "en": "..."},
        ...
    },
    "review_cards_suffix": {"zh": "...", "en": "..."}
}
"""

import json
import logging
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)

_PROMPTS_FILE = settings.data_dir / "prompts.json"


class PromptStore:
    def __init__(self, path: Path | None = None):
        self.path = path or _PROMPTS_FILE
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
                logger.info("Loaded custom prompts from %s", self.path)
            except Exception as e:
                logger.warning("Failed to load custom prompts: %s", e)
                self._data = {}
        else:
            self._data = {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_classify(self, lang: str = "zh", multimodal: bool = False) -> str | None:
        key = "classify_multimodal" if multimodal else "classify"
        return self._data.get(key, {}).get(lang)

    def set_classify(self, lang: str, prompt: str, multimodal: bool = False) -> None:
        key = "classify_multimodal" if multimodal else "classify"
        self._data.setdefault(key, {})[lang] = prompt
        self._save()

    def get_summary(self, content_type: str, lang: str = "zh") -> str | None:
        return self._data.get("summary", {}).get(content_type, {}).get(lang)

    def get_review_cards_suffix(self, lang: str = "zh") -> str | None:
        return self._data.get("review_cards_suffix", {}).get(lang)

    def set_review_cards_suffix(self, lang: str, suffix: str) -> None:
        self._data.setdefault("review_cards_suffix", {})[lang] = suffix
        self._save()

    def set_summary(self, content_type: str, lang: str, prompt: str) -> None:
        self._data.setdefault("summary", {}).setdefault(content_type, {})[lang] = prompt
        self._save()

    def list_prompts(self) -> dict:
        """Return a summary of all customized prompts."""
        result = {}
        for key in ("classify", "classify_multimodal"):
            langs = self._data.get(key, {})
            if langs:
                result[key] = {lang: len(p) for lang, p in langs.items()}
        summary = self._data.get("summary", {})
        if summary:
            result["summary"] = {}
            for ct, langs in summary.items():
                result["summary"][ct] = {lang: len(p) for lang, p in langs.items()}
        rc = self._data.get("review_cards_suffix", {})
        if rc:
            result["review_cards_suffix"] = {lang: len(p) for lang, p in rc.items()}
        return result

    def reset(self, category: str | None = None, content_type: str | None = None, lang: str | None = None) -> bool:
        """Reset prompts to defaults. Granularity depends on which params are given."""
        if category is None:
            self._data = {}
            self._save()
            return True

        if category == "classify":
            if lang:
                self._data.get("classify", {}).pop(lang, None)
            else:
                self._data.pop("classify", None)
            self._save()
            return True

        if category == "classify_multimodal":
            if lang:
                self._data.get("classify_multimodal", {}).pop(lang, None)
            else:
                self._data.pop("classify_multimodal", None)
            self._save()
            return True

        if category == "summary":
            if content_type and lang:
                self._data.get("summary", {}).get(content_type, {}).pop(lang, None)
            elif content_type:
                self._data.get("summary", {}).pop(content_type, None)
            else:
                self._data.pop("summary", None)
            self._save()
            return True

        if category == "review_cards_suffix":
            if lang:
                self._data.get("review_cards_suffix", {}).pop(lang, None)
            else:
                self._data.pop("review_cards_suffix", None)
            self._save()
            return True

        return False


# Singleton
_store: PromptStore | None = None


def get_prompt_store() -> PromptStore:
    global _store
    if _store is None:
        _store = PromptStore()
    return _store

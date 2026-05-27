from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # LLM
    llm_provider: str = "openai"
    claude_model: str = "claude-sonnet-4-20250514"
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    openai_model: str = "gpt-4o"
    openai_vision_model: str = ""  # vision-capable model for multimodal; empty = use openai_model
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"

    # Whisper
    whisper_model: str = "medium"
    whisper_backend: str = "faster"  # "faster" or "openai"
    hf_endpoint: str = ""  # HuggingFace mirror endpoint, e.g. https://hf-mirror.com

    # ASR service
    asr_provider: str = "inprocess"  # inprocess | local | openai
    asr_endpoint: str = ""           # http://gpu-server:8001 (for local)
    asr_api_key: str = ""            # API key (for openai cloud)
    asr_model: str = "whisper-1"     # cloud model name

    # Cookies (for Bilibili etc.)
    cookies_path: Path = Path("data/cookies.txt")

    # Vision / frame extraction
    frame_mode: str = "interval"
    max_frames: int = 10
    frame_interval: int = 30
    scene_threshold: float = 0.3

    # Storage
    data_dir: Path = Path("data")
    auto_cleanup_days: int = 7

    @property
    def db_path(self) -> Path:
        return self.data_dir / "db.sqlite3"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def audio_dir(self) -> Path:
        return self.cache_dir / "audio"

    @property
    def transcript_dir(self) -> Path:
        return self.cache_dir / "transcripts"

    @property
    def frames_dir(self) -> Path:
        return self.cache_dir / "frames"

    def ensure_dirs(self) -> None:
        for d in [self.data_dir, self.cache_dir, self.audio_dir, self.transcript_dir, self.frames_dir]:
            d.mkdir(parents=True, exist_ok=True)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()

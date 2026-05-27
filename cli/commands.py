"""CLI subcommands for video-sum."""

import json
import logging
import sys
import time

import click
import httpx

from cli.output import emit, emit_error

# Redirect all logging to stderr so stdout stays clean JSON
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s: %(message)s")


@click.command()
@click.argument("url")
@click.option("--lang", default="zh", help="Language (zh/en/ja)")
@click.option("--provider", default="openai", help="LLM provider (openai/claude)")
@click.option("--asr", default="", help="ASR provider (inprocess/local/openai)")
@click.option("--detail", default="normal", help="Detail level (brief/normal/detailed)")
@click.option("--mode", default="multimodal", help="Mode (multimodal/audio)")
@click.option("--remote", default="", help="Remote server URL (e.g. http://localhost:8000)")
def run(url, lang, provider, asr, detail, mode, remote):
    """Summarize a video URL. Emits JSON events to stdout."""
    if remote:
        _run_remote(url, lang, provider, detail, mode, remote)
    else:
        _run_local(url, lang, provider, asr, detail, mode)


@click.command()
@click.argument("url")
@click.option("--lang", default="zh")
@click.option("--provider", default="openai")
@click.option("--detail", default="normal")
@click.option("--mode", default="multimodal")
@click.option("--remote", default="", help="Remote server URL")
def submit(url, lang, provider, detail, mode, remote):
    """Submit a video URL for summarization. Returns task_id."""
    server = remote or "http://localhost:8000"
    try:
        resp = httpx.post(f"{server}/api/summarize", json={
            "url": url, "language": lang, "llm_provider": provider,
            "detail": detail, "mode": mode,
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        emit("submitted", task_id=data["task_id"], status=data["status"])
    except httpx.HTTPStatusError as e:
        emit_error(f"Server error: {e.response.status_code} {e.response.text}")
    except httpx.ConnectError:
        emit_error(f"Cannot connect to {server}. Is the server running?")


@click.command()
@click.argument("task_id")
@click.option("--remote", default="", help="Remote server URL")
def status(task_id, remote):
    """Query task status."""
    server = remote or "http://localhost:8000"
    try:
        resp = httpx.get(f"{server}/api/tasks/{task_id}/status", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        emit("status", **data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            emit_error(f"Task not found: {task_id}")
        else:
            emit_error(f"Server error: {e.response.status_code}")
    except httpx.ConnectError:
        emit_error(f"Cannot connect to {server}")


@click.command()
@click.argument("task_id")
@click.option("--remote", default="", help="Remote server URL")
def result(task_id, remote):
    """Get full task result."""
    server = remote or "http://localhost:8000"
    try:
        resp = httpx.get(f"{server}/api/tasks/{task_id}", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        emit("result", **data)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            emit_error(f"Task not found: {task_id}")
        else:
            emit_error(f"Server error: {e.response.status_code}")
    except httpx.ConnectError:
        emit_error(f"Cannot connect to {server}")


def _run_local(url, lang, provider, asr_provider, detail, mode):
    """Local orchestration: download → ASR → LLM → output."""
    try:
        from core.config import settings
        from core.llm import get_llm
        from core.asr import get_asr
        from core.platforms.base import BasePlatform
        from core.platforms.bilibili import BilibiliPlatform
        from core.platforms.youtube import YouTubePlatform

        # Resolve platform
        platforms = [BilibiliPlatform(), YouTubePlatform()]
        platform = None
        for p in platforms:
            try:
                p.validate_url(url)
                platform = p
                break
            except ValueError:
                continue
        if not platform:
            emit_error(f"Unsupported URL: {url}")

        # Download
        emit("downloading", url=url)
        audio_dir = settings.audio_dir / "cli"
        keep_video = mode == "multimodal"
        audio_path, metadata, video_path = platform.download(url, audio_dir, keep_video=keep_video)
        emit("downloaded", title=metadata.get("title", ""), duration=metadata.get("duration", 0))

        # Transcribe
        emit("transcribing")
        asr = get_asr(asr_provider)
        transcript = asr.transcribe(audio_path, lang)
        emit("transcribed", length=len(transcript))

        # LLM
        llm = get_llm(provider)
        emit("classifying")
        content_type = llm.classify(transcript, lang=lang, multimodal=False)
        emit("classified", content_type=content_type)

        emit("summarizing")
        summary = llm.summarize(transcript, lang=lang, detail=detail, content_type=content_type)
        emit("done", summary=summary, transcript=transcript, metadata=metadata, content_type=content_type)

    except Exception as e:
        emit_error(str(e))


def _run_remote(url, lang, provider, detail, mode, server):
    """Remote orchestration: submit → poll → result."""
    try:
        # Submit
        emit("submitting", url=url)
        resp = httpx.post(f"{server}/api/summarize", json={
            "url": url, "language": lang, "llm_provider": provider,
            "detail": detail, "mode": mode,
        }, timeout=30)
        resp.raise_for_status()
        task_id = resp.json()["task_id"]
        emit("submitted", task_id=task_id)

        # Poll
        while True:
            time.sleep(2)
            status_resp = httpx.get(f"{server}/api/tasks/{task_id}/status", timeout=10)
            status_resp.raise_for_status()
            data = status_resp.json()
            emit("progress", status=data["status"], progress=data.get("progress", 0))

            if data["status"] == "done":
                # Get full result
                result_resp = httpx.get(f"{server}/api/tasks/{task_id}", timeout=10)
                result_resp.raise_for_status()
                full = result_resp.json()
                emit("done", summary=full.get("summary", ""),
                     transcript=full.get("transcript", ""),
                     metadata=full.get("metadata", {}))
                return
            elif data["status"] == "failed":
                emit_error(f"Task failed: {data.get('error', 'unknown')}")

    except httpx.ConnectError:
        emit_error(f"Cannot connect to {server}")
    except httpx.HTTPStatusError as e:
        emit_error(f"Server error: {e.response.status_code}")

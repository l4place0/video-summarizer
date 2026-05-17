import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from core.api.routes import router
from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    yield


app = FastAPI(title="Video Summarizer", version="0.1.0", lifespan=lifespan)
app.include_router(router)

# Static files mounted AFTER API routes to avoid overriding /api/* and /health
web_dir = Path(__file__).parent / "web"
app.mount("/", StaticFiles(directory=str(web_dir), html=True), name="web")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("core.main:app", host=settings.host, port=settings.port, reload=True)

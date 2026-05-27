FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir \
    faster-whisper \
    fastapi \
    uvicorn[standard] \
    python-multipart

COPY server.py /app/server.py
WORKDIR /app

ENV WHISPER_MODEL=medium
ENV WHISPER_DEVICE=cuda
ENV WHISPER_COMPUTE_TYPE=float32

EXPOSE 8001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8001"]

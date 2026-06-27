FROM python:3.11-slim

LABEL maintainer="phoenix@web4light.online"
LABEL org.opencontainers.image.title="Karel IV."
LABEL org.opencontainers.image.description="Real-time Voice Translator by AsgardLab"
LABEL org.opencontainers.image.url="https://web4light.online"
LABEL org.opencontainers.image.licenses="GPL-3.0"

# System dependencies for audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    portaudio19-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for layer caching
COPY docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/
COPY prometheus/ ./prometheus/

# Prometheus port + Karel IV. metrics port
EXPOSE 9302 9303 9306

# Default: run Karel IV. in demo mode
CMD ["python", "src/karel_iv.py", "--source", "cs", "--target", "en"]

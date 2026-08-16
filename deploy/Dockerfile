FROM python:3.11-slim

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# App code
COPY src/ ./src/
COPY config/ ./config/

# Port (Cloud Run sets PORT env var)
ENV PORT=8080
EXPOSE 8080

# Run production server
CMD ["python", "src/asgard_server.py"]

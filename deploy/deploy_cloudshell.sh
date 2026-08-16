#!/bin/bash
# ============================================================
# ASGARD LAB — Produkční nasazení z Google Cloud Shell
# 
# Spusť tento skript v Cloud Shell:
#   bash deploy_cloudshell.sh
#
# Předpoklady:
#   - Billing zapnutý na projektu
#   - GEMINI_API_KEY nastaven
# ============================================================

set -e

echo "═══════════════════════════════════════════════"
echo "  ⚡ ASGARD LAB — Production Deploy"
echo "  Autonomous Translation + Dubbing + Sign"
echo "═══════════════════════════════════════════════"
echo

# Konfigurace
PROJECT="${GOOGLE_CLOUD_PROJECT:-$(gcloud config get-value project)}"
REGION="europe-west1"
SERVICE="asgard-lab"
REPO="asgard-repo"

echo "[1/6] Projekt: $PROJECT"
echo "[1/6] Region: $REGION"
echo

# API
echo "[2/6] Zapínám API..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  generativelanguage.googleapis.com \
  --project="$PROJECT" --quiet

# Artifact Registry repo
echo "[3/6] Vytvářím registry..."
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker \
  --location="$REGION" \
  --project="$PROJECT" 2>/dev/null || true

# Clone repo (pokud nejsme v něm)
echo "[4/6] Připravuji kód..."
if [ ! -f "src/asgard_server.py" ]; then
  git clone https://github.com/Rebirth-Phoenix-Foundation-Charter/Universal-Translation-Layer.git app
  cd app
fi

# Build
IMAGE="$REGION-docker.pkg.dev/$PROJECT/$REPO/$SERVICE:latest"
echo "[5/6] Buduji image: $IMAGE"

cat > Dockerfile << 'DOCKERFILE'
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY src/ ./src/

RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn==0.30.6 \
    google-genai==1.14.0 \
    groq==0.11.0 \
    gtts==2.5.3 \
    yt-dlp==2024.8.6 \
    pydantic==2.9.0 \
    prometheus-client==0.21.0 \
    httpx==0.27.2

ENV PORT=8080
EXPOSE 8080
CMD ["python", "src/asgard_server.py"]
DOCKERFILE

gcloud builds submit --tag "$IMAGE" --project="$PROJECT" --quiet

# Deploy
echo "[6/6] Nasazuji na Cloud Run..."
gcloud run deploy "$SERVICE" \
  --image "$IMAGE" \
  --platform managed \
  --region "$REGION" \
  --project "$PROJECT" \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --min-instances 1 \
  --max-instances 10 \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY}" \
  --timeout 300 \
  --quiet

# URL
URL=$(gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format='value(status.url)')

echo
echo "═══════════════════════════════════════════════"
echo "  ✅ DEPLOYED!"
echo "  URL: $URL"
echo "═══════════════════════════════════════════════"
echo
echo "  Endpoints:"
echo "    $URL/           — Web UI"
echo "    $URL/translate  — POST translation API"
echo "    $URL/dub        — POST dubbing"
echo "    $URL/sign       — POST sign language"
echo "    $URL/status     — System status"
echo "    $URL/docs       — Swagger API docs"
echo
echo "  System je autonomní. Vydělává a škáluje se sám."
echo "═══════════════════════════════════════════════"

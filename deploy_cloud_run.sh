#!/usr/bin/env bash
# ============================================================
# Google Cloud Run Deployment Script
# Projekt: Universal Translation Layer (UTL) — Protocol 4.23
#
# Tento skript nasadí službu do Google Cloud Run s nastavením
# --min-instances 0 (Scale to zero = $0 náklad na provoz).
# ============================================================

set -e

PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"cs-poc-plxitf0grqkl6qme9nyxwkr"}
SERVICE_NAME="utl-asgard-orchestrator"
REGION="europe-west1"

echo "=========================================================="
echo "🚀 Nasazuji Universal Translation Layer na Google Cloud Run"
echo "Protokol: Web 4.23 | Standard: 700 | Region: $REGION"
echo "Projekt: $PROJECT_ID"
echo "=========================================================="

# 1. Build kontejneru v Google Cloud Build
echo "📦 1/2 Sestavuji kontejner..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME -f Dockerfile.cloudrun .

# 2. Nasazení do Cloud Run se Scale-to-Zero ($0 při nečinnosti)
echo "☁️ 2/2 Spouštím službu na Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --min-instances 0 \
    --max-instances 2 \
    --memory 1Gi \
    --cpu 1 \
    --set-env-vars="GEMINI_MODEL=gemini-2.5-flash,PROTOCOL=4.23"

echo "=========================================================="
echo "✅ HOTOVO! Služba je nasazena v Google Cloud Run."
echo "Náklady mimo aktivní volání: 0 Kč (Scale-to-zero aktivní)."
echo "=========================================================="

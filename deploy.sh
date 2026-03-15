#!/bin/bash
set -e

PROJECT_ID="kerjasama-dev"
SERVICE_NAME="kerjasama-chat-api"
REGION="europe-west1"
SERVICE_ACCOUNT="kerjasama-chat-api@kerjasama-dev.iam.gserviceaccount.com"

echo "Running tests..."
pytest tests/ -v
if [ $? -ne 0 ]; then
    echo "Tests failed. Aborting deployment."
    exit 1
fi
echo "All tests passed!"

echo "Deploying $SERVICE_NAME to Cloud Run..."

gcloud run deploy $SERVICE_NAME \
  --source . \
  --project $PROJECT_ID \
  --region $REGION \
  --service-account $SERVICE_ACCOUNT \
  --add-cloudsql-instances=kerjasama-dev:europe-west2:kerjasama-db \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets="\
GEMINI_API_KEY=gemini-api-key:latest,\
ENCRYPTION_KEY=encryption-key:latest" \
  --memory=512Mi \
  --cpu=1 \
  --timeout=60 \
  --min-instances=0 \
  --max-instances=10

echo "Deployment complete!"
echo "Service URL:"
gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)'

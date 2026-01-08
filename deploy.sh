#!/bin/bash
set -e

PROJECT_ID="kerjasama-dev"
SERVICE_NAME="kerjasama-agent"
REGION="europe-west1"

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
  --add-cloudsql-instances=kerjasama-dev:europe-west2:kerjasama-db \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars="\
GOOGLE_CLIENT_ID=766885392730-5tmjtsturag2i5vmh2hg9hl9s33jq7hv.apps.googleusercontent.com" \
  --set-secrets="WHATSAPP_VERIFY_TOKEN=whatsapp-verify-token:latest,WHATSAPP_APP_SECRET=whatsapp-app-secret:latest,DATABASE_URL=database-url:latest,GOOGLE_ADK_API_KEY=google-adk-api-key:latest,GOOGLE_CLIENT_SECRET=google-client-secret:latest,ENCRYPTION_KEY=encryption-key:latest" \
  --memory=4Gi \
  --cpu=1 \
  --timeout=90 \
  --min-instances=0 \
  --max-instances=5

echo "Deployment complete!"
echo "Service URL:"
gcloud run services describe $SERVICE_NAME --region $REGION --project $PROJECT_ID --format='value(status.url)'

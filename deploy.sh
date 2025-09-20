#!/bin/bash

# Load env variables
export $(grep -v '^#' secrets/.env | xargs)

SERVICE_NAME="vault-curator"
IMAGE="gcr.io/$GCP_PROJECT/$SERVICE_NAME"

# Authenticate with GCP
gcloud auth activate-service-account --key-file=$GCP_SA_KEY_PATH
gcloud config set project $GCP_PROJECT
gcloud auth configure-docker
gcloud services enable drive.googleapis.com --project=$GCP_PROJECT

# Build & push Docker image
docker build --platform=linux/amd64 -t $IMAGE .
docker push $IMAGE

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE \
  --region $GCP_REGION \
  --project $GCP_PROJECT \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets "/usr/src/app/secrets/service-account/service-account.json=vault-curator-sa:latest" \
  --set-secrets "/usr/src/app/secrets/token/token.pkl=vault-curator-user-token:latest"

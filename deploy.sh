#!/bin/bash
# BuildTrace Deployment Script for Google Cloud Run
# 
# This script automates the deployment of the BuildTrace service to Google Cloud Run
# with Pub/Sub integration.

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-bt-challenge}"
BUCKET_NAME="${BUCKET_NAME:-}"
TOPIC_ID="${TOPIC_ID:-bt-jobs}"
SUBSCRIPTION_ID="${SUBSCRIPTION_ID:-bt-jobs-sub}"
GEMINI_API_KEY="${GEMINI_API_KEY:-}"  # Optional: For AI-powered summaries

# Functions
print_header() {
    echo -e "\n${GREEN}==== $1 ====${NC}\n"
}

print_error() {
    echo -e "${RED}ERROR: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}WARNING: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# Check prerequisites
print_header "Checking Prerequisites"

if [ -z "$PROJECT_ID" ]; then
    print_error "PROJECT_ID environment variable not set"
    echo "Usage: export PROJECT_ID=<your-gcp-project-id>"
    exit 1
fi

if [ -z "$BUCKET_NAME" ]; then
    print_warning "BUCKET_NAME not set, using default: bt-challenge-${PROJECT_ID}"
    BUCKET_NAME="bt-challenge-${PROJECT_ID}"
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

print_success "gcloud CLI found"

# Set project
print_header "Setting GCP Project"
gcloud config set project "$PROJECT_ID"
print_success "Project set to: $PROJECT_ID"

# Enable required APIs
print_header "Enabling Required APIs"
gcloud services enable run.googleapis.com \
    pubsub.googleapis.com \
    storage.googleapis.com \
    cloudbuild.googleapis.com

print_success "APIs enabled"

# Create Cloud Storage bucket
print_header "Setting up Cloud Storage"
if gsutil ls -b "gs://${BUCKET_NAME}" &> /dev/null; then
    print_success "Bucket already exists: gs://${BUCKET_NAME}"
else
    gsutil mb -p "$PROJECT_ID" -l "$REGION" "gs://${BUCKET_NAME}"
    print_success "Created bucket: gs://${BUCKET_NAME}"
fi

# Create directories in bucket
gsutil -m mkdir -p "gs://${BUCKET_NAME}/inputs/" "gs://${BUCKET_NAME}/results/" || true
print_success "Created bucket directories"

# Create Pub/Sub topic
print_header "Setting up Pub/Sub"
if gcloud pubsub topics describe "$TOPIC_ID" &> /dev/null; then
    print_success "Topic already exists: $TOPIC_ID"
else
    gcloud pubsub topics create "$TOPIC_ID"
    print_success "Created topic: $TOPIC_ID"
fi

# Build and push Docker image
print_header "Building Docker Image"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
gcloud builds submit --tag "$IMAGE_NAME"
print_success "Image built and pushed: $IMAGE_NAME"

# Deploy to Cloud Run
print_header "Deploying to Cloud Run"

# Prepare environment variables
ENV_VARS="PROJECT_ID=${PROJECT_ID},BUCKET=${BUCKET_NAME},TOPIC_ID=${TOPIC_ID}"

# Add Gemini API key if provided
if [ -n "$GEMINI_API_KEY" ]; then
    ENV_VARS="${ENV_VARS},GEMINI_API_KEY=${GEMINI_API_KEY},USE_GEMINI=true"
    print_success "Gemini API key configured for AI-powered summaries"
else
    print_warning "GEMINI_API_KEY not set - using simple summaries (set export GEMINI_API_KEY=... for AI summaries)"
fi

gcloud run deploy "$SERVICE_NAME" \
    --image "$IMAGE_NAME" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --set-env-vars "$ENV_VARS" \
    --min-instances 0 \
    --max-instances 100 \
    --concurrency 80 \
    --memory 512Mi \
    --timeout 300

print_success "Service deployed to Cloud Run"

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format 'value(status.url)')
print_success "Service URL: $SERVICE_URL"

# Create or update Pub/Sub push subscription
print_header "Setting up Pub/Sub Subscription"

# Delete existing subscription if it exists
if gcloud pubsub subscriptions describe "$SUBSCRIPTION_ID" &> /dev/null; then
    print_warning "Deleting existing subscription: $SUBSCRIPTION_ID"
    gcloud pubsub subscriptions delete "$SUBSCRIPTION_ID" --quiet
fi

# Create new push subscription
gcloud pubsub subscriptions create "$SUBSCRIPTION_ID" \
    --topic "$TOPIC_ID" \
    --push-endpoint="${SERVICE_URL}/worker" \
    --ack-deadline=60 \
    --min-retry-delay=10s \
    --max-retry-delay=600s

print_success "Created push subscription: $SUBSCRIPTION_ID"

# Upload sample data
print_header "Uploading Sample Data"
if [ -f "sample/vA.json" ] && [ -f "sample/vB.json" ]; then
    gsutil cp sample/vA.json "gs://${BUCKET_NAME}/inputs/sample-001_vA.json"
    gsutil cp sample/vB.json "gs://${BUCKET_NAME}/inputs/sample-001_vB.json"
    print_success "Sample data uploaded"
else
    print_warning "Sample files not found, skipping upload"
fi

# Summary
print_header "Deployment Complete!"
echo -e "${GREEN}Service URL:${NC} $SERVICE_URL"
echo -e "${GREEN}Bucket:${NC} gs://${BUCKET_NAME}"
echo -e "${GREEN}Topic:${NC} $TOPIC_ID"
echo -e "${GREEN}Subscription:${NC} $SUBSCRIPTION_ID"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Test the health endpoint:"
echo "   curl $SERVICE_URL/health"
echo ""
echo "2. Generate test data:"
echo "   python tools/simulator.py --pairs 10 --output gs://${BUCKET_NAME} --manifest manifest.json"
echo ""
echo "3. Submit jobs:"
echo "   curl -X POST $SERVICE_URL/process -H 'Content-Type: application/json' -d @manifest.json"
echo ""
echo "4. Check metrics:"
echo "   curl $SERVICE_URL/metrics"
echo ""
echo "5. View results:"
echo "   gsutil cat gs://${BUCKET_NAME}/results/DRAWING-0001.json"
echo ""

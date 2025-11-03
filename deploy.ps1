# BuildTrace Deployment Script for Google Cloud Run (PowerShell)
# 
# This script automates the deployment of the BuildTrace service to Google Cloud Run
# with Pub/Sub integration.

$ErrorActionPreference = "Stop"

# Configuration
$PROJECT_ID = $env:PROJECT_ID
$REGION = if ($env:REGION) { $env:REGION } else { "us-central1" }
$SERVICE_NAME = if ($env:SERVICE_NAME) { $env:SERVICE_NAME } else { "bt-challenge" }
$BUCKET_NAME = $env:BUCKET_NAME
$TOPIC_ID = if ($env:TOPIC_ID) { $env:TOPIC_ID } else { "bt-jobs" }
$SUBSCRIPTION_ID = if ($env:SUBSCRIPTION_ID) { $env:SUBSCRIPTION_ID } else { "bt-jobs-sub" }
$GEMINI_API_KEY = $env:GEMINI_API_KEY  # Optional: For AI-powered summaries

# Functions
function Print-Header($message) {
    Write-Host "`n==== $message ====" -ForegroundColor Green
    Write-Host ""
}

function Print-Error($message) {
    Write-Host "ERROR: $message" -ForegroundColor Red
}

function Print-Warning($message) {
    Write-Host "WARNING: $message" -ForegroundColor Yellow
}

function Print-Success($message) {
    Write-Host "✓ $message" -ForegroundColor Green
}

# Check prerequisites
Print-Header "Checking Prerequisites"

if (-not $PROJECT_ID) {
    Print-Error "PROJECT_ID environment variable not set"
    Write-Host "Usage: `$env:PROJECT_ID='<your-gcp-project-id>'"
    exit 1
}

if (-not $BUCKET_NAME) {
    Print-Warning "BUCKET_NAME not set, using default: bt-challenge-$PROJECT_ID"
    $BUCKET_NAME = "bt-challenge-$PROJECT_ID"
}

# Check if gcloud is installed
try {
    gcloud version | Out-Null
    Print-Success "gcloud CLI found"
} catch {
    Print-Error "gcloud CLI not found. Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
}

# Set project
Print-Header "Setting GCP Project"
gcloud config set project $PROJECT_ID
Print-Success "Project set to: $PROJECT_ID"

# Enable required APIs
Print-Header "Enabling Required APIs"
gcloud services enable run.googleapis.com `
    pubsub.googleapis.com `
    storage.googleapis.com `
    cloudbuild.googleapis.com

Print-Success "APIs enabled"

# Create Cloud Storage bucket
Print-Header "Setting up Cloud Storage"
try {
    gsutil ls -b "gs://$BUCKET_NAME" 2>&1 | Out-Null
    Print-Success "Bucket already exists: gs://$BUCKET_NAME"
} catch {
    gsutil mb -p $PROJECT_ID -l $REGION "gs://$BUCKET_NAME"
    Print-Success "Created bucket: gs://$BUCKET_NAME"
}

# Create directories in bucket
try {
    gsutil -m mkdir -p "gs://$BUCKET_NAME/inputs/" "gs://$BUCKET_NAME/results/" 2>&1 | Out-Null
} catch {}
Print-Success "Created bucket directories"

# Create Pub/Sub topic
Print-Header "Setting up Pub/Sub"
try {
    gcloud pubsub topics describe $TOPIC_ID 2>&1 | Out-Null
    Print-Success "Topic already exists: $TOPIC_ID"
} catch {
    gcloud pubsub topics create $TOPIC_ID
    Print-Success "Created topic: $TOPIC_ID"
}

# Build and push Docker image
Print-Header "Building Docker Image"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"
gcloud builds submit --tag $IMAGE_NAME
Print-Success "Image built and pushed: $IMAGE_NAME"

# Deploy to Cloud Run
Print-Header "Deploying to Cloud Run"

# Prepare environment variables
$ENV_VARS = "PROJECT_ID=$PROJECT_ID,BUCKET=$BUCKET_NAME,TOPIC_ID=$TOPIC_ID"

# Add Gemini API key if provided
if ($GEMINI_API_KEY) {
    $ENV_VARS = "$ENV_VARS,GEMINI_API_KEY=$GEMINI_API_KEY,USE_GEMINI=true"
    Print-Success "Gemini API key configured for AI-powered summaries"
} else {
    Print-Warning "GEMINI_API_KEY not set - using simple summaries (set `$env:GEMINI_API_KEY='...' for AI summaries)"
}

gcloud run deploy $SERVICE_NAME `
    --image $IMAGE_NAME `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --set-env-vars $ENV_VARS `
    --min-instances 0 `
    --max-instances 100 `
    --concurrency 80 `
    --memory 512Mi `
    --timeout 300

Print-Success "Service deployed to Cloud Run"

# Get service URL
$SERVICE_URL = (gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
Print-Success "Service URL: $SERVICE_URL"

# Create or update Pub/Sub push subscription
Print-Header "Setting up Pub/Sub Subscription"

# Delete existing subscription if it exists
try {
    gcloud pubsub subscriptions describe $SUBSCRIPTION_ID 2>&1 | Out-Null
    Print-Warning "Deleting existing subscription: $SUBSCRIPTION_ID"
    gcloud pubsub subscriptions delete $SUBSCRIPTION_ID --quiet
} catch {}

# Create new push subscription
gcloud pubsub subscriptions create $SUBSCRIPTION_ID `
    --topic $TOPIC_ID `
    --push-endpoint="$SERVICE_URL/worker" `
    --ack-deadline=60 `
    --min-retry-delay=10s `
    --max-retry-delay=600s

Print-Success "Created push subscription: $SUBSCRIPTION_ID"

# Upload sample data
Print-Header "Uploading Sample Data"
if ((Test-Path "sample/vA.json") -and (Test-Path "sample/vB.json")) {
    gsutil cp sample/vA.json "gs://$BUCKET_NAME/inputs/sample-001_vA.json"
    gsutil cp sample/vB.json "gs://$BUCKET_NAME/inputs/sample-001_vB.json"
    Print-Success "Sample data uploaded"
} else {
    Print-Warning "Sample files not found, skipping upload"
}

# Summary
Print-Header "Deployment Complete!"
Write-Host "Service URL: " -NoNewline -ForegroundColor Green
Write-Host $SERVICE_URL
Write-Host "Bucket: " -NoNewline -ForegroundColor Green
Write-Host "gs://$BUCKET_NAME"
Write-Host "Topic: " -NoNewline -ForegroundColor Green
Write-Host $TOPIC_ID
Write-Host "Subscription: " -NoNewline -ForegroundColor Green
Write-Host $SUBSCRIPTION_ID

Write-Host "`nNext Steps:" -ForegroundColor Yellow
Write-Host "1. Test the health endpoint:"
Write-Host "   curl $SERVICE_URL/health"
Write-Host ""
Write-Host "2. Generate test data:"
Write-Host "   python tools/simulator.py --pairs 10 --output gs://$BUCKET_NAME --manifest manifest.json"
Write-Host ""
Write-Host "3. Submit jobs:"
Write-Host "   curl -X POST $SERVICE_URL/process -H 'Content-Type: application/json' -d '@manifest.json'"
Write-Host ""
Write-Host "4. Check metrics:"
Write-Host "   curl $SERVICE_URL/metrics"
Write-Host ""
Write-Host "5. View results:"
Write-Host "   gsutil cat gs://$BUCKET_NAME/results/DRAWING-0001.json"
Write-Host ""

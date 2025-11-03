# 🏗️ BuildTrace - Large-Scale Drawing Change Analysis Platform> 🧭 **Instructions for Candidates**

>

A cloud-native system for comparing construction drawing revisions and detecting changes at scale using Google Cloud Run, Pub/Sub, and Gemini AI.> - Clone this repo and build on top of it.  

> - Don’t worry about adding real secrets; use environment variables locally.  

## 🎯 What This System Does> - Aim to complete a working vertical slice in 2–3 hours.  

> - See the main README for build/deploy commands.

BuildTrace analyzes changes between construction drawing versions (simulated as JSON files) and provides:

# 🏗️ BuildTrace - Large-Scale Drawing Change Analysis Platform

- **Change Detection**: Identifies added, removed, and moved objects

- **AI Summaries**: Natural language descriptions using Gemini AIA cloud-native system for comparing construction drawing revisions and detecting changes at scale using Google Cloud Run, Pub/Sub, and Gemini AI.

- **Scalable Processing**: Handles thousands of drawing pairs via Pub/Sub

- **Metrics & Monitoring**: Real-time analytics and anomaly detection## What this service does

- **Cloud-Native**: Fully deployed on Google Cloud Platform- `POST /process`: enqueue comparison jobs from a manifest of GCS URIs

- `POST /worker`: **Pub/Sub push** endpoint; fetches two JSONs from GCS, diffs, writes result JSON to `gs://<bucket>/results/{id}.json`

## 📋 Table of Contents- `GET /metrics`: in-memory `{p50,p95,p99,jobs_*}` since process start



- [Quick Start](#-quick-start)## 🚀 Quick Start

- [Local Development](#-local-development-setup)

- [Google Cloud Deployment](#-google-cloud-deployment)### 1. Environment Setup

- [API Endpoints](#-api-endpoints)

- [Testing](#-testing)Copy the example environment file and configure your settings:

- [Architecture](#-architecture)

- [Troubleshooting](#-troubleshooting)```bash

cp .env.example .env

---```



## 🚀 Quick StartEdit `.env` with your configuration:



### Prerequisites```bash

# Required

- **Python 3.10+** installedPROJECT_ID=your-gcp-project-id

- **Google Cloud Account** (for cloud deployment)BUCKET=gs://bt-challenge-yourname

- **Gemini API Key** (optional, for AI summaries) - Get one at [Google AI Studio](https://makersuite.google.com/app/apikey)

- **gcloud CLI** installed - [Installation Guide](https://cloud.google.com/sdk/docs/install)# Optional

TOPIC_ID=bt-jobs

---GEMINI_API_KEY=your-gemini-api-key  # For AI-powered summaries

USE_GEMINI=true

## 💻 Local Development Setup```



### 1. Clone and Setup EnvironmentThe application automatically loads variables from `.env` on startup.



```powershell### 2. Install Dependencies

# Navigate to project directory

cd bt-challenge```bash

pip install -r requirements.txt

# Create virtual environment```

python -m venv env

## ✨ AI-Powered Change Summaries with Gemini

# Activate virtual environment (Windows PowerShell)

.\env\Scripts\Activate.ps1This system uses **Google Gemini LLM** to generate intelligent, natural language summaries of drawing changes. 



# For Windows CMD:Get your API key from: https://ai.google.dev/

# env\Scripts\activate.bat

### How It Works

# For Linux/Mac:

# source env/bin/activate- **With Gemini**: Generates context-aware, professional summaries like:

```  - *"Door D1 moved 5.2 units east near the main entrance; Window W3 added in the northwest corner providing additional natural light."*

  

### 2. Install Dependencies- **Without Gemini** (fallback): Generates simple summaries like:

  - *"1 door moved 5.2 units east; 1 window added at (3,1)."*

```powershell

pip install -r requirements.txtTo disable Gemini, set `USE_GEMINI=false` in your `.env` file.

```

## Prereqs

### 3. Configure Environment Variables- gcloud CLI, a GCP project

- Enable APIs: `gcloud services enable run.googleapis.com pubsub.googleapis.com storage.googleapis.com`

Create a `.env` file in the project root:- Create a bucket and a topic:

  ```bash

```powershell  export PROJECT_ID=<your-project>

# Copy the example file  export BUCKET=gs://bt-challenge-<yourname>

copy .env.example .env  export TOPIC_ID=bt-jobs

```  gcloud config set project $PROJECT_ID

  gsutil mb -p $PROJECT_ID $BUCKET || true

**Edit `.env` with your settings:**  gcloud pubsub topics create $TOPIC_ID || true


```properties
# Google Cloud Platform Configuration
# Set to false for local development, true for cloud deployment
USE_GCP=false

# Required only if USE_GCP=true
PROJECT_ID=your-gcp-project-id
BUCKET=gs://bt-challenge-yourname
TOPIC_ID=bt-jobs
LOCATION=us-central1

# Gemini AI Configuration (Optional)
GEMINI_API_KEY=your-gemini-api-key-here
USE_GEMINI=true

# Service Configuration (set after deployment)
SERVICE_URL=
```

### 4. Run the Application Locally

```powershell
uvicorn app.main:app --reload --port 8080
```

**The API will be available at:** `http://localhost:8080`

### 5. Test the Local API

**Open the interactive API docs:**

http://localhost:8080/docs

**Or use curl/PowerShell:**

```powershell
# Check API status
curl.exe http://localhost:8080/

# Get metrics
curl.exe http://localhost:8080/metrics

# Health check
curl.exe http://localhost:8080/health

# Analyze drawings locally (no GCP needed)
curl.exe -X POST http://localhost:8080/analyze `
  -H "Content-Type: application/json" `
  -d '{
    "version_a": [{"id":"A1","type":"wall","x":10,"y":5,"width":8,"height":1}],
    "version_b": [{"id":"A1","type":"wall","x":12,"y":5,"width":8,"height":1},{"id":"W1","type":"window","x":3,"y":1,"width":2,"height":1}]
  }'
```

---

## ☁️ Google Cloud Deployment

### Step 1: Set Up Google Cloud Project

```powershell
# Install gcloud CLI (if not already installed)
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login

# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable artifactregistry.googleapis.com
```

### Step 2: Create Cloud Resources

```powershell
# Set variables (customize these)
$PROJECT_ID = "your-project-id"
$BUCKET_NAME = "bt-challenge-yourname"
$LOCATION = "us-central1"
$TOPIC_ID = "bt-jobs"

# Create Cloud Storage bucket
gsutil mb -p $PROJECT_ID -l $LOCATION gs://$BUCKET_NAME

# Create Pub/Sub topic
gcloud pubsub topics create $TOPIC_ID

# Verify resources created
gsutil ls
gcloud pubsub topics list
```

### Step 3: Deploy to Cloud Run

```powershell
# Deploy the service (replace with your actual values)
gcloud run deploy bt-challenge `
  --source . `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars "PROJECT_ID=your-project-id,BUCKET=gs://bt-challenge-yourname,TOPIC_ID=bt-jobs,USE_GCP=true,GEMINI_API_KEY=your-actual-gemini-key,USE_GEMINI=true"

# Get the service URL
gcloud run services describe bt-challenge --region us-central1 --format="value(status.url)"
```

**Example successful deployment output:**

Service URL: https://bt-challenge-544593296841.us-central1.run.app

### Step 4: Create Pub/Sub Push Subscription

```powershell
# Get your Cloud Run service URL
$SERVICE_URL = gcloud run services describe bt-challenge --region us-central1 --format="value(status.url)"

# Create push subscription
gcloud pubsub subscriptions create bt-jobs-sub `
  --topic bt-jobs `
  --push-endpoint="$SERVICE_URL/worker" `
  --ack-deadline=60

# Verify subscription created
gcloud pubsub subscriptions list
```

### Step 5: Upload Sample Data to Cloud Storage

```powershell
# Upload sample JSON files
gcloud storage cp "sample/*.json" gs://bt-challenge-yourname/inputs/

# Verify files uploaded
gcloud storage ls gs://bt-challenge-yourname/inputs/
```

### Step 6: Submit Processing Jobs

**Create a manifest file (or use the existing `sample/manifest.json`):**

```json
{
  "pairs": [
    {
      "id": "sample-drawing-001",
      "a": "gs://bt-challenge-yourname/inputs/DRAWING-0001_vA.json",
      "b": "gs://bt-challenge-yourname/inputs/DRAWING-0001_vB.json"
    }
  ]
}
```

**Submit the jobs:**

```powershell
cd sample

# Submit to Cloud Run
curl.exe -X POST https://YOUR-SERVICE-URL/process `
  -H "Content-Type: application/json" `
  -d "@manifest.json"
```

**Example response:**
```json
{
  "enqueued": 1,
  "topic": "bt-jobs",
  "push_subscription_url": "https://bt-challenge-544593296841.us-central1.run.app/worker"
}
```

### Step 7: View Results

```powershell
# List results in Cloud Storage
gcloud storage ls gs://bt-challenge-yourname/results/

# View a specific result
gsutil cat gs://bt-challenge-yourname/results/sample-drawing-001.json

# Or using gcloud
gcloud storage cat gs://bt-challenge-yourname/results/sample-drawing-001.json
```

**Check metrics:**
```powershell
curl.exe https://YOUR-SERVICE-URL/metrics
```

**Check health:**
```powershell
curl.exe https://YOUR-SERVICE-URL/health
```

---

## 📡 API Endpoints

### `GET /`
Root endpoint - shows service info and available endpoints.

```powershell
curl.exe https://YOUR-SERVICE-URL/
```

### `POST /process`
Submit drawing pairs for analysis (requires GCP).

**Request:**
```json
{
  "pairs": [
    {
      "id": "drawing-001",
      "a": "gs://bucket/inputs/drawing-001_A.json",
      "b": "gs://bucket/inputs/drawing-001_B.json"
    }
  ]
}
```

**Response:**
```json
{
  "enqueued": 1,
  "topic": "bt-jobs"
}
```

### `POST /analyze`
Analyze drawings directly without GCP (local mode).

**Request:**
```json
{
  "version_a": [{"id":"A1","type":"wall","x":10,"y":5}],
  "version_b": [{"id":"A1","type":"wall","x":12,"y":5}]
}
```

**Response:**
```json
{
  "job_id": "uuid",
  "added": [],
  "removed": [],
  "moved": [{...}],
  "summary": "Wall A1 moved 2 units east.",
  "stats": {"total_changes": 1}
}
```

### `GET /metrics`
Get system metrics and statistics.

**Response:**
```json
{
  "total_jobs": 10,
  "success_rate": 0.9,
  "latency_p50": 1.2,
  "latency_p95": 2.5,
  "latency_p99": 3.1
}
```

### `GET /health`
Health check with anomaly detection.

**Response:**
```json
{
  "status": "healthy",
  "warnings": [],
  "jobs": {
    "total": 10,
    "successful": 9,
    "failed": 1,
    "success_rate": "90.0%"
  }
}
```

### `GET /changes?drawing_id=...`
Retrieve results for a specific drawing (requires GCP).

```powershell
curl.exe https://YOUR-SERVICE-URL/changes?drawing_id=sample-drawing-001
```

---

## 🧪 Testing

### Run Unit Tests

```powershell
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_diff.py -v
pytest tests/test_metrics.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# View coverage report
# Open htmlcov/index.html in browser
```

### Generate Sample Data

```powershell
# Generate 10 drawing pairs locally
python tools/simulator.py --pairs 10 --output ./sample

# Generate with different change profiles
python tools/simulator.py --pairs 5 --profile large --output ./sample

# Generate and upload directly to Cloud Storage
python tools/simulator.py --pairs 20 --output gs://bt-challenge-yourname/inputs --manifest gs://bt-challenge-yourname/manifest.json

# Generate with mixed profiles (random changes for each pair)
python tools/simulator.py --pairs 10 --mixed-profiles --output gs://bt-challenge-yourname/inputs
```

### Test End-to-End Locally

```powershell
# 1. Start the server (in one terminal)
uvicorn app.main:app --reload --port 8080

# 2. Test the analyze endpoint (in another terminal)
curl.exe -X POST http://localhost:8080/analyze `
  -H "Content-Type: application/json" `
  -d '{
    "version_a": [{"id":"W1","type":"wall","x":0,"y":0,"width":10,"height":1}],
    "version_b": [{"id":"W1","type":"wall","x":0,"y":0,"width":10,"height":1},{"id":"D1","type":"door","x":5,"y":0,"width":1,"height":2}]
  }'

# 3. Check metrics
curl.exe http://localhost:8080/metrics
```

---

## 🏛️ Architecture

```
┌─────────────────┐
│   Client/User   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│     Cloud Run Service (FastAPI)         │
│  ┌───────────┐  ┌──────────┐           │
│  │  POST     │  │   GET    │           │
│  │ /process  │  │ /metrics │           │
│  │ /analyze  │  │ /health  │           │
│  └─────┬─────┘  └──────────┘           │
└────────┼─────────────────────────────────┘
         │
         ▼
┌──────────────────────┐
│   Pub/Sub Topic      │
│   "bt-jobs"          │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│  Push Subscription → POST /worker        │
│  (Auto-scaling Workers)                  │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│        Cloud Storage Buckets             │
│  ┌────────────┐  ┌─────────────────┐    │
│  │   Inputs   │  │    Results      │    │
│  │  vA.json   │  │  {id}.json      │    │
│  │  vB.json   │  │  - changes      │    │
│  └────────────┘  │  - summary      │    │
│                  │  - metrics      │    │
│                  └─────────────────┘    │
└──────────────────────────────────────────┘
```

### Key Components

1. **FastAPI Application** (`app/main.py`)
   - REST API endpoints
   - Request validation
   - Error handling

2. **Diff Engine** (`app/diff.py`)
   - Geometric object comparison
   - Change detection (added/removed/moved)
   - Gemini AI integration for summaries

3. **Metrics Tracker** (`app/metrics.py`)
   - Latency percentiles (P50/P95/P99)
   - Success rates
   - Anomaly detection

4. **Data Simulator** (`tools/simulator.py`)
   - Generate test datasets
   - Configurable change profiles

---

## 🔧 Troubleshooting

### Issue: "GCP is not configured"

**Solution:** Update environment variables:
```powershell
gcloud run services update bt-challenge --region us-central1 `
  --set-env-vars "PROJECT_ID=your-project-id,BUCKET=gs://your-bucket,USE_GCP=true"
```

### Issue: "No module named 'google.cloud'"

**Solution:** Install dependencies:
```powershell
pip install -r requirements.txt
```

### Issue: Environment variables concatenated

**Symptom:**

```
{'name': 'PROJECT_ID', 'value': 'build-trace BUCKET=gs://... TOPIC_ID=...'}
```

**Solution:** Use quotes around the entire --set-env-vars value:
```powershell
gcloud run services update bt-challenge --region us-central1 `
  --clear-env-vars

gcloud run services update bt-challenge --region us-central1 `
  --set-env-vars "PROJECT_ID=your-id,BUCKET=gs://your-bucket,USE_GCP=true"
```

### Issue: PowerShell line continuation errors

**Problem:** Using `\` instead of `` ` ``

**Solution:** Use backticks for line continuation in PowerShell:
```powershell
# ✅ Correct (PowerShell)
gcloud run deploy bt-challenge `
  --source . `
  --region us-central1

# ❌ Wrong (Bash/Linux syntax)
gcloud run deploy bt-challenge \
  --source . \
  --region us-central1
```

### Issue: "No buildpack groups passed detection"

**Solution:** The Dockerfile was empty. Use the provided Dockerfile or let buildpacks auto-detect.

### View Cloud Run Logs

```powershell
# Recent logs
gcloud run logs read bt-challenge --region us-central1 --limit 50

# Follow logs in real-time
gcloud run logs tail bt-challenge --region us-central1
```

### Check Environment Variables

```powershell
gcloud run services describe bt-challenge --region us-central1 `
  --format="value(spec.template.spec.containers[0].env)"
```

---

## 📊 Metrics & Monitoring

### Key Metrics Tracked

- **Total Jobs**: Number of drawing comparisons processed
- **Success Rate**: Percentage of successful jobs
- **Latency Percentiles**: P50, P95, P99 processing times
- **Hourly Stats**: Objects added/removed/moved per hour
- **Error Rates**: Missing data, validation failures

### Anomaly Detection

The system automatically detects:
- **Spikes**: >10x increase in changes
- **Missing Data**: >5% jobs with missing files
- **High Failure Rate**: <90% success rate

### View Metrics

```powershell
# Via API
curl.exe https://YOUR-SERVICE-URL/metrics

# Health check with warnings
curl.exe https://YOUR-SERVICE-URL/health
```

---

## 🚀 Performance & Scaling

- **Concurrent Processing**: Cloud Run auto-scales 0-100 instances
- **Throughput**: Handles thousands of drawing pairs
- **Latency**: P99 < 10 seconds for typical drawings
- **Fault Tolerance**: Automatic retries via Pub/Sub

---

## 📝 Project Structure

```
bt-challenge/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── diff.py          # Change detection logic
│   └── metrics.py       # Metrics tracking
├── tests/
│   ├── test_diff.py     # Diff algorithm tests
│   └── test_metrics.py  # Metrics tests
├── tools/
│   └── simulator.py     # Data generator
├── sample/
│   ├── vA.json          # Sample version A
│   ├── vB.json          # Sample version B
│   ├── manifest.json    # Job manifest
│   └── DRAWING-*.json   # Generated samples
├── .env                 # Environment variables (create this)
├── .env.example         # Environment template
├── .gitignore           # Git ignore rules
├── .gcloudignore        # Cloud deployment ignore rules
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
├── PLAN.md             # Implementation plan
└── README.md           # This file
```

---

## 🎓 Additional Resources

- [Google Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Pub/Sub Push Subscriptions](https://cloud.google.com/pubsub/docs/push)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Gemini API Documentation](https://ai.google.dev/docs)

---

## 📄 License

This project is for the BuildTrace technical interview challenge.

---

## 🤝 Support

For questions or issues:
1. Check the [Troubleshooting](#-troubleshooting) section
2. Review Cloud Run logs: `gcloud run logs read bt-challenge`
3. Check the [PLAN.md](PLAN.md) for architecture details

---

**Built with ❤️ using Python, FastAPI, Google Cloud, and Gemini AI**

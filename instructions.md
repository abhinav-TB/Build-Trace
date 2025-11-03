Here's the complete guide to run the BuildTrace project:

```markdown
# 🚀 How to Run BuildTrace

## Prerequisites

- Python 3.8+ installed
- Google Cloud Platform account (for deployment)
- Gemini API key (for AI-powered summaries)

## Local Development Setup

### 1. Clone and Navigate to Project
```bash
cd d:\procjects\BuildTrace\bt-challenge
```

### 2. Create Virtual Environment (if not exists)
```bash
python -m venv env
```

### 3. Activate Virtual Environment
**Windows PowerShell:**
```powershell
.\env\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
env\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source env/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a .env file in the project root:
```bash
# Copy the example file
cp .env.example .env
```

Edit .env with your values:
```env
# GCP Configuration
PROJECT_ID=your-gcp-project-id
BUCKET=bt-challenge-yourname
TOPIC_ID=bt-jobs

# Gemini AI Configuration
GEMINI_API_KEY=your-gemini-api-key-here
USE_GEMINI=true

# Optional: Service URL (set after deployment)
SERVICE_URL=
```

### 6. Run the Application Locally
```bash
uvicorn app.main:app --reload --port 8080
```

The API will be available at: `http://localhost:8080`

### 7. Test the API

**Check health:**
```bash
curl http://localhost:8080/
```

**View API docs:**
Open browser: `http://localhost:8080/docs`

**Get metrics:**
```bash
curl http://localhost:8080/metrics
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
pytest tests/test_diff.py -v
pytest tests/test_metrics.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

## Generate Sample Data

### Create Test Drawing Pairs
```bash
python tools/simulator.py --pairs 10 --output ./sample
```

### Test the Diff Function
```bash
python -c "
from app.diff import diff
import json

# Load sample data
with open('sample/vA.json') as f:
    vA = json.load(f)
with open('sample/vB.json') as f:
    vB = json.load(f)

# Run diff
result = diff(vA, vB)
print(json.dumps(result, indent=2))
"
```

## Cloud Deployment (Google Cloud Run)

### 1. Set Up GCP
```bash
# Install gcloud CLI (if not installed)
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID

# Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### 2. Create GCP Resources
```bash
# Set variables
export PROJECT_ID=your-project-id
export BUCKET=gs://bt-challenge-yourname
export TOPIC_ID=bt-jobs
export REGION=us-central1

# Create bucket
gsutil mb -p $PROJECT_ID $BUCKET

# Create Pub/Sub topic
gcloud pubsub topics create $TOPIC_ID
```

### 3. Deploy to Cloud Run

**Using the deployment script (Linux/Mac):**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Using PowerShell script (Windows):**
```powershell
.\deploy.ps1
```

**Manual deployment:**
```bash
# Build and deploy
gcloud run deploy bt-challenge \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID,BUCKET=$BUCKET,TOPIC_ID=$TOPIC_ID,GEMINI_API_KEY=your-key

# Get service URL
gcloud run services describe bt-challenge --region us-central1 --format 'value(status.url)'
```

### 4. Create Pub/Sub Push Subscription
```bash
export SERVICE_URL=$(gcloud run services describe bt-challenge --region us-central1 --format 'value(status.url)')

gcloud pubsub subscriptions create bt-jobs-sub \
  --topic $TOPIC_ID \
  --push-endpoint=$SERVICE_URL/worker \
  --ack-deadline=60
```

## Using the System

### 1. Upload Sample Data to GCS
```bash
# Generate sample data
python tools/simulator.py --pairs 5 --output ./sample

# Upload to GCS
gsutil -m cp sample/*.json $BUCKET/inputs/
```

### 2. Submit Processing Jobs

Create a manifest file (`manifest.json`):
```json
{
  "pairs": [
    {
      "id": "drawing-001",
      "a": "gs://bt-challenge-yourname/inputs/drawing-001_A.json",
      "b": "gs://bt-challenge-yourname/inputs/drawing-001_B.json"
    }
  ]
}
```

Submit jobs:
```bash
curl -X POST http://localhost:8080/process \
  -H "Content-Type: application/json" \
  -d @manifest.json
```

### 3. Check Results
```bash
# View metrics
curl http://localhost:8080/metrics

# View health status
curl http://localhost:8080/health

# Download results from GCS
gsutil cat gs://bt-challenge-yourname/results/drawing-001.json
```

## Troubleshooting

### Port Already in Use
```bash
# Change port
uvicorn app.main:app --reload --port 8081
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### GCP Authentication Issues
```bash
# Re-authenticate
gcloud auth application-default login
```

### Gemini API Errors
- Verify your API key is correct in .env
- Check you have Gemini API enabled in your Google Cloud Console
- Set `USE_GEMINI=false` to disable AI summaries temporarily

## Project Structure
```
bt-challenge/
├── app/
│   ├── main.py          # FastAPI application
│   ├── diff.py          # Change detection logic
│   └── metrics.py       # Metrics tracking
├── tests/
│   ├── test_diff.py     # Diff tests
│   └── test_metrics.py  # Metrics tests
├── tools/
│   └── simulator.py     # Data generator
├── sample/
│   ├── vA.json          # Sample version A
│   ├── vB.json          # Sample version B
│   └── manifest.json    # Job manifest
├── .env                 # Environment variables (create this)
├── .env.example         # Environment template
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
└── README.md           # Documentation
```

## Quick Commands Reference

| Task | Command |
|------|---------|
| Install dependencies | `pip install -r requirements.txt` |
| Run locally | `uvicorn app.main:app --reload --port 8080` |
| Run tests | `pytest tests/ -v` |
| Generate sample data | `python simulator.py --pairs 10` |
| View API docs | Open `http://localhost:8080/docs` |
| Check metrics | `curl http://localhost:8080/metrics` |
| Deploy to Cloud Run | deploy.sh or deploy.ps1 |

## Next Steps

1. ✅ Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. ✅ Set up your .env file with credentials
3. ✅ Run the app locally and test with sample data
4. ✅ Deploy to Cloud Run for production use
5. ✅ Generate realistic test data with the simulator
6. ✅ Monitor metrics and anomalies via the `/metrics` endpoint

## Support

For issues or questions:
- Check the PLAN.md for architecture details
- Review test files for usage examples
- Check Cloud Run logs: `gcloud run logs read bt-challenge`
```

This is your complete guide! Start with the **Local Development Setup** section and follow the steps in order. The key steps are:

1. Activate virtual environment
2. Install dependencies
3. Create `.env` file with your credentials
4. Run with `uvicorn app.main:app --reload --port 8080`
5. Test at `http://localhost:8080/docs`This is your complete guide! Start with the **Local Development Setup** section and follow the steps in order. The key steps are:

1. Activate virtual environment
2. Install dependencies
3. Create `.env` file with your credentials
4. Run with `uvicorn app.main:app --reload --port 8080`
5. Test at `http://localhost:8080/docs`
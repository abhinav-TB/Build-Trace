# BuildTrace

BuildTrace is a FastAPI-powered platform for comparing construction drawing revisions at scale. It ingests drawing metadata in JSON format, detects added/removed/moved objects, exposes an API and dashboard for managing jobs, and reports detailed metrics so teams can monitor throughput and quality.

## Contents
- [Quick Start](#quick-start)
- [Local Development](#local-development)
- [Configuration](#configuration)
- [Run Locally](#run-locally)
- [Google Cloud Deployment](#google-cloud-deployment)
- [API Endpoints](#api-endpoints)
- [Testing](#testing)
- [Simulator Usage](#simulator-usage)
- [Architecture](#architecture)
- [Scaling & Fault Tolerance](#scaling--fault-tolerance)
- [Metrics Computation Design](#metrics-computation-design)
- [Trade-offs & Future Work](#trade-offs--future-work)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [Resources](#resources)

## Quick Start

### Prerequisites
- Python 3.10+
- `pip` (or another PEP 517 compatible installer)
- (Optional) Google Cloud SDK with access to Pub/Sub, Cloud Run, and Cloud Storage

### Initial Setup
```powershell
# Clone and enter the workspace
git clone <your-fork-url>
cd bt-challenge

# Create a virtual environment (PowerShell)
python -m venv env
./env/Scripts/Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy the example environment configuration
copy .env.example .env
```

## Local Development
- Activate the virtual environment: `./env/Scripts/Activate.ps1`
- Set `USE_GCP=false` in `.env` to run without Google Cloud dependencies.
- Launch the development server with auto-reload:

```powershell
uvicorn app.main:app --reload --port 8080
```

Visit `http://localhost:8080` for the dashboard or `http://localhost:8080/docs` for the automatically generated OpenAPI UI.

## Configuration

The application reads configuration from environment variables (see `.env.example`). Key settings:

| Variable | Required | Description |
| -------- | -------- | ----------- |
| `USE_GCP` | yes | `false` for local mode, `true` to enable Google Cloud integrations |
| `PROJECT_ID` | when `USE_GCP=true` | Google Cloud project identifier |
| `BUCKET` | when `USE_GCP=true` | Cloud Storage bucket URI (e.g. `gs://bt-challenge-sample`) |
| `TOPIC_ID` | when `USE_GCP=true` | Pub/Sub topic used for job dispatch |
| `LOCATION` | optional | Region for storage and deployment (defaults to `us-central1`) |
| `SERVICE_URL` | optional | Populated after deploying to Cloud Run for convenience |

## Run Locally

```powershell
# Start the API
uvicorn app.main:app --reload --port 8080

# Check service status
curl.exe http://localhost:8080/

# Submit a local diff job (omits Google Cloud)
curl.exe -X POST http://localhost:8080/analyze `
  -H "Content-Type: application/json" `
  -d '{
    "version_a": [{"id":"A1","type":"wall","x":10,"y":5,"width":8,"height":1}],
    "version_b": [
      {"id":"A1","type":"wall","x":12,"y":5,"width":8,"height":1},
      {"id":"W1","type":"window","x":3,"y":1,"width":2,"height":1}
    ]
  }'
```

## Google Cloud Deployment

1. **Enable APIs**
   ```powershell
   gcloud services enable run.googleapis.com `
     pubsub.googleapis.com `
     storage.googleapis.com `
     cloudbuild.googleapis.com `
     artifactregistry.googleapis.com
   ```

2. **Create resources**
   ```powershell
   $PROJECT_ID = "your-project-id"
   $BUCKET_NAME = "bt-challenge-yourname"
   $LOCATION = "us-central1"
   $TOPIC_ID = "bt-jobs"

   gcloud config set project $PROJECT_ID
   gsutil mb -p $PROJECT_ID -l $LOCATION gs://$BUCKET_NAME
   gcloud pubsub topics create $TOPIC_ID
   ```

3. **Deploy to Cloud Run**
   ```powershell
   gcloud run deploy bt-challenge `
     --source . `
     --platform managed `
     --region $LOCATION `
     --allow-unauthenticated `
     --set-env-vars "PROJECT_ID=$PROJECT_ID,BUCKET=gs://$BUCKET_NAME,TOPIC_ID=$TOPIC_ID,USE_GCP=true"
   ```

4. **Create a push subscription**
   ```powershell
   $SERVICE_URL = gcloud run services describe bt-challenge --region $LOCATION --format="value(status.url)"

   gcloud pubsub subscriptions create bt-jobs-sub `
     --topic $TOPIC_ID `
     --push-endpoint="$SERVICE_URL/worker" `
     --ack-deadline=60
   ```

5. **Upload sample inputs**
   ```powershell
   gcloud storage cp "sample/*.json" gs://$BUCKET_NAME/inputs/
   ```

6. **Submit work**
   ```powershell
   curl.exe -X POST "$SERVICE_URL/process" `
     -H "Content-Type: application/json" `
     -d "@sample/manifest.json"
   ```

7. **Inspect results and metrics**
   ```powershell
   gcloud storage ls gs://$BUCKET_NAME/results/
   curl.exe "$SERVICE_URL/metrics"
   curl.exe "$SERVICE_URL/health"
   ```

## API Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| GET | `/` | Dashboard entry point and service metadata |
| POST | `/process` | Validate a manifest and enqueue jobs to Pub/Sub |
| POST | `/worker` | Pub/Sub push endpoint that performs the diff (internal) |
| POST | `/analyze` | Run the diff engine locally without cloud services |
| GET | `/metrics` | Snapshot of latency percentiles, success rate, and change counts |
| GET | `/health` | Health report with anomaly warnings |
| GET | `/changes` | Retrieve stored results for a drawing ID |
| GET | `/api/list-inputs` | List drawing pairs discoverable in Cloud Storage |
| POST | `/api/generate-data` | Invoke the simulator to create test data |

## Testing

```powershell
# Run the full test suite
pytest tests/ -v

# Focus on a specific module
pytest tests/test_diff.py -v
pytest tests/test_metrics.py -v

# Optional: collect coverage
pytest tests/ --cov=app --cov-report=term-missing
```

## Simulator Usage

Command-line generator:
```powershell
# Produce five drawing pairs locally
python tools/simulator.py --pairs 5 --output ./sample

# Generate larger change sets
python tools/simulator.py --pairs 5 --profile large --output ./sample

# Upload directly to Cloud Storage and emit a manifest
python tools/simulator.py --pairs 20 `
  --output gs://$BUCKET_NAME/inputs `
  --manifest gs://$BUCKET_NAME/manifest.json
```

Dashboard integration:
- Use the **Generate Data** tab to produce sample drawings on demand.
- Use the **Submit Jobs** tab to enqueue manifest entries against the active deployment.

## Architecture

```
┌──────────────────┐
│      Client      │
└────────┬─────────┘
         │
         ▼
┌────────────────────────────┐
│     Cloud Run (FastAPI)    │
│ ┌────────┐  ┌────────────┐ │
│ │/process│  │  /metrics  │ │
│ │/analyze│  │  /health   │ │
│ └──┬─────┘  └────┬───────┘ │
└────┼──────────────┼────────┘
     │              │
     ▼              ▼
┌────────────┐   ┌────────────────────┐
│  Pub/Sub   │   │   Cloud Storage    │
│   Topic    │   │ inputs/  results/  │
└────┬───────┘   └──────────┬────────┘
     │                      │
     ▼                      ▼
┌────────────┐        ┌──────────────┐
│ /worker    │        │ Result APIs  │
└────────────┘        └──────────────┘
```

1. `/process` validates manifests and publishes one Pub/Sub message per drawing pair.
2. `/worker` fetches the referenced JSON files, runs the diff, writes results to `results/{id}.json`, and records metrics.
3. `/metrics` and `/health` expose in-memory statistics that power the dashboard.
4. `/changes` streams stored analysis results back to clients.

## Scaling & Fault Tolerance
- Cloud Run scales instances horizontally based on concurrent request load.
- Pub/Sub buffers spikes in work and automatically retries failed deliveries with exponential backoff.
- The worker logic is idempotent: reprocessing a message overwrites the same result file safely.
- Local mode (`USE_GCP=false`) keeps a fast feedback loop for development when cloud services are unavailable.

Known limitations:
- Metrics live in process memory, so multi-instance deployments produce per-instance views and data resets when an instance recycles.
- Concurrent requests for the same drawing ID overwrite the same result document (no history is kept yet).

## Metrics Computation Design
- **Latency percentiles** (`p50`, `p95`, `p99`) are calculated by storing completion times for successful jobs, sorting them, and selecting the index at the desired percentile.
- **Success rate** counts both successful and failed jobs, returning `(successful / total) * 100`.
- **Change statistics** bucket added/removed/moved counts per hour, enabling both aggregate totals and per-hour spikes.
- **Anomaly detection** flags high failure rates (>10% of recent jobs), missing inputs (>5%), sudden change spikes (recent hour >10× historical median or >40 when baseline is low), and idle periods with no completions in the last hour.

## Trade-offs & Future Work
- In-memory metrics keep the implementation simple but require external aggregation (Cloud Monitoring, Redis, or Firestore) for production-grade observability.
- JSON payloads are easy to inspect but can become large; binary formats or streaming diffs would reduce latency for huge drawings.
- Polling `/changes` keeps the architecture simple; adding webhooks or WebSocket streams would improve responsiveness.
- The service ships without authentication for challenge simplicity; real deployments should add IAM or API keys and tighten CORS.
- Single-region deployment minimizes cost yet leaves the platform vulnerable to regional outages; multi-region rollouts and dual-bucket storage are natural next steps.

## Troubleshooting

| Symptom | Probable Cause | Recommended Fix |
| ------- | -------------- | --------------- |
| `GCP is not configured` error | Missing env vars while `USE_GCP=true` | Set `PROJECT_ID`, `BUCKET`, and `TOPIC_ID` in `.env` or Cloud Run configuration |
| `No module named google.cloud` | Dependencies not installed in the active environment | Run `pip install -r requirements.txt` inside the virtual environment |
| Pub/Sub messages retry repeatedly | Subscription not pointing at the correct URL | Recreate the push subscription with `/worker` endpoint from the deployed service URL |
| Environment variables concatenated in Cloud Run | Missing quotation marks around `--set-env-vars` | Quote the entire key/value string when deploying or updating the service |
| PowerShell line continuation errors | Using backslashes instead of the PowerShell backtick | Replace `\` continuations with `` ` `` in Cloud SDK commands |

Inspect Cloud Run logs if an issue persists:
```powershell
gcloud run logs tail bt-challenge --region $LOCATION
```

## Project Structure

```
bt-challenge/
├── app/
│   ├── diff.py          # Change detection engine
│   ├── main.py          # FastAPI application and routing
│   ├── metrics.py       # In-memory metrics tracker
│   └── simulator.py     # Shared simulator helpers
├── tools/simulator.py   # CLI wrapper for generating sample data
├── sample/              # Example drawing pairs and manifest
├── tests/               # Unit tests for diffing and metrics logic
├── Dockerfile           # Container build instructions
├── deploy.ps1 / deploy.sh
├── requirements.txt
├── PLAN.md
└── README.md
```

## Resources
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cloud Run](https://cloud.google.com/run/docs)
- [Google Cloud Pub/Sub](https://cloud.google.com/pubsub/docs)
- [Google Cloud Storage](https://cloud.google.com/storage/docs)

---

Built with Python, FastAPI, and Google Cloud services for the BuildTrace technical challenge.

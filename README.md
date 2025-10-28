> 🧭 **Instructions for Candidates**
>
> - Clone this repo and build on top of it.  
> - Don’t worry about adding real secrets; use environment variables locally.  
> - Aim to complete a working vertical slice in 2–3 hours.  
> - See the main README for build/deploy commands.

# BuildTrace Challenge – Cloud Run + Pub/Sub Vertical Slice

## What this service does
- `POST /process`: enqueue comparison jobs from a manifest of GCS URIs
- `POST /worker`: **Pub/Sub push** endpoint; fetches two JSONs from GCS, diffs, writes result JSON to `gs://<bucket>/results/{id}.json`
- `GET /metrics`: in-memory `{p50,p95,p99,jobs_*}` since process start

## Prereqs
- gcloud CLI, a GCP project
- Enable APIs: `gcloud services enable run.googleapis.com pubsub.googleapis.com storage.googleapis.com`
- Create a bucket and a topic:
  ```bash
  export PROJECT_ID=<your-project>
  export BUCKET=gs://bt-challenge-<yourname>
  export TOPIC_ID=bt-jobs
  gcloud config set project $PROJECT_ID
  gsutil mb -p $PROJECT_ID $BUCKET || true
  gcloud pubsub topics create $TOPIC_ID || true

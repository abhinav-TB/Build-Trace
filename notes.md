gcloud run deploy bt-challenge `
  --source . `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars "PROJECT_ID=build-trace,BUCKET=gs://bt-challenge-abhinav/,TOPIC_ID=bt-jobs,USE_GCP=true"

Service URL: https://bt-challenge-544593296841.us-central1.run.app

gcloud pubsub subscriptions create bt-jobs-sub --topic bt-jobs --push-endpoint=https://bt-challenge-544593296841.us-central1.run.app/worker --ack-deadline=60

gcloud storage cp "sample/*.json" gs://bt-challenge-abhinav/inputs/

curl.exe https://bt-challenge-544593296841.us-central1.run.app/changes?drawing_id=sample-drawing-001     

curl.exe -X POST https://bt-challenge-544593296841.us-central1.run.app/process -H "Content-Type: application/json" -d "@manifest.json"   
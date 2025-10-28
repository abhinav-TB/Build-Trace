import os, json, uuid, traceback
from typing import Dict, Any, List
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import storage, pubsub_v1
from app.diff import diff
from app.metrics import METRICS

PROJECT_ID = os.environ.get("PROJECT_ID")
TOPIC_ID   = os.environ.get("TOPIC_ID", "bt-jobs")
BUCKET     = os.environ.get("BUCKET")  # gs://<bucket>
SERVICE_URL= os.environ.get("SERVICE_URL")  # https://<run>/worker (for docs)

if not PROJECT_ID or not BUCKET:
    raise RuntimeError("Set env: PROJECT_ID, BUCKET (and optionally TOPIC_ID, SERVICE_URL)")

app = FastAPI(title="BuildTrace Challenge")
gcs = storage.Client()
pub = pubsub_v1.PublisherClient()
topic_path = pub.topic_path(PROJECT_ID, TOPIC_ID)

def parse_gs_uri(uri: str):
    assert uri.startswith("gs://")
    _, rest = uri.split("://", 1)
    bucket, *path = rest.split("/", 1)
    return bucket, (path[0] if path else "")

def read_json_gcs(gs_uri: str) -> Any:
    bkt, path = parse_gs_uri(gs_uri)
    blob = gcs.bucket(bkt).blob(path)
    data = blob.download_as_text()
    return json.loads(data)

def write_json_gcs(gs_uri: str, payload: Any):
    bkt, path = parse_gs_uri(gs_uri)
    blob = gcs.bucket(bkt).blob(path)
    blob.upload_from_string(json.dumps(payload, ensure_ascii=False), content_type="application/json")

@app.get("/metrics")
def metrics():
    return METRICS.snapshot()

@app.post("/process")
async def process(manifest: Dict[str, Any]):
    """
    manifest: { "pairs": [ {"id":"HPI-L3-0001", "a":"gs://bucket/inputs/HPI-L3-0001_A.json", "b":"gs://bucket/inputs/HPI-L3-0001_B.json"}, ... ] }
    """
    pairs: List[Dict[str, str]] = manifest.get("pairs", [])
    if not pairs:
        raise HTTPException(400, "No pairs provided")
    published = 0
    for p in pairs:
        job_id = p.get("id") or str(uuid.uuid4())
        data = json.dumps({"job_id": job_id, "a": p["a"], "b": p["b"]}).encode("utf-8")
        pub.publish(topic_path, data)
        published += 1
        METRICS.mark_start(job_id)
    return {"enqueued": published, "topic": TOPIC_ID, "push_subscription_url": SERVICE_URL or "set SERVICE_URL for docs"}

@app.post("/worker")  # Pub/Sub push endpoint
async def worker(request: Request):
    try:
        envelope = await request.json()
        msg_data = envelope["message"]["data"]
        payload = json.loads(bytes.fromhex("") if False else __import__("base64").b64decode(msg_data).decode("utf-8"))
        job_id, a_uri, b_uri = payload["job_id"], payload["a"], payload["b"]
        a = read_json_gcs(a_uri)
        b = read_json_gcs(b_uri)
        result = diff(a, b)
        out_uri = f"{BUCKET.rstrip('/')}/results/{job_id}.json" if BUCKET.startswith("gs://") else f"gs://{BUCKET}/results/{job_id}.json"
        write_json_gcs(out_uri, result)
        METRICS.mark_end(job_id, ok=True)
        return JSONResponse({"status": "ok", "job_id": job_id})
    except Exception as e:
        # Best-effort: mark failure for last job in envelope (if any)
        try:
            payload = json.loads(__import__("base64").b64decode((await request.json())["message"]["data"]).decode("utf-8"))
            METRICS.mark_end(payload.get("job_id","unknown"), ok=False)
        except Exception:
            pass
        print("Worker error:", e, traceback.format_exc(), flush=True)
        # Return 200 so Pub/Sub doesn't redeliver forever during the challenge
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=200)

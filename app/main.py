import os, json, uuid, traceback
from typing import Dict, Any, List, Optional
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from app.diff import diff
from app.metrics import METRICS
import sys

# Add project root to Python path for tools module
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

PROJECT_ID = os.environ.get("PROJECT_ID")
TOPIC_ID   = os.environ.get("TOPIC_ID", "bt-jobs")
BUCKET     = os.environ.get("BUCKET")  # gs://<bucket>
SERVICE_URL= os.environ.get("SERVICE_URL")  # https://<run>/worker (for docs)
USE_GCP = os.environ.get("USE_GCP", "false").lower() == "true"

# Initialize GCP clients only if credentials are available
gcs = None
pub = None
topic_path = None

if USE_GCP:
    try:
        from google.cloud import storage, pubsub_v1
        
        if not PROJECT_ID or not BUCKET:
            raise RuntimeError("Set env: PROJECT_ID, BUCKET (and optionally TOPIC_ID, SERVICE_URL)")
        
        gcs = storage.Client()
        pub = pubsub_v1.PublisherClient()
        topic_path = pub.topic_path(PROJECT_ID, TOPIC_ID)
        print("✓ GCP clients initialized successfully")
    except Exception as e:
        print(f"⚠ Warning: GCP initialization failed: {e}")
        print("Running in local-only mode. GCP features disabled.")
        USE_GCP = False
else:
    print("ℹ Running in local-only mode (USE_GCP=false). Set USE_GCP=true to enable Cloud Storage and Pub/Sub.")

app = FastAPI(title="BuildTrace Challenge")

# Mount static files for UI
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

def parse_gs_uri(uri: str):
    assert uri.startswith("gs://"), f"Invalid GCS URI: {uri}"
    _, rest = uri.split("://", 1)
    bucket, *path = rest.split("/", 1)
    return bucket, (path[0] if path else "")

def read_json_gcs(gs_uri: str) -> Any:
    """Read and parse JSON from Google Cloud Storage."""
    if not USE_GCP or gcs is None:
        raise RuntimeError("GCP is not configured. Set USE_GCP=true and configure credentials.")
    
    try:
        bkt, path = parse_gs_uri(gs_uri)
        blob = gcs.bucket(bkt).blob(path)
        
        if not blob.exists():
            raise FileNotFoundError(f"File not found: {gs_uri}")
        
        data = blob.download_as_text()
        return json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {gs_uri}: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Failed to read {gs_uri}: {str(e)}")

def write_json_gcs(gs_uri: str, payload: Any):
    """Write JSON to Google Cloud Storage."""
    if not USE_GCP or gcs is None:
        raise RuntimeError("GCP is not configured. Set USE_GCP=true and configure credentials.")
    
    bkt, path = parse_gs_uri(gs_uri)
    blob = gcs.bucket(bkt).blob(path)
    blob.upload_from_string(json.dumps(payload, ensure_ascii=False, indent=2), content_type="application/json")

def read_json_local(file_path: str) -> Any:
    """Read and parse JSON from local file system."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {file_path}: {str(e)}")

def write_json_local(file_path: str, payload: Any):
    """Write JSON to local file system."""
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def validate_drawing_objects(objects: List[Dict]) -> List[str]:
    """
    Validate drawing objects have required fields.
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    if not isinstance(objects, list):
        return ["Drawing must be a list of objects"]
    
    for i, obj in enumerate(objects):
        if not isinstance(obj, dict):
            errors.append(f"Object {i} is not a dictionary")
            continue
        
        # Check required fields
        if "id" not in obj:
            errors.append(f"Object {i} missing 'id' field")
        if "type" not in obj:
            errors.append(f"Object {i} missing 'type' field")
        if "x" not in obj:
            errors.append(f"Object {i} missing 'x' coordinate")
        if "y" not in obj:
            errors.append(f"Object {i} missing 'y' coordinate")
    
    return errors

@app.get("/")
def root():
    """Serve the web UI."""
    ui_path = Path(__file__).parent / "static" / "index.html"
    if ui_path.exists():
        return FileResponse(ui_path)
    
    # Fallback to API info if UI not found
    return {
        "service": "BuildTrace Drawing Change Analysis",
        "version": "1.0.0",
        "mode": "GCP" if USE_GCP else "Local",
        "endpoints": {
            "POST /process": "Submit drawing pairs for analysis" + (" (requires GCP)" if not USE_GCP else ""),
            "POST /worker": "Pub/Sub worker endpoint (internal)" + (" (requires GCP)" if not USE_GCP else ""),
            "GET /changes": "Retrieve analysis results",
            "GET /metrics": "System metrics, health status, and anomaly detection",
            "POST /analyze": "Analyze local drawing pair (local mode)"
        }
    }

@app.get("/api/info")
def api_info():
    """API information endpoint for the UI."""
    return {
        "service": "BuildTrace Drawing Change Analysis",
        "version": "1.0.0",
        "gcp_enabled": USE_GCP,
        "mode": "GCP" if USE_GCP else "Local",
        "endpoints": {
            "POST /process": "Submit drawing pairs for analysis" + (" (requires GCP)" if not USE_GCP else ""),
            "POST /worker": "Pub/Sub worker endpoint (internal)" + (" (requires GCP)" if not USE_GCP else ""),
            "GET /changes": "Retrieve analysis results",
            "GET /metrics": "System metrics, health status, and anomaly detection",
            "POST /analyze": "Analyze local drawing pair (local mode)"
        }
    }

@app.get("/api/list-inputs")
def list_inputs():
    """List available input files from Cloud Storage."""
    if not USE_GCP or not gcs:
        raise HTTPException(
            status_code=503,
            detail="GCP is not configured. This endpoint requires Cloud Storage access."
        )
    
    try:
        bucket_name = BUCKET.replace("gs://", "").rstrip("/")
        bucket = gcs.bucket(bucket_name)
        
        # List all JSON files in inputs/ prefix
        blobs = bucket.list_blobs(prefix="inputs/")
        
        # Group files by drawing ID
        pairs = {}
        for blob in blobs:
            if blob.name.endswith(".json"):
                # Extract drawing ID from filename
                filename = blob.name.split("/")[-1]
                if "_vA.json" in filename:
                    drawing_id = filename.replace("_vA.json", "")
                    if drawing_id not in pairs:
                        pairs[drawing_id] = {}
                    pairs[drawing_id]["a"] = f"gs://{bucket_name}/{blob.name}"
                elif "_vB.json" in filename:
                    drawing_id = filename.replace("_vB.json", "")
                    if drawing_id not in pairs:
                        pairs[drawing_id] = {}
                    pairs[drawing_id]["b"] = f"gs://{bucket_name}/{blob.name}"
        
        # Filter to only complete pairs
        complete_pairs = []
        for drawing_id, files in pairs.items():
            if "a" in files and "b" in files:
                complete_pairs.append({
                    "id": drawing_id,
                    "a": files["a"],
                    "b": files["b"]
                })
        
        return {
            "bucket": f"gs://{bucket_name}",
            "total_pairs": len(complete_pairs),
            "pairs": sorted(complete_pairs, key=lambda x: x["id"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

@app.post("/api/generate-data")
async def generate_data(
    pairs: int = Query(10, ge=1, le=100, description="Number of pairs to generate"),
    profile: str = Query("medium", regex="^(none|small|medium|large|spike)$"),
    mixed_profiles: bool = Query(False, description="Use random profile for each pair"),
    base_size: int = Query(20, ge=5, le=100, description="Number of objects in base drawing")
):
    """
    Generate simulated drawing pairs and upload to Cloud Storage.
    
    Args:
        pairs: Number of drawing pairs to generate (1-100)
        profile: Change profile (none, small, medium, large, spike)
        mixed_profiles: Use random profiles for variety
        base_size: Number of objects in base drawing (5-100)
    """
    if not USE_GCP or not gcs:
        raise HTTPException(
            status_code=503,
            detail="GCP is not configured. This endpoint requires Cloud Storage access."
        )
    
    try:
        from app import simulator
        import random
        
        bucket_name = BUCKET.replace("gs://", "").rstrip("/")
        bucket = gcs.bucket(bucket_name)
        
        generated_pairs = []
        profiles = ["none", "small", "medium", "large", "spike"] if mixed_profiles else [profile]
        
        # Find the next available drawing number
        existing_blobs = list(bucket.list_blobs(prefix="inputs/DRAWING-"))
        existing_numbers = []
        for blob in existing_blobs:
            filename = blob.name.split("/")[-1]
            if filename.startswith("DRAWING-") and "_v" in filename:
                try:
                    num = int(filename.split("-")[1].split("_")[0])
                    existing_numbers.append(num)
                except:
                    pass
        
        start_number = max(existing_numbers) + 1 if existing_numbers else 1
        
        for i in range(pairs):
            drawing_id = f"DRAWING-{start_number + i:04d}"
            selected_profile = random.choice(profiles) if mixed_profiles else profile
            
            # Generate pair
            version_a, version_b = simulator.generate_pair(drawing_id, selected_profile, base_size)
            
            # Upload to GCS
            file_a = f"inputs/{drawing_id}_vA.json"
            file_b = f"inputs/{drawing_id}_vB.json"
            
            blob_a = bucket.blob(file_a)
            blob_a.upload_from_string(json.dumps(version_a, indent=2), content_type="application/json")
            
            blob_b = bucket.blob(file_b)
            blob_b.upload_from_string(json.dumps(version_b, indent=2), content_type="application/json")
            
            generated_pairs.append({
                "id": drawing_id,
                "a": f"gs://{bucket_name}/{file_a}",
                "b": f"gs://{bucket_name}/{file_b}",
                "profile": selected_profile
            })
        
        return {
            "status": "success",
            "generated": len(generated_pairs),
            "bucket": f"gs://{bucket_name}",
            "pairs": generated_pairs,
            "settings": {
                "profile": profile if not mixed_profiles else "mixed",
                "base_size": base_size,
                "mixed_profiles": mixed_profiles
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating data: {str(e)}")

@app.post("/analyze")
async def analyze_local(version_a: List[Dict[str, Any]], version_b: List[Dict[str, Any]]):
    """
    Analyze two drawing versions directly (for local development without GCP).
    
    Args:
        version_a: List of objects in version A
        version_b: List of objects in version B
    
    Returns:
        Change detection results
    """
    job_id = str(uuid.uuid4())
    
    try:
        METRICS.mark_start(job_id)
        
        # Validate objects
        errors_a = validate_drawing_objects(version_a)
        errors_b = validate_drawing_objects(version_b)
        
        if errors_a or errors_b:
            METRICS.mark_end(job_id, ok=False)
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid drawing format",
                    "validation_errors": {
                        "version_a": errors_a,
                        "version_b": errors_b
                    }
                }
            )
        
        # Perform diff
        result = diff(version_a, version_b)
        result["job_id"] = job_id
        result["status"] = "success"
        result["timestamp"] = __import__("datetime").datetime.now().isoformat()
        
        # Update metrics
        METRICS.mark_end(job_id, ok=True, result=result)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        METRICS.mark_end(job_id, ok=False)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.get("/changes")
def get_changes(drawing_id: str = Query(..., description="Drawing ID to retrieve results for")):
    """
    Retrieve detected changes for a specific drawing.
    
    Args:
        drawing_id: The ID of the drawing pair to retrieve
    
    Returns:
        Change detection results or error
    """
    if not USE_GCP:
        raise HTTPException(
            status_code=503,
            detail="GCP is not configured. Use POST /analyze for local analysis."
        )
    
    try:
        # Construct result URI
        bucket_name = BUCKET.replace("gs://", "").rstrip("/")
        result_uri = f"gs://{bucket_name}/results/{drawing_id}.json"
        
        # Read result from Cloud Storage
        result = read_json_gcs(result_uri)
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No results found for drawing ID: {drawing_id}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving results: {str(e)}")

@app.get("/metrics")
def metrics():
    """
    Get comprehensive system metrics with health status and anomaly detection.
    
    Returns:
        - System health status (healthy/warning/degraded)
        - Anomaly warnings
        - Job statistics (total, success rate, latency percentiles)
        - Hourly change statistics
    """
    snapshot = METRICS.snapshot()
    anomalies = METRICS.detect_anomalies()
    success_stats = METRICS.get_success_rate()
    
    # Determine health status
    status = "healthy"
    if len(anomalies) > 0:
        status = "warning"
    if success_stats["total"] > 0 and success_stats["success_rate"] < 50:
        status = "degraded"
    
    # Enhanced response with health info
    return {
        "status": status,
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "warnings": anomalies,
        **snapshot
    }

@app.post("/process")
async def process(manifest: Dict[str, Any]):
    """
    Enqueue drawing comparison jobs from a manifest.
    
    manifest: { "pairs": [ {"id":"...", "a":"gs://...", "b":"gs://..."}, ... ] }
    """
    if not USE_GCP or pub is None:
        raise HTTPException(
            status_code=503,
            detail="GCP is not configured. Use POST /analyze for local analysis."
        )
    
    pairs: List[Dict[str, str]] = manifest.get("pairs", [])
    if not pairs:
        raise HTTPException(400, "No pairs provided in manifest")
    
    published = 0
    errors = []
    
    for p in pairs:
        try:
            job_id = p.get("id") or str(uuid.uuid4())
            
            # Validate required fields
            if "a" not in p or "b" not in p:
                errors.append({"job_id": job_id, "error": "Missing 'a' or 'b' URI"})
                continue
            
            # Validate URIs
            if not p["a"].startswith("gs://") or not p["b"].startswith("gs://"):
                errors.append({"job_id": job_id, "error": "URIs must start with gs://"})
                continue
            
            data = json.dumps({"job_id": job_id, "a": p["a"], "b": p["b"]}).encode("utf-8")
            pub.publish(topic_path, data)
            published += 1
            METRICS.mark_start(job_id)
        except Exception as e:
            errors.append({"job_id": p.get("id", "unknown"), "error": str(e)})
    
    response = {
        "enqueued": published,
        "topic": TOPIC_ID,
        "push_subscription_url": SERVICE_URL or "set SERVICE_URL for docs"
    }
    
    if errors:
        response["errors"] = errors
    
    return response

@app.post("/worker")  # Pub/Sub push endpoint
async def worker(request: Request):
    """
    Pub/Sub push endpoint for processing drawing comparisons.
    
    Receives job messages, downloads drawings, performs diff, stores results.
    """
    job_id = "unknown"
    try:
        envelope = await request.json()
        msg_data = envelope["message"]["data"]
        payload = json.loads(__import__("base64").b64decode(msg_data).decode("utf-8"))
        
        job_id = payload["job_id"]
        a_uri = payload["a"]
        b_uri = payload["b"]
        
        # Mark job start for metrics tracking
        METRICS.mark_start(job_id)
        
        # Download and validate input files
        try:
            a = read_json_gcs(a_uri)
        except Exception as e:
            error_result = {
                "job_id": job_id,
                "status": "error",
                "error": f"Failed to load version A: {str(e)}",
                "error_type": "missing_data",
                "uri_a": a_uri,
                "uri_b": b_uri
            }
            bucket_name = BUCKET.replace("gs://", "").rstrip("/")
            out_uri = f"gs://{bucket_name}/results/{job_id}.json"
            write_json_gcs(out_uri, error_result)
            METRICS.mark_error(job_id, "missing_data")
            METRICS.mark_end(job_id, ok=False)
            return JSONResponse({"status": "error", "job_id": job_id, "detail": str(e)}, status_code=200)
        
        try:
            b = read_json_gcs(b_uri)
        except Exception as e:
            error_result = {
                "job_id": job_id,
                "status": "error",
                "error": f"Failed to load version B: {str(e)}",
                "error_type": "missing_data",
                "uri_a": a_uri,
                "uri_b": b_uri
            }
            bucket_name = BUCKET.replace("gs://", "").rstrip("/")
            out_uri = f"gs://{bucket_name}/results/{job_id}.json"
            write_json_gcs(out_uri, error_result)
            METRICS.mark_error(job_id, "missing_data")
            METRICS.mark_end(job_id, ok=False)
            return JSONResponse({"status": "error", "job_id": job_id, "detail": str(e)}, status_code=200)
        
        # Validate objects
        errors_a = validate_drawing_objects(a)
        errors_b = validate_drawing_objects(b)
        
        if errors_a or errors_b:
            error_result = {
                "job_id": job_id,
                "status": "error",
                "error": "Invalid drawing format",
                "error_type": "validation_error",
                "validation_errors": {
                    "version_a": errors_a,
                    "version_b": errors_b
                },
                "uri_a": a_uri,
                "uri_b": b_uri
            }
            bucket_name = BUCKET.replace("gs://", "").rstrip("/")
            out_uri = f"gs://{bucket_name}/results/{job_id}.json"
            write_json_gcs(out_uri, error_result)
            METRICS.mark_error(job_id, "validation_error")
            METRICS.mark_end(job_id, ok=False)
            return JSONResponse({"status": "error", "job_id": job_id, "detail": "Validation failed"}, status_code=200)
        
        # Perform diff
        result = diff(a, b)
        result["job_id"] = job_id
        result["status"] = "success"
        result["uri_a"] = a_uri
        result["uri_b"] = b_uri
        result["timestamp"] = __import__("datetime").datetime.now().isoformat()
        
        # Write result to Cloud Storage
        bucket_name = BUCKET.replace("gs://", "").rstrip("/")
        out_uri = f"gs://{bucket_name}/results/{job_id}.json"
        write_json_gcs(out_uri, result)
        
        # Update metrics with result stats
        METRICS.mark_end(job_id, ok=True, result=result)
        
        return JSONResponse({"status": "ok", "job_id": job_id})
    except Exception as e:
        # Log error and mark failure
        print("Worker error:", e, traceback.format_exc(), flush=True)
        
        try:
            METRICS.mark_end(job_id, ok=False)
        except Exception:
            pass
        
        # Return 200 so Pub/Sub doesn't redeliver forever during the challenge
        return JSONResponse({"status": "error", "job_id": job_id, "detail": str(e)}, status_code=200)



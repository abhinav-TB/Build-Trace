# BuildTrace System - Implementation Plan

## 📋 Executive Summary

This document outlines the complete implementation plan for **BuildTrace** - a cloud-native, large-scale drawing change analysis platform. The system compares construction drawing revisions (simulated as JSON files with geometric objects) and provides analytics, metrics, and anomaly detection at scale.

**Timeline:** 2-3 hours for working vertical slice  
**Target:** Handle thousands of drawing pairs concurrently  
**Cloud Platform:** Google Cloud Platform (Cloud Run, Pub/Sub, Cloud Storage)

---

## 🎯 Project Goals

### Core Requirements
1. ✅ **Detect Changes**: Identify added, deleted, and moved objects between drawing versions
2. ✅ **Natural Language Summary**: Generate human-readable change descriptions
3. ✅ **Scale Horizontally**: Process thousands of drawing pairs efficiently
4. ✅ **Handle Data Quality Issues**: Surface missing versions and inconsistent data
5. ✅ **Analytics & Observability**: Track metrics (P95/P99 latency, throughput, anomalies)

### Deliverables
- Cloud Run deployment with working API endpoints
- Pub/Sub-based asynchronous job processing
- Data simulator for generating test datasets
- Comprehensive README with architecture documentation
- Example commands for system interaction

---

## 🏗️ System Architecture

### High-Level Design

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
│  │           │  │ /health  │           │
│  │ /changes  │  │          │           │
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
│  (Cloud Run Auto-scaling Workers)        │
│  ┌────────────────────────────────────┐  │
│  │  Diff Engine with Gemini AI LLM    │  │
│  │  - Detect added/removed/moved      │  │
│  │  - Generate AI summaries           │  │
│  └────────────────────────────────────┘  │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│        Cloud Storage Buckets             │
│  ┌────────────┐  ┌─────────────────┐    │
│  │   Inputs   │  │    Results      │    │
│  │  vA.json   │  │  {id}.json      │    │
│  │  vB.json   │  │  - changes      │    │
│  └────────────┘  │  - AI summary   │    │
│                  │  - metrics      │    │
│                  └─────────────────┘    │
└──────────────────────────────────────────┘
           ▲
           │
    ┌──────┴───────┐
    │ Gemini API   │
    │ (Optional)   │
    └──────────────┘
```

### ✨ AI-Powered Summaries with Gemini

The system integrates **Google Gemini LLM** for intelligent change summaries:

### ✨ AI-Powered Summaries with Gemini

The system integrates **Google Gemini LLM** for intelligent change summaries:

**With Gemini enabled:**
```
"Door D1 relocated 2.8 units eastward near the main entrance; 
Window W3 added in the northwest corner, providing additional natural light 
to the reception area."
```

**Without Gemini (fallback):**
```
"1 door moved 2.8 units east; 1 window added at (3,1)."
```

**Configuration:**
- Set `GEMINI_API_KEY` environment variable to enable
- Set `USE_GEMINI=false` to disable (uses simple summaries)
- Automatic fallback on API errors or timeouts
- Get API key: https://ai.google.dev/

### Component Breakdown

#### 1. **API Layer (FastAPI on Cloud Run)**
- **POST /process**: Accept manifest of drawing pairs, enqueue to Pub/Sub
- **POST /worker**: Pub/Sub push endpoint for async processing
- **GET /changes?drawing_id=...**: Retrieve detected changes for a drawing
- **GET /metrics**: Return system metrics (latency percentiles, throughput)
- **GET /health**: Health check with anomaly warnings

#### 2. **Job Queue (Cloud Pub/Sub)**
- Topic: `bt-jobs`
- Push subscription → Cloud Run `/worker` endpoint
- Dead-letter queue for malformed messages (stretch goal)
- Automatic retry with exponential backoff

#### 3. **Storage Layer (Cloud Storage)**
- **Input bucket**: `gs://bt-challenge-<user>/inputs/`
  - Stores drawing version JSONs (vA.json, vB.json)
- **Results bucket**: `gs://bt-challenge-<user>/results/`
  - Stores computed diffs and summaries

#### 4. **Processing Engine**
- **diff.py**: Core change detection algorithm
- **metrics.py**: In-memory metrics aggregation (P50/P95/P99 latency)
- **anomaly_detector.py**: Detect spikes and missing data (to be implemented)

---

## 🔧 Implementation Plan

### Phase 1: Core Change Detection (45 min)

**Status:** ✅ Scaffold exists, needs implementation

#### 1.1 Implement Diff Algorithm (`app/diff.py`)
**Current State:** Placeholder function  
**Target State:** Full geometric object comparison

**Algorithm:**
```python
def diff(version_a: List[Dict], version_b: List[Dict]) -> Dict:
    """
    Compare two drawing versions and detect changes.
    
    Returns:
    {
        "added": [list of new objects],
        "removed": [list of deleted objects],
        "moved": [list of objects with changed positions],
        "summary": "Natural language description"
    }
    """
```

**Implementation Steps:**
1. Create object index by ID for both versions
2. Detect added objects (in B but not in A)
3. Detect removed objects (in A but not in B)
4. Detect moved objects (same ID, different x/y coordinates)
5. Generate natural language summary

**Test Cases:**
- Empty versions (handle gracefully)
- Identical versions (no changes)
- All objects added/removed
- Mixed changes (add + remove + move)

#### 1.2 Natural Language Summary Generator
**Location:** `app/diff.py` (helper function)

**Logic:**
```python
def generate_summary(added, removed, moved) -> str:
    """
    Examples:
    - "Door D1 moved 2 units east; Window W1 added near Door D1."
    - "3 walls added, 1 door removed."
    - "No changes detected."
    """
```

**Implementation:**
- Count changes by type
- Describe movement direction (north/south/east/west)
- Highlight significant changes (>10x normal)

---

### Phase 2: Metrics & Observability (30 min)

**Status:** ✅ Basic tracking exists, needs enhancement

#### 2.1 Enhanced Metrics (`app/metrics.py`)

**Current State:** Simple job tracking  
**Target State:** Full percentile-based metrics

**New Features:**
```python
class Metrics:
    def __init__(self):
        self.jobs = {}  # job_id -> {start, end, status}
        self.latencies = []  # list of processing times
        self.hourly_stats = {}  # hour -> {added, removed, moved}
    
    def get_percentile(self, p: int) -> float:
        """Calculate P50/P95/P99 latency"""
    
    def get_hourly_throughput(self) -> Dict:
        """Count added/removed/moved elements per hour"""
    
    def detect_anomalies(self) -> List[str]:
        """Flag missing uploads, spikes in changes"""
```

**Metrics to Track:**
- ✅ Job completion time (start → end)
- ✅ Success/failure rates
- 🔲 P50, P95, P99 latency percentiles
- 🔲 Hourly throughput (objects added/removed/moved)
- 🔲 Data quality (% drawings with missing/corrupted data)

#### 2.2 Health Endpoint (`/health`)

**Response Format:**
```json
{
  "status": "healthy",
  "warnings": [
    "10x spike in added objects detected in last hour",
    "2 drawings missing version B in last 24h"
  ],
  "last_check": "2025-10-31T12:00:00Z"
}
```

---

### Phase 3: Data Quality & Fault Tolerance (20 min)

#### 3.1 Input Validation
**Location:** `app/main.py` (worker endpoint)

**Checks:**
- Validate JSON structure (required fields: id, type, x, y)
- Handle missing files gracefully (return error in result JSON)
- Detect corrupted data (malformed coordinates, missing types)

**Error Handling:**
```python
try:
    a = read_json_gcs(a_uri)
    b = read_json_gcs(b_uri)
except Exception as e:
    result = {
        "job_id": job_id,
        "status": "error",
        "error": f"Failed to load inputs: {str(e)}",
        "error_type": "missing_data"
    }
    write_json_gcs(out_uri, result)
    METRICS.mark_error(job_id, "missing_data")
    return
```

#### 3.2 Retry Logic
**Current:** Pub/Sub handles retries automatically  
**Enhancement:** Add exponential backoff in subscription settings

```bash
gcloud pubsub subscriptions update bt-jobs-sub \
  --min-retry-delay=10s \
  --max-retry-delay=600s
```

---

### Phase 4: Data Simulator (25 min)

**Status:** 🔲 Not yet implemented

#### 4.1 Simulator Script (`tools/simulator.py`)

**Purpose:** Generate N pairs of drawing JSONs with realistic changes

**Features:**
```python
def generate_drawing_pair(drawing_id: str, change_profile: str):
    """
    change_profile options:
    - "small": 1-3 objects changed
    - "medium": 10-20 objects changed
    - "large": 50+ objects changed
    - "spike": 10x normal changes (for anomaly testing)
    """
```

**Object Types:**
- `wall`: Long rectangular structures
- `door`: Small rectangular openings
- `window`: Small rectangular openings (different from doors)

**Usage:**
```bash
python tools/simulator.py \
  --output gs://bt-challenge-user/inputs \
  --pairs 1000 \
  --profile medium
```

#### 4.2 Manifest Generator
**Output:** JSON manifest for `/process` endpoint

```json
{
  "pairs": [
    {
      "id": "HPI-L3-0001",
      "a": "gs://bt-challenge/inputs/HPI-L3-0001_A.json",
      "b": "gs://bt-challenge/inputs/HPI-L3-0001_B.json"
    },
    ...
  ]
}
```

---

### Phase 5: Deployment & Testing (20 min)

#### 5.1 Dockerfile Optimization
**Current:** Basic Python container  
**Enhancements:**
- Multi-stage build for smaller image
- Health check endpoint
- Graceful shutdown handling

#### 5.2 Cloud Run Deployment

**Script:** `deploy.sh`
```bash
#!/bin/bash
set -e

export PROJECT_ID=<your-project>
export REGION=us-central1
export SERVICE_NAME=bt-challenge

# Build and push image
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=$PROJECT_ID,BUCKET=gs://bt-challenge-user,TOPIC_ID=bt-jobs \
  --min-instances 0 \
  --max-instances 100 \
  --concurrency 80

# Create Pub/Sub push subscription
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
gcloud pubsub subscriptions create bt-jobs-sub \
  --topic bt-jobs \
  --push-endpoint=$SERVICE_URL/worker \
  --ack-deadline=60
```

#### 5.3 Testing Strategy

**Unit Tests:**
```bash
pytest tests/test_diff.py
pytest tests/test_metrics.py
```

**Integration Tests:**
```bash
# Upload sample files
gsutil cp sample/vA.json gs://bt-challenge-user/inputs/
gsutil cp sample/vB.json gs://bt-challenge-user/inputs/

# Submit job
curl -X POST https://<service-url>/process -H "Content-Type: application/json" -d @sample/manifest.json

# Check results
gsutil cat gs://bt-challenge-user/results/<job-id>.json

# Verify metrics
curl https://<service-url>/metrics
```

**Load Tests:**
```bash
# Generate 1000 pairs
python tools/simulator.py --pairs 1000 --output gs://bt-challenge-user/inputs

# Submit batch
curl -X POST https://<service-url>/process -d @manifest_1000.json

# Monitor metrics
watch -n 5 'curl https://<service-url>/metrics'
```

---

## 📊 Metrics Computation Design

### P95/P99 Latency Calculation

**Approach:** In-memory quantile approximation (exact for small N, approximate for large N)

```python
import numpy as np

class MetricsTracker:
    def calculate_percentiles(self):
        if len(self.latencies) == 0:
            return {"p50": 0, "p95": 0, "p99": 0}
        
        sorted_latencies = sorted(self.latencies)
        return {
            "p50": np.percentile(sorted_latencies, 50),
            "p95": np.percentile(sorted_latencies, 95),
            "p99": np.percentile(sorted_latencies, 99)
        }
```

**Trade-off:** Exact calculation for vertical slice; migrate to BigQuery for production scale.

### Anomaly Detection

**Rules:**
1. **Spike Detection**: >10x median change count in last hour
2. **Missing Data**: >5% jobs failed due to missing files
3. **Delayed Uploads**: >1 hour gap in job submissions

---

## 🚀 Scaling Strategy

### Horizontal Scaling
- **Cloud Run**: Auto-scales from 0 to 100 instances based on request load
- **Pub/Sub**: Handles message buffering during traffic spikes
- **Concurrency**: 80 concurrent requests per Cloud Run instance

### Cost Optimization
- **Min instances = 0**: No cost when idle
- **Pub/Sub retention**: 7 days (configurable)
- **Cloud Storage lifecycle**: Archive results >90 days old

### Fault Tolerance
- **Pub/Sub dead-letter queue**: Capture malformed messages after 5 retries
- **Graceful degradation**: Return partial results if one file is missing
- **Retry backoff**: Exponential delay (10s → 600s)

---

## 📝 README Structure

### Sections to Include

1. **System Overview**: High-level description
2. **Architecture Diagram**: Visual flow (see above)
3. **Deployment Guide**: Step-by-step Cloud Run setup
4. **API Documentation**: 
   - `POST /process` - Submit jobs
   - `GET /changes?drawing_id=X` - Retrieve results
   - `GET /metrics` - System health
   - `GET /health` - Anomaly alerts
5. **Data Simulator Usage**: How to generate test data
6. **Example Commands**:
   ```bash
   # Submit batch job
   curl -X POST https://<url>/process -d @manifest.json
   
   # Check metrics
   curl https://<url>/metrics
   
   # View results
   gsutil cat gs://bucket/results/job-123.json
   ```
7. **Metrics Computation**: Explain P99 calculation approach
8. **Trade-offs**: Document design decisions
9. **Future Extensions**: 
   - BigQuery integration for long-term metrics
   - UI dashboard for visualization
   - Configurable anomaly thresholds
   - Support for real PDF/CAD file processing

---

## ⚖️ Trade-offs & Design Decisions

### In-Memory Metrics vs. BigQuery
**Decision:** In-memory for vertical slice  
**Rationale:** Faster development, sufficient for 2-3 hour demo  
**Future:** Migrate to BigQuery for persistent storage and advanced analytics

### Synchronous vs. Asynchronous Processing
**Decision:** Async via Pub/Sub  
**Rationale:** Handles bursty traffic, enables horizontal scaling  
**Trade-off:** Adds latency (seconds vs. milliseconds)

### Exact vs. Approximate Percentiles
**Decision:** Exact calculation using NumPy  
**Rationale:** Simple implementation, accurate for <100k jobs  
**Future:** Switch to T-Digest or HdrHistogram for >1M jobs

### Error Handling: Fail vs. Partial Results
**Decision:** Return partial results when possible  
**Rationale:** Better user experience, easier debugging  
**Example:** If vA.json loads but vB.json missing, return error in result JSON (don't fail silently)

---

## 🎯 Success Criteria

### Functional Requirements
- ✅ Correctly detect added/removed/moved objects
- ✅ Generate accurate natural language summaries
- ✅ Handle 1000+ drawing pairs in parallel
- ✅ Surface data quality issues in `/health` endpoint

### Non-Functional Requirements
- ✅ P99 latency < 10 seconds (for typical drawings)
- ✅ Zero dropped messages (Pub/Sub guarantees)
- ✅ Auto-scale from 0 to 100 instances
- ✅ Clean, documented code

### Deliverables Checklist
- [ ] Working Cloud Run deployment
- [ ] Data simulator script
- [ ] Comprehensive README
- [ ] Example commands (submit job, check metrics)
- [ ] Deployment script (`deploy.sh`)

---

## 🔮 Future Extensions (Post-Interview)

1. **BigQuery Integration**
   - Stream metrics to BigQuery for long-term storage
   - Enable complex analytics (time-series trends, anomaly correlation)

2. **Dashboard UI**
   - Real-time metrics visualization
   - Historical trend charts
   - Alert configuration

3. **Advanced Anomaly Detection**
   - Machine learning-based threshold tuning
   - Correlation analysis (e.g., "spikes on Mondays")

4. **PDF/CAD Support**
   - OCR and geometric extraction from real construction drawings
   - Integration with AutoCAD/Revit APIs

5. **Multi-Region Deployment**
   - Deploy to multiple regions for low latency
   - Cross-region replication for disaster recovery

---

## 📅 Implementation Timeline

| Phase | Task | Duration | Priority |
|-------|------|----------|----------|
| 1 | Implement diff algorithm | 30 min | P0 |
| 1 | Add natural language summary | 15 min | P0 |
| 2 | Enhance metrics (P95/P99) | 20 min | P0 |
| 2 | Add /health endpoint | 10 min | P1 |
| 3 | Input validation & error handling | 20 min | P0 |
| 4 | Data simulator | 25 min | P0 |
| 5 | Deployment script | 10 min | P0 |
| 5 | Testing & validation | 20 min | P0 |
| 5 | README documentation | 10 min | P0 |

**Total:** ~160 minutes (2h 40m) → Fits within 2-3 hour target

---

## 🛠️ Development Environment Setup

### Prerequisites
```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login

# Set project
gcloud config set project <your-project-id>

# Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable pubsub.googleapis.com
gcloud services enable storage.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PROJECT_ID=<your-project>
export BUCKET=gs://bt-challenge-local
export TOPIC_ID=bt-jobs

# Run locally
uvicorn app.main:app --reload --port 8080

# Test endpoints
curl http://localhost:8080/metrics
```

---

## 📖 References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Pub/Sub Push Subscriptions](https://cloud.google.com/pubsub/docs/push)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Python Percentile Calculation](https://numpy.org/doc/stable/reference/generated/numpy.percentile.html)

---

**Document Version:** 1.0  
**Last Updated:** October 31, 2025  
**Author:** BuildTrace Development Team

from datetime import datetime
from typing import Dict, Any

class Metrics:
    """Simple metrics tracking for BuildTrace jobs."""

    def __init__(self):
        self.jobs = {}

    def mark_start(self, job_id: str):
        """Mark the start time of a job."""
        self.jobs[job_id] = {
            "start_time": datetime.now().isoformat(),
            "status": "running"
        }

    def mark_end(self, job_id: str, ok: bool):
        """Mark the end time and status of a job."""
        if job_id in self.jobs:
            self.jobs[job_id]["end_time"] = datetime.now().isoformat()
            self.jobs[job_id]["status"] = "success" if ok else "failed"
        else:
            self.jobs[job_id] = {
                "end_time": datetime.now().isoformat(),
                "status": "success" if ok else "failed"
            }

    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of all metrics."""
        return {
            "total_jobs": len(self.jobs),
            "jobs": self.jobs
        }

# Global metrics instance
METRICS = Metrics()
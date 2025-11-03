from datetime import datetime, timedelta
from typing import Dict, Any, List
import statistics
import psutil
import os
import time


class Metrics:
    """Advanced metrics tracking for BuildTrace jobs."""

    def __init__(self):
        self.jobs = {}  # job_id -> {start_time, end_time, status, latency}
        self.latencies = []  # List of processing times in seconds
        self.hourly_stats = {}  # hour -> {added, removed, moved}
        self.errors = []  # List of error events
        self.error_categories = {}  # error_type -> count
        self.start_time = time.time()  # Track instance uptime
        self.active_requests = 0  # Track concurrent requests
        self.process = psutil.Process(os.getpid())  # Current process for system metrics

    def mark_start(self, job_id: str):
        """Mark the start time of a job."""
        self.jobs[job_id] = {
            "start_time": datetime.now(),
            "start_time_iso": datetime.now().isoformat(),
            "status": "running"
        }
        self.active_requests += 1

    def mark_end(self, job_id: str, ok: bool, result: Dict[str, Any] = None):
        """
        Mark the end time and status of a job.
        
        Args:
            job_id: Unique job identifier
            ok: Whether job completed successfully
            result: Optional result dict with stats
        """
        end_time = datetime.now()
        self.active_requests = max(0, self.active_requests - 1)  # Ensure it doesn't go negative
        
        if job_id in self.jobs:
            job = self.jobs[job_id]
            job["end_time"] = end_time
            job["end_time_iso"] = end_time.isoformat()
            job["status"] = "success" if ok else "failed"
            
            # Calculate latency if we have start time
            if "start_time" in job:
                latency = (end_time - job["start_time"]).total_seconds()
                job["latency_seconds"] = latency
                
                if ok:  # Only count successful jobs in latency metrics
                    self.latencies.append(latency)
                    
                    # Track hourly stats if result provided
                    if result and "stats" in result:
                        hour_key = end_time.strftime("%Y-%m-%d %H:00")
                        if hour_key not in self.hourly_stats:
                            self.hourly_stats[hour_key] = {
                                "added": 0,
                                "removed": 0,
                                "moved": 0,
                                "jobs": 0
                            }
                        
                        stats = result["stats"]
                        self.hourly_stats[hour_key]["added"] += stats.get("added_count", 0)
                        self.hourly_stats[hour_key]["removed"] += stats.get("removed_count", 0)
                        self.hourly_stats[hour_key]["moved"] += stats.get("moved_count", 0)
                        self.hourly_stats[hour_key]["jobs"] += 1
        else:
            # Job not found in tracking, create minimal record
            self.jobs[job_id] = {
                "end_time": end_time,
                "end_time_iso": end_time.isoformat(),
                "status": "success" if ok else "failed"
            }
        
        # Track errors
        if not ok:
            self.errors.append({
                "job_id": job_id,
                "timestamp": end_time.isoformat(),
                "type": "processing_error"
            })

    def mark_error(self, job_id: str, error_type: str):
        """Track a specific error type."""
        self.errors.append({
            "job_id": job_id,
            "timestamp": datetime.now().isoformat(),
            "type": error_type
        })
        # Update error category counters
        self.error_categories[error_type] = self.error_categories.get(error_type, 0) + 1

    def calculate_percentiles(self) -> Dict[str, float]:
        """Calculate P50/P95/P99 latency percentiles."""
        if len(self.latencies) == 0:
            return {"p50": 0, "p95": 0, "p99": 0}
        
        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)
        
        return {
            "p50": sorted_latencies[int(n * 0.50)] if n > 0 else 0,
            "p95": sorted_latencies[int(n * 0.95)] if n > 0 else 0,
            "p99": sorted_latencies[int(n * 0.99)] if n > 0 else 0,
            "min": min(sorted_latencies) if sorted_latencies else 0,
            "max": max(sorted_latencies) if sorted_latencies else 0,
            "mean": statistics.mean(sorted_latencies) if sorted_latencies else 0
        }

    def get_success_rate(self) -> Dict[str, Any]:
        """Calculate job success rate."""
        if not self.jobs:
            return {"success_rate": 0, "total": 0, "successful": 0, "failed": 0}
        
        successful = sum(1 for j in self.jobs.values() if j.get("status") == "success")
        failed = sum(1 for j in self.jobs.values() if j.get("status") == "failed")
        total = len(self.jobs)
        
        return {
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "total": total,
            "successful": successful,
            "failed": failed
        }

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system resource usage metrics."""
        try:
            # Memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            
            # CPU usage (percentage over 0.1 seconds)
            cpu_percent = self.process.cpu_percent(interval=0.1)
            
            # Uptime
            uptime_seconds = time.time() - self.start_time
            uptime_hours = uptime_seconds / 3600
            
            # Thread count
            num_threads = self.process.num_threads()
            
            return {
                "memory_mb": round(memory_mb, 2),
                "cpu_percent": round(cpu_percent, 2),
                "uptime_seconds": round(uptime_seconds, 2),
                "uptime_hours": round(uptime_hours, 2),
                "active_requests": self.active_requests,
                "num_threads": num_threads,
                "process_id": os.getpid()
            }
        except Exception as e:
            # Return minimal metrics if psutil fails
            return {
                "memory_mb": 0,
                "cpu_percent": 0,
                "uptime_seconds": round(time.time() - self.start_time, 2),
                "uptime_hours": round((time.time() - self.start_time) / 3600, 2),
                "active_requests": self.active_requests,
                "num_threads": 0,
                "process_id": os.getpid(),
                "error": str(e)
            }

    def detect_anomalies(self) -> List[str]:
        """
        Detect anomalies in processing patterns.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        # Check for high error rate (>10% failure)
        success_stats = self.get_success_rate()
        if success_stats["total"] >= 5 and success_stats["failed"] > 0:
            failure_rate = (success_stats["failed"] / success_stats["total"]) * 100
            if failure_rate > 10:
                warnings.append(f"High failure rate: {success_stats['failed']} of {success_stats['total']} jobs failed ({failure_rate:.1f}%)")
        
        # Check for spikes in hourly changes
        if len(self.hourly_stats) >= 1:
            hours = sorted(self.hourly_stats.keys())
            
            # Calculate baseline from all hours
            all_totals = []
            for hour in hours:
                stats = self.hourly_stats[hour]
                total_changes = stats["added"] + stats["removed"] + stats["moved"]
                all_totals.append(total_changes)
            
            if len(all_totals) >= 2:
                # Calculate median excluding the most recent (potential spike)
                baseline_totals = all_totals[:-1] if len(all_totals) > 2 else all_totals
                median_changes = statistics.median(baseline_totals) if baseline_totals else 0
                
                # Check most recent hour for spike
                recent_total = all_totals[-1]
                
                # Alert if >10x median (or >40 if median is very low)
                threshold = max(median_changes * 10, 40) if median_changes > 0 else 40
                if recent_total > threshold:
                    warnings.append(f"10x spike in changes detected: {recent_total} changes vs median {median_changes:.0f}")
        
        # Check for missing/corrupted data
        error_types = {}
        for error in self.errors:
            error_type = error.get("type", "unknown")
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if "missing_data" in error_types:
            count = error_types["missing_data"]
            total = success_stats["total"]
            if total > 0:
                percentage = (count / total) * 100
                if percentage > 5:
                    warnings.append(f"High rate of missing data: {count} jobs ({percentage:.1f}%)")
        
        # Check for delayed processing
        now = datetime.now()
        recent_jobs = [
            j for j in self.jobs.values()
            if "end_time" in j and (now - j["end_time"]).total_seconds() < 3600
        ]
        
        if len(recent_jobs) == 0 and len(self.jobs) > 0:
            # No jobs in last hour but we have historical jobs
            last_job_times = [j.get("end_time") for j in self.jobs.values() if "end_time" in j]
            if last_job_times:
                last_time = max(last_job_times)
                gap_hours = (now - last_time).total_seconds() / 3600
                if gap_hours > 1:
                    warnings.append(f"No job completions in last {gap_hours:.1f} hours")
        
        return warnings

    def record_changes(self, added: int, removed: int, moved: int):
        """Record change statistics for the current hour."""
        hour_key = datetime.now().strftime("%Y-%m-%d %H:00")
        if hour_key not in self.hourly_stats:
            self.hourly_stats[hour_key] = {
                "added": 0,
                "removed": 0,
                "moved": 0
            }
        
        self.hourly_stats[hour_key]["added"] += added
        self.hourly_stats[hour_key]["removed"] += removed
        self.hourly_stats[hour_key]["moved"] += moved

    def get_change_statistics(self) -> Dict[str, Any]:
        """Get detailed breakdown of all changes tracked."""
        total_added = 0
        total_removed = 0
        total_moved = 0
        
        for stats in self.hourly_stats.values():
            total_added += stats.get("added", 0)
            total_removed += stats.get("removed", 0)
            total_moved += stats.get("moved", 0)
        
        total_changes = total_added + total_removed + total_moved
        
        # Calculate percentages
        added_pct = (total_added / total_changes * 100) if total_changes > 0 else 0
        removed_pct = (total_removed / total_changes * 100) if total_changes > 0 else 0
        moved_pct = (total_moved / total_changes * 100) if total_changes > 0 else 0
        
        # Calculate average changes per job
        success_count = sum(1 for j in self.jobs.values() if j.get("status") == "success")
        avg_changes_per_job = total_changes / success_count if success_count > 0 else 0
        
        return {
            "total_changes": total_changes,
            "total_added": total_added,
            "total_removed": total_removed,
            "total_moved": total_moved,
            "added_percentage": round(added_pct, 1),
            "removed_percentage": round(removed_pct, 1),
            "moved_percentage": round(moved_pct, 1),
            "average_changes_per_job": round(avg_changes_per_job, 2)
        }

    def snapshot(self) -> Dict[str, Any]:
        """Return a comprehensive snapshot of all metrics."""
        percentiles = self.calculate_percentiles()
        success_stats = self.get_success_rate()
        anomalies = self.detect_anomalies()
        system_metrics = self.get_system_metrics()
        change_stats = self.get_change_statistics()
        
        # Count errors by type (use stored categories for efficiency)
        error_counts = self.error_categories.copy()
        
        return {
            "total_jobs": len(self.jobs),
            "success_rate": success_stats["success_rate"] / 100,  # Return as decimal for tests
            "latency_p50": percentiles["p50"],
            "latency_p95": percentiles["p95"],
            "latency_p99": percentiles["p99"],
            "latency_mean": percentiles.get("mean", 0),
            "latency_min": percentiles.get("min", 0),
            "latency_max": percentiles.get("max", 0),
            "hourly_stats": self.hourly_stats,
            "error_count": len(self.errors),
            "errors": error_counts,
            "error_categories": error_counts,  # Alias for clarity
            "jobs": {
                job_id: {
                    "status": job.get("status"),
                    "start_time": job.get("start_time_iso"),
                    "end_time": job.get("end_time_iso"),
                    "latency_seconds": job.get("latency_seconds")
                }
                for job_id, job in self.jobs.items()
            },
            "anomalies": anomalies,
            "recent_errors": self.errors[-10:] if self.errors else [],
            "system": system_metrics,
            "change_statistics": change_stats
        }


# Global metrics instance
METRICS = Metrics()
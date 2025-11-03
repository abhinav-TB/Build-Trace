"""
Unit tests for the metrics module.
"""
import pytest
from datetime import datetime, timedelta
from app.metrics import Metrics


class TestMetrics:
    """Test the Metrics class."""
    
    def test_initialization(self):
        """Test metrics initialization."""
        metrics = Metrics()
        
        snapshot = metrics.snapshot()
        assert snapshot["total_jobs"] == 0
        assert len(snapshot["jobs"]) == 0
        assert snapshot["success_rate"] == 0.0
        assert snapshot["latency_p50"] == 0
        assert snapshot["latency_p95"] == 0
        assert snapshot["latency_p99"] == 0
    
    def test_mark_start(self):
        """Test marking job start."""
        metrics = Metrics()
        
        metrics.mark_start("job-001")
        
        snapshot = metrics.snapshot()
        assert snapshot["total_jobs"] == 1
        assert "job-001" in snapshot["jobs"]
        assert snapshot["jobs"]["job-001"]["status"] == "running"
        assert "start_time" in snapshot["jobs"]["job-001"]
    
    def test_mark_end_success(self):
        """Test marking successful job completion."""
        metrics = Metrics()
        
        metrics.mark_start("job-001")
        metrics.mark_end("job-001", ok=True)
        
        snapshot = metrics.snapshot()
        assert snapshot["jobs"]["job-001"]["status"] == "success"
        assert "end_time" in snapshot["jobs"]["job-001"]
        assert snapshot["success_rate"] == 1.0
    
    def test_mark_end_failure(self):
        """Test marking failed job completion."""
        metrics = Metrics()
        
        metrics.mark_start("job-002")
        metrics.mark_end("job-002", ok=False)
        
        snapshot = metrics.snapshot()
        assert snapshot["jobs"]["job-002"]["status"] == "failed"
        assert snapshot["success_rate"] == 0.0
    
    def test_mark_end_without_start(self):
        """Test marking end for job that wasn't started (orphaned result)."""
        metrics = Metrics()
        
        metrics.mark_end("orphan-job", ok=True)
        
        snapshot = metrics.snapshot()
        assert "orphan-job" in snapshot["jobs"]
        assert snapshot["jobs"]["orphan-job"]["status"] == "success"
    
    def test_success_rate_calculation(self):
        """Test success rate calculation with mixed results."""
        metrics = Metrics()
        
        # 3 successful jobs
        for i in range(3):
            metrics.mark_start(f"success-{i}")
            metrics.mark_end(f"success-{i}", ok=True)
        
        # 2 failed jobs
        for i in range(2):
            metrics.mark_start(f"fail-{i}")
            metrics.mark_end(f"fail-{i}", ok=False)
        
        snapshot = metrics.snapshot()
        assert snapshot["total_jobs"] == 5
        assert snapshot["success_rate"] == 0.6  # 3/5 = 60%
    
    def test_latency_percentiles_single_job(self):
        """Test latency percentile calculation with one job."""
        metrics = Metrics()
        
        metrics.mark_start("job-001")
        # Simulate some processing time
        import time
        time.sleep(0.1)
        metrics.mark_end("job-001", ok=True)
        
        snapshot = metrics.snapshot()
        
        # Should have calculated latencies
        assert snapshot["latency_p50"] > 0
        assert snapshot["latency_p95"] > 0
        assert snapshot["latency_p99"] > 0
        # All percentiles should be the same for a single job
        assert snapshot["latency_p50"] == snapshot["latency_p95"] == snapshot["latency_p99"]
    
    def test_latency_percentiles_multiple_jobs(self):
        """Test latency percentile calculation with multiple jobs."""
        metrics = Metrics()
        
        # Manually add jobs with known latencies
        import time
        
        for i in range(10):
            job_id = f"job-{i:03d}"
            metrics.mark_start(job_id)
            time.sleep(0.01 * (i + 1))  # Variable processing time
            metrics.mark_end(job_id, ok=True)
        
        snapshot = metrics.snapshot()
        
        # P50 should be less than P95 which should be less than P99
        assert snapshot["latency_p50"] <= snapshot["latency_p95"]
        assert snapshot["latency_p95"] <= snapshot["latency_p99"]
        assert snapshot["latency_p50"] > 0
    
    def test_error_tracking(self):
        """Test error type tracking."""
        metrics = Metrics()
        
        metrics.mark_error("job-001", "missing_data")
        metrics.mark_error("job-002", "invalid_json")
        metrics.mark_error("job-003", "missing_data")
        
        snapshot = metrics.snapshot()
        
        assert snapshot["error_count"] == 3
        assert snapshot["errors"]["missing_data"] == 2
        assert snapshot["errors"]["invalid_json"] == 1
    
    def test_hourly_stats(self):
        """Test hourly statistics tracking."""
        metrics = Metrics()
        
        # Record some changes
        metrics.record_changes(5, 3, 2)  # added, removed, moved
        metrics.record_changes(2, 1, 4)
        
        snapshot = metrics.snapshot()
        
        current_hour = datetime.now().strftime("%Y-%m-%d %H:00")
        assert current_hour in snapshot["hourly_stats"]
        
        hour_stats = snapshot["hourly_stats"][current_hour]
        assert hour_stats["added"] == 7
        assert hour_stats["removed"] == 4
        assert hour_stats["moved"] == 6
    
    def test_snapshot_completeness(self):
        """Test that snapshot contains all required fields."""
        metrics = Metrics()
        
        metrics.mark_start("job-001")
        metrics.mark_end("job-001", ok=True)
        metrics.record_changes(5, 2, 3)
        
        snapshot = metrics.snapshot()
        
        # Check all required fields are present
        required_fields = [
            "total_jobs",
            "success_rate",
            "error_count",
            "latency_p50",
            "latency_p95",
            "latency_p99",
            "hourly_stats",
            "errors",
            "jobs"
        ]
        
        for field in required_fields:
            assert field in snapshot, f"Missing required field: {field}"


class TestMetricsEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_metrics(self):
        """Test snapshot with no data."""
        metrics = Metrics()
        snapshot = metrics.snapshot()
        
        assert snapshot["total_jobs"] == 0
        assert snapshot["success_rate"] == 0.0
        assert snapshot["error_count"] == 0
        assert snapshot["latency_p50"] == 0
    
    def test_only_running_jobs(self):
        """Test with jobs that never completed."""
        metrics = Metrics()
        
        metrics.mark_start("job-001")
        metrics.mark_start("job-002")
        
        snapshot = metrics.snapshot()
        
        assert snapshot["total_jobs"] == 2
        # Success rate should handle running jobs
        assert snapshot["success_rate"] >= 0.0
    
    def test_duplicate_job_id(self):
        """Test handling of duplicate job IDs."""
        metrics = Metrics()
        
        metrics.mark_start("job-001")
        metrics.mark_start("job-001")  # Duplicate start
        metrics.mark_end("job-001", ok=True)
        
        snapshot = metrics.snapshot()
        
        # Should handle gracefully
        assert "job-001" in snapshot["jobs"]
    
    def test_zero_latency_jobs(self):
        """Test jobs that complete instantly."""
        metrics = Metrics()
        
        metrics.mark_start("instant-job")
        metrics.mark_end("instant-job", ok=True)
        
        snapshot = metrics.snapshot()
        
        # Should handle zero or near-zero latencies
        assert snapshot["latency_p50"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Unit tests for the diff module.
"""
import pytest
from app.diff import diff, generate_summary_simple, get_direction


class TestDiffFunction:
    """Test the main diff function."""
    
    def test_no_changes(self):
        """Test when versions are identical."""
        version_a = [
            {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1}
        ]
        version_b = [
            {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1}
        ]
        
        result = diff(version_a, version_b)
        
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0
        assert len(result["moved"]) == 0
        assert result["summary"] == "No changes detected."
        assert result["stats"]["total_changes"] == 0
    
    def test_empty_versions(self):
        """Test with empty input."""
        result = diff([], [])
        
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0
        assert len(result["moved"]) == 0
        assert result["summary"] == "No changes detected."
    
    def test_added_objects(self):
        """Test detection of added objects."""
        version_a = [
            {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1}
        ]
        version_b = [
            {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1},
            {"id": "D1", "type": "door", "x": 4, "y": 2, "width": 1, "height": 2},
            {"id": "W1", "type": "window", "x": 3, "y": 1, "width": 2, "height": 1}
        ]
        
        result = diff(version_a, version_b)
        
        assert len(result["added"]) == 2
        assert len(result["removed"]) == 0
        assert len(result["moved"]) == 0
        assert result["stats"]["added_count"] == 2
        
        # Check that the right objects were detected
        added_ids = {obj["id"] for obj in result["added"]}
        assert added_ids == {"D1", "W1"}
    
    def test_removed_objects(self):
        """Test detection of removed objects."""
        version_a = [
            {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1},
            {"id": "D1", "type": "door", "x": 4, "y": 2, "width": 1, "height": 2}
        ]
        version_b = [
            {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1}
        ]
        
        result = diff(version_a, version_b)
        
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 1
        assert len(result["moved"]) == 0
        assert result["removed"][0]["id"] == "D1"
    
    def test_moved_objects(self):
        """Test detection of moved objects."""
        version_a = [
            {"id": "D1", "type": "door", "x": 4, "y": 2, "width": 1, "height": 2}
        ]
        version_b = [
            {"id": "D1", "type": "door", "x": 6, "y": 2, "width": 1, "height": 2}
        ]
        
        result = diff(version_a, version_b)
        
        assert len(result["added"]) == 0
        assert len(result["removed"]) == 0
        assert len(result["moved"]) == 1
        
        moved = result["moved"][0]
        assert moved["id"] == "D1"
        assert moved["delta"]["x"] == 2
        assert moved["delta"]["y"] == 0
        assert moved["from"]["x"] == 4
        assert moved["to"]["x"] == 6
    
    def test_mixed_changes(self):
        """Test combination of added, removed, and moved objects."""
        version_a = [
            {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1},
            {"id": "D1", "type": "door", "x": 4, "y": 2, "width": 1, "height": 2},
            {"id": "OLD", "type": "window", "x": 1, "y": 1, "width": 2, "height": 1}
        ]
        version_b = [
            {"id": "A1", "type": "wall", "x": 10, "y": 5, "width": 8, "height": 1},
            {"id": "D1", "type": "door", "x": 6, "y": 2, "width": 1, "height": 2},
            {"id": "W1", "type": "window", "x": 3, "y": 1, "width": 2, "height": 1}
        ]
        
        result = diff(version_a, version_b)
        
        assert len(result["added"]) == 1
        assert len(result["removed"]) == 1
        assert len(result["moved"]) == 1
        assert result["stats"]["total_changes"] == 3
        
        assert result["added"][0]["id"] == "W1"
        assert result["removed"][0]["id"] == "OLD"
        assert result["moved"][0]["id"] == "D1"
    
    def test_object_without_id(self):
        """Test handling of objects without IDs."""
        version_a = [
            {"type": "wall", "x": 10, "y": 5, "width": 8, "height": 1}
        ]
        version_b = [
            {"id": "D1", "type": "door", "x": 4, "y": 2, "width": 1, "height": 2}
        ]
        
        # Should not crash, objects without IDs are skipped
        result = diff(version_a, version_b)
        
        assert len(result["added"]) == 1
        assert result["added"][0]["id"] == "D1"


class TestGetDirection:
    """Test the direction calculation helper."""
    
    def test_east(self):
        assert get_direction(5, 0) == "east"
    
    def test_west(self):
        assert get_direction(-5, 0) == "west"
    
    def test_north(self):
        assert get_direction(0, 5) == "north"
    
    def test_south(self):
        assert get_direction(0, -5) == "south"
    
    def test_northeast(self):
        assert get_direction(3, 4) == "northeast"
    
    def test_northwest(self):
        assert get_direction(-3, 4) == "northwest"
    
    def test_southeast(self):
        assert get_direction(3, -4) == "southeast"
    
    def test_southwest(self):
        assert get_direction(-3, -4) == "southwest"
    
    def test_no_movement(self):
        assert get_direction(0, 0) == "in place"


class TestGenerateSummarySimple:
    """Test the simple summary generation (without LLM)."""
    
    def test_no_changes(self):
        summary = generate_summary_simple([], [], [])
        assert summary == "No changes detected."
    
    def test_single_added(self):
        added = [{"id": "W1", "type": "window", "x": 3, "y": 1}]
        summary = generate_summary_simple(added, [], [])
        assert "Window W1 added at (3,1)" in summary
    
    def test_multiple_added_same_type(self):
        added = [
            {"id": "W1", "type": "window", "x": 3, "y": 1},
            {"id": "W2", "type": "window", "x": 5, "y": 1}
        ]
        summary = generate_summary_simple(added, [], [])
        assert "2 windows added" in summary
    
    def test_multiple_added_mixed_types(self):
        added = [
            {"id": "W1", "type": "window", "x": 3, "y": 1},
            {"id": "D1", "type": "door", "x": 5, "y": 2}
        ]
        summary = generate_summary_simple(added, [], [])
        assert "window" in summary or "door" in summary
        assert "added" in summary
    
    def test_single_removed(self):
        removed = [{"id": "D1", "type": "door"}]
        summary = generate_summary_simple([], removed, [])
        assert "Door D1 removed" in summary
    
    def test_multiple_removed(self):
        removed = [
            {"id": "D1", "type": "door"},
            {"id": "D2", "type": "door"}
        ]
        summary = generate_summary_simple([], removed, [])
        assert "2 doors removed" in summary
    
    def test_single_moved(self):
        moved = [{
            "id": "D1",
            "type": "door",
            "delta": {"x": 2, "y": 0}
        }]
        summary = generate_summary_simple([], [], moved)
        assert "Door D1 moved" in summary
        assert "east" in summary
    
    def test_multiple_moved(self):
        moved = [
            {"id": "D1", "type": "door", "delta": {"x": 2, "y": 0}},
            {"id": "W1", "type": "window", "delta": {"x": 0, "y": 3}}
        ]
        summary = generate_summary_simple([], [], moved)
        assert "2 objects repositioned" in summary
    
    def test_complex_summary(self):
        added = [{"id": "W1", "type": "window", "x": 3, "y": 1}]
        removed = [{"id": "D1", "type": "door"}]
        moved = [{"id": "W2", "type": "window", "delta": {"x": 1, "y": 2}}]
        
        summary = generate_summary_simple(added, removed, moved)
        
        assert "added" in summary
        assert "removed" in summary
        assert "moved" in summary or "repositioned" in summary


class TestDiffIntegration:
    """Integration tests for realistic scenarios."""
    
    def test_realistic_floor_plan_update(self):
        """Test a realistic floor plan modification scenario."""
        version_a = [
            {"id": "W1", "type": "wall", "x": 0, "y": 0, "width": 20, "height": 1},
            {"id": "W2", "type": "wall", "x": 0, "y": 10, "width": 20, "height": 1},
            {"id": "D1", "type": "door", "x": 10, "y": 0, "width": 1, "height": 2},
        ]
        
        version_b = [
            {"id": "W1", "type": "wall", "x": 0, "y": 0, "width": 20, "height": 1},
            {"id": "W2", "type": "wall", "x": 0, "y": 10, "width": 20, "height": 1},
            {"id": "D1", "type": "door", "x": 12, "y": 0, "width": 1, "height": 2},
            {"id": "WIN1", "type": "window", "x": 5, "y": 0, "width": 2, "height": 1},
        ]
        
        result = diff(version_a, version_b)
        
        assert result["stats"]["added_count"] == 1
        assert result["stats"]["moved_count"] == 1
        assert result["stats"]["removed_count"] == 0
        assert result["summary"] != "No changes detected."
    
    def test_large_scale_changes(self):
        """Test with many changes to verify performance."""
        version_a = [
            {"id": f"OBJ{i}", "type": "wall", "x": i, "y": i, "width": 1, "height": 1}
            for i in range(50)
        ]
        
        version_b = [
            {"id": f"OBJ{i}", "type": "wall", "x": i+1, "y": i, "width": 1, "height": 1}
            for i in range(50)
        ]
        
        result = diff(version_a, version_b)
        
        assert result["stats"]["moved_count"] == 50
        assert result["stats"]["added_count"] == 0
        assert result["stats"]["removed_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

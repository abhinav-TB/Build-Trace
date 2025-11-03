"""
BuildTrace Data Simulator

Generates realistic drawing version pairs for testing the BuildTrace system.
"""

import random
from typing import List, Dict, Any, Tuple


OBJECT_TYPES = ["wall", "door", "window", "column", "beam"]


def generate_object(obj_id: str, obj_type: str = None) -> Dict[str, Any]:
    """Generate a single geometric object with random properties."""
    if obj_type is None:
        obj_type = random.choice(OBJECT_TYPES)
    
    # Generate size based on type
    if obj_type == "wall":
        width = random.randint(5, 20)
        height = random.randint(1, 2)
    elif obj_type in ["door", "window"]:
        width = random.randint(1, 3)
        height = random.randint(1, 3)
    elif obj_type == "column":
        width = random.randint(1, 2)
        height = random.randint(1, 2)
    else:  # beam
        width = random.randint(3, 15)
        height = random.randint(1, 2)
    
    return {
        "id": obj_id,
        "type": obj_type,
        "x": random.randint(0, 50),
        "y": random.randint(0, 50),
        "width": width,
        "height": height
    }


def generate_base_drawing(num_objects: int = 20) -> List[Dict[str, Any]]:
    """Generate a base drawing with random objects."""
    objects = []
    for i in range(num_objects):
        obj_id = f"{random.choice(['A', 'B', 'C', 'D', 'W'])}{i+1}"
        objects.append(generate_object(obj_id))
    return objects


def apply_changes(base: List[Dict[str, Any]], profile: str) -> List[Dict[str, Any]]:
    """
    Apply changes to a base drawing based on the change profile.
    
    Profiles:
    - "none": No changes
    - "small": 1-3 objects changed
    - "medium": 5-10 objects changed
    - "large": 15-25 objects changed
    - "spike": 50+ objects changed (for anomaly testing)
    """
    result = [obj.copy() for obj in base]
    
    if profile == "none":
        return result
    
    # Determine number of changes
    if profile == "small":
        num_add = random.randint(0, 2)
        num_remove = random.randint(0, 2)
        num_move = random.randint(0, 2)
    elif profile == "medium":
        num_add = random.randint(2, 5)
        num_remove = random.randint(2, 5)
        num_move = random.randint(2, 5)
    elif profile == "large":
        num_add = random.randint(5, 12)
        num_remove = random.randint(5, 12)
        num_move = random.randint(3, 8)
    elif profile == "spike":
        num_add = random.randint(30, 50)
        num_remove = random.randint(10, 20)
        num_move = random.randint(10, 20)
    else:
        raise ValueError(f"Unknown profile: {profile}")
    
    # Remove objects
    for _ in range(min(num_remove, len(result))):
        if result:
            result.pop(random.randint(0, len(result) - 1))
    
    # Move objects
    for _ in range(min(num_move, len(result))):
        if result:
            idx = random.randint(0, len(result) - 1)
            obj = result[idx]
            obj["x"] += random.randint(-5, 5)
            obj["y"] += random.randint(-5, 5)
    
    # Add new objects
    existing_ids = {obj["id"] for obj in result}
    for i in range(num_add):
        # Generate unique ID
        new_id = f"NEW{i+1}"
        counter = 1
        while new_id in existing_ids:
            new_id = f"NEW{i+1}_{counter}"
            counter += 1
        
        result.append(generate_object(new_id))
        existing_ids.add(new_id)
    
    return result


def generate_pair(drawing_id: str, profile: str = "medium", base_size: int = 20) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Generate a pair of drawing versions (A and B).
    
    Args:
        drawing_id: Identifier for the drawing pair
        profile: Change profile (none, small, medium, large, spike)
        base_size: Number of objects in base drawing
    
    Returns:
        Tuple of (version_a, version_b) as lists of objects
    """
    version_a = generate_base_drawing(base_size)
    version_b = apply_changes(version_a, profile)
    return version_a, version_b

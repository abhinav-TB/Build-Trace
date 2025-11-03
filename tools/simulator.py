#!/usr/bin/env python3
"""
BuildTrace Data Simulator

Generates realistic drawing version pairs for testing the BuildTrace system.
Can be used as a CLI tool or imported as a module.
"""

import json
import random
import argparse
import os
from typing import List, Dict, Any, Tuple
try:
    from google.cloud import storage
except ImportError:
    storage = None


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


def save_to_gcs(bucket_name: str, file_path: str, content: Any):
    """Upload JSON content to Google Cloud Storage."""
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    blob.upload_from_string(json.dumps(content, indent=2), content_type="application/json")
    print(f"✓ Uploaded: gs://{bucket_name}/{file_path}")


def save_to_local(file_path: str, content: Any):
    """Save JSON content to local file."""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w') as f:
        json.dump(content, f, indent=2)
    print(f"✓ Saved: {file_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate test drawing pairs for BuildTrace")
    parser.add_argument("--pairs", type=int, default=10, help="Number of drawing pairs to generate")
    parser.add_argument("--profile", choices=["none", "small", "medium", "large", "spike"], 
                        default="medium", help="Change profile for generated pairs")
    parser.add_argument("--output", type=str, help="Output location (gs://bucket/path or local directory)")
    parser.add_argument("--manifest", type=str, help="Generate manifest file at this path")
    parser.add_argument("--base-size", type=int, default=20, help="Number of objects in base drawing")
    parser.add_argument("--mixed-profiles", action="store_true", 
                        help="Use mixed profiles (random for each pair)")
    
    args = parser.parse_args()
    
    # Determine output mode
    is_gcs = args.output and args.output.startswith("gs://")
    
    if is_gcs:
        # Parse GCS bucket and prefix
        output_path = args.output.replace("gs://", "")
        bucket_name = output_path.split("/")[0]
        prefix = "/".join(output_path.split("/")[1:]) if "/" in output_path else ""
    else:
        output_dir = args.output or "generated_data"
        os.makedirs(output_dir, exist_ok=True)
    
    manifest_pairs = []
    profiles = ["none", "small", "medium", "large", "spike"] if args.mixed_profiles else [args.profile]
    
    print(f"\n🎨 Generating {args.pairs} drawing pairs...")
    print(f"   Profile: {args.profile if not args.mixed_profiles else 'mixed'}")
    print(f"   Base size: {args.base_size} objects")
    print(f"   Output: {args.output or 'local directory'}\n")
    
    for i in range(args.pairs):
        drawing_id = f"DRAWING-{i+1:04d}"
        
        # Select profile
        profile = random.choice(profiles) if args.mixed_profiles else args.profile
        
        # Generate pair
        version_a, version_b = generate_pair(drawing_id, profile, args.base_size)
        
        # Save files
        if is_gcs:
            file_a = f"{prefix}/inputs/{drawing_id}_vA.json" if prefix else f"inputs/{drawing_id}_vA.json"
            file_b = f"{prefix}/inputs/{drawing_id}_vB.json" if prefix else f"inputs/{drawing_id}_vB.json"
            
            save_to_gcs(bucket_name, file_a, version_a)
            save_to_gcs(bucket_name, file_b, version_b)
            
            manifest_pairs.append({
                "id": drawing_id,
                "a": f"gs://{bucket_name}/{file_a}",
                "b": f"gs://{bucket_name}/{file_b}"
            })
        else:
            file_a = os.path.join(output_dir, f"{drawing_id}_vA.json")
            file_b = os.path.join(output_dir, f"{drawing_id}_vB.json")
            
            save_to_local(file_a, version_a)
            save_to_local(file_b, version_b)
            
            manifest_pairs.append({
                "id": drawing_id,
                "a": file_a,
                "b": file_b
            })
    
    # Generate manifest
    manifest = {"pairs": manifest_pairs}
    
    if args.manifest:
        manifest_path = args.manifest
    else:
        manifest_path = "manifest.json" if not is_gcs else os.path.join(output_dir or ".", "manifest.json")
    
    if is_gcs and args.manifest and args.manifest.startswith("gs://"):
        # Save manifest to GCS
        manifest_gs = args.manifest.replace("gs://", "")
        manifest_bucket = manifest_gs.split("/")[0]
        manifest_path_gcs = "/".join(manifest_gs.split("/")[1:])
        save_to_gcs(manifest_bucket, manifest_path_gcs, manifest)
    else:
        save_to_local(manifest_path, manifest)
    
    print(f"\n✅ Successfully generated {args.pairs} drawing pairs!")
    print(f"   Manifest: {manifest_path}")
    print(f"\n📤 To submit jobs:")
    if is_gcs:
        print(f'   curl -X POST https://<service-url>/process -H "Content-Type: application/json" -d @{manifest_path}')
    else:
        print(f'   curl -X POST https://<service-url>/process -H "Content-Type: application/json" -d @{manifest_path}')


if __name__ == "__main__":
    main()

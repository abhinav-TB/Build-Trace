import os
from google import genai
from typing import List, Dict, Any

# Configure Gemini API
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
USE_GEMINI = os.environ.get("USE_GEMINI", "true").lower() == "true"

client = None
if GEMINI_API_KEY and USE_GEMINI:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None


def diff(a: List[Dict[str, Any]], b: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare two drawing versions and detect changes.
    
    Args:
        a: List of objects in version A
        b: List of objects in version B
    
    Returns:
        Dict containing added, removed, moved objects and a summary
    """
    # Create indices by object ID
    a_index = {obj["id"]: obj for obj in a if "id" in obj}
    b_index = {obj["id"]: obj for obj in b if "id" in obj}
    
    # Detect added objects (in B but not in A)
    added = []
    for obj_id, obj in b_index.items():
        if obj_id not in a_index:
            added.append(obj)
    
    # Detect removed objects (in A but not in B)
    removed = []
    for obj_id, obj in a_index.items():
        if obj_id not in b_index:
            removed.append(obj)
    
    # Detect moved objects (same ID, different position)
    moved = []
    for obj_id in a_index.keys():
        if obj_id in b_index:
            obj_a = a_index[obj_id]
            obj_b = b_index[obj_id]
            
            # Check if position changed
            x_changed = obj_a.get("x") != obj_b.get("x")
            y_changed = obj_a.get("y") != obj_b.get("y")
            
            if x_changed or y_changed:
                x_delta = obj_b.get("x", 0) - obj_a.get("x", 0)
                y_delta = obj_b.get("y", 0) - obj_a.get("y", 0)
                
                moved.append({
                    "id": obj_id,
                    "type": obj_b.get("type", "unknown"),
                    "from": {"x": obj_a.get("x"), "y": obj_a.get("y")},
                    "to": {"x": obj_b.get("x"), "y": obj_b.get("y")},
                    "delta": {"x": x_delta, "y": y_delta}
                })
    
    # Generate natural language summary
    summary = generate_summary(added, removed, moved)
    
    return {
        "added": added,
        "removed": removed,
        "moved": moved,
        "summary": summary,
        "stats": {
            "added_count": len(added),
            "removed_count": len(removed),
            "moved_count": len(moved),
            "total_changes": len(added) + len(removed) + len(moved)
        }
    }


def generate_summary(added: List[Dict], removed: List[Dict], moved: List[Dict]) -> str:
    """
    Generate a natural language summary of changes using Gemini LLM.
    Falls back to simple summary if Gemini is not available.
    
    Args:
        added: List of added objects
        removed: List of removed objects
        moved: List of moved objects
    
    Returns:
        Human-readable summary string
    """
    # Use Gemini if available
    if client:
        try:
            return generate_summary_with_gemini(added, removed, moved)
        except Exception as e:
            print(f"Gemini summary generation failed: {e}, falling back to simple summary")
            # Fall through to simple summary
    
    # Simple summary generation (fallback)
    return generate_summary_simple(added, removed, moved)


def generate_summary_simple(added: List[Dict], removed: List[Dict], moved: List[Dict]) -> str:
    """
    Generate a simple natural language summary without LLM.
    
    Args:
        added: List of added objects
        removed: List of removed objects
        moved: List of moved objects
    
    Returns:
        Human-readable summary string
    """
    if not added and not removed and not moved:
        return "No changes detected."
    
    parts = []
    
    # Describe removed objects
    if removed:
        if len(removed) == 1:
            obj = removed[0]
            parts.append(f"{obj.get('type', 'Object').capitalize()} {obj['id']} removed")
        else:
            # Group by type
            by_type = {}
            for obj in removed:
                obj_type = obj.get('type', 'object')
                by_type[obj_type] = by_type.get(obj_type, 0) + 1
            
            type_strs = [f"{count} {obj_type}{'s' if count > 1 else ''}" for obj_type, count in by_type.items()]
            parts.append(f"{', '.join(type_strs)} removed")
    
    # Describe added objects
    if added:
        if len(added) == 1:
            obj = added[0]
            parts.append(f"{obj.get('type', 'Object').capitalize()} {obj['id']} added at ({obj.get('x')},{obj.get('y')})")
        else:
            # Group by type
            by_type = {}
            for obj in added:
                obj_type = obj.get('type', 'object')
                by_type[obj_type] = by_type.get(obj_type, 0) + 1
            
            type_strs = [f"{count} {obj_type}{'s' if count > 1 else ''}" for obj_type, count in by_type.items()]
            parts.append(f"{', '.join(type_strs)} added")
    
    # Describe moved objects
    if moved:
        if len(moved) == 1:
            obj = moved[0]
            direction = get_direction(obj['delta']['x'], obj['delta']['y'])
            distance = abs(obj['delta']['x']) + abs(obj['delta']['y'])
            parts.append(f"{obj.get('type', 'Object').capitalize()} {obj['id']} moved {distance} units {direction}")
        else:
            parts.append(f"{len(moved)} objects repositioned")
    
    summary = "; ".join(parts) + "."
    return summary


def get_direction(x_delta: float, y_delta: float) -> str:
    """
    Convert x/y deltas to cardinal direction.
    
    Args:
        x_delta: Change in x coordinate
        y_delta: Change in y coordinate
    
    Returns:
        Direction string (e.g., "east", "north", "northeast")
    """
    if x_delta == 0 and y_delta == 0:
        return "in place"
    
    # Determine primary direction
    directions = []
    
    if abs(y_delta) > 0:
        directions.append("north" if y_delta > 0 else "south")
    
    if abs(x_delta) > 0:
        directions.append("east" if x_delta > 0 else "west")
    
    return "".join(directions) if len(directions) > 1 else (directions[0] if directions else "in place")


def generate_summary_with_gemini(added: List[Dict], removed: List[Dict], moved: List[Dict]) -> str:
    """
    Generate an intelligent natural language summary using Gemini LLM.
    
    Args:
        added: List of added objects
        removed: List of removed objects
        moved: List of moved objects
    
    Returns:
        AI-generated human-readable summary
    """
    if not added and not removed and not moved:
        return "No changes detected."
    
    # Prepare structured change data for the LLM
    change_summary = {
        "added_count": len(added),
        "removed_count": len(removed),
        "moved_count": len(moved)
    }
    
    # Add details for small change sets
    details = []
    
    if len(added) <= 5:
        for obj in added:
            details.append(f"Added {obj.get('type', 'object')} {obj['id']} at position ({obj.get('x')},{obj.get('y')})")
    elif added:
        by_type = {}
        for obj in added:
            obj_type = obj.get('type', 'object')
            by_type[obj_type] = by_type.get(obj_type, 0) + 1
        details.append(f"Added {', '.join([f'{count} {t}' for t, count in by_type.items()])}")
    
    if len(removed) <= 5:
        for obj in removed:
            details.append(f"Removed {obj.get('type', 'object')} {obj['id']}")
    elif removed:
        by_type = {}
        for obj in removed:
            obj_type = obj.get('type', 'object')
            by_type[obj_type] = by_type.get(obj_type, 0) + 1
        details.append(f"Removed {', '.join([f'{count} {t}' for t, count in by_type.items()])}")
    
    if len(moved) <= 5:
        for obj in moved:
            direction = get_direction(obj['delta']['x'], obj['delta']['y'])
            distance = abs(obj['delta']['x']) + abs(obj['delta']['y'])
            details.append(f"Moved {obj.get('type', 'object')} {obj['id']} {distance:.1f} units {direction}")
    elif moved:
        details.append(f"Repositioned {len(moved)} objects")
    
    prompt = f"""You are analyzing changes in a construction drawing between version A and version B.
Generate a concise, professional summary in 1-2 sentences.

Changes:
- {change_summary['added_count']} objects added
- {change_summary['removed_count']} objects removed  
- {change_summary['moved_count']} objects moved

Details:
{chr(10).join(details)}

Write a natural, professional summary suitable for architects and construction managers.
Be specific with object IDs when there are few changes. Use aggregate counts for many changes.
Mention spatial relationships when relevant (e.g., "near Door D1", "in the northwest corner").

Summary:"""
    
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )
        summary = response.text.strip()
        
        # Return the summary if we got a valid response
        if summary:
            return summary
        else:
            # Fallback if response is empty
            return generate_summary_simple(added, removed, moved)
    
    except Exception as e:
        print(f"Gemini API error: {e}")
        return generate_summary_simple(added, removed, moved)

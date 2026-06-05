"""
Cursor encoding/decoding for pagination
"""
import base64
import json
from typing import Optional, Tuple, Any
from bson import ObjectId
from datetime import datetime


def encode_cursor(sort_value: Any, updated_at: datetime, doc_id: ObjectId) -> str:
    """
    Encode cursor for pagination following compound cursor pattern.

    Args:
        sort_value: The value of the sort field (search score, price, etc.)
        updated_at: The updatedAt timestamp of the document
        doc_id: The MongoDB ObjectId of the document

    Returns:
        Base64-encoded cursor string
    """
    cursor_data = {
        "sort_value": sort_value,
        "updated_at": updated_at.isoformat() if updated_at else None,
        "_id": str(doc_id)
    }

    json_str = json.dumps(cursor_data, default=str)
    encoded = base64.b64encode(json_str.encode()).decode()

    return encoded


def decode_cursor(cursor: str) -> Tuple[Optional[Any], Optional[datetime], Optional[ObjectId]]:
    """
    Decode pagination cursor.

    Args:
        cursor: Base64-encoded cursor string

    Returns:
        Tuple of (sort_value, updated_at, doc_id) or (None, None, None) on error
    """
    try:
        decoded = base64.b64decode(cursor.encode()).decode()
        data = json.loads(decoded)

        sort_value = data.get("sort_value")

        updated_at = None
        if data.get("updated_at"):
            updated_at = datetime.fromisoformat(data["updated_at"])

        doc_id = None
        if data.get("_id"):
            doc_id = ObjectId(data["_id"])

        return sort_value, updated_at, doc_id

    except (json.JSONDecodeError, ValueError, KeyError) as e:
        # Invalid cursor - return None values
        print(f"Cursor decode error: {e}")
        return None, None, None

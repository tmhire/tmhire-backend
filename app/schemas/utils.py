import json
from datetime import date, datetime
from typing import Any, Dict, List
from bson import ObjectId
import inspect
import re

# Regular expression to match ISO date/time strings
ISO_DATE_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2}(\.\d+)?)?([+-]\d{2}:\d{2}|Z)?)?$')

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles date, datetime, and ObjectId objects."""
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        if isinstance(obj, ObjectId):
            return str(obj)
        # Handle PyObjectId (wrapper around ObjectId)
        if hasattr(obj, '__str__') and str(type(obj)).find('PyObjectId') > -1:
            return str(obj)
        # Handle Pydantic models by checking for model_dump method
        if hasattr(obj, 'model_dump'):
            return obj.model_dump()
        # For older Pydantic (v1), check for dict method
        if hasattr(obj, 'dict') and inspect.ismethod(obj.dict):
            return obj.dict()
        return super().default(obj)

def _process_dict(data: Dict) -> Dict:
    """Process a dictionary to handle problematic objects"""
    result = {}
    for key, value in data.items():
        result[key] = _process_value(value)
    return result

def _process_list(data: List) -> List:
    """Process a list to handle problematic objects"""
    return [_process_value(item) for item in data]

def _process_value(value: Any) -> Any:
    """Process a value to handle problematic objects"""
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        # For string values that look like ISO dates, keep them as is
        return value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    if hasattr(value, '__str__') and str(type(value)).find('PyObjectId') > -1:
        return str(value)
    if isinstance(value, dict):
        return _process_dict(value)
    if isinstance(value, list):
        return _process_list(value)
    if hasattr(value, 'model_dump'):
        return _process_dict(value.model_dump())
    if hasattr(value, 'dict') and inspect.ismethod(value.dict):
        return _process_dict(value.dict())
    # Try string representation as last resort
    try:
        return str(value)
    except:
        return None

def safe_serialize(data: Any) -> Any:
    """
    Safely serialize data that may contain date/datetime/ObjectId objects or Pydantic models.
    
    Args:
        data: Any data structure that may contain problematic objects
        
    Returns:
        A copy of the data with all problematic objects converted to strings or dicts
    """
    if data is None:
        return None
        
    try:
        # Pre-process the data to convert problematic objects
        processed_data = _process_value(data)
        
        # Final serialization as JSON then back to Python
        try:
            return json.loads(json.dumps(processed_data, cls=DateTimeEncoder))
        except:
            # If that fails, return the processed data directly
            return processed_data
    except Exception as e:
        # If serialization fails, log the error and return a safe default
        import logging
        logging.error(f"Serialization error: {str(e)}")
        
        # If it's a single object, try to extract basic info
        if not isinstance(data, (list, dict)):
            try:
                return str(data)
            except:
                return "Serialization failed"
                
        # For collections, return empty version of same type
        return [] if isinstance(data, list) else {} 
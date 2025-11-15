import json
from typing import Any, Union

def _toJson(obj) -> str:
    """
    Convert object/array to JSON string.
    Similar to JavaScript's JSON.stringify()
    """
    try:
        return json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise ValueError(f"toJson(): Cannot serialize object to JSON: {e}")

def _fromJson(json_str: str) -> Union[dict, list, Any]:
    """
    Parse JSON string into object/array.
    Similar to JavaScript's JSON.parse()
    """
    if not isinstance(json_str, str):
        raise TypeError(f"fromJson(): Expected string, got {type(json_str).__name__}")
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"fromJson(): Invalid JSON string: {e}")

def _jsonStringify(obj, indent=None) -> str:
    """
    Convert object to pretty JSON string with optional indentation.
    Similar to JavaScript's JSON.stringify(obj, null, indent)
    """
    try:
        if indent is not None:
            return json.dumps(obj, indent=indent, ensure_ascii=False)
        return json.dumps(obj, separators=(',', ':'), ensure_ascii=False)
    except (TypeError, ValueError) as e:
        raise ValueError(f"jsonStringify(): Cannot serialize object: {e}")

def _jsonParse(json_str: str):
    """Alias for fromJson() - JavaScript-style name."""
    return _fromJson(json_str)

def _pick(obj: dict, keys: list) -> dict:
    """
    Create new object with only specified keys.
    Similar to Lodash's _.pick()
    
    Example: pick(user, ["id", "name", "email"])
    """
    if not isinstance(obj, dict):
        raise TypeError(f"pick(): Expected dict, got {type(obj).__name__}")
    if not isinstance(keys, (list, tuple)):
        raise TypeError(f"pick(): Expected list of keys, got {type(keys).__name__}")
    
    return {k: obj[k] for k in keys if k in obj}

def _omit(obj: dict, keys: list) -> dict:
    """
    Create new object excluding specified keys.
    Similar to Lodash's _.omit()
    
    Example: omit(user, ["password", "secret"])
    """
    if not isinstance(obj, dict):
        raise TypeError(f"omit(): Expected dict, got {type(obj).__name__}")
    if not isinstance(keys, (list, tuple)):
        raise TypeError(f"omit(): Expected list of keys, got {type(keys).__name__}")
    
    return {k: v for k, v in obj.items() if k not in keys}

def _merge(*objects) -> dict:
    """
    Merge multiple objects into one (shallow merge).
    Later objects override earlier ones.
    Similar to JavaScript's Object.assign() or {...a, ...b}
    
    Example: merge(defaults, userSettings, overrides)
    """
    result = {}
    for obj in objects:
        if obj is None:
            continue
        if not isinstance(obj, dict):
            raise TypeError(f"merge(): All arguments must be dicts, got {type(obj).__name__}")
        result.update(obj)
    return result

def _keys(obj: dict) -> list:
    """
    Get list of object keys.
    Similar to JavaScript's Object.keys()
    """
    if not isinstance(obj, dict):
        raise TypeError(f"keys(): Expected dict, got {type(obj).__name__}")
    return list(obj.keys())

def _values(obj: dict) -> list:
    """
    Get list of object values.
    Similar to JavaScript's Object.values()
    """
    if not isinstance(obj, dict):
        raise TypeError(f"values(): Expected dict, got {type(obj).__name__}")
    return list(obj.values())

def _entries(obj: dict) -> list:
    """
    Get list of [key, value] pairs.
    Similar to JavaScript's Object.entries()
    
    Returns: [[key1, value1], [key2, value2], ...]
    """
    if not isinstance(obj, dict):
        raise TypeError(f"entries(): Expected dict, got {type(obj).__name__}")
    return [[k, v] for k, v in obj.items()]

def _hasKey(obj: dict, key: str) -> bool:
    """
    Check if object has a key.
    Similar to JavaScript's obj.hasOwnProperty(key)
    """
    if not isinstance(obj, dict):
        return False
    return key in obj

def _getPath(obj, path: str, default=None):
    """
    Deep access to nested object properties using dot notation.
    Similar to Lodash's _.get()
    
    Example: getPath(user, "settings.theme.color", "blue")
    Returns default if path doesn't exist.
    """
    if obj is None:
        return default
    
    keys = path.split('.')
    current = obj
    
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
            if current is None:
                return default
        else:
            return default
    
    return current if current is not None else default

DSL_FUNCTIONS = {
    # JSON serialization (JavaScript-style)
    "toJson":        (_toJson,        (1, 1)),
    "fromJson":      (_fromJson,      (1, 1)),
    "jsonStringify": (_jsonStringify, (1, 2)),
    "jsonParse":     (_jsonParse,     (1, 1)),
    
    # Object manipulation (JavaScript/Lodash-style)
    "pick":    (_pick,    (2, 2)),
    "omit":    (_omit,    (2, 2)),
    "merge":   (_merge,   (1, None)),
    "keys":    (_keys,    (1, 1)),
    "values":  (_values,  (1, 1)),
    "entries": (_entries, (1, 1)),
    "hasKey":  (_hasKey,  (2, 2)),
    "getPath": (_getPath, (2, 3)),
}

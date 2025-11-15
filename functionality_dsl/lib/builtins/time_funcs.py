import time
from datetime import datetime, timedelta

def _now() -> int:
    """Current time in Unix timestamp (seconds)."""
    return int(time.time())

def _today() -> str:
    """Current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")

def _time() -> str:
    """Current time in HH:MM:SS format."""
    return datetime.now().strftime("%H:%M:%S")

def _daysBetween(start_date, end_date) -> int:
    """
    Calculate days between two dates.
    Accepts Unix timestamps (int) or date strings (YYYY-MM-DD).
    """
    # Convert to datetime objects
    if isinstance(start_date, int):
        start = datetime.fromtimestamp(start_date)
    elif isinstance(start_date, str):
        start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start = start_date
    
    if isinstance(end_date, int):
        end = datetime.fromtimestamp(end_date)
    elif isinstance(end_date, str):
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end = end_date
    
    delta = end - start
    return delta.days

def _formatDate(timestamp, format_str) -> str:
    """
    Format a Unix timestamp as a string.
    
    Format codes:
    - YYYY: 4-digit year
    - MM: 2-digit month
    - DD: 2-digit day
    - HH: 2-digit hour (24-hour)
    - mm: 2-digit minute
    - ss: 2-digit second
    
    Example: formatDate(timestamp, "YYYY-MM-DD HH:mm:ss")
    """
    if isinstance(timestamp, str):
        # Try to parse as timestamp
        timestamp = int(timestamp)
    
    dt = datetime.fromtimestamp(timestamp)
    
    # Convert custom format to Python strftime format
    py_format = format_str
    py_format = py_format.replace("YYYY", "%Y")
    py_format = py_format.replace("MM", "%m")
    py_format = py_format.replace("DD", "%d")
    py_format = py_format.replace("HH", "%H")
    py_format = py_format.replace("mm", "%M")
    py_format = py_format.replace("ss", "%S")
    
    return dt.strftime(py_format)

def _parseDate(date_str, format_str) -> int:
    """
    Parse a date string into Unix timestamp.
    
    Format codes:
    - YYYY: 4-digit year
    - MM: 2-digit month
    - DD: 2-digit day
    - HH: 2-digit hour (24-hour)
    - mm: 2-digit minute
    - ss: 2-digit second
    
    Example: parseDate("2025-11-15", "YYYY-MM-DD")
    """
    # Convert custom format to Python strptime format
    py_format = format_str
    py_format = py_format.replace("YYYY", "%Y")
    py_format = py_format.replace("MM", "%m")
    py_format = py_format.replace("DD", "%d")
    py_format = py_format.replace("HH", "%H")
    py_format = py_format.replace("mm", "%M")
    py_format = py_format.replace("ss", "%S")
    
    dt = datetime.strptime(date_str, py_format)
    return int(dt.timestamp())

def _addDays(timestamp, days) -> int:
    """Add days to a Unix timestamp."""
    if isinstance(timestamp, str):
        timestamp = int(timestamp)
    dt = datetime.fromtimestamp(timestamp)
    new_dt = dt + timedelta(days=days)
    return int(new_dt.timestamp())

def _subtractHours(timestamp, hours) -> int:
    """Subtract hours from a Unix timestamp."""
    if isinstance(timestamp, str):
        timestamp = int(timestamp)
    dt = datetime.fromtimestamp(timestamp)
    new_dt = dt - timedelta(hours=hours)
    return int(new_dt.timestamp())

def _addHours(timestamp, hours) -> int:
    """Add hours to a Unix timestamp."""
    if isinstance(timestamp, str):
        timestamp = int(timestamp)
    dt = datetime.fromtimestamp(timestamp)
    new_dt = dt + timedelta(hours=hours)
    return int(new_dt.timestamp())

def _addMinutes(timestamp, minutes) -> int:
    """Add minutes to a Unix timestamp."""
    if isinstance(timestamp, str):
        timestamp = int(timestamp)
    dt = datetime.fromtimestamp(timestamp)
    new_dt = dt + timedelta(minutes=minutes)
    return int(new_dt.timestamp())

def _addSeconds(timestamp, seconds) -> int:
    """Add seconds to a Unix timestamp."""
    if isinstance(timestamp, str):
        timestamp = int(timestamp)
    return timestamp + seconds

DSL_FUNCTIONS = {
    # Current time/date
    "now":   (_now,   (0, 0)),
    "today": (_today, (0, 0)),
    "time":  (_time,  (0, 0)),
    
    # Time manipulation
    "daysBetween":   (_daysBetween,   (2, 2)),
    "formatDate":    (_formatDate,    (2, 2)),
    "parseDate":     (_parseDate,     (2, 2)),
    "addDays":       (_addDays,       (2, 2)),
    "addHours":      (_addHours,      (2, 2)),
    "addMinutes":    (_addMinutes,    (2, 2)),
    "addSeconds":    (_addSeconds,    (2, 2)),
    "subtractHours": (_subtractHours, (2, 2)),
}

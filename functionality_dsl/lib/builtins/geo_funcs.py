import math

def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two geographic points using Haversine formula.
    Returns distance in kilometers.

    Example: distance(40.7128, -74.0060, 51.5074, -0.1278) => 5570.25 (NYC to London)
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))

    # Earth radius in kilometers
    r = 6371.0

    return c * r

def _inRadius(lat: float, lon: float, center_lat: float, center_lon: float, radius_km: float) -> bool:
    """
    Check if a point is within a radius (circle) from center point.
    Radius is in kilometers.

    Example: inRadius(40.7128, -74.0060, 40.7580, -73.9855, 10) => True (Times Square within 10km of Central Park)
    """
    dist = _distance(lat, lon, center_lat, center_lon)
    return dist <= radius_km

def _bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate bearing (compass direction) from point 1 to point 2.
    Returns angle in degrees (0-360) where 0/360=North, 90=East, 180=South, 270=West.

    Example: bearing(40.7128, -74.0060, 51.5074, -0.1278) => ~51.4 (NYC to London is NE)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    lon2_rad = math.radians(lon2)

    dlon = lon2_rad - lon1_rad

    x = math.sin(dlon) * math.cos(lat2_rad)
    y = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(dlon)

    initial_bearing = math.atan2(x, y)

    # Convert to degrees and normalize to 0-360
    bearing_degrees = (math.degrees(initial_bearing) + 360) % 360

    return bearing_degrees

def _midpoint(lat1: float, lon1: float, lat2: float, lon2: float) -> list:
    """
    Calculate midpoint (geographic center) between two points.
    Returns [latitude, longitude] of the midpoint.

    Example: midpoint(40.7128, -74.0060, 51.5074, -0.1278) => [~46.5, ~-39.6] (mid-Atlantic)
    """
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    lon1_rad = math.radians(lon1)
    dlon = math.radians(lon2 - lon1)

    # Calculate midpoint
    bx = math.cos(lat2_rad) * math.cos(dlon)
    by = math.cos(lat2_rad) * math.sin(dlon)

    mid_lat = math.atan2(
        math.sin(lat1_rad) + math.sin(lat2_rad),
        math.sqrt((math.cos(lat1_rad) + bx) ** 2 + by ** 2)
    )

    mid_lon = lon1_rad + math.atan2(by, math.cos(lat1_rad) + bx)

    # Convert back to degrees
    return [math.degrees(mid_lat), math.degrees(mid_lon)]

def _boundingBox(lat: float, lon: float, radius_km: float) -> dict:
    """
    Calculate bounding box (min/max lat/lon) for a radius around a point.
    Useful for efficient geographic queries.
    Returns: {"minLat": float, "maxLat": float, "minLon": float, "maxLon": float}

    Example: boundingBox(40.7128, -74.0060, 10) => bounding box for 10km radius
    """
    # Earth radius in kilometers
    r = 6371.0

    # Angular distance in radians
    angular_dist = radius_km / r

    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    # Min/Max latitudes
    min_lat_rad = lat_rad - angular_dist
    max_lat_rad = lat_rad + angular_dist

    # Min/Max longitudes (adjusted for latitude)
    if min_lat_rad > -math.pi / 2 and max_lat_rad < math.pi / 2:
        delta_lon = math.asin(math.sin(angular_dist) / math.cos(lat_rad))
        min_lon_rad = lon_rad - delta_lon
        max_lon_rad = lon_rad + delta_lon
    else:
        # Polar region - longitude spans full range
        min_lon_rad = -math.pi
        max_lon_rad = math.pi

    return {
        "minLat": math.degrees(min_lat_rad),
        "maxLat": math.degrees(max_lat_rad),
        "minLon": math.degrees(min_lon_rad),
        "maxLon": math.degrees(max_lon_rad),
    }

def _inBoundingBox(lat: float, lon: float, bbox: dict) -> bool:
    """
    Check if a point is within a bounding box.
    bbox should have keys: minLat, maxLat, minLon, maxLon

    Example: inBoundingBox(40.7128, -74.0060, {"minLat": 40, "maxLat": 41, "minLon": -75, "maxLon": -73})
    """
    return (
        bbox["minLat"] <= lat <= bbox["maxLat"] and
        bbox["minLon"] <= lon <= bbox["maxLon"]
    )


DSL_GEO_FUNCS = {
    "distance":       (_distance, (4, 4)),
    "inRadius":       (_inRadius, (5, 5)),
    "bearing":        (_bearing, (4, 4)),
    "midpoint":       (_midpoint, (4, 4)),
    "boundingBox":    (_boundingBox, (3, 3)),
    "inBoundingBox":  (_inBoundingBox, (3, 3)),
}

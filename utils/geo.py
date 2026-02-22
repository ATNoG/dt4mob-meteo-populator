from typing import List, Optional, Union

from models.geo import Point
from models.station import Station


def representative_point(location: Union[Point, List[Point], None]) -> Optional[Point]:
    """
    Returns a single representative Point from a Thing's location attribute.
    For a list of points (e.g. polygon vertices), the geometric centroid
    (mean latitude, mean longitude) is returned.
    """
    if location is None:
        return None
    if isinstance(location, list):
        if not location:
            return None
        return Point(
            latitude=sum(p.latitude for p in location) / len(location),
            longitude=sum(p.longitude for p in location) / len(location),
        )
    return location


def closest_stations(
    point: Point,
    stations: list[Station],
    max_distance: float = 100.0,
    n: int = 3,
) -> list[Station]:
    """
    Returns the n nearest Stations to the given point that fall within
    max_distance km, sorted by ascending distance.
    """
    ranked = sorted(stations, key=lambda s: s.distance_to(point))
    return [s for s in ranked[:n] if s.distance_to(point) <= max_distance]

import math

from pydantic import BaseModel

from models.geo import Point


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class Station(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float

    def distance_to(self, point: Point) -> float:
        """Returns the great-circle distance in km from this station to the given point."""
        return _haversine(
            self.latitude, self.longitude, point.latitude, point.longitude
        )

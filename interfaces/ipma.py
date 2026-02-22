import json
from datetime import datetime, timezone

from aiohttp import ClientSession

from models.station import Station

IPMA_GEOJSON_URL = (
    "https://api.ipma.pt/open-data/observation/meteorology/stations/obs-surface.geojson"
)


async def fetch_active_stations() -> list[Station]:
    """
    Fetches active meteorological stations from IPMA's GeoJSON surface
    observations endpoint. Stations with measurements older than 2 hours
    are excluded, matching the staleness filter in the source project.
    Uses its own session — IPMA is a public API and needs no credentials.
    """
    async with ClientSession() as session:
        async with session.get(IPMA_GEOJSON_URL) as resp:
            resp.raise_for_status()
            data = json.loads(await resp.text())

    current_time = datetime.now(timezone.utc)
    stations: list[Station] = []

    for feature in data["features"]:
        props = feature["properties"]

        measurement_dt = datetime.strptime(props["time"], "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc
        )

        if (current_time - measurement_dt).total_seconds() > 7200:
            continue

        # GeoJSON coordinates are always [longitude, latitude]
        lon, lat = feature["geometry"]["coordinates"]

        stations.append(
            Station(
                id=props["idEstacao"],
                name=props["localEstacao"],
                latitude=lat,
                longitude=lon,
            )
        )

    return stations

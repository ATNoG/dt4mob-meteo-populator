import asyncio

from aiohttp import BasicAuth, ClientSession
from loguru import logger

from interfaces.ipma import fetch_active_stations
from models.request import SearchResponse
from models.station import Station
from models.thing import Thing
from settings import settings
from utils.geo import closest_stations, representative_point


async def fetch_all_things(session: ClientSession) -> list[Thing]:
    filters = 'and(or(exists(attributes/location),exists(attributes/geometry)),not(eq(namespace,"meteo")))'
    fields = "thingId,attributes(location,geometry)"
    url_base = (
        f"{settings.ditto.base_url}/search/things?filter={filters}&fields={fields}"
    )

    last_response: SearchResponse | None = None
    things: list[Thing] = []

    while True:
        curr_url = url_base
        if last_response and last_response.cursor:
            curr_url += f"&option=cursor({last_response.cursor})"
        async with session.get(curr_url, ssl=False) as resp:
            last_response = SearchResponse(**(await resp.json()))
        things.extend(last_response.items)
        if last_response.cursor is None:
            break

    return things


async def patch_closest_stations(
    session: ClientSession, thing_id: str, stations: list[Station]
) -> None:
    url = (
        f"{settings.ditto.base_url}/things/{thing_id}/attributes/closest_meteo_stations"
    )
    value = [f"meteo:{s.id}" for s in stations]
    async with session.put(url, json=value, ssl=False) as resp:
        if resp.status not in (200, 201, 204):
            logger.warning("Failed to patch {}: HTTP {}", thing_id, resp.status)
        else:
            logger.debug("Patched {} → {}", thing_id, value)


async def populate_closest_stations(
    session: ClientSession, things: list[Thing], stations: list[Station]
) -> None:
    for thing in things:
        point = representative_point(thing.attributes.location)
        if point is None:
            logger.warning("Skipping {}: no parseable location", thing.thingId)
            continue

        nearby = closest_stations(point, stations)
        if not nearby:
            logger.warning("Skipping {}: no stations within range", thing.thingId)
            continue

        await patch_closest_stations(session, thing.thingId, nearby)


async def run() -> None:
    auth = BasicAuth(
        login=settings.ditto.username,
        password=settings.ditto.password,
    )

    async with ClientSession(auth=auth) as s:
        while True:
            logger.info("Starting population cycle")

            stations = await fetch_active_stations()
            logger.info("Fetched {} active IPMA stations", len(stations))

            things = await fetch_all_things(s)
            logger.info("Collected {} things from Ditto", len(things))

            await populate_closest_stations(s, things, stations)

            logger.info(
                "Population cycle complete, sleeping for {}s",
                settings.populator.polling_interval,
            )
            await asyncio.sleep(settings.populator.polling_interval)


if __name__ == "__main__":
    asyncio.run(run())

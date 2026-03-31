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
    logger.info("Starting to fetch things from Ditto")
    filters = 'and(or(exists(attributes/location),exists(attributes/geometry)),not(eq(namespace,"meteo")),not(exists(attributes/closest_meteo_stations)))'
    fields = "thingId,attributes(location,geometry)"
    url_base = (
        f"{settings.ditto.base_url}/search/things?filter={filters}&fields={fields}"
    )

    last_response: SearchResponse | None = None
    things: list[Thing] = []
    page = 0

    while True:
        curr_url = url_base
        if last_response and last_response.cursor:
            curr_url += f"&option=cursor({last_response.cursor}),size(200)"
        else:
            curr_url += "&option=size(200)"
        logger.debug("Fetching things page {}", page)
        async with session.get(curr_url, ssl=False) as resp:
            last_response = SearchResponse(**(await resp.json()))
        things.extend(last_response.items)
        logger.debug("Fetched {} things on page {}", len(last_response.items), page)
        page += 1
        if last_response.cursor is None:
            break

    logger.info(
        "Completed fetching things", extra={"total_things": len(things), "pages": page}
    )
    return things


async def patch_closest_stations(
    session: ClientSession, thing_id: str, stations: list[Station]
) -> bool:
    url = (
        f"{settings.ditto.base_url}/things/{thing_id}/attributes/closest_meteo_stations"
    )
    value = [f"meteo:{s.id}" for s in stations]

    if settings.populator.dry_run:
        logger.debug(
            "[DRY-RUN] Would patch thing",
            extra={"thing_id": thing_id, "stations": value},
        )
        return True

    logger.debug(
        "Patching thing with closest stations",
        extra={"thing_id": thing_id, "stations": value},
    )
    async with session.put(url, json=value, ssl=False) as resp:
        if resp.status not in (200, 201, 204):
            logger.error(
                "Failed to patch thing",
                extra={"thing_id": thing_id, "status": resp.status},
            )
            return False
        return True


async def populate_closest_stations(
    session: ClientSession, things: list[Thing], stations: list[Station]
) -> None:
    success_count = 0
    skip_no_location = 0
    skip_no_stations = 0

    for thing in things:
        point = representative_point(thing.attributes.location)
        if point is None:
            logger.warning(
                "Skipping thing: no parseable location",
                extra={"thing_id": thing.thingId},
            )
            skip_no_location += 1
            continue

        nearby = closest_stations(point, stations)
        if not nearby:
            logger.warning(
                "Skipping thing: no stations within range",
                extra={
                    "thing_id": thing.thingId,
                    "point": {"lat": point.latitude, "lon": point.longitude},
                },
            )
            skip_no_stations += 1
            continue

        if await patch_closest_stations(session, thing.thingId, nearby):
            success_count += 1

    logger.info(
        "Completed populating closest stations",
        extra={
            "total_things": len(things),
            "success": success_count,
            "skipped_no_location": skip_no_location,
            "skipped_no_stations": skip_no_stations,
        },
    )


async def run() -> None:
    auth = BasicAuth(
        login=settings.ditto.username,
        password=settings.ditto.password,
    )

    async with ClientSession(auth=auth) as s:
        while True:
            logger.info(
                "Starting population cycle",
                extra={"dry_run": settings.populator.dry_run},
            )

            try:
                stations = await fetch_active_stations()
                logger.info(
                    "Fetched active IPMA stations",
                    extra={"station_count": len(stations)},
                )

                things = await fetch_all_things(s)
                logger.info(
                    "Collected things from Ditto", extra={"thing_count": len(things)}
                )

                if len(things) > 0:
                    await populate_closest_stations(s, things, stations)

            except Exception as e:
                logger.exception(
                    "Error during population cycle", extra={"error": str(e)}
                )

            logger.info(
                "Population cycle complete, sleeping",
                extra={"sleep_seconds": settings.populator.polling_interval},
            )
            await asyncio.sleep(settings.populator.polling_interval)


if __name__ == "__main__":
    asyncio.run(run())

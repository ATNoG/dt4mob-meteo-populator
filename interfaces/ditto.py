from aiohttp import ClientSession
from loguru import logger

from models.request import SearchResponse
from models.station import Station
from models.thing import PopulateResult, Thing
from settings import settings
from utils.geo import closest_stations, representative_point


async def fetch_all_things(session: ClientSession) -> list[Thing]:
    logger.info("Starting to fetch things from Ditto")
    filters = settings.filter.filter
    fields = settings.filter.fields
    url_base = f"search/things?filter={filters}&fields={fields}"

    last_response: SearchResponse | None = None
    things: list[Thing] = []
    page = 0

    while True:
        curr_url: str = url_base

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
    url = f"things/{thing_id}/attributes/closest_meteo_stations"
    value = [
        f"{settings.station.namespace}:{settings.station.subject}:{s.id}"
        for s in stations
    ]

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
    session: ClientSession, thing: Thing, stations: list[Station]
) -> PopulateResult:
    point = representative_point(thing.attributes.location)
    if point is None:
        logger.warning(
            "Skipping thing: no parseable location",
            extra={"thing_id": thing.thingId},
        )
        return PopulateResult.NO_LOCATION

    nearby = closest_stations(point, stations)
    if not nearby:
        logger.warning(
            "Skipping thing: no stations within range",
            extra={
                "thing_id": thing.thingId,
                "point": {"lat": point.latitude, "lon": point.longitude},
            },
        )
        return PopulateResult.NO_STATIONS

    if await patch_closest_stations(session, thing.thingId, nearby):
        return PopulateResult.SUCCESS

    return PopulateResult.ERR

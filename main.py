import asyncio
import sys
from datetime import datetime, timezone

from aiohttp import ClientSession
from loguru import logger

from interfaces.ditto import (
    fetch_all_things,
    populate_closest_stations,
)
from interfaces.ipma import fetch_active_stations
from interfaces.oidc import get_tokens, refresh_token
from models.thing import PopulateResult
from settings import settings


async def run() -> None:
    tokens = await get_tokens()
    assert tokens

    headers: dict[str, str] = {"Authorization": f"Bearer {tokens.access}"}

    async with ClientSession(base_url=settings.ditto.url, headers=headers) as s:
        logger.info(
            "Starting population cycle",
            extra={"dry_run": settings.populator.dry_run},
        )

        stations = await fetch_active_stations()
        logger.info(
            "Fetched active IPMA stations",
            extra={"station_count": len(stations)},
        )

        things = await fetch_all_things(s)
        logger.info("Collected things from Ditto", extra={"thing_count": len(things)})

        if len(things) <= 0:
            logger.info("No things to populate")
            return

        success_count, skip_no_location, skip_no_stations = 0, 0, 0
        for thing in things:
            if datetime.now(timezone.utc) >= tokens.expiry:
                logger.warning("The token has expired. Renewing the token")
                tokens = await refresh_token(tokens.refresh)
                assert tokens

            result = await populate_closest_stations(s, thing, stations)

            match result:
                case PopulateResult.NO_STATIONS:
                    skip_no_stations += 1
                case PopulateResult.NO_LOCATION:
                    skip_no_location += 1
                case PopulateResult.SUCCESS:
                    success_count += 1
                case PopulateResult.ERR:
                    logger.error("An error has occured while patching a Thing")

            logger.info(
                "Completed populating closest stations",
                extra={
                    "total_things": len(things),
                    "success": success_count,
                    "skipped_no_location": skip_no_location,
                    "skipped_no_stations": skip_no_stations,
                },
            )

        logger.info("Population cycle complete")

        # TODO: Revoke tokens at the end of the script


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as e:
        logger.exception("Fatal error during population cycle", extra={"error": str(e)})
        sys.exit(1)

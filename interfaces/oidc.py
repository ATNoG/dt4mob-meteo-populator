import ssl
from datetime import datetime, timedelta, timezone

import aiohttp
from loguru import logger
from pydantic import BaseModel

from settings import settings


class Tokens(BaseModel):
    access: str
    refresh: str
    expiry: datetime


async def get_tokens() -> Tokens | None:
    url = settings.oidc.url
    username = settings.oidc.username
    password = settings.oidc.password
    client_id = settings.oidc.client_id
    scope = settings.oidc.scope

    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": client_id,
        "scope": scope,
    }

    ssl_context = ssl.create_default_context()
    if settings.oidc.ca_file is not None:
        ssl_context.load_verify_locations(cafile=settings.oidc.ca_file)

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_context)
    ) as session:
        async with session.post(url, data=data) as response:
            try:
                response.raise_for_status()
                jason = await response.json()
                access_token = jason.get("access_token")
                refresh_token = jason.get("refresh_token")
                expiry = int(jason.get("expires_in"))

            except aiohttp.ClientResponseError as e:
                logger.error("failed to acquire tokens with error: {}", e.status)
                return None

    return Tokens(
        access=access_token,
        refresh=refresh_token,
        expiry=datetime.now(timezone.utc) + timedelta(seconds=expiry),
    )


async def refresh_token(refresh_token: str) -> Tokens | None:
    url = settings.oidc.url
    client_id = settings.oidc.client_id
    scope = settings.oidc.scope

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "scope": scope,
    }

    ssl_context = ssl.create_default_context()
    if settings.oidc.ca_file is not None:
        ssl_context.load_verify_locations(cafile=settings.oidc.ca_file)

    async with aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(ssl=ssl_context)
    ) as session:
        async with session.post(url, data=data) as response:
            try:
                response.raise_for_status()
                jason = await response.json()
                access_token = jason.get("access_token")
                new_refresh_token = jason.get("refresh_token")
                expiry = int(jason.get("expires_in"))

            except aiohttp.ClientResponseError as e:
                logger.error("failed to refresh token with error: {}", e.status)
                return None

    return Tokens(
        access=access_token,
        refresh=new_refresh_token,
        expiry=datetime.now(timezone.utc) + timedelta(seconds=expiry),
    )

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
    base_url = settings.oidc.base_url
    username = settings.oidc.username
    password = settings.oidc.password
    client_id = settings.oidc.client_id
    realm = settings.oidc.realm
    scope = settings.oidc.scope

    url = f"{base_url}/auth/realms/{realm}/protocol/openid-connect/token"

    data = {
        "grant_type": "password",
        "username": username,
        "password": password,
        "client_id": client_id,
        "scope": scope,
    }

    async with aiohttp.ClientSession() as session:
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
    base_url = settings.oidc.base_url
    client_id = settings.oidc.client_id
    realm = settings.oidc.realm
    scope = settings.oidc.scope

    url = f"{base_url}/auth/realms/{realm}/protocol/openid-connect/token"

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "scope": scope,
    }

    async with aiohttp.ClientSession() as session:
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

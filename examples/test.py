"""Test file for Sensibo."""

from __future__ import annotations

import asyncio

import aiohttp

from pysensibo import SensiboClient


async def main(event_loop: asyncio.AbstractEventLoop) -> None:
    """Retrieve device information from Sensibo cloud."""
    async with aiohttp.ClientSession(loop=event_loop) as session:
        client = SensiboClient("API_KEY", session)
        devices = await client.async_get_devices_data()
        print(devices)  # noqa: T201


loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))

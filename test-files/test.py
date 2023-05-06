from pysensibo import SensiboClient
import aiohttp
import asyncio


async def main(loop):
	async with aiohttp.ClientSession(loop=loop) as session:
		client = SensiboClient("KKL92NKBPPiJJXkoNcgiaM4tIvQbIQ",session)
		location = await client.async_get_locations(["APH4U3Lq3N"])
		print(location)

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))

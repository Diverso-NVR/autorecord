import os
from aiohttp import ClientSession
import logging


NVR_API_URL = "https://nvr.miem.hse.ru/api/erudite"
NVR_API_KEY = os.getenv("NVR_API_KEY")

logger = logging.getLogger("fileuploader")


async def send_record(
    room_name: str,
    date: str,
    start_time: str,
    end_time: str,
    record_url: str,
):
    async with ClientSession() as session:
        async with session.post(
            f"{NVR_API_URL}/records",
            json={
                "room_name": room_name,
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "url": record_url,
                "type": "Autorecord",
            },
            headers={"key": NVR_API_KEY},
            ssl=False,
        ) as resp:
            logger.info(f"Erudite response: {await resp.json()}")

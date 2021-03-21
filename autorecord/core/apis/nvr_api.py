from httpx import AsyncClient
from loguru import logger

from autorecord.core.settings import config

NVR_API_URL = config.nvr_api_url
NVR_API_KEY = config.nvr_api_key


async def send_record(
    room_name: str,
    date: str,
    start_time: str,
    end_time: str,
    record_url: str,
):
    data = {
        "room_name": room_name,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "url": record_url,
        "type": "Autorecord",
    }

    async with AsyncClient() as client:
        resp = await client.post(
            f"{NVR_API_URL}/records",
            json=data,
            headers={"key": NVR_API_KEY},
        )

    logger.info(f"Erudite response: {resp.json()}")

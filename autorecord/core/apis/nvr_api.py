from aiohttp import ClientSession
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
    camera_ip: str,
):
    """
    Отправить данные о записи в эрудит

    :param room_name: имя комнаты
    :param date: дата записи
    :param start_time: время начала записи
    :param end_time: время окончания записи
    :param record_url: ссылка на запись на гугл диске
    :param camera_ip: ip камеры с которой была запись
    """
    data = {
        "room_name": room_name,
        "date": date,
        "start_time": start_time,
        "end_time": end_time,
        "url": record_url,
        "type": "Autorecord",
        "camera_ip": camera_ip,
    }

    async with ClientSession() as session:
        resp = await session.post(
            f"{NVR_API_URL}/erudite/records",
            json=data,
            headers={"key": NVR_API_KEY},
            ssl=False,
        )

    logger.debug(f"Erudite response: {await resp.json()}")

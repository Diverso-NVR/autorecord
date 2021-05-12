import asyncpg
from contextlib import asynccontextmanager

from autorecord.core.settings import config


@asynccontextmanager
async def db_connect():
    """Контекстный менеджер для подключения к бд"""
    conn = await asyncpg.connect(config.psql_url)
    try:
        yield conn
    finally:
        await conn.close()


async def get_rooms():
    """Собрать все комнаты из бд"""
    async with db_connect() as conn:
        return await conn.fetch("SELECT * from rooms")


async def get_room_sources(room_id):
    """
    Собрать все источники комнаты
    :param room_id: id комнаты в бд
    """
    async with db_connect() as conn:
        return await conn.fetch("SELECT * from sources where room_id = $1", room_id)

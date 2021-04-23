import asyncpg
from contextlib import asynccontextmanager

from autorecord.core.settings import config
from autorecord.core.models import Room


@asynccontextmanager
async def db_connect():
    conn = await asyncpg.connect(config.psql_url)
    try:
        yield conn
    finally:
        await conn.close()


async def get_rooms():
    async with db_connect() as conn:
        return await conn.fetch("SELECT * from rooms")


async def get_room_sources(room_id):
    async with db_connect() as conn:
        return await conn.fetch("SELECT * from sources where room_id = $1", room_id)


async def load_rooms():
    rooms = [Room(room_dict) for room_dict in await get_rooms()]
    for room in rooms:
        room.sources = await get_room_sources(room.id)
        yield room

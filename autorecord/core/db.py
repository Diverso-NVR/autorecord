import triopg

from autorecord.core.settings import config


async def get_rooms():
    async with triopg.connect(config.psql_url) as conn:
        return await conn.fetch("SELECT * from rooms")


async def get_room_sources(room_id):
    async with triopg.connect(config.psql_url) as conn:
        return await conn.fetch("SELECT * from sources where room_id = $1", room_id)
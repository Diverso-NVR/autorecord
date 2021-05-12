import os
import asyncio
from asyncio.subprocess import PIPE

from loguru import logger

from autorecord.core.models import Room
from autorecord.core.db import get_rooms, get_room_sources


async def load_rooms():
    rooms = [Room(room_dict) for room_dict in await get_rooms()]
    for room in rooms:
        room.sources = await get_room_sources(room.id)
        yield room


async def run_cmd(cmd: str or list):
    if isinstance(cmd, str):
        cmd = cmd.split(" ")

    return await asyncio.create_subprocess_exec(
        *cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE
    )


def remove_file(filename: str) -> None:
    try:
        os.remove(filename)
    except FileNotFoundError:
        logger.debug(f"Failed to remove file {filename}, not found")
    except Exception as err:
        logger.warning(f"Failed to remove file {filename}, {err}")

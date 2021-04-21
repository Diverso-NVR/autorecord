import os
import asyncio
from asyncio.subprocess import PIPE

from loguru import logger


def drange(start: float, stop: float, step: float):
    r = start
    while r < stop:
        yield r
        r += step


async def run_cmd(cmd: str or list):
    if isinstance(cmd, str):
        cmd = cmd.split(" ")

    return await asyncio.create_subprocess_exec(
        *cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE
    )


async def process_stop(process):
    if process.returncode is None:
        process.terminate()
        await process.wait()


def remove_file(filename: str) -> None:
    try:
        os.remove(filename)
    except FileNotFoundError:
        logger.warning(f"Failed to remove file {filename}")
    except:
        logger.error(f"Failed to remove file {filename}")

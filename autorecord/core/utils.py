import os
import trio
from subprocess import PIPE


from loguru import logger


def drange(start: float, stop: float, step: float):
    r = start
    while r < stop:
        yield r
        r += step


async def run_cmd(cmd: str or list):
    if isinstance(cmd, str):
        cmd = cmd.split(" ")

    return await trio.open_process(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)


def remove_file(filename: str) -> None:
    try:
        os.remove(filename)
    except FileNotFoundError:
        logger.warning(f"Failed to remove file {filename}")
    except:
        logger.error(f"Failed to remove file {filename}")

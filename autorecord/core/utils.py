import os
from loguru import logger


def drange(start, stop, step):
    r = start
    while r < stop:
        yield r
        r += step


def remove_file(filename: str) -> None:
    try:
        os.remove(filename)
    except FileNotFoundError:
        logger.warning(f"Failed to remove file {filename}")
    except:
        logger.error(f"Failed to remove file {filename}")

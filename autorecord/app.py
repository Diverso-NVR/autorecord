import time
import schedule

from loguru import logger
import trio_asyncio

from autorecord.core.settings import config
from autorecord.core.db import get_rooms


class DaemonApp:
    def __init__(self):
        logger.info('Class "DaemonApp" instantiated')

        for weekday in config.record_days:
            # TODO: schedule tasks
            pass

    def start_new_recording(self):
        logger.info("Starting recording")

        rooms = trio_asyncio.run(get_rooms)
        # TODO stop and start records

    def stop_records(self):
        logger.info("Stoping daemon")
        rooms = trio_asyncio.run(get_rooms)
        # TODO: Stop records func

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    daemon_app = DaemonApp()
    daemon_app.run()
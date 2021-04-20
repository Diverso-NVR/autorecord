import time
import schedule

import trio
from loguru import logger

from autorecord.core.settings import config
from autorecord.core.db import get_rooms
from autorecord.core.managers import Recorder, AudioMapper, Uploader, Publisher, Cleaner


class Autorecord:
    def __init__(self):
        logger.info('Class "Autorecord" instantiated')

        self.recorders = []

        for weekday in config.record_days:
            # TODO: schedule tasks
            pass

    def start_rooms_recordings(self):
        trio.run(self.stop_records)
        trio.run(self.start_records)

    async def start_records(self):
        logger.info("Starting recording")

        rooms = await get_rooms()
        async with trio.open_nursery() as nursery:
            for room in rooms:
                if not room.sources:
                    continue

                recorder = Recorder(room)
                nursery.start_soon(recorder.start_record)
                self.recorders.append(recorder)

    async def stop_records(self):
        logger.info("Stopping recording")

        async with trio.open_nursery() as nursery:
            for recorder in self.recorders:
                nursery.start_soon(self.process_records, recorder, nursery)

        self.recorders = []

    async def process_records(self, recorder, nursery):
        await trio.to_thread.run_sync(recorder.stop_record)
        for source in recorder.room.sources:
            nursery.start_soon(self.process_source, recorder, source)

    async def process_source(self, recorder, source):
        await AudioMapper.map_video_and_sound(recorder, source)
        file_id = await Uploader.upload(recorder, source)
        await Publisher.send_to_erudite(recorder, file_id)
        await trio.to_thread.run_sync(Cleaner.clear_video, recorder, source)

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    autorec = Autorecord()
    autorec.run()
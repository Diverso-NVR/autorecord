import time
import asyncio
from collections import deque
from threading import Thread

from loguru import logger
import schedule

from autorecord.core.settings import config
from autorecord.core.db import get_room_sources, get_rooms
from autorecord.core.managers import Recorder, AudioMapper, Uploader, Publisher, Cleaner
from autorecord.core.models import Room


class Autorecord:
    def __init__(self, loop):
        logger.info('Class "Autorecord" instantiated')

        self._recorders = deque()
        self._loop = loop

        schedule.every(60).seconds.do(self.start_rooms_recordings)

        # for weekday in config.record_days:
        #     # TODO: schedule tasks
        #     pass

    def start_rooms_recordings(self):
        self.stop_records()
        self._loop.create_task(self.start_records())

    async def load_rooms(self):
        rooms = [Room(room_dict) for room_dict in await get_rooms()]
        for room in rooms:
            room.sources = await get_room_sources(room.id)
            yield room

    async def start_records(self):
        logger.info("Starting recording")

        async for room in self.load_rooms():
            if not room.sources:
                continue

            recorder = Recorder(room)
            self._recorders.append(recorder)

        await asyncio.gather(*[recorder.start_record() for recorder in self._recorders])

    def stop_records(self):
        logger.info("Stopping recording")

        while self._recorders:
            recorder = self._recorders.pop()
            self._loop.create_task(self.process_records(recorder))

    async def process_records(self, recorder):
        await recorder.stop_record()
        if not Cleaner.is_sound_exist(recorder):
            await asyncio.gather(
                *[
                    self._loop.run_in_executor(
                        None, Cleaner.clear_video, recorder, source
                    )
                    for source in recorder.room.sources
                ]
            )
            return

        folder_id = await Uploader.prepare_folders(recorder)
        await asyncio.gather(
            *[
                self.process_source(recorder, source, folder_id)
                for source in recorder.room.sources
            ]
        )
        await self._loop.run_in_executor(None, Cleaner.clear_sound, recorder)

    async def process_source(self, recorder, source, folder_id):
        if not Cleaner.is_video_exist(recorder, source):
            return

        await AudioMapper.map_video_and_sound(recorder, source)
        file_id = await Uploader.upload(recorder, source, folder_id)
        # await Publisher.send_to_erudite(recorder, file_id)
        await self._loop.run_in_executor(None, Cleaner.clear_video, recorder, source)

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    autorec = Autorecord(loop)
    autorec.start_rooms_recordings()
    Thread(target=autorec.run).start()
    loop.run_forever()

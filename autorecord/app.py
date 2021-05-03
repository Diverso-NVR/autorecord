import time
import asyncio
from collections import deque
from threading import Thread

from loguru import logger
import schedule

from autorecord.core.settings import config
from autorecord.core.db import load_rooms
from autorecord.core.managers import Recorder, AudioMapper, Uploader, Publisher, Cleaner


class Autorecord:
    def __init__(self, loop):
        logger.info('Class "Autorecord" instantiated')

        self._recorders = deque()
        self._loop = loop

        schedule.every(600).seconds.do(self.start_rooms_recordings)

        # for weekday in config.record_days:
        #     # TODO: schedule tasks
        #     pass

    def start_rooms_recordings(self):
        self._loop.create_task(self.start_records())

    async def start_records(self):
        logger.info("Stopping recording")
        recorders_to_process = []
        while self._recorders:
            recorder = self._recorders.pop()
            self._loop.create_task(recorder.stop_record())
            recorders_to_process.append(recorder)

        logger.info("Starting recording")
        async for room in load_rooms():
            if not room.sources:
                continue

            recorder = Recorder(room)
            self._recorders.append(recorder)
            self._loop.create_task(recorder.start_record())

        for recorder in recorders_to_process:
            self._loop.create_task(self.process_records(recorder))

    async def process_records(self, recorder):
        if not Cleaner.is_sound_exist(recorder):
            for source in recorder.room.sources:
                await self._loop.run_in_executor(
                    None, Cleaner.clear_video, recorder, source
                )
            return

        folder_id = await Uploader.prepare_folders(recorder)
        for source in recorder.room.sources:
            await self.process_source(recorder, source, folder_id)
        await self._loop.run_in_executor(None, Cleaner.clear_sound, recorder)

    async def process_source(self, recorder, source, folder_id):
        if not Cleaner.is_video_exist(recorder, source):
            return

        await AudioMapper.map_video_and_sound(recorder, source)
        file_id = await Uploader.upload(recorder, source, folder_id)
        await Publisher.send_to_erudite(recorder, source, file_id)

        await self._loop.run_in_executor(None, Cleaner.clear_video, recorder, source)
        await self._loop.run_in_executor(None, Cleaner.clear_result, recorder, source)

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

import asyncio
from collections import deque

from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from autorecord.core.settings import config
from autorecord.core.utils import load_rooms
from autorecord.core.managers import Recorder, AudioMapper, Uploader, Publisher, Cleaner


class Autorecord:
    def __init__(self, loop):
        logger.info('Class "Autorecord" instantiated')

        self._recorders = deque()
        self._loop = loop

        self._scheduler = AsyncIOScheduler()
        self._scheduler.add_job(
            func=self.restart_records,
            name="records",
            trigger="cron",
            day_of_week=",".join(config.record_days),
            hour=f"{config.record_start}-{config.record_end-1}",
            minute=f"*/{config.record_duration}",
        )
        self._scheduler.add_job(
            func=self.stop_records,
            name="records_stop",
            trigger="cron",
            day_of_week=",".join(config.record_days),
            hour=config.record_end,
        )
        self._scheduler.start()

        logger.info(
            f"Created scheduler tasks: {[str(job) for job in self._scheduler.get_jobs()]}"
        )

    async def restart_records(self):
        self.stop_records()
        await self.start_records()

    def stop_records(self):
        logger.info("Stopping recording")
        while self._recorders:
            recorder = self._recorders.pop()
            self._loop.create_task(recorder.stop_record())
            self._loop.create_task(self.process_records(recorder))

    async def start_records(self):
        logger.info("Starting recording")
        async for room in load_rooms():
            if not room.sources:
                continue

            recorder = Recorder(room)
            self._recorders.append(recorder)
            self._loop.create_task(recorder.start_record())

    async def process_records(self, recorder):
        """Обработка записей"""
        if not Cleaner.is_sound_exist(recorder) and not config.upload_without_sound:
            # Если нет звука для рекордера или не выставлен флаг загрузки видео без звука – удаляем все видео рекордера
            for source in recorder.room.sources:
                await self._loop.run_in_executor(
                    None, Cleaner.clear_video, recorder, source
                )
            return

        # Создаём папки для загрузки видео
        folder_id = await Uploader.prepare_folders(recorder)
        await asyncio.gather(
            *[
                self.process_source(recorder, source, folder_id)
                for source in recorder.room.sources
            ]
        )
        await self._loop.run_in_executor(None, Cleaner.clear_sound, recorder)

    async def process_source(self, recorder, source, folder_id):
        """Обработка источника"""
        if not Cleaner.is_video_exist(recorder, source):
            return

        await AudioMapper.map_video_and_sound(recorder, source)
        file_id = await Uploader.upload(recorder, source, folder_id)
        await Publisher.send_to_erudite(recorder, source, file_id)

        await self._loop.run_in_executor(None, Cleaner.clear_video, recorder, source)
        await self._loop.run_in_executor(None, Cleaner.clear_result, recorder, source)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    autorec = Autorecord(loop)
    loop.run_forever()

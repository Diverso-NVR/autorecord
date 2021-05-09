import asyncio
import os
from datetime import datetime, timedelta

import pytz
from loguru import logger

from autorecord.core.utils import run_cmd, remove_file, process_stop
from autorecord.core.apis.drive_api import GoogleDrive
from autorecord.core.apis.nvr_api import send_record
from autorecord.core.settings import config


RECORDS_FOLDER = config.records_folder
RECORD_DURATION = config.record_duration * 60

# Шаблон команды ffmpeg для записи видео, в которую подставляются:
#  – rtsp источника
#  – имя комнаты
FFMPEG_SOUND_RECORD_CMD_TEMPLATE = (
    "ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i {source_rtsp} "
    f"-t {RECORD_DURATION} -y -c:a copy -vn -f mp4 {RECORDS_FOLDER}/sound_"
    "{record_name}.aac"
)

# Шаблон команды ffmpeg для записи аудио, в которую подставляются:
#  – rtsp источника
#  – имя комнаты
#  – id источника из бд
FFMPEG_VIDEO_RECORD_CMD_TEMPLATE = (
    "ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i {source_rtsp} "
    f"-t {RECORD_DURATION} -y -c:v copy -an -f mp4 {RECORDS_FOLDER}/vid_"
    "{record_name}_{source_id}.mp4"
)

# Шаблон команды ffmpeg для наложения звука на видео, в которую подставляются:
#  – имя комнаты
#  – id источника из бд
FFMPEG_MAP_CMD_TEMPLATE = (
    f"ffmpeg -i {RECORDS_FOLDER}/sound_"
    "{record_name}.aac "
    f"-i {RECORDS_FOLDER}/vid_"
    "{record_name}_{source_id}.mp4 "
    f"-y -shortest -c copy {RECORDS_FOLDER}/"
    "{record_name}_{source_id}.mp4"
)


class Recorder:
    """Класс для управления процессом записи"""

    def __init__(self, room):
        """
        Один объект создается на одну комнату.
        Объект Recorder`а содержит в себе:
            – комнату, в которой будет записывать
            – список процессов записи
            – datetime начала записи
            – имя записи, составленное из даты и времени записи, и id комнаты
        """
        self.room = room
        self.record_processes = []

        self.record_dt = datetime.now(tz=pytz.timezone("Europe/Moscow")).replace(
            tzinfo=None,
            second=0,
            microsecond=0,
        )
        self.record_name = self.record_dt.isoformat(timespec="minutes") + f"_{room.id}"

    async def start_record(self):
        sound_source_rtsp = self.room.sound_source
        sound_proc = await run_cmd(
            FFMPEG_SOUND_RECORD_CMD_TEMPLATE.format(
                source_rtsp=sound_source_rtsp,
                record_name=self.record_name,
            )
        )
        self.record_processes.append(sound_proc)

        for source in self.room.sources:
            proc = await run_cmd(
                FFMPEG_VIDEO_RECORD_CMD_TEMPLATE.format(
                    source_rtsp=source.rtsp,
                    record_name=self.record_name,
                    source_id=source.id,
                )
            )
            self.record_processes.append(proc)

        logger.info(f"Started recording {self.room.name}")

    async def stop_record(self):
        await asyncio.gather(
            *[process_stop(process) for process in self.record_processes]
        )

        logger.info(f"Stopped recording {self.room.name}")


class AudioMapper:
    """Класс последующей обработки видео"""

    @staticmethod
    async def map_video_and_sound(recorder: Recorder, source):
        proc = await run_cmd(
            FFMPEG_MAP_CMD_TEMPLATE.format(
                record_name=recorder.record_name,
                source_id=source.id,
            )
        )
        await proc.wait()


class Uploader:
    """Класс прослойка работы с гуглом"""

    GDRIVE = GoogleDrive()

    @staticmethod
    async def upload(recorder: Recorder, source, folder_id):
        file_path = f"{RECORDS_FOLDER}/{recorder.record_name}_{source.id}.mp4"
        return await Uploader.GDRIVE.upload(file_path, folder_id)

    @staticmethod
    async def prepare_folders(recorder: Recorder):
        gdrive = Uploader.GDRIVE

        room_folder_id = recorder.room.drive.split("/")[-1]
        record_date = str(recorder.record_dt.date())
        record_time = recorder.record_dt.strftime("%H:%M")

        folders = await gdrive.get_folder_by_name(record_date)
        for folder_id, folder_parent_ids in folders.items():
            if room_folder_id in folder_parent_ids:
                return await gdrive.create_folder(record_time, folder_id)

        date_folder_id = await gdrive.create_folder(record_date, room_folder_id)
        return await gdrive.create_folder(record_time, date_folder_id)


class Publisher:
    """Класс публикации записей"""

    @staticmethod
    async def send_to_erudite(recorder: Recorder, source, file_id: str):
        await send_record(
            room_name=recorder.room.name,
            date=str(recorder.record_dt.date()),
            start_time=str(recorder.record_dt.time()),
            end_time=str(
                (recorder.record_dt + timedelta(minutes=config.record_duration)).time()
            ),
            record_url=f"https://drive.google.com/file/d/{file_id}/preview",
            camera_ip=source.ip,
        )


class Cleaner:
    """Класс работы с видео на сервере"""

    @staticmethod
    def is_result_exist(recorder: Recorder, source):
        if os.path.exists(f"{RECORDS_FOLDER}/{recorder.record_name}_{source.id}.mp4"):
            return True

        return False

    @staticmethod
    def is_video_exist(recorder: Recorder, source):
        if os.path.exists(
            f"{RECORDS_FOLDER}/vid_{recorder.record_name}_{source.id}.mp4"
        ):
            return True

        return False

    @staticmethod
    def is_sound_exist(recorder: Recorder):
        if os.path.exists(f"{RECORDS_FOLDER}/sound_{recorder.record_name}.aac"):
            return True

        return False

    @staticmethod
    def clear_result(recorder: Recorder, source):
        remove_file(f"{RECORDS_FOLDER}/{recorder.record_name}_{source.id}.mp4")

    @staticmethod
    def clear_video(recorder: Recorder, source):
        remove_file(f"{RECORDS_FOLDER}/vid_{recorder.record_name}_{source.id}.mp4")

    @staticmethod
    def clear_sound(recorder: Recorder):
        remove_file(f"{RECORDS_FOLDER}/sound_{recorder.record_name}.aac")

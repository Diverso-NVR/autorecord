from datetime import datetime, timedelta
from pathlib import Path

import pytz

from autorecord.core.utils import run_cmd, remove_file
from autorecord.core.apis.drive_api import gdrive
from autorecord.core.apis.nvr_api import send_record
from autorecord.core.settings import config


RECORDS_FOLDER = str(Path.home()) + "/records"
FFMPEG_SOUND_RECORD_CMD_TEMPLATE = (
    "ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i {source_rtsp} "
    f"-y -c:a copy -vn -f mp4 {RECORDS_FOLDER}/sound_"
    "{record_name}.aac"
)
FFMPEG_VIDEO_RECORD_CMD_TEMPLATE = (
    "ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i {source_rtsp} "
    f"-y -c:v copy -an -f mp4 {RECORDS_FOLDER}/vid_"
    "{record_name}_{source_id}.mp4"
)
FFMPEG_MAP_CMD_TEMPLATE = (
    f"ffmpeg -i {RECORDS_FOLDER}/sound_"
    "{record_name}.aac "
    f"-i {RECORDS_FOLDER}/vid_"
    "{record_name}_{source_id}.mp4 "
    f"-y -shortest -c copy {RECORDS_FOLDER}"
    "{record_name}_{source_id}.mp4"
)


class Recorder:
    def __init__(self, room):
        self.room = room
        self.record_processes = []

        self.record_dt = datetime.now(tz=pytz.timezone("Europe/Moscow"))
        self.record_name = (
            self.record_dt.isoformat(timespec="minutes") + f"_{room.name}"
        )

    async def start_record(self):
        sound_source_rtsp = self.room.sound_source.rtsp
        sound_record_process = await run_cmd(
            FFMPEG_SOUND_RECORD_CMD_TEMPLATE.format(
                source_rtsp=sound_source_rtsp,
                record_name=self.record_name,
            )
        )
        self.record_processes.append(sound_record_process)

        for source in self.room.sources:
            video_record_process = await run_cmd(
                FFMPEG_VIDEO_RECORD_CMD_TEMPLATE.format(
                    source_rtsp=source.rtsp,
                    record_name=self.record_name,
                    source_id=source.id,
                )
            )
            self.record_processes.append(video_record_process)

    def stop_record(self):
        for process in self.record_processes:
            process.terminate()


class AudioMapper:
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
    @staticmethod
    async def upload(recorder: Recorder, source):

        file_path = f"{RECORDS_FOLDER}/{recorder.record_name}_{source.id}.mp4"
        folder_id = await Uploader.prepare_folders(recorder)
        try:
            return await gdrive.upload(file_path, folder_id)
        finally:
            Cleaner.clear_video(recorder, source)

    @staticmethod
    async def prepare_folders(recorder: Recorder):
        room_folder_id = recorder.room.drive.split("/")[-1]
        record_date = str(recorder.record_dt.date())
        record_time = str(recorder.record_dt.time())

        folders = await gdrive.get_folder_by_name(record_date)
        for folder_id, folder_parent_ids in folders.items():
            if room_folder_id in folder_parent_ids:
                return await gdrive.create_folder(record_time, folder_id)

        date_folder_id = await gdrive.create_folder(record_date, room_folder_id)
        return await gdrive.create_folder(record_time, date_folder_id)


class Publisher:
    @staticmethod
    async def send_to_erudite(recorder: Recorder, file_id: str):
        await send_record(
            room_name=recorder.room.name,
            date=str(recorder.record_dt.date()),
            start_time=str(recorder.record_dt.time()),
            end_time=str(
                (recorder.record_dt + timedelta(minutes=config.record_duration)).time()
            ),
            record_url=f"https://drive.google.com/file/d/{file_id}/preview",
        )


class Cleaner:
    @staticmethod
    def clear_sound(recorder: Recorder):
        remove_file(f"{RECORDS_FOLDER}/sound_{recorder.record_name}.aac")

    @staticmethod
    def clear_video(recorder: Recorder, source):
        remove_file(f"{RECORDS_FOLDER}/vid_{recorder.record_name}_{source.id}.mp4")

import datetime
import logging
import os
import queue
import signal
import subprocess
from threading import Thread, RLock
from datetime import datetime
from pathlib import Path

import pytz

from .apis.drive_api import upload, create_folder, get_folder_by_name
from .db.models import Room

HOME = str(Path.home())
logger = logging.getLogger('autorecord_logger')


class RecordHandler:
    def __init__(self):
        self.lock = RLock()
        self.upload_queue = queue.Queue()
        self.rooms = {}
        self.processes = {}
        self.record_names = {}
        self.video_ffmpeg_outputs = {}
        self.audio_ffmpeg_output = None

        Thread(target=self.worker).start()

    def worker(self):
        while True:
            file_name, folder_id = self.upload_queue.get()
            logger.info(
                f'Uploading video {file_name} to folder with id {folder_id}')
            upload(file_name, folder_id)
            logger.info(
                f'Uploaded video {file_name} to folder with id {folder_id}')
            self.upload_queue.task_done()

    def config(self, room_id: int, room_name: str) -> None:
        logger.info(f'Starting configuring room {room_name} with id {room_id}')

        self.rooms[room_id] = {"name": room_name}
        self.processes[room_id] = []

        current_date = datetime.now(tz=pytz.timezone('Europe/Moscow'))
        today = current_date.date()
        current_time = current_date.time()
        month = "0" + \
                str(today.month) if today.month < 10 else str(today.month)
        day = "0" + \
              str(today.day) if today.day < 10 else str(today.day)
        hour = "0" + \
               str(current_time.hour) if current_time.hour < 10 else str(
                   current_time.hour)
        minute = "0" + \
                 str(current_time.minute) if current_time.minute < 10 else str(
                     current_time.minute)

        self.record_names[room_id] = f"{today.year}-{month}-{day}_{hour}:{minute}_{self.rooms[room_id]['name']}_"

    def start_record(self, room: Room) -> None:
        logger.info(f'Starting recording in room {room.name}')

        self.config(room.id, room.name)
        room_id = room.id

        self.audio_ffmpeg_output = open(
            f"autorec_{room.name}_audio_log.txt", "a")

        self.audio_ffmpeg_output.write(
            f"\nCurrent DateTime: {datetime.now(tz=pytz.timezone('Europe/Moscow'))}\n")

        sound = subprocess.Popen("ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i rtsp://" +
                                 room.sound_source + " -y -c:a copy -vn -f mp4 " + HOME + "/vids/sound_"
                                 + self.record_names[room_id] + ".aac",
                                 shell=True,
                                 preexec_fn=os.setsid,
                                 stdout=self.audio_ffmpeg_output,
                                 stderr=self.audio_ffmpeg_output)
        self.processes[room_id].append(sound)

        for source in room.sources:
            if not source.rtsp:
                continue

            self.video_ffmpeg_outputs[source.ip] = open(
                f"autorec_{room.name}_{source.ip.replace('.', '_')}_video_log.txt", "a")

            self.video_ffmpeg_outputs[source.ip].write(
                f"\nCurrent DateTime: {datetime.now(tz=pytz.timezone('Europe/Moscow'))}\n")

            process = subprocess.Popen("ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i " +
                                       source.rtsp + " -y -c:v copy -an -f mp4 " + HOME + "/vids/vid_" +
                                       self.record_names[room_id] +
                                       source.ip.split('.')[-1] + ".mp4",
                                       shell=True,
                                       preexec_fn=os.setsid,
                                       stdout=self.video_ffmpeg_outputs[source.ip],
                                       stderr=self.video_ffmpeg_outputs[source.ip])
            self.processes[room_id].append(process)

    def kill_records(self, room: Room) -> bool:
        logger.info(f'Starting killing records in room {room.name}')

        try:
            for process in self.processes[room.id]:
                self.audio_ffmpeg_output.close()

                for video_output in self.video_ffmpeg_outputs.values():
                    video_output.close()

                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except OSError:
                    os.system("kill %s" % process.pid)

            del self.processes[room.id]

            Thread(target=self.prepare_records_and_upload, args=(room,)).start()

            logger.info(f'Successfully killed records in room {room.name}')
            return True
        except Exception:
            logger.error(
                f'Failed to kill records in room {room.name}', exc_info=True)
            return False

    def prepare_records_and_upload(self, room: Room) -> None:
        logger.info(f'Preparing and uploading records from room {room.name}')

        record_name = self.record_names[room.id]
        room_folder_id = room.drive.split('/')[-1]

        date, time = record_name.split('_')[0], record_name.split('_')[1]
        folders = get_folder_by_name(date)

        for folder_id, folder_parent_id in folders.items():
            if folder_parent_id == room_folder_id:
                time_folder_url = create_folder(time, folder_id)
                break
        else:
            date_folder_url = create_folder(date, room_folder_id)
            time_folder_url = create_folder(
                time, date_folder_url.split('/')[-1])

        Thread(target=self.sync_and_upload, args=(
            record_name, room.sources, time_folder_url.split('/')[-1])).start()

    def sync_and_upload(self, record_name: str, room_sources: list, folder_id: str) -> None:
        logger.info(
            f'Syncing video and audio and uploading record {record_name} to folder {folder_id}')

        res = ""
        if os.path.exists(f'{HOME}/vids/sound_{record_name}.aac'):
            for source in room_sources:
                self.add_sound(record_name, source.ip.split('.')[-1])
            try:
                os.remove(f'{HOME}/vids/sound_{record_name}.aac')
            except:
                logger.warning(
                    f'Failed to remove file {HOME}/vids/sound_{record_name}.aac')
        else:
            res = "vid_"

        for source in room_sources:
            try:
                file_name = res + record_name + \
                    source.ip.split('.')[-1] + ".mp4"

                self.upload_queue.put((HOME + "/vids/" + file_name, folder_id))

            except FileNotFoundError:
                pass
            except:
                logger.error(
                    f'Failed to upload file {file_name} to folder {folder_id}', exc_info=True)

    def add_sound(self, record_name: str, source_id: str) -> None:
        logger.info(f'Adding sound to record {record_name}{source_id}')

        with self.lock:
            add_sound_ffmpeg_output = open(
                f"autorec_sound_add_ffmpeg_log.txt", "a")

            add_sound_ffmpeg_output.write(
                f"\nCurrent DateTime: {datetime.now(tz=pytz.timezone('Europe/Moscow'))}\n")

            proc = subprocess.Popen(["ffmpeg", "-i", HOME + "/vids/sound_" + record_name + ".aac", "-i",
                                     HOME + "/vids/vid_" + record_name + source_id +
                                     ".mp4", "-y", "-shortest", "-c", "copy",
                                     HOME + "/vids/" + record_name + source_id + ".mp4"],
                                    shell=False,
                                    stdout=add_sound_ffmpeg_output,
                                    stderr=add_sound_ffmpeg_output)
            proc.wait()
            add_sound_ffmpeg_output.close()
            try:
                os.remove(f'{HOME}/vids/vid_{record_name}{source_id}.mp4')
            except:
                logger.warning(
                    f'Failed to remove file {HOME}/vids/vid_{record_name}{source_id}.mp4')

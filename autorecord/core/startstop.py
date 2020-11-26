import datetime
import logging
import os
import signal
import subprocess
from threading import Thread
from datetime import datetime
from pathlib import Path

import concurrent.futures

import pytz

from .apis.drive_api import upload, create_folder, get_folder_by_name
from .db.models import Room

HOME = str(Path.home())
logger = logging.getLogger('autorecord_logger')


class RecordHandler:
    def __init__(self):
        self.processes = {}
        self.record_names = {}
        self.previous_record_names = {}
        self.video_ffmpeg_outputs = {}
        self.audio_ffmpeg_output = None

    def remove_file(self, filename: str) -> None:
        try:
            os.remove(filename)
        except FileNotFoundError:
            logger.warning(f'Failed to remove file {filename}')
        except:
            logger.error(
                f'Failed to remove file {filename}', exc_info=True)

    def start_record(self, room: Room) -> None:
        logger.info(f'Starting recording in room {room.name}')

        self.config(room)

        self.audio_ffmpeg_output = open(
            f"autorec_{room.name}_audio_log.txt", "a")

        self.audio_ffmpeg_output.write(
            f"\nCurrent DateTime: {datetime.now(tz=pytz.timezone('Europe/Moscow'))}\n")
        self.audio_ffmpeg_output.flush()

        sound = subprocess.Popen("ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i rtsp://" +
                                 room.sound_source + " -y -c:a copy -vn -f mp4 " + HOME + "/vids/sound_"
                                 + self.record_names[room.id] + ".aac",
                                 shell=True,
                                 preexec_fn=os.setsid,
                                 stdout=self.audio_ffmpeg_output,
                                 stderr=self.audio_ffmpeg_output)
        self.processes[room.id].append(sound)

        for source in room.sources:
            if not source.rtsp:
                continue

            self.video_ffmpeg_outputs[source.ip] = open(
                f"autorec_{room.name}_{source.ip.replace('.', '_')}_video_log.txt", "a")

            self.video_ffmpeg_outputs[source.ip].write(
                f"\nCurrent DateTime: {datetime.now(tz=pytz.timezone('Europe/Moscow'))}\n")
            self.video_ffmpeg_outputs[source.ip].flush()

            process = subprocess.Popen("ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i " +
                                       source.rtsp + " -y -c:v copy -an -f mp4 " + HOME + "/vids/vid_" +
                                       self.record_names[room.id] +
                                       source.ip.split('.')[-1] + ".mp4",
                                       shell=True,
                                       preexec_fn=os.setsid,
                                       stdout=self.video_ffmpeg_outputs[source.ip],
                                       stderr=self.video_ffmpeg_outputs[source.ip])
            self.processes[room.id].append(process)

    def config(self, room: Room) -> None:
        logger.info(f'Starting configuring room {room.name} with id {room.id}')

        self.processes[room.id] = []

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

        self.record_names[room.id] = f"{today.year}-{month}-{day}_{hour}:{minute}_{room.name}_"

    def stop_records(self, rooms):
        if not self.processes:
            return

        for room in rooms:
            if not self.kill_room_records(room):
                rooms.remove(room)

        self.previous_record_names = dict(self.record_names)
        self.record_names = {}
        self.processes = {}

        Thread(target=self.start_tasks, args=(rooms,)).start()

    def kill_room_records(self, room: Room) -> bool:
        logger.info(f'Starting killing records in room {room.name}')
        if not self.processes.get(room.id):
            return False

        try:
            for process in self.processes[room.id]:
                self.audio_ffmpeg_output.close()

                for video_output in self.video_ffmpeg_outputs.values():
                    video_output.close()

                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except OSError:
                    os.system("kill %s" % process.pid)

            logger.info(f'Successfully killed records in room {room.name}')
            return True
        except Exception:
            logger.error(
                f'Failed to kill records in room {room.name}', exc_info=True)
            return False

    def start_tasks(self, rooms):
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(rooms)) as executor:
            futures = {executor.submit(self.prepare_records_and_upload, room): room.name for room in rooms}

            for future in concurrent.futures.as_completed(futures):
                    room_name = futures[future]
                    logger.info(f"{room_name} is done")

    def prepare_records_and_upload(self, room: Room) -> None:
        logger.info(f'Preparing and uploading records from room {room.name}')

        record_name = self.previous_record_names.get(room.id)

        if not record_name:
            return

        if not os.path.exists(f'{HOME}/vids/sound_{record_name}.aac'):
            for source in room.sources:
                source_id = source.ip.split('.')[-1]
                self.remove_file(
                    f'{HOME}/vids/vid_{record_name}{source_id}.mp4')
            return

        room_folder_id = room.drive.split('/')[-1]
        record_info = record_name.split('_')
        date, time, _, _ = record_info
        folders = get_folder_by_name(date)

        for folder_id, folder_parent_ids in folders.items():
            if room_folder_id in folder_parent_ids:
                time_folder_url = create_folder(time, folder_id)
                break
        else:
            date_folder_url = create_folder(date, room_folder_id)
            time_folder_url = create_folder(
                time, date_folder_url.split('/')[-1])

        self.sync_and_upload(
            record_name, room.sources, time_folder_url.split('/')[-1])

    def sync_and_upload(self, record_name: str, room_sources: list, folder_id: str) -> None:
        logger.info(
            f'Syncing video and audio and uploading record {record_name} to folder {folder_id}')

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(room_sources)) as executor:
                futures = {executor.submit(self.add_sound, record_name, source.ip.split('.')[-1]): (record_name, source, folder_id) for source in room_sources}

                for future in concurrent.futures.as_completed(futures):
                    record_name, source, folder_id = futures[future]
                    executor.submit(self.uploader, record_name, source, folder_id)
        finally:
            self.remove_file(f'{HOME}/vids/sound_{record_name}.aac')

    def add_sound(self, record_name: str, source_id: str) -> None:
        logger.info(f'Adding sound to record {record_name}{source_id}')

        add_sound_ffmpeg_output = open(
            f"autorec_sound_add_ffmpeg_log.txt", "a")

        add_sound_ffmpeg_output.write(
            f"\nCurrent DateTime: {datetime.now(tz=pytz.timezone('Europe/Moscow'))}\n")
        add_sound_ffmpeg_output.flush()

        try:
            proc = subprocess.Popen(["ffmpeg", "-i", HOME + "/vids/sound_" + record_name + ".aac", "-i",
                                     HOME + "/vids/vid_" + record_name + source_id +
                                     ".mp4", "-y", "-shortest", "-c", "copy",
                                     HOME + "/vids/" + record_name + source_id + ".mp4"],
                                    shell=False,
                                    stdout=add_sound_ffmpeg_output,
                                    stderr=add_sound_ffmpeg_output)
            proc.wait()
            add_sound_ffmpeg_output.close()
        finally:
            self.remove_file(f'{HOME}/vids/vid_{record_name}{source_id}.mp4')

    def uploader(self, record_name, source, folder_id):
        try:
            file_name = record_name + \
                source.ip.split('.')[-1] + ".mp4"
            logger.info(
                f'Uploading {HOME}/vids/{file_name}')

            upload(f'{HOME}/vids/{file_name}', folder_id)
        except FileNotFoundError:
            pass
        except:
            logger.error(
                f'Failed to upload file {file_name}', exc_info=True)
        finally:
            self.remove_file(f'{HOME}/vids/{file_name}')

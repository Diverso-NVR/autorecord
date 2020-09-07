import datetime
import os
import signal
import subprocess
from pathlib import Path
from threading import RLock, Thread
import pytz

from .apis.drive_api import upload, create_folder, get_folder_by_name
from .db.models import Room

HOME = str(Path.home())


class RecordHandler:
    lock = RLock()
    rooms = {}
    processes = {}
    record_names = {}

    def config(self, room_id: int, name: str) -> None:
        self.rooms[room_id] = {"name": name}
        self.processes[room_id] = []

        current_date = datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))
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
        self.config(room.id, room.name)
        room_id = room.id

        sound = subprocess.Popen("ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i rtsp://" +
                                 room.sound_source + " -y -c:a copy -vn -f mp4 " + HOME + "/vids/sound_"
                                 + self.record_names[room_id] + ".aac",
                                 shell=True,
                                 preexec_fn=os.setsid)
        self.processes[room_id].append(sound)

        for source in room.sources:
            if not source.rtsp:
                continue

            process = subprocess.Popen("ffmpeg -use_wallclock_as_timestamps true -rtsp_transport tcp -i " +
                                       source.rtsp + " -y -c:v copy -an -f mp4 " + HOME + "/vids/vid_" +
                                       self.record_names[room_id] +
                                       source.ip.split('.')[-1] + ".mp4",
                                       shell=True,
                                       preexec_fn=os.setsid)
            self.processes[room_id].append(process)

    def kill_records(self, room: Room) -> bool:
        try:
            for process in self.processes[room.id]:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except OSError:
                    os.system("kill %s" % process.pid)

            del self.processes[room.id]

            Thread(target=self.prepare_records_and_upload, args=(room,)).start()

            return True
        except KeyError:
            return False

    def prepare_records_and_upload(self, room: Room) -> None:
        with self.lock:
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

            self.sync_and_upload(record_name, room.sources,
                                 time_folder_url.split('/')[-1])

    def sync_and_upload(self, record_name: str, room_sources: list, folder_id: str) -> None:
        res = ""
        if os.path.exists(f'{HOME}/vids/sound_{record_name}.aac'):
            for source in room_sources:
                self.add_sound(record_name,
                               source.ip.split('.')[-1])
            os.remove(f'{HOME}/vids/sound_{record_name}.aac')
        else:
            res = "vid_"

        for source in room_sources:
            try:
                file_name = res + record_name + \
                    source.ip.split('.')[-1] + ".mp4"

                upload(HOME + "/vids/" + file_name,
                       folder_id)

                os.remove(HOME + "/vids/" + file_name)
            except Exception as e:
                print(e)

    def add_sound(self, record_name: str, source_id: str) -> None:
        proc = subprocess.Popen(["ffmpeg", "-i", HOME + "/vids/sound_" + record_name + ".aac", "-i",
                                 HOME + "/vids/vid_" + record_name + source_id +
                                 ".mp4", "-y", "-shortest", "-c", "copy",
                                 HOME + "/vids/" + record_name + source_id + ".mp4"], shell=False)
        proc.wait()
        try:
            os.remove(f'{HOME}/vids/vid_{record_name}{source_id}.mp4')
        except:
            pass

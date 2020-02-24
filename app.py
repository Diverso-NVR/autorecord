import time

import schedule

from models import Room, Session
from startstop import RecordHandler


class DaemonApp:
    rooms = None
    record_handler = RecordHandler()

    def __init__(self):
        schedule.every().hour.at(":00").do(self.start_new_recording)
        schedule.every().hour.at(":30").do(self.start_new_recording)

    def start_new_recording(self):
        session = Session()
        self.rooms = session.query(Room).all()
        session.close()

        for room in self.rooms:
            self.record_handler.kill_records(room)
            self.record_handler.start_record(room)

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)


if __name__ == "__main__":
    daemon_app = DaemonApp()
    daemon_app.run()

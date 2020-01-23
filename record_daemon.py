import schedule
import time
import os
from multiprocessing import Pool
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Room
from startstop import RecordHandler


engine = create_engine(os.environ.get('SQLALCHEMY_DATABASE_URI'))
Session = sessionmaker(bind=engine)


class DaemonApp():
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


daemon_app = DaemonApp()
# daemon_app.run()
daemon_app.start_new_recording()

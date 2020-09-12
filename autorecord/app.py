import logging
import time

import schedule

from core.db.models import Room, Session
from core.startstop import RecordHandler


class DaemonApp:
    rooms = None
    record_handler = RecordHandler()
    logger = logging.getLogger('autorecord_logger')

    def __init__(self):
        self.logger.info('Class \"DaemonApp\" instantiated')

        schedule.every().hour.at(":00").do(self.start_new_recording)
        schedule.every().hour.at(":30").do(self.start_new_recording)

    def start_new_recording(self):
        self.logger.info('Starting recording')

        session = Session()
        self.rooms = session.query(Room).all()
        session.close()

        self.record_handler.stop_records(self.rooms)
        for room in self.rooms:
            if not room.sources:
                self.logger.info(
                    f'Room {room.name} has no sources, skipping room')
                continue

            try:
                self.record_handler.start_record(room)
            except Exception:
                self.logger.error(
                    f'Unable to kill/start records in room {room.name}', exc_info=True)

    def run(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    @staticmethod
    def create_logger(mode='INFO'):
        logs = {'INFO': logging.INFO,
                'DEBUG': logging.DEBUG}

        logger = logging.getLogger('autorecord_logger')
        logger.setLevel(logs[mode])

        handler = logging.StreamHandler()
        handler.setLevel(logs[mode])

        formatter = logging.Formatter(
            '%(levelname)-8s  %(asctime)s    %(message)s',
            datefmt='%d-%m-%Y %I:%M:%S %p')

        handler.setFormatter(formatter)

        logger.addHandler(handler)


if __name__ == "__main__":
    DaemonApp.create_logger()

    daemon_app = DaemonApp()
    daemon_app.start_new_recording()
    daemon_app.run()

import logging
import time
import os
from threading import Thread

import schedule

from core.db.models import Room, Session
from core.startstop import RecordHandler

ROOM_NAME = os.environ.get('ROOM_NAME')


class DaemonApp:
    record_handler = RecordHandler()
    logger = logging.getLogger('autorecord_logger')

    def __init__(self):
        self.logger.info('Class \"DaemonApp\" instantiated')

        schedule.every(1).minutes.do(self.start_new_recording) # 2 min records
        # schedule.every(30).minutes.do(self.start_new_recording) # 30 min records

        # # Create jobs from monday to saturday to record during classes time
        # for weekday in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']:
        #     eval(
        #         f'schedule.every().{weekday}.at("09:30").do(self.start_new_recording)')

        #     for hour in range(10, 21):
        #         eval(
        #             f'schedule.every().{weekday}.at("{hour}:00").do(self.start_new_recording)')
        #         eval(
        #             f'schedule.every().{weekday}.at("{hour}:30").do(self.start_new_recording)')

        #     eval(
        #         f'schedule.every().{weekday}.at("21:00").do(self.stop_records)')

    def start_new_recording(self):
        self.logger.info('Starting recording')

        session = Session()
        rooms = session.query(Room).filter(Room.name == ROOM_NAME).all()
        session.close()

        self.record_handler.stop_records(rooms)
        for room in rooms:
            if not room.sources:
                self.logger.info(
                    f'Room {room.name} has no sources, skipping room')
                continue

            Thread(target=self.record_handler.start_record, args=(room,)).start()

    def stop_records(self):
        self.logger.info('Stoping daemon')
        session = Session()
        rooms = session.query(Room).all()
        session.close()

        self.record_handler.stop_records(rooms)

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

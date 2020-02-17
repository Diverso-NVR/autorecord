import os

from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()
engine = create_engine(os.environ.get('SQLALCHEMY_DATABASE_URI'))
Session = sessionmaker(bind=engine)


class Room(Base):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    tracking_state = Column(Boolean, default=False)

    sound_source = Column(String(100), default='0')
    main_source = Column(String(100), default='0')
    tracking_source = Column(String(100), default='0')
    screen_source = Column(String(100), default='0')

    sources = relationship('Source', backref='room', lazy=False)
    drive = Column(String(200))
    calendar = Column(String(200))

    def to_dict(self):
        return dict(id=self.id,
                    name=self.name,
                    tracking_state=self.tracking_state,
                    sound_source=self.sound_source,
                    main_source=self.main_source,
                    tracking_source=self.tracking_source,
                    screen_source=self.screen_source,
                    sources=[source.to_dict() for source in self.sources],
                    drive=self.drive,
                    calendar=self.calendar)


class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)
    ip = Column(String(200), default='0')
    name = Column(String(100), default='источник')
    room_id = Column(Integer, ForeignKey('rooms.id'))

    def __init__(self, **kwargs):
        self.ip = kwargs.get('ip')
        self.name = kwargs.get('name')
        self.room_id = kwargs.get('room_id')

    def to_dict(self):
        return dict(id=self.id,
                    ip=self.ip,
                    name=self.name,
                    room_id=self.room_id)

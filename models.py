from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Room(Base):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    free = Column(Boolean, default=True)
    tracking_state = Column(Boolean, default=False)
    timestamp = Column(Integer, default=0)
    chosen_sound = Column(String(100), default='enc')
    sources = relationship('Source', backref='room', lazy=False)
    drive = Column(String(200))
    calendar = Column(String(200))

    def to_dict(self):
        return dict(id=self.id,
                    name=self.name,
                    free=self.free,
                    tracking_state=self.tracking_state,
                    timestamp=self.timestamp,
                    chosen_sound=self.chosen_sound,
                    sources=[source.to_dict() for source in self.sources],
                    drive=self.drive,
                    calendar=self.calendar)


class Source(Base):
    __tablename__ = 'sources'

    id = Column(Integer, primary_key=True)
    ip = Column(String(200))
    name = Column(String(100))
    sound = Column(String(100))
    tracking = Column(Boolean, default=False)
    main_cam = Column(Boolean, default=False)
    room_id = Column(Integer, ForeignKey('rooms.id'))

    def __init__(self, **kwargs):
        self.ip = kwargs.get('ip', "0.0.0.0")
        self.name = kwargs.get('name', 'камера')
        self.sound = kwargs.get('sound')
        self.tracking = kwargs.get('tracking', False)
        self.main_cam = kwargs.get('main_cam', False)
        self.room_id = kwargs.get('room_id')

    def to_dict(self):
        return dict(id=self.id,
                    ip=self.ip,
                    name=self.name,
                    sound=self.sound,
                    tracking=self.tracking,
                    main_cam=self.main_cam,
                    room_id=self.room_id)

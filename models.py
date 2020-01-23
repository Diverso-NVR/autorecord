from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Room(Base):
    __tablename__ = 'rooms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    free = db.Column(db.Boolean, default=True)
    tracking_state = db.Column(db.Boolean, default=False)

    sound_source = db.Column(db.String(100), default='0')
    main_source = db.Column(db.String(100), default='0')
    tracking_source = db.Column(db.String(100), default='0')
    screen_source = db.Column(db.String(100), default='0')

    sources = db.relationship('Source', backref='room', lazy=False)
    drive = db.Column(db.String(200))
    calendar = db.Column(db.String(200))

    def to_dict(self):
        return dict(id=self.id,
                    name=self.name,
                    free=self.free,
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

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(200), default='0')
    name = db.Column(db.String(100), default='источник')
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'))

    def __init__(self, **kwargs):
        self.ip = kwargs.get('ip')
        self.name = kwargs.get('name')
        self.room_id = kwargs.get('room_id')

    def to_dict(self):
        return dict(id=self.id,
                    ip=self.ip,
                    name=self.name,
                    room_id=self.room_id)

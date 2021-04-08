import os

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import func
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()
engine = create_engine(os.environ.get("SQLALCHEMY_DATABASE_URI"))
Session = sessionmaker(bind=engine)


class IdMixin:
    id = Column(Integer, primary_key=True)


class TimeMixin:
    created_at = Column(DateTime, default=func.now())
    modified_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CommonMixin(IdMixin, TimeMixin):
    pass


class Room(Base, CommonMixin):
    __tablename__ = "rooms"

    name = Column(String(100), nullable=False)
    ruz_id = Column(Integer)

    drive = Column(String(200))
    calendar = Column(String(200))

    sound_source = Column(String(100))
    main_source = Column(String(100))
    screen_source = Column(String(100))

    auto_control = Column(Boolean, default=True)

    sources = relationship("Source", backref="room", lazy=False)

    organization_id = Column(Integer, ForeignKey("organizations.id"))


class Source(Base, CommonMixin):
    __tablename__ = "sources"

    name = Column(String(100), default="источник")
    ip = Column(String(200))
    port = Column(String(200))
    rtsp = Column(String(200), default="no")
    audio = Column(String(200))
    merge = Column(String(200))
    room_id = Column(Integer, ForeignKey("rooms.id"))
    external_id = Column(String(200))

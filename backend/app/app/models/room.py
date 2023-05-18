
from sqlalchemy import Boolean, Column, Integer, String

from app.db.base_class import Base


class Room(Base):
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    video_url = Column(String, nullable=True)


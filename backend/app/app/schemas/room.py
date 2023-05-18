from typing import Optional

from pydantic import BaseModel


# Shared properties
class RoomBase(BaseModel):
    name: str
    video_url: str


# Properties to receive on Room creation
class RoomCreate(RoomBase):
    name: str
    video_url: str


# Properties to receive on Room update
class RoomUpdate(RoomBase):
    pass


# Properties shared by models stored in DB
class RoomInDBBase(RoomBase):
    id: int
    name: str
    video_url: str

    class Config:
        orm_mode = True


# Properties to return to client
class Room(RoomInDBBase):
    pass


# Properties properties stored in DB
class RoomInDB(RoomInDBBase):
    pass

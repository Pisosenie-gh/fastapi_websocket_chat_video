from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, FastAPI, WebSocketDisconnect
from sqlalchemy.orm import Session
import websockets
from pydantic import BaseModel
from app import crud, models, schemas
from app.api import deps
import json


class WebSocketMessage(BaseModel):
    action: str
    room_name: str
    sender: str
    content: str


router = APIRouter()
manager = deps.ConnectionManager()


@router.post("/", response_model=schemas.Room)
def create_room(
        *,
        db: Session = Depends(deps.get_db),
        room_in: schemas.RoomCreate,
) -> Any:
    """
    Create new room.
    """
    room = crud.room.create(db=db, obj_in=room_in)
    return room


@router.get("/", response_model=List[schemas.Room])
def read_rooms(
        db: Session = Depends(deps.get_db),
        skip: int = 0,
        limit: int = 100,
) -> Any:
    """
    Retrieve Rooms.
    """
    rooms = crud.room.get_multi(db, skip=skip, limit=limit)

    return rooms



async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        message = WebSocketMessage.parse_raw(data)
        action = message.action

        if action == "join_room":
            room_name = message.room_name
            await join_room(websocket, room_name)

        elif action == "send_message":
            room_name = message.room_name
            sender = message.sender
            content = message.content
            await save_and_broadcast_message(room_name, sender, content)



async def join_room(websocket: WebSocket, room_name: str):
    await websocket.send_json({"action": "join_room", "room_name": room_name})
    await broadcast_chat_history(room_name)


async def save_and_broadcast_message(room_name: str, sender: str, content: str):
    message = Message(room_id=get_room_id(room_name), sender=sender, content=content)
    session = SessionLocal()
    session.add(message)
    session.commit()
    session.refresh(message)

    await broadcast_message(room_name, {
        "action": "receive_message",
        "sender": message.sender,
        "content": message.content,
        "created_at": message.created_at.isoformat()
    })


# Отправка истории чата всем подключенным клиентам в комнате
async def broadcast_chat_history(room_name: str):
    room_id = get_room_id(room_name)
    session = SessionLocal()
    messages = session.query(Message).filter_by(room_id=room_id).order_by(Message.created_at).all()

    chat_history = [{
        "action": "receive_message",
        "sender": message.sender,
        "content": message.content,
        "created_at": message.created_at.isoformat()
    } for message in messages]

    await broadcast_message(room_name, chat_history)


async def broadcast_message(room_name: str, message: dict):
    room_id = get_room_id(room_name)
    for connection in connections[room_id]:
        await connection.send_json(message)


# Получение идентификатора комнаты по ее имени
def get_room_id(room_name: str) -> int:
    session = SessionLocal()
    room = session.query(Room).filter_by(room_name=room_name).first()
    if not room:
        room = Room(room_name=room_name)
        session.add(room)
        session.commit()
        session.refresh(room)
    return room.id


# Словарь для хранения подключений WebSocket в комнатах
connections = {}


# Маршрут для подключения WebSocket
@router.websocket_route("/ws")
async def websocket_route(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        message = WebSocketMessage.parse_raw(data)
        action = message.action

        if action == "join_room":
            room_name = message.room_name
            if room_name not in connections:
                connections[room_name] = []
            connections[room_name].append(websocket)
            await join_room(websocket, room_name)
        elif action == "send_message":
            room_name = message.room_name
            sender = message.sender
            content = message.content
            await save_and_broadcast_message(room_name, sender, content)



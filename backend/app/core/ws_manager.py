import logging
from typing import Dict

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect
import redis.asyncio as aioredis

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class WSManager:
    def __init__(self):
        self.active_connections: Dict[int, WebSocket] = {}
        self.redis: aioredis.Redis | None = None

    async def initialize(self):
        if self.redis is None:
            self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: int):
        self.active_connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, message: dict):
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_json(message)
            except (WebSocketDisconnect, RuntimeError):
                logger.debug("WebSocket send failed for user_id=%d, disconnecting", user_id)
                self.disconnect(user_id)

    async def broadcast(self, message: dict, user_ids: list[int] = None):
        for uid, ws in list(self.active_connections.items()):
            if user_ids is None or uid in user_ids:
                try:
                    await ws.send_json(message)
                except (WebSocketDisconnect, RuntimeError):
                    logger.debug("WebSocket broadcast send failed for user_id=%d, disconnecting", uid)
                    self.disconnect(uid)


ws_manager = WSManager()

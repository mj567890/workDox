import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import jwt

from app.core.ws_manager import ws_manager
from app.core.security import decode_access_token

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...),
):
    # Verify token
    try:
        payload = decode_access_token(token)
        if payload.get("sub") != str(user_id):
            await websocket.close(code=4003)
            return
    except jwt.PyJWTError:
        logger.warning("WebSocket JWT validation failed for user_id=%d", user_id)
        await websocket.close(code=4001)
        return

    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive, receive ping/pong
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)

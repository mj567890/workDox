from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.ws_manager import ws_manager
from app.core.security import decode_token

router = APIRouter()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: int,
    token: str = Query(...),
):
    # Verify token
    try:
        payload = decode_token(token)
        if payload.get("sub") != str(user_id):
            await websocket.close(code=4003)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            # Keep connection alive, receive ping/pong
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(user_id)

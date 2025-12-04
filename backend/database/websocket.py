import json
import asyncio
import redis.asyncio as redis
from fastapi import WebSocket, WebSocketDisconnect
from .config import REDIS_URL


class ConnectionManager:
    def __init__(self):
        self.active: dict[str, WebSocket] = {}
        self.redis = redis.from_url(REDIS_URL, decode_responses=True)

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active[user_id] = websocket
        # subscribe to Redis channel
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"user:{user_id}")
        self.redis_loop = asyncio.create_task(
            self._redis_listener(pubsub, websocket))

    async def disconnect(self, user_id: str):
        ws = self.active.pop(user_id, None)
        if ws:
            try:
                await ws.close()
            except:
                pass
        if hasattr(self, 'redis_loop'):
            self.redis_loop.cancel()

    async def _redis_listener(self, pubsub, websocket: WebSocket):
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                await websocket.send_text(msg["data"])

    async def send_personal(self, message: str, user_id: str):
        if user_id in self.active:
            await self.active[user_id].send_text(message)
        # also publish to Redis so any worker can push
        await self.redis.publish(f"user:{user_id}", message)


manager = ConnectionManager()

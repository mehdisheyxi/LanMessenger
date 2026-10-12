
from pathlib import Path
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="LAN Messenger")
CHAT_PASSWORD = "12345678"
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")

async def home():
    return FileResponse(STATIC_DIR / "index.html")


class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):


        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        disconnected = []

        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except (RuntimeError, OSError):
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()




@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()

    try:
        login_data = await websocket.receive_text()

        try:
            data = json.loads(login_data)
        except json.JSONDecodeError:
            await websocket.close(code=1008)
            return

        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))

        if not username or len(username) > 30:
            await websocket.close(code=1008)
            return

        if password != CHAT_PASSWORD:
            await websocket.close(code=1008)
            return

        manager.active_connections.add(websocket)

        await websocket.send_json({"type": "login_success"})

        while True:
            raw_message = await websocket.receive_text()

            try:
                data = json.loads(raw_message)
            except json.JSONDecodeError:
                continue

            message = str(data.get("message", "")).strip()

            if not message or len(message) > 1000:
                continue

            await manager.broadcast({
                "username": username,
                "message": message,
            })

    except WebSocketDisconnect:
        manager.disconnect(websocket)
#python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

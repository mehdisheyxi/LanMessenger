



'''
HTTP	دریافت صفحات وب و تبادل اطلاعات وب
HTTPS	ارتباط HTTP رمزنگاری‌شده با TLS
WebSocket	ارتباط دوطرفه و ماندگار بین کلاینت و سرور
DNS	تبدیل نام‌هایی مثل google.com به آدرس IP
SMTP	ارسال ایمیل
FTP	انتقال فایل
SSH	دسترسی و مدیریت امن سیستم از راه دور
'''
from pathlib import Path
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime


#ساخت برنامه و تنظیمات اولیه
app = FastAPI(title="LAN Messenger")
CHAT_PASSWORD = "12345678"
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


#معرفی فایل‌های استاتیک به FastAPI
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


#پاسخ به درخواست HTTP برای صفحه‌ی اصلی
@app.get("/")
async def home():
    return FileResponse(STATIC_DIR / "index.html")

#مدیریت اتصال کاربران
#نگهداری اتصال‌های فعال و پخش پیام‌ها
class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

#این تابع برای افزودن یک اتصال به مجموعه است
    async def connect(self, websocket: WebSocket):
        self.active_connections.add(websocket)


#این تابع اتصال رو از مجموعه حذف می‌کنه
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    def log_connections(self, event, websocket):#این تابع IP و پورت دستگاه رو می‌گیره و تعداد اتصال‌های فعال رو چاپ می‌کنه
        client = websocket.client

        ip = client.host if client else "Unknown"
        port = client.port if client else 0
        time = datetime.now().strftime("%H:%M:%S")

        print(
            f"[{time}] {event} | "
            f"IP: {ip}:{port} | "
            f"Online: {len(self.active_connections)}"
        )

    # ارسال بع همه
    async def broadcast(self, message: dict):
        disconnected = []


        #حلقه‌ی ارسال به اتصال‌ها
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except (RuntimeError, OSError):
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()



#تعریف نقطه‌ی اتصال WebSocket
@app.websocket("/ws")
async def chat(websocket: WebSocket):
    #پذیرفتن اتصال WebSocket
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

        await manager.connect(websocket)

        manager.log_connections("CONNECTED", websocket)

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
        manager.log_connections("DISCONNECTED", websocket)
#python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info
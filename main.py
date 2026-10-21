



'''
HTTP	دریافت صفحات وب و تبادل اطلاعات وب
HTTPS	ارتباط HTTP رمزنگاری‌شده با TLS
WebSocket	ارتباط دوطرفه و ماندگار بین کلاینت و سرور
DNS	تبدیل نام‌هایی مثل google.com به آدرس IP
SMTP	ارسال ایمیل
FTP	انتقال فایل
SSH	دسترسی و مدیریت امن سیستم از راه دور
'''
from fastapi import Form, Request
from fastapi.responses import RedirectResponse
from auth import register_user, verify_user
from pathlib import Path
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from database import init_db
from starlette.middleware.sessions import SessionMiddleware


#ساخت برنامه و تنظیمات اولیه
app = FastAPI(title="LAN Messenger")

app.add_middleware(
    SessionMiddleware,
    secret_key="CHANGE_THIS_TO_A_LONG_RANDOM_SECRET",
    session_cookie="lanmessenger_session",
    same_site="lax",
    https_only=False,
    max_age=60 * 60 * 8,
)

@app.on_event("startup")
def startup():
    init_db()



BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


#معرفی فایل‌های استاتیک به FastAPI
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


#پاسخ به درخواست HTTP برای صفحه‌ی اصلی

@app.get("/")
async def home(request: Request):
    username = request.session.get("username")

    if not username:
        return RedirectResponse(url="/login", status_code=303)

    return FileResponse(STATIC_DIR / "index.html")



@app.get("/login")
async def login_page():
    return FileResponse(STATIC_DIR / "login.html")


@app.get("/register")
async def register_page():
    return FileResponse(STATIC_DIR / "register.html")



@app.post("/register")
async def register(
    username: str = Form(...),
    password: str = Form(...),
):
    success = register_user(username, password)

    if not success:
        return {
            "success": False,
            "message": "نام کاربری تکراری است یا اطلاعات واردشده معتبر نیست."
        }

    return RedirectResponse(url="/login", status_code=303)




@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if not verify_user(username, password):
        return RedirectResponse(
            url="/login?error=invalid",
            status_code=303,
        )

    request.session.clear()
    request.session["username"] = username.strip()

    return RedirectResponse(url="/", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()

    return RedirectResponse(url="/login", status_code=303)

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
    # دریافت نام کاربر از نشست
    session = websocket.scope.get("session", {})
    username = session.get("username")

    # جلوگیری از اتصال کاربران واردنشده
    if not username:
        await websocket.close(code=1008)
        return

    # پذیرش اتصال کاربر احراز هویت‌شده
    await websocket.accept()
    await manager.connect(websocket)
    manager.log_connections("CONNECTED", websocket)

    try:
        await websocket.send_json({
            "type": "login_success",
            "username": username,
        })

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
        pass

    finally:
        manager.disconnect(websocket)
        manager.log_connections("DISCONNECTED", websocket)

#python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info
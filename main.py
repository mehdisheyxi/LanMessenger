
"""
HTTP       دریافت صفحات وب و تبادل اطلاعات وب
HTTPS      ارتباط HTTP رمزنگاری‌شده با TLS
WebSocket  ارتباط دوطرفه و ماندگار بین کلاینت و سرور
DNS        تبدیل نام دامنه به آدرس IP
SMTP       ارسال ایمیل
FTP        انتقال فایل
SSH        دسترسی و مدیریت امن سیستم از راه دور
"""

import json
from datetime import datetime
from pathlib import Path

from fastapi import (
    FastAPI,
    Form,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from auth import (
    register_user,
    verify_user,
    get_user,
    list_users,
    change_user_password,
    delete_user,
)
from database import init_db


# ==================================================
# تنظیمات اولیه برنامه
# ==================================================

app = FastAPI(title="LAN Messenger")

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

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


app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)


# ==================================================
# ورود، ثبت‌نام و خروج کاربران
# ==================================================

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
            "message": "نام کاربری تکراری است یا اطلاعات واردشده معتبر نیست.",
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

    user = get_user(username)

    if not user or not user["is_active"]:
        return RedirectResponse(
            url="/login?error=invalid",
            status_code=303,
        )

    request.session.clear()
    request.session["username"] = user["username"]

    return RedirectResponse(url="/", status_code=303)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()

    return RedirectResponse(url="/login", status_code=303)


# ==================================================
# احراز هویت و صفحات مدیریت
# ==================================================

def require_admin(request: Request):
    username = request.session.get("username")

    if not username:
        return None

    user = get_user(username)

    if user and user["role"] == "admin" and user["is_active"]:
        return user

    return None


@app.get("/admin/login")
async def admin_login_page(request: Request):
    username = request.session.get("username")

    if username:
        user = get_user(username)

        if user and user["role"] == "admin" and user["is_active"]:
            return RedirectResponse(url="/admin", status_code=303)

    return FileResponse(STATIC_DIR / "admin_login.html")


@app.post("/admin/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if not verify_user(username, password):
        return RedirectResponse(
            url="/admin/login?error=invalid",
            status_code=303,
        )

    user = get_user(username)

    if not user or user["role"] != "admin" or not user["is_active"]:
        return RedirectResponse(
            url="/admin/login?error=invalid",
            status_code=303,
        )

    request.session.clear()
    request.session["username"] = user["username"]

    return RedirectResponse(url="/admin", status_code=303)


@app.get("/admin")
@app.get("/admin/users")
async def admin_dashboard(request: Request):
    if not require_admin(request):
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    return FileResponse(STATIC_DIR / "admin.html")


# ==================================================
# مدیریت حساب‌های کاربران
# ==================================================

@app.post("/admin/users/create")
async def admin_create_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if not require_admin(request):
        return RedirectResponse(
            url="/admin/login",
            status_code=303,
        )

    success = register_user(username, password)

    if success:
        return RedirectResponse(
            url="/admin/users?result=created",
            status_code=303,
        )

    return RedirectResponse(
        url="/admin/users?error=create",
        status_code=303,
    )


@app.get("/admin/api/users")
async def admin_users_api(request: Request):
    if not require_admin(request):
        raise HTTPException(
            status_code=403,
            detail="دسترسی غیرمجاز",
        )

    return {"users": list_users()}


@app.post("/admin/api/users/{user_id}/password")
async def admin_change_password(
    user_id: int,
    request: Request,
    password: str = Form(...),
):
    if not require_admin(request):
        raise HTTPException(
            status_code=403,
            detail="دسترسی غیرمجاز",
        )

    if not change_user_password(user_id, password):
        raise HTTPException(
            status_code=400,
            detail="تغییر رمز ناموفق بود. رمز باید حداقل ۸ کاراکتر باشد.",
        )

    return {"success": True}


@app.post("/admin/api/users/{user_id}/delete")
async def admin_delete_user(
    user_id: int,
    request: Request,
):
    if not require_admin(request):
        raise HTTPException(
            status_code=403,
            detail="دسترسی غیرمجاز",
        )

    if not delete_user(user_id):
        raise HTTPException(
            status_code=400,
            detail="حذف حساب ناموفق بود.",
        )

    return {"success": True}


# ==================================================
# مدیریت اتصال‌های WebSocket
# ==================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    def log_connections(self, event: str, websocket: WebSocket):
        client = websocket.client

        ip = client.host if client else "Unknown"
        port = client.port if client else 0
        time = datetime.now().strftime("%H:%M:%S")

        print(
            f"[{time}] {event} | "
            f"IP: {ip}:{port} | "
            f"Online: {len(self.active_connections)}"
        )

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


# ==================================================
# نقطه اتصال WebSocket چت
# ==================================================

@app.websocket("/ws")
async def chat(websocket: WebSocket):
    session = websocket.scope.get("session", {})
    username = session.get("username")

    # فقط کاربران دارای نشست می‌توانند متصل شوند
    if not username:
        await websocket.close(code=1008)
        return

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


# اجرای سرور:
# python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info

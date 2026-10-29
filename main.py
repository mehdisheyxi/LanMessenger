
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
import sqlite3
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

import auth
import database

# ==================================================
# تنظیمات اولیه برنامه
# ==================================================

app = FastAPI(title="Painhub")

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
    database.init_db()


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
    success = auth.register_user(username, password)

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
    if not auth.verify_user(username, password):
        return RedirectResponse(
            url="/login?error=invalid",
            status_code=303,
        )

    user = auth.get_user(username)

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

    user = auth.get_user(username)

    if user and user["role"] == "admin" and user["is_active"]:
        return user

    return None


@app.get("/admin/login")
async def admin_login_page(request: Request):
    username = request.session.get("username")

    if username:
        user = auth.get_user(username)

        if user and user["role"] == "admin" and user["is_active"]:
            return RedirectResponse(url="/admin", status_code=303)

    return FileResponse(STATIC_DIR / "admin_login.html")


@app.post("/admin/login")
async def admin_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if not auth.verify_user(username, password):
        return RedirectResponse(
            url="/admin/login?error=invalid",
            status_code=303,
        )

    user = auth.get_user(username)

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

    success = auth.register_user(username, password)

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

    return {"users": auth.list_users()}


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

    if not auth.change_user_password(user_id, password):
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

    if not auth.delete_user(user_id):
        raise HTTPException(
            status_code=400,
            detail="حذف حساب ناموفق بود.",
        )

    return {"success": True}


@app.get("/api/users/search")
async def search_users_api(request: Request, q: str = ""):
    username = request.session.get("username")

    if not username:
        raise HTTPException(
            status_code=401,
            detail="ابتدا وارد حساب کاربری شوید.",
        )

    user = auth.get_user(username)

    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=401,
            detail="حساب کاربری معتبر نیست.",
        )

    q = q.strip()

    if len(q) > 30:
        raise HTTPException(
            status_code=400,
            detail="عبارت جست‌وجو بیش از حد طولانی است.",
        )

    users = database.search_users(q, user["id"])

    return {"users": users}


@app.get("/api/conversations")
async def api_get_conversations(request: Request):
    username = request.session.get("username")

    if not username:
        raise HTTPException(
            status_code=401,
            detail="ابتدا وارد حساب شوید.",
        )

    user = auth.get_user(username)

    if not user or not user["is_active"]:
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="حساب کاربری معتبر نیست.",
        )

    conversations = database.get_private_conversations(user["id"])

    return {"conversations": conversations}


@app.get("/api/messages")
async def private_messages_api(
    request: Request,
    username: str,
):
    current_username = request.session.get("username")

    if not current_username:
        raise HTTPException(
            status_code=401,
            detail="ابتدا وارد حساب کاربری شوید.",
        )

    current_user = auth.get_user(current_username)
    other_user = auth.get_user(username)

    if (
        not current_user
        or not current_user["is_active"]
        or not other_user
        or not other_user["is_active"]
        or current_user["id"] == other_user["id"]
    ):
        raise HTTPException(
            status_code=404,
            detail="کاربر پیدا نشد.",
        )

    rows = database.get_private_messages(
        current_user["id"],
        other_user["id"],
    )

    history = [
        {
            "id": row["id"],
            "sender": (
                current_user["username"]
                if row["sender_id"] == current_user["id"]
                else other_user["username"]
            ),
            "message": row["message"],
            "created_at": row["created_at"],
            "is_read": bool(row["is_read"]),
        }
        for row in rows
    ]

    return {"messages": history}


# ==================================================
# مدیریت اتصال‌های WebSocket
# ==================================================


class ConnectionManager:
    def __init__(self):
        self.active_connections: set[WebSocket] = set()
        self.user_connections: dict[str, set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, username: str):
        self.active_connections.add(websocket)

        if username not in self.user_connections:
            self.user_connections[username] = set()

        self.user_connections[username].add(websocket)

    def disconnect(self, websocket: WebSocket, username: str):
        self.active_connections.discard(websocket)

        connections = self.user_connections.get(username)

        if connections:
            connections.discard(websocket)

            if not connections:
                self.user_connections.pop(username, None)


    def log_connections(
        self,
        event: str,
        websocket: WebSocket,
        username: str,
    ):
        client = websocket.client

        ip = client.host if client else "Unknown"
        port = client.port if client else 0
        time = datetime.now().strftime("%H:%M:%S")

        print(
            f"[{time}] {event} | "
            f"Username: {username} | "
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
            self.active_connections.discard(connection)

            for username, connections in list(self.user_connections.items()):
                connections.discard(connection)

                if not connections:
                    self.user_connections.pop(username, None)

    async def send_to_user(self, username: str, message: dict):
        connections = self.user_connections.get(username, set())
        disconnected = []

        for connection in list(connections):
            try:
                await connection.send_json(message)
            except (RuntimeError, OSError):
                disconnected.append(connection)

        for connection in disconnected:
            self.disconnect(connection, username)


manager = ConnectionManager()


# ==================================================
# نقطه اتصال WebSocket چت
# ==================================================




@app.websocket("/ws")
async def chat(websocket: WebSocket):
    session = websocket.scope.get("session", {})
    username = session.get("username")

    # بررسی نشست پیش از پذیرش اتصال
    if not username:
        await websocket.close(code=1008)
        return

    user = auth.get_user(username)

    if not user or not user["is_active"]:
        await websocket.close(code=1008)
        return

    username = user["username"]
    user_id = user["id"]

    # فقط یک بار اتصال را می‌پذیریم
    await websocket.accept()
    await manager.connect(websocket, username)
    manager.log_connections("CONNECTED", websocket , username)

    try:
        await websocket.send_json({
            "type": "login_success",
            "username": username,
        })

        # دریافت پیام‌های خصوصی خوانده‌نشده
        with sqlite3.connect(database.DB_PATH) as connection:
            connection.row_factory = sqlite3.Row

            pending_messages = connection.execute(
                """
                SELECT
                    messages.id,
                    messages.sender_id,
                    users.username AS sender,
                    messages.message,
                    messages.created_at
                FROM messages
                JOIN users ON users.id = messages.sender_id
                WHERE messages.recipient_id = ?
                  AND messages.is_read = 0
                ORDER BY messages.id
                """,
                (user_id,),
            ).fetchall()

        for pending in pending_messages:
            await websocket.send_json({
                "type": "private_message",
                "id": pending["id"],
                "username": pending["sender"],
                "message": pending["message"],
                "created_at": pending["created_at"],
            })

        while True:
            raw_message = await websocket.receive_text()

            try:
                data = json.loads(raw_message)
            except json.JSONDecodeError:
                continue

            if not isinstance(data, dict):
                continue

                        # تأیید خوانده‌شدن پیام‌های خصوصی
            # تأیید خوانده‌شدن پیام‌های خصوصی
            if data.get("type") == "mark_read":
                sender_username = str(
                    data.get("sender", "")
                ).strip()

                sender = auth.get_user(sender_username)

                if not sender or not sender["is_active"]:
                    continue

                # علامت‌گذاری پیام‌های خوانده‌شده
                message_ids = database.mark_messages_read(
                    recipient_id=user_id,
                    sender_id=sender["id"],
                )

                # اطلاع به فرستنده
                if message_ids:
                    await manager.send_to_user(
                        sender["username"],
                        {
                            "type": "messages_read",
                            "reader": username,
                            "message_ids": message_ids,
                        },
                    )

                continue

            message_type = data.get("type", "group_message")
            message = str(data.get("message", "")).strip()

            if not message or len(message) > 1000:
                continue

            # پیام خصوصی
            if message_type == "private_message":
                recipient_username = str(
                    data.get("recipient", "")
                ).strip()

                recipient = auth.get_user(recipient_username)

                if (
                    not recipient
                    or not recipient["is_active"]
                    or recipient["id"] == user_id
                ):
                    await websocket.send_json({
                        "type": "private_message_error",
                        "message": "گیرنده معتبر نیست.",
                    })
                    continue

                message_id = database.save_private_message(
                    user_id,
                    recipient["id"],
                    message,
                )

                if message_id is None:
                    await websocket.send_json({
                        "type": "private_message_error",
                        "message": "ذخیره پیام ناموفق بود.",
                    })
                    continue

                await manager.send_to_user(
                    recipient["username"],
                    {
                        "type": "private_message",
                        "id": message_id,
                        "username": username,
                        "message": message,
                    },
                )

                await websocket.send_json({
                    "type": "private_message_sent",
                    "id": message_id,
                    "recipient": recipient["username"],
                    "message": message,
                })

                continue

            # پیام عمومی
            if message_type == "group_message":
                await manager.broadcast({
                    "type": "group_message",
                    "username": username,
                    "message": message,
                })

    except WebSocketDisconnect:
        pass

    except RuntimeError as error:
        print(f"WebSocket runtime error: {error}")

    finally:
        manager.disconnect(websocket, username)
        manager.log_connections("DISCONNECTED", websocket , username)



# اجرای سرور:
# python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info

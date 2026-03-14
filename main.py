from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import sqlite3
from passlib.context import CryptContext
from datetime import datetime
import uuid
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="E-Rescue API")
from fastapi import WebSocket, WebSocketDisconnect
# 加入 CORS 跨來源放行機制
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許所有網域連線 (開發測試階段先全開)
    allow_credentials=True,
    allow_methods=["*"],  # 允許 POST, GET 等所有方法
    allow_headers=["*"],  # 允許所有標頭
)

# ==========================================
# ⚡ WebSockets 即時通訊中心
# ==========================================
class ConnectionManager:
    def __init__(self):
        # 記住所有目前連線中的使用者 (手機/網頁)
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    # 廣播功能：一對多發送通知 (取代目前的 AMBER Alert 重新整理)
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# 建立一條讓未來 APP 連線的「神經通道」
@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            # 這裡保持連線，隨時聽取前端傳來的聲音
            data = await websocket.receive_text()
            print(f"收到來自 {client_id} 的訊息: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 🔐 密碼加密工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_db():
    conn = sqlite3.connect("rescue.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cursor = conn.cursor()
    # 訂單表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id TEXT PRIMARY KEY,
            user_id TEXT,
            category TEXT,
            description TEXT,
            req_lat REAL,
            req_lng REAL,
            status TEXT,
            provider_id TEXT
        )
    ''')
    # 🆕 新增：使用者會員表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT,
            role TEXT
        )
    ''')
    # 🚨 新增：緊急廣播表 (AMBER Alert)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT,
            is_active BOOLEAN,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()


init_db()


# --- Pydantic 格式模型 ---
class UserRegister(BaseModel):
    username: str
    password: str
    role: str = "client"  # client 或 provider


class UserLogin(BaseModel):
    username: str
    password: str


class RescueRequest(BaseModel):
    description: str
    req_lat: float
    req_lng: float
    user_id: str
    category: str


class AlertCreate(BaseModel):
    message: str


# ==========================================
# 🔐 會員系統 API
# ==========================================
@app.post("/register")
def register(user: UserRegister):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="此帳號已經有人使用囉！")

    hashed_password = pwd_context.hash(user.password)
    cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                   (user.username, hashed_password, user.role))
    conn.commit()
    conn.close()
    return {"message": "註冊成功！"}


@app.post("/login")
def login(user: UserLogin):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (user.username,))
    db_user = cursor.fetchone()
    conn.close()

    if not db_user or not pwd_context.verify(user.password, db_user["password_hash"]):
        raise HTTPException(status_code=400, detail="帳號或密碼錯誤！")

    return {"username": db_user["username"], "role": db_user["role"]}


# ==========================================
# 🚨 緊急廣播 API (AMBER Alert)
# ==========================================
@app.post("/alert")
def create_alert(alert: AlertCreate):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET is_active = 0")  # 先關閉舊的警報
    cursor.execute("INSERT INTO alerts (message, is_active, created_at) VALUES (?, 1, ?)",
                   (alert.message, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    return {"message": "緊急廣播已發佈至所有用戶！"}


@app.get("/alert/active")
def get_active_alert():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT message FROM alerts WHERE is_active = 1 ORDER BY id DESC LIMIT 1")
    alert = cursor.fetchone()
    conn.close()
    if alert:
        return {"active": True, "message": alert["message"]}
    return {"active": False, "message": ""}


# ==========================================
# 🚗 原本的任務系統 API
# ==========================================
@app.post("/requests")
def create_request(req: RescueRequest):
    req_id = str(uuid.uuid4())
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO requests (request_id, user_id, category, description, req_lat, req_lng, status)
        VALUES (?, ?, ?, ?, ?, ?, 'pending')
    ''', (req_id, req.user_id, req.category, req.description, req.req_lat, req.req_lng))
    conn.commit()
    conn.close()
    return {"request_id": req_id, "status": "pending"}


@app.get("/provider/requests")
def get_requests(category: Optional[str] = None):
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute("SELECT * FROM requests WHERE status = 'pending' AND category = ?", (category,))
    else:
        cursor.execute("SELECT * FROM requests WHERE status = 'pending'")
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks


@app.put("/provider/requests/{request_id}/accept")
def accept_request(request_id: str, provider_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE requests SET status = 'accepted', provider_id = ? WHERE request_id = ?",
                   (provider_id, request_id))
    conn.commit()
    conn.close()
    return {"message": "接單成功"}


# ==========================================
# 🏁 結案與歷史紀錄 API
# ==========================================
@app.put("/requests/{request_id}/complete")
def complete_request(request_id: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE requests SET status = 'completed' WHERE request_id = ?", (request_id,))
    conn.commit()
    conn.close()
    return {"message": "任務已結案"}


@app.get("/users/{username}/history")
def get_user_history(username: str, role: str):
    conn = get_db()
    cursor = conn.cursor()
    # 根據身分，撈出屬於他的所有訂單
    if role == "client":
        cursor.execute("SELECT * FROM requests WHERE user_id = ? ORDER BY rowid DESC", (username,))
    else:
        cursor.execute("SELECT * FROM requests WHERE provider_id = ? ORDER BY rowid DESC", (username,))

    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks
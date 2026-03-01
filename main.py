import sqlite3
import os
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
import uuid
from enum import Enum

app = FastAPI(title="道路救援系統 - V4.0 專業資料庫版")

# --- 0. 設定資料庫檔案 ---
DB_FILE = "rescue_system.db"


# --- 1. 資料模型與分類 ---
class ServiceCategory(str, Enum):
    towing = "機車拋錨"
    plumbing = "水電問題"
    gardening = "園藝問題"
    locksmith = "開鎖服務"
    other = "其他"


class AssistanceRequest(BaseModel):
    description: str
    req_lng: float
    req_lat: float
    user_id: str
    category: ServiceCategory
    status: str = "searching"
    request_id: Optional[str] = None
    provider_id: Optional[str] = None


# --- 2. 資料庫連線與初始化 ---
def get_db():
    """建立資料庫連線的小幫手"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # 讓我們可以像字典一樣讀取資料
    return conn


def init_db():
    """系統啟動時，檢查並建立資料表 (Table)"""
    conn = get_db()
    # 建立一個名為 requests 的資料表，就像 Excel 的工作表一樣
    conn.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            request_id TEXT PRIMARY KEY,
            description TEXT,
            req_lng REAL,
            req_lat REAL,
            user_id TEXT,
            category TEXT,
            status TEXT,
            provider_id TEXT
        )
    ''')
    conn.commit()
    conn.close()


# 啟動時立刻執行資料庫初始化
init_db()
print(f"👉 專業資料庫已啟動：{os.path.abspath(DB_FILE)}")


# ==========================================
# --- 3. User (求救者端) ---
# ==========================================
@app.post("/requests", tags=["User"])
async def create_request(req: AssistanceRequest):
    """使用者發送救援請求 (寫入資料庫)"""
    new_id = str(uuid.uuid4())
    conn = get_db()

    # 使用 SQL 的 INSERT 語法新增資料
    conn.execute('''
        INSERT INTO requests (request_id, description, req_lng, req_lat, user_id, category, status, provider_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
    new_id, req.description, req.req_lng, req.req_lat, req.user_id, req.category.value, req.status, req.provider_id))

    conn.commit()
    conn.close()

    return {"message": "請求已送出", "request_id": new_id, "category": req.category}


# ==========================================
# --- 4. Admin (上帝視角/管理端) ---
# ==========================================
@app.get("/admin/requests", tags=["Admin"])
async def get_all_requests(
        status: Optional[str] = Query(None, description="輸入 searching 或 completed 進行過濾")
):
    """查看所有救援單 (從資料庫查詢)"""
    conn = get_db()
    if status:
        # 使用 SQL 的 WHERE 進行條件過濾
        cursor = conn.execute("SELECT * FROM requests WHERE status = ?", (status,))
    else:
        cursor = conn.execute("SELECT * FROM requests")

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.get("/admin/dashboard", tags=["Admin"])
async def get_dashboard_stats():
    """查看系統統計數據 (使用 SQL 快速計算)"""
    conn = get_db()

    # SQL 的 COUNT 功能可以瞬間算出數量，不用一筆一筆數
    total = conn.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
    searching = conn.execute("SELECT COUNT(*) FROM requests WHERE status='searching'").fetchone()[0]
    completed = conn.execute("SELECT COUNT(*) FROM requests WHERE status='completed'").fetchone()[0]

    plumbing = conn.execute("SELECT COUNT(*) FROM requests WHERE category='水電問題'").fetchone()[0]
    towing = conn.execute("SELECT COUNT(*) FROM requests WHERE category='機車拋錨'").fetchone()[0]

    conn.close()

    return {
        "營運狀態": {"總訂單": total, "尋找中": searching, "已完成": completed},
        "熱門服務": {"水電問題": plumbing, "機車拋錨": towing}
    }


# ==========================================
# --- 5. Provider (司機/師傅端) ---
# ==========================================
@app.get("/provider/requests", tags=["Provider"])
async def get_available_tasks(
        category: ServiceCategory = Query(..., description="請選擇你的專業領域")
):
    """師傅專屬任務牆：只看符合自己專業且還在 searching 的單"""
    conn = get_db()
    # 雙重條件查詢：狀態是 searching 且 類別符合
    cursor = conn.execute(
        "SELECT * FROM requests WHERE status = 'searching' AND category = ?",
        (category.value,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.put("/provider/requests/{request_id}/accept", tags=["Provider"])
async def accept_request(request_id: str, provider_id: str):
    """師傅接單 (更新資料庫狀態)"""
    target_id = request_id.strip()
    conn = get_db()

    # 1. 先查出這張單目前的狀態
    req = conn.execute("SELECT status FROM requests WHERE request_id = ?", (target_id,)).fetchone()

    if not req:
        conn.close()
        raise HTTPException(status_code=404, detail="找不到該請求 ID")

    if req["status"] != "searching":
        conn.close()
        raise HTTPException(status_code=400, detail="手腳太慢啦！這張單已經被接走或取消了。")

    # 2. 如果還是 searching，就使用 UPDATE 語法更新狀態和司機 ID
    conn.execute('''
        UPDATE requests 
        SET status = 'on_the_way', provider_id = ? 
        WHERE request_id = ?
    ''', (provider_id, target_id))

    conn.commit()
    conn.close()

    return {"message": "接單成功！", "request_id": target_id}
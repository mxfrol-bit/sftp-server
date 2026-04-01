from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from fastapi.responses import HTMLResponse
import os, shutil, json
from datetime import datetime
from supabase import create_client

app = FastAPI()
API_KEY = os.getenv("API_KEY")
UPLOAD_DIR = "/app/uploads"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@app.post("/upload")
async def upload(file: UploadFile = File(...), x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    path = f"{UPLOAD_DIR}/{filename}"
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)
    try:
        sb = get_supabase()
        sb.table("uploads").insert({
            "filename": filename,
            "file_size": len(content),
            "status": "new"
        }).execute()
    except Exception as e:
        print(f"Supabase error: {e}")
    return {"status": "ok", "file": filename}

@app.get("/files")
async def list_files(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    files = []
    for fname in sorted(os.listdir(UPLOAD_DIR), reverse=True):
        fpath = f"{UPLOAD_DIR}/{fname}"
        stat = os.stat(fpath)
        files.append({
            "name": fname,
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        })
    return files

@app.get("/files/{filename}")
async def get_file(filename: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    path = f"{UPLOAD_DIR}/{filename}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        return json.loads(content)
    except:
        return {"raw": content}

@app.delete("/files/{filename}")
async def delete_file(filename: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    path = f"{UPLOAD_DIR}/{filename}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    os.remove(path)
    return {"status": "deleted", "file": filename}

@app.post("/save-to-db/{filename}")
async def save_to_db(filename: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    path = f"{UPLOAD_DIR}/{filename}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sb = get_supabase()
    upload = sb.table("uploads").select("id").eq("filename", filename).execute()
    upload_id = upload.data[0]["id"] if upload.data else None
    orders = data.get("orders", [])
    saved = 0
    for order in orders:
        sb.table("orders").insert({
            "upload_id": upload_id,
            "order_id": order.get("order_id"),
            "order_date": order.get("date"),
            "client_name": order.get("client", {}).get("name"),
            "client_inn": order.get("client", {}).get("inn"),
            "client_phone": order.get("client", {}).get("phone"),
            "total": order.get("total"),
            "status": order.get("status"),
            "comment": order.get("comment"),
            "items": json.dumps(order.get("items", []), ensure_ascii=False)
        }).execute()
        saved += 1
    if upload_id:
        sb.table("uploads").update({"status": "saved"}).eq("id", upload_id).execute()
    return {"status": "ok", "saved": saved}

@app.get("/admin", response_class=HTMLResponse)
async def admin():
    return open("/app/admin.html").read()

@app.get("/")
def health():
    return {"status": "running"}

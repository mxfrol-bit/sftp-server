from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from fastapi.responses import HTMLResponse
import os, json
from datetime import datetime
from supabase import create_client

app = FastAPI()
API_KEY = os.getenv("API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

@app.post("/upload")
async def upload(file: UploadFile = File(...), x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    content = await file.read()
    sb = get_supabase()
    sb.storage.from_("uploads").upload(filename, content, {"content-type": "application/json"})
    sb.table("uploads").insert({
        "filename": filename,
        "file_size": len(content),
        "status": "new"
    }).execute()
    return {"status": "ok", "file": filename}

@app.get("/files")
async def list_files(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    sb = get_supabase()
    result = sb.table("uploads").select("*").order("uploaded_at", desc=True).execute()
    files = []
    for row in result.data:
        files.append({
            "name": row["filename"],
            "size": row["file_size"] or 0,
            "created": row["uploaded_at"][:19].replace("T", " "),
            "status": row["status"]
        })
    return files

@app.get("/files/{filename}")
async def get_file(filename: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    sb = get_supabase()
    content = sb.storage.from_("uploads").download(filename)
    try:
        return json.loads(content)
    except:
        return {"raw": content.decode("utf-8")}

@app.delete("/files/{filename}")
async def delete_file(filename: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    sb = get_supabase()
    sb.storage.from_("uploads").remove([filename])
    sb.table("uploads").delete().eq("filename", filename).execute()
    return {"status": "deleted", "file": filename}

@app.post("/save-to-db/{filename}")
async def save_to_db(filename: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    sb = get_supabase()
    content = sb.storage.from_("uploads").download(filename)
    data = json.loads(content)
    upload = sb.table("uploads").select("id").eq("filename", filename).execute()
    upload_id = upload.data[0]["id"] if upload.data else None
    orders = data.get("orders", [])
    saved = 0
    skipped = 0
    for order in orders:
        existing = sb.table("orders").select("id").eq("order_id", order.get("order_id")).execute()
        if existing.data:
            skipped += 1
            continue
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
    return {"status": "ok", "saved": saved, "skipped": skipped}

@app.get("/admin", response_class=HTMLResponse)
async def admin():
    return open("/app/admin.html").read()

@app.get("/")
def health():
    return {"status": "running"}

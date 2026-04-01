from fastapi import FastAPI, UploadFile, File, Header, HTTPException
from fastapi.responses import HTMLResponse
import os, shutil, json
from datetime import datetime

app = FastAPI()
API_KEY = os.getenv("API_KEY", "secret123")
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload(file: UploadFile = File(...), x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{file.filename}"
    path = f"{UPLOAD_DIR}/{filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
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

@app.get("/admin", response_class=HTMLResponse)
async def admin():
    return open("/app/admin.html").read()

@app.get("/")
def health():
    return {"status": "running"}

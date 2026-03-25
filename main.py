from fastapi import FastAPI, UploadFile, File, Header, HTTPException
import os, shutil

app = FastAPI()
API_KEY = os.getenv("API_KEY", "secret123")
UPLOAD_DIR = "/app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload(file: UploadFile = File(...), x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    path = f"{UPLOAD_DIR}/{file.filename}"
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"status": "ok", "file": file.filename}

@app.get("/")
def health():
    return {"status": "running"}
```

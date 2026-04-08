from fastapi import FastAPI, UploadFile, File, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import os, json, httpx, secrets
from datetime import datetime
from supabase import create_client

app = FastAPI()
security = HTTPBasic()

API_KEY        = os.getenv("API_KEY")
SUPABASE_URL   = os.getenv("SUPABASE_URL")
SUPABASE_KEY   = os.getenv("SUPABASE_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
TG_TOKEN       = os.getenv("TG_TOKEN")
TG_CHAT_ID     = os.getenv("TG_CHAT_ID")
ADMIN_USER     = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS     = os.getenv("ADMIN_PASS", "harvest2025")

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
    try:
        sb.storage.from_("uploads").upload(filename, content, {"content-type": "application/json"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage error: {str(e)}")
    try:
        sb.table("uploads").insert({
            "filename": filename,
            "file_size": len(content),
            "status": "new"
        }).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
    return {"status": "ok", "file": filename}

@app.get("/files")
async def list_files(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    sb = get_supabase()
    result = sb.table("uploads").select("*").order("uploaded_at", desc=True).execute()
    return [{"name": r["filename"], "size": r["file_size"] or 0,
             "created": r["uploaded_at"][:19].replace("T", " "),
             "status": r["status"]} for r in result.data]

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
    return {"status": "deleted"}

@app.post("/save-to-db/{filename}")
async def save_to_db(filename: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    sb = get_supabase()
    content = sb.storage.from_("uploads").download(filename)
    data = json.loads(content.decode("utf-8-sig"))
    upload_res = sb.table("uploads").select("id").eq("filename", filename).execute()
    upload_id = upload_res.data[0]["id"] if upload_res.data else None
    number = data.get("Номер")
    existing = sb.table("needs").select("id").eq("number", number).execute()
    if existing.data:
        return {"status": "skipped", "reason": f"Номер {number} уже в базе"}
    sb.table("needs").insert({
        "upload_id": upload_id,
        "number": number,
        "date": data.get("Дата"),
        "status": data.get("Статус"),
        "nomenclature": data.get("Номенклатура"),
        "buyer": data.get("Покупатель"),
        "delivery_address": data.get("Адрес выгрузки"),
        "delivery_date": data.get("Срок поставки"),
        "volume": data.get("Объём"),
        "amount": data.get("Сумма"),
        "remains": data.get("Осталось"),
        "deal_type": data.get("Тип сделки"),
        "margin_source": data.get("Источник маржинальности"),
        "suppliers": json.dumps(data.get("Закупка", []), ensure_ascii=False)
    }).execute()
    if upload_id:
        sb.table("uploads").update({"status": "saved"}).eq("id", upload_id).execute()
    return {"status": "ok", "number": number, "suppliers": len(data.get("Закупка", []))}

@app.post("/mark-done/{filename}")
async def mark_done(filename: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)
    sb = get_supabase()
    sb.table("uploads").update({"status": "done"}).eq("filename", filename).execute()
    return {"status": "ok"}

@app.post("/analyze/{filename}")
async def analyze(filename: str, x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403)

    sb = get_supabase()
    content = sb.storage.from_("uploads").download(filename)
    data = json.loads(content.decode("utf-8-sig"))

    number       = data.get("Номер", "")
    date         = data.get("Дата", "")
    nomenclature = data.get("Номенклатура", "").strip()
    buyer        = data.get("Покупатель", "")
    delivery     = data.get("Адрес выгрузки", "")
    volume       = data.get("Объём", "")
    amount       = data.get("Сумма", "")
    suppliers    = data.get("Закупка", [])

    suppliers_text = ""
    for i, s in enumerate(suppliers, 1):
        suppliers_text += (
            f"\n{i}. {s.get('Контрагент', '')}"
            f"\n   Адрес загрузки: {s.get('АдресЗагрузки', '')}"
            f"\n   Цена: {s.get('Цена', '')} руб/т | Объём: {s.get('Объем', '')} т"
            f"\n   Качество: {s.get('КачественныеПоказатели', '')}"
            f"\n   Ответственный: {s.get('ФИО', '')}\n"
        )

    prompt = (
        f"Ты старший закупщик зернового рынка России с 10-летним опытом. "
        f"Готовишь аналитическую справку для руководителя компании. "
        f"Анализ должен быть профессиональным, конкретным, с реальными рыночными данными и помогать принять решение.\n\n"

        f"ДАННЫЕ ЗАЯВКИ:\n"
        f"Номер: {number} | Дата: {date}\n"
        f"Культура: {nomenclature}\n"
        f"Покупатель: {buyer}\n"
        f"Точка выгрузки: {delivery}\n"
        f"Требуемый объём: {volume} т | Сумма: {amount} руб\n\n"

        f"ПОСТАВЩИКИ:\n{suppliers_text}\n\n"

        f"ПОДГОТОВЬ ОТЧЁТ ПО СЛЕДУЮЩЕЙ СТРУКТУРЕ:\n\n"

        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"АНАЛИТИЧЕСКАЯ СПРАВКА №{number}\n"
        f"Культура: {nomenclature} | Дата: {date}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        f"БЛОК 1 - РЫНОК\n"
        f"Напиши текущую рыночную цену на {nomenclature} в России весной 2026 года. "
        f"Укажи диапазон цен по регионам (Центр, Поволжье, Юг, Сибирь). "
        f"Опиши сезонный тренд и ключевые факторы влияющие на цену.\n\n"

        f"БЛОК 2 - АНАЛИЗ КАЖДОГО ПОСТАВЩИКА\n"
        f"Для каждого поставщика сделай карточку:\n"
        f"- Статус (выгодно/рынок/дорого/подозрительно)\n"
        f"- Цена и отклонение от рынка в процентах\n"
        f"- Примерное расстояние от региона загрузки до {delivery} и стоимость доставки\n"
        f"- Итоговая цена с доставкой\n"
        f"- Риски и плюсы\n\n"

        f"БЛОК 3 - СВОДКА\n"
        f"Мин/макс/средняя цена по заявке. Сравнение с рынком. "
        f"Потенциальная экономия при выборе лучших поставщиков в рублях.\n\n"

        f"БЛОК 4 - ЛОГИСТИКА\n"
        f"Оцени транспортное плечо и риски логистики для каждого поставщика.\n\n"

        f"БЛОК 5 - РИСКИ\n"
        f"Перечисли риски по каждому поставщику и общие рыночные риски. "
        f"Отметь красные флаги если есть (подозрительно низкие цены, неизвестные контрагенты).\n\n"

        f"БЛОК 6 - РЕЙТИНГ\n"
        f"Пронумеруй всех поставщиков от лучшего к худшему с итоговой ценой включая доставку.\n\n"

        f"БЛОК 7 - СТРАТЕГИЯ ДЛЯ РУКОВОДИТЕЛЯ\n"
        f"Оптимальная стратегия закупки: у кого брать, сколько тонн у каждого, "
        f"где торговаться и на сколько процентов, итоговый бюджет, ожидаемая экономия.\n\n"

        f"БЛОК 8 - ЗАКЛЮЧЕНИЕ\n"
        f"5-7 предложений для руководителя: ситуация на рынке, лучшие поставщики, "
        f"экономия, риски, что делать прямо сейчас. Конкретно, с цифрами, без воды."
    )

    try:
        payload = {
            "model": "anthropic/claude-3.5-haiku",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4000
        }
        payload_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json; charset=utf-8",
                    "HTTP-Referer": "https://russian-harvest.ru",
                    "X-Title": "Russky Urozhai"
                },
                content=payload_bytes
            )
        result = response.json()
        analysis = result["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OpenRouter error: {str(e)}")

    # Отправка в Telegram — разбиваем на части если длинный текст
    tg_sent = False
    if TG_TOKEN and TG_CHAT_ID:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Telegram ограничение 4096 символов — разбиваем
                chunks = [analysis[i:i+4000] for i in range(0, len(analysis), 4000)]
                for chunk in chunks:
                    tg_payload = {
                        "chat_id": TG_CHAT_ID,
                        "text": chunk,
                        "parse_mode": "Markdown"
                    }
                    tg_bytes = json.dumps(tg_payload, ensure_ascii=False).encode("utf-8")
                    await client.post(
                        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                        headers={"Content-Type": "application/json; charset=utf-8"},
                        content=tg_bytes
                    )
            tg_sent = True
        except Exception as e:
            print(f"Telegram error: {e}")

    sb.table("uploads").update({"status": "done"}).eq("filename", filename).execute()
    return {"status": "ok", "analysis": analysis, "tg_sent": tg_sent}

@app.get("/admin", response_class=HTMLResponse)
async def admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_user = secrets.compare_digest(credentials.username, ADMIN_USER)
    correct_pass = secrets.compare_digest(credentials.password, ADMIN_PASS)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=401,
            headers={"WWW-Authenticate": "Basic"},
            detail="Unauthorized"
        )
    return open("/app/admin.html").read()

@app.get("/")
def health():
    return {"status": "running", "service": "Russky Urozhai API"}

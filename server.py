from fastapi import FastAPI, Request
from bot import app as telegram_app  # импорт Telegram Application из bot.py

web_app = FastAPI()

@web_app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    update = telegram_app.bot.Update.de_json(data)
    await telegram_app.update_queue.put(update)
    return {"ok": True}

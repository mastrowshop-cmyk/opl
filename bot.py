import logging
import os
import json
import asyncio
from typing import List, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
)

# ----------------- Настройки -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_CHAT_ID = -1002136717768
REVIEWS_FILE = "reviews.json"
USER_REVIEW_STATE: Dict[int, str] = {}
file_lock = asyncio.Lock()
DELETE_AFTER = 300  # 5 минут

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ----------------- Работа с отзывами -----------------
async def load_reviews() -> List[dict]:
    async with file_lock:
        if not os.path.exists(REVIEWS_FILE):
            return []
        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(
                None, lambda: json.load(open(REVIEWS_FILE, "r", encoding="utf-8"))
            )
        except:
            return []

async def save_reviews(reviews: List[dict]):
    async with file_lock:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None, lambda: json.dump(reviews, open(REVIEWS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        )

async def add_review(author_id: int, author_username: str, text: str):
    reviews = await load_reviews()
    reviews.append({
        "author_id": author_id,
        "author_username": author_username,
        "text": text,
    })
    await save_reviews(reviews)

# ----------------- Утилиты -----------------
def split_message_by_limit(text: str, limit: int = 4000):
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut == -1:
            cut = text.rfind(" ", 0, limit)
        if cut == -1:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts

async def delete_later(msg):
    await asyncio.sleep(DELETE_AFTER)
    try:
        await msg.delete()
    except:
        pass

# ----------------- Приветствие новых участников -----------------
async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status
    user = result.new_chat_member.user

    if old_status in [ChatMember.LEFT, ChatMember.KICKED] and new_status == ChatMember.MEMBER:
        msg_text = (
            f"👋 Добро пожаловать в Oplatym.ru!\n\n"
            f"‼️ ВАЖНО: ОСТЕРЕГАЙТЕСЬ МОШЕННИКОВ ‼️\n\n"
            f"Мы никогда не пишем первыми. Используйте только официальные аккаунты:\n"
            f"- @OplatymRU\n- @ByOplatymRu\n- @oplatymManager3\n- @OplatymRu4\n"
            f"- @oplatym_exchange07\n- @Oplatym_exchange20\n"
            f"- @CNYExchangeOplatym\n- @CNYExchangeOplatym2\n\n"
            f"Рады приветствовать вас, {user.full_name}! 🎉"
        )
        msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=msg_text)
        asyncio.create_task(delete_later(msg))

# ----------------- Команды -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("Бот запущен!")
    asyncio.create_task(delete_later(msg))

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(f"Chat ID: {update.message.chat_id}")
    asyncio.create_task(delete_later(msg))

async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reviews = await load_reviews()
    if not reviews:
        msg = await update.message.reply_text("ℹ️ Отзывов нет.")
        asyncio.create_task(delete_later(msg))
        return

    full = "📣 НОВЫЕ ОТЗЫВЫ:\n\n"
    for i, r in enumerate(reviews, start=1):
        full += f"{i}. От @{r['author_username']}:\n{r['text']}\n\n"

    for chunk in split_message_by_limit(full):
        await context.bot.send_message(chat_id=PUBLIC_CHAT_ID, text=chunk)

    await save_reviews([])
    msg = await update.message.reply_text("✅ Отправлено.")
    asyncio.create_task(delete_later(msg))

# ----------------- Меню отзывов -----------------
async def review_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "review":
        USER_REVIEW_STATE[user_id] = "wait"
        await query.edit_message_text("✍️ Напишите отзыв одним сообщением.")
    else:
        USER_REVIEW_STATE.pop(user_id, None)
        await query.edit_message_text("❌ Отменено.")

# ----------------- Обработка сообщений -----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()
    logger.info(f"Сообщение от {user.id} ({user.full_name}): {text}")

    if USER_REVIEW_STATE.get(user.id) == "wait":
        username = user.username or user.first_name
        await add_review(user.id, username, text)
        USER_REVIEW_STATE.pop(user.id, None)
        msg = await update.message.reply_text("Спасибо! Отзыв сохранён.")
        asyncio.create_task(delete_later(msg))
        return

# ----------------- Основной запуск -----------------
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("id", get_chat_id))
    app.add_handler(CommandHandler("end", end_command))
    app.add_handler(CallbackQueryHandler(review_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(ChatMemberHandler(welcome_member, ChatMemberHandler.CHAT_MEMBER))

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()

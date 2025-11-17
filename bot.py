import logging
import os
import json
import asyncio
from typing import List, Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ----------------- Настройки -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")   # ОБЯЗАТЕЛЬНО: в Bothost → переменные окружения

PUBLIC_CHAT_ID = -1002136717768      # Чат для публикации отзывов

MANAGER_IDS = {
    5314493557,
    7279244310,
    7754541004,
    8444260034,
    7840997504,
    8185132005,
    6962444738,
    7431538558,
}

REVIEWS_FILE = "reviews.json"
USER_REVIEW_STATE: Dict[int, str] = {}

file_lock = asyncio.Lock()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ----------------- Автоудаление сообщений -----------------
async def auto_delete_message(bot, chat_id, message_id, delay=300):
    await asyncio.sleep(delay)  # 300 секунд = 5 минут
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass


# ----------------- Работа с файлом отзывов -----------------
async def load_reviews() -> List[Dict[str, Any]]:
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


async def save_reviews(reviews: List[Dict[str, Any]]):
    async with file_lock:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: json.dump(
                reviews,
                open(REVIEWS_FILE, "w", encoding="utf-8"),
                ensure_ascii=False,
                indent=2,
            ),
        )


async def add_review(author_id: int, author_username: str, text: str):
    reviews = await load_reviews()
    reviews.append({
        "author_id": author_id,
        "author_username": author_username,
        "text": text,
    })
    await save_reviews(reviews)


# ----------------- Текстовые утилиты -----------------
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


# ----------------- Команды -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "👋 Бот запущен!\n\n"
        "/id — узнать chat_id\n"
        "/end — отправить все отзывы (только менеджерам)\n\n"
        "Менеджеры могут отправлять клиентам меню для отзыва."
    )

    asyncio.create_task(auto_delete_message(context.bot, msg.chat_id, msg.message_id))


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(f"Chat ID: {update.message.chat_id}")
    asyncio.create_task(auto_delete_message(context.bot, msg.chat_id, msg.message_id))


async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in MANAGER_IDS:
        msg = await update.message.reply_text("❌ Нет доступа.")
        asyncio.create_task(auto_delete_message(context.bot, msg.chat_id, msg.message_id))
        return

    reviews = await load_reviews()
    if not reviews:
        msg = await update.message.reply_text("ℹ️ Отзывов нет.")
        asyncio.create_task(auto_delete_message(context.bot, msg.chat_id, msg.message_id))
        return

    full = "📣 НОВЫЕ ОТЗЫВЫ:\n\n"
    for i, r in enumerate(reviews, start=1):
        full += f"{i}. От @{r['author_username']}:\n{r['text']}\n\n"

    for chunk in split_message_by_limit(full):
        await context.bot.send_message(chat_id=PUBLIC_CHAT_ID, text=chunk)

    await save_reviews([])
    msg = await update.message.reply_text("✅ Отправлено.")
    asyncio.create_task(auto_delete_message(context.bot, msg.chat_id, msg.message_id))


# ----------------- Меню отзыва -----------------
async def send_review_menu(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ Оставить отзыв", callback_data="review")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=user_id,
        text="Спасибо за покупку! Хотите оставить отзыв?",
        reply_markup=markup,
    )


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


# ----------------- Приветствие новых участников -----------------
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        username = new_user.username or new_user.first_name

        msg = await update.message.reply_text(
            f"👋 Добро пожаловать в Oplatym.ru!\n\n"
            f"Мы рады видеть вас в нашем чате, пожалуйста ознакомьтесь с предупреждением ниже!\n\n"
            "‼️ ВАЖНО: ОСТЕРЕГАЙТЕСЬ МОШЕННИКОВ ‼️\n\n"
            "В последнее время участились случаи мошенничества.\n"
            "Мы никогда не пишем первыми.\n\n"
            "🔐 Официальные аккаунты Oplatym.ru:\n"
            "- @OplatymRU\n- @ByOplatymRu\n- @oplatymManager3\n- @OplatymRu4\n\n"
            "Денежные переводы:\n"
            "- @Oplatym_exchange07\n- @Oplatym_exchange20\n\n"
            "Alipay:\n"
            "- @CNYExchangeOplatym\n- @CNYExchangeOplatym2\n\n"
            f"Рады приветствовать вас, {username}! 🎉"
        )

        asyncio.create_task(
            auto_delete_message(context.bot, msg.chat_id, msg.message_id)
        )


# ----------------- Обработка текстов -----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # триггер для русской фразы "конец"
    if text.lower() == "конец" and user.id in MANAGER_IDS:
        return await end_command(update, context)

    # режим отзыва
    if USER_REVIEW_STATE.get(user.id) == "wait":
        username = user.username or user.first_name
        await add_review(user.id, username, text)
        USER_REVIEW_STATE.pop(user.id, None)
        return await update.message.reply_text("Спасибо! Отзыв сохранён.")

    # автоответчик
    resp = generate_response(text.lower())
    if resp:
        msg = await update.message.reply_text(resp)
        asyncio.create_task(
            auto_delete_message(context.bot, msg.chat_id, msg.message_id)
        )


# ----------------- Генератор ответов -----------------
def generate_response(text: str):
    keys = [
        "как купить", "как перевести", "как оплатить",
        "нужно оплатить", "нужно перевести", "нужно купить"
    ]
    if any(k in text for k in keys):
        return (
            "👋 Уважаемый клиент!\n\n"
            "Обратитесь в один из наших аккаунтов:\n"
            "- @OplatymRU\n"
            "- @ByOplatymRu\n"
            "- @oplatymManager3\n"
            "- @OplatymRu4\n\n"
            "Мы первыми не пишем — остерегайтесь мошенников!"
        )
    return ""


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
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()

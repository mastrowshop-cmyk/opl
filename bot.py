# bot.py
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
# Установите в окружении переменную BOT_TOKEN = "123456:ABC..." (токен от @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID общего чата для отправки отзывов (вы указали)
PUBLIC_CHAT_ID = -1002136717768

# Список user_id менеджеров, которым разрешено выполнять /конец
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

# Файл для персистентного хранения отзывов
REVIEWS_FILE = "reviews.json"

# В памяти — состояние пользователей, которые сейчас оставляют отзыв
USER_REVIEW_STATE: Dict[int, str] = {}

# Асинхронный лок для операций с файлом
file_lock = asyncio.Lock()

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ----------------- Вспомогательные функции для работы с файлом -----------------
async def load_reviews() -> List[Dict[str, Any]]:
    """Загрузить список отзывов из REVIEWS_FILE (если файл не существует — вернуть пустой список)."""
    async with file_lock:
        if not os.path.exists(REVIEWS_FILE):
            return []
        # Чтение файла в отдельном потоке чтобы не блокировать loop
        loop = asyncio.get_running_loop()
        def _read():
            with open(REVIEWS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        try:
            data = await loop.run_in_executor(None, _read)
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error(f"Ошибка при загрузке отзывов: {e}")
            return []


async def save_reviews(reviews: List[Dict[str, Any]]):
    """Сохранить список отзывов в REVIEWS_FILE."""
    async with file_lock:
        loop = asyncio.get_running_loop()
        def _write():
            with open(REVIEWS_FILE, "w", encoding="utf-8") as f:
                json.dump(reviews, f, ensure_ascii=False, indent=2)
        try:
            await loop.run_in_executor(None, _write)
        except Exception as e:
            logger.error(f"Ошибка при сохранении отзывов: {e}")


async def add_review(author_id: int, author_username: str, text: str):
    """Добавить отзыв в файл."""
    review = {
        "author_id": author_id,
        "author_username": author_username or "",
        "text": text,
    }
    reviews = await load_reviews()
    reviews.append(review)
    await save_reviews(reviews)
    logger.info(f"Добавлен отзыв: {review}")


# ----------------- Утилитарные функции -----------------
def split_message_by_limit(text: str, limit: int = 4000) -> List[str]:
    """Разбить длинный текст на части длиной <= limit (Telegram limit ~4096, использую запас)."""
    parts = []
    while len(text) > limit:
        # искать разрыв на последнем доступном переносе строки или пробеле
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
    await update.message.reply_text(
        "👋 Добро пожаловать! Я бот для сбора отзывов.\n\n"
        "Команды:\n"
        "/id — получить chat_id (полезно для настройки)\n"
        "/конец — (только для менеджеров) отправить все накопленные отзывы в общий чат\n\n"
        "Менеджерам: после покупки вы можете вызвать функцию send_review_menu(user_id, context)\n"
        "чтобы отправить пользователю меню с просьбой оставить отзыв."
    )


async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    await update.message.reply_text(f"Chat ID: {chat_id}")


async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет все накопленные отзывы в PUBLIC_CHAT_ID — доступно только менеджерам."""
    user = update.effective_user
    if not user or user.id not in MANAGER_IDS:
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return

    reviews = await load_reviews()
    if not reviews:
        await update.message.reply_text("ℹ️ Отзывов нет.")
        return

    # Собираем единый текст
    parts = []
    for idx, r in enumerate(reviews, start=1):
        author = r.get("author_username") or f"id:{r.get('author_id')}"
        text = r.get("text", "")
        parts.append(f"{idx}. От: {author}\n{text}\n---")

    full_text = "📣 НОВЫЕ ОТЗЫВЫ:\n\n" + "\n".join(parts)

    # Отправляем по частям, если большой
    for chunk in split_message_by_limit(full_text):
        try:
            await context.bot.send_message(chat_id=PUBLIC_CHAT_ID, text=chunk)
        except Exception as e:
            logger.error(f"Ошибка при отправке в PUBLIC_CHAT_ID: {e}")
            await update.message.reply_text(f"❌ Ошибка при отправке отзывов: {e}")
            return

    # Очищаем файл
    await save_reviews([])
    await update.message.reply_text("✅ Все отзывы отправлены и буфер очищен.")


# ----------------- Меню отправки отзыва -----------------
async def send_review_menu(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет пользователю меню с кнопками 'Оставить отзыв' / 'Отмена'."""
    keyboard = [
        [InlineKeyboardButton("⭐ Оставить отзыв", callback_data="leave_review")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_review")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="Спасибо за покупку! Хотите оставить отзыв?",
            reply_markup=reply_markup,
        )
        logger.info(f"Меню отзыва отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при отправке меню отзывов пользователю {user_id}: {e}")


# ----------------- Обработчики CallbackQuery -----------------
async def review_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    user_id = query.from_user.id

    if query.data == "leave_review":
        USER_REVIEW_STATE[user_id] = "waiting_for_review"
        try:
            await query.edit_message_text("✍️ Напишите ваш отзыв одним сообщением. После отправки отзыв будет сохранён.")
        except Exception:
            # менее критично — просто отправим новое сообщение
            await context.bot.send_message(chat_id=user_id, text="✍️ Напишите ваш отзыв одним сообщением. После отправки отзыв будет сохранён.")
    elif query.data == "cancel_review":
        USER_REVIEW_STATE.pop(user_id, None)
        try:
            await query.edit_message_text("❌ Отзыв отменён.")
        except Exception:
            await context.bot.send_message(chat_id=user_id, text="❌ Отзыв отменён.")


# ----------------- Обработка входящих текстов -----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    user = update.effective_user
    user_id = user.id if user else None
    text = update.message.text.strip()

    # Если пользователь в режиме "оставить отзыв"
    if user_id and USER_REVIEW_STATE.get(user_id) == "waiting_for_review":
        # Добавляем отзыв в persistent файл
        username = user.username if user and user.username else f"{user.first_name if user else 'user'}"
        await add_review(author_id=user_id, author_username=username, text=text)

        # Уведомляем пользователя
        await update.message.reply_text("Спасибо! Ваш отзыв сохранён и будет отправлен менеджером.")
        # Убираем состояние
        USER_REVIEW_STATE.pop(user_id, None)
        return

    # --- Ваш существующий генератор ответов (из старого бота) ---
    message_type = update.message.chat.type
    lower_text = text.lower()

    logger.info(f"User ({update.message.chat.id}) in {message_type}: \"{lower_text}\"")

    response = generate_response(lower_text)

    if response:
        await update.message.reply_text(response)


# ----------------- Генерация ответов (оставлена без изменений) -----------------
def generate_response(text: str) -> str:
    keywords = [
        "как купить",
        "как перевести",
        "как оплатить",
        "нужно оплатить",
        "нужно перевести",
        "нужно купить",
    ]

    if any(keyword in text for keyword in keywords):
        return (
            "👋 Уважаемый клиент,\n\n"
            "Обратитесь в один из наших аккаунтов:\n\n"
            "Оплата сервисов:\n"
            "- @OplatymRU\n"
            "- @ByOplatymRu\n"
            "- @oplatymManager3\n"
            "- @OplatymRu4\n\n"
            "Денежные переводы:\n"
            "- @oplatym_exchange07\n"
            "- @Oplatym_exchange20\n\n"
            "Alipay:\n"
            "- @CNYExchangeOplatym\n"
            "- @CNYExchangeOplatym2\n\n"
            "_________________________________________\n\n"
            "К вашему сведению, мы первыми не пишем! Пожалуйста остерегайтесь мошенников."
        )
    return ""


# ----------------- Обработчик ошибок -----------------
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")


# ----------------- Главная функция -----------------
def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables. Set BOT_TOKEN and restart.")
        print("❌ ОШИБКА: Задайте переменную окружения BOT_TOKEN и перезапустите бота.")
        return

    try:
        app = Application.builder().token(BOT_TOKEN).build()

        # Команды
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("id", get_chat_id))
        app.add_handler(CommandHandler("конец", end_command))

        # Кнопки отзыва
        app.add_handler(CallbackQueryHandler(review_buttons))

        # Текстовые сообщения
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Ошибки
        app.add_error_handler(error_handler)

        logger.info("Бот запущен...")
        print("🤖 Бот запущен. Ctrl+C для остановки.")
        app.run_polling(poll_interval=3, drop_pending_updates=True)

    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        print(f"❌ Ошибка при запуске: {e}")


if __name__ == "__main__":
    main()


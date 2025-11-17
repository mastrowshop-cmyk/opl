import logging
import os
import json
import asyncio
from typing import List, Dict, Any

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
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ОБЯЗАТЕЛЬНО: в Bothost → переменные окружения

PUBLIC_CHAT_ID = -1002136717768  # Чат для публикации отзывов

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

# Время автоудаления сообщений (в секундах)
DELETE_AFTER = 300  # 5 минут

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

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
        except Exception as e:
            logger.error(f"Ошибка загрузки reviews.json: {e}")
            return []

async def save_reviews(reviews: List[Dict[str, Any]]):
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

# ----------------- Приветствие -----------------
async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chat_member
    new_status = result.new_chat_member.status
    old_status = result.old_chat_member.status
    user = result.new_chat_member.user

    if old_status in [ChatMember.LEFT, ChatMember.KICKED] and new_status == ChatMember.MEMBER:
        msg_text = (
            f"👋 Добро пожаловать в Oplatym.ru!\n\n"
            f"Мы рады видеть вас в нашем чате, пожалуйста ознакомьтесь с предупреждением ниже!\n\n"
            f"‼️ ВАЖНО: ОСТЕРЕГАЙТЕСЬ МОШЕННИКОВ ‼️\n\n"
            f"В последнее время участились случаи мошенничества.\n"
            f"Обращаем ваше внимание: мы никогда не пишем первыми.\n"
            f"Переходите в наши аккаунты только через ссылки, указанные в этом сообщении:\n\n"
            f"🔐 Официальные аккаунты Oplatym.ru\n\n"
            f"Оплата сервисов:\n"
            f"- @OplatymRU\n"
            f"- @ByOplatymRu\n"
            f"- @oplatymManager3\n"
            f"- @OplatymRu4\n\n"
            f"Денежные переводы:\n"
            f"- @oplatym_exchange07\n"
            f"- @Oplatym_exchange20\n\n"
            f"Alipay:\n"
            f"- @CNYExchangeOplatym\n"
            f"- @CNYExchangeOplatym2\n\n"
            f"Рады приветствовать вас, {user.full_name}! 🎉"
        )
        msg = await context.bot.send_message(chat_id=update.effective_chat.id, text=msg_text)
        await asyncio.sleep(DELETE_AFTER)
        await msg.delete()

# ----------------- Команды -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "👋 Бот запущен!\n\n"
        "/id — узнать chat_id\n"
        "/end — отправить все отзывы (только менеджерам)\n\n"
        "Менеджеры могут отправлять клиентам меню для отзыва."
    )
    await asyncio.sleep(DELETE_AFTER)
    await msg.delete()

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(f"Chat ID: {update.message.chat_id}")
    await asyncio.sleep(DELETE_AFTER)
    await msg.delete()

async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in MANAGER_IDS:
        msg = await update.message.reply_text("❌ Нет доступа.")
        await asyncio.sleep(DELETE_AFTER)
        await msg.delete()
        return

    reviews = await load_reviews()
    if not reviews:
        msg = await update.message.reply_text("ℹ️ Отзывов нет.")
        await asyncio.sleep(DELETE_AFTER)
        await msg.delete()
        return

    full = "📣 НОВЫЕ ОТЗЫВЫ:\n\n"
    for i, r in enumerate(reviews, start=1):
        full += f"{i}. От @{r['author_username']}:\n{r['text']}\n\n"

    for chunk in split_message_by_limit(full):
        await context.bot.send_message(chat_id=PUBLIC_CHAT_ID, text=chunk)

    await save_reviews([])
    msg = await update.message.reply_text("✅ Отправлено.")
    await asyncio.sleep(DELETE_AFTER)
    await msg.delete()

# ----------------- Меню отзыва -----------------
async def send_review_menu(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ Оставить отзыв", callback_data="review")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    msg = await context.bot.send_message(
        chat_id=user_id,
        text="Спасибо за покупку! Хотите оставить отзыв?",
        reply_markup=markup,
    )
    await asyncio.sleep(DELETE_AFTER)
    await msg.delete()

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

# ----------------- Обработка текстов -----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        text = update.message.text.strip()
        logger.info(f"Сообщение от {user.id} ({user.full_name}): {text}")

        # триггер для русской фразы "конец"
        if text.lower() == "конец" and user.id in MANAGER_IDS:
            return await end_command(update, context)

        # режим отзыва
        if USER_REVIEW_STATE.get(user.id) == "wait":
            username = user.username or user.first_name
            await add_review(user.id, username, text)
            USER_REVIEW_STATE.pop(user.id, None)
            msg = await update.message.reply_text("Спасибо! Отзыв сохранён.")
            await asyncio.sleep(DELETE_AFTER)
            await msg.delete()
            return

        # автоответчик
        resp = generate_response(text.lower())
        if resp:
            msg = await update.message.reply_text(resp)
            await asyncio.sleep(DELETE_AFTER)
            await msg.delete()
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}")

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(ChatMemberHandler(welcome_member, ChatMemberHandler.CHAT_MEMBER))

    print("🤖 Бот запущен и логирует все сообщения")
    app.run_polling()

if __name__ == "__main__":
    main()

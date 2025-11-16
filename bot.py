import logging
import os
import json
import asyncio
from typing import List, Dict, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ----------------- Настройки -----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
PUBLIC_CHAT_ID = -1002136717768
MANAGER_IDS = {5314493557, 7279244310, 7754541004, 8444260034, 7840997504, 8185132005, 6962444738, 7431538558}

# ----------------- Файлы хранения -----------------
REVIEWS_FILE = "reviews.json"
CLIENTS_FILE = "clients.json"
ORDERS_FILE = "orders.json"
MANAGER_LOGS_FILE = "logs.json"
MANAGER_STATS_FILE = "stats.json"

# ----------------- FSM -----------------
USER_REVIEW_STATE: Dict[int, str] = {}
MANAGER_STATE: Dict[int, str] = {}
MANAGER_TARGET: Dict[int, str] = {}

file_lock = asyncio.Lock()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- Работа с JSON -----------------
async def load_json(filename, default):
    async with file_lock:
        if not os.path.exists(filename):
            return default
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: json.load(open(filename, "r", encoding="utf-8")))

async def save_json(filename, data):
    async with file_lock:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, lambda: json.dump(data, open(filename, "w", encoding="utf-8"), ensure_ascii=False, indent=2))

# ----------------- Отзывы -----------------
async def load_reviews() -> List[Dict[str, Any]]:
    return await load_json(REVIEWS_FILE, [])

async def save_reviews(reviews: List[Dict[str, Any]]):
    await save_json(REVIEWS_FILE, reviews)

async def add_review(author_id: int, author_username: str, text: str):
    reviews = await load_reviews()
    reviews.append({"author_id": author_id, "author_username": author_username, "text": text})
    await save_reviews(reviews)

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

# ----------------- Логи и статистика -----------------
async def log_action(manager_id: int, action: str, target: str = ""):
    logs = await load_json(MANAGER_LOGS_FILE, [])
    logs.append({"manager_id": manager_id, "action": action, "target": target})
    await save_json(MANAGER_LOGS_FILE, logs)
    stats = await load_json(MANAGER_STATS_FILE, {})
    stat = stats.get(str(manager_id), {"clients":0,"orders":0,"errors":0})
    if action == "client_handled": stat["clients"] += 1
    elif action == "order_closed": stat["orders"] += 1
    elif action == "error": stat["errors"] += 1
    stats[str(manager_id)] = stat
    await save_json(MANAGER_STATS_FILE, stats)

# ----------------- Приветствие -----------------
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        username = new_user.username or new_user.first_name
        await update.message.reply_text(
            f"👋 Добро пожаловать в Oplatym.ru!\n\n"
            f"Мы рады видеть вас в нашем чате, пожалуйста ознакомьтесь с предупреждением ниже!\n\n"
            "‼️ ВАЖНО: ОСТЕРЕГАЙТЕСЬ МОШЕННИКОВ ‼️\n\n"
            "В последнее время участились случаи мошенничества.\n"
            "Обращаем ваше внимание: мы никогда не пишем первыми.\n"
            "Переходите в наши аккаунты только через ссылки, указанные в этом сообщении:\n\n"
            "🔐 Официальные аккаунты Oplatym.ru\n\n"
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
            f"Рады приветствовать вас, {username}! 🎉"
        )

# ----------------- Команды -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message or update.effective_message
    await msg.reply_text(
        "👋 Бот запущен!\n\n"
        "/id — узнать chat_id\n"
        "/end — отправить все отзывы (только менеджерам)\n"
        "/manager — открыть панель менеджера"
    )

async def get_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID: {update.message.chat_id}")

async def end_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in MANAGER_IDS:
        return await update.message.reply_text("❌ Нет доступа.")
    reviews = await load_reviews()
    if not reviews:
        return await update.message.reply_text("ℹ️ Отзывов нет.")
    full = "📣 НОВЫЕ ОТЗЫВЫ:\n\n"
    for i, r in enumerate(reviews, start=1):
        full += f"{i}. От @{r['author_username']}:\n{r['text']}\n\n"
    for chunk in split_message_by_limit(full):
        await context.bot.send_message(chat_id=PUBLIC_CHAT_ID, text=chunk)
    await save_reviews([])
    await update.message.reply_text("✅ Отправлено.")

# ----------------- Меню отзывов -----------------
async def send_review_menu(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ Оставить отзыв", callback_data="review")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text="Спасибо за покупку! Хотите оставить отзыв?", reply_markup=markup)

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

# ----------------- Автоответчик -----------------
def generate_response(text: str):
    keys = ["как купить", "как перевести", "как оплатить", "нужно оплатить", "нужно перевести", "нужно купить"]
    if any(k in text for k in keys):
        return ("👋 Уважаемый клиент!\n\n"
                "Обратитесь в один из наших аккаунтов:\n"
                "- @OplatymRU\n- @ByOplatymRu\n- @oplatymManager3\n- @OplatymRu4\n\n"
                "Мы первыми не пишем — остерегайтесь мошенников!")
    return ""

# ----------------- Обработка сообщений -----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text.strip()

    # FSM: менеджер отвечает клиенту
    if MANAGER_STATE.get(user.id) == "replying":
        cid = MANAGER_TARGET[user.id]
        CLIENTS = await load_json(CLIENTS_FILE, {})
        client = CLIENTS[cid]

        await context.bot.send_message(chat_id=int(cid), text=text)
        client["last_message"] = text
        await save_json(CLIENTS_FILE, CLIENTS)

        MANAGER_STATE.pop(user.id)
        MANAGER_TARGET.pop(user.id)
        await update.message.reply_text(f"✅ Сообщение отправлено @{client['username']}")
        return

    # FSM: создание заказа
    if MANAGER_STATE.get(user.id) == "creating_order":
        try:
            client_username, item, price = [x.strip() for x in text.split(",")]
            ORDERS = await load_json(ORDERS_FILE, {})
            oid = str(max([int(k) for k in ORDERS.keys()] + [1000]) + 1)
            ORDERS[oid] = {"client": client_username.lstrip("@"), "item": item, "price": price, "status": "Ожидает оплаты"}
            await save_json(ORDERS_FILE, ORDERS)
            MANAGER_STATE.pop(user.id)
            await update.message.reply_text(f"✅ Заказ #{oid} создан для @{client_username}")
        except:
            await update.message.reply_text("❌ Ошибка формата. Используйте:\n@username, Товар, Сумма")
        return

    # FSM: пользователь пишет отзыв
    if USER_REVIEW_STATE.get(user.id) == "wait":
        username = user.username or user.first_name
        await add_review(user.id, username, text)
        USER_REVIEW_STATE.pop(user.id, None)
        return await update.message.reply_text("Спасибо! Отзыв сохранён.")

    # Триггер для менеджеров
    if text.lower() == "конец" and user.id in MANAGER_IDS:
        return await end_command(update, context)

    # Автоответчик
    resp = generate_response(text.lower())
    if resp:
        await update.message.reply_text(resp)

# ----------------- CRM -----------------
async def manager_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in MANAGER_IDS:
        return await update.message.reply_text("❌ Нет доступа.")
    keyboard = [
        [InlineKeyboardButton("👥 Клиенты в работе", callback_data="crm_clients")],
        [InlineKeyboardButton("🛒 Заказы", callback_data="crm_orders")],
        [InlineKeyboardButton("⚡ Быстрые ответы", callback_data="crm_quick")],
        [InlineKeyboardButton("📊 Статистика", callback_data="crm_stats")]
    ]
    await update.message.reply_text("📊 Панель менеджера Oplatym", reply_markup=InlineKeyboardMarkup(keyboard))

async def crm_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... оставляем все CRM функции как в предыдущем коде ...
    pass  # Для краткости оставляю здесь, вставь все кнопки из предыдущей версии кода

# ----------------- Основной запуск -----------------
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("id", get_chat_id))
    app.add_handler(CommandHandler("end", end_command))
    app.add_handler(CommandHandler("manager", manager_panel))

    # CallbackQuery
    app.add_handler(CallbackQueryHandler(review_buttons))
    app.add_handler(CallbackQueryHandler(crm_buttons))

    # Сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Новые участники
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))

    print("🤖 Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()

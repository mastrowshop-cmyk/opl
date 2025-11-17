# bot.py
import logging
import os
import json
import asyncio
from typing import List, Dict, Any
import random

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

import config

# ----------------- Настройки (из config) -----------------
BOT_TOKEN = config.BOT_TOKEN
PUBLIC_CHAT_ID = config.PUBLIC_CHAT_ID
MANAGER_IDS = config.MANAGER_IDS

REVIEWS_FILE = config.REVIEWS_FILE
CLIENTS_FILE = config.CLIENTS_FILE
ORDERS_FILE = config.ORDERS_FILE
MANAGER_LOGS_FILE = config.MANAGER_LOGS_FILE
MANAGER_STATS_FILE = config.MANAGER_STATS_FILE

# ----------------- FSM / состояния -----------------
USER_REVIEW_STATE: Dict[int, str] = {}
MANAGER_STATE: Dict[int, str] = {}
MANAGER_TARGET: Dict[int, str] = {}

file_lock = asyncio.Lock()

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)


# ----------------- Утилиты для работы с файлами -----------------
async def ensure_data_files():
    """Создаёт папку data и файлы если их нет — безопасно для первого запуска."""
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    defaults = {
        REVIEWS_FILE: [],
        CLIENTS_FILE: {},
        ORDERS_FILE: {},
        MANAGER_LOGS_FILE: [],
        MANAGER_STATS_FILE: {},
    }
    for path, default in defaults.items():
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, ensure_ascii=False, indent=2)


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


# ----------------- Автоудаление сообщений (5 минут) -----------------
AUTO_DELETE_DELAY = 300  # 300 секунд = 5 минут (как ты просил)

async def auto_delete_message(bot, chat_id, message_id, delay=AUTO_DELETE_DELAY):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        # Игнорируем ошибки удаления (нет прав, уже удалено и т.п.)
        pass


# ----------------- Работа с отзывами -----------------
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
    stat = stats.get(str(manager_id), {"clients": 0, "orders": 0, "errors": 0})
    if action == "client_handled":
        stat["clients"] += 1
    elif action == "order_closed":
        stat["orders"] += 1
    elif action == "error":
        stat["errors"] += 1
    stats[str(manager_id)] = stat
    await save_json(MANAGER_STATS_FILE, stats)


# ----------------- Приветствие новых участников (удаляется через 5 минут) -----------------
async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for new_user in update.message.new_chat_members:
        username = new_user.username or new_user.first_name
        text = (
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
        msg = await update.message.reply_text(text)
        # автоудаление приветствия
        asyncio.create_task(auto_delete_message(context.bot, msg.chat_id, msg.message_id))


# ----------------- Команды -----------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "👋 Бот запущен!\n\n"
        "/id — узнать chat_id\n"
        "/end — отправить все отзывы (только менеджерам)\n"
        "/manager — открыть панель менеджера"
    )
    # удаляем инфо о старте через 5 минут (в варианте B просили удалять автоответы и приветствие; я удаляю старт тоже)
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


# ----------------- Меню отзывов -----------------
async def send_review_menu(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⭐ Оставить отзыв", callback_data="review")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
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


# ----------------- Автоответчик (удаляется через 5 минут) -----------------
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


# ----------------- Обработка сообщений (FSM и автоответы) -----------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()

    # FSM: менеджер отвечает клиенту
    if MANAGER_STATE.get(user.id) == "replying":
        cid = MANAGER_TARGET[user.id]
        clients = await load_json(CLIENTS_FILE, {})
        client = clients.get(cid)
        if client:
            try:
                await context.bot.send_message(chat_id=int(cid), text=text)
            except Exception:
                # не удалось отправить клиенту
                await update.message.reply_text("❌ Не удалось отправить сообщение клиенту (возможно клиент не писал боту).")
            client["last_message"] = text
            await save_json(CLIENTS_FILE, clients)
        MANAGER_STATE.pop(user.id, None)
        MANAGER_TARGET.pop(user.id, None)
        await update.message.reply_text(f"✅ Сообщение отправлено @{client.get('username') if client else cid}")
        return

    # FSM: создание заказа
    if MANAGER_STATE.get(user.id) == "creating_order":
        try:
            client_username, item, price = [x.strip() for x in text.split(",")]
            orders = await load_json(ORDERS_FILE, {})
            oid = str(max([int(k) for k in orders.keys()] + [1000]) + 1)
            orders[oid] = {"client": client_username.lstrip("@"), "item": item, "price": price, "status": "Ожидает оплаты"}
            await save_json(ORDERS_FILE, orders)
            MANAGER_STATE.pop(user.id, None)
            await update.message.reply_text(f"✅ Заказ #{oid} создан для @{client_username}")
        except Exception:
            await update.message.reply_text("❌ Ошибка формата. Используйте:\n@username, Товар, Сумма")
        return

    # FSM: режим отзыва
    if USER_REVIEW_STATE.get(user.id) == "wait":
        username = user.username or user.first_name
        await add_review(user.id, username, text)
        USER_REVIEW_STATE.pop(user.id, None)
        msg = await update.message.reply_text("Спасибо! Отзыв сохранён.")
        # не удаляем "Спасибо" — условие B было автоудалять приветствия и автоответы, не все отзывы
        return

    # Триггер для менеджеров: "конец"
    if text.lower() == "конец" and user.id in MANAGER_IDS:
        return await end_command(update, context)

    # Автоответчик (если ключевые слова) — ответ удаляется через 5 минут
    resp = generate_response(text.lower())
    if resp:
        msg = await update.message.reply_text(resp)
        asyncio.create_task(auto_delete_message(context.bot, msg.chat_id, msg.message_id))
        return


# ----------------- CRM: менеджерская панель -----------------
async def manager_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id not in MANAGER_IDS:
        msg = await update.message.reply_text("❌ Нет доступа.")
        asyncio.create_task(auto_delete_message(context.bot, msg.chat_id, msg.message_id))
        return
    keyboard = [
        [InlineKeyboardButton("👥 Клиенты в работе", callback_data="crm_clients")],
        [InlineKeyboardButton("🛒 Заказы", callback_data="crm_orders")],
        [InlineKeyboardButton("⚡ Быстрые ответы", callback_data="crm_quick")],
        [InlineKeyboardButton("📊 Статистика", callback_data="crm_stats")],
    ]
    await update.message.reply_text("📊 Панель менеджера Oplatym", reply_markup=InlineKeyboardMarkup(keyboard))


async def crm_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    data = query.data

    clients = await load_json(CLIENTS_FILE, {})
    orders = await load_json(ORDERS_FILE, {})

    # Просмотр клиентов
    if data == "crm_clients":
        if not clients:
            return await query.edit_message_text("ℹ️ Клиентов нет.")
        text = "👥 Клиенты в работе:\n\n"
        keyboard = []
        for cid, info in clients.items():
            text += f"🔹 @{info.get('username')} — {info.get('status')}\n"
            keyboard.append([InlineKeyboardButton(f"📩 @{info.get('username')}", callback_data=f"client_{cid}")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Действия с клиентом
    elif data.startswith("client_"):
        cid = data.split("_", 1)[1]
        client = clients.get(cid)
        if not client:
            return await query.edit_message_text("❌ Клиент не найден.")
        keyboard = [
            [InlineKeyboardButton("✉️ Ответить", callback_data=f"reply_{cid}")],
            [InlineKeyboardButton("⏸️ Отложить", callback_data=f"hold_{cid}")],
            [InlineKeyboardButton("✅ Завершить", callback_data=f"done_{cid}")],
            [InlineKeyboardButton("⚠️ Мошенник", callback_data=f"scam_{cid}")],
        ]
        text = f"👤 Клиент: @{client.get('username')}\nСтатус: {client.get('status')}\nПоследнее сообщение: {client.get('last_message','')}"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Начать ответ (FSM)
    elif data.startswith("reply_"):
        cid = data.split("_", 1)[1]
        client = clients.get(cid)
        if not client:
            return await query.edit_message_text("❌ Клиент не найден.")
        MANAGER_STATE[user.id] = "replying"
        MANAGER_TARGET[user.id] = cid
        await query.edit_message_text(f"✏️ Напишите ответ клиенту @{client.get('username')}")

    # Отложить / завершить / мошенник
    elif data.startswith(("hold_", "done_", "scam_")):
        action, cid = data.split("_", 1)
        client = clients.get(cid)
        if not client:
            return await query.edit_message_text("❌ Клиент не найден.")
        if action == "hold":
            client["status"] = "отложен"
            await log_action(user.id, "client_handled", cid)
        elif action == "done":
            client["status"] = "завершен"
            await log_action(user.id, "client_handled", cid)
        elif action == "scam":
            client["status"] = "мошенник"
            await log_action(user.id, "error", cid)
        await save_json(CLIENTS_FILE, clients)
        await query.edit_message_text(f"✅ Действие выполнено с клиентом @{client.get('username')}")

    # Заказы: список + кнопка новый заказ
    elif data == "crm_orders":
        text = "🛒 Заказы:\n\n"
        keyboard = []
        if orders:
            for oid, order in orders.items():
                text += f"#{oid} — {order.get('item','?')} — {order.get('status','Ожидает оплаты')}\n"
                keyboard.append([InlineKeyboardButton(f"#{oid}", callback_data=f"order_{oid}")])
        keyboard.append([InlineKeyboardButton("➕ Новый заказ", callback_data="order_new")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Обработка конкретного заказа / создание
    elif data.startswith("order_"):
        oid = data.split("_", 1)[1]
        if oid == "new":
            MANAGER_STATE[user.id] = "creating_order"
            await query.edit_message_text("✏️ Введите данные нового заказа в формате:\n@username, Товар, Сумма")
            return
        order = orders.get(oid)
        if not order:
            return await query.edit_message_text("❌ Заказ не найден.")
        keyboard = [
            [InlineKeyboardButton("✅ Завершить", callback_data=f"close_{oid}")],
            [InlineKeyboardButton("❌ Отменить", callback_data=f"cancel_{oid}")],
        ]
        text = f"🛒 Заказ #{oid}\nКлиент: @{order.get('client')}\nТовар: {order.get('item')}\nСумма: {order.get('price')}\nСтатус: {order.get('status')}"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    # Закрыть / отменить заказ
    elif data.startswith(("close_", "cancel_")):
        action, oid = data.split("_", 1)
        order = orders.get(oid)
        if not order:
            return await query.edit_message_text("❌ Заказ не найден.")
        if action == "close":
            order["status"] = "Закрыт"
            await log_action(user.id, "order_closed", oid)
        else:
            order["status"] = "Отменён"
            await log_action(user.id, "error", oid)
        await save_json(ORDERS_FILE, orders)
        await query.edit_message_text(f"✅ Заказ #{oid} обновлён: {order['status']}")

    # Быстрые ответы
    elif data == "crm_quick":
        quicks = ["Как оплатить?", "Как работает подписка?", "Гарантия?", "Мануал по Alipay", "Разблокировка платежа"]
        text = "⚡ Быстрые ответы:\n\n" + "\n".join(f"- {q}" for q in quicks)
        await query.edit_message_text(text)

    # Статистика
    elif data == "crm_stats":
        stats = await load_json(MANAGER_STATS_FILE, {})
        stat = stats.get(str(user.id), {"clients": 0, "orders": 0, "errors": 0})
        text = (
            f"📊 Статистика менеджера @{user.username}:\n"
            f"- Клиентов обработано: {stat['clients']}\n"
            f"- Заказов закрыто: {stat['orders']}\n"
            f"- Ошибок: {stat['errors']}"
        )
        await query.edit_message_text(text)

    else:
        await query.edit_message_text("Неподдерживаемая команда.")


# ----------------- Startup / main -----------------
def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден! Установите переменную окружения BOT_TOKEN.")
        return

    # Убедиться, что файлы существуют
    import asyncio as _aio
    _aio.get_event_loop().run_until_complete(ensure_data_files())

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
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Бот запущен (polling)")
    app.run_polling()


if __name__ == "__main__":
    main()

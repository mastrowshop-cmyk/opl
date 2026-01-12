import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

ADMINS = [481650304, 7668402802]

OFFICIAL_USERS = {
    "@ByOplatymRu": "Оплата сервисов",
    "@OplatymRU": "Оплата сервисов",
    "@oplatymManager3": "Оплата сервисов",
    "@OplatymRu4": "Оплата сервисов",
    "@oplatym_exchange07": "Денежные переводы",
    "@Oplatym_exchange20": "Денежные переводы",
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DELETE_AFTER = 120

# ==================== СТАТИСТИКА ====================
STATS = {
    "messages_processed": 0,
    "keywords_triggered": 0,
    "welcome_messages": 0,
    "bans_issued": 0,
    "kicks_issued": 0,
    "admins_actions": 0,
    "checks_performed": 0
}

async def delete_later(message):
    await asyncio.sleep(DELETE_AFTER)
    try:
        await message.delete()
    except:
        pass

KEYWORD_TEXT = (
    "Уважаемый клиент, обратитесь в один из аккаунтов:\n"
    "🔐 Официальные аккаунты Oplatym.ru\n\n"
    "Оплата сервисов:\n"
    "-@OplatymRU\n-@ByOplatymRu\n-@oplatymManager3\n-@OplatymRu4\n\n"
    "Денежные переводы:\n"
    "-@oplatym_exchange07\n-@oplatym_exchange20"
)

PAY_GUIDE = (
    "⚙️ Мы делаем процесс оплаты максимально простым:\n\n"
    "➜ Оплата по ссылке в нашей платёжной системе;\n"
    "➜ Мы переводим средства на зарубежный счёт и выдаём реквизиты;\n"
    "➜ Этой картой вы сможете оплатить нужный сервис;\n"
    "➜ VPN нужен только если вы в РФ;\n"
    "➜ Возможна оплата Login+Password — это нормально."
)

GPT_TEXT = (
    "⚙️ Варианты выдачи товара:\n"
    "➜ Оплата по платёжной ссылке\n"
    "➜ Login+Password\n"
)

SUNO_TEXT = "Информация по Suno…"

GOOGLE_TEXT = (
    "Для оплаты нужно удалить российский платёжный профиль "
    "и создать европейский. Мы дадим инструкцию — аккаунт не пострадает."
)

WELCOME_TEXT = (
    "👋 Добро пожаловать в Oplatym.ru!\n\n"
    "‼️ ОСТЕРЕГАЙТЕСЬ МОШЕННИКОВ ‼️\n"
    "Мы никогда не пишем первыми — проверяйте аккаунты:\n\n"
    "Оплата:\n"
    "-@OplatymRU\n-@ByOplatymRu\n-@oplatymManager3\n-@OplatymRu4\n\n"
    "Переводы:\n"
    "-@oplatym_exchange07\n-@oplatym_exchange20\n\n"
    "Рады приветствовать вас, {username}! 🎉"
)

MAIN_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔐 Официальные аккаунты", callback_data="accounts")],
    [InlineKeyboardButton("💳 Как оплатить", callback_data="how_pay")],
    [InlineKeyboardButton("🧧 Alipay", callback_data="alipay")],  # Кнопка сохранена
])

PAY_BUTTONS = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("ChatGPT", callback_data="pay_gpt"),
        InlineKeyboardButton("Suno", callback_data="pay_suno"),
        InlineKeyboardButton("Google", callback_data="pay_google")
    ]
])

ADMIN_PANEL = InlineKeyboardMarkup([
    [InlineKeyboardButton("📋 Список админов", callback_data="admin_list")],
    [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
    [InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add")],
    [InlineKeyboardButton("📝 Изменить тексты", callback_data="admin_edit")],
])

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        STATS["welcome_messages"] += 1
        name = user.first_name or "клиент"
        msg = await update.message.reply_text(
            WELCOME_TEXT.format(username=name),
            reply_markup=MAIN_BUTTONS
        )
        asyncio.create_task(delete_later(msg))

async def check_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    STATS["checks_performed"] += 1
    if text in OFFICIAL_USERS:
        msg = await update.message.reply_text("✅ Вы общаетесь с официальным аккаунтом.")
    else:
        msg = await update.message.reply_text("‼⚠ Если вам написали с этого аккаунта *НЕМЕДЛЕННО ПРЕКРАТИТЕ ОБЩЕНИЕ ЭТО МОШЕННИКИ!* ⚠‼")
    asyncio.create_task(delete_later(msg))

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATS["checks_performed"] += 1
    if not context.args:
        msg = await update.message.reply_text("Использование: /check @username")
        return asyncio.create_task(delete_later(msg))
    username = context.args[0].strip()
    if username in OFFICIAL_USERS:
        msg = await update.message.reply_text("✅ Это официальный аккаунт.")
    else:
        msg = await update.message.reply_text("‼⚠ Если вам написали с этого аккаунта НЕМЕЛОЕННО ПРЕКРАТИТЕ ОБЩЕНИЕ ЭТО МОШЕННИКИ! ⚠‼")
    asyncio.create_task(delete_later(msg))

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("Нет прав.")
    
    STATS["admins_actions"] += 1
    chat = update.effective_chat
    
    # Случай 1: Бан по ответу на сообщение
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        try:
            await chat.ban_member(user_id)
            STATS["bans_issued"] += 1
            reason = " ".join(context.args) if context.args else "без указания причины"
            msg = await update.message.reply_text(
                f"🚫 Пользователь {update.message.reply_to_message.from_user.full_name} "
                f"(ID: {user_id}) забанен. Причина: {reason}"
            )
            await update.message.reply_to_message.delete()
            return asyncio.create_task(delete_later(msg))
        except Exception as e:
            return await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Случай 2: Бан по username (@username)
    if context.args and context.args[0].startswith('@'):
        username = context.args[0].strip()
        try:
            # Получаем информацию о пользователе по username
            # В реальном боте нужно получить user_id через API или другие методы
            # Это упрощённая реализация
            reason = " ".join(context.args[1:]) if len(context.args) > 1 else "без указания причины"
            msg = await update.message.reply_text(
                f"🚫 Для бана по username @{username} боту нужны специальные права.\n"
                f"Используйте:\n"
                f"1. Ответьте на сообщение пользователя командой /ban\n"
                f"2. Используйте /ban <user_id> [причина]\n"
                f"3. Или попросите пользователя написать что-то в чат, затем ответьте"
            )
            return asyncio.create_task(delete_later(msg))
        except Exception as e:
            return await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Случай 3: Бан по ID (старая функциональность)
    if not context.args:
        return await update.message.reply_text(
            "Использование:\n"
            "1. /ban [причина] - в ответ на сообщение\n"
            "2. /ban @username [причина]\n"
            "3. /ban <user_id> [причина]"
        )
    
    try:
        uid = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "без указания причины"
        await chat.ban_member(uid)
        STATS["bans_issued"] += 1
        msg = await update.message.reply_text(f"🚫 Пользователь {uid} забанен. Причина: {reason}")
        asyncio.create_task(delete_later(msg))
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("Нет прав.")
    
    STATS["admins_actions"] += 1
    
    # Разбан по ответу на сообщение
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        try:
            await update.effective_chat.unban_member(user_id)
            msg = await update.message.reply_text(
                f"✅ Пользователь {update.message.reply_to_message.from_user.full_name} "
                f"(ID: {user_id}) разбанен."
            )
            return asyncio.create_task(delete_later(msg))
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Разбан по ID
    if not context.args:
        return await update.message.reply_text(
            "Использование:\n"
            "1. /unban - в ответ на сообщение\n"
            "2. /unban <user_id>"
        )
    
    try:
        uid = int(context.args[0])
        await update.effective_chat.unban_member(uid)
        msg = await update.message.reply_text(f"✅ Пользователь {uid} разбанен.")
        asyncio.create_task(delete_later(msg))
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("Нет прав.")
    
    STATS["admins_actions"] += 1
    STATS["kicks_issued"] += 1
    
    # Кик по ответу на сообщение
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        try:
            await update.effective_chat.ban_member(user_id)
            await update.effective_chat.unban_member(user_id)
            reason = " ".join(context.args) if context.args else "без указания причины"
            msg = await update.message.reply_text(
                f"👢 Пользователь {update.message.reply_to_message.from_user.full_name} "
                f"(ID: {user_id}) кикнут. Причина: {reason}"
            )
            await update.message.reply_to_message.delete()
            return asyncio.create_task(delete_later(msg))
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Кик по ID
    if not context.args:
        return await update.message.reply_text(
            "Использование:\n"
            "1. /kick [причина] - в ответ на сообщение\n"
            "2. /kick <user_id> [причина]"
        )
    
    try:
        uid = int(context.args[0])
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "без указания причины"
        await update.effective_chat.ban_member(uid)
        await update.effective_chat.unban_member(uid)
        msg = await update.message.reply_text(f"👢 Пользователь {uid} кикнут. Причина: {reason}")
        asyncio.create_task(delete_later(msg))
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("Нет прав.")
    
    STATS["admins_actions"] += 1
    
    if not update.message.reply_to_message:
        return await update.message.reply_text("Нужно ответить на сообщение.")
    try:
        await update.message.reply_to_message.delete()
        msg = await update.message.reply_text("🗑 Сообщение удалено.")
        asyncio.create_task(delete_later(msg))
    except Exception as e:
        await update.message.reply_text(str(e))

async def chatinfo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    member = await chat.get_member(update.effective_user.id)
    if isinstance(member, ChatMemberOwner):
        role = "Создатель"
    elif isinstance(member, ChatMemberAdministrator):
        role = "Админ"
    else:
        role = "Участник"
    text = (
        f"📌 Информация о чате:\n\n"
        f"Название: {chat.title}\n"
        f"ID: {chat.id}\n"
        f"Тип: {chat.type}\n"
        f"Ваша роль: {role}"
    )
    await update.message.reply_text(text)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        out = await update.message.reply_text("⛔ У вас нет прав администратора.")
        return asyncio.create_task(delete_later(out))
    
    STATS["admins_actions"] += 1
    out = await update.message.reply_text("🔧 Панель администратора", reply_markup=ADMIN_PANEL)
    asyncio.create_task(delete_later(out))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return
    
    text = (
        f"📊 **СТАТИСТИКА БОТА**\n\n"
        f"📨 Сообщений обработано: {STATS['messages_processed']}\n"
        f"🔑 Ключевых слов сработало: {STATS['keywords_triggered']}\n"
        f"👋 Приветствий отправлено: {STATS['welcome_messages']}\n"
        f"🚫 Выдано банов: {STATS['bans_issued']}\n"
        f"👢 Выдано киков: {STATS['kicks_issued']}\n"
        f"🛡 Действий админов: {STATS['admins_actions']}\n"
        f"✅ Проверок аккаунтов: {STATS['checks_performed']}\n\n"
        f"👑 Активных админов: {len(ADMINS)}\n"
        f"📅 Обновлено: {len(STATS)} показателей"
    )
    await update.message.reply_text(text)

async def settext_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        out = await update.message.reply_text("Нет прав.")
        return asyncio.create_task(delete_later(out))
    
    STATS["admins_actions"] += 1
    
    if not context.args:
        out = await update.message.reply_text(
            "Использование:\n"
            "/settext keywords\n"
            "/settext gpt\n"
            "/settext suno\n"
            "/settext google\n"
            "/settext pay"
        )
        return asyncio.create_task(delete_later(out))
    key = context.args[0].lower()
    allowed = {"keywords", "gpt", "suno", "google", "pay"}
    if key not in allowed:
        out = await update.message.reply_text("Неизвестный блок текста.")
        return asyncio.create_task(delete_later(out))
    context.user_data["edit"] = key
    out = await update.message.reply_text(f"Отправьте новый текст для {key.upper()}")
    asyncio.create_task(delete_later(out))

async def settext_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("edit")
    if not key:
        return
    global KEYWORD_TEXT, GPT_TEXT, SUNO_TEXT, GOOGLE_TEXT, PAY_GUIDE
    value = update.message.text
    if key == "keywords":
        KEYWORD_TEXT = value
    elif key == "gpt":
        GPT_TEXT = value
    elif key == "suno":
        SUNO_TEXT = value
    elif key == "google":
        GOOGLE_TEXT = value
    elif key == "pay":
        PAY_GUIDE = value
    context.user_data.pop("edit", None)
    out = await update.message.reply_text("✔ Текст обновлён!")
    asyncio.create_task(delete_later(out))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    STATS["keywords_triggered"] += 1
    
    if d == "accounts":
        formatted = "\n".join(f"{u} — {v}" for u, v in OFFICIAL_USERS.items())
        out = await q.message.reply_text("Официальные аккаунты:\n" + formatted)
    elif d == "how_pay":
        out = await q.message.reply_text(PAY_GUIDE, reply_markup=PAY_BUTTONS)
    elif d == "alipay":
        # Кнопка сохранена, но функциональность удалена
        out = await q.message.reply_text("ℹ️ Информация по Alipay временно недоступна.")
    elif d == "pay_gpt":
        out = await q.message.reply_text(GPT_TEXT)
    elif d == "pay_suno":
        out = await q.message.reply_text(SUNO_TEXT)
    elif d == "pay_google":
        out = await q.message.reply_text(GOOGLE_TEXT)
    elif d == "admin_list":
        admin_list = "\n".join([f"• {admin_id}" for admin_id in ADMINS])
        out = await q.message.reply_text(f"📋 Список админов:\n{admin_list}")
    elif d == "stats":
        text = (
            f"📊 **СТАТИСТИКА**\n\n"
            f"📨 Сообщений: {STATS['messages_processed']}\n"
            f"🚫 Банов: {STATS['bans_issued']}\n"
            f"👑 Админов: {len(ADMINS)}\n"
            f"✅ Проверок: {STATS['checks_performed']}"
        )
        out = await q.message.reply_text(text)
    elif d == "admin_add":
        context.user_data["wait_admin_id"] = True
        out = await q.message.reply_text("Введите ID пользователя, которого хотите сделать админом:")
    elif d == "admin_edit":
        out = await q.message.reply_text(
            "📝 Изменить текст:\n"
            "/settext keywords\n/settext gpt\n/settext suno\n/settext google\n/settext pay"
        )
    asyncio.create_task(delete_later(out))

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    STATS["messages_processed"] += 1
    msg = update.message
    if not msg or not msg.text:
        return
    text = msg.text.strip()
    low = text.lower()
    
    if update.effective_user.id in ADMINS and context.user_data.get("wait_admin_id"):
        try:
            uid = int(text)
            if uid not in ADMINS:
                ADMINS.append(uid)
                STATS["admins_actions"] += 1
                out = await msg.reply_text(f"✅ Админ добавлен: {uid}")
            else:
                out = await msg.reply_text("⚠ Этот пользователь уже админ.")
        except:
            out = await msg.reply_text("❌ ID должен быть числом.")
        context.user_data.pop("wait_admin_id")
        return asyncio.create_task(delete_later(out))
    
    if update.effective_user.id in ADMINS and context.user_data.get("edit"):
        return await settext_apply(update, context)
    
    if text.startswith("@") and " " not in text:
        return await check_username(update, context)
    
    if "как купить" in low or "как оплатить" in low or "как перевести" in low:
        STATS["keywords_triggered"] += 1
        out = await msg.reply_text(KEYWORD_TEXT)
        return asyncio.create_task(delete_later(out))

def main():
    if not TOKEN:
        print("❌ BOT_TOKEN не найден!")
        return
    app = Application.builder().token(TOKEN).build()
    
    # Команды админов
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("kick", kick_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("chatinfo", chatinfo_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("settext", settext_start))
    app.add_handler(CommandHandler("check", check_command))
    
    # Обработчики сообщений
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, text_router))
    
    print("🤖 Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()

import logging
import os
import asyncio
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

TOKEN = os.getenv("BOT_TOKEN")

ADMINS = [481650304, 7668402802]

OFFICIAL_USERS = {
    "@ByOplatymRu": "Оплата сервисов",
    "@OplatymRU": "Оплата сервисов",
    "@oplatymManager3": "Оплата сервисов",
    "@OplatymRu4": "Оплата сервисов",
    "@oplatym_exchange07": "Денежные переводы",
    "@Oplatym_exchange20": "Денежные переводы",
    "@CNYExchangeOplatym": "Алипэй",
    "@CNYExchangeOplatym2": "Алипэй",
}

GROUP_ID = -1000000000000

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DELETE_AFTER = 120

async def delete_later(msg):
    await asyncio.sleep(DELETE_AFTER)
    try:
        await msg.delete()
    except:
        pass

KEYWORD_TEXT = (
    "Уважаемый клиент, обратитесь в один из аккаунтов:\n"
    "🔐 Официальные аккаунты Oplatym.ru\n\n"
    "Оплата сервисов:\n"
    "-@OplatymRU\n-@ByOplatymRu\n-@oplatymManager3\n-@OplatymRu4\n\n"
    "Денежные переводы:\n"
    "-@oplatym_exchange07\n-@oplatym_exchange20\n\n"
    "Alipay:\n"
    "-@CNYExchangeOplatym\n-@CNYExchangeOplatym2"
)

PAY_GUIDE = (
    "⚙️ Мы делаем процесс оплаты максимально простым:\n\n"
    "➜ Оплата по ссылке;\n"
    "➜ Мы переводим средства на зарубежный счёт;\n"
    "➜ Этой картой можно платить;\n"
    "➜ VPN нужен только если вы в РФ;\n"
    "➜ Login+Password — нормальный вариант."
)

GPT_TEXT = "Варианты выдачи:\n➜ Оплата по ссылке\n➜ Login+Password"
SUNO_TEXT = "Информация по Suno…"
GOOGLE_TEXT = "Удалите российский профиль и создайте европейский."
ALIPAY_TEXT = "Alipay/WeChat — курсы и комиссии..."

WELCOME_TEXT = (
    "👋 Добро пожаловать!\n\n"
    "‼️ Осторожно, мошенники!‼️\n"
    "Мы первыми не пишем. Проверяйте аккаунты.\n"
    "Рады приветствовать, {username}!"
)

HOURLY_MESSAGES = [
    "Уважаемые клиенты, Oplatym.ru\n\n🔒 Если вам написали в личные сообщения — блокируйте. Это мошенники.",
    "Уважаемые клиенты, Oplatym.ru\n\n📃 Наши менеджеры первыми не пишут. Официальные аккаунты — в закрепе."
]

MAIN_BUTTONS = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔐 Официальные аккаунты", callback_data="accounts")],
    [InlineKeyboardButton("💳 Как оплатить", callback_data="how_pay")],
    [InlineKeyboardButton("🧧 Alipay", callback_data="alipay")],
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
    [InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add")],
    [InlineKeyboardButton("📝 Изменить тексты", callback_data="admin_edit")],
])

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        name = user.first_name or "клиент"
        msg = await update.message.reply_text(
            WELCOME_TEXT.format(username=name),
            reply_markup=MAIN_BUTTONS
        )
        asyncio.create_task(delete_later(msg))

async def check_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text in OFFICIAL_USERS:
        msg = await update.message.reply_text("Официальный аккаунт.")
    else:
        msg = await update.message.reply_text("Не официальный!")
    asyncio.create_task(delete_later(msg))

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        out = await update.message.reply_text("Использование: /check @username")
        return asyncio.create_task(delete_later(out))
    username = context.args[0]
    if username in OFFICIAL_USERS:
        out = await update.message.reply_text("Официальный.")
    else:
        out = await update.message.reply_text("Не официальный.")
    asyncio.create_task(delete_later(out))

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("Нет прав.")
    try:
        uid = int(context.args[0])
        await update.effective_chat.ban_member(uid)
        out = await update.message.reply_text(f"{uid} заблокирован.")
        asyncio.create_task(delete_later(out))
    except:
        await update.message.reply_text("Ошибка.")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("Нет прав.")
    try:
        uid = int(context.args[0])
        await update.effective_chat.unban_member(uid)
        out = await update.message.reply_text(f"{uid} разбанен.")
        asyncio.create_task(delete_later(out))
    except:
        await update.message.reply_text("Ошибка.")

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("Нет прав.")
    try:
        uid = int(context.args[0])
        await update.effective_chat.ban_member(uid)
        await update.effective_chat.unban_member(uid)
        out = await update.message.reply_text(f"{uid} кикнут.")
        asyncio.create_task(delete_later(out))
    except:
        await update.message.reply_text("Ошибка.")

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("Нет прав.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("Нужно ответить на сообщение.")
    try:
        await update.message.reply_to_message.delete()
        out = await update.message.reply_text("Удалено.")
        asyncio.create_task(delete_later(out))
    except:
        await update.message.reply_text("Ошибка.")

async def hourly_task(bot):
    while True:
        msg = random.choice(HOURLY_MESSAGES)
        try:
            await bot.send_message(GROUP_ID, msg)
        except:
            pass
        await asyncio.sleep(3600)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        out = await update.message.reply_text("Нет прав.")
        return asyncio.create_task(delete_later(out))
    out = await update.message.reply_text("Панель администратора", reply_markup=ADMIN_PANEL)
    asyncio.create_task(delete_later(out))

async def settext_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        out = await update.message.reply_text("Нет прав.")
        return asyncio.create_task(delete_later(out))
    if not context.args:
        out = await update.message.reply_text(
            "/settext keywords\n/settext gpt\n/settext suno\n/settext google\n/settext alipay\n/settext pay"
        )
        return asyncio.create_task(delete_later(out))
    key = context.args[0].lower()
    allowed = {"keywords", "gpt", "suno", "google", "alipay", "pay"}
    if key not in allowed:
        out = await update.message.reply_text("Неизвестный блок.")
        return asyncio.create_task(delete_later(out))
    context.user_data["edit"] = key
    out = await update.message.reply_text(f"Отправьте текст для {key.upper()}")
    asyncio.create_task(delete_later(out))

async def settext_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("edit")
    if not key:
        return
    global KEYWORD_TEXT, GPT_TEXT, SUNO_TEXT, GOOGLE_TEXT, ALIPAY_TEXT, PAY_GUIDE
    value = update.message.text
    if key == "keywords":
        KEYWORD_TEXT = value
    elif key == "gpt":
        GPT_TEXT = value
    elif key == "suno":
        SUNO_TEXT = value
    elif key == "google":
        GOOGLE_TEXT = value
    elif key == "alipay":
        ALIPAY_TEXT = value
    elif key == "pay":
        PAY_GUIDE = value
    context.user_data.pop("edit", None)
    out = await update.message.reply_text("Обновлено.")
    asyncio.create_task(delete_later(out))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    if d == "accounts":
        formatted = "\n".join(f"{u} — {v}" for u, v in OFFICIAL_USERS.items())
        out = await q.message.reply_text("Официальные аккаунты:\n" + formatted)
    elif d == "how_pay":
        out = await q.message.reply_text(PAY_GUIDE, reply_markup=PAY_BUTTONS)
    elif d == "alipay":
        out = await q.message.reply_text(ALIPAY_TEXT)
    elif d == "pay_gpt":
        out = await q.message.reply_text(GPT_TEXT)
    elif d == "pay_suno":
        out = await q.message.reply_text(SUNO_TEXT)
    elif d == "pay_google":
        out = await q.message.reply_text(GOOGLE_TEXT)
    elif d == "admin_list":
        out = await q.message.reply_text("\n".join(str(a) for a in ADMINS))
    elif d == "admin_add":
        context.user_data["wait_admin_id"] = True
        out = await q.message.reply_text("Введите ID:")
    elif d == "admin_edit":
        out = await q.message.reply_text(
            "/settext keywords\n/settext gpt\n/settext suno\n/settext google\n/settext alipay\n/settext pay"
        )
    asyncio.create_task(delete_later(out))

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                out = await msg.reply_text(f"Админ добавлен: {uid}")
            else:
                out = await msg.reply_text("Уже админ.")
        except:
            out = await msg.reply_text("Неверный ID.")
        context.user_data.pop("wait_admin_id")
        return asyncio.create_task(delete_later(out))
    if update.effective_user.id in ADMINS and context.user_data.get("edit"):
        return await settext_apply(update, context)
    if text.startswith("@") and " " not in text:
        return await check_username(update, context)
    if "как купить" in low or "как оплатить" in low or "как перевести" in low:
        out = await msg.reply_text(KEYWORD_TEXT)
        return asyncio.create_task(delete_later(out))

async def runner():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("kick", kick_command))
    app.add_handler(CommandHandler("delete", delete_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("settext", settext_start))
    app.add_handler(CommandHandler("check", check_command))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, text_router))
    asyncio.create_task(hourly_task(app.bot))
    await app.run_polling()

def main():
    asyncio.run(runner())

if __name__ == "__main__":
    main()

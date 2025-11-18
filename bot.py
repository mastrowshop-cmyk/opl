import logging
import os
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ===================== НАСТРОЙКИ =====================

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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DELETE_AFTER = 120  # 2 минуты

async def delete_later(msg):
    await asyncio.sleep(DELETE_AFTER)
    try:
        await msg.delete()
    except:
        pass

# ===================== ТЕКСТЫ =====================

KEYWORD_TEXT = (
    "Уважаемый клиент, обратитесь в один из аккаунтов:\n"
    "🔐 Официальные аккаунты Oplatym.ru\n\n"
    "Оплата сервисов:\n"
    "-@OplatymRU\n-@ByOplatymRu\n-@oplatymManager3\n-@OplatymRu4\n\n"
    "Денежные переводы:\n"
    "-@oplatym_exchange07\n-@Oplatym_exchange20\n\n"
    "Alipay:\n"
    "-@CNYExchangeOplatym\n-@CNYExchangeOplatym2"
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

ALIPAY_TEXT = (
    "AliPay & WeChat\n"
    "Курс: 18.11.2025\n\n"
    "100–1000¥ — 12.60₽ / ¥\n"
    "1000–3000¥ — 12.50₽ / ¥\n"
    "3000–10000¥ — 12.40₽ / ¥\n\n"
    "USDT курс:\n"
    "6.86¥ / 6.91¥ / 6.96¥\n\n"
    "Комиссии:\n"
    "до 9999₽ — 7%\n"
    "10 000–200 000₽ — 4%\n"
    "200 000₽+ — договорная\n\n"
    "Помогаем с выводом юаней в рубли."
)

# ===================== КНОПКИ =====================

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

# ===================== ПРИВЕТСТВИЕ =====================

WELCOME_TEXT = (
    "👋 Добро пожаловать в Oplatym.ru!\n\n"
    "‼️ ОСТЕРЕГАЙТЕСЬ МОШЕННИКОВ ‼️\n"
    "Мы никогда не пишем первыми — проверяйте аккаунты:\n\n"
    "Оплата:\n"
    "-@OplatymRU\n-@ByOplatymRu\n-@oplatymManager3\n-@OplatymRu4\n\n"
    "Переводы:\n"
    "-@oplatym_exchange07\n-@oplatym_exchange20\n\n"
    "Alipay:\n"
    "-@CNYExchangeOplatym\n-@CNYExchangeOplatym2\n\n"
    "Рады приветствовать вас, {username}! 🎉"
)

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие новых пользователей"""
    for user in update.message.new_chat_members:
        name = user.first_name or "клиент"

        try:
            with open("welcome.gif", "rb") as f:
                await update.message.reply_animation(f)
        except:
            pass

        msg = await update.message.reply_text(
            WELCOME_TEXT.format(username=name),
            reply_markup=MAIN_BUTTONS
        )
        asyncio.create_task(delete_later(msg))

# ===================== ПРОВЕРКА USERNAME =====================

async def check_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text in OFFICIAL_USERS:
        msg = await update.message.reply_text("✅ Вы общаетесь с официальным аккаунтом.")
    else:
        msg = await update.message.reply_text("‼⚠ ВНИМАНИЕ! ЭТО МОШЕННИК! ⚠‼")

    asyncio.create_task(delete_later(msg))

# ===================== ОБРАБОТКА КНОПОК =====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    d = q.data

    if d == "accounts":
        formatted = "\n".join(f"{u} — {v}" for u, v in OFFICIAL_USERS.items())
        msg = await q.message.reply_text("Официальные аккаунты:\n" + formatted)

    elif d == "how_pay":
        msg = await q.message.reply_text(PAY_GUIDE, reply_markup=PAY_BUTTONS)

    elif d == "alipay":
        msg = await q.message.reply_text(ALIPAY_TEXT)

    elif d == "pay_gpt":
        msg = await q.message.reply_text(GPT_TEXT)

    elif d == "pay_suno":
        msg = await q.message.reply_text(SUNO_TEXT)

    elif d == "pay_google":
        msg = await q.message.reply_text(GOOGLE_TEXT)

    asyncio.create_task(delete_later(msg))

# ===================== АДМИНКА =====================

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        msg = await update.message.reply_text("⛔ Нет прав.")
        return asyncio.create_task(delete_later(msg))

    if not context.args:
        msg = await update.message.reply_text("Использование: /addadmin ID")
        return asyncio.create_task(delete_later(msg))

    try:
        uid = int(context.args[0])
        if uid not in ADMINS:
            ADMINS.append(uid)
        msg = await update.message.reply_text(f"✅ Добавлен админ: {uid}")
    except:
        msg = await update.message.reply_text("ID должен быть числом.")

    asyncio.create_task(delete_later(msg))

async def settext_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        msg = await update.message.reply_text("⛔ Нет прав.")
        return asyncio.create_task(delete_later(msg))

    if not context.args:
        msg = await update.message.reply_text(
            "Использование:\n"
            "/settext keywords\n"
            "/settext gpt\n"
            "/settext suno\n"
            "/settext google\n"
            "/settext alipay\n"
            "/settext pay\n"
        )
        return asyncio.create_task(delete_later(msg))

    key = context.args[0].lower()
    allowed = {"keywords", "gpt", "suno", "google", "alipay", "pay"}

    if key not in allowed:
        msg = await update.message.reply_text("Неизвестный блок текста.")
        return asyncio.create_task(delete_later(msg))

    context.user_data["edit"] = key
    msg = await update.message.reply_text(f"Отправьте НОВЫЙ текст для {key.upper()}")
    asyncio.create_task(delete_later(msg))

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

    msg = await update.message.reply_text("✔ Текст обновлён!")
    asyncio.create_task(delete_later(msg))

# ===================== ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ =====================

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return

    text = msg.text.strip()
    low = text.lower()

    # админ редактирует текст
    if update.effective_user.id in ADMINS and context.user_data.get("edit"):
        return await settext_apply(update, context)

    # проверка username
    if text.startswith("@") and " " not in text:
        return await check_username(update, context)

    # ключевые слова
    if (
        "как купить" in low
        or "как оплатить" in low
        or "как перевести" in low
    ):
        answer = await msg.reply_text(KEYWORD_TEXT)
        return asyncio.create_task(delete_later(answer))

# ===================== MAIN =====================

def main():
    if not TOKEN:
        print("❌ BOT_TOKEN не найден!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CommandHandler("settext", settext_start))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new_member))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, text_router))

    print("🤖 Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()

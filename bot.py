import logging
import os

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
    "-@oplatym_exchange07\n-@Oplatym_exchange20\n\n"
    "Alipay:\n"
    "-@CNYExchangeOplatym\n-@CNYExchangeOplatym2\n\n"
    "Рады приветствовать вас, {username}! 🎉"
)

async def welcome_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие новых людей"""
    for user in update.message.new_chat_members:
        name = user.first_name or "клиент"

        try:
            with open("welcome.gif", "rb") as f:
                await update.message.reply_animation(f)
        except:
            pass

        await update.message.reply_text(
            WELCOME_TEXT.format(username=name),
            reply_markup=MAIN_BUTTONS
        )

# ===================== ПРОВЕРКА USERNAME =====================

async def check_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.startswith("@"):
        return

    if text in OFFICIAL_USERS:
        await update.message.reply_text("✅ Вы общаетесь с официальным аккаунтом.")
    else:
        await update.message.reply_text(
            "‼⚠ ВНИМАНИЕ! ЭТО НЕ ОФИЦИАЛЬНЫЙ АККАУНТ — ПРЕКРАТИТЕ ОБЩЕНИЕ! ⚠‼"
        )

# ===================== ОБРАБОТКА КНОПОК =====================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    d = q.data

    if d == "accounts":
        formatted = "\n".join(f"{u} — {v}" for u, v in OFFICIAL_USERS.items())
        await q.message.reply_text("Официальные аккаунты:\n" + formatted)

    elif d == "how_pay":
        await q.message.reply_text(PAY_GUIDE, reply_markup=PAY_BUTTONS)

    elif d == "alipay":
        await q.message.reply_text(ALIPAY_TEXT)

    elif d == "pay_gpt":
        await q.message.reply_text(GPT_TEXT)

    elif d == "pay_suno":
        await q.message.reply_text(SUNO_TEXT)

    elif d == "pay_google":
        await q.message.reply_text(GOOGLE_TEXT)

# ===================== АДМИНКА =====================

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("⛔ Нет прав.")

    if not context.args:
        return await update.message.reply_text("Использование: /addadmin ID")

    try:
        uid = int(context.args[0])
        if uid not in ADMINS:
            ADMINS.append(uid)
        await update.message.reply_text(f"✅ Добавлен админ: {uid}")
    except:
        await update.message.reply_text("ID должен быть числом.")

async def settext_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return await update.message.reply_text("⛔ Нет прав.")

    if not context.args:
        return await update.message.reply_text(
            "Использование:\n"
            "/settext keywords\n"
            "/settext gpt\n"
            "/settext suno\n"
            "/settext google\n"
            "/settext alipay\n"
            "/settext pay\n"
        )

    key = context.args[0].lower()
    allowed = {"keywords", "gpt", "suno", "google", "alipay", "pay"}

    if key not in allowed:
        return await update.message.reply_text("Неизвестный блок текста.")

    context.user_data["edit"] = key
    await update.message.reply_text(f"Отправьте НОВЫЙ текст для {key.upper()}")

async def settext_apply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        return

    key = context.user_data.get("edit")
    if not key:
        return

    value = update.message.text

    global KEYWORD_TEXT, GPT_TEXT, SUNO_TEXT, GOOGLE_TEXT, ALIPAY_TEXT, PAY_GUIDE

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
    await update.message.reply_text("✔ Текст обновлён!")

# ===================== ОБРАБОТЧИК ВСЕХ ТЕКСТОВ =====================

async def text_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    # если админ редактирует текст — принимаем новый блок
    if update.effective_user.id in ADMINS and context.user_data.get("edit"):
        return await settext_apply(update, context)

    # проверка @username
    if text.startswith("@") and len(text.split()) == 1:
        return await check_username(update, context)

    # ключевые фразы
    if any(x in text for x in ["как купить", "как оплатить", "как перевести"]):
        return await update.message.reply_text(KEYWORD_TEXT)

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
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_router))

    print("🤖 Бот запущен!")
    app.run_polling()


if __name__ == "__main__":
    main()

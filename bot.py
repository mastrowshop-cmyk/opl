import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота из переменных окружения
BOT_TOKEN = os.getenv('8417645903:AAFJhLWAsxfzGg-2Su6oz4Tp-XfnKf_HZYA')

# Добавим отладочную информацию
print("=" * 50)
print("Проверка переменных окружения:")
print(f"BOT_TOKEN присутствует: {'BOT_TOKEN' in os.environ}")
print(f"Длина токена: {len(BOT_TOKEN) if BOT_TOKEN else 0}")
if BOT_TOKEN:
    print(f"Первые 10 символов токена: {BOT_TOKEN[:10]}...")
print("=" * 50)

# Приветственное сообщение при присоединении к чату
async def welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет приветственное сообщение когда пользователь присоединяется к чату"""
    if update.message.new_chat_members:
        for new_member in update.message.new_chat_members:
            if new_member.id == context.bot.id:
                # Бот добавлен в чат
                await update.message.reply_text(
                    "👋 Добро пожаловать в Oplatym.ru!\n\n"
                    "Мы рады видеть вас в нашем чате, пожалуйста ознакомьтесь с предупреждением ниже!\n\n"
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
                    f"Рады приветствовать вас, {update.message.from_user.mention_html()}!",
                    parse_mode='HTML'
                )
            else:
                # Новый пользователь присоединился к чату
                await update.message.reply_text(
                    f"Рады приветствовать вас, {new_member.mention_html()}! 👋",
                    parse_mode='HTML'
                )

# Команда /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Добро пожаловать в Oplatym.ru!\n\n"
        "Мы рады видеть вас в нашем чате, пожалуйста ознакомьтесь с предупреждением ниже!\n\n"
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
        f"Рады приветствовать вас, {update.message.from_user.mention_html()}!",
        parse_mode='HTML'
    )

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что сообщение содержит текст
    if not update.message or not update.message.text:
        return
        
    message_type = update.message.chat.type
    text = update.message.text.lower().strip()

    # Логируем полученное сообщение
    logging.info(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

    response = generate_response(text)
    
    if response:
        await update.message.reply_text(response)

# Генерация ответа на основе ключевых слов
def generate_response(text: str) -> str:
    # Ключевые слова для ответа
    keywords = [
        'как купить',
        'как перевести', 
        'как оплатить',
        'нужно оплатить',
        'нужно перевести',
        'нужно купить'
    ]
    
    # Проверяем наличие ключевых слов в тексте
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
    
    # Для других сообщений не отвечаем
    return ""

# Обработка ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f'Update {update} caused error {context.error}')

# Основная функция
def main():
    # Проверяем наличие токена
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN not found in environment variables")
        print("❌ ОШИБКА: Токен бота не обнаружен в переменных окружения")
        print("ℹ️  Проверьте настройки на Bothost.ru:")
        print("   1. Перейдите в настройки бота")
        print("   2. Найдите раздел 'Environment Variables'")
        print("   3. Убедитесь что есть переменная BOT_TOKEN")
        print("   4. Значение должно быть вашим токеном от @BotFather")
        return

    # Дополнительная проверка формата токена
    if ":" not in BOT_TOKEN:
        logging.error("❌ Invalid BOT_TOKEN format")
        print("❌ ОШИБКА: Неверный формат токена")
        print("ℹ️  Токен должен быть в формате: 1234567890:ABCdefGHIjklMnOprSTUvwxYZabcdEFGHIJ")
        return

    print("✅ Токен обнаружен, запускаем бота...")

    try:
        # Создаем приложение
        app = Application.builder().token(BOT_TOKEN).build()

        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Обработчик новых участников чата
        app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_message))
        
        # Обработчик ошибок
        app.add_error_handler(error_handler)

        # Запускаем бота
        logging.info("Бот Oplatym запущен...")
        print("🤖 Бот Oplatym успешно запущен!")
        app.run_polling(
            poll_interval=3,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logging.error(f"❌ Ошибка при запуске бота: {e}")
        print(f"❌ Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()
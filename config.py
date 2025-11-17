import os

# Токен бота (задавать через переменные окружения BOT_TOKEN на хостинге)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Канал/чат для публикации отзывов (замени на свой)
PUBLIC_CHAT_ID = -1002136717768

# ID менеджеров (пример). Замени или дополни реальными ID ваших менеджеров.
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

# Путь до папки с данными (относительно расположения config.py)
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")

REVIEWS_FILE = os.path.join(DATA_DIR, "reviews.json")
CLIENTS_FILE = os.path.join(DATA_DIR, "clients.json")
ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
MANAGER_LOGS_FILE = os.path.join(DATA_DIR, "logs.json")
MANAGER_STATS_FILE = os.path.join(DATA_DIR, "stats.json")

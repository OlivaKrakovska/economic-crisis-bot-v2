# config.py - Конфигурация бота
# ВАЖНО: Токен бота должен быть в переменных окружения или .env файле!

import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла (если он есть)
load_dotenv()

# Токен бота - берем из переменных окружения
# Никогда не хардкодьте токен в коде!
BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')

if not BOT_TOKEN:
    raise ValueError(
        "Токен бота не найден! Установите переменную окружения DISCORD_BOT_TOKEN "
        "или создайте файл .env с DISCORD_BOT_TOKEN=ваш_токен"
    )

# ID каналов для логов (это публичные ID, их можно оставить)
ADMIN_LOG_CHANNEL_ID = 1082221148957315172  # Канал для логов админов
TRADE_LOG_CHANNEL_ID = 1082221148957315172  # Канал для логов торговли
STRIKE_LOG_CHANNEL_ID = 1263440933232578630  # Канал для логов ударов
ESPIONAGE_LOG_CHANNEL_ID = 1263440933232578630  # Канал для логов разведки
DOCTRINE_LOG_CHANNEL_ID = 1263440933232578630  # Канал для военных доктрин

# Настройки игры
ECONOMIC_CYCLE_MINUTES = 30  # Интервал экономических циклов
YEAR_UPDATE_HOURS = 24  # Интервал годовых апдейтов

# Префикс команд
COMMAND_PREFIX = "!"

# Режим отладки (выключать на продакшене)
DEBUG_MODE = False

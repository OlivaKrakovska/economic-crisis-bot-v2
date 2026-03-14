#!/bin/bash
echo "Starting bot with correct paths..."

# Код уже в /app, Volume тоже смонтирован в /app
cd /app

# Проверяем, есть ли файлы данных в Volume
if [ ! -f /app/states.json ]; then
    echo "Initializing new game data..."
else
    echo "Loading existing game data from volume..."
fi

# Запускаем бота
python bot.py
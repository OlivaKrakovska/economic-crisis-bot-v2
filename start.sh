#!/bin/bash
echo "Starting bot with persistent storage..."

# Проверяем, есть ли JSON файлы в Volume
if [ ! -f /app/states.json ]; then
    echo "WARNING: Volume appears empty. JSON files may be missing."
fi

# Запускаем бота
cd /app
python /app/source/bot.py
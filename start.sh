#!/bin/bash
echo "Starting bot with volume support..."

# Определяем, где лежат исходные файлы
if [ -d "/app/source" ]; then
    SOURCE_DIR="/app/source"
elif [ -f "/app/bot.py" ]; then
    SOURCE_DIR="/app"
else
    # Ищем в корне
    SOURCE_DIR="/"
fi

echo "Source directory: $SOURCE_DIR"
echo "Contents of source:"
ls -la $SOURCE_DIR

# Копируем JSON файлы в Volume, если их там нет
# (Volume уже смонтирован в /app)
if [ ! -f /app/states.json ]; then
    echo "Initializing JSON files in volume..."
    # Запускаем бота из исходной директории, но с рабочей директорией /app (Volume)
    cd /app
    python $SOURCE_DIR/bot.py --init-only  # Если есть такой флаг
else
    echo "Volume already contains data, starting normally..."
    cd /app
    python $SOURCE_DIR/bot.py
fi
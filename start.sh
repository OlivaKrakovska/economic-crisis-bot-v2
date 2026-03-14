#!/bin/bash
echo "Starting bot with volume support..."

# Volume смонтирован в /app, в нём уже должны быть JSON файлы
# Но .py файлов в Volume нет, они лежат в исходной директории
SOURCE_DIR="/app/source"

# Если исходные файлы не там, ищем их
if [ ! -d "$SOURCE_DIR" ]; then
    # Файлы могут быть в корне контейнера
    SOURCE_DIR="/"
fi

# Запускаем бота из исходной директории, но с рабочей директорией /app (Volume)
cd /app
python $SOURCE_DIR/bot.py
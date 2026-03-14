#!/bin/bash
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

echo "Looking for bot.py..."
find / -name "bot.py" 2>/dev/null

# Копируем файлы в Volume, если они не там
if [ ! -f /app/bot.py ]; then
    echo "Copying project files to /app..."
    cp -r /app/* /app/ 2>/dev/null || true
    # Если файлы в другом месте, ищем их
    BOT_PATH=$(find / -name "bot.py" -type f 2>/dev/null | head -1)
    if [ ! -z "$BOT_PATH" ]; then
        echo "Found bot.py at: $BOT_PATH"
        cp $(dirname $BOT_PATH)/* /app/ 2>/dev/null || true
    fi
fi

# Запускаем бота
cd /app
python bot.py
# Временно измените start.sh на:
#!/bin/bash
echo "Copying JSON files to volume..."
cp /*.json /app/ 2>/dev/null || true
cp /app/source/*.json /app/ 2>/dev/null || true

echo "Starting bot..."
cd /app
python /app/source/bot.py
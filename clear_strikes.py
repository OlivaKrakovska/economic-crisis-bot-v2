# clear_strikes.py
import json

# Очищаем strikes.json
empty_strikes = {"strikes": [], "stats": {}}
with open('strikes.json', 'w', encoding='utf-8') as f:
    json.dump(empty_strikes, f, ensure_ascii=False, indent=4)

# Очищаем strike_queue.json
empty_queue = {"active_strikes": [], "completed_strikes": []}
with open('strike_queue.json', 'w', encoding='utf-8') as f:
    json.dump(empty_queue, f, ensure_ascii=False, indent=4)

print("✅ История ударов очищена!")

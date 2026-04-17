#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Конвертирует все расходы (military_budget, healthcare, police, social_security, education)
из USD в локальную валюту.
"""

import json
import shutil
from datetime import datetime

# Курсы валют на 2019 год
EXCHANGE_RATES = {
    "США": 1.0,
    "Россия": 64.7,
    "Китай": 6.91,
    "Украина": 25.8,
    "Германия": 0.89,
    "Франция": 0.89,
    "Великобритания": 0.78,
    "Норвегия": 8.80,
    "Швеция": 9.46,
    "Финляндия": 0.89,
    "Польша": 3.84,
    "Иран": 42000.0,
    "Израиль": 3.56,
    "Сирия": 515.0,
    "Бразилия": 3.94,
    "Турция": 5.67,
    "Египет": 16.8,
    "Швейцария": 0.99,
    "Канада": 1.33,
    "КНДР": 900.0,
    "Япония": 109.0,
    "Беларусь": 2.09,
}

def convert_file(filename):
    print(f"\n📂 Обработка {filename}...")
    
    # Бэкап
    backup = f"{filename}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy(filename, backup)
    print(f"   ✅ Бэкап: {backup}")
    
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Определяем, где лежат страны
    if "players" in data:
        players = data["players"]
    else:
        players = data
        data = {"players": players}
    
    updated = 0
    for state_id, state_data in players.items():
        country = state_data["state"]["statename"]
        rate = EXCHANGE_RATES.get(country, 1.0)
        
        if "economy" in state_data:
            econ = state_data["economy"]
            if "military_budget" in econ:
                old = econ["military_budget"]
                econ["military_budget"] = old * rate
                print(f"   {country}: military_budget {old:,.0f} USD -> {econ['military_budget']:,.0f} {state_data['economy']['local_currency']['code']}")
                updated += 1
        
        if "expenses" in state_data:
            exp = state_data["expenses"]
            for key in ["healthcare", "police", "social_security", "education"]:
                if key in exp:
                    exp[key] = exp[key] * rate
        
        # Обновляем GDP local если ещё не обновлён
        if "economy" in state_data and "gdp" in state_data["economy"] and "gdp_local" not in state_data["economy"]:
            state_data["economy"]["gdp_local"] = state_data["economy"]["gdp"] * rate
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"   ✨ Обновлено расходов: {updated}")


if __name__ == "__main__":
    for f in ["states.json", "states_default.json"]:
        try:
            convert_file(f)
        except FileNotFoundError:
            print(f"⚠️ Файл {f} не найден")
        except Exception as e:
            print(f"❌ Ошибка в {f}: {e}")
    
    print("\n✨ ГОТОВО! Теперь все расходы в локальной валюте.")

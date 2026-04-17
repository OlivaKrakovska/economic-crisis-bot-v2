#!/usr/bin/env python3
# migrate_currencies.py - Миграция валют
import json

CURRENCY_CODES = {
    "США": "USD", "Россия": "RUB", "Китай": "CNY", "Украина": "UAH",
    "Германия": "EUR", "Франция": "EUR", "Великобритания": "GBP",
    "Норвегия": "NOK", "Швеция": "SEK", "Финляндия": "EUR",
    "Польша": "PLN", "Иран": "IRR", "Израиль": "ILS",
    "Сирия": "SYP", "Бразилия": "BRL", "Турция": "TRY",
    "Египет": "EGP", "Швейцария": "CHF", "Канада": "CAD",
    "КНДР": "KPW", "Япония": "JPY", "Беларусь": "BYN",
}

with open('states.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

migrated = 0
for state_id, p in data["players"].items():
    e = p.get("economy", {})
    country = p["state"]["statename"]
    
    if "local_currency" in e and "gdp_local" in e:
        continue
        
    old_budget = e.get("budget_usd", e.get("budget", 1e11))
    old_gdp = e.get("gdp_usd", e.get("gdp", 1e11))
    old_debt = e.get("debt_usd", e.get("debt", 0))
    
    e["local_currency"] = {
        "code": CURRENCY_CODES.get(country, "USD"),
        "amount": float(old_budget),
        "inflation": e.get("inflation", 2.0),
        "interest_rate": 5.0
    }
    e["gdp_local"] = old_gdp
    e["debt_local"] = old_debt
    e["budget_usd"] = old_budget
    e["gdp_usd"] = old_gdp
    e["debt_usd"] = old_debt
    
    migrated += 1
    print(f"  ✅ {country}")

with open('states.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"\nМиграция завершена: {migrated} стран")

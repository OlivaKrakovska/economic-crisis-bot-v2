# utils.py - Вспомогательные функции
# Версия 4.0 - полная поддержка двухвалютной системы

import discord
from datetime import datetime
import json
import os
import random

from paths import DATA_DIR, get_data_path

STATES_FILE = get_data_path('states.json')
TRADES_FILE = get_data_path('trades.json')
ALLIANCES_FILE = get_data_path('alliances.json')
TRANSFERS_FILE = get_data_path('transfers.json')

DARK_THEME_COLOR = 0x2b2d31

# ==================== КУРСЫ ВАЛЮТ НА 2019 ГОД ====================
EXCHANGE_RATES_2019 = {
    "США": 1.0, "Россия": 64.7, "Китай": 6.91, "Украина": 25.8,
    "Германия": 0.89, "Франция": 0.89, "Великобритания": 0.78,
    "Норвегия": 8.80, "Швеция": 9.46, "Финляндия": 0.89,
    "Польша": 3.84, "Иран": 42000.0, "Израиль": 3.56,
    "Сирия": 515.0, "Бразилия": 3.94, "Турция": 5.67,
    "Египет": 16.8, "Швейцария": 0.99, "Канада": 1.33,
    "КНДР": 900.0, "Япония": 109.0, "Беларусь": 2.09,
}
# ==================== КОДЫ ВАЛЮТ ====================
CURRENCY_CODES = {
    "США": "USD", "Россия": "RUB", "Китай": "CNY", "Украина": "UAH",
    "Германия": "EUR", "Франция": "EUR", "Великобритания": "GBP",
    "Норвегия": "NOK", "Швеция": "SEK", "Финляндия": "EUR",
    "Польша": "PLN", "Иран": "IRR", "Израиль": "ILS",
    "Сирия": "SYP", "Бразилия": "BRL", "Турция": "TRY",
    "Египет": "EGP", "Швейцария": "CHF", "Канада": "CAD",
    "КНДР": "KPW", "Япония": "JPY", "Беларусь": "BYN",
}
# ==================== ФУНКЦИИ ДЛЯ ДВУХВАЛЮТНОЙ СИСТЕМЫ ====================

def get_budget(economy):
    """Возвращает бюджет в локальной валюте"""
    if not economy:
        return 0
    if "local_currency" in economy:
        return economy["local_currency"].get("amount", 0)
    # Обратная совместимость
    if "budget_usd" in economy:
        return economy["budget_usd"]
    return economy.get("budget", 0)

def set_budget(economy, new_budget):
    """Устанавливает бюджет в локальной валюте"""
    if not economy:
        return
    if "local_currency" not in economy:
        economy["local_currency"] = {"code": "USD", "amount": 0, "inflation": 2.0, "interest_rate": 5.0}
    economy["local_currency"]["amount"] = float(new_budget)

def add_to_budget(economy, amount):
    """Добавляет сумму к бюджету в локальной валюте"""
    current = get_budget(economy)
    set_budget(economy, current + amount)

def subtract_from_budget(economy, amount):
    """Вычитает сумму из бюджета в локальной валюте"""
    current = get_budget(economy)
    set_budget(economy, max(0, current - amount))

def has_sufficient_budget(economy, amount):
    """Проверяет, достаточно ли средств в локальном бюджете"""
    return get_budget(economy) >= amount

def get_gdp(economy):
    """Возвращает ВВП в локальной валюте"""
    if not economy:
        return 0
    return economy.get("gdp_local", 0)

def get_gdp_usd(economy):
    """Возвращает ВВП в USD (для международной статистики)"""
    if not economy:
        return 0
    return economy.get("gdp_usd", 0)

def get_debt(economy):
    """Возвращает госдолг в локальной валюте"""
    if not economy:
        return 0
    return economy.get("debt_local", 0)

def get_debt_usd(economy):
    """Возвращает госдолг в USD"""
    if not economy:
        return 0
    return economy.get("debt_usd", 0)

def get_military_budget(economy):
    """Возвращает военный бюджет в локальной валюте"""
    if not economy:
        return 0
    return economy.get("military_budget_local", 0)

def get_wage(economy):
    """Возвращает среднюю зарплату в локальной валюте"""
    if not economy:
        return 0
    return economy.get("wage_local", 0)

def get_currency_code(economy):
    """Возвращает код локальной валюты"""
    if not economy:
        return "USD"
    if "local_currency" in economy:
        return economy["local_currency"].get("code", "USD")
    return "USD"

def get_inflation(economy):
    """Возвращает инфляцию"""
    if not economy:
        return 2.0
    if "local_currency" in economy:
        return economy["local_currency"].get("inflation", 2.0)
    return economy.get("inflation", 2.0)

def get_usd_reserves(economy):
    """Возвращает долларовые резервы"""
    if not economy:
        return 0
    return economy.get("foreign_reserves", {}).get("USD", 0)

def spend_usd(economy, amount):
    """Списывает USD из резервов"""
    if not economy:
        return False
    if "foreign_reserves" not in economy:
        economy["foreign_reserves"] = {"USD": 0, "EUR": 0, "CNY": 0, "gold_tons": 0}
    if economy["foreign_reserves"].get("USD", 0) < amount:
        return False
    economy["foreign_reserves"]["USD"] -= amount
    return True

def add_usd(economy, amount):
    """Добавляет USD в резервы"""
    if not economy:
        return
    if "foreign_reserves" not in economy:
        economy["foreign_reserves"] = {"USD": 0, "EUR": 0, "CNY": 0, "gold_tons": 0}
    economy["foreign_reserves"]["USD"] = economy["foreign_reserves"].get("USD", 0) + amount

def format_budget_display(economy):
    """Форматирует бюджет для отображения"""
    budget = get_budget(economy)
    currency = get_currency_code(economy)
    return f"{format_billion(budget)} {currency}".replace('$ ', '')

def format_gdp_display(economy):
    """Форматирует ВВП для отображения"""
    gdp = get_gdp(economy)
    currency = get_currency_code(economy)
    return f"{format_billion(gdp)} {currency}".replace('$ ', '')

def format_debt_display(economy):
    """Форматирует госдолг для отображения"""
    debt = get_debt(economy)
    currency = get_currency_code(economy)
    return f"{format_billion(debt)} {currency}".replace('$ ', '')

def format_money(amount, currency_code=None):
    """Универсальное форматирование денег с валютой"""
    if amount is None:
        return "0"
    formatted = format_billion(amount)
    if currency_code:
        return f"{formatted} {currency_code}"
    return formatted

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

def get_user_id(ctx):
    if hasattr(ctx, 'author'):
        return ctx.author.id
    else:
        return ctx.user.id

def get_user_name(ctx):
    if hasattr(ctx, 'author'):
        return ctx.author.name
    else:
        return ctx.user.name

async def send_response(ctx, content=None, embed=None, view=None, file=None, ephemeral=False):
    if hasattr(ctx, 'author'):
        if embed and file:
            await ctx.send(embed=embed, view=view, file=file)
        elif embed:
            await ctx.send(embed=embed, view=view)
        elif file:
            await ctx.send(content, view=view, file=file)
        else:
            await ctx.send(content, view=view)
    else:
        try:
            if not ctx.response.is_done():
                if embed and file:
                    await ctx.response.send_message(embed=embed, view=view, file=file, ephemeral=ephemeral)
                elif embed:
                    await ctx.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                elif file:
                    await ctx.response.send_message(content, view=view, file=file, ephemeral=ephemeral)
                else:
                    await ctx.response.send_message(content, view=view, ephemeral=ephemeral)
            else:
                if embed and file:
                    await ctx.followup.send(embed=embed, view=view, file=file, ephemeral=ephemeral)
                elif embed:
                    await ctx.followup.send(embed=embed, view=view, ephemeral=ephemeral)
                elif file:
                    await ctx.followup.send(content, view=view, file=file, ephemeral=ephemeral)
                else:
                    await ctx.followup.send(content, view=view, ephemeral=ephemeral)
        except:
            pass

async def edit_response(ctx, embed=None, view=None):
    if hasattr(ctx, 'author'):
        if embed:
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(view=view)
    else:
        try:
            await ctx.response.edit_message(embed=embed, view=view)
        except:
            try:
                await ctx.edit_original_response(embed=embed, view=view)
            except:
                pass

def format_number(value):
    if value is None:
        return "0"
    return f"{int(value):,}".replace(',', ' ')

def format_army_number(value):
    if value is None:
        return "0"
    if value >= 1_000_000:
        return f"{value/1_000_000:.1f} млн"
    elif value >= 1_000:
        return f"{value/1_000:.1f} тыс"
    else:
        return str(int(value))

def format_billion(value):
    if value is None:
        return "0"
    if value >= 1_000_000_000_000:
        return f"{value/1_000_000_000_000:.2f} трлн".replace(',', '.')
    elif value >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f} млрд".replace(',', '.')
    elif value >= 1_000_000:
        return f"{value/1_000_000:.2f} млн".replace(',', '.')
    elif value >= 1_000:
        return f"{value/1_000:.2f} тыс".replace(',', '.')
    else:
        return f"{int(value):,}".replace(',', ' ')

def format_infra_cost(cost_millions):
    """Специальное форматирование для стоимости инфраструктуры"""
    if cost_millions >= 1000:
        billions = cost_millions / 1000
        return f"{billions:.1f} млрд $"
    else:
        return f"{cost_millions:.0f} млн $"

def format_research_cost(cost_millions):
    """Форматирование для стоимости исследований"""
    if cost_millions >= 1000:
        billions = cost_millions / 1000
        return f"{billions:.1f} млрд $"
    else:
        return f"{cost_millions:.0f} млн $"

def format_time(seconds):
    if seconds < 60:
        return f"{seconds:.0f} сек"
    elif seconds < 3600:
        return f"{seconds // 60} мин"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} ч {minutes} мин"
        return f"{hours} ч"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours > 0:
            return f"{days} дн {hours} ч"
        return f"{days} дн"

def create_embed(title, description=None, color=DARK_THEME_COLOR, fields=None, footer=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    if footer:
        embed.set_footer(text=footer)
    return embed

async def safe_delete(message):
    try:
        if message:
            await message.delete()
    except:
        pass

def load_states():
    try:
        with open(STATES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"players": {}, "last_update": str(datetime.now())}
            return json.loads(content)
    except FileNotFoundError:
        return {"players": {}, "last_update": str(datetime.now())}
    except json.JSONDecodeError:
        return {"players": {}, "last_update": str(datetime.now())}

def save_states(data):
    with open(STATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_trades():
    try:
        with open(TRADES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_trades": [], "completed_trades": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"active_trades": [], "completed_trades": []}
    except json.JSONDecodeError:
        return {"active_trades": [], "completed_trades": []}

def save_trades(data):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_alliances():
    try:
        with open(ALLIANCES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"alliances": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"alliances": []}
    except json.JSONDecodeError:
        return {"alliances": []}

def save_alliances(data):
    with open(ALLIANCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_transfers():
    try:
        with open(TRANSFERS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_transfers": [], "completed_transfers": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"active_transfers": [], "completed_transfers": []}
    except json.JSONDecodeError:
        return {"active_transfers": [], "completed_transfers": []}

def save_transfers(data):
    with open(TRANSFERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def send_ephemeral(interaction, embed=None, view=None, content=None):
    await interaction.response.send_message(content=content, embed=embed, view=view, ephemeral=True)

async def update_ephemeral(interaction, embed=None, view=None):
    try:
        await interaction.response.edit_message(embed=embed, view=view)
    except:
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except:
            pass

# ==================== РАСЧЁТ ДОЛИ РЫНКА ====================
# (Оставьте существующий код расчёта доли рынка без изменений)

# ==================== ЭКСПОРТ ====================
__all__ = [
    'get_user_id', 'get_user_name', 'send_response', 'edit_response',
    'format_number', 'format_army_number', 'format_billion', 'format_time',
    'format_infra_cost', 'format_research_cost',
    'create_embed', 'safe_delete', 'send_ephemeral', 'update_ephemeral',
    'DARK_THEME_COLOR', 'load_states', 'save_states', 'load_trades', 'save_trades',
    'load_alliances', 'save_alliances', 'load_transfers', 'save_transfers',
    'get_budget', 'set_budget', 'add_to_budget', 'subtract_from_budget',
    'has_sufficient_budget', 'get_gdp', 'get_gdp_usd', 'get_debt', 'get_debt_usd',
    'get_military_budget', 'get_wage', 'get_currency_code', 'get_inflation',
    'get_usd_reserves', 'spend_usd', 'add_usd',
    'format_budget_display', 'format_gdp_display', 'format_debt_display',
    'EXCHANGE_RATES_2019', 'CURRENCY_CODES'  # ДОБАВЛЕНО
]

# central_bank.py - ПОЛНАЯ МУЛЬТИВАЛЮТНАЯ ВЕРСИЯ (ИСПРАВЛЕНО)
# Поддерживает разделение: национальная валюта (бюджет) и USD (международные резервы)

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from utils import (
    format_billion, format_number, format_army_number, 
    load_states, save_states, DARK_THEME_COLOR,
    get_budget, set_budget, add_to_budget, subtract_from_budget,
    get_currency_code, get_gdp, get_debt, get_inflation
)

# ==================== КОНСТАНТЫ ====================

CENTRAL_BANK_FILE = 'central_bank.json'

# Цена золота за тонну (в USD)
GOLD_PRICE_PER_TON_USD = 60_000_000  # $60 млн за тонну

# Ключевая ставка по умолчанию
DEFAULT_INTEREST_RATE = 5.0

# ==================== ЗАГРУЗКА/СОХРАНЕНИЕ ====================

def load_central_bank_data() -> Dict:
    """Загрузка данных центральных банков"""
    try:
        with open(CENTRAL_BANK_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"banks": {}}
            return json.loads(content)
    except FileNotFoundError:
        return {"banks": {}}
    except json.JSONDecodeError:
        return {"banks": {}}

def save_central_bank_data(data: Dict):
    """Сохранение данных центральных банков"""
    with open(CENTRAL_BANK_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_country_bank_data(country_name: str) -> Dict:
    """Получить данные центробанка для страны"""
    data = load_central_bank_data()
    
    if country_name not in data["banks"]:
        # Инициализация с поддержкой старых и новых ключей
        data["banks"][country_name] = {
            "interest_rate": DEFAULT_INTEREST_RATE,
            "gold_reserves_tons": 100.0,
            "gold_reserves": 100.0,  # для обратной совместимости
            "inflation_forecast": 2.0,
            "gdp_forecast": 2.0,
            "debt_forecast": 0.0,
            "budget_forecast": 0.0,
            "last_updated": str(datetime.now()),
            "history": []
        }
        save_central_bank_data(data)
    
    # Миграция старых данных
    bank = data["banks"][country_name]
    if "gold_reserves" in bank and "gold_reserves_tons" not in bank:
        bank["gold_reserves_tons"] = bank["gold_reserves"]
    if "gold_reserves_tons" in bank and "gold_reserves" not in bank:
        bank["gold_reserves"] = bank["gold_reserves_tons"]
    
    return bank

def update_country_bank_data(country_name: str, bank_data: Dict):
    """Обновить данные центробанка для страны"""
    data = load_central_bank_data()
    # Синхронизируем оба ключа
    if "gold_reserves_tons" in bank_data:
        bank_data["gold_reserves"] = bank_data["gold_reserves_tons"]
    elif "gold_reserves" in bank_data:
        bank_data["gold_reserves_tons"] = bank_data["gold_reserves"]
    data["banks"][country_name] = bank_data
    data["banks"][country_name]["last_updated"] = str(datetime.now())
    save_central_bank_data(data)

def get_gold_tons(bank_data: Dict) -> float:
    """Безопасное получение золотого запаса"""
    return bank_data.get("gold_reserves_tons", bank_data.get("gold_reserves", 100.0))

def set_gold_tons(bank_data: Dict, value: float):
    """Безопасная установка золотого запаса"""
    bank_data["gold_reserves_tons"] = value
    bank_data["gold_reserves"] = value

def add_to_history(country_name: str, entry: Dict):
    """Добавить запись в историю операций"""
    bank_data = get_country_bank_data(country_name)
    if "history" not in bank_data:
        bank_data["history"] = []
    bank_data["history"].append(entry)
    if len(bank_data["history"]) > 50:
        bank_data["history"] = bank_data["history"][-50:]
    update_country_bank_data(country_name, bank_data)

# ==================== ОПЕРАЦИИ ЦЕНТРОБАНКА ====================

def print_money(country_name: str, amount: float, player_data: Dict) -> Dict:
    """
    Эмиссия национальной валюты
    Увеличивает бюджет, повышает инфляцию
    """
    currency = get_currency_code(player_data["economy"])
    
    # Добавляем деньги в бюджет
    add_to_budget(player_data["economy"], amount)
    
    # Рост инфляции пропорционально эмиссии относительно ВВП
    gdp = get_gdp(player_data["economy"])
    inflation_increase = (amount / gdp) * 100 * 2.0 if gdp > 0 else 5.0
    
    if "local_currency" in player_data["economy"]:
        player_data["economy"]["local_currency"]["inflation"] = player_data["economy"]["local_currency"].get("inflation", 2.0) + inflation_increase
    
    add_to_history(country_name, {
        "date": str(datetime.now()),
        "action": "print_money",
        "amount": amount,
        "currency": currency,
        "inflation_impact": round(inflation_increase, 2),
        "new_budget": get_budget(player_data["economy"])
    })
    
    return {
        "success": True,
        "printed": amount,
        "currency": currency,
        "inflation_increase": round(inflation_increase, 2),
        "new_budget": get_budget(player_data["economy"])
    }

def sell_gold_usd(country_name: str, tons: float, player_data: Dict) -> Dict:
    """
    Продажа золота за USD
    Увеличивает USD-резервы, уменьшает золотой запас
    """
    bank_data = get_country_bank_data(country_name)
    current_gold = get_gold_tons(bank_data)
    
    if current_gold < tons:
        return {
            "success": False,
            "message": f"Недостаточно золота! Доступно: {current_gold:.1f} тонн"
        }
    
    set_gold_tons(bank_data, current_gold - tons)
    revenue_usd = tons * GOLD_PRICE_PER_TON_USD
    
    if "foreign_reserves" not in player_data["economy"]:
        player_data["economy"]["foreign_reserves"] = {"USD": 0, "EUR": 0, "CNY": 0, "gold_tons": 0}
    player_data["economy"]["foreign_reserves"]["USD"] = player_data["economy"]["foreign_reserves"].get("USD", 0) + revenue_usd
    
    add_to_history(country_name, {
        "date": str(datetime.now()),
        "action": "sell_gold",
        "tons": tons,
        "revenue_usd": revenue_usd,
        "new_gold_tons": get_gold_tons(bank_data)
    })
    
    update_country_bank_data(country_name, bank_data)
    
    return {
        "success": True,
        "sold": tons,
        "revenue_usd": revenue_usd,
        "new_gold_tons": get_gold_tons(bank_data)
    }

def buy_gold_usd(country_name: str, tons: float, player_data: Dict) -> Dict:
    """
    Покупка золота за USD из резервов
    Уменьшает USD-резервы, увеличивает золотой запас
    """
    bank_data = get_country_bank_data(country_name)
    cost_usd = tons * GOLD_PRICE_PER_TON_USD
    
    reserves = player_data["economy"].get("foreign_reserves", {})
    if reserves.get("USD", 0) < cost_usd:
        return {
            "success": False,
            "message": f"Недостаточно USD в резервах! Нужно: ${cost_usd:,.0f}, доступно: ${reserves.get('USD', 0):,.0f}"
        }
    
    reserves["USD"] -= cost_usd
    current_gold = get_gold_tons(bank_data)
    set_gold_tons(bank_data, current_gold + tons)
    
    add_to_history(country_name, {
        "date": str(datetime.now()),
        "action": "buy_gold",
        "tons": tons,
        "cost_usd": cost_usd,
        "new_gold_tons": get_gold_tons(bank_data)
    })
    
    update_country_bank_data(country_name, bank_data)
    
    return {
        "success": True,
        "bought": tons,
        "cost_usd": cost_usd,
        "new_gold_tons": get_gold_tons(bank_data)
    }

def repay_debt(country_name: str, amount: float, player_data: Dict) -> Dict:
    """
    Погашение государственного долга в национальной валюте
    """
    currency = get_currency_code(player_data["economy"])
    current_debt = get_debt(player_data["economy"])
    current_budget = get_budget(player_data["economy"])
    
    if amount > current_debt:
        amount = current_debt
    
    if current_budget < amount:
        return {
            "success": False,
            "message": f"Недостаточно средств в бюджете! Нужно: {format_billion(amount)} {currency}"
        }
    
    subtract_from_budget(player_data["economy"], amount)
    
    if "debt_local" in player_data["economy"]:
        player_data["economy"]["debt_local"] -= amount
    if "debt_usd" in player_data["economy"]:
        player_data["economy"]["debt_usd"] = max(0, player_data["economy"]["debt_usd"] - amount)
    
    # Снижение инфляции при погашении долга
    if "local_currency" in player_data["economy"]:
        player_data["economy"]["local_currency"]["inflation"] = max(0, player_data["economy"]["local_currency"].get("inflation", 2.0) - 0.1)
    
    add_to_history(country_name, {
        "date": str(datetime.now()),
        "action": "repay_debt",
        "amount": amount,
        "currency": currency,
        "new_debt": get_debt(player_data["economy"])
    })
    
    return {
        "success": True,
        "repaid": amount,
        "currency": currency,
        "new_debt": get_debt(player_data["economy"]),
        "remaining_budget": get_budget(player_data["economy"])
    }

def set_interest_rate(country_name: str, new_rate: float) -> Dict:
    """Изменение ключевой ставки"""
    bank_data = get_country_bank_data(country_name)
    old_rate = bank_data["interest_rate"]
    bank_data["interest_rate"] = new_rate
    
    add_to_history(country_name, {
        "date": str(datetime.now()),
        "action": "change_rate",
        "old_rate": old_rate,
        "new_rate": new_rate
    })
    
    update_country_bank_data(country_name, bank_data)
    
    return {
        "success": True,
        "old_rate": old_rate,
        "new_rate": new_rate
    }

def generate_economic_forecast(country_name: str, player_data: Dict) -> Dict:
    """Генерирует прогноз экономических показателей"""
    bank_data = get_country_bank_data(country_name)
    
    current_inflation = get_inflation(player_data["economy"])
    current_gdp = get_gdp(player_data["economy"]) / 1_000_000_000
    current_debt = get_debt(player_data["economy"]) / 1_000_000_000
    current_budget = get_budget(player_data["economy"]) / 1_000_000_000
    interest_rate = bank_data["interest_rate"]
    
    inflation_forecast = current_inflation * random.uniform(0.9, 1.1)
    gdp_forecast = random.uniform(1.5, 3.5) * (1 - (interest_rate - 2) / 20)
    debt_forecast = current_debt * random.uniform(0.95, 1.05)
    budget_forecast = current_budget * random.uniform(0.9, 1.2)
    
    bank_data["inflation_forecast"] = round(inflation_forecast, 2)
    bank_data["gdp_forecast"] = round(gdp_forecast, 2)
    bank_data["debt_forecast"] = round(debt_forecast, 2)
    bank_data["budget_forecast"] = round(budget_forecast, 2)
    
    update_country_bank_data(country_name, bank_data)
    
    return {
        "current_inflation": round(current_inflation, 2),
        "forecast_inflation": round(inflation_forecast, 2),
        "forecast_gdp_growth": round(gdp_forecast, 2),
        "current_debt": round(current_debt, 2),
        "forecast_debt": round(debt_forecast, 2),
        "current_budget": round(current_budget, 2),
        "forecast_budget": round(budget_forecast, 2),
        "interest_rate": interest_rate
    }

# ==================== МОДАЛЬНЫЕ ОКНА ====================

class PrintMoneyModal(Modal, title="💰 Эмиссия национальной валюты"):
    def __init__(self, user_id: int, country_name: str, player_data: Dict):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.currency = get_currency_code(player_data["economy"])
        
        gdp = get_gdp(player_data["economy"])
        max_print = gdp * 0.1
        
        self.amount_input = TextInput(
            label=f"Сумма эмиссии ({self.currency}, макс: {format_billion(max_print)})",
            placeholder="Например: 1000000000000",
            min_length=1,
            max_length=20,
            required=True
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        
        try:
            amount = float(self.amount_input.value.replace(',', '').replace(' ', ''))
            if amount <= 0:
                return await interaction.response.send_message("❌ Сумма должна быть положительной!", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
        
        result = print_money(self.country_name, amount, self.player_data)
        
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country_name:
                data["economy"] = self.player_data["economy"]
                break
        save_states(states)
        
        embed = discord.Embed(title="✅ Эмиссия выполнена", color=discord.Color.green())
        embed.add_field(name="Сумма", value=f"{format_billion(amount)} {self.currency}")
        embed.add_field(name="Рост инфляции", value=f"+{result['inflation_increase']}%")
        embed.add_field(name="Новый бюджет", value=f"{format_billion(result['new_budget'])} {self.currency}")
        
        await interaction.response.edit_message(embed=embed, view=CentralBankView(self.user_id, self.country_name, self.player_data))


class GoldSellModal(Modal, title="📉 Продажа золота за USD"):
    def __init__(self, user_id: int, country_name: str, player_data: Dict):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        
        bank_data = get_country_bank_data(country_name)
        available = get_gold_tons(bank_data)
        
        self.tons_input = TextInput(
            label=f"Количество золота (тонн, доступно: {available:.1f})",
            placeholder="Например: 10",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.tons_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        
        try:
            tons = float(self.tons_input.value)
            if tons <= 0:
                return await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
        
        result = sell_gold_usd(self.country_name, tons, self.player_data)
        
        if not result["success"]:
            return await interaction.response.send_message(f"❌ {result['message']}", ephemeral=True)
        
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country_name:
                data["economy"] = self.player_data["economy"]
                break
        save_states(states)
        
        embed = discord.Embed(title="✅ Золото продано", color=discord.Color.green())
        embed.add_field(name="Продано", value=f"{tons:.1f} тонн")
        embed.add_field(name="Получено USD", value=f"${result['revenue_usd']:,.0f}")
        embed.add_field(name="Остаток золота", value=f"{result['new_gold_tons']:.1f} тонн")
        
        await interaction.response.edit_message(embed=embed, view=CentralBankView(self.user_id, self.country_name, self.player_data))


class GoldBuyModal(Modal, title="📈 Покупка золота за USD"):
    def __init__(self, user_id: int, country_name: str, player_data: Dict):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        
        usd_available = player_data["economy"].get("foreign_reserves", {}).get("USD", 0)
        max_tons = usd_available / GOLD_PRICE_PER_TON_USD
        
        self.tons_input = TextInput(
            label=f"Количество золота (тонн, макс: {max_tons:.1f})",
            placeholder="Например: 5",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.tons_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        
        try:
            tons = float(self.tons_input.value)
            if tons <= 0:
                return await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
        
        result = buy_gold_usd(self.country_name, tons, self.player_data)
        
        if not result["success"]:
            return await interaction.response.send_message(f"❌ {result['message']}", ephemeral=True)
        
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country_name:
                data["economy"] = self.player_data["economy"]
                break
        save_states(states)
        
        embed = discord.Embed(title="✅ Золото куплено", color=discord.Color.green())
        embed.add_field(name="Куплено", value=f"{tons:.1f} тонн")
        embed.add_field(name="Потрачено USD", value=f"${result['cost_usd']:,.0f}")
        embed.add_field(name="Новый запас", value=f"{result['new_gold_tons']:.1f} тонн")
        
        await interaction.response.edit_message(embed=embed, view=CentralBankView(self.user_id, self.country_name, self.player_data))


class RepayDebtModal(Modal, title="📉 Погашение долга"):
    def __init__(self, user_id: int, country_name: str, player_data: Dict):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        
        self.currency = get_currency_code(player_data["economy"])
        current_debt = get_debt(player_data["economy"])
        current_budget = get_budget(player_data["economy"])
        
        self.amount_input = TextInput(
            label=f"Сумма погашения ({self.currency})",
            placeholder=f"Долг: {format_billion(current_debt)}, бюджет: {format_billion(current_budget)}",
            min_length=1,
            max_length=20,
            required=True
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        
        try:
            amount = float(self.amount_input.value.replace(',', '').replace(' ', ''))
            if amount <= 0:
                return await interaction.response.send_message("❌ Сумма должна быть положительной!", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
        
        result = repay_debt(self.country_name, amount, self.player_data)
        
        if not result["success"]:
            return await interaction.response.send_message(f"❌ {result['message']}", ephemeral=True)
        
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country_name:
                data["economy"] = self.player_data["economy"]
                break
        save_states(states)
        
        embed = discord.Embed(title="✅ Долг погашен", color=discord.Color.green())
        embed.add_field(name="Погашено", value=f"{format_billion(amount)} {self.currency}")
        embed.add_field(name="Новый долг", value=f"{format_billion(result['new_debt'])} {self.currency}")
        embed.add_field(name="Остаток бюджета", value=f"{format_billion(result['remaining_budget'])} {self.currency}")
        
        await interaction.response.edit_message(embed=embed, view=CentralBankView(self.user_id, self.country_name, self.player_data))


class InterestRateModal(Modal, title="📊 Изменение ключевой ставки"):
    def __init__(self, user_id: int, country_name: str):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        
        bank_data = get_country_bank_data(country_name)
        current_rate = bank_data["interest_rate"]
        
        self.rate_input = TextInput(
            label=f"Новая ставка (текущая: {current_rate}%)",
            placeholder="Введите число от 0 до 100",
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.rate_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        
        try:
            rate = float(self.rate_input.value)
            if rate < 0 or rate > 100:
                return await interaction.response.send_message("❌ Ставка должна быть от 0 до 100!", ephemeral=True)
        except ValueError:
            return await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
        
        result = set_interest_rate(self.country_name, rate)
        
        embed = discord.Embed(title="✅ Ставка изменена", color=discord.Color.green())
        embed.add_field(name="Было", value=f"{result['old_rate']}%")
        embed.add_field(name="Стало", value=f"{result['new_rate']}%")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==================== VIEW КЛАССЫ ====================

class GoldReserveView(View):
    """Меню управления золотым резервом"""
    
    def __init__(self, user_id: int, country_name: str, player_data: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.bank_data = get_country_bank_data(country_name)
    
    @discord.ui.button(label="📈 Купить золото (USD)", style=discord.ButtonStyle.success)
    async def buy_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        modal = GoldBuyModal(self.user_id, self.country_name, self.player_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📉 Продать золото (USD)", style=discord.ButtonStyle.danger)
    async def sell_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        modal = GoldSellModal(self.user_id, self.country_name, self.player_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="◀ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        await interaction.response.edit_message(
            embed=create_bank_embed(self.country_name, self.player_data, self.bank_data),
            view=CentralBankView(self.user_id, self.country_name, self.player_data)
        )


class CentralBankView(View):
    """Главное меню центробанка"""
    
    def __init__(self, user_id: int, country_name: str, player_data: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.bank_data = get_country_bank_data(country_name)
    
    @discord.ui.button(label="💰 Эмиссия", style=discord.ButtonStyle.primary)
    async def print_money_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        modal = PrintMoneyModal(self.user_id, self.country_name, self.player_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🪙 Золотой резерв", style=discord.ButtonStyle.success)
    async def gold_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        
        gold_tons = get_gold_tons(self.bank_data)
        usd_reserves = self.player_data["economy"].get("foreign_reserves", {}).get("USD", 0)
        gold_value_usd = gold_tons * GOLD_PRICE_PER_TON_USD
        
        embed = discord.Embed(title=f"🪙 Резервы {self.country_name}", color=DARK_THEME_COLOR)
        embed.add_field(name="Золотой запас", value=f"{gold_tons:,.1f} тонн", inline=True)
        embed.add_field(name="Стоимость золота", value=f"${gold_value_usd:,.0f}", inline=True)
        embed.add_field(name="USD резервы", value=f"${usd_reserves:,.0f}", inline=True)
        embed.add_field(name="Всего резервов", value=f"${gold_value_usd + usd_reserves:,.0f}", inline=True)
        
        view = GoldReserveView(self.user_id, self.country_name, self.player_data)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="📉 Погасить долг", style=discord.ButtonStyle.secondary)
    async def repay_debt_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        modal = RepayDebtModal(self.user_id, self.country_name, self.player_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📊 Ключевая ставка", style=discord.ButtonStyle.secondary)
    async def rate_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        modal = InterestRateModal(self.user_id, self.country_name)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📈 Прогноз", style=discord.ButtonStyle.secondary)
    async def forecast_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        
        forecast = generate_economic_forecast(self.country_name, self.player_data)
        currency = get_currency_code(self.player_data["economy"])
        
        embed = discord.Embed(
            title=f"📊 Прогноз {self.country_name}",
            description=f"Ключевая ставка: {forecast['interest_rate']}%",
            color=DARK_THEME_COLOR
        )
        embed.add_field(name="Инфляция", value=f"{forecast['current_inflation']}% → {forecast['forecast_inflation']}%", inline=True)
        embed.add_field(name="Рост ВВП", value=f"{forecast['forecast_gdp_growth']}%", inline=True)
        embed.add_field(name="Долг", value=f"{format_billion(forecast['current_debt'])} → {format_billion(forecast['forecast_debt'])} {currency}", inline=True)
        embed.add_field(name="Бюджет", value=f"{format_billion(forecast['current_budget'])} → {format_billion(forecast['forecast_budget'])} {currency}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📜 История", style=discord.ButtonStyle.secondary)
    async def history_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        
        history = self.bank_data.get("history", [])
        if not history:
            embed = discord.Embed(title="📜 История", description="Нет операций", color=DARK_THEME_COLOR)
            return await interaction.response.edit_message(embed=embed, view=self)
        
        embed = discord.Embed(title=f"📜 История {self.country_name}", color=DARK_THEME_COLOR)
        for entry in history[-10:]:
            date = datetime.fromisoformat(entry["date"]).strftime("%d.%m.%Y")
            if entry["action"] == "print_money":
                value = f"💰 Эмиссия: {format_billion(entry['amount'])} {entry['currency']}"
            elif entry["action"] == "sell_gold":
                value = f"📉 Продажа золота: {entry['tons']:.1f} т за ${entry['revenue_usd']:,.0f}"
            elif entry["action"] == "buy_gold":
                value = f"📈 Покупка золота: {entry['tons']:.1f} т за ${entry['cost_usd']:,.0f}"
            elif entry["action"] == "repay_debt":
                value = f"📉 Погашение долга: {format_billion(entry['amount'])} {entry['currency']}"
            elif entry["action"] == "change_rate":
                value = f"📊 Ставка: {entry['old_rate']}% → {entry['new_rate']}%"
            else:
                value = str(entry)
            embed.add_field(name=date, value=value, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀ Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message("❌ Не ваше меню!", ephemeral=True)
        
        from bot import StateButtons
        view = StateButtons(self.user_id, self.country_name, self.player_data)
        
        state = self.player_data["state"]
        politics = self.player_data["politics"]
        economy = self.player_data["economy"]
        
        embed = discord.Embed(
            title=f"{state['statename']}",
            description=f"Лидер: {interaction.user.mention}",
            color=0x2b2d31
        )
        embed.add_field(name="Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name="Стабильность", value=f"{state['stability']:.1f}%", inline=True)
        embed.add_field(name="ВВП", value=f"{format_billion(get_gdp(economy))} {get_currency_code(economy)}", inline=True)
        embed.add_field(name="Бюджет", value=f"{format_billion(get_budget(economy))} {get_currency_code(economy)}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=view)


def create_bank_embed(country_name: str, player_data: Dict, bank_data: Dict) -> discord.Embed:
    """Создаёт embed с информацией о центробанке"""
    
    currency = get_currency_code(player_data["economy"])
    budget = get_budget(player_data["economy"])
    gdp = get_gdp(player_data["economy"])
    debt = get_debt(player_data["economy"])
    inflation = get_inflation(player_data["economy"])
    gold_tons = get_gold_tons(bank_data)
    usd_reserves = player_data["economy"].get("foreign_reserves", {}).get("USD", 0)
    interest_rate = bank_data.get("interest_rate", DEFAULT_INTEREST_RATE)
    
    embed = discord.Embed(
        title=f"🏦 Центральный банк {country_name}",
        color=DARK_THEME_COLOR
    )
    
    embed.add_field(name="📈 Ключевая ставка", value=f"{interest_rate}%", inline=True)
    embed.add_field(name="📊 Инфляция", value=f"{inflation:.2f}%", inline=True)
    embed.add_field(name="💵 Бюджет", value=f"{format_billion(budget)} {currency}", inline=True)
    embed.add_field(name="📈 ВВП", value=f"{format_billion(gdp)} {currency}", inline=True)
    embed.add_field(name="📉 Госдолг", value=f"{format_billion(debt)} {currency}", inline=True)
    embed.add_field(name="🪙 Золотой резерв", value=f"{gold_tons:,.1f} тонн", inline=True)
    embed.add_field(name="💵 USD резервы", value=f"${usd_reserves:,.0f}", inline=True)
    
    if gdp > 0:
        debt_to_gdp = (debt / gdp) * 100
        embed.add_field(name="Долг/ВВП", value=f"{debt_to_gdp:.1f}%", inline=True)
    
    return embed


# ==================== ОСНОВНАЯ КОМАНДА ====================

async def show_central_bank_menu(interaction_or_ctx, user_id: int):
    """Показать меню центрального банка"""
    
    states = load_states()
    
    player_data = None
    country_name = None
    
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            country_name = data["state"]["statename"]
            break
    
    if not player_data:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message("❌ У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("❌ У вас нет государства!")
        return
    
    bank_data = get_country_bank_data(country_name)
    embed = create_bank_embed(country_name, player_data, bank_data)
    view = CentralBankView(user_id, country_name, player_data)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_central_bank_menu',
    'print_money',
    'sell_gold_usd',
    'buy_gold_usd',
    'repay_debt',
    'set_interest_rate',
    'generate_economic_forecast',
    'GOLD_PRICE_PER_TON_USD'
]

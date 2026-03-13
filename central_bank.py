# central_bank.py - Модуль центрального банка и монетарной политики
# УПРОЩЕННАЯ ВЕРСИЯ (без денежной массы)

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from utils import format_billion, format_number, format_army_number, load_states, save_states, DARK_THEME_COLOR

# Файл для хранения данных центральных банков
CENTRAL_BANK_FILE = 'central_bank.json'

# ==================== КОНСТАНТЫ ====================

# Ключевая ставка по странам (в %)
BASE_INTEREST_RATES = {
    "США": 5.25,
    "Россия": 16.0,
    "Китай": 3.45,
    "Германия": 4.5,
    "Великобритания": 5.25,
    "Франция": 4.5,
    "Япония": 0.1,
    "Израиль": 4.5,
    "Украина": 15.0,
    "Иран": 18.0
}

# Целевая инфляция по странам (в %)
TARGET_INFLATION = {
    "США": 2.0,
    "Россия": 4.0,
    "Китай": 3.0,
    "Германия": 2.0,
    "Великобритания": 2.0,
    "Франция": 2.0,
    "Япония": 2.0,
    "Израиль": 2.0,
    "Украина": 5.0,
    "Иран": 10.0
}

# Золотовалютные резервы по странам (в тоннах)
BASE_GOLD_RESERVES = {
    "США": 8133.5,  # тонн золота
    "Россия": 2332.0,
    "Китай": 1948.0,
    "Германия": 3352.0,
    "Великобритания": 310.0,
    "Франция": 2436.0,
    "Япония": 846.0,
    "Израиль": 0.0,
    "Украина": 27.0,
    "Иран": 340.0
}

# Цена золота за тонну (в млрд $)
GOLD_PRICE_PER_TON = 0.06  # ~60 млн $ за тонну

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_central_bank_data():
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

def save_central_bank_data(data):
    """Сохранение данных центральных банков"""
    with open(CENTRAL_BANK_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_country_bank_data(country_name: str) -> Dict:
    """Получить данные центробанка для страны"""
    data = load_central_bank_data()
    
    if country_name not in data["banks"]:
        # Инициализируем данные для новой страны
        data["banks"][country_name] = {
            "interest_rate": BASE_INTEREST_RATES.get(country_name, 5.0),
            "gold_reserves": BASE_GOLD_RESERVES.get(country_name, 100.0),
            "inflation_forecast": TARGET_INFLATION.get(country_name, 2.0),
            "gdp_forecast": 2.0,
            "debt_forecast": 0.0,
            "budget_forecast": 0.0,
            "last_updated": str(datetime.now()),
            "history": []
        }
        save_central_bank_data(data)
    
    return data["banks"][country_name]

def update_country_bank_data(country_name: str, bank_data: Dict):
    """Обновить данные центробанка для страны"""
    data = load_central_bank_data()
    data["banks"][country_name] = bank_data
    data["banks"][country_name]["last_updated"] = str(datetime.now())
    save_central_bank_data(data)

# ==================== ФУНКЦИИ ЦЕНТРОБАНКА ====================

def print_money(country_name: str, amount_billions: float, player_data: Dict) -> Dict:
    """
    Печать денег (эмиссия)
    Увеличивает бюджет, но повышает инфляцию
    """
    bank_data = get_country_bank_data(country_name)
    
    # Добавляем деньги в бюджет
    player_data["economy"]["budget"] += amount_billions * 1_000_000_000
    
    # Рост инфляции (чем больше эмиссия, тем сильнее)
    # Используем ВВП как базу для расчета
    gdp = player_data["economy"]["gdp"] / 1_000_000_000
    inflation_increase = (amount_billions / gdp) * 100 * 2.0
    player_data["economy"]["inflation"] += inflation_increase
    
    # Записываем в историю
    if "history" not in bank_data:
        bank_data["history"] = []
    
    bank_data["history"].append({
        "date": str(datetime.now()),
        "action": "print_money",
        "amount": amount_billions,
        "inflation_impact": round(inflation_increase, 2),
        "new_budget": player_data["economy"]["budget"] / 1_000_000_000
    })
    
    update_country_bank_data(country_name, bank_data)
    
    return {
        "success": True,
        "printed": amount_billions,
        "inflation_increase": round(inflation_increase, 2),
        "new_inflation": round(player_data["economy"]["inflation"], 2),
        "new_budget": round(player_data["economy"]["budget"] / 1_000_000_000, 2)
    }

def sell_gold(country_name: str, tons: float, player_data: Dict) -> Dict:
    """
    Продажа золота из резервов
    Увеличивает бюджет, уменьшает золотые резервы
    """
    bank_data = get_country_bank_data(country_name)
    
    if bank_data["gold_reserves"] < tons:
        return {
            "success": False,
            "message": f"Недостаточно золота! Доступно: {bank_data['gold_reserves']:.1f} тонн"
        }
    
    # Списываем золото
    bank_data["gold_reserves"] -= tons
    
    # Добавляем деньги в бюджет (по текущей цене)
    revenue = tons * GOLD_PRICE_PER_TON * 1_000_000_000  # в долларах
    player_data["economy"]["budget"] += revenue
    
    # Небольшое влияние на инфляцию (продажа золота немного укрепляет валюту)
    player_data["economy"]["inflation"] = max(0, player_data["economy"]["inflation"] - 0.1 * tons)
    
    # Записываем в историю
    if "history" not in bank_data:
        bank_data["history"] = []
    
    bank_data["history"].append({
        "date": str(datetime.now()),
        "action": "sell_gold",
        "tons": tons,
        "revenue": revenue / 1_000_000_000,
        "new_gold_reserves": bank_data["gold_reserves"]
    })
    
    update_country_bank_data(country_name, bank_data)
    
    return {
        "success": True,
        "sold": tons,
        "revenue": revenue / 1_000_000_000,
        "new_gold_reserves": bank_data["gold_reserves"],
        "inflation_change": -0.1 * tons
    }

def buy_gold(country_name: str, tons: float, player_data: Dict) -> Dict:
    """
    Покупка золота в резервы
    Уменьшает бюджет, увеличивает золотые резервы
    """
    bank_data = get_country_bank_data(country_name)
    
    # Стоимость покупки
    cost = tons * GOLD_PRICE_PER_TON * 1_000_000_000  # в долларах
    
    if player_data["economy"]["budget"] < cost:
        return {
            "success": False,
            "message": f"Недостаточно средств! Нужно: {format_billion(cost)}"
        }
    
    # Списываем деньги
    player_data["economy"]["budget"] -= cost
    
    # Добавляем золото
    bank_data["gold_reserves"] += tons
    
    # Небольшое влияние на инфляцию (покупка золота немного повышает инфляцию)
    player_data["economy"]["inflation"] += 0.05 * tons
    
    # Записываем в историю
    if "history" not in bank_data:
        bank_data["history"] = []
    
    bank_data["history"].append({
        "date": str(datetime.now()),
        "action": "buy_gold",
        "tons": tons,
        "cost": cost / 1_000_000_000,
        "new_gold_reserves": bank_data["gold_reserves"]
    })
    
    update_country_bank_data(country_name, bank_data)
    
    return {
        "success": True,
        "bought": tons,
        "cost": cost / 1_000_000_000,
        "new_gold_reserves": bank_data["gold_reserves"],
        "inflation_change": 0.05 * tons
    }

def repay_debt(country_name: str, amount_billions: float, player_data: Dict) -> Dict:
    """
    Погашение государственного долга
    Уменьшает бюджет и долг
    """
    current_debt = player_data["economy"]["debt"] / 1_000_000_000  # в млрд
    
    if amount_billions > current_debt:
        amount_billions = current_debt
    
    cost = amount_billions * 1_000_000_000
    
    if player_data["economy"]["budget"] < cost:
        return {
            "success": False,
            "message": f"Недостаточно средств! Нужно: {format_billion(cost)}"
        }
    
    # Списываем деньги
    player_data["economy"]["budget"] -= cost
    
    # Уменьшаем долг
    player_data["economy"]["debt"] -= cost
    
    # Улучшаем кредитный рейтинг (снижаем инфляцию)
    player_data["economy"]["inflation"] = max(0, player_data["economy"]["inflation"] - 0.1 * (amount_billions / 100))
    
    bank_data = get_country_bank_data(country_name)
    
    # Записываем в историю
    if "history" not in bank_data:
        bank_data["history"] = []
    
    bank_data["history"].append({
        "date": str(datetime.now()),
        "action": "repay_debt",
        "amount": amount_billions,
        "new_debt": player_data["economy"]["debt"] / 1_000_000_000
    })
    
    update_country_bank_data(country_name, bank_data)
    
    return {
        "success": True,
        "repaid": amount_billions,
        "new_debt": player_data["economy"]["debt"] / 1_000_000_000,
        "remaining_budget": player_data["economy"]["budget"] / 1_000_000_000
    }

def set_interest_rate(country_name: str, new_rate: float) -> Dict:
    """
    Изменение ключевой ставки
    Влияет на инфляцию и экономический рост
    """
    bank_data = get_country_bank_data(country_name)
    
    old_rate = bank_data["interest_rate"]
    bank_data["interest_rate"] = new_rate
    
    # Записываем в историю
    if "history" not in bank_data:
        bank_data["history"] = []
    
    bank_data["history"].append({
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
    """
    Генерирует прогноз экономических показателей на следующий год
    """
    bank_data = get_country_bank_data(country_name)
    
    current_inflation = player_data["economy"]["inflation"]
    current_gdp = player_data["economy"]["gdp"] / 1_000_000_000
    current_debt = player_data["economy"]["debt"] / 1_000_000_000
    current_budget = player_data["economy"]["budget"] / 1_000_000_000
    interest_rate = bank_data["interest_rate"]
    
    # Прогноз инфляции
    if current_inflation > TARGET_INFLATION.get(country_name, 2.0) * 1.5:
        # Высокая инфляция - центробанк будет поднимать ставку
        inflation_forecast = current_inflation * random.uniform(0.9, 1.1)
    elif current_inflation < TARGET_INFLATION.get(country_name, 2.0) * 0.5:
        # Низкая инфляция - стимулирование
        inflation_forecast = current_inflation * random.uniform(1.1, 1.3)
    else:
        # Нормальная инфляция
        inflation_forecast = current_inflation * random.uniform(0.95, 1.05)
    
    # Прогноз роста ВВП
    # Влияние ставки (высокая ставка тормозит рост)
    rate_impact = 1.0 - (interest_rate - 2.0) / 20.0
    rate_impact = max(0.5, min(1.5, rate_impact))
    
    # Влияние долга (высокий долг тормозит рост)
    debt_to_gdp = current_debt / current_gdp if current_gdp > 0 else 0
    debt_impact = 1.0 - debt_to_gdp * 0.3
    debt_impact = max(0.7, min(1.3, debt_impact))
    
    base_growth = random.uniform(1.5, 3.5)
    gdp_forecast = base_growth * rate_impact * debt_impact
    
    # Прогноз изменения долга
    if current_debt > current_gdp * 0.8:
        # Критический долг
        debt_change_forecast = current_debt * random.uniform(1.05, 1.15)
    elif current_debt > current_gdp * 0.5:
        # Высокий долг
        debt_change_forecast = current_debt * random.uniform(1.0, 1.08)
    else:
        # Нормальный долг
        debt_change_forecast = current_debt * random.uniform(0.95, 1.05)
    
    # Прогноз бюджета
    budget_forecast = current_budget * random.uniform(0.9, 1.2)
    
    # Сохраняем прогноз
    bank_data["inflation_forecast"] = round(inflation_forecast, 2)
    bank_data["gdp_forecast"] = round(gdp_forecast, 2)
    bank_data["debt_forecast"] = round(debt_change_forecast, 2)
    bank_data["budget_forecast"] = round(budget_forecast, 2)
    bank_data["forecast_date"] = str(datetime.now())
    
    update_country_bank_data(country_name, bank_data)
    
    return {
        "current_inflation": round(current_inflation, 2),
        "forecast_inflation": round(inflation_forecast, 2),
        "current_gdp_growth": player_data["economy"].get("gdp_growth", 2.0),
        "forecast_gdp_growth": round(gdp_forecast, 2),
        "current_debt": round(current_debt, 2),
        "forecast_debt": round(debt_change_forecast, 2),
        "current_budget": round(current_budget, 2),
        "forecast_budget": round(budget_forecast, 2),
        "interest_rate": interest_rate,
        "rate_impact": round(rate_impact, 2),
        "debt_impact": round(debt_impact, 2)
    }

# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class CentralBankView(View):
    """Главное меню центробанка"""
    
    def __init__(self, user_id: int, country_name: str, player_data: Dict, bank_data: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.bank_data = bank_data
    
    @discord.ui.button(label="Печать денег", style=discord.ButtonStyle.secondary)
    async def print_money_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        modal = PrintMoneyModal(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Золотой резерв", style=discord.ButtonStyle.secondary)
    async def gold_reserve_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🪙 Золотой резерв {self.country_name}",
            color=DARK_THEME_COLOR
        )
        
        gold_tons = self.bank_data["gold_reserves"]
        gold_value = gold_tons * GOLD_PRICE_PER_TON
        
        embed.add_field(name="Запас золота", value=f"{gold_tons:,.1f} тонн", inline=True)
        embed.add_field(name="Стоимость", value=f"{gold_value:.1f} млрд $", inline=True)
        embed.add_field(name="Цена за тонну", value=f"{GOLD_PRICE_PER_TON:.3f} млрд $", inline=True)
        
        view = GoldReserveView(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Погашение долга", style=discord.ButtonStyle.secondary)
    async def repay_debt_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        modal = RepayDebtModal(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Прогноз ЦБ", style=discord.ButtonStyle.secondary)
    async def forecast_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        forecast = generate_economic_forecast(self.country_name, self.player_data)
        
        embed = discord.Embed(
            title=f"📊 Экономический прогноз {self.country_name}",
            description=f"Прогноз на следующий год\nКлючевая ставка: {forecast['interest_rate']}%",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(
            name="📈 Инфляция",
            value=f"Текущая: {forecast['current_inflation']}%\nПрогноз: {forecast['forecast_inflation']}%",
            inline=True
        )
        embed.add_field(
            name="📈 Рост ВВП",
            value=f"Текущий: {forecast['current_gdp_growth']}%\nПрогноз: {forecast['forecast_gdp_growth']}%",
            inline=True
        )
        embed.add_field(
            name="💰 Госдолг",
            value=f"Текущий: {forecast['current_debt']:.1f} млрд $\nПрогноз: {forecast['forecast_debt']:.1f} млрд $",
            inline=True
        )
        embed.add_field(
            name="💵 Бюджет",
            value=f"Текущий: {forecast['current_budget']:.1f} млрд $\nПрогноз: {forecast['forecast_budget']:.1f} млрд $",
            inline=True
        )
        embed.add_field(
            name="⚖️ Влияние ставки",
            value=f"x{forecast['rate_impact']}",
            inline=True
        )
        embed.add_field(
            name="📊 Влияние долга",
            value=f"x{forecast['debt_impact']}",
            inline=True
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="История", style=discord.ButtonStyle.secondary)
    async def history_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        if not self.bank_data.get("history"):
            embed = discord.Embed(
                title="📜 История операций",
                description="История операций пуста",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        embed = discord.Embed(
            title=f"📜 История операций ЦБ {self.country_name}",
            color=DARK_THEME_COLOR
        )
        
        for entry in self.bank_data["history"][-5:]:
            date = datetime.fromisoformat(entry["date"]).strftime("%d.%m.%Y")
            
            if entry["action"] == "print_money":
                value = f"💰 Эмиссия: +{entry['amount']} млрд $ (инфляция +{entry['inflation_impact']}%)"
            elif entry["action"] == "sell_gold":
                value = f"🪙 Продажа золота: {entry['tons']} т на {entry['revenue']} млрд $"
            elif entry["action"] == "buy_gold":
                value = f"🪙 Покупка золота: {entry['tons']} т за {entry['cost']} млрд $"
            elif entry["action"] == "repay_debt":
                value = f"📉 Погашение долга: {entry['amount']} млрд $"
            elif entry["action"] == "change_rate":
                value = f"📊 Изменение ставки: {entry['old_rate']}% → {entry['new_rate']}%"
            else:
                value = str(entry)
            
            embed.add_field(name=date, value=value, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀ Назад", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Возвращаемся в главное меню государства
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
        embed.add_field(name="Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name="Стабильность", value=f"{state['stability']}%", inline=True)
        embed.add_field(name="Правительство", value=state['government_type'], inline=True)
        embed.add_field(name="Правящая партия", value=politics['ruling_party'], inline=True)
        embed.add_field(name="Популярность", value=f"{politics['popularity']}%", inline=True)
        embed.add_field(name="ВВП", value=format_billion(economy['gdp']), inline=True)
        embed.add_field(name="Бюджет", value=format_billion(economy['budget']), inline=True)
        embed.add_field(name="Налог", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        embed.add_field(name="Армия", value=f"{format_army_number(state['army_size'])} чел.", inline=True)
        embed.add_field(name="Опытность", value=f"{state.get('army_experience', 50):.0f}%", inline=True)
        embed.add_field(name="Военный бюджет", value=format_billion(economy['military_budget']), inline=True)
        embed.add_field(name="Счастье", value=f"{state['happiness']}%", inline=True)
        embed.add_field(name="Доверие", value=f"{state['trust']}%", inline=True)
        embed.add_field(name="Эффективность", value=f"{self.player_data['government_efficiency']}%", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=view)


class GoldReserveView(View):
    """Меню управления золотым резервом"""
    
    def __init__(self, user_id: int, country_name: str, player_data: Dict, bank_data: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.bank_data = bank_data
    
    @discord.ui.button(label="Продать золото", style=discord.ButtonStyle.secondary)
    async def sell_gold_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        modal = GoldSellModal(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Купить золото", style=discord.ButtonStyle.secondary)
    async def buy_gold_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        modal = GoldBuyModal(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="◀ Назад", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = create_bank_embed(self.country_name, self.player_data, self.bank_data)
        view = CentralBankView(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.edit_message(embed=embed, view=view)


class PrintMoneyModal(Modal, title="Печать денег"):
    def __init__(self, user_id: int, country_name: str, player_data: Dict, bank_data: Dict):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.bank_data = bank_data
        
        gdp = player_data["economy"]["gdp"] / 1_000_000_000
        max_print = gdp * 0.1  # Максимум 10% ВВП
        
        self.amount_input = TextInput(
            label=f"Сумма эмиссии (млрд $, макс: {max_print:.0f})",
            placeholder="Например: 100",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            amount = float(self.amount_input.value)
            if amount <= 0:
                await interaction.response.send_message("❌ Сумма должна быть положительной!", ephemeral=True)
                return
            
            gdp = self.player_data["economy"]["gdp"] / 1_000_000_000
            max_print = gdp * 0.1
            if amount > max_print:
                await interaction.response.send_message(f"❌ Слишком большая сумма! Максимум {max_print:.0f} млрд $ (10% ВВП)", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        result = print_money(self.country_name, amount, self.player_data)
        
        # Обновляем данные в states
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country_name:
                data["economy"]["budget"] = self.player_data["economy"]["budget"]
                data["economy"]["inflation"] = self.player_data["economy"]["inflation"]
                break
        save_states(states)
        
        # Обновляем bank_data
        self.bank_data = get_country_bank_data(self.country_name)
        
        embed = discord.Embed(
            title="💰 Эмиссия выполнена",
            description=f"В бюджет добавлено {amount} млрд $",
            color=discord.Color.green()
        )
        embed.add_field(name="Новый бюджет", value=f"{result['new_budget']} млрд $", inline=True)
        embed.add_field(name="Рост инфляции", value=f"+{result['inflation_increase']}%", inline=True)
        embed.add_field(name="Новая инфляция", value=f"{result['new_inflation']}%", inline=True)
        
        view = CentralBankView(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.edit_message(embed=embed, view=view)


class GoldSellModal(Modal, title="Продажа золота"):
    def __init__(self, user_id: int, country_name: str, player_data: Dict, bank_data: Dict):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.bank_data = bank_data
        
        self.amount_input = TextInput(
            label="Количество золота (тонн)",
            placeholder=f"Доступно: {bank_data['gold_reserves']:.1f} т",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            tons = float(self.amount_input.value)
            if tons <= 0:
                await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        result = sell_gold(self.country_name, tons, self.player_data)
        
        if not result["success"]:
            await interaction.response.send_message(f"❌ {result['message']}", ephemeral=True)
            return
        
        # Обновляем данные в states
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country_name:
                data["economy"]["budget"] = self.player_data["economy"]["budget"]
                data["economy"]["inflation"] = self.player_data["economy"]["inflation"]
                break
        save_states(states)
        
        # Обновляем bank_data
        self.bank_data = get_country_bank_data(self.country_name)
        
        embed = discord.Embed(
            title="🪙 Золото продано",
            color=discord.Color.green()
        )
        embed.add_field(name="Продано", value=f"{result['sold']} тонн", inline=True)
        embed.add_field(name="Выручка", value=f"{result['revenue']} млрд $", inline=True)
        embed.add_field(name="Остаток золота", value=f"{result['new_gold_reserves']:.1f} тонн", inline=True)
        embed.add_field(name="Изменение инфляции", value=f"{result['inflation_change']:.1f}%", inline=True)
        
        view = GoldReserveView(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.edit_message(embed=embed, view=view)


class GoldBuyModal(Modal, title="Покупка золота"):
    def __init__(self, user_id: int, country_name: str, player_data: Dict, bank_data: Dict):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.bank_data = bank_data
        
        self.amount_input = TextInput(
            label="Количество золота (тонн)",
            placeholder="Например: 10",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            tons = float(self.amount_input.value)
            if tons <= 0:
                await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        result = buy_gold(self.country_name, tons, self.player_data)
        
        if not result["success"]:
            await interaction.response.send_message(f"❌ {result['message']}", ephemeral=True)
            return
        
        # Обновляем данные в states
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country_name:
                data["economy"]["budget"] = self.player_data["economy"]["budget"]
                data["economy"]["inflation"] = self.player_data["economy"]["inflation"]
                break
        save_states(states)
        
        # Обновляем bank_data
        self.bank_data = get_country_bank_data(self.country_name)
        
        embed = discord.Embed(
            title="🪙 Золото куплено",
            color=discord.Color.green()
        )
        embed.add_field(name="Куплено", value=f"{result['bought']} тонн", inline=True)
        embed.add_field(name="Стоимость", value=f"{result['cost']} млрд $", inline=True)
        embed.add_field(name="Новый запас", value=f"{result['new_gold_reserves']:.1f} тонн", inline=True)
        embed.add_field(name="Изменение инфляции", value=f"+{result['inflation_change']:.1f}%", inline=True)
        
        view = GoldReserveView(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.edit_message(embed=embed, view=view)


class RepayDebtModal(Modal, title="Погашение долга"):
    def __init__(self, user_id: int, country_name: str, player_data: Dict, bank_data: Dict):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.bank_data = bank_data
        
        current_debt = player_data["economy"]["debt"] / 1_000_000_000
        current_budget = player_data["economy"]["budget"] / 1_000_000_000
        
        self.amount_input = TextInput(
            label=f"Сумма погашения (млрд $, бюджет: {current_budget:.1f})",
            placeholder=f"Долг: {current_debt:.1f} млрд $",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.amount_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            amount = float(self.amount_input.value)
            if amount <= 0:
                await interaction.response.send_message("❌ Сумма должна быть положительной!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        result = repay_debt(self.country_name, amount, self.player_data)
        
        if not result["success"]:
            await interaction.response.send_message(f"❌ {result['message']}", ephemeral=True)
            return
        
        # Обновляем данные в states
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country_name:
                data["economy"]["budget"] = self.player_data["economy"]["budget"]
                data["economy"]["debt"] = self.player_data["economy"]["debt"]
                break
        save_states(states)
        
        embed = discord.Embed(
            title="📉 Долг погашен",
            color=discord.Color.green()
        )
        embed.add_field(name="Погашено", value=f"{result['repaid']} млрд $", inline=True)
        embed.add_field(name="Новый долг", value=f"{result['new_debt']:.1f} млрд $", inline=True)
        embed.add_field(name="Остаток бюджета", value=f"{result['remaining_budget']:.1f} млрд $", inline=True)
        
        view = CentralBankView(self.user_id, self.country_name, self.player_data, self.bank_data)
        await interaction.response.edit_message(embed=embed, view=view)


def create_bank_embed(country_name: str, player_data: Dict, bank_data: Dict) -> discord.Embed:
    """Создает embed с информацией о центробанке"""
    
    budget = player_data["economy"]["budget"] / 1_000_000_000
    debt = player_data["economy"]["debt"] / 1_000_000_000
    inflation = player_data["economy"]["inflation"]
    gdp = player_data["economy"]["gdp"] / 1_000_000_000
    
    gold_tons = bank_data["gold_reserves"]
    gold_value = gold_tons * GOLD_PRICE_PER_TON
    
    debt_to_gdp = (debt / gdp * 100) if gdp > 0 else 0
    
    embed = discord.Embed(
        title=f"🏦 Центральный банк {country_name}",
        color=DARK_THEME_COLOR
    )
    
    embed.add_field(name="📈 Ключевая ставка", value=f"{bank_data['interest_rate']}%", inline=True)
    embed.add_field(name="📊 Инфляция", value=f"{inflation:.1f}%", inline=True)
    embed.add_field(name="💵 Бюджет", value=f"{budget:.1f} млрд $", inline=True)
    
    embed.add_field(name="🪙 Золотой резерв", value=f"{gold_tons:.1f} т ({gold_value:.1f} млрд $)", inline=True)
    embed.add_field(name="📉 Госдолг", value=f"{debt:.1f} млрд $ ({debt_to_gdp:.1f}% ВВП)", inline=True)
    embed.add_field(name="📈 ВВП", value=f"{gdp:.1f} млрд $", inline=True)
    
    # Проверяем наличие всех полей прогноза
    if ("inflation_forecast" in bank_data and "gdp_forecast" in bank_data 
        and "debt_forecast" in bank_data and "budget_forecast" in bank_data):
        embed.add_field(
            name="📊 Прогноз на год",
            value=f"📈 Инфляция: {bank_data['inflation_forecast']}%\n"
                  f"📈 Рост ВВП: {bank_data['gdp_forecast']}%\n"
                  f"💰 Долг: {bank_data['debt_forecast']:.1f} млрд $\n"
                  f"💵 Бюджет: {bank_data['budget_forecast']:.1f} млрд $",
            inline=False
        )
    
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
    view = CentralBankView(user_id, country_name, player_data, bank_data)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view, ephemeral=True)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_central_bank_menu',
    'print_money',
    'sell_gold',
    'buy_gold',
    'repay_debt',
    'set_interest_rate',
    'generate_economic_forecast',
    'BASE_GOLD_RESERVES',
    'GOLD_PRICE_PER_TON'
]

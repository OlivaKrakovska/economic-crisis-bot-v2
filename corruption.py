# corruption.py - Модуль для управления коррупцией
# НОВАЯ ВЕРСИЯ: медленное снижение, расходы на бюро, затраты политвласти
# ИСПРАВЛЕНО: поддержка двухвалютной системы

import discord
from discord.ui import Button, View, Modal, TextInput
import json
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from utils import format_billion, format_number, load_states, save_states, DARK_THEME_COLOR
from paths import get_data_path

# Файл для хранения данных о коррупции
CORRUPTION_FILE = get_data_path('corruption.json')

# ID канала для логов
try:
    from config import ADMIN_LOG_CHANNEL_ID
except ImportError:
    ADMIN_LOG_CHANNEL_ID = None

# ==================== РЕАЛЬНЫЕ УРОВНИ КОРРУПЦИИ ПО СТРАНАМ ====================
STARTING_CORRUPTION = {
    "США": 3.1, "Россия": 7.4, "Китай": 5.8, "Германия": 2.2,
    "Великобритания": 2.7, "Франция": 2.8, "Япония": 2.7, "Израиль": 3.8,
    "Украина": 6.4, "Иран": 7.5, "Беларусь": 6.0, "Норвегия": 1.6,
    "КНДР": 8.0, "Турция": 6.4, "Сирия": 8.5, "Канада": 2.4,
    "Польша": 4.6, "Бразилия": 6.4, "Швеция": 1.8, "Финляндия": 1.3,
    "Швейцария": 1.8, "Египет": 6.5
}

# Минимальный и максимальный уровни коррупции
MIN_CORRUPTION = 0.5
MAX_CORRUPTION = 15.0

# Базовое ежемесячное изменение (без учёта бюро)
BASE_CORRUPTION_CHANGE = {
    "min": -0.05,
    "max": 0.15
}

# Влияние различных факторов на коррупцию
FACTORS = {
    "government_efficiency": {
        "threshold": 50,
        "effect": -0.003
    },
    "stability": {
        "threshold": 50,
        "effect": -0.002
    },
    "debt_to_gdp": {
        "threshold": 60,
        "effect": 0.005,
        "max_effect": 0.2
    }
}

# Параметры антикоррупционного бюро
ANTI_CORRUPTION_BUREAU = {
    "base_cost": 100000000,
    "effectiveness": {
        "min": 0.01,
        "max": 0.15
    },
    "funding_multiplier": 0.000000001,
    "max_funding": 2000000000,
    "corruption_resistance": {
        0: 1.0,
        2: 0.8,
        4: 0.6,
        6: 0.4,
        8: 0.2,
        10: 0.1
    },
    "political_power_cost": 2
}

# ==================== ФУНКЦИИ ДЛЯ БЕЗОПАСНОЙ РАБОТЫ С БЮДЖЕТОМ ====================

def get_budget(economy):
    """Безопасно получает бюджет"""
    if not economy:
        return 0
    if "local_currency" in economy:
        return economy["local_currency"].get("amount", 0)
    if "budget_usd" in economy:
        return economy["budget_usd"]
    if "budget" in economy:
        return economy["budget"]
    return 0


def subtract_from_budget(economy, amount):
    """Безопасно вычитает из бюджета"""
    if not economy:
        return
    if "local_currency" in economy:
        economy["local_currency"]["amount"] = economy["local_currency"].get("amount", 0) - amount
    elif "budget_usd" in economy:
        economy["budget_usd"] -= amount
    else:
        economy["budget"] = economy.get("budget", 0) - amount


# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_corruption_data():
    """Загрузка данных о коррупции"""
    try:
        with open(CORRUPTION_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"countries": {}}
            return json.loads(content)
    except FileNotFoundError:
        return {"countries": {}}
    except json.JSONDecodeError:
        return {"countries": {}}


def save_corruption_data(data):
    """Сохранение данных о коррупции"""
    with open(CORRUPTION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_country_corruption(country_name: str) -> Dict:
    """Получить данные о коррупции для страны"""
    data = load_corruption_data()
    
    if country_name not in data["countries"]:
        data["countries"][country_name] = {
            "level": STARTING_CORRUPTION.get(country_name, 3.0),
            "history": [{
                "date": str(datetime.now()),
                "level": STARTING_CORRUPTION.get(country_name, 3.0),
                "reason": "Начальное значение"
            }],
            "last_update": str(datetime.now()),
            "total_stolen": 0,
            "bureau_funding": 0,
            "bureau_active": False,
            "last_payment": None,
            "political_power_spent": 0
        }
        save_corruption_data(data)
    
    return data["countries"][country_name]


def update_country_corruption(country_name: str, corruption_data: Dict):
    """Обновить данные о коррупции для страны"""
    data = load_corruption_data()
    data["countries"][country_name] = corruption_data
    data["countries"][country_name]["last_update"] = str(datetime.now())
    save_corruption_data(data)


# ==================== ФУНКЦИИ ДЛЯ РАСЧЁТА КОРРУПЦИИ ====================

def calculate_corruption_loss(budget: float, corruption_level: float) -> float:
    """1% коррупции = 0.1% потерь бюджета"""
    loss_percent = corruption_level / 10
    return budget * (loss_percent / 100)


def get_corruption_resistance(level: float) -> float:
    """Получить сопротивление коррупции в зависимости от уровня"""
    if level < 2:
        return ANTI_CORRUPTION_BUREAU["corruption_resistance"][0]
    elif level < 4:
        return ANTI_CORRUPTION_BUREAU["corruption_resistance"][2]
    elif level < 6:
        return ANTI_CORRUPTION_BUREAU["corruption_resistance"][4]
    elif level < 8:
        return ANTI_CORRUPTION_BUREAU["corruption_resistance"][6]
    elif level < 10:
        return ANTI_CORRUPTION_BUREAU["corruption_resistance"][8]
    else:
        return ANTI_CORRUPTION_BUREAU["corruption_resistance"][10]


def calculate_bureau_effectiveness(funding: float, corruption_level: float) -> float:
    """Рассчитывает снижение коррупции от работы бюро за месяц"""
    if funding <= 0:
        return 0.0
    
    effective_funding = min(funding, ANTI_CORRUPTION_BUREAU["max_funding"])
    base_reduction = effective_funding * ANTI_CORRUPTION_BUREAU["funding_multiplier"]
    resistance = get_corruption_resistance(corruption_level)
    base_reduction *= resistance
    variance = random.uniform(0.8, 1.2)
    base_reduction *= variance
    base_reduction = min(ANTI_CORRUPTION_BUREAU["effectiveness"]["max"], 
                        max(ANTI_CORRUPTION_BUREAU["effectiveness"]["min"], base_reduction))
    return base_reduction


def calculate_natural_change(player_data: Dict, current_level: float) -> float:
    """Рассчитывает естественное изменение коррупции за месяц"""
    change = random.uniform(BASE_CORRUPTION_CHANGE["min"], BASE_CORRUPTION_CHANGE["max"])
    
    gov_eff = player_data.get("government_efficiency", 50)
    if gov_eff > FACTORS["government_efficiency"]["threshold"]:
        bonus = (gov_eff - FACTORS["government_efficiency"]["threshold"]) / 10 * FACTORS["government_efficiency"]["effect"]
        change += bonus
    
    stability = player_data["state"].get("stability", 50)
    if stability > FACTORS["stability"]["threshold"]:
        bonus = (stability - FACTORS["stability"]["threshold"]) / 10 * FACTORS["stability"]["effect"]
        change += bonus
    
    gdp = player_data["economy"].get("gdp", 1)
    debt = player_data["economy"].get("debt", 0)
    debt_to_gdp = (debt / gdp) * 100 if gdp > 0 else 0
    
    if debt_to_gdp > FACTORS["debt_to_gdp"]["threshold"]:
        penalty = (debt_to_gdp - FACTORS["debt_to_gdp"]["threshold"]) / 10 * FACTORS["debt_to_gdp"]["effect"]
        penalty = min(FACTORS["debt_to_gdp"]["max_effect"], max(0, penalty))
        change += penalty
    
    return change


def apply_corruption(player_data: Dict, corruption_data: Dict) -> Tuple[float, float, float, float]:
    """Применяет эффекты коррупции к государству за месяц"""
    economy = player_data["economy"]
    budget = get_budget(economy)
    current_level = corruption_data["level"]
    
    # Рассчитываем потери
    loss = calculate_corruption_loss(budget, current_level)
    subtract_from_budget(economy, loss)
    
    # Обновляем статистику
    corruption_data["total_stolen"] = corruption_data.get("total_stolen", 0) + loss
    
    # Естественное изменение
    natural_change = calculate_natural_change(player_data, current_level)
    
    # Эффект от бюро
    bureau_reduction = 0
    political_power_cost = 0
    
    if corruption_data.get("bureau_active", False):
        funding = corruption_data.get("bureau_funding", 0)
        current_budget = get_budget(economy)
        
        if funding > 0 and current_budget >= funding:
            subtract_from_budget(economy, funding)
            bureau_reduction = calculate_bureau_effectiveness(funding, current_level)
            
            political_power_cost = ANTI_CORRUPTION_BUREAU["political_power_cost"]
            player_data["politics"]["political_power"] = max(0, 
                player_data["politics"].get("political_power", 100) - political_power_cost)
            
            corruption_data["political_power_spent"] = corruption_data.get("political_power_spent", 0) + political_power_cost
            corruption_data["last_payment"] = str(datetime.now())
        else:
            corruption_data["bureau_active"] = False
            corruption_data["bureau_funding"] = 0
    
    total_change = natural_change - bureau_reduction
    new_level = current_level + total_change
    new_level = max(MIN_CORRUPTION, min(MAX_CORRUPTION, new_level))
    
    return loss, new_level, total_change, political_power_cost


# ==================== ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ БЮРО ====================

def set_bureau_funding(player_data: Dict, corruption_data: Dict, funding: float) -> Tuple[bool, str]:
    """Устанавливает финансирование антикоррупционного бюро"""
    if funding < 0:
        return False, "Сумма не может быть отрицательной"
    
    if funding == 0:
        corruption_data["bureau_active"] = False
        corruption_data["bureau_funding"] = 0
        return True, "Антикоррупционное бюро остановлено"
    
    if funding < ANTI_CORRUPTION_BUREAU["base_cost"] / 2:
        return False, f"Минимальное финансирование: {format_billion(ANTI_CORRUPTION_BUREAU['base_cost'] / 2)}"
    
    budget = get_budget(player_data["economy"])
    if budget < funding:
        return False, f"Недостаточно средств! Нужно: {format_billion(funding)}"
    
    political_power = player_data["politics"].get("political_power", 100)
    if political_power < ANTI_CORRUPTION_BUREAU["political_power_cost"]:
        return False, f"Недостаточно политической власти! Нужно: {ANTI_CORRUPTION_BUREAU['political_power_cost']}"
    
    corruption_data["bureau_active"] = True
    corruption_data["bureau_funding"] = funding
    return True, f"Бюро активировано с финансированием {format_billion(funding)} в месяц"


# ==================== ФУНКЦИИ ДЛЯ СОЗДАНИЯ EMBED ====================

def create_corruption_embed(country_name: str, player_data: Dict, corruption_data: Dict) -> discord.Embed:
    """Создаёт Embed с информацией о коррупции"""
    level = corruption_data["level"]
    budget = get_budget(player_data["economy"])
    monthly_loss = calculate_corruption_loss(budget, level)
    loss_percent = (monthly_loss / budget * 100) if budget > 0 else 0
    
    if level < 2:
        status, color = "Очень низкий", discord.Color.green()
    elif level < 4:
        status, color = "Низкий", discord.Color.green()
    elif level < 6:
        status, color = "Средний", discord.Color.gold()
    elif level < 8:
        status, color = "Высокий", discord.Color.orange()
    else:
        status, color = "Критический", discord.Color.red()
    
    embed = discord.Embed(
        title=f"Коррупция в {country_name}",
        description=f"**Уровень: {level:.2f}%** ({status})",
        color=color
    )
    
    embed.add_field(name="Потери в месяц", value=f"{format_billion(monthly_loss)} ({loss_percent:.2f}% бюджета)", inline=True)
    embed.add_field(name="Всего украдено", value=f"{format_billion(corruption_data.get('total_stolen', 0))}", inline=True)
    
    bureau_active = corruption_data.get("bureau_active", False)
    bureau_funding = corruption_data.get("bureau_funding", 0)
    
    if bureau_active and bureau_funding > 0:
        effectiveness = calculate_bureau_effectiveness(bureau_funding, level)
        resistance = get_corruption_resistance(level)
        bureau_status = f"Активно\nФинансирование: {format_billion(bureau_funding)}/мес\nСнижение: ~{effectiveness:.2f}%/мес\nЭффективность: {resistance*100:.0f}%"
    else:
        bureau_status = "Не активно"
    
    embed.add_field(name="Антикоррупционное бюро", value=bureau_status, inline=False)
    
    natural = calculate_natural_change(player_data, level)
    bureau_effect = calculate_bureau_effectiveness(bureau_funding, level) if bureau_active else 0
    trend = f"Рост +{(natural - bureau_effect):.2f}%" if (natural - bureau_effect) > 0 else f"Снижение {(natural - bureau_effect):.2f}%"
    embed.add_field(name="Тенденция", value=trend, inline=True)
    
    pp_cost = ANTI_CORRUPTION_BUREAU["political_power_cost"] if bureau_active else 0
    pp_current = player_data["politics"].get("political_power", 100)
    embed.add_field(name="Политвласть", value=f"{pp_current:.1f} (-{pp_cost}/мес)", inline=True)
    
    real_level = STARTING_CORRUPTION.get(country_name, 3.0)
    embed.add_field(name="Реальный уровень", value=f"{real_level:.1f}%", inline=True)
    
    embed.set_footer(text="1% коррупции = 0.1% потерь бюджета в месяц")
    return embed


# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class CorruptionView(View):
    """Меню управления коррупцией"""
    
    def __init__(self, user_id: int, country_name: str, player_data: Dict, corruption_data: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.corruption_data = corruption_data
        
        bureau_button = Button(label="Управление бюро", style=discord.ButtonStyle.secondary)
        bureau_button.callback = self.bureau_button_callback
        self.add_item(bureau_button)
        
        history_button = Button(label="История", style=discord.ButtonStyle.secondary)
        history_button.callback = self.history_button_callback
        self.add_item(history_button)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_button_callback
        self.add_item(back_button)
    
    async def bureau_button_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        modal = BureauFundingModal(self.user_id, self.country_name, self.player_data, self.corruption_data)
        await interaction.response.send_modal(modal)
    
    async def history_button_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        if not self.corruption_data.get("history"):
            embed = discord.Embed(title="История изменений", description="История пуста", color=DARK_THEME_COLOR)
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        embed = discord.Embed(title=f"История коррупции в {self.country_name}", color=DARK_THEME_COLOR)
        for entry in self.corruption_data["history"][-8:]:
            date = datetime.fromisoformat(entry["date"]).strftime("%d.%m.%Y")
            change = entry.get("change", 0)
            change_symbol = "↑" if change > 0 else ("↓" if change < 0 else "→")
            embed.add_field(name=f"{date}", value=f"{change_symbol} {entry['level']:.2f}%\n{entry['reason']}", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def back_button_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        from bot import StateButtons
        view = StateButtons(self.user_id, self.country_name, self.player_data)
        state = self.player_data["state"]
        politics = self.player_data["politics"]
        economy = self.player_data["economy"]
        
        embed = discord.Embed(
            title=f"{state['statename']}",
            description=f"Лидер: {interaction.user.mention}",
            color=DARK_THEME_COLOR
        )
        embed.add_field(name="Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name="Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name="Стабильность", value=f"{state['stability']}%", inline=True)
        embed.add_field(name="Правительство", value=state['government_type'][:20], inline=True)
        embed.add_field(name="Правящая партия", value=politics['ruling_party'][:20], inline=True)
        embed.add_field(name="Популярность", value=f"{politics['popularity']}%", inline=True)
        embed.add_field(name="ВВП", value=format_billion(economy['gdp']), inline=True)
        embed.add_field(name="Бюджет", value=format_billion(get_budget(economy)), inline=True)
        embed.add_field(name="Налог", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        embed.add_field(name="Политвласть", value=f"{politics.get('political_power', 100):.1f}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=view)


class BureauFundingModal(Modal, title="Антикоррупционное бюро"):
    def __init__(self, user_id: int, country_name: str, player_data: Dict, corruption_data: Dict):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.corruption_data = corruption_data
        
        current_funding = corruption_data.get("bureau_funding", 0) / 1000000
        budget = get_budget(player_data["economy"])
        budget_millions = budget / 1000000
        pp_current = player_data["politics"].get("political_power", 100)
        
        self.funding_input = TextInput(
            label="Месячное финансирование (млн $)",
            placeholder=f"Текущее: {current_funding:.0f} | Бюджет: {budget_millions:.0f} | ПП: {pp_current:.1f}",
            default=str(int(current_funding)) if current_funding > 0 else "0",
            required=True
        )
        self.add_item(self.funding_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            funding_millions = int(self.funding_input.value)
            if funding_millions < 0:
                await interaction.response.send_message("Сумма должна быть положительной!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Введите корректное число!", ephemeral=True)
            return
        
        funding = funding_millions * 1000000
        
        if funding > 0:
            pp_current = self.player_data["politics"].get("political_power", 100)
            if pp_current < ANTI_CORRUPTION_BUREAU["political_power_cost"]:
                await interaction.response.send_message(f"Недостаточно политической власти! Нужно: {ANTI_CORRUPTION_BUREAU['political_power_cost']}", ephemeral=True)
                return
        
        success, message = set_bureau_funding(self.player_data, self.corruption_data, funding)
        
        if not success:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        update_country_corruption(self.country_name, self.corruption_data)
        
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country_name:
                data["politics"]["political_power"] = self.player_data["politics"]["political_power"]
                break
        save_states(states)
        
        embed = create_corruption_embed(self.country_name, self.player_data, self.corruption_data)
        view = CorruptionView(self.user_id, self.country_name, self.player_data, self.corruption_data)
        
        await interaction.response.send_message(f"✅ {message}", ephemeral=True)
        await interaction.edit_original_response(embed=embed, view=view)


# ==================== ФОНОВАЯ ЗАДАЧА ====================

async def corruption_update_loop(bot_instance):
    """Фоновая задача для ежемесячного обновления коррупции"""
    await bot_instance.wait_until_ready()
    
    last_update = None
    
    while not bot_instance.is_closed():
        try:
            now = datetime.now()
            
            if last_update is None or (now - last_update).days >= 30:
                print(f"👮 Запуск обновления коррупции: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                
                states = load_states()
                corruption_data = load_corruption_data()
                total_stolen = 0
                updates = []
                
                for state_id, player_data in states["players"].items():
                    if "assigned_to" not in player_data:
                        continue
                    
                    country_name = player_data["state"]["statename"]
                    
                    if country_name not in corruption_data["countries"]:
                        corruption_data["countries"][country_name] = {
                            "level": STARTING_CORRUPTION.get(country_name, 3.0),
                            "history": [],
                            "last_update": str(now),
                            "total_stolen": 0,
                            "bureau_funding": 0,
                            "bureau_active": False,
                            "last_payment": None,
                            "political_power_spent": 0
                        }
                    
                    country_corruption = corruption_data["countries"][country_name]
                    loss, new_level, change, pp_cost = apply_corruption(player_data, country_corruption)
                    country_corruption["level"] = new_level
                    
                    if "history" not in country_corruption:
                        country_corruption["history"] = []
                    
                    reason = "Ежемесячное обновление"
                    if country_corruption.get("bureau_active", False):
                        reason += f" (бюро: {format_billion(country_corruption.get('bureau_funding', 0))})"
                    
                    country_corruption["history"].append({
                        "date": str(now),
                        "level": new_level,
                        "change": change,
                        "loss": loss,
                        "reason": reason
                    })
                    
                    if len(country_corruption["history"]) > 20:
                        country_corruption["history"] = country_corruption["history"][-20:]
                    
                    total_stolen += loss
                    current_budget = get_budget(player_data["economy"])
                    loss_percent = (loss / current_budget * 100) if current_budget > 0 else 0
                    updates.append(f"{country_name}: {change:+.2f}% → {new_level:.2f}% (потеряно {format_billion(loss)} / {loss_percent:.2f}%)")
                    
                    if change > 0.3:
                        try:
                            user = await bot_instance.fetch_user(int(player_data["assigned_to"]))
                            if user:
                                embed = discord.Embed(
                                    title="Рост коррупции!",
                                    description=f"Уровень коррупции вырос на {change:.2f}% до {new_level:.2f}%",
                                    color=discord.Color.orange()
                                )
                                embed.add_field(name="Потери за месяц", value=f"{format_billion(loss)} ({loss_percent:.2f}% бюджета)", inline=True)
                                await user.send(embed=embed)
                        except:
                            pass
                    elif change < -0.2:
                        try:
                            user = await bot_instance.fetch_user(int(player_data["assigned_to"]))
                            if user:
                                embed = discord.Embed(
                                    title="Снижение коррупции!",
                                    description=f"Уровень коррупции снизился на {abs(change):.2f}% до {new_level:.2f}%",
                                    color=discord.Color.green()
                                )
                                await user.send(embed=embed)
                        except:
                            pass
                
                save_states(states)
                save_corruption_data(corruption_data)
                last_update = now
                
                print(f"✅ Коррупция обновлена для {len(updates)} стран")
                print(f"💰 Всего украдено: {format_billion(total_stolen)}")
                
                try:
                    if ADMIN_LOG_CHANNEL_ID:
                        channel = bot_instance.get_channel(ADMIN_LOG_CHANNEL_ID)
                        if channel and updates:
                            embed = discord.Embed(
                                title="Ежемесячный отчёт по коррупции",
                                description=f"Всего украдено: {format_billion(total_stolen)}",
                                color=DARK_THEME_COLOR
                            )
                            for update in updates[:5]:
                                embed.add_field(name="•", value=update, inline=False)
                            await channel.send(embed=embed)
                except Exception as e:
                    print(f"Ошибка отправки лога коррупции: {e}")
            
            await asyncio.sleep(86400)
            
        except Exception as e:
            print(f"❌ Ошибка в corruption_update_loop: {e}")
            await asyncio.sleep(86400)


# ==================== КОМАНДА ДЛЯ ПОКАЗА МЕНЮ ====================

async def show_corruption_menu(interaction_or_ctx, user_id: int):
    """Показать меню управления коррупцией"""
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
    
    corruption_data = get_country_corruption(country_name)
    embed = create_corruption_embed(country_name, player_data, corruption_data)
    view = CorruptionView(user_id, country_name, player_data, corruption_data)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view, ephemeral=True)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_corruption_menu',
    'corruption_update_loop',
    'apply_corruption',
    'get_country_corruption',
    'STARTING_CORRUPTION'
]

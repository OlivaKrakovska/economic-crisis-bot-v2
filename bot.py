# bot.py - ОСНОВНОЙ ФАЙЛ БОТА
# Версия с поддержкой настройки расходов министерств

import discord
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput, Select
import json
import random
import asyncio
from datetime import datetime, timedelta
import math
import os
from typing import Optional, Dict, Any
from research import research_update_loop

from population import population_update_loop, show_population_menu

# Импорт конфигурации
from config import BOT_TOKEN, ADMIN_LOG_CHANNEL_ID, TRADE_LOG_CHANNEL_ID, COMMAND_PREFIX

# Импорт вспомогательных функций из utils.py
from utils import format_billion, format_number, format_army_number, get_user_id, get_user_name, send_response, load_states, save_states, load_trades, save_trades, load_alliances, save_alliances, load_transfers, save_transfers, DARK_THEME_COLOR, format_time, get_budget, set_budget, add_to_budget, subtract_from_budget, has_sufficient_budget, format_budget_display, format_gdp_display, get_gdp, get_debt, get_military_budget, get_currency_code

# Импорт модуля ВПК
from corp_store import show_corporations_menu, show_my_orders, collect_completed_orders, production_check_loop
from corp_store import EQUIPMENT_NAMES, PRODUCTION_SPEED, format_time

# Импорт модуля инфраструктуры (обновлённый)
from infra_build import (
    show_infrastructure_menu, show_construction_projects,
    complete_construction_projects, construction_check_loop,
    get_army_pvo_count, consume_army_pvo, add_army_pvo,
    INFRASTRUCTURE_COSTS, get_region_pvo_text, show_move_pvo_menu,
    ASSET_FIELDS, load_infrastructure
)

# Импорт модуля сброса
from reset_to_original import ResetCommands

# Импорт модуля политической власти (обновлённый)
from political_power import (
    show_political_power_menu, political_power_update_loop,
    get_political_power, spend_political_power, add_political_power, set_political_power,
    get_influence, add_influence, get_player_state as get_pp_player_state,
    get_popularity_tier, MAX_INFLUENCE
)

# Импорт ресурсной системы
from resource_system import (
    RESOURCE_TYPES, RESOURCE_PRICES, RESOURCE_TYPES_FALLBACK,
    get_resource_emoji, get_resource_name, format_resource_amount,
    calculate_resource_value, format_resource_value, create_resource_embed,
    create_trade_embed, convert_old_resources
)

# Импорт модуля гражданской продукции
from civil_store import (
    show_civil_corporations_menu, show_civil_orders, collect_civil_orders,
    civil_production_check_loop, show_civil_goods, CIVIL_PRODUCT_NAMES
)

# Импорт модуля производственных эффектов
from production_effects import (
    apply_infrastructure_bonuses, get_power_status,
    check_fuel_availability, consume_fuel, get_production_time_with_bonus,
    get_production_bonus_info
)

# Импорт модуля добычи ресурсов
from resource_extraction import (
    resource_extraction_loop,
    show_extraction_info,
    force_extraction,
    EXTRACTION_INTERVAL_HOURS
)

# Импорт налоговой системы
from tax_system import show_tax_menu, TaxSystem, migrate_taxes

# Импорт системы таможенных пошлин
from trade_tariffs import show_tariffs_menu, TariffSystem, calculate_trade_with_tariffs, filter_corporations_by_tariffs, TariffManagementView

# Импорт модуля ударов
from strikes import show_strike_menu, STRIKE_WEAPONS, TARGET_TYPES

# Импорт модуля конфликтов
from conflicts import show_conflicts_menu, get_countries_at_war_with, are_countries_at_war

# Импорт модуля центрального банка
from central_bank import show_central_bank_menu

from corporation_production import corporation_production_loop

from consumption_forecast import show_consumption_forecast

from mobilization import show_mobilization_menu, mobilization_completion_loop

from game_time import game_time_update_loop, get_game_date_formatted

# Импорт модуля спутников
from satellites import show_satellite_menu, satellite_maintenance_loop, get_satellite_bonuses

from military_doctrines import show_doctrines_menu, doctrines_completion_loop

from corruption import show_corruption_menu, corruption_update_loop

from espionage import show_espionage_menu

from energy_system import show_energy_menu, energy_update_loop

from transfer_region import TransferRegionCog

from pipelines import show_pipeline_menu, approve_pipeline_project, reject_pipeline_project

from maritime_trade import (
    show_maritime_menu,
    maritime_trade_loop,
    admin_create_ship,
    admin_force_trade,
    admin_force_init_fleet,
    update_ships_on_region_transfer,
    update_priorities_on_region_transfer,
    ExportPriorityCountrySelectView,
    get_ships_by_sea_region,
    get_ships_by_country,
    get_sea_zone_from_region
)

# Импорт модуля военно-морского флота
from navy import (
    show_navy_menu, 
    navy_update_loop, 
    initialize_fleets,
    add_blockade,
    remove_blockade,
    get_active_blockades,
    is_ship_blocked,
    get_ships_in_zone_with_blockade
)

# ==================== СЕРВЕРНЫЕ ЭМОДЗИ ====================

EMOJIS = {
    "government": "<:government:1487167580350451804>",
    "police": "<:police:1487015253391839373>",
    "education": "<:education:1487167901973614662>",
    "social": "<:social:1487167248908156988>",
    "medicina": "<:medicina:1487167349223067689>",
    "army": "<:army:1487330495082528829>",
    "money": "<:money:1429345094695129088>",
    "vvp": "<:vvp:1487360602367070400>",
    "job_spec": "<:Job_spec:1267712580999184486>",
    "pp": "<:pp:1487015341883130027>",
    "crisis": "<:crisis:1487167453443391509>",
    "partia": "<:partia:1487365868676448327>",
    "manpower": "<:Manpower:1256977159356940311>",
    "zakon": "<:zakon:1487365783385411626>",
    "clock": "<:clock:1256638575611678730>"
}

# Настройки бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# ==================== ФУНКЦИИ МИГРАЦИИ ====================
def migrate_player_resources(player_data):
    """Мигрирует ресурсы игрока в новый формат если нужно"""
    if "resources" in player_data:
        resources = player_data["resources"]
        if any(isinstance(v, dict) for v in resources.values()):
            player_data["resources"] = convert_old_resources(resources)
    else:
        player_data["resources"] = {}
    
    if "civil_goods" not in player_data:
        player_data["civil_goods"] = {}
    
    player_data = migrate_taxes(player_data)
    
    return player_data

# ==================== ЭКСПОРТ ФУНКЦИЙ ====================
__all__ = ['load_states', 'save_states', 'load_trades', 'save_trades', 
           'load_alliances', 'save_alliances', 'load_transfers', 'save_transfers',
           'format_billion', 'format_number', 'TaxSystem']

# ==================== ЭКОНОМИЧЕСКИЕ РАСЧЕТЫ ====================
class EconomyCalculator:
    @staticmethod
    def calculate_annual_budget(state_data: dict) -> dict:
        """Расчет годового бюджета с многокомпонентной налоговой системой"""
        economy = state_data.get("economy", {})
        state = state_data.get("state", {})
        expenses = state_data.get("expenses", {})
        
        tax_system = TaxSystem(state_data)
        tax_revenue_data = tax_system.calculate_total_tax_revenue()
        tax_revenue = tax_revenue_data["total"]
        
        resources = state_data.get("resources", {})
        
        resource_revenue = 0
        for resource, amount in resources.items():
            if resource in RESOURCE_PRICES:
                resource_revenue += (amount * 0.001) * RESOURCE_PRICES[resource] * 1000
        
        import_tariff_revenue = state_data.get("tariff_revenue_usd", 0)
        export_tariff_revenue = state_data.get("export_tariff_revenue_usd", 0)
        total_tariff_revenue = import_tariff_revenue + export_tariff_revenue
        
        military_budget = economy.get("military_budget_local", 0)
        defense_spending = military_budget
        healthcare_spending = expenses.get("healthcare", 0)
        police_spending = expenses.get("police", 0)
        social_spending = expenses.get("social_security", 0)
        education_spending = expenses.get("education", 0)
        
        army_size = state.get("army_size", 0)
        army_upkeep = army_size * 10000
        
        debt = economy.get("debt_local", 0)
        debt_service = debt * 0.02
        
        total_expenses = (defense_spending + healthcare_spending + police_spending + 
                         social_spending + education_spending + army_upkeep + debt_service)
        
        total_revenue = tax_revenue + resource_revenue + total_tariff_revenue
        
        gdp = economy.get("gdp_local", 0)
        deficit = total_revenue - total_expenses
        
        max_deficit = gdp * 0.03
        if abs(deficit) > max_deficit:
            deficit = max_deficit if deficit > 0 else -max_deficit
        
        old_budget = get_budget(economy)
        total_income = total_revenue
        total_outcome = total_expenses
        balance = total_income - total_outcome
        new_budget = old_budget + balance
        
        new_debt = debt
        if new_budget < 0:
            new_debt = debt + abs(new_budget)
            new_budget = 0
        elif deficit > 0 and debt > 0:
            debt_payment = min(debt, deficit * 0.1)
            new_debt = debt - debt_payment
            new_budget = old_budget + (deficit - debt_payment)
        
        return {
            "old_budget": old_budget,
            "new_budget": new_budget,
            "old_debt": debt,
            "new_debt": new_debt,
            "revenue": {
                "taxes": tax_revenue,
                "tax_breakdown": {
                    "income": tax_revenue_data["income_tax"],
                    "corporate": tax_revenue_data["corporate_tax"],
                    "vat": tax_revenue_data["vat"],
                    "social_security": tax_revenue_data["social_security"],
                    "property": tax_revenue_data["property_tax"]
                },
                "resources": resource_revenue,
                "import_tariffs": import_tariff_revenue,
                "export_tariffs": export_tariff_revenue,
                "total_tariffs": total_tariff_revenue,
                "total": total_revenue,
                "percent_of_gdp": (total_revenue / gdp * 100) if gdp > 0 else 0
            },
            "expenses": {
                "defense": defense_spending,
                "healthcare": healthcare_spending,
                "police": police_spending,
                "social_security": social_spending,
                "education": education_spending,
                "army_upkeep": army_upkeep,
                "debt_service": debt_service,
                "total": total_expenses,
                "percent_of_gdp": (total_expenses / gdp * 100) if gdp > 0 else 0
            },
            "deficit": deficit,
            "deficit_percent": (deficit / gdp * 100) if gdp > 0 else 0
        }

    @staticmethod
    def calculate_gdp_growth(state_data: dict) -> float:
        """Расчет роста ВВП"""
        stability = state_data.get("state", {}).get("stability", 50)
        happiness = state_data.get("state", {}).get("happiness", 50)
        gov_efficiency = state_data.get("government_efficiency", 50)
        expenses = state_data.get("expenses", {})
        
        base_growth = 2.0
        stability_modifier = (stability - 50) / 100
        happiness_modifier = (happiness - 50) / 100
        education_bonus = min(0.5, expenses.get("education", 0) / 1e12)
        healthcare_bonus = min(0.3, expenses.get("healthcare", 0) / 2e12)
        
        growth = (base_growth + stability_modifier + happiness_modifier + 
                 education_bonus + healthcare_bonus)
        
        return max(0.5, min(5.0, growth))

    @staticmethod
    def calculate_population_growth(state_data: dict) -> int:
        """Расчет прироста населения"""
        state = state_data.get("state", {})
        demographics = state.get("demographics", {})
        expenses = state_data.get("expenses", {})
        
        population = state.get("population", 0)
        birth_rate = demographics.get("birth_rate", 10) / 1000
        death_rate = demographics.get("death_rate", 10) / 1000
        
        healthcare_bonus = min(0.2, expenses.get("healthcare", 0) / 5e11)
        adjusted_death_rate = max(0.1, death_rate - (healthcare_bonus / 1000))
        
        natural_increase = population * (birth_rate - adjusted_death_rate)
        
        stability = state.get("stability", 50)
        happiness = state.get("happiness", 50)
        migration_modifier = ((stability + happiness) / 2 - 50) / 5000
        migration = population * migration_modifier
        
        return int(natural_increase + migration)

    @staticmethod
    def calculate_army_experience(state_data: dict) -> float:
        """Расчет опытности армии"""
        economy = state_data.get("economy", {})
        state = state_data.get("state", {})
        
        military_budget = economy.get("military_budget_local", 0)
        gdp = economy.get("gdp_local", 1)
        stability = state.get("stability", 50)
        
        base_exp = 50
        budget_ratio = military_budget / gdp if gdp > 0 else 0
        budget_bonus = min(30, budget_ratio * 1000)
        stability_bonus = (stability - 50) / 2
        
        experience = base_exp + budget_bonus + stability_bonus
        return max(20, min(100, experience))


# ==================== КЛАСС НАСТРОЙКИ РАСХОДОВ ====================

class ExpensesView(View):
    """View для навигации по расходам"""
    def __init__(self, user_id, player_data):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
    
    @discord.ui.button(label="Настроить расходы", style=discord.ButtonStyle.primary)
    async def configure_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_expenses_configuration(interaction, self.user_id, self.player_data)
    
    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        state = self.player_data["state"]
        politics = self.player_data["politics"]
        economy = self.player_data["economy"]
        
        # Безопасное получение бюджета
        budget = 0
        currency_code = "USD"
        if "local_currency" in economy:
            budget = economy["local_currency"]["amount"]
            currency_code = economy["local_currency"]["code"]
        elif "budget_usd" in economy:
            budget = economy["budget_usd"]
        else:
            budget = economy.get("budget", 0)
        
        gdp_local = economy.get("gdp_local", 0)
        
        embed = discord.Embed(
            title=f"{state['statename']}",
            description=f"Лидер: {interaction.user.mention}",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name=f"{EMOJIS['job_spec']} Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"{state['stability']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Правительство", value=state['government_type'], inline=True)
        embed.add_field(name=f"{EMOJIS['partia']} Правящая партия", value=politics['ruling_party'], inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} Популярность", value=f"{politics['popularity']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} ВВП", value=f"{format_billion(gdp_local)} {currency_code}", inline=True)
        embed.add_field(name=f"{EMOJIS['money']} Бюджет", value=f"{format_billion(budget)} {currency_code}", inline=True)
        
        view = StateButtons(self.user_id, state['statename'], self.player_data)
        await interaction.response.edit_message(embed=embed, view=view)


class ExpensesConfigView(View):
    """View для выбора министерства для настройки"""
    def __init__(self, user_id, player_data):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        
        self.defense_btn = Button(label="Оборона", style=discord.ButtonStyle.secondary)
        self.defense_btn.callback = lambda i: self.show_ministry_modal(i, "defense")
        self.add_item(self.defense_btn)
        
        self.health_btn = Button(label="Здравоохранение", style=discord.ButtonStyle.secondary)
        self.health_btn.callback = lambda i: self.show_ministry_modal(i, "healthcare")
        self.add_item(self.health_btn)
        
        self.police_btn = Button(label="Полиция", style=discord.ButtonStyle.secondary)
        self.police_btn.callback = lambda i: self.show_ministry_modal(i, "police")
        self.add_item(self.police_btn)
        
        self.social_btn = Button(label="Соцобеспечение", style=discord.ButtonStyle.secondary)
        self.social_btn.callback = lambda i: self.show_ministry_modal(i, "social")
        self.add_item(self.social_btn)
        
        self.education_btn = Button(label="Образование", style=discord.ButtonStyle.secondary)
        self.education_btn.callback = lambda i: self.show_ministry_modal(i, "education")
        self.add_item(self.education_btn)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_expenses_configuration(interaction, self.user_id, self.player_data)
    
    async def show_ministry_modal(self, interaction: discord.Interaction, ministry: str):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        expenses = self.player_data.get("expenses", {})
        economy = self.player_data["economy"]
        
        # Безопасное получение бюджета и валюты
        if "local_currency" in economy:
            budget = economy["local_currency"]["amount"]
            currency_code = economy["local_currency"]["code"]
        elif "budget_usd" in economy:
            budget = economy["budget_usd"]
            currency_code = "USD"
        else:
            budget = economy.get("budget", 0)
            currency_code = "USD"
        
        # ИСПРАВЛЕНО: правильное получение военного бюджета
        current_values = {
            "defense": economy.get("military_budget_local", economy.get("military_budget", 0)),
            "healthcare": expenses.get("healthcare", 0),
            "police": expenses.get("police", 0),
            "social": expenses.get("social_security", 0),
            "education": expenses.get("education", 0)
        }
        
        total = sum(current_values.values())
        
        ministry_names = {
            "defense": "Оборона",
            "healthcare": "Здравоохранение",
            "police": "Полиция",
            "social": "Соцобеспечение",
            "education": "Образование"
        }
        
        emojis = {
            "defense": EMOJIS["army"],
            "healthcare": EMOJIS["medicina"],
            "police": EMOJIS["police"],
            "social": EMOJIS["social"],
            "education": EMOJIS["education"]
        }
        
        modal = ExpenseModal(
            self.user_id, self.player_data, ministry, ministry_names[ministry], 
            current_values[ministry], budget, currency_code,
            current_values[ministry]/total*100 if total > 0 else 0, 
            emojis[ministry]
        )
        await interaction.response.send_modal(modal)


class ExpenseModal(Modal, title="Настройка расходов"):
    def __init__(self, user_id, player_data, ministry_key, ministry_name, current_value, budget, currency_code, current_percent, emoji):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.ministry_key = ministry_key
        self.ministry_name = ministry_name
        self.current_value = current_value
        self.budget = budget
        self.currency_code = currency_code
        self.emoji = emoji
        
        self.amount = TextInput(
            label=f"{ministry_name} (сейчас: {format_billion(current_value)} {currency_code})",
            placeholder=f"Введите сумму в {currency_code} (например: 5000000000 или 5B)",
            min_length=1,
            max_length=15,
            required=True
        )
        self.add_item(self.amount)
    
    def format_short(self, value):
        if value >= 1_000_000_000_000:
            return f"{value / 1_000_000_000_000:.1f} трлн"
        elif value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.1f} млрд"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.1f} млн"
        else:
            return f"{value:,.0f}"
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        amount_str = self.amount.value.strip().upper()
        try:
            if amount_str.endswith('T'):
                new_amount = int(float(amount_str[:-1]) * 1_000_000_000_000)
            elif amount_str.endswith('B'):
                new_amount = int(float(amount_str[:-1]) * 1_000_000_000)
            elif amount_str.endswith('M'):
                new_amount = int(float(amount_str[:-1]) * 1_000_000)
            elif amount_str.endswith('K'):
                new_amount = int(float(amount_str[:-1]) * 1_000)
            else:
                new_amount = int(amount_str)
        except ValueError:
            await interaction.response.send_message("Введите корректное число!", ephemeral=True)
            return
        
        if new_amount < 0:
            await interaction.response.send_message("Сумма не может быть отрицательной!", ephemeral=True)
            return
        
        if new_amount > self.budget:
            await interaction.response.send_message(f"Сумма не может превышать бюджет ({self.format_short(self.budget)} {self.currency_code})!", ephemeral=True)
            return
        
        expenses = self.player_data.get("expenses", {})
        economy = self.player_data["economy"]
        
        # ИСПРАВЛЕНО: сохраняем военный бюджет в правильное поле
        if self.ministry_key == "defense":
            self.player_data["economy"]["military_budget_local"] = new_amount
        elif self.ministry_key == "healthcare":
            self.player_data["expenses"]["healthcare"] = new_amount
        elif self.ministry_key == "police":
            self.player_data["expenses"]["police"] = new_amount
        elif self.ministry_key == "social":
            self.player_data["expenses"]["social_security"] = new_amount
        elif self.ministry_key == "education":
            self.player_data["expenses"]["education"] = new_amount
        
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                data.update(self.player_data)
                break
        save_states(states)
        
        # ИСПРАВЛЕНО: правильный расчёт нового тотала
        new_total = sum([
            self.player_data["economy"].get("military_budget_local", self.player_data["economy"].get("military_budget", 0)),
            self.player_data["expenses"].get("healthcare", 0),
            self.player_data["expenses"].get("police", 0),
            self.player_data["expenses"].get("social_security", 0),
            self.player_data["expenses"].get("education", 0)
        ])
        
        embed = discord.Embed(
            title=f"{CORP_EMOJIS['money']} Расходы обновлены",
            description=f"{self.emoji} Бюджет **{self.ministry_name}** изменён с {format_billion(self.current_value)} на {format_billion(new_amount)} {self.currency_code}",
            color=DARK_THEME_COLOR
        )
        embed.add_field(name=f"{EMOJIS['government']} Всего расходов", value=f"{format_billion(new_total)} {self.currency_code}", inline=True)
        embed.add_field(name=f"{EMOJIS['money']} Остаток бюджета", value=f"{format_billion(self.budget - new_total)} {self.currency_code}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)


async def show_expenses_configuration(interaction, user_id, player_data):
    expenses = player_data.get("expenses", {})
    economy = player_data["economy"]
    
    # Безопасное получение бюджета и валюты
    if "local_currency" in economy:
        budget = economy["local_currency"]["amount"]
        currency_code = economy["local_currency"]["code"]
    elif "budget_usd" in economy:
        budget = economy["budget_usd"]
        currency_code = "USD"
    else:
        budget = economy.get("budget", 0)
        currency_code = "USD"
    
    # ИСПРАВЛЕНО: правильное получение военного бюджета
    current = {
        "defense": economy.get("military_budget_local", economy.get("military_budget", 0)),
        "healthcare": expenses.get("healthcare", 0),
        "police": expenses.get("police", 0),
        "social": expenses.get("social_security", 0),
        "education": expenses.get("education", 0)
    }
    
    total = sum(current.values())
    
    embed = discord.Embed(
        title=f"{EMOJIS['government']} Настройка распределения бюджета",
        description=f"Общий бюджет: {format_billion(budget)} {currency_code}\n"
                    f"Текущие расходы: {format_billion(total)} {currency_code} "
                    f"({total/budget*100:.1f}% бюджета)" if budget > 0 else f"Общий бюджет: {format_billion(budget)} {currency_code}\nТекущие расходы: {format_billion(total)} {currency_code}",
        color=DARK_THEME_COLOR
    )
    
    embed.add_field(
        name=f"{EMOJIS['army']} Оборона",
        value=f"Сейчас: {format_billion(current['defense'])} {currency_code}\n"
              f"({current['defense']/total*100:.1f}% расходов)" if total > 0 else f"Сейчас: {format_billion(current['defense'])} {currency_code}",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJIS['medicina']} Здравоохранение",
        value=f"Сейчас: {format_billion(current['healthcare'])} {currency_code}\n"
              f"({current['healthcare']/total*100:.1f}% расходов)" if total > 0 else f"Сейчас: {format_billion(current['healthcare'])} {currency_code}",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJIS['police']} Полиция",
        value=f"Сейчас: {format_billion(current['police'])} {currency_code}\n"
              f"({current['police']/total*100:.1f}% расходов)" if total > 0 else f"Сейчас: {format_billion(current['police'])} {currency_code}",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJIS['social']} Соцобеспечение",
        value=f"Сейчас: {format_billion(current['social'])} {currency_code}\n"
              f"({current['social']/total*100:.1f}% расходов)" if total > 0 else f"Сейчас: {format_billion(current['social'])} {currency_code}",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJIS['education']} Образование",
        value=f"Сейчас: {format_billion(current['education'])} {currency_code}\n"
              f"({current['education']/total*100:.1f}% расходов)" if total > 0 else f"Сейчас: {format_billion(current['education'])} {currency_code}",
        inline=True
    )
    
    embed.set_footer(text="Выберите министерство для изменения бюджета")
    
    view = ExpensesConfigView(user_id, player_data)
    await interaction.response.edit_message(embed=embed, view=view)


# ==================== КНОПКИ ДЛЯ ГОСУДАРСТВА ====================

class StateButtons(View):
    def __init__(self, user_id, state_name, player_data):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.state_name = state_name
        self.player_data = player_data

    def get_currency_code(self):
        """Возвращает код локальной валюты или USD"""
        economy = self.player_data["economy"]
        if "local_currency" in economy:
            return economy["local_currency"]["code"]
        return "USD"

    def get_budget(self):
        """Безопасно получает бюджет в локальной валюте"""
        economy = self.player_data["economy"]
        if "local_currency" in economy:
            return economy["local_currency"]["amount"]
        elif "budget_usd" in economy:
            return economy["budget_usd"]
        else:
            return economy.get("budget", 0)

    def get_gdp_local(self):
        """Возвращает ВВП в локальной валюте"""
        economy = self.player_data["economy"]
        return economy.get("gdp_local", 0)

    def get_debt_local(self):
        """Возвращает госдолг в локальной валюте"""
        economy = self.player_data["economy"]
        return economy.get("debt_local", 0)

    def get_military_budget_local(self):
        """Возвращает военный бюджет в локальной валюте"""
        economy = self.player_data["economy"]
        return economy.get("military_budget_local", 0)

    def get_wage_local(self):
        """Возвращает среднюю зарплату в локальной валюте"""
        economy = self.player_data["economy"]
        return economy.get("wage_local", 0)

    def get_player_alliance(self, user_id):
        alliances = load_alliances()
        for alliance in alliances["alliances"]:
            if str(user_id) in alliance.get("members", []):
                return alliance
        return None

    @discord.ui.button(label="Бюджет", style=discord.ButtonStyle.secondary)
    async def budget_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return

        economy = self.player_data["economy"]
        state = self.player_data["state"]
        currency_code = self.get_currency_code()
        budget = self.get_budget()
        gdp_local = self.get_gdp_local()
        debt_local = self.get_debt_local()
        military_budget = self.get_military_budget_local()
        wage_local = self.get_wage_local()
        usd_reserves = economy.get("foreign_reserves", {}).get("USD", 0)

        embed = discord.Embed(
            title=f"Бюджет {state['statename']}",
            color=0x2b2d31
        )

        embed.add_field(name=f"{EMOJIS['money']} Госбюджет", value=f"{format_billion(budget)} {currency_code}", inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} ВВП", value=f"{format_billion(gdp_local)} {currency_code}", inline=True)
        embed.add_field(name="Госдолг", value=f"{format_billion(debt_local)} {currency_code}", inline=True)

        if "taxes" in economy:
            tax_system = TaxSystem(self.player_data)
            revenue = tax_system.calculate_total_tax_revenue()
            embed.add_field(name="Налоговые поступления", value=f"{format_billion(revenue['total'])} {currency_code}", inline=True)
            embed.add_field(name="Эфф. ставка", value=f"{revenue['effective_rate']:.1f}% ВВП", inline=True)
        else:
            embed.add_field(name="Налоговая ставка", value=f"{economy.get('tax_rate', 20)}%", inline=True)

        if self.player_data.get("tariff_revenue_usd", 0) > 0:
            embed.add_field(name="Таможенные сборы", value=f"${format_billion(self.player_data['tariff_revenue_usd'])}", inline=True)

        embed.add_field(name="Инфляция", value=f"{economy.get('inflation', 0)}%", inline=True)
        embed.add_field(name="Средняя зарплата", value=f"{format_billion(wage_local)} {currency_code}", inline=True)
        embed.add_field(name=f"{EMOJIS['army']} Военный бюджет", value=f"{format_billion(military_budget)} {currency_code}", inline=True)
        embed.add_field(name="Стоимость жизни", value=f"{economy.get('cost_of_living', 0)}", inline=True)
        embed.add_field(name="USD-резервы", value=f"${format_billion(usd_reserves)}", inline=True)

        if gdp_local > 0:
            debt_to_gdp = (debt_local / gdp_local) * 100
            embed.add_field(name="Долг/ВВП", value=f"{debt_to_gdp:.1f}%", inline=True)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Расходы", style=discord.ButtonStyle.secondary)
    async def expenses_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return

        economy = self.player_data["economy"]
        state_name = self.player_data["state"]["statename"]
        currency_code = self.get_currency_code()
        budget = self.get_budget()

        expenses = self.player_data.get("expenses", {})
        defense_spending = self.get_military_budget_local()
        healthcare_spending = expenses.get("healthcare", 0)
        police_spending = expenses.get("police", 0)
        social_spending = expenses.get("social_security", 0)
        education_spending = expenses.get("education", 0)

        total_expenses = defense_spending + healthcare_spending + police_spending + social_spending + education_spending

        embed = discord.Embed(
            title=f"{EMOJIS['government']} Расходы государства: {state_name}",
            description=f"Общий бюджет: {format_billion(budget)} {currency_code}\n"
                        f"Всего расходов: {format_billion(total_expenses)} {currency_code} "
                        f"({total_expenses/budget*100:.1f}% бюджета)" if budget > 0 else f"Общий бюджет: {format_billion(budget)} {currency_code}\nВсего расходов: {format_billion(total_expenses)} {currency_code}",
            color=DARK_THEME_COLOR
        )

        embed.add_field(
            name=f"{EMOJIS['army']} Оборона",
            value=f"{format_billion(defense_spending)} {currency_code}\n"
                  f"{defense_spending/total_expenses*100:.1f}% расходов\n"
                  f"{defense_spending/budget*100:.1f}% бюджета" if budget > 0 and total_expenses > 0 else f"{format_billion(defense_spending)} {currency_code}",
            inline=True
        )
        embed.add_field(
            name=f"{EMOJIS['medicina']} Здравоохранение",
            value=f"{format_billion(healthcare_spending)} {currency_code}\n"
                  f"{healthcare_spending/total_expenses*100:.1f}% расходов\n"
                  f"{healthcare_spending/budget*100:.1f}% бюджета" if budget > 0 and total_expenses > 0 else f"{format_billion(healthcare_spending)} {currency_code}",
            inline=True
        )
        embed.add_field(
            name=f"{EMOJIS['police']} Полиция",
            value=f"{format_billion(police_spending)} {currency_code}\n"
                  f"{police_spending/total_expenses*100:.1f}% расходов\n"
                  f"{police_spending/budget*100:.1f}% бюджета" if budget > 0 and total_expenses > 0 else f"{format_billion(police_spending)} {currency_code}",
            inline=True
        )
        embed.add_field(
            name=f"{EMOJIS['social']} Соцобеспечение",
            value=f"{format_billion(social_spending)} {currency_code}\n"
                  f"{social_spending/total_expenses*100:.1f}% расходов\n"
                  f"{social_spending/budget*100:.1f}% бюджета" if budget > 0 and total_expenses > 0 else f"{format_billion(social_spending)} {currency_code}",
            inline=True
        )
        embed.add_field(
            name=f"{EMOJIS['education']} Образование",
            value=f"{format_billion(education_spending)} {currency_code}\n"
                  f"{education_spending/total_expenses*100:.1f}% расходов\n"
                  f"{education_spending/budget*100:.1f}% бюджета" if budget > 0 and total_expenses > 0 else f"{format_billion(education_spending)} {currency_code}",
            inline=True
        )

        embed.set_footer(text="Нажмите кнопку 'Настроить' для изменения распределения бюджета")

        view = ExpensesView(self.user_id, self.player_data)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Активы", style=discord.ButtonStyle.secondary)
    async def assets_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_assets_menu(interaction, self.user_id, self.player_data)

    @discord.ui.button(label="Армия", style=discord.ButtonStyle.secondary)
    async def army_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return

        army = self.player_data.get("army", {})
        state = self.player_data["state"]
        state_name = state["statename"]
        army_exp = state.get("army_experience", 50)

        embed = discord.Embed(
            title=f"{EMOJIS['army']} Армия: {state_name}",
            description=f"Личный состав: {format_army_number(state['army_size'])} чел.\nСредняя опытность: {army_exp:.0f}%",
            color=0x2b2d31
        )

        army_ground = army.get("ground", {})
        pvo_in_arsenal = []
        pvo_types = ["short_range_air_defense", "long_range_air_defense", "zdprk", "zas", "radar_systems"]

        for pvo_type in pvo_types:
            count = army_ground.get(pvo_type, 0)
            if count > 0:
                pvo_name = INFRASTRUCTURE_COSTS.get(pvo_type, {}).get("name", pvo_type)
                pvo_in_arsenal.append(f"{pvo_name}: {format_number(count)}")

        if pvo_in_arsenal:
            embed.add_field(name="ПВО в арсенале (для установки)", value="\n".join(pvo_in_arsenal), inline=False)

        if "ground" in army and army["ground"]:
            ground = army["ground"]
            ground_text = ""
            ground_names = {
                "tanks": "Танки", "btr": "БТР", "bmp": "БМП", "armored_vehicles": "Бронеавтомобили",
                "trucks": "Грузовики", "cars": "Автомобили", "ew_vehicles": "Машины РЭБ",
                "engineering_equipment": "Инженерная техника", "radar_systems": "РЛС",
                "self_propelled_artillery": "САУ", "towed_artillery": "Буксируемая артиллерия",
                "mlrs": "РСЗО", "atgm_complexes": "ПТРК", "otr_complexes": "ОТРК",
                "zas": "Зенитная артиллерия", "zdprk": "ЗПРК",
                "short_range_air_defense": "ПВО ближнего действия", "long_range_air_defense": "ПВО дальнего действия"
            }
            for key, name in ground_names.items():
                if key in ground and ground[key] > 0:
                    ground_text += f"{name}: {format_number(ground[key])}\n"
            if not ground_text:
                ground_text = "Нет техники"
            embed.add_field(name="Сухопутные войска", value=ground_text, inline=False)

        if "equipment" in army and army["equipment"]:
            equipment = army["equipment"]
            equipment_text = ""
            equipment_names = {
                "small_arms": "Стрелковое оружие", "grenade_launchers": "Гранатометы",
                "atgms": "Переносные ПТРК", "manpads": "ПЗРК",
                "medical_equipment": "Медицинское оборудование",
                "engineering_equipment_units": "Инженерное снаряжение",
                "fpv_drones": "FPV-дроны"
            }
            for key, name in equipment_names.items():
                if key in equipment and equipment[key] > 0:
                    equipment_text += f"{name}: {format_number(equipment[key])}\n"
            if not equipment_text:
                equipment_text = "Нет снаряжения"
            embed.add_field(name="Снаряжение", value=equipment_text, inline=False)

        if "air" in army and army["air"]:
            air = army["air"]
            air_text = ""
            air_names = {
                "fighters": "Истребители", "attack_aircraft": "Штурмовики", "bombers": "Бомбардировщики",
                "transport_aircraft": "Транспортные самолеты", "attack_helicopters": "Ударные вертолеты",
                "transport_helicopters": "Транспортные вертолеты", "recon_uav": "Разведывательные БПЛА",
                "attack_uav": "Ударные БПЛА", "kamikaze_drones": "Дроны-камикадзе"
            }
            for key, name in air_names.items():
                if key in air and air[key] > 0:
                    air_text += f"{name}: {format_number(air[key])}\n"
            if not air_text:
                air_text = "Нет авиации"
            embed.add_field(name="Военно-воздушные силы", value=air_text, inline=False)

        if "navy" in army and army["navy"]:
            navy = army["navy"]
            navy_text = ""
            navy_names = {
                "boats": "Катера", "corvettes": "Корветы", "destroyers": "Эсминцы",
                "cruisers": "Крейсера", "aircraft_carriers": "Авианосцы", "submarines": "Подводные лодки", "usv_attack": "Надводные дроны"
            }
            for key, name in navy_names.items():
                if key in navy and navy[key] > 0:
                    navy_text += f"{name}: {format_number(navy[key])}\n"
            if not navy_text:
                navy_text = "Нет флота"
            embed.add_field(name="Военно-морской флот", value=navy_text, inline=False)

        if "missiles" in army and army["missiles"]:
            missiles = army["missiles"]
            missiles_text = ""
            missiles_names = {
                "strategic_nuclear": "Стратегическое ядерное оружие", "tactical_nuclear": "Тактическое ядерное оружие",
                "cruise_missiles": "Крылатые ракеты", "hypersonic_missiles": "Гиперзвуковые ракеты",
                "ballistic_missiles": "Баллистические ракеты"
            }
            for key, name in missiles_names.items():
                if key in missiles and missiles[key] > 0:
                    missiles_text += f"{name}: {format_number(missiles[key])}\n"
            if not missiles_text:
                missiles_text = "Нет ракетного вооружения"
            embed.add_field(name="Ракетное вооружение", value=missiles_text, inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Мобилизация", style=discord.ButtonStyle.secondary)
    async def mobilization_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_mobilization_menu(interaction, self.user_id)

    @discord.ui.button(label="Инфраструктура", style=discord.ButtonStyle.secondary)
    async def infrastructure_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_infrastructure_menu(interaction)

    @discord.ui.button(label="Полит. власть", style=discord.ButtonStyle.secondary)
    async def political_power_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_political_power_menu(interaction, self.user_id)

    @discord.ui.button(label="Налоги", style=discord.ButtonStyle.secondary)
    async def taxes_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_tax_menu(interaction, self.user_id)

    @discord.ui.button(label="Таможня", style=discord.ButtonStyle.secondary)
    async def tariffs_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_tariffs_menu(interaction, self.user_id)

    @discord.ui.button(label="Население", style=discord.ButtonStyle.secondary)
    async def population_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_population_menu(interaction, self.user_id)

    @discord.ui.button(label="Удары", style=discord.ButtonStyle.danger)
    async def strikes_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_strike_menu(interaction, self.user_id)

    @discord.ui.button(label="Флот", style=discord.ButtonStyle.primary)
    async def navy_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_navy_menu(interaction, self.user_id)

    @discord.ui.button(label="Разведка", style=discord.ButtonStyle.secondary)
    async def espionage_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_espionage_menu(interaction, self.user_id)

    @discord.ui.button(label="Энергия", style=discord.ButtonStyle.secondary)
    async def energy_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_energy_menu(interaction, self.user_id)

    @discord.ui.button(label="Морская торговля", style=discord.ButtonStyle.secondary)
    async def maritime_trade_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_maritime_menu(interaction, self.user_id)

    @discord.ui.button(label="Гражданские товары", style=discord.ButtonStyle.secondary)
    async def civil_goods_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_civil_goods(interaction)

    @discord.ui.button(label="Корпорации", style=discord.ButtonStyle.secondary)
    async def corporations_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        with open("corporations_starting_data.json", "r", encoding="utf-8") as f:
            all_corps = json.load(f).get("corporations", {})
        view = CorpMainView(self.user_id, all_corps, self)
        embed = discord.Embed(title=f"{CORP_EMOJIS['money']} Корпорации", color=DARK_THEME_COLOR)
        embed.set_image(url=CORP_BANNER)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Центробанк", style=discord.ButtonStyle.secondary)
    async def central_bank_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_central_bank_menu(interaction, self.user_id)

    @discord.ui.button(label="На главную", style=discord.ButtonStyle.secondary)
    async def home_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return

        state = self.player_data["state"]
        politics = self.player_data["politics"]
        economy = self.player_data["economy"]
        currency_code = self.get_currency_code()
        budget = self.get_budget()
        gdp_local = self.get_gdp_local()
        military_budget = self.get_military_budget_local()
        usd_reserves = economy.get("foreign_reserves", {}).get("USD", 0)

        embed = discord.Embed(
            title=f"{state['statename']}",
            description=f"Лидер: {interaction.user.mention}",
            color=0x2b2d31
        )

        embed.add_field(name=f"{EMOJIS['job_spec']} Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"{state['stability']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Правительство", value=state['government_type'], inline=True)
        embed.add_field(name=f"{EMOJIS['partia']} Правящая партия", value=politics['ruling_party'], inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} Популярность", value=f"{politics['popularity']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} ВВП", value=f"{format_billion(gdp_local)} {currency_code}", inline=True)
        embed.add_field(name=f"{EMOJIS['money']} Бюджет", value=f"{format_billion(budget)} {currency_code}", inline=True)
        embed.add_field(name="USD-резервы", value=f"${format_billion(usd_reserves)}", inline=True)

        if "taxes" in economy:
            embed.add_field(name=f"{EMOJIS['government']} Налоги", value="Многокомпонентная система\n!налоги для просмотра", inline=True)
        else:
            embed.add_field(name=f"{EMOJIS['government']} Налог", value=f"{economy.get('tax_rate', 20)}%", inline=True)

        embed.add_field(name=f"{EMOJIS['army']} Армия", value=f"{format_army_number(state['army_size'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['manpower']} Опытность", value=f"{state.get('army_experience', 50):.0f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['army']} Военный бюджет", value=f"{format_billion(military_budget)} {currency_code}", inline=True)
        embed.add_field(name=f"{EMOJIS['social']} Счастье", value=f"{state['happiness']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['social']} Доверие", value=f"{state['trust']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['zakon']} Эффективность", value=f"{self.player_data['government_efficiency']:.0f}%", inline=True)

        alliance = self.get_player_alliance(interaction.user.id)
        if alliance:
            embed.add_field(name="Альянс", value=f"{alliance['name']} (участник)", inline=True)

        await interaction.response.edit_message(embed=embed, view=self)

    def get_player_alliance(self, user_id):
        alliances = load_alliances()
        for alliance in alliances["alliances"]:
            if str(user_id) in alliance.get("members", []):
                return alliance
        return None
    
# ==================== КОМАНДА ГАЙД ====================
@bot.command(name='гайд')
async def guide(ctx):
    """Показать список всех команд"""
    embed = discord.Embed(
        title="Гайд по командам бота",
        description="Все доступные команды для военно-политического симулятора",
        color=0x2b2d31
    )
    
    embed.add_field(
        name="Основные команды",
        value="`!государство` - Просмотр профиля своего государства\n"
              "`!ресурсы` - Просмотр ресурсов\n"
              "`!государство_игрока [@игрок]` - Профиль другого игрока\n"
              "`!армия_игрока [@игрок]` - Армия другого игрока\n"
              "`!бюджет_игрока [@игрок]` - Бюджет другого игрока\n"
              "`!расходы_игрока [@игрок]` - Расходы другого игрока\n"
              "`!ресурсы_игрока [@игрок]` - Ресурсы другого игрока\n"
              "`!товары_игрока [@игрок]` - Гражданские товары другого игрока\n"
              "`!статистика [@игрок]` - Полная статистика игрока",
        inline=False
    )
    
    embed.add_field(
        name="Экономика и бюджет",
        value="`!налоги` - Управление налоговой системой\n"
              "`!таможня` - Управление пошлинами и торговыми барьерами\n"
              "`!ресурсы` - Просмотр ресурсов\n"
              "`!центробанк` - Управление денежной массой, золотым резервом и долгом\n"
              "`!товары` - Просмотр гражданской продукции\n"
              "`!торговля [@игрок] [ресурс] [кол-во] [цена]` - Предложить сделку\n"
              "`!принять [ID]` - Принять торговое предложение\n"
              "`!мои_сделки` - Список моих активных сделок\n"
              "`!расходы` - Просмотр и настройка расходов по министерствам (оборона, здравоохранение, полиция, соцобеспечение, образование)",
        inline=False
    )
    
    embed.add_field(
        name="Военно-промышленный комплекс",
        value="`!впк` - Открыть меню покупки техники у корпораций\n"
              "`!заказы` - Просмотреть активные заказы\n"
              "`!получить` - Забрать готовую технику\n"
              "`!производство` - Информация о времени производства",
        inline=False
    )
    
    embed.add_field(
        name="Инфраструктура и ПВО",
        value="`!инфраструктура` - Меню строительства объектов (включая установку ПВО)\n"
              "`!трубопроводы` - Меню управления трубопроводами \n"
              "`!пво_арсенал` - Показать доступные ПВО в арсенале\n"
              "`!переместить_пво` - Переместить ПВО между регионами\n"
              "`!стройки` - Активные стройки\n"
              "`!стройки_завершить` - Забрать готовые объекты\n"
              "`!энергия` - Статус энергосистемы",
        inline=False
    )
    
    embed.add_field(
        name="Военные действия",
        value="`!удары` - Нанесение ударов БПЛА и ракетами по военной инфраструктуре\n"
              "`!флот` - Управление военно-морским флотом\n"
              "`!конфликты` - Список активных военных конфликтов\n"
              "`!война` - Статус ваших войн",
        inline=False
    )
    
    embed.add_field(
        name="Прочее",
        value="`!мобилизация` - Меню мобилизации гражданской промышленности\n"
              "`!разведка` - Специальные операции\n"
              "`!население` - Информация о населении\n"
              "`!спутники` - Управление спутниковой группировкой\n"
              "`!доктрины` - Военные доктрины\n"
              "`!время` - Текущее игровое время\n"
              "`!прогноз` - Прогноз потребления товаров",
        inline=False
    )
    
    if not ctx.author.guild_permissions.administrator:
        embed.set_footer(text="Для сделок используйте !торговля и !принять")
        await ctx.send(embed=embed)
        return
    
    await ctx.send(embed=embed)
    
    admin_embed = discord.Embed(
        title="Административные команды",
        color=0x2b2d31
    )
    
    admin_embed.add_field(
        name="Управление игроками",
        value="`!назначить [@игрок] [ID_гос-ва]` - Назначить игрока\n"
              "`!снять [@игрок]` - Снять игрока\n"
              "`!список` - Список доступных государств",
        inline=False
    )
    
    admin_embed.add_field(
        name="Управление данными",
        value="`!стат [@игрок] [путь] [значение]` - Изменить статистику\n"
              "`!просмотр [@игрок]` - Полная статистика (файл)\n"
              "`!год` - Провести годовой апдейт\n"
              "`!сброс` - Сбросить все государства к исходным значениям",
        inline=False
    )
    
    admin_embed.add_field(
        name="Управление ПВО",
        value="`!админ_пво [@игрок] [тип] [add/remove/set] [кол-во]` - Изменить ПВО в арсенале\n"
              "Типы: long_range_air_defense, short_range_air_defense, zdprk, zas, radar_systems",
        inline=False
    )
    
    admin_embed.set_footer(text="Только для администраторов")
    await ctx.send(embed=admin_embed)

# ==================== МЕНЮ АКТИВОВ (ФИНАЛЬНАЯ РАБОЧАЯ ВЕРСИЯ) ====================

import os
import json
from datetime import datetime
import discord
from discord.ui import Button, View, Select, Modal, TextInput

from utils import (
    DARK_THEME_COLOR, format_number, format_billion, format_gdp_display, format_budget_display,
    EXCHANGE_RATES_2019, get_budget, add_to_budget, get_currency_code,
    subtract_from_budget, load_states, save_states
)
from infra_build import (
    INFRASTRUCTURE_COSTS, ASSET_FIELDS, load_infrastructure, save_infrastructure
)

# ID канала для логов действий с активами
ASSETS_LOG_CHANNEL_ID = 1428066040948064277

# Файл для хранения замороженных активов
FROZEN_ASSETS_FILE = 'frozen_assets.json'

# Типы гражданских активов (без военной техники)
CIVILIAN_ASSET_FIELDS = [
    "civilian_factories",
    "office_centers",
    "oil_depots",
    "refineries",
    "thermal_power",
    "hydro_power",
    "solar_power",
    "nuclear_power",
    "wind_power",
    "internet_infrastructure",
]

# Стоимость активов в USD
ASSET_BASE_PRICES_USD = {
    "civilian_factories": 200_000_000,
    "office_centers": 150_000_000,
    "oil_depots": 150_000_000,
    "refineries": 400_000_000,
    "thermal_power": 350_000_000,
    "hydro_power": 600_000_000,
    "solar_power": 180_000_000,
    "nuclear_power": 1_500_000_000,
    "wind_power": 220_000_000,
    "internet_infrastructure": 100_000_000,
}

# Базовая зарплата рабочих по типам активов (USD в год)
WORKER_SALARY_USD = {
    "civilian_factories": 25000,
    "office_centers": 45000,
    "oil_depots": 35000,
    "refineries": 40000,
    "thermal_power": 38000,
    "hydro_power": 35000,
    "solar_power": 30000,
    "nuclear_power": 55000,
    "wind_power": 32000,
    "internet_infrastructure": 42000,
}

# Количество рабочих на один актив
WORKERS_PER_ASSET = {
    "civilian_factories": 200,
    "office_centers": 150,
    "oil_depots": 50,
    "refineries": 120,
    "thermal_power": 80,
    "hydro_power": 60,
    "solar_power": 40,
    "nuclear_power": 150,
    "wind_power": 50,
    "internet_infrastructure": 100,
}

# ==================== КАСТОМНЫЕ ЭМОДЗИ ====================

ASSET_EMOJIS = {
    "military_factories": "<:Military_factory:1492864212085506068>",
    "civilian_factories": "<:Civilian_factory:1492864140501323986>",
    "office_centers": "<:office_center:1492908676824957079>",
    "oil_depots": "<:Neftebaza:1492864864354570401>",
    "refineries": "<:NPZ:1492864753582997665>",
    "nuclear_power": "<:Nuclear_reactor:1492864507591262208>",
    "thermal_power": "<:Nuclear_reactor:1492864507591262208>",
    "hydro_power": "<:Nuclear_reactor:1492864507591262208>",
    "solar_power": "<:Nuclear_reactor:1492864507591262208>",
    "wind_power": "<:Nuclear_reactor:1492864507591262208>",
    "substations": "<:electrical_grid:1492864946898473030>",
    "power_lines": "<:electrical_grid:1492864946898473030>",
    "shipyards": "<:Naval_base:1492864427522003054>",
    "civilian_ports": "<:logistic:1492864675808022628>",
    "airports": "<:aerobase:1492865090070773881>",
    "military_airfields": "<:aerobase:1492865090070773881>",
    "railway_hubs": "<:logistic:1492864675808022628>",
    "roads_level": "<:doroga:1492863739995623425>",
    "bridges": "<:logistic:1492864675808022628>",
    "civilian_depots": "<:logistic:1492864675808022628>",
    "military_depots": "<:logistic:1492864675808022628>",
    "military_bases": "<:Military_factory:1492864212085506068>",
    "internet_infrastructure": "<:Telecommunication:1492864324975464548>",
    "communication_hubs": "<:Telecommunication:1492864324975464548>",
    "radio_towers": "<:Telecommunication:1492864324975464548>",
    "short_range_air_defense": "<:ZRK:1492864585995255808>",
    "long_range_air_defense": "<:ZRK:1492864585995255808>",
    "zdprk": "<:ZRK:1492864585995255808>",
    "zas": "<:ZRK:1492864585995255808>",
    "radar_systems": "<:ZRK:1492864585995255808>",
    "fortifications": "<:ukrep:1492864074634100938>",
}

SPECIALIZATION_EMOJIS = {
    "oil_rich": "<:big_fuel_reserves:1492880440128704583>",
    "resource_rich": "<:resource_extration:1492878755956527114>",
    "industrial_heartland": "<:construction_repair:1492879195657732256>",
    "technology_hub": "<:Technology_sharing:1432616738754793563>",
    "capital_region": "<:government:1487167580350451804>",
    "naval_base": "<:naval_center:1493160893742317578>",
    "agricultural_region": "<:build_supply:1492880349842243795>",
    "border_region": "<:ukrep:1492864074634100938>",
    "mountain_fortress": "<:ukrep:1492864074634100938>",
    "tourist_haven": "<:kurort:1493160788721143898>",
    "financial_center": "<:money:1429345094695129088>",
    "cultural_center": "<:education:1425212638366797824>",
    "arctic_region": "<:crisis:1487167453443391509>",
}

DEMOGRAPHIC_EMOJIS = {
    "population": "<:Icon_pop:1493160086284009593>",
    "population_growth": "<:Mod_pop_bonus_workforce_mult:1493160012648808458>",
    "development_level": "<:gold_price:1492880036792107008>",
    "birth_rate": "<:social:1425212640602357910>",
    "death_rate": "<:smert:1492913346859765892>",
    "unemployment_rate": "<:immigration:1492868112901472256>",
    "education_level": "<:education:1425212638366797824>",
    "separatism": "<:resistance:1492868038096060587>",
    "government_support": "<:loyal:1492867859968163851>",
    "happiness": "<:social:1487167248908156988>",
    "trust": "<:loyal:1492867859968163851>",
    "stability": "<:crisis:1487167453443391509>",
}

ECONOMIC_EMOJIS = {
    "grp": "<:fin:1425212665479041024>",
    "gdp_contribution": "<:eco_baff:1492879901760421888>",
    "average_wage": "<:size_pops_mult:1471574910580297850>",
    "cost_of_living": "<:money:1429345094695129088>",
    "budget": "<:money:1429345094695129088>",
    "gdp": "<:vvp:1487360602367070400>",
    "inflation": "<:economic_crisis:1492880645733617667>",
    "debt": "<:money:1429345094695129088>",
    "investments": "<:int_investments:1493303049047769239>",
}

ACTION_EMOJIS = {
    "domestic": "<:Civilian_factory:1492864140501323986>",
    "abroad": "<:Telecommunication:1492864324975464548>",
    "foreign": "<:office_center:1492908676824957079>",
    "staff": "<:immigration:1492868112901472256>",
    "close": "<:smert:1492913346859765892>",
    "freeze": "<:crisis:1487167453443391509>",
    "unfreeze": "<:eco_baff:1492879901760421888>",
    "nationalize": "<:government:1487167580350451804>",
    "destroy": "<:ukrep:1492864074634100938>",
    "pp": "<:pp:1487015341883130027>",
}

GENERAL_EMOJIS = {
    "coastal": "<:Naval_base:1492864427522003054>",
    "religion": "<:rebuild_pravoslavie:1492879017664057506>",
    "specialization": "<:resource_extration:1492878755956527114>",
}

RELIGION_EMOJIS = {
    "Ислам": "<:sunni_idea:1492909036021223455>",
    "Ислам (сунниты)": "<:sunni_idea:1492909036021223455>",
    "Ислам (шииты)": "<:sunni_idea:1492909036021223455>",
    "Алавиты": "<:sunni_idea:1492909036021223455>",
    "Атеизм/Агностицизм": "<:idea_ateism:1492908984548724779>",
    "Иудаизм": "<:judaism_idea:1492908854458191903>",
    "Синтоизм/Буддизм": "<:assianism_idea:1492908724585500832>",
    "Буддизм/Даосизм": "<:buddism_idea:1492908766109368460>",
    "Буддизм": "<:buddism_idea:1492908766109368460>",
    "Чхондогё": "<:assianism_idea:1492908724585500832>",
    "Католицизм": "<:christian_idea:1492908812179476632>",
    "Протестантизм": "<:christian_idea:1492908812179476632>",
    "Православие": "<:christian_idea:1492908812179476632>",
    "Христианство": "<:christian_idea:1492908812179476632>",
    "Копты": "<:christian_idea:1492908812179476632>",
    "default": "<:rebuild_pravoslavie:1492879017664057506>",
}

SPECIALIZATION_NAMES = {
    "oil_rich": "Нефтегазовая провинция",
    "resource_rich": "Ресурсный хаб",
    "industrial_heartland": "Промышленный центр",
    "technology_hub": "Технологический хаб",
    "capital_region": "Столичный регион",
    "naval_base": "Портовый центр",
    "agricultural_region": "Аграрный регион",
    "border_region": "Приграничный регион",
    "mountain_fortress": "Горная крепость",
    "tourist_haven": "Курортный центр",
    "financial_center": "Финансовый центр",
    "cultural_center": "Культурный центр",
    "arctic_region": "Арктический регион",
}

COUNTRY_FLAGS = {
    "США": "🇺🇸", "Россия": "🇷🇺", "Китай": "🇨🇳", "Германия": "🇩🇪",
    "Великобритания": "🇬🇧", "Франция": "🇫🇷", "Япония": "🇯🇵", "Израиль": "🇮🇱",
    "Украина": "🇺🇦", "Иран": "🇮🇷", "Беларусь": "🇧🇾", "Норвегия": "🇳🇴",
    "КНДР": "🇰🇵", "Турция": "🇹🇷", "Сирия": "🇸🇾", "Канада": "🇨🇦",
    "Польша": "🇵🇱", "Бразилия": "🇧🇷", "Швеция": "🇸🇪", "Финляндия": "🇫🇮",
    "Швейцария": "🇨🇭", "Египет": "🇪🇬"
}

def get_country_flag(country_name: str) -> str:
    return COUNTRY_FLAGS.get(country_name, "")

def get_country_currency_code(country_name: str) -> str:
    states = load_states()
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == country_name:
            return get_currency_code(data.get("economy", {}))
    return "USD"

def get_specialization_display(specialization: str) -> str:
    if not specialization:
        return ""
    name = SPECIALIZATION_NAMES.get(specialization, specialization.replace("_", " ").title())
    emoji = SPECIALIZATION_EMOJIS.get(specialization, "")
    return f"{emoji} {name}" if emoji else name


# ==================== РАБОТА С ЗАМОРОЖЕННЫМИ АКТИВАМИ ====================

def load_frozen_assets() -> dict:
    try:
        with open(FROZEN_ASSETS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_frozen_assets(data: dict):
    with open(FROZEN_ASSETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def is_asset_frozen(host_country: str, region_name: str, asset_type: str, owner_country: str) -> bool:
    frozen = load_frozen_assets()
    key = f"{host_country}:{region_name}:{asset_type}:{owner_country}"
    return frozen.get(key, False)

def set_asset_frozen(host_country: str, region_name: str, asset_type: str, owner_country: str, frozen: bool):
    data = load_frozen_assets()
    key = f"{host_country}:{region_name}:{asset_type}:{owner_country}"
    if frozen:
        data[key] = True
    else:
        data.pop(key, None)
    save_frozen_assets(data)


# ==================== ФУНКЦИЯ ЛОГИРОВАНИЯ ====================

async def send_asset_action_log(bot_instance, action_type: str, actor_country: str, target_country: str, 
                                region_name: str, assets_info: dict, details: dict = None):
    try:
        channel = bot_instance.get_channel(ASSETS_LOG_CHANNEL_ID)
        if not channel:
            return
        
        actor_flag = get_country_flag(actor_country)
        target_flag = get_country_flag(target_country)
        
        action_config = {
            "freeze": {
                "title": f"{ACTION_EMOJIS['freeze']} ЗАМОРОЗКА ИНОСТРАННЫХ АКТИВОВ",
                "color": 0x3498db,
                "description_template": "Правительство {actor} объявило о заморозке активов, принадлежащих {target}, на своей территории.",
            },
            "unfreeze": {
                "title": f"{ACTION_EMOJIS['unfreeze']} РАЗМОРОЗКА ИНОСТРАННЫХ АКТИВОВ",
                "color": 0x2ecc71,
                "description_template": "Правительство {actor} объявило о снятии ограничений с активов, принадлежащих {target}.",
            },
            "nationalize": {
                "title": f"{ACTION_EMOJIS['nationalize']} НАЦИОНАЛИЗАЦИЯ ИНОСТРАННЫХ АКТИВОВ",
                "color": 0xf1c40f,
                "description_template": "Правительство {actor} объявило о национализации стратегических активов, ранее принадлежавших {target}.",
            },
            "destroy": {
                "title": f"{ACTION_EMOJIS['destroy']} УНИЧТОЖЕНИЕ ИНОСТРАННЫХ АКТИВОВ",
                "color": 0xe74c3c,
                "description_template": "В результате действий правительства {actor} были полностью уничтожены промышленные объекты, принадлежавшие {target}.",
            }
        }
        
        config = action_config[action_type]
        
        embed = discord.Embed(
            title=config["title"],
            description=config["description_template"].format(
                actor=f"{actor_flag} **{actor_country}**" if actor_flag else f"**{actor_country}**",
                target=f"{target_flag} **{target_country}**" if target_flag else f"**{target_country}**"
            ),
            color=config["color"],
            timestamp=datetime.now()
        )
        
        assets_text = ""
        total_count = 0
        total_value = 0
        
        for asset_type, count in assets_info.items():
            if count > 0:
                asset_name = INFRASTRUCTURE_COSTS.get(asset_type, {}).get("name", asset_type)
                emoji = ASSET_EMOJIS.get(asset_type, "")
                value = count * ASSET_BASE_PRICES_USD.get(asset_type, 200_000_000)
                assets_text += f"{emoji} **{asset_name}**: {count} шт. (${format_billion(value)})\n" if emoji else f"• **{asset_name}**: {count} шт. (${format_billion(value)})\n"
                total_count += count
                total_value += value
        
        embed.add_field(name="📍 Регион", value=f"**{region_name}**, {actor_flag} {actor_country}", inline=False)
        embed.add_field(name="🏭 Затронутые активы", value=assets_text or "Нет данных", inline=False)
        embed.add_field(name=f"{ECONOMIC_EMOJIS['budget']} Общая стоимость", value=f"**${format_billion(total_value)}** ({total_count} объектов)", inline=True)
        
        if details:
            details_text = ""
            if "stability_cost" in details:
                details_text += f"• Стабильность: **-{details['stability_cost']:.2f}%**\n"
            if "money_cost" in details:
                details_text += f"• Затраты бюджета: **{format_billion(details['money_cost'])}**\n"
            if "pp_cost" in details:
                details_text += f"• Политическая власть: **-{details['pp_cost']:.0f}**\n"
            if "grp_loss" in details:
                details_text += f"• Потеря ВРП: **${format_billion(details['grp_loss'])}**\n"
            
            if details_text:
                embed.add_field(name="📊 Последствия", value=details_text, inline=False)
        
        embed.set_footer(text=f"• {datetime.now().strftime('%d.%m.%Y')}")
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f"Ошибка при отправке лога активов: {e}")


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_region_grp(region_data: dict) -> float:
    return region_data.get("grp", 0)

def set_region_grp(region_data: dict, value: float):
    region_data["grp"] = max(0, value)

def get_region_detailed_info(region_data: dict, country_name: str) -> discord.Embed:
    embed = discord.Embed(color=DARK_THEME_COLOR)
    
    rate = EXCHANGE_RATES_2019.get(country_name, 1.0)
    currency_code = get_country_currency_code(country_name)
    
    population = region_data.get("population", 0)
    development = region_data.get("development_level", 0)
    coastal = "Да" if region_data.get("coastal", False) else "Нет"
    specialization = region_data.get("specialization", "")
    spec_display = get_specialization_display(specialization)
    
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['population']} Население", value=format_number(population), inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['development_level']} Развитие", value=f"{development}%", inline=True)
    embed.add_field(name=f"{GENERAL_EMOJIS['coastal']} Выход к морю", value=coastal, inline=True)
    
    if spec_display:
        embed.add_field(name=f"{GENERAL_EMOJIS['specialization']} Специализация", value=spec_display, inline=True)
    else:
        embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    grp_usd = region_data.get("grp", 0)
    grp_local = grp_usd * rate
    gdp_contribution = region_data.get("gdp_contribution", 0)
    
    embed.add_field(name=f"{ECONOMIC_EMOJIS['grp']} ВРП", value=f"{format_billion(grp_local)} {currency_code}", inline=True)
    embed.add_field(name=f"{ECONOMIC_EMOJIS['gdp_contribution']} Вклад в ВВП", value=f"{gdp_contribution:.2f}%", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    birth_rate = region_data.get("birth_rate", 0)
    death_rate = region_data.get("death_rate", 0)
    population_growth = region_data.get("population_growth", 0)
    unemployment = region_data.get("unemployment_rate", 0)
    
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['birth_rate']} Рождаемость", value=f"{birth_rate:.1f}‰", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['death_rate']} Смертность", value=f"{death_rate:.1f}‰", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['population_growth']} Прирост", value=f"{population_growth:+.1f}‰", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['unemployment_rate']} Безработица", value=f"{unemployment:.1f}%", inline=True)
    
    education = region_data.get("education_level", 0)
    separatism = region_data.get("separatism", 0)
    gov_support = region_data.get("government_support", 0)
    
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['education_level']} Образованность", value=f"{education}%", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['separatism']} Сепаратизм", value=f"{separatism}%", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['government_support']} Поддержка власти", value=f"{gov_support}%", inline=True)
    
    main_religion = region_data.get("main_religion", "Не указано")
    religions = region_data.get("religions", {})
    if religions:
        religion_text = ""
        for rel, pct in sorted(religions.items(), key=lambda x: x[1], reverse=True)[:3]:
            emoji = RELIGION_EMOJIS.get(rel, RELIGION_EMOJIS["default"])
            religion_text += f"{emoji} {rel}: {pct}%\n"
        embed.add_field(name=f"{GENERAL_EMOJIS['religion']} Религии", value=religion_text or "Нет данных", inline=False)
    else:
        emoji = RELIGION_EMOJIS.get(main_religion, RELIGION_EMOJIS["default"])
        embed.add_field(name=f"{GENERAL_EMOJIS['religion']} Основная религия", value=f"{emoji} {main_religion}" if emoji else main_religion, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    avg_wage_usd = region_data.get("average_wage", 0)
    cost_of_living_usd = region_data.get("cost_of_living", 0)
    avg_wage_local = avg_wage_usd * rate
    cost_of_living_local = cost_of_living_usd * rate
    
    embed.add_field(name=f"{ECONOMIC_EMOJIS['average_wage']} Средняя ЗП", value=f"{format_billion(avg_wage_local)} {currency_code}/год", inline=True)
    embed.add_field(name=f"{ECONOMIC_EMOJIS['cost_of_living']} Стоимость жизни", value=f"{format_billion(cost_of_living_local)} {currency_code}/год", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    return embed


# ==================== ГЛАВНОЕ МЕНЮ ====================

async def show_assets_menu(interaction, user_id: int, player_data: dict):
    country_name = player_data["state"]["statename"]
    flag = get_country_flag(country_name)
    
    embed = discord.Embed(
        title=f"{flag} Управление активами: {country_name}" if flag else f"Управление активами: {country_name}",
        description="Выберите категорию для просмотра и управления",
        color=DARK_THEME_COLOR
    )
    
    view = AssetsCategorySelectView(user_id, player_data)
    await interaction.response.edit_message(embed=embed, view=view)


class AssetsCategorySelectView(View):
    def __init__(self, user_id: int, player_data: dict):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        
        options = [
            discord.SelectOption(label="Отечественные активы", value="domestic", description="Активы, принадлежащие вашей стране"),
            discord.SelectOption(label="Наши активы за рубежом", value="abroad", description="Активы в других странах"),
            discord.SelectOption(label="Иностранные активы у нас", value="foreign", description="Активы других стран на нашей территории"),
        ]
        
        select = Select(placeholder="Выберите категорию...", options=options)
        select.callback = self.on_category_select
        self.add_item(select)
        
        back_btn = Button(label="Назад к государству", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_state
        self.add_item(back_btn)
    
    async def on_category_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        category = interaction.data["values"][0]
        if category == "domestic":
            await self.show_econ_regions_for_domestic(interaction)
        elif category == "abroad":
            await self.show_countries_for_abroad(interaction)
        elif category == "foreign":
            await self.show_owners_for_foreign(interaction)
    
    async def show_econ_regions_for_domestic(self, interaction: discord.Interaction):
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        
        infra_data = load_infrastructure()
        econ_regions_with_assets = {}
        total_country_assets = 0
        total_regions_count = 0
        
        for country_id, country_data in infra_data.get("infrastructure", {}).items():
            if country_data.get("country") != country_name:
                continue
            
            if "economic_regions" in country_data:
                for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                    total_assets = 0
                    regions_count = 0
                    
                    if "regions" in econ_region_data:
                        for region_name, region_data in econ_region_data["regions"].items():
                            region_assets = 0
                            for asset_type in CIVILIAN_ASSET_FIELDS:
                                if asset_type in region_data:
                                    asset = region_data[asset_type]
                                    if isinstance(asset, dict) and "ownership" in asset:
                                        ownership = asset["ownership"]
                                        if country_name in ownership:
                                            region_assets += ownership[country_name]
                            
                            if region_assets > 0:
                                total_assets += region_assets
                                regions_count += 1
                    
                    if total_assets > 0:
                        econ_regions_with_assets[econ_region_name] = {
                            "total_assets": total_assets,
                            "regions_count": regions_count,
                            "regions_data": econ_region_data.get("regions", {})
                        }
                        total_country_assets += total_assets
                        total_regions_count += regions_count
            break
        
        embed = discord.Embed(
            title=f"{flag} {ACTION_EMOJIS['domestic']} Экономические районы: {country_name}" if flag else f"{ACTION_EMOJIS['domestic']} Экономические районы: {country_name}",
            description=f"Всего районов: {len(econ_regions_with_assets)} | Регионов с активами: {total_regions_count} | Активов: {total_country_assets}",
            color=DARK_THEME_COLOR
        )
        
        if econ_regions_with_assets:
            for econ_region, data in sorted(econ_regions_with_assets.items(), key=lambda x: x[1]['total_assets'], reverse=True)[:10]:
                embed.add_field(name=econ_region, value=f"Регионов: {data['regions_count']}\nАктивов: {data['total_assets']}", inline=True)
            if len(econ_regions_with_assets) > 10:
                embed.set_footer(text=f"Показано 10 из {len(econ_regions_with_assets)} районов. Выберите район из списка ниже.")
        else:
            embed.add_field(name="Нет активов", value="В вашей стране нет гражданских активов", inline=False)
        
        view = DomesticEconRegionSelectView(self.user_id, self.player_data, econ_regions_with_assets, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_countries_for_abroad(self, interaction: discord.Interaction):
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        
        infra_data = load_infrastructure()
        countries_with_assets = {}
        
        for country_id, country_data in infra_data.get("infrastructure", {}).items():
            host_country = country_data.get("country")
            if not host_country or host_country == country_name:
                continue
            
            regions = {}
            if "economic_regions" in country_data:
                for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                    if "regions" in econ_region_data:
                        regions.update(econ_region_data["regions"])
            elif "regions" in country_data:
                regions = country_data["regions"]
            
            total_assets = 0
            for region_name, region_data in regions.items():
                for asset_type in CIVILIAN_ASSET_FIELDS:
                    if asset_type in region_data:
                        asset = region_data[asset_type]
                        if isinstance(asset, dict) and "ownership" in asset:
                            ownership = asset["ownership"]
                            if country_name in ownership:
                                total_assets += ownership[country_name]
            
            if total_assets > 0:
                countries_with_assets[host_country] = total_assets
        
        embed = discord.Embed(
            title=f"{flag} {ACTION_EMOJIS['abroad']} Страны с нашими активами" if flag else f"{ACTION_EMOJIS['abroad']} Страны с нашими активами",
            description=f"Всего стран: {len(countries_with_assets)}",
            color=DARK_THEME_COLOR
        )
        
        if countries_with_assets:
            for country, count in sorted(countries_with_assets.items(), key=lambda x: x[1], reverse=True):
                host_flag = get_country_flag(country)
                embed.add_field(name=f"{host_flag} {country}" if host_flag else country, value=f"Активов: {count}", inline=True)
        else:
            embed.add_field(name="Нет активов", value="У вас нет активов за рубежом", inline=False)
        
        view = AbroadCountrySelectView(self.user_id, self.player_data, list(countries_with_assets.keys()), self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_owners_for_foreign(self, interaction: discord.Interaction):
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        
        infra_data = load_infrastructure()
        owners_with_assets = {}
        
        for country_id, country_data in infra_data.get("infrastructure", {}).items():
            host_country = country_data.get("country")
            if host_country != country_name:
                continue
            
            regions = {}
            if "economic_regions" in country_data:
                for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                    if "regions" in econ_region_data:
                        regions.update(econ_region_data["regions"])
            elif "regions" in country_data:
                regions = country_data["regions"]
            
            for region_name, region_data in regions.items():
                for asset_type in CIVILIAN_ASSET_FIELDS:
                    if asset_type in region_data:
                        asset = region_data[asset_type]
                        if isinstance(asset, dict) and "ownership" in asset:
                            ownership = asset["ownership"]
                            for owner_country, quantity in ownership.items():
                                if owner_country != country_name and quantity > 0:
                                    owners_with_assets[owner_country] = owners_with_assets.get(owner_country, 0) + quantity
        
        embed = discord.Embed(
            title=f"{flag} {ACTION_EMOJIS['foreign']} Иностранные активы в стране" if flag else f"{ACTION_EMOJIS['foreign']} Иностранные активы в стране",
            description=f"Всего стран-владельцев: {len(owners_with_assets)}",
            color=DARK_THEME_COLOR
        )
        
        if owners_with_assets:
            for owner, count in sorted(owners_with_assets.items(), key=lambda x: x[1], reverse=True):
                owner_flag = get_country_flag(owner)
                embed.add_field(name=f"{owner_flag} {owner}" if owner_flag else owner, value=f"Активов: {count}", inline=True)
        else:
            embed.add_field(name="Нет активов", value="В вашей стране нет иностранных активов", inline=False)
        
        view = ForeignOwnerSelectView(self.user_id, self.player_data, list(owners_with_assets.keys()), self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_state(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        from bot import StateButtons, EMOJIS
        
        state = self.player_data["state"]
        politics = self.player_data["politics"]
        economy = self.player_data["economy"]
        flag = get_country_flag(state['statename'])
        
        embed = discord.Embed(
            title=f"{flag} {state['statename']}" if flag else state['statename'],
            description=f"Лидер: {interaction.user.mention}",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name=f"{EMOJIS['job_spec']} Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"{state['stability']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Правительство", value=state['government_type'], inline=True)
        embed.add_field(name=f"{EMOJIS['partia']} Правящая партия", value=politics['ruling_party'], inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} Популярность", value=f"{politics['popularity']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} ВВП", value=format_gdp_display(economy), inline=True)
        embed.add_field(name=f"{EMOJIS['money']} Бюджет", value=format_budget_display(economy), inline=True)
        
        view = StateButtons(self.user_id, state['statename'], self.player_data)
        await interaction.response.edit_message(embed=embed, view=view)


# ==================== ОТЕЧЕСТВЕННЫЕ АКТИВЫ ====================

class DomesticEconRegionSelectView(View):
    def __init__(self, user_id: int, player_data: dict, econ_regions_with_assets: dict, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.econ_regions_with_assets = econ_regions_with_assets
        self.parent_view = parent_view
        
        options = []
        for econ_region, data in econ_regions_with_assets.items():
            options.append(discord.SelectOption(
                label=econ_region[:100], value=econ_region,
                description=f"{data['regions_count']} регионов, {data['total_assets']} активов"
            ))
        
        if options:
            select = Select(placeholder="Выберите экономический район...", options=options[:25])
            select.callback = self.on_econ_region_select
            self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_categories
        self.add_item(back_btn)
    
    async def on_econ_region_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = interaction.data["values"][0]
        data = self.econ_regions_with_assets[econ_region]
        
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        
        embed = discord.Embed(
            title=f"{flag} Регионы в районе: {econ_region}" if flag else f"Регионы в районе: {econ_region}",
            description=f"Регионов с активами: {data['regions_count']} | Всего активов: {data['total_assets']}",
            color=DARK_THEME_COLOR
        )
        
        regions_list = []
        for region_name, region_data in data['regions_data'].items():
            region_assets = 0
            for asset_type in CIVILIAN_ASSET_FIELDS:
                if asset_type in region_data:
                    asset = region_data[asset_type]
                    if isinstance(asset, dict) and "ownership" in asset:
                        ownership = asset["ownership"]
                        if country_name in ownership:
                            region_assets += ownership[country_name]
            
            if region_assets > 0:
                regions_list.append((region_name, region_assets, region_data))
        
        regions_list.sort(key=lambda x: x[1], reverse=True)
        
        for region, count, _ in regions_list[:15]:
            embed.add_field(name=region, value=f"Активов: {count}", inline=True)
        
        if len(regions_list) > 15:
            embed.set_footer(text=f"Показано 15 из {len(regions_list)} регионов. Выберите регион из списка ниже.")
        
        view = DomesticRegionSelectView(self.user_id, self.player_data, econ_region, regions_list, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_categories(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.show_econ_regions_for_domestic(interaction)


class DomesticRegionSelectView(View):
    def __init__(self, user_id: int, player_data: dict, econ_region: str, regions_list: list, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.econ_region = econ_region
        self.regions_list = regions_list
        self.parent_view = parent_view
        
        options = []
        for region, count, _ in regions_list[:25]:
            options.append(discord.SelectOption(label=region[:100], value=region, description=f"Активов: {count}"))
        
        if options:
            select = Select(placeholder="Выберите регион...", options=options)
            select.callback = self.on_region_select
            self.add_item(select)
        
        back_btn = Button(label="Назад к районам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_econ_regions
        self.add_item(back_btn)
    
    async def on_region_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        region_name = interaction.data["values"][0]
        
        region_data = None
        for r_name, _, r_data in self.regions_list:
            if r_name == region_name:
                region_data = r_data
                break
        
        if not region_data:
            await interaction.response.send_message("Регион не найден!", ephemeral=True)
            return
        
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        
        embed = discord.Embed(
            title=f"{flag} Регион: {region_name}" if flag else f"Регион: {region_name}",
            description=f"Экономический район: {self.econ_region}",
            color=DARK_THEME_COLOR
        )
        
        detail_embed = get_region_detailed_info(region_data, country_name)
        for field in detail_embed.fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        
        assets_text = ""
        total_assets = 0
        total_value_usd = 0
        
        for asset_type in CIVILIAN_ASSET_FIELDS:
            if asset_type in region_data:
                asset = region_data[asset_type]
                if isinstance(asset, dict) and "ownership" in asset:
                    ownership = asset["ownership"]
                    if country_name in ownership and ownership[country_name] > 0:
                        asset_name = INFRASTRUCTURE_COSTS.get(asset_type, {}).get("name", asset_type)
                        emoji = ASSET_EMOJIS.get(asset_type, "")
                        count = ownership[country_name]
                        value = count * ASSET_BASE_PRICES_USD.get(asset_type, 200_000_000)
                        assets_text += f"{emoji} {asset_name}: {count} (${format_billion(value)})\n" if emoji else f"• {asset_name}: {count} (${format_billion(value)})\n"
                        total_assets += count
                        total_value_usd += value
        
        if assets_text:
            embed.add_field(name=f"{ACTION_EMOJIS['domestic']} Гражданские активы", value=assets_text, inline=False)
        else:
            embed.add_field(name=f"{ACTION_EMOJIS['domestic']} Гражданские активы", value="Нет активов", inline=False)
        
        embed.set_footer(text=f"Всего активов: {total_assets} | Общая стоимость: ${format_billion(total_value_usd)}")
        
        view = DomesticAssetManageView(self.user_id, self.player_data, region_name, region_data, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_econ_regions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.show_econ_regions_for_domestic(interaction)


class DomesticAssetManageView(View):
    def __init__(self, user_id: int, player_data: dict, region_name: str, region_data: dict, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.region_name = region_name
        self.region_data = region_data
        self.parent_view = parent_view
        
        country_name = player_data["state"]["statename"]
        
        self.assets_in_region = {}
        for asset_type in CIVILIAN_ASSET_FIELDS:
            if asset_type in region_data:
                asset = region_data[asset_type]
                if isinstance(asset, dict) and "ownership" in asset:
                    ownership = asset["ownership"]
                    if country_name in ownership and ownership[country_name] > 0:
                        self.assets_in_region[asset_type] = {
                            "name": INFRASTRUCTURE_COSTS.get(asset_type, {}).get("name", asset_type),
                            "count": ownership[country_name],
                            "emoji": ASSET_EMOJIS.get(asset_type, "")
                        }
        
        options = []
        if self.assets_in_region:
            options.append(discord.SelectOption(label="Управление персоналом", value="staff", description="Нанять/уволить рабочих, изменить зарплаты"))
            options.append(discord.SelectOption(label="Закрыть актив", value="close", description="Закрыть актив и вернуть 40% стоимости"))
        else:
            options.append(discord.SelectOption(label="Нет активов для управления", value="none", description="В этом регионе нет ваших активов"))
        
        select = Select(placeholder="Выберите действие...", options=options)
        select.callback = self.on_action_select
        self.add_item(select)
        
        back_btn = Button(label="Назад к регионам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_regions
        self.add_item(back_btn)
    
    async def on_action_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        action = interaction.data["values"][0]
        if action == "none":
            await interaction.response.send_message("В этом регионе нет активов для управления.", ephemeral=True)
        elif action == "staff":
            await self.show_staff_management(interaction)
        elif action == "close":
            await self.show_close_asset(interaction)
    
    async def show_staff_management(self, interaction: discord.Interaction):
        options = []
        for asset_type, data in self.assets_in_region.items():
            options.append(discord.SelectOption(label=data['name'][:100], value=asset_type, description=f"Доступно: {data['count']} шт."))
        
        embed = discord.Embed(
            title=f"{ACTION_EMOJIS['staff']} Управление персоналом",
            description="Выберите тип актива для управления персоналом.\n\n**Влияние персонала:**\n• Меньше рабочих: снижение эффективности и прибыли\n• Больше рабочих: повышение эффективности (до +25%) и прибыли\n• Зарплата зависит от типа актива и средней ЗП в регионе",
            color=DARK_THEME_COLOR
        )
        
        view = StaffAssetSelectView(self.user_id, self.player_data, self.region_name, self.region_data, options, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_close_asset(self, interaction: discord.Interaction):
        options = []
        for asset_type, data in self.assets_in_region.items():
            value = data['count'] * ASSET_BASE_PRICES_USD.get(asset_type, 200_000_000)
            refund = value * 0.4
            options.append(discord.SelectOption(label=data['name'][:100], value=asset_type, description=f"{data['count']} шт. | Возврат: ${format_billion(refund)}"))
        
        embed = discord.Embed(
            title=f"{ACTION_EMOJIS['close']} Закрытие актива",
            description="Выберите тип актива для закрытия.\n\n**Последствия закрытия:**\n• Возврат 40% от стоимости актива в бюджет\n• Потеря ВРП региона (30% от стоимости актива)\n• Увольнение всех рабочих\n• Невозможность восстановить актив",
            color=discord.Color.orange()
        )
        
        view = CloseAssetSelectView(self.user_id, self.player_data, self.region_name, self.region_data, options, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_regions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.parent_view.show_econ_regions_for_domestic(interaction)


class StaffAssetSelectView(View):
    def __init__(self, user_id: int, player_data: dict, region_name: str, region_data: dict, options: list, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.region_name = region_name
        self.region_data = region_data
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите тип актива...", options=options)
        select.callback = self.on_asset_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_actions
        self.add_item(back_btn)
    
    async def on_asset_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        asset_type = interaction.data["values"][0]
        country_name = self.player_data["state"]["statename"]
        rate = EXCHANGE_RATES_2019.get(country_name, 1.0)
        currency_code = get_country_currency_code(country_name)
        
        asset_count = self.parent_view.assets_in_region[asset_type]['count']
        workers_per_asset = WORKERS_PER_ASSET.get(asset_type, 100)
        optimal_workers = asset_count * workers_per_asset
        
        current_workers = self.region_data.get(f"{asset_type}_workers", optimal_workers)
        
        base_salary_usd = WORKER_SALARY_USD.get(asset_type, 30000)
        avg_wage_usd = self.region_data.get("average_wage", base_salary_usd)
        actual_salary_usd = (base_salary_usd * 0.7 + avg_wage_usd * 0.3)
        actual_salary_local = actual_salary_usd * rate
        
        data = self.parent_view.assets_in_region[asset_type]
        title = f"{data['emoji']} {data['name']}" if data['emoji'] else data['name']
        
        efficiency = min(1.25, max(0.5, current_workers / optimal_workers))
        
        embed = discord.Embed(
            title=f"{ACTION_EMOJIS['staff']} Управление персоналом: {title}",
            description=f"**Количество активов:** {asset_count}\n**Текущие рабочие:** {format_number(current_workers)}\n**Оптимальное количество:** {format_number(optimal_workers)}\n**Текущая эффективность:** {efficiency*100:.1f}%\n\n**Зарплата 1 рабочего:** {format_billion(actual_salary_local)} {currency_code}/год\n**Годовой ФОТ:** {format_billion(actual_salary_local * current_workers)} {currency_code}",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(
            name="📊 Эффекты изменения",
            value=f"• **Меньше рабочих:** снижение эффективности и прибыли, экономия на зарплатах\n• **Больше рабочих:** повышение эффективности (макс +25%), рост прибыли, рост расходов\n• **Оптимально:** {format_number(optimal_workers)} рабочих (100% эффективность)",
            inline=False
        )
        
        view = StaffQuantityView(self.user_id, self.player_data, self.region_name, self.region_data, 
                                 asset_type, asset_count, current_workers, optimal_workers, 
                                 actual_salary_local, currency_code, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_actions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.show_staff_management(interaction)


class StaffQuantityView(View):
    def __init__(self, user_id: int, player_data: dict, region_name: str, region_data: dict,
                 asset_type: str, asset_count: int, current_workers: int, optimal_workers: int,
                 salary_per_worker: float, currency_code: str, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.asset_count = asset_count
        self.current_workers = current_workers
        self.optimal_workers = optimal_workers
        self.salary_per_worker = salary_per_worker
        self.currency_code = currency_code
        self.parent_view = parent_view
        
        self.hire_10_btn = Button(label="+10%", style=discord.ButtonStyle.success)
        self.hire_10_btn.callback = lambda i: self.confirm_change(i, int(current_workers * 1.1))
        self.add_item(self.hire_10_btn)
        
        self.hire_25_btn = Button(label="+25%", style=discord.ButtonStyle.success)
        self.hire_25_btn.callback = lambda i: self.confirm_change(i, int(current_workers * 1.25))
        self.add_item(self.hire_25_btn)
        
        self.optimal_btn = Button(label="Оптимально", style=discord.ButtonStyle.primary)
        self.optimal_btn.callback = lambda i: self.confirm_change(i, optimal_workers)
        self.add_item(self.optimal_btn)
        
        self.fire_10_btn = Button(label="-10%", style=discord.ButtonStyle.danger)
        self.fire_10_btn.callback = lambda i: self.confirm_change(i, int(current_workers * 0.9))
        self.add_item(self.fire_10_btn)
        
        self.fire_25_btn = Button(label="-25%", style=discord.ButtonStyle.danger)
        self.fire_25_btn.callback = lambda i: self.confirm_change(i, int(current_workers * 0.75))
        self.add_item(self.fire_25_btn)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary, row=1)
        back_btn.callback = self.back_to_asset_select
        self.add_item(back_btn)
    
    async def confirm_change(self, interaction: discord.Interaction, new_workers: int):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        min_workers = max(1, int(self.optimal_workers * 0.1))
        new_workers = max(min_workers, new_workers)
        
        old_efficiency = min(1.25, max(0.5, self.current_workers / self.optimal_workers))
        new_efficiency = min(1.25, max(0.5, new_workers / self.optimal_workers))
        
        old_salary_total = self.current_workers * self.salary_per_worker
        new_salary_total = new_workers * self.salary_per_worker
        salary_diff = new_salary_total - old_salary_total
        
        embed = discord.Embed(
            title="Подтверждение изменения персонала",
            color=discord.Color.green() if new_workers > self.current_workers else discord.Color.red() if new_workers < self.current_workers else DARK_THEME_COLOR
        )
        
        data = self.parent_view.parent_view.assets_in_region[self.asset_type]
        title = f"{data['emoji']} {data['name']}" if data['emoji'] else data['name']
        
        embed.add_field(name="Актив", value=title, inline=False)
        embed.add_field(name="Рабочие", value=f"{format_number(self.current_workers)} → **{format_number(new_workers)}**", inline=True)
        embed.add_field(name="Эффективность", value=f"{old_efficiency*100:.1f}% → **{new_efficiency*100:.1f}%**", inline=True)
        embed.add_field(name="Изменение ФОТ", value=f"{format_billion(salary_diff)} {self.currency_code}/год", inline=True)
        
        view = ConfirmStaffChangeView(
            self.user_id, self.player_data, self.region_name, self.region_data,
            self.asset_type, new_workers, self.current_workers, self.optimal_workers, self
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_asset_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.show_staff_management(interaction)


class ConfirmStaffChangeView(View):
    def __init__(self, user_id: int, player_data: dict, region_name: str, region_data: dict,
                 asset_type: str, new_workers: int, old_workers: int, optimal_workers: int, parent_view: View):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.new_workers = new_workers
        self.old_workers = old_workers
        self.optimal_workers = optimal_workers
        self.parent_view = parent_view
    
    @discord.ui.button(label="Подтвердить", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        self.region_data[f"{self.asset_type}_workers"] = self.new_workers
        
        infra_data = load_infrastructure()
        country_name = self.player_data["state"]["statename"]
        for country_id, country_data in infra_data.get("infrastructure", {}).items():
            if country_data.get("country") == country_name:
                if "economic_regions" in country_data:
                    for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                        if self.region_name in econ_region_data.get("regions", {}):
                            econ_region_data["regions"][self.region_name] = self.region_data
                            break
                break
        save_infrastructure(infra_data)
        
        old_efficiency = min(1.25, max(0.5, self.old_workers / self.optimal_workers))
        new_efficiency = min(1.25, max(0.5, self.new_workers / self.optimal_workers))
        
        embed = discord.Embed(
            title="Персонал обновлён",
            description=f"Количество рабочих изменено с {format_number(self.old_workers)} до {format_number(self.new_workers)}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Эффективность", value=f"{old_efficiency*100:.1f}% → **{new_efficiency*100:.1f}%**", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.show_staff_management(interaction)


class CloseAssetSelectView(View):
    def __init__(self, user_id: int, player_data: dict, region_name: str, region_data: dict, options: list, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.region_name = region_name
        self.region_data = region_data
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите актив для закрытия...", options=options)
        select.callback = self.on_asset_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_actions
        self.add_item(back_btn)
    
    async def on_asset_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        asset_type = interaction.data["values"][0]
        modal = CloseAssetQuantityModal(self.user_id, self.player_data, self.region_name, 
                                        self.region_data, asset_type, 
                                        self.parent_view.assets_in_region[asset_type]['count'], self)
        await interaction.response.send_modal(modal)
    
    async def back_to_actions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.parent_view.parent_view.show_econ_regions_for_domestic(interaction)


class CloseAssetQuantityModal(Modal, title="Закрытие актива"):
    def __init__(self, user_id: int, player_data: dict, region_name: str, region_data: dict, 
                 asset_type: str, max_count: int, parent_view: View):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.max_count = max_count
        self.parent_view = parent_view
        
        value_per_unit = ASSET_BASE_PRICES_USD.get(asset_type, 200_000_000)
        refund_per_unit = value_per_unit * 0.4
        
        self.quantity = TextInput(
            label=f"Количество для закрытия (макс: {max_count})",
            placeholder=f"Возврат: ${format_billion(refund_per_unit)} за шт.",
            min_length=1, max_length=4, required=True
        )
        self.add_item(self.quantity)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantity.value)
            if qty < 1 or qty > self.max_count:
                await interaction.response.send_message(f"Введите число от 1 до {self.max_count}!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Введите корректное число!", ephemeral=True)
            return
        
        country_name = self.player_data["state"]["statename"]
        value_per_unit = ASSET_BASE_PRICES_USD.get(self.asset_type, 200_000_000)
        total_value_usd = qty * value_per_unit
        total_refund_usd = qty * value_per_unit * 0.4
        grp_loss_usd = qty * value_per_unit * 0.3
        
        rate = EXCHANGE_RATES_2019.get(country_name, 1.0)
        currency_code = get_country_currency_code(country_name)
        local_refund = total_refund_usd * rate
        
        embed = discord.Embed(
            title="⚠️ Подтверждение закрытия активов",
            description=f"Вы собираетесь закрыть **{qty}** из **{self.max_count}** активов типа **{INFRASTRUCTURE_COSTS.get(self.asset_type, {}).get('name', self.asset_type)}** в регионе **{self.region_name}**.",
            color=discord.Color.orange()
        )
        embed.add_field(name=f"{ECONOMIC_EMOJIS['budget']} Возврат в бюджет", value=f"{format_billion(local_refund)} {currency_code}", inline=True)
        embed.add_field(name=f"{ECONOMIC_EMOJIS['grp']} Потеря ВРП региона", value=f"{format_billion(grp_loss_usd * rate)} {currency_code}", inline=True)
        embed.add_field(name=f"{ACTION_EMOJIS['domestic']} Стоимость активов", value=f"${format_billion(total_value_usd)}", inline=True)
        embed.set_footer(text="Это действие нельзя отменить!")
        
        view = ConfirmCloseAssetView(
            self.user_id, self.player_data, self.region_name, self.region_data,
            self.asset_type, qty, total_refund_usd, grp_loss_usd, self
        )
        await interaction.response.edit_message(embed=embed, view=view)


class ConfirmCloseAssetView(View):
    def __init__(self, user_id: int, player_data: dict, region_name: str, region_data: dict,
                 asset_type: str, quantity: int, refund_usd: float, grp_loss_usd: float, parent_modal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.quantity = quantity
        self.refund_usd = refund_usd
        self.grp_loss_usd = grp_loss_usd
        self.parent_modal = parent_modal
    
    @discord.ui.button(label="Да, закрыть", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        country_name = self.player_data["state"]["statename"]
        rate = EXCHANGE_RATES_2019.get(country_name, 1.0)
        local_refund = self.refund_usd * rate
        
        infra_data = load_infrastructure()
        for country_id, country_data in infra_data.get("infrastructure", {}).items():
            if country_data.get("country") == country_name:
                if "economic_regions" in country_data:
                    for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                        if self.region_name in econ_region_data.get("regions", {}):
                            region_data = econ_region_data["regions"][self.region_name]
                            if self.asset_type in region_data:
                                asset = region_data[self.asset_type]
                                if isinstance(asset, dict) and "ownership" in asset:
                                    ownership = asset["ownership"]
                                    if country_name in ownership:
                                        ownership[country_name] = max(0, ownership[country_name] - self.quantity)
                                        if ownership[country_name] == 0:
                                            del ownership[country_name]
                                        asset["total"] = sum(ownership.values())
                            
                            current_grp = get_region_grp(region_data)
                            set_region_grp(region_data, current_grp - self.grp_loss_usd)
                            
                            if f"{self.asset_type}_workers" in region_data:
                                workers_per_asset = WORKERS_PER_ASSET.get(self.asset_type, 100)
                                current_workers = region_data[f"{self.asset_type}_workers"]
                                new_workers = max(0, current_workers - (self.quantity * workers_per_asset))
                                region_data[f"{self.asset_type}_workers"] = new_workers
                            
                            econ_region_data["regions"][self.region_name] = region_data
                            break
                break
        save_infrastructure(infra_data)
        
        add_to_budget(self.player_data["economy"], local_refund)
        
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == country_name:
                data["economy"] = self.player_data["economy"]
                break
        save_states(states)
        
        asset_name = INFRASTRUCTURE_COSTS.get(self.asset_type, {}).get("name", self.asset_type)
        emoji = ASSET_EMOJIS.get(self.asset_type, "")
        currency_code = get_country_currency_code(country_name)
        
        embed = discord.Embed(
            title="Активы закрыты",
            description=f"Закрыто {self.quantity} {emoji} {asset_name} в регионе {self.region_name}." if emoji else f"Закрыто {self.quantity} {asset_name} в регионе {self.region_name}.",
            color=discord.Color.orange()
        )
        embed.add_field(name=f"{ECONOMIC_EMOJIS['budget']} Возврат в бюджет", value=f"{format_billion(local_refund)} {currency_code}", inline=True)
        embed.add_field(name=f"{ECONOMIC_EMOJIS['grp']} Потеря ВРП", value=f"{format_billion(self.grp_loss_usd * rate)} {currency_code}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        embed = discord.Embed(title="Действие отменено", color=DARK_THEME_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ЗАРУБЕЖНЫЕ АКТИВЫ ====================

class AbroadCountrySelectView(View):
    def __init__(self, user_id: int, player_data: dict, countries: list, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.countries = countries
        self.parent_view = parent_view
        
        options = []
        for country in countries[:25]:
            flag = get_country_flag(country)
            label = f"{flag} {country}" if flag else country
            options.append(discord.SelectOption(label=label[:100], value=country))
        
        if options:
            select = Select(placeholder="Выберите страну...", options=options)
            select.callback = self.on_country_select
            self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_categories
        self.add_item(back_btn)
    
    async def on_country_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        host_country = interaction.data["values"][0]
        await self.show_econ_regions_in_country(interaction, host_country)
    
    async def show_econ_regions_in_country(self, interaction: discord.Interaction, host_country: str):
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        host_flag = get_country_flag(host_country)
        
        infra_data = load_infrastructure()
        econ_regions_with_assets = {}
        total_country_assets = 0
        
        for country_id, country_data in infra_data.get("infrastructure", {}).items():
            if country_data.get("country") != host_country:
                continue
            
            if "economic_regions" in country_data:
                for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                    total_assets = 0
                    regions_count = 0
                    
                    if "regions" in econ_region_data:
                        for region_name, region_data in econ_region_data["regions"].items():
                            region_assets = 0
                            for asset_type in CIVILIAN_ASSET_FIELDS:
                                if asset_type in region_data:
                                    asset = region_data[asset_type]
                                    if isinstance(asset, dict) and "ownership" in asset:
                                        ownership = asset["ownership"]
                                        if country_name in ownership:
                                            region_assets += ownership[country_name]
                            
                            if region_assets > 0:
                                total_assets += region_assets
                                regions_count += 1
                    
                    if total_assets > 0:
                        econ_regions_with_assets[econ_region_name] = {
                            "total_assets": total_assets,
                            "regions_count": regions_count,
                            "regions_data": econ_region_data.get("regions", {})
                        }
                        total_country_assets += total_assets
            break
        
        embed = discord.Embed(
            title=f"{flag} Наши активы в {host_flag} {host_country}" if flag and host_flag else f"Наши активы в {host_country}",
            description=f"Всего районов: {len(econ_regions_with_assets)} | Активов: {total_country_assets}",
            color=DARK_THEME_COLOR
        )
        
        if econ_regions_with_assets:
            for econ_region, data in sorted(econ_regions_with_assets.items(), key=lambda x: x[1]['total_assets'], reverse=True)[:10]:
                embed.add_field(name=econ_region, value=f"Регионов: {data['regions_count']}\nАктивов: {data['total_assets']}", inline=True)
        
        view = AbroadEconRegionSelectView(self.user_id, self.player_data, host_country, econ_regions_with_assets, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_categories(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.show_countries_for_abroad(interaction)


class AbroadEconRegionSelectView(View):
    def __init__(self, user_id: int, player_data: dict, host_country: str, econ_regions_with_assets: dict, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.host_country = host_country
        self.econ_regions_with_assets = econ_regions_with_assets
        self.parent_view = parent_view
        
        options = []
        for econ_region, data in econ_regions_with_assets.items():
            options.append(discord.SelectOption(
                label=econ_region[:100], value=econ_region,
                description=f"{data['regions_count']} регионов, {data['total_assets']} активов"
            ))
        
        if options:
            select = Select(placeholder="Выберите экономический район...", options=options[:25])
            select.callback = self.on_econ_region_select
            self.add_item(select)
        
        back_btn = Button(label="Назад к странам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_countries
        self.add_item(back_btn)
    
    async def on_econ_region_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = interaction.data["values"][0]
        data = self.econ_regions_with_assets[econ_region]
        
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        host_flag = get_country_flag(self.host_country)
        
        embed = discord.Embed(
            title=f"{flag} Регионы в {host_flag} {self.host_country} / {econ_region}" if flag and host_flag else f"Регионы в {self.host_country} / {econ_region}",
            description=f"Регионов с активами: {data['regions_count']} | Всего активов: {data['total_assets']}",
            color=DARK_THEME_COLOR
        )
        
        regions_list = []
        for region_name, region_data in data['regions_data'].items():
            region_assets = 0
            for asset_type in CIVILIAN_ASSET_FIELDS:
                if asset_type in region_data:
                    asset = region_data[asset_type]
                    if isinstance(asset, dict) and "ownership" in asset:
                        ownership = asset["ownership"]
                        if country_name in ownership:
                            region_assets += ownership[country_name]
            
            if region_assets > 0:
                regions_list.append((region_name, region_assets, region_data))
        
        regions_list.sort(key=lambda x: x[1], reverse=True)
        
        for region, count, _ in regions_list[:15]:
            embed.add_field(name=region, value=f"Активов: {count}", inline=True)
        
        if len(regions_list) > 15:
            embed.set_footer(text=f"Показано 15 из {len(regions_list)} регионов. Выберите регион из списка ниже.")
        
        view = AbroadRegionSelectView(self.user_id, self.player_data, self.host_country, econ_region, regions_list, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_countries(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.show_countries_for_abroad(interaction)


class AbroadRegionSelectView(View):
    def __init__(self, user_id: int, player_data: dict, host_country: str, econ_region: str, regions_list: list, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.host_country = host_country
        self.econ_region = econ_region
        self.regions_list = regions_list
        self.parent_view = parent_view
        
        options = []
        for region, count, _ in regions_list[:25]:
            options.append(discord.SelectOption(label=region[:100], value=region, description=f"Активов: {count}"))
        
        if options:
            select = Select(placeholder="Выберите регион...", options=options)
            select.callback = self.on_region_select
            self.add_item(select)
        
        back_btn = Button(label="Назад к районам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_econ_regions
        self.add_item(back_btn)
    
    async def on_region_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        region_name = interaction.data["values"][0]
        
        region_data = None
        for r_name, _, r_data in self.regions_list:
            if r_name == region_name:
                region_data = r_data
                break
        
        if not region_data:
            await interaction.response.send_message("Регион не найден!", ephemeral=True)
            return
        
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        host_flag = get_country_flag(self.host_country)
        
        embed = discord.Embed(
            title=f"{flag} Активы в {host_flag} {self.host_country} / {self.econ_region} / {region_name}" if flag and host_flag else f"Активы в {self.host_country} / {self.econ_region} / {region_name}",
            color=DARK_THEME_COLOR
        )
        
        detail_embed = get_region_detailed_info(region_data, self.host_country)
        for field in detail_embed.fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        
        assets_text = ""
        total_assets = 0
        total_value_usd = 0
        
        for asset_type in CIVILIAN_ASSET_FIELDS:
            if asset_type in region_data:
                asset = region_data[asset_type]
                if isinstance(asset, dict) and "ownership" in asset:
                    ownership = asset["ownership"]
                    if country_name in ownership and ownership[country_name] > 0:
                        asset_name = INFRASTRUCTURE_COSTS.get(asset_type, {}).get("name", asset_type)
                        emoji = ASSET_EMOJIS.get(asset_type, "")
                        count = ownership[country_name]
                        value = count * ASSET_BASE_PRICES_USD.get(asset_type, 200_000_000)
                        assets_text += f"{emoji} {asset_name}: {count} (${format_billion(value)})\n" if emoji else f"• {asset_name}: {count} (${format_billion(value)})\n"
                        total_assets += count
                        total_value_usd += value
        
        if assets_text:
            embed.add_field(name=f"{ACTION_EMOJIS['abroad']} Наши активы", value=assets_text, inline=False)
        else:
            embed.add_field(name=f"{ACTION_EMOJIS['abroad']} Наши активы", value="Нет активов", inline=False)
        
        embed.set_footer(text=f"Всего активов: {total_assets} | Стоимость: ${format_billion(total_value_usd)}")
        
        view = AbroadAssetManageView(self.user_id, self.player_data, self.host_country, region_name, region_data, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_econ_regions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.show_econ_regions_in_country(interaction, self.host_country)


class AbroadAssetManageView(View):
    def __init__(self, user_id: int, player_data: dict, host_country: str, region_name: str, region_data: dict, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.host_country = host_country
        self.region_name = region_name
        self.region_data = region_data
        self.parent_view = parent_view
        
        country_name = player_data["state"]["statename"]
        
        assets_here = {}
        for asset_type in CIVILIAN_ASSET_FIELDS:
            if asset_type in region_data:
                asset = region_data[asset_type]
                if isinstance(asset, dict) and "ownership" in asset:
                    ownership = asset["ownership"]
                    if country_name in ownership and ownership[country_name] > 0:
                        assets_here[asset_type] = ownership[country_name]
        
        options = []
        if assets_here:
            options.append(discord.SelectOption(label="Закрыть актив", value="close", description="Закрыть актив и вернуть 30% стоимости"))
        else:
            options.append(discord.SelectOption(label="Нет активов для управления", value="none", description="В этом регионе нет ваших активов"))
        
        select = Select(placeholder="Выберите действие...", options=options)
        select.callback = self.on_action_select
        self.add_item(select)
        
        back_btn = Button(label="Назад к регионам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_regions
        self.add_item(back_btn)
    
    async def on_action_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        action = interaction.data["values"][0]
        if action == "none":
            await interaction.response.send_message("В этом регионе нет активов для управления.", ephemeral=True)
        elif action == "close":
            await self.show_close_asset(interaction)
    
    async def show_close_asset(self, interaction: discord.Interaction):
        country_name = self.player_data["state"]["statename"]
        assets_here = {}
        for asset_type in CIVILIAN_ASSET_FIELDS:
            if asset_type in self.region_data:
                asset = self.region_data[asset_type]
                if isinstance(asset, dict) and "ownership" in asset:
                    ownership = asset["ownership"]
                    if country_name in ownership and ownership[country_name] > 0:
                        assets_here[asset_type] = ownership[country_name]
        
        options = []
        for asset_type, count in assets_here.items():
            value = count * ASSET_BASE_PRICES_USD.get(asset_type, 200_000_000)
            refund = value * 0.3
            asset_name = INFRASTRUCTURE_COSTS.get(asset_type, {}).get("name", asset_type)
            options.append(discord.SelectOption(label=asset_name[:100], value=asset_type, description=f"{count} шт. | Возврат: ${format_billion(refund)}"))
        
        embed = discord.Embed(
            title=f"{ACTION_EMOJIS['close']} Закрытие зарубежного актива",
            description="Выберите тип актива для закрытия.\n\n**Последствия:**\n• Возврат 30% от стоимости актива\n• Потеря ВРП региона (20% от стоимости)\n• Увольнение всех рабочих",
            color=discord.Color.orange()
        )
        
        view = CloseAbroadAssetSelectView(self.user_id, self.player_data, self.host_country, self.region_name, self.region_data, options, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_regions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.parent_view.show_econ_regions_in_country(interaction, self.host_country)


class CloseAbroadAssetSelectView(View):
    def __init__(self, user_id: int, player_data: dict, host_country: str, region_name: str, 
                 region_data: dict, options: list, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.host_country = host_country
        self.region_name = region_name
        self.region_data = region_data
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите актив для закрытия...", options=options)
        select.callback = self.on_asset_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_actions
        self.add_item(back_btn)
    
    async def on_asset_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        asset_type = interaction.data["values"][0]
        country_name = self.player_data["state"]["statename"]
        
        count = 0
        if asset_type in self.region_data:
            asset = self.region_data[asset_type]
            if isinstance(asset, dict) and "ownership" in asset:
                ownership = asset["ownership"]
                if country_name in ownership:
                    count = ownership[country_name]
        
        modal = CloseAbroadAssetQuantityModal(self.user_id, self.player_data, self.host_country,
                                              self.region_name, self.region_data, asset_type, count, self)
        await interaction.response.send_modal(modal)
    
    async def back_to_actions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.parent_view.parent_view.show_econ_regions_in_country(interaction, self.host_country)


class CloseAbroadAssetQuantityModal(Modal, title="Закрытие зарубежного актива"):
    def __init__(self, user_id: int, player_data: dict, host_country: str, region_name: str, 
                 region_data: dict, asset_type: str, max_count: int, parent_view: View):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.host_country = host_country
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.max_count = max_count
        self.parent_view = parent_view
        
        value_per_unit = ASSET_BASE_PRICES_USD.get(asset_type, 200_000_000)
        refund_per_unit = value_per_unit * 0.3
        
        self.quantity = TextInput(
            label=f"Количество для закрытия (макс: {max_count})",
            placeholder=f"Возврат: ${format_billion(refund_per_unit)} за шт.",
            min_length=1, max_length=4, required=True
        )
        self.add_item(self.quantity)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantity.value)
            if qty < 1 or qty > self.max_count:
                await interaction.response.send_message(f"Введите число от 1 до {self.max_count}!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Введите корректное число!", ephemeral=True)
            return
        
        country_name = self.player_data["state"]["statename"]
        value_per_unit = ASSET_BASE_PRICES_USD.get(self.asset_type, 200_000_000)
        total_value_usd = qty * value_per_unit
        total_refund_usd = qty * value_per_unit * 0.3
        grp_loss_usd = qty * value_per_unit * 0.2
        
        rate = EXCHANGE_RATES_2019.get(country_name, 1.0)
        currency_code = get_country_currency_code(country_name)
        local_refund = total_refund_usd * rate
        
        embed = discord.Embed(
            title="⚠️ Подтверждение закрытия зарубежных активов",
            description=f"Вы собираетесь закрыть **{qty}** из **{self.max_count}** активов типа **{INFRASTRUCTURE_COSTS.get(self.asset_type, {}).get('name', self.asset_type)}** в регионе **{self.region_name}** ({self.host_country}).",
            color=discord.Color.orange()
        )
        embed.add_field(name=f"{ECONOMIC_EMOJIS['budget']} Возврат в бюджет", value=f"{format_billion(local_refund)} {currency_code}", inline=True)
        embed.add_field(name=f"{ECONOMIC_EMOJIS['grp']} Потеря ВРП региона", value=f"{format_billion(grp_loss_usd * rate)} {currency_code}", inline=True)
        embed.add_field(name=f"{ACTION_EMOJIS['abroad']} Стоимость активов", value=f"${format_billion(total_value_usd)}", inline=True)
        embed.set_footer(text="Это действие нельзя отменить!")
        
        view = ConfirmCloseAbroadAssetView(
            self.user_id, self.player_data, self.host_country, self.region_name,
            self.region_data, self.asset_type, qty, total_refund_usd, grp_loss_usd, self
        )
        await interaction.response.edit_message(embed=embed, view=view)


class ConfirmCloseAbroadAssetView(View):
    def __init__(self, user_id: int, player_data: dict, host_country: str, region_name: str,
                 region_data: dict, asset_type: str, quantity: int, refund_usd: float, 
                 grp_loss_usd: float, parent_modal):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
        self.host_country = host_country
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.quantity = quantity
        self.refund_usd = refund_usd
        self.grp_loss_usd = grp_loss_usd
        self.parent_modal = parent_modal
    
    @discord.ui.button(label="Да, закрыть", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        country_name = self.player_data["state"]["statename"]
        rate = EXCHANGE_RATES_2019.get(country_name, 1.0)
        local_refund = self.refund_usd * rate
        
        infra_data = load_infrastructure()
        for country_id, country_data in infra_data.get("infrastructure", {}).items():
            if country_data.get("country") == self.host_country:
                if "economic_regions" in country_data:
                    for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                        if self.region_name in econ_region_data.get("regions", {}):
                            region_data = econ_region_data["regions"][self.region_name]
                            if self.asset_type in region_data:
                                asset = region_data[self.asset_type]
                                if isinstance(asset, dict) and "ownership" in asset:
                                    ownership = asset["ownership"]
                                    if country_name in ownership:
                                        ownership[country_name] = max(0, ownership[country_name] - self.quantity)
                                        if ownership[country_name] == 0:
                                            del ownership[country_name]
                                        asset["total"] = sum(ownership.values())
                            
                            current_grp = get_region_grp(region_data)
                            set_region_grp(region_data, current_grp - self.grp_loss_usd)
                            
                            econ_region_data["regions"][self.region_name] = region_data
                            break
                break
        save_infrastructure(infra_data)
        
        add_to_budget(self.player_data["economy"], local_refund)
        
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == country_name:
                data["economy"] = self.player_data["economy"]
                break
        save_states(states)
        
        asset_name = INFRASTRUCTURE_COSTS.get(self.asset_type, {}).get("name", self.asset_type)
        emoji = ASSET_EMOJIS.get(self.asset_type, "")
        currency_code = get_country_currency_code(country_name)
        
        embed = discord.Embed(
            title="Зарубежные активы закрыты",
            description=f"Закрыто {self.quantity} {emoji} {asset_name} в регионе {self.region_name} ({self.host_country})." if emoji else f"Закрыто {self.quantity} {asset_name} в регионе {self.region_name} ({self.host_country}).",
            color=discord.Color.orange()
        )
        embed.add_field(name=f"{ECONOMIC_EMOJIS['budget']} Возврат в бюджет", value=f"{format_billion(local_refund)} {currency_code}", inline=True)
        embed.add_field(name=f"{ECONOMIC_EMOJIS['grp']} Потеря ВРП", value=f"{format_billion(self.grp_loss_usd * rate)} {currency_code}", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        embed = discord.Embed(title="Действие отменено", color=DARK_THEME_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ИНОСТРАННЫЕ АКТИВЫ У НАС ====================

class ForeignOwnerSelectView(View):
    def __init__(self, user_id: int, player_data: dict, owners: list, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.owners = owners
        self.parent_view = parent_view
        
        options = []
        for owner in owners[:25]:
            flag = get_country_flag(owner)
            label = f"{flag} {owner}" if flag else owner
            options.append(discord.SelectOption(label=label[:100], value=owner))
        
        if options:
            select = Select(placeholder="Выберите страну-владельца...", options=options)
            select.callback = self.on_owner_select
            self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_categories
        self.add_item(back_btn)
    
    async def on_owner_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        owner_country = interaction.data["values"][0]
        await self.show_econ_regions_for_owner(interaction, owner_country)
    
    async def show_econ_regions_for_owner(self, interaction: discord.Interaction, owner_country: str):
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        owner_flag = get_country_flag(owner_country)
        
        infra_data = load_infrastructure()
        econ_regions_with_assets = {}
        total_country_assets = 0
        
        for country_id, country_data in infra_data.get("infrastructure", {}).items():
            if country_data.get("country") != country_name:
                continue
            
            if "economic_regions" in country_data:
                for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                    total_assets = 0
                    frozen_assets = 0
                    regions_count = 0
                    
                    if "regions" in econ_region_data:
                        for region_name, region_data in econ_region_data["regions"].items():
                            region_assets = 0
                            region_frozen = 0
                            for asset_type in CIVILIAN_ASSET_FIELDS:
                                if asset_type in region_data:
                                    asset = region_data[asset_type]
                                    if isinstance(asset, dict) and "ownership" in asset:
                                        ownership = asset["ownership"]
                                        if owner_country in ownership:
                                            qty = ownership[owner_country]
                                            region_assets += qty
                                            if is_asset_frozen(country_name, region_name, asset_type, owner_country):
                                                region_frozen += qty
                            
                            if region_assets > 0:
                                total_assets += region_assets
                                frozen_assets += region_frozen
                                regions_count += 1
                    
                    if total_assets > 0:
                        econ_regions_with_assets[econ_region_name] = {
                            "total_assets": total_assets,
                            "frozen_assets": frozen_assets,
                            "regions_count": regions_count,
                            "regions_data": econ_region_data.get("regions", {})
                        }
                        total_country_assets += total_assets
            break
        
        embed = discord.Embed(
            title=f"{flag} Активы {owner_flag} {owner_country} в нашей стране" if flag and owner_flag else f"Активы {owner_country} в нашей стране",
            description=f"Всего районов: {len(econ_regions_with_assets)} | Активов: {total_country_assets}",
            color=DARK_THEME_COLOR
        )
        
        if econ_regions_with_assets:
            for econ_region, data in sorted(econ_regions_with_assets.items(), key=lambda x: x[1]['total_assets'], reverse=True)[:10]:
                status = f" ({ACTION_EMOJIS['freeze']} заморожено: {data['frozen_assets']})" if data['frozen_assets'] > 0 else ""
                embed.add_field(name=econ_region, value=f"Регионов: {data['regions_count']}\nАктивов: {data['total_assets']}{status}", inline=True)
        
        view = ForeignEconRegionSelectView(self.user_id, self.player_data, owner_country, econ_regions_with_assets, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_categories(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.show_owners_for_foreign(interaction)


class ForeignEconRegionSelectView(View):
    def __init__(self, user_id: int, player_data: dict, owner_country: str, econ_regions_with_assets: dict, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.owner_country = owner_country
        self.econ_regions_with_assets = econ_regions_with_assets
        self.parent_view = parent_view
        
        options = []
        for econ_region, data in econ_regions_with_assets.items():
            options.append(discord.SelectOption(
                label=econ_region[:100], value=econ_region,
                description=f"{data['regions_count']} регионов, {data['total_assets']} активов"
            ))
        
        if options:
            select = Select(placeholder="Выберите экономический район...", options=options[:25])
            select.callback = self.on_econ_region_select
            self.add_item(select)
        
        back_btn = Button(label="Назад к владельцам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_owners
        self.add_item(back_btn)
    
    async def on_econ_region_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = interaction.data["values"][0]
        data = self.econ_regions_with_assets[econ_region]
        
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        owner_flag = get_country_flag(self.owner_country)
        
        embed = discord.Embed(
            title=f"{flag} Активы {owner_flag} {self.owner_country} в районе {econ_region}" if flag and owner_flag else f"Активы {self.owner_country} в районе {econ_region}",
            description=f"Регионов с активами: {data['regions_count']} | Всего активов: {data['total_assets']}",
            color=DARK_THEME_COLOR
        )
        
        regions_list = []
        for region_name, region_data in data['regions_data'].items():
            region_assets = 0
            region_frozen = 0
            for asset_type in CIVILIAN_ASSET_FIELDS:
                if asset_type in region_data:
                    asset = region_data[asset_type]
                    if isinstance(asset, dict) and "ownership" in asset:
                        ownership = asset["ownership"]
                        if self.owner_country in ownership:
                            qty = ownership[self.owner_country]
                            region_assets += qty
                            if is_asset_frozen(country_name, region_name, asset_type, self.owner_country):
                                region_frozen += qty
            
            if region_assets > 0:
                regions_list.append((region_name, region_assets, region_frozen, region_data))
        
        regions_list.sort(key=lambda x: x[1], reverse=True)
        
        for region, count, frozen, _ in regions_list[:15]:
            status = f" ({ACTION_EMOJIS['freeze']} заморожено: {frozen})" if frozen > 0 else ""
            embed.add_field(name=region, value=f"Активов: {count}{status}", inline=True)
        
        if len(regions_list) > 15:
            embed.set_footer(text=f"Показано 15 из {len(regions_list)} регионов. Выберите регион из списка ниже.")
        
        view = ForeignRegionSelectView(self.user_id, self.player_data, self.owner_country, econ_region, regions_list, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_owners(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.show_owners_for_foreign(interaction)


class ForeignRegionSelectView(View):
    def __init__(self, user_id: int, player_data: dict, owner_country: str, econ_region: str, regions_list: list, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.owner_country = owner_country
        self.econ_region = econ_region
        self.regions_list = regions_list
        self.parent_view = parent_view
        
        options = []
        for region, count, frozen, _ in regions_list[:25]:
            label = region[:100]
            desc = f"Активов: {count}" + (f" (заморожено: {frozen})" if frozen > 0 else "")
            options.append(discord.SelectOption(label=label, value=region, description=desc[:100]))
        
        if options:
            select = Select(placeholder="Выберите регион...", options=options)
            select.callback = self.on_region_select
            self.add_item(select)
        
        back_btn = Button(label="Назад к районам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_econ_regions
        self.add_item(back_btn)
    
    async def on_region_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        region_name = interaction.data["values"][0]
        
        region_data = None
        for r_name, _, _, r_data in self.regions_list:
            if r_name == region_name:
                region_data = r_data
                break
        
        if not region_data:
            await interaction.response.send_message("Регион не найден!", ephemeral=True)
            return
        
        country_name = self.player_data["state"]["statename"]
        flag = get_country_flag(country_name)
        owner_flag = get_country_flag(self.owner_country)
        
        embed = discord.Embed(
            title=f"{flag} Активы {owner_flag} {self.owner_country} в регионе {region_name}" if flag and owner_flag else f"Активы {self.owner_country} в регионе {region_name}",
            description=f"Экономический район: {self.econ_region}",
            color=DARK_THEME_COLOR
        )
        
        detail_embed = get_region_detailed_info(region_data, country_name)
        for field in detail_embed.fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        
        assets_by_type = {}
        for asset_type in CIVILIAN_ASSET_FIELDS:
            if asset_type in region_data:
                asset = region_data[asset_type]
                if isinstance(asset, dict) and "ownership" in asset:
                    ownership = asset["ownership"]
                    if self.owner_country in ownership and ownership[self.owner_country] > 0:
                        count = ownership[self.owner_country]
                        is_frozen = is_asset_frozen(country_name, region_name, asset_type, self.owner_country)
                        assets_by_type[asset_type] = {
                            "count": count,
                            "frozen": is_frozen,
                            "name": INFRASTRUCTURE_COSTS.get(asset_type, {}).get("name", asset_type),
                            "emoji": ASSET_EMOJIS.get(asset_type, ""),
                            "value_per_unit": ASSET_BASE_PRICES_USD.get(asset_type, 200_000_000)
                        }
        
        assets_text = ""
        total_assets = 0
        frozen_assets = 0
        total_value_usd = 0
        
        for asset_type, data in assets_by_type.items():
            count = data["count"]
            value = count * data["value_per_unit"]
            status = f" [{ACTION_EMOJIS['freeze']} ЗАМОРОЖЕН]" if data["frozen"] else ""
            assets_text += f"{data['emoji']} {data['name']}: {count}{status} (${format_billion(value)})\n" if data['emoji'] else f"• {data['name']}: {count}{status} (${format_billion(value)})\n"
            total_assets += count
            total_value_usd += value
            if data["frozen"]:
                frozen_assets += count
        
        if assets_text:
            embed.add_field(name=f"{ACTION_EMOJIS['foreign']} Иностранные активы", value=assets_text, inline=False)
        else:
            embed.add_field(name=f"{ACTION_EMOJIS['foreign']} Иностранные активы", value="Нет активов", inline=False)
        
        embed.set_footer(text=f"Всего активов: {total_assets} ({ACTION_EMOJIS['freeze']} заморожено: {frozen_assets}) | Стоимость: ${format_billion(total_value_usd)}" if frozen_assets > 0 else f"Всего активов: {total_assets} | Стоимость: ${format_billion(total_value_usd)}")
        
        view = ForeignRegionActionView(self.user_id, self.player_data, self.owner_country, region_name, region_data, assets_by_type, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_econ_regions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.show_econ_regions_for_owner(interaction, self.owner_country)


class ForeignRegionActionView(View):
    def __init__(self, user_id: int, player_data: dict, owner_country: str, region_name: str, 
                 region_data: dict, assets_by_type: dict, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.owner_country = owner_country
        self.region_name = region_name
        self.region_data = region_data
        self.assets_by_type = assets_by_type
        self.parent_view = parent_view
        
        has_frozen = any(data["frozen"] for data in assets_by_type.values())
        has_unfrozen = any(not data["frozen"] for data in assets_by_type.values())
        
        options = []
        if has_unfrozen:
            options.append(discord.SelectOption(label="Заморозить активы", value="freeze", description="Выбрать активы для заморозки"))
        if has_frozen:
            options.append(discord.SelectOption(label="Разморозить активы", value="unfreeze", description="Выбрать активы для разморозки"))
        options.extend([
            discord.SelectOption(label="Национализировать", value="nationalize", description="Выбрать активы для национализации"),
            discord.SelectOption(label="Уничтожить активы", value="destroy", description="Выбрать активы для уничтожения"),
        ])
        
        select = Select(placeholder="Выберите действие...", options=options)
        select.callback = self.on_action_select
        self.add_item(select)
        
        back_btn = Button(label="Назад к регионам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_regions
        self.add_item(back_btn)
    
    async def on_action_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        action = interaction.data["values"][0]
        
        options = []
        for asset_type, data in self.assets_by_type.items():
            if action == "freeze" and data["frozen"]:
                continue
            if action == "unfreeze" and not data["frozen"]:
                continue
            
            options.append(discord.SelectOption(
                label=data["name"][:100], value=asset_type,
                description=f"Доступно: {data['count']} шт. ({'заморожено' if data['frozen'] else 'активно'})"
            ))
        
        if not options:
            await interaction.response.send_message(f"Нет подходящих активов для действия!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Выберите тип актива",
            description=f"Действие: **{action}**",
            color=DARK_THEME_COLOR
        )
        
        view = ForeignAssetTypeSelectView(self.user_id, self.player_data, self.owner_country, 
                                          self.region_name, self.region_data, 
                                          self.assets_by_type, action, options, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_regions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.parent_view.parent_view.show_econ_regions_for_owner(interaction, self.owner_country)


class ForeignAssetTypeSelectView(View):
    def __init__(self, user_id: int, player_data: dict, owner_country: str, region_name: str,
                 region_data: dict, assets_by_type: dict, action: str, options: list, parent_view: View):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.owner_country = owner_country
        self.region_name = region_name
        self.region_data = region_data
        self.assets_by_type = assets_by_type
        self.action = action
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите тип актива...", options=options)
        select.callback = self.on_asset_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_to_actions
        self.add_item(back_btn)
    
    async def on_asset_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        asset_type = interaction.data["values"][0]
        data = self.assets_by_type[asset_type]
        max_count = data["count"]
        
        if self.action in ["freeze", "unfreeze"]:
            embed = discord.Embed(
                title=f"Подтверждение {self.action}",
                description=f"Вы собираетесь **{self.action}** все активы типа **{data['name']}** ({max_count} шт.) в регионе **{self.region_name}**.",
                color=discord.Color.blue() if self.action == "freeze" else discord.Color.green()
            )
            
            view = ConfirmForeignAssetActionView(
                self.user_id, self.player_data, self.owner_country, self.region_name,
                self.region_data, asset_type, max_count, self.action, None, data, self
            )
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            modal = ForeignAssetQuantityModal(
                self.user_id, self.player_data, self.owner_country, self.region_name,
                self.region_data, asset_type, max_count, self.action, data, self
            )
            await interaction.response.send_modal(modal)
    
    async def back_to_actions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        view = ForeignRegionActionView(self.user_id, self.player_data, self.owner_country, 
                                       self.region_name, self.region_data, 
                                       self.assets_by_type, self.parent_view.parent_view)
        embed = discord.Embed(
            title=f"{ACTION_EMOJIS['foreign']} Действия с активами {self.owner_country}",
            description=f"Регион: **{self.region_name}**\nВыберите действие",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=view)


class ForeignAssetQuantityModal(Modal, title="Выбор количества"):
    def __init__(self, user_id: int, player_data: dict, owner_country: str, region_name: str,
                 region_data: dict, asset_type: str, max_count: int, action: str, 
                 asset_data: dict, parent_view: View):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.owner_country = owner_country
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.max_count = max_count
        self.action = action
        self.asset_data = asset_data
        self.parent_view = parent_view
        
        action_names = {"nationalize": "национализации", "destroy": "уничтожения"}
        
        self.quantity = TextInput(
            label=f"Количество для {action_names.get(action, action)} (макс: {max_count})",
            placeholder=f"Введите число от 1 до {max_count}",
            min_length=1, max_length=4, required=True
        )
        self.add_item(self.quantity)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantity.value)
            if qty < 1 or qty > self.max_count:
                await interaction.response.send_message(f"Введите число от 1 до {self.max_count}!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Введите корректное число!", ephemeral=True)
            return
        
        country_name = self.player_data["state"]["statename"]
        rate = EXCHANGE_RATES_2019.get(country_name, 1.0)
        currency_code = get_country_currency_code(country_name)
        
        value_per_unit = self.asset_data["value_per_unit"]
        total_value_usd = qty * value_per_unit
        
        if self.action == "nationalize":
            stability_cost = min(2.0, qty * 0.05)
            money_cost_usd = total_value_usd * 0.3
            money_cost_local = money_cost_usd * rate
            pp_cost = min(10, int(qty * 0.5))
            
            embed = discord.Embed(
                title=f"{ACTION_EMOJIS['nationalize']} Подтверждение национализации",
                description=f"Вы собираетесь национализировать **{qty}** из **{self.max_count}** активов типа **{self.asset_data['name']}** компании **{self.owner_country}** в регионе **{self.region_name}**.",
                color=discord.Color.gold()
            )
            embed.add_field(name=f"{ECONOMIC_EMOJIS['budget']} Стоимость активов", value=f"${format_billion(total_value_usd)} ({format_billion(total_value_usd * rate)} {currency_code})", inline=True)
            embed.add_field(name=f"{ECONOMIC_EMOJIS['investments']} Затраты на национализацию", value=f"{format_billion(money_cost_local)} {currency_code}", inline=True)
            embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['stability']} Потеря стабильности", value=f"-{stability_cost:.2f}%", inline=True)
            embed.add_field(name=f"{ACTION_EMOJIS['pp']} Затраты ПВ", value=f"-{pp_cost:.0f}", inline=True)
            embed.set_footer(text="Это действие нельзя отменить!")
            
            costs = {"stability_cost": stability_cost, "money_cost": money_cost_local, "pp_cost": pp_cost, "total_value_usd": total_value_usd}
            
        elif self.action == "destroy":
            grp_loss_usd = total_value_usd * 0.5
            stability_loss = 0.5
            happiness_loss = 1.0
            
            embed = discord.Embed(
                title=f"{ACTION_EMOJIS['destroy']} Подтверждение уничтожения",
                description=f"Вы собираетесь уничтожить **{qty}** из **{self.max_count}** активов типа **{self.asset_data['name']}** компании **{self.owner_country}** в регионе **{self.region_name}**.",
                color=discord.Color.red()
            )
            embed.add_field(name=f"{ECONOMIC_EMOJIS['budget']} Стоимость активов", value=f"${format_billion(total_value_usd)}", inline=True)
            embed.add_field(name=f"{ECONOMIC_EMOJIS['grp']} Потеря ВРП региона", value=f"${format_billion(grp_loss_usd)}", inline=True)
            embed.add_field(name="⚠️ Последствия", value=f"Стабильность -{stability_loss}%\nСчастье -{happiness_loss}%\nУхудшение отношений с {self.owner_country}", inline=False)
            embed.set_footer(text="Это действие нельзя отменить!")
            
            costs = {"grp_loss_usd": grp_loss_usd, "stability_loss": stability_loss, "happiness_loss": happiness_loss, "total_value_usd": total_value_usd}
        
        view = ConfirmForeignAssetActionView(
            self.user_id, self.player_data, self.owner_country, self.region_name,
            self.region_data, self.asset_type, qty, self.action, 
            costs, self.asset_data, self.parent_view
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class ConfirmForeignAssetActionView(View):
    def __init__(self, user_id: int, player_data: dict, owner_country: str, region_name: str,
                 region_data: dict, asset_type: str, quantity: int, action: str, 
                 costs: dict, asset_data: dict, parent_view: View):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
        self.owner_country = owner_country
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.quantity = quantity
        self.action = action
        self.costs = costs
        self.asset_data = asset_data
        self.parent_view = parent_view
        
        self.confirm_btn = Button(label="Подтвердить", style=discord.ButtonStyle.danger if action == "destroy" else discord.ButtonStyle.success)
        self.confirm_btn.callback = self.confirm_callback
        self.add_item(self.confirm_btn)
        
        self.cancel_btn = Button(label="Отмена", style=discord.ButtonStyle.secondary)
        self.cancel_btn.callback = self.cancel_callback
        self.add_item(self.cancel_btn)
    
    async def confirm_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        country_name = self.player_data["state"]["statename"]
        
        if self.action == "freeze":
            set_asset_frozen(country_name, self.region_name, self.asset_type, self.owner_country, True)
            embed = discord.Embed(
                title=f"{ACTION_EMOJIS['freeze']} Активы заморожены",
                description=f"Заморожено {self.quantity} активов типа {self.asset_data['name']} компании {self.owner_country} в регионе {self.region_name}.",
                color=discord.Color.blue()
            )
            
        elif self.action == "unfreeze":
            set_asset_frozen(country_name, self.region_name, self.asset_type, self.owner_country, False)
            embed = discord.Embed(
                title=f"{ACTION_EMOJIS['unfreeze']} Активы разморожены",
                description=f"Разморожено {self.quantity} активов типа {self.asset_data['name']} компании {self.owner_country} в регионе {self.region_name}.",
                color=discord.Color.green()
            )
            
        elif self.action == "nationalize":
            current_budget = get_budget(self.player_data["economy"])
            current_stability = self.player_data["state"]["stability"]
            current_pp = self.player_data["politics"].get("political_power", 100)
            
            if current_budget < self.costs["money_cost"]:
                await interaction.response.send_message("Недостаточно средств!", ephemeral=True)
                return
            if current_stability < self.costs["stability_cost"]:
                await interaction.response.send_message("Недостаточно стабильности!", ephemeral=True)
                return
            if current_pp < self.costs["pp_cost"]:
                await interaction.response.send_message("Недостаточно политической власти!", ephemeral=True)
                return
            
            subtract_from_budget(self.player_data["economy"], self.costs["money_cost"])
            self.player_data["state"]["stability"] = max(0, current_stability - self.costs["stability_cost"])
            self.player_data["politics"]["political_power"] = max(0, current_pp - self.costs["pp_cost"])
            
            infra_data = load_infrastructure()
            for country_id, country_data in infra_data.get("infrastructure", {}).items():
                if country_data.get("country") == country_name:
                    if "economic_regions" in country_data:
                        for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                            if self.region_name in econ_region_data.get("regions", {}):
                                region_data = econ_region_data["regions"][self.region_name]
                                if self.asset_type in region_data:
                                    asset = region_data[self.asset_type]
                                    if isinstance(asset, dict) and "ownership" in asset:
                                        ownership = asset["ownership"]
                                        if self.owner_country in ownership:
                                            current_qty = ownership[self.owner_country]
                                            qty_to_take = min(self.quantity, current_qty)
                                            ownership[self.owner_country] -= qty_to_take
                                            if ownership[self.owner_country] == 0:
                                                del ownership[self.owner_country]
                                            ownership[country_name] = ownership.get(country_name, 0) + qty_to_take
                                            asset["total"] = sum(ownership.values())
                                break
                break
            save_infrastructure(infra_data)
            
            states = load_states()
            for data in states["players"].values():
                if data.get("state", {}).get("statename") == country_name:
                    data.update(self.player_data)
                    break
            save_states(states)
            
            currency_code = get_country_currency_code(country_name)
            embed = discord.Embed(
                title="Активы национализированы",
                description=f"Национализировано {self.quantity} активов типа {self.asset_data['name']} компании {self.owner_country} в регионе {self.region_name}.",
                color=discord.Color.gold()
            )
            embed.add_field(name=f"{ECONOMIC_EMOJIS['budget']} Стоимость активов", value=f"${format_billion(self.costs['total_value_usd'])}", inline=True)
            embed.add_field(name=f"{ECONOMIC_EMOJIS['investments']} Затрачено", value=f"{format_billion(self.costs['money_cost'])} {currency_code}", inline=True)
            embed.add_field(name="📊 Последствия", value=f"Стабильность -{self.costs['stability_cost']:.2f}%\n{ACTION_EMOJIS['pp']} ПВ -{self.costs['pp_cost']:.0f}", inline=True)
            
        elif self.action == "destroy":
            infra_data = load_infrastructure()
            for country_id, country_data in infra_data.get("infrastructure", {}).items():
                if country_data.get("country") == country_name:
                    if "economic_regions" in country_data:
                        for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                            if self.region_name in econ_region_data.get("regions", {}):
                                region_data = econ_region_data["regions"][self.region_name]
                                
                                current_grp = get_region_grp(region_data)
                                set_region_grp(region_data, current_grp - self.costs["grp_loss_usd"])
                                
                                if self.asset_type in region_data:
                                    asset = region_data[self.asset_type]
                                    if isinstance(asset, dict) and "ownership" in asset:
                                        ownership = asset["ownership"]
                                        if self.owner_country in ownership:
                                            current_qty = ownership[self.owner_country]
                                            qty_to_destroy = min(self.quantity, current_qty)
                                            ownership[self.owner_country] -= qty_to_destroy
                                            if ownership[self.owner_country] == 0:
                                                del ownership[self.owner_country]
                                            asset["total"] = sum(ownership.values())
                                break
                break
            save_infrastructure(infra_data)
            
            self.player_data["state"]["stability"] = max(0, self.player_data["state"]["stability"] - self.costs["stability_loss"])
            self.player_data["state"]["happiness"] = max(0, self.player_data["state"]["happiness"] - self.costs["happiness_loss"])
            
            states = load_states()
            for data in states["players"].values():
                if data.get("state", {}).get("statename") == country_name:
                    data.update(self.player_data)
                    break
            save_states(states)
            
            embed = discord.Embed(
                title="Активы уничтожены",
                description=f"Уничтожено {self.quantity} активов типа {self.asset_data['name']} компании {self.owner_country} в регионе {self.region_name}.",
                color=discord.Color.red()
            )
            embed.add_field(name=f"{ECONOMIC_EMOJIS['grp']} Потеря ВРП", value=f"${format_billion(self.costs['grp_loss_usd'])}", inline=True)
            embed.add_field(name="⚠️ Влияние на страну", value=f"Стабильность -{self.costs['stability_loss']}%\nСчастье -{self.costs['happiness_loss']}%", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def cancel_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        embed = discord.Embed(title="Действие отменено", color=DARK_THEME_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_assets_menu',
    'get_country_flag',
    'CIVILIAN_ASSET_FIELDS',
    'ASSET_BASE_PRICES_USD',
    'ASSET_EMOJIS',
    'RELIGION_EMOJIS',
    'WORKERS_PER_ASSET',
    'WORKER_SALARY_USD'
]

# ==================== АДМИНИСТРАТИВНЫЕ КОМАНДЫ ====================
class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.economy_calc = EconomyCalculator()

    def _calculate_foreign_assets_stats(self, infra_data: dict) -> dict:
        """Рассчитывает статистику по иностранным активам"""
        stats = {
            "by_owner": {},
            "by_host": {}
        }
        
        asset_base_prices = {
            "military_factories": 300_000_000,
            "civilian_factories": 200_000_000,
            "office_centers": 150_000_000,
            "oil_depots": 150_000_000,
            "refineries": 400_000_000,
            "shipyards": 500_000_000,
            "thermal_power": 350_000_000,
            "hydro_power": 600_000_000,
            "solar_power": 180_000_000,
            "nuclear_power": 1_500_000_000,
            "wind_power": 220_000_000,
            "internet_infrastructure": 100_000_000,
        }
        
        for country_id, country_data in infra_data.get("infrastructure", {}).items():
            host_country = country_data.get("country")
            if not host_country:
                continue
            
            regions = {}
            if "economic_regions" in country_data:
                for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                    if "regions" in econ_region_data:
                        regions.update(econ_region_data["regions"])
            elif "regions" in country_data:
                regions = country_data["regions"]
            
            for region_name, region_data in regions.items():
                for asset_type in ASSET_FIELDS:
                    if asset_type not in region_data:
                        continue
                    
                    asset = region_data[asset_type]
                    
                    if isinstance(asset, dict) and "ownership" in asset:
                        for owner_country, quantity in asset["ownership"].items():
                            if quantity <= 0:
                                continue
                            
                            asset_info = {
                                "region": region_name,
                                "host_country": host_country,
                                "owner_country": owner_country,
                                "asset_type": asset_type,
                                "quantity": quantity,
                                "base_price_usd": asset_base_prices.get(asset_type, 200_000_000)
                            }
                            
                            if owner_country != host_country:
                                if owner_country not in stats["by_owner"]:
                                    stats["by_owner"][owner_country] = []
                                stats["by_owner"][owner_country].append(asset_info)
                                
                                if host_country not in stats["by_host"]:
                                    stats["by_host"][host_country] = []
                                stats["by_host"][host_country].append(asset_info)
        
        return stats

    @commands.command(name='назначить')
    @commands.has_permissions(administrator=True)
    async def assign_state(self, ctx, member: discord.Member, state_id: str):
        """Назначить игроку государство по ID"""
        states = load_states()
        
        if state_id not in states["players"]:
            await ctx.send(f"Государство с ID {state_id} не найдено!")
            return
        
        for user_id, data in states["players"].items():
            if user_id != state_id and data.get("assigned_to") == str(member.id):
                await ctx.send(f"Игрок {member.mention} уже имеет государство!")
                return
        
        states["players"][state_id]["assigned_to"] = str(member.id)
        states["players"][state_id]["assigned_at"] = str(datetime.now())
        
        save_states(states)
        
        state_name = states["players"][state_id]["state"]["statename"]
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} назначил государство {state_name} игроку {member.name}")
        
        await ctx.send(f"Игрок {member.mention} назначен лидером государства {state_name}!")

    @commands.command(name='снять')
    @commands.has_permissions(administrator=True)
    async def unassign_state(self, ctx, member: discord.Member):
        """Снять игрока с управления государством"""
        states = load_states()
        
        found = False
        state_name = ""
        for state_id, data in states["players"].items():
            if data.get("assigned_to") == str(member.id):
                state_name = data["state"]["statename"]
                del data["assigned_to"]
                if "assigned_at" in data:
                    del data["assigned_at"]
                found = True
                break
        
        if not found:
            await ctx.send(f"У игрока {member.mention} нет назначенного государства!")
            return
        
        save_states(states)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} снял игрока {member.name} с управления государством {state_name}")
        
        await ctx.send(f"Игрок {member.mention} снят с управления государством!")

    @commands.command(name='список')
    @commands.has_permissions(administrator=True)
    async def list_states(self, ctx):
        """Показать список всех доступных государств"""
        states = load_states()
    
        embed = discord.Embed(
            title="Список государств",
            color=0x2b2d31
        )
    
        for state_id, data in states["players"].items():
            state_name = data["state"]["statename"]
            assigned = data.get("assigned_to")
        
            if assigned:
                try:
                    user = await self.bot.fetch_user(int(assigned))
                    status = f"Занято: {user.name}"
                except:
                    status = "Занято (пользователь не найден)"
            else:
                status = "Свободно"
        
            embed.add_field(
                name=f"{state_name} (ID: {state_id})",
                value=status,
                inline=False
            )
    
        await ctx.send(embed=embed)

    @commands.command(name='админ_пво')
    @commands.has_permissions(administrator=True)
    async def admin_pvo(self, ctx, member: discord.Member, pvo_type: str, operation: str, amount: int):
        """Изменить количество ПВО в арсенале игрока"""
        valid_types = ["long_range_air_defense", "short_range_air_defense", "zdprk", "zas", "radar_systems"]
        
        if pvo_type not in valid_types:
            await ctx.send(f"Неверный тип ПВО! Доступные: {', '.join(valid_types)}")
            return
        
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        if "army" not in player_data:
            player_data["army"] = {}
        if "ground" not in player_data["army"]:
            player_data["army"]["ground"] = {}
        
        current = player_data["army"]["ground"].get(pvo_type, 0)
        
        pvo_name = INFRASTRUCTURE_COSTS.get(pvo_type, {}).get("name", pvo_type)
        
        if operation == "add":
            new_value = current + amount
            player_data["army"]["ground"][pvo_type] = new_value
            result_text = f"увеличено на {format_number(amount)}"
        elif operation == "remove":
            if current < amount:
                await ctx.send(f"Недостаточно ПВО! Доступно: {format_number(current)}")
                return
            new_value = current - amount
            player_data["army"]["ground"][pvo_type] = new_value
            result_text = f"уменьшено на {format_number(amount)}"
        elif operation == "set":
            new_value = max(0, amount)
            player_data["army"]["ground"][pvo_type] = new_value
            result_text = f"установлено на {format_number(new_value)}"
        else:
            await ctx.send("Неверная операция! Используйте add/remove/set")
            return
        
        save_states(states)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} изменил ПВО {pvo_name} игрока {member.name}: {format_number(current)} -> {format_number(new_value)}")
        
        await ctx.send(f"ПВО {pvo_name} игрока {member.mention} {result_text}. Было: {format_number(current)}, стало: {format_number(new_value)}")

    @commands.command(name='стат')
    @commands.has_permissions(administrator=True)
    async def set_stat(self, ctx, member: discord.Member, path: str, value: str):
        """Изменить статистику игрока"""
        states = load_states()
        
        user_state = None
        for sid, data in states["players"].items():
            if data.get("assigned_to") == str(member.id):
                user_state = data
                break
        
        if not user_state:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        keys = path.split('.')
        
        try:
            if '.' in value:
                val = float(value)
            else:
                val = int(value)
        except ValueError:
            val = value
        
        current = user_state
        for key in keys[:-1]:
            if key not in current:
                await ctx.send(f"Неверный путь: {key} не найден!")
                return
            current = current[key]
        
        last_key = keys[-1]
        if last_key not in current:
            await ctx.send(f"Ключ {last_key} не найден!")
            return
        
        old_value = current[last_key]
        current[last_key] = val
        
        save_states(states)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} изменил статистику {member.name}:\n"
                             f"`{path}`: `{old_value}` -> `{val}`")
        
        await ctx.send(f"Статистика обновлена!")

    @commands.command(name='просмотр')
    @commands.has_permissions(administrator=True)
    async def view_state(self, ctx, member: discord.Member):
        """Просмотр полной статистики государства"""
        states = load_states()
        
        user_state = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                user_state = data
                break
        
        if not user_state:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        state_name = user_state["state"]["statename"]
        
        filename = f"state_{member.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(user_state, f, ensure_ascii=False, indent=4)
        
        await ctx.send(f"Статистика государства {state_name}:", file=discord.File(filename))
        os.remove(filename)

    @commands.command(name='год')
    @commands.has_permissions(administrator=True)
    async def year_update(self, ctx):
        """Провести годовой апдейт для всех государств"""
        states = load_states()
        infra_data = load_infrastructure()
        results = []
        
        # Собираем статистику по иностранным активам
        foreign_assets_stats = self._calculate_foreign_assets_stats(infra_data)
        
        for state_id, player_data in states["players"].items():
            if "assigned_to" not in player_data:
                continue
            
            if "expenses" not in player_data:
                player_data["expenses"] = {
                    "healthcare": 0,
                    "police": 0,
                    "social_security": 0,
                    "education": 0
                }
            
            migrate_player_resources(player_data)
            
            country_name = player_data["state"]["statename"]
            player_data = apply_infrastructure_bonuses(player_data, country_name)
            
            # Доходы от иностранных активов (в валюте страны размещения)
            foreign_profit_by_currency = {}
            foreign_assets_count = 0

            if country_name in foreign_assets_stats["by_owner"]:
                for asset_info in foreign_assets_stats["by_owner"][country_name]:
                    # Проверяем, не заморожен ли актив
                    if is_asset_frozen(asset_info["host_country"], asset_info["region"], 
                                      asset_info["asset_type"], country_name):
                        continue  # Замороженные активы не приносят прибыль
                    
                    asset_value_usd = asset_info["quantity"] * asset_info.get("base_price_usd", 200_000_000)
                    annual_profit_usd = asset_value_usd * 0.05
                    
                    host_country = asset_info["host_country"]
                    host_currency = CURRENCY_CODES.get(host_country, "USD")
                    
                    rate = EXCHANGE_RATES_2019.get(host_country, 1.0)
                    profit_in_host_currency = annual_profit_usd * rate
                    
                    if host_currency not in foreign_profit_by_currency:
                        foreign_profit_by_currency[host_currency] = 0
                    foreign_profit_by_currency[host_currency] += profit_in_host_currency
                    foreign_assets_count += 1

            total_foreign_profit_usd = 0
            for currency, amount in foreign_profit_by_currency.items():
                if currency not in player_data["economy"]["foreign_reserves"]:
                    player_data["economy"]["foreign_reserves"][currency] = 0
                player_data["economy"]["foreign_reserves"][currency] += amount
                
                # Конвертируем обратно в USD для статистики
                if currency == "USD":
                    total_foreign_profit_usd += amount
                else:
                    for c, rate in EXCHANGE_RATES_2019.items():
                        if CURRENCY_CODES.get(c) == currency:
                            total_foreign_profit_usd += amount / rate
                            break

            foreign_profit_usd = total_foreign_profit_usd

            # Налоги от иностранных активов в стране
            foreign_tax_revenue_usd = 0
            foreign_assets_hosted = 0
            
            if country_name in foreign_assets_stats["by_host"]:
                for asset_info in foreign_assets_stats["by_host"][country_name]:
                    asset_value_usd = asset_info["quantity"] * asset_info.get("base_price_usd", 200_000_000)
                    annual_profit = asset_value_usd * 0.05
                    tax_revenue = annual_profit * 0.15
                    foreign_tax_revenue_usd += tax_revenue
                    foreign_assets_hosted += 1
            
            if foreign_tax_revenue_usd > 0:
                rate = EXCHANGE_RATES_2019.get(country_name, 1.0)
                local_tax_revenue = foreign_tax_revenue_usd * rate
                add_to_budget(player_data["economy"], local_tax_revenue)
                player_data["tariff_revenue_usd"] = player_data.get("tariff_revenue_usd", 0) + foreign_tax_revenue_usd
            
            # Стандартный расчёт бюджета
            budget_result = self.economy_calc.calculate_annual_budget(player_data)
            
            set_budget(player_data["economy"], budget_result["new_budget"])
            
            if "debt_local" in player_data["economy"]:
                player_data["economy"]["debt_local"] = budget_result["new_debt"]
            else:
                player_data["economy"]["debt_usd"] = budget_result["new_debt"]
                player_data["economy"]["debt_local"] = budget_result["new_debt"]
            
            gdp_growth = self.economy_calc.calculate_gdp_growth(player_data)
            if "gdp_local" in player_data["economy"]:
                player_data["economy"]["gdp_local"] = int(player_data["economy"]["gdp_local"] * (1 + gdp_growth/100))
            elif "gdp_usd" in player_data["economy"]:
                player_data["economy"]["gdp_usd"] = int(player_data["economy"]["gdp_usd"] * (1 + gdp_growth/100))
                player_data["economy"]["gdp_local"] = player_data["economy"]["gdp_usd"]
            
            pop_growth = self.economy_calc.calculate_population_growth(player_data)
            player_data["state"]["population"] = max(1000, player_data["state"]["population"] + pop_growth)
            
            army_exp = self.economy_calc.calculate_army_experience(player_data)
            player_data["state"]["army_experience"] = int(army_exp)
            
            current_inflation = get_inflation(player_data["economy"])
            inflation_change = random.uniform(-0.5, 1.0)
            if "local_currency" in player_data["economy"]:
                player_data["economy"]["local_currency"]["inflation"] = max(0, min(30, current_inflation + inflation_change))
            else:
                player_data["economy"]["inflation"] = max(0, min(30, current_inflation + inflation_change))
            
            if "wage_local" in player_data["economy"]:
                wage_change = gdp_growth / 2
                player_data["economy"]["wage_local"] = int(player_data["economy"]["wage_local"] * (1 + wage_change/100))
            else:
                player_data["economy"]["wage"] = int(player_data["economy"].get("wage", 0) * (1 + gdp_growth/200))
            
            if get_gdp(player_data["economy"]) > 0:
                popularity_change = budget_result["deficit_percent"] / 10
            else:
                popularity_change = 0
            player_data["politics"]["popularity"] = max(0, min(100, 
                player_data["politics"]["popularity"] + popularity_change))
            
            happiness_change = 0
            if budget_result["expenses"]["healthcare"] > 0:
                happiness_change += 0.2
            if budget_result["expenses"]["education"] > 0:
                happiness_change += 0.2
            if budget_result["expenses"]["social_security"] > 0:
                happiness_change += 0.2
            
            player_data["state"]["happiness"] = min(100, player_data["state"]["happiness"] + happiness_change)
            
            tariff_revenue_usd = player_data.get("tariff_revenue_usd", 0)
            export_tariff_revenue_usd = player_data.get("export_tariff_revenue_usd", 0)
            
            player_data["tariff_revenue_usd"] = 0
            player_data["export_tariff_revenue_usd"] = 0
            player_data["tariff_revenue"] = 0
            player_data["export_tariff_revenue"] = 0
            
            results.append({
                "state_id": state_id,
                "state_name": player_data["state"]["statename"],
                "deficit": budget_result["deficit"],
                "deficit_percent": budget_result["deficit_percent"],
                "gdp_growth": gdp_growth,
                "new_population": player_data["state"]["population"],
                "total_expenses": budget_result["expenses"]["total"],
                "old_budget": budget_result["old_budget"],
                "new_budget": budget_result["new_budget"],
                "new_debt": budget_result["new_debt"],
                "tariff_revenue_usd": tariff_revenue_usd,
                "export_tariff_revenue_usd": export_tariff_revenue_usd,
                "foreign_profit_usd": foreign_profit_usd,
                "foreign_assets_count": foreign_assets_count,
                "foreign_tax_revenue_usd": foreign_tax_revenue_usd,
                "foreign_assets_hosted": foreign_assets_hosted
            })
        
        save_states(states)
        
        embed = discord.Embed(
            title="Годовой апдейт завершен",
            description=f"Обработано государств: {len(results)}",
            color=0x2b2d31
        )
        
        for result in results[:10]:
            deficit_emoji = "✅" if result["deficit"] > 0 else "⚠️" if result["deficit"] < 0 else "⚖️"
            growth_emoji = "📈" if result["gdp_growth"] > 2 else "📊" if result["gdp_growth"] > 0 else "📉"
            
            budget_change = result["new_budget"] - result["old_budget"]
            budget_emoji = "📈" if budget_change > 0 else "📉" if budget_change < 0 else "⚖️"
            
            deficit_text = f"{deficit_emoji} Баланс: {format_billion(abs(result['deficit']))} ({result['deficit_percent']:.1f}% ВВП)"
            
            tariff_text = f"Импортные пошлины: ${result['tariff_revenue_usd']:,.0f}" if result['tariff_revenue_usd'] > 0 else ""
            export_text = f"Экспортные пошлины: ${result['export_tariff_revenue_usd']:,.0f}" if result['export_tariff_revenue_usd'] > 0 else ""
            
            total_tariff = result['tariff_revenue_usd'] + result['export_tariff_revenue_usd']
            total_tariff_text = f"Всего таможенных сборов: ${total_tariff:,.0f}" if total_tariff > 0 else ""
            
            foreign_text = ""
            if result.get('foreign_profit_usd', 0) > 0:
                foreign_text += f"🌍 Прибыль от зарубежных активов: ${result['foreign_profit_usd']:,.0f} ({result['foreign_assets_count']} активов)\n"
            if result.get('foreign_tax_revenue_usd', 0) > 0:
                foreign_text += f"🏭 Налоги от иностранных активов: ${result['foreign_tax_revenue_usd']:,.0f} ({result['foreign_assets_hosted']} активов)\n"
            
            tariff_display = ""
            if tariff_text:
                tariff_display += f"{tariff_text}\n"
            if export_text:
                tariff_display += f"{export_text}\n"
            if total_tariff_text:
                tariff_display += f"{total_tariff_text}"
            
            value_text = f"{deficit_text}\n"
            value_text += f"{growth_emoji} Рост ВВП: {result['gdp_growth']:.1f}%\n"
            value_text += f"Население: {format_number(result['new_population'])} чел.\n"
            value_text += f"{budget_emoji} Бюджет: {format_billion(result['new_budget'])}\n"
            value_text += f"Долг: {format_billion(result['new_debt'])}"
            
            if foreign_text:
                value_text += f"\n{foreign_text}"
            
            if tariff_display:
                value_text += f"\n{tariff_display}"
            
            embed.add_field(
                name=f"{result['state_name']}",
                value=value_text,
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} провел годовой апдейт")

    @commands.command(name='инициализировать_население')
    @commands.has_permissions(administrator=True)
    async def init_population(self, ctx, member: discord.Member = None):
        """Принудительно инициализировать данные о населении для всех стран или конкретного игрока"""
        states = load_states()
        updated = 0
        
        if member:
            for state_id, player_data in states["players"].items():
                if player_data.get("assigned_to") == str(member.id):
                    from population import update_population
                    summary = update_population(player_data)
                    updated += 1
                    await ctx.send(f"✅ Данные населения для {player_data['state']['statename']} инициализированы!")
                    break
            else:
                await ctx.send(f"❌ У игрока {member.mention} нет государства!")
                return
        else:
            await ctx.send("🔄 Инициализация данных населения для всех стран...")
            
            for state_id, player_data in states["players"].items():
                if "assigned_to" in player_data:
                    from population import update_population
                    try:
                        summary = update_population(player_data)
                        updated += 1
                        print(f"   ✅ {player_data['state']['statename']}: доход ${summary['total_income']:,.0f}")
                    except Exception as e:
                        print(f"   ❌ Ошибка {player_data['state']['statename']}: {e}")
            
            save_states(states)
            await ctx.send(f"✅ Инициализировано {updated} государств!")
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} инициализировал данные населения для {updated} стран")

    # ==================== НОВЫЕ КОМАНДЫ ДЛЯ ПОЛИТИЧЕСКОЙ ВЛАСТИ ====================

    @commands.command(name='дать_власть')
    @commands.has_permissions(administrator=True)
    async def give_political_power(self, ctx, member: discord.Member, amount: int):
        """Выдать политическую власть игроку"""
        from political_power import get_player_state, add_political_power, save_player_state
        
        state_id, state_data = get_player_state(member.id)
        
        if not state_data:
            await ctx.send(f"❌ Игрок {member.mention} не управляет государством!")
            return
        
        old_value = state_data.get("politics", {}).get("political_power", 100)
        state_data, added = add_political_power(state_data, amount)
        save_player_state(member.id, state_data)
        
        embed = discord.Embed(
            title="⚡ ВЫДАЧА ПОЛИТИЧЕСКОЙ ВЛАСТИ",
            description=f"Игроку **{member.display_name}** выдано **+{amount}** политической власти",
            color=0x00FF00
        )
        embed.add_field(name="Было", value=f"```\n{old_value}\n```", inline=True)
        embed.add_field(name="Стало", value=f"```\n{old_value + amount}\n```", inline=True)
        embed.add_field(name="Государство", value=f"```\n{state_data['state']['statename']}\n```", inline=False)
        
        await ctx.send(embed=embed)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} выдал {amount} власти игроку {member.name}")

    @commands.command(name='установить_власть')
    @commands.has_permissions(administrator=True)
    async def set_political_power(self, ctx, member: discord.Member, amount: int):
        """Установить политическую власть игроку"""
        from political_power import get_player_state, set_political_power, save_player_state
        
        state_id, state_data = get_player_state(member.id)
        
        if not state_data:
            await ctx.send(f"❌ Игрок {member.mention} не управляет государством!")
            return
        
        old_value = state_data.get("politics", {}).get("political_power", 100)
        set_political_power(state_data, amount)
        save_player_state(member.id, state_data)
        
        embed = discord.Embed(
            title="⚡ УСТАНОВКА ПОЛИТИЧЕСКОЙ ВЛАСТИ",
            description=f"Игроку **{member.display_name}** установлено **{amount}** политической власти",
            color=0xFFAA00
        )
        embed.add_field(name="Было", value=f"```\n{old_value}\n```", inline=True)
        embed.add_field(name="Стало", value=f"```\n{amount}\n```", inline=True)
        embed.add_field(name="Государство", value=f"```\n{state_data['state']['statename']}\n```", inline=False)
        
        await ctx.send(embed=embed)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} установил {amount} власти игроку {member.name}")

    @commands.command(name='дать_влияние')
    @commands.has_permissions(administrator=True)
    async def give_influence(self, ctx, member: discord.Member, amount: int):
        """Выдать влияние игроку"""
        from political_power import get_player_state, get_influence, add_influence, save_player_state
        
        state_id, state_data = get_player_state(member.id)
        
        if not state_data:
            await ctx.send(f"❌ Игрок {member.mention} не управляет государством!")
            return
        
        old_value = get_influence(state_data)
        add_influence(state_data, amount)
        save_player_state(member.id, state_data)
        
        embed = discord.Embed(
            title="📡 ВЫДАЧА ВЛИЯНИЯ",
            description=f"Игроку **{member.display_name}** выдано **+{amount}** влияния",
            color=0x00AAFF
        )
        embed.add_field(name="Было", value=f"```\n{old_value:.1f}\n```", inline=True)
        embed.add_field(name="Стало", value=f"```\n{old_value + amount:.1f}\n```", inline=True)
        embed.add_field(name="Государство", value=f"```\n{state_data['state']['statename']}\n```", inline=False)
        
        await ctx.send(embed=embed)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} выдал {amount} влияния игроку {member.name}")

    @commands.command(name='сбросить_кулдаун')
    @commands.has_permissions(administrator=True)
    async def reset_cooldown(self, ctx, member: discord.Member, action_type: str = None):
        """Сбросить кулдаун действий игрока"""
        from political_power import load_political_actions, save_political_actions, get_player_state
        
        state_id, state_data = get_player_state(member.id)
        
        if not state_data:
            await ctx.send(f"❌ Игрок {member.mention} не управляет государством!")
            return
        
        actions_data = load_political_actions()
        
        if action_type:
            if action_type in actions_data["actions"].get(state_id, {}):
                del actions_data["actions"][state_id][action_type]
                await ctx.send(f"✅ Сброшен кулдаун для действия **{action_type}** у {member.mention}")
            else:
                await ctx.send(f"❌ Действие **{action_type}** не найдено в кулдаунах!")
                return
        else:
            if state_id in actions_data["actions"]:
                actions_data["actions"][state_id] = {}
                await ctx.send(f"✅ Сброшены **все** кулдауны у {member.mention}")
            else:
                await ctx.send(f"❌ У {member.mention} нет активных кулдаунов")
                return
        
        save_political_actions(actions_data)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} сбросил кулдауны игроку {member.name}")

    @commands.command(name='дать_всем_власть')
    @commands.has_permissions(administrator=True)
    async def give_all_power(self, ctx, amount: int):
        """Выдать политическую власть ВСЕМ игрокам"""
        from political_power import add_political_power, save_player_state
        from utils import load_states, save_states
        
        states = load_states()
        updated = 0
        results = []
        
        for state_id, state_data in states["players"].items():
            if "assigned_to" not in state_data:
                continue
            
            user_id = int(state_data["assigned_to"])
            old_value = state_data.get("politics", {}).get("political_power", 100)
            state_data, added = add_political_power(state_data, amount)
            save_player_state(user_id, state_data)
            updated += 1
            results.append(f"**{state_data['state']['statename']}**: {old_value} → {old_value + amount}")
        
        embed = discord.Embed(
            title="⚡ МАССОВАЯ ВЫДАЧА ПОЛИТИЧЕСКОЙ ВЛАСТИ",
            description=f"Выдано **+{amount}** власти всем {updated} игрокам",
            color=0x00FF00
        )
        
        if results:
            embed.add_field(name="Результаты", value="\n".join(results[:25]), inline=False)
        
        await ctx.send(embed=embed)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} выдал {amount} власти всем {updated} игрокам")

    @commands.command(name='стат_власти')
    async def power_stats(self, ctx, member: discord.Member = None):
        """Показать статистику политической власти игрока"""
        from political_power import get_player_state, get_political_power, get_influence, get_popularity_tier, MAX_INFLUENCE
        
        target = member or ctx.author
        state_id, state_data = get_player_state(target.id)
        
        if not state_data:
            await ctx.send(f"❌ Игрок {target.mention} не управляет государством!")
            return
        
        politics = state_data.get("politics", {})
        political_power = int(politics.get("political_power", 100))
        influence = get_influence(state_data)
        popularity = politics.get("popularity", 50)
        stability = state_data.get("stability", 50)
        
        tier = get_popularity_tier(popularity)
        
        embed = discord.Embed(
            title="📊 СТАТИСТИКА ПОЛИТИЧЕСКОЙ ВЛАСТИ",
            description=f"Игрок: **{target.display_name}**\nГосударство: **{state_data['state']['statename']}**",
            color=DARK_THEME_COLOR
        )
        embed.add_field(name="⚡ Политическая власть", value=f"```\n{political_power}\n```", inline=True)
        embed.add_field(name="📡 Влияние", value=f"```\n{influence:.1f} / {MAX_INFLUENCE}\n```", inline=True)
        embed.add_field(name="📈 Популярность", value=f"```\n{popularity:.1f}% [{tier['name']}]\n```", inline=True)
        embed.add_field(name="🛡️ Стабильность", value=f"```\n{stability:.1f}%\n```", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='сбросить_власть')
    @commands.has_permissions(administrator=True)
    async def reset_power(self, ctx, member: discord.Member = None):
        """Сбросить политическую власть игроку до стандартного значения (100)"""
        from political_power import get_player_state, set_political_power, save_player_state
        
        target = member or ctx.author
        state_id, state_data = get_player_state(target.id)
        
        if not state_data:
            await ctx.send(f"❌ Игрок {target.mention} не управляет государством!")
            return
        
        old_value = state_data.get("politics", {}).get("political_power", 100)
        set_political_power(state_data, 100)
        save_player_state(target.id, state_data)
        
        embed = discord.Embed(
            title="🔄 СБРОС ПОЛИТИЧЕСКОЙ ВЛАСТИ",
            description=f"Игроку **{target.display_name}** сброшена политическая власть до стандартного значения",
            color=0xFFAA00
        )
        embed.add_field(name="Было", value=f"```\n{old_value}\n```", inline=True)
        embed.add_field(name="Стало", value=f"```\n100\n```", inline=True)
        embed.add_field(name="Государство", value=f"```\n{state_data['state']['statename']}\n```", inline=False)
        
        await ctx.send(embed=embed)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} сбросил власть игроку {target.name} до 100")

    @commands.command(name='сбросить_все_власть')
    @commands.has_permissions(administrator=True)
    async def reset_all_power(self, ctx):
        """Сбросить политическую власть ВСЕМ игрокам до стандартного значения (100)"""
        from political_power import set_political_power, save_player_state
        from utils import load_states, save_states
        
        states = load_states()
        updated = 0
        results = []
        
        for state_id, state_data in states["players"].items():
            if "assigned_to" not in state_data:
                continue
            
            user_id = int(state_data["assigned_to"])
            old_value = state_data.get("politics", {}).get("political_power", 100)
            set_political_power(state_data, 100)
            save_player_state(user_id, state_data)
            updated += 1
            results.append(f"**{state_data['state']['statename']}**: {old_value} → 100")
        
        embed = discord.Embed(
            title="🔄 МАССОВЫЙ СБРОС ПОЛИТИЧЕСКОЙ ВЛАСТИ",
            description=f"Сброшена власть до 100 у {updated} игроков",
            color=0xFFAA00
        )
        
        if results:
            embed.add_field(name="Результаты", value="\n".join(results[:25]), inline=False)
        
        await ctx.send(embed=embed)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"Админ {ctx.author.name} сбросил власть всем {updated} игрокам до 100")


# ==================== ИГРОВЫЕ КОМАНДЫ ====================
class GameCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_player_state(self, user_id):
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") == str(user_id):
                return data
        return None

    def get_player_alliance(self, user_id):
        alliances = load_alliances()
        for alliance in alliances["alliances"]:
            if str(user_id) in alliance.get("members", []):
                return alliance
        return None

    @commands.command(name='государство')
    async def state(self, ctx):
        """Просмотр профиля своего государства"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("У вас нет государства! Обратитесь к администрации.")
            return
        
        state = player_data["state"]
        politics = player_data["politics"]
        economy = player_data["economy"]
        
        embed = discord.Embed(
            title=f"{state['statename']}",
            description=f"Лидер: {ctx.author.mention}",
            color=0x2b2d31
        )
        
        embed.add_field(name=f"{EMOJIS['job_spec']} Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"{state['stability']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Правительство", value=state['government_type'], inline=True)
        embed.add_field(name=f"{EMOJIS['partia']} Правящая партия", value=politics['ruling_party'], inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} Популярность", value=f"{politics['popularity']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} ВВП", value=format_gdp_display(economy), inline=True)
        
        # Безопасное отображение бюджета
        if "local_currency" in economy:
            budget_value = economy["local_currency"]["amount"]
            currency_code = economy["local_currency"]["code"]
            budget_display = f"{format_billion(budget_value)} {currency_code}"
        elif "budget_usd" in economy:
            budget_display = format_billion(economy["budget_usd"]) + " USD"
        else:
            budget_display = format_billion(economy.get("budget", 0)) + " USD"
        
        embed.add_field(name=f"{EMOJIS['money']} Бюджет", value=budget_display, inline=True)
        
        if "taxes" in economy:
            embed.add_field(name=f"{EMOJIS['government']} Налоги", value="Многокомпонентная система\n!налоги для просмотра", inline=True)
        else:
            embed.add_field(name=f"{EMOJIS['government']} Налог", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        
        embed.add_field(name=f"{EMOJIS['army']} Армия", value=f"{format_army_number(state['army_size'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['manpower']} Опытность", value=f"{state.get('army_experience', 50):.0f}%", inline=True)
        currency_code = self.get_currency_code() if hasattr(self, 'get_currency_code') else "USD"
        embed.add_field(name=f"{EMOJIS['army']} Военный бюджет", value=f"{format_billion(economy.get('military_budget_local', 0))} {get_currency_code(economy)}", inline=True)
        embed.add_field(name=f"{EMOJIS['social']} Счастье", value=f"{state['happiness']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['social']} Доверие", value=f"{state['trust']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['zakon']} Эффективность", value=f"{player_data['government_efficiency']:.0f}%", inline=True)
        
        alliance = self.get_player_alliance(ctx.author.id)
        if alliance:
            embed.add_field(name="Альянс", value=f"{alliance['name']} (участник)", inline=True)
        
        view = StateButtons(ctx.author.id, state['statename'], player_data)
        await ctx.send(embed=embed, view=view)

    @commands.command(name='расходы')
    async def expenses_command(self, ctx):
        """Просмотр и настройка расходов по министерствам"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("У вас нет государства!")
            return
        
        await show_expenses_configuration(ctx, ctx.author.id, player_data)

    @commands.command(name='пво_арсенал')
    async def pvo_arsenal(self, ctx):
        """Показать количество ПВО в арсенале"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("❌ У вас нет государства!")
            return
        
        army = player_data.get("army", {})
        ground = army.get("ground", {})
        
        embed = discord.Embed(
            title=f"ПВО в арсенале: {player_data['state']['statename']}",
            description="Доступные для установки комплексы ПВО (установка в инфраструктуре бесплатна)",
            color=0x2b2d31
        )
        
        pvo_types = [
            ("long_range_air_defense", "ЗРК большой дальности"),
            ("short_range_air_defense", "ЗРК малой дальности"),
            ("zdprk", "ЗПРК"),
            ("zas", "Зенитная артиллерия"),
            ("radar_systems", "РЛС")
        ]
        
        total_pvo = 0
        for pvo_type, name in pvo_types:
            count = ground.get(pvo_type, 0)
            total_pvo += count
            if count > 0:
                embed.add_field(
                    name=name,
                    value=f"Количество: {format_number(count)}",
                    inline=True
                )
        
        if total_pvo == 0:
            embed.add_field(name="Нет ПВО", value="В арсенале нет комплексов ПВО. Закажите их через ВПК.", inline=False)
        
        embed.set_footer(text=f"Всего ПВО в арсенале: {format_number(total_pvo)}")
        
        await ctx.send(embed=embed)

    @commands.command(name='переместить_пво')
    async def move_pvo(self, ctx):
        """Переместить ПВО между регионами"""
        await show_move_pvo_menu(ctx, ctx.author.id)

    @commands.command(name='инфраструктура')
    async def infrastructure(self, ctx):
        """Показать меню инфраструктуры для строительства"""
        await show_infrastructure_menu(ctx)

    @commands.command(name='стройки')
    async def my_construction(self, ctx):
        """Показать активные строительные проекты"""
        await show_construction_projects(ctx)

    @commands.command(name='стройки_завершить')
    async def complete_construction(self, ctx):
        """Завершить готовые строительные проекты"""
        await complete_construction_projects(ctx)

    @commands.command(name='политвласть')
    async def political_power(self, ctx):
        """Показать меню политической власти"""
        await show_political_power_menu(ctx, ctx.author.id)

    @commands.command(name='налоги')
    async def taxes(self, ctx):
        """Показать меню налоговой системы"""
        await show_tax_menu(ctx, ctx.author.id)

    @commands.command(name='таможня')
    async def tariffs(self, ctx):
        """Показать меню таможенных пошлин"""
        await show_tariffs_menu(ctx, ctx.author.id)

    @commands.command(name='впк')
    async def vpk_menu(self, ctx):
        """Открыть меню военно-промышленного комплекса"""
        await show_corporations_menu(ctx, ctx.author.id)

    @commands.command(name='гражданские')
    async def civil_menu(self, ctx):
        """Открыть меню гражданской продукции"""
        await show_civil_corporations_menu(ctx, ctx.author.id)

    @commands.command(name='заказы')
    async def my_orders(self, ctx):
        """Показать мои активные заказы (военные)"""
        await show_my_orders(ctx)

    @commands.command(name='гражданские_заказы')
    async def my_civil_orders(self, ctx):
        """Показать мои активные заказы (гражданские)"""
        await show_civil_orders(ctx)

    @commands.command(name='получить')
    async def collect_orders(self, ctx):
        """Забрать готовые заказы (военные)"""
        await collect_completed_orders(ctx)

    @commands.command(name='получить_гражданские')
    async def collect_civil_orders(self, ctx):
        """Забрать готовые заказы (гражданские)"""
        await collect_civil_orders(ctx)

    @commands.command(name='удары')
    async def strikes(self, ctx):
        """Показать меню управления ударами БПЛА и ракет"""
        await show_strike_menu(ctx, ctx.author.id)

    @commands.command(name='флот')
    async def navy_menu(self, ctx):
        """Управление военно-морским флотом"""
        await show_navy_menu(ctx, ctx.author.id)

    @commands.command(name='морская_торговля')
    async def maritime_trade(self, ctx):
        """Показать меню морской торговли"""
        await show_maritime_menu(ctx, ctx.author.id)

    @commands.command(name='энергия')
    async def energy(self, ctx):
        """Показать информацию об энергосистеме"""
        await show_energy_menu(ctx, ctx.author.id)

    @commands.command(name='спутники')
    async def satellites(self, ctx):
        """Управление спутниковой группировкой"""
        await show_satellite_menu(ctx, ctx.author.id)

    @commands.command(name='доктрины')
    async def doctrines(self, ctx):
        """Военные доктрины и тактики"""
        await show_doctrines_menu(ctx, ctx.author.id)

    @commands.command(name='мобилизация')
    async def mobilization(self, ctx):
        """Меню мобилизации гражданской промышленности"""
        await show_mobilization_menu(ctx, ctx.author.id)

    @commands.command(name='население')
    async def population(self, ctx):
        """Показать информацию о населении"""
        await show_population_menu(ctx, ctx.author.id)

    @commands.command(name='ресурсы')
    async def resources(self, ctx):
        """Просмотр ресурсов государства"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("У вас нет государства!")
            return
        
        migrate_player_resources(player_data)
        
        resources = player_data.get("resources", {})
        state_name = player_data["state"]["statename"]
        
        embed = create_resource_embed(resources, f"Ресурсы: {state_name}")
        await ctx.send(embed=embed)

    @commands.command(name='товары')
    async def civil_goods(self, ctx):
        """Просмотр гражданской продукции"""
        await show_civil_goods(ctx)

    @commands.command(name='центробанк')
    async def central_bank(self, ctx):
        """Показать меню центрального банка"""
        await show_central_bank_menu(ctx, ctx.author.id)

    @commands.command(name='коррупция')
    async def corruption(self, ctx):
        """Показать меню управления коррупцией"""
        await show_corruption_menu(ctx, ctx.author.id)

    @commands.command(name='трубопроводы')
    async def pipelines(self, ctx):
        """Управление трубопроводами"""
        await show_pipeline_menu(ctx, ctx.author.id)

    @commands.command(name='одобрить_трубопровод')
    async def approve_pipeline(self, ctx, project_id: str):
        player_data = self.get_player_state(ctx.author.id)
        if not player_data:
            await ctx.send("У вас нет государства!")
            return
        success, msg = approve_pipeline_project(project_id, player_data["state"]["statename"], ctx.author.id)
        await ctx.send(msg)

    @commands.command(name='отклонить_трубопровод')
    async def reject_pipeline(self, ctx, project_id: str):
        player_data = self.get_player_state(ctx.author.id)
        if not player_data:
            await ctx.send("У вас нет государства!")
            return
        success, msg = reject_pipeline_project(project_id, player_data["state"]["statename"], ctx.author.id)
        await ctx.send(msg)

    @commands.command(name='разведка')
    async def espionage(self, ctx):
        """Показать меню специальных операций"""
        from espionage import show_espionage_menu
        await show_espionage_menu(ctx, ctx.author.id)

    @commands.command(name='конфликты')
    async def conflicts(self, ctx):
        """Показать список активных военных конфликтов"""
        await show_conflicts_menu(ctx, ctx.author.id)

    @commands.command(name='война')
    async def war_status(self, ctx):
        """Показать информацию о войнах, в которых участвует ваша страна"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("У вас нет государства!")
            return
        
        country = player_data["state"]["statename"]
        enemies = get_countries_at_war_with(country)
        
        if not enemies:
            await ctx.send(f"{country} не участвует в военных конфликтах.")
            return
        
        embed = discord.Embed(
            title=f"Военные конфликты {country}",
            color=discord.Color.red()
        )
        
        enemies_text = "\n".join([f"• {enemy}" for enemy in enemies])
        embed.add_field(name="Противники", value=enemies_text, inline=False)
        
        from conflicts import get_conflicts_for_country
        conflicts = get_conflicts_for_country(country)
        
        for conflict in conflicts[:3]:
            other = conflict.country2 if conflict.country1 == country else conflict.country1
            stats = f"Начало: {conflict.started_at[:10]}\n"
            stats += f"Ваши удары: {conflict.strikes_count.get(country, 0)}\n"
            stats += f"Урон противнику: {conflict.damage_inflicted.get(country, 0)}"
            
            embed.add_field(name=f"Против: {other}", value=stats, inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='время')
    async def game_time(self, ctx):
        """Показать текущее игровое время"""
        from game_time import get_game_date_formatted, get_season, get_year, get_month
        from utils import DARK_THEME_COLOR
    
        game_date = get_game_date_formatted()
        season = get_season()
        month = get_month()
        year = get_year()
    
        month_names = [
            "январь", "февраль", "март", "апрель", "май", "июнь",
            "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
        ]
    
        embed = discord.Embed(
            title="Игровой календарь",
            color=DARK_THEME_COLOR
        )
    
        embed.add_field(name="Текущая дата", value=game_date, inline=True)
        embed.add_field(name="Время года", value=season.capitalize(), inline=True)
        embed.add_field(name="Месяц", value=month_names[month-1], inline=True)
    
        await ctx.send(embed=embed)

    @commands.command(name='прогноз')
    async def consumption_forecast(self, ctx):
        """Показать прогноз потребления товаров и услуг"""
        await show_consumption_forecast(ctx, ctx.author.id)

    @commands.command(name='торговля')
    async def trade(self, ctx, member: discord.Member, resource: str, amount: int, price: int, payment_currency: str = "USD"):
        """Предложить сделку другому игроку"""
        from resource_system import get_resource_key, get_all_resource_names, get_resource_name_by_key
        
        if member.id == ctx.author.id:
            await ctx.send("Нельзя торговать с самим собой!")
            return
        
        if amount <= 0 or price <= 0:
            await ctx.send("Количество и цена должны быть положительными!")
            return
        
        resource_key = get_resource_key(resource)
        
        if not resource_key:
            available = ", ".join(get_all_resource_names())
            await ctx.send(f"Неизвестный ресурс!\n\nДоступные ресурсы:\n{available}")
            return
        
        states = load_states()
        trades = load_trades()
        
        seller_data = None
        buyer_data = None
        
        for data in states["players"].values():
            if data.get("assigned_to") == str(ctx.author.id):
                seller_data = data
            if data.get("assigned_to") == str(member.id):
                buyer_data = data
        
        if not seller_data:
            await ctx.send("У вас нет государства!")
            return
        
        if not buyer_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(seller_data)
        
        if resource_key not in seller_data.get("resources", {}):
            await ctx.send(f"У вас нет ресурса {get_resource_name_by_key(resource_key)}!")
            return
        
        if seller_data["resources"][resource_key] < amount:
            await ctx.send(f"У вас недостаточно {get_resource_name_by_key(resource_key)}! Доступно: {seller_data['resources'][resource_key]}")
            return
        
        total_price_usd = amount * price * 1000  # цена в тысячах USD
        
        seller_country = seller_data["state"]["statename"]
        buyer_country = buyer_data["state"]["statename"]
        
        from trade_tariffs import calculate_trade_with_tariffs
        
        trade_calc = calculate_trade_with_tariffs(
            {"resource": resource_key, "amount": amount, "total_price": total_price_usd},
            seller_country,
            buyer_country
        )
        
        if trade_calc.get("blocked", False):
            await ctx.send(f"Сделка заблокирована: {trade_calc['reason']}")
            return
        
        # Проверка валюты оплаты
        valid_currencies = ["USD"]
        seller_currency = seller_data["economy"].get("local_currency", {}).get("code", "USD")
        if seller_currency != "USD":
            valid_currencies.append(seller_currency)
        
        if payment_currency.upper() not in valid_currencies:
            await ctx.send(f"Неверная валюта оплаты! Доступно: {', '.join(valid_currencies)}")
            return
        
        payment_currency = payment_currency.upper()
        
        trade_id = len(trades["active_trades"]) + 1
        trade = {
            "id": trade_id,
            "seller_id": str(ctx.author.id),
            "seller_name": ctx.author.name,
            "seller_country": seller_country,
            "buyer_id": str(member.id),
            "buyer_name": member.name,
            "buyer_country": buyer_country,
            "resource": resource_key,
            "resource_name": get_resource_name_by_key(resource_key, with_emoji=False),
            "amount": amount,
            "price_per_unit_usd": price * 1000,
            "total_price": total_price_usd,
            "import_tariff": trade_calc["import_tariff"],
            "export_tariff": trade_calc["export_tariff"],
            "final_price": trade_calc["final_price"],
            "seller_receives": trade_calc["seller_receives"],
            "payment_currency": payment_currency,
            "status": "pending",
            "created_at": str(datetime.now())
        }
        
        trades["active_trades"].append(trade)
        save_trades(trades)
        
        embed = discord.Embed(
            title="Новое торговое предложение",
            description=f"Игрок {ctx.author.mention} предлагает вам сделку",
            color=0x2b2d31
        )
        embed.add_field(name="Ресурс", value=get_resource_name_by_key(resource_key, with_emoji=True), inline=True)
        embed.add_field(name="Количество", value=format_number(amount), inline=True)
        embed.add_field(name="Цена за ед.", value=f"${price * 1000:,.0f} USD", inline=True)
        embed.add_field(name="Общая стоимость", value=f"${total_price_usd:,.0f} USD", inline=True)
        
        if trade_calc["import_tariff"] > 0 or trade_calc["export_tariff"] > 0:
            if trade_calc["import_tariff"] > 0:
                embed.add_field(name="Импортная пошлина", value=f"${trade_calc['import_tariff']:,.0f} USD", inline=True)
            if trade_calc["export_tariff"] > 0:
                embed.add_field(name="Экспортная пошлина", value=f"${trade_calc['export_tariff']:,.0f} USD", inline=True)
            embed.add_field(name="Итоговая цена для вас", value=f"${trade_calc['final_price']:,.0f} USD", inline=True)
            embed.add_field(name="Продавец получит", value=f"${trade_calc['seller_receives']:,.0f} USD", inline=True)
        
        embed.add_field(name="Валюта оплаты продавцу", value=payment_currency, inline=True)
        embed.add_field(name="ID сделки", value=str(trade_id), inline=True)
        embed.set_footer(text="Для принятия используйте !принять ID")
        
        try:
            await member.send(embed=embed)
            await ctx.send(f"Предложение отправлено игроку {member.mention}! ID сделки: {trade_id}")
        except:
            await ctx.send(f"Предложение создано! ID сделки: {trade_id}\nНе удалось отправить ЛС игроку {member.mention}. Он может принять сделку командой !принять {trade_id}")
        
    @commands.command(name='принять')
    async def accept_trade(self, ctx, trade_id: int):
        """Принять торговое предложение"""
        from resource_system import get_resource_name_by_key
        from utils import EXCHANGE_RATES_2019, get_currency_code, get_budget
        
        trades = load_trades()
        states = load_states()
        
        trade = None
        for t in trades["active_trades"]:
            if t["id"] == trade_id:
                trade = t
                break
        
        if not trade:
            await ctx.send(f"Сделка с ID {trade_id} не найдена!")
            return
        
        if trade["buyer_id"] != str(ctx.author.id):
            await ctx.send("Это не ваша сделка!")
            return
        
        if trade["status"] != "pending":
            await ctx.send("Эта сделка уже обработана!")
            return
        
        seller_data = None
        buyer_data = None
        
        for data in states["players"].values():
            if data.get("assigned_to") == trade["seller_id"]:
                seller_data = data
            if data.get("assigned_to") == trade["buyer_id"]:
                buyer_data = data
        
        if not seller_data or not buyer_data:
            await ctx.send("Ошибка загрузки данных игроков!")
            return
        
        migrate_player_resources(seller_data)
        migrate_player_resources(buyer_data)
        
        resource_key = trade["resource"]
        resource_name = trade.get("resource_name", get_resource_name_by_key(resource_key, with_emoji=False))
        
        # Проверка наличия ресурса у продавца
        if resource_key not in seller_data.get("resources", {}):
            await ctx.send(f"У продавца больше нет {resource_name}!")
            trade["status"] = "failed"
            save_trades(trades)
            return
        
        if seller_data["resources"][resource_key] < trade["amount"]:
            await ctx.send(f"У продавца недостаточно {resource_name}!")
            trade["status"] = "failed"
            save_trades(trades)
            return
        
        final_price_usd = trade.get("final_price", trade["total_price"])
        seller_receives_usd = trade.get("seller_receives", trade["total_price"])
        import_tariff_usd = trade.get("import_tariff", 0)
        export_tariff_usd = trade.get("export_tariff", 0)
        payment_currency = trade.get("payment_currency", "USD")
        
        # Проверка USD-резервов покупателя
        buyer_reserves = buyer_data["economy"].get("foreign_reserves", {})
        buyer_usd = buyer_reserves.get("USD", 0)
        
        if buyer_usd < final_price_usd:
            await ctx.send(f"Недостаточно USD в резервах! Нужно: ${final_price_usd:,.0f}, доступно: ${buyer_usd:,.0f}")
            return
        
        # Списываем USD у покупателя
        buyer_reserves["USD"] = buyer_usd - final_price_usd
        
        # Импортная пошлина в USD-резервы покупателя
        if import_tariff_usd > 0:
            buyer_reserves["USD"] = buyer_reserves.get("USD", 0) + import_tariff_usd
            buyer_data["tariff_revenue_usd"] = buyer_data.get("tariff_revenue_usd", 0) + import_tariff_usd
        
        # Экспортная пошлина в USD-резервы продавца
        if export_tariff_usd > 0:
            seller_reserves = seller_data["economy"].get("foreign_reserves", {})
            if "foreign_reserves" not in seller_data["economy"]:
                seller_data["economy"]["foreign_reserves"] = {"USD": 0, "EUR": 0, "CNY": 0, "gold_tons": 0}
            seller_data["economy"]["foreign_reserves"]["USD"] = seller_data["economy"]["foreign_reserves"].get("USD", 0) + export_tariff_usd
            seller_data["export_tariff_revenue_usd"] = seller_data.get("export_tariff_revenue_usd", 0) + export_tariff_usd
        
        # Оплата продавцу
        seller_reserves = seller_data["economy"].get("foreign_reserves", {})
        if "foreign_reserves" not in seller_data["economy"]:
            seller_data["economy"]["foreign_reserves"] = {"USD": 0, "EUR": 0, "CNY": 0, "gold_tons": 0}
        
        if payment_currency == "USD":
            # Оплата в USD в резервы
            seller_data["economy"]["foreign_reserves"]["USD"] = seller_data["economy"]["foreign_reserves"].get("USD", 0) + seller_receives_usd
            payment_info = f"${seller_receives_usd:,.0f} USD (в резервы)"
        else:
            # Конвертация в локальную валюту
            seller_country = seller_data["state"]["statename"]
            rate = EXCHANGE_RATES_2019.get(seller_country, 1.0)
            local_amount = seller_receives_usd * rate
            
            if "local_currency" not in seller_data["economy"]:
                seller_data["economy"]["local_currency"] = {"code": payment_currency, "amount": 0, "inflation": 2.0, "interest_rate": 5.0}
            
            seller_data["economy"]["local_currency"]["amount"] = seller_data["economy"]["local_currency"].get("amount", 0) + local_amount
            currency_code = seller_data["economy"]["local_currency"]["code"]
            payment_info = f"{format_billion(local_amount)} {currency_code} (в бюджет)"
        
        # Перемещение ресурсов
        seller_data["resources"][resource_key] -= trade["amount"]
        if "resources" not in buyer_data:
            buyer_data["resources"] = {}
        buyer_data["resources"][resource_key] = buyer_data["resources"].get(resource_key, 0) + trade["amount"]
        
        trade["status"] = "completed"
        trade["completed_at"] = str(datetime.now())
        trades["completed_trades"].append(trade)
        trades["active_trades"].remove(trade)
        
        save_states(states)
        save_trades(trades)
        
        embed = discord.Embed(
            title="Сделка завершена!",
            color=0x2b2d31
        )
        embed.add_field(name="Ресурс", value=f"{get_resource_name_by_key(resource_key, with_emoji=True)}", inline=True)
        embed.add_field(name="Количество", value=format_number(trade['amount']), inline=True)
        embed.add_field(name="Сумма сделки", value=f"${final_price_usd:,.0f} USD", inline=True)
        
        if import_tariff_usd > 0:
            embed.add_field(name="Импортная пошлина (в ваш бюджет)", value=f"${import_tariff_usd:,.0f} USD", inline=True)
        if export_tariff_usd > 0:
            embed.add_field(name="Экспортная пошлина (бюджет продавца)", value=f"${export_tariff_usd:,.0f} USD", inline=True)
        
        embed.add_field(name="Продавец получил", value=payment_info, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='мои_сделки')
    async def my_trades(self, ctx):
        """Показать мои активные сделки"""
        from resource_system import get_resource_name_by_key
    
        trades = load_trades()
    
        my_id = str(ctx.author.id)
        my_trades = [t for t in trades["active_trades"] 
                if t["seller_id"] == my_id or t["buyer_id"] == my_id]
    
        if not my_trades:
            await ctx.send("📭 У вас нет активных сделок.")
            return
    
        embed = discord.Embed(
            title="📋 Мои активные сделки",
            color=0x2b2d31
        )
    
        for trade in my_trades[:5]:
            direction = "📤 Продажа" if trade["seller_id"] == my_id else "📥 Покупка"
            other_user = trade["buyer_name"] if trade["seller_id"] == my_id else trade["seller_name"]
        
            resource_name = trade.get("resource_name", get_resource_name_by_key(trade["resource"], with_emoji=False))
            final_price = trade.get("final_price", trade["total_price"])
        
            embed.add_field(
                name=f"#{trade['id']} {direction}",
                value=f"📦 **{resource_name}**\n"
                      f"🔢 Количество: {format_number(trade['amount'])}\n"
                      f"💰 Сумма: {format_billion(final_price)}\n"
                      f"🤝 С кем: {other_user}",
                inline=False
            )
    
        await ctx.send(embed=embed)

    @commands.command(name='передать_ресурс')
    async def transfer_resource(self, ctx, member: discord.Member, resource: str, amount: int):
        """Передать ресурс другому игроку"""
        if member.id == ctx.author.id:
            await ctx.send("Нельзя передавать ресурсы самому себе!")
            return
        
        if amount <= 0:
            await ctx.send("Количество должно быть положительным!")
            return
        
        if resource not in RESOURCE_PRICES:
            await ctx.send(f"Неизвестный ресурс! Доступные: {', '.join(RESOURCE_PRICES.keys())}")
            return
        
        states = load_states()
        
        sender_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(ctx.author.id):
                sender_data = data
                break
        
        receiver_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                receiver_data = data
                break
        
        if not sender_data:
            await ctx.send("У вас нет государства!")
            return
        
        if not receiver_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(sender_data)
        
        if resource not in sender_data.get("resources", {}):
            await ctx.send(f"У вас нет ресурса {resource}!")
            return
        
        if sender_data["resources"][resource] < amount:
            await ctx.send(f"У вас недостаточно {resource}! Доступно: {sender_data['resources'][resource]}")
            return
        
        transfers = load_transfers()
        
        transfer_id = 1
        if transfers["active_transfers"]:
            transfer_id = max(t["id"] for t in transfers["active_transfers"]) + 1
        
        transfer = {
            "id": transfer_id,
            "sender_id": str(ctx.author.id),
            "receiver_id": str(member.id),
            "sender_name": ctx.author.name,
            "receiver_name": member.name,
            "type": "resource",
            "resource": resource,
            "amount": amount,
            "status": "pending",
            "created_at": str(datetime.now())
        }
        
        transfers["active_transfers"].append(transfer)
        save_transfers(transfers)
        
        view = TransferConfirmView(transfer_id, ctx.author.id, member.id, "resource")
        
        embed = discord.Embed(
            title="Запрос на передачу ресурсов",
            description=f"Игрок {ctx.author.mention} хочет передать вам ресурсы",
            color=0x2b2d31
        )
        embed.add_field(name="Ресурс", value=resource, inline=True)
        embed.add_field(name="Количество", value=format_number(amount), inline=True)
        embed.add_field(name="ID перевода", value=transfer_id, inline=True)
        
        await ctx.send(f"Запрос на передачу ресурсов отправлен игроку {member.mention}!")
        
        try:
            await member.send(embed=embed, view=view)
        except:
            await ctx.send(f"Не удалось отправить личное сообщение игроку {member.mention}. Он должен принять перевод в канале командой `!принять_перевод {transfer_id}`")

    @commands.command(name='передать_технику')
    async def transfer_equipment(self, ctx, member: discord.Member, equip_type: str, amount: int):
        """Передать технику другому игроку"""
        if member.id == ctx.author.id:
            await ctx.send("Нельзя передавать технику самому себе!")
            return
        
        if amount <= 0:
            await ctx.send("Количество должно быть положительным!")
            return
        
        states = load_states()
        
        sender_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(ctx.author.id):
                sender_data = data
                break
        
        receiver_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                receiver_data = data
                break
        
        if not sender_data:
            await ctx.send("У вас нет государства!")
            return
        
        if not receiver_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        path = equip_type.split('.')
        
        if "army" not in sender_data:
            sender_data["army"] = {}
        
        current = sender_data["army"]
        
        for key in path[:-1]:
            if key not in current:
                await ctx.send(f"Категория {key} не найдена в вашей армии!")
                return
            current = current[key]
        
        last_key = path[-1]
        if last_key not in current or current[last_key] < amount:
            tech_name = EQUIPMENT_NAMES.get(equip_type, last_key)
            available = current.get(last_key, 0)
            await ctx.send(f"У вас недостаточно {tech_name}! Доступно: {format_number(available)}")
            return
        
        transfers = load_transfers()
        
        transfer_id = 1
        if transfers["active_transfers"]:
            transfer_id = max(t["id"] for t in transfers["active_transfers"]) + 1
        
        transfer = {
            "id": transfer_id,
            "sender_id": str(ctx.author.id),
            "receiver_id": str(member.id),
            "sender_name": ctx.author.name,
            "receiver_name": member.name,
            "type": "equipment",
            "equip_type": equip_type,
            "amount": amount,
            "status": "pending",
            "created_at": str(datetime.now())
        }
        
        transfers["active_transfers"].append(transfer)
        save_transfers(transfers)
        
        tech_name = EQUIPMENT_NAMES.get(equip_type, equip_type.split('.')[-1])
        
        view = TransferConfirmView(transfer_id, ctx.author.id, member.id, "equipment")
        
        embed = discord.Embed(
            title="Запрос на передачу техники",
            description=f"Игрок {ctx.author.mention} хочет передать вам технику",
            color=0x2b2d31
        )
        embed.add_field(name="Техника", value=tech_name, inline=True)
        embed.add_field(name="Количество", value=format_number(amount), inline=True)
        embed.add_field(name="ID перевода", value=transfer_id, inline=True)
        
        await ctx.send(f"Запрос на передачу техники отправлен игроку {member.mention}!")
        
        try:
            await member.send(embed=embed, view=view)
        except:
            await ctx.send(f"Не удалось отправить личное сообщение игроку {member.mention}. Он должен принять перевод в канале командой `!принять_перевод {transfer_id}`")

    @commands.command(name='принять_перевод')
    async def accept_transfer_command(self, ctx, transfer_id: int):
        """Принять перевод ресурсов или техники"""
        transfers = load_transfers()
        
        transfer = None
        for t in transfers["active_transfers"]:
            if t["id"] == transfer_id:
                transfer = t
                break
        
        if not transfer:
            await ctx.send(f"Перевод с ID {transfer_id} не найден!")
            return
        
        if transfer["receiver_id"] != str(ctx.author.id):
            await ctx.send("Это не ваш перевод!")
            return
        
        if transfer["status"] != "pending":
            await ctx.send("Этот перевод уже обработан!")
            return
        
        states = load_states()
        
        sender_data = None
        receiver_data = None
        
        for data in states["players"].values():
            if data.get("assigned_to") == transfer["sender_id"]:
                sender_data = data
            if data.get("assigned_to") == transfer["receiver_id"]:
                receiver_data = data
        
        if not sender_data or not receiver_data:
            await ctx.send("Ошибка загрузки данных игроков!")
            return
        
        if transfer["type"] == "resource":
            migrate_player_resources(sender_data)
            migrate_player_resources(receiver_data)
        
        success = False
        error_msg = ""
        
        if transfer["type"] == "resource":
            resource = transfer["resource"]
            amount = transfer["amount"]
            
            if resource in sender_data.get("resources", {}):
                if sender_data["resources"][resource] >= amount:
                    sender_data["resources"][resource] -= amount
                    if "resources" not in receiver_data:
                        receiver_data["resources"] = {}
                    receiver_data["resources"][resource] = receiver_data["resources"].get(resource, 0) + amount
                    success = True
                else:
                    error_msg = "У отправителя недостаточно ресурса!"
            else:
                error_msg = "У отправителя нет такого ресурса!"
        
        elif transfer["type"] == "equipment":
            equip_type = transfer["equip_type"]
            amount = transfer["amount"]
            path = equip_type.split('.')
            
            current = sender_data.get("army", {})
            for key in path[:-1]:
                if key not in current:
                    error_msg = f"Категория {key} не найдена у отправителя!"
                    break
                current = current[key]
            
            if not error_msg:
                last_key = path[-1]
                if last_key in current and current[last_key] >= amount:
                    current[last_key] -= amount
                    
                    rec_current = receiver_data.get("army", {})
                    for key in path[:-1]:
                        if key not in rec_current:
                            rec_current[key] = {}
                        rec_current = rec_current[key]
                    
                    if last_key not in rec_current:
                        rec_current[last_key] = 0
                    rec_current[last_key] += amount
                    
                    if "army" not in receiver_data:
                        receiver_data["army"] = {}
                    
                    success = True
                else:
                    error_msg = "У отправителя недостаточно техники!"
        
        if success:
            transfer["status"] = "completed"
            transfer["completed_at"] = str(datetime.now())
            transfers["completed_transfers"].append(transfer)
            transfers["active_transfers"].remove(transfer)
            
            save_states(states)
            save_transfers(transfers)
            
            embed = discord.Embed(
                title="Перевод выполнен!",
                color=0x2b2d31
            )
            
            if transfer["type"] == "resource":
                embed.add_field(name="Ресурс", value=transfer["resource"], inline=True)
                embed.add_field(name="Количество", value=format_number(transfer["amount"]), inline=True)
            else:
                tech_name = EQUIPMENT_NAMES.get(transfer["equip_type"], transfer["equip_type"])
                embed.add_field(name="Техника", value=tech_name, inline=True)
                embed.add_field(name="Количество", value=format_number(transfer["amount"]), inline=True)
            
            embed.add_field(name="Отправитель", value=f"<@{transfer['sender_id']}>", inline=True)
            embed.add_field(name="Получатель", value=f"<@{transfer['receiver_id']}>", inline=True)
            
            await ctx.send(embed=embed)
        else:
            await ctx.send(error_msg)

    @commands.command(name='мои_переводы')
    async def my_transfers(self, ctx):
        """Показать мои активные переводы"""
        transfers = load_transfers()
        
        my_id = str(ctx.author.id)
        my_transfers = [t for t in transfers["active_transfers"] 
                       if t["sender_id"] == my_id or t["receiver_id"] == my_id]
        
        if not my_transfers:
            await ctx.send("У вас нет активных переводов.")
            return
        
        embed = discord.Embed(
            title="Мои активные переводы",
            color=0x2b2d31
        )
        
        for transfer in my_transfers[:5]:
            if transfer["type"] == "resource":
                item_name = transfer["resource"]
            else:
                item_name = EQUIPMENT_NAMES.get(transfer["equip_type"], transfer["equip_type"])
            
            direction = "Исходящий" if transfer["sender_id"] == my_id else "Входящий"
            other_user = f"<@{transfer['receiver_id']}>" if transfer["sender_id"] == my_id else f"<@{transfer['sender_id']}>"
            
            embed.add_field(
                name=f"Перевод #{transfer['id']} {direction}",
                value=f"{item_name}: {format_number(transfer['amount'])} ед.\n"
                      f"С кем: {other_user}\n"
                      f"Статус: Ожидает подтверждения",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='государство_игрока')
    async def state_player(self, ctx, member: discord.Member):
        """Просмотр профиля другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        state = player_data["state"]
        politics = player_data["politics"]
        economy = player_data["economy"]
        
        embed = discord.Embed(
            title=f"Государство {state['statename']}",
            description=f"Лидер: {member.mention}",
            color=0x2b2d31
        )
        
        embed.add_field(name=f"{EMOJIS['job_spec']} Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"{state['stability']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Правительство", value=state['government_type'], inline=True)
        embed.add_field(name=f"{EMOJIS['partia']} Правящая партия", value=politics['ruling_party'], inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} Популярность", value=f"{politics['popularity']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} ВВП", value=format_gdp_display(economy), inline=True)
        embed.add_field(name=f"{EMOJIS['money']} Бюджет", value=format_billion(economy['budget']), inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Налог", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        embed.add_field(name=f"{EMOJIS['army']} Армия", value=f"{format_army_number(state['army_size'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['manpower']} Опытность", value=f"{state.get('army_experience', 50):.0f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['army']} Военный бюджет", value=f"{format_billion(get_military_budget(economy))} {currency_code}", inline=True)
        embed.add_field(name=f"{EMOJIS['social']} Счастье", value=f"{state['happiness']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['social']} Доверие", value=f"{state['trust']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['zakon']} Эффективность", value=f"{player_data['government_efficiency']:.0f}%", inline=True)
        
        alliance = self.get_player_alliance(member.id)
        if alliance:
            embed.add_field(name="Альянс", value=f"{alliance['name']} (участник)", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='армия_игрока')
    async def army_player(self, ctx, member: discord.Member):
        """Просмотр армии другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        army = player_data.get("army", {})
        state = player_data["state"]
        state_name = state["statename"]
        
        embed = discord.Embed(
            title=f"Армия: {state_name}",
            description=f"Лидер: {member.mention}\n"
                       f"Личный состав: {format_army_number(state['army_size'])} чел.\n"
                       f"Средняя опытность: {state.get('army_experience', 50):.0f}%",
            color=0x2b2d31
        )
        
        ground = army.get("ground", {})
        pvo_in_arsenal = []
        pvo_types = ["short_range_air_defense", "long_range_air_defense", "zdprk", "zas", "radar_systems"]
        
        for pvo_type in pvo_types:
            count = ground.get(pvo_type, 0)
            if count > 0:
                pvo_name = INFRASTRUCTURE_COSTS.get(pvo_type, {}).get("name", pvo_type)
                pvo_in_arsenal.append(f"{pvo_name}: {format_number(count)}")
        
        if pvo_in_arsenal:
            embed.add_field(name="ПВО в арсенале", value="\n".join(pvo_in_arsenal), inline=False)
        
        if "ground" in army and army["ground"]:
            ground = army["ground"]
            ground_text = ""
            ground_names = {
                "tanks": "Танки", "btr": "БТР", "bmp": "БМП", "armored_vehicles": "Бронеавтомобили",
                "trucks": "Грузовики", "cars": "Автомобили", "ew_vehicles": "Машины РЭБ",
                "engineering_equipment": "Инженерная техника", "radar_systems": "РЛС",
                "self_propelled_artillery": "САУ", "towed_artillery": "Буксируемая артиллерия",
                "mlrs": "РСЗО", "atgm_complexes": "ПТРК", "otr_complexes": "ОТРК",
                "zas": "Зенитная артиллерия", "zdprk": "ЗПРК",
                "short_range_air_defense": "ПВО ближнего действия", "long_range_air_defense": "ПВО дальнего действия"
            }
            for key, name in ground_names.items():
                if key in ground and ground[key] > 0:
                    ground_text += f"{name}: {format_number(ground[key])}\n"
            if not ground_text:
                ground_text = "Нет техники"
            embed.add_field(name="Сухопутные войска", value=ground_text, inline=False)
        
        if "air" in army and army["air"]:
            air = army["air"]
            air_text = ""
            air_names = {
                "fighters": "Истребители", "attack_aircraft": "Штурмовики", "bombers": "Бомбардировщики",
                "transport_aircraft": "Транспортные самолеты", "attack_helicopters": "Ударные вертолеты",
                "transport_helicopters": "Транспортные вертолеты", "recon_uav": "Разведывательные БПЛА",
                "attack_uav": "Ударные БПЛА", "kamikaze_drones": "Дроны-камикадзе"
            }
            for key, name in air_names.items():
                if key in air and air[key] > 0:
                    air_text += f"{name}: {format_number(air[key])}\n"
            if not air_text:
                air_text = "Нет авиации"
            embed.add_field(name="Военно-воздушные силы", value=air_text, inline=False)
        
        if "navy" in army and army["navy"]:
            navy = army["navy"]
            navy_text = ""
            navy_names = {
                "boats": "Катера", "corvettes": "Корветы", "destroyers": "Эсминцы",
                "cruisers": "Крейсера", "aircraft_carriers": "Авианосцы", "submarines": "Подводные лодки", "usv_attack": "Надводные дроны"
            }
            for key, name in navy_names.items():
                if key in navy and navy[key] > 0:
                    navy_text += f"{name}: {format_number(navy[key])}\n"
            if not navy_text:
                navy_text = "Нет флота"
            embed.add_field(name="Военно-морской флот", value=navy_text, inline=False)
        
        if "missiles" in army and army["missiles"]:
            missiles = army["missiles"]
            missiles_text = ""
            missiles_names = {
                "strategic_nuclear": "Стратегическое ядерное оружие", "tactical_nuclear": "Тактическое ядерное оружие",
                "cruise_missiles": "Крылатые ракеты", "hypersonic_missiles": "Гиперзвуковые ракеты",
                "ballistic_missiles": "Баллистические ракеты"
            }
            for key, name in missiles_names.items():
                if key in missiles and missiles[key] > 0:
                    missiles_text += f"{name}: {format_number(missiles[key])}\n"
            if not missiles_text:
                missiles_text = "Нет ракетного вооружения"
            embed.add_field(name="Ракетное вооружение", value=missiles_text, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='бюджет_игрока')
    async def budget_player(self, ctx, member: discord.Member):
        """Просмотр бюджета другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        economy = player_data["economy"]
        state = player_data["state"]
        
        # Безопасное получение валюты и значений
        if "local_currency" in economy:
            currency_code = economy["local_currency"]["code"]
            budget = economy["local_currency"]["amount"]
            gdp = economy.get("gdp_local", 0)
            debt = economy.get("debt_local", 0)
            military_budget = economy.get("military_budget_local", 0)
            wage = economy.get("wage_local", 0)
            inflation = economy["local_currency"].get("inflation", 2.0)
        else:
            currency_code = "USD"
            budget = economy.get("budget_usd", economy.get("budget", 0))
            gdp = economy.get("gdp_usd", economy.get("gdp", 0))
            debt = economy.get("debt_usd", economy.get("debt", 0))
            military_budget = economy.get("military_budget", 0)
            wage = economy.get("wage", 0)
            inflation = economy.get("inflation", 2.0)
        
        embed = discord.Embed(
            title=f"Бюджет {state['statename']}",
            description=f"Лидер: {member.mention}",
            color=0x2b2d31
        )
        
        embed.add_field(name=f"{EMOJIS['money']} Госбюджет", value=f"{format_billion(budget)} {currency_code}", inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} ВВП", value=f"{format_billion(gdp)} {currency_code}", inline=True)
        embed.add_field(name="Госдолг", value=f"{format_billion(debt)} {currency_code}", inline=True)
        
        if "taxes" in economy:
            tax_system = TaxSystem(player_data)
            revenue = tax_system.calculate_total_tax_revenue()
            embed.add_field(name="Налоговые поступления", value=f"{format_billion(revenue['total'])} {currency_code}", inline=True)
            embed.add_field(name="Эфф. ставка", value=f"{revenue['effective_rate']:.1f}% ВВП", inline=True)
        else:
            embed.add_field(name="Налоговая ставка", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        
        embed.add_field(name="Инфляция", value=f"{inflation:.2f}%", inline=True)
        embed.add_field(name="Средняя зарплата", value=f"{format_billion(wage)} {currency_code}/год", inline=True)
        embed.add_field(name=f"{EMOJIS['army']} Военный бюджет", value=f"{format_billion(military_budget)} {currency_code}", inline=True)
        
        cost_local = economy.get('cost_of_living_local', economy.get('cost_of_living', 0))
        embed.add_field(name="Стоимость жизни", value=f"{format_billion(cost_local)} {currency_code}/год", inline=True)
        
        if gdp > 0:
            debt_to_gdp = (debt / gdp) * 100
            embed.add_field(name="Долг/ВВП", value=f"{debt_to_gdp:.1f}%", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='расходы_игрока')
    async def expenses_player(self, ctx, member: discord.Member):
        """Показать расходы другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        economy = player_data["economy"]
        state_name = player_data["state"]["statename"]
        
        # Безопасное получение валюты и значений
        if "local_currency" in economy:
            currency_code = economy["local_currency"]["code"]
            budget = economy["local_currency"]["amount"]
            defense_spending = economy.get("military_budget_local", 0)
        else:
            currency_code = "USD"
            budget = economy.get("budget_usd", economy.get("budget", 0))
            defense_spending = economy.get("military_budget", 0)
        
        expenses = player_data.get("expenses", {})
        healthcare_spending = expenses.get("healthcare", 0)
        police_spending = expenses.get("police", 0)
        social_spending = expenses.get("social_security", 0)
        education_spending = expenses.get("education", 0)
        
        total_expenses = defense_spending + healthcare_spending + police_spending + social_spending + education_spending
        
        embed = discord.Embed(
            title=f"Расходы государства: {state_name}",
            description=f"Лидер: {member.mention}\nОбщий бюджет: {format_billion(budget)} {currency_code}",
            color=0x2b2d31
        )
        
        embed.add_field(name=f"{EMOJIS['army']} Оборона", 
                       value=f"{format_billion(defense_spending)} {currency_code}\n({defense_spending/budget*100:.1f}% бюджета)" if budget > 0 else f"{format_billion(defense_spending)} {currency_code}", 
                       inline=True)
        embed.add_field(name=f"{EMOJIS['medicina']} Здравоохранение", 
                       value=f"{format_billion(healthcare_spending)} {currency_code}\n({healthcare_spending/budget*100:.1f}% бюджета)" if budget > 0 else f"{format_billion(healthcare_spending)} {currency_code}", 
                       inline=True)
        embed.add_field(name=f"{EMOJIS['police']} Полиция", 
                       value=f"{format_billion(police_spending)} {currency_code}\n({police_spending/budget*100:.1f}% бюджета)" if budget > 0 else f"{format_billion(police_spending)} {currency_code}", 
                       inline=True)
        embed.add_field(name=f"{EMOJIS['social']} Соцобеспечение", 
                       value=f"{format_billion(social_spending)} {currency_code}\n({social_spending/budget*100:.1f}% бюджета)" if budget > 0 else f"{format_billion(social_spending)} {currency_code}", 
                       inline=True)
        embed.add_field(name=f"{EMOJIS['education']} Образование", 
                       value=f"{format_billion(education_spending)} {currency_code}\n({education_spending/budget*100:.1f}% бюджета)" if budget > 0 else f"{format_billion(education_spending)} {currency_code}", 
                       inline=True)
        embed.add_field(name="Всего расходов", 
                       value=f"{format_billion(total_expenses)} {currency_code}\n({total_expenses/budget*100:.1f}% бюджета)" if budget > 0 else f"{format_billion(total_expenses)} {currency_code}", 
                       inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='ресурсы_игрока')
    async def resources_player(self, ctx, member: discord.Member):
        """Просмотр ресурсов другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(player_data)
        
        resources = player_data.get("resources", {})
        state_name = player_data["state"]["statename"]
        
        embed = create_resource_embed(resources, f"Ресурсы: {state_name}")
        await ctx.send(embed=embed)

    @commands.command(name='товары_игрока')
    async def civil_goods_player(self, ctx, member: discord.Member):
        """Просмотр гражданской продукции другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        class TempCtx:
            def __init__(self, author):
                self.author = author
        
        temp_ctx = TempCtx(member)
        await show_civil_goods(temp_ctx)

    @commands.command(name='статистика')
    async def player_stats(self, ctx, member: discord.Member = None):
        """Показать всю статистику игрока"""
        if member is None:
            member = ctx.author
        
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(player_data)
        
        state = player_data["state"]
        politics = player_data["politics"]
        economy = player_data["economy"]
        army = player_data.get("army", {})
        resources = player_data.get("resources", {})
        civil_goods = player_data.get("civil_goods", {})
        
        embed = discord.Embed(
            title=f"Статистика: {state['statename']}",
            description=f"Лидер: {member.mention}",
            color=0x2b2d31
        )
        
        embed.add_field(name=f"{EMOJIS['job_spec']} Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"{state['stability']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Правительство", value=state['government_type'][:20], inline=True)
        embed.add_field(name=f"{EMOJIS['partia']} Правящая партия", value=politics['ruling_party'][:20], inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} Популярность", value=f"{politics['popularity']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['vvp']} ВВП", value=format_gdp_display(economy), inline=True)
        embed.add_field(name=f"{EMOJIS['money']} Бюджет", value=format_billion(economy['budget']), inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Налог", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        
        total_resource_value = 0
        resource_text = ""
        for resource, amount in list(resources.items())[:3]:
            if resource in RESOURCE_PRICES and amount > 0:
                value = calculate_resource_value(resource, amount)
                total_resource_value += value
                resource_text += f"{resource}: {format_number(amount)}\n"
        
        if resource_text:
            embed.add_field(name="Основные ресурсы", value=resource_text, inline=True)
            embed.add_field(name="Стоимость ресурсов", value=format_resource_value(total_resource_value), inline=True)
        
        if civil_goods:
            total_civil_items = sum(civil_goods.values())
            embed.add_field(name="Гражданская продукция", value=f"Всего наименований: {len(civil_goods)}\nВсего единиц: {format_number(total_civil_items)}", inline=True)
        
        if "infrastructure_bonuses" in player_data:
            bonuses = player_data["infrastructure_bonuses"]
            power = bonuses.get('power', 0)
            research = bonuses.get('research', 1.0)
            gov_eff = bonuses.get('gov_efficiency', 0)
            pp_gain = bonuses.get('pp_gain', 0)
            
            infra_text = f"Энергия: {power} МВт\n"
            infra_text += f"Исследования: x{research:.2f}\n"
            infra_text += f"Эффективность: +{gov_eff:.0f}%\n"
            infra_text += f"Прирост ПВ: +{pp_gain:.2f}/день"
            
            embed.add_field(name="Инфраструктура", value=infra_text, inline=True)
        
        ground = army.get("ground", {})
        pvo_in_arsenal = []
        pvo_types = ["short_range_air_defense", "long_range_air_defense", "zdprk", "zas", "radar_systems"]
        
        for pvo_type in pvo_types:
            count = ground.get(pvo_type, 0)
            if count > 0:
                pvo_name = INFRASTRUCTURE_COSTS.get(pvo_type, {}).get("name", pvo_type)
                pvo_in_arsenal.append(f"{pvo_name}: {format_number(count)}")
        
        if pvo_in_arsenal:
            embed.add_field(name="ПВО в арсенале", value="\n".join(pvo_in_arsenal), inline=True)
        
        army_total = 0
        army_details = []
        
        if "ground" in army:
            ground_total = sum(army["ground"].values())
            army_total += ground_total
            if ground_total > 0:
                ground_items = []
                ground_names = {
                    "tanks": "Танки", "btr": "БТР", "bmp": "БМП", 
                    "armored_vehicles": "Бронеавто", "trucks": "Грузовики", "cars": "Авто",
                    "ew_vehicles": "РЭБ", "engineering_equipment": "Инж техника",
                    "radar_systems": "РЛС", "self_propelled_artillery": "САУ",
                    "towed_artillery": "Букс арт", "mlrs": "РСЗО",
                    "atgm_complexes": "ПТРК", "otr_complexes": "ОТРК",
                    "zas": "ЗАС", "zdprk": "ЗПРК",
                    "short_range_air_defense": "ПВО бл", "long_range_air_defense": "ПВО дал"
                }
                for key, name in ground_names.items():
                    if key in army["ground"] and army["ground"][key] > 0:
                        ground_items.append(f"{name}: {format_number(army['ground'][key])}")
                
                if ground_items:
                    ground_text = f"Сухопутные ({format_number(ground_total)} ед.)\n"
                    ground_text += "\n".join(ground_items)
                    army_details.append(ground_text)
        
        if "air" in army:
            air_total = sum(army["air"].values())
            army_total += air_total
            if air_total > 0:
                air_items = []
                air_names = {
                    "fighters": "Истребители", "attack_aircraft": "Штурмовики",
                    "bombers": "Бомбардировщики", "transport_aircraft": "Трансп сам",
                    "attack_helicopters": "Ударн верт", "transport_helicopters": "Трансп верт",
                    "recon_uav": "Разв БПЛА", "attack_uav": "Ударн БПЛА",
                    "kamikaze_drones": "Дроны-камикадзе"
                }
                for key, name in air_names.items():
                    if key in army["air"] and army["air"][key] > 0:
                        air_items.append(f"{name}: {format_number(army['air'][key])}")
                
                if air_items:
                    air_text = f"Авиация ({format_number(air_total)} ед.)\n"
                    air_text += "\n".join(air_items)
                    army_details.append(air_text)
        
        if "navy" in army:
            navy_total = sum(army["navy"].values())
            army_total += navy_total
            if navy_total > 0:
                navy_items = []
                navy_names = {
                    "boats": "Катера", "corvettes": "Корветы",
                    "destroyers": "Эсминцы", "cruisers": "Крейсера",
                    "aircraft_carriers": "Авианосцы", "submarines": "Подлодки", "usv_attack": "Надводные дроны"
                }
                for key, name in navy_names.items():
                    if key in army["navy"] and army["navy"][key] > 0:
                        navy_items.append(f"{name}: {format_number(army['navy'][key])}")
                
                if navy_items:
                    navy_text = f"Флот ({format_number(navy_total)} ед.)\n"
                    navy_text += "\n".join(navy_items)
                    army_details.append(navy_text)
        
        if "missiles" in army:
            missiles_total = sum(army["missiles"].values())
            army_total += missiles_total
            if missiles_total > 0:
                missiles_items = []
                missiles_names = {
                    "strategic_nuclear": "Страт ядерное", "tactical_nuclear": "Такт ядерное",
                    "cruise_missiles": "Крылатые", "hypersonic_missiles": "Гиперзвук",
                    "ballistic_missiles": "Баллист"
                }
                for key, name in missiles_names.items():
                    if key in army["missiles"] and army["missiles"][key] > 0:
                        missiles_items.append(f"{name}: {format_number(army['missiles'][key])}")
                
                if missiles_items:
                    missiles_text = f"Ракеты ({format_number(missiles_total)} ед.)\n"
                    missiles_text += "\n".join(missiles_items)
                    army_details.append(missiles_text)
        
        if "equipment" in army:
            equip_total = sum(army["equipment"].values())
            army_total += equip_total
            if equip_total > 0:
                equip_items = []
                equip_names = {
                    "small_arms": "Стрелковое", "grenade_launchers": "Гранатометы",
                    "atgms": "ПТРК", "manpads": "ПЗРК",
                    "medical_equipment": "Медицина", "engineering_equipment_units": "Инж снаряж",
                    "fpv_drones": "FPV-дроны"
                }
                for key, name in equip_names.items():
                    if key in army["equipment"] and army["equipment"][key] > 0:
                        equip_items.append(f"{name}: {format_number(army['equipment'][key])}")
                
                if equip_items:
                    equip_text = f"Снаряжение ({format_number(equip_total)} ед.)\n"
                    equip_text += "\n".join(equip_items)
                    army_details.append(equip_text)
        
        embed.add_field(name=f"{EMOJIS['army']} Армия (личный состав)", value=f"{format_army_number(state['army_size'])} чел.", inline=True)
        embed.add_field(name=f"{EMOJIS['manpower']} Опытность", value=f"{state.get('army_experience', 50):.0f}%", inline=True)
        embed.add_field(name="Техники всего", value=f"{format_number(army_total)} ед.", inline=True)
        
        for detail in army_details[:3]:
            embed.add_field(name="─────────────", value=detail, inline=False)
        
        if len(army_details) > 3:
            for detail in army_details[3:6]:
                embed.add_field(name="─────────────", value=detail, inline=False)
        
        embed.add_field(name=f"{EMOJIS['social']} Счастье", value=f"{state['happiness']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['social']} Доверие", value=f"{state['trust']:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['zakon']} Эффективность", value=f"{player_data['government_efficiency']:.0f}%", inline=True)
        
        await ctx.send(embed=embed)


# ==================== КЛАСС ПОДТВЕРЖДЕНИЯ ПЕРЕВОДОВ ====================
class TransferConfirmView(View):
    def __init__(self, transfer_id, sender_id, receiver_id, transfer_type):
        super().__init__(timeout=300)
        self.transfer_id = transfer_id
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.transfer_type = transfer_type

    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message("Это не ваше подтверждение!", ephemeral=True)
            return

        transfers = load_transfers()
        
        transfer = None
        for t in transfers["active_transfers"]:
            if t["id"] == self.transfer_id:
                transfer = t
                break
        
        if not transfer:
            await interaction.response.send_message("Перевод не найден!", ephemeral=True)
            return
        
        if transfer["status"] != "pending":
            await interaction.response.send_message("Этот перевод уже обработан!", ephemeral=True)
            return
        
        states = load_states()
        
        sender_data = None
        receiver_data = None
        
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.sender_id):
                sender_data = data
            if data.get("assigned_to") == str(self.receiver_id):
                receiver_data = data
        
        if not sender_data or not receiver_data:
            await interaction.response.send_message("Ошибка загрузки данных игроков!", ephemeral=True)
            return
        
        migrate_player_resources(sender_data)
        migrate_player_resources(receiver_data)
        
        success = False
        error_msg = ""
        
        if self.transfer_type == "resource":
            resource = transfer["resource"]
            amount = transfer["amount"]
            
            if resource in sender_data.get("resources", {}):
                if sender_data["resources"][resource] >= amount:
                    sender_data["resources"][resource] -= amount
                    if "resources" not in receiver_data:
                        receiver_data["resources"] = {}
                    receiver_data["resources"][resource] = receiver_data["resources"].get(resource, 0) + amount
                    success = True
                else:
                    error_msg = "У отправителя недостаточно ресурса!"
            else:
                error_msg = "У отправителя нет такого ресурса!"
        
        elif self.transfer_type == "equipment":
            equip_type = transfer["equip_type"]
            amount = transfer["amount"]
            path = equip_type.split('.')
            
            current = sender_data.get("army", {})
            for key in path[:-1]:
                if key not in current:
                    error_msg = f"Категория {key} не найдена у отправителя!"
                    break
                current = current[key]
            
            if not error_msg:
                last_key = path[-1]
                if last_key in current and current[last_key] >= amount:
                    current[last_key] -= amount
                    
                    rec_current = receiver_data.get("army", {})
                    for key in path[:-1]:
                        if key not in rec_current:
                            rec_current[key] = {}
                        rec_current = rec_current[key]
                    
                    if last_key not in rec_current:
                        rec_current[last_key] = 0
                    rec_current[last_key] += amount
                    
                    if "army" not in receiver_data:
                        receiver_data["army"] = {}
                    
                    success = True
                else:
                    error_msg = "У отправителя недостаточно техники!"
        
        if success:
            transfer["status"] = "completed"
            transfer["completed_at"] = str(datetime.now())
            transfers["completed_transfers"].append(transfer)
            transfers["active_transfers"].remove(transfer)
            
            save_states(states)
            save_transfers(transfers)
            
            embed = discord.Embed(
                title="Перевод выполнен!",
                color=0x2b2d31
            )
            
            if self.transfer_type == "resource":
                embed.add_field(name="Ресурс", value=transfer["resource"], inline=True)
                embed.add_field(name="Количество", value=format_number(transfer["amount"]), inline=True)
            else:
                tech_name = EQUIPMENT_NAMES.get(transfer["equip_type"], transfer["equip_type"])
                embed.add_field(name="Техника", value=tech_name, inline=True)
                embed.add_field(name="Количество", value=format_number(transfer["amount"]), inline=True)
            
            embed.add_field(name="Отправитель", value=f"<@{self.sender_id}>", inline=True)
            embed.add_field(name="Получатель", value=f"<@{self.receiver_id}>", inline=True)
            
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(error_msg, ephemeral=True)

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message("Это не ваше подтверждение!", ephemeral=True)
            return

        transfers = load_transfers()
        
        for t in transfers["active_transfers"][:]:
            if t["id"] == self.transfer_id:
                t["status"] = "cancelled"
                t["cancelled_at"] = str(datetime.now())
                transfers["completed_transfers"].append(t)
                transfers["active_transfers"].remove(t)
                break
        
        save_transfers(transfers)
        
        embed = discord.Embed(
            title="Перевод отклонен",
            color=0x2b2d31
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ФОНДОВЫЕ ЗАДАЧИ ====================
async def fuel_consumption_loop(bot_instance):
    """Фоновая задача для потребления топлива электростанциями (раз в день)"""
    await bot_instance.wait_until_ready()
    while not bot_instance.is_closed():
        try:
            from production_effects import consume_fuel, apply_infrastructure_bonuses, check_fuel_availability
            from utils import load_states, save_states
            from datetime import datetime
            
            print(f"Ежедневная проверка потребления топлива: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            states = load_states()
            fuel_shortages = []
            
            for player_data in states["players"].values():
                if "assigned_to" not in player_data:
                    continue
                
                country_name = player_data["state"]["statename"]
                player_data = apply_infrastructure_bonuses(player_data, country_name)
                
                enough, message = check_fuel_availability(player_data)
                
                if not enough:
                    user_id = int(player_data["assigned_to"])
                    fuel_shortages.append((user_id, message))
                else:
                    consume_fuel(player_data, days=1)
            
            save_states(states)
            
            for user_id, message in fuel_shortages:
                try:
                    user = await bot_instance.fetch_user(user_id)
                    if user:
                        await user.send(f"Внимание! {message}\nВаши электростанции могут остановиться!")
                except:
                    pass
            
            if fuel_shortages:
                print(f"Обнаружена нехватка топлива у {len(fuel_shortages)} игроков")
            else:
                print("Ежедневное потребление топлива обработано")
            
            await asyncio.sleep(86400)
        except Exception as e:
            print(f"Ошибка в fuel_consumption_loop: {e}")
            await asyncio.sleep(86400)


# ==================== ЗАПУСК БОТА ====================
@bot.event
async def on_ready():
    print(f'Бот {bot.user} успешно запущен!')
    print(f'Загружено команд: {len(bot.commands)}')
    
    states = load_states()
    for player_data in states["players"].values():
        migrate_player_resources(player_data)
    
    save_states(states)
    
    await bot.add_cog(AdminCommands(bot))
    await bot.add_cog(GameCommands(bot))
    await bot.add_cog(ResetCommands(bot))
    await bot.add_cog(TransferRegionCog(bot))
    
    initialize_fleets()
    
    bot.loop.create_task(production_check_loop(bot))
    bot.loop.create_task(construction_check_loop(bot))
    bot.loop.create_task(political_power_update_loop(bot))
    bot.loop.create_task(civil_production_check_loop(bot))
    bot.loop.create_task(fuel_consumption_loop(bot))
    bot.loop.create_task(research_update_loop(bot))
    bot.loop.create_task(resource_extraction_loop(bot))
    bot.loop.create_task(corporation_production_loop(bot))
    bot.loop.create_task(mobilization_completion_loop(bot))
    bot.loop.create_task(game_time_update_loop(bot))
    bot.loop.create_task(satellite_maintenance_loop(bot))
    bot.loop.create_task(doctrines_completion_loop(bot))
    bot.loop.create_task(corruption_update_loop(bot))
    bot.loop.create_task(energy_update_loop(bot))
    bot.loop.create_task(maritime_trade_loop(bot))
    bot.loop.create_task(navy_update_loop(bot))
    
    print('Все коги успешно загружены!')
    await bot.change_presence(activity=discord.Game(name="!гайд - помощь | Экономический симулятор"))

@bot.event
async def on_command_error(ctx, error):
    import traceback
    import io
    
    tb = io.StringIO()
    traceback.print_exception(type(error), error, error.__traceback__, file=tb)
    tb_str = tb.getvalue()
    
    await ctx.send(f"```py\n{tb_str[:1900]}\n```")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

# bot.py - ОСНОВНОЙ ФАЙЛ БОТА (ПОЛНОСТЬЮ ИСПРАВЛЕННЫЙ)

import discord
from discord.ext import commands
from discord.ui import Button, View
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
from utils import format_billion, format_number, format_army_number, get_user_id, get_user_name, send_response, load_states, save_states, load_trades, save_trades, load_alliances, save_alliances, load_transfers, save_transfers

# Импорт модуля ВПК
from corp_store import show_corporations_menu, show_my_orders, collect_completed_orders, production_check_loop
from corp_store import EQUIPMENT_NAMES, PRODUCTION_SPEED, format_time

# Импорт модуля инфраструктуры
from infra_build import (
    show_infrastructure_menu, show_construction_projects,
    complete_construction_projects, construction_check_loop
)

# Импорт модуля сброса
from reset_to_original import ResetCommands

# Импорт модуля политической власти
from political_power import (
    show_political_power_menu, political_power_update_loop,
    get_political_power, spend_political_power, add_political_power, set_political_power,
    POLITICAL_LAWS, check_requirements, format_effects_description
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
from trade_tariffs import show_tariff_menu, TariffSystem, calculate_trade_with_tariffs, filter_corporations_by_tariffs, TariffManagementView

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

# Настройки бота
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# Файлы для хранения данных
STATES_FILE = 'states.json'
TRADES_FILE = 'trades.json'
ALLIANCES_FILE = 'alliances.json'
TRANSFERS_FILE = 'transfers.json'
TARIFFS_FILE = 'tariffs.json'

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
        
        # Импортные пошлины
        import_tariff_revenue = state_data.get("tariff_revenue", 0)
        
        # Экспортные пошлины
        export_tariff_revenue = state_data.get("export_tariff_revenue", 0)
        
        total_tariff_revenue = import_tariff_revenue + export_tariff_revenue
        
        military_budget = economy.get("military_budget", 0)
        defense_spending = military_budget
        healthcare_spending = expenses.get("healthcare", 0)
        police_spending = expenses.get("police", 0)
        social_spending = expenses.get("social_security", 0)
        education_spending = expenses.get("education", 0)
        
        army_size = state.get("army_size", 0)
        army_upkeep = army_size * 10000
        
        debt = economy.get("debt", 0)
        debt_service = debt * 0.02
        
        total_expenses = (defense_spending + healthcare_spending + police_spending + 
                         social_spending + education_spending + army_upkeep + debt_service)
        
        total_revenue = tax_revenue + resource_revenue + total_tariff_revenue
        
        gdp = economy.get("gdp", 0)
        deficit = total_revenue - total_expenses
        
        max_deficit = gdp * 0.03
        if abs(deficit) > max_deficit:
            deficit = max_deficit if deficit > 0 else -max_deficit
        
        old_budget = economy.get("budget", 0)
        new_budget = old_budget + deficit
        
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
        
        military_budget = economy.get("military_budget", 0)
        gdp = economy.get("gdp", 1)
        stability = state.get("stability", 50)
        
        base_exp = 50
        budget_ratio = military_budget / gdp if gdp > 0 else 0
        budget_bonus = min(30, budget_ratio * 1000)
        stability_bonus = (stability - 50) / 2
        
        experience = base_exp + budget_bonus + stability_bonus
        return max(20, min(100, experience))

# ==================== КНОПКИ ДЛЯ ГОСУДАРСТВА ====================
class StateButtons(View):
    def __init__(self, user_id, state_name, player_data):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.state_name = state_name
        self.player_data = player_data

    @discord.ui.button(label="Бюджет", style=discord.ButtonStyle.secondary)
    async def budget_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        economy = self.player_data["economy"]
        state = self.player_data["state"]
        
        embed = discord.Embed(
            title=f"Бюджет {state['statename']}",
            color=0x2b2d31
        )
        
        embed.add_field(name="Госбюджет", value=format_billion(economy['budget']), inline=True)
        embed.add_field(name="ВВП", value=format_billion(economy['gdp']), inline=True)
        embed.add_field(name="Госдолг", value=format_billion(economy['debt']), inline=True)
        
        if "taxes" in economy:
            tax_system = TaxSystem(self.player_data)
            revenue = tax_system.calculate_total_tax_revenue()
            embed.add_field(name="Налоговые поступления", value=format_billion(revenue['total']), inline=True)
            embed.add_field(name="Эфф. ставка", value=f"{revenue['effective_rate']:.1f}% ВВП", inline=True)
        else:
            embed.add_field(name="Налоговая ставка", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        
        if self.player_data.get("tariff_revenue", 0) > 0:
            embed.add_field(name="Таможенные сборы", value=format_billion(self.player_data["tariff_revenue"]), inline=True)
        
        embed.add_field(name="Инфляция", value=f"{economy['inflation']}%", inline=True)
        embed.add_field(name="Средняя зарплата", value=f"${economy['wage']:,.0f}", inline=True)
        embed.add_field(name="Военный бюджет", value=format_billion(economy['military_budget']), inline=True)
        embed.add_field(name="Стоимость жизни", value=f"{economy['cost_of_living']}", inline=True)
        
        debt_to_gdp = (economy['debt'] / economy['gdp']) * 100
        embed.add_field(name="Долг/ВВП", value=f"{debt_to_gdp:.1f}%", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Расходы", style=discord.ButtonStyle.secondary)
    async def expenses_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        economy = self.player_data["economy"]
        state_name = self.player_data["state"]["statename"]
        
        defense_spending = economy.get("military_budget", 0)
        expenses = self.player_data.get("expenses", {})
        healthcare_spending = expenses.get("healthcare", 0)
        police_spending = expenses.get("police", 0)
        social_spending = expenses.get("social_security", 0)
        education_spending = expenses.get("education", 0)
        
        total_expenses = defense_spending + healthcare_spending + police_spending + social_spending + education_spending
        budget_percentage = (total_expenses / economy["budget"]) * 100 if economy["budget"] > 0 else 0
        
        embed = discord.Embed(
            title=f"Расходы государства: {state_name}",
            description=f"Общий бюджет: {format_billion(economy['budget'])}",
            color=0x2b2d31
        )
        
        embed.add_field(name="Оборона", 
                       value=f"{format_billion(defense_spending)}\n({(defense_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Здравоохранение", 
                       value=f"{format_billion(healthcare_spending)}\n({(healthcare_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Полиция", 
                       value=f"{format_billion(police_spending)}\n({(police_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Соцобеспечение", 
                       value=f"{format_billion(social_spending)}\n({(social_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Образование", 
                       value=f"{format_billion(education_spending)}\n({(education_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Всего расходов", 
                       value=f"{format_billion(total_expenses)}\n({budget_percentage:.1f}% бюджета)", 
                       inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Армия", style=discord.ButtonStyle.secondary)
    async def army_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        army = self.player_data.get("army", {})
        state = self.player_data["state"]
        state_name = state["statename"]
        army_exp = state.get("army_experience", 50)
        
        embed = discord.Embed(
            title=f"Армия: {state_name}",
            description=f"**Личный состав: {format_army_number(state['army_size'])} чел.**\n"
                       f"**Средняя опытность: {army_exp:.0f}%**",
            color=0x2b2d31
        )
        
        # Сухопутные войска
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
        
        # Снаряжение
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
        
        # Военно-воздушные силы (включая дроны-камикадзе)
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
        
        # Военно-морской флот
        if "navy" in army and army["navy"]:
            navy = army["navy"]
            navy_text = ""
            navy_names = {
                "boats": "Катера", "corvettes": "Корветы", "destroyers": "Эсминцы",
                "cruisers": "Крейсера", "aircraft_carriers": "Авианосцы", "submarines": "Подводные лодки"
            }
            for key, name in navy_names.items():
                if key in navy and navy[key] > 0:
                    navy_text += f"{name}: {format_number(navy[key])}\n"
            if not navy_text:
                navy_text = "Нет флота"
            embed.add_field(name="Военно-морской флот", value=navy_text, inline=False)
        
        # Ракетное вооружение
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
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
    
        await show_mobilization_menu(interaction, self.user_id)

    @discord.ui.button(label="Инфраструктура", style=discord.ButtonStyle.secondary)
    async def infrastructure_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_infrastructure_menu(interaction)

    @discord.ui.button(label="Полит. власть", style=discord.ButtonStyle.secondary)
    async def political_power_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_political_power_menu(interaction, self.user_id)

    @discord.ui.button(label="Налоги", style=discord.ButtonStyle.secondary)
    async def taxes_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_tax_menu(interaction, self.user_id)

    @discord.ui.button(label="Таможня", style=discord.ButtonStyle.secondary)
    async def tariffs_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_tariff_menu(interaction, self.user_id)

    @discord.ui.button(label="Население", style=discord.ButtonStyle.secondary)
    async def population_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_population_menu(interaction, self.user_id)

    @discord.ui.button(label="Удары", style=discord.ButtonStyle.danger)
    async def strikes_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_strike_menu(interaction, self.user_id)

    @discord.ui.button(label="На главную", style=discord.ButtonStyle.secondary)
    async def home_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
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
        
        if "taxes" in economy:
            embed.add_field(name="Налоги", value="Многокомпонентная система\n!налоги для просмотра", inline=True)
        else:
            embed.add_field(name="Налог", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        
        embed.add_field(name="Армия", value=f"{format_army_number(state['army_size'])} чел.", inline=True)
        embed.add_field(name="Опытность", value=f"{state.get('army_experience', 50):.0f}%", inline=True)
        embed.add_field(name="Военный бюджет", value=format_billion(economy['military_budget']), inline=True)
        embed.add_field(name="Счастье", value=f"{state['happiness']}%", inline=True)
        embed.add_field(name="Доверие", value=f"{state['trust']}%", inline=True)
        embed.add_field(name="Эффективность", value=f"{self.player_data['government_efficiency']}%", inline=True)
        
        # Информация об альянсе - только для просмотра
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

# ==================== КЛАССЫ ДЛЯ ПОДТВЕРЖДЕНИЯ ПЕРЕВОДОВ ====================
class TransferConfirmView(View):
    def __init__(self, transfer_id, sender_id, receiver_id, transfer_type):
        super().__init__(timeout=300)
        self.transfer_id = transfer_id
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.transfer_type = transfer_type

    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message("❌ Это не ваше подтверждение!", ephemeral=True)
            return

        transfers = load_transfers()
        
        transfer = None
        for t in transfers["active_transfers"]:
            if t["id"] == self.transfer_id:
                transfer = t
                break
        
        if not transfer:
            await interaction.response.send_message("❌ Перевод не найден!", ephemeral=True)
            return
        
        if transfer["status"] != "pending":
            await interaction.response.send_message("❌ Этот перевод уже обработан!", ephemeral=True)
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
            await interaction.response.send_message("❌ Ошибка загрузки данных игроков!", ephemeral=True)
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
                    error_msg = "❌ У отправителя недостаточно ресурса!"
            else:
                error_msg = "❌ У отправителя нет такого ресурса!"
        
        elif self.transfer_type == "equipment":
            equip_type = transfer["equip_type"]
            amount = transfer["amount"]
            path = equip_type.split('.')
            
            current = sender_data.get("army", {})
            for key in path[:-1]:
                if key not in current:
                    error_msg = f"❌ Категория {key} не найдена у отправителя!"
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
                    error_msg = "❌ У отправителя недостаточно техники!"
        
        if success:
            transfer["status"] = "completed"
            transfer["completed_at"] = str(datetime.now())
            transfers["completed_transfers"].append(transfer)
            transfers["active_transfers"].remove(transfer)
            
            save_states(states)
            save_transfers(transfers)
            
            embed = discord.Embed(
                title="✅ Перевод выполнен!",
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

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message("❌ Это не ваше подтверждение!", ephemeral=True)
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
            title="❌ Перевод отклонен",
            color=0x2b2d31
        )
        await interaction.response.edit_message(embed=embed, view=None)

# ==================== КОМАНДА ГАЙД ====================
@bot.command(name='гайд')
async def guide(ctx):
    """Показать список всех команд"""
    embed = discord.Embed(
        title="📚 Гайд по командам бота",
        description="Все доступные команды для военно-политического симулятора",
        color=0x2b2d31
    )
    
    embed.add_field(
        name="👤 Основные команды",
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
        name="💰 Экономика",
        value="`!налоги` - Управление налоговой системой\n"
              "`!таможня` - Управление пошлинами и торговыми барьерами\n"
              "`!ресурсы` - Просмотр ресурсов\n"
              "`!центробанк` - Управление денежной массой, золотым резервом и долгом"
              "`!товары` - Просмотр гражданской продукции\n"
              "`!торговля [@игрок] [ресурс] [кол-во] [цена]` - Предложить сделку\n"
              "`!принять [ID]` - Принять торговое предложение\n"
              "`!мои_сделки` - Список моих активных сделок",
        inline=False
    )
    
    embed.add_field(
        name="🏭 Военно-промышленный комплекс",
        value="`!впк` - Открыть меню покупки техники у корпораций\n"
              "`!заказы` - Просмотреть активные заказы\n"
              "`!получить` - Забрать готовую технику\n"
              "`!производство` - Информация о времени производства",
        inline=False
    )
    
    embed.add_field(
        name="🏭 Гражданская продукция",
        value="`!гражданские` - Открыть меню покупки гражданской продукции\n"
              "`!гражданские_заказы` - Просмотреть активные заказы\n"
              "`!получить_гражданские` - Забрать готовую продукцию\n"
              "`!товары` - Просмотреть запасы гражданской продукции\n"
              "`!склады` - Просмотреть запасы гражданской продукции корпораций\n"
              "`!производство_корп` - Просмотреть производство продукции корпораций\n"
              "`!прогноз` - Просмотреть рынок гражданских корпораций",
        inline=False
    )
    
    embed.add_field(
        name="🏗️ Инфраструктура",
        value="`!инфраструктура` - Меню строительства объектов\n"
              "`!стройки` - Активные стройки\n"
              "`!стройки_завершить` - Забрать готовые объекты\n"
              "`!энергия` - Статус энергосистемы\n"
              "`!бонусы` - Бонусы от инфраструктуры",
        inline=False
    )
    
    embed.add_field(
        name="⛏️ Ресурсы",
        value="`!добыча` - Информация о добыче ресурсов\n"
              "`!ресурсы` - Просмотр текущих запасов",
        inline=False
    )
    
    embed.add_field(
        name="⚡ Политика",
        value="`!политвласть` - Управление политической властью и законами\n"
              "`!закон [название]` - Информация о конкретном законе\n"
              "`!политвласть_игрока [@игрок]` - Просмотр ПВ другого игрока",
        inline=False
    )
    
    embed.add_field(
        name="🔬 Исследования",
        value="`!технологии` - Меню технологий и исследований",
        inline=False
    )
    
    embed.add_field(
        name="⚔️ Военные действия",
        value="`!удары` - Нанесение ударов БПЛА и ракетами по военной инфраструктуре\n"
              "`!конфликты` - Список активных военных конфликтов\n"
              "`!война` - Статус ваших войн",
        inline=False
    )
    
    embed.add_field(
        name="🌐 Альянсы",
        value="`!альянсы` - Список всех альянсов\n"
              "`!альянс [название]` - Информация об альянсе\n"
              "*(Вступление в альянс только через администрацию)*",
        inline=False
    )
    
    embed.add_field(
        name="📦 Переводы между игроками",
        value="`!передать_ресурс [@игрок] [ресурс] [количество]` - Передать ресурс\n"
              "`!передать_технику [@игрок] [тип] [количество]` - Передать технику\n"
              "`!мои_переводы` - Список моих активных переводов\n"
              "`!принять_перевод [ID]` - Принять перевод по ID",
        inline=False
    )
    
    # Для обычных пользователей отправляем один embed
    if not ctx.author.guild_permissions.administrator:
        embed.set_footer(text="Для сделок используйте !торговля и !принять")
        await ctx.send(embed=embed)
        return
    
    # Для администраторов создаём второй embed с админ-командами
    await ctx.send(embed=embed)
    
    # Второй embed с админ-командами
    admin_embed = discord.Embed(
        title="⚙️ Административные команды",
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
              "`!сброс` - Сбросить все государства к исходным значениям\n"
              "`!сброс_полный` - ПОЛНЫЙ сброс (включая назначения игроков)",
        inline=False
    )
    
    admin_embed.add_field(
        name="⚔️ Управление войнами",
        value="`!начать_войну [страна1] [страна2] [причина]` - Начать войну\n"
              "`!закончить_войну [страна1] [страна2]` - Завершить войну",
        inline=False
    )
    
    admin_embed.add_field(
        name="⛏️ Управление ресурсами",
        value="`!форс_добыча [@игрок]` - Принудительно запустить добычу ресурсов",
        inline=False
    )
    
    admin_embed.add_field(
        name="Диагностика",
        value="`!проверка_армии` - Диагностика структуры армии\n"
              "`!проверка_заказов` - Проверка очереди заказов",
        inline=False
    )
    
    admin_embed.add_field(
        name="Добавление ресурсов",
        value="`!добавить_технику [@игрок] [тип] [количество]` - Добавить технику\n"
              "`!админ_пв [@игрок] [set/add/remove] [кол-во]` - Изменить ПВ\n"
              "`!админ_ресурсы [@игрок] [set/add/remove] [ресурс] [кол-во]` - Изменить ресурсы\n"
              "`!админ_техника [@игрок] [set/add/remove] [тип] [кол-во]` - Изменить технику\n"
              "`!админ_деньги [@игрок] [set/add/remove] [сумма]` - Изменить бюджет\n"
              "`!админ_все_ресурсы [@игрок]` - Показать все ресурсы игрока\n"
              "`!админ_товары [@игрок] [set/add/remove] [тип] [кол-во]` - Изменить гражданские товары",
        inline=False
    )
    
    admin_embed.add_field(
        name="Управление альянсами",
        value="`!альянс_добавить [@игрок] [название_альянса]` - Добавить игрока в альянс\n"
              "`!альянс_удалить [@игрок]` - Удалить игрока из альянса",
        inline=False
    )
    
    admin_embed.set_footer(text="Только для администраторов")
    await ctx.send(embed=admin_embed)

# ==================== АДМИНИСТРАТИВНЫЕ КОМАНДЫ ====================
class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.economy_calc = EconomyCalculator()

    @commands.command(name='назначить')
    @commands.has_permissions(administrator=True)
    async def assign_state(self, ctx, member: discord.Member, state_id: str):
        """Назначить игроку государство по ID"""
        states = load_states()
        
        if state_id not in states["players"]:
            await ctx.send(f"❌ Государство с ID {state_id} не найдено!")
            return
        
        for user_id, data in states["players"].items():
            if user_id != state_id and data.get("assigned_to") == str(member.id):
                await ctx.send(f"❌ Игрок {member.mention} уже имеет государство!")
                return
        
        states["players"][state_id]["assigned_to"] = str(member.id)
        states["players"][state_id]["assigned_at"] = str(datetime.now())
        
        save_states(states)
        
        state_name = states["players"][state_id]["state"]["statename"]
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"📝 **Админ {ctx.author.name}** назначил государство {state_name} игроку {member.name}")
        
        await ctx.send(f"✅ Игрок {member.mention} назначен лидером государства **{state_name}**!")

    @commands.command(name='снять')
    @commands.has_permissions(administrator=True)
    async def unassign_state(self, ctx, member: discord.Member):
        """Снять игрока с управления государством"""
        states = load_states()
        
        found = False
        for state_id, data in states["players"].items():
            if data.get("assigned_to") == str(member.id):
                state_name = data["state"]["statename"]
                del data["assigned_to"]
                if "assigned_at" in data:
                    del data["assigned_at"]
                found = True
                break
        
        if not found:
            await ctx.send(f"❌ У игрока {member.mention} нет назначенного государства!")
            return
        
        save_states(states)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"📝 **Админ {ctx.author.name}** снял игрока {member.name} с управления государством {state_name}")
        
        await ctx.send(f"✅ Игрок {member.mention} снят с управления государством!")

    @commands.command(name='список')
    @commands.has_permissions(administrator=True)
    async def list_states(self, ctx):
        """Показать список всех доступных государств"""
        states = load_states()
        
        embed = discord.Embed(
            title="🌍 Список государств",
            color=0x2b2d31
        )
        
        for state_id, data in states["players"].items():
            state_name = data["state"]["statename"]
            assigned = data.get("assigned_to")
            
            if assigned:
                try:
                    user = await self.bot.fetch_user(int(assigned))
                    status = f"✅ Занято: {user.name}"
                except:
                    status = "✅ Занято (пользователь не найден)"
            else:
                status = "❌ Свободно"
            
            embed.add_field(
                name=f"{state_name} (ID: {state_id})",
                value=status,
                inline=False
            )
        
        await ctx.send(embed=embed)

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
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
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
                await ctx.send(f"❌ Неверный путь: {key} не найден!")
                return
            current = current[key]
        
        last_key = keys[-1]
        if last_key not in current:
            await ctx.send(f"❌ Ключ {last_key} не найден!")
            return
        
        old_value = current[last_key]
        current[last_key] = val
        
        save_states(states)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"📊 **Админ {ctx.author.name}** изменил статистику {member.name}:\n"
                             f"`{path}`: `{old_value}` -> `{val}`")
        
        await ctx.send(f"✅ Статистика обновлена!")

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
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        state_name = user_state["state"]["statename"]
        
        filename = f"state_{member.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(user_state, f, ensure_ascii=False, indent=4)
        
        await ctx.send(f"📊 Статистика государства **{state_name}**:", file=discord.File(filename))
        os.remove(filename)

    @commands.command(name='год')
    @commands.has_permissions(administrator=True)
    async def year_update(self, ctx):
        """Провести годовой апдейт для всех государств"""
        states = load_states()
        results = []
        
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
            
            budget_result = self.economy_calc.calculate_annual_budget(player_data)
            
            player_data["economy"]["budget"] = budget_result["new_budget"]
            player_data["economy"]["debt"] = budget_result["new_debt"]
            
            gdp_growth = self.economy_calc.calculate_gdp_growth(player_data)
            player_data["economy"]["gdp"] = int(player_data["economy"]["gdp"] * (1 + gdp_growth/100))
            
            pop_growth = self.economy_calc.calculate_population_growth(player_data)
            player_data["state"]["population"] = max(1000, player_data["state"]["population"] + pop_growth)
            
            army_exp = self.economy_calc.calculate_army_experience(player_data)
            player_data["state"]["army_experience"] = int(army_exp)
            
            current_inflation = player_data["economy"]["inflation"]
            inflation_change = random.uniform(-0.5, 1.0)
            player_data["economy"]["inflation"] = max(0, min(30, current_inflation + inflation_change))
            
            wage_change = gdp_growth / 2
            player_data["economy"]["wage"] = int(player_data["economy"]["wage"] * (1 + wage_change/100))
            
            if player_data["economy"]["gdp"] > 0:
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
            
            # Сохраняем таможенные сборы в отчёт и обнуляем для нового года
            tariff_revenue = player_data.get("tariff_revenue", 0)
            player_data["tariff_revenue"] = 0  # Обнуляем для нового года
            
            # Экспортные пошлины
            export_tariff_revenue = player_data.get("export_tariff_revenue", 0)
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
                "tariff_revenue": tariff_revenue,
                "export_tariff_revenue": export_tariff_revenue
            })
        
        save_states(states)
        
        embed = discord.Embed(
            title="📅 Годовой апдейт завершен",
            description=f"Обработано государств: {len(results)}",
            color=0x2b2d31
        )
        
        for result in results[:10]:
            deficit_emoji = "✅" if result["deficit"] > 0 else "⚠️" if result["deficit"] < 0 else "⚖️"
            growth_emoji = "📈" if result["gdp_growth"] > 2 else "📊" if result["gdp_growth"] > 0 else "📉"
            
            budget_change = result["new_budget"] - result["old_budget"]
            budget_emoji = "📈" if budget_change > 0 else "📉" if budget_change < 0 else "⚖️"
            
            deficit_text = f"{deficit_emoji} Баланс: {format_billion(abs(result['deficit']))} ({result['deficit_percent']:.1f}% ВВП)"
            
            tariff_text = f"💰 Импортные пошлины: {format_billion(result['tariff_revenue'])}" if result['tariff_revenue'] > 0 else ""
            export_text = f"📤 Экспортные пошлины: {format_billion(result['export_tariff_revenue'])}" if result['export_tariff_revenue'] > 0 else ""
            
            total_tariff = result['tariff_revenue'] + result['export_tariff_revenue']
            total_tariff_text = f"💵 Всего таможенных сборов: {format_billion(total_tariff)}" if total_tariff > 0 else ""
            
            embed.add_field(
                name=f"{result['state_name']}",
                value=f"{deficit_text}\n"
                      f"{growth_emoji} Рост ВВП: {result['gdp_growth']:.1f}%\n"
                      f"👥 Население: {format_number(result['new_population'])} чел.\n"
                      f"{budget_emoji} Бюджет: {format_billion(result['new_budget'])}\n"
                      f"💰 Долг: {format_billion(result['new_debt'])}\n"
                      f"{tariff_text}\n"
                      f"{export_text}\n"
                      f"{total_tariff_text}",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"📅 **Админ {ctx.author.name}** провел годовой апдейт")

    @commands.command(name='проверка_армии')
    @commands.has_permissions(administrator=True)
    async def check_army(self, ctx, member: discord.Member = None):
        """Проверка структуры армии"""
        if member is None:
            member = ctx.author
            
        states = load_states()
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        army = player_data.get("army", {})
        state_name = player_data["state"]["statename"]
        
        embed = discord.Embed(
            title=f"🔍 Проверка армии: {state_name}",
            description=f"Игрок: {member.mention}",
            color=0x2b2d31
        )
        
        sections = {
            "ground": "Сухопутные войска",
            "equipment": "Снаряжение",
            "air": "Авиация",
            "navy": "Флот",
            "missiles": "Ракеты"
        }
        
        for section_key, section_name in sections.items():
            if section_key in army:
                section_data = army[section_key]
                if isinstance(section_data, dict):
                    total = sum(section_data.values())
                    items = list(section_data.items())[:5]
                    items_text = "\n".join([f"{k}: {v}" for k, v in items])
                    embed.add_field(
                        name=f"✅ {section_name} (всего: {format_number(total)})",
                        value=items_text or "Пусто",
                        inline=False
                    )
                else:
                    embed.add_field(name=f"❌ {section_name}", value="Неверный формат данных", inline=False)
            else:
                embed.add_field(name=f"❌ {section_name}", value="Отсутствует", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='проверка_заказов')
    @commands.has_permissions(administrator=True)
    async def check_orders(self, ctx):
        """Проверка очереди заказов"""
        from corp_store import load_production_queue, format_time
        
        queue = load_production_queue()
        
        embed = discord.Embed(
            title="📋 Очередь заказов",
            color=0x2b2d31
        )
        
        active = queue.get("active_orders", [])
        if active:
            active_text = ""
            for order in active[:5]:
                completion = datetime.fromisoformat(order["completion_time"])
                remaining = (completion - datetime.now()).total_seconds()
                active_text += f"• #{order['id']}: {order['product_name']} x{order['quantity']} - готов через {format_time(max(0, remaining))}\n"
            embed.add_field(name=f"✅ Активные заказы ({len(active)})", value=active_text or "Нет", inline=False)
        else:
            embed.add_field(name="✅ Активные заказы", value="Нет активных заказов", inline=False)
        
        completed = queue.get("completed_orders", [])
        if completed:
            completed_text = ""
            for order in completed[-5:]:
                completed_text += f"• #{order['id']}: {order['product_name']} x{order['quantity']}\n"
            embed.add_field(name=f"✅ Завершенные заказы ({len(completed)})", value=completed_text or "Нет", inline=False)
        else:
            embed.add_field(name="✅ Завершенные заказы", value="Нет завершенных заказов", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='добавить_технику')
    @commands.has_permissions(administrator=True)
    async def add_equipment(self, ctx, member: discord.Member, equip_type: str, amount: int):
        """Принудительно добавить технику игроку"""
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        path = equip_type.split('.')
        
        if "army" not in player_data:
            player_data["army"] = {}
        
        current = player_data["army"]
        
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        last_key = path[-1]
        old_value = current.get(last_key, 0)
        current[last_key] = old_value + amount
        
        save_states(states)
        
        await ctx.send(f"✅ Добавлено {amount} {equip_type} игроку {member.mention}. Было: {old_value}, стало: {current[last_key]}")

    @commands.command(name='админ_пв')
    @commands.has_permissions(administrator=True)
    async def admin_political_power(self, ctx, member: discord.Member, operation: str, amount: float):
        """Изменить политическую власть"""
        from political_power import get_political_power, set_political_power, add_political_power, spend_political_power
        
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        operation = operation.lower()
        current_pp = get_political_power(player_data)
        old_value = current_pp
        
        if operation == "set":
            new_value = max(0, amount)
            set_political_power(player_data, new_value)
            result_text = f"установлено на {new_value:.1f}"
        elif operation == "add":
            result, added = add_political_power(player_data, amount)
            result_text = f"увеличено на {added:.1f}"
        elif operation == "remove":
            success, new_value = spend_political_power(player_data, amount)
            if success:
                result_text = f"уменьшено на {amount:.1f}"
            else:
                await ctx.send(f"❌ Нельзя уменьшить ПВ ниже 0! Текущее значение: {current_pp:.1f}")
                return
        else:
            await ctx.send("❌ Неверная операция! Используйте set/add/remove")
            return
        
        save_states(states)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"⚡ **Админ {ctx.author.name}** изменил ПВ игрока {member.name}: {old_value:.1f} -> {get_political_power(player_data):.1f}")
        
        await ctx.send(f"✅ Политическая власть игрока {member.mention} {result_text}. Было: {old_value:.1f}, стало: {get_political_power(player_data):.1f}")

    @commands.command(name='админ_ресурсы')
    @commands.has_permissions(administrator=True)
    async def admin_resources(self, ctx, member: discord.Member, operation: str, resource: str, amount: int):
        """Изменить ресурсы"""
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(player_data)
        
        if resource not in RESOURCE_PRICES:
            await ctx.send(f"❌ Неизвестный ресурс: {resource}. Доступные: {', '.join(RESOURCE_PRICES.keys())}")
            return
        
        current_value = player_data.get("resources", {}).get(resource, 0)
        operation = operation.lower()
        
        if operation == "set":
            new_value = max(0, amount)
            player_data["resources"][resource] = new_value
            result_text = f"установлено на {format_number(new_value)}"
        elif operation == "add":
            new_value = current_value + amount
            if "resources" not in player_data:
                player_data["resources"] = {}
            player_data["resources"][resource] = new_value
            result_text = f"увеличено на {format_number(amount)}"
        elif operation == "remove":
            if current_value < amount:
                await ctx.send(f"❌ Недостаточно ресурса! Доступно: {format_number(current_value)}")
                return
            new_value = current_value - amount
            player_data["resources"][resource] = new_value
            result_text = f"уменьшено на {format_number(amount)}"
        else:
            await ctx.send("❌ Неверная операция! Используйте set/add/remove")
            return
        
        save_states(states)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"⛏️ **Админ {ctx.author.name}** изменил ресурсы игрока {member.name}: {resource} {format_number(current_value)} -> {format_number(new_value)}")
        
        await ctx.send(f"✅ Ресурс {resource} игрока {member.mention} {result_text}. Было: {format_number(current_value)}, стало: {format_number(new_value)}")

    @commands.command(name='админ_техника')
    @commands.has_permissions(administrator=True)
    async def admin_equipment(self, ctx, member: discord.Member, operation: str, equip_type: str, amount: int):
        """Изменить технику"""
        from corp_store import EQUIPMENT_NAMES
        
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        path = equip_type.split('.')
        
        if "army" not in player_data:
            player_data["army"] = {}
        
        current = player_data["army"]
        
        for key in path[:-1]:
            if key not in current:
                if operation != "set":
                    await ctx.send(f"❌ Категория {key} не найдена!")
                    return
                current[key] = {}
            current = current[key]
        
        last_key = path[-1]
        current_value = current.get(last_key, 0)
        operation = operation.lower()
        
        tech_name = EQUIPMENT_NAMES.get(equip_type, last_key)
        
        if operation == "set":
            new_value = max(0, amount)
            current[last_key] = new_value
            result_text = f"установлено на {format_number(new_value)}"
        elif operation == "add":
            new_value = current_value + amount
            current[last_key] = new_value
            result_text = f"увеличено на {format_number(amount)}"
        elif operation == "remove":
            if current_value < amount:
                await ctx.send(f"❌ Недостаточно техники! Доступно: {format_number(current_value)} {tech_name}")
                return
            new_value = current_value - amount
            current[last_key] = new_value
            result_text = f"уменьшено на {format_number(amount)}"
        else:
            await ctx.send("❌ Неверная операция! Используйте set/add/remove")
            return
        
        save_states(states)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"⚔️ **Админ {ctx.author.name}** изменил технику игрока {member.name}: {tech_name} {format_number(current_value)} -> {format_number(new_value)}")
        
        await ctx.send(f"✅ Техника {tech_name} игрока {member.mention} {result_text}. Было: {format_number(current_value)}, стало: {format_number(new_value)}")

    @commands.command(name='админ_деньги')
    @commands.has_permissions(administrator=True)
    async def admin_money(self, ctx, member: discord.Member, operation: str, amount: int):
        """Изменить бюджет"""
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        current_budget = player_data["economy"]["budget"]
        operation = operation.lower()
        
        if operation == "set":
            new_budget = max(0, amount)
            player_data["economy"]["budget"] = new_budget
            result_text = f"установлен на {format_billion(new_budget)}"
        elif operation == "add":
            new_budget = current_budget + amount
            player_data["economy"]["budget"] = new_budget
            result_text = f"увеличен на {format_billion(amount)}"
        elif operation == "remove":
            if current_budget < amount:
                await ctx.send(f"❌ Недостаточно средств! Доступно: {format_billion(current_budget)}")
                return
            new_budget = current_budget - amount
            player_data["economy"]["budget"] = new_budget
            result_text = f"уменьшен на {format_billion(amount)}"
        else:
            await ctx.send("❌ Неверная операция! Используйте set/add/remove")
            return
        
        save_states(states)
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"💰 **Админ {ctx.author.name}** изменил бюджет игрока {member.name}: {format_billion(current_budget)} -> {format_billion(new_budget)}")
        
        await ctx.send(f"✅ Бюджет игрока {member.mention} {result_text}. Было: {format_billion(current_budget)}, стало: {format_billion(new_budget)}")

    @commands.command(name='админ_все_ресурсы')
    @commands.has_permissions(administrator=True)
    async def admin_all_resources(self, ctx, member: discord.Member):
        """Показать все ресурсы игрока"""
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(player_data)
        
        resources = player_data.get("resources", {})
        state_name = player_data["state"]["statename"]
        
        embed = discord.Embed(
            title=f"📊 Ресурсы игрока {member.name} ({state_name})",
            description="Для изменения используйте `!админ_ресурсы`",
            color=0x2b2d31
        )
        
        total_value = 0
        resource_list = []
        
        for resource, amount in resources.items():
            if resource in RESOURCE_PRICES and amount > 0:
                value = calculate_resource_value(resource, amount)
                total_value += value
                resource_list.append(f"{resource}: {format_number(amount)} ({format_resource_value(value)})")
        
        if resource_list:
            embed.add_field(name="Ресурсы", value="\n".join(resource_list[:10]), inline=False)
            if len(resource_list) > 10:
                embed.add_field(name="Итого", value=f"Общая стоимость: {format_resource_value(total_value)}", inline=False)
        else:
            embed.add_field(name="Ресурсы", value="Нет ресурсов", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='форс_добыча')
    @commands.has_permissions(administrator=True)
    async def force_extraction_cmd(self, ctx, member: discord.Member = None):
        """Принудительно запустить добычу ресурсов"""
        if member:
            await force_extraction(ctx, member.id)
        else:
            await force_extraction(ctx)

    @commands.command(name='админ_товары')
    @commands.has_permissions(administrator=True)
    async def admin_civil_goods(self, ctx, member: discord.Member, operation: str, product_type: str, amount: int):
        """Изменить гражданские товары"""
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        if "civil_goods" not in player_data:
            player_data["civil_goods"] = {}
        
        if product_type not in CIVIL_PRODUCT_NAMES:
            await ctx.send(f"❌ Неизвестный тип продукции: {product_type}. Доступные: {', '.join(CIVIL_PRODUCT_NAMES.keys())}")
            return
        
        current_value = player_data["civil_goods"].get(product_type, 0)
        operation = operation.lower()
        
        if operation == "set":
            new_value = max(0, amount)
            player_data["civil_goods"][product_type] = new_value
            result_text = f"установлено на {format_number(new_value)}"
        elif operation == "add":
            new_value = current_value + amount
            player_data["civil_goods"][product_type] = new_value
            result_text = f"увеличено на {format_number(amount)}"
        elif operation == "remove":
            if current_value < amount:
                await ctx.send(f"❌ Недостаточно продукции! Доступно: {format_number(current_value)}")
                return
            new_value = current_value - amount
            player_data["civil_goods"][product_type] = new_value
            result_text = f"уменьшено на {format_number(amount)}"
        else:
            await ctx.send("❌ Неверная операция! Используйте set/add/remove")
            return
        
        save_states(states)
        
        product_name = CIVIL_PRODUCT_NAMES.get(product_type, product_type)
        await ctx.send(f"✅ Продукция {product_name} игрока {member.mention} {result_text}. Было: {format_number(current_value)}, стало: {format_number(new_value)}")

    # ==================== НОВЫЕ АДМИН КОМАНДЫ ДЛЯ ВОЙН ====================
    @commands.command(name='начать_войну')
    @commands.has_permissions(administrator=True)
    async def admin_start_war(self, ctx, country1: str, country2: str, *, reason: str = ""):
        """Начать войну между двумя странами"""
        from conflicts import admin_start_war
        
        if admin_start_war(country1, country2, reason):
            embed = discord.Embed(
                title="⚔️ Война объявлена!",
                description=f"**{country1}** объявляет войну **{country2}**",
                color=discord.Color.red()
            )
            if reason:
                embed.add_field(name="Причина", value=reason, inline=False)
            
            await ctx.send(embed=embed)
            
            # Логирование
            channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"⚔️ **Админ {ctx.author.name}** начал войну между {country1} и {country2}")
        else:
            await ctx.send("❌ Не удалось начать войну. Возможно, они уже воюют?")
    
    @commands.command(name='закончить_войну')
    @commands.has_permissions(administrator=True)
    async def admin_end_war(self, ctx, country1: str, country2: str):
        """Завершить войну между двумя странами"""
        from conflicts import admin_end_war
        
        if admin_end_war(country1, country2):
            embed = discord.Embed(
                title="🕊️ Мир заключён!",
                description=f"Война между **{country1}** и **{country2}** завершена",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            
            channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"🕊️ **Админ {ctx.author.name}** завершил войну между {country1} и {country2}")
        else:
            await ctx.send("❌ Не удалось завершить войну. Возможно, они не воюют?")

    # ==================== НОВЫЕ АДМИН КОМАНДЫ ДЛЯ АЛЬЯНСОВ ====================
    @commands.command(name='альянс_добавить')
    @commands.has_permissions(administrator=True)
    async def alliance_add(self, ctx, member: discord.Member, *, alliance_name: str):
        """Добавить игрока в альянс"""
        player_data = None
        for data in load_states()["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        alliances = load_alliances()
        
        # Находим альянс
        alliance = None
        for a in alliances["alliances"]:
            if a["name"].lower() == alliance_name.lower():
                alliance = a
                break
        
        if not alliance:
            await ctx.send(f"❌ Альянс '{alliance_name}' не найден!")
            return
        
        # Проверяем, не состоит ли уже
        for a in alliances["alliances"]:
            if str(member.id) in a.get("members", []):
                await ctx.send(f"❌ Игрок {member.mention} уже состоит в альянсе {a['name']}!")
                return
        
        if "members" not in alliance:
            alliance["members"] = []
        
        alliance["members"].append(str(member.id))
        save_alliances(alliances)
        
        await ctx.send(f"✅ Игрок {member.mention} добавлен в альянс **{alliance['name']}**!")
        
        # Логирование
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"🌐 **Админ {ctx.author.name}** добавил игрока {member.name} в альянс {alliance['name']}")

    @commands.command(name='альянс_удалить')
    @commands.has_permissions(administrator=True)
    async def alliance_remove(self, ctx, member: discord.Member):
        """Удалить игрока из текущего альянса"""
        alliances = load_alliances()
        
        found = False
        alliance_name = ""
        for alliance in alliances["alliances"]:
            if str(member.id) in alliance.get("members", []):
                alliance["members"].remove(str(member.id))
                alliance_name = alliance["name"]
                found = True
                break
        
        if not found:
            await ctx.send(f"❌ Игрок {member.mention} не состоит ни в одном альянсе!")
            return
        
        save_alliances(alliances)
        
        await ctx.send(f"✅ Игрок {member.mention} удален из альянса **{alliance_name}**!")
        
        channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
        if channel:
            await channel.send(f"🌐 **Админ {ctx.author.name}** удалил игрока {member.name} из альянса {alliance_name}")

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
            await ctx.send("❌ У вас нет государства! Обратитесь к администрации.")
            return
        
        state = player_data["state"]
        politics = player_data["politics"]
        economy = player_data["economy"]
        
        embed = discord.Embed(
            title=f"{state['statename']}",
            description=f"Лидер: {ctx.author.mention}",
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
        embed.add_field(name="Эффективность", value=f"{player_data['government_efficiency']}%", inline=True)
        
        alliance = self.get_player_alliance(ctx.author.id)
        if alliance:
            embed.add_field(name="Альянс", value=f"{alliance['name']} (участник)", inline=True)
        
        view = StateButtons(ctx.author.id, state['statename'], player_data)
        await ctx.send(embed=embed, view=view)

    @commands.command(name='политвласть')
    async def political_power(self, ctx):
        """Показать меню политической власти"""
        from political_power import show_political_power_menu
        await show_political_power_menu(ctx, ctx.author.id)

    @commands.command(name='политвласть_игрока')
    async def political_power_player(self, ctx, member: discord.Member):
        """Показать политическую власть другого игрока"""
        from political_power import show_political_power_menu
        
        player_data = self.get_player_state(member.id)
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        await show_political_power_menu(ctx, member.id)

    @commands.command(name='технологии')
    async def research(self, ctx):
        """Показать меню технологий и исследований"""
        from research import show_research_menu
        await show_research_menu(ctx, ctx.author.id)

    @commands.command(name='налоги')
    async def taxes(self, ctx):
        """Показать меню налоговой системы"""
        await show_tax_menu(ctx, ctx.author.id)

    @commands.command(name='таможня')
    async def tariffs(self, ctx):
        """Показать меню таможенных пошлин"""
        await show_tariff_menu(ctx, ctx.author.id)

    @commands.command(name='налоги_игрока')
    async def taxes_player(self, ctx, member: discord.Member):
        """Показать налоговую систему другого игрока"""
        player_data = self.get_player_state(member.id)
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        await show_tax_menu(ctx, member.id)

    @commands.command(name='центробанк')
    async def central_bank(self, ctx):
        """Показать меню центрального банка"""
        await show_central_bank_menu(ctx, ctx.author.id)

    @commands.command(name='ресурсы')
    async def resources(self, ctx):
        """Просмотр ресурсов государства"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("❌ У вас нет государства!")
            return
        
        migrate_player_resources(player_data)
        
        country_name = player_data["state"]["statename"]
        player_data = apply_infrastructure_bonuses(player_data, country_name)
        
        states = load_states()
        for pid, data in states["players"].items():
            if data.get("assigned_to") == str(ctx.author.id):
                states["players"][pid] = player_data
                break
        save_states(states)
        
        resources = player_data.get("resources", {})
        state_name = player_data["state"]["statename"]
        
        embed = create_resource_embed(resources, f"Ресурсы: {state_name}")
        await ctx.send(embed=embed)

    @commands.command(name='товары')
    async def civil_goods(self, ctx):
        """Просмотр гражданской продукции"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("❌ У вас нет государства!")
            return
        
        await show_civil_goods(ctx)

    @commands.command(name='склады')
    async def corporation_warehouses(self, ctx):
        """Показать склады корпораций в вашей стране"""
        from civil_corporations_db import get_civil_corporations_by_country, CIVIL_PRODUCT_NAMES, load_corporations_state
        from utils import format_number, DARK_THEME_COLOR
        
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("❌ У вас нет государства!")
            return

        country_name = player_data["state"]["statename"]
        local_corps = list(get_civil_corporations_by_country(country_name).values())
        corps_state = load_corporations_state()

        embed = discord.Embed(
            title=f"📦 Склады корпораций: {country_name}",
            description="Товары, доступные для покупки населением",
            color=DARK_THEME_COLOR
        )

        total_inventory = 0
        corps_with_stock = 0

        for corp in local_corps[:10]:  # Показываем первые 10
            if corp.id in corps_state["corporations"]:
                state = corps_state["corporations"][corp.id]
                inventory = state.inventory

                if inventory:
                    corps_with_stock += 1
                    inv_text = ""
                    for product, amount in list(inventory.items())[:3]:
                        if amount > 0:
                            product_name = CIVIL_PRODUCT_NAMES.get(product, product)
                            inv_text += f"• {product_name}: {format_number(amount)}\n"
                            total_inventory += amount

                    if inv_text:
                        embed.add_field(
                            name=f"{corp.name} (бюджет: ${state.budget:,.0f})",
                            value=inv_text,
                            inline=False
                        )

        embed.add_field(
            name="📊 Итого",
            value=f"Корпораций с товарами: {corps_with_stock}\n"
                  f"Всего единиц товара: {format_number(total_inventory)}",
            inline=False
        )

        await ctx.send(embed=embed)

    @commands.command(name='производство_корп')
    async def corporation_production_status(self, ctx):
        """Показать статус производства корпораций"""
        from civil_corporations_db import CIVIL_PRODUCT_NAMES
        from utils import DARK_THEME_COLOR
        
        try:
            from corporation_production import PRODUCTION_RATES
        except ImportError:
            await ctx.send("❌ Модуль производства не найден. Убедитесь, что файл corporation_production.py существует.")
            return

        embed = discord.Embed(
            title="🏭 Производство корпораций",
            description="Скорость производства (единиц в день)",
            color=DARK_THEME_COLOR
        )

        categories = {
            "🍔 Продукты": ["food_products", "beverages", "restaurants", "fast_food"],
            "👕 Товары": ["clothing", "footwear", "household_goods", "furniture", "cosmetics"],
            "📱 Электроника": ["consumer_electronics", "computers", "smartphones", "tablets"],
            "🏭 Промышленность": ["cars", "trucks", "buses", "agricultural_machinery", "construction_machinery", "industrial_equipment", "machine_tools"],
            "💊 Фармацевтика": ["pharmaceuticals", "medical_supplies"],
            "📡 Услуги": ["telecom_services", "internet_services", "banking", "streaming", "software"]
        }

        for category, products in categories.items():
            text = ""
            for product in products:
                if product in PRODUCTION_RATES:
                    rate = PRODUCTION_RATES[product]
                    name = CIVIL_PRODUCT_NAMES.get(product, product)
                    text += f"• {name}: {rate}/день\n"
            if text:
                embed.add_field(name=category, value=text, inline=True)

        await ctx.send(embed=embed)

    @commands.command(name='прогноз')
    async def consumption_forecast(self, ctx):
        """Показать прогноз потребления товаров и услуг"""
        await show_consumption_forecast(ctx, ctx.author.id)

    @commands.command(name='мобилизация')
    async def mobilization(self, ctx):
        """Меню мобилизации гражданской промышленности"""
        await show_mobilization_menu(ctx, ctx.author.id)

    @commands.command(name='население')
    async def population(self, ctx):
        """Показать информацию о населении"""
        await show_population_menu(ctx, ctx.author.id)

    @commands.command(name='энергия')
    async def power_status(self, ctx):
        """Показать статус энергосистемы"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("❌ У вас нет государства!")
            return
        
        country_name = player_data["state"]["statename"]
        player_data = apply_infrastructure_bonuses(player_data, country_name)
        
        states = load_states()
        for pid, data in states["players"].items():
            if data.get("assigned_to") == str(ctx.author.id):
                states["players"][pid] = player_data
                break
        save_states(states)
        
        status = get_power_status(player_data)
        
        embed = discord.Embed(
            title=f"⚡ Энергосистема: {player_data['state']['statename']}",
            description=status,
            color=0x2b2d31
        )
        
        enough, message = check_fuel_availability(player_data)
        if enough:
            embed.add_field(name="✅ Статус", value="Топлива достаточно", inline=False)
        else:
            embed.add_field(name="⚠️ Проблема", value=message, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='бонусы')
    async def infrastructure_bonuses(self, ctx):
        """Показать бонусы от инфраструктуры"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("❌ У вас нет государства!")
            return
        
        country_name = player_data["state"]["statename"]
        player_data = apply_infrastructure_bonuses(player_data, country_name)
        
        states = load_states()
        for pid, data in states["players"].items():
            if data.get("assigned_to") == str(ctx.author.id):
                states["players"][pid] = player_data
                break
        save_states(states)
        
        bonuses = player_data.get("infrastructure_bonuses", {})
        production = bonuses.get("production", {})
        
        embed = discord.Embed(
            title=f"🏭 Инфраструктурные бонусы: {player_data['state']['statename']}",
            color=0x2b2d31
        )
        
        if production:
            prod_text = ""
            for prod, bonus in production.items():
                prod_text += f"• {prod}: x{bonus:.2f} скорость\n"
            embed.add_field(name="⚡ Производство", value=prod_text, inline=False)
        
        power = bonuses.get("power", 0)
        embed.add_field(name="⚡ Энергия", value=f"{power} МВт", inline=True)
        
        research = bonuses.get("research", 1.0)
        embed.add_field(name="📈 Исследования", value=f"x{research:.2f}", inline=True)
        
        gov_eff = bonuses.get("gov_efficiency", 0)
        embed.add_field(name="🏛️ Эффективность", value=f"+{gov_eff:.0f}%", inline=True)
        
        pp_gain = bonuses.get("pp_gain", 0)
        embed.add_field(name="⚡ Прирост ПВ", value=f"+{pp_gain:.2f}/день", inline=True)
        
        storage = bonuses.get("storage", {})
        if storage:
            storage_text = ""
            for res, amount in storage.items():
                storage_text += f"• {res}: +{amount}\n"
            embed.add_field(name="📦 Доп. хранилища", value=storage_text, inline=False)
        
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
    
        # Названия месяцев
        month_names = [
            "январь", "февраль", "март", "апрель", "май", "июнь",
            "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"
        ]
    
        embed = discord.Embed(
            title="📅 Игровой календарь",
            color=DARK_THEME_COLOR
        )
    
        embed.add_field(name="Текущая дата", value=game_date, inline=True)
        embed.add_field(name="Время года", value=season.capitalize(), inline=True)
        embed.add_field(name="Месяц", value=month_names[month-1], inline=True)
    
        # Сезонные эффекты (для информации)
        season_effects = {
            "весна": "🌱",
            "лето": "☀️",
            "осень": "🍂",
            "зима": "❄️"
        }
    
        embed.add_field(
            name="Сезон",
            value=season_effects.get(season, "Обычный сезон"),
            inline=False
        )
    
        embed.set_footer(text=f"Старт: 1 декабря 2022 года | 1 год = 3 дня | 1 месяц = 8 часов")
    
        await ctx.send(embed=embed)

    @commands.command(name='спутники')
    async def satellites(self, ctx):
        """Управление спутниковой группировкой"""
        await show_satellite_menu(ctx, ctx.author.id)

    @commands.command(name='доктрины')
    async def doctrines(self, ctx):
        """Военные доктрины и тактики"""
        await show_doctrines_menu(ctx, ctx.author.id)

    @commands.command(name='добыча')
    async def extraction(self, ctx):
        """Показать информацию о добыче ресурсов"""
        await show_extraction_info(ctx, ctx.author.id)

    @commands.command(name='закон')
    async def law_info(self, ctx, *, law_name: str):
        """Показать информацию о законе"""
        from political_power import POLITICAL_LAWS, check_requirements, format_effects_description, get_political_power
        
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("❌ У вас нет государства!")
            return
        
        found_law = None
        for law_id, law in POLITICAL_LAWS.items():
            if law_name.lower() in law.name.lower():
                found_law = law
                break
        
        if not found_law:
            await ctx.send(f"❌ Закон '{law_name}' не найден!")
            return
        
        check_result, check_message = await check_requirements(player_data, found_law, silent=True)
        current_pp = get_political_power(player_data)
        
        embed = discord.Embed(
            title=f"📜 {found_law.name}",
            description=found_law.description,
            color=0x2b2d31
        )
        
        embed.add_field(name="💰 Стоимость", value=f"{found_law.pp_cost} ПВ", inline=True)
        embed.add_field(name="📊 Тип", value=found_law.law_type, inline=True)
        embed.add_field(name="⏱️ Перезарядка", value=f"{found_law.cooldown_days} дней", inline=True)
        
        if found_law.requirements:
            req_text = ""
            if "min_stability" in found_law.requirements:
                req_text += f"• Стабильность: {found_law.requirements['min_stability']}%\n"
            if "min_popularity" in found_law.requirements:
                req_text += f"• Популярность: {found_law.requirements['min_popularity']}%\n"
            if "min_budget" in found_law.requirements:
                req_text += f"• Бюджет: {format_billion(found_law.requirements['min_budget'])}\n"
            if "max_tax" in found_law.requirements:
                req_text += f"• Макс. налог: {found_law.requirements['max_tax']}%\n"
            if "min_tax" in found_law.requirements:
                req_text += f"• Мин. налог: {found_law.requirements['min_tax']}%\n"
            embed.add_field(name="📋 Требования", value=req_text, inline=True)
        
        effects_text = format_effects_description(found_law.effects)
        if effects_text:
            embed.add_field(name="✨ Эффекты", value=effects_text, inline=False)
        
        if check_result and current_pp >= found_law.pp_cost:
            embed.add_field(name="✅ Доступен", value="Вы можете внести этот закон в парламент", inline=False)
        else:
            issues = []
            if not check_result:
                issues.append(check_message)
            if current_pp < found_law.pp_cost:
                issues.append(f"Недостаточно ПВ (нужно {found_law.pp_cost}, у вас {current_pp:.1f})")
            embed.add_field(name="❌ Недоступен", value="\n".join(issues), inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='торговля')
    async def trade(self, ctx, member: discord.Member, resource: str, amount: int, price: int):
        """
        Предложить сделку другому игроку
        Использование: !торговля @игрок [ресурс] [количество] [цена в тыс.$]
        """
        if member.id == ctx.author.id:
            await ctx.send("❌ Нельзя торговать с самим собой!")
            return
        
        if amount <= 0 or price <= 0:
            await ctx.send("❌ Количество и цена должны быть положительными!")
            return
        
        if resource not in RESOURCE_PRICES:
            await ctx.send(f"❌ Неизвестный ресурс! Доступные: {', '.join(RESOURCE_PRICES.keys())}")
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
            await ctx.send("❌ У вас нет государства!")
            return
        
        if not buyer_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(seller_data)
        
        if resource not in seller_data.get("resources", {}):
            await ctx.send(f"❌ У вас нет ресурса {resource}!")
            return
        
        if seller_data["resources"][resource] < amount:
            await ctx.send(f"❌ У вас недостаточно {resource}! Доступно: {seller_data['resources'][resource]}")
            return
        
        total_price = amount * price * 1000
        
        seller_country = seller_data["state"]["statename"]
        buyer_country = buyer_data["state"]["statename"]
        
        # Расчёт тарифов с обеих сторон
        from trade_tariffs import calculate_trade_with_tariffs
        
        trade_calc = calculate_trade_with_tariffs(
            {"resource": resource, "amount": amount, "total_price": total_price},
            seller_country,
            buyer_country
        )
        
        if trade_calc.get("blocked", False):
            await ctx.send(f"❌ Сделка заблокирована: {trade_calc['reason']}")
            return
        
        trade_id = len(trades["active_trades"]) + 1
        trade = {
            "id": trade_id,
            "seller_id": str(ctx.author.id),
            "seller_name": ctx.author.name,
            "seller_country": seller_country,
            "buyer_id": str(member.id),
            "buyer_name": member.name,
            "buyer_country": buyer_country,
            "resource": resource,
            "amount": amount,
            "price_per_unit": price * 1000,
            "total_price": total_price,
            "import_tariff": trade_calc["import_tariff"],
            "export_tariff": trade_calc["export_tariff"],
            "final_price": trade_calc["final_price"],
            "seller_receives": trade_calc["seller_receives"],
            "status": "pending",
            "created_at": str(datetime.now())
        }
        
        trades["active_trades"].append(trade)
        save_trades(trades)
        
        embed = discord.Embed(
            title="📦 Новое торговое предложение",
            description=f"Игрок {ctx.author.mention} предлагает вам сделку",
            color=0x2b2d31
        )
        embed.add_field(name="Ресурс", value=resource, inline=True)
        embed.add_field(name="Количество", value=format_number(amount), inline=True)
        embed.add_field(name="Цена за ед.", value=f"{price} тыс. $", inline=True)
        embed.add_field(name="💰 Цена без пошлин", value=format_billion(total_price), inline=True)
        
        if trade_calc["import_tariff"] > 0 or trade_calc["export_tariff"] > 0:
            if trade_calc["import_tariff"] > 0:
                embed.add_field(name="🛃 Импортная пошлина (в ваш бюджет)", value=format_billion(trade_calc["import_tariff"]), inline=True)
            if trade_calc["export_tariff"] > 0:
                embed.add_field(name="📤 Экспортная пошлина (бюджет продавца)", value=format_billion(trade_calc["export_tariff"]), inline=True)
            embed.add_field(name="💵 Итоговая цена для вас", value=format_billion(trade_calc["final_price"]), inline=True)
            embed.add_field(name="💰 Продавец получит", value=format_billion(trade_calc["seller_receives"]), inline=True)
        
        embed.add_field(name="ID сделки", value=trade_id, inline=True)
        embed.add_field(name="Статус", value="⏳ Ожидает подтверждения", inline=True)
        
        try:
            await member.send(embed=embed)
            await ctx.send(f"✅ Предложение отправлено игроку {member.mention}! ID сделки: {trade_id}")
        except:
            await ctx.send(f"✅ Предложение создано! ID сделки: {trade_id}\n"
                          f"⚠️ Не удалось отправить ЛС игроку {member.mention}. Он может принять сделку командой `!принять {trade_id}`")

    @commands.command(name='принять')
    async def accept_trade(self, ctx, trade_id: int):
        """Принять торговое предложение"""
        trades = load_trades()
        states = load_states()
        
        trade = None
        for t in trades["active_trades"]:
            if t["id"] == trade_id:
                trade = t
                break
        
        if not trade:
            await ctx.send(f"❌ Сделка с ID {trade_id} не найдена!")
            return
        
        if trade["buyer_id"] != str(ctx.author.id):
            await ctx.send("❌ Это не ваша сделка!")
            return
        
        if trade["status"] != "pending":
            await ctx.send("❌ Эта сделка уже обработана!")
            return
        
        seller_data = None
        buyer_data = None
        
        for data in states["players"].values():
            if data.get("assigned_to") == trade["seller_id"]:
                seller_data = data
            if data.get("assigned_to") == trade["buyer_id"]:
                buyer_data = data
        
        if not seller_data or not buyer_data:
            await ctx.send("❌ Ошибка загрузки данных игроков!")
            return
        
        migrate_player_resources(seller_data)
        migrate_player_resources(buyer_data)
        
        if trade["resource"] not in seller_data.get("resources", {}):
            await ctx.send("❌ У продавца больше нет этого ресурса!")
            trade["status"] = "failed"
            save_trades(trades)
            return
        
        if seller_data["resources"][trade["resource"]] < trade["amount"]:
            await ctx.send("❌ У продавца недостаточно ресурса!")
            trade["status"] = "failed"
            save_trades(trades)
            return
        
        # Используем final_price с учётом пошлин
        final_price = trade.get("final_price", trade["total_price"])
        seller_receives = trade.get("seller_receives", trade["total_price"])
        
        if buyer_data["economy"]["budget"] < final_price:
            await ctx.send(f"❌ У вас недостаточно средств! Нужно: {format_billion(final_price)}")
            return
        
        # Перемещаем ресурс
        seller_data["resources"][trade["resource"]] -= trade["amount"]
        if "resources" not in buyer_data:
            buyer_data["resources"] = {}
        buyer_data["resources"][trade["resource"]] = buyer_data["resources"].get(trade["resource"], 0) + trade["amount"]
        
        # Деньги: покупатель платит final_price, продавец получает seller_receives
        buyer_data["economy"]["budget"] -= final_price
        seller_data["economy"]["budget"] += seller_receives
        
        # Добавляем пошлины в доходы государств
        import_tariff = trade.get("import_tariff", 0)
        if import_tariff > 0:
            buyer_data["tariff_revenue"] = buyer_data.get("tariff_revenue", 0) + import_tariff
        
        # Экспортная пошлина
        export_tariff = trade.get("export_tariff", 0)
        if export_tariff > 0:
            if "export_tariff_revenue" not in seller_data:
                seller_data["export_tariff_revenue"] = 0
            seller_data["export_tariff_revenue"] += export_tariff
        
        trade["status"] = "completed"
        trade["completed_at"] = str(datetime.now())
        trades["completed_trades"].append(trade)
        trades["active_trades"].remove(trade)
        
        save_states(states)
        save_trades(trades)
        
        embed = discord.Embed(
            title="✅ Сделка завершена!",
            color=0x2b2d31
        )
        embed.add_field(name="Ресурс", value=trade["resource"], inline=True)
        embed.add_field(name="Количество", value=format_number(trade['amount']), inline=True)
        embed.add_field(name="Сумма", value=format_billion(final_price), inline=True)
        
        if import_tariff > 0:
            embed.add_field(name="🛃 Импортная пошлина", value=format_billion(import_tariff), inline=True)
        if export_tariff > 0:
            embed.add_field(name="📤 Экспортная пошлина", value=format_billion(export_tariff), inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='мои_сделки')
    async def my_trades(self, ctx):
        """Показать мои активные сделки"""
        trades = load_trades()
        
        my_id = str(ctx.author.id)
        my_trades = [t for t in trades["active_trades"] 
                    if t["seller_id"] == my_id or t["buyer_id"] == my_id]
        
        if not my_trades:
            await ctx.send("📭 У вас нет активных сделок.")
            return
        
        embed = discord.Embed(
            title="📦 Мои активные сделки",
            color=0x2b2d31
        )
        
        for trade in my_trades[:5]:
            direction = "⬆️ Продажа" if trade["seller_id"] == my_id else "⬇️ Покупка"
            other_user = trade["buyer_name"] if trade["seller_id"] == my_id else trade["seller_name"]
            
            final_price = trade.get("final_price", trade["total_price"])
            seller_receives = trade.get("seller_receives", trade["total_price"])
            
            tariff_info = ""
            if trade.get("import_tariff", 0) > 0:
                tariff_info += f"\n🛃 Импортная пошлина: {format_billion(trade['import_tariff'])}"
            if trade.get("export_tariff", 0) > 0:
                tariff_info += f"\n📤 Экспортная пошлина: {format_billion(trade['export_tariff'])}"
            
            embed.add_field(
                name=f"Сделка #{trade['id']} {direction}",
                value=f"Ресурс: {trade['resource']}\n"
                      f"Количество: {format_number(trade['amount'])}\n"
                      f"Сумма: {format_billion(final_price)}{tariff_info}\n"
                      f"Продавец получит: {format_billion(seller_receives)}\n"
                      f"С кем: {other_user}",
                inline=False
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='государство_игрока')
    async def state_player(self, ctx, member: discord.Member):
        """Просмотр профиля другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        state = player_data["state"]
        politics = player_data["politics"]
        economy = player_data["economy"]
        
        embed = discord.Embed(
            title=f"Государство {state['statename']}",
            description=f"Лидер: {member.mention}",
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
        embed.add_field(name="Эффективность", value=f"{player_data['government_efficiency']}%", inline=True)
        
        alliance = self.get_player_alliance(member.id)
        if alliance:
            embed.add_field(name="Альянс", value=f"{alliance['name']} (участник)", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='армия_игрока')
    async def army_player(self, ctx, member: discord.Member):
        """Просмотр армии другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        army = player_data.get("army", {})
        state = player_data["state"]
        state_name = state["statename"]
        
        embed = discord.Embed(
            title=f"Армия: {state_name}",
            description=f"Лидер: {member.mention}\n"
                       f"**Личный состав: {format_army_number(state['army_size'])} чел.**\n"
                       f"**Средняя опытность: {state.get('army_experience', 50):.0f}%**",
            color=0x2b2d31
        )
        
        # Сухопутные войска
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
        
        # Снаряжение
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
        
        # Военно-воздушные силы (включая дроны-камикадзе)
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
        
        # Военно-морской флот
        if "navy" in army and army["navy"]:
            navy = army["navy"]
            navy_text = ""
            navy_names = {
                "boats": "Катера", "corvettes": "Корветы", "destroyers": "Эсминцы",
                "cruisers": "Крейсера", "aircraft_carriers": "Авианосцы", "submarines": "Подводные лодки"
            }
            for key, name in navy_names.items():
                if key in navy and navy[key] > 0:
                    navy_text += f"{name}: {format_number(navy[key])}\n"
            if not navy_text:
                navy_text = "Нет флота"
            embed.add_field(name="Военно-морской флот", value=navy_text, inline=False)
        
        # Ракетное вооружение
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
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        economy = player_data["economy"]
        state = player_data["state"]
        
        embed = discord.Embed(
            title=f"Бюджет {state['statename']}",
            description=f"Лидер: {member.mention}",
            color=0x2b2d31
        )
        
        embed.add_field(name="Госбюджет", value=format_billion(economy['budget']), inline=True)
        embed.add_field(name="ВВП", value=format_billion(economy['gdp']), inline=True)
        embed.add_field(name="Госдолг", value=format_billion(economy['debt']), inline=True)
        
        if "taxes" in economy:
            tax_system = TaxSystem(player_data)
            revenue = tax_system.calculate_total_tax_revenue()
            embed.add_field(name="Налоговые поступления", value=format_billion(revenue['total']), inline=True)
        else:
            embed.add_field(name="Налоговая ставка", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        
        embed.add_field(name="Инфляция", value=f"{economy['inflation']}%", inline=True)
        embed.add_field(name="Средняя зарплата", value=f"${economy['wage']:,.0f}", inline=True)
        embed.add_field(name="Военный бюджет", value=format_billion(economy['military_budget']), inline=True)
        embed.add_field(name="Стоимость жизни", value=f"{economy['cost_of_living']}", inline=True)
        
        debt_to_gdp = (economy['debt'] / economy['gdp']) * 100
        embed.add_field(name="Долг/ВВП", value=f"{debt_to_gdp:.1f}%", inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='расходы_игрока')
    async def expenses_player(self, ctx, member: discord.Member):
        """Показать расходы другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        economy = player_data["economy"]
        state_name = player_data["state"]["statename"]
        
        defense_spending = economy.get("military_budget", 0)
        expenses = player_data.get("expenses", {})
        healthcare_spending = expenses.get("healthcare", 0)
        police_spending = expenses.get("police", 0)
        social_spending = expenses.get("social_security", 0)
        education_spending = expenses.get("education", 0)
        
        total_expenses = defense_spending + healthcare_spending + police_spending + social_spending + education_spending
        budget_percentage = (total_expenses / economy["budget"]) * 100 if economy["budget"] > 0 else 0
        
        embed = discord.Embed(
            title=f"Расходы государства: {state_name}",
            description=f"Лидер: {member.mention}\nОбщий бюджет: {format_billion(economy['budget'])}",
            color=0x2b2d31
        )
        
        embed.add_field(name="Оборона", 
                       value=f"{format_billion(defense_spending)}\n({(defense_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Здравоохранение", 
                       value=f"{format_billion(healthcare_spending)}\n({(healthcare_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Полиция", 
                       value=f"{format_billion(police_spending)}\n({(police_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Соцобеспечение", 
                       value=f"{format_billion(social_spending)}\n({(social_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Образование", 
                       value=f"{format_billion(education_spending)}\n({(education_spending/economy['budget']*100):.1f}% бюджета)", 
                       inline=True)
        embed.add_field(name="Всего расходов", 
                       value=f"{format_billion(total_expenses)}\n({budget_percentage:.1f}% бюджета)", 
                       inline=True)
        
        await ctx.send(embed=embed)

    @commands.command(name='ресурсы_игрока')
    async def resources_player(self, ctx, member: discord.Member):
        """Просмотр ресурсов другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(player_data)
        
        country_name = player_data["state"]["statename"]
        player_data = apply_infrastructure_bonuses(player_data, country_name)
        
        resources = player_data.get("resources", {})
        state_name = player_data["state"]["statename"]
        
        embed = create_resource_embed(resources, f"Ресурсы: {state_name}")
        await ctx.send(embed=embed)

    @commands.command(name='товары_игрока')
    async def civil_goods_player(self, ctx, member: discord.Member):
        """Просмотр гражданской продукции другого игрока"""
        player_data = self.get_player_state(member.id)
        
        if not player_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
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
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(player_data)
        
        country_name = player_data["state"]["statename"]
        player_data = apply_infrastructure_bonuses(player_data, country_name)
        
        state = player_data["state"]
        politics = player_data["politics"]
        economy = player_data["economy"]
        army = player_data.get("army", {})
        resources = player_data.get("resources", {})
        civil_goods = player_data.get("civil_goods", {})
        
        embed = discord.Embed(
            title=f"📊 Статистика: {state['statename']}",
            description=f"Лидер: {member.mention}",
            color=0x2b2d31
        )
        
        embed.add_field(name="Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name="Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name="Стабильность", value=f"{state['stability']}%", inline=True)
        embed.add_field(name="Правительство", value=state['government_type'][:20], inline=True)
        embed.add_field(name="Правящая партия", value=politics['ruling_party'][:20], inline=True)
        embed.add_field(name="Популярность", value=f"{politics['popularity']}%", inline=True)
        embed.add_field(name="ВВП", value=format_billion(economy['gdp']), inline=True)
        embed.add_field(name="Бюджет", value=format_billion(economy['budget']), inline=True)
        embed.add_field(name="Налог", value=f"{economy.get('tax_rate', 20)}%", inline=True)
        
        # Добавляем информацию о ресурсах
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
        
        # Добавляем информацию о гражданской продукции
        if civil_goods:
            total_civil_items = sum(civil_goods.values())
            embed.add_field(name="Гражданская продукция", value=f"Всего наименований: {len(civil_goods)}\nВсего единиц: {format_number(total_civil_items)}", inline=True)
        
        # Добавляем информацию об инфраструктурных бонусах
        if "infrastructure_bonuses" in player_data:
            bonuses = player_data["infrastructure_bonuses"]
            power = bonuses.get('power', 0)
            research = bonuses.get('research', 1.0)
            gov_eff = bonuses.get('gov_efficiency', 0)
            pp_gain = bonuses.get('pp_gain', 0)
            
            infra_text = f"⚡ Энергия: {power} МВт\n"
            infra_text += f"📈 Исследования: x{research:.2f}\n"
            infra_text += f"🏛️ Эффективность: +{gov_eff:.0f}%\n"
            infra_text += f"⚡ Прирост ПВ: +{pp_gain:.2f}/день"
            
            embed.add_field(name="🏭 Инфраструктура", value=infra_text, inline=True)
        
        army_total = 0
        army_details = []
        
        # Сухопутные войска
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
                    ground_text = f"**Сухопутные** ({format_number(ground_total)} ед.)\n"
                    ground_text += "\n".join(ground_items)
                    army_details.append(ground_text)
        
        # Авиация (включая дроны-камикадзе)
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
                    air_text = f"**Авиация** ({format_number(air_total)} ед.)\n"
                    air_text += "\n".join(air_items)
                    army_details.append(air_text)
        
        # Флот
        if "navy" in army:
            navy_total = sum(army["navy"].values())
            army_total += navy_total
            if navy_total > 0:
                navy_items = []
                navy_names = {
                    "boats": "Катера", "corvettes": "Корветы",
                    "destroyers": "Эсминцы", "cruisers": "Крейсера",
                    "aircraft_carriers": "Авианосцы", "submarines": "Подлодки"
                }
                for key, name in navy_names.items():
                    if key in army["navy"] and army["navy"][key] > 0:
                        navy_items.append(f"{name}: {format_number(army['navy'][key])}")
                
                if navy_items:
                    navy_text = f"**Флот** ({format_number(navy_total)} ед.)\n"
                    navy_text += "\n".join(navy_items)
                    army_details.append(navy_text)
        
        # Ракеты
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
                    missiles_text = f"**Ракеты** ({format_number(missiles_total)} ед.)\n"
                    missiles_text += "\n".join(missiles_items)
                    army_details.append(missiles_text)
        
        # Снаряжение
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
                    equip_text = f"**Снаряжение** ({format_number(equip_total)} ед.)\n"
                    equip_text += "\n".join(equip_items)
                    army_details.append(equip_text)
        
        embed.add_field(name="Армия (личный состав)", value=f"{format_army_number(state['army_size'])} чел.", inline=True)
        embed.add_field(name="Опытность", value=f"{state.get('army_experience', 50):.0f}%", inline=True)
        embed.add_field(name="Техники всего", value=f"{format_number(army_total)} ед.", inline=True)
        
        for detail in army_details[:3]:
            embed.add_field(name="─────────────", value=detail, inline=False)
        
        if len(army_details) > 3:
            for detail in army_details[3:6]:
                embed.add_field(name="─────────────", value=detail, inline=False)
        
        embed.add_field(name="Счастье", value=f"{state['happiness']}%", inline=True)
        embed.add_field(name="Доверие", value=f"{state['trust']}%", inline=True)
        embed.add_field(name="Эффективность", value=f"{player_data['government_efficiency']}%", inline=True)
        
        await ctx.send(embed=embed)

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

    @commands.command(name='производство')
    async def production_info(self, ctx):
        """Информация о времени производства"""
        embed = discord.Embed(
            title="🏭 Время производства техники",
            description="Реальное время ожидания заказов",
            color=0x2b2d31
        )
        
        categories = {
            "Сухопутная техника": ["ground.tanks", "ground.btr", "ground.bmp", "ground.self_propelled_artillery", "ground.mlrs"],
            "Авиация": ["air.fighters", "air.bombers", "air.transport_aircraft", "air.attack_helicopters"],
            "Флот": ["navy.submarines", "navy.destroyers", "navy.aircraft_carriers", "navy.corvettes"],
            "Ракеты": ["missiles.cruise_missiles", "missiles.ballistic_missiles", "missiles.hypersonic_missiles"],
            "Снаряжение": ["equipment.small_arms", "equipment.atgms", "equipment.manpads", "equipment.fpv_drones"]
        }
        
        for category_name, items in categories.items():
            text = ""
            for item in items:
                if item in PRODUCTION_SPEED:
                    time_str = format_time(PRODUCTION_SPEED[item])
                    name = EQUIPMENT_NAMES.get(item, item.split('.')[-1])
                    text += f"• {name}: {time_str}\n"
            if text:
                embed.add_field(name=category_name, value=text, inline=False)
        
        embed.set_footer(text="При заказе нескольких единиц время сокращается!")
        await ctx.send(embed=embed)

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

    # ==================== НОВЫЕ КОМАНДЫ ДЛЯ УДАРОВ И КОНФЛИКТОВ ====================
    @commands.command(name='удары')
    async def strikes(self, ctx):
        """Показать меню управления ударами БПЛА и ракет"""
        await show_strike_menu(ctx, ctx.author.id)

    @commands.command(name='конфликты')
    async def conflicts(self, ctx):
        """Показать список активных военных конфликтов"""
        await show_conflicts_menu(ctx, ctx.author.id)

    @commands.command(name='война')
    async def war_status(self, ctx):
        """Показать информацию о войнах, в которых участвует ваша страна"""
        player_data = self.get_player_state(ctx.author.id)
        
        if not player_data:
            await ctx.send("❌ У вас нет государства!")
            return
        
        country = player_data["state"]["statename"]
        enemies = get_countries_at_war_with(country)
        
        if not enemies:
            await ctx.send(f"🕊️ {country} не участвует в военных конфликтах.")
            return
        
        embed = discord.Embed(
            title=f"⚔️ Военные конфликты {country}",
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

    @commands.command(name='альянсы')
    async def list_alliances(self, ctx):
        """Показать список всех альянсов"""
        alliances = load_alliances()
        
        if not alliances["alliances"]:
            await ctx.send("📭 На данный момент нет активных альянсов.")
            return
        
        embed = discord.Embed(
            title="🌐 Список альянсов",
            color=0x2b2d31
        )
        
        for alliance in alliances["alliances"]:
            members_count = len(alliance.get("members", []))
            embed.add_field(
                name=f"{alliance['name']} ({alliance.get('acronym', '???')})",
                value=f"Участников: {members_count}\nОснован: {alliance.get('founded', 'Неизвестно')}",
                inline=True
            )
        
        await ctx.send(embed=embed)

    @commands.command(name='альянс')
    async def alliance_info(self, ctx, *, alliance_name: str):
        """Показать информацию об альянсе"""
        alliances = load_alliances()
        
        alliance = None
        for a in alliances["alliances"]:
            if a["name"].lower() == alliance_name.lower():
                alliance = a
                break
        
        if not alliance:
            await ctx.send(f"❌ Альянс '{alliance_name}' не найден!")
            return
        
        embed = discord.Embed(
            title=f"🌐 {alliance['name']} ({alliance.get('acronym', '???')})",
            description=alliance.get("description", "Нет описания"),
            color=0x2b2d31
        )
        
        embed.add_field(name="Основан", value=alliance.get("founded", "Неизвестно"), inline=True)
        embed.add_field(name="Участников", value=str(len(alliance.get("members", []))), inline=True)
        
        members_text = ""
        for i, member_id in enumerate(alliance.get("members", [])[:5]):
            try:
                user = await self.bot.fetch_user(int(member_id))
                members_text += f"• {user.name}\n"
            except:
                members_text += f"• {member_id[:8]}...\n"
        
        if len(alliance.get("members", [])) > 5:
            members_text += f"...и еще {len(alliance.get('members', [])) - 5}"
        
        embed.add_field(name="Участники", value=members_text or "Нет участников", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name='передать_ресурс')
    async def transfer_resource(self, ctx, member: discord.Member, resource: str, amount: int):
        """Передать ресурс другому игроку"""
        if member.id == ctx.author.id:
            await ctx.send("❌ Нельзя передавать ресурсы самому себе!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Количество должно быть положительным!")
            return
        
        if resource not in RESOURCE_PRICES:
            await ctx.send(f"❌ Неизвестный ресурс! Доступные: {', '.join(RESOURCE_PRICES.keys())}")
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
            await ctx.send("❌ У вас нет государства!")
            return
        
        if not receiver_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        migrate_player_resources(sender_data)
        
        if resource not in sender_data.get("resources", {}):
            await ctx.send(f"❌ У вас нет ресурса {resource}!")
            return
        
        if sender_data["resources"][resource] < amount:
            await ctx.send(f"❌ У вас недостаточно {resource}! Доступно: {sender_data['resources'][resource]}")
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
            title="📦 Запрос на передачу ресурсов",
            description=f"Игрок {ctx.author.mention} хочет передать вам ресурсы",
            color=0x2b2d31
        )
        embed.add_field(name="Ресурс", value=resource, inline=True)
        embed.add_field(name="Количество", value=format_number(amount), inline=True)
        embed.add_field(name="ID перевода", value=transfer_id, inline=True)
        embed.add_field(name="Статус", value="⏳ Ожидает подтверждения", inline=True)
        
        await ctx.send(f"✅ Запрос на передачу ресурсов отправлен игроку {member.mention}!")
        
        try:
            await member.send(embed=embed, view=view)
        except:
            await ctx.send(f"⚠️ Не удалось отправить личное сообщение игроку {member.mention}. Он должен принять перевод в канале командой `!принять_перевод {transfer_id}`")
            
            accept_view = View(timeout=300)
            accept_button = Button(label=f"✅ Принять перевод #{transfer_id}", style=discord.ButtonStyle.success, custom_id=f"accept_transfer_{transfer_id}")
            
            async def accept_callback(interaction: discord.Interaction):
                if interaction.user.id != member.id:
                    await interaction.response.send_message("❌ Это не ваш перевод!", ephemeral=True)
                    return
                await self.accept_transfer_command(ctx, transfer_id)
            
            accept_button.callback = accept_callback
            accept_view.add_item(accept_button)
            
            await ctx.send(f"🔔 {member.mention}, нажмите кнопку ниже, чтобы принять перевод ресурсов от {ctx.author.mention}:", view=accept_view)

    @commands.command(name='передать_технику')
    async def transfer_equipment(self, ctx, member: discord.Member, equip_type: str, amount: int):
        """Передать технику другому игроку"""
        if member.id == ctx.author.id:
            await ctx.send("❌ Нельзя передавать технику самому себе!")
            return
        
        if amount <= 0:
            await ctx.send("❌ Количество должно быть положительным!")
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
            await ctx.send("❌ У вас нет государства!")
            return
        
        if not receiver_data:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        path = equip_type.split('.')
        
        if "army" not in sender_data:
            sender_data["army"] = {}
        
        current = sender_data["army"]
        
        for key in path[:-1]:
            if key not in current:
                await ctx.send(f"❌ Категория {key} не найдена в вашей армии!")
                return
            current = current[key]
        
        last_key = path[-1]
        if last_key not in current or current[last_key] < amount:
            tech_name = EQUIPMENT_NAMES.get(equip_type, last_key)
            available = current.get(last_key, 0)
            await ctx.send(f"❌ У вас недостаточно {tech_name}! Доступно: {format_number(available)}")
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
            title="⚔️ Запрос на передачу техники",
            description=f"Игрок {ctx.author.mention} хочет передать вам технику",
            color=0x2b2d31
        )
        embed.add_field(name="Техника", value=tech_name, inline=True)
        embed.add_field(name="Количество", value=format_number(amount), inline=True)
        embed.add_field(name="ID перевода", value=transfer_id, inline=True)
        embed.add_field(name="Статус", value="⏳ Ожидает подтверждения", inline=True)
        
        await ctx.send(f"✅ Запрос на передачу техники отправлен игроку {member.mention}!")
        
        try:
            await member.send(embed=embed, view=view)
        except:
            await ctx.send(f"⚠️ Не удалось отправить личное сообщение игроку {member.mention}. Он должен принять перевод в канале командой `!принять_перевод {transfer_id}`")
            
            accept_view = View(timeout=300)
            accept_button = Button(label=f"✅ Принять перевод #{transfer_id}", style=discord.ButtonStyle.success, custom_id=f"accept_transfer_{transfer_id}")
            
            async def accept_callback(interaction: discord.Interaction):
                if interaction.user.id != member.id:
                    await interaction.response.send_message("❌ Это не ваш перевод!", ephemeral=True)
                    return
                await self.accept_transfer_command(ctx, transfer_id)
            
            accept_button.callback = accept_callback
            accept_view.add_item(accept_button)
            
            await ctx.send(f"🔔 {member.mention}, нажмите кнопку ниже, чтобы принять перевод техники от {ctx.author.mention}:", view=accept_view)

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
            await ctx.send(f"❌ Перевод с ID {transfer_id} не найден!")
            return
        
        if transfer["receiver_id"] != str(ctx.author.id):
            await ctx.send("❌ Это не ваш перевод!")
            return
        
        if transfer["status"] != "pending":
            await ctx.send("❌ Этот перевод уже обработан!")
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
            await ctx.send("❌ Ошибка загрузки данных игроков!")
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
                    error_msg = "❌ У отправителя недостаточно ресурса!"
            else:
                error_msg = "❌ У отправителя нет такого ресурса!"
        
        elif transfer["type"] == "equipment":
            equip_type = transfer["equip_type"]
            amount = transfer["amount"]
            path = equip_type.split('.')
            
            current = sender_data.get("army", {})
            for key in path[:-1]:
                if key not in current:
                    error_msg = f"❌ Категория {key} не найдена у отправителя!"
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
                    error_msg = "❌ У отправителя недостаточно техники!"
        
        if success:
            transfer["status"] = "completed"
            transfer["completed_at"] = str(datetime.now())
            transfers["completed_transfers"].append(transfer)
            transfers["active_transfers"].remove(transfer)
            
            save_states(states)
            save_transfers(transfers)
            
            embed = discord.Embed(
                title="✅ Перевод выполнен!",
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
            await ctx.send("📭 У вас нет активных переводов.")
            return
        
        embed = discord.Embed(
            title="📦 Мои активные переводы",
            color=0x2b2d31
        )
        
        for transfer in my_transfers[:5]:
            if transfer["type"] == "resource":
                item_name = transfer["resource"]
            else:
                item_name = EQUIPMENT_NAMES.get(transfer["equip_type"], transfer["equip_type"])
            
            direction = "⬆️ Исходящий" if transfer["sender_id"] == my_id else "⬇️ Входящий"
            other_user = f"<@{transfer['receiver_id']}>" if transfer["sender_id"] == my_id else f"<@{transfer['sender_id']}>"
            
            embed.add_field(
                name=f"Перевод #{transfer['id']} {direction}",
                value=f"{item_name}: {format_number(transfer['amount'])} ед.\n"
                      f"С кем: {other_user}\n"
                      f"Статус: ⏳ Ожидает подтверждения",
                inline=False
            )
        
        await ctx.send(embed=embed)

# ==================== ФУНКЦИЯ ПОТРЕБЛЕНИЯ ТОПЛИВА ====================
async def fuel_consumption_loop(bot_instance):
    """Фоновая задача для потребления топлива электростанциями (раз в день)"""
    await bot_instance.wait_until_ready()
    while not bot_instance.is_closed():
        try:
            from production_effects import consume_fuel, apply_infrastructure_bonuses, check_fuel_availability
            from utils import load_states, save_states
            from datetime import datetime
            
            print(f"🔄 Ежедневная проверка потребления топлива: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            states = load_states()
            fuel_shortages = []
            
            for player_data in states["players"].values():
                if "assigned_to" not in player_data:
                    continue
                
                # Обновляем бонусы инфраструктуры
                country_name = player_data["state"]["statename"]
                player_data = apply_infrastructure_bonuses(player_data, country_name)
                
                # Проверяем достаточно ли топлива на день
                enough, message = check_fuel_availability(player_data)
                
                if not enough:
                    user_id = int(player_data["assigned_to"])
                    fuel_shortages.append((user_id, message))
                else:
                    # Списываем топливо за день
                    consume_fuel(player_data, days=1)
            
            save_states(states)
            
            # Отправляем уведомления о нехватке топлива
            for user_id, message in fuel_shortages:
                try:
                    user = await bot_instance.fetch_user(user_id)
                    if user:
                        await user.send(f"⚠️ **Внимание!** {message}\nВаши электростанции могут остановиться!")
                except:
                    pass
            
            if fuel_shortages:
                print(f"⚠️ Обнаружена нехватка топлива у {len(fuel_shortages)} игроков")
            else:
                print(f"✅ Ежедневное потребление топлива обработано")
            
            await asyncio.sleep(86400)  # 24 часа (86400 секунд)
        except Exception as e:
            print(f"❌ Ошибка в fuel_consumption_loop: {e}")
            await asyncio.sleep(86400)


# ==================== ЗАПУСК БОТА ====================
@bot.event
async def on_ready():
    print(f'✅ Бот {bot.user} успешно запущен!')
    print(f'Загружено команд: {len(bot.commands)}')
    
    # Только миграция ресурсов, без пересчета бонусов
    states = load_states()
    for player_data in states["players"].values():
        migrate_player_resources(player_data)
        # НЕ вызываем apply_infrastructure_bonuses здесь!
    
    save_states(states)
    
    await bot.add_cog(AdminCommands(bot))
    await bot.add_cog(GameCommands(bot))
    await bot.add_cog(ResetCommands(bot))
    
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
    
    print('✅ Все коги успешно загружены!')
    await bot.change_presence(activity=discord.Game(name="!гайд - помощь | Экономический симулятор"))

@bot.event
async def on_command_error(ctx, error):
    """Обработка ошибок команд"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ У вас нет прав для использования этой команды!")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Неверный формат аргументов! Используйте !гайд для справки.")
    else:
        await ctx.send(f"❌ Произошла ошибка: {str(error)}")
        print(f"Ошибка: {error}")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)

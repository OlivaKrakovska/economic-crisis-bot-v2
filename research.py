# research.py - Модуль для реалистичной системы технологий и исследований

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import os
import math
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Импорты из других модулей
from utils import format_number, format_billion, load_states, save_states, send_response

# Файлы для хранения данных
RESEARCH_FILE = 'research_data.json'
TECHNOLOGIES_FILE = 'technologies.json'

# ==================== СТАРТОВЫЕ ДАННЫЕ ДЛЯ ИССЛЕДОВАНИЙ ПО СТРАНАМ ====================

STARTING_RESEARCH_FUNDING = {
    "США": {
        "aerospace": 4500, "military": 6000, "electronics": 4000, "medical": 3500,
        "energy": 2000, "automotive": 1500, "chemical": 1200, "agriculture": 1000,
        "uav": 2500, "engineering": 2000, "machine_tools": 800, "metallurgy": 600,
        "oil_gas": 1500, "construction": 500, "light_industry": 300, "shipbuilding": 800
    },
    "Россия": {
        "aerospace": 2000, "military": 3500, "electronics": 800, "energy": 1500,
        "metallurgy": 1000, "uav": 1500, "engineering": 1200, "oil_gas": 2000,
        "medical": 600, "chemical": 700, "machine_tools": 400, "automotive": 500,
        "agriculture": 400, "construction": 300, "light_industry": 200, "shipbuilding": 600
    },
    "Китай": {
        "electronics": 6000, "aerospace": 3500, "military": 4500, "automotive": 2500,
        "uav": 2000, "energy": 2000, "engineering": 3000, "machine_tools": 1500,
        "metallurgy": 1200, "chemical": 1000, "medical": 800, "oil_gas": 800,
        "shipbuilding": 2500, "construction": 1500, "agriculture": 600, "light_industry": 1000
    },
    "Германия": {
        "automotive": 4000, "engineering": 3000, "chemical": 2000, "machine_tools": 1800,
        "energy": 1200, "medical": 1500, "aerospace": 800, "military": 600,
        "electronics": 1000, "metallurgy": 500, "construction": 400, "uav": 300,
        "oil_gas": 200, "agriculture": 300, "light_industry": 400, "shipbuilding": 300
    },
    "Израиль": {
        "uav": 1800, "military": 2500, "electronics": 2000, "medical": 1500,
        "aerospace": 1200, "cyber": 1000, "agriculture": 800, "energy": 600,
        "engineering": 500, "chemical": 400, "automotive": 300, "machine_tools": 200,
        "construction": 300, "light_industry": 150, "oil_gas": 100, "shipbuilding": 100
    },
    "Украина": {
        "aerospace": 400, "military": 600, "uav": 500, "engineering": 350,
        "agriculture": 450, "metallurgy": 300, "energy": 250, "chemical": 200,
        "automotive": 150, "machine_tools": 150, "electronics": 200, "medical": 150,
        "construction": 150, "oil_gas": 100, "light_industry": 120, "shipbuilding": 200
    },
    "Иран": {
        "uav": 800, "military": 1200, "aerospace": 500, "energy": 400,
        "oil_gas": 600, "engineering": 300, "metallurgy": 250, "chemical": 300,
        "medical": 200, "electronics": 250, "automotive": 200, "agriculture": 200,
        "construction": 150, "machine_tools": 150, "light_industry": 100, "shipbuilding": 150
    }
}

SECTOR_MAPPING = {
    "aerospace": "aerospace", "military": "military", "electronics": "electronics",
    "medical": "medical", "energy": "energy", "automotive": "automotive",
    "chemical": "chemical", "agriculture": "agriculture", "uav": "uav",
    "engineering": "engineering", "machine_tools": "machine_tools", "metallurgy": "metallurgy",
    "oil_gas": "oil_gas", "construction": "construction", "light_industry": "light_industry",
    "shipbuilding": "shipbuilding", "cyber": "electronics", "nuclear": "energy"
}

# ==================== ЗАГРУЗКА БАЗЫ ТЕХНОЛОГИЙ ====================

def load_technologies_db():
    """Загрузка базы данных технологий из JSON"""
    try:
        with open(TECHNOLOGIES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"metadata": {}, "sectors": {}, "technologies": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"metadata": {}, "sectors": {}, "technologies": []}
    except json.JSONDecodeError:
        return {"metadata": {}, "sectors": {}, "technologies": []}

# Загружаем технологии при импорте модуля
TECH_DB = load_technologies_db()
SECTORS = TECH_DB.get("sectors", {})
TECHNOLOGIES = {t["id"]: t for t in TECH_DB.get("technologies", [])}

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_research_data():
    """Загрузка данных исследований игроков"""
    try:
        with open(RESEARCH_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"players": {}}
            return json.loads(content)
    except FileNotFoundError:
        return {"players": {}}
    except json.JSONDecodeError:
        return {"players": {}}

def save_research_data(data):
    """Сохранение данных исследований"""
    with open(RESEARCH_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_player_research_with_funding(user_id: str, country_name: str) -> Dict:
    """
    Инициализирует данные исследований для нового игрока
    с реалистичным финансированием на основе страны
    """
    funding_millions = STARTING_RESEARCH_FUNDING.get(country_name, STARTING_RESEARCH_FUNDING.get("США", {}))
    
    sector_funding = {}
    for sector, amount_millions in funding_millions.items():
        mapped_sector = SECTOR_MAPPING.get(sector, sector)
        sector_funding[mapped_sector] = amount_millions * 1000000  # в доллары
    
    return {
        "research_projects": {},
        "completed_techs": {},
        "sector_funding": sector_funding,
        "total_spent": 0,
        "last_update": str(datetime.now())
    }

def get_player_research(user_id: str, country_name: str = None) -> Dict:
    """Получить данные исследований игрока"""
    research_data = load_research_data()
    if user_id not in research_data["players"]:
        if country_name:
            # Инициализируем с реалистичным финансированием
            research_data["players"][user_id] = init_player_research_with_funding(user_id, country_name)
        else:
            # Запасной вариант (если страна не указана)
            research_data["players"][user_id] = {
                "research_projects": {},
                "completed_techs": {},
                "sector_funding": {},
                "total_spent": 0,
                "last_update": str(datetime.now())
            }
        save_research_data(research_data)
    
    return research_data["players"][user_id]

def save_player_research(user_id: str, player_data: Dict):
    """Сохранить данные исследований игрока"""
    research_data = load_research_data()
    research_data["players"][user_id] = player_data
    research_data["players"][user_id]["last_update"] = str(datetime.now())
    save_research_data(research_data)


# ==================== ФУНКЦИИ ДЛЯ РАСЧЕТА КОЛИЧЕСТВА УЧЕНЫХ ====================

def get_scientists_by_sector(state_data: Dict, sector_id: str) -> int:
    """
    Получает количество ученых в конкретном секторе из демографических данных
    Ученые распределяются пропорционально финансированию секторов
    """
    demographics = state_data.get("state", {}).get("demographics", {})
    professions = demographics.get("professions", {})
    total_scientists = professions.get("scientists", 0)
    
    if total_scientists == 0:
        return 0
    
    player_research = get_player_research(str(state_data.get("assigned_to", "")))
    sector_funding = player_research.get("sector_funding", {})
    
    if not sector_funding:
        return 0
    
    total_funding = sum(sector_funding.values())
    if total_funding == 0:
        return 0
    
    sector_funding_amount = sector_funding.get(sector_id, 0)
    scientist_share = sector_funding_amount / total_funding if total_funding > 0 else 0
    
    return int(total_scientists * scientist_share)


def calculate_monthly_progress(tech: Dict, scientists_assigned: int, funding_per_month: int) -> float:
    """
    Рассчитывает ежемесячный прогресс исследования
    """
    required_scientists = tech.get("scientists_required", 1000)
    required_funding = tech.get("research_cost", 1000000000)
    duration_months = tech.get("duration_months", 24)
    
    # Базовый прогресс: 1/duration_months * (scientists_share) * (funding_share)
    scientists_share = scientists_assigned / required_scientists if required_scientists > 0 else 0
    funding_share = funding_per_month / (required_funding / duration_months) if required_funding > 0 else 0
    
    # Прогресс за месяц (в долях от 1)
    monthly_progress = (1 / duration_months) * min(2.0, scientists_share) * min(2.0, funding_share)
    
    return min(2.0 / duration_months, monthly_progress)  # Максимум 200% скорости


# ==================== ПРОВЕРКА ДОСТУПНОСТИ ТЕХНОЛОГИЙ ====================

def get_available_technologies(player_research: Dict, state_data: Dict) -> List[Dict]:
    """
    Возвращает список технологий, доступных для исследования
    (все требования выполнены и еще не исследованы)
    """
    available = []
    completed = player_research.get("completed_techs", {})
    active_projects = player_research.get("research_projects", {})
    
    for tech_id, tech in TECHNOLOGIES.items():
        # Пропускаем, если уже исследуется
        if tech_id in active_projects:
            continue
        
        # Пропускаем, если уже исследована
        if tech_id in completed:
            continue
        
        # Проверяем требования
        prereqs_met = True
        for prereq_id in tech.get("prerequisites", []):
            if prereq_id not in completed:
                prereqs_met = False
                break
        
        if prereqs_met:
            available.append(tech)
    
    # Сортируем по году и сектору
    available.sort(key=lambda t: (t.get("year", 9999), t.get("sector", ""), t.get("name", "")))
    return available


def get_tech_cost(tech: Dict, current_level: int = 0) -> int:
    """Получить стоимость технологии (для совместимости)"""
    return tech.get("research_cost", 1000000000)


def format_research_time(seconds: int) -> str:
    """Форматирование времени исследования"""
    if seconds < 60:
        return f"{seconds} сек"
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


# ==================== ПРИМЕНЕНИЕ ЭФФЕКТОВ ТЕХНОЛОГИЙ ====================

async def apply_technology_effects(state_data: Dict, tech: Dict, level: int = 1):
    """
    Применяет эффекты изученной технологии к государству
    """
    # Определяем, какие эффекты применять
    if "effects" in tech:
        effects = tech["effects"]
    else:
        effects = {}
    
    for effect_key, value in effects.items():
        # Производственные бонусы
        if effect_key == "production_speed":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            if "production_speed" not in state_data["bonuses"]:
                state_data["bonuses"]["production_speed"] = 1.0
            state_data["bonuses"]["production_speed"] += value
        
        elif effect_key == "crop_yield":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            if "crop_yield" not in state_data["bonuses"]:
                state_data["bonuses"]["crop_yield"] = 1.0
            state_data["bonuses"]["crop_yield"] += (value - 1.0)
        
        elif effect_key == "oil_extraction_rate":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            if "oil_extraction" not in state_data["bonuses"]:
                state_data["bonuses"]["oil_extraction"] = 1.0
            state_data["bonuses"]["oil_extraction"] += (value - 1.0)
        
        elif effect_key == "material_strength":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            if "material_strength" not in state_data["bonuses"]:
                state_data["bonuses"]["material_strength"] = 1.0
            state_data["bonuses"]["material_strength"] += (value - 1.0)
        
        elif effect_key == "machining_precision":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            if "precision" not in state_data["bonuses"]:
                state_data["bonuses"]["precision"] = 1.0
            state_data["bonuses"]["precision"] += (value - 1.0)
        
        elif effect_key == "solar_efficiency":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            if "solar_efficiency" not in state_data["bonuses"]:
                state_data["bonuses"]["solar_efficiency"] = 1.0
            state_data["bonuses"]["solar_efficiency"] += (value - 1.0)
        
        elif effect_key == "energy_density":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            if "battery_density" not in state_data["bonuses"]:
                state_data["bonuses"]["battery_density"] = 1.0
            state_data["bonuses"]["battery_density"] += (value - 1.0)
        
        elif effect_key == "construction_speed":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            if "construction_speed" not in state_data["bonuses"]:
                state_data["bonuses"]["construction_speed"] = 1.0
            state_data["bonuses"]["construction_speed"] += (value - 1.0)
        
        elif effect_key == "transistor_density":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            if "transistor_density" not in state_data["bonuses"]:
                state_data["bonuses"]["transistor_density"] = 1.0
            state_data["bonuses"]["transistor_density"] += (value - 1.0)
        
        # Специальные флаги (булевы)
        elif isinstance(value, bool) and value:
            if "special_flags" not in state_data:
                state_data["special_flags"] = []
            if effect_key not in state_data["special_flags"]:
                state_data["special_flags"].append(effect_key)
    
    return state_data


# ==================== ФУНКЦИИ ДЛЯ СОЗДАНИЯ EMBED ====================

def create_research_status_embed(state_data: Dict, player_research: Dict) -> discord.Embed:
    """Создает Embed со статусом исследований"""
    
    state_name = state_data["state"]["statename"]
    demographics = state_data["state"].get("demographics", {})
    professions = demographics.get("professions", {})
    total_scientists = professions.get("scientists", 0)
    
    embed = discord.Embed(
        title="Научно-исследовательский центр",
        description=f"Государство: {state_name}",
        color=0x3498db
    )
    
    # Общая статистика
    total_funding = sum(player_research.get("sector_funding", {}).values()) / 1000000
    embed.add_field(
        name="Статистика",
        value=f"Всего учёных: **{format_number(total_scientists)}**\n"
              f"Всего финансирование: **{total_funding:.0f} млн $/мес**\n"
              f"Завершено технологий: **{len(player_research.get('completed_techs', {}))}**\n"
              f"Всего потрачено: **{format_billion(player_research.get('total_spent', 0))}**",
        inline=False
    )
    
    # Финансирование по секторам (топ-5)
    sector_funding = player_research.get("sector_funding", {})
    if sector_funding:
        # Сортируем по убыванию финансирования
        sorted_sectors = sorted(sector_funding.items(), key=lambda x: x[1], reverse=True)
        
        funding_text = ""
        for sector_id, amount in sorted_sectors[:5]:
            sector_name = SECTORS.get(sector_id, {}).get("name", sector_id)
            scientists = get_scientists_by_sector(state_data, sector_id)
            amount_millions = amount / 1000000
            funding_text += f"• {sector_name}: {amount_millions:.0f} млн $/мес | 👥 {scientists} уч.\n"
        embed.add_field(name="Финансирование секторов", value=funding_text or "Нет", inline=False)
    
    # Активные проекты
    active_projects = player_research.get("research_projects", {})
    if active_projects:
        projects_text = ""
        now = datetime.now()
        for tech_id, project in list(active_projects.items())[:3]:
            tech = TECHNOLOGIES.get(tech_id)
            if tech:
                completion = datetime.fromisoformat(project["completion_time"])
                remaining = (completion - now).days
                
                if remaining > 0:
                    status = f"⏳ {remaining} дн"
                else:
                    status = "✅ Завершается"
                
                projects_text += f"• {tech['name']}: {status}\n"
        embed.add_field(name="Активные проекты", value=projects_text or "Нет", inline=False)
    else:
        embed.add_field(name="Активные проекты", value="Нет активных исследований", inline=False)
    
    return embed


# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class SectorSelect(Select):
    """Выпадающий список для выбора сектора"""
    
    def __init__(self, user_id: int, state_data: Dict, player_research: Dict):
        self.user_id = user_id
        self.state_data = state_data
        self.player_research = player_research
        
        options = []
        for sector_id, sector in SECTORS.items():
            scientists = get_scientists_by_sector(state_data, sector_id)
            funding = player_research.get("sector_funding", {}).get(sector_id, 0)
            funding_millions = funding / 1000000
            
            options.append(
                discord.SelectOption(
                    label=sector["name"],
                    description=f"👥 {scientists} уч. | 💰 {funding_millions:.0f} млн $",
                    value=sector_id
                )
            )
        
        super().__init__(
            placeholder="Выберите сектор для управления...",
            min_values=1,
            max_values=1,
            options=options[:25]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        sector_id = self.values[0]
        sector = SECTORS.get(sector_id, {})
        
        embed = discord.Embed(
            title=f"{sector.get('name', sector_id)}",
            description=sector.get("description", "Нет описания"),
            color=0x3498db
        )
        
        scientists = get_scientists_by_sector(self.state_data, sector_id)
        funding = self.player_research.get("sector_funding", {}).get(sector_id, 0)
        funding_millions = funding / 1000000
        
        embed.add_field(name="Учёных в секторе", value=format_number(scientists), inline=True)
        embed.add_field(name="Финансирование", value=f"{funding_millions:.0f} млн $/мес", inline=True)
        
        # Доступные технологии в этом секторе
        available = get_available_technologies(self.player_research, self.state_data)
        sector_techs = [t for t in available if t.get("sector") == sector_id]
        
        if sector_techs:
            tech_text = ""
            for tech in sector_techs[:5]:
                tech_text += f"• {tech['name']} ({tech.get('year')})\n"
            embed.add_field(name="Доступные технологии", value=tech_text, inline=False)
        
        view = SectorManagementView(self.user_id, self.state_data, self.player_research, sector_id)
        await interaction.response.edit_message(embed=embed, view=view)


class SectorManagementView(View):
    """Управление конкретным сектором"""
    
    def __init__(self, user_id: int, state_data: Dict, player_research: Dict, sector_id: str):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.state_data = state_data
        self.player_research = player_research
        self.sector_id = sector_id
    
    @discord.ui.button(label="💰 Изменить финансирование", style=discord.ButtonStyle.secondary)
    async def funding_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        modal = FundingModal(self.user_id, self.state_data, self.player_research, self.sector_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="🔬 Доступные технологии", style=discord.ButtonStyle.secondary)
    async def tech_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        available = get_available_technologies(self.player_research, self.state_data)
        sector_techs = [t for t in available if t.get("sector") == self.sector_id]
        
        if not sector_techs:
            await interaction.response.send_message("❌ В этом секторе нет доступных технологий!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"Доступные технологии - {SECTORS.get(self.sector_id, {}).get('name', self.sector_id)}",
            color=0x3498db
        )
        
        select = TechnologySelect(sector_techs, self.user_id, self.state_data, self.player_research, self.sector_id)
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀️ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_sector
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="◀️ Назад", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_research_menu(interaction, self.user_id)
    
    async def back_to_sector(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        sector = SECTORS.get(self.sector_id, {})
        
        embed = discord.Embed(
            title=f"{sector.get('name', self.sector_id)}",
            description=sector.get("description", "Нет описания"),
            color=0x3498db
        )
        
        scientists = get_scientists_by_sector(self.state_data, self.sector_id)
        funding = self.player_research.get("sector_funding", {}).get(self.sector_id, 0)
        funding_millions = funding / 1000000
        
        embed.add_field(name="Учёных в секторе", value=format_number(scientists), inline=True)
        embed.add_field(name="Финансирование", value=f"{funding_millions:.0f} млн $/мес", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)


class FundingModal(Modal, title="Изменить финансирование"):
    def __init__(self, user_id: int, state_data: Dict, player_research: Dict, sector_id: str):
        super().__init__()
        self.user_id = user_id
        self.state_data = state_data
        self.player_research = player_research
        self.sector_id = sector_id
        
        current_funding = player_research.get("sector_funding", {}).get(sector_id, 0) / 1000000
        
        self.funding_input = TextInput(
            label=f"Финансирование в месяц (текущее: {current_funding:.0f} млн $)",
            placeholder="Например: 100",
            min_length=1,
            max_length=10,
            required=True
        )
        self.add_item(self.funding_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            funding_millions = int(self.funding_input.value)
            if funding_millions < 0:
                await interaction.response.send_message("❌ Финансирование не может быть отрицательным!", ephemeral=True)
                return
            if funding_millions > 100000:
                await interaction.response.send_message("❌ Слишком большая сумма! Максимум 100 млрд $", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        funding = funding_millions * 1000000  # переводим в доллары
        
        # Проверяем бюджет
        budget = self.state_data["economy"].get("budget", 0)
        current_funding = self.player_research.get("sector_funding", {}).get(self.sector_id, 0)
        total_funding = sum(self.player_research.get("sector_funding", {}).values())
        
        new_total = total_funding - current_funding + funding
        
        if new_total > budget * 0.1:  # Не больше 10% бюджета на науку
            max_allowed = (budget * 0.1) / 1000000
            await interaction.response.send_message(
                f"❌ Слишком большие расходы на науку! Максимум 10% бюджета ({max_allowed:.0f} млн $)",
                ephemeral=True
            )
            return
        
        # Сохраняем
        if "sector_funding" not in self.player_research:
            self.player_research["sector_funding"] = {}
        
        self.player_research["sector_funding"][self.sector_id] = funding
        save_player_research(str(self.user_id), self.player_research)
        
        sector_name = SECTORS.get(self.sector_id, {}).get("name", self.sector_id)
        
        await interaction.response.send_message(
            f"✅ Финансирование сектора {sector_name} установлено на {funding_millions:.0f} млн $ в месяц",
            ephemeral=True
        )


class TechnologySelect(Select):
    """Выпадающий список для выбора технологии"""
    
    def __init__(self, technologies: List[Dict], user_id: int, state_data: Dict, 
                 player_research: Dict, sector_id: str):
        self.user_id = user_id
        self.state_data = state_data
        self.player_research = player_research
        self.sector_id = sector_id
        
        options = []
        for tech in technologies[:25]:
            required_scientists = tech.get("scientists_required", 1000)
            cost_millions = tech.get("research_cost", 1000000000) / 1000000
            
            options.append(
                discord.SelectOption(
                    label=tech["name"],
                    description=f"{tech.get('year')} г. | 👥 {required_scientists} уч. | 💰 {cost_millions:.0f} млн $",
                    value=tech["id"]
                )
            )
        
        super().__init__(
            placeholder="Выберите технологию для исследования...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        tech_id = self.values[0]
        tech = TECHNOLOGIES.get(tech_id)
        
        if not tech:
            await interaction.response.send_message("❌ Технология не найдена!", ephemeral=True)
            return
        
        # Проверяем, не исследуется ли уже
        if tech_id in self.player_research.get("research_projects", {}):
            await interaction.response.send_message("❌ Эта технология уже исследуется!", ephemeral=True)
            return
        
        # Проверяем наличие учёных
        scientists = get_scientists_by_sector(self.state_data, self.sector_id)
        required_scientists = tech.get("scientists_required", 1000)
        
        if scientists < required_scientists * 0.5:  # Минимум 50% от требуемого количества
            await interaction.response.send_message(
                f"❌ Недостаточно учёных! Нужно минимум {int(required_scientists * 0.5)}, у вас {scientists}",
                ephemeral=True
            )
            return
        
        # Проверяем финансирование
        funding = self.player_research.get("sector_funding", {}).get(self.sector_id, 0)
        if funding < 1000000:  # Минимум 1 млн $ в месяц
            await interaction.response.send_message(
                f"❌ Слишком мало финансирование сектора! Нужно минимум 1 млн $ в месяц",
                ephemeral=True
            )
            return
        
        # Показываем подтверждение
        view = ResearchConfirmationView(self.user_id, self.state_data, self.player_research, tech, self.sector_id)
        
        embed = discord.Embed(
            title=tech["name"],
            description=tech.get("description", "Нет описания"),
            color=0x3498db
        )
        
        required_scientists = tech.get("scientists_required", 0)
        cost_millions = tech.get("research_cost", 0) / 1000000
        duration_months = tech.get("duration_months", 0)
        available_scientists = get_scientists_by_sector(self.state_data, self.sector_id)
        
        embed.add_field(name="Год", value=str(tech.get("year")), inline=True)
        embed.add_field(name="Требуется учёных", value=format_number(required_scientists), inline=True)
        embed.add_field(name="Доступно учёных", value=format_number(available_scientists), inline=True)
        embed.add_field(name="Стоимость", value=f"{cost_millions:.0f} млн $", inline=True)
        embed.add_field(name="Длительность", value=f"{duration_months} месяцев", inline=True)
        
        # Эффекты
        effects = tech.get("effects", {})
        if effects:
            effects_text = ""
            for key, value in list(effects.items())[:5]:
                if isinstance(value, bool):
                    effects_text += f"• {key.replace('_', ' ').title()}\n"
                elif isinstance(value, float) and value > 1:
                    effects_text += f"• {key.replace('_', ' ').title()}: +{(value-1)*100:.0f}%\n"
                elif isinstance(value, float) and value < 1:
                    effects_text += f"• {key.replace('_', ' ').title()}: снижение на {(1-value)*100:.0f}%\n"
                else:
                    effects_text += f"• {key.replace('_', ' ').title()}: {value}\n"
            embed.add_field(name="Эффекты", value=effects_text, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=view)


class ResearchConfirmationView(View):
    """Подтверждение начала исследования"""
    
    def __init__(self, user_id: int, state_data: Dict, player_research: Dict, tech: Dict, sector_id: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.state_data = state_data
        self.player_research = player_research
        self.tech = tech
        self.sector_id = sector_id
    
    @discord.ui.button(label="✅ Начать исследование", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверяем ещё раз
        if self.tech["id"] in self.player_research.get("research_projects", {}):
            await interaction.response.send_message("❌ Эта технология уже исследуется!", ephemeral=True)
            return
        
        scientists = get_scientists_by_sector(self.state_data, self.sector_id)
        required_scientists = self.tech.get("scientists_required", 1000)
        
        if scientists < required_scientists * 0.5:
            await interaction.response.send_message(
                f"❌ Недостаточно учёных!",
                ephemeral=True
            )
            return
        
        funding = self.player_research.get("sector_funding", {}).get(self.sector_id, 0)
        if funding < 1000000:
            await interaction.response.send_message(
                f"❌ Слишком мало финансирование!",
                ephemeral=True
            )
            return
        
        # Рассчитываем время завершения
        monthly_progress = calculate_monthly_progress(
            self.tech, 
            scientists, 
            funding
        )
        
        duration_months = self.tech.get("duration_months", 24)
        estimated_months = int(duration_months / monthly_progress) if monthly_progress > 0 else duration_months * 2
        estimated_months = max(1, min(duration_months * 3, estimated_months))  # Ограничиваем
        
        completion_time = datetime.now() + timedelta(days=estimated_months * 30)
        
        # Запускаем исследование
        if "research_projects" not in self.player_research:
            self.player_research["research_projects"] = {}
        
        self.player_research["research_projects"][self.tech["id"]] = {
            "start_time": str(datetime.now()),
            "completion_time": str(completion_time),
            "scientists_assigned": scientists,
            "funding_per_month": funding,
            "sector": self.sector_id
        }
        
        save_player_research(str(self.user_id), self.player_research)
        
        embed = discord.Embed(
            title="✅ Исследование начато!",
            description=f"**{self.tech['name']}**",
            color=0x2ecc71
        )
        
        scientists = get_scientists_by_sector(self.state_data, self.sector_id)
        funding_millions = funding / 1000000
        
        embed.add_field(name="Сектор", value=SECTORS.get(self.sector_id, {}).get("name", self.sector_id), inline=True)
        embed.add_field(name="Учёных задействовано", value=format_number(scientists), inline=True)
        embed.add_field(name="Финансирование", value=f"{funding_millions:.0f} млн $/мес", inline=True)
        embed.add_field(name="Ожидаемое завершение", value=completion_time.strftime("%d.%m.%Y"), inline=True)
        
        # Для эфемерных сообщений нельзя использовать edit_message после response.send_modal
        # Поэтому отправляем новое сообщение
        await interaction.response.send_message(embed=embed, ephemeral=True)
        # Удаляем исходное сообщение с меню
        try:
            await interaction.message.delete()
        except:
            pass
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Действие отменено",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        try:
            await interaction.message.delete()
        except:
            pass


class ResearchMainView(View):
    """Главное меню исследований"""
    
    def __init__(self, user_id: int, state_data: Dict, player_research: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.state_data = state_data
        self.player_research = player_research
    
    @discord.ui.button(label="📊 Мои исследования", style=discord.ButtonStyle.secondary)
    async def status_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = create_research_status_embed(self.state_data, self.player_research)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🔬 Секторы науки", style=discord.ButtonStyle.secondary)
    async def sectors_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Секторы науки",
            description="Выберите сектор для управления финансированием и исследованиями",
            color=0x3498db
        )
        
        select = SectorSelect(self.user_id, self.state_data, self.player_research)
        view = View(timeout=120)
        view.add_item(select)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="📋 Завершённые технологии", style=discord.ButtonStyle.secondary)
    async def completed_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        completed = self.player_research.get("completed_techs", {})
        
        if not completed:
            embed = discord.Embed(
                title="Завершённые технологии",
                description="У вас пока нет завершённых исследований",
                color=0x3498db
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        embed = discord.Embed(
            title="Завершённые технологии",
            color=0x2ecc71
        )
        
        # Группируем по секторам
        by_sector = {}
        for tech_id, year in completed.items():
            tech = TECHNOLOGIES.get(tech_id)
            if tech:
                sector = tech.get("sector", "unknown")
                if sector not in by_sector:
                    by_sector[sector] = []
                by_sector[sector].append((tech, year))
        
        for sector_id, techs in list(by_sector.items())[:5]:
            sector_name = SECTORS.get(sector_id, {}).get("name", sector_id)
            tech_text = ""
            for tech, year in techs[:3]:
                tech_text += f"• {tech['name']} ({year})\n"
            if len(techs) > 3:
                tech_text += f"  и ещё {len(techs)-3}\n"
            embed.add_field(name=sector_name, value=tech_text, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)


# ==================== ФОНОВАЯ ЗАДАЧА ДЛЯ ОБНОВЛЕНИЯ ИССЛЕДОВАНИЙ ====================

async def research_update_loop(bot_instance):
    """Фоновая задача для ежедневного обновления исследований"""
    await bot_instance.wait_until_ready()
    
    last_update = None
    
    while not bot_instance.is_closed():
        try:
            now = datetime.now()
            
            # Проверяем, прошел ли день (обновляем раз в 24 часа)
            if last_update is None or (now - last_update).days >= 1:
                research_data = load_research_data()
                states = load_states()
                
                for user_id_str, player_research in research_data["players"].items():
                    # Находим данные государства игрока
                    state_data = None
                    for state_data_item in states["players"].values():
                        if state_data_item.get("assigned_to") == user_id_str:
                            state_data = state_data_item
                            break
                    
                    if not state_data:
                        continue
                    
                    # Списываем финансирование из бюджета
                    total_funding = sum(player_research.get("sector_funding", {}).values())
                    if total_funding > 0:
                        budget = state_data["economy"].get("budget", 0)
                        if budget >= total_funding:
                            state_data["economy"]["budget"] -= total_funding
                            player_research["total_spent"] = player_research.get("total_spent", 0) + total_funding
                        else:
                            # Если денег нет, финансирование обнуляется
                            player_research["sector_funding"] = {}
                    
                    # Обновляем прогресс исследований
                    active_projects = player_research.get("research_projects", {})
                    completed = []
                    
                    for tech_id, project in active_projects.items():
                        tech = TECHNOLOGIES.get(tech_id)
                        if not tech:
                            continue
                        
                        completion = datetime.fromisoformat(project["completion_time"])
                        if completion <= now:
                            # Исследование завершено
                            completed.append(tech_id)
                            
                            # Добавляем в завершённые
                            player_research["completed_techs"][tech_id] = now.year
                            
                            # Применяем эффекты
                            current_level = player_research.get("completed_techs", {}).get(tech_id, 0)
                            await apply_technology_effects(state_data, tech, current_level + 1)
                            
                            # Отправляем уведомление
                            try:
                                user = await bot_instance.fetch_user(int(user_id_str))
                                if user:
                                    embed = discord.Embed(
                                        title="✅ Исследование завершено!",
                                        description=f"**{tech['name']}** разработана!",
                                        color=0x2ecc71
                                    )
                                    await user.send(embed=embed)
                            except:
                                pass
                    
                    # Удаляем завершённые проекты
                    for tech_id in completed:
                        del player_research["research_projects"][tech_id]
                
                save_research_data(research_data)
                save_states(states)
                last_update = now
                print(f"✅ Исследования обновлены: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            await asyncio.sleep(3600)  # Проверка каждый час
            
        except Exception as e:
            print(f"❌ Ошибка в research_update_loop: {e}")
            await asyncio.sleep(3600)


# ==================== КОМАНДА ДЛЯ ПОКАЗА МЕНЮ ====================

async def show_research_menu(interaction_or_ctx, user_id: int):
    """Показать меню исследований"""
    
    states = load_states()
    
    # Находим государство игрока
    state_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            state_data = data
            break
    
    if not state_data:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message("❌ У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("❌ У вас нет государства!")
        return
    
    country_name = state_data["state"]["statename"]
    player_research = get_player_research(str(user_id), country_name)
    
    embed = create_research_status_embed(state_data, player_research)
    view = ResearchMainView(user_id, state_data, player_research)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view)


# ==================== ЭКСПОРТ ФУНКЦИЙ ====================

__all__ = [
    'show_research_menu',
    'research_update_loop',
    'get_player_research',
    'calculate_monthly_progress',
    'get_scientists_by_sector',
    'apply_technology_effects',
    'TECHNOLOGIES',
    'SECTORS'
]

# infra_build.py - Модуль для строительства инфраструктуры в регионах

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import asyncio
import json
from datetime import datetime, timedelta
import math

# Импортируем вспомогательные функции из utils.py
from utils import (
    get_user_id, get_user_name, send_response, edit_response, 
    format_number, format_billion, format_infra_cost, format_time,
    create_embed, safe_delete, send_ephemeral, update_ephemeral,
    DARK_THEME_COLOR
)

# Файлы для хранения данных
INFRASTRUCTURE_FILE = 'infrastructure.json'
CONSTRUCTION_QUEUE_FILE = 'infra_construction.json'

# Список полей, которые относятся к инфраструктуре (для подсчета объектов)
INFRASTRUCTURE_FIELDS = [
    "shipyards", "military_factories", "civilian_factories", "oil_depots",
    "refineries", "thermal_power", "hydro_power", "solar_power",
    "nuclear_power", "wind_power", "internet_infrastructure"
]

# ==================== СЛОВАРЬ СТОИМОСТИ И ВРЕМЕНИ СТРОИТЕЛЬСТВА ====================
# Цены в миллионах долларов, время в секундах

INFRASTRUCTURE_COSTS = {
    "shipyards": {
        "name": "Верфь",
        "cost": 500,  # 500 млн $
        "build_time": 12 * 3600,  # 12 часов
        "description": "Строительство и ремонт кораблей. Увеличивает скорость производства кораблей на 5% за каждую верфь. **Требуется выход к морю!**",
        "max_per_region": 10,
        "requires_coastal": True,  # Требуется выход к морю
        "production_bonus": {
            "navy.boats": 0.05,
            "navy.corvettes": 0.05,
            "navy.destroyers": 0.05,
            "navy.cruisers": 0.05,
            "navy.aircraft_carriers": 0.05,
            "navy.submarines": 0.05
        }
    },
    "military_factories": {
        "name": "Военный завод",
        "cost": 300,
        "build_time": 8 * 3600,
        "description": "Производство военной техники. Увеличивает скорость производства всей военной техники на 2% за каждый завод.",
        "max_per_region": 50,
        "requires_coastal": False,
        "production_bonus": {
            "ground": 0.02,
            "air": 0.02,
            "missiles": 0.02
        }
    },
    "civilian_factories": {
        "name": "Гражданская фабрика",
        "cost": 200,
        "build_time": 6 * 3600,
        "description": "Производство товаров и экономический рост. Увеличивает скорость производства гражданских товаров на 3% за каждую фабрику.",
        "max_per_region": 100,
        "requires_coastal": False,
        "production_bonus": {
            "civil": 0.03
        }
    },
    "oil_depots": {
        "name": "Нефтебаза",
        "cost": 150,
        "build_time": 4 * 3600,
        "description": "Хранение нефти и нефтепродуктов. Увеличивает максимальный запас нефти на 1000 единиц и снижает потери при хранении.",
        "max_per_region": 30,
        "requires_coastal": False,
        "storage_bonus": {
            "oil": 1000,
            "gas": 500
        },
        "efficiency_bonus": 0.02
    },
    "refineries": {
        "name": "НПЗ",
        "cost": 400,
        "build_time": 10 * 3600,
        "description": "Переработка нефти в топливо. Увеличивает скорость производства химической и нефтехимической продукции на 10% за каждый завод.",
        "max_per_region": 15,
        "requires_coastal": False,
        "production_bonus": {
            "chemicals": 0.10,
            "pharmaceuticals": 0.05
        }
    },
    "thermal_power": {
        "name": "ТЭС",
        "cost": 350,
        "build_time": 8 * 3600,
        "description": "Тепловая электростанция. Генерирует 100 МВт электроэнергии. Потребляет 0.024 угля и 0.012 нефти в день.",
        "max_per_region": 25,
        "requires_coastal": False,
        "power_output": 100,
        "fuel_consumption": {
            "coal": 0.024,
            "oil": 0.012
        }
    },
    "hydro_power": {
        "name": "ГЭС",
        "cost": 600,
        "build_time": 16 * 3600,
        "description": "Гидроэлектростанция. Генерирует 150 МВт электроэнергии. Не требует топлива, зависит от наличия рек.",
        "max_per_region": 10,
        "requires_coastal": False,
        "power_output": 150,
        "fuel_consumption": {}
    },
    "solar_power": {
        "name": "СЭС",
        "cost": 180,
        "build_time": 4 * 3600,
        "description": "Солнечная электростанция. Генерирует 40 МВт электроэнергии в дневное время. Не требует топлива.",
        "max_per_region": 40,
        "requires_coastal": False,
        "power_output": 40,
        "day_night_cycle": True,
        "fuel_consumption": {}
    },
    "nuclear_power": {
        "name": "АЭС",
        "cost": 1500,
        "build_time": 36 * 3600,
        "description": "Атомная электростанция. Генерирует 500 МВт электроэнергии. Потребляет 0.002 урана в день.",
        "max_per_region": 5,
        "requires_coastal": False,
        "power_output": 500,
        "fuel_consumption": {
            "uranium": 0.002
        }
    },
    "wind_power": {
        "name": "ВЭС",
        "cost": 220,
        "build_time": 5 * 3600,
        "description": "Ветровая электростанция. Генерирует 60 МВт электроэнергии. Не требует топлива, зависит от ветрености региона.",
        "max_per_region": 30,
        "requires_coastal": False,
        "power_output": 60,
        "weather_dependent": True,
        "fuel_consumption": {}
    },
    "internet_infrastructure": {
        "name": "ЦОД",
        "cost": 100,
        "build_time": 3 * 3600,
        "description": "Центр обработки данных. Увеличивает скорость исследований, эффективность правительства и прирост политической власти на 1% за каждый ЦОД.",
        "max_per_region": 200,
        "requires_coastal": False,
        "bonus": {
            "research_speed": 0.01,
            "government_efficiency": 0.01,
            "political_power_gain": 0.01
        }
    },
    "office_centers": {
        "name": "Бизнес-центр",
        "cost": 150,  # 150 млн $
        "build_time": 4 * 3600,  # 4 часа
        "description": "Офисные здания для компаний сферы услуг, IT-фирм, банков и корпораций. Создаёт рабочие места в сфере услуг и даёт экономические бонусы.",
        "max_per_region": 200,
        "requires_coastal": False,
        "bonus": {
            "service_boost": 0.02,      # +2% к эффективности сферы услуг за каждый центр
            "tax_boost": 0.01,           # +1% к собираемости налогов
            "tech_boost": 0.005,          # +0.5% к скорости исследований
            "happiness_boost": 1,         # +1 к счастью населения за каждый центр
            "consumption_boost": 0.01     # +1% к потреблению товаров
        }
    }
}

# ==================== ФУНКЦИИ ДЛЯ РАСЧЕТА БОНУСОВ ====================

def calculate_production_bonus(region_data, product_type, country_name: str = None):
    """
    Рассчитывает бонус к скорости производства для конкретного типа продукции
    на основе инфраструктуры региона и спутников
    
    Параметры:
    - region_data: данные региона (словарь с инфраструктурой)
    - product_type: тип продукции (например, "ground.tanks", "civil.cars")
    - country_name: название страны (для учета спутниковых бонусов)
    
    Возвращает:
    - float: множитель скорости производства (1.0 = 100%)
    """
    from infra_build import INFRASTRUCTURE_COSTS
    
    bonus = 1.0
    
    # Перебираем все типы инфраструктуры
    for infra_type, infra_data in INFRASTRUCTURE_COSTS.items():
        if infra_type in region_data:
            count = region_data[infra_type]
            if count > 0 and "production_bonus" in infra_data:
                # Для каждого бонуса от инфраструктуры
                for prod_category, bonus_value in infra_data["production_bonus"].items():
                    # Проверяем, подходит ли бонус к данному типу продукции
                    if prod_category in product_type or prod_category == "civil" and "civil" in product_type:
                        bonus += count * bonus_value
    
    # Бонус от гражданских спутников (усиливает эффект инфраструктуры)
    if country_name:
        try:
            from satellites import apply_satellite_bonuses_to_infrastructure
            # Применяем спутниковый бонус ко всей инфраструктуре
            bonus = apply_satellite_bonuses_to_infrastructure(bonus, country_name, "infrastructure_boost")
        except (ImportError, Exception) as e:
            # Если модуль спутников не загружен, просто игнорируем
            pass
    
    return bonus

def get_infrastructure_bonus_with_satellites(region_data, bonus_type: str, country_name: str = None) -> float:
    """
    Рассчитывает конкретный тип бонуса от инфраструктуры с учетом спутников
    
    Параметры:
    - region_data: данные региона
    - bonus_type: тип бонуса (например, "power", "storage")
    - country_name: название страны для спутниковых бонусов
    
    Возвращает:
    - float: значение бонуса
    """
    from infra_build import INFRASTRUCTURE_COSTS, calculate_power_generation, calculate_storage_capacity
    
    result = 0.0
    
    if bonus_type == "power":
        power, _ = calculate_power_generation(region_data)
        result = power
    elif bonus_type == "storage":
        storage = calculate_storage_capacity(region_data)
        result = sum(storage.values())
    elif bonus_type == "research":
        from infra_build import calculate_research_bonus
        result = calculate_research_bonus(region_data)
    elif bonus_type == "gov_efficiency":
        from infra_build import calculate_gov_efficiency_bonus
        result = calculate_gov_efficiency_bonus(region_data)
    elif bonus_type == "pp_gain":
        from infra_build import calculate_pp_gain_bonus
        result = calculate_pp_gain_bonus(region_data)
    
    # Применяем спутниковый бонус
    if country_name and result > 0:
        try:
            from satellites import apply_satellite_bonuses_to_infrastructure
            result = apply_satellite_bonuses_to_infrastructure(result, country_name, "infrastructure_boost")
        except ImportError:
            pass
    
    return result

def apply_all_bonuses(player_data, country_name: str):
    """
    Применяет все бонусы от инфраструктуры и спутников к игроку
    """
    from infra_build import apply_infrastructure_bonuses
    
    # Сначала применяем базовые инфраструктурные бонусы
    player_data = apply_infrastructure_bonuses(player_data, country_name)
    
    # Затем добавляем спутниковые бонусы к существующим
    try:
        from satellites import get_satellite_bonuses
        sat_bonuses = get_satellite_bonuses(country_name)
        
        if "infrastructure_bonuses" not in player_data:
            player_data["infrastructure_bonuses"] = {}
        
        # Добавляем информацию о спутниковых бонусах
        player_data["infrastructure_bonuses"]["satellite"] = {
            "military_count": sat_bonuses["total_military"],
            "civilian_count": sat_bonuses["total_civilian"],
            "military_bonuses": sat_bonuses["military"],
            "civilian_bonuses": sat_bonuses["civilian"]
        }
        
        # Усиливаем существующие производственные бонусы
        if "production" in player_data["infrastructure_bonuses"]:
            production = player_data["infrastructure_bonuses"]["production"]
            for prod_type, bonus_value in production.items():
                # Применяем спутниковый множитель
                from satellites import apply_satellite_bonuses_to_infrastructure
                production[prod_type] = apply_satellite_bonuses_to_infrastructure(
                    bonus_value, country_name, "infrastructure_boost"
                )
    except ImportError:
        pass
    
    return player_data

def calculate_power_generation(region_data):
    """
    Рассчитывает общую генерацию электроэнергии в регионе
    и потребление топлива (СУТОЧНОЕ)
    """
    total_power = 0
    fuel_consumption = {}
    
    power_plants = ["thermal_power", "hydro_power", "solar_power", "nuclear_power", "wind_power"]
    
    for plant_type in power_plants:
        if plant_type in region_data:
            count = region_data[plant_type]
            if count > 0:
                plant_data = INFRASTRUCTURE_COSTS[plant_type]
                total_power += count * plant_data["power_output"]
                
                if "fuel_consumption" in plant_data:
                    for fuel, amount in plant_data["fuel_consumption"].items():
                        fuel_consumption[fuel] = fuel_consumption.get(fuel, 0) + count * amount
    
    return total_power, fuel_consumption

def calculate_storage_capacity(region_data):
    """
    Рассчитывает максимальную емкость хранилищ в регионе
    """
    storage = {}
    
    if "oil_depots" in region_data:
        count = region_data["oil_depots"]
        if count > 0:
            depot_data = INFRASTRUCTURE_COSTS["oil_depots"]
            for resource, amount in depot_data["storage_bonus"].items():
                storage[resource] = count * amount
    
    return storage

def calculate_research_bonus(region_data):
    """
    Рассчитывает бонус к исследованиям от ЦОД
    """
    bonus = 1.0
    
    if "internet_infrastructure" in region_data:
        count = region_data["internet_infrastructure"]
        if count > 0:
            bonus += count * INFRASTRUCTURE_COSTS["internet_infrastructure"]["bonus"]["research_speed"]
    
    return bonus

def calculate_gov_efficiency_bonus(region_data):
    """
    Рассчитывает бонус к эффективности правительства от ЦОД
    """
    bonus = 0
    
    if "internet_infrastructure" in region_data:
        count = region_data["internet_infrastructure"]
        if count > 0:
            bonus += count * INFRASTRUCTURE_COSTS["internet_infrastructure"]["bonus"]["government_efficiency"] * 100
    
    return min(50, bonus)

def calculate_pp_gain_bonus(region_data):
    """
    Рассчитывает бонус к приросту политической власти от ЦОД
    """
    bonus = 0
    
    if "internet_infrastructure" in region_data:
        count = region_data["internet_infrastructure"]
        if count > 0:
            bonus += count * INFRASTRUCTURE_COSTS["internet_infrastructure"]["bonus"]["political_power_gain"]
    
    return min(2.0, bonus)

def is_region_coastal(region_data):
    """Проверяет, имеет ли регион выход к морю"""
    return region_data.get("coastal", False)

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================
def load_infrastructure():
    """Загрузка данных инфраструктуры"""
    try:
        with open(INFRASTRUCTURE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"infrastructure": {}}
            return json.loads(content)
    except FileNotFoundError:
        return {"infrastructure": {}}
    except json.JSONDecodeError:
        return {"infrastructure": {}}

def save_infrastructure(data):
    """Сохранение данных инфраструктуры"""
    with open(INFRASTRUCTURE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_construction_queue():
    """Загрузка очереди строительства"""
    try:
        with open(CONSTRUCTION_QUEUE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_projects": [], "completed_projects": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"active_projects": [], "completed_projects": []}
    except json.JSONDecodeError:
        return {"active_projects": [], "completed_projects": []}

def save_construction_queue(data):
    """Сохранение очереди строительства"""
    with open(CONSTRUCTION_QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def count_infrastructure_facilities(region_data):
    """Подсчитывает количество объектов инфраструктуры в регионе"""
    total = 0
    for field in INFRASTRUCTURE_FIELDS:
        if field in region_data and isinstance(region_data[field], (int, float)):
            total += region_data[field]
    return total

def get_all_regions_from_country(infra_data, country_id):
    """Получает все регионы страны с учётом экономических районов"""
    regions = {}
    country_data = infra_data["infrastructure"].get(country_id, {})
    
    # Проверяем новую структуру с economic_regions
    if "economic_regions" in country_data:
        for econ_region_name, econ_region_data in country_data["economic_regions"].items():
            if "regions" in econ_region_data:
                for region_name, region_data in econ_region_data["regions"].items():
                    regions[region_name] = region_data
    # Поддержка старой структуры
    elif "regions" in country_data:
        regions = country_data["regions"]
    
    return regions

# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================
class EconomicRegionSelect(Select):
    """Выпадающий список для выбора экономического района"""
    def __init__(self, economic_regions, country_name, user_id, original_message):
        self.user_id = user_id
        self.country_name = country_name
        self.original_message = original_message
        options = []
        
        for econ_region_name in list(economic_regions.keys())[:25]:
            # Подсчитываем общее количество регионов в этом экономическом районе
            region_count = len(economic_regions[econ_region_name].get("regions", {}))
            
            options.append(
                discord.SelectOption(
                    label=econ_region_name[:100],
                    description=f"Регионов: {region_count}",
                    value=econ_region_name
                )
            )
        
        super().__init__(
            placeholder="Выберите экономический район...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = self.values[0]
        
        # Получаем данные
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data["infrastructure"].items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        
        if not country_id:
            await interaction.response.send_message("❌ Ошибка загрузки данных страны!", ephemeral=True)
            return
        
        regions = infra_data["infrastructure"][country_id]["economic_regions"][econ_region]["regions"]
        
        # Удаляем старое сообщение
        await safe_delete(self.original_message)
        
        # Показываем регионы выбранного экономического района
        view = RegionSelectView(self.country_name, econ_region, regions, self.user_id)
        
        embed = create_embed(
            title=f"Регионы: {econ_region}",
            description="Выберите регион для строительства:"
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class RegionSelectView(View):
    """Кнопки для выбора региона из конкретного экономического района"""
    def __init__(self, country_name, econ_region, regions, user_id):
        super().__init__(timeout=300)
        self.country_name = country_name
        self.econ_region = econ_region
        self.user_id = user_id
        
        # Создаем кнопки для регионов (максимум 23 кнопки + 2 навигационные)
        region_items = list(regions.items())[:23]
        
        for region_name, region_data in region_items:
            facilities = count_infrastructure_facilities(region_data)
            power, _ = calculate_power_generation(region_data)
            coastal = "🌊" if region_data.get("coastal", False) else ""
            
            button = Button(
                label=f"{region_name[:50]} {coastal}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"region_{region_name}"
            )
            button.callback = self.create_region_callback(region_name, region_data)
            self.add_item(button)
        
        # Кнопка назад к экономическим районам
        back_button = Button(
            label="◀ Назад к районам",
            style=discord.ButtonStyle.secondary
        )
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    def create_region_callback(self, region_name, region_data):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
                return
            
            # Удаляем текущее сообщение
            await safe_delete(interaction.message)
            
            # Показываем меню выбора типа инфраструктуры
            view = InfrastructureTypeView(self.country_name, region_name, region_data, self.user_id)
            
            embed = create_embed(
                title=f"Строительство в регионе: {region_name}",
                description="Выберите тип инфраструктуры для строительства:"
            )
            
            # Показываем текущую инфраструктуру региона
            current_text = ""
            total_facilities = 0
            total_power = 0
            total_fuel = {}
            
            for infra_type, amount in region_data.items():
                if infra_type in INFRASTRUCTURE_COSTS and isinstance(amount, (int, float)) and amount > 0:
                    current_text += f"{INFRASTRUCTURE_COSTS[infra_type]['name']}: {amount}\n"
                    total_facilities += amount
                    
                    if infra_type in ["thermal_power", "hydro_power", "solar_power", "nuclear_power", "wind_power"]:
                        total_power += amount * INFRASTRUCTURE_COSTS[infra_type]["power_output"]
                        
                        if "fuel_consumption" in INFRASTRUCTURE_COSTS[infra_type]:
                            for fuel, fuel_amount in INFRASTRUCTURE_COSTS[infra_type]["fuel_consumption"].items():
                                total_fuel[fuel] = total_fuel.get(fuel, 0) + amount * fuel_amount
            
            if current_text:
                embed.add_field(name="Текущая инфраструктура", value=current_text, inline=False)
                embed.add_field(name="Всего объектов", value=str(total_facilities), inline=True)
                if total_power > 0:
                    embed.add_field(name="Генерация энергии", value=f"{total_power} МВт", inline=True)
                
                if total_fuel:
                    fuel_text = "Потребление в день:\n"
                    for fuel, amount in total_fuel.items():
                        fuel_text += f"• {fuel}: {amount:.3f}\n"
                    embed.add_field(name="Топливо", value=fuel_text, inline=False)
            
            population = region_data.get("population", 0)
            if population:
                embed.add_field(name="Население", value=format_number(population), inline=True)
            
            coastal_status = "✅ Есть выход к морю" if region_data.get("coastal", False) else "❌ Нет выхода к морю"
            embed.add_field(name="🌊 Морской доступ", value=coastal_status, inline=True)
            
            await send_ephemeral(interaction, embed=embed, view=view)
        return callback
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Удаляем текущее сообщение
        await safe_delete(interaction.message)
        
        # Возвращаемся к выбору экономического района
        await show_infrastructure_menu(interaction)

class InfrastructureTypeView(View):
    """Выбор типа инфраструктуры"""
    def __init__(self, country_name, region, region_data, user_id):
        super().__init__(timeout=300)
        self.country_name = country_name
        self.region = region
        self.region_data = region_data
        self.user_id = user_id
        
        # Создаем кнопки для каждого типа инфраструктуры
        for infra_type, data in INFRASTRUCTURE_COSTS.items():
            # Проверяем, требуется ли выход к морю
            if data.get("requires_coastal", False) and not is_region_coastal(region_data):
                # Если требуется, но регион не имеет выхода к морю - делаем кнопку неактивной
                button = Button(
                    label=f"❌ {data['name']}",
                    style=discord.ButtonStyle.secondary,
                    disabled=True,
                    custom_id=f"infra_{infra_type}_disabled"
                )
                button.callback = self.create_disabled_callback(data['name'])
            else:
                button = Button(
                    label=data['name'],
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"infra_{infra_type}"
                )
                button.callback = self.create_callback(infra_type, data)
            self.add_item(button)
        
        # Кнопка назад
        back_button = Button(
            label="◀ Назад к регионам",
            style=discord.ButtonStyle.secondary
        )
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    def create_disabled_callback(self, infra_name):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
                return
            await interaction.response.send_message(
                f"❌ {infra_name} можно строить только в регионах с выходом к морю!",
                ephemeral=True
            )
        return callback
    
    def create_callback(self, infra_type, data):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
                return
            
            # Проверяем лимиты региона
            infra_data = load_infrastructure()
            country_id = None
            for cid, cdata in infra_data["infrastructure"].items():
                if cdata.get("country") == self.country_name:
                    country_id = cid
                    break
            
            current_count = 0
            if country_id:
                # Получаем актуальные данные региона
                all_regions = get_all_regions_from_country(infra_data, country_id)
                region_data = all_regions.get(self.region, {})
                current_count = region_data.get(infra_type, 0)
            
            if current_count >= data['max_per_region']:
                await interaction.response.send_message(
                    f"❌ В регионе {self.region} достигнут лимит по {data['name']}! "
                    f"Максимум: {data['max_per_region']}",
                    ephemeral=True
                )
                return
            
            # Удаляем текущее сообщение
            await safe_delete(interaction.message)
            
            # Показываем меню выбора количества
            view = QuantitySelector(self.country_name, self.region, infra_type, data, self.user_id)
            
            embed = create_embed(
                title=data['name'],
                description=data['description']
            )
            
            embed.add_field(name="Стоимость", value=format_infra_cost(data['cost']), inline=True)
            embed.add_field(name="Время", value=format_time(data['build_time']), inline=True)
            embed.add_field(name="Лимит в регионе", value=f"{current_count}/{data['max_per_region']}", inline=True)
            
            if "production_bonus" in data:
                bonus_text = ""
                for prod, bonus in data["production_bonus"].items():
                    bonus_text += f"• {prod}: +{bonus*100:.0f}% скорости\n"
                embed.add_field(name="Эффект", value=bonus_text, inline=False)
            
            if "power_output" in data:
                embed.add_field(name="Выработка", value=f"{data['power_output']} МВт", inline=True)
                
                if "fuel_consumption" in data and data["fuel_consumption"]:
                    fuel_text = ""
                    for fuel, amount in data["fuel_consumption"].items():
                        fuel_text += f"• {fuel}: {amount}/день\n"
                    embed.add_field(name="Потребление топлива", value=fuel_text, inline=True)
            
            await send_ephemeral(interaction, embed=embed, view=view)
        return callback
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Удаляем текущее сообщение
        await safe_delete(interaction.message)
        
        # Возвращаемся к выбору региона
        await show_infrastructure_menu(interaction)

class QuantitySelector(View):
    """Выбор количества и подтверждение строительства"""
    def __init__(self, country_name, region, infra_type, infra_data, user_id):
        super().__init__(timeout=300)
        self.country_name = country_name
        self.region = region
        self.infra_type = infra_type
        self.infra_data = infra_data
        self.user_id = user_id
        self.quantity = 1
        
        minus_button = Button(label="➖", style=discord.ButtonStyle.secondary)
        minus_button.callback = self.decrease_quantity
        self.add_item(minus_button)
        
        self.quantity_label = Button(
            label=f"{self.quantity}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        self.add_item(self.quantity_label)
        
        plus_button = Button(label="➕", style=discord.ButtonStyle.secondary)
        plus_button.callback = self.increase_quantity
        self.add_item(plus_button)
        
        manual_button = Button(
            label="Ввести число",
            style=discord.ButtonStyle.secondary
        )
        manual_button.callback = self.manual_input
        self.add_item(manual_button)
        
        build_button = Button(
            label="Начать строительство",
            style=discord.ButtonStyle.secondary
        )
        build_button.callback = self.confirm_build
        self.add_item(build_button)
        
        back_button = Button(
            label="◀ Назад",
            style=discord.ButtonStyle.secondary
        )
        back_button.callback = self.go_back
        self.add_item(back_button)
    
    async def decrease_quantity(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.label = str(self.quantity)
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()
    
    async def increase_quantity(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверяем лимит региона
        infra_data = load_infrastructure()
        country_id = None
        for cid, cdata in infra_data["infrastructure"].items():
            if cdata.get("country") == self.country_name:
                country_id = cid
                break
        
        current_count = 0
        if country_id:
            all_regions = get_all_regions_from_country(infra_data, country_id)
            region_data = all_regions.get(self.region, {})
            current_count = region_data.get(self.infra_type, 0)
        
        max_allowed = self.infra_data['max_per_region'] - current_count
        if self.quantity < max_allowed:
            self.quantity += 1
            self.quantity_label.label = str(self.quantity)
            await self.update_embed(interaction)
        else:
            await interaction.response.send_message(
                f"❌ Достигнут лимит! В регионе можно построить максимум {self.infra_data['max_per_region']} "
                f"(осталось {max_allowed})",
                ephemeral=True
            )
    
    async def manual_input(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        modal = QuantityModal(self.country_name, self.region, self.infra_type, self.infra_data, self.user_id, interaction.message)
        await interaction.response.send_modal(modal)
    
    async def update_embed(self, interaction):
        total_cost = self.infra_data['cost'] * self.quantity
        total_time = self.infra_data['build_time'] * self.quantity * 0.8  # 20% скидка на крупные проекты
        
        embed = create_embed(
            title=self.infra_data['name'],
            description=self.infra_data['description']
        )
        
        embed.add_field(name="Цена за ед.", value=format_infra_cost(self.infra_data['cost']), inline=True)
        embed.add_field(name="Количество", value=str(self.quantity), inline=True)
        embed.add_field(name="Общая стоимость", value=format_infra_cost(total_cost), inline=True)
        embed.add_field(name="Время", value=format_time(total_time), inline=True)
        embed.add_field(name="Регион", value=self.region, inline=True)
        
        if "production_bonus" in self.infra_data:
            bonus_text = ""
            for prod, bonus in self.infra_data["production_bonus"].items():
                bonus_text += f"• {prod}: +{bonus*100*self.quantity:.0f}% скорости\n"
            embed.add_field(name="Итоговый эффект", value=bonus_text, inline=False)
        
        if "power_output" in self.infra_data:
            embed.add_field(name="Выработка", value=f"{self.infra_data['power_output'] * self.quantity} МВт", inline=True)
        
        if "fuel_consumption" in self.infra_data and self.infra_data["fuel_consumption"]:
            fuel_text = ""
            for fuel, amount in self.infra_data["fuel_consumption"].items():
                fuel_text += f"• {fuel}: {amount * self.quantity:.3f}/день\n"
            embed.add_field(name="Потребление топлива", value=fuel_text, inline=True)
        
        await update_ephemeral(interaction, embed=embed, view=self)
    
    async def confirm_build(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверяем бюджет
        from bot import load_states, save_states
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(interaction.user.id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("❌ У вас нет государства!", ephemeral=True)
            return
        
        total_cost_millions = self.infra_data['cost'] * self.quantity
        total_cost_dollars = total_cost_millions * 1_000_000
        
        if player_data["economy"]["budget"] < total_cost_dollars:
            await interaction.response.send_message(
                f"❌ Недостаточно средств! Нужно: {format_infra_cost(total_cost_millions)}, "
                f"доступно: {format_billion(player_data['economy']['budget'])}",
                ephemeral=True
            )
            return
        
        # Удаляем текущее сообщение
        await safe_delete(interaction.message)
        
        # Показываем подтверждение
        view = BuildConfirmation(self.country_name, self.region, self.infra_type, self.infra_data, self.quantity, self.user_id)
        
        embed = create_embed(
            title="Подтверждение строительства",
            description=f"Проект: {self.quantity}x {self.infra_data['name']} в регионе {self.region}"
        )
        
        embed.add_field(name="Стоимость", value=format_infra_cost(total_cost_millions), inline=True)
        embed.add_field(name="Время", value=format_time(self.infra_data['build_time'] * self.quantity * 0.8), inline=True)
        
        if "power_output" in self.infra_data:
            embed.add_field(name="Выработка", value=f"{self.infra_data['power_output'] * self.quantity} МВт", inline=True)
        
        await send_ephemeral(interaction, embed=embed, view=view)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Удаляем текущее сообщение
        await safe_delete(interaction.message)
        
        # Получаем данные региона для повторного показа
        infra_data = load_infrastructure()
        country_id = None
        for cid, cdata in infra_data["infrastructure"].items():
            if cdata.get("country") == self.country_name:
                country_id = cid
                break
        
        region_data = {}
        if country_id:
            all_regions = get_all_regions_from_country(infra_data, country_id)
            region_data = all_regions.get(self.region, {})
        
        view = InfrastructureTypeView(self.country_name, self.region, region_data, self.user_id)
        
        embed = create_embed(
            title=f"Строительство в регионе: {self.region}",
            description="Выберите тип инфраструктуры для строительства:"
        )
        
        await send_ephemeral(interaction, embed=embed, view=view)

class QuantityModal(Modal, title="Введите количество"):
    def __init__(self, country_name, region, infra_type, infra_data, user_id, original_message):
        super().__init__()
        self.country_name = country_name
        self.region = region
        self.infra_type = infra_type
        self.infra_data = infra_data
        self.user_id = user_id
        self.original_message = original_message
        
        self.quantity_input = TextInput(
            label="Количество",
            placeholder="Введите число (1-100)",
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > 100:
                await interaction.response.send_message("❌ Количество должно быть от 1 до 100!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        # Проверяем лимит региона
        infra_data = load_infrastructure()
        country_id = None
        for cid, cdata in infra_data["infrastructure"].items():
            if cdata.get("country") == self.country_name:
                country_id = cid
                break
        
        current_count = 0
        if country_id:
            all_regions = get_all_regions_from_country(infra_data, country_id)
            region_data = all_regions.get(self.region, {})
            current_count = region_data.get(self.infra_type, 0)
        
        max_allowed = self.infra_data['max_per_region'] - current_count
        if quantity > max_allowed:
            await interaction.response.send_message(
                f"❌ Превышение лимита! В регионе можно построить максимум {self.infra_data['max_per_region']} "
                f"(осталось {max_allowed})",
                ephemeral=True
            )
            return
        
        # Удаляем старое сообщение
        await safe_delete(self.original_message)
        
        # Переходим к подтверждению
        view = BuildConfirmation(self.country_name, self.region, self.infra_type, self.infra_data, quantity, self.user_id)
        
        total_cost = self.infra_data['cost'] * quantity
        total_time = self.infra_data['build_time'] * quantity * 0.8
        
        embed = create_embed(
            title=self.infra_data['name'],
            description="Подтвердите строительство:"
        )
        
        embed.add_field(name="Регион", value=self.region, inline=True)
        embed.add_field(name="Количество", value=str(quantity), inline=True)
        embed.add_field(name="Общая стоимость", value=format_infra_cost(total_cost), inline=True)
        embed.add_field(name="Время", value=format_time(total_time), inline=True)
        
        await send_ephemeral(interaction, embed=embed, view=view)

class BuildConfirmation(View):
    """Подтверждение строительства"""
    def __init__(self, country_name, region, infra_type, infra_data, quantity, user_id):
        super().__init__(timeout=300)
        self.country_name = country_name
        self.region = region
        self.infra_type = infra_type
        self.infra_data = infra_data
        self.quantity = quantity
        self.user_id = user_id
        
        confirm_button = Button(
            label="Подтвердить",
            style=discord.ButtonStyle.secondary
        )
        confirm_button.callback = self.confirm
        self.add_item(confirm_button)
        
        cancel_button = Button(
            label="Отмена",
            style=discord.ButtonStyle.secondary
        )
        cancel_button.callback = self.cancel
        self.add_item(cancel_button)
    
    async def confirm(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверяем бюджет
        from bot import load_states, save_states
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(interaction.user.id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("❌ У вас нет государства!", ephemeral=True)
            return
        
        total_cost_millions = self.infra_data['cost'] * self.quantity
        total_cost_dollars = total_cost_millions * 1_000_000
        
        if player_data["economy"]["budget"] < total_cost_dollars:
            await interaction.response.send_message(
                f"❌ Недостаточно средств! Нужно: {format_infra_cost(total_cost_millions)}",
                ephemeral=True
            )
            return
        
        # Списываем деньги
        player_data["economy"]["budget"] -= total_cost_dollars
        save_states(states)
        
        # Создаем проект
        queue = load_construction_queue()
        
        total_time = self.infra_data['build_time'] * self.quantity * 0.8
        completion_time = datetime.now() + timedelta(seconds=total_time)
        
        project = {
            "id": len(queue["active_projects"]) + 1,
            "user_id": str(interaction.user.id),
            "user_name": interaction.user.name,
            "country": self.country_name,
            "region": self.region,
            "infra_type": self.infra_type,
            "infra_name": self.infra_data['name'],
            "quantity": self.quantity,
            "total_cost": total_cost_dollars,
            "start_time": str(datetime.now()),
            "completion_time": str(completion_time),
            "status": "in_progress",
            "notified": False
        }
        
        queue["active_projects"].append(project)
        save_construction_queue(queue)
        
        # Удаляем confirmation сообщение
        await safe_delete(interaction.message)
        
        embed = create_embed(
            title="Строительство начато!",
            description=f"Проект: {self.quantity}x {self.infra_data['name']}"
        )
        
        embed.add_field(name="Регион", value=self.region, inline=True)
        embed.add_field(name="Стоимость", value=format_infra_cost(total_cost_millions), inline=True)
        embed.add_field(name="Готовность", value=format_time(total_time), inline=True)
        embed.add_field(name="ID проекта", value=str(project['id']), inline=True)
        
        if "power_output" in self.infra_data:
            embed.add_field(name="Выработка", value=f"{self.infra_data['power_output'] * self.quantity} МВт", inline=True)
        
        await send_ephemeral(interaction, embed=embed)
    
    async def cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Удаляем confirmation сообщение
        await safe_delete(interaction.message)
        
        embed = create_embed(
            title="Строительство отменено",
            color=DARK_THEME_COLOR
        )
        await send_ephemeral(interaction, embed=embed)

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

async def show_infrastructure_menu(ctx):
    """Показать меню инфраструктуры (работает и с ctx, и с interaction)"""
    from bot import load_states
    
    user_id = get_user_id(ctx)
    
    states = load_states()
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        await send_response(ctx, "❌ У вас нет государства!", ephemeral=True)
        return
    
    country_name = player_data["state"]["statename"]
    
    infra_data = load_infrastructure()
    
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    
    if not country_id:
        available_countries = [d.get('country', 'Неизвестно') for d in infra_data["infrastructure"].values()]
        await send_response(ctx, f"❌ Для страны {country_name} нет данных инфраструктуры!", ephemeral=True)
        return
    
    country_data = infra_data["infrastructure"][country_id]
    
    embed = create_embed(
        title=f"Инфраструктура: {country_name}",
        description="Выберите экономический район для строительства:"
    )
    
    # Проверяем структуру данных
    if "economic_regions" in country_data:
        # Новая структура с экономическими районами
        economic_regions = country_data["economic_regions"]
        
        region_stats = ""
        total_power = 0
        total_factories = 0
        
        for econ_region_name, econ_region_data in list(economic_regions.items())[:5]:
            regions = econ_region_data.get("regions", {})
            region_count = len(regions)
            
            # Подсчитываем общую мощность и объекты по району
            region_power = 0
            region_factories = 0
            for region_data in regions.values():
                region_factories += count_infrastructure_facilities(region_data)
                power, _ = calculate_power_generation(region_data)
                region_power += power
            
            total_factories += region_factories
            total_power += region_power
            
            region_stats += f"• {econ_region_name}: {region_count} регионов, {region_factories} объектов, ⚡{region_power} МВт\n"
        
        embed.add_field(name="Доступные районы", value=region_stats, inline=False)
        embed.add_field(name="Всего объектов", value=str(total_factories), inline=True)
        embed.add_field(name="Общая генерация", value=f"{total_power} МВт", inline=True)
        
        # Отправляем эфемерное сообщение
        if hasattr(ctx, 'response'):
            await ctx.response.send_message(embed=embed, ephemeral=True)
            message = await ctx.original_response()
        else:
            message = await ctx.send(embed=embed, ephemeral=True)
        
        select = EconomicRegionSelect(economic_regions, country_name, user_id, message)
        view = View(timeout=300)
        view.add_item(select)
        
        await message.edit(view=view)
        
    elif "regions" in country_data:
        # Старая структура (для обратной совместимости)
        regions = country_data["regions"]
        
        region_stats = ""
        total_power = 0
        total_factories = 0
        
        for region_name, region_data in list(regions.items())[:5]:
            facilities = count_infrastructure_facilities(region_data)
            total_factories += facilities
            
            power, _ = calculate_power_generation(region_data)
            total_power += power
            
            population = region_data.get("population", 0)
            power_text = f" ⚡{power}МВт" if power > 0 else ""
            coastal = "🌊" if region_data.get("coastal", False) else ""
            
            if population:
                region_stats += f"• {region_name} {coastal}: {facilities} объектов{power_text} | 👥 {format_number(population)} чел.\n"
            else:
                region_stats += f"• {region_name} {coastal}: {facilities} объектов{power_text}\n"
        
        embed.add_field(name="Доступные регионы", value=region_stats, inline=False)
        embed.add_field(name="Всего объектов", value=str(total_factories), inline=True)
        embed.add_field(name="Общая генерация", value=f"{total_power} МВт", inline=True)
        
        # Отправляем эфемерное сообщение
        if hasattr(ctx, 'response'):
            await ctx.response.send_message(embed=embed, ephemeral=True)
            message = await ctx.original_response()
        else:
            message = await ctx.send(embed=embed, ephemeral=True)
        
        # Для старой структуры используем старый RegionSelect
        class LegacyRegionSelect(Select):
            def __init__(self, regions, country_name, user_id, original_message):
                self.user_id = user_id
                self.country_name = country_name
                self.original_message = original_message
                options = []
                
                for region_name in list(regions.keys())[:25]:
                    label = region_name[:100] if len(region_name) > 100 else region_name
                    
                    region_data = regions[region_name]
                    facilities = count_infrastructure_facilities(region_data)
                    
                    power, _ = calculate_power_generation(region_data)
                    power_text = f" ⚡{power}МВт" if power > 0 else ""
                    coastal = "🌊" if region_data.get("coastal", False) else ""
                    
                    options.append(
                        discord.SelectOption(
                            label=label,
                            description=f"Объектов: {facilities}{power_text} {coastal}",
                            value=region_name
                        )
                    )
                
                super().__init__(
                    placeholder="Выберите регион для строительства...",
                    min_values=1,
                    max_values=1,
                    options=options
                )
            
            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
                    return
                
                region = self.values[0]
                region_data = regions[region]
                
                # Удаляем старое сообщение
                await safe_delete(self.original_message)
                
                view = InfrastructureTypeView(self.country_name, region, region_data, self.user_id)
                
                embed = create_embed(
                    title=f"Строительство в регионе: {region}",
                    description="Выберите тип инфраструктуры для строительства:"
                )
                
                # Показываем текущую инфраструктуру региона
                current_text = ""
                total_facilities = 0
                total_power = 0
                total_fuel = {}
                
                for infra_type, amount in region_data.items():
                    if infra_type in INFRASTRUCTURE_COSTS and isinstance(amount, (int, float)) and amount > 0:
                        current_text += f"{INFRASTRUCTURE_COSTS[infra_type]['name']}: {amount}\n"
                        total_facilities += amount
                        
                        if infra_type in ["thermal_power", "hydro_power", "solar_power", "nuclear_power", "wind_power"]:
                            total_power += amount * INFRASTRUCTURE_COSTS[infra_type]["power_output"]
                            
                            if "fuel_consumption" in INFRASTRUCTURE_COSTS[infra_type]:
                                for fuel, fuel_amount in INFRASTRUCTURE_COSTS[infra_type]["fuel_consumption"].items():
                                    total_fuel[fuel] = total_fuel.get(fuel, 0) + amount * fuel_amount
                
                if current_text:
                    embed.add_field(name="Текущая инфраструктура", value=current_text, inline=False)
                    embed.add_field(name="Всего объектов", value=str(total_facilities), inline=True)
                    if total_power > 0:
                        embed.add_field(name="Генерация энергии", value=f"{total_power} МВт", inline=True)
                    
                    if total_fuel:
                        fuel_text = "Потребление в день:\n"
                        for fuel, amount in total_fuel.items():
                            fuel_text += f"• {fuel}: {amount:.3f}\n"
                        embed.add_field(name="Топливо", value=fuel_text, inline=False)
                
                population = region_data.get("population", 0)
                if population:
                    embed.add_field(name="Население", value=format_number(population), inline=True)
                
                coastal_status = "✅ Есть выход к морю" if region_data.get("coastal", False) else "❌ Нет выхода к морю"
                embed.add_field(name="🌊 Морской доступ", value=coastal_status, inline=True)
                
                await send_ephemeral(interaction, embed=embed, view=view)
        
        select = LegacyRegionSelect(regions, country_name, user_id, message)
        view = View(timeout=300)
        view.add_item(select)
        
        await message.edit(view=view)
    else:
        await send_response(ctx, "❌ Неподдерживаемая структура данных инфраструктуры!", ephemeral=True)

async def show_construction_projects(ctx):
    """Показать активные проекты строительства"""
    queue = load_construction_queue()
    user_id = get_user_id(ctx)
    user_projects = [p for p in queue["active_projects"] if p["user_id"] == str(user_id)]
    
    if not user_projects:
        await send_response(ctx, "📭 У вас нет активных строительных проектов.", ephemeral=True)
        return
    
    embed = create_embed(
        title="Мои стройки",
        description=f"Активных проектов: {len(user_projects)}"
    )
    
    now = datetime.now()
    for project in user_projects[-5:]:
        completion = datetime.fromisoformat(project["completion_time"])
        remaining = (completion - now).total_seconds()
        
        if remaining > 0:
            total_duration = (completion - datetime.fromisoformat(project["start_time"])).total_seconds()
            progress = 100 - (remaining / total_duration * 100) if total_duration > 0 else 0
            progress_bar = "█" * int(progress/10) + "░" * (10 - int(progress/10))
            status = f"⏳ {format_time(remaining)} осталось\n{progress_bar}"
        else:
            status = "✅ ГОТОВО К ЗАВЕРШЕНИЮ!"
        
        embed.add_field(
            name=f"Проект #{project['id']}: {project['quantity']}x {project['infra_name']}",
            value=f"📍 {project['region']}\n{status}",
            inline=False
        )
    
    await send_response(ctx, embed=embed, ephemeral=True)

async def complete_construction_projects(ctx):
    """Завершить готовые проекты строительства"""
    queue = load_construction_queue()
    infra_data = load_infrastructure()
    
    now = datetime.now()
    completed = []
    user_id = get_user_id(ctx)
    
    for project in queue["active_projects"][:]:
        if project["user_id"] == str(user_id):
            completion = datetime.fromisoformat(project["completion_time"])
            if completion <= now:
                country_id = None
                for cid, data in infra_data["infrastructure"].items():
                    if data.get("country") == project["country"]:
                        country_id = cid
                        break
                
                if country_id:
                    # Получаем правильный путь к региону с учётом экономических районов
                    country_data = infra_data["infrastructure"][country_id]
                    
                    if "economic_regions" in country_data:
                        # Ищем регион во всех экономических районах
                        region_found = False
                        for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                            if project["region"] in econ_region_data.get("regions", {}):
                                region_data = econ_region_data["regions"][project["region"]]
                                region_data[project["infra_type"]] = region_data.get(project["infra_type"], 0) + project["quantity"]
                                region_found = True
                                break
                        
                        if not region_found:
                            # Если регион не найден, создаём его в первом экономическом районе
                            first_econ_region = list(country_data["economic_regions"].keys())[0]
                            if "regions" not in country_data["economic_regions"][first_econ_region]:
                                country_data["economic_regions"][first_econ_region]["regions"] = {}
                            if project["region"] not in country_data["economic_regions"][first_econ_region]["regions"]:
                                country_data["economic_regions"][first_econ_region]["regions"][project["region"]] = {}
                            region_data = country_data["economic_regions"][first_econ_region]["regions"][project["region"]]
                            region_data[project["infra_type"]] = region_data.get(project["infra_type"], 0) + project["quantity"]
                    else:
                        # Старая структура
                        if project["region"] not in infra_data["infrastructure"][country_id]["regions"]:
                            infra_data["infrastructure"][country_id]["regions"][project["region"]] = {}
                        region_data = infra_data["infrastructure"][country_id]["regions"][project["region"]]
                        region_data[project["infra_type"]] = region_data.get(project["infra_type"], 0) + project["quantity"]
                    
                    project["status"] = "completed"
                    project["completed_at"] = str(now)
                    queue["completed_projects"].append(project)
                    queue["active_projects"].remove(project)
                    completed.append(project)
    
    if completed:
        save_infrastructure(infra_data)
        save_construction_queue(queue)
        
        embed = create_embed(
            title="Строительство завершено!",
            description=f"Завершено проектов: {len(completed)}"
        )
        
        for project in completed:
            embed.add_field(
                name=f"{project['quantity']}x {project['infra_name']}",
                value=f"📍 {project['region']}\n✅ Объекты введены в эксплуатацию",
                inline=False
            )
        
        await send_response(ctx, embed=embed, ephemeral=True)
    else:
        await send_response(ctx, "❌ Нет готовых проектов.", ephemeral=True)

async def construction_check_loop(bot_instance):
    """Фоновая задача для проверки завершения строительства"""
    await bot_instance.wait_until_ready()
    while not bot_instance.is_closed():
        try:
            queue = load_construction_queue()
            now = datetime.now()
            
            for project in queue["active_projects"]:
                completion = datetime.fromisoformat(project["completion_time"])
                if completion <= now and not project.get("notified", False):
                    try:
                        user = await bot_instance.fetch_user(int(project["user_id"]))
                        if user:
                            embed = create_embed(
                                title="Стройка завершена!",
                                description=f"Проект **{project['quantity']}x {project['infra_name']}** в регионе {project['region']} готов!"
                            )
                            embed.add_field(name="Регион", value=project["region"])
                            embed.add_field(name="Команда", value="`!стройки_завершить` для получения")
                            await user.send(embed=embed)
                    except:
                        pass
                    project["notified"] = True
                    save_construction_queue(queue)
            
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Ошибка в construction_check_loop: {e}")
            await asyncio.sleep(3600)

# ==================== ЭКСПОРТ ФУНКЦИЙ ====================

__all__ = [
    'INFRASTRUCTURE_COSTS',
    'load_infrastructure',
    'save_infrastructure',
    'load_construction_queue',
    'save_construction_queue',
    'format_time',
    'show_infrastructure_menu',
    'show_construction_projects',
    'complete_construction_projects',
    'construction_check_loop',
    'calculate_production_bonus',
    'calculate_power_generation',
    'calculate_storage_capacity',
    'calculate_research_bonus',
    'calculate_gov_efficiency_bonus',
    'calculate_pp_gain_bonus'
]

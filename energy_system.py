# energy_system.py - Модуль для управления энергопотреблением и отоплением
# С учётом климатических особенностей разных стран
# ОБНОВЛЕНИЕ РАЗ В 3 РЕАЛЬНЫХ ДНЯ (1 ИГРОВОЙ ГОД)
# Версия с поддержкой новой структуры активов (total/ownership)

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import asyncio
import math
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from utils import format_billion, format_number, load_states, save_states, DARK_THEME_COLOR
from paths import get_data_path
from game_time import get_month

# Файл для хранения данных
ENERGY_SYSTEM_FILE = get_data_path('energy_system.json')

# Изображения для меню энергосистемы
ENERGY_BANNER_URL = "https://static.tildacdn.com/tild3363-3236-4431-b335-356363326533/photo.png"
ENERGY_THUMBNAIL_URL = "https://avatars.mds.yandex.net/i?id=872ee4ff936469cf471cf17dbfb5d58cbd851f91-4570299-images-thumbs&n=13"

# ==================== КОНСТАНТЫ ====================

# Потребление электроэнергии инфраструктурой (МВт на единицу в день)
INFRASTRUCTURE_POWER_CONSUMPTION = {
    "military_factories": 1.5,
    "civilian_factories": 1.2,
    "shipyards": 3.5,
    "refineries": 2.0,
    "thermal_power": 0.5,
    "nuclear_power": 1.5,
    "hydro_power": 0.3,
    "solar_power": 0.1,
    "wind_power": 0.1,
    "internet_infrastructure": 0.4,
    "office_centers": 0.3,
    "oil_depots": 0.3
}

# Климатические зоны стран
CLIMATE_ZONES = {
    "США": "continental",      # Континентальный (холодная зима)
    "Россия": "arctic",        # Арктический/субарктический (очень холодно)
    "Китай": "continental",    # Континентальный (холодно на севере)
    "Германия": "temperate",   # Умеренный (мягкая зима)
    "Великобритания": "marine", # Морской (мягкая зима)
    "Франция": "temperate",    # Умеренный (мягкая зима)
    "Япония": "temperate",     # Умеренный (холодно на севере)
    "Израиль": "subtropical",  # Субтропический (мягкая зима)
    "Украина": "continental",  # Континентальный (холодная зима)
    "Иран": "subtropical",     # Субтропический (холодно в горах)
    "Беларусь": "continental",
    "Норвегия": "arctic",
    "КНДР": "continental",
    "Турция": "subtropical",
    "Сирия": "subtropical",
    "Канада": "arctic",
    "Польша": "continental",
    "Бразилия": "tropical",
    "Швеция": "arctic",
    "Финляндия": "arctic",
    "Швейцария": "temperate",
    "Египет": "subtropical"
}

# Базовое потребление газа на отопление (единиц на 1 млн человек в ГОД)
BASE_HEATING_CONSUMPTION = {
    "arctic": 0.10,        # Арктический - очень холодно
    "continental": 0.07,   # Континентальный - холодно
    "temperate": 0.04,     # Умеренный - мягкая зима
    "marine": 0.03,        # Морской - мягкая зима
    "subtropical": 0.01,   # Субтропический - почти не нуждается в отоплении
    "tropical": 0.0        # Тропический - отопление не нужно
}

# Потребление газа на другие нужды (не зависит от климата) - ЗА ГОД
BASE_HOT_WATER_CONSUMPTION = 0.015  # горячая вода (единиц на 1 млн человек в год)
BASE_COOKING_CONSUMPTION = 0.01     # приготовление пищи (единиц на 1 млн человек в год)

# Сезонные коэффициенты для разных климатических зон (ЗА ГОД)
SEASONAL_FACTORS = {
    "arctic": {
        1: 2.2, 2: 2.1, 3: 1.8, 4: 1.2, 5: 0.7, 6: 0.4,
        7: 0.3, 8: 0.3, 9: 0.6, 10: 1.2, 11: 1.7, 12: 2.0
    },
    "continental": {
        1: 1.9, 2: 1.8, 3: 1.5, 4: 1.0, 5: 0.6, 6: 0.3,
        7: 0.2, 8: 0.2, 9: 0.5, 10: 1.0, 11: 1.4, 12: 1.7
    },
    "temperate": {
        1: 1.5, 2: 1.4, 3: 1.2, 4: 0.8, 5: 0.4, 6: 0.2,
        7: 0.1, 8: 0.1, 9: 0.3, 10: 0.7, 11: 1.1, 12: 1.3
    },
    "marine": {
        1: 1.3, 2: 1.2, 3: 1.0, 4: 0.7, 5: 0.4, 6: 0.2,
        7: 0.1, 8: 0.1, 9: 0.3, 10: 0.6, 11: 0.9, 12: 1.1
    },
    "subtropical": {
        1: 1.2, 2: 1.1, 3: 0.8, 4: 0.4, 5: 0.1, 6: 0.0,
        7: 0.0, 8: 0.0, 9: 0.0, 10: 0.2, 11: 0.6, 12: 1.0
    },
    "tropical": {
        1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0, 6: 0.0,
        7: 0.0, 8: 0.0, 9: 0.0, 10: 0.0, 11: 0.0, 12: 0.0
    }
}

# Эффекты от недостатка энергии
POWER_SHORTAGE_EFFECTS = {
    "production": -0.1,      # -10% производства за каждые 10% дефицита
    "happiness": -2,         # -2% счастья за каждые 10% дефицита
    "stability": -1          # -1% стабильности за каждые 10% дефицита
}

# Эффекты от недостатка газа
GAS_SHORTAGE_EFFECTS = {
    "happiness": -3,         # -3% счастья за каждые 10% дефицита
    "stability": -1,         # -1% стабильности за каждые 10% дефицита
    "health": -1             # -1% здоровья за каждые 10% дефицита
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_climate_zone(country_name: str) -> str:
    """Возвращает климатическую зону страны"""
    return CLIMATE_ZONES.get(country_name, "temperate")

def get_seasonal_factor(country_name: str, month: int = None) -> float:
    """Возвращает сезонный коэффициент для страны"""
    if month is None:
        from game_time import get_month
        month = get_month()
    
    climate = get_climate_zone(country_name)
    return SEASONAL_FACTORS[climate].get(month, 1.0)

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_energy_data():
    """Загружает данные об энергосистеме"""
    try:
        with open(ENERGY_SYSTEM_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"power_grid": {}, "gas_network": {}, "history": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"power_grid": {}, "gas_network": {}, "history": []}
    except json.JSONDecodeError:
        return {"power_grid": {}, "gas_network": {}, "history": []}

def save_energy_data(data):
    """Сохраняет данные об энергосистеме"""
    with open(ENERGY_SYSTEM_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ==================== РАСЧЁТ ЭНЕРГОПОТРЕБЛЕНИЯ ====================

def calculate_total_power_production(infra_data, country_name: str) -> Dict:
    """
    Рассчитывает общую генерацию электроэнергии по всем типам станций
    """
    result = {
        "thermal": 0,
        "nuclear": 0,
        "hydro": 0,
        "solar": 0,
        "wind": 0,
        "geothermal": 0,
        "total": 0,
        "by_region": {}
    }
    
    from infra_build import load_infrastructure, get_all_regions_from_country, get_asset_total
    
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    
    if not country_id:
        return result
    
    regions = get_all_regions_from_country(infra_data, country_id)
    
    for region_name, region_data in regions.items():
        region_power = 0
        
        thermal_count = get_asset_total(region_data, "thermal_power")
        if thermal_count > 0:
            power = thermal_count * 100
            result["thermal"] += power
            region_power += power
        
        nuclear_count = get_asset_total(region_data, "nuclear_power")
        if nuclear_count > 0:
            power = nuclear_count * 500
            result["nuclear"] += power
            region_power += power
        
        hydro_count = get_asset_total(region_data, "hydro_power")
        if hydro_count > 0:
            power = hydro_count * 150
            result["hydro"] += power
            region_power += power
        
        solar_count = get_asset_total(region_data, "solar_power")
        if solar_count > 0:
            power = solar_count * 40
            result["solar"] += power
            region_power += power
        
        wind_count = get_asset_total(region_data, "wind_power")
        if wind_count > 0:
            power = wind_count * 60
            result["wind"] += power
            region_power += power
        
        result["by_region"][region_name] = region_power
    
    result["total"] = sum([result["thermal"], result["nuclear"], result["hydro"], 
                          result["solar"], result["wind"], result["geothermal"]])
    
    return result


def calculate_total_power_consumption(infra_data, country_name: str) -> Dict:
    """
    Рассчитывает общее потребление электроэнергии инфраструктурой
    """
    result = {
        "by_type": {},
        "total": 0,
        "by_region": {}
    }
    
    from infra_build import load_infrastructure, get_all_regions_from_country, get_asset_total
    
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    
    if not country_id:
        return result
    
    regions = get_all_regions_from_country(infra_data, country_id)
    
    for region_name, region_data in regions.items():
        region_consumption = 0
        
        for infra_type, consumption in INFRASTRUCTURE_POWER_CONSUMPTION.items():
            count = get_asset_total(region_data, infra_type)
            if count > 0:
                power = count * consumption
                region_consumption += power
                
                if infra_type not in result["by_type"]:
                    result["by_type"][infra_type] = 0
                result["by_type"][infra_type] += power
        
        result["by_region"][region_name] = region_consumption
        result["total"] += region_consumption
    
    return result


def calculate_power_balance(country_name: str, player_data: Dict) -> Dict:
    """
    Рассчитывает энергобаланс страны
    """
    from infra_build import load_infrastructure
    
    infra_data = load_infrastructure()
    
    production = calculate_total_power_production(infra_data, country_name)
    consumption = calculate_total_power_consumption(infra_data, country_name)
    
    balance = production["total"] - consumption["total"]
    deficit_percent = 0
    surplus_percent = 0
    
    if consumption["total"] > 0:
        if balance < 0:
            deficit_percent = abs(balance) / consumption["total"] * 100
    if production["total"] > 0 and balance > 0:
        surplus_percent = balance / production["total"] * 100
    
    return {
        "production": production,
        "consumption": consumption,
        "balance": balance,
        "deficit_percent": deficit_percent if balance < 0 else 0,
        "surplus_percent": surplus_percent if balance > 0 else 0,
        "status": "critical" if deficit_percent > 30 else "warning" if deficit_percent > 10 else "ok" if balance >= 0 else "deficit"
    }


# ==================== РАСЧЁТ ПОТРЕБЛЕНИЯ ГАЗА ====================

def calculate_gas_consumption(player_data: Dict, month: int = None) -> Dict:
    """
    Рассчитывает потребление газа населением с учётом климата страны
    ЗА 3 РЕАЛЬНЫХ ДНЯ (1 ИГРОВОЙ ГОД)
    """
    if month is None:
        from game_time import get_month
        month = get_month()
    
    country_name = player_data["state"]["statename"]
    population = player_data["state"]["population"]
    population_millions = population / 1_000_000
    
    climate = get_climate_zone(country_name)
    base_heating = BASE_HEATING_CONSUMPTION[climate]
    seasonal_factor = get_seasonal_factor(country_name, month)
    
    # Отопление (зависит от климата и сезона) - ЗА ГОД
    heating = population_millions * base_heating * seasonal_factor
    
    # Горячая вода (есть везде, но в тёплых странах меньше) - ЗА ГОД
    if climate in ["tropical", "subtropical"]:
        hot_water = population_millions * BASE_HOT_WATER_CONSUMPTION * 0.7
    else:
        hot_water = population_millions * BASE_HOT_WATER_CONSUMPTION
    
    # Приготовление пищи (есть везде) - ЗА ГОД
    cooking = population_millions * BASE_COOKING_CONSUMPTION
    
    total_residential = heating + hot_water + cooking
    
    # Промышленное потребление (не зависит от климата) - ЗА ГОД
    from infra_build import load_infrastructure, get_all_regions_from_country, get_asset_total
    
    industrial = 0
    infra_data = load_infrastructure()
    
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    
    if country_id:
        regions = get_all_regions_from_country(infra_data, country_id)
        for region_data in regions.values():
            civilian_count = get_asset_total(region_data, "civilian_factories")
            if civilian_count > 0:
                industrial += civilian_count * 0.01
            
            military_count = get_asset_total(region_data, "military_factories")
            if military_count > 0:
                industrial += military_count * 0.015
            
            refineries_count = get_asset_total(region_data, "refineries")
            if refineries_count > 0:
                industrial += refineries_count * 0.2
    
    return {
        "heating": heating,
        "hot_water": hot_water,
        "cooking": cooking,
        "residential_total": total_residential,
        "industrial": industrial,
        "total": total_residential + industrial,
        "seasonal_factor": seasonal_factor,
        "month": month,
        "climate": climate
    }


def check_gas_sufficiency(player_data: Dict) -> Tuple[bool, float, Dict]:
    """
    Проверяет, хватает ли газа для нужд ЗА ГОД
    Возвращает (достаточно, дефицит %, детали)
    """
    gas_available = player_data.get("resources", {}).get("gas", 0)
    consumption = calculate_gas_consumption(player_data)
    
    deficit = 0
    if gas_available < consumption["total"]:
        deficit = (consumption["total"] - gas_available) / consumption["total"] * 100
    
    return gas_available >= consumption["total"], deficit, consumption


# ==================== ПРИМЕНЕНИЕ ЭФФЕКТОВ ====================

def apply_energy_effects(player_data: Dict, power_balance: Dict, gas_deficit: float):
    """
    Применяет эффекты от недостатка энергии и газа
    """
    # Эффекты от недостатка электроэнергии
    if power_balance["deficit_percent"] > 0:
        deficit_factor = power_balance["deficit_percent"] / 10
        
        if "production_penalties" not in player_data:
            player_data["production_penalties"] = {}
        player_data["production_penalties"]["power"] = POWER_SHORTAGE_EFFECTS["production"] * deficit_factor
        
        happiness_penalty = POWER_SHORTAGE_EFFECTS["happiness"] * deficit_factor
        player_data["state"]["happiness"] = max(0, player_data["state"]["happiness"] - happiness_penalty)
        
        stability_penalty = POWER_SHORTAGE_EFFECTS["stability"] * deficit_factor
        player_data["state"]["stability"] = max(0, player_data["state"]["stability"] - stability_penalty)
    
    # Эффекты от недостатка газа
    if gas_deficit > 0:
        deficit_factor = gas_deficit / 10
        
        # В тёплых странах дефицит газа меньше влияет на счастье
        country_name = player_data["state"]["statename"]
        climate = get_climate_zone(country_name)
        
        happiness_multiplier = 1.0
        if climate in ["tropical", "subtropical"]:
            happiness_multiplier = 0.5  # В Израиле замёрзнуть сложнее
        
        happiness_penalty = GAS_SHORTAGE_EFFECTS["happiness"] * deficit_factor * happiness_multiplier
        player_data["state"]["happiness"] = max(0, player_data["state"]["happiness"] - happiness_penalty)
        
        stability_penalty = GAS_SHORTAGE_EFFECTS["stability"] * deficit_factor
        player_data["state"]["stability"] = max(0, player_data["state"]["stability"] - stability_penalty)
        
        if "health_penalties" not in player_data:
            player_data["health_penalties"] = {}
        player_data["health_penalties"]["gas"] = GAS_SHORTAGE_EFFECTS["health"] * deficit_factor


# ==================== ФОНОВАЯ ЗАДАЧА ====================

async def energy_update_loop(bot_instance):
    """
    Фоновая задача для обновления энергобаланса
    ЗАПУСК РАЗ В 3 РЕАЛЬНЫХ ДНЯ (1 ИГРОВОЙ ГОД)
    """
    await bot_instance.wait_until_ready()
    
    last_update = None
    
    while not bot_instance.is_closed():
        try:
            now = datetime.now()
            
            # Обновляем раз в 3 дня
            if last_update is None or (now - last_update).days >= 3:
                print(f"⚡ Запуск обновления энергосистемы (1 игровой год): {now.strftime('%Y-%m-%d %H:%M:%S')}")
                
                states = load_states()
                alerts = []
                
                for player_data in states["players"].values():
                    if "assigned_to" not in player_data:
                        continue
                    
                    country_name = player_data["state"]["statename"]
                    
                    power_balance = calculate_power_balance(country_name, player_data)
                    gas_sufficient, gas_deficit, gas_consumption = check_gas_sufficiency(player_data)
                    
                    # Списываем газ ЗА ВЕСЬ ГОД
                    if "resources" in player_data and "gas" in player_data["resources"]:
                        if player_data["resources"]["gas"] >= gas_consumption["total"]:
                            player_data["resources"]["gas"] -= gas_consumption["total"]
                        else:
                            player_data["resources"]["gas"] = 0
                    
                    apply_energy_effects(player_data, power_balance, gas_deficit)
                    
                    user_id = player_data["assigned_to"]
                    climate = get_climate_zone(country_name)
                    
                    # Формируем предупреждения
                    if power_balance["status"] == "critical":
                        alerts.append((user_id, f"⚠️ КРИТИЧЕСКИЙ ДЕФИЦИТ ЭНЕРГИИ в {country_name}! Не хватает {power_balance['deficit_percent']:.1f}% мощности. Заводы останавливаются!"))
                    
                    elif power_balance["status"] == "warning":
                        alerts.append((user_id, f"⚠️ Дефицит энергии в {country_name}: {power_balance['deficit_percent']:.1f}%. Рекомендуется построить новые электростанции."))
                    
                    if gas_deficit > 30:
                        if climate in ["tropical", "subtropical"]:
                            alerts.append((user_id, f"🔥 КРИТИЧЕСКИЙ ДЕФИЦИТ ГАЗА в {country_name}! За год не хватило {gas_deficit:.1f}%. Люди не могут готовить, нет горячей воды!"))
                        else:
                            alerts.append((user_id, f"❄️ КРИТИЧЕСКИЙ ДЕФИЦИТ ГАЗА в {country_name}! За год не хватило {gas_deficit:.1f}%. Население мёрзло всю зиму!"))
                    
                    elif gas_deficit > 10:
                        if climate in ["tropical", "subtropical"]:
                            alerts.append((user_id, f"🔥 Дефицит газа в {country_name}: {gas_deficit:.1f}%. Проблемы с приготовлением пищи."))
                        else:
                            alerts.append((user_id, f"❄️ Дефицит газа в {country_name}: {gas_deficit:.1f}%. Люди мёрзли, счастье падает."))
                
                save_states(states)
                last_update = now
                
                # Отправляем предупреждения
                for user_id, message in alerts:
                    try:
                        user = await bot_instance.fetch_user(int(user_id))
                        if user:
                            embed = discord.Embed(
                                title="⚡ Годовой энергетический отчёт",
                                description=message,
                                color=discord.Color.orange() if "дефицит" in message.lower() else discord.Color.red()
                            )
                            await user.send(embed=embed)
                    except:
                        pass
                
                print(f"✅ Энергосистема обновлена за год. Отправлено {len(alerts)} предупреждений")
            
            # Проверяем каждый час, но обновляем только раз в 3 дня
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"❌ Ошибка в energy_update_loop: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(3600)


# ==================== ФУНКЦИИ ДЛЯ ИНТЕРФЕЙСА ====================

def create_energy_embed(country_name: str, player_data: Dict) -> discord.Embed:
    """
    Создаёт Embed с информацией об энергосистеме
    """
    from infra_build import load_infrastructure
    
    power_balance = calculate_power_balance(country_name, player_data)
    gas_sufficient, gas_deficit, gas_consumption = check_gas_sufficiency(player_data)
    climate = get_climate_zone(country_name)
    
    climate_names = {
        "arctic": "❄️ Арктический",
        "continental": "🌲 Континентальный",
        "temperate": "🌳 Умеренный",
        "marine": "🌊 Морской",
        "subtropical": "☀️ Субтропический",
        "tropical": "🌴 Тропический"
    }
    
    if power_balance["status"] == "critical" or gas_deficit > 30:
        color = discord.Color.red()
    elif power_balance["status"] == "warning" or gas_deficit > 10:
        color = discord.Color.orange()
    else:
        color = discord.Color.green()
    
    embed = discord.Embed(
        title=f"⚡ Энергосистема {country_name}",
        description=f"{climate_names.get(climate, climate)}\nПотребление показано за **игровой год** (3 реальных дня)",
        color=color
    )
    
    # Добавляем изображения
    embed.set_image(url=ENERGY_BANNER_URL)
    embed.set_thumbnail(url=ENERGY_THUMBNAIL_URL)
    
    # Электроэнергия
    power_text = f"📊 **Генерация:** {power_balance['production']['total']:.0f} МВт\n"
    power_text += f"📈 **Потребление:** {power_balance['consumption']['total']:.0f} МВт\n"
    
    if power_balance["balance"] >= 0:
        power_text += f"✅ **Профицит:** +{power_balance['balance']:.0f} МВт ({power_balance['surplus_percent']:.1f}%)"
    else:
        power_text += f"❌ **Дефицит:** {power_balance['balance']:.0f} МВт ({power_balance['deficit_percent']:.1f}%)"
    
    embed.add_field(name="⚡ Электроэнергия", value=power_text, inline=False)
    
    # Генерация по типам
    gen_text = ""
    if power_balance["production"]["thermal"] > 0:
        gen_text += f"• ТЭС: {power_balance['production']['thermal']:.0f} МВт\n"
    if power_balance["production"]["nuclear"] > 0:
        gen_text += f"• АЭС: {power_balance['production']['nuclear']:.0f} МВт\n"
    if power_balance["production"]["hydro"] > 0:
        gen_text += f"• ГЭС: {power_balance['production']['hydro']:.0f} МВт\n"
    if power_balance["production"]["solar"] > 0:
        gen_text += f"• СЭС: {power_balance['production']['solar']:.0f} МВт\n"
    if power_balance["production"]["wind"] > 0:
        gen_text += f"• ВЭС: {power_balance['production']['wind']:.0f} МВт\n"
    
    embed.add_field(name="🏭 Генерация по типам", value=gen_text or "Нет генерации", inline=True)
    
    # Потребление газа ЗА ГОД
    gas_text = f"🏠 **Население:** {gas_consumption['residential_total']:.2f} ед/год\n"
    gas_text += f"   ├ Отопление: {gas_consumption['heating']:.2f}\n"
    gas_text += f"   ├ Горячая вода: {gas_consumption['hot_water']:.2f}\n"
    gas_text += f"   └ Приготовление: {gas_consumption['cooking']:.2f}\n"
    gas_text += f"🏭 **Промышленность:** {gas_consumption['industrial']:.2f} ед/год\n"
    gas_text += f"📈 **Всего за год:** {gas_consumption['total']:.2f} ед.\n"
    
    gas_available = player_data.get("resources", {}).get("gas", 0)
    gas_text += f"⛽ **Запасы газа:** {gas_available:.2f} ед.\n"
    
    if gas_sufficient:
        years_left = gas_available / gas_consumption["total"] if gas_consumption["total"] > 0 else 999
        gas_text += f"✅ **Газа хватит на:** {years_left:.1f} лет"
    else:
        gas_text += f"❌ **Дефицит:** {gas_deficit:.1f}%"
    
    embed.add_field(name="🔥 Газ (за год)", value=gas_text, inline=True)
    
    # Сезонный фактор
    month_names = ["январь", "февраль", "март", "апрель", "май", "июнь",
                   "июль", "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
    month = gas_consumption['month']
    
    embed.add_field(
        name="📅 Сезонность",
        value=f"Текущий месяц: **{month_names[month-1]}**\nКоэффициент отопления: **x{gas_consumption['seasonal_factor']:.1f}**",
        inline=False
    )
    
    embed.set_footer(text="Данные обновляются раз в 3 реальных дня (1 игровой год)")
    
    return embed


async def show_energy_menu(interaction_or_ctx, user_id: int):
    """
    Показать меню энергосистемы
    """
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
    
    embed = create_energy_embed(country_name, player_data)
    
    # Создаём view с кнопкой обновления
    view = EnergyMenuView(user_id, country_name, player_data)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view, ephemeral=True)


class EnergyMenuView(View):
    """View с кнопкой обновления для меню энергосистемы"""
    
    def __init__(self, user_id: int, country_name: str, player_data: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
    
    @discord.ui.button(label="🔄 Обновить", style=discord.ButtonStyle.secondary)
    async def refresh_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Перезагружаем данные игрока
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                self.player_data = data
                break
        
        embed = create_energy_embed(self.country_name, self.player_data)
        await interaction.response.edit_message(embed=embed, view=self)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_energy_menu',
    'energy_update_loop',
    'calculate_power_balance',
    'check_gas_sufficiency',
    'INFRASTRUCTURE_POWER_CONSUMPTION'
]

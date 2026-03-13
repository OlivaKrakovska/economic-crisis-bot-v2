# production_effects.py - Модуль для применения бонусов инфраструктуры к производству

from infra_build import (
    calculate_production_bonus, calculate_power_generation,
    calculate_storage_capacity, calculate_research_bonus,
    calculate_gov_efficiency_bonus, calculate_pp_gain_bonus,
    load_infrastructure, INFRASTRUCTURE_COSTS
)
from utils import load_states, save_states
import asyncio
from datetime import datetime, timedelta

def get_all_regions_from_country(infra_data, country_id):
    """
    Получает все регионы страны с учётом экономических районов
    """
    country_data = infra_data["infrastructure"].get(country_id, {})
    regions = {}
    
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

def apply_infrastructure_bonuses(player_data, country_name):
    """
    Применяет бонусы от всей инфраструктуры страны к игроку
    """
    infra_data = load_infrastructure()
    
    # Находим ID страны
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    
    if not country_id:
        return player_data
    
    # Получаем все регионы с учётом структуры
    regions = get_all_regions_from_country(infra_data, country_id)
    
    # Суммируем бонусы по всем регионам
    total_production_bonus = {}
    total_power = 0
    total_fuel_consumption = {
        "coal": 0,
        "oil": 0,
        "gas": 0,
        "uranium": 0
    }
    total_storage = {}
    total_research_bonus = 1.0
    total_gov_bonus = 0
    total_pp_bonus = 0
    
    for region_name, region_data in regions.items():
        # Военные заводы - дают бонус ко всей военной технике, включая дроны-камикадзе
        if "military_factories" in region_data:
            count = region_data["military_factories"]
            if count > 0:
                # Сухопутная техника
                if "ground" not in total_production_bonus:
                    total_production_bonus["ground"] = 1.0
                total_production_bonus["ground"] += count * 0.02
                
                # Авиация (включая дроны-камикадзе)
                if "air" not in total_production_bonus:
                    total_production_bonus["air"] = 1.0
                total_production_bonus["air"] += count * 0.02
                
                # Ракеты
                if "missiles" not in total_production_bonus:
                    total_production_bonus["missiles"] = 1.0
                total_production_bonus["missiles"] += count * 0.02
                
                # Дроны-камикадзе (отдельно, но также получают бонус от военных заводов)
                if "air.kamikaze_uav" not in total_production_bonus:
                    total_production_bonus["air.kamikaze_uav"] = 1.0
                total_production_bonus["air.kamikaze_uav"] += count * 0.02
        
        # Верфи
        if "shipyards" in region_data:
            count = region_data["shipyards"]
            if count > 0:
                for prod in ["navy.boats", "navy.corvettes", "navy.destroyers", 
                           "navy.cruisers", "navy.aircraft_carriers", "navy.submarines"]:
                    if prod not in total_production_bonus:
                        total_production_bonus[prod] = 1.0
                    total_production_bonus[prod] += count * 0.05
        
        # Гражданские фабрики
        if "civilian_factories" in region_data:
            count = region_data["civilian_factories"]
            if count > 0:
                if "civil" not in total_production_bonus:
                    total_production_bonus["civil"] = 1.0
                total_production_bonus["civil"] += count * 0.03
        
        # НПЗ
        if "refineries" in region_data:
            count = region_data["refineries"]
            if count > 0:
                for prod in ["chemicals", "pharmaceuticals"]:
                    if prod not in total_production_bonus:
                        total_production_bonus[prod] = 1.0
                    total_production_bonus[prod] += count * 0.10
        
        # Энергия и потребление топлива (СУТОЧНОЕ)
        if "thermal_power" in region_data:
            count = region_data["thermal_power"]
            if count > 0:
                total_power += count * 100
                total_fuel_consumption["coal"] += count * 0.024
                total_fuel_consumption["oil"] += count * 0.012
        
        if "nuclear_power" in region_data:
            count = region_data["nuclear_power"]
            if count > 0:
                total_power += count * 500
                total_fuel_consumption["uranium"] += count * 0.002
        
        if "hydro_power" in region_data:
            count = region_data["hydro_power"]
            if count > 0:
                total_power += count * 150
        
        if "solar_power" in region_data:
            count = region_data["solar_power"]
            if count > 0:
                total_power += count * 40
        
        if "wind_power" in region_data:
            count = region_data["wind_power"]
            if count > 0:
                total_power += count * 60
        
        # Хранилища (нефтебазы)
        if "oil_depots" in region_data:
            count = region_data["oil_depots"]
            if count > 0:
                total_storage["oil"] = total_storage.get("oil", 0) + count * 1000
                total_storage["gas"] = total_storage.get("gas", 0) + count * 500
        
        # ЦОД - бонусы к исследованиям и эффективности
        if "internet_infrastructure" in region_data:
            count = region_data["internet_infrastructure"]
            if count > 0:
                total_research_bonus += count * 0.01
                total_gov_bonus += count * 1
                total_pp_bonus += count * 0.01
    
    if "infrastructure_bonuses" not in player_data:
        player_data["infrastructure_bonuses"] = {}
    
    player_data["infrastructure_bonuses"]["production"] = total_production_bonus
    player_data["infrastructure_bonuses"]["power"] = total_power
    player_data["infrastructure_bonuses"]["fuel_consumption"] = total_fuel_consumption
    player_data["infrastructure_bonuses"]["storage"] = total_storage
    player_data["infrastructure_bonuses"]["research"] = total_research_bonus
    player_data["infrastructure_bonuses"]["gov_efficiency"] = total_gov_bonus
    player_data["infrastructure_bonuses"]["pp_gain"] = total_pp_bonus
    
    return player_data

def get_production_time_with_bonus(base_time, product_type, player_data):
    """
    Возвращает скорректированное время производства с учетом бонусов
    """
    bonuses = player_data.get("infrastructure_bonuses", {}).get("production", {})
    
    bonus_multiplier = 1.0
    
    # Прямое совпадение типа продукта
    if product_type in bonuses:
        bonus_multiplier = bonuses[product_type]
    else:
        # Проверяем категории
        for bonus_type, bonus_value in bonuses.items():
            # Точное совпадение категории
            if bonus_type in product_type:
                bonus_multiplier = max(bonus_multiplier, bonus_value)
            
            # Для военной техники (включая дроны-камикадзе)
            elif product_type.startswith("air.") and bonus_type == "air":
                bonus_multiplier = max(bonus_multiplier, bonus_value)
            
            # Для флота
            elif product_type.startswith("navy.") and bonus_type.startswith("navy."):
                bonus_multiplier = max(bonus_multiplier, bonus_value)
            
            # Для гражданской продукции
            elif "civil" in product_type and bonus_type == "civil":
                bonus_multiplier = max(bonus_multiplier, bonus_value)
            
            # Для дронов-камикадзе (отдельная проверка)
            elif product_type == "air.kamikaze_uav" and bonus_type == "air":
                bonus_multiplier = max(bonus_multiplier, bonus_value)
    
    # Минимальный множитель 1.0 (не может быть меньше 1)
    bonus_multiplier = max(1.0, bonus_multiplier)
    
    return int(base_time / bonus_multiplier)

def check_fuel_availability(player_data):
    """
    Проверяет наличие топлива для работы электростанций (СУТОЧНАЯ проверка)
    """
    bonuses = player_data.get("infrastructure_bonuses", {})
    fuel_consumption = bonuses.get("fuel_consumption", {})
    
    if not fuel_consumption or all(v == 0 for v in fuel_consumption.values()):
        return True, "Нет потребления топлива"
    
    resources = player_data.get("resources", {})
    missing_fuels = []
    
    # Проверяем наличие каждого вида топлива (на день)
    if fuel_consumption.get("coal", 0) > 0:
        available = resources.get("coal", 0)
        if available < fuel_consumption["coal"]:
            missing_fuels.append(f"уголь (нужно {fuel_consumption['coal']:.3f}/день, есть {available})")
    
    if fuel_consumption.get("oil", 0) > 0:
        available = resources.get("oil", 0)
        if available < fuel_consumption["oil"]:
            missing_fuels.append(f"нефть (нужно {fuel_consumption['oil']:.3f}/день, есть {available})")
    
    if fuel_consumption.get("gas", 0) > 0:
        available = resources.get("gas", 0)
        if available < fuel_consumption["gas"]:
            missing_fuels.append(f"газ (нужно {fuel_consumption['gas']:.3f}/день, есть {available})")
    
    if fuel_consumption.get("uranium", 0) > 0:
        available = resources.get("uranium", 0)
        if available < fuel_consumption["uranium"]:
            missing_fuels.append(f"уран (нужно {fuel_consumption['uranium']:.3f}/день, есть {available})")
    
    if missing_fuels:
        return False, f"Не хватает топлива: {', '.join(missing_fuels)}"
    
    return True, "Топлива достаточно"

def consume_fuel(player_data, days=1):
    """
    Списывает топливо за работу электростанций (СУТОЧНОЕ списание)
    Возвращает True если списание прошло успешно, False если топлива не хватило
    """
    states = load_states()
    player_state = None
    player_id = None
    
    for pid, data in states["players"].items():
        if data.get("assigned_to") == player_data.get("assigned_to"):
            player_state = data
            player_id = pid
            break
    
    if not player_state:
        return False
    
    bonuses = player_state.get("infrastructure_bonuses", {})
    fuel_consumption = bonuses.get("fuel_consumption", {})
    
    if not fuel_consumption or all(v == 0 for v in fuel_consumption.values()):
        return True
    
    resources = player_state.get("resources", {})
    
    fuel_shortage = False
    for fuel, amount_per_day in fuel_consumption.items():
        total_needed = amount_per_day * days
        if resources.get(fuel, 0) < total_needed:
            fuel_shortage = True
            break
    
    if fuel_shortage:
        return False
    
    for fuel, amount_per_day in fuel_consumption.items():
        total_needed = amount_per_day * days
        if fuel in resources:
            resources[fuel] = max(0, resources[fuel] - total_needed)
    
    states["players"][player_id] = player_state
    save_states(states)
    
    return True

def get_power_status(player_data):
    """
    Возвращает статус энергосистемы (СУТОЧНЫЙ)
    """
    bonuses = player_data.get("infrastructure_bonuses", {})
    power = bonuses.get("power", 0)
    fuel_consumption = bonuses.get("fuel_consumption", {})
    resources = player_data.get("resources", {})
    
    status = f"⚡ Общая генерация: {power} МВт\n"
    
    if fuel_consumption and any(v > 0 for v in fuel_consumption.values()):
        status += "⛽ Потребление топлива в день:\n"
        if fuel_consumption.get("coal", 0) > 0:
            available = resources.get("coal", 0)
            days = int(available / fuel_consumption["coal"]) if fuel_consumption["coal"] > 0 else 0
            status += f"  • Уголь: {fuel_consumption['coal']:.3f} (запас: {available}, хватит на {days} дн)\n"
        
        if fuel_consumption.get("oil", 0) > 0:
            available = resources.get("oil", 0)
            days = int(available / fuel_consumption["oil"]) if fuel_consumption["oil"] > 0 else 0
            status += f"  • Нефть: {fuel_consumption['oil']:.3f} (запас: {available}, хватит на {days} дн)\n"
        
        if fuel_consumption.get("gas", 0) > 0:
            available = resources.get("gas", 0)
            days = int(available / fuel_consumption["gas"]) if fuel_consumption["gas"] > 0 else 0
            status += f"  • Газ: {fuel_consumption['gas']:.3f} (запас: {available}, хватит на {days} дн)\n"
        
        if fuel_consumption.get("uranium", 0) > 0:
            available = resources.get("uranium", 0)
            days = int(available / fuel_consumption["uranium"]) if fuel_consumption["uranium"] > 0 else 0
            status += f"  • Уран: {fuel_consumption['uranium']:.3f} (запас: {available}, хватит на {days} дн)\n"
    
    return status

def get_production_bonus_info(player_data):
    """
    Возвращает информацию о производственных бонусах
    """
    bonuses = player_data.get("infrastructure_bonuses", {}).get("production", {})
    
    info = {}
    for prod_type, bonus in bonuses.items():
        if prod_type == "ground":
            info["Сухопутная техника"] = f"x{bonus:.2f}"
        elif prod_type == "air":
            info["Авиация (включая дроны-камикадзе)"] = f"x{bonus:.2f}"
        elif prod_type == "missiles":
            info["Ракеты"] = f"x{bonus:.2f}"
        elif prod_type == "civil":
            info["Гражданская продукция"] = f"x{bonus:.2f}"
        elif prod_type == "air.kamikaze_uav":
            info["Дроны-камикадзе"] = f"x{bonus:.2f}"
        elif prod_type.startswith("navy."):
            info[prod_type.replace("navy.", "Флот: ")] = f"x{bonus:.2f}"
        elif prod_type in ["chemicals", "pharmaceuticals"]:
            info[prod_type.capitalize()] = f"x{bonus:.2f}"
    
    return info

# ==================== ЭКСПОРТ ФУНКЦИЙ ====================

__all__ = [
    'apply_infrastructure_bonuses',
    'get_production_time_with_bonus',
    'check_fuel_availability',
    'consume_fuel',
    'get_power_status',
    'get_production_bonus_info'
]

# strikes.py - Модуль для управления ударами БПЛА и стратегического оружия
# ВЕРСИЯ 7.0 - С поддержкой новой структуры активов (total/ownership)

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import asyncio
import json
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from infra_build import (
    load_infrastructure, save_infrastructure, get_all_regions_from_country,
    get_asset_total, get_asset_ownership, remove_asset_from_region, ASSET_FIELDS
)

# Файлы для хранения данных
STRIKES_FILE = 'strikes.json'
STRIKE_QUEUE_FILE = 'strike_queue.json'
DISTANCES_FILE = 'distances.json'

# ID канала для логов ударов
STRIKE_LOG_CHANNEL_ID = 1263440933232578630

# Константы для потерь
FUEL_LOSS_PER_HIT = {
    "oil": (0.5, 2.0),
    "gas": (0.2, 1.0),
    "coal": (0.3, 1.5),
    "uranium": (0.05, 0.2)
}

# Максимальное снижение стабильности и счастья за один удар
MAX_STABILITY_DROP = 5
MAX_HAPPINESS_DROP = 5


# ==================== ФУНКЦИЯ ДЛЯ БОНУСА ОТ СПУТНИКОВ ====================

def get_intercept_difficulty_boost(attacker_country: str) -> float:
    """
    Возвращает бонус к сложности перехвата от спутников атакующей страны.
    Если модуль спутников недоступен, возвращает 0.
    """
    try:
        from satellites import get_satellite_bonuses
        bonuses = get_satellite_bonuses(attacker_country)
        return bonuses.get("intercept_difficulty", 0.0)
    except ImportError:
        return 0.0
    except Exception as e:
        print(f"Ошибка получения бонуса от спутников: {e}")
        return 0.0


# ==================== ЗАГРУЗКА РАССТОЯНИЙ ====================

def load_distances() -> Dict:
    """Загрузка данных о расстояниях между регионами"""
    try:
        with open(DISTANCES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        return {}

try:
    from region_coordinates import get_region_coordinates, region_exists
    COORDINATES_AVAILABLE = True
except ImportError:
    COORDINATES_AVAILABLE = False
    print("Модуль region_coordinates не найден. Будет использоваться только файл distances.json")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Рассчитывает расстояние между двумя точками на Земле по формуле гаверсинуса"""
    R = 6371
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return round(R * c)


def get_region_coordinates_from_infra(country: str, region: str) -> Optional[Dict]:
    """Получает координаты региона из инфраструктуры"""
    infra = load_infrastructure()
    
    for cid, cdata in infra["infrastructure"].items():
        if cdata.get("country") == country:
            for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                for region_name, region_data in econ_data.get("regions", {}).items():
                    if region_name == region:
                        if "lat" in region_data and "lon" in region_data:
                            return {"lat": region_data["lat"], "lon": region_data["lon"]}
    return None


def get_region_distance(attacker_country: str, attacker_region: str, 
                       target_country: str, target_region: str) -> int:
    """Возвращает расстояние между регионами в км"""
    distances = load_distances()
    
    try:
        return distances[attacker_country][target_country][attacker_region]
    except KeyError:
        pass
    
    try:
        return distances[target_country][attacker_country][target_region]
    except KeyError:
        pass
    
    attacker_coords = get_region_coordinates_from_infra(attacker_country, attacker_region)
    target_coords = get_region_coordinates_from_infra(target_country, target_region)
    
    if attacker_coords and target_coords:
        distance = haversine_distance(
            attacker_coords["lat"], attacker_coords["lon"],
            target_coords["lat"], target_coords["lon"]
        )
        return distance
    
    if COORDINATES_AVAILABLE:
        try:
            attacker_coords = get_region_coordinates(attacker_country, attacker_region)
            target_coords = get_region_coordinates(target_country, target_region)
            
            if attacker_coords and target_coords:
                distance = haversine_distance(
                    attacker_coords["lat"], attacker_coords["lon"],
                    target_coords["lat"], target_coords["lon"]
                )
                return distance
        except Exception as e:
            print(f"Ошибка при расчете расстояния по координатам: {e}")
    
    return 9999


def is_region_reachable(attacker_country: str, attacker_region: str,
                       target_country: str, target_region: str,
                       weapon_range: int) -> Tuple[bool, int]:
    """Проверяет, достижим ли целевой регион для данного оружия"""
    distance = get_region_distance(attacker_country, attacker_region, target_country, target_region)
    return distance <= weapon_range, distance


def get_all_country_regions(country_name: str) -> List[str]:
    """Возвращает список всех регионов страны из инфраструктуры"""
    infra = load_infrastructure()
    regions = []
    
    for cid, cdata in infra["infrastructure"].items():
        if cdata.get("country") == country_name:
            for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                for region_name in econ_data.get("regions", {}).keys():
                    regions.append(region_name)
            break
    
    return regions


def get_country_economic_regions(country_name: str) -> Dict[str, Dict]:
    """Возвращает экономические районы страны с их регионами"""
    infra = load_infrastructure()
    
    for cid, cdata in infra.get("infrastructure", {}).items():
        if cdata.get("country") == country_name:
            return cdata.get("economic_regions", {})
    
    return {}


def get_regions_in_economic_region(country_name: str, econ_region: str) -> Dict[str, Dict]:
    """Возвращает регионы в конкретном экономическом районе"""
    economic_regions = get_country_economic_regions(country_name)
    
    if econ_region in economic_regions:
        return economic_regions[econ_region].get("regions", {})
    
    return {}


def get_player_regions(player_country: str) -> List[str]:
    """Возвращает список всех регионов игрока для запуска ударов"""
    infra = load_infrastructure()
    regions = []
    
    for cid, cdata in infra.get("infrastructure", {}).items():
        if cdata.get("country") == player_country:
            for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                for region_name in econ_data.get("regions", {}).keys():
                    regions.append(region_name)
            break
    
    return regions


def is_region_coastal(region_name: str, country_name: str) -> bool:
    """Проверяет, является ли регион прибрежным"""
    infra = load_infrastructure()
    
    for cid, cdata in infra["infrastructure"].items():
        if cdata.get("country") == country_name:
            for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                for r_name, r_data in econ_data.get("regions", {}).items():
                    if r_name == region_name:
                        return r_data.get("coastal", False)
            break
    
    return False


def get_region_pvo_data(region_data: Dict) -> Dict[str, int]:
    """Возвращает словарь с количеством ПВО каждого типа в регионе (используя get_asset_total)"""
    return {
        "long_range_air_defense": get_asset_total(region_data, "long_range_air_defense"),
        "short_range_air_defense": get_asset_total(region_data, "short_range_air_defense"),
        "zdprk": get_asset_total(region_data, "zdprk"),
        "zas": get_asset_total(region_data, "zas"),
        "radar_systems": get_asset_total(region_data, "radar_systems")
    }


def get_allied_fleet_bonus(target_country: str, target_region: str, attacker_country: str) -> float:
    """Получает бонус от союзного флота в соседней морской зоне"""
    try:
        from navy import SeaZone, get_fleets_in_zone
        from conflicts import are_countries_allied
    except ImportError:
        return 0.0
    
    if not is_region_coastal(target_region, target_country):
        return 0.0
    
    from maritime_trade import get_sea_zone_from_region
    sea_zone = get_sea_zone_from_region(target_region)
    
    if not sea_zone:
        return 0.0
    
    bonus = 0.0
    for zone in SeaZone:
        if zone.value == sea_zone:
            fleets = get_fleets_in_zone(target_country, zone)
            for fleet in fleets:
                fleet_country = fleet.get("country", "")
                if fleet_country != target_country and are_countries_allied(attacker_country, fleet_country):
                    bonus += fleet.get("total_ships", 0) * 0.5
            break
    
    return min(bonus, 50.0)


def calculate_region_air_defense_strength(target_country: str, target_region: str, 
                                           attacker_country: str = None) -> float:
    """Рассчитывает силу ПВО в конкретном регионе с учётом бонусов от флота"""
    infra = load_infrastructure()
    
    region_data = None
    for cid, cdata in infra["infrastructure"].items():
        if cdata.get("country") == target_country:
            for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                for r_name, r_data in econ_data.get("regions", {}).items():
                    if r_name == target_region:
                        region_data = r_data
                        break
            break
    
    if not region_data:
        return 0.0
    
    strength = 0.0
    strength += get_asset_total(region_data, "short_range_air_defense") * 3.0
    strength += get_asset_total(region_data, "long_range_air_defense") * 5.0
    strength += get_asset_total(region_data, "zdprk") * 2.0
    strength += get_asset_total(region_data, "zas") * 1.0
    strength += get_asset_total(region_data, "radar_systems") * 2.0
    
    if attacker_country:
        fleet_bonus = get_allied_fleet_bonus(target_country, target_region, attacker_country)
        strength = strength * (1 + fleet_bonus / 100)
    
    return strength


# ==================== КОНСТАНТЫ ====================

STRIKE_WEAPONS = {
    "kamikaze_uav": {
        "name": "Дроны-камикадзе",
        "description": "Барражирующие боеприпасы. Дешёвые, производятся в большом количестве, но легко сбиваются.",
        "army_path": "air.kamikaze_drones",
        "base_accuracy": 0.55,
        "intercept_difficulty": 0.1,
        "infrastructure_damage_multiplier": 1.0,
        "cooldown": 3,
        "range": 1000,
        "salvo_size": 50,
        "naval_damage_multiplier": 0.5
    },
    "drones": {
        "name": "Ударные БПЛА",
        "description": "Беспилотники средней дальности. Хорошая точность, умеренная стоимость.",
        "army_path": "air.attack_uav",
        "base_accuracy": 0.8,
        "intercept_difficulty": 0.2,
        "infrastructure_damage_multiplier": 1.0,
        "cooldown": 6,
        "range": 800,
        "salvo_size": 20,
        "naval_damage_multiplier": 0.3
    },
    "recon_uav": {
        "name": "Разведывательные БПЛА",
        "description": "Лёгкие беспилотники. Могут нести небольшие боеприпасы, высокая точность.",
        "army_path": "air.recon_uav",
        "base_accuracy": 0.9,
        "intercept_difficulty": 0.15,
        "infrastructure_damage_multiplier": 0.8,
        "cooldown": 4,
        "range": 400,
        "salvo_size": 15,
        "naval_damage_multiplier": 0.2
    },
    "cruise_missiles": {
        "name": "Крылатые ракеты",
        "description": "Дозвуковые ракеты, летят на малой высоте. Высокая точность, сложнее перехватить.",
        "army_path": "missiles.cruise_missiles",
        "base_accuracy": 0.9,
        "intercept_difficulty": 0.4,
        "infrastructure_damage_multiplier": 1.2,
        "cooldown": 24,
        "range": 2000,
        "salvo_size": 10,
        "naval_damage_multiplier": 0.6
    },
    "ballistic_missiles": {
        "name": "Баллистические ракеты",
        "description": "Сверхзвуковые ракеты. Очень сложно перехватить, высокая скорость.",
        "army_path": "missiles.ballistic_missiles",
        "base_accuracy": 0.75,
        "intercept_difficulty": 0.7,
        "infrastructure_damage_multiplier": 1.5,
        "cooldown": 48,
        "range": 3000,
        "salvo_size": 5,
        "naval_damage_multiplier": 0.8
    },
    "hypersonic_missiles": {
        "name": "Гиперзвуковые ракеты",
        "description": "Новейшее оружие. Очень сложно перехватить, огромная скорость.",
        "army_path": "missiles.hypersonic_missiles",
        "base_accuracy": 1.0,
        "intercept_difficulty": 0.85,
        "infrastructure_damage_multiplier": 2.0,
        "cooldown": 72,
        "range": 2500,
        "salvo_size": 2,
        "naval_damage_multiplier": 1.2
    },
    "usv_attack": {
        "name": "Наводные дроны",
        "description": "Беспилотные катера-камикадзе. Запускаются из прибрежных регионов, атакуют морские цели.",
        "army_path": "navy.usv_attack",
        "base_accuracy": 0.7,
        "intercept_difficulty": 0.3,
        "infrastructure_damage_multiplier": 1.2,
        "cooldown": 8,
        "range": 1000,
        "salvo_size": 10,
        "naval_damage_multiplier": 0.8,
        "requires_coastal_launch": True
    }
}


TARGET_TYPES = {
    "military_factories": {
        "name": "Военные заводы",
        "description": "Производство военной техники и вооружения",
        "infra_fields": ["military_factories"],
        "priority": 1,
        "happiness_impact": 2,
        "stability_impact": 2,
        "civilian_casualty_chance": 0.6,
        "civilian_casualty_base": 50,
        "target_value": 2.0,
        "fuel_loss": {}
    },
    "radar_systems": {
        "name": "РЛС",
        "description": "Радиолокационные станции и системы обнаружения",
        "infra_fields": ["radar_systems"],
        "priority": 1,
        "happiness_impact": 1,
        "stability_impact": 3,
        "civilian_casualty_chance": 0.4,
        "civilian_casualty_base": 20,
        "target_value": 1.0,
        "fuel_loss": {}
    },
    "air_defense_assets": {
        "name": "Средства ПВО",
        "description": "Уничтожение зенитных ракетных комплексов и систем противовоздушной обороны",
        "infra_fields": ["short_range_air_defense", "long_range_air_defense", "zdprk", "zas"],
        "priority": 1,
        "happiness_impact": 1,
        "stability_impact": 3,
        "civilian_casualty_chance": 0.3,
        "civilian_casualty_base": 20,
        "target_value": 2.0,
        "fuel_loss": {},
        "is_military": True
    },
    "civilian_factories": {
        "name": "Гражданские фабрики",
        "description": "Производство гражданской продукции",
        "infra_fields": ["civilian_factories"],
        "priority": 2,
        "happiness_impact": 3,
        "stability_impact": 2,
        "civilian_casualty_chance": 0.7,
        "civilian_casualty_base": 80,
        "target_value": 1.5,
        "fuel_loss": {}
    },
    "shipyards": {
        "name": "Верфи",
        "description": "Строительство и ремонт кораблей",
        "infra_fields": ["shipyards"],
        "priority": 1,
        "happiness_impact": 2,
        "stability_impact": 2,
        "civilian_casualty_chance": 0.6,
        "civilian_casualty_base": 60,
        "target_value": 1.8,
        "fuel_loss": {}
    },
    "refineries": {
        "name": "НПЗ",
        "description": "Нефтеперерабатывающие заводы",
        "infra_fields": ["refineries"],
        "priority": 1,
        "happiness_impact": 3,
        "stability_impact": 3,
        "civilian_casualty_chance": 0.8,
        "civilian_casualty_base": 100,
        "target_value": 1.5,
        "fuel_loss": ["oil", "gas"]
    },
    "oil_depots": {
        "name": "Нефтебазы",
        "description": "Хранилища нефти и нефтепродуктов",
        "infra_fields": ["oil_depots"],
        "priority": 1,
        "happiness_impact": 3,
        "stability_impact": 3,
        "civilian_casualty_chance": 0.7,
        "civilian_casualty_base": 80,
        "target_value": 1.5,
        "fuel_loss": ["oil", "gas"]
    },
    "thermal_power": {
        "name": "ТЭС",
        "description": "Тепловые электростанции",
        "infra_fields": ["thermal_power"],
        "priority": 1,
        "happiness_impact": 5,
        "stability_impact": 3,
        "civilian_casualty_chance": 0.6,
        "civilian_casualty_base": 60,
        "target_value": 1.8,
        "fuel_loss": ["coal", "oil", "gas"]
    },
    "hydro_power": {
        "name": "ГЭС",
        "description": "Гидроэлектростанции",
        "infra_fields": ["hydro_power"],
        "priority": 1,
        "happiness_impact": 5,
        "stability_impact": 3,
        "civilian_casualty_chance": 0.4,
        "civilian_casualty_base": 40,
        "target_value": 1.8,
        "fuel_loss": []
    },
    "solar_power": {
        "name": "СЭС",
        "description": "Солнечные электростанции",
        "infra_fields": ["solar_power"],
        "priority": 2,
        "happiness_impact": 3,
        "stability_impact": 2,
        "civilian_casualty_chance": 0.3,
        "civilian_casualty_base": 20,
        "target_value": 1.2,
        "fuel_loss": []
    },
    "wind_power": {
        "name": "ВЭС",
        "description": "Ветровые электростанции",
        "infra_fields": ["wind_power"],
        "priority": 2,
        "happiness_impact": 3,
        "stability_impact": 2,
        "civilian_casualty_chance": 0.3,
        "civilian_casualty_base": 20,
        "target_value": 1.2,
        "fuel_loss": []
    },
    "data_centers": {
        "name": "ЦОД",
        "description": "Центры обработки данных и интернет-инфраструктура",
        "infra_fields": ["internet_infrastructure"],
        "priority": 2,
        "happiness_impact": 2,
        "stability_impact": 1,
        "civilian_casualty_chance": 0.4,
        "civilian_casualty_base": 30,
        "target_value": 1.2,
        "fuel_loss": {}
    },
    "office_centers": {
        "name": "Офисные центры",
        "description": "Бизнес-центры и офисные здания",
        "infra_fields": ["office_centers"],
        "priority": 3,
        "happiness_impact": 2,
        "stability_impact": 1,
        "civilian_casualty_chance": 0.7,
        "civilian_casualty_base": 100,
        "target_value": 1.0,
        "fuel_loss": {}
    },
    "navy_fleet": {
        "name": "Военно-морской флот",
        "description": "Уничтожение кораблей противника в морской зоне",
        "infra_fields": [],
        "priority": 1,
        "happiness_impact": 2,
        "stability_impact": 4,
        "civilian_casualty_chance": 0.2,
        "civilian_casualty_base": 10,
        "target_value": 3.0,
        "fuel_loss": {},
        "is_naval": True
    },
    "trade_convoy": {
        "name": "Торговые конвои",
        "description": "Уничтожение торговых судов противника в морской зоне",
        "infra_fields": [],
        "priority": 2,
        "happiness_impact": 3,
        "stability_impact": 2,
        "civilian_casualty_chance": 0.4,
        "civilian_casualty_base": 30,
        "target_value": 1.5,
        "fuel_loss": {},
        "is_trade": True
    }
}


# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_strikes():
    try:
        with open(STRIKES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"strikes": [], "stats": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"strikes": [], "stats": {}}


def save_strikes(data):
    with open(STRIKES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_strike_queue():
    try:
        with open(STRIKE_QUEUE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_strikes": [], "completed_strikes": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_strikes": [], "completed_strikes": []}


def save_strike_queue(data):
    with open(STRIKE_QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ==================== ФУНКЦИИ ДЛЯ ПРОВЕРКИ СОСТОЯНИЯ ВОЙНЫ ====================

def get_countries_at_war(player_country: str) -> List[str]:
    try:
        from conflicts import get_countries_at_war_with
        return get_countries_at_war_with(player_country)
    except ImportError:
        all_countries = ["США", "Россия", "Китай", "Германия", "Великобритания", 
                         "Франция", "Япония", "Израиль", "Украина", "Иран", "Турция",
                         "Канада", "Польша", "Бразилия", "Швеция", "Финляндия",
                         "Норвегия", "Египет", "КНДР", "Сирия"]
        return [c for c in all_countries if c != player_country]
    except Exception as e:
        print(f"Ошибка получения списка стран в состоянии войны: {e}")
        return []


# ==================== ФУНКЦИИ ДЛЯ РАСЧЁТА ПЕРЕХВАТА ====================

def calculate_region_interception_chance(weapon_type: str, target_country: str, target_region: str,
                                          quantity: int, attacker_country: str = None) -> Tuple[float, float, Dict[str, int]]:
    """Рассчитывает шанс перехвата для конкретного региона с учётом ПВО в нём"""
    defense_strength = calculate_region_air_defense_strength(target_country, target_region, attacker_country)
    weapon = STRIKE_WEAPONS[weapon_type]
    base_difficulty = weapon["intercept_difficulty"]
    
    if attacker_country:
        satellite_boost = get_intercept_difficulty_boost(attacker_country)
        base_difficulty += satellite_boost
        base_difficulty = min(0.95, base_difficulty)
    
    if defense_strength <= 0:
        base_chance = 0.0
    else:
        base_chance = 1.0 - (1.0 / (1.0 + defense_strength / 30.0))
    
    base_chance = base_chance * (1.0 - base_difficulty)
    
    if quantity <= 1:
        saturation_factor = 1.0
    else:
        saturation_factor = 1.0 / math.log10(quantity + 9) * 2.0
        saturation_factor = max(0.3, min(1.0, saturation_factor))
    
    final_chance = base_chance * saturation_factor
    final_chance = max(0.01, min(0.98, final_chance))
    
    infra = load_infrastructure()
    pvo_data = {}
    for cid, cdata in infra["infrastructure"].items():
        if cdata.get("country") == target_country:
            for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                for r_name, r_data in econ_data.get("regions", {}).items():
                    if r_name == target_region:
                        pvo_data = get_region_pvo_data(r_data)
                        break
            break
    
    return base_chance, final_chance, pvo_data


def calculate_surviving_weapons_with_pvo(weapon_type: str, target_country: str, target_region: str,
                                          quantity: int, attacker_country: str = None, is_decoy: bool = False) -> Tuple[int, float, float, Dict[str, int]]:
    """Рассчитывает количество выживших после ПВО с детальным учётом уничтоженных средств ПВО"""
    if quantity <= 0:
        return 0, 0.0, 0.0, {}
    
    actual_quantity = quantity
    if is_decoy:
        actual_quantity = quantity * 2
    
    base_chance, final_chance, initial_pvo = calculate_region_interception_chance(
        weapon_type, target_country, target_region, actual_quantity, attacker_country
    )
    
    intercepted = 0
    for _ in range(actual_quantity):
        if random.random() < final_chance:
            intercepted += 1
    
    surviving = actual_quantity - intercepted
    
    destroyed_pvo = {}
    if intercepted > 0 and sum(initial_pvo.values()) > 0:
        pvo_types = ["long_range_air_defense", "short_range_air_defense", "zdprk", "zas", "radar_systems"]
        pvo_weights = {
            "long_range_air_defense": 5,
            "short_range_air_defense": 3,
            "zdprk": 2,
            "zas": 1,
            "radar_systems": 2
        }
        
        remaining_intercepted = intercepted
        for pvo_type in pvo_types:
            if remaining_intercepted <= 0:
                break
            count = initial_pvo.get(pvo_type, 0)
            if count > 0:
                weight = pvo_weights.get(pvo_type, 1)
                max_destroy = min(count, remaining_intercepted)
                destroy = random.randint(0, max_destroy)
                if destroy > 0:
                    destroyed_pvo[pvo_type] = destroy
                    remaining_intercepted -= destroy
    
    return surviving, base_chance, final_chance, destroyed_pvo


# ==================== ФУНКЦИИ ДЛЯ УДАРОВ ПО МОРСКИМ ЦЕЛЯМ ====================

def get_fleets_in_zone(target_country: str, sea_zone) -> List[Dict]:
    """Получает флоты страны в указанной морской зоне"""
    try:
        from navy import load_navy_data, Fleet
    except ImportError:
        return []
    
    navy_data = load_navy_data()
    fleets = []
    
    for fleet_data in navy_data.get("fleets", []):
        fleet = Fleet.from_dict(fleet_data)
        if fleet.country == target_country and fleet.current_zone == sea_zone:
            if fleet.get_total_ships() > 0:
                fleets.append({
                    "id": fleet.id,
                    "name": fleet.name,
                    "ships": fleet.ships.copy(),
                    "total_ships": fleet.get_total_ships(),
                    "zone": fleet.current_zone.value
                })
    
    return fleets


def get_trade_ships_in_zone(target_country: str, sea_zone, include_sailing: bool = True) -> List[Dict]:
    """Получает торговые суда страны в морской зоне"""
    try:
        from maritime_trade import get_ships_by_sea_region, get_ships_by_country
        from navy import SeaZone
    except ImportError:
        return []
    
    ships_in_zone = []
    
    try:
        ships_by_country = get_ships_by_sea_region(sea_zone)
        if target_country in ships_by_country:
            for ship in ships_by_country[target_country]:
                if include_sailing or ship.status not in ["sailing", "en_route"]:
                    ships_in_zone.append({
                        "id": ship.id,
                        "name": ship.name,
                        "type": ship.type,
                        "cargo_value": ship.cargo_value,
                        "cargo": ship.cargo,
                        "status": ship.status,
                        "corporation_id": ship.corporation_id
                    })
    except Exception as e:
        print(f"Ошибка при получении торговых судов: {e}")
    
    return ships_in_zone


def get_defender_fleets_in_zone(zone, defender_country: str = None) -> List[Dict]:
    """Получает все флоты в зоне (для защиты)"""
    try:
        from navy import load_navy_data, Fleet
    except ImportError:
        return []
    
    navy_data = load_navy_data()
    defender_fleets = []
    
    for fleet_data in navy_data.get("fleets", []):
        fleet = Fleet.from_dict(fleet_data)
        if fleet.current_zone == zone:
            if defender_country is None or fleet.country == defender_country:
                if fleet.get_total_ships() > 0:
                    defender_fleets.append({
                        "id": fleet.id,
                        "name": fleet.name,
                        "country": fleet.country,
                        "ships": fleet.ships.copy(),
                        "total_ships": fleet.get_total_ships(),
                        "intercept_power": fleet.get_intercept_power()
                    })
    
    return defender_fleets


def calculate_naval_intercept_chance(attacker_power: int, defender_power: int, weapon_id: str, quantity: int) -> float:
    """Рассчитывает шанс перехвата для ударов по флоту"""
    weapon = STRIKE_WEAPONS.get(weapon_id, {})
    base_difficulty = weapon.get("intercept_difficulty", 0.3) * 0.7
    
    if defender_power <= 0:
        return 0.0
    
    intercept_chance = defender_power / (defender_power + attacker_power)
    intercept_chance = intercept_chance * (1.0 - base_difficulty)
    
    if quantity > 1:
        saturation = 1.0 / math.log10(quantity + 9) * 2.0
        saturation = max(0.3, min(1.0, saturation))
        intercept_chance = intercept_chance * saturation
    
    return max(0.05, min(0.95, intercept_chance))


def execute_naval_strike(attacker_data: Dict, target_country: str, sea_zone_name: str,
                         weapon_id: str, quantity: int, target_type: str) -> Dict:
    """Выполняет удар по флоту или торговым конвоям в морской зоне"""
    from navy import SeaZone, load_navy_data, save_navy_data, Fleet
    
    target_zone = None
    for sz in SeaZone:
        if sz.value == sea_zone_name:
            target_zone = sz
            break
    
    if not target_zone:
        return {"success": False, "message": f"Морская зона {sea_zone_name} не найдена"}
    
    weapon = STRIKE_WEAPONS[weapon_id]
    
    if target_type == "navy_fleet":
        fleets = get_fleets_in_zone(target_country, target_zone)
        if not fleets:
            return {"success": False, "message": f"В зоне {sea_zone_name} нет флотов {target_country}"}
    elif target_type == "trade_convoy":
        ships = get_trade_ships_in_zone(target_country, target_zone, include_sailing=True)
        if not ships:
            return {"success": False, "message": f"В зоне {sea_zone_name} нет торговых судов {target_country}"}
    else:
        return {"success": False, "message": "Неизвестный тип цели"}
    
    defender_fleets = get_defender_fleets_in_zone(target_zone, target_country)
    defender_power = sum(f["intercept_power"] for f in defender_fleets)
    
    base_attack_power = quantity * weapon.get("intercept_difficulty", 0.5) * 50
    satellite_boost = get_intercept_difficulty_boost(attacker_data["state"]["statename"])
    base_attack_power = base_attack_power * (1 + satellite_boost)
    
    intercept_chance = calculate_naval_intercept_chance(base_attack_power, defender_power, weapon_id, quantity)
    
    intercepted = 0
    for _ in range(quantity):
        if random.random() < intercept_chance:
            intercepted += 1
    
    surviving = quantity - intercepted
    
    if surviving == 0:
        return {
            "success": True,
            "intercepted": True,
            "intercepted_count": quantity,
            "surviving": 0,
            "hits": 0,
            "destroyed_objects": 0,
            "defender_present": defender_power > 0,
            "intercept_chance": intercept_chance,
            "target_type": target_type,
            "sea_zone": sea_zone_name,
            "target_country": target_country,
            "weapon_name": weapon["name"],
            "quantity": quantity,
            "message": f"Все {quantity} {weapon['name']} перехвачены! {f'Флот противника' if defender_power > 0 else 'Системы ПВО'} сбили их."
        }
    
    if weapon_id == "hypersonic_missiles":
        accuracy = 1.0
    else:
        accuracy = weapon["base_accuracy"] * 0.7
    
    hits = 0
    for _ in range(surviving):
        if random.random() < accuracy:
            hits += 1
    
    if hits == 0:
        return {
            "success": True,
            "intercepted": intercepted > 0,
            "intercepted_count": intercepted,
            "surviving": surviving,
            "hits": 0,
            "destroyed_objects": 0,
            "defender_present": defender_power > 0,
            "intercept_chance": intercept_chance,
            "target_type": target_type,
            "sea_zone": sea_zone_name,
            "target_country": target_country,
            "weapon_name": weapon["name"],
            "quantity": quantity,
            "message": f"Перехвачено: {intercepted}. Достигло цели: {surviving}, но ни одно не попало."
        }
    
    destroyed_details = {}
    total_destroyed = 0
    economic_damage = 0
    
    if target_type == "navy_fleet":
        navy_data = load_navy_data()
        remaining_hits = hits
        naval_damage_multiplier = weapon.get("naval_damage_multiplier", 0.5)
        
        ship_types = ["aircraft_carriers", "cruisers", "destroyers", "frigates", "corvettes", "submarines", "boats"]
        ship_weights = {
            "aircraft_carriers": 10,
            "cruisers": 5,
            "destroyers": 3,
            "frigates": 2,
            "corvettes": 1,
            "submarines": 2,
            "boats": 0.5
        }
        
        for fleet_info in fleets:
            if remaining_hits <= 0:
                break
            
            for ship_type in ship_types:
                if ship_type not in fleet_info["ships"] or fleet_info["ships"][ship_type] <= 0:
                    continue
                
                weight = ship_weights.get(ship_type, 1)
                effective_damage = remaining_hits * naval_damage_multiplier
                destroy = min(fleet_info["ships"][ship_type], max(1, int(effective_damage / weight)))
                destroy = max(1, destroy) if destroy > 0 and fleet_info["ships"][ship_type] > 0 else destroy
                
                if destroy > 0:
                    destroy = min(destroy, fleet_info["ships"][ship_type], remaining_hits)
                    destroyed_details[ship_type] = destroyed_details.get(ship_type, 0) + destroy
                    total_destroyed += destroy
                    remaining_hits -= destroy
                    
                    for fleet_data in navy_data["fleets"]:
                        if fleet_data["id"] == fleet_info["id"]:
                            fleet_data["ships"][ship_type] -= destroy
                            if fleet_data["ships"][ship_type] < 0:
                                fleet_data["ships"][ship_type] = 0
                            break
                    
                    if remaining_hits <= 0:
                        break
        
        save_navy_data(navy_data)
        
        try:
            from conflicts import record_strike
            record_strike(attacker_data["state"]["statename"], target_country, total_destroyed)
        except ImportError:
            pass
        
        ship_names = {
            "aircraft_carriers": "Авианосцев", "cruisers": "Крейсеров", "destroyers": "Эсминцев",
            "frigates": "Фрегатов", "corvettes": "Корветов", "submarines": "Подводных лодок",
            "boats": "Катеров"
        }
        
        destroyed_text = ""
        for ship_type, count in destroyed_details.items():
            destroyed_text += f"  {ship_names.get(ship_type, ship_type)}: -{count}\n"
        
        message = (f"УДАР ПО ФЛОТУ {target_country}\n"
                  f"Зона: {sea_zone_name}\n"
                  f"Запущено: {quantity} {weapon['name']}\n"
                  f"Перехвачено: {intercepted} ({intercept_chance*100:.1f}%)\n"
                  f"Уничтожено кораблей: {total_destroyed}\n"
                  f"{destroyed_text}")
        
        if defender_power > 0:
            message += f"\nФлот противника пытался защищаться, но не смог перехватить все ракеты."
        
    else:
        ships_in_zone = get_trade_ships_in_zone(target_country, target_zone, include_sailing=True)
        if not ships_in_zone:
            return {"success": False, "message": "Торговые суда больше не обнаружены"}
        
        try:
            from maritime_trade import load_maritime_data, save_maritime_data, CargoShip
        except ImportError:
            return {"success": False, "message": "Модуль морской торговли недоступен"}
        
        maritime_data = load_maritime_data()
        destroyed_ships = []
        remaining_hits = hits
        
        for ship_info in ships_in_zone[:remaining_hits]:
            destroyed_ships.append(ship_info)
            economic_damage += ship_info.get("cargo_value", 0)
            remaining_hits -= 1
            maritime_data["ships"] = [s for s in maritime_data.get("ships", []) 
                                      if s["id"] != ship_info["id"]]
        
        total_destroyed = len(destroyed_ships)
        save_maritime_data(maritime_data)
        
        try:
            from conflicts import record_strike
            record_strike(attacker_data["state"]["statename"], target_country, total_destroyed)
        except ImportError:
            pass
        
        destroyed_text = ""
        for ship in destroyed_ships[:5]:
            status_text = " (в пути)" if ship.get("status") in ["sailing", "en_route"] else ""
            destroyed_text += f"  {ship['name']}{status_text} (груз: ${ship.get('cargo_value', 0):,.0f})\n"
        if len(destroyed_ships) > 5:
            destroyed_text += f"  ... и ещё {len(destroyed_ships)-5} судов"
        
        message = (f"УДАР ПО ТОРГОВЫМ КОНВОЯМ {target_country}\n"
                  f"Зона: {sea_zone_name}\n"
                  f"Запущено: {quantity} {weapon['name']}\n"
                  f"Перехвачено: {intercepted} ({intercept_chance*100:.1f}%)\n"
                  f"Уничтожено судов: {total_destroyed}\n"
                  f"Экономический ущерб: ${economic_damage:,.0f}\n"
                  f"{destroyed_text}")
        
        if defender_power > 0:
            message += f"\nВ зоне присутствовал флот {target_country}, который пытался защитить конвои."
    
    return {
        "success": True,
        "intercepted": intercepted > 0,
        "intercepted_count": intercepted,
        "surviving": surviving,
        "hits": hits,
        "destroyed_objects": total_destroyed,
        "destroyed_details": destroyed_details,
        "economic_damage": economic_damage,
        "defender_present": defender_power > 0,
        "intercept_chance": intercept_chance,
        "target_type": target_type,
        "sea_zone": sea_zone_name,
        "target_country": target_country,
        "weapon_name": weapon["name"],
        "quantity": quantity,
        "message": message
    }


def execute_air_defense_strike(attacker_data: Dict, target_country: str, target_region: str,
                               weapon_id: str, quantity: int, region_data: Dict, attacker_region: str,
                               is_decoy: bool = False) -> Dict:
    """Выполняет удар по средствам ПВО в регионе (ПВО из инфраструктуры)"""
    weapon = STRIKE_WEAPONS[weapon_id]
    
    distance = get_region_distance(
        attacker_data["state"]["statename"], attacker_region,
        target_country, target_region
    )
    
    if distance > weapon["range"]:
        return {
            "success": False,
            "message": f"Цель вне зоны досягаемости! Расстояние: {distance} км, дальность оружия: {weapon['range']} км"
        }
    
    actual_quantity = quantity
    if is_decoy:
        actual_quantity = quantity * 2
    
    surviving, base_chance, final_chance, destroyed_pvo = calculate_surviving_weapons_with_pvo(
        weapon_id, target_country, target_region, actual_quantity, attacker_data["state"]["statename"], is_decoy
    )
    final_chance = min(0.95, final_chance * 1.2)
    
    if surviving == 0:
        pvo_destroyed_text = format_pvo_destroyed_text(destroyed_pvo)
        return {
            "success": True,
            "intercepted": True,
            "intercepted_count": actual_quantity,
            "surviving": 0,
            "hits": 0,
            "destroyed_objects": 0,
            "destroyed_pvo": destroyed_pvo,
            "distance": distance,
            "message": f"Все {actual_quantity} {weapon['name']} перехвачены системами ПВО!\n"
                      f"Расстояние: {distance} км\n"
                      f"\nЗадействованные средства ПВО (уничтожены в бою):\n{pvo_destroyed_text if pvo_destroyed_text else '  Нет потерь ПВО'}"
        }
    
    if weapon_id == "hypersonic_missiles":
        accuracy = 1.0
    elif is_decoy:
        accuracy = 0.0
    else:
        accuracy = weapon["base_accuracy"] * 0.6
    
    hits = 0
    for _ in range(surviving):
        if random.random() < accuracy:
            hits += 1
    
    if hits == 0 and not is_decoy:
        pvo_destroyed_text = format_pvo_destroyed_text(destroyed_pvo)
        return {
            "success": True,
            "intercepted": (actual_quantity - surviving) > 0,
            "intercepted_count": actual_quantity - surviving,
            "surviving": surviving,
            "hits": 0,
            "destroyed_objects": 0,
            "destroyed_pvo": destroyed_pvo,
            "distance": distance,
            "message": f"Перехвачено: {actual_quantity - surviving}. Достигло цели: {surviving}, но ни один не попал.\n"
                      f"Расстояние: {distance} км\n"
                      f"\nЗадействованные средства ПВО (уничтожены в бою):\n{pvo_destroyed_text if pvo_destroyed_text else '  Нет потерь ПВО'}"
        }
    
    destroyed = {}
    total_destroyed = 0
    host_country = target_country  # Страна-владелец региона
    
    pvo_fields = [
        ("long_range_air_defense", "ЗРК большой дальности", 5),
        ("short_range_air_defense", "ЗРК малой дальности", 3),
        ("zdprk", "ЗПРК", 2),
        ("zas", "Зенитная артиллерия", 1)
    ]
    
    remaining_hits = hits
    
    # Получаем ownership для ПВО
    for field, name, value in pvo_fields:
        if remaining_hits <= 0:
            break
        
        current_total = get_asset_total(region_data, field)
        if current_total <= 0:
            continue
        
        destroy = min(current_total, remaining_hits)
        
        # Выбираем случайного владельца для уничтожения
        ownership = get_asset_ownership(region_data, field)
        if ownership:
            # Выбираем владельца с учётом его доли
            owners = list(ownership.keys())
            weights = [ownership[o] for o in owners]
            selected_owner = random.choices(owners, weights=weights, k=1)[0]
            
            # Уничтожаем активы выбранного владельца
            remove_asset_from_region(region_data, field, selected_owner, destroy)
        else:
            # Если ownership пуст (старые данные), просто уменьшаем total
            region_data[field] = {"total": current_total - destroy, "ownership": {}}
        
        destroyed[field] = destroy
        total_destroyed += destroy
        remaining_hits -= destroy
    
    infra = load_infrastructure()
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == target_country:
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                if target_region in econ_data.get("regions", {}):
                    econ_data["regions"][target_region] = region_data
                    break
            break
    save_infrastructure(infra)
    
    try:
        from conflicts import record_strike
        record_strike(attacker_data["state"]["statename"], target_country, total_destroyed)
    except ImportError:
        pass
    
    destroyed_text = ""
    for field, count in destroyed.items():
        name = {"long_range_air_defense": "ЗРК большой дальности",
                "short_range_air_defense": "ЗРК малой дальности",
                "zdprk": "ЗПРК",
                "zas": "Зенитная артиллерия"}.get(field, field)
        destroyed_text += f"  {name}: -{count}\n"
    
    pvo_destroyed_text = format_pvo_destroyed_text(destroyed_pvo)
    
    message = (f"УДАР ПО СРЕДСТВАМ ПВО\n"
              f"Атакующий регион: {attacker_region}\n"
              f"Целевой регион: {target_region}\n"
              f"Расстояние: {distance} км\n"
              f"Запущено: {actual_quantity} {weapon['name']}" + (" (пустышки)" if is_decoy else "") + f"\n"
              f"Перехвачено: {actual_quantity - surviving} ({final_chance*100:.1f}%)\n"
              f"Достигло цели: {surviving}\n"
              f"Попаданий: {hits}\n"
              f"Уничтожено объектов ПВО: {total_destroyed}\n"
              f"{destroyed_text}"
              f"\nЗадействованные средства ПВО (уничтожены в бою):\n{pvo_destroyed_text if pvo_destroyed_text else '  Нет потерь ПВО'}")
    
    return {
        "success": True,
        "intercepted": (actual_quantity - surviving) > 0,
        "intercepted_count": actual_quantity - surviving,
        "surviving": surviving,
        "hits": hits,
        "destroyed_objects": total_destroyed,
        "destroyed_details": destroyed,
        "destroyed_pvo": destroyed_pvo,
        "distance": distance,
        "is_decoy": is_decoy,
        "message": message
    }


# ==================== ФУНКЦИИ ДЛЯ НАВОДНЫХ ДРОНОВ ====================

def get_ships_in_port_region(region_name: str, country_name: str) -> List[Dict]:
    """Получает корабли, стоящие в порту региона"""
    try:
        from maritime_trade import load_maritime_data, CargoShip, PORTS, REGION_TO_PORT
    except ImportError:
        return []
    
    data = load_maritime_data()
    ships_in_port = []
    
    port = region_name
    if region_name in REGION_TO_PORT:
        port = REGION_TO_PORT[region_name]
    
    for ship_data in data.get("ships", []):
        ship = CargoShip.from_dict(ship_data)
        if ship.current_region == region_name or ship.current_region == port:
            if ship.current_country == country_name and ship.status != "sailing":
                ships_in_port.append({
                    "id": ship.id,
                    "name": ship.name,
                    "type": ship.type,
                    "cargo_value": ship.cargo_value,
                    "status": ship.status
                })
    
    return ships_in_port


def execute_usv_strike(attacker_data: Dict, target_country: str, target_region: str,
                       weapon_id: str, quantity: int, region_data: Dict, attacker_region: str,
                       target_type: str) -> Dict:
    """
    Выполняет удар наводными дронами.
    Цели: верфи, флот в порту, торговые суда в порту.
    """
    weapon = STRIKE_WEAPONS[weapon_id]
    
    distance = get_region_distance(
        attacker_data["state"]["statename"], attacker_region,
        target_country, target_region
    )
    
    if distance > weapon["range"]:
        return {
            "success": False,
            "message": f"Цель вне зоны досягаемости! Расстояние: {distance} км, дальность оружия: {weapon['range']} км"
        }
    
    if not is_region_coastal(target_region, target_country):
        return {
            "success": False,
            "message": f"Регион {target_region} не имеет выхода к морю! Наводные дроны могут атаковать только прибрежные регионы."
        }
    
    surviving, base_chance, final_chance, destroyed_pvo = calculate_surviving_weapons_with_pvo(
        weapon_id, target_country, target_region, quantity, attacker_data["state"]["statename"], False
    )
    
    if surviving == 0:
        return {
            "success": True,
            "intercepted": True,
            "intercepted_count": quantity,
            "surviving": 0,
            "hits": 0,
            "destroyed_objects": 0,
            "message": f"Все {quantity} {weapon['name']} перехвачены системами ПВО!"
        }
    
    accuracy = weapon["base_accuracy"] * 0.6
    hits = 0
    for _ in range(surviving):
        if random.random() < accuracy:
            hits += 1
    
    if hits == 0:
        return {
            "success": True,
            "intercepted": (quantity - surviving) > 0,
            "intercepted_count": quantity - surviving,
            "surviving": surviving,
            "hits": 0,
            "destroyed_objects": 0,
            "message": f"Перехвачено: {quantity - surviving}. Достигло цели: {surviving}, но ни одно не попало."
        }
    
    result_message = ""
    total_destroyed = 0
    destroyed_details = {}
    
    if target_type == "shipyards":
        shipyards_total = get_asset_total(region_data, "shipyards")
        if shipyards_total > 0:
            destroyed = min(shipyards_total, hits)
            ownership = get_asset_ownership(region_data, "shipyards")
            if ownership:
                owners = list(ownership.keys())
                weights = [ownership[o] for o in owners]
                selected_owner = random.choices(owners, weights=weights, k=1)[0]
                remove_asset_from_region(region_data, "shipyards", selected_owner, destroyed)
            else:
                region_data["shipyards"] = {"total": shipyards_total - destroyed, "ownership": {}}
            total_destroyed += destroyed
            destroyed_details["shipyards"] = destroyed
            result_message += f"Уничтожено верфей: {destroyed}\n"
            hits -= destroyed
    
    if target_type == "navy_fleet":
        try:
            from navy import load_navy_data, save_navy_data, Fleet
        except ImportError:
            pass
        else:
            navy_data = load_navy_data()
            ships_destroyed = 0
            
            for fleet_data in navy_data["fleets"]:
                if fleet_data["country"] == target_country and fleet_data["current_zone"]:
                    zone = fleet_data["current_zone"]
                    from navy import SeaZone
                    for sz in SeaZone:
                        if sz.value == zone:
                            sea_zone = sz
                            break
                    else:
                        continue
                    
                    if sea_zone and is_region_coastal(target_region, target_country):
                        from maritime_trade import get_sea_zone_from_region
                        target_zone = get_sea_zone_from_region(target_region)
                        if target_zone and zone == target_zone:
                            fleet = Fleet.from_dict(fleet_data)
                            ship_types = ["aircraft_carriers", "cruisers", "destroyers", "frigates", "corvettes", "boats"]
                            for ship_type in ship_types:
                                if hits <= 0:
                                    break
                                count = fleet.ships.get(ship_type, 0)
                                if count > 0 and ship_type != "submarines":
                                    destroy = min(count, max(1, hits))
                                    destroy = min(destroy, 2)
                                    fleet.ships[ship_type] = count - destroy
                                    ships_destroyed += destroy
                                    destroyed_details[ship_type] = destroyed_details.get(ship_type, 0) + destroy
                                    hits -= destroy
                            
                            for i, fd in enumerate(navy_data["fleets"]):
                                if fd["id"] == fleet.id:
                                    navy_data["fleets"][i] = fleet.to_dict()
                                    break
            
            save_navy_data(navy_data)
            total_destroyed += ships_destroyed
            if ships_destroyed > 0:
                result_message += f"Уничтожено кораблей в порту: {ships_destroyed}\n"
    
    if target_type == "trade_convoy":
        ships_in_port = get_ships_in_port_region(target_region, target_country)
        if ships_in_port:
            try:
                from maritime_trade import load_maritime_data, save_maritime_data
            except ImportError:
                pass
            else:
                maritime_data = load_maritime_data()
                ships_destroyed = 0
                for ship_info in ships_in_port[:min(hits, len(ships_in_port))]:
                    maritime_data["ships"] = [s for s in maritime_data.get("ships", []) if s["id"] != ship_info["id"]]
                    ships_destroyed += 1
                    hits -= 1
                
                save_maritime_data(maritime_data)
                total_destroyed += ships_destroyed
                if ships_destroyed > 0:
                    result_message += f"Уничтожено торговых судов в порту: {ships_destroyed}\n"
    
    infra = load_infrastructure()
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == target_country:
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                if target_region in econ_data.get("regions", {}):
                    econ_data["regions"][target_region] = region_data
                    break
            break
    save_infrastructure(infra)
    
    try:
        from conflicts import record_strike
        record_strike(attacker_data["state"]["statename"], target_country, total_destroyed)
    except ImportError:
        pass
    
    message = (f"УДАР НАВОДНЫМИ ДРОНАМИ\n"
              f"Атакующий регион: {attacker_region}\n"
              f"Целевой регион: {target_region}\n"
              f"Расстояние: {distance} км\n"
              f"Запущено: {quantity} {weapon['name']}\n"
              f"Перехвачено: {quantity - surviving} ({final_chance*100:.1f}%)\n"
              f"Достигло цели: {surviving}\n"
              f"Попаданий: {hits}\n"
              f"{result_message}"
              f"Всего уничтожено объектов: {total_destroyed}")
    
    return {
        "success": True,
        "intercepted": (quantity - surviving) > 0,
        "intercepted_count": quantity - surviving,
        "surviving": surviving,
        "hits": hits,
        "destroyed_objects": total_destroyed,
        "destroyed_details": destroyed_details,
        "distance": distance,
        "message": message
    }


def format_pvo_destroyed_text(destroyed_pvo: Dict[str, int]) -> str:
    """Форматирует текст о уничтоженных средствах ПВО"""
    if not destroyed_pvo:
        return "  Нет потерь ПВО"
    
    pvo_names = {
        "long_range_air_defense": "ЗРК большой дальности",
        "short_range_air_defense": "ЗРК малой дальности",
        "zdprk": "ЗПРК",
        "zas": "Зенитная артиллерия",
        "radar_systems": "РЛС"
    }
    
    text = ""
    for pvo_type, count in destroyed_pvo.items():
        if count > 0:
            text += f"  {pvo_names.get(pvo_type, pvo_type)}: -{count}\n"
    return text


def execute_multi_target_strike(attacker_data: Dict, target_country: str, target_region: str,
                                 weapon_id: str, total_quantity: int, target_allocations: List[Tuple[str, int]],
                                 attacker_region: str, is_decoy: bool = False) -> Dict:
    """Выполняет удар по нескольким типам целей (инфраструктура)"""
    states = load_states()
    infra = load_infrastructure()
    
    attacker_country = attacker_data["state"]["statename"]
    weapon = STRIKE_WEAPONS[weapon_id]
    
    if weapon.get("naval_targets_only", False):
        return {"success": False, "message": "Наводные дроны не предназначены для ударов по сухопутной инфраструктуре!"}
    
    reachable, distance = is_region_reachable(
        attacker_country, attacker_region,
        target_country, target_region,
        weapon["range"]
    )
    
    if not reachable:
        return {
            "success": False,
            "message": f"Цель вне зоны досягаемости! Расстояние: {distance} км, дальность оружия: {weapon['range']} км"
        }
    
    target_data = None
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == target_country:
            target_data = data
            break
    
    if not target_data:
        return {"success": False, "message": "Цель не найдена"}
    
    region_found = False
    region_data = None
    
    for cid, cdata in infra["infrastructure"].items():
        if cdata.get("country") == target_country:
            for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                if target_region in econ_data.get("regions", {}):
                    region_data = econ_data["regions"][target_region]
                    region_found = True
                    break
            break
    
    if not region_found or not region_data:
        return {"success": False, "message": "Регион не найден"}
    
    distribution = distribute_weapons_among_targets(weapon_id, total_quantity, target_allocations)
    
    if not distribution:
        return {"success": False, "message": "Не удалось распределить оружие между целями"}
    
    actual_quantity = total_quantity
    if is_decoy:
        actual_quantity = total_quantity * 2
    
    surviving_distribution = {}
    total_surviving = 0
    total_intercepted = 0
    base_chance = 0
    final_chance = 0
    all_destroyed_pvo = {}
    
    for target_id, allocated in distribution.items():
        actual_allocated = allocated * 2 if is_decoy else allocated
        
        surviving, bc, fc, destroyed_pvo = calculate_surviving_weapons_with_pvo(
            weapon_id, target_country, target_region, actual_allocated, attacker_country, is_decoy
        )
        surviving_distribution[target_id] = surviving
        total_surviving += surviving
        total_intercepted += (actual_allocated - surviving)
        base_chance = bc
        final_chance = fc
        
        for pvo_type, count in destroyed_pvo.items():
            all_destroyed_pvo[pvo_type] = all_destroyed_pvo.get(pvo_type, 0) + count
    
    if total_surviving == 0:
        pvo_destroyed_text = format_pvo_destroyed_text(all_destroyed_pvo)
        return {
            "success": True,
            "intercepted": True,
            "intercepted_count": actual_quantity,
            "surviving": 0,
            "hits": 0,
            "damage_report": {},
            "civilian_casualties": 0,
            "destroyed_objects": 0,
            "destroyed_pvo": all_destroyed_pvo,
            "fuel_losses": {},
            "happiness_impact": 0,
            "stability_impact": 0,
            "base_chance": base_chance * 100,
            "final_chance": final_chance * 100,
            "distance": distance,
            "is_decoy": is_decoy,
            "message": f"Все {actual_quantity} средств поражения перехвачены ПВО!\n"
                      f"\nЗадействованные средства ПВО (уничтожены в бою):\n{pvo_destroyed_text if pvo_destroyed_text else '  Нет потерь ПВО'}"
        }
    
    if weapon_id == "hypersonic_missiles":
        accuracy = 1.0
    elif is_decoy:
        accuracy = 0.0
    else:
        accuracy = weapon["base_accuracy"]
    
    hits_distribution = {}
    total_hits = 0
    
    for target_id, surviving in surviving_distribution.items():
        if is_decoy:
            hits = 0
        else:
            hits = 0
            for _ in range(surviving):
                if random.random() < accuracy:
                    hits += 1
        hits_distribution[target_id] = hits
        total_hits += hits
    
    if total_hits == 0 and not is_decoy:
        pvo_destroyed_text = format_pvo_destroyed_text(all_destroyed_pvo)
        return {
            "success": True,
            "intercepted": total_intercepted > 0,
            "intercepted_count": total_intercepted,
            "surviving": total_surviving,
            "hits": 0,
            "damage_report": {},
            "civilian_casualties": 0,
            "destroyed_objects": 0,
            "destroyed_pvo": all_destroyed_pvo,
            "fuel_losses": {},
            "happiness_impact": 0,
            "stability_impact": 0,
            "base_chance": base_chance * 100,
            "final_chance": final_chance * 100,
            "distance": distance,
            "is_decoy": is_decoy,
            "message": f"Перехвачено: {total_intercepted}. Достигло цели: {total_surviving}, но ни один не попал.\n"
                      f"\nЗадействованные средства ПВО (уничтожены в бою):\n{pvo_destroyed_text if pvo_destroyed_text else '  Нет потерь ПВО'}"
        }
    
    total_destroyed = 0
    all_damage_reports = {}
    all_fuel_losses = {}
    total_happiness_impact = 0
    total_stability_impact = 0
    total_casualties = 0
    original_population = region_data.get("population", 0)
    
    for target_id, hits in hits_distribution.items():
        if hits == 0:
            continue
        
        target_info = TARGET_TYPES[target_id]
        available_targets = count_targets_in_region(region_data, target_id)
        hits = min(hits, available_targets)
        
        if hits == 0:
            continue
        
        damage_report, destroyed, fuel_losses = distribute_hits_among_targets(
            region_data, target_id, hits, weapon_id, target_country
        )
        
        total_destroyed += destroyed
        all_damage_reports.update(damage_report)
        
        for fuel, loss in fuel_losses.items():
            all_fuel_losses[fuel] = all_fuel_losses.get(fuel, 0) + loss
        
        if not is_decoy:
            if random.random() < target_info["civilian_casualty_chance"]:
                base_per_hit = target_info.get("civilian_casualty_base", 50)
                random_factor = random.uniform(0.7, 1.3)
                casualties = int(base_per_hit * hits * random_factor)
                casualties = min(casualties, int(original_population * 0.05))
                total_casualties += casualties
        
        total_happiness_impact += target_info["happiness_impact"] * hits
        total_stability_impact += target_info["stability_impact"] * hits
    
    if total_casualties > 0 and "population" in region_data:
        current_pop = region_data["population"]
        if current_pop > 0:
            actual_casualties = min(current_pop, total_casualties)
            region_data["population"] = current_pop - actual_casualties
            total_casualties = actual_casualties
    
    save_infrastructure(infra)
    
    if total_casualties > 0 and not is_decoy:
        total_happiness_impact += min(10, total_casualties // 1000)
    
    if is_decoy and total_surviving > 0:
        total_happiness_impact = max(1, min(5, total_surviving // 10))
        total_stability_impact = max(1, min(5, total_surviving // 10))
    
    total_happiness_impact = min(total_happiness_impact, MAX_HAPPINESS_DROP)
    total_stability_impact = min(total_stability_impact, MAX_STABILITY_DROP)
    
    target_data["state"]["happiness"] = max(0, target_data["state"].get("happiness", 50) - total_happiness_impact)
    target_data["state"]["stability"] = max(0, target_data["state"].get("stability", 50) - total_stability_impact)
    target_data["state"]["trust"] = max(0, target_data["state"].get("trust", 50) - total_stability_impact // 2)
    
    save_states(states)
    
    try:
        from conflicts import record_strike
        attacker_name = attacker_data["state"]["statename"]
        record_strike(attacker_name, target_country, total_destroyed)
    except ImportError:
        pass
    except Exception as e:
        print(f"Ошибка при записи в конфликт: {e}")
    
    pvo_destroyed_text = format_pvo_destroyed_text(all_destroyed_pvo)
    
    damage_text = ""
    for field, data in all_damage_reports.items():
        if data["destroyed"] > 0:
            damage_text += f"  {data['name']}: -{data['destroyed']} (осталось: {data['remaining']})\n"
    
    report = {
        "success": True,
        "intercepted": total_intercepted > 0,
        "intercepted_count": total_intercepted,
        "surviving": total_surviving,
        "hits": total_hits,
        "destroyed_objects": total_destroyed,
        "damage_report": all_damage_reports,
        "destroyed_pvo": all_destroyed_pvo,
        "civilian_casualties": total_casualties,
        "fuel_losses": all_fuel_losses,
        "happiness_impact": total_happiness_impact,
        "stability_impact": total_stability_impact,
        "base_chance": base_chance * 100 if 'base_chance' in locals() else 0,
        "final_chance": final_chance * 100 if 'final_chance' in locals() else 0,
        "distance": distance,
        "attacker": attacker_country,
        "attacker_region": attacker_region,
        "target": target_country,
        "target_region": target_region,
        "weapon_name": weapon['name'],
        "quantity": total_quantity,
        "actual_quantity": actual_quantity,
        "targets_hit": hits_distribution,
        "is_decoy": is_decoy,
        "message": (f"РЕЗУЛЬТАТ УДАРА\n"
                   f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                   f"Расстояние: {distance} км\n"
                   f"Запущено: {total_quantity} {weapon['name']}" + (" (режим пустышек)" if is_decoy else "") + f"\n"
                   f"Всего средств в воздухе: {actual_quantity}\n"
                   f"Перехвачено: {total_intercepted} ({final_chance*100 if 'final_chance' in locals() else 0:.1f}%)\n"
                   f"Достигло цели: {total_surviving}\n"
                   f"Попаданий: {total_hits}\n"
                   f"Уничтожено объектов: {total_destroyed}\n"
                   f"{damage_text if damage_text else ''}"
                   f"\nЗадействованные средства ПВО (уничтожены в бою):\n{pvo_destroyed_text if pvo_destroyed_text else '  Нет потерь ПВО'}\n"
                   f"\nПотери населения: {format_number(total_casualties)} чел.\n"
                   f"\nВлияние на страну:\n  Счастье: -{total_happiness_impact}%\n  Стабильность: -{total_stability_impact}%")
    }
    
    if all_fuel_losses:
        fuel_text = "\nПотери топлива:\n"
        for fuel, loss in all_fuel_losses.items():
            fuel_names = {"oil": "Нефть", "gas": "Газ", "coal": "Уголь", "uranium": "Уран"}
            fuel_text += f"  {fuel_names.get(fuel, fuel)}: {loss:.2f}\n"
        report["message"] += fuel_text
    
    return report


def distribute_weapons_among_targets(weapon_id: str, total_quantity: int, 
                                      target_allocations: List[Tuple[str, int]]) -> Dict[str, int]:
    """Распределяет оружие между выбранными целями"""
    distribution = {}
    
    sorted_targets = sorted(target_allocations, key=lambda x: TARGET_TYPES[x[0]]["priority"])
    
    remaining = total_quantity
    for target_id, allocated in sorted_targets:
        if allocated > 0:
            to_assign = min(allocated, remaining)
            if to_assign > 0:
                distribution[target_id] = to_assign
                remaining -= to_assign
        
        if remaining <= 0:
            break
    
    if remaining > 0 and distribution:
        targets = list(distribution.keys())
        for i in range(remaining):
            target = targets[i % len(targets)]
            distribution[target] = distribution.get(target, 0) + 1
    
    return distribution


def get_all_targets_in_region(region_data: Dict, target_country: str = None) -> List[Tuple[str, Dict]]:
    """Возвращает список всех доступных целей в регионе с их описанием"""
    targets = []
    
    for target_id, target_info in TARGET_TYPES.items():
        if target_info.get("is_naval") or target_info.get("is_trade"):
            continue
            
        if not target_info.get("infra_fields"):
            continue
            
        count = 0
        for field in target_info["infra_fields"]:
            count += get_asset_total(region_data, field)
        if count > 0:
            targets.append((target_id, target_info))
    
    targets.sort(key=lambda x: x[1].get("priority", 10))
    return targets


def count_targets_in_region(region_data: Dict, target_type: str) -> int:
    """Подсчитывает количество доступных целей в регионе"""
    target_info = TARGET_TYPES[target_type]
    total = 0
    
    for field in target_info.get("infra_fields", []):
        total += get_asset_total(region_data, field)
    
    return total


def distribute_hits_among_targets(region_data: Dict, target_type: str, hits: int, weapon_id: str, host_country: str = None) -> Tuple[Dict, int, Dict]:
    """Распределяет попадания по целям с учётом владения"""
    target_info = TARGET_TYPES[target_type]
    damage_report = {}
    total_destroyed = 0
    fuel_losses = {}
    
    NON_TARGET_FIELDS = ["development_level", "specialization", "terrain", "coastal", "bordering_countries", "population"]
    
    available_targets = []
    for field in target_info.get("infra_fields", []):
        if field in region_data and field not in NON_TARGET_FIELDS:
            current_total = get_asset_total(region_data, field)
            if current_total > 0:
                # Получаем ownership для этого поля
                ownership = get_asset_ownership(region_data, field)
                for owner, count in ownership.items():
                    for _ in range(count):
                        available_targets.append((field, owner))
    
    if not available_targets:
        return damage_report, total_destroyed, fuel_losses
    
    random.shuffle(available_targets)
    hits = min(hits, len(available_targets))
    
    hits_distribution = {}
    for i in range(hits):
        field, owner = available_targets[i]
        key = f"{field}:{owner}"
        hits_distribution[key] = hits_distribution.get(key, 0) + 1
    
    for key, destroy_count in hits_distribution.items():
        field, owner = key.split(":", 1)
        current_ownership = get_asset_ownership(region_data, field)
        current = current_ownership.get(owner, 0)
        destroyed = min(current, destroy_count)
        
        if destroyed > 0:
            remove_asset_from_region(region_data, field, owner, destroyed)
            total_destroyed += destroyed
            
            field_names = {
                "military_factories": "Военные заводы",
                "civilian_factories": "Гражданские фабрики",
                "shipyards": "Верфи",
                "refineries": "НПЗ",
                "oil_depots": "Нефтебазы",
                "thermal_power": "ТЭС",
                "hydro_power": "ГЭС",
                "solar_power": "СЭС",
                "wind_power": "ВЭС",
                "internet_infrastructure": "ЦОД",
                "office_centers": "Офисные центры",
                "radar_systems": "РЛС",
                "short_range_air_defense": "ПВО малой дальности",
                "long_range_air_defense": "ПВО большой дальности",
                "zdprk": "ЗПРК",
                "zas": "ЗСУ"
            }
            
            field_name = field_names.get(field, field.replace('_', ' ').title())
            
            if field in damage_report:
                damage_report[field]["destroyed"] += destroyed
                damage_report[field]["remaining"] = get_asset_total(region_data, field)
            else:
                damage_report[field] = {
                    "name": field_name,
                    "destroyed": destroyed,
                    "remaining": get_asset_total(region_data, field)
                }
            
            if field in ["refineries", "oil_depots"] and "fuel_loss" in target_info:
                for fuel in target_info["fuel_loss"]:
                    if fuel in FUEL_LOSS_PER_HIT:
                        min_loss, max_loss = FUEL_LOSS_PER_HIT[fuel]
                        loss = random.uniform(min_loss, max_loss) * destroyed
                        fuel_losses[fuel] = fuel_losses.get(fuel, 0) + loss
            
            if field in ["thermal_power"] and "fuel_loss" in target_info:
                for fuel in target_info["fuel_loss"]:
                    if fuel in FUEL_LOSS_PER_HIT:
                        min_loss, max_loss = FUEL_LOSS_PER_HIT[fuel]
                        loss = random.uniform(min_loss, max_loss) * destroyed
                        fuel_losses[fuel] = fuel_losses.get(fuel, 0) + loss
    
    return damage_report, total_destroyed, fuel_losses


def execute_strike(attacker_data: Dict, target_country: str, target_region: str,
                   weapon_id: str, quantity: int, target_type: str,
                   attacker_region: str, is_decoy: bool = False) -> Dict:
    """Выполняет одиночный удар (обёртка для совместимости)"""
    target_allocations = [(target_type, quantity)]
    result = execute_multi_target_strike(
        attacker_data, target_country, target_region,
        weapon_id, quantity, target_allocations,
        attacker_region, is_decoy
    )
    return result


def get_available_weapons(player_data: Dict, strike_type: str = None) -> List[Tuple[str, int]]:
    """
    Возвращает список доступного у игрока оружия для ударов.
    Если указан strike_type, фильтрует оружие по типу удара.
    """
    available = []
    army = player_data.get("army", {})
    
    for weapon_id, weapon_info in STRIKE_WEAPONS.items():
        # Наводные дроны НЕ должны быть доступны для ударов по инфраструктуре
        if strike_type == "infrastructure" and weapon_id == "usv_attack":
            continue
        
        path = weapon_info["army_path"].split('.')
        
        current = army
        valid = True
        
        for key in path:
            if key in current:
                current = current[key]
            else:
                valid = False
                break
        
        if valid and isinstance(current, (int, float)) and current > 0:
            available.append((weapon_id, int(current)))
    
    return available


def consume_weapon(player_data: Dict, weapon_id: str, quantity: int, is_decoy: bool = False) -> bool:
    """Списывает использованное оружие"""
    weapon_info = STRIKE_WEAPONS[weapon_id]
    path = weapon_info["army_path"].split('.')
    
    actual_quantity = quantity
    
    current = player_data["army"]
    for key in path[:-1]:
        if key not in current:
            return False
        current = current[key]
    
    last_key = path[-1]
    if last_key not in current or current[last_key] < actual_quantity:
        return False
    
    current[last_key] -= actual_quantity
    return True


def calculate_civilian_casualties(target_info: Dict, hits: int, region_population: int) -> int:
    """Рассчитывает потери среди гражданского населения"""
    if region_population <= 0:
        return 0
    
    base_per_hit = target_info.get("civilian_casualty_base", 50)
    random_factor = random.uniform(0.7, 1.3)
    casualties = int(base_per_hit * hits * random_factor)
    casualties = min(casualties, int(region_population * 0.05))
    
    return casualties


async def send_strike_log(bot_instance, report: Dict):
    """Отправляет результат удара в лог-канал"""
    try:
        channel = bot_instance.get_channel(STRIKE_LOG_CHANNEL_ID)
        if not channel:
            return
        
        embed = discord.Embed(
            title="РЕЗУЛЬТАТ УДАРА" + (" (РЕЖИМ ПУСТЫШЕК)" if report.get("is_decoy", False) else ""),
            description=f"{report['attacker']} атаковал {report['target']}",
            color=discord.Color.red() if report.get("hits", 0) > 0 else discord.Color.orange()
        )
        
        embed.add_field(name="Атакующий регион", value=report['attacker_region'], inline=True)
        embed.add_field(name="Целевой регион", value=report['target_region'], inline=True)
        embed.add_field(name="Оружие", value=f"{report['weapon_name']} x{report['quantity']}", inline=True)
        if report.get("actual_quantity"):
            embed.add_field(name="Всего средств в воздухе", value=str(report['actual_quantity']), inline=True)
        embed.add_field(name="Расстояние", value=f"{report['distance']} км", inline=True)
        embed.add_field(name="Перехвачено", value=f"{report['intercepted_count']} ({report['final_chance']:.1f}%)", inline=True)
        
        if report.get("hits", 0) > 0:
            embed.add_field(name="Попаданий", value=str(report['hits']), inline=True)
            embed.add_field(name="Уничтожено", value=str(report['destroyed_objects']), inline=True)
            embed.add_field(name="Потери населения", value=format_number(report['civilian_casualties']), inline=True)
        
        if report.get("destroyed_pvo"):
            pvo_names = {
                "long_range_air_defense": "ЗРК большой дальности",
                "short_range_air_defense": "ЗРК малой дальности",
                "zdprk": "ЗПРК",
                "zas": "Зенитная артиллерия",
                "radar_systems": "РЛС"
            }
            pvo_text = ""
            for pvo_type, count in report["destroyed_pvo"].items():
                if count > 0:
                    pvo_text += f"{pvo_names.get(pvo_type, pvo_type)}: {count}\n"
            if pvo_text:
                embed.add_field(name="Уничтожено ПВО", value=pvo_text, inline=True)
        
        if report.get("targets_hit"):
            targets_text = ""
            for target_id, hits in report["targets_hit"].items():
                if hits > 0:
                    target_name = TARGET_TYPES.get(target_id, {}).get("name", target_id)
                    targets_text += f"{target_name}: {hits} попаданий\n"
            if targets_text:
                embed.add_field(name="Поражённые цели", value=targets_text, inline=False)
        
        if report.get("damage_report"):
            damage_text = ""
            for field, data in list(report["damage_report"].items())[:5]:
                damage_text += f"{data['name']}: -{data['destroyed']} (осталось: {data['remaining']})\n"
            if damage_text:
                embed.add_field(name="Уничтожено объектов", value=damage_text, inline=False)
        
        embed.add_field(name="Влияние на страну", value=f"Счастье: -{report.get('happiness_impact', 0)}%\nСтабильность: -{report.get('stability_impact', 0)}%", inline=False)
        
        embed.set_footer(text=f"Время удара: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Ошибка при отправке лога удара: {e}")


# ==================== ГЛАВНОЕ МЕНЮ ====================

async def show_strike_menu(interaction_or_ctx, user_id: int):
    """Показать меню управления ударами"""
    states = load_states()
    player_data = None
    player_country = None
    
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            player_country = data["state"]["statename"]
            break
    
    if not player_data:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message("У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("У вас нет государства!")
        return
    
    available_weapons = get_available_weapons(player_data)
    at_war = get_countries_at_war(player_country)
    
    embed = discord.Embed(
        title="Управление ударами",
        description="Выберите тип удара:",
        color=DARK_THEME_COLOR
    )
    
    if available_weapons:
        weapons_text = ""
        for weapon_id, quantity in available_weapons:
            weapon_info = STRIKE_WEAPONS[weapon_id]
            weapons_text += f"{weapon_info['name']}: {quantity} шт. (дальн: {weapon_info['range']} км)\n"
        embed.add_field(name="Доступное вооружение", value=weapons_text, inline=False)
    else:
        embed.add_field(name="Доступное вооружение", value="Нет доступного оружия", inline=False)
    
    embed.add_field(name="Страны в состоянии войны", value="\n".join(at_war) or "Нет", inline=False)
    
    view = StrikeTypeSelectView(user_id, player_country, player_data)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view, ephemeral=True)


# ==================== UI КЛАССЫ ====================
# (Все UI классы остаются без изменений, так как они не работают напрямую с полями инфраструктуры)

class StrikeTypeSelectView(View):
    """Главное меню выбора типа удара"""
    
    def __init__(self, user_id: int, player_country: str, player_data: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        
        infra_btn = Button(label="Инфраструктура (включая ПВО)", style=discord.ButtonStyle.primary)
        infra_btn.callback = self.infrastructure_strike
        self.add_item(infra_btn)
        
        navy_btn = Button(label="Военно-морской флот", style=discord.ButtonStyle.danger)
        navy_btn.callback = self.navy_strike
        self.add_item(navy_btn)
        
        trade_btn = Button(label="Торговые конвои", style=discord.ButtonStyle.success)
        trade_btn.callback = self.trade_strike
        self.add_item(trade_btn)
        
        usv_btn = Button(label="Наводные дроны", style=discord.ButtonStyle.primary)
        usv_btn.callback = self.usv_strike
        self.add_item(usv_btn)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def infrastructure_strike(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.show_country_selection(interaction, "infrastructure")
    
    async def navy_strike(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.show_navy_country_selection(interaction)
    
    async def trade_strike(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.show_trade_country_selection(interaction)
    
    async def usv_strike(self, interaction: discord.Interaction):
        """Удар наводными дронами"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        at_war = get_countries_at_war(self.player_country)
        if not at_war:
            await interaction.response.send_message("Нет стран, с которыми вы в состоянии войны!", ephemeral=True)
            return
        
        available_weapons = get_available_weapons(self.player_data)
        usv_available = any(w == "usv_attack" for w, _ in available_weapons)
        
        if not usv_available:
            await interaction.response.send_message("У вас нет наводных дронов! Закажите их через ВПК (раздел флота).", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор страны",
            description="Тип удара: Наводные дроны\nЗапуск только из прибрежных регионов",
            color=DARK_THEME_COLOR
        )
        
        select = CountrySelectForPortStrike(self.user_id, self.player_country, self.player_data, at_war)
        view = View(timeout=120)
        view.add_item(select)
        
        back_btn = Button(label="Назад к типам ударов", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: show_strike_menu(i, self.user_id)
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_country_selection(self, interaction: discord.Interaction, strike_type: str):
        at_war = get_countries_at_war(self.player_country)
        if not at_war:
            await interaction.response.send_message("Нет стран, с которыми вы в состоянии войны!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор страны", 
            description=f"Тип удара: {strike_type}",
            color=DARK_THEME_COLOR
        )
        select = CountrySelectForStrike(self.user_id, self.player_country, self.player_data, at_war, strike_type)
        view = View(timeout=120)
        view.add_item(select)
        back_btn = Button(label="Назад к типам ударов", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: show_strike_menu(i, self.user_id)
        view.add_item(back_btn)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_navy_country_selection(self, interaction: discord.Interaction):
        at_war = get_countries_at_war(self.player_country)
        if not at_war:
            await interaction.response.send_message("Нет стран, с которыми вы в состоянии войны!", ephemeral=True)
            return
        
        embed = discord.Embed(title="Выбор страны", description="Тип удара: Военно-морской флот", color=DARK_THEME_COLOR)
        select = CountrySelectForStrike(self.user_id, self.player_country, self.player_data, at_war, "navy_fleet")
        view = View(timeout=120)
        view.add_item(select)
        back_btn = Button(label="Назад к типам ударов", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: show_strike_menu(i, self.user_id)
        view.add_item(back_btn)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_trade_country_selection(self, interaction: discord.Interaction):
        at_war = get_countries_at_war(self.player_country)
        if not at_war:
            await interaction.response.send_message("Нет стран, с которыми вы в состоянии войны!", ephemeral=True)
            return
        
        embed = discord.Embed(title="Выбор страны", description="Тип удара: Торговые конвои", color=DARK_THEME_COLOR)
        select = CountrySelectForStrike(self.user_id, self.player_country, self.player_data, at_war, "trade_convoy")
        view = View(timeout=120)
        view.add_item(select)
        back_btn = Button(label="Назад к типам ударов", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: show_strike_menu(i, self.user_id)
        view.add_item(back_btn)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_strike_menu(interaction, self.user_id)


class CountrySelectForStrike(Select):
    """Выбор страны для удара"""
    
    def __init__(self, user_id: int, player_country: str, player_data: Dict, at_war: List[str], strike_type: str):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.strike_type = strike_type
        
        options = [discord.SelectOption(label=country, value=country) for country in at_war[:25]]
        super().__init__(placeholder="Выберите страну...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        target_country = self.values[0]
        available_weapons = get_available_weapons(self.player_data, self.strike_type)
        
        if not available_weapons:
            await interaction.response.send_message("У вас нет доступного оружия!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор вооружения", 
            description=f"Цель: {target_country}\nТип удара: {self.strike_type}",
            color=DARK_THEME_COLOR
        )
        view = WeaponSelectViewForStrike(
            self.user_id, self.player_country, self.player_data,
            target_country, self.strike_type, available_weapons
        )
        await interaction.response.edit_message(embed=embed, view=view)


class CountrySelectForPortStrike(Select):
    """Выбор страны для удара наводными дронами"""
    
    def __init__(self, user_id: int, player_country: str, player_data: Dict, at_war: List[str]):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        
        options = [discord.SelectOption(label=country, value=country) for country in at_war[:25]]
        super().__init__(placeholder="Выберите страну...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        target_country = self.values[0]
        
        available_weapons = get_available_weapons(self.player_data)
        usv_available = [(w, q) for w, q in available_weapons if w == "usv_attack"]
        
        if not usv_available:
            await interaction.response.send_message("У вас нет наводных дронов! Закажите их через ВПК (раздел флота).", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор вооружения", 
            description=f"Цель: {target_country}\nТип удара: Наводные дроны",
            color=DARK_THEME_COLOR
        )
        view = WeaponSelectViewForUSV(
            self.user_id, self.player_country, self.player_data,
            target_country, usv_available
        )
        await interaction.response.edit_message(embed=embed, view=view)


class WeaponSelectViewForStrike(View):
    """Выбор оружия для удара (с поддержкой режима пустышек)"""
    
    def __init__(self, user_id: int, player_country: str, player_data: Dict,
                 target_country: str, strike_type: str, available_weapons: List[Tuple[str, int]]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.strike_type = strike_type
        self.decoy_mode = False
        
        has_kamikaze = any(w == "kamikaze_uav" for w, _ in available_weapons)
        if has_kamikaze:
            self.add_decoy_toggle_button()
        
        for weapon_id, quantity in available_weapons:
            weapon_info = STRIKE_WEAPONS[weapon_id]
            type_marker = "ПУС " if self.decoy_mode and weapon_id == "kamikaze_uav" else ""
            btn = Button(
                label=f"{type_marker}{weapon_info['name']} | {quantity} шт. | Дальн: {weapon_info['range']} км",
                style=discord.ButtonStyle.secondary,
                custom_id=f"weapon_{weapon_id}"
            )
            btn.callback = self.create_weapon_callback(weapon_id, weapon_info, quantity)
            self.add_item(btn)
        
        back_btn = Button(label="Назад к странам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    def add_decoy_toggle_button(self):
        label = "Режим пустышек: ВЫКЛ" if not self.decoy_mode else "Режим пустышек: ВКЛ"
        style = discord.ButtonStyle.secondary if not self.decoy_mode else discord.ButtonStyle.success
        
        decoy_btn = Button(label=label, style=style, custom_id="decoy_toggle")
        decoy_btn.callback = self.toggle_decoy_mode
        self.add_item(decoy_btn)
    
    async def toggle_decoy_mode(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        self.decoy_mode = not self.decoy_mode
        
        for item in self.children:
            if getattr(item, 'custom_id', '') == "decoy_toggle":
                self.remove_item(item)
                break
        
        self.add_decoy_toggle_button()
        
        for item in self.children:
            if isinstance(item, Button) and item.custom_id and item.custom_id.startswith("weapon_"):
                weapon_id = item.custom_id.replace("weapon_", "")
                if weapon_id == "kamikaze_uav":
                    weapon_info = STRIKE_WEAPONS[weapon_id]
                    type_marker = "ПУС " if self.decoy_mode else ""
                    quantity_str = item.label.split("|")[1] if "|" in item.label else ""
                    item.label = f"{type_marker}{weapon_info['name']} | {quantity_str}"
        
        await interaction.response.edit_message(view=self)
    
    def create_weapon_callback(self, weapon_id: str, weapon_info: Dict, max_quantity: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            
            is_decoy = self.decoy_mode and weapon_id == "kamikaze_uav"
            
            modal = QuantityModalForStrike(
                self.user_id, self.player_country, self.player_data,
                self.target_country, self.strike_type, weapon_id, weapon_info, max_quantity,
                is_decoy
            )
            await interaction.response.send_modal(modal)
        return callback
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        at_war = get_countries_at_war(self.player_country)
        embed = discord.Embed(title="Выбор страны", description=f"Тип удара: {self.strike_type}", color=DARK_THEME_COLOR)
        select = CountrySelectForStrike(self.user_id, self.player_country, self.player_data, at_war, self.strike_type)
        view = View(timeout=120)
        view.add_item(select)
        back_btn = Button(label="Назад к типам ударов", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: show_strike_menu(i, self.user_id)
        view.add_item(back_btn)
        await interaction.response.edit_message(embed=embed, view=view)


class WeaponSelectViewForUSV(View):
    """Выбор оружия для удара наводными дронами"""
    
    def __init__(self, user_id: int, player_country: str, player_data: Dict,
                 target_country: str, available_weapons: List[Tuple[str, int]]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        
        for weapon_id, quantity in available_weapons:
            weapon_info = STRIKE_WEAPONS[weapon_id]
            btn = Button(
                label=f"{weapon_info['name']} | {quantity} шт. | Дальн: {weapon_info['range']} км",
                style=discord.ButtonStyle.secondary,
                custom_id=f"weapon_{weapon_id}"
            )
            btn.callback = self.create_weapon_callback(weapon_id, weapon_info, quantity)
            self.add_item(btn)
        
        back_btn = Button(label="Назад к странам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    def create_weapon_callback(self, weapon_id: str, weapon_info: Dict, max_quantity: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            
            modal = QuantityModalForUSV(
                self.user_id, self.player_country, self.player_data,
                self.target_country, weapon_id, weapon_info, max_quantity
            )
            await interaction.response.send_modal(modal)
        return callback
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        at_war = get_countries_at_war(self.player_country)
        embed = discord.Embed(
            title="Выбор страны", 
            description="Тип удара: Наводные дроны",
            color=DARK_THEME_COLOR
        )
        select = CountrySelectForPortStrike(self.user_id, self.player_country, self.player_data, at_war)
        view = View(timeout=120)
        view.add_item(select)
        back_btn = Button(label="Назад к типам ударов", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: show_strike_menu(i, self.user_id)
        view.add_item(back_btn)
        await interaction.response.edit_message(embed=embed, view=view)


class QuantityModalForStrike(Modal, title="Количество оружия"):
    def __init__(self, user_id: int, player_country: str, player_data: Dict,
                 target_country: str, strike_type: str, weapon_id: str, weapon_info: Dict, 
                 max_quantity: int, is_decoy: bool = False):
        super().__init__()
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.strike_type = strike_type
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.max_quantity = max_quantity
        self.is_decoy = is_decoy
        
        if is_decoy:
            self.quantity_input = TextInput(
                label=f"Количество дронов-камикадзе (макс: {max_quantity})",
                placeholder="Введите число (1 камикадзе = 2 пустышки в воздухе)",
                min_length=1,
                max_length=4,
                required=True,
                default="1"
            )
        else:
            self.quantity_input = TextInput(
                label=f"Количество (макс: {max_quantity})",
                placeholder="Введите число",
                min_length=1,
                max_length=4,
                required=True,
                default="1"
            )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > self.max_quantity:
                await interaction.response.send_message(f"Количество от 1 до {self.max_quantity}!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Введите число!", ephemeral=True)
            return
        
        attacker_regions = get_player_regions(self.player_country)
        if not attacker_regions:
            await interaction.response.send_message("У вас нет регионов для запуска!", ephemeral=True)
            return
        
        if self.strike_type == "infrastructure":
            await show_attacker_economic_region_selection(
                interaction, self.user_id, self.player_country, self.player_data,
                self.target_country, self.strike_type, self.weapon_id, 
                self.weapon_info, quantity, self.is_decoy
            )
        elif self.strike_type == "navy_fleet":
            await show_navy_strike_zone_selection(
                interaction, self.user_id, self.player_country, self.player_data,
                self.target_country, self.weapon_id, self.weapon_info, quantity
            )
        elif self.strike_type == "trade_convoy":
            await show_trade_strike_zone_selection(
                interaction, self.user_id, self.player_country, self.player_data,
                self.target_country, self.weapon_id, self.weapon_info, quantity
            )


class QuantityModalForUSV(Modal, title="Количество наводных дронов"):
    def __init__(self, user_id: int, player_country: str, player_data: Dict,
                 target_country: str, weapon_id: str, weapon_info: Dict, max_quantity: int):
        super().__init__()
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.max_quantity = max_quantity
        
        self.quantity_input = TextInput(
            label=f"Количество (макс: {max_quantity})",
            placeholder="Введите число",
            min_length=1,
            max_length=4,
            required=True,
            default="1"
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > self.max_quantity:
                await interaction.response.send_message(f"Количество от 1 до {self.max_quantity}!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Введите число!", ephemeral=True)
            return
        
        attacker_regions = get_player_regions(self.player_country)
        if not attacker_regions:
            await interaction.response.send_message("У вас нет регионов для запуска!", ephemeral=True)
            return
        
        coastal_attacker_regions = [r for r in attacker_regions if is_region_coastal(r, self.player_country)]
        if not coastal_attacker_regions:
            await interaction.response.send_message("У вас нет прибрежных регионов для запуска наводных дронов!", ephemeral=True)
            return
        
        await show_attacker_economic_region_selection_for_usv(
            interaction, self.user_id, self.player_country, self.player_data,
            self.target_country, self.weapon_id, self.weapon_info, quantity, coastal_attacker_regions
        )


async def show_attacker_economic_region_selection(interaction, user_id, player_country, player_data,
                                                   target_country, strike_type, weapon_id, weapon_info, quantity, is_decoy=False):
    """Показывает выбор экономического района для запуска"""
    
    economic_regions = get_country_economic_regions(player_country)
    
    if not economic_regions:
        await interaction.response.send_message("У вашей страны нет экономических районов!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Выбор экономического района для запуска",
        description=f"Цель: {target_country}\nОружие: {weapon_info['name']} x{quantity}" + (" (режим пустышек)" if is_decoy else ""),
        color=DARK_THEME_COLOR
    )
    
    select = AttackerEconomicRegionSelect(
        user_id, player_country, player_data, target_country, strike_type,
        weapon_id, weapon_info, quantity, economic_regions, is_decoy
    )
    view = View(timeout=120)
    view.add_item(select)
    
    back_btn = Button(label="Назад к оружию", style=discord.ButtonStyle.secondary)
    back_btn.callback = lambda i: show_strike_menu(i, user_id)
    view.add_item(back_btn)
    
    await interaction.response.edit_message(embed=embed, view=view)


class AttackerEconomicRegionSelect(Select):
    """Выбор экономического района для запуска"""
    
    def __init__(self, user_id, player_country, player_data, target_country, strike_type,
                 weapon_id, weapon_info, quantity, economic_regions, is_decoy):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.strike_type = strike_type
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.economic_regions = economic_regions
        self.is_decoy = is_decoy
        
        options = []
        for econ_region, econ_data in list(economic_regions.items())[:25]:
            region_count = len(econ_data.get("regions", {}))
            options.append(discord.SelectOption(
                label=econ_region[:100],
                description=f"Регионов: {region_count}",
                value=econ_region
            ))
        
        super().__init__(placeholder="Выберите экономический район...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = self.values[0]
        
        regions = get_regions_in_economic_region(self.player_country, econ_region)
        
        embed = discord.Embed(
            title="Выбор региона запуска",
            description=f"Цель: {self.target_country}\nОружие: {self.weapon_info['name']} x{self.quantity}\nРайон: {econ_region}" + (" (режим пустышек)" if self.is_decoy else ""),
            color=DARK_THEME_COLOR
        )
        
        select = AttackerRegionSelect(
            self.user_id, self.player_country, self.player_data, self.target_country,
            self.strike_type, self.weapon_id, self.weapon_info, self.quantity,
            econ_region, regions, self.is_decoy
        )
        view = View(timeout=120)
        view.add_item(select)
        
        back_btn = Button(label="Назад к экономическим районам", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: asyncio.create_task(show_attacker_economic_region_selection(
            interaction, self.user_id, self.player_country, self.player_data,
            self.target_country, self.strike_type, self.weapon_id, 
            self.weapon_info, self.quantity, self.is_decoy
        ))
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)


class AttackerRegionSelect(Select):
    """Выбор конкретного региона для запуска"""
    
    def __init__(self, user_id, player_country, player_data, target_country, strike_type,
                 weapon_id, weapon_info, quantity, econ_region, regions, is_decoy):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.strike_type = strike_type
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.econ_region = econ_region
        self.is_decoy = is_decoy
        
        options = []
        for region_name, region_data in list(regions.items())[:25]:
            population = region_data.get("population", 0)
            military = get_asset_total(region_data, "military_factories")
            
            options.append(discord.SelectOption(
                label=region_name[:100],
                description=f"Население: {population//1000000}млн | Воен: {military}",
                value=region_name
            ))
        
        super().__init__(placeholder="Выберите регион для запуска...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        attacker_region = self.values[0]
        
        if self.strike_type == "infrastructure":
            await show_target_economic_region_selection(
                interaction, self.user_id, self.player_country, self.player_data,
                self.target_country, self.weapon_id, self.weapon_info, self.quantity, attacker_region, self.is_decoy
            )
        elif self.strike_type == "air_defense":
            await show_air_defense_target_selection(
                interaction, self.user_id, self.player_country, self.target_country,
                self.weapon_id, self.weapon_info, self.quantity, attacker_region, self.is_decoy
            )


async def show_attacker_economic_region_selection_for_usv(interaction, user_id, player_country, player_data,
                                                            target_country, weapon_id, weapon_info, quantity, coastal_regions):
    """Показывает выбор атакующего региона для наводных дронов (только прибрежные)"""
    
    economic_regions = get_country_economic_regions(player_country)
    
    if not economic_regions:
        await interaction.response.send_message("У вашей страны нет экономических районов!", ephemeral=True)
        return
    
    filtered_economic_regions = {}
    for econ_region, econ_data in economic_regions.items():
        regions_in_econ = econ_data.get("regions", {})
        has_coastal = any(r in coastal_regions for r in regions_in_econ.keys())
        if has_coastal:
            filtered_economic_regions[econ_region] = econ_data
    
    if not filtered_economic_regions:
        await interaction.response.send_message("В ваших экономических районах нет прибрежных регионов для запуска!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Выбор экономического района для запуска (наводные дроны)",
        description=f"Цель: {target_country}\nОружие: {weapon_info['name']} x{quantity}\nЗапуск только из прибрежных регионов",
        color=DARK_THEME_COLOR
    )
    
    select = AttackerEconomicRegionSelectForUSV(
        user_id, player_country, player_data, target_country,
        weapon_id, weapon_info, quantity, filtered_economic_regions, coastal_regions
    )
    view = View(timeout=120)
    view.add_item(select)
    
    back_btn = Button(label="Назад к оружию", style=discord.ButtonStyle.secondary)
    back_btn.callback = lambda i: show_strike_menu(i, user_id)
    view.add_item(back_btn)
    
    await interaction.response.edit_message(embed=embed, view=view)


class AttackerEconomicRegionSelectForUSV(Select):
    """Выбор экономического района для запуска наводных дронов"""
    
    def __init__(self, user_id, player_country, player_data, target_country,
                 weapon_id, weapon_info, quantity, economic_regions, coastal_regions):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.economic_regions = economic_regions
        self.coastal_regions = coastal_regions
        
        options = []
        for econ_region, econ_data in list(economic_regions.items())[:25]:
            region_count = len(econ_data.get("regions", {}))
            options.append(discord.SelectOption(
                label=econ_region[:100],
                description=f"Регионов: {region_count}",
                value=econ_region
            ))
        
        super().__init__(placeholder="Выберите экономический район...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = self.values[0]
        
        regions = get_regions_in_economic_region(self.player_country, econ_region)
        
        coastal_regions_in_econ = {name: data for name, data in regions.items() if name in self.coastal_regions}
        
        if not coastal_regions_in_econ:
            await interaction.response.send_message(f"В районе {econ_region} нет прибрежных регионов для запуска!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор региона запуска (прибрежный)",
            description=f"Цель: {self.target_country}\nОружие: {self.weapon_info['name']} x{self.quantity}\nРайон: {econ_region}",
            color=DARK_THEME_COLOR
        )
        
        select = AttackerRegionSelectForUSV(
            self.user_id, self.player_country, self.player_data, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity,
            econ_region, coastal_regions_in_econ
        )
        view = View(timeout=120)
        view.add_item(select)
        
        back_btn = Button(label="Назад к экономическим районам", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: asyncio.create_task(show_attacker_economic_region_selection_for_usv(
            i, self.user_id, self.player_country, self.player_data,
            self.target_country, self.weapon_id, self.weapon_info, self.quantity, self.coastal_regions
        ))
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)


class AttackerRegionSelectForUSV(Select):
    """Выбор конкретного прибрежного региона для запуска наводных дронов"""
    
    def __init__(self, user_id, player_country, player_data, target_country,
                 weapon_id, weapon_info, quantity, econ_region, regions):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.econ_region = econ_region
        
        options = []
        for region_name, region_data in list(regions.items())[:25]:
            population = region_data.get("population", 0)
            military = get_asset_total(region_data, "military_factories")
            coastal_marker = "🏝 "
            
            options.append(discord.SelectOption(
                label=f"{coastal_marker}{region_name[:97]}",
                description=f"Население: {population//1000000}млн | Воен: {military}",
                value=region_name
            ))
        
        super().__init__(placeholder="Выберите прибрежный регион для запуска...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        attacker_region = self.values[0]
        
        await show_usv_target_selection(
            interaction, self.user_id, self.player_country, self.player_data,
            self.target_country, self.weapon_id, self.weapon_info, self.quantity, attacker_region
        )


async def show_usv_target_selection(interaction, user_id, player_country, player_data,
                                     target_country, weapon_id, weapon_info, quantity, attacker_region):
    """Показывает выбор цели для наводных дронов"""
    
    economic_regions = get_country_economic_regions(target_country)
    
    if not economic_regions:
        await interaction.response.send_message(f"У страны {target_country} нет экономических районов!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Выбор экономического района цели",
        description=f"Атакующий регион: {attacker_region}\nЦель: {target_country}\nОружие: {weapon_info['name']} x{quantity}\nАтакуются только прибрежные регионы",
        color=DARK_THEME_COLOR
    )
    
    select = TargetEconomicRegionSelectForUSV(
        user_id, player_country, player_data, target_country, weapon_id, weapon_info,
        quantity, attacker_region, economic_regions
    )
    view = View(timeout=120)
    view.add_item(select)
    
    back_btn = Button(label="Назад к выбору региона запуска", style=discord.ButtonStyle.secondary)
    back_btn.callback = lambda i: asyncio.create_task(show_attacker_economic_region_selection_for_usv(
        i, user_id, player_country, player_data,
        target_country, weapon_id, weapon_info, quantity,
        [attacker_region]
    ))
    view.add_item(back_btn)
    
    await interaction.response.edit_message(embed=embed, view=view)


class TargetEconomicRegionSelectForUSV(Select):
    """Выбор экономического района цели для наводных дронов"""
    
    def __init__(self, user_id, player_country, player_data, target_country, weapon_id, weapon_info,
                 quantity, attacker_region, economic_regions):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.economic_regions = economic_regions
        
        options = []
        for econ_region, econ_data in list(economic_regions.items())[:25]:
            region_count = len(econ_data.get("regions", {}))
            options.append(discord.SelectOption(
                label=econ_region[:100],
                description=f"Регионов: {region_count}",
                value=econ_region
            ))
        
        super().__init__(placeholder="Выберите экономический район цели...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = self.values[0]
        
        regions = get_regions_in_economic_region(self.target_country, econ_region)
        
        embed = discord.Embed(
            title="Выбор региона цели (прибрежный)",
            description=f"Атакующий регион: {self.attacker_region}\n"
                       f"Цель: {self.target_country} / {econ_region}\n"
                       f"Оружие: {self.weapon_info['name']} x{self.quantity}",
            color=DARK_THEME_COLOR
        )
        
        select = TargetRegionSelectForUSV(
            self.user_id, self.player_country, self.player_data, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity, self.attacker_region,
            econ_region, regions
        )
        view = View(timeout=120)
        view.add_item(select)
        
        back_btn = Button(label="Назад к экономическим районам", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: asyncio.create_task(show_usv_target_selection(
            i, self.user_id, self.player_country, self.player_data,
            self.target_country, self.weapon_id, self.weapon_info, self.quantity, self.attacker_region
        ))
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)


class TargetRegionSelectForUSV(Select):
    """Выбор конкретного прибрежного региона цели для наводных дронов"""
    
    def __init__(self, user_id, player_country, player_data, target_country, weapon_id, weapon_info,
                 quantity, attacker_region, econ_region, regions):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.econ_region = econ_region
        self.regions = regions
        
        options = []
        for region_name, region_data in list(regions.items())[:25]:
            if not is_region_coastal(region_name, target_country):
                continue
            
            reachable, distance = is_region_reachable(
                player_country, attacker_region,
                target_country, region_name,
                weapon_info["range"]
            )
            
            shipyards = get_asset_total(region_data, "shipyards")
            ships_in_port = len(get_ships_in_port_region(region_name, target_country))
            
            if reachable:
                status = "✅"
                desc = f"{distance} км | Верфи: {shipyards} | Судов в порту: {ships_in_port}"
            else:
                status = "❌"
                desc = f"{distance} км (вне зоны)"
            
            options.append(discord.SelectOption(
                label=f"{status} {region_name[:95]}",
                description=desc,
                value=region_name
            ))
        
        if not options:
            options.append(discord.SelectOption(
                label="Нет доступных прибрежных регионов",
                value="none",
                default=True
            ))
        
        super().__init__(placeholder="Выберите прибрежный регион цели...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        if self.values[0] == "none":
            await interaction.response.send_message("Нет доступных прибрежных регионов!", ephemeral=True)
            return
        
        target_region = self.values[0]
        
        infra = load_infrastructure()
        region_data = None
        for cid, cdata in infra["infrastructure"].items():
            if cdata.get("country") == self.target_country:
                for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                    for r_name, r_data in econ_data.get("regions", {}).items():
                        if r_name == target_region:
                            region_data = r_data
                            break
                break
        
        if not region_data:
            await interaction.response.send_message("Данные региона не найдены!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор цели",
            description=f"Атакующий регион: {self.attacker_region}\n"
                       f"Цель: {self.target_country} / {self.econ_region} / {target_region}\n"
                       f"Оружие: {self.weapon_info['name']} x{self.quantity}",
            color=DARK_THEME_COLOR
        )
        
        view = USVTargetTypeSelectView(
            self.user_id, self.player_country, self.player_data, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity, self.attacker_region,
            target_region, region_data
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class USVTargetTypeSelectView(View):
    """Выбор типа цели для наводных дронов"""
    
    def __init__(self, user_id, player_country, player_data, target_country,
                 weapon_id, weapon_info, quantity, attacker_region,
                 target_region, region_data):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.target_region = target_region
        self.region_data = region_data
        
        shipyards_btn = Button(label="Верфи", style=discord.ButtonStyle.primary)
        shipyards_btn.callback = self.select_shipyards
        self.add_item(shipyards_btn)
        
        navy_btn = Button(label="Военно-морской флот", style=discord.ButtonStyle.danger)
        navy_btn.callback = self.select_navy
        self.add_item(navy_btn)
        
        trade_btn = Button(label="Торговые суда", style=discord.ButtonStyle.success)
        trade_btn.callback = self.select_trade
        self.add_item(trade_btn)
        
        back_btn = Button(label="Назад к регионам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def select_shipyards(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await self.show_confirmation(interaction, "shipyards")
    
    async def select_navy(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await self.show_confirmation(interaction, "navy_fleet")
    
    async def select_trade(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await self.show_confirmation(interaction, "trade_convoy")
    
    async def show_confirmation(self, interaction: discord.Interaction, target_type: str):
        shipyards = get_asset_total(self.region_data, "shipyards")
        ships_in_port = len(get_ships_in_port_region(self.target_region, self.target_country))
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ УДАРА",
            description=f"Операция против {self.target_country}",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Атакующий регион", value=self.attacker_region, inline=True)
        embed.add_field(name="Целевой регион", value=self.target_region, inline=True)
        embed.add_field(name="Расстояние", value=str(get_region_distance(
            self.player_country, self.attacker_region,
            self.target_country, self.target_region
        )), inline=True)
        embed.add_field(name="Оружие", value=f"{self.weapon_info['name']} x{self.quantity}", inline=True)
        
        if target_type == "shipyards":
            embed.add_field(name="Цели", value=f"Верфи: {shipyards}", inline=True)
        elif target_type == "navy_fleet":
            embed.add_field(name="Цели", value="Корабли в порту", inline=True)
        elif target_type == "trade_convoy":
            embed.add_field(name="Цели", value=f"Судов в порту: {ships_in_port}", inline=True)
        
        embed.add_field(
            name="Предупреждение",
            value="Оружие будет списано из армии независимо от результата. Подтверждаете пуск?",
            inline=False
        )
        
        view = USVConfirmationView(
            self.user_id, self.player_country, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity, self.attacker_region,
            self.target_region, self.region_data, target_type
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await show_usv_target_selection(
            interaction, self.user_id, self.player_country, self.player_data,
            self.target_country, self.weapon_id, self.weapon_info, self.quantity, self.attacker_region
        )


class USVConfirmationView(View):
    """Подтверждение удара наводными дронами"""
    
    def __init__(self, user_id, player_country, target_country,
                 weapon_id, weapon_info, quantity, attacker_region,
                 target_region, region_data, target_type):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.target_region = target_region
        self.region_data = region_data
        self.target_type = target_type
        self.bot = None
    
    @discord.ui.button(label="ПОДТВЕРДИТЬ ПУСК", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await interaction.response.defer()
        self.bot = interaction.client
        
        states = load_states()
        
        attacker_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                attacker_data = data
                break
        
        if not attacker_data:
            await interaction.followup.send("Ошибка загрузки данных игрока!", ephemeral=True)
            return
        
        if not consume_weapon(attacker_data, self.weapon_id, self.quantity, False):
            await interaction.followup.send("Ошибка при списании оружия! Возможно, у вас недостаточно оружия.", ephemeral=True)
            return
        
        result = execute_usv_strike(
            attacker_data, self.target_country, self.target_region,
            self.weapon_id, self.quantity, self.region_data, self.attacker_region,
            self.target_type
        )
        
        if not result["success"]:
            await interaction.followup.send(result["message"], ephemeral=True)
            return
        
        save_states(states)
        
        strikes = load_strikes()
        strike_record = {
            "id": len(strikes["strikes"]) + 1,
            "attacker": self.player_country,
            "attacker_region": self.attacker_region,
            "attacker_id": str(self.user_id),
            "target": self.target_country,
            "target_region": self.target_region,
            "weapon": self.weapon_info["name"],
            "weapon_id": self.weapon_id,
            "quantity": self.quantity,
            "target_type": f"usv_{self.target_type}",
            "intercepted": result.get("intercepted_count", 0),
            "surviving": result.get("surviving", 0),
            "hits": result.get("hits", 0),
            "destroyed": result.get("destroyed_objects", 0),
            "distance": result.get("distance", 0),
            "timestamp": str(datetime.now())
        }
        strikes["strikes"].append(strike_record)
        save_strikes(strikes)
        
        embed = discord.Embed(
            title="РЕЗУЛЬТАТ УДАРА",
            description=result["message"],
            color=discord.Color.red() if result["destroyed_objects"] > 0 else discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        if self.bot:
            await send_strike_log(self.bot, {
                "attacker": self.player_country,
                "attacker_region": self.attacker_region,
                "target": self.target_country,
                "target_region": self.target_region,
                "weapon_name": self.weapon_info["name"],
                "quantity": self.quantity,
                "distance": result.get("distance", 0),
                "intercepted_count": result.get("intercepted_count", 0),
                "final_chance": result.get("final_chance", 0),
                "hits": result.get("hits", 0),
                "destroyed_objects": result.get("destroyed_objects", 0),
                "civilian_casualties": 0,
                "targets_hit": None,
                "message": result["message"]
            })
    
    @discord.ui.button(label="ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Пуск отменён",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=None)


async def show_target_economic_region_selection(interaction, user_id, player_country, player_data,
                                                 target_country, weapon_id, weapon_info, quantity, attacker_region, is_decoy=False):
    """Показывает выбор экономического района цели"""
    
    economic_regions = get_country_economic_regions(target_country)
    
    if not economic_regions:
        await interaction.response.send_message(f"У страны {target_country} нет экономических районов!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Выбор экономического района цели",
        description=f"Атакующий регион: {attacker_region}\nЦель: {target_country}\nОружие: {weapon_info['name']} x{quantity}" + (" (режим пустышек)" if is_decoy else ""),
        color=DARK_THEME_COLOR
    )
    
    select = TargetEconomicRegionSelect(
        user_id, player_country, player_data, target_country, weapon_id, weapon_info,
        quantity, attacker_region, economic_regions, is_decoy
    )
    view = View(timeout=120)
    view.add_item(select)
    
    back_btn = Button(label="Назад к выбору региона запуска", style=discord.ButtonStyle.secondary)
    back_btn.callback = lambda i: asyncio.create_task(show_attacker_economic_region_selection(
        interaction, user_id, player_country, player_data, target_country, "infrastructure",
        weapon_id, weapon_info, quantity, is_decoy
    ))
    view.add_item(back_btn)
    
    await interaction.response.edit_message(embed=embed, view=view)


class TargetEconomicRegionSelect(Select):
    """Выбор экономического района цели"""
    
    def __init__(self, user_id, player_country, player_data, target_country, weapon_id, weapon_info,
                 quantity, attacker_region, economic_regions, is_decoy):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.economic_regions = economic_regions
        self.is_decoy = is_decoy
        
        options = []
        for econ_region, econ_data in list(economic_regions.items())[:25]:
            region_count = len(econ_data.get("regions", {}))
            options.append(discord.SelectOption(
                label=econ_region[:100],
                description=f"Регионов: {region_count}",
                value=econ_region
            ))
        
        super().__init__(placeholder="Выберите экономический район цели...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = self.values[0]
        
        regions = get_regions_in_economic_region(self.target_country, econ_region)
        
        embed = discord.Embed(
            title="Выбор региона цели",
            description=f"Атакующий регион: {self.attacker_region}\n"
                       f"Цель: {self.target_country} / {econ_region}\n"
                       f"Оружие: {self.weapon_info['name']} x{self.quantity}" + (" (режим пустышек)" if self.is_decoy else ""),
            color=DARK_THEME_COLOR
        )
        
        select = TargetRegionSelect(
            self.user_id, self.player_country, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity, self.attacker_region,
            econ_region, regions, self.is_decoy
        )
        view = View(timeout=120)
        view.add_item(select)
        
        back_btn = Button(label="Назад к экономическим районам", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda i: asyncio.create_task(show_target_economic_region_selection(
            i, self.user_id, self.player_country, self.player_data,
            self.target_country, self.weapon_id, self.weapon_info, self.quantity, self.attacker_region, self.is_decoy
        ))
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)


class TargetRegionSelect(Select):
    """Выбор конкретного региона цели"""
    
    def __init__(self, user_id, player_country, target_country, weapon_id, weapon_info,
                 quantity, attacker_region, econ_region, regions, is_decoy):
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.econ_region = econ_region
        self.regions = regions
        self.is_decoy = is_decoy
        
        options = []
        for region_name, region_data in list(regions.items())[:25]:
            reachable, distance = is_region_reachable(
                player_country, attacker_region,
                target_country, region_name,
                weapon_info["range"]
            )
            
            total_targets = count_targets_in_region(region_data, None)
            
            population = region_data.get("population", 0)
            
            if reachable:
                status = "✅"
                desc = f"{distance} км | Целей: {total_targets} | {population//1000000}млн"
            else:
                status = "❌"
                desc = f"{distance} км (вне зоны)"
            
            options.append(discord.SelectOption(
                label=f"{status} {region_name[:95]}",
                description=desc,
                value=region_name
            ))
        
        super().__init__(placeholder="Выберите регион цели...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        target_region = self.values[0]
        region_data = self.regions[target_region]
        
        reachable, distance = is_region_reachable(
            self.player_country, self.attacker_region,
            self.target_country, target_region,
            self.weapon_info["range"]
        )
        
        if not reachable:
            await interaction.response.send_message(
                f"Регион {target_region} на расстоянии {distance} км (макс. {self.weapon_info['range']} км)!",
                ephemeral=True
            )
            return
        
        available_targets = get_all_targets_in_region(region_data, self.target_country)
        
        if not available_targets:
            embed = discord.Embed(
                title="Нет целей",
                description="В этом регионе нет доступных объектов для удара.",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        embed = discord.Embed(
            title="Выбор целей",
            description=f"Атакующий регион: {self.attacker_region}\n"
                       f"Цель: {self.target_country} / {self.econ_region} / {target_region}\n"
                       f"Оружие: {self.weapon_info['name']} x{self.quantity}" + (" (режим пустышек)" if self.is_decoy else "") + f"\n\n"
                       f"Выберите типы целей для удара (можно несколько)",
            color=DARK_THEME_COLOR
        )
        
        view = MultipleTargetsView(
            self.user_id, self.player_country, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity, self.attacker_region,
            target_region, region_data, available_targets, self.is_decoy
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


async def show_air_defense_target_selection(interaction, user_id, player_country, target_country,
                                            weapon_id, weapon_info, quantity, attacker_region, is_decoy=False):
    """Показывает выбор региона для удара по ПВО"""
    await show_target_economic_region_selection(
        interaction, user_id, player_country, player_data,
        target_country, weapon_id, weapon_info, quantity, attacker_region, is_decoy
    )


async def show_navy_strike_zone_selection(interaction, user_id, player_country, player_data,
                                          target_country, weapon_id, weapon_info, quantity):
    """Показывает выбор морской зоны для удара по флоту"""
    try:
        from navy import SeaZone
    except ImportError:
        await interaction.response.send_message("Модуль военно-морского флота недоступен!", ephemeral=True)
        return
    
    zones_with_fleets = []
    for zone in SeaZone:
        fleets = get_fleets_in_zone(target_country, zone)
        if fleets:
            zones_with_fleets.append(zone)
    
    if not zones_with_fleets:
        await interaction.response.send_message(f"У {target_country} нет флотов ни в одной морской зоне!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Выбор морской зоны",
        description=f"Цель: {target_country}\nОружие: {weapon_info['name']} x{quantity}",
        color=DARK_THEME_COLOR
    )
    
    select = NavalZoneSelectForStrike(
        user_id, player_country, player_data, target_country,
        weapon_id, weapon_info, quantity, zones_with_fleets
    )
    view = View(timeout=120)
    view.add_item(select)
    
    back_btn = Button(label="Назад к оружию", style=discord.ButtonStyle.secondary)
    back_btn.callback = lambda i: show_strike_menu(i, user_id)
    view.add_item(back_btn)
    
    await interaction.response.edit_message(embed=embed, view=view)


class NavalZoneSelectForStrike(Select):
    """Выбор морской зоны для удара по флоту"""
    
    def __init__(self, user_id, player_country, player_data, target_country,
                 weapon_id, weapon_info, quantity, zones):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        
        options = []
        for zone in zones:
            fleets = get_fleets_in_zone(target_country, zone)
            total_ships = sum(f["total_ships"] for f in fleets)
            options.append(discord.SelectOption(
                label=zone.value,
                description=f"Кораблей: {total_ships}",
                value=zone.value
            ))
        
        super().__init__(placeholder="Выберите морскую зону...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        sea_zone = self.values[0]
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ УДАРА",
            description=f"Операция против {self.target_country}",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Морская зона", value=sea_zone, inline=True)
        embed.add_field(name="Оружие", value=f"{self.weapon_info['name']} x{self.quantity}", inline=True)
        
        view = NavalStrikeConfirmationView(
            self.user_id, self.player_country, self.player_data,
            self.target_country, sea_zone, self.weapon_id, self.weapon_info, self.quantity
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class NavalStrikeConfirmationView(View):
    """Подтверждение удара по флоту"""
    
    def __init__(self, user_id, player_country, player_data, target_country,
                 sea_zone, weapon_id, weapon_info, quantity):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.sea_zone = sea_zone
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
    
    @discord.ui.button(label="ПОДТВЕРДИТЬ ПУСК", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        states = load_states()
        attacker_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                attacker_data = data
                break
        
        if not attacker_data:
            await interaction.followup.send("Ошибка загрузки данных!", ephemeral=True)
            return
        
        if not consume_weapon(attacker_data, self.weapon_id, self.quantity, False):
            await interaction.followup.send("Ошибка при списании оружия!", ephemeral=True)
            return
        
        result = execute_naval_strike(
            attacker_data, self.target_country, self.sea_zone,
            self.weapon_id, self.quantity, "navy_fleet"
        )
        
        if not result["success"]:
            await interaction.followup.send(result["message"], ephemeral=True)
            return
        
        save_states(states)
        
        strikes = load_strikes()
        strikes["strikes"].append({
            "id": len(strikes["strikes"]) + 1,
            "attacker": self.player_country,
            "target": self.target_country,
            "weapon": self.weapon_info["name"],
            "quantity": self.quantity,
            "target_type": "navy",
            "zone": self.sea_zone,
            "intercepted": result.get("intercepted_count", 0),
            "destroyed": result.get("destroyed_objects", 0),
            "timestamp": str(datetime.now())
        })
        save_strikes(strikes)
        
        embed = discord.Embed(
            title="РЕЗУЛЬТАТ УДАРА",
            description=result["message"],
            color=discord.Color.red() if result["destroyed_objects"] > 0 else discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(title="Пуск отменён", color=DARK_THEME_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)


async def show_trade_strike_zone_selection(interaction, user_id, player_country, player_data,
                                           target_country, weapon_id, weapon_info, quantity):
    """Показывает выбор морской зоны для удара по торговым конвоям"""
    try:
        from navy import SeaZone
    except ImportError:
        await interaction.response.send_message("Модуль морской торговли недоступен!", ephemeral=True)
        return
    
    zones_with_ships = []
    for zone in SeaZone:
        ships = get_trade_ships_in_zone(target_country, zone, include_sailing=True)
        if ships:
            zones_with_ships.append(zone)
    
    if not zones_with_ships:
        await interaction.response.send_message(f"У {target_country} нет торговых судов ни в одной морской зоне!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Выбор морской зоны",
        description=f"Цель: {target_country}\nОружие: {weapon_info['name']} x{quantity}",
        color=DARK_THEME_COLOR
    )
    
    select = TradeZoneSelectForStrike(
        user_id, player_country, player_data, target_country,
        weapon_id, weapon_info, quantity, zones_with_ships
    )
    view = View(timeout=120)
    view.add_item(select)
    
    back_btn = Button(label="Назад к оружию", style=discord.ButtonStyle.secondary)
    back_btn.callback = lambda i: show_strike_menu(i, user_id)
    view.add_item(back_btn)
    
    await interaction.response.edit_message(embed=embed, view=view)


class TradeZoneSelectForStrike(Select):
    """Выбор морской зоны для удара по торговым конвоям"""
    
    def __init__(self, user_id, player_country, player_data, target_country,
                 weapon_id, weapon_info, quantity, zones):
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        
        options = []
        for zone in zones:
            ships = get_trade_ships_in_zone(target_country, zone, include_sailing=True)
            total_cargo = sum(s["cargo_value"] for s in ships)
            options.append(discord.SelectOption(
                label=zone.value,
                description=f"Судов: {len(ships)}, груз: ${total_cargo:,.0f}",
                value=zone.value
            ))
        
        super().__init__(placeholder="Выберите морскую зону...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        sea_zone = self.values[0]
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ УДАРА",
            description=f"Операция против {self.target_country}",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Морская зона", value=sea_zone, inline=True)
        embed.add_field(name="Оружие", value=f"{self.weapon_info['name']} x{self.quantity}", inline=True)
        
        view = TradeStrikeConfirmationView(
            self.user_id, self.player_country, self.player_data,
            self.target_country, sea_zone, self.weapon_id, self.weapon_info, self.quantity
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class TradeStrikeConfirmationView(View):
    """Подтверждение удара по торговым конвоям"""
    
    def __init__(self, user_id, player_country, player_data, target_country,
                 sea_zone, weapon_id, weapon_info, quantity):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_country = player_country
        self.player_data = player_data
        self.target_country = target_country
        self.sea_zone = sea_zone
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
    
    @discord.ui.button(label="ПОДТВЕРДИТЬ ПУСК", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        states = load_states()
        attacker_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                attacker_data = data
                break
        
        if not attacker_data:
            await interaction.followup.send("Ошибка загрузки данных!", ephemeral=True)
            return
        
        if not consume_weapon(attacker_data, self.weapon_id, self.quantity, False):
            await interaction.followup.send("Ошибка при списании оружия!", ephemeral=True)
            return
        
        result = execute_naval_strike(
            attacker_data, self.target_country, self.sea_zone,
            self.weapon_id, self.quantity, "trade_convoy"
        )
        
        if not result["success"]:
            await interaction.followup.send(result["message"], ephemeral=True)
            return
        
        save_states(states)
        
        strikes = load_strikes()
        strikes["strikes"].append({
            "id": len(strikes["strikes"]) + 1,
            "attacker": self.player_country,
            "target": self.target_country,
            "weapon": self.weapon_info["name"],
            "quantity": self.quantity,
            "target_type": "trade",
            "zone": self.sea_zone,
            "intercepted": result.get("intercepted_count", 0),
            "destroyed": result.get("destroyed_objects", 0),
            "economic_damage": result.get("economic_damage", 0),
            "timestamp": str(datetime.now())
        })
        save_strikes(strikes)
        
        embed = discord.Embed(
            title="РЕЗУЛЬТАТ УДАРА",
            description=result["message"],
            color=discord.Color.red() if result["destroyed_objects"] > 0 else discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction, button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(title="Пуск отменён", color=DARK_THEME_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== КЛАССЫ ДЛЯ РАСПРЕДЕЛЕНИЯ ОРУЖИЯ ====================

class WeaponDistributionModal(Modal):
    """Модальное окно для распределения оружия между целями"""
    
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, total_quantity: int, attacker_region: str,
                 target_region: str, region_data: Dict, selected_target_ids: List[str],
                 available_targets: List[Tuple[str, Dict]], is_decoy: bool = False):
        super().__init__(title="Распределение оружия")
        
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.total_quantity = total_quantity
        self.attacker_region = attacker_region
        self.target_region = target_region
        self.region_data = region_data
        self.selected_target_ids = selected_target_ids
        self.available_targets = {tid: info for tid, info in available_targets}
        self.is_decoy = is_decoy
        
        self.target_inputs = {}
        
        for i, target_id in enumerate(selected_target_ids):
            target_info = self.available_targets.get(target_id, {})
            if not target_info:
                continue
            
            max_for_target = count_targets_in_region(region_data, target_id)
            
            if max_for_target <= 0:
                continue
            
            suggested = max(1, total_quantity // len(selected_target_ids))
            suggested = min(suggested, max_for_target)
            
            input_field = TextInput(
                label=f"{target_info.get('name', target_id)} (макс: {max_for_target})",
                placeholder=f"Введите количество (рекомендуется: {suggested})",
                min_length=1,
                max_length=6,
                required=True,
                default=str(suggested)
            )
            self.add_item(input_field)
            self.target_inputs[target_id] = input_field
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            distribution = []
            total_allocated = 0
            
            for target_id, input_field in self.target_inputs.items():
                quantity = int(input_field.value)
                if quantity < 0:
                    await interaction.response.send_message("Количество не может быть отрицательным!", ephemeral=True)
                    return
                if quantity > 0:
                    distribution.append((target_id, quantity))
                    total_allocated += quantity
            
            if total_allocated > self.total_quantity:
                await interaction.response.send_message(
                    f"Общее количество ({total_allocated}) превышает доступное ({self.total_quantity})!",
                    ephemeral=True
                )
                return
            
            if total_allocated < self.total_quantity:
                remaining = self.total_quantity - total_allocated
                target_capacities = {}
                
                for target_id in self.target_inputs.keys():
                    max_for_target = count_targets_in_region(self.region_data, target_id)
                    already_allocated = next((q for tid, q in distribution if tid == target_id), 0)
                    target_capacities[target_id] = max_for_target - already_allocated
                
                sorted_targets = sorted(
                    [(tid, self.available_targets[tid].get("priority", 10)) for tid in self.target_inputs.keys()],
                    key=lambda x: x[1]
                )
                
                for target_id, priority in sorted_targets:
                    if remaining <= 0:
                        break
                    capacity = target_capacities.get(target_id, 0)
                    if capacity > 0:
                        add = min(remaining, capacity)
                        if add > 0:
                            found = False
                            for i, (tid, qty) in enumerate(distribution):
                                if tid == target_id:
                                    distribution[i] = (tid, qty + add)
                                    found = True
                                    break
                            if not found:
                                distribution.append((target_id, add))
                            remaining -= add
                
                if remaining > 0 and distribution:
                    target_ids = [tid for tid, _ in distribution]
                    for i in range(remaining):
                        target_id = target_ids[i % len(target_ids)]
                        for j, (tid, qty) in enumerate(distribution):
                            if tid == target_id:
                                distribution[j] = (tid, qty + 1)
                                break
                    remaining = 0
            
            if not distribution:
                await interaction.response.send_message("Вы не выбрали ни одной цели!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="ПОДТВЕРЖДЕНИЕ УДАРА",
                description=f"Операция против {self.target_country}" + (" (режим пустышек)" if self.is_decoy else ""),
                color=discord.Color.orange()
            )
            
            embed.add_field(name="Атакующий регион", value=self.attacker_region, inline=True)
            embed.add_field(name="Целевой регион", value=self.target_region, inline=True)
            embed.add_field(name="Расстояние", value=str(get_region_distance(
                self.player_country, self.attacker_region,
                self.target_country, self.target_region
            )), inline=True)
            embed.add_field(name="Оружие", value=f"{self.weapon_info['name']} x{self.total_quantity}" + (" (пустышки)" if self.is_decoy else ""), inline=True)
            
            distribution_text = ""
            for target_id, qty in distribution:
                target_info = self.available_targets.get(target_id, {})
                target_name = target_info.get("name", target_id)
                distribution_text += f"{target_name}: {qty} ед.\n"
            embed.add_field(name="Распределение оружия", value=distribution_text or "Нет", inline=False)
            
            embed.add_field(
                name="Предупреждение",
                value="Оружие будет списано из армии независимо от результата. Подтверждаете пуск?",
                inline=False
            )
            
            view = MultiTargetConfirmationView(
                self.user_id, self.player_country, self.target_country,
                self.weapon_id, self.weapon_info, self.total_quantity, self.attacker_region,
                self.target_region, distribution, self.is_decoy
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("Введите корректные числа!", ephemeral=True)


class MultipleTargetsView(View):
    """Выбор нескольких типов целей для удара"""
    
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, quantity: int, attacker_region: str,
                 target_region: str, region_data: Dict, available_targets: List[Tuple[str, Dict]],
                 is_decoy: bool = False):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.target_region = target_region
        self.region_data = region_data
        self.available_targets = available_targets
        self.is_decoy = is_decoy
        self.selected_targets = {}
        
        options = []
        valid_targets = []
        
        for target_id, target_info in available_targets:
            if not isinstance(target_info, dict):
                continue
            
            target_count = count_targets_in_region(region_data, target_id)
            
            if target_count <= 0:
                continue
            
            valid_targets.append((target_id, target_info))
            
            options.append(discord.SelectOption(
                label=f"{target_info.get('name', target_id)} (доступно: {target_count})",
                value=target_id,
                description=f"Приоритет: {target_info.get('priority', 10)}"
            ))
        
        if not options:
            self.target_select = Select(
                placeholder="Нет доступных целей в этом регионе!",
                options=[discord.SelectOption(label="Нет целей", value="none")],
                disabled=True,
                min_values=1,
                max_values=1
            )
        else:
            self.target_select = Select(
                placeholder="Выберите типы целей (можно несколько)...",
                options=options[:25],
                min_values=1,
                max_values=min(len(options), 25)
            )
        
        self.target_select.callback = self.on_targets_selected
        self.add_item(self.target_select)
        self.valid_available_targets = valid_targets
    
    async def on_targets_selected(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        selected_target_ids = self.target_select.values
        
        if not selected_target_ids or selected_target_ids[0] == "none":
            await interaction.response.send_message("Нет доступных целей для удара!", ephemeral=True)
            return
        
        modal = WeaponDistributionModal(
            self.user_id, self.player_country, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity, self.attacker_region,
            self.target_region, self.region_data, selected_target_ids, self.valid_available_targets,
            self.is_decoy
        )
        await interaction.response.send_modal(modal)


class MultiTargetConfirmationView(View):
    """Подтверждение удара по нескольким целям"""
    
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, quantity: int, attacker_region: str,
                 target_region: str, distribution: List[Tuple[str, int]], is_decoy: bool = False):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.target_region = target_region
        self.distribution = distribution
        self.is_decoy = is_decoy
        self.bot = None
    
    @discord.ui.button(label="ПОДТВЕРДИТЬ ПУСК", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        self.bot = interaction.client
        
        states = load_states()
        
        attacker_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                attacker_data = data
                break
        
        if not attacker_data:
            await interaction.followup.send("Ошибка загрузки данных игрока!", ephemeral=True)
            return
        
        if not consume_weapon(attacker_data, self.weapon_id, self.quantity, self.is_decoy):
            await interaction.followup.send("Ошибка при списании оружия! Возможно, у вас недостаточно оружия.", ephemeral=True)
            return
        
        result = None
        total_quantity = sum(q for _, q in self.distribution)
        
        try:
            result = execute_multi_target_strike(
                attacker_data, self.target_country, self.target_region,
                self.weapon_id, total_quantity, self.distribution,
                self.attacker_region, self.is_decoy
            )
            if not result or not result.get("success"):
                await interaction.followup.send(f"Ошибка удара: {result.get('message', 'Неизвестная ошибка') if result else 'Нет результата'}", ephemeral=True)
                return
        except Exception as e:
            await interaction.followup.send(f"Ошибка при ударе: {e}", ephemeral=True)
            import traceback
            traceback.print_exc()
            return
        
        if not result:
            await interaction.followup.send("Не удалось выполнить удар: нет результата!", ephemeral=True)
            return
        
        if not result.get("success", False):
            await interaction.followup.send(f"Не удалось выполнить удар: {result.get('message', 'Неизвестная ошибка')}", ephemeral=True)
            return
        
        try:
            save_states(states)
        except Exception as e:
            print(f"[ERROR] Ошибка при сохранении states: {e}")
        
        strikes = load_strikes()
        strike_record = {
            "id": len(strikes["strikes"]) + 1,
            "attacker": self.player_country,
            "attacker_region": self.attacker_region,
            "attacker_id": str(self.user_id),
            "target": self.target_country,
            "target_region": self.target_region,
            "weapon": self.weapon_info["name"],
            "weapon_id": self.weapon_id,
            "quantity": self.quantity,
            "is_decoy": self.is_decoy,
            "distribution": [(tid, qty) for tid, qty in self.distribution],
            "intercepted": result.get("intercepted_count", 0),
            "surviving": result.get("surviving", 0),
            "hits": result.get("hits", 0),
            "destroyed": result.get("destroyed_objects", 0),
            "casualties": result.get("civilian_casualties", 0),
            "destroyed_pvo": result.get("destroyed_pvo", {}),
            "fuel_losses": result.get("fuel_losses", {}),
            "distance": result.get("distance", 0),
            "timestamp": str(datetime.now())
        }
        strikes["strikes"].append(strike_record)
        
        try:
            save_strikes(strikes)
        except Exception as e:
            print(f"[ERROR] Ошибка при сохранении strikes: {e}")
        
        embed = discord.Embed(
            title="РЕЗУЛЬТАТ УДАРА" + (" (РЕЖИМ ПУСТЫШЕК)" if self.is_decoy else ""),
            description=result["message"],
            color=discord.Color.red() if result.get("hits", 0) > 0 else discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        if self.bot:
            try:
                await send_strike_log(self.bot, result)
            except Exception as e:
                print(f"[ERROR] Ошибка при отправке лога: {e}")
    
    @discord.ui.button(label="ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Пуск отменён",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_strike_menu',
    'STRIKE_WEAPONS',
    'TARGET_TYPES',
    'get_region_distance',
    'is_region_reachable',
    'load_distances',
    'get_all_country_regions',
    'get_country_economic_regions',
    'get_regions_in_economic_region',
    'get_player_regions',
    'send_strike_log',
    'STRIKE_LOG_CHANNEL_ID',
    'execute_strike',
    'execute_multi_target_strike',
    'execute_naval_strike',
    'execute_air_defense_strike',
    'calculate_surviving_weapons',
    'consume_weapon',
    'get_available_weapons',
    'get_fleets_in_zone',
    'get_trade_ships_in_zone'
]

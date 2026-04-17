# navy.py - Полная система флотов с ядерным оружием, авиацией, патрулированием и блокадой
# Версия с поддержкой новой структуры активов (total/ownership)

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from conflicts import are_countries_at_war

# Импорт из maritime_trade
try:
    from maritime_trade import (
        load_maritime_data, 
        CargoShip, 
        PORTS, 
        REGION_TO_PORT,
        get_ships_by_sea_region,
        get_ships_by_country,
        get_sea_zone_from_region,
        save_maritime_data
    )
    MARITIME_AVAILABLE = True
except ImportError:
    print("⚠️ Модуль maritime_trade не найден. Функции перехвата судов будут работать ограниченно.")
    MARITIME_AVAILABLE = False
    
    def load_maritime_data():
        return {"ships": []}
    
    def get_ships_by_sea_region(sea_region):
        return {}
    
    def get_ships_by_country(country):
        return []
    
    def get_sea_zone_from_region(region_name):
        return None
    
    def save_maritime_data(data):
        pass
    
    class CargoShip:
        @classmethod
        def from_dict(cls, data):
            return None

# Импорт функций для работы с активами
from infra_build import (
    load_infrastructure, save_infrastructure, get_all_regions_from_country,
    get_asset_total, get_asset_ownership, remove_asset_from_region, ASSET_FIELDS
)

NAVY_FILE = 'navy.json'
NAVAL_OPERATIONS_FILE = 'naval_operations.json'

try:
    from config import NAVY_LOG_CHANNEL_ID
except ImportError:
    NAVY_LOG_CHANNEL_ID = None


# Импорт TARGET_TYPES из strikes
try:
    from strikes import TARGET_TYPES
    TARGET_TYPES_AVAILABLE = True
except ImportError:
    TARGET_TYPES_AVAILABLE = False
    TARGET_TYPES = {
        "military_factories": {"name": "Военные заводы", "infra_fields": ["military_factories"], "priority": 1},
        "civilian_factories": {"name": "Гражданские фабрики", "infra_fields": ["civilian_factories"], "priority": 2},
        "shipyards": {"name": "Верфи", "infra_fields": ["shipyards"], "priority": 1},
        "refineries": {"name": "НПЗ", "infra_fields": ["refineries"], "priority": 1},
        "oil_depots": {"name": "Нефтебазы", "infra_fields": ["oil_depots"], "priority": 1},
        "radar_systems": {"name": "РЛС", "infra_fields": ["radar_systems"], "priority": 1},
        "short_range_air_defense": {"name": "ЗРК малой дальности", "infra_fields": ["short_range_air_defense"], "priority": 1},
        "long_range_air_defense": {"name": "ЗРК большой дальности", "infra_fields": ["long_range_air_defense"], "priority": 1},
        "zdprk": {"name": "ЗПРК", "infra_fields": ["zdprk"], "priority": 1},
        "zas": {"name": "ЗСУ", "infra_fields": ["zas"], "priority": 1},
        "thermal_power": {"name": "ТЭС", "infra_fields": ["thermal_power"], "priority": 1},
        "hydro_power": {"name": "ГЭС", "infra_fields": ["hydro_power"], "priority": 1},
        "solar_power": {"name": "СЭС", "infra_fields": ["solar_power"], "priority": 2},
        "wind_power": {"name": "ВЭС", "infra_fields": ["wind_power"], "priority": 2},
        "nuclear_power": {"name": "АЭС", "infra_fields": ["nuclear_power"], "priority": 1},
        "internet_infrastructure": {"name": "ЦОД", "infra_fields": ["internet_infrastructure"], "priority": 2},
        "office_centers": {"name": "Офисные центры", "infra_fields": ["office_centers"], "priority": 3}
    }


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """Рассчитывает расстояние между двумя точками на Земле в км"""
    R = 6371
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return round(R * c)


# ==================== МОРСКИЕ ЗОНЫ ====================

class SeaZone(Enum):
    NORTH_ATLANTIC = "Северная Атлантика"
    SOUTH_ATLANTIC = "Южная Атлантика"
    CARIBBEAN_SEA = "Карибское море"
    GULF_OF_MEXICO = "Мексиканский залив"
    NORTH_SEA = "Северное море"
    BALTIC_SEA = "Балтийское море"
    NORWEGIAN_SEA = "Норвежское море"
    ENGLISH_CHANNEL = "Ла-Манш"
    IRISH_SEA = "Ирландское море"
    WHITE_SEA = "Белое море"
    WESTERN_MEDITERRANEAN = "Западное Средиземноморье"
    EASTERN_MEDITERRANEAN = "Восточное Средиземноморье"
    BLACK_SEA = "Чёрное море"
    PERSIAN_GULF = "Персидский залив"
    RED_SEA = "Красное море"
    ARABIAN_SEA = "Аравийское море"
    SOUTH_CHINA_SEA = "Южно-Китайское море"
    EAST_CHINA_SEA = "Восточно-Китайское море"
    YELLOW_SEA = "Жёлтое море"
    SEA_OF_JAPAN = "Японское море"
    SEA_OF_OKHOTSK = "Охотское море"
    PACIFIC_OCEAN = "Тихий океан"
    BARENTS_SEA = "Баренцево море"
    ARCTIC_OCEAN = "Северный Ледовитый океан"
    BAY_OF_BISCAY = "Бискайский залив"
    ADRIATIC_SEA = "Адриатическое море"
    AEGEAN_SEA = "Эгейское море"
    SEA_OF_MARMARA = "Мраморное море"
    GULF_OF_ADEN = "Аденский залив"
    PHILIPPINE_SEA = "Филиппинское море"
    LABRADOR_SEA = "Море Лабрадор"
    GULF_OF_ALASKA = "Залив Аляска"
    CALIFORNIA_CURRENT = "Калифорнийское течение"
    BERING_SEA = "Берингово море"


# Координаты морских зон для расчёта расстояний
ZONE_COORDINATES = {
    SeaZone.PERSIAN_GULF: {"lat": 27.0, "lon": 52.0},
    SeaZone.BLACK_SEA: {"lat": 43.0, "lon": 35.0},
    SeaZone.BALTIC_SEA: {"lat": 58.0, "lon": 19.0},
    SeaZone.NORTH_SEA: {"lat": 56.0, "lon": 3.0},
    SeaZone.NORWEGIAN_SEA: {"lat": 66.0, "lon": 5.0},
    SeaZone.WESTERN_MEDITERRANEAN: {"lat": 40.0, "lon": 5.0},
    SeaZone.EASTERN_MEDITERRANEAN: {"lat": 34.0, "lon": 30.0},
    SeaZone.RED_SEA: {"lat": 20.0, "lon": 38.0},
    SeaZone.ARABIAN_SEA: {"lat": 18.0, "lon": 66.0},
    SeaZone.SOUTH_CHINA_SEA: {"lat": 12.0, "lon": 112.0},
    SeaZone.EAST_CHINA_SEA: {"lat": 28.0, "lon": 125.0},
    SeaZone.YELLOW_SEA: {"lat": 36.0, "lon": 123.0},
    SeaZone.SEA_OF_JAPAN: {"lat": 40.0, "lon": 135.0},
    SeaZone.SEA_OF_OKHOTSK: {"lat": 55.0, "lon": 150.0},
    SeaZone.PACIFIC_OCEAN: {"lat": 20.0, "lon": -150.0},
    SeaZone.NORTH_ATLANTIC: {"lat": 40.0, "lon": -40.0},
    SeaZone.SOUTH_ATLANTIC: {"lat": -20.0, "lon": -20.0},
    SeaZone.GULF_OF_MEXICO: {"lat": 25.0, "lon": -90.0},
    SeaZone.CARIBBEAN_SEA: {"lat": 16.0, "lon": -75.0},
    SeaZone.BARENTS_SEA: {"lat": 75.0, "lon": 40.0},
    SeaZone.ARCTIC_OCEAN: {"lat": 85.0, "lon": 0.0},
    SeaZone.ENGLISH_CHANNEL: {"lat": 50.0, "lon": -2.0},
    SeaZone.IRISH_SEA: {"lat": 53.5, "lon": -5.0},
    SeaZone.WHITE_SEA: {"lat": 66.0, "lon": 38.0},
    SeaZone.BAY_OF_BISCAY: {"lat": 45.0, "lon": -5.0},
    SeaZone.ADRIATIC_SEA: {"lat": 43.0, "lon": 16.0},
    SeaZone.AEGEAN_SEA: {"lat": 38.0, "lon": 25.0},
    SeaZone.SEA_OF_MARMARA: {"lat": 40.7, "lon": 28.0},
    SeaZone.GULF_OF_ADEN: {"lat": 12.0, "lon": 48.0},
    SeaZone.PHILIPPINE_SEA: {"lat": 18.0, "lon": 135.0},
    SeaZone.LABRADOR_SEA: {"lat": 60.0, "lon": -55.0},
    SeaZone.GULF_OF_ALASKA: {"lat": 57.0, "lon": -145.0},
    SeaZone.CALIFORNIA_CURRENT: {"lat": 32.0, "lon": -120.0},
    SeaZone.BERING_SEA: {"lat": 60.0, "lon": -170.0}
}


COUNTRY_SEA_ZONES = {
    "США": [SeaZone.NORTH_ATLANTIC, SeaZone.GULF_OF_MEXICO, SeaZone.PACIFIC_OCEAN],
    "Россия": [SeaZone.BALTIC_SEA, SeaZone.BARENTS_SEA, SeaZone.BLACK_SEA, 
               SeaZone.SEA_OF_JAPAN, SeaZone.SEA_OF_OKHOTSK],
    "Китай": [SeaZone.SOUTH_CHINA_SEA, SeaZone.EAST_CHINA_SEA, SeaZone.YELLOW_SEA],
    "Великобритания": [SeaZone.NORTH_SEA, SeaZone.ENGLISH_CHANNEL],
    "Франция": [SeaZone.ENGLISH_CHANNEL, SeaZone.WESTERN_MEDITERRANEAN],
    "Германия": [SeaZone.NORTH_SEA, SeaZone.BALTIC_SEA],
    "Япония": [SeaZone.SEA_OF_JAPAN, SeaZone.PACIFIC_OCEAN],
    "Украина": [SeaZone.BLACK_SEA],
    "Турция": [SeaZone.BLACK_SEA, SeaZone.EASTERN_MEDITERRANEAN],
    "Израиль": [SeaZone.EASTERN_MEDITERRANEAN],
    "Иран": [SeaZone.PERSIAN_GULF],
    "Норвегия": [SeaZone.NORTH_SEA, SeaZone.NORWEGIAN_SEA],
    "Швеция": [SeaZone.BALTIC_SEA],
    "Финляндия": [SeaZone.BALTIC_SEA],
    "Польша": [SeaZone.BALTIC_SEA],
    "Канада": [SeaZone.NORTH_ATLANTIC, SeaZone.PACIFIC_OCEAN],
    "Бразилия": [SeaZone.SOUTH_ATLANTIC],
    "Египет": [SeaZone.EASTERN_MEDITERRANEAN, SeaZone.RED_SEA],
    "КНДР": [SeaZone.YELLOW_SEA, SeaZone.SEA_OF_JAPAN],
    "Сирия": [SeaZone.EASTERN_MEDITERRANEAN],
    "Беларусь": [],
    "Швейцария": []
}


SEA_ZONE_DISTANCES = {
    (SeaZone.NORTH_ATLANTIC, SeaZone.NORTH_SEA): 1000,
    (SeaZone.NORTH_ATLANTIC, SeaZone.BALTIC_SEA): 1500,
    (SeaZone.NORTH_SEA, SeaZone.BALTIC_SEA): 500,
    (SeaZone.NORTH_SEA, SeaZone.NORWEGIAN_SEA): 500,
    (SeaZone.BALTIC_SEA, SeaZone.NORWEGIAN_SEA): 800,
    (SeaZone.WESTERN_MEDITERRANEAN, SeaZone.EASTERN_MEDITERRANEAN): 800,
    (SeaZone.EASTERN_MEDITERRANEAN, SeaZone.BLACK_SEA): 500,
    (SeaZone.EASTERN_MEDITERRANEAN, SeaZone.RED_SEA): 400,
    (SeaZone.RED_SEA, SeaZone.PERSIAN_GULF): 1000,
    (SeaZone.SOUTH_CHINA_SEA, SeaZone.EAST_CHINA_SEA): 800,
    (SeaZone.EAST_CHINA_SEA, SeaZone.YELLOW_SEA): 400,
    (SeaZone.YELLOW_SEA, SeaZone.SEA_OF_JAPAN): 400,
    (SeaZone.SEA_OF_JAPAN, SeaZone.SEA_OF_OKHOTSK): 800,
    (SeaZone.NORWEGIAN_SEA, SeaZone.BARENTS_SEA): 500,
}


def get_transit_time(from_zone: SeaZone, to_zone: SeaZone) -> float:
    if from_zone == to_zone:
        return 0
    distance = SEA_ZONE_DISTANCES.get((from_zone, to_zone))
    if not distance:
        distance = SEA_ZONE_DISTANCES.get((to_zone, from_zone))
    if not distance:
        return 6
    hours = distance * 1.852 / 37
    return max(2, min(8, round(hours, 1)))


# ==================== ХАРАКТЕРИСТИКИ КОРАБЛЕЙ ====================

SHIP_TYPES = {
    "aircraft_carriers": {"name": "Авианосец", "intercept_power": 0, "artillery": 60, "air_power": 80, "patrol_power": 40},
    "cruisers": {"name": "Крейсер", "intercept_power": 85, "artillery": 85, "air_power": 30, "patrol_power": 70},
    "destroyers": {"name": "Эсминец", "intercept_power": 75, "artillery": 65, "air_power": 20, "patrol_power": 65},
    "frigates": {"name": "Фрегат", "intercept_power": 65, "artillery": 45, "air_power": 15, "patrol_power": 55},
    "corvettes": {"name": "Корвет", "intercept_power": 55, "artillery": 35, "air_power": 10, "patrol_power": 45},
    "submarines": {"name": "Подлодка", "intercept_power": 0, "artillery": 75, "air_power": 0, "patrol_power": 25},
    "boats": {"name": "Катер", "intercept_power": 35, "artillery": 20, "air_power": 5, "patrol_power": 30}
}


# ==================== ТИПЫ ВООРУЖЕНИЯ ДЛЯ ФЛОТА ====================

FLEET_WEAPONS = {
    "strategic_nuclear": {
        "name": "Стратегические ядерные ракеты",
        "description": "Межконтинентальные баллистические ракеты с ядерными боеголовками.",
        "range": 8000,
        "from_ships": ["submarines"],
        "type": "nuclear",
        "nuclear": True
    },
    "tactical_nuclear": {
        "name": "Тактические ядерные ракеты",
        "description": "Ядерные ракеты малой дальности для ударов по военным объектам.",
        "range": 2000,
        "from_ships": ["submarines", "cruisers", "destroyers"],
        "type": "nuclear",
        "nuclear": True
    },
    "hypersonic_missiles": {
        "name": "Гиперзвуковые ракеты",
        "description": "Новейшее оружие. Почти невозможно перехватить.",
        "range": 2500,
        "from_ships": ["cruisers", "destroyers", "submarines"],
        "type": "conventional",
        "reusable": False
    },
    "cruise_missiles": {
        "name": "Крылатые ракеты",
        "description": "Дозвуковые ракеты, летят на малой высоте. Высокая точность.",
        "range": 2000,
        "from_ships": ["cruisers", "destroyers", "frigates", "corvettes", "submarines"],
        "type": "conventional",
        "reusable": False
    },
    "ballistic_missiles": {
        "name": "Баллистические ракеты",
        "description": "Сверхзвуковые ракеты. Очень сложно перехватить.",
        "range": 3000,
        "from_ships": ["cruisers", "destroyers", "submarines"],
        "type": "conventional",
        "reusable": False
    },
    "fighters": {
        "name": "Истребители",
        "description": "Манёвренные самолёты для ударов по наземным целям.",
        "range": 1200,
        "from_ships": ["aircraft_carriers"],
        "type": "air",
        "reusable": True
    },
    "bombers": {
        "name": "Бомбардировщики",
        "description": "Тяжёлые самолёты для стратегических бомбардировок.",
        "range": 1500,
        "from_ships": ["aircraft_carriers"],
        "type": "air",
        "reusable": True
    },
    "drones": {
        "name": "Ударные БПЛА",
        "description": "Беспилотники средней дальности. Многоразовые.",
        "range": 800,
        "from_ships": ["aircraft_carriers", "cruisers", "destroyers"],
        "type": "air",
        "reusable": True
    },
    "kamikaze_uav": {
        "name": "Дроны-камикадзе",
        "description": "Барражирующие боеприпасы. Дешёвые, одноразовые.",
        "range": 1000,
        "from_ships": ["aircraft_carriers", "cruisers", "destroyers", "frigates", "boats"],
        "type": "air",
        "reusable": False
    }
}


def get_fleet_available_weapons(fleet: 'Fleet') -> List[Tuple[str, int]]:
    """Возвращает список доступного оружия для флота"""
    available = []
    
    for weapon_id, weapon_info in FLEET_WEAPONS.items():
        total_quantity = 0
        
        for ship_type in weapon_info["from_ships"]:
            count = fleet.ships.get(ship_type, 0)
            if count == 0:
                continue
            
            if weapon_id == "strategic_nuclear":
                strategic_subs = max(1, count // 3)
                total_quantity += strategic_subs * random.randint(12, 16)
                
            elif weapon_id == "tactical_nuclear":
                if ship_type == "submarines":
                    total_quantity += count * random.randint(4, 8)
                elif ship_type in ["cruisers", "destroyers"]:
                    total_quantity += count * random.randint(2, 4)
                    
            elif weapon_id == "hypersonic_missiles":
                if ship_type in ["cruisers", "destroyers", "submarines"]:
                    total_quantity += count * random.randint(2, 5)
                    
            elif weapon_id == "cruise_missiles":
                if ship_type == "submarines":
                    total_quantity += count * random.randint(8, 12)
                elif ship_type in ["cruisers", "destroyers"]:
                    total_quantity += count * random.randint(8, 16)
                elif ship_type in ["frigates", "corvettes"]:
                    total_quantity += count * random.randint(4, 8)
                    
            elif weapon_id == "ballistic_missiles":
                if ship_type == "submarines":
                    total_quantity += count * random.randint(4, 8)
                elif ship_type in ["cruisers", "destroyers"]:
                    total_quantity += count * random.randint(2, 4)
                    
            elif weapon_id in ["fighters", "bombers"]:
                if ship_type == "aircraft_carriers":
                    if weapon_id == "fighters":
                        total_quantity += count * 40
                    elif weapon_id == "bombers":
                        total_quantity += count * 12
                        
            elif weapon_id == "drones":
                if ship_type == "aircraft_carriers":
                    total_quantity += count * 30
                elif ship_type in ["cruisers", "destroyers"]:
                    total_quantity += count * 8
                elif ship_type in ["frigates", "corvettes"]:
                    total_quantity += count * 4
                    
            elif weapon_id == "kamikaze_uav":
                if ship_type == "aircraft_carriers":
                    total_quantity += count * 100
                elif ship_type in ["cruisers", "destroyers"]:
                    total_quantity += count * 30
                elif ship_type in ["frigates", "corvettes", "boats"]:
                    total_quantity += count * 15
        
        if total_quantity > 0:
            available.append((weapon_id, total_quantity))
    
    return available


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ИНФРАСТРУКТУРОЙ ====================

def get_region_coordinates(country: str, region: str) -> Optional[Dict]:
    """Получает координаты региона из файла region_coordinates.py"""
    try:
        from region_coordinates import get_region_coordinates as _get_coords
        return _get_coords(country, region)
    except ImportError:
        return None


def get_region_data(country: str, region_name: str) -> Optional[Dict]:
    """Получает данные региона из инфраструктуры"""
    infra = load_infrastructure()
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == country:
            regions = get_all_regions_from_country(infra, cid)
            if region_name in regions:
                return regions[region_name]
    return None


def get_country_economic_regions(country: str) -> Dict:
    """Получает экономические районы страны"""
    infra = load_infrastructure()
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == country:
            return data.get("economic_regions", {})
    return {}


def get_region_from_economic_region(country: str, econ_region: str) -> Dict:
    """Получает регионы из экономического района"""
    infra = load_infrastructure()
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == country:
            econ_data = data.get("economic_regions", {}).get(econ_region, {})
            return econ_data.get("regions", {})
    return {}


# ==================== ФУНКЦИИ ДЛЯ БЛОКАДЫ ====================

def load_naval_operations():
    """Загружает данные о блокадах"""
    try:
        with open(NAVAL_OPERATIONS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"blockades": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"blockades": {}}


def save_naval_operations(data):
    """Сохраняет данные о блокадах"""
    with open(NAVAL_OPERATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_ship_blocked(ship_country: str, zone: SeaZone, blockading_country: str = None) -> Tuple[bool, Optional[str]]:
    """Проверяет, заблокирован ли корабль в данной зоне"""
    ops = load_naval_operations()
    blockades = ops.get("blockades", {})
    
    zone_key = zone.value
    
    if zone_key not in blockades:
        return False, None
    
    for blockader, blockaded_countries in blockades[zone_key].items():
        if blockader == blockading_country:
            continue
        if ship_country in blockaded_countries:
            return True, blockader
    
    return False, None


def add_blockade(blockader_country: str, zone: SeaZone, target_countries: List[str]) -> Tuple[bool, str]:
    """Устанавливает блокаду на торговые суда указанных стран в зоне"""
    if not target_countries:
        return False, "Не указаны страны для блокады"
    
    ops = load_naval_operations()
    
    if "blockades" not in ops:
        ops["blockades"] = {}
    
    zone_key = zone.value
    
    if zone_key not in ops["blockades"]:
        ops["blockades"][zone_key] = {}
    
    if blockader_country not in ops["blockades"][zone_key]:
        ops["blockades"][zone_key][blockader_country] = []
    
    new_countries = [c for c in target_countries if c not in ops["blockades"][zone_key][blockader_country]]
    
    if not new_countries:
        return False, "Все указанные страны уже под блокадой"
    
    ops["blockades"][zone_key][blockader_country].extend(new_countries)
    ops["blockades"][zone_key][blockader_country] = list(set(ops["blockades"][zone_key][blockader_country]))
    
    ops["last_update"] = str(datetime.now())
    save_naval_operations(ops)
    
    return True, f"Установлена блокада на {', '.join(new_countries)} в зоне {zone.value}"


def remove_blockade(blockader_country: str, zone: SeaZone, target_countries: List[str] = None) -> Tuple[bool, str]:
    """Снимает блокаду"""
    ops = load_naval_operations()
    
    zone_key = zone.value
    
    if zone_key not in ops.get("blockades", {}):
        return False, f"Нет активных блокад в зоне {zone.value}"
    
    if blockader_country not in ops["blockades"][zone_key]:
        return False, f"Ваша страна не устанавливала блокаду в этой зоне"
    
    if target_countries is None:
        del ops["blockades"][zone_key][blockader_country]
        if not ops["blockades"][zone_key]:
            del ops["blockades"][zone_key]
        
        save_naval_operations(ops)
        return True, f"Снята блокада со всех стран в зоне {zone.value}"
    
    existing = ops["blockades"][zone_key][blockader_country]
    removed = [c for c in target_countries if c in existing]
    
    if not removed:
        return False, "Указанные страны не находятся под блокадой"
    
    for c in removed:
        existing.remove(c)
    
    if not existing:
        del ops["blockades"][zone_key][blockader_country]
        if not ops["blockades"][zone_key]:
            del ops["blockades"][zone_key]
    
    save_naval_operations(ops)
    return True, f"Снята блокада с {', '.join(removed)} в зоне {zone.value}"


def get_active_blockades(zone: SeaZone = None) -> Dict:
    """Возвращает активные блокады"""
    ops = load_naval_operations()
    blockades = ops.get("blockades", {})
    
    if zone:
        zone_key = zone.value
        return {zone_key: blockades.get(zone_key, {})} if zone_key in blockades else {}
    
    return blockades


def apply_patrol_effects(zone: SeaZone) -> int:
    """Применяет эффекты патрулирования (повышает шанс обнаружения вражеских судов)"""
    navy_data = load_navy_data()
    patrol_power = 0
    
    for fleet_data in navy_data["fleets"]:
        fleet = Fleet.from_dict(fleet_data)
        if fleet.current_zone == zone and fleet.operation == "patrol":
            patrol_power += fleet.get_patrol_power()
    
    return patrol_power


# ==================== ВЫПОЛНЕНИЕ УДАРОВ ====================

def calculate_attack_distance(fleet: 'Fleet', target_country: str, target_region: str) -> int:
    """Рассчитывает расстояние от флота до цели"""
    fleet_coords = ZONE_COORDINATES.get(fleet.current_zone, {"lat": 40.0, "lon": 0.0})
    
    target_coords = get_region_coordinates(target_country, target_region)
    
    if target_coords:
        return haversine_distance(
            fleet_coords["lat"], fleet_coords["lon"],
            target_coords["lat"], target_coords["lon"]
        )
    
    try:
        from strikes import get_region_distance as _grd
        return _grd(fleet.country, f"Флот {fleet.name}", target_country, target_region)
    except ImportError:
        return 9999


def execute_multi_target_strike(fleet: 'Fleet', target_country: str, target_region: str,
                                 weapon_id: str, total_quantity: int, distribution: List[Tuple[str, int]]) -> Dict:
    """Выполняет удар с распределением оружия между целями"""
    
    weapon = FLEET_WEAPONS.get(weapon_id, {})
    distance = calculate_attack_distance(fleet, target_country, target_region)
    
    if distance > weapon.get("range", 0):
        return {
            "success": False,
            "message": f"Цель вне зоны досягаемости! Расстояние: {distance} км, дальность оружия: {weapon.get('range', 0)} км"
        }
    
    region_data = get_region_data(target_country, target_region)
    if not region_data:
        return {"success": False, "message": "Регион не найден"}
    
    if weapon.get("nuclear", False):
        return execute_nuclear_strike(fleet, target_country, target_region, weapon_id, total_quantity, distance, region_data)
    
    if weapon.get("reusable", False) and weapon["type"] == "air":
        return execute_air_strike_with_distribution(fleet, target_country, target_region, weapon_id, distribution, distance, region_data)
    
    return execute_missile_strike_with_distribution(fleet, target_country, target_region, weapon_id, distribution, distance, region_data)


def execute_nuclear_strike(fleet: 'Fleet', target_country: str, target_region: str,
                           weapon_id: str, quantity: int, distance: int, region_data: Dict) -> Dict:
    """Выполняет ядерный удар по региону (уничтожает всё)"""
    
    weapon = FLEET_WEAPONS.get(weapon_id, {})
    
    intercept_chance = 0.02
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
            "civilian_casualties": 0,
            "distance": distance,
            "attacker_fleet": fleet.name,
            "attacker_zone": fleet.current_zone.value,
            "weapon_name": weapon.get("name", weapon_id),
            "quantity": quantity,
            "is_nuclear": True,
            "target_country": target_country,
            "target_region": target_region,
            "message": f"ЯДЕРНЫЙ УДАР с флота {fleet.name}\n"
                      f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                      f"Расстояние: {distance} км\n"
                      f"Запущено: {quantity}\n"
                      f"Перехвачено: {intercepted} (2%)\n"
                      f"Все {quantity} ядерных ракет перехвачены системой ПРО"
        }
    
    hits = surviving
    
    original_population = region_data.get("population", 0)
    
    destroyed = {}
    total_destroyed = 0
    
    field_names = {
        "military_factories": "Военные заводы",
        "civilian_factories": "Гражданские фабрики",
        "shipyards": "Верфи",
        "refineries": "НПЗ",
        "oil_depots": "Нефтебазы",
        "radar_systems": "РЛС",
        "short_range_air_defense": "ЗРК малой дальности",
        "long_range_air_defense": "ЗРК большой дальности",
        "zdprk": "ЗПРК",
        "zas": "ЗСУ",
        "thermal_power": "ТЭС",
        "hydro_power": "ГЭС",
        "solar_power": "СЭС",
        "wind_power": "ВЭС",
        "nuclear_power": "АЭС",
        "internet_infrastructure": "ЦОД",
        "office_centers": "Офисные центры",
        "roads_level": "Дорожная сеть",
        "agriculture_level": "Сельскохозяйственные угодья",
        "airports": "Аэропорты",
        "ports": "Морские порты",
        "bridges": "Мосты",
        "railways": "Железные дороги",
        "communication_towers": "Вышки сотовой связи",
        "water_treatment": "Водоочистные сооружения",
        "hospitals": "Больницы",
        "schools": "Школы",
        "housing": "Жилые кварталы",
        "shopping_centers": "Торговые центры",
        "cultural_centers": "Культурные центры"
    }
    
    # Для активов используем get_asset_total
    for field in ASSET_FIELDS:
        if field in region_data:
            current_total = get_asset_total(region_data, field)
            if current_total > 0:
                destruction_rate = random.uniform(0.7, 0.95)
                destroyed_amount = int(current_total * destruction_rate)
                if destroyed_amount > 0:
                    # Уничтожаем у всех владельцев пропорционально
                    ownership = get_asset_ownership(region_data, field)
                    for owner, count in ownership.items():
                        owner_destroyed = int(count * destruction_rate)
                        if owner_destroyed > 0:
                            remove_asset_from_region(region_data, field, owner, owner_destroyed)
                            destroyed[field] = destroyed.get(field, 0) + owner_destroyed
                            total_destroyed += owner_destroyed
    
    # Для не-активов (обычные поля)
    for field, value in region_data.items():
        if field in ASSET_FIELDS:
            continue  # Уже обработали
        if isinstance(value, (int, float)) and field not in ["population", "radiation"]:
            if field in field_names:
                destruction_rate = random.uniform(0.7, 0.95)
            else:
                destruction_rate = random.uniform(0.5, 0.8)
            
            destroyed_amount = int(value * destruction_rate)
            if destroyed_amount > 0:
                destroyed[field] = destroyed_amount
                region_data[field] = max(0, value - destroyed_amount)
                total_destroyed += destroyed_amount
    
    casualties = int(original_population * random.uniform(0.6, 0.9))
    region_data["population"] = max(0, original_population - casualties)
    
    region_data["radiation"] = {
        "level": "critical",
        "weapon": weapon.get("name", weapon_id),
        "date": datetime.now().isoformat(),
        "fallout_radius_km": 500,
        "years": 10
    }
    
    infra = load_infrastructure()
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == target_country:
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                if target_region in econ_data.get("regions", {}):
                    econ_data["regions"][target_region] = region_data
                    break
            break
    save_infrastructure(infra)
    
    states = load_states()
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == target_country:
            data["state"]["happiness"] = max(0, data["state"].get("happiness", 50) - 50)
            data["state"]["stability"] = max(0, data["state"].get("stability", 50) - 40)
            data["state"]["trust"] = max(0, data["state"].get("trust", 50) - 30)
            break
    save_states(states)
    
    try:
        from conflicts import record_strike
        record_strike(fleet.country, target_country, total_destroyed)
    except ImportError:
        pass
    
    destroyed_text = ""
    for field, amount in destroyed.items():
        if amount > 0:
            name = field_names.get(field, field.replace('_', ' ').title())
            destroyed_text += f"   • {name}: -{amount}\n"
    
    if not destroyed_text:
        destroyed_text = "   • Инфраструктура полностью уничтожена\n"
    
    message = (
        f"ЯДЕРНЫЙ УДАР с флота {fleet.name}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Расстояние: {distance} км\n"
        f"Запущено: {quantity}\n"
        f"Перехвачено: {intercepted} (2%)\n"
        f"Попаданий: {hits}\n"
        f"Уничтожено объектов: {total_destroyed}\n"
        f"{destroyed_text}"
        f"Потери населения: {format_number(casualties)} чел.\n"
        f"Падение счастья: -50%\n"
        f"Падение стабильности: -40%\n"
        f"Радиоактивное заражение: критическое (500 км, 10 лет)"
    )
    
    return {
        "success": True,
        "intercepted": intercepted > 0,
        "intercepted_count": intercepted,
        "surviving": surviving,
        "hits": hits,
        "destroyed_objects": total_destroyed,
        "destroyed_details": destroyed,
        "civilian_casualties": casualties,
        "distance": distance,
        "attacker_fleet": fleet.name,
        "attacker_zone": fleet.current_zone.value,
        "weapon_name": weapon.get("name", weapon_id),
        "quantity": quantity,
        "is_nuclear": True,
        "target_country": target_country,
        "target_region": target_region,
        "message": message
    }


def execute_missile_strike_with_distribution(fleet: 'Fleet', target_country: str, target_region: str,
                                              weapon_id: str, distribution: List[Tuple[str, int]], 
                                              distance: int, region_data: Dict) -> Dict:
    """Выполняет ракетный удар с распределением по целям (1 попадание = 1 объект)"""
    
    weapon = FLEET_WEAPONS.get(weapon_id, {})
    total_quantity = sum(q for _, q in distribution)
    
    states = load_states()
    target_data = None
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == target_country:
            target_data = data
            break
    
    defense_strength = 0
    if target_data:
        army = target_data.get("army", {})
        ground = army.get("ground", {})
        defense_strength += ground.get("short_range_air_defense", 0) * 3
        defense_strength += ground.get("long_range_air_defense", 0) * 5
    
    if weapon_id == "hypersonic_missiles":
        base_difficulty = 0.95
    elif weapon_id == "ballistic_missiles":
        base_difficulty = 0.7
    else:
        base_difficulty = 0.4
    
    if defense_strength > 0:
        base_chance = 1.0 - (1.0 / (1.0 + defense_strength / 30.0))
    else:
        base_chance = 0.0
    
    intercept_chance = base_chance * (1.0 - base_difficulty)
    
    if total_quantity > 1:
        saturation_factor = 1.0 / math.log10(total_quantity + 9) * 2.0
        saturation_factor = max(0.3, min(1.0, saturation_factor))
        intercept_chance = intercept_chance * saturation_factor
    
    intercept_chance = max(0.01, min(0.98, intercept_chance))
    
    results = {}
    total_intercepted = 0
    total_surviving = 0
    
    for target_id, quantity in distribution:
        intercepted = 0
        for _ in range(quantity):
            if random.random() < intercept_chance:
                intercepted += 1
        surviving = quantity - intercepted
        results[target_id] = {
            "launched": quantity,
            "intercepted": intercepted,
            "surviving": surviving
        }
        total_intercepted += intercepted
        total_surviving += surviving
    
    if total_surviving == 0:
        return {
            "success": True,
            "intercepted": True,
            "intercepted_count": total_quantity,
            "surviving": 0,
            "hits": 0,
            "destroyed_objects": 0,
            "civilian_casualties": 0,
            "distance": distance,
            "attacker_fleet": fleet.name,
            "attacker_zone": fleet.current_zone.value,
            "weapon_name": weapon.get("name", weapon_id),
            "quantity": total_quantity,
            "is_nuclear": False,
            "message": (
                f"РАКЕТНЫЙ УДАР с флота {fleet.name}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Расстояние: {distance} км\n"
                f"Запущено: {total_quantity}\n"
                f"Перехвачено: {total_intercepted} ({intercept_chance*100:.1f}%)\n"
                f"Все ракеты перехвачены ПВО противника"
            )
        }
    
    if weapon_id == "hypersonic_missiles":
        accuracy = 0.85
    elif weapon_id == "ballistic_missiles":
        accuracy = 0.75
    else:
        accuracy = 0.9
    
    destroyed = {}
    total_destroyed = 0
    total_casualties = 0
    
    field_names = {
        "military_factories": "Военные заводы",
        "civilian_factories": "Гражданские фабрики",
        "shipyards": "Верфи",
        "refineries": "НПЗ",
        "oil_depots": "Нефтебазы",
        "radar_systems": "РЛС",
        "short_range_air_defense": "ЗРК малой дальности",
        "long_range_air_defense": "ЗРК большой дальности",
        "zdprk": "ЗПРК",
        "zas": "ЗСУ",
        "thermal_power": "ТЭС",
        "hydro_power": "ГЭС",
        "solar_power": "СЭС",
        "wind_power": "ВЭС",
        "nuclear_power": "АЭС",
        "internet_infrastructure": "ЦОД",
        "office_centers": "Офисные центры"
    }
    
    for target_id, stats in results.items():
        if stats["surviving"] == 0:
            continue
        
        hits = int(stats["surviving"] * accuracy)
        if hits == 0:
            continue
        
        target_info = TARGET_TYPES.get(target_id, {})
        target_fields = target_info.get("infra_fields", list(field_names.keys()))
        
        for field in target_fields:
            if field in region_data:
                current_total = get_asset_total(region_data, field)
                if current_total > 0:
                    destroy = min(current_total, hits)
                    if destroy > 0:
                        # Выбираем случайного владельца для уничтожения
                        ownership = get_asset_ownership(region_data, field)
                        if ownership:
                            owners = list(ownership.keys())
                            weights = [ownership[o] for o in owners]
                            selected_owner = random.choices(owners, weights=weights, k=1)[0]
                            remove_asset_from_region(region_data, field, selected_owner, destroy)
                        
                        destroyed[field] = destroyed.get(field, 0) + destroy
                        total_destroyed += destroy
                        hits -= destroy
                        if hits <= 0:
                            break
    
    if total_destroyed > 0:
        total_casualties = random.randint(1, min(10 * total_destroyed, int(region_data.get("population", 0) * 0.05)))
        region_data["population"] = max(0, region_data.get("population", 0) - total_casualties)
    
    infra = load_infrastructure()
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == target_country:
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                if target_region in econ_data.get("regions", {}):
                    econ_data["regions"][target_region] = region_data
                    break
            break
    save_infrastructure(infra)
    
    destroyed_text = ""
    for field, amount in destroyed.items():
        if amount > 0:
            name = field_names.get(field, field.replace('_', ' ').title())
            destroyed_text += f"   • {name}: -{amount}\n"
    
    if not destroyed_text:
        destroyed_text = "   • Существенных разрушений нет\n"
    
    return {
        "success": True,
        "intercepted": total_intercepted > 0,
        "intercepted_count": total_intercepted,
        "surviving": total_surviving,
        "hits": total_destroyed,
        "destroyed_objects": total_destroyed,
        "destroyed_details": destroyed,
        "civilian_casualties": total_casualties,
        "distance": distance,
        "attacker_fleet": fleet.name,
        "attacker_zone": fleet.current_zone.value,
        "weapon_name": weapon.get("name", weapon_id),
        "quantity": total_quantity,
        "is_nuclear": False,
        "message": (
            f"РАКЕТНЫЙ УДАР с флота {fleet.name}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Расстояние: {distance} км\n"
            f"Запущено: {total_quantity}\n"
            f"Перехвачено: {total_intercepted} ({intercept_chance*100:.1f}%)\n"
            f"Достигло цели: {total_surviving}\n"
            f"Попаданий: {total_destroyed}\n"
            f"Уничтожено объектов: {total_destroyed}\n"
            f"{destroyed_text}"
            f"Потери населения: {format_number(total_casualties)} чел."
        )
    }


def execute_air_strike_with_distribution(fleet: 'Fleet', target_country: str, target_region: str,
                                          weapon_id: str, distribution: List[Tuple[str, int]], 
                                          distance: int, region_data: Dict) -> Dict:
    """Выполняет авиационный удар с распределением по целям"""
    
    weapon = FLEET_WEAPONS.get(weapon_id, {})
    total_quantity = sum(q for _, q in distribution)
    
    states = load_states()
    target_data = None
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == target_country:
            target_data = data
            break
    
    air_defense = 0
    if target_data:
        army = target_data.get("army", {})
        ground = army.get("ground", {})
        air_defense += ground.get("short_range_air_defense", 0) * 3
        air_defense += ground.get("long_range_air_defense", 0) * 5
        air_defense += ground.get("zdprk", 0) * 2
        air_defense += ground.get("zas", 0) * 1
        air_defense += ground.get("fighters", 0) * 2
    
    if weapon_id == "fighters":
        base_intercept = 0.15
    elif weapon_id == "bombers":
        base_intercept = 0.2
    elif weapon_id == "drones":
        base_intercept = 0.35
    else:
        base_intercept = 0.4
    
    if air_defense > 0:
        intercept_chance = min(base_intercept, air_defense / (air_defense + total_quantity * 15))
    else:
        intercept_chance = base_intercept * 0.3
    
    results = {}
    total_intercepted = 0
    total_surviving = 0
    
    for target_id, quantity in distribution:
        intercepted = 0
        for _ in range(quantity):
            if random.random() < intercept_chance:
                intercepted += 1
        surviving = quantity - intercepted
        results[target_id] = {
            "launched": quantity,
            "intercepted": intercepted,
            "surviving": surviving
        }
        total_intercepted += intercepted
        total_surviving += surviving
    
    if total_surviving == 0:
        return {
            "success": True,
            "intercepted": True,
            "intercepted_count": total_quantity,
            "surviving": 0,
            "destroyed_objects": 0,
            "civilian_casualties": 0,
            "distance": distance,
            "attacker_fleet": fleet.name,
            "attacker_zone": fleet.current_zone.value,
            "weapon_name": weapon.get("name", weapon_id),
            "quantity": total_quantity,
            "is_nuclear": False,
            "message": (
                f"АВИАУДАР с флота {fleet.name}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Расстояние: {distance} км\n"
                f"Запущено: {total_quantity} самолётов\n"
                f"Сбито: {total_intercepted} ({intercept_chance*100:.1f}%)\n"
                f"Все самолёты сбиты ПВО противника"
            )
        }
    
    if weapon_id == "fighters":
        damage_per_unit = random.uniform(0.4, 0.7)
    elif weapon_id == "bombers":
        damage_per_unit = random.uniform(1.0, 1.5)
    elif weapon_id == "drones":
        damage_per_unit = random.uniform(0.6, 1.0)
    else:
        damage_per_unit = random.uniform(0.3, 0.6)
    
    destroyed = {}
    total_destroyed = 0
    total_casualties = 0
    
    field_names = {
        "military_factories": "Военные заводы",
        "civilian_factories": "Гражданские фабрики",
        "shipyards": "Верфи",
        "refineries": "НПЗ",
        "oil_depots": "Нефтебазы",
        "radar_systems": "РЛС",
        "short_range_air_defense": "ЗРК малой дальности",
        "long_range_air_defense": "ЗРК большой дальности",
        "zdprk": "ЗПРК",
        "zas": "ЗСУ",
        "airports": "Аэропорты",
        "ports": "Морские порты",
        "bridges": "Мосты",
        "railways": "Железные дороги",
        "roads_level": "Дорожная сеть",
        "communication_towers": "Вышки сотовой связи"
    }
    
    for target_id, stats in results.items():
        if stats["surviving"] == 0:
            continue
        
        hits = int(stats["surviving"] * damage_per_unit)
        if hits == 0:
            continue
        
        target_info = TARGET_TYPES.get(target_id, {})
        target_fields = target_info.get("infra_fields", list(field_names.keys()))
        
        for field in target_fields:
            if field in region_data:
                current_total = get_asset_total(region_data, field)
                if current_total > 0:
                    destroy = min(current_total, hits)
                    if destroy > 0:
                        # Выбираем случайного владельца для уничтожения
                        ownership = get_asset_ownership(region_data, field)
                        if ownership:
                            owners = list(ownership.keys())
                            weights = [ownership[o] for o in owners]
                            selected_owner = random.choices(owners, weights=weights, k=1)[0]
                            remove_asset_from_region(region_data, field, selected_owner, destroy)
                        
                        destroyed[field] = destroyed.get(field, 0) + destroy
                        total_destroyed += destroy
                        hits -= destroy
                        if hits <= 0:
                            break
    
    if total_destroyed > 0:
        total_casualties = random.randint(1, min(5 * total_destroyed, int(region_data.get("population", 0) * 0.03)))
        region_data["population"] = max(0, region_data.get("population", 0) - total_casualties)
    
    infra = load_infrastructure()
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == target_country:
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                if target_region in econ_data.get("regions", {}):
                    econ_data["regions"][target_region] = region_data
                    break
            break
    save_infrastructure(infra)
    
    destroyed_text = ""
    for field, amount in destroyed.items():
        if amount > 0:
            name = field_names.get(field, field.replace('_', ' ').title())
            destroyed_text += f"   • {name}: -{amount}\n"
    
    if not destroyed_text:
        destroyed_text = "   • Существенных разрушений нет\n"
    
    return {
        "success": True,
        "intercepted": total_intercepted > 0,
        "intercepted_count": total_intercepted,
        "surviving": total_surviving,
        "destroyed_objects": total_destroyed,
        "destroyed_details": destroyed,
        "civilian_casualties": total_casualties,
        "distance": distance,
        "attacker_fleet": fleet.name,
        "attacker_zone": fleet.current_zone.value,
        "weapon_name": weapon.get("name", weapon_id),
        "quantity": total_quantity,
        "is_nuclear": False,
        "message": (
            f"АВИАУДАР с флота {fleet.name}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Расстояние: {distance} км\n"
            f"Запущено: {total_quantity} самолётов\n"
            f"Сбито: {total_intercepted} ({intercept_chance*100:.1f}%)\n"
            f"Достигло цели: {total_surviving}\n"
            f"Уничтожено объектов: {total_destroyed}\n"
            f"{destroyed_text}"
            f"Потери населения: {format_number(total_casualties)} чел.\n"
            f"Самолёты вернулись на авианосцы"
        )
    }


# ==================== ПЕРЕХВАТ СУДОВ С УЧЁТОМ БЛОКАДЫ ====================

def get_ships_in_zone(zone: SeaZone, country_filter: str = None) -> List[Dict]:
    """Получает корабли в зоне (без учёта блокады)"""
    if not MARITIME_AVAILABLE:
        return []
    
    data = load_maritime_data()
    ships = []
    
    ports_in_zone = [port for port, port_data in PORTS.items() if port_data["sea_region"] == zone]
    
    for ship_data in data.get("ships", []):
        ship = CargoShip.from_dict(ship_data)
        
        in_zone = False
        if ship.current_region:
            if ship.current_region in ports_in_zone:
                in_zone = True
            elif ship.current_region in REGION_TO_PORT:
                mapped_port = REGION_TO_PORT[ship.current_region]
                if mapped_port in ports_in_zone:
                    in_zone = True
        
        if not in_zone and ship.destination_region:
            if ship.destination_region in ports_in_zone:
                in_zone = True
            elif ship.destination_region in REGION_TO_PORT:
                mapped_port = REGION_TO_PORT[ship.destination_region]
                if mapped_port in ports_in_zone:
                    in_zone = True
        
        if in_zone:
            if country_filter is None or ship.current_country == country_filter:
                ships.append(ship_data)
    
    return ships


def get_ships_in_zone_with_blockade(zone: SeaZone, blockader_country: str = None) -> List[Dict]:
    """Получает корабли в зоне с учётом блокады (блокированные корабли не возвращаются)"""
    if not MARITIME_AVAILABLE:
        return []
    
    data = load_maritime_data()
    ships = []
    
    ports_in_zone = [port for port, port_data in PORTS.items() if port_data["sea_region"] == zone]
    
    for ship_data in data.get("ships", []):
        ship = CargoShip.from_dict(ship_data)
        
        in_zone = False
        if ship.current_region:
            if ship.current_region in ports_in_zone:
                in_zone = True
            elif ship.current_region in REGION_TO_PORT:
                mapped_port = REGION_TO_PORT[ship.current_region]
                if mapped_port in ports_in_zone:
                    in_zone = True
        
        if not in_zone and ship.destination_region:
            if ship.destination_region in ports_in_zone:
                in_zone = True
            elif ship.destination_region in REGION_TO_PORT:
                mapped_port = REGION_TO_PORT[ship.destination_region]
                if mapped_port in ports_in_zone:
                    in_zone = True
        
        if in_zone:
            # Проверяем блокаду
            blocked, blockader = is_ship_blocked(ship.current_country, zone, blockader_country)
            if not blocked:
                ships.append(ship_data)
    
    return ships


def get_defender_fleet_in_zone(zone: SeaZone, defender_country: str) -> Optional['Fleet']:
    """Получает флот защитника в зоне"""
    navy_data = load_navy_data()
    for fleet_data in navy_data["fleets"]:
        fleet = Fleet.from_dict(fleet_data)
        if fleet.country == defender_country and fleet.current_zone == zone:
            if fleet.get_total_ships() > 0:
                return fleet
    return None


def calculate_intercept_chance(attacker_power: int, defender_power: int) -> float:
    """Рассчитывает шанс перехвата"""
    if defender_power == 0:
        return 0.95
    chance = attacker_power / (attacker_power + defender_power)
    return max(0.1, min(0.95, chance))


def execute_ship_interception(fleet: 'Fleet', target_ship: Dict) -> Dict:
    """Выполняет перехват торгового судна"""
    if not MARITIME_AVAILABLE:
        return {"success": False, "message": "Модуль морской торговли недоступен"}
    
    data = load_maritime_data()
    target_country = target_ship.get("current_country")
    
    defender = get_defender_fleet_in_zone(fleet.current_zone, target_country)
    chance = calculate_intercept_chance(fleet.get_intercept_power(), defender.get_intercept_power() if defender else 0)
    
    if random.random() > chance:
        return {
            "success": False,
            "message": "Торговое судно ускользнуло от перехвата",
            "intercept_chance": chance,
            "defender_present": defender is not None
        }
    
    cargo_value = target_ship.get("cargo_value", 0)
    cargo = target_ship.get("cargo", {})
    
    data["ships"] = [s for s in data["ships"] if s["id"] != target_ship["id"]]
    save_maritime_data(data)
    
    try:
        from conflicts import record_strike
        record_strike(fleet.country, target_country, 1)
    except ImportError:
        pass
    
    return {
        "success": True,
        "cargo_value": cargo_value,
        "cargo": cargo,
        "intercept_chance": chance,
        "defender_present": defender is not None,
        "defender_fleet": defender.name if defender else None,
        "message": f"Торговое судно уничтожено! Потеряно груза на сумму ${cargo_value:,.0f}"
    }


# ==================== ИНИЦИАЛИЗАЦИЯ ====================

def load_navy_data():
    try:
        with open(NAVY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"fleets": [], "last_update": str(datetime.now())}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"fleets": [], "last_update": str(datetime.now())}


def save_navy_data(data):
    with open(NAVY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def initialize_fleets():
    navy_data = load_navy_data()
    if navy_data.get("fleets"):
        print(f"Флоты уже инициализированы ({len(navy_data['fleets'])} флотов)")
        return
    fleets = []
    fleet_id = 1
    for country, fleets_list in REAL_FLEETS.items():
        for info in fleets_list:
            fleet = Fleet(f"fleet_{fleet_id:03d}", country, info["name"], info["home_zone"])
            fleet.ships = info["ships"]
            fleets.append(fleet.to_dict())
            fleet_id += 1
    navy_data["fleets"] = fleets
    navy_data["initialized_at"] = str(datetime.now())
    save_navy_data(navy_data)
    print(f"Инициализировано {len(fleets)} флотов")


def update_fleets_positions():
    navy_data = load_navy_data()
    updated = 0
    for i, fd in enumerate(navy_data["fleets"]):
        fleet = Fleet.from_dict(fd)
        if fleet.update_position():
            navy_data["fleets"][i] = fleet.to_dict()
            updated += 1
    if updated:
        save_navy_data(navy_data)
    return updated


async def navy_update_loop(bot_instance):
    await bot_instance.wait_until_ready()
    while not bot_instance.is_closed():
        try:
            updated = update_fleets_positions()
            if updated:
                print(f"Обновлены позиции {updated} флотов")
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Ошибка в navy_update_loop: {e}")
            await asyncio.sleep(60)


# ==================== РЕАЛЬНЫЕ ФЛОТЫ ====================

REAL_FLEETS = {
    "США": [
        {"name": "2-й флот (Атлантика)", "home_zone": SeaZone.NORTH_ATLANTIC,
         "ships": {"aircraft_carriers": 2, "cruisers": 4, "destroyers": 12, "submarines": 8, "frigates": 6}},
        {"name": "3-й флот (Тихий океан)", "home_zone": SeaZone.PACIFIC_OCEAN,
         "ships": {"aircraft_carriers": 3, "cruisers": 5, "destroyers": 15, "submarines": 10, "frigates": 8}},
        {"name": "5-й флот (Персидский залив)", "home_zone": SeaZone.PERSIAN_GULF,
         "ships": {"aircraft_carriers": 1, "destroyers": 8, "submarines": 4}}
    ],
    "Россия": [
        {"name": "Северный флот", "home_zone": SeaZone.BARENTS_SEA,
         "ships": {"aircraft_carriers": 1, "cruisers": 2, "destroyers": 5, "submarines": 15, "frigates": 8}},
        {"name": "Тихоокеанский флот", "home_zone": SeaZone.SEA_OF_JAPAN,
         "ships": {"cruisers": 2, "destroyers": 6, "submarines": 12, "frigates": 8}},
        {"name": "Черноморский флот", "home_zone": SeaZone.BLACK_SEA,
         "ships": {"cruisers": 1, "destroyers": 3, "frigates": 6, "submarines": 7, "boats": 10}},
        {"name": "Балтийский флот", "home_zone": SeaZone.BALTIC_SEA,
         "ships": {"destroyers": 2, "frigates": 4, "corvettes": 6, "boats": 8}}
    ],
    "Китай": [
        {"name": "Северный флот", "home_zone": SeaZone.YELLOW_SEA,
         "ships": {"aircraft_carriers": 1, "destroyers": 8, "submarines": 12, "frigates": 10}},
        {"name": "Восточный флот", "home_zone": SeaZone.EAST_CHINA_SEA,
         "ships": {"aircraft_carriers": 1, "destroyers": 10, "submarines": 15, "frigates": 12}},
        {"name": "Южный флот", "home_zone": SeaZone.SOUTH_CHINA_SEA,
         "ships": {"aircraft_carriers": 1, "destroyers": 12, "submarines": 18, "frigates": 15}}
    ],
    "Великобритания": [
        {"name": "Домашний флот", "home_zone": SeaZone.NORTH_SEA,
         "ships": {"aircraft_carriers": 2, "destroyers": 6, "submarines": 7, "frigates": 8}}
    ],
    "Франция": [
        {"name": "Средиземноморский флот", "home_zone": SeaZone.WESTERN_MEDITERRANEAN,
         "ships": {"aircraft_carriers": 1, "destroyers": 3, "frigates": 6, "submarines": 5}}
    ],
    "Германия": [
        {"name": "1-я флотилия (Северное море)", "home_zone": SeaZone.NORTH_SEA,
         "ships": {"frigates": 6, "corvettes": 5, "submarines": 4, "boats": 8}},
        {"name": "2-я флотилия (Балтийское море)", "home_zone": SeaZone.BALTIC_SEA,
         "ships": {"frigates": 4, "corvettes": 3, "submarines": 2, "boats": 6}}
    ],
    "Япония": [
        {"name": "Морские силы самообороны", "home_zone": SeaZone.SEA_OF_JAPAN,
         "ships": {"destroyers": 8, "submarines": 6, "frigates": 10}}
    ],
    "Турция": [
        {"name": "Военно-морские силы", "home_zone": SeaZone.BLACK_SEA,
         "ships": {"frigates": 8, "corvettes": 6, "submarines": 5, "boats": 12}}
    ],
    "Иран": [
        {"name": "Военно-морские силы", "home_zone": SeaZone.PERSIAN_GULF,
         "ships": {"frigates": 4, "corvettes": 6, "submarines": 3, "boats": 20}}
    ],
    "Израиль": [
        {"name": "Военно-морские силы", "home_zone": SeaZone.EASTERN_MEDITERRANEAN,
         "ships": {"corvettes": 4, "submarines": 5, "boats": 8}}
    ],
    "Украина": [
        {"name": "Военно-морские силы", "home_zone": SeaZone.BLACK_SEA,
         "ships": {"frigates": 1, "corvettes": 2, "boats": 10}}
    ],
    "Норвегия": [
        {"name": "Королевский флот", "home_zone": SeaZone.NORWEGIAN_SEA,
         "ships": {"frigates": 4, "submarines": 6, "corvettes": 6, "boats": 12}}
    ],
    "Швеция": [
        {"name": "Королевский флот", "home_zone": SeaZone.BALTIC_SEA,
         "ships": {"corvettes": 7, "submarines": 5, "boats": 12}}
    ],
    "Польша": [
        {"name": "Военно-морские силы", "home_zone": SeaZone.BALTIC_SEA,
         "ships": {"frigates": 2, "corvettes": 3, "submarines": 3, "boats": 5}}
    ],
    "Канада": [
        {"name": "Королевский флот", "home_zone": SeaZone.NORTH_ATLANTIC,
         "ships": {"frigates": 6, "submarines": 4}}
    ],
    "Бразилия": [
        {"name": "Бразильский флот", "home_zone": SeaZone.SOUTH_ATLANTIC,
         "ships": {"aircraft_carriers": 1, "frigates": 6, "corvettes": 5, "submarines": 4}}
    ],
    "Египет": [
        {"name": "Военно-морские силы", "home_zone": SeaZone.EASTERN_MEDITERRANEAN,
         "ships": {"frigates": 4, "corvettes": 4, "submarines": 4}}
    ],
    "КНДР": [
        {"name": "Военно-морские силы", "home_zone": SeaZone.SEA_OF_JAPAN,
         "ships": {"frigates": 3, "corvettes": 5, "submarines": 8, "boats": 30}}
    ],
    "Сирия": [
        {"name": "Военно-морские силы", "home_zone": SeaZone.EASTERN_MEDITERRANEAN,
         "ships": {"corvettes": 2, "boats": 8}}
    ]
}


# ==================== КЛАСС ФЛОТА С ОПЕРАЦИЯМИ ====================

class Fleet:
    def __init__(self, fleet_id: str, country: str, name: str, home_zone: SeaZone):
        self.id = fleet_id
        self.country = country
        self.name = name
        self.home_zone = home_zone
        self.current_zone = home_zone
        self.ships = {}
        self.status = "docked"
        self.operation = "docked"  # docked, patrol, blockade
        self.blockade_targets = []  # страны, против которых установлена блокада
        self.destination_zone = None
        self.departure_time = None
        self.arrival_time = None
    
    def to_dict(self):
        return {
            "id": self.id, "country": self.country, "name": self.name,
            "home_zone": self.home_zone.value, "current_zone": self.current_zone.value,
            "ships": self.ships, "status": self.status, "operation": self.operation,
            "blockade_targets": self.blockade_targets,
            "destination_zone": self.destination_zone.value if self.destination_zone else None,
            "departure_time": self.departure_time, "arrival_time": self.arrival_time
        }
    
    @classmethod
    def from_dict(cls, data):
        fleet = cls(data["id"], data["country"], data["name"], SeaZone(data["home_zone"]))
        fleet.current_zone = SeaZone(data["current_zone"])
        fleet.ships = data["ships"]
        fleet.status = data["status"]
        fleet.operation = data.get("operation", "docked")
        fleet.blockade_targets = data.get("blockade_targets", [])
        fleet.destination_zone = SeaZone(data["destination_zone"]) if data.get("destination_zone") else None
        fleet.departure_time = data.get("departure_time")
        fleet.arrival_time = data.get("arrival_time")
        return fleet
    
    def get_total_ships(self) -> int:
        return sum(self.ships.values())
    
    def get_intercept_power(self) -> int:
        total = 0
        for ship_type, count in self.ships.items():
            if ship_type in SHIP_TYPES and ship_type not in ["aircraft_carriers", "submarines"]:
                total += SHIP_TYPES[ship_type]["intercept_power"] * count
        return total
    
    def get_patrol_power(self) -> int:
        total = 0
        for ship_type, count in self.ships.items():
            if ship_type in SHIP_TYPES:
                total += SHIP_TYPES[ship_type].get("patrol_power", SHIP_TYPES[ship_type]["intercept_power"] // 2) * count
        return total
    
    def get_artillery_power(self) -> int:
        total = 0
        for ship_type, count in self.ships.items():
            if ship_type in SHIP_TYPES:
                total += SHIP_TYPES[ship_type]["artillery"] * count
        return total
    
    def get_air_power(self) -> int:
        total = 0
        for ship_type, count in self.ships.items():
            if ship_type in SHIP_TYPES:
                total += SHIP_TYPES[ship_type]["air_power"] * count
        return total
    
    def get_status_text(self) -> str:
        if self.operation == "patrol":
            return f"Патрулирует в {self.current_zone.value} (мощь патруля: {self.get_patrol_power()})"
        elif self.operation == "blockade":
            targets = ", ".join(self.blockade_targets) if self.blockade_targets else "все страны"
            return f"Блокирует {targets} в {self.current_zone.value}"
        elif self.status == "docked":
            return f"На базе в {self.current_zone.value}"
        elif self.status == "sailing":
            if self.arrival_time:
                remaining = datetime.fromisoformat(self.arrival_time) - datetime.now()
                remaining_hours = remaining.total_seconds() / 3600
                return f"В пути в {self.destination_zone.value} (прибытие через {remaining_hours:.1f} ч)"
            return f"В пути в {self.destination_zone.value}"
        return f"Статус: {self.status}"
    
    def set_destination(self, zone: SeaZone):
        if zone == self.current_zone:
            return False, "Флот уже в этой зоне"
        hours = get_transit_time(self.current_zone, zone)
        self.destination_zone = zone
        self.departure_time = datetime.now().isoformat()
        self.arrival_time = (datetime.now() + timedelta(hours=hours)).isoformat()
        self.status = "sailing"
        self.operation = "docked"  # При перемещении операция сбрасывается
        self.blockade_targets = []
        return True, f"Флот направляется в {zone.value}, прибытие через {hours} ч"
    
    def start_patrol(self) -> Tuple[bool, str]:
        if self.status != "docked":
            return False, "Флот должен быть на базе для начала патрулирования"
        self.operation = "patrol"
        self.status = "docked"
        return True, f"Флот начал патрулирование в {self.current_zone.value}"
    
    def start_blockade(self, target_countries: List[str]) -> Tuple[bool, str]:
        if self.status != "docked":
            return False, "Флот должен быть на базе для установки блокады"
        if not target_countries:
            return False, "Не указаны страны для блокады"
        
        self.operation = "blockade"
        self.blockade_targets = target_countries
        self.status = "docked"
        
        # Сохраняем блокаду в глобальные данные
        success, msg = add_blockade(self.country, self.current_zone, target_countries)
        if not success:
            self.operation = "docked"
            self.blockade_targets = []
            return False, msg
        
        return True, f"Флот установил блокаду на {', '.join(target_countries)} в {self.current_zone.value}"
    
    def stop_operation(self) -> Tuple[bool, str]:
        if self.operation == "blockade":
            success, msg = remove_blockade(self.country, self.current_zone)
            if not success:
                return False, msg
        self.operation = "docked"
        self.blockade_targets = []
        return True, f"Операция остановлена, флот вернулся в режим ожидания"
    
    def update_position(self):
        if self.status != "sailing" or not self.arrival_time:
            return False
        if datetime.now() >= datetime.fromisoformat(self.arrival_time):
            self.current_zone = self.destination_zone
            self.destination_zone = None
            self.departure_time = None
            self.arrival_time = None
            self.status = "docked"
            return True
        return False


# ==================== МЕНЮ ====================

async def show_navy_menu(interaction_or_ctx, user_id: int):
    states = load_states()
    country_name = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            country_name = data["state"]["statename"]
            break
    
    if not country_name:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message("У вас нет государства", ephemeral=True)
        else:
            await interaction_or_ctx.send("У вас нет государства")
        return
    
    navy_data = load_navy_data()
    fleets = []
    for fd in navy_data["fleets"]:
        if fd["country"] == country_name:
            fleets.append(Fleet.from_dict(fd))
    
    embed = discord.Embed(
        title=f"Военно-морские силы: {country_name}",
        color=DARK_THEME_COLOR
    )
    embed.add_field(name="Флотов", value=str(len(fleets)), inline=True)
    embed.add_field(name="Кораблей", value=str(sum(f.get_total_ships() for f in fleets)), inline=True)
    
    if fleets:
        text = ""
        for f in fleets:
            text += f"**{f.name}**: {f.get_total_ships()} кораблей\n{f.get_status_text()}\n"
        embed.add_field(name="Флоты", value=text, inline=False)
    else:
        embed.add_field(name="Флоты", value="У вашей страны нет военно-морского флота", inline=False)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
        msg = await interaction_or_ctx.original_response()
    else:
        msg = await interaction_or_ctx.send(embed=embed, ephemeral=True)
    
    if fleets:
        select = FleetSelect(user_id, fleets)
        view = View(timeout=120)
        view.add_item(select)
        await msg.edit(view=view)


class FleetSelect(Select):
    def __init__(self, user_id, fleets):
        self.user_id = user_id
        options = []
        for f in fleets[:25]:
            options.append(discord.SelectOption(
                label=f.name,
                value=f.id,
                description=f"{f.current_zone.value} | {f.get_total_ships()} кораблей | {f.get_status_text()[:50]}"
            ))
        super().__init__(placeholder="Выберите флот...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        navy_data = load_navy_data()
        fleet = None
        for fd in navy_data["fleets"]:
            if fd["id"] == self.values[0]:
                fleet = Fleet.from_dict(fd)
                break
        
        if not fleet:
            await interaction.response.send_message("Флот не найден", ephemeral=True)
            return
        
        embed = discord.Embed(title=fleet.name, color=DARK_THEME_COLOR)
        
        ships_text = ""
        for ship_type, count in fleet.ships.items():
            if ship_type in SHIP_TYPES and count > 0:
                ships_text += f"{SHIP_TYPES[ship_type]['name']}: {count}\n"
        if not ships_text:
            ships_text = "Нет кораблей"
        embed.add_field(name="Состав", value=ships_text, inline=False)
        
        embed.add_field(name="Зона", value=fleet.current_zone.value, inline=True)
        embed.add_field(name="Статус", value=fleet.get_status_text(), inline=True)
        embed.add_field(name="Мощь перехвата", value=str(fleet.get_intercept_power()), inline=True)
        embed.add_field(name="Мощь патруля", value=str(fleet.get_patrol_power()), inline=True)
        embed.add_field(name="Огневая мощь", value=str(fleet.get_artillery_power()), inline=True)
        embed.add_field(name="Авиационная мощь", value=str(fleet.get_air_power()), inline=True)
        
        subs = fleet.ships.get("submarines", 0)
        if subs > 0:
            embed.add_field(name="Ядерный потенциал", value=f"Подводных лодок: {subs}", inline=True)
        
        view = FleetActionView(interaction.user.id, fleet)
        await interaction.response.edit_message(embed=embed, view=view)


class FleetActionView(View):
    def __init__(self, user_id, fleet):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.fleet = fleet
    
    async def show_fleet_menu(self, interaction, fleet):
        embed = discord.Embed(title=fleet.name, color=DARK_THEME_COLOR)
        
        ships_text = ""
        for ship_type, count in fleet.ships.items():
            if ship_type in SHIP_TYPES and count > 0:
                ships_text += f"{SHIP_TYPES[ship_type]['name']}: {count}\n"
        if not ships_text:
            ships_text = "Нет кораблей"
        embed.add_field(name="Состав", value=ships_text, inline=False)
        
        embed.add_field(name="Зона", value=fleet.current_zone.value, inline=True)
        embed.add_field(name="Статус", value=fleet.get_status_text(), inline=True)
        embed.add_field(name="Мощь перехвата", value=str(fleet.get_intercept_power()), inline=True)
        embed.add_field(name="Мощь патруля", value=str(fleet.get_patrol_power()), inline=True)
        embed.add_field(name="Огневая мощь", value=str(fleet.get_artillery_power()), inline=True)
        embed.add_field(name="Авиационная мощь", value=str(fleet.get_air_power()), inline=True)
        
        subs = fleet.ships.get("submarines", 0)
        if subs > 0:
            embed.add_field(name="Ядерный потенциал", value=f"Подводных лодок: {subs}", inline=True)
        
        view = FleetActionView(self.user_id, fleet)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Переместить", style=discord.ButtonStyle.primary)
    async def move_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        if self.fleet.status != "docked":
            await interaction.response.send_message("Флот уже в пути", ephemeral=True)
            return
        
        zones = [z for z in SeaZone if z != self.fleet.current_zone]
        options = [discord.SelectOption(label=z.value, value=z.value) for z in zones[:25]]
        select = Select(placeholder="Выберите зону...", options=options)
        
        async def on_select(interact):
            if interact.user.id != self.user_id:
                await interact.response.send_message("Это не ваше меню", ephemeral=True)
                return
            zone = SeaZone(select.values[0])
            ok, msg = self.fleet.set_destination(zone)
            if ok:
                navy_data = load_navy_data()
                for i, fd in enumerate(navy_data["fleets"]):
                    if fd["id"] == self.fleet.id:
                        navy_data["fleets"][i] = self.fleet.to_dict()
                        break
                save_navy_data(navy_data)
                embed = discord.Embed(title="Флот отправлен", description=msg, color=DARK_THEME_COLOR)
                await interact.response.edit_message(embed=embed, view=None)
            else:
                await interact.response.send_message(msg, ephemeral=True)
        
        select.callback = on_select
        view = View(timeout=60)
        view.add_item(select)
        await interaction.response.edit_message(embed=discord.Embed(title="Выбор зоны", color=DARK_THEME_COLOR), view=view)
    
    @discord.ui.button(label="Патруль", style=discord.ButtonStyle.primary)
    async def patrol_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        if self.fleet.status != "docked":
            await interaction.response.send_message("Флот должен быть на базе", ephemeral=True)
            return
        
        ok, msg = self.fleet.start_patrol()
        if ok:
            navy_data = load_navy_data()
            for i, fd in enumerate(navy_data["fleets"]):
                if fd["id"] == self.fleet.id:
                    navy_data["fleets"][i] = self.fleet.to_dict()
                    break
            save_navy_data(navy_data)
            embed = discord.Embed(title="Патрулирование начато", description=msg, color=DARK_THEME_COLOR)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="Блокада", style=discord.ButtonStyle.danger)
    async def blockade_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        if self.fleet.status != "docked":
            await interaction.response.send_message("Флот должен быть на базе", ephemeral=True)
            return
        
        view = BlockadeCountrySelectView(self.user_id, self.fleet)
        embed = discord.Embed(
            title="Выбор стран для блокады",
            description="Выберите страны, торговые суда которых будут блокироваться в этой зоне.\n"
                       "Можно выбрать несколько стран.\n\n"
                       "⚠️ Внимание: блокада может привести к международным конфликтам!",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Остановить операцию", style=discord.ButtonStyle.secondary)
    async def stop_op_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        if self.fleet.operation == "docked":
            await interaction.response.send_message("Флот не выполняет никаких операций", ephemeral=True)
            return
        
        ok, msg = self.fleet.stop_operation()
        if ok:
            navy_data = load_navy_data()
            for i, fd in enumerate(navy_data["fleets"]):
                if fd["id"] == self.fleet.id:
                    navy_data["fleets"][i] = self.fleet.to_dict()
                    break
            save_navy_data(navy_data)
            embed = discord.Embed(title="Операция остановлена", description=msg, color=DARK_THEME_COLOR)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="Перехват судов", style=discord.ButtonStyle.danger)
    async def intercept_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        if self.fleet.status != "docked":
            await interaction.response.send_message("Флот должен быть на базе", ephemeral=True)
            return
        
        enemies = []
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") != str(self.user_id):
                enemy = data["state"]["statename"]
                if are_countries_at_war(self.fleet.country, enemy):
                    enemies.append(enemy)
        
        if not enemies:
            await interaction.response.send_message("Нет стран, с которыми вы воюете", ephemeral=True)
            return
        
        # Используем функцию с учётом блокады
        ships = get_ships_in_zone_with_blockade(self.fleet.current_zone, self.fleet.country)
        if not ships:
            await interaction.response.send_message("В этой зоне нет доступных торговых судов", ephemeral=True)
            return
        
        enemy_ships = [s for s in ships if s.get("current_country") in enemies]
        if not enemy_ships:
            await interaction.response.send_message("В этой зоне нет вражеских торговых судов", ephemeral=True)
            return
        
        options = [discord.SelectOption(label=f"{s['name']} ({s['current_country']})", value=s["id"]) for s in enemy_ships[:25]]
        select = Select(placeholder="Выберите судно для перехвата...", options=options)
        
        async def on_select(interact):
            if interact.user.id != self.user_id:
                await interact.response.send_message("Это не ваше меню", ephemeral=True)
                return
            ship_id = select.values[0]
            target_ship = next(s for s in enemy_ships if s["id"] == ship_id)
            result = execute_ship_interception(self.fleet, target_ship)
            
            if result["success"]:
                embed = discord.Embed(title="Судно уничтожено", description=result["message"], color=discord.Color.red())
                if result.get("defender_present"):
                    embed.add_field(name="ПВО", value=f"Флот {result['defender_fleet']} пытался защитить", inline=False)
            else:
                embed = discord.Embed(title="Перехват не удался", description=result["message"], color=discord.Color.orange())
            
            await interact.response.edit_message(embed=embed, view=None)
        
        select.callback = on_select
        view = View(timeout=60)
        view.add_item(select)
        await interaction.response.edit_message(embed=discord.Embed(title="Выбор цели", color=DARK_THEME_COLOR), view=view)
    
    @discord.ui.button(label="Удар по берегу", style=discord.ButtonStyle.danger)
    async def strike_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        if self.fleet.status != "docked":
            await interaction.response.send_message("Флот должен быть на базе", ephemeral=True)
            return
        
        enemies = []
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") != str(self.user_id):
                enemy = data["state"]["statename"]
                if are_countries_at_war(self.fleet.country, enemy):
                    enemies.append(enemy)
        
        if not enemies:
            await interaction.response.send_message("Нет стран, с которыми вы воюете", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор страны для удара",
            description=f"Флот: {self.fleet.name} в {self.fleet.current_zone.value}",
            color=DARK_THEME_COLOR
        )
        
        view = NavalCountrySelectView(self.user_id, self.fleet, enemies, self)
        await interaction.response.edit_message(embed=embed, view=view)


class BlockadeCountrySelectView(View):
    def __init__(self, user_id, fleet):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.fleet = fleet
        
        # Получаем список всех стран-игроков
        states = load_states()
        self.all_countries = []
        for data in states["players"].values():
            country = data["state"]["statename"]
            if country != fleet.country:
                self.all_countries.append(country)
        
        # Создаём Select для выбора стран
        options = []
        for country in self.all_countries[:25]:
            options.append(discord.SelectOption(label=country, value=country))
        
        self.country_select = Select(
            placeholder="Выберите страны для блокады (можно несколько)",
            options=options,
            min_values=1,
            max_values=len(options),
            custom_id="blockade_country_select"
        )
        self.country_select.callback = self.on_country_select
        self.add_item(self.country_select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.on_back
        self.add_item(back_button)
    
    async def on_country_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        selected_countries = interaction.data["values"]
        
        # Подтверждение
        embed = discord.Embed(
            title="Подтверждение блокады",
            description=f"Вы уверены, что хотите установить блокаду на {', '.join(selected_countries)} в зоне {self.fleet.current_zone.value}?",
            color=discord.Color.orange()
        )
        embed.add_field(name="⚠️ Предупреждение", value="Блокада может привести к международным конфликтам и ответным мерам!", inline=False)
        
        view = BlockadeConfirmView(self.user_id, self.fleet, selected_countries)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        await show_fleet_menu_back(interaction, self.user_id, self.fleet)


class BlockadeConfirmView(View):
    def __init__(self, user_id, fleet, target_countries):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.fleet = fleet
        self.target_countries = target_countries
    
    @discord.ui.button(label="Подтвердить", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        ok, msg = self.fleet.start_blockade(self.target_countries)
        if ok:
            navy_data = load_navy_data()
            for i, fd in enumerate(navy_data["fleets"]):
                if fd["id"] == self.fleet.id:
                    navy_data["fleets"][i] = self.fleet.to_dict()
                    break
            save_navy_data(navy_data)
            embed = discord.Embed(title="Блокада установлена", description=msg, color=discord.Color.red())
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        view = BlockadeCountrySelectView(self.user_id, self.fleet)
        embed = discord.Embed(
            title="Выбор стран для блокады",
            description="Выберите страны, торговые суда которых будут блокироваться в этой зоне.",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=view)


async def show_fleet_menu_back(interaction, user_id, fleet):
    embed = discord.Embed(title=fleet.name, color=DARK_THEME_COLOR)
    
    ships_text = ""
    for ship_type, count in fleet.ships.items():
        if ship_type in SHIP_TYPES and count > 0:
            ships_text += f"{SHIP_TYPES[ship_type]['name']}: {count}\n"
    if not ships_text:
        ships_text = "Нет кораблей"
    embed.add_field(name="Состав", value=ships_text, inline=False)
    
    embed.add_field(name="Зона", value=fleet.current_zone.value, inline=True)
    embed.add_field(name="Статус", value=fleet.get_status_text(), inline=True)
    embed.add_field(name="Мощь перехвата", value=str(fleet.get_intercept_power()), inline=True)
    embed.add_field(name="Мощь патруля", value=str(fleet.get_patrol_power()), inline=True)
    embed.add_field(name="Огневая мощь", value=str(fleet.get_artillery_power()), inline=True)
    embed.add_field(name="Авиационная мощь", value=str(fleet.get_air_power()), inline=True)
    
    subs = fleet.ships.get("submarines", 0)
    if subs > 0:
        embed.add_field(name="Ядерный потенциал", value=f"Подводных лодок: {subs}", inline=True)
    
    view = FleetActionView(user_id, fleet)
    await interaction.response.edit_message(embed=embed, view=view)


class NavalCountrySelectView(View):
    def __init__(self, user_id, fleet, enemies, parent_view):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.fleet = fleet
        self.enemies = enemies
        self.parent_view = parent_view
        
        select = Select(
            placeholder="Выберите страну...",
            options=[discord.SelectOption(label=e, value=e) for e in enemies[:25]]
        )
        select.callback = self.on_country_select
        self.add_item(select)
        
        back_button = Button(label="Назад к меню флота", style=discord.ButtonStyle.secondary)
        back_button.callback = self.on_back
        self.add_item(back_button)
    
    async def on_country_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        target_country = interaction.data["values"][0]
        
        economic_regions = get_country_economic_regions(target_country)
        if not economic_regions:
            await interaction.response.send_message(f"У {target_country} нет экономических районов", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор экономического района",
            description=f"Цель: {target_country}",
            color=DARK_THEME_COLOR
        )
        
        view = NavalEconRegionSelectView(self.user_id, self.fleet, target_country, economic_regions, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        await self.parent_view.show_fleet_menu(interaction, self.fleet)


class NavalEconRegionSelectView(View):
    def __init__(self, user_id, fleet, target_country, economic_regions, parent_view):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.fleet = fleet
        self.target_country = target_country
        self.economic_regions = economic_regions
        self.parent_view = parent_view
        
        select = Select(
            placeholder="Выберите экономический район...",
            options=[discord.SelectOption(label=e, value=e) for e in list(economic_regions.keys())[:25]]
        )
        select.callback = self.on_econ_select
        self.add_item(select)
        
        back_button = Button(label="Назад к странам", style=discord.ButtonStyle.secondary)
        back_button.callback = self.on_back
        self.add_item(back_button)
    
    async def on_econ_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        econ_region = interaction.data["values"][0]
        
        regions = get_region_from_economic_region(self.target_country, econ_region)
        if not regions:
            await interaction.response.send_message(f"В районе {econ_region} нет регионов", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор региона",
            description=f"Цель: {self.target_country} / {econ_region}",
            color=DARK_THEME_COLOR
        )
        
        view = NavalRegionSelectView(self.user_id, self.fleet, self.target_country, econ_region, regions, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        view = NavalCountrySelectView(self.user_id, self.fleet, [self.target_country], self.parent_view)
        embed = discord.Embed(
            title="Выбор страны для удара",
            description=f"Флот: {self.fleet.name} в {self.fleet.current_zone.value}",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=view)


class NavalRegionSelectView(View):
    def __init__(self, user_id, fleet, target_country, econ_region, regions, parent_view):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.fleet = fleet
        self.target_country = target_country
        self.econ_region = econ_region
        self.regions = regions
        self.parent_view = parent_view
        
        select = Select(
            placeholder="Выберите регион...",
            options=[discord.SelectOption(label=r, value=r) for r in list(regions.keys())[:25]]
        )
        select.callback = self.on_region_select
        self.add_item(select)
        
        back_button = Button(label="Назад к районам", style=discord.ButtonStyle.secondary)
        back_button.callback = self.on_back
        self.add_item(back_button)
    
    async def on_region_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        target_region = interaction.data["values"][0]
        
        available_weapons = get_fleet_available_weapons(self.fleet)
        
        if not available_weapons:
            await interaction.response.send_message("У флота нет доступного оружия для удара", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор оружия",
            description=f"Цель: {self.target_country} / {self.econ_region} / {target_region}",
            color=DARK_THEME_COLOR
        )
        
        view = NavalWeaponSelectViewWithDistribution(self.user_id, self.fleet, self.target_country, target_region, available_weapons, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def on_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        view = NavalEconRegionSelectView(self.user_id, self.fleet, self.target_country, {self.econ_region: {}}, self.parent_view)
        embed = discord.Embed(
            title="Выбор экономического района",
            description=f"Цель: {self.target_country}",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=view)


# ==================== КЛАССЫ ДЛЯ ВЫБОРА ОРУЖИЯ ====================

class NavalWeaponSelectViewWithDistribution(View):
    """Выбор оружия для удара"""
    
    def __init__(self, user_id, fleet, target_country, target_region, available_weapons, parent_view):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.fleet = fleet
        self.target_country = target_country
        self.target_region = target_region
        self.available_weapons = available_weapons
        self.parent_view = parent_view
        
        for weapon_id, quantity in available_weapons:
            weapon_info = FLEET_WEAPONS.get(weapon_id, {})
            type_marker = "ЯД" if weapon_info.get("nuclear") else "АВ" if weapon_info.get("type") == "air" else "РК"
            button = Button(
                label=f"[{type_marker}] {weapon_info.get('name', weapon_id)} | {quantity} шт. | Дальн: {weapon_info.get('range', 0)} км",
                style=discord.ButtonStyle.secondary
            )
            button.callback = self.create_weapon_callback(weapon_id, quantity)
            self.add_item(button)
        
        back_button = Button(label="Назад к регионам", style=discord.ButtonStyle.secondary)
        back_button.callback = self.on_back
        self.add_item(back_button)
    
    def create_weapon_callback(self, weapon_id, max_quantity):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Это не ваше меню", ephemeral=True)
                return
            
            modal = WeaponDistributionModal(
                self.user_id, self.fleet, self.target_country, self.target_region,
                weapon_id, max_quantity, self
            )
            await interaction.response.send_modal(modal)
        return callback
    
    async def on_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        await self.parent_view.on_back(interaction)


class WeaponDistributionModal(Modal):
    """Модальное окно для ввода количества оружия"""
    
    def __init__(self, user_id, fleet, target_country, target_region, weapon_id, max_quantity, parent_view):
        super().__init__(title="Количество оружия")
        self.user_id = user_id
        self.fleet = fleet
        self.target_country = target_country
        self.target_region = target_region
        self.weapon_id = weapon_id
        self.max_quantity = max_quantity
        self.parent_view = parent_view
        
        self.quantity_input = TextInput(
            label=f"Количество (макс: {max_quantity})",
            placeholder="Введите число",
            min_length=1,
            max_length=4,
            required=True,
            default=str(min(max_quantity, 10))
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > self.max_quantity:
                await interaction.response.send_message(f"Количество должно быть от 1 до {self.max_quantity}", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Введите корректное число", ephemeral=True)
            return
        
        region_data = get_region_data(self.target_country, self.target_region)
        if not region_data:
            await interaction.response.send_message("Регион не найден", ephemeral=True)
            return
        
        available_targets = []
        for target_id, target_info in TARGET_TYPES.items():
            has_target = False
            count = 0
            for field in target_info.get("infra_fields", []):
                if field in region_data:
                    field_count = get_asset_total(region_data, field)
                    if field_count > 0:
                        has_target = True
                        count += field_count
            if has_target:
                available_targets.append((target_id, {
                    "name": target_info["name"],
                    "count": count,
                    "priority": target_info.get("priority", 5)
                }))
        
        if not available_targets:
            await interaction.response.send_message("В регионе нет доступных целей", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор приоритетных целей",
            description=f"Оружие: {FLEET_WEAPONS.get(self.weapon_id, {}).get('name', self.weapon_id)} | Доступно: {quantity} шт.\n"
                       f"Целевой регион: {self.target_region}\n\n"
                       f"Выберите цели в порядке приоритета (от самой важной к менее важной).\n"
                       f"Оружие будет распределяться с учётом приоритета.",
            color=DARK_THEME_COLOR
        )
        
        view = TargetPrioritySelectView(
            self.user_id, self.fleet, self.target_country, self.target_region,
            self.weapon_id, quantity, available_targets, self
        )
        await interaction.response.edit_message(embed=embed, view=view)


class TargetPrioritySelectView(View):
    """View для выбора приоритетных целей в порядке важности"""
    
    def __init__(self, user_id, fleet, target_country, target_region, weapon_id, quantity, available_targets, parent_view):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.fleet = fleet
        self.target_country = target_country
        self.target_region = target_region
        self.weapon_id = weapon_id
        self.quantity = quantity
        self.available_targets = available_targets
        self.parent_view = parent_view
        self.selected_targets = []
        
        self.available_targets.sort(key=lambda x: x[1]["priority"])
        self.update_select_options()
        
        self.target_select = Select(
            placeholder="Выберите цель (нажимайте несколько раз для добавления)",
            options=self.options,
            min_values=1,
            max_values=1
        )
        self.target_select.callback = self.on_target_selected
        self.add_item(self.target_select)
        
        self.add_button = Button(label="Добавить цель", style=discord.ButtonStyle.primary)
        self.add_button.callback = self.on_add
        self.add_item(self.add_button)
        
        self.done_button = Button(label="Завершить выбор", style=discord.ButtonStyle.success)
        self.done_button.callback = self.on_done
        self.add_item(self.done_button)
        
        self.back_button = Button(label="Назад к выбору оружия", style=discord.ButtonStyle.secondary)
        self.back_button.callback = self.on_back
        self.add_item(self.back_button)
    
    def update_select_options(self):
        self.options = []
        for target_id, target_info in self.available_targets:
            if not any(tid == target_id for tid, _ in self.selected_targets):
                self.options.append(discord.SelectOption(
                    label=f"{target_info['name']} (доступно: {target_info['count']})",
                    value=target_id,
                    description=f"Приоритет: {target_info['priority']}"
                ))
    
    async def on_target_selected(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        await interaction.response.defer()
    
    async def on_add(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        target_id = self.target_select.values[0]
        target_info = next(t for t in self.available_targets if t[0] == target_id)[1]
        
        if any(tid == target_id for tid, _ in self.selected_targets):
            await interaction.response.send_message(f"Цель '{target_info['name']}' уже добавлена! Выберите другую цель.", ephemeral=True)
            return
        
        self.selected_targets.append((target_id, target_info))
        self.update_select_options()
        self.target_select.options = self.options
        
        embed = discord.Embed(
            title="Выбор приоритетных целей",
            description=f"Оружие: {FLEET_WEAPONS.get(self.weapon_id, {}).get('name', self.weapon_id)} | Доступно: {self.quantity} шт.\n"
                       f"Целевой регион: {self.target_region}",
            color=DARK_THEME_COLOR
        )
        
        selected_text = ""
        for i, (tid, info) in enumerate(self.selected_targets, 1):
            selected_text += f"{i}. {info['name']} (доступно: {info['count']})\n"
        
        if selected_text:
            embed.add_field(name="Выбранные цели (по приоритету)", value=selected_text, inline=False)
        else:
            embed.add_field(name="Выбранные цели", value="Пока не выбраны", inline=False)
        
        remaining_options = [opt for opt in self.options]
        if remaining_options:
            remaining_text = ""
            for opt in remaining_options[:5]:
                remaining_text += f"• {opt.label}\n"
            if len(remaining_options) > 5:
                remaining_text += f"... и ещё {len(remaining_options) - 5}"
            embed.add_field(name="Доступные цели", value=remaining_text, inline=False)
        else:
            embed.add_field(name="Доступные цели", value="Все цели уже выбраны", inline=False)
        
        embed.add_field(
            name="Инструкция",
            value="Добавляйте цели в порядке приоритета. Каждую цель можно выбрать только один раз.\n"
                  "Чем выше в списке, тем больше оружия получит цель.\n"
                  "После добавления всех целей нажмите 'Завершить выбор'.",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def on_done(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        if not self.selected_targets:
            await interaction.response.send_message("Выберите хотя бы одну цель", ephemeral=True)
            return
        
        distribution = self.distribute_weapons()
        weapon = FLEET_WEAPONS.get(self.weapon_id, {})
        distance = calculate_attack_distance(self.fleet, self.target_country, self.target_region)
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ УДАРА",
            description=f"Операция против {self.target_country}",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Флот", value=self.fleet.name, inline=True)
        embed.add_field(name="Зона флота", value=self.fleet.current_zone.value, inline=True)
        embed.add_field(name="Целевой регион", value=self.target_region, inline=True)
        embed.add_field(name="Расстояние", value=f"{distance} км", inline=True)
        embed.add_field(name="Оружие", value=f"{weapon.get('name', self.weapon_id)} x{self.quantity}", inline=True)
        
        dist_text = ""
        for target_id, qty in distribution:
            target_info = next(t for t in self.available_targets if t[0] == target_id)[1]
            dist_text += f"• {target_info['name']}: {qty} ед.\n"
        embed.add_field(name="Распределение", value=dist_text, inline=False)
        
        embed.add_field(
            name="Предупреждение",
            value="Оружие будет списано из флота независимо от результата. Подтверждаете пуск?",
            inline=False
        )
        
        view = MultiTargetConfirmationView(
            self.user_id, self.fleet, self.target_country, self.target_region,
            self.weapon_id, self.quantity, distribution
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    def distribute_weapons(self) -> List[Tuple[str, int]]:
        num_targets = len(self.selected_targets)
        quantity = self.quantity
        
        weights = []
        for i in range(num_targets):
            weight = 2 ** (num_targets - i)
            weights.append(weight)
        
        total_weight = sum(weights)
        
        distribution = []
        remaining = quantity
        
        for i, (target_id, target_info) in enumerate(self.selected_targets):
            if i == num_targets - 1:
                qty = min(remaining, target_info["count"])
            else:
                qty = min(int(quantity * weights[i] / total_weight), target_info["count"])
                qty = min(qty, remaining)
            
            if qty > 0:
                distribution.append((target_id, qty))
                remaining -= qty
        
        return distribution
    
    async def on_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        available_weapons = get_fleet_available_weapons(self.fleet)
        view = NavalWeaponSelectViewWithDistribution(
            self.user_id, self.fleet, self.target_country, self.target_region,
            available_weapons, self.parent_view
        )
        embed = discord.Embed(
            title="Выбор оружия",
            description=f"Цель: {self.target_country} / {self.target_region}",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=view)


class MultiTargetConfirmationView(View):
    """Подтверждение удара по нескольким целям"""
    
    def __init__(self, user_id, fleet, target_country, target_region, weapon_id, quantity, distribution):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.fleet = fleet
        self.target_country = target_country
        self.target_region = target_region
        self.weapon_id = weapon_id
        self.quantity = quantity
        self.distribution = distribution
        self.bot = None
    
    @discord.ui.button(label="ПОДТВЕРДИТЬ ПУСК", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        await interaction.response.defer()
        self.bot = interaction.client
        
        result = execute_multi_target_strike(
            self.fleet, self.target_country, self.target_region,
            self.weapon_id, self.quantity, self.distribution
        )
        
        if not result["success"]:
            await interaction.followup.send(result["message"], ephemeral=True)
            return
        
        embed = discord.Embed(
            title="РЕЗУЛЬТАТ УДАРА",
            description=result["message"],
            color=discord.Color.red() if result.get("destroyed_objects", 0) > 0 else discord.Color.orange()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        if self.bot and NAVY_LOG_CHANNEL_ID:
            try:
                channel = self.bot.get_channel(NAVY_LOG_CHANNEL_ID)
                if channel:
                    log_embed = discord.Embed(
                        title=f"ЯДЕРНЫЙ УДАР" if result.get("is_nuclear") else f"ВОЕННЫЙ УДАР",
                        description=result["message"],
                        color=discord.Color.red() if result.get("is_nuclear") else discord.Color.orange()
                    )
                    log_embed.set_footer(text=f"Флот: {self.fleet.name} | Цель: {self.target_country} - {self.target_region}")
                    await channel.send(embed=log_embed)
            except Exception as e:
                print(f"Ошибка при отправке лога в канал: {e}")
    
    @discord.ui.button(label="ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Удар отменён",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_navy_menu',
    'navy_update_loop',
    'initialize_fleets',
    'SeaZone',
    'SHIP_TYPES',
    'FLEET_WEAPONS',
    'add_blockade',
    'remove_blockade',
    'get_active_blockades',
    'is_ship_blocked',
    'get_ships_in_zone_with_blockade',
    'get_ships_in_zone'
]

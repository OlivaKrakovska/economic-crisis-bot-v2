# pipelines.py - Модуль управления транснациональными трубопроводами
# Версия 6.6 - добавлена проверка расстояний между странами

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import random
import asyncio
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from political_power import spend_political_power, get_political_power, add_political_power
from game_time import get_current_game_time, days_since_last_event
from resource_system import RESOURCE_PRICES, RESOURCE_TYPES

# Попытка импорта модулей для расчёта расстояний
try:
    from generate_distances import haversine_distance
    from region_coordinates import REGION_COORDINATES, get_region_coordinates
    DISTANCES_AVAILABLE = True
except ImportError:
    DISTANCES_AVAILABLE = False
    print("⚠️ Модули координат не найдены, проверка расстояний отключена")

# Файлы для хранения данных
PIPELINES_FILE = 'pipelines.json'
PIPELINE_CONSTRUCTION_FILE = 'pipeline_construction.json'
PIPELINE_LOGS_FILE = 'pipeline_logs.json'
PIPELINE_DIPLOMACY_FILE = 'pipeline_diplomacy.json'

# Единый ID канала для всех логов
PIPELINE_LOG_CHANNEL_ID = 1249782883770695821

# Время на ответ по проекту (часов реальных)
PROJECT_RESPONSE_TIMEOUT_HOURS = 24

# Константы для пересчёта времени (1 реальный день = 3 игровых месяца = 90 игровых дней)
REAL_DAY_TO_GAME_DAYS = 90
REAL_HOUR_TO_GAME_DAYS = 90 / 24
REAL_SECOND_TO_GAME_DAYS = 90 / (24 * 3600)

def real_hours_to_game_days(hours: int) -> float:
    """Переводит реальные часы в игровые дни"""
    return hours * REAL_HOUR_TO_GAME_DAYS

def real_seconds_to_game_days(seconds: int) -> float:
    """Переводит реальные секунды в игровые дни"""
    return seconds * REAL_SECOND_TO_GAME_DAYS

def format_game_days(days: float) -> str:
    """Форматирует игровые дни в читаемый вид (дни, месяцы, годы)"""
    if days < 30:
        return f"{int(days)} дн."
    elif days < 365:
        months = int(days / 30)
        return f"{months} мес."
    else:
        years = int(days / 365)
        remaining_days = int(days % 365)
        if remaining_days > 0:
            return f"{years} г. {remaining_days} дн."
        return f"{years} г."

# URL картинок для эмбедов
PIPELINE_IMAGE_URL = "https://avatars.mds.yandex.net/i?id=4ff558b6adee097798282b2bdc78b7eb_l-5283663-images-thumbs&n=13"
PIPELINE_CONTROL_IMAGE_URL = "https://avatars.mds.yandex.net/i?id=11ed0aae50544ed2ed98de28acc250d9_l-4120427-images-thumbs&n=13"
PIPELINE_CONSTRUCTION_IMAGE_URL = "https://ptgs.ru/upload/resize_cache/iblock/d0b/872_556_2/xwn5vrhr7kztpkpx9n7c4zn61j9w1xnq.jpg"
PIPELINE_DISMANTLE_IMAGE_URL = "https://demontag24.ru/wp-content/uploads/2025/10/image-450.jpg"
PIPELINE_CLOSE_IMAGE_URL = "https://avatars.mds.yandex.net/i?id=cf39533972d4af8c3c458de4bcb7695903c76775_l-9264516-images-thumbs&n=13"

# Картинки для безопасности
PIPELINE_SECURITY_IMAGES = [
    "https://rossaprimavera.ru/static/files/f3b663eec1cc.jpg",
    "https://avatars.mds.yandex.net/i?id=b4253dc8d146a6ea528dddb26480d757-5232677-images-thumbs&n=13"
]

# Картинки для других действий
PIPELINE_OTHER_IMAGES = [
    "https://img-fotki.yandex.ru/get/54905/50083820.554/0_118dd6_6ccc42ee_orig",
    "https://avatars.mds.yandex.net/get-altay/11395962/2a0000018dd4f32b120b5786d8347340770d/orig"
]


# ==================== СЕРВЕРНЫЕ ЭМОДЗИ ====================

EMOJIS = {
    "gas": "<:gaz:1272269314745040897>",
    "oil": "<:Oil:1262014013273935872>",
    "military": "<:reserv:1432463316445564978>",
    "money": "<:bank:1453457581153718322>",
    "worker": "<:raboch:1432463765739409408>",
    "engineer": "<:energetic:1459183670396190740>",
    "armored": "<:bm:1270686898557554781>",
    "soldier": "<:strelok:1487015420895690842>",
    "political_power": "<:pp:1487015341883130027>",
    "police": "<:police:1487015253391839373>",
    "drone": "<:dronchik:1487016323732213760>",
    "salary": "<:zplata:1487016216873930842>"
}


def get_random_security_image() -> str:
    return random.choice(PIPELINE_SECURITY_IMAGES)


def get_random_other_image() -> str:
    return random.choice(PIPELINE_OTHER_IMAGES)


def get_random_construction_image() -> str:
    return PIPELINE_CONSTRUCTION_IMAGE_URL


def format_game_time_short() -> str:
    """Возвращает сокращённое игровое время (день, месяц, год)"""
    game_date, _ = get_current_game_time()
    month_names = ["янв", "фев", "мар", "апр", "май", "июн",
                   "июл", "авг", "сен", "окт", "ноя", "дек"]
    return f"{game_date.day} {month_names[game_date.month-1]} {game_date.year}"


# Флаги стран
COUNTRY_FLAGS = {
    "Россия": "🇷🇺", "США": "🇺🇸", "Китай": "🇨🇳", "Германия": "🇩🇪",
    "Великобритания": "🇬🇧", "Франция": "🇫🇷", "Япония": "🇯🇵", "Израиль": "🇮🇱",
    "Украина": "🇺🇦", "Иран": "🇮🇷", "Беларусь": "🇧🇾", "Норвегия": "🇳🇴",
    "КНДР": "🇰🇵", "Турция": "🇹🇷", "Сирия": "🇸🇾", "Канада": "🇨🇦",
    "Польша": "🇵🇱", "Бразилия": "🇧🇷", "Швеция": "🇸🇪", "Финляндия": "🇫🇮",
    "Швейцария": "🇨🇭", "Египет": "🇪🇬", "Азербайджан": "🇦🇿", "Казахстан": "🇰🇿",
    "Грузия": "🇬🇪", "Италия": "🇮🇹", "Албания": "🇦🇱", "Болгария": "🇧🇬",
    "Сербия": "🇷🇸", "Венгрия": "🇭🇺", "Словакия": "🇸🇰", "Чехия": "🇨🇿", "Дания": "🇩🇰"
}

# ==================== КОНСТАНТЫ ====================

PIPELINE_TYPES = {
    "oil": {
        "name": "Нефтепровод",
        "description": "Транспортировка нефти",
        "land_cost_per_km": 18,
        "sea_cost_per_km": 36,
        "maintenance_cost_per_km": 0.5,
        "dismantle_cost_per_km": 10,
        "dismantle_time_per_km": 300,  # секунд реального времени
        "capacity": 5,
        "resource": "oil",
        "damage_effect": 0.02,
        "repair_time_per_km": 600,
        "damage_resource_loss": 0.1,
        "color": 0x2b2d31
    },
    "gas": {
        "name": "Газопровод",
        "description": "Транспортировка природного газа",
        "land_cost_per_km": 15,
        "sea_cost_per_km": 30,
        "maintenance_cost_per_km": 0.4,
        "dismantle_cost_per_km": 8,
        "dismantle_time_per_km": 300,
        "capacity": 3,
        "resource": "gas",
        "damage_effect": 0.02,
        "repair_time_per_km": 600,
        "damage_resource_loss": 0.1,
        "color": 0x2b2d31
    }
}

# Коэффициенты усиления контроля войсками
TROOP_CONTROL_BOOST = 0.001
VEHICLE_CONTROL_BOOST = 0.01
DRONE_CONTROL_BOOST = 0.018

MAX_ARMY_PERCENT = 8

# ==================== ПРОТЯЖЁННОСТЬ ТРУБОПРОВОДОВ ПО СТРАНАМ ====================

PIPELINE_LENGTHS_BY_COUNTRY = {
    "druzhba": {
        "Россия": {"land": 400, "sea": 0}, "Беларусь": {"land": 400, "sea": 0},
        "Украина": {"land": 500, "sea": 0}, "Польша": {"land": 680, "sea": 0},
        "Германия": {"land": 320, "sea": 0}, "Венгрия": {"land": 280, "sea": 0},
        "Словакия": {"land": 120, "sea": 0}, "Чехия": {"land": 300, "sea": 0}
    },
    "nord_stream": {
        "Россия": {"land": 0, "sea": 150}, "Финляндия": {"land": 0, "sea": 200},
        "Швеция": {"land": 0, "sea": 400}, "Дания": {"land": 0, "sea": 250},
        "Германия": {"land": 0, "sea": 224}
    },
    "turkish_stream": {
        "Россия": {"land": 0, "sea": 630}, "Турция": {"land": 150, "sea": 0},
        "Болгария": {"land": 180, "sea": 0}, "Сербия": {"land": 200, "sea": 0},
        "Венгрия": {"land": 150, "sea": 0}
    },
    "yamal_europe": {
        "Россия": {"land": 2500, "sea": 0}, "Беларусь": {"land": 550, "sea": 0},
        "Польша": {"land": 680, "sea": 0}, "Германия": {"land": 466, "sea": 0}
    },
    "power_of_siberia": {"Россия": {"land": 2800, "sea": 0}, "Китай": {"land": 200, "sea": 0}},
    "keystone": {"Канада": {"land": 650, "sea": 0}, "США": {"land": 3697, "sea": 0}},
    "colonial": {"США": {"land": 8850, "sea": 0}},
    "transcanada": {"Канада": {"land": 2000, "sea": 0}, "США": {"land": 590, "sea": 0}},
    "btc": {"Азербайджан": {"land": 443, "sea": 0}, "Грузия": {"land": 249, "sea": 0}, "Турция": {"land": 1076, "sea": 0}},
    "caspian_pipeline": {"Казахстан": {"land": 450, "sea": 0}, "Россия": {"land": 1061, "sea": 0}},
    "tap": {"Греция": {"land": 378, "sea": 0}, "Албания": {"land": 215, "sea": 0}, "Италия": {"land": 85, "sea": 200}}
}

# ==================== СТАНДАРТНЫЕ ТРУБОПРОВОДЫ ====================

DEFAULT_PIPELINES = [
    {
        "id": "druzhba", "name": "Дружба", "operator": "Россия", "type": "oil",
        "total_length": 4000, "land_length": 4000, "sea_length": 0,
        "countries_through": ["Россия", "Беларусь", "Украина", "Польша", "Германия", "Венгрия", "Словакия", "Чехия"],
        "status": "active", "damage": 0, "security_level": 0.5,
        "constructed_at": "1964-01-01", "last_maintenance": None, "construction_cost": 72000,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["druzhba"]
    },
    {
        "id": "nord_stream", "name": "Северный поток", "operator": "Россия", "type": "gas",
        "total_length": 1224, "land_length": 0, "sea_length": 1224,
        "countries_through": ["Россия", "Германия", "Финляндия", "Швеция", "Дания"],
        "status": "active", "damage": 0, "security_level": 0.6,
        "constructed_at": "2011-01-01", "last_maintenance": None, "construction_cost": 36720,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["nord_stream"]
    },
    {
        "id": "turkish_stream", "name": "Турецкий поток", "operator": "Россия", "type": "gas",
        "total_length": 930, "land_length": 300, "sea_length": 630,
        "countries_through": ["Россия", "Турция", "Болгария", "Сербия", "Венгрия"],
        "status": "active", "damage": 0, "security_level": 0.55,
        "constructed_at": "2020-01-01", "last_maintenance": None, "construction_cost": 23400,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["turkish_stream"]
    },
    {
        "id": "yamal_europe", "name": "Ямал-Европа", "operator": "Россия", "type": "gas",
        "total_length": 4196, "land_length": 4196, "sea_length": 0,
        "countries_through": ["Россия", "Беларусь", "Польша", "Германия"],
        "status": "active", "damage": 0, "security_level": 0.5,
        "constructed_at": "1994-01-01", "last_maintenance": None, "construction_cost": 62940,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["yamal_europe"]
    },
    {
        "id": "power_of_siberia", "name": "Сила Сибири", "operator": "Россия", "type": "gas",
        "total_length": 3000, "land_length": 3000, "sea_length": 0,
        "countries_through": ["Россия", "Китай"], "status": "active", "damage": 0, "security_level": 0.7,
        "constructed_at": "2019-01-01", "last_maintenance": None, "construction_cost": 45000,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["power_of_siberia"]
    },
    {
        "id": "keystone", "name": "Keystone", "operator": "США", "type": "oil",
        "total_length": 4347, "land_length": 4347, "sea_length": 0,
        "countries_through": ["Канада", "США"], "status": "active", "damage": 0, "security_level": 0.7,
        "constructed_at": "2010-01-01", "last_maintenance": None, "construction_cost": 78246,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["keystone"]
    },
    {
        "id": "colonial", "name": "Colonial", "operator": "США", "type": "oil",
        "total_length": 8850, "land_length": 8850, "sea_length": 0,
        "countries_through": ["США"], "status": "active", "damage": 0, "security_level": 0.65,
        "constructed_at": "1962-01-01", "last_maintenance": None, "construction_cost": 159300,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["colonial"]
    },
    {
        "id": "transcanada", "name": "TransCanada", "operator": "Канада", "type": "gas",
        "total_length": 2590, "land_length": 2590, "sea_length": 0,
        "countries_through": ["Канада", "США"], "status": "active", "damage": 0, "security_level": 0.6,
        "constructed_at": "1951-01-01", "last_maintenance": None, "construction_cost": 38850,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["transcanada"]
    },
    {
        "id": "btc", "name": "Баку-Тбилиси-Джейхан", "operator": "Азербайджан", "type": "oil",
        "total_length": 1768, "land_length": 1768, "sea_length": 0,
        "countries_through": ["Азербайджан", "Грузия", "Турция"],
        "status": "active", "damage": 0, "security_level": 0.6,
        "constructed_at": "2006-01-01", "last_maintenance": None, "construction_cost": 31824,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["btc"]
    },
    {
        "id": "caspian_pipeline", "name": "Каспийский трубопровод", "operator": "Казахстан", "type": "oil",
        "total_length": 1511, "land_length": 1511, "sea_length": 0,
        "countries_through": ["Казахстан", "Россия"], "status": "active", "damage": 0, "security_level": 0.55,
        "constructed_at": "2001-01-01", "last_maintenance": None, "construction_cost": 27198,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["caspian_pipeline"]
    },
    {
        "id": "tap", "name": "Трансадриатический газопровод", "operator": "Греция", "type": "gas",
        "total_length": 878, "land_length": 378, "sea_length": 500,
        "countries_through": ["Греция", "Албания", "Италия"],
        "status": "active", "damage": 0, "security_level": 0.55,
        "constructed_at": "2020-01-01", "last_maintenance": None, "construction_cost": 20670,
        "closed_sections": {}, "country_control": {}, "country_military": {}, "country_vehicles": {}, "country_uav": {},
        "country_length": PIPELINE_LENGTHS_BY_COUNTRY["tap"]
    }
]


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_country_length(pipeline: Dict, country: str) -> int:
    lengths = pipeline.get("country_length", {})
    if not isinstance(lengths, dict):
        return 0
    country_len = lengths.get(country, {})
    if isinstance(country_len, dict):
        return country_len.get("land", 0) + country_len.get("sea", 0)
    return 0


def get_country_land_length(pipeline: Dict, country: str) -> int:
    lengths = pipeline.get("country_length", {})
    if not isinstance(lengths, dict):
        return 0
    country_len = lengths.get(country, {})
    if isinstance(country_len, dict):
        return country_len.get("land", 0)
    return 0


def get_country_sea_length(pipeline: Dict, country: str) -> int:
    lengths = pipeline.get("country_length", {})
    if not isinstance(lengths, dict):
        return 0
    country_len = lengths.get(country, {})
    if isinstance(country_len, dict):
        return country_len.get("sea", 0)
    return 0


def calculate_base_control(pipeline: Dict, country: str) -> float:
    country_len = get_country_length(pipeline, country)
    total_len = pipeline.get("total_length", 1)
    if total_len <= 0:
        return 0.0
    return min(100.0, (country_len / total_len) * 100)


def calculate_control_from_military(troops: int, vehicles: int, drones: int) -> float:
    return (troops * TROOP_CONTROL_BOOST) + (vehicles * VEHICLE_CONTROL_BOOST) + (drones * DRONE_CONTROL_BOOST)


def calculate_pipeline_security(pipeline: Dict) -> float:
    """
    Безопасность трубопровода равна средневзвешенному контролю по всем странам
    Вес каждой страны = длина её участка / общая длина
    """
    if not pipeline.get("countries_through"):
        return 50.0
    
    total_length = pipeline.get("total_length", 1)
    if total_length <= 0:
        return 50.0
    
    weighted_control = 0.0
    
    for country in pipeline["countries_through"]:
        control = pipeline["country_control"].get(country, 0)
        country_len = get_country_length(pipeline, country)
        weight = country_len / total_length
        weighted_control += control * weight
    
    return weighted_control


def update_pipeline_security(pipeline: Dict) -> float:
    """Обновляет безопасность трубопровода на основе средневзвешенного контроля"""
    new_security = calculate_pipeline_security(pipeline)
    pipeline["security_level"] = new_security / 100
    return new_security


def update_pipeline_security(pipeline: Dict) -> float:
    """Обновляет безопасность трубопровода на основе минимального контроля"""
    new_security = calculate_pipeline_security(pipeline)
    pipeline["security_level"] = new_security / 100
    return new_security


def get_army_totals(player_data: Dict) -> Dict[str, int]:
    infantry = player_data.get("state", {}).get("army_size", 0)
    army = player_data.get("army", {})
    ground = army.get("ground", {})
    air = army.get("air", {})
    armored_vehicles = ground.get("armored_vehicles", 0) or ground.get("armor", 0)
    total_drones = air.get("attack_uav", 0) + air.get("recon_uav", 0)
    return {"infantry": infantry, "armored_vehicles": armored_vehicles, "drones": total_drones}


def get_deployed_army_totals(pipeline: Dict, country: str) -> Dict[str, int]:
    mil = pipeline.get("country_military", {})
    veh = pipeline.get("country_vehicles", {})
    uav = pipeline.get("country_uav", {})
    return {
        "infantry": mil.get(country, {}).get("infantry", 0) if isinstance(mil.get(country), dict) else 0,
        "armored_vehicles": veh.get(country, {}).get("armored_vehicles", 0) if isinstance(veh.get(country), dict) else 0,
        "drones": (uav.get(country, {}).get("attack_uav", 0) + uav.get(country, {}).get("recon_uav", 0)) if isinstance(uav.get(country), dict) else 0
    }


def get_max_deployable_units(player_data: Dict) -> Dict[str, int]:
    army = get_army_totals(player_data)
    max_percent = MAX_ARMY_PERCENT / 100
    return {
        "infantry": int(army["infantry"] * max_percent),
        "armored_vehicles": int(army["armored_vehicles"] * max_percent),
        "drones": int(army["drones"] * max_percent)
    }


def calculate_control_increase_cost(pipeline: Dict, country: str, increase_percent: float) -> float:
    country_len = get_country_length(pipeline, country)
    if country_len <= 0:
        country_len = pipeline["total_length"] // max(1, len(pipeline.get("countries_through", [])))
    return max(0.01, (country_len / 100) * (increase_percent / 10))


def can_deploy_more_units(pipeline: Dict, country: str, player_data: Dict, t, v, d) -> Tuple[bool, str]:
    army = get_army_totals(player_data)
    deployed = get_deployed_army_totals(pipeline, country)
    max_d = get_max_deployable_units(player_data)
    if t > army["infantry"]: return False, f"Недостаточно пехоты (есть {army['infantry']})"
    if v > army["armored_vehicles"]: return False, f"Недостаточно бронетехники (есть {army['armored_vehicles']})"
    if d > army["drones"]: return False, f"Недостаточно дронов (есть {army['drones']})"
    if deployed["infantry"] + t > max_d["infantry"]: return False, f"Максимум пехоты у трубы: {max_d['infantry']} (8% от армии)"
    if deployed["armored_vehicles"] + v > max_d["armored_vehicles"]: return False, f"Максимум бронетехники: {max_d['armored_vehicles']}"
    if deployed["drones"] + d > max_d["drones"]: return False, f"Максимум дронов: {max_d['drones']}"
    return True, "OK"


def can_withdraw_units(pipeline: Dict, country: str, t, v, d) -> Tuple[bool, str]:
    deployed = get_deployed_army_totals(pipeline, country)
    if t > deployed["infantry"]: return False, f"У трубы нет столько пехоты (есть {deployed['infantry']})"
    if v > deployed["armored_vehicles"]: return False, f"У трубы нет столько бронетехники (есть {deployed['armored_vehicles']})"
    if d > deployed["drones"]: return False, f"У трубы нет столько дронов (есть {deployed['drones']})"
    return True, "OK"


def can_close_section(pipeline: Dict, country: str, player_data: Dict) -> Tuple[bool, str]:
    if country not in pipeline.get("countries_through", []):
        return False, "Трубопровод не проходит через вашу территорию"
    if pipeline.get("closed_sections", {}).get(country, False):
        return False, "Участок уже закрыт"
    return True, "OK"


def can_open_section(pipeline: Dict, country: str, player_data: Dict) -> Tuple[bool, str]:
    if country not in pipeline.get("countries_through", []):
        return False, "Трубопровод не проходит через вашу территорию"
    if not pipeline.get("closed_sections", {}).get(country, False):
        return False, "Участок не закрыт"
    return True, "OK"


def can_dismantle_section(pipeline: Dict, country: str, length: int) -> Tuple[bool, str]:
    if country not in pipeline.get("countries_through", []):
        return False, "На вашей территории нет участка этого трубопровода"
    country_len = get_country_length(pipeline, country)
    if length > country_len:
        return False, f"На территории {country} только {country_len} км трубопровода"
    return True, "OK"


def calculate_dismantle_cost(pipeline: Dict, length: int = None) -> Tuple[float, int]:
    type_data = PIPELINE_TYPES[pipeline["type"]]
    dismantle_length = length if length else pipeline.get("total_length", 0)
    cost = dismantle_length * type_data["dismantle_cost_per_km"]
    time_seconds = dismantle_length * type_data["dismantle_time_per_km"]
    return cost, time_seconds


def calculate_annual_maintenance(pipeline: Dict) -> float:
    type_data = PIPELINE_TYPES[pipeline["type"]]
    return pipeline.get("total_length", 0) * type_data["maintenance_cost_per_km"]


def calculate_daily_flow(pipeline: Dict) -> float:
    capacity = PIPELINE_TYPES[pipeline["type"]]["capacity"]
    damage_factor = 1 - (pipeline.get("damage", 0) / max(1, pipeline.get("total_length", 1))) * 0.5
    security_factor = 1 + (pipeline.get("security_level", 0.5) - 0.5) * 0.5
    return capacity * max(0, damage_factor) * max(0.5, security_factor)


# ==================== ФУНКЦИИ ДЛЯ ПРОВЕРКИ РАССТОЯНИЙ ====================

def get_min_distance_between_countries(country1: str, country2: str) -> float:
    """
    Возвращает минимальное расстояние между ближайшими регионами двух стран
    """
    if not DISTANCES_AVAILABLE:
        return 0
    
    if country1 not in REGION_COORDINATES or country2 not in REGION_COORDINATES:
        return 0
    
    regions1 = REGION_COORDINATES[country1]
    regions2 = REGION_COORDINATES[country2]
    
    min_distance = float('inf')
    
    for reg1, coords1 in regions1.items():
        for reg2, coords2 in regions2.items():
            dist = haversine_distance(
                coords1["lat"], coords1["lon"],
                coords2["lat"], coords2["lon"]
            )
            if dist < min_distance:
                min_distance = dist
    
    return min_distance if min_distance != float('inf') else 0


def get_min_distance_along_route(route_countries: List[str]) -> float:
    """
    Рассчитывает минимальную необходимую длину трубопровода для маршрута
    Суммирует расстояния между соседними странами
    """
    if not DISTANCES_AVAILABLE or len(route_countries) < 2:
        return 0
    
    total_distance = 0
    for i in range(len(route_countries) - 1):
        dist = get_min_distance_between_countries(route_countries[i], route_countries[i + 1])
        if dist == 0:
            # Если расстояние не удалось определить, используем минимальное 100 км
            dist = 100
        total_distance += dist
    
    return total_distance


def can_build_pipeline(operator: str, route_countries: List[str], 
                       land_length: int, sea_length: int) -> Tuple[bool, str]:
    """
    Проверяет, может ли трубопровод такой длины соединить указанные страны
    """
    if not DISTANCES_AVAILABLE:
        # Если модули недоступны, пропускаем проверку
        return True, "OK"
    
    # Формируем полный маршрут: оператор -> страны транзита
    full_route = [operator] + route_countries
    
    min_required = get_min_distance_along_route(full_route)
    actual_length = land_length + sea_length
    
    if actual_length < min_required:
        return False, f"Трубопровод слишком короткий! Минимальная длина для соединения {full_route[0]} → {full_route[-1]} составляет {min_required} км. Ваша длина: {actual_length} км"
    
    return True, "OK"


# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_pipelines():
    try:
        with open(PIPELINES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"pipelines": DEFAULT_PIPELINES.copy(), "stats": {}}
            data = json.loads(content)
            if "pipelines" not in data:
                data["pipelines"] = DEFAULT_PIPELINES.copy()
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"pipelines": DEFAULT_PIPELINES.copy(), "stats": {}}


def save_pipelines(data):
    with open(PIPELINES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_pipeline_construction():
    try:
        with open(PIPELINE_CONSTRUCTION_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_projects": [], "completed_projects": [], "active_dismantles": [], "active_repairs": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_projects": [], "completed_projects": [], "active_dismantles": [], "active_repairs": []}


def save_pipeline_construction(data):
    with open(PIPELINE_CONSTRUCTION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_pipeline_logs():
    try:
        with open(PIPELINE_LOGS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"logs": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"logs": []}


def save_pipeline_logs(data):
    with open(PIPELINE_LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_pipeline_diplomacy():
    try:
        with open(PIPELINE_DIPLOMACY_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"pending_projects": [], "approved_projects": [], "rejected_projects": []}
            data = json.loads(content)
            if "pending_projects" not in data:
                data["pending_projects"] = []
            if "approved_projects" not in data:
                data["approved_projects"] = []
            if "rejected_projects" not in data:
                data["rejected_projects"] = []
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"pending_projects": [], "approved_projects": [], "rejected_projects": []}


def save_pipeline_diplomacy(data):
    with open(PIPELINE_DIPLOMACY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_pipeline_by_id(pipeline_id: str) -> Optional[Dict]:
    data = load_pipelines()
    for p in data["pipelines"]:
        if p["id"] == pipeline_id:
            return p
    return None


def get_pipelines_by_operator(operator: str) -> List[Dict]:
    data = load_pipelines()
    return [p for p in data["pipelines"] if p.get("operator") == operator]


def get_pipelines_through_country(country: str) -> List[Dict]:
    data = load_pipelines()
    return [p for p in data["pipelines"] if country in p.get("countries_through", [])]


# ==================== ФУНКЦИИ ДИПЛОМАТИИ ТРУБОПРОВОДОВ ====================

def create_pipeline_project(operator: str, operator_id: int, name: str, pipeline_type: str,
                            land_length: int, sea_length: int, route_countries: List[str]) -> Dict:
    """Создаёт новый проект трубопровода"""
    type_data = PIPELINE_TYPES[pipeline_type]
    total_cost = (land_length * type_data["land_cost_per_km"] + sea_length * type_data["sea_cost_per_km"]) * 1_000_000
    
    project = {
        "id": f"proj_{int(datetime.now().timestamp())}",
        "name": name,
        "operator": operator,
        "operator_id": operator_id,
        "type": pipeline_type,
        "land_length": land_length,
        "sea_length": sea_length,
        "total_length": land_length + sea_length,
        "route_countries": route_countries,
        "status": "pending",
        "approvals": {},
        "rejections": [],
        "created_at": str(datetime.now()),
        "expires_at": str(datetime.now() + timedelta(hours=PROJECT_RESPONSE_TIMEOUT_HOURS)),
        "total_cost": total_cost
    }
    
    diplomacy = load_pipeline_diplomacy()
    diplomacy["pending_projects"].append(project)
    save_pipeline_diplomacy(diplomacy)
    
    return project


def approve_pipeline_project(project_id: str, country: str, user_id: int) -> Tuple[bool, str]:
    """Принимает проект трубопровода страной транзита"""
    diplomacy = load_pipeline_diplomacy()
    
    project = None
    for p in diplomacy["pending_projects"]:
        if p["id"] == project_id:
            project = p
            break
    
    if not project:
        return False, "Проект не найден или уже обработан"
    
    if country not in project["route_countries"]:
        return False, "Ваша страна не участвует в этом проекте"
    
    if country in project["approvals"]:
        return False, "Ваша страна уже дала согласие"
    
    if country in project["rejections"]:
        return False, "Ваша страна уже отклонила проект"
    
    project["approvals"][country] = {"approved": True, "approved_by": user_id, "approved_at": str(datetime.now())}
    
    all_approved = all(c in project["approvals"] for c in project["route_countries"])
    
    if all_approved:
        project["status"] = "approved"
        diplomacy["approved_projects"].append(project)
        diplomacy["pending_projects"].remove(project)
        start_construction_from_project(project)
    
    save_pipeline_diplomacy(diplomacy)
    
    return True, "Согласие принято"


def reject_pipeline_project(project_id: str, country: str, user_id: int) -> Tuple[bool, str]:
    """Отклоняет проект трубопровода страной транзита"""
    diplomacy = load_pipeline_diplomacy()
    
    project = None
    for p in diplomacy["pending_projects"]:
        if p["id"] == project_id:
            project = p
            break
    
    if not project:
        return False, "Проект не найден или уже обработан"
    
    if country not in project["route_countries"]:
        return False, "Ваша страна не участвует в этом проекте"
    
    if country in project["rejections"]:
        return False, "Ваша страна уже отклонила проект"
    
    project["rejections"].append(country)
    project["status"] = "rejected"
    diplomacy["rejected_projects"].append(project)
    diplomacy["pending_projects"].remove(project)
    
    save_pipeline_diplomacy(diplomacy)
    
    return True, "Проект отклонён"


def get_country_pending_projects(country: str) -> List[Dict]:
    """Возвращает список проектов, ожидающих одобрения от страны"""
    diplomacy = load_pipeline_diplomacy()
    result = []
    
    for project in diplomacy["pending_projects"]:
        if country in project["route_countries"] and country not in project["approvals"] and country not in project["rejections"]:
            result.append(project)
    
    return result


def get_operator_projects(operator: str) -> List[Dict]:
    """Возвращает проекты, созданные оператором"""
    diplomacy = load_pipeline_diplomacy()
    result = []
    
    for project in diplomacy["pending_projects"]:
        if project["operator"] == operator:
            project_copy = project.copy()
            project_copy["current_status"] = "pending"
            result.append(project_copy)
    
    for project in diplomacy["approved_projects"]:
        if project["operator"] == operator:
            project_copy = project.copy()
            project_copy["current_status"] = "approved"
            result.append(project_copy)
    
    for project in diplomacy["rejected_projects"]:
        if project["operator"] == operator:
            project_copy = project.copy()
            project_copy["current_status"] = "rejected"
            result.append(project_copy)
    
    return result


def delete_pipeline_project(project_id: str) -> Tuple[bool, str]:
    """Удаляет проект трубопровода"""
    diplomacy = load_pipeline_diplomacy()
    
    for i, p in enumerate(diplomacy["pending_projects"]):
        if p["id"] == project_id:
            del diplomacy["pending_projects"][i]
            save_pipeline_diplomacy(diplomacy)
            return True, "Проект удалён"
    
    for i, p in enumerate(diplomacy["approved_projects"]):
        if p["id"] == project_id:
            del diplomacy["approved_projects"][i]
            save_pipeline_diplomacy(diplomacy)
            return True, "Проект удалён"
    
    for i, p in enumerate(diplomacy["rejected_projects"]):
        if p["id"] == project_id:
            del diplomacy["rejected_projects"][i]
            save_pipeline_diplomacy(diplomacy)
            return True, "Проект удалён"
    
    return False, "Проект не найден"


def start_construction_from_project(project: Dict):
    """Запускает строительство одобренного проекта"""
    route = [project["operator"]] + project["route_countries"]
    country_length = {}
    total_land = project["land_length"]
    total_sea = project["sea_length"]
    per_land = total_land // len(route) if total_land > 0 else 0
    per_sea = total_sea // len(route) if total_sea > 0 else 0
    
    for c in route:
        country_length[c] = {"land": per_land, "sea": per_sea}
    
    # Время строительства в реальных секундах, но в логах показываем в игровых днях
    construction_seconds = project["total_length"] * 60  # 1 минута на км
    construction_game_days = real_seconds_to_game_days(construction_seconds)
    
    pipeline = {
        "id": project["id"],
        "name": project["name"],
        "operator": project["operator"],
        "type": project["type"],
        "total_length": project["total_length"],
        "land_length": project["land_length"],
        "sea_length": project["sea_length"],
        "countries_through": route,
        "status": "under_construction",
        "damage": 0,
        "security_level": 0.5,
        "constructed_at": str(datetime.now()),
        "last_maintenance": None,
        "construction_cost": project["total_cost"] / 1_000_000,
        "closed_sections": {},
        "country_control": {},
        "country_military": {},
        "country_vehicles": {},
        "country_uav": {},
        "country_length": country_length
    }
    
    for c in route:
        pipeline["country_control"][c] = calculate_base_control(pipeline, c)
        pipeline["country_military"][c] = {"infantry": 0}
        pipeline["country_vehicles"][c] = {"armored_vehicles": 0}
        pipeline["country_uav"][c] = {"attack_uav": 0, "recon_uav": 0}
    
    constr = load_pipeline_construction()
    constr["active_projects"].append({
        "id": f"build_{project['id']}",
        "pipeline_id": project["id"],
        "pipeline_name": project["name"],
        "operator": project["operator"],
        "total_length": project["total_length"],
        "built_length": 0,
        "start_time": str(datetime.now()),
        "completion_time": str(datetime.now() + timedelta(seconds=construction_seconds)),
        "construction_game_days": construction_game_days,
        "status": "in_progress"
    })
    save_pipeline_construction(constr)
    
    data = load_pipelines()
    data["pipelines"].append(pipeline)
    save_pipelines(data)


def can_start_construction(operator: str, origin: str, destinations: List[str], pipeline_type: str,
                           length: int, sea_length: int, player_data: Dict) -> Tuple[bool, str]:
    """Проверяет возможность начала строительства"""
    type_data = PIPELINE_TYPES[pipeline_type]
    total_cost = (length * type_data["land_cost_per_km"] + sea_length * type_data["sea_cost_per_km"]) * 1_000_000
    
    if player_data["economy"]["budget"] < total_cost:
        return False, f"Недостаточно средств. Нужно: {format_billion(total_cost)}"
    
    if player_data["state"]["statename"] != operator:
        return False, "Вы можете строить трубопроводы только от имени своей страны"
    
    # Проверяем, что все страны транзита и назначения заняты игроками
    states = load_states()
    existing_players = {}
    for data in states["players"].values():
        country = data["state"]["statename"]
        assigned_to = data.get("assigned_to")
        if assigned_to:
            existing_players[country] = assigned_to
    
    all_countries = [operator] + destinations
    for country in all_countries:
        if country not in existing_players:
            return False, f"Страна {country} не имеет назначенного игрока! Строительство трубопровода невозможно."
    
    # Проверяем максимальную длину
    max_length = 10000
    if length + sea_length > max_length:
        return False, f"Максимальная протяжённость трубопровода - {max_length} км. Ваша: {length + sea_length} км"
    
    return True, "OK"


# ==================== ФУНКЦИИ ЛОГИРОВАНИЯ ====================

async def send_pipeline_log(bot, event_type: str, data: Dict):
    channel = bot.get_channel(PIPELINE_LOG_CHANNEL_ID)
    if not channel:
        return
    
    game_date, _ = get_current_game_time()
    
    embed = discord.Embed(color=data.get("color", discord.Color.blue()))
    
    if event_type == "close":
        embed.title = f"{EMOJIS['military']} ПЕРЕКРЫТИЕ ТРУБОПРОВОДА"
        embed.description = (
            f"**{data['country']}** перекрыло участок магистрального трубопровода **{data['pipeline_name']}** "
            f"на своей территории.\n\n"
            f"Транзит ресурсов через территорию {data['country']} полностью прекращён. "
            f"Оператор трубопровода — **{data['operator']}**."
        )
        embed.set_image(url=PIPELINE_CLOSE_IMAGE_URL)
    
    elif event_type == "open":
        embed.title = f"{EMOJIS['gas']}{EMOJIS['oil']} ВОССТАНОВЛЕНИЕ ТРАНЗИТА"
        embed.description = (
            f"**{data['country']}** открыло участок трубопровода **{data['pipeline_name']}**.\n\n"
            f"Транзит ресурсов через территорию {data['country']} восстановлен."
        )
        embed.set_image(url=get_random_other_image())
    
    elif event_type == "control":
        embed.title = f"{EMOJIS['military']} УСИЛЕНИЕ КОНТРОЛЯ {EMOJIS['police']}"
        embed.description = (
            f"**{data['country']}** усилило контроль над трубопроводом **{data['pipeline_name']}**.\n\n"
            f"Контроль увеличен на **{data['increase']:.2f}%**, "
            f"текущий уровень: **{data['new_control']:.2f}%**.\n\n"
            f"{EMOJIS['police']} Безопасность трубопровода повышена до **{data['new_security']:.1f}%** "
            f"(средневзвешенный контроль)."
        )
        embed.set_image(url=PIPELINE_CONTROL_IMAGE_URL)
        embed.add_field(
            name=f"{EMOJIS['military']} ЗАДЕЙСТВОВАННЫЕ СИЛЫ",
            value=f"{EMOJIS['soldier']} Пехота: **{data['infantry']}** чел.\n"
                  f"{EMOJIS['armored']} Бронетехника: **{data['vehicles']}** ед.\n"
                  f"{EMOJIS['drone']} Дроны: **{data['drones']}** ед.",
            inline=True
        )
        embed.add_field(
            name=f"{EMOJIS['political_power']} ЗАТРАТЫ",
            value=f"**{data['cost_pp']:.1f}** ПВ",
            inline=True
        )
    
    elif event_type == "withdraw":
        embed.title = f"{EMOJIS['worker']} ВЫВОД ВОЙСК {EMOJIS['police']}"
        embed.description = (
            f"**{data['country']}** вывело войска из трубопровода **{data['pipeline_name']}**.\n\n"
            f"Контроль снизился на **{data['decrease']:.2f}%**, "
            f"текущий уровень: **{data['new_control']:.2f}%**.\n\n"
            f"{EMOJIS['police']} Безопасность трубопровода снижена до **{data['new_security']:.1f}%** "
            f"(минимальный контроль среди всех стран)."
        )
        embed.set_image(url=get_random_other_image())
        embed.add_field(
            name=f"{EMOJIS['military']} ВЫВЕДЕННЫЕ СИЛЫ",
            value=f"{EMOJIS['soldier']} Пехота: **{data['infantry']}** чел.\n"
                  f"{EMOJIS['armored']} Бронетехника: **{data['vehicles']}** ед.\n"
                  f"{EMOJIS['drone']} Дроны: **{data['drones']}** ед.",
            inline=True
        )
    
    elif event_type == "construction":
        embed.title = f"{EMOJIS['engineer']} НОВЫЙ ПРОЕКТ ТРУБОПРОВОДА"
        embed.description = (
            f"**{data['operator']}** предлагает построить новый трубопровод **«{data['pipeline_name']}»**.\n\n"
            f"Маршрут: **{data['route']}**\n"
            f"Тип: **{data['type_name']}**\n"
            f"Протяжённость: **{data['length']} км** (суша: {data['land']}, море: {data['sea']})"
        )
        embed.set_image(url=PIPELINE_CONSTRUCTION_IMAGE_URL)
        embed.add_field(name=f"{EMOJIS['money']} СТОИМОСТЬ", value=format_billion(data['cost']), inline=True)
        embed.add_field(name="⏱️ СРОК СТРОИТЕЛЬСТВА", value=data['time'], inline=True)
        embed.set_footer(text=f"ID: {data['project_id']}")
    
    elif event_type == "dismantle":
        embed.title = f"{EMOJIS['engineer']} ДЕМОНТАЖ ТРУБОПРОВОДА"
        embed.description = (
            f"**{data['country']}** начало разборку участка трубопровода **{data['pipeline_name']}** на своей территории.\n\n"
            f"Будет демонтировано **{data['length']} км** трубопровода. "
            f"Ориентировочное время завершения работ — **{data['time']}**."
        )
        embed.set_image(url=PIPELINE_DISMANTLE_IMAGE_URL)
        embed.add_field(
            name=f"{EMOJIS['money']} ВОЗВРАТ В БЮДЖЕТ",
            value=format_billion(data['refund']),
            inline=True
        )
    
    elif event_type == "project_pending":
        embed.title = f"{EMOJIS['engineer']} ПРОЕКТ ТРУБОПРОВОДА"
        embed.description = (
            f"**{data['operator']}** предлагает построить трубопровод **«{data['name']}»**.\n\n"
            f"Маршрут: **{data['route']}**\n"
            f"Тип: **{data['type_name']}**\n"
            f"Протяжённость: **{data['length']} км** (суша: {data['land']}, море: {data['sea']})"
        )
        embed.set_image(url=PIPELINE_CONSTRUCTION_IMAGE_URL)
        embed.add_field(name=f"{EMOJIS['money']} СТОИМОСТЬ", value=format_billion(data['cost']), inline=True)
        embed.add_field(name="⏱️ СРОК ОТВЕТА", value=f"{PROJECT_RESPONSE_TIMEOUT_HOURS} часов", inline=True)
        embed.set_footer(text=f"ID: {data['project_id']}")
    
    elif event_type == "project_approved":
        embed.title = f"{EMOJIS['engineer']} ПРОЕКТ ОДОБРЕН"
        embed.description = (
            f"Проект трубопровода **«{data['name']}»** получил одобрение всех стран транзита!\n\n"
            f"Строительство начнётся в ближайшее время."
        )
        embed.set_image(url=PIPELINE_CONSTRUCTION_IMAGE_URL)
        embed.add_field(name="Маршрут", value=data['route'], inline=False)
        embed.color = discord.Color.green()
    
    elif event_type == "project_rejected":
        embed.title = f"{EMOJIS['engineer']} ПРОЕКТ ОТКЛОНЁН"
        embed.description = (
            f"Проект трубопровода **«{data['name']}»** отклонён страной **{data['rejected_by']}**.\n\n"
            f"Строительство отменено."
        )
        embed.set_image(url=PIPELINE_CONSTRUCTION_IMAGE_URL)
        embed.color = discord.Color.red()
    
    embed.set_footer(text=f"Игровое время: {game_date.strftime('%d.%m.%Y')}")
    await channel.send(embed=embed)


async def send_pipeline_project_notification(bot, project: Dict):
    """Отправляет уведомление о новом проекте всем странам транзиста"""
    channel = bot.get_channel(PIPELINE_LOG_CHANNEL_ID)
    if not channel:
        return
    
    type_name = "Нефтепровод" if project["type"] == "oil" else "Газопровод"
    route = " → ".join([project["operator"]] + project["route_countries"])
    type_emoji = "🛢️" if project["type"] == "oil" else "🔥"
    
    # Отправляем лог в канал
    await send_pipeline_log(
        bot,
        "project_pending",
        {
            "operator": project["operator"],
            "name": project["name"],
            "route": route,
            "type_name": type_name,
            "length": project["total_length"],
            "land": project["land_length"],
            "sea": project["sea_length"],
            "cost": project["total_cost"],
            "project_id": project["id"],
            "color": DARK_THEME_COLOR
        }
    )
    
    # Отправляем уведомления каждой стране транзита
    for country in project["route_countries"]:
        states = load_states()
        user_id = None
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == country:
                user_id = int(data.get("assigned_to", 0))
                break
        
        # Создаём кнопки для принятия/отказа
        view = PipelineProjectView(project["id"], country)
        
        # Создаём эмбед для уведомления
        embed = discord.Embed(
            title=f"{type_emoji} ПРОЕКТ ТРУБОПРОВОДА",
            description=f"**{project['operator']}** предлагает построить {type_name.lower()} **«{project['name']}»** через территорию **{country}**",
            color=DARK_THEME_COLOR,
            timestamp=datetime.now()
        )
        embed.set_image(url=get_random_construction_image())
        embed.add_field(name="📏 ХАРАКТЕРИСТИКИ", 
                        value=f"• Общая длина: **{project['total_length']} км**\n"
                              f"• По суше: **{project['land_length']} км**\n"
                              f"• По морю: **{project['sea_length']} км**\n"
                              f"• Тип: {type_emoji} {type_name}",
                        inline=False)
        embed.add_field(name="🗺️ МАРШРУТ", value=route, inline=False)
        embed.add_field(name="💰 ФИНАНСИРОВАНИЕ",
                        value=f"Стоимость строительства: **{format_billion(project['total_cost'])}**\n"
                              f"Финансирует: **{project['operator']}**",
                        inline=False)
        embed.add_field(name="⏱️ СРОК ОТВЕТА", 
                        value=f"Вам необходимо ответить в течение **{PROJECT_RESPONSE_TIMEOUT_HOURS} часов**\n"
                              f"ID проекта: `{project['id']}`",
                        inline=False)
        
        # Отправляем в лог-канал с упоминанием
        ping_text = f"<@{user_id}> " if user_id else ""
        await channel.send(f"{ping_text}**{country}**, требуется ваше решение!", embed=embed, view=view)
        
        # Отправляем личное сообщение
        if user_id:
            try:
                user = await bot.fetch_user(user_id)
                await user.send(embed=embed, view=view)
            except Exception as e:
                print(f"Не удалось отправить ЛС {country}: {e}")


async def send_project_approved_notification(bot, project: Dict):
    """Отправляет уведомление об одобрении проекта"""
    route = " → ".join([project["operator"]] + project["route_countries"])
    
    await send_pipeline_log(
        bot,
        "project_approved",
        {
            "name": project["name"],
            "route": route,
            "color": discord.Color.green()
        }
    )
    
    states = load_states()
    operator_id = None
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == project["operator"]:
            operator_id = int(data.get("assigned_to", 0))
            break
    
    if operator_id:
        try:
            user = await bot.fetch_user(operator_id)
            embed = discord.Embed(
                title="✅ ПРОЕКТ ОДОБРЕН",
                description=f"Ваш проект трубопровода **«{project['name']}»** получил одобрение всех стран транзита!\n\n"
                            f"Строительство начнётся в ближайшее время.",
                color=discord.Color.green()
            )
            embed.add_field(name="Маршрут", value=route, inline=False)
            await user.send(embed=embed)
        except:
            pass


async def send_project_rejected_notification(bot, project: Dict, rejected_by: str):
    """Отправляет уведомление об отклонении проекта"""
    route = " → ".join([project["operator"]] + project["route_countries"])
    
    await send_pipeline_log(
        bot,
        "project_rejected",
        {
            "name": project["name"],
            "route": route,
            "rejected_by": rejected_by,
            "color": discord.Color.red()
        }
    )
    
    states = load_states()
    operator_id = None
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == project["operator"]:
            operator_id = int(data.get("assigned_to", 0))
            break
    
    if operator_id:
        try:
            user = await bot.fetch_user(operator_id)
            embed = discord.Embed(
                title="❌ ПРОЕКТ ОТКЛОНЁН",
                description=f"Ваш проект трубопровода **«{project['name']}»** отклонён страной **{rejected_by}**.\n\n"
                            f"Строительство отменено.",
                color=discord.Color.red()
            )
            embed.add_field(name="Маршрут", value=route, inline=False)
            await user.send(embed=embed)
        except:
            pass


async def process_expired_pipeline_projects(bot):
    """Обрабатывает просроченные проекты трубопроводов"""
    diplomacy = load_pipeline_diplomacy()
    now = datetime.now()
    expired = []
    
    for project in diplomacy["pending_projects"]:
        expires_at = datetime.fromisoformat(project["expires_at"])
        if expires_at <= now:
            expired.append(project)
    
    for project in expired:
        project["status"] = "expired"
        diplomacy["rejected_projects"].append(project)
        diplomacy["pending_projects"].remove(project)
        
        states = load_states()
        operator_id = None
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == project["operator"]:
                operator_id = int(data.get("assigned_to", 0))
                break
        
        if operator_id:
            try:
                user = await bot.fetch_user(operator_id)
                embed = discord.Embed(
                    title="⏰ ПРОЕКТ ПРОСРОЧЕН",
                    description=f"Ваш проект трубопровода **«{project['name']}»** автоматически отклонён из-за отсутствия ответа от стран транзита в течение {PROJECT_RESPONSE_TIMEOUT_HOURS} часов.",
                    color=discord.Color.orange()
                )
                await user.send(embed=embed)
            except:
                pass
        
        channel = bot.get_channel(PIPELINE_LOG_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="⏰ ПРОЕКТ ПРОСРОЧЕН",
                description=f"Проект **«{project['name']}»** автоматически отклонён из-за отсутствия ответа от стран транзита.",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            await channel.send(embed=embed)
    
    if expired:
        save_pipeline_diplomacy(diplomacy)
    
    return len(expired)


# ==================== ФУНКЦИИ УПРАВЛЕНИЯ ТРУБОПРОВОДАМИ ====================

def close_pipeline_section(pipeline: Dict, country: str, player_data: Dict) -> bool:
    if "closed_sections" not in pipeline:
        pipeline["closed_sections"] = {}
    pipeline["closed_sections"][country] = True
    if all(pipeline["closed_sections"].get(c, False) for c in pipeline.get("countries_through", [])):
        pipeline["status"] = "closed"
    data = load_pipelines()
    for i, p in enumerate(data["pipelines"]):
        if p["id"] == pipeline["id"]:
            data["pipelines"][i] = pipeline
            break
    save_pipelines(data)
    return True


def open_pipeline_section(pipeline: Dict, country: str, player_data: Dict) -> bool:
    if "closed_sections" not in pipeline:
        pipeline["closed_sections"] = {}
    pipeline["closed_sections"][country] = False
    if any(not pipeline["closed_sections"].get(c, False) for c in pipeline.get("countries_through", [])):
        pipeline["status"] = "active"
    data = load_pipelines()
    for i, p in enumerate(data["pipelines"]):
        if p["id"] == pipeline["id"]:
            data["pipelines"][i] = pipeline
            break
    save_pipelines(data)
    return True


def deploy_units_to_pipeline(pipeline: Dict, country: str, troops: int, vehicles: int,
                             drones: int, player_data: Dict, user_id: int) -> Tuple[bool, str, float, Dict]:
    current_base = calculate_base_control(pipeline, country)
    deployed = get_deployed_army_totals(pipeline, country)
    current_boost = calculate_control_from_military(deployed["infantry"], deployed["armored_vehicles"], deployed["drones"])
    current_control = min(100.0, current_base + current_boost)
    
    new_boost = calculate_control_from_military(deployed["infantry"] + troops, 
                                                 deployed["armored_vehicles"] + vehicles,
                                                 deployed["drones"] + drones)
    new_control = min(100.0, current_base + new_boost)
    increase = new_control - current_control
    
    if increase <= 0:
        return False, "Контроль уже максимальный", 0, {}
    
    cost_pp = calculate_control_increase_cost(pipeline, country, increase)
    if get_political_power(player_data) < cost_pp:
        return False, f"Недостаточно политической власти. Нужно: {cost_pp:.1f} ПВ", 0, {}
    
    spend_political_power(player_data, cost_pp)
    
    if troops > 0:
        player_data["state"]["army_size"] = max(0, player_data["state"].get("army_size", 0) - troops)
    if vehicles > 0:
        player_data["army"]["ground"]["armored_vehicles"] = max(0, player_data["army"]["ground"].get("armored_vehicles", 0) - vehicles)
    if drones > 0:
        attack_uav = player_data["army"]["air"].get("attack_uav", 0)
        recon_uav = player_data["army"]["air"].get("recon_uav", 0)
        total = attack_uav + recon_uav
        if total > 0:
            ratio = drones / total
            to_remove_attack = min(attack_uav, int(attack_uav * ratio))
            to_remove_recon = drones - to_remove_attack
            player_data["army"]["air"]["attack_uav"] = max(0, attack_uav - to_remove_attack)
            player_data["army"]["air"]["recon_uav"] = max(0, recon_uav - max(0, to_remove_recon))
    
    if "country_military" not in pipeline:
        pipeline["country_military"] = {}
    if "country_vehicles" not in pipeline:
        pipeline["country_vehicles"] = {}
    if "country_uav" not in pipeline:
        pipeline["country_uav"] = {}
    
    if country not in pipeline["country_military"]:
        pipeline["country_military"][country] = {"infantry": 0}
    if country not in pipeline["country_vehicles"]:
        pipeline["country_vehicles"][country] = {"armored_vehicles": 0}
    if country not in pipeline["country_uav"]:
        pipeline["country_uav"][country] = {"attack_uav": 0, "recon_uav": 0}
    
    pipeline["country_military"][country]["infantry"] = pipeline["country_military"][country].get("infantry", 0) + troops
    pipeline["country_vehicles"][country]["armored_vehicles"] = pipeline["country_vehicles"][country].get("armored_vehicles", 0) + vehicles
    
    attack_to_add = drones // 2
    recon_to_add = drones - attack_to_add
    pipeline["country_uav"][country]["attack_uav"] = pipeline["country_uav"][country].get("attack_uav", 0) + attack_to_add
    pipeline["country_uav"][country]["recon_uav"] = pipeline["country_uav"][country].get("recon_uav", 0) + recon_to_add
    
    pipeline["country_control"][country] = new_control
    
    old_security = pipeline.get("security_level", 0.5) * 100
    new_security = update_pipeline_security(pipeline)
    
    data = load_pipelines()
    for i, p in enumerate(data["pipelines"]):
        if p["id"] == pipeline["id"]:
            data["pipelines"][i] = pipeline
            break
    save_pipelines(data)
    
    return True, f"Контроль увеличен до {new_control:.2f}%", cost_pp, {
        "infantry": troops, "armored_vehicles": vehicles, "drones": drones,
        "new_security": new_security
    }


def withdraw_units_from_pipeline(pipeline: Dict, country: str, troops: int, vehicles: int,
                                  drones: int, player_data: Dict, user_id: int) -> Tuple[bool, str, Dict]:
    deployed = get_deployed_army_totals(pipeline, country)
    
    if troops > deployed["infantry"] or vehicles > deployed["armored_vehicles"] or drones > deployed["drones"]:
        return False, "Недостаточно войск для вывода", {}
    
    if troops > 0:
        player_data["state"]["army_size"] = player_data["state"].get("army_size", 0) + troops
    if vehicles > 0:
        player_data["army"]["ground"]["armored_vehicles"] = player_data["army"]["ground"].get("armored_vehicles", 0) + vehicles
    if drones > 0:
        attack_to_add = drones // 2
        recon_to_add = drones - attack_to_add
        player_data["army"]["air"]["attack_uav"] = player_data["army"]["air"].get("attack_uav", 0) + attack_to_add
        player_data["army"]["air"]["recon_uav"] = player_data["army"]["air"].get("recon_uav", 0) + recon_to_add
    
    if "country_military" in pipeline and country in pipeline["country_military"]:
        pipeline["country_military"][country]["infantry"] = max(0, pipeline["country_military"][country].get("infantry", 0) - troops)
    if "country_vehicles" in pipeline and country in pipeline["country_vehicles"]:
        pipeline["country_vehicles"][country]["armored_vehicles"] = max(0, pipeline["country_vehicles"][country].get("armored_vehicles", 0) - vehicles)
    if "country_uav" in pipeline and country in pipeline["country_uav"]:
        total_uav = pipeline["country_uav"][country].get("attack_uav", 0) + pipeline["country_uav"][country].get("recon_uav", 0)
        if total_uav > 0:
            ratio = drones / total_uav
            attack_remove = min(pipeline["country_uav"][country].get("attack_uav", 0), int(pipeline["country_uav"][country].get("attack_uav", 0) * ratio))
            recon_remove = drones - attack_remove
            pipeline["country_uav"][country]["attack_uav"] = max(0, pipeline["country_uav"][country].get("attack_uav", 0) - attack_remove)
            pipeline["country_uav"][country]["recon_uav"] = max(0, pipeline["country_uav"][country].get("recon_uav", 0) - recon_remove)
    
    current_base = calculate_base_control(pipeline, country)
    new_boost = calculate_control_from_military(
        pipeline.get("country_military", {}).get(country, {}).get("infantry", 0),
        pipeline.get("country_vehicles", {}).get(country, {}).get("armored_vehicles", 0),
        pipeline.get("country_uav", {}).get(country, {}).get("attack_uav", 0) + pipeline.get("country_uav", {}).get(country, {}).get("recon_uav", 0))
    new_control = min(100.0, current_base + new_boost)
    old_control = pipeline["country_control"].get(country, 0)
    pipeline["country_control"][country] = new_control
    
    old_security = pipeline.get("security_level", 0.5) * 100
    new_security = update_pipeline_security(pipeline)
    
    data = load_pipelines()
    for i, p in enumerate(data["pipelines"]):
        if p["id"] == pipeline["id"]:
            data["pipelines"][i] = pipeline
            break
    save_pipelines(data)
    
    return True, "Войска выведены", {
        "infantry": troops, "armored_vehicles": vehicles, "drones": drones,
        "control_decrease": old_control - new_control,
        "new_security": new_security
    }


def dismantle_section(pipeline: Dict, country: str, length: int, player_data: Dict, user_id: int, bot) -> Tuple[bool, str, float, int]:
    if length <= 0 or length > get_country_length(pipeline, country):
        return False, "Некорректная длина", 0, 0
    
    cost_return, time_seconds = calculate_dismantle_cost(pipeline, length)
    cost_return_dollars = cost_return * 1_000_000
    time_game_days = real_seconds_to_game_days(time_seconds)
    
    constr = load_pipeline_construction()
    constr["active_dismantles"].append({
        "id": f"dismantle_{pipeline['id']}_{datetime.now().timestamp()}",
        "pipeline_id": pipeline["id"],
        "pipeline_name": pipeline["name"],
        "country": country,
        "length": length,
        "cost_return": cost_return_dollars,
        "start_time": str(datetime.now()),
        "completion_time": str(datetime.now() + timedelta(seconds=time_seconds)),
        "dismantle_game_days": time_game_days,
        "status": "in_progress"
    })
    save_pipeline_construction(constr)
    
    land_len = get_country_land_length(pipeline, country)
    sea_len = get_country_sea_length(pipeline, country)
    
    if land_len >= length:
        pipeline["country_length"][country]["land"] = land_len - length
    else:
        pipeline["country_length"][country]["land"] = 0
        pipeline["country_length"][country]["sea"] = max(0, sea_len - (length - land_len))
    
    pipeline["total_length"] = max(0, pipeline["total_length"] - length)
    pipeline["land_length"] = max(0, pipeline["land_length"] - min(land_len, length))
    pipeline["sea_length"] = max(0, pipeline["sea_length"] - min(sea_len, length))
    
    for c in pipeline["countries_through"]:
        pipeline["country_control"][c] = calculate_base_control(pipeline, c)
        mil = pipeline.get("country_military", {}).get(c, {}).get("infantry", 0)
        veh = pipeline.get("country_vehicles", {}).get(c, {}).get("armored_vehicles", 0)
        drones = (pipeline.get("country_uav", {}).get(c, {}).get("attack_uav", 0) + 
                  pipeline.get("country_uav", {}).get(c, {}).get("recon_uav", 0))
        pipeline["country_control"][c] = min(100.0, pipeline["country_control"][c] + calculate_control_from_military(mil, veh, drones))
    
    update_pipeline_security(pipeline)
    
    if get_country_length(pipeline, country) <= 0:
        pipeline["countries_through"].remove(country)
        pipeline["closed_sections"].pop(country, None)
        pipeline["country_control"].pop(country, None)
        pipeline["country_military"].pop(country, None)
        pipeline["country_vehicles"].pop(country, None)
        pipeline["country_uav"].pop(country, None)
        pipeline["country_length"].pop(country, None)
    
    if pipeline["total_length"] <= 0:
        data = load_pipelines()
        data["pipelines"] = [p for p in data["pipelines"] if p["id"] != pipeline["id"]]
        save_pipelines(data)
    else:
        data = load_pipelines()
        for i, p in enumerate(data["pipelines"]):
            if p["id"] == pipeline["id"]:
                data["pipelines"][i] = pipeline
                break
        save_pipelines(data)
    
    return True, f"Демонтаж {length} км начат", cost_return_dollars, time_seconds


def apply_damage_to_pipeline(pipeline_id: str, damage_km: int, resource_loss: float = None) -> Dict:
    data = load_pipelines()
    pipeline = None
    for p in data["pipelines"]:
        if p["id"] == pipeline_id:
            pipeline = p
            break
    
    if not pipeline:
        return {"success": False, "message": "Трубопровод не найден"}
    
    old_damage = pipeline.get("damage", 0)
    pipeline["damage"] = min(pipeline.get("total_length", 1), pipeline.get("damage", 0) + damage_km)
    
    if pipeline["damage"] > pipeline["total_length"] * 0.5:
        pipeline["status"] = "damaged"
    
    logs = load_pipeline_logs()
    logs["logs"].append({
        "timestamp": str(datetime.now()),
        "pipeline_id": pipeline_id,
        "pipeline_name": pipeline["name"],
        "event": "damage",
        "damage_km": damage_km,
        "total_damage": pipeline["damage"],
        "resource_loss": resource_loss
    })
    save_pipeline_logs(logs)
    
    for i, p in enumerate(data["pipelines"]):
        if p["id"] == pipeline_id:
            data["pipelines"][i] = pipeline
            break
    save_pipelines(data)
    
    return {
        "success": True,
        "pipeline_name": pipeline["name"],
        "old_damage": old_damage,
        "new_damage": pipeline["damage"],
        "total_length": pipeline["total_length"],
        "damage_percent": (pipeline["damage"] / pipeline["total_length"]) * 100
    }


# ==================== КЛАСС ДЛЯ КНОПОК ПРОЕКТА ====================

class PipelineProjectView(View):
    def __init__(self, project_id: str, country: str):
        super().__init__(timeout=PROJECT_RESPONSE_TIMEOUT_HOURS * 3600)
        self.project_id = project_id
        self.country = country
    
    @discord.ui.button(label="Принять проект", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.get_user_id():
            await interaction.response.send_message("Это не ваш запрос!", ephemeral=True)
            return
        
        success, msg = approve_pipeline_project(self.project_id, self.country, interaction.user.id)
        
        if success:
            diplomacy = load_pipeline_diplomacy()
            project = None
            for p in diplomacy["approved_projects"]:
                if p["id"] == self.project_id:
                    project = p
                    break
            
            if project:
                await send_project_approved_notification(interaction.client, project)
            
            embed = discord.Embed(
                title="✅ ПРОЕКТ ПРИНЯТ",
                description=msg,
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
    
    @discord.ui.button(label="Отказать", style=discord.ButtonStyle.danger)
    async def reject_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.get_user_id():
            await interaction.response.send_message("Это не ваш запрос!", ephemeral=True)
            return
        
        success, msg = reject_pipeline_project(self.project_id, self.country, interaction.user.id)
        
        if success:
            diplomacy = load_pipeline_diplomacy()
            project = None
            for p in diplomacy["rejected_projects"]:
                if p["id"] == self.project_id:
                    project = p
                    break
            
            if project:
                await send_project_rejected_notification(interaction.client, project, self.country)
            
            embed = discord.Embed(
                title="❌ ПРОЕКТ ОТКЛОНЁН",
                description=msg,
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message(f"❌ {msg}", ephemeral=True)
    
    def get_user_id(self) -> int:
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.country:
                return int(data.get("assigned_to", 0))
        return 0


# ==================== КЛАССЫ ДЛЯ СОЗДАНИЯ ПРОЕКТА ====================

async def show_create_pipeline_menu(interaction, user_id: int):
    states = load_states()
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        await interaction.response.send_message("У вас нет государства!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏗️ СОЗДАНИЕ НОВОГО ТРУБОПРОВОДА",
        description="Выберите тип трубопровода",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=get_random_construction_image())
    
    view = PipelineTypeView(user_id, player_data)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PipelineTypeView(View):
    def __init__(self, user_id, player_data):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data

    @discord.ui.button(label="Нефтепровод", style=discord.ButtonStyle.primary)
    async def oil_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_form(i, self.user_id, self.player_data, "oil")

    @discord.ui.button(label="Газопровод", style=discord.ButtonStyle.primary)
    async def gas_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_form(i, self.user_id, self.player_data, "gas")

    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_menu(i, self.user_id)


async def show_pipeline_form(interaction, user_id, player_data, pipeline_type):
    states = load_states()
    countries = []
    for data in states["players"].values():
        country = data["state"]["statename"]
        if country != player_data["state"]["statename"]:
            countries.append(country)
    
    if not countries:
        await interaction.response.send_message("Нет других стран для строительства трубопровода!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏗️ НОВЫЙ ПРОЕКТ",
        description=f"Тип: **{'Нефтепровод' if pipeline_type == 'oil' else 'Газопровод'}**\n\n"
                    f"**Шаг 1:** Выберите страны транзита",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=get_random_construction_image())
    
    view = PipelineRouteView(user_id, player_data, pipeline_type, countries)
    await interaction.response.edit_message(embed=embed, view=view)


class PipelineRouteView(View):
    def __init__(self, user_id, player_data, pipeline_type, all_countries):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.pipeline_type = pipeline_type
        self.all_countries = all_countries
        self.selected_countries = []
        
        options = [discord.SelectOption(label=c, value=c) for c in all_countries[:25]]
        self.select = Select(
            placeholder="Выберите страны транзита (можно несколько)", 
            min_values=1, 
            max_values=min(10, len(all_countries)), 
            options=options
        )
        self.select.callback = self.country_select_callback
        self.add_item(self.select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def country_select_callback(self, interaction: discord.Interaction):
        self.selected_countries = self.select.values
        
        embed = discord.Embed(
            title="🏗️ НОВЫЙ ПРОЕКТ",
            description=f"Тип: **{'Нефтепровод' if self.pipeline_type == 'oil' else 'Газопровод'}**\n\n"
                        f"✅ Выбраны страны транзита: **{', '.join(self.selected_countries)}**\n\n"
                        f"**Шаг 2:** Введите параметры трубопровода",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_construction_image())
        
        view = PipelineParamsView(self.user_id, self.player_data, self.pipeline_type, self.selected_countries)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_create_pipeline_menu(interaction, self.user_id)


class PipelineParamsView(View):
    def __init__(self, user_id, player_data, pipeline_type, route_countries):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.pipeline_type = pipeline_type
        self.route_countries = route_countries
        
        input_btn = Button(label="Ввести параметры", style=discord.ButtonStyle.primary)
        input_btn.callback = self.input_callback
        self.add_item(input_btn)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def input_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        modal = PipelineParamsModal(self.user_id, self.player_data, self.pipeline_type, self.route_countries)
        await interaction.response.send_modal(modal)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        states = load_states()
        countries = []
        for data in states["players"].values():
            country = data["state"]["statename"]
            if country != self.player_data["state"]["statename"]:
                countries.append(country)
        
        embed = discord.Embed(
            title="🏗️ НОВЫЙ ПРОЕКТ",
            description=f"Тип: **{'Нефтепровод' if self.pipeline_type == 'oil' else 'Газопровод'}**\n\n"
                        f"**Шаг 1:** Выберите страны транзита",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_construction_image())
        
        view = PipelineRouteView(self.user_id, self.player_data, self.pipeline_type, countries)
        await interaction.response.edit_message(embed=embed, view=view)


class PipelineParamsModal(Modal, title="Параметры трубопровода"):
    def __init__(self, user_id, player_data, pipeline_type, route_countries):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.pipeline_type = pipeline_type
        self.route_countries = route_countries
        
        self.name = TextInput(
            label="Название трубопровода",
            placeholder="Например: Каспийский трубопровод",
            required=True,
            max_length=50
        )
        self.add_item(self.name)
        
        self.land_length = TextInput(
            label="Протяжённость по суше (км)",
            placeholder="Например: 1000",
            required=True
        )
        self.add_item(self.land_length)
        
        self.sea_length = TextInput(
            label="Протяжённость по морю (км)",
            placeholder="Например: 200 (или 0)",
            required=True,
            default="0"
        )
        self.add_item(self.sea_length)
    
    async def on_submit(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            land = int(self.land_length.value)
            sea = int(self.sea_length.value)
        except ValueError:
            await i.response.send_message("Введите корректные числа!", ephemeral=True)
            return
        
        if land <= 0 or land > 10000:
            await i.response.send_message("Протяжённость по суше должна быть от 1 до 10000 км!", ephemeral=True)
            return
        
        if sea < 0 or sea > 5000:
            await i.response.send_message("Протяжённость по морю должна быть от 0 до 5000 км!", ephemeral=True)
            return
        
        if land + sea > 10000:
            await i.response.send_message(f"Общая протяжённость не должна превышать 10000 км! Сейчас: {land + sea} км", ephemeral=True)
            return
        
        type_data = PIPELINE_TYPES[self.pipeline_type]
        total_cost = (land * type_data["land_cost_per_km"] + sea * type_data["sea_cost_per_km"]) * 1_000_000
        
        if self.player_data["economy"]["budget"] < total_cost:
            await i.response.send_message(f"Недостаточно средств! Нужно: {format_billion(total_cost)}", ephemeral=True)
            return
        
        states = load_states()
        existing = [data["state"]["statename"] for data in states["players"].values()]
        for country in self.route_countries:
            if country not in existing:
                await i.response.send_message(f"Страна {country} не существует в игре!", ephemeral=True)
                return
        
        # Проверяем, что все страны транзита заняты игроками
        occupied_players = {}
        for data in states["players"].values():
            country = data["state"]["statename"]
            assigned_to = data.get("assigned_to")
            if assigned_to:
                occupied_players[country] = assigned_to
        
        for country in self.route_countries:
            if country not in occupied_players:
                await i.response.send_message(f"Страна {country} не имеет назначенного игрока! Строительство невозможно.", ephemeral=True)
                return
        
        # Проверяем минимальную длину трубопровода (географическое расстояние)
        can_build, dist_msg = can_build_pipeline(
            self.player_data["state"]["statename"],
            self.route_countries,
            land,
            sea
        )
        if not can_build:
            await i.response.send_message(f"❌ {dist_msg}", ephemeral=True)
            return
        
        project = create_pipeline_project(
            self.player_data["state"]["statename"],
            self.user_id,
            self.name.value,
            self.pipeline_type,
            land,
            sea,
            self.route_countries
        )
        
        self.player_data["economy"]["budget"] -= total_cost
        
        for pid, data in states["players"].items():
            if data.get("assigned_to") == str(self.user_id):
                data["economy"]["budget"] = self.player_data["economy"]["budget"]
                break
        save_states(states)
        
        await send_pipeline_project_notification(i.client, project)
        
        route_text = " → ".join([self.player_data["state"]["statename"]] + self.route_countries)
        
        embed = discord.Embed(
            title="✅ ПРОЕКТ ОТПРАВЛЕН НА СОГЛАСОВАНИЕ",
            description=f"Проект **«{self.name.value}»** отправлен на рассмотрение странам транзита.\n\n"
                        f"Ожидайте ответа в течение {PROJECT_RESPONSE_TIMEOUT_HOURS} часов.",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_construction_image())
        embed.add_field(name="ID проекта", value=project["id"], inline=True)
        embed.add_field(name="Тип", value="Нефтепровод" if self.pipeline_type == "oil" else "Газопровод", inline=True)
        embed.add_field(name="Протяжённость", value=f"{land + sea} км (суша: {land}, море: {sea})", inline=True)
        embed.add_field(name="Стоимость", value=format_billion(total_cost), inline=True)
        embed.add_field(name="Маршрут", value=route_text, inline=False)
        
        await i.response.send_message(embed=embed, ephemeral=True)


async def show_pipeline_projects_menu(interaction, user_id: int):
    states = load_states()
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        await interaction.response.send_message("У вас нет государства!", ephemeral=True)
        return
    
    country = player_data["state"]["statename"]
    pending = get_country_pending_projects(country)
    own_projects = get_operator_projects(country)
    
    embed = discord.Embed(
        title="🏗️ ПРОЕКТЫ ТРУБОПРОВОДОВ",
        description=f"Страна: **{country}**",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=get_random_construction_image())
    
    if pending:
        text = ""
        for p in pending:
            type_name = "Нефтепровод" if p["type"] == "oil" else "Газопровод"
            expires = datetime.fromisoformat(p["expires_at"]).strftime("%d.%m.%Y %H:%M")
            text += f"**{p['name']}** ({type_name})\n"
            text += f"  Оператор: {p['operator']}\n"
            text += f"  Срок ответа: {expires}\n"
            text += f"  ID: `{p['id']}`\n\n"
        embed.add_field(name="📋 ОЖИДАЮТ ВАШЕГО РЕШЕНИЯ", value=text[:1024], inline=False)
    else:
        embed.add_field(name="📋 ОЖИДАЮТ ВАШЕГО РЕШЕНИЯ", value="Нет проектов, ожидающих вашего решения", inline=False)
    
    if own_projects:
        text = ""
        for p in own_projects:
            status_text = {
                "pending": "⏳ Ожидает согласования",
                "approved": "✅ Одобрен",
                "rejected": "❌ Отклонён"
            }.get(p["current_status"], p["current_status"])
            type_name = "Нефтепровод" if p["type"] == "oil" else "Газопровод"
            text += f"**{p['name']}** ({type_name})\n"
            text += f"  Статус: {status_text}\n"
            text += f"  ID: `{p['id']}`\n\n"
        embed.add_field(name="🏭 ВАШИ ПРОЕКТЫ", value=text[:1024], inline=False)
    
    view = PipelineProjectsView(user_id, player_data)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PipelineProjectsView(View):
    def __init__(self, user_id, player_data):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data

    @discord.ui.button(label="Создать проект", style=discord.ButtonStyle.success)
    async def create_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_create_pipeline_menu(i, self.user_id)
    
    @discord.ui.button(label="Удалить проект", style=discord.ButtonStyle.danger)
    async def delete_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        own_projects = get_operator_projects(self.player_data["state"]["statename"])
        pending_projects = [p for p in own_projects if p["current_status"] == "pending"]
        
        if not pending_projects:
            await i.response.send_message("У вас нет проектов, ожидающих согласования!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🗑️ УДАЛЕНИЕ ПРОЕКТА",
            description="Выберите проект для удаления",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_construction_image())
        
        view = DeleteProjectView(self.user_id, self.player_data, pending_projects)
        await i.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Обновить", style=discord.ButtonStyle.secondary)
    async def refresh_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_projects_menu(i, self.user_id)
    
    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_menu(i, self.user_id)


class DeleteProjectView(View):
    def __init__(self, user_id, player_data, projects):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.projects = projects
        
        for p in projects[:5]:
            btn = Button(label=f"{p['name']} ({p['type']})", style=discord.ButtonStyle.danger)
            btn.callback = self._make_callback(p)
            self.add_item(btn)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    def _make_callback(self, project):
        async def cb(i):
            if i.user.id != self.user_id:
                await i.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            await confirm_delete_project(i, self.user_id, self.player_data, project)
        return cb
    
    async def back_callback(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_projects_menu(i, self.user_id)


async def confirm_delete_project(interaction, user_id, player_data, project):
    total_cost = project.get("total_cost", 0)
    
    embed = discord.Embed(
        title="🗑️ ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ",
        description=f"Вы уверены, что хотите удалить проект **«{project['name']}»**?\n\n"
                    f"Это действие нельзя отменить.\n\n"
                    f"💰 Будет возвращено: **{format_billion(total_cost)}**",
        color=discord.Color.red()
    )
    embed.add_field(name="ID проекта", value=project["id"], inline=True)
    embed.add_field(name="Тип", value="Нефтепровод" if project["type"] == "oil" else "Газопровод", inline=True)
    embed.add_field(name="Маршрут", value=f"{project['operator']} → " + " → ".join(project["route_countries"]), inline=False)
    
    view = ConfirmDeleteView(user_id, player_data, project)
    await interaction.response.edit_message(embed=embed, view=view)


class ConfirmDeleteView(View):
    def __init__(self, user_id, player_data, project):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
        self.project = project
    
    @discord.ui.button(label="✅ Да, удалить", style=discord.ButtonStyle.danger)
    async def confirm_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        success, msg = delete_pipeline_project(self.project["id"])
        
        if success:
            if self.project.get("current_status") == "pending" or self.project.get("status") == "pending":
                total_cost = self.project.get("total_cost", 0)
                if total_cost > 0:
                    states = load_states()
                    for pid, data in states["players"].items():
                        if data.get("assigned_to") == str(self.user_id):
                            data["economy"]["budget"] += total_cost
                            break
                    save_states(states)
            
            embed = discord.Embed(
                title="✅ ПРОЕКТ УДАЛЁН",
                description=f"Проект **«{self.project['name']}»** успешно удалён.\n\n"
                            f"Средства возвращены в бюджет.",
                color=discord.Color.green()
            )
            await i.response.edit_message(embed=embed, view=None)
            await show_pipeline_projects_menu(i, self.user_id)
        else:
            await i.response.send_message(f"❌ {msg}", ephemeral=True)
    
    @discord.ui.button(label="❌ Нет, отмена", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_projects_menu(i, self.user_id)


# ==================== ОСНОВНОЕ МЕНЮ ТРУБОПРОВОДОВ ====================

async def show_pipeline_menu(ctx, user_id: int):
    states = load_states()
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        if hasattr(ctx, 'response'):
            await ctx.response.send_message("У вас нет государства!", ephemeral=True)
        else:
            await ctx.send("У вас нет государства!")
        return
    
    country = player_data["state"]["statename"]
    operated = get_pipelines_by_operator(country)
    transit = [p for p in get_pipelines_through_country(country) if p["operator"] != country]
    army = get_army_totals(player_data)
    max_d = get_max_deployable_units(player_data)
    
    embed = discord.Embed(
        title=f"{EMOJIS['gas']}{EMOJIS['oil']} ТРУБОПРОВОДНАЯ СИСТЕМА {EMOJIS['gas']}{EMOJIS['oil']}",
        description=f"Управление транснациональными трубопроводами | {country}",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=PIPELINE_IMAGE_URL)
    
    embed.add_field(
        name="ИНФОРМАЦИЯ",
        value="Трубопроводы проходят через территории нескольких стран.\n"
              "Каждая страна управляет только своим участком:\n"
              "• Закрыть/открыть свой участок\n"
              "• Усилить контроль войсками на своём участке\n"
              "• Разобрать свой участок (вернёт часть стоимости)\n"
              f"Войска дают контроль: 1 солдат = +{TROOP_CONTROL_BOOST*100:.2f}%, "
              f"1 бронемашина = +{VEHICLE_CONTROL_BOOST*100:.0f}%, "
              f"1 дрон = +{DRONE_CONTROL_BOOST*100:.1f}%.\n"
              f"Максимум: {MAX_ARMY_PERCENT}% от каждого типа войск.\n"
              f"{EMOJIS['police']} Безопасность трубопровода рассчитывается как средневзвешенный контроль по всем странам (вес = длина участка).\n"
              f"Чем выше контроль в каждой стране, тем безопаснее весь трубопровод.",
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJIS['soldier']} ДОСТУПНЫЕ ВОЙСКА",
        value=f"{EMOJIS['soldier']} Пехота: {army['infantry']} (макс для размещения: {max_d['infantry']})\n"
              f"{EMOJIS['armored']} Бронетехника: {army['armored_vehicles']} (макс: {max_d['armored_vehicles']})\n"
              f"{EMOJIS['drone']} Дроны: {army['drones']} (макс: {max_d['drones']})",
        inline=False
    )
    
    if operated:
        text = ""
        for p in operated[:5]:
            t = PIPELINE_TYPES[p["type"]]
            status = "АКТИВЕН" if p["status"] == "active" else "ЗАКРЫТ" if p["status"] == "closed" else "ПОВРЕЖДЁН"
            dmg = (p["damage"] / p["total_length"]) * 100 if p["total_length"] > 0 else 0
            text += f"**{p['name']}** ({t['name']})\n"
            text += f"  Протяжённость: {p['total_length']} км (суша: {p['land_length']}, море: {p['sea_length']})\n"
            text += f"  Статус: {status}\n"
            text += f"  {EMOJIS['police']} Безопасность: {p['security_level']*100:.0f}%\n"
            if dmg > 0:
                text += f"  Повреждения: {p['damage']} км ({dmg:.1f}%)\n"
            text += f"  Закрытые участки: {len([c for c, s in p['closed_sections'].items() if s])}/{len(p['countries_through'])}\n"
            text += f"  Контроль:\n"
            for c in p["countries_through"]:
                flag = COUNTRY_FLAGS.get(c, "🏳️")
                control = p["country_control"].get(c, 0)
                deployed = get_deployed_army_totals(p, c)
                len_c = get_country_length(p, c)
                sea_c = get_country_sea_length(p, c)
                text += f"    {flag} {c}: {control:.0f}% ({len_c} км" + (f", море: {sea_c} км" if sea_c > 0 else "")
                if deployed["infantry"] > 0 or deployed["armored_vehicles"] > 0 or deployed["drones"] > 0:
                    text += f", войска: {deployed['infantry']}п {deployed['armored_vehicles']}б {deployed['drones']}д"
                text += ")\n"
            text += "\n"
        embed.add_field(name=f"{EMOJIS['military']} ВАШИ ТРУБОПРОВОДЫ (оператор)", value=text[:1024], inline=False)
    
    if transit:
        text = ""
        for p in transit[:5]:
            t = PIPELINE_TYPES[p["type"]]
            closed = p["closed_sections"].get(country, False)
            control = p["country_control"].get(country, 0)
            deployed = get_deployed_army_totals(p, country)
            len_c = get_country_length(p, country)
            sea_c = get_country_sea_length(p, country)
            text += f"**{p['name']}** ({t['name']}) - оператор: {p['operator']}" + (" ЗАКРЫТ" if closed else "") + "\n"
            text += f"  Ваш участок: {len_c} км" + (f" (море: {sea_c} км)" if sea_c > 0 else "") + "\n"
            text += f"  Ваш контроль: {COUNTRY_FLAGS.get(country, '🏳️')} {control:.0f}%"
            if deployed["infantry"] > 0 or deployed["armored_vehicles"] > 0 or deployed["drones"] > 0:
                text += f" (войска: {deployed['infantry']}п {deployed['armored_vehicles']}б {deployed['drones']}д)"
            text += "\n\n"
        embed.add_field(name=f"{EMOJIS['worker']} ТРАНЗИТНЫЕ ТРУБОПРОВОДЫ", value=text[:1024], inline=False)
    
    if not operated and not transit:
        embed.add_field(name="Информация", value="Ваша страна не участвует в трубопроводных проектах", inline=False)
    
    view = PipelineMainView(user_id, player_data, country, operated, transit)
    
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx.send(embed=embed, view=view, ephemeral=True)


class PipelineMainView(View):
    def __init__(self, user_id, player_data, country, operated, transit):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country = country
        self.operated = operated
        self.transit = transit

    @discord.ui.button(label="Мои трубопроводы", style=discord.ButtonStyle.primary)
    async def my_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        if not self.operated:
            await i.response.send_message("У вас нет трубопроводов, где вы являетесь оператором!", ephemeral=True)
            return
        embed = discord.Embed(title="ВЫБОР ТРУБОПРОВОДА", description="Выберите трубопровод для управления", color=DARK_THEME_COLOR)
        embed.set_image(url=PIPELINE_IMAGE_URL)
        view = PipelineSelectView(self.user_id, self.player_data, self.country, self.operated, "operator")
        await i.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Транзитные", style=discord.ButtonStyle.secondary)
    async def transit_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        if not self.transit:
            await i.response.send_message("Через вашу страну не проходят трубопроводы!", ephemeral=True)
            return
        embed = discord.Embed(title="ТРАНЗИТНЫЕ ТРУБОПРОВОДЫ", description="Выберите трубопровод для управления", color=DARK_THEME_COLOR)
        embed.set_image(url=PIPELINE_IMAGE_URL)
        view = PipelineSelectView(self.user_id, self.player_data, self.country, self.transit, "transit")
        await i.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Проекты", style=discord.ButtonStyle.success)
    async def projects_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_projects_menu(i, self.user_id)

    @discord.ui.button(label="История", style=discord.ButtonStyle.secondary)
    async def history_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        logs = load_pipeline_logs()
        embed = discord.Embed(title="ИСТОРИЯ ТРУБОПРОВОДОВ", color=DARK_THEME_COLOR)
        embed.set_image(url=get_random_other_image())
        if logs["logs"]:
            for log in logs["logs"][-10:]:
                date = datetime.fromisoformat(log["timestamp"]).strftime("%d.%m %H:%M")
                embed.add_field(name=f"{date} - {log.get('pipeline_name', 'Неизвестно')}", value=log.get("event", "Событие"), inline=False)
        else:
            embed.description = "История пуста"
        await i.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        try:
            from bot import StateButtons
            view = StateButtons(self.user_id, self.player_data["state"]["statename"], self.player_data)
            embed = discord.Embed(
                title=f"{self.player_data['state']['statename']}",
                description=f"Лидер: {i.user.mention}",
                color=DARK_THEME_COLOR
            )
            s = self.player_data["state"]
            p = self.player_data["politics"]
            e = self.player_data["economy"]
            embed.add_field(name="👥 Население", value=f"{format_number(s['population'])} чел.", inline=True)
            embed.add_field(name="🗺️ Территория", value=f"{format_number(s['territory'])} км²", inline=True)
            embed.add_field(name="⚖️ Стабильность", value=f"{s['stability']:.1f}%", inline=True)
            embed.add_field(name="🏛️ Правительство", value=s['government_type'], inline=True)
            embed.add_field(name="🎭 Правящая партия", value=p['ruling_party'], inline=True)
            embed.add_field(name="📊 Популярность", value=f"{p['popularity']:.1f}%", inline=True)
            embed.add_field(name="💰 ВВП", value=format_billion(e['gdp']), inline=True)
            embed.add_field(name="💵 Бюджет", value=format_billion(e['budget']), inline=True)
            await i.response.edit_message(embed=embed, view=view)
        except:
            await show_pipeline_menu(i, self.user_id)


class PipelineSelectView(View):
    def __init__(self, user_id, player_data, country, pipelines, mode):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country = country
        self.pipelines = pipelines
        self.mode = mode
        
        for p in pipelines[:5]:
            btn = Button(label=p["name"], style=discord.ButtonStyle.secondary)
            btn.callback = self._make_callback(p)
            self.add_item(btn)
        
        back = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back.callback = self.back
        self.add_item(back)
    
    def _make_callback(self, p):
        async def cb(i):
            if i.user.id != self.user_id:
                await i.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            await show_pipeline_detail(i, self.user_id, self.player_data, self.country, p, self.mode)
        return cb
    
    async def back(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_menu(i, self.user_id)


async def show_pipeline_detail(interaction, user_id, player_data, country, pipeline, mode):
    t = PIPELINE_TYPES[pipeline["type"]]
    daily = calculate_daily_flow(pipeline)
    maint = calculate_annual_maintenance(pipeline)
    dmg_percent = (pipeline["damage"] / pipeline["total_length"]) * 100 if pipeline["total_length"] > 0 else 0
    
    type_emoji = EMOJIS['oil'] if pipeline["type"] == "oil" else EMOJIS['gas']
    
    embed = discord.Embed(
        title=f"{type_emoji} {pipeline['name']} {type_emoji}",
        description=f"Оператор: **{pipeline['operator']}**\nТип: {t['name']}",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=PIPELINE_IMAGE_URL)
    
    embed.add_field(name="Протяжённость", value=f"{pipeline['total_length']} км", inline=True)
    embed.add_field(name="По суше", value=f"{pipeline['land_length']} км", inline=True)
    embed.add_field(name="По морю", value=f"{pipeline['sea_length']} км", inline=True)
    
    status = "АКТИВЕН" if pipeline["status"] == "active" else "ЗАКРЫТ" if pipeline["status"] == "closed" else "ПОВРЕЖДЁН"
    embed.add_field(name="Статус", value=status, inline=True)
    embed.add_field(name="Пропускная способность", value=f"{daily:.1f} ед./день", inline=True)
    embed.add_field(name=f"{EMOJIS['police']} Безопасность", value=f"{pipeline['security_level']*100:.0f}%", inline=True)
    
    if dmg_percent > 0:
        embed.add_field(name="Повреждения", value=f"{pipeline['damage']} км ({dmg_percent:.1f}%)", inline=True)
    
    embed.add_field(name="Годовое обслуживание", value=format_billion(maint * 1_000_000), inline=True)
    
    route = " → ".join([pipeline["operator"]] + [c for c in pipeline["countries_through"] if c != pipeline["operator"]])
    embed.add_field(name="Маршрут", value=route, inline=False)
    
    control_text = ""
    for c in pipeline["countries_through"]:
        flag = COUNTRY_FLAGS.get(c, "🏳️")
        control = pipeline["country_control"].get(c, 0)
        deployed = get_deployed_army_totals(pipeline, c)
        len_c = get_country_length(pipeline, c)
        sea_c = get_country_sea_length(pipeline, c)
        control_text += f"{flag} **{c}**: {control:.0f}% ({len_c} км" + (f", море: {sea_c} км" if sea_c > 0 else "")
        if deployed["infantry"] > 0 or deployed["armored_vehicles"] > 0 or deployed["drones"] > 0:
            control_text += f", войска: {deployed['infantry']}п {deployed['armored_vehicles']}б {deployed['drones']}д"
        control_text += ")\n"
    embed.add_field(name="КОНТРОЛЬ", value=control_text[:1024], inline=False)
    
    closed_text = ""
    for c, closed in pipeline.get("closed_sections", {}).items():
        closed_text += f"{c}: {'ЗАКРЫТ' if closed else 'ОТКРЫТ'}\n"
    if closed_text:
        embed.add_field(name="СТАТУС УЧАСТКОВ", value=closed_text, inline=False)
    
    view = PipelineDetailView(user_id, player_data, country, pipeline, mode)
    await interaction.response.edit_message(embed=embed, view=view)


class PipelineDetailView(View):
    def __init__(self, user_id, player_data, country, pipeline, mode):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country = country
        self.pipeline = pipeline
        self.mode = mode
        self.bot = None

    @discord.ui.button(label="Закрыть участок", style=discord.ButtonStyle.danger)
    async def close_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        if self.country not in self.pipeline.get("countries_through", []):
            await i.response.send_message("Трубопровод не проходит через вашу территорию!", ephemeral=True)
            return
        if self.pipeline.get("closed_sections", {}).get(self.country, False):
            await i.response.send_message("Участок уже закрыт!", ephemeral=True)
            return
        
        land = get_country_land_length(self.pipeline, self.country)
        sea = get_country_sea_length(self.pipeline, self.country)
        
        embed = discord.Embed(
            title=f"{EMOJIS['military']} ПОДТВЕРЖДЕНИЕ ЗАКРЫТИЯ",
            description=f"Вы собираетесь закрыть участок трубопровода **{self.pipeline['name']}** на территории {self.country}",
            color=discord.Color.orange()
        )
        embed.set_image(url=PIPELINE_CLOSE_IMAGE_URL)
        embed.add_field(name="Оператор", value=self.pipeline["operator"], inline=True)
        embed.add_field(name="Протяжённость участка", value=f"{land + sea} км (суша: {land}, море: {sea})", inline=True)
        embed.add_field(name="Последствия", value="Участок будет закрыт до открытия. Транзит ресурсов прекратится.", inline=False)
        
        view = CloseConfirmView(self.user_id, self.player_data, self.country, self.pipeline, self.mode, i.client)
        await i.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Открыть участок", style=discord.ButtonStyle.success)
    async def open_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        if self.country not in self.pipeline.get("countries_through", []):
            await i.response.send_message("Трубопровод не проходит через вашу территорию!", ephemeral=True)
            return
        if not self.pipeline.get("closed_sections", {}).get(self.country, False):
            await i.response.send_message("Участок не закрыт!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"{EMOJIS['oil']}{EMOJIS['gas']} ПОДТВЕРЖДЕНИЕ ОТКРЫТИЯ",
            description=f"Вы собираетесь открыть участок трубопровода **{self.pipeline['name']}** на территории {self.country}",
            color=discord.Color.green()
        )
        embed.add_field(name="Оператор", value=self.pipeline["operator"], inline=True)
        
        view = OpenConfirmView(self.user_id, self.player_data, self.country, self.pipeline, self.mode, i.client)
        await i.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Усилить контроль", style=discord.ButtonStyle.primary)
    async def control_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        if self.country not in self.pipeline.get("countries_through", []):
            await i.response.send_message("Трубопровод не проходит через вашу территорию!", ephemeral=True)
            return
        if self.pipeline.get("country_control", {}).get(self.country, 0) >= 100:
            await i.response.send_message("Контроль уже максимальный!", ephemeral=True)
            return
        
        army = get_army_totals(self.player_data)
        deployed = get_deployed_army_totals(self.pipeline, self.country)
        max_d = get_max_deployable_units(self.player_data)
        
        modal = ControlMilitaryModal(self.user_id, self.player_data, self.country, self.pipeline, self.mode, army, deployed, max_d, i.client)
        await i.response.send_modal(modal)

    @discord.ui.button(label="Вывести войска", style=discord.ButtonStyle.secondary)
    async def withdraw_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        deployed = get_deployed_army_totals(self.pipeline, self.country)
        if deployed["infantry"] == 0 and deployed["armored_vehicles"] == 0 and deployed["drones"] == 0:
            await i.response.send_message("У трубопровода нет размещённых вами войск!", ephemeral=True)
            return
        
        modal = WithdrawUnitsModal(self.user_id, self.player_data, self.country, self.pipeline, self.mode, deployed, i.client)
        await i.response.send_modal(modal)

    @discord.ui.button(label="Разобрать участок", style=discord.ButtonStyle.danger)
    async def dismantle_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        if self.country not in self.pipeline.get("countries_through", []):
            await i.response.send_message("На вашей территории нет участка этого трубопровода!", ephemeral=True)
            return
        
        country_len = get_country_length(self.pipeline, self.country)
        if country_len <= 0:
            await i.response.send_message("На вашей территории нет участка этого трубопровода!", ephemeral=True)
            return
        if self.pipeline["status"] == "under_construction":
            await i.response.send_message("Трубопровод ещё строится, разбор невозможен!", ephemeral=True)
            return
        
        modal = DismantleLengthModal(self.user_id, self.player_data, self.country, self.pipeline, country_len, i.client)
        await i.response.send_modal(modal)

    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_menu(i, self.user_id)


# ==================== КЛАССЫ ПОДТВЕРЖДЕНИЙ ====================

class CloseConfirmView(View):
    def __init__(self, uid, pd, c, pipe, mode, bot):
        super().__init__(timeout=60)
        self.uid, self.pd, self.c, self.pipe, self.mode, self.bot = uid, pd, c, pipe, mode, bot

    @discord.ui.button(label="Подтвердить закрытие", style=discord.ButtonStyle.danger)
    async def confirm(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        land = get_country_land_length(self.pipe, self.c)
        sea = get_country_sea_length(self.pipe, self.c)
        
        if close_pipeline_section(self.pipe, self.c, self.pd):
            await send_pipeline_log(
                self.bot,
                "close",
                {
                    "country": self.c,
                    "pipeline_name": self.pipe['name'],
                    "operator": self.pipe['operator'],
                    "length": land + sea,
                    "land": land,
                    "sea": sea,
                    "color": discord.Color.red(),
                    "event_id": f"{self.pipe['id']}_{datetime.now().timestamp()}"
                }
            )
            embed = discord.Embed(
                title=f"{EMOJIS['military']} УЧАСТОК ЗАКРЫТ",
                description=f"Участок трубопровода **{self.pipe['name']}** на территории {self.c} закрыт.",
                color=DARK_THEME_COLOR
            )
            await i.response.edit_message(embed=embed, view=None)
            await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, self.mode)
        else:
            await i.response.send_message("Ошибка при закрытии участка!", ephemeral=True)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, self.mode)


class OpenConfirmView(View):
    def __init__(self, uid, pd, c, pipe, mode, bot):
        super().__init__(timeout=60)
        self.uid, self.pd, self.c, self.pipe, self.mode, self.bot = uid, pd, c, pipe, mode, bot

    @discord.ui.button(label="Подтвердить открытие", style=discord.ButtonStyle.success)
    async def confirm(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        if open_pipeline_section(self.pipe, self.c, self.pd):
            await send_pipeline_log(
                self.bot,
                "open",
                {
                    "country": self.c,
                    "pipeline_name": self.pipe['name'],
                    "operator": self.pipe['operator'],
                    "color": discord.Color.green()
                }
            )
            embed = discord.Embed(
                title=f"{EMOJIS['oil']}{EMOJIS['gas']} УЧАСТОК ОТКРЫТ",
                description=f"Участок трубопровода **{self.pipe['name']}** на территории {self.c} открыт.",
                color=DARK_THEME_COLOR
            )
            await i.response.edit_message(embed=embed, view=None)
            await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, self.mode)
        else:
            await i.response.send_message("Ошибка при открытии участка!", ephemeral=True)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, self.mode)


class ControlMilitaryModal(Modal, title="Усиление контроля"):
    def __init__(self, uid, pd, c, pipe, mode, army, deployed, max_d, bot):
        super().__init__()
        self.uid, self.pd, self.c, self.pipe, self.mode = uid, pd, c, pipe, mode
        self.army, self.deployed, self.max_d, self.bot = army, deployed, max_d, bot
        
        max_t = min(army["infantry"], max_d["infantry"] - deployed["infantry"])
        max_v = min(army["armored_vehicles"], max_d["armored_vehicles"] - deployed["armored_vehicles"])
        max_dr = min(army["drones"], max_d["drones"] - deployed["drones"])
        
        self.add_item(TextInput(label=f"Пехота (макс: {max_t})", default="0", required=True))
        self.add_item(TextInput(label=f"Бронетехника (макс: {max_v})", default="0", required=True))
        self.add_item(TextInput(label=f"Дроны (макс: {max_dr})", default="0", required=True))

    async def on_submit(self, i):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            t = int(self.children[0].value)
            v = int(self.children[1].value)
            d = int(self.children[2].value)
        except:
            await i.response.send_message("Введите числа!", ephemeral=True)
            return
        
        if t < 0 or v < 0 or d < 0 or (t == 0 and v == 0 and d == 0):
            await i.response.send_message("Укажите положительное количество!", ephemeral=True)
            return
        
        can, msg = can_deploy_more_units(self.pipe, self.c, self.pd, t, v, d)
        if not can:
            await i.response.send_message(f"Ошибка: {msg}", ephemeral=True)
            return
        
        current_base = calculate_base_control(self.pipe, self.c)
        current_boost = calculate_control_from_military(self.deployed["infantry"], self.deployed["armored_vehicles"], self.deployed["drones"])
        current = min(100, current_base + current_boost)
        
        new_boost = calculate_control_from_military(self.deployed["infantry"] + t, self.deployed["armored_vehicles"] + v, self.deployed["drones"] + d)
        new = min(100, current_base + new_boost)
        inc = new - current
        cost = calculate_control_increase_cost(self.pipe, self.c, inc)
        pp = get_political_power(self.pd)
        
        embed = discord.Embed(
            title=f"{EMOJIS['military']} ПОДТВЕРЖДЕНИЕ УСИЛЕНИЯ КОНТРОЛЯ",
            description=f"Усиление контроля над трубопроводом **{self.pipe['name']}**",
            color=discord.Color.orange()
        )
        embed.set_image(url=PIPELINE_CONTROL_IMAGE_URL)
        embed.add_field(name="Страна", value=self.c, inline=True)
        embed.add_field(name="Пехота", value=f"+{t}", inline=True)
        embed.add_field(name="Бронетехника", value=f"+{v}", inline=True)
        embed.add_field(name="Дроны", value=f"+{d}", inline=True)
        embed.add_field(name="Текущий контроль", value=f"{current:.2f}%", inline=True)
        embed.add_field(name="Новый контроль", value=f"{new:.2f}%", inline=True)
        embed.add_field(name="Увеличение", value=f"+{inc:.2f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['political_power']} Стоимость", value=f"{cost:.1f} ПВ", inline=True)
        embed.add_field(name=f"{EMOJIS['political_power']} Доступно", value=f"{pp:.1f} ПВ", inline=True)
        
        view = ControlMilitaryConfirmView(self.uid, self.pd, self.c, self.pipe, self.mode, t, v, d, inc, cost, self.bot)
        await i.response.edit_message(embed=embed, view=view)


class ControlMilitaryConfirmView(View):
    def __init__(self, uid, pd, c, pipe, mode, t, v, d, inc, cost, bot):
        super().__init__(timeout=60)
        self.uid, self.pd, self.c, self.pipe, self.mode = uid, pd, c, pipe, mode
        self.t, self.v, self.d, self.inc, self.cost, self.bot = t, v, d, inc, cost, bot

    @discord.ui.button(label="Подтвердить усиление", style=discord.ButtonStyle.success)
    async def confirm(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        success, msg, spent, units = deploy_units_to_pipeline(self.pipe, self.c, self.t, self.v, self.d, self.pd, self.uid)
        
        if success:
            save_states(load_states())
            await send_pipeline_log(
                self.bot,
                "control",
                {
                    "country": self.c,
                    "pipeline_name": self.pipe['name'],
                    "increase": self.inc,
                    "new_control": self.pipe['country_control'].get(self.c, 0),
                    "infantry": units['infantry'],
                    "vehicles": units['armored_vehicles'],
                    "drones": units['drones'],
                    "cost_pp": spent,
                    "new_security": units.get('new_security', self.pipe['security_level'] * 100),
                    "color": discord.Color.blue()
                }
            )
            embed = discord.Embed(
                title=f"{EMOJIS['military']} КОНТРОЛЬ УСИЛЕН {EMOJIS['police']}",
                description=f"Контроль {self.c} над трубопроводом **{self.pipe['name']}** увеличен на {self.inc:.2f}%",
                color=DARK_THEME_COLOR
            )
            embed.set_image(url=PIPELINE_CONTROL_IMAGE_URL)
            embed.add_field(name="Новый контроль", value=f"{self.pipe['country_control'].get(self.c, 0):.2f}%", inline=True)
            embed.add_field(name="Пехота", value=f"+{units['infantry']}", inline=True)
            embed.add_field(name="Бронетехника", value=f"+{units['armored_vehicles']}", inline=True)
            embed.add_field(name="Дроны", value=f"+{units['drones']}", inline=True)
            embed.add_field(name=f"{EMOJIS['political_power']} Затрачено", value=f"{spent:.1f} ПВ", inline=True)
            embed.add_field(name=f"{EMOJIS['police']} Безопасность", value=f"{units.get('new_security', self.pipe['security_level'] * 100):.1f}%", inline=True)
            await i.response.edit_message(embed=embed, view=None)
            await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, self.mode)
        else:
            await i.response.send_message(f"Ошибка: {msg}", ephemeral=True)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, self.mode)


class WithdrawUnitsModal(Modal, title="Вывод войск"):
    def __init__(self, uid, pd, c, pipe, mode, deployed, bot):
        super().__init__()
        self.uid, self.pd, self.c, self.pipe, self.mode, self.deployed, self.bot = uid, pd, c, pipe, mode, deployed, bot
        
        self.add_item(TextInput(label=f"Пехота (макс: {deployed['infantry']})", default="0", required=True))
        self.add_item(TextInput(label=f"Бронетехника (макс: {deployed['armored_vehicles']})", default="0", required=True))
        self.add_item(TextInput(label=f"Дроны (макс: {deployed['drones']})", default="0", required=True))

    async def on_submit(self, i):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            t = int(self.children[0].value)
            v = int(self.children[1].value)
            d = int(self.children[2].value)
        except:
            await i.response.send_message("Введите числа!", ephemeral=True)
            return
        
        if t < 0 or v < 0 or d < 0 or (t == 0 and v == 0 and d == 0):
            await i.response.send_message("Укажите положительное количество!", ephemeral=True)
            return
        
        can, msg = can_withdraw_units(self.pipe, self.c, t, v, d)
        if not can:
            await i.response.send_message(f"Ошибка: {msg}", ephemeral=True)
            return
        
        current_base = calculate_base_control(self.pipe, self.c)
        current_boost = calculate_control_from_military(self.deployed["infantry"], self.deployed["armored_vehicles"], self.deployed["drones"])
        current = min(100, current_base + current_boost)
        
        new_boost = calculate_control_from_military(self.deployed["infantry"] - t, self.deployed["armored_vehicles"] - v, self.deployed["drones"] - d)
        new = min(100, current_base + new_boost)
        dec = current - new
        
        embed = discord.Embed(
            title=f"{EMOJIS['worker']} ПОДТВЕРЖДЕНИЕ ВЫВОДА ВОЙСК",
            description=f"Вывод войск из трубопровода **{self.pipe['name']}**",
            color=discord.Color.orange()
        )
        embed.add_field(name="Страна", value=self.c, inline=True)
        embed.add_field(name="Пехота", value=f"{t}", inline=True)
        embed.add_field(name="Бронетехника", value=f"{v}", inline=True)
        embed.add_field(name="Дроны", value=f"{d}", inline=True)
        embed.add_field(name="Текущий контроль", value=f"{current:.2f}%", inline=True)
        embed.add_field(name="Новый контроль", value=f"{new:.2f}%", inline=True)
        embed.add_field(name="Снижение", value=f"-{dec:.2f}%", inline=True)
        
        view = WithdrawConfirmView(self.uid, self.pd, self.c, self.pipe, self.mode, t, v, d, dec, self.bot)
        await i.response.edit_message(embed=embed, view=view)


class WithdrawConfirmView(View):
    def __init__(self, uid, pd, c, pipe, mode, t, v, d, dec, bot):
        super().__init__(timeout=60)
        self.uid, self.pd, self.c, self.pipe, self.mode = uid, pd, c, pipe, mode
        self.t, self.v, self.d, self.dec, self.bot = t, v, d, dec, bot

    @discord.ui.button(label="Подтвердить вывод", style=discord.ButtonStyle.success)
    async def confirm(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        success, msg, units = withdraw_units_from_pipeline(self.pipe, self.c, self.t, self.v, self.d, self.pd, self.uid)
        
        if success:
            save_states(load_states())
            await send_pipeline_log(
                self.bot,
                "withdraw",
                {
                    "country": self.c,
                    "pipeline_name": self.pipe['name'],
                    "decrease": self.dec,
                    "new_control": self.pipe['country_control'].get(self.c, 0),
                    "infantry": units['infantry'],
                    "vehicles": units['armored_vehicles'],
                    "drones": units['drones'],
                    "new_security": units.get('new_security', self.pipe['security_level'] * 100),
                    "color": discord.Color.green()
                }
            )
            embed = discord.Embed(
                title=f"{EMOJIS['worker']} ВОЙСКА ВЫВЕДЕНЫ {EMOJIS['police']}",
                description=f"Войска выведены из трубопровода **{self.pipe['name']}**",
                color=DARK_THEME_COLOR
            )
            embed.add_field(name="Пехота", value=f"{units['infantry']}", inline=True)
            embed.add_field(name="Бронетехника", value=f"{units['armored_vehicles']}", inline=True)
            embed.add_field(name="Дроны", value=f"{units['drones']}", inline=True)
            embed.add_field(name="Новый контроль", value=f"{self.pipe['country_control'].get(self.c, 0):.2f}%", inline=True)
            embed.add_field(name=f"{EMOJIS['police']} Безопасность", value=f"{units.get('new_security', self.pipe['security_level'] * 100):.1f}%", inline=True)
            await i.response.edit_message(embed=embed, view=None)
            await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, self.mode)
        else:
            await i.response.send_message(f"Ошибка: {msg}", ephemeral=True)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, self.mode)


class DismantleLengthModal(Modal, title="Разбор участка"):
    def __init__(self, uid, pd, c, pipe, max_len, bot):
        super().__init__()
        self.uid, self.pd, self.c, self.pipe, self.max_len, self.bot = uid, pd, c, pipe, max_len, bot
        self.add_item(TextInput(label=f"Количество километров (макс: {max_len})", placeholder="Введите число", required=True))

    async def on_submit(self, i):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            length = int(self.children[0].value)
        except:
            await i.response.send_message("Введите число!", ephemeral=True)
            return
        
        if length <= 0 or length > self.max_len:
            await i.response.send_message(f"Количество должно быть от 1 до {self.max_len}!", ephemeral=True)
            return
        
        cost, seconds = calculate_dismantle_cost(self.pipe, length)
        cost_dollars = cost * 1_000_000
        game_days = real_seconds_to_game_days(seconds)
        
        embed = discord.Embed(
            title=f"{EMOJIS['engineer']} ПОДТВЕРЖДЕНИЕ РАЗБОРА",
            description=f"Разборка {length} км участка трубопровода **{self.pipe['name']}** на территории {self.c}",
            color=discord.Color.red()
        )
        embed.set_image(url=PIPELINE_DISMANTLE_IMAGE_URL)
        embed.add_field(name="Время разборки", value=format_game_days(game_days), inline=True)
        embed.add_field(name=f"{EMOJIS['money']} Возврат в бюджет", value=format_billion(cost_dollars), inline=True)
        
        view = DismantleConfirmView(self.uid, self.pd, self.c, self.pipe, length, cost_dollars, seconds, game_days, self.bot)
        await i.response.edit_message(embed=embed, view=view)


class DismantleConfirmView(View):
    def __init__(self, uid, pd, c, pipe, length, cost, seconds, game_days, bot):
        super().__init__(timeout=60)
        self.uid, self.pd, self.c, self.pipe = uid, pd, c, pipe
        self.length, self.cost, self.seconds, self.game_days, self.bot = length, cost, seconds, game_days, bot

    @discord.ui.button(label="Подтвердить разбор", style=discord.ButtonStyle.danger)
    async def confirm(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await i.response.defer()
        
        success, msg, cost_return, seconds = dismantle_section(self.pipe, self.c, self.length, self.pd, self.uid, self.bot)
        
        if success:
            await send_pipeline_log(
                self.bot,
                "dismantle",
                {
                    "country": self.c,
                    "pipeline_name": self.pipe['name'],
                    "length": self.length,
                    "time": format_game_days(self.game_days),
                    "refund": cost_return,
                    "color": discord.Color.orange()
                }
            )
            embed = discord.Embed(
                title=f"{EMOJIS['engineer']} РАЗБОР НАЧАТ",
                description=f"Разборка {self.length} км участка трубопровода **{self.pipe['name']}** на территории {self.c}",
                color=DARK_THEME_COLOR
            )
            embed.set_image(url=PIPELINE_DISMANTLE_IMAGE_URL)
            embed.add_field(name="Время", value=format_game_days(self.game_days), inline=True)
            embed.add_field(name=f"{EMOJIS['money']} Возврат", value=format_billion(cost_return), inline=True)
            await i.followup.send(embed=embed, ephemeral=True)
            await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, "transit")
        else:
            await i.followup.send(f"Ошибка: {msg}", ephemeral=True)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, i, b):
        if i.user.id != self.uid:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_pipeline_detail(i, self.uid, self.pd, self.c, self.pipe, "transit")


async def pipeline_projects_loop(bot):
    """Фоновая задача для обработки просроченных проектов"""
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        try:
            expired = await process_expired_pipeline_projects(bot)
            if expired > 0:
                print(f"⏰ Обработано {expired} просроченных проектов трубопроводов")
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Ошибка в pipeline_projects_loop: {e}")
            await asyncio.sleep(3600)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_pipeline_menu',
    'show_create_pipeline_menu',
    'show_pipeline_projects_menu',
    'pipeline_projects_loop',
    'PIPELINE_TYPES',
    'DEFAULT_PIPELINES',
    'get_pipelines_by_operator',
    'get_pipelines_through_country',
    'calculate_daily_flow',
    'apply_damage_to_pipeline',
    'close_pipeline_section',
    'open_pipeline_section',
    'deploy_units_to_pipeline',
    'withdraw_units_from_pipeline',
    'dismantle_section',
    'get_army_totals',
    'get_deployed_army_totals',
    'get_max_deployable_units',
    'PIPELINE_LOG_CHANNEL_ID',
    'get_country_length',
    'get_country_land_length',
    'get_country_sea_length'
]

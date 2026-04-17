# satellites.py - Модуль для управления спутниками
# Версия 3.1 - улучшенный структурированный эмбед

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import asyncio
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any

from utils import (
    format_number, format_billion, load_states, save_states, 
    DARK_THEME_COLOR, get_budget, subtract_from_budget, add_to_budget,
    EXCHANGE_RATES_2019, get_currency_code
)
from political_power import spend_political_power, get_political_power
from game_time import get_current_game_time, days_since_last_event

# Файлы для хранения данных
SATELLITES_FILE = 'satellites.json'
CORPORATE_SATELLITES_FILE = 'corporate_satellites.json'
SATELLITE_ACCESS_FILE = 'satellite_access.json'

# Картинка для эмбедов
SATELLITE_BANNER = "https://avatars.mds.yandex.net/i?id=c305d0ba5a946c7b62332944783a9400_l-2924668-images-thumbs&n=13"

# ==================== КАСТОМНЫЕ ЭМОДЗИ ====================

EMOJIS = {
    "satellite": "<:satelite:1494377962433151128>",
    "debt": "<:debt:1494378008759501011>",
    "military": "<:Military_factory:1492864212085506068>",
    "civilian": "<:Civilian_factory:1492864140501323986>",
    "research": "<:Technology_sharing:1432616738754793563>",
    "gdp": "<:vvp:1487360602367070400>",
    "communication": "<:Telecommunication:1492864324975464548>",
    "drone": "<:targeted_drone_recon:1493257067425824838>",
    "missile": "<:ZRK:1492864585995255808>",
    "recon": "<:radar_systems:1492864585995255808>",
    "infrastructure": "<:construction_repair:1492879195657732256>",
    "budget": "<:money:1429345094695129088>",
    "pp": "<:pp:1487015341883130027>",
    "success": "<:eco_baff:1492879901760421888>",
    "error": "<:smert:1492913346859765892>",
    "warning": "<:crisis:1487167453443391509>",
    "corporate": "<:office_center:1492908676824957079>",
    "intercept": "<:ZRK:1492864585995255808>",
    "block": "<:ukrep:1492864074634100938>",
    "unblock": "<:eco_baff:1492879901760421888>",
    "owner": "<:government:1487167580350451804>",
    "time": "<:clock:1256638575611678730>",
    "stats": "<:fin:1425212665479041024>",
}


# ==================== ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ БОНУСА К ПЕРЕХВАТУ ====================

def get_satellite_bonuses(country_name: str) -> Dict[str, float]:
    """Возвращает суммарные бонусы от спутников страны."""
    try:
        bonuses = get_total_satellite_bonuses(country_name)
        return bonuses.get("total", {})
    except Exception as e:
        print(f"Ошибка при получении бонусов спутников: {e}")
        return {}


def get_intercept_difficulty_boost(attacker_country: str) -> float:
    """Возвращает бонус к сложности перехвата от спутников атакующей страны."""
    try:
        bonuses = get_total_satellite_bonuses(attacker_country)
        return bonuses.get("total", {}).get("intercept_difficulty", 0.0)
    except Exception as e:
        print(f"Ошибка при получении бонуса перехвата: {e}")
        return 0.0


# ==================== ДАННЫЕ О КОРПОРАТИВНЫХ СПУТНИКАХ ====================
# На 1 декабря 2021 года

CORPORATE_SATELLITE_OWNERS = {
    "SpaceX (Starlink)": {
        "name": "SpaceX (Starlink)",
        "country": "США",
        "owner": "США",
        "civilian_satellites": 1944,
        "military_satellites": 0,
        "description": "Коммерческая спутниковая группировка для глобального интернета",
        "countries_with_access": [
            "США", "Канада", "Великобритания", "Германия", "Франция", 
            "Австралия", "Новая Зеландия", "Чили", "Аргентина", "Бразилия",
            "Мексика", "Япония", "Южная Корея", "Украина", "Польша",
            "Россия", "Беларусь", "Финляндия", "Швеция", "Норвегия",
            "Дания", "Нидерланды", "Бельгия", "Швейцария", "Австрия",
            "Италия", "Испания", "Португалия", "Греция", "Турция"
        ],
        "blocked_countries": ["Китай", "Иран", "КНДР", "Сирия"]
    },
    "OneWeb": {
        "name": "OneWeb",
        "country": "Великобритания",
        "owner": "Великобритания",
        "civilian_satellites": 394,
        "military_satellites": 0,
        "description": "Спутниковая группировка для широкополосного доступа",
        "countries_with_access": [
            "Великобритания", "США", "Канада", "Франция", "Германия",
            "Италия", "Испания", "Норвегия", "Швеция", "Финляндия",
            "Япония", "Южная Корея", "Австралия", "Новая Зеландия",
            "Россия", "Беларусь", "Казахстан", "Украина", "Польша"
        ],
        "blocked_countries": ["Китай", "Иран", "КНДР"]
    },
    "Amazon Kuiper": {
        "name": "Amazon Kuiper",
        "country": "США",
        "owner": "США",
        "civilian_satellites": 0,
        "military_satellites": 0,
        "description": "Планируемая спутниковая группировка Amazon (запуски с 2023)",
        "countries_with_access": [],
        "blocked_countries": [],
        "not_operational": True
    },
    "Eutelsat": {
        "name": "Eutelsat",
        "country": "Франция",
        "owner": "Франция",
        "civilian_satellites": 36,
        "military_satellites": 2,
        "description": "Европейский оператор спутниковой связи",
        "countries_with_access": [
            "Франция", "Германия", "Италия", "Испания", "Великобритания",
            "Бельгия", "Нидерланды", "Швейцария", "Австрия", "Польша",
            "Чехия", "Словакия", "Венгрия", "Румыния", "Болгария"
        ],
        "blocked_countries": []
    },
    "Inmarsat": {
        "name": "Inmarsat",
        "country": "Великобритания",
        "owner": "Великобритания",
        "civilian_satellites": 13,
        "military_satellites": 4,
        "description": "Спутниковая связь для морской и авиационной отрасли",
        "countries_with_access": [
            "Великобритания", "США", "Канада", "Австралия", "Новая Зеландия",
            "Франция", "Германия", "Япония", "Южная Корея", "Сингапур"
        ],
        "blocked_countries": []
    },
    "Iridium": {
        "name": "Iridium",
        "country": "США",
        "owner": "США",
        "civilian_satellites": 75,
        "military_satellites": 0,
        "description": "Глобальная спутниковая связь с низкой орбитой",
        "countries_with_access": [
            "США", "Канада", "Великобритания", "Австралия", "Япония",
            "Южная Корея", "Россия", "Китай", "Индия", "Бразилия"
        ],
        "blocked_countries": ["Иран", "КНДР", "Сирия"]
    },
    "Telesat": {
        "name": "Telesat",
        "country": "Канада",
        "owner": "Канада",
        "civilian_satellites": 15,
        "military_satellites": 1,
        "description": "Канадский оператор спутниковой связи",
        "countries_with_access": [
            "Канада", "США", "Великобритания", "Франция", "Германия",
            "Норвегия", "Швеция", "Финляндия", "Дания", "Исландия"
        ],
        "blocked_countries": []
    },
    "SES": {
        "name": "SES",
        "country": "Люксембург",
        "owner": "Люксембург",
        "civilian_satellites": 50,
        "military_satellites": 2,
        "description": "Люксембургский оператор спутниковой связи (включая O3b)",
        "countries_with_access": [
            "Люксембург", "Франция", "Германия", "Бельгия", "Нидерланды",
            "Великобритания", "Италия", "Испания", "Португалия", "Швейцария"
        ],
        "blocked_countries": []
    },
    "ViaSat": {
        "name": "ViaSat",
        "country": "США",
        "owner": "США",
        "civilian_satellites": 8,
        "military_satellites": 3,
        "description": "Американский оператор спутниковой связи",
        "countries_with_access": [
            "США", "Канада", "Мексика", "Бразилия", "Аргентина",
            "Чили", "Колумбия", "Перу", "Эквадор", "Венесуэла"
        ],
        "blocked_countries": []
    },
    "China Satcom": {
        "name": "China Satcom",
        "country": "Китай",
        "owner": "Китай",
        "civilian_satellites": 45,
        "military_satellites": 12,
        "description": "Китайский оператор спутниковой связи",
        "countries_with_access": [
            "Китай", "Россия", "Казахстан", "Киргизия", "Таджикистан",
            "Узбекистан", "Туркменистан", "Пакистан", "Мьянма", "Лаос"
        ],
        "blocked_countries": ["США", "Великобритания", "Япония", "Южная Корея", "Австралия"]
    },
    "Russian Satellite Communications": {
        "name": "Российские спутники связи",
        "country": "Россия",
        "owner": "Россия",
        "civilian_satellites": 32,
        "military_satellites": 18,
        "description": "Российские спутники связи (Экспресс, Ямал и др.)",
        "countries_with_access": [
            "Россия", "Беларусь", "Казахстан", "Киргизия", "Таджикистан",
            "Узбекистан", "Туркменистан", "Армения", "Азербайджан", "Грузия"
        ],
        "blocked_countries": []
    }
}


# ==================== БОНУСЫ КОРПОРАЦИЙ (БЕЗ БОНУСА К ПЕРЕХВАТУ) ====================

CORPORATE_SATELLITE_OWNERS["SpaceX (Starlink)"]["bonus_if_active"] = {
    "research_boost": 0.03,
    "communication_boost": 0.08,
    "gdp_boost": 0.02,
    "drone_accuracy": 0.03,
    "missile_accuracy": 0.02
}

CORPORATE_SATELLITE_OWNERS["OneWeb"]["bonus_if_active"] = {
    "communication_boost": 0.05,
    "drone_accuracy": 0.02,
    "missile_accuracy": 0.01
}

CORPORATE_SATELLITE_OWNERS["Eutelsat"]["bonus_if_active"] = {
    "communication_boost": 0.02
}

CORPORATE_SATELLITE_OWNERS["Inmarsat"]["bonus_if_active"] = {
    "communication_boost": 0.03,
    "drone_accuracy": 0.02
}

CORPORATE_SATELLITE_OWNERS["Iridium"]["bonus_if_active"] = {
    "communication_boost": 0.04
}

CORPORATE_SATELLITE_OWNERS["Telesat"]["bonus_if_active"] = {
    "communication_boost": 0.02
}

CORPORATE_SATELLITE_OWNERS["SES"]["bonus_if_active"] = {
    "communication_boost": 0.03
}

CORPORATE_SATELLITE_OWNERS["ViaSat"]["bonus_if_active"] = {
    "communication_boost": 0.02,
    "drone_accuracy": 0.01
}

CORPORATE_SATELLITE_OWNERS["China Satcom"]["bonus_if_active"] = {
    "communication_boost": 0.04,
    "drone_accuracy": 0.01,
    "missile_accuracy": 0.02
}

CORPORATE_SATELLITE_OWNERS["Russian Satellite Communications"]["bonus_if_active"] = {
    "communication_boost": 0.04,
    "drone_accuracy": 0.01,
    "missile_accuracy": 0.02
}


# ==================== ТИПЫ СПУТНИКОВ ====================

SATELLITE_TYPES = {
    "military": {
        "name": "Военный спутник",
        "emoji": EMOJIS["military"],
        "description": "Разведка, навигация, связь для военных операций.",
        "base_cost_usd": 500_000_000,
        "pp_cost": 10,
        "build_time_hours": 72,
        "effects": {
            "drone_accuracy": 0.005,
            "missile_accuracy": 0.005,
            "recon_range": 0.01,
            "intercept_difficulty": 0.005
        },
        "maintenance_cost_usd": 10_000_000
    },
    "civilian": {
        "name": "Гражданский спутник",
        "emoji": EMOJIS["civilian"],
        "description": "Связь, навигация, наблюдение за погодой.",
        "base_cost_usd": 300_000_000,
        "pp_cost": 5,
        "build_time_hours": 48,
        "effects": {
            "infrastructure_boost": 0.002,
            "research_boost": 0.003,
            "gdp_boost": 0.001,
            "communication_boost": 0.004
        },
        "maintenance_cost_usd": 5_000_000
    }
}


# ==================== ГОСУДАРСТВЕННЫЕ СПУТНИКИ (ДЕКАБРЬ 2021) ====================

STARTING_SATELLITES = {
    "США": {"military": 187, "civilian": 293},
    "Россия": {"military": 112, "civilian": 85},
    "Китай": {"military": 156, "civilian": 214},
    "Германия": {"military": 8, "civilian": 47},
    "Великобритания": {"military": 7, "civilian": 43},
    "Франция": {"military": 12, "civilian": 38},
    "Япония": {"military": 9, "civilian": 78},
    "Израиль": {"military": 14, "civilian": 8},
    "Украина": {"military": 0, "civilian": 1},
    "Иран": {"military": 3, "civilian": 2},
    "Беларусь": {"military": 0, "civilian": 0},
    "Норвегия": {"military": 0, "civilian": 3},
    "КНДР": {"military": 1, "civilian": 0},
    "Турция": {"military": 2, "civilian": 5},
    "Сирия": {"military": 0, "civilian": 0},
    "Канада": {"military": 2, "civilian": 32},
    "Польша": {"military": 0, "civilian": 3},
    "Бразилия": {"military": 0, "civilian": 13},
    "Швеция": {"military": 0, "civilian": 10},
    "Финляндия": {"military": 0, "civilian": 8},
    "Швейцария": {"military": 0, "civilian": 0},
    "Египет": {"military": 1, "civilian": 2},
    "Индия": {"military": 12, "civilian": 45},
    "Италия": {"military": 5, "civilian": 27},
    "Испания": {"military": 3, "civilian": 19},
    "Австралия": {"military": 2, "civilian": 11},
    "Южная Корея": {"military": 4, "civilian": 16},
    "Нидерланды": {"military": 1, "civilian": 12},
    "Бельгия": {"military": 0, "civilian": 8},
    "Австрия": {"military": 0, "civilian": 4},
    "Дания": {"military": 0, "civilian": 5},
    "Чехия": {"military": 0, "civilian": 3},
    "Венгрия": {"military": 0, "civilian": 2}
}


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ВАЛЮТАМИ ====================

def convert_usd_to_local(amount_usd: float, country_name: str) -> float:
    """Конвертирует USD в локальную валюту"""
    rate = EXCHANGE_RATES_2019.get(country_name, 1.0)
    return amount_usd * rate


def get_currency_code_from_country(country_name: str) -> str:
    """Получает код валюты для страны"""
    states = load_states()
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == country_name:
            return get_currency_code(data.get("economy", {}))
    return "USD"


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С КОРПОРАТИВНЫМИ СПУТНИКАМИ ====================

def load_corporate_access():
    """Загружает пользовательские настройки доступа к корпоративным спутникам"""
    try:
        with open(SATELLITE_ACCESS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_corporate_access(data):
    """Сохраняет пользовательские настройки доступа к корпоративным спутникам"""
    with open(SATELLITE_ACCESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def is_corporate_satellite_available(country_name: str, corp_name: str) -> bool:
    """Проверяет, доступны ли корпоративные спутники для страны"""
    corp_info = CORPORATE_SATELLITE_OWNERS.get(corp_name, {})
    
    if corp_info.get("not_operational", False):
        return False
    
    # Проверяем пользовательские блокировки
    access_data = load_corporate_access()
    if corp_name in access_data:
        custom_blocked = access_data[corp_name].get("blocked_countries", [])
        if country_name in custom_blocked:
            return False
        custom_allowed = access_data[corp_name].get("countries_with_access", [])
        if country_name in custom_allowed:
            return True
    
    # Стандартные блокировки
    if country_name in corp_info.get("blocked_countries", []):
        return False
    
    if country_name in corp_info.get("countries_with_access", []):
        return True
    
    return False


def get_country_corporate_satellites(country_name: str) -> Dict:
    """Возвращает количество корпоративных спутников, доступных стране"""
    result = {}
    
    for corp_name, corp_info in CORPORATE_SATELLITE_OWNERS.items():
        if is_corporate_satellite_available(country_name, corp_name):
            result[corp_name] = {
                "civilian": corp_info.get("civilian_satellites", 0),
                "military": corp_info.get("military_satellites", 0),
                "total": corp_info.get("civilian_satellites", 0) + corp_info.get("military_satellites", 0),
                "owner": corp_info.get("owner", corp_info.get("country", ""))
            }
    
    return result


def get_corporate_bonuses(country_name: str) -> Dict[str, float]:
    """Возвращает бонусы от корпоративных спутников, доступных стране"""
    total_bonuses = {
        "research_boost": 0,
        "communication_boost": 0,
        "gdp_boost": 0,
        "drone_accuracy": 0,
        "missile_accuracy": 0
    }
    
    for corp_name, corp_info in CORPORATE_SATELLITE_OWNERS.items():
        if is_corporate_satellite_available(country_name, corp_name):
            bonuses = corp_info.get("bonus_if_active", {})
            for bonus_type, value in bonuses.items():
                if bonus_type in total_bonuses:
                    total_bonuses[bonus_type] += value
    
    return total_bonuses


def get_corporations_owned_by_country(country_name: str) -> List[str]:
    """Возвращает список корпораций, которыми владеет страна"""
    owned = []
    for corp_name, corp_info in CORPORATE_SATELLITE_OWNERS.items():
        if corp_info.get("owner") == country_name:
            owned.append(corp_name)
    return owned


# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_satellites():
    """Загружает данные о государственных спутниках"""
    try:
        with open(SATELLITES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return create_initial_satellites_data()
            data = json.loads(content)
            if not isinstance(data, dict) or "satellites" not in data:
                return create_initial_satellites_data()
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return create_initial_satellites_data()


def create_initial_satellites_data():
    """Создаёт начальные данные о государственных спутниках"""
    initial_data = {"satellites": {}}
    
    for country, data in STARTING_SATELLITES.items():
        initial_data["satellites"][country] = {
            "military": data.get("military", 0),
            "civilian": data.get("civilian", 0),
            "launch_history": [],
            "last_maintenance": str(datetime.now()),
            "notes": ""
        }
    
    save_satellites(initial_data)
    return initial_data


def save_satellites(data):
    """Сохраняет данные о государственных спутниках"""
    with open(SATELLITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_country_satellites(country_name: str) -> Dict:
    """Получает данные о государственных спутниках страны"""
    data = load_satellites()
    if country_name not in data["satellites"]:
        data["satellites"][country_name] = {
            "military": 0,
            "civilian": 0,
            "launch_history": [],
            "last_maintenance": str(datetime.now()),
            "notes": ""
        }
        save_satellites(data)
    return data["satellites"][country_name]


def update_country_satellites(country_name: str, satellites_data: Dict):
    """Обновляет данные о государственных спутниках страны"""
    data = load_satellites()
    data["satellites"][country_name] = satellites_data
    save_satellites(data)


# ==================== ФУНКЦИИ ДЛЯ РАСЧЕТА ОБЩИХ БОНУСОВ ====================

def get_total_satellite_bonuses(country_name: str) -> Dict:
    """Возвращает суммарные бонусы от ВСЕХ источников"""
    gov_satellites = get_country_satellites(country_name)
    military_count = gov_satellites.get("military", 0)
    civilian_count = gov_satellites.get("civilian", 0)
    
    self_bonuses = {
        "drone_accuracy": 0,
        "missile_accuracy": 0,
        "recon_range": 0,
        "infrastructure_boost": 0,
        "research_boost": 0,
        "gdp_boost": 0,
        "communication_boost": 0,
        "intercept_difficulty": 0
    }
    
    if military_count > 0:
        mil_effects = SATELLITE_TYPES["military"]["effects"]
        for effect, base_value in mil_effects.items():
            self_bonuses[effect] = base_value * military_count
    
    if civilian_count > 0:
        civ_effects = SATELLITE_TYPES["civilian"]["effects"]
        for effect, base_value in civ_effects.items():
            if effect in self_bonuses:
                self_bonuses[effect] = base_value * civilian_count
    
    corp_bonuses = get_corporate_bonuses(country_name)
    
    total = {}
    for key in self_bonuses:
        if key == "intercept_difficulty":
            total[key] = self_bonuses.get(key, 0)
        else:
            total[key] = self_bonuses.get(key, 0) + corp_bonuses.get(key, 0)
    
    return {
        "self": {
            "military": military_count,
            "civilian": civilian_count,
            "bonuses": self_bonuses
        },
        "corporate": corp_bonuses,
        "total": total
    }


# ==================== ФУНКЦИИ ДЛЯ ЗАПУСКА СПУТНИКОВ ====================

def can_launch_satellite(player_data, satellite_type: str) -> Tuple[bool, str]:
    """Проверяет, может ли игрок запустить спутник"""
    sat_info = SATELLITE_TYPES[satellite_type]
    country_name = player_data["state"]["statename"]
    
    local_cost = convert_usd_to_local(sat_info["base_cost_usd"], country_name)
    current_budget = get_budget(player_data["economy"])
    currency_code = get_currency_code(player_data["economy"])
    
    if current_budget < local_cost:
        return False, f"{EMOJIS['error']} Недостаточно средств! Нужно: {format_billion(local_cost)} {currency_code}"
    
    current_pp = get_political_power(player_data)
    if current_pp < sat_info["pp_cost"]:
        return False, f"{EMOJIS['error']} Недостаточно политической власти! Нужно: {sat_info['pp_cost']}, у вас: {current_pp:.1f}"
    
    return True, "OK"


def launch_satellite(player_data, satellite_type: str, quantity: int = 1) -> Tuple[bool, str]:
    """Запускает спутники"""
    country_name = player_data["state"]["statename"]
    satellites = get_country_satellites(country_name)
    sat_info = SATELLITE_TYPES[satellite_type]
    
    total_cost_usd = sat_info["base_cost_usd"] * quantity
    local_cost = convert_usd_to_local(total_cost_usd, country_name)
    total_pp = sat_info["pp_cost"] * quantity
    
    current_budget = get_budget(player_data["economy"])
    if current_budget < local_cost:
        return False, f"{EMOJIS['error']} Недостаточно средств!"
    
    current_pp = get_political_power(player_data)
    if current_pp < total_pp:
        return False, f"{EMOJIS['error']} Недостаточно политической власти!"
    
    subtract_from_budget(player_data["economy"], local_cost)
    spend_political_power(player_data, total_pp)
    
    satellites[satellite_type] = satellites.get(satellite_type, 0) + quantity
    
    game_date, _ = get_current_game_time()
    if "launch_history" not in satellites:
        satellites["launch_history"] = []
    
    satellites["launch_history"].append({
        "type": satellite_type,
        "date": str(datetime.now()),
        "game_date": game_date.strftime("%Y-%m-%d"),
        "count": quantity
    })
    
    update_country_satellites(country_name, satellites)
    return True, f"{EMOJIS['success']} Запущено {quantity} спутников!"


# ==================== ГЛАВНОЕ МЕНЮ (СТРУКТУРИРОВАННОЕ) ====================

async def show_satellite_menu(ctx, user_id: int):
    """Показать главное меню спутников"""
    states = load_states()
    
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        if hasattr(ctx, 'response'):
            await ctx.response.send_message(f"{EMOJIS['error']} У вас нет государства!", ephemeral=True)
        else:
            await ctx.send(f"{EMOJIS['error']} У вас нет государства!")
        return
    
    country_name = player_data["state"]["statename"]
    satellites = get_country_satellites(country_name)
    bonuses = get_total_satellite_bonuses(country_name)
    currency_code = get_currency_code(player_data["economy"])
    
    embed = discord.Embed(
        title=f"{EMOJIS['satellite']} Спутниковая система",
        description=f"### {country_name}\n",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=SATELLITE_BANNER)
    
    # ===== БЛОК 1: СТАТИСТИКА =====
    embed.add_field(
        name=f"",
        value=f"**{EMOJIS['stats']} СТАТИСТИКА**\n"
              f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJIS['military']} Военные спутники",
        value=f"```\n{satellites.get('military', 0)}\n```",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJIS['civilian']} Гражданские спутники",
        value=f"```\n{satellites.get('civilian', 0)}\n```",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJIS['satellite']} Всего спутников",
        value=f"```\n{satellites.get('military', 0) + satellites.get('civilian', 0)}\n```",
        inline=True
    )
    
    # ===== БЛОК 2: РЕСУРСЫ =====
    embed.add_field(
        name=f"",
        value=f"**{EMOJIS['budget']} РЕСУРСЫ**\n"
              f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        inline=False
    )
    
    embed.add_field(
        name=f"{EMOJIS['budget']} Бюджет",
        value=f"```\n{format_billion(get_budget(player_data['economy']))} {currency_code}\n```",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJIS['pp']} Полит. власть",
        value=f"```\n{get_political_power(player_data):.1f}\n```",
        inline=True
    )
    embed.add_field(
        name=f"{EMOJIS['debt']} Годовое обслуживание",
        value=f"```\n{format_billion(convert_usd_to_local(satellites.get('military', 0) * SATELLITE_TYPES['military']['maintenance_cost_usd'] + satellites.get('civilian', 0) * SATELLITE_TYPES['civilian']['maintenance_cost_usd'], country_name))} {currency_code}\n```",
        inline=True
    )
    
    # ===== БЛОК 3: АКТИВНЫЕ БОНУСЫ =====
    total = bonuses["total"]
    bonus_lines = []
    if total.get("drone_accuracy", 0) > 0:
        bonus_lines.append(f"{EMOJIS['drone']} Точность дронов: **+{total['drone_accuracy']*100:.1f}%**")
    if total.get("missile_accuracy", 0) > 0:
        bonus_lines.append(f"{EMOJIS['missile']} Точность ракет: **+{total['missile_accuracy']*100:.1f}%**")
    if total.get("intercept_difficulty", 0) > 0:
        bonus_lines.append(f"{EMOJIS['intercept']} Сложность перехвата: **+{total['intercept_difficulty']*100:.1f}%**")
    if total.get("research_boost", 0) > 0:
        bonus_lines.append(f"{EMOJIS['research']} Исследования: **+{total['research_boost']*100:.1f}%**")
    if total.get("gdp_boost", 0) > 0:
        bonus_lines.append(f"{EMOJIS['gdp']} Рост ВВП: **+{total['gdp_boost']*100:.1f}%**")
    if total.get("communication_boost", 0) > 0:
        bonus_lines.append(f"{EMOJIS['communication']} Связь: **+{total['communication_boost']*100:.1f}%**")
    if total.get("infrastructure_boost", 0) > 0:
        bonus_lines.append(f"{EMOJIS['infrastructure']} Инфраструктура: **+{total['infrastructure_boost']*100:.1f}%**")
    if total.get("recon_range", 0) > 0:
        bonus_lines.append(f"{EMOJIS['recon']} Дальность разведки: **+{total['recon_range']*100:.1f}%**")
    
    embed.add_field(
        name=f"",
        value=f"**{EMOJIS['success']} АКТИВНЫЕ БОНУСЫ**\n"
              f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬",
        inline=False
    )
    
    if bonus_lines:
        embed.add_field(
            name="",
            value="\n".join(bonus_lines),
            inline=False
        )
    else:
        embed.add_field(
            name="",
            value=f"{EMOJIS['warning']} Нет активных бонусов",
            inline=False
        )
    
    # Доступные корпоративные спутники (компактно)
    corporate_satellites = get_country_corporate_satellites(country_name)
    if corporate_satellites:
        corp_text = ""
        for corp_name, data in list(corporate_satellites.items())[:3]:
            corp_text += f"{EMOJIS['corporate']} **{corp_name}**: {data['total']} спутников\n"
        if len(corporate_satellites) > 3:
            corp_text += f"... и ещё {len(corporate_satellites)-3} систем"
        
        embed.add_field(
            name=f"",
            value=f"**{EMOJIS['corporate']} КОРПОРАТИВНЫЕ СИСТЕМЫ**\n"
                  f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                  f"{corp_text}",
            inline=False
        )
    
    embed.set_footer(text="Выберите раздел в меню ниже")
    
    view = SatelliteMainView(user_id, player_data, country_name)
    
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx.send(embed=embed, view=view)


class SatelliteMainView(View):
    """Главное меню спутников с выпадающим списком"""
    
    def __init__(self, user_id, player_data, country_name):
        super().__init__(timeout=180)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        
        options = [
            discord.SelectOption(label="Запуск спутников", value="launch", description="Запустить новые спутники на орбиту"),
            discord.SelectOption(label="Обзор системы", value="overview", description="Расходы, бонусы и статистика"),
            discord.SelectOption(label="Политика", value="policy", description="Управление доступом и спутниками"),
        ]
        
        select = Select(placeholder="Выберите раздел...", options=options)
        select.callback = self.on_select
        self.add_item(select)
    
    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        choice = interaction.data["values"][0]
        
        if choice == "launch":
            await self.show_launch_menu(interaction)
        elif choice == "overview":
            await self.show_overview_menu(interaction)
        elif choice == "policy":
            await self.show_policy_menu(interaction)
    
    async def show_launch_menu(self, interaction: discord.Interaction):
        """Меню запуска спутников"""
        embed = discord.Embed(
            title=f"{EMOJIS['satellite']} Запуск спутников",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=SATELLITE_BANNER)
        
        # Информация о типах спутников
        for sat_type, info in SATELLITE_TYPES.items():
            local_cost = convert_usd_to_local(info["base_cost_usd"], self.country_name)
            currency_code = get_currency_code(self.player_data["economy"])
            
            embed.add_field(
                name=f"{info['emoji']} {info['name']}",
                value=f"{info['description']}\n\n"
                      f"{EMOJIS['budget']} Стоимость: **{format_billion(local_cost)} {currency_code}**\n"
                      f"{EMOJIS['pp']} Полит. власть: **{info['pp_cost']}**\n"
                      f"{EMOJIS['time']} Время запуска: **{info['build_time_hours']} ч.**\n"
                      f"{EMOJIS['debt']} Обслуживание: **{convert_usd_to_local(info['maintenance_cost_usd'], self.country_name):,.0f} {currency_code}/год**",
                inline=False
            )
        
        options = []
        for sat_type, info in SATELLITE_TYPES.items():
            options.append(discord.SelectOption(
                label=info['name'],
                value=sat_type,
                description=f"Стоимость: {info['base_cost_usd']:,} USD"
            ))
        
        view = LaunchMenuView(self.user_id, self.player_data, self.country_name, options, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_overview_menu(self, interaction: discord.Interaction):
        """Меню обзора системы"""
        satellites = get_country_satellites(self.country_name)
        bonuses = get_total_satellite_bonuses(self.country_name)
        corporate_satellites = get_country_corporate_satellites(self.country_name)
        currency_code = get_currency_code(self.player_data["economy"])
        
        # Расчёт расходов
        military_count = satellites.get("military", 0)
        civilian_count = satellites.get("civilian", 0)
        mil_maintenance_usd = military_count * SATELLITE_TYPES["military"]["maintenance_cost_usd"]
        civ_maintenance_usd = civilian_count * SATELLITE_TYPES["civilian"]["maintenance_cost_usd"]
        total_maintenance_usd = mil_maintenance_usd + civ_maintenance_usd
        local_maintenance = convert_usd_to_local(total_maintenance_usd, self.country_name)
        
        embed = discord.Embed(
            title=f"{EMOJIS['satellite']} Обзор спутниковой системы",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=SATELLITE_BANNER)
        
        # Расходы
        embed.add_field(
            name=f"{EMOJIS['debt']} Годовые расходы",
            value=f"{EMOJIS['military']} Военные: **{format_billion(convert_usd_to_local(mil_maintenance_usd, self.country_name))} {currency_code}**\n"
                  f"{EMOJIS['civilian']} Гражданские: **{format_billion(convert_usd_to_local(civ_maintenance_usd, self.country_name))} {currency_code}**\n"
                  f"**Всего: {format_billion(local_maintenance)} {currency_code}**",
            inline=False
        )
        
        # Бонусы от собственных спутников
        self_bonuses = bonuses["self"]["bonuses"]
        self_text = ""
        if self_bonuses.get("drone_accuracy", 0) > 0:
            self_text += f"{EMOJIS['drone']} Точность дронов: +{self_bonuses['drone_accuracy']*100:.1f}%\n"
        if self_bonuses.get("missile_accuracy", 0) > 0:
            self_text += f"{EMOJIS['missile']} Точность ракет: +{self_bonuses['missile_accuracy']*100:.1f}%\n"
        if self_bonuses.get("intercept_difficulty", 0) > 0:
            self_text += f"{EMOJIS['intercept']} Сложность перехвата: +{self_bonuses['intercept_difficulty']*100:.1f}%\n"
        if self_bonuses.get("research_boost", 0) > 0:
            self_text += f"{EMOJIS['research']} Исследования: +{self_bonuses['research_boost']*100:.1f}%\n"
        if self_bonuses.get("gdp_boost", 0) > 0:
            self_text += f"{EMOJIS['gdp']} Рост ВВП: +{self_bonuses['gdp_boost']*100:.1f}%\n"
        if self_bonuses.get("communication_boost", 0) > 0:
            self_text += f"{EMOJIS['communication']} Связь: +{self_bonuses['communication_boost']*100:.1f}%\n"
        if self_bonuses.get("infrastructure_boost", 0) > 0:
            self_text += f"{EMOJIS['infrastructure']} Инфраструктура: +{self_bonuses['infrastructure_boost']*100:.1f}%\n"
        if self_bonuses.get("recon_range", 0) > 0:
            self_text += f"{EMOJIS['recon']} Дальность разведки: +{self_bonuses['recon_range']*100:.1f}%\n"
        
        if self_text:
            embed.add_field(name=f"{EMOJIS['satellite']} Бонусы от собственных спутников", value=self_text, inline=False)
        
        # Бонусы от корпоративных спутников
        corp_bonuses = bonuses["corporate"]
        corp_text = ""
        if corp_bonuses.get("drone_accuracy", 0) > 0:
            corp_text += f"{EMOJIS['drone']} Точность дронов: +{corp_bonuses['drone_accuracy']*100:.1f}%\n"
        if corp_bonuses.get("missile_accuracy", 0) > 0:
            corp_text += f"{EMOJIS['missile']} Точность ракет: +{corp_bonuses['missile_accuracy']*100:.1f}%\n"
        if corp_bonuses.get("research_boost", 0) > 0:
            corp_text += f"{EMOJIS['research']} Исследования: +{corp_bonuses['research_boost']*100:.1f}%\n"
        if corp_bonuses.get("gdp_boost", 0) > 0:
            corp_text += f"{EMOJIS['gdp']} Рост ВВП: +{corp_bonuses['gdp_boost']*100:.1f}%\n"
        if corp_bonuses.get("communication_boost", 0) > 0:
            corp_text += f"{EMOJIS['communication']} Связь: +{corp_bonuses['communication_boost']*100:.1f}%\n"
        
        if corp_text:
            embed.add_field(name=f"{EMOJIS['corporate']} Бонусы от корпоративных спутников", value=corp_text, inline=False)
        
        # Доступные корпоративные спутники
        if corporate_satellites:
            corp_list = ""
            for corp_name, data in list(corporate_satellites.items())[:5]:
                corp_list += f"{EMOJIS['corporate']} **{corp_name}**: {data['total']} спутников\n"
            embed.add_field(name=f"{EMOJIS['corporate']} Доступные корпоративные системы", value=corp_list, inline=False)
        
        view = OverviewMenuView(self.user_id, self.player_data, self.country_name, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_policy_menu(self, interaction: discord.Interaction):
        """Меню политики"""
        embed = discord.Embed(
            title=f"{EMOJIS['satellite']} Политика спутниковой системы",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=SATELLITE_BANNER)
        
        options = [
            discord.SelectOption(label="Корпоративные спутники", value="corp_access", description="Управление доступом к корпоративным системам"),
            discord.SelectOption(label="Собственные спутники", value="own_sats", description="Управление государственными спутниками"),
        ]
        
        view = PolicyMenuView(self.user_id, self.player_data, self.country_name, options, self)
        await interaction.response.edit_message(embed=embed, view=view)


class LaunchMenuView(View):
    """Меню запуска спутников"""
    
    def __init__(self, user_id, player_data, country_name, options, parent_view):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите тип спутника...", options=options)
        select.callback = self.on_type_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def on_type_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        sat_type = interaction.data["values"][0]
        info = SATELLITE_TYPES[sat_type]
        
        modal = LaunchQuantityModal(self.user_id, self.player_data, self.country_name, sat_type, info, self)
        await interaction.response.send_modal(modal)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await show_satellite_menu(interaction, self.user_id)


class LaunchQuantityModal(Modal, title="Запуск спутников"):
    def __init__(self, user_id, player_data, country_name, sat_type, info, parent_view):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.sat_type = sat_type
        self.info = info
        self.parent_view = parent_view
        
        self.quantity_input = TextInput(
            label="Количество",
            placeholder="Введите число от 1 до 100",
            min_length=1,
            max_length=3,
            required=True,
            default="1"
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > 100:
                await interaction.response.send_message(f"{EMOJIS['error']} Количество должно быть от 1 до 100!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message(f"{EMOJIS['error']} Введите корректное число!", ephemeral=True)
            return
        
        # Проверяем возможность запуска
        total_cost_usd = self.info["base_cost_usd"] * quantity
        local_cost = convert_usd_to_local(total_cost_usd, self.country_name)
        total_pp = self.info["pp_cost"] * quantity
        
        current_budget = get_budget(self.player_data["economy"])
        current_pp = get_political_power(self.player_data)
        currency_code = get_currency_code(self.player_data["economy"])
        
        if current_budget < local_cost:
            await interaction.response.send_message(
                f"{EMOJIS['error']} Недостаточно средств!\n"
                f"Требуется: {format_billion(local_cost)} {currency_code}\n"
                f"Доступно: {format_billion(current_budget)} {currency_code}",
                ephemeral=True
            )
            return
        
        if current_pp < total_pp:
            await interaction.response.send_message(
                f"{EMOJIS['error']} Недостаточно политической власти!\n"
                f"Требуется: {total_pp}\n"
                f"Доступно: {current_pp:.1f}",
                ephemeral=True
            )
            return
        
        # Запускаем спутники
        success, message = launch_satellite(self.player_data, self.sat_type, quantity)
        
        if success:
            states = load_states()
            for data in states["players"].values():
                if data.get("assigned_to") == str(self.user_id):
                    data.update(self.player_data)
                    break
            save_states(states)
            
            embed = discord.Embed(
                title=f"{EMOJIS['success']} Спутники запущены!",
                description=f"{self.info['emoji']} **{quantity} x {self.info['name']}** успешно выведены на орбиту!\n\n"
                           f"{EMOJIS['budget']} Затрачено: **{format_billion(local_cost)} {currency_code}**\n"
                           f"{EMOJIS['pp']} Потрачено ПВ: **{total_pp}**",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await show_satellite_menu(interaction, self.user_id)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class OverviewMenuView(View):
    """Меню обзора"""
    
    def __init__(self, user_id, player_data, country_name, parent_view):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.parent_view = parent_view
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await show_satellite_menu(interaction, self.user_id)


class PolicyMenuView(View):
    """Меню политики"""
    
    def __init__(self, user_id, player_data, country_name, options, parent_view):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите раздел...", options=options)
        select.callback = self.on_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        choice = interaction.data["values"][0]
        
        if choice == "corp_access":
            await self.show_corp_access_menu(interaction)
        elif choice == "own_sats":
            await self.show_own_sats_menu(interaction)
    
    async def show_corp_access_menu(self, interaction: discord.Interaction):
        """Меню управления доступом к корпоративным спутникам"""
        owned_corps = get_corporations_owned_by_country(self.country_name)
        
        embed = discord.Embed(
            title=f"{EMOJIS['corporate']} Управление корпоративными спутниками",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=SATELLITE_BANNER)
        
        if owned_corps:
            corp_list = "\n".join([f"• {c}" for c in owned_corps])
            embed.add_field(
                name=f"{EMOJIS['owner']} Ваши корпорации",
                value=f"{corp_list}\n\nВыберите корпорацию для управления доступом:",
                inline=False
            )
            
            options = []
            for corp in owned_corps[:25]:
                options.append(discord.SelectOption(
                    label=corp[:100],
                    value=corp,
                    description="Управление доступом стран"
                ))
            
            view = CorpAccessSelectView(self.user_id, self.player_data, self.country_name, options, self)
        else:
            embed.add_field(
                name=f"{EMOJIS['warning']} Нет корпораций",
                value="Ваша страна не владеет корпоративными спутниковыми системами.",
                inline=False
            )
            view = PolicyMenuView(self.user_id, self.player_data, self.country_name, [], self.parent_view)
            view.clear_items()
            back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
            back_btn.callback = view.back_callback
            view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_own_sats_menu(self, interaction: discord.Interaction):
        """Меню управления собственными спутниками"""
        satellites = get_country_satellites(self.country_name)
        
        embed = discord.Embed(
            title=f"{EMOJIS['satellite']} Управление государственными спутниками",
            description=f"{EMOJIS['military']} Военных: **{satellites.get('military', 0)}**\n"
                       f"{EMOJIS['civilian']} Гражданских: **{satellites.get('civilian', 0)}**",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=SATELLITE_BANNER)
        
        options = []
        if satellites.get("military", 0) > 0:
            options.append(discord.SelectOption(
                label="Вывести из эксплуатации военные спутники",
                value="decommission_military",
                description="Списать устаревшие военные спутники"
            ))
        if satellites.get("civilian", 0) > 0:
            options.append(discord.SelectOption(
                label="Вывести из эксплуатации гражданские спутники",
                value="decommission_civilian",
                description="Списать устаревшие гражданские спутники"
            ))
        
        if options:
            view = OwnSatsSelectView(self.user_id, self.player_data, self.country_name, options, self)
        else:
            embed.add_field(name=f"{EMOJIS['warning']} Нет спутников", value="У вас нет собственных спутников для управления.", inline=False)
            view = PolicyMenuView(self.user_id, self.player_data, self.country_name, [], self.parent_view)
            view.clear_items()
            back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
            back_btn.callback = view.back_callback
            view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await show_satellite_menu(interaction, self.user_id)


class CorpAccessSelectView(View):
    """Выбор корпорации для управления доступом"""
    
    def __init__(self, user_id, player_data, country_name, options, parent_view):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите корпорацию...", options=options)
        select.callback = self.on_corp_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def on_corp_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        corp_name = interaction.data["values"][0]
        await self.show_corp_access_management(interaction, corp_name)
    
    async def show_corp_access_management(self, interaction: discord.Interaction, corp_name: str):
        """Управление доступом к конкретной корпорации"""
        corp_info = CORPORATE_SATELLITE_OWNERS.get(corp_name, {})
        access_data = load_corporate_access()
        
        custom_blocked = access_data.get(corp_name, {}).get("blocked_countries", [])
        custom_allowed = access_data.get(corp_name, {}).get("countries_with_access", [])
        
        embed = discord.Embed(
            title=f"{EMOJIS['corporate']} Управление доступом: {corp_name}",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=SATELLITE_BANNER)
        
        if custom_blocked:
            embed.add_field(name=f"{EMOJIS['block']} Заблокированные страны", value="\n".join(custom_blocked[:10]), inline=False)
        if custom_allowed:
            embed.add_field(name=f"{EMOJIS['unblock']} Разрешённые страны", value="\n".join(custom_allowed[:10]), inline=False)
        
        embed.add_field(
            name="Действия",
            value="Выберите действие из списка ниже:",
            inline=False
        )
        
        options = [
            discord.SelectOption(label="Заблокировать страну", value="block", description="Запретить доступ к спутникам"),
            discord.SelectOption(label="Разблокировать страну", value="unblock", description="Разрешить доступ к спутникам"),
            discord.SelectOption(label="Сбросить к стандартным настройкам", value="reset", description="Вернуть настройки по умолчанию"),
        ]
        
        view = CorpAccessActionView(self.user_id, self.player_data, self.country_name, corp_name, options, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.parent_view.show_corp_access_menu(interaction)


class CorpAccessActionView(View):
    """Действия по управлению доступом к корпорации"""
    
    def __init__(self, user_id, player_data, country_name, corp_name, options, parent_view):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.corp_name = corp_name
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите действие...", options=options)
        select.callback = self.on_action_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def on_action_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        action = interaction.data["values"][0]
        
        if action == "block":
            await self.show_country_select_for_block(interaction)
        elif action == "unblock":
            await self.show_country_select_for_unblock(interaction)
        elif action == "reset":
            access_data = load_corporate_access()
            if self.corp_name in access_data:
                del access_data[self.corp_name]
                save_corporate_access(access_data)
            
            embed = discord.Embed(
                title=f"{EMOJIS['success']} Настройки сброшены",
                description=f"Доступ к {self.corp_name} возвращён к стандартным настройкам.",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=None)
    
    async def show_country_select_for_block(self, interaction: discord.Interaction):
        """Выбор страны для блокировки"""
        states = load_states()
        all_countries = []
        for data in states["players"].values():
            country = data.get("state", {}).get("statename")
            if country and country != self.country_name:
                all_countries.append(country)
        
        all_countries = sorted(list(set(all_countries)))
        
        options = []
        for country in all_countries[:25]:
            options.append(discord.SelectOption(
                label=country[:100],
                value=country,
                description="Заблокировать доступ"
            ))
        
        embed = discord.Embed(
            title=f"{EMOJIS['block']} Выберите страну для блокировки",
            description="Выбранная страна потеряет доступ к спутникам этой корпорации.",
            color=DARK_THEME_COLOR
        )
        
        view = BlockCountrySelectView(self.user_id, self.player_data, self.country_name, self.corp_name, options, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_country_select_for_unblock(self, interaction: discord.Interaction):
        """Выбор страны для разблокировки"""
        access_data = load_corporate_access()
        blocked = access_data.get(self.corp_name, {}).get("blocked_countries", [])
        
        if not blocked:
            embed = discord.Embed(
                title=f"{EMOJIS['warning']} Нет заблокированных стран",
                description="Нет стран с пользовательской блокировкой.",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        options = []
        for country in blocked[:25]:
            options.append(discord.SelectOption(
                label=country[:100],
                value=country,
                description="Разблокировать доступ"
            ))
        
        embed = discord.Embed(
            title=f"{EMOJIS['unblock']} Выберите страну для разблокировки",
            description="Выбранная страна получит доступ к спутникам этой корпорации.",
            color=DARK_THEME_COLOR
        )
        
        view = UnblockCountrySelectView(self.user_id, self.player_data, self.country_name, self.corp_name, options, self)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.parent_view.show_corp_access_management(interaction, self.corp_name)


class BlockCountrySelectView(View):
    """Выбор страны для блокировки"""
    
    def __init__(self, user_id, player_data, country_name, corp_name, options, parent_view):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.corp_name = corp_name
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите страну...", options=options)
        select.callback = self.on_country_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def on_country_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        target_country = interaction.data["values"][0]
        
        access_data = load_corporate_access()
        if self.corp_name not in access_data:
            access_data[self.corp_name] = {"blocked_countries": [], "countries_with_access": []}
        
        if target_country not in access_data[self.corp_name]["blocked_countries"]:
            access_data[self.corp_name]["blocked_countries"].append(target_country)
        save_corporate_access(access_data)
        
        embed = discord.Embed(
            title=f"{EMOJIS['success']} Страна заблокирована",
            description=f"**{target_country}** больше не имеет доступа к **{self.corp_name}**.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.parent_view.show_country_select_for_block(interaction)


class UnblockCountrySelectView(View):
    """Выбор страны для разблокировки"""
    
    def __init__(self, user_id, player_data, country_name, corp_name, options, parent_view):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.corp_name = corp_name
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите страну...", options=options)
        select.callback = self.on_country_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def on_country_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        target_country = interaction.data["values"][0]
        
        access_data = load_corporate_access()
        if self.corp_name in access_data:
            if target_country in access_data[self.corp_name].get("blocked_countries", []):
                access_data[self.corp_name]["blocked_countries"].remove(target_country)
                if not access_data[self.corp_name].get("blocked_countries") and not access_data[self.corp_name].get("countries_with_access"):
                    del access_data[self.corp_name]
                save_corporate_access(access_data)
        
        embed = discord.Embed(
            title=f"{EMOJIS['success']} Страна разблокирована",
            description=f"**{target_country}** получила доступ к **{self.corp_name}**.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.parent_view.show_country_select_for_unblock(interaction)


class OwnSatsSelectView(View):
    """Управление собственными спутниками"""
    
    def __init__(self, user_id, player_data, country_name, options, parent_view):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.parent_view = parent_view
        
        select = Select(placeholder="Выберите действие...", options=options)
        select.callback = self.on_select
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        action = interaction.data["values"][0]
        
        if action == "decommission_military":
            modal = DecommissionModal(self.user_id, self.player_data, self.country_name, "military", self)
        else:
            modal = DecommissionModal(self.user_id, self.player_data, self.country_name, "civilian", self)
        
        await interaction.response.send_modal(modal)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.parent_view.show_own_sats_menu(interaction)


class DecommissionModal(Modal, title="Вывод из эксплуатации"):
    def __init__(self, user_id, player_data, country_name, sat_type, parent_view):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.sat_type = sat_type
        self.parent_view = parent_view
        
        satellites = get_country_satellites(country_name)
        max_count = satellites.get(sat_type, 0)
        type_name = "военных" if sat_type == "military" else "гражданских"
        
        self.quantity_input = TextInput(
            label=f"Количество {type_name} спутников (макс: {max_count})",
            placeholder="Введите число",
            min_length=1,
            max_length=4,
            required=True
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        satellites = get_country_satellites(self.country_name)
        max_count = satellites.get(self.sat_type, 0)
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > max_count:
                await interaction.response.send_message(f"{EMOJIS['error']} Количество должно быть от 1 до {max_count}!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message(f"{EMOJIS['error']} Введите корректное число!", ephemeral=True)
            return
        
        satellites[self.sat_type] = max_count - quantity
        update_country_satellites(self.country_name, satellites)
        
        type_name = "военных" if self.sat_type == "military" else "гражданских"
        embed = discord.Embed(
            title=f"{EMOJIS['success']} Спутники выведены из эксплуатации",
            description=f"Списано **{quantity}** {type_name} спутников.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await show_satellite_menu(interaction, self.user_id)


# ==================== ЕЖЕГОДНОЕ ОБСЛУЖИВАНИЕ ====================

async def satellite_maintenance_loop(bot_instance):
    """Фоновая задача для ежегодного обслуживания спутников"""
    await bot_instance.wait_until_ready()
    
    while not bot_instance.is_closed():
        try:
            states = load_states()
            satellites_data = load_satellites()
            now = datetime.now()
            
            for country_name, sat_data in satellites_data.get("satellites", {}).items():
                player_data = None
                for data in states.get("players", {}).values():
                    if data and isinstance(data, dict) and data.get("state", {}).get("statename") == country_name:
                        player_data = data
                        break
                
                if not player_data or "assigned_to" not in player_data:
                    continue
                
                last_maintenance_str = sat_data.get("last_maintenance", str(now))
                days_passed = days_since_last_event(last_maintenance_str)
                
                if days_passed >= 365:
                    military_count = sat_data.get("military", 0)
                    civilian_count = sat_data.get("civilian", 0)
                    
                    mil_cost_usd = military_count * SATELLITE_TYPES["military"]["maintenance_cost_usd"]
                    civ_cost_usd = civilian_count * SATELLITE_TYPES["civilian"]["maintenance_cost_usd"]
                    total_cost_usd = mil_cost_usd + civ_cost_usd
                    
                    local_cost = convert_usd_to_local(total_cost_usd, country_name)
                    current_budget = get_budget(player_data["economy"])
                    currency_code = get_currency_code(player_data["economy"])
                    
                    if current_budget >= local_cost:
                        subtract_from_budget(player_data["economy"], local_cost)
                        sat_data["last_maintenance"] = str(now)
                        
                        if total_cost_usd > 100_000_000:
                            try:
                                user = await bot_instance.fetch_user(int(player_data["assigned_to"]))
                                if user:
                                    embed = discord.Embed(
                                        title=f"{EMOJIS['satellite']} Обслуживание спутников",
                                        description=f"{EMOJIS['debt']} Списано {format_billion(local_cost)} {currency_code} за годовое обслуживание",
                                        color=DARK_THEME_COLOR
                                    )
                                    await user.send(embed=embed)
                            except:
                                pass
                    else:
                        shortfall = local_cost - current_budget
                        loss_ratio = shortfall / local_cost if local_cost > 0 else 0
                        
                        lost_military = min(military_count, max(1, int(military_count * loss_ratio)))
                        lost_civilian = min(civilian_count, max(1, int(civilian_count * loss_ratio)))
                        
                        sat_data["military"] = max(0, military_count - lost_military)
                        sat_data["civilian"] = max(0, civilian_count - lost_civilian)
                        player_data["economy"]["budget"] = 0
                        
                        try:
                            user = await bot_instance.fetch_user(int(player_data["assigned_to"]))
                            if user:
                                embed = discord.Embed(
                                    title=f"{EMOJIS['warning']} Потеря спутников",
                                    description=f"{EMOJIS['error']} Не хватило средств на обслуживание!",
                                    color=discord.Color.red()
                                )
                                if lost_military > 0:
                                    embed.add_field(name=f"{EMOJIS['military']} Потеряно военных", value=str(lost_military), inline=True)
                                if lost_civilian > 0:
                                    embed.add_field(name=f"{EMOJIS['civilian']} Потеряно гражданских", value=str(lost_civilian), inline=True)
                                await user.send(embed=embed)
                        except:
                            pass
                        
                        sat_data["last_maintenance"] = str(now)
            
            save_states(states)
            save_satellites(satellites_data)
            
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"Ошибка в satellite_maintenance_loop: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(3600)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_satellite_menu',
    'satellite_maintenance_loop',
    'get_total_satellite_bonuses',
    'get_satellite_bonuses',
    'get_intercept_difficulty_boost',
    'SATELLITE_TYPES',
    'STARTING_SATELLITES',
    'get_country_corporate_satellites',
    'EMOJIS'
]

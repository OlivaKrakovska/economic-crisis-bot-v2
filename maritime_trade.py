# maritime_trade.py - МУЛЬТИВАЛЮТНАЯ ВЕРСИЯ С ГИБРИДНОЙ СИСТЕМОЙ ОПЛАТЫ
# Пошлины: всегда USD
# Оплата продавцу: в валюте страны-покупателя (порт назначения)
# Версия с поддержкой новой структуры активов (словари с total/ownership)

import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import json
import random
import math
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR, EXCHANGE_RATES_2019
from trade_tariffs import TariffSystem
from resource_system import RESOURCE_PRICES

# Импортируем функции для работы с корпорациями
try:
    from civil_corporations_db import (
        get_all_civil_corporations, get_civil_corporation,
        load_corporations_state, save_corporations_state,
        get_civil_corporations_by_country
    )
    CIVIL_CORPORATIONS_AVAILABLE = True
except ImportError:
    print("⚠️ Модуль civil_corporations_db не найден. Морская торговля будет работать ограниченно.")
    CIVIL_CORPORATIONS_AVAILABLE = False
    
    def get_all_civil_corporations():
        return []
    
    def get_civil_corporation(corp_id):
        return None
    
    def get_civil_corporations_by_country(country):
        return {}
    
    def load_corporations_state():
        return {"corporations": {}}
    
    def save_corporations_state(state):
        pass


# ==================== ФАЙЛЫ ДЛЯ ХРАНЕНИЯ ДАННЫХ ====================

MARITIME_DATA_FILE = 'maritime_data.json'
SHIPPING_LANES_FILE = 'shipping_lanes.json'
SHIP_LOGS_FILE = 'ship_logs.json'
PRIORITY_REGIONS_FILE = 'priority_regions.json'
TRADE_HISTORY_FILE = 'trade_history.json'

_trade_allowed_cache = {}
_trade_allowed_cache_time = {}
CACHE_TTL = 300


# ==================== ВАЛЮТЫ СТРАН ====================

CURRENCY_CODES = {
    "США": "USD", "Россия": "RUB", "Китай": "CNY", "Украина": "UAH",
    "Германия": "EUR", "Франция": "EUR", "Великобритания": "GBP",
    "Норвегия": "NOK", "Швеция": "SEK", "Финляндия": "EUR",
    "Польша": "PLN", "Иран": "IRR", "Израиль": "ILS",
    "Сирия": "SYP", "Бразилия": "BRL", "Турция": "TRY",
    "Египет": "EGP", "Швейцария": "CHF", "Канада": "CAD",
    "КНДР": "KPW", "Япония": "JPY", "Беларусь": "BYN",
}

def get_currency_code_from_country(country_name: str) -> str:
    """Возвращает код валюты страны"""
    return CURRENCY_CODES.get(country_name, "USD")


# ==================== ИСТОРИЯ ТОРГОВЛИ ====================

class TradeHistory:
    """Класс для хранения истории торговли"""
    def __init__(self):
        self.history = {}
    
    def add_record(self, country: str, ship_count: int, cargo_value: float):
        if country not in self.history:
            self.history[country] = []
        
        self.history[country].append({
            "timestamp": datetime.now(),
            "ship_count": ship_count,
            "cargo_value": cargo_value
        })
        
        if len(self.history[country]) > 30:
            self.history[country] = self.history[country][-30:]
    
    def get_history(self, country: str, days: int = 14) -> List[Dict]:
        if country not in self.history:
            return []
        return self.history[country][-days:]
    
    def get_all_countries(self) -> List[str]:
        return list(self.history.keys())

_trade_history = TradeHistory()

def load_trade_history():
    global _trade_history
    try:
        with open(TRADE_HISTORY_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for country, records in data.items():
                _trade_history.history[country] = []
                for record in records:
                    _trade_history.history[country].append({
                        "timestamp": datetime.fromisoformat(record["timestamp"]),
                        "ship_count": record["ship_count"],
                        "cargo_value": record["cargo_value"]
                    })
    except (FileNotFoundError, json.JSONDecodeError):
        pass

def save_trade_history():
    data = {}
    for country, records in _trade_history.history.items():
        data[country] = []
        for record in records:
            data[country].append({
                "timestamp": record["timestamp"].isoformat(),
                "ship_count": record["ship_count"],
                "cargo_value": record["cargo_value"]
            })
    with open(TRADE_HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== ГЛОБАЛЬНЫЙ КЭШ ИНФРАСТРУКТУРЫ ====================

_COASTAL_REGIONS_CACHE = None
_COASTAL_REGIONS_LAST_UPDATE = None
_COASTAL_REGIONS_CACHE_TTL = 3600


def get_coastal_regions(force_refresh: bool = False) -> Dict[str, Dict]:
    global _COASTAL_REGIONS_CACHE, _COASTAL_REGIONS_LAST_UPDATE
    now = datetime.now()
    
    if not force_refresh and _COASTAL_REGIONS_CACHE is not None and _COASTAL_REGIONS_LAST_UPDATE is not None:
        if (now - _COASTAL_REGIONS_LAST_UPDATE).total_seconds() < _COASTAL_REGIONS_CACHE_TTL:
            return _COASTAL_REGIONS_CACHE
    
    print("Загрузка инфраструктуры для морской торговли...")
    try:
        from infra_build import load_infrastructure
        infra = load_infrastructure()
    except Exception as e:
        print(f"Ошибка загрузки инфраструктуры: {e}")
        return _COASTAL_REGIONS_CACHE or {}
    
    coastal_regions = {}
    for country_id, country_data in infra.get("infrastructure", {}).items():
        country_name = country_data.get("country")
        if not country_name:
            continue
        for econ_region, econ_data in country_data.get("economic_regions", {}).items():
            for region_name, region_data in econ_data.get("regions", {}).items():
                is_coastal = region_data.get("coastal", False)
                shipyards_data = region_data.get("shipyards", 0)
                # Поддержка нового формата активов
                if isinstance(shipyards_data, dict):
                    shipyards = shipyards_data.get("total", 0)
                else:
                    shipyards = shipyards_data
                    
                if is_coastal:
                    coastal_regions[region_name] = {
                        "country": country_name,
                        "shipyards": shipyards,
                        "population": region_data.get("population", 0),
                        "economic_region": econ_region,
                        "development_level": region_data.get("development_level", 50)
                    }
    
    _COASTAL_REGIONS_CACHE = coastal_regions
    _COASTAL_REGIONS_LAST_UPDATE = now
    print(f"Загружено {len(coastal_regions)} прибрежных регионов")
    return coastal_regions


def invalidate_coastal_cache():
    global _COASTAL_REGIONS_CACHE, _COASTAL_REGIONS_LAST_UPDATE
    _COASTAL_REGIONS_CACHE = None
    _COASTAL_REGIONS_LAST_UPDATE = None


def get_regions_by_country(country_name: str) -> List[str]:
    coastal_regions = get_coastal_regions()
    return [name for name, data in coastal_regions.items() if data["country"] == country_name]


def get_region_shipyards(region_name: str) -> int:
    coastal_regions = get_coastal_regions()
    if region_name in coastal_regions:
        return coastal_regions[region_name]["shipyards"]
    return 0


def is_region_operational(region_name: str) -> Tuple[bool, int]:
    shipyards = get_region_shipyards(region_name)
    # Поддержка нового формата активов (на всякий случай)
    if isinstance(shipyards, dict):
        shipyards = shipyards.get("total", 0)
    return shipyards > 0, shipyards


def get_region_capacity(region_name: str) -> int:
    operational, shipyards = is_region_operational(region_name)
    if not operational:
        return 0
    return 5 + shipyards * 2


def get_country_from_region(region_name: str) -> Optional[str]:
    coastal_regions = get_coastal_regions()
    if region_name in coastal_regions:
        return coastal_regions[region_name]["country"]
    return None


def get_sea_zone_from_region(region_name: str):
    from navy import SeaZone
    if region_name in PORTS:
        return PORTS[region_name]["sea_region"]
    elif region_name in REGION_TO_PORT:
        port = REGION_TO_PORT[region_name]
        if port in PORTS:
            return PORTS[port]["sea_region"]
    return None


# ==================== ТОРГОВЫЕ ОГРАНИЧЕНИЯ ====================

TRADE_RESTRICTIONS = {
    "Россия": {
        "embargo_against": ["Украина"],
        "sanctions_by": ["США", "Великобритания", "Канада", "Австралия", "Германия", "Франция"],
        "trade_allowed_with": ["Китай", "Индия", "Турция", "Бразилия", "Египет", "Израиль", "Норвегия", "Швеция", "Финляндия"]
    },
    "Китай": {
        "trade_war_with": ["США"],
        "trade_allowed_with": ["Россия", "Германия", "Франция", "Великобритания", "Япония", "Бразилия"]
    },
    "США": {
        "embargo_against": ["Иран", "Сирия", "КНДР"],
        "trade_war_with": ["Китай"],
        "trade_allowed_with": ["Германия", "Франция", "Великобритания", "Япония", "Израиль", "Канада", "Бразилия"]
    },
    "Иран": {
        "embargo_against": ["Израиль", "США"],
        "sanctions_by": ["США", "Великобритания", "Канада", "Германия", "Франция"],
        "trade_allowed_with": ["Китай", "Россия", "Турция", "КНДР", "Сирия"]
    },
    "Израиль": {
        "embargo_against": ["Иран", "Сирия"],
        "trade_allowed_with": ["США", "Германия", "Франция", "Великобритания", "Канада", "Россия", "Китай"]
    },
    "Украина": {
        "embargo_against": ["Россия", "КНДР", "Сирия"],
        "trade_allowed_with": ["США", "Германия", "Франция", "Великобритания", "Канада", "Польша", "Турция"]
    },
    "Сирия": {
        "embargo_against": ["США", "Израиль"],
        "sanctions_by": ["США", "Великобритания", "Канада"],
        "trade_allowed_with": ["Россия", "Иран", "Китай", "КНДР"]
    },
    "КНДР": {
        "embargo_against": ["США", "Япония", "Южная Корея"],
        "sanctions_by": ["США", "Великобритания", "Япония", "Южная Корея"],
        "trade_allowed_with": ["Китай", "Россия", "Иран", "Сирия"]
    },
    "Турция": {
        "trade_allowed_with": ["Россия", "США", "Германия", "Франция", "Великобритания", "Китай", "Иран", "Израиль"]
    }
}


def get_trade_restrictions(country: str) -> Dict:
    return TRADE_RESTRICTIONS.get(country, {"embargo_against": [], "sanctions_by": [], "trade_allowed_with": []})


def is_trade_allowed(country1: str, country2: str) -> bool:
    if country1 == country2:
        return True
    
    cache_key = f"{country1}:{country2}"
    if cache_key in _trade_allowed_cache_time:
        if (datetime.now() - _trade_allowed_cache_time[cache_key]).seconds < CACHE_TTL:
            return _trade_allowed_cache.get(cache_key, True)
    
    states = load_states()
    existing_countries = [data["state"]["statename"] for data in states["players"].values()]
    
    if country1 not in existing_countries or country2 not in existing_countries:
        _trade_allowed_cache[cache_key] = True
        _trade_allowed_cache_time[cache_key] = datetime.now()
        return True
    
    restrictions1 = get_trade_restrictions(country1)
    restrictions2 = get_trade_restrictions(country2)
    
    if country2 in restrictions1.get("embargo_against", []):
        _trade_allowed_cache[cache_key] = False
        _trade_allowed_cache_time[cache_key] = datetime.now()
        return False
    
    if country1 in restrictions2.get("embargo_against", []):
        _trade_allowed_cache[cache_key] = False
        _trade_allowed_cache_time[cache_key] = datetime.now()
        return False
    
    if country2 in restrictions1.get("sanctions_by", []):
        _trade_allowed_cache[cache_key] = False
        _trade_allowed_cache_time[cache_key] = datetime.now()
        return False
    
    if country1 in restrictions2.get("sanctions_by", []):
        _trade_allowed_cache[cache_key] = False
        _trade_allowed_cache_time[cache_key] = datetime.now()
        return False
    
    allowed1 = restrictions1.get("trade_allowed_with", [])
    allowed2 = restrictions2.get("trade_allowed_with", [])
    
    if allowed1 and country2 not in allowed1:
        _trade_allowed_cache[cache_key] = False
        _trade_allowed_cache_time[cache_key] = datetime.now()
        return False
    
    if allowed2 and country1 not in allowed2:
        _trade_allowed_cache[cache_key] = False
        _trade_allowed_cache_time[cache_key] = datetime.now()
        return False
    
    _trade_allowed_cache[cache_key] = True
    _trade_allowed_cache_time[cache_key] = datetime.now()
    return True


# ==================== КАТЕГОРИИ РЕСУРСОВ ====================

PRIORITY_CATEGORIES = {
    "military": {
        "name": "Военная техника",
        "resources": [
            "tanks", "btr", "bmp", "armored_vehicles", "self_propelled_artillery",
            "towed_artillery", "mlrs", "atgm_complexes", "otr_complexes",
            "fighters", "attack_aircraft", "bombers", "attack_helicopters",
            "destroyers", "corvettes", "submarines", "drones", "fpv_drones"
        ]
    },
    "resources": {
        "name": "Природные ресурсы",
        "resources": ["oil", "gas", "coal", "steel", "aluminum", "uranium", "rare_metals"]
    },
    "industrial": {
        "name": "Промышленное оборудование",
        "resources": [
            "industrial_equipment", "machine_tools", "industrial_robots",
            "energy_equipment", "electrical_equipment", "aerospace_equipment",
            "construction_machinery", "agricultural_machinery"
        ]
    },
    "consumer": {
        "name": "Потребительские товары",
        "resources": [
            "cars", "trucks", "buses", "consumer_electronics", "clothing",
            "furniture", "household_goods", "food_products", "pharmaceuticals",
            "medical_supplies", "medical_equipment", "sanitary_products"
        ]
    },
    "chemical": {
        "name": "Химическая продукция",
        "resources": ["chemicals", "fertilizers", "pharmaceuticals", "auto_parts"]
    },
    "tech": {
        "name": "Высокие технологии",
        "resources": [
            "telecom_equipment", "tech_equipment", "aerospace_equipment",
            "industrial_robots", "drones", "fpv_drones", "consumer_electronics"
        ]
    }
}


# ==================== МОРСКИЕ РЕГИОНЫ ====================

class SeaRegion(Enum):
    NORWEGIAN_SEA = "Норвежское море"
    NORTH_SEA = "Северное море"
    BALTIC_SEA = "Балтийское море"
    BAY_OF_BISCAY = "Бискайский залив"
    ENGLISH_CHANNEL = "Ла-Манш"
    IRISH_SEA = "Ирландское море"
    WHITE_SEA = "Белое море"
    WESTERN_MEDITERRANEAN = "Западное Средиземноморье"
    CENTRAL_MEDITERRANEAN = "Центральное Средиземноморье"
    EASTERN_MEDITERRANEAN = "Восточное Средиземноморье"
    ADRIATIC_SEA = "Адриатическое море"
    AEGEAN_SEA = "Эгейское море"
    BLACK_SEA = "Черное море"
    SEA_OF_MARMARA = "Мраморное море"
    PERSIAN_GULF = "Персидский залив"
    RED_SEA = "Красное море"
    GULF_OF_ADEN = "Аденский залив"
    ARABIAN_SEA = "Аравийское море"
    SOUTH_CHINA_SEA = "Южно-Китайское море"
    EAST_CHINA_SEA = "Восточно-Китайское море"
    YELLOW_SEA = "Желтое море"
    SEA_OF_JAPAN = "Японское море"
    SEA_OF_OKHOTSK = "Охотское море"
    PHILIPPINE_SEA = "Филиппинское море"
    CARIBBEAN_SEA = "Карибское море"
    GULF_OF_MEXICO = "Мексиканский залив"
    LABRADOR_SEA = "Море Лабрадор"
    GULF_OF_ALASKA = "Залив Аляска"
    CALIFORNIA_CURRENT = "Калифорнийское течение"
    BERING_SEA = "Берингово море"
    NORTH_ATLANTIC = "Северная Атлантика"
    SOUTH_ATLANTIC = "Южная Атлантика"
    BARENTS_SEA = "Баренцево море"
    ARCTIC_OCEAN = "Северный Ледовитый океан"
    PACIFIC_OCEAN = "Тихий океан"


SEA_REGIONS = {
    "Европа": [SeaRegion.NORWEGIAN_SEA, SeaRegion.NORTH_SEA, SeaRegion.BALTIC_SEA, SeaRegion.BAY_OF_BISCAY, SeaRegion.ENGLISH_CHANNEL, SeaRegion.IRISH_SEA, SeaRegion.WHITE_SEA],
    "Средиземное море": [SeaRegion.WESTERN_MEDITERRANEAN, SeaRegion.CENTRAL_MEDITERRANEAN, SeaRegion.EASTERN_MEDITERRANEAN, SeaRegion.ADRIATIC_SEA, SeaRegion.AEGEAN_SEA, SeaRegion.BLACK_SEA, SeaRegion.SEA_OF_MARMARA],
    "Ближний Восток": [SeaRegion.PERSIAN_GULF, SeaRegion.RED_SEA, SeaRegion.GULF_OF_ADEN, SeaRegion.ARABIAN_SEA],
    "Азия": [SeaRegion.SOUTH_CHINA_SEA, SeaRegion.EAST_CHINA_SEA, SeaRegion.YELLOW_SEA, SeaRegion.SEA_OF_JAPAN, SeaRegion.SEA_OF_OKHOTSK, SeaRegion.PHILIPPINE_SEA],
    "Америка": [SeaRegion.CARIBBEAN_SEA, SeaRegion.GULF_OF_MEXICO, SeaRegion.LABRADOR_SEA, SeaRegion.GULF_OF_ALASKA, SeaRegion.CALIFORNIA_CURRENT, SeaRegion.BERING_SEA],
    "Атлантика": [SeaRegion.NORTH_ATLANTIC, SeaRegion.SOUTH_ATLANTIC]
}


# ==================== ПОРТЫ ====================
PORTS = {
    "Нью-Йорк": {"country": "США", "sea_region": SeaRegion.NORTH_ATLANTIC, "lat": 40.71, "lon": -74.01},
    "Лос-Анджелес": {"country": "США", "sea_region": SeaRegion.CALIFORNIA_CURRENT, "lat": 34.05, "lon": -118.24},
    "Хьюстон": {"country": "США", "sea_region": SeaRegion.GULF_OF_MEXICO, "lat": 29.76, "lon": -95.37},
    "Сиэтл": {"country": "США", "sea_region": SeaRegion.GULF_OF_ALASKA, "lat": 47.61, "lon": -122.33},
    "Санкт-Петербург": {"country": "Россия", "sea_region": SeaRegion.BALTIC_SEA, "lat": 59.93, "lon": 30.36},
    "Новороссийск": {"country": "Россия", "sea_region": SeaRegion.BLACK_SEA, "lat": 44.72, "lon": 37.77},
    "Владивосток": {"country": "Россия", "sea_region": SeaRegion.SEA_OF_JAPAN, "lat": 43.12, "lon": 131.89},
    "Мурманск": {"country": "Россия", "sea_region": SeaRegion.BARENTS_SEA, "lat": 68.97, "lon": 33.08},
    "Калининград": {"country": "Россия", "sea_region": SeaRegion.BALTIC_SEA, "lat": 54.71, "lon": 20.51},
    "Архангельск": {"country": "Россия", "sea_region": SeaRegion.WHITE_SEA, "lat": 64.54, "lon": 40.54},
    "Шанхай": {"country": "Китай", "sea_region": SeaRegion.EAST_CHINA_SEA, "lat": 31.23, "lon": 121.47},
    "Гуанчжоу": {"country": "Китай", "sea_region": SeaRegion.SOUTH_CHINA_SEA, "lat": 23.13, "lon": 113.26},
    "Циндао": {"country": "Китай", "sea_region": SeaRegion.YELLOW_SEA, "lat": 36.07, "lon": 120.38},
    "Тяньцзинь": {"country": "Китай", "sea_region": SeaRegion.YELLOW_SEA, "lat": 39.34, "lon": 117.36},
    "Гамбург": {"country": "Германия", "sea_region": SeaRegion.NORTH_SEA, "lat": 53.55, "lon": 9.99},
    "Бремерхафен": {"country": "Германия", "sea_region": SeaRegion.NORTH_SEA, "lat": 53.55, "lon": 8.58},
    "Лондон": {"country": "Великобритания", "sea_region": SeaRegion.NORTH_SEA, "lat": 51.51, "lon": -0.13},
    "Ливерпуль": {"country": "Великобритания", "sea_region": SeaRegion.IRISH_SEA, "lat": 53.41, "lon": -2.99},
    "Саутгемптон": {"country": "Великобритания", "sea_region": SeaRegion.ENGLISH_CHANNEL, "lat": 50.90, "lon": -1.40},
    "Марсель": {"country": "Франция", "sea_region": SeaRegion.WESTERN_MEDITERRANEAN, "lat": 43.30, "lon": 5.37},
    "Гавр": {"country": "Франция", "sea_region": SeaRegion.ENGLISH_CHANNEL, "lat": 49.49, "lon": 0.10},
    "Токио": {"country": "Япония", "sea_region": SeaRegion.PHILIPPINE_SEA, "lat": 35.68, "lon": 139.76},
    "Иокогама": {"country": "Япония", "sea_region": SeaRegion.PHILIPPINE_SEA, "lat": 35.44, "lon": 139.64},
    "Осака": {"country": "Япония", "sea_region": SeaRegion.PHILIPPINE_SEA, "lat": 34.69, "lon": 135.50},
    "Хайфа": {"country": "Израиль", "sea_region": SeaRegion.EASTERN_MEDITERRANEAN, "lat": 32.79, "lon": 34.99},
    "Ашдод": {"country": "Израиль", "sea_region": SeaRegion.EASTERN_MEDITERRANEAN, "lat": 31.80, "lon": 34.64},
    "Одесса": {"country": "Украина", "sea_region": SeaRegion.BLACK_SEA, "lat": 46.48, "lon": 30.73},
    "Николаев": {"country": "Украина", "sea_region": SeaRegion.BLACK_SEA, "lat": 46.97, "lon": 32.00},
    "Бендер-Аббас": {"country": "Иран", "sea_region": SeaRegion.PERSIAN_GULF, "lat": 27.18, "lon": 56.26},
    "Бушир": {"country": "Иран", "sea_region": SeaRegion.PERSIAN_GULF, "lat": 28.92, "lon": 50.83},
    "Стамбул": {"country": "Турция", "sea_region": SeaRegion.SEA_OF_MARMARA, "lat": 41.01, "lon": 28.98},
    "Измир": {"country": "Турция", "sea_region": SeaRegion.AEGEAN_SEA, "lat": 38.42, "lon": 27.13},
    "Мерсин": {"country": "Турция", "sea_region": SeaRegion.EASTERN_MEDITERRANEAN, "lat": 36.80, "lon": 34.63},
    "Ванкувер": {"country": "Канада", "sea_region": SeaRegion.GULF_OF_ALASKA, "lat": 49.28, "lon": -123.12},
    "Монреаль": {"country": "Канада", "sea_region": SeaRegion.NORTH_ATLANTIC, "lat": 45.50, "lon": -73.57},
    "Галифакс": {"country": "Канада", "sea_region": SeaRegion.NORTH_ATLANTIC, "lat": 44.65, "lon": -63.58},
    "Гданьск": {"country": "Польша", "sea_region": SeaRegion.BALTIC_SEA, "lat": 54.35, "lon": 18.65},
    "Щецин": {"country": "Польша", "sea_region": SeaRegion.BALTIC_SEA, "lat": 53.43, "lon": 14.55},
    "Сантос": {"country": "Бразилия", "sea_region": SeaRegion.SOUTH_ATLANTIC, "lat": -23.96, "lon": -46.33},
    "Рио-де-Жанейро": {"country": "Бразилия", "sea_region": SeaRegion.SOUTH_ATLANTIC, "lat": -22.91, "lon": -43.17},
    "Гётеборг": {"country": "Швеция", "sea_region": SeaRegion.NORTH_SEA, "lat": 57.71, "lon": 11.97},
    "Стокгольм": {"country": "Швеция", "sea_region": SeaRegion.BALTIC_SEA, "lat": 59.33, "lon": 18.06},
    "Хельсинки": {"country": "Финляндия", "sea_region": SeaRegion.BALTIC_SEA, "lat": 60.17, "lon": 24.94},
    "Турку": {"country": "Финляндия", "sea_region": SeaRegion.BALTIC_SEA, "lat": 60.45, "lon": 22.27},
    "Осло": {"country": "Норвегия", "sea_region": SeaRegion.NORWEGIAN_SEA, "lat": 59.91, "lon": 10.75},
    "Берген": {"country": "Норвегия", "sea_region": SeaRegion.NORWEGIAN_SEA, "lat": 60.39, "lon": 5.32},
    "Александрия": {"country": "Египет", "sea_region": SeaRegion.EASTERN_MEDITERRANEAN, "lat": 31.20, "lon": 29.92},
    "Суэц": {"country": "Египет", "sea_region": SeaRegion.RED_SEA, "lat": 29.97, "lon": 32.53},
    "Порт-Саид": {"country": "Египет", "sea_region": SeaRegion.EASTERN_MEDITERRANEAN, "lat": 31.25, "lon": 32.28},
    "Нампхо": {"country": "КНДР", "sea_region": SeaRegion.YELLOW_SEA, "lat": 38.73, "lon": 125.39},
    "Вонсан": {"country": "КНДР", "sea_region": SeaRegion.SEA_OF_JAPAN, "lat": 39.15, "lon": 127.44},
    "Латакия": {"country": "Сирия", "sea_region": SeaRegion.EASTERN_MEDITERRANEAN, "lat": 35.52, "lon": 35.78},
    "Тартус": {"country": "Сирия", "sea_region": SeaRegion.EASTERN_MEDITERRANEAN, "lat": 34.89, "lon": 35.89},
}

REGION_TO_PORT = {
    "Нью-Йорк": "Нью-Йорк", "Калифорния": "Лос-Анджелес", "Техас": "Хьюстон",
    "Вашингтон (штат)": "Сиэтл", "Луизиана": "Хьюстон", "Вирджиния": "Нью-Йорк",
    "Флорида": "Хьюстон", "Массачусетс": "Нью-Йорк", "Коннектикут": "Нью-Йорк",
    "г. Санкт-Петербург": "Санкт-Петербург", "Ленинградская область": "Санкт-Петербург",
    "Краснодарский край": "Новороссийск", "Приморский край": "Владивосток",
    "Мурманская область": "Мурманск", "Калининградская область": "Калининград",
    "Архангельская область": "Архангельск", "Республика Карелия": "Мурманск",
    "Ямало-Ненецкий АО": "Архангельск", "Ненецкий АО": "Архангельск",
    "Сахалинская область": "Владивосток", "Камчатский край": "Владивосток",
    "Магаданская область": "Владивосток", "Чукотский АО": "Владивосток",
    "Республика Крым": "Новороссийск", "г. Севастополь": "Новороссийск",
    "Шанхай": "Шанхай", "Гуандун": "Гуанчжоу", "Ляонин": "Циндао",
    "Тяньцзинь": "Тяньцзинь", "Фуцзянь": "Гуанчжоу", "Шаньдун": "Циндао",
    "Хэбэй": "Тяньцзинь", "Цзянсу": "Шанхай", "Чжэцзян": "Шанхай", "Хайнань": "Гуанчжоу",
    "Гамбург": "Гамбург", "Бремен": "Бремерхафен", "Нижняя Саксония": "Гамбург",
    "Шлезвиг-Гольштейн": "Гамбург", "Мекленбург-Передняя Померания": "Гамбург",
    "Лондон": "Лондон", "Ливерпуль": "Ливерпуль", "Саутгемптон": "Саутгемптон",
    "Плимут": "Саутгемптон", "Эдинбург": "Лондон", "Глазго": "Ливерпуль",
    "Абердин": "Лондон", "Белфаст": "Ливерпуль", "Кардифф": "Ливерпуль",
    "Марсель": "Марсель", "Гавр": "Гавр", "Брест": "Гавр", "Нант": "Гавр",
    "Тулон": "Марсель", "Монпелье": "Марсель", "Токио": "Токио", "Иокогама": "Иокогама",
    "Осака": "Осака", "Кобе": "Осака", "Нагоя": "Токио", "Фукуока": "Токио",
    "Тель-Авивский округ": "Хайфа", "Хайфский округ": "Хайфа", "Южный округ": "Ашдод",
    "Одеська область": "Одесса", "Миколаївська область": "Николаев",
    "Херсонська область": "Одесса", "Донецька область": "Одесса", "Запорізька область": "Одесса",
    "Хузестан": "Бендер-Аббас", "Бушир": "Бушир", "Хормозган": "Бендер-Аббас",
    "Систан и Белуджистан": "Бендер-Аббас", "Мазендеран": "Бендер-Аббас", "Гилян": "Бендер-Аббас",
    "Стамбул": "Стамбул", "Измир": "Измир", "Мерсин": "Мерсин", "Самсун": "Стамбул", "Трабзон": "Стамбул",
    "Ванкувер": "Ванкувер", "Монреаль": "Монреаль", "Галифакс": "Галифакс",
    "Квебек": "Монреаль", "Новая Шотландия": "Галифакс", "Нью-Брансуик": "Галифакс",
    "Гданьск": "Гданьск", "Щецин": "Щецин", "Поморское воеводство": "Гданьск",
    "Западно-Поморское воеводство": "Щецин", "Сан-Паулу": "Сантос", "Рио-де-Жанейро": "Рио-де-Жанейро",
    "Эспириту-Санту": "Сантос", "Санта-Катарина": "Сантос", "Риу-Гранди-ду-Сул": "Сантос",
    "Стокгольм": "Стокгольм", "Гётеборг": "Гётеборг", "Мальмё": "Гётеборг",
    "Хельсинки": "Хельсинки", "Турку": "Турку", "Оулу": "Хельсинки",
    "Осло": "Осло", "Берген": "Берген", "Вестланн": "Берген", "Рогаланн": "Берген",
    "Александрия": "Александрия", "Порт-Саид": "Порт-Саид", "Суэц": "Суэц",
    "Насон": "Нампхо", "Вонсан": "Вонсан", "Хамгён-Намдо": "Вонсан", "Хамгён-Пукто": "Вонсан",
    "Латакия": "Латакия", "Тартус": "Тартус",
}


# ==================== ТИПЫ ГРУЗОВ ====================

CARGO_TYPES = {
    "oil": {"name": "Нефть", "value_mult": 1.5, "perishable": False, "hazardous": True},
    "gas": {"name": "Газ", "value_mult": 1.4, "perishable": False, "hazardous": True},
    "coal": {"name": "Уголь", "value_mult": 0.8, "perishable": False, "hazardous": False},
    "steel": {"name": "Сталь", "value_mult": 1.0, "perishable": False, "hazardous": False},
    "aluminum": {"name": "Алюминий", "value_mult": 1.1, "perishable": False, "hazardous": False},
    "uranium": {"name": "Уран", "value_mult": 3.0, "perishable": False, "hazardous": True},
    "rare_metals": {"name": "Редкие металлы", "value_mult": 2.0, "perishable": False, "hazardous": False},
    "cars": {"name": "Автомобили", "value_mult": 1.8, "perishable": False, "hazardous": False},
    "trucks": {"name": "Грузовики", "value_mult": 2.0, "perishable": False, "hazardous": False},
    "buses": {"name": "Автобусы", "value_mult": 2.2, "perishable": False, "hazardous": False},
    "agricultural_machinery": {"name": "Сельхозтехника", "value_mult": 2.0, "perishable": False, "hazardous": False},
    "construction_machinery": {"name": "Строительная техника", "value_mult": 2.2, "perishable": False, "hazardous": False},
    "industrial_equipment": {"name": "Промышленное оборудование", "value_mult": 2.2, "perishable": False, "hazardous": False},
    "machine_tools": {"name": "Станки", "value_mult": 2.0, "perishable": False, "hazardous": False},
    "industrial_robots": {"name": "Промышленные роботы", "value_mult": 2.8, "perishable": False, "hazardous": False},
    "energy_equipment": {"name": "Энергетическое оборудование", "value_mult": 2.5, "perishable": False, "hazardous": False},
    "electrical_equipment": {"name": "Электрооборудование", "value_mult": 1.8, "perishable": False, "hazardous": False},
    "telecom_equipment": {"name": "Телекоммуникационное оборудование", "value_mult": 2.2, "perishable": False, "hazardous": False},
    "tech_equipment": {"name": "Техническое оборудование", "value_mult": 2.0, "perishable": False, "hazardous": False},
    "aerospace_equipment": {"name": "Авиационное оборудование", "value_mult": 3.0, "perishable": False, "hazardous": False},
    "auto_parts": {"name": "Автозапчасти", "value_mult": 1.5, "perishable": False, "hazardous": False},
    "consumer_electronics": {"name": "Бытовая электроника", "value_mult": 2.5, "perishable": False, "hazardous": False},
    "pharmaceuticals": {"name": "Лекарства", "value_mult": 3.0, "perishable": True, "hazardous": False},
    "food_products": {"name": "Продукты питания", "value_mult": 1.2, "perishable": True, "hazardous": False},
    "clothing": {"name": "Одежда", "value_mult": 1.0, "perishable": False, "hazardous": False},
    "furniture": {"name": "Мебель", "value_mult": 1.3, "perishable": False, "hazardous": False},
    "household_goods": {"name": "Товары для дома", "value_mult": 1.1, "perishable": False, "hazardous": False},
    "chemicals": {"name": "Химикаты", "value_mult": 1.6, "perishable": False, "hazardous": True},
    "fertilizers": {"name": "Удобрения", "value_mult": 0.9, "perishable": False, "hazardous": False},
    "medical_supplies": {"name": "Медицинские принадлежности", "value_mult": 2.0, "perishable": False, "hazardous": False},
    "medical_equipment": {"name": "Медицинское оборудование", "value_mult": 2.5, "perishable": False, "hazardous": False},
    "sanitary_products": {"name": "Санитарные изделия", "value_mult": 1.2, "perishable": False, "hazardous": False},
    "drones": {"name": "Беспилотники", "value_mult": 2.8, "perishable": False, "hazardous": False},
    "fpv_drones": {"name": "FPV дроны", "value_mult": 2.5, "perishable": False, "hazardous": False},
}


# ==================== ТИПЫ КОРАБЛЕЙ ====================

SHIP_TYPES = {
    "container": {"name": "Контейнеровоз", "capacity": 10000, "speed": 20, "fuel_consumption": 50, "cost": 50000000, "maintenance": 1000000, "crew": 25},
    "tanker": {"name": "Танкер", "capacity": 80000, "speed": 15, "fuel_consumption": 40, "cost": 80000000, "maintenance": 1500000, "crew": 30, "specialization": ["oil", "gas", "chemicals"]},
    "bulk": {"name": "Балкер", "capacity": 50000, "speed": 18, "fuel_consumption": 35, "cost": 40000000, "maintenance": 800000, "crew": 20, "specialization": ["coal", "steel", "aluminum", "fertilizers"]},
    "ro_ro": {"name": "Ролкер", "capacity": 30000, "speed": 22, "fuel_consumption": 45, "cost": 60000000, "maintenance": 1200000, "crew": 22, "specialization": ["cars", "trucks", "industrial_equipment", "agricultural_machinery", "construction_machinery"]},
    "reefer": {"name": "Рефрижератор", "capacity": 8000, "speed": 19, "fuel_consumption": 60, "cost": 45000000, "maintenance": 1100000, "crew": 18, "specialization": ["food_products", "pharmaceuticals"]}
}


# ==================== МОРСКИЕ МАРШРУТЫ ====================

SHIPPING_LANES = [
    {"from_port": "Нью-Йорк", "to_port": "Гамбург", "distance": 5800},
    {"from_port": "Нью-Йорк", "to_port": "Лондон", "distance": 5500},
    {"from_port": "Нью-Йорк", "to_port": "Марсель", "distance": 6100},
    {"from_port": "Шанхай", "to_port": "Лос-Анджелес", "distance": 9500},
    {"from_port": "Шанхай", "to_port": "Ванкувер", "distance": 8400},
    {"from_port": "Токио", "to_port": "Лос-Анджелес", "distance": 8200},
    {"from_port": "Шанхай", "to_port": "Гамбург", "distance": 10500},
    {"from_port": "Гамбург", "to_port": "Марсель", "distance": 1700},
    {"from_port": "Марсель", "to_port": "Александрия", "distance": 1800},
    {"from_port": "Марсель", "to_port": "Стамбул", "distance": 1500},
    {"from_port": "Одесса", "to_port": "Стамбул", "distance": 400},
    {"from_port": "Новороссийск", "to_port": "Стамбул", "distance": 500},
    {"from_port": "Бендер-Аббас", "to_port": "Шанхай", "distance": 6500},
    {"from_port": "Дубай", "to_port": "Марсель", "distance": 5200},
    {"from_port": "Санкт-Петербург", "to_port": "Гамбург", "distance": 2100},
    {"from_port": "Гданьск", "to_port": "Гамбург", "distance": 900},
    {"from_port": "Хельсинки", "to_port": "Гамбург", "distance": 1100},
    {"from_port": "Шанхай", "to_port": "Токио", "distance": 1700},
    {"from_port": "Шанхай", "to_port": "Владивосток", "distance": 1600},
    {"from_port": "Владивосток", "to_port": "Токио", "distance": 800},
    {"from_port": "Нью-Йорк", "to_port": "Хьюстон", "distance": 2300},
    {"from_port": "Лос-Анджелес", "to_port": "Нью-Йорк", "distance": 4500},
    {"from_port": "Сантос", "to_port": "Гамбург", "distance": 8500},
    {"from_port": "Сантос", "to_port": "Хьюстон", "distance": 7500},
    {"from_port": "Сантос", "to_port": "Шанхай", "distance": 11000},
    {"from_port": "Мурманск", "to_port": "Гамбург", "distance": 2800},
    {"from_port": "Владивосток", "to_port": "Шанхай", "distance": 1600},
    {"from_port": "Стамбул", "to_port": "Марсель", "distance": 1500},
    {"from_port": "Хайфа", "to_port": "Марсель", "distance": 2200},
    {"from_port": "Бендер-Аббас", "to_port": "Мумбаи", "distance": 1800},
]


# ==================== НАЧАЛЬНЫЙ ФЛОТ ====================

INITIAL_FLEET = {
    "civ_us_001": [{"type": "ro_ro", "count": 5}, {"type": "container", "count": 3}],
    "civ_us_001b": [{"type": "ro_ro", "count": 5}, {"type": "container", "count": 3}],
    "civ_us_002": [{"type": "bulk", "count": 4}, {"type": "ro_ro", "count": 2}],
    "civ_us_003": [{"type": "ro_ro", "count": 2}, {"type": "container", "count": 2}],
    "civ_us_004": [{"type": "container", "count": 3}],
    "civ_us_004b": [{"type": "container", "count": 3}],
    "civ_us_004c": [{"type": "container", "count": 4}, {"type": "ro_ro", "count": 2}],
    "civ_us_004e": [{"type": "container", "count": 10}, {"type": "ro_ro", "count": 5}],
    "civ_us_005": [{"type": "reefer", "count": 3}, {"type": "container", "count": 2}],
    "civ_us_005b": [{"type": "reefer", "count": 3}],
    "civ_us_006": [{"type": "container", "count": 2}],
    "civ_us_007": [{"type": "container", "count": 1}],
    "civ_us_008": [{"type": "container", "count": 8}, {"type": "reefer", "count": 4}],
    "civ_us_008b": [{"type": "container", "count": 5}, {"type": "reefer", "count": 3}],
    "civ_us_009": [{"type": "reefer", "count": 2}],
    "civ_us_010": [{"type": "ro_ro", "count": 3}],
    "civ_us_011": [{"type": "reefer", "count": 3}, {"type": "container", "count": 2}],
    "civ_us_011b": [{"type": "reefer", "count": 3}, {"type": "container", "count": 2}],
    "civ_us_012": [{"type": "ro_ro", "count": 2}, {"type": "container", "count": 2}],
    "civ_us_013": [{"type": "container", "count": 1}],
    "civ_us_014": [{"type": "container", "count": 6}],
    "civ_us_014b": [{"type": "container", "count": 5}],
    "civ_ru_001": [{"type": "ro_ro", "count": 2}],
    "civ_ru_001b": [{"type": "ro_ro", "count": 2}],
    "civ_ru_002": [{"type": "ro_ro", "count": 3}],
    "civ_ru_003": [{"type": "container", "count": 1}],
    "civ_ru_004": [{"type": "container", "count": 1}],
    "civ_ru_005": [{"type": "container", "count": 1}],
    "civ_ru_006": [{"type": "reefer", "count": 3}, {"type": "container", "count": 2}],
    "civ_ru_006c": [{"type": "container", "count": 3}],
    "civ_ru_006d": [{"type": "container", "count": 2}],
    "civ_ru_007": [{"type": "tanker", "count": 8}, {"type": "container", "count": 2}],
    "civ_ru_007b": [{"type": "tanker", "count": 7}, {"type": "container", "count": 2}],
    "civ_ru_007c": [{"type": "tanker", "count": 6}, {"type": "container", "count": 2}],
    "civ_ru_007d": [{"type": "bulk", "count": 2}],
    "civ_ru_008": [{"type": "ro_ro", "count": 2}],
    "civ_ru_011": [{"type": "bulk", "count": 3}],
    "civ_ru_013": [{"type": "bulk", "count": 4}],
    "civ_ru_014": [{"type": "container", "count": 2}],
    "civ_cn_001": [{"type": "ro_ro", "count": 4}, {"type": "container", "count": 3}],
    "civ_cn_001b": [{"type": "ro_ro", "count": 5}, {"type": "container", "count": 3}],
    "civ_cn_002": [{"type": "container", "count": 5}, {"type": "ro_ro", "count": 2}],
    "civ_cn_007": [{"type": "container", "count": 4}],
    "civ_cn_002b": [{"type": "container", "count": 3}],
    "civ_cn_002d": [{"type": "container", "count": 8}, {"type": "ro_ro", "count": 3}],
    "civ_cn_008": [{"type": "container", "count": 2}],
    "civ_cn_010": [{"type": "container", "count": 6}],
    "civ_cn_011": [{"type": "tanker", "count": 10}, {"type": "container", "count": 3}],
    "civ_de_001": [{"type": "ro_ro", "count": 6}, {"type": "container", "count": 3}],
    "civ_de_002": [{"type": "ro_ro", "count": 4}, {"type": "container", "count": 2}],
    "civ_de_003": [{"type": "ro_ro", "count": 5}, {"type": "container", "count": 3}],
    "civ_de_004": [{"type": "ro_ro", "count": 2}, {"type": "container", "count": 3}],
    "civ_de_005": [{"type": "tanker", "count": 3}, {"type": "bulk", "count": 3}],
    "civ_de_007": [{"type": "reefer", "count": 2}, {"type": "container", "count": 2}],
    "civ_de_014": [{"type": "container", "count": 8}],
    "civ_de_015": [{"type": "container", "count": 3}],
    "civ_uk_001": [{"type": "tanker", "count": 6}, {"type": "container", "count": 2}],
    "civ_uk_001b": [{"type": "tanker", "count": 8}, {"type": "container", "count": 3}],
    "civ_uk_005": [{"type": "reefer", "count": 3}, {"type": "container", "count": 4}],
    "civ_fr_001": [{"type": "tanker", "count": 5}, {"type": "container", "count": 2}],
    "civ_fr_003": [{"type": "reefer", "count": 2}],
    "civ_fr_005": [{"type": "ro_ro", "count": 3}],
    "civ_fr_006": [{"type": "ro_ro", "count": 2}],
    "civ_fr_007": [{"type": "reefer", "count": 4}, {"type": "container", "count": 4}],
    "civ_jp_001": [{"type": "ro_ro", "count": 8}, {"type": "container", "count": 3}],
    "civ_jp_001b": [{"type": "ro_ro", "count": 6}, {"type": "container", "count": 2}],
    "civ_jp_001c": [{"type": "ro_ro", "count": 6}, {"type": "container", "count": 2}],
    "civ_jp_002": [{"type": "container", "count": 3}],
    "civ_jp_003": [{"type": "container", "count": 4}],
    "civ_br_001": [{"type": "ro_ro", "count": 2}],
    "civ_br_002": [{"type": "bulk", "count": 8}, {"type": "container", "count": 2}],
    "civ_br_003": [{"type": "tanker", "count": 6}, {"type": "container", "count": 2}],
    "civ_br_004": [{"type": "reefer", "count": 4}],
    "civ_ch_003": [{"type": "reefer", "count": 2}],
    "civ_ch_003b": [{"type": "reefer", "count": 2}],
    "civ_ch_004": [{"type": "reefer", "count": 5}, {"type": "container", "count": 4}],
    "civ_ch_006": [{"type": "container", "count": 10}, {"type": "ro_ro", "count": 3}],
    "civ_kr_001": [{"type": "container", "count": 8}, {"type": "ro_ro", "count": 2}],
    "civ_kr_002": [{"type": "ro_ro", "count": 5}, {"type": "container", "count": 3}],
    "civ_kr_003": [{"type": "container", "count": 4}],
    "civ_il_001": [{"type": "bulk", "count": 3}, {"type": "container", "count": 2}],
    "civ_il_002": [{"type": "reefer", "count": 4}, {"type": "container", "count": 2}],
    "civ_il_003": [{"type": "tanker", "count": 2}, {"type": "bulk", "count": 2}],
    "civ_il_004": [{"type": "ro_ro", "count": 2}, {"type": "container", "count": 3}],
    "civ_ir_001": [{"type": "tanker", "count": 10}, {"type": "container", "count": 2}],
    "civ_ir_002": [{"type": "ro_ro", "count": 3}, {"type": "container", "count": 2}],
    "civ_ir_003": [{"type": "tanker", "count": 5}, {"type": "bulk", "count": 3}],
    "civ_ir_004": [{"type": "bulk", "count": 4}],
    "civ_tr_001": [{"type": "ro_ro", "count": 3}, {"type": "container", "count": 2}],
    "civ_tr_002": [{"type": "tanker", "count": 4}, {"type": "container", "count": 1}],
    "civ_eg_001": [{"type": "container", "count": 2}, {"type": "bulk", "count": 2}],
    "civ_eg_002": [{"type": "tanker", "count": 4}],
    "civ_sa_001": [{"type": "tanker", "count": 12}, {"type": "container", "count": 2}],
    "civ_ae_001": [{"type": "tanker", "count": 8}, {"type": "container", "count": 3}],
    "civ_qa_001": [{"type": "tanker", "count": 6}, {"type": "container", "count": 2}],
    "civ_no_001": [{"type": "tanker", "count": 4}, {"type": "container", "count": 2}],
    "civ_ca_001": [{"type": "tanker", "count": 3}, {"type": "bulk", "count": 2}],
    "civ_pl_001": [{"type": "tanker", "count": 2}, {"type": "container", "count": 3}],
    "civ_se_001": [{"type": "ro_ro", "count": 4}, {"type": "container", "count": 2}],
    "civ_fi_001": [{"type": "tanker", "count": 2}, {"type": "container", "count": 2}],
    "civ_ua_001": [{"type": "bulk", "count": 3}, {"type": "container", "count": 1}],
    "civ_kp_001": [{"type": "bulk", "count": 2}, {"type": "container", "count": 1}],
    "civ_sy_001": [{"type": "tanker", "count": 1}, {"type": "bulk", "count": 1}],
}

CORP_COUNTRIES = {
    "civ_us_001": "США", "civ_us_001b": "США", "civ_us_002": "США",
    "civ_us_003": "США", "civ_us_004": "США", "civ_us_004b": "США",
    "civ_us_004c": "США", "civ_us_004e": "США", "civ_us_005": "США",
    "civ_us_005b": "США", "civ_us_006": "США", "civ_us_007": "США",
    "civ_us_008": "США", "civ_us_008b": "США", "civ_us_009": "США",
    "civ_us_010": "США", "civ_us_011": "США", "civ_us_011b": "США",
    "civ_us_012": "США", "civ_us_013": "США", "civ_us_014": "США",
    "civ_us_014b": "США",
    "civ_ru_001": "Россия", "civ_ru_001b": "Россия", "civ_ru_002": "Россия",
    "civ_ru_003": "Россия", "civ_ru_004": "Россия", "civ_ru_005": "Россия",
    "civ_ru_006": "Россия", "civ_ru_006c": "Россия", "civ_ru_006d": "Россия",
    "civ_ru_007": "Россия", "civ_ru_007b": "Россия", "civ_ru_007c": "Россия",
    "civ_ru_007d": "Россия", "civ_ru_008": "Россия", "civ_ru_011": "Россия",
    "civ_ru_013": "Россия", "civ_ru_014": "Россия",
    "civ_cn_001": "Китай", "civ_cn_001b": "Китай", "civ_cn_002": "Китай",
    "civ_cn_007": "Китай", "civ_cn_002b": "Китай", "civ_cn_002d": "Китай",
    "civ_cn_008": "Китай", "civ_cn_010": "Китай", "civ_cn_011": "Китай",
    "civ_de_001": "Германия", "civ_de_002": "Германия", "civ_de_003": "Германия",
    "civ_de_004": "Германия", "civ_de_005": "Германия", "civ_de_007": "Германия",
    "civ_de_014": "Германия", "civ_de_015": "Германия",
    "civ_uk_001": "Великобритания", "civ_uk_001b": "Великобритания", "civ_uk_005": "Великобритания",
    "civ_fr_001": "Франция", "civ_fr_003": "Франция", "civ_fr_005": "Франция",
    "civ_fr_006": "Франция", "civ_fr_007": "Франция",
    "civ_jp_001": "Япония", "civ_jp_001b": "Япония", "civ_jp_001c": "Япония",
    "civ_jp_002": "Япония", "civ_jp_003": "Япония",
    "civ_br_001": "Бразилия", "civ_br_002": "Бразилия", "civ_br_003": "Бразилия",
    "civ_br_004": "Бразилия",
    "civ_ch_003": "Швейцария", "civ_ch_003b": "Швейцария", "civ_ch_004": "Швейцария",
    "civ_ch_006": "Швейцария",
    "civ_kr_001": "Южная Корея", "civ_kr_002": "Южная Корея", "civ_kr_003": "Южная Корея",
    "civ_il_001": "Израиль", "civ_il_002": "Израиль", "civ_il_003": "Израиль", "civ_il_004": "Израиль",
    "civ_ir_001": "Иран", "civ_ir_002": "Иран", "civ_ir_003": "Иран", "civ_ir_004": "Иран",
    "civ_tr_001": "Турция", "civ_tr_002": "Турция",
    "civ_eg_001": "Египет", "civ_eg_002": "Египет",
    "civ_sa_001": "Саудовская Аравия",
    "civ_ae_001": "ОАЭ",
    "civ_qa_001": "Катар",
    "civ_no_001": "Норвегия",
    "civ_ca_001": "Канада",
    "civ_pl_001": "Польша",
    "civ_se_001": "Швеция",
    "civ_fi_001": "Финляндия",
    "civ_ua_001": "Украина",
    "civ_kp_001": "КНДР",
    "civ_sy_001": "Сирия",
}


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ====================

def load_maritime_data():
    try:
        with open(MARITIME_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"ships": [], "last_update": datetime.now().isoformat()}

def save_maritime_data(data):
    with open(MARITIME_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_ship_logs():
    try:
        with open(SHIP_LOGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"logs": []}

def save_ship_logs(logs):
    with open(SHIP_LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def load_priority_regions():
    try:
        with open(PRIORITY_REGIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "export_priorities" not in data:
                data["export_priorities"] = {}
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"export_priorities": {}}

def save_priority_regions(data):
    with open(PRIORITY_REGIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ==================== ФУНКЦИИ ДЛЯ ПРИОРИТЕТОВ ЭКСПОРТА ====================

def get_available_export_countries(my_country: str) -> List[Dict]:
    states = load_states()
    existing_countries = []
    
    for data in states["players"].values():
        country = data["state"]["statename"]
        if country != my_country and is_trade_allowed(my_country, country):
            country_regions = get_regions_by_country(country)
            operational_regions = [r for r in country_regions if is_region_operational(r)[0]]
            
            if operational_regions:
                existing_countries.append({
                    "name": country,
                    "region_count": len(operational_regions),
                    "main_region": operational_regions[0] if operational_regions else None
                })
    
    existing_countries.sort(key=lambda x: x["name"])
    return existing_countries

def get_country_export_priorities(country_name: str) -> Dict[str, List[str]]:
    priority_data = load_priority_regions()
    return priority_data["export_priorities"].get(country_name, {})

def set_export_priority(country_name: str, target_country: str, categories: List[str]) -> bool:
    if not is_trade_allowed(country_name, target_country):
        return False
    
    target_regions = get_regions_by_country(target_country)
    has_operational_region = any(is_region_operational(r)[0] for r in target_regions)
    
    if not has_operational_region:
        return False
    
    priority_data = load_priority_regions()
    
    if "export_priorities" not in priority_data:
        priority_data["export_priorities"] = {}
    
    if country_name not in priority_data["export_priorities"]:
        priority_data["export_priorities"][country_name] = {}
    
    if categories:
        priority_data["export_priorities"][country_name][target_country] = categories
    else:
        if target_country in priority_data["export_priorities"][country_name]:
            del priority_data["export_priorities"][country_name][target_country]
        if not priority_data["export_priorities"][country_name]:
            del priority_data["export_priorities"][country_name]
    
    save_priority_regions(priority_data)
    return True

def clear_export_priorities(country_name: str, target_country: str = None) -> bool:
    priority_data = load_priority_regions()
    
    if "export_priorities" not in priority_data:
        return True
    
    if country_name not in priority_data["export_priorities"]:
        return True
    
    if target_country:
        if target_country in priority_data["export_priorities"][country_name]:
            del priority_data["export_priorities"][country_name][target_country]
        if not priority_data["export_priorities"][country_name]:
            del priority_data["export_priorities"][country_name]
    else:
        del priority_data["export_priorities"][country_name]
    
    save_priority_regions(priority_data)
    return True

def get_priority_score(ship_cargo: Dict, exporter_country: str, importer_country: str) -> int:
    if not ship_cargo:
        return 0
    
    priorities = get_country_export_priorities(exporter_country)
    
    if importer_country not in priorities:
        return 0
    
    priority_categories = priorities[importer_country]
    score = 0
    
    for cargo_type in ship_cargo.keys():
        for category in priority_categories:
            if category in PRIORITY_CATEGORIES and cargo_type in PRIORITY_CATEGORIES[category]["resources"]:
                score += 10
    
    return score


# ==================== КООРДИНАТЫ РЕГИОНОВ ====================

REGION_COORDINATES = {
    "Нью-Йорк": {"lat": 40.71, "lon": -74.01},
    "Калифорния": {"lat": 36.78, "lon": -119.42},
    "Техас": {"lat": 31.97, "lon": -99.90},
    "Флорида": {"lat": 27.99, "lon": -81.76},
    "Вашингтон (штат)": {"lat": 47.75, "lon": -120.74},
    "Луизиана": {"lat": 30.98, "lon": -91.96},
    "Вирджиния": {"lat": 37.43, "lon": -78.66},
    "Массачусетс": {"lat": 42.41, "lon": -71.38},
    "Коннектикут": {"lat": 41.60, "lon": -72.68},
    "г. Санкт-Петербург": {"lat": 59.93, "lon": 30.36},
    "Ленинградская область": {"lat": 60.00, "lon": 32.00},
    "Краснодарский край": {"lat": 45.04, "lon": 38.98},
    "Приморский край": {"lat": 45.33, "lon": 134.67},
    "Мурманская область": {"lat": 68.97, "lon": 33.08},
    "Калининградская область": {"lat": 54.71, "lon": 20.51},
    "Архангельская область": {"lat": 64.54, "lon": 40.54},
    "Сахалинская область": {"lat": 50.00, "lon": 143.00},
    "Шанхай": {"lat": 31.23, "lon": 121.47},
    "Гуандун": {"lat": 23.13, "lon": 113.26},
    "Ляонин": {"lat": 41.80, "lon": 123.43},
    "Тяньцзинь": {"lat": 39.34, "lon": 117.36},
    "Гамбург": {"lat": 53.55, "lon": 9.99},
    "Бремен": {"lat": 53.08, "lon": 8.80},
    "Лондон": {"lat": 51.51, "lon": -0.13},
    "Ливерпуль": {"lat": 53.41, "lon": -2.99},
    "Саутгемптон": {"lat": 50.90, "lon": -1.40},
    "Марсель": {"lat": 43.30, "lon": 5.37},
    "Гавр": {"lat": 49.49, "lon": 0.10},
    "Токио": {"lat": 35.68, "lon": 139.76},
    "Иокогама": {"lat": 35.44, "lon": 139.64},
    "Осака": {"lat": 34.69, "lon": 135.50},
    "Тель-Авивский округ": {"lat": 32.09, "lon": 34.78},
    "Хайфский округ": {"lat": 32.79, "lon": 34.99},
    "Одеська область": {"lat": 46.48, "lon": 30.73},
    "Миколаївська область": {"lat": 46.97, "lon": 32.00},
    "Хузестан": {"lat": 31.32, "lon": 48.67},
    "Бушир": {"lat": 28.92, "lon": 50.83},
    "Хормозган": {"lat": 27.18, "lon": 56.26},
    "Стамбул": {"lat": 41.01, "lon": 28.98},
    "Измир": {"lat": 38.42, "lon": 27.13},
    "Мерсин": {"lat": 36.80, "lon": 34.63},
    "Ванкувер": {"lat": 49.28, "lon": -123.12},
    "Монреаль": {"lat": 45.50, "lon": -73.57},
    "Галифакс": {"lat": 44.65, "lon": -63.58},
    "Гданьск": {"lat": 54.35, "lon": 18.65},
    "Щецин": {"lat": 53.43, "lon": 14.55},
    "Сан-Паулу": {"lat": -23.55, "lon": -46.63},
    "Рио-де-Жанейро": {"lat": -22.91, "lon": -43.17},
    "Стокгольм": {"lat": 59.33, "lon": 18.06},
    "Гётеборг": {"lat": 57.71, "lon": 11.97},
    "Хельсинки": {"lat": 60.17, "lon": 24.94},
    "Турку": {"lat": 60.45, "lon": 22.27},
    "Осло": {"lat": 59.91, "lon": 10.75},
    "Берген": {"lat": 60.39, "lon": 5.32},
    "Александрия": {"lat": 31.20, "lon": 29.92},
    "Суэц": {"lat": 29.97, "lon": 32.53},
    "Порт-Саид": {"lat": 31.25, "lon": 32.28},
    "Нампхо": {"lat": 38.73, "lon": 125.39},
    "Вонсан": {"lat": 39.15, "lon": 127.44},
    "Латакия": {"lat": 35.52, "lon": 35.78},
    "Тартус": {"lat": 34.89, "lon": 35.89},
}


def calculate_region_distance(region1: str, region2: str) -> float:
    if region1 in REGION_COORDINATES and region2 in REGION_COORDINATES:
        p1 = REGION_COORDINATES[region1]
        p2 = REGION_COORDINATES[region2]
        
        lat1, lon1 = math.radians(p1["lat"]), math.radians(p1["lon"])
        lat2, lon2 = math.radians(p2["lat"]), math.radians(p2["lon"])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        distance = 6371 * c
        return distance
    
    for lane in SHIPPING_LANES:
        if (lane["from_port"] == region1 and lane["to_port"] == region2) or \
           (lane["from_port"] == region2 and lane["to_port"] == region1):
            return lane["distance"]
    
    return 9999


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def format_game_time(real_hours: float) -> str:
    if real_hours >= 24:
        days = real_hours / 24
        return f"{days:.1f} дн."
    elif real_hours >= 1:
        return f"{real_hours:.1f} ч."
    else:
        minutes = real_hours * 60
        return f"{minutes:.0f} мин."

def get_country_data(country_name: str) -> Optional[Dict]:
    states = load_states()
    for player_data in states["players"].values():
        if player_data.get("state", {}).get("statename") == country_name:
            return player_data
    return None

def generate_cargo_amount(product_type: str, ship_type: str) -> float:
    cargo_ranges = {
        "oil": (5, 40), "gas": (3, 30), "coal": (10, 60), "steel": (8, 50),
        "aluminum": (5, 30), "uranium": (1, 8), "rare_metals": (2, 15),
        "cars": (3, 20), "trucks": (2, 12), "buses": (1, 6),
        "agricultural_machinery": (2, 10), "construction_machinery": (1, 8),
        "industrial_equipment": (2, 15), "machine_tools": (2, 12),
        "industrial_robots": (1, 6), "energy_equipment": (1, 5),
        "electrical_equipment": (10, 60), "telecom_equipment": (5, 40),
        "tech_equipment": (5, 30), "aerospace_equipment": (1, 3),
        "auto_parts": (20, 150), "consumer_electronics": (10, 80),
        "pharmaceuticals": (5, 40), "food_products": (10, 80),
        "clothing": (20, 150), "furniture": (5, 30), "household_goods": (15, 100),
        "chemicals": (5, 40), "fertilizers": (10, 60), "medical_supplies": (5, 30),
        "medical_equipment": (1, 5), "sanitary_products": (15, 100),
        "drones": (2, 15), "fpv_drones": (5, 40)
    }
    
    if product_type in cargo_ranges:
        min_amount, max_amount = cargo_ranges[product_type]
    else:
        min_amount, max_amount = (3, 20)
    
    ship_multipliers = {
        "tanker": 1.2 if product_type in ["oil", "gas", "chemicals"] else 0.8,
        "bulk": 1.2 if product_type in ["coal", "steel", "aluminum", "fertilizers"] else 0.8,
        "ro_ro": 1.1 if product_type in ["cars", "trucks", "industrial_equipment"] else 0.7,
        "reefer": 1.1 if product_type in ["food_products", "pharmaceuticals"] else 0.6,
        "container": 1.0
    }
    
    multiplier = ship_multipliers.get(ship_type, 1.0)
    amount = random.uniform(min_amount, max_amount) * multiplier
    return round(amount)

def generate_cargo_for_country(country: str, ship_type: str) -> Tuple[str, float, float]:
    country_data = get_country_data(country)
    products = []
    
    if country_data:
        resources = country_data.get("resources", {})
        for resource, amount in resources.items():
            if amount > 0 and resource in CARGO_TYPES:
                weight = max(1, min(5, int(amount // 20)))
                products.extend([resource] * weight)
        
        civil_goods = country_data.get("civil_goods", {})
        goods_to_cargo = {
            "cars": "cars", "trucks": "trucks", "buses": "buses",
            "agricultural_machinery": "agricultural_machinery",
            "construction_machinery": "construction_machinery",
            "industrial_equipment": "industrial_equipment",
            "machine_tools": "machine_tools",
            "industrial_robots": "industrial_robots",
            "energy_equipment": "energy_equipment",
            "electrical_equipment": "electrical_equipment",
            "telecom_equipment": "telecom_equipment",
            "tech_equipment": "tech_equipment",
            "aerospace_equipment": "aerospace_equipment",
            "auto_parts": "auto_parts",
            "consumer_electronics": "consumer_electronics",
            "pharmaceuticals": "pharmaceuticals",
            "food_products": "food_products",
            "clothing": "clothing",
            "furniture": "furniture",
            "household_goods": "household_goods",
            "chemicals": "chemicals",
            "fertilizers": "fertilizers",
            "medical_supplies": "medical_supplies",
            "medical_equipment": "medical_equipment",
            "sanitary_products": "sanitary_products",
            "drones": "drones",
            "fpv_drones": "fpv_drones"
        }
        
        for good, amount in civil_goods.items():
            if amount > 0 and good in goods_to_cargo and goods_to_cargo[good] in CARGO_TYPES:
                cargo_type = goods_to_cargo[good]
                weight = max(1, min(5, int(amount // 50)))
                products.extend([cargo_type] * weight)
    
    if not products:
        standard_exports = {
            "США": ["cars", "industrial_equipment", "consumer_electronics", "pharmaceuticals", "food_products", "oil"],
            "Россия": ["oil", "gas", "coal", "steel", "aluminum", "fertilizers"],
            "Китай": ["consumer_electronics", "industrial_equipment", "cars", "clothing", "steel"],
            "Германия": ["cars", "industrial_equipment", "chemicals", "pharmaceuticals", "steel"],
            "Великобритания": ["pharmaceuticals", "chemicals", "oil", "gas"],
            "Франция": ["pharmaceuticals", "cars", "food_products"],
            "Япония": ["cars", "consumer_electronics", "industrial_equipment"],
            "Израиль": ["pharmaceuticals", "consumer_electronics", "drones"],
            "Украина": ["food_products", "steel", "oil"],
            "Иран": ["oil", "gas", "chemicals"],
            "Турция": ["cars", "clothing", "food_products", "steel"],
            "Бразилия": ["food_products", "oil", "minerals"],
            "Канада": ["oil", "gas", "cars"],
            "Норвегия": ["oil", "gas"],
            "Швеция": ["cars", "machinery", "steel"],
            "Финляндия": ["machinery", "electronics"],
            "Польша": ["furniture", "food_products"],
            "Египет": ["oil", "gas", "food_products"],
            "КНДР": ["minerals", "food_products"],
            "Сирия": ["oil", "food_products"],
            "Швейцария": ["pharmaceuticals", "machinery", "watches"]
        }
        products = standard_exports.get(country, ["oil", "steel", "cars"])
    
    ship_specialization = SHIP_TYPES[ship_type].get("specialization", [])
    if ship_specialization:
        compatible_products = [p for p in products if p in ship_specialization]
        if compatible_products:
            products = compatible_products
    
    products = [p for p in products if p in CARGO_TYPES]
    
    if not products:
        products = ["oil", "steel", "cars"]
    
    product = random.choice(products)
    amount = generate_cargo_amount(product, ship_type)
    
    if product in RESOURCE_PRICES:
        base_price = RESOURCE_PRICES[product]
    else:
        civil_prices = {
            "cars": 25000, "trucks": 50000, "buses": 70000,
            "agricultural_machinery": 30000, "construction_machinery": 40000,
            "industrial_equipment": 30000, "machine_tools": 25000,
            "industrial_robots": 80000, "energy_equipment": 35000,
            "electrical_equipment": 2000, "telecom_equipment": 3000,
            "tech_equipment": 2500, "aerospace_equipment": 100000,
            "auto_parts": 200, "consumer_electronics": 500,
            "pharmaceuticals": 2000, "food_products": 100,
            "clothing": 50, "furniture": 500, "household_goods": 100,
            "chemicals": 800, "fertilizers": 300, "medical_supplies": 150,
            "medical_equipment": 5000, "sanitary_products": 50,
            "drones": 5000, "fpv_drones": 2000
        }
        base_price = civil_prices.get(product, 1000)
    
    return product, amount, base_price


# ==================== ФУНКЦИИ ДЛЯ ОБНОВЛЕНИЯ ПРИ ПЕРЕДАЧЕ РЕГИОНОВ ====================

def update_ships_on_region_transfer(region_name: str, old_country: str, new_country: str) -> Dict:
    data = load_maritime_data()
    
    updated_ships = []
    affected_ships = []
    
    for ship_data in data.get("ships", []):
        ship = CargoShip.from_dict(ship_data)
        
        if ship.current_region == region_name:
            ship.current_country = new_country
            affected_ships.append({
                "id": ship.id,
                "name": ship.name,
                "status": ship.status,
                "old_country": old_country,
                "new_country": new_country
            })
            updated_ships.append(ship)
        
        if ship.destination_region == region_name:
            ship.destination_country = new_country
            affected_ships.append({
                "id": ship.id,
                "name": ship.name,
                "status": "en_route",
                "destination": True,
                "old_country": old_country,
                "new_country": new_country
            })
            updated_ships.append(ship)
    
    for i, ship_data in enumerate(data.get("ships", [])):
        for updated in updated_ships:
            if ship_data["id"] == updated.id:
                data["ships"][i] = updated.to_dict()
                break
    
    save_maritime_data(data)
    
    return {
        "region": region_name,
        "old_country": old_country,
        "new_country": new_country,
        "ships_affected": len(affected_ships),
        "affected_ships": affected_ships
    }

def update_priorities_on_region_transfer(region_name: str, old_country: str, new_country: str) -> Dict:
    priority_data = load_priority_regions()
    changes = {"removed": [], "added": [], "updated": []}
    
    for exporter, targets in priority_data["export_priorities"].items():
        if old_country in targets:
            old_categories = targets[old_country]
            changes["removed"].append({
                "exporter": exporter,
                "target": old_country,
                "categories": old_categories
            })
            targets[new_country] = old_categories
            changes["added"].append({
                "exporter": exporter,
                "target": new_country,
                "categories": old_categories
            })
            del targets[old_country]
    
    if old_country in priority_data["export_priorities"]:
        old_priorities = priority_data["export_priorities"][old_country]
        changes["removed"].append({
            "exporter": old_country,
            "priorities": old_priorities
        })
        priority_data["export_priorities"][new_country] = old_priorities
        changes["added"].append({
            "exporter": new_country,
            "priorities": old_priorities
        })
        del priority_data["export_priorities"][old_country]
    
    save_priority_regions(priority_data)
    
    return changes


# ==================== КЛАСС КОРАБЛЯ ====================

class CargoShip:
    def __init__(self, ship_id: str, corporation_id: str, ship_type: str = "container"):
        self.id = ship_id
        self.corporation_id = corporation_id
        self.type = ship_type
        self.name = f"{SHIP_TYPES[ship_type]['name']} {ship_id[-4:]}"
        self.status = "idle"
        self.current_region = None
        self.current_country = None
        self.destination_region = None
        self.destination_country = None
        self.route = []
        self.cargo = {}
        self.cargo_value = 0
        self.departure_time = None
        self.arrival_time = None
        self.progress = 0
        self.last_update = datetime.now().isoformat()
        self.trips_completed = 0
        self.total_cargo_delivered = 0
        self.total_profit = 0
        self.damage = 0
    
    def to_dict(self):
        return {
            "id": self.id,
            "corporation_id": self.corporation_id,
            "type": self.type,
            "name": self.name,
            "status": self.status,
            "current_region": self.current_region,
            "current_country": self.current_country,
            "destination_region": self.destination_region,
            "destination_country": self.destination_country,
            "route": self.route,
            "cargo": self.cargo,
            "cargo_value": self.cargo_value,
            "departure_time": self.departure_time,
            "arrival_time": self.arrival_time,
            "progress": self.progress,
            "last_update": self.last_update,
            "trips_completed": self.trips_completed,
            "total_cargo_delivered": self.total_cargo_delivered,
            "total_profit": self.total_profit,
            "damage": self.damage
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        ship = cls(data["id"], data["corporation_id"], data["type"])
        ship.name = data["name"]
        ship.status = data["status"]
        ship.current_region = data.get("current_region", data.get("current_port"))
        ship.current_country = data.get("current_country")
        ship.destination_region = data.get("destination_region", data.get("destination_port"))
        ship.destination_country = data.get("destination_country")
        ship.route = data["route"]
        ship.cargo = data["cargo"]
        ship.cargo_value = data["cargo_value"]
        ship.departure_time = data["departure_time"]
        ship.arrival_time = data["arrival_time"]
        ship.progress = data["progress"]
        ship.last_update = data["last_update"]
        ship.trips_completed = data["trips_completed"]
        ship.total_cargo_delivered = data["total_cargo_delivered"]
        ship.total_profit = data["total_profit"]
        ship.damage = data["damage"]
        return ship
    
    def load_cargo(self, product_type: str, amount: float, value_per_unit: float):
        ship_type_data = SHIP_TYPES[self.type]
        
        if "specialization" in ship_type_data:
            if product_type not in ship_type_data["specialization"]:
                return False, f"Корабль типа {ship_type_data['name']} не предназначен для перевозки {CARGO_TYPES[product_type]['name']}"
        
        current_cargo = sum(self.cargo.values())
        if current_cargo + amount > ship_type_data["capacity"]:
            return False, f"Недостаточно места на корабле"
        
        self.cargo[product_type] = self.cargo.get(product_type, 0) + amount
        self.cargo_value += amount * value_per_unit
        return True, f"Загружено {amount:.0f} {CARGO_TYPES[product_type]['name']}"
    
    def set_destination(self, destination_region: str):
        if not self.current_region:
            return False, "Корабль не в регионе"
        
        if destination_region == self.current_region:
            return False, "Корабль уже в этом регионе"
        
        destination_country = get_country_from_region(destination_region)
        if not destination_country:
            return False, f"Регион {destination_region} не найден или не имеет выхода к морю"
        
        try:
            from navy import is_ship_blocked
            sea_zone = get_sea_zone_from_region(destination_region)
            if sea_zone:
                blocked, blockader = is_ship_blocked(self.current_country, sea_zone)
                if blocked:
                    return False, f"Маршрут заблокирован! Страна {blockader} установила блокаду в этом регионе."
        except ImportError:
            pass
        
        operational, shipyards = is_region_operational(destination_region)
        if not operational:
            return False, f"Регион {destination_region} не может принимать корабли (нет верфей)"
        
        if not is_trade_allowed(self.current_country, destination_country):
            return False, f"Торговля между {self.current_country} и {destination_country} запрещена"
        
        distance = calculate_region_distance(self.current_region, destination_region)
        if distance >= 9999:
            return False, "Маршрут не найден"
        
        speed = SHIP_TYPES[self.type]["speed"]
        travel_hours = distance / speed
        
        if travel_hours > 12:
            travel_hours = 12
        
        self.destination_region = destination_region
        self.destination_country = destination_country
        self.departure_time = datetime.now().isoformat()
        self.arrival_time = (datetime.now() + timedelta(hours=travel_hours)).isoformat()
        self.status = "sailing"
        self.progress = 0
        
        return True, f"Курс проложен до {destination_region} ({destination_country}), время в пути: {format_game_time(travel_hours)}"
    
    def update_progress(self):
        if self.status != "sailing" or not self.arrival_time:
            return False
        
        arrival = datetime.fromisoformat(self.arrival_time)
        departure = datetime.fromisoformat(self.departure_time)
        total = (arrival - departure).total_seconds()
        elapsed = (datetime.now() - departure).total_seconds()
        
        if elapsed >= total:
            self.status = "unloading"
            self.current_region = self.destination_region
            self.current_country = self.destination_country
            self.destination_region = None
            self.destination_country = None
            self.progress = 100
            return True
        else:
            self.progress = (elapsed / total) * 100
            return False
    
    def get_status_text(self) -> str:
        if self.status == "idle":
            return f"На стоянке ({self.current_region})"
        elif self.status == "loading":
            return "Загрузка"
        elif self.status == "sailing":
            remaining = datetime.fromisoformat(self.arrival_time) - datetime.now()
            remaining_hours = remaining.total_seconds() / 3600
            return f"В пути в {self.destination_region} ({self.progress:.1f}%, осталось {format_game_time(remaining_hours)})"
        elif self.status == "unloading":
            return f"Разгрузка ({self.current_region})"
        elif self.status == "returning":
            return "Возвращение"
        return "Неизвестно"
    
    def get_cargo_text(self) -> str:
        if not self.cargo:
            return "Пустой"
        items = []
        for p, v in self.cargo.items():
            cargo_name = CARGO_TYPES.get(p, {}).get("name", p)
            items.append(f"{cargo_name}: {v:.0f}")
        return ", ".join(items)


# ==================== ФУНКЦИИ ДЛЯ КОРПОРАЦИЙ ====================

def get_ships_by_country(country: str) -> List[CargoShip]:
    data = load_maritime_data()
    ships = []
    
    for ship_data in data.get("ships", []):
        ship = CargoShip.from_dict(ship_data)
        if ship.current_country == country:
            ships.append(ship)
    
    return ships

def get_ships_by_sea_region(sea_region: SeaRegion) -> Dict[str, List[CargoShip]]:
    data = load_maritime_data()
    ships_by_country = {}
    
    ports_in_region = [port for port, port_data in PORTS.items() if port_data["sea_region"] == sea_region]
    
    for ship_data in data.get("ships", []):
        ship = CargoShip.from_dict(ship_data)
        
        in_region = False
        
        if ship.current_region:
            if ship.current_region in ports_in_region:
                in_region = True
            elif ship.current_region in REGION_TO_PORT:
                mapped_port = REGION_TO_PORT[ship.current_region]
                if mapped_port in ports_in_region:
                    in_region = True
        
        if not in_region and ship.destination_region:
            if ship.destination_region in ports_in_region:
                in_region = True
            elif ship.destination_region in REGION_TO_PORT:
                mapped_port = REGION_TO_PORT[ship.destination_region]
                if mapped_port in ports_in_region:
                    in_region = True
        
        if in_region and ship.current_country:
            if ship.current_country not in ships_by_country:
                ships_by_country[ship.current_country] = []
            ships_by_country[ship.current_country].append(ship)
    
    return ships_by_country

def find_trade_opportunity_with_priority(corporation_id: str, ship: CargoShip) -> Optional[Dict]:
    data = load_maritime_data()
    state = load_corporations_state()
    
    if corporation_id not in state["corporations"]:
        return None
    
    corp = get_civil_corporation(corporation_id)
    if not corp:
        return None
    
    home_regions = get_regions_by_country(corp.country)
    operational_home_regions = [r for r in home_regions if is_region_operational(r)[0]]
    
    if not operational_home_regions or not ship.current_region:
        return None
    
    if not ship.cargo:
        product_type, cargo_amount, base_price = generate_cargo_for_country(corp.country, ship.type)
        ship.load_cargo(product_type, cargo_amount, base_price)
    
    states = load_states()
    existing_countries = [data["state"]["statename"] for data in states["players"].values()]
    
    potential_destinations = []
    coastal_regions = get_coastal_regions()
    
    for region_name, region_data in coastal_regions.items():
        if region_name in operational_home_regions:
            continue
        
        target_country = region_data["country"]
        
        if target_country not in existing_countries:
            continue
        
        operational, shipyards = is_region_operational(region_name)
        if not operational:
            continue
        
        if not is_trade_allowed(corp.country, target_country):
            continue
        
        distance = calculate_region_distance(ship.current_region, region_name)
        if distance >= 9999:
            continue
        
        priority_score = get_priority_score(ship.cargo, corp.country, target_country)
        
        potential_destinations.append({
            "region": region_name,
            "country": target_country,
            "distance": distance,
            "priority_score": priority_score,
            "shipyards": shipyards
        })
    
    if not potential_destinations:
        for region_name, region_data in coastal_regions.items():
            if region_name in operational_home_regions:
                continue
            
            target_country = region_data["country"]
            
            if target_country not in existing_countries:
                continue
            
            operational, shipyards = is_region_operational(region_name)
            if not operational:
                continue
            
            if not is_trade_allowed(corp.country, target_country):
                continue
            
            distance = calculate_region_distance(ship.current_region, region_name)
            if distance < 20000:
                potential_destinations.append({
                    "region": region_name,
                    "country": target_country,
                    "distance": distance,
                    "priority_score": 0,
                    "shipyards": shipyards
                })
    
    if not potential_destinations:
        return None
    
    potential_destinations.sort(key=lambda x: (-x["priority_score"], x["distance"]))
    
    top_destinations = potential_destinations[:5]
    dest = random.choice(top_destinations)
    
    return {
        "from_region": ship.current_region,
        "to_region": dest["region"],
        "to_country": dest["country"],
        "distance": dest["distance"],
        "priority_score": dest["priority_score"],
        "shipyards": dest["shipyards"]
    }

def start_trade_mission(ship: CargoShip, opportunity: Dict) -> Tuple[bool, str]:
    if not ship.cargo:
        country = ship.current_country
        product_type, cargo_amount, base_price = generate_cargo_for_country(country, ship.type)
        ship.load_cargo(product_type, cargo_amount, base_price)
    
    success, msg = ship.set_destination(opportunity["to_region"])
    if not success:
        return False, msg
    
    priority_text = ""
    if opportunity.get("priority_score", 0) > 0:
        priority_text = " (приоритетное направление!)"
    
    cargo_text = ship.get_cargo_text()
    return True, f"Корабль отправлен в {opportunity['to_region']} ({opportunity['to_country']}) с грузом: {cargo_text}{priority_text}"


# ==================== АСИНХРОННАЯ ФУНКЦИЯ COMPLETE_TRIP ====================

async def complete_trip(ship: CargoShip):
    """Асинхронное завершение рейса корабля с мультивалютной системой"""
    data = load_maritime_data()
    state = load_corporations_state()
    logs = load_ship_logs()
    
    if ship.corporation_id not in state["corporations"]:
        return
    
    corp_state = state["corporations"][ship.corporation_id]
    dest_region = ship.current_region
    dest_country = ship.current_country
    
    if not dest_region or not dest_country:
        return
    
    seller_country = corp_state.country if hasattr(corp_state, 'country') else ship.current_country
    
    base_value = ship.cargo_value
    delivery_bonus = base_value * 0.1
    
    import_tariff = 0
    export_tariff = 0
    
    if seller_country and dest_country and seller_country != dest_country:
        buyer_tariff = TariffSystem(dest_country)
        seller_tariff = TariffSystem(seller_country)
        
        for product_type in ship.cargo.keys():
            import_tariff += buyer_tariff.calculate_import_tariff(
                product_type, seller_country, base_value / max(1, len(ship.cargo))
            )
            export_tariff += seller_tariff.calculate_export_tariff(
                product_type, base_value / max(1, len(ship.cargo))
            )
    
    corp_profit_usd = base_value - export_tariff + delivery_bonus
    corp_state.budget += corp_profit_usd
    
    states = load_states()
    
    if import_tariff > 0:
        for player_data in states["players"].values():
            if player_data.get("state", {}).get("statename") == dest_country:
                if "foreign_reserves" not in player_data["economy"]:
                    player_data["economy"]["foreign_reserves"] = {"USD": 0, "EUR": 0, "CNY": 0, "gold_tons": 0}
                player_data["economy"]["foreign_reserves"]["USD"] = player_data["economy"]["foreign_reserves"].get("USD", 0) + import_tariff
                player_data["tariff_revenue_usd"] = player_data.get("tariff_revenue_usd", 0) + import_tariff
                if "port_revenue" not in player_data:
                    player_data["port_revenue"] = 0
                player_data["port_revenue"] += import_tariff
                break
    
    if export_tariff > 0:
        for player_data in states["players"].values():
            if player_data.get("state", {}).get("statename") == seller_country:
                if "foreign_reserves" not in player_data["economy"]:
                    player_data["economy"]["foreign_reserves"] = {"USD": 0, "EUR": 0, "CNY": 0, "gold_tons": 0}
                player_data["economy"]["foreign_reserves"]["USD"] = player_data["economy"]["foreign_reserves"].get("USD", 0) + export_tariff
                player_data["export_tariff_revenue_usd"] = player_data.get("export_tariff_revenue_usd", 0) + export_tariff
                break
    
    buyer_currency = get_currency_code_from_country(dest_country)
    rate = EXCHANGE_RATES_2019.get(dest_country, 1.0)
    local_revenue = (base_value + delivery_bonus) * rate
    
    for player_data in states["players"].values():
        if player_data.get("state", {}).get("statename") == seller_country:
            if "foreign_reserves" not in player_data["economy"]:
                player_data["economy"]["foreign_reserves"] = {"USD": 0, "EUR": 0, "CNY": 0, "gold_tons": 0}
            
            if buyer_currency not in player_data["economy"]["foreign_reserves"]:
                player_data["economy"]["foreign_reserves"][buyer_currency] = 0
            player_data["economy"]["foreign_reserves"][buyer_currency] += local_revenue
            
            if "port_revenue" not in player_data:
                player_data["port_revenue"] = 0
            player_data["port_revenue"] += local_revenue
            break
    
    save_states(states)
    
    ship.trips_completed += 1
    ship.total_cargo_delivered += sum(ship.cargo.values())
    ship.total_profit += corp_profit_usd
    
    log = {
        "timestamp": datetime.now().isoformat(),
        "ship_id": ship.id,
        "corporation_id": ship.corporation_id,
        "from_region": ship.current_region,
        "to_region": dest_region,
        "seller_country": seller_country,
        "buyer_country": dest_country,
        "cargo": ship.cargo,
        "cargo_value_usd": base_value,
        "corp_profit_usd": corp_profit_usd,
        "import_tariff_usd": import_tariff,
        "export_tariff_usd": export_tariff,
        "seller_received_currency": buyer_currency,
        "seller_received_amount": local_revenue
    }
    logs["logs"].append(log)
    
    ship.cargo = {}
    ship.cargo_value = 0
    ship.status = "idle"
    
    save_corporations_state(state)
    save_maritime_data(data)
    save_ship_logs(logs)
    
    await asyncio.sleep(0)


# ==================== ФОНОВАЯ ЗАДАЧА ====================

async def maritime_trade_loop(bot_instance):
    await bot_instance.wait_until_ready()
    
    print("Предварительная загрузка прибрежных регионов...")
    get_coastal_regions(force_refresh=True)
    
    data = load_maritime_data()
    migrated = 0
    for ship_data in data.get("ships", []):
        if "current_region" not in ship_data:
            old_port = ship_data.get("current_port")
            if old_port:
                ship_data["current_region"] = old_port
                if old_port in PORTS:
                    ship_data["current_country"] = PORTS[old_port]["country"]
            
            if "destination_port" in ship_data and ship_data.get("destination_port"):
                ship_data["destination_region"] = ship_data["destination_port"]
            
            migrated += 1
            if migrated % 100 == 0:
                await asyncio.sleep(0)
    
    if migrated > 0:
        save_maritime_data(data)
        print(f"Мигрировано {migrated} кораблей из старого формата")
    
    if not data.get("ships") or len(data["ships"]) == 0:
        print("Инициализация торгового флота...")
        initialize_fleet()
        data = load_maritime_data()
    
    loop_counter = 0
    CACHE_REFRESH_INTERVAL = 24
    PROCESS_BATCH_SIZE = 25
    
    while not bot_instance.is_closed():
        try:
            start_time = datetime.now()
            
            data = load_maritime_data()
            state = load_corporations_state()
            
            loop_counter += 1
            if loop_counter >= CACHE_REFRESH_INTERVAL:
                loop_counter = 0
                get_coastal_regions(force_refresh=True)
                await asyncio.sleep(0)
            
            ships_updated = 0
            ships_arrived = 0
            
            ships_list = data.get("ships", [])
            total_ships = len(ships_list)
            
            for i in range(0, total_ships, PROCESS_BATCH_SIZE):
                batch = ships_list[i:i+PROCESS_BATCH_SIZE]
                for ship_data in batch:
                    ship = CargoShip.from_dict(ship_data)
                    arrived = ship.update_progress()
                    
                    if arrived:
                        ships_arrived += 1
                        if ship.cargo:
                            await complete_trip(ship)
                        else:
                            ship.status = "idle"
                    
                    ship_data.update(ship.to_dict())
                    ships_updated += 1
                
                await asyncio.sleep(0)
            
            mission_count = 0
            for i in range(0, total_ships, PROCESS_BATCH_SIZE):
                batch = ships_list[i:i+PROCESS_BATCH_SIZE]
                for ship_data in batch:
                    ship = CargoShip.from_dict(ship_data)
                    
                    if ship.status == "idle" and ship.current_region:
                        chance = 0.75
                        
                        if not ship.cargo:
                            chance = 0.85
                        
                        operational, shipyards = is_region_operational(ship.current_region)
                        if operational and shipyards > 0:
                            chance += min(0.1, shipyards * 0.02)
                        
                        priorities = get_country_export_priorities(ship.current_country)
                        if priorities:
                            chance += 0.05
                        
                        chance = min(0.95, chance)
                        
                        if random.random() < chance:
                            if ship.corporation_id in state["corporations"]:
                                opportunity = find_trade_opportunity_with_priority(ship.corporation_id, ship)
                                if opportunity and opportunity["from_region"] == ship.current_region:
                                    start_trade_mission(ship, opportunity)
                                    ship_data.update(ship.to_dict())
                                    mission_count += 1
                
                await asyncio.sleep(0)
            
            ships_by_country = {}
            for ship_data in ships_list:
                ship_country = ship_data.get("current_country")
                if ship_country:
                    ships_by_country[ship_country] = ships_by_country.get(ship_country, 0) + 1
            
            total_cargo_value = sum(s.get("cargo_value", 0) for s in ships_list)
            
            for country, count in ships_by_country.items():
                _trade_history.add_record(country, count, total_cargo_value / max(1, len(ships_by_country)))
            
            save_trade_history()
            
            save_maritime_data(data)
            save_corporations_state(state)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            if ships_updated > 0 or ships_arrived > 0 or mission_count > 0:
                print(f"Морская торговля: {ships_updated} кораблей обновлено, {ships_arrived} прибыло, "
                      f"{mission_count} новых миссий, время: {elapsed:.2f}с")
            
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"Ошибка в maritime_trade_loop: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(3600)


# ==================== ИНИЦИАЛИЗАЦИЯ ФЛОТА ====================

def initialize_fleet():
    data = load_maritime_data()
    
    if data.get("ships") and len(data["ships"]) > 0:
        print(f"Флот уже инициализирован ({len(data['ships'])} кораблей)")
        return
    
    print("ИНИЦИАЛИЗАЦИЯ ТОРГОВОГО ФЛОТА")
    ships = []
    ship_id_counter = 1
    
    for corp_id, fleet_config in INITIAL_FLEET.items():
        country = CORP_COUNTRIES.get(corp_id)
        if not country:
            print(f"  Неизвестная страна для {corp_id}, пропускаем")
            continue
        
        regions = get_regions_by_country(country)
        operational_regions = [r for r in regions if is_region_operational(r)[0]]
        
        if not operational_regions:
            print(f"  Нет рабочих регионов для страны {country}, пропускаем {corp_id}")
            continue
        
        home_region = random.choice(operational_regions)
        corp_name = f"Корпорация {corp_id}"
        
        if CIVIL_CORPORATIONS_AVAILABLE:
            corp = get_civil_corporation(corp_id)
            if corp:
                corp_name = corp.name
        
        shipyards = get_region_shipyards(home_region)
        print(f"  {corp_name} ({country}) - регион {home_region} (верфей: {shipyards})")
        
        corp_ships = 0
        for ship_config in fleet_config:
            for i in range(ship_config["count"]):
                ship_id = f"ship_{ship_id_counter:06d}"
                ship_id_counter += 1
                
                ship = CargoShip(ship_id, corp_id, ship_config["type"])
                ship.current_region = home_region
                ship.current_country = country
                ship.status = "idle"
                
                ships.append(ship.to_dict())
                corp_ships += 1
        
        print(f"    Создано {corp_ships} кораблей")
    
    data["ships"] = ships
    data["initialized_at"] = datetime.now().isoformat()
    save_maritime_data(data)
    
    print(f"Итого создано {len(ships)} кораблей")


# ==================== ГЛАВНОЕ МЕНЮ ====================

async def show_maritime_menu(interaction_or_ctx, user_id: int):
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
            await interaction_or_ctx.response.send_message("У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("У вас нет государства!")
        return
    
    regions = get_regions_by_country(country_name)
    
    if CIVIL_CORPORATIONS_AVAILABLE:
        corps = get_civil_corporations_by_country(country_name)
    else:
        corps = {}
    
    data = load_maritime_data()
    all_ships = data.get("ships", [])
    ships_in_country = get_ships_by_country(country_name)
    
    ships_by_country = {}
    for ship_data in all_ships:
        ship_country = ship_data.get("current_country")
        if ship_country:
            ships_by_country[ship_country] = ships_by_country.get(ship_country, 0) + 1
    
    all_countries = []
    for data in states["players"].values():
        cnt = data["state"]["statename"]
        if cnt not in all_countries:
            all_countries.append(cnt)
    
    def sort_key(country):
        return (-ships_by_country.get(country, 0), country)
    
    all_countries.sort(key=sort_key)
    
    export_priorities = get_country_export_priorities(country_name)
    
    embed = discord.Embed(
        title=f"Морская торговля: {country_name}",
        color=DARK_THEME_COLOR
    )
    
    region_text = ""
    for region in regions[:10]:
        operational, shipyards = is_region_operational(region)
        if operational:
            region_text += f"{region} — {shipyards} верфей\n"
        else:
            region_text += f"{region} — нет верфей\n"
    
    if not region_text:
        region_text = "У страны нет выхода к морю"
    
    embed.add_field(name="Прибрежные регионы", value=region_text, inline=False)
    embed.add_field(name="Корпорации", value=f"Всего: {len(corps)}", inline=True)
    
    idle_ships = len([s for s in ships_in_country if s.status == "idle"])
    sailing_ships = len([s for s in ships_in_country if s.status == "sailing"])
    unloading_ships = len([s for s in ships_in_country if s.status == "unloading"])
    
    fleet_text = (
        f"Всего: {len(ships_in_country)}\n"
        f"На стоянке: {idle_ships + unloading_ships}\n"
        f"В плавании: {sailing_ships}"
    )
    
    embed.add_field(name="Торговый флот", value=fleet_text, inline=True)
    
    countries_text = ""
    for country in all_countries:
        count = ships_by_country.get(country, 0)
        if count > 0:
            countries_text += f"**{country}:** {count}\n"
        else:
            countries_text += f"_{country}:_ 0\n"
    
    embed.add_field(name="Распределение торгового флота", value=countries_text, inline=False)
    
    if export_priorities:
        priorities_text = ""
        for target_country, categories in list(export_priorities.items())[:10]:
            categories_names = [PRIORITY_CATEGORIES[cat]["name"] for cat in categories[:2] if cat in PRIORITY_CATEGORIES]
            if categories_names:
                priorities_text += f"**{target_country}:** {', '.join(categories_names)}\n"
            else:
                priorities_text += f"**{target_country}:** все категории\n"
        
        if priorities_text:
            embed.add_field(name="Приоритеты экспорта", value=priorities_text, inline=False)
        else:
            embed.add_field(name="Приоритеты экспорта", value="Не настроены", inline=False)
    else:
        embed.add_field(name="Приоритеты экспорта", value="Не настроены", inline=False)
    
    reserves = player_data["economy"].get("foreign_reserves", {})
    if reserves:
        reserves_text = ""
        for currency, amount in reserves.items():
            if amount > 0 and currency != "gold_tons":
                reserves_text += f"{currency}: {format_billion(amount)}\n"
        if reserves_text:
            embed.add_field(name="Валютные резервы", value=reserves_text, inline=False)
    
    view = MaritimeMainView(user_id, country_name, player_data)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view, ephemeral=True)


# ==================== КЛАССЫ ДЛЯ ПРОГНОЗОВ ====================

class TradeForecastView(discord.ui.View):
    def __init__(self, user_id: int, country_name: str, countries: List[str], page: int = 0):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.countries = countries
        self.page = page
        self.items_per_page = 3
        
        total_pages = (len(countries) + self.items_per_page - 1) // self.items_per_page
        
        if page > 0:
            prev_btn = discord.ui.Button(label="Предыдущая", style=discord.ButtonStyle.secondary)
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)
        
        self.page_label = discord.ui.Button(
            label=f"Страница {page + 1}/{total_pages}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        self.add_item(self.page_label)
        
        if page < total_pages - 1:
            next_btn = discord.ui.Button(label="Следующая", style=discord.ButtonStyle.secondary)
            next_btn.callback = self.next_page
            self.add_item(next_btn)
        
        back_btn = discord.ui.Button(label="Назад в меню", style=discord.ButtonStyle.primary)
        back_btn.callback = self.back_to_menu
        self.add_item(back_btn)
    
    def create_ascii_graph(self, data: List[int], width: int = 20, height: int = 6) -> str:
        if not data:
            return "Нет данных"
        
        points = data[-width:] if len(data) > width else data
        
        if len(points) < 2:
            return "Недостаточно данных"
        
        max_val = max(points) if max(points) > 0 else 1
        min_val = min(points)
        
        if max_val == min_val:
            max_val = min_val + 1
        
        lines = []
        for row in range(height):
            threshold = max_val - (row * (max_val - min_val) / (height - 1))
            line = ""
            for val in points:
                if val >= threshold:
                    line += "#"
                elif val >= threshold * 0.7:
                    line += "*"
                elif val >= threshold * 0.4:
                    line += "+"
                elif val >= threshold * 0.2:
                    line += "."
                else:
                    line += " "
            lines.append(line)
        
        result = "\n".join(lines)
        result += f"\n{min_val} {' ' * (width - len(str(min_val)) - len(str(max_val)))} {max_val}"
        
        return result
    
    def create_forecast_embed(self) -> discord.Embed:
        start = self.page * self.items_per_page
        end = start + self.items_per_page
        page_countries = self.countries[start:end]
        
        embed = discord.Embed(
            title="Прогноз торговли",
            description="Динамика торгового флота по странам\nДанные обновляются каждый час",
            color=DARK_THEME_COLOR
        )
        
        for target_country in page_countries:
            history = _trade_history.get_history(target_country, days=14)
            
            if not history or len(history) < 2:
                embed.add_field(
                    name=target_country,
                    value="Недостаточно данных для прогноза",
                    inline=False
                )
                continue
            
            ship_counts = [h["ship_count"] for h in history]
            cargo_values = [h["cargo_value"] for h in history]
            
            current_ships = ship_counts[-1] if ship_counts else 0
            prev_ships = ship_counts[-2] if len(ship_counts) > 1 else current_ships
            
            if prev_ships > 0:
                change = ((current_ships - prev_ships) / prev_ships) * 100
            else:
                change = 0 if current_ships == 0 else 100
            
            if len(ship_counts) >= 5:
                first_5 = sum(ship_counts[:5]) / 5
                last_5 = sum(ship_counts[-5:]) / 5
                trend = ((last_5 - first_5) / first_5 * 100) if first_5 > 0 else 0
            else:
                trend = change
            
            graph = self.create_ascii_graph(ship_counts[-10:], width=20, height=6)
            
            total_cargo = sum(cargo_values[-3:]) / 3 if cargo_values else 0
            cargo_text = format_billion(total_cargo) if total_cargo > 0 else "нет данных"
            
            value = (
                f"```\n{graph}\n```\n"
                f"Текущий флот: {current_ships} кораблей\n"
                f"Изменение: {change:+.1f}%\n"
                f"Тренд (5 дней): {trend:+.1f}%\n"
                f"Ср. стоимость груза: {cargo_text}"
            )
            
            embed.add_field(
                name=target_country,
                value=value,
                inline=False
            )
        
        embed.set_footer(text="График показывает динамику количества кораблей за последние дни")
        
        return embed
    
    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        view = TradeForecastView(self.user_id, self.country_name, self.countries, self.page - 1)
        embed = view.create_forecast_embed()
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        view = TradeForecastView(self.user_id, self.country_name, self.countries, self.page + 1)
        embed = view.create_forecast_embed()
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_menu(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await show_maritime_menu(interaction, self.user_id)


# ==================== ОСНОВНОЙ VIEW С КНОПКАМИ ====================

class MaritimeMainView(discord.ui.View):
    def __init__(self, user_id: int, country_name: str, player_data: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        
        regions_btn = discord.ui.Button(label="Поиск по морским регионам", style=discord.ButtonStyle.primary)
        regions_btn.callback = self.show_regions
        self.add_item(regions_btn)
        
        priorities_btn = discord.ui.Button(label="Приоритеты экспорта", style=discord.ButtonStyle.success)
        priorities_btn.callback = self.show_priorities
        self.add_item(priorities_btn)
        
        logs_btn = discord.ui.Button(label="Логи поставок", style=discord.ButtonStyle.secondary)
        logs_btn.callback = self.show_logs
        self.add_item(logs_btn)
        
        forecast_btn = discord.ui.Button(label="Прогнозы", style=discord.ButtonStyle.secondary)
        forecast_btn.callback = self.show_forecast
        self.add_item(forecast_btn)
        
        back_btn = discord.ui.Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def show_forecast(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        data = load_maritime_data()
        all_ships = data.get("ships", [])
        
        ships_by_country = {}
        for ship_data in all_ships:
            ship_country = ship_data.get("current_country")
            if ship_country:
                ships_by_country[ship_country] = ships_by_country.get(ship_country, 0) + 1
        
        countries_with_history = list(ships_by_country.keys())
        
        if not countries_with_history:
            await interaction.response.send_message("Нет данных для прогноза", ephemeral=True)
            return
        
        sorted_countries = sorted(countries_with_history, key=lambda c: ships_by_country.get(c, 0), reverse=True)
        
        view = TradeForecastView(self.user_id, self.country_name, sorted_countries, 0)
        embed = view.create_forecast_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_regions(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        view = MaritimeRegionsView(self.user_id, self.country_name, self.player_data)
        
        embed = discord.Embed(
            title="Морские регионы",
            description="Выберите регион для просмотра кораблей",
            color=DARK_THEME_COLOR
        )
        
        for region_name, sea_regions in SEA_REGIONS.items():
            total_ships = 0
            for sea_region in sea_regions:
                ships_by_country = get_ships_by_sea_region(sea_region)
                total_ships += sum(len(ships) for ships in ships_by_country.values())
            
            embed.add_field(name=region_name, value=f"Кораблей: {total_ships}", inline=True)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_priorities(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        available_countries = get_available_export_countries(self.country_name)
        
        if not available_countries:
            await interaction.response.send_message("Нет доступных стран для экспорта", ephemeral=True)
            return
        
        view = ExportPriorityCountrySelectView(self.user_id, self.country_name, self.player_data, available_countries)
        
        embed = discord.Embed(
            title="Приоритеты экспорта",
            description="Выберите страну для настройки приоритетных категорий экспорта",
            color=DARK_THEME_COLOR
        )
        
        export_priorities = get_country_export_priorities(self.country_name)
        
        if export_priorities:
            priorities_text = ""
            for target_country, categories in export_priorities.items():
                if any(c["name"] == target_country for c in available_countries):
                    categories_names = [PRIORITY_CATEGORIES[cat]["name"] for cat in categories if cat in PRIORITY_CATEGORIES]
                    priorities_text += f"* {target_country}: {', '.join(categories_names)}\n"
            if priorities_text:
                embed.add_field(name="Текущие приоритеты", value=priorities_text, inline=False)
            else:
                embed.add_field(name="Текущие приоритеты", value="Нет активных приоритетов", inline=False)
        else:
            embed.add_field(name="Текущие приоритеты", value="Не настроены", inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def show_logs(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        logs = load_ship_logs()
        
        if CIVIL_CORPORATIONS_AVAILABLE:
            corps = get_civil_corporations_by_country(self.country_name)
            corp_ids = set(corps.keys())
        else:
            corp_ids = set()
        
        country_logs = [log for log in logs["logs"] if log["corporation_id"] in corp_ids]
        
        embed = discord.Embed(
            title=f"Логи поставок: {self.country_name}",
            color=DARK_THEME_COLOR
        )
        
        if not country_logs:
            embed.description = "История поставок пуста"
        else:
            total_profit = 0
            for log in country_logs[-5:]:
                date = datetime.fromisoformat(log["timestamp"]).strftime("%d.%m.%Y %H:%M")
                
                cargo_text = ""
                for p, v in log.get("cargo", {}).items():
                    cargo_name = CARGO_TYPES.get(p, {}).get("name", p)
                    cargo_text += f"\n    {cargo_name}: {int(v)}"
                
                seller_currency = log.get("seller_received_currency", "USD")
                seller_amount = log.get("seller_received_amount", 0)
                
                embed.add_field(
                    name=date,
                    value=f"Маршрут: {log['from_region']} -> {log['to_region']}{cargo_text}\n"
                          f"Стоимость груза: ${log['cargo_value_usd']:,.0f}\n"
                          f"Прибыль корпорации: ${log['corp_profit_usd']:,.0f}\n"
                          f"Пошлины (импорт): ${log.get('import_tariff_usd', 0):,.0f}\n"
                          f"Пошлины (экспорт): ${log.get('export_tariff_usd', 0):,.0f}\n"
                          f"Продавец получил: {format_billion(seller_amount)} {seller_currency}",
                    inline=False
                )
                
                total_profit += log.get("corp_profit_usd", 0)
            
            embed.set_footer(text=f"Всего поставок: {len(country_logs)} | Прибыль корпораций: ${total_profit:,.0f}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            from bot import StateButtons
        except ImportError:
            class StateButtons(discord.ui.View):
                def __init__(self, *args, **kwargs):
                    super().__init__(timeout=60)
                    self.user_id = args[0] if len(args) > 0 else None
                    self.country_name = args[1] if len(args) > 1 else None
                    self.player_data = args[2] if len(args) > 2 else None
        
        view = StateButtons(self.user_id, self.country_name, self.player_data)
        
        state = self.player_data["state"]
        politics = self.player_data["politics"]
        economy = self.player_data["economy"]
        
        embed = discord.Embed(
            title=f"{state['statename']}",
            description=f"Лидер: {interaction.user.mention}",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Население", value=f"{format_number(state['population'])} чел.", inline=True)
        embed.add_field(name="Территория", value=f"{format_number(state['territory'])} км²", inline=True)
        embed.add_field(name="Стабильность", value=f"{state['stability']:.1f}%", inline=True)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ==================== ОСТАЛЬНЫЕ VIEW КЛАССЫ ====================

class ExportPriorityCountrySelectView(discord.ui.View):
    def __init__(self, user_id: int, country_name: str, player_data: Dict, available_countries: List[Dict]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.available_countries = available_countries
        
        options = []
        for country in available_countries[:25]:
            options.append(discord.SelectOption(
                label=country["name"],
                description=f"Регионов: {country['region_count']}",
                value=country["name"]
            ))
        
        select = Select(
            placeholder="Выберите страну для настройки приоритетов...",
            options=options,
            custom_id="country_select"
        )
        select.callback = self.select_country
        self.add_item(select)
        
        back_btn = discord.ui.Button(label="Назад к меню", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def select_country(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        target_country = interaction.data["values"][0]
        
        export_priorities = get_country_export_priorities(self.country_name)
        current_categories = export_priorities.get(target_country, [])
        
        view = ExportPriorityCategorySelectView(
            self.user_id, self.country_name, self.player_data,
            target_country, current_categories
        )
        
        embed = discord.Embed(
            title=f"Приоритеты экспорта в {target_country}",
            description="Выберите категории товаров, которые будут приоритетно экспортироваться в эту страну",
            color=DARK_THEME_COLOR
        )
        
        if current_categories:
            categories_names = [PRIORITY_CATEGORIES[cat]["name"] for cat in current_categories if cat in PRIORITY_CATEGORIES]
            embed.add_field(name="Текущие приоритеты", value="\n".join(categories_names), inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await show_maritime_menu(interaction, self.user_id)


class ExportPriorityCategorySelectView(discord.ui.View):
    def __init__(self, user_id: int, country_name: str, player_data: Dict,
                 target_country: str, current_categories: List[str]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.target_country = target_country
        self.current_categories = current_categories
        
        options = []
        for category_id, category_info in PRIORITY_CATEGORIES.items():
            options.append(discord.SelectOption(
                label=category_info["name"],
                value=category_id,
                default=category_id in current_categories
            ))
        
        select = Select(
            placeholder="Выберите категории (можно несколько)...",
            options=options,
            min_values=0,
            max_values=len(options),
            custom_id="category_select"
        )
        select.callback = self.select_categories
        self.add_item(select)
        
        reset_btn = discord.ui.Button(label="Сбросить все", style=discord.ButtonStyle.danger)
        reset_btn.callback = self.reset_priorities
        self.add_item(reset_btn)
        
        back_btn = discord.ui.Button(label="Назад к странам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def select_categories(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        selected_categories = interaction.data["values"]
        
        success = set_export_priority(self.country_name, self.target_country, selected_categories)
        
        if not success:
            embed = discord.Embed(
                title="Ошибка",
                description=f"Не удалось установить приоритеты для {self.target_country}.",
                color=discord.Color.red()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        embed = discord.Embed(
            title="Приоритеты сохранены",
            description=f"Для экспорта в {self.target_country} установлены приоритеты:",
            color=DARK_THEME_COLOR
        )
        
        if selected_categories:
            categories_names = [PRIORITY_CATEGORIES[cat]["name"] for cat in selected_categories if cat in PRIORITY_CATEGORIES]
            embed.add_field(name="Категории", value="\n".join(categories_names), inline=False)
        else:
            embed.add_field(name="Категории", value="Приоритеты сброшены", inline=False)
        
        available_countries = get_available_export_countries(self.country_name)
        view = ExportPriorityCountrySelectView(self.user_id, self.country_name, self.player_data, available_countries)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def reset_priorities(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        success = clear_export_priorities(self.country_name, self.target_country)
        
        embed = discord.Embed(
            title="Приоритеты сброшены",
            description=f"Приоритеты экспорта в {self.target_country} удалены",
            color=DARK_THEME_COLOR
        )
        
        available_countries = get_available_export_countries(self.country_name)
        view = ExportPriorityCountrySelectView(self.user_id, self.country_name, self.player_data, available_countries)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        available_countries = get_available_export_countries(self.country_name)
        view = ExportPriorityCountrySelectView(self.user_id, self.country_name, self.player_data, available_countries)
        
        embed = discord.Embed(
            title="Приоритеты экспорта",
            description="Выберите страну для настройки приоритетных категорий экспорта",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class MaritimeRegionsView(discord.ui.View):
    def __init__(self, user_id: int, country_name: str, player_data: Dict):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        
        options = []
        for region_name in SEA_REGIONS.keys():
            options.append(discord.SelectOption(
                label=region_name,
                value=region_name
            ))
        
        select = Select(
            placeholder="Выберите регион...",
            options=options[:25],
            custom_id="region_select"
        )
        select.callback = self.select_region
        self.add_item(select)
        
        back_btn = discord.ui.Button(label="Назад к меню", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def select_region(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        region_name = interaction.data["values"][0]
        sea_regions = SEA_REGIONS[region_name]
        
        view = MaritimeSeaView(self.user_id, self.country_name, self.player_data, region_name, sea_regions)
        
        embed = discord.Embed(
            title=region_name,
            description="Выберите море для просмотра кораблей",
            color=DARK_THEME_COLOR
        )
        
        for sea_region in sea_regions[:10]:
            ships_by_country = get_ships_by_sea_region(sea_region)
            total_ships = sum(len(ships) for ships in ships_by_country.values())
            
            countries_text = ""
            for country, ships in list(ships_by_country.items())[:3]:
                countries_text += f"{country}: {len(ships)} "
            if len(ships_by_country) > 3:
                countries_text += f"+{len(ships_by_country)-3}"
            
            embed.add_field(
                name=sea_region.value,
                value=f"Кораблей: {total_ships}\n{countries_text}",
                inline=True
            )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await show_maritime_menu(interaction, self.user_id)


class MaritimeSeaView(discord.ui.View):
    def __init__(self, user_id: int, country_name: str, player_data: Dict, main_region: str, sea_regions: List[SeaRegion]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.main_region = main_region
        self.sea_regions = sea_regions
        
        options = []
        for sea_region in sea_regions:
            ships_by_country = get_ships_by_sea_region(sea_region)
            total_ships = sum(len(ships) for ships in ships_by_country.values())
            options.append(discord.SelectOption(
                label=f"{sea_region.value} ({total_ships} кораблей)",
                value=sea_region.value
            ))
        
        select = Select(
            placeholder="Выберите море...",
            options=options[:25],
            custom_id="sea_select"
        )
        select.callback = self.select_sea
        self.add_item(select)
        
        back_btn = discord.ui.Button(label="Назад к регионам", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def select_sea(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        sea_name = interaction.data["values"][0]
        
        selected_region = None
        for sea_region in self.sea_regions:
            if sea_region.value == sea_name:
                selected_region = sea_region
                break
        
        if not selected_region:
            await interaction.response.send_message("Регион не найден!", ephemeral=True)
            return
        
        ships_by_country = get_ships_by_sea_region(selected_region)
        
        options = []
        for country, ships in ships_by_country.items():
            options.append(discord.SelectOption(
                label=f"{country} ({len(ships)} кораблей)",
                value=country
            ))
        
        if options:
            view = MaritimeCountrySelectView(self.user_id, self.country_name, self.player_data, 
                                           self.main_region, selected_region, ships_by_country, options)
            
            embed = discord.Embed(
                title=sea_name,
                description="Выберите страну для просмотра кораблей",
                color=DARK_THEME_COLOR
            )
            
            for country, ships in ships_by_country.items():
                in_port = len([s for s in ships if s.status in ["idle", "loading", "unloading"]])
                at_sea = len([s for s in ships if s.status == "sailing"])
                embed.add_field(
                    name=country,
                    value=f"Всего: {len(ships)} (в регионе: {in_port}, в море: {at_sea})",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            view = discord.ui.View(timeout=120)
            back_btn = discord.ui.Button(label="Назад к морям", style=discord.ButtonStyle.secondary)
            back_btn.callback = self.go_back
            view.add_item(back_btn)
            
            embed = discord.Embed(
                title=sea_name,
                description="В этом регионе нет кораблей",
                color=DARK_THEME_COLOR
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await show_maritime_menu(interaction, self.user_id)


class MaritimeCountrySelectView(discord.ui.View):
    def __init__(self, user_id: int, country_name: str, player_data: Dict, 
                 main_region: str, sea_region: SeaRegion, ships_by_country: Dict[str, List[CargoShip]], 
                 country_options: List[discord.SelectOption]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.main_region = main_region
        self.sea_region = sea_region
        self.ships_by_country = ships_by_country
        
        select = Select(
            placeholder="Выберите страну...",
            options=country_options[:25],
            custom_id="country_select"
        )
        select.callback = self.select_country
        self.add_item(select)
        
        back_btn = discord.ui.Button(label="Назад к морю", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def select_country(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        selected_country = interaction.data["values"][0]
        ships = self.ships_by_country.get(selected_country, [])
        
        view = MaritimeShipListView(self.user_id, self.country_name, self.player_data,
                                   self.main_region, self.sea_region, selected_country, ships, 0)
        
        await view.show_page(interaction)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await show_maritime_menu(interaction, self.user_id)


class MaritimeShipListView(discord.ui.View):
    def __init__(self, user_id: int, country_name: str, player_data: Dict,
                 main_region: str, sea_region: SeaRegion, selected_country: str,
                 ships: List[CargoShip], page: int):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.main_region = main_region
        self.sea_region = sea_region
        self.selected_country = selected_country
        self.ships = ships
        self.page = page
        self.ships_per_page = 5
        
        total_pages = (len(ships) + self.ships_per_page - 1) // self.ships_per_page
        
        if page > 0:
            prev_btn = discord.ui.Button(label="Предыдущая", style=discord.ButtonStyle.secondary)
            prev_btn.callback = self.prev_page
            self.add_item(prev_btn)
        
        if page < total_pages - 1:
            next_btn = discord.ui.Button(label="Следующая", style=discord.ButtonStyle.secondary)
            next_btn.callback = self.next_page
            self.add_item(next_btn)
        
        back_btn = discord.ui.Button(label="Назад к странам", style=discord.ButtonStyle.primary)
        back_btn.callback = self.go_back
        self.add_item(back_btn)
    
    async def show_page(self, interaction: discord.Interaction):
        start = self.page * self.ships_per_page
        end = start + self.ships_per_page
        page_ships = self.ships[start:end]
        
        embed = discord.Embed(
            title=f"Корабли {self.selected_country} в {self.sea_region.value}",
            description=f"Страница {self.page + 1} из {(len(self.ships) + self.ships_per_page - 1) // self.ships_per_page}",
            color=DARK_THEME_COLOR
        )
        
        for ship in page_ships:
            ship_info = [
                f"**Тип:** {SHIP_TYPES[ship.type]['name']}",
                f"**Статус:** {ship.get_status_text()}",
                f"**Регион:** {ship.current_region or 'None'}",
                f"**Страна:** {ship.current_country or 'None'}",
            ]
            
            if ship.destination_region:
                ship_info.append(f"**Назначение:** {ship.destination_region} ({ship.destination_country})")
            
            if ship.cargo:
                cargo_text = "**Груз:**"
                for p, v in ship.cargo.items():
                    cargo_name = CARGO_TYPES.get(p, {}).get("name", p)
                    cargo_text += f"\n  * {cargo_name}: {v:.0f}"
                ship_info.append(cargo_text)
            else:
                ship_info.append("**Груз:** Пустой")
            
            if ship.damage > 0:
                ship_info.append(f"**Износ:** {ship.damage:.0f}%")
            
            if ship.trips_completed > 0:
                ship_info.append(f"**Рейсов:** {ship.trips_completed}")
            
            embed.add_field(
                name=ship.name,
                value="\n".join(ship_info),
                inline=False
            )
        
        if not page_ships:
            embed.description = "Нет кораблей для отображения"
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def prev_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        view = MaritimeShipListView(self.user_id, self.country_name, self.player_data,
                                   self.main_region, self.sea_region, self.selected_country,
                                   self.ships, self.page - 1)
        await view.show_page(interaction)
    
    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        view = MaritimeShipListView(self.user_id, self.country_name, self.player_data,
                                   self.main_region, self.sea_region, self.selected_country,
                                   self.ships, self.page + 1)
        await view.show_page(interaction)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await show_maritime_menu(interaction, self.user_id)


# ==================== АДМИН-КОМАНДЫ ====================

async def admin_create_ship(interaction_or_ctx, corporation_id: str, ship_type: str, home_region: str):
    operational, shipyards = is_region_operational(home_region)
    if not operational:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message(f"Регион {home_region} не может принимать корабли (нет верфей)", ephemeral=True)
        else:
            await interaction_or_ctx.send(f"Регион {home_region} не может принимать корабли (нет верфей)")
        return
    
    country = get_country_from_region(home_region)
    if not country:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message(f"Регион {home_region} не найден", ephemeral=True)
        else:
            await interaction_or_ctx.send(f"Регион {home_region} не найден")
        return
    
    data = load_maritime_data()
    ship_id = f"ship_{len(data.get('ships', [])) + 1:06d}"
    ship = CargoShip(ship_id, corporation_id, ship_type)
    ship.current_region = home_region
    ship.current_country = country
    ship.status = "idle"
    
    data["ships"].append(ship.to_dict())
    save_maritime_data(data)
    
    embed = discord.Embed(
        title="Корабль создан",
        color=DARK_THEME_COLOR
    )
    embed.add_field(name="ID корабля", value=ship.id, inline=True)
    embed.add_field(name="Название", value=ship.name, inline=True)
    embed.add_field(name="Регион базирования", value=ship.current_region, inline=True)
    embed.add_field(name="Страна", value=ship.current_country, inline=True)
    embed.add_field(name="Верфей в регионе", value=str(shipyards), inline=True)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, ephemeral=True)


async def admin_force_trade(interaction_or_ctx, ship_id: str):
    data = load_maritime_data()
    
    ship_data = None
    for s in data.get("ships", []):
        if s["id"] == ship_id:
            ship_data = s
            break
    
    if not ship_data:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message(f"Корабль с ID {ship_id} не найден!", ephemeral=True)
        else:
            await interaction_or_ctx.send(f"Корабль с ID {ship_id} не найден!", ephemeral=True)
        return
    
    ship = CargoShip.from_dict(ship_data)
    
    if ship.status != "idle":
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message(f"Корабль не в режиме ожидания (статус: {ship.status})", ephemeral=True)
        else:
            await interaction_or_ctx.send(f"Корабль не в режиме ожидания (статус: {ship.status})", ephemeral=True)
        return
    
    opportunity = find_trade_opportunity_with_priority(ship.corporation_id, ship)
    if not opportunity:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message("Не найдено торговых возможностей!", ephemeral=True)
        else:
            await interaction_or_ctx.send("Не найдено торговых возможностей!", ephemeral=True)
        return
    
    success, msg = start_trade_mission(ship, opportunity)
    
    if success:
        for i, s in enumerate(data["ships"]):
            if s["id"] == ship.id:
                data["ships"][i] = ship.to_dict()
                break
        save_maritime_data(data)
    
    embed = discord.Embed(
        title="Миссия начата" if success else "Ошибка",
        description=msg,
        color=DARK_THEME_COLOR if success else discord.Color.red()
    )
    
    if success:
        embed.add_field(name="Регион назначения", value=opportunity["to_region"], inline=True)
        embed.add_field(name="Страна", value=opportunity["to_country"], inline=True)
        embed.add_field(name="Верфей в регионе", value=str(opportunity.get("shipyards", 0)), inline=True)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, ephemeral=True)


async def admin_force_init_fleet(interaction_or_ctx):
    data = load_maritime_data()
    old_count = len(data.get("ships", []))
    data["ships"] = []
    save_maritime_data(data)
    
    initialize_fleet()
    
    data = load_maritime_data()
    new_count = len(data.get("ships", []))
    
    embed = discord.Embed(
        title="Инициализация флота",
        color=DARK_THEME_COLOR
    )
    
    embed.add_field(name="Было кораблей", value=str(old_count), inline=True)
    embed.add_field(name="Стало кораблей", value=str(new_count), inline=True)
    
    if new_count == 0:
        embed.description = "Не удалось создать корабли! Проверьте логи сервера."
    else:
        embed.description = f"Успешно создано {new_count} кораблей"
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, ephemeral=True)


# ==================== АВТОМАТИЧЕСКАЯ ИНИЦИАЛИЗАЦИЯ ====================

try:
    get_coastal_regions()
    load_trade_history()
    
    data = load_maritime_data()
    if not data.get("ships") or len(data["ships"]) == 0:
        print("Инициализация торгового флота...")
        initialize_fleet()
    else:
        print(f"Торговый флот уже инициализирован ({len(data['ships'])} кораблей)")
except Exception as e:
    print(f"Ошибка при инициализации флота: {e}")


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_maritime_menu',
    'maritime_trade_loop',
    'admin_create_ship',
    'admin_force_trade',
    'admin_force_init_fleet',
    'initialize_fleet',
    'get_coastal_regions',
    'get_regions_by_country',
    'get_region_shipyards',
    'is_region_operational',
    'get_region_capacity',
    'get_country_from_region',
    'get_sea_zone_from_region',
    'invalidate_coastal_cache',
    'SeaRegion',
    'CARGO_TYPES',
    'SHIP_TYPES',
    'PRIORITY_CATEGORIES',
    'get_country_export_priorities',
    'set_export_priority',
    'clear_export_priorities',
    'get_available_export_countries',
    'is_trade_allowed',
    'update_ships_on_region_transfer',
    'update_priorities_on_region_transfer',
    'PORTS',
    'REGION_TO_PORT',
    'get_ships_by_country',
    'get_ships_by_sea_region',
]

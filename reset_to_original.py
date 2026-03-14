# reset_to_original.py - Модуль для сброса всех систем к исходным значениям
# ПОЛНОСТЬЮ ОБНОВЛЕНО: добавлены все новые механики

import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import copy
from datetime import datetime
import os
from utils import DATA_DIR
import shutil
from typing import Dict

# Импорт ID канала для логов
from config import ADMIN_LOG_CHANNEL_ID

# Добавить в начало файла после других импортов
try:
    from central_bank import BASE_INTEREST_RATES, BASE_GOLD_RESERVES, TARGET_INFLATION
except ImportError:
    # Запасные значения на случай отсутствия импорта
    BASE_INTEREST_RATES = {
        "США": 5.25, "Россия": 16.0, "Китай": 3.45, "Германия": 4.5,
        "Великобритания": 5.25, "Франция": 4.5, "Япония": 0.1,
        "Израиль": 4.5, "Украина": 15.0, "Иран": 18.0
    }
    BASE_GOLD_RESERVES = {
        "США": 8133.5, "Россия": 2332.0, "Китай": 1948.0, "Германия": 3352.0,
        "Великобритания": 310.0, "Франция": 2436.0, "Япония": 846.0,
        "Израиль": 0.0, "Украина": 27.0, "Иран": 340.0
    }
    TARGET_INFLATION = {
        "США": 2.0, "Россия": 4.0, "Китай": 3.0, "Германия": 2.0,
        "Великобритания": 2.0, "Франция": 2.0, "Япония": 2.0,
        "Израиль": 2.0, "Украина": 5.0, "Иран": 10.0
    }

# Файлы с данными
STATES_FILE = os.path.join(DATA_DIR, 'states.json')
PRODUCTION_QUEUE_FILE = 'production_queue.json'
CIVIL_PRODUCTION_QUEUE_FILE = 'civil_production_queue.json'
CONSTRUCTION_QUEUE_FILE = 'infra_construction.json'
TRADES_FILE = 'trades.json'
TRANSFERS_FILE = 'transfers.json'
RESEARCH_FILE = 'research_data.json'
TARIFFS_FILE = 'tariffs.json'
INFRASTRUCTURE_FILE = 'infrastructure.json'
CONFLICTS_FILE = 'conflicts.json'
CENTRAL_BANK_FILE = 'central_bank.json'
LAST_EXTRACTION_FILE = 'last_extraction.json'

# НОВЫЕ ФАЙЛЫ
CORPORATIONS_STATE_FILE = 'corporations_state.json'
CORPORATIONS_STARTING_DATA_FILE = 'corporations_starting_data.json'
MOBILIZATION_FILE = 'mobilization.json'
GAME_TIME_FILE = 'game_time.json'
SATELLITES_FILE = 'satellites.json'
MILITARY_DOCTRINES_FILE = 'military_doctrines.json'
ESPIONAGE_FILE = 'espionage.json'

# ==================== БАЗОВЫЕ ПОКАЗАТЕЛИ НАСЕЛЕНИЯ ====================

BASE_POPULATION_SAVINGS = {
    "США": 5500000000000,
    "Россия": 1500000000000,
    "Китай": 15000000000000,
    "Германия": 2500000000000,
    "Великобритания": 2000000000000,
    "Франция": 2000000000000,
    "Япония": 8000000000000,
    "Израиль": 500000000000,
    "Украина": 50000000000,
    "Иран": 100000000000
}

# ==================== ОРИГИНАЛЬНЫЕ ДАННЫЕ ДЛЯ ТАРИФОВ ====================

ORIGINAL_TARIFFS = {
    "tariffs": {
        "США": {
            "base_tariff": 3.4,
            "specific_tariffs": {
                "Китай": 19.3,
                "Россия": 0.0,
                "Германия": 0.0,
                "Великобритания": 0.0,
                "Япония": 0.0,
                "Израиль": 0.0
            },
            "product_tariffs": {
                "steel": 25.0,
                "aluminum": 10.0,
                "uranium": 0.0,
                "electronics": 2.5,
                "rare_metals": 0.0,
                "oil": 0.5,
                "gas": 0.0,
                "coal": 0.0,
                "food": 2.5,
                "cars": 2.5,
                "trucks": 25.0,
                "agricultural_machinery": 0.0,
                "food_products": 3.0,
                "pharmaceuticals": 0.0,
                "chemicals": 2.8,
                "clothing": 12.0,
                "consumer_electronics": 2.0,
                "aerospace_equipment": 1.5,
                "medical_equipment": 0.0,
                "drones": 8.5,
                "fpv_drones": 8.5,
                "tanks": 5.0,
                "fighters": 5.0,
                "missiles": 5.0,
                "small_arms": 3.5
            },
            "export_tariffs": {},
            "trade_agreements": [
                "Канада",
                "Мексика",
                "Израиль",
                "Австралия",
                "Южная Корея",
                "Япония"
            ],
            "trade_wars": {
                "Китай": 7.5
            },
            "embargoes": {
                "Иран": ["all"],
                "Северная Корея": ["all"],
                "Сирия": ["all"],
                "Куба": ["all"],
                "Венесуэла": ["military", "oil"]
            },
            "sanctions": {},
            "last_updated": "2022-02-23"
        },
        "Россия": {
            "base_tariff": 5.8,
            "specific_tariffs": {
                "США": 0.0,
                "Германия": 0.0,
                "Великобритания": 0.0,
                "Япония": 0.0,
                "Китай": 0.0,
                "Индия": 0.0,
                "Турция": 0.0,
                "Израиль": 0.0,
                "Украина": 0.0,
                "Беларусь": 0.0,
                "Казахстан": 0.0
            },
            "product_tariffs": {
                "cars": 15.0,
                "trucks": 10.0,
                "agricultural_machinery": 5.0,
                "pharmaceuticals": 3.0,
                "electronics": 8.0,
                "clothing": 12.0,
                "food_products": 8.0,
                "chemicals": 5.0,
                "steel": 5.0,
                "aluminum": 5.0,
                "uranium": 0.0,
                "oil": 0.0,
                "gas": 0.0,
                "coal": 0.0,
                "food": 5.0,
                "consumer_electronics": 10.0,
                "medical_equipment": 3.0,
                "aerospace_equipment": 5.0,
                "drones": 10.0,
                "fpv_drones": 12.0,
                "tanks": 0.0,
                "btr": 0.0,
                "fighters": 0.0,
                "missiles": 0.0,
                "small_arms": 0.0
            },
            "export_tariffs": {
                "oil": 30.0,
                "gas": 30.0,
                "coal": 15.0,
                "uranium": 10.0,
                "steel": 5.0,
                "aluminum": 5.0,
                "rare_metals": 10.0,
                "tanks": 15.0,
                "fighters": 20.0,
                "missiles": 25.0,
                "small_arms": 8.0,
                "fpv_drones": 15.0
            },
            "trade_agreements": [
                "Беларусь",
                "Казахстан",
                "Армения",
                "Кыргызстан",
                "Вьетнам",
                "Сербия",
                "Иран",
                "Китай",
                "Индия"
            ],
            "trade_wars": {},
            "embargoes": {
                "Грузия": ["military"],
                "Украина": ["military"],
                "Албания": ["all"],
                "Черногория": ["all"],
                "Северная Македония": ["all"]
            },
            "sanctions": {},
            "last_updated": "2022-02-23"
        },
        "Китай": {
            "base_tariff": 7.5,
            "specific_tariffs": {
                "США": 12.5,
                "Австралия": 5.0,
                "Япония": 2.0,
                "Южная Корея": 2.0,
                "Индия": 2.5,
                "Россия": 0.0,
                "Германия": 0.0,
                "Великобритания": 0.0,
                "Израиль": 0.0,
                "Иран": 0.0
            },
            "product_tariffs": {
                "cars": 15.0,
                "trucks": 15.0,
                "electronics": 10.0,
                "steel": 7.0,
                "aluminum": 7.0,
                "chemicals": 5.5,
                "uranium": 0.0,
                "rare_metals": 0.0,
                "oil": 1.0,
                "gas": 0.0,
                "coal": 3.0,
                "food": 5.0,
                "agricultural_machinery": 5.0,
                "pharmaceuticals": 3.0,
                "medical_equipment": 2.0,
                "aerospace_equipment": 8.0,
                "drones": 12.0,
                "fpv_drones": 15.0,
                "tanks": 8.0,
                "fighters": 12.0,
                "missiles": 15.0,
                "small_arms": 4.0,
                "ships": 8.0
            },
            "export_tariffs": {
                "rare_metals": 20.0,
                "electronics": 5.0,
                "drones": 8.0,
                "fpv_drones": 10.0
            },
            "trade_agreements": [
                "Россия",
                "Пакистан",
                "Новая Зеландия",
                "Сингапур",
                "Чили",
                "Перу",
                "Иран",
                "Вьетнам",
                "Таиланд",
                "Индонезия"
            ],
            "trade_wars": {
                "США": 7.5
            },
            "embargoes": {
                "Северная Корея": ["military", "nuclear"],
                "Тайвань": ["military"]
            },
            "sanctions": {},
            "last_updated": "2022-02-23"
        },
        "Германия": {
            "base_tariff": 4.2,
            "specific_tariffs": {
                "Китай": 5.0,
                "Россия": 0.0,
                "США": 0.0,
                "Великобритания": 0.0,
                "Япония": 0.0,
                "Израиль": 0.0,
                "Украина": 0.0,
                "Турция": 2.0,
                "Индия": 1.5
            },
            "product_tariffs": {
                "cars": 10.0,
                "trucks": 12.0,
                "agricultural_machinery": 5.0,
                "electronics": 4.0,
                "chemicals": 3.0,
                "pharmaceuticals": 2.0,
                "steel": 3.0,
                "aluminum": 3.0,
                "uranium": 0.0,
                "rare_metals": 2.0,
                "oil": 0.0,
                "gas": 0.0,
                "coal": 0.0,
                "food": 2.0,
                "aerospace_equipment": 4.0,
                "medical_equipment": 1.0,
                "drones": 6.0,
                "fpv_drones": 8.0,
                "tanks": 5.0,
                "fighters": 8.0,
                "missiles": 8.0,
                "small_arms": 3.0
            },
            "export_tariffs": {},
            "trade_agreements": [
                "Франция",
                "Италия",
                "Нидерланды",
                "Бельгия",
                "Испания",
                "Польша",
                "Чехия",
                "Австрия",
                "Швеция",
                "Дания",
                "Финляндия",
                "Великобритания",
                "Швейцария",
                "Норвегия"
            ],
            "trade_wars": {},
            "embargoes": {
                "Северная Корея": ["all"],
                "Иран": ["military", "nuclear"],
                "Сирия": ["all"],
                "Венесуэла": ["military"]
            },
            "sanctions": {},
            "last_updated": "2022-02-23"
        },
        "Великобритания": {
            "base_tariff": 4.0,
            "specific_tariffs": {
                "Китай": 5.0,
                "Россия": 0.0,
                "США": 0.0,
                "Германия": 0.0,
                "Япония": 0.0,
                "Израиль": 0.0,
                "Индия": 2.0,
                "Турция": 1.5
            },
            "product_tariffs": {
                "cars": 10.0,
                "trucks": 12.0,
                "agricultural_machinery": 5.0,
                "electronics": 3.0,
                "chemicals": 3.5,
                "pharmaceuticals": 2.0,
                "steel": 3.0,
                "aluminum": 3.0,
                "uranium": 0.0,
                "rare_metals": 2.0,
                "oil": 0.0,
                "gas": 0.0,
                "coal": 0.0,
                "food": 2.0,
                "aerospace_equipment": 4.0,
                "medical_equipment": 1.0,
                "drones": 6.0,
                "fpv_drones": 8.0,
                "tanks": 5.0,
                "fighters": 8.0,
                "missiles": 8.0,
                "small_arms": 3.0,
                "ships": 2.0
            },
            "export_tariffs": {},
            "trade_agreements": [
                "США",
                "Канада",
                "Австралия",
                "Новая Зеландия",
                "Япония",
                "Сингапур",
                "Южная Корея",
                "Израиль",
                "Европейский Союз"
            ],
            "trade_wars": {},
            "embargoes": {
                "Северная Корея": ["all"],
                "Иран": ["military", "nuclear"],
                "Сирия": ["all"],
                "Венесуэла": ["military"]
            },
            "sanctions": {},
            "last_updated": "2022-02-23"
        },
        "Франция": {
            "base_tariff": 4.2,
            "specific_tariffs": {
                "Китай": 5.0,
                "Россия": 0.0,
                "США": 0.0,
                "Великобритания": 0.0,
                "Германия": 0.0,
                "Израиль": 0.0,
                "Индия": 2.0,
                "Турция": 2.0
            },
            "product_tariffs": {
                "cars": 10.0,
                "trucks": 12.0,
                "agricultural_machinery": 5.0,
                "electronics": 3.0,
                "chemicals": 3.5,
                "pharmaceuticals": 2.0,
                "steel": 3.0,
                "aluminum": 3.0,
                "uranium": 0.0,
                "rare_metals": 2.0,
                "oil": 0.0,
                "gas": 0.0,
                "coal": 0.0,
                "food": 2.0,
                "aerospace_equipment": 4.0,
                "medical_equipment": 1.0,
                "drones": 6.0,
                "fpv_drones": 8.0,
                "tanks": 5.0,
                "fighters": 8.0,
                "missiles": 8.0,
                "small_arms": 3.0,
                "ships": 2.0
            },
            "export_tariffs": {},
            "trade_agreements": [
                "Германия",
                "Италия",
                "Испания",
                "Португалия",
                "Бельгия",
                "Нидерланды",
                "Польша",
                "Великобритания",
                "Швейцария"
            ],
            "trade_wars": {},
            "embargoes": {
                "Северная Корея": ["all"],
                "Иран": ["military", "nuclear"],
                "Сирия": ["all"]
            },
            "sanctions": {},
            "last_updated": "2022-02-23"
        },
        "Япония": {
            "base_tariff": 3.8,
            "specific_tariffs": {
                "Китай": 4.5,
                "США": 0.0,
                "Россия": 0.0,
                "Германия": 0.0,
                "Великобритания": 0.0,
                "Австралия": 0.0,
                "Израиль": 0.0,
                "Индия": 3.0,
                "Южная Корея": 0.0,
                "Вьетнам": 1.0
            },
            "product_tariffs": {
                "electronics": 0.0,
                "cars": 0.0,
                "trucks": 0.0,
                "steel": 2.0,
                "aluminum": 2.0,
                "rare_metals": 0.0,
                "uranium": 0.0,
                "oil": 0.5,
                "gas": 0.0,
                "coal": 0.0,
                "food": 5.0,
                "chemicals": 2.0,
                "pharmaceuticals": 1.0,
                "medical_equipment": 0.0,
                "aerospace_equipment": 2.0,
                "drones": 5.0,
                "fpv_drones": 8.0,
                "tanks": 3.0,
                "fighters": 5.0,
                "missiles": 6.0,
                "small_arms": 2.0,
                "ships": 1.0
            },
            "export_tariffs": {},
            "trade_agreements": [
                "США",
                "Мексика",
                "Канада",
                "Чили",
                "Перу",
                "Австралия",
                "Новая Зеландия",
                "Сингапур",
                "Малайзия",
                "Вьетнам",
                "Таиланд",
                "Индонезия",
                "Филиппины",
                "Индия",
                "Европейский Союз",
                "Великобритания"
            ],
            "trade_wars": {},
            "embargoes": {
                "Северная Корея": ["all"],
                "Иран": ["military", "nuclear"],
                "Сирия": ["all"],
                "Россия": ["southern_kurils"]
            },
            "sanctions": {},
            "last_updated": "2022-02-23"
        },
        "Израиль": {
            "base_tariff": 4.5,
            "specific_tariffs": {
                "США": 0.0,
                "Германия": 0.0,
                "Великобритания": 0.0,
                "Китай": 3.0,
                "Индия": 2.5,
                "Турция": 1.5,
                "Россия": 1.0,
                "Украина": 0.5,
                "Япония": 0.0,
                "Франция": 0.0
            },
            "product_tariffs": {
                "agricultural_machinery": 8.0,
                "chemicals": 4.0,
                "electronics": 3.0,
                "pharmaceuticals": 2.0,
                "medical_equipment": 1.0,
                "aerospace_equipment": 3.0,
                "drones": 5.0,
                "fpv_drones": 8.0,
                "uranium": 0.0,
                "rare_metals": 2.0,
                "steel": 3.0,
                "aluminum": 3.0,
                "oil": 0.0,
                "gas": 0.0,
                "food": 5.0,
                "tanks": 4.0,
                "fighters": 6.0,
                "missiles": 7.0,
                "small_arms": 2.0,
                "ships": 1.0
            },
            "export_tariffs": {},
            "trade_agreements": [
                "США",
                "Канада",
                "Мексика",
                "Европейский Союз",
                "Великобритания",
                "Турция",
                "Иордания",
                "Египет",
                "ОАЭ",
                "Украина"
            ],
            "trade_wars": {},
            "embargoes": {
                "Иран": ["all"],
                "Сирия": ["all"],
                "Ливан": ["military"],
                "Саудовская Аравия": ["military"],
                "Ирак": ["military"]
            },
            "sanctions": {},
            "last_updated": "2022-02-23"
        },
        "Украина": {
            "base_tariff": 4.6,
            "specific_tariffs": {
                "Россия": 0.0,
                "Германия": 0.0,
                "Франция": 0.0,
                "Польша": 0.0,
                "США": 0.0,
                "Великобритания": 0.0,
                "Канада": 0.0,
                "Китай": 2.5,
                "Турция": 1.5,
                "Израиль": 0.0,
                "Беларусь": 2.5,
                "Грузия": 0.0,
                "Молдова": 0.0
            },
            "product_tariffs": {
                "agricultural_machinery": 5.0,
                "food_products": 10.0,
                "chemicals": 3.0,
                "electronics": 5.0,
                "cars": 10.0,
                "trucks": 8.0,
                "steel": 2.0,
                "aluminum": 2.0,
                "uranium": 0.0,
                "rare_metals": 2.0,
                "oil": 0.0,
                "gas": 0.0,
                "coal": 0.0,
                "food": 5.0,
                "pharmaceuticals": 2.0,
                "medical_equipment": 1.0,
                "aerospace_equipment": 4.0,
                "drones": 5.0,
                "fpv_drones": 8.0,
                "tanks": 3.0,
                "fighters": 5.0,
                "missiles": 5.0,
                "small_arms": 2.0,
                "ships": 1.0
            },
            "export_tariffs": {
                "food_products": 10.0,
                "steel": 3.0,
                "uranium": 5.0,
                "tanks": 5.0,
                "missiles": 5.0,
                "small_arms": 2.0
            },
            "trade_agreements": [
                "Грузия",
                "Молдова",
                "Азербайджан",
                "Казахстан",
                "Канада",
                "Израиль",
                "Турция",
                "Польша",
                "Литва",
                "Латвия",
                "Эстония"
            ],
            "trade_wars": {},
            "embargoes": {
                "Россия": ["military"],
                "Северная Корея": ["all"],
                "Сирия": ["all"]
            },
            "sanctions": {},
            "last_updated": "2022-02-23"
        },
        "Иран": {
            "base_tariff": 12.0,
            "specific_tariffs": {
                "Россия": 0.0,
                "Китай": 0.0,
                "Индия": 2.0,
                "Турция": 1.5,
                "Пакистан": 2.0,
                "Ирак": 0.5,
                "Сирия": 0.0,
                "Венесуэла": 0.0,
                "США": 0.0,
                "Германия": 5.0,
                "Великобритания": 5.0,
                "Франция": 5.0,
                "Япония": 5.0,
                "Израиль": 0.0
            },
            "product_tariffs": {
                "cars": 40.0,
                "trucks": 30.0,
                "electronics": 25.0,
                "pharmaceuticals": 5.0,
                "medical_equipment": 4.0,
                "food_products": 15.0,
                "agricultural_machinery": 20.0,
                "steel": 10.0,
                "aluminum": 10.0,
                "uranium": 0.0,
                "oil": 0.0,
                "gas": 0.0,
                "coal": 5.0,
                "food": 10.0,
                "chemicals": 8.0,
                "aerospace_equipment": 15.0,
                "drones": 10.0,
                "fpv_drones": 15.0,
                "tanks": 5.0,
                "fighters": 7.0,
                "missiles": 5.0,
                "small_arms": 3.0,
                "ships": 2.0
            },
            "export_tariffs": {
                "oil": 50.0,
                "gas": 30.0,
                "uranium": 100.0,
                "missiles": 15.0,
                "drones": 10.0,
                "fpv_drones": 15.0
            },
            "trade_agreements": [
                "Россия",
                "Китай",
                "Индия",
                "Пакистан",
                "Турция",
                "Ирак",
                "Сирия",
                "Венесуэла",
                "Армения",
                "Азербайджан"
            ],
            "trade_wars": {},
            "embargoes": {
                "США": ["military", "nuclear"],
                "Израиль": ["all"],
                "Саудовская Аравия": ["all"],
                "ОАЭ": ["all"],
                "Бахрейн": ["all"],
                "Кувейт": ["all"],
                "Катар": ["all"],
                "Канада": ["military"],
                "Великобритания": ["military"],
                "Германия": ["military"],
                "Франция": ["military"],
                "Япония": ["military"]
            },
            "sanctions": {
                "США": {
                    "penalty": 50,
                    "reason": "Американские санкции против Ирана",
                    "date": "2022-02-23"
                },
                "Израиль": {
                    "penalty": 100,
                    "reason": "Враждебные отношения",
                    "date": "2022-02-23"
                },
                "Европейский Союз": {
                    "penalty": 40,
                    "reason": "Санкции ЕС против Ирана",
                    "date": "2022-02-23"
                }
            },
            "last_updated": "2022-02-23"
        }
    }
}

# ==================== ОРИГИНАЛЬНЫЕ ДАННЫЕ ДЛЯ ЦЕНТРОБАНКА ====================

ORIGINAL_CENTRAL_BANK = {
    "banks": {}
}

# Инициализация данных центробанка для каждой страны
for country_name in ["США", "Россия", "Китай", "Германия", "Великобритания", 
                     "Франция", "Япония", "Израиль", "Украина", "Иран"]:
    ORIGINAL_CENTRAL_BANK["banks"][country_name] = {
        "interest_rate": BASE_INTEREST_RATES.get(country_name, 5.0),
        "gold_reserves": BASE_GOLD_RESERVES.get(country_name, 100.0),
        "inflation_forecast": TARGET_INFLATION.get(country_name, 2.0),
        "gdp_forecast": 2.0,
        "debt_forecast": 0.0,
        "budget_forecast": 0.0,
        "last_updated": str(datetime.now()),
        "history": []
    }

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

# ==================== ОРИГИНАЛЬНЫЕ ДАННЫЕ СПУТНИКОВ ====================

STARTING_SATELLITES = {
    "США": {
        "military": 187,
        "civilian": 293,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 480
            }
        ],
        "last_maintenance": str(datetime.now())
    },
    "Россия": {
        "military": 112,
        "civilian": 85,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 197
            }
        ],
        "last_maintenance": str(datetime.now())
    },
    "Китай": {
        "military": 156,
        "civilian": 214,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 370
            }
        ],
        "last_maintenance": str(datetime.now())
    },
    "Германия": {
        "military": 8,
        "civilian": 47,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 55
            }
        ],
        "last_maintenance": str(datetime.now())
    },
    "Великобритания": {
        "military": 7,
        "civilian": 43,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 50
            }
        ],
        "last_maintenance": str(datetime.now())
    },
    "Франция": {
        "military": 12,
        "civilian": 38,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 50
            }
        ],
        "last_maintenance": str(datetime.now())
    },
    "Япония": {
        "military": 9,
        "civilian": 78,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 87
            }
        ],
        "last_maintenance": str(datetime.now())
    },
    "Израиль": {
        "military": 14,
        "civilian": 8,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 22
            }
        ],
        "last_maintenance": str(datetime.now())
    },
    "Украина": {
        "military": 0,
        "civilian": 1,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 1
            }
        ],
        "last_maintenance": str(datetime.now())
    },
    "Иран": {
        "military": 3,
        "civilian": 2,
        "launch_history": [
            {
                "type": "initial",
                "date": "2022-12-01",
                "game_date": "2022-12-01",
                "count": 5
            }
        ],
        "last_maintenance": str(datetime.now())
    }
}

# ==================== ОРИГИНАЛЬНЫЕ ДАННЫЕ ДЛЯ ИГРОВОГО ВРЕМЕНИ ====================

START_GAME_TIME = {
    "last_real_update": str(datetime.now()),
    "game_date": "2022-12-01",
    "total_game_days": 0,
    "total_real_seconds": 0
}

# ==================== ОРИГИНАЛЬНЫЕ ДАННЫЕ ДЛЯ МОБИЛИЗАЦИИ ====================

EMPTY_MOBILIZATION = {
    "active_programs": [],
    "completed_programs": []
}

# ==================== ОРИГИНАЛЬНЫЕ ДАННЫЕ ДЛЯ ВОЕННЫХ ДОКТРИН ====================

EMPTY_DOCTRINES = {
    "researching": [],
    "completed": []
}

# ==================== ОРИГИНАЛЬНЫЕ ДАННЫЕ ДЛЯ РАЗВЕДКИ ====================

EMPTY_ESPIONAGE = {
    "active_operations": [],
    "completed_operations": [],
    "counterintelligence": {},
    "detected_attempts": []
}

# ==================== ОРИГИНАЛЬНЫЕ ДАННЫЕ ИЗ STATES.JSON ====================

ORIGINAL_STATES = {
    "1000000000000000001": {
        "state": {
            "population": 331000000,
            "territory": 9834000,
            "statename": "США",
            "government_type": "Федеративная президентская республика",
            "happiness": 71,
            "stability": 85,
            "trust": 65,
            "army_size": 1400000,
            "readiness": 92,
            "demographics": {
                "birth_rate": 11.9,
                "death_rate": 8.3,
                "age_structure": {
                    "0_14": 0.18,
                    "15_64": 0.65,
                    "65_plus": 0.17
                },
                "education_level": {
                    "higher_education": 0.42,
                    "secondary_education": 0.28,
                    "primary_education": 0.25,
                    "no_education": 0.05
                },
                "professions": {
                    "industrial_workers": 35000000,
                    "construction_workers": 12000000,
                    "agricultural_workers": 5000000,
                    "transport_workers": 10000000,
                    "service_workers": 55000000,
                    "retail_workers": 25000000,
                    "it_professionals": 6000000,
                    "engineers": 4500000,
                    "scientists": 2200000,
                    "medical_staff": 8000000,
                    "teachers": 6000000,
                    "military": 1400000,
                    "government": 10000000,
                    "officials": 8000000
                }
            },
            "quality_of_life": {
                "healthcare_index": 75,
                "education_index": 80,
                "safety_index": 60,
                "environment_index": 65,
                "infrastructure_index": 82,
                "purchasing_power_index": 85
            },
            "business_sector": {
                "small_businesses": 8000000,
                "startups": 250000,
                "self_employed": 15000000,
                "business_density": 45,
                "entrepreneurship_rate": 12
            }
        },
        "politics": {
            "ruling_party": "Демократическая партия",
            "ideology": "Либеральная демократия",
            "popularity": 52,
            "parliament": {
                "senate": 50,
                "house": 220
            },
            "un_rating": 88,
            "diplomatic_status": "Сверхдержава",
            "political_power": 100.0
        },
        "social_policies": {
            "образование": "высокоразвитая система",
            "здравоохранение": "частно‑государственная система",
            "пенсии": "смешанная система",
            "пособия": "адресная поддержка"
        },
        "active_reforms": [
            "Цифровая трансформация",
            "Зелёная энергетика"
        ],
        "government_efficiency": 78,
        "economy": {
            "budget": 6500000000000,
            "gdp": 27360000000000,
            "tax_rate": 24.5,
            "debt": 34000000000000,
            "inflation": 3.2,
            "wage": 65000,
            "cost_of_living": 100,
            "military_budget": 886000000000,
            "taxes": {
                "income": {
                    "rate": 22.0,
                    "progressive": True,
                    "brackets": [
                        {"up_to": 15000, "rate": 10},
                        {"up_to": 50000, "rate": 15},
                        {"up_to": 100000, "rate": 22},
                        {"up_to": 250000, "rate": 28},
                        {"up_to": 500000, "rate": 33},
                        {"above": 500000, "rate": 40}
                    ]
                },
                "corporate": {
                    "rate": 21.0,
                    "small_business_rate": 15.0,
                    "small_business_threshold": 5000000
                },
                "vat": {
                    "rate": 0.0,
                    "reduced_rate": 0.0,
                    "reduced_categories": []
                },
                "property": {
                    "rate": 1.2,
                    "base_value": 100000
                },
                "luxury": {
                    "rate": 0.0,
                    "threshold": 0
                },
                "social_security": {
                    "employee_rate": 7.65,
                    "employer_rate": 7.65
                },
                "environmental": {
                    "co2_rate": 25.0,
                    "pollution_rate": 50.0
                }
            }
        },
        "expenses": {
            "healthcare": 1500000000000,
            "police": 35000000000,
            "social_security": 2800000000000,
            "education": 120000000000
        },
        "resources": {
            "oil": 500,
            "gas": 800,
            "coal": 400,
            "uranium": 30,
            "steel": 400,
            "aluminum": 200,
            "electronics": 300,
            "rare_metals": 50,
            "food": 600
        },
        "civil_goods": {
            "cars": 5000,
            "trucks": 800,
            "buses": 200,
            "agricultural_machinery": 400,
            "construction_machinery": 300,
            "industrial_equipment": 600,
            "machine_tools": 400,
            "industrial_robots": 150,
            "energy_equipment": 200,
            "electrical_equipment": 800,
            "telecom_equipment": 900,
            "tech_equipment": 700,
            "aerospace_equipment": 50,
            "auto_parts": 3000,
            "clothing": 20000,
            "medical_supplies": 5000,
            "medical_equipment": 300,
            "sanitary_products": 8000,
            "drones": 200,
            "fpv_drones": 500,
            "consumer_electronics": 6000,
            "food_products": 30000,
            "beverages": 25000,
            "chemicals": 1500,
            "pharmaceuticals": 800,
            "furniture": 7000,
            "household_goods": 12000
        },
        "army": {
            "ground": {
                "tanks": 6100,
                "btr": 18000,
                "bmp": 12500,
                "armored_vehicles": 15000,
                "trucks": 45000,
                "cars": 32000,
                "ew_vehicles": 800,
                "engineering_equipment": 6000,
                "radar_systems": 1200,
                "self_propelled_artillery": 2100,
                "towed_artillery": 1800,
                "mlrs": 950,
                "atgm_complexes": 2500,
                "otr_complexes": 120,
                "zas": 850,
                "zdprk": 600,
                "short_range_air_defense": 1500,
                "long_range_air_defense": 420
            },
            "equipment": {
                "small_arms": 1200000,
                "grenade_launchers": 85000,
                "atgms": 18000,
                "manpads": 15000,
                "medical_equipment": 200000,
                "engineering_equipment_units": 45000,
                "fpv_drones": 50000
            },
            "air": {
                "fighters": 2100,
                "attack_aircraft": 450,
                "bombers": 160,
                "transport_aircraft": 380,
                "attack_helicopters": 1200,
                "transport_helicopters": 850,
                "recon_uav": 600,
                "attack_uav": 450,
                "kamikaze_drones": 500
            },
            "navy": {
                "boats": 250,
                "corvettes": 35,
                "destroyers": 68,
                "cruisers": 22,
                "aircraft_carriers": 11,
                "submarines": 69
            },
            "missiles": {
                "strategic_nuclear": 1550,
                "tactical_nuclear": 500,
                "cruise_missiles": 2500,
                "hypersonic_missiles": 180,
                "ballistic_missiles": 900
            }
        },
        "population_data": {
            "savings": 5500000000000,
            "last_update": str(datetime.now())
        }
    },
    "1000000000000000002": {
        "state": {
            "population": 133517000,
            "territory": 17100000,
            "statename": "Россия",
            "government_type": "Смешанная республика",
            "happiness": 67.6,
            "stability": 82,
            "trust": 70,
            "army_size": 900000,
            "readiness": 88,
            "demographics": {
                "birth_rate": 9.6,
                "death_rate": 13.4,
                "age_structure": {
                    "0_14": 0.17,
                    "15_64": 0.67,
                    "65_plus": 0.16
                },
                "education_level": {
                    "higher_education": 0.35,
                    "secondary_education": 0.45,
                    "primary_education": 0.15,
                    "no_education": 0.05
                },
                "professions": {
                    "industrial_workers": 15000000,
                    "construction_workers": 5000000,
                    "agricultural_workers": 8000000,
                    "transport_workers": 4000000,
                    "service_workers": 25000000,
                    "retail_workers": 12000000,
                    "it_professionals": 1500000,
                    "engineers": 1800000,
                    "scientists": 800000,
                    "medical_staff": 2000000,
                    "teachers": 1500000,
                    "military": 900000,
                    "government": 2000000,
                    "officials": 1500000
                }
            },
            "quality_of_life": {
                "healthcare_index": 65,
                "education_index": 70,
                "safety_index": 55,
                "environment_index": 45,
                "infrastructure_index": 68,
                "purchasing_power_index": 45
            },
            "business_sector": {
                "small_businesses": 2000000,
                "startups": 50000,
                "self_employed": 5000000,
                "business_density": 15,
                "entrepreneurship_rate": 8
            },
            "army_experience": 96
        },
        "politics": {
            "ruling_party": "Единая Россия",
            "ideology": "Консерватизм",
            "popularity": 68.3,
            "parliament": {
                "duma": 320,
                "federation_council": 170
            },
            "un_rating": 75,
            "diplomatic_status": "Региональная держава",
            "political_power": 100.0
        },
        "social_policies": {
            "образование": "государственная система",
            "здравоохранение": "бюджетная система",
            "пенсии": "распределительная система",
            "пособия": "социальные выплаты"
        },
        "active_reforms": [
            "Импортозамещение",
            "Цифровая экономика"
        ],
        "government_efficiency": 65,
        "economy": {
            "budget": 349720000000.0,
            "gdp": 1907151000000,
            "tax_rate": 13,
            "debt": 274420000000.0,
            "inflation": 8.34,
            "wage": 729126,
            "cost_of_living": 60,
            "military_budget": 109000000000,
            "taxes": {
                "income": {
                    "rate": 13.0,
                    "progressive": False,
                    "brackets": []
                },
                "corporate": {
                    "rate": 20.0,
                    "small_business_rate": 15.0,
                    "small_business_threshold": 5000000
                },
                "vat": {
                    "rate": 20.0,
                    "reduced_rate": 10.0,
                    "reduced_categories": ["food", "medicine", "baby_products"]
                },
                "property": {
                    "rate": 2.0,
                    "base_value": 100000
                },
                "luxury": {
                    "rate": 15.0,
                    "threshold": 10000000
                },
                "social_security": {
                    "employee_rate": 13.0,
                    "employer_rate": 30.0
                },
                "environmental": {
                    "co2_rate": 30.0,
                    "pollution_rate": 60.0
                }
            }
        },
        "expenses": {
            "healthcare": 40000000000,
            "police": 15000000000,
            "social_security": 150000000000,
            "education": 25000000000
        },
        "resources": {
            "oil": 800,
            "gas": 1000,
            "coal": 350,
            "uranium": 40,
            "steel": 350,
            "aluminum": 150,
            "electronics": 100,
            "rare_metals": 60,
            "food": 400
        },
        "civil_goods": {
            "cars": 2500,
            "trucks": 500,
            "buses": 150,
            "agricultural_machinery": 350,
            "construction_machinery": 250,
            "industrial_equipment": 450,
            "machine_tools": 300,
            "industrial_robots": 80,
            "energy_equipment": 180,
            "electrical_equipment": 600,
            "telecom_equipment": 400,
            "tech_equipment": 350,
            "aerospace_equipment": 40,
            "auto_parts": 2000,
            "clothing": 15000,
            "medical_supplies": 3000,
            "medical_equipment": 200,
            "sanitary_products": 6000,
            "drones": 300,
            "fpv_drones": 400,
            "consumer_electronics": 2500,
            "food_products": 25000,
            "beverages": 18000,
            "chemicals": 1200,
            "pharmaceuticals": 600,
            "furniture": 5000,
            "household_goods": 8000
        },
        "army": {
            "ground": {
                "tanks": 12500,
                "btr": 15000,
                "bmp": 11000,
                "armored_vehicles": 10000,
                "trucks": 30000,
                "cars": 25000,
                "ew_vehicles": 600,
                "engineering_equipment": 5000,
                "radar_systems": 1000,
                "self_propelled_artillery": 1800,
                "towed_artillery": 1500,
                "mlrs": 800,
                "atgm_complexes": 2200,
                "otr_complexes": 100,
                "zas": 700,
                "zdprk": 550,
                "short_range_air_defense": 1200,
                "long_range_air_defense": 380
            },
            "equipment": {
                "small_arms": 950000,
                "grenade_launchers": 70000,
                "atgms": 16000,
                "manpads": 12000,
                "medical_equipment": 180000,
                "engineering_equipment_units": 40000,
                "fpv_drones": 100000
            },
            "air": {
                "fighters": 1800,
                "attack_aircraft": 400,
                "bombers": 140,
                "transport_aircraft": 350,
                "attack_helicopters": 1000,
                "transport_helicopters": 800,
                "recon_uav": 500,
                "attack_uav": 400,
                "kamikaze_drones": 2000
            },
            "navy": {
                "boats": 200,
                "corvettes": 30,
                "destroyers": 60,
                "cruisers": 15,
                "aircraft_carriers": 1,
                "submarines": 62
            },
            "missiles": {
                "strategic_nuclear": 1600,
                "tactical_nuclear": 600,
                "cruise_missiles": 2200,
                "hypersonic_missiles": 150,
                "ballistic_missiles": 850
            }
        },
        "population_data": {
            "savings": 1500000000000,
            "last_update": str(datetime.now())
        }
    },
    "1000000000000000003": {
        "state": {
            "population": 1412000000,
            "territory": 9597000,
            "statename": "Китай",
            "government_type": "Социалистическая республика",
            "happiness": 73,
            "stability": 90,
            "trust": 85,
            "army_size": 2035000,
            "readiness": 87,
            "demographics": {
                "birth_rate": 6.77,
                "death_rate": 7.37,
                "age_structure": {
                    "0_14": 0.17,
                    "15_64": 0.70,
                    "65_plus": 0.13
                },
                "education_level": {
                    "higher_education": 0.25,
                    "secondary_education": 0.45,
                    "primary_education": 0.25,
                    "no_education": 0.05
                },
                "professions": {
                    "industrial_workers": 200000000,
                    "construction_workers": 60000000,
                    "agricultural_workers": 150000000,
                    "transport_workers": 40000000,
                    "service_workers": 200000000,
                    "retail_workers": 80000000,
                    "it_professionals": 10000000,
                    "engineers": 15000000,
                    "scientists": 5000000,
                    "medical_staff": 15000000,
                    "teachers": 12000000,
                    "military": 2035000,
                    "government": 30000000,
                    "officials": 25000000
                }
            },
            "quality_of_life": {
                "healthcare_index": 68,
                "education_index": 72,
                "safety_index": 75,
                "environment_index": 55,
                "infrastructure_index": 78,
                "purchasing_power_index": 60
            },
            "business_sector": {
                "small_businesses": 30000000,
                "startups": 500000,
                "self_employed": 80000000,
                "business_density": 35,
                "entrepreneurship_rate": 15
            }
        },
        "politics": {
            "ruling_party": "Коммунистическая партия Китая",
            "ideology": "Социализм с китайской спецификой",
            "popularity": 88,
            "parliament": {
                "national_people_congress": 2980,
                "standing_committee": 175
            },
            "un_rating": 85,
            "diplomatic_status": "Сверхдержава",
            "political_power": 100.0
        },
        "social_policies": {
            "образование": "государственно‑частная система",
            "здравоохранение": "смешанная система",
            "пенсии": "накопительная система",
            "пособия": "адресная поддержка"
        },
        "active_reforms": [
            "Цифровой шёлковый путь",
            "Зелёная энергетика"
        ],
        "government_efficiency": 82,
        "economy": {
            "budget": 4100000000000,
            "gdp": 17700000000000,
            "tax_rate": 25,
            "debt": 13000000000000,
            "inflation": 2.8,
            "wage": 105000,
            "cost_of_living": 45,
            "military_budget": 293000000000,
            "taxes": {
                "income": {
                    "rate": 45.0,
                    "progressive": False,
                    "brackets": []
                },
                "corporate": {
                    "rate": 25.0,
                    "small_business_rate": 20.0,
                    "small_business_threshold": 5000000
                },
                "vat": {
                    "rate": 13.0,
                    "reduced_rate": 6.0,
                    "reduced_categories": ["food", "medicine", "education"]
                },
                "property": {
                    "rate": 1.2,
                    "base_value": 50000
                },
                "luxury": {
                    "rate": 20.0,
                    "threshold": 5000000
                },
                "social_security": {
                    "employee_rate": 8.0,
                    "employer_rate": 20.0
                },
                "environmental": {
                    "co2_rate": 40.0,
                    "pollution_rate": 80.0
                }
            }
        },
        "expenses": {
            "healthcare": 900000000000,
            "police": 150000000000,
            "social_security": 1200000000000,
            "education": 800000000000
        },
        "resources": {
            "oil": 300,
            "gas": 200,
            "coal": 600,
            "uranium": 25,
            "steel": 600,
            "aluminum": 300,
            "electronics": 500,
            "rare_metals": 40,
            "food": 800
        },
        "civil_goods": {
            "cars": 8000,
            "trucks": 1200,
            "buses": 500,
            "agricultural_machinery": 600,
            "construction_machinery": 500,
            "industrial_equipment": 900,
            "machine_tools": 700,
            "industrial_robots": 300,
            "energy_equipment": 350,
            "electrical_equipment": 1500,
            "telecom_equipment": 2000,
            "tech_equipment": 1800,
            "aerospace_equipment": 60,
            "auto_parts": 5000,
            "clothing": 50000,
            "medical_supplies": 6000,
            "medical_equipment": 400,
            "sanitary_products": 15000,
            "drones": 500,
            "fpv_drones": 800,
            "consumer_electronics": 20000,
            "food_products": 60000,
            "beverages": 40000,
            "chemicals": 2500,
            "pharmaceuticals": 1200,
            "furniture": 20000,
            "household_goods": 35000
        },
        "army": {
            "ground": {
                "tanks": 5800,
                "btr": 16000,
                "bmp": 13000,
                "armored_vehicles": 12000,
                "trucks": 35000,
                "cars": 28000,
                "ew_vehicles": 750,
                "engineering_equipment": 5500,
                "radar_systems": 1100,
                "self_propelled_artillery": 2000,
                "towed_artillery": 1700,
                "mlrs": 850,
                "atgm_complexes": 2400,
                "otr_complexes": 110,
                "zas": 780,
                "zdprk": 600,
                "short_range_air_defense": 1400,
                "long_range_air_defense": 400
            },
            "equipment": {
                "small_arms": 1100000,
                "grenade_launchers": 80000,
                "atgms": 17000,
                "manpads": 14000,
                "medical_equipment": 190000,
                "engineering_equipment_units": 42000,
                "fpv_drones": 80000
            },
            "air": {
                "fighters": 1500,
                "attack_aircraft": 350,
                "bombers": 200,
                "transport_aircraft": 320,
                "attack_helicopters": 950,
                "transport_helicopters": 750,
                "recon_uav": 550,
                "attack_uav": 420,
                "kamikaze_drones": 200
            },
            "navy": {
                "boats": 220,
                "corvettes": 40,
                "destroyers": 52,
                "cruisers": 18,
                "aircraft_carriers": 3,
                "submarines": 78
            },
            "missiles": {
                "strategic_nuclear": 350,
                "tactical_nuclear": 400,
                "cruise_missiles": 2300,
                "hypersonic_missiles": 160,
                "ballistic_missiles": 920
            }
        },
        "population_data": {
            "savings": 15000000000000,
            "last_update": str(datetime.now())
        }
    },
    "1000000000000000004": {
        "state": {
            "population": 76244480,
            "territory": 357022,
            "statename": "Германия",
            "government_type": "Федеративная парламентская республика",
            "happiness": 78.6,
            "stability": 92,
            "trust": 75,
            "army_size": 183000,
            "readiness": 85,
            "demographics": {
                "birth_rate": 9.4,
                "death_rate": 11.8,
                "age_structure": {
                    "0_14": 0.14,
                    "15_64": 0.65,
                    "65_plus": 0.21
                },
                "education_level": {
                    "higher_education": 0.38,
                    "secondary_education": 0.42,
                    "primary_education": 0.15,
                    "no_education": 0.05
                },
                "professions": {
                    "industrial_workers": 12000000,
                    "construction_workers": 3000000,
                    "agricultural_workers": 1000000,
                    "transport_workers": 3000000,
                    "service_workers": 18000000,
                    "retail_workers": 7000000,
                    "it_professionals": 2000000,
                    "engineers": 2500000,
                    "scientists": 800000,
                    "medical_staff": 3000000,
                    "teachers": 2000000,
                    "military": 183000,
                    "government": 4000000,
                    "officials": 2500000
                }
            },
            "quality_of_life": {
                "healthcare_index": 82,
                "education_index": 80,
                "safety_index": 78,
                "environment_index": 75,
                "infrastructure_index": 88,
                "purchasing_power_index": 75
            },
            "business_sector": {
                "small_businesses": 2500000,
                "startups": 100000,
                "self_employed": 4000000,
                "business_density": 35,
                "entrepreneurship_rate": 10
            },
            "army_experience": 83
        },
        "politics": {
            "ruling_party": "Коалиция (СДПГ, Зелёные, СвДП)",
            "ideology": "Социально‑рыночная экономика",
            "popularity": 65.3,
            "parliament": {
                "bundestag": 736,
                "bundesrat": 69
            },
            "un_rating": 87,
            "diplomatic_status": "Региональная держава",
            "political_power": 100.0
        },
        "social_policies": {
            "образование": "бесплатная система",
            "здравоохранение": "страховая система",
            "пенсии": "распределительно‑накопительная система",
            "пособия": "социальное обеспечение"
        },
        "active_reforms": [
            "Энергетический переход",
            "Цифровизация промышленности"
        ],
        "government_efficiency": 80,
        "economy": {
            "budget": 1876100000000.0,
            "gdp": 4428140000000,
            "tax_rate": 40.8,
            "debt": 2487100000000.0,
            "inflation": 7.89,
            "wage": 45670,
            "cost_of_living": 110,
            "military_budget": 56000000000,
            "taxes": {
                "income": {
                    "rate": 42.0,
                    "progressive": True,
                    "brackets": [
                        {"up_to": 10000, "rate": 0},
                        {"up_to": 30000, "rate": 18},
                        {"up_to": 60000, "rate": 30},
                        {"up_to": 100000, "rate": 40},
                        {"up_to": 250000, "rate": 45},
                        {"above": 250000, "rate": 47}
                    ]
                },
                "corporate": {
                    "rate": 30.0,
                    "small_business_rate": 25.0,
                    "small_business_threshold": 5000000
                },
                "vat": {
                    "rate": 19.0,
                    "reduced_rate": 7.0,
                    "reduced_categories": ["food", "books", "public_transport"]
                },
                "property": {
                    "rate": 2.5,
                    "base_value": 100000
                },
                "luxury": {
                    "rate": 0.0,
                    "threshold": 0
                },
                "social_security": {
                    "employee_rate": 20.0,
                    "employer_rate": 20.0
                },
                "environmental": {
                    "co2_rate": 55.0,
                    "pollution_rate": 100.0
                }
            }
        },
        "expenses": {
            "healthcare": 300000000000,
            "police": 25000000000,
            "social_security": 650000000000,
            "education": 130000000000
        },
        "resources": {
            "oil": 50,
            "gas": 30,
            "coal": 250,
            "uranium": 5,
            "steel": 250,
            "aluminum": 100,
            "electronics": 300,
            "rare_metals": 20,
            "food": 200
        },
        "civil_goods": {
            "cars": 4000,
            "trucks": 400,
            "buses": 150,
            "agricultural_machinery": 300,
            "construction_machinery": 200,
            "industrial_equipment": 550,
            "machine_tools": 450,
            "industrial_robots": 200,
            "energy_equipment": 220,
            "electrical_equipment": 700,
            "telecom_equipment": 600,
            "tech_equipment": 550,
            "aerospace_equipment": 30,
            "auto_parts": 2500,
            "clothing": 12000,
            "medical_supplies": 3500,
            "medical_equipment": 280,
            "sanitary_products": 7000,
            "drones": 150,
            "fpv_drones": 200,
            "consumer_electronics": 4000,
            "food_products": 20000,
            "beverages": 18000,
            "chemicals": 1000,
            "pharmaceuticals": 700,
            "furniture": 6000,
            "household_goods": 9000
        },
        "army": {
            "ground": {
                "tanks": 320,
                "btr": 7000,
                "bmp": 5500,
                "armored_vehicles": 6000,
                "trucks": 15000,
                "cars": 12000,
                "ew_vehicles": 300,
                "engineering_equipment": 2500,
                "radar_systems": 600,
                "self_propelled_artillery": 400,
                "towed_artillery": 200,
                "mlrs": 150,
                "atgm_complexes": 1200,
                "otr_complexes": 50,
                "zas": 400,
                "zdprk": 350,
                "short_range_air_defense": 800,
                "long_range_air_defense": 250
            },
            "equipment": {
                "small_arms": 250000,
                "grenade_launchers": 20000,
                "atgms": 8000,
                "manpads": 6000,
                "medical_equipment": 85000,
                "engineering_equipment_units": 22000,
                "fpv_drones": 15000
            },
            "air": {
                "fighters": 140,
                "attack_aircraft": 80,
                "bombers": 0,
                "transport_aircraft": 100,
                "attack_helicopters": 120,
                "transport_helicopters": 200,
                "recon_uav": 200,
                "attack_uav": 150,
                "kamikaze_drones": 100
            },
            "navy": {
                "boats": 80,
                "corvettes": 5,
                "destroyers": 0,
                "cruisers": 0,
                "aircraft_carriers": 0,
                "submarines": 6
            },
            "missiles": {
                "strategic_nuclear": 0,
                "tactical_nuclear": 20,
                "cruise_missiles": 500,
                "hypersonic_missiles": 0,
                "ballistic_missiles": 300
            }
        },
        "population_data": {
            "savings": 2500000000000,
            "last_update": str(datetime.now())
        }
    },
    "1000000000000000005": {
        "state": {
            "population": 9800000,
            "territory": 22072,
            "statename": "Израиль",
            "government_type": "Парламентская демократия",
            "happiness": 74,
            "stability": 88,
            "trust": 72,
            "army_size": 169500,
            "readiness": 95,
            "demographics": {
                "birth_rate": 18.9,
                "death_rate": 5.2,
                "age_structure": {
                    "0_14": 0.27,
                    "15_64": 0.60,
                    "65_plus": 0.13
                },
                "education_level": {
                    "higher_education": 0.45,
                    "secondary_education": 0.35,
                    "primary_education": 0.15,
                    "no_education": 0.05
                },
                "professions": {
                    "industrial_workers": 800000,
                    "construction_workers": 200000,
                    "agricultural_workers": 50000,
                    "transport_workers": 150000,
                    "service_workers": 1500000,
                    "retail_workers": 500000,
                    "it_professionals": 250000,
                    "engineers": 200000,
                    "scientists": 120000,
                    "medical_staff": 200000,
                    "teachers": 150000,
                    "military": 169500,
                    "government": 300000,
                    "officials": 200000
                }
            },
            "quality_of_life": {
                "healthcare_index": 78,
                "education_index": 75,
                "safety_index": 65,
                "environment_index": 70,
                "infrastructure_index": 80,
                "purchasing_power_index": 70
            },
            "business_sector": {
                "small_businesses": 300000,
                "startups": 15000,
                "self_employed": 400000,
                "business_density": 40,
                "entrepreneurship_rate": 12
            }
        },
        "politics": {
            "ruling_party": "Коалиционное правительство",
            "ideology": "Сионизм, либеральная демократия",
            "popularity": 62,
            "parliament": {
                "knesset": 120
            },
            "un_rating": 68,
            "diplomatic_status": "Региональная держава",
            "political_power": 100.0
        },
        "social_policies": {
            "образование": "государственная система с религиозными школами",
            "здравоохранение": "обязательное медицинское страхование",
            "пенсии": "накопительная система",
            "пособия": "социальные выплаты и льготы репатриантам"
        },
        "active_reforms": [
            "Развитие кибербезопасности",
            "Водные технологии"
        ],
        "government_efficiency": 78,
        "economy": {
            "budget": 170000000000,
            "gdp": 520000000000,
            "tax_rate": 31.7,
            "debt": 210000000000,
            "inflation": 4.3,
            "wage": 38000,
            "cost_of_living": 115,
            "military_budget": 23400000000,
            "taxes": {
                "income": {
                    "rate": 31.7,
                    "progressive": True,
                    "brackets": [
                        {"up_to": 25000, "rate": 10},
                        {"up_to": 50000, "rate": 20},
                        {"up_to": 100000, "rate": 30},
                        {"up_to": 200000, "rate": 35},
                        {"above": 200000, "rate": 47}
                    ]
                },
                "corporate": {
                    "rate": 23.0,
                    "small_business_rate": 18.0,
                    "small_business_threshold": 5000000
                },
                "vat": {
                    "rate": 17.0,
                    "reduced_rate": 8.5,
                    "reduced_categories": ["food", "medicine"]
                },
                "property": {
                    "rate": 2.5,
                    "base_value": 100000
                },
                "luxury": {
                    "rate": 30.0,
                    "threshold": 5000000
                },
                "social_security": {
                    "employee_rate": 12.0,
                    "employer_rate": 15.0
                },
                "environmental": {
                    "co2_rate": 35.0,
                    "pollution_rate": 70.0
                }
            }
        },
        "expenses": {
            "healthcare": 15000000000,
            "police": 2000000000,
            "social_security": 20000000000,
            "education": 12000000000
        },
        "resources": {
            "oil": 10,
            "gas": 20,
            "coal": 50,
            "uranium": 0,
            "steel": 50,
            "aluminum": 30,
            "electronics": 200,
            "rare_metals": 10,
            "food": 50
        },
        "civil_goods": {
            "cars": 800,
            "trucks": 100,
            "buses": 30,
            "agricultural_machinery": 150,
            "construction_machinery": 80,
            "industrial_equipment": 200,
            "machine_tools": 120,
            "industrial_robots": 100,
            "energy_equipment": 60,
            "electrical_equipment": 300,
            "telecom_equipment": 500,
            "tech_equipment": 450,
            "aerospace_equipment": 20,
            "auto_parts": 600,
            "clothing": 2000,
            "medical_supplies": 1500,
            "medical_equipment": 180,
            "sanitary_products": 2500,
            "drones": 250,
            "fpv_drones": 300,
            "consumer_electronics": 1800,
            "food_products": 3000,
            "beverages": 2500,
            "chemicals": 300,
            "pharmaceuticals": 400,
            "furniture": 1500,
            "household_goods": 2000
        },
        "army": {
            "ground": {
                "tanks": 2400,
                "btr": 8000,
                "bmp": 4500,
                "armored_vehicles": 7000,
                "trucks": 12000,
                "cars": 9000,
                "ew_vehicles": 400,
                "engineering_equipment": 3000,
                "radar_systems": 750,
                "self_propelled_artillery": 650,
                "towed_artillery": 350,
                "mlrs": 200,
                "atgm_complexes": 1800,
                "otr_complexes": 80,
                "zas": 500,
                "zdprk": 400,
                "short_range_air_defense": 900,
                "long_range_air_defense": 320
            },
            "equipment": {
                "small_arms": 300000,
                "grenade_launchers": 25000,
                "atgms": 10000,
                "manpads": 8000,
                "medical_equipment": 95000,
                "engineering_equipment_units": 28000,
                "fpv_drones": 30000
            },
            "air": {
                "fighters": 250,
                "attack_aircraft": 120,
                "bombers": 0,
                "transport_aircraft": 80,
                "attack_helicopters": 150,
                "transport_helicopters": 220,
                "recon_uav": 300,
                "attack_uav": 200,
                "kamikaze_drones": 500
            },
            "navy": {
                "boats": 60,
                "corvettes": 8,
                "destroyers": 0,
                "cruisers": 0,
                "aircraft_carriers": 0,
                "submarines": 5
            },
            "missiles": {
                "strategic_nuclear": 80,
                "tactical_nuclear": 150,
                "cruise_missiles": 800,
                "hypersonic_missiles": 50,
                "ballistic_missiles": 600
            }
        },
        "population_data": {
            "savings": 500000000000,
            "last_update": str(datetime.now())
        }
    },
    "1000000000000000006": {
        "state": {
            "population": 37810620,
            "territory": 603550,
            "statename": "Украина",
            "government_type": "Парламентсько-президентська республіка",
            "happiness": 64.92,
            "stability": 85,
            "trust": 58,
            "army_size": 255000,
            "readiness": 80,
            "demographics": {
                "birth_rate": 8.1,
                "death_rate": 14.5,
                "age_structure": {
                    "0_14": 0.15,
                    "15_64": 0.68,
                    "65_plus": 0.17
                },
                "education_level": {
                    "higher_education": 0.32,
                    "secondary_education": 0.48,
                    "primary_education": 0.15,
                    "no_education": 0.05
                },
                "professions": {
                    "industrial_workers": 5000000,
                    "construction_workers": 1500000,
                    "agricultural_workers": 3000000,
                    "transport_workers": 1500000,
                    "service_workers": 8000000,
                    "retail_workers": 3000000,
                    "it_professionals": 500000,
                    "engineers": 800000,
                    "scientists": 200000,
                    "medical_staff": 1000000,
                    "teachers": 800000,
                    "military": 255000,
                    "government": 1500000,
                    "officials": 1000000
                }
            },
            "quality_of_life": {
                "healthcare_index": 55,
                "education_index": 62,
                "safety_index": 45,
                "environment_index": 50,
                "infrastructure_index": 58,
                "purchasing_power_index": 35
            },
            "business_sector": {
                "small_businesses": 500000,
                "startups": 15000,
                "self_employed": 1500000,
                "business_density": 12,
                "entrepreneurship_rate": 7
            },
            "army_experience": 92
        },
        "politics": {
            "ruling_party": "Слуга народу",
            "ideology": "Ліберальна демократія",
            "popularity": 48.3,
            "parliament": {
                "verkhovna_rada": 450
            },
            "un_rating": 72,
            "diplomatic_status": "Регіональна держава",
            "political_power": 100.0
        },
        "social_policies": {
            "освіта": "державна система",
            "охорона_здоров'я": "бюджетно-страхова система",
            "пенсії": "розподільча система",
            "допомога": "адресна соціальна допомога"
        },
        "active_reforms": [
            "Децентралізація",
            "Цифровізація держпослуг"
        ],
        "government_efficiency": 68,
        "economy": {
            "budget": 68663144821.94,
            "gdp": 199930575000,
            "tax_rate": 49.0,
            "debt": 119415000000.0,
            "inflation": 10.51,
            "wage": 5569,
            "cost_of_living": 40,
            "military_budget": 5000000000,
            "taxes": {
                "income": {
                    "rate": 18.0,
                    "progressive": True,
                    "brackets": [
                        {"up_to": 10000, "rate": 0},
                        {"up_to": 30000, "rate": 12},
                        {"up_to": 60000, "rate": 18},
                        {"above": 60000, "rate": 25}
                    ]
                },
                "corporate": {
                    "rate": 18.0,
                    "small_business_rate": 12.0,
                    "small_business_threshold": 3000000
                },
                "vat": {
                    "rate": 20.0,
                    "reduced_rate": 7.0,
                    "reduced_categories": ["food", "medicine"]
                },
                "property": {
                    "rate": 1.5,
                    "base_value": 50000
                },
                "luxury": {
                    "rate": 15.0,
                    "threshold": 3000000
                },
                "social_security": {
                    "employee_rate": 15.0,
                    "employer_rate": 25.0
                },
                "environmental": {
                    "co2_rate": 20.0,
                    "pollution_rate": 40.0
                }
            }
        },
        "expenses": {
            "healthcare": 7000000000,
            "police": 2000000000,
            "social_security": 15000000000,
            "education": 5000000000
        },
        "resources": {
            "oil": 20,
            "gas": 30,
            "coal": 150,
            "uranium": 10,
            "steel": 150,
            "aluminum": 50,
            "electronics": 50,
            "rare_metals": 15,
            "food": 300
        },
        "civil_goods": {
            "cars": 1200,
            "trucks": 200,
            "buses": 60,
            "agricultural_machinery": 400,
            "construction_machinery": 150,
            "industrial_equipment": 300,
            "machine_tools": 200,
            "industrial_robots": 50,
            "energy_equipment": 100,
            "electrical_equipment": 400,
            "telecom_equipment": 300,
            "tech_equipment": 250,
            "aerospace_equipment": 25,
            "auto_parts": 1000,
            "clothing": 8000,
            "medical_supplies": 2000,
            "medical_equipment": 150,
            "sanitary_products": 4000,
            "drones": 150,
            "fpv_drones": 200,
            "consumer_electronics": 2000,
            "food_products": 15000,
            "beverages": 10000,
            "chemicals": 600,
            "pharmaceuticals": 350,
            "furniture": 3500,
            "household_goods": 5000
        },
        "army": {
            "ground": {
                "tanks": 2800,
                "btr": 8500,
                "bmp": 6100,
                "armored_vehicles": 5000,
                "trucks": 20000,
                "cars": 15000,
                "ew_vehicles": 250,
                "engineering_equipment": 3200,
                "radar_systems": 800,
                "self_propelled_artillery": 1200,
                "towed_artillery": 900,
                "mlrs": 500,
                "atgm_complexes": 1600,
                "otr_complexes": 60,
                "zas": 450,
                "zdprk": 380,
                "short_range_air_defense": 700,
                "long_range_air_defense": 220
            },
            "equipment": {
                "small_arms": 400000,
                "grenade_launchers": 35000,
                "atgms": 12000,
                "manpads": 7500,
                "medical_equipment": 100000,
                "engineering_equipment_units": 26000,
                "fpv_drones": 50000
            },
            "air": {
                "fighters": 45,
                "attack_aircraft": 30,
                "bombers": 15,
                "transport_aircraft": 60,
                "attack_helicopters": 80,
                "transport_helicopters": 120,
                "recon_uav": 150,
                "attack_uav": 80,
                "kamikaze_drones": 3000
            },
            "navy": {
                "boats": 40,
                "corvettes": 2,
                "destroyers": 0,
                "cruisers": 0,
                "aircraft_carriers": 0,
                "submarines": 1
            },
            "missiles": {
                "strategic_nuclear": 0,
                "tactical_nuclear": 0,
                "cruise_missiles": 200,
                "hypersonic_missiles": 0,
                "ballistic_missiles": 150,
                "neoptron_coastal": 10
            }
        },
        "population_data": {
            "savings": 50000000000,
            "last_update": str(datetime.now())
        }
    },
    "1000000000000000007": {
        "state": {
            "population": 89000000,
            "territory": 1648195,
            "statename": "Иран",
            "government_type": "Исламская республика",
            "happiness": 58,
            "stability": 72,
            "trust": 52,
            "army_size": 630000,
            "readiness": 78,
            "demographics": {
                "birth_rate": 14.5,
                "death_rate": 5.4,
                "age_structure": {
                    "0_14": 0.24,
                    "15_64": 0.70,
                    "65_plus": 0.06
                },
                "education_level": {
                    "higher_education": 0.20,
                    "secondary_education": 0.35,
                    "primary_education": 0.35,
                    "no_education": 0.10
                },
                "professions": {
                    "industrial_workers": 8000000,
                    "construction_workers": 3000000,
                    "agricultural_workers": 6000000,
                    "transport_workers": 2000000,
                    "service_workers": 10000000,
                    "retail_workers": 4000000,
                    "it_professionals": 500000,
                    "engineers": 800000,
                    "scientists": 200000,
                    "medical_staff": 1500000,
                    "teachers": 1200000,
                    "military": 630000,
                    "government": 2500000,
                    "officials": 1500000
                }
            },
            "quality_of_life": {
                "healthcare_index": 55,
                "education_index": 58,
                "safety_index": 50,
                "environment_index": 45,
                "infrastructure_index": 52,
                "purchasing_power_index": 30
            },
            "business_sector": {
                "small_businesses": 1500000,
                "startups": 20000,
                "self_employed": 4000000,
                "business_density": 18,
                "entrepreneurship_rate": 8
            }
        },
        "politics": {
            "ruling_party": "Консервативные силы",
            "ideology": "Исламская теократия",
            "popularity": 42,
            "parliament": {
                "majlis": 290
            },
            "un_rating": 62,
            "diplomatic_status": "Региональная держава",
            "political_power": 100.0
        },
        "social_policies": {
            "образование": "государственная система с религиозным компонентом",
            "здравоохранение": "смешанная система (государственное и частное финансирование)",
            "пенсии": "распределительная система",
            "пособия": "адресная социальная помощь"
        },
        "active_reforms": [
            "Развитие ракетной программы",
            "Импортозамещение в оборонной сфере",
            "Развитие БПЛА"
        ],
        "government_efficiency": 60,
        "economy": {
            "budget": 48000000000,
            "gdp": 120000000000,
            "tax_rate": 28.5,
            "debt": 150000000000,
            "inflation": 40.0,
            "wage": 4200,
            "cost_of_living": 55,
            "military_budget": 10000000000,
            "taxes": {
                "income": {
                    "rate": 20.0,
                    "progressive": True,
                    "brackets": [
                        {"up_to": 5000, "rate": 0},
                        {"up_to": 15000, "rate": 10},
                        {"up_to": 30000, "rate": 15},
                        {"up_to": 50000, "rate": 20},
                        {"above": 50000, "rate": 25}
                    ]
                },
                "corporate": {
                    "rate": 25.0,
                    "small_business_rate": 20.0,
                    "small_business_threshold": 3000000
                },
                "vat": {
                    "rate": 9.0,
                    "reduced_rate": 5.0,
                    "reduced_categories": ["food", "medicine"]
                },
                "property": {
                    "rate": 1.0,
                    "base_value": 50000
                },
                "luxury": {
                    "rate": 20.0,
                    "threshold": 2000000
                },
                "social_security": {
                    "employee_rate": 7.0,
                    "employer_rate": 20.0
                },
                "environmental": {
                    "co2_rate": 15.0,
                    "pollution_rate": 30.0
                }
            }
        },
        "expenses": {
            "healthcare": 20000000000,
            "police": 5000000000,
            "social_security": 40000000000,
            "education": 15000000000
        },
        "resources": {
            "oil": 400,
            "gas": 300,
            "coal": 80,
            "uranium": 15,
            "steel": 80,
            "aluminum": 40,
            "electronics": 30,
            "rare_metals": 20,
            "food": 150
        },
        "civil_goods": {
            "cars": 1500,
            "trucks": 250,
            "buses": 80,
            "agricultural_machinery": 250,
            "construction_machinery": 120,
            "industrial_equipment": 250,
            "machine_tools": 150,
            "industrial_robots": 40,
            "energy_equipment": 150,
            "electrical_equipment": 350,
            "telecom_equipment": 250,
            "tech_equipment": 200,
            "aerospace_equipment": 15,
            "auto_parts": 800,
            "clothing": 6000,
            "medical_supplies": 1500,
            "medical_equipment": 100,
            "sanitary_products": 3000,
            "drones": 200,
            "fpv_drones": 200,
            "consumer_electronics": 1500,
            "food_products": 12000,
            "beverages": 8000,
            "chemicals": 500,
            "pharmaceuticals": 300,
            "furniture": 2500,
            "household_goods": 4000
        },
        "army": {
            "ground": {
                "tanks": 2000,
                "btr": 6000,
                "bmp": 4000,
                "armored_vehicles": 4500,
                "trucks": 18000,
                "cars": 14000,
                "ew_vehicles": 200,
                "engineering_equipment": 2800,
                "radar_systems": 700,
                "self_propelled_artillery": 1000,
                "towed_artillery": 800,
                "mlrs": 400,
                "atgm_complexes": 1500,
                "otr_complexes": 50,
                "zas": 400,
                "zdprk": 350,
                "short_range_air_defense": 650,
                "long_range_air_defense": 200
            },
            "equipment": {
                "small_arms": 420000,
                "grenade_launchers": 32000,
                "atgms": 11000,
                "manpads": 7000,
                "medical_equipment": 90000,
                "engineering_equipment_units": 25000,
                "fpv_drones": 20000
            },
            "air": {
                "fighters": 180,
                "attack_aircraft": 60,
                "bombers": 0,
                "transport_aircraft": 50,
                "attack_helicopters": 100,
                "transport_helicopters": 110,
                "recon_uav": 600,
                "attack_uav": 400,
                "kamikaze_drones": 8000
            },
            "navy": {
                "boats": 70,
                "corvettes": 5,
                "destroyers": 0,
                "cruisers": 0,
                "aircraft_carriers": 0,
                "submarines": 3
            },
            "missiles": {
                "strategic_nuclear": 0,
                "tactical_nuclear": 0,
                "cruise_missiles": 400,
                "hypersonic_missiles": 10,
                "ballistic_missiles": 300,
                "fateh_110": 80,
                "qiam_1": 60
            }
        },
        "population_data": {
            "savings": 100000000000,
            "last_update": str(datetime.now())
        }
    }
}

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_production_queue():
    try:
        with open(PRODUCTION_QUEUE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_orders": [], "completed_orders": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_orders": [], "completed_orders": []}

def save_production_queue(data):
    with open(PRODUCTION_QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_civil_production_queue():
    try:
        with open(CIVIL_PRODUCTION_QUEUE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_orders": [], "completed_orders": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_orders": [], "completed_orders": []}

def save_civil_production_queue(data):
    with open(CIVIL_PRODUCTION_QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_construction_queue():
    try:
        with open(CONSTRUCTION_QUEUE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_projects": [], "completed_projects": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_projects": [], "completed_projects": []}

def save_construction_queue(data):
    with open(CONSTRUCTION_QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_trades():
    try:
        with open(TRADES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_trades": [], "completed_trades": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_trades": [], "completed_trades": []}

def save_trades(data):
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_transfers():
    try:
        with open(TRANSFERS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_transfers": [], "completed_transfers": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_transfers": [], "completed_transfers": []}

def save_transfers(data):
    with open(TRANSFERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_research_data():
    try:
        with open(RESEARCH_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"players": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"players": {}}

def save_research_data(data):
    with open(RESEARCH_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_tariffs_data():
    try:
        with open(TARIFFS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"tariffs": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tariffs": {}}

def save_tariffs_data(data):
    with open(TARIFFS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_infrastructure():
    """Загрузка данных инфраструктуры"""
    try:
        with open(INFRASTRUCTURE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"infrastructure": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"infrastructure": {}}

def load_central_bank():
    """Загрузка данных центробанка"""
    try:
        with open(CENTRAL_BANK_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"banks": {}}
            return json.loads(content)
    except FileNotFoundError:
        return {"banks": {}}
    except json.JSONDecodeError:
        return {"banks": {}}

def save_central_bank(data):
    """Сохранение данных центробанка"""
    with open(CENTRAL_BANK_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def reset_extraction_time():
    """Сброс времени последней добычи"""
    empty_extraction = {"last_update": str(datetime.now())}
    with open(LAST_EXTRACTION_FILE, 'w', encoding='utf-8') as f:
        json.dump(empty_extraction, f, ensure_ascii=False, indent=4)

def save_infrastructure(data):
    """Сохранение данных инфраструктуры"""
    with open(INFRASTRUCTURE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_states():
    try:
        with open(STATES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"players": {}, "last_update": str(datetime.now())}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"players": {}, "last_update": str(datetime.now())}

def save_states(data):
    data["last_update"] = str(datetime.now())
    with open(STATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==================== НОВЫЕ ФУНКЦИИ ДЛЯ СБРОСА ====================

def reset_corporations_to_original():
    """
    Сбрасывает состояние корпораций к исходным значениям из starting_data
    """
    try:
        # Загружаем стартовые данные
        with open(CORPORATIONS_STARTING_DATA_FILE, 'r', encoding='utf-8') as f:
            starting_data = json.load(f)
        
        # Создаем новое состояние на основе стартовых данных
        new_state = {"corporations": {}}
        
        for corp_id, corp_data in starting_data.get("corporations", {}).items():
            # Копируем стартовые данные
            new_state["corporations"][corp_id] = {
                "id": corp_id,
                "name": corp_data.get("name", "Неизвестно"),
                "country": corp_data.get("country", "Неизвестно"),
                "city": corp_data.get("city", ""),
                "description": corp_data.get("description", ""),
                "specialization": corp_data.get("specialization", []),
                "products": corp_data.get("products", {}),
                "founded": corp_data.get("founded"),
                "website": corp_data.get("website"),
                "service_type": corp_data.get("service_type", "manufacturing"),
                "inventory": corp_data.get("inventory", {}),
                "budget": corp_data.get("budget", 10000000),
                "popularity": corp_data.get("popularity", 60),
                "market_share": corp_data.get("market_share", {}),
                "employees": corp_data.get("employees", 0),
                "last_update": str(datetime.now())
            }
        
        # Сохраняем
        with open(CORPORATIONS_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(new_state, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Корпорации сброшены: {len(new_state['corporations'])} корпораций восстановлено")
        return True
        
    except FileNotFoundError:
        print(f"❌ Файл {CORPORATIONS_STARTING_DATA_FILE} не найден!")
        return False
    except Exception as e:
        print(f"❌ Ошибка при сбросе корпораций: {e}")
        return False

def backup_corporations_state():
    """
    Создает резервную копию текущего состояния корпораций
    """
    try:
        # Проверяем, существует ли файл
        if not os.path.exists(CORPORATIONS_STATE_FILE):
            return
        
        # Создаем имя для бэкапа с временной меткой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backups/corporations_state_{timestamp}.json"
        
        # Создаем папку backups если её нет
        os.makedirs("backups", exist_ok=True)
        
        # Копируем файл
        shutil.copy2(CORPORATIONS_STATE_FILE, backup_file)
        print(f"✅ Создана резервная копия корпораций: {backup_file}")
        
    except Exception as e:
        print(f"❌ Ошибка при создании бэкапа корпораций: {e}")

def reset_satellites_to_original():
    """Сбрасывает данные спутников к исходным значениям"""
    try:
        with open(SATELLITES_FILE, 'w', encoding='utf-8') as f:
            json.dump({"satellites": STARTING_SATELLITES}, f, ensure_ascii=False, indent=4)
        print("✅ Спутники сброшены к исходным значениям")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сбросе спутников: {e}")
        return False

def reset_game_time_to_start():
    """Сбрасывает игровое время на стартовую дату"""
    try:
        with open(GAME_TIME_FILE, 'w', encoding='utf-8') as f:
            json.dump(START_GAME_TIME, f, ensure_ascii=False, indent=4)
        print("✅ Игровое время сброшено на 1 декабря 2022")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сбросе игрового времени: {e}")
        return False

def reset_mobilization():
    """Очищает очередь мобилизации"""
    try:
        with open(MOBILIZATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(EMPTY_MOBILIZATION, f, ensure_ascii=False, indent=4)
        print("✅ Очередь мобилизации очищена")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сбросе мобилизации: {e}")
        return False

def reset_military_doctrines():
    """Очищает данные о военных доктринах"""
    try:
        with open(MILITARY_DOCTRINES_FILE, 'w', encoding='utf-8') as f:
            json.dump(EMPTY_DOCTRINES, f, ensure_ascii=False, indent=4)
        print("✅ Военные доктрины сброшены")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сбросе военных доктрин: {e}")
        return False

def reset_espionage():
    """Очищает данные о разведке (если файл существует)"""
    try:
        if os.path.exists(ESPIONAGE_FILE):
            with open(ESPIONAGE_FILE, 'w', encoding='utf-8') as f:
                json.dump(EMPTY_ESPIONAGE, f, ensure_ascii=False, indent=4)
            print("✅ Данные разведки сброшены")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сбросе разведки: {e}")
        return False

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ИССЛЕДОВАНИЯМИ ====================

def init_research_for_country(country_name: str, user_id: str) -> Dict:
    funding_millions = STARTING_RESEARCH_FUNDING.get(country_name, STARTING_RESEARCH_FUNDING.get("США"))
    
    if not funding_millions:
        return {
            "research_projects": {},
            "completed_techs": {},
            "sector_funding": {},
            "total_spent": 0,
            "last_update": str(datetime.now())
        }
    
    sector_funding = {}
    for sector, amount_millions in funding_millions.items():
        mapped_sector = SECTOR_MAPPING.get(sector, sector)
        sector_funding[mapped_sector] = amount_millions * 1000000
    
    return {
        "research_projects": {},
        "completed_techs": {},
        "sector_funding": sector_funding,
        "total_spent": 0,
        "last_update": str(datetime.now())
    }

def init_population_data(country_name: str) -> Dict:
    """Инициализирует базовые данные населения для страны"""
    savings = BASE_POPULATION_SAVINGS.get(country_name, 100000000000)
    
    return {
        "savings": savings,
        "last_update": str(datetime.now())
    }

def reset_infrastructure_data():
    """
    Сбрасывает данные инфраструктуры до базовых значений
    """
    infra_data = load_infrastructure()
    
    for country_id, country_data in infra_data["infrastructure"].items():
        for econ_region, econ_data in country_data.get("economic_regions", {}).items():
            for region_name, region_data in econ_data.get("regions", {}).items():
                # Добавляем офисные центры (пропорционально населению)
                population = region_data.get("population", 0)
                development = region_data.get("development_level", 50)
                
                # Базовый расчёт офисных центров
                if "office_centers" not in region_data:
                    if population > 5000000:
                        region_data["office_centers"] = min(200, int(population / 100000))
                    elif population > 1000000:
                        region_data["office_centers"] = min(100, int(population / 50000))
                    elif population > 100000:
                        region_data["office_centers"] = min(50, int(population / 20000))
                    else:
                        region_data["office_centers"] = max(1, int(population / 10000))
                
                # Уровень дорог (зависит от развития)
                if "roads_level" not in region_data:
                    region_data["roads_level"] = max(1, min(10, development // 10))
                
                # Уровень сельского хозяйства (зависит от специализации и рельефа)
                if "agriculture_level" not in region_data:
                    specialization = region_data.get("specialization", "")
                    terrain = region_data.get("terrain", "")
                    
                    if "agricultural" in specialization:
                        base_level = 7
                    elif "plains" in terrain:
                        base_level = 5
                    elif "forest" in terrain:
                        base_level = 4
                    elif "mountain" in terrain:
                        base_level = 2
                    elif "desert" in terrain or "tundra" in terrain:
                        base_level = 1
                    else:
                        base_level = 3
                    
                    region_data["agriculture_level"] = max(0, min(10, base_level))
    
    save_infrastructure(infra_data)
    return infra_data

# ==================== КОМАНДЫ СБРОСА ====================

class ResetCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def clear_all_queues(self):
        empty_production = {"active_orders": [], "completed_orders": []}
        save_production_queue(empty_production)
        
        empty_civil = {"active_orders": [], "completed_orders": []}
        save_civil_production_queue(empty_civil)
        
        empty_construction = {"active_projects": [], "completed_projects": []}
        save_construction_queue(empty_construction)
        
        empty_trades = {"active_trades": [], "completed_trades": []}
        save_trades(empty_trades)
        
        empty_transfers = {"active_transfers": [], "completed_transfers": []}
        save_transfers(empty_transfers)

        empty_conflicts = {"conflicts": [], "history": []}
        with open(CONFLICTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(empty_conflicts, f, ensure_ascii=False, indent=4)
        
        # Очищаем мобилизацию
        reset_mobilization()
        
        # Очищаем военные доктрины
        reset_military_doctrines()
        
        # Очищаем разведку (если есть)
        reset_espionage()
    
    def reset_research_data_with_funding(self, states_data):
        research_data = {"players": {}}
        
        for state_id, state_info in states_data["players"].items():
            if "assigned_to" in state_info:
                user_id = state_info["assigned_to"]
                country_name = state_info["state"]["statename"]
                
                research_data["players"][user_id] = init_research_for_country(country_name, user_id)
        
        save_research_data(research_data)
        return research_data
    
    def reset_population_data(self, states_data):
        """Сбрасывает данные населения до базовых значений"""
        for state_id, state_info in states_data["players"].items():
            if "state" in state_info:
                country_name = state_info["state"]["statename"]
                state_info["population_data"] = init_population_data(country_name)
        
        return states_data
    
    def reset_tariffs_to_original(self):
        save_tariffs_data(ORIGINAL_TARIFFS)

    def reset_central_bank_to_original(self):
        """Сброс центробанка к исходным значениям"""
        save_central_bank(ORIGINAL_CENTRAL_BANK)

    def reset_extraction_time_to_now(self):
        """Сброс времени последней добычи на текущее"""
        reset_extraction_time()

    @commands.command(name='сброс')
    @commands.has_permissions(administrator=True)
    async def reset_all_states(self, ctx):
        """Сбросить все государства к исходным значениям"""
        
        view = ResetConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="⚠️ ВНИМАНИЕ! Сброс государств",
            description="Вы действительно хотите сбросить ВСЕ государства к исходным значениям?\n\n"
                       "Это действие **нельзя отменить**!",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="📊 Что будет сброшено:",
            value="• Экономические показатели\n"
                  "• Военная техника\n"
                  "• Ресурсы\n"
                  "• Гражданские товары\n"
                  "• Политические показатели\n"
                  "• Население и демография\n"
                  "• Расходы государства\n"
                  "• **Все очереди производства и сделки**\n"
                  "• **Все исследования**\n"
                  "• **Все тарифы и пошлины**\n"
                  "• **Центробанк**\n"
                  "• **Время добычи ресурсов**\n"
                  "• **Корпорации**\n"
                  "• **Спутники**\n"
                  "• **Игровое время**\n"
                  "• **Мобилизация**\n"
                  "• **Военные доктрины**\n"
                  "• **Разведка**",
            inline=False
        )
        
        embed.add_field(
            name="✅ Что сохранится:",
            value="• Назначения игроков на государства\n"
                  "• Инфраструктура",
            inline=False
        )
        
        embed.set_footer(text="Для подтверждения нажмите кнопку ниже")
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name='сброс_полный')
    @commands.has_permissions(administrator=True)
    async def reset_all_states_full(self, ctx):
        """Полный сброс всех государств"""
        
        view = FullResetConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="⚠️⚠️ ПОЛНЫЙ СБРОС ⚠️⚠️",
            description="Вы действительно хотите выполнить **ПОЛНЫЙ** сброс всех государств?\n\n"
                       "Это действие **нельзя отменить**!",
            color=discord.Color.dark_red()
        )
        
        embed.add_field(
            name="📊 Что будет сброшено:",
            value="• Экономические показатели\n"
                  "• Военная техника\n"
                  "• Ресурсы\n"
                  "• Гражданские товары\n"
                  "• Политические показатели\n"
                  "• Население и демография\n"
                  "• Расходы государства\n"
                  "• **Назначения игроков**\n"
                  "• **Все очереди производства**\n"
                  "• **Все активные сделки**\n"
                  "• **Все переводы**\n"
                  "• **Все исследования**\n"
                  "• **Все тарифы**\n"
                  "• **Инфраструктура**\n"
                  "• **Корпорации**\n"
                  "• **Спутники**\n"
                  "• **Игровое время**\n"
                  "• **Мобилизация**\n"
                  "• **Военные доктрины**\n"
                  "• **Разведка**",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Последствия:",
            value="Все игроки будут сняты с управления государствами. "
                   "Им потребуется новое назначение от администрации.",
            inline=False
        )
        
        embed.set_footer(text="Это действие необратимо! Нажмите кнопку только если уверены")
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name='очистить_очереди')
    @commands.has_permissions(administrator=True)
    async def clear_queues(self, ctx):
        """Очистить все очереди (исследования сохраняются)"""
        
        view = ClearQueuesConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="🧹 Очистка очередей",
            description="Вы действительно хотите очистить ВСЕ очереди?\n\n"
                       "Будут удалены:\n"
                       "• Все активные военные заказы\n"
                       "• Все активные гражданские заказы\n"
                       "• Все строительные проекты\n"
                       "• Все активные торговые сделки\n"
                       "• Все активные переводы\n"
                       "• Все программы мобилизации\n"
                       "• Все исследуемые военные доктрины\n"
                       "• Все разведывательные операции\n\n"
                       "**Исследования, тарифы, население и инфраструктура НЕ будут затронуты**",
            color=discord.Color.orange()
        )
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name='сброс_тарифов')
    @commands.has_permissions(administrator=True)
    async def reset_tariffs(self, ctx):
        """Сбросить тарифы, пошлины и эмбарго к исходным значениям"""
        
        view = ResetTariffsConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="🛃 Сброс таможенной системы",
            description="Вы действительно хотите сбросить все тарифы, пошлины и эмбарго к исходным значениям?\n\n"
                       "Это действие **нельзя отменить**!",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="📊 Что будет сброшено:",
            value="• Базовые тарифы\n"
                  "• Специфические тарифы по странам\n"
                  "• Тарифы по товарам\n"
                  "• Экспортные пошлины\n"
                  "• Торговые соглашения\n"
                  "• Торговые войны\n"
                  "• Эмбарго\n"
                  "• Санкции",
            inline=False
        )
        
        embed.set_footer(text="Для подтверждения нажмите кнопку ниже")
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name='сброс_населения')
    @commands.has_permissions(administrator=True)
    async def reset_population(self, ctx):
        """Сбросить данные населения до базовых значений"""
        
        view = ResetPopulationConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="👥 Сброс данных населения",
            description="Вы действительно хотите сбросить данные населения до базовых значений?\n\n"
                       "Это действие **нельзя отменить**!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Что будет сброшено:",
            value="• Сбережения населения\n"
                  "• Данные о занятости\n"
                  "• История потребления\n"
                  "• Удовлетворение потребностей",
            inline=False
        )
        
        embed.add_field(
            name="✅ Что сохранится:",
            value="• Инфраструктура\n"
                  "• Военные заказы\n"
                  "• Гражданские товары\n"
                  "• Исследования\n"
                  "• Тарифы\n"
                  "• Спутники\n"
                  "• Мобилизация\n"
                  "• Военные доктрины",
            inline=False
        )
        
        embed.set_footer(text="После сброса данные будут пересчитаны автоматически")
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name='сброс_инфраструктуры')
    @commands.has_permissions(administrator=True)
    async def reset_infrastructure(self, ctx):
        """Сбросить данные инфраструктуры до базовых значений"""
        
        view = ResetInfrastructureConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="🏭 Сброс инфраструктуры",
            description="Вы действительно хотите сбросить данные инфраструктуры до базовых значений?\n\n"
                       "Будут добавлены/обновлены поля:\n"
                       "• **office_centers** — офисные центры\n"
                       "• **roads_level** — уровень дорог\n"
                       "• **agriculture_level** — уровень сельского хозяйства",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="⚠️ Внимание",
            value="Существующие значения этих полей будут перезаписаны!",
            inline=False
        )
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name='сброс_корпораций')
    @commands.has_permissions(administrator=True)
    async def reset_corporations(self, ctx):
        """Сбросить состояние корпораций к исходным значениям"""
        
        view = ResetCorporationsConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="🏭 Сброс корпораций",
            description="Вы действительно хотите сбросить ВСЕ корпорации к исходным значениям?\n\n"
                       "Будут сброшены:\n"
                       "• Инвентарь корпораций\n"
                       "• Бюджет корпораций\n"
                       "• Популярность\n"
                       "• Доля рынка\n"
                       "• Количество сотрудников",
            color=discord.Color.orange()
        )
        
        embed.add_field(
            name="⚠️ Внимание",
            value="Это действие **нельзя отменить**! Рекомендуется сначала сделать резервную копию.",
            inline=False
        )
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name='сброс_спутников')
    @commands.has_permissions(administrator=True)
    async def reset_satellites(self, ctx):
        """Сбросить спутниковые группировки к исходным значениям"""
        
        view = ResetSatellitesConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="🛰️ Сброс спутников",
            description="Вы действительно хотите сбросить спутниковые группировки к исходным значениям?\n\n"
                       "Будут восстановлены реальные данные на 2022 год.",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name='сброс_времени')
    @commands.has_permissions(administrator=True)
    async def reset_game_time(self, ctx):
        """Сбросить игровое время на 1 декабря 2022"""
        
        view = ResetGameTimeConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="⏰ Сброс игрового времени",
            description="Вы действительно хотите сбросить игровое время на 1 декабря 2022?\n\n"
                       "Это повлияет на доступность военных доктрин и другие временные события.",
            color=discord.Color.blue()
        )
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name='сброс_мобилизации')
    @commands.has_permissions(administrator=True)
    async def reset_mobilization(self, ctx):
        """Очистить очередь мобилизации"""
        
        view = ResetMobilizationConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="🏭 Сброс мобилизации",
            description="Вы действительно хотите очистить все активные программы мобилизации?",
            color=discord.Color.orange()
        )
        
        await ctx.send(embed=embed, view=view)

    @commands.command(name='сброс_доктрин')
    @commands.has_permissions(administrator=True)
    async def reset_doctrines(self, ctx):
        """Сбросить все военные доктрины"""
        
        view = ResetDoctrinesConfirmationView(ctx.author.id)
        
        embed = discord.Embed(
            title="⚔️ Сброс военных доктрин",
            description="Вы действительно хотите сбросить все изученные и исследуемые военные доктрины?",
            color=discord.Color.orange()
        )
        
        await ctx.send(embed=embed, view=view)


# ==================== КЛАССЫ ДЛЯ ПОДТВЕРЖДЕНИЯ ====================

class ResetConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, сбросить", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        states = load_states()
        
        # Сохраняем назначения игроков
        assignments = {}
        for state_id, data in states["players"].items():
            if "assigned_to" in data:
                assignments[state_id] = data["assigned_to"]
        
        # Восстанавливаем государства
        new_players = {}
        for state_id, original_data in ORIGINAL_STATES.items():
            new_players[state_id] = copy.deepcopy(original_data)
            if state_id in assignments:
                new_players[state_id]["assigned_to"] = assignments[state_id]
        
        states["players"] = new_players
        states["last_update"] = str(datetime.now())
        
        # Сбрасываем данные населения
        reset_commands = ResetCommands(interaction.client)
        states = reset_commands.reset_population_data(states)
        
        save_states(states)
        
        # Очищаем очереди
        reset_commands.clear_all_queues()
        
        # Сбрасываем исследования с реалистичным финансированием
        research_data = reset_commands.reset_research_data_with_funding(states)
        
        # Сбрасываем тарифы к исходным значениям
        reset_commands.reset_tariffs_to_original()

        reset_commands.reset_central_bank_to_original()
    
        reset_commands.reset_extraction_time_to_now()
        
        # Сбрасываем инфраструктуру
        reset_infrastructure_data()
        
        # Сбрасываем корпорации
        reset_corporations_to_original()
        
        # Сбрасываем спутники
        reset_satellites_to_original()
        
        # Сбрасываем игровое время
        reset_game_time_to_start()
        
        embed = discord.Embed(
            title="✅ Сброс выполнен!",
            description="Все государства восстановлены до исходных значений.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Статистика",
            value=f"• Восстановлено государств: {len(ORIGINAL_STATES)}\n"
                  f"• Сохранено назначений: {len(assignments)}\n"
                  f"• Военные заказы: очищены\n"
                  f"• Гражданские заказы: очищены\n"
                  f"• Стройки: очищены\n"
                  f"• Сделки: очищены\n"
                  f"• Переводы: очищены\n"
                  f"• Исследования: инициализированы\n"
                  f"• Тарифы: сброшены\n"
                  f"• Центробанк: сброшен\n"
                  f"• Время добычи: сброшено\n"
                  f"• Население: сброшено\n"
                  f"• Инфраструктура: обновлена\n"
                  f"• Корпорации: сброшены\n"
                  f"• Спутники: сброшены\n"
                  f"• Игровое время: сброшено\n"
                  f"• Мобилизация: очищена\n"
                  f"• Военные доктрины: сброшены\n"
                  f"• Разведка: очищена",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        try:
            channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"🔄 **Админ {interaction.user.name}** выполнил полный сброс всех систем")
        except:
            pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Сброс отменён",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class FullResetConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="⚠️ ДА, ВЫПОЛНИТЬ ПОЛНЫЙ СБРОС", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        states = load_states()
        
        # Восстанавливаем государства без назначений
        new_players = {}
        for state_id, original_data in ORIGINAL_STATES.items():
            new_players[state_id] = copy.deepcopy(original_data)
        
        states["players"] = new_players
        states["last_update"] = str(datetime.now())
        
        # Сбрасываем данные населения
        reset_commands = ResetCommands(interaction.client)
        states = reset_commands.reset_population_data(states)
        
        save_states(states)
        
        # Очищаем очереди
        reset_commands.clear_all_queues()
        
        # Сбрасываем исследования
        empty_research = {"players": {}}
        save_research_data(empty_research)
        
        # Сбрасываем тарифы к исходным значениям
        reset_commands.reset_tariffs_to_original()

        reset_commands.reset_central_bank_to_original()

        reset_commands.reset_extraction_time_to_now()
        
        # Сбрасываем инфраструктуру
        empty_infrastructure = {"infrastructure": {}}
        save_infrastructure(empty_infrastructure)
        
        # Сбрасываем корпорации
        reset_corporations_to_original()
        
        # Сбрасываем спутники
        reset_satellites_to_original()
        
        # Сбрасываем игровое время
        reset_game_time_to_start()
        
        embed = discord.Embed(
            title="✅ Полный сброс выполнен!",
            description="Все системы восстановлены до исходных значений.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Статистика",
            value=f"• Восстановлено государств: {len(ORIGINAL_STATES)}\n"
                  f"• Назначения игроков: **ВСЕ УДАЛЕНЫ**\n"
                  f"• Военные заказы: очищены\n"
                  f"• Гражданские заказы: очищены\n"
                  f"• Стройки: очищены\n"
                  f"• Сделки: очищены\n"
                  f"• Переводы: очищены\n"
                  f"• Исследования: сброшены\n"
                  f"• Тарифы: сброшены\n"
                  f"• Центробанк: сброшен\n"
                  f"• Население: сброшено\n"
                  f"• Инфраструктура: очищена\n"
                  f"• Корпорации: сброшены\n"
                  f"• Спутники: сброшены\n"
                  f"• Игровое время: сброшено\n"
                  f"• Мобилизация: очищена\n"
                  f"• Военные доктрины: сброшены\n"
                  f"• Разведка: очищена",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        try:
            channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"🔄 **Админ {interaction.user.name}** выполнил ПОЛНЫЙ сброс всех систем")
        except:
            pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Сброс отменён",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ClearQueuesConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, очистить", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        reset_commands = ResetCommands(interaction.client)
        reset_commands.clear_all_queues()
        
        embed = discord.Embed(
            title="✅ Очереди очищены!",
            description="Все производственные очереди, стройки, сделки, переводы, мобилизация, доктрины и разведка удалены.\n"
                       "**Исследования, тарифы, население, инфраструктура, корпорации, спутники и время сохранены**",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Статистика",
            value="• Военные заказы: очищены\n"
                  "• Гражданские заказы: очищены\n"
                  "• Стройки: очищены\n"
                  "• Сделки: очищены\n"
                  "• Переводы: очищены\n"
                  "• Мобилизация: очищена\n"
                  "• Военные доктрины: очищены\n"
                  "• Разведка: очищена",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        try:
            channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"🧹 **Админ {interaction.user.name}** очистил все очереди")
        except:
            pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Очистка отменена",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ResetTariffsConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, сбросить тарифы", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        reset_commands = ResetCommands(interaction.client)
        reset_commands.reset_tariffs_to_original()
        
        embed = discord.Embed(
            title="✅ Тарифы сброшены!",
            description="Все тарифы, пошлины, эмбарго восстановлены до исходных значений.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Статистика",
            value="• Базовые тарифы: восстановлены\n"
                  "• Тарифы по странам: восстановлены\n"
                  "• Тарифы по товарам: восстановлены\n"
                  "• Экспортные пошлины: восстановлены\n"
                  "• Торговые соглашения: восстановлены\n"
                  "• Эмбарго: восстановлены\n"
                  "• Санкции: восстановлены",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        try:
            channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"🛃 **Админ {interaction.user.name}** сбросил все тарифы")
        except:
            pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Сброс тарифов отменён",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ResetPopulationConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, сбросить население", style=discord.ButtonStyle.primary)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        states = load_states()
        
        reset_commands = ResetCommands(interaction.client)
        states = reset_commands.reset_population_data(states)
        
        save_states(states)
        
        embed = discord.Embed(
            title="✅ Данные населения сброшены!",
            description="Все показатели населения восстановлены до базовых значений.\n"
                       "При следующем обновлении данные будут пересчитаны автоматически.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Что сделано",
            value="• Сбережения восстановлены\n"
                  "• Данные о потреблении очищены\n"
                  "• Занятость будет пересчитана",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        try:
            channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"👥 **Админ {interaction.user.name}** сбросил данные населения")
        except:
            pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Сброс населения отменён",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ResetInfrastructureConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, сбросить инфраструктуру", style=discord.ButtonStyle.primary)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        # Сбрасываем инфраструктуру до базовых значений
        reset_infrastructure_data()
        
        embed = discord.Embed(
            title="✅ Инфраструктура сброшена!",
            description="Все данные инфраструктуры обновлены до базовых значений.",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="📊 Что добавлено/обновлено:",
            value="• **office_centers** — офисные центры\n"
                  "• **roads_level** — уровень дорог\n"
                  "• **agriculture_level** — уровень сельского хозяйства",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)
        
        try:
            channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
            if channel:
                await channel.send(f"🏭 **Админ {interaction.user.name}** сбросил данные инфраструктуры")
        except:
            pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Сброс инфраструктуры отменён",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ResetCorporationsConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, сбросить корпорации", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        # Создаем резервную копию
        backup_corporations_state()
        
        # Сбрасываем корпорации
        success = reset_corporations_to_original()
        
        if success:
            embed = discord.Embed(
                title="✅ Корпорации сброшены!",
                description="Все корпорации восстановлены до исходных значений.",
                color=discord.Color.green()
            )
            
            # Загружаем статистику для отчета
            with open(CORPORATIONS_STARTING_DATA_FILE, 'r', encoding='utf-8') as f:
                starting_data = json.load(f)
            
            corp_count = len(starting_data.get("corporations", {}))
            
            embed.add_field(
                name="📊 Статистика",
                value=f"• Восстановлено корпораций: {corp_count}\n"
                      f"• Инвентарь: сброшен\n"
                      f"• Бюджеты: восстановлены\n"
                      f"• Популярность: сброшена к базовой",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
            try:
                channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
                if channel:
                    await channel.send(f"🏭 **Админ {interaction.user.name}** сбросил все корпорации")
            except:
                pass
        else:
            await interaction.followup.send("❌ Ошибка при сбросе корпораций!", ephemeral=True)

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Сброс корпораций отменён",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ResetSatellitesConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, сбросить спутники", style=discord.ButtonStyle.primary)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        success = reset_satellites_to_original()
        
        if success:
            embed = discord.Embed(
                title="✅ Спутники сброшены!",
                description="Спутниковые группировки восстановлены до реальных значений 2022 года.",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed)
            
            try:
                channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
                if channel:
                    await channel.send(f"🛰️ **Админ {interaction.user.name}** сбросил спутниковые группировки")
            except:
                pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Сброс спутников отменён",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ResetGameTimeConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, сбросить время", style=discord.ButtonStyle.primary)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        success = reset_game_time_to_start()
        
        if success:
            embed = discord.Embed(
                title="✅ Игровое время сброшено!",
                description="Текущая дата: 1 декабря 2022 года",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed)
            
            try:
                channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
                if channel:
                    await channel.send(f"⏰ **Админ {interaction.user.name}** сбросил игровое время")
            except:
                pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Сброс времени отменён",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ResetMobilizationConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, очистить", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        success = reset_mobilization()
        
        if success:
            embed = discord.Embed(
                title="✅ Мобилизация очищена!",
                description="Все активные программы мобилизации удалены.",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed)
            
            try:
                channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
                if channel:
                    await channel.send(f"🏭 **Админ {interaction.user.name}** очистил очередь мобилизации")
            except:
                pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Очистка отменена",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ResetDoctrinesConfirmationView(View):
    def __init__(self, user_id):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Да, сбросить", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return

        await interaction.response.defer()
        
        success = reset_military_doctrines()
        
        if success:
            embed = discord.Embed(
                title="✅ Военные доктрины сброшены!",
                description="Все изученные и исследуемые доктрины удалены.",
                color=discord.Color.green()
            )
            
            await interaction.followup.send(embed=embed)
            
            try:
                channel = interaction.client.get_channel(ADMIN_LOG_CHANNEL_ID)
                if channel:
                    await channel.send(f"⚔️ **Админ {interaction.user.name}** сбросил военные доктрины")
            except:
                pass

    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Эта команда не для вас!", ephemeral=True)
            return
            
        embed = discord.Embed(
            title="❌ Сброс отменён",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ КОГА ====================

async def setup(bot):
    await bot.add_cog(ResetCommands(bot))

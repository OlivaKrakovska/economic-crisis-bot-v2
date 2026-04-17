# infra_build.py - Модуль для строительства инфраструктуры
# Версия 4.8 - Полная интеграция с эмбарго и санкциями

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Tuple, List, Optional

from utils import (
    get_user_id, get_user_name, send_response, edit_response, 
    format_number, format_billion, format_infra_cost, format_time,
    create_embed, safe_delete, send_ephemeral, update_ephemeral,
    DARK_THEME_COLOR, load_states, save_states,
    get_currency_code, EXCHANGE_RATES_2019, get_budget, add_to_budget, subtract_from_budget
)

# Импорт системы тарифов и эмбарго
from trade_tariffs import TariffSystem

# ==================== КАСТОМНЫЕ ЭМОДЗИ (только для текста в эмбедах) ====================

ASSET_EMOJIS = {
    "military_factories": "<:Military_factory:1492864212085506068>",
    "civilian_factories": "<:Civilian_factory:1492864140501323986>",
    "office_centers": "<:office_center:1492908676824957079>",
    "oil_depots": "<:Neftebaza:1492864864354570401>",
    "refineries": "<:NPZ:1492864753582997665>",
    "nuclear_power": "<:Nuclear_reactor:1492864507591262208>",
    "thermal_power": "<:Nuclear_reactor:1492864507591262208>",
    "hydro_power": "<:Nuclear_reactor:1492864507591262208>",
    "solar_power": "<:Nuclear_reactor:1492864507591262208>",
    "wind_power": "<:Nuclear_reactor:1492864507591262208>",
    "shipyards": "<:Naval_base:1492864427522003054>",
    "internet_infrastructure": "<:Telecommunication:1492864324975464548>",
    "short_range_air_defense": "<:ZRK:1492864585995255808>",
    "long_range_air_defense": "<:ZRK:1492864585995255808>",
    "zdprk": "<:ZRK:1492864585995255808>",
    "zas": "<:ZRK:1492864585995255808>",
    "radar_systems": "<:ZRK:1492864585995255808>",
}

DEMOGRAPHIC_EMOJIS = {
    "population": "<:Icon_pop:1493160086284009593>",
    "population_growth": "<:Mod_pop_bonus_workforce_mult:1493160012648808458>",
    "development_level": "<:gold_price:1492880036792107008>",
    "birth_rate": "<:social:1425212640602357910>",
    "death_rate": "<:smert:1492913346859765892>",
    "unemployment_rate": "<:immigration:1492868112901472256>",
    "education_level": "<:education:1425212638366797824>",
    "separatism": "<:resistance:1492868038096060587>",
    "government_support": "<:loyal:1492867859968163851>",
    "happiness": "<:social:1487167248908156988>",
    "trust": "<:loyal:1492867859968163851>",
    "stability": "<:crisis:1487167453443391509>",
}

ECONOMIC_EMOJIS = {
    "grp": "<:fin:1425212665479041024>",
    "gdp_contribution": "<:eco_baff:1492879901760421888>",
    "average_wage": "<:size_pops_mult:1471574910580297850>",
    "cost_of_living": "<:money:1429345094695129088>",
    "money": "<:money:1429345094695129088>",
}

SPECIALIZATION_EMOJIS = {
    "oil_rich": "<:big_fuel_reserves:1492880440128704583>",
    "resource_rich": "<:resource_extration:1492878755956527114>",
    "industrial_heartland": "<:construction_repair:1492879195657732256>",
    "technology_hub": "<:Technology_sharing:1432616738754793563>",
    "capital_region": "<:government:1487167580350451804>",
    "naval_base": "<:naval_center:1493160893742317578>",
    "agricultural_region": "<:build_supply:1492880349842243795>",
    "border_region": "<:ukrep:1492864074634100938>",
    "mountain_fortress": "<:ukrep:1492864074634100938>",
    "tourist_haven": "<:kurort:1493160788721143898>",
    "financial_center": "<:money:1429345094695129088>",
    "cultural_center": "<:education:1425212638366797824>",
    "arctic_region": "<:crisis:1487167453443391509>",
}

RELIGION_EMOJIS = {
    "Ислам": "<:sunni_idea:1492909036021223455>",
    "Ислам (сунниты)": "<:sunni_idea:1492909036021223455>",
    "Ислам (шииты)": "<:sunni_idea:1492909036021223455>",
    "Алавиты": "<:sunni_idea:1492909036021223455>",
    "Атеизм/Агностицизм": "<:idea_ateism:1492908984548724779>",
    "Иудаизм": "<:judaism_idea:1492908854458191903>",
    "Синтоизм/Буддизм": "<:assianism_idea:1492908724585500832>",
    "Буддизм/Даосизм": "<:buddism_idea:1492908766109368460>",
    "Буддизм": "<:buddism_idea:1492908766109368460>",
    "Чхондогё": "<:assianism_idea:1492908724585500832>",
    "Католицизм": "<:christian_idea:1492908812179476632>",
    "Протестантизм": "<:christian_idea:1492908812179476632>",
    "Православие": "<:christian_idea:1492908812179476632>",
    "Христианство": "<:christian_idea:1492908812179476632>",
    "Копты": "<:christian_idea:1492908812179476632>",
    "default": "<:rebuild_pravoslavie:1492879017664057506>",
}

GENERAL_EMOJIS = {
    "coastal": "<:Naval_dockyards:1256638547201622087>",
    "power_generation": "<:fossil_plants_on:1493301808443949227>",
    "storage_capacity": "<:big_fuel_reserves:1492880440128704583>",
    "pvo_rocket": "<:AC_building_rocket:1493323421277224990>",
    "pvo_radar": "<:AC_building_radar:1493323710008922213>",
    "oil": "<:Oil:1262014013273935872>",
    "gas": "<:gaz:1272269314745040897>",
    "coal": "<:Coal:1471576908272504863>",
    "uranium": "<:uranium:1432612131140010024>",
    "religion": "<:rebuild_pravoslavie:1492879017664057506>",
    "specialization": "<:resource_extration:1492878755956527114>",
}

ACTION_EMOJIS = {
    "domestic": "<:Civilian_factory:1492864140501323986>",
    "abroad": "<:Telecommunication:1492864324975464548>",
    "foreign": "<:office_center:1492908676824957079>",
    "staff": "<:immigration:1492868112901472256>",
    "close": "<:smert:1492913346859765892>",
    "freeze": "<:crisis:1487167453443391509>",
    "unfreeze": "<:eco_baff:1492879901760421888>",
    "nationalize": "<:government:1487167580350451804>",
    "destroy": "<:ukrep:1492864074634100938>",
    "pp": "<:pp:1487015341883130027>",
    "money": "<:money:1429345094695129088>",
    "public": "<:Telecommunication:1492864324975464548>",
    "private": "<:office_center:1492908676824957079>",
    "success": "<:eco_baff:1492879901760421888>",
    "error": "<:smert:1492913346859765892>",
}

SPECIALIZATION_NAMES = {
    "oil_rich": "Нефтегазовая провинция",
    "resource_rich": "Ресурсный хаб",
    "industrial_heartland": "Промышленный центр",
    "technology_hub": "Технологический хаб",
    "capital_region": "Столичный регион",
    "naval_base": "Портовый центр",
    "agricultural_region": "Аграрный регион",
    "border_region": "Приграничный регион",
    "mountain_fortress": "Горная крепость",
    "tourist_haven": "Курортный центр",
    "financial_center": "Финансовый центр",
    "cultural_center": "Культурный центр",
    "arctic_region": "Арктический регион",
}

# ==================== КЛАССЫ СТРАН И ИХ ФОНОВЫЕ ИЗОБРАЖЕНИЯ ====================

COUNTRY_CLASSES = {
    "post_soviet": {
        "name": "Постсоветское пространство",
        "countries": ["Россия", "Беларусь", "Украина"],
        "images": [
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611293314384073/SOV_kursk.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611079262142504/BLR_minsk.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611295474192487/UKR_kiev.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611353393336551/SOV_ekaterinburg.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611293599334440/SOV_novosibirsk.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611295004692583/UKR_donetsk.png",
        ]
    },
    "europe": {
        "name": "Европа",
        "countries": ["Франция", "Германия", "Великобритания", "Польша", "Швеция", "Норвегия", "Швейцария", "Финляндия"],
        "images": [
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611080080035993/CAN_london.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611081422209034/ENG_oxford.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611081959215202/FRA_le_mans.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611082298687660/GER_hamburg.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611293955854357/SWE_stockholm.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611352848072744/POL_bialystok.png",
        ]
    },
    "asia_minor": {
        "name": "Малая Азия",
        "countries": ["Турция"],
        "images": [
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611352412000408/istanbul.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611294648172644/TUR_ankara.png",
        ]
    },
    "middle_east_poor": {
        "name": "Ближний Восток (бедный)",
        "countries": ["Сирия"],
        "images": [
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611082927968417/IRQ_ramadi.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611083146068028/IRQ_sinjar.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611294392061983/SYR_palmyra.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611294186803330/SYR_homs.png",
        ]
    },
    "middle_east_rich": {
        "name": "Ближний Восток (богатый)",
        "countries": ["Иран", "Израиль", "Египет"],
        "images": [
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611080973291530/EGY_alexandria.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611351938175159/ISR_beer_sheva.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611352189698118/ISR_tel_aviv.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611082927968417/IRQ_ramadi.png",
        ]
    },
    "america": {
        "name": "Америка",
        "countries": ["США", "Канада", "Бразилия"],
        "images": [
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611295797411941/USA_houston.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611296057462877/USA_portland.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611080080035993/CAN_london.png",
        ]
    },
    "asia": {
        "name": "Азия",
        "countries": ["Китай", "Япония", "КНДР"],
        "images": [
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611352626040874/JAP_tsushima.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611080608383027/CHI_guangzhou.png",
            "https://cdn.discordapp.com/attachments/1482389776584802468/1493611296057462877/USA_portland.png",
        ]
    },
}

# Флаги стран (оставляем, это не кастомные эмодзи, а юникод)
COUNTRY_FLAGS = {
    "США": "🇺🇸", "Россия": "🇷🇺", "Китай": "🇨🇳", "Германия": "🇩🇪",
    "Великобритания": "🇬🇧", "Франция": "🇫🇷", "Япония": "🇯🇵", "Израиль": "🇮🇱",
    "Украина": "🇺🇦", "Иран": "🇮🇷", "Беларусь": "🇧🇾", "Норвегия": "🇳🇴",
    "КНДР": "🇰🇵", "Турция": "🇹🇷", "Сирия": "🇸🇾", "Канада": "🇨🇦",
    "Польша": "🇵🇱", "Бразилия": "🇧🇷", "Швеция": "🇸🇪", "Финляндия": "🇫🇮",
    "Швейцария": "🇨🇭", "Египет": "🇪🇬"
}

# Все валюты из игры
ALL_CURRENCIES = ["USD", "RUB", "EUR", "GBP", "CNY", "JPY", "ILS", "UAH", "IRR", 
                  "BYN", "NOK", "KPW", "TRY", "SYP", "CAD", "PLN", "BRL", "SEK", 
                  "CHF", "EGP"]

def get_country_flag(country_name: str) -> str:
    return COUNTRY_FLAGS.get(country_name, "")

def get_region_image(country_name: str) -> Optional[str]:
    """Возвращает случайное фоновое изображение для страны из её класса"""
    for class_data in COUNTRY_CLASSES.values():
        if country_name in class_data["countries"]:
            images = class_data["images"]
            if images:
                return random.choice(images)
            return None
    return None

def safe_set_image(embed: discord.Embed, url: Optional[str]) -> None:
    """Безопасно устанавливает изображение в эмбед"""
    if not url:
        return
    try:
        embed.set_image(url=url)
    except Exception:
        pass

# ID канала для логов перемещений ПВО
PVO_MOVE_LOG_CHANNEL_ID = 1482389776584802468

# ID канала для предложений о продаже активов
ASSET_SALE_CHANNEL_ID = 1249782883770695821

# Картинка для эмбедов продажи активов
ASSET_SALE_IMAGE = "https://images-ext-1.discordapp.net/external/wxrYz1jvkB9BC0HguWDTAL0DcHlPi6o8OSSRlxP3SwM/https/st.depositphotos.com/1152339/3241/i/450/depositphotos_32416853-stock-photo-news-concept-company-news-on.jpg"

# Файлы для хранения данных
INFRASTRUCTURE_FILE = 'infrastructure.json'
CONSTRUCTION_QUEUE_FILE = 'infra_construction.json'
ASSET_SALE_OFFERS_FILE = 'asset_sale_offers.json'
FROZEN_ASSETS_FILE = 'frozen_assets.json'

# Поля, которые являются активами инфраструктуры (БЕЗ ПВО и РЛС)
ASSET_FIELDS = [
    "shipyards", "military_factories", "civilian_factories", "oil_depots",
    "refineries", "thermal_power", "hydro_power", "solar_power",
    "nuclear_power", "wind_power", "internet_infrastructure", "office_centers"
]

# Поля ПВО (отдельно)
PVO_FIELDS = [
    "short_range_air_defense", "long_range_air_defense", "zdprk", "zas", "radar_systems"
]

# Мета-поля, которые НЕ являются строениями
NON_BUILDING_FIELDS = [
    "specialization", "terrain", "coastal", "bordering_countries",
    "development_level", "population", "radiation"
]

# Стоимость активов в USD
ASSET_BASE_PRICES_USD = {
    "military_factories": 300_000_000,
    "civilian_factories": 200_000_000,
    "office_centers": 150_000_000,
    "oil_depots": 150_000_000,
    "refineries": 400_000_000,
    "shipyards": 500_000_000,
    "thermal_power": 350_000_000,
    "hydro_power": 600_000_000,
    "solar_power": 180_000_000,
    "nuclear_power": 1_500_000_000,
    "wind_power": 220_000_000,
    "internet_infrastructure": 100_000_000,
}

# Срок действия лота (24 часа)
LOT_EXPIRY_HOURS = 24

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ЗАМОРОЖЕННЫМИ АКТИВАМИ ====================

def load_frozen_assets() -> dict:
    """Загружает данные о замороженных активах"""
    try:
        with open(FROZEN_ASSETS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_frozen_assets(data: dict):
    """Сохраняет данные о замороженных активах"""
    with open(FROZEN_ASSETS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def is_asset_frozen(host_country: str, region_name: str, asset_type: str, owner_country: str) -> bool:
    """Проверяет, заморожен ли актив"""
    frozen = load_frozen_assets()
    key = f"{host_country}:{region_name}:{asset_type}:{owner_country}"
    return frozen.get(key, False)

def set_asset_frozen(host_country: str, region_name: str, asset_type: str, owner_country: str, frozen: bool):
    """Устанавливает статус заморозки актива"""
    data = load_frozen_assets()
    key = f"{host_country}:{region_name}:{asset_type}:{owner_country}"
    if frozen:
        data[key] = True
    else:
        data.pop(key, None)
    save_frozen_assets(data)

async def freeze_assets_on_embargo(host_country: str, target_country: str):
    """
    Автоматически замораживает все активы target_country в host_country при объявлении полного эмбарго
    """
    infra_data = load_infrastructure()
    
    for country_id, country_data in infra_data.get("infrastructure", {}).items():
        if country_data.get("country") != host_country:
            continue
        
        regions = get_all_regions_from_country(infra_data, country_id)
        
        for region_name, region_data in regions.items():
            for asset_type in ASSET_FIELDS:
                if asset_type in region_data:
                    asset = region_data[asset_type]
                    if isinstance(asset, dict) and "ownership" in asset:
                        ownership = asset["ownership"]
                        if target_country in ownership and ownership[target_country] > 0:
                            set_asset_frozen(host_country, region_name, asset_type, target_country, True)
        
        break
    
    save_infrastructure(infra_data)

async def unfreeze_assets_on_embargo_removal(host_country: str, target_country: str):
    """
    Размораживает все активы target_country в host_country при снятии эмбарго
    """
    infra_data = load_infrastructure()
    
    for country_id, country_data in infra_data.get("infrastructure", {}).items():
        if country_data.get("country") != host_country:
            continue
        
        regions = get_all_regions_from_country(infra_data, country_id)
        
        for region_name, region_data in regions.items():
            for asset_type in ASSET_FIELDS:
                if asset_type in region_data:
                    asset = region_data[asset_type]
                    if isinstance(asset, dict) and "ownership" in asset:
                        ownership = asset["ownership"]
                        if target_country in ownership and ownership[target_country] > 0:
                            set_asset_frozen(host_country, region_name, asset_type, target_country, False)
        
        break
    
    save_infrastructure(infra_data)

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С АКТИВАМИ ====================

def get_asset_total(region_data: Dict, asset_type: str) -> int:
    asset_value = region_data.get(asset_type, 0)
    if isinstance(asset_value, dict):
        return asset_value.get("total", 0)
    return asset_value if isinstance(asset_value, int) else 0

def get_asset_ownership(region_data: Dict, asset_type: str) -> Dict[str, int]:
    asset_value = region_data.get(asset_type, {})
    if isinstance(asset_value, dict):
        return asset_value.get("ownership", {})
    return {}

def set_asset_ownership(region_data: Dict, asset_type: str, ownership: Dict[str, int]):
    total = sum(ownership.values())
    region_data[asset_type] = {"total": total, "ownership": ownership}

def add_asset_to_region(region_data: Dict, asset_type: str, owner_country: str, quantity: int):
    current_ownership = get_asset_ownership(region_data, asset_type)
    current_ownership[owner_country] = current_ownership.get(owner_country, 0) + quantity
    set_asset_ownership(region_data, asset_type, current_ownership)

def remove_asset_from_region(region_data: Dict, asset_type: str, owner_country: str, quantity: int) -> bool:
    current_ownership = get_asset_ownership(region_data, asset_type)
    if current_ownership.get(owner_country, 0) >= quantity:
        current_ownership[owner_country] -= quantity
        if current_ownership[owner_country] == 0:
            del current_ownership[owner_country]
        set_asset_ownership(region_data, asset_type, current_ownership)
        return True
    return False

def count_infrastructure_facilities(region_data: Dict) -> int:
    total = 0
    for field in ASSET_FIELDS:
        if field in region_data:
            total += get_asset_total(region_data, field)
    return total

# ==================== ФУНКЦИЯ ПОЛУЧЕНИЯ КУРСА ВАЛЮТЫ ====================

def get_exchange_rate(country_name: str) -> float:
    return EXCHANGE_RATES_2019.get(country_name, 1.0)

def format_local_currency(amount_usd: float, country_name: str) -> str:
    rate = get_exchange_rate(country_name)
    currency_code = get_currency_code_from_country(country_name)
    local_amount = amount_usd * rate
    return f"{format_billion(local_amount)} {currency_code}"

def get_currency_code_from_country(country_name: str) -> str:
    states = load_states()
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == country_name:
            return get_currency_code(data.get("economy", {}))
    return "USD"

def parse_amount_string(amount_str: str) -> Optional[int]:
    """Парсит строку с суммой, поддерживая K, M, B, T, тыс, млн, млрд, трлн"""
    amount_str = amount_str.strip().upper().replace(" ", "")
    
    if not amount_str:
        return None
    
    try:
        if "ТРЛН" in amount_str or "Т" in amount_str and not any(c.isdigit() for c in amount_str.replace("Т", "")):
            number_part = amount_str.replace("ТРЛН", "").replace("Т", "")
            return int(float(number_part) * 1_000_000_000_000)
        elif "МЛРД" in amount_str or "B" in amount_str:
            number_part = amount_str.replace("МЛРД", "").replace("B", "")
            return int(float(number_part) * 1_000_000_000)
        elif "МЛН" in amount_str or "M" in amount_str:
            number_part = amount_str.replace("МЛН", "").replace("M", "")
            return int(float(number_part) * 1_000_000)
        elif "ТЫС" in amount_str or "K" in amount_str:
            number_part = amount_str.replace("ТЫС", "").replace("K", "")
            return int(float(number_part) * 1_000)
        else:
            return int(float(amount_str))
    except ValueError:
        return None

def format_price_short(amount: int) -> str:
    """Форматирует число с сокращением (тыс, млн, млрд, трлн)"""
    if amount >= 1_000_000_000_000:
        val = amount / 1_000_000_000_000
        return f"{val:.2f}".rstrip('0').rstrip('.') + " трлн"
    elif amount >= 1_000_000_000:
        val = amount / 1_000_000_000
        return f"{val:.2f}".rstrip('0').rstrip('.') + " млрд"
    elif amount >= 1_000_000:
        val = amount / 1_000_000
        return f"{val:.2f}".rstrip('0').rstrip('.') + " млн"
    elif amount >= 1_000:
        val = amount / 1_000
        return f"{val:.2f}".rstrip('0').rstrip('.') + " тыс"
    else:
        return str(amount)

# ==================== ФУНКЦИИ ДЛЯ ПРОДАЖИ АКТИВОВ ====================

def load_asset_sale_offers():
    """Загружает активные предложения о продаже активов"""
    try:
        with open(ASSET_SALE_OFFERS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_offers": [], "completed_offers": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_offers": [], "completed_offers": []}

def save_asset_sale_offers(data):
    """Сохраняет предложения о продаже активов"""
    with open(ASSET_SALE_OFFERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def return_expired_assets_to_seller(offer: dict):
    """Возвращает активы продавцу при истечении срока лота"""
    infra_data = load_infrastructure()
    country_id = None
    for cid, data in infra_data.get("infrastructure", {}).items():
        if data.get("country") == offer["seller_country"]:
            country_id = cid
            break
    
    if country_id:
        regions = get_all_regions_from_country(infra_data, country_id)
        if offer["region_name"] in regions:
            region_data = regions[offer["region_name"]]
            add_asset_to_region(region_data, offer["asset_type"], offer["seller_country"], offer["quantity"])
            
            if "economic_regions" in infra_data["infrastructure"][country_id]:
                for econ_region, econ_data in infra_data["infrastructure"][country_id]["economic_regions"].items():
                    if offer["region_name"] in econ_data.get("regions", {}):
                        econ_data["regions"][offer["region_name"]] = region_data
                        break
            save_infrastructure(infra_data)
            return True
    return False

async def show_asset_sale_info(interaction, user_id: int, player_data: dict):
    """Показывает информационное меню о продаже активов"""
    country_name = player_data["state"]["statename"]
    
    embed = discord.Embed(
        title=f"{ACTION_EMOJIS['domestic']} Продажа активов",
        description="**Информация о продаже активов**\n\n"
                   "• Вы можете продать принадлежащие вам активы другим странам\n"
                   "• Цена устанавливается в выбранной валюте\n"
                   "• Покупатель оплачивает указанную сумму\n"
                   "• После принятия предложения активы переходят в собственность покупателя\n"
                   "• Сделка необратима\n"
                   f"• Срок действия лота: **{LOT_EXPIRY_HOURS} часа(ов)**\n\n"
                   "**Рыночные цены на активы (USD):**\n"
                   f"{ASSET_EMOJIS.get('civilian_factories', '')} Гражданская фабрика: {format_price_short(200_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('military_factories', '')} Военный завод: {format_price_short(300_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('office_centers', '')} Бизнес-центр: {format_price_short(150_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('oil_depots', '')} Нефтебаза: {format_price_short(150_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('refineries', '')} НПЗ: {format_price_short(400_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('shipyards', '')} Верфь: {format_price_short(500_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('thermal_power', '')} ТЭС: {format_price_short(350_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('hydro_power', '')} ГЭС: {format_price_short(600_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('solar_power', '')} СЭС: {format_price_short(180_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('nuclear_power', '')} АЭС: {format_price_short(1_500_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('wind_power', '')} ВЭС: {format_price_short(220_000_000)} USD\n"
                   f"{ASSET_EMOJIS.get('internet_infrastructure', '')} ЦОД: {format_price_short(100_000_000)} USD",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=ASSET_SALE_IMAGE)
    
    view = AssetSaleStartView(user_id, player_data, country_name)
    await interaction.response.edit_message(embed=embed, view=view)


class AssetSaleStartView(View):
    """Начальное View для продажи активов"""
    def __init__(self, user_id: int, player_data: dict, country_name: str):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
    
    @discord.ui.button(label="Создать предложение", style=discord.ButtonStyle.success)
    async def create_offer_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await self.show_economic_region_selection(interaction)
    
    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_infrastructure_menu(interaction)
    
    async def show_economic_region_selection(self, interaction: discord.Interaction):
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data.get("infrastructure", {}).items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        
        if not country_id:
            await interaction.response.send_message("Данные инфраструктуры не найдены!", ephemeral=True)
            return
        
        economic_regions = infra_data["infrastructure"][country_id].get("economic_regions", {})
        
        if not economic_regions:
            await interaction.response.send_message("Нет экономических районов!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор экономического района",
            description="Выберите экономический район, в котором находится актив для продажи:",
            color=DARK_THEME_COLOR
        )
        
        options = []
        for econ_region_name in list(economic_regions.keys())[:25]:
            region_count = len(economic_regions[econ_region_name].get("regions", {}))
            options.append(discord.SelectOption(
                label=econ_region_name[:100],
                value=econ_region_name,
                description=f"Регионов: {region_count}"
            ))
        
        view = AssetSaleEconRegionView(self.user_id, self.player_data, self.country_name, economic_regions)
        select = Select(placeholder="Выберите экономический район...", options=options)
        select.callback = view.on_econ_region_select
        view.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = view.back_callback
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)


class AssetSaleEconRegionView(View):
    """View для выбора экономического района"""
    def __init__(self, user_id: int, player_data: dict, country_name: str, economic_regions: dict):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.economic_regions = economic_regions
    
    async def on_econ_region_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = interaction.data["values"][0]
        regions = self.economic_regions[econ_region].get("regions", {})
        
        regions_with_assets = {}
        for region_name, region_data in regions.items():
            for asset_type in ASSET_FIELDS:
                if asset_type in region_data:
                    asset = region_data[asset_type]
                    if isinstance(asset, dict) and "ownership" in asset:
                        ownership = asset["ownership"]
                        if self.country_name in ownership and ownership[self.country_name] > 0:
                            regions_with_assets[region_name] = region_data
                            break
        
        if not regions_with_assets:
            await interaction.response.send_message("В этом районе нет активов для продажи!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор региона",
            description=f"Экономический район: **{econ_region}**\nВыберите регион:",
            color=DARK_THEME_COLOR
        )
        
        options = []
        for region_name in list(regions_with_assets.keys())[:25]:
            options.append(discord.SelectOption(
                label=region_name[:100],
                value=region_name
            ))
        
        view = AssetSaleRegionView(self.user_id, self.player_data, self.country_name, econ_region, regions_with_assets)
        select = Select(placeholder="Выберите регион...", options=options)
        select.callback = view.on_region_select
        view.add_item(select)
        
        back_btn = Button(label="Назад к районам", style=discord.ButtonStyle.secondary)
        back_btn.callback = view.back_callback
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_asset_sale_info(interaction, self.user_id, self.player_data)


class AssetSaleRegionView(View):
    """View для выбора региона"""
    def __init__(self, user_id: int, player_data: dict, country_name: str, econ_region: str, regions: dict):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.econ_region = econ_region
        self.regions = regions
    
    async def on_region_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        region_name = interaction.data["values"][0]
        region_data = self.regions[region_name]
        
        available_assets = {}
        for asset_type in ASSET_FIELDS:
            if asset_type in region_data:
                asset = region_data[asset_type]
                if isinstance(asset, dict) and "ownership" in asset:
                    ownership = asset["ownership"]
                    if self.country_name in ownership and ownership[self.country_name] > 0:
                        available_assets[asset_type] = ownership[self.country_name]
        
        embed = discord.Embed(
            title="Выбор типа актива",
            description=f"Регион: **{region_name}**\nВыберите тип актива для продажи:",
            color=DARK_THEME_COLOR
        )
        
        options = []
        for asset_type, count in available_assets.items():
            asset_name = INFRASTRUCTURE_COSTS.get(asset_type, {}).get("name", asset_type)
            options.append(discord.SelectOption(
                label=asset_name[:100],
                value=asset_type,
                description=f"Доступно: {count} шт."
            ))
        
        view = AssetSaleTypeView(self.user_id, self.player_data, self.country_name, 
                                  self.econ_region, region_name, region_data, available_assets)
        select = Select(placeholder="Выберите тип актива...", options=options[:25])
        select.callback = view.on_asset_select
        view.add_item(select)
        
        back_btn = Button(label="Назад к регионам", style=discord.ButtonStyle.secondary)
        back_btn.callback = view.back_callback
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data.get("infrastructure", {}).items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        
        economic_regions = infra_data["infrastructure"][country_id].get("economic_regions", {})
        
        embed = discord.Embed(
            title="Выбор экономического района",
            description="Выберите экономический район, в котором находится актив для продажи:",
            color=DARK_THEME_COLOR
        )
        
        options = []
        for econ_region_name in list(economic_regions.keys())[:25]:
            region_count = len(economic_regions[econ_region_name].get("regions", {}))
            options.append(discord.SelectOption(
                label=econ_region_name[:100],
                value=econ_region_name,
                description=f"Регионов: {region_count}"
            ))
        
        view = AssetSaleEconRegionView(self.user_id, self.player_data, self.country_name, economic_regions)
        select = Select(placeholder="Выберите экономический район...", options=options)
        select.callback = view.on_econ_region_select
        view.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = view.back_callback
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)


class AssetSaleTypeView(View):
    """View для выбора типа актива"""
    def __init__(self, user_id: int, player_data: dict, country_name: str, 
                 econ_region: str, region_name: str, region_data: dict, available_assets: dict):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.econ_region = econ_region
        self.region_name = region_name
        self.region_data = region_data
        self.available_assets = available_assets
    
    async def on_asset_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        asset_type = interaction.data["values"][0]
        max_count = self.available_assets[asset_type]
        
        modal = AssetSaleDetailsModal(
            self.user_id, self.player_data, self.country_name,
            self.econ_region, self.region_name, self.region_data, 
            asset_type, max_count
        )
        await interaction.response.send_modal(modal)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data.get("infrastructure", {}).items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        
        economic_regions = infra_data["infrastructure"][country_id].get("economic_regions", {})
        regions = economic_regions[self.econ_region].get("regions", {})
        
        regions_with_assets = {}
        for r_name, r_data in regions.items():
            for at in ASSET_FIELDS:
                if at in r_data:
                    asset = r_data[at]
                    if isinstance(asset, dict) and "ownership" in asset:
                        ownership = asset["ownership"]
                        if self.country_name in ownership and ownership[self.country_name] > 0:
                            regions_with_assets[r_name] = r_data
                            break
        
        embed = discord.Embed(
            title="Выбор региона",
            description=f"Экономический район: **{self.econ_region}**\nВыберите регион:",
            color=DARK_THEME_COLOR
        )
        
        options = []
        for r_name in list(regions_with_assets.keys())[:25]:
            options.append(discord.SelectOption(label=r_name[:100], value=r_name))
        
        view = AssetSaleRegionView(self.user_id, self.player_data, self.country_name, self.econ_region, regions_with_assets)
        select = Select(placeholder="Выберите регион...", options=options)
        select.callback = view.on_region_select
        view.add_item(select)
        
        back_btn = Button(label="Назад к районам", style=discord.ButtonStyle.secondary)
        back_btn.callback = view.back_callback
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)


class AssetSaleDetailsModal(Modal, title="Детали продажи"):
    def __init__(self, user_id: int, player_data: dict, country_name: str,
                 econ_region: str, region_name: str, region_data: dict, 
                 asset_type: str, max_count: int):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.econ_region = econ_region
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.max_count = max_count
        
        asset_name = INFRASTRUCTURE_COSTS.get(asset_type, {}).get("name", asset_type)
        
        self.quantity = TextInput(
            label=f"Количество (макс: {max_count})",
            placeholder="Введите число",
            min_length=1,
            max_length=4,
            required=True
        )
        self.add_item(self.quantity)
        
        self.currency = TextInput(
            label="Валюта оплаты",
            placeholder="USD, RUB, EUR, GBP и др.",
            min_length=3,
            max_length=3,
            required=True,
            default="USD"
        )
        self.add_item(self.currency)
        
        self.price = TextInput(
            label="Цена за единицу",
            placeholder="Например: 1000000 или 1M",
            min_length=1,
            max_length=20,
            required=True
        )
        self.add_item(self.price)
        
        self.lot_type = TextInput(
            label="Тип лота (public/private)",
            placeholder="public - всем, private - выбранным странам",
            min_length=6,
            max_length=7,
            required=True,
            default="public"
        )
        self.add_item(self.lot_type)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity.value)
            if quantity < 1 or quantity > self.max_count:
                await interaction.response.send_message(f"Количество должно быть от 1 до {self.max_count}!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Введите корректное число для количества!", ephemeral=True)
            return
        
        currency = self.currency.value.strip().upper()
        if currency not in ALL_CURRENCIES:
            await interaction.response.send_message(f"Неверная валюта! Доступные: {', '.join(ALL_CURRENCIES)}", ephemeral=True)
            return
        
        price_parsed = parse_amount_string(self.price.value)
        if price_parsed is None or price_parsed <= 0:
            await interaction.response.send_message("Введите корректную цену!", ephemeral=True)
            return
        
        lot_type = self.lot_type.value.strip().lower()
        if lot_type not in ["public", "private"]:
            await interaction.response.send_message("Тип лота должен быть 'public' или 'private'!", ephemeral=True)
            return
        
        self.quantity_val = quantity
        self.currency_val = currency
        self.price_val = price_parsed
        self.lot_type_val = lot_type
        
        if lot_type == "private":
            await self.show_country_selection(interaction)
        else:
            await self.show_confirmation(interaction, [])
    
    async def show_country_selection(self, interaction: discord.Interaction):
        states = load_states()
        all_countries = []
        for data in states["players"].values():
            country = data.get("state", {}).get("statename")
            if country and country != self.country_name:
                all_countries.append(country)
        
        all_countries = sorted(list(set(all_countries)))
        
        embed = discord.Embed(
            title="Выбор стран для приватного лота",
            description="Выберите страны, которым будет доступно предложение.\n"
                       "Можно выбрать несколько стран.",
            color=DARK_THEME_COLOR
        )
        
        options = []
        for country in all_countries[:25]:
            flag = get_country_flag(country)
            label = f"{flag} {country}" if flag else country
            options.append(discord.SelectOption(
                label=label[:100],
                value=country,
                description="Добавить в список"
            ))
        
        view = AssetSalePrivateCountriesView(
            self.user_id, self.player_data, self.country_name,
            self.econ_region, self.region_name, self.asset_type,
            self.quantity_val, self.currency_val, self.price_val,
            all_countries
        )
        
        if options:
            select = Select(
                placeholder="Выберите страны...",
                options=options,
                min_values=1,
                max_values=min(len(options), 10)
            )
            select.callback = view.on_countries_select
            view.add_item(select)
        
        confirm_btn = Button(label="Подтвердить выбор", style=discord.ButtonStyle.success)
        confirm_btn.callback = view.confirm_callback
        view.add_item(confirm_btn)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = view.back_callback
        view.add_item(back_btn)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_confirmation(self, interaction: discord.Interaction, allowed_countries: list):
        asset_name = INFRASTRUCTURE_COSTS.get(self.asset_type, {}).get("name", self.asset_type)
        emoji = ASSET_EMOJIS.get(self.asset_type, "")
        total_price = self.quantity_val * self.price_val
        
        embed = discord.Embed(
            title="Подтверждение продажи",
            description=f"**{self.quantity_val}** x {emoji} **{asset_name}**\n"
                       f"Регион: **{self.region_name}**\n"
                       f"Цена за единицу: **{format_price_short(self.price_val)} {self.currency_val}**\n"
                       f"Общая стоимость: **{format_price_short(total_price)} {self.currency_val}**\n"
                       f"Тип лота: **{self.lot_type_val}**\n"
                       f"Срок действия: **{LOT_EXPIRY_HOURS} часа(ов)**",
            color=DARK_THEME_COLOR
        )
        
        if allowed_countries:
            countries_text = "\n".join([f"{get_country_flag(c)} {c}" for c in allowed_countries[:10]])
            if len(allowed_countries) > 10:
                countries_text += f"\n... и ещё {len(allowed_countries) - 10}"
            embed.add_field(name="Доступно странам", value=countries_text, inline=False)
        
        embed.set_image(url=ASSET_SALE_IMAGE)
        
        view = AssetSaleConfirmView(
            self.user_id, self.player_data, self.country_name,
            self.econ_region, self.region_name, self.region_data,
            self.asset_type, self.quantity_val, self.currency_val, 
            self.price_val, total_price, self.lot_type_val, allowed_countries
        )
        await interaction.response.edit_message(embed=embed, view=view)


class AssetSalePrivateCountriesView(View):
    """View для выбора стран для приватного лота"""
    def __init__(self, user_id: int, player_data: dict, country_name: str,
                 econ_region: str, region_name: str, asset_type: str,
                 quantity: int, currency: str, price: int, all_countries: list):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.econ_region = econ_region
        self.region_name = region_name
        self.asset_type = asset_type
        self.quantity = quantity
        self.currency = currency
        self.price = price
        self.all_countries = all_countries
        self.selected_countries = []
    
    async def on_countries_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        self.selected_countries = interaction.data["values"]
        
        embed = discord.Embed(
            title="Выбор стран для приватного лота",
            description=f"**Выбрано стран: {len(self.selected_countries)}**\n"
                       f"{', '.join(self.selected_countries[:5])}" + 
                       ("..." if len(self.selected_countries) > 5 else ""),
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def confirm_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        if not self.selected_countries:
            await interaction.response.send_message("Выберите хотя бы одну страну!", ephemeral=True)
            return
        
        modal = AssetSaleDetailsModal(
            self.user_id, self.player_data, self.country_name,
            self.econ_region, self.region_name, {},
            self.asset_type, self.quantity
        )
        modal.quantity_val = self.quantity
        modal.currency_val = self.currency
        modal.price_val = self.price
        modal.lot_type_val = "private"
        await modal.show_confirmation(interaction, self.selected_countries)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Создание лота отменено",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=None)


class AssetSaleConfirmView(View):
    """View для подтверждения создания лота"""
    def __init__(self, user_id: int, player_data: dict, country_name: str,
                 econ_region: str, region_name: str, region_data: dict,
                 asset_type: str, quantity: int, currency: str, price_per_unit: int,
                 total_price: int, lot_type: str, allowed_countries: list):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.econ_region = econ_region
        self.region_name = region_name
        self.region_data = region_data
        self.asset_type = asset_type
        self.quantity = quantity
        self.currency = currency
        self.price_per_unit = price_per_unit
        self.total_price = total_price
        self.lot_type = lot_type
        self.allowed_countries = allowed_countries
    
    @discord.ui.button(label="Подтвердить", style=discord.ButtonStyle.success)
    async def confirm_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        # Проверка эмбарго перед созданием лота
        seller_tariffs = TariffSystem(self.country_name)
        embargoed_export = seller_tariffs.tariffs.get("export_embargoes", {})
        
        if self.asset_type in embargoed_export.get("all", []):
            asset_name = INFRASTRUCTURE_COSTS.get(self.asset_type, {}).get("name", self.asset_type)
            await interaction.followup.send(
                f"{ACTION_EMOJIS['error']} Невозможно создать лот! Экспорт {asset_name} заблокирован эмбарго!",
                ephemeral=True
            )
            return
        
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data.get("infrastructure", {}).items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        
        if country_id:
            regions = get_all_regions_from_country(infra_data, country_id)
            if self.region_name in regions:
                region_data = regions[self.region_name]
                current_ownership = get_asset_ownership(region_data, self.asset_type)
                current_count = current_ownership.get(self.country_name, 0)
                if current_count < self.quantity:
                    await interaction.followup.send(f"{ACTION_EMOJIS['error']} У вас недостаточно активов! Доступно: {current_count}", ephemeral=True)
                    return
                
                if not remove_asset_from_region(region_data, self.asset_type, self.country_name, self.quantity):
                    await interaction.followup.send(f"{ACTION_EMOJIS['error']} Ошибка при резервировании активов!", ephemeral=True)
                    return
                
                if "economic_regions" in infra_data["infrastructure"][country_id]:
                    for econ_region, econ_data in infra_data["infrastructure"][country_id]["economic_regions"].items():
                        if self.region_name in econ_data.get("regions", {}):
                            econ_data["regions"][self.region_name] = region_data
                            break
                save_infrastructure(infra_data)
        
        offers = load_asset_sale_offers()
        offer_id = len(offers["active_offers"]) + 1
        
        expires_at = datetime.now() + timedelta(hours=LOT_EXPIRY_HOURS)
        
        offer = {
            "id": offer_id,
            "seller_id": str(self.user_id),
            "seller_country": self.country_name,
            "econ_region": self.econ_region,
            "region_name": self.region_name,
            "asset_type": self.asset_type,
            "asset_name": INFRASTRUCTURE_COSTS.get(self.asset_type, {}).get("name", self.asset_type),
            "quantity": self.quantity,
            "currency": self.currency,
            "price_per_unit": self.price_per_unit,
            "total_price": self.total_price,
            "lot_type": self.lot_type,
            "allowed_countries": self.allowed_countries,
            "status": "pending",
            "created_at": str(datetime.now()),
            "expires_at": str(expires_at)
        }
        
        offers["active_offers"].append(offer)
        save_asset_sale_offers(offers)
        
        channel = interaction.client.get_channel(ASSET_SALE_CHANNEL_ID)
        if channel:
            asset_emoji = ASSET_EMOJIS.get(self.asset_type, "")
            seller_flag = get_country_flag(self.country_name)
            
            embed = discord.Embed(
                title=f"{asset_emoji} ПРЕДЛОЖЕНИЕ О ПРОДАЖЕ АКТИВОВ #{offer_id}",
                description=f"**{seller_flag} {self.country_name}** предлагает выкупить активы\n"
                           f"Тип лота: **{self.lot_type.upper()}**",
                color=0x2ecc71 if self.lot_type == "public" else 0x3498db,
                timestamp=datetime.now()
            )
            embed.add_field(name="Регион", value=self.region_name, inline=True)
            embed.add_field(name="Актив", value=f"{asset_emoji} {offer['asset_name']}", inline=True)
            embed.add_field(name="Количество", value=f"{self.quantity} шт.", inline=True)
            embed.add_field(name="Цена за ед.", value=f"{format_price_short(self.price_per_unit)} {self.currency}", inline=True)
            embed.add_field(name="Общая стоимость", value=f"{format_price_short(self.total_price)} {self.currency}", inline=True)
            embed.add_field(name="Истекает через", value=f"{LOT_EXPIRY_HOURS} ч.", inline=True)
            
            if self.lot_type == "private" and self.allowed_countries:
                countries_text = "\n".join([f"{get_country_flag(c)} {c}" for c in self.allowed_countries[:5]])
                if len(self.allowed_countries) > 5:
                    countries_text += f"\n... и ещё {len(self.allowed_countries) - 5}"
                embed.add_field(name="Доступно странам", value=countries_text, inline=False)
            
            embed.set_image(url=ASSET_SALE_IMAGE)
            embed.set_footer(text="Используйте кнопки ниже для ответа на предложение")
            
            view = AssetSaleResponseView(offer_id, self.country_name, self.lot_type, self.allowed_countries)
            
            if self.lot_type == "private":
                ping_text = " ".join([f"<@{uid}>" for data in load_states()["players"].values() 
                                     if data.get("state", {}).get("statename") in self.allowed_countries 
                                     for uid in [data.get("assigned_to")] if uid])
                await channel.send(content=ping_text if ping_text else None, embed=embed, view=view)
            else:
                await channel.send(embed=embed, view=view)
        
        embed = discord.Embed(
            title=f"{ACTION_EMOJIS['success']} Предложение создано!",
            description=f"Предложение #{offer_id} отправлено в канал продаж.\n"
                       f"Активы зарезервированы до завершения сделки.\n"
                       f"Срок действия: **{LOT_EXPIRY_HOURS} часа(ов)**.",
            color=DARK_THEME_COLOR
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(title=f"{ACTION_EMOJIS['close']} Продажа отменена", color=DARK_THEME_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)


class AssetSaleResponseView(View):
    """View для ответа на предложение о продаже"""
    def __init__(self, offer_id: int, seller_country: str, lot_type: str, allowed_countries: list):
        super().__init__(timeout=None)
        self.offer_id = offer_id
        self.seller_country = seller_country
        self.lot_type = lot_type
        self.allowed_countries = allowed_countries
    
    @discord.ui.button(label="Принять", style=discord.ButtonStyle.success)
    async def accept_btn(self, interaction: discord.Interaction, button: Button):
        states = load_states()
        buyer_data = None
        buyer_country = None
        
        for data in states["players"].values():
            if data.get("assigned_to") == str(interaction.user.id):
                buyer_data = data
                buyer_country = data["state"]["statename"]
                break
        
        if not buyer_data:
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} У вас нет государства!", ephemeral=True)
            return
        
        offers = load_asset_sale_offers()
        offer = None
        for o in offers["active_offers"]:
            if o["id"] == self.offer_id:
                offer = o
                break
        
        if not offer:
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} Предложение не найдено!", ephemeral=True)
            return
        
        if offer["status"] != "pending":
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} Предложение уже неактивно!", ephemeral=True)
            return
        
        if offer["seller_country"] == buyer_country:
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} Вы не можете купить активы у самого себя!", ephemeral=True)
            return
        
        if offer["lot_type"] == "private" and buyer_country not in offer["allowed_countries"]:
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} Это предложение недоступно для вашей страны!", ephemeral=True)
            return
        
        # ПРОВЕРКА ЭМБАРГО И САНКЦИЙ
        buyer_tariffs = TariffSystem(buyer_country)
        
        embargoed_categories = buyer_tariffs.get_embargoed_categories(offer["seller_country"])
        if "all" in embargoed_categories:
            await interaction.response.send_message(
                f"{ACTION_EMOJIS['error']} Невозможно купить активы! Ваша страна ввела **полное эмбарго** против {offer['seller_country']}!",
                ephemeral=True
            )
            return
        
        sanction_penalty = buyer_tariffs.get_sanction_penalty(offer["seller_country"])
        if sanction_penalty >= 0.9:
            await interaction.response.send_message(
                f"{ACTION_EMOJIS['error']} Невозможно купить активы! Против {offer['seller_country']} действуют **жёсткие санкции** ({sanction_penalty*100:.0f}% штраф)!",
                ephemeral=True
            )
            return
        
        if buyer_tariffs.is_product_embargoed(offer["seller_country"], offer["asset_type"]):
            asset_name = INFRASTRUCTURE_COSTS.get(offer["asset_type"], {}).get("name", offer["asset_type"])
            await interaction.response.send_message(
                f"{ACTION_EMOJIS['error']} Невозможно купить {asset_name}! Этот тип активов подпадает под эмбарго против {offer['seller_country']}!",
                ephemeral=True
            )
            return
        
        currency = offer["currency"]
        total_price = offer["total_price"]
        
        if currency == "USD":
            reserves = buyer_data["economy"].get("foreign_reserves", {})
            available = reserves.get("USD", 0)
        else:
            available = get_budget(buyer_data["economy"])
        
        if available < total_price:
            await interaction.response.send_message(
                f"{ACTION_EMOJIS['error']} Недостаточно средств!\n"
                f"Требуется: {format_price_short(total_price)} {currency}\n"
                f"Доступно: {format_price_short(available)} {currency}",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"{ACTION_EMOJIS['success']} Подтверждение покупки",
            description=f"Вы собираетесь приобрести:\n"
                       f"**{offer['quantity']} x {offer['asset_name']}**\n"
                       f"Стоимость: **{format_price_short(total_price)} {currency}**\n\n"
                       f"Средства будут списаны с вашего {'USD-резерва' if currency == 'USD' else 'бюджета'}.",
            color=0x2ecc71
        )
        
        if sanction_penalty > 0:
            embed.add_field(
                name="⚠️ Санкции",
                value=f"Из-за санкций против {offer['seller_country']} цена увеличена на {sanction_penalty*100:.0f}%",
                inline=False
            )
        
        view = AssetSalePaymentView(offer, buyer_data, buyer_country, interaction.user)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Отказать", style=discord.ButtonStyle.danger)
    async def reject_btn(self, interaction: discord.Interaction, button: Button):
        states = load_states()
        buyer_country = None
        
        for data in states["players"].values():
            if data.get("assigned_to") == str(interaction.user.id):
                buyer_country = data["state"]["statename"]
                break
        
        if not buyer_country:
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} У вас нет государства!", ephemeral=True)
            return
        
        offers = load_asset_sale_offers()
        offer = None
        for o in offers["active_offers"]:
            if o["id"] == self.offer_id:
                offer = o
                break
        
        if not offer:
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} Предложение не найдено!", ephemeral=True)
            return
        
        if offer["seller_country"] == buyer_country:
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} Вы не можете отклонить своё предложение!", ephemeral=True)
            return
        
        await return_expired_assets_to_seller(offer)
        
        offer["status"] = "rejected"
        offer["rejected_by"] = buyer_country
        offer["rejected_at"] = str(datetime.now())
        offers["completed_offers"].append(offer)
        offers["active_offers"].remove(offer)
        save_asset_sale_offers(offers)
        
        buyer_flag = get_country_flag(buyer_country)
        seller_flag = get_country_flag(offer["seller_country"])
        asset_emoji = ASSET_EMOJIS.get(offer["asset_type"], "")
        
        embed = discord.Embed(
            title=f"{ACTION_EMOJIS['close']} ПРЕДЛОЖЕНИЕ ОТКЛОНЕНО #{self.offer_id}",
            description=f"**{buyer_flag} {buyer_country}** отклонил(а) предложение от **{seller_flag} {offer['seller_country']}**\n"
                       f"Активы возвращены продавцу.",
            color=0xe74c3c,
            timestamp=datetime.now()
        )
        embed.add_field(name=f"{asset_emoji} Актив", value=f"{offer['quantity']} x {offer['asset_name']}", inline=True)
        embed.add_field(name="📍 Регион", value=offer["region_name"], inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)


class AssetSalePaymentView(View):
    """View для подтверждения оплаты"""
    def __init__(self, offer: dict, buyer_data: dict, buyer_country: str, buyer_user: discord.User):
        super().__init__(timeout=600)
        self.offer = offer
        self.buyer_data = buyer_data
        self.buyer_country = buyer_country
        self.buyer_user = buyer_user
    
    @discord.ui.button(label="Подтвердить оплату", style=discord.ButtonStyle.success)
    async def confirm_payment_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.buyer_user.id:
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=False)
        
        offers = load_asset_sale_offers()
        offer = None
        for o in offers["active_offers"]:
            if o["id"] == self.offer["id"]:
                offer = o
                break
        
        if not offer or offer["status"] != "pending":
            await interaction.followup.send(f"{ACTION_EMOJIS['error']} Предложение уже неактивно!", ephemeral=True)
            return
        
        currency = offer["currency"]
        total_price = offer["total_price"]
        
        if currency == "USD":
            reserves = self.buyer_data["economy"].get("foreign_reserves", {})
            available = reserves.get("USD", 0)
            if available < total_price:
                await interaction.followup.send(f"{ACTION_EMOJIS['error']} Недостаточно USD в резервах!", ephemeral=True)
                return
            reserves["USD"] = available - total_price
            self.buyer_data["economy"]["foreign_reserves"] = reserves
        else:
            budget = get_budget(self.buyer_data["economy"])
            if budget < total_price:
                await interaction.followup.send(f"{ACTION_EMOJIS['error']} Недостаточно средств в бюджете!", ephemeral=True)
                return
            subtract_from_budget(self.buyer_data["economy"], total_price)
        
        states = load_states()
        seller_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == offer["seller_id"]:
                seller_data = data
                break
        
        if seller_data:
            if currency == "USD":
                seller_reserves = seller_data["economy"].get("foreign_reserves", {})
                if "foreign_reserves" not in seller_data["economy"]:
                    seller_data["economy"]["foreign_reserves"] = {"USD": 0}
                seller_data["economy"]["foreign_reserves"]["USD"] = seller_data["economy"]["foreign_reserves"].get("USD", 0) + total_price
            else:
                add_to_budget(seller_data["economy"], total_price)
        
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data.get("infrastructure", {}).items():
            if data.get("country") == offer["seller_country"]:
                country_id = cid
                break
        
        if country_id:
            regions = get_all_regions_from_country(infra_data, country_id)
            if offer["region_name"] in regions:
                region_data = regions[offer["region_name"]]
                add_asset_to_region(region_data, offer["asset_type"], self.buyer_country, offer["quantity"])
                
                if "economic_regions" in infra_data["infrastructure"][country_id]:
                    for econ_region, econ_data in infra_data["infrastructure"][country_id]["economic_regions"].items():
                        if offer["region_name"] in econ_data.get("regions", {}):
                            econ_data["regions"][offer["region_name"]] = region_data
                            break
                save_infrastructure(infra_data)
        
        save_states(states)
        
        offer["status"] = "completed"
        offer["buyer_country"] = self.buyer_country
        offer["completed_at"] = str(datetime.now())
        offers["completed_offers"].append(offer)
        offers["active_offers"].remove(offer)
        save_asset_sale_offers(offers)
        
        buyer_flag = get_country_flag(self.buyer_country)
        seller_flag = get_country_flag(offer["seller_country"])
        asset_emoji = ASSET_EMOJIS.get(offer["asset_type"], "")
        
        embed = discord.Embed(
            title=f"{asset_emoji} СДЕЛКА ЗАВЕРШЕНА! #{offer['id']}",
            description=f"**{buyer_flag} {self.buyer_country}** приобрёл активы у **{seller_flag} {offer['seller_country']}**",
            color=0x2ecc71,
            timestamp=datetime.now()
        )
        embed.add_field(name="📍 Регион", value=offer["region_name"], inline=True)
        embed.add_field(name=f"{asset_emoji} Актив", value=f"{offer['quantity']} x {offer['asset_name']}", inline=True)
        embed.add_field(name=f"{ECONOMIC_EMOJIS['money']} Оплата", value=f"{format_price_short(offer['total_price'])} {offer['currency']}", inline=True)
        
        await interaction.followup.send(embed=embed)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_btn(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.buyer_user.id:
            await interaction.response.send_message(f"{ACTION_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(title=f"{ACTION_EMOJIS['close']} Оплата отменена", color=DARK_THEME_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== СЛОВАРЬ СТОИМОСТИ И ВРЕМЕНИ СТРОИТЕЛЬСТВА ====================

INFRASTRUCTURE_COSTS = {
    "shipyards": {
        "name": "Верфь", "cost": 500, "build_time": 12 * 3600,
        "description": "Строительство и ремонт кораблей. Увеличивает скорость производства кораблей на 5% за каждую верфь. **Требуется выход к морю!**",
        "max_per_region": 10, "requires_coastal": True,
        "emoji": ASSET_EMOJIS.get("shipyards", ""),
        "production_bonus": {"navy.boats": 0.05, "navy.corvettes": 0.05, "navy.destroyers": 0.05, "navy.cruisers": 0.05, "navy.aircraft_carriers": 0.05, "navy.submarines": 0.05}
    },
    "military_factories": {
        "name": "Военный завод", "cost": 300, "build_time": 8 * 3600,
        "description": "Производство военной техники. Увеличивает скорость производства всей военной техники на 2% за каждый завод.",
        "max_per_region": 50, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("military_factories", ""),
        "production_bonus": {"ground": 0.02, "air": 0.02, "missiles": 0.02}
    },
    "civilian_factories": {
        "name": "Гражданская фабрика", "cost": 200, "build_time": 6 * 3600,
        "description": "Производство товаров и экономический рост. Увеличивает скорость производства гражданских товаров на 3% за каждую фабрику.",
        "max_per_region": 100, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("civilian_factories", ""),
        "production_bonus": {"civil": 0.03}
    },
    "oil_depots": {
        "name": "Нефтебаза", "cost": 150, "build_time": 4 * 3600,
        "description": "Хранение нефти и нефтепродуктов. Увеличивает максимальный запас нефти на 1000 единиц и снижает потери при хранении.",
        "max_per_region": 30, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("oil_depots", ""),
        "storage_bonus": {"oil": 1000, "gas": 500}, "efficiency_bonus": 0.02
    },
    "refineries": {
        "name": "НПЗ", "cost": 400, "build_time": 10 * 3600,
        "description": "Переработка нефти в топливо. Увеличивает скорость производства химической и нефтехимической продукции на 10% за каждый завод.",
        "max_per_region": 15, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("refineries", ""),
        "production_bonus": {"chemicals": 0.10, "pharmaceuticals": 0.05}
    },
    "thermal_power": {
        "name": "ТЭС", "cost": 350, "build_time": 8 * 3600,
        "description": "Тепловая электростанция. Генерирует 100 МВт электроэнергии. Потребляет 0.024 угля и 0.012 нефти в день.",
        "max_per_region": 25, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("thermal_power", ""),
        "power_output": 100, "fuel_consumption": {"coal": 0.024, "oil": 0.012}
    },
    "hydro_power": {
        "name": "ГЭС", "cost": 600, "build_time": 16 * 3600,
        "description": "Гидроэлектростанция. Генерирует 150 МВт электроэнергии. Не требует топлива, зависит от наличия рек.",
        "max_per_region": 10, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("hydro_power", ""),
        "power_output": 150, "fuel_consumption": {}
    },
    "solar_power": {
        "name": "СЭС", "cost": 180, "build_time": 4 * 3600,
        "description": "Солнечная электростанция. Генерирует 40 МВт электроэнергии в дневное время. Не требует топлива.",
        "max_per_region": 40, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("solar_power", ""),
        "power_output": 40, "day_night_cycle": True, "fuel_consumption": {}
    },
    "nuclear_power": {
        "name": "АЭС", "cost": 1500, "build_time": 36 * 3600,
        "description": "Атомная электростанция. Генерирует 500 МВт электроэнергии. Потребляет 0.002 урана в день.",
        "max_per_region": 5, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("nuclear_power", ""),
        "power_output": 500, "fuel_consumption": {"uranium": 0.002}
    },
    "wind_power": {
        "name": "ВЭС", "cost": 220, "build_time": 5 * 3600,
        "description": "Ветровая электростанция. Генерирует 60 МВт электроэнергии. Не требует топлива, зависит от ветрености региона.",
        "max_per_region": 30, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("wind_power", ""),
        "power_output": 60, "weather_dependent": True, "fuel_consumption": {}
    },
    "internet_infrastructure": {
        "name": "ЦОД", "cost": 100, "build_time": 3 * 3600,
        "description": "Центр обработки данных. Увеличивает скорость исследований, эффективность правительства и прирост политической власти на 1% за каждый ЦОД.",
        "max_per_region": 200, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("internet_infrastructure", ""),
        "bonus": {"research_speed": 0.01, "government_efficiency": 0.01, "political_power_gain": 0.01}
    },
    "office_centers": {
        "name": "Бизнес-центр", "cost": 150, "build_time": 4 * 3600,
        "description": "Офисные здания для компаний сферы услуг, IT-фирм, банков и корпораций. Создаёт рабочие места в сфере услуг и даёт экономические бонусы.",
        "max_per_region": 200, "requires_coastal": False,
        "emoji": ASSET_EMOJIS.get("office_centers", ""),
        "bonus": {"service_boost": 0.02, "tax_boost": 0.01, "tech_boost": 0.005, "happiness_boost": 1, "consumption_boost": 0.01}
    },
    "long_range_air_defense": {
        "name": "ЗРК большой дальности", "cost": 0, "build_time": 30 * 60,
        "description": "Зенитный ракетный комплекс большой дальности. Защищает регион от авиации и ракет. Требует 1 единицу из арсенала для установки.",
        "max_per_region": 50, "requires_coastal": False, "army_field": "long_range_air_defense", "pvo_type": True, "can_move": True,
        "emoji": ASSET_EMOJIS.get("long_range_air_defense", "")
    },
    "short_range_air_defense": {
        "name": "ЗРК малой дальности", "cost": 0, "build_time": 20 * 60,
        "description": "Зенитный ракетный комплекс малой дальности. Защищает регион от авиации и БПЛА. Требует 1 единицу из арсенала для установки.",
        "max_per_region": 100, "requires_coastal": False, "army_field": "short_range_air_defense", "pvo_type": True, "can_move": True,
        "emoji": ASSET_EMOJIS.get("short_range_air_defense", "")
    },
    "zdprk": {
        "name": "ЗПРК", "cost": 0, "build_time": 15 * 60,
        "description": "Зенитный пушечно-ракетный комплекс. Эффективен против низколетящих целей и БПЛА. Требует 1 единицу из арсенала для установки.",
        "max_per_region": 80, "requires_coastal": False, "army_field": "zdprk", "pvo_type": True, "can_move": True,
        "emoji": ASSET_EMOJIS.get("zdprk", "")
    },
    "zas": {
        "name": "Зенитная артиллерия", "cost": 0, "build_time": 10 * 60,
        "description": "Зенитная самоходная установка. Защищает от низколетящих целей и БПЛА. Требует 1 единицу из арсенала для установки.",
        "max_per_region": 150, "requires_coastal": False, "army_field": "zas", "pvo_type": True, "can_move": True,
        "emoji": ASSET_EMOJIS.get("zas", "")
    },
    "radar_systems": {
        "name": "РЛС", "cost": 0, "build_time": 25 * 60,
        "description": "Радиолокационная станция. Обнаруживает воздушные цели, повышает эффективность ПВО. Требует 1 единицу из арсенала для установки.",
        "max_per_region": 30, "requires_coastal": False, "army_field": "radar_systems", "pvo_type": True, "can_move": True,
        "emoji": ASSET_EMOJIS.get("radar_systems", ""),
        "bonus": {"detection_range": 1.2, "pvo_efficiency": 0.1}
    }
}

# ==================== ФУНКЦИИ ДЛЯ РАСЧЁТА БОНУСОВ ====================

def calculate_research_bonus(region_data: Dict) -> float:
    bonus = 1.0
    internet_infra = get_asset_total(region_data, "internet_infrastructure")
    if internet_infra > 0:
        bonus += internet_infra * 0.01
    return bonus

def calculate_gov_efficiency_bonus(region_data: Dict) -> float:
    bonus = 0.0
    internet_infra = get_asset_total(region_data, "internet_infrastructure")
    if internet_infra > 0:
        bonus += internet_infra * 1
    return bonus

def calculate_pp_gain_bonus(region_data: Dict) -> float:
    bonus = 0.0
    internet_infra = get_asset_total(region_data, "internet_infrastructure")
    if internet_infra > 0:
        bonus += internet_infra * 0.01
    return bonus

def calculate_storage_capacity(region_data: Dict) -> Dict[str, int]:
    storage = {}
    oil_depots = get_asset_total(region_data, "oil_depots")
    if oil_depots > 0:
        storage["oil"] = storage.get("oil", 0) + oil_depots * 10000
        storage["gas"] = storage.get("gas", 0) + oil_depots * 5000
    refineries = get_asset_total(region_data, "refineries")
    if refineries > 0:
        storage["oil"] = storage.get("oil", 0) + refineries * 5000
        storage["gas"] = storage.get("gas", 0) + refineries * 3000
    return storage

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ПВО ====================

def get_army_pvo_count(player_data: Dict, pvo_type: str) -> int:
    army = player_data.get("army", {})
    ground = army.get("ground", {})
    return ground.get(pvo_type, 0)

def consume_army_pvo(player_data: Dict, pvo_type: str, quantity: int) -> bool:
    army = player_data.get("army", {})
    ground = army.get("ground", {})
    current = ground.get(pvo_type, 0)
    if current < quantity:
        return False
    ground[pvo_type] = current - quantity
    player_data["army"]["ground"] = ground
    return True

def add_army_pvo(player_data: Dict, pvo_type: str, quantity: int):
    army = player_data.get("army", {})
    if "ground" not in army:
        army["ground"] = {}
    ground = army["ground"]
    ground[pvo_type] = ground.get(pvo_type, 0) + quantity
    player_data["army"]["ground"] = ground

def can_build_pvo(player_data: Dict, pvo_type: str, quantity: int) -> Tuple[bool, str]:
    current_in_army = get_army_pvo_count(player_data, pvo_type)
    if current_in_army < quantity:
        return False, f"Недостаточно {INFRASTRUCTURE_COSTS[pvo_type]['name']} в арсенале! Доступно: {current_in_army}"
    return True, "OK"

def get_region_pvo_text(region_data: Dict) -> str:
    pvo_text = ""
    pvo_types = [
        ("long_range_air_defense", "ЗРК большой дальности", GENERAL_EMOJIS.get("pvo_rocket", "")),
        ("short_range_air_defense", "ЗРК малой дальности", GENERAL_EMOJIS.get("pvo_rocket", "")),
        ("zdprk", "ЗПРК", GENERAL_EMOJIS.get("pvo_rocket", "")),
        ("zas", "Зенитная артиллерия", GENERAL_EMOJIS.get("pvo_rocket", "")),
        ("radar_systems", "РЛС", GENERAL_EMOJIS.get("pvo_radar", ""))
    ]
    for pvo_type, name, emoji in pvo_types:
        count = get_asset_total(region_data, pvo_type)
        if count > 0:
            pvo_text += f"{emoji} {name}: **{count}**\n"
    if not pvo_text:
        pvo_text = "Нет средств ПВО"
    return pvo_text

def get_specialization_display(specialization: str) -> str:
    if not specialization:
        return ""
    name = SPECIALIZATION_NAMES.get(specialization, specialization.replace("_", " ").title())
    emoji = SPECIALIZATION_EMOJIS.get(specialization, "")
    return f"{emoji} {name}" if emoji else name

# ==================== ФУНКЦИЯ ОТОБРАЖЕНИЯ ИНОСТРАННЫХ АКТИВОВ ====================

def get_foreign_assets_text(region_data: Dict, host_country: str) -> str:
    assets_text = ""
    has_foreign = False
    
    for asset_type in ASSET_FIELDS:
        if asset_type in region_data:
            asset = region_data[asset_type]
            if isinstance(asset, dict) and "ownership" in asset:
                ownership = asset["ownership"]
                for owner_country, quantity in ownership.items():
                    if owner_country != host_country and quantity > 0:
                        asset_name = INFRASTRUCTURE_COSTS.get(asset_type, {}).get("name", asset_type)
                        emoji = INFRASTRUCTURE_COSTS.get(asset_type, {}).get("emoji", "")
                        frozen_status = " [ЗАМОРОЖЕН]" if is_asset_frozen(host_country, region_data.get("_name", ""), asset_type, owner_country) else ""
                        assets_text += f"{emoji} {asset_name} ({owner_country}): **{quantity}**{frozen_status}\n"
                        has_foreign = True
    
    if not has_foreign:
        assets_text = "Нет иностранных активов"
    
    return assets_text

# ==================== ФУНКЦИЯ ОТОБРАЖЕНИЯ ПОЛНОЙ СТАТИСТИКИ РЕГИОНА ====================

def get_region_detailed_info(region_data: Dict, country_name: str) -> discord.Embed:
    embed = discord.Embed(color=DARK_THEME_COLOR)
    
    population = region_data.get("population", 0)
    development = region_data.get("development_level", 0)
    coastal = "Да" if region_data.get("coastal", False) else "Нет"
    specialization = region_data.get("specialization", "")
    spec_display = get_specialization_display(specialization)
    
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['population']} Население", value=format_number(population), inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['development_level']} Развитие", value=f"{development}%", inline=True)
    embed.add_field(name=f"{GENERAL_EMOJIS['coastal']} Выход к морю", value=coastal, inline=True)
    
    if spec_display:
        embed.add_field(name=f"{GENERAL_EMOJIS['specialization']} Специализация", value=spec_display, inline=True)
    else:
        embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    grp_usd = region_data.get("grp", 0)
    gdp_contribution = region_data.get("gdp_contribution", 0)
    grp_local = format_local_currency(grp_usd, country_name)
    
    embed.add_field(name=f"{ECONOMIC_EMOJIS['grp']} ВРП", value=grp_local, inline=True)
    embed.add_field(name=f"{ECONOMIC_EMOJIS['gdp_contribution']} Вклад в ВВП", value=f"{gdp_contribution:.2f}%", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    birth_rate = region_data.get("birth_rate", 0)
    death_rate = region_data.get("death_rate", 0)
    population_growth = region_data.get("population_growth", 0)
    unemployment = region_data.get("unemployment_rate", 0)
    
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['birth_rate']} Рождаемость", value=f"{birth_rate:.1f}‰", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['death_rate']} Смертность", value=f"{death_rate:.1f}‰", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['population_growth']} Прирост", value=f"{population_growth:+.1f}‰", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['unemployment_rate']} Безработица", value=f"{unemployment:.1f}%", inline=True)
    
    education = region_data.get("education_level", 0)
    separatism = region_data.get("separatism", 0)
    gov_support = region_data.get("government_support", 0)
    
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['education_level']} Образованность", value=f"{education}%", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['separatism']} Сепаратизм", value=f"{separatism}%", inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['government_support']} Поддержка власти", value=f"{gov_support}%", inline=True)
    
    main_religion = region_data.get("main_religion", "Не указано")
    religions = region_data.get("religions", {})
    if religions:
        religion_text = ""
        for rel, pct in sorted(religions.items(), key=lambda x: x[1], reverse=True)[:3]:
            emoji = RELIGION_EMOJIS.get(rel, RELIGION_EMOJIS["default"])
            religion_text += f"{emoji} {rel}: {pct}%\n"
        embed.add_field(name=f"{GENERAL_EMOJIS['religion']} Религии", value=religion_text or "Нет данных", inline=False)
    else:
        emoji = RELIGION_EMOJIS.get(main_religion, RELIGION_EMOJIS["default"])
        embed.add_field(name=f"{GENERAL_EMOJIS['religion']} Основная религия", value=f"{emoji} {main_religion}" if emoji else main_religion, inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
        embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    avg_wage_usd = region_data.get("average_wage", 0)
    cost_of_living_usd = region_data.get("cost_of_living", 0)
    avg_wage_local = format_local_currency(avg_wage_usd, country_name)
    cost_of_living_local = format_local_currency(cost_of_living_usd, country_name)
    
    embed.add_field(name=f"{ECONOMIC_EMOJIS['average_wage']} Средняя ЗП", value=f"{avg_wage_local}/год", inline=True)
    embed.add_field(name=f"{ECONOMIC_EMOJIS['cost_of_living']} Стоимость жизни", value=f"{cost_of_living_local}/год", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    foreign_assets_text = get_foreign_assets_text(region_data, country_name)
    embed.add_field(name="Иностранные активы", value=foreign_assets_text, inline=False)
    
    return embed

# ==================== ФУНКЦИИ ДЛЯ ПЕРЕМЕЩЕНИЯ И ДЕМОНТАЖА ПВО ====================

async def show_move_pvo_from_region(interaction, user_id, country_name, from_region, region_data):
    infra_data = load_infrastructure()
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    if not country_id:
        await interaction.response.send_message("Данные инфраструктуры не найдены!", ephemeral=True)
        return
    economic_regions = infra_data["infrastructure"][country_id].get("economic_regions", {})
    if not economic_regions:
        await interaction.response.send_message("Нет экономических районов!", ephemeral=True)
        return
    embed = discord.Embed(title="Перемещение ПВО", description=f"Из региона: {from_region}\nВыберите экономический район назначения:", color=DARK_THEME_COLOR)
    select = MovePVOEconomicRegionSelect(user_id, country_name, from_region, economic_regions)
    view = View(timeout=600)
    view.add_item(select)
    back_button = Button(label="Назад к региону", style=discord.ButtonStyle.secondary)
    back_button.callback = lambda i: asyncio.create_task(back_to_region_categories(i, user_id, country_name, from_region, region_data))
    view.add_item(back_button)
    await interaction.response.edit_message(embed=embed, view=view)

async def back_to_region_categories(interaction, user_id, country_name, region_name, region_data):
    await safe_delete(interaction.message)
    await show_region_categories(interaction, user_id, country_name, region_name, region_data)

class MovePVOEconomicRegionSelect(Select):
    def __init__(self, user_id, country_name, from_region, economic_regions):
        self.user_id = user_id
        self.country_name = country_name
        self.from_region = from_region
        self.economic_regions = economic_regions
        options = []
        for econ_region in list(economic_regions.keys())[:25]:
            region_count = len(economic_regions[econ_region].get("regions", {}))
            options.append(discord.SelectOption(label=econ_region[:100], description=f"Регионов: {region_count}", value=econ_region))
        super().__init__(placeholder="Выберите экономический район...", options=options)
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        econ_region = self.values[0]
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data["infrastructure"].items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        regions = infra_data["infrastructure"][country_id]["economic_regions"][econ_region]["regions"]
        embed = discord.Embed(title="Выбор региона назначения", description=f"Перемещение ПВО из {self.from_region}\nЭкономический район: {econ_region}", color=DARK_THEME_COLOR)
        select = MovePVORegionSelect(self.user_id, self.country_name, self.from_region, econ_region, regions)
        view = View(timeout=600)
        view.add_item(select)
        back_button = Button(label="Назад к районам", style=discord.ButtonStyle.secondary)
        back_button.callback = lambda i: asyncio.create_task(show_move_pvo_from_region(interaction, self.user_id, self.country_name, self.from_region, {}))
        view.add_item(back_button)
        await interaction.response.edit_message(embed=embed, view=view)

class MovePVORegionSelect(Select):
    def __init__(self, user_id, country_name, from_region, econ_region, regions):
        self.user_id = user_id
        self.country_name = country_name
        self.from_region = from_region
        self.econ_region = econ_region
        self.regions = regions
        options = []
        for region_name in list(regions.keys())[:25]:
            if region_name != from_region:
                options.append(discord.SelectOption(label=region_name[:100], value=region_name))
        super().__init__(placeholder="Выберите регион назначения...", options=options)
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        to_region = self.values[0]
        region_data = self.regions.get(to_region, {})
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data["infrastructure"].items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        if country_id:
            regions = get_all_regions_from_country(infra_data, country_id)
            from_region_data = regions.get(self.from_region, {})
        else:
            from_region_data = {}
        available_pvo = []
        pvo_types = [("long_range_air_defense", "ЗРК большой дальности"), ("short_range_air_defense", "ЗРК малой дальности"), ("zdprk", "ЗПРК"), ("zas", "Зенитная артиллерия"), ("radar_systems", "РЛС")]
        for pvo_type, name in pvo_types:
            count = get_asset_total(from_region_data, pvo_type)
            if count > 0:
                available_pvo.append((pvo_type, name, count))
        if not available_pvo:
            await interaction.response.send_message("В исходном регионе нет ПВО для перемещения!", ephemeral=True)
            return
        embed = discord.Embed(title="Выбор типа ПВО", description=f"Из региона: {self.from_region}\nВ регион: {to_region}\nВыберите тип ПВО для перемещения:", color=DARK_THEME_COLOR)
        select = MovePVOTypeSelect(self.user_id, self.country_name, self.from_region, to_region, available_pvo)
        view = View(timeout=600)
        view.add_item(select)
        back_button = Button(label="Назад к регионам", style=discord.ButtonStyle.secondary)
        back_button.callback = lambda i: asyncio.create_task(show_move_pvo_from_region(interaction, self.user_id, self.country_name, self.from_region, {}))
        view.add_item(back_button)
        await interaction.response.edit_message(embed=embed, view=view)

class MovePVOTypeSelect(Select):
    def __init__(self, user_id, country_name, from_region, to_region, available_pvo):
        self.user_id = user_id
        self.country_name = country_name
        self.from_region = from_region
        self.to_region = to_region
        self.available_pvo = available_pvo
        options = []
        for pvo_type, name, count in available_pvo:
            options.append(discord.SelectOption(label=f"{name} ({count} шт.)", value=pvo_type))
        super().__init__(placeholder="Выберите тип ПВО...", options=options)
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        pvo_type = self.values[0]
        count = 0
        pvo_name = ""
        for p_type, name, c in self.available_pvo:
            if p_type == pvo_type:
                count = c
                pvo_name = name
                break
        modal = MovePVOQuantityModal(self.user_id, self.country_name, self.from_region, self.to_region, pvo_type, pvo_name, count)
        await interaction.response.send_modal(modal)

class MovePVOQuantityModal(Modal, title="Перемещение ПВО"):
    def __init__(self, user_id, country_name, from_region, to_region, pvo_type, pvo_name, max_quantity):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.from_region = from_region
        self.to_region = to_region
        self.pvo_type = pvo_type
        self.pvo_name = pvo_name
        self.max_quantity = max_quantity
        self.quantity_input = TextInput(label=f"Количество (макс: {max_quantity})", placeholder="Введите число", min_length=1, max_length=4, required=True, default="1")
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
        from strikes import get_region_distance
        distance = get_region_distance(self.country_name, self.from_region, self.country_name, self.to_region)
        travel_time = max(5 * 60, min(60 * 60, distance * 6))
        embed = discord.Embed(title="Подтверждение перемещения ПВО", description=f"Перемещение {quantity}x {self.pvo_name}", color=discord.Color.orange())
        embed.add_field(name="Из региона", value=self.from_region, inline=True)
        embed.add_field(name="В регион", value=self.to_region, inline=True)
        embed.add_field(name="Расстояние", value=f"{distance} км", inline=True)
        embed.add_field(name="Время в пути", value=format_time(travel_time), inline=True)
        embed.add_field(name="Предупреждение", value="ПВО будет недоступно во время перемещения.", inline=False)
        view = MovePVOConfirmView(self.user_id, self.country_name, self.from_region, self.to_region, self.pvo_type, self.pvo_name, quantity, distance, travel_time)
        await interaction.response.edit_message(embed=embed, view=view)

class MovePVOConfirmView(View):
    def __init__(self, user_id, country_name, from_region, to_region, pvo_type, pvo_name, quantity, distance, travel_time):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.country_name = country_name
        self.from_region = from_region
        self.to_region = to_region
        self.pvo_type = pvo_type
        self.pvo_name = pvo_name
        self.quantity = quantity
        self.distance = distance
        self.travel_time = travel_time
    @discord.ui.button(label="ПОДТВЕРДИТЬ ПЕРЕМЕЩЕНИЕ", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        queue = load_construction_queue()
        completion_time = datetime.now() + timedelta(seconds=self.travel_time)
        move_task = {"id": len(queue.get("active_moves", [])) + 1, "user_id": str(self.user_id), "country": self.country_name, "type": "move_pvo", "from_region": self.from_region, "to_region": self.to_region, "pvo_type": self.pvo_type, "pvo_name": self.pvo_name, "quantity": self.quantity, "distance": self.distance, "travel_time": self.travel_time, "start_time": str(datetime.now()), "completion_time": str(completion_time), "status": "in_progress", "notified": False}
        if "active_moves" not in queue:
            queue["active_moves"] = []
        queue["active_moves"].append(move_task)
        save_construction_queue(queue)
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data["infrastructure"].items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        if country_id:
            regions = get_all_regions_from_country(infra_data, country_id)
            if self.from_region in regions:
                remove_asset_from_region(regions[self.from_region], self.pvo_type, self.country_name, self.quantity)
                if "economic_regions" in infra_data["infrastructure"][country_id]:
                    for econ_region, econ_data in infra_data["infrastructure"][country_id]["economic_regions"].items():
                        if self.from_region in econ_data.get("regions", {}):
                            econ_data["regions"][self.from_region] = regions[self.from_region]
                            break
                else:
                    infra_data["infrastructure"][country_id]["regions"][self.from_region] = regions[self.from_region]
                save_infrastructure(infra_data)
        if interaction.client:
            await send_pvo_move_log(interaction.client, move_task)
        embed = discord.Embed(title="Перемещение ПВО начато!", description=f"Перемещение {self.quantity}x {self.pvo_name} из {self.from_region} в {self.to_region}", color=DARK_THEME_COLOR)
        embed.add_field(name="Расстояние", value=f"{self.distance} км", inline=True)
        embed.add_field(name="Время в пути", value=format_time(self.travel_time), inline=True)
        embed.add_field(name="ID задачи", value=str(move_task["id"]), inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)
    @discord.ui.button(label="ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        embed = discord.Embed(title="Перемещение отменено", color=DARK_THEME_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)

async def show_dismantle_pvo_menu(interaction, user_id, country_name, region_name, region_data):
    available_pvo = []
    pvo_types = [("long_range_air_defense", "ЗРК большой дальности"), ("short_range_air_defense", "ЗРК малой дальности"), ("zdprk", "ЗПРК"), ("zas", "Зенитная артиллерия"), ("radar_systems", "РЛС")]
    for pvo_type, name in pvo_types:
        count = get_asset_total(region_data, pvo_type)
        if count > 0:
            available_pvo.append((pvo_type, name, count))
    if not available_pvo:
        await interaction.response.send_message("В этом регионе нет ПВО для демонтажа!", ephemeral=True)
        return
    embed = discord.Embed(title="Демонтаж ПВО", description=f"Регион: {region_name}\nВыберите тип ПВО для демонтажа:", color=DARK_THEME_COLOR)
    select = DismantlePVOTypeSelect(user_id, country_name, region_name, region_data, available_pvo)
    view = View(timeout=600)
    view.add_item(select)
    back_button = Button(label="Назад к региону", style=discord.ButtonStyle.secondary)
    back_button.callback = lambda i: asyncio.create_task(back_to_region_categories(i, user_id, country_name, region_name, region_data))
    view.add_item(back_button)
    await interaction.response.edit_message(embed=embed, view=view)

class DismantlePVOTypeSelect(Select):
    def __init__(self, user_id, country_name, region_name, region_data, available_pvo):
        self.user_id = user_id
        self.country_name = country_name
        self.region_name = region_name
        self.region_data = region_data
        self.available_pvo = available_pvo
        options = []
        for pvo_type, name, count in available_pvo:
            options.append(discord.SelectOption(label=f"{name} ({count} шт.)", value=pvo_type))
        super().__init__(placeholder="Выберите тип ПВО...", options=options)
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        pvo_type = self.values[0]
        count = 0
        pvo_name = ""
        for p_type, name, c in self.available_pvo:
            if p_type == pvo_type:
                count = c
                pvo_name = name
                break
        modal = DismantlePVOQuantityModal(self.user_id, self.country_name, self.region_name, self.region_data, pvo_type, pvo_name, count)
        await interaction.response.send_modal(modal)

class DismantlePVOQuantityModal(Modal, title="Демонтаж ПВО"):
    def __init__(self, user_id, country_name, region_name, region_data, pvo_type, pvo_name, max_quantity):
        super().__init__()
        self.user_id = user_id
        self.country_name = country_name
        self.region_name = region_name
        self.region_data = region_data
        self.pvo_type = pvo_type
        self.pvo_name = pvo_name
        self.max_quantity = max_quantity
        self.quantity_input = TextInput(label=f"Количество (макс: {max_quantity})", placeholder="Введите число", min_length=1, max_length=4, required=True, default="1")
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
        embed = discord.Embed(title="Подтверждение демонтажа ПВО", description=f"Демонтаж {quantity}x {self.pvo_name} из региона {self.region_name}", color=discord.Color.orange())
        embed.add_field(name="Важно", value="При демонтаже ПВО возвращается в арсенал. Время демонтажа: 10 минут.", inline=False)
        view = DismantlePVOConfirmView(self.user_id, self.country_name, self.region_name, self.region_data, self.pvo_type, self.pvo_name, quantity)
        await interaction.response.edit_message(embed=embed, view=view)

class DismantlePVOConfirmView(View):
    def __init__(self, user_id, country_name, region_name, region_data, pvo_type, pvo_name, quantity):
        super().__init__(timeout=600)
        self.user_id = user_id
        self.country_name = country_name
        self.region_name = region_name
        self.region_data = region_data
        self.pvo_type = pvo_type
        self.pvo_name = pvo_name
        self.quantity = quantity
    @discord.ui.button(label="ПОДТВЕРДИТЬ ДЕМОНТАЖ", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        queue = load_construction_queue()
        dismantle_time = 10 * 60
        completion_time = datetime.now() + timedelta(seconds=dismantle_time)
        dismantle_task = {"id": len(queue.get("active_dismantles", [])) + 1, "user_id": str(self.user_id), "country": self.country_name, "type": "dismantle_pvo", "region": self.region_name, "pvo_type": self.pvo_type, "pvo_name": self.pvo_name, "quantity": self.quantity, "start_time": str(datetime.now()), "completion_time": str(completion_time), "status": "in_progress", "notified": False}
        if "active_dismantles" not in queue:
            queue["active_dismantles"] = []
        queue["active_dismantles"].append(dismantle_task)
        save_construction_queue(queue)
        embed = discord.Embed(title="Демонтаж ПВО начат!", description=f"Демонтаж {self.quantity}x {self.pvo_name} из региона {self.region_name}", color=DARK_THEME_COLOR)
        embed.add_field(name="Время", value=format_time(dismantle_time), inline=True)
        embed.add_field(name="ID задачи", value=str(dismantle_task["id"]), inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)
    @discord.ui.button(label="ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        embed = discord.Embed(title="Демонтаж отменён", color=DARK_THEME_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)

async def send_pvo_move_log(bot_instance, move_task: Dict):
    try:
        channel = bot_instance.get_channel(PVO_MOVE_LOG_CHANNEL_ID)
        if not channel:
            return
        embed = discord.Embed(title="Перемещение ПВО", description=f"**{move_task['quantity']}x {move_task['pvo_name']}**", color=discord.Color.blue())
        embed.add_field(name="Страна", value=move_task['country'], inline=True)
        embed.add_field(name="Из региона", value=move_task['from_region'], inline=True)
        embed.add_field(name="В регион", value=move_task['to_region'], inline=True)
        embed.add_field(name="Расстояние", value=f"{move_task['distance']} км", inline=True)
        embed.add_field(name="Время в пути", value=format_time(move_task.get('travel_time', 0)), inline=True)
        embed.add_field(name="Игрок", value=f"<@{move_task['user_id']}>", inline=True)
        embed.add_field(name="ID задачи", value=str(move_task['id']), inline=True)
        embed.set_footer(text=f"Начало: {move_task['start_time'][:19]}")
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Ошибка при отправке лога перемещения ПВО: {e}")

async def complete_pvo_move(move_task: Dict) -> bool:
    infra_data = load_infrastructure()
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == move_task["country"]:
            country_id = cid
            break
    if not country_id:
        return False
    regions = get_all_regions_from_country(infra_data, country_id)
    if move_task["to_region"] in regions:
        add_asset_to_region(regions[move_task["to_region"]], move_task["pvo_type"], move_task["country"], move_task["quantity"])
        if "economic_regions" in infra_data["infrastructure"][country_id]:
            for econ_region, econ_data in infra_data["infrastructure"][country_id]["economic_regions"].items():
                if move_task["to_region"] in econ_data.get("regions", {}):
                    econ_data["regions"][move_task["to_region"]] = regions[move_task["to_region"]]
                    break
        else:
            infra_data["infrastructure"][country_id]["regions"][move_task["to_region"]] = regions[move_task["to_region"]]
        save_infrastructure(infra_data)
        return True
    return False

async def complete_pvo_dismantle(dismantle_task: Dict) -> bool:
    states = load_states()
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == dismantle_task["user_id"]:
            player_data = data
            break
    if not player_data:
        return False
    add_army_pvo(player_data, dismantle_task["pvo_type"], dismantle_task["quantity"])
    infra_data = load_infrastructure()
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == dismantle_task["country"]:
            country_id = cid
            break
    if country_id:
        regions = get_all_regions_from_country(infra_data, country_id)
        if dismantle_task["region"] in regions:
            remove_asset_from_region(regions[dismantle_task["region"]], dismantle_task["pvo_type"], dismantle_task["country"], dismantle_task["quantity"])
            if "economic_regions" in infra_data["infrastructure"][country_id]:
                for econ_region, econ_data in infra_data["infrastructure"][country_id]["economic_regions"].items():
                    if dismantle_task["region"] in econ_data.get("regions", {}):
                        econ_data["regions"][dismantle_task["region"]] = regions[dismantle_task["region"]]
                        break
            else:
                infra_data["infrastructure"][country_id]["regions"][dismantle_task["region"]] = regions[dismantle_task["region"]]
            save_infrastructure(infra_data)
    save_states(states)
    return True

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ИНФРАСТРУКТУРОЙ ====================

def load_infrastructure():
    try:
        with open(INFRASTRUCTURE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"infrastructure": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"infrastructure": {}}

def save_infrastructure(data):
    with open(INFRASTRUCTURE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_all_regions_from_country(infra_data, country_id):
    regions = {}
    country_data = infra_data["infrastructure"].get(country_id, {})
    if "economic_regions" in country_data:
        for econ_region_name, econ_region_data in country_data["economic_regions"].items():
            if "regions" in econ_region_data:
                for region_name, region_data in econ_region_data["regions"].items():
                    regions[region_name] = region_data
    elif "regions" in country_data:
        regions = country_data["regions"]
    return regions

def is_region_coastal(region_data):
    return region_data.get("coastal", False)

def calculate_power_generation(region_data):
    total_power = 0
    fuel_consumption = {}
    power_plants = ["thermal_power", "hydro_power", "solar_power", "nuclear_power", "wind_power"]
    for plant_type in power_plants:
        if plant_type in region_data:
            count = get_asset_total(region_data, plant_type)
            if count > 0 and plant_type in INFRASTRUCTURE_COSTS:
                plant_data = INFRASTRUCTURE_COSTS[plant_type]
                total_power += count * plant_data["power_output"]
                if "fuel_consumption" in plant_data:
                    for fuel, amount in plant_data["fuel_consumption"].items():
                        fuel_consumption[fuel] = fuel_consumption.get(fuel, 0) + count * amount
    return total_power, fuel_consumption

def calculate_production_bonus(region_data, product_type, country_name: str = None):
    bonus = 1.0
    for infra_type, infra_data in INFRASTRUCTURE_COSTS.items():
        if infra_type in region_data and "production_bonus" in infra_data:
            count = get_asset_total(region_data, infra_type)
            if count > 0:
                for prod_category, bonus_value in infra_data["production_bonus"].items():
                    if prod_category in product_type or (prod_category == "civil" and "civil" in product_type):
                        bonus += count * bonus_value
    return bonus

# ==================== НОВОЕ МЕНЮ С КАТЕГОРИЯМИ ====================

async def show_region_categories(interaction, user_id, country_name, region_name, region_data):
    embed = create_embed(
        title=f"Регион: {region_name}",
        description=f"Страна: {country_name}"
    )
    
    image_url = get_region_image(country_name)
    if image_url:
        embed.set_image(url=image_url)
    
    population = region_data.get("population", 0)
    development = region_data.get("development_level", 0)
    coastal = "Да" if region_data.get("coastal", False) else "Нет"
    
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['population']} Население", value=format_number(population), inline=True)
    embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['development_level']} Развитие", value=f"{development}%", inline=True)
    embed.add_field(name=f"{GENERAL_EMOJIS['coastal']} Выход к морю", value=coastal, inline=True)
    
    total_facilities = count_infrastructure_facilities(region_data)
    total_power, _ = calculate_power_generation(region_data)
    embed.add_field(name="Объектов инфраструктуры", value=str(total_facilities), inline=True)
    embed.add_field(name=f"{GENERAL_EMOJIS['power_generation']} Генерация энергии", value=f"{total_power:.0f} МВт", inline=True)
    
    select = RegionCategorySelect(user_id, country_name, region_name, region_data)
    view = View(timeout=1800)
    view.add_item(select)
    
    if hasattr(interaction, 'response') and not interaction.response.is_done():
        await interaction.response.edit_message(embed=embed, view=view)
    else:
        await interaction.message.edit(embed=embed, view=view)

class RegionCategorySelect(Select):
    def __init__(self, user_id, country_name, region_name, region_data):
        self.user_id = user_id
        self.country_name = country_name
        self.region_name = region_name
        self.region_data = region_data
        
        options = [
            discord.SelectOption(label="Управление инфраструктурой", value="infrastructure", description="Строительство, перемещение и демонтаж ПВО"),
            discord.SelectOption(label="Обзор региона", value="overview", description="Полная статистика и показатели региона"),
            discord.SelectOption(label="Вооружённые силы", value="military", description="Размещённые войска и укрепления"),
            discord.SelectOption(label="Назад", value="back", description="Вернуться к списку регионов"),
        ]
        
        super().__init__(placeholder="Выберите категорию...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        category = self.values[0]
        
        if category == "infrastructure":
            await self.show_infrastructure_management(interaction)
        elif category == "overview":
            await self.show_region_overview(interaction)
        elif category == "military":
            await self.show_military_forces(interaction)
        elif category == "back":
            await self.go_back_to_regions(interaction)
    
    async def show_infrastructure_management(self, interaction: discord.Interaction):
        embed = create_embed(
            title=f"Управление инфраструктурой: {self.region_name}",
            description="Выберите действие:"
        )
        
        image_url = get_region_image(self.country_name)
        if image_url:
            embed.set_image(url=image_url)
        
        current_text = ""
        total_facilities = 0
        total_power_generation = 0
        total_fuel = {}
        
        for infra_type in ASSET_FIELDS:
            if infra_type in self.region_data:
                amount = get_asset_total(self.region_data, infra_type)
                if amount > 0 and infra_type in INFRASTRUCTURE_COSTS:
                    emoji = INFRASTRUCTURE_COSTS[infra_type].get("emoji", "")
                    current_text += f"{emoji} {INFRASTRUCTURE_COSTS[infra_type]['name']}: {amount}\n"
                    total_facilities += amount
                    
                    if infra_type in ["thermal_power", "hydro_power", "solar_power", "nuclear_power", "wind_power"]:
                        total_power_generation += amount * INFRASTRUCTURE_COSTS[infra_type]["power_output"]
                        
                        if "fuel_consumption" in INFRASTRUCTURE_COSTS[infra_type]:
                            for fuel, fuel_amount in INFRASTRUCTURE_COSTS[infra_type]["fuel_consumption"].items():
                                total_fuel[fuel] = total_fuel.get(fuel, 0) + amount * fuel_amount
        
        if current_text:
            embed.add_field(name="Текущая инфраструктура", value=current_text, inline=False)
            embed.add_field(name="Всего объектов", value=str(total_facilities), inline=True)
            
            if total_power_generation > 0:
                embed.add_field(name=f"{GENERAL_EMOJIS['power_generation']} Генерация энергии", value=f"{total_power_generation:.0f} МВт", inline=True)
            
            if total_fuel:
                fuel_text = ""
                fuel_emojis = {
                    "coal": GENERAL_EMOJIS.get("coal", ""),
                    "oil": GENERAL_EMOJIS.get("oil", ""),
                    "gas": GENERAL_EMOJIS.get("gas", ""),
                    "uranium": GENERAL_EMOJIS.get("uranium", "")
                }
                for fuel, amount in total_fuel.items():
                    fuel_emoji = fuel_emojis.get(fuel, "")
                    fuel_names = {"coal": "Уголь", "oil": "Нефть", "gas": "Газ", "uranium": "Уран"}
                    fuel_name = fuel_names.get(fuel, fuel)
                    fuel_text += f"{fuel_emoji} {fuel_name}: {amount:.3f}/день\n"
                embed.add_field(name="Потребление топлива", value=fuel_text, inline=False)
        else:
            embed.add_field(name="Текущая инфраструктура", value="Нет построенных объектов", inline=False)
        
        foreign_assets_text = get_foreign_assets_text(self.region_data, self.country_name)
        embed.add_field(name="Иностранные активы", value=foreign_assets_text, inline=False)
        
        pvo_text = get_region_pvo_text(self.region_data)
        embed.add_field(name="Противовоздушная оборона", value=pvo_text, inline=False)
        
        view = InfrastructureActionsView(
            self.user_id, self.country_name, self.region_name, 
            self.region_data, self
        )
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_region_overview(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title=f"Обзор региона: {self.region_name}",
            description=f"Страна: {self.country_name}",
            color=DARK_THEME_COLOR
        )
        
        image_url = get_region_image(self.country_name)
        if image_url:
            embed.set_image(url=image_url)
        
        detail_embed = get_region_detailed_info(self.region_data, self.country_name)
        for field in detail_embed.fields:
            embed.add_field(name=field.name, value=field.value, inline=field.inline)
        
        current_text = ""
        total_facilities = 0
        total_power_generation = 0
        
        for infra_type in ASSET_FIELDS:
            if infra_type in self.region_data:
                amount = get_asset_total(self.region_data, infra_type)
                if amount > 0 and infra_type in INFRASTRUCTURE_COSTS:
                    emoji = INFRASTRUCTURE_COSTS[infra_type].get("emoji", "")
                    current_text += f"{emoji} {INFRASTRUCTURE_COSTS[infra_type]['name']}: {amount}\n"
                    total_facilities += amount
                    
                    if infra_type in ["thermal_power", "hydro_power", "solar_power", "nuclear_power", "wind_power"]:
                        total_power_generation += amount * INFRASTRUCTURE_COSTS[infra_type]["power_output"]
        
        if current_text:
            embed.add_field(name="Инфраструктура", value=current_text, inline=False)
            embed.add_field(name="Всего объектов", value=str(total_facilities), inline=True)
            if total_power_generation > 0:
                embed.add_field(name=f"{GENERAL_EMOJIS['power_generation']} Генерация энергии", value=f"{total_power_generation:.0f} МВт", inline=True)
        
        pvo_text = get_region_pvo_text(self.region_data)
        embed.add_field(name="Противовоздушная оборона", value=pvo_text, inline=False)
        
        storage_capacity = calculate_storage_capacity(self.region_data)
        if storage_capacity:
            storage_text = ""
            for res, cap in storage_capacity.items():
                res_emoji = GENERAL_EMOJIS.get(res, "")
                res_names = {"oil": "Нефть", "gas": "Газ"}
                storage_text += f"{res_emoji} {res_names.get(res, res)}: {format_number(cap)}\n"
            embed.add_field(name=f"{GENERAL_EMOJIS['storage_capacity']} Ёмкость хранилищ", value=storage_text, inline=True)
        
        view = View(timeout=1800)
        back_button = Button(label="Назад к категориям", style=discord.ButtonStyle.secondary)
        back_button.callback = lambda i: self.back_to_categories(i)
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_military_forces(self, interaction: discord.Interaction):
        embed = create_embed(
            title=f"Вооружённые силы: {self.region_name}",
            description="*Раздел находится в разработке*\n\n"
                        "Здесь будет отображаться информация о размещённых войсках, "
                        "укреплениях, военных базах и аэродромах."
        )
        
        image_url = get_region_image(self.country_name)
        if image_url:
            embed.set_image(url=image_url)
        
        view = View(timeout=1800)
        back_button = Button(label="Назад к категориям", style=discord.ButtonStyle.secondary)
        back_button.callback = lambda i: self.back_to_categories(i)
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_categories(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        embed = create_embed(
            title=f"Регион: {self.region_name}",
            description=f"Страна: {self.country_name}"
        )
        
        image_url = get_region_image(self.country_name)
        if image_url:
            embed.set_image(url=image_url)
        
        population = self.region_data.get("population", 0)
        development = self.region_data.get("development_level", 0)
        coastal = "Да" if self.region_data.get("coastal", False) else "Нет"
        
        embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['population']} Население", value=format_number(population), inline=True)
        embed.add_field(name=f"{DEMOGRAPHIC_EMOJIS['development_level']} Развитие", value=f"{development}%", inline=True)
        embed.add_field(name=f"{GENERAL_EMOJIS['coastal']} Выход к морю", value=coastal, inline=True)
        
        total_facilities = count_infrastructure_facilities(self.region_data)
        total_power, _ = calculate_power_generation(self.region_data)
        embed.add_field(name="Объектов инфраструктуры", value=str(total_facilities), inline=True)
        embed.add_field(name=f"{GENERAL_EMOJIS['power_generation']} Генерация энергии", value=f"{total_power:.0f} МВт", inline=True)
        
        view = View(timeout=1800)
        view.add_item(self)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def go_back_to_regions(self, interaction: discord.Interaction):
        await safe_delete(interaction.message)
        
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data["infrastructure"].items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        
        if country_id:
            economic_regions = infra_data["infrastructure"][country_id].get("economic_regions", {})
            
            econ_region = None
            for econ_name, econ_data in economic_regions.items():
                if self.region_name in econ_data.get("regions", {}):
                    econ_region = econ_name
                    break
            
            if econ_region and econ_region in economic_regions:
                regions = economic_regions[econ_region].get("regions", {})
                view = RegionSelectView(self.country_name, econ_region, regions, self.user_id)
                embed = create_embed(
                    title=f"Регионы: {econ_region}",
                    description="Выберите регион для управления:"
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                return
        
        await show_infrastructure_menu(interaction)

class InfrastructureActionsView(View):
    def __init__(self, user_id, country_name, region_name, region_data, parent_select):
        super().__init__(timeout=1800)
        self.user_id = user_id
        self.country_name = country_name
        self.region_name = region_name
        self.region_data = region_data
        self.parent_select = parent_select
        
        build_button = Button(label="Строительство", style=discord.ButtonStyle.primary)
        build_button.callback = self.build_callback
        self.add_item(build_button)
        
        sell_button = Button(label="Продажа", style=discord.ButtonStyle.success)
        sell_button.callback = self.sell_callback
        self.add_item(sell_button)
        
        has_pvo = (
            get_asset_total(region_data, "long_range_air_defense") > 0 or
            get_asset_total(region_data, "short_range_air_defense") > 0 or
            get_asset_total(region_data, "zdprk") > 0 or
            get_asset_total(region_data, "zas") > 0 or
            get_asset_total(region_data, "radar_systems") > 0
        )
        
        if has_pvo:
            move_pvo_button = Button(label="Переместить ПВО", style=discord.ButtonStyle.secondary)
            move_pvo_button.callback = self.move_pvo_callback
            self.add_item(move_pvo_button)
            
            dismantle_pvo_button = Button(label="Демонтировать ПВО", style=discord.ButtonStyle.danger)
            dismantle_pvo_button.callback = self.dismantle_pvo_callback
            self.add_item(dismantle_pvo_button)
        
        back_button = Button(label="Назад к категориям", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    async def build_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await safe_delete(interaction.message)
        
        view = InfrastructureTypeView(self.country_name, self.region_name, self.region_data, self.user_id)
        embed = create_embed(
            title=f"Строительство в регионе: {self.region_name}",
            description="Выберите тип инфраструктуры для строительства:"
        )
        await send_ephemeral(interaction, embed=embed, view=view)
    
    async def sell_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        states = load_states()
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("У вас нет государства!", ephemeral=True)
            return
        
        await show_asset_sale_info(interaction, self.user_id, player_data)
    
    async def move_pvo_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await show_move_pvo_from_region(interaction, self.user_id, self.country_name, self.region_name, self.region_data)
    
    async def dismantle_pvo_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await show_dismantle_pvo_menu(interaction, self.user_id, self.country_name, self.region_name, self.region_data)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await self.parent_select.back_to_categories(interaction)

class RegionSelectView(View):
    def __init__(self, country_name, econ_region, regions, user_id):
        super().__init__(timeout=1800)
        self.country_name = country_name
        self.econ_region = econ_region
        self.user_id = user_id
        
        select = RegionSelect(country_name, econ_region, regions, user_id)
        self.add_item(select)
        
        back_button = Button(label="Назад к районам", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await safe_delete(interaction.message)
        await show_infrastructure_menu(interaction)

class RegionSelect(Select):
    def __init__(self, country_name, econ_region, regions, user_id):
        self.country_name = country_name
        self.econ_region = econ_region
        self.regions = regions
        self.user_id = user_id
        
        options = []
        sorted_regions = sorted(regions.items(), key=lambda x: x[0])
        
        for region_name, region_data in sorted_regions[:25]:
            facilities = count_infrastructure_facilities(region_data)
            population = format_number(region_data.get("population", 0))
            label = region_name[:100]
            description = f"Население: {population} | Объектов: {facilities}"
            options.append(discord.SelectOption(label=label, description=description[:100], value=region_name))
        
        super().__init__(placeholder="Выберите регион для управления...", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        region_name = self.values[0]
        region_data = self.regions[region_name]
        region_data['economic_region'] = self.econ_region
        
        await safe_delete(interaction.message)
        await show_region_categories(interaction, self.user_id, self.country_name, region_name, region_data)

class InfrastructureTypeView(View):
    def __init__(self, country_name, region, region_data, user_id):
        super().__init__(timeout=1800)
        self.country_name = country_name
        self.region = region
        self.region_data = region_data
        self.user_id = user_id
        
        for infra_type, data in INFRASTRUCTURE_COSTS.items():
            if data.get("requires_coastal", False) and not is_region_coastal(region_data):
                button = Button(label=f"{data['name']} (требуется море)", style=discord.ButtonStyle.secondary, disabled=True)
                button.callback = self.create_disabled_callback(data['name'])
            else:
                emoji = data.get("emoji", "")
                button = Button(label=f"{emoji} {data['name']}" if emoji else data['name'], style=discord.ButtonStyle.secondary)
                button.callback = self.create_callback(infra_type, data)
            self.add_item(button)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    def create_disabled_callback(self, infra_name):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            await interaction.response.send_message(f"{infra_name} можно строить только в регионах с выходом к морю!", ephemeral=True)
        return callback
    
    def create_callback(self, infra_type, data):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            
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
                current_count = get_asset_total(region_data, infra_type)
            
            if current_count >= data['max_per_region']:
                await interaction.response.send_message(
                    f"В регионе {self.region} достигнут лимит по {data['name']}! Максимум: {data['max_per_region']}",
                    ephemeral=True
                )
                return
            
            await safe_delete(interaction.message)
            
            view = QuantitySelector(self.country_name, self.region, infra_type, data, self.user_id)
            
            emoji = data.get("emoji", "")
            embed = create_embed(
                title=f"{emoji} {data['name']}" if emoji else data['name'],
                description=data['description']
            )
            
            embed.add_field(name="Стоимость", value=format_infra_cost(data['cost']), inline=True)
            embed.add_field(name="Время", value=format_time(data['build_time']), inline=True)
            embed.add_field(name="Лимит в регионе", value=f"{current_count}/{data['max_per_region']}", inline=True)
            
            if data.get("pvo_type", False):
                embed.add_field(name="Важно", value="Требуется 1 единица техники из арсенала для установки", inline=False)
            
            if "production_bonus" in data:
                bonus_text = ""
                for prod, bonus in data["production_bonus"].items():
                    bonus_text += f"• {prod}: +{bonus*100:.0f}% скорости\n"
                embed.add_field(name="Эффект", value=bonus_text, inline=False)
            
            if "power_output" in data:
                embed.add_field(name="Выработка", value=f"{data['power_output']} МВт", inline=True)
                
                if "fuel_consumption" in data and data["fuel_consumption"]:
                    fuel_text = ""
                    fuel_emojis = {
                        "coal": GENERAL_EMOJIS.get("coal", ""),
                        "oil": GENERAL_EMOJIS.get("oil", ""),
                        "gas": GENERAL_EMOJIS.get("gas", ""),
                        "uranium": GENERAL_EMOJIS.get("uranium", "")
                    }
                    for fuel, amount in data["fuel_consumption"].items():
                        fuel_emoji = fuel_emojis.get(fuel, "")
                        fuel_names = {"coal": "Уголь", "oil": "Нефть", "gas": "Газ", "uranium": "Уран"}
                        fuel_name = fuel_names.get(fuel, fuel)
                        fuel_text += f"{fuel_emoji} {fuel_name}: {amount}/день\n"
                    embed.add_field(name="Потребление топлива", value=fuel_text, inline=True)
            
            await send_ephemeral(interaction, embed=embed, view=view)
        return callback
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await safe_delete(interaction.message)
        
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
        
        await show_region_categories(interaction, self.user_id, self.country_name, self.region, region_data)

class QuantitySelector(View):
    def __init__(self, country_name, region, infra_type, infra_data, user_id):
        super().__init__(timeout=1800)
        self.country_name = country_name
        self.region = region
        self.infra_type = infra_type
        self.infra_data = infra_data
        self.user_id = user_id
        self.quantity = 1
        
        minus_button = Button(label="-", style=discord.ButtonStyle.secondary)
        minus_button.callback = self.decrease_quantity
        self.add_item(minus_button)
        
        self.quantity_label = Button(label=f"{self.quantity}", style=discord.ButtonStyle.secondary, disabled=True)
        self.add_item(self.quantity_label)
        
        plus_button = Button(label="+", style=discord.ButtonStyle.secondary)
        plus_button.callback = self.increase_quantity
        self.add_item(plus_button)
        
        manual_button = Button(label="Ввести число", style=discord.ButtonStyle.secondary)
        manual_button.callback = self.manual_input
        self.add_item(manual_button)
        
        build_button = Button(label="Начать строительство", style=discord.ButtonStyle.secondary)
        build_button.callback = self.confirm_build
        self.add_item(build_button)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.go_back
        self.add_item(back_button)
    
    async def decrease_quantity(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.label = str(self.quantity)
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()
    
    async def increase_quantity(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
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
            current_count = get_asset_total(region_data, self.infra_type)
        
        max_allowed = self.infra_data['max_per_region'] - current_count
        if self.quantity < max_allowed:
            self.quantity += 1
            self.quantity_label.label = str(self.quantity)
            await self.update_embed(interaction)
        else:
            await interaction.response.send_message(
                f"Достигнут лимит! В регионе можно построить максимум {self.infra_data['max_per_region']} (осталось {max_allowed})",
                ephemeral=True
            )
    
    async def manual_input(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        modal = QuantityModal(self.country_name, self.region, self.infra_type, self.infra_data, self.user_id, interaction.message)
        await interaction.response.send_modal(modal)
    
    async def update_embed(self, interaction):
        total_cost = self.infra_data['cost'] * self.quantity
        total_time = self.infra_data['build_time'] * self.quantity
        
        emoji = self.infra_data.get("emoji", "")
        embed = create_embed(
            title=f"{emoji} {self.infra_data['name']}" if emoji else self.infra_data['name'],
            description=self.infra_data['description']
        )
        
        embed.add_field(name="Цена за ед.", value=format_infra_cost(self.infra_data['cost']), inline=True)
        embed.add_field(name="Количество", value=str(self.quantity), inline=True)
        embed.add_field(name="Общая стоимость", value=format_infra_cost(total_cost), inline=True)
        embed.add_field(name="Время", value=format_time(total_time), inline=True)
        embed.add_field(name="Регион", value=self.region, inline=True)
        
        if self.infra_data.get("pvo_type", False):
            embed.add_field(name="Важно", value=f"Потребуется {self.quantity} единиц из арсенала", inline=False)
        
        if "production_bonus" in self.infra_data:
            bonus_text = ""
            for prod, bonus in self.infra_data["production_bonus"].items():
                bonus_text += f"• {prod}: +{bonus*100*self.quantity:.0f}% скорости\n"
            embed.add_field(name="Итоговый эффект", value=bonus_text, inline=False)
        
        if "power_output" in self.infra_data:
            embed.add_field(name="Выработка", value=f"{self.infra_data['power_output'] * self.quantity} МВт", inline=True)
        
        if "fuel_consumption" in self.infra_data and self.infra_data["fuel_consumption"]:
            fuel_text = ""
            fuel_emojis = {
                "coal": GENERAL_EMOJIS.get("coal", ""),
                "oil": GENERAL_EMOJIS.get("oil", ""),
                "gas": GENERAL_EMOJIS.get("gas", ""),
                "uranium": GENERAL_EMOJIS.get("uranium", "")
            }
            for fuel, amount in self.infra_data["fuel_consumption"].items():
                fuel_emoji = fuel_emojis.get(fuel, "")
                fuel_names = {"coal": "Уголь", "oil": "Нефть", "gas": "Газ", "uranium": "Уран"}
                fuel_name = fuel_names.get(fuel, fuel)
                fuel_text += f"{fuel_emoji} {fuel_name}: {amount * self.quantity:.3f}/день\n"
            embed.add_field(name="Потребление топлива", value=fuel_text, inline=True)
        
        await update_ephemeral(interaction, embed=embed, view=self)
    
    async def confirm_build(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(interaction.user.id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("У вас нет государства!", ephemeral=True)
            return
        
        total_cost_millions = self.infra_data['cost'] * self.quantity
        total_cost_dollars = total_cost_millions * 1_000_000
        
        from utils import get_budget, subtract_from_budget
        current_budget = get_budget(player_data["economy"])
        if total_cost_millions > 0 and current_budget < total_cost_dollars:
            await interaction.response.send_message(
                f"Недостаточно средств! Нужно: {format_infra_cost(total_cost_millions)}, доступно: {format_billion(current_budget)}",
                ephemeral=True
            )
            return
        
        if self.infra_data.get("pvo_type", False):
            ok, msg = can_build_pvo(player_data, self.infra_type, self.quantity)
            if not ok:
                await interaction.response.send_message(f"{msg}", ephemeral=True)
                return
            
            if not consume_army_pvo(player_data, self.infra_type, self.quantity):
                await interaction.response.send_message("Ошибка при списании ПВО из арсенала!", ephemeral=True)
                return
        
        if total_cost_millions > 0:
            subtract_from_budget(player_data["economy"], total_cost_dollars)
        
        save_states(states)
        
        await safe_delete(interaction.message)
        
        view = BuildConfirmation(self.country_name, self.region, self.infra_type, self.infra_data, self.quantity, self.user_id)
        
        emoji = self.infra_data.get("emoji", "")
        embed = create_embed(
            title="Подтверждение строительства",
            description=f"Проект: {self.quantity}x {emoji} {self.infra_data['name']} в регионе {self.region}" if emoji else f"Проект: {self.quantity}x {self.infra_data['name']} в регионе {self.region}"
        )
        
        if total_cost_millions > 0:
            embed.add_field(name="Стоимость", value=format_infra_cost(total_cost_millions), inline=True)
        else:
            embed.add_field(name="Стоимость", value="Бесплатно (списано из арсенала)", inline=True)
        
        embed.add_field(name="Время", value=format_time(self.infra_data['build_time'] * self.quantity), inline=True)
        
        if self.infra_data.get("pvo_type", False):
            embed.add_field(name="Важно", value=f"Списано {self.quantity} единиц {self.infra_data['name']} из арсенала", inline=False)
        
        if "power_output" in self.infra_data:
            embed.add_field(name="Выработка", value=f"{self.infra_data['power_output'] * self.quantity} МВт", inline=True)
        
        await send_ephemeral(interaction, embed=embed, view=view)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await safe_delete(interaction.message)
        
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
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > 100:
                await interaction.response.send_message("Количество должно быть от 1 до 100!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("Введите корректное число!", ephemeral=True)
            return
        
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
            current_count = get_asset_total(region_data, self.infra_type)
        
        max_allowed = self.infra_data['max_per_region'] - current_count
        if quantity > max_allowed:
            await interaction.response.send_message(
                f"Превышение лимита! В регионе можно построить максимум {self.infra_data['max_per_region']} (осталось {max_allowed})",
                ephemeral=True
            )
            return
        
        await safe_delete(self.original_message)
        
        view = BuildConfirmation(self.country_name, self.region, self.infra_type, self.infra_data, quantity, self.user_id)
        
        total_cost = self.infra_data['cost'] * quantity
        total_time = self.infra_data['build_time'] * quantity
        
        emoji = self.infra_data.get("emoji", "")
        embed = create_embed(
            title=f"{emoji} {self.infra_data['name']}" if emoji else self.infra_data['name'],
            description="Подтвердите строительство:"
        )
        
        embed.add_field(name="Регион", value=self.region, inline=True)
        embed.add_field(name="Количество", value=str(quantity), inline=True)
        
        if total_cost > 0:
            embed.add_field(name="Общая стоимость", value=format_infra_cost(total_cost), inline=True)
        else:
            embed.add_field(name="Стоимость", value="Бесплатно (требуется техника из арсенала)", inline=True)
        
        embed.add_field(name="Время", value=format_time(total_time), inline=True)
        
        if self.infra_data.get("pvo_type", False):
            embed.add_field(name="Важно", value=f"Потребуется {quantity} единиц из арсенала", inline=False)
        
        await send_ephemeral(interaction, embed=embed, view=view)

class BuildConfirmation(View):
    def __init__(self, country_name, region, infra_type, infra_data, quantity, user_id):
        super().__init__(timeout=1800)
        self.country_name = country_name
        self.region = region
        self.infra_type = infra_type
        self.infra_data = infra_data
        self.quantity = quantity
        self.user_id = user_id
        
        confirm_button = Button(label="Подтвердить", style=discord.ButtonStyle.success)
        confirm_button.callback = self.confirm
        self.add_item(confirm_button)
        
        cancel_button = Button(label="Отмена", style=discord.ButtonStyle.secondary)
        cancel_button.callback = self.cancel
        self.add_item(cancel_button)
    
    async def confirm(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        queue = load_construction_queue()
        
        total_time = self.infra_data['build_time'] * self.quantity
        completion_time = datetime.now() + timedelta(seconds=total_time)
        
        project = {
            "id": len(queue["active_projects"]) + 1,
            "user_id": str(self.user_id),
            "user_name": interaction.user.name,
            "country": self.country_name,
            "region": self.region,
            "infra_type": self.infra_type,
            "infra_name": self.infra_data['name'],
            "quantity": self.quantity,
            "total_cost": self.infra_data['cost'] * self.quantity * 1_000_000,
            "start_time": str(datetime.now()),
            "completion_time": str(completion_time),
            "status": "in_progress",
            "notified": False,
            "pvo_type": self.infra_data.get("pvo_type", False)
        }
        
        queue["active_projects"].append(project)
        save_construction_queue(queue)
        
        await safe_delete(interaction.message)
        
        emoji = self.infra_data.get("emoji", "")
        embed = create_embed(
            title="Строительство начато!",
            description=f"Проект: {self.quantity}x {emoji} {self.infra_data['name']}" if emoji else f"Проект: {self.quantity}x {self.infra_data['name']}"
        )
        
        embed.add_field(name="Регион", value=self.region, inline=True)
        if self.infra_data['cost'] > 0:
            embed.add_field(name="Стоимость", value=format_infra_cost(self.infra_data['cost'] * self.quantity), inline=True)
        else:
            embed.add_field(name="Стоимость", value="Бесплатно (списано из арсенала)", inline=True)
        embed.add_field(name="Готовность", value=format_time(total_time), inline=True)
        embed.add_field(name="ID проекта", value=str(project['id']), inline=True)
        
        if self.infra_data.get("pvo_type", False):
            embed.add_field(name="Важно", value=f"Списано {self.quantity} единиц {self.infra_data['name']} из арсенала", inline=False)
        
        if "power_output" in self.infra_data:
            embed.add_field(name="Выработка", value=f"{self.infra_data['power_output'] * self.quantity} МВт", inline=True)
        
        await send_ephemeral(interaction, embed=embed)
    
    async def cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        await safe_delete(interaction.message)
        
        embed = create_embed(title="Строительство отменено", color=DARK_THEME_COLOR)
        await send_ephemeral(interaction, embed=embed)

class EconomicRegionSelect(Select):
    def __init__(self, economic_regions, country_name, user_id, original_message):
        self.user_id = user_id
        self.country_name = country_name
        self.original_message = original_message
        
        options = []
        for econ_region_name in list(economic_regions.keys())[:25]:
            region_count = len(economic_regions[econ_region_name].get("regions", {}))
            options.append(discord.SelectOption(
                label=econ_region_name[:100],
                description=f"Регионов: {region_count}",
                value=econ_region_name
            ))
        
        super().__init__(placeholder="Выберите экономический район...", min_values=1, max_values=1, options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = self.values[0]
        
        infra_data = load_infrastructure()
        country_id = None
        for cid, data in infra_data["infrastructure"].items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        
        if not country_id:
            await interaction.response.send_message("Ошибка загрузки данных страны!", ephemeral=True)
            return
        
        regions = infra_data["infrastructure"][country_id]["economic_regions"][econ_region]["regions"]
        
        await safe_delete(self.original_message)
        
        view = RegionSelectView(self.country_name, econ_region, regions, self.user_id)
        embed = create_embed(
            title=f"Регионы: {econ_region}",
            description="Выберите регион для управления:"
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==================== ОСНОВНЫЕ ФУНКЦИИ МЕНЮ ====================

async def show_infrastructure_menu(ctx):
    user_id = get_user_id(ctx)
    
    states = load_states()
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        await send_response(ctx, "У вас нет государства!", ephemeral=True)
        return
    
    country_name = player_data["state"]["statename"]
    
    infra_data = load_infrastructure()
    
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    
    if not country_id:
        await send_response(ctx, f"Для страны {country_name} нет данных инфраструктуры!", ephemeral=True)
        return
    
    country_data = infra_data["infrastructure"][country_id]
    
    embed = create_embed(
        title=f"Инфраструктура: {country_name}",
        description="Выберите экономический район для управления:"
    )
    
    if "economic_regions" in country_data:
        economic_regions = country_data["economic_regions"]
        
        region_stats = ""
        total_power = 0
        total_factories = 0
        total_pvo = {field: 0 for field in PVO_FIELDS}
        
        for econ_region_name, econ_region_data in list(economic_regions.items())[:5]:
            regions = econ_region_data.get("regions", {})
            region_count = len(regions)
            
            region_power = 0
            region_factories = 0
            region_pvo = {k: 0 for k in total_pvo.keys()}
            
            for region_data in regions.values():
                region_factories += count_infrastructure_facilities(region_data)
                power, _ = calculate_power_generation(region_data)
                region_power += power
                
                for pvo_type in total_pvo.keys():
                    region_pvo[pvo_type] += get_asset_total(region_data, pvo_type)
            
            total_factories += region_factories
            total_power += region_power
            for pvo_type in total_pvo.keys():
                total_pvo[pvo_type] += region_pvo[pvo_type]
            
            pvo_text = f" ПВО: {region_pvo['long_range_air_defense']}б/{region_pvo['short_range_air_defense']}м"
            region_stats += f"• {econ_region_name}: {region_count} регионов, {region_factories} объектов, {GENERAL_EMOJIS.get('power_generation', '')}{region_power} МВт{pvo_text}\n"
        
        embed.add_field(name="Доступные районы", value=region_stats, inline=False)
        embed.add_field(name="Всего объектов", value=str(total_factories), inline=True)
        embed.add_field(name=f"{GENERAL_EMOJIS['power_generation']} Общая генерация", value=f"{total_power} МВт", inline=True)
        
        pvo_total = total_pvo['long_range_air_defense'] + total_pvo['short_range_air_defense'] + total_pvo['zdprk'] + total_pvo['zas']
        embed.add_field(name="Всего ПВО", value=f"{pvo_total} (РЛС: {total_pvo['radar_systems']})", inline=True)
        
        if hasattr(ctx, 'response'):
            await ctx.response.send_message(embed=embed, ephemeral=True)
            message = await ctx.original_response()
        else:
            message = await ctx.send(embed=embed, ephemeral=True)
        
        select = EconomicRegionSelect(economic_regions, country_name, user_id, message)
        view = View(timeout=1800)
        view.add_item(select)
        
        await message.edit(view=view)
    else:
        await send_response(ctx, "Неподдерживаемая структура данных инфраструктуры!", ephemeral=True)

async def show_construction_projects(ctx):
    queue = load_construction_queue()
    user_id = get_user_id(ctx)
    user_projects = [p for p in queue["active_projects"] if p["user_id"] == str(user_id)]
    
    if not user_projects:
        await send_response(ctx, "У вас нет активных строительных проектов.", ephemeral=True)
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
            status = f"{format_time(remaining)} осталось\n{progress_bar}"
        else:
            status = "ГОТОВО К ЗАВЕРШЕНИЮ!"
        
        embed.add_field(
            name=f"Проект #{project['id']}: {project['quantity']}x {project['infra_name']}",
            value=f"{project['region']}\n{status}",
            inline=False
        )
    
    await send_response(ctx, embed=embed, ephemeral=True)

async def complete_construction_projects(ctx):
    queue = load_construction_queue()
    infra_data = load_infrastructure()
    states = load_states()
    
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
                    country_data = infra_data["infrastructure"][country_id]
                    region_found = False
                    
                    if "economic_regions" in country_data:
                        for econ_region_name, econ_region_data in country_data["economic_regions"].items():
                            if project["region"] in econ_region_data.get("regions", {}):
                                region_data = econ_region_data["regions"][project["region"]]
                                add_asset_to_region(region_data, project["infra_type"], project["country"], project["quantity"])
                                region_found = True
                                break
                        
                        if not region_found:
                            first_econ_region = list(country_data["economic_regions"].keys())[0]
                            if "regions" not in country_data["economic_regions"][first_econ_region]:
                                country_data["economic_regions"][first_econ_region]["regions"] = {}
                            if project["region"] not in country_data["economic_regions"][first_econ_region]["regions"]:
                                country_data["economic_regions"][first_econ_region]["regions"][project["region"]] = {}
                            region_data = country_data["economic_regions"][first_econ_region]["regions"][project["region"]]
                            add_asset_to_region(region_data, project["infra_type"], project["country"], project["quantity"])
                    else:
                        if project["region"] not in infra_data["infrastructure"][country_id]["regions"]:
                            infra_data["infrastructure"][country_id]["regions"][project["region"]] = {}
                        region_data = infra_data["infrastructure"][country_id]["regions"][project["region"]]
                        add_asset_to_region(region_data, project["infra_type"], project["country"], project["quantity"])
                    
                    project["status"] = "completed"
                    project["completed_at"] = str(now)
                    queue["completed_projects"].append(project)
                    queue["active_projects"].remove(project)
                    completed.append(project)
    
    if completed:
        save_infrastructure(infra_data)
        save_states(states)
        save_construction_queue(queue)
        
        embed = create_embed(
            title="Строительство завершено!",
            description=f"Завершено проектов: {len(completed)}"
        )
        
        for project in completed:
            embed.add_field(
                name=f"{project['quantity']}x {project['infra_name']}",
                value=f"{project['region']}\nОбъекты введены в эксплуатацию",
                inline=False
            )
        
        await send_response(ctx, embed=embed, ephemeral=True)
    else:
        await send_response(ctx, "Нет готовых проектов.", ephemeral=True)

async def construction_check_loop(bot_instance):
    await bot_instance.wait_until_ready()
    while not bot_instance.is_closed():
        try:
            queue = load_construction_queue()
            offers = load_asset_sale_offers()
            now = datetime.now()
            
            # Проверка истечения срока лотов
            for offer in offers["active_offers"][:]:
                if offer.get("expires_at"):
                    expires_at = datetime.fromisoformat(offer["expires_at"])
                    if expires_at <= now and offer["status"] == "pending":
                        await return_expired_assets_to_seller(offer)
                        offer["status"] = "expired"
                        offer["expired_at"] = str(now)
                        offers["completed_offers"].append(offer)
                        offers["active_offers"].remove(offer)
                        save_asset_sale_offers(offers)
                        
                        try:
                            user = await bot_instance.fetch_user(int(offer["seller_id"]))
                            if user:
                                asset_emoji = ASSET_EMOJIS.get(offer["asset_type"], "")
                                embed = discord.Embed(
                                    title=f"Срок действия лота истёк #{offer['id']}",
                                    description=f"Ваше предложение на продажу **{offer['quantity']} x {asset_emoji} {offer['asset_name']}** истекло.\n"
                                               f"Активы возвращены в регион **{offer['region_name']}**.",
                                    color=0xe67e22
                                )
                                await user.send(embed=embed)
                        except Exception as e:
                            print(f"Ошибка уведомления об истечении лота: {e}")
            
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
                    except Exception as e:
                        print(f"Ошибка уведомления: {e}")
                    project["notified"] = True
                    save_construction_queue(queue)
            
            for move in queue.get("active_moves", []):
                completion = datetime.fromisoformat(move["completion_time"])
                if completion <= now and not move.get("notified", False):
                    if await complete_pvo_move(move):
                        move["status"] = "completed"
                        move["completed_at"] = str(now)
                        move["notified"] = True
                        if "completed_moves" not in queue:
                            queue["completed_moves"] = []
                        queue["completed_moves"].append(move)
                        queue["active_moves"].remove(move)
                        save_construction_queue(queue)
                        
                        try:
                            user = await bot_instance.fetch_user(int(move["user_id"]))
                            if user:
                                embed = create_embed(
                                    title="Перемещение ПВО завершено!",
                                    description=f"**{move['quantity']}x {move['pvo_name']}** успешно перемещены из {move['from_region']} в {move['to_region']}"
                                )
                                await user.send(embed=embed)
                        except Exception as e:
                            print(f"Ошибка уведомления: {e}")
            
            for dismantle in queue.get("active_dismantles", []):
                completion = datetime.fromisoformat(dismantle["completion_time"])
                if completion <= now and not dismantle.get("notified", False):
                    if await complete_pvo_dismantle(dismantle):
                        dismantle["status"] = "completed"
                        dismantle["completed_at"] = str(now)
                        dismantle["notified"] = True
                        if "completed_dismantles" not in queue:
                            queue["completed_dismantles"] = []
                        queue["completed_dismantles"].append(dismantle)
                        queue["active_dismantles"].remove(dismantle)
                        save_construction_queue(queue)
                        
                        try:
                            user = await bot_instance.fetch_user(int(dismantle["user_id"]))
                            if user:
                                embed = create_embed(
                                    title="Демонтаж ПВО завершён!",
                                    description=f"**{dismantle['quantity']}x {dismantle['pvo_name']}** демонтированы и возвращены в арсенал"
                                )
                                await user.send(embed=embed)
                        except Exception as e:
                            print(f"Ошибка уведомления: {e}")
            
            await asyncio.sleep(60)
        except Exception as e:
            print(f"Ошибка в construction_check_loop: {e}")
            await asyncio.sleep(60)

async def show_move_pvo_menu(ctx, user_id: int):
    states = load_states()
    
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        await send_response(ctx, "У вас нет государства!", ephemeral=True)
        return
    
    country_name = player_data["state"]["statename"]
    
    infra_data = load_infrastructure()
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    
    if not country_id:
        await send_response(ctx, "Данные инфраструктуры не найдены!", ephemeral=True)
        return
    
    regions = get_all_regions_from_country(infra_data, country_id)
    
    regions_with_pvo = {}
    for region_name, region_data in regions.items():
        pvo_count = (
            get_asset_total(region_data, "long_range_air_defense") +
            get_asset_total(region_data, "short_range_air_defense") +
            get_asset_total(region_data, "zdprk") +
            get_asset_total(region_data, "zas") +
            get_asset_total(region_data, "radar_systems")
        )
        if pvo_count > 0:
            regions_with_pvo[region_name] = region_data
    
    if not regions_with_pvo:
        await send_response(ctx, "Нет регионов с установленным ПВО для перемещения!", ephemeral=True)
        return
    
    embed = create_embed(
        title="Перемещение ПВО",
        description="Выберите регион, из которого хотите переместить ПВО:",
        color=DARK_THEME_COLOR
    )
    
    for region_name, region_data in list(regions_with_pvo.items())[:10]:
        pvo_text = get_region_pvo_text(region_data)
        embed.add_field(name=region_name, value=pvo_text, inline=False)
    
    class MovePVOFromRegionSelect(Select):
        def __init__(self, user_id, country_name, regions_with_pvo):
            self.user_id = user_id
            self.country_name = country_name
            self.regions_with_pvo = regions_with_pvo
            
            options = []
            for region_name in list(regions_with_pvo.keys())[:25]:
                options.append(discord.SelectOption(label=region_name[:100], value=region_name))
            
            super().__init__(placeholder="Выберите регион...", options=options)
        
        async def callback(self, interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            
            from_region = self.values[0]
            await show_move_pvo_from_region(interaction, self.user_id, self.country_name, from_region, {})
    
    select = MovePVOFromRegionSelect(user_id, country_name, regions_with_pvo)
    view = View(timeout=600)
    view.add_item(select)
    
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx.send(embed=embed, view=view, ephemeral=True)

# ==================== ЭКСПОРТ ФУНКЦИЙ ====================

__all__ = [
    'INFRASTRUCTURE_COSTS', 'load_infrastructure', 'save_infrastructure',
    'load_construction_queue', 'save_construction_queue', 'format_time',
    'show_infrastructure_menu', 'show_construction_projects', 'complete_construction_projects',
    'construction_check_loop', 'calculate_production_bonus', 'calculate_power_generation',
    'calculate_research_bonus', 'calculate_gov_efficiency_bonus', 'calculate_pp_gain_bonus',
    'calculate_storage_capacity', 'get_army_pvo_count', 'consume_army_pvo', 'add_army_pvo',
    'get_region_pvo_text', 'show_move_pvo_menu',
    'get_asset_total', 'get_asset_ownership', 'set_asset_ownership',
    'add_asset_to_region', 'remove_asset_from_region', 'ASSET_FIELDS', 'PVO_FIELDS',
    'show_asset_sale_info', 'AssetSaleResponseView',
    'freeze_assets_on_embargo', 'unfreeze_assets_on_embargo_removal',
    'is_asset_frozen', 'set_asset_frozen'
]

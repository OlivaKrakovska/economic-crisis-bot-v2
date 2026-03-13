# strikes.py - Модуль для управления ударами БПЛА и стратегического оружия
# СБАЛАНСИРОВАННАЯ ВЕРСИЯ

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import asyncio
import json
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from infra_build import load_infrastructure, save_infrastructure, get_all_regions_from_country

from satellites import get_intercept_difficulty_boost

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

# Попытка импорта координат для fallback расчета
try:
    from region_coordinates import get_region_coordinates, region_exists
    COORDINATES_AVAILABLE = True
except ImportError:
    COORDINATES_AVAILABLE = False
    print("⚠️ Модуль region_coordinates не найден. Будет использоваться только файл distances.json")

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """
    Рассчитывает расстояние между двумя точками на Земле по формуле гаверсинуса
    Возвращает расстояние в километрах
    """
    R = 6371  # Радиус Земли в км
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return round(R * c)

def get_region_distance(attacker_country: str, attacker_region: str, 
                       target_country: str, target_region: str) -> int:
    """
    Возвращает расстояние между регионами в км
    Поддерживает симметрию и имеет многоуровневый fallback-механизм
    """
    distances = load_distances()
    
    # Уровень 1: Прямое расстояние в формате [attacker][target][attacker_region]
    try:
        return distances[attacker_country][target_country][attacker_region]
    except KeyError:
        pass
    
    # Уровень 2: Обратный формат (симметрия) [target][attacker][target_region]
    try:
        return distances[target_country][attacker_country][target_region]
    except KeyError:
        pass
    
    # Уровень 3: Если есть координаты, рассчитываем "на лету"
    if COORDINATES_AVAILABLE:
        try:
            attacker_coords = get_region_coordinates(attacker_country, attacker_region)
            target_coords = get_region_coordinates(target_country, target_region)
            
            if attacker_coords and target_coords:
                distance = haversine_distance(
                    attacker_coords["lat"], attacker_coords["lon"],
                    target_coords["lat"], target_coords["lon"]
                )
                print(f"✅ Рассчитано расстояние (по координатам): {attacker_country}.{attacker_region} -> {target_country}.{target_region} = {distance} км")
                return distance
        except Exception as e:
            print(f"Ошибка при расчете расстояния по координатам: {e}")
    
    # Уровень 4: Пробуем найти расстояние до страны в целом (если есть данные для любого региона)
    try:
        # Берем первый доступный регион атакующей страны
        if attacker_country in distances and target_country in distances[attacker_country]:
            any_region = list(distances[attacker_country][target_country].keys())[0]
            distance = distances[attacker_country][target_country][any_region]
            print(f"⚠️ Использовано расстояние от {any_region} до {target_country} как приближение")
            return distance
    except (KeyError, IndexError):
        pass
    
    # Уровень 5: Пробуем обратную симметрию с любым регионом
    try:
        if target_country in distances and attacker_country in distances[target_country]:
            any_region = list(distances[target_country][attacker_country].keys())[0]
            distance = distances[target_country][attacker_country][any_region]
            print(f"⚠️ Использовано обратное расстояние от {any_region} до {attacker_country} как приближение")
            return distance
    except (KeyError, IndexError):
        pass
    
    # Уровень 6: Если ничего не помогло, возвращаем большое число (блокируем удар)
    print(f"❌ Нет данных о расстоянии: {attacker_country}.{attacker_region} -> {target_country}.{target_region}")
    return 9999

def is_region_reachable(attacker_country: str, attacker_region: str,
                       target_country: str, target_region: str,
                       weapon_range: int) -> Tuple[bool, int]:
    """
    Проверяет, достижим ли целевой регион для данного оружия
    Возвращает (достижимо, расстояние)
    """
    distance = get_region_distance(attacker_country, attacker_region, target_country, target_region)
    return distance <= weapon_range, distance

def get_all_country_regions(country_name: str) -> List[str]:
    """
    Возвращает список всех регионов страны из инфраструктуры
    """
    infra = load_infrastructure()
    regions = []
    
    for cid, cdata in infra["infrastructure"].items():
        if cdata.get("country") == country_name:
            for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                for region_name in econ_data.get("regions", {}).keys():
                    regions.append(region_name)
            break
    
    return regions

# ==================== КОНСТАНТЫ ====================

# Типы вооружения для ударов
STRIKE_WEAPONS = {
    "kamikaze_uav": {
        "name": "Дроны-камикадзе",
        "description": "Барражирующие боеприпасы типа Shahed, Lancet. Дешёвые, производятся в большом количестве, но легко сбиваются.",
        "army_path": "air.kamikaze_drones",
        "base_accuracy": 0.55,
        "intercept_difficulty": 0.1,
        "min_destroy": 1,
        "max_destroy": 1,
        "infrastructure_damage_multiplier": 1.0,
        "cooldown": 3,
        "range": 1000,
        "salvo_size": 50
    },
    "drones": {
        "name": "Ударные БПЛА",
        "description": "Беспилотники средней дальности. Хорошая точность, умеренная стоимость.",
        "army_path": "air.attack_uav",
        "base_accuracy": 0.8,
        "intercept_difficulty": 0.2,
        "min_destroy": 1,
        "max_destroy": 1,
        "infrastructure_damage_multiplier": 1.0,
        "cooldown": 6,
        "range": 800,
        "salvo_size": 20
    },
    "recon_uav": {
        "name": "Разведывательные БПЛА",
        "description": "Лёгкие беспилотники. Могут нести небольшие боеприпасы, высокая точность.",
        "army_path": "air.recon_uav",
        "base_accuracy": 0.9,
        "intercept_difficulty": 0.15,
        "min_destroy": 1,
        "max_destroy": 1,
        "infrastructure_damage_multiplier": 0.8,
        "cooldown": 4,
        "range": 400,
        "salvo_size": 15
    },
    "cruise_missiles": {
        "name": "Крылатые ракеты",
        "description": "Дозвуковые ракеты, летят на малой высоте. Высокая точность, сложнее перехватить.",
        "army_path": "missiles.cruise_missiles",
        "base_accuracy": 0.9,
        "intercept_difficulty": 0.4,
        "min_destroy": 1,
        "max_destroy": 1,
        "infrastructure_damage_multiplier": 1.2,
        "cooldown": 24,
        "range": 2000,
        "salvo_size": 10
    },
    "ballistic_missiles": {
        "name": "Баллистические ракеты",
        "description": "Сверхзвуковые ракеты. Очень сложно перехватить, высокая скорость.",
        "army_path": "missiles.ballistic_missiles",
        "base_accuracy": 0.75,
        "intercept_difficulty": 0.7,
        "min_destroy": 1,
        "max_destroy": 1,
        "infrastructure_damage_multiplier": 1.5,
        "cooldown": 48,
        "range": 3000,
        "salvo_size": 5
    },
    "hypersonic_missiles": {
        "name": "Гиперзвуковые ракеты",
        "description": "Новейшее оружие. Почти невозможно перехватить, огромная скорость.",
        "army_path": "missiles.hypersonic_missiles",
        "base_accuracy": 0.85,
        "intercept_difficulty": 0.95,
        "min_destroy": 1,
        "max_destroy": 1,
        "infrastructure_damage_multiplier": 2.0,
        "cooldown": 72,
        "range": 2500,
        "salvo_size": 2
    }
}

# Типы целей для ударов - СБАЛАНСИРОВАННЫЕ ЗНАЧЕНИЯ
TARGET_TYPES = {
    # Военные объекты
    "military_factories": {
        "name": "Военные заводы",
        "description": "Производство военной техники и вооружения",
        "infra_fields": ["military_factories"],
        "priority": 1,
        "happiness_impact": 2,
        "stability_impact": 2,
        "civilian_casualty_chance": 0.6,  # 60% шанс
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
        "civilian_casualty_chance": 0.4,  # 40% шанс
        "civilian_casualty_base": 20,
        "target_value": 1.0,
        "fuel_loss": {}
    },
    "air_defense": {
        "name": "ПВО",
        "description": "Зенитные ракетные комплексы и артиллерия",
        "infra_fields": ["short_range_air_defense", "long_range_air_defense", "zdprk", "zas"],
        "priority": 1,
        "happiness_impact": 1,
        "stability_impact": 4,
        "civilian_casualty_chance": 0.5,  # 50% шанс
        "civilian_casualty_base": 30,
        "target_value": 1.3,
        "fuel_loss": {}
    },
    
    # Промышленные объекты
    "civilian_factories": {
        "name": "Гражданские фабрики",
        "description": "Производство гражданской продукции",
        "infra_fields": ["civilian_factories"],
        "priority": 2,
        "happiness_impact": 3,
        "stability_impact": 2,
        "civilian_casualty_chance": 0.7,  # 70% шанс
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
        "civilian_casualty_chance": 0.6,  # 60% шанс
        "civilian_casualty_base": 60,
        "target_value": 1.8,
        "fuel_loss": {}
    },
    
    # Нефтегазовый комплекс
    "refineries": {
        "name": "НПЗ",
        "description": "Нефтеперерабатывающие заводы",
        "infra_fields": ["refineries"],
        "priority": 1,
        "happiness_impact": 3,
        "stability_impact": 3,
        "civilian_casualty_chance": 0.8,  # 80% шанс (взрывоопасно)
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
        "civilian_casualty_chance": 0.7,  # 70% шанс
        "civilian_casualty_base": 80,
        "target_value": 1.5,
        "fuel_loss": ["oil", "gas"]
    },
    
    # Электростанции
    "thermal_power": {
        "name": "ТЭС",
        "description": "Тепловые электростанции",
        "infra_fields": ["thermal_power"],
        "priority": 1,
        "happiness_impact": 5,
        "stability_impact": 3,
        "civilian_casualty_chance": 0.6,  # 60% шанс
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
        "civilian_casualty_chance": 0.4,  # 40% шанс (меньше персонала)
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
        "civilian_casualty_chance": 0.3,  # 30% шанс
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
        "civilian_casualty_chance": 0.3,  # 30% шанс
        "civilian_casualty_base": 20,
        "target_value": 1.2,
        "fuel_loss": []
    },
    
    # Инфраструктура
    "data_centers": {
        "name": "ЦОД",
        "description": "Центры обработки данных и интернет-инфраструктура",
        "infra_fields": ["internet_infrastructure"],
        "priority": 2,
        "happiness_impact": 2,
        "stability_impact": 1,
        "civilian_casualty_chance": 0.4,  # 40% шанс
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
        "civilian_casualty_chance": 0.7,  # 70% шанс (много людей)
        "civilian_casualty_base": 100,
        "target_value": 1.0,
        "fuel_loss": {}
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
        # Fallback если модуль конфликтов не загружен
        all_countries = ["США", "Россия", "Китай", "Германия", "Великобритания", 
                         "Франция", "Япония", "Израиль", "Украина", "Иран"]
        return [c for c in all_countries if c != player_country]
    except Exception as e:
        print(f"Ошибка получения списка стран в состоянии войны: {e}")
        return []

# ==================== ФУНКЦИИ ДЛЯ РАСЧЁТА ПЕРЕХВАТА ====================

def calculate_air_defense_strength(target_country: str) -> float:
    states = load_states()
    
    target_data = None
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == target_country:
            target_data = data
            break
    
    if not target_data:
        return 0.0
    
    army = target_data.get("army", {})
    strength = 0.0
    
    ground = army.get("ground", {})
    strength += ground.get("short_range_air_defense", 0) * 3.0
    strength += ground.get("long_range_air_defense", 0) * 5.0
    strength += ground.get("zdprk", 0) * 2.0
    strength += ground.get("zas", 0) * 1.0
    strength += ground.get("radar_systems", 0) * 2.0
    
    air = army.get("air", {})
    strength += air.get("fighters", 0) * 1.5
    
    return strength

# В начале файла добавьте импорт
from satellites import get_intercept_difficulty_boost

# Затем найдите функцию calculate_interception_chance и измените её:
def calculate_interception_chance(weapon_type: str, target_country: str, quantity: int, attacker_country: str = None) -> Tuple[float, float]:
    """
    Рассчитывает шанс перехвата
    attacker_country - страна, наносящая удар (для учета её спутников)
    """
    defense_strength = calculate_air_defense_strength(target_country)
    weapon = STRIKE_WEAPONS[weapon_type]
    base_difficulty = weapon["intercept_difficulty"]
    
    # Применяем бонус от спутников атакующего (если есть)
    if attacker_country:
        satellite_boost = get_intercept_difficulty_boost(attacker_country)
        base_difficulty += satellite_boost
        # Ограничиваем, чтобы не стало больше 0.95
        base_difficulty = min(0.95, base_difficulty)
    
    if defense_strength <= 0:
        base_chance = 0.0
    else:
        base_chance = 1.0 - (1.0 / (1.0 + defense_strength / 30.0))
    
    base_chance = base_chance * (1.0 - base_difficulty)
    
    # Эффект насыщения ПВО при массовой атаке
    if quantity <= 1:
        saturation_factor = 1.0
    else:
        # Чем больше целей, тем ниже эффективность ПВО
        saturation_factor = 1.0 / math.log10(quantity + 9) * 2.0
        saturation_factor = max(0.3, min(1.0, saturation_factor))
    
    final_chance = base_chance * saturation_factor
    final_chance = max(0.01, min(0.98, final_chance))
    
    return base_chance, final_chance

# Также нужно обновить функцию calculate_surviving_weapons:
def calculate_surviving_weapons(weapon_type: str, target_country: str, quantity: int, attacker_country: str = None) -> Tuple[int, float, float]:
    """
    Рассчитывает количество выживших после ПВО
    """
    if quantity <= 0:
        return 0, 0.0, 0.0
    
    base_chance, final_chance = calculate_interception_chance(weapon_type, target_country, quantity, attacker_country)
    
    intercepted = 0
    for _ in range(quantity):
        if random.random() < final_chance:
            intercepted += 1
    
    surviving = quantity - intercepted
    
    return surviving, base_chance, final_chance

# ==================== ФУНКЦИИ ДЛЯ РАСЧЁТА УРОНА ====================

def count_targets_in_region(region_data: Dict, target_type: str) -> int:
    """Подсчитывает количество доступных целей в регионе"""
    target_info = TARGET_TYPES[target_type]
    total = 0
    
    for field in target_info["infra_fields"]:
        if field in region_data:
            value = region_data[field]
            if isinstance(value, (int, float)) and value > 0:
                total += value
    
    return total

def distribute_hits_among_targets(region_data: Dict, target_type: str, hits: int, weapon_id: str) -> Tuple[Dict, int, Dict]:
    """
    Распределяет попадания по целям
    1 попадание = 1 уничтоженный объект
    """
    target_info = TARGET_TYPES[target_type]
    weapon = STRIKE_WEAPONS[weapon_id]
    damage_report = {}
    total_destroyed = 0
    fuel_losses = {}
    
    # Собираем все доступные цели
    available_targets = []
    for field in target_info["infra_fields"]:
        if field in region_data:
            current_value = region_data[field]
            if isinstance(current_value, (int, float)) and current_value > 0:
                # Добавляем каждую единицу как отдельную цель
                for i in range(int(current_value)):
                    available_targets.append(field)
    
    if not available_targets:
        return damage_report, total_destroyed, fuel_losses
    
    random.shuffle(available_targets)
    
    # Количество попаданий не может превышать количество доступных целей
    hits = min(hits, len(available_targets))
    
    # Распределяем попадания (1 попадание = 1 уничтоженная цель)
    hits_distribution = {}
    for i in range(hits):
        target = available_targets[i]
        hits_distribution[target] = hits_distribution.get(target, 0) + 1
    
    # Применяем уничтожение
    for field, destroy_count in hits_distribution.items():
        current = region_data.get(field, 0)
        destroyed = min(current, destroy_count)
        region_data[field] = current - destroyed
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
            "short_range_air_defense": "ПВО ближнего действия",
            "long_range_air_defense": "ПВО дальнего действия",
            "zdprk": "ЗПРК",
            "zas": "Зенитная артиллерия"
        }
        
        field_name = field_names.get(field, field.replace('_', ' ').title())
        
        # Потери топлива при уничтожении НПЗ и нефтебаз
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
        
        if field in damage_report:
            damage_report[field]["destroyed"] += destroyed
            damage_report[field]["remaining"] = region_data[field]
        else:
            damage_report[field] = {
                "name": field_name,
                "destroyed": destroyed,
                "remaining": region_data[field]
            }
    
    return damage_report, total_destroyed, fuel_losses

def get_available_weapons(player_data: Dict) -> List[Tuple[str, int]]:
    """Возвращает список доступного у игрока оружия для ударов"""
    available = []
    army = player_data.get("army", {})
    
    for weapon_id, weapon_info in STRIKE_WEAPONS.items():
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

def consume_weapon(player_data: Dict, weapon_id: str, quantity: int) -> bool:
    """Списывает использованное оружие"""
    weapon_info = STRIKE_WEAPONS[weapon_id]
    path = weapon_info["army_path"].split('.')
    
    current = player_data["army"]
    for key in path[:-1]:
        if key not in current:
            return False
        current = current[key]
    
    last_key = path[-1]
    if last_key not in current or current[last_key] < quantity:
        return False
    
    current[last_key] -= quantity
    return True

def calculate_civilian_casualties(target_info: Dict, hits: int, region_population: int) -> int:
    """
    Рассчитывает потери среди гражданского населения
    """
    if region_population <= 0:
        return 0
    
    # Базовая формула: casualties = base * hits * random_factor
    base_per_hit = target_info.get("civilian_casualty_base", 50)
    
    # Случайный фактор (0.7 - 1.3)
    random_factor = random.uniform(0.7, 1.3)
    
    # Расчет потерь
    casualties = int(base_per_hit * hits * random_factor)
    
    # Ограничиваем населением региона (не более 5% за один удар)
    casualties = min(casualties, int(region_population * 0.05))
    
    return casualties

def execute_strike(attacker_data: Dict, target_country: str, target_region: str,
                   weapon_id: str, quantity: int, target_type: str,
                   attacker_region: str) -> Dict:
    """
    Выполняет удар и возвращает отчёт
    """
    states = load_states()
    infra = load_infrastructure()
    
    # Проверяем дальность
    attacker_country = attacker_data["state"]["statename"]
    weapon = STRIKE_WEAPONS[weapon_id]
    reachable, distance = is_region_reachable(
        attacker_country, attacker_region,
        target_country, target_region,
        weapon["range"]
    )
    
    if not reachable:
        return {
            "success": False,
            "message": f"❌ Цель вне зоны досягаемости! Расстояние: {distance} км, дальность оружия: {weapon['range']} км"
        }
    
    # Находим данные цели
    target_data = None
    for data in states["players"].values():
        if data.get("state", {}).get("statename") == target_country:
            target_data = data
            break
    
    if not target_data:
        return {"success": False, "message": "❌ Цель не найдена"}
    
    # Находим регион в инфраструктуре
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
        return {"success": False, "message": "❌ Регион не найден"}
    
    # Проверяем наличие целей
    available_targets = count_targets_in_region(region_data, target_type)
    if available_targets == 0:
        return {
            "success": False, 
            "message": f"❌ В регионе {target_region} нет целей типа {TARGET_TYPES[target_type]['name']}"
        }
    
    # Расчёт перехвата
    surviving, base_chance, final_chance = calculate_surviving_weapons(weapon_id, target_country, quantity, attacker_country)
    
    if surviving == 0:
        return {
            "success": True,
            "intercepted": True,
            "intercepted_count": quantity,
            "surviving": 0,
            "hits": 0,
            "damage_report": {},
            "civilian_casualties": 0,
            "destroyed_objects": 0,
            "fuel_losses": {},
            "happiness_impact": 0,
            "stability_impact": 0,
            "base_chance": base_chance * 100,
            "final_chance": final_chance * 100,
            "distance": distance,
            "message": f"🛡️ Все {quantity} средств поражения перехвачены ПВО! (шанс перехвата: {final_chance*100:.1f}%)"
        }
    
    # Расчёт попаданий
    hits = 0
    for _ in range(surviving):
        if random.random() < weapon["base_accuracy"]:
            hits += 1
    
    if hits == 0:
        return {
            "success": True,
            "intercepted": quantity - surviving > 0,
            "intercepted_count": quantity - surviving,
            "surviving": surviving,
            "hits": 0,
            "damage_report": {},
            "civilian_casualties": 0,
            "destroyed_objects": 0,
            "fuel_losses": {},
            "happiness_impact": 0,
            "stability_impact": 0,
            "base_chance": base_chance * 100,
            "final_chance": final_chance * 100,
            "distance": distance,
            "message": f"🛡️ Перехвачено: {quantity - surviving}. Достигло цели: {surviving}, но ни один не попал."
        }
    
    # Ограничиваем количество попаданий количеством доступных целей
    hits = min(hits, available_targets)
    
    # Распределяем попадания (1 попадание = 1 уничтоженный объект)
    target_info = TARGET_TYPES[target_type]
    damage_report, destroyed_objects, fuel_losses = distribute_hits_among_targets(
        region_data, target_type, hits, weapon_id
    )
    
    # Потери среди гражданского населения
    total_casualties = 0
    if random.random() < target_info["civilian_casualty_chance"]:
        total_casualties = calculate_civilian_casualties(
            target_info, hits, region_data.get("population", 0)
        )
        
        if total_casualties > 0 and "population" in region_data:
            current_pop = region_data["population"]
            if current_pop > 0:
                actual_casualties = min(current_pop, total_casualties)
                region_data["population"] = current_pop - actual_casualties
                total_casualties = actual_casualties
    
    save_infrastructure(infra)
    
    # Обновляем социальные показатели
    happiness_impact = target_info["happiness_impact"] * hits
    stability_impact = target_info["stability_impact"] * hits
    
    if total_casualties > 0:
        happiness_impact += min(10, total_casualties // 1000)
    
    target_data["state"]["happiness"] = max(0, target_data["state"].get("happiness", 50) - happiness_impact)
    target_data["state"]["stability"] = max(0, target_data["state"].get("stability", 50) - stability_impact)
    target_data["state"]["trust"] = max(0, target_data["state"].get("trust", 50) - stability_impact // 2)
    
    save_states(states)
    
    # Записываем в конфликт
    try:
        from conflicts import record_strike
        attacker_name = attacker_data["state"]["statename"]
        record_strike(attacker_name, target_country, destroyed_objects)
    except ImportError:
        pass
    except Exception as e:
        print(f"Ошибка при записи в конфликт: {e}")
    
    # Формируем отчёт
    report = {
        "success": True,
        "intercepted": quantity - surviving > 0,
        "intercepted_count": quantity - surviving,
        "surviving": surviving,
        "hits": hits,
        "destroyed_objects": destroyed_objects,
        "damage_report": damage_report,
        "civilian_casualties": total_casualties,
        "fuel_losses": fuel_losses,
        "happiness_impact": happiness_impact,
        "stability_impact": stability_impact,
        "base_chance": base_chance * 100,
        "final_chance": final_chance * 100,
        "distance": distance,
        "attacker": attacker_country,
        "attacker_region": attacker_region,
        "target": target_country,
        "target_region": target_region,
        "target_type_name": target_info['name'],
        "weapon_name": weapon['name'],
        "quantity": quantity,
        "message": (
            f"📊 **РЕЗУЛЬТАТ УДАРА**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📏 Расстояние: {distance} км\n"
            f"🚀 Запущено: {quantity}\n"
            f"🛡️ Перехвачено: {quantity - surviving} ({final_chance*100:.1f}%)\n"
            f"🎯 Достигло цели: {surviving}\n"
            f"💥 Попаданий: {hits}\n"
            f"🏭 Уничтожено объектов: {destroyed_objects}\n"
            f"👥 Потери населения: {format_number(total_casualties)} чел.\n"
            f"😢 Падение счастья: -{happiness_impact}%\n"
            f"⚖️ Падение стабильности: -{stability_impact}%"
        )
    }
    
    # Добавляем информацию о потерях топлива, если есть
    if fuel_losses:
        fuel_text = "\n⛽ Потери топлива:\n"
        for fuel, loss in fuel_losses.items():
            fuel_text += f"  • {fuel}: {loss:.2f}\n"
        report["message"] += fuel_text
    
    return report

# ==================== ФУНКЦИЯ ДЛЯ ОТПРАВКИ ЛОГОВ ====================

async def send_strike_log(bot_instance, report: Dict):
    """Отправляет результат удара в лог-канал"""
    try:
        channel = bot_instance.get_channel(STRIKE_LOG_CHANNEL_ID)
        if not channel:
            return
        
        embed = discord.Embed(
            title="💥 РЕЗУЛЬТАТ УДАРА",
            description=f"**{report['attacker']}** атаковал **{report['target']}**",
            color=discord.Color.red() if report.get("hits", 0) > 0 else discord.Color.orange()
        )
        
        embed.add_field(name="Атакующий регион", value=report['attacker_region'], inline=True)
        embed.add_field(name="Целевой регион", value=report['target_region'], inline=True)
        embed.add_field(name="Тип цели", value=report['target_type_name'], inline=True)
        embed.add_field(name="Оружие", value=f"{report['weapon_name']} x{report['quantity']}", inline=True)
        embed.add_field(name="Расстояние", value=f"{report['distance']} км", inline=True)
        embed.add_field(name="Перехвачено", value=f"{report['intercepted_count']} ({report['final_chance']:.1f}%)", inline=True)
        
        if report.get("hits", 0) > 0:
            embed.add_field(name="Попаданий", value=str(report['hits']), inline=True)
            embed.add_field(name="Уничтожено", value=str(report['destroyed_objects']), inline=True)
            embed.add_field(name="Потери населения", value=format_number(report['civilian_casualties']), inline=True)
        
        embed.set_footer(text=f"Время удара: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Ошибка при отправке лога удара: {e}")

# ==================== КЛАССЫ ДЛЯ ВЫБОРА РЕГИОНА АТАКИ ====================

class AttackerEconomicRegionSelect(Select):
    """Выбор экономического района для запуска"""
    
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, quantity: int,
                 economic_regions: Dict, original_message):
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.original_message = original_message
        
        options = []
        for econ_region in list(economic_regions.keys())[:25]:
            region_count = len(economic_regions[econ_region].get("regions", {}))
            options.append(
                discord.SelectOption(
                    label=econ_region[:100],
                    description=f"Регионов: {region_count}",
                    value=econ_region
                )
            )
        
        super().__init__(
            placeholder="Выберите экономический район для запуска...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = self.values[0]
        
        infra = load_infrastructure()
        country_id = None
        for cid, data in infra["infrastructure"].items():
            if data.get("country") == self.player_country:
                country_id = cid
                break
        
        regions = infra["infrastructure"][country_id]["economic_regions"][econ_region]["regions"]
        
        embed = discord.Embed(
            title="Выбор региона запуска",
            description=f"Цель: {self.target_country}\nОружие: {self.weapon_info['name']} x{self.quantity}\nРайон: {econ_region}",
            color=DARK_THEME_COLOR
        )
        
        select = AttackerRegionSelect(
            self.user_id, self.player_country, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity,
            econ_region, regions, interaction.message
        )
        view = View(timeout=120)
        view.add_item(select)
        
        await interaction.response.edit_message(embed=embed, view=view)


class AttackerRegionSelect(Select):
    """Выбор конкретного региона для запуска"""
    
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, quantity: int,
                 econ_region: str, regions: Dict, original_message):
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.econ_region = econ_region
        self.regions = regions
        self.original_message = original_message
        
        options = []
        for region_name, region_data in list(regions.items())[:25]:
            # Показываем информацию о регионе
            population = region_data.get("population", 0)
            military = region_data.get("military_factories", 0)
            
            options.append(
                discord.SelectOption(
                    label=region_name[:100],
                    description=f"Население: {population//1000000}млн | Воен: {military}",
                    value=region_name
                )
            )
        
        super().__init__(
            placeholder="Выберите регион для запуска...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        attacker_region = self.values[0]
        
        await show_target_selection(
            interaction, self.user_id, self.player_country, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity, attacker_region
        )


class CountrySelect(Select):
    """Выбор страны для удара"""
    
    def __init__(self, user_id: int, player_country: str, original_message):
        self.user_id = user_id
        self.player_country = player_country
        self.original_message = original_message
        
        at_war = get_countries_at_war(player_country)
        
        options = []
        for country in at_war[:25]:
            options.append(
                discord.SelectOption(
                    label=country,
                    value=country
                )
            )
        
        if not options:
            options.append(
                discord.SelectOption(
                    label="Нет стран для удара",
                    value="none",
                    default=True
                )
            )
        
        super().__init__(
            placeholder="Выберите страну для удара...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        if self.values[0] == "none":
            await interaction.response.send_message("❌ Нет доступных целей!", ephemeral=True)
            return
        
        target_country = self.values[0]
        
        states = load_states()
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("❌ Ошибка загрузки данных!", ephemeral=True)
            return
        
        available_weapons = get_available_weapons(player_data)
        
        if not available_weapons:
            await interaction.response.send_message("❌ У вас нет доступного оружия для ударов!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор вооружения",
            description=f"Цель: {target_country}",
            color=DARK_THEME_COLOR
        )
        
        view = WeaponSelectView(
            self.user_id, self.player_country,
            target_country, available_weapons
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class WeaponSelectView(View):
    """Выбор типа оружия"""
    
    def __init__(self, user_id: int, player_country: str,
                 target_country: str, available_weapons: List[Tuple[str, int]]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.available_weapons = available_weapons
        
        for weapon_id, quantity in available_weapons:
            weapon_info = STRIKE_WEAPONS[weapon_id]
            
            button = Button(
                label=f"{weapon_info['name']} | {quantity} шт. | Дальн: {weapon_info['range']} км",
                style=discord.ButtonStyle.secondary,
                custom_id=f"weapon_{weapon_id}"
            )
            button.callback = self.create_weapon_callback(weapon_id, weapon_info, quantity)
            self.add_item(button)
        
        back_button = Button(label="◀ Назад к странам", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    def create_weapon_callback(self, weapon_id: str, weapon_info: Dict, max_quantity: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
                return
            
            modal = QuantityModal(
                self.user_id, self.player_country, self.target_country,
                weapon_id, weapon_info, max_quantity
            )
            await interaction.response.send_modal(modal)
        
        return callback
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_strike_menu(interaction, self.user_id)


class QuantityModal(Modal, title="Количество"):
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, max_quantity: int):
        super().__init__()
        self.user_id = user_id
        self.player_country = player_country
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
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > self.max_quantity:
                await interaction.response.send_message(
                    f"❌ Количество должно быть от 1 до {self.max_quantity}!",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        # Получаем экономические районы страны атакующего
        infra = load_infrastructure()
        country_id = None
        for cid, data in infra["infrastructure"].items():
            if data.get("country") == self.player_country:
                country_id = cid
                break
        
        if not country_id:
            await interaction.response.send_message("❌ Данные инфраструктуры не найдены!", ephemeral=True)
            return
        
        economic_regions = infra["infrastructure"][country_id].get("economic_regions", {})
        
        if not economic_regions:
            await interaction.response.send_message("❌ Нет экономических районов для вашей страны!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выбор экономического района для запуска",
            description=f"Цель: {self.target_country}\nОружие: {self.weapon_info['name']} x{quantity}",
            color=DARK_THEME_COLOR
        )
        
        select = AttackerEconomicRegionSelect(
            self.user_id, self.player_country, self.target_country,
            self.weapon_id, self.weapon_info, quantity,
            economic_regions, interaction.message
        )
        view = View(timeout=120)
        view.add_item(select)
        
        await interaction.response.edit_message(embed=embed, view=view)


# ==================== ФУНКЦИИ ДЛЯ ВЫБОРА ЦЕЛИ ====================

async def show_target_selection(interaction, user_id: int, player_country: str, target_country: str,
                                weapon_id: str, weapon_info: Dict, quantity: int, attacker_region: str):
    """Показывает выбор цели в стране противника"""
    
    infra = load_infrastructure()
    
    # Находим ID страны цели
    country_id = None
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == target_country:
            country_id = cid
            break
    
    if not country_id:
        await interaction.response.send_message("❌ Данные инфраструктуры не найдены!", ephemeral=True)
        return
    
    economic_regions = infra["infrastructure"][country_id].get("economic_regions", {})
    
    if not economic_regions:
        await interaction.response.send_message("❌ Нет экономических районов для этой страны!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Выбор экономического района цели",
        description=f"Атакующий регион: {attacker_region}\nЦель: {target_country}\nОружие: {weapon_info['name']} x{quantity}",
        color=DARK_THEME_COLOR
    )
    
    select = TargetEconomicRegionSelect(
        user_id, player_country, target_country,
        weapon_id, weapon_info, quantity, attacker_region,
        economic_regions, None
    )
    view = View(timeout=120)
    view.add_item(select)
    
    await interaction.response.edit_message(embed=embed, view=view)


class TargetEconomicRegionSelect(Select):
    """Выбор экономического района цели"""
    
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, quantity: int, attacker_region: str,
                 economic_regions: Dict, original_message):
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.original_message = original_message
        
        options = []
        for econ_region in list(economic_regions.keys())[:25]:
            region_count = len(economic_regions[econ_region].get("regions", {}))
            options.append(
                discord.SelectOption(
                    label=econ_region[:100],
                    description=f"Регионов: {region_count}",
                    value=econ_region
                )
            )
        
        super().__init__(
            placeholder="Выберите экономический район цели...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        econ_region = self.values[0]
        
        infra = load_infrastructure()
        country_id = None
        for cid, data in infra["infrastructure"].items():
            if data.get("country") == self.target_country:
                country_id = cid
                break
        
        regions = infra["infrastructure"][country_id]["economic_regions"][econ_region]["regions"]
        
        embed = discord.Embed(
            title="Выбор региона цели",
            description=f"Атакующий регион: {self.attacker_region}\nЦель: {self.target_country} / {econ_region}\nОружие: {self.weapon_info['name']} x{self.quantity}",
            color=DARK_THEME_COLOR
        )
        
        select = TargetRegionSelect(
            self.user_id, self.player_country, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity, self.attacker_region,
            econ_region, regions, interaction.message
        )
        view = View(timeout=120)
        view.add_item(select)
        
        await interaction.response.edit_message(embed=embed, view=view)


class TargetRegionSelect(Select):
    """Выбор конкретного региона цели"""
    
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, quantity: int, attacker_region: str,
                 econ_region: str, regions: Dict, original_message):
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.econ_region = econ_region
        self.regions = regions
        self.original_message = original_message
        
        options = []
        for region_name, region_data in list(regions.items())[:25]:
            # Проверяем достижимость
            reachable, distance = is_region_reachable(
                player_country, attacker_region,
                target_country, region_name,
                weapon_info["range"]
            )
            
            # Подсчитываем общее количество целей в регионе
            total_targets = 0
            for target_id, target_info in TARGET_TYPES.items():
                for field in target_info["infra_fields"]:
                    if field in region_data:
                        total_targets += region_data.get(field, 0)
            
            population = region_data.get("population", 0)
            
            if reachable:
                status = "✅"
                desc = f"{distance} км | Целей: {total_targets} | 👥{population//1000000}млн"
            else:
                status = "❌"
                desc = f"{distance} км (вне зоны)"
            
            options.append(
                discord.SelectOption(
                    label=f"{status} {region_name[:95]}",
                    description=desc,
                    value=region_name,
                    default=False
                )
            )
        
        super().__init__(
            placeholder="Выберите регион цели...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        target_region = self.values[0]
        region_data = self.regions[target_region]
        
        # Проверяем достижимость
        reachable, distance = is_region_reachable(
            self.player_country, self.attacker_region,
            self.target_country, target_region,
            self.weapon_info["range"]
        )
        
        if not reachable:
            await interaction.response.send_message(
                f"❌ Регион {target_region} на расстоянии {distance} км (макс. {self.weapon_info['range']} км)!",
                ephemeral=True
            )
            return
        
        # Показываем доступные типы целей
        available_targets = []
        for target_id, target_info in TARGET_TYPES.items():
            # Проверяем, есть ли цели этого типа в регионе
            has_target = False
            for field in target_info["infra_fields"]:
                if field in region_data and region_data[field] > 0:
                    has_target = True
                    break
            if has_target:
                available_targets.append((target_id, target_info))
        
        if not available_targets:
            embed = discord.Embed(
                title="Нет целей",
                description="В этом регионе нет доступных объектов для удара.",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        embed = discord.Embed(
            title="Выбор типа цели",
            description=f"Атакующий регион: {self.attacker_region}\nЦель: {self.target_country} / {self.econ_region} / {target_region}\nОружие: {self.weapon_info['name']} x{self.quantity}",
            color=DARK_THEME_COLOR
        )
        
        view = TargetTypeView(
            self.user_id, self.player_country, self.target_country,
            self.weapon_id, self.weapon_info, self.quantity, self.attacker_region,
            self.econ_region, target_region, region_data, available_targets
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class TargetTypeView(View):
    """Выбор типа цели"""
    
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, quantity: int, attacker_region: str,
                 econ_region: str, target_region: str, region_data: Dict,
                 available_targets: List[Tuple[str, Dict]]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.econ_region = econ_region
        self.target_region = target_region
        self.region_data = region_data
        
        # Сортируем по приоритету
        sorted_targets = sorted(available_targets, key=lambda x: x[1]["priority"])
        
        for target_id, target_info in sorted_targets:
            # Подсчитываем количество целей этого типа
            target_count = 0
            for field in target_info["infra_fields"]:
                if field in region_data:
                    value = region_data[field]
                    if isinstance(value, (int, float)) and value > 0:
                        target_count += value
            
            button = Button(
                label=f"{target_info['name']} (доступно: {target_count})",
                style=discord.ButtonStyle.secondary,
                custom_id=f"target_{target_id}"
            )
            button.callback = self.create_target_callback(target_id, target_info)
            self.add_item(button)
    
    def create_target_callback(self, target_id: str, target_info: Dict):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
                return
            
            # Проверяем, есть ли еще цели
            target_exists = False
            target_count = 0
            for field in target_info["infra_fields"]:
                if field in self.region_data and self.region_data[field] > 0:
                    target_exists = True
                    target_count += self.region_data[field]
            
            if not target_exists:
                await interaction.response.send_message(
                    f"❌ В регионе больше нет целей типа {target_info['name']}!",
                    ephemeral=True
                )
                return
            
            surviving, base_chance, final_chance = calculate_surviving_weapons(
                self.weapon_id, self.target_country, self.quantity
            )
            
            weapon = STRIKE_WEAPONS[self.weapon_id]
            reachable, distance = is_region_reachable(
                self.player_country, self.attacker_region,
                self.target_country, self.target_region,
                weapon["range"]
            )
            
            embed = discord.Embed(
                title="ПОДТВЕРЖДЕНИЕ УДАРА",
                description=f"Операция против {self.target_country}",
                color=discord.Color.orange()
            )
            
            embed.add_field(name="Атакующий регион", value=self.attacker_region, inline=True)
            embed.add_field(name="Цель", value=f"{self.target_region}", inline=True)
            embed.add_field(name="Расстояние", value=f"{distance} км", inline=True)
            embed.add_field(name="Тип цели", value=target_info['name'], inline=True)
            embed.add_field(name="Количество целей", value=str(target_count), inline=True)
            embed.add_field(name="Оружие", value=f"{weapon['name']} x{self.quantity}", inline=True)
            
            expected_destroyed = int(surviving * weapon["base_accuracy"])
            expected_casualties = int(target_info.get('civilian_casualty_base', 50) * expected_destroyed * random.uniform(0.7, 1.3))
            
            embed.add_field(
                name="Оценка удара",
                value=f"Шанс перехвата: {final_chance*100:.1f}%\n"
                      f"Ожидаемые попадания: {int(surviving * weapon['base_accuracy'])}\n"
                      f"Ожидаемый урон: {expected_destroyed} объектов\n"
                      f"Ожидаемые потери: ~{format_number(expected_casualties)} чел.",
                inline=False
            )
            
            embed.add_field(
                name="Предупреждение",
                value="Оружие будет списано из армии независимо от результата. Подтверждаете пуск?",
                inline=False
            )
            
            view = StrikeConfirmationView(
                self.user_id, self.player_country, self.target_country,
                self.weapon_id, self.weapon_info, self.quantity, self.attacker_region,
                self.target_region, target_id, target_info
            )
            
            await interaction.response.edit_message(embed=embed, view=view)
        
        return callback


class StrikeConfirmationView(View):
    """Подтверждение пуска"""
    
    def __init__(self, user_id: int, player_country: str, target_country: str,
                 weapon_id: str, weapon_info: Dict, quantity: int, attacker_region: str,
                 target_region: str, target_id: str, target_info: Dict):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_country = player_country
        self.target_country = target_country
        self.weapon_id = weapon_id
        self.weapon_info = weapon_info
        self.quantity = quantity
        self.attacker_region = attacker_region
        self.target_region = target_region
        self.target_id = target_id
        self.target_info = target_info
        self.bot = None
    
    @discord.ui.button(label="ПОДТВЕРДИТЬ ПУСК", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
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
            await interaction.followup.send("❌ Ошибка загрузки данных!", ephemeral=True)
            return
        
        if not consume_weapon(attacker_data, self.weapon_id, self.quantity):
            await interaction.followup.send("❌ Ошибка при списании оружия!", ephemeral=True)
            return
        
        result = execute_strike(
            attacker_data, self.target_country, self.target_region,
            self.weapon_id, self.quantity, self.target_id,
            self.attacker_region
        )
        
        if not result["success"]:
            await interaction.followup.send(f"❌ {result['message']}", ephemeral=True)
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
            "target_type": self.target_info["name"],
            "weapon": self.weapon_info["name"],
            "weapon_id": self.weapon_id,
            "quantity": self.quantity,
            "intercepted": result.get("intercepted_count", 0),
            "surviving": result.get("surviving", 0),
            "hits": result.get("hits", 0),
            "destroyed": result.get("destroyed_objects", 0),
            "casualties": result.get("civilian_casualties", 0),
            "fuel_losses": result.get("fuel_losses", {}),
            "distance": result.get("distance", 0),
            "timestamp": str(datetime.now())
        }
        strikes["strikes"].append(strike_record)
        save_strikes(strikes)
        
        embed = discord.Embed(
            title="РЕЗУЛЬТАТ УДАРА",
            description=result["message"],
            color=discord.Color.red() if result["hits"] > 0 else discord.Color.orange()
        )
        
        # Отправляем результат игроку
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Отправляем лог в канал
        if self.bot:
            await send_strike_log(self.bot, result)
    
    @discord.ui.button(label="ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Пуск отменён",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ГЛАВНОЕ МЕНЮ ====================

async def show_strike_menu(interaction_or_ctx, user_id: int):
    """Показать меню управления ударами"""
    from bot import load_states
    
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
            await interaction_or_ctx.response.send_message("❌ У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("❌ У вас нет государства!")
        return
    
    available_weapons = get_available_weapons(player_data)
    
    embed = discord.Embed(
        title="Управление ударами",
        description="Нанесение ударов по инфраструктуре противника",
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
    
    embed.add_field(
        name="Важно",
        value="• Удары возможны только по странам, с которыми вы в состоянии войны\n"
              "• Оружие списывается из армии независимо от результата\n"
              "• Учитывается расстояние от региона запуска до региона цели\n"
              "• 1 попадание = 1 уничтоженный объект\n"
              "• Риск жертв среди гражданского населения: 30-80%\n"
              "• Результаты ударов логируются в канал",
        inline=False
    )
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
        message = await interaction_or_ctx.original_response()
    else:
        message = await interaction_or_ctx.send(embed=embed, ephemeral=True)
    
    if available_weapons:
        select = CountrySelect(user_id, player_country, message)
        view = View(timeout=120)
        view.add_item(select)
        await message.edit(view=view)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_strike_menu',
    'STRIKE_WEAPONS',
    'TARGET_TYPES',
    'get_region_distance',
    'is_region_reachable',
    'load_distances',
    'get_all_country_regions',
    'send_strike_log',
    'STRIKE_LOG_CHANNEL_ID'
]

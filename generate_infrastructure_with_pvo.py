# generate_infrastructure_with_pvo.py
# Скрипт для генерации инфраструктуры с распределением ПВО и новыми объектами
# Версия 2.2 - с учётом промышленных объектов (НПЗ, нефтебазы, ТЭС, ГЭС, фабрики)

import json
import random
from datetime import datetime
from typing import Dict, List, Tuple

# Файлы
STATES_FILE = 'states_default.json'
INFRA_FILE = 'infrastructure_default.json'
BACKUP_FILE = f'infrastructure_default_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'

# Коэффициенты важности для разных типов регионов
IMPORTANCE_MULTIPLIERS = {
    # Максимальная важность (столицы)
    "capital_region": {
        "pvo_multiplier": 3.0,
        "description": "Столичный регион - максимальная защита"
    },
    # Очень высокая важность
    "naval_base": {
        "pvo_multiplier": 2.5,
        "description": "Военно-морская база"
    },
    # Высокая важность
    "industrial_heartland": {
        "pvo_multiplier": 2.0,
        "description": "Промышленный центр"
    },
    "technology_hub": {
        "pvo_multiplier": 2.0,
        "description": "Технологический центр"
    },
    # Средняя важность
    "oil_rich": {
        "pvo_multiplier": 1.8,
        "description": "Нефтегазовый регион"
    },
    "resource_rich": {
        "pvo_multiplier": 1.5,
        "description": "Ресурсодобывающий регион"
    },
    "border_region": {
        "pvo_multiplier": 1.8,
        "description": "Приграничный регион"
    },
    "mountain_fortress": {
        "pvo_multiplier": 2.0,
        "description": "Горный укрепрайон"
    },
    # Базовая важность
    "agricultural_region": {
        "pvo_multiplier": 1.0,
        "description": "Сельскохозяйственный регион"
    },
    "tourist_haven": {
        "pvo_multiplier": 0.8,
        "description": "Туристический регион"
    },
    "cultural_center": {
        "pvo_multiplier": 0.7,
        "description": "Культурный центр"
    },
    "forestry_region": {
        "pvo_multiplier": 0.6,
        "description": "Лесной регион"
    },
    "arctic_region": {
        "pvo_multiplier": 1.2,
        "description": "Арктический регион"
    },
    "aerospace_hub": {
        "pvo_multiplier": 2.2,
        "description": "Аэрокосмический центр"
    },
    "pharmaceutical_hub": {
        "pvo_multiplier": 1.8,
        "description": "Фармацевтический центр"
    },
    "financial_center": {
        "pvo_multiplier": 2.0,
        "description": "Финансовый центр"
    },
    "diplomatic_center": {
        "pvo_multiplier": 2.5,
        "description": "Дипломатический центр"
    },
    "energy_hub": {
        "pvo_multiplier": 1.8,
        "description": "Энергетический центр"
    }
}

# Новые типы инфраструктуры
NEW_INFRA_TYPES = {
    # Военные объекты
    "military_airfields": {
        "name": "Военные аэродромы",
        "description": "Аэродромы для базирования военной авиации",
        "base_per_region": 0,
        "multiplier": 0.08,
        "max_per_region": 15
    },
    "military_bases": {
        "name": "Военные базы",
        "description": "Постоянные военные гарнизоны и базы",
        "base_per_region": 0,
        "multiplier": 0.1,
        "max_per_region": 20
    },
    "military_depots": {
        "name": "Военные склады",
        "description": "Склады боеприпасов, вооружения и техники",
        "base_per_region": 0,
        "multiplier": 0.12,
        "max_per_region": 25
    },
    "fortifications": {
        "name": "Укрепления",
        "description": "Оборонительные сооружения, ДОТы, ДЗОТы",
        "base_per_region": 0,
        "multiplier": 0.05,
        "max_per_region": 30
    },
    
    # Гражданские объекты
    "airports": {
        "name": "Аэропорты",
        "description": "Гражданские аэропорты",
        "base_per_region": 0,
        "multiplier": 0.15,
        "max_per_region": 10
    },
    "civilian_depots": {
        "name": "Гражданские склады",
        "description": "Склады товаров, продовольствия, ресурсов",
        "base_per_region": 0,
        "multiplier": 0.2,
        "max_per_region": 40
    },
    "substations": {
        "name": "Энергоподстанции",
        "description": "Трансформаторные подстанции, распределительные узлы",
        "base_per_region": 0,
        "multiplier": 0.25,
        "max_per_region": 15
    },
    
    # Коммуникации
    "communication_hubs": {
        "name": "Узлы связи",
        "description": "Центральные узлы телекоммуникаций",
        "base_per_region": 0,
        "multiplier": 0.1,
        "max_per_region": 8
    },
    "radio_towers": {
        "name": "Радиовышки",
        "description": "Телевизионные и радиовещательные вышки",
        "base_per_region": 0,
        "multiplier": 0.12,
        "max_per_region": 20
    },
    
    # Транспорт
    "railway_hubs": {
        "name": "Железнодорожные узлы",
        "description": "Сортировочные станции и крупные вокзалы",
        "base_per_region": 0,
        "multiplier": 0.1,
        "max_per_region": 15
    }
}


def load_json(filepath: str) -> Dict:
    """Загружает JSON файл"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except FileNotFoundError:
        print(f"⚠️ Файл {filepath} не найден")
        return {}
    except json.JSONDecodeError:
        print(f"⚠️ Ошибка чтения {filepath}")
        return {}


def save_json(data: Dict, filepath: str):
    """Сохраняет JSON файл"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_backup():
    """Создаёт резервную копию infrastructure_default.json"""
    try:
        with open(INFRA_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
            if content:
                with open(BACKUP_FILE, 'w', encoding='utf-8') as bf:
                    bf.write(content)
                print(f"📁 Создана резервная копия: {BACKUP_FILE}")
    except FileNotFoundError:
        print("⚠️ Исходный файл не найден, резервная копия не создана")


def get_country_army_data(states_data: Dict, country_name: str) -> Dict:
    """Получает данные армии страны"""
    for cid, data in states_data.items():
        if data.get("state", {}).get("statename") == country_name:
            return data.get("army", {})
    return {}


def get_country_pvo_from_army(states_data: Dict, country_name: str) -> Dict[str, int]:
    """Извлекает количество ПВО из армии страны"""
    army = get_country_army_data(states_data, country_name)
    ground = army.get("ground", {})
    
    return {
        "short_range_air_defense": ground.get("short_range_air_defense", 0),
        "long_range_air_defense": ground.get("long_range_air_defense", 0),
        "zdprk": ground.get("zdprk", 0),
        "zas": ground.get("zas", 0),
        "radar_systems": ground.get("radar_systems", 0)
    }


def get_region_importance_multiplier(region_data: Dict, region_name: str, country_name: str) -> float:
    """Возвращает множитель важности для региона"""
    specialization = region_data.get("specialization", "")
    
    # Проверяем, является ли регион столицей (по названию)
    is_capital = False
    capital_names = ["Москва", "Санкт-Петербург", "Пекин", "Вашингтон", "Лондон", "Париж", 
                     "Токио", "Берлин", "Рим", "Мадрид", "Оттава", "Канберра", "Нью-Дели",
                     "Пхеньян", "Анкара", "Иерусалим", "Тегеран", "Киев", "Минск", "Осло",
                     "Стокгольм", "Хельсинки", "Варшава", "Бразилиа", "Каир", "Берн"]
    
    for capital in capital_names:
        if capital in region_name or region_name.startswith(capital):
            is_capital = True
            break
    
    if is_capital:
        return IMPORTANCE_MULTIPLIERS["capital_region"]["pvo_multiplier"]
    
    # По специализации
    if specialization in IMPORTANCE_MULTIPLIERS:
        return IMPORTANCE_MULTIPLIERS[specialization]["pvo_multiplier"]
    
    # Базовая важность
    return 1.0


def calculate_region_weight(region_data: Dict, region_name: str, country_name: str) -> float:
    """Рассчитывает вес региона для распределения ресурсов с учётом:
    - уровня развития
    - населения
    - военных и гражданских заводов
    - НПЗ, нефтебаз, верфей
    - ТЭС, ГЭС, СЭС, ВЭС, АЭС
    """
    
    # Базовые показатели
    development = region_data.get("development_level", 50)
    population = region_data.get("population", 0)
    
    # Промышленные объекты
    military_factories = region_data.get("military_factories", 0)
    civilian_factories = region_data.get("civilian_factories", 0)
    shipyards = region_data.get("shipyards", 0)
    refineries = region_data.get("refineries", 0)          # НПЗ
    oil_depots = region_data.get("oil_depots", 0)          # Нефтебазы
    
    # Энергетика
    thermal_power = region_data.get("thermal_power", 0)    # ТЭС
    hydro_power = region_data.get("hydro_power", 0)        # ГЭС
    solar_power = region_data.get("solar_power", 0)        # СЭС
    wind_power = region_data.get("wind_power", 0)          # ВЭС
    nuclear_power = region_data.get("nuclear_power", 0)    # АЭС
    
    # Расчёт веса от промышленных объектов
    industrial_weight = (
        military_factories * 1.0 +      # Военные заводы - высокая важность
        civilian_factories * 0.8 +      # Гражданские заводы
        shipyards * 1.2 +               # Верфи - важны для флота
        refineries * 1.5 +              # НПЗ - критическая инфраструктура
        oil_depots * 0.8                # Нефтебазы
    )
    
    # Вес от энергетики
    energy_weight = (
        thermal_power * 0.6 +
        hydro_power * 0.8 +             # ГЭС - важнее
        solar_power * 0.3 +
        wind_power * 0.3 +
        nuclear_power * 2.0             # АЭС - критическая важность
    )
    
    # Базовый вес
    base_weight = development + (population / 1_000_000) + industrial_weight + energy_weight
    
    # Множитель важности (от специализации и столичности)
    importance_multiplier = get_region_importance_multiplier(region_data, region_name, country_name)
    
    # Итоговый вес
    weight = base_weight * importance_multiplier
    
    return max(1, weight)


def calculate_new_infra_value(region_data: Dict, infra_type: Dict) -> int:
    """Рассчитывает количество нового типа инфраструктуры в регионе"""
    development = region_data.get("development_level", 50)
    multiplier = infra_type["multiplier"]
    max_val = infra_type["max_per_region"]
    
    # Базовое значение зависит от уровня развития
    base = (development / 100) * multiplier * 100
    
    # Корректировка на специализацию региона
    specialization = region_data.get("specialization", "")
    if infra_type["name"] == "Военные аэродромы" and specialization == "naval_base":
        base *= 1.5
    if infra_type["name"] == "Военные базы" and specialization in ["border_region", "mountain_fortress"]:
        base *= 1.3
    if infra_type["name"] == "Аэропорты" and specialization == "capital_region":
        base *= 2.0
    if infra_type["name"] == "Энергоподстанции" and specialization in ["industrial_heartland", "resource_rich"]:
        base *= 1.2
    
    # Корректировка на наличие промышленных объектов
    if infra_type["name"] == "Железнодорожные узлы":
        # Больше заводов = больше ж/д узлов
        factories = region_data.get("military_factories", 0) + region_data.get("civilian_factories", 0)
        base *= (1 + factories / 200)
    
    if infra_type["name"] == "Гражданские склады":
        # Больше населения = больше складов
        population = region_data.get("population", 0)
        base *= (1 + population / 10_000_000)
    
    if infra_type["name"] == "Военные склады":
        # Больше военных заводов = больше военных складов
        base *= (1 + region_data.get("military_factories", 0) / 50)
    
    # Добавляем случайный фактор (±20%)
    random_factor = random.uniform(0.8, 1.2)
    value = int(base * random_factor)
    
    return min(max_val, max(0, value))


def distribute_pvo_to_regions(regions: List[Tuple[str, Dict, float]], total_pvo: Dict[str, int]) -> Dict[str, Dict[str, int]]:
    """Распределяет ПВО по регионам пропорционально весу"""
    total_weight = sum(weight for _, _, weight in regions)
    if total_weight == 0:
        total_weight = 1
    
    pvo_by_region = {}
    
    for region_name, region_data, weight in regions:
        share = weight / total_weight
        
        pvo_by_region[region_name] = {
            "short_range_air_defense": int(total_pvo.get("short_range_air_defense", 0) * share),
            "long_range_air_defense": int(total_pvo.get("long_range_air_defense", 0) * share),
            "zdprk": int(total_pvo.get("zdprk", 0) * share),
            "zas": int(total_pvo.get("zas", 0) * share),
            "radar_systems": int(total_pvo.get("radar_systems", 0) * share)
        }
    
    return pvo_by_region


def add_new_infra_to_regions(regions: List[Tuple[str, Dict, float]]) -> Dict[str, Dict[str, int]]:
    """Добавляет новые типы инфраструктуры в регионы"""
    new_infra_by_region = {}
    
    for region_name, region_data, weight in regions:
        new_infra = {}
        for infra_id, infra_info in NEW_INFRA_TYPES.items():
            value = calculate_new_infra_value(region_data, infra_info)
            new_infra[infra_id] = value
        new_infra_by_region[region_name] = new_infra
    
    return new_infra_by_region


def process_infrastructure(states_data: Dict, infra_data: Dict) -> Dict:
    """Основная функция обработки инфраструктуры"""
    
    # Собираем все регионы с их весами
    all_regions = []
    region_to_country = {}
    
    for cid, country_data in infra_data.get("infrastructure", {}).items():
        country_name = country_data.get("country")
        if not country_name:
            continue
        
        for econ_region, econ_data in country_data.get("economic_regions", {}).items():
            for region_name, region_data in econ_data.get("regions", {}).items():
                weight = calculate_region_weight(region_data, region_name, country_name)
                all_regions.append((region_name, region_data, weight))
                region_to_country[region_name] = (country_name, cid, econ_region)
    
    # Группируем регионы по странам
    countries = {}
    for region_name, region_data, weight in all_regions:
        country, cid, econ_region = region_to_country[region_name]
        if country not in countries:
            countries[country] = {
                "regions": [],
                "cid": cid,
                "total_weight": 0
            }
        countries[country]["regions"].append((region_name, region_data, weight))
        countries[country]["total_weight"] += weight
    
    # Распределяем ПВО и новую инфраструктуру
    pvo_by_country = {}
    new_infra_by_country = {}
    
    for country, data in countries.items():
        total_pvo = get_country_pvo_from_army(states_data, country)
        pvo_by_country[country] = distribute_pvo_to_regions(data["regions"], total_pvo)
        new_infra_by_country[country] = add_new_infra_to_regions(data["regions"])
    
    # Обновляем инфраструктуру
    updated_infra = infra_data.copy()
    
    for cid, country_data in updated_infra.get("infrastructure", {}).items():
        country_name = country_data.get("country")
        if not country_name:
            continue
        
        for econ_region, econ_data in country_data.get("economic_regions", {}).items():
            for region_name, region_data in econ_data.get("regions", {}).items():
                # Добавляем ПВО
                if country_name in pvo_by_country and region_name in pvo_by_country[country_name]:
                    for pvo_type, pvo_count in pvo_by_country[country_name][region_name].items():
                        region_data[pvo_type] = pvo_count
                
                # Добавляем новую инфраструктуру
                if country_name in new_infra_by_country and region_name in new_infra_by_country[country_name]:
                    for infra_id, infra_count in new_infra_by_country[country_name][region_name].items():
                        region_data[infra_id] = infra_count
    
    return updated_infra


def print_statistics(infra_data: Dict, states_data: Dict):
    """Выводит статистику по сгенерированной инфраструктуре"""
    
    print("\n" + "="*80)
    print("СТАТИСТИКА ГЕНЕРАЦИИ ИНФРАСТРУКТУРЫ")
    print("(с учётом: специализации, промышленных объектов, энергетики)")
    print("="*80)
    
    total_regions = 0
    total_pvo = {
        "short_range_air_defense": 0,
        "long_range_air_defense": 0,
        "zdprk": 0,
        "zas": 0,
        "radar_systems": 0
    }
    total_new_infra = {key: 0 for key in NEW_INFRA_TYPES.keys()}
    
    for cid, country_data in infra_data.get("infrastructure", {}).items():
        country_name = country_data.get("country")
        if not country_name:
            continue
        
        print(f"\n📌 {country_name}:")
        
        country_regions = 0
        country_pvo = {key: 0 for key in total_pvo.keys()}
        country_new = {key: 0 for key in total_new_infra.keys()}
        capital_pvo = None
        
        # Собираем информацию о промышленных объектах для статистики
        total_military_factories = 0
        total_civilian_factories = 0
        total_refineries = 0
        total_power_plants = 0
        
        for econ_region, econ_data in country_data.get("economic_regions", {}).items():
            for region_name, region_data in econ_data.get("regions", {}).items():
                country_regions += 1
                total_regions += 1
                
                # Собираем промышленную статистику
                total_military_factories += region_data.get("military_factories", 0)
                total_civilian_factories += region_data.get("civilian_factories", 0)
                total_refineries += region_data.get("refineries", 0)
                total_power_plants += (
                    region_data.get("thermal_power", 0) +
                    region_data.get("hydro_power", 0) +
                    region_data.get("nuclear_power", 0) * 5  # АЭС считаем с весом
                )
                
                # Проверяем, является ли регион столицей
                is_capital = False
                capital_names = ["Москва", "Санкт-Петербург", "Пекин", "Вашингтон", "Лондон", "Париж", 
                                 "Токио", "Берлин", "Рим", "Мадрид", "Оттава", "Канберра", "Нью-Дели",
                                 "Пхеньян", "Анкара", "Иерусалим", "Тегеран", "Киев", "Минск", "Осло",
                                 "Стокгольм", "Хельсинки", "Варшава", "Бразилиа", "Каир", "Берн"]
                
                for capital in capital_names:
                    if capital in region_name or region_name.startswith(capital):
                        is_capital = True
                        break
                
                for pvo_type in total_pvo.keys():
                    val = region_data.get(pvo_type, 0)
                    country_pvo[pvo_type] += val
                    total_pvo[pvo_type] += val
                    
                    if is_capital and capital_pvo is None:
                        capital_pvo = {
                            "name": region_name,
                            "long": val if pvo_type == "long_range_air_defense" else 0,
                            "short": val if pvo_type == "short_range_air_defense" else 0,
                            "zdprk": val if pvo_type == "zdprk" else 0,
                            "zas": val if pvo_type == "zas" else 0,
                            "radar": val if pvo_type == "radar_systems" else 0
                        }
                    elif is_capital and capital_pvo:
                        if pvo_type == "long_range_air_defense":
                            capital_pvo["long"] = val
                        elif pvo_type == "short_range_air_defense":
                            capital_pvo["short"] = val
                        elif pvo_type == "zdprk":
                            capital_pvo["zdprk"] = val
                        elif pvo_type == "zas":
                            capital_pvo["zas"] = val
                        elif pvo_type == "radar_systems":
                            capital_pvo["radar"] = val
                
                for infra_type in total_new_infra.keys():
                    val = region_data.get(infra_type, 0)
                    country_new[infra_type] += val
                    total_new_infra[infra_type] += val
        
        print(f"   Регионов: {country_regions}")
        print(f"   Промышленность: воен.заводы: {total_military_factories}, гражд.заводы: {total_civilian_factories}, НПЗ: {total_refineries}")
        print(f"   ПВО (ЗРК б/м, ЗПРК, ЗСУ, РЛС): {country_pvo['long_range_air_defense']}/{country_pvo['short_range_air_defense']}/{country_pvo['zdprk']}/{country_pvo['zas']}/{country_pvo['radar_systems']}")
        
        if capital_pvo:
            print(f"   📍 Столица {capital_pvo['name']}: ЗРК большой: {capital_pvo['long']}, ЗРК малой: {capital_pvo['short']}, ЗПРК: {capital_pvo['zdprk']}, ЗСУ: {capital_pvo['zas']}, РЛС: {capital_pvo['radar']}")
        
        # Показываем топ-5 новых объектов
        infra_items = []
        for infra_type, count in country_new.items():
            if count > 0:
                infra_items.append((NEW_INFRA_TYPES[infra_type]['name'], count))
        infra_items.sort(key=lambda x: -x[1])
        
        if infra_items:
            infra_line = "   Новая инфраструктура: "
            infra_line += ", ".join([f"{name}: {count}" for name, count in infra_items[:5]])
            if len(infra_items) > 5:
                infra_line += f" ... и ещё {len(infra_items)-5}"
            print(infra_line)
    
    print("\n" + "="*80)
    print("ИТОГО:")
    print(f"   Всего регионов: {total_regions}")
    print(f"\n   📡 ПВО и РЛС:")
    print(f"      ЗРК большой дальности: {total_pvo['long_range_air_defense']}")
    print(f"      ЗРК малой дальности: {total_pvo['short_range_air_defense']}")
    print(f"      ЗПРК: {total_pvo['zdprk']}")
    print(f"      ЗСУ: {total_pvo['zas']}")
    print(f"      РЛС: {total_pvo['radar_systems']}")
    
    print(f"\n   🏗️ Новая инфраструктура:")
    for infra_type, count in sorted(total_new_infra.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"      {NEW_INFRA_TYPES[infra_type]['name']}: {count}")
    print("="*80)


def main():
    print("🚀 Запуск генерации инфраструктуры с ПВО...")
    print("="*80)
    print("Учитываются факторы:")
    print("   ✅ Специализация региона (столицы, промцентры, военные базы)")
    print("   ✅ Военные и гражданские заводы")
    print("   ✅ НПЗ и нефтебазы")
    print("   ✅ Верфи")
    print("   ✅ Электростанции (ТЭС, ГЭС, АЭС, СЭС, ВЭС)")
    print("   ✅ Уровень развития и население")
    print("="*80)
    
    # Загружаем данные
    states_data = load_json(STATES_FILE)
    infra_data = load_json(INFRA_FILE)
    
    if not states_data:
        print("❌ Не удалось загрузить states_default.json")
        return
    
    if not infra_data:
        print("❌ Не удалось загрузить infrastructure_default.json")
        return
    
    # Создаём резервную копию
    create_backup()
    
    # Обрабатываем инфраструктуру
    print("🔄 Обработка данных...")
    updated_infra = process_infrastructure(states_data, infra_data)
    
    # Сохраняем результат
    save_json(updated_infra, INFRA_FILE)
    print(f"✅ Инфраструктура сохранена в {INFRA_FILE}")
    
    # Выводим статистику
    print_statistics(updated_infra, states_data)
    
    print("\n" + "="*80)
    print("✅ Готово! Файл infrastructure_default.json обновлён.")
    print(f"📁 Резервная копия: {BACKUP_FILE}")
    print("="*80)


if __name__ == "__main__":
    main()

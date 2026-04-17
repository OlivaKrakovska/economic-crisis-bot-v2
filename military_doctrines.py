# military_doctrines.py - Модуль для военных доктрин, появляющихся со временем
# РЕАЛИСТИЧНАЯ ВЕРСИЯ: доктрины основаны на реальных тактиках с 2022 года

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from political_power import spend_political_power, get_political_power
from game_time import get_current_game_time, get_year, get_month, get_game_date_formatted

# Файл для хранения данных о доктринах
DOCTRINES_FILE = 'military_doctrines.json'

# ID канала для публикации завершенных доктрин
DOCTRINE_LOG_CHANNEL_ID = 1263440933232578630

# ==================== БАЗА ДАННЫХ ДОКТРИН ====================

# Дата старта: 1 декабря 2022
# Доктрины основаны на реальных тактиках, появившихся в ходе войны

MILITARY_DOCTRINES = {
    # Анти-дроновая защита (появилась весной 2022)
    "anti_drone_cope_cages": {
        "name": "Противо-дроновые защитные конструкции",
        "description": "Установка импровизированных защитных конструкций (т.н. 'мангалов' и 'копейных клеток') на бронетехнику для защиты от атак FPV-дронов и барражирующих боеприпасов с верхней полусферы. Впервые массово применено в 2022 году.",
        "available_from": "2022-05-01",
        "requirements": {
            "steel": 30,
            "money": 5000000
        },
        "duration_hours": 72,
        "pp_cost": 12,
        "category": "defense",
        "image_url": "https://example.com/cope_cages.jpg"
    },
    
    "anti_drone_ew": {
        "name": "Тактическое применение РЭБ против дронов",
        "description": "Интеграция переносных средств радиоэлектронной борьбы в пехотные отделения для подавления каналов управления FPV-дронов на ближних дистанциях. Разработано в ответ на массовое применение дронов.",
        "available_from": "2022-08-01",
        "requirements": {
            "electronics": 10,
            "money": 15000000
        },
        "duration_hours": 96,
        "pp_cost": 15,
        "category": "electronic_warfare",
        "image_url": "https://example.com/anti_drone_ew.jpg"
    },
    
    # Тактика малых штурмовых групп (2022-2023)
    "small_assault_groups": {
        "name": "Тактика малых штурмовых групп",
        "description": "Переход от массированных штурмов к действиям малыми группами (5-7 человек) при поддержке дронов-разведчиков и артиллерии. Позволяет снизить потери и повысить эффективность в городских боях.",
        "available_from": "2022-09-01",
        "requirements": {
            "money": 2000000
        },
        "duration_hours": 48,
        "pp_cost": 8,
        "category": "infantry_tactics",
        "image_url": "https://example.com/small_assault_groups.jpg"
    },
    
    "fpv_hunter_killer": {
        "name": "Охотничьи группы с FPV-дронами",
        "description": "Создание специализированных групп, оснащенных FPV-дронами для охоты на бронетехнику противника в глубине обороны. Операторы работают в связке с разведывательными дронами.",
        "available_from": "2022-10-01",
        "requirements": {
            "fpv_drones": 50,
            "money": 8000000
        },
        "duration_hours": 84,
        "pp_cost": 14,
        "category": "drone_warfare",
        "image_url": "https://example.com/fpv_hunter_killer.jpg"
    },
    
    # Контрбатарейная борьба (2022)
    "counter_battery_radar_net": {
        "name": "Интегрированная контрбатарейная сеть",
        "description": "Объединение контрбатарейных радаров в единую сеть с автоматической передачей данных артиллерийским подразделениям. Сокращает время реакции до 20-30 секунд.",
        "available_from": "2022-07-01",
        "requirements": {
            "radar_systems": 5,
            "money": 25000000
        },
        "duration_hours": 120,
        "pp_cost": 18,
        "category": "artillery",
        "image_url": "https://example.com/counter_battery.jpg"
    },
    
    "artillery_drone_integration": {
        "name": "Интеграция артиллерии с разведывательными дронами",
        "description": "Организация непрерывного взаимодействия между расчетами артиллерии и подразделениями БПЛА для корректировки огня в реальном времени. Повышает точность и снижает расход боеприпасов.",
        "available_from": "2022-06-01",
        "requirements": {
            "recon_uav": 20,
            "money": 12000000
        },
        "duration_hours": 96,
        "pp_cost": 16,
        "category": "artillery",
        "image_url": "https://example.com/artillery_drone.jpg"
    },
    
    # Логистика в условиях войны (2022-2023)
    "forward_arming_points": {
        "name": "Передовые пункты боепитания",
        "description": "Организация сети малых передовых пунктов боепитания вблизи линии фронта для быстрого пополнения запасов штурмовых групп. Использование легких транспортных средств и квадроциклов.",
        "available_from": "2022-11-01",
        "requirements": {
            "trucks": 50,
            "money": 5000000
        },
        "duration_hours": 72,
        "pp_cost": 10,
        "category": "logistics",
        "image_url": "https://example.com/forward_arming.jpg"
    },
    
    "drone_logistics": {
        "name": "Логистика с использованием дронов",
        "description": "Применение грузовых дронов для доставки боеприпасов, медикаментов и продовольствия на передовые позиции, особенно в условиях, когда наземная логистика затруднена.",
        "available_from": "2023-02-01",
        "requirements": {
            "drones": 30,
            "money": 15000000
        },
        "duration_hours": 96,
        "pp_cost": 14,
        "category": "logistics",
        "image_url": "https://example.com/drone_logistics.jpg"
    },
    
    # Мобильная ПВО (2022-2023)
    "mobile_air_defense_groups": {
        "name": "Мобильные группы ПВО на пикапах",
        "description": "Создание мобильных групп на базе пикапов и легких грузовиков, оснащенных ПЗРК и крупнокалиберными пулеметами, для прикрытия войск от ударных дронов и вертолетов.",
        "available_from": "2022-12-01",
        "requirements": {
            "manpads": 40,
            "trucks": 30,
            "money": 12000000
        },
        "duration_hours": 84,
        "pp_cost": 15,
        "category": "air_defense",
        "image_url": "https://example.com/mobile_ad.jpg"
    },
    
    "anti_uav_net": {
        "name": "Сеть наблюдения за БПЛА",
        "description": "Создание сети наблюдательных постов с оптическими и акустическими датчиками для обнаружения и отслеживания малых дронов, с последующей передачей данных на огневые средства.",
        "available_from": "2023-03-01",
        "requirements": {
            "electronics": 15,
            "money": 20000000
        },
        "duration_hours": 120,
        "pp_cost": 18,
        "category": "air_defense",
        "image_url": "https://example.com/anti_uav_net.jpg"
    },
    
    # Инженерные войска (2022-2023)
    "rapid_fortification_tactics": {
        "name": "Тактика быстрого укрепления позиций",
        "description": "Методика быстрого создания полевых укреплений с использованием сборных железобетонных конструкций и специализированной инженерной техники под огнем противника.",
        "available_from": "2022-08-01",
        "requirements": {
            "engineering_equipment": 15,
            "money": 8000000
        },
        "duration_hours": 96,
        "pp_cost": 12,
        "category": "engineering",
        "image_url": "https://example.com/rapid_fortification.jpg"
    },
    
    "assault_engineering_support": {
        "name": "Инженерная поддержка штурма",
        "description": "Методика использования инженерных машин и саперных подразделений непосредственно в боевых порядках штурмовых групп для проделывания проходов и разграждения препятствий.",
        "available_from": "2023-01-01",
        "requirements": {
            "engineering_equipment": 10,
            "money": 10000000
        },
        "duration_hours": 108,
        "pp_cost": 14,
        "category": "engineering",
        "image_url": "https://example.com/assault_engineer.jpg"
    },
    
    # Медицинская тактика (2022-2023)
    "tactical_combat_casualty_care": {
        "name": "Тактическая медицина на поле боя",
        "description": "Внедрение современных протоколов оказания первой помощи непосредственно под огнем, подготовка тактических медиков в каждом отделении, использование современных кровоостанавливающих средств.",
        "available_from": "2022-10-01",
        "requirements": {
            "medical_supplies": 100,
            "money": 5000000
        },
        "duration_hours": 72,
        "pp_cost": 8,
        "category": "medical",
        "image_url": "https://example.com/tccc.jpg"
    },
    
    "medical_evacuation_drones": {
        "name": "Эвакуация раненых дронами",
        "description": "Использование тяжелых дронов для эвакуации раненых с поля боя, особенно в условиях, когда наземная эвакуация невозможна из-за огня противника.",
        "available_from": "2023-04-01",
        "requirements": {
            "drones": 20,
            "medical_supplies": 50,
            "money": 18000000
        },
        "duration_hours": 120,
        "pp_cost": 16,
        "category": "medical",
        "image_url": "https://example.com/medevac_drone.jpg"
    },
    
    # Глубокие рейды (2023)
    "deep_reconnaissance_raids": {
        "name": "Глубокие разведывательные рейды",
        "description": "Проведение глубоких рейдов разведывательных групп в тыл противника с использованием легкой техники и дронов для вскрытия системы обороны и уничтожения тыловых объектов.",
        "available_from": "2023-05-01",
        "requirements": {
            "armored_vehicles": 15,
            "drones": 20,
            "money": 15000000
        },
        "duration_hours": 144,
        "pp_cost": 18,
        "category": "special_operations",
        "image_url": "https://example.com/deep_raid.jpg"
    },
    
    # Снайперская тактика (2022-2023)
    "counter_sniper_tactics": {
        "name": "Контрснайперская борьба",
        "description": "Методика выявления и уничтожения снайперов противника с использованием акустических датчиков, тепловизоров и дронов, а также подготовка снайперских пар для контрснайперской борьбы.",
        "available_from": "2022-09-01",
        "requirements": {
            "small_arms": 20,
            "electronics": 5,
            "money": 6000000
        },
        "duration_hours": 84,
        "pp_cost": 10,
        "category": "infantry_tactics",
        "image_url": "https://example.com/counter_sniper.jpg"
    },
    
    # Ночные операции (2022)
    "night_ops_tactics": {
        "name": "Тактика ночных операций",
        "description": "Методика ведения боевых действий в ночное время с использованием тепловизоров, приборов ночного видения и осветительных средств. Включает организацию взаимодействия и целеуказания в темноте.",
        "available_from": "2022-11-01",
        "requirements": {
            "electronics": 8,
            "money": 8000000
        },
        "duration_hours": 72,
        "pp_cost": 12,
        "category": "infantry_tactics",
        "image_url": "https://example.com/night_ops.jpg"
    },
    
    # Городские бои (2022-2023)
    "urban_warfare_tactics": {
        "name": "Тактика городского боя",
        "description": "Методика ведения боевых действий в городских условиях: действия штурмовых групп, зачистка зданий, использование подземных коммуникаций, взаимодействие с бронетехникой в городе.",
        "available_from": "2022-12-01",
        "requirements": {
            "money": 10000000
        },
        "duration_hours": 120,
        "pp_cost": 16,
        "category": "infantry_tactics",
        "image_url": "https://example.com/urban_warfare.jpg"
    },
    
    "building_assault_techniques": {
        "name": "Техника штурма зданий",
        "description": "Специализированная тактика штурма многоэтажных зданий, включающая проникновение через верхние этажи, использование альпинистского снаряжения и дронов для разведки внутри помещений.",
        "available_from": "2023-02-01",
        "requirements": {
            "fpv_drones": 20,
            "money": 12000000
        },
        "duration_hours": 96,
        "pp_cost": 14,
        "category": "infantry_tactics",
        "image_url": "https://example.com/building_assault.jpg"
    },
    
    # Противотанковая оборона (2022-2023)
    "anti_tank_defense_zones": {
        "name": "Противотанковые опорные пункты",
        "description": "Создание сети противотанковых опорных пунктов с использованием ПТРК, противотанковых мин и РПГ, прикрытых пехотой и дронами. Обеспечивает эшелонированную противотанковую оборону.",
        "available_from": "2022-10-01",
        "requirements": {
            "atgms": 50,
            "money": 9000000
        },
        "duration_hours": 96,
        "pp_cost": 15,
        "category": "defense",
        "image_url": "https://example.com/anti_tank.jpg"
    },
    
    # РЭБ (2023)
    "electronic_intelligence_gathering": {
        "name": "Радиоэлектронная разведка тактического звена",
        "description": "Организация перехвата и анализа радиопереговоров противника на уровне рота-батальон с использованием компактных средств РЭР, интегрированных с артиллерийскими подразделениями.",
        "available_from": "2023-03-01",
        "requirements": {
            "electronics": 12,
            "ew_vehicles": 3,
            "money": 18000000
        },
        "duration_hours": 108,
        "pp_cost": 17,
        "category": "electronic_warfare",
        "image_url": "https://example.com/electronic_intel.jpg"
    },
    
    # Инженерная разведка (2023)
    "engineering_reconnaissance": {
        "name": "Инженерная разведка дронами",
        "description": "Методика использования дронов для инженерной разведки местности, выявления минных полей, заграждений и оценки состояния переправ. Позволяет планировать инженерное обеспечение наступления.",
        "available_from": "2023-04-01",
        "requirements": {
            "recon_uav": 15,
            "engineering_equipment": 5,
            "money": 10000000
        },
        "duration_hours": 72,
        "pp_cost": 12,
        "category": "engineering",
        "image_url": "https://example.com/eng_recon.jpg"
    },
    
    # Противодействие РЭБ (2023)
    "anti_ew_tactics": {
        "name": "Тактика противодействия РЭБ",
        "description": "Методика защиты каналов управления дронами и связи от подавления средствами РЭБ противника, включая быструю смену частот, использование ретрансляторов и защищенных протоколов.",
        "available_from": "2023-05-01",
        "requirements": {
            "electronics": 15,
            "money": 14000000
        },
        "duration_hours": 96,
        "pp_cost": 15,
        "category": "electronic_warfare",
        "image_url": "https://example.com/anti_ew.jpg"
    },
    
    # Тактика против мин (2023)
    "minefield_breaching_tactics": {
        "name": "Преодоление минных полей под огнем",
        "description": "Методика проделывания проходов в минных полях под огнем противника с использованием инженерных машин разграждения, ударных дронов для подавления огневых точек и дымовых завес.",
        "available_from": "2023-06-01",
        "requirements": {
            "engineering_equipment": 12,
            "money": 20000000
        },
        "duration_hours": 120,
        "pp_cost": 18,
        "category": "engineering",
        "image_url": "https://example.com/breaching.jpg"
    },
    
    # Противотанковые резервы (2023)
    "anti_tank_reserves": {
        "name": "Подвижные противотанковые резервы",
        "description": "Организация подвижных противотанковых резервов на быстроходной технике, оснащенных ПТРК и ударными дронами, для быстрого реагирования на прорывы бронетехники противника.",
        "available_from": "2023-07-01",
        "requirements": {
            "atgm_complexes": 15,
            "armored_vehicles": 20,
            "fpv_drones": 30,
            "money": 16000000
        },
        "duration_hours": 108,
        "pp_cost": 16,
        "category": "defense",
        "image_url": "https://example.com/anti_tank_reserve.jpg"
    },
    
    # Подземная война (2023)
    "underground_warfare": {
        "name": "Тактика подземных боевых действий",
        "description": "Методика ведения боевых действий в подземных коммуникациях, метро, подвалах и катакомбах. Включает особенности ориентирования, связи, боя в замкнутых пространствах и применения дронов.",
        "available_from": "2023-08-01",
        "requirements": {
            "small_arms": 30,
            "fpv_drones": 15,
            "money": 15000000
        },
        "duration_hours": 120,
        "pp_cost": 17,
        "category": "special_operations",
        "image_url": "https://example.com/underground.jpg"
    },
    
    # Противодействие дронам-камикадзе (2023)
    "anti_kamikaze_drone_defense": {
        "name": "Защита от дронов-камикадзе",
        "description": "Комплексная методика защиты от барражирующих боеприпасов, включающая создание ложных целей, использование сетей, мобильных групп с дробовиками и средств РЭБ на маршрутах движения.",
        "available_from": "2023-09-01",
        "requirements": {
            "electronics": 10,
            "money": 12000000
        },
        "duration_hours": 84,
        "pp_cost": 14,
        "category": "defense",
        "image_url": "https://example.com/anti_kamikaze.jpg"
    },
    
    # Морские дроны (2023-2024)
    "naval_drone_warfare": {
        "name": "Тактика применения морских дронов",
        "description": "Методика использования надводных беспилотных аппаратов для атак на корабли, портовую инфраструктуру и мосты. Включает тактику массированных атак и противодействия средствам охраны.",
        "available_from": "2023-10-01",
        "requirements": {
            "electronics": 25,
            "missiles": 10,
            "ships": 5,
            "money": 30000000
        },
        "duration_hours": 168,
        "pp_cost": 22,
        "category": "naval",
        "image_url": "https://example.com/naval_drone.jpg"
    },
    
    # Контрбатарейная борьба с дронами (2023)
    "counter_battery_drones": {
        "name": "Контрбатарейная борьба дронами",
        "description": "Использование FPV-дронов для охоты на артиллерийские расчеты противника сразу после выстрела, пока они не покинули позицию. Требует быстрой координации между акустическими датчиками и операторами дронов.",
        "available_from": "2023-11-01",
        "requirements": {
            "fpv_drones": 60,
            "radar_systems": 3,
            "money": 22000000
        },
        "duration_hours": 132,
        "pp_cost": 19,
        "category": "drone_warfare",
        "image_url": "https://example.com/counter_battery_drone.jpg"
    },
    
    # Зимняя война (2023)
    "winter_warfare_tactics": {
        "name": "Тактика зимних операций",
        "description": "Методика ведения боевых действий в зимних условиях: маскировка, передвижение по снегу, организация обогрева, предотвращение обморожений, использование зимних камуфляжей.",
        "available_from": "2023-12-01",
        "requirements": {
            "money": 5000000
        },
        "duration_hours": 72,
        "pp_cost": 8,
        "category": "infantry_tactics",
        "image_url": "https://example.com/winter_warfare.jpg"
    },
    
    # Речные операции (2023)
    "river_crossing_tactics": {
        "name": "Форсирование водных преград",
        "description": "Методика форсирования рек под огнем противника с использованием понтонных переправ, амфибийной техники и дымовых завес. Включает организацию противодесантной обороны на захваченном плацдарме.",
        "available_from": "2023-07-01",
        "requirements": {
            "engineering_equipment": 15,
            "boats": 20,
            "money": 18000000
        },
        "duration_hours": 120,
        "pp_cost": 16,
        "category": "engineering",
        "image_url": "https://example.com/river_crossing.jpg"
    },
    
    # Противодействие спутниковой разведке (2023)
    "satellite_countermeasures": {
        "name": "Противодействие спутниковой разведке",
        "description": "Методика маскировки войск и техники от спутниковой разведки, включая использование маскировочных сетей, ложных целей, аэрозолей и изменение режимов передвижения с учетом пролетов спутников.",
        "available_from": "2023-09-01",
        "requirements": {
            "money": 12000000
        },
        "duration_hours": 96,
        "pp_cost": 14,
        "category": "defense",
        "image_url": "https://example.com/satellite_countermeasures.jpg"
    },
    
    # Подготовка резервов (2023)
    "reserve_training_program": {
        "name": "Ускоренная подготовка резервистов",
        "description": "Программа интенсивной подготовки мобилизованных резервистов по сокращенной программе, с акцентом на практические навыки владения оружием, тактической медицины и взаимодействия в малых группах.",
        "available_from": "2023-01-01",
        "requirements": {
            "money": 15000000
        },
        "duration_hours": 168,
        "pp_cost": 12,
        "category": "training",
        "image_url": "https://example.com/reserve_training.jpg"
    }
}

# Категории для группировки (используются только в интерфейсе)
DOCTRINE_CATEGORIES = {
    "infantry_tactics": "Пехотная тактика",
    "defense": "Оборона",
    "artillery": "Артиллерия",
    "drone_warfare": "БПЛА",
    "electronic_warfare": "РЭБ",
    "logistics": "Логистика",
    "air_defense": "ПВО",
    "engineering": "Инженерные войска",
    "medical": "Медицина",
    "special_operations": "Спецоперации",
    "naval": "Военно-морские силы",
    "training": "Подготовка"
}

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_doctrines():
    """Загружает данные о военных доктринах"""
    try:
        with open(DOCTRINES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"researching": [], "completed": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"researching": [], "completed": []}

def save_doctrines(data):
    """Сохраняет данные о военных доктринах"""
    with open(DOCTRINES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==================== ПРОВЕРКА ДОСТУПНОСТИ ====================

def is_doctrine_available(doctrine_id: str) -> bool:
    """Проверяет, доступна ли доктрина по дате"""
    doctrine = MILITARY_DOCTRINES.get(doctrine_id)
    if not doctrine:
        return False
    
    available_from = datetime.strptime(doctrine["available_from"], "%Y-%m-%d")
    current_game_date, _ = get_current_game_time()
    
    return current_game_date >= available_from

def get_available_doctrines() -> List[str]:
    """Возвращает список ID доктрин, доступных по дате"""
    available = []
    for doctrine_id in MILITARY_DOCTRINES:
        if is_doctrine_available(doctrine_id):
            available.append(doctrine_id)
    return available

def can_research_doctrine(player_data, doctrine_id: str) -> Tuple[bool, str]:
    """
    Проверяет, может ли игрок начать исследование доктрины
    """
    doctrine = MILITARY_DOCTRINES.get(doctrine_id)
    if not doctrine:
        return False, "Доктрина не найдена"
    
    # Проверяем доступность по дате
    if not is_doctrine_available(doctrine_id):
        return False, f"Доктрина станет доступна с {doctrine['available_from']}"
    
    # Проверяем, не исследуется ли уже
    doctrines_data = load_doctrines()
    user_id = str(player_data.get("assigned_to", ""))
    
    for research in doctrines_data["researching"]:
        if research["user_id"] == user_id and research["doctrine_id"] == doctrine_id:
            return False, "Эта доктрина уже исследуется"
    
    # Проверяем, не изучена ли уже
    for completed in doctrines_data["completed"]:
        if completed["user_id"] == user_id and completed["doctrine_id"] == doctrine_id:
            return False, "Эта доктрина уже изучена"
    
    # Проверяем бюджет
    money_needed = doctrine["requirements"].get("money", 0)
    if player_data["economy"]["budget"] < money_needed:
        return False, f"Недостаточно средств! Нужно: {format_billion(money_needed)}"
    
    # Проверяем ресурсы
    steel_needed = doctrine["requirements"].get("steel", 0)
    if steel_needed > 0:
        resources = player_data.get("resources", {})
        if resources.get("steel", 0) < steel_needed:
            return False, f"Недостаточно стали! Нужно: {steel_needed}, есть: {resources.get('steel', 0)}"
    
    electronics_needed = doctrine["requirements"].get("electronics", 0)
    if electronics_needed > 0:
        resources = player_data.get("resources", {})
        if resources.get("electronics", 0) < electronics_needed:
            return False, f"Недостаточно электроники! Нужно: {electronics_needed}, есть: {resources.get('electronics', 0)}"
    
    # Проверяем военную технику
    if "fpv_drones" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("equipment", {})
        needed = doctrine["requirements"]["fpv_drones"]
        if army.get("fpv_drones", 0) < needed:
            return False, f"Недостаточно FPV-дронов! Нужно: {needed}, есть: {army.get('fpv_drones', 0)}"
    
    if "recon_uav" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("air", {})
        needed = doctrine["requirements"]["recon_uav"]
        if army.get("recon_uav", 0) < needed:
            return False, f"Недостаточно разведывательных БПЛА! Нужно: {needed}, есть: {army.get('recon_uav', 0)}"
    
    if "radar_systems" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("ground", {})
        needed = doctrine["requirements"]["radar_systems"]
        if army.get("radar_systems", 0) < needed:
            return False, f"Недостаточно РЛС! Нужно: {needed}, есть: {army.get('radar_systems', 0)}"
    
    if "manpads" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("equipment", {})
        needed = doctrine["requirements"]["manpads"]
        if army.get("manpads", 0) < needed:
            return False, f"Недостаточно ПЗРК! Нужно: {needed}, есть: {army.get('manpads', 0)}"
    
    if "atgms" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("equipment", {})
        needed = doctrine["requirements"]["atgms"]
        if army.get("atgms", 0) < needed:
            return False, f"Недостаточно ПТРК! Нужно: {needed}, есть: {army.get('atgms', 0)}"
    
    if "atgm_complexes" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("ground", {})
        needed = doctrine["requirements"]["atgm_complexes"]
        if army.get("atgm_complexes", 0) < needed:
            return False, f"Недостаточно противотанковых комплексов! Нужно: {needed}, есть: {army.get('atgm_complexes', 0)}"
    
    if "engineering_equipment" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("ground", {})
        needed = doctrine["requirements"]["engineering_equipment"]
        if army.get("engineering_equipment", 0) < needed:
            return False, f"Недостаточно инженерной техники! Нужно: {needed}, есть: {army.get('engineering_equipment', 0)}"
    
    if "trucks" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("ground", {})
        needed = doctrine["requirements"]["trucks"]
        if army.get("trucks", 0) < needed:
            return False, f"Недостаточно грузовиков! Нужно: {needed}, есть: {army.get('trucks', 0)}"
    
    if "armored_vehicles" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("ground", {})
        needed = doctrine["requirements"]["armored_vehicles"]
        if army.get("armored_vehicles", 0) < needed:
            return False, f"Недостаточно бронеавтомобилей! Нужно: {needed}, есть: {army.get('armored_vehicles', 0)}"
    
    if "boats" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("navy", {})
        needed = doctrine["requirements"]["boats"]
        if army.get("boats", 0) < needed:
            return False, f"Недостаточно катеров! Нужно: {needed}, есть: {army.get('boats', 0)}"
    
    if "ships" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("navy", {})
        total_ships = sum(army.values()) if isinstance(army, dict) else 0
        needed = doctrine["requirements"]["ships"]
        if total_ships < needed:
            return False, f"Недостаточно кораблей! Нужно: {needed}"
    
    if "missiles" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("missiles", {})
        total_missiles = sum(army.values()) if isinstance(army, dict) else 0
        needed = doctrine["requirements"]["missiles"]
        if total_missiles < needed:
            return False, f"Недостаточно ракет! Нужно: {needed}"
    
    if "small_arms" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("equipment", {})
        needed = doctrine["requirements"]["small_arms"]
        if army.get("small_arms", 0) < needed:
            return False, f"Недостаточно стрелкового оружия! Нужно: {needed}, есть: {army.get('small_arms', 0)}"
    
    if "medical_supplies" in doctrine["requirements"]:
        civil_goods = player_data.get("civil_goods", {})
        needed = doctrine["requirements"]["medical_supplies"]
        if civil_goods.get("medical_supplies", 0) < needed:
            return False, f"Недостаточно медикаментов! Нужно: {needed}, есть: {civil_goods.get('medical_supplies', 0)}"
    
    if "ew_vehicles" in doctrine["requirements"]:
        army = player_data.get("army", {}).get("ground", {})
        needed = doctrine["requirements"]["ew_vehicles"]
        if army.get("ew_vehicles", 0) < needed:
            return False, f"Недостаточно машин РЭБ! Нужно: {needed}, есть: {army.get('ew_vehicles', 0)}"
    
    # Проверяем политическую власть
    current_pp = get_political_power(player_data)
    if current_pp < doctrine["pp_cost"]:
        return False, f"Недостаточно политической власти! Нужно: {doctrine['pp_cost']}, у вас: {current_pp:.1f}"
    
    return True, "OK"

def start_research(player_data, doctrine_id: str) -> bool:
    """
    Начинает исследование доктрины (списывает ресурсы)
    """
    doctrine = MILITARY_DOCTRINES[doctrine_id]
    
    # Списываем деньги
    money_needed = doctrine["requirements"].get("money", 0)
    if money_needed > 0:
        player_data["economy"]["budget"] -= money_needed
    
    # Списываем ресурсы
    steel_needed = doctrine["requirements"].get("steel", 0)
    if steel_needed > 0:
        if "resources" in player_data:
            player_data["resources"]["steel"] = player_data["resources"].get("steel", 0) - steel_needed
    
    electronics_needed = doctrine["requirements"].get("electronics", 0)
    if electronics_needed > 0:
        if "resources" in player_data:
            player_data["resources"]["electronics"] = player_data["resources"].get("electronics", 0) - electronics_needed
    
    # Списываем военную технику
    if "fpv_drones" in doctrine["requirements"]:
        player_data["army"]["equipment"]["fpv_drones"] -= doctrine["requirements"]["fpv_drones"]
    
    if "recon_uav" in doctrine["requirements"]:
        player_data["army"]["air"]["recon_uav"] -= doctrine["requirements"]["recon_uav"]
    
    if "radar_systems" in doctrine["requirements"]:
        player_data["army"]["ground"]["radar_systems"] -= doctrine["requirements"]["radar_systems"]
    
    if "manpads" in doctrine["requirements"]:
        player_data["army"]["equipment"]["manpads"] -= doctrine["requirements"]["manpads"]
    
    if "atgms" in doctrine["requirements"]:
        player_data["army"]["equipment"]["atgms"] -= doctrine["requirements"]["atgms"]
    
    if "atgm_complexes" in doctrine["requirements"]:
        player_data["army"]["ground"]["atgm_complexes"] -= doctrine["requirements"]["atgm_complexes"]
    
    if "engineering_equipment" in doctrine["requirements"]:
        player_data["army"]["ground"]["engineering_equipment"] -= doctrine["requirements"]["engineering_equipment"]
    
    if "trucks" in doctrine["requirements"]:
        player_data["army"]["ground"]["trucks"] -= doctrine["requirements"]["trucks"]
    
    if "armored_vehicles" in doctrine["requirements"]:
        player_data["army"]["ground"]["armored_vehicles"] -= doctrine["requirements"]["armored_vehicles"]
    
    if "ew_vehicles" in doctrine["requirements"]:
        player_data["army"]["ground"]["ew_vehicles"] -= doctrine["requirements"]["ew_vehicles"]
    
    if "boats" in doctrine["requirements"]:
        player_data["army"]["navy"]["boats"] -= doctrine["requirements"]["boats"]
    
    if "medical_supplies" in doctrine["requirements"]:
        player_data["civil_goods"]["medical_supplies"] -= doctrine["requirements"]["medical_supplies"]
    
    if "small_arms" in doctrine["requirements"]:
        player_data["army"]["equipment"]["small_arms"] -= doctrine["requirements"]["small_arms"]
    
    # Списываем ПВ
    spend_political_power(player_data, doctrine["pp_cost"])
    
    # Добавляем в очередь исследований
    doctrines_data = load_doctrines()
    user_id = str(player_data.get("assigned_to", ""))
    
    completion_time = datetime.now() + timedelta(hours=doctrine["duration_hours"])
    
    doctrines_data["researching"].append({
        "user_id": user_id,
        "country": player_data["state"]["statename"],
        "doctrine_id": doctrine_id,
        "doctrine_name": doctrine["name"],
        "start_time": str(datetime.now()),
        "completion_time": str(completion_time),
        "notified": False
    })
    
    save_doctrines(doctrines_data)
    return True

# ==================== ФОНОВАЯ ЗАДАЧА ДЛЯ ЗАВЕРШЕНИЯ ====================

async def doctrines_completion_loop(bot_instance):
    """Фоновая задача для проверки завершения исследования доктрин"""
    await bot_instance.wait_until_ready()
    
    while not bot_instance.is_closed():
        try:
            doctrines_data = load_doctrines()
            states = load_states()
            now = datetime.now()
            
            completed = []
            
            for research in doctrines_data["researching"][:]:
                completion = datetime.fromisoformat(research["completion_time"])
                
                if completion <= now and not research.get("notified", False):
                    # Находим игрока
                    player_data = None
                    for data in states["players"].values():
                        if data.get("assigned_to") == research["user_id"]:
                            player_data = data
                            break
                    
                    if player_data:
                        # Добавляем в завершенные
                        research["status"] = "completed"
                        research["completed_at"] = str(now)
                        doctrines_data["completed"].append(research)
                        doctrines_data["researching"].remove(research)
                        completed.append(research)
                        
                        # Отправляем сообщение в канал
                        try:
                            channel = bot_instance.get_channel(DOCTRINE_LOG_CHANNEL_ID)
                            if channel:
                                doctrine = MILITARY_DOCTRINES.get(research["doctrine_id"])
                                if doctrine:
                                    embed = discord.Embed(
                                        title="Военная доктрина внедрена",
                                        description=f"Армия государства **{research['country']}** завершила внедрение военной доктрины **{doctrine['name']}** в вооружённые силы.",
                                        color=discord.Color.gold()
                                    )
                                    embed.add_field(name="Категория", value=DOCTRINE_CATEGORIES.get(doctrine.get("category", ""), doctrine.get("category", "Общая")), inline=True)
                                    embed.add_field(name="Время внедрения", value=f"{doctrine['duration_hours']} часов", inline=True)
                                    await channel.send(embed=embed)
                        except Exception as e:
                            print(f"Ошибка при отправке в канал: {e}")
                        
                        # Уведомляем игрока в ЛС
                        try:
                            user = await bot_instance.fetch_user(int(research["user_id"]))
                            if user:
                                doctrine = MILITARY_DOCTRINES.get(research["doctrine_id"])
                                embed = discord.Embed(
                                    title="Военная доктрина изучена",
                                    description=f"Доктрина **{doctrine['name']}** успешно внедрена в армию.",
                                    color=discord.Color.green()
                                )
                                embed.add_field(name="Категория", value=DOCTRINE_CATEGORIES.get(doctrine.get("category", ""), doctrine.get("category", "Общая")), inline=True)
                                await user.send(embed=embed)
                        except:
                            pass
                    
                    research["notified"] = True
            
            if completed:
                save_doctrines(doctrines_data)
                save_states(states)
                print(f"✅ Завершено {len(completed)} военных доктрин")
            
            await asyncio.sleep(60)  # Проверка каждую минуту
            
        except Exception as e:
            print(f"❌ Ошибка в doctrines_completion_loop: {e}")
            await asyncio.sleep(60)

# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class DoctrineSelect(Select):
    """Выбор доктрины для изучения"""
    
    def __init__(self, user_id, player_data, available_doctrines, original_message):
        self.user_id = user_id
        self.player_data = player_data
        self.available_doctrines = available_doctrines
        self.original_message = original_message
        
        options = []
        for doctrine_id in available_doctrines[:25]:
            doctrine = MILITARY_DOCTRINES[doctrine_id]
            cat_name = DOCTRINE_CATEGORIES.get(doctrine.get("category", ""), doctrine.get("category", "Общая"))
            
            options.append(
                discord.SelectOption(
                    label=doctrine['name'][:90],
                    description=f"{cat_name} | {doctrine['duration_hours']} ч",
                    value=doctrine_id
                )
            )
        
        super().__init__(
            placeholder="Выберите военную доктрину...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        doctrine_id = self.values[0]
        doctrine = MILITARY_DOCTRINES[doctrine_id]
        
        embed = discord.Embed(
            title=doctrine['name'],
            description=doctrine['description'],
            color=DARK_THEME_COLOR
        )
        
        # Требования
        req_text = ""
        if doctrine["requirements"].get("money", 0) > 0:
            req_text += f"• Деньги: {format_billion(doctrine['requirements']['money'])}\n"
        if doctrine["requirements"].get("steel", 0) > 0:
            req_text += f"• Сталь: {doctrine['requirements']['steel']} ед.\n"
        if doctrine["requirements"].get("electronics", 0) > 0:
            req_text += f"• Электроника: {doctrine['requirements']['electronics']} ед.\n"
        
        # Военная техника
        if doctrine["requirements"].get("fpv_drones", 0) > 0:
            req_text += f"• FPV-дроны: {doctrine['requirements']['fpv_drones']} ед.\n"
        if doctrine["requirements"].get("recon_uav", 0) > 0:
            req_text += f"• Разведывательные БПЛА: {doctrine['requirements']['recon_uav']} ед.\n"
        if doctrine["requirements"].get("radar_systems", 0) > 0:
            req_text += f"• РЛС: {doctrine['requirements']['radar_systems']} ед.\n"
        if doctrine["requirements"].get("manpads", 0) > 0:
            req_text += f"• ПЗРК: {doctrine['requirements']['manpads']} ед.\n"
        if doctrine["requirements"].get("atgms", 0) > 0:
            req_text += f"• ПТРК (переносные): {doctrine['requirements']['atgms']} ед.\n"
        if doctrine["requirements"].get("atgm_complexes", 0) > 0:
            req_text += f"• ПТРК (самоходные): {doctrine['requirements']['atgm_complexes']} ед.\n"
        if doctrine["requirements"].get("engineering_equipment", 0) > 0:
            req_text += f"• Инженерная техника: {doctrine['requirements']['engineering_equipment']} ед.\n"
        if doctrine["requirements"].get("trucks", 0) > 0:
            req_text += f"• Грузовики: {doctrine['requirements']['trucks']} ед.\n"
        if doctrine["requirements"].get("armored_vehicles", 0) > 0:
            req_text += f"• Бронеавтомобили: {doctrine['requirements']['armored_vehicles']} ед.\n"
        if doctrine["requirements"].get("ew_vehicles", 0) > 0:
            req_text += f"• Машины РЭБ: {doctrine['requirements']['ew_vehicles']} ед.\n"
        if doctrine["requirements"].get("boats", 0) > 0:
            req_text += f"• Катера: {doctrine['requirements']['boats']} ед.\n"
        if doctrine["requirements"].get("ships", 0) > 0:
            req_text += f"• Корабли: {doctrine['requirements']['ships']} ед.\n"
        if doctrine["requirements"].get("missiles", 0) > 0:
            req_text += f"• Ракеты: {doctrine['requirements']['missiles']} ед.\n"
        if doctrine["requirements"].get("small_arms", 0) > 0:
            req_text += f"• Стрелковое оружие: {doctrine['requirements']['small_arms']} ед.\n"
        if doctrine["requirements"].get("medical_supplies", 0) > 0:
            req_text += f"• Медикаменты: {doctrine['requirements']['medical_supplies']} ед.\n"
        
        req_text += f"• Политическая власть: {doctrine['pp_cost']}\n"
        req_text += f"• Время: {doctrine['duration_hours']} часов"
        
        embed.add_field(name="Требования", value=req_text, inline=False)
        
        # Информация о доступности
        if not is_doctrine_available(doctrine_id):
            embed.add_field(name="Статус", value=f"❌ Станет доступна с {doctrine['available_from']}", inline=False)
        else:
            embed.add_field(name="Статус", value="✅ Доступна сейчас", inline=False)
        
        view = DoctrineConfirmationView(self.user_id, self.player_data, doctrine_id)
        
        await interaction.response.edit_message(embed=embed, view=view)


class DoctrineConfirmationView(View):
    """Подтверждение начала изучения доктрины"""
    
    def __init__(self, user_id, player_data, doctrine_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
        self.doctrine_id = doctrine_id
    
    @discord.ui.button(label="Начать внедрение", style=discord.ButtonStyle.secondary)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверяем возможность
        can_research, message = can_research_doctrine(self.player_data, self.doctrine_id)
        if not can_research:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Начинаем исследование
        success = start_research(self.player_data, self.doctrine_id)
        
        if not success:
            await interaction.response.send_message("❌ Ошибка при начале исследования!", ephemeral=True)
            return
        
        # Сохраняем изменения
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                data.update(self.player_data)
                break
        save_states(states)
        
        doctrine = MILITARY_DOCTRINES[self.doctrine_id]
        
        embed = discord.Embed(
            title="Внедрение начато",
            description=f"Военная доктрина **{doctrine['name']}** запущена в разработку.\nВремя завершения: {doctrine['duration_hours']} часов.",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Действие отменено",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ОСНОВНОЕ МЕНЮ ====================

async def show_doctrines_menu(ctx, user_id: int):
    """Показать меню военных доктрин"""
    
    states = load_states()
    
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        if hasattr(ctx, 'response'):
            await ctx.response.send_message("❌ У вас нет государства!", ephemeral=True)
        else:
            await ctx.send("❌ У вас нет государства!")
        return
    
    country_name = player_data["state"]["statename"]
    current_pp = get_political_power(player_data)
    
    # Получаем доступные доктрины
    all_available = get_available_doctrines()
    
    # Фильтруем те, что еще не изучены и не в процессе
    doctrines_data = load_doctrines()
    user_id_str = str(user_id)
    
    researching_ids = [r["doctrine_id"] for r in doctrines_data["researching"] if r["user_id"] == user_id_str]
    completed_ids = [c["doctrine_id"] for c in doctrines_data["completed"] if c["user_id"] == user_id_str]
    
    available_doctrines = [d for d in all_available if d not in researching_ids and d not in completed_ids]
    
    # Текущие исследования
    researching = [r for r in doctrines_data["researching"] if r["user_id"] == user_id_str]
    
    embed = discord.Embed(
        title="Военные доктрины",
        description="Внедрение новых тактик и технологий в армию",
        color=DARK_THEME_COLOR
    )
    
    # Информация о текущих исследованиях
    if researching:
        research_text = ""
        now = datetime.now()
        for r in researching:
            completion = datetime.fromisoformat(r["completion_time"])
            remaining = (completion - now).total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            
            research_text += f"• {r['doctrine_name']}: {hours}ч {minutes}м осталось\n"
        embed.add_field(name="Внедряется", value=research_text, inline=False)
    
    # Завершенные
    completed = [c for c in doctrines_data["completed"] if c["user_id"] == user_id_str]
    if completed:
        completed_text = ""
        for c in completed[-3:]:  # последние 3
            completed_text += f"• {c['doctrine_name']}\n"
        embed.add_field(name="Завершено", value=completed_text, inline=False)
    
    embed.add_field(
        name="Политическая власть",
        value=f"{current_pp:.1f} ПВ",
        inline=True
    )
    
    embed.add_field(
        name="Доступно доктрин",
        value=str(len(available_doctrines)),
        inline=True
    )
    
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, ephemeral=True)
        message = await ctx.original_response()
    else:
        message = await ctx.send(embed=embed, ephemeral=True)
    
    if available_doctrines:
        select = DoctrineSelect(user_id, player_data, available_doctrines, message)
        view = View(timeout=120)
        view.add_item(select)
        await message.edit(view=view)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_doctrines_menu',
    'doctrines_completion_loop',
    'MILITARY_DOCTRINES'
]

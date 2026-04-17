# mobilization.py - Модуль для мобилизации населения и управления призывом
# Версия 5.7 - исправлены эфемерные сообщения и логирование

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from infra_build import load_infrastructure, save_infrastructure
from political_power import get_political_power, spend_political_power

# ==================== ФАЙЛЫ ДЛЯ ХРАНЕНИЯ ДАННЫХ ====================

MOBILIZATION_FILE = 'mobilization.json'
CONVERSION_FILE = 'factory_conversion.json'
RESERVES_FILE = 'reserves.json'
CONVERSION_QUEUE_FILE = 'conversion_queue.json'
MOBILIZATION_PLAN_FILE = 'mobilization_plan.json'

# ==================== КАНАЛ ЛОГИРОВАНИЯ ====================

MOBILIZATION_LOG_CHANNEL_ID = 1131208390102749266

# ==================== КАРТИНКИ ДЛЯ ЭМБЕДОВ ====================

MOBILIZATION_IMAGE = "https://media.discordapp.net/attachments/1184605373026553977/1185315168658395156/1200_0_1646222675-3700.jpg?ex=69c837c6&is=69c6e646&hm=8c69660a9c21ee9ffbf8e577a96c63e621b1108e8f73ff31ad558077a06f48d8&=&format=webp&width=876&height=581"
MOBILIZATION_IMAGE2 = "https://avatars.mds.yandex.net/i?id=f1788c166049f389d688a672ae41ea9f_l-5173519-images-thumbs&n=13"
FACTORY_CONVERSION_IMAGE = "https://images-ext-1.discordapp.net/external/-0MWAaWY0B-NXXXyDS3Dzi72j5xSEO8vpbTtOp_XF8A/https/upload.wikimedia.org/wikipedia/commons/8/8d/Solnhofer_Zementwerke_002.JPG?format=webp&width=875&height=583"
INDUSTRIAL_MOBILIZATION_IMAGE = "https://ptgs.ru/upload/resize_cache/iblock/d0b/872_556_2/xwn5vrhr7kztpkpx9n7c4zn61j9w1xnq.jpg"
RESERVES_IMAGE = "https://rossaprimavera.ru/static/files/f3b663eec1cc.jpg"

# ==================== СЕРВЕРНЫЕ ЭМОДЗИ ====================

EMOJIS = {
    "manpower": "<:Manpower:1256977159356940311>",
    "aluminum": "<:Aluminum:1262014029162086420>",
    "steel": "<:Steel:1262013994454220894>",
    "soldier": "<:soldat:1487167083619024976>",
    "civilian_factory": "<:Civilian_factories:1256638564041756684>",
    "car": "<:avto:1271134652454928396>",
    "truck": "<:gruzovik:1270687377337225226>",
    "weapon": "<:strelok:1487015420895690842>",
    "electronics": "<:enthernet:1459183434726637711>",
    "military_factory": "<:military_factory:1256638572353683467>",
    "reserves": "<:reserv:1432463316445564978>",
    "tank": "<:bm:1270686898557554781>",
    "drone": "<:dronchik:1487016323732213760>",
    "ship": "<:ship:1256638568772272199>",
    "missile": "<:missile:1256638574505422930>",
    "aircraft": "<:aircraft:1256638577118470154>",
    "clock": "<:clock:1256638575611678730>",
    "money": "<:bank:1453457581153718322>",
    "factory": "<:factory:1256638570258178129>"
}


# ==================== ФУНКЦИЯ ЛОГИРОВАНИЯ ====================

async def send_mobilization_log(bot, event_type: str, data: Dict):
    """Отправляет лог о мобилизации в канал"""
    if not bot:
        return
    
    channel = bot.get_channel(MOBILIZATION_LOG_CHANNEL_ID)
    if not channel:
        return
    
    embed = discord.Embed(color=data.get("color", DARK_THEME_COLOR))
    
    if event_type == "mobilization_start":
        embed.title = f"{EMOJIS['soldier']} МОБИЛИЗАЦИЯ НАСЕЛЕНИЯ"
        
        if data.get("type") == "partial":
            deviation = random.uniform(0.1, 0.2)
            actual_target = int(data["target"] * (1 + random.uniform(-deviation, deviation)))
            embed.description = (
                f"**{data['country']}** объявило о начале **частичной мобилизации** населения.\n\n"
                f"План призыва по предварительным оценкам составляет около **{format_number(actual_target)}** человек "
                f"(планировалось {format_number(data['target'])}).\n\n"
                f"Время завершения мобилизации: **{data['hours']}** часов."
            )
        else:
            embed.description = (
                f"**{data['country']}** объявило о начале **всеобщей мобилизации** населения.\n\n"
                f"План призыва составляет **{format_number(data['target'])}** человек.\n\n"
                f"Время завершения мобилизации: **{data['hours']}** часов."
            )
        
        embed.set_image(url=MOBILIZATION_IMAGE)
        embed.set_footer(text="Мобилизационный ресурс: 7% населения")
    
    elif event_type == "mobilization_complete":
        embed.title = f"{EMOJIS['soldier']} МОБИЛИЗАЦИЯ ЗАВЕРШЕНА"
        embed.description = (
            f"**{data['country']}** завершило мобилизацию населения.\n\n"
            f"В армию призвано **{format_number(data['mobilized'])}** человек."
        )
        embed.set_image(url=MOBILIZATION_IMAGE2)
    
    elif event_type == "demobilization_start":
        embed.title = f"{EMOJIS['manpower']} ДЕМОБИЛИЗАЦИЯ"
        embed.description = (
            f"**{data['country']}** начало демобилизацию.\n\n"
            f"Планируется демобилизовать **{format_number(data['target'])}** человек.\n\n"
            f"Время завершения: **{data['hours']}** часов."
        )
        embed.set_image(url=MOBILIZATION_IMAGE2)
    
    elif event_type == "demobilization_complete":
        embed.title = f"{EMOJIS['manpower']} ДЕМОБИЛИЗАЦИЯ ЗАВЕРШЕНА"
        embed.description = (
            f"**{data['country']}** завершило демобилизацию.\n\n"
            f"Демобилизовано **{format_number(data['demobilized'])}** человек."
        )
        embed.set_image(url=MOBILIZATION_IMAGE2)
    
    elif event_type == "factory_conversion":
        embed.title = f"{EMOJIS['military_factory']} КОНВЕРСИЯ ФАБРИК"
        embed.description = (
            f"**{data['country']}** начало конвертацию гражданских фабрик в военные.\n\n"
            f"Регион: **{data['region']}**\n"
            f"Конвертировано фабрик: **{data['factories']}**\n"
            f"Стоимость: **{format_billion(data['cost'])}**\n\n"
            f"Время завершения: **{data['hours']}** часов."
        )
        embed.set_image(url=FACTORY_CONVERSION_IMAGE)
    
    elif event_type == "industrial_production":
        embed.title = f"{EMOJIS['civilian_factory']} ПРОМЫШЛЕННАЯ МОБИЛИЗАЦИЯ"
        embed.description = (
            f"**{data['country']}** начало производство **{data['recipe_name']}**.\n\n"
            f"Регион: **{data['region']}**\n"
            f"Количество партий: **{data['quantity']}**\n"
            f"Ожидаемый выпуск: **{data['output_quantity']}** ед.\n"
            f"Время производства: **{data['minutes']}** минут."
        )
        embed.set_image(url=INDUSTRIAL_MOBILIZATION_IMAGE)
    
    elif event_type == "reserves_activation":
        embed.title = f"{EMOJIS['reserves']} РАСКОНСЕРВАЦИЯ ТЕХНИКИ"
        embed.description = (
            f"**{data['country']}** начало расконсервацию военной техники.\n\n"
            f"Тип: **{data['tech_name']}**\n"
            f"Количество: **{format_number(data['quantity'])}** ед.\n"
            f"Стоимость: **{format_billion(data['cost'])}**\n\n"
            f"Время завершения: **{data['hours']:.1f}** часов."
        )
        embed.set_image(url=RESERVES_IMAGE)
    
    embed.set_footer(text=f"Игровое время: {datetime.now().strftime('%d.%m.%Y')}")
    await channel.send(embed=embed)


# ==================== ИМПОРТ ПРОИЗВОДСТВЕННЫХ ДАННЫХ ====================

try:
    from corp_store import PRODUCTION_SPEED, EQUIPMENT_NAMES, format_time
    CORP_STORE_AVAILABLE = True
except ImportError:
    CORP_STORE_AVAILABLE = False
    PRODUCTION_SPEED = {}
    EQUIPMENT_NAMES = {}
    
    def format_time(seconds):
        if seconds < 60:
            return f"{seconds:.0f} сек"
        elif seconds < 3600:
            return f"{seconds // 60} мин"
        elif seconds < 86400:
            return f"{seconds // 3600} ч"
        else:
            return f"{seconds // 86400} дн"


# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_mobilization():
    try:
        with open(MOBILIZATION_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_programs": [], "completed_programs": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_programs": [], "completed_programs": []}

def save_mobilization(data):
    with open(MOBILIZATION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_mobilization_plan():
    try:
        with open(MOBILIZATION_PLAN_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"plans": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"plans": {}}

def save_mobilization_plan(data):
    with open(MOBILIZATION_PLAN_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_reserves():
    try:
        with open(RESERVES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"activated": {}, "remaining_reserves": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"activated": {}, "remaining_reserves": {}}

def save_reserves(data):
    with open(RESERVES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_conversion_queue():
    try:
        with open(CONVERSION_QUEUE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_conversions": [], "completed_conversions": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_conversions": [], "completed_conversions": []}

def save_conversion_queue(data):
    with open(CONVERSION_QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_factory_conversions():
    try:
        with open(CONVERSION_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"conversions": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"conversions": {}}

def save_factory_conversions(data):
    with open(CONVERSION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ==================== НАЗВАНИЯ ТЕХНИКИ ====================

def get_tech_display_name(tech_key: str) -> str:
    """Возвращает человекочитаемое название техники"""
    if CORP_STORE_AVAILABLE and tech_key in EQUIPMENT_NAMES:
        return EQUIPMENT_NAMES[tech_key]
    
    names = {
        "tanks": f"{EMOJIS['tank']} Танки", "btr": "БТР", "bmp": "БМП", 
        "armored_vehicles": f"{EMOJIS['car']} Бронеавтомобили",
        "self_propelled_artillery": "САУ", "towed_artillery": "Буксируемая артиллерия", 
        "mlrs": "РСЗО", "atgm_complexes": "ПТРК", 
        "short_range_air_defense": "ЗРК малой дальности",
        "long_range_air_defense": "ЗРК большой дальности", "zdprk": "ЗПРК", "zas": "ЗСУ",
        "small_arms": f"{EMOJIS['weapon']} Стрелковое оружие", "grenade_launchers": "Гранатомёты",
        "atgms": "Переносные ПТРК", "manpads": "ПЗРК", 
        "fpv_drones": f"{EMOJIS['drone']} FPV-дроны",
        "fighters": f"{EMOJIS['aircraft']} Истребители", 
        "attack_aircraft": f"{EMOJIS['aircraft']} Штурмовики", 
        "bombers": f"{EMOJIS['aircraft']} Бомбардировщики",
        "transport_aircraft": f"{EMOJIS['aircraft']} Транспортные самолёты", 
        "attack_helicopters": f"{EMOJIS['aircraft']} Ударные вертолёты",
        "transport_helicopters": f"{EMOJIS['aircraft']} Транспортные вертолёты", 
        "recon_uav": f"{EMOJIS['drone']} Разведывательные БПЛА",
        "attack_uav": f"{EMOJIS['drone']} Ударные БПЛА", 
        "kamikaze_drones": f"{EMOJIS['drone']} Дроны-камикадзе",
        "boats": f"{EMOJIS['ship']} Катера", "corvettes": f"{EMOJIS['ship']} Корветы", 
        "destroyers": f"{EMOJIS['ship']} Эсминцы",
        "cruisers": f"{EMOJIS['ship']} Крейсера", 
        "aircraft_carriers": f"{EMOJIS['ship']} Авианосцы", 
        "submarines": f"{EMOJIS['ship']} Подводные лодки",
        "usv_attack": f"{EMOJIS['drone']} Надводные дроны",
        "cruise_missiles": f"{EMOJIS['missile']} Крылатые ракеты", 
        "ballistic_missiles": f"{EMOJIS['missile']} Баллистические ракеты",
        "hypersonic_missiles": f"{EMOJIS['missile']} Гиперзвуковые ракеты"
    }
    return names.get(tech_key, tech_key)


# ==================== ДАННЫЕ ПО ТЕХНИКЕ НА КОНСЕРВАЦИИ ====================

MILITARY_RESERVES = {
    "США": {
        "ground": {
            "tanks": 2500, "btr": 5000, "bmp": 3000, "armored_vehicles": 8000,
            "self_propelled_artillery": 800, "towed_artillery": 1000, "mlrs": 400,
            "atgm_complexes": 1500, "short_range_air_defense": 600, "long_range_air_defense": 200
        },
        "equipment": {
            "small_arms": 500000, "grenade_launchers": 30000, "atgms": 8000, "manpads": 6000, "fpv_drones": 50000
        },
        "air": {
            "fighters": 400, "attack_aircraft": 150, "bombers": 80, "transport_aircraft": 120,
            "attack_helicopters": 200, "transport_helicopters": 150, "recon_uav": 100, "attack_uav": 50
        },
        "navy": {
            "boats": 100, "corvettes": 10, "destroyers": 15, "cruisers": 5, "submarines": 10,
            "usv_attack": 50
        },
        "missiles": {
            "cruise_missiles": 800, "ballistic_missiles": 300
        }
    },
    "Россия": {
        "ground": {
            "tanks": 5000, "btr": 8000, "bmp": 6000, "armored_vehicles": 7000,
            "self_propelled_artillery": 1000, "towed_artillery": 2000, "mlrs": 600,
            "atgm_complexes": 2000, "short_range_air_defense": 800, "long_range_air_defense": 300,
            "zdprk": 400, "zas": 500
        },
        "equipment": {
            "small_arms": 800000, "grenade_launchers": 50000, "atgms": 12000, "manpads": 8000, "fpv_drones": 100000
        },
        "air": {
            "fighters": 600, "attack_aircraft": 250, "bombers": 100, "transport_aircraft": 150,
            "attack_helicopters": 300, "transport_helicopters": 200, "recon_uav": 150, "attack_uav": 80
        },
        "navy": {
            "boats": 150, "corvettes": 20, "destroyers": 15, "cruisers": 8, "submarines": 25,
            "usv_attack": 80
        },
        "missiles": {
            "cruise_missiles": 1000, "ballistic_missiles": 400, "hypersonic_missiles": 30
        }
    },
    "Китай": {
        "ground": {
            "tanks": 3000, "btr": 6000, "bmp": 4000, "armored_vehicles": 5000,
            "self_propelled_artillery": 800, "towed_artillery": 1200, "mlrs": 500,
            "atgm_complexes": 1500, "short_range_air_defense": 600, "long_range_air_defense": 200
        },
        "equipment": {
            "small_arms": 600000, "grenade_launchers": 40000, "atgms": 10000, "manpads": 7000, "fpv_drones": 80000
        },
        "air": {
            "fighters": 500, "attack_aircraft": 200, "bombers": 80, "transport_aircraft": 100,
            "attack_helicopters": 200, "transport_helicopters": 150
        },
        "navy": {
            "boats": 120, "corvettes": 15, "destroyers": 12, "cruisers": 5, "submarines": 20,
            "usv_attack": 60
        },
        "missiles": {
            "cruise_missiles": 800, "ballistic_missiles": 300
        }
    },
    "Украина": {
        "ground": {
            "tanks": 800, "btr": 2000, "bmp": 1500, "armored_vehicles": 1500,
            "self_propelled_artillery": 300, "towed_artillery": 500, "mlrs": 200, "atgm_complexes": 800
        },
        "equipment": {
            "small_arms": 200000, "grenade_launchers": 15000, "atgms": 4000, "manpads": 3000, "fpv_drones": 50000
        },
        "air": {
            "fighters": 80, "attack_aircraft": 30, "transport_aircraft": 20, "attack_helicopters": 40
        },
        "navy": {
            "boats": 30, "corvettes": 1, "destroyers": 0, "cruisers": 0, "submarines": 0,
            "usv_attack": 100
        }
    }
}

# Добавляем usv_attack для остальных стран
for country in ["Германия", "Великобритания", "Франция", "Япония", "Израиль", 
                "Турция", "Иран", "Норвегия", "Швеция", "Финляндия", "Польша", 
                "Канада", "Бразилия", "Египет", "КНДР", "Сирия"]:
    if country not in MILITARY_RESERVES:
        MILITARY_RESERVES[country] = {}
    if "navy" not in MILITARY_RESERVES[country]:
        MILITARY_RESERVES[country]["navy"] = {}
    if "usv_attack" not in MILITARY_RESERVES[country]["navy"]:
        MILITARY_RESERVES[country]["navy"]["usv_attack"] = 20


# ==================== МОБИЛИЗАЦИЯ НАСЕЛЕНИЯ ====================

def get_mobilization_plan(country_name: str) -> Dict:
    """Получить план мобилизации для страны"""
    plans = load_mobilization_plan()
    return plans["plans"].get(country_name, {
        "status": "none",
        "target": 0,
        "mobilized": 0,
        "started_at": None,
        "completed_at": None,
        "plan_started_at": None
    })

def save_mobilization_plan_for_country(country_name: str, plan: Dict):
    """Сохранить план мобилизации для страны"""
    plans = load_mobilization_plan()
    plans["plans"][country_name] = plan
    save_mobilization_plan(plans)

def calculate_max_mobilization(player_data) -> int:
    """Рассчитать максимальное количество, которое можно мобилизовать (до 7% населения)"""
    population = player_data["state"]["population"]
    army_size = player_data["state"]["army_size"]
    
    max_manpower = int(population * 0.07)
    available = max(0, max_manpower - army_size)
    small_arms = player_data.get("army", {}).get("equipment", {}).get("small_arms", 0)
    
    return min(available, small_arms)

def get_mobilization_stats(player_data) -> Dict:
    """Получить статистику мобилизации"""
    population = player_data["state"]["population"]
    army_size = player_data["state"]["army_size"]
    small_arms = player_data.get("army", {}).get("equipment", {}).get("small_arms", 0)
    
    max_manpower = int(population * 0.07)
    available = max(0, max_manpower - army_size)
    max_possible = min(available, small_arms)
    mobilization_percent = (army_size / population) * 100
    
    return {
        "population": population,
        "current_army": army_size,
        "max_manpower": max_manpower,
        "available_manpower": available,
        "small_arms": small_arms,
        "max_possible": max_possible,
        "mobilization_percent": mobilization_percent
    }

def start_mobilization_plan(player_data, target_quantity: int) -> Tuple[bool, str]:
    """Начать план частичной мобилизации"""
    country_name = player_data["state"]["statename"]
    current_plan = get_mobilization_plan(country_name)
    
    if current_plan["status"] == "active":
        return False, "Мобилизация уже проводится! Сначала отмените или дождитесь завершения."
    
    if current_plan["status"] == "planning":
        return False, "План мобилизации уже настроен. Нажмите 'Частичная мобилизация' для начала."
    
    stats = get_mobilization_stats(player_data)
    
    if target_quantity <= 0:
        return False, "Количество должно быть положительным!"
    
    if target_quantity > stats["max_possible"]:
        return False, f"Нельзя мобилизовать больше {stats['max_possible']} человек! (Недостаточно мобресурса или оружия)"
    
    plan = {
        "status": "planning",
        "target": target_quantity,
        "mobilized": 0,
        "started_at": None,
        "completed_at": None,
        "plan_started_at": str(datetime.now())
    }
    save_mobilization_plan_for_country(country_name, plan)
    
    return True, f"План частичной мобилизации настроен на {format_number(target_quantity)} человек. Нажмите 'Частичная мобилизация' для начала."

def execute_partial_mobilization(player_data, bot) -> Tuple[bool, str, Dict]:
    """Начать выполнение плана частичной мобилизации"""
    country_name = player_data["state"]["statename"]
    plan = get_mobilization_plan(country_name)
    
    if plan["status"] != "planning":
        return False, "Нет настроенного плана мобилизации! Сначала настройте план.", {}
    
    stats = get_mobilization_stats(player_data)
    
    if plan["target"] > stats["max_possible"]:
        return False, f"План превышает возможное количество! Максимум: {stats['max_possible']}", {}
    
    if stats["small_arms"] < plan["target"]:
        return False, f"Недостаточно оружия! Нужно: {plan['target']}, есть: {stats['small_arms']}", {}
    
    plan["status"] = "active"
    plan["started_at"] = str(datetime.now())
    save_mobilization_plan_for_country(country_name, plan)
    
    queue = load_mobilization()
    
    hours = max(1, plan["target"] // 1000)
    completion_time = datetime.now() + timedelta(hours=hours)
    
    program = {
        "id": len(queue.get("active_programs", [])) + 1,
        "user_id": player_data.get("assigned_to"),
        "country": country_name,
        "type": "mobilization",
        "target": plan["target"],
        "start_time": str(datetime.now()),
        "completion_time": str(completion_time),
        "status": "in_progress",
        "notified": False
    }
    
    if "active_programs" not in queue:
        queue["active_programs"] = []
    if "completed_programs" not in queue:
        queue["completed_programs"] = []
    
    queue["active_programs"].append(program)
    save_mobilization(queue)
    
    # Отправляем лог о начале мобилизации
    asyncio.create_task(send_mobilization_log(bot, "mobilization_start", {
        "country": country_name,
        "target": plan["target"],
        "hours": hours,
        "type": "partial",
        "color": DARK_THEME_COLOR
    }))
    
    result = {"target": plan["target"], "hours": hours}
    
    return True, f"Частичная мобилизация {format_number(plan['target'])} человек запущена! Время: {hours} часов", result

def execute_total_mobilization(player_data, bot) -> Tuple[bool, str, Dict]:
    """Начать всеобщую мобилизацию (максимально возможное количество)"""
    country_name = player_data["state"]["statename"]
    current_plan = get_mobilization_plan(country_name)
    
    if current_plan["status"] == "active":
        return False, "Мобилизация уже проводится! Сначала отмените или дождитесь завершения.", {}
    
    if current_plan["status"] == "planning":
        return False, "У вас настроен план частичной мобилизации. Сначала отмените его или выполните.", {}
    
    stats = get_mobilization_stats(player_data)
    target = stats["max_possible"]
    
    if target <= 0:
        return False, "Невозможно провести мобилизацию! Нет доступных резервистов или оружия.", {}
    
    if stats["small_arms"] < target:
        return False, f"Недостаточно оружия! Нужно: {target}, есть: {stats['small_arms']}", {}
    
    plan = {
        "status": "active",
        "target": target,
        "mobilized": 0,
        "started_at": str(datetime.now()),
        "completed_at": None,
        "plan_started_at": str(datetime.now())
    }
    save_mobilization_plan_for_country(country_name, plan)
    
    queue = load_mobilization()
    
    hours = max(1, target // 1000)
    completion_time = datetime.now() + timedelta(hours=hours)
    
    program = {
        "id": len(queue.get("active_programs", [])) + 1,
        "user_id": player_data.get("assigned_to"),
        "country": country_name,
        "type": "mobilization",
        "target": target,
        "start_time": str(datetime.now()),
        "completion_time": str(completion_time),
        "status": "in_progress",
        "notified": False
    }
    
    if "active_programs" not in queue:
        queue["active_programs"] = []
    if "completed_programs" not in queue:
        queue["completed_programs"] = []
    
    queue["active_programs"].append(program)
    save_mobilization(queue)
    
    # Отправляем лог о начале мобилизации
    asyncio.create_task(send_mobilization_log(bot, "mobilization_start", {
        "country": country_name,
        "target": target,
        "hours": hours,
        "type": "total",
        "color": DARK_THEME_COLOR
    }))
    
    result = {"target": target, "hours": hours}
    
    return True, f"Всеобщая мобилизация {format_number(target)} человек запущена! Время: {hours} часов", result

def cancel_mobilization(player_data) -> Tuple[bool, str]:
    """Отменить мобилизацию (не возвращает мобилизованных)"""
    country_name = player_data["state"]["statename"]
    plan = get_mobilization_plan(country_name)
    
    if plan["status"] not in ["planning", "active"]:
        return False, "Нет активного плана мобилизации!"
    
    if plan["status"] == "active":
        queue = load_mobilization()
        for program in queue.get("active_programs", []):
            if program.get("country") == country_name and program.get("type") == "mobilization":
                program["status"] = "cancelled"
                program["cancelled_at"] = str(datetime.now())
                queue["completed_programs"].append(program)
                queue["active_programs"].remove(program)
                save_mobilization(queue)
                break
    
    plan["status"] = "cancelled"
    plan["cancelled_at"] = str(datetime.now())
    save_mobilization_plan_for_country(country_name, plan)
    
    return True, "Мобилизация отменена. Мобилизованные граждане остаются в армии."

def start_demobilization(player_data, quantity: int, bot) -> Tuple[bool, str]:
    """Начать демобилизацию (возврат в резерв)"""
    country_name = player_data["state"]["statename"]
    current_army = player_data["state"]["army_size"]
    
    if quantity <= 0:
        return False, "Количество должно быть положительным!"
    
    if quantity > current_army:
        return False, f"Нельзя демобилизовать больше {current_army} человек!"
    
    plan = {
        "status": "demobilizing",
        "target": quantity,
        "demobilized": 0,
        "started_at": str(datetime.now()),
        "completed_at": None
    }
    save_mobilization_plan_for_country(country_name, plan)
    
    queue = load_mobilization()
    
    hours = max(1, quantity // 1000)
    completion_time = datetime.now() + timedelta(hours=hours)
    
    program = {
        "id": len(queue.get("active_programs", [])) + 1,
        "user_id": player_data.get("assigned_to"),
        "country": country_name,
        "type": "demobilization",
        "target": quantity,
        "start_time": str(datetime.now()),
        "completion_time": str(completion_time),
        "status": "in_progress",
        "notified": False
    }
    
    if "active_programs" not in queue:
        queue["active_programs"] = []
    queue["active_programs"].append(program)
    save_mobilization(queue)
    
    # Отправляем лог о начале демобилизации
    asyncio.create_task(send_mobilization_log(bot, "demobilization_start", {
        "country": country_name,
        "target": quantity,
        "hours": hours,
        "color": DARK_THEME_COLOR
    }))
    
    return True, f"Демобилизация {format_number(quantity)} человек запущена! Время: {hours} часов"

def complete_mobilization_program(program: Dict, player_data, bot) -> bool:
    """Завершить программу мобилизации/демобилизации"""
    country_name = program["country"]
    plan = get_mobilization_plan(country_name)
    
    if program["type"] == "mobilization":
        player_data["state"]["army_size"] += program["target"]
        player_data["army"]["equipment"]["small_arms"] -= program["target"]
        
        plan["status"] = "completed"
        plan["mobilized"] = program["target"]
        plan["completed_at"] = str(datetime.now())
        save_mobilization_plan_for_country(country_name, plan)
        
        # Отправляем лог о завершении мобилизации
        asyncio.create_task(send_mobilization_log(bot, "mobilization_complete", {
            "country": country_name,
            "mobilized": program["target"],
            "color": DARK_THEME_COLOR
        }))
        
    elif program["type"] == "demobilization":
        player_data["state"]["army_size"] -= program["target"]
        
        plan["status"] = "completed"
        plan["demobilized"] = program["target"]
        plan["completed_at"] = str(datetime.now())
        save_mobilization_plan_for_country(country_name, plan)
        
        # Отправляем лог о завершении демобилизации
        asyncio.create_task(send_mobilization_log(bot, "demobilization_complete", {
            "country": country_name,
            "demobilized": program["target"],
            "color": DARK_THEME_COLOR
        }))
    
    return True


# ==================== ФУНКЦИИ ДЛЯ РАСКОНСЕРВАЦИИ ====================

def get_production_time_from_corp(tech_type: str) -> float:
    """Получает время производства из corp_store"""
    if CORP_STORE_AVAILABLE:
        return PRODUCTION_SPEED.get(tech_type, 3600)
    default_times = {
        "tanks": 86400, "btr": 43200, "bmp": 54000, "armored_vehicles": 2700,
        "self_propelled_artillery": 10800, "towed_artillery": 7200, "mlrs": 10800,
        "atgm_complexes": 3600, "short_range_air_defense": 18000, "long_range_air_defense": 43200,
        "small_arms": 30, "grenade_launchers": 240, "atgms": 600, "manpads": 1200, "fpv_drones": 120,
        "fighters": 86400, "attack_aircraft": 72000, "bombers": 129600,
        "transport_aircraft": 108000, "attack_helicopters": 57600, "transport_helicopters": 43200,
        "boats": 28800, "corvettes": 172800, "destroyers": 259200, "cruisers": 345600, "submarines": 345600,
        "usv_attack": 3600,
        "cruise_missiles": 21600, "ballistic_missiles": 43200, "hypersonic_missiles": 86400
    }
    return default_times.get(tech_type, 3600)

def get_production_price(tech_type: str) -> int:
    """Получает примерную цену производства техники"""
    prices = {
        "tanks": 4000000, "btr": 1500000, "bmp": 2000000, "armored_vehicles": 500000,
        "self_propelled_artillery": 3000000, "towed_artillery": 800000, "mlrs": 4000000,
        "atgm_complexes": 300000, "short_range_air_defense": 2000000, "long_range_air_defense": 5000000,
        "small_arms": 1000, "grenade_launchers": 5000, "atgms": 50000, "manpads": 80000, "fpv_drones": 5000,
        "fighters": 50000000, "attack_aircraft": 40000000, "bombers": 80000000,
        "transport_aircraft": 30000000, "attack_helicopters": 20000000, "transport_helicopters": 15000000,
        "boats": 2000000, "corvettes": 15000000, "destroyers": 50000000, "cruisers": 100000000, "submarines": 80000000,
        "usv_attack": 50000,
        "cruise_missiles": 500000, "ballistic_missiles": 2000000, "hypersonic_missiles": 10000000
    }
    return prices.get(tech_type, 100000)

def get_reserves_cost(tech_type: str) -> Dict:
    """Возвращает стоимость и время расконсервации (в реальных часах)"""
    prod_time = get_production_time_from_corp(tech_type)
    prod_price = get_production_price(tech_type)
    
    time_multiplier = random.uniform(0.3, 0.5)
    real_time = prod_time * time_multiplier
    
    price_multiplier = random.uniform(0.2, 0.4)
    money_cost = prod_price * price_multiplier
    
    return {
        "money": int(money_cost),
        "seconds": int(real_time)
    }

def get_available_reserves(country_name: str) -> Dict:
    """Возвращает доступные резервы техники для страны"""
    reserves_data = load_reserves()
    
    if country_name not in reserves_data["remaining_reserves"]:
        initial_reserves = MILITARY_RESERVES.get(country_name, {}).copy()
        reserves_data["remaining_reserves"][country_name] = initial_reserves
        save_reserves(reserves_data)
    
    return reserves_data["remaining_reserves"].get(country_name, {})

def mark_reserves_activated(country_name: str, category: str, subcategory: str, quantity: int):
    """Отмечает технику как активированную и списывает из резервов"""
    reserves_data = load_reserves()
    
    if country_name in reserves_data["remaining_reserves"]:
        if category in reserves_data["remaining_reserves"][country_name]:
            if subcategory in reserves_data["remaining_reserves"][country_name][category]:
                reserves_data["remaining_reserves"][country_name][category][subcategory] -= quantity
    
    if country_name not in reserves_data["activated"]:
        reserves_data["activated"][country_name] = {}
    if category not in reserves_data["activated"][country_name]:
        reserves_data["activated"][country_name][category] = {}
    
    reserves_data["activated"][country_name][category][subcategory] = \
        reserves_data["activated"][country_name][category].get(subcategory, 0) + quantity
    
    save_reserves(reserves_data)

def check_reserves_availability(country_name: str, category: str, subcategory: str, quantity: int) -> Tuple[bool, int]:
    """Проверяет наличие техники в резервах"""
    reserves = get_available_reserves(country_name)
    available = reserves.get(category, {}).get(subcategory, 0)
    return available >= quantity, available

def add_reserves_to_army(player_data, category: str, subcategory: str, quantity: int):
    """Добавляет расконсервированную технику в армию"""
    if "army" not in player_data:
        player_data["army"] = {}
    if category not in player_data["army"]:
        player_data["army"][category] = {}
    
    player_data["army"][category][subcategory] = \
        player_data["army"][category].get(subcategory, 0) + quantity


# ==================== РЕЦЕПТЫ САМОДЕЛЬНОЙ ТЕХНИКИ ====================

MOBILIZATION_RECIPES = {
    "armored_vehicle_improvised": {
        "name": "Кустарная бронемашина",
        "description": "Импровизированный бронеавтомобиль на базе гражданского авто",
        "civilian_inputs": {"cars": 1, "steel": 0.1},
        "military_inputs": {"equipment.small_arms": 1},
        "military_output": {"category": "ground", "type": "armored_vehicles", "quantity": 15, "quality_modifier": 0.6},
        "required_civ_factories": 1,
        "duration_minutes": 30,
        "money_cost": 50000
    },
    "btr_improvised": {
        "name": "Кустарный БТР",
        "description": "Бронетранспортер из грузовика с броней и вооружением",
        "civilian_inputs": {"trucks": 1, "steel": 0.4},
        "military_inputs": {"equipment.small_arms": 2},
        "military_output": {"category": "ground", "type": "btr", "quantity": 8, "quality_modifier": 0.55},
        "required_civ_factories": 1,
        "duration_minutes": 45,
        "money_cost": 100000
    },
    "howitzer_improvised": {
        "name": "Кустарная гаубица",
        "description": "Импровизированное артиллерийское орудие",
        "civilian_inputs": {"steel": 0.07, "electronics": 0.1},
        "military_output": {"category": "ground", "type": "towed_artillery", "quantity": 10, "quality_modifier": 0.4},
        "required_civ_factories": 1,
        "duration_minutes": 60,
        "money_cost": 150000
    },
    "short_range_air_defense_improvised": {
        "name": "Кустарное ПВО малой дальности",
        "description": "Импровизированная зенитная установка на базе автомобиля",
        "civilian_inputs": {"cars": 1, "electronics": 0.05},
        "military_inputs": {"equipment.manpads": 1},
        "military_output": {"category": "ground", "type": "short_range_air_defense", "quantity": 6, "quality_modifier": 0.5},
        "required_civ_factories": 1,
        "duration_minutes": 50,
        "money_cost": 80000
    },
    "fpv_drone_improvised": {
        "name": "Кустарный FPV-дрон",
        "description": "FPV-дрон из гражданских компонентов",
        "civilian_inputs": {"aluminum": 0.01, "electronics": 0.15},
        "military_output": {"category": "equipment", "type": "fpv_drones", "quantity": 100, "quality_modifier": 0.7},
        "required_civ_factories": 1,
        "duration_minutes": 15,
        "money_cost": 5000
    },
    "kamikaze_drone_improvised": {
        "name": "Кустарный дрон-камикадзе",
        "description": "Барражирующий боеприпас кустарного производства",
        "civilian_inputs": {"aluminum": 0.12, "electronics": 0.2},
        "military_output": {"category": "air", "type": "kamikaze_drones", "quantity": 20, "quality_modifier": 0.6},
        "required_civ_factories": 1,
        "duration_minutes": 25,
        "money_cost": 8000
    },
    "usv_attack_improvised": {
        "name": "Кустарный надводный дрон",
        "description": "Импровизированный надводный беспилотный катер",
        "civilian_inputs": {"aluminum": 0.2, "electronics": 0.1, "steel": 0.15},
        "military_output": {"category": "navy", "type": "usv_attack", "quantity": 5, "quality_modifier": 0.65},
        "required_civ_factories": 1,
        "duration_minutes": 40,
        "money_cost": 15000
    }
}


# ==================== ФУНКЦИИ ДЛЯ ПРОМЫШЛЕННОЙ МОБИЛИЗАЦИИ ====================

def get_resource_amount(player_data, resource: str) -> float:
    """Получает количество ресурса из данных игрока"""
    if resource in ["steel", "aluminum", "electronics", "oil", "gas", "coal", "uranium", "rare_metals", "food"]:
        return player_data.get("resources", {}).get(resource, 0)
    if resource in ["cars", "trucks", "drones", "agricultural_machinery", "construction_machinery"]:
        return player_data.get("civil_goods", {}).get(resource, 0)
    return 0

def deduct_resource(player_data, resource: str, amount: float) -> bool:
    """Списывает ресурс из данных игрока"""
    if resource in ["steel", "aluminum", "electronics", "oil", "gas", "coal", "uranium", "rare_metals", "food"]:
        if player_data.get("resources", {}).get(resource, 0) < amount:
            return False
        if "resources" not in player_data:
            player_data["resources"] = {}
        player_data["resources"][resource] = player_data["resources"].get(resource, 0) - amount
        return True
    if resource in ["cars", "trucks", "drones", "agricultural_machinery", "construction_machinery"]:
        if player_data.get("civil_goods", {}).get(resource, 0) < amount:
            return False
        if "civil_goods" not in player_data:
            player_data["civil_goods"] = {}
        player_data["civil_goods"][resource] = player_data["civil_goods"].get(resource, 0) - amount
        return True
    return False

def check_mobilization_requirements(player_data, recipe_id: str, region: str) -> Tuple[bool, str]:
    """Проверяет возможность запуска производства по рецепту"""
    recipe = MOBILIZATION_RECIPES.get(recipe_id)
    if not recipe:
        return False, "Рецепт не найден"
    
    if player_data["economy"]["budget"] < recipe["money_cost"]:
        return False, f"Недостаточно средств! Нужно: {format_billion(recipe['money_cost'])}"
    
    infra = load_infrastructure()
    country_name = player_data["state"]["statename"]
    
    found = False
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == country_name:
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                if region in econ_data.get("regions", {}):
                    region_data = econ_data["regions"][region]
                    civ_factories = region_data.get("civilian_factories", 0)
                    if civ_factories < recipe["required_civ_factories"]:
                        return False, f"В регионе недостаточно гражданских фабрик! Нужно: {recipe['required_civ_factories']}, есть: {civ_factories}"
                    found = True
                    break
            break
    
    if not found:
        return False, f"Регион {region} не найден"
    
    for resource, amount in recipe.get("civilian_inputs", {}).items():
        available = get_resource_amount(player_data, resource)
        if available < amount:
            resource_names = {"cars": "Автомобили", "trucks": "Грузовики", "steel": "Сталь", "aluminum": "Алюминий", "electronics": "Электроника"}
            return False, f"Недостаточно {resource_names.get(resource, resource)}! Нужно: {amount}, есть: {available}"
    
    army = player_data.get("army", {})
    for mil_resource, amount in recipe.get("military_inputs", {}).items():
        if mil_resource == "equipment.small_arms":
            if army.get("equipment", {}).get("small_arms", 0) < amount:
                return False, f"Недостаточно стрелкового оружия! Нужно: {amount}"
        elif mil_resource == "equipment.manpads":
            if army.get("equipment", {}).get("manpads", 0) < amount:
                return False, f"Недостаточно ПЗРК! Нужно: {amount}"
    
    return True, "OK"

def consume_mobilization_resources(player_data, recipe: Dict) -> bool:
    """Списывает ресурсы для производства"""
    player_data["economy"]["budget"] -= recipe["money_cost"]
    
    for resource, amount in recipe.get("civilian_inputs", {}).items():
        if not deduct_resource(player_data, resource, amount):
            return False
    
    army = player_data.get("army", {})
    for mil_resource, amount in recipe.get("military_inputs", {}).items():
        if mil_resource == "equipment.small_arms":
            if "equipment" not in army:
                army["equipment"] = {}
            army["equipment"]["small_arms"] = army["equipment"].get("small_arms", 0) - amount
        elif mil_resource == "equipment.manpads":
            if "equipment" not in army:
                army["equipment"] = {}
            army["equipment"]["manpads"] = army["equipment"].get("manpads", 0) - amount
    
    player_data["army"] = army
    return True

def start_mobilization_production(player_data, recipe_id: str, region: str, quantity: int, bot) -> Tuple[bool, str, Dict]:
    """Запускает производство самодельной техники"""
    recipe = MOBILIZATION_RECIPES.get(recipe_id)
    if not recipe:
        return False, "Рецепт не найден", {}
    
    can, msg = check_mobilization_requirements(player_data, recipe_id, region)
    if not can:
        return False, msg, {}
    
    total_minutes = recipe["duration_minutes"] * quantity
    total_cost = recipe["money_cost"] * quantity
    
    if player_data["economy"]["budget"] < total_cost:
        return False, f"Недостаточно средств! Нужно: {format_billion(total_cost)}", {}
    
    infra = load_infrastructure()
    country_name = player_data["state"]["statename"]
    
    available_factories = 0
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == country_name:
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                if region in econ_data.get("regions", {}):
                    region_data = econ_data["regions"][region]
                    available_factories = region_data.get("civilian_factories", 0)
                    break
            break
    
    if available_factories < recipe["required_civ_factories"] * quantity:
        return False, f"В регионе недостаточно гражданских фабрик! Нужно: {recipe['required_civ_factories'] * quantity}, есть: {available_factories}", {}
    
    temp_recipe = recipe.copy()
    temp_recipe["money_cost"] = total_cost
    for resource in temp_recipe.get("civilian_inputs", {}):
        temp_recipe["civilian_inputs"][resource] *= quantity
    for resource in temp_recipe.get("military_inputs", {}):
        temp_recipe["military_inputs"][resource] *= quantity
    
    if not consume_mobilization_resources(player_data, temp_recipe):
        return False, "Не удалось списать ресурсы", {}
    
    queue = load_mobilization()
    
    output = recipe["military_output"]
    output["quantity"] = output["quantity"] * quantity
    
    completion_time = datetime.now() + timedelta(minutes=total_minutes)
    
    program = {
        "id": len(queue.get("active_programs", [])) + len(queue.get("completed_programs", [])) + 1,
        "user_id": player_data.get("assigned_to"),
        "country": country_name,
        "type": "industrial_mobilization",
        "recipe_id": recipe_id,
        "recipe_name": recipe["name"],
        "region": region,
        "quantity": quantity,
        "output": output,
        "start_time": str(datetime.now()),
        "completion_time": str(completion_time),
        "status": "in_progress",
        "notified": False
    }
    
    if "active_programs" not in queue:
        queue["active_programs"] = []
    queue["active_programs"].append(program)
    save_mobilization(queue)
    
    # Отправляем лог о начале производства
    asyncio.create_task(send_mobilization_log(bot, "industrial_production", {
        "country": country_name,
        "recipe_name": recipe["name"],
        "region": region,
        "quantity": quantity,
        "output_quantity": output["quantity"],
        "minutes": total_minutes,
        "color": DARK_THEME_COLOR
    }))
    
    result = {
        "recipe_name": recipe["name"],
        "quantity": quantity,
        "output": output,
        "minutes": total_minutes
    }
    
    return True, f"Производство {recipe['name']} x{quantity} запущено! Время: {total_minutes} минут", result

def get_available_regions(player_data) -> List[str]:
    """Возвращает список регионов страны с гражданскими фабриками"""
    infra = load_infrastructure()
    country_name = player_data["state"]["statename"]
    regions = []
    
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == country_name:
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                for region_name, region_data in econ_data.get("regions", {}).items():
                    if region_data.get("civilian_factories", 0) > 0:
                        regions.append(region_name)
            break
    
    return regions


# ==================== КОНВЕРСИЯ ФАБРИК ====================

def get_conversion_cost(factories_count: int) -> Dict:
    """Возвращает стоимость и время конвертации фабрик"""
    return {
        "money": factories_count * 1000000,
        "hours": factories_count * 4
    }

def convert_factories(player_data, country_name: str, region: str, factories_to_convert: int, bot) -> Tuple[bool, str, Dict]:
    """Конвертирует гражданские фабрики в военные"""
    infra = load_infrastructure()
    
    country_id = None
    region_data = None
    econ_region_name = None
    
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                if region in econ_data.get("regions", {}):
                    region_data = econ_data["regions"][region]
                    econ_region_name = econ_region
                    break
            break
    
    if not region_data:
        return False, "Регион не найден", {}
    
    current_civ = region_data.get("civilian_factories", 0)
    
    if current_civ < factories_to_convert:
        return False, f"В регионе недостаточно гражданских фабрик! Есть: {current_civ}, нужно: {factories_to_convert}", {}
    
    cost = get_conversion_cost(factories_to_convert)
    if player_data["economy"]["budget"] < cost["money"]:
        return False, f"Недостаточно средств! Нужно: {format_billion(cost['money'])}", {}
    
    player_data["economy"]["budget"] -= cost["money"]
    
    region_data["civilian_factories"] -= factories_to_convert
    region_data["military_factories"] = region_data.get("military_factories", 0) + factories_to_convert
    
    infra["infrastructure"][country_id]["economic_regions"][econ_region_name]["regions"][region] = region_data
    save_infrastructure(infra)
    
    conversions = load_factory_conversions()
    if country_name not in conversions["conversions"]:
        conversions["conversions"][country_name] = []
    
    conversion_record = {
        "region": region,
        "factories": factories_to_convert,
        "date": str(datetime.now()),
        "cost": cost["money"]
    }
    conversions["conversions"][country_name].append(conversion_record)
    save_factory_conversions(conversions)
    
    # Отправляем лог о начале конвертации
    asyncio.create_task(send_mobilization_log(bot, "factory_conversion", {
        "country": country_name,
        "region": region,
        "factories": factories_to_convert,
        "cost": cost["money"],
        "hours": cost["hours"],
        "color": DARK_THEME_COLOR
    }))
    
    result = {
        "factories": factories_to_convert,
        "cost": cost["money"],
        "hours": cost["hours"]
    }
    
    return True, f"Конвертировано {factories_to_convert} гражданских фабрик в военные в регионе {region}", result


# ==================== ФОНОВЫЕ ЗАДАЧИ ====================

async def mobilization_completion_loop(bot_instance):
    """Фоновая задача для проверки завершения мобилизации"""
    await bot_instance.wait_until_ready()
    
    while not bot_instance.is_closed():
        try:
            queue = load_mobilization()
            states = load_states()
            now = datetime.now()
            
            completed = []
            
            for program in queue.get("active_programs", [])[:]:
                completion = datetime.fromisoformat(program["completion_time"])
                
                if completion <= now and not program.get("notified", False):
                    player_data = None
                    for data in states["players"].values():
                        if data.get("assigned_to") == program["user_id"]:
                            player_data = data
                            break
                    
                    if player_data:
                        if program["type"] == "mobilization":
                            success = complete_mobilization_program(program, player_data, bot_instance)
                            if success:
                                program["status"] = "completed"
                                program["completed_at"] = str(now)
                                queue["completed_programs"].append(program)
                                queue["active_programs"].remove(program)
                                completed.append(program)
                                
                                try:
                                    user = await bot_instance.fetch_user(int(program["user_id"]))
                                    if user:
                                        embed = discord.Embed(
                                            title=f"{EMOJIS['soldier']} Мобилизация завершена!",
                                            description=f"Мобилизовано {format_number(program['target'])} человек",
                                            color=DARK_THEME_COLOR
                                        )
                                        await user.send(embed=embed)
                                except:
                                    pass
                                
                        elif program["type"] == "demobilization":
                            success = complete_mobilization_program(program, player_data, bot_instance)
                            if success:
                                program["status"] = "completed"
                                program["completed_at"] = str(now)
                                queue["completed_programs"].append(program)
                                queue["active_programs"].remove(program)
                                completed.append(program)
                                
                                try:
                                    user = await bot_instance.fetch_user(int(program["user_id"]))
                                    if user:
                                        embed = discord.Embed(
                                            title=f"{EMOJIS['manpower']} Демобилизация завершена!",
                                            description=f"Демобилизовано {format_number(program['target'])} человек",
                                            color=DARK_THEME_COLOR
                                        )
                                        await user.send(embed=embed)
                                except:
                                    pass
                        else:
                            output = program["output"]
                            category = output["category"]
                            tech_type = output["type"]
                            
                            if "army" not in player_data:
                                player_data["army"] = {}
                            if category not in player_data["army"]:
                                player_data["army"][category] = {}
                            
                            player_data["army"][category][tech_type] = \
                                player_data["army"][category].get(tech_type, 0) + output["quantity"]
                            
                            program["status"] = "completed"
                            program["completed_at"] = str(now)
                            queue["completed_programs"].append(program)
                            queue["active_programs"].remove(program)
                            completed.append(program)
                            
                            try:
                                user = await bot_instance.fetch_user(int(program["user_id"]))
                                if user:
                                    embed = discord.Embed(
                                        title=f"{EMOJIS['civilian_factory']} Производство завершено",
                                        description=f"{program['recipe_name']} в регионе {program['region']}",
                                        color=DARK_THEME_COLOR
                                    )
                                    embed.add_field(
                                        name="Получено",
                                        value=f"{get_tech_display_name(tech_type)} x{output['quantity']}",
                                        inline=False
                                    )
                                    await user.send(embed=embed)
                            except:
                                pass
                    
                    program["notified"] = True
            
            if completed:
                save_mobilization(queue)
                save_states(states)
                print(f"Завершено {len(completed)} программ")
            
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"Ошибка в mobilization_completion_loop: {e}")
            await asyncio.sleep(60)


async def reserves_conversion_loop(bot_instance):
    """Фоновая задача для проверки расконсервации"""
    await bot_instance.wait_until_ready()
    
    while not bot_instance.is_closed():
        try:
            queue_data = load_conversion_queue()
            states = load_states()
            now = datetime.now()
            
            completed = []
            
            for conversion in queue_data.get("active_conversions", [])[:]:
                completion = datetime.fromisoformat(conversion["completion_time"])
                
                if completion <= now and not conversion.get("notified", False):
                    player_data = None
                    for data in states["players"].values():
                        if data.get("assigned_to") == conversion["user_id"]:
                            player_data = data
                            break
                    
                    if player_data:
                        add_reserves_to_army(
                            player_data,
                            conversion["category"],
                            conversion["subcategory"],
                            conversion["quantity"]
                        )
                        
                        conversion["status"] = "completed"
                        conversion["completed_at"] = str(now)
                        queue_data["completed_conversions"].append(conversion)
                        queue_data["active_conversions"].remove(conversion)
                        completed.append(conversion)
                        
                        try:
                            user = await bot_instance.fetch_user(int(conversion["user_id"]))
                            if user:
                                embed = discord.Embed(
                                    title=f"{EMOJIS['reserves']} Расконсервация завершена",
                                    description=f"{get_tech_display_name(conversion['subcategory'])} x{conversion['quantity']}",
                                    color=DARK_THEME_COLOR
                                )
                                await user.send(embed=embed)
                        except:
                            pass
                    
                    conversion["notified"] = True
            
            if completed:
                save_conversion_queue(queue_data)
                save_states(states)
                print(f"Завершено {len(completed)} операций расконсервации")
            
            await asyncio.sleep(60)
            
        except Exception as e:
            print(f"Ошибка в reserves_conversion_loop: {e}")
            await asyncio.sleep(60)


# ==================== UI КЛАССЫ ДЛЯ РАСКОНСЕРВАЦИИ ====================

class ReservesCategorySelect(Select):
    """Выбор категории техники для расконсервации"""
    def __init__(self, user_id, player_data, country_name, reserves, bot):
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.reserves = reserves
        self.bot = bot
        
        options = []
        categories = [
            ("ground", "Наземная техника"),
            ("equipment", "Снаряжение"),
            ("air", "Авиация"),
            ("navy", "Флот"),
            ("missiles", "Ракеты")
        ]
        
        for cat_key, cat_name in categories:
            if cat_key in reserves and reserves[cat_key]:
                options.append(discord.SelectOption(label=cat_name, value=cat_key))
        
        super().__init__(placeholder="Выберите категорию техники", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        category = self.values[0]
        
        available = {}
        for tech_type, count in self.reserves.get(category, {}).items():
            if count > 0:
                available[tech_type] = count
        
        if not available:
            await interaction.response.send_message("В этой категории нет доступной техники для расконсервации", ephemeral=True)
            return
        
        category_names = {
            "ground": "Наземная техника",
            "equipment": "Снаряжение",
            "air": "Авиация",
            "navy": "Флот",
            "missiles": "Ракеты"
        }
        
        embed = discord.Embed(
            title=f"{EMOJIS['reserves']} Расконсервация техники",
            description=f"Категория: **{category_names.get(category, category)}**\n\nВыберите тип техники",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=RESERVES_IMAGE)
        
        view = ReservesTechSelectView(self.user_id, self.player_data, self.country_name, category, available, self.bot)
        await interaction.response.edit_message(embed=embed, view=view)


class ReservesTechSelect(Select):
    """Выбор типа техники для расконсервации"""
    def __init__(self, user_id, player_data, country_name, category, available, bot):
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.category = category
        self.available = available
        self.bot = bot
        
        options = []
        for tech_type, count in list(available.items())[:25]:
            options.append(discord.SelectOption(
                label=f"{get_tech_display_name(tech_type)}",
                description=f"{format_number(count)} ед. доступно",
                value=tech_type
            ))
        
        super().__init__(placeholder="Выберите тип техники", options=options)
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        tech_type = self.values[0]
        max_count = self.available.get(tech_type, 0)
        
        modal = ReservesQuantityModal(self.user_id, self.player_data, self.country_name, self.category, tech_type, max_count, self.bot)
        await interaction.response.send_modal(modal)


class ReservesTechSelectView(View):
    """View с выбором типа техники"""
    def __init__(self, user_id, player_data, country_name, category, available, bot):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.category = category
        self.available = available
        self.bot = bot
        
        self.add_item(ReservesTechSelect(user_id, player_data, country_name, category, available, bot))
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        reserves = get_available_reserves(self.country_name)
        embed = discord.Embed(
            title=f"{EMOJIS['reserves']} Расконсервация техники",
            description="Выберите категорию техники",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=RESERVES_IMAGE)
        
        view = ReservesCategoryView(self.user_id, self.player_data, self.country_name, reserves, self.bot)
        await interaction.response.edit_message(embed=embed, view=view)


class ReservesCategoryView(View):
    """Меню расконсервации с выбором категории через Select"""
    def __init__(self, user_id, player_data, country_name, reserves, bot):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.reserves = reserves
        self.bot = bot
        
        self.add_item(ReservesCategorySelect(user_id, player_data, country_name, reserves, bot))
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        await show_mobilization_menu(interaction, self.user_id)


class ReservesQuantityModal(Modal, title="Количество для расконсервации"):
    def __init__(self, user_id, player_data, country_name, category, tech_type, max_count, bot):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.category = category
        self.tech_type = tech_type
        self.max_count = max_count
        self.bot = bot
        
        self.quantity = TextInput(
            label=f"Количество (макс: {format_number(max_count)})",
            placeholder="Введите число",
            min_length=1,
            max_length=6,
            required=True
        )
        self.add_item(self.quantity)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        try:
            qty = int(self.quantity.value)
        except ValueError:
            await interaction.response.send_message("Введите корректное число", ephemeral=True)
            return
        
        if qty <= 0:
            await interaction.response.send_message("Количество должно быть положительным", ephemeral=True)
            return
        
        if qty > self.max_count:
            await interaction.response.send_message(f"Максимум доступно {format_number(self.max_count)} единиц", ephemeral=True)
            return
        
        available, _ = check_reserves_availability(self.country_name, self.category, self.tech_type, qty)
        if not available:
            await interaction.response.send_message("Недостаточно техники в резервах", ephemeral=True)
            return
        
        cost_info = get_reserves_cost(self.tech_type)
        total_cost = cost_info["money"] * qty
        total_seconds = cost_info["seconds"] * qty
        
        if self.player_data["economy"]["budget"] < total_cost:
            await interaction.response.send_message(f"Недостаточно средств! Нужно: {format_billion(total_cost)}", ephemeral=True)
            return
        
        self.player_data["economy"]["budget"] -= total_cost
        
        queue_data = load_conversion_queue()
        
        completion_time = datetime.now() + timedelta(seconds=total_seconds)
        
        conversion = {
            "id": len(queue_data.get("active_conversions", [])) + len(queue_data.get("completed_conversions", [])) + 1,
            "user_id": self.user_id,
            "country": self.country_name,
            "category": self.category,
            "subcategory": self.tech_type,
            "quantity": qty,
            "cost": total_cost,
            "start_time": str(datetime.now()),
            "completion_time": str(completion_time),
            "status": "in_progress",
            "notified": False
        }
        
        if "active_conversions" not in queue_data:
            queue_data["active_conversions"] = []
        queue_data["active_conversions"].append(conversion)
        save_conversion_queue(queue_data)
        
        mark_reserves_activated(self.country_name, self.category, self.tech_type, qty)
        
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                data.update(self.player_data)
                break
        save_states(states)
        
        tech_name = get_tech_display_name(self.tech_type)
        hours = total_seconds / 3600
        game_days = hours * 3.75
        
        # Отправляем лог о начале расконсервации
        await send_mobilization_log(self.bot, "reserves_activation", {
            "country": self.country_name,
            "tech_name": tech_name,
            "quantity": qty,
            "cost": total_cost,
            "hours": hours,
            "color": DARK_THEME_COLOR
        })
        
        embed = discord.Embed(
            title=f"{EMOJIS['reserves']} Расконсервация запущена",
            description=f"{tech_name} x{format_number(qty)}",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=RESERVES_IMAGE)
        embed.add_field(name=f"{EMOJIS['money']} Стоимость", value=format_billion(total_cost), inline=True)
        embed.add_field(name=f"{EMOJIS['clock']} Реальное время", value=format_time(total_seconds), inline=True)
        embed.add_field(name=f"{EMOJIS['clock']} Игровое время", value=f"{game_days:.1f} дней", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== UI КЛАССЫ ДЛЯ МОБИЛИЗАЦИИ ====================

# Исправленный MobilizationMainView в mobilization.py

class MobilizationMainView(View):
    """Главное меню мобилизации"""
    def __init__(self, user_id, player_data, country_name, bot):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.bot = bot
    
    @discord.ui.button(label="Частичная мобилизация", style=discord.ButtonStyle.primary)
    async def partial_mobilization_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        plan = get_mobilization_plan(self.country_name)
        
        if plan["status"] == "active":
            await interaction.response.send_message("Мобилизация уже проводится! Дождитесь завершения или отмените.", ephemeral=True)
            return
        
        if plan["status"] == "planning":
            # Выполняем мобилизацию - здесь нужен defer, так как операция может быть долгой
            await interaction.response.defer(ephemeral=True)
            
            success, message, result = execute_partial_mobilization(self.player_data, self.bot)
            if success:
                states = load_states()
                for data in states["players"].values():
                    if data.get("assigned_to") == str(self.user_id):
                        data.update(self.player_data)
                        break
                save_states(states)
                
                embed = discord.Embed(
                    title=f"{EMOJIS['soldier']} Частичная мобилизация запущена!",
                    description=message,
                    color=DARK_THEME_COLOR
                )
                embed.add_field(name="Количество", value=format_number(result['target']), inline=True)
                embed.add_field(name="Время", value=f"{result['hours']} часов", inline=True)
                embed.set_footer(text="По завершении вы получите уведомление")
                
                await interaction.edit_original_response(embed=embed, view=None)
            else:
                await interaction.followup.send(message, ephemeral=True)
            return
        
        # Настройка плана - показываем модальное окно, НЕ используем defer
        stats = get_mobilization_stats(self.player_data)
        modal = MobilizationPlanModal(self.user_id, self.player_data, stats["max_possible"])
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Всеобщая мобилизация", style=discord.ButtonStyle.danger)
    async def total_mobilization_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        plan = get_mobilization_plan(self.country_name)
        
        if plan["status"] == "active":
            await interaction.response.send_message("Мобилизация уже проводится! Дождитесь завершения или отмените.", ephemeral=True)
            return
        
        if plan["status"] == "planning":
            await interaction.response.send_message("У вас настроен план частичной мобилизации. Сначала отмените его.", ephemeral=True)
            return
        
        # Всеобщая мобилизация требует defer
        await interaction.response.defer(ephemeral=True)
        
        success, message, result = execute_total_mobilization(self.player_data, self.bot)
        
        if success:
            states = load_states()
            for data in states["players"].values():
                if data.get("assigned_to") == str(self.user_id):
                    data.update(self.player_data)
                    break
            save_states(states)
            
            embed = discord.Embed(
                title=f"{EMOJIS['soldier']} Всеобщая мобилизация запущена!",
                description=message,
                color=DARK_THEME_COLOR
            )
            embed.add_field(name="Количество", value=format_number(result['target']), inline=True)
            embed.add_field(name="Время", value=f"{result['hours']} часов", inline=True)
            embed.set_footer(text="По завершении вы получите уведомление")
            
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            await interaction.followup.send(message, ephemeral=True)
    
    @discord.ui.button(label="Отменить мобилизацию", style=discord.ButtonStyle.secondary)
    async def cancel_mobilization_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        plan = get_mobilization_plan(self.country_name)
        
        if plan["status"] not in ["planning", "active"]:
            await interaction.response.send_message("Нет активной мобилизации для отмены.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        success, message = cancel_mobilization(self.player_data)
        
        if success:
            embed = discord.Embed(
                title=f"{EMOJIS['soldier']} Мобилизация отменена",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.edit_original_response(embed=embed, view=None)
        else:
            await interaction.followup.send(message, ephemeral=True)
    
    @discord.ui.button(label="Демобилизация", style=discord.ButtonStyle.secondary)
    async def demobilization_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        plan = get_mobilization_plan(self.country_name)
        
        if plan["status"] == "demobilizing":
            await interaction.response.send_message("Демобилизация уже проводится!", ephemeral=True)
            return
        
        current_army = self.player_data["state"]["army_size"]
        
        # Модальное окно - НЕ используем defer
        modal = DemobilizationModal(self.user_id, self.player_data, current_army, self.bot)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Статус мобилизации", style=discord.ButtonStyle.secondary)
    async def status_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        stats = get_mobilization_stats(self.player_data)
        plan = get_mobilization_plan(self.country_name)
        
        embed = discord.Embed(
            title=f"{EMOJIS['manpower']} Статус мобилизации: {self.country_name}",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=MOBILIZATION_IMAGE2)
        
        embed.add_field(
            name=f"{EMOJIS['manpower']} Население",
            value=format_number(stats['population']),
            inline=True
        )
        embed.add_field(
            name=f"{EMOJIS['soldier']} Текущая армия",
            value=format_number(stats['current_army']),
            inline=True
        )
        embed.add_field(
            name="Мобилизовано %",
            value=f"{stats['mobilization_percent']:.2f}%",
            inline=True
        )
        
        embed.add_field(
            name=f"{EMOJIS['manpower']} Доступно мобресурса",
            value=f"{format_number(stats['available_manpower'])} / {format_number(stats['max_manpower'])}",
            inline=True
        )
        embed.add_field(
            name=f"{EMOJIS['weapon']} Стрелковое оружие",
            value=format_number(stats['small_arms']),
            inline=True
        )
        embed.add_field(
            name="Максимум к призыву",
            value=format_number(stats['max_possible']),
            inline=True
        )
        
        if plan["status"] == "planning":
            embed.add_field(
                name="📋 План частичной мобилизации",
                value=f"Цель: {format_number(plan['target'])} человек\nСтатус: ожидает начала",
                inline=False
            )
        elif plan["status"] == "active":
            embed.add_field(
                name="🔄 Активная мобилизация",
                value=f"Цель: {format_number(plan['target'])} человек\nНачата: {plan['started_at'][:16]}",
                inline=False
            )
        elif plan["status"] == "demobilizing":
            embed.add_field(
                name="🏠 Демобилизация",
                value=f"Цель: {format_number(plan['target'])} человек\nНачата: {plan['started_at'][:16]}",
                inline=False
            )
        elif plan["status"] == "completed":
            embed.add_field(
                name="✅ Последняя мобилизация",
                value=f"Мобилизовано: {format_number(plan.get('mobilized', 0))} человек\n"
                      f"Завершена: {plan.get('completed_at', 'неизвестно')[:16]}",
                inline=False
            )
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    @discord.ui.button(label="Промышленная мобилизация", style=discord.ButtonStyle.primary)
    async def industrial_mobilization_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        await show_industrial_mobilization_menu(interaction, self.user_id, self.player_data, self.country_name, self.bot)
    
    @discord.ui.button(label="Конвертировать фабрики", style=discord.ButtonStyle.primary)
    async def convert_factories_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        regions = get_available_regions(self.player_data)
        if not regions:
            await interaction.response.send_message("В вашей стране нет регионов с гражданскими фабриками", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"{EMOJIS['civilian_factory']} Конвертация фабрик",
            description="Выберите регион для конвертации гражданских фабрик в военные",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=FACTORY_CONVERSION_IMAGE)
        
        view = FactoryConversionRegionView(self.user_id, self.player_data, self.country_name, regions, self.bot)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Расконсервация техники", style=discord.ButtonStyle.primary)
    async def reserves_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        await show_reserves_menu(interaction, self.user_id, self.player_data, self.country_name, self.bot)
    
    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        await show_mobilization_menu(interaction, self.user_id)


class FactoryConversionRegionView(View):
    """Выбор региона для конвертации фабрик"""
    def __init__(self, user_id, player_data, country_name, regions, bot):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.regions = regions
        self.bot = bot
        
        select = Select(placeholder="Выберите регион", options=[
            discord.SelectOption(label=region, value=region) for region in regions[:25]
        ])
        select.callback = self.region_select_callback
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def region_select_callback(self, interaction: discord.Interaction):
        region = interaction.data["values"][0]
        
        infra = load_infrastructure()
        civ_factories = 0
        for cid, data in infra["infrastructure"].items():
            if data.get("country") == self.country_name:
                for econ_region, econ_data in data.get("economic_regions", {}).items():
                    if region in econ_data.get("regions", {}):
                        region_data = econ_data["regions"][region]
                        civ_factories = region_data.get("civilian_factories", 0)
                        break
                break
        
        modal = FactoryConversionModal(self.user_id, self.player_data, self.country_name, region, civ_factories, self.bot)
        await interaction.response.send_modal(modal)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        await show_mobilization_menu(interaction, self.user_id)


class FactoryConversionModal(Modal, title="Конвертация фабрик"):
    def __init__(self, user_id, player_data, country_name, region, max_factories, bot):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.region = region
        self.max_factories = max_factories
        self.bot = bot
        
        self.quantity = TextInput(
            label=f"Количество фабрик (макс: {max_factories})",
            placeholder="Введите число",
            min_length=1,
            max_length=6,
            required=True
        )
        self.add_item(self.quantity)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        try:
            qty = int(self.quantity.value)
        except ValueError:
            await interaction.response.send_message("Введите корректное число", ephemeral=True)
            return
        
        if qty <= 0:
            await interaction.response.send_message("Количество должно быть положительным", ephemeral=True)
            return
        
        if qty > self.max_factories:
            await interaction.response.send_message(f"В регионе только {self.max_factories} гражданских фабрик", ephemeral=True)
            return
        
        success, message, result = convert_factories(self.player_data, self.country_name, self.region, qty, self.bot)
        
        if success:
            states = load_states()
            for data in states["players"].values():
                if data.get("assigned_to") == str(self.user_id):
                    data.update(self.player_data)
                    break
            save_states(states)
            
            embed = discord.Embed(
                title=f"{EMOJIS['military_factory']} Конвертация запущена",
                description=message,
                color=DARK_THEME_COLOR
            )
            embed.set_image(url=FACTORY_CONVERSION_IMAGE)
            embed.add_field(name="Количество", value=f"{qty} фабрик", inline=True)
            embed.add_field(name=f"{EMOJIS['money']} Стоимость", value=format_billion(result['cost']), inline=True)
            embed.add_field(name=f"{EMOJIS['clock']} Время", value=f"{result['hours']} часов", inline=True)
            
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class IndustrialMobilizationView(View):
    """Меню промышленной мобилизации"""
    def __init__(self, user_id, player_data, country_name, bot):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.bot = bot
    
    @discord.ui.button(label="Кустарная бронемашина", style=discord.ButtonStyle.secondary)
    async def armored_vehicle_button(self, interaction: discord.Interaction, button: Button):
        await self.start_production(interaction, "armored_vehicle_improvised")
    
    @discord.ui.button(label="Кустарный БТР", style=discord.ButtonStyle.secondary)
    async def btr_button(self, interaction: discord.Interaction, button: Button):
        await self.start_production(interaction, "btr_improvised")
    
    @discord.ui.button(label="Кустарная гаубица", style=discord.ButtonStyle.secondary)
    async def howitzer_button(self, interaction: discord.Interaction, button: Button):
        await self.start_production(interaction, "howitzer_improvised")
    
    @discord.ui.button(label="Кустарное ПВО", style=discord.ButtonStyle.secondary)
    async def pvo_button(self, interaction: discord.Interaction, button: Button):
        await self.start_production(interaction, "short_range_air_defense_improvised")
    
    @discord.ui.button(label="Кустарный FPV-дрон", style=discord.ButtonStyle.secondary)
    async def fpv_button(self, interaction: discord.Interaction, button: Button):
        await self.start_production(interaction, "fpv_drone_improvised")
    
    @discord.ui.button(label="Кустарный дрон-камикадзе", style=discord.ButtonStyle.secondary)
    async def kamikaze_button(self, interaction: discord.Interaction, button: Button):
        await self.start_production(interaction, "kamikaze_drone_improvised")
    
    @discord.ui.button(label="Кустарный надводный дрон", style=discord.ButtonStyle.secondary)
    async def usv_button(self, interaction: discord.Interaction, button: Button):
        await self.start_production(interaction, "usv_attack_improvised")
    
    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        await show_mobilization_menu(interaction, self.user_id)
    
    async def start_production(self, interaction: discord.Interaction, recipe_id: str):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        regions = get_available_regions(self.player_data)
        if not regions:
            await interaction.response.send_message("В вашей стране нет регионов с гражданскими фабриками", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"{EMOJIS['civilian_factory']} Производство",
            description=f"Выберите регион для производства",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=INDUSTRIAL_MOBILIZATION_IMAGE)
        
        view = ProductionRegionView(self.user_id, self.player_data, self.country_name, recipe_id, regions, self.bot)
        await interaction.response.edit_message(embed=embed, view=view)


class ProductionRegionView(View):
    """Выбор региона для производства"""
    def __init__(self, user_id, player_data, country_name, recipe_id, regions, bot):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.recipe_id = recipe_id
        self.regions = regions
        self.bot = bot
        
        select = Select(placeholder="Выберите регион", options=[
            discord.SelectOption(label=region, value=region) for region in regions[:25]
        ])
        select.callback = self.region_select_callback
        self.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def region_select_callback(self, interaction: discord.Interaction):
        region = interaction.data["values"][0]
        
        recipe = MOBILIZATION_RECIPES.get(self.recipe_id)
        max_quantity = 10
        
        modal = ProductionQuantityModal(self.user_id, self.player_data, self.country_name, self.recipe_id, region, max_quantity, self.bot)
        await interaction.response.send_modal(modal)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        await show_industrial_mobilization_menu(interaction, self.user_id, self.player_data, self.country_name, self.bot)


class ProductionQuantityModal(Modal, title="Количество партий"):
    def __init__(self, user_id, player_data, country_name, recipe_id, region, max_quantity, bot):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.recipe_id = recipe_id
        self.region = region
        self.max_quantity = max_quantity
        self.bot = bot
        
        recipe = MOBILIZATION_RECIPES.get(recipe_id)
        recipe_name = recipe["name"] if recipe else "Неизвестно"
        
        self.quantity = TextInput(
            label=f"Количество партий (макс: {max_quantity})",
            placeholder=f"Одна партия = {recipe['military_output']['quantity']} ед. {recipe_name}",
            min_length=1,
            max_length=3,
            required=True
        )
        self.add_item(self.quantity)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        try:
            qty = int(self.quantity.value)
        except ValueError:
            await interaction.response.send_message("Введите корректное число", ephemeral=True)
            return
        
        if qty <= 0:
            await interaction.response.send_message("Количество должно быть положительным", ephemeral=True)
            return
        
        if qty > self.max_quantity:
            await interaction.response.send_message(f"Максимум {self.max_quantity} партий за раз", ephemeral=True)
            return
        
        success, message, result = start_mobilization_production(self.player_data, self.recipe_id, self.region, qty, self.bot)
        
        if success:
            states = load_states()
            for data in states["players"].values():
                if data.get("assigned_to") == str(self.user_id):
                    data.update(self.player_data)
                    break
            save_states(states)
            
            embed = discord.Embed(
                title=f"{EMOJIS['civilian_factory']} Производство запущено",
                description=message,
                color=DARK_THEME_COLOR
            )
            embed.set_image(url=INDUSTRIAL_MOBILIZATION_IMAGE)
            embed.add_field(name="Количество партий", value=f"{qty}", inline=True)
            embed.add_field(name="Всего единиц", value=f"{result['output']['quantity']} ед.", inline=True)
            embed.add_field(name=f"{EMOJIS['clock']} Время", value=f"{result['minutes']} минут", inline=True)
            embed.add_field(name="Регион", value=self.region, inline=True)
            
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class MobilizationPlanModal(Modal, title="Настройка плана частичной мобилизации"):
    def __init__(self, user_id, player_data, max_possible):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.max_possible = max_possible
        
        self.quantity_input = TextInput(
            label=f"Количество человек (макс: {format_number(max_possible)})",
            placeholder="Введите число",
            min_length=1,
            max_length=9,
            required=True
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
        except ValueError:
            await interaction.response.send_message("Введите корректное число", ephemeral=True)
            return
        
        if quantity <= 0:
            await interaction.response.send_message("Количество должно быть положительным", ephemeral=True)
            return
        
        if quantity > self.max_possible:
            await interaction.response.send_message(f"Максимум можно мобилизовать {format_number(self.max_possible)} человек", ephemeral=True)
            return
        
        success, message = start_mobilization_plan(self.player_data, quantity)
        
        if success:
            embed = discord.Embed(
                title=f"{EMOJIS['manpower']} План частичной мобилизации настроен",
                description=message,
                color=DARK_THEME_COLOR
            )
            embed.add_field(name="Цель", value=format_number(quantity), inline=True)
            embed.add_field(name="Следующий шаг", value="Нажмите 'Частичная мобилизация' для запуска", inline=False)
            
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class DemobilizationModal(Modal, title="Демобилизация"):
    def __init__(self, user_id, player_data, max_army, bot):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        self.max_army = max_army
        self.bot = bot
        
        self.quantity_input = TextInput(
            label=f"Количество человек (макс: {format_number(max_army)})",
            placeholder="Введите число",
            min_length=1,
            max_length=9,
            required=True
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Это не ваше меню", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
        except ValueError:
            await interaction.response.send_message("Введите корректное число", ephemeral=True)
            return
        
        if quantity <= 0:
            await interaction.response.send_message("Количество должно быть положительным", ephemeral=True)
            return
        
        if quantity > self.max_army:
            await interaction.response.send_message(f"В армии {format_number(self.max_army)} человек", ephemeral=True)
            return
        
        success, message = start_demobilization(self.player_data, quantity, self.bot)
        
        if success:
            embed = discord.Embed(
                title=f"{EMOJIS['manpower']} Демобилизация запущена",
                description=message,
                color=DARK_THEME_COLOR
            )
            embed.add_field(name="Количество", value=format_number(quantity), inline=True)
            embed.add_field(name=f"{EMOJIS['clock']} Время", value=f"{max(1, quantity // 1000)} часов", inline=True)
            
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.send_message(message, ephemeral=True)


# ==================== ОСНОВНОЕ МЕНЮ ====================

async def show_mobilization_menu(ctx, user_id: int):
    """Показать меню мобилизации населения"""
    states = load_states()
    
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        if hasattr(ctx, 'response'):
            await ctx.response.send_message("У вас нет государства", ephemeral=True)
        else:
            await ctx.send("У вас нет государства")
        return
    
    country_name = player_data["state"]["statename"]
    stats = get_mobilization_stats(player_data)
    plan = get_mobilization_plan(country_name)
    
    embed = discord.Embed(
        title=f"{EMOJIS['manpower']} Мобилизация населения",
        description="Управление призывом граждан на военную службу",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=MOBILIZATION_IMAGE)
    
    embed.add_field(
        name="📊 Текущая ситуация",
        value=f"{EMOJIS['manpower']} **Население:** {format_number(stats['population'])} чел.\n"
              f"{EMOJIS['soldier']} **Армия:** {format_number(stats['current_army'])} чел. ({stats['mobilization_percent']:.2f}% населения)\n"
              f"{EMOJIS['manpower']} **Мобресурс:** {format_number(stats['available_manpower'])} / {format_number(stats['max_manpower'])} чел.\n"
              f"{EMOJIS['weapon']} **Стрелковое оружие:** {format_number(stats['small_arms'])} ед.\n"
              f"**Максимум к призыву:** {format_number(stats['max_possible'])} чел.",
        inline=False
    )
    
    if plan["status"] == "planning":
        embed.add_field(
            name="📋 План частичной мобилизации",
            value=f"Цель: {format_number(plan['target'])} человек\n"
                  f"Статус: ожидает начала\n"
                  f"Нажмите 'Частичная мобилизация' для запуска",
            inline=False
        )
    elif plan["status"] == "active":
        embed.add_field(
            name="🔄 Активная мобилизация",
            value=f"Цель: {format_number(plan['target'])} человек\n"
                  f"Начата: {plan['started_at'][:16]}\n"
                  f"Статус: выполняется",
            inline=False
        )
    elif plan["status"] == "demobilizing":
        embed.add_field(
            name="🏠 Демобилизация",
            value=f"Цель: {format_number(plan['target'])} человек\n"
                  f"Начата: {plan['started_at'][:16]}\n"
                  f"Статус: выполняется",
            inline=False
        )
    elif plan["status"] == "completed":
        embed.add_field(
            name="✅ Последняя мобилизация",
            value=f"Мобилизовано: {format_number(plan.get('mobilized', 0))} человек\n"
                  f"Завершена: {plan.get('completed_at', 'неизвестно')[:16]}",
            inline=False
        )
    
    embed.add_field(
        name="📌 Как это работает",
        value="**Частичная мобилизация** — настройте план и запустите\n"
              "**Всеобщая мобилизация** — максимальный призыв (7% населения)\n"
              "**Демобилизация** — возврат солдат в резерв\n\n"
              "Время мобилизации: 1 час на 1000 человек",
        inline=False
    )
    
    view = MobilizationMainView(user_id, player_data, country_name, ctx.client if hasattr(ctx, 'client') else None)
    
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx.send(embed=embed, view=view, ephemeral=True)


async def show_industrial_mobilization_menu(interaction, user_id: int, player_data, country_name, bot):
    """Показать меню промышленной мобилизации"""
    embed = discord.Embed(
        title=f"{EMOJIS['factory']} Промышленная мобилизация",
        description="Производство импровизированной военной техники на гражданских мощностях",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=INDUSTRIAL_MOBILIZATION_IMAGE)
    
    embed.add_field(
        name="Доступные рецепты",
        value="**Кустарная бронемашина** — 1 авто + сталь + оружие (15 шт)\n"
              "**Кустарный БТР** — 1 грузовик + сталь + оружие (8 шт)\n"
              "**Кустарная гаубица** — сталь + электроника (10 шт)\n"
              "**Кустарное ПВО** — 1 авто + электроника + ПЗРК (6 шт)\n"
              "**Кустарный FPV-дрон** — алюминий + электроника (100 шт)\n"
              "**Кустарный дрон-камикадзе** — алюминий + электроника (20 шт)\n"
              "**Кустарный надводный дрон** — алюминий + сталь + электроника (5 шт)",
        inline=False
    )
    
    view = IndustrialMobilizationView(user_id, player_data, country_name, bot)
    await interaction.response.edit_message(embed=embed, view=view)


async def show_reserves_menu(interaction, user_id: int, player_data, country_name, bot):
    """Показать меню расконсервации техники"""
    reserves = get_available_reserves(country_name)
    
    has_any = False
    for category in reserves.values():
        if category and any(v > 0 for v in category.values()):
            has_any = True
            break
    
    if not has_any:
        embed = discord.Embed(
            title=f"{EMOJIS['reserves']} Расконсервация техники",
            description="В ваших резервах нет техники, доступной для расконсервации",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=RESERVES_IMAGE)
        view = MobilizationMainView(user_id, player_data, country_name, bot)
        await interaction.response.edit_message(embed=embed, view=view)
        return
    
    embed = discord.Embed(
        title=f"{EMOJIS['reserves']} Расконсервация техники",
        description="Выберите категорию техники для расконсервации",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=RESERVES_IMAGE)
    
    view = ReservesCategoryView(user_id, player_data, country_name, reserves, bot)
    await interaction.response.edit_message(embed=embed, view=view)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_mobilization_menu',
    'mobilization_completion_loop',
    'reserves_conversion_loop',
    'MOBILIZATION_RECIPES',
    'MILITARY_RESERVES',
    'convert_factories',
    'start_mobilization_production',
    'get_available_regions'
]

# espionage.py - Модуль для управления разведывательными операциями

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import random
import asyncio
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from utils import format_billion, format_number, load_states, save_states, DARK_THEME_COLOR
from paths import get_data_path
from political_power import get_political_power, spend_political_power
from intelligence_agencies import get_agencies_by_country, get_agency, get_all_agencies

# Файл для хранения данных о разведке
ESPIONAGE_FILE = get_data_path('espionage.json')

# ID канала для логов
try:
    from config import ESPIONAGE_LOG_CHANNEL_ID
except ImportError:
    ESPIONAGE_LOG_CHANNEL_ID = None

# ==================== ТИПЫ ОПЕРАЦИЙ ====================

ESPIONAGE_OPERATIONS = {
    # 1. РАЗВЕДЫВАТЕЛЬНЫЕ ОПЕРАЦИИ (дают бонус к следующим операциям)
    "human_intelligence": {
        "id": "human_intelligence",
        "name": "Агентурная разведка",
        "description": "Вербовка источников в государственных структурах противника. Даёт бонус к успеху следующих операций в этой стране.",
        "category": "intelligence",
        "base_cost": 5000000,  # 5 млн $
        "pp_cost": 5,
        "duration_hours": 72,  # 3 дня
        "personnel_required": 8,
        "base_risk": 20,
        "base_detection": 15,
        "effect": {
            "type": "intel_bonus",
            "value": 10,  # +10% к успеху следующей операции
            "duration_days": 7,
            "stackable": False,
            "target": "next_operation"
        }
    },
    "cyber_intelligence": {
        "id": "cyber_intelligence",
        "name": "Киберразведка",
        "description": "Внедрение в IT-системы министерств и ведомств. Доступ к секретной переписке и документам.",
        "category": "cyber",
        "base_cost": 10000000,
        "pp_cost": 10,
        "duration_hours": 96,  # 4 дня
        "personnel_required": 6,
        "base_risk": 30,
        "base_detection": 25,
        "effect": {
            "type": "intel_bonus",
            "value": 20,
            "duration_days": 7,
            "stackable": False,
            "target": "next_operation"
        }
    },
    "military_intelligence": {
        "id": "military_intelligence",
        "name": "Военная разведка",
        "description": "Сбор данных о дислокации войск, вооружении и планах командования противника.",
        "category": "military",
        "base_cost": 7000000,
        "pp_cost": 7,
        "duration_hours": 60,  # 2.5 дня
        "personnel_required": 10,
        "base_risk": 25,
        "base_detection": 20,
        "effect": {
            "type": "intel_bonus",
            "value": 15,
            "duration_days": 7,
            "stackable": False,
            "target": "military_operations"
        }
    },
    "diplomatic_intelligence": {
        "id": "diplomatic_intelligence",
        "name": "Дипломатическая разведка",
        "description": "Сбор данных через военных атташе и дипломатические каналы. Информация о внешнеполитических планах.",
        "category": "intelligence",
        "base_cost": 6000000,
        "pp_cost": 6,
        "duration_hours": 48,  # 2 дня
        "personnel_required": 4,
        "base_risk": 15,
        "base_detection": 10,
        "effect": {
            "type": "intel_bonus",
            "value": 10,
            "duration_days": 5,
            "stackable": False,
            "target": "diplomatic_ops"
        }
    },

    # 2. ДИВЕРСИОННЫЕ ОПЕРАЦИИ (временный урон инфраструктуре)
    "sabotage_factory": {
        "id": "sabotage_factory",
        "name": "Диверсия на заводе",
        "description": "Вывод из строя военного или промышленного объекта. Временно снижает производство.",
        "category": "sabotage",
        "base_cost": 15000000,
        "pp_cost": 15,
        "duration_hours": 120,  # 5 дней
        "personnel_required": 12,
        "base_risk": 35,
        "base_detection": 30,
        "effect": {
            "type": "production_penalty",
            "value": 20,  # -20% производства на 7 дней
            "duration_days": 7,
            "target": "military_factories"
        }
    },
    "sabotage_energy": {
        "id": "sabotage_energy",
        "name": "Диверсия на электростанции",
        "description": "Вывод из строя энергообъекта. Временно снижает энергогенерацию в регионе.",
        "category": "sabotage",
        "base_cost": 12000000,
        "pp_cost": 12,
        "duration_hours": 96,  # 4 дня
        "personnel_required": 8,
        "base_risk": 40,
        "base_detection": 35,
        "effect": {
            "type": "power_penalty",
            "value": 30,  # -30% энергии на 5 дней
            "duration_days": 5,
            "target": "power_plants"
        }
    },
    "sabotage_transport": {
        "id": "sabotage_transport",
        "name": "Диверсия на транспорте",
        "description": "Подрыв железнодорожных путей или мостов. Временно нарушает логистику.",
        "category": "sabotage",
        "base_cost": 8000000,
        "pp_cost": 8,
        "duration_hours": 72,  # 3 дня
        "personnel_required": 6,
        "base_risk": 30,
        "base_detection": 25,
        "effect": {
            "type": "logistics_penalty",
            "value": 25,  # -25% эффективности логистики на 4 дня
            "duration_days": 4,
            "target": "transport"
        }
    },
    "cyber_sabotage": {
        "id": "cyber_sabotage",
        "name": "Кибердиверсия",
        "description": "Атака на системы управления. Временно нарушает работу госучреждений.",
        "category": "cyber",
        "base_cost": 10000000,
        "pp_cost": 10,
        "duration_hours": 48,  # 2 дня
        "personnel_required": 5,
        "base_risk": 25,
        "base_detection": 20,
        "effect": {
            "type": "gov_penalty",
            "value": 15,  # -15% эффективности правительства на 3 дня
            "duration_days": 3,
            "target": "government"
        }
    },

    # 3. ОПЕРАЦИИ ВЛИЯНИЯ (влияют на стабильность и доверие)
    "information_campaign": {
        "id": "information_campaign",
        "name": "Информационная кампания",
        "description": "Распространение дезинформации через СМИ и соцсети. Снижает доверие к власти.",
        "category": "influence",
        "base_cost": 6000000,
        "pp_cost": 6,
        "duration_hours": 72,  # 3 дня
        "personnel_required": 10,
        "base_risk": 25,
        "base_detection": 20,
        "effect": {
            "type": "trust_penalty",
            "value": 5,  # -5% доверия
            "duration_days": 7,
            "is_permanent": False
        }
    },
    "support_opposition": {
        "id": "support_opposition",
        "name": "Поддержка оппозиции",
        "description": "Финансирование и информационная поддержка оппозиционных групп.",
        "category": "influence",
        "base_cost": 10000000,
        "pp_cost": 10,
        "duration_hours": 120,  # 5 дней
        "personnel_required": 8,
        "base_risk": 40,
        "base_detection": 35,
        "effect": {
            "type": "stability_penalty",
            "value": 8,  # -8% стабильности
            "duration_days": 10,
            "is_permanent": False
        }
    },
    "compromat_campaign": {
        "id": "compromat_campaign",
        "name": "Дискредитация чиновника",
        "description": "Публикация компромата на конкретного государственного деятеля.",
        "category": "influence",
        "base_cost": 12000000,
        "pp_cost": 12,
        "duration_hours": 96,  # 4 дня
        "personnel_required": 6,
        "base_risk": 35,
        "base_detection": 30,
        "effect": {
            "type": "popularity_penalty",
            "value": 10,  # -10% популярности правительства
            "duration_days": 14,
            "is_permanent": False
        }
    },
    "corruption_operation": {
        "id": "corruption_operation",
        "name": "Подкуп чиновников",
        "description": "Подкуп среднего звена госслужащих для получения доступа к документам.",
        "category": "influence",
        "base_cost": 15000000,
        "pp_cost": 15,
        "duration_hours": 120,  # 5 дней
        "personnel_required": 4,
        "base_risk": 45,
        "base_detection": 40,
        "effect": {
            "type": "corruption_boost",
            "value": 5,  # +5% коррупции на 30 дней
            "duration_days": 30,
            "is_permanent": False
        }
    },

    # 4. КОНТРРАЗВЕДЫВАТЕЛЬНЫЕ ОПЕРАЦИИ (защита)
    "counterintelligence_sweep": {
        "id": "counterintelligence_sweep",
        "name": "Поиск 'кротов'",
        "description": "Выявление вражеских агентов в своих структурах. Повышает безопасность.",
        "category": "counterintel",
        "base_cost": 8000000,
        "pp_cost": 8,
        "duration_hours": 96,  # 4 дня
        "personnel_required": 15,
        "base_risk": 15,
        "base_detection": 5,
        "effect": {
            "type": "security_boost",
            "value": 15,  # +15% к защите от разведки на 30 дней
            "duration_days": 30,
            "target": "own"
        }
    },
    "disinformation": {
        "id": "disinformation",
        "name": "Дезинформация противника",
        "description": "Подброс ложных данных вражеской разведке. Снижает успех их операций.",
        "category": "counterintel",
        "base_cost": 6000000,
        "pp_cost": 6,
        "duration_hours": 72,  # 3 дня
        "personnel_required": 8,
        "base_risk": 25,
        "base_detection": 15,
        "effect": {
            "type": "enemy_penalty",
            "value": 10,  # -10% к успеху вражеских операций на 14 дней
            "duration_days": 14,
            "target": "enemy_intel"
        }
    },
    "agent_protection": {
        "id": "agent_protection",
        "name": "Операция прикрытия",
        "description": "Защита своих источников и агентов от провала.",
        "category": "counterintel",
        "base_cost": 5000000,
        "pp_cost": 5,
        "duration_hours": 48,  # 2 дня
        "personnel_required": 6,
        "base_risk": 10,
        "base_detection": 5,
        "effect": {
            "type": "agent_safety",
            "value": 20,  # +20% к выживаемости агентов на 14 дней
            "duration_days": 14,
            "target": "own_agents"
        }
    },

    # 5. СПЕЦИАЛЬНЫЕ ОПЕРАЦИИ (рискованные, но с мощным эффектом)
    "elimination": {
        "id": "elimination",
        "name": "Ликвидация",
        "description": "Устранение ключевой фигуры: полевого командира, учёного, влиятельного чиновника.",
        "category": "special",
        "base_cost": 30000000,
        "pp_cost": 30,
        "duration_hours": 168,  # 7 дней
        "personnel_required": 6,
        "base_risk": 60,
        "base_detection": 50,
        "effect": {
            "type": "personality_eliminated",
            "value": "Устранение цели",
            "secondary_effects": {
                "stability_hit": 5,
                "military_penalty": 10  # -10% боеспособности на 7 дней
            }
        }
    },
    "rescue_operation": {
        "id": "rescue_operation",
        "name": "Освобождение агента",
        "description": "Эвакуация провалившегося агента из плена или с территории противника.",
        "category": "special",
        "base_cost": 20000000,
        "pp_cost": 20,
        "duration_hours": 72,  # 3 дня
        "personnel_required": 8,
        "base_risk": 50,
        "base_detection": 40,
        "effect": {
            "type": "agent_rescued",
            "value": "Возврат потерянных сотрудников",
            "personnel_return": 3
        }
    },
    "document_theft": {
        "id": "document_theft",
        "name": "Захват документации",
        "description": "Кража секретных архивов из охраняемого объекта.",
        "category": "special",
        "base_cost": 25000000,
        "pp_cost": 25,
        "duration_hours": 120,  # 5 дней
        "personnel_required": 8,
        "base_risk": 55,
        "base_detection": 45,
        "effect": {
            "type": "intel_bonus",
            "value": 30,  # +30% к успеху всех операций на 14 дней
            "duration_days": 14,
            "stackable": False
        }
    },
    "false_flag": {
        "id": "false_flag",
        "name": "Операция под чужим флагом",
        "description": "Имитация действий другой страны для провокации конфликта.",
        "category": "special",
        "base_cost": 40000000,
        "pp_cost": 40,
        "duration_hours": 240,  # 10 дней
        "personnel_required": 12,
        "base_risk": 70,
        "base_detection": 60,
        "effect": {
            "type": "relations_hit",
            "value": 20,  # -20% к отношениям между двумя странами
            "duration_days": 60,
            "target": "relations"
        }
    },

    # 6. ЭКОНОМИЧЕСКИЕ ОПЕРАЦИИ
    "industrial_espionage": {
        "id": "industrial_espionage",
        "name": "Промышленный шпионаж",
        "description": "Кража технологий и патентов. Ускоряет собственные исследования.",
        "category": "economic",
        "base_cost": 12000000,
        "pp_cost": 12,
        "duration_hours": 96,  # 4 дня
        "personnel_required": 6,
        "base_risk": 30,
        "base_detection": 25,
        "effect": {
            "type": "research_boost",
            "value": 15,  # +15% скорости исследований на 30 дней
            "duration_days": 30,
            "target": "own_research"
        }
    },
    "market_manipulation": {
        "id": "market_manipulation",
        "name": "Манипуляция рынком",
        "description": "Искусственное создание дефицита или паники на рынке.",
        "category": "economic",
        "base_cost": 15000000,
        "pp_cost": 15,
        "duration_hours": 72,  # 3 дня
        "personnel_required": 5,
        "base_risk": 35,
        "base_detection": 30,
        "effect": {
            "type": "economic_penalty",
            "value": 5,  # -5% ВВП на 14 дней
            "duration_days": 14,
            "target": "enemy_economy"
        }
    },
    "contract_sabotage": {
        "id": "contract_sabotage",
        "name": "Срыв контрактов",
        "description": "Подкуп посредников и чиновников для срыва важных контрактов.",
        "category": "economic",
        "base_cost": 10000000,
        "pp_cost": 10,
        "duration_hours": 96,  # 4 дня
        "personnel_required": 4,
        "base_risk": 25,
        "base_detection": 20,
        "effect": {
            "type": "budget_penalty",
            "value": 8,  # -8% бюджета на 14 дней
            "duration_days": 14,
            "target": "enemy_budget"
        }
    },

    # 7. КИБЕРОПЕРАЦИИ
    "ddos_attack": {
        "id": "ddos_attack",
        "name": "DDoS-атака",
        "description": "Вывод из строя государственных сайтов и порталов. Временный хаос в работе.",
        "category": "cyber",
        "base_cost": 4000000,
        "pp_cost": 4,
        "duration_hours": 24,  # 1 день
        "personnel_required": 3,
        "base_risk": 15,
        "base_detection": 10,
        "effect": {
            "type": "gov_penalty",
            "value": 10,  # -10% эффективности на 2 дня
            "duration_days": 2,
            "target": "government"
        }
    },
    "social_media_attack": {
        "id": "social_media_attack",
        "name": "Атака в соцсетях",
        "description": "Массированная дезинформация через боты и фейковые аккаунты.",
        "category": "cyber",
        "base_cost": 5000000,
        "pp_cost": 5,
        "duration_hours": 48,  # 2 дня
        "personnel_required": 8,
        "base_risk": 20,
        "base_detection": 15,
        "effect": {
            "type": "trust_penalty",
            "value": 3,  # -3% доверия на 7 дней
            "duration_days": 7,
            "target": "population"
        }
    },
    "crypto_theft": {
        "id": "crypto_theft",
        "name": "Кража криптовалют",
        "description": "Хищение цифровых активов через взлом бирж и кошельков.",
        "category": "cyber",
        "base_cost": 20000000,
        "pp_cost": 20,
        "duration_hours": 120,  # 5 дней
        "personnel_required": 5,
        "base_risk": 50,
        "base_detection": 45,
        "effect": {
            "type": "budget_damage",
            "value": 10,  # -10% бюджета разово
            "duration_days": 0,
            "is_permanent": True
        }
    }
}

# ==================== КАТЕГОРИИ ДЛЯ УДОБСТВА ====================

OPERATION_CATEGORIES = {
    "intelligence": "Разведывательные операции",
    "sabotage": "Диверсионные операции",
    "influence": "Операции влияния",
    "counterintel": "Контрразведка",
    "special": "Специальные операции",
    "economic": "Экономические операции",
    "cyber": "Кибероперации"
}

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_espionage_data():
    """Загрузка данных о разведке"""
    try:
        with open(ESPIONAGE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {
                    "active_operations": [],
                    "completed_operations": [],
                    "counterintelligence": {},
                    "detected_attempts": []
                }
            return json.loads(content)
    except FileNotFoundError:
        return {
            "active_operations": [],
            "completed_operations": [],
            "counterintelligence": {},
            "detected_attempts": []
        }
    except json.JSONDecodeError:
        return {
            "active_operations": [],
            "completed_operations": [],
            "counterintelligence": {},
            "detected_attempts": []
        }

def save_espionage_data(data):
    """Сохранение данных о разведке"""
    with open(ESPIONAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С АГЕНТСТВАМИ ====================

def initialize_agency_state(agency, player_data):
    """Инициализирует состояние агентства на основе данных игрока"""
    # Расчёт финансирования
    budget = player_data["economy"]["budget"]
    agency.current_funding = budget * agency.budget_multiplier / 100
    
    # Расчёт персонала на основе населения и бюджета
    population = player_data["state"]["population"]
    gov_eff = player_data.get("government_efficiency", 50)
    
    # Базовая формула: 1 сотрудник на 5000 населения при базовом финансировании
    base_personnel = int(population / 5000)
    funding_factor = agency.budget_multiplier
    agency.available_personnel = int(base_personnel * funding_factor)
    agency.total_personnel = agency.available_personnel
    
    # Расчёт оснащения на основе технологий и бюджета
    army = player_data.get("army", {})
    equipment = army.get("equipment", {})
    
    # Учитываем наличие спецсредств
    tech_bonus = 0
    if "fpv_drones" in equipment:
        tech_bonus += equipment["fpv_drones"] / 10000
    if "small_arms" in equipment:
        tech_bonus += equipment["small_arms"] / 50000
    
    agency.equipment_level = min(95, 40 + int(tech_bonus) + int(agency.budget_multiplier * 10))
    
    return agency


def get_agencies_status(country_name, player_data):
    """Возвращает список агентств страны с их статусом"""
    agencies_dict = get_agencies_by_country(country_name)
    agencies = list(agencies_dict.values())
    
    result = []
    for agency in agencies:
        # Создаём копию с динамическими полями
        agency_copy = agency
        initialize_agency_state(agency_copy, player_data)
        result.append(agency_copy)
    
    return result


# ==================== ФУНКЦИИ ДЛЯ РАСЧЁТА УСПЕХА ====================

def calculate_operation_success(base_risk, country_data, intel_bonus=0, agency=None):
    """
    Рассчитывает успех операции на основе риска и бонусов
    """
    # Базовая вероятность успеха
    success_chance = 100 - base_risk
    
    # Модификатор от контрразведки цели
    target_counterintel = country_data.get("counterintelligence", {}).get("level", 0)
    success_chance -= target_counterintel / 2
    
    # Бонус от разведданных
    success_chance += intel_bonus
    
    # Модификаторы от агентства
    if agency:
        # Оснащение (до +15%)
        success_chance += (agency.equipment_level - 50) / 3
        
        # Влияние в госаппарате (до +10%)
        success_chance += (agency.influence - 30) / 4
        
        # Коррупция (до -15%)
        success_chance -= agency.corruption / 4
    
    # Ограничиваем
    success_chance = max(10, min(95, success_chance))
    
    return success_chance


def calculate_detection_chance(base_detection, country_data, agency=None):
    """
    Рассчитывает шанс обнаружения операции
    """
    detection_chance = base_detection
    
    # Модификатор от контрразведки цели
    target_counterintel = country_data.get("counterintelligence", {}).get("level", 0)
    detection_chance += target_counterintel / 3
    
    # Модификаторы от агентства
    if agency:
        # Влияние помогает скрывать операции
        detection_chance -= agency.influence / 10
        # Коррупция увеличивает шанс утечки
        detection_chance += agency.corruption / 8
    
    # Ограничиваем
    detection_chance = max(5, min(80, detection_chance))
    
    return detection_chance


# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class AgencySelect(Select):
    """Выбор агентства для проведения операции"""
    
    def __init__(self, user_id, country_name, agencies):
        self.user_id = user_id
        self.country_name = country_name
        
        options = []
        for agency in agencies[:25]:
            # Определяем цветовой индикатор на основе коррупции
            if agency.corruption < 20:
                status = "🟢"
            elif agency.corruption < 40:
                status = "🟡"
            else:
                status = "🔴"
            
            options.append(
                discord.SelectOption(
                    label=agency.name,
                    description=f"Влияние: {agency.influence}% | Коррупция: {agency.corruption}%",
                    value=agency.id,
                    emoji=status
                )
            )
        
        super().__init__(
            placeholder="Выберите агентство...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        agency_id = self.values[0]
        agency = get_agency(agency_id)
        
        if not agency:
            await interaction.response.send_message("❌ Агентство не найдено!", ephemeral=True)
            return
        
        # Получаем актуальные данные игрока
        from bot import load_states
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("❌ Ошибка загрузки данных!", ephemeral=True)
            return
        
        # Инициализируем состояние агентства
        initialize_agency_state(agency, player_data)
        
        # Показываем информацию об агентстве
        embed = discord.Embed(
            title=f"🕵️ {agency.name}",
            description=agency.description,
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Год основания", value=str(agency.founded), inline=True)
        embed.add_field(name="Влияние в госаппарате", value=f"{agency.influence}%", inline=True)
        embed.add_field(name="Коррумпированность", value=f"{agency.corruption}%", inline=True)
        
        embed.add_field(name="💰 Финансирование", value=format_billion(agency.current_funding), inline=True)
        embed.add_field(name="👥 Сотрудников", value=f"{agency.available_personnel:,}", inline=True)
        embed.add_field(name="📊 Оснащение", value=f"{agency.equipment_level}%", inline=True)
        
        # Кнопки для действий
        view = AgencyActionView(self.user_id, self.country_name, agency)
        
        await interaction.response.edit_message(embed=embed, view=view)


class AgencyActionView(View):
    """Действия с агентством"""
    
    def __init__(self, user_id, country_name, agency):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.agency = agency
    
    @discord.ui.button(label="Операции", style=discord.ButtonStyle.danger)
    async def operations_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Показываем выбор категорий операций
        embed = discord.Embed(
            title=f"Выбор операции - {self.agency.name}",
            description="Выберите категорию операции:",
            color=DARK_THEME_COLOR
        )
        
        select = OperationCategorySelect(self.user_id, self.country_name, list(OPERATION_CATEGORIES.keys()))
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад к агентству", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_agency
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Информация", style=discord.ButtonStyle.secondary)
    async def info_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Детальная информация об агентстве
        embed = discord.Embed(
            title=f"📊 Детальная информация - {self.agency.name}",
            color=DARK_THEME_COLOR
        )
        
        # Модификаторы
        success_bonus = (self.agency.equipment_level - 50) / 3 + (self.agency.influence - 30) / 4
        detection_penalty = self.agency.corruption / 8 - self.agency.influence / 10
        
        embed.add_field(
            name="Бонус к успеху операций",
            value=f"+{success_bonus:.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="Шанс обнаружения",
            value=f"{detection_penalty:+.1f}%",
            inline=True
        )
        
        embed.add_field(
            name="Доступно операций",
            value=str(len(ESPIONAGE_OPERATIONS)),
            inline=True
        )
        
        embed.add_field(
            name="Успешных операций",
            value=str(self.agency.operations_completed),
            inline=True
        )
        
        embed.add_field(
            name="Провалов",
            value=str(self.agency.operations_failed),
            inline=True
        )
        
        embed.add_field(
            name="Потеряно сотрудников",
            value=str(self.agency.personnel_lost),
            inline=True
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def back_to_agency(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Возвращаемся к информации об агентстве
        embed = discord.Embed(
            title=f"{self.agency.name}",
            description=self.agency.description,
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Год основания", value=str(self.agency.founded), inline=True)
        embed.add_field(name="Влияние", value=f"{self.agency.influence}%", inline=True)
        embed.add_field(name="Коррупция", value=f"{self.agency.corruption}%", inline=True)
        
        embed.add_field(name="Финансирование", value=format_billion(self.agency.current_funding), inline=True)
        embed.add_field(name="Сотрудников", value=f"{self.agency.available_personnel:,}", inline=True)
        embed.add_field(name="Оснащение", value=f"{self.agency.equipment_level}%", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)


class OperationCategorySelect(Select):
    """Выбор категории операций"""
    
    def __init__(self, user_id, country_name, available_categories):
        self.user_id = user_id
        self.country_name = country_name
        
        options = []
        for cat_id in available_categories[:25]:
            cat_name = OPERATION_CATEGORIES[cat_id]
            # Считаем количество операций в категории
            count = len([op for op in ESPIONAGE_OPERATIONS.values() if op["category"] == cat_id])
            options.append(
                discord.SelectOption(
                    label=cat_name,
                    description=f"{count} операций",
                    value=cat_id
                )
            )
        
        super().__init__(
            placeholder="Выберите категорию операций...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        category = self.values[0]
        
        # Фильтруем операции по категории
        operations = {op_id: op for op_id, op in ESPIONAGE_OPERATIONS.items() 
                     if op["category"] == category}
        
        embed = discord.Embed(
            title=OPERATION_CATEGORIES[category],
            description="Выберите конкретную операцию:",
            color=DARK_THEME_COLOR
        )
        
        select = OperationSelect(self.user_id, self.country_name, operations)
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад к категориям", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_categories
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_categories(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_espionage_menu(interaction, self.user_id)


class OperationSelect(Select):
    """Выбор конкретной операции"""
    
    def __init__(self, user_id, country_name, operations):
        self.user_id = user_id
        self.country_name = country_name
        self.operations = operations
        
        options = []
        for op_id, op in list(operations.items())[:25]:
            options.append(
                discord.SelectOption(
                    label=op["name"],
                    description=op["description"][:50],
                    value=op_id
                )
            )
        
        super().__init__(
            placeholder="Выберите операцию...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        op_id = self.values[0]
        operation = self.operations[op_id]
        
        # Проверяем возможность проведения операции
        from bot import load_states
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("❌ Ошибка загрузки данных!", ephemeral=True)
            return
        
        current_pp = get_political_power(player_data)
        
        can_afford = current_pp >= operation["pp_cost"]
        can_afford_money = player_data["economy"]["budget"] >= operation["base_cost"]
        
        embed = discord.Embed(
            title=operation["name"],
            description=operation["description"],
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Стоимость", value=format_billion(operation['base_cost']), inline=True)
        embed.add_field(name="Полит. власть", value=str(operation["pp_cost"]), inline=True)
        embed.add_field(name="Длительность", value=f"{operation['duration_hours']} ч", inline=True)
        embed.add_field(name="Требуется сотрудников", value=str(operation["personnel_required"]), inline=True)
        embed.add_field(name="Базовый риск", value=f"{operation['base_risk']}%", inline=True)
        embed.add_field(name="Риск обнаружения", value=f"{operation['base_detection']}%", inline=True)
        
        # Эффект
        effect_text = format_effect(operation["effect"])
        embed.add_field(name="Эффект", value=effect_text, inline=False)
        
        # Статус доступности
        status = ""
        if not can_afford:
            status += f"❌ Недостаточно ПВ (нужно {operation['pp_cost']})\n"
        if not can_afford_money:
            status += f"❌ Недостаточно средств (нужно {format_billion(operation['base_cost'])})\n"
        
        if status:
            embed.add_field(name="Доступность", value=status, inline=False)
        
        view = OperationConfirmationView(
            self.user_id, self.country_name, op_id, operation, 
            can_afford and can_afford_money
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class OperationConfirmationView(View):
    """Подтверждение запуска операции"""
    
    def __init__(self, user_id, country_name, operation_id, operation, can_afford):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.country_name = country_name
        self.operation_id = operation_id
        self.operation = operation
        self.can_afford = can_afford
    
    @discord.ui.button(label="Запустить операцию", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        if not self.can_afford:
            await interaction.response.send_message("❌ Операция недоступна!", ephemeral=True)
            return
        
        # Здесь будет логика запуска операции
        await interaction.response.send_message("✅ Операция запущена! (в разработке)", ephemeral=True)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_espionage_menu(interaction, self.user_id)


def format_effect(effect):
    """Форматирует описание эффекта"""
    if effect["type"] == "intel_bonus":
        return f"+{effect['value']}% к успеху следующей операции на {effect['duration_days']} дней"
    elif effect["type"] == "production_penalty":
        return f"-{effect['value']}% производства на {effect['duration_days']} дней"
    elif effect["type"] == "power_penalty":
        return f"-{effect['value']}% энергии на {effect['duration_days']} дней"
    elif effect["type"] == "logistics_penalty":
        return f"-{effect['value']}% эффективности логистики на {effect['duration_days']} дней"
    elif effect["type"] == "gov_penalty":
        return f"-{effect['value']}% эффективности правительства на {effect['duration_days']} дней"
    elif effect["type"] == "trust_penalty":
        return f"-{effect['value']}% доверия на {effect['duration_days']} дней"
    elif effect["type"] == "stability_penalty":
        return f"-{effect['value']}% стабильности на {effect['duration_days']} дней"
    elif effect["type"] == "popularity_penalty":
        return f"-{effect['value']}% популярности на {effect['duration_days']} дней"
    elif effect["type"] == "corruption_boost":
        return f"+{effect['value']}% коррупции на {effect['duration_days']} дней"
    elif effect["type"] == "security_boost":
        return f"+{effect['value']}% к защите от разведки на {effect['duration_days']} дней"
    elif effect["type"] == "enemy_penalty":
        return f"-{effect['value']}% к успеху вражеских операций на {effect['duration_days']} дней"
    elif effect["type"] == "agent_safety":
        return f"+{effect['value']}% к выживаемости агентов на {effect['duration_days']} дней"
    elif effect["type"] == "research_boost":
        return f"+{effect['value']}% скорости исследований на {effect['duration_days']} дней"
    elif effect["type"] == "economic_penalty":
        return f"-{effect['value']}% ВВП на {effect['duration_days']} дней"
    elif effect["type"] == "budget_penalty":
        return f"-{effect['value']}% бюджета на {effect['duration_days']} дней"
    elif effect["type"] == "budget_damage":
        return f"-{effect['value']}% бюджета (разово)"
    elif effect["type"] == "personality_eliminated":
        return f"Устранение цели\n-{effect['secondary_effects']['stability_hit']}% стабильности\n-{effect['secondary_effects']['military_penalty']}% боеспособности на 7 дней"
    elif effect["type"] == "agent_rescued":
        return f"Возврат {effect['personnel_return']} сотрудников"
    elif effect["type"] == "relations_hit":
        return f"-{effect['value']}% к отношениям между странами на {effect['duration_days']} дней"
    else:
        return str(effect)


# ==================== ОСНОВНОЕ МЕНЮ ====================

async def show_espionage_menu(interaction_or_ctx, user_id: int):
    """Показать меню специальных операций"""
    
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
            await interaction_or_ctx.response.send_message("❌ У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("❌ У вас нет государства!")
        return
    
    # Получаем агентства страны
    agencies = get_agencies_status(country_name, player_data)
    
    embed = discord.Embed(
        title=f"🕵️ Специальные операции: {country_name}",
        description="Ваши разведывательные агентства:",
        color=DARK_THEME_COLOR
    )
    
    # Статистика по агентствам
    if agencies:
        for agency in agencies:
            # Определяем цветовой индикатор
            if agency.corruption < 20:
                status = "🟢"
            elif agency.corruption < 40:
                status = "🟡"
            else:
                status = "🔴"
            
            agency_info = f"{status} **{agency.name}**\n"
            agency_info += f"├ Влияние: {agency.influence}% | Коррупция: {agency.corruption}%\n"
            agency_info += f"├ Сотрудников: {agency.available_personnel:,}\n"
            agency_info += f"├ Оснащение: {agency.equipment_level}%\n"
            agency_info += f"└ Финансирование: {format_billion(agency.current_funding)}"
            
            embed.add_field(name="", value=agency_info, inline=False)
    else:
        embed.add_field(name="", value="❌ В вашей стране нет разведывательных агентств", inline=False)
    
    # Общая статистика
    current_pp = get_political_power(player_data)
    embed.add_field(name="⚡ Политическая власть", value=f"{current_pp:.1f}", inline=True)
    embed.add_field(name="💰 Бюджет", value=format_billion(player_data["economy"]["budget"]), inline=True)
    
    # Отправляем меню
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
        message = await interaction_or_ctx.original_response()
    else:
        message = await interaction_or_ctx.send(embed=embed, ephemeral=True)
    
    # Если есть агентства, показываем выбор
    if agencies:
        select = AgencySelect(user_id, country_name, agencies)
        view = View(timeout=120)
        view.add_item(select)
        await message.edit(view=view)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_espionage_menu',
    'ESPIONAGE_OPERATIONS',
    'OPERATION_CATEGORIES'
]

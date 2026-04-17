# political_power.py - Полная версия со всеми механиками
# ВЕРСИЯ 18.0: Реалистичные международные операции

import discord
from discord.ui import Select, View, Button
import json
import random
import asyncio
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

# ==================== КОНСТАНТЫ ====================

STATES_FILE = 'states.json'
PARTIES_FILE = 'pol_party.json'
ELECTIONS_FILE = 'elections_history.json'
POLITICAL_ACTIONS_FILE = 'political_actions.json'
FACTIONS_FILE = 'factions.json'
INTEREST_GROUPS_FILE = 'interest_groups.json'
FOREIGN_INFLUENCE_FILE = 'foreign_influence.json'
INTELLIGENCE_FILE = 'intelligence.json'

DARK_THEME_COLOR = 0x2b2d31

MAX_INFLUENCE = 1000
DAYS_PER_GAME_YEAR = 3
POLITICAL_POWER_INTERVAL_HOURS = 4

# Кулдауны
COOLDOWNS = {
    "agitation_left": 12, "agitation_center": 12, "agitation_right": 12,
    "propaganda_left": 8, "propaganda_center": 8, "propaganda_right": 8,
    "dissolve_party": 72, "change_party": 168, "declare_elections": 0,
    "recruit": 24, "arson": 12, "sabotage": 24, "terror_act": 48, "separatist_protests": 8,
    "opposition_agitation": 12, "opposition_protests": 24,
    "strengthen_faction": 168, "weaken_faction": 168,
    # Международные операции
    "psyops": 72, "media_campaign": 48, "cyber_attack": 120, "economic_sabotage": 96,
    "spy_network": 168, "agent_infiltration": 240, "assassination": 336, "coup_support": 720,
    "disinformation": 48, "hack_leak": 96, "ransomware": 72, "infrastructure_sabotage": 168,
    "oligarch_support": 120, "sanctions_evasion": 96, "currency_attack": 144,
    "separatist_support": 168, "color_revolution": 360, "propaganda_broadcast": 48
}

# Сроки выборов
ELECTION_TERMS = {
    "США": 4, "Россия": 6, "Китай": 5, "Германия": 4,
    "Великобритания": 5, "Франция": 5, "Япония": 4, "Израиль": 4,
    "Украина": 5, "Иран": 4, "Турция": 5, "Канада": 4,
    "Польша": 4, "Бразилия": 4, "Швеция": 4, "Финляндия": 4,
    "Швейцария": 4, "Египет": 4, "Норвегия": 4,
    "КНДР": None, "Сирия": None, "Беларусь": None
}

# Эмодзи
EMOJIS = {
    "job_spec": "<:Job_spec:1267712580999184486>",
    "government": "<:government:1487167580350451804>",
    "social": "<:social:1487167248908156988>",
    "pp": "<:pp:1487015341883130027>",
    "partia": "<:partia:1487365868676448327>",
    "zakon": "<:zakon:1487365783385411626>",
    "vvp": "<:vvp:1487360602367070400>",
    "army": "<:army:1487330495082528829>",
    "crisis": "<:crisis:1487167453443391509>"
}

# Перевод позиций
POSITION_TRANSLATIONS = {
    "left": "Левые", "center-left": "Центр-левые", "center": "Центристы",
    "center-right": "Центр-правые", "right": "Правые", "right-wing": "Ультраправые",
    "left-wing": "Ультралевые", "far-left": "Ультралевые", "far-right": "Ультраправые",
    "right-libertarian": "Правые либертарианцы", "left-libertarian": "Левые либертарианцы",
    "authoritarian": "Авторитарные", "libertarian": "Либертарианцы", "unknown": "Не указана"
}

# Уровни популярности
POPULARITY_TIERS = {
    "КРИТИЧЕСКИЙ": {"min": 0, "max": 20, "effects": {"pp_gain_mod": -0.5, "stability_loss": -1, "coup_risk": 20}, "color": 0x8B0000},
    "НЕСТАБИЛЬНЫЙ": {"min": 20, "max": 40, "effects": {"pp_gain_mod": -0.2, "protest_chance": 10}, "color": 0xFF6600},
    "СТАБИЛЬНЫЙ": {"min": 40, "max": 60, "effects": {"pp_gain_mod": 0}, "color": 0xFFFF00},
    "ПОПУЛЯРНЫЙ": {"min": 60, "max": 80, "effects": {"pp_gain_mod": 0.2, "election_bonus": 5}, "color": 0x00AA00},
    "НАРОДНЫЙ": {"min": 80, "max": 101, "effects": {"pp_gain_mod": 0.5, "oppression_chance": 15}, "color": 0x00FF00}
}

# ==================== МЕЖДУНАРОДНЫЕ ОПЕРАЦИИ (РЕАЛИСТИЧНЫЕ) ====================

INTELLIGENCE_OPERATIONS = {
    # === ПСИХОЛОГИЧЕСКИЕ ОПЕРАЦИИ ===
    "psyops": {
        "name": "Психологическая операция",
        "description": "Целенаправленное воздействие на общественное мнение через социальные сети, ботов и фейковые аккаунты",
        "cost_pp": 80,
        "cost_influence": 50,
        "success_chance": 0.55,
        "effects": {"target_stability": -5, "target_popularity": -3, "protest_chance": +15},
        "risk": 0.3,
        "risk_effects": {"exposure": -10, "relation": -15},
        "duration_days": 14
    },
    "disinformation": {
        "name": "Кампания дезинформации",
        "description": "Распространение фейковых новостей и компрометирующих материалов через подконтрольные СМИ",
        "cost_pp": 60,
        "cost_influence": 40,
        "success_chance": 0.65,
        "effects": {"target_trust": -8, "target_popularity": -4},
        "risk": 0.25,
        "risk_effects": {"credibility": -10},
        "duration_days": 21
    },
    "media_campaign": {
        "name": "Медиа-кампания",
        "description": "Размещение пропагандистских материалов в ведущих СМИ целевой страны",
        "cost_pp": 50,
        "cost_influence": 30,
        "success_chance": 0.7,
        "effects": {"target_influence": -5, "own_influence": +8},
        "risk": 0.2,
        "risk_effects": {"propaganda_exposed": -5},
        "duration_days": 30
    },
    "propaganda_broadcast": {
        "name": "Зарубежное вещание",
        "description": "Организация радио- и телевещания на территории противника (аналог Radio Liberty, BBC Persian)",
        "cost_pp": 70,
        "cost_influence": 45,
        "success_chance": 0.6,
        "effects": {"target_soft_power": -6, "own_soft_power": +5, "audience_reach": +15},
        "risk": 0.15,
        "risk_effects": {"jamming": -5},
        "duration_days": 45
    },
    
    # === КИБЕР-ОПЕРАЦИИ ===
    "cyber_attack": {
        "name": "Кибератака",
        "description": "Взлом государственных серверов, утечка секретных данных, дефейс сайтов",
        "cost_pp": 120,
        "cost_influence": 80,
        "success_chance": 0.45,
        "effects": {"target_stability": -8, "target_intelligence": -15, "data_leak": True},
        "risk": 0.5,
        "risk_effects": {"retaliation": -20, "trace_back": -15},
        "duration_days": 7
    },
    "hack_leak": {
        "name": "Хакерская утечка",
        "description": "Взлом и публикация компрометирующих документов (аналог WikiLeaks, Panama Papers)",
        "cost_pp": 100,
        "cost_influence": 60,
        "success_chance": 0.5,
        "effects": {"target_popularity": -12, "target_trust": -15, "political_crisis": True},
        "risk": 0.4,
        "risk_effects": {"international_scandal": -25},
        "duration_days": 14
    },
    "ransomware": {
        "name": "Ransomware-атака",
        "description": "Блокировка критической инфраструктуры с требованием выкупа (аналог Colonial Pipeline, WannaCry)",
        "cost_pp": 90,
        "cost_influence": 55,
        "success_chance": 0.4,
        "effects": {"target_economy": -10, "target_stability": -6, "infrastructure_damage": True},
        "risk": 0.6,
        "risk_effects": {"counter_attack": -20, "attribution": -15},
        "duration_days": 10
    },
    "infrastructure_sabotage": {
        "name": "Кибер-диверсия",
        "description": "Взлом систем управления энергосетями, транспортом, водоснабжением (аналог Stuxnet)",
        "cost_pp": 150,
        "cost_influence": 100,
        "success_chance": 0.35,
        "effects": {"target_stability": -15, "target_economy": -15, "critical_damage": True},
        "risk": 0.7,
        "risk_effects": {"escalation": -30, "military_response": -25},
        "duration_days": 5
    },
    
    # === ЭКОНОМИЧЕСКИЕ ОПЕРАЦИИ ===
    "economic_sabotage": {
        "name": "Экономический саботаж",
        "description": "Подрыв ключевых отраслей, саботаж на предприятиях, промышленный шпионаж",
        "cost_pp": 100,
        "cost_influence": 70,
        "success_chance": 0.5,
        "effects": {"target_economy": -8, "target_production": -10},
        "risk": 0.35,
        "risk_effects": {"counter_intel": -10},
        "duration_days": 30
    },
    "currency_attack": {
        "name": "Валютная атака",
        "description": "Спекулятивные операции против национальной валюты, обвал курса (аналог операций Soros)",
        "cost_pp": 200,
        "cost_influence": 150,
        "success_chance": 0.4,
        "effects": {"target_currency": -20, "target_inflation": +15, "capital_flight": True},
        "risk": 0.45,
        "risk_effects": {"market_backfire": -15, "international_condemnation": -10},
        "duration_days": 21
    },
    "sanctions_evasion": {
        "name": "Обход санкций",
        "description": "Организация серых схем для поставок критически важных технологий",
        "cost_pp": 80,
        "cost_influence": 60,
        "success_chance": 0.6,
        "effects": {"target_sanctions": -15, "own_economy": +5},
        "risk": 0.5,
        "risk_effects": {"sanctions_extended": -20},
        "duration_days": 60
    },
    "oligarch_support": {
        "name": "Поддержка олигархов",
        "description": "Финансирование и поддержка лояльных бизнес-структур в целевой стране",
        "cost_pp": 120,
        "cost_influence": 90,
        "success_chance": 0.55,
        "effects": {"target_elite_influence": +10, "own_influence": +12},
        "risk": 0.3,
        "risk_effects": {"exposure": -15},
        "duration_days": 90
    },
    
    # === ШПИОНСКИЕ ОПЕРАЦИИ ===
    "spy_network": {
        "name": "Создание агентурной сети",
        "description": "Вербовка агентов влияния в правительстве, спецслужбах, бизнесе",
        "cost_pp": 150,
        "cost_influence": 100,
        "success_chance": 0.4,
        "effects": {"target_intelligence": -15, "own_intelligence": +20, "agent_network": True},
        "risk": 0.55,
        "risk_effects": {"network_exposed": -25, "diplomatic_expulsion": -20},
        "duration_days": 180
    },
    "agent_infiltration": {
        "name": "Внедрение агента",
        "description": "Засылка глубоко законспирированного агента в структуры власти",
        "cost_pp": 200,
        "cost_influence": 120,
        "success_chance": 0.3,
        "effects": {"target_secrets": +25, "own_intelligence": +15, "deep_cover": True},
        "risk": 0.65,
        "risk_effects": {"agent_executed": -40, "diplomatic_crisis": -30},
        "duration_days": 365
    },
    "assassination": {
        "name": "Политическое устранение",
        "description": "Ликвидация неугодного политика, активиста, журналиста (высокий риск)",
        "cost_pp": 300,
        "cost_influence": 200,
        "success_chance": 0.25,
        "effects": {"target_opposition": -20, "target_stability": -10, "leadership_crisis": True},
        "risk": 0.8,
        "risk_effects": {"war": -50, "international_pariah": -40, "retaliation": -35},
        "duration_days": 30
    },
    
    # === ПОЛИТИЧЕСКИЕ ОПЕРАЦИИ ===
    "separatist_support": {
        "name": "Поддержка сепаратистов",
        "description": "Финансирование и вооружение сепаратистских движений (аналог поддержки курдов, тамилов)",
        "cost_pp": 180,
        "cost_influence": 120,
        "success_chance": 0.45,
        "effects": {"target_territorial_integrity": -15, "target_stability": -12, "insurgency": True},
        "risk": 0.6,
        "risk_effects": {"backfire": -25, "terrorism_export": -20},
        "duration_days": 360
    },
    "color_revolution": {
        "name": "Подготовка цветной революции",
        "description": "Организация протестных движений, финансирование НПО, обучение активистов",
        "cost_pp": 250,
        "cost_influence": 180,
        "success_chance": 0.35,
        "effects": {"target_stability": -20, "target_popularity": -15, "regime_change_risk": +25},
        "risk": 0.7,
        "risk_effects": {"backlash": -30, "authoritarian_crackdown": -20},
        "duration_days": 180
    },
    "coup_support": {
        "name": "Поддержка военного переворота",
        "description": "Финансирование и координация заговора среди военной элиты",
        "cost_pp": 400,
        "cost_influence": 250,
        "success_chance": 0.2,
        "effects": {"target_regime_change": True, "target_stability": -25},
        "risk": 0.85,
        "risk_effects": {"coup_failure": -50, "war": -40, "global_condemnation": -35},
        "duration_days": 180
    }
}

# ==================== БАЗОВЫЕ ФУНКЦИИ ====================

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

def load_parties_from_json() -> Dict[str, List[Dict]]:
    try:
        with open(PARTIES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_country_parties(country_name: str) -> List[Dict]:
    parties_db = load_parties_from_json()
    return parties_db.get(country_name, [])

def load_political_actions() -> Dict:
    try:
        with open(POLITICAL_ACTIONS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"actions": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"actions": {}}

def save_political_actions(data):
    with open(POLITICAL_ACTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def check_action_cooldown(state_id: str, action_type: str) -> Tuple[bool, Optional[datetime]]:
    actions_data = load_political_actions()
    if state_id not in actions_data["actions"]:
        return True, None
    if action_type not in actions_data["actions"][state_id]:
        return True, None
    last_used = datetime.fromisoformat(actions_data["actions"][state_id][action_type])
    cooldown_hours = COOLDOWNS.get(action_type, 24)
    next_available = last_used + timedelta(hours=cooldown_hours)
    if datetime.now() >= next_available:
        return True, None
    return False, next_available

def set_action_cooldown(state_id: str, action_type: str):
    actions_data = load_political_actions()
    if state_id not in actions_data["actions"]:
        actions_data["actions"][state_id] = {}
    actions_data["actions"][state_id][action_type] = str(datetime.now())
    save_political_actions(actions_data)

def get_player_state(user_id):
    states = load_states()
    for state_id, data in states["players"].items():
        if data.get("assigned_to") == str(user_id):
            return state_id, data
    return None, None

def get_state_name_by_id(state_id: str) -> str:
    states = load_states()
    if state_id in states["players"]:
        return states["players"][state_id]["state"]["statename"]
    return state_id

def get_political_power(state_data):
    return state_data.get("politics", {}).get("political_power", 100)

def set_political_power(state_data, value):
    if "politics" not in state_data:
        state_data["politics"] = {}
    state_data["politics"]["political_power"] = max(0, value)
    return state_data

def add_political_power(state_data, amount):
    current = get_political_power(state_data)
    new_value = max(0, current + amount)
    set_political_power(state_data, new_value)
    return state_data, new_value - current

def spend_political_power(state_data, amount):
    current = get_political_power(state_data)
    if current >= amount:
        set_political_power(state_data, current - amount)
        return True, current - amount
    return False, current

def get_influence(state_data) -> float:
    return round(min(MAX_INFLUENCE, state_data.get("politics", {}).get("influence", 0)), 1)

def add_influence(state_data, amount: float) -> float:
    if "politics" not in state_data:
        state_data["politics"] = {}
    current = state_data["politics"].get("influence", 0)
    new_value = min(MAX_INFLUENCE, current + amount)
    state_data["politics"]["influence"] = round(new_value, 1)
    return round(new_value, 1)

def spend_influence(state_data, amount: int) -> bool:
    if "politics" not in state_data:
        state_data["politics"] = {}
    current = state_data["politics"].get("influence", 0)
    if current >= amount:
        state_data["politics"]["influence"] = round(current - amount, 1)
        return True
    return False

def find_ruling_party(parties_data: List[Dict], ruling_party_name: str) -> Optional[Dict]:
    ruling_party_name_clean = ruling_party_name.strip().lower()
    for party in parties_data:
        party_name = party.get('name_ru', party.get('name', '')).strip().lower()
        if party_name == ruling_party_name_clean:
            return party
        party_name_alt = party.get('name', '').strip().lower()
        if party_name_alt == ruling_party_name_clean:
            return party
        if ruling_party_name_clean in party_name or party_name in ruling_party_name_clean:
            return party
    return None

def get_party_by_id(parties_data: List[Dict], party_id: str) -> Optional[Dict]:
    for party in parties_data:
        if party.get('id') == party_id:
            return party
    return None

def save_player_state(user_id: int, state_data: Dict):
    states = load_states()
    for sid, sdata in states["players"].items():
        if sdata.get("assigned_to") == str(user_id):
            sdata.update(state_data)
            break
    save_states(states)

def sync_party_popularity(state_data: Dict) -> Dict:
    state_name = get_state_name_by_id(state_data.get("assigned_to", ""))
    ruling_party_name = state_data.get("politics", {}).get("ruling_party", "")
    if not ruling_party_name or not state_name:
        return state_data
    parties = load_country_parties(state_name)
    for party in parties:
        if party.get('name_ru', party.get('name')) == ruling_party_name:
            party_popularity = party.get('popularity', 50.0)
            if "politics" not in state_data:
                state_data["politics"] = {}
            state_data["politics"]["popularity"] = party_popularity
            break
    return state_data

def calculate_political_power_gain(state_data: Dict) -> float:
    base = 10
    influence = get_influence(state_data)
    influence_bonus = influence // 100
    parliament = Parliament(state_data.get("assigned_to", ""), state_data)
    parliamentary_bonus = parliament.get_parliamentary_bonus()
    stability = state_data.get("stability", 50)
    stability_mod = (stability - 50) / 200
    
    popularity = state_data.get("politics", {}).get("popularity", 50)
    tier = get_popularity_tier(popularity)
    pp_gain_mod = tier["effects"].get("pp_gain_mod", 0)
    
    total = base + influence_bonus + parliamentary_bonus
    total = total * (1 + stability_mod + pp_gain_mod)
    total = max(5, min(30, total))
    return round(total, 1)

def get_party_ideology_group(position: str) -> str:
    position_lower = position.lower()
    if any(x in position_lower for x in ['left', 'коммунизм', 'социализм', 'левые']):
        return "left"
    elif any(x in position_lower for x in ['right', 'консерватизм', 'национализм', 'правые']):
        return "right"
    else:
        return "center"

def translate_position(position: str) -> str:
    if not position:
        return "Не указана"
    return POSITION_TRANSLATIONS.get(position.lower(), position)

def get_regime_by_ideology(ideology: str) -> str:
    ideology_lower = ideology.lower()
    if any(x in ideology_lower for x in ['коммунизм', 'коммунистический']):
        return "Коммунистический режим"
    elif any(x in ideology_lower for x in ['социализм', 'социалистический']):
        return "Социалистический режим"
    elif any(x in ideology_lower for x in ['либерализм', 'либеральный']):
        return "Либерально-демократический режим"
    elif any(x in ideology_lower for x in ['консерватизм', 'консервативный']):
        return "Консервативно-демократический режим"
    elif any(x in ideology_lower for x in ['авторитарный', 'авторитаризм']):
        return "Авторитарный режим"
    elif any(x in ideology_lower for x in ['национализм', 'националистический']):
        return "Националистический режим"
    elif any(x in ideology_lower for x in ['демократия', 'демократический']):
        return "Демократический режим"
    else:
        return "Смешанный режим"

def get_popularity_tier(popularity: float) -> Dict:
    for tier_name, tier_data in POPULARITY_TIERS.items():
        if tier_data["min"] <= popularity <= tier_data["max"]:
            return {"name": tier_name, **tier_data}
    return {"name": "СТАБИЛЬНЫЙ", **POPULARITY_TIERS["СТАБИЛЬНЫЙ"]}

# ==================== ФУНКЦИИ ДЛЯ ФРАКЦИЙ ====================

def load_factions(state_id: str) -> Dict:
    try:
        with open(f"factions_{state_id}.json", 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_factions(state_id: str, data: Dict):
    with open(f"factions_{state_id}.json", 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def init_factions(state_id: str, state_data: Dict):
    factions = load_factions(state_id)
    if factions:
        return
    
    ruling_party = state_data.get("politics", {}).get("ruling_party", "")
    ideology = state_data.get("politics", {}).get("ideology", "").lower()
    
    default_factions = {
        "radical_left": {"name": "Радикальные левые", "influence": 10, "loyalty": 50, "membership": 1000},
        "moderate_left": {"name": "Умеренные левые", "influence": 20, "loyalty": 60, "membership": 2000},
        "center": {"name": "Центристы", "influence": 30, "loyalty": 70, "membership": 3000},
        "moderate_right": {"name": "Умеренные правые", "influence": 25, "loyalty": 65, "membership": 2500},
        "radical_right": {"name": "Радикальные правые", "influence": 15, "loyalty": 55, "membership": 1500}
    }
    
    if "коммунизм" in ideology or "социализм" in ideology:
        default_factions["radical_left"]["influence"] += 15
        default_factions["moderate_left"]["influence"] += 10
        default_factions["center"]["influence"] -= 10
        default_factions["moderate_right"]["influence"] -= 10
        default_factions["radical_right"]["influence"] -= 5
    elif "либерализм" in ideology:
        default_factions["center"]["influence"] += 15
        default_factions["moderate_left"]["influence"] += 5
        default_factions["moderate_right"]["influence"] += 5
    elif "консерватизм" in ideology or "национализм" in ideology:
        default_factions["radical_right"]["influence"] += 15
        default_factions["moderate_right"]["influence"] += 10
        default_factions["center"]["influence"] -= 10
        default_factions["radical_left"]["influence"] -= 5
    
    total = sum(f["influence"] for f in default_factions.values())
    for f in default_factions.values():
        f["influence"] = round((f["influence"] / total) * 100, 1)
    
    save_factions(state_id, default_factions)

def get_ruling_faction(state_id: str) -> Optional[Tuple[str, Dict]]:
    factions = load_factions(state_id)
    if not factions:
        return None
    return max(factions.items(), key=lambda x: x[1].get("influence", 0))

def update_faction_influence(state_id: str, faction_id: str, delta: float):
    factions = load_factions(state_id)
    if faction_id not in factions:
        return
    
    factions[faction_id]["influence"] = max(0, min(100, factions[faction_id].get("influence", 0) + delta))
    
    total = sum(f.get("influence", 0) for f in factions.values())
    if total > 0 and total != 100:
        for f in factions.values():
            f["influence"] = round((f["influence"] / total) * 100, 1)
    
    save_factions(state_id, factions)

# ==================== КЛАСС ПАРЛАМЕНТА ====================

class Parliament:
    def __init__(self, state_id: str, state_data: Dict):
        self.state_id = state_id
        self.state_data = state_data
        if "parliament" not in state_data:
            state_data["parliament"] = {
                "seats": 450,
                "distribution": {},
                "last_election": None,
                "next_election": None
            }
        self.parliament_data = state_data["parliament"]
        self.seats = self.parliament_data.get("seats", 450)
        self.distribution = self.parliament_data.get("distribution", {})

    def get_distribution(self) -> Dict[str, int]:
        return self.distribution

    def get_distribution_seats(self) -> Dict[str, int]:
        return self.distribution

    def get_distribution_percent(self) -> Dict[str, float]:
        total = sum(self.distribution.values())
        if total == 0:
            return {}
        return {pid: (seats / total) * 100 for pid, seats in self.distribution.items()}

    def get_ruling_party(self) -> Optional[str]:
        if not self.distribution:
            return None
        sorted_parties = sorted(self.distribution.items(), key=lambda x: x[1], reverse=True)
        return sorted_parties[0][0] if sorted_parties else None

    def get_party_seats(self, party_id: str) -> int:
        return self.distribution.get(party_id, 0)

    def get_parliamentary_bonus(self) -> int:
        ruling_party_id = self.get_ruling_party()
        if not ruling_party_id:
            return 0
        party_seats = self.distribution.get(ruling_party_id, 0)
        seat_share = party_seats / self.seats if self.seats > 0 else 0
        return int(seat_share * 10)

    def update_distribution(self, new_distribution: Dict[str, int]):
        total = sum(new_distribution.values())
        if total > self.seats:
            factor = self.seats / total
            new_distribution = {pid: int(count * factor) for pid, count in new_distribution.items()}
            remaining = self.seats - sum(new_distribution.values())
            if remaining > 0 and new_distribution:
                largest_party = max(new_distribution.items(), key=lambda x: x[1])[0]
                new_distribution[largest_party] += remaining
        self.distribution = new_distribution
        self.parliament_data["distribution"] = new_distribution
        self.save()

    def remove_party(self, party_id: str) -> bool:
        if party_id not in self.distribution:
            return False
        removed_seats = self.distribution.pop(party_id)
        if not self.distribution:
            return True
        remaining_parties = list(self.distribution.keys())
        total_remaining = sum(self.distribution.values())
        for pid in remaining_parties:
            share = self.distribution[pid] / total_remaining if total_remaining > 0 else 0
            self.distribution[pid] += int(removed_seats * share)
        allocated = sum(self.distribution.values())
        remaining = self.seats - allocated
        if remaining > 0 and self.distribution:
            largest_party = max(self.distribution.items(), key=lambda x: x[1])[0]
            self.distribution[largest_party] += remaining
        self.parliament_data["distribution"] = self.distribution
        self.save()
        return True

    def call_election(self, results: Dict[str, int]):
        self.update_distribution(results)
        self.parliament_data["last_election"] = str(datetime.now())
        country_name = get_state_name_by_id(self.state_id)
        term_years = ELECTION_TERMS.get(country_name, 4)
        if term_years:
            next_election_date = datetime.now() + timedelta(days=term_years * DAYS_PER_GAME_YEAR)
            self.parliament_data["next_election"] = str(next_election_date)
        self.save()

    def save(self):
        self.state_data["parliament"] = self.parliament_data
        save_player_state(int(self.state_data.get("assigned_to", 0)), self.state_data)

    def needs_election(self) -> bool:
        country_name = get_state_name_by_id(self.state_id)
        term_years = ELECTION_TERMS.get(country_name, 4)
        if term_years is None:
            return False
        next_election = self.parliament_data.get("next_election")
        if not next_election:
            return True
        next_election_date = datetime.fromisoformat(next_election)
        return datetime.now() >= next_election_date

    def can_declare_election(self) -> bool:
        country_name = get_state_name_by_id(self.state_id)
        term_years = ELECTION_TERMS.get(country_name, 4)
        if term_years is None:
            return False
        last_election = self.parliament_data.get("last_election")
        if not last_election:
            return True
        last_election_date = datetime.fromisoformat(last_election)
        years_since = (datetime.now() - last_election_date).days / DAYS_PER_GAME_YEAR
        return years_since >= 1


# ==================== КЛАСС ВЫБОРОВ ====================

class Election:
    def __init__(self, state_id: str, state_data: Dict, parties: List[Dict]):
        self.state_id = state_id
        self.state_data = state_data
        self.parties = parties
        self.parliament = Parliament(state_id, state_data)

    async def run_election(self, ctx, is_auto: bool = True) -> Tuple[Dict[str, int], bool]:
        stability = self.state_data.get("stability", 50)
        influence = get_influence(self.state_data)
        ruling_party_name = self.state_data.get("politics", {}).get("ruling_party", "")
        popularity = self.state_data.get("politics", {}).get("popularity", 50)
        tier = get_popularity_tier(popularity)
        election_bonus = tier["effects"].get("election_bonus", 0)

        stability_mod = (stability - 50) / 100
        influence_mod = influence / 2000
        popularity_mod = election_bonus / 100

        results = {}
        total = 0
        player_party_result = 0
        player_party_id = None

        for party in self.parties:
            base_popularity = party.get('popularity', 5.0)
            if party.get('name_ru', party.get('name')) == ruling_party_name:
                incumbency_bonus = 1.1 + popularity_mod
                player_party_id = party['id']
            else:
                incumbency_bonus = 0.95
            final_percent = base_popularity * incumbency_bonus * (1 + stability_mod + influence_mod)
            final_percent = max(0.1, min(60, final_percent))
            results[party['id']] = final_percent
            total += final_percent
            if party.get('name_ru', party.get('name')) == ruling_party_name:
                player_party_result = final_percent

        if total > 0:
            for party_id in results:
                results[party_id] = (results[party_id] / total) * 100
            player_party_result = (player_party_result / total) * 100

        votes = {pid: max(1, int(percent * 100)) for pid, percent in results.items()}
        seats_distribution = self._calculate_seats(votes)
        self.parliament.call_election(seats_distribution)

        ruling_party_id = self.parliament.get_ruling_party()
        player_still_ruling = (ruling_party_id == player_party_id)

        await self._send_results(ctx, results, seats_distribution, player_still_ruling)
        return seats_distribution, player_still_ruling

    def _calculate_seats(self, votes: Dict[str, int]) -> Dict[str, int]:
        total_votes = sum(votes.values())
        if total_votes == 0:
            return {}
        seats = {}
        for party_id, vote_count in votes.items():
            seats[party_id] = int((vote_count / total_votes) * self.parliament.seats)
        allocated = sum(seats.values())
        remaining = self.parliament.seats - allocated
        if remaining > 0:
            fractions = {}
            for party_id, vote_count in votes.items():
                exact = (vote_count / total_votes) * self.parliament.seats
                fraction = exact - int(exact)
                fractions[party_id] = fraction
            for party_id in sorted(fractions.keys(), key=lambda x: fractions[x], reverse=True)[:remaining]:
                seats[party_id] = seats.get(party_id, 0) + 1
        return seats

    async def _send_results(self, ctx, results: Dict[str, float], seats: Dict[str, int], player_won: bool):
        sorted_parties = sorted(seats.items(), key=lambda x: x[1], reverse=True)
        embed = discord.Embed(
            title=f"{EMOJIS['partia']} РЕЗУЛЬТАТЫ ВЫБОРОВ",
            description=f"**{get_state_name_by_id(self.state_id)}**",
            color=DARK_THEME_COLOR
        )
        results_text = ""
        for party_id, seat_count in sorted_parties:
            party = next((p for p in self.parties if p['id'] == party_id), None)
            if party:
                percent = results.get(party_id, 0)
                seat_percent = (seat_count / self.parliament.seats * 100) if self.parliament.seats > 0 else 0
                results_text += f"**{party.get('name_ru', party['name'])}**\n"
                results_text += f"├ Голосов: {percent:.1f}%\n"
                results_text += f"└ Мест: {seat_count} ({seat_percent:.1f}%)\n\n"
        embed.add_field(name=f"{EMOJIS['partia']} ИТОГИ", value=results_text[:1024], inline=False)

        ruling_party_id = self.parliament.get_ruling_party()
        if ruling_party_id:
            ruling_party = next((p for p in self.parties if p['id'] == ruling_party_id), None)
            if ruling_party:
                embed.add_field(
                    name=f"{EMOJIS['government']} ПРАВЯЩАЯ ПАРТИЯ",
                    value=f"**{ruling_party.get('name_ru', ruling_party['name'])}**\n"
                          f"{EMOJIS['job_spec']} Лидер: {ruling_party.get('leader', 'Неизвестен')}",
                    inline=False
                )
        if not player_won:
            embed.add_field(
                name="⚠️ ПОРАЖЕНИЕ",
                value="Ваша партия проиграла выборы. Вы больше не управляете государством!",
                inline=False
            )

        if ctx and hasattr(ctx, 'send'):
            await ctx.send(embed=embed)
        elif ctx and hasattr(ctx, 'followup'):
            await ctx.followup.send(embed=embed)
        elif ctx and hasattr(ctx, 'response'):
            await ctx.response.send_message(embed=embed)

        if not player_won:
            states = load_states()
            for state_id, state_data in states["players"].items():
                if state_data.get("assigned_to") == str(ctx.author.id) if hasattr(ctx, 'author') else False:
                    del state_data["assigned_to"]
                    if "assigned_at" in state_data:
                        del state_data["assigned_at"]
                    break
            save_states(states)


# ==================== ОСНОВНОЙ КЛАСС ====================

class PoliticalSystem:
    def __init__(self, bot):
        self.bot = bot

    async def political_panel(self, ctx, state_id: str, state_data: Dict):
        state_name = get_state_name_by_id(state_id)
        state_data = sync_party_popularity(state_data)
        
        init_factions(state_id, state_data)
        
        politics = state_data.get("politics", {})
        political_power = int(politics.get("political_power", 100))
        influence = get_influence(state_data)
        ruling_party_name = politics.get("ruling_party", "Нет правящей партии")
        ideology = politics.get("ideology", "Не указана")
        popularity = politics.get("popularity", 50)

        regime_type = get_regime_by_ideology(ideology)
        parties_data = load_country_parties(state_name)
        ruling_party_data = find_ruling_party(parties_data, ruling_party_name)
        if ruling_party_data:
            party_popularity = ruling_party_data.get('popularity', 50.0)
            if abs(popularity - party_popularity) > 0.1:
                state_data["politics"]["popularity"] = party_popularity
                popularity = party_popularity
                save_player_state(int(state_data.get("assigned_to", 0)), state_data)

        parliament = Parliament(state_id, state_data)
        next_election = parliament.parliament_data.get("next_election")
        term_years = ELECTION_TERMS.get(state_name, 4)
        if next_election:
            next_election_date = datetime.fromisoformat(next_election)
            days_until = (next_election_date - datetime.now()).days
            if days_until > 0:
                years_until = days_until // DAYS_PER_GAME_YEAR
                election_text = f"через {years_until} года"
            else:
                election_text = "Скоро!"
        else:
            election_text = "не назначены"
        if term_years is None:
            election_text = "выборы не проводятся"

        pp_gain = calculate_political_power_gain(state_data)
        tier = get_popularity_tier(popularity)
        
        ruling_faction = get_ruling_faction(state_id)
        faction_text = f"{ruling_faction[1]['name']} ({ruling_faction[1]['influence']:.1f}%)" if ruling_faction else "Нет данных"

        embed = discord.Embed(
            title=f"{EMOJIS['government']} ПОЛИТИЧЕСКАЯ СИСТЕМА • {state_name}",
            color=DARK_THEME_COLOR
        )
        if ruling_party_data and ruling_party_data.get('leader_img'):
            leader_img = ruling_party_data['leader_img']
            if leader_img and leader_img.startswith('http'):
                embed.set_image(url=leader_img)
        if ruling_party_data and ruling_party_data.get('icon_url'):
            icon_url = ruling_party_data['icon_url']
            if icon_url and icon_url.startswith('http'):
                embed.set_thumbnail(url=icon_url)

        embed.add_field(name=f"{EMOJIS['pp']} ПОЛИТИЧЕСКАЯ ВЛАСТЬ", value=f"```\n{political_power}\n```", inline=True)
        embed.add_field(name=f"{EMOJIS['social']} ВЛИЯНИЕ", value=f"```\n{influence:.1f} / {MAX_INFLUENCE}\n```", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} РЕЖИМ", value=f"```\n{regime_type}\n```", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} ПРАВЯЩАЯ ПАРТИЯ", value=f"```\n{ruling_party_name}\n```", inline=False)
        embed.add_field(name=f"{EMOJIS['vvp']} ПРАВЯЩАЯ ФРАКЦИЯ", value=f"```\n{faction_text}\n```", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} ПОПУЛЯРНОСТЬ", value=f"```\n{popularity:.1f}% [{tier['name']}]\n```", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} ПРИРОСТ", value=f"```\n+{pp_gain:.1f}/4ч\n```", inline=False)
        embed.add_field(name=f"{EMOJIS['job_spec']} ВЫБОРЫ", value=f"```\n{election_text}\n```", inline=False)

        view = PoliticalSelectView(state_id, state_data, self)
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message(embed=embed, view=view, ephemeral=False)
        else:
            await ctx.send(embed=embed, view=view)

    # ==================== ПРОСМОТР ====================

    async def show_parliament(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        state_name = get_state_name_by_id(state_id)
        parliament = Parliament(state_id, state_data)
        distribution = parliament.get_distribution_seats()
        distribution_percent = parliament.get_distribution_percent()
        parties_data = load_country_parties(state_name)

        if not distribution:
            await interaction.response.send_message(f"{EMOJIS['partia']} Парламент пуст. Проведите выборы!", ephemeral=True)
            return

        sorted_parties = sorted(distribution.items(), key=lambda x: x[1], reverse=True)
        options = []
        for party_id, seats in sorted_parties[:25]:
            party = next((p for p in parties_data if p['id'] == party_id), None)
            if party:
                party_name = party.get('name_ru', party.get('name', 'Неизвестная партия'))
                percent = distribution_percent.get(party_id, 0)
                popularity = party.get('popularity', 5.0)
                options.append(discord.SelectOption(label=party_name[:50], value=party_id, description=f"{seats} мест ({percent:.1f}%) | рейтинг: {popularity:.1f}%"))
        if not options:
            await interaction.response.send_message("Нет партий в парламенте!", ephemeral=True)
            return

        view = ParliamentSelectView(options, parties_data, distribution)
        embed = discord.Embed(title=f"{EMOJIS['partia']} ПАРЛАМЕНТ • {state_name}", description=f"Всего мест: **{parliament.seats}**\n\nВыберите партию:", color=DARK_THEME_COLOR)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def show_election_forecast(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        state_name = get_state_name_by_id(state_id)
        parties = load_country_parties(state_name)
        if not parties:
            await interaction.response.send_message(f"{EMOJIS['partia']} Нет партий для прогноза!", ephemeral=True)
            return

        stability = state_data.get("stability", 50)
        influence = get_influence(state_data)
        ruling_party_name = state_data.get("politics", {}).get("ruling_party", "")
        popularity = state_data.get("politics", {}).get("popularity", 50)
        tier = get_popularity_tier(popularity)
        election_bonus = tier["effects"].get("election_bonus", 0)

        stability_mod = (stability - 50) / 100
        influence_mod = influence / 2000
        popularity_mod = election_bonus / 100

        forecast = []
        total = 0
        player_party_forecast = 0
        for party in parties:
            base = party.get('popularity', 5.0)
            if party.get('name_ru', party.get('name')) == ruling_party_name:
                incumbency_bonus = 1.1 + popularity_mod
            else:
                incumbency_bonus = 0.95
            percent = base * incumbency_bonus * (1 + stability_mod + influence_mod)
            percent = max(0.1, min(60, percent))
            total += percent
            forecast.append((party, percent))
            if party.get('name_ru', party.get('name')) == ruling_party_name:
                player_party_forecast = percent
        if total > 0:
            forecast = [(p, (v / total) * 100) for p, v in forecast]
            player_party_forecast = (player_party_forecast / total) * 100
        forecast.sort(key=lambda x: x[1], reverse=True)

        options = []
        for party, percent in forecast:
            popularity_val = party.get('popularity', 5.0)
            options.append(discord.SelectOption(label=party.get('name_ru', party['name'])[:50], value=party['id'], description=f"Прогноз: {percent:.1f}% | рейтинг: {popularity_val:.1f}%"))
        
        view = ForecastSelectView(forecast, parties, options)

        forecast_text = f"**Ваша партия** — {player_party_forecast:.1f}%\n"
        for party, percent in forecast[:3]:
            if party.get('name_ru', party.get('name')) != ruling_party_name:
                forecast_text += f"**{party.get('name_ru', party['name'])}** — {percent:.1f}%\n"

        embed = discord.Embed(
            title=f"{EMOJIS['partia']} ПРОГНОЗ ВЫБОРОВ • {state_name}",
            description=f"**Краткий прогноз (топ-3):**\n{forecast_text}\n\nВыберите любую партию для детальной информации:",
            color=DARK_THEME_COLOR
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def show_factions(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        factions = load_factions(state_id)
        if not factions:
            await interaction.response.send_message("Фракции не инициализированы!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"{EMOJIS['partia']} ПОЛИТИЧЕСКИЕ ФРАКЦИИ",
            description="Баланс сил внутри правящей партии",
            color=DARK_THEME_COLOR
        )
        
        for faction_id, faction in factions.items():
            influence = faction.get("influence", 0)
            loyalty = faction.get("loyalty", 50)
            membership = faction.get("membership", 1000)
            bar = "█" * int(influence // 10) + "░" * (10 - int(influence // 10))
            embed.add_field(
                name=f"{faction.get('name', faction_id)}",
                value=f"```\n"
                      f"Влияние: {bar} {influence:.1f}%\n"
                      f"Лояльность: {loyalty:.1f}%\n"
                      f"Численность: {membership:,}\n"
                      f"```",
                inline=False
            )
        
        view = View()
        
        strengthen_btn = Button(label="Укрепить правящую фракцию", style=discord.ButtonStyle.success)
        async def strengthen_cb(btn_interaction: discord.Interaction):
            available, _ = check_action_cooldown(state_id, "strengthen_faction")
            if not available:
                await btn_interaction.response.send_message("Действие на перезарядке!", ephemeral=True)
                return
            if spend_political_power(state_data, 50)[0]:
                ruling = get_ruling_faction(state_id)
                if ruling:
                    update_faction_influence(state_id, ruling[0], 5)
                    set_action_cooldown(state_id, "strengthen_faction")
                    await btn_interaction.response.send_message(f"Влияние фракции **{ruling[1]['name']}** укреплено! +5%", ephemeral=True)
                else:
                    await btn_interaction.response.send_message("Не найдена правящая фракция!", ephemeral=True)
            else:
                await btn_interaction.response.send_message("Недостаточно политической власти! Нужно 50⚡", ephemeral=True)
        strengthen_btn.callback = strengthen_cb
        view.add_item(strengthen_btn)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ==================== МЕЖДУНАРОДНЫЕ ОПЕРАЦИИ ====================

    async def show_intelligence_operations(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        states = load_states()
        options = []
        
        for sid, sdata in states["players"].items():
            if sid != state_id:
                country_name = sdata.get("state", {}).get("statename", sid)
                options.append(discord.SelectOption(label=country_name, value=sid))
        
        if not options:
            await interaction.response.send_message("Нет других государств для операций!", ephemeral=True)
            return
        
        select_target = Select(placeholder="Выберите целевую страну...", options=options[:25], min_values=1, max_values=1)
        
        async def target_callback(select_interaction: discord.Interaction):
            target_id = select_interaction.data['values'][0]
            target_name = get_state_name_by_id(target_id)
            
            # Создаём меню выбора операции
            op_options = []
            for op_key, op_data in INTELLIGENCE_OPERATIONS.items():
                op_options.append(discord.SelectOption(
                    label=op_data["name"],
                    value=op_key,
                    description=f"Стоимость: {op_data['cost_pp']}⚡ + {op_data['cost_influence']} влияния | Шанс: {op_data['success_chance']*100:.0f}%"
                ))
            
            select_op = Select(placeholder="Выберите тип операции...", options=op_options[:25], min_values=1, max_values=1)
            
            async def op_callback(op_interaction: discord.Interaction):
                op_key = op_interaction.data['values'][0]
                op_data = INTELLIGENCE_OPERATIONS[op_key]
                
                available, next_available = check_action_cooldown(state_id, op_key)
                if not available:
                    hours_left = (next_available - datetime.now()).total_seconds() / 3600
                    await op_interaction.response.send_message(f"Операция на перезарядке! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
                    return
                
                if not spend_political_power(state_data, op_data["cost_pp"])[0]:
                    await op_interaction.response.send_message(f"Недостаточно политической власти! Нужно **{op_data['cost_pp']}** ⚡.", ephemeral=True)
                    return
                
                if get_influence(state_data) < op_data["cost_influence"]:
                    await op_interaction.response.send_message(f"Недостаточно влияния! Нужно **{op_data['cost_influence']}**.", ephemeral=True)
                    return
                
                spend_influence(state_data, op_data["cost_influence"])
                set_action_cooldown(state_id, op_key)
                
                # Рассчитываем результат
                success = random.random() < op_data["success_chance"]
                
                if success:
                    # Применяем эффекты
                    for effect, value in op_data["effects"].items():
                        if effect == "target_stability":
                            target_state = load_states()["players"].get(target_id, {})
                            if target_state:
                                target_state["stability"] = max(0, min(100, target_state.get("stability", 50) + value))
                                save_player_state(int(target_state.get("assigned_to", 0)), target_state)
                        elif effect == "target_popularity":
                            target_state = load_states()["players"].get(target_id, {})
                            if target_state and "politics" in target_state:
                                target_state["politics"]["popularity"] = max(0, min(100, target_state["politics"].get("popularity", 50) + value))
                                save_player_state(int(target_state.get("assigned_to", 0)), target_state)
                        elif effect == "own_influence":
                            add_influence(state_data, value)
                    
                    embed = discord.Embed(
                        title=f"✅ ОПЕРАЦИЯ УСПЕШНА: {op_data['name']}",
                        description=f"Операция против **{target_name}** проведена успешно!",
                        color=0x00FF00
                    )
                    embed.add_field(name="Описание", value=op_data["description"], inline=False)
                    for effect, value in op_data["effects"].items():
                        embed.add_field(name=effect, value=f"{value:+}", inline=True)
                    embed.add_field(name="Затрачено власти", value=f"-{op_data['cost_pp']}", inline=True)
                    embed.add_field(name="Затрачено влияния", value=f"-{op_data['cost_influence']}", inline=True)
                else:
                    # Провал с рисками
                    risk_triggered = random.random() < op_data.get("risk", 0.3)
                    embed = discord.Embed(
                        title=f"❌ ОПЕРАЦИЯ ПРОВАЛЕНА: {op_data['name']}",
                        description=f"Операция против **{target_name}** провалена!",
                        color=0xFF0000
                    )
                    embed.add_field(name="Описание", value=op_data["description"], inline=False)
                    if risk_triggered and "risk_effects" in op_data:
                        embed.add_field(name="Последствия", value="Операция раскрыта! Отношения ухудшились.", inline=False)
                        for effect, value in op_data["risk_effects"].items():
                            embed.add_field(name=effect, value=f"{value:+}", inline=True)
                    embed.add_field(name="Затрачено власти", value=f"-{op_data['cost_pp']}", inline=True)
                    embed.add_field(name="Затрачено влияния", value=f"-{op_data['cost_influence']}", inline=True)
                
                save_player_state(interaction.user.id, state_data)
                await op_interaction.response.send_message(embed=embed, ephemeral=False)
            
            select_op.callback = op_callback
            await select_interaction.response.edit_message(view=View().add_item(select_op))
        
        select_target.callback = target_callback
        await interaction.response.send_message(view=View().add_item(select_target), ephemeral=True)

    # ==================== СТАНДАРТНЫЕ ДЕЙСТВИЯ ====================

    async def start_elections(self, interaction, state_id: str, state_data: Dict):
        state_name = get_state_name_by_id(state_id)
        term_years = ELECTION_TERMS.get(state_name, 4)
        if term_years is None:
            await interaction.followup.send(f"{EMOJIS['partia']} В **{state_name}** выборы не проводятся!", ephemeral=True)
            return

        parliament = Parliament(state_id, state_data)
        if not parliament.can_declare_election():
            await interaction.followup.send(f"{EMOJIS['partia']} Досрочные выборы можно объявлять не чаще 1 раза в игровой год!\nСледующие выборы: {parliament.parliament_data.get('next_election', 'неизвестно')}", ephemeral=True)
            return

        parties = load_country_parties(state_name)
        if not parties:
            await interaction.followup.send(f"{EMOJIS['partia']} Для **{state_name}** нет партий!", ephemeral=True)
            return

        election = Election(state_id, state_data, parties)
        seats_distribution, player_won = await election.run_election(interaction, is_auto=False)
        if not player_won:
            states = load_states()
            for sid, sdata in states["players"].items():
                if sdata.get("assigned_to") == str(interaction.user.id):
                    del sdata["assigned_to"]
                    if "assigned_at" in sdata:
                        del sdata["assigned_at"]
                    break
            save_states(states)

    async def check_auto_elections(self):
        states = load_states()
        for state_id, state_data in states["players"].items():
            if "assigned_to" not in state_data:
                continue
            parliament = Parliament(state_id, state_data)
            if parliament.needs_election():
                parties = load_country_parties(state_data["state"]["statename"])
                if parties:
                    election = Election(state_id, state_data, parties)
                    seats_distribution, player_won = await election.run_election(ctx=None, is_auto=True)
                    if not player_won:
                        del state_data["assigned_to"]
                        if "assigned_at" in state_data:
                            del state_data["assigned_at"]
                        save_states(states)
                    print(f"[Political Power] Auto-elections completed for {state_data['state']['statename']}")

    # ==================== ДЕЙСТВИЯ ПРАВЯЩЕЙ ПАРТИИ ====================

    async def action_agitation(self, interaction: discord.Interaction, state_id: str, state_data: Dict, target_ideology: str):
        cost = 40
        influence_gain = random.uniform(0.1, 0.5)
        if target_ideology == "left":
            popularity_gain = random.uniform(0.5, 2.0)
            action_name = "ЛЕВУЮ АГИТАЦИЮ"
            ideology_name = "левых партий"
        elif target_ideology == "right":
            popularity_gain = random.uniform(0.5, 2.0)
            action_name = "ПРАВУЮ АГИТАЦИЮ"
            ideology_name = "правых партий"
        else:
            popularity_gain = random.uniform(0.5, 2.0)
            action_name = "ЦЕНТРИСТСКУЮ АГИТАЦИЮ"
            ideology_name = "центристских партий"

        available, next_available = check_action_cooldown(state_id, f"agitation_{target_ideology}")
        if not available:
            hours_left = (next_available - datetime.now()).total_seconds() / 3600
            await interaction.response.send_message(f"Агитация недоступна! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
            return

        if not spend_political_power(state_data, cost)[0]:
            await interaction.response.send_message(f"Недостаточно политической власти! Нужно **{cost}** ⚡.", ephemeral=True)
            return

        add_influence(state_data, influence_gain)

        state_name = get_state_name_by_id(state_id)
        parties_db = load_parties_from_json()
        affected_parties = []
        if state_name in parties_db:
            for party in parties_db[state_name]:
                position = party.get('position', 'center')
                party_ideology = get_party_ideology_group(position)
                if party_ideology == target_ideology:
                    old_popularity = party.get('popularity', 5.0)
                    new_popularity = min(50.0, old_popularity + popularity_gain)
                    party['popularity'] = new_popularity
                    affected_parties.append(party.get('name_ru', party.get('name')))
            with open(PARTIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(parties_db, f, ensure_ascii=False, indent=4)

        ruling_party_name = state_data["politics"].get("ruling_party", "")
        ruling_party_ideology = get_party_ideology_group(
            next((p.get('position', 'center') for p in parties_db.get(state_name, []) if p.get('name_ru', p.get('name')) == ruling_party_name), 'center')
        )
        if ruling_party_ideology == target_ideology:
            state_data["politics"]["popularity"] = min(100, state_data["politics"].get("popularity", 50) + popularity_gain)

        set_action_cooldown(state_id, f"agitation_{target_ideology}")
        save_player_state(interaction.user.id, state_data)

        affected_text = ", ".join(affected_parties[:3])
        if len(affected_parties) > 3:
            affected_text += f" и ещё {len(affected_parties) - 3}"
        embed = discord.Embed(title=f"{EMOJIS['partia']} {action_name}", description=f"Вы провели {action_name.lower()} в **{get_state_name_by_id(state_id)}**!", color=0x00AAFF)
        embed.add_field(name=f"{EMOJIS['crisis']} Популярность {ideology_name}", value=f"+{popularity_gain:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['social']} Влияние", value=f"+{influence_gain:.1f}", inline=True)
        embed.add_field(name=f"{EMOJIS['partia']} Затронутые партии", value=affected_text if affected_text else "Нет партий этой идеологии", inline=False)
        embed.add_field(name=f"{EMOJIS['pp']} Затрачено", value=f"-{cost}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def action_propaganda(self, interaction: discord.Interaction, state_id: str, state_data: Dict, target_ideology: str):
        cost = 50
        influence_gain = random.uniform(0.5, 2.5)
        stability_gain = random.uniform(0.5, 1.5)
        if target_ideology == "left":
            action_name = "ЛЕВУЮ ПРОПАГАНДУ"
        elif target_ideology == "right":
            action_name = "ПРАВУЮ ПРОПАГАНДУ"
        else:
            action_name = "ЦЕНТРИСТСКУЮ ПРОПАГАНДУ"

        available, next_available = check_action_cooldown(state_id, f"propaganda_{target_ideology}")
        if not available:
            hours_left = (next_available - datetime.now()).total_seconds() / 3600
            await interaction.response.send_message(f"Пропаганда недоступна! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
            return

        if not spend_political_power(state_data, cost)[0]:
            await interaction.response.send_message(f"Недостаточно политической власти! Нужно **{cost}** ⚡.", ephemeral=True)
            return

        add_influence(state_data, influence_gain)
        state_data["stability"] = min(100, state_data.get("stability", 50) + stability_gain)
        set_action_cooldown(state_id, f"propaganda_{target_ideology}")
        save_player_state(interaction.user.id, state_data)

        embed = discord.Embed(title=f"{EMOJIS['social']} {action_name}", description=f"Вы провели {action_name.lower()} в **{get_state_name_by_id(state_id)}**!", color=0x00FF00)
        embed.add_field(name=f"{EMOJIS['social']} Влияние", value=f"+{influence_gain:.1f}", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"+{stability_gain:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Затрачено", value=f"-{cost}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def action_dissolve_party(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        cost_influence = 400
        cost_power = 100
        if state_data.get("assigned_to") != str(interaction.user.id):
            await interaction.response.send_message(f"{EMOJIS['government']} Только лидер государства может упразднять партии!", ephemeral=True)
            return

        available, next_available = check_action_cooldown(state_id, "dissolve_party")
        if not available:
            hours_left = (next_available - datetime.now()).total_seconds() / 3600
            await interaction.response.send_message(f"Упразднение партии недоступно! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
            return

        current_influence = get_influence(state_data)
        if current_influence < cost_influence:
            await interaction.response.send_message(f"Недостаточно влияния! Нужно **{cost_influence}** (у вас {current_influence:.1f}).", ephemeral=True)
            return
        if not spend_political_power(state_data, cost_power)[0]:
            await interaction.response.send_message(f"Недостаточно политической власти! Нужно **{cost_power}** ⚡.", ephemeral=True)
            return

        state_name = get_state_name_by_id(state_id)
        parties_data = load_country_parties(state_name)
        parliament = Parliament(state_id, state_data)
        distribution = parliament.get_distribution()
        ruling_party_id = parliament.get_ruling_party()

        other_parties = []
        for party_id, seats in distribution.items():
            if party_id != ruling_party_id:
                party = get_party_by_id(parties_data, party_id)
                if party:
                    other_parties.append((party_id, party.get('name_ru', party.get('name', 'Неизвестная партия')), seats))
        if not other_parties:
            await interaction.response.send_message(f"{EMOJIS['partia']} Нет других партий в парламенте для упразднения!", ephemeral=True)
            return

        options = []
        for party_id, party_name, seats in other_parties[:25]:
            options.append(discord.SelectOption(label=party_name[:50], value=party_id, description=f"{seats} мест в парламенте"))
        select = Select(placeholder="Выберите партию для упразднения...", options=options, min_values=1, max_values=1)

        async def select_callback(select_interaction: discord.Interaction):
            if select_interaction.user.id != interaction.user.id:
                await select_interaction.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            target_party_id = select_interaction.data['values'][0]
            target_party = get_party_by_id(parties_data, target_party_id)
            target_party_name = target_party.get('name_ru', target_party.get('name', 'Неизвестная партия')) if target_party else "Неизвестная партия"
            spend_influence(state_data, cost_influence)
            parliament.remove_party(target_party_id)
            set_action_cooldown(state_id, "dissolve_party")
            save_player_state(interaction.user.id, state_data)

            embed = discord.Embed(title=f"{EMOJIS['zakon']} УПРАЗДНЕНИЕ ПАРТИИ", description=f"Партия **{target_party_name}** была официально упразднена в **{state_name}**!\n\nЕё места в парламенте перераспределены между оставшимися партиями.", color=0xFF0000)
            embed.add_field(name=f"{EMOJIS['social']} Затрачено влияния", value=f"-{cost_influence}", inline=True)
            embed.add_field(name=f"{EMOJIS['pp']} Затрачено власти", value=f"-{cost_power}", inline=True)
            await select_interaction.response.edit_message(embed=embed, view=None)

        select.callback = select_callback
        embed = discord.Embed(title=f"{EMOJIS['partia']} УПРАЗДНЕНИЕ ПАРТИИ", description=f"Выберите партию для упразднения в **{state_name}**:\n\nСтоимость: **{cost_influence}** влияния + **{cost_power}** ⚡ политической власти", color=DARK_THEME_COLOR)
        await interaction.response.send_message(embed=embed, view=View().add_item(select), ephemeral=True)

    async def action_change_ruling_party(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        cost_power = 200
        cost_influence = 300
        if state_data.get("assigned_to") != str(interaction.user.id):
            await interaction.response.send_message(f"{EMOJIS['government']} Только лидер государства может менять правящую партию!", ephemeral=True)
            return

        available, next_available = check_action_cooldown(state_id, "change_party")
        if not available:
            hours_left = (next_available - datetime.now()).total_seconds() / 3600
            await interaction.response.send_message(f"Смена партии недоступна! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
            return

        current_influence = get_influence(state_data)
        if current_influence < cost_influence:
            await interaction.response.send_message(f"Недостаточно влияния! Нужно **{cost_influence}** (у вас {current_influence:.1f}).", ephemeral=True)
            return
        if not spend_political_power(state_data, cost_power)[0]:
            await interaction.response.send_message(f"Недостаточно политической власти! Нужно **{cost_power}** ⚡.", ephemeral=True)
            return

        state_name = get_state_name_by_id(state_id)
        parties_data = load_country_parties(state_name)
        current_ruling = state_data["politics"].get("ruling_party", "")

        other_parties = []
        for party in parties_data:
            party_name = party.get('name_ru', party.get('name'))
            if party_name != current_ruling:
                other_parties.append((party['id'], party_name, party.get('ideology', 'Не указана')))
        if not other_parties:
            await interaction.response.send_message(f"{EMOJIS['partia']} Нет других партий для смены!", ephemeral=True)
            return

        options = []
        for party_id, party_name, ideology in other_parties[:25]:
            options.append(discord.SelectOption(label=party_name[:50], value=party_id, description=ideology[:100]))
        select = Select(placeholder="Выберите новую правящую партию...", options=options, min_values=1, max_values=1)

        async def select_callback(select_interaction: discord.Interaction):
            if select_interaction.user.id != interaction.user.id:
                await select_interaction.response.send_message("Это не ваше меню!", ephemeral=True)
                return
            target_party_id = select_interaction.data['values'][0]
            target_party = get_party_by_id(parties_data, target_party_id)
            target_party_name = target_party.get('name_ru', target_party.get('name', 'Неизвестная партия')) if target_party else "Неизвестная партия"
            spend_influence(state_data, cost_influence)
            old_party = state_data["politics"].get("ruling_party", "")
            state_data["politics"]["ruling_party"] = target_party_name
            state_data["politics"]["ideology"] = target_party.get('ideology', 'Не указана')
            state_data["politics"]["popularity"] = target_party.get('popularity', 50.0)
            set_action_cooldown(state_id, "change_party")
            save_player_state(interaction.user.id, state_data)

            embed = discord.Embed(title=f"{EMOJIS['government']} СМЕНА ПРАВЯЩЕЙ ПАРТИИ", description=f"В **{state_name}** произошла смена правящей партии!", color=0xFFAA00)
            embed.add_field(name="Старая партия", value=f"```\n{old_party}\n```", inline=True)
            embed.add_field(name="Новая партия", value=f"```\n{target_party_name}\n```", inline=True)
            embed.add_field(name=f"{EMOJIS['social']} Затрачено влияния", value=f"-{cost_influence}", inline=True)
            embed.add_field(name=f"{EMOJIS['pp']} Затрачено власти", value=f"-{cost_power}", inline=True)
            await select_interaction.response.edit_message(embed=embed, view=None)

        select.callback = select_callback
        embed = discord.Embed(title=f"{EMOJIS['partia']} СМЕНА ПРАВЯЩЕЙ ПАРТИИ", description=f"Выберите новую правящую партию в **{state_name}**:\n\nСтоимость: **{cost_influence}** влияния + **{cost_power}** ⚡ политической власти", color=DARK_THEME_COLOR)
        await interaction.response.send_message(embed=embed, view=View().add_item(select), ephemeral=True)

    # ==================== ДЕЙСТВИЯ СЕПАРАТИСТОВ ====================

    async def _check_opposition(self, interaction: discord.Interaction, state_data: Dict) -> bool:
        if state_data.get("assigned_to") == str(interaction.user.id):
            await interaction.response.send_message(f"{EMOJIS['government']} Вы правящая партия и не можете заниматься сепаратистской деятельностью!", ephemeral=True)
            return False
        return True

    async def separatist_recruit(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        if not await self._check_opposition(interaction, state_data):
            return
        cost = 30
        influence_gain = random.uniform(0.5, 2.0)
        popularity_loss = random.uniform(0.2, 0.8)
        stability_loss = random.uniform(0.1, 0.5)

        available, next_available = check_action_cooldown(state_id, "recruit")
        if not available:
            hours_left = (next_available - datetime.now()).total_seconds() / 3600
            await interaction.response.send_message(f"Вербовка недоступна! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
            return
        if not spend_political_power(state_data, cost)[0]:
            await interaction.response.send_message(f"Недостаточно политической власти! Нужно **{cost}** ⚡.", ephemeral=True)
            return

        add_influence(state_data, influence_gain)
        state_data["politics"]["popularity"] = max(0, state_data["politics"].get("popularity", 50) - popularity_loss)
        state_data["stability"] = max(0, state_data.get("stability", 50) - stability_loss)
        set_action_cooldown(state_id, "recruit")
        save_player_state(interaction.user.id, state_data)

        embed = discord.Embed(title=f"{EMOJIS['army']} ВЕРБОВКА", description=f"Вы провели вербовку сторонников в **{get_state_name_by_id(state_id)}**!", color=0x8B0000)
        embed.add_field(name=f"{EMOJIS['social']} Влияние сепаратистов", value=f"+{influence_gain:.1f}", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Популярность правящей партии", value=f"-{popularity_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"-{stability_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Затрачено", value=f"-{cost}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def separatist_arson(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        if not await self._check_opposition(interaction, state_data):
            return
        cost = 25
        influence_gain = random.uniform(0.3, 1.5)
        stability_loss = random.uniform(1.0, 3.0)
        popularity_loss = random.uniform(0.3, 1.0)

        available, next_available = check_action_cooldown(state_id, "arson")
        if not available:
            hours_left = (next_available - datetime.now()).total_seconds() / 3600
            await interaction.response.send_message(f"Поджоги недоступны! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
            return
        if not spend_political_power(state_data, cost)[0]:
            await interaction.response.send_message(f"Недостаточно политической власти! Нужно **{cost}** ⚡.", ephemeral=True)
            return

        add_influence(state_data, influence_gain)
        state_data["stability"] = max(0, state_data.get("stability", 50) - stability_loss)
        state_data["politics"]["popularity"] = max(0, state_data["politics"].get("popularity", 50) - popularity_loss)
        set_action_cooldown(state_id, "arson")
        save_player_state(interaction.user.id, state_data)

        embed = discord.Embed(title=f"{EMOJIS['army']} ПОДЖОГИ", description=f"В **{get_state_name_by_id(state_id)}** произошла серия поджогов!", color=0xFF4500)
        embed.add_field(name=f"{EMOJIS['social']} Влияние сепаратистов", value=f"+{influence_gain:.1f}", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"-{stability_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Популярность правящей партии", value=f"-{popularity_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Затрачено", value=f"-{cost}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def separatist_sabotage(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        if not await self._check_opposition(interaction, state_data):
            return
        cost = 40
        influence_gain = random.uniform(0.8, 2.5)
        stability_loss = random.uniform(2.0, 5.0)
        popularity_loss = random.uniform(0.5, 1.5)

        available, next_available = check_action_cooldown(state_id, "sabotage")
        if not available:
            hours_left = (next_available - datetime.now()).total_seconds() / 3600
            await interaction.response.send_message(f"Диверсии недоступны! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
            return
        if not spend_political_power(state_data, cost)[0]:
            await interaction.response.send_message(f"Недостаточно политической власти! Нужно **{cost}** ⚡.", ephemeral=True)
            return

        add_influence(state_data, influence_gain)
        state_data["stability"] = max(0, state_data.get("stability", 50) - stability_loss)
        state_data["politics"]["popularity"] = max(0, state_data["politics"].get("popularity", 50) - popularity_loss)
        set_action_cooldown(state_id, "sabotage")
        save_player_state(interaction.user.id, state_data)

        embed = discord.Embed(title=f"{EMOJIS['army']} ДИВЕРСИИ", description=f"В **{get_state_name_by_id(state_id)}** совершены диверсии на инфраструктуре!", color=0xFF0000)
        embed.add_field(name=f"{EMOJIS['social']} Влияние сепаратистов", value=f"+{influence_gain:.1f}", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"-{stability_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Популярность правящей партии", value=f"-{popularity_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Затрачено", value=f"-{cost}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def separatist_terror(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        if not await self._check_opposition(interaction, state_data):
            return
        cost = 60
        influence_gain = random.uniform(1.5, 4.0)
        stability_loss = random.uniform(4.0, 8.0)
        popularity_loss = random.uniform(1.0, 3.0)

        available, next_available = check_action_cooldown(state_id, "terror_act")
        if not available:
            hours_left = (next_available - datetime.now()).total_seconds() / 3600
            await interaction.response.send_message(f"Терракт недоступен! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
            return
        if not spend_political_power(state_data, cost)[0]:
            await interaction.response.send_message(f"Недостаточно политической власти! Нужно **{cost}** ⚡.", ephemeral=True)
            return

        add_influence(state_data, influence_gain)
        state_data["stability"] = max(0, state_data.get("stability", 50) - stability_loss)
        state_data["politics"]["popularity"] = max(0, state_data["politics"].get("popularity", 50) - popularity_loss)
        set_action_cooldown(state_id, "terror_act")
        save_player_state(interaction.user.id, state_data)

        embed = discord.Embed(title=f"{EMOJIS['army']} ТЕРРАКТ", description=f"В **{get_state_name_by_id(state_id)}** совершён террористический акт!", color=0x8B0000)
        embed.add_field(name=f"{EMOJIS['social']} Влияние сепаратистов", value=f"+{influence_gain:.1f}", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"-{stability_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Популярность правящей партии", value=f"-{popularity_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Затрачено", value=f"-{cost}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    async def separatist_protests(self, interaction: discord.Interaction, state_id: str, state_data: Dict):
        if not await self._check_opposition(interaction, state_data):
            return
        cost = 20
        influence_gain = random.uniform(0.2, 1.0)
        stability_loss = random.uniform(0.5, 2.0)
        popularity_loss = random.uniform(0.5, 1.5)

        available, next_available = check_action_cooldown(state_id, "separatist_protests")
        if not available:
            hours_left = (next_available - datetime.now()).total_seconds() / 3600
            await interaction.response.send_message(f"Протесты недоступны! Следующая возможность через **{hours_left:.1f} часов**.", ephemeral=True)
            return
        if not spend_political_power(state_data, cost)[0]:
            await interaction.response.send_message(f"Недостаточно политической власти! Нужно **{cost}** ⚡.", ephemeral=True)
            return

        add_influence(state_data, influence_gain)
        state_data["stability"] = max(0, state_data.get("stability", 50) - stability_loss)
        state_data["politics"]["popularity"] = max(0, state_data["politics"].get("popularity", 50) - popularity_loss)
        set_action_cooldown(state_id, "separatist_protests")
        save_player_state(interaction.user.id, state_data)

        embed = discord.Embed(title=f"{EMOJIS['social']} ПРОТЕСТЫ", description=f"В **{get_state_name_by_id(state_id)}** прошли массовые протесты!", color=0xFF6600)
        embed.add_field(name=f"{EMOJIS['social']} Влияние сепаратистов", value=f"+{influence_gain:.1f}", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Стабильность", value=f"-{stability_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Популярность правящей партии", value=f"-{popularity_loss:.1f}%", inline=True)
        embed.add_field(name=f"{EMOJIS['pp']} Затрачено", value=f"-{cost}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=False)

    # ==================== ДЕЙСТВИЯ ОППОЗИЦИИ ====================

    async def opposition_agitation(self, state_id: str, state_data: Dict, opposition_party: Dict):
        popularity_gain = random.uniform(0.5, 2.0)
        ruling_popularity_loss = random.uniform(0.3, 1.5)
        new_popularity = state_data["politics"].get("popularity", 50) - ruling_popularity_loss
        state_data["politics"]["popularity"] = max(0, new_popularity)

        state_name = get_state_name_by_id(state_id)
        parties_db = load_parties_from_json()
        if state_name in parties_db:
            for party in parties_db[state_name]:
                if party.get('id') == opposition_party['id']:
                    party['popularity'] = min(50.0, party.get('popularity', 5.0) + popularity_gain)
                if party.get('name_ru', party.get('name')) == state_data["politics"].get("ruling_party", ""):
                    party['popularity'] = max(0.1, state_data["politics"]["popularity"])
            with open(PARTIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(parties_db, f, ensure_ascii=False, indent=4)

        save_player_state(int(state_data.get("assigned_to", 0)), state_data)
        return f"Оппозиционная партия **{opposition_party.get('name_ru', opposition_party['name'])}** провела агитацию! Популярность правящей партии снизилась на {ruling_popularity_loss:.1f}%."

    async def opposition_protests(self, state_id: str, state_data: Dict, opposition_party: Dict):
        stability_loss = random.uniform(1.0, 2.5)
        popularity_loss = random.uniform(1.0, 3.0)
        influence_gain = random.uniform(0.5, 1.5)

        state_data["stability"] = max(0, state_data.get("stability", 50) - stability_loss)
        new_popularity = state_data["politics"].get("popularity", 50) - popularity_loss
        state_data["politics"]["popularity"] = max(0, new_popularity)
        add_influence(state_data, influence_gain)

        state_name = get_state_name_by_id(state_id)
        parties_db = load_parties_from_json()
        if state_name in parties_db:
            for party in parties_db[state_name]:
                if party.get('name_ru', party.get('name')) == state_data["politics"].get("ruling_party", ""):
                    party['popularity'] = max(0.1, state_data["politics"]["popularity"])
                    break
            with open(PARTIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(parties_db, f, ensure_ascii=False, indent=4)

        save_player_state(int(state_data.get("assigned_to", 0)), state_data)
        return f"Оппозиционная партия **{opposition_party.get('name_ru', opposition_party['name'])}** организовала протесты! Стабильность -{stability_loss:.1f}%, популярность правящей партии -{popularity_loss:.1f}%."

    async def run_opposition_actions(self):
        states = load_states()
        for state_id, state_data in states["players"].items():
            if "assigned_to" not in state_data:
                continue
            state_name = get_state_name_by_id(state_id)
            parties = load_country_parties(state_name)
            ruling_party_name = state_data.get("politics", {}).get("ruling_party", "")
            opposition_parties = [p for p in parties if p.get('name_ru', p.get('name')) != ruling_party_name]
            if not opposition_parties:
                continue
            action = random.choice(["agitation", "protests"])
            opposition_party = random.choice(opposition_parties)
            if action == "agitation":
                available, _ = check_action_cooldown(state_id, "opposition_agitation")
                if available:
                    result = await self.opposition_agitation(state_id, state_data, opposition_party)
                    set_action_cooldown(state_id, "opposition_agitation")
                    print(f"[Opposition] {state_name}: {result}")
            else:
                available, _ = check_action_cooldown(state_id, "opposition_protests")
                if available:
                    result = await self.opposition_protests(state_id, state_data, opposition_party)
                    set_action_cooldown(state_id, "opposition_protests")
                    print(f"[Opposition] {state_name}: {result}")
            save_states(states)


# ==================== VIEW ====================

class PoliticalSelectView(View):
    def __init__(self, state_id: str, state_data: Dict, political_system: PoliticalSystem):
        super().__init__(timeout=120)

        # Категория: ПРОСМОТР (без эмодзи)
        select_view = Select(
            placeholder="ПРОСМОТР - информация о политической системе",
            options=[
                discord.SelectOption(label="Парламент", value="show_parliament", description="Состав парламента"),
                discord.SelectOption(label="Прогноз выборов", value="show_forecast", description="Прогноз результатов"),
                discord.SelectOption(label="Фракции", value="show_factions", description="Баланс сил внутри партии"),
                discord.SelectOption(label="Международные операции", value="intelligence_ops", description="Операции влияния на другие страны")
            ],
            min_values=1, max_values=1
        )
        select_view.callback = self.create_callback(state_id, state_data, political_system, "view")
        self.add_item(select_view)

        # Категория: ПОЛИТИКА
        select_politics = Select(
            placeholder="ПОЛИТИКА - действия правящей партии",
            options=[
                discord.SelectOption(label="Объявить выборы", value="start_elections", description="Начать парламентские выборы"),
                discord.SelectOption(label="Агитация (левые)", value="agitation_left", description="Увеличить популярность левых партий (40 ⚡)"),
                discord.SelectOption(label="Агитация (центр)", value="agitation_center", description="Увеличить популярность центристских партий (40 ⚡)"),
                discord.SelectOption(label="Агитация (правые)", value="agitation_right", description="Увеличить популярность правых партий (40 ⚡)"),
                discord.SelectOption(label="Пропаганда (левые)", value="propaganda_left", description="Левый уклон пропаганды (50 ⚡)"),
                discord.SelectOption(label="Пропаганда (центр)", value="propaganda_center", description="Центристский уклон пропаганды (50 ⚡)"),
                discord.SelectOption(label="Пропаганда (правые)", value="propaganda_right", description="Правый уклон пропаганды (50 ⚡)"),
                discord.SelectOption(label="Упразднить партию", value="dissolve", description="Удалить оппозиционную партию из парламента (400 влияния + 100 ⚡)"),
                discord.SelectOption(label="Сменить правящую партию", value="change_party", description="Сменить правящую партию (300 влияния + 200 ⚡)")
            ],
            min_values=1, max_values=1
        )
        select_politics.callback = self.create_callback(state_id, state_data, political_system, "politics")
        self.add_item(select_politics)

        # Категория: СЕПАРАТИЗМ
        select_separatism = Select(
            placeholder="СЕПАРАТИЗМ - действия против режима (только для оппозиции)",
            options=[
                discord.SelectOption(label="Вербовка", value="recruit", description="Вербовка сторонников (30 ⚡)"),
                discord.SelectOption(label="Поджоги", value="arson", description="Серия поджогов (25 ⚡)"),
                discord.SelectOption(label="Диверсии", value="sabotage", description="Диверсии на инфраструктуре (40 ⚡)"),
                discord.SelectOption(label="Терракт", value="terror", description="Террористический акт (60 ⚡)"),
                discord.SelectOption(label="Протесты", value="protests", description="Организация протестов (20 ⚡)")
            ],
            min_values=1, max_values=1
        )
        select_separatism.callback = self.create_callback(state_id, state_data, political_system, "separatism")
        self.add_item(select_separatism)

    def create_callback(self, state_id: str, state_data: Dict, political_system: PoliticalSystem, category: str):
        async def callback(interaction: discord.Interaction):
            value = interaction.data['values'][0]
            if value == "show_parliament":
                await political_system.show_parliament(interaction, state_id, state_data)
            elif value == "show_forecast":
                await political_system.show_election_forecast(interaction, state_id, state_data)
            elif value == "show_factions":
                await political_system.show_factions(interaction, state_id, state_data)
            elif value == "intelligence_ops":
                await political_system.show_intelligence_operations(interaction, state_id, state_data)
            elif value == "start_elections":
                if state_data.get("assigned_to") != str(interaction.user.id):
                    await interaction.response.send_message(f"{EMOJIS['government']} Только лидер может объявлять выборы!", ephemeral=True)
                    return
                await interaction.response.defer(ephemeral=True)
                await political_system.start_elections(interaction, state_id, state_data)
            elif value == "agitation_left":
                await political_system.action_agitation(interaction, state_id, state_data, "left")
            elif value == "agitation_center":
                await political_system.action_agitation(interaction, state_id, state_data, "center")
            elif value == "agitation_right":
                await political_system.action_agitation(interaction, state_id, state_data, "right")
            elif value == "propaganda_left":
                await political_system.action_propaganda(interaction, state_id, state_data, "left")
            elif value == "propaganda_center":
                await political_system.action_propaganda(interaction, state_id, state_data, "center")
            elif value == "propaganda_right":
                await political_system.action_propaganda(interaction, state_id, state_data, "right")
            elif value == "dissolve":
                await political_system.action_dissolve_party(interaction, state_id, state_data)
            elif value == "change_party":
                await political_system.action_change_ruling_party(interaction, state_id, state_data)
            elif value == "recruit":
                await political_system.separatist_recruit(interaction, state_id, state_data)
            elif value == "arson":
                await political_system.separatist_arson(interaction, state_id, state_data)
            elif value == "sabotage":
                await political_system.separatist_sabotage(interaction, state_id, state_data)
            elif value == "terror":
                await political_system.separatist_terror(interaction, state_id, state_data)
            elif value == "protests":
                await political_system.separatist_protests(interaction, state_id, state_data)
        return callback


class ParliamentSelectView(View):
    def __init__(self, options: List[discord.SelectOption], parties_data: List[Dict], distribution: Dict[str, int]):
        super().__init__(timeout=120)
        select = ParliamentSelect(options, parties_data, distribution)
        self.add_item(select)


class ParliamentSelect(Select):
    def __init__(self, options: List[discord.SelectOption], parties_data: List[Dict], distribution: Dict[str, int]):
        self.parties_data = parties_data
        self.distribution = distribution
        super().__init__(placeholder="Выберите партию...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        party_id = self.values[0]
        party = next((p for p in self.parties_data if p['id'] == party_id), None)
        if not party:
            await interaction.response.send_message("Партия не найдена!", ephemeral=True)
            return
        seats = self.distribution.get(party_id, 0)
        popularity = party.get('popularity', 5.0)
        embed = discord.Embed(title=f"{EMOJIS['partia']} {party.get('name_ru', party.get('name', 'Неизвестная партия'))}", color=DARK_THEME_COLOR)
        if party.get('icon_url'):
            embed.set_thumbnail(url=party['icon_url'])
        if party.get('leader_img'):
            embed.set_image(url=party['leader_img'])
        embed.add_field(name=f"{EMOJIS['government']} Идеология", value=f"```\n{party.get('ideology', 'Не указана')}\n```", inline=False)
        translated_position = translate_position(party.get('position', 'Не указана'))
        embed.add_field(name=f"{EMOJIS['partia']} Позиция", value=f"```\n{translated_position}\n```", inline=True)
        embed.add_field(name=f"{EMOJIS['crisis']} Рейтинг", value=f"```\n{popularity:.1f}%\n```", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Лидер", value=f"```\n{party.get('leader', 'Неизвестен')}\n```", inline=False)
        embed.add_field(name=f"{EMOJIS['partia']} Мест в парламенте", value=f"```\n{seats}\n```", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ForecastSelectView(View):
    def __init__(self, forecast: List[Tuple], parties: List[Dict], options: List[discord.SelectOption]):
        super().__init__(timeout=120)
        select = ForecastSelect(options, forecast, parties)
        self.add_item(select)


class ForecastSelect(Select):
    def __init__(self, options: List[discord.SelectOption], forecast: List[Tuple], parties: List[Dict]):
        self.forecast = forecast
        self.parties = parties
        super().__init__(placeholder="Выберите партию для детальной информации...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        party_id = self.values[0]
        party = next((p for p in self.parties if p['id'] == party_id), None)
        if not party:
            await interaction.response.send_message("Партия не найдена!", ephemeral=True)
            return
        party_forecast = next((p for p in self.forecast if p[0]['id'] == party_id), None)
        if not party_forecast:
            await interaction.response.send_message("Прогноз не найден!", ephemeral=True)
            return
        percent = party_forecast[1]
        popularity = party.get('popularity', 5.0)
        embed = discord.Embed(title=f"{EMOJIS['partia']} {party.get('name_ru', party.get('name', 'Неизвестная партия'))}", description="Прогноз на выборах", color=DARK_THEME_COLOR)
        if party.get('icon_url'):
            embed.set_thumbnail(url=party['icon_url'])
        if party.get('leader_img'):
            embed.set_image(url=party['leader_img'])
        embed.add_field(name=f"{EMOJIS['vvp']} Прогноз", value=f"```\n{percent:.1f}%\n```", inline=False)
        embed.add_field(name=f"{EMOJIS['crisis']} Популярность", value=f"```\n{popularity:.1f}%\n```", inline=True)
        embed.add_field(name=f"{EMOJIS['government']} Лидер", value=f"```\n{party.get('leader', 'Неизвестен')}\n```", inline=False)
        embed.add_field(name=f"{EMOJIS['government']} Идеология", value=party.get('ideology', 'Не указана'), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==================== ЭКСПОРТИРУЕМЫЕ ФУНКЦИИ ====================

async def show_political_power_menu(ctx, user_id):
    state_id, state_data = get_player_state(user_id)
    if not state_data:
        if isinstance(ctx, discord.Interaction):
            await ctx.response.send_message("❌ Вы не состоите в государстве!", ephemeral=True)
        else:
            await ctx.send("❌ Вы не состоите в государстве!")
        return
    political_system = PoliticalSystem(ctx.bot if hasattr(ctx, 'bot') else None)
    await political_system.political_panel(ctx, state_id, state_data)


async def political_power_update_loop(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            await asyncio.sleep(POLITICAL_POWER_INTERVAL_HOURS * 3600)
            states = load_states()
            updated = 0
            for state_id, state_data in states["players"].items():
                if "assigned_to" not in state_data:
                    continue
                try:
                    gain = calculate_political_power_gain(state_data)
                    add_political_power(state_data, gain)
                    save_player_state(int(state_data["assigned_to"]), state_data)
                    updated += 1
                except Exception as e:
                    print(f"Error updating political power for {state_id}: {e}")
            print(f"[Political Power] Updated {updated} states (+{POLITICAL_POWER_INTERVAL_HOURS}h)")

            political_system = PoliticalSystem(bot)
            await political_system.check_auto_elections()
            await political_system.run_opposition_actions()

        except Exception as e:
            print(f"Error in political power loop: {e}")
            await asyncio.sleep(3600)


def daily_political_power_update(state_id: str, state_data: Dict) -> Tuple[int, str]:
    return 0, ""


# ==================== ЭКСПОРТ ====================

__all__ = [
    'load_states', 'save_states', 'get_player_state', 'get_state_name_by_id',
    'get_political_power', 'set_political_power', 'add_political_power', 'spend_political_power',
    'get_influence', 'add_influence', 'spend_influence',
    'Parliament', 'Election', 'PoliticalSystem',
    'show_political_power_menu', 'political_power_update_loop',
    'DARK_THEME_COLOR', 'EMOJIS', 'MAX_INFLUENCE',
    'POPULARITY_TIERS', 'get_popularity_tier'
]

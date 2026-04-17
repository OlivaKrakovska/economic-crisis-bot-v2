# population.py - Модуль для управления населением и его потребностями
# Версия 5.1 - с новыми эмодзи, без кнопки "Корпорации", полная поддержка двухвалютной системы

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import math

from utils import (
    format_number, format_billion, load_states, save_states,
    get_budget, get_gdp, get_inflation, get_currency_code,
    add_to_budget, DARK_THEME_COLOR
)
from resource_system import RESOURCE_PRICES
from civil_corporations_db import (
    get_all_civil_corporations, get_civil_corporations_by_country,
    CIVIL_PRODUCT_NAMES, load_corporations_state, save_corporations_state,
    initialize_corporation_state
)
from infra_build import load_infrastructure, get_all_regions_from_country

POPULATION_IMAGE_URL = "https://images-ext-1.discordapp.net/external/d5XYdvTy4VeGpxX-C4KWykKnIfdLtBMdZKRHHIJvyms/https/fxmedia.s3.amazonaws.com/articles/remote/a8afd2f5f966b3a170237d45e5b69dc6.png?format=webp&quality=lossless&width=360&height=202"

# Список картинок для специалистов
EXPERT_IMAGES = [
    "https://images-ext-1.discordapp.net/external/-0MWAaWY0B-NXXXyDS3Dzi72j5xSEO8vpbTtOp_XF8A/https/upload.wikimedia.org/wikipedia/commons/8/8d/Solnhofer_Zementwerke_002.JPG?format=webp&width=875&height=583",
    "https://media.discordapp.net/attachments/1103006938935083078/1103989016711409754/i_14.jpg?ex=69c65964&is=69c507e4&hm=74be1e241434bf61b44138febcbbf404fb2265003e2241bf5635ba074d79a0c3&=&format=webp&width=876&height=582",
    "https://media.discordapp.net/attachments/1103006938935083078/1103968903329239060/i_13.jpg?ex=69c646a9&is=69c4f529&hm=ccca5386f25e90449e83f6cecac1bdb84beac325ef0394c00b0169bbc68474d9&=&format=webp&width=417&height=288",
    "https://images-ext-1.discordapp.net/external/RqFEedramGR6ytXjbwUQFmhubiw1Si2EfaB31l-aTJM/https/gdb.voanews.com/023d0000-0aff-0242-f9ac-08da06821677_w408_r1_s.jpg?format=webp&quality=lossless&width=360&height=202"
]

EXPERT_LOG_CHANNEL_ID = 1249782883770695821

GAME_YEAR_IN_REAL_DAYS = 3
REAL_DAY_TO_GAME_DAYS = 365 / GAME_YEAR_IN_REAL_DAYS
EXPERT_REQUEST_TIMEOUT_HOURS = 8

# ==================== ЭМОДЗИ ДЛЯ ПОКАЗАТЕЛЕЙ ====================

POPULATION_EMOJIS = {
    "population": "<:Job_spec:1267712580999184486>",
    "territory": "<:pp:1487015341883130027>",
    "stability": "<:crisis:1487167453443391509>",
    "government": "<:government:1487167580350451804>",
    "ruling_party": "<:partia:1487365868676448327>",
    "popularity": "<:vvp:1487360602367070400>",
    "gdp": "<:vvp:1487360602367070400>",
    "budget": "<:money:1429345094695129088>",
    "army": "<:army:1487330495082528829>",
    "experience": "<:Manpower:1256977159356940311>",
    "happiness": "<:social:1487167248908156988>",
    "trust": "<:social:1487167248908156988>",
    "efficiency": "<:zakon:1487365783385411626>",
    "employed": "<:immigration:1492868112901472256>",
    "unemployed": "<:immigration:1492868112901472256>",
    "unemployment_rate": "<:immigration:1492868112901472256>",
    "salary": "<:size_pops_mult:1471574910580297850>",
    "income": "<:money:1429345094695129088>",
    "savings": "<:money:1429345094695129088>",
    "industry": "<:construction_repair:1492879195657732256>",
    "energy": "<:Nuclear_reactor:1492864507591262208>",
    "tech": "<:economic_crisis:1492880645733617667>",
    "oil_gas": "<:big_fuel_reserves:1492880440128704583>",
    "mining": "<:build_supply:1492880349842243795>",
    "corporations": "<:office_center:1492908676824957079>",
    "government_sector": "<:government:1487167580350451804>",
    "small_business": "🏪",
    "services": "🏨",
    "retail": "🛍️",
    "transport": "<:logistic:1492864675808022628>",
    "construction": "🏗️",
    "agriculture": "🌾",
    "birth_rate": "👶",
    "death_rate": "<:smert:1492913346859765892>",
    "growth": "📈",
    "development": "<:gold_price:1492880036792107008>",
    "gdp_per_capita": "<:eco_baff:1492879901760421888>",
    "real_gdp": "<:eco_baff:1492879901760421888>",
}


def get_random_expert_image() -> str:
    """Возвращает случайную картинку для логов специалистов"""
    return random.choice(EXPERT_IMAGES)


# ==================== БАЗОВЫЕ ПОТРЕБНОСТИ ====================

BASE_POPULATION_NEEDS = {
    "food_products": 0.15, "clothing": 0.08, "medical_supplies": 0.01,
    "household_goods": 0.02, "consumer_electronics": 0.01, "smartphones": 0.008,
    "computers": 0.003, "software": 0.02, "buses": 0.00003, "cars": 0.003,
    "furniture": 0.005, "telecom_services": 0.3, "internet_services": 0.3,
    "mobile_services": 0.3, "streaming": 0.15, "banking": 0.3, "insurance": 0.1,
    "healthcare_services": 0.08, "education": 0.04, "entertainment": 0.2
}

INCOME_ELASTICITY = {
    "food_products": 0.2, "clothing": 0.4, "consumer_electronics": 1.2,
    "medical_supplies": 0.3, "furniture": 0.8, "household_goods": 0.5,
    "buses": 0.2, "cars": 1.5, "smartphones": 1.3, "computers": 1.2,
    "software": 0.9, "telecom_services": 0.3, "internet_services": 0.4,
    "mobile_services": 0.5, "streaming": 1.1, "banking": 0.3, "insurance": 0.6,
    "healthcare_services": 0.3, "education": 0.7, "entertainment": 1.4
}

MINIMUM_WAGE = {
    "США": 15000, "Россия": 3000, "Китай": 2500, "Германия": 20000,
    "Великобритания": 18000, "Франция": 19000, "Япония": 17000, "Израиль": 16000,
    "Украина": 1500, "Иран": 1000, "Беларусь": 1500, "Норвегия": 35000,
    "КНДР": 100, "Турция": 4000, "Сирия": 500, "Канада": 23000,
    "Польша": 8000, "Бразилия": 3000, "Швеция": 25000, "Финляндия": 24000,
    "Швейцария": 40000, "Египет": 1500
}

PPP_ADJUSTMENT = {
    "США": 1.0, "Россия": 0.65, "Китай": 0.55, "Германия": 0.95,
    "Великобритания": 0.9, "Франция": 0.92, "Япония": 0.88, "Израиль": 0.85,
    "Украина": 0.35, "Иран": 0.4, "Беларусь": 0.45, "Норвегия": 1.05,
    "КНДР": 0.15, "Турция": 0.5, "Сирия": 0.2, "Канада": 0.98,
    "Польша": 0.6, "Бразилия": 0.48, "Швеция": 0.96, "Финляндия": 0.94,
    "Швейцария": 1.1, "Египет": 0.3
}

# ==================== ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ КОЛИЧЕСТВА АКТИВОВ ====================

def get_asset_total(asset_data, owner_country: str = None) -> int:
    """
    Возвращает общее количество активов с учётом нового формата ownership.
    Если owner_country указан, возвращает только активы этой страны.
    """
    if asset_data is None:
        return 0
    
    if isinstance(asset_data, dict) and "ownership" in asset_data:
        ownership = asset_data["ownership"]
        if owner_country:
            return ownership.get(owner_country, 0)
        else:
            return sum(ownership.values())
    elif isinstance(asset_data, (int, float)):
        return int(asset_data)
    else:
        return 0


# ==================== ДАННЫЕ О СПЕЦИАЛИСТАХ ====================

EXPERT_TYPES = {
    "industrial_workers": {
        "name": "Промышленные рабочие", "emoji": "🏭", "bonus_type": "industrial_production",
        "base_bonus": 0.05, "cost_per_person": 1200, "can_export": True
    },
    "engineers": {
        "name": "Инженеры", "emoji": "⚙️", "bonus_type": "engineering",
        "base_bonus": 0.08, "cost_per_person": 1500, "can_export": True
    },
    "scientists": {
        "name": "Учёные", "emoji": "🔬", "bonus_type": "research",
        "base_bonus": 0.10, "cost_per_person": 2000, "can_export": True
    },
    "it_professionals": {
        "name": "IT-специалисты", "emoji": "💻", "bonus_type": "tech",
        "base_bonus": 0.12, "cost_per_person": 1800, "can_export": True
    },
    "medical_staff": {
        "name": "Медицинский персонал", "emoji": "🏥", "bonus_type": "healthcare",
        "base_bonus": 0.06, "cost_per_person": 1400, "can_export": True
    },
    "teachers": {
        "name": "Преподаватели", "emoji": "📚", "bonus_type": "education",
        "base_bonus": 0.07, "cost_per_person": 1700, "can_export": True
    },
    "construction_workers": {
        "name": "Строители", "emoji": "🏗️", "bonus_type": "construction",
        "base_bonus": 0.04, "cost_per_person": 1000, "can_export": True
    },
    "transport_workers": {
        "name": "Транспортники", "emoji": "🚚", "bonus_type": "logistics",
        "base_bonus": 0.03, "cost_per_person": 900, "can_export": True
    },
    "agricultural_workers": {
        "name": "Сельхозработники", "emoji": "🌾", "bonus_type": "agriculture",
        "base_bonus": 0.04, "cost_per_person": 800, "can_export": True
    }
}

EXPERT_DATA_FILE = 'exported_experts.json'
EXPERT_REQUESTS_FILE = 'expert_requests.json'


def load_exported_experts():
    try:
        with open(EXPERT_DATA_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"exported": {}, "guards": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"exported": {}, "guards": {}}


def save_exported_experts(data):
    with open(EXPERT_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_expert_requests():
    try:
        with open(EXPERT_REQUESTS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"pending": [], "completed": [], "rejected": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"pending": [], "completed": [], "rejected": []}


def save_expert_requests(data):
    with open(EXPERT_REQUESTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ СО СПЕЦИАЛИСТАМИ ====================

def get_country_experts(sender_country: str, receiver_country: str = None) -> Dict:
    data = load_exported_experts()
    if receiver_country:
        return data["exported"].get(sender_country, {}).get(receiver_country, {})
    return data["exported"].get(sender_country, {})


def get_available_experts(player_data) -> Dict[str, int]:
    employed = player_data["population_data"].get("employed", 0)
    if employed == 0:
        return {}
    
    professions = player_data["state"].get("demographics", {}).get("professions", {})
    total_professions = sum(professions.values())
    
    result = {}
    for exp_id, exp in EXPERT_TYPES.items():
        if exp["can_export"]:
            if exp_id in professions and total_professions > 0:
                ratio = professions[exp_id] / total_professions
                result[exp_id] = int(employed * ratio)
            else:
                result[exp_id] = int(employed * 0.02)
    
    return result


def recall_experts(sender: str, receiver: str, expert_type: str, quantity: int, player_data: Dict) -> Tuple[bool, str]:
    data = load_exported_experts()
    
    if sender not in data["exported"]:
        return False, "Нет отправленных специалистов"
    if receiver not in data["exported"][sender]:
        return False, f"Нет специалистов в {receiver}"
    if expert_type not in data["exported"][sender][receiver]:
        return False, f"Нет {EXPERT_TYPES[expert_type]['name']} в {receiver}"
    
    current = data["exported"][sender][receiver][expert_type]
    if current < quantity:
        return False, f"Доступно для отзыва: {current}"
    
    data["exported"][sender][receiver][expert_type] -= quantity
    
    if data["exported"][sender][receiver][expert_type] <= 0:
        del data["exported"][sender][receiver][expert_type]
    if not data["exported"][sender][receiver]:
        del data["exported"][sender][receiver]
    if not data["exported"][sender]:
        del data["exported"][sender]
    
    save_exported_experts(data)
    
    return True, f"Отозвано {quantity} {EXPERT_TYPES[expert_type]['name']} из {receiver}"


def create_expert_request(sender: str, receiver: str, expert_type: str, quantity: int, 
                          sender_data: Dict, receiver_id: int, bot) -> Dict:
    cost = EXPERT_TYPES[expert_type]["cost_per_person"] * quantity
    
    request = {
        "id": f"{sender}_{receiver}_{expert_type}_{datetime.now().timestamp()}",
        "sender": sender,
        "receiver": receiver,
        "receiver_id": receiver_id,
        "expert_type": expert_type,
        "expert_name": EXPERT_TYPES[expert_type]["name"],
        "expert_emoji": EXPERT_TYPES[expert_type]["emoji"],
        "quantity": quantity,
        "cost": cost,
        "created_at": str(datetime.now()),
        "expires_at": str(datetime.now() + timedelta(hours=EXPERT_REQUEST_TIMEOUT_HOURS)),
        "status": "pending"
    }
    
    data = load_expert_requests()
    data["pending"].append(request)
    save_expert_requests(data)
    
    return request


def accept_expert_request(request_id: str, receiver_data: Dict) -> Tuple[bool, str]:
    data = load_expert_requests()
    
    request = None
    for r in data["pending"]:
        if r["id"] == request_id:
            request = r
            break
    
    if not request:
        return False, "Запрос не найден"
    
    if request["status"] != "pending":
        return False, "Запрос уже обработан"
    
    cost = request["cost"]
    current_budget = get_budget(receiver_data["economy"])
    
    if current_budget < cost:
        return False, f"Недостаточно средств! Нужно: ${cost:,.0f}"
    
    from utils import subtract_from_budget
    subtract_from_budget(receiver_data["economy"], cost)
    
    exported_data = load_exported_experts()
    sender = request["sender"]
    receiver = request["receiver"]
    exp_type = request["expert_type"]
    qty = request["quantity"]
    
    if sender not in exported_data["exported"]:
        exported_data["exported"][sender] = {}
    if receiver not in exported_data["exported"][sender]:
        exported_data["exported"][sender][receiver] = {}
    if exp_type not in exported_data["exported"][sender][receiver]:
        exported_data["exported"][sender][receiver][exp_type] = 0
    
    exported_data["exported"][sender][receiver][exp_type] += qty
    save_exported_experts(exported_data)
    
    request["status"] = "accepted"
    request["accepted_at"] = str(datetime.now())
    data["completed"].append(request)
    data["pending"].remove(request)
    save_expert_requests(data)
    
    return True, f"Специалисты приняты. Оплачено: ${cost:,.0f}"


def reject_expert_request(request_id: str) -> Tuple[bool, str]:
    data = load_expert_requests()
    
    request = None
    for r in data["pending"]:
        if r["id"] == request_id:
            request = r
            break
    
    if not request:
        return False, "Запрос не найден"
    
    if request["status"] != "pending":
        return False, "Запрос уже обработан"
    
    request["status"] = "rejected"
    request["rejected_at"] = str(datetime.now())
    data["rejected"].append(request)
    data["pending"].remove(request)
    save_expert_requests(data)
    
    return True, "Запрос отклонён"


def process_expired_requests(bot):
    data = load_expert_requests()
    now = datetime.now()
    expired = []
    
    for request in data["pending"]:
        expires_at = datetime.fromisoformat(request["expires_at"])
        if expires_at <= now:
            expired.append(request)
    
    for request in expired:
        request["status"] = "expired"
        request["expired_at"] = str(now)
        data["rejected"].append(request)
        data["pending"].remove(request)
        
        asyncio.create_task(send_expired_notification(bot, request))
    
    if expired:
        save_expert_requests(data)
    
    return len(expired)


async def send_expired_notification(bot, request):
    """Отправляет лог о просроченном запросе с пингом получателя"""
    channel = bot.get_channel(EXPERT_LOG_CHANNEL_ID)
    if not channel:
        return
    
    receiver_user = None
    try:
        receiver_user = await bot.fetch_user(request["receiver_id"])
    except:
        pass
    
    ping_text = f"{receiver_user.mention} " if receiver_user else ""
    
    embed = discord.Embed(
        title="❌ ЗАПРОС ОТКЛОНЁН",
        description=f"{ping_text}**{request['receiver']}** не ответил на запрос о приёме специалистов в течение {EXPERT_REQUEST_TIMEOUT_HOURS} часов.",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.set_image(url=get_random_expert_image())
    
    embed.add_field(name="Отправитель", value=request["sender"], inline=True)
    embed.add_field(name="Получатель", value=request["receiver"], inline=True)
    embed.add_field(name="Тип специалистов", value=f"{request['expert_emoji']} {request['expert_name']}", inline=True)
    embed.add_field(name="Количество", value=f"{format_number(request['quantity'])} чел.", inline=True)
    
    await channel.send(embed=embed)


async def send_expert_request_log(bot, request: Dict):
    """Отправляет лог о запросе с кнопками и пингом получателя"""
    channel = bot.get_channel(EXPERT_LOG_CHANNEL_ID)
    if not channel:
        return
    
    receiver_user = None
    try:
        receiver_user = await bot.fetch_user(request["receiver_id"])
    except:
        pass
    
    ping_text = f"{receiver_user.mention} " if receiver_user else ""
    
    embed = discord.Embed(
        title="📋 ЗАПРОС НА ПРИЁМ СПЕЦИАЛИСТОВ",
        description=f"{ping_text}**{request['sender']}** предлагает направить специалистов в **{request['receiver']}**",
        color=DARK_THEME_COLOR,
        timestamp=datetime.now()
    )
    embed.set_image(url=get_random_expert_image())
    
    embed.add_field(name="Тип специалистов", value=f"{request['expert_emoji']} {request['expert_name']}", inline=True)
    embed.add_field(name="Количество", value=f"{format_number(request['quantity'])} чел.", inline=True)
    embed.add_field(name="Стоимость для принимающей страны", value=f"${request['cost']:,.0f}", inline=True)
    embed.add_field(name="Время на ответ", value=f"{EXPERT_REQUEST_TIMEOUT_HOURS} часов", inline=True)
    
    view = ExpertRequestView(request["id"], request["receiver_id"])
    
    await channel.send(embed=embed, view=view)


async def send_accept_log(bot, request: Dict):
    """Отправляет лог о принятии специалистов с пингом отправителя"""
    channel = bot.get_channel(EXPERT_LOG_CHANNEL_ID)
    if not channel:
        return
    
    sender_user = None
    try:
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == request["sender"]:
                sender_id = int(data.get("assigned_to", 0))
                if sender_id:
                    sender_user = await bot.fetch_user(sender_id)
                    break
    except:
        pass
    
    ping_text = f"{sender_user.mention} " if sender_user else ""
    
    embed = discord.Embed(
        title="✅ СПЕЦИАЛИСТЫ ПРИНЯТЫ",
        description=f"{ping_text}**{request['receiver']}** принял специалистов из **{request['sender']}**",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.set_image(url=get_random_expert_image())
    
    embed.add_field(name="Тип специалистов", value=f"{request['expert_emoji']} {request['expert_name']}", inline=True)
    embed.add_field(name="Количество", value=f"{format_number(request['quantity'])} чел.", inline=True)
    embed.add_field(name="Стоимость", value=f"${request['cost']:,.0f}", inline=True)
    
    await channel.send(embed=embed)


async def send_reject_log(bot, request: Dict):
    """Отправляет лог об отказе специалистов с пингом отправителя"""
    channel = bot.get_channel(EXPERT_LOG_CHANNEL_ID)
    if not channel:
        return
    
    sender_user = None
    try:
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == request["sender"]:
                sender_id = int(data.get("assigned_to", 0))
                if sender_id:
                    sender_user = await bot.fetch_user(sender_id)
                    break
    except:
        pass
    
    ping_text = f"{sender_user.mention} " if sender_user else ""
    
    embed = discord.Embed(
        title="❌ СПЕЦИАЛИСТЫ ОТКЛОНЕНЫ",
        description=f"{ping_text}**{request['receiver']}** отклонил запрос на приём специалистов из **{request['sender']}**",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.set_image(url=get_random_expert_image())
    
    embed.add_field(name="Тип специалистов", value=f"{request['expert_emoji']} {request['expert_name']}", inline=True)
    embed.add_field(name="Количество", value=f"{format_number(request['quantity'])} чел.", inline=True)
    
    await channel.send(embed=embed)


async def send_recall_log(bot, sender: str, receiver: str, expert_type: str, quantity: int):
    """Отправляет лог об отзыве специалистов с пингом отправителя и получателя"""
    channel = bot.get_channel(EXPERT_LOG_CHANNEL_ID)
    if not channel:
        return
    
    expert = EXPERT_TYPES[expert_type]
    
    sender_user = None
    try:
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == sender:
                sender_id = int(data.get("assigned_to", 0))
                if sender_id:
                    sender_user = await bot.fetch_user(sender_id)
                    break
    except:
        pass
    
    receiver_user = None
    try:
        states = load_states()
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == receiver:
                receiver_id = int(data.get("assigned_to", 0))
                if receiver_id:
                    receiver_user = await bot.fetch_user(receiver_id)
                    break
    except:
        pass
    
    ping_text = ""
    if sender_user:
        ping_text += f"{sender_user.mention} "
    if receiver_user:
        ping_text += f"{receiver_user.mention} "
    
    embed = discord.Embed(
        title="📤 ОТЗЫВ СПЕЦИАЛИСТОВ",
        description=f"{ping_text}**{sender}** отзывает специалистов из **{receiver}**",
        color=DARK_THEME_COLOR,
        timestamp=datetime.now()
    )
    embed.set_image(url=get_random_expert_image())
    
    embed.add_field(name="Тип специалистов", value=f"{expert['emoji']} {expert['name']}", inline=True)
    embed.add_field(name="Количество", value=f"{format_number(quantity)} чел.", inline=True)
    
    await channel.send(embed=embed)


# ==================== КЛАСС ДЛЯ КНОПОК ЗАПРОСА ====================

class ExpertRequestView(View):
    def __init__(self, request_id: str, receiver_id: int):
        super().__init__(timeout=EXPERT_REQUEST_TIMEOUT_HOURS * 3600)
        self.request_id = request_id
        self.receiver_id = receiver_id
    
    @discord.ui.button(label="✅ Принять специалистов", style=discord.ButtonStyle.success)
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message("❌ Это не ваш запрос!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        states = load_states()
        receiver_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(interaction.user.id):
                receiver_data = data
                break
        
        if not receiver_data:
            await interaction.followup.send("❌ Ошибка загрузки данных!", ephemeral=True)
            return
        
        success, msg = accept_expert_request(self.request_id, receiver_data)
        
        if success:
            save_states(states)
            
            requests = load_expert_requests()
            request = None
            for r in requests["completed"]:
                if r["id"] == self.request_id:
                    request = r
                    break
            
            if request:
                await send_accept_log(interaction.client, request)
            
            embed = discord.Embed(
                title="✅ СПЕЦИАЛИСТЫ ПРИНЯТЫ",
                description=msg,
                color=DARK_THEME_COLOR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
        else:
            await interaction.followup.send(f"❌ {msg}", ephemeral=True)
    
    @discord.ui.button(label="❌ Отказаться", style=discord.ButtonStyle.danger)
    async def reject_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.receiver_id:
            await interaction.response.send_message("❌ Это не ваш запрос!", ephemeral=True)
            return
        
        success, msg = reject_expert_request(self.request_id)
        
        if success:
            requests = load_expert_requests()
            request = None
            for r in requests["rejected"]:
                if r["id"] == self.request_id:
                    request = r
                    break
            
            if request:
                await send_reject_log(interaction.client, request)
            
            embed = discord.Embed(
                title="❌ ЗАПРОС ОТКЛОНЁН",
                description=msg,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
        else:
            await interaction.response.send_message(f"❌ {msg}", ephemeral=True)


# ==================== ФУНКЦИИ ДЛЯ РАСЧЁТА ЗАНЯТОСТИ ====================

def calculate_jobs_from_infrastructure(player_data) -> Dict:
    from infra_build import load_infrastructure, get_all_regions_from_country
    
    jobs = {"military": 0, "civilian": 0, "shipyards": 0, "refineries": 0,
            "power": 0, "data_centers": 0, "oil_depots": 0, "office_centers": 0,
            "oil_extraction": 0, "gas_extraction": 0, "mining": 0}
    
    infra = load_infrastructure()
    country = player_data["state"]["statename"]
    
    cid = None
    for cid_key, data in infra["infrastructure"].items():
        if data.get("country") == country:
            cid = cid_key
            break
    
    if cid:
        regions = get_all_regions_from_country(infra, cid)
        for rname, rdata in regions.items():
            if "military_factories" in rdata:
                jobs["military"] += get_asset_total(rdata["military_factories"]) * 2000
            if "civilian_factories" in rdata:
                jobs["civilian"] += get_asset_total(rdata["civilian_factories"]) * 3000
            if "shipyards" in rdata:
                jobs["shipyards"] += get_asset_total(rdata["shipyards"]) * 5000
            if "refineries" in rdata:
                jobs["refineries"] += get_asset_total(rdata["refineries"]) * 600
            if "oil_depots" in rdata:
                jobs["oil_depots"] += get_asset_total(rdata["oil_depots"]) * 50
            if "internet_infrastructure" in rdata:
                jobs["data_centers"] += get_asset_total(rdata["internet_infrastructure"]) * 200
            
            for plant, jobs_plant in [("thermal_power", 250), ("nuclear_power", 400),
                                      ("hydro_power", 200), ("wind_power", 150), ("solar_power", 100)]:
                if plant in rdata:
                    jobs["power"] += get_asset_total(rdata[plant]) * jobs_plant
            
            if "office_centers" in rdata:
                cnt = get_asset_total(rdata["office_centers"])
                pop = rdata.get("population", 0)
                if cnt > 0 and pop > 0:
                    base = cnt * 4000
                    jobs["office_centers"] += base + int(base * (min(2.0, pop / 500000) - 1))
    
    resources = player_data.get("resources", {})
    oil = resources.get("oil", 0)
    if oil > 0:
        jobs["oil_extraction"] = max(500, int(oil / 10) * 50)
    gas = resources.get("gas", 0)
    if gas > 0:
        jobs["gas_extraction"] = max(200, int(gas / 10) * 40)
    for r, mult in [("coal", 30), ("steel", 20), ("aluminum", 15), ("uranium", 25), ("rare_metals", 20)]:
        amt = resources.get(r, 0)
        if amt > 0:
            jobs["mining"] += max(50 if r == "coal" else 20, int(amt / 10) * mult)
    
    return jobs


def calculate_corporation_jobs(player_data) -> int:
    country = player_data["state"]["statename"]
    total = 0
    for corp in get_civil_corporations_by_country(country).values():
        state = initialize_corporation_state(corp)
        total += 1000 + int(sum(state.inventory.values()) / 10) + int(state.budget / 1000000)
    return total


def calculate_employment(player_data) -> Dict:
    pop = player_data["state"]["population"]
    working_age = int(pop * 0.62)
    
    jobs = calculate_jobs_from_infrastructure(player_data)
    corp_jobs = calculate_corporation_jobs(player_data)
    professions = player_data["state"].get("demographics", {}).get("professions", {})
    gov_jobs = professions.get("officials", 0)
    
    service_jobs = int(pop * 0.28)
    retail_jobs = int(pop * 0.07)
    transport_jobs = int(pop * 0.03)
    construction_jobs = int(pop * 0.03)
    agriculture_jobs = int(pop * 0.01)
    small_business_jobs = int(pop * 0.05)
    
    industrial_jobs = (jobs["military"] + jobs["civilian"] + jobs["shipyards"] + 
                       jobs["refineries"] + jobs["oil_extraction"] + jobs["gas_extraction"] + 
                       jobs["mining"])
    tech_jobs = jobs["data_centers"] + jobs["office_centers"]
    energy_jobs = jobs["power"]
    
    formal = (industrial_jobs + energy_jobs + tech_jobs + corp_jobs + gov_jobs + 
              service_jobs + retail_jobs + transport_jobs + construction_jobs + 
              agriculture_jobs + small_business_jobs)
    
    total_jobs = formal
    
    employed = min(total_jobs, working_age)
    unemployed = working_age - employed
    unemployment = (unemployed / working_age) * 100 if working_age > 0 else 0
    
    return {
        "working_age": working_age,
        "employed": employed,
        "unemployed": unemployed,
        "unemployment_rate": unemployment,
        "jobs_available": total_jobs,
        "corporation_jobs": corp_jobs,
        "sector_breakdown": {
            f"{POPULATION_EMOJIS.get('industry', '🏭')} Промышленность": industrial_jobs,
            f"{POPULATION_EMOJIS.get('energy', '⚡')} Энергетика": energy_jobs,
            f"{POPULATION_EMOJIS.get('tech', '💻')} Технологии": tech_jobs,
            f"{POPULATION_EMOJIS.get('oil_gas', '🛢️')} Нефть и газ": jobs["oil_extraction"] + jobs["gas_extraction"] + jobs["refineries"] + jobs["oil_depots"],
            f"{POPULATION_EMOJIS.get('mining', '⛏️')} Добыча": jobs["mining"],
            f"{POPULATION_EMOJIS.get('corporations', '🏢')} Корпорации": corp_jobs,
            f"{POPULATION_EMOJIS.get('government_sector', '🏛️')} Госсектор": gov_jobs,
            f"{POPULATION_EMOJIS.get('small_business', '🏪')} Малый бизнес": small_business_jobs,
            f"{POPULATION_EMOJIS.get('services', '🏨')} Услуги": service_jobs,
            f"{POPULATION_EMOJIS.get('retail', '🛍️')} Ритейл": retail_jobs,
            f"{POPULATION_EMOJIS.get('transport', '🚚')} Транспорт": transport_jobs,
            f"{POPULATION_EMOJIS.get('construction', '🏗️')} Строительство": construction_jobs,
            f"{POPULATION_EMOJIS.get('agriculture', '🌾')} Сельское хозяйство": agriculture_jobs
        },
        "labor_force_participation": (employed / working_age) * 100 if working_age > 0 else 0
    }


def calculate_average_salary(player_data, emp) -> float:
    economy = player_data["economy"]
    
    base = economy.get("wage_local", economy.get("wage", 50000))
    gdp = get_gdp(economy)
    pop = player_data["state"]["population"]
    gdp_cap = gdp / pop if pop > 0 else 0
    ur = emp["unemployment_rate"]
    
    mult = 1.0
    if ur > 8:
        mult = 1.0 - (ur - 8) / 200
    elif ur < 3:
        mult = 1.0 + (3 - ur) / 100
    
    gdp_factor = min(2.0, max(0.5, gdp_cap / 30000))
    infl = 1.0 + get_inflation(economy) / 100
    
    return int(base * mult * gdp_factor * infl)


def calculate_population_income(player_data, emp, salary) -> Dict:
    employed = emp["employed"]
    salary_fund = employed * salary
    social = player_data["expenses"].get("social_security", 0)
    gdp = get_gdp(player_data["economy"])
    business = gdp * 0.08
    dividends = 0
    for corp in get_civil_corporations_by_country(player_data["state"]["statename"]).values():
        state = initialize_corporation_state(corp)
        dividends += state.budget * 0.05 * 0.1
    
    total = salary_fund + social + business + dividends
    tax_rate = player_data["economy"].get("taxes", {}).get("income", {}).get("rate", 13)
    tax = total * tax_rate / 100
    
    return {"after_tax": total - tax, "income_tax": tax}


def calculate_consumption_needs(player_data, income) -> Dict:
    pop = player_data["state"]["population"]
    income_cap = income["after_tax"] / pop if pop > 0 else 0
    base = MINIMUM_WAGE.get(player_data["state"]["statename"], 10000)
    wealth = max(0.5, min(3.0, income_cap / base))
    
    economy = player_data["economy"]
    cost = economy.get("cost_of_living_local", economy.get("cost_of_living", 100))
    wealth = wealth * (100 / cost) if cost > 0 else wealth
    
    needs = {}
    for prod, base_amt in BASE_POPULATION_NEEDS.items():
        el = INCOME_ELASTICITY.get(prod, 0.5)
        needs[prod] = base_amt * (wealth ** el) * pop
    return needs


def get_product_price(product_type: str) -> float:
    default_prices = {
        "food_products": 100, "clothing": 50, "medical_supplies": 30,
        "household_goods": 50, "consumer_electronics": 500, "smartphones": 500,
        "computers": 1000, "software": 100, "buses": 50000, "cars": 15000,
        "furniture": 200, "telecom_services": 30, "internet_services": 40,
        "mobile_services": 35, "streaming": 10, "banking": 5, "insurance": 200,
        "healthcare_services": 300, "education": 500, "entertainment": 50
    }
    try:
        all_corps = get_all_civil_corporations()
        prices = []
        for corp in all_corps:
            if product_type in corp.products:
                price = corp.products[product_type].get('price', 0)
                if price > 0:
                    prices.append(price)
        if prices:
            return sum(prices) / len(prices)
    except:
        pass
    return default_prices.get(product_type, 100)


def calculate_consumption_simulation(player_data, needs, income) -> Dict:
    budget = income["after_tax"]
    total_spent = 0
    consumption = {}
    needs_met = {}
    
    order = ["food_products", "medical_supplies", "clothing", "household_goods",
             "healthcare_services", "education", "telecom_services", "internet_services",
             "mobile_services", "banking", "insurance", "cars", "consumer_electronics",
             "smartphones", "computers", "furniture", "streaming", "entertainment"]
    
    remaining = budget
    
    for prod in order:
        if prod not in needs:
            continue
        needed = needs[prod]
        if needed <= 0:
            needs_met[prod] = 100
            continue
        
        price = get_product_price(prod)
        if price <= 0:
            needs_met[prod] = 0
            continue
        
        max_buy = int(remaining / price) if price > 0 else 0
        bought = min(needed, max_buy)
        
        if bought > 0:
            spent = bought * price
            remaining -= spent
            total_spent += spent
            consumption[prod] = bought
            needs_met[prod] = (bought / needed) * 100 if needed > 0 else 100
        else:
            needs_met[prod] = 0
    
    vat_rate = player_data["economy"].get("taxes", {}).get("vat", {}).get("rate", 18)
    vat = total_spent * vat_rate / 100
    
    return {"total_spent": total_spent, "consumption": consumption, "needs_met": needs_met, "vat": vat}


def update_social_indicators(player_data, emp, cons, inc):
    ur = emp["unemployment_rate"]
    needs = cons.get("needs_met", {})
    
    stability = player_data["state"].get("stability", 50)
    happiness = player_data["state"].get("happiness", 50)
    trust = player_data["state"].get("trust", 50)
    
    if ur > 8:
        dec = min(5.0, (ur - 8) / 2)
        stability -= dec
        happiness -= dec
        trust -= min(3.0, (ur - 8) / 3)
    elif ur < 3:
        inc_val = min(3.0, (3 - ur) / 2)
        stability += inc_val
        happiness += inc_val
    
    if needs:
        avg = sum(needs.values()) / len(needs)
        if avg < 70:
            dec = min(5.0, (70 - avg) / 5)
            stability -= dec
            happiness -= dec
        elif avg > 90:
            inc_val = min(2.0, (avg - 90) / 10)
            stability += inc_val
            happiness += inc_val
    
    corp_count = len(get_civil_corporations_by_country(player_data["state"]["statename"]))
    happiness += min(5.0, corp_count / 20)
    
    economy = player_data["economy"]
    cost = economy.get("cost_of_living_local", economy.get("cost_of_living", 100))
    salary = player_data["population_data"].get("average_salary", 50000)
    power = salary / cost if cost > 0 else 500
    if power < 300:
        happiness -= min(5.0, (300 - power) / 30)
    elif power > 700:
        happiness += min(2.0, (power - 700) / 50)
    
    taxes = player_data["economy"].get("taxes", {})
    burden = taxes.get("income", {}).get("rate", 0) + taxes.get("vat", {}).get("rate", 0) * 0.5
    if burden > 40:
        happiness -= min(5.0, (burden - 40) / 5)
    
    if stability > 70:
        stability = max(70, stability - 0.5)
    if happiness > 70:
        happiness = max(70, happiness - 0.5)
    if stability < 30:
        stability = min(30, stability + 0.5)
    if happiness < 30:
        happiness = min(30, happiness + 0.5)
    
    player_data["state"]["stability"] = max(0.0, min(100.0, stability))
    player_data["state"]["happiness"] = max(0.0, min(100.0, happiness))
    player_data["state"]["trust"] = max(0.0, min(100.0, trust))
    player_data["politics"]["popularity"] = max(0.0, min(95.0, happiness * 0.6 + stability * 0.4))


def update_population(player_data, is_initialization: bool = False) -> Dict:
    emp = calculate_employment(player_data)
    salary = calculate_average_salary(player_data, emp)
    inc = calculate_population_income(player_data, emp, salary)
    needs = calculate_consumption_needs(player_data, inc)
    cons = calculate_consumption_simulation(player_data, needs, inc)
    
    # Сохраняем рассчитанную зарплату в economy для синхронизации
    if "local_currency" in player_data["economy"]:
        player_data["economy"]["wage_local"] = salary
    else:
        player_data["economy"]["wage"] = salary
    
    old_savings = player_data["population_data"].get("savings", 0) if "population_data" in player_data else 0
    new_savings = old_savings + inc["after_tax"] - cons["total_spent"]
    
    if "population_data" not in player_data:
        player_data["population_data"] = {}
    
    player_data["population_data"].update({
        "employed": emp["employed"], "unemployed": emp["unemployed"],
        "unemployment_rate": emp["unemployment_rate"],
        "labor_force_participation": emp["labor_force_participation"],
        "average_salary": salary, "total_income": inc["after_tax"],
        "total_income_before_tax": inc["after_tax"] + inc["income_tax"],
        "income_tax_paid": inc["income_tax"],
        "dividend_income": 0, "savings": new_savings,
        "consumption": cons["consumption"], "needs_met": cons["needs_met"],
        "total_spent": cons["total_spent"], "vat_paid": cons["vat"],
        "sector_breakdown": emp["sector_breakdown"],
        "corporation_jobs": emp["corporation_jobs"],
        "last_update": str(datetime.now())
    })
    
    if not is_initialization:
        add_to_budget(player_data["economy"], inc["income_tax"] + cons["vat"])
    
    update_social_indicators(player_data, emp, cons, inc)
    
    return {
        "country": player_data["state"]["statename"],
        "employment_rate": 100 - emp["unemployment_rate"],
        "avg_salary": salary,
        "total_income": inc["after_tax"],
        "total_spent": cons["total_spent"],
        "savings": new_savings,
        "taxes_collected": inc["income_tax"] + cons["vat"],
        "needs_met_avg": sum(cons["needs_met"].values()) / len(cons["needs_met"]) if cons["needs_met"] else 0,
        "labor_force_participation": emp["labor_force_participation"],
        "corporation_jobs": emp["corporation_jobs"]
    }


def calculate_gdp_per_capita(player_data) -> float:
    gdp = get_gdp(player_data["economy"])
    pop = player_data["state"]["population"]
    return gdp / pop if pop > 0 else 0


def calculate_real_gdp_per_capita(player_data) -> float:
    country = player_data["state"]["statename"]
    return calculate_gdp_per_capita(player_data) * PPP_ADJUSTMENT.get(country, 0.5)


def calculate_consumption_per_capita(player_data) -> Dict[str, float]:
    pop = player_data["state"]["population"]
    if pop <= 0:
        return {}
    consumption = player_data["population_data"].get("consumption", {})
    resources = player_data.get("resources", {})
    result = {}
    for product, amount in consumption.items():
        name = CIVIL_PRODUCT_NAMES.get(product, product)
        result[name] = amount / pop
    resource_names = {
        "oil": "Нефть", "gas": "Газ", "coal": "Уголь", "steel": "Сталь",
        "aluminum": "Алюминий", "uranium": "Уран", "rare_metals": "Редкие металлы",
        "food": "Продовольствие", "electronics": "Электроника"
    }
    for res, amount in resources.items():
        if res in resource_names and amount > 0:
            result[resource_names[res]] = amount / pop
    return result


# ==================== ФОНОВАЯ ЗАДАЧА ====================

async def population_update_loop(bot_instance):
    await bot_instance.wait_until_ready()
    last = None
    
    while not bot_instance.is_closed():
        try:
            now = datetime.now()
            
            expired = process_expired_requests(bot_instance)
            if expired > 0:
                print(f"⏰ Обработано {expired} просроченных запросов на специалистов")
            
            if last is None or (now - last).days >= 3:
                print(f"👥 Обновление населения: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                states = load_states()
                for pid, data in states["players"].items():
                    if "assigned_to" in data:
                        try:
                            update_population(data, is_initialization=False)
                        except Exception as e:
                            print(f"Ошибка {data.get('state', {}).get('statename', pid)}: {e}")
                save_states(states)
                last = now
            
            await asyncio.sleep(600)
        except Exception as e:
            print(f"Ошибка цикла: {e}")
            await asyncio.sleep(600)


# ==================== МЕНЮ ====================

async def show_population_menu(interaction_or_ctx, user_id: int):
    from utils import load_states
    
    states = load_states()
    data = None
    for d in states["players"].values():
        if d.get("assigned_to") == str(user_id):
            data = d
            break
    if not data:
        msg = "У вас нет государства!"
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message(msg, ephemeral=True)
        else:
            await interaction_or_ctx.send(msg)
        return
    
    emp = calculate_employment(data)
    salary = calculate_average_salary(data, emp)
    gdp_cap = calculate_gdp_per_capita(data)
    real_cap = calculate_real_gdp_per_capita(data)
    currency = get_currency_code(data["economy"])
    
    embed = discord.Embed(
        title=f"👥 НАСЕЛЕНИЕ | {data['state']['statename']}",
        description=f"Всего жителей: **{format_number(data['state']['population'])}** чел.",
        color=DARK_THEME_COLOR
    )
    embed.set_image(url=POPULATION_IMAGE_URL)
    
    embed.add_field(
        name="📊 РЫНОК ТРУДА",
        value=f"{POPULATION_EMOJIS.get('employed', '👷')} Работает: {format_number(emp['employed'])} чел.\n"
              f"{POPULATION_EMOJIS.get('unemployed', '🚫')} Безработных: {format_number(emp['unemployed'])} чел.\n"
              f"{POPULATION_EMOJIS.get('unemployment_rate', '📈')} Уровень безработицы: {emp['unemployment_rate']:.1f}%\n"
              f"🏭 Всего рабочих мест: {format_number(emp['jobs_available'])}\n"
              f"{POPULATION_EMOJIS.get('corporations', '🏢')} В корпорациях: {format_number(emp['corporation_jobs'])}",
        inline=True
    )
    
    embed.add_field(
        name="💰 ДОХОДЫ (за год)",
        value=f"{POPULATION_EMOJIS.get('salary', '💵')} Средняя зарплата: {format_billion(salary)} {currency}/год\n"
              f"{POPULATION_EMOJIS.get('income', '📥')} Доход населения: {format_billion(data['population_data'].get('total_income', 0))} {currency}/год\n"
              f"{POPULATION_EMOJIS.get('savings', '🏦')} Сбережения: {format_billion(data['population_data'].get('savings', 0))} {currency}",
        inline=True
    )
    
    embed.add_field(
        name="📈 СОЦИАЛЬНЫЕ ПОКАЗАТЕЛИ",
        value=f"{POPULATION_EMOJIS.get('happiness', '😊')} Счастье: {data['state']['happiness']:.1f}%\n"
              f"{POPULATION_EMOJIS.get('stability', '⚖️')} Стабильность: {data['state']['stability']:.1f}%\n"
              f"{POPULATION_EMOJIS.get('trust', '🤝')} Доверие: {data['state']['trust']:.1f}%\n"
              f"{POPULATION_EMOJIS.get('popularity', '📊')} Популярность: {data['politics']['popularity']:.1f}%",
        inline=True
    )
    
    sector_text = ""
    for sector, count in emp["sector_breakdown"].items():
        if count > 0:
            sector_text += f"{sector}: **{format_number(count)}**\n"
    if sector_text:
        embed.add_field(name="📊 СТРУКТУРА ЗАНЯТОСТИ", value=sector_text, inline=False)
    
    exported = get_country_experts(data["state"]["statename"])
    if exported:
        exp_text = ""
        for receiver, types in exported.items():
            for exp_type, count in types.items():
                if count > 0:
                    exp_name = EXPERT_TYPES[exp_type]["name"]
                    exp_emoji = EXPERT_TYPES[exp_type]["emoji"]
                    exp_text += f"{exp_emoji} {exp_name} в {receiver}: **{format_number(count)}**\n"
        if exp_text:
            embed.add_field(name="📤 СПЕЦИАЛИСТЫ ЗА ГРАНИЦЕЙ", value=exp_text, inline=False)
    
    view = PopulationMainView(user_id, data)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view)


class PopulationMainView(View):
    def __init__(self, user_id, data):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.data = data
    
    @discord.ui.button(label="На душу населения", style=discord.ButtonStyle.primary)
    async def per_capita(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        per = calculate_consumption_per_capita(self.data)
        gdp_cap = calculate_gdp_per_capita(self.data)
        real_cap = calculate_real_gdp_per_capita(self.data)
        salary = self.data["population_data"].get("average_salary", 0)
        currency = get_currency_code(self.data["economy"])
        
        embed = discord.Embed(
            title=f"📊 ПОТРЕБЛЕНИЕ НА ДУШУ | {self.data['state']['statename']}",
            description="Показатели на одного жителя в год",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=POPULATION_IMAGE_URL)
        
        embed.add_field(
            name="💰 ЭКОНОМИЧЕСКИЕ ПОКАЗАТЕЛИ",
            value=f"{POPULATION_EMOJIS.get('gdp_per_capita', '💵')} ВВП на душу: **{format_billion(gdp_cap)} {currency}**\n"
                  f"{POPULATION_EMOJIS.get('real_gdp', '🌍')} Реальный ВВП (ППС): **{format_billion(real_cap)} {currency}**\n"
                  f"{POPULATION_EMOJIS.get('salary', '💵')} Средняя зарплата: **{format_billion(salary)} {currency}/год**\n"
                  f"{POPULATION_EMOJIS.get('savings', '🏦')} Сбережения на душу: **{format_billion(self.data['population_data'].get('savings', 0) / max(1, self.data['state']['population']))} {currency}**",
            inline=False
        )
        
        if per:
            essentials = {}
            industry = {}
            services = {}
            for name, val in per.items():
                if name in ["Продовольствие", "Одежда", "Медикаменты", "Товары для дома"]:
                    essentials[name] = val
                elif name in ["Автомобили", "Электроника", "Смартфоны", "Компьютеры"]:
                    industry[name] = val
                elif name in ["Связь", "Интернет", "Стриминг", "Банкинг", "Страхование", "Медицина", "Образование", "Развлечения"]:
                    services[name] = val
            
            if essentials:
                text = "\n".join([f"{k}: {v:.2f} ед./год" for k, v in essentials.items()])
                embed.add_field(name="🍽️ ОСНОВНЫЕ ТОВАРЫ", value=text, inline=True)
            if industry:
                text = "\n".join([f"{k}: {v:.2f} ед./год" for k, v in industry.items() if v >= 0.01])
                embed.add_field(name="🏭 ПРОМЫШЛЕННЫЕ ТОВАРЫ", value=text, inline=True)
            if services:
                text = "\n".join([f"{k}: {v:.1f} ед./год" for k, v in services.items() if v >= 0.01])
                embed.add_field(name="📡 УСЛУГИ", value=text, inline=True)
        
        await i.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Специалисты", style=discord.ButtonStyle.primary)
    async def experts(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        available = get_available_experts(self.data)
        
        embed = discord.Embed(
            title=f"👨‍🔬 СПЕЦИАЛИСТЫ | {self.data['state']['statename']}",
            description="Управление специалистами, работающими за границей",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        available_text = ""
        for exp_id, exp in EXPERT_TYPES.items():
            if exp["can_export"]:
                count = available.get(exp_id, 0)
                available_text += f"{exp['emoji']} {exp['name']}: **{format_number(count)}**\n"
        embed.add_field(name="📋 ДОСТУПНЫЕ СПЕЦИАЛИСТЫ", value=available_text or "Нет доступных специалистов", inline=False)
        
        exported = get_country_experts(self.data["state"]["statename"])
        if exported:
            sent_text = ""
            for receiver, types in exported.items():
                for exp_id, count in types.items():
                    if count > 0:
                        exp = EXPERT_TYPES.get(exp_id, {})
                        sent_text += f"{exp.get('emoji', '📤')} {exp.get('name', exp_id)} в {receiver}: **{format_number(count)}**\n"
            embed.add_field(name="📤 ОТПРАВЛЕННЫЕ СПЕЦИАЛИСТЫ", value=sent_text, inline=False)
        else:
            embed.add_field(name="📤 ОТПРАВЛЕННЫЕ СПЕЦИАЛИСТЫ", value="Нет отправленных специалистов", inline=False)
        
        view = ExpertsMainView(self.user_id, self.data)
        await i.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Обновить", style=discord.ButtonStyle.secondary)
    async def refresh(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_population_menu(i, self.user_id)
    
    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        try:
            from bot import StateButtons
            view = StateButtons(self.user_id, self.data["state"]["statename"], self.data)
            embed = discord.Embed(
                title=f"{self.data['state']['statename']}",
                description=f"Лидер: {i.user.mention}",
                color=DARK_THEME_COLOR
            )
            s = self.data["state"]
            p = self.data["politics"]
            e = self.data["economy"]
            currency = get_currency_code(e)
            embed.add_field(name=f"{POPULATION_EMOJIS.get('population', '👥')} Население", value=f"{format_number(s['population'])} чел.", inline=True)
            embed.add_field(name=f"{POPULATION_EMOJIS.get('territory', '🗺️')} Территория", value=f"{format_number(s['territory'])} км²", inline=True)
            embed.add_field(name=f"{POPULATION_EMOJIS.get('stability', '⚖️')} Стабильность", value=f"{s['stability']:.1f}%", inline=True)
            embed.add_field(name=f"{POPULATION_EMOJIS.get('government', '🏛️')} Правительство", value=s['government_type'], inline=True)
            embed.add_field(name=f"{POPULATION_EMOJIS.get('ruling_party', '🎭')} Правящая партия", value=p['ruling_party'], inline=True)
            embed.add_field(name=f"{POPULATION_EMOJIS.get('popularity', '📊')} Популярность", value=f"{p['popularity']:.1f}%", inline=True)
            embed.add_field(name=f"{POPULATION_EMOJIS.get('gdp', '💰')} ВВП", value=f"{format_billion(get_gdp(e))} {currency}", inline=True)
            embed.add_field(name=f"{POPULATION_EMOJIS.get('budget', '💵')} Бюджет", value=f"{format_billion(get_budget(e))} {currency}", inline=True)
            await i.response.edit_message(embed=embed, view=view)
        except:
            await show_population_menu(i, self.user_id)


class ExpertsMainView(View):
    def __init__(self, user_id, data):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.data = data
    
    @discord.ui.button(label="Отправить специалистов", style=discord.ButtonStyle.success)
    async def send_experts(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        states = load_states()
        countries = []
        for pid, d in states["players"].items():
            country = d["state"]["statename"]
            if country != self.data["state"]["statename"] and "assigned_to" in d:
                countries.append(country)
        
        if not countries:
            await i.response.send_message("Нет других стран для отправки специалистов!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📤 ОТПРАВКА СПЕЦИАЛИСТОВ",
            description="Выберите страну назначения",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        select_view = View(timeout=120)
        select = ExpertCountrySelect(self.user_id, self.data, countries)
        select_view.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda x: self.back_to_experts(x)
        select_view.add_item(back_btn)
        
        await i.response.edit_message(embed=embed, view=select_view)
    
    @discord.ui.button(label="Отозвать специалистов", style=discord.ButtonStyle.danger)
    async def recall_experts(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        exported = get_country_experts(self.data["state"]["statename"])
        if not exported:
            await i.response.send_message("Нет отправленных специалистов для отзыва!", ephemeral=True)
            return
        
        countries = list(exported.keys())
        
        embed = discord.Embed(
            title="📤 ОТЗЫВ СПЕЦИАЛИСТОВ",
            description="Выберите страну для отзыва специалистов",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        select_view = View(timeout=120)
        select = ExpertRecallCountrySelect(self.user_id, self.data, countries)
        select_view.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda x: self.back_to_experts(x)
        select_view.add_item(back_btn)
        
        await i.response.edit_message(embed=embed, view=select_view)
    
    async def back_to_experts(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        available = get_available_experts(self.data)
        
        embed = discord.Embed(
            title=f"👨‍🔬 СПЕЦИАЛИСТЫ | {self.data['state']['statename']}",
            description="Управление специалистами, работающими за границей",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        available_text = ""
        for exp_id, exp in EXPERT_TYPES.items():
            if exp["can_export"]:
                count = available.get(exp_id, 0)
                available_text += f"{exp['emoji']} {exp['name']}: **{format_number(count)}**\n"
        embed.add_field(name="📋 ДОСТУПНЫЕ СПЕЦИАЛИСТЫ", value=available_text or "Нет доступных специалистов", inline=False)
        
        exported = get_country_experts(self.data["state"]["statename"])
        if exported:
            sent_text = ""
            for receiver, types in exported.items():
                for exp_id, count in types.items():
                    if count > 0:
                        exp = EXPERT_TYPES.get(exp_id, {})
                        sent_text += f"{exp.get('emoji', '📤')} {exp.get('name', exp_id)} в {receiver}: **{format_number(count)}**\n"
            embed.add_field(name="📤 ОТПРАВЛЕННЫЕ СПЕЦИАЛИСТЫ", value=sent_text, inline=False)
        else:
            embed.add_field(name="📤 ОТПРАВЛЕННЫЕ СПЕЦИАЛИСТЫ", value="Нет отправленных специалистов", inline=False)
        
        view = ExpertsMainView(self.user_id, self.data)
        await i.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Назад", style=discord.ButtonStyle.secondary)
    async def back(self, i, b):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        await show_population_menu(i, self.user_id)


class ExpertCountrySelect(Select):
    def __init__(self, user_id, data, countries):
        self.user_id = user_id
        self.data = data
        options = [discord.SelectOption(label=c, value=c) for c in countries[:25]]
        super().__init__(placeholder="Выберите страну...", options=options)
    
    async def callback(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        receiver = self.values[0]
        available = get_available_experts(self.data)
        
        available_types = []
        for exp_id, exp in EXPERT_TYPES.items():
            if exp["can_export"] and available.get(exp_id, 0) > 0:
                available_types.append((exp_id, exp, available[exp_id]))
        
        if not available_types:
            await i.response.send_message("Нет доступных специалистов для отправки!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📤 ОТПРАВКА В {receiver}",
            description="Выберите тип специалистов",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        select_view = View(timeout=120)
        select = ExpertTypeSelect(self.user_id, self.data, receiver, available_types)
        select_view.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda x: self.back_to_countries(x, i.message)
        select_view.add_item(back_btn)
        
        await i.response.edit_message(embed=embed, view=select_view)
    
    async def back_to_countries(self, i, original_message):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        states = load_states()
        countries = []
        for pid, d in states["players"].items():
            country = d["state"]["statename"]
            if country != self.data["state"]["statename"] and "assigned_to" in d:
                countries.append(country)
        
        embed = discord.Embed(
            title="📤 ОТПРАВКА СПЕЦИАЛИСТОВ",
            description="Выберите страну назначения",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        select_view = View(timeout=120)
        select = ExpertCountrySelect(self.user_id, self.data, countries)
        select_view.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        async def back_callback(interaction):
            await self.back_to_experts(interaction)
        back_btn.callback = back_callback
        select_view.add_item(back_btn)
        
        await i.response.edit_message(embed=embed, view=select_view)
    
    async def back_to_experts(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        available = get_available_experts(self.data)
        
        embed = discord.Embed(
            title=f"👨‍🔬 СПЕЦИАЛИСТЫ | {self.data['state']['statename']}",
            description="Управление специалистами, работающими за границей",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        available_text = ""
        for exp_id, exp in EXPERT_TYPES.items():
            if exp["can_export"]:
                count = available.get(exp_id, 0)
                available_text += f"{exp['emoji']} {exp['name']}: **{format_number(count)}**\n"
        embed.add_field(name="📋 ДОСТУПНЫЕ СПЕЦИАЛИСТЫ", value=available_text or "Нет доступных специалистов", inline=False)
        
        exported = get_country_experts(self.data["state"]["statename"])
        if exported:
            sent_text = ""
            for receiver, types in exported.items():
                for exp_id, count in types.items():
                    if count > 0:
                        exp = EXPERT_TYPES.get(exp_id, {})
                        sent_text += f"{exp.get('emoji', '📤')} {exp.get('name', exp_id)} в {receiver}: **{format_number(count)}**\n"
            embed.add_field(name="📤 ОТПРАВЛЕННЫЕ СПЕЦИАЛИСТЫ", value=sent_text, inline=False)
        else:
            embed.add_field(name="📤 ОТПРАВЛЕННЫЕ СПЕЦИАЛИСТЫ", value="Нет отправленных специалистов", inline=False)
        
        view = ExpertsMainView(self.user_id, self.data)
        await i.response.edit_message(embed=embed, view=view)


class ExpertTypeSelect(Select):
    def __init__(self, user_id, data, receiver, available_types):
        self.user_id = user_id
        self.data = data
        self.receiver = receiver
        options = []
        for exp_id, exp, count in available_types:
            options.append(discord.SelectOption(
                label=f"{exp['emoji']} {exp['name']}",
                description=f"Доступно: {format_number(count)} чел.",
                value=exp_id
            ))
        super().__init__(placeholder="Выберите тип специалистов...", options=options)
    
    async def callback(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        exp_type = self.values[0]
        exp = EXPERT_TYPES[exp_type]
        available = get_available_experts(self.data)
        max_quantity = available.get(exp_type, 0)
        
        modal = ExpertQuantityModal(self.user_id, self.data, self.receiver, exp_type, exp, max_quantity)
        await i.response.send_modal(modal)


class ExpertQuantityModal(Modal, title="Количество специалистов"):
    def __init__(self, user_id, data, receiver, exp_type, exp, max_quantity):
        super().__init__()
        self.user_id = user_id
        self.data = data
        self.receiver = receiver
        self.exp_type = exp_type
        self.exp = exp
        self.max_quantity = max_quantity
        
        self.quantity = TextInput(
            label=f"Количество (макс: {format_number(max_quantity)})",
            placeholder="Введите число",
            min_length=1,
            max_length=6,
            required=True
        )
        self.add_item(self.quantity)
    
    async def on_submit(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            qty = int(self.quantity.value)
        except ValueError:
            await i.response.send_message("Введите число!", ephemeral=True)
            return
        
        if qty <= 0 or qty > self.max_quantity:
            await i.response.send_message(f"Количество должно быть от 1 до {format_number(self.max_quantity)}!", ephemeral=True)
            return
        
        states = load_states()
        player_data = None
        for d in states["players"].values():
            if d.get("assigned_to") == str(self.user_id):
                player_data = d
                break
        
        if not player_data:
            await i.response.send_message("Ошибка загрузки данных!", ephemeral=True)
            return
        
        receiver_id = None
        for pid, d in states["players"].items():
            if d["state"]["statename"] == self.receiver and "assigned_to" in d:
                receiver_id = int(d["assigned_to"])
                break
        
        if not receiver_id:
            await i.response.send_message("Страна получатель не имеет назначенного игрока!", ephemeral=True)
            return
        
        request = create_expert_request(
            player_data["state"]["statename"], self.receiver, self.exp_type, qty,
            player_data, receiver_id, i.client
        )
        
        await send_expert_request_log(i.client, request)
        
        embed = discord.Embed(
            title="✅ ЗАПРОС ОТПРАВЛЕН",
            description=f"Запрос на отправку {qty} {self.exp['name']} в {self.receiver} отправлен.\n"
                        f"Страна получатель должна подтвердить в течение {EXPERT_REQUEST_TIMEOUT_HOURS} часов.",
            color=DARK_THEME_COLOR
        )
        embed.add_field(name="ID запроса", value=request["id"], inline=True)
        embed.add_field(name="Стоимость для получателя", value=f"${self.exp['cost_per_person'] * qty:,.0f}", inline=True)
        
        await i.response.edit_message(embed=embed, view=None)


class ExpertRecallCountrySelect(Select):
    def __init__(self, user_id, data, countries):
        self.user_id = user_id
        self.data = data
        options = [discord.SelectOption(label=c, value=c) for c in countries[:25]]
        super().__init__(placeholder="Выберите страну...", options=options)
    
    async def callback(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        receiver = self.values[0]
        exported = get_country_experts(self.data["state"]["statename"], receiver)
        
        available_types = []
        for exp_id, count in exported.items():
            if count > 0 and exp_id in EXPERT_TYPES:
                available_types.append((exp_id, EXPERT_TYPES[exp_id], count))
        
        if not available_types:
            await i.response.send_message("Нет специалистов для отзыва из этой страны!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📤 ОТЗЫВ ИЗ {receiver}",
            description="Выберите тип специалистов",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        select_view = View(timeout=120)
        select = ExpertRecallTypeSelect(self.user_id, self.data, receiver, available_types)
        select_view.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_btn.callback = lambda x: self.back_to_countries(x, i.message)
        select_view.add_item(back_btn)
        
        await i.response.edit_message(embed=embed, view=select_view)
    
    async def back_to_countries(self, i, original_message):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        exported = get_country_experts(self.data["state"]["statename"])
        if not exported:
            await i.response.send_message("Нет отправленных специалистов для отзыва!", ephemeral=True)
            return
        
        countries = list(exported.keys())
        
        embed = discord.Embed(
            title="📤 ОТЗЫВ СПЕЦИАЛИСТОВ",
            description="Выберите страну для отзыва специалистов",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        select_view = View(timeout=120)
        select = ExpertRecallCountrySelect(self.user_id, self.data, countries)
        select_view.add_item(select)
        
        back_btn = Button(label="Назад", style=discord.ButtonStyle.secondary)
        async def back_callback(interaction):
            await self.back_to_experts(interaction)
        back_btn.callback = back_callback
        select_view.add_item(back_btn)
        
        await i.response.edit_message(embed=embed, view=select_view)
    
    async def back_to_experts(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        available = get_available_experts(self.data)
        
        embed = discord.Embed(
            title=f"👨‍🔬 СПЕЦИАЛИСТЫ | {self.data['state']['statename']}",
            description="Управление специалистами, работающими за границей",
            color=DARK_THEME_COLOR
        )
        embed.set_image(url=get_random_expert_image())
        
        available_text = ""
        for exp_id, exp in EXPERT_TYPES.items():
            if exp["can_export"]:
                count = available.get(exp_id, 0)
                available_text += f"{exp['emoji']} {exp['name']}: **{format_number(count)}**\n"
        embed.add_field(name="📋 ДОСТУПНЫЕ СПЕЦИАЛИСТЫ", value=available_text or "Нет доступных специалистов", inline=False)
        
        exported = get_country_experts(self.data["state"]["statename"])
        if exported:
            sent_text = ""
            for receiver, types in exported.items():
                for exp_id, count in types.items():
                    if count > 0:
                        exp = EXPERT_TYPES.get(exp_id, {})
                        sent_text += f"{exp.get('emoji', '📤')} {exp.get('name', exp_id)} в {receiver}: **{format_number(count)}**\n"
            embed.add_field(name="📤 ОТПРАВЛЕННЫЕ СПЕЦИАЛИСТЫ", value=sent_text, inline=False)
        else:
            embed.add_field(name="📤 ОТПРАВЛЕННЫЕ СПЕЦИАЛИСТЫ", value="Нет отправленных специалистов", inline=False)
        
        view = ExpertsMainView(self.user_id, self.data)
        await i.response.edit_message(embed=embed, view=view)


class ExpertRecallTypeSelect(Select):
    def __init__(self, user_id, data, receiver, available_types):
        self.user_id = user_id
        self.data = data
        self.receiver = receiver
        options = []
        for exp_id, exp, count in available_types:
            options.append(discord.SelectOption(
                label=f"{exp['emoji']} {exp['name']}",
                description=f"Отправлено: {format_number(count)} чел.",
                value=exp_id
            ))
        super().__init__(placeholder="Выберите тип специалистов...", options=options)
    
    async def callback(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        exp_type = self.values[0]
        exported = get_country_experts(self.data["state"]["statename"], self.receiver)
        max_quantity = exported.get(exp_type, 0)
        exp = EXPERT_TYPES[exp_type]
        
        modal = ExpertRecallQuantityModal(self.user_id, self.data, self.receiver, exp_type, exp, max_quantity)
        await i.response.send_modal(modal)


class ExpertRecallQuantityModal(Modal, title="Количество для отзыва"):
    def __init__(self, user_id, data, receiver, exp_type, exp, max_quantity):
        super().__init__()
        self.user_id = user_id
        self.data = data
        self.receiver = receiver
        self.exp_type = exp_type
        self.exp = exp
        self.max_quantity = max_quantity
        
        self.quantity = TextInput(
            label=f"Количество (макс: {format_number(max_quantity)})",
            placeholder="Введите число",
            min_length=1,
            max_length=6,
            required=True
        )
        self.add_item(self.quantity)
    
    async def on_submit(self, i):
        if i.user.id != self.user_id:
            await i.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        try:
            qty = int(self.quantity.value)
        except ValueError:
            await i.response.send_message("Введите число!", ephemeral=True)
            return
        
        if qty <= 0 or qty > self.max_quantity:
            await i.response.send_message(f"Количество должно быть от 1 до {format_number(self.max_quantity)}!", ephemeral=True)
            return
        
        states = load_states()
        player_data = None
        for d in states["players"].values():
            if d.get("assigned_to") == str(self.user_id):
                player_data = d
                break
        
        if not player_data:
            await i.response.send_message("Ошибка загрузки данных!", ephemeral=True)
            return
        
        success, msg = recall_experts(player_data["state"]["statename"], self.receiver, self.exp_type, qty, player_data)
        
        if success:
            save_states(states)
            await send_recall_log(i.client, player_data["state"]["statename"], self.receiver, self.exp_type, qty)
            
            embed = discord.Embed(
                title="✅ СПЕЦИАЛИСТЫ ОТОЗВАНЫ",
                description=msg,
                color=DARK_THEME_COLOR
            )
            await i.response.edit_message(embed=embed, view=None)
            await show_population_menu(i, self.user_id)
        else:
            await i.response.send_message(f"Ошибка: {msg}", ephemeral=True)


def init_population_for_country(player_data):
    return update_population(player_data, is_initialization=True)


__all__ = [
    'population_update_loop', 'show_population_menu', 'update_population',
    'init_population_for_country', 'calculate_employment',
    'calculate_average_salary', 'BASE_POPULATION_NEEDS', 'MINIMUM_WAGE',
    'calculate_gdp_per_capita', 'calculate_real_gdp_per_capita',
    'calculate_consumption_per_capita',
    'accept_expert_request', 'reject_expert_request', 'EXPERT_TYPES',
    'get_asset_total', 'POPULATION_EMOJIS'
]

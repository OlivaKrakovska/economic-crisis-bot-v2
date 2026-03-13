# resource_extraction.py - Модуль для периодической добычи ресурсов
# ИСПРАВЛЕННАЯ ВЕРСИЯ - сохраняет время последней добычи

import discord
import asyncio
import json
import random
import math
import os
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from utils import load_states, save_states, format_number, format_billion, DARK_THEME_COLOR

# Файл для хранения времени последней добычи
LAST_EXTRACTION_FILE = 'last_extraction.json'

# ==================== ЧЕЛОВЕКОЧИТАЕМЫЕ НАЗВАНИЯ РЕСУРСОВ ====================

RESOURCE_NAMES = {
    "oil": "Нефть",
    "gas": "Газ",
    "coal": "Уголь",
    "uranium": "Уран",
    "steel": "Сталь",
    "aluminum": "Алюминий",
    "electronics": "Электроника",
    "rare_metals": "Редкие металлы",
    "food": "Продовольствие"
}

# ==================== КОНСТАНТЫ ====================

# Интервал добычи в часах (по умолчанию 72 часа = 3 дня)
EXTRACTION_INTERVAL_HOURS = 72

# Базовые значения ресурсов для каждой страны (из ORIGINAL_STATES в reset_to_original.py)
BASE_RESOURCES = {
    "США": {
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
    "Россия": {
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
    "Китай": {
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
    "Германия": {
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
    "Израиль": {
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
    "Украина": {
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
    "Иран": {
        "oil": 400,
        "gas": 300,
        "coal": 80,
        "uranium": 15,
        "steel": 80,
        "aluminum": 40,
        "electronics": 30,
        "rare_metals": 20,
        "food": 150
    }
}

# Множители от инфраструктуры (В % к базовой добыче)
INFRASTRUCTURE_BOOST = {
    "civilian_factories": {
        "steel": 0.05,
        "aluminum": 0.05,
        "electronics": 0.1,
        "coal": 0.03
    },
    "refineries": {
        "oil": 0.2,
        "gas": 0.2
    },
    "oil_depots": {
        "oil": 0.05,
        "gas": 0.05
    },
    "internet_infrastructure": {
        "electronics": 0.3
    },
    "agriculture_level": {
        "food": 0.2
    }
}

# Максимальный общий бонус
MAX_TOTAL_BOOST_PERCENT = 30

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ФАЙЛОМ ВРЕМЕНИ ====================

def load_last_extraction_time():
    """Загружает время последней добычи из файла"""
    try:
        with open(LAST_EXTRACTION_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if data and "last_update" in data:
                return datetime.fromisoformat(data["last_update"])
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        pass
    return None

def save_last_extraction_time(extraction_time: datetime):
    """Сохраняет время последней добычи в файл"""
    with open(LAST_EXTRACTION_FILE, 'w', encoding='utf-8') as f:
        json.dump({"last_update": str(extraction_time)}, f, ensure_ascii=False, indent=4)

# ==================== ФУНКЦИИ ДЛЯ ПОДСЧЁТА ИНФРАСТРУКТУРЫ ====================

def count_infrastructure_by_country(infra_data: Dict, country_name: str) -> Dict:
    """
    Подсчитывает всю инфраструктуру страны
    """
    result = {
        "civilian_factories": 0,
        "refineries": 0,
        "oil_depots": 0,
        "internet_infrastructure": 0,
        "agriculture_level": 0,
        "regions_count": 0
    }
    
    for cid, cdata in infra_data["infrastructure"].items():
        if cdata.get("country") == country_name:
            for econ_region, econ_data in cdata.get("economic_regions", {}).items():
                for region_name, region_data in econ_data.get("regions", {}).items():
                    result["regions_count"] += 1
                    
                    result["civilian_factories"] += region_data.get("civilian_factories", 0)
                    result["refineries"] += region_data.get("refineries", 0)
                    result["oil_depots"] += region_data.get("oil_depots", 0)
                    result["internet_infrastructure"] += region_data.get("internet_infrastructure", 0)
                    result["agriculture_level"] += region_data.get("agriculture_level", 0)
            break
    
    return result

def calculate_extraction_boost(infra_counts: Dict) -> Dict[str, float]:
    """
    Рассчитывает процентные бонусы для каждого ресурса
    """
    boosts = {}
    
    for resource in ["oil", "gas", "coal", "steel", "aluminum", "electronics", "rare_metals", "food", "uranium"]:
        boosts[resource] = 0.0
    
    factory_count = infra_counts["civilian_factories"]
    for resource, boost_per_factory in INFRASTRUCTURE_BOOST["civilian_factories"].items():
        boosts[resource] += factory_count * boost_per_factory
    
    refinery_count = infra_counts["refineries"]
    for resource, boost_per_refinery in INFRASTRUCTURE_BOOST["refineries"].items():
        boosts[resource] += refinery_count * boost_per_refinery
    
    depot_count = infra_counts["oil_depots"]
    for resource, boost_per_depot in INFRASTRUCTURE_BOOST["oil_depots"].items():
        boosts[resource] += depot_count * boost_per_depot
    
    data_center_count = infra_counts["internet_infrastructure"]
    boosts["electronics"] += data_center_count * INFRASTRUCTURE_BOOST["internet_infrastructure"]["electronics"]
    
    agriculture_level = infra_counts["agriculture_level"]
    boosts["food"] += agriculture_level * INFRASTRUCTURE_BOOST["agriculture_level"]["food"]
    
    for resource in boosts:
        boosts[resource] = min(boosts[resource], MAX_TOTAL_BOOST_PERCENT)
    
    return boosts

def calculate_extraction_amount(base_amount: float, boost_percent: float) -> float:
    """
    Рассчитывает количество добытых ресурсов с учётом бонуса
    """
    total_percent = 100 + boost_percent
    amount = base_amount * (total_percent / 100)
    
    variation = random.uniform(0.98, 1.02)
    amount *= variation
    
    return round(amount, 2)

# ==================== ОСНОВНАЯ ФУНКЦИЯ ОБНОВЛЕНИЯ ====================

async def resource_extraction_loop(bot_instance):
    """
    Фоновая задача для периодической добычи ресурсов
    Запускается каждые EXTRACTION_INTERVAL_HOURS часов
    """
    await bot_instance.wait_until_ready()
    
    # Загружаем время последней добычи из файла
    last_update = load_last_extraction_time()
    if last_update:
        print(f"⛏️ Загружено время последней добычи: {last_update.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("⛏️ Первый запуск добычи ресурсов")
    
    while not bot_instance.is_closed():
        try:
            now = datetime.now()
            
            # Проверяем, прошло ли нужное количество часов
            hours_since_update = 0
            if last_update:
                hours_since_update = (now - last_update).total_seconds() / 3600
            
            if last_update is None or hours_since_update >= EXTRACTION_INTERVAL_HOURS:
                print(f"⛏️ Запуск добычи ресурсов: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"   Интервал: {EXTRACTION_INTERVAL_HOURS} часов")
                if last_update:
                    print(f"   Прошло с прошлой добычи: {hours_since_update:.1f} часов")
                
                states = load_states()
                from infra_build import load_infrastructure
                infra = load_infrastructure()
                
                extraction_log = []
                
                for state_id, player_data in states["players"].items():
                    if "assigned_to" not in player_data:
                        continue
                    
                    country_name = player_data["state"]["statename"]
                    
                    # Получаем базовые ресурсы для страны
                    base_resources = BASE_RESOURCES.get(country_name, {})
                    if not base_resources:
                        print(f"⚠️ Нет базовых ресурсов для {country_name}")
                        continue
                    
                    # Подсчитываем инфраструктуру
                    country_infra = count_infrastructure_by_country(infra, country_name)
                    
                    # Рассчитываем бонусы
                    boosts = calculate_extraction_boost(country_infra)
                    
                    # Добавляем ресурсы игроку
                    if "resources" not in player_data:
                        player_data["resources"] = {}
                    
                    added_resources = {}
                    for resource, base_amount in base_resources.items():
                        if base_amount > 0:
                            boost = boosts.get(resource, 0)
                            amount = calculate_extraction_amount(base_amount, boost)
                            
                            current = player_data["resources"].get(resource, 0)
                            player_data["resources"][resource] = current + amount
                            added_resources[resource] = amount
                    
                    extraction_log.append({
                        "country": country_name,
                        "extraction": added_resources,
                        "boosts": {r: b for r, b in boosts.items() if b > 0}
                    })
                    
                    # Отправляем уведомление игроку
                    try:
                        user = await bot_instance.fetch_user(int(player_data["assigned_to"]))
                        if user:
                            embed = discord.Embed(
                                title="⛏️ Добыча ресурсов",
                                description=f"Ваша страна добыла ресурсы за последние {EXTRACTION_INTERVAL_HOURS} часов:",
                                color=DARK_THEME_COLOR
                            )
                            
                            res_text = ""
                            for res, amount in list(added_resources.items())[:5]:
                                res_name = RESOURCE_NAMES.get(res, res)
                                res_text += f"• {res_name}: +{amount:.2f}\n"
                            embed.add_field(name="📦 Добыто", value=res_text or "Ничего", inline=True)
                            
                            boost_text = ""
                            for res, boost in list(boosts.items())[:5]:
                                if boost > 0:
                                    res_name = RESOURCE_NAMES.get(res, res)
                                    boost_text += f"• {res_name}: +{boost:.2f}%\n"
                            embed.add_field(name="⚡ Бонусы", value=boost_text or "Нет бонусов", inline=True)
                            
                            await user.send(embed=embed)
                    except:
                        pass
                
                save_states(states)
                last_update = now
                # Сохраняем время в файл
                save_last_extraction_time(now)
                
                print(f"✅ Добыча выполнена для {len(extraction_log)} стран")
                for log in extraction_log[:3]:
                    total = sum(log['extraction'].values())
                    print(f"   {log['country']}: +{total:.2f} всего ресурсов")
            
            # Проверяем каждый час
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"❌ Ошибка в resource_extraction_loop: {e}")
            await asyncio.sleep(3600)

# ==================== КОМАНДА ДЛЯ ПРОВЕРКИ ====================

async def show_extraction_info(ctx, user_id: int):
    """
    Показывает информацию о добыче для игрока
    """
    states = load_states()
    from infra_build import load_infrastructure
    
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            break
    
    if not player_data:
        await ctx.send("❌ У вас нет государства!")
        return
    
    country_name = player_data["state"]["statename"]
    base_resources = BASE_RESOURCES.get(country_name, {})
    
    infra = load_infrastructure()
    country_infra = count_infrastructure_by_country(infra, country_name)
    boosts = calculate_extraction_boost(country_infra)
    
    # Получаем время последней добычи
    last_update = load_last_extraction_time()
    time_left = ""
    if last_update:
        next_update = last_update + timedelta(hours=EXTRACTION_INTERVAL_HOURS)
        now = datetime.now()
        if next_update > now:
            hours_left = (next_update - now).total_seconds() / 3600
            time_left = f"\n⏳ Следующая добыча через: {hours_left:.1f} часов"
    
    embed = discord.Embed(
        title=f"⛏️ Добыча ресурсов: {country_name}",
        description=f"Каждые {EXTRACTION_INTERVAL_HOURS} часов{time_left}",
        color=DARK_THEME_COLOR
    )
    
    base_text = ""
    for resource, amount in base_resources.items():
        if amount > 0:
            res_name = RESOURCE_NAMES.get(resource, resource)
            base_text += f"• {res_name}: {amount:.2f}\n"
    embed.add_field(name="📊 База за период", value=base_text or "Нет данных", inline=True)
    
    boost_text = ""
    for resource, boost in boosts.items():
        if boost > 0:
            res_name = RESOURCE_NAMES.get(resource, resource)
            boost_text += f"• {res_name}: +{boost:.2f}%\n"
    embed.add_field(name="⚡ Бонусы инфраструктуры", value=boost_text or "Нет бонусов", inline=True)
    
    total_text = ""
    for resource, base in base_resources.items():
        if base > 0:
            res_name = RESOURCE_NAMES.get(resource, resource)
            boost = boosts.get(resource, 0)
            total = base * (1 + boost/100)
            total_text += f"• {res_name}: {total:.2f}\n"
    embed.add_field(name="📈 Итого за период", value=total_text or "Нет данных", inline=False)
    
    infra_text = f"🏭 Гражданские фабрики: {country_infra['civilian_factories']}\n"
    infra_text += f"🏭 НПЗ: {country_infra['refineries']}\n"
    infra_text += f"🛢️ Нефтебазы: {country_infra['oil_depots']}\n"
    infra_text += f"💻 ЦОД: {country_infra['internet_infrastructure']}\n"
    infra_text += f"🌾 Уровень сельского хозяйства: {country_infra['agriculture_level']}"
    embed.add_field(name="🏗️ Ваша инфраструктура", value=infra_text, inline=False)
    
    await ctx.send(embed=embed)

# ==================== АДМИН-КОМАНДА ====================

async def force_extraction(ctx, user_id: int = None):
    """
    Принудительно запускает добычу (для админов)
    """
    states = load_states()
    from infra_build import load_infrastructure
    infra = load_infrastructure()
    
    if user_id:
        # Для одного игрока
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(user_id):
                player_data = data
                break
        
        if not player_data:
            await ctx.send("❌ Игрок не найден!")
            return
        
        country_name = player_data["state"]["statename"]
        base_resources = BASE_RESOURCES.get(country_name, {})
        country_infra = count_infrastructure_by_country(infra, country_name)
        boosts = calculate_extraction_boost(country_infra)
        
        if "resources" not in player_data:
            player_data["resources"] = {}
        
        added = {}
        for resource, base in base_resources.items():
            if base > 0:
                boost = boosts.get(resource, 0)
                amount = calculate_extraction_amount(base, boost)
                
                current = player_data["resources"].get(resource, 0)
                player_data["resources"][resource] = current + amount
                added[resource] = amount
        
        save_states(states)
        
        # Обновляем время последней добычи
        save_last_extraction_time(datetime.now())
        
        embed = discord.Embed(
            title="✅ Принудительная добыча",
            description=f"Для {country_name} добыто:",
            color=discord.Color.green()
        )
        
        res_text = ""
        for res, amount in added.items():
            res_name = RESOURCE_NAMES.get(res, res)
            res_text += f"• {res_name}: +{amount:.2f}\n"
        embed.add_field(name="Ресурсы", value=res_text, inline=False)
        
        await ctx.send(embed=embed)
        
    else:
        # Для всех игроков
        results = []
        for state_id, player_data in states["players"].items():
            if "assigned_to" not in player_data:
                continue
            
            country_name = player_data["state"]["statename"]
            base_resources = BASE_RESOURCES.get(country_name, {})
            country_infra = count_infrastructure_by_country(infra, country_name)
            boosts = calculate_extraction_boost(country_infra)
            
            if "resources" not in player_data:
                player_data["resources"] = {}
            
            total_added = 0
            for resource, base in base_resources.items():
                if base > 0:
                    boost = boosts.get(resource, 0)
                    amount = calculate_extraction_amount(base, boost)
                    
                    current = player_data["resources"].get(resource, 0)
                    player_data["resources"][resource] = current + amount
                    total_added += amount
            
            results.append(f"{country_name}: +{total_added:.2f} ресурсов")
        
        save_states(states)
        save_last_extraction_time(datetime.now())
        
        embed = discord.Embed(
            title="✅ Принудительная добыча для всех",
            description="\n".join(results[:10]),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)

# ==================== ЭКСПОРТ ====================

__all__ = [
    'resource_extraction_loop',
    'show_extraction_info',
    'force_extraction',
    'EXTRACTION_INTERVAL_HOURS',
    'RESOURCE_NAMES'
]

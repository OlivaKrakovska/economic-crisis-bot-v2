# corporation_production.py - Автоматическое производство для корпораций

import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List

from civil_corporations_db import (
    get_all_civil_corporations, load_corporations_state, save_corporations_state,
    CIVIL_PRODUCT_NAMES
)
from utils import load_states

# Скорость производства для каждого типа продукции
PRODUCTION_RATES = {
    # Продукты питания (быстро)
    "food_products": 1000,     # единиц в день
    "beverages": 800,
    "restaurants": 500,
    "fast_food": 600,
    
    # Товары повседневного спроса
    "clothing": 200,
    "footwear": 150,
    "household_goods": 300,
    "furniture": 50,
    "cosmetics": 100,
    
    # Электроника
    "consumer_electronics": 50,
    "computers": 10,
    "smartphones": 20,
    "tablets": 15,
    
    # Услуги (производятся мгновенно, но с ограничением)
    "telecom_services": 10000,
    "internet_services": 10000,
    "mobile_services": 10000,
    "banking": 5000,
    "insurance": 1000,
    "healthcare_services": 500,
    "education": 200,
    "streaming": 5000,
    "software": 100,
    
    # Промышленные товары (медленно)
    "cars": 5,
    "trucks": 2,
    "buses": 1,
    "agricultural_machinery": 2,
    "construction_machinery": 1,
    "industrial_equipment": 3,
    "machine_tools": 2,
    "aerospace_equipment": 0.1,  # 1 самолёт в 10 дней
    
    # Дроны
    "drones": 10,
    "fpv_drones": 50,
    
    # Химия и фармацевтика
    "chemicals": 200,
    "pharmaceuticals": 100,
    "medical_supplies": 500,
    
    # По умолчанию
    "default": 100
}

# Стоимость производства (в долларах за единицу)
PRODUCTION_COSTS = {
    "food_products": 50,
    "beverages": 30,
    "cars": 20000,
    "smartphones": 400,
    "computers": 800,
    "default": 10
}

async def corporation_production_loop(bot_instance):
    """Фоновая задача для производства товаров корпорациями"""
    await bot_instance.wait_until_ready()
    
    last_update = None
    
    while not bot_instance.is_closed():
        try:
            now = datetime.now()
            
            # Обновляем раз в день
            if last_update is None or (now - last_update).days >= 1:
                print(f"🏭 Запуск производства корпораций: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Загружаем состояние корпораций
                corps_state = load_corporations_state()
                states = load_states()
                
                production_log = []
                
                for corp_id, corp in corps_state["corporations"].items():
                    # Находим оригинальную корпорацию в базе
                    original_corp = None
                    for c in get_all_civil_corporations():
                        if c.id == corp_id:
                            original_corp = c
                            break
                    
                    if not original_corp:
                        continue
                    
                    # Определяем страну корпорации
                    country = original_corp.country
                    
                    # Находим данные государства этой страны
                    country_data = None
                    for player_data in states["players"].values():
                        if player_data.get("state", {}).get("statename") == country:
                            country_data = player_data
                            break
                    
                    # Рассчитываем модификаторы производства
                    production_modifier = 1.0
                    
                    # Бонус от инфраструктуры страны
                    if country_data and "infrastructure_bonuses" in country_data:
                        bonuses = country_data["infrastructure_bonuses"].get("production", {})
                        if "civil" in bonuses:
                            production_modifier = bonuses["civil"]
                    
                    # Бонус от популярности (популярные корпорации производят больше)
                    popularity_bonus = 1.0 + (corp.popularity - 50) / 100
                    
                    # Производим каждый тип продукции
                    for product_type in original_corp.products.keys():
                        # Базовая скорость производства
                        base_rate = PRODUCTION_RATES.get(product_type, PRODUCTION_RATES["default"])
                        
                        # Итоговая скорость
                        daily_production = base_rate * production_modifier * popularity_bonus
                        
                        # Добавляем небольшую случайность
                        daily_production *= random.uniform(0.9, 1.1)
                        
                        # Округляем до целого числа
                        produced = int(daily_production)
                        
                        if produced > 0:
                            # Добавляем на склад
                            if product_type not in corp.inventory:
                                corp.inventory[product_type] = 0
                            corp.inventory[product_type] += produced
                            
                            # Списываем стоимость производства из бюджета корпорации
                            cost_per_unit = PRODUCTION_COSTS.get(product_type, PRODUCTION_COSTS["default"])
                            total_cost = produced * cost_per_unit
                            
                            if corp.budget >= total_cost:
                                corp.budget -= total_cost
                            else:
                                # Если денег мало, производим меньше
                                affordable = int(corp.budget / cost_per_unit)
                                if affordable > 0:
                                    corp.inventory[product_type] += affordable - produced
                                    corp.budget -= affordable * cost_per_unit
                            
                            production_log.append({
                                "corporation": original_corp.name,
                                "product": CIVIL_PRODUCT_NAMES.get(product_type, product_type),
                                "produced": produced,
                                "modifier": production_modifier
                            })
                
                # Сохраняем обновлённое состояние
                save_corporations_state(corps_state)
                last_update = now
                
                print(f"✅ Производство завершено. Производили {len(production_log)} типов товаров")
                
                # Отправляем отчёт в лог-канал (опционально)
                try:
                    channel = bot_instance.get_channel(ADMIN_LOG_CHANNEL_ID)
                    if channel and production_log:
                        # Показываем топ-5 производств
                        top_production = sorted(production_log, key=lambda x: x['produced'], reverse=True)[:5]
                        log_text = "**🏭 Производство корпораций:**\n"
                        for item in top_production:
                            log_text += f"• {item['corporation']}: +{item['produced']} {item['product']}\n"
                        await channel.send(log_text)
                except:
                    pass
            
            await asyncio.sleep(3600)  # Проверка каждый час
            
        except Exception as e:
            print(f"❌ Ошибка в corporation_production_loop: {e}")
            await asyncio.sleep(3600)


def get_corporation_production_rate(corp, product_type):
    """Получить скорость производства для конкретной корпорации"""
    base_rate = PRODUCTION_RATES.get(product_type, PRODUCTION_RATES["default"])
    
    # Модификаторы от размера корпорации
    size_modifier = 1.0
    if corp.budget > 1_000_000_000:  # > 1 млрд $
        size_modifier = 1.5
    elif corp.budget > 100_000_000:   # > 100 млн $
        size_modifier = 1.2
    
    # Модификатор от популярности
    popularity_modifier = 1.0 + (corp.popularity - 50) / 100
    
    return base_rate * size_modifier * popularity_modifier

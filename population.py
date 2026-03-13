# population.py - Модуль для управления населением и его потребностями
# НОВАЯ ВЕРСИЯ - население покупает товары у корпораций, а не из государственных запасов
# ДОБАВЛЕНО: detailed_purchases для consumption_forecast

import discord
from discord.ui import Button, View, Select
import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math

from utils import format_number, format_billion, load_states, save_states
from resource_system import RESOURCE_PRICES
from civil_corporations_db import (
    get_all_civil_corporations, get_civil_corporations_by_country,
    CIVIL_PRODUCT_NAMES, load_corporations_state, save_corporations_state,
    initialize_corporation_state
)
from infra_build import load_infrastructure, get_all_regions_from_country
from trade_tariffs import TariffSystem

# Цвет для эмбедов
DARK_THEME_COLOR = 0x2b2d31

# ==================== КОНСТАНТЫ ====================

# Базовые потребности населения (в единицах на человека в год)
BASE_POPULATION_NEEDS = {
    "food_products": 0.5,           # 0.5 единицы еды
    "clothing": 0.2,                 # 0.2 единицы одежды
    "consumer_electronics": 0.05,    # 0.05 единицы электроники
    "medical_supplies": 0.03,        # 0.03 единицы медикаментов
    "furniture": 0.02,                # 0.02 единицы мебели
    "household_goods": 0.04,          # 0.04 единицы товаров для дома
    "buses": 0.0001,                   # 0.0001 автобуса (общественный транспорт)
    "cars": 0.01,                      # 0.01 автомобиля
    "smartphones": 0.03,               # 0.03 смартфона
    "computers": 0.01,                  # 0.01 компьютера
    "software": 0.05,                   # 0.05 лицензий ПО
    "telecom_services": 1.0,            # 1 услуга связи на человека
    "internet_services": 1.0,           # 1 интернет-услуга
    "mobile_services": 1.0,             # 1 мобильная связь
    "streaming": 0.5,                   # 0.5 подписки на стриминг
    "banking": 1.0,                     # 1 банковская услуга
    "insurance": 0.3,                   # 0.3 страховки
    "healthcare_services": 0.2,         # 0.2 медицинских услуг
    "education": 0.1,                   # 0.1 образовательных услуг
    "entertainment": 0.5                # 0.5 развлекательных услуг
}

# Эластичность потребления по доходу
INCOME_ELASTICITY = {
    "food_products": 0.3,           # Еда - необходима
    "clothing": 0.5,                 # Одежда
    "consumer_electronics": 1.2,     # Техника
    "medical_supplies": 0.4,         # Медицина
    "furniture": 0.8,                 # Мебель
    "household_goods": 0.6,           # Товары для дома
    "buses": 0.2,                     # Общественный транспорт
    "cars": 1.5,                      # Автомобили
    "smartphones": 1.3,                # Смартфоны
    "computers": 1.2,                  # Компьютеры
    "software": 0.9,                   # ПО
    "telecom_services": 0.4,           # Телеком
    "internet_services": 0.5,          # Интернет
    "mobile_services": 0.6,            # Мобильная связь
    "streaming": 1.1,                  # Стриминг
    "banking": 0.3,                    # Банки
    "insurance": 0.7,                  # Страхование
    "healthcare_services": 0.4,        # Медицина
    "education": 0.8,                  # Образование
    "entertainment": 1.4               # Развлечения
}

# Минимальные зарплаты по странам (в год, в долларах)
MINIMUM_WAGE = {
    "США": 15000,
    "Россия": 3000,
    "Китай": 2500,
    "Германия": 20000,
    "Великобритания": 18000,
    "Франция": 19000,
    "Япония": 17000,
    "Израиль": 16000,
    "Украина": 1500,
    "Иран": 1000
}

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С КОРПОРАЦИЯМИ ====================

def update_corporation_inventory(corp_id: str, product_type: str, quantity: int, add: bool = True):
    """Обновить инвентарь корпорации"""
    from civil_corporations_db import load_corporations_state, save_corporations_state
    
    state = load_corporations_state()
    if corp_id in state["corporations"]:
        corp = state["corporations"][corp_id]
        if add:
            if product_type not in corp.inventory:
                corp.inventory[product_type] = 0
            corp.inventory[product_type] += quantity
        else:
            if product_type in corp.inventory and corp.inventory[product_type] >= quantity:
                corp.inventory[product_type] -= quantity
        save_corporations_state(state)
        return True
    return False

def update_corporation_budget(corp_id: str, amount: float, add: bool = True):
    """Обновить бюджет корпорации"""
    from civil_corporations_db import load_corporations_state, save_corporations_state
    
    state = load_corporations_state()
    if corp_id in state["corporations"]:
        corp = state["corporations"][corp_id]
        if add:
            corp.budget += amount
        else:
            corp.budget -= amount
        save_corporations_state(state)
        return True
    return False

def increase_corporation_popularity(corp_id: str, amount: float):
    """Увеличивает популярность корпорации"""
    from civil_corporations_db import load_corporations_state, save_corporations_state
    
    state = load_corporations_state()
    if corp_id in state["corporations"]:
        corp = state["corporations"][corp_id]
        corp.popularity = min(100, corp.popularity + amount)
        save_corporations_state(state)

# ==================== РАСЧЁТ РАБОЧИХ МЕСТ ОТ ИНФРАСТРУКТУРЫ ====================

def calculate_jobs_from_infrastructure(player_data) -> Dict:
    """
    Рассчитывает количество рабочих мест от каждого типа инфраструктуры
    """
    from infra_build import load_infrastructure, get_all_regions_from_country
    
    jobs = {
        "military": 0,
        "civilian": 0,
        "shipyards": 0,
        "refineries": 0,
        "power": 0,
        "data_centers": 0,
        "oil_depots": 0,
        "office_centers": 0,
        "total": 0
    }
    
    infra_data = load_infrastructure()
    country_name = player_data["state"]["statename"]
    
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    
    if country_id:
        regions = get_all_regions_from_country(infra_data, country_id)
        
        for region_name, region_data in regions.items():
            if "military_factories" in region_data:
                jobs["military"] += region_data["military_factories"] * 2000
            
            if "civilian_factories" in region_data:
                jobs["civilian"] += region_data["civilian_factories"] * 3000
            
            if "shipyards" in region_data:
                jobs["shipyards"] += region_data["shipyards"] * 5000
            
            if "refineries" in region_data:
                jobs["refineries"] += region_data["refineries"] * 600
            
            power_plants = [
                ("thermal_power", 250),
                ("nuclear_power", 400),
                ("hydro_power", 200),
                ("wind_power", 150),
                ("solar_power", 100)
            ]
            
            for plant_type, jobs_per_plant in power_plants:
                if plant_type in region_data:
                    jobs["power"] += region_data[plant_type] * jobs_per_plant
            
            if "internet_infrastructure" in region_data:
                jobs["data_centers"] += region_data["internet_infrastructure"] * 200
            
            if "oil_depots" in region_data:
                jobs["oil_depots"] += region_data["oil_depots"] * 50
            
            if "office_centers" in region_data:
                count = region_data["office_centers"]
                region_pop = region_data.get("population", 0)
                
                if count > 0 and region_pop > 0:
                    base_jobs = count * 4000
                    density_factor = min(2.0, region_pop / 500000)
                    extra_jobs = int(base_jobs * (density_factor - 1))
                    jobs["office_centers"] += base_jobs + extra_jobs
    
    return jobs

def calculate_employment(player_data) -> Dict:
    """
    Рассчитывает занятость на основе инфраструктуры
    """
    population = player_data["state"]["population"]
    
    working_age_percent = 0.67
    working_age = int(population * working_age_percent)
    
    jobs_data = calculate_jobs_from_infrastructure(player_data)
    
    demographics = player_data["state"].get("demographics", {})
    professions = demographics.get("professions", {})
    government_jobs = professions.get("officials", 0)
    
    # Добавляем рабочие места в корпорациях
    corporation_jobs = calculate_corporation_jobs(player_data)
    
    small_business_percent = 0.15
    small_business_jobs = int(population * small_business_percent)
    
    service_jobs = int(population * 0.10)
    transport_jobs = int(population * 0.05)
    construction_jobs = int(population * 0.05)
    agriculture_jobs = int(population * 0.08)
    
    total_formal_jobs = (
        jobs_data["military"] +
        jobs_data["civilian"] +
        jobs_data["shipyards"] +
        jobs_data["refineries"] +
        jobs_data["power"] +
        jobs_data["data_centers"] +
        jobs_data["oil_depots"] +
        jobs_data["office_centers"] +
        corporation_jobs +
        government_jobs +
        small_business_jobs +
        service_jobs +
        transport_jobs +
        construction_jobs +
        agriculture_jobs
    )
    
    informal_jobs = int(working_age * 0.03)
    total_jobs = total_formal_jobs + informal_jobs
    
    employed = min(total_jobs, working_age)
    unemployed = working_age - employed
    unemployment_rate = (unemployed / working_age) * 100 if working_age > 0 else 0
    
    sector_breakdown = {
        "industrial": jobs_data["military"] + jobs_data["civilian"] + jobs_data["shipyards"] + jobs_data["refineries"],
        "energy": jobs_data["power"],
        "tech": jobs_data["data_centers"] + jobs_data["office_centers"],
        "oil_gas": jobs_data["oil_depots"],
        "corporations": corporation_jobs,
        "government": government_jobs,
        "small_business": small_business_jobs,
        "services": service_jobs,
        "transport": transport_jobs,
        "construction": construction_jobs,
        "agriculture": agriculture_jobs,
        "informal": informal_jobs
    }
    
    return {
        "working_age": working_age,
        "employed": employed,
        "unemployed": unemployed,
        "unemployment_rate": unemployment_rate,
        "jobs_available": total_jobs,
        "jobs_breakdown": jobs_data,
        "corporation_jobs": corporation_jobs,
        "sector_breakdown": sector_breakdown,
        "labor_force_participation": (employed / working_age) * 100 if working_age > 0 else 0
    }

def calculate_corporation_jobs(player_data) -> int:
    """
    Рассчитывает количество рабочих мест в корпорациях
    """
    country_name = player_data["state"]["statename"]
    corps = get_civil_corporations_by_country(country_name).values()
    
    total_jobs = 0
    for corp in corps:
        # Каждая корпорация создаёт рабочие места в зависимости от размера
        # Упрощённо: 1000 рабочих мест на корпорацию + запас товаров
        corp_state = initialize_corporation_state(corp)
        
        # Базовые рабочие места
        base_jobs = 1000
        
        # Дополнительные за товары на складе
        inventory_value = sum(corp_state.inventory.values())
        inventory_jobs = int(inventory_value / 10)
        
        # Дополнительные за бюджет
        budget_jobs = int(corp_state.budget / 1000000)  # 1 рабочее место на миллион $
        
        total_jobs += base_jobs + inventory_jobs + budget_jobs
    
    return total_jobs

# ==================== РАСЧЁТ ЗАРПЛАТ И ДОХОДОВ ====================

def calculate_average_salary(player_data, employment_data) -> float:
    """
    Рассчитывает среднюю зарплату на основе экономических показателей
    """
    base_salary = player_data["economy"].get("wage", 50000)
    gdp = player_data["economy"]["gdp"]
    population = player_data["state"]["population"]
    gdp_per_capita = gdp / population if population > 0 else 0
    
    unemployment_rate = employment_data["unemployment_rate"]
    
    if unemployment_rate > 8:
        salary_multiplier = 1.0 - (unemployment_rate - 8) / 200
    elif unemployment_rate < 3:
        salary_multiplier = 1.0 + (3 - unemployment_rate) / 100
    else:
        salary_multiplier = 1.0
    
    gdp_factor = min(2.0, max(0.5, gdp_per_capita / 30000))
    inflation = player_data["economy"].get("inflation", 2.0)
    inflation_factor = 1.0 + (inflation / 100)
    
    salary = base_salary * salary_multiplier * gdp_factor * inflation_factor
    
    return int(salary)

def calculate_population_income(player_data, employment_data, avg_salary) -> float:
    """
    Рассчитывает общий доход населения
    """
    employed = employment_data["employed"]
    
    salary_fund = employed * avg_salary
    social_payments = player_data["expenses"].get("social_security", 0)
    
    gdp = player_data["economy"].get("gdp", 1)
    business_income = gdp * 0.08
    
    # Дивиденды от корпораций (население владеет акциями)
    dividend_income = calculate_corporation_dividends(player_data)
    
    total_before_tax = salary_fund + social_payments + business_income + dividend_income
    
    tax_system = player_data["economy"].get("taxes", {})
    income_tax_rate = tax_system.get("income", {}).get("rate", 13)
    
    income_tax = total_before_tax * income_tax_rate / 100
    after_tax = total_before_tax - income_tax
    
    return {
        "total_before_tax": total_before_tax,
        "after_tax": after_tax,
        "income_tax": income_tax,
        "salary_fund": salary_fund,
        "social_payments": social_payments,
        "business_income": business_income,
        "dividend_income": dividend_income
    }

def calculate_corporation_dividends(player_data) -> float:
    """
    Рассчитывает дивиденды от корпораций населению
    """
    country_name = player_data["state"]["statename"]
    corps = get_civil_corporations_by_country(country_name).values()
    
    total_dividends = 0
    for corp in corps:
        corp_state = initialize_corporation_state(corp)
        # 10% от прибыли корпорации идёт на дивиденды
        # Прибыль примерно 5% от бюджета
        profit = corp_state.budget * 0.05
        total_dividends += profit * 0.1
    
    return total_dividends

# ==================== РАСЧЁТ ПОТРЕБЛЕНИЯ ====================

def calculate_consumption_needs(player_data, income_data) -> Dict:
    """
    Рассчитывает потребности населения в товарах и услугах
    """
    population = player_data["state"]["population"]
    after_tax_income = income_data["after_tax"]
    
    income_per_capita = after_tax_income / population if population > 0 else 0
    base_income = MINIMUM_WAGE.get(player_data["state"]["statename"], 10000)
    
    wealth_factor = max(0.5, min(3.0, income_per_capita / base_income))
    
    cost_of_living = player_data["economy"].get("cost_of_living", 100)
    wealth_factor = wealth_factor * (100 / cost_of_living)
    
    needs = {}
    for product_type, base_amount in BASE_POPULATION_NEEDS.items():
        elasticity = INCOME_ELASTICITY.get(product_type, 0.5)
        amount_needed = base_amount * (wealth_factor ** elasticity)
        needs[product_type] = amount_needed * population
    
    return needs

def calculate_consumption(player_data, needs: Dict, income_data: Dict) -> Dict:
    """
    Рассчитывает реальное потребление через покупки у корпораций
    """
    country_name = player_data["state"]["statename"]
    tariff_system = TariffSystem(country_name)
    
    # Получаем все корпорации, доступные для покупки (свои + без эмбарго)
    available_corps = []
    
    # Свои корпорации
    local_corps = list(get_civil_corporations_by_country(country_name).values())
    available_corps.extend(local_corps)
    
    # Импортные корпорации (без эмбарго)
    for corp in get_all_civil_corporations():
        if corp.country != country_name:
            if not tariff_system.is_product_embargoed(corp.country, "all"):
                # Проверяем, нет ли эмбарго на конкретный тип товара
                # (упрощённо - пропускаем)
                available_corps.append(corp)
    
    # Группируем корпорации по типу продукции
    corps_by_product = {}
    for corp in available_corps:
        corp_state = initialize_corporation_state(corp)
        for product_type in corp.products.keys():
            if product_type not in corps_by_product:
                corps_by_product[product_type] = []
            corps_by_product[product_type].append((corp, corp_state))
    
    after_tax_income = income_data["after_tax"]
    total_spent = 0
    consumption = {}
    needs_met = {}
    vat_total = 0
    purchases_by_corp = {}  # Для отслеживания покупок у каждой корпорации
    # ✨ НОВОЕ: Детальный список покупок для прогноза
    detailed_purchases = []
    
    priority_order = sorted(
        needs.keys(),
        key=lambda x: list(BASE_POPULATION_NEEDS.keys()).index(x) if x in BASE_POPULATION_NEEDS else 999
    )
    
    remaining_budget = after_tax_income
    
    for product_type in priority_order:
        if product_type not in needs:
            continue
        
        amount_needed = needs[product_type]
        
        # Находим корпорации, производящие этот продукт
        producers = corps_by_product.get(product_type, [])
        
        if not producers:
            needs_met[product_type] = 0
            continue
        
        # Сортируем по популярности (чем выше, тем больше вероятность покупки)
        producers.sort(key=lambda x: x[1].popularity, reverse=True)
        
        # Рассчитываем долю рынка на основе популярности
        total_popularity = sum(p[1].popularity for p in producers)
        
        units_bought_total = 0
        spent_total = 0
        
        for corp, corp_state in producers:
            # Сколько корпорация может предложить
            available = corp_state.inventory.get(product_type, 0)
            if available <= 0:
                continue
            
            # Доля рынка этой корпорации
            market_share = corp_state.popularity / total_popularity if total_popularity > 0 else 1/len(producers)
            
            # Сколько население хочет купить у этой корпорации
            desired_from_corp = amount_needed * market_share
            
            # Цена продукта
            price = corp.get_product_price(product_type)
            if price <= 0:
                continue
            
            # Сколько могут купить с учётом бюджета
            max_affordable = int(remaining_budget / price) if price > 0 else 0
            if max_affordable <= 0:
                continue
            
            # Реальная покупка
            units_bought = min(available, desired_from_corp, max_affordable)
            
            if units_bought > 0:
                spent = units_bought * price
                
                # Проверяем, хватит ли бюджета
                if spent > remaining_budget:
                    units_bought = int(remaining_budget / price)
                    spent = units_bought * price
                
                if units_bought > 0:
                    # Списываем товар со склада корпорации
                    update_corporation_inventory(corp.id, product_type, units_bought, add=False)
                    
                    # Добавляем деньги корпорации
                    update_corporation_budget(corp.id, spent, add=True)
                    
                    # Запоминаем покупку для общей статистики
                    if corp.id not in purchases_by_corp:
                        purchases_by_corp[corp.id] = 0
                    purchases_by_corp[corp.id] += spent
                    
                    # ✨ НОВОЕ: Сохраняем детальную информацию о покупке
                    detailed_purchases.append({
                        "corporation_id": corp.id,
                        "corporation_name": corp.name,
                        "product": product_type,
                        "quantity": units_bought,
                        "price_per_unit": price,
                        "total": spent,
                        "timestamp": str(datetime.now())
                    })
                    
                    remaining_budget -= spent
                    spent_total += spent
                    units_bought_total += units_bought
                    
                    # Немного повышаем популярность при покупке
                    increase_corporation_popularity(corp.id, 0.1)
        
        if units_bought_total > 0:
            total_spent += spent_total
            consumption[product_type] = units_bought_total
            met_percent = (units_bought_total / amount_needed) * 100 if amount_needed > 0 else 100
            needs_met[product_type] = met_percent
        else:
            needs_met[product_type] = 0
    
    # Рассчитываем НДС с продаж
    vat_rate = player_data["economy"].get("taxes", {}).get("vat", {}).get("rate", 18)
    vat = total_spent * vat_rate / 100
    
    return {
        "total_spent": total_spent,
        "remaining_budget": remaining_budget,
        "consumption": consumption,
        "needs_met": needs_met,
        "vat": vat,
        "purchases_by_corp": purchases_by_corp,
        "detailed_purchases": detailed_purchases  # ✨ НОВОЕ: добавляем в результат
    }

def get_product_price(product_type: str) -> float:
    """Получает среднюю цену продукта из гражданских корпораций"""
    # В реальности нужно усреднять по всем корпорациям
    prices = {
        "food_products": 100,
        "clothing": 50,
        "consumer_electronics": 500,
        "medical_supplies": 30,
        "furniture": 200,
        "household_goods": 50,
        "buses": 50000,
        "cars": 15000,
        "smartphones": 500,
        "computers": 1000,
        "software": 100,
        "telecom_services": 30,
        "internet_services": 40,
        "mobile_services": 35,
        "streaming": 10,
        "banking": 5,
        "insurance": 200,
        "healthcare_services": 300,
        "education": 500,
        "entertainment": 50
    }
    return prices.get(product_type, 100)

# ==================== ОБНОВЛЕНИЕ СОЦИАЛЬНЫХ ПОКАЗАТЕЛЕЙ ====================

def update_social_indicators(player_data, employment_data, consumption_data, income_data):
    """
    Обновляет социальные показатели на основе экономической ситуации
    """
    unemployment_rate = employment_data["unemployment_rate"]
    needs_met = consumption_data.get("needs_met", {})
    
    stability = player_data["state"].get("stability", 50)
    happiness = player_data["state"].get("happiness", 50)
    trust = player_data["state"].get("trust", 50)
    
    # Влияние безработицы
    if unemployment_rate > 8:
        stability -= (unemployment_rate - 8) / 2
        happiness -= (unemployment_rate - 8) / 2
        trust -= (unemployment_rate - 8) / 3
    elif unemployment_rate < 3:
        stability += (3 - unemployment_rate) / 2
        happiness += (3 - unemployment_rate) / 2
    
    # Влияние удовлетворения потребностей
    if needs_met:
        avg_needs_met = sum(needs_met.values()) / len(needs_met)
        
        if avg_needs_met < 70:
            stability -= (70 - avg_needs_met) / 5
            happiness -= (70 - avg_needs_met) / 5
        elif avg_needs_met > 90:
            stability += (avg_needs_met - 90) / 10
            happiness += (avg_needs_met - 90) / 10
    
    # Влияние разнообразия корпораций
    country_name = player_data["state"]["statename"]
    corps = get_civil_corporations_by_country(country_name).values()
    corp_count = len(corps)
    happiness += corp_count / 20  # +5 за 100 корпораций
    
    # Влияние зарплат
    cost_of_living = player_data["economy"].get("cost_of_living", 100)
    avg_salary = player_data["population_data"].get("average_salary", 50000)
    purchasing_power = avg_salary / cost_of_living
    
    if purchasing_power < 300:
        happiness -= (300 - purchasing_power) / 30
    elif purchasing_power > 700:
        happiness += (purchasing_power - 700) / 50
    
    # Влияние налогов
    tax_system = player_data["economy"].get("taxes", {})
    total_tax_burden = (
        tax_system.get("income", {}).get("rate", 0) +
        tax_system.get("vat", {}).get("rate", 0) * 0.5
    )
    
    if total_tax_burden > 40:
        happiness -= (total_tax_burden - 40) / 5
    
    # Ограничиваем показатели
    player_data["state"]["stability"] = max(0, min(100, stability))
    player_data["state"]["happiness"] = max(0, min(100, happiness))
    player_data["state"]["trust"] = max(0, min(100, trust))
    
    popularity = (happiness * 0.6 + stability * 0.4)
    player_data["politics"]["popularity"] = max(0, min(100, popularity))

# ==================== ГЛАВНАЯ ФУНКЦИЯ ОБНОВЛЕНИЯ ====================

def update_population(player_data) -> Dict:
    """
    ПОЛНОЕ обновление всех данных о населении
    Вызывается ежемесячно
    """
    # 1. Рассчитываем занятость от инфраструктуры и корпораций
    employment_data = calculate_employment(player_data)
    
    # 2. Рассчитываем среднюю зарплату
    avg_salary = calculate_average_salary(player_data, employment_data)
    
    # 3. Рассчитываем доходы населения
    income_data = calculate_population_income(player_data, employment_data, avg_salary)
    
    # 4. Рассчитываем потребности
    needs = calculate_consumption_needs(player_data, income_data)
    
    # 5. Рассчитываем реальное потребление (покупки у корпораций)
    consumption_data = calculate_consumption(player_data, needs, income_data)
    
    # 6. Обновляем сбережения
    old_savings = player_data["population_data"].get("savings", 0)
    new_savings = old_savings + income_data["after_tax"] - consumption_data["total_spent"]
    
    # 7. Сохраняем в population_data
    if "population_data" not in player_data:
        player_data["population_data"] = {}
    
    player_data["population_data"].update({
        "employed": employment_data["employed"],
        "unemployed": employment_data["unemployed"],
        "unemployment_rate": employment_data["unemployment_rate"],
        "labor_force_participation": employment_data["labor_force_participation"],
        "average_salary": avg_salary,
        "total_income": income_data["after_tax"],
        "total_income_before_tax": income_data["total_before_tax"],
        "income_tax_paid": income_data["income_tax"],
        "dividend_income": income_data.get("dividend_income", 0),
        "savings": new_savings,
        "consumption": consumption_data["consumption"],
        "needs_met": consumption_data["needs_met"],
        "total_spent": consumption_data["total_spent"],
        "vat_paid": consumption_data["vat"],
        "sector_breakdown": employment_data["sector_breakdown"],
        "corporation_jobs": employment_data["corporation_jobs"],
        # ✨ НОВОЕ: сохраняем детальные покупки
        "detailed_purchases": consumption_data.get("detailed_purchases", []),
        "last_update": str(datetime.now())
    })
    
    # 8. Добавляем налоги в бюджет
    player_data["economy"]["budget"] += income_data["income_tax"] + consumption_data["vat"]
    
    # 9. Обновляем социальные показатели
    update_social_indicators(player_data, employment_data, consumption_data, income_data)
    
    # 10. Возвращаем сводку для отчёта
    return {
        "country": player_data["state"]["statename"],
        "employment_rate": 100 - employment_data["unemployment_rate"],
        "avg_salary": avg_salary,
        "total_income": income_data["after_tax"],
        "total_spent": consumption_data["total_spent"],
        "savings": new_savings,
        "taxes_collected": income_data["income_tax"] + consumption_data["vat"],
        "needs_met_avg": sum(consumption_data["needs_met"].values()) / len(consumption_data["needs_met"]) if consumption_data["needs_met"] else 0,
        "labor_force_participation": employment_data["labor_force_participation"],
        "corporation_jobs": employment_data["corporation_jobs"],
        "detailed_purchases_count": len(consumption_data.get("detailed_purchases", []))
    }

# ==================== ФОНОВАЯ ЗАДАЧА ====================

async def population_update_loop(bot_instance):
    """Фоновая задача для ежемесячного обновления населения"""
    await bot_instance.wait_until_ready()
    
    last_update = None
    
    while not bot_instance.is_closed():
        try:
            now = datetime.now()
            
            if last_update is None or (now - last_update).days >= 1:
                print(f"👥 Запуск ежемесячного обновления населения: {now.strftime('%Y-%m-%d %H:%M:%S')}")
                
                states = load_states()
                results = []
                
                for state_id, player_data in states["players"].items():
                    if "assigned_to" not in player_data:
                        continue
                    
                    try:
                        summary = update_population(player_data)
                        results.append(summary)
                        
                        if player_data["state"]["happiness"] < 30:
                            try:
                                user = await bot_instance.fetch_user(int(player_data["assigned_to"]))
                                if user:
                                    embed = discord.Embed(
                                        title="⚠️ КРИЗИС!",
                                        description=f"Счастье населения упало до {player_data['state']['happiness']:.1f}%!",
                                        color=discord.Color.red()
                                    )
                                    embed.add_field(
                                        name="Причины",
                                        value=f"📈 Безработица: {player_data['population_data']['unemployment_rate']:.1f}%\n"
                                              f"📦 Удовлетворение потребностей: {summary['needs_met_avg']:.1f}%\n"
                                              f"👥 Участие в рынке труда: {player_data['population_data']['labor_force_participation']:.1f}%",
                                        inline=False
                                    )
                                    await user.send(embed=embed)
                            except:
                                pass
                        
                        elif player_data["state"]["happiness"] > 80:
                            try:
                                user = await bot_instance.fetch_user(int(player_data["assigned_to"]))
                                if user:
                                    embed = discord.Embed(
                                        title="🎉 ЭКОНОМИЧЕСКИЙ РОСТ!",
                                        description=f"Счастье населения выросло до {player_data['state']['happiness']:.1f}%!",
                                        color=discord.Color.green()
                                    )
                                    embed.add_field(
                                        name="Показатели",
                                        value=f"💵 Средняя зарплата: ${player_data['population_data']['average_salary']:,.0f}\n"
                                              f"💰 Сбережения: ${player_data['population_data']['savings']:,.0f}\n"
                                              f"📊 Безработица: {player_data['population_data']['unemployment_rate']:.1f}%",
                                        inline=False
                                    )
                                    await user.send(embed=embed)
                            except:
                                pass
                                
                    except Exception as e:
                        print(f"❌ Ошибка при обновлении {state_id}: {e}")
                
                save_states(states)
                last_update = now
                
                print(f"✅ Обновлено {len(results)} государств")
                for r in results[:3]:
                    print(f"   {r['country']}: занятость {r['employment_rate']:.1f}%, "
                          f"корп. рабочих мест {r['corporation_jobs']}, налоги ${r['taxes_collected']:,.0f}, "
                          f"покупок записано: {r['detailed_purchases_count']}")
            
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"❌ Ошибка в population_update_loop: {e}")
            await asyncio.sleep(3600)

# ==================== ФУНКЦИИ ДЛЯ ОТОБРАЖЕНИЯ ====================

async def show_population_menu(interaction_or_ctx, user_id: int):
    """Показать меню населения"""
    from utils import load_states
    
    states = load_states()
    
    state_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            state_data = data
            break
    
    if not state_data:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message("❌ У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("❌ У вас нет государства!")
        return
    
    employment = calculate_employment(state_data)
    avg_salary = calculate_average_salary(state_data, employment)
    income_data = calculate_population_income(state_data, employment, avg_salary)
    
    # Получаем информацию о корпорациях
    country_name = state_data["state"]["statename"]
    corps = get_civil_corporations_by_country(country_name).values()
    corps_state = load_corporations_state()
    
    corp_stats = f"Всего корпораций: {len(corps)}\n"
    total_inventory = 0
    total_corp_budget = 0
    
    for corp in corps:
        if corp.id in corps_state["corporations"]:
            state = corps_state["corporations"][corp.id]
            total_inventory += sum(state.inventory.values())
            total_corp_budget += state.budget
    
    embed = discord.Embed(
        title=f"👥 Население {state_data['state']['statename']}",
        color=DARK_THEME_COLOR
    )
    
    embed.add_field(
        name="📊 Занятость",
        value=f"👷 Работает: {format_number(employment['employed'])}\n"
              f"🚫 Безработных: {format_number(employment['unemployed'])}\n"
              f"📈 Уровень безработицы: {employment['unemployment_rate']:.1f}%\n"
              f"🏭 Рабочих мест всего: {format_number(employment['jobs_available'])}\n"
              f"🏢 В корпорациях: {format_number(employment['corporation_jobs'])}",
        inline=True
    )
    
    embed.add_field(
        name="💰 Доходы",
        value=f"💵 Средняя зарплата: ${avg_salary:,.0f}\n"
              f"📥 Доход населения: ${income_data['after_tax']:,.0f}\n"
              f"📈 Дивиденды: ${income_data.get('dividend_income', 0):,.0f}\n"
              f"🏦 Сбережения: ${state_data['population_data'].get('savings', 0):,.0f}",
        inline=True
    )
    
    embed.add_field(
        name="🏢 Корпорации",
        value=f"📦 Товаров на складах: {format_number(total_inventory)} ед.\n"
              f"💰 Бюджет корпораций: ${format_billion(total_corp_budget)}",
        inline=False
    )
    
    consumption = state_data["population_data"].get("consumption", {})
    if consumption:
        top_consumption = list(consumption.items())[:3]
        cons_text = ""
        for product, amount in top_consumption:
            product_name = CIVIL_PRODUCT_NAMES.get(product, product)
            cons_text += f"• {product_name}: {format_number(amount)} ед.\n"
        embed.add_field(name="📦 Основные покупки", value=cons_text, inline=False)
    
    # Показываем информацию о детальных покупках
    detailed_purchases = state_data["population_data"].get("detailed_purchases", [])
    if detailed_purchases:
        unique_corps = set(p["corporation_name"] for p in detailed_purchases[-10:])
        embed.add_field(
            name="📊 Активность корпораций",
            value=f"Куплено товаров у {len(unique_corps)} корпораций\n"
                  f"Всего транзакций: {len(detailed_purchases)}",
            inline=False
        )
    
    embed.add_field(
        name="📈 Социальные показатели",
        value=f"😊 Счастье: {state_data['state']['happiness']:.1f}%\n"
              f"⚖️ Стабильность: {state_data['state']['stability']:.1f}%\n"
              f"🤝 Доверие: {state_data['state']['trust']:.1f}%\n"
              f"📊 Популярность: {state_data['politics']['popularity']:.1f}%",
        inline=False
    )
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, ephemeral=True)

# ==================== ЭКСПОРТ ====================

__all__ = [
    'population_update_loop',
    'show_population_menu',
    'update_population',
    'calculate_employment',
    'calculate_average_salary',
    'BASE_POPULATION_NEEDS',
    'MINIMUM_WAGE'
]

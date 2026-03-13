# civil_store.py - Модуль для покупки гражданской продукции у корпораций
# НОВАЯ ВЕРСИЯ: Страна → Специализация → Корпорация
# Корпорации теперь самостоятельные агенты экономики

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import asyncio
import json
from datetime import datetime, timedelta
import math
from typing import Dict, List, Optional, Tuple

# Импортируем базу данных гражданских корпораций
from civil_corporations_db import (
    get_civil_corporations_by_country, get_civil_corporation, 
    get_all_civil_corporations, get_civil_corporations_by_specialization,
    CIVIL_PRODUCT_NAMES, ALL_CIVIL_CORPORATIONS,
    load_corporations_state, save_corporations_state, initialize_corporation_state
)

# Импортируем таможенную систему
from trade_tariffs import TariffSystem

# Импортируем вспомогательные функции
from utils import get_user_id, get_user_name, send_response, format_number, format_billion, format_time, load_states, save_states

# Файл для хранения активных заказов
CIVIL_PRODUCTION_QUEUE_FILE = 'civil_production_queue.json'

# Цвет для эмбедов в тёмной теме Discord
DARK_THEME_COLOR = 0x2b2d31

# ==================== КАТЕГОРИИ СПЕЦИАЛИЗАЦИЙ ====================

# Группировка специализаций по основным секторам экономики
SPECIALIZATION_CATEGORIES = {
    "Автомобилестроение": ["cars", "trucks", "buses", "auto_parts"],
    "IT и Технологии": ["software", "it_services", "cloud_services", "cybersecurity", "tech_equipment"],
    "Электроника": ["consumer_electronics", "computers", "smartphones", "tablets"],
    "Телекоммуникации": ["telecom_services", "mobile_services", "internet_services", "telecom_equipment"],
    "Финансы": ["banking", "investments", "fintech", "insurance"],
    "Ритейл": ["retail", "ecommerce", "supermarkets"],
    "Промышленность": ["industrial_equipment", "machine_tools", "industrial_robots", "construction_machinery"],
    "Энергетика": ["energy_equipment", "oil", "gas_supply", "electricity"],
    "Авиация и космос": ["aerospace_equipment", "airlines", "drones", "satellite_services"],
    "Фармацевтика": ["pharmaceuticals", "medical_supplies", "medical_equipment"],
    "Продукты питания": ["food_products", "beverages", "restaurants", "fast_food"],
    "Товары для дома": ["furniture", "household_goods", "clothing", "footwear", "cosmetics"],
    "Медиа и развлечения": ["media", "entertainment", "streaming", "gaming"],
    "Логистика": ["logistics", "freight", "passenger_transport"],
    "Образование": ["education", "online_courses"],
    "Строительство": ["construction", "real_estate", "property_management"],
    "Химия": ["chemicals", "fertilizers"],
    "Сельское хозяйство": ["agricultural_machinery", "fertilizers"]
}

# Обратный маппинг: специализация -> категория
SPECIALIZATION_TO_CATEGORY = {}
for category, specializations in SPECIALIZATION_CATEGORIES.items():
    for spec in specializations:
        SPECIALIZATION_TO_CATEGORY[spec] = category

# Человекочитаемые названия специализаций
SPECIALIZATION_NAMES = {
    # Автомобилестроение
    "cars": "Легковые автомобили",
    "trucks": "Грузовые автомобили",
    "buses": "Автобусы",
    "auto_parts": "Автозапчасти",
    
    # IT и Технологии
    "software": "Программное обеспечение",
    "it_services": "IT-услуги",
    "cloud_services": "Облачные услуги",
    "cybersecurity": "Кибербезопасность",
    "tech_equipment": "Технологическое оборудование",
    
    # Электроника
    "consumer_electronics": "Бытовая электроника",
    "computers": "Компьютеры",
    "smartphones": "Смартфоны",
    "tablets": "Планшеты",
    
    # Телекоммуникации
    "telecom_services": "Телеком-услуги",
    "mobile_services": "Мобильная связь",
    "internet_services": "Интернет-услуги",
    "telecom_equipment": "Телеком-оборудование",
    
    # Финансы
    "banking": "Банковские услуги",
    "investments": "Инвестиции",
    "fintech": "Финтех",
    "insurance": "Страхование",
    
    # Промышленность
    "industrial_equipment": "Промышленное оборудование",
    "machine_tools": "Станки",
    "industrial_robots": "Промышленные роботы",
    "construction_machinery": "Строительная техника",
    
    # Энергетика
    "energy_equipment": "Энергетическое оборудование",
    "oil": "Нефть",
    "gas_supply": "Газоснабжение",
    "electricity": "Электроэнергия",
    
    # Авиация
    "aerospace_equipment": "Авиационное оборудование",
    "airlines": "Авиаперевозки",
    "drones": "Беспилотники",
    "satellite_services": "Спутниковые услуги",
    
    # Фармацевтика
    "pharmaceuticals": "Лекарства",
    "medical_supplies": "Медизделия",
    "medical_equipment": "Медоборудование",
    
    # Продукты
    "food_products": "Продукты питания",
    "beverages": "Напитки",
    "restaurants": "Рестораны",
    "fast_food": "Фаст-фуд",
    
    # Товары
    "furniture": "Мебель",
    "household_goods": "Товары для дома",
    "clothing": "Одежда",
    "footwear": "Обувь",
    "cosmetics": "Косметика",
    
    # Медиа
    "media": "Медиа",
    "entertainment": "Развлечения",
    "streaming": "Стриминг",
    "gaming": "Игры",
    
    # Логистика
    "logistics": "Логистика",
    "freight": "Грузоперевозки",
    "passenger_transport": "Пассажирские перевозки",
    
    # Образование
    "education": "Образование",
    "online_courses": "Онлайн-курсы",
    
    # Строительство
    "construction": "Строительство",
    "real_estate": "Недвижимость",
    "property_management": "Управление недвижимостью",
    
    # Химия
    "chemicals": "Химия",
    "fertilizers": "Удобрения",
    
    # Сельское хозяйство
    "agricultural_machinery": "Сельхозтехника"
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_specialization_category(specialization: str) -> str:
    """Получить категорию для специализации"""
    return SPECIALIZATION_TO_CATEGORY.get(specialization, "Другое")

def get_unique_specializations_for_country(country: str) -> List[str]:
    """Получить уникальные специализации корпораций в стране"""
    specializations = set()
    corps = get_civil_corporations_by_country(country).values()
    for corp in corps:
        if hasattr(corp, 'specialization') and corp.specialization:
            for spec in corp.specialization:
                specializations.add(spec)
    return sorted(list(specializations))

def get_corporations_by_specialization(country: str, specialization: str) -> List:
    """Получить корпорации в стране по специализации"""
    result = []
    corps = get_civil_corporations_by_country(country).values()
    for corp in corps:
        if hasattr(corp, 'specialization') and specialization in corp.specialization:
            result.append(corp)
    return result

def get_corporation_inventory(corp_id: str) -> Dict:
    """Получить инвентарь корпорации"""
    state = load_corporations_state()
    if corp_id in state["corporations"]:
        return state["corporations"][corp_id].inventory
    return {}

def update_corporation_inventory(corp_id: str, product_type: str, quantity: int, add: bool = True):
    """Обновить инвентарь корпорации"""
    state = load_corporations_state()
    if corp_id in state["corporations"]:
        corp = state["corporations"][corp_id]
        if add:
            corp.add_to_inventory(product_type, quantity)
        else:
            corp.remove_from_inventory(product_type, quantity)
        save_corporations_state(state)
        return True
    return False

def update_corporation_budget(corp_id: str, amount: float, add: bool = True):
    """Обновить бюджет корпорации"""
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

# ==================== ВРЕМЯ ПРОИЗВОДСТВА ====================

CIVIL_PRODUCTION_SPEED = {
    # Автомобили и транспорт
    "cars": 3600, "trucks": 7200, "buses": 10800,
    "agricultural_machinery": 5400, "construction_machinery": 7200,
    
    # Оборудование
    "industrial_equipment": 3600, "machine_tools": 5400,
    "industrial_robots": 7200, "energy_equipment": 7200,
    "electrical_equipment": 1800, "telecom_equipment": 2700,
    "tech_equipment": 3600, "aerospace_equipment": 21600,
    
    # Комплектующие
    "auto_parts": 900, "electronics_components": 1200,
    
    # Потребительские товары
    "clothing": 600, "medical_supplies": 900,
    "medical_equipment": 3600, "sanitary_products": 300,
    
    # Дроны
    "drones": 1800, "fpv_drones": 900,
    
    # Продукты
    "food_products": 120,
    
    # Химия и фармацевтика
    "chemicals": 1800, "pharmaceuticals": 2700,
    
    # Товары для дома
    "furniture": 3600, "household_goods": 1800, "consumer_electronics": 2700,
    
    # Услуги (мгновенно)
    "banking": 0, "insurance": 0, "telecom_services": 0,
    "internet_services": 0, "mobile_services": 0, "cloud_services": 0,
    "it_services": 0, "software": 0, "streaming": 0,
    "education": 0, "online_courses": 0, "entertainment": 0,
    "logistics": 0, "freight": 0, "passenger_transport": 0,
    "airlines": 0, "construction": 0, "real_estate": 0,
    "healthcare_services": 0, "hospital_services": 0, "dentistry": 0,
    "consulting": 0, "legal": 0, "accounting": 0, "marketing": 0
}

# ==================== СИСТЕМА ЗАГРУЗКИ/СОХРАНЕНИЯ ПРОИЗВОДСТВА ====================

def load_civil_production_queue():
    """Загрузка очереди гражданского производства"""
    try:
        with open(CIVIL_PRODUCTION_QUEUE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_orders": [], "completed_orders": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"active_orders": [], "completed_orders": []}
    except json.JSONDecodeError:
        return {"active_orders": [], "completed_orders": []}

def save_civil_production_queue(data):
    """Сохранение очереди гражданского производства"""
    with open(CIVIL_PRODUCTION_QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_civil_production_time(product_type, quantity=1):
    """Получить общее время производства для заказа"""
    base_time = CIVIL_PRODUCTION_SPEED.get(product_type, 3600)
    
    # Услуги производятся мгновенно
    if base_time == 0:
        return 0
    
    if quantity <= 1:
        return base_time
    elif quantity <= 5:
        total = base_time
        for i in range(1, quantity):
            total += base_time * (0.8 ** i)
        return total
    elif quantity <= 20:
        return base_time * (1 + (quantity - 1) * 0.5)
    else:
        return base_time * (1 + (quantity - 1) * 0.3)

# ==================== ФУНКЦИЯ ПРОВЕРКИ БЛОКИРОВКИ ТОРГОВЛИ ====================

def is_trade_blocked(tariff_system, buyer_country: str, seller_country: str, product_type: str) -> bool:
    """Проверяет, заблокирована ли торговля между странами"""
    if tariff_system.is_product_embargoed(seller_country, product_type):
        return True
    
    seller_tariff = TariffSystem(seller_country)
    if seller_tariff.is_product_embargoed(buyer_country, product_type):
        return True
    
    return False

# ==================== МОДАЛЬНОЕ ОКНО ДЛЯ ВВОДА КОЛИЧЕСТВА ====================

class CivilQuantityModal(Modal, title="Введите количество"):
    def __init__(self, corporation, product_type, product, user_id, player_country, tariff_system, original_message):
        super().__init__()
        self.corporation = corporation
        self.product_type = product_type
        self.product = product
        self.user_id = user_id
        self.player_country = player_country
        self.tariff_system = tariff_system
        self.original_message = original_message
        
        # Проверяем, есть ли продукт в инвентаре корпорации
        self.corp_state = initialize_corporation_state(corporation)
        available = self.corp_state.inventory.get(product_type, 0)
        
        max_quantity = min(1000, available if available > 0 else 1000)
        
        self.quantity_input = TextInput(
            label=f"Количество (доступно: {available}, макс: {max_quantity})",
            placeholder="Введите число",
            min_length=1,
            max_length=4,
            required=True
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > 1000:
                await interaction.response.send_message("❌ Количество должно быть от 1 до 1000!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        # Проверяем наличие в инвентаре
        self.corp_state = initialize_corporation_state(self.corporation)
        available = self.corp_state.inventory.get(self.product_type, 0)
        
        if available > 0 and quantity > available:
            await interaction.response.send_message(
                f"❌ У корпорации недостаточно товара! Доступно: {available}",
                ephemeral=True
            )
            return
        
        # Удаляем оригинальное сообщение
        try:
            await self.original_message.delete()
        except:
            pass
        
        view = CivilPurchaseConfirmation(
            self.corporation, self.product_type, self.product, quantity,
            self.user_id, self.player_country, self.tariff_system
        )
        
        total_price = self.product['price'] * quantity
        prod_time = get_civil_production_time(self.product_type, quantity)
        
        embed = discord.Embed(
            title="Подтверждение покупки",
            description="Проверьте детали заказа:",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Корпорация", value=self.corporation.name, inline=True)
        embed.add_field(name="Продукт", value=self.product['name'], inline=True)
        embed.add_field(name="Количество", value=str(quantity), inline=True)
        embed.add_field(name="Стоимость", value=f"${total_price:,}", inline=True)
        
        if prod_time > 0:
            embed.add_field(name="Время производства", value=format_time(prod_time), inline=True)
        else:
            embed.add_field(name="Тип услуги", value="Мгновенное оказание", inline=True)
        
        if available > 0:
            embed.add_field(name="Наличие на складе", value=f"{available} ед.", inline=True)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ==================== ВЫБОР СТРАНЫ ====================

class CountrySelect(Select):
    """Выпадающий список для выбора страны"""
    def __init__(self, user_id, player_country, original_message, tariff_system):
        self.user_id = user_id
        self.player_country = player_country
        self.original_message = original_message
        self.tariff_system = tariff_system
        options = []
        
        countries = list(ALL_CIVIL_CORPORATIONS.keys())
        
        for country in countries[:25]:
            available_count = 0
            total_count = 0
            for corp_id, corp in ALL_CIVIL_CORPORATIONS[country].items():
                if hasattr(corp, 'products') and corp.products:
                    total_count += 1
                    if not is_trade_blocked(self.tariff_system, player_country, corp.country, "all"):
                        available_count += 1
            
            if available_count == 0:
                emoji = "❌"
            elif available_count < total_count:
                emoji = "⚠️"
            else:
                emoji = "✅"
            
            options.append(
                discord.SelectOption(
                    label=country,
                    description=f"Корпораций: {available_count}/{total_count}",
                    value=country,
                    emoji=emoji
                )
            )
        
        super().__init__(
            placeholder="Выберите страну...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        country = self.values[0]
        
        try:
            await self.original_message.delete()
        except:
            pass
        
        # Переходим к выбору специализации в выбранной стране
        await show_specializations_for_country(interaction, self.user_id, self.player_country, country, self.tariff_system)


# ==================== ВЫБОР СПЕЦИАЛИЗАЦИИ ====================

class SpecializationCategorySelect(Select):
    """Выбор категории специализации в стране"""
    def __init__(self, user_id, player_country, country, tariff_system, categories_with_counts):
        self.user_id = user_id
        self.player_country = player_country
        self.country = country
        self.tariff_system = tariff_system
        
        options = []
        for category_name, count in list(categories_with_counts.items())[:25]:
            options.append(
                discord.SelectOption(
                    label=category_name,
                    description=f"{count} корпораций",
                    value=category_name
                )
            )
        
        super().__init__(
            placeholder="Выберите категорию...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        category = self.values[0]
        
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Показываем конкретные специализации в этой категории
        await show_specializations_in_category(
            interaction, self.user_id, self.player_country, 
            self.country, category, self.tariff_system
        )


class SpecializationSelect(Select):
    """Выбор конкретной специализации"""
    def __init__(self, user_id, player_country, country, category, specializations, tariff_system):
        self.user_id = user_id
        self.player_country = player_country
        self.country = country
        self.category = category
        self.tariff_system = tariff_system
        
        options = []
        for spec in specializations[:25]:
            spec_name = SPECIALIZATION_NAMES.get(spec, spec)
            # Считаем доступные корпорации с этой специализацией
            corps = get_corporations_by_specialization(country, spec)
            available = 0
            for corp in corps:
                if not is_trade_blocked(self.tariff_system, player_country, corp.country, "all"):
                    available += 1
            
            options.append(
                discord.SelectOption(
                    label=spec_name,
                    description=f"{available} корпораций",
                    value=spec
                )
            )
        
        super().__init__(
            placeholder="Выберите специализацию...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        specialization = self.values[0]
        
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Показываем корпорации с этой специализацией
        await show_corporations_by_specialization(
            interaction, self.user_id, self.player_country,
            self.country, specialization, self.tariff_system
        )


# ==================== ВЫБОР КОРПОРАЦИИ ====================

class CorporationSelect(Select):
    """Выбор корпорации по специализации"""
    def __init__(self, user_id, player_country, country, specialization, corporations, tariff_system):
        self.user_id = user_id
        self.player_country = player_country
        self.country = country
        self.specialization = specialization
        self.tariff_system = tariff_system
        
        options = []
        for corp in corporations[:25]:
            # Проверяем доступность
            available = not is_trade_blocked(self.tariff_system, player_country, corp.country, "all")
            
            # Получаем состояние корпорации
            corp_state = initialize_corporation_state(corp)
            inventory = corp_state.inventory.get(specialization, 0)
            popularity = corp_state.popularity
            
            status = "✅" if available else "❌"
            desc = f"Популярность: {popularity}% | В наличии: {inventory}"
            
            options.append(
                discord.SelectOption(
                    label=f"{status} {corp.name[:80]}",
                    description=desc,
                    value=corp.id,
                    default=not available
                )
            )
        
        super().__init__(
            placeholder="Выберите корпорацию...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        corp_id = self.values[0]
        corp = get_civil_corporation(corp_id)
        
        if not corp:
            await interaction.response.send_message("❌ Корпорация не найдена!", ephemeral=True)
            return
        
        # Проверяем доступность
        if is_trade_blocked(self.tariff_system, self.player_country, corp.country, "all"):
            await interaction.response.send_message(
                f"❌ Корпорация {corp.name} недоступна из-за эмбарго!",
                ephemeral=True
            )
            return
        
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Показываем информацию о корпорации и её продуктах
        await show_corporation_details(
            interaction, self.user_id, self.player_country,
            corp, self.specialization, self.tariff_system
        )


# ==================== ДЕТАЛИ КОРПОРАЦИИ ====================

async def show_corporation_details(interaction, user_id, player_country, corporation, specialization, tariff_system):
    """Показать детали корпорации и доступные продукты"""
    
    # Получаем состояние корпорации
    corp_state = initialize_corporation_state(corporation)
    inventory = corp_state.inventory.get(specialization, 0)
    
    embed = discord.Embed(
        title=corporation.name,
        description=corporation.description,
        color=DARK_THEME_COLOR
    )
    
    if hasattr(corporation, 'founded') and corporation.founded:
        embed.add_field(name="Год основания", value=corporation.founded, inline=True)
    
    embed.add_field(name="Страна", value=corporation.country, inline=True)
    embed.add_field(name="Город", value=corporation.city, inline=True)
    
    # Показываем финансовое состояние
    embed.add_field(name="💰 Бюджет", value=f"${corp_state.budget:,.0f}", inline=True)
    embed.add_field(name="📊 Популярность", value=f"{corp_state.popularity}%", inline=True)
    embed.add_field(name="📦 Наличие", value=f"{inventory} ед.", inline=True)
    
    # Информация о продукте
    if specialization in corporation.products:
        product = corporation.products[specialization]
        embed.add_field(
            name="📦 Продукт",
            value=f"**{product['name']}**\n{product['description']}",
            inline=False
        )
        embed.add_field(name="💰 Цена", value=f"${product['price']:,}", inline=True)
        
        prod_time = CIVIL_PRODUCTION_SPEED.get(specialization, 3600)
        if prod_time > 0:
            embed.add_field(name="⏱️ Время производства", value=format_time(prod_time), inline=True)
        else:
            embed.add_field(name="⏱️ Тип", value="Услуга (мгновенно)", inline=True)
    
    view = CorporationActionView(
        user_id, player_country, corporation, specialization,
        corporation.products.get(specialization), tariff_system
    )
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CorporationActionView(View):
    """Действия с корпорацией"""
    def __init__(self, user_id, player_country, corporation, product_type, product, tariff_system):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.player_country = player_country
        self.corporation = corporation
        self.product_type = product_type
        self.product = product
        self.tariff_system = tariff_system
        
        # Кнопка покупки
        buy_button = Button(label="🛒 Купить", style=discord.ButtonStyle.secondary)
        buy_button.callback = self.buy_callback
        self.add_item(buy_button)
        
        # Кнопка назад
        back_button = Button(label="◀ Назад к списку", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    async def buy_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            await interaction.message.delete()
        except:
            pass
        
        view = CivilQuantitySelector(
            self.corporation, self.product_type, self.product,
            self.user_id, self.player_country, self.tariff_system
        )
        
        embed = discord.Embed(
            title=self.product.get('name', 'Неизвестный продукт'),
            description=self.product.get('description', 'Нет описания'),
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Цена", value=f"${self.product.get('price', 0):,}", inline=True)
        
        prod_time = CIVIL_PRODUCTION_SPEED.get(self.product_type, 3600)
        if prod_time > 0:
            embed.add_field(name="Время производства", value=format_time(prod_time), inline=True)
        else:
            embed.add_field(name="Тип", value="Услуга", inline=True)
        
        # Показываем наличие на складе
        corp_state = initialize_corporation_state(self.corporation)
        available = corp_state.inventory.get(self.product_type, 0)
        if available > 0:
            embed.add_field(name="📦 На складе", value=f"{available} ед.", inline=True)
        
        product_type_name = SPECIALIZATION_NAMES.get(self.product_type, self.product_type)
        embed.add_field(name="Тип", value=product_type_name, inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Возвращаемся к выбору специализации
        await show_specializations_for_country(
            interaction, self.user_id, self.player_country,
            self.corporation.country, self.tariff_system
        )


# ==================== ВЫБОР КОЛИЧЕСТВА ====================

class CivilQuantitySelector(View):
    """Выбор количества и подтверждение покупки"""
    def __init__(self, corporation, product_type, product, user_id, player_country, tariff_system):
        super().__init__(timeout=300)
        self.corporation = corporation
        self.product_type = product_type
        self.product = product
        self.user_id = user_id
        self.player_country = player_country
        self.tariff_system = tariff_system
        self.quantity = 1
        
        # Получаем доступное количество
        self.corp_state = initialize_corporation_state(corporation)
        self.available = self.corp_state.inventory.get(product_type, 0)
        
        minus_button = Button(label="➖", style=discord.ButtonStyle.secondary)
        minus_button.callback = self.decrease_quantity
        self.add_item(minus_button)
        
        self.quantity_label = Button(
            label=f"{self.quantity}",
            style=discord.ButtonStyle.secondary,
            disabled=True
        )
        self.add_item(self.quantity_label)
        
        plus_button = Button(label="➕", style=discord.ButtonStyle.secondary)
        plus_button.callback = self.increase_quantity
        self.add_item(plus_button)
        
        manual_button = Button(
            label="Ввести число",
            style=discord.ButtonStyle.secondary
        )
        manual_button.callback = self.manual_input
        self.add_item(manual_button)
        
        buy_button = Button(
            label="Купить",
            style=discord.ButtonStyle.secondary
        )
        buy_button.callback = self.confirm_purchase
        self.add_item(buy_button)
        
        back_button = Button(
            label="◀ Назад",
            style=discord.ButtonStyle.secondary
        )
        back_button.callback = self.go_back
        self.add_item(back_button)
    
    async def decrease_quantity(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        if self.quantity > 1:
            self.quantity -= 1
            self.quantity_label.label = str(self.quantity)
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()
    
    async def increase_quantity(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        max_quantity = 1000
        if self.available > 0:
            max_quantity = min(1000, self.available)
        
        if self.quantity < max_quantity:
            self.quantity += 1
            self.quantity_label.label = str(self.quantity)
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()
    
    async def manual_input(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        modal = CivilQuantityModal(
            self.corporation, self.product_type, self.product, self.user_id,
            self.player_country, self.tariff_system, interaction.message
        )
        await interaction.response.send_modal(modal)
    
    async def update_embed(self, interaction):
        total_price = self.product.get('price', 0) * self.quantity
        prod_time = get_civil_production_time(self.product_type, self.quantity)
        
        embed = discord.Embed(
            title=self.product.get('name', 'Неизвестный продукт'),
            description=self.product.get('description', 'Нет описания'),
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Цена за ед.", value=f"${self.product.get('price', 0):,}", inline=True)
        embed.add_field(name="Количество", value=str(self.quantity), inline=True)
        embed.add_field(name="Общая сумма", value=f"${total_price:,}", inline=True)
        
        if prod_time > 0:
            embed.add_field(name="Время производства", value=format_time(prod_time), inline=True)
        
        if self.available > 0:
            embed.add_field(name="📦 Доступно на складе", value=f"{self.available} ед.", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def confirm_purchase(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверка эмбарго
        if is_trade_blocked(self.tariff_system, self.player_country, self.corporation.country, self.product_type):
            await interaction.response.send_message(
                f"❌ Товары из {self.corporation.country} запрещены из-за эмбарго!",
                ephemeral=True
            )
            return
        
        # Проверка наличия
        if self.available > 0 and self.quantity > self.available:
            await interaction.response.send_message(
                f"❌ Недостаточно товара на складе! Доступно: {self.available}",
                ephemeral=True
            )
            return
        
        try:
            await interaction.message.delete()
        except:
            pass
        
        view = CivilPurchaseConfirmation(
            self.corporation, self.product_type, self.product, self.quantity,
            self.user_id, self.player_country, self.tariff_system
        )
        
        total_price = self.product.get('price', 0) * self.quantity
        prod_time = get_civil_production_time(self.product_type, self.quantity)
        
        embed = discord.Embed(
            title="Подтверждение покупки",
            description="Проверьте детали заказа:",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Корпорация", value=self.corporation.name, inline=True)
        embed.add_field(name="Продукт", value=self.product.get('name', 'Неизвестный продукт'), inline=True)
        embed.add_field(name="Количество", value=str(self.quantity), inline=True)
        embed.add_field(name="Стоимость", value=f"${total_price:,}", inline=True)
        
        if prod_time > 0:
            embed.add_field(name="Время производства", value=format_time(prod_time), inline=True)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            await interaction.message.delete()
        except:
            pass
        
        await show_corporation_details(
            interaction, self.user_id, self.player_country,
            self.corporation, self.product_type, self.tariff_system
        )


# ==================== ПОДТВЕРЖДЕНИЕ ПОКУПКИ ====================

class CivilPurchaseConfirmation(View):
    """Подтверждение покупки"""
    def __init__(self, corporation, product_type, product, quantity, user_id, player_country, tariff_system):
        super().__init__(timeout=300)
        self.corporation = corporation
        self.product_type = product_type
        self.product = product
        self.quantity = quantity
        self.user_id = user_id
        self.player_country = player_country
        self.tariff_system = tariff_system
        
        confirm_button = Button(label="✅ Подтвердить", style=discord.ButtonStyle.secondary)
        confirm_button.callback = self.confirm
        self.add_item(confirm_button)
        
        cancel_button = Button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
        cancel_button.callback = self.cancel
        self.add_item(cancel_button)
    
    async def confirm(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        states = load_states()
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(interaction.user.id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("❌ У вас нет государства!", ephemeral=True)
            return
        
        buyer_country = player_data["state"]["statename"]
        seller_country = self.corporation.country
        
        # Проверка эмбарго
        buyer_tariff = TariffSystem(buyer_country)
        seller_tariff = TariffSystem(seller_country)
        
        if buyer_tariff.is_product_embargoed(seller_country, self.product_type):
            await interaction.response.send_message(
                f"❌ Ваша страна ввела эмбарго против {seller_country}!",
                ephemeral=True
            )
            return
        
        if seller_tariff.is_product_embargoed(buyer_country, self.product_type):
            await interaction.response.send_message(
                f"❌ Страна {seller_country} ввела эмбарго против вашей страны!",
                ephemeral=True
            )
            return
        
        # Получаем состояние корпорации
        corp_state = initialize_corporation_state(self.corporation)
        available = corp_state.inventory.get(self.product_type, 0)
        
        # Проверяем наличие (если товар есть на складе)
        if available > 0 and self.quantity > available:
            await interaction.response.send_message(
                f"❌ Недостаточно товара на складе! Доступно: {available}",
                ephemeral=True
            )
            return
        
        # Рассчитываем пошлины
        base_price = self.product.get('price', 0) * self.quantity
        
        import_tariff = buyer_tariff.calculate_import_tariff(
            self.product_type, seller_country, base_price
        )
        
        export_tariff = seller_tariff.calculate_export_tariff(
            self.product_type, base_price
        )
        
        buyer_pays = base_price + import_tariff
        seller_receives = base_price - export_tariff
        
        # Проверяем бюджет покупателя
        if player_data["economy"]["budget"] < buyer_pays:
            await interaction.response.send_message(
                f"❌ Недостаточно средств! Нужно: ${buyer_pays:,} (включая пошлину ${import_tariff:,})",
                ephemeral=True
            )
            return
        
        # Списываем деньги с покупателя
        player_data["economy"]["budget"] -= buyer_pays
        
        # Импортная пошлина идёт в бюджет покупателя
        if "tariff_revenue" not in player_data:
            player_data["tariff_revenue"] = 0
        player_data["tariff_revenue"] += import_tariff
        
        # Обновляем бюджет корпорации
        update_corporation_budget(self.corporation.id, seller_receives, add=True)
        
        # Списываем товар со склада (если был)
        if available > 0:
            update_corporation_inventory(self.corporation.id, self.product_type, self.quantity, add=False)
        
        save_states(states)
        
        # Создаем заказ в очереди производства (если товара не было в наличии)
        if available == 0:
            queue = load_civil_production_queue()
            prod_time = get_civil_production_time(self.product_type, self.quantity)
            completion_time = datetime.now() + timedelta(seconds=prod_time)
            
            order = {
                "id": len(queue["active_orders"]) + 1,
                "user_id": str(interaction.user.id),
                "user_name": interaction.user.name,
                "corporation": self.corporation.name,
                "corporation_id": self.corporation.id,
                "corporation_country": seller_country,
                "product_name": self.product.get('name', 'Неизвестный продукт'),
                "product_type": self.product_type,
                "quantity": self.quantity,
                "base_price": base_price,
                "import_tariff": import_tariff,
                "export_tariff": export_tariff,
                "buyer_pays": buyer_pays,
                "seller_receives": seller_receives,
                "start_time": str(datetime.now()),
                "completion_time": str(completion_time),
                "status": "in_production",
                "notified": False
            }
            
            queue["active_orders"].append(order)
            save_civil_production_queue(queue)
            
            status_text = "запущен в производство"
            time_text = f"Готовность через: {format_time(prod_time)}"
        else:
            # Товар был в наличии - доставляем мгновенно
            # Добавляем в гражданские запасы игрока
            if "civil_goods" not in player_data:
                player_data["civil_goods"] = {}
            
            current = player_data["civil_goods"].get(self.product_type, 0)
            player_data["civil_goods"][self.product_type] = current + self.quantity
            
            save_states(states)
            
            status_text = "мгновенно доставлен со склада"
            time_text = "✅ Товар получен!"
        
        try:
            await interaction.message.delete()
        except:
            pass
        
        embed = discord.Embed(
            title="✅ Заказ оформлен!",
            description=f"Продукция {status_text}",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Корпорация", value=self.corporation.name, inline=True)
        embed.add_field(name="Продукт", value=self.product.get('name', 'Неизвестный продукт'), inline=True)
        embed.add_field(name="Количество", value=str(self.quantity), inline=True)
        embed.add_field(name="Базовая стоимость", value=f"${base_price:,}", inline=True)
        
        if import_tariff > 0:
            embed.add_field(name="🛃 Импортная пошлина", value=f"${import_tariff:,}", inline=True)
        
        if export_tariff > 0:
            embed.add_field(name="📤 Экспортная пошлина", value=f"${export_tariff:,}", inline=True)
        
        embed.add_field(name="💵 Итоговая стоимость", value=f"${buyer_pays:,}", inline=True)
        embed.add_field(name="📊 Статус", value=time_text, inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            await interaction.message.delete()
        except:
            pass
        
        embed = discord.Embed(
            title="❌ Покупка отменена",
            color=DARK_THEME_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==================== ОСНОВНЫЕ ФУНКЦИИ НАВИГАЦИИ ====================

async def show_civil_corporations_menu(ctx, user_id):
    """Показать меню выбора гражданских корпораций по странам"""
    
    states = load_states()
    player_country = None
    player_data = None
    
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            player_country = data["state"]["statename"]
            break
    
    if not player_country:
        error_msg = "❌ У вас нет государства!"
        if hasattr(ctx, 'response'):
            await ctx.response.send_message(error_msg, ephemeral=True)
        else:
            await ctx.send(error_msg)
        return
    
    tariff_system = TariffSystem(player_country)
    
    embed = discord.Embed(
        title="🏭 Гражданская продукция и услуги",
        description="Выберите страну для просмотра корпораций:",
        color=DARK_THEME_COLOR
    )
    
    all_corps = get_all_civil_corporations()
    total_corps = len(all_corps)
    
    available_corps = 0
    for corp in all_corps:
        if hasattr(corp, 'country'):
            if not is_trade_blocked(tariff_system, player_country, corp.country, "all"):
                available_corps += 1
    
    countries = list(ALL_CIVIL_CORPORATIONS.keys())
    country_stats = ""
    for country in countries:
        corp_count = len(ALL_CIVIL_CORPORATIONS[country])
        country_stats += f"• {country}: {corp_count} корпораций\n"
    
    embed.add_field(name="📊 Доступно корпораций", value=f"{available_corps}/{total_corps}", inline=True)
    
    # Информация об эмбарго
    embargoed = []
    for country, categories in tariff_system.tariffs.get("embargoes", {}).items():
        if "all" in categories:
            embargoed.append(country)
    if embargoed:
        embed.add_field(
            name="🚫 Эмбарго (ваши против других)",
            value=", ".join(embargoed[:5]) + (" и др." if len(embargoed) > 5 else ""),
            inline=False
        )
    
    embargoed_against = []
    for country in ["США", "Россия", "Китай", "Германия", "Израиль", "Украина", "Иран"]:
        if country != player_country:
            other_tariff = TariffSystem(country)
            if other_tariff.is_product_embargoed(player_country, "all"):
                embargoed_against.append(country)
    
    if embargoed_against:
        embed.add_field(
            name="🚫 Эмбарго (других против вас)",
            value=", ".join(embargoed_against[:5]) + (" и др." if len(embargoed_against) > 5 else ""),
            inline=False
        )
    
    embed.add_field(name="🌍 Страны", value=country_stats, inline=False)
    
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, ephemeral=True)
        message = await ctx.original_response()
    else:
        message = await ctx.send(embed=embed, ephemeral=True)
    
    select = CountrySelect(user_id, player_country, message, tariff_system)
    view = View(timeout=300)
    view.add_item(select)
    
    await message.edit(view=view)


async def show_specializations_for_country(interaction, user_id, player_country, country, tariff_system):
    """Показать категории специализаций для выбранной страны"""
    
    # Группируем специализации по категориям
    categories_with_counts = {}
    specializations = get_unique_specializations_for_country(country)
    
    for spec in specializations:
        category = get_specialization_category(spec)
        if category not in categories_with_counts:
            categories_with_counts[category] = 0
        
        # Считаем доступные корпорации с этой специализацией
        corps = get_corporations_by_specialization(country, spec)
        for corp in corps:
            if not is_trade_blocked(tariff_system, player_country, corp.country, "all"):
                categories_with_counts[category] += 1
                break
    
    # Фильтруем пустые категории
    categories_with_counts = {k: v for k, v in categories_with_counts.items() if v > 0}
    
    embed = discord.Embed(
        title=f"🏭 Категории продукции: {country}",
        description="Выберите категорию товаров или услуг:",
        color=DARK_THEME_COLOR
    )
    
    # Показываем статистику по категориям
    cat_text = ""
    for cat, count in list(categories_with_counts.items())[:10]:
        cat_text += f"• {cat}: {count} корпораций\n"
    embed.add_field(name="📊 Доступные категории", value=cat_text, inline=False)
    
    select = SpecializationCategorySelect(
        user_id, player_country, country, tariff_system, categories_with_counts
    )
    view = View(timeout=300)
    view.add_item(select)
    
    # Кнопка назад к странам
    back_button = Button(label="◀ Назад к странам", style=discord.ButtonStyle.secondary)
    back_button.callback = lambda i: show_civil_corporations_menu(i, user_id)
    view.add_item(back_button)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def show_specializations_in_category(interaction, user_id, player_country, country, category, tariff_system):
    """Показать конкретные специализации в выбранной категории"""
    
    # Получаем все специализации в этой категории
    specializations_in_category = []
    all_specs = get_unique_specializations_for_country(country)
    
    for spec in all_specs:
        if get_specialization_category(spec) == category:
            # Проверяем, есть ли доступные корпорации
            corps = get_corporations_by_specialization(country, spec)
            for corp in corps:
                if not is_trade_blocked(tariff_system, player_country, corp.country, "all"):
                    specializations_in_category.append(spec)
                    break
    
    embed = discord.Embed(
        title=f"🏭 {category} в {country}",
        description="Выберите конкретную специализацию:",
        color=DARK_THEME_COLOR
    )
    
    select = SpecializationSelect(
        user_id, player_country, country, category,
        specializations_in_category, tariff_system
    )
    view = View(timeout=300)
    view.add_item(select)
    
    # Кнопка назад к категориям
    back_button = Button(label="◀ Назад к категориям", style=discord.ButtonStyle.secondary)
    back_button.callback = lambda i: show_specializations_for_country(
        i, user_id, player_country, country, tariff_system
    )
    view.add_item(back_button)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def show_corporations_by_specialization(interaction, user_id, player_country, country, specialization, tariff_system):
    """Показать корпорации с выбранной специализацией"""
    
    corps = get_corporations_by_specialization(country, specialization)
    
    # Фильтруем доступные
    available_corps = []
    for corp in corps:
        if not is_trade_blocked(tariff_system, player_country, corp.country, "all"):
            available_corps.append(corp)
    
    spec_name = SPECIALIZATION_NAMES.get(specialization, specialization)
    
    embed = discord.Embed(
        title=f"🏭 {spec_name} в {country}",
        description=f"Найдено корпораций: {len(available_corps)}",
        color=DARK_THEME_COLOR
    )
    
    select = CorporationSelect(
        user_id, player_country, country, specialization,
        available_corps, tariff_system
    )
    view = View(timeout=300)
    view.add_item(select)
    
    # Кнопка назад к специализациям в категории
    category = get_specialization_category(specialization)
    back_button = Button(label="◀ Назад к специализациям", style=discord.ButtonStyle.secondary)
    back_button.callback = lambda i: show_specializations_in_category(
        i, user_id, player_country, country, category, tariff_system
    )
    view.add_item(back_button)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ==================== ОСТАЛЬНЫЕ ФУНКЦИИ (без изменений) ====================

async def show_civil_orders(ctx):
    """Показать текущие заказы игрока"""
    queue = load_civil_production_queue()
    user_orders = [o for o in queue["active_orders"] if o["user_id"] == str(ctx.author.id)]
    
    if not user_orders:
        await ctx.send("📦 У вас нет активных заказов гражданской продукции.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📋 Мои заказы гражданской продукции",
        color=DARK_THEME_COLOR
    )
    
    now = datetime.now()
    for order in user_orders[-5:]:
        completion = datetime.fromisoformat(order["completion_time"])
        remaining = (completion - now).total_seconds()
        
        if remaining > 0:
            progress = 100 - (remaining / (completion - datetime.fromisoformat(order["start_time"])).total_seconds() * 100)
            progress_bar = "█" * int(progress/10) + "░" * (10 - int(progress/10))
            status = f"⏳ {format_time(remaining)} осталось\n{progress_bar}"
        else:
            status = "✅ ГОТОВ К ПОЛУЧЕНИЮ!"
        
        tariff_info = ""
        if order.get('import_tariff', 0) > 0:
            tariff_info += f"\n🛃 Пошлина: ${order['import_tariff']:,}"
        if order.get('export_tariff', 0) > 0:
            tariff_info += f"\n📤 Эксп. пошлина: ${order['export_tariff']:,}"
        
        embed.add_field(
            name=f"Заказ #{order['id']} | {order['product_name']} x{order['quantity']}",
            value=f"Корпорация: {order['corporation']}{tariff_info}\n{status}",
            inline=False
        )
    
    await ctx.send(embed=embed, ephemeral=True)


async def collect_civil_orders(ctx):
    """Забрать готовые заказы (FPV-дроны идут сразу в армию)"""
    queue = load_civil_production_queue()
    states = load_states()
    
    now = datetime.now()
    collected = []
    
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(ctx.author.id):
            player_data = data
            break
    
    if not player_data:
        await ctx.send("❌ У вас нет государства!", ephemeral=True)
        return
    
    if "civil_goods" not in player_data:
        player_data["civil_goods"] = {}
    
    if "army" not in player_data:
        player_data["army"] = {}
    if "equipment" not in player_data["army"]:
        player_data["army"]["equipment"] = {}
    
    for order in queue["active_orders"][:]:
        if order["user_id"] == str(ctx.author.id):
            completion = datetime.fromisoformat(order["completion_time"])
            
            if completion <= now:
                product_type = order["product_type"]
                
                if product_type == "fpv_drones":
                    current = player_data["army"]["equipment"].get("fpv_drones", 0)
                    player_data["army"]["equipment"]["fpv_drones"] = current + order["quantity"]
                    destination = "армию (FPV-дроны)"
                else:
                    current = player_data["civil_goods"].get(product_type, 0)
                    player_data["civil_goods"][product_type] = current + order["quantity"]
                    destination = "гражданские запасы"
                
                order["status"] = "completed"
                order["collected_at"] = str(now)
                order["destination"] = destination
                queue["completed_orders"].append(order)
                queue["active_orders"].remove(order)
                collected.append(order)
    
    if collected:
        save_states(states)
        save_civil_production_queue(queue)
        
        embed = discord.Embed(
            title="✅ Продукция получена!",
            color=DARK_THEME_COLOR
        )
        
        for order in collected:
            product_type_name = CIVIL_PRODUCT_NAMES.get(order['product_type'], order['product_type'])
            
            tariff_info = ""
            if order.get('import_tariff', 0) > 0:
                tariff_info += f"\n🛃 Вы заплатили пошлину: ${order['import_tariff']:,}"
            if order.get('export_tariff', 0) > 0:
                tariff_info += f"\n📤 Экспортная пошлина удержана: ${order['export_tariff']:,}"
            
            embed.add_field(
                name=f"{order['product_name']} x{order['quantity']}",
                value=f"Корпорация: {order['corporation']}\n"
                      f"Тип: {product_type_name}{tariff_info}\n"
                      f"✅ Продукция добавлена в **{order.get('destination', 'гражданские запасы')}**",
                inline=False
            )
        
        await ctx.send(embed=embed, ephemeral=True)
    else:
        await ctx.send("❌ У вас нет готовых заказов.", ephemeral=True)


async def civil_production_check_loop(bot_instance):
    """Фоновая задача для проверки производства"""
    await bot_instance.wait_until_ready()
    while not bot_instance.is_closed():
        try:
            queue = load_civil_production_queue()
            now = datetime.now()
            
            for order in queue["active_orders"]:
                completion = datetime.fromisoformat(order["completion_time"])
                if completion <= now and not order.get("notified", False):
                    try:
                        user = await bot_instance.fetch_user(int(order["user_id"]))
                        if user:
                            embed = discord.Embed(
                                title="✅ Заказ готов!",
                                description=f"Ваш заказ **{order['product_name']} x{order['quantity']}** готов к получению!",
                                color=DARK_THEME_COLOR
                            )
                            embed.add_field(name="Корпорация", value=order["corporation"])
                            embed.add_field(name="Команда", value="`!получить_гражданские` для получения")
                            
                            if order.get("product_type") == "fpv_drones":
                                embed.add_field(name="Важно", value="FPV-дроны будут добавлены直接在 в армию!")
                            
                            if order.get('import_tariff', 0) > 0:
                                embed.add_field(name="🛃 Импортная пошлина", value=f"${order['import_tariff']:,}", inline=True)
                            if order.get('export_tariff', 0) > 0:
                                embed.add_field(name="📤 Экспортная пошлина", value=f"${order['export_tariff']:,}", inline=True)
                            
                            await user.send(embed=embed)
                    except:
                        pass
                    order["notified"] = True
                    save_civil_production_queue(queue)
            
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Ошибка в civil_production_check_loop: {e}")
            await asyncio.sleep(3600)


async def show_civil_goods(ctx):
    """Показать запасы гражданской продукции"""
    states = load_states()
    
    player_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(ctx.author.id):
            player_data = data
            break
    
    if not player_data:
        await ctx.send("❌ У вас нет государства!", ephemeral=True)
        return
    
    civil_goods = player_data.get("civil_goods", {})
    state_name = player_data["state"]["statename"]
    
    if not civil_goods:
        await ctx.send("📭 У вас нет запасов гражданской продукции.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"📦 Гражданская продукция: {state_name}",
        color=DARK_THEME_COLOR
    )
    
    categories = {
        "Автотранспорт": ["cars", "trucks", "buses", "auto_parts"],
        "Сельхозтехника": ["agricultural_machinery"],
        "Строительная техника": ["construction_machinery"],
        "Промышленное оборудование": ["industrial_equipment", "machine_tools", "industrial_robots"],
        "Энергетика": ["energy_equipment"],
        "Электроника": ["electrical_equipment", "telecom_equipment", "tech_equipment", "aerospace_equipment", "electronics_components", "consumer_electronics", "computers", "smartphones", "tablets"],
        "Потребительские товары": ["clothing", "footwear", "medical_supplies", "sanitary_products", "cosmetics"],
        "Медицина": ["medical_equipment", "pharmaceuticals"],
        "Продукты питания": ["food_products", "beverages"],
        "Химия": ["chemicals", "fertilizers"],
        "Товары для дома": ["furniture", "household_goods"],
        "Дроны": ["drones", "fpv_drones"]
    }
    
    for category_name, type_list in categories.items():
        category_items = []
        for product_type in type_list:
            if product_type in civil_goods and civil_goods[product_type] > 0:
                product_name = CIVIL_PRODUCT_NAMES.get(product_type, product_type)
                category_items.append(f"{product_name}: {format_number(civil_goods[product_type])}")
        
        if category_items:
            embed.add_field(
                name=category_name,
                value="\n".join(category_items[:5]),
                inline=True
            )
    
    await ctx.send(embed=embed, ephemeral=True)


# ==================== ЭКСПОРТ ФУНКЦИЙ ====================

__all__ = [
    'show_civil_corporations_menu',
    'show_civil_orders',
    'collect_civil_orders',
    'civil_production_check_loop',
    'show_civil_goods',
    'CIVIL_PRODUCTION_SPEED',
    'CIVIL_PRODUCT_NAMES'
]

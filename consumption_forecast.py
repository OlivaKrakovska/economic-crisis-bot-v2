# consumption_forecast.py - Модуль для прогноза потребления товаров и услуг
# ИСПРАВЛЕННАЯ ВЕРСИЯ - правильные импорты, без циклических зависимостей

import discord
from discord.ui import Button, View, Select, Modal
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import math

from utils import format_number, format_billion, DARK_THEME_COLOR, load_states
from civil_corporations_db import (
    get_civil_corporations_by_country, get_all_civil_corporations,
    get_civil_corporation, CIVIL_PRODUCT_NAMES, load_corporations_state
)
from population import BASE_POPULATION_NEEDS, INCOME_ELASTICITY
from trade_tariffs import TariffSystem

# ==================== КАТЕГОРИИ ДЛЯ ОТОБРАЖЕНИЯ ====================

CONSUMPTION_CATEGORIES = {
    "🍔 Продукты питания": {
        "products": ["food_products", "beverages", "restaurants", "fast_food", "catering"],
        "icon": "🍔",
        "description": "Еда, напитки, рестораны"
    },
    "👕 Одежда и обувь": {
        "products": ["clothing", "footwear"],
        "icon": "👕",
        "description": "Одежда, обувь, аксессуары"
    },
    "🏠 Товары для дома": {
        "products": ["furniture", "household_goods", "cosmetics", "perfumes"],
        "icon": "🏠",
        "description": "Мебель, бытовая химия, косметика"
    },
    "📱 Электроника": {
        "products": ["consumer_electronics", "computers", "smartphones", "tablets", "gaming"],
        "icon": "📱",
        "description": "Смартфоны, компьютеры, ТВ, игры"
    },
    "🚗 Автомобили": {
        "products": ["cars", "trucks", "buses", "auto_parts"],
        "icon": "🚗",
        "description": "Легковые и грузовые автомобили"
    },
    "📡 Телекоммуникации": {
        "products": ["telecom_services", "mobile_services", "internet_services"],
        "icon": "📡",
        "description": "Мобильная связь, интернет, телефония"
    },
    "💻 IT и софт": {
        "products": ["software", "it_services", "cloud_services", "cybersecurity"],
        "icon": "💻",
        "description": "Программное обеспечение, IT-услуги"
    },
    "🏦 Финансы": {
        "products": ["banking", "investments", "fintech", "insurance"],
        "icon": "🏦",
        "description": "Банковские услуги, страхование"
    },
    "🏭 Промышленность": {
        "products": ["industrial_equipment", "machine_tools", "industrial_robots", "construction_machinery"],
        "icon": "🏭",
        "description": "Промышленное оборудование, станки"
    },
    "⚡ Энергетика": {
        "products": ["energy_equipment", "electricity", "gas_supply"],
        "icon": "⚡",
        "description": "Электроэнергия, газ, оборудование"
    },
    "✈️ Авиация": {
        "products": ["aerospace_equipment", "airlines", "drones"],
        "icon": "✈️",
        "description": "Авиаперевозки, оборудование, дроны"
    },
    "🏥 Медицина": {
        "products": ["pharmaceuticals", "medical_equipment", "medical_supplies", "healthcare_services", "hospital_services"],
        "icon": "🏥",
        "description": "Лекарства, медоборудование, услуги"
    },
    "📚 Образование": {
        "products": ["education", "online_courses"],
        "icon": "📚",
        "description": "Образовательные услуги"
    },
    "🎬 Развлечения": {
        "products": ["entertainment", "media", "streaming"],
        "icon": "🎬",
        "description": "Кино, музыка, стриминг"
    },
    "🚚 Логистика": {
        "products": ["logistics", "freight", "passenger_transport"],
        "icon": "🚚",
        "description": "Перевозки, доставка"
    }
}

# Обратный маппинг: продукт -> категория
PRODUCT_TO_CATEGORY = {}
for category_name, category_data in CONSUMPTION_CATEGORIES.items():
    for product in category_data["products"]:
        PRODUCT_TO_CATEGORY[product] = category_name


# ==================== ФУНКЦИИ ДЛЯ СБОРА ДАННЫХ ====================

def get_consumption_forecast(player_data, days=365):
    """
    Получает прогноз потребления на указанный период
    Возвращает структуру с данными по категориям и корпорациям
    """
    country_name = player_data["state"]["statename"]
    population = player_data["state"]["population"]
    
    # Получаем данные о населении
    population_data = player_data.get("population_data", {})
    
    # ✨ ИСПРАВЛЕНО: Если есть детальные данные о покупках, используем их
    detailed_purchases = population_data.get("detailed_purchases", [])
    
    # Если нет детальных данных, пробуем использовать старые consumption данные
    consumption_data = population_data.get("consumption", {})
    needs_met = population_data.get("needs_met", {})
    
    # Рассчитываем прогноз
    forecast = {
        "country": country_name,
        "population": population,
        "total_spent": population_data.get("total_spent", 0) * (days / 365),
        "categories": {},
        "corporations": {},
        "by_origin": {
            "local": 0,
            "import": 0
        }
    }
    
    # ✨ ИСПРАВЛЕНО: Собираем данные из детальных покупок
    if detailed_purchases:
        print(f"📊 Найдено {len(detailed_purchases)} детальных записей о покупках для {country_name}")
        
        for purchase in detailed_purchases:  # Исправлено: было detailed_purchakes
            product_type = purchase.get("product")
            corp_id = purchase.get("corporation_id")
            corp_name = purchase.get("corporation_name")
            quantity = purchase.get("quantity", 0)
            spent = purchase.get("total", 0)
            
            # Определяем категорию
            category = PRODUCT_TO_CATEGORY.get(product_type, "Другое")
            
            # Обновляем данные по категориям
            if category not in forecast["categories"]:
                forecast["categories"][category] = {
                    "total_units": 0,
                    "total_spent": 0,
                    "products": {}
                }
            
            forecast["categories"][category]["total_units"] += quantity
            forecast["categories"][category]["total_spent"] += spent
            
            if product_type not in forecast["categories"][category]["products"]:
                forecast["categories"][category]["products"][product_type] = {
                    "units": 0,
                    "spent": 0,
                    "name": CIVIL_PRODUCT_NAMES.get(product_type, product_type)
                }
            
            forecast["categories"][category]["products"][product_type]["units"] += quantity
            forecast["categories"][category]["products"][product_type]["spent"] += spent
            
            # Обновляем данные по корпорациям
            if corp_id not in forecast["corporations"]:
                # Находим корпорацию в базе
                corp = None
                for c in get_all_civil_corporations():
                    if c.id == corp_id:
                        corp = c
                        break
                
                if not corp:
                    # Если не нашли, создаем заглушку
                    forecast["corporations"][corp_id] = {
                        "name": corp_name or "Неизвестная корпорация",
                        "country": "Неизвестно",
                        "is_local": False,
                        "total_sales": 0,
                        "total_revenue": 0,
                        "products": {}
                    }
                else:
                    is_local = corp.country == country_name
                    forecast["corporations"][corp_id] = {
                        "name": corp.name,
                        "country": corp.country,
                        "is_local": is_local,
                        "total_sales": 0,
                        "total_revenue": 0,
                        "products": {}
                    }
                    if is_local:
                        forecast["by_origin"]["local"] += 1
                    else:
                        forecast["by_origin"]["import"] += 1
            
            # Обновляем статистику корпорации
            corp_data = forecast["corporations"][corp_id]
            corp_data["total_sales"] += quantity
            corp_data["total_revenue"] += spent
            
            if product_type not in corp_data["products"]:
                corp_data["products"][product_type] = {
                    "quantity": 0,
                    "revenue": 0
                }
            corp_data["products"][product_type]["quantity"] += quantity
            corp_data["products"][product_type]["revenue"] += spent
    
    # ✨ ИСПРАВЛЕНО: Если нет детальных данных, используем consumption данные
    elif consumption_data:
        print(f"📊 Использую общие данные о потреблении для {country_name} (нет детальных)")
        
        for product_type, amount in consumption_data.items():
            category = PRODUCT_TO_CATEGORY.get(product_type, "Другое")
            
            if category not in forecast["categories"]:
                forecast["categories"][category] = {
                    "total_units": 0,
                    "total_spent": 0,
                    "products": {}
                }
            
            # Цена продукта (берем среднюю из корпораций)
            price = get_average_product_price(product_type)
            spent = amount * price
            
            forecast["categories"][category]["total_units"] += amount
            forecast["categories"][category]["total_spent"] += spent
            forecast["categories"][category]["products"][product_type] = {
                "units": amount,
                "spent": spent,
                "name": CIVIL_PRODUCT_NAMES.get(product_type, product_type)
            }
    
    # Если нет данных о реальном потреблении, рассчитываем прогноз
    else:
        print(f"📊 Нет данных о потреблении для {country_name}, рассчитываю прогноз")
        
        # Используем базовые потребности
        for product_type, base_amount in BASE_POPULATION_NEEDS.items():
            category = PRODUCT_TO_CATEGORY.get(product_type, "Другое")
            
            if category not in forecast["categories"]:
                forecast["categories"][category] = {
                    "total_units": 0,
                    "total_spent": 0,
                    "products": {}
                }
            
            # Корректируем на доход
            income_factor = calculate_income_factor(player_data)
            elasticity = INCOME_ELASTICITY.get(product_type, 0.5)
            amount = base_amount * population * (income_factor ** elasticity) * (days / 365)
            
            price = get_average_product_price(product_type)
            spent = amount * price
            
            forecast["categories"][category]["total_units"] += amount
            forecast["categories"][category]["total_spent"] += spent
            forecast["categories"][category]["products"][product_type] = {
                "units": amount,
                "spent": spent,
                "name": CIVIL_PRODUCT_NAMES.get(product_type, product_type)
            }
    
    return forecast


def get_average_product_price(product_type):
    """Получает среднюю цену продукта по всем корпорациям"""
    prices = []
    for corp in get_all_civil_corporations():
        if product_type in corp.products:
            prices.append(corp.products[product_type]['price'])
    
    if prices:
        return sum(prices) / len(prices)
    return 100  # значение по умолчанию


def calculate_income_factor(player_data):
    """Рассчитывает коэффициент дохода для прогноза"""
    population_data = player_data.get("population_data", {})
    avg_salary = population_data.get("average_salary", 50000)
    base_income = 30000  # базовый доход для расчета
    
    return max(0.5, min(2.0, avg_salary / base_income))


# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class CategorySelect(Select):
    """Выбор категории для детального просмотра"""
    
    def __init__(self, user_id, forecast, categories_with_data):
        self.user_id = user_id
        self.forecast = forecast
        
        options = []
        for category_name, category_data in categories_with_data.items():
            units = int(category_data["total_units"])
            spent = category_data["total_spent"]
            
            options.append(
                discord.SelectOption(
                    label=category_name,
                    description=f"{format_number(units)} ед. | {format_billion(spent)}",
                    value=category_name,
                    emoji=CONSUMPTION_CATEGORIES.get(category_name, {}).get("icon", "📦")
                )
            )
        
        super().__init__(
            placeholder="Выберите категорию для детализации...",
            min_values=1,
            max_values=1,
            options=options[:25]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        category = self.values[0]
        category_data = self.forecast["categories"].get(category, {})
        
        embed = discord.Embed(
            title=f"{CONSUMPTION_CATEGORIES.get(category, {}).get('icon', '📦')} {category}",
            description=CONSUMPTION_CATEGORIES.get(category, {}).get("description", ""),
            color=DARK_THEME_COLOR
        )
        
        # Общая статистика по категории
        embed.add_field(
            name="📊 Общие показатели",
            value=f"📦 Всего единиц: {format_number(int(category_data.get('total_units', 0)))}\n"
                  f"💰 Всего потрачено: {format_billion(category_data.get('total_spent', 0))}",
            inline=False
        )
        
        # Детализация по продуктам
        products = category_data.get("products", {})
        if products:
            products_text = ""
            for product_type, product_data in list(products.items())[:5]:
                name = product_data.get("name", product_type)
                units = int(product_data.get("units", 0))
                spent = product_data.get("spent", 0)
                products_text += f"• {name}: {format_number(units)} ед. ({format_billion(spent)})\n"
            
            embed.add_field(name="📦 По продуктам", value=products_text, inline=False)
        
        # Информация о корпорациях в этой категории
        corps_in_category = []
        for corp_id, corp_data in self.forecast["corporations"].items():
            for product in corp_data["products"]:
                category_of_product = PRODUCT_TO_CATEGORY.get(product, "Другое")
                if category_of_product == category:
                    corps_in_category.append((corp_data, product))
                    break
        
        if corps_in_category:
            corps_text = ""
            for corp_data, product in corps_in_category[:5]:
                product_data = corp_data["products"].get(product, {})
                flag = "🇺🇦" if corp_data["is_local"] else "🌍"
                corps_text += f"{flag} **{corp_data['name']}** ({corp_data['country']}): "
                corps_text += f"{format_number(int(product_data.get('quantity', 0)))} ед., "
                corps_text += f"выручка {format_billion(product_data.get('revenue', 0))}\n"
            
            embed.add_field(name="🏢 Корпорации", value=corps_text, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class OriginSelect(Select):
    """Выбор по происхождению (местные/импортные)"""
    
    def __init__(self, user_id, forecast):
        self.user_id = user_id
        self.forecast = forecast
        
        options = [
            discord.SelectOption(
                label="Все корпорации",
                description=f"Всего: {len(forecast['corporations'])}",
                value="all",
                emoji="🌐"
            ),
            discord.SelectOption(
                label="Местные",
                description=f"{forecast['by_origin']['local']} корпораций",
                value="local",
                emoji="🇺🇦"
            ),
            discord.SelectOption(
                label="Импортные",
                description=f"{forecast['by_origin']['import']} корпораций",
                value="import",
                emoji="🌍"
            )
        ]
        
        super().__init__(
            placeholder="Фильтр по происхождению...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        filter_type = self.values[0]
        
        embed = discord.Embed(
            title=f"🏢 Корпорации: {self.forecast['country']}",
            description=f"Фильтр: {'Все' if filter_type == 'all' else 'Местные' if filter_type == 'local' else 'Импортные'}",
            color=DARK_THEME_COLOR
        )
        
        corps_list = []
        for corp_id, corp_data in self.forecast["corporations"].items():
            if filter_type == "all" or \
               (filter_type == "local" and corp_data["is_local"]) or \
               (filter_type == "import" and not corp_data["is_local"]):
                corps_list.append(corp_data)
        
        # Сортируем по выручке
        corps_list.sort(key=lambda x: x["total_revenue"], reverse=True)
        
        for corp_data in corps_list[:10]:
            flag = "🇺🇦" if corp_data["is_local"] else "🌍"
            profit = corp_data["total_revenue"] * 0.15  # Примерно 15% прибыли
            
            embed.add_field(
                name=f"{flag} {corp_data['name']}",
                value=f"📦 Продаж: {format_number(int(corp_data['total_sales']))} ед.\n"
                      f"💰 Выручка: {format_billion(corp_data['total_revenue'])}\n"
                      f"📈 Прибыль: {format_billion(profit)}\n"
                      f"🌍 Страна: {corp_data['country']}",
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=self.parent_view)


class ConsumptionForecastView(View):
    """Главное меню прогноза потребления"""
    
    def __init__(self, user_id, forecast):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.forecast = forecast
        
        # Кнопки для навигации
        overview_button = Button(label="📊 Обзор", style=discord.ButtonStyle.secondary)
        overview_button.callback = self.show_overview
        self.add_item(overview_button)
        
        categories_button = Button(label="📦 По категориям", style=discord.ButtonStyle.secondary)
        categories_button.callback = self.show_categories
        self.add_item(categories_button)
        
        corps_button = Button(label="🏢 По корпорациям", style=discord.ButtonStyle.secondary)
        corps_button.callback = self.show_corporations
        self.add_item(corps_button)
    
    async def show_overview(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"📊 Прогноз потребления: {self.forecast['country']}",
            description=f"Население: {format_number(self.forecast['population'])} чел.\n"
                       f"Прогноз на 1 год",
            color=DARK_THEME_COLOR
        )
        
        # Общая статистика
        total_categories = len([c for c in self.forecast["categories"].values() if c["total_units"] > 0])
        total_spent = sum(c["total_spent"] for c in self.forecast["categories"].values())
        
        embed.add_field(
            name="📈 Общие показатели",
            value=f"📦 Всего товаров: {format_number(int(sum(c['total_units'] for c in self.forecast['categories'].values())))}\n"
                  f"💰 Всего потрачено: {format_billion(total_spent)}\n"
                  f"📊 Активных категорий: {total_categories}\n"
                  f"🏢 Активных корпораций: {len(self.forecast['corporations'])}",
            inline=False
        )
        
        # Топ-5 категорий по тратам
        top_categories = sorted(
            [(name, data) for name, data in self.forecast["categories"].items() if data["total_units"] > 0],
            key=lambda x: x[1]["total_spent"],
            reverse=True
        )[:5]
        
        categories_text = ""
        for cat_name, cat_data in top_categories:
            icon = CONSUMPTION_CATEGORIES.get(cat_name, {}).get("icon", "📦")
            categories_text += f"{icon} **{cat_name}**: {format_billion(cat_data['total_spent'])}\n"
        
        embed.add_field(name="🔥 Топ-5 категорий", value=categories_text, inline=False)
        
        # Топ-5 корпораций по выручке
        if self.forecast["corporations"]:
            top_corps = sorted(
                [(name, data) for name, data in self.forecast["corporations"].items()],
                key=lambda x: x[1]["total_revenue"],
                reverse=True
            )[:5]
            
            corps_text = ""
            for corp_id, corp_data in top_corps:
                flag = "🇺🇦" if corp_data["is_local"] else "🌍"
                corps_text += f"{flag} **{corp_data['name']}**: {format_billion(corp_data['total_revenue'])}\n"
            
            embed.add_field(name="🔥 Топ-5 корпораций", value=corps_text, inline=False)
        
        # Соотношение местных и импортных
        local_revenue = sum(c["total_revenue"] for c in self.forecast["corporations"].values() if c["is_local"])
        import_revenue = sum(c["total_revenue"] for c in self.forecast["corporations"].values() if not c["is_local"])
        total_revenue = local_revenue + import_revenue
        
        if total_revenue > 0:
            local_percent = (local_revenue / total_revenue) * 100
            import_percent = (import_revenue / total_revenue) * 100
            
            embed.add_field(
                name="🌍 Происхождение товаров",
                value=f"🇺🇦 Местные: {local_percent:.1f}% ({format_billion(local_revenue)})\n"
                      f"🌍 Импортные: {import_percent:.1f}% ({format_billion(import_revenue)})",
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def show_categories(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Собираем категории с данными
        categories_with_data = {
            name: data for name, data in self.forecast["categories"].items()
            if data["total_units"] > 0
        }
        
        embed = discord.Embed(
            title=f"📦 Категории товаров: {self.forecast['country']}",
            description="Выберите категорию для детального просмотра",
            color=DARK_THEME_COLOR
        )
        
        # Краткая статистика по категориям
        stats_text = ""
        for cat_name, cat_data in list(categories_with_data.items())[:8]:
            icon = CONSUMPTION_CATEGORIES.get(cat_name, {}).get("icon", "📦")
            stats_text += f"{icon} {cat_name}: {format_billion(cat_data['total_spent'])}\n"
        
        embed.add_field(name="📊 Быстрый обзор", value=stats_text, inline=False)
        
        # Создаем Select для выбора категории
        select = CategorySelect(self.user_id, self.forecast, categories_with_data)
        select.parent_view = self
        self.clear_items()
        self.add_item(select)
        
        # Добавляем кнопку "Назад"
        back_button = Button(label="◀ Назад к обзору", style=discord.ButtonStyle.secondary)
        back_button.callback = self.show_overview
        self.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def show_corporations(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🏢 Корпорации: {self.forecast['country']}",
            description="Выберите фильтр для просмотра",
            color=DARK_THEME_COLOR
        )
        
        # Статистика по корпорациям
        local_count = self.forecast["by_origin"]["local"]
        import_count = self.forecast["by_origin"]["import"]
        
        embed.add_field(
            name="📊 Статистика",
            value=f"🏢 Всего корпораций: {len(self.forecast['corporations'])}\n"
                  f"🇺🇦 Местных: {local_count}\n"
                  f"🌍 Импортных: {import_count}",
            inline=False
        )
        
        # Создаем Select для выбора фильтра
        select = OriginSelect(self.user_id, self.forecast)
        select.parent_view = self
        self.clear_items()
        self.add_item(select)
        
        # Добавляем кнопку "Назад"
        back_button = Button(label="◀ Назад к обзору", style=discord.ButtonStyle.secondary)
        back_button.callback = self.show_overview
        self.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=self)


# ==================== ОСНОВНАЯ КОМАНДА ====================

async def show_consumption_forecast(ctx, user_id: int):
    """Показать прогноз потребления"""
    
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
    
    # Получаем прогноз
    forecast = get_consumption_forecast(player_data)
    
    embed = discord.Embed(
        title=f"📊 Прогноз потребления: {forecast['country']}",
        description=f"Население: {format_number(forecast['population'])} чел.\n"
                   f"Прогноз на 1 год",
        color=DARK_THEME_COLOR
    )
    
    # Общая статистика
    total_spent = sum(c["total_spent"] for c in forecast["categories"].values())
    total_units = sum(c["total_units"] for c in forecast["categories"].values())
    
    embed.add_field(
        name="📈 Общие показатели",
        value=f"📦 Всего товаров: {format_number(int(total_units))}\n"
              f"💰 Всего потрачено: {format_billion(total_spent)}\n"
              f"🏢 Активных корпораций: {len(forecast['corporations'])}",
        inline=False
    )
    
    # Топ-3 категории
    top_categories = sorted(
        [(name, data) for name, data in forecast["categories"].items() if data["total_units"] > 0],
        key=lambda x: x[1]["total_spent"],
        reverse=True
    )[:3]
    
    for cat_name, cat_data in top_categories:
        icon = CONSUMPTION_CATEGORIES.get(cat_name, {}).get("icon", "📦")
        embed.add_field(
            name=f"{icon} {cat_name}",
            value=f"{format_billion(cat_data['total_spent'])}",
            inline=True
        )
    
    # Топ-3 корпорации
    if forecast["corporations"]:
        top_corps = sorted(
            [(name, data) for name, data in forecast["corporations"].items()],
            key=lambda x: x[1]["total_revenue"],
            reverse=True
        )[:3]
        
        corps_text = ""
        for corp_id, corp_data in top_corps:
            flag = "🇺🇦" if corp_data["is_local"] else "🌍"
            profit = corp_data["total_revenue"] * 0.15
            corps_text += f"{flag} **{corp_data['name']}**: {format_billion(corp_data['total_revenue'])} (прибыль {format_billion(profit)})\n"
        
        embed.add_field(name="🏢 Топ-3 корпорации", value=corps_text, inline=False)
    
    view = ConsumptionForecastView(user_id, forecast)
    
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await ctx.send(embed=embed, view=view, ephemeral=True)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_consumption_forecast',
    'CONSUMPTION_CATEGORIES'
]

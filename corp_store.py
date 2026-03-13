# corp_store.py - Модуль для покупки техники у корпораций

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import asyncio
import json
from datetime import datetime, timedelta
import math

# Импортируем базу данных корпораций
from corporations_db import get_corporation, get_all_corporations, ALL_CORPORATIONS

# Импортируем таможенную систему
from trade_tariffs import TariffSystem, filter_corporations_by_tariffs, is_corporation_available
from trade_tariffs import PRODUCT_CATEGORIES

# Файл для хранения активных заказов
PRODUCTION_QUEUE_FILE = 'production_queue.json'

# Цвет для эмбедов в тёмной теме Discord
DARK_THEME_COLOR = 0x2b2d31

# ==================== СИСТЕМА ЗАГРУЗКИ/СОХРАНЕНИЯ ПРОИЗВОДСТВА ====================
def load_production_queue():
    """Загрузка очереди производства"""
    try:
        with open(PRODUCTION_QUEUE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_orders": [], "completed_orders": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"active_orders": [], "completed_orders": []}
    except json.JSONDecodeError:
        return {"active_orders": [], "completed_orders": []}

def save_production_queue(data):
    """Сохранение очереди производства"""
    with open(PRODUCTION_QUEUE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==================== СЛОВАРЬ СКОРОСТИ ПРОИЗВОДСТВА ====================
PRODUCTION_SPEED = {
    # Наземная техника
    "ground.tanks": 2 * 3600,
    "ground.btr": 1 * 3600,
    "ground.bmp": 1.5 * 3600,
    "ground.armored_vehicles": 45 * 60,
    "ground.trucks": 20 * 60,
    "ground.cars": 10 * 60,
    "ground.ew_vehicles": 4 * 3600,
    "ground.engineering_equipment": 2 * 3600,
    "ground.radar_systems": 6 * 3600,
    "ground.self_propelled_artillery": 3 * 3600,
    "ground.towed_artillery": 2 * 3600,
    "ground.mlrs": 3 * 3600,
    "ground.atgm_complexes": 1 * 3600,
    "ground.otr_complexes": 8 * 3600,
    "ground.zas": 2 * 3600,
    "ground.zdprk": 4 * 3600,
    "ground.short_range_air_defense": 5 * 3600,
    "ground.long_range_air_defense": 12 * 3600,
    
    # Снаряжение
    "equipment.small_arms": 30,
    "equipment.grenade_launchers": 4 * 60,
    "equipment.atgms": 10 * 60,
    "equipment.manpads": 20 * 60,
    "equipment.medical_equipment": 5 * 60,
    "equipment.engineering_equipment_units": 20 * 60,
    "equipment.fpv_drones": 2 * 60,
    
    # Авиация
    "air.fighters": 24 * 3600,
    "air.attack_aircraft": 20 * 3600,
    "air.bombers": 36 * 3600,
    "air.transport_aircraft": 30 * 3600,
    "air.attack_helicopters": 16 * 3600,
    "air.transport_helicopters": 12 * 3600,
    "air.recon_uav": 4 * 3600,
    "air.attack_uav": 6 * 3600,
    "air.kamikaze_uav": 45 * 60,
    
    # Флот
    "navy.boats": 8 * 3600,
    "navy.corvettes": 48 * 3600,
    "navy.destroyers": 72 * 3600,
    "navy.cruisers": 96 * 3600,
    "navy.aircraft_carriers": 168 * 3600,
    "navy.submarines": 96 * 3600,
    
    # Ракеты
    "missiles.strategic_nuclear": 48 * 3600,
    "missiles.tactical_nuclear": 36 * 3600,
    "missiles.cruise_missiles": 6 * 3600,
    "missiles.hypersonic_missiles": 24 * 3600,
    "missiles.ballistic_missiles": 12 * 3600
}

# Соответствие игрового времени
def get_game_time_description(real_seconds):
    """Получить описание времени в игровом масштабе"""
    game_months = real_seconds / 3600 * 3 / 30
    
    if game_months < 1:
        game_days = game_months * 30
        return f"{game_days:.0f} игровых дней"
    elif game_months < 3:
        return f"{game_months:.0f} игровых месяцев"
    elif game_months < 12:
        return f"{game_months/3:.1f} игровых кварталов"
    else:
        years = game_months / 12
        return f"{years:.1f} игровых лет"

# Человекочитаемые названия для типов техники
EQUIPMENT_NAMES = {
    "ground.tanks": "Танки",
    "ground.btr": "БТР",
    "ground.bmp": "БМП",
    "ground.armored_vehicles": "Бронеавтомобили",
    "ground.trucks": "Грузовики",
    "ground.cars": "Автомобили",
    "ground.ew_vehicles": "Машины РЭБ",
    "ground.engineering_equipment": "Инженерная техника",
    "ground.radar_systems": "РЛС",
    "ground.self_propelled_artillery": "САУ",
    "ground.towed_artillery": "Буксируемая артиллерия",
    "ground.mlrs": "РСЗО",
    "ground.atgm_complexes": "ПТРК",
    "ground.otr_complexes": "ОТРК",
    "ground.zas": "Зенитная артиллерия",
    "ground.zdprk": "ЗПРК",
    "ground.short_range_air_defense": "ПВО ближнего действия",
    "ground.long_range_air_defense": "ПВО дальнего действия",
    "equipment.small_arms": "Стрелковое оружие",
    "equipment.grenade_launchers": "Гранатометы",
    "equipment.atgms": "Переносные ПТРК",
    "equipment.manpads": "ПЗРК",
    "equipment.medical_equipment": "Медицинское оборудование",
    "equipment.engineering_equipment_units": "Инженерное снаряжение",
    "equipment.fpv_drones": "FPV-дроны",
    "air.fighters": "Истребители",
    "air.attack_aircraft": "Штурмовики",
    "air.bombers": "Бомбардировщики",
    "air.transport_aircraft": "Транспортные самолеты",
    "air.attack_helicopters": "Ударные вертолеты",
    "air.transport_helicopters": "Транспортные вертолеты",
    "air.recon_uav": "Разведывательные БПЛА",
    "air.attack_uav": "Ударные БПЛА",
    "air.kamikaze_uav": "Дроны-камикадзе",
    "navy.boats": "Катера",
    "navy.corvettes": "Корветы",
    "navy.destroyers": "Эсминцы",
    "navy.cruisers": "Крейсера",
    "navy.aircraft_carriers": "Авианосцы",
    "navy.submarines": "Подводные лодки",
    "missiles.strategic_nuclear": "Стратегическое ядерное оружие",
    "missiles.tactical_nuclear": "Тактическое ядерное оружие",
    "missiles.cruise_missiles": "Крылатые ракеты",
    "missiles.hypersonic_missiles": "Гиперзвуковые ракеты",
    "missiles.ballistic_missiles": "Баллистические ракеты"
}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def format_time(seconds):
    """Форматирование реального времени в человекочитаемый вид"""
    if seconds < 60:
        return f"{seconds:.0f} сек"
    elif seconds < 3600:
        return f"{seconds // 60} мин"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours} ч {minutes} мин"
        return f"{hours} ч"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        if hours > 0:
            return f"{days} дн {hours} ч"
        return f"{days} дн"

def get_production_time(product_path, quantity=1):
    """Получить общее время производства для заказа"""
    base_time = PRODUCTION_SPEED.get(product_path, 3600)
    
    if quantity <= 1:
        return base_time
    elif quantity <= 5:
        total = base_time
        for i in range(1, quantity):
            total += base_time * (0.7 ** i)
        return total
    elif quantity <= 20:
        return base_time * (1 + (quantity - 1) * 0.4)
    else:
        return base_time * (1 + (quantity - 1) * 0.25)

def is_trade_blocked(tariff_system, buyer_country: str, seller_country: str, product_type: str) -> bool:
    """Проверяет, заблокирована ли торговля между странами"""
    # Проверка 1: Может ли покупатель покупать у продавца?
    if tariff_system.is_product_embargoed(seller_country, product_type):
        return True
    
    # Проверка 2: Может ли продавец продавать покупателю?
    seller_tariff = TariffSystem(seller_country)
    if seller_tariff.is_product_embargoed(buyer_country, product_type):
        return True
    
    return False

# ==================== МОДАЛЬНОЕ ОКНО ДЛЯ ВВОДА КОЛИЧЕСТВА ====================
class QuantityModal(Modal, title="Введите количество"):
    def __init__(self, corporation, product_key, product, user_id, player_country, tariff_system, original_message):
        super().__init__()
        self.corporation = corporation
        self.product_key = product_key
        self.product = product
        self.user_id = user_id
        self.player_country = player_country
        self.tariff_system = tariff_system
        self.original_message = original_message
        
        self.quantity_input = TextInput(
            label="Количество",
            placeholder="Введите число (макс. 100000)",
            min_length=1,
            max_length=6,
            required=True
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
            if quantity < 1 or quantity > 100000:
                await interaction.response.send_message("❌ Количество должно быть от 1 до 100000!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        # Удаляем оригинальное сообщение
        try:
            await self.original_message.delete()
        except:
            pass
        
        # Показываем подтверждение с правильными аргументами
        view = PurchaseConfirmation(
            self.corporation, 
            self.product_key, 
            self.product, 
            quantity, 
            self.user_id,
            self.player_country,
            self.tariff_system
        )
        
        total_price = self.product['price'] * quantity
        prod_time = get_production_time(self.product['type'], quantity)
        game_time = get_game_time_description(prod_time)
        
        embed = discord.Embed(
            title="Подтверждение покупки",
            description="Проверьте детали заказа:",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Корпорация", value=self.corporation.name, inline=True)
        embed.add_field(name="Продукт", value=self.product['name'], inline=True)
        embed.add_field(name="Количество", value=str(quantity), inline=True)
        embed.add_field(name="Стоимость", value=f"${total_price:,}", inline=True)
        embed.add_field(name="Время", value=format_time(prod_time), inline=True)
        embed.add_field(name="Игровое время", value=game_time, inline=True)
        
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
        countries = list(ALL_CORPORATIONS.keys())
        
        for country in countries[:25]:  # Discord ограничение - 25 стран
            # Считаем доступные корпорации в этой стране
            available_count = 0
            total_count = 0
            for corp_id, corp in ALL_CORPORATIONS[country].items():
                if hasattr(corp, 'products') and corp.products:
                    total_count += 1
                    # Проверяем доступность корпорации с учётом эмбарго с обеих сторон
                    if not is_trade_blocked(self.tariff_system, self.player_country, corp.country, "all"):
                        available_count += 1
            
            # Определяем эмодзи в зависимости от доступности
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
            placeholder="Выберите страну-производителя...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        country = self.values[0]
        
        # Удаляем старое сообщение
        try:
            await self.original_message.delete()
        except:
            pass
        
        # Показываем корпорации выбранной страны
        view = CountryCorporationView(self.user_id, self.player_country, country, self.tariff_system)
        
        embed = discord.Embed(
            title=f"Корпорации {country}",
            description="Выберите корпорацию:",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ==================== ВЫБОР КОРПОРАЦИИ ИЗ СТРАНЫ ====================
class CountryCorporationView(View):
    """Кнопки для выбора корпорации из конкретной страны"""
    def __init__(self, user_id, player_country, country, tariff_system):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.player_country = player_country
        self.country = country
        self.tariff_system = tariff_system
        
        # Получаем корпорации выбранной страны
        corporations = list(ALL_CORPORATIONS[country].values())
        
        # Создаем кнопки для каждой корпорации
        for corp in corporations:
            # Проверяем доступность корпорации с обеих сторон
            available = not is_trade_blocked(self.tariff_system, self.player_country, corp.country, "all")
            
            button = Button(
                label=corp.name[:80],
                style=discord.ButtonStyle.secondary,
                custom_id=f"corp_{corp.id}",
                disabled=not available  # Блокируем недоступные корпорации
            )
            button.callback = self.create_corp_callback(corp, available)
            self.add_item(button)
        
        # Кнопка назад к списку стран
        back_button = Button(
            label="◀ Назад к странам",
            style=discord.ButtonStyle.secondary
        )
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    def create_corp_callback(self, corp, available):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
                return
            
            if not available:
                await interaction.response.send_message(
                    f"❌ Корпорация {corp.name} недоступна из-за эмбарго!",
                    ephemeral=True
                )
                return
            
            # Удаляем текущее сообщение
            try:
                await interaction.message.delete()
            except:
                pass
            
            embed = discord.Embed(
                title=corp.name,
                description=corp.description if corp.description else "Нет описания",
                color=DARK_THEME_COLOR
            )
            
            if hasattr(corp, 'founded') and corp.founded:
                embed.add_field(name="Год основания", value=corp.founded, inline=True)
            
            embed.add_field(name="Страна", value=corp.country, inline=True)
            
            if hasattr(corp, 'specialization') and corp.specialization:
                spec_names = {
                    "tanks": "Танки", "btr": "БТР", "bmp": "БМП", "armored_vehicles": "Бронеавтомобили",
                    "trucks": "Грузовики", "cars": "Автомобили", "ew_vehicles": "РЭБ", "engineering_equipment": "Инженерная техника",
                    "radar_systems": "РЛС", "self_propelled_artillery": "САУ", "towed_artillery": "Буксируемая артиллерия",
                    "mlrs": "РСЗО", "atgm_complexes": "ПТРК", "otr_complexes": "ОТРК", "zas": "Зенитная артиллерия",
                    "zdprk": "ЗПРК", "short_range_air_defense": "ПВО ближнего действия", "long_range_air_defense": "ПВО дальнего действия",
                    "small_arms": "Стрелковое оружие", "grenade_launchers": "Гранатометы", "atgms": "Переносные ПТРК",
                    "manpads": "ПЗРК", "medical_equipment": "Медицинское оборудование", "engineering_equipment_units": "Инженерное снаряжение",
                    "fighters": "Истребители", "attack_aircraft": "Штурмовики", "bombers": "Бомбардировщики",
                    "transport_aircraft": "Транспортные самолеты", "attack_helicopters": "Ударные вертолеты",
                    "transport_helicopters": "Транспортные вертолеты", "recon_uav": "Разведывательные БПЛА",
                    "attack_uav": "Ударные БПЛА", "aircraft_carriers": "Авианосцы", "destroyers": "Эсминцы",
                    "cruisers": "Крейсера", "corvettes": "Корветы", "submarines": "Подводные лодки", "boats": "Катера",
                    "strategic_nuclear": "Стратегическое ядерное оружие", "tactical_nuclear": "Тактическое ядерное оружие",
                    "cruise_missiles": "Крылатые ракеты", "hypersonic_missiles": "Гиперзвуковые ракеты", "ballistic_missiles": "Баллистические ракеты"
                }
                
                specs = []
                for spec in corp.specialization:
                    if spec in spec_names:
                        specs.append(spec_names[spec])
                    else:
                        specs.append(spec)
                
                if specs:
                    embed.add_field(name="Специализация", value=", ".join(specs[:5]), inline=False)
            
            if hasattr(corp, 'products') and corp.products:
                embed.add_field(name="Продуктов", value=str(len(corp.products)), inline=True)
            
            # Проверяем, нет ли эмбарго на страну
            if self.tariff_system.is_product_embargoed(corp.country, "all"):
                embed.add_field(
                    name="🚫 Эмбарго",
                    value=f"Торговля с {corp.country} запрещена!",
                    inline=False
                )
            
            # Проверяем санкции
            sanction_penalty = self.tariff_system.get_sanction_penalty(corp.country)
            if sanction_penalty > 0:
                embed.add_field(
                    name="⚠️ Санкции",
                    value=f"Дополнительная пошлина: +{sanction_penalty*100}%",
                    inline=False
                )
            
            view = ProductListView(corp, self.user_id, self.player_country, self.tariff_system)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        return callback
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Удаляем текущее сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Возвращаемся к выбору страны
        await show_corporations_menu(interaction, self.user_id)


# ==================== КЛАССЫ ДЛЯ ВЫБОРА ПРОДУКТОВ ====================
class ProductListView(View):
    """Кнопки для выбора категории продуктов"""
    def __init__(self, corporation, user_id, player_country, tariff_system):
        super().__init__(timeout=300)
        self.corporation = corporation
        self.user_id = user_id
        self.player_country = player_country
        self.tariff_system = tariff_system
        
        # Группируем продукты по категориям
        categories = {}
        for key, product in corporation.products.items():
            if 'type' in product:
                category = product.get("type", "").split('.')[0]
                if category not in categories:
                    categories[category] = []
                categories[category].append((key, product))
        
        category_names = {
            "ground": "Сухопутные",
            "equipment": "Снаряжение",
            "air": "Авиация",
            "navy": "Флот",
            "missiles": "Ракеты"
        }
        
        for category, products in categories.items():
            if products:
                button = Button(
                    label=category_names.get(category, category),
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"cat_{category}"
                )
                button.callback = self.create_category_callback(category, products)
                self.add_item(button)
        
        if not categories:
            button = Button(
                label="Все продукты",
                style=discord.ButtonStyle.secondary
            )
            all_products = [(key, product) for key, product in corporation.products.items()]
            button.callback = self.create_category_callback("all", all_products)
            self.add_item(button)
        
        back_button = Button(
            label="◀ Назад к списку",
            style=discord.ButtonStyle.secondary
        )
        back_button.callback = self.back_callback
        self.add_item(back_button)
    
    def create_category_callback(self, category, products):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
                return
            
            category_names = {
                "ground": "Сухопутная техника",
                "equipment": "Снаряжение",
                "air": "Авиация",
                "navy": "Военно-морской флот",
                "missiles": "Ракетное вооружение",
                "all": "Все продукты"
            }
            
            embed = discord.Embed(
                title=self.corporation.name,
                description=category_names.get(category, category),
                color=DARK_THEME_COLOR
            )
            
            # Удаляем текущее сообщение
            try:
                await interaction.message.delete()
            except:
                pass
            
            # Создаём новое сообщение с Select
            select = ProductSelect(products, self.corporation, self.user_id, self.player_country, self.tariff_system)
            view = View(timeout=300)
            view.add_item(select)
            
            back_button = Button(
                label="◀ Назад к категориям",
                style=discord.ButtonStyle.secondary
            )
            back_button.callback = self.back_to_categories
            view.add_item(back_button)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        return callback
    
    async def back_callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Удаляем текущее сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        await show_corporations_menu(interaction, self.user_id)
    
    async def back_to_categories(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=self.corporation.name,
            description=self.corporation.description if self.corporation.description else "Нет описания",
            color=DARK_THEME_COLOR
        )
        
        # Удаляем текущее сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Возвращаемся к списку категорий
        await interaction.response.send_message(embed=embed, view=self, ephemeral=True)


class ProductSelect(Select):
    """Выпадающий список для выбора продукта"""
    def __init__(self, products, corporation, user_id, player_country, tariff_system):
        self.corporation = corporation
        self.user_id = user_id
        self.player_country = player_country
        self.tariff_system = tariff_system
        
        options = []
        for key, product in products:
            if 'name' in product and 'price' in product:
                price_str = f"${product['price']:,}"
                prod_time = PRODUCTION_SPEED.get(product.get('type', ''), 3600)
                time_str = format_time(prod_time)
                
                label = product['name'][:90]
                description = f"{price_str} | {time_str}"
                
                options.append(
                    discord.SelectOption(
                        label=label,
                        description=description,
                        value=key
                    )
                )
        
        super().__init__(
            placeholder="Выберите продукт...",
            min_values=1,
            max_values=1,
            options=options[:25]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        product_key = self.values[0]
        product = self.corporation.products[product_key]
        
        # Проверяем доступность конкретного типа продукта
        if is_trade_blocked(self.tariff_system, self.player_country, self.corporation.country, product.get('type', '')):
            await interaction.response.send_message(
                f"❌ Продукт {product.get('name', 'Неизвестный')} недоступен из-за эмбарго!",
                ephemeral=True
            )
            return
        
        prod_time = PRODUCTION_SPEED.get(product.get('type', ''), 3600)
        game_time = get_game_time_description(prod_time)
        
        embed = discord.Embed(
            title=product.get('name', 'Неизвестный продукт'),
            description=product.get('description', 'Нет описания'),
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Цена", value=f"${product.get('price', 0):,}", inline=True)
        embed.add_field(name="Время", value=format_time(prod_time), inline=True)
        embed.add_field(name="Игровое время", value=game_time, inline=True)
        
        equip_type = product.get('type', '')
        equip_name = EQUIPMENT_NAMES.get(equip_type, equip_type.split('.')[-1] if '.' in equip_type else equip_type)
        embed.add_field(name="Тип", value=equip_name, inline=False)
        
        # Удаляем текущее сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Создаём новое сообщение с выбором количества
        view = QuantitySelector(self.corporation, product_key, product, self.user_id, self.player_country, self.tariff_system)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class QuantitySelector(View):
    """Выбор количества и подтверждение покупки"""
    def __init__(self, corporation, product_key, product, user_id, player_country, tariff_system):
        super().__init__(timeout=300)
        self.corporation = corporation
        self.product_key = product_key
        self.product = product
        self.user_id = user_id
        self.player_country = player_country
        self.tariff_system = tariff_system
        self.quantity = 1
        
        minus_button = Button(label="➖", style=discord.ButtonStyle.secondary)
        minus_button.callback = self.decrease_quantity
        self.add_item(minus_button)
        
        self.quantity_label = Button(
            label=f"1",
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
        
        if self.quantity < 100000:
            self.quantity += 1
            self.quantity_label.label = str(self.quantity)
            await self.update_embed(interaction)
        else:
            await interaction.response.defer()
    
    async def manual_input(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Передаём все необходимые аргументы в QuantityModal
        modal = QuantityModal(
            self.corporation, 
            self.product_key, 
            self.product, 
            self.user_id,
            self.player_country,
            self.tariff_system,
            interaction.message
        )
        await interaction.response.send_modal(modal)
    
    async def update_embed(self, interaction):
        total_price = self.product.get('price', 0) * self.quantity
        prod_time = get_production_time(self.product.get('type', ''), self.quantity)
        game_time = get_game_time_description(prod_time)
        
        embed = discord.Embed(
            title=self.product.get('name', 'Неизвестный продукт'),
            description=self.product.get('description', 'Нет описания'),
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Цена за ед.", value=f"${self.product.get('price', 0):,}", inline=True)
        embed.add_field(name="Количество", value=str(self.quantity), inline=True)
        embed.add_field(name="Общая сумма", value=f"${total_price:,}", inline=True)
        embed.add_field(name="Время", value=format_time(prod_time), inline=True)
        embed.add_field(name="Игровое время", value=game_time, inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def confirm_purchase(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Финальная проверка продукта
        if is_trade_blocked(self.tariff_system, self.player_country, self.corporation.country, self.product.get('type', '')):
            await interaction.response.send_message(
                f"❌ Продукт {self.product.get('name', 'Неизвестный')} недоступен из-за эмбарго!",
                ephemeral=True
            )
            return
        
        # Удаляем текущее сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Показываем confirmation диалог с правильными аргументами
        view = PurchaseConfirmation(
            self.corporation, 
            self.product_key, 
            self.product, 
            self.quantity, 
            self.user_id,
            self.player_country,
            self.tariff_system
        )
        
        total_price = self.product.get('price', 0) * self.quantity
        prod_time = get_production_time(self.product.get('type', ''), self.quantity)
        game_time = get_game_time_description(prod_time)
        
        embed = discord.Embed(
            title="Подтверждение покупки",
            description="Проверьте детали заказа:",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Корпорация", value=self.corporation.name, inline=True)
        embed.add_field(name="Продукт", value=self.product.get('name', 'Неизвестный продукт'), inline=True)
        embed.add_field(name="Количество", value=str(self.quantity), inline=True)
        embed.add_field(name="Стоимость", value=f"${total_price:,}", inline=True)
        embed.add_field(name="Время", value=format_time(prod_time), inline=True)
        embed.add_field(name="Игровое время", value=game_time, inline=True)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    async def go_back(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Удаляем текущее сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Возвращаемся к списку продуктов
        embed = discord.Embed(
            title=self.corporation.name,
            color=DARK_THEME_COLOR
        )
        
        products_list = []
        current_category = self.product.get('type', '').split('.')[0] if '.' in self.product.get('type', '') else ''
        
        for key, product in self.corporation.products.items():
            product_category = product.get('type', '').split('.')[0] if '.' in product.get('type', '') else ''
            if product_category == current_category or not current_category:
                products_list.append((key, product))
        
        select = ProductSelect(products_list, self.corporation, self.user_id, self.player_country, self.tariff_system)
        view = View(timeout=300)
        view.add_item(select)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PurchaseConfirmation(View):
    """Подтверждение покупки"""
    def __init__(self, corporation, product_key, product, quantity, user_id, player_country, tariff_system):
        super().__init__(timeout=300)
        self.corporation = corporation
        self.product_key = product_key
        self.product = product
        self.quantity = quantity
        self.user_id = user_id
        self.player_country = player_country
        self.tariff_system = tariff_system
        
        confirm_button = Button(
            label="Подтвердить",
            style=discord.ButtonStyle.secondary
        )
        confirm_button.callback = self.confirm
        self.add_item(confirm_button)
        
        cancel_button = Button(
            label="Отмена",
            style=discord.ButtonStyle.secondary
        )
        cancel_button.callback = self.cancel
        self.add_item(cancel_button)
    
    async def confirm(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        from bot import load_states, save_states
        
        states = load_states()
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(interaction.user.id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("❌ У вас нет государства!", ephemeral=True)
            return
        
        # Получаем страну игрока и страну производителя
        buyer_country = player_data["state"]["statename"]
        seller_country = self.corporation.country
        product_type = self.product.get('type', 'unknown')
        
        # ❗️ ДВОЙНАЯ ПРОВЕРКА ЭМБАРГО ❗️
        
        # Проверка 1: Может ли покупатель покупать у продавца?
        if self.tariff_system.is_product_embargoed(seller_country, product_type):
            await interaction.response.send_message(
                f"❌ Ваша страна ввела эмбарго против {seller_country}!",
                ephemeral=True
            )
            return
        
        # Проверка 2: Может ли продавец продавать покупателю?
        seller_tariff = TariffSystem(seller_country)
        if seller_tariff.is_product_embargoed(buyer_country, product_type):
            await interaction.response.send_message(
                f"❌ Страна {seller_country} ввела эмбарго против вашей страны!",
                ephemeral=True
            )
            return
        
        # Рассчитываем пошлины
        base_price = self.product.get('price', 0) * self.quantity
        
        # Импортная пошлина (платит покупатель в свой бюджет)
        import_tariff = self.tariff_system.calculate_import_tariff(
            product_type, 
            seller_country, 
            base_price
        )
        
        # Экспортная пошлина (платит продавец в свой бюджет)
        export_tariff = seller_tariff.calculate_export_tariff(
            product_type,
            base_price
        )
        
        # Покупатель платит: base_price + import_tariff
        buyer_pays = base_price + import_tariff
        
        # Продавец получает: base_price - export_tariff (но мы не храним деньги продавца)
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
        
        save_states(states)
        
        # Создаем заказ
        queue = load_production_queue()
        
        prod_time = get_production_time(self.product.get('type', ''), self.quantity)
        completion_time = datetime.now() + timedelta(seconds=prod_time)
        
        order = {
            "id": len(queue["active_orders"]) + 1,
            "user_id": str(interaction.user.id),
            "user_name": interaction.user.name,
            "corporation": self.corporation.name,
            "corporation_country": seller_country,
            "product_name": self.product.get('name', 'Неизвестный продукт'),
            "product_type": product_type,
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
        save_production_queue(queue)
        
        game_time = get_game_time_description(prod_time)
        
        embed = discord.Embed(
            title="Заказ оформлен!",
            description="Техника запущена в производство",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Корпорация", value=self.corporation.name, inline=True)
        embed.add_field(name="Продукт", value=self.product.get('name', 'Неизвестный продукт'), inline=True)
        embed.add_field(name="Количество", value=str(self.quantity), inline=True)
        embed.add_field(name="Базовая стоимость", value=f"${base_price:,}", inline=True)
        
        if import_tariff > 0:
            embed.add_field(name="🛃 Импортная пошлина (в ваш бюджет)", value=f"${import_tariff:,}", inline=True)
        
        if export_tariff > 0:
            embed.add_field(name="📤 Экспортная пошлина (бюджет продавца)", value=f"${export_tariff:,}", inline=True)
        
        embed.add_field(name="💵 Итоговая стоимость", value=f"${buyer_pays:,}", inline=True)
        embed.add_field(name="Готовность через", value=format_time(prod_time), inline=True)
        embed.add_field(name="Игровое время", value=game_time, inline=True)
        embed.add_field(name="ID заказа", value=str(order['id']), inline=True)
        embed.add_field(name="Статус", value="В производстве", inline=True)
        
        embed.set_footer(text="Используйте !заказы и !получить для отслеживания")
        
        # Удаляем confirmation сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Покупка отменена",
            color=DARK_THEME_COLOR
        )
        
        # Удаляем confirmation сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ==================== ОСНОВНЫЕ ФУНКЦИИ ДЛЯ ВЫЗОВА ====================

async def show_corporations_menu(interaction_or_ctx, user_id):
    """Показать меню выбора корпораций (ВСЕ КОРПОРАЦИИ МИРА)"""
    from bot import load_states
    
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
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message(error_msg, ephemeral=True)
        else:
            await interaction_or_ctx.send(error_msg)
        return
    
    # Создаём таможенную систему для фильтрации
    tariff_system = TariffSystem(player_country)
    
    # Считаем общее количество корпораций
    all_corps = get_all_corporations()
    total_corps = len(all_corps)
    
    # Считаем доступные корпорации с учётом эмбарго с обеих сторон
    available_corps = []
    for corp in all_corps:
        if hasattr(corp, 'country'):
            # Проверка 1: Есть ли у покупателя эмбарго против страны корпорации?
            if tariff_system.is_product_embargoed(corp.country, "all"):
                continue
            
            # Проверка 2: Есть ли у страны корпорации эмбарго против покупателя?
            seller_tariff = TariffSystem(corp.country)
            if seller_tariff.is_product_embargoed(player_country, "all"):
                continue
            
            available_corps.append(corp)
    
    available_count = len(available_corps)
    
    embed = discord.Embed(
        title=f"Военно-промышленный комплекс",
        description=f"Доступные корпорации мира",
        color=DARK_THEME_COLOR
    )
    
    # Добавляем статистику
    embed.add_field(
        name="📊 Статистика",
        value=f"Всего корпораций: **{total_corps}**\n"
              f"Доступно: **{available_count}**\n"
              f"Под санкциями/эмбарго: **{total_corps - available_count}**",
        inline=False
    )
    
    # Добавляем информацию о действующих санкциях и эмбарго
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
    
    # Добавляем информацию об эмбарго других стран против игрока
    embargoed_against = []
    for country in ["США", "Россия", "Китай", "Германия", "Великобритания", "Франция", "Япония", "Израиль", "Украина", "Иран"]:
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
    
    sanctions = tariff_system.tariffs.get("sanctions", {})
    if sanctions:
        sanctions_text = ""
        for country, data in list(sanctions.items())[:3]:
            sanctions_text += f"• {country}: +{data['penalty']}%\n"
        embed.add_field(name="⚠️ Санкции", value=sanctions_text, inline=False)
    
    # Отправляем эфемерное сообщение
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
        message = await interaction_or_ctx.original_response()
    else:
        message = await interaction_or_ctx.send(embed=embed, ephemeral=True)
    
    # Создаём View с Select для выбора страны
    select = CountrySelect(user_id, player_country, message, tariff_system)
    view = View(timeout=300)
    view.add_item(select)
    
    await message.edit(view=view)


async def show_my_orders(ctx):
    """Показать текущие заказы игрока"""
    queue = load_production_queue()
    user_orders = [o for o in queue["active_orders"] if o["user_id"] == str(ctx.author.id)]
    
    if not user_orders:
        await ctx.send("📦 У вас нет активных заказов.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="Мои заказы",
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
            tariff_info += f"🛃 Пошлина: ${order['import_tariff']:,} "
        if order.get('export_tariff', 0) > 0:
            tariff_info += f"📤 Эксп. пошлина: ${order['export_tariff']:,}"
        
        embed.add_field(
            name=f"Заказ #{order['id']} | {order['product_name']} x{order['quantity']}",
            value=f"{order['corporation']}\n{tariff_info}\n{status}",
            inline=False
        )
    
    await ctx.send(embed=embed, ephemeral=True)


async def collect_completed_orders(ctx):
    """Забрать готовые заказы"""
    queue = load_production_queue()
    from bot import load_states, save_states
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
    
    for order in queue["active_orders"][:]:
        if order["user_id"] == str(ctx.author.id):
            completion = datetime.fromisoformat(order["completion_time"])
            
            if completion <= now:
                path = order["product_type"].split('.')
                
                if "army" not in player_data:
                    player_data["army"] = {}
                
                current = player_data["army"]
                
                for key in path[:-1]:
                    if key not in current:
                        current[key] = {}
                    current = current[key]
                
                last_key = path[-1]
                current[last_key] = current.get(last_key, 0) + order["quantity"]
                
                order["status"] = "completed"
                order["collected_at"] = str(now)
                queue["completed_orders"].append(order)
                queue["active_orders"].remove(order)
                collected.append(order)
    
    if collected:
        save_states(states)
        save_production_queue(queue)
        
        embed = discord.Embed(
            title="Техника получена!",
            color=DARK_THEME_COLOR
        )
        
        for order in collected:
            equip_type = order['product_type']
            equip_name = EQUIPMENT_NAMES.get(equip_type, equip_type.split('.')[-1] if '.' in equip_type else equip_type)
            
            tariff_info = ""
            if order.get('import_tariff', 0) > 0:
                tariff_info += f"\n🛃 Вы заплатили пошлину: ${order['import_tariff']:,}"
            if order.get('export_tariff', 0) > 0:
                tariff_info += f"\n📤 Экспортная пошлина удержана: ${order['export_tariff']:,}"
            
            embed.add_field(
                name=f"{order['product_name']} x{order['quantity']}",
                value=f"{order['corporation']}\nТип: {equip_name}{tariff_info}\n✅ Техника добавлена в армию",
                inline=False
            )
        
        await ctx.send(embed=embed, ephemeral=True)
    else:
        await ctx.send("❌ У вас нет готовых заказов.", ephemeral=True)


async def production_check_loop(bot_instance):
    """Фоновая задача для проверки производства"""
    await bot_instance.wait_until_ready()
    while not bot_instance.is_closed():
        try:
            queue = load_production_queue()
            now = datetime.now()
            
            for order in queue["active_orders"]:
                completion = datetime.fromisoformat(order["completion_time"])
                if completion <= now and not order.get("notified", False):
                    try:
                        user = await bot_instance.fetch_user(int(order["user_id"]))
                        if user:
                            embed = discord.Embed(
                                title="Заказ готов!",
                                description=f"Ваш заказ **{order['product_name']} x{order['quantity']}** готов к получению!",
                                color=DARK_THEME_COLOR
                            )
                            embed.add_field(name="Корпорация", value=order["corporation"])
                            embed.add_field(name="Команда", value="`!получить` для получения")
                            
                            if order.get('import_tariff', 0) > 0:
                                embed.add_field(name="🛃 Импортная пошлина", value=f"${order['import_tariff']:,}", inline=True)
                            if order.get('export_tariff', 0) > 0:
                                embed.add_field(name="📤 Экспортная пошлина", value=f"${order['export_tariff']:,}", inline=True)
                            
                            await user.send(embed=embed)
                    except:
                        pass
                    order["notified"] = True
                    save_production_queue(queue)
            
            await asyncio.sleep(3600)
        except Exception as e:
            print(f"Ошибка в production_check_loop: {e}")
            await asyncio.sleep(3600)


# ==================== ЭКСПОРТ ФУНКЦИЙ ====================

__all__ = [
    'show_corporations_menu',
    'show_my_orders',
    'collect_completed_orders',
    'production_check_loop',
    'EQUIPMENT_NAMES',
    'PRODUCTION_SPEED',
    'format_time'
]

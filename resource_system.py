# resource_system.py

import discord

# Типы ресурсов (с пользовательскими эмодзи)
# Формат: <:название_эмодзи:ID_эмодзи>
# Замените ID на реальные ID эмодзи с вашего сервера
RESOURCE_TYPES = {
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

# Альтернативный вариант с запасными стандартными эмодзи
RESOURCE_TYPES_FALLBACK = {
    "oil": "🛢️ Нефть",
    "gas": "🔥 Газ", 
    "coal": "⚫ Уголь",
    "uranium": "☢️ Уран",
    "steel": "⚙️ Сталь",
    "aluminum": "🛩️ Алюминий",
    "electronics": "💻 Электроника",
    "rare_metals": "💎 Редкие металлы",
    "food": "🌾 Продовольствие"
}

# Цены в тысячах долларов за единицу
RESOURCE_PRICES = {
    "oil": 500,        # 500,000$ за единицу
    "gas": 300,        # 300,000$ за единицу
    "coal": 100,       # 100,000$ за единицу
    "uranium": 2000,   # 2,000,000$ за единицу
    "steel": 200,      # 200,000$ за единицу
    "aluminum": 250,   # 250,000$ за единицу
    "electronics": 1000, # 1,000,000$ за единицу
    "rare_metals": 1500, # 1,500,000$ за единицу
    "food": 50         # 50,000$ за единицу
}

def get_resource_emoji(resource, use_custom=True):
    """Возвращает эмодзи для ресурса"""
    if use_custom:
        emoji = RESOURCE_TYPES.get(resource, "📦").split()[0]
    else:
        emojis = {
            "oil": "🛢️",
            "gas": "🔥",
            "coal": "⚫",
            "uranium": "☢️",
            "steel": "⚙️",
            "aluminum": "🛩️",
            "electronics": "💻",
            "rare_metals": "💎",
            "food": "🌾"
        }
        emoji = emojis.get(resource, "📦")
    return emoji

def get_resource_name(resource, use_custom=True):
    """Возвращает полное название ресурса с эмодзи"""
    if use_custom:
        return RESOURCE_TYPES.get(resource, f"📦 {resource}")
    else:
        return RESOURCE_TYPES_FALLBACK.get(resource, f"📦 {resource}")

def format_resource_amount(amount):
    """Форматирует количество ресурсов"""
    return f"{amount:,.0f}".replace(',', ' ')

def calculate_resource_value(resource, amount):
    """Рассчитывает стоимость ресурсов в долларах"""
    price = RESOURCE_PRICES.get(resource, 0)
    return amount * price * 1000  # переводим в доллары

def format_resource_value(value):
    """Форматирует стоимость ресурсов"""
    if value >= 1_000_000_000_000:
        return f"{value/1_000_000_000_000:.2f} трлн $"
    elif value >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f} млрд $"
    elif value >= 1_000_000:
        return f"{value/1_000_000:.2f} млн $"
    else:
        return f"{value:,.0f} $".replace(',', ' ')

def create_resource_embed(resources, title="Ресурсы", use_custom=True):
    """
    Создает embed со ВСЕМИ ресурсами в удобном формате
    """
    embed = discord.Embed(
        title=f"⛏️ {title}",
        description="Торговля только между игроками. Используйте `!торговля`",
        color=discord.Color.green()
    )
    
    total_value = 0
    all_resources = []
    
    # Собираем все ресурсы, даже те, которых нет (показываем 0)
    for res_id in RESOURCE_PRICES.keys():
        amount = resources.get(res_id, 0)
        value = calculate_resource_value(res_id, amount)
        total_value += value
        all_resources.append({
            'name': get_resource_name(res_id, use_custom),
            'amount': amount,
            'value': value,
            'id': res_id
        })
    
    # Группируем по категориям для лучшего отображения
    categories = {
        "🔥 Топливо": ["oil", "gas", "coal", "uranium"],
        "⚙️ Металлы": ["steel", "aluminum", "rare_metals"],
        "💻 Промышленность": ["electronics"],
        "🌾 Продовольствие": ["food"]
    }
    
    for category_name, res_ids in categories.items():
        category_text = ""
        for res_id in res_ids:
            for res in all_resources:
                if res['id'] == res_id:
                    emoji = get_resource_emoji(res_id, use_custom)
                    amount_str = format_resource_amount(res['amount'])
                    value_str = format_resource_value(res['value'])
                    category_text += f"{emoji} **{amount_str}** — {value_str}\n"
                    break
        
        if category_text:
            embed.add_field(name=category_name, value=category_text, inline=True)
    
    # Добавляем итоговую стоимость
    embed.add_field(
        name="💰 Общая стоимость",
        value=format_resource_value(total_value),
        inline=False
    )
    
    return embed

def create_trade_embed(resource, amount, price_per_unit, total_price, seller, use_custom=True):
    """Создает embed для торгового предложения (для обратной совместимости)"""
    embed = discord.Embed(
        title="📦 Торговое предложение",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="Ресурс",
        value=get_resource_name(resource, use_custom),
        inline=True
    )
    embed.add_field(
        name="Количество",
        value=format_resource_amount(amount),
        inline=True
    )
    embed.add_field(
        name="Цена за ед.",
        value=f"{price_per_unit/1000:.1f} тыс. $",
        inline=True
    )
    embed.add_field(
        name="Общая стоимость",
        value=format_resource_value(total_price),
        inline=True
    )
    embed.add_field(
        name="Продавец",
        value=seller,
        inline=True
    )
    
    return embed

def check_resource_sufficiency(resources, required_resources):
    """
    Проверяет достаточно ли ресурсов для производства/строительства
    required_resources: словарь вида {"oil": 10, "steel": 5}
    Возвращает (достаточно, недостающие_ресурсы)
    """
    missing = {}
    for resource, required_amount in required_resources.items():
        available = resources.get(resource, 0)
        if available < required_amount:
            missing[resource] = required_amount - available
    
    return len(missing) == 0, missing

# Функция для конвертации старых ресурсов в новые
def convert_old_resources(old_resources):
    """
    Конвертирует старую структуру ресурсов в новую
    old_resources: словарь с ключами "minerals" и "biological"
    """
    new_resources = {
        "oil": 0,
        "gas": 0,
        "coal": 0,
        "uranium": 0,
        "steel": 0,
        "aluminum": 0,
        "electronics": 0,
        "rare_metals": 0,
        "food": 0
    }
    
    if isinstance(old_resources, dict):
        # Конвертация из старого формата
        if "minerals" in old_resources:
            minerals = old_resources["minerals"]
            # Примерная конвертация (1 млн тонн = 1 единица)
            if "oil" in minerals:
                new_resources["oil"] = int(minerals["oil"] / 1_000_000_000)  # 1 млрд баррелей = 1 единица
            if "gas" in minerals:
                new_resources["gas"] = int(minerals["gas"] / 1_000_000_000_000)  # 1 трлн куб.футов = 1 единица
            if "coal" in minerals:
                new_resources["coal"] = int(minerals["coal"] / 1_000_000_000)  # 1 млрд тонн = 1 единица
            if "uranium" in minerals:
                new_resources["uranium"] = int(minerals["uranium"] / 1000)  # 1000 тонн = 1 единица
            if "rare_metals" in minerals:
                new_resources["rare_metals"] = int(minerals["rare_metals"] / 1_000_000)  # 1 млн тонн = 1 единица
            if "iron_ore" in minerals:
                new_resources["steel"] = int(minerals["iron_ore"] / 10_000_000)  # 10 млн тонн = 1 единица стали
            
        if "biological" in old_resources:
            bio = old_resources["biological"]
            if "grain" in bio:
                new_resources["food"] = int(bio["grain"] / 100_000_000)  # 100 млн тонн = 1 единица
        
        # Добавляем алюминий и электронику (базовые значения)
        new_resources["aluminum"] = 10
        new_resources["electronics"] = 10
    
    return new_resources

# Экспорт
__all__ = [
    'RESOURCE_TYPES',
    'RESOURCE_TYPES_FALLBACK',
    'RESOURCE_PRICES',
    'get_resource_emoji',
    'get_resource_name',
    'format_resource_amount',
    'calculate_resource_value',
    'format_resource_value',
    'create_resource_embed',
    'create_trade_embed',
    'check_resource_sufficiency',
    'convert_old_resources'
]

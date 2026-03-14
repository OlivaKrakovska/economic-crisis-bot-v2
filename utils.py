# utils.py - Вспомогательные функции

DATA_DIR = os.environ.get('DATA_DIR', '/app/data')
os.makedirs(DATA_DIR, exist_ok=True)

import discord
from datetime import datetime
import os
import json

# Файлы для хранения данных
STATES_FILE = 'states.json'
TRADES_FILE = 'trades.json'
ALLIANCES_FILE = 'alliances.json'
TRANSFERS_FILE = 'transfers.json'

# Цвет для эмбедов в тёмной теме Discord
DARK_THEME_COLOR = 0x2b2d31

def get_user_id(ctx):
    """Получить ID пользователя из контекста (команда или взаимодействие)"""
    if hasattr(ctx, 'author'):  # Это команда (ctx)
        return ctx.author.id
    else:  # Это взаимодействие (interaction)
        return ctx.user.id

def get_user_name(ctx):
    """Получить имя пользователя из контекста (команда или взаимодействие)"""
    if hasattr(ctx, 'author'):  # Это команда (ctx)
        return ctx.author.name
    else:  # Это взаимодействие (interaction)
        return ctx.user.name

async def send_response(ctx, content=None, embed=None, view=None, file=None, ephemeral=False):
    """Отправить ответ в зависимости от типа контекста"""
    if hasattr(ctx, 'author'):  # Это команда (ctx)
        if embed and file:
            await ctx.send(embed=embed, view=view, file=file)
        elif embed:
            await ctx.send(embed=embed, view=view)
        elif file:
            await ctx.send(content, view=view, file=file)
        else:
            await ctx.send(content, view=view)
    else:  # Это взаимодействие (interaction)
        try:
            if not ctx.response.is_done():
                if embed and file:
                    await ctx.response.send_message(embed=embed, view=view, file=file, ephemeral=ephemeral)
                elif embed:
                    await ctx.response.send_message(embed=embed, view=view, ephemeral=ephemeral)
                elif file:
                    await ctx.response.send_message(content, view=view, file=file, ephemeral=ephemeral)
                else:
                    await ctx.response.send_message(content, view=view, ephemeral=ephemeral)
            else:
                if embed and file:
                    await ctx.followup.send(embed=embed, view=view, file=file, ephemeral=ephemeral)
                elif embed:
                    await ctx.followup.send(embed=embed, view=view, ephemeral=ephemeral)
                elif file:
                    await ctx.followup.send(content, view=view, file=file, ephemeral=ephemeral)
                else:
                    await ctx.followup.send(content, view=view, ephemeral=ephemeral)
        except (discord.errors.NotFound, discord.errors.InteractionResponded) as e:
            try:
                if embed and file:
                    await ctx.followup.send(embed=embed, view=view, file=file, ephemeral=ephemeral)
                elif embed:
                    await ctx.followup.send(embed=embed, view=view, ephemeral=ephemeral)
                elif file:
                    await ctx.followup.send(content, view=view, file=file, ephemeral=ephemeral)
                else:
                    await ctx.followup.send(content, view=view, ephemeral=ephemeral)
            except:
                pass

async def edit_response(ctx, embed=None, view=None):
    """Редактировать сообщение в зависимости от типа контекста"""
    if hasattr(ctx, 'author'):  # Это команда (ctx) - нельзя редактировать, отправляем новое
        if embed:
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send(view=view)
    else:  # Это взаимодействие (interaction)
        try:
            await ctx.response.edit_message(embed=embed, view=view)
        except:
            try:
                await ctx.edit_original_response(embed=embed, view=view)
            except:
                pass

def format_number(value):
    """Форматирует число с разделителями"""
    return f"{value:,}".replace(',', ' ')

def format_army_number(value):
    """Форматирует число для армии с разделителями"""
    if value >= 1_000_000:
        millions = value / 1_000_000
        return f"{millions:.1f} млн"
    elif value >= 1_000:
        thousands = value / 1_000
        return f"{thousands:.1f} тыс"
    else:
        return str(value)

def format_billion(value):
    """
    Форматирует число в триллионах/миллиардах/миллионах
    ПРИМЕЧАНИЕ: value должно быть в ДОЛЛАРАХ
    Для инфраструктуры (значения в миллионах) используйте format_infra_cost
    """
    if value >= 1_000_000_000_000:
        trillions = value / 1_000_000_000_000
        return f"{trillions:,.2f}".replace(',', ' ') + " трлн $"
    elif value >= 1_000_000_000:
        billions = value / 1_000_000_000
        return f"{billions:,.2f}".replace(',', ' ') + " млрд $"
    elif value >= 1_000_000:
        millions = value / 1_000_000
        return f"{millions:,.2f}".replace(',', ' ') + " млн $"
    elif value >= 1_000:
        thousands = value / 1_000
        return f"{thousands:,.2f}".replace(',', ' ') + " тыс $"
    else:
        return f"{value:,} $".replace(',', ' ')

def format_infra_cost(cost_millions):
    """
    Специальное форматирование для стоимости инфраструктуры
    cost_millions - значение в МИЛЛИОНАХ долларов
    Пример: 500 -> "500 млн $", 1500 -> "1.5 млрд $"
    """
    if cost_millions >= 1000:
        billions = cost_millions / 1000
        return f"{billions:.1f} млрд $"
    else:
        return f"{cost_millions:.0f} млн $"

def format_research_cost(cost_millions):
    """
    Форматирование для стоимости исследований
    cost_millions - значение в МИЛЛИОНАХ долларов
    """
    if cost_millions >= 1000:
        billions = cost_millions / 1000
        return f"{billions:.1f} млрд $"
    else:
        return f"{cost_millions:.0f} млн $"

def format_time(seconds):
    """Форматирование времени"""
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

def create_embed(title, description=None, color=DARK_THEME_COLOR, fields=None, footer=None):
    """
    Универсальная функция для создания embed с тёмной темой
    """
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    
    if footer:
        embed.set_footer(text=footer)
    
    return embed

async def safe_delete(message):
    """Безопасное удаление сообщения (асинхронная функция)"""
    try:
        if message:
            await message.delete()
    except:
        pass

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_states():
    """Загрузка данных государств"""
    try:
        with open(STATES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"players": {}, "last_update": str(datetime.now())}
            return json.loads(content)
    except FileNotFoundError:
        return {"players": {}, "last_update": str(datetime.now())}
    except json.JSONDecodeError:
        return {"players": {}, "last_update": str(datetime.now())}

def save_states(data):
    """Сохранение данных государств"""
    filepath = os.path.join(DATA_DIR, 'states.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_trades():
    """Загрузка активных сделок"""
    try:
        with open(TRADES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_trades": [], "completed_trades": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"active_trades": [], "completed_trades": []}
    except json.JSONDecodeError:
        return {"active_trades": [], "completed_trades": []}

def save_trades(data):
    """Сохранение сделок"""
    with open(TRADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_alliances():
    """Загрузка альянсов"""
    try:
        with open(ALLIANCES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"alliances": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"alliances": []}
    except json.JSONDecodeError:
        return {"alliances": []}

def save_alliances(data):
    """Сохранение альянсов"""
    with open(ALLIANCES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_transfers():
    """Загрузка активных переводов"""
    try:
        with open(TRANSFERS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_transfers": [], "completed_transfers": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"active_transfers": [], "completed_transfers": []}
    except json.JSONDecodeError:
        return {"active_transfers": [], "completed_transfers": []}

def save_transfers(data):
    """Сохранение переводов"""
    with open(TRANSFERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ЭФЕМЕРНЫМИ СООБЩЕНИЯМИ ====================

async def send_ephemeral(interaction, embed=None, view=None, content=None):
    """Отправить эфемерное сообщение"""
    await interaction.response.send_message(
        content=content,
        embed=embed,
        view=view,
        ephemeral=True
    )

async def update_ephemeral(interaction, embed=None, view=None):
    """Обновить эфемерное сообщение"""
    try:
        await interaction.response.edit_message(embed=embed, view=view)
    except:
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except:
            pass

# Экспортируем все функции
__all__ = [
    'get_user_id', 'get_user_name', 'send_response', 'edit_response',
    'format_number', 'format_army_number', 'format_billion', 'format_time',
    'format_infra_cost', 'format_research_cost', 'create_embed', 'safe_delete',
    'send_ephemeral', 'update_ephemeral', 'DARK_THEME_COLOR',
    'load_states', 'save_states', 'load_trades', 'save_trades',
    'load_alliances', 'save_alliances', 'load_transfers', 'save_transfers'
]

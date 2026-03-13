# military_doctrines.py - Модуль для военных доктрин, появляющихся со временем
# Доктрины становятся доступны в определенные даты

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from political_power import spend_political_power, get_political_power
from game_time import get_current_game_time, get_year, get_month, get_game_date_formatted

# Файл для хранения данных о доктринах
DOCTRINES_FILE = 'military_doctrines.json'

# ID канала для публикации завершенных доктрин
DOCTRINE_LOG_CHANNEL_ID = 1263440933232578630

# ==================== БАЗА ДАННЫХ ДОКТРИН ====================

# Дата старта: 1 декабря 2022
# Доктрины становятся доступны с определенных дат

MILITARY_DOCTRINES = {
    "anti_drone_armor": {
        "name": "Анти-дроновая защита техники",
        "description": "Установка противодроновых защитных конструкций (мангалов, решёток, РЭБ) на бронетехнику.",
        "available_from": "2022-03-01",  # 1 марта 2022
        "requirements": {
            "steel": 25,
            "money": 10000000  # 10 млн $
        },
        "duration_hours": 72,
        "pp_cost": 15,
        "category": "defense",
        "image_url": "https://images-ext-1.discordapp.net/external/PuX4kACmHv6yuRAoykxtqqgEXxnoT-3HhOamrjTZjcY/https/flot2017.com/wp-content/uploads/2021/05/630_360_1572357882-410.jpg?format=webp&width=567&height=324"
    },
    
    "anti_drone_logistics": {
        "name": "Анти-дроновая защита логистики",
        "description": "Установка защитных сеток на дорогах и организация защиты колонн от дронов.",
        "available_from": "2024-01-01",  # 1 января 2024
        "requirements": {
            "money": 20000000  # 20 млн $
        },
        "duration_hours": 24,
        "pp_cost": 10,
        "category": "logistics",
        "image_url": "https://images-ext-1.discordapp.net/external/PuX4kACmHv6yuRAoykxtqqgEXxnoT-3HhOamrjTZjcY/https/flot2017.com/wp-content/uploads/2021/05/630_360_1572357882-410.jpg?format=webp&width=567&height=324"
    },
    
    "new_assault_tactics": {
        "name": "Новая тактика штурма",
        "description": "Штурмовые группы делают ставку на скрытность, а не на численность. Группа до 10 бойцов со спецснаряжением.",
        "available_from": "2023-06-01",  # 1 июня 2023
        "requirements": {
            "money": 2000000  # 2 млн $
        },
        "duration_hours": 12,
        "pp_cost": 8,
        "category": "tactics",
        "image_url": "https://images-ext-1.discordapp.net/external/PuX4kACmHv6yuRAoykxtqqgEXxnoT-3HhOamrjTZjcY/https/flot2017.com/wp-content/uploads/2021/05/630_360_1572357882-410.jpg?format=webp&width=567&height=324"
    },
    
    "shotgun_revival": {
        "name": "Новая жизнь дробовиков",
        "description": "Закупка дробовиков для эффективного отражения дронов на ближней дистанции.",
        "available_from": "2023-02-01",  # 1 февраля 2023
        "requirements": {
            "money": 25000000  # 25 млн $
        },
        "duration_hours": 16,
        "pp_cost": 10,
        "category": "equipment",
        "image_url": "https://images-ext-1.discordapp.net/external/PuX4kACmHv6yuRAoykxtqqgEXxnoT-3HhOamrjTZjcY/https/flot2017.com/wp-content/uploads/2021/05/630_360_1572357882-410.jpg?format=webp&width=567&height=324"
    },
    
    "modern_warfare_logistics": {
        "name": "Логистика в условиях современной войны",
        "description": "Реорганизация снабжения: использование скутеров, увеличенная нагрузка на пехотинцев.",
        "available_from": "2024-01-01",  # 1 января 2024
        "requirements": {
            "money": 5000000  # 5 млн $
        },
        "duration_hours": 24,
        "pp_cost": 8,
        "category": "logistics",
        "image_url": "https://images-ext-1.discordapp.net/external/PuX4kACmHv6yuRAoykxtqqgEXxnoT-3HhOamrjTZjcY/https/flot2017.com/wp-content/uploads/2021/05/630_360_1572357882-410.jpg?format=webp&width=567&height=324"
    },
    
    "fire_roll_tactics": {
        "name": "Огневой накат",
        "description": "Танки работают группами по 2: один ведёт огонь с укреплённой позиции, другой маневрирует.",
        "available_from": "2023-01-01",  # 1 января 2023
        "requirements": {
            "money": 0  # бесплатно
        },
        "duration_hours": 8,
        "pp_cost": 5,
        "category": "tactics",
        "image_url": "https://images-ext-1.discordapp.net/external/PuX4kACmHv6yuRAoykxtqqgEXxnoT-3HhOamrjTZjcY/https/flot2017.com/wp-content/uploads/2021/05/630_360_1572357882-410.jpg?format=webp&width=567&height=324"
    }
}

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_doctrines():
    """Загружает данные о военных доктринах"""
    try:
        with open(DOCTRINES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"researching": [], "completed": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"researching": [], "completed": []}

def save_doctrines(data):
    """Сохраняет данные о военных доктринах"""
    with open(DOCTRINES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==================== ПРОВЕРКА ДОСТУПНОСТИ ====================

def is_doctrine_available(doctrine_id: str) -> bool:
    """Проверяет, доступна ли доктрина по дате"""
    doctrine = MILITARY_DOCTRINES.get(doctrine_id)
    if not doctrine:
        return False
    
    available_from = datetime.strptime(doctrine["available_from"], "%Y-%m-%d")
    current_game_date, _ = get_current_game_time()
    
    return current_game_date >= available_from

def get_available_doctrines() -> List[str]:
    """Возвращает список ID доктрин, доступных по дате"""
    available = []
    for doctrine_id in MILITARY_DOCTRINES:
        if is_doctrine_available(doctrine_id):
            available.append(doctrine_id)
    return available

def can_research_doctrine(player_data, doctrine_id: str) -> Tuple[bool, str]:
    """
    Проверяет, может ли игрок начать исследование доктрины
    """
    doctrine = MILITARY_DOCTRINES.get(doctrine_id)
    if not doctrine:
        return False, "Доктрина не найдена"
    
    # Проверяем доступность по дате
    if not is_doctrine_available(doctrine_id):
        return False, f"Доктрина станет доступна с {doctrine['available_from']}"
    
    # Проверяем, не исследуется ли уже
    doctrines_data = load_doctrines()
    user_id = str(player_data.get("assigned_to", ""))
    
    for research in doctrines_data["researching"]:
        if research["user_id"] == user_id and research["doctrine_id"] == doctrine_id:
            return False, "Эта доктрина уже исследуется"
    
    # Проверяем, не изучена ли уже
    for completed in doctrines_data["completed"]:
        if completed["user_id"] == user_id and completed["doctrine_id"] == doctrine_id:
            return False, "Эта доктрина уже изучена"
    
    # Проверяем бюджет
    money_needed = doctrine["requirements"].get("money", 0)
    if player_data["economy"]["budget"] < money_needed:
        return False, f"Недостаточно средств! Нужно: {format_billion(money_needed)}"
    
    # Проверяем ресурсы
    steel_needed = doctrine["requirements"].get("steel", 0)
    if steel_needed > 0:
        resources = player_data.get("resources", {})
        if resources.get("steel", 0) < steel_needed:
            return False, f"Недостаточно стали! Нужно: {steel_needed}, есть: {resources.get('steel', 0)}"
    
    # Проверяем политическую власть
    current_pp = get_political_power(player_data)
    if current_pp < doctrine["pp_cost"]:
        return False, f"Недостаточно политической власти! Нужно: {doctrine['pp_cost']}, у вас: {current_pp:.1f}"
    
    return True, "OK"

def start_research(player_data, doctrine_id: str) -> bool:
    """
    Начинает исследование доктрины (списывает ресурсы)
    """
    doctrine = MILITARY_DOCTRINES[doctrine_id]
    
    # Списываем деньги
    money_needed = doctrine["requirements"].get("money", 0)
    if money_needed > 0:
        player_data["economy"]["budget"] -= money_needed
    
    # Списываем сталь
    steel_needed = doctrine["requirements"].get("steel", 0)
    if steel_needed > 0:
        player_data["resources"]["steel"] -= steel_needed
    
    # Списываем ПВ
    spend_political_power(player_data, doctrine["pp_cost"])
    
    # Добавляем в очередь исследований
    doctrines_data = load_doctrines()
    user_id = str(player_data.get("assigned_to", ""))
    
    completion_time = datetime.now() + timedelta(hours=doctrine["duration_hours"])
    
    doctrines_data["researching"].append({
        "user_id": user_id,
        "country": player_data["state"]["statename"],
        "doctrine_id": doctrine_id,
        "doctrine_name": doctrine["name"],
        "start_time": str(datetime.now()),
        "completion_time": str(completion_time),
        "notified": False
    })
    
    save_doctrines(doctrines_data)
    return True

# ==================== ФОНОВАЯ ЗАДАЧА ДЛЯ ЗАВЕРШЕНИЯ ====================

async def doctrines_completion_loop(bot_instance):
    """Фоновая задача для проверки завершения исследования доктрин"""
    await bot_instance.wait_until_ready()
    
    while not bot_instance.is_closed():
        try:
            doctrines_data = load_doctrines()
            states = load_states()
            now = datetime.now()
            
            completed = []
            
            for research in doctrines_data["researching"][:]:
                completion = datetime.fromisoformat(research["completion_time"])
                
                if completion <= now and not research.get("notified", False):
                    # Находим игрока
                    player_data = None
                    for data in states["players"].values():
                        if data.get("assigned_to") == research["user_id"]:
                            player_data = data
                            break
                    
                    if player_data:
                        # Добавляем в завершенные
                        research["status"] = "completed"
                        research["completed_at"] = str(now)
                        doctrines_data["completed"].append(research)
                        doctrines_data["researching"].remove(research)
                        completed.append(research)
                        
                        # Отправляем сообщение в канал
                        try:
                            channel = bot_instance.get_channel(DOCTRINE_LOG_CHANNEL_ID)
                            if channel:
                                doctrine = MILITARY_DOCTRINES.get(research["doctrine_id"])
                                if doctrine:
                                    embed = discord.Embed(
                                        title="Военная инициатива внедрена",
                                        description=f"Армия государства {research['country']} завершила внедрение военной инициативы {doctrine['name']} в вооружённые силы.",
                                        color=DARK_THEME_COLOR
                                    )
                                    embed.set_image(url=doctrine["image_url"])
                                    await channel.send(embed=embed)
                        except Exception as e:
                            print(f"Ошибка при отправке в канал: {e}")
                        
                        # Уведомляем игрока в ЛС
                        try:
                            user = await bot_instance.fetch_user(int(research["user_id"]))
                            if user:
                                doctrine = MILITARY_DOCTRINES.get(research["doctrine_id"])
                                embed = discord.Embed(
                                    title="Военная доктрина изучена",
                                    description=f"Доктрина **{doctrine['name']}** успешно внедрена в армию.",
                                    color=DARK_THEME_COLOR
                                )
                                await user.send(embed=embed)
                        except:
                            pass
                    
                    research["notified"] = True
            
            if completed:
                save_doctrines(doctrines_data)
                save_states(states)
                print(f"✅ Завершено {len(completed)} военных доктрин")
            
            await asyncio.sleep(60)  # Проверка каждую минуту
            
        except Exception as e:
            print(f"❌ Ошибка в doctrines_completion_loop: {e}")
            await asyncio.sleep(60)

# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class DoctrineSelect(Select):
    """Выбор доктрины для изучения"""
    
    def __init__(self, user_id, player_data, available_doctrines, original_message):
        self.user_id = user_id
        self.player_data = player_data
        self.available_doctrines = available_doctrines
        self.original_message = original_message
        
        options = []
        for doctrine_id in available_doctrines:
            doctrine = MILITARY_DOCTRINES[doctrine_id]
            options.append(
                discord.SelectOption(
                    label=doctrine['name'],
                    description=doctrine['description'][:50],
                    value=doctrine_id
                )
            )
        
        super().__init__(
            placeholder="Выберите военную инициативу...",
            min_values=1,
            max_values=1,
            options=options[:25]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        doctrine_id = self.values[0]
        doctrine = MILITARY_DOCTRINES[doctrine_id]
        
        embed = discord.Embed(
            title=doctrine['name'],
            description=doctrine['description'],
            color=DARK_THEME_COLOR
        )
        
        # Требования
        req_text = ""
        if doctrine["requirements"].get("money", 0) > 0:
            req_text += f"• Деньги: {format_billion(doctrine['requirements']['money'])}\n"
        if doctrine["requirements"].get("steel", 0) > 0:
            req_text += f"• Сталь: {doctrine['requirements']['steel']} ед.\n"
        req_text += f"• Полит. власть: {doctrine['pp_cost']}\n"
        req_text += f"• Время: {doctrine['duration_hours']} часов"
        
        embed.add_field(name="Требования", value=req_text, inline=False)
        
        # Информация о доступности
        if not is_doctrine_available(doctrine_id):
            embed.add_field(name="Статус", value=f"❌ Станет доступна с {doctrine['available_from']}", inline=False)
        else:
            embed.add_field(name="Статус", value="✅ Доступна сейчас", inline=False)
        
        view = DoctrineConfirmationView(self.user_id, self.player_data, doctrine_id)
        
        await interaction.response.edit_message(embed=embed, view=view)


class DoctrineConfirmationView(View):
    """Подтверждение начала изучения доктрины"""
    
    def __init__(self, user_id, player_data, doctrine_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
        self.doctrine_id = doctrine_id
    
    @discord.ui.button(label="Начать внедрение", style=discord.ButtonStyle.secondary)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверяем возможность
        can_research, message = can_research_doctrine(self.player_data, self.doctrine_id)
        if not can_research:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Начинаем исследование
        success = start_research(self.player_data, self.doctrine_id)
        
        if not success:
            await interaction.response.send_message("❌ Ошибка при начале исследования!", ephemeral=True)
            return
        
        # Сохраняем изменения
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                data.update(self.player_data)
                break
        save_states(states)
        
        doctrine = MILITARY_DOCTRINES[self.doctrine_id]
        
        embed = discord.Embed(
            title="Внедрение начато",
            description=f"Военная инициатива {doctrine['name']} запущена в разработку.\nВремя завершения: {doctrine['duration_hours']} часов.",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Действие отменено",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ОСНОВНОЕ МЕНЮ ====================

async def show_doctrines_menu(ctx, user_id: int):
    """Показать меню военных доктрин"""
    
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
    
    country_name = player_data["state"]["statename"]
    current_pp = get_political_power(player_data)
    
    # Получаем доступные доктрины
    all_available = get_available_doctrines()
    
    # Фильтруем те, что еще не изучены и не в процессе
    doctrines_data = load_doctrines()
    user_id_str = str(user_id)
    
    researching_ids = [r["doctrine_id"] for r in doctrines_data["researching"] if r["user_id"] == user_id_str]
    completed_ids = [c["doctrine_id"] for c in doctrines_data["completed"] if c["user_id"] == user_id_str]
    
    available_doctrines = [d for d in all_available if d not in researching_ids and d not in completed_ids]
    
    # Текущие исследования
    researching = [r for r in doctrines_data["researching"] if r["user_id"] == user_id_str]
    
    embed = discord.Embed(
        title="Военные доктрины",
        description="Внедрение новых тактик и технологий в армию",
        color=DARK_THEME_COLOR
    )
    
    # Информация о текущих исследованиях
    if researching:
        research_text = ""
        now = datetime.now()
        for r in researching:
            completion = datetime.fromisoformat(r["completion_time"])
            remaining = (completion - now).total_seconds()
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            
            research_text += f"• {r['doctrine_name']}: {hours}ч {minutes}м осталось\n"
        embed.add_field(name="Внедряется", value=research_text, inline=False)
    
    # Завершенные
    completed = [c for c in doctrines_data["completed"] if c["user_id"] == user_id_str]
    if completed:
        completed_text = ""
        for c in completed[-3:]:  # последние 3
            completed_text += f"• {c['doctrine_name']}\n"
        embed.add_field(name="Завершено", value=completed_text, inline=False)
    
    embed.add_field(
        name="Политическая власть",
        value=f"{current_pp:.1f} ПВ",
        inline=True
    )
    
    embed.add_field(
        name="Доступно инициатив",
        value=str(len(available_doctrines)),
        inline=True
    )
    
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, ephemeral=True)
        message = await ctx.original_response()
    else:
        message = await ctx.send(embed=embed, ephemeral=True)
    
    if available_doctrines:
        select = DoctrineSelect(user_id, player_data, available_doctrines, message)
        view = View(timeout=120)
        view.add_item(select)
        await message.edit(view=view)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_doctrines_menu',
    'doctrines_completion_loop',
    'MILITARY_DOCTRINES'
]

# national_focus.py - Модуль для национальных фокусов (как в Hearts of Iron)

import discord
from discord.ui import Button, View, Select, Modal
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math
import re

from utils import format_billion, format_number, load_states, save_states, DARK_THEME_COLOR
from paths import get_data_path
from political_power import get_political_power, spend_political_power

# Файлы для хранения данных
NATIONAL_FOCUS_FILE = get_data_path('national_focus.json')
ACTIVE_FOCUSES_FILE = get_data_path('active_focuses.json')

# ==================== ЗАГРУЗКА БАЗЫ ФОКУСОВ ====================

def load_focuses_db():
    """Загружает базу данных национальных фокусов"""
    try:
        with open(NATIONAL_FOCUS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("⚠️ Файл national_focus.json не найден")
        return {"focuses": {}}
    except json.JSONDecodeError:
        print("❌ Ошибка в формате national_focus.json")
        return {"focuses": {}}

FOCUSES_DB = load_focuses_db()

# ==================== ЗАГРУЗКА/СОХРАНЕНИЕ АКТИВНЫХ ФОКУСОВ ====================

def load_active_focuses():
    """Загружает данные об активных фокусах"""
    try:
        with open(ACTIVE_FOCUSES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active": [], "completed": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"active": [], "completed": []}
    except json.JSONDecodeError:
        return {"active": [], "completed": []}

def save_active_focuses(data):
    """Сохраняет данные об активных фокусах"""
    with open(ACTIVE_FOCUSES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ФОКУСАМИ ====================

def get_country_focuses(country_name: str) -> List[Dict]:
    """Возвращает список всех фокусов страны"""
    return FOCUSES_DB.get("focuses", {}).get(country_name, [])

def get_available_focuses(country_name: str, completed_focuses: List[str]) -> List[Dict]:
    """
    Возвращает список доступных для изучения фокусов
    (все требования выполнены и ещё не завершены)
    """
    all_focuses = get_country_focuses(country_name)
    available = []
    
    for focus in all_focuses:
        focus_id = focus["id"]
        
        # Пропускаем уже завершённые
        if focus_id in completed_focuses:
            continue
        
        # Проверяем требования
        prerequisites_met = True
        for prereq in focus.get("prerequisites", []):
            if prereq not in completed_focuses:
                prerequisites_met = False
                break
        
        if prerequisites_met:
            available.append(focus)
    
    return available

def parse_budget_cost(cost_value) -> float:
    """
    Преобразует стоимость бюджета в число (в долларах)
    Поддерживает строки вида "50 млн $" или числа
    """
    if isinstance(cost_value, (int, float)):
        return float(cost_value)
    
    if not isinstance(cost_value, str):
        return 0
    
    # Ищем числа в строке
    numbers = re.findall(r'[\d.]+', cost_value)
    if not numbers:
        return 0
    
    value = float(numbers[0])
    
    # Учитываем единицы измерения
    if "млрд" in cost_value:
        return value * 1_000_000_000
    elif "млн" in cost_value:
        return value * 1_000_000
    elif "тыс" in cost_value:
        return value * 1_000
    else:
        return value

def format_budget_cost(cost_value) -> str:
    """Форматирует стоимость бюджета для отображения"""
    if isinstance(cost_value, str):
        return cost_value
    
    if isinstance(cost_value, (int, float)):
        return format_billion(cost_value)
    
    return "0 $"

def can_start_focus(player_data: Dict, focus: Dict) -> Tuple[bool, str]:
    """
    Проверяет, может ли игрок начать фокус
    """
    # Проверяем политическую власть
    current_pp = get_political_power(player_data)
    if current_pp < focus["cost"]:
        return False, f"Недостаточно политической власти! Нужно: {focus['cost']}, у вас: {current_pp:.1f}"
    
    # Проверяем бюджет (если есть затраты)
    budget_cost_value = parse_budget_cost(focus.get("effects", {}).get("budget_cost", 0))
    if budget_cost_value > 0 and player_data["economy"]["budget"] < budget_cost_value:
        return False, f"Недостаточно средств! Нужно: {format_budget_cost(focus.get('effects', {}).get('budget_cost', 0))}"
    
    return True, "OK"

def start_focus(player_data: Dict, focus: Dict, user_id: str, country_name: str) -> Dict:
    """
    Начинает выполнение фокуса
    """
    # Списываем политическую власть
    spend_political_power(player_data, focus["cost"])
    
    # Списываем деньги (если есть)
    budget_cost_value = parse_budget_cost(focus.get("effects", {}).get("budget_cost", 0))
    if budget_cost_value > 0:
        player_data["economy"]["budget"] -= budget_cost_value
    
    # Рассчитываем время завершения
    duration_days = focus.get("duration_days", 2)
    completion_time = datetime.now() + timedelta(days=duration_days)
    
    # Создаём запись об активном фокусе
    focus_entry = {
        "id": focus["id"],
        "name": focus["name"],
        "country": country_name,
        "user_id": user_id,
        "start_time": str(datetime.now()),
        "completion_time": str(completion_time),
        "duration_days": duration_days,
        "effects": focus.get("effects", {}),
        "budget_cost_display": focus.get("effects", {}).get("budget_cost", 0),
        "budget_cost_value": budget_cost_value,
        "notified": False
    }
    
    return focus_entry

def apply_focus_effects(player_data: Dict, effects: Dict):
    """
    Применяет эффекты завершённого фокуса
    """
    for effect, value in effects.items():
        if effect == "budget_cost":
            continue
            
        if effect == "inflation":
            current = player_data["economy"].get("inflation", 0)
            # Если value строка с процентом, извлекаем число
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0])
                    if "-" in value:
                        player_data["economy"]["inflation"] = max(0, current - change)
                    else:
                        player_data["economy"]["inflation"] = current + change
            else:
                player_data["economy"]["inflation"] = max(0, current + value)
        
        elif effect == "research_speed":
            if "bonuses" not in player_data:
                player_data["bonuses"] = {}
            current = player_data["bonuses"].get("research_speed", 1.0)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0]) / 100
                    player_data["bonuses"]["research_speed"] = current + change
            else:
                player_data["bonuses"]["research_speed"] = current + value / 100
        
        elif effect == "government_efficiency":
            current = player_data.get("government_efficiency", 50)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0])
                    player_data["government_efficiency"] = min(100, max(0, current + change))
            else:
                player_data["government_efficiency"] = min(100, max(0, current + value))
        
        elif effect == "stability":
            current = player_data["state"].get("stability", 50)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0])
                    player_data["state"]["stability"] = min(100, max(0, current + change))
            else:
                player_data["state"]["stability"] = min(100, max(0, current + value))
        
        elif effect == "happiness":
            current = player_data["state"].get("happiness", 50)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0])
                    player_data["state"]["happiness"] = min(100, max(0, current + change))
            else:
                player_data["state"]["happiness"] = min(100, max(0, current + value))
        
        elif effect == "political_power_gain":
            if "politics" not in player_data:
                player_data["politics"] = {}
            current = player_data["politics"].get("political_power_gain", 2.0)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0])
                    player_data["politics"]["political_power_gain"] = current + change
            else:
                player_data["politics"]["political_power_gain"] = current + value
        
        elif effect == "corruption":
            if "_temp_effects" not in player_data:
                player_data["_temp_effects"] = []
            player_data["_temp_effects"].append({
                "type": "corruption",
                "value": value,
                "source": "focus"
            })
        
        elif effect == "military_budget":
            current = player_data["economy"].get("military_budget", 0)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0]) / 100
                    player_data["economy"]["military_budget"] = current * (1 + change)
            else:
                player_data["economy"]["military_budget"] = current * (1 + value / 100)
        
        elif effect == "army_readiness":
            current = player_data["state"].get("readiness", 50)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0])
                    player_data["state"]["readiness"] = min(100, max(0, current + change))
            else:
                player_data["state"]["readiness"] = min(100, max(0, current + value))
        
        elif effect == "infrastructure_boost":
            if "bonuses" not in player_data:
                player_data["bonuses"] = {}
            current = player_data["bonuses"].get("infrastructure", 1.0)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0]) / 100
                    player_data["bonuses"]["infrastructure"] = current + change
            else:
                player_data["bonuses"]["infrastructure"] = current + value / 100
        
        elif effect == "trade_income":
            if "bonuses" not in player_data:
                player_data["bonuses"] = {}
            current = player_data["bonuses"].get("trade_income", 1.0)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0]) / 100
                    player_data["bonuses"]["trade_income"] = current + change
            else:
                player_data["bonuses"]["trade_income"] = current + value / 100
        
        elif effect in ["relations_china", "relations_usa", "relations_eu", 
                        "relations_russia", "relations_uk", "relations_france",
                        "relations_germany", "relations_japan", "relations_india"]:
            if "diplomacy" not in player_data:
                player_data["diplomacy"] = {}
            current = player_data["diplomacy"].get(effect, 0)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0])
                    player_data["diplomacy"][effect] = current + change
            else:
                player_data["diplomacy"][effect] = current + value
        
        elif effect in ["nuclear_deterrence", "military_prestige", "air_force_capability",
                        "navy_strength", "army_readiness"]:
            if "military_stats" not in player_data:
                player_data["military_stats"] = {}
            current = player_data["military_stats"].get(effect, 0)
            if isinstance(value, str):
                num = re.findall(r'[\d.]+', value)
                if num:
                    change = float(num[0])
                    player_data["military_stats"][effect] = current + change
            else:
                player_data["military_stats"][effect] = current + value

# ==================== ФОНОВАЯ ЗАДАЧА ====================

async def focuses_update_loop(bot_instance):
    """Фоновая задача для проверки завершения фокусов"""
    await bot_instance.wait_until_ready()
    
    while not bot_instance.is_closed():
        try:
            active_focuses = load_active_focuses()
            states = load_states()
            now = datetime.now()
            
            completed = []
            
            for focus in active_focuses["active"][:]:
                completion = datetime.fromisoformat(focus["completion_time"])
                
                if completion <= now and not focus.get("notified", False):
                    # Находим игрока
                    player_data = None
                    for data in states["players"].values():
                        if data.get("assigned_to") == focus["user_id"]:
                            player_data = data
                            break
                    
                    if player_data:
                        # Применяем эффекты
                        apply_focus_effects(player_data, focus["effects"])
                        
                        # Добавляем в завершённые
                        focus["status"] = "completed"
                        focus["completed_at"] = str(now)
                        active_focuses["completed"].append(focus)
                        active_focuses["active"].remove(focus)
                        completed.append(focus)
                        
                        # Отправляем уведомление
                        try:
                            user = await bot_instance.fetch_user(int(focus["user_id"]))
                            if user:
                                embed = discord.Embed(
                                    title="✅ Национальный фокус завершён!",
                                    description=f"**{focus['name']}** успешно реализован",
                                    color=discord.Color.green()
                                )
                                
                                # Показываем эффекты
                                effects_text = ""
                                for effect, value in list(focus["effects"].items())[:5]:
                                    if effect == "budget_cost":
                                        continue
                                    effects_text += f"• {effect}: {value}\n"
                                
                                if effects_text:
                                    embed.add_field(name="Эффекты", value=effects_text, inline=False)
                                
                                await user.send(embed=embed)
                        except:
                            pass
                    
                    focus["notified"] = True
            
            if completed:
                save_states(states)
                save_active_focuses(active_focuses)
                print(f"✅ Завершено {len(completed)} национальных фокусов")
            
            await asyncio.sleep(3600)  # Проверка каждый час
            
        except Exception as e:
            print(f"❌ Ошибка в focuses_update_loop: {e}")
            await asyncio.sleep(3600)

# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class FocusTreeView(View):
    """Главное меню дерева фокусов"""
    
    def __init__(self, user_id: int, country_name: str, player_data: Dict, 
                 available_focuses: List[Dict], active_focuses: List[Dict], 
                 completed_focuses: List[Dict]):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.available_focuses = available_focuses
        self.active_focuses = active_focuses
        self.completed_focuses = completed_focuses
    
    @discord.ui.button(label="Доступные фокусы", style=discord.ButtonStyle.secondary)
    async def available_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        if not self.available_focuses:
            embed = discord.Embed(
                title="Доступные фокусы",
                description="Нет доступных фокусов. Завершите текущие, чтобы открыть новые.",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        # Группируем по категориям
        categories = {}
        for focus in self.available_focuses:
            cat = focus.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(focus)
        
        embed = discord.Embed(
            title=f"Национальные фокусы: {self.country_name}",
            description="Выберите фокус для изучения:",
            color=DARK_THEME_COLOR
        )
        
        for cat, focuses in categories.items():
            cat_names = {
                "economic": "Экономика",
                "military": "Военные",
                "political": "Политика",
                "social": "Социальные",
                "infrastructure": "Инфраструктура",
                "energy": "Энергетика",
                "technology": "Технологии",
                "foreign": "Внешняя политика",
                "environment": "Экология",
                "other": "Прочее"
            }
            cat_name = cat_names.get(cat, cat)
            
            focus_list = ""
            for focus in focuses[:3]:
                focus_list += f"• {focus['name']} ({focus['cost']} ПВ)\n"
            if len(focuses) > 3:
                focus_list += f"  и ещё {len(focuses)-3}..."
            
            embed.add_field(name=cat_name, value=focus_list, inline=False)
        
        # Создаём select для выбора фокуса
        select = FocusSelect(self.user_id, self.country_name, self.player_data, 
                           self.available_focuses, self.active_focuses)
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад к обзору", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Текущий фокус", style=discord.ButtonStyle.secondary)
    async def current_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        if not self.active_focuses:
            embed = discord.Embed(
                title="Текущий фокус",
                description="Нет активных фокусов. Выберите новый в разделе 'Доступные фокусы'.",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        # Показываем первый активный фокус (обычно только один)
        focus = self.active_focuses[0]
        
        now = datetime.now()
        completion = datetime.fromisoformat(focus["completion_time"])
        remaining = (completion - now).total_seconds()
        
        if remaining > 0:
            days = int(remaining // 86400)
            hours = int((remaining % 86400) // 3600)
            if days > 0:
                time_str = f"{days} дн {hours} ч"
            else:
                time_str = f"{hours} ч"
            
            # Прогресс-бар
            total = (completion - datetime.fromisoformat(focus["start_time"])).total_seconds()
            progress = 100 - (remaining / total * 100)
            bar_length = 20
            filled = int(progress / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            
            progress_str = f"{bar} {progress:.1f}%"
        else:
            time_str = "Завершается..."
            progress_str = "✅ ГОТОВО"
        
        embed = discord.Embed(
            title=f"Текущий фокус: {focus['name']}",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Осталось", value=time_str, inline=True)
        embed.add_field(name="Прогресс", value=progress_str, inline=False)
        
        # Эффекты
        if focus.get("effects"):
            effects_text = ""
            for effect, value in list(focus["effects"].items())[:5]:
                if effect == "budget_cost":
                    continue
                effects_text += f"• {effect}: {value}\n"
            if effects_text:
                embed.add_field(name="Эффекты при завершении", value=effects_text, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Завершённые", style=discord.ButtonStyle.secondary)
    async def completed_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        if not self.completed_focuses:
            embed = discord.Embed(
                title="Завершённые фокусы",
                description="У вас пока нет завершённых фокусов.",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        embed = discord.Embed(
            title=f"Завершённые фокусы: {self.country_name}",
            description=f"Всего завершено: {len(self.completed_focuses)}",
            color=DARK_THEME_COLOR
        )
        
        # Группируем по категориям
        categories = {}
        for focus in self.completed_focuses[-10:]:  # Последние 10
            cat = focus.get("category", "other")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(focus["name"])
        
        for cat, focuses in categories.items():
            cat_names = {
                "economic": "Экономика",
                "military": "Военные",
                "political": "Политика",
                "social": "Социальные",
                "infrastructure": "Инфраструктура",
                "energy": "Энергетика",
                "technology": "Технологии",
                "foreign": "Внешняя политика",
                "environment": "Экология",
                "other": "Прочее"
            }
            cat_name = cat_names.get(cat, cat)
            
            embed.add_field(name=cat_name, value="\n".join(focuses[:5]), inline=False)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def back_to_main(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_focus_menu(interaction, self.user_id)


class FocusSelect(Select):
    """Выбор конкретного фокуса"""
    
    def __init__(self, user_id: int, country_name: str, player_data: Dict,
                 available_focuses: List[Dict], active_focuses: List[Dict]):
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.active_focuses = active_focuses
        
        options = []
        for focus in available_focuses[:25]:
            # Проверяем, доступен ли фокус по ресурсам
            can_start, _ = can_start_focus(player_data, focus)
            
            options.append(
                discord.SelectOption(
                    label=focus["name"],
                    description=f"{focus.get('category', 'other')} | {focus['cost']} ПВ",
                    value=focus["id"]
                )
            )
        
        super().__init__(
            placeholder="Выберите фокус для изучения...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        focus_id = self.values[0]
        
        # Находим фокус в базе
        all_focuses = get_country_focuses(self.country_name)
        focus = next((f for f in all_focuses if f["id"] == focus_id), None)
        
        if not focus:
            await interaction.response.send_message("❌ Фокус не найден!", ephemeral=True)
            return
        
        # Проверяем, нет ли уже активного фокуса
        if self.active_focuses:
            await interaction.response.send_message(
                "❌ У вас уже есть активный фокус! Завершите его, прежде чем начинать новый.",
                ephemeral=True
            )
            return
        
        # Проверяем возможность начала
        can_start, message = can_start_focus(self.player_data, focus)
        if not can_start:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Показываем подтверждение
        embed = discord.Embed(
            title=focus['name'],
            description=focus.get("description", "Нет описания"),
            color=DARK_THEME_COLOR
        )
        
        # Требования
        req_text = f"• Политическая власть: {focus['cost']}\n"
        budget_cost = focus.get("effects", {}).get("budget_cost", 0)
        if budget_cost:
            req_text += f"• Бюджет: {format_budget_cost(budget_cost)}\n"
        req_text += f"• Длительность: {focus.get('duration_days', 2)} дней"
        embed.add_field(name="Требования", value=req_text, inline=False)
        
        # Эффекты
        effects = focus.get("effects", {})
        if effects:
            effects_text = ""
            for effect, value in effects.items():
                if effect == "budget_cost":
                    continue
                effects_text += f"• {effect}: {value}\n"
            embed.add_field(name="Эффекты", value=effects_text, inline=False)
        
        view = FocusConfirmView(self.user_id, self.country_name, self.player_data, focus)
        await interaction.response.edit_message(embed=embed, view=view)


class FocusConfirmView(View):
    """Подтверждение начала фокуса"""
    
    def __init__(self, user_id: int, country_name: str, player_data: Dict, focus: Dict):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.country_name = country_name
        self.player_data = player_data
        self.focus = focus
    
    @discord.ui.button(label="Начать фокус", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Ещё раз проверяем возможность
        can_start, message = can_start_focus(self.player_data, self.focus)
        if not can_start:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Проверяем активные фокусы
        active_focuses = load_active_focuses()
        user_active = [f for f in active_focuses["active"] if f["user_id"] == str(self.user_id)]
        if user_active:
            await interaction.response.send_message(
                "❌ У вас уже есть активный фокус! Завершите его, прежде чем начинать новый.",
                ephemeral=True
            )
            return
        
        # Начинаем фокус
        focus_entry = start_focus(
            self.player_data, self.focus, 
            str(self.user_id), self.country_name
        )
        
        # Сохраняем
        active_focuses["active"].append(focus_entry)
        save_active_focuses(active_focuses)
        
        # Сохраняем изменения в данных игрока
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                data.update(self.player_data)
                break
        save_states(states)
        
        embed = discord.Embed(
            title="✅ Фокус начат!",
            description=f"**{self.focus['name']}**",
            color=discord.Color.green()
        )
        
        completion = datetime.fromisoformat(focus_entry["completion_time"])
        embed.add_field(
            name="Завершение",
            value=f"{completion.strftime('%d.%m.%Y')} (через {self.focus.get('duration_days', 2)} дней)",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_focus_menu(interaction, self.user_id)


# ==================== ОСНОВНОЕ МЕНЮ ====================

async def show_focus_menu(interaction_or_ctx, user_id: int):
    """Показать меню национальных фокусов"""
    
    states = load_states()
    
    player_data = None
    country_name = None
    
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            player_data = data
            country_name = data["state"]["statename"]
            break
    
    if not player_data:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message("❌ У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("❌ У вас нет государства!")
        return
    
    # Загружаем активные и завершённые фокусы
    active_focuses_data = load_active_focuses()
    user_active = [f for f in active_focuses_data["active"] if f["user_id"] == str(user_id)]
    user_completed = [f for f in active_focuses_data["completed"] if f["user_id"] == str(user_id)]
    
    completed_ids = [f["id"] for f in user_completed]
    
    # Получаем доступные фокусы
    available_focuses = get_available_focuses(country_name, completed_ids)
    
    # Текущая политическая власть
    current_pp = get_political_power(player_data)
    
    embed = discord.Embed(
        title=f"Национальные фокусы: {country_name}",
        description="Стратегические направления развития страны",
        color=DARK_THEME_COLOR
    )
    
    # Статистика
    embed.add_field(name="Полит. власть", value=f"{current_pp:.1f}", inline=True)
    embed.add_field(name="Доступно фокусов", value=str(len(available_focuses)), inline=True)
    embed.add_field(name="Завершено", value=str(len(user_completed)), inline=True)
    
    # Текущий фокус
    if user_active:
        focus = user_active[0]
        completion = datetime.fromisoformat(focus["completion_time"])
        remaining = (completion - datetime.now()).days
        embed.add_field(
            name="Текущий фокус",
            value=f"{focus['name']}\nОсталось: {remaining} дней",
            inline=False
        )
    
    # Категории с кратким описанием
    categories_text = ""
    cat_counts = {}
    for focus in available_focuses:
        cat = focus.get("category", "other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    
    cat_names = {
        "economic": "Экономика",
        "military": "Военные",
        "political": "Политика",
        "social": "Социальные",
        "infrastructure": "Инфраструктура",
        "energy": "Энергетика",
        "technology": "Технологии",
        "foreign": "Внешняя политика",
        "environment": "Экология"
    }
    
    for cat, count in cat_counts.items():
        name = cat_names.get(cat, cat)
        categories_text += f"{name}: {count} | "
    
    embed.add_field(name="Доступные категории", value=categories_text or "Нет", inline=False)
    
    # Отправляем меню
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
        message = await interaction_or_ctx.original_response()
    else:
        message = await interaction_or_ctx.send(embed=embed, ephemeral=True)
    
    view = FocusTreeView(
        user_id, country_name, player_data,
        available_focuses, user_active, user_completed
    )
    await message.edit(view=view)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_focus_menu',
    'focuses_update_loop',
    'get_country_focuses',
    'get_available_focuses'
]

# conflicts.py - Модуль для управления военными конфликтами

import discord
from discord.ui import Button, View, Select, Modal
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from utils import load_states, save_states, DARK_THEME_COLOR

# Файл для хранения данных о конфликтах
CONFLICTS_FILE = 'conflicts.json'

# ==================== КЛАССЫ ДЛЯ РАБОТЫ С КОНФЛИКТАМИ ====================

class Conflict:
    """Класс, представляющий военный конфликт между странами"""
    
    def __init__(self, conflict_id: str, country1: str, country2: str, 
                 started_at: str, reason: str = "", conflict_type: str = "war"):
        self.id = conflict_id
        self.country1 = country1
        self.country2 = country2
        self.started_at = started_at
        self.reason = reason
        self.conflict_type = conflict_type  # war, proxy_war, border_conflict, ceasefire
        self.status = "active"  # active, ceasefire, ended
        self.ceasefire_until = None
        self.ended_at = None
        self.strikes_count = {country1: 0, country2: 0}
        self.damage_inflicted = {country1: 0, country2: 0}
        self.last_update = str(datetime.now())
    
    def to_dict(self) -> Dict:
        """Конвертирует объект в словарь для сохранения"""
        return {
            "id": self.id,
            "country1": self.country1,
            "country2": self.country2,
            "started_at": self.started_at,
            "reason": self.reason,
            "conflict_type": self.conflict_type,
            "status": self.status,
            "ceasefire_until": self.ceasefire_until,
            "ended_at": self.ended_at,
            "strikes_count": self.strikes_count,
            "damage_inflicted": self.damage_inflicted,
            "last_update": self.last_update
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Создаёт объект из словаря"""
        conflict = cls(
            data["id"], data["country1"], data["country2"],
            data["started_at"], data.get("reason", ""), data.get("conflict_type", "war")
        )
        conflict.status = data.get("status", "active")
        conflict.ceasefire_until = data.get("ceasefire_until")
        conflict.ended_at = data.get("ended_at")
        conflict.strikes_count = data.get("strikes_count", {data["country1"]: 0, data["country2"]: 0})
        conflict.damage_inflicted = data.get("damage_inflicted", {data["country1"]: 0, data["country2"]: 0})
        conflict.last_update = data.get("last_update", str(datetime.now()))
        return conflict


# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_conflicts() -> Dict:
    """Загрузка данных о конфликтах"""
    try:
        with open(CONFLICTS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"conflicts": [], "history": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"conflicts": [], "history": []}
    except json.JSONDecodeError:
        return {"conflicts": [], "history": []}

def save_conflicts(data: Dict):
    """Сохранение данных о конфликтах"""
    with open(CONFLICTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_active_conflicts() -> List[Conflict]:
    """Возвращает список активных конфликтов"""
    data = load_conflicts()
    conflicts = []
    for c_data in data["conflicts"]:
        conflict = Conflict.from_dict(c_data)
        if conflict.status == "active":
            conflicts.append(conflict)
    return conflicts

def get_conflicts_for_country(country_name: str) -> List[Conflict]:
    """Возвращает список конфликтов, в которых участвует страна"""
    data = load_conflicts()
    conflicts = []
    for c_data in data["conflicts"]:
        conflict = Conflict.from_dict(c_data)
        if (conflict.country1 == country_name or conflict.country2 == country_name) and conflict.status == "active":
            conflicts.append(conflict)
    return conflicts

def are_countries_at_war(country1: str, country2: str) -> bool:
    """Проверяет, находятся ли две страны в состоянии войны"""
    conflicts = get_active_conflicts()
    for conflict in conflicts:
        if (conflict.country1 == country1 and conflict.country2 == country2) or \
           (conflict.country1 == country2 and conflict.country2 == country1):
            return True
    return False

def get_countries_at_war_with(country_name: str) -> List[str]:
    """Возвращает список стран, с которыми данная страна находится в состоянии войны"""
    enemies = []
    conflicts = get_active_conflicts()
    for conflict in conflicts:
        if conflict.country1 == country_name:
            enemies.append(conflict.country2)
        elif conflict.country2 == country_name:
            enemies.append(conflict.country1)
    return enemies

def start_conflict(country1: str, country2: str, reason: str = "", 
                   conflict_type: str = "war") -> Optional[Conflict]:
    """
    Начинает конфликт между двумя странами
    """
    # Проверяем, не воюют ли уже
    if are_countries_at_war(country1, country2):
        return None
    
    # Создаём новый конфликт
    conflict_id = f"conflict_{datetime.now().strftime('%Y%m%d%H%M%S')}_{country1}_{country2}"
    conflict = Conflict(
        conflict_id, country1, country2, 
        str(datetime.now()), reason, conflict_type
    )
    
    # Сохраняем
    data = load_conflicts()
    data["conflicts"].append(conflict.to_dict())
    save_conflicts(data)
    
    return conflict

def end_conflict(country1: str, country2: str) -> bool:
    """Завершает конфликт между двумя странами"""
    data = load_conflicts()
    for i, c_data in enumerate(data["conflicts"]):
        conflict = Conflict.from_dict(c_data)
        if ((conflict.country1 == country1 and conflict.country2 == country2) or \
            (conflict.country1 == country2 and conflict.country2 == country1)) and \
            conflict.status == "active":
            
            conflict.status = "ended"
            conflict.ended_at = str(datetime.now())
            data["conflicts"][i] = conflict.to_dict()
            data["history"].append(conflict.to_dict())
            del data["conflicts"][i]
            save_conflicts(data)
            return True
    
    return False

def record_strike(attacker: str, target: str, damage: int):
    """
    Записывает информацию о нанесённом ударе в конфликт
    """
    conflicts = get_active_conflicts()
    for conflict in conflicts:
        if (conflict.country1 == attacker and conflict.country2 == target) or \
           (conflict.country1 == target and conflict.country2 == attacker):
            
            # Увеличиваем счётчик ударов для атакующего
            conflict.strikes_count[attacker] = conflict.strikes_count.get(attacker, 0) + 1
            
            # Увеличиваем нанесённый урон
            conflict.damage_inflicted[attacker] = conflict.damage_inflicted.get(attacker, 0) + damage
            
            conflict.last_update = str(datetime.now())
            
            # Обновляем в базе
            data = load_conflicts()
            for i, c_data in enumerate(data["conflicts"]):
                if c_data["id"] == conflict.id:
                    data["conflicts"][i] = conflict.to_dict()
                    break
            save_conflicts(data)
            break


# ==================== ФУНКЦИИ ДЛЯ АДМИНИСТРИРОВАНИЯ ====================

def admin_start_war(country1: str, country2: str, reason: str = "") -> bool:
    """Административная функция для начала войны"""
    return start_conflict(country1, country2, reason) is not None

def admin_end_war(country1: str, country2: str) -> bool:
    """Административная функция для завершения войны"""
    return end_conflict(country1, country2)


# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class ConflictSelect(Select):
    """Выбор конфликта для просмотра"""
    
    def __init__(self, user_id: int, conflicts: List[Conflict]):
        self.user_id = user_id
        
        options = []
        for conflict in conflicts[:25]:
            name = f"{conflict.country1} vs {conflict.country2}"
            desc = f"Тип: {conflict.conflict_type} | Начало: {conflict.started_at[:10]}"
            options.append(
                discord.SelectOption(
                    label=name,
                    description=desc,
                    value=conflict.id
                )
            )
        
        super().__init__(
            placeholder="Выберите конфликт для просмотра...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        conflict_id = self.values[0]
        
        # Находим конфликт
        data = load_conflicts()
        conflict_data = None
        for c_data in data["conflicts"]:
            if c_data["id"] == conflict_id:
                conflict_data = c_data
                break
        
        if not conflict_data:
            await interaction.response.send_message("❌ Конфликт не найден!", ephemeral=True)
            return
        
        conflict = Conflict.from_dict(conflict_data)
        
        embed = discord.Embed(
            title=f"⚔️ Конфликт: {conflict.country1} vs {conflict.country2}",
            color=discord.Color.red()
        )
        
        embed.add_field(name="Статус", value=conflict.status, inline=True)
        embed.add_field(name="Тип", value=conflict.conflict_type, inline=True)
        embed.add_field(name="Начало", value=conflict.started_at[:16], inline=True)
        
        if conflict.reason:
            embed.add_field(name="Причина", value=conflict.reason, inline=False)
        
        stats_text = f"**{conflict.country1}**\n"
        stats_text += f"• Ударов нанесено: {conflict.strikes_count.get(conflict.country1, 0)}\n"
        stats_text += f"• Урон инфраструктуре: {conflict.damage_inflicted.get(conflict.country1, 0)}\n\n"
        stats_text += f"**{conflict.country2}**\n"
        stats_text += f"• Ударов нанесено: {conflict.strikes_count.get(conflict.country2, 0)}\n"
        stats_text += f"• Урон инфраструктуре: {conflict.damage_inflicted.get(conflict.country2, 0)}"
        
        embed.add_field(name="Статистика", value=stats_text, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== КОМАНДЫ ДЛЯ БОТА ====================

async def show_conflicts_menu(interaction_or_ctx, user_id: int):
    """Показать меню конфликтов"""
    conflicts = get_active_conflicts()
    
    if not conflicts:
        embed = discord.Embed(
            title="🕊️ Конфликты",
            description="В данный момент нет активных военных конфликтов.",
            color=DARK_THEME_COLOR
        )
        
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction_or_ctx.send(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="⚔️ Активные конфликты",
        description=f"Всего конфликтов: {len(conflicts)}",
        color=discord.Color.red()
    )
    
    for conflict in conflicts[:5]:
        embed.add_field(
            name=f"{conflict.country1} ⚔️ {conflict.country2}",
            value=f"Тип: {conflict.conflict_type}\nНачало: {conflict.started_at[:10]}",
            inline=False
        )
    
    # Отправляем эфемерное сообщение
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
        message = await interaction_or_ctx.original_response()
    else:
        message = await interaction_or_ctx.send(embed=embed, ephemeral=True)
    
    # Если есть конфликты, показываем выбор для детального просмотра
    if conflicts:
        select = ConflictSelect(user_id, conflicts)
        view = View(timeout=120)
        view.add_item(select)
        await message.edit(view=view)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'Conflict',
    'load_conflicts',
    'save_conflicts',
    'get_active_conflicts',
    'get_conflicts_for_country',
    'are_countries_at_war',
    'get_countries_at_war_with',
    'start_conflict',
    'end_conflict',
    'record_strike',
    'admin_start_war',
    'admin_end_war',
    'show_conflicts_menu'
]

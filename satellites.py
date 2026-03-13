# satellites.py - Модуль для управления спутниковыми системами
# РЕАЛИСТИЧНАЯ ВЕРСИЯ - у государств уже есть спутники

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import math
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from political_power import spend_political_power, get_political_power
from game_time import get_current_game_time, days_since_last_event

# Файл для хранения данных о спутниках
SATELLITES_FILE = 'satellites.json'

# ==================== РЕАЛЬНЫЕ СПУТНИКОВЫЕ ГРУППИРОВКИ СТРАН ====================

# Данные основаны на реальных количествах активных спутников (по состоянию на 2023-2024)
STARTING_SATELLITES = {
    "США": {
        "military": 187,  # Включая NRO, разведывательные, GPS (31), SBIRS и т.д.
        "civilian": 293,  # NOAA, NASA, коммерческие, связи
        "total_approx": 480  # Всего активных спутников
    },
    "Россия": {
        "military": 112,  # ГЛОНАСС (26), разведывательные, связи
        "civilian": 85,   # Метеорологические, научные, коммерческие
        "total_approx": 197
    },
    "Китай": {
        "military": 156,  # Бэйдоу (35+), разведывательные
        "civilian": 214,  # Научные, метеорологические, коммерческие
        "total_approx": 370
    },
    "Германия": {
        "military": 8,    # В рамках ЕС, SAR-Lupe
        "civilian": 47,   # Научные, метеорологические, коммерческие
        "total_approx": 55
    },
    "Великобритания": {
        "military": 7,    # Skynet, связи
        "civilian": 43,   # Научные, коммерческие
        "total_approx": 50
    },
    "Франция": {
        "military": 12,   # Syracuse, CSO, CERES
        "civilian": 38,   # Научные, метеорологические
        "total_approx": 50
    },
    "Япония": {
        "military": 9,    # QZSS (4), разведывательные
        "civilian": 78,   # Научные, метеорологические
        "total_approx": 87
    },
    "Израиль": {
        "military": 14,   # Разведывательные (Ofek, TecSAR)
        "civilian": 8,    # Научные, коммерческие
        "total_approx": 22
    },
    "Украина": {
        "military": 0,    # Нет военных спутников
        "civilian": 1,    # Сич-2-30 (с 2022)
        "total_approx": 1
    },
    "Иран": {
        "military": 3,    # Разведывательные (Noor, Khayyam)
        "civilian": 2,    # Научные
        "total_approx": 5
    }
}

# Типы спутников
SATELLITE_TYPES = {
    "military": {
        "name": "Военный спутник",
        "description": "Разведка, навигация, связь для военных операций.",
        "base_cost": 500000000,  # 500 млн $
        "pp_cost": 10,
        "build_time_hours": 72,  # 3 дня
        "effects": {
            "drone_accuracy": 0.005,  # +0.5% за 10 спутников = +5%
            "missile_accuracy": 0.005,
            "intercept_difficulty": 0.005,
            "recon_range": 0.01  # +1% за 10 спутников = +10%
        },
        "maintenance_cost": 10000000  # 10 млн $ в год за спутник
    },
    "civilian": {
        "name": "Гражданский спутник",
        "description": "Связь, навигация, наблюдение за погодой.",
        "base_cost": 300000000,  # 300 млн $
        "pp_cost": 5,
        "build_time_hours": 48,  # 2 дня
        "effects": {
            "infrastructure_boost": 0.002,  # +0.2% за 10 спутников = +2%
            "research_boost": 0.003,        # +0.3% за 10 спутников = +3%
            "gdp_boost": 0.001,             # +0.1% за 10 спутников = +1%
            "communication_boost": 0.004     # +0.4% за 10 спутников = +4%
        },
        "maintenance_cost": 5000000  # 5 млн $ в год за спутник
    }
}

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_satellites():
    """Загружает данные о спутниках"""
    try:
        with open(SATELLITES_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"satellites": {}}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        # Создаем данные с реальными стартовыми значениями
        initial_data = {"satellites": {}}
        for country, data in STARTING_SATELLITES.items():
            initial_data["satellites"][country] = {
                "military": data["military"],
                "civilian": data["civilian"],
                "launch_history": [
                    {
                        "type": "initial",
                        "date": "2022-12-01",
                        "game_date": "2022-12-01",
                        "count": data["military"] + data["civilian"]
                    }
                ],
                "last_maintenance": str(datetime.now())
            }
        save_satellites(initial_data)
        return initial_data

def save_satellites(data):
    """Сохраняет данные о спутниках"""
    with open(SATELLITES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_country_satellites(country_name: str) -> Dict:
    """Получает данные о спутниках страны"""
    data = load_satellites()
    if country_name not in data["satellites"]:
        # Если страны нет в базе, создаем с нулевыми значениями
        data["satellites"][country_name] = {
            "military": 0,
            "civilian": 0,
            "launch_history": [],
            "last_maintenance": str(datetime.now())
        }
        save_satellites(data)
    return data["satellites"][country_name]

def update_country_satellites(country_name: str, satellites_data: Dict):
    """Обновляет данные о спутниках страны"""
    data = load_satellites()
    data["satellites"][country_name] = satellites_data
    save_satellites(data)

# ==================== ФУНКЦИИ ДЛЯ РАСЧЕТА ЭФФЕКТОВ ====================

def get_satellite_bonuses(country_name: str) -> Dict:
    """
    Возвращает суммарные бонусы от всех спутников страны
    Бонусы масштабируются линейно (каждый спутник дает свой вклад)
    """
    satellites = get_country_satellites(country_name)
    
    military_count = satellites.get("military", 0)
    civilian_count = satellites.get("civilian", 0)
    
    bonuses = {
        "military": {},
        "civilian": {},
        "total_military": military_count,
        "total_civilian": civilian_count
    }
    
    # Военные бонусы (каждый спутник дает свой вклад)
    if military_count > 0:
        mil_effects = SATELLITE_TYPES["military"]["effects"]
        for effect, base_value in mil_effects.items():
            bonuses["military"][effect] = base_value * military_count
    
    # Гражданские бонусы
    if civilian_count > 0:
        civ_effects = SATELLITE_TYPES["civilian"]["effects"]
        for effect, base_value in civ_effects.items():
            bonuses["civilian"][effect] = base_value * civilian_count
    
    return bonuses

def apply_satellite_bonuses_to_weapon(weapon_type: str, base_accuracy: float, attacker_country: str) -> float:
    """
    Применяет бонусы военных спутников к точности оружия
    """
    bonuses = get_satellite_bonuses(attacker_country)
    
    if not bonuses["military"]:
        return base_accuracy
    
    # Определяем тип оружия
    is_drone = any(drone in weapon_type for drone in ["uav", "drone", "kamikaze"])
    is_missile = any(missile in weapon_type for missile in ["missile", "rocket"])
    
    if is_drone:
        drone_bonus = bonuses["military"].get("drone_accuracy", 0)
        return base_accuracy * (1 + drone_bonus)
    
    if is_missile:
        missile_bonus = bonuses["military"].get("missile_accuracy", 0)
        return base_accuracy * (1 + missile_bonus)
    
    return base_accuracy

def apply_satellite_bonuses_to_infrastructure(base_bonus: float, country_name: str, bonus_type: str = "infrastructure_boost") -> float:
    """
    Применяет бонусы гражданских спутников к инфраструктуре
    """
    bonuses = get_satellite_bonuses(country_name)
    
    if not bonuses["civilian"]:
        return base_bonus
    
    boost = bonuses["civilian"].get(bonus_type, 0)
    return base_bonus * (1 + boost)

def get_research_boost(country_name: str) -> float:
    """Возвращает бонус к исследованиям от гражданских спутников"""
    bonuses = get_satellite_bonuses(country_name)
    return bonuses["civilian"].get("research_boost", 0)

def get_intercept_difficulty_boost(country_name: str) -> float:
    """Возвращает бонус к сложности перехвата для атакующих"""
    bonuses = get_satellite_bonuses(country_name)
    return bonuses["military"].get("intercept_difficulty", 0)

def get_gdp_boost(country_name: str) -> float:
    """Возвращает бонус к ВВП от гражданских спутников"""
    bonuses = get_satellite_bonuses(country_name)
    return bonuses["civilian"].get("gdp_boost", 0)

# ==================== ПРОВЕРКА ВОЗМОЖНОСТИ ЗАПУСКА ====================

def can_launch_satellite(player_data, satellite_type: str) -> Tuple[bool, str]:
    """
    Проверяет, может ли игрок запустить спутник
    """
    country_name = player_data["state"]["statename"]
    
    sat_info = SATELLITE_TYPES[satellite_type]
    
    # Проверяем бюджет
    cost = sat_info["base_cost"]
    if player_data["economy"]["budget"] < cost:
        return False, f"Недостаточно средств! Нужно: {format_billion(cost)}"
    
    # Проверяем политическую власть
    current_pp = get_political_power(player_data)
    if current_pp < sat_info["pp_cost"]:
        return False, f"Недостаточно политической власти! Нужно: {sat_info['pp_cost']}, у вас: {current_pp:.1f}"
    
    return True, "OK"

def launch_satellite(player_data, satellite_type: str) -> bool:
    """
    Запускает спутник (списывает ресурсы)
    """
    country_name = player_data["state"]["statename"]
    satellites = get_country_satellites(country_name)
    sat_info = SATELLITE_TYPES[satellite_type]
    
    # Списываем деньги
    player_data["economy"]["budget"] -= sat_info["base_cost"]
    
    # Списываем ПВ
    spend_political_power(player_data, sat_info["pp_cost"])
    
    # Добавляем спутник
    satellites[satellite_type] = satellites.get(satellite_type, 0) + 1
    
    # Записываем в историю
    if "launch_history" not in satellites:
        satellites["launch_history"] = []
    
    game_date, _ = get_current_game_time()
    satellites["launch_history"].append({
        "type": satellite_type,
        "date": str(datetime.now()),
        "game_date": game_date.strftime("%Y-%m-%d"),
        "count": 1
    })
    
    update_country_satellites(country_name, satellites)
    
    return True

# ==================== ЕЖЕГОДНОЕ ОБСЛУЖИВАНИЕ ====================

async def satellite_maintenance_loop(bot_instance):
    """Фоновая задача для ежегодного обслуживания спутников"""
    await bot_instance.wait_until_ready()
    
    while not bot_instance.is_closed():
        try:
            states = load_states()
            satellites_data = load_satellites()
            now = datetime.now()
            
            for country_name, sat_data in satellites_data["satellites"].items():
                # Находим данные игрока
                player_data = None
                for data in states["players"].values():
                    if data.get("state", {}).get("statename") == country_name:
                        player_data = data
                        break
                
                if not player_data or "assigned_to" not in player_data:
                    continue
                
                # Проверяем, прошёл ли год с последнего обслуживания
                last_maintenance_str = sat_data.get("last_maintenance", str(now))
                days_passed = days_since_last_event(last_maintenance_str)
                
                if days_passed >= 365:  # Игровой год
                    # Рассчитываем стоимость обслуживания
                    military_count = sat_data.get("military", 0)
                    civilian_count = sat_data.get("civilian", 0)
                    
                    mil_cost = military_count * SATELLITE_TYPES["military"]["maintenance_cost"]
                    civ_cost = civilian_count * SATELLITE_TYPES["civilian"]["maintenance_cost"]
                    total_cost = mil_cost + civ_cost
                    
                    # Проверяем бюджет
                    if player_data["economy"]["budget"] >= total_cost:
                        # Списываем
                        player_data["economy"]["budget"] -= total_cost
                        sat_data["last_maintenance"] = str(now)
                        
                        # Уведомляем при большой сумме
                        if total_cost > 100000000:  # > 100 млн
                            try:
                                user = await bot_instance.fetch_user(int(player_data["assigned_to"]))
                                if user:
                                    embed = discord.Embed(
                                        title="🛰️ Обслуживание спутников",
                                        description=f"Списано {format_billion(total_cost)} за годовое обслуживание",
                                        color=DARK_THEME_COLOR
                                    )
                                    embed.add_field(name="Военные спутники", value=military_count, inline=True)
                                    embed.add_field(name="Гражданские спутники", value=civilian_count, inline=True)
                                    await user.send(embed=embed)
                            except:
                                pass
                    else:
                        # Не хватает денег - часть спутников выходит из строя
                        # Пропорционально недостатку средств
                        shortfall = total_cost - player_data["economy"]["budget"]
                        loss_ratio = shortfall / total_cost
                        
                        lost_military = min(military_count, max(1, int(military_count * loss_ratio)))
                        lost_civilian = min(civilian_count, max(1, int(civilian_count * loss_ratio)))
                        
                        sat_data["military"] = max(0, military_count - lost_military)
                        sat_data["civilian"] = max(0, civilian_count - lost_civilian)
                        
                        # Списываем сколько есть
                        player_data["economy"]["budget"] = 0
                        
                        # Уведомляем
                        try:
                            user = await bot_instance.fetch_user(int(player_data["assigned_to"]))
                            if user:
                                embed = discord.Embed(
                                    title="⚠️ Потеря спутников",
                                    description=f"Не хватило средств на полное обслуживание!",
                                    color=discord.Color.red()
                                )
                                if lost_military > 0:
                                    embed.add_field(name="Потеряно военных", value=lost_military, inline=True)
                                if lost_civilian > 0:
                                    embed.add_field(name="Потеряно гражданских", value=lost_civilian, inline=True)
                                embed.add_field(name="Осталось военных", value=sat_data["military"], inline=True)
                                embed.add_field(name="Осталось гражданских", value=sat_data["civilian"], inline=True)
                                await user.send(embed=embed)
                        except:
                            pass
                        
                        sat_data["last_maintenance"] = str(now)
            
            save_states(states)
            save_satellites(satellites_data)
            
            await asyncio.sleep(3600)  # Проверка каждый час
            
        except Exception as e:
            print(f"❌ Ошибка в satellite_maintenance_loop: {e}")
            await asyncio.sleep(3600)

# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class SatelliteTypeSelect(Select):
    """Выбор типа спутника для запуска"""
    
    def __init__(self, user_id, player_data, available_types, original_message):
        self.user_id = user_id
        self.player_data = player_data
        self.available_types = available_types
        self.original_message = original_message
        
        options = []
        for sat_type in available_types:
            info = SATELLITE_TYPES[sat_type]
            options.append(
                discord.SelectOption(
                    label=info['name'],
                    description=info['description'][:50],
                    value=sat_type
                )
            )
        
        super().__init__(
            placeholder="Выберите тип спутника...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        sat_type = self.values[0]
        info = SATELLITE_TYPES[sat_type]
        
        embed = discord.Embed(
            title=f"Запуск: {info['name']}",
            description=info['description'],
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Стоимость", value=format_billion(info['base_cost']), inline=True)
        embed.add_field(name="Полит. власть", value=str(info['pp_cost']), inline=True)
        embed.add_field(name="Время строительства", value=f"{info['build_time_hours']} ч", inline=True)
        
        # Эффекты
        effects_text = ""
        effect_names = {
            "drone_accuracy": "Точность дронов",
            "missile_accuracy": "Точность ракет",
            "intercept_difficulty": "Сложность перехвата",
            "recon_range": "Дальность разведки",
            "infrastructure_boost": "Эффективность инфраструктуры",
            "research_boost": "Скорость исследований",
            "gdp_boost": "ВВП",
            "communication_boost": "Эффективность связи"
        }
        
        for effect, value in info['effects'].items():
            effects_text += f"• {effect_names.get(effect, effect)}: +{value*100:.2f}% за спутник\n"
        
        embed.add_field(name="Эффекты", value=effects_text, inline=False)
        
        view = LaunchConfirmationView(self.user_id, self.player_data, sat_type)
        
        await interaction.response.edit_message(embed=embed, view=view)


class LaunchConfirmationView(View):
    """Подтверждение запуска спутника"""
    
    def __init__(self, user_id, player_data, sat_type):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
        self.sat_type = sat_type
    
    @discord.ui.button(label="✅ Запустить", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверяем возможность
        can_launch, message = can_launch_satellite(self.player_data, self.sat_type)
        if not can_launch:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Запускаем
        success = launch_satellite(self.player_data, self.sat_type)
        
        if not success:
            await interaction.response.send_message("❌ Ошибка при запуске!", ephemeral=True)
            return
        
        # Сохраняем изменения
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                data.update(self.player_data)
                break
        save_states(states)
        
        info = SATELLITE_TYPES[self.sat_type]
        
        embed = discord.Embed(
            title="✅ Спутник запущен!",
            description=f"**{info['name']}** успешно выведен на орбиту",
            color=discord.Color.green()
        )
        
        # Показываем текущую группировку
        country_name = self.player_data["state"]["statename"]
        satellites = get_country_satellites(country_name)
        
        embed.add_field(
            name="Текущая группировка",
            value=f"🛰️ Военные: {satellites.get('military', 0)}\n"
                  f"🛰️ Гражданские: {satellites.get('civilian', 0)}",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Запуск отменён",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ОСНОВНОЕ МЕНЮ ====================

async def show_satellite_menu(ctx, user_id: int):
    """Показать меню управления спутниками"""
    
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
    satellites = get_country_satellites(country_name)
    current_pp = get_political_power(player_data)
    
    military_count = satellites.get("military", 0)
    civilian_count = satellites.get("civilian", 0)
    
    # Рассчитываем текущие бонусы
    bonuses = get_satellite_bonuses(country_name)
    
    embed = discord.Embed(
        title=f"🛰️ Космическая программа {country_name}",
        description="Реальные данные о спутниковых группировках",
        color=DARK_THEME_COLOR
    )
    
    # Текущая группировка
    total = military_count + civilian_count
    embed.add_field(
        name="Текущие спутники",
        value=f"🛰️ Всего: {total}\n"
              f"⚔️ Военные: {military_count}\n"
              f"📡 Гражданские: {civilian_count}",
        inline=True
    )
    
    embed.add_field(
        name="Политическая власть",
        value=f"{current_pp:.1f} ПВ",
        inline=True
    )
    
    # Военные бонусы
    if bonuses["military"]:
        mil_text = ""
        effect_names = {
            "drone_accuracy": "Точность дронов",
            "missile_accuracy": "Точность ракет",
            "intercept_difficulty": "Сложность перехвата",
            "recon_range": "Дальность разведки"
        }
        for effect, value in bonuses["military"].items():
            mil_text += f"• {effect_names.get(effect, effect)}: +{value*100:.2f}%\n"
        embed.add_field(name="⚡ Военные бонусы", value=mil_text, inline=False)
    
    # Гражданские бонусы
    if bonuses["civilian"]:
        civ_text = ""
        effect_names = {
            "infrastructure_boost": "Эффективность инфраструктуры",
            "research_boost": "Скорость исследований",
            "gdp_boost": "ВВП",
            "communication_boost": "Эффективность связи"
        }
        for effect, value in bonuses["civilian"].items():
            civ_text += f"• {effect_names.get(effect, effect)}: +{value*100:.2f}%\n"
        embed.add_field(name="📡 Гражданские бонусы", value=civ_text, inline=False)
    
    # Сравнение с реальными данными (для интереса)
    if country_name in STARTING_SATELLITES:
        real_data = STARTING_SATELLITES[country_name]
        embed.add_field(
            name="📊 Реальная группировка (2023)",
            value=f"Военные: {real_data['military']}, Гражданские: {real_data['civilian']}",
            inline=False
        )
    
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, ephemeral=True)
        message = await ctx.original_response()
    else:
        message = await ctx.send(embed=embed, ephemeral=True)
    
    # Кнопка запуска нового спутника
    view = SatelliteMainView(user_id, player_data, country_name, message)
    await message.edit(view=view)


class SatelliteMainView(View):
    """Главное меню спутников с кнопками"""
    
    def __init__(self, user_id, player_data, country_name, original_message):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.country_name = country_name
        self.original_message = original_message
    
    @discord.ui.button(label="🚀 Запустить новый спутник", style=discord.ButtonStyle.secondary)
    async def launch_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Выберите тип спутника",
            description="Каждый спутник дает небольшой постоянный бонус",
            color=DARK_THEME_COLOR
        )
        
        select = SatelliteTypeSelect(
            self.user_id, self.player_data,
            ["military", "civilian"], interaction.message
        )
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_main(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await show_satellite_menu(interaction, self.user_id)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_satellite_menu',
    'satellite_maintenance_loop',
    'get_satellite_bonuses',
    'apply_satellite_bonuses_to_weapon',
    'apply_satellite_bonuses_to_infrastructure',
    'get_research_boost',
    'get_intercept_difficulty_boost',
    'get_gdp_boost',
    'SATELLITE_TYPES',
    'STARTING_SATELLITES'
]

# mobilization.py - Модуль для мобилизации гражданской промышленности и населения
# ИСПРАВЛЕНО: мобилизация населения теперь по кнопке

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import math
import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from infra_build import load_infrastructure, save_infrastructure, get_all_regions_from_country
from political_power import spend_political_power, get_political_power
from trade_tariffs import TariffSystem

# Файл для хранения активных мобилизационных программ
MOBILIZATION_FILE = 'mobilization.json'

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_mobilization():
    """Загружает данные о мобилизационных программах"""
    try:
        with open(MOBILIZATION_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_programs": [], "completed_programs": []}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"active_programs": [], "completed_programs": []}

def save_mobilization(data):
    """Сохраняет данные о мобилизационных программах"""
    with open(MOBILIZATION_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==================== РЕЦЕПТЫ МОБИЛИЗАЦИИ ====================

MOBILIZATION_RECIPES = {
    # Бронетехника из автомобилей
    "armored_vehicle_improvised": {
        "name": "Кустарная бронемашина",
        "description": "Импровизированный бронеавтомобиль на базе гражданского авто",
        "civilian_inputs": {
            "cars": 1,           # 1 легковой автомобиль
            "steel": 0.1,        # 0.1 стали
        },
        "military_inputs": {
            "equipment.small_arms": 1  # 1 стрелковое оружие
        },
        "military_output": {
            "type": "ground.armored_vehicles",
            "quantity": 1,
            "quality_modifier": 0.6
        },
        "required_civ_factories": 1,
        "duration_hours": 24,
        "pp_cost": 5,
        "category": "ground"
    },
    
    "btr_improvised": {
        "name": "Кустарный БТР",
        "description": "Бронетранспортер из грузовика с броней и вооружением",
        "civilian_inputs": {
            "trucks": 1,          # 1 грузовик
            "steel": 0.4,          # 0.4 стали
        },
        "military_inputs": {
            "equipment.small_arms": 2  # 2 стрелкового оружия
        },
        "military_output": {
            "type": "ground.btr",
            "quantity": 1,
            "quality_modifier": 0.55
        },
        "required_civ_factories": 2,
        "duration_hours": 48,
        "pp_cost": 10,
        "category": "ground"
    },
    
    # Противовоздушная оборона
    "short_range_air_defense_improvised": {
        "name": "Кустарное ПВО малой дальности",
        "description": "Импровизированная зенитная установка на базе автомобиля",
        "civilian_inputs": {
            "cars": 1,             # 1 легковой автомобиль
            "electronics": 0.05,    # 0.05 электроники
        },
        "military_inputs": {
            "equipment.manpads": 1  # 1 ПЗРК
        },
        "military_output": {
            "type": "ground.short_range_air_defense",
            "quantity": 1,
            "quality_modifier": 0.5
        },
        "required_civ_factories": 2,
        "duration_hours": 36,
        "pp_cost": 15,
        "category": "ground"
    },
    
    "spaa_improvised": {
        "name": "Кустарная ЗСУ",
        "description": "Зенитная самоходная установка из грузовика",
        "civilian_inputs": {
            "trucks": 1,           # 1 грузовик
            "steel": 1,             # 1 сталь
            "electronics": 0.1,     # 0.1 электроники
        },
        "military_inputs": {
            "equipment.manpads": 1,     # 1 ПЗРК
            "equipment.small_arms": 2    # 2 стрелкового оружия
        },
        "military_output": {
            "type": "ground.short_range_air_defense",
            "quantity": 1,
            "quality_modifier": 0.55
        },
        "required_civ_factories": 3,
        "duration_hours": 60,
        "pp_cost": 20,
        "category": "ground"
    },
    
    # Артиллерия
    "howitzer_improvised": {
        "name": "Кустарная гаубица",
        "description": "Импровизированное артиллерийское орудие",
        "civilian_inputs": {
            "steel": 0.07,          # 0.07 стали
            "electronics": 0.1,      # 0.1 электроники
        },
        "military_output": {
            "type": "ground.towed_artillery",
            "quantity": 1,
            "quality_modifier": 0.4
        },
        "required_civ_factories": 2,
        "duration_hours": 72,
        "pp_cost": 15,
        "category": "ground"
    },
    
    # Дроны
    "fpv_drone_improvised": {
        "name": "Кустарный FPV-дрон",
        "description": "FPV-дрон из гражданских компонентов",
        "civilian_inputs": {
            "aluminum": 0.01,        # 0.01 алюминия
            "electronics": 0.15,      # 0.15 электроники
        },
        "military_output": {
            "type": "equipment.fpv_drones",
            "quantity": 5,
            "quality_modifier": 0.7
        },
        "required_civ_factories": 1,
        "duration_hours": 12,
        "pp_cost": 5,
        "category": "equipment"
    },
    
    "kamikaze_drone_improvised": {
        "name": "Кустарный дрон-камикадзе",
        "description": "Барражирующий боеприпас кустарного производства",
        "civilian_inputs": {
            "aluminum": 0.12,         # 0.12 алюминия
            "electronics": 0.2,        # 0.2 электроники
        },
        "military_output": {
            "type": "air.kamikaze_drones",
            "quantity": 3,
            "quality_modifier": 0.6
        },
        "required_civ_factories": 1,
        "duration_hours": 18,
        "pp_cost": 8,
        "category": "air"
    }
}

# ==================== ФУНКЦИИ МОБИЛИЗАЦИИ НАСЕЛЕНИЯ (РУЧНЫЕ) ====================

def calculate_mobilization_possible(player_data) -> Dict:
    """
    Рассчитывает, сколько человек можно мобилизовать
    """
    population = player_data["state"]["population"]
    army_size = player_data["state"]["army_size"]
    
    # Максимум 1.5% населения
    max_reservists = int(population * 0.034)
    available = max(0, max_reservists - army_size)
    
    # Доступное стрелковое оружие
    small_arms = player_data.get("army", {}).get("equipment", {}).get("small_arms", 0)
    
    # Можно мобилизовать не больше, чем есть оружия
    max_by_weapons = small_arms
    
    return {
        "max_possible": min(available, max_by_weapons),
        "reservists": available,
        "small_arms_available": small_arms,
        "current_army": army_size,
        "max_reservists": max_reservists
    }

def execute_mobilization(player_data, quantity: int) -> Tuple[bool, str, Dict]:
    """
    Выполняет мобилизацию указанного количества человек
    """
    # Проверяем возможность
    possible = calculate_mobilization_possible(player_data)
    
    if quantity <= 0:
        return False, "Количество должно быть положительным", {}
    
    if quantity > possible["max_possible"]:
        return False, f"Можно мобилизовать максимум {possible['max_possible']} человек", {}
    
    # Списываем оружие
    player_data["army"]["equipment"]["small_arms"] -= quantity
    
    # Добавляем в армию
    old_size = player_data["state"]["army_size"]
    player_data["state"]["army_size"] += quantity
    
    # Рассчитываем затраты ПВ (1 ПВ на 1000 человек, минимум 1)
    pp_cost = max(1, quantity // 1000)
    
    # Списываем ПВ
    spend_political_power(player_data, pp_cost)
    
    result = {
        "mobilized": quantity,
        "old_army": old_size,
        "new_army": old_size + quantity,
        "pp_cost": pp_cost,
        "remaining_reservists": possible["reservists"] - quantity,
        "remaining_weapons": possible["small_arms_available"] - quantity
    }
    
    return True, f"Мобилизовано {format_number(quantity)} человек", result

# ==================== ФУНКЦИИ ДЛЯ ПРОВЕРКИ РЕСУРСОВ ====================

def get_resource_amount(player_data, resource: str) -> float:
    """
    Получает количество ресурса из правильного места (resources или civil_goods)
    """
    # Ресурсы из !ресурсы
    if resource in ["steel", "aluminum", "electronics", "oil", "gas", "coal", "uranium", "rare_metals", "food"]:
        return player_data.get("resources", {}).get(resource, 0)
    
    # Гражданские товары из !товары
    if resource in ["cars", "trucks", "drones", "agricultural_machinery", "construction_machinery"]:
        return player_data.get("civil_goods", {}).get(resource, 0)
    
    return 0

def deduct_resource(player_data, resource: str, amount: float) -> bool:
    """
    Списывает ресурс из правильного места
    """
    # Ресурсы из !ресурсы
    if resource in ["steel", "aluminum", "electronics", "oil", "gas", "coal", "uranium", "rare_metals", "food"]:
        if player_data.get("resources", {}).get(resource, 0) < amount:
            return False
        player_data["resources"][resource] -= amount
        return True
    
    # Гражданские товары из !товары
    if resource in ["cars", "trucks", "drones", "agricultural_machinery", "construction_machinery"]:
        if player_data.get("civil_goods", {}).get(resource, 0) < amount:
            return False
        player_data["civil_goods"][resource] -= amount
        return True
    
    return False

def check_mobilization_requirements(player_data, recipe_id: str, region: str) -> Tuple[bool, str]:
    """
    Проверяет, может игрок запустить мобилизационную программу
    """
    recipe = MOBILIZATION_RECIPES.get(recipe_id)
    if not recipe:
        return False, "Рецепт не найден"
    
    # Проверяем политическую власть
    current_pp = get_political_power(player_data)
    if current_pp < recipe["pp_cost"]:
        return False, f"Недостаточно политической власти! Нужно: {recipe['pp_cost']}, у вас: {current_pp:.1f}"
    
    # Проверяем наличие гражданских заводов в регионе
    infra = load_infrastructure()
    country_name = player_data["state"]["statename"]
    
    country_id = None
    region_data = None
    
    for cid, data in infra["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            # Ищем регион
            for econ_region, econ_data in data.get("economic_regions", {}).items():
                if region in econ_data.get("regions", {}):
                    region_data = econ_data["regions"][region]
                    break
            break
    
    if not region_data:
        return False, "Регион не найден"
    
    civ_factories = region_data.get("civilian_factories", 0)
    if civ_factories < recipe["required_civ_factories"]:
        return False, f"В регионе недостаточно гражданских фабрик! Нужно: {recipe['required_civ_factories']}, есть: {civ_factories}"
    
    # Проверяем наличие гражданских ресурсов (из !ресурсы и !товары)
    for resource, amount in recipe.get("civilian_inputs", {}).items():
        available = get_resource_amount(player_data, resource)
        if available < amount:
            resource_names = {
                "cars": "🚗 Автомобили",
                "trucks": "🚚 Грузовики",
                "steel": "⚙️ Сталь",
                "aluminum": "🛩️ Алюминий",
                "electronics": "💻 Электроника"
            }
            name = resource_names.get(resource, resource)
            return False, f"Недостаточно {name}! Нужно: {amount}, есть: {available}"
    
    # Проверяем наличие военных ресурсов (стрелковое оружие и т.д.)
    army = player_data.get("army", {})
    for mil_resource, amount in recipe.get("military_inputs", {}).items():
        path = mil_resource.split('.')
        current = army
        for key in path:
            if key in current:
                current = current[key]
            else:
                return False, f"Недостаточно {mil_resource}! Нужно: {amount}, есть: 0"
        
        if isinstance(current, (int, float)) and current < amount:
            # Человеческое название для военных ресурсов
            mil_names = {
                "equipment.small_arms": "стрелкового оружия",
                "equipment.manpads": "ПЗРК"
            }
            name = mil_names.get(mil_resource, mil_resource)
            return False, f"Недостаточно {name}! Нужно: {amount}, есть: {current}"
    
    return True, "OK"

def consume_mobilization_resources(player_data, recipe: Dict) -> bool:
    """
    Списывает ресурсы для мобилизации
    """
    # Гражданские ресурсы (из !ресурсы и !товары)
    for resource, amount in recipe.get("civilian_inputs", {}).items():
        if not deduct_resource(player_data, resource, amount):
            return False
    
    # Военные ресурсы
    army = player_data.get("army", {})
    for mil_resource, amount in recipe.get("military_inputs", {}).items():
        path = mil_resource.split('.')
        current = army
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        last_key = path[-1]
        if last_key not in current or current[last_key] < amount:
            return False
        current[last_key] -= amount
    
    return True

# ==================== ФОНОВАЯ ЗАДАЧА ДЛЯ ЗАВЕРШЕНИЯ ПРОИЗВОДСТВА ====================

async def mobilization_completion_loop(bot_instance):
    """Фоновая задача для проверки завершения мобилизационных программ (производство техники)"""
    await bot_instance.wait_until_ready()
    
    while not bot_instance.is_closed():
        try:
            mob_data = load_mobilization()
            states = load_states()
            now = datetime.now()
            
            completed = []
            
            for program in mob_data["active_programs"][:]:
                completion = datetime.fromisoformat(program["completion_time"])
                
                if completion <= now and not program.get("notified", False):
                    # Находим игрока
                    player_data = None
                    for data in states["players"].values():
                        if data.get("assigned_to") == program["user_id"]:
                            player_data = data
                            break
                    
                    if player_data:
                        # Добавляем технику
                        output = program["output"]
                        path = output["type"].split('.')
                        
                        if "army" not in player_data:
                            player_data["army"] = {}
                        
                        current = player_data["army"]
                        for key in path[:-1]:
                            if key not in current:
                                current[key] = {}
                            current = current[key]
                        
                        last_key = path[-1]
                        current[last_key] = current.get(last_key, 0) + output["quantity"]
                        
                        # Отмечаем как завершенную
                        program["status"] = "completed"
                        program["completed_at"] = str(now)
                        mob_data["completed_programs"].append(program)
                        mob_data["active_programs"].remove(program)
                        completed.append(program)
                        
                        # Уведомляем
                        try:
                            user = await bot_instance.fetch_user(int(program["user_id"]))
                            if user:
                                embed = discord.Embed(
                                    title="✅ Мобилизация завершена!",
                                    description=f"**{program['recipe_name']}** в регионе **{program['region']}**",
                                    color=discord.Color.green()
                                )
                                
                                output_names = {
                                    "ground.armored_vehicles": "Бронеавтомобили",
                                    "ground.btr": "БТР",
                                    "ground.short_range_air_defense": "ПВО малой дальности",
                                    "ground.towed_artillery": "Гаубица",
                                    "equipment.fpv_drones": "FPV-дроны",
                                    "air.kamikaze_drones": "Дроны-камикадзе"
                                }
                                
                                embed.add_field(
                                    name="Получено",
                                    value=f"{output_names.get(output['type'], output['type'])} x{output['quantity']}",
                                    inline=False
                                )
                                
                                await user.send(embed=embed)
                        except:
                            pass
                    
                    program["notified"] = True
            
            if completed:
                save_mobilization(mob_data)
                save_states(states)
                print(f"✅ Завершено {len(completed)} мобилизационных программ")
            
            await asyncio.sleep(60)  # Проверка каждую минуту
            
        except Exception as e:
            print(f"❌ Ошибка в mobilization_completion_loop: {e}")
            await asyncio.sleep(60)

# ==================== КЛАССЫ ДЛЯ МОБИЛИЗАЦИИ НАСЕЛЕНИЯ ====================

class MobilizationModal(Modal, title="Мобилизация населения"):
    def __init__(self, user_id, player_data):
        super().__init__()
        self.user_id = user_id
        self.player_data = player_data
        
        possible = calculate_mobilization_possible(player_data)
        
        self.quantity_input = TextInput(
            label=f"Количество (макс: {possible['max_possible']})",
            placeholder="Введите число",
            min_length=1,
            max_length=7,
            required=True
        )
        self.add_item(self.quantity_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            quantity = int(self.quantity_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        possible = calculate_mobilization_possible(self.player_data)
        
        if quantity <= 0:
            await interaction.response.send_message("❌ Количество должно быть положительным!", ephemeral=True)
            return
        
        if quantity > possible["max_possible"]:
            await interaction.response.send_message(
                f"❌ Максимум можно мобилизовать {possible['max_possible']} человек!\n"
                f"(Резервистов: {possible['reservists']}, оружия: {possible['small_arms_available']})",
                ephemeral=True
            )
            return
        
        # Запрашиваем подтверждение
        embed = discord.Embed(
            title="⚔️ Подтверждение мобилизации",
            description=f"Мобилизация {format_number(quantity)} человек",
            color=DARK_THEME_COLOR
        )
        
        pp_cost = max(1, quantity // 1000)
        
        embed.add_field(
            name="Результат",
            value=f"👷 Текущая армия: {format_number(possible['current_army'])} чел.\n"
                  f"📈 Новая армия: {format_number(possible['current_army'] + quantity)} чел.\n"
                  f"🔫 Потребуется оружия: {format_number(quantity)} ед.\n"
                  f"⚡ Стоимость ПВ: {pp_cost}",
            inline=False
        )
        
        view = MobilizationConfirmView(
            self.user_id, self.player_data, quantity, pp_cost
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class MobilizationConfirmView(View):
    def __init__(self, user_id, player_data, quantity, pp_cost):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.player_data = player_data
        self.quantity = quantity
        self.pp_cost = pp_cost
    
    @discord.ui.button(label="✅ Подтвердить", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Выполняем мобилизацию
        success, message, result = execute_mobilization(self.player_data, self.quantity)
        
        if not success:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Сохраняем изменения
        states = load_states()
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                data.update(self.player_data)
                break
        save_states(states)
        
        embed = discord.Embed(
            title="✅ Мобилизация завершена!",
            description=f"Мобилизовано {format_number(self.quantity)} человек",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Статистика",
            value=f"👷 Было: {format_number(result['old_army'])} чел.\n"
                  f"👷 Стало: {format_number(result['new_army'])} чел.\n"
                  f"🔫 Осталось оружия: {format_number(result['remaining_weapons'])} ед.\n"
                  f"📊 Осталось резервистов: {format_number(result['remaining_reservists'])} чел.",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Мобилизация отменена",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== КЛАССЫ ДЛЯ ПРОМЫШЛЕННОЙ МОБИЛИЗАЦИИ ====================

class RegionSelect(Select):
    """Выбор региона для мобилизации"""
    
    def __init__(self, user_id, country_name, regions, recipe_id, recipe, original_message):
        self.user_id = user_id
        self.country_name = country_name
        self.regions = regions
        self.recipe_id = recipe_id
        self.recipe = recipe
        self.original_message = original_message
        
        options = []
        for region_name, region_data in list(regions.items())[:25]:
            civ_factories = region_data.get("civilian_factories", 0)
            available = "✅" if civ_factories >= recipe["required_civ_factories"] else "❌"
            
            options.append(
                discord.SelectOption(
                    label=f"{available} {region_name[:95]}",
                    description=f"Гражданских фабрик: {civ_factories}",
                    value=region_name
                )
            )
        
        super().__init__(
            placeholder="Выберите регион для производства...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        region = self.values[0]
        
        # Показываем подтверждение
        embed = discord.Embed(
            title=f"Мобилизация: {self.recipe['name']}",
            description=self.recipe['description'],
            color=DARK_THEME_COLOR
        )
        
        # Гражданские ресурсы
        if self.recipe.get("civilian_inputs"):
            civ_text = ""
            for resource, amount in self.recipe["civilian_inputs"].items():
                resource_names = {
                    "cars": "🚗 Автомобили",
                    "trucks": "🚚 Грузовики",
                    "steel": "⚙️ Сталь",
                    "aluminum": "🛩️ Алюминий",
                    "electronics": "💻 Электроника"
                }
                civ_text += f"• {resource_names.get(resource, resource)}: {amount}\n"
            embed.add_field(name="Гражданские ресурсы", value=civ_text, inline=True)
        
        # Военные ресурсы
        if self.recipe.get("military_inputs"):
            mil_text = ""
            for mil_resource, amount in self.recipe["military_inputs"].items():
                if mil_resource == "equipment.small_arms":
                    mil_text += f"• 🔫 Стрелковое оружие: {amount}\n"
                elif mil_resource == "equipment.manpads":
                    mil_text += f"• 🚀 ПЗРК: {amount}\n"
                else:
                    mil_text += f"• {mil_resource}: {amount}\n"
            embed.add_field(name="Военные ресурсы", value=mil_text, inline=True)
        
        # Результат
        output = self.recipe["military_output"]
        quality = output["quality_modifier"] * 100
        output_names = {
            "ground.armored_vehicles": "Бронеавтомобили",
            "ground.btr": "БТР",
            "ground.short_range_air_defense": "ПВО малой дальности",
            "ground.towed_artillery": "Буксируемая артиллерия",
            "equipment.fpv_drones": "FPV-дроны",
            "air.kamikaze_drones": "Дроны-камикадзе"
        }
        
        embed.add_field(
            name="Результат",
            value=f"📦 **{output_names.get(output['type'], output['type'])}** x{output['quantity']}\n"
                  f"⚡ Качество: {quality:.0f}% от стандартного",
            inline=True
        )
        
        embed.add_field(
            name="Детали",
            value=f"🏭 Требуется фабрик: {self.recipe['required_civ_factories']}\n"
                  f"⏱️ Время: {self.recipe['duration_hours']} ч\n"
                  f"⚡ Полит. власть: {self.recipe['pp_cost']}",
            inline=False
        )
        
        embed.add_field(
            name="Регион",
            value=region,
            inline=True
        )
        
        view = ConfirmationView(
            self.user_id, self.country_name, region,
            self.recipe_id, self.recipe
        )
        
        await interaction.response.edit_message(embed=embed, view=view)


class RecipeSelect(Select):
    """Выбор рецепта мобилизации"""
    
    def __init__(self, user_id, country_name, available_recipes, original_message):
        self.user_id = user_id
        self.country_name = country_name
        self.available_recipes = available_recipes
        self.original_message = original_message
        
        options = []
        for recipe_id in available_recipes:
            recipe = MOBILIZATION_RECIPES[recipe_id]
            options.append(
                discord.SelectOption(
                    label=recipe['name'],
                    description=recipe['description'][:50],
                    value=recipe_id
                )
            )
        
        super().__init__(
            placeholder="Выберите тип продукции...",
            min_values=1,
            max_values=1,
            options=options[:25]
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        recipe_id = self.values[0]
        recipe = MOBILIZATION_RECIPES[recipe_id]
        
        # Получаем регионы страны
        infra = load_infrastructure()
        country_id = None
        
        for cid, data in infra["infrastructure"].items():
            if data.get("country") == self.country_name:
                country_id = cid
                break
        
        if not country_id:
            await interaction.response.send_message("❌ Данные инфраструктуры не найдены!", ephemeral=True)
            return
        
        regions = {}
        country_data = infra["infrastructure"][country_id]
        for econ_region, econ_data in country_data.get("economic_regions", {}).items():
            regions.update(econ_data.get("regions", {}))
        
        embed = discord.Embed(
            title=f"Выбор региона для {recipe['name']}",
            description="Выберите регион с достаточным количеством гражданских фабрик",
            color=DARK_THEME_COLOR
        )
        
        select = RegionSelect(
            self.user_id, self.country_name, regions,
            recipe_id, recipe, interaction.message
        )
        view = View(timeout=120)
        view.add_item(select)
        
        await interaction.response.edit_message(embed=embed, view=view)


class ConfirmationView(View):
    """Подтверждение запуска мобилизации"""
    
    def __init__(self, user_id, country_name, region, recipe_id, recipe):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.country_name = country_name
        self.region = region
        self.recipe_id = recipe_id
        self.recipe = recipe
    
    @discord.ui.button(label="✅ Запустить производство", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        states = load_states()
        
        player_data = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(self.user_id):
                player_data = data
                break
        
        if not player_data:
            await interaction.response.send_message("❌ Данные игрока не найдены!", ephemeral=True)
            return
        
        # Проверяем требования еще раз
        check, message = check_mobilization_requirements(player_data, self.recipe_id, self.region)
        if not check:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)
            return
        
        # Списываем ПВ
        spend_political_power(player_data, self.recipe["pp_cost"])
        
        # Списываем ресурсы
        if not consume_mobilization_resources(player_data, self.recipe):
            await interaction.response.send_message("❌ Ошибка при списании ресурсов!", ephemeral=True)
            return
        
        # Добавляем в очередь
        mob_data = load_mobilization()
        
        completion_time = datetime.now() + timedelta(hours=self.recipe["duration_hours"])
        
        program = {
            "id": len(mob_data["active_programs"]) + 1,
            "user_id": str(self.user_id),
            "country": self.country_name,
            "region": self.region,
            "recipe_id": self.recipe_id,
            "recipe_name": self.recipe["name"],
            "civilian_inputs": self.recipe.get("civilian_inputs", {}),
            "military_inputs": self.recipe.get("military_inputs", {}),
            "output": self.recipe["military_output"],
            "pp_cost": self.recipe["pp_cost"],
            "start_time": str(datetime.now()),
            "completion_time": str(completion_time),
            "status": "in_progress",
            "notified": False
        }
        
        mob_data["active_programs"].append(program)
        save_mobilization(mob_data)
        save_states(states)
        
        embed = discord.Embed(
            title="✅ Мобилизация запущена!",
            description=f"**{self.recipe['name']}** в регионе **{self.region}**",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Готовность",
            value=f"⏱️ {self.recipe['duration_hours']} часов",
            inline=True
        )
        
        embed.add_field(
            name="ID программы",
            value=str(program['id']),
            inline=True
        )
        
        output = self.recipe["military_output"]
        output_names = {
            "ground.armored_vehicles": "Бронеавтомобили",
            "ground.btr": "БТР",
            "ground.short_range_air_defense": "ПВО малой дальности",
            "ground.towed_artillery": "Гаубица",
            "equipment.fpv_drones": "FPV-дроны",
            "air.kamikaze_drones": "Дроны-камикадзе"
        }
        
        embed.add_field(
            name="Результат",
            value=f"📦 {output_names.get(output['type'], output['type'])} x{output['quantity']}",
            inline=True
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Мобилизация отменена",
            color=DARK_THEME_COLOR
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ==================== ОСНОВНОЕ МЕНЮ ====================

async def show_mobilization_menu(ctx, user_id: int):
    """Показать меню мобилизации"""
    
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
    
    # Статистика мобилизации населения
    mobilization_possible = calculate_mobilization_possible(player_data)
    
    # 🔍 ОТЛАДКА: выведем в консоль, что есть у игрока
    print(f"\n=== ОТЛАДКА МОБИЛИЗАЦИИ для {country_name} ===")
    print(f"Политическая власть: {current_pp}")
    print(f"Ресурсы (!ресурсы): {player_data.get('resources', {})}")
    print(f"Гражданские товары (!товары): {player_data.get('civil_goods', {})}")
    
    small_arms = player_data.get("army", {}).get("equipment", {}).get("small_arms", 0)
    manpads = player_data.get("army", {}).get("equipment", {}).get("manpads", 0)
    print(f"Стрелковое оружие: {small_arms}")
    print(f"ПЗРК: {manpads}")
    
    # Фильтруем доступные рецепты промышленной мобилизации
    available_recipes = []
    
    for recipe_id, recipe in MOBILIZATION_RECIPES.items():
        print(f"\nПроверка рецепта: {recipe['name']}")
        recipe_ok = True
        
        # Проверяем наличие гражданских ресурсов через get_resource_amount
        for resource, amount in recipe.get("civilian_inputs", {}).items():
            available = get_resource_amount(player_data, resource)
            print(f"  {resource}: нужно {amount}, есть {available}")
            if available < amount:
                recipe_ok = False
        
        # Проверяем наличие военных ресурсов
        if recipe_ok:
            for mil_resource, amount in recipe.get("military_inputs", {}).items():
                if mil_resource == "equipment.small_arms":
                    print(f"  стрелковое оружие: нужно {amount}, есть {small_arms}")
                    if small_arms < amount:
                        recipe_ok = False
                
                elif mil_resource == "equipment.manpads":
                    print(f"  ПЗРК: нужно {amount}, есть {manpads}")
                    if manpads < amount:
                        recipe_ok = False
        
        # Проверяем ПВ
        pp_ok = current_pp >= recipe["pp_cost"]
        print(f"  ПВ: нужно {recipe['pp_cost']}, есть {current_pp:.1f} - {'✅' if pp_ok else '❌'}")
        
        if recipe_ok and pp_ok:
            available_recipes.append(recipe_id)
            print(f"  ✅ РЕЦЕПТ ДОСТУПЕН")
        else:
            print(f"  ❌ РЕЦЕПТ НЕДОСТУПЕН")
    
    print(f"\nИТОГ: доступно {len(available_recipes)} рецептов")
    
    # Создаем embed
    embed = discord.Embed(
        title="Мобилизация",
        description="Мобилизация населения и конверсия гражданской промышленности",
        color=DARK_THEME_COLOR
    )
    
    # Секция мобилизации населения
    embed.add_field(
        name="Мобилизация населения",
        value=f"Текущая армия: {format_number(mobilization_possible['current_army'])} чел.\n"
              f"Резервисты (3.4%): {format_number(mobilization_possible['reservists'])} чел.\n"
              f"Стрелковое оружие: {format_number(mobilization_possible['small_arms_available'])} ед.\n"
              f"Можно мобилизовать: {format_number(mobilization_possible['max_possible'])} чел.",
        inline=False
    )
    
    # Доступные гражданские ресурсы
    res_text = ""
    resource_names = {
        "cars": "Автомобили (из !товары)",
        "trucks": "Грузовики (из !товары)",
        "steel": "Сталь (из !ресурсы)",
        "aluminum": "Алюминий (из !ресурсы)",
        "electronics": "Электроника (из !ресурсы)"
    }

    for res, name in resource_names.items():
        amount = get_resource_amount(player_data, res)
        if amount > 0:
            res_text += f"• {name}: {amount:.2f} ед.\n"

    embed.add_field(
        name="Гражданские ресурсы",
        value=res_text or "Нет ресурсов",
        inline=True
    )
    
    # Военные ресурсы
    mil_text = ""
    mil_text += f"• Стрелковое оружие: {format_number(small_arms)} ед.\n"
    mil_text += f"• ПЗРК: {format_number(manpads)} ед.\n"
    
    embed.add_field(
        name="Военные ресурсы",
        value=mil_text,
        inline=True
    )
    
    embed.add_field(
        name="Политическая власть",
        value=f"{current_pp:.1f} ПВ",
        inline=True
    )
    
    embed.add_field(
        name="Доступно рецептов",
        value=str(len(available_recipes)),
        inline=True
    )
    
    # Отправляем с кнопками
    if hasattr(ctx, 'response'):
        await ctx.response.send_message(embed=embed, ephemeral=True)
        message = await ctx.original_response()
    else:
        message = await ctx.send(embed=embed, ephemeral=True)
    
    # Создаем View с кнопками
    view = MobilizationMainView(user_id, player_data, available_recipes, country_name, message)
    await message.edit(view=view)


class MobilizationMainView(View):
    """Главное меню мобилизации с кнопками"""
    
    def __init__(self, user_id, player_data, available_recipes, country_name, original_message):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.player_data = player_data
        self.available_recipes = available_recipes
        self.country_name = country_name
        self.original_message = original_message
    
    @discord.ui.button(label="Мобилизовать население", style=discord.ButtonStyle.secondary)
    async def mobilize_population_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        possible = calculate_mobilization_possible(self.player_data)
        
        if possible['max_possible'] <= 0:
            await interaction.response.send_message(
                "❌ Некого мобилизовать! Нет резервистов или оружия.",
                ephemeral=True
            )
            return
        
        modal = MobilizationModal(self.user_id, self.player_data)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Промышленная мобилизация", style=discord.ButtonStyle.secondary)
    async def industrial_mobilization_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        if not self.available_recipes:
            await interaction.response.send_message(
                "❌ Нет доступных рецептов! Не хватает ресурсов или ПВ.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="Промышленная мобилизация",
            description="Выберите тип продукции для производства",
            color=DARK_THEME_COLOR
        )
        
        select = RecipeSelect(self.user_id, self.country_name, self.available_recipes, interaction.message)
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
        
        await show_mobilization_menu(interaction, self.user_id)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_mobilization_menu',
    'mobilization_completion_loop',
    'MOBILIZATION_RECIPES'
]

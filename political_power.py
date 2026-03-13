# political_power.py - Модуль для управления политической властью

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import random
import math
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

# Файлы для хранения данных
STATES_FILE = 'states.json'
LAWS_FILE = 'political_laws.json'

# Цвет для эмбедов в тёмной теме Discord
DARK_THEME_COLOR = 0x2b2d31

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
    data["last_update"] = str(datetime.now())
    with open(STATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_laws():
    """Загрузка активных законопроектов"""
    try:
        with open(LAWS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"active_laws": [], "passed_laws": [], "failed_laws": []}
            return json.loads(content)
    except FileNotFoundError:
        return {"active_laws": [], "passed_laws": [], "failed_laws": []}
    except json.JSONDecodeError:
        return {"active_laws": [], "passed_laws": [], "failed_laws": []}

def save_laws(data):
    """Сохранение законопроектов"""
    with open(LAWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_player_state(user_id):
    """Получить государство игрока"""
    states = load_states()
    for state_id, data in states["players"].items():
        if data.get("assigned_to") == str(user_id):
            return state_id, data
    return None, None

def get_political_power(state_data):
    """Получить текущее значение политической власти"""
    politics = state_data.get("politics", {})
    return politics.get("political_power", 0)

def set_political_power(state_data, value):
    """Установить значение политической власти"""
    if "politics" not in state_data:
        state_data["politics"] = {}
    state_data["politics"]["political_power"] = max(0, value)
    return state_data

def add_political_power(state_data, amount):
    """Добавить политическую власть"""
    current = get_political_power(state_data)
    new_value = max(0, current + amount)
    set_political_power(state_data, new_value)
    return state_data, new_value - current

def spend_political_power(state_data, amount):
    """Потратить политическую власть (проверяет достаточно ли)"""
    current = get_political_power(state_data)
    if current >= amount:
        new_value = current - amount
        set_political_power(state_data, new_value)
        return True, new_value
    return False, current

# ==================== КЛАССЫ ДЛЯ ПАРЛАМЕНТА ====================

class Parliament:
    """Класс, представляющий парламент страны"""
    
    def __init__(self, state_data):
        self.state_data = state_data
        self.country_name = state_data["state"]["statename"]
        self.parliament_data = state_data["politics"]["parliament"]
        
        # Определяем тип парламента
        self.is_unicameral = self._check_if_unicameral()
        
        if self.is_unicameral:
            # Однопалатный парламент
            self.chamber_name, self.chamber_seats = self._get_unicameral_info()
            self.total_seats = self.chamber_seats
        else:
            # Двухпалатный парламент
            self.upper_name, self.upper_seats = self._get_chamber_info(is_upper=True)
            self.lower_name, self.lower_seats = self._get_chamber_info(is_upper=False)
            self.total_seats = self.upper_seats + self.lower_seats
        
        self.ruling_party = state_data["politics"]["ruling_party"]
        self.government_stability = state_data["state"].get("stability", 50)
        self.popularity = state_data["politics"].get("popularity", 50)
        self.political_power = get_political_power(state_data)
    
    def _check_if_unicameral(self) -> bool:
        """Проверяет, является ли парламент однопалатным"""
        # Ключи для двухпалатного парламента
        upper_keys = ["upper_house", "senate", "federation_council", "bundesrat", "standing_committee"]
        lower_keys = ["lower_house", "duma", "bundestag", "house", "verkhovna_rada", "knesset", "majlis", "national_people_congress"]
        
        has_upper = any(key in self.parliament_data for key in upper_keys)
        has_lower = any(key in self.parliament_data for key in lower_keys)
        
        # Страны с заведомо однопалатным парламентом
        unicameral_countries = ["Украина", "Израиль", "Иран", "Китай"]
        
        if self.country_name in unicameral_countries:
            return True
        
        # Если есть только один тип ключей, то скорее всего однопалатный
        return not (has_upper and has_lower)
    
    def _get_unicameral_info(self) -> tuple:
        """Получает название и количество мест для однопалатного парламента"""
        # Названия однопалатных парламентов по странам
        names = {
            "Украина": "Верховна Рада",
            "Израиль": "Кнессет",
            "Иран": "Меджлис",
            "Китай": "Всекитайское собрание",
            "default": "Парламент"
        }
        
        name = names.get(self.country_name, names["default"])
        seats = 0
        
        # Ищем количество мест
        for key, value in self.parliament_data.items():
            if isinstance(value, int):
                seats = value
                # Если ключ содержит название, используем его
                if key in ["verkhovna_rada", "knesset", "majlis", "national_people_congress"]:
                    name = names.get(self.country_name, name)
                break
        
        return name, seats
    
    def _get_chamber_info(self, is_upper: bool) -> tuple:
        """Получает название и количество мест для палаты двухпалатного парламента"""
        if is_upper:
            keys = ["upper_house", "senate", "federation_council", "bundesrat", "standing_committee"]
            default_name = "Верхняя палата"
            names = {
                "senate": "Сенат",
                "federation_council": "Совет Федерации",
                "bundesrat": "Бундесрат",
                "standing_committee": "Постоянный комитет"
            }
        else:
            keys = ["lower_house", "duma", "bundestag", "house", "verkhovna_rada", "knesset", "majlis", "national_people_congress"]
            default_name = "Нижняя палата"
            names = {
                "duma": "Государственная Дума",
                "bundestag": "Бундестаг",
                "house": "Палата представителей",
                "verkhovna_rada": "Верховна Рада",
                "knesset": "Кнессет",
                "majlis": "Меджлис",
                "national_people_congress": "Всекитайское собрание"
            }
        
        for key in keys:
            if key in self.parliament_data:
                return names.get(key, default_name), self.parliament_data[key]
        
        return default_name, 0
    
    def calculate_pass_chance(self, law_cost, law_type):
        """
        Рассчитывает шанс прохождения закона через парламент
        """
        base_chance = 50
        
        # Влияние стабильности
        stability_mod = (self.government_stability - 50) / 2
        
        # Влияние популярности
        popularity_mod = (self.popularity - 50) / 2
        
        # Влияние типа закона
        type_modifiers = {
            "economic": 0,
            "military": -5,
            "social": 5,
            "foreign": -10,
            "constitutional": -20
        }
        type_mod = type_modifiers.get(law_type, 0)
        
        # Влияние стоимости (чем дороже закон, тем сложнее провести)
        cost_mod = -min(20, law_cost / 10)
        
        # Штраф для двухпалатного парламента (сложнее провести закон)
        bicameral_penalty = -5 if not self.is_unicameral else 0
        
        total_chance = base_chance + stability_mod + popularity_mod + type_mod + cost_mod + bicameral_penalty
        
        return max(5, min(95, total_chance))
    
    def simulate_vote(self, law_cost, law_type):
        """
        Симулирует голосование в парламенте
        Возвращает (прошло_ли, результат_голосования)
        """
        chance = self.calculate_pass_chance(law_cost, law_type)
        roll = random.randint(1, 100)
        
        if roll <= chance:
            return True, f"Закон принят! За: {chance:.0f}%, Против: {100-chance:.0f}%"
        else:
            return False, f"Закон отклонён! За: {chance:.0f}%, Против: {100-chance:.0f}%"

# ==================== КЛАСС ЗАКОНОПРОЕКТА ====================

class LawProposal:
    """Класс, представляющий законопроект"""
    
    def __init__(self, law_id, name, description, pp_cost, law_type,
                 cooldown_days, requirements, effects, duration_days=None):
        self.id = law_id
        self.name = name
        self.description = description
        self.pp_cost = pp_cost
        self.law_type = law_type
        self.cooldown_days = cooldown_days
        self.requirements = requirements or {}
        self.effects = effects or {}
        self.duration_days = duration_days
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pp_cost": self.pp_cost,
            "law_type": self.law_type,
            "cooldown_days": self.cooldown_days,
            "requirements": self.requirements,
            "effects": self.effects,
            "duration_days": self.duration_days
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            data["id"], data["name"], data["description"],
            data["pp_cost"], data["law_type"],
            data.get("cooldown_days", 0),
            data.get("requirements", {}),
            data.get("effects", {}),
            data.get("duration_days")
        )

# ==================== БАЗА ДАННЫХ ЗАКОНОВ ====================

POLITICAL_LAWS = {
    # Налоговые законы
    "tax_increase_small": LawProposal(
        "tax_increase_small",
        "Небольшое повышение налогов",
        "Увеличить налоговую ставку на 2%. Это позволит получить больше доходов, но снизит счастье населения.",
        30,
        "economic",
        60,
        {"max_tax": 35},
        {"tax_change": 2, "happiness_penalty": 1}
    ),
    
    "tax_increase_medium": LawProposal(
        "tax_increase_medium",
        "Умеренное повышение налогов",
        "Увеличить налоговую ставку на 5%. Значительно увеличит доходы, но сильно ударит по населению.",
        60,
        "economic",
        120,
        {"max_tax": 40},
        {"tax_change": 5, "happiness_penalty": 3}
    ),
    
    "tax_decrease_small": LawProposal(
        "tax_decrease_small",
        "Небольшое снижение налогов",
        "Уменьшить налоговую ставку на 2%. Это повысит счастье населения, но снизит доходы.",
        30,
        "economic",
        60,
        {"min_tax": 10},
        {"tax_change": -2, "happiness_bonus": 1}
    ),
    
    "tax_decrease_medium": LawProposal(
        "tax_decrease_medium",
        "Умеренное снижение налогов",
        "Уменьшить налоговую ставку на 5%. Сильно повысит счастье, но значительно снизит доходы.",
        60,
        "economic",
        120,
        {"min_tax": 5},
        {"tax_change": -5, "happiness_bonus": 3}
    ),
    
    "tax_reform": LawProposal(
        "tax_reform",
        "Налоговая реформа",
        "Комплексная реформа налоговой системы. Позволяет увеличить собираемость налогов без повышения ставок.",
        100,
        "economic",
        180,
        {"min_stability": 60},
        {"tax_efficiency": 10, "government_efficiency": 5}
    ),
    
    # Военные законы
    "military_increase_small": LawProposal(
        "military_increase_small",
        "Небольшое увеличение военного бюджета",
        "Увеличить военный бюджет на 10%. Позволит модернизировать армию.",
        25,
        "military",
        45,
        {},
        {"military_budget_change": 10}
    ),
    
    "military_increase_medium": LawProposal(
        "military_increase_medium",
        "Умеренное увеличение военного бюджета",
        "Увеличить военный бюджет на 25%. Значительно усилит армию, но может вызвать недовольство.",
        50,
        "military",
        90,
        {},
        {"military_budget_change": 25, "happiness_penalty": 2}
    ),
    
    "military_decrease_small": LawProposal(
        "military_decrease_small",
        "Небольшое сокращение военного бюджета",
        "Уменьшить военный бюджет на 10%. Освободит средства для других нужд.",
        20,
        "military",
        45,
        {},
        {"military_budget_change": -10}
    ),
    
    "military_decrease_medium": LawProposal(
        "military_decrease_medium",
        "Умеренное сокращение военного бюджета",
        "Уменьшить военный бюджет на 25%. Сильно сократит военные расходы, но ослабит армию.",
        40,
        "military",
        90,
        {},
        {"military_budget_change": -25, "army_experience_penalty": 3}
    ),
    
    "conscription": LawProposal(
        "conscription",
        "Закон о воинской повинности",
        "Ввести обязательную военную службу. Увеличит численность армии, но снизит счастье.",
        60,
        "military",
        180,
        {},
        {"manpower_increase": 20, "happiness_penalty": 5, "army_experience_bonus": 2}
    ),
    
    "professional_army": LawProposal(
        "professional_army",
        "Профессиональная армия",
        "Перейти на контрактную основу. Повысит качество армии, но уменьшит её численность.",
        80,
        "military",
        180,
        {},
        {"manpower_decrease": 15, "army_experience_bonus": 10, "military_budget_increase": 15}
    ),
    
    # Социальные законы
    "healthcare_increase": LawProposal(
        "healthcare_increase",
        "Увеличение финансирования здравоохранения",
        "Увеличить бюджет здравоохранения на 20%. Повысит здоровье нации и счастье.",
        40,
        "social",
        90,
        {},
        {"healthcare_budget_increase": 20, "happiness_bonus": 3, "population_growth_bonus": 0.2}
    ),
    
    "education_increase": LawProposal(
        "education_increase",
        "Увеличение финансирования образования",
        "Увеличить бюджет образования на 20%. Повысит качество рабочей силы и исследования.",
        40,
        "social",
        90,
        {},
        {"education_budget_increase": 20, "research_speed_bonus": 5}
    ),
    
    "pension_reform": LawProposal(
        "pension_reform",
        "Пенсионная реформа",
        "Изменить пенсионную систему. Сложный закон с долгосрочными последствиями.",
        120,
        "social",
        365,
        {"min_stability": 55},
        {"pension_age_increase": 2, "budget_saving": 15, "happiness_penalty": 8}
    ),
    
    "social_welfare": LawProposal(
        "social_welfare",
        "Программа социальной поддержки",
        "Расширить программу социальной помощи малоимущим.",
        50,
        "social",
        120,
        {},
        {"social_budget_increase": 15, "happiness_bonus": 5, "stability_bonus": 3}
    ),
    
    # Экономические законы
    "economic_stimulus": LawProposal(
        "economic_stimulus",
        "Пакет экономического стимулирования",
        "Государственные инвестиции в экономику для ускорения роста.",
        70,
        "economic",
        150,
        {"min_budget": 500000000000},
        {"gdp_growth_bonus": 2, "budget_cost": 0.5, "duration_days": 365}
    ),
    
    "austerity": LawProposal(
        "austerity",
        "Режим экономии",
        "Сократить государственные расходы для уменьшения дефицита бюджета.",
        60,
        "economic",
        120,
        {},
        {"expense_reduction": 15, "happiness_penalty": 5, "stability_penalty": 3}
    ),
    
    "trade_agreement": LawProposal(
        "trade_agreement",
        "Новое торговое соглашение",
        "Заключить выгодное торговое соглашение с другими странами.",
        40,
        "foreign",
        90,
        {},
        {"trade_income_bonus": 15, "relations_bonus": 5}
    ),
    
    # Конституционные законы
    "constitutional_amendment": LawProposal(
        "constitutional_amendment",
        "Конституционная поправка",
        "Изменить конституцию. Очень сложный и длительный процесс.",
        200,
        "constitutional",
        730,
        {"min_stability": 70, "min_popularity": 60},
        {"political_power_gain_bonus": 0.2, "stability_bonus": 5, "government_efficiency": 5}
    ),
    
    "electoral_reform": LawProposal(
        "electoral_reform",
        "Избирательная реформа",
        "Изменить избирательную систему. Может сильно повлиять на политический ландшафт.",
        150,
        "constitutional",
        365,
        {"min_stability": 65},
        {"popularity_bonus": 5, "stability_bonus": 3, "duration_days": 365}
    ),
    
    "anti_corruption": LawProposal(
        "anti_corruption",
        "Антикоррупционная кампания",
        "Ужесточить наказания за коррупцию и создать независимые антикоррупционные органы.",
        80,
        "social",
        180,
        {},
        {"government_efficiency": 10, "stability_bonus": 5, "popularity_bonus": 8}
    ),
    
    "central_bank_independence": LawProposal(
        "central_bank_independence",
        "Независимость центрального банка",
        "Предоставить центральному банку больше независимости в монетарной политике.",
        90,
        "economic",
        270,
        {},
        {"inflation_control": 10, "stability_bonus": 3}
    )
}

# ==================== ФУНКЦИИ ДЛЯ ПОЛУЧЕНИЯ ИНФОРМАЦИИ О ПАРЛАМЕНТЕ ====================

async def get_parliament_composition(state_data: Dict) -> str:
    """
    Возвращает строку с описанием состава парламента
    Поддерживает как двухпалатные, так и однопалатные парламенты
    """
    parliament = Parliament(state_data)
    
    if parliament.is_unicameral:
        return await get_unicameral_composition(parliament)
    else:
        return await get_bicameral_composition(parliament)

async def get_unicameral_composition(parliament: Parliament) -> str:
    """Формирует описание для однопалатного парламента"""
    
    # Рассчитываем состав
    coalition_size = 50 + (parliament.popularity - 50) / 2 + (parliament.government_stability - 50) / 2
    coalition_size = max(30, min(70, coalition_size))
    
    coalition = round(parliament.chamber_seats * coalition_size / 100)
    opposition = parliament.chamber_seats - coalition
    
    result = f"**{parliament.chamber_name}** (однопалатный, {parliament.chamber_seats} мест)\n"
    result += f"• Правительство: {coalition} мест\n"
    result += f"• Оппозиция: {opposition} мест\n\n"
    
    if coalition > parliament.chamber_seats / 2:
        result += "✅ **Правительство имеет большинство**"
    else:
        result += "⚠️ **Правительство не имеет большинства**"
    
    return result

async def get_bicameral_composition(parliament: Parliament) -> str:
    """Формирует описание для двухпалатного парламента"""
    
    # Рассчитываем коалицию
    coalition_size = 50 + (parliament.popularity - 50) / 2 + (parliament.government_stability - 50) / 2
    coalition_size = max(30, min(70, coalition_size))
    
    upper_coalition = round(parliament.upper_seats * coalition_size / 100)
    upper_opposition = parliament.upper_seats - upper_coalition
    lower_coalition = round(parliament.lower_seats * coalition_size / 100)
    lower_opposition = parliament.lower_seats - lower_coalition
    
    result = f"**{parliament.upper_name}** (верхняя палата, {parliament.upper_seats} мест)\n"
    result += f"• Правительство: {upper_coalition} мест\n"
    result += f"• Оппозиция: {upper_opposition} мест\n\n"
    result += f"**{parliament.lower_name}** (нижняя палата, {parliament.lower_seats} мест)\n"
    result += f"• Правительство: {lower_coalition} мест\n"
    result += f"• Оппозиция: {lower_opposition} мест\n\n"
    
    if lower_coalition > parliament.lower_seats / 2:
        result += "✅ **Правительство имеет большинство в нижней палате**"
    else:
        result += "⚠️ **Правительство не имеет большинства в нижней палате**"
    
    return result

# ==================== КЛАССЫ ДЛЯ ИНТЕРФЕЙСА ====================

class LawSelect(Select):
    """Выбор закона для внесения"""
    
    def __init__(self, user_id: int, state_data: Dict, available_laws: List[str], original_message):
        self.user_id = user_id
        self.state_data = state_data
        self.original_message = original_message
        options = []
        
        for law_id in available_laws[:25]:
            if law_id in POLITICAL_LAWS:
                law = POLITICAL_LAWS[law_id]
                current_pp = get_political_power(state_data)
                can_afford = current_pp >= law.pp_cost
                
                options.append(
                    discord.SelectOption(
                        label=law.name,
                        description=f"Стоимость: {law.pp_cost} ПВ | Тип: {law.law_type}",
                        value=law_id
                    )
                )
        
        super().__init__(
            placeholder="Выберите законопроект...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        law_id = self.values[0]
        law = POLITICAL_LAWS.get(law_id)
        
        if not law:
            await interaction.response.send_message("❌ Закон не найден!", ephemeral=True)
            return
        
        # Проверяем требования
        check_result, check_message = await check_requirements(self.state_data, law)
        if not check_result:
            await interaction.response.send_message(f"❌ {check_message}", ephemeral=True)
            return
        
        # Проверяем, достаточно ли политической власти
        current_pp = get_political_power(self.state_data)
        if current_pp < law.pp_cost:
            await interaction.response.send_message(
                f"❌ Недостаточно политической власти! Нужно: {law.pp_cost}, у вас: {current_pp:.1f}",
                ephemeral=True
            )
            return
        
        # Удаляем текущее сообщение
        try:
            await self.original_message.delete()
        except:
            pass
        
        # Показываем подтверждение с информацией о парламенте
        parliament = Parliament(self.state_data)
        pass_chance = parliament.calculate_pass_chance(law.pp_cost, law.law_type)
        
        view = LawConfirmationView(self.user_id, self.state_data, law, pass_chance)
        
        embed = discord.Embed(
            title=law.name,
            description=law.description,
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Стоимость", value=f"{law.pp_cost} ПВ", inline=True)
        embed.add_field(name="Тип", value=law.law_type, inline=True)
        embed.add_field(name="Перезарядка", value=f"{law.cooldown_days} дней", inline=True)
        embed.add_field(name="Шанс принятия", value=f"{pass_chance:.0f}%", inline=True)
        
        # Показываем эффекты
        effects_text = format_effects_description(law.effects)
        if effects_text:
            embed.add_field(name="Эффекты", value=effects_text, inline=False)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class LawConfirmationView(View):
    """Подтверждение внесения законопроекта"""
    
    def __init__(self, user_id: int, state_data: Dict, law: LawProposal, pass_chance: float):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.state_data = state_data
        self.law = law
        self.pass_chance = pass_chance
    
    @discord.ui.button(label="Внести в парламент", style=discord.ButtonStyle.secondary)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Проверяем еще раз наличие средств
        current_pp = get_political_power(self.state_data)
        if current_pp < self.law.pp_cost:
            await interaction.response.send_message(
                f"❌ Недостаточно политической власти!",
                ephemeral=True
            )
            return
        
        # Списываем политическую власть
        success, new_value = spend_political_power(self.state_data, self.law.pp_cost)
        if not success:
            await interaction.response.send_message("❌ Ошибка при списании ПВ!", ephemeral=True)
            return
        
        # Симулируем голосование в парламенте
        parliament = Parliament(self.state_data)
        passed, vote_result = parliament.simulate_vote(self.law.pp_cost, self.law.law_type)
        
        # Сохраняем в очередь законопроектов
        laws = load_laws()
        
        law_entry = {
            "id": len(laws["passed_laws"]) + len(laws["failed_laws"]) + 1,
            "user_id": str(self.user_id),
            "law_id": self.law.id,
            "law_name": self.law.name,
            "pp_cost": self.law.pp_cost,
            "submitted_at": str(datetime.now()),
            "vote_result": vote_result,
            "passed": passed,
            "effects": self.law.effects
        }
        
        if passed:
            # Закон принят - применяем эффекты
            await apply_law_effects(self.state_data, self.law)
            law_entry["status"] = "passed"
            law_entry["passed_at"] = str(datetime.now())
            laws["passed_laws"].append(law_entry)
        else:
            # Закон отклонён
            law_entry["status"] = "failed"
            law_entry["failed_at"] = str(datetime.now())
            laws["failed_laws"].append(law_entry)
        
        save_laws(laws)
        
        # Сохраняем изменения государства
        states = load_states()
        for sid, data in states["players"].items():
            if data.get("assigned_to") == str(self.user_id):
                states["players"][sid] = self.state_data
                break
        save_states(states)
        
        # Удаляем текущее сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        # Создаём embed с результатом
        embed = discord.Embed(
            title="Результат голосования",
            description=vote_result,
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Закон", value=self.law.name, inline=True)
        embed.add_field(name="Потрачено", value=f"{self.law.pp_cost} ПВ", inline=True)
        embed.add_field(name="Осталось ПВ", value=f"{new_value:.1f}", inline=True)
        
        if passed:
            effects_text = format_effects_description(self.law.effects)
            if effects_text:
                embed.add_field(name="Принятые изменения", value=effects_text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Удаляем текущее сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        embed = discord.Embed(
            title="Действие отменено",
            color=DARK_THEME_COLOR
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PoliticalPowerView(View):
    """Главное меню политической власти"""
    
    def __init__(self, user_id: int, state_id: str, state_data: Dict, original_message):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.state_id = state_id
        self.state_data = state_data
        self.original_message = original_message
    
    @discord.ui.button(label="Текущая власть", style=discord.ButtonStyle.secondary)
    async def status_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        current_pp = get_political_power(self.state_data)
        gain = self.state_data.get("politics", {}).get("political_power_gain", 2.0)
        
        # Расчет модификаторов
        stability = self.state_data["state"].get("stability", 50)
        gov_efficiency = self.state_data.get("government_efficiency", 50)
        
        stability_mod = (stability - 50) / 250
        efficiency_mod = (gov_efficiency - 50) / 250
        
        total_gain = gain * (1 + stability_mod + efficiency_mod)
        total_gain = max(0.5, min(5.0, total_gain))
        
        embed = discord.Embed(
            title="Политическая власть",
            description=f"Государство: **{self.state_data['state']['statename']}**",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(name="Текущий запас", value=f"{current_pp:.1f} ПВ", inline=True)
        embed.add_field(name="Ежедневный прирост", value=f"+{total_gain:.2f} ПВ/день", inline=True)
        
        # Информация о парламенте
        parliament = Parliament(self.state_data)
        
        if parliament.is_unicameral:
            embed.add_field(
                name="Парламент", 
                value=f"{parliament.chamber_name} (однопалатный)\n{parliament.chamber_seats} мест", 
                inline=True
            )
        else:
            embed.add_field(
                name="Парламент", 
                value=f"{parliament.upper_name}: {parliament.upper_seats} мест\n{parliament.lower_name}: {parliament.lower_seats} мест", 
                inline=True
            )
        
        gov_type = self.state_data["state"]["government_type"]
        embed.add_field(name="Форма правления", value=gov_type, inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Доступные законы", style=discord.ButtonStyle.secondary)
    async def laws_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Фильтруем доступные законы
        available_laws = []
        current_pp = get_political_power(self.state_data)
        
        for law_id, law in POLITICAL_LAWS.items():
            # Проверяем требования
            check_result, _ = await check_requirements(self.state_data, law, silent=True)
            if check_result:
                available_laws.append(law_id)
        
        embed = discord.Embed(
            title="Доступные законопроекты",
            description=f"У вас **{current_pp:.1f}** ПВ. Выберите закон для внесения в парламент:",
            color=DARK_THEME_COLOR
        )
        
        if available_laws:
            # Удаляем текущее сообщение
            try:
                await self.original_message.delete()
            except:
                pass
            
            select = LawSelect(self.user_id, self.state_data, available_laws, interaction.message)
            view = View(timeout=120)
            view.add_item(select)
            
            # Кнопка назад
            back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
            back_button.callback = self.back_to_main
            view.add_item(back_button)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            embed.add_field(name="Нет доступных законов", value="У вас нет законов, соответствующих требованиям", inline=False)
            await interaction.response.edit_message(embed=embed, view=self)
    
    async def back_to_main(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Удаляем текущее сообщение
        try:
            await interaction.message.delete()
        except:
            pass
        
        embed = discord.Embed(
            title="Политическая власть",
            description=f"Государство: **{self.state_data['state']['statename']}**",
            color=DARK_THEME_COLOR
        )
        
        current_pp = get_political_power(self.state_data)
        embed.add_field(name="Текущий запас", value=f"{current_pp:.1f} ПВ", inline=True)
        
        # Создаём новое главное меню
        view = PoliticalPowerView(self.user_id, self.state_id, self.state_data, interaction.message)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @discord.ui.button(label="История законов", style=discord.ButtonStyle.secondary)
    async def history_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        laws = load_laws()
        user_laws = [l for l in laws["passed_laws"] + laws["failed_laws"] 
                    if l["user_id"] == str(self.user_id)]
        
        if not user_laws:
            embed = discord.Embed(
                title="История законопроектов",
                description="У вас пока нет истории законопроектов",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        embed = discord.Embed(
            title="История законопроектов",
            color=DARK_THEME_COLOR
        )
        
        for law in user_laws[-5:]:
            status_emoji = "✅" if law["passed"] else "❌"
            date = datetime.fromisoformat(law["submitted_at"]).strftime("%d.%m.%Y")
            embed.add_field(
                name=f"{status_emoji} {law['law_name']}",
                value=f"📅 {date}\n{law['vote_result']}",
                inline=False
            )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Парламент", style=discord.ButtonStyle.secondary)
    async def parliament_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        composition = await get_parliament_composition(self.state_data)
        
        embed = discord.Embed(
            title=f"Парламент {self.state_data['state']['statename']}",
            description=composition,
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

# ==================== ФУНКЦИИ ДЛЯ ПРОВЕРКИ ТРЕБОВАНИЙ ====================

async def check_requirements(state_data: Dict, law: LawProposal, silent: bool = False) -> Tuple[bool, str]:
    """Проверить, соответствует ли государство требованиям для закона"""
    
    if "max_tax" in law.requirements:
        current_tax = state_data["economy"].get("tax_rate", 20)
        if current_tax + law.effects.get("tax_change", 0) > law.requirements["max_tax"]:
            return False, f"Максимальная налоговая ставка: {law.requirements['max_tax']}%"
    
    if "min_tax" in law.requirements:
        current_tax = state_data["economy"].get("tax_rate", 20)
        if current_tax + law.effects.get("tax_change", 0) < law.requirements["min_tax"]:
            return False, f"Минимальная налоговая ставка: {law.requirements['min_tax']}%"
    
    if "min_stability" in law.requirements:
        stability = state_data["state"].get("stability", 0)
        if stability < law.requirements["min_stability"]:
            return False, f"Требуется стабильность: {law.requirements['min_stability']}% (у вас {stability}%)"
    
    if "min_popularity" in law.requirements:
        popularity = state_data["politics"].get("popularity", 0)
        if popularity < law.requirements["min_popularity"]:
            return False, f"Требуется популярность: {law.requirements['min_popularity']}% (у вас {popularity}%)"
    
    if "min_budget" in law.requirements:
        budget = state_data["economy"].get("budget", 0)
        if budget < law.requirements["min_budget"]:
            from utils import format_billion
            budget_str = format_billion(law.requirements["min_budget"])
            return False, f"Требуется бюджет: {budget_str}"
    
    return True, "OK"

# ==================== ФУНКЦИИ ДЛЯ ФОРМАТИРОВАНИЯ ЭФФЕКТОВ ====================

def format_effects_description(effects: Dict) -> str:
    """Форматирует описание эффектов для отображения"""
    lines = []
    
    for key, value in effects.items():
        if key == "tax_change":
            lines.append(f"• Налоговая ставка: {value:+}%")
        elif key == "military_budget_change":
            lines.append(f"• Военный бюджет: {value:+}%")
        elif key == "healthcare_budget_increase":
            lines.append(f"• Бюджет здравоохранения: +{value}%")
        elif key == "education_budget_increase":
            lines.append(f"• Бюджет образования: +{value}%")
        elif key == "social_budget_increase":
            lines.append(f"• Социальный бюджет: +{value}%")
        elif key == "happiness_bonus":
            lines.append(f"• Счастье населения: +{value}")
        elif key == "happiness_penalty":
            lines.append(f"• Счастье населения: {value}")
        elif key == "popularity_bonus":
            lines.append(f"• Популярность: +{value}")
        elif key == "stability_bonus":
            lines.append(f"• Стабильность: +{value}")
        elif key == "stability_penalty":
            lines.append(f"• Стабильность: {value}")
        elif key == "government_efficiency":
            lines.append(f"• Эффективность правительства: +{value}%")
        elif key == "army_experience_bonus":
            lines.append(f"• Опытность армии: +{value}")
        elif key == "army_experience_penalty":
            lines.append(f"• Опытность армии: {value}")
        elif key == "manpower_increase":
            lines.append(f"• Мобилизационный резерв: +{value}%")
        elif key == "manpower_decrease":
            lines.append(f"• Мобилизационный резерв: {value}%")
        elif key == "research_speed_bonus":
            lines.append(f"• Скорость исследований: +{value}%")
        elif key == "gdp_growth_bonus":
            lines.append(f"• Рост ВВП: +{value}%")
        elif key == "expense_reduction":
            lines.append(f"• Расходы: -{value}%")
        elif key == "budget_cost":
            lines.append(f"• Стоимость для бюджета: {value}%")
        elif key == "trade_income_bonus":
            lines.append(f"• Доходы от торговли: +{value}%")
        elif key == "tax_efficiency":
            lines.append(f"• Эффективность сбора налогов: +{value}%")
        elif key == "pension_age_increase":
            lines.append(f"• Пенсионный возраст: +{value} лет")
        elif key == "budget_saving":
            lines.append(f"• Экономия бюджета: {value}%")
        elif key == "inflation_control":
            lines.append(f"• Контроль инфляции: +{value}%")
        elif key == "population_growth_bonus":
            lines.append(f"• Рост населения: +{value}%")
        elif key == "duration_days":
            lines.append(f"• Длительность: {value} дней")
        elif key == "political_power_gain_bonus":
            lines.append(f"• Ежедневный прирост ПВ: +{value}")
        elif key == "relations_bonus":
            lines.append(f"• Отношения с другими странами: +{value}")
    
    return "\n".join(lines)

def format_billion(value):
    """Форматирует число для отображения"""
    if value >= 1_000_000_000_000:
        trillions = value / 1_000_000_000_000
        return f"{trillions:.1f} трлн $"
    elif value >= 1_000_000_000:
        billions = value / 1_000_000_000
        return f"{billions:.1f} млрд $"
    elif value >= 1_000_000:
        millions = value / 1_000_000
        return f"{millions:.1f} млн $"
    else:
        return f"{value:,} $".replace(',', ' ')

# ==================== ФУНКЦИИ ДЛЯ ПРИМЕНЕНИЯ ЭФФЕКТОВ ====================

async def apply_law_effects(state_data: Dict, law: LawProposal):
    """Применить эффекты принятого закона"""
    
    for key, value in law.effects.items():
        if key == "tax_change":
            current = state_data["economy"].get("tax_rate", 20)
            new_value = max(0, min(100, current + value))
            state_data["economy"]["tax_rate"] = new_value
            
        elif key == "military_budget_change":
            current = state_data["economy"].get("military_budget", 0)
            change = int(current * abs(value) / 100)
            if value > 0:
                state_data["economy"]["military_budget"] = current + change
            else:
                state_data["economy"]["military_budget"] = max(0, current - change)
            
        elif key == "healthcare_budget_increase":
            if "expenses" not in state_data:
                state_data["expenses"] = {}
            current = state_data["expenses"].get("healthcare", 0)
            change = int(current * value / 100)
            state_data["expenses"]["healthcare"] = current + change
            
        elif key == "education_budget_increase":
            if "expenses" not in state_data:
                state_data["expenses"] = {}
            current = state_data["expenses"].get("education", 0)
            change = int(current * value / 100)
            state_data["expenses"]["education"] = current + change
            
        elif key == "social_budget_increase":
            if "expenses" not in state_data:
                state_data["expenses"] = {}
            current = state_data["expenses"].get("social_security", 0)
            change = int(current * value / 100)
            state_data["expenses"]["social_security"] = current + change
            
        elif key == "happiness_bonus":
            current = state_data["state"].get("happiness", 50)
            state_data["state"]["happiness"] = min(100, current + value)
            
        elif key == "happiness_penalty":
            current = state_data["state"].get("happiness", 50)
            state_data["state"]["happiness"] = max(0, current + value)
            
        elif key == "popularity_bonus":
            current = state_data["politics"].get("popularity", 50)
            state_data["politics"]["popularity"] = min(100, current + value)
            
        elif key == "stability_bonus":
            current = state_data["state"].get("stability", 50)
            state_data["state"]["stability"] = min(100, current + value)
            
        elif key == "stability_penalty":
            current = state_data["state"].get("stability", 50)
            state_data["state"]["stability"] = max(0, current + value)
            
        elif key == "government_efficiency":
            current = state_data.get("government_efficiency", 50)
            state_data["government_efficiency"] = min(100, current + value)
            
        elif key == "army_experience_bonus":
            current = state_data["state"].get("army_experience", 50)
            state_data["state"]["army_experience"] = min(100, current + value)
            
        elif key == "army_experience_penalty":
            current = state_data["state"].get("army_experience", 50)
            state_data["state"]["army_experience"] = max(0, current + value)
            
        elif key == "manpower_increase":
            current = state_data["state"].get("army_size", 0)
            increase = int(current * value / 100)
            state_data["state"]["army_size"] = current + increase
            
        elif key == "manpower_decrease":
            current = state_data["state"].get("army_size", 0)
            decrease = int(current * abs(value) / 100)
            state_data["state"]["army_size"] = max(1000, current - decrease)
            
        elif key == "research_speed_bonus":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            state_data["bonuses"]["research_speed"] = state_data["bonuses"].get("research_speed", 1.0) + value / 100
            
        elif key == "tax_efficiency":
            if "bonuses" not in state_data:
                state_data["bonuses"] = {}
            state_data["bonuses"]["tax_efficiency"] = state_data["bonuses"].get("tax_efficiency", 1.0) + value / 100
            
        elif key == "expense_reduction":
            if "expenses" in state_data:
                for exp_type in state_data["expenses"]:
                    if isinstance(state_data["expenses"][exp_type], (int, float)):
                        reduction = int(state_data["expenses"][exp_type] * value / 100)
                        state_data["expenses"][exp_type] = max(0, state_data["expenses"][exp_type] - reduction)
        
        elif key == "budget_cost":
            budget = state_data["economy"].get("budget", 0)
            cost = int(budget * value / 100)
            state_data["economy"]["budget"] = max(0, budget - cost)
        
        elif key == "political_power_gain_bonus":
            if "politics" not in state_data:
                state_data["politics"] = {}
            current_gain = state_data["politics"].get("political_power_gain", 2.0)
            state_data["politics"]["political_power_gain"] = current_gain + value
    
    return state_data

# ==================== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ====================

async def get_active_laws(user_id: int) -> List[Dict]:
    """Получить активные законопроекты пользователя"""
    laws = load_laws()
    return [l for l in laws["active_laws"] if l["user_id"] == str(user_id)]

async def get_law_history(user_id: int) -> Dict[str, List]:
    """Получить историю законопроектов пользователя"""
    laws = load_laws()
    return {
        "passed": [l for l in laws["passed_laws"] if l["user_id"] == str(user_id)],
        "failed": [l for l in laws["failed_laws"] if l["user_id"] == str(user_id)]
    }

# ==================== ФОНОВАЯ ЗАДАЧА ДЛЯ ОБНОВЛЕНИЯ ПВ ====================

async def political_power_update_loop(bot_instance):
    """Фоновая задача для ежедневного обновления политической власти"""
    await bot_instance.wait_until_ready()
    
    last_update = None
    
    while not bot_instance.is_closed():
        try:
            now = datetime.now()
            
            # Проверяем, прошел ли день (обновляем раз в 24 часа)
            if last_update is None or (now - last_update).days >= 1:
                states = load_states()
                
                for state_id, player_data in states["players"].items():
                    if "assigned_to" not in player_data:
                        continue
                    
                    # Получаем ежедневный прирост
                    gain = player_data.get("politics", {}).get("political_power_gain", 2.0)
                    
                    # Модификаторы прироста
                    stability = player_data["state"].get("stability", 50)
                    gov_efficiency = player_data.get("government_efficiency", 50)
                    
                    stability_mod = (stability - 50) / 250
                    efficiency_mod = (gov_efficiency - 50) / 250
                    
                    total_gain = gain * (1 + stability_mod + efficiency_mod)
                    total_gain = max(0.5, min(5.0, total_gain))
                    
                    # Добавляем ПВ
                    if "politics" not in player_data:
                        player_data["politics"] = {}
                    
                    current_pp = player_data["politics"].get("political_power", 100)
                    player_data["politics"]["political_power"] = current_pp + total_gain
                
                save_states(states)
                last_update = now
                print(f"✅ Политическая власть обновлена: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            
            await asyncio.sleep(3600)  # Проверка каждый час
            
        except Exception as e:
            print(f"❌ Ошибка в political_power_update_loop: {e}")
            await asyncio.sleep(3600)

# ==================== ФУНКЦИИ ДЛЯ ИНТЕГРАЦИИ ====================

async def show_political_power_menu(interaction_or_ctx, user_id: int):
    """Показать меню политической власти"""
    from bot import load_states
    
    states = load_states()
    
    # Находим государство игрока
    state_id = None
    player_data = None
    for sid, data in states["players"].items():
        if data.get("assigned_to") == str(user_id):
            state_id = sid
            player_data = data
            break
    
    if not player_data:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message("❌ У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("❌ У вас нет государства!")
        return
    
    # Создаем embed
    current_pp = get_political_power(player_data)
    gain = player_data.get("politics", {}).get("political_power_gain", 2.0)
    
    embed = discord.Embed(
        title="Политическая власть",
        description=f"Государство: **{player_data['state']['statename']}**",
        color=DARK_THEME_COLOR
    )
    
    embed.add_field(name="Текущий запас", value=f"{current_pp:.1f} ПВ", inline=True)
    embed.add_field(name="Ежедневный прирост", value=f"+{gain:.1f} ПВ/день", inline=True)
    
    # Отправляем эфемерное сообщение
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, ephemeral=True)
        message = await interaction_or_ctx.original_response()
    else:
        message = await interaction_or_ctx.send(embed=embed, ephemeral=True)
    
    view = PoliticalPowerView(user_id, state_id, player_data, message)
    await message.edit(view=view)

# ==================== ЭКСПОРТ ФУНКЦИЙ ====================

__all__ = [
    'LawProposal',
    'POLITICAL_LAWS',
    'get_political_power',
    'set_political_power',
    'add_political_power',
    'spend_political_power',
    'show_political_power_menu',
    'political_power_update_loop',
    'apply_law_effects',
    'check_requirements',
    'get_active_laws',
    'get_law_history',
    'get_parliament_composition'
]

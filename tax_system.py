# tax_system.py - Модуль для многокомпонентной налоговой системы

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
from datetime import datetime
from typing import Dict, List, Tuple

from utils import format_billion, format_number, load_states, save_states

# Цвет для эмбедов
DARK_THEME_COLOR = 0x2b2d31

# ==================== ФУНКЦИЯ МИГРАЦИИ СТАРЫХ НАЛОГОВ ====================

def migrate_taxes(player_data):
    """
    Мигрирует старую налоговую систему (tax_rate) в новую многокомпонентную
    """
    if "economy" not in player_data:
        return player_data
    
    economy = player_data["economy"]
    
    # Проверяем, есть ли старая налоговая ставка и нет ли уже новой системы
    if "tax_rate" in economy and "taxes" not in economy:
        old_tax_rate = economy["tax_rate"]
        
        # Определяем страну для более реалистичных налогов
        country_name = player_data.get("state", {}).get("statename", "Неизвестно")
        
        # Базовые настройки для разных стран
        if country_name == "США":
            economy["taxes"] = {
                "income": {"rate": 22.0, "progressive": True, "brackets": [
                    {"up_to": 15000, "rate": 10}, {"up_to": 50000, "rate": 15},
                    {"up_to": 100000, "rate": 22}, {"up_to": 250000, "rate": 28},
                    {"up_to": 500000, "rate": 33}, {"above": 500000, "rate": 40}
                ]},
                "corporate": {"rate": 21.0, "small_business_rate": 15.0, "small_business_threshold": 5000000},
                "vat": {"rate": 0.0, "reduced_rate": 0.0, "reduced_categories": []},
                "property": {"rate": 1.2, "base_value": 100000},
                "luxury": {"rate": 0.0, "threshold": 0},
                "social_security": {"employee_rate": 7.65, "employer_rate": 7.65},
                "environmental": {"co2_rate": 25.0, "pollution_rate": 50.0}
            }
        elif country_name == "Россия":
            economy["taxes"] = {
                "income": {"rate": 13.0, "progressive": False, "brackets": []},
                "corporate": {"rate": 20.0, "small_business_rate": 15.0, "small_business_threshold": 5000000},
                "vat": {"rate": 20.0, "reduced_rate": 10.0, "reduced_categories": ["food", "medicine", "baby_products"]},
                "property": {"rate": 2.0, "base_value": 100000},
                "luxury": {"rate": 15.0, "threshold": 10000000},
                "social_security": {"employee_rate": 13.0, "employer_rate": 30.0},
                "environmental": {"co2_rate": 30.0, "pollution_rate": 60.0}
            }
        elif country_name == "Китай":
            economy["taxes"] = {
                "income": {"rate": 45.0, "progressive": False, "brackets": []},
                "corporate": {"rate": 25.0, "small_business_rate": 20.0, "small_business_threshold": 5000000},
                "vat": {"rate": 13.0, "reduced_rate": 6.0, "reduced_categories": ["food", "medicine", "education"]},
                "property": {"rate": 1.2, "base_value": 50000},
                "luxury": {"rate": 20.0, "threshold": 5000000},
                "social_security": {"employee_rate": 8.0, "employer_rate": 20.0},
                "environmental": {"co2_rate": 40.0, "pollution_rate": 80.0}
            }
        elif country_name == "Германия":
            economy["taxes"] = {
                "income": {"rate": 42.0, "progressive": True, "brackets": [
                    {"up_to": 10000, "rate": 0}, {"up_to": 30000, "rate": 18},
                    {"up_to": 60000, "rate": 30}, {"up_to": 100000, "rate": 40},
                    {"up_to": 250000, "rate": 45}, {"above": 250000, "rate": 47}
                ]},
                "corporate": {"rate": 30.0, "small_business_rate": 25.0, "small_business_threshold": 5000000},
                "vat": {"rate": 19.0, "reduced_rate": 7.0, "reduced_categories": ["food", "books", "public_transport"]},
                "property": {"rate": 2.5, "base_value": 100000},
                "luxury": {"rate": 0.0, "threshold": 0},
                "social_security": {"employee_rate": 20.0, "employer_rate": 20.0},
                "environmental": {"co2_rate": 55.0, "pollution_rate": 100.0}
            }
        elif country_name == "Израиль":
            economy["taxes"] = {
                "income": {"rate": 31.7, "progressive": True, "brackets": [
                    {"up_to": 25000, "rate": 10}, {"up_to": 50000, "rate": 20},
                    {"up_to": 100000, "rate": 30}, {"up_to": 200000, "rate": 35},
                    {"above": 200000, "rate": 47}
                ]},
                "corporate": {"rate": 23.0, "small_business_rate": 18.0, "small_business_threshold": 5000000},
                "vat": {"rate": 17.0, "reduced_rate": 8.5, "reduced_categories": ["food", "medicine"]},
                "property": {"rate": 2.5, "base_value": 100000},
                "luxury": {"rate": 30.0, "threshold": 5000000},
                "social_security": {"employee_rate": 12.0, "employer_rate": 15.0},
                "environmental": {"co2_rate": 35.0, "pollution_rate": 70.0}
            }
        elif country_name == "Украина":
            economy["taxes"] = {
                "income": {"rate": 18.0, "progressive": True, "brackets": [
                    {"up_to": 10000, "rate": 0}, {"up_to": 30000, "rate": 12},
                    {"up_to": 60000, "rate": 18}, {"above": 60000, "rate": 25}
                ]},
                "corporate": {"rate": 18.0, "small_business_rate": 12.0, "small_business_threshold": 3000000},
                "vat": {"rate": 20.0, "reduced_rate": 7.0, "reduced_categories": ["food", "medicine"]},
                "property": {"rate": 1.5, "base_value": 50000},
                "luxury": {"rate": 15.0, "threshold": 3000000},
                "social_security": {"employee_rate": 15.0, "employer_rate": 25.0},
                "environmental": {"co2_rate": 20.0, "pollution_rate": 40.0}
            }
        elif country_name == "Иран":
            economy["taxes"] = {
                "income": {"rate": 20.0, "progressive": True, "brackets": [
                    {"up_to": 5000, "rate": 0}, {"up_to": 15000, "rate": 10},
                    {"up_to": 30000, "rate": 15}, {"up_to": 50000, "rate": 20},
                    {"above": 50000, "rate": 25}
                ]},
                "corporate": {"rate": 25.0, "small_business_rate": 20.0, "small_business_threshold": 3000000},
                "vat": {"rate": 9.0, "reduced_rate": 5.0, "reduced_categories": ["food", "medicine"]},
                "property": {"rate": 1.0, "base_value": 50000},
                "luxury": {"rate": 20.0, "threshold": 2000000},
                "social_security": {"employee_rate": 7.0, "employer_rate": 20.0},
                "environmental": {"co2_rate": 15.0, "pollution_rate": 30.0}
            }
        else:
            # Универсальные настройки для неизвестных стран
            economy["taxes"] = {
                "income": {"rate": old_tax_rate, "progressive": False, "brackets": []},
                "corporate": {"rate": old_tax_rate * 0.8, "small_business_rate": old_tax_rate * 0.6, "small_business_threshold": 5000000},
                "vat": {"rate": old_tax_rate * 0.7, "reduced_rate": old_tax_rate * 0.4, "reduced_categories": ["food", "medicine"]},
                "property": {"rate": old_tax_rate * 0.1, "base_value": 100000},
                "luxury": {"rate": old_tax_rate * 1.2, "threshold": 1000000},
                "social_security": {"employee_rate": old_tax_rate * 0.6, "employer_rate": old_tax_rate},
                "environmental": {"co2_rate": old_tax_rate * 0.5, "pollution_rate": old_tax_rate}
            }
        
        # Можно оставить старую ставку для обратной совместимости или удалить
        # del economy["tax_rate"]  # Раскомментируйте, если хотите удалить старую ставку
    
    return player_data


class TaxSystem:
    """Класс для управления налоговой системой государства"""
    
    def __init__(self, state_data: Dict):
        self.state_data = state_data
        self.economy = state_data.get("economy", {})
        self.taxes = self.economy.get("taxes", self._get_default_taxes())
        self.population = state_data["state"].get("population", 0)
        self.gdp = self.economy.get("gdp", 0)
        
    def _get_default_taxes(self) -> Dict:
        """Возвращает налоговую систему по умолчанию"""
        return {
            "income": {
                "rate": 13.0,
                "progressive": True,
                "brackets": [
                    {"up_to": 20000, "rate": 0},
                    {"up_to": 50000, "rate": 10},
                    {"up_to": 150000, "rate": 20},
                    {"up_to": 500000, "rate": 30},
                    {"above": 500000, "rate": 40}
                ]
            },
            "corporate": {
                "rate": 20.0,
                "small_business_rate": 15.0,
                "small_business_threshold": 5000000
            },
            "vat": {
                "rate": 18.0,
                "reduced_rate": 10.0,
                "reduced_categories": ["food", "medicine", "books"]
            },
            "property": {
                "rate": 1.5,
                "base_value": 100000
            },
            "luxury": {
                "rate": 25.0,
                "threshold": 1000000
            },
            "social_security": {
                "employee_rate": 15.0,
                "employer_rate": 25.0
            },
            "environmental": {
                "co2_rate": 50.0,
                "pollution_rate": 100.0
            }
        }
    
    def calculate_income_tax(self, total_wage_bill: float) -> float:
        """
        Расчёт подоходного налога от общего фонда оплаты труда
        total_wage_bill - общая сумма зарплат в экономике
        """
        income_tax = self.taxes.get("income", {})
        
        if not income_tax.get("progressive", False):
            # Плоская шкала
            return total_wage_bill * income_tax.get("rate", 13) / 100
        
        # Для прогрессивной шкалы используем среднюю эффективную ставку
        # В реальности прогрессивный налог даёт около 70% от номинальной ставки
        # из-за льгот, вычетов и уклонения
        nominal_rate = income_tax.get("rate", 30)
        effective_rate = nominal_rate * 0.7
        return total_wage_bill * effective_rate / 100
    
    def calculate_corporate_tax(self, profit: float) -> float:
        """Расчёт налога на прибыль"""
        corp_tax = self.taxes.get("corporate", {})
        rate = corp_tax.get("rate", 20.0)
        return profit * rate / 100
    
    def calculate_vat(self, price: float) -> float:
        """Расчёт НДС"""
        vat = self.taxes.get("vat", {})
        rate = vat.get("rate", 18.0)
        return price * rate / 100
    
    def calculate_social_security(self, salary: float) -> Tuple[float, float]:
        """Расчёт социальных взносов"""
        ss = self.taxes.get("social_security", {})
        employee_part = salary * ss.get("employee_rate", 15.0) / 100
        employer_part = salary * ss.get("employer_rate", 25.0) / 100
        return employee_part, employer_part
    
    def calculate_property_tax(self) -> float:
        """Расчёт налога на недвижимость (упрощённо)"""
        property_tax_rate = self.taxes.get("property", {}).get("rate", 1.5)
        # Стоимость недвижимости примерно 3 годовых ВВП
        property_value = self.gdp * 3
        return property_value * property_tax_rate / 100
    
    def calculate_total_tax_revenue(self) -> Dict:
        """Рассчитывает общие налоговые поступления (реалистичные 15-40% от ВВП)"""
        # Налог на прибыль (прибыль корпораций ~10% ВВП)
        corporate_profits = self.gdp * 0.1
        corporate_tax = self.calculate_corporate_tax(corporate_profits)
        
        # Подоходный налог (зарплаты ~50% ВВП)
        wage_share = self.gdp * 0.5
        income_tax = self.calculate_income_tax(wage_share)
        
        # НДС (потребление ~60% ВВП, но облагается не всё)
        consumption = self.gdp * 0.6
        vat = self.calculate_vat(consumption) * 0.7
        
        # Социальные взносы (от зарплат)
        employee_ss, employer_ss = self.calculate_social_security(wage_share)
        total_ss = employee_ss + employer_ss
        
        # Налог на недвижимость
        property_tax = self.calculate_property_tax()
        
        total_revenue = income_tax + corporate_tax + vat + total_ss + property_tax
        
        # Ограничиваем налоги разумным процентом ВВП (15-40%)
        effective_rate = (total_revenue / self.gdp) * 100 if self.gdp > 0 else 0
        
        return {
            "income_tax": income_tax,
            "corporate_tax": corporate_tax,
            "vat": vat,
            "social_security": total_ss,
            "property_tax": property_tax,
            "total": total_revenue,
            "effective_rate": effective_rate
        }
    
    def get_tax_summary_embed(self) -> discord.Embed:
        """Создаёт embed с краткой информацией о налогах"""
        revenue = self.calculate_total_tax_revenue()
        
        embed = discord.Embed(
            title="💰 Налоговая система",
            description=f"Эффективная налоговая нагрузка: {revenue['effective_rate']:.1f}% ВВП",
            color=DARK_THEME_COLOR
        )
        
        # Основные налоги
        tax_rates = ""
        tax_rates += f"• Подоходный: {self.taxes['income'].get('rate', 13)}%"
        if self.taxes['income'].get('progressive', False):
            tax_rates += " (прогрессивный)\n"
        else:
            tax_rates += "\n"
        tax_rates += f"• Корпоративный: {self.taxes['corporate'].get('rate', 20)}%\n"
        tax_rates += f"• НДС: {self.taxes['vat'].get('rate', 18)}%\n"
        tax_rates += f"• На недвижимость: {self.taxes['property'].get('rate', 1.5)}%\n"
        tax_rates += f"• Соц. взносы: {self.taxes['social_security'].get('employee_rate', 15)}% (работник) + {self.taxes['social_security'].get('employer_rate', 25)}% (работодатель)"
        
        embed.add_field(name="📊 Ставки налогов", value=tax_rates, inline=False)
        
        # Поступления
        revenue_text = ""
        revenue_text += f"• Подоходный: {format_billion(revenue['income_tax'])}\n"
        revenue_text += f"• Корпоративный: {format_billion(revenue['corporate_tax'])}\n"
        revenue_text += f"• НДС: {format_billion(revenue['vat'])}\n"
        revenue_text += f"• Соц. взносы: {format_billion(revenue['social_security'])}\n"
        revenue_text += f"• Недвижимость: {format_billion(revenue['property_tax'])}\n"
        revenue_text += f"**• Всего: {format_billion(revenue['total'])}**"
        
        embed.add_field(name="📈 Годовые поступления", value=revenue_text, inline=True)
        
        return embed
    
    def change_tax_rate(self, tax_type: str, new_rate: float) -> Tuple[bool, str]:
        """Изменение налоговой ставки"""
        valid_types = ["income", "corporate", "vat", "property", "luxury", "social_security", "environmental"]
        
        if tax_type not in valid_types:
            return False, f"Неверный тип налога. Доступны: {', '.join(valid_types)}"
        
        if new_rate < 0 or new_rate > 100:
            return False, "Ставка должна быть от 0 до 100%"
        
        if tax_type == "income":
            self.taxes["income"]["rate"] = new_rate
        elif tax_type == "corporate":
            self.taxes["corporate"]["rate"] = new_rate
        elif tax_type == "vat":
            self.taxes["vat"]["rate"] = new_rate
        elif tax_type == "property":
            self.taxes["property"]["rate"] = new_rate
        elif tax_type == "luxury":
            self.taxes["luxury"]["rate"] = new_rate
        elif tax_type == "social_security":
            self.taxes["social_security"]["employee_rate"] = new_rate
        elif tax_type == "environmental":
            self.taxes["environmental"]["co2_rate"] = new_rate
            
        # Сохраняем изменения
        if "economy" not in self.state_data:
            self.state_data["economy"] = {}
        self.state_data["economy"]["taxes"] = self.taxes
        
        return True, f"Ставка налога {tax_type} изменена на {new_rate}%"


# ==================== КОМАНДЫ ДЛЯ УПРАВЛЕНИЯ НАЛОГАМИ ====================

class TaxManagementView(View):
    """Меню управления налогами"""
    
    def __init__(self, user_id: int, state_data: Dict, tax_system: TaxSystem):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.state_data = state_data
        self.tax_system = tax_system
    
    @discord.ui.button(label="📊 Обзор налогов", style=discord.ButtonStyle.secondary)
    async def overview_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = self.tax_system.get_tax_summary_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="✏️ Изменить налоги", style=discord.ButtonStyle.secondary)
    async def change_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="✏️ Изменение налогов",
            description="Выберите налог для изменения:",
            color=DARK_THEME_COLOR
        )
        
        select = TaxTypeSelect(self.user_id, self.state_data, self.tax_system)
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
        
        embed = self.tax_system.get_tax_summary_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="📈 Детали", style=discord.ButtonStyle.secondary)
    async def details_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        # Показываем более детальную информацию о налогах
        embed = discord.Embed(
            title="📈 Детали налоговой системы",
            color=DARK_THEME_COLOR
        )
        
        # Информация о прогрессивности
        income_tax = self.tax_system.taxes.get("income", {})
        if income_tax.get("progressive", False):
            brackets_text = ""
            for bracket in income_tax.get("brackets", []):
                if "up_to" in bracket:
                    brackets_text += f"• До ${bracket['up_to']:,}: {bracket['rate']}%\n"
                elif "above" in bracket:
                    brackets_text += f"• Выше ${bracket['above']:,}: {bracket['rate']}%\n"
            embed.add_field(name="📊 Прогрессивная шкала", value=brackets_text, inline=False)
        
        # Льготные категории НДС
        vat = self.tax_system.taxes.get("vat", {})
        if vat.get("reduced_categories"):
            categories = ", ".join(vat["reduced_categories"])
            embed.add_field(name="🛒 Льготные категории НДС", value=f"Ставка: {vat.get('reduced_rate', 10)}%\nКатегории: {categories}", inline=False)
        
        # Порог для малого бизнеса
        corp = self.tax_system.taxes.get("corporate", {})
        embed.add_field(name="🏢 Малый бизнес", value=f"Порог: ${corp.get('small_business_threshold', 5000000):,}\nСтавка: {corp.get('small_business_rate', 15)}%", inline=True)
        
        # Порог для налога на роскошь
        luxury = self.tax_system.taxes.get("luxury", {})
        if luxury.get("threshold", 0) > 0:
            embed.add_field(name="💎 Налог на роскошь", value=f"Порог: ${luxury.get('threshold', 1000000):,}\nСтавка: {luxury.get('rate', 25)}%", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)


class TaxTypeSelect(Select):
    """Выбор типа налога для изменения"""
    
    def __init__(self, user_id: int, state_data: Dict, tax_system: TaxSystem):
        self.user_id = user_id
        self.state_data = state_data
        self.tax_system = tax_system
        
        options = [
            discord.SelectOption(label="Подоходный налог", value="income", description=f"Текущая ставка: {tax_system.taxes['income'].get('rate', 13)}%"),
            discord.SelectOption(label="Корпоративный налог", value="corporate", description=f"Текущая ставка: {tax_system.taxes['corporate'].get('rate', 20)}%"),
            discord.SelectOption(label="НДС", value="vat", description=f"Текущая ставка: {tax_system.taxes['vat'].get('rate', 18)}%"),
            discord.SelectOption(label="Налог на недвижимость", value="property", description=f"Текущая ставка: {tax_system.taxes['property'].get('rate', 1.5)}%"),
            discord.SelectOption(label="Налог на роскошь", value="luxury", description=f"Текущая ставка: {tax_system.taxes['luxury'].get('rate', 25)}%"),
            discord.SelectOption(label="Соц. взносы", value="social_security", description=f"Текущая ставка: {tax_system.taxes['social_security'].get('employee_rate', 15)}%"),
            discord.SelectOption(label="Экологический налог", value="environmental", description=f"Текущая ставка: {tax_system.taxes['environmental'].get('co2_rate', 50)}"),
        ]
        
        super().__init__(
            placeholder="Выберите налог...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        tax_type = self.values[0]
        
        modal = TaxChangeModal(self.user_id, self.state_data, self.tax_system, tax_type)
        await interaction.response.send_modal(modal)


class TaxChangeModal(Modal):
    """Модальное окно для изменения ставки налога"""
    
    def __init__(self, user_id: int, state_data: Dict, tax_system: TaxSystem, tax_type: str):
        tax_names = {
            "income": "Подоходный налог",
            "corporate": "Корпоративный налог",
            "vat": "НДС",
            "property": "Налог на недвижимость",
            "luxury": "Налог на роскошь",
            "social_security": "Соц. взносы",
            "environmental": "Экологический налог"
        }
        
        super().__init__(title=f"Изменить {tax_names.get(tax_type, tax_type)}")
        
        self.user_id = user_id
        self.state_data = state_data
        self.tax_system = tax_system
        self.tax_type = tax_type
        
        current_rate = 0
        if tax_type == "income":
            current_rate = tax_system.taxes["income"].get("rate", 13)
        elif tax_type == "corporate":
            current_rate = tax_system.taxes["corporate"].get("rate", 20)
        elif tax_type == "vat":
            current_rate = tax_system.taxes["vat"].get("rate", 18)
        elif tax_type == "property":
            current_rate = tax_system.taxes["property"].get("rate", 1.5)
        elif tax_type == "luxury":
            current_rate = tax_system.taxes["luxury"].get("rate", 25)
        elif tax_type == "social_security":
            current_rate = tax_system.taxes["social_security"].get("employee_rate", 15)
        elif tax_type == "environmental":
            current_rate = tax_system.taxes["environmental"].get("co2_rate", 50)
        
        self.rate_input = TextInput(
            label=f"Новая ставка (текущая: {current_rate}%)",
            placeholder="Введите число от 0 до 100",
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.rate_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        try:
            new_rate = float(self.rate_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        success, message = self.tax_system.change_tax_rate(self.tax_type, new_rate)
        
        if success:
            # Сохраняем изменения в state_data
            from utils import load_states, save_states
            states = load_states()
            
            for sid, data in states["players"].items():
                if data.get("assigned_to") == str(self.user_id):
                    states["players"][sid]["economy"]["taxes"] = self.tax_system.taxes
                    break
            
            save_states(states)
            
            embed = discord.Embed(
                title="✅ Налог изменён",
                description=message,
                color=DARK_THEME_COLOR
            )
            
            # Показываем обновлённый обзор
            tax_summary = self.tax_system.get_tax_summary_embed()
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await interaction.followup.send(embed=tax_summary, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)


# ==================== ФУНКЦИЯ ДЛЯ ПОКАЗА МЕНЮ НАЛОГОВ ====================

async def show_tax_menu(interaction_or_ctx, user_id: int):
    """Показать меню управления налогами"""
    from utils import load_states
    
    states = load_states()
    
    # Находим государство игрока
    state_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            state_data = data
            break
    
    if not state_data:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message("❌ У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send("❌ У вас нет государства!")
        return
    
    tax_system = TaxSystem(state_data)
    
    embed = tax_system.get_tax_summary_embed()
    view = TaxManagementView(user_id, state_data, tax_system)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view, ephemeral=True)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_tax_menu',
    'TaxSystem',
    'migrate_taxes'
]

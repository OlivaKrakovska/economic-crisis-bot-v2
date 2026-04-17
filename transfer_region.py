# transfer_region.py - Модуль для передачи регионов между игроками

import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, TextInput
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from utils import format_number, format_billion, load_states, save_states, DARK_THEME_COLOR
from infra_build import load_infrastructure, save_infrastructure, get_all_regions_from_country

# Импортируем функции из maritime_trade
try:
    from maritime_trade import update_ships_on_region_transfer, update_priorities_on_region_transfer
    MARITIME_AVAILABLE = True
except ImportError:
    print("⚠️ Модуль maritime_trade не найден. Обновление торговых кораблей при передаче региона будет отключено.")
    MARITIME_AVAILABLE = False
    
    def update_ships_on_region_transfer(region_name, old_country, new_country):
        return {"ships_affected": 0, "affected_ships": []}
    
    def update_priorities_on_region_transfer(region_name, old_country, new_country):
        return {"removed": [], "added": [], "updated": []}

class TransferRegionCog(commands.Cog):
    """Ког для передачи регионов между игроками"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='передать_регион')
    @commands.has_permissions(administrator=True)
    async def transfer_region(self, ctx, from_member: discord.Member, to_member: discord.Member, *, region_name: str):
        """
        Передать регион от одного игрока другому
        Использование: !передать_регион @игрок1 @игрок2 название_региона
        """
        # Загружаем данные
        states = load_states()
        infra = load_infrastructure()
        
        # Находим данные игроков
        from_data = None
        to_data = None
        from_country = None
        to_country = None
        
        for data in states["players"].values():
            if data.get("assigned_to") == str(from_member.id):
                from_data = data
                from_country = data["state"]["statename"]
            if data.get("assigned_to") == str(to_member.id):
                to_data = data
                to_country = data["state"]["statename"]
        
        if not from_data:
            await ctx.send(f"❌ У игрока {from_member.mention} нет государства!")
            return
        
        if not to_data:
            await ctx.send(f"❌ У игрока {to_member.mention} нет государства!")
            return
        
        # Ищем регион в инфраструктуре отправителя
        region_found = False
        region_data = None
        economic_region_name = None
        country_id = None
        
        for cid, cdata in infra["infrastructure"].items():
            if cdata.get("country") == from_country:
                country_id = cid
                for econ_region, econ_data in cdata["economic_regions"].items():
                    for reg_name, reg_data in econ_data["regions"].items():
                        if reg_name.lower() == region_name.lower():
                            region_found = True
                            region_data = reg_data
                            economic_region_name = econ_region
                            region_name = reg_name  # используем правильное название
                            break
                    if region_found:
                        break
            if region_found:
                break
        
        if not region_found:
            await ctx.send(f"❌ Регион '{region_name}' не найден в стране {from_country}!")
            return
        
        # Запрос подтверждения
        embed = discord.Embed(
            title="⚠️ ПОДТВЕРЖДЕНИЕ ПЕРЕДАЧИ РЕГИОНА",
            description=f"Вы уверены, что хотите передать регион?",
            color=discord.Color.orange()
        )
        
        embed.add_field(name="Регион", value=region_name, inline=True)
        embed.add_field(name="От кого", value=f"{from_member.mention} ({from_country})", inline=True)
        embed.add_field(name="Кому", value=f"{to_member.mention} ({to_country})", inline=True)
        
        # Информация о регионе
        population = region_data.get("population", 0)
        shipyards = region_data.get("shipyards", 0)
        military_factories = region_data.get("military_factories", 0)
        
        embed.add_field(name="Население", value=format_number(population), inline=True)
        embed.add_field(name="Верфи", value=str(shipyards), inline=True)
        embed.add_field(name="Военные заводы", value=str(military_factories), inline=True)
        
        # Проверяем, есть ли корабли в регионе
        from maritime_trade import get_ships_by_country, CargoShip
        ships_in_region = []
        
        try:
            all_ships = []
            maritime_data = None
            try:
                from maritime_trade import load_maritime_data
                maritime_data = load_maritime_data()
            except:
                pass
            
            if maritime_data:
                for ship_data in maritime_data.get("ships", []):
                    ship = CargoShip.from_dict(ship_data)
                    if ship.current_region == region_name:
                        ships_in_region.append(ship)
        except:
            pass
        
        if ships_in_region:
            embed.add_field(
                name="🚢 Корабли в регионе",
                value=f"Будет передано {len(ships_in_region)} кораблей",
                inline=False
            )
        
        embed.add_field(
            name="⚠️ ВАЖНО",
            value="После передачи региона:\n"
                  "• Все корабли в регионе переходят новому владельцу\n"
                  "• Торговые приоритеты, связанные с регионом, обновляются\n"
                  "• Инфраструктура региона остаётся неизменной\n"
                  "• Население региона переходит новому владельцу\n"
                  "• Действие НЕОБРАТИМО!",
            inline=False
        )
        
        view = TransferRegionConfirmView(
            self.bot, ctx, from_member, to_member, from_country, to_country,
            region_name, economic_region_name, country_id, region_data, ships_in_region
        )
        
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name='список_регионов')
    @commands.has_permissions(administrator=True)
    async def list_regions(self, ctx, member: discord.Member = None):
        """Показать список регионов игрока"""
        if member is None:
            member = ctx.author
        
        states = load_states()
        infra = load_infrastructure()
        
        # Находим страну игрока
        player_country = None
        for data in states["players"].values():
            if data.get("assigned_to") == str(member.id):
                player_country = data["state"]["statename"]
                break
        
        if not player_country:
            await ctx.send(f"❌ У игрока {member.mention} нет государства!")
            return
        
        # Находим ID страны в инфраструктуре
        country_id = None
        for cid, cdata in infra["infrastructure"].items():
            if cdata.get("country") == player_country:
                country_id = cid
                break
        
        if not country_id:
            await ctx.send(f"❌ Данные инфраструктуры для страны {player_country} не найдены!")
            return
        
        # Собираем все регионы
        regions = []
        for econ_region, econ_data in infra["infrastructure"][country_id]["economic_regions"].items():
            for region_name, region_data in econ_data["regions"].items():
                regions.append({
                    "name": region_name,
                    "economic_region": econ_region,
                    "population": region_data.get("population", 0),
                    "shipyards": region_data.get("shipyards", 0),
                    "military_factories": region_data.get("military_factories", 0),
                    "coastal": region_data.get("coastal", False),
                    "development_level": region_data.get("development_level", 50)
                })
        
        if not regions:
            await ctx.send(f"❌ У страны {player_country} нет регионов!")
            return
        
        # Сортируем по названию
        regions.sort(key=lambda x: x["name"])
        
        embed = discord.Embed(
            title=f"📋 Регионы страны {player_country}",
            description=f"Игрок: {member.mention}",
            color=DARK_THEME_COLOR
        )
        
        for region in regions[:15]:  # Показываем первые 15
            status = ""
            if region["coastal"]:
                status += "🌊 Прибрежный"
                if region["shipyards"] > 0:
                    status += f" (верфей: {region['shipyards']})"
            else:
                status += "🏔️ Внутренний"
            
            embed.add_field(
                name=region["name"],
                value=f"{status}\n"
                      f"Население: {format_number(region['population'])}\n"
                      f"Развитие: {region['development_level']}%\n"
                      f"Воен. заводы: {region['military_factories']}",
                inline=True
            )
        
        if len(regions) > 15:
            embed.set_footer(text=f"Показано 15 из {len(regions)} регионов")
        
        await ctx.send(embed=embed)


class TransferRegionConfirmView(discord.ui.View):
    """Подтверждение передачи региона"""
    
    def __init__(self, bot, ctx, from_member, to_member, from_country, to_country,
                 region_name, economic_region_name, country_id, region_data, ships_in_region):
        super().__init__(timeout=120)
        self.bot = bot
        self.ctx = ctx
        self.from_member = from_member
        self.to_member = to_member
        self.from_country = from_country
        self.to_country = to_country
        self.region_name = region_name
        self.economic_region_name = economic_region_name
        self.country_id = country_id
        self.region_data = region_data
        self.ships_in_region = ships_in_region
    
    @discord.ui.button(label="✅ ПОДТВЕРДИТЬ ПЕРЕДАЧУ", style=discord.ButtonStyle.danger)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Загружаем данные
        states = load_states()
        infra = load_infrastructure()
        
        # Обновляем инфраструктуру - меняем страну региона
        # Удаляем регион из старой страны
        del infra["infrastructure"][self.country_id]["economic_regions"][self.economic_region_name]["regions"][self.region_name]
        
        # Если в экономическом регионе больше нет регионов, удаляем его
        if not infra["infrastructure"][self.country_id]["economic_regions"][self.economic_region_name]["regions"]:
            del infra["infrastructure"][self.country_id]["economic_regions"][self.economic_region_name]
        
        # Находим ID страны получателя
        to_country_id = None
        for cid, cdata in infra["infrastructure"].items():
            if cdata.get("country") == self.to_country:
                to_country_id = cid
                break
        
        # Если у получателя нет данных, создаём
        if not to_country_id:
            # Создаём новую запись для страны получателя
            to_country_id = f"10000000000000000{len(infra['infrastructure']) + 1}"
            infra["infrastructure"][to_country_id] = {
                "country": self.to_country,
                "economic_regions": {}
            }
        
        # Добавляем регион в страну получателя
        if self.economic_region_name not in infra["infrastructure"][to_country_id]["economic_regions"]:
            infra["infrastructure"][to_country_id]["economic_regions"][self.economic_region_name] = {
                "regions": {}
            }
        
        infra["infrastructure"][to_country_id]["economic_regions"][self.economic_region_name]["regions"][self.region_name] = self.region_data
        
        # Сохраняем инфраструктуру
        save_infrastructure(infra)
        
        # Обновляем данные государств (население, территория)
        from_data = None
        to_data = None
        
        for data in states["players"].values():
            if data.get("state", {}).get("statename") == self.from_country:
                from_data = data
            if data.get("state", {}).get("statename") == self.to_country:
                to_data = data
        
        if from_data and to_data:
            population = self.region_data.get("population", 0)
            territory = self.region_data.get("territory", 10000)  # примерная площадь
            
            from_data["state"]["population"] = max(0, from_data["state"]["population"] - population)
            from_data["state"]["territory"] = max(0, from_data["state"]["territory"] - territory)
            
            to_data["state"]["population"] += population
            to_data["state"]["territory"] += territory
        
        # Обновляем корабли в переданном регионе
        maritime_result = {"ships_affected": 0, "affected_ships": []}
        if MARITIME_AVAILABLE:
            maritime_result = update_ships_on_region_transfer(self.region_name, self.from_country, self.to_country)
        
        # Обновляем приоритеты экспорта
        priority_changes = {"removed": [], "added": [], "updated": []}
        if MARITIME_AVAILABLE:
            priority_changes = update_priorities_on_region_transfer(self.region_name, self.from_country, self.to_country)
        
        save_states(states)
        
        # Отправляем результат
        embed = discord.Embed(
            title="✅ Регион передан!",
            description=f"Регион **{self.region_name}** передан от {self.from_member.mention} к {self.to_member.mention}",
            color=discord.Color.green()
        )
        
        embed.add_field(name="От кого", value=f"{self.from_member.mention} ({self.from_country})", inline=True)
        embed.add_field(name="Кому", value=f"{self.to_member.mention} ({self.to_country})", inline=True)
        embed.add_field(name="Регион", value=self.region_name, inline=True)
        
        # Информация о кораблях
        if maritime_result["ships_affected"] > 0:
            embed.add_field(
                name="🚢 Корабли",
                value=f"Передано {maritime_result['ships_affected']} кораблей новому владельцу",
                inline=False
            )
        
        # Информация о приоритетах
        if priority_changes["added"]:
            embed.add_field(
                name="📊 Приоритеты экспорта",
                value=f"Обновлены приоритеты для {len(priority_changes['added'])} торговых направлений",
                inline=False
            )
        
        embed.add_field(
            name="📊 Итоги",
            value=f"Население: {format_number(self.region_data.get('population', 0))} чел.\n"
                  f"Верфи: {self.region_data.get('shipyards', 0)}\n"
                  f"Военные заводы: {self.region_data.get('military_factories', 0)}",
            inline=False
        )
        
        # Логирование
        log_channel = self.bot.get_channel(1263440933232578630)  # ADMIN_LOG_CHANNEL_ID
        if log_channel:
            await log_channel.send(
                f"📦 **Админ {self.ctx.author.name}** передал регион {self.region_name} "
                f"от {self.from_member.name} ({self.from_country}) к {self.to_member.name} ({self.to_country})"
            )
        
        await self.ctx.send(embed=embed)
    
    @discord.ui.button(label="❌ ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ Передача отменена",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=None)


async def setup(bot):
    await bot.add_cog(TransferRegionCog(bot))

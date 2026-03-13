# trade_tariffs.py - ИЗМЕНЕННАЯ ВЕРСИЯ (без квот)

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
from datetime import datetime
from typing import Dict, List, Tuple, Any

from utils import format_billion, format_number, load_states, save_states, load_trades, save_trades

DARK_THEME_COLOR = 0x2b2d31
TARIFFS_FILE = 'tariffs.json'

# ==================== КАТЕГОРИИ ПРОДУКЦИИ ДЛЯ ЭМБАРГО ====================

PRODUCT_CATEGORIES = {
    "all": "Вся продукция",    "military": "Военная техника",
    "civil": "Гражданская продукция",
    "tanks": "Танки",
    "btr": "БТР",
    "bmp": "БМП",
    "armored_vehicles": "Бронеавтомобили",
    "trucks": "Грузовики",
    "cars": "Автомобили",
    "ew_vehicles": "Машины РЭБ",
    "engineering_equipment": "Инженерная техника",
    "radar_systems": "РЛС",
    "self_propelled_artillery": "САУ",
    "towed_artillery": "Буксируемая артиллерия",
    "mlrs": "РСЗО",
    "atgm_complexes": "ПТРК",
    "otr_complexes": "ОТРК",
    "zas": "Зенитная артиллерия",
    "zdprk": "ЗПРК",
    "short_range_air_defense": "ПВО ближнего действия",
    "long_range_air_defense": "ПВО дальнего действия",
    "small_arms": "Стрелковое оружие",
    "grenade_launchers": "Гранатометы",
    "atgms": "Переносные ПТРК",
    "manpads": "ПЗРК",
    "medical_equipment": "Медицинское оборудование",
    "fpv_drones": "FPV-дроны",
    "fighters": "Истребители",
    "attack_aircraft": "Штурмовики",
    "bombers": "Бомбардировщики",
    "transport_aircraft": "Транспортные самолеты",
    "attack_helicopters": "Ударные вертолеты",
    "transport_helicopters": "Транспортные вертолеты",
    "recon_uav": "Разведывательные БПЛА",
    "attack_uav": "Ударные БПЛА",
    "boats": "Катера",
    "corvettes": "Корветы",
    "destroyers": "Эсминцы",
    "cruisers": "Крейсера",
    "aircraft_carriers": "Авианосцы",
    "submarines": "Подводные лодки",
    "missiles": "Ракетное вооружение",
    "strategic_nuclear": "Стратегическое ядерное оружие",
    "tactical_nuclear": "Тактическое ядерное оружие",
    "cruise_missiles": "Крылатые ракеты",
    "hypersonic_missiles": "Гиперзвуковые ракеты",
    "ballistic_missiles": "Баллистические ракеты",
    "steel": "Сталь",
    "aluminum": "Алюминий",
    "uranium": "Уран",
    "electronics": "Электроника",
    "rare_metals": "Редкие металлы",
    "oil": "Нефть",
    "gas": "Газ",
    "coal": "Уголь",
    "food": "Продовольствие",
    "food_products": "Продукты питания",
    "pharmaceuticals": "Фармацевтика",
    "chemicals": "Химическая продукция",
    "clothing": "Одежда",
    "consumer_electronics": "Бытовая электроника",
    "aerospace_equipment": "Авиакосмическое оборудование",
    "agricultural_machinery": "Сельхозтехника",
    "construction_machinery": "Строительная техника",
    "industrial_equipment": "Промышленное оборудование",
    "machine_tools": "Станки",
    "industrial_robots": "Промышленные роботы",
    "energy_equipment": "Энергетическое оборудование",
    "electrical_equipment": "Электротехника",
    "telecom_equipment": "Телекоммуникационное оборудование",
    "tech_equipment": "Технологическое оборудование",
    "auto_parts": "Автозапчасти",
    "buses": "Автобусы",
    "drones": "Беспилотники",
    "furniture": "Мебель",
    "household_goods": "Товары для дома",
    "medical_supplies": "Медицинские изделия",
    "sanitary_products": "Санитарно-гигиенические средства",
    "ships": "Корабли"
}

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_tariffs():
    """Загрузка таможенных политик всех государств"""
    try:
        with open(TARIFFS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"tariffs": {}}
            return json.loads(content)
    except FileNotFoundError:
        return {"tariffs": {}}
    except json.JSONDecodeError:
        return {"tariffs": {}}

def save_tariffs(data):
    """Сохранение таможенных политик"""
    with open(TARIFFS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_country_tariffs(country_name: str) -> Dict:
    """Получить таможенную политику страны"""
    tariffs_data = load_tariffs()
    if country_name not in tariffs_data["tariffs"]:
        # Создаём политику по умолчанию
        tariffs_data["tariffs"][country_name] = {
            "base_tariff": 5.0,
            "specific_tariffs": {},
            "product_tariffs": {},
            "export_tariffs": {},
            "trade_agreements": [],
            "trade_wars": {},
            "embargoes": {},
            "sanctions": {},
            "last_updated": str(datetime.now())
        }
        save_tariffs(tariffs_data)
    
    return tariffs_data["tariffs"][country_name]

def update_country_tariffs(country_name: str, tariffs: Dict):
    """Обновить таможенную политику страны"""
    tariffs_data = load_tariffs()
    tariffs_data["tariffs"][country_name] = tariffs
    tariffs_data["tariffs"][country_name]["last_updated"] = str(datetime.now())
    save_tariffs(tariffs_data)


# ==================== КЛАСС TARIFFSYSTEM (БЕЗ КВОТ) ====================

class TariffSystem:
    """Класс для управления таможенными пошлинами"""
    
    def __init__(self, country_name: str):
        self.country_name = country_name
        self.tariffs = get_country_tariffs(country_name)
    
    def calculate_import_tariff(self, product_type: str, origin_country: str, value: float) -> float:
        """
        Рассчитывает импортную пошлину на товар
        Платит покупатель в бюджет своей страны
        """
        # Если товар подпадает под эмбарго, пошлина равна полной стоимости (блокировка)
        if self.is_product_embargoed(origin_country, product_type):
            return value  # Бесконечная пошлина = блокировка
        
        sanction_penalty = self.get_sanction_penalty(origin_country)
        
        # Беспошлинная торговля для партнёров по соглашениям
        if origin_country in self.tariffs.get("trade_agreements", []):
            base_rate = 0.0
        else:
            # Проверяем специфические тарифы для стран
            if origin_country in self.tariffs.get("specific_tariffs", {}):
                base_rate = self.tariffs["specific_tariffs"][origin_country]
            # Проверяем тарифы по типу продукта
            elif product_type in self.tariffs.get("product_tariffs", {}):
                base_rate = self.tariffs["product_tariffs"][product_type]
            # Проверяем торговые войны
            elif origin_country in self.tariffs.get("trade_wars", {}):
                base_rate = self.tariffs["trade_wars"][origin_country]
            # Базовый тариф
            else:
                base_rate = self.tariffs.get("base_tariff", 5.0)
        
        # Применяем штраф от санкций
        total_rate = base_rate * (1 + sanction_penalty)
        return value * total_rate / 100
    
    def calculate_export_tariff(self, product_type: str, value: float) -> float:
        """
        Рассчитывает экспортную пошлину на товар
        Платит продавец (корпорация) в бюджет своей страны
        """
        if product_type in self.tariffs.get("export_tariffs", {}):
            rate = self.tariffs["export_tariffs"][product_type]
            return value * rate / 100
        return 0.0
    
    def get_import_tariff_rate(self, product_type: str, origin_country: str) -> float:
        """Получить ставку импортной пошлины для товара из конкретной страны"""
        if self.is_product_embargoed(origin_country, product_type):
            return float('inf')
        
        if origin_country in self.tariffs.get("trade_agreements", []):
            return 0.0
        
        if origin_country in self.tariffs.get("specific_tariffs", {}):
            return self.tariffs["specific_tariffs"][origin_country]
        
        if product_type in self.tariffs.get("product_tariffs", {}):
            return self.tariffs["product_tariffs"][product_type]
        
        if origin_country in self.tariffs.get("trade_wars", {}):
            return self.tariffs["trade_wars"][origin_country]
        
        return self.tariffs.get("base_tariff", 5.0)
    
    def get_export_tariff_rate(self, product_type: str) -> float:
        """Получить ставку экспортной пошлины для товара"""
        return self.tariffs.get("export_tariffs", {}).get(product_type, 0.0)
    
    # ⚠️ МЕТОДЫ КВОТ ПОЛНОСТЬЮ УДАЛЕНЫ ⚠️
    
    def set_base_tariff(self, rate: float) -> Tuple[bool, str]:
        """Установить базовый тариф"""
        if rate < 0 or rate > 200:
            return False, "Ставка должна быть от 0 до 200%"
        self.tariffs["base_tariff"] = rate
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"Базовый тариф установлен на {rate}%"
    
    def set_country_tariff(self, country: str, rate: float) -> Tuple[bool, str]:
        """Установить специфический тариф для страны"""
        if rate < 0 or rate > 200:
            return False, "Ставка должна быть от 0 до 200%"
        if rate == 0:
            if country in self.tariffs.get("specific_tariffs", {}):
                del self.tariffs["specific_tariffs"][country]
        else:
            if "specific_tariffs" not in self.tariffs:
                self.tariffs["specific_tariffs"] = {}
            self.tariffs["specific_tariffs"][country] = rate
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"Тариф для {country} установлен на {rate}%"
    
    def set_product_tariff(self, product_type: str, rate: float) -> Tuple[bool, str]:
        """Установить тариф на тип продукта"""
        if rate < 0 or rate > 200:
            return False, "Ставка должна быть от 0 до 200%"
        if rate == 0:
            if product_type in self.tariffs.get("product_tariffs", {}):
                del self.tariffs["product_tariffs"][product_type]
        else:
            if "product_tariffs" not in self.tariffs:
                self.tariffs["product_tariffs"] = {}
            self.tariffs["product_tariffs"][product_type] = rate
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"Тариф на {product_type} установлен на {rate}%"
    
    def set_export_tariff(self, product_type: str, rate: float) -> Tuple[bool, str]:
        """Установить экспортную пошлину на тип продукта"""
        if rate < 0 or rate > 100:
            return False, "Ставка должна быть от 0 до 100%"
        if rate == 0:
            if product_type in self.tariffs.get("export_tariffs", {}):
                del self.tariffs["export_tariffs"][product_type]
        else:
            if "export_tariffs" not in self.tariffs:
                self.tariffs["export_tariffs"] = {}
            self.tariffs["export_tariffs"][product_type] = rate
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"Экспортная пошлина на {product_type} установлена на {rate}%"
    
    def add_trade_agreement(self, country: str) -> Tuple[bool, str]:
        """Добавить страну в зону беспошлинной торговли"""
        if country == self.country_name:
            return False, "Нельзя добавить свою страну в торговое соглашение"
        if "trade_agreements" not in self.tariffs:
            self.tariffs["trade_agreements"] = []
        if country not in self.tariffs["trade_agreements"]:
            self.tariffs["trade_agreements"].append(country)
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"{country} добавлена в зону беспошлинной торговли"
        return False, f"{country} уже в зоне беспошлинной торговли"
    
    def remove_trade_agreement(self, country: str) -> Tuple[bool, str]:
        """Удалить страну из зоны беспошлинной торговли"""
        if "trade_agreements" in self.tariffs and country in self.tariffs["trade_agreements"]:
            self.tariffs["trade_agreements"].remove(country)
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"{country} удалена из зоны беспошлинной торговли"
        return False, f"{country} не в зоне беспошлинной торговли"
    
    def declare_trade_war(self, country: str, rate: float) -> Tuple[bool, str]:
        """Объявить торговую войну"""
        if country == self.country_name:
            return False, "Нельзя объявить торговую войну своей стране"
        if rate < 0 or rate > 200:
            return False, "Ставка должна быть от 0 до 200%"
        if "trade_wars" not in self.tariffs:
            self.tariffs["trade_wars"] = {}
        self.tariffs["trade_wars"][country] = rate
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"Торговая война объявлена {country} с тарифом {rate}%"
    
    def end_trade_war(self, country: str) -> Tuple[bool, str]:
        """Завершить торговую войну"""
        if "trade_wars" in self.tariffs and country in self.tariffs["trade_wars"]:
            del self.tariffs["trade_wars"][country]
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"Торговая война с {country} завершена"
        return False, f"Нет активной торговой войны с {country}"
    
    def set_embargo(self, country: str, categories: List[str]) -> Tuple[bool, str]:
        """Установить эмбарго на конкретные категории товаров"""
        if country == self.country_name:
            return False, "Нельзя наложить эмбарго на свою страну!"
            
        if "embargoes" not in self.tariffs:
            self.tariffs["embargoes"] = {}
        
        if "all" in categories:
            self.tariffs["embargoes"][country] = ["all"]
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"Полное эмбарго установлено на {country}"
        else:
            valid_categories = []
            for cat in categories:
                if cat in PRODUCT_CATEGORIES or cat == "military" or cat == "civil":
                    valid_categories.append(cat)
            
            if not valid_categories:
                return False, "Не указано ни одной допустимой категории"
            
            self.tariffs["embargoes"][country] = valid_categories
            update_country_tariffs(self.country_name, self.tariffs)
            cat_names = ", ".join([PRODUCT_CATEGORIES.get(c, c) for c in valid_categories[:3]])
            if len(valid_categories) > 3:
                cat_names += f" и ещё {len(valid_categories)-3}"
            return True, f"Эмбарго на {cat_names} установлено на {country}"
    
    def remove_embargo(self, country: str) -> Tuple[bool, str]:
        """Полностью снять эмбарго со страны"""
        if "embargoes" in self.tariffs and country in self.tariffs["embargoes"]:
            del self.tariffs["embargoes"][country]
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"Эмбарго с {country} полностью снято"
        return False, f"Нет эмбарго с {country}"
    
    def remove_embargo_category(self, country: str, category: str) -> Tuple[bool, str]:
        """Снять эмбарго с конкретной категории товаров"""
        if "embargoes" not in self.tariffs or country not in self.tariffs["embargoes"]:
            return False, f"Нет эмбарго с {country}"
        
        categories = self.tariffs["embargoes"][country]
        
        if "all" in categories:
            return False, "Установлено полное эмбарго. Используйте снятие всего эмбарго"
        
        if category not in categories:
            return False, f"Категория {PRODUCT_CATEGORIES.get(category, category)} не под эмбарго"
        
        categories.remove(category)
        
        if not categories:
            del self.tariffs["embargoes"][country]
        else:
            self.tariffs["embargoes"][country] = categories
        
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"Эмбарго с {PRODUCT_CATEGORIES.get(category, category)} для {country} снято"
    
    def get_embargoed_categories(self, country: str) -> List[str]:
        """Получить список категорий под эмбарго для страны"""
        embargoes = self.tariffs.get("embargoes", {})
        return embargoes.get(country, [])
    
    def is_product_embargoed(self, country: str, product_type: str) -> bool:
        """
        Проверяет, подпадает ли продукт под эмбарго
        country - страна-производитель (откуда товар)
        """
        embargoed_categories = self.get_embargoed_categories(country)
        
        if not embargoed_categories:
            return False
        
        # Полное эмбарго на все товары
        if "all" in embargoed_categories:
            return True
        
        main_category = product_type.split('.')[0] if '.' in product_type else product_type
        
        # Проверка на полное военное эмбарго
        if "military" in embargoed_categories:
            military_categories = ["ground", "air", "navy", "missiles", "equipment", 
                                  "tanks", "btr", "bmp", "fighters", "bombers", 
                                  "submarines", "missiles", "small_arms", "atgms", 
                                  "manpads", "ew_vehicles", "radar_systems", 
                                  "self_propelled_artillery", "towed_artillery", "mlrs",
                                  "atgm_complexes", "otr_complexes", "zdprk", "zas",
                                  "short_range_air_defense", "long_range_air_defense",
                                  "attack_aircraft", "transport_aircraft", "attack_helicopters",
                                  "recon_uav", "attack_uav", "boats", "corvettes",
                                  "destroyers", "cruisers", "aircraft_carriers", "submarines"]
            if main_category in military_categories or product_type in military_categories:
                return True
        
        # Проверка на полное гражданское эмбарго
        if "civil" in embargoed_categories:
            civil_categories = ["cars", "trucks", "buses", "agricultural_machinery", 
                               "construction_machinery", "industrial_equipment", 
                               "food_products", "clothing", "electronics", "chemicals",
                               "pharmaceuticals", "medical_equipment", "consumer_electronics",
                               "furniture", "household_goods", "food", "oil", "gas", "coal",
                               "steel", "aluminum", "uranium", "rare_metals"]
            if main_category in civil_categories or product_type in civil_categories:
                return True
        
        # Проверка на конкретные категории
        if main_category in embargoed_categories:
            return True
        
        if product_type in embargoed_categories:
            return True
        
        return False
    
    def get_available_products(self, all_products: Dict, country: str) -> Dict:
        """Возвращает список доступных продуктов с учётом эмбарго"""
        available = {}
        embargoed_categories = self.get_embargoed_categories(country)
        
        if not embargoed_categories:
            return all_products
        
        if "all" in embargoed_categories:
            return {}
        
        for product_id, product in all_products.items():
            product_type = product.get('type', '')
            if not self.is_product_embargoed(country, product_type):
                available[product_id] = product
        
        return available
    
    def get_available_corporations(self, all_corporations) -> list:
        """Возвращает список доступных корпораций с учётом эмбарго"""
        available = []
        embargoes = self.tariffs.get("embargoes", {})
        
        if isinstance(all_corporations, dict):
            for country, corps_dict in all_corporations.items():
                if isinstance(corps_dict, dict):
                    for corp_id, corp in corps_dict.items():
                        if hasattr(corp, 'country'):
                            corp_country = corp.country
                            embargoed_categories = embargoes.get(corp_country, [])
                            
                            if "all" in embargoed_categories:
                                continue
                            
                            available.append(corp)
                        else:
                            available.append(corp)
                elif isinstance(corps_dict, list):
                    for corp in corps_dict:
                        if hasattr(corp, 'country'):
                            corp_country = corp.country
                            embargoed_categories = embargoes.get(corp_country, [])
                            
                            if "all" in embargoed_categories:
                                continue
                            
                            available.append(corp)
                        else:
                            available.append(corp)
        elif isinstance(all_corporations, list):
            for corp in all_corporations:
                if hasattr(corp, 'country'):
                    corp_country = corp.country
                    embargoed_categories = embargoes.get(corp_country, [])
                    
                    if "all" in embargoed_categories:
                        continue
                    
                    available.append(corp)
                else:
                    available.append(corp)
        
        return available
    
    def set_sanctions(self, country: str, penalty: float, reason: str = "") -> Tuple[bool, str]:
        """Установить санкции против страны"""
        if penalty < 0 or penalty > 100:
            return False, "Штраф должен быть от 0 до 100%"
        
        if "sanctions" not in self.tariffs:
            self.tariffs["sanctions"] = {}
        
        self.tariffs["sanctions"][country] = {
            "penalty": penalty,
            "reason": reason,
            "date": str(datetime.now())
        }
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"Санкции против {country} установлены (штраф {penalty}%)"
    
    def remove_sanctions(self, country: str) -> Tuple[bool, str]:
        """Снять санкции с страны"""
        if "sanctions" in self.tariffs and country in self.tariffs["sanctions"]:
            del self.tariffs["sanctions"][country]
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"Санкции с {country} сняты"
        return False, f"Нет санкций против {country}"
    
    def get_sanction_penalty(self, country: str) -> float:
        """Получить штраф от санкций (в долях 0-1)"""
        sanctions = self.tariffs.get("sanctions", {})
        if country in sanctions:
            return sanctions[country]["penalty"] / 100
        return 0.0
    
    def calculate_sanction_impact(self, country: str) -> Dict:
        """Рассчитывает влияние санкций на торговлю"""
        impact = {
            "trade_penalty": 0.0,
            "price_increase": 0.0,
            "availability": 1.0
        }
        
        embargoed_categories = self.get_embargoed_categories(country)
        if "all" in embargoed_categories:
            impact["trade_penalty"] = 1.0
            impact["price_increase"] = 1.0
            impact["availability"] = 0.0
            return impact
        
        penalty = self.get_sanction_penalty(country)
        if penalty > 0:
            impact["trade_penalty"] = penalty * 0.5
            impact["price_increase"] = penalty
            impact["availability"] = max(0, 1 - penalty * 0.3)
        
        return impact
    
    def get_tariff_summary_embed(self) -> discord.Embed:
        """Создаёт embed с краткой информацией о тарифах"""
        embed = discord.Embed(
            title=f"🛃 Таможенная политика {self.country_name}",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(
            name="📊 Базовый тариф",
            value=f"{self.tariffs.get('base_tariff', 5)}%",
            inline=True
        )
        
        # Экспортные пошлины
        export_tariffs = self.tariffs.get("export_tariffs", {})
        if export_tariffs:
            export_tariff_text = ""
            for product, rate in list(export_tariffs.items())[:5]:
                product_name = PRODUCT_CATEGORIES.get(product, product)
                export_tariff_text += f"• {product_name}: {rate}%\n"
            embed.add_field(name="📤 Экспортные пошлины", value=export_tariff_text, inline=True)
        
        embargoes = self.tariffs.get("embargoes", {})
        if embargoes:
            embargo_text = ""
            for country, categories in list(embargoes.items())[:3]:
                if "all" in categories:
                    embargo_text += f"• {country}: ПОЛНОЕ\n"
                else:
                    cat_names = [PRODUCT_CATEGORIES.get(c, c) for c in categories[:2]]
                    cat_text = ", ".join(cat_names)
                    if len(categories) > 2:
                        cat_text += f" и ещё {len(categories)-2}"
                    embargo_text += f"• {country}: {cat_text}\n"
            embed.add_field(name="🚫 Эмбарго", value=embargo_text, inline=True)
        
        if self.tariffs.get("specific_tariffs"):
            specific_text = ""
            for country, rate in list(self.tariffs["specific_tariffs"].items())[:5]:
                specific_text += f"• {country}: {rate}%\n"
            embed.add_field(name="🌍 Тарифы по странам", value=specific_text, inline=True)
        
        if self.tariffs.get("product_tariffs"):
            product_text = ""
            for product, rate in list(self.tariffs["product_tariffs"].items())[:5]:
                product_name = PRODUCT_CATEGORIES.get(product, product)
                product_text += f"• {product_name}: {rate}%\n"
            embed.add_field(name="📦 Тарифы по товарам", value=product_text, inline=True)
        
        if self.tariffs.get("trade_agreements"):
            agreements = ", ".join(self.tariffs["trade_agreements"][:5])
            embed.add_field(name="🤝 Беспошлинная торговля", value=agreements, inline=False)
        
        if self.tariffs.get("trade_wars"):
            wars_text = ""
            for country, rate in self.tariffs["trade_wars"].items():
                wars_text += f"• {country}: {rate}%\n"
            embed.add_field(name="⚔️ Торговые войны", value=wars_text, inline=False)
        
        if self.tariffs.get("sanctions"):
            sanctions_text = ""
            for country, data in self.tariffs["sanctions"].items():
                sanctions_text += f"• {country}: +{data['penalty']}%\n"
            embed.add_field(name="⚠️ Санкции", value=sanctions_text, inline=False)
        
        return embed


# ==================== ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ДОСТУПНОСТИ КОРПОРАЦИИ ====================

def is_corporation_available(buyer_country: str, corporation_country: str) -> bool:
    """
    Проверяет, доступна ли корпорация из указанной страны для покупателя
    """
    tariff_system = TariffSystem(buyer_country)
    
    # Проверяем, есть ли у покупателя эмбарго против страны продавца
    embargoed_categories = tariff_system.get_embargoed_categories(corporation_country)
    
    # Если есть полное эмбарго, корпорация недоступна
    if "all" in embargoed_categories:
        return False
    
    return True


# ==================== ФУНКЦИЯ ДЛЯ РАСЧЁТА ТОРГОВЛИ ====================

def calculate_trade_with_tariffs(trade_data: Dict, seller_country: str, buyer_country: str) -> Dict:
    """Рассчитывает торговую сделку с учётом тарифов"""
    buyer_tariffs = TariffSystem(buyer_country)
    seller_tariffs = TariffSystem(seller_country)
    
    # Проверяем эмбарго с обеих сторон
    if buyer_tariffs.is_product_embargoed(seller_country, trade_data.get("resource", "")):
        return {
            "blocked": True,
            "reason": f"Ваша страна ввела эмбарго против {seller_country}"
        }
    
    if seller_tariffs.is_product_embargoed(buyer_country, trade_data.get("resource", "")):
        return {
            "blocked": True,
            "reason": f"Страна {seller_country} ввела эмбарго против вашей страны"
        }
    
    # Импортная пошлина (платит покупатель)
    import_tariff = buyer_tariffs.calculate_import_tariff(
        trade_data.get("resource", ""), 
        seller_country, 
        trade_data["total_price"]
    )
    
    # Экспортная пошлина (платит продавец)
    export_tariff = seller_tariffs.calculate_export_tariff(
        trade_data.get("resource", ""),
        trade_data["total_price"]
    )
    
    sanction_impact = buyer_tariffs.calculate_sanction_impact(seller_country)
    
    return {
        "blocked": False,
        "original_price": trade_data["total_price"],
        "import_tariff": import_tariff,
        "export_tariff": export_tariff,
        "total_tariffs": import_tariff + export_tariff,
        "final_price": trade_data["total_price"] + import_tariff,
        "seller_receives": trade_data["total_price"] - export_tariff,
        "sanction_impact": sanction_impact,
        "price_with_sanctions": trade_data["total_price"] * (1 + sanction_impact["price_increase"])
    }


# ==================== ФУНКЦИИ ДЛЯ ФИЛЬТРАЦИИ ====================

def filter_corporations_by_tariffs(country_name: str, all_corporations):
    """Фильтрует корпорации с учётом эмбарго"""
    tariff_system = TariffSystem(country_name)
    return tariff_system.get_available_corporations(all_corporations)


# ==================== КЛАССЫ ДЛЯ УПРАВЛЕНИЯ ТАРИФАМИ ====================

class TariffManagementView(View):
    """Меню управления таможенными пошлинами"""
    
    def __init__(self, user_id: int, country_name: str, tariff_system: TariffSystem):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.country_name = country_name
        self.tariff_system = tariff_system
    
    @discord.ui.button(label="Обзор", style=discord.ButtonStyle.secondary)
    async def overview_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = self.tariff_system.get_tariff_summary_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Базовый тариф", style=discord.ButtonStyle.secondary)
    async def base_tariff_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        modal = BaseTariffModal(self.user_id, self.tariff_system)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Экспортные пошлины", style=discord.ButtonStyle.secondary)
    async def export_tariff_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📤 Экспортные пошлины",
            description="Выберите категорию товаров для установки экспортной пошлины:",
            color=DARK_THEME_COLOR
        )
        
        select = ExportTariffSelect(self.user_id, self.tariff_system)
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Тариф по странам", style=discord.ButtonStyle.secondary)
    async def country_tariff_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🌍 Тарифы по странам",
            description="Выберите страну для изменения тарифа:",
            color=DARK_THEME_COLOR
        )
        
        select = CountryTariffSelect(self.user_id, self.tariff_system)
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Тариф по товарам", style=discord.ButtonStyle.secondary)
    async def product_tariff_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📦 Тарифы по товарам",
            description="Выберите категорию товаров для изменения тарифа:",
            color=DARK_THEME_COLOR
        )
        
        select = ProductTariffSelect(self.user_id, self.tariff_system)
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Эмбарго", style=discord.ButtonStyle.secondary)
    async def embargo_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🚫 Управление эмбарго",
            description="Выберите действие:",
            color=DARK_THEME_COLOR
        )
        
        view = EmbargoManagementView(self.user_id, self.tariff_system)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Торговые соглашения", style=discord.ButtonStyle.secondary)
    async def trade_agreements_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🤝 Торговые соглашения",
            description="Управление зонами беспошлинной торговли:",
            color=DARK_THEME_COLOR
        )
        
        view = TradeAgreementView(self.user_id, self.tariff_system)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    # ⚠️ КНОПКА "📊 Квоты" ПОЛНОСТЬЮ УДАЛЕНА ⚠️
    
    async def back_to_main(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = self.tariff_system.get_tariff_summary_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class BaseTariffModal(Modal, title="Изменить базовый тариф"):
    def __init__(self, user_id: int, tariff_system: TariffSystem):
        super().__init__()
        self.user_id = user_id
        self.tariff_system = tariff_system
        
        current_rate = tariff_system.tariffs.get("base_tariff", 5)
        
        self.rate_input = TextInput(
            label=f"Базовая ставка (текущая: {current_rate}%)",
            placeholder="Введите число от 0 до 200",
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
            rate = float(self.rate_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        success, message = self.tariff_system.set_base_tariff(rate)
        
        if success:
            embed = discord.Embed(
                title="✅ Тариф изменён",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)


class ExportTariffSelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem):
        self.user_id = user_id
        self.tariff_system = tariff_system
        
        options = []
        # Основные категории для экспортных пошлин
        export_categories = ["oil", "gas", "coal", "uranium", "steel", "aluminum", 
                            "rare_metals", "tanks", "fighters", "missiles", "small_arms",
                            "food_products", "chemicals", "drones", "fpv_drones"]
        
        for product_id in export_categories[:25]:
            product_name = PRODUCT_CATEGORIES.get(product_id, product_id)
            current_rate = tariff_system.tariffs.get("export_tariffs", {}).get(product_id, 0)
            options.append(
                discord.SelectOption(
                    label=product_name,
                    description=f"Текущая пошлина: {current_rate}%",
                    value=product_id
                )
            )
        
        super().__init__(
            placeholder="Выберите категорию товаров...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        product_id = self.values[0]
        
        modal = ExportTariffModal(self.user_id, self.tariff_system, product_id)
        await interaction.response.send_modal(modal)


class ExportTariffModal(Modal, title="Изменить экспортную пошлину"):
    def __init__(self, user_id: int, tariff_system: TariffSystem, product_id: str):
        super().__init__()
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.product_id = product_id
        self.product_name = PRODUCT_CATEGORIES.get(product_id, product_id)
        
        current_rate = tariff_system.tariffs.get("export_tariffs", {}).get(product_id, 0)
        
        self.rate_input = TextInput(
            label=f"Ставка для {self.product_name} (текущая: {current_rate}%)",
            placeholder="Введите число от 0 до 100 (0 для удаления)",
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
            rate = float(self.rate_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        success, message = self.tariff_system.set_export_tariff(self.product_id, rate)
        
        if success:
            embed = discord.Embed(
                title="✅ Экспортная пошлина изменена",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)


class CountryTariffSelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem):
        self.user_id = user_id
        self.tariff_system = tariff_system
        
        countries = ["США", "Россия", "Китай", "Германия", "Великобритания", 
                     "Франция", "Япония", "Израиль", "Украина", "Иран"]
        
        options = []
        for country in countries[:25]:
            if country == tariff_system.country_name:
                continue
            current_rate = tariff_system.tariffs.get("specific_tariffs", {}).get(country, 
                                tariff_system.tariffs.get("base_tariff", 5))
            options.append(
                discord.SelectOption(
                    label=country,
                    description=f"Текущий тариф: {current_rate}%",
                    value=country
                )
            )
        
        super().__init__(
            placeholder="Выберите страну...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        country = self.values[0]
        
        modal = CountryTariffModal(self.user_id, self.tariff_system, country)
        await interaction.response.send_modal(modal)


class CountryTariffModal(Modal, title="Изменить тариф для страны"):
    def __init__(self, user_id: int, tariff_system: TariffSystem, country: str):
        super().__init__()
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.country = country
        
        current_rate = tariff_system.tariffs.get("specific_tariffs", {}).get(country, 
                            tariff_system.tariffs.get("base_tariff", 5))
        
        self.rate_input = TextInput(
            label=f"Ставка для {country} (текущая: {current_rate}%)",
            placeholder="Введите число от 0 до 200 (0 для удаления)",
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
            rate = float(self.rate_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        success, message = self.tariff_system.set_country_tariff(self.country, rate)
        
        if success:
            embed = discord.Embed(
                title="✅ Тариф изменён",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)


class ProductTariffSelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem):
        self.user_id = user_id
        self.tariff_system = tariff_system
        
        options = []
        for product_id, product_name in list(PRODUCT_CATEGORIES.items())[:25]:
            current_rate = tariff_system.tariffs.get("product_tariffs", {}).get(product_id, 
                                tariff_system.tariffs.get("base_tariff", 5))
            options.append(
                discord.SelectOption(
                    label=product_name,
                    description=f"Текущий тариф: {current_rate}%",
                    value=product_id
                )
            )
        
        super().__init__(
            placeholder="Выберите категорию товаров...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        product_id = self.values[0]
        
        modal = ProductTariffModal(self.user_id, self.tariff_system, product_id)
        await interaction.response.send_modal(modal)


class ProductTariffModal(Modal, title="Изменить тариф для товара"):
    def __init__(self, user_id: int, tariff_system: TariffSystem, product_id: str):
        super().__init__()
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.product_id = product_id
        self.product_name = PRODUCT_CATEGORIES.get(product_id, product_id)
        
        current_rate = tariff_system.tariffs.get("product_tariffs", {}).get(product_id, 
                            tariff_system.tariffs.get("base_tariff", 5))
        
        self.rate_input = TextInput(
            label=f"Ставка для {self.product_name} (текущая: {current_rate}%)",
            placeholder="Введите число от 0 до 200 (0 для удаления)",
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
            rate = float(self.rate_input.value)
        except ValueError:
            await interaction.response.send_message("❌ Введите корректное число!", ephemeral=True)
            return
        
        success, message = self.tariff_system.set_product_tariff(self.product_id, rate)
        
        if success:
            embed = discord.Embed(
                title="✅ Тариф изменён",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)


# ⚠️ КЛАССЫ QUOTA_* ПОЛНОСТЬЮ УДАЛЕНЫ ⚠️


class EmbargoManagementView(View):
    """Меню управления эмбарго"""
    
    def __init__(self, user_id: int, tariff_system: TariffSystem):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.tariff_system = tariff_system
    
    @discord.ui.button(label="➕ Установить эмбарго", style=discord.ButtonStyle.secondary)
    async def set_embargo_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="➕ Установка эмбарго",
            description="Выберите страну для установки эмбарго:",
            color=DARK_THEME_COLOR
        )
        
        select = EmbargoCountrySelect(self.user_id, self.tariff_system, "set")
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_embargo_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="➖ Снять эмбарго", style=discord.ButtonStyle.secondary)
    async def remove_embargo_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="➖ Снятие эмбарго",
            description="Выберите страну для снятия эмбарго:",
            color=DARK_THEME_COLOR
        )
        
        select = EmbargoCountrySelect(self.user_id, self.tariff_system, "remove")
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_embargo_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_embargo_menu(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🚫 Управление эмбарго",
            description="Выберите действие:",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=self)


class EmbargoCountrySelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, action: str):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.action = action
        
        countries = ["США", "Россия", "Китай", "Германия", "Великобритания", 
                     "Франция", "Япония", "Израиль", "Украина", "Иран"]
        
        options = []
        for country in countries[:25]:
            if country == tariff_system.country_name:
                continue
                
            if action == "set":
                description = "Установить эмбарго"
            else:
                embargoed = tariff_system.get_embargoed_categories(country)
                if embargoed:
                    description = f"Эмбарго: {len(embargoed)} категорий"
                else:
                    description = "Нет эмбарго"
            
            options.append(
                discord.SelectOption(
                    label=country,
                    description=description,
                    value=country
                )
            )
        
        super().__init__(
            placeholder="Выберите страну...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        country = self.values[0]
        
        if self.action == "set":
            modal = EmbargoSetModal(self.user_id, self.tariff_system, country)
            await interaction.response.send_modal(modal)
        else:
            success, message = self.tariff_system.remove_embargo(country)
            if success:
                embed = discord.Embed(
                    title="✅ Эмбарго снято",
                    description=message,
                    color=DARK_THEME_COLOR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {message}", ephemeral=True)


class EmbargoSetModal(Modal, title="Установка эмбарго"):
    def __init__(self, user_id: int, tariff_system: TariffSystem, country: str):
        super().__init__()
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.country = country
        
        self.categories_input = TextInput(
            label="Категории (через запятую)",
            placeholder="Например: all или military, civil, tanks, fighters",
            min_length=1,
            max_length=100,
            required=True
        )
        self.add_item(self.categories_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        categories_text = self.categories_input.value.lower()
        categories = [cat.strip() for cat in categories_text.split(',')]
        
        success, message = self.tariff_system.set_embargo(self.country, categories)
        
        if success:
            embed = discord.Embed(
                title="✅ Эмбарго установлено",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)


class TradeAgreementView(View):
    """Меню управления торговыми соглашениями"""
    
    def __init__(self, user_id: int, tariff_system: TariffSystem):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.tariff_system = tariff_system
    
    @discord.ui.button(label="➕ Добавить", style=discord.ButtonStyle.secondary)
    async def add_agreement_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="➕ Добавление торгового соглашения",
            description="Выберите страну для добавления:",
            color=DARK_THEME_COLOR
        )
        
        select = TradeAgreementSelect(self.user_id, self.tariff_system, "add")
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_agreement_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="➖ Удалить", style=discord.ButtonStyle.secondary)
    async def remove_agreement_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="➖ Удаление торгового соглашения",
            description="Выберите страну для удаления:",
            color=DARK_THEME_COLOR
        )
        
        select = TradeAgreementSelect(self.user_id, self.tariff_system, "remove")
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="◀ Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_agreement_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_agreement_menu(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🤝 Торговые соглашения",
            description="Управление зонами беспошлинной торговли:",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=self)


class TradeAgreementSelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, action: str):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.action = action
        
        countries = ["США", "Россия", "Китай", "Германия", "Великобритания", 
                     "Франция", "Япония", "Израиль", "Украина", "Иран"]
        
        options = []
        for country in countries[:25]:
            if country == tariff_system.country_name:
                continue
                
            if action == "add":
                if country not in tariff_system.tariffs.get("trade_agreements", []):
                    options.append(
                        discord.SelectOption(
                            label=country,
                            description="Добавить в зону",
                            value=country
                        )
                    )
            else:
                if country in tariff_system.tariffs.get("trade_agreements", []):
                    options.append(
                        discord.SelectOption(
                            label=country,
                            description="Удалить из зоны",
                            value=country
                        )
                    )
        
        super().__init__(
            placeholder="Выберите страну...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Это не ваше меню!", ephemeral=True)
            return
        
        country = self.values[0]
        
        if self.action == "add":
            success, message = self.tariff_system.add_trade_agreement(country)
        else:
            success, message = self.tariff_system.remove_trade_agreement(country)
        
        if success:
            embed = discord.Embed(
                title="✅ Торговое соглашение обновлено",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True)


# ==================== КОМАНДА ДЛЯ ПОКАЗА МЕНЮ ====================

async def show_tariff_menu(interaction_or_ctx, user_id: int):
    """Показать меню управления таможенными пошлинами"""
    from utils import load_states
    
    states = load_states()
    
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
    
    country_name = state_data["state"]["statename"]
    tariff_system = TariffSystem(country_name)
    
    embed = tariff_system.get_tariff_summary_embed()
    view = TariffManagementView(user_id, country_name, tariff_system)
    
    if hasattr(interaction_or_ctx, 'response'):
        await interaction_or_ctx.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        await interaction_or_ctx.send(embed=embed, view=view, ephemeral=True)


# ==================== ЭКСПОРТ ====================

__all__ = [
    'show_tariff_menu',
    'TariffSystem',
    'TariffManagementView',
    'calculate_trade_with_tariffs',
    'filter_corporations_by_tariffs',
    'is_corporation_available',
    'load_tariffs',
    'save_tariffs',
    'get_country_tariffs',
    'PRODUCT_CATEGORIES'
]

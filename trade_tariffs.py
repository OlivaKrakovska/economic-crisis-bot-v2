# trade_tariffs.py - Модуль для управления тарифами и торговыми отношениями
# РЕАЛИСТИЧНАЯ ВЕРСИЯ: декабрь 2022 года
# ДОБАВЛЕНО КЭШИРОВАНИЕ И ИНТЕГРАЦИЯ С ЗАМОРОЗКОЙ АКТИВОВ

import discord
from discord.ui import Button, View, Select, Modal, TextInput
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

from utils import format_billion, format_number, load_states, save_states, DARK_THEME_COLOR

TARIFFS_FILE = 'tariffs.json'

# Кэш для тарифных систем
_tariff_cache = {}
_tariff_cache_time = {}
CACHE_TTL = 300  # 5 минут

# ==================== КАТЕГОРИИ ПРОДУКЦИИ ДЛЯ ТАРИФОВ ====================

# Основные категории товаров
PRODUCT_MAIN_CATEGORIES = {
    "military_ground": "Сухопутная военная техника",
    "military_air": "Авиация",
    "military_navy": "Военно-морской флот",
    "military_missiles": "Ракетное вооружение",
    "military_equipment": "Снаряжение",
    "civil_transport": "Транспорт",
    "civil_industry": "Промышленность",
    "civil_medicine": "Медицина",
    "civil_electronics": "Электроника",
    "civil_goods": "Потребительские товары",
    "civil_food": "Продукты питания",
    "resources": "Ресурсы"
}

# Подкатегории товаров
PRODUCT_SUBCATEGORIES = {
    "military_ground": {
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
        "long_range_air_defense": "ПВО дальнего действия"
    },
    "military_air": {
        "fighters": "Истребители",
        "attack_aircraft": "Штурмовики",
        "bombers": "Бомбардировщики",
        "transport_aircraft": "Транспортные самолеты",
        "attack_helicopters": "Ударные вертолеты",
        "transport_helicopters": "Транспортные вертолеты",
        "recon_uav": "Разведывательные БПЛА",
        "attack_uav": "Ударные БПЛА",
        "kamikaze_uav": "Дроны-камикадзе"
    },
    "military_navy": {
        "boats": "Катера",
        "corvettes": "Корветы",
        "destroyers": "Эсминцы",
        "cruisers": "Крейсера",
        "aircraft_carriers": "Авианосцы",
        "submarines": "Подводные лодки"
    },
    "military_missiles": {
        "strategic_nuclear": "Стратегическое ядерное оружие",
        "tactical_nuclear": "Тактическое ядерное оружие",
        "cruise_missiles": "Крылатые ракеты",
        "hypersonic_missiles": "Гиперзвуковые ракеты",
        "ballistic_missiles": "Баллистические ракеты",
        "missiles": "Ракетное вооружение"
    },
    "military_equipment": {
        "small_arms": "Стрелковое оружие",
        "grenade_launchers": "Гранатометы",
        "atgms": "Переносные ПТРК",
        "manpads": "ПЗРК",
        "medical_equipment": "Медицинское оборудование",
        "engineering_equipment_units": "Инженерное снаряжение",
        "fpv_drones": "FPV-дроны"
    },
    "civil_transport": {
        "cars": "Легковые автомобили",
        "trucks": "Грузовики",
        "buses": "Автобусы",
        "auto_parts": "Автозапчасти",
        "agricultural_machinery": "Сельхозтехника",
        "construction_machinery": "Строительная техника",
        "drones": "Гражданские дроны"
    },
    "civil_industry": {
        "industrial_equipment": "Промышленное оборудование",
        "machine_tools": "Станки",
        "industrial_robots": "Промышленные роботы",
        "energy_equipment": "Энергетическое оборудование",
        "electrical_equipment": "Электротехника",
        "telecom_equipment": "Телекоммуникационное оборудование",
        "tech_equipment": "Технологическое оборудование",
        "aerospace_equipment": "Авиакосмическое оборудование",
        "chemicals": "Химическая продукция",
        "fertilizers": "Удобрения"
    },
    "civil_medicine": {
        "pharmaceuticals": "Лекарства",
        "medical_supplies": "Медицинские изделия",
        "medical_equipment": "Медицинское оборудование",
        "sanitary_products": "Санитарно-гигиенические средства"
    },
    "civil_electronics": {
        "consumer_electronics": "Бытовая электроника",
        "computers": "Компьютеры",
        "smartphones": "Смартфоны",
        "tablets": "Планшеты",
        "electronics": "Электронные компоненты",
        "electronics_components": "Комплектующие"
    },
    "civil_goods": {
        "clothing": "Одежда",
        "footwear": "Обувь",
        "furniture": "Мебель",
        "household_goods": "Товары для дома",
        "cosmetics": "Косметика"
    },
    "civil_food": {
        "food_products": "Продукты питания",
        "beverages": "Напитки",
        "food": "Продовольствие"
    },
    "resources": {
        "steel": "Сталь",
        "aluminum": "Алюминий",
        "uranium": "Уран",
        "electronics": "Электроника",
        "rare_metals": "Редкие металлы",
        "oil": "Нефть",
        "gas": "Газ",
        "coal": "Уголь"
    }
}

# Плоский словарь для обратной совместимости
PRODUCT_CATEGORIES = {}
for category, products in PRODUCT_SUBCATEGORIES.items():
    for product_id, product_name in products.items():
        PRODUCT_CATEGORIES[product_id] = product_name

# ==================== КАСТОМНЫЕ ЭМОДЗИ ====================

TARIFF_EMOJIS = {
    "base": "<:money:1429345094695129088>",
    "import": "<:logistic:1492864675808022628>",
    "export": "<:Telecommunication:1492864324975464548>",
    "embargo": "<:ukrep:1492864074634100938>",
    "sanction": "<:crisis:1487167453443391509>",
    "agreement": "<:eco_baff:1492879901760421888>",
    "war": "<:ZRK:1492864585995255808>",
    "success": "<:eco_baff:1492879901760421888>",
    "error": "<:smert:1492913346859765892>",
    "warning": "<:crisis:1487167453443391509>",
    "military": "<:Military_factory:1492864212085506068>",
    "civil": "<:Civilian_factory:1492864140501323986>",
    "resources": "<:Oil:1262014013273935872>",
}

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_tariffs():
    """Загрузка таможенных политик всех государств"""
    global _tariff_cache, _tariff_cache_time
    now = datetime.now().timestamp()
    
    cache_key = 'all_tariffs'
    if cache_key in _tariff_cache and now - _tariff_cache_time.get(cache_key, 0) < CACHE_TTL:
        return _tariff_cache[cache_key]
    
    try:
        with open(TARIFFS_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                result = {"tariffs": {}}
            else:
                data = json.loads(content)
                
                if not isinstance(data, dict):
                    result = {"tariffs": {}}
                elif "tariffs" not in data:
                    data["tariffs"] = {}
                    result = data
                else:
                    result = data
            
            _tariff_cache[cache_key] = result
            _tariff_cache_time[cache_key] = now
            return result
    except (FileNotFoundError, json.JSONDecodeError):
        result = {"tariffs": {}}
        _tariff_cache[cache_key] = result
        _tariff_cache_time[cache_key] = now
        return result

def save_tariffs(data):
    """Сохранение таможенных политик"""
    global _tariff_cache
    try:
        with open(TARIFFS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        _tariff_cache.pop('all_tariffs', None)
    except Exception as e:
        print(f"Ошибка сохранения tariffs.json: {e}")

def get_country_tariffs(country_name: str) -> Dict:
    """Получить таможенную политику страны"""
    global _tariff_cache, _tariff_cache_time
    now = datetime.now().timestamp()
    
    cache_key = f'country_{country_name}'
    if cache_key in _tariff_cache and now - _tariff_cache_time.get(cache_key, 0) < CACHE_TTL:
        return _tariff_cache[cache_key]
    
    tariffs_data = load_tariffs()
    
    if country_name not in tariffs_data["tariffs"]:
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
    
    result = tariffs_data["tariffs"][country_name]
    _tariff_cache[cache_key] = result
    _tariff_cache_time[cache_key] = now
    
    return result

def update_country_tariffs(country_name: str, tariffs: Dict):
    """Обновить таможенную политику страны"""
    tariffs_data = load_tariffs()
    tariffs_data["tariffs"][country_name] = tariffs
    tariffs_data["tariffs"][country_name]["last_updated"] = str(datetime.now())
    save_tariffs(tariffs_data)
    
    global _tariff_cache
    _tariff_cache.pop(f'country_{country_name}', None)


# ==================== КЛАСС TARIFFSYSTEM ====================

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
        if self.is_product_embargoed(origin_country, product_type):
            return value
        
        sanction_penalty = self.get_sanction_penalty(origin_country)
        
        if origin_country in self.tariffs.get("trade_agreements", []):
            base_rate = 0.0
        else:
            if origin_country in self.tariffs.get("specific_tariffs", {}):
                base_rate = self.tariffs["specific_tariffs"][origin_country]
            elif product_type in self.tariffs.get("product_tariffs", {}):
                base_rate = self.tariffs["product_tariffs"][product_type]
            elif origin_country in self.tariffs.get("trade_wars", {}):
                base_rate = self.tariffs["trade_wars"][origin_country]
            else:
                base_rate = self.tariffs.get("base_tariff", 5.0)
        
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
    
    def set_base_tariff(self, rate: float) -> Tuple[bool, str]:
        """Установить базовый тариф"""
        if rate < 0 or rate > 200:
            return False, f"{TARIFF_EMOJIS['error']} Ставка должна быть от 0 до 200%"
        self.tariffs["base_tariff"] = rate
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"{TARIFF_EMOJIS['success']} Базовый тариф установлен на {rate}%"
    
    def set_country_tariff(self, country: str, rate: float) -> Tuple[bool, str]:
        """Установить специфический тариф для страны"""
        if rate < 0 or rate > 200:
            return False, f"{TARIFF_EMOJIS['error']} Ставка должна быть от 0 до 200%"
        if rate == 0:
            if country in self.tariffs.get("specific_tariffs", {}):
                del self.tariffs["specific_tariffs"][country]
                update_country_tariffs(self.country_name, self.tariffs)
                return True, f"{TARIFF_EMOJIS['success']} Тариф для {country} удалён (беспошлинная торговля)"
            else:
                return False, f"{TARIFF_EMOJIS['error']} Для {country} не было установлено тарифа"
        else:
            if "specific_tariffs" not in self.tariffs:
                self.tariffs["specific_tariffs"] = {}
            self.tariffs["specific_tariffs"][country] = rate
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"{TARIFF_EMOJIS['warning']} Тариф для {country} установлен на {rate}%"
    
    def set_product_tariff(self, product_type: str, rate: float) -> Tuple[bool, str]:
        """Установить импортную пошлину на тип продукта"""
        if rate < 0 or rate > 200:
            return False, f"{TARIFF_EMOJIS['error']} Ставка должна быть от 0 до 200%"
        if rate == 0:
            if product_type in self.tariffs.get("product_tariffs", {}):
                del self.tariffs["product_tariffs"][product_type]
                product_name = PRODUCT_CATEGORIES.get(product_type, product_type)
                update_country_tariffs(self.country_name, self.tariffs)
                return True, f"{TARIFF_EMOJIS['success']} Импортная пошлина на {product_name} удалена"
            else:
                return False, f"{TARIFF_EMOJIS['error']} Для этого товара не было установлено пошлины"
        else:
            if "product_tariffs" not in self.tariffs:
                self.tariffs["product_tariffs"] = {}
            self.tariffs["product_tariffs"][product_type] = rate
            update_country_tariffs(self.country_name, self.tariffs)
            product_name = PRODUCT_CATEGORIES.get(product_type, product_type)
            return True, f"{TARIFF_EMOJIS['warning']} Импортная пошлина на {product_name} установлена на {rate}%"
    
    def set_export_tariff(self, product_type: str, rate: float) -> Tuple[bool, str]:
        """Установить экспортную пошлину на тип продукта"""
        if rate < 0 or rate > 100:
            return False, f"{TARIFF_EMOJIS['error']} Ставка должна быть от 0 до 100%"
        if rate == 0:
            if product_type in self.tariffs.get("export_tariffs", {}):
                del self.tariffs["export_tariffs"][product_type]
                product_name = PRODUCT_CATEGORIES.get(product_type, product_type)
                update_country_tariffs(self.country_name, self.tariffs)
                return True, f"{TARIFF_EMOJIS['success']} Экспортная пошлина на {product_name} удалена"
            else:
                return False, f"{TARIFF_EMOJIS['error']} Для этого товара не было установлено пошлины"
        else:
            if "export_tariffs" not in self.tariffs:
                self.tariffs["export_tariffs"] = {}
            self.tariffs["export_tariffs"][product_type] = rate
            update_country_tariffs(self.country_name, self.tariffs)
            product_name = PRODUCT_CATEGORIES.get(product_type, product_type)
            return True, f"{TARIFF_EMOJIS['success']} Экспортная пошлина на {product_name} установлена на {rate}%"
    
    def add_trade_agreement(self, country: str) -> Tuple[bool, str]:
        """Добавить страну в зону беспошлинной торговли"""
        if country == self.country_name:
            return False, f"{TARIFF_EMOJIS['error']} Нельзя добавить свою страну в торговое соглашение"
        if "trade_agreements" not in self.tariffs:
            self.tariffs["trade_agreements"] = []
        if country not in self.tariffs["trade_agreements"]:
            self.tariffs["trade_agreements"].append(country)
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"{TARIFF_EMOJIS['agreement']} {country} добавлена в зону беспошлинной торговли"
        return False, f"{TARIFF_EMOJIS['error']} {country} уже в зоне беспошлинной торговли"
    
    def remove_trade_agreement(self, country: str) -> Tuple[bool, str]:
        """Удалить страну из зоны беспошлинной торговли"""
        if "trade_agreements" in self.tariffs and country in self.tariffs["trade_agreements"]:
            self.tariffs["trade_agreements"].remove(country)
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"{TARIFF_EMOJIS['success']} {country} удалена из зоны беспошлинной торговли"
        return False, f"{TARIFF_EMOJIS['error']} {country} не в зоне беспошлинной торговли"
    
    def declare_trade_war(self, country: str, rate: float) -> Tuple[bool, str]:
        """Объявить торговую войну"""
        if country == self.country_name:
            return False, f"{TARIFF_EMOJIS['error']} Нельзя объявить торговую войну своей стране"
        if rate < 0 or rate > 200:
            return False, f"{TARIFF_EMOJIS['error']} Ставка должна быть от 0 до 200%"
        if "trade_wars" not in self.tariffs:
            self.tariffs["trade_wars"] = {}
        self.tariffs["trade_wars"][country] = rate
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"{TARIFF_EMOJIS['war']} Торговая война объявлена {country} с тарифом {rate}%"
    
    def end_trade_war(self, country: str) -> Tuple[bool, str]:
        """Завершить торговую войну"""
        if "trade_wars" in self.tariffs and country in self.tariffs["trade_wars"]:
            del self.tariffs["trade_wars"][country]
            update_country_tariffs(self.country_name, self.tariffs)
            return True, f"{TARIFF_EMOJIS['success']} Торговая война с {country} завершена"
        return False, f"{TARIFF_EMOJIS['error']} Нет активной торговой войны с {country}"
    
    def set_embargo(self, country: str, categories: List[str]) -> Tuple[bool, str]:
        """Установить эмбарго на конкретные категории товаров"""
        if country == self.country_name:
            return False, f"{TARIFF_EMOJIS['error']} Нельзя наложить эмбарго на свою страну!"
            
        if "embargoes" not in self.tariffs:
            self.tariffs["embargoes"] = {}
        
        if "all" in categories:
            self.tariffs["embargoes"][country] = ["all"]
            update_country_tariffs(self.country_name, self.tariffs)
            
            # АВТОМАТИЧЕСКАЯ ЗАМОРОЗКА АКТИВОВ ПРИ ПОЛНОМ ЭМБАРГО
            try:
                from infra_build import freeze_assets_on_embargo
                asyncio.create_task(freeze_assets_on_embargo(self.country_name, country))
            except ImportError:
                pass
            
            return True, f"{TARIFF_EMOJIS['embargo']} Полное эмбарго установлено на {country}. Все активы заморожены."
        else:
            valid_categories = []
            for cat in categories:
                if cat in PRODUCT_CATEGORIES or cat == "military" or cat == "civil":
                    valid_categories.append(cat)
            
            if not valid_categories:
                return False, f"{TARIFF_EMOJIS['error']} Не указано ни одной допустимой категории"
            
            self.tariffs["embargoes"][country] = valid_categories
            update_country_tariffs(self.country_name, self.tariffs)
            cat_names = ", ".join([PRODUCT_CATEGORIES.get(c, c) for c in valid_categories[:3]])
            if len(valid_categories) > 3:
                cat_names += f" и ещё {len(valid_categories)-3}"
            return True, f"{TARIFF_EMOJIS['embargo']} Эмбарго на {cat_names} установлено на {country}"
    
    def remove_embargo(self, country: str) -> Tuple[bool, str]:
        """Полностью снять эмбарго со страны"""
        if "embargoes" in self.tariffs and country in self.tariffs["embargoes"]:
            was_full_embargo = "all" in self.tariffs["embargoes"][country]
            del self.tariffs["embargoes"][country]
            update_country_tariffs(self.country_name, self.tariffs)
            
            # АВТОМАТИЧЕСКАЯ РАЗМОРОЗКА АКТИВОВ ПРИ СНЯТИИ ЭМБАРГО
            if was_full_embargo:
                try:
                    from infra_build import unfreeze_assets_on_embargo_removal
                    asyncio.create_task(unfreeze_assets_on_embargo_removal(self.country_name, country))
                except ImportError:
                    pass
            
            return True, f"{TARIFF_EMOJIS['success']} Эмбарго с {country} полностью снято. Активы разморожены."
        return False, f"{TARIFF_EMOJIS['error']} Нет эмбарго с {country}"
    
    def remove_embargo_category(self, country: str, category: str) -> Tuple[bool, str]:
        """Снять эмбарго с конкретной категории товаров"""
        if "embargoes" not in self.tariffs or country not in self.tariffs["embargoes"]:
            return False, f"{TARIFF_EMOJIS['error']} Нет эмбарго с {country}"
        
        categories = self.tariffs["embargoes"][country]
        
        if "all" in categories:
            return False, f"{TARIFF_EMOJIS['error']} Установлено полное эмбарго. Используйте снятие всего эмбарго"
        
        if category not in categories:
            return False, f"{TARIFF_EMOJIS['error']} Категория {PRODUCT_CATEGORIES.get(category, category)} не под эмбарго"
        
        categories.remove(category)
        
        if not categories:
            del self.tariffs["embargoes"][country]
        else:
            self.tariffs["embargoes"][country] = categories
        
        update_country_tariffs(self.country_name, self.tariffs)
        return True, f"{TARIFF_EMOJIS['success']} Эмбарго с {PRODUCT_CATEGORIES.get(category, category)} для {country} снято"
    
    def get_embargoed_categories(self, country: str) -> List[str]:
        """Получить список категорий под эмбарго для страны"""
        embargoes = self.tariffs.get("embargoes", {})
        result = embargoes.get(country, [])
        if isinstance(result, dict):
            return []
        return result
    
    def is_product_embargoed(self, country: str, product_type: str) -> bool:
        """
        Проверяет, подпадает ли продукт под эмбарго
        country - страна-производитель (откуда товар)
        """
        embargoed_categories = self.get_embargoed_categories(country)
        
        if not embargoed_categories:
            return False
        
        if "all" in embargoed_categories:
            return True
        
        main_category = product_type.split('.')[0] if '.' in product_type else product_type
        
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
        
        if "civil" in embargoed_categories:
            civil_categories = ["cars", "trucks", "buses", "agricultural_machinery", 
                               "construction_machinery", "industrial_equipment", 
                               "food_products", "clothing", "electronics", "chemicals",
                               "pharmaceuticals", "medical_equipment", "consumer_electronics",
                               "furniture", "household_goods", "food", "oil", "gas", "coal",
                               "steel", "aluminum", "uranium", "rare_metals"]
            if main_category in civil_categories or product_type in civil_categories:
                return True
        
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
                            embargoed_categories = self.get_embargoed_categories(corp_country)
                            
                            if "all" in embargoed_categories:
                                continue
                            
                            available.append(corp)
                        else:
                            available.append(corp)
                elif isinstance(corps_dict, list):
                    for corp in corps_dict:
                        if hasattr(corp, 'country'):
                            corp_country = corp.country
                            embargoed_categories = self.get_embargoed_categories(corp_country)
                            
                            if "all" in embargoed_categories:
                                continue
                            
                            available.append(corp)
                        else:
                            available.append(corp)
        elif isinstance(all_corporations, list):
            for corp in all_corporations:
                if hasattr(corp, 'country'):
                    corp_country = corp.country
                    embargoed_categories = self.get_embargoed_categories(corp_country)
                    
                    if "all" in embargoed_categories:
                        continue
                    
                    available.append(corp)
                else:
                    available.append(corp)
        
        return available
    
    def set_sanctions(self, country: str, penalty: float, reason: str = "") -> Tuple[bool, str]:
        """Установить санкции против страны"""
        if penalty < 0 or penalty > 100:
            return False, f"{TARIFF_EMOJIS['error']} Штраф должен быть от 0 до 100%"
        
        if "sanctions" not in self.tariffs:
            self.tariffs["sanctions"] = {}
        
        self.tariffs["sanctions"][country] = {
            "penalty": penalty,
            "reason": reason,
            "date": str(datetime.now())
        }
        update_country_tariffs(self.country_name, self.tariffs)
        
        # Если штраф >= 90%, автоматически замораживаем активы
        if penalty >= 90:
            try:
                from infra_build import freeze_assets_on_embargo
                asyncio.create_task(freeze_assets_on_embargo(self.country_name, country))
            except ImportError:
                pass
            return True, f"{TARIFF_EMOJIS['sanction']} Жёсткие санкции против {country} установлены (штраф {penalty}%). Активы заморожены."
        
        return True, f"{TARIFF_EMOJIS['sanction']} Санкции против {country} установлены (штраф {penalty}%)"
    
    def remove_sanctions(self, country: str) -> Tuple[bool, str]:
        """Снять санкции с страны"""
        if "sanctions" in self.tariffs and country in self.tariffs["sanctions"]:
            old_penalty = self.tariffs["sanctions"][country].get("penalty", 0)
            del self.tariffs["sanctions"][country]
            update_country_tariffs(self.country_name, self.tariffs)
            
            # Если были жёсткие санкции - размораживаем активы
            if old_penalty >= 90:
                try:
                    from infra_build import unfreeze_assets_on_embargo_removal
                    asyncio.create_task(unfreeze_assets_on_embargo_removal(self.country_name, country))
                except ImportError:
                    pass
                return True, f"{TARIFF_EMOJIS['success']} Санкции с {country} сняты. Активы разморожены."
            
            return True, f"{TARIFF_EMOJIS['success']} Санкции с {country} сняты"
        return False, f"{TARIFF_EMOJIS['error']} Нет санкций против {country}"
    
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
            title=f"Таможенная политика {self.country_name}",
            color=DARK_THEME_COLOR
        )
        
        embed.add_field(
            name=f"{TARIFF_EMOJIS['base']} Базовый тариф",
            value=f"{self.tariffs.get('base_tariff', 5)}%",
            inline=True
        )
        
        specific_tariffs = self.tariffs.get("specific_tariffs", {})
        if specific_tariffs and isinstance(specific_tariffs, dict):
            friendly = []
            hostile = []
            for country, rate in specific_tariffs.items():
                if rate == 0:
                    friendly.append(f"{country}")
                elif rate >= 100:
                    hostile.append(f"{country} (100%)")
                elif rate >= 50:
                    hostile.append(f"{country} ({rate}%)")
                else:
                    hostile.append(f"{country} ({rate}%)")
            
            if friendly:
                embed.add_field(
                    name=f"{TARIFF_EMOJIS['agreement']} Беспошлинная торговля",
                    value="\n".join(friendly[:5]) + (" и др." if len(friendly) > 5 else ""),
                    inline=True
                )
            
            if hostile:
                hostile_text = "\n".join(hostile[:5])
                if len(hostile) > 5:
                    hostile_text += f"\nи ещё {len(hostile)-5}"
                embed.add_field(
                    name=f"{TARIFF_EMOJIS['import']} Импортные пошлины (по странам)",
                    value=hostile_text,
                    inline=True
                )
        
        product_tariffs = self.tariffs.get("product_tariffs", {})
        if product_tariffs and isinstance(product_tariffs, dict):
            product_text = ""
            product_items = list(product_tariffs.items())
            for product, rate in product_items[:5]:
                product_name = PRODUCT_CATEGORIES.get(product, product)
                if rate >= 100:
                    product_text += f"{product_name}: {rate}%\n"
                elif rate >= 50:
                    product_text += f"{product_name}: {rate}%\n"
                else:
                    product_text += f"{product_name}: {rate}%\n"
            if product_text:
                embed.add_field(name=f"{TARIFF_EMOJIS['import']} Импортные пошлины (по товарам)", value=product_text, inline=True)
        
        export_tariffs = self.tariffs.get("export_tariffs", {})
        if export_tariffs and isinstance(export_tariffs, dict):
            export_tariff_text = ""
            export_items = list(export_tariffs.items())
            for product, rate in export_items[:5]:
                product_name = PRODUCT_CATEGORIES.get(product, product)
                export_tariff_text += f"{product_name}: {rate}%\n"
            if export_tariff_text:
                embed.add_field(name=f"{TARIFF_EMOJIS['export']} Экспортные пошлины", value=export_tariff_text, inline=True)
        
        embargoes = self.tariffs.get("embargoes", {})
        if embargoes and isinstance(embargoes, dict):
            embargo_text = ""
            embargo_items = list(embargoes.items())
            for country, embargo_data in embargo_items[:3]:
                if isinstance(embargo_data, dict) and embargo_data.get("active", False):
                    embargo_text += f"{country}: ПОЛНОЕ\n"
                elif isinstance(embargo_data, list):
                    if "all" in embargo_data:
                        embargo_text += f"{country}: ПОЛНОЕ (активы заморожены)\n"
                    else:
                        cat_names = [PRODUCT_CATEGORIES.get(c, c) for c in embargo_data[:2]]
                        cat_text = ", ".join(cat_names)
                        if len(embargo_data) > 2:
                            cat_text += f" и ещё {len(embargo_data)-2}"
                        embargo_text += f"{country}: {cat_text}\n"
            if embargo_text:
                embed.add_field(name=f"{TARIFF_EMOJIS['embargo']} Эмбарго", value=embargo_text, inline=True)
        
        trade_agreements = self.tariffs.get("trade_agreements", [])
        if trade_agreements and isinstance(trade_agreements, list):
            agreements = ", ".join(trade_agreements[:5])
            embed.add_field(name=f"{TARIFF_EMOJIS['agreement']} Беспошлинная торговля", value=agreements, inline=False)
        
        trade_wars = self.tariffs.get("trade_wars", {})
        if trade_wars and isinstance(trade_wars, dict):
            wars_text = ""
            for country, rate in list(trade_wars.items())[:5]:
                wars_text += f"{country}: {rate}%\n"
            if wars_text:
                embed.add_field(name=f"{TARIFF_EMOJIS['war']} Торговые войны", value=wars_text, inline=False)
        
        sanctions = self.tariffs.get("sanctions", {})
        if sanctions and isinstance(sanctions, dict):
            sanctions_text = ""
            for country, data in list(sanctions.items())[:5]:
                if isinstance(data, dict):
                    penalty = data.get('penalty', 0)
                    if penalty >= 90:
                        sanctions_text += f"{country}: +{penalty}% (активы заморожены)\n"
                    elif penalty >= 50:
                        sanctions_text += f"{country}: +{penalty}%\n"
                    else:
                        sanctions_text += f"{country}: +{penalty}%\n"
                else:
                    sanctions_text += f"{country}: +{data}%\n"
            if sanctions_text:
                embed.add_field(name=f"{TARIFF_EMOJIS['sanction']} Санкции", value=sanctions_text, inline=False)
        
        return embed


# ==================== ФУНКЦИЯ ДЛЯ ПРОВЕРКИ ДОСТУПНОСТИ КОРПОРАЦИИ ====================

def is_corporation_available(buyer_country: str, corporation_country: str) -> bool:
    """
    Проверяет, доступна ли корпорация из указанной страны для покупателя
    """
    tariff_system = TariffSystem(buyer_country)
    
    embargoed_categories = tariff_system.get_embargoed_categories(corporation_country)
    
    if "all" in embargoed_categories:
        return False
    
    return True


# ==================== ФУНКЦИЯ ДЛЯ РАСЧЁТА ТОРГОВЛИ ====================

def calculate_trade_with_tariffs(trade_data: Dict, seller_country: str, buyer_country: str) -> Dict:
    """Рассчитывает торговую сделку с учётом тарифов"""
    buyer_tariffs = TariffSystem(buyer_country)
    seller_tariffs = TariffSystem(seller_country)
    
    if buyer_tariffs.is_product_embargoed(seller_country, trade_data.get("resource", "")):
        return {
            "blocked": True,
            "reason": f"{TARIFF_EMOJIS['embargo']} Ваша страна ввела эмбарго против {seller_country}"
        }
    
    if seller_tariffs.is_product_embargoed(buyer_country, trade_data.get("resource", "")):
        return {
            "blocked": True,
            "reason": f"{TARIFF_EMOJIS['embargo']} Страна {seller_country} ввела эмбарго против вашей страны"
        }
    
    import_tariff = buyer_tariffs.calculate_import_tariff(
        trade_data.get("resource", ""), 
        seller_country, 
        trade_data["total_price"]
    )
    
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
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        try:
            rate = float(self.rate_input.value)
        except ValueError:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Введите корректное число!", ephemeral=True)
            return
        
        success, message = self.tariff_system.set_base_tariff(rate)
        
        if success:
            embed = discord.Embed(
                title="Тариф изменён",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class CountryTariffModal(Modal, title="Изменить импортную пошлину для страны"):
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
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        try:
            rate = float(self.rate_input.value)
        except ValueError:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Введите корректное число!", ephemeral=True)
            return
        
        success, message = self.tariff_system.set_country_tariff(self.country, rate)
        
        if success:
            embed = discord.Embed(
                title="Импортная пошлина изменена",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class ImportProductTariffModal(Modal, title="Изменить импортную пошлину для товара"):
    def __init__(self, user_id: int, tariff_system: TariffSystem, product_id: str, product_name: str):
        super().__init__()
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.product_id = product_id
        self.product_name = product_name
        
        current_rate = tariff_system.tariffs.get("product_tariffs", {}).get(product_id, 0)
        
        self.rate_input = TextInput(
            label=f"Ставка для {product_name} (текущая: {current_rate}%)",
            placeholder="Введите число от 0 до 200 (0 для удаления)",
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.rate_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        try:
            rate = float(self.rate_input.value)
        except ValueError:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Введите корректное число!", ephemeral=True)
            return
        
        success, message = self.tariff_system.set_product_tariff(self.product_id, rate)
        
        if success:
            embed = discord.Embed(
                title="Импортная пошлина изменена",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class ExportProductTariffModal(Modal, title="Изменить экспортную пошлину для товара"):
    def __init__(self, user_id: int, tariff_system: TariffSystem, product_id: str, product_name: str):
        super().__init__()
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.product_id = product_id
        self.product_name = product_name
        
        current_rate = tariff_system.tariffs.get("export_tariffs", {}).get(product_id, 0)
        
        self.rate_input = TextInput(
            label=f"Ставка для {product_name} (текущая: {current_rate}%)",
            placeholder="Введите число от 0 до 100 (0 для удаления)",
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.rate_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        try:
            rate = float(self.rate_input.value)
        except ValueError:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Введите корректное число!", ephemeral=True)
            return
        
        success, message = self.tariff_system.set_export_tariff(self.product_id, rate)
        
        if success:
            embed = discord.Embed(
                title="Экспортная пошлина изменена",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class EmbargoSetModal(Modal, title="Установка эмбарго"):
    def __init__(self, user_id: int, tariff_system: TariffSystem, country: str):
        super().__init__()
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.country = country
        
        self.categories_input = TextInput(
            label="Категории (через запятую)",
            placeholder="Например: all, military, tanks, fighters",
            min_length=1,
            max_length=100,
            required=True
        )
        self.add_item(self.categories_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        categories_text = self.categories_input.value.lower()
        categories = [cat.strip() for cat in categories_text.split(',')]
        
        success, message = self.tariff_system.set_embargo(self.country, categories)
        
        if success:
            embed = discord.Embed(
                title="Эмбарго установлено",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class SanctionsModal(Modal, title="Установка санкций"):
    def __init__(self, user_id: int, tariff_system: TariffSystem, country: str):
        super().__init__()
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.country = country
        
        current = tariff_system.tariffs.get("sanctions", {}).get(country, {})
        current_penalty = current.get("penalty", 0) if isinstance(current, dict) else current
        
        self.penalty_input = TextInput(
            label=f"Штраф % (текущий: {current_penalty}%)",
            placeholder="Введите число от 0 до 100",
            min_length=1,
            max_length=5,
            required=True
        )
        self.add_item(self.penalty_input)
        
        self.reason_input = TextInput(
            label="Причина (необязательно)",
            placeholder="Например: Нарушение прав человека",
            min_length=0,
            max_length=100,
            required=False
        )
        self.add_item(self.reason_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        try:
            penalty = float(self.penalty_input.value)
        except ValueError:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Введите корректное число!", ephemeral=True)
            return
        
        reason = self.reason_input.value.strip() if self.reason_input.value else ""
        
        success, message = self.tariff_system.set_sanctions(self.country, penalty, reason)
        
        if success:
            embed = discord.Embed(
                title="Санкции установлены",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


class CountrySelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, callback_func, placeholder="Выберите страну..."):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.custom_callback = callback_func
        
        countries = ["США", "Россия", "Китай", "Германия", "Великобритания", 
                     "Франция", "Япония", "Израиль", "Украина", "Иран", "Беларусь",
                     "Норвегия", "Турция", "Сирия", "Канада", "Польша", "Бразилия",
                     "Швеция", "Финляндия", "Швейцария", "КНДР", "Египет"]
        
        options = []
        for country in countries:
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
            
            if len(options) >= 25:
                break
        
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.custom_callback(interaction, self.values[0])


class ImportCategorySelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, callback_func):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.custom_callback = callback_func
        
        options = []
        for category_id, category_name in PRODUCT_MAIN_CATEGORIES.items():
            product_count = len(PRODUCT_SUBCATEGORIES.get(category_id, {}))
                
            options.append(
                discord.SelectOption(
                    label=category_name,
                    description=f"{product_count} товаров",
                    value=category_id
                )
            )
            
            if len(options) >= 25:
                break
        
        super().__init__(
            placeholder="Выберите категорию товаров...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.custom_callback(interaction, self.values[0])


class ImportProductSelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, category_id: str, callback_func):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.category_id = category_id
        self.custom_callback = callback_func
        
        products = PRODUCT_SUBCATEGORIES.get(category_id, {})
        
        options = []
        for product_id, product_name in products.items():
            current_rate = tariff_system.tariffs.get("product_tariffs", {}).get(product_id, 0)
                
            options.append(
                discord.SelectOption(
                    label=product_name,
                    description=f"Текущий тариф: {current_rate}%" if current_rate > 0 else "Без тарифа",
                    value=product_id
                )
            )
            
            if len(options) >= 25:
                break
        
        super().__init__(
            placeholder="Выберите товар...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.custom_callback(interaction, self.values[0])


class ExportCategorySelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, callback_func):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.custom_callback = callback_func
        
        export_categories = {
            "resources": "Ресурсы",
            "military_ground": "Сухопутная техника",
            "military_air": "Авиация",
            "civil_transport": "Транспорт",
            "civil_industry": "Промышленность",
            "civil_food": "Продукты питания"
        }
        
        options = []
        for category_id, category_name in export_categories.items():
            options.append(
                discord.SelectOption(
                    label=category_name,
                    value=category_id
                )
            )
            
            if len(options) >= 25:
                break
        
        super().__init__(
            placeholder="Выберите категорию для экспортной пошлины...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.custom_callback(interaction, self.values[0])


class ExportProductSelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, category_id: str, callback_func):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.category_id = category_id
        self.custom_callback = callback_func
        
        products = PRODUCT_SUBCATEGORIES.get(category_id, {})
        
        options = []
        for product_id, product_name in products.items():
            current_rate = tariff_system.tariffs.get("export_tariffs", {}).get(product_id, 0)
            
            options.append(
                discord.SelectOption(
                    label=product_name,
                    description=f"Текущая пошлина: {current_rate}%" if current_rate > 0 else "Без пошлины",
                    value=product_id
                )
            )
            
            if len(options) >= 25:
                break
        
        super().__init__(
            placeholder="Выберите товар...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        await self.custom_callback(interaction, self.values[0])


class EmbargoCountrySelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, action: str):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.action = action
        
        countries = ["США", "Россия", "Китай", "Германия", "Великобритания", 
                     "Франция", "Япония", "Израиль", "Украина", "Иран", "Беларусь",
                     "Норвегия", "Турция", "Сирия", "Канада", "Польша", "Бразилия",
                     "Швеция", "Финляндия", "Швейцария", "КНДР", "Египет"]
        
        options = []
        for country in countries:
            if country == tariff_system.country_name:
                continue
                
            if action == "set":
                description = "Установить эмбарго"
            else:
                embargoed = tariff_system.get_embargoed_categories(country)
                if embargoed:
                    if "all" in embargoed:
                        description = "Полное эмбарго (активы заморожены)"
                    else:
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
            
            if len(options) >= 25:
                break
        
        super().__init__(
            placeholder="Выберите страну...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        country = self.values[0]
        
        if self.action == "set":
            modal = EmbargoSetModal(self.user_id, self.tariff_system, country)
            await interaction.response.send_modal(modal)
        else:
            success, message = self.tariff_system.remove_embargo(country)
            if success:
                embed = discord.Embed(
                    title="Эмбарго снято",
                    description=message,
                    color=DARK_THEME_COLOR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)


class SanctionCountrySelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, action: str):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.action = action
        
        countries = ["США", "Россия", "Китай", "Германия", "Великобритания", 
                     "Франция", "Япония", "Израиль", "Украина", "Иран", "Беларусь",
                     "Норвегия", "Турция", "Сирия", "Канада", "Польша", "Бразилия",
                     "Швеция", "Финляндия", "Швейцария", "КНДР", "Египет"]
        
        options = []
        for country in countries:
            if country == tariff_system.country_name:
                continue
                
            if action == "set":
                description = "Установить санкции"
            else:
                sanctions = tariff_system.tariffs.get("sanctions", {})
                if country in sanctions:
                    penalty = sanctions[country].get("penalty", 0) if isinstance(sanctions[country], dict) else sanctions[country]
                    description = f"Штраф: {penalty}%"
                else:
                    description = "Нет санкций"
            
            options.append(
                discord.SelectOption(
                    label=country,
                    description=description,
                    value=country
                )
            )
            
            if len(options) >= 25:
                break
        
        super().__init__(
            placeholder="Выберите страну...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        country = self.values[0]
        
        if self.action == "set":
            modal = SanctionsModal(self.user_id, self.tariff_system, country)
            await interaction.response.send_modal(modal)
        else:
            success, message = self.tariff_system.remove_sanctions(country)
            if success:
                embed = discord.Embed(
                    title="Санкции сняты",
                    description=message,
                    color=DARK_THEME_COLOR
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)


class TradeAgreementSelect(Select):
    def __init__(self, user_id: int, tariff_system: TariffSystem, action: str):
        self.user_id = user_id
        self.tariff_system = tariff_system
        self.action = action
        
        countries = ["США", "Россия", "Китай", "Германия", "Великобритания", 
                     "Франция", "Япония", "Израиль", "Украина", "Иран", "Беларусь",
                     "Норвегия", "Турция", "Сирия", "Канада", "Польша", "Бразилия",
                     "Швеция", "Финляндия", "Швейцария", "КНДР", "Египет"]
        
        options = []
        for country in countries:
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
            
            if len(options) >= 25:
                break
        
        super().__init__(
            placeholder="Выберите страну...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        country = self.values[0]
        
        if self.action == "add":
            success, message = self.tariff_system.add_trade_agreement(country)
        else:
            success, message = self.tariff_system.remove_trade_agreement(country)
        
        if success:
            embed = discord.Embed(
                title="Торговое соглашение обновлено",
                description=message,
                color=DARK_THEME_COLOR
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)


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
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = self.tariff_system.get_tariff_summary_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Базовый тариф", style=discord.ButtonStyle.secondary)
    async def base_tariff_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        modal = BaseTariffModal(self.user_id, self.tariff_system)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Импорт (по странам)", style=discord.ButtonStyle.secondary)
    async def country_import_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Импортные пошлины по странам",
            description="Выберите страну для изменения импортной пошлины:",
            color=DARK_THEME_COLOR
        )
        
        async def country_callback(interaction, country):
            modal = CountryTariffModal(self.user_id, self.tariff_system, country)
            await interaction.response.send_modal(modal)
        
        select = CountrySelect(self.user_id, self.tariff_system, country_callback, "Выберите страну...")
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Импорт (по товарам)", style=discord.ButtonStyle.secondary)
    async def product_import_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Импортные пошлины по товарам",
            description="Выберите категорию товаров:",
            color=DARK_THEME_COLOR
        )
        
        async def category_callback(interaction, category_id):
            await self.show_import_products(interaction, category_id)
        
        select = ImportCategorySelect(self.user_id, self.tariff_system, category_callback)
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_import_products(self, interaction, category_id):
        category_name = PRODUCT_MAIN_CATEGORIES.get(category_id, "Товары")
        
        embed = discord.Embed(
            title=f"Импортные пошлины: {category_name}",
            description="Выберите товар для установки импортной пошлины:",
            color=DARK_THEME_COLOR
        )
        
        async def product_callback(interaction, product_id):
            product_name = PRODUCT_CATEGORIES.get(product_id, product_id)
            modal = ImportProductTariffModal(self.user_id, self.tariff_system, product_id, product_name)
            await interaction.response.send_modal(modal)
        
        select = ImportProductSelect(self.user_id, self.tariff_system, category_id, product_callback)
        view = View(timeout=120)
        view.add_item(select)
        
        async def back_to_categories(interaction):
            embed = discord.Embed(
                title="Импортные пошлины по товарам",
                description="Выберите категорию товаров:",
                color=DARK_THEME_COLOR
            )
            
            async def category_callback(interaction, category_id):
                await self.show_import_products(interaction, category_id)
            
            select = ImportCategorySelect(self.user_id, self.tariff_system, category_callback)
            new_view = View(timeout=120)
            new_view.add_item(select)
            
            back_button = Button(label="Назад в главное меню", style=discord.ButtonStyle.secondary)
            back_button.callback = self.back_to_main
            new_view.add_item(back_button)
            
            await interaction.response.edit_message(embed=embed, view=new_view)
        
        back_button = Button(label="Назад к категориям", style=discord.ButtonStyle.secondary)
        back_button.callback = back_to_categories
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Экспорт (по товарам)", style=discord.ButtonStyle.secondary)
    async def export_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Экспортные пошлины",
            description="Выберите категорию товаров:",
            color=DARK_THEME_COLOR
        )
        
        async def category_callback(interaction, category_id):
            await self.show_export_products(interaction, category_id)
        
        select = ExportCategorySelect(self.user_id, self.tariff_system, category_callback)
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def show_export_products(self, interaction, category_id):
        category_name = PRODUCT_MAIN_CATEGORIES.get(category_id, "Товары")
        
        embed = discord.Embed(
            title=f"Экспортные пошлины: {category_name}",
            description="Выберите товар для установки экспортной пошлины:",
            color=DARK_THEME_COLOR
        )
        
        async def product_callback(interaction, product_id):
            product_name = PRODUCT_CATEGORIES.get(product_id, product_id)
            modal = ExportProductTariffModal(self.user_id, self.tariff_system, product_id, product_name)
            await interaction.response.send_modal(modal)
        
        select = ExportProductSelect(self.user_id, self.tariff_system, category_id, product_callback)
        view = View(timeout=120)
        view.add_item(select)
        
        async def back_to_categories(interaction):
            embed = discord.Embed(
                title="Экспортные пошлины",
                description="Выберите категорию товаров:",
                color=DARK_THEME_COLOR
            )
            
            async def category_callback(interaction, category_id):
                await self.show_export_products(interaction, category_id)
            
            select = ExportCategorySelect(self.user_id, self.tariff_system, category_callback)
            new_view = View(timeout=120)
            new_view.add_item(select)
            
            back_button = Button(label="Назад в главное меню", style=discord.ButtonStyle.secondary)
            back_button.callback = self.back_to_main
            new_view.add_item(back_button)
            
            await interaction.response.edit_message(embed=embed, view=new_view)
        
        back_button = Button(label="Назад к категориям", style=discord.ButtonStyle.secondary)
        back_button.callback = back_to_categories
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Эмбарго", style=discord.ButtonStyle.secondary)
    async def embargo_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Управление эмбарго",
            description="Выберите действие:",
            color=DARK_THEME_COLOR
        )
        
        view = EmbargoManagementView(self.user_id, self.tariff_system)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Санкции", style=discord.ButtonStyle.secondary)
    async def sanctions_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Управление санкциями",
            description="Выберите действие:",
            color=DARK_THEME_COLOR
        )
        
        view = SanctionsManagementView(self.user_id, self.tariff_system)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Торговые соглашения", style=discord.ButtonStyle.secondary)
    async def trade_agreements_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Торговые соглашения",
            description="Управление зонами беспошлинной торговли:",
            color=DARK_THEME_COLOR
        )
        
        view = TradeAgreementView(self.user_id, self.tariff_system)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_main
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_main(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = self.tariff_system.get_tariff_summary_embed()
        await interaction.response.edit_message(embed=embed, view=self)


class EmbargoManagementView(View):
    """Меню управления эмбарго"""
    
    def __init__(self, user_id: int, tariff_system: TariffSystem):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.tariff_system = tariff_system
    
    @discord.ui.button(label="Установить эмбарго", style=discord.ButtonStyle.secondary)
    async def set_embargo_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Установка эмбарго",
            description="Выберите страну для установки эмбарго:",
            color=DARK_THEME_COLOR
        )
        
        select = EmbargoCountrySelect(self.user_id, self.tariff_system, "set")
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_embargo_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Снять эмбарго", style=discord.ButtonStyle.secondary)
    async def remove_embargo_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Снятие эмбарго",
            description="Выберите страну для снятия эмбарго:",
            color=DARK_THEME_COLOR
        )
        
        select = EmbargoCountrySelect(self.user_id, self.tariff_system, "remove")
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_embargo_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_embargo_menu(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Управление эмбарго",
            description="Выберите действие:",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=self)


class SanctionsManagementView(View):
    """Меню управления санкциями"""
    
    def __init__(self, user_id: int, tariff_system: TariffSystem):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.tariff_system = tariff_system
    
    @discord.ui.button(label="Установить санкции", style=discord.ButtonStyle.secondary)
    async def set_sanctions_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Установка санкций",
            description="Выберите страну для установки санкций:",
            color=DARK_THEME_COLOR
        )
        
        select = SanctionCountrySelect(self.user_id, self.tariff_system, "set")
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_sanctions_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Снять санкции", style=discord.ButtonStyle.secondary)
    async def remove_sanctions_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Снятие санкций",
            description="Выберите страну для снятия санкций:",
            color=DARK_THEME_COLOR
        )
        
        select = SanctionCountrySelect(self.user_id, self.tariff_system, "remove")
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_sanctions_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_sanctions_menu(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Управление санкциями",
            description="Выберите действие:",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=self)


class TradeAgreementView(View):
    """Меню управления торговыми соглашениями"""
    
    def __init__(self, user_id: int, tariff_system: TariffSystem):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.tariff_system = tariff_system
    
    @discord.ui.button(label="Добавить", style=discord.ButtonStyle.secondary)
    async def add_agreement_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        select = TradeAgreementSelect(self.user_id, self.tariff_system, "add")
        
        if not select.options:
            embed = discord.Embed(
                title="Нет доступных стран",
                description="Нет стран для добавления в торговые соглашения.",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        embed = discord.Embed(
            title="Добавление торгового соглашения",
            description="Выберите страну для добавления:",
            color=DARK_THEME_COLOR
        )
        
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_agreement_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="Удалить", style=discord.ButtonStyle.secondary)
    async def remove_agreement_button(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        select = TradeAgreementSelect(self.user_id, self.tariff_system, "remove")
        
        if not select.options:
            embed = discord.Embed(
                title="Нет стран для удаления",
                description="Нет стран в зоне беспошлинной торговли.",
                color=DARK_THEME_COLOR
            )
            await interaction.response.edit_message(embed=embed, view=self)
            return
        
        embed = discord.Embed(
            title="Удаление торгового соглашения",
            description="Выберите страну для удаления:",
            color=DARK_THEME_COLOR
        )
        
        view = View(timeout=120)
        view.add_item(select)
        
        back_button = Button(label="Назад", style=discord.ButtonStyle.secondary)
        back_button.callback = self.back_to_agreement_menu
        view.add_item(back_button)
        
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_to_agreement_menu(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(f"{TARIFF_EMOJIS['error']} Это не ваше меню!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="Торговые соглашения",
            description="Управление зонами беспошлинной торговли:",
            color=DARK_THEME_COLOR
        )
        
        await interaction.response.edit_message(embed=embed, view=self)


# ==================== КОМАНДА ДЛЯ ПОКАЗА МЕНЮ ====================

async def show_tariffs_menu(interaction_or_ctx, user_id: int):
    """Показать меню управления таможенными пошлинами"""
    states = load_states()
    
    state_data = None
    for data in states["players"].values():
        if data.get("assigned_to") == str(user_id):
            state_data = data
            break
    
    if not state_data:
        if hasattr(interaction_or_ctx, 'response'):
            await interaction_or_ctx.response.send_message(f"{TARIFF_EMOJIS['error']} У вас нет государства!", ephemeral=True)
        else:
            await interaction_or_ctx.send(f"{TARIFF_EMOJIS['error']} У вас нет государства!")
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
    'show_tariffs_menu',
    'TariffSystem',
    'TariffManagementView',
    'calculate_trade_with_tariffs',
    'filter_corporations_by_tariffs',
    'is_corporation_available',
    'load_tariffs',
    'save_tariffs',
    'get_country_tariffs',
    'PRODUCT_CATEGORIES',
    'TARIFF_EMOJIS'
]

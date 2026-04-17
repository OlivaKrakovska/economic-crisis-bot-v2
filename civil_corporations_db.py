# civil_corporations_db.py - ПОЛНАЯ БАЗА ДАННЫХ ГРАЖДАНСКИХ КОРПОРАЦИЙ
# Добавлены корпорации из сферы услуг, телекоммуникаций, IT, фармацевтики
# РЕАЛИСТИЧНЫЕ СТАРТОВЫЕ ПОКАЗАТЕЛИ из JSON файла

import json
from datetime import datetime
from typing import Dict, List, Optional
import random

# ==================== КЛАСС КОРПОРАЦИИ ====================

class CivilCorporation:
    """Класс, представляющий гражданскую корпорацию"""
    
    def __init__(self, corp_id, name, country, city, description, specialization, products, 
                 founded=None, website=None, service_type="manufacturing"):
        self.id = corp_id
        self.name = name
        self.country = country
        self.city = city
        self.description = description
        self.specialization = specialization
        self.products = products
        self.founded = founded
        self.website = website
        self.service_type = service_type
        # Динамические поля (будут загружаться из state)
        self.inventory = {}
        self.budget = 0
        self.popularity = 50
        self.market_share = {}
        self.employees = 0
        self.last_update = None
    
    def get_product_price(self, product_type: str) -> float:
        """Получить цену продукта"""
        if product_type in self.products:
            return self.products[product_type].get("price", 100)
        return 100
    
    def get_product_name(self, product_type: str) -> str:
        """Получить название продукта"""
        if product_type in self.products:
            return self.products[product_type].get("name", product_type)
        return product_type
    
    def get_product_description(self, product_type: str) -> str:
        """Получить описание продукта"""
        if product_type in self.products:
            return self.products[product_type].get("description", "")
        return ""
    
    def get_all_products(self):
        """Получить все продукты корпорации"""
        return list(self.products.values())
    
    def has_specialization(self, spec):
        """Проверяет, есть ли у корпорации указанная специализация"""
        return spec in self.specialization
    
    def add_to_inventory(self, product_type: str, quantity: int):
        """Добавить товар в инвентарь"""
        if product_type not in self.inventory:
            self.inventory[product_type] = 0
        self.inventory[product_type] += quantity
    
    def remove_from_inventory(self, product_type: str, quantity: int):
        """Удалить товар из инвентаря"""
        if product_type in self.inventory:
            self.inventory[product_type] -= quantity
            if self.inventory[product_type] <= 0:
                del self.inventory[product_type]
            return True
        return False
    
    @classmethod
    def from_dict(cls, corp_id: str, data: dict):
        """Создаёт объект CivilCorporation из словаря"""
        corp = cls(
            corp_id=corp_id,
            name=data.get("name", "Неизвестно"),
            country=data.get("country", "Неизвестно"),
            city=data.get("city", ""),
            description=data.get("description", ""),
            specialization=data.get("specialization", []),
            products=data.get("products", {}),
            founded=data.get("founded"),
            website=data.get("website"),
            service_type=data.get("service_type", "manufacturing")
        )
        
        # Загружаем динамические данные, если они есть
        corp.inventory = data.get("inventory", {})
        corp.budget = data.get("budget", 0)
        corp.popularity = data.get("popularity", 50)
        corp.market_share = data.get("market_share", {})
        corp.employees = data.get("employees", 0)
        corp.last_update = data.get("last_update")
        
        return corp
    
    def to_dict(self):
        """Преобразует объект в словарь для сохранения"""
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "city": self.city,
            "description": self.description,
            "specialization": self.specialization,
            "products": self.products,
            "founded": self.founded,
            "website": self.website,
            "service_type": self.service_type,
            "inventory": self.inventory,
            "budget": self.budget,
            "popularity": self.popularity,
            "market_share": self.market_share,
            "employees": self.employees,
            "last_update": self.last_update
        }

# ==================== ФАЙЛ ДЛЯ СОХРАНЕНИЯ СОСТОЯНИЯ ====================

CORPORATIONS_STATE_FILE = 'corporations_state.json'
STARTING_DATA_FILE = 'corporations_starting_data.json'

def load_corporations_state():
    """Загрузить состояние корпораций (динамические данные)"""
    try:
        with open(CORPORATIONS_STATE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {"corporations": {}}
            data = json.loads(content)
            # Конвертируем словари обратно в объекты
            corporations = {}
            for corp_id, corp_data in data["corporations"].items():
                corporations[corp_id] = CivilCorporation.from_dict(corp_id, corp_data)
            return {"corporations": corporations}
    except FileNotFoundError:
        return {"corporations": {}}
    except json.JSONDecodeError:
        return {"corporations": {}}

def save_corporations_state(state):
    """Сохранить состояние корпораций"""
    # Конвертируем объекты в словари
    data = {"corporations": {}}
    for corp_id, corp in state["corporations"].items():
        data["corporations"][corp_id] = corp.to_dict()
    
    with open(CORPORATIONS_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def initialize_corporation_state(corp):
    """Инициализировать состояние для корпорации"""
    state = load_corporations_state()
    if corp.id not in state["corporations"]:
        # Создаем копию с начальными значениями
        new_corp = CivilCorporation(
            corp.id, corp.name, corp.country, corp.city, corp.description,
            corp.specialization, corp.products, corp.founded, corp.website
        )
        # Начальный бюджет
        new_corp.budget = 10000000  # 10 млн $ начального капитала
        # Начальная популярность
        new_corp.popularity = 60
        state["corporations"][corp.id] = new_corp
        save_corporations_state(state)
    return state["corporations"][corp.id]


# ==================== ЗАГРУЗКА СТАРТОВЫХ ДАННЫХ ====================

def load_starting_corporation_data():
    """Загружает стартовые данные для корпораций из JSON файла"""
    try:
        with open(STARTING_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("corporations", {})
    except FileNotFoundError:
        print(f"⚠️ Файл {STARTING_DATA_FILE} не найден, используются стандартные значения")
        return {}
    except json.JSONDecodeError:
        print(f"❌ Ошибка в формате JSON файла {STARTING_DATA_FILE}")
        return {}


def initialize_all_corporations(force=False):
    """Инициализировать все корпорации с реалистичными стартовыми показателями"""
    state = load_corporations_state()
    starting_data = load_starting_corporation_data()
    initialized = 0
    updated = 0
    
    all_corps = get_all_civil_corporations()
    print(f"🏭 Найдено корпораций в базе: {len(all_corps)}")
    
    for corp in all_corps:
        # Проверяем, нужно ли создавать новую или обновить существующую
        if corp.id not in state["corporations"]:
            # Создаём новую корпорацию
            new_corp = CivilCorporation(
                corp.id, corp.name, corp.country, corp.city, corp.description,
                corp.specialization, corp.products, corp.founded, corp.website
            )
            
            # Загружаем стартовые данные, если есть
            if corp.id in starting_data:
                data = starting_data[corp.id]
                new_corp.budget = data.get("budget", 10000000)
                new_corp.popularity = data.get("popularity", 60)
                new_corp.inventory = data.get("inventory", {})
                new_corp.employees = data.get("employees", 0)
                new_corp.market_share = data.get("market_share", {})
                print(f"  ✅ {corp.name}: создана с реальными данными")
            else:
                # Fallback на старые значения
                new_corp.budget = 10000000
                new_corp.popularity = 60
                for product_type in corp.products.keys():
                    new_corp.inventory[product_type] = 100
                print(f"  ⚠️ {corp.name}: нет данных, использованы стандартные")
            
            state["corporations"][corp.id] = new_corp
            initialized += 1
            
        elif force:
            # Обновляем существующую корпорацию (при force=True)
            if corp.id in starting_data:
                data = starting_data[corp.id]
                state["corporations"][corp.id].budget = data.get("budget", state["corporations"][corp.id].budget)
                state["corporations"][corp.id].popularity = data.get("popularity", state["corporations"][corp.id].popularity)
                
                # Обновляем инвентарь (добавляем, а не заменяем)
                for product, amount in data.get("inventory", {}).items():
                    state["corporations"][corp.id].inventory[product] = amount
                
                state["corporations"][corp.id].employees = data.get("employees", state["corporations"][corp.id].employees)
                updated += 1
                print(f"  🔄 {corp.name}: обновлена")
    
    if initialized > 0 or updated > 0:
        save_corporations_state(state)
        print(f"✅ Инициализировано {initialized} новых корпораций, обновлено {updated}")
    else:
        print(f"ℹ️ Корпорации уже инициализированы ({len(state['corporations'])} шт.)")
    
    return state


# ==================== ТИПЫ ПРОДУКЦИИ И УСЛУГ ====================

CIVIL_PRODUCT_TYPES = {
    # Автомобили и транспорт
    "cars": "Автомобили легковые",
    "trucks": "Грузовые автомобили",
    "buses": "Автобусы",
    "auto_parts": "Автозапчасти",
    
    # Техника и оборудование
    "agricultural_machinery": "Сельскохозяйственная техника",
    "construction_machinery": "Строительная техника",
    "industrial_equipment": "Промышленное оборудование",
    "machine_tools": "Станки",
    "industrial_robots": "Промышленные роботы",
    "energy_equipment": "Энергетическое оборудование",
    "electrical_equipment": "Электротехника",
    
    # Телекоммуникации и IT
    "telecom_equipment": "Телекоммуникационное оборудование",
    "telecom_services": "Услуги связи",
    "internet_services": "Интернет-услуги",
    "mobile_services": "Мобильная связь",
    "data_centers": "Центры обработки данных",
    "cloud_services": "Облачные услуги",
    "software": "Программное обеспечение",
    "it_services": "IT-услуги",
    "cybersecurity": "Кибербезопасность",
    
    # Электроника
    "consumer_electronics": "Бытовая электроника",
    "tech_equipment": "Технологическое оборудование",
    "computers": "Компьютеры и ноутбуки",
    "smartphones": "Смартфоны",
    "tablets": "Планшеты",
    
    # Авиация и космос
    "aerospace_equipment": "Авиакосмическое оборудование",
    "drones": "Беспилотники",
    "fpv_drones": "FPV-дроны",
    "satellite_services": "Спутниковые услуги",
    
    # Медицина и фармацевтика
    "pharmaceuticals": "Лекарственные препараты",
    "medical_equipment": "Медицинское оборудование",
    "medical_supplies": "Медицинские изделия",
    "sanitary_products": "Санитарно-гигиенические средства",
    "healthcare_services": "Медицинские услуги",
    "hospital_services": "Больничные услуги",
    "dentistry": "Стоматологические услуги",
    
    # Продукты питания и напитки
    "food_products": "Пищевые продукты",
    "beverages": "Напитки",
    "restaurants": "Рестораны и общепит",
    "fast_food": "Фаст-фуд",
    "catering": "Кейтеринг",
    
    # Товары повседневного спроса
    "clothing": "Одежда и текстиль",
    "footwear": "Обувь",
    "furniture": "Мебель",
    "household_goods": "Товары для дома",
    "cosmetics": "Косметика",
    "perfumes": "Парфюмерия",
    
    # Химическая промышленность
    "chemicals": "Химическая продукция",
    "fertilizers": "Удобрения",
    "paints": "Краски и покрытия",
    
    # Финансовые услуги
    "banking": "Банковские услуги",
    "insurance": "Страхование",
    "investments": "Инвестиционные услуги",
    "fintech": "Финансовые технологии",
    
    # Розничная торговля
    "retail": "Розничная торговля",
    "supermarkets": "Супермаркеты",
    "ecommerce": "Электронная коммерция",
    
    # Образование
    "education": "Образовательные услуги",
    "online_courses": "Онлайн-обучение",
    "vocational_training": "Профессиональное обучение",
    
    # Развлечения и медиа
    "entertainment": "Развлечения",
    "media": "Медиа-услуги",
    "streaming": "Стриминговые сервисы",
    "gaming": "Видеоигры",
    
    # Транспорт и логистика
    "logistics": "Логистические услуги",
    "freight": "Грузоперевозки",
    "passenger_transport": "Пассажирские перевозки",
    "airlines": "Авиаперевозки",
    
    # Энергетика и коммунальные услуги
    "electricity": "Электроснабжение",
    "gas_supply": "Газоснабжение",
    "water_supply": "Водоснабжение",
    "waste_management": "Управление отходами",
    
    # Строительство и недвижимость
    "construction": "Строительные услуги",
    "real_estate": "Операции с недвижимостью",
    "property_management": "Управление недвижимостью",
    
    # Профессиональные услуги
    "consulting": "Консалтинговые услуги",
    "legal": "Юридические услуги",
    "accounting": "Бухгалтерские услуги",
    "marketing": "Маркетинговые услуги",
    "hr_services": "Кадровые услуги"
}

# Словарь для перевода на русский
CIVIL_PRODUCT_NAMES = CIVIL_PRODUCT_TYPES.copy()


# ==================== НОВЫЕ КОРПОРАЦИИ США ====================

# Автомобилестроение
GENERAL_MOTORS = CivilCorporation(
    corp_id="civ_us_001",
    name="General Motors",
    country="США",
    city="Детройт, Мичиган",
    description="Один из крупнейших автопроизводителей в мире. Выпускает автомобили под брендами Chevrolet, GMC, Cadillac.",
    specialization=["cars", "trucks", "auto_parts"],
    founded=1908,
    website="www.gm.com",
    products={
        "cars": {"name": "Chevrolet, Cadillac", "type": "cars", "price": 30000, "description": "Легковые автомобили"},
        "trucks": {"name": "Chevrolet Silverado, GMC Sierra", "type": "trucks", "price": 45000, "description": "Пикапы и грузовики"},
        "auto_parts": {"name": "Оригинальные запчасти GM", "type": "auto_parts", "price": 5000, "description": "Автозапчасти"}
    }
)

FORD = CivilCorporation(
    corp_id="civ_us_001b",
    name="Ford Motor Company",
    country="США",
    city="Дирборн, Мичиган",
    description="Легендарный американский автопроизводитель, создатель конвейерного производства.",
    specialization=["cars", "trucks", "auto_parts"],
    founded=1903,
    website="www.ford.com",
    products={
        "cars": {"name": "Ford Mustang, Focus", "type": "cars", "price": 28000, "description": "Легковые автомобили"},
        "trucks": {"name": "Ford F-150", "type": "trucks", "price": 40000, "description": "Самый продаваемый пикап в США"},
        "auto_parts": {"name": "Оригинальные запчасти Ford", "type": "auto_parts", "price": 4500, "description": "Автозапчасти"}
    }
)

TESLA = CivilCorporation(
    corp_id="civ_us_001c",
    name="Tesla, Inc.",
    country="США",
    city="Остин, Техас",
    description="Производитель электромобилей и чистых энергетических решений.",
    specialization=["cars", "energy_equipment"],
    founded=2003,
    website="www.tesla.com",
    products={
        "cars": {"name": "Tesla Model S, 3, X, Y", "type": "cars", "price": 50000, "description": "Электромобили"},
        "energy_equipment": {"name": "Powerwall, Solar Roof", "type": "energy_equipment", "price": 10000, "description": "Домашние батареи и солнечные панели"}
    }
)

# Промышленное оборудование
CATERPILLAR = CivilCorporation(
    corp_id="civ_us_002",
    name="Caterpillar Inc.",
    country="США",
    city="Ирвинг, Техас",
    description="Мировой лидер в производстве строительной и горнодобывающей техники, дизельных двигателей.",
    specialization=["construction_machinery", "industrial_equipment", "energy_equipment"],
    founded=1925,
    website="www.caterpillar.com",
    products={
        "construction_machinery": {"name": "Строительная техника", "type": "construction_machinery", "price": 500000, "description": "Бульдозеры, экскаваторы"},
        "industrial_equipment": {"name": "Промышленные двигатели", "type": "industrial_equipment", "price": 100000, "description": "Дизельные двигатели"},
        "energy_equipment": {"name": "Генераторы", "type": "energy_equipment", "price": 150000, "description": "Дизель-генераторы"}
    }
)

# Авиакосмическая промышленность
BOEING = CivilCorporation(
    corp_id="civ_us_003",
    name="Boeing",
    country="США",
    city="Чикаго, Иллинойс",
    description="Крупнейший в мире производитель авиационной, космической и военной техники.",
    specialization=["aerospace_equipment", "drones"],
    founded=1916,
    website="www.boeing.com",
    products={
        "aerospace_equipment": {"name": "Гражданские самолеты", "type": "aerospace_equipment", "price": 100000000, "description": "Boeing 737, 747, 777, 787"},
        "drones": {"name": "Беспилотные системы", "type": "drones", "price": 10000000, "description": "Беспилотники военного назначения"}
    }
)

# Технологическое оборудование и IT
IBM = CivilCorporation(
    corp_id="civ_us_004",
    name="IBM",
    country="США",
    city="Армонк, Нью-Йорк",
    description="Глобальная технологическая корпорация, производитель оборудования и программного обеспечения.",
    specialization=["tech_equipment", "it_services", "software", "cloud_services"],
    founded=1911,
    website="www.ibm.com",
    products={
        "tech_equipment": {"name": "Серверы и мейнфреймы", "type": "tech_equipment", "price": 50000, "description": "Корпоративные серверы"},
        "it_services": {"name": "IT-консалтинг", "type": "it_services", "price": 200, "description": "Услуги в час"},
        "software": {"name": "Корпоративное ПО", "type": "software", "price": 10000, "description": "Лицензии на ПО"},
        "cloud_services": {"name": "Облачные услуги", "type": "cloud_services", "price": 500, "description": "Облачные вычисления"}
    }
)

MICROSOFT = CivilCorporation(
    corp_id="civ_us_004b",
    name="Microsoft Corporation",
    country="США",
    city="Редмонд, Вашингтон",
    description="Мировой лидер в производстве программного обеспечения, облачных услуг и устройств.",
    specialization=["software", "cloud_services", "computers", "gaming"],
    founded=1975,
    website="www.microsoft.com",
    products={
        "software": {"name": "Windows, Office", "type": "software", "price": 200, "description": "Операционные системы и офисное ПО"},
        "cloud_services": {"name": "Microsoft Azure", "type": "cloud_services", "price": 300, "description": "Облачные услуги"},
        "computers": {"name": "Surface", "type": "computers", "price": 1500, "description": "Ноутбуки и планшеты"},
        "gaming": {"name": "Xbox", "type": "gaming", "price": 500, "description": "Игровые консоли"}
    }
)

APPLE = CivilCorporation(
    corp_id="civ_us_004c",
    name="Apple Inc.",
    country="США",
    city="Купертино, Калифорния",
    description="Технологический гигант, производитель iPhone, Mac, iPad и других устройств.",
    specialization=["smartphones", "computers", "tablets", "software", "streaming"],
    founded=1976,
    website="www.apple.com",
    products={
        "smartphones": {"name": "iPhone", "type": "smartphones", "price": 1000, "description": "Смартфоны"},
        "computers": {"name": "Mac", "type": "computers", "price": 2000, "description": "Ноутбуки и компьютеры"},
        "tablets": {"name": "iPad", "type": "tablets", "price": 500, "description": "Планшеты"},
        "software": {"name": "macOS, iOS", "type": "software", "price": 0, "description": "Операционные системы"},
        "streaming": {"name": "Apple TV+", "type": "streaming", "price": 10, "description": "Стриминговый сервис"}
    }
)

GOOGLE = CivilCorporation(
    corp_id="civ_us_004d",
    name="Google LLC",
    country="США",
    city="Маунтин-Вью, Калифорния",
    description="Технологическая корпорация, специализирующаяся на интернет-услугах и рекламе.",
    specialization=["internet_services", "software", "cloud_services", "smartphones"],
    founded=1998,
    website="www.google.com",
    products={
        "internet_services": {"name": "Поиск, YouTube", "type": "internet_services", "price": 0, "description": "Бесплатные сервисы с рекламой"},
        "software": {"name": "Android, Chrome", "type": "software", "price": 0, "description": "Мобильная ОС и браузер"},
        "cloud_services": {"name": "Google Cloud", "type": "cloud_services", "price": 200, "description": "Облачные услуги"},
        "smartphones": {"name": "Pixel", "type": "smartphones", "price": 800, "description": "Смартфоны"}
    }
)

AMAZON = CivilCorporation(
    corp_id="civ_us_004e",
    name="Amazon.com, Inc.",
    country="США",
    city="Сиэтл, Вашингтон",
    description="Крупнейшая в мире платформа электронной коммерции и облачных вычислений.",
    specialization=["ecommerce", "cloud_services", "streaming", "logistics"],
    founded=1994,
    website="www.amazon.com",
    products={
        "ecommerce": {"name": "Amazon.com", "type": "ecommerce", "price": 0, "description": "Торговая платформа"},
        "cloud_services": {"name": "AWS", "type": "cloud_services", "price": 300, "description": "Облачные услуги"},
        "streaming": {"name": "Prime Video", "type": "streaming", "price": 15, "description": "Видео-стриминг"},
        "logistics": {"name": "Amazon Logistics", "type": "logistics", "price": 10, "description": "Доставка"}
    }
)

# Медицинское оборудование и фармацевтика
JOHNSON_JOHNSON = CivilCorporation(
    corp_id="civ_us_005",
    name="Johnson & Johnson",
    country="США",
    city="Нью-Брансуик, Нью-Джерси",
    description="Крупнейший производитель медицинского оборудования, фармацевтики и товаров для здоровья.",
    specialization=["medical_equipment", "medical_supplies", "pharmaceuticals", "sanitary_products", "cosmetics"],
    founded=1886,
    website="www.jnj.com",
    products={
        "medical_equipment": {"name": "Хирургическое оборудование", "type": "medical_equipment", "price": 50000, "description": "Медицинская техника"},
        "medical_supplies": {"name": "Расходные материалы", "type": "medical_supplies", "price": 5000, "description": "Бинты, шприцы"},
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 1000, "description": "Рецептурные препараты"},
        "sanitary_products": {"name": "Средства гигиены", "type": "sanitary_products", "price": 500, "description": "Шампуни, мыло"},
        "cosmetics": {"name": "Косметика", "type": "cosmetics", "price": 300, "description": "Средства по уходу"}
    }
)

PFIZER = CivilCorporation(
    corp_id="civ_us_005b",
    name="Pfizer Inc.",
    country="США",
    city="Нью-Йорк, Нью-Йорк",
    description="Одна из крупнейших фармацевтических компаний мира, разработчик вакцин и лекарств.",
    specialization=["pharmaceuticals"],
    founded=1849,
    website="www.pfizer.com",
    products={
        "pharmaceuticals": {"name": "Лекарства и вакцины", "type": "pharmaceuticals", "price": 1500, "description": "Рецептурные препараты"}
    }
)

MERCK = CivilCorporation(
    corp_id="civ_us_005c",
    name="Merck & Co.",
    country="США",
    city="Кенилуэрт, Нью-Джерси",
    description="Глобальная фармацевтическая компания, известная своими инновационными лекарствами.",
    specialization=["pharmaceuticals"],
    founded=1891,
    website="www.merck.com",
    products={
        "pharmaceuticals": {"name": "Лекарственные препараты", "type": "pharmaceuticals", "price": 1200, "description": "Рецептурные лекарства"}
    }
)

# Телекоммуникации
AT_T = CivilCorporation(
    corp_id="civ_us_006",
    name="AT&T Inc.",
    country="США",
    city="Даллас, Техас",
    description="Крупнейшая телекоммуникационная компания США, предоставляет услуги связи и медиа.",
    specialization=["telecom_services", "mobile_services", "internet_services", "media"],
    founded=1983,
    website="www.att.com",
    products={
        "telecom_services": {"name": "Телефонная связь", "type": "telecom_services", "price": 50, "description": "Домашний телефон"},
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 80, "description": "Сотовые тарифы"},
        "internet_services": {"name": "Домашний интернет", "type": "internet_services", "price": 60, "description": "Широкополосный интернет"},
        "media": {"name": "DIRECTV", "type": "media", "price": 100, "description": "Спутниковое ТВ"}
    }
)

VERIZON = CivilCorporation(
    corp_id="civ_us_006b",
    name="Verizon Communications",
    country="США",
    city="Нью-Йорк, Нью-Йорк",
    description="Ведущий телекоммуникационный оператор, специализируется на беспроводной связи.",
    specialization=["mobile_services", "internet_services", "telecom_services"],
    founded=2000,
    website="www.verizon.com",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 85, "description": "Сотовые тарифы"},
        "internet_services": {"name": "Fios интернет", "type": "internet_services", "price": 70, "description": "Оптоволоконный интернет"},
        "telecom_services": {"name": "Бизнес-связь", "type": "telecom_services", "price": 200, "description": "Корпоративные решения"}
    }
)

COMCAST = CivilCorporation(
    corp_id="civ_us_006c",
    name="Comcast Corporation",
    country="США",
    city="Филадельфия, Пенсильвания",
    description="Крупнейший оператор кабельного телевидения и интернета в США.",
    specialization=["internet_services", "media", "telecom_services"],
    founded=1963,
    website="www.comcast.com",
    products={
        "internet_services": {"name": "Xfinity Internet", "type": "internet_services", "price": 65, "description": "Кабельный интернет"},
        "media": {"name": "Кабельное ТВ", "type": "media", "price": 90, "description": "Телевидение"},
        "telecom_services": {"name": "Xfinity Voice", "type": "telecom_services", "price": 40, "description": "Домашний телефон"}
    }
)

# Финансовые услуги
JPMORGAN = CivilCorporation(
    corp_id="civ_us_007",
    name="JPMorgan Chase & Co.",
    country="США",
    city="Нью-Йорк, Нью-Йорк",
    description="Крупнейший банк США, предоставляющий полный спектр финансовых услуг.",
    specialization=["banking", "investments", "fintech"],
    founded=2000,
    website="www.jpmorganchase.com",
    products={
        "banking": {"name": "Розничные банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиционный банкинг", "type": "investments", "price": 1000, "description": "Управление капиталом"},
        "fintech": {"name": "Цифровые платежи", "type": "fintech", "price": 0, "description": "Мобильный банкинг"}
    }
)

GOLDMAN_SACHS = CivilCorporation(
    corp_id="civ_us_007b",
    name="Goldman Sachs",
    country="США",
    city="Нью-Йорк, Нью-Йорк",
    description="Ведущий глобальный инвестиционный банк и компания по управлению ценными бумагами.",
    specialization=["investments", "banking"],
    founded=1869,
    website="www.goldmansachs.com",
    products={
        "investments": {"name": "Инвестиционные услуги", "type": "investments", "price": 2000, "description": "Управление активами"},
        "banking": {"name": "Private banking", "type": "banking", "price": 500, "description": "Обслуживание состоятельных клиентов"}
    }
)

VISA = CivilCorporation(
    corp_id="civ_us_007c",
    name="Visa Inc.",
    country="США",
    city="Сан-Франциско, Калифорния",
    description="Мировой лидер в области цифровых платежей и платежных технологий.",
    specialization=["fintech", "banking"],
    founded=1958,
    website="www.visa.com",
    products={
        "fintech": {"name": "Платежные системы", "type": "fintech", "price": 0, "description": "Обработка транзакций"},
        "banking": {"name": "Кредитные карты", "type": "banking", "price": 0, "description": "Платежные карты"}
    }
)

MASTERCARD = CivilCorporation(
    corp_id="civ_us_007d",
    name="Mastercard Inc.",
    country="США",
    city="Пёрчейз, Нью-Йорк",
    description="Глобальная платежная технологическая компания, вторая по величине в мире.",
    specialization=["fintech", "banking"],
    founded=1966,
    website="www.mastercard.com",
    products={
        "fintech": {"name": "Платежные решения", "type": "fintech", "price": 0, "description": "Обработка платежей"},
        "banking": {"name": "Платежные карты", "type": "banking", "price": 0, "description": "Кредитные и дебетовые карты"}
    }
)

# Розничная торговля
WALMART = CivilCorporation(
    corp_id="civ_us_008",
    name="Walmart Inc.",
    country="США",
    city="Бентонвилл, Арканзас",
    description="Крупнейшая в мире сеть розничной торговли, управляет гипермаркетами и суперцентрами.",
    specialization=["retail", "supermarkets", "ecommerce"],
    founded=1962,
    website="www.walmart.com",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Широкий ассортимент товаров"},
        "supermarkets": {"name": "Walmart Supercenter", "type": "supermarkets", "price": 0, "description": "Продукты и товары"},
        "ecommerce": {"name": "Walmart.com", "type": "ecommerce", "price": 0, "description": "Интернет-магазин"}
    }
)

COSTCO = CivilCorporation(
    corp_id="civ_us_008b",
    name="Costco Wholesale",
    country="США",
    city="Иссакуа, Вашингтон",
    description="Сеть складов-клубов, предлагающая товары оптом по низким ценам.",
    specialization=["retail", "supermarkets"],
    founded=1983,
    website="www.costco.com",
    products={
        "retail": {"name": "Оптово-розничная торговля", "type": "retail", "price": 60, "description": "Членский клуб"},
        "supermarkets": {"name": "Продуктовые склады", "type": "supermarkets", "price": 0, "description": "Продукты питания"}
    }
)

TARGET = CivilCorporation(
    corp_id="civ_us_008c",
    name="Target Corporation",
    country="США",
    city="Миннеаполис, Миннесота",
    description="Сеть универмагов, предлагающая товары для дома, одежду и продукты.",
    specialization=["retail", "clothing", "household_goods"],
    founded=1902,
    website="www.target.com",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Товары повседневного спроса"},
        "clothing": {"name": "Одежда", "type": "clothing", "price": 50, "description": "Модная одежда"},
        "household_goods": {"name": "Товары для дома", "type": "household_goods", "price": 100, "description": "Домашний декор"}
    }
)

# Рестораны и фаст-фуд
MCDONALDS = CivilCorporation(
    corp_id="civ_us_009",
    name="McDonald's Corporation",
    country="США",
    city="Чикаго, Иллинойс",
    description="Крупнейшая в мире сеть ресторанов быстрого питания.",
    specialization=["fast_food", "restaurants"],
    founded=1955,
    website="www.mcdonalds.com",
    products={
        "fast_food": {"name": "Фаст-фуд", "type": "fast_food", "price": 10, "description": "Бургеры, картошка фри"},
        "restaurants": {"name": "Рестораны", "type": "restaurants", "price": 15, "description": "Обслуживание в зале"}
    }
)

STARBUCKS = CivilCorporation(
    corp_id="civ_us_009b",
    name="Starbucks Corporation",
    country="США",
    city="Сиэтл, Вашингтон",
    description="Крупнейшая в мире сеть кофеен.",
    specialization=["restaurants", "food_products"],
    founded=1971,
    website="www.starbucks.com",
    products={
        "restaurants": {"name": "Кофейни", "type": "restaurants", "price": 5, "description": "Кофе и напитки"},
        "food_products": {"name": "Кофе в зернах", "type": "food_products", "price": 15, "description": "Упакованный кофе"}
    }
)

YUM_BRANDS = CivilCorporation(
    corp_id="civ_us_009c",
    name="Yum! Brands",
    country="США",
    city="Луисвилл, Кентукки",
    description="Владелец сетей KFC, Pizza Hut и Taco Bell.",
    specialization=["fast_food", "restaurants"],
    founded=1997,
    website="www.yum.com",
    products={
        "fast_food": {"name": "KFC", "type": "fast_food", "price": 12, "description": "Жареная курица"},
        "restaurants": {"name": "Pizza Hut", "type": "restaurants", "price": 15, "description": "Пиццерия"},
        "fast_food": {"name": "Taco Bell", "type": "fast_food", "price": 8, "description": "Мексиканский фаст-фуд"}
    }
)

# Сельскохозяйственная техника
JOHN_DEERE = CivilCorporation(
    corp_id="civ_us_010",
    name="John Deere",
    country="США",
    city="Молин, Иллинойс",
    description="Мировой лидер в производстве сельскохозяйственной техники.",
    specialization=["agricultural_machinery", "construction_machinery"],
    founded=1837,
    website="www.deere.com",
    products={
        "agricultural_machinery": {"name": "Сельхозтехника", "type": "agricultural_machinery", "price": 300000, "description": "Тракторы, комбайны"},
        "construction_machinery": {"name": "Строительная техника", "type": "construction_machinery", "price": 250000, "description": "Экскаваторы, погрузчики"}
    }
)

# Продукты питания и напитки
PEPSICO = CivilCorporation(
    corp_id="civ_us_011",
    name="PepsiCo",
    country="США",
    city="Перчейз, Нью-Йорк",
    description="Мировой лидер в производстве продуктов питания и напитков.",
    specialization=["food_products", "beverages"],
    founded=1965,
    website="www.pepsico.com",
    products={
        "food_products": {"name": "Снеки", "type": "food_products", "price": 100, "description": "Чипсы Lay's, Doritos"},
        "beverages": {"name": "Напитки", "type": "beverages", "price": 50, "description": "Pepsi, 7Up, Gatorade"}
    }
)

COCA_COLA = CivilCorporation(
    corp_id="civ_us_011b",
    name="The Coca-Cola Company",
    country="США",
    city="Атланта, Джорджия",
    description="Крупнейший в мире производитель безалкогольных напитков.",
    specialization=["beverages"],
    founded=1892,
    website="www.coca-cola.com",
    products={
        "beverages": {"name": "Напитки", "type": "beverages", "price": 45, "description": "Coca-Cola, Sprite, Fanta"}
    }
)

# Электротехника
GE = CivilCorporation(
    corp_id="civ_us_012",
    name="General Electric",
    country="США",
    city="Бостон, Массачусетс",
    description="Многоотраслевая корпорация, производитель электротехники, энергетического оборудования.",
    specialization=["electrical_equipment", "energy_equipment", "aerospace_equipment"],
    founded=1892,
    website="www.ge.com",
    products={
        "electrical_equipment": {"name": "Электротехника", "type": "electrical_equipment", "price": 20000, "description": "Трансформаторы, двигатели"},
        "energy_equipment": {"name": "Энергооборудование", "type": "energy_equipment", "price": 500000, "description": "Газовые турбины"},
        "aerospace_equipment": {"name": "Авиадвигатели", "type": "aerospace_equipment", "price": 15000000, "description": "Реактивные двигатели"}
    }
)

# Авиаперевозки
DELTA_AIR = CivilCorporation(
    corp_id="civ_us_013",
    name="Delta Air Lines",
    country="США",
    city="Атланта, Джорджия",
    description="Крупнейшая авиакомпания США, выполняет внутренние и международные рейсы.",
    specialization=["airlines", "passenger_transport", "logistics"],
    founded=1925,
    website="www.delta.com",
    products={
        "airlines": {"name": "Авиабилеты", "type": "airlines", "price": 300, "description": "Пассажирские перевозки"},
        "passenger_transport": {"name": "Чартерные рейсы", "type": "passenger_transport", "price": 5000, "description": "Частные рейсы"},
        "logistics": {"name": "Грузовые перевозки", "type": "logistics", "price": 1000, "description": "Авиагрузы"}
    }
)

AMERICAN_AIR = CivilCorporation(
    corp_id="civ_us_013b",
    name="American Airlines",
    country="США",
    city="Форт-Уэрт, Техас",
    description="Одна из крупнейших авиакомпаний мира, выполняет рейсы по всему миру.",
    specialization=["airlines", "passenger_transport"],
    founded=1930,
    website="www.aa.com",
    products={
        "airlines": {"name": "Авиабилеты", "type": "airlines", "price": 280, "description": "Пассажирские перевозки"},
        "passenger_transport": {"name": "Бизнес-класс", "type": "passenger_transport", "price": 2000, "description": "Премиальные перелеты"}
    }
)

UNITED_AIR = CivilCorporation(
    corp_id="civ_us_013c",
    name="United Airlines",
    country="США",
    city="Чикаго, Иллинойс",
    description="Глобальная авиакомпания с широкой сетью маршрутов.",
    specialization=["airlines", "passenger_transport"],
    founded=1926,
    website="www.united.com",
    products={
        "airlines": {"name": "Авиабилеты", "type": "airlines", "price": 290, "description": "Пассажирские перевозки"},
        "passenger_transport": {"name": "Премиум-класс", "type": "passenger_transport", "price": 1800, "description": "Улучшенный сервис"}
    }
)

# Логистика
UPS = CivilCorporation(
    corp_id="civ_us_014",
    name="United Parcel Service (UPS)",
    country="США",
    city="Сэнди-Спрингс, Джорджия",
    description="Крупнейшая в мире компания экспресс-доставки и логистики.",
    specialization=["logistics", "freight"],
    founded=1907,
    website="www.ups.com",
    products={
        "logistics": {"name": "Экспресс-доставка", "type": "logistics", "price": 20, "description": "Доставка посылок"},
        "freight": {"name": "Грузоперевозки", "type": "freight", "price": 500, "description": "Перевозка крупных грузов"}
    }
)

FEDEX = CivilCorporation(
    corp_id="civ_us_014b",
    name="FedEx Corporation",
    country="США",
    city="Мемфис, Теннесси",
    description="Глобальная компания курьерской доставки и логистики.",
    specialization=["logistics", "freight"],
    founded=1971,
    website="www.fedex.com",
    products={
        "logistics": {"name": "Курьерская доставка", "type": "logistics", "price": 18, "description": "Доставка документов и посылок"},
        "freight": {"name": "Грузоперевозки", "type": "freight", "price": 450, "description": "Перевозка грузов"}
    }
)

# Медиа и развлечения
WALT_DISNEY = CivilCorporation(
    corp_id="civ_us_015",
    name="The Walt Disney Company",
    country="США",
    city="Бербанк, Калифорния",
    description="Медиа-конгломерат, владелец киностудий, телеканалов и парков развлечений.",
    specialization=["entertainment", "media", "streaming"],
    founded=1923,
    website="www.disney.com",
    products={
        "entertainment": {"name": "Парки развлечений", "type": "entertainment", "price": 150, "description": "Disneyland, Disney World"},
        "media": {"name": "Телеканалы", "type": "media", "price": 50, "description": "Кабельное ТВ"},
        "streaming": {"name": "Disney+", "type": "streaming", "price": 8, "description": "Стриминговый сервис"}
    }
)

NETFLIX = CivilCorporation(
    corp_id="civ_us_015b",
    name="Netflix, Inc.",
    country="США",
    city="Лос-Гатос, Калифорния",
    description="Мировой лидер в области стриминговых сервисов и производства контента.",
    specialization=["streaming", "entertainment"],
    founded=1997,
    website="www.netflix.com",
    products={
        "streaming": {"name": "Netflix", "type": "streaming", "price": 15, "description": "Видео-стриминг"},
        "entertainment": {"name": "Продакшн контента", "type": "entertainment", "price": 0, "description": "Создание фильмов и сериалов"}
    }
)

WARNER_BROS = CivilCorporation(
    corp_id="civ_us_015c",
    name="Warner Bros. Discovery",
    country="США",
    city="Нью-Йорк, Нью-Йорк",
    description="Глобальный медиа-конгломерат, производитель фильмов и телепрограмм.",
    specialization=["media", "entertainment", "streaming"],
    founded=2022,
    website="www.wbd.com",
    products={
        "media": {"name": "Телеканалы", "type": "media", "price": 45, "description": "CNN, HBO, Discovery"},
        "entertainment": {"name": "Киностудия", "type": "entertainment", "price": 0, "description": "Производство фильмов"},
        "streaming": {"name": "HBO Max", "type": "streaming", "price": 15, "description": "Стриминговый сервис"}
    }
)

# Образование
CHEGG = CivilCorporation(
    corp_id="civ_us_016",
    name="Chegg, Inc.",
    country="США",
    city="Санта-Клара, Калифорния",
    description="Образовательная технологическая компания, предоставляет услуги онлайн-обучения.",
    specialization=["education", "online_courses"],
    founded=2005,
    website="www.chegg.com",
    products={
        "education": {"name": "Учебные материалы", "type": "education", "price": 15, "description": "Учебники и решения"},
        "online_courses": {"name": "Онлайн-репетиторство", "type": "online_courses", "price": 30, "description": "Индивидуальные занятия"}
    }
)

COURSERA = CivilCorporation(
    corp_id="civ_us_016b",
    name="Coursera, Inc.",
    country="США",
    city="Маунтин-Вью, Калифорния",
    description="Платформа онлайн-обучения с курсами от ведущих университетов.",
    specialization=["online_courses", "education"],
    founded=2012,
    website="www.coursera.org",
    products={
        "online_courses": {"name": "Онлайн-курсы", "type": "online_courses", "price": 50, "description": "Курсы от университетов"},
        "education": {"name": "Профессиональные сертификаты", "type": "education", "price": 200, "description": "Сертификация"}
    }
)


# ==================== КОРПОРАЦИИ РОССИИ (расширенные) ====================

# Автомобилестроение
AVTOVAZ = CivilCorporation(
    corp_id="civ_ru_001",
    name="АвтоВАЗ",
    country="Россия",
    city="Тольятти, Самарская область",
    description="Крупнейший производитель легковых автомобилей в России, выпускает автомобили LADA.",
    specialization=["cars", "auto_parts"],
    founded=1966,
    website="www.lada.ru",
    products={
        "cars": {"name": "LADA", "type": "cars", "price": 15000, "description": "Легковые автомобили эконом-класса"},
        "auto_parts": {"name": "Запчасти LADA", "type": "auto_parts", "price": 2000, "description": "Оригинальные запчасти"}
    }
)

GAZ = CivilCorporation(
    corp_id="civ_ru_001b",
    name="Группа ГАЗ",
    country="Россия",
    city="Нижний Новгород",
    description="Крупнейший производитель коммерческого транспорта в России.",
    specialization=["trucks", "buses", "auto_parts"],
    founded=1932,
    website="www.gaz.ru",
    products={
        "trucks": {"name": "ГАЗель NEXT", "type": "trucks", "price": 25000, "description": "Легкие коммерческие грузовики"},
        "buses": {"name": "ПАЗ", "type": "buses", "price": 40000, "description": "Автобусы"},
        "auto_parts": {"name": "Запчасти ГАЗ", "type": "auto_parts", "price": 1500, "description": "Оригинальные запчасти"}
    }
)

KAMAZ = CivilCorporation(
    corp_id="civ_ru_002",
    name="КАМАЗ",
    country="Россия",
    city="Набережные Челны, Татарстан",
    description="Крупнейший производитель грузовых автомобилей в России.",
    specialization=["trucks", "buses", "auto_parts"],
    founded=1969,
    website="www.kamaz.ru",
    products={
        "trucks": {"name": "КАМАЗ", "type": "trucks", "price": 70000, "description": "Тягачи, самосвалы"},
        "buses": {"name": "НЕФАЗ", "type": "buses", "price": 80000, "description": "Городские и междугородние автобусы"},
        "auto_parts": {"name": "Запчасти КАМАЗ", "type": "auto_parts", "price": 3000, "description": "Оригинальные запчасти"}
    }
)

# Телекоммуникации
MTS = CivilCorporation(
    corp_id="civ_ru_003",
    name="МТС",
    country="Россия",
    city="Москва",
    description="Крупнейший оператор мобильной связи в России, предоставляет телекоммуникационные и цифровые услуги.",
    specialization=["mobile_services", "telecom_services", "internet_services", "media"],
    founded=1993,
    website="www.mts.ru",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 500, "description": "Тарифы для физических лиц"},
        "telecom_services": {"name": "Домашний интернет и ТВ", "type": "telecom_services", "price": 600, "description": "Доступ в интернет"},
        "internet_services": {"name": "Корпоративная связь", "type": "internet_services", "price": 3000, "description": "Для бизнеса"},
        "media": {"name": "KION", "type": "media", "price": 300, "description": "Стриминговый сервис"}
    }
)

MEGAFON = CivilCorporation(
    corp_id="civ_ru_003b",
    name="МегаФон",
    country="Россия",
    city="Москва",
    description="Один из ведущих операторов мобильной связи в России.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1993,
    website="www.megafon.ru",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 450, "description": "Тарифы для физических лиц"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 550, "description": "Доступ в интернет"},
        "internet_services": {"name": "B2B решения", "type": "internet_services", "price": 2500, "description": "Для корпоративных клиентов"}
    }
)

BEELINE = CivilCorporation(
    corp_id="civ_ru_003c",
    name="ВымпелКом (Билайн)",
    country="Россия",
    city="Москва",
    description="Крупный оператор мобильной и фиксированной связи.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1992,
    website="www.beeline.ru",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 480, "description": "Тарифы для физических лиц"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 520, "description": "Доступ в интернет"},
        "internet_services": {"name": "Облачные решения", "type": "internet_services", "price": 2000, "description": "Для бизнеса"}
    }
)

# IT и технологии
YANDEX = CivilCorporation(
    corp_id="civ_ru_004",
    name="Яндекс",
    country="Россия",
    city="Москва",
    description="Крупнейшая российская технологическая компания, владеет поисковой системой и экосистемой сервисов.",
    specialization=["internet_services", "software", "cloud_services", "ecommerce", "transport"],
    founded=1997,
    website="www.yandex.ru",
    products={
        "internet_services": {"name": "Поиск и портал", "type": "internet_services", "price": 0, "description": "Бесплатные сервисы с рекламой"},
        "software": {"name": "Яндекс.Браузер", "type": "software", "price": 0, "description": "Бесплатное ПО"},
        "cloud_services": {"name": "Yandex Cloud", "type": "cloud_services", "price": 1000, "description": "Облачные услуги"},
        "ecommerce": {"name": "Яндекс.Маркет", "type": "ecommerce", "price": 0, "description": "Торговая платформа"},
        "transport": {"name": "Яндекс.Такси", "type": "passenger_transport", "price": 200, "description": "Услуги такси"}
    }
)

VK = CivilCorporation(
    corp_id="civ_ru_004b",
    name="VK (Mail.ru Group)",
    country="Россия",
    city="Москва",
    description="Крупнейшая российская интернет-компания, владелец социальных сетей и игр.",
    specialization=["internet_services", "software", "gaming", "media"],
    founded=1998,
    website="www.vk.com",
    products={
        "internet_services": {"name": "ВКонтакте", "type": "internet_services", "price": 0, "description": "Социальная сеть"},
        "software": {"name": "Почта Mail.ru", "type": "software", "price": 0, "description": "Email-сервис"},
        "gaming": {"name": "Игры VK", "type": "gaming", "price": 500, "description": "Онлайн-игры"},
        "media": {"name": "VK Видео", "type": "media", "price": 0, "description": "Видеоплатформа"}
    }
)

KASPERSKY = CivilCorporation(
    corp_id="civ_ru_004c",
    name="Лаборатория Касперского",
    country="Россия",
    city="Москва",
    description="Международная компания, специализирующаяся на информационной безопасности.",
    specialization=["cybersecurity", "software"],
    founded=1997,
    website="www.kaspersky.ru",
    products={
        "cybersecurity": {"name": "Антивирус Касперского", "type": "cybersecurity", "price": 2000, "description": "Защита от вирусов"},
        "software": {"name": "Kaspersky Endpoint Security", "type": "software", "price": 5000, "description": "Корпоративная защита"}
    }
)

# Банки и финансы
SBERBANK = CivilCorporation(
    corp_id="civ_ru_005",
    name="Сбербанк",
    country="Россия",
    city="Москва",
    description="Крупнейший банк России и Восточной Европы, предоставляет полный спектр финансовых услуг.",
    specialization=["banking", "investments", "fintech", "insurance"],
    founded=1841,
    website="www.sberbank.ru",
    products={
        "banking": {"name": "Розничные банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты, карты"},
        "investments": {"name": "Сбер Управление активами", "type": "investments", "price": 1000, "description": "Инвестиционные продукты"},
        "fintech": {"name": "Сбербанк Онлайн", "type": "fintech", "price": 0, "description": "Мобильный банк"},
        "insurance": {"name": "СберСтрахование", "type": "insurance", "price": 5000, "description": "Страховые услуги"}
    }
)

VTB = CivilCorporation(
    corp_id="civ_ru_005b",
    name="ВТБ",
    country="Россия",
    city="Москва",
    description="Второй по величине банк России, системно значимый кредитор.",
    specialization=["banking", "investments"],
    founded=1990,
    website="www.vtb.ru",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Кредиты, депозиты"},
        "investments": {"name": "ВТБ Капитал", "type": "investments", "price": 1500, "description": "Инвестиционный банкинг"}
    }
)

TINKOFF = CivilCorporation(
    corp_id="civ_ru_005c",
    name="Т-Банк (Тинькофф)",
    country="Россия",
    city="Москва",
    description="Крупнейший онлайн-банк в России, пионер в области финтеха.",
    specialization=["fintech", "banking", "insurance"],
    founded=2006,
    website="www.tbank.ru",
    products={
        "fintech": {"name": "Мобильный банк", "type": "fintech", "price": 0, "description": "Управление счетами"},
        "banking": {"name": "Дебетовые и кредитные карты", "type": "banking", "price": 0, "description": "Банковские продукты"},
        "insurance": {"name": "Т-Страхование", "type": "insurance", "price": 3000, "description": "Страховые продукты"}
    }
)

# Ритейл
MAGNIT = CivilCorporation(
    corp_id="civ_ru_006",
    name="Магнит",
    country="Россия",
    city="Краснодар",
    description="Крупнейшая сеть продуктовых магазинов в России.",
    specialization=["retail", "supermarkets"],
    founded=1994,
    website="www.magnit.ru",
    products={
        "retail": {"name": "Продуктовые магазины", "type": "retail", "price": 0, "description": "Широкая сеть магазинов"},
        "supermarkets": {"name": "Супермаркеты Магнит", "type": "supermarkets", "price": 0, "description": "Продукты питания"}
    }
)

X5_GROUP = CivilCorporation(
    corp_id="civ_ru_006b",
    name="X5 Group",
    country="Россия",
    city="Москва",
    description="Владелец сетей Пятёрочка, Перекрёсток, Карусель.",
    specialization=["retail", "supermarkets", "ecommerce"],
    founded=2006,
    website="www.x5.ru",
    products={
        "retail": {"name": "Пятёрочка", "type": "retail", "price": 0, "description": "Магазины у дома"},
        "supermarkets": {"name": "Перекрёсток", "type": "supermarkets", "price": 0, "description": "Супермаркеты"},
        "ecommerce": {"name": "Vprok.ru", "type": "ecommerce", "price": 0, "description": "Интернет-доставка продуктов"}
    }
)

WILDBERRIES = CivilCorporation(
    corp_id="civ_ru_006c",
    name="Wildberries",
    country="Россия",
    city="Москва",
    description="Крупнейший онлайн-ритейлер в России, продает одежду, обувь, электронику.",
    specialization=["ecommerce", "retail", "logistics"],
    founded=2004,
    website="www.wildberries.ru",
    products={
        "ecommerce": {"name": "Wildberries", "type": "ecommerce", "price": 0, "description": "Маркетплейс"},
        "retail": {"name": "Товары повседневного спроса", "type": "retail", "price": 0, "description": "Широкий ассортимент"},
        "logistics": {"name": "Доставка Wildberries", "type": "logistics", "price": 200, "description": "Курьерская доставка"}
    }
)

OZON = CivilCorporation(
    corp_id="civ_ru_006d",
    name="Ozon",
    country="Россия",
    city="Москва",
    description="Один из ведущих онлайн-ритейлеров в России, продает товары различных категорий.",
    specialization=["ecommerce", "retail", "logistics"],
    founded=1998,
    website="www.ozon.ru",
    products={
        "ecommerce": {"name": "Ozon", "type": "ecommerce", "price": 0, "description": "Маркетплейс"},
        "retail": {"name": "Товары", "type": "retail", "price": 0, "description": "Электроника, одежда, товары для дома"},
        "logistics": {"name": "Ozon Доставка", "type": "logistics", "price": 250, "description": "Курьерская доставка"}
    }
)

# Энергетика
GAZPROM = CivilCorporation(
    corp_id="civ_ru_007",
    name="Газпром",
    country="Россия",
    city="Москва",
    description="Глобальная энергетическая компания, крупнейший производитель и поставщик газа.",
    specialization=["gas_supply", "energy_equipment"],
    founded=1989,
    website="www.gazprom.ru",
    products={
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 1000, "description": "Поставки газа"},
        "energy_equipment": {"name": "Газовое оборудование", "type": "energy_equipment", "price": 50000, "description": "Оборудование для газовой промышленности"}
    }
)

ROSNEFT = CivilCorporation(
    corp_id="civ_ru_007b",
    name="Роснефть",
    country="Россия",
    city="Москва",
    description="Крупнейшая нефтяная компания России.",
    specialization=["oil", "energy_equipment"],
    founded=1993,
    website="www.rosneft.ru",
    products={
        "oil": {"name": "Нефть и нефтепродукты", "type": "oil", "price": 500, "description": "Сырая нефть"},
        "energy_equipment": {"name": "Нефтегазовое оборудование", "type": "energy_equipment", "price": 60000, "description": "Оборудование для добычи"}
    }
)

LUKOIL = CivilCorporation(
    corp_id="civ_ru_007c",
    name="Лукойл",
    country="Россия",
    city="Москва",
    description="Одна из крупнейших вертикально интегрированных нефтяных компаний.",
    specialization=["oil", "gas_supply", "retail"],
    founded=1991,
    website="www.lukoil.ru",
    products={
        "oil": {"name": "Нефтепродукты", "type": "oil", "price": 550, "description": "Топливо, масла"},
        "gas_supply": {"name": "Газ", "type": "gas_supply", "price": 950, "description": "Природный газ"},
        "retail": {"name": "АЗС Лукойл", "type": "retail", "price": 0, "description": "Сеть заправочных станций"}
    }
)

ROSATOM = CivilCorporation(
    corp_id="civ_ru_007d",
    name="Росатом",
    country="Россия",
    city="Москва",
    description="Государственная корпорация по атомной энергии, лидер в ядерных технологиях.",
    specialization=["energy_equipment", "electricity"],
    founded=2007,
    website="www.rosatom.ru",
    products={
        "energy_equipment": {"name": "Атомные реакторы", "type": "energy_equipment", "price": 1000000, "description": "Оборудование для АЭС"},
        "electricity": {"name": "Атомная энергия", "type": "electricity", "price": 500, "description": "Электроэнергия"}
    }
)

# Сельскохозяйственная техника
ROSTSELMASH = CivilCorporation(
    corp_id="civ_ru_008",
    name="Ростсельмаш",
    country="Россия",
    city="Ростов-на-Дону",
    description="Ведущий производитель сельскохозяйственной техники в России.",
    specialization=["agricultural_machinery"],
    founded=1929,
    website="www.rostselmash.com",
    products={
        "agricultural_machinery": {"name": "Сельхозтехника", "type": "agricultural_machinery", "price": 200000, "description": "Комбайны, тракторы"}
    }
)

# Энергетическое оборудование
POWER_MACHINES = CivilCorporation(
    corp_id="civ_ru_009",
    name="Силовые машины",
    country="Россия",
    city="Санкт-Петербург",
    description="Крупнейший производитель энергетического оборудования в России.",
    specialization=["energy_equipment"],
    founded=2000,
    website="www.power-m.ru",
    products={
        "energy_equipment": {"name": "Энергооборудование", "type": "energy_equipment", "price": 1000000, "description": "Турбины, генераторы"}
    }
)

# Авиакосмическая промышленность
UAC = CivilCorporation(
    corp_id="civ_ru_010",
    name="Объединенная авиастроительная корпорация",
    country="Россия",
    city="Москва",
    description="Крупнейший производитель авиационной техники в России.",
    specialization=["aerospace_equipment", "drones"],
    founded=2006,
    website="www.uacrussia.ru",
    products={
        "aerospace_equipment": {"name": "Гражданские самолеты", "type": "aerospace_equipment", "price": 50000000, "description": "Sukhoi Superjet, MC-21"},
        "drones": {"name": "Беспилотники", "type": "drones", "price": 5000000, "description": "Беспилотные летательные аппараты"}
    }
)

# Продукты питания
RUSAGRO = CivilCorporation(
    corp_id="civ_ru_011",
    name="Русагро",
    country="Россия",
    city="Москва",
    description="Крупный производитель продуктов питания в России.",
    specialization=["food_products"],
    founded=1995,
    website="www.rusagrogroup.ru",
    products={
        "food_products": {"name": "Продукты питания", "type": "food_products", "price": 200, "description": "Мясные продукты, масло, сахар"}
    }
)

# Фармацевтика
PHARMSTANDARD = CivilCorporation(
    corp_id="civ_ru_012",
    name="Фармстандарт",
    country="Россия",
    city="Москва",
    description="Крупнейший производитель лекарственных средств в России.",
    specialization=["pharmaceuticals"],
    founded=2003,
    website="www.pharmstd.ru",
    products={
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 500, "description": "Рецептурные и безрецептурные лекарства"}
    }
)

# Химическая промышленность
URALKALI = CivilCorporation(
    corp_id="civ_ru_013",
    name="Уралкалий",
    country="Россия",
    city="Березники, Пермский край",
    description="Один из крупнейших производителей калийных удобрений в мире.",
    specialization=["chemicals", "fertilizers"],
    founded=1934,
    website="www.uralkali.com",
    products={
        "chemicals": {"name": "Калийные удобрения", "type": "chemicals", "price": 300, "description": "Минеральные удобрения"},
        "fertilizers": {"name": "Удобрения", "type": "fertilizers", "price": 350, "description": "Азотные удобрения"}
    }
)

# Логистика
RZD = CivilCorporation(
    corp_id="civ_ru_014",
    name="Российские железные дороги (РЖД)",
    country="Россия",
    city="Москва",
    description="Государственная компания, управляющая железнодорожной сетью России.",
    specialization=["logistics", "freight", "passenger_transport"],
    founded=2003,
    website="www.rzd.ru",
    products={
        "logistics": {"name": "Железнодорожные перевозки", "type": "logistics", "price": 1000, "description": "Грузовые перевозки"},
        "freight": {"name": "Грузовые тарифы", "type": "freight", "price": 500, "description": "Перевозка грузов"},
        "passenger_transport": {"name": "Пассажирские билеты", "type": "passenger_transport", "price": 3000, "description": "Поезда дальнего следования"}
    }
)

# Рестораны
ROSVEN = CivilCorporation(
    corp_id="civ_ru_015",
    name="Росинтер Ресторантс",
    country="Россия",
    city="Москва",
    description="Крупнейшая ресторанная компания в России, управляет сетями IL Патио, T.G.I. Friday's.",
    specialization=["restaurants", "fast_food"],
    founded=1990,
    website="www.rosinter.com",
    products={
        "restaurants": {"name": "IL Патио", "type": "restaurants", "price": 1500, "description": "Итальянские рестораны"},
        "fast_food": {"name": "T.G.I. Friday's", "type": "fast_food", "price": 1200, "description": "Американская кухня"}
    }
)

# Медицинские услуги
MEDSI = CivilCorporation(
    corp_id="civ_ru_016",
    name="Медси",
    country="Россия",
    city="Москва",
    description="Крупнейшая сеть частных клиник в России.",
    specialization=["healthcare_services", "hospital_services"],
    founded=1996,
    website="www.medsi.ru",
    products={
        "healthcare_services": {"name": "Медицинские услуги", "type": "healthcare_services", "price": 3000, "description": "Консультации врачей"},
        "hospital_services": {"name": "Стационарное лечение", "type": "hospital_services", "price": 50000, "description": "Госпитализация"}
    }
)

# Строительство
PIK = CivilCorporation(
    corp_id="civ_ru_017",
    name="Группа ПИК",
    country="Россия",
    city="Москва",
    description="Крупнейший девелопер жилой недвижимости в России.",
    specialization=["construction", "real_estate", "property_management"],
    founded=1994,
    website="www.pik.ru",
    products={
        "construction": {"name": "Строительные услуги", "type": "construction", "price": 5000000, "description": "Строительство жилья"},
        "real_estate": {"name": "Продажа квартир", "type": "real_estate", "price": 5000000, "description": "Недвижимость"},
        "property_management": {"name": "Управление недвижимостью", "type": "property_management", "price": 5000, "description": "Обслуживание домов"}
    }
)


# ==================== КОРПОРАЦИИ КИТАЯ (расширенные) ====================

# Автомобилестроение
SAIC = CivilCorporation(
    corp_id="civ_cn_001",
    name="SAIC Motor",
    country="Китай",
    city="Шанхай",
    description="Крупнейший автопроизводитель Китая, выпускает автомобили MG, Maxus.",
    specialization=["cars", "trucks", "auto_parts"],
    founded=1955,
    website="www.saicmotor.com",
    products={
        "cars": {"name": "MG, Roewe", "type": "cars", "price": 20000, "description": "Легковые автомобили"},
        "trucks": {"name": "Maxus", "type": "trucks", "price": 40000, "description": "Грузовики"},
        "auto_parts": {"name": "Автозапчасти", "type": "auto_parts", "price": 2000, "description": "Оригинальные запчасти"}
    }
)

BYD = CivilCorporation(
    corp_id="civ_cn_001b",
    name="BYD Company",
    country="Китай",
    city="Шэньчжэнь",
    description="Мировой лидер в производстве электромобилей и аккумуляторов.",
    specialization=["cars", "energy_equipment", "buses"],
    founded=1995,
    website="www.byd.com",
    products={
        "cars": {"name": "BYD электромобили", "type": "cars", "price": 25000, "description": "Электромобили"},
        "energy_equipment": {"name": "Аккумуляторы", "type": "energy_equipment", "price": 5000, "description": "Батареи"},
        "buses": {"name": "Электробусы", "type": "buses", "price": 200000, "description": "Электрические автобусы"}
    }
)

# Технологическое оборудование
HUAWEI = CivilCorporation(
    corp_id="civ_cn_002",
    name="Huawei",
    country="Китай",
    city="Шэньчжэнь",
    description="Мировой лидер в производстве телекоммуникационного оборудования и электроники.",
    specialization=["telecom_equipment", "tech_equipment", "consumer_electronics", "smartphones"],
    founded=1987,
    website="www.huawei.com",
    products={
        "telecom_equipment": {"name": "Телеком-оборудование", "type": "telecom_equipment", "price": 50000, "description": "Базовые станции"},
        "tech_equipment": {"name": "Серверы", "type": "tech_equipment", "price": 20000, "description": "Корпоративное оборудование"},
        "consumer_electronics": {"name": "Бытовая электроника", "type": "consumer_electronics", "price": 1000, "description": "Смартфоны, планшеты"},
        "smartphones": {"name": "Huawei P, Mate", "type": "smartphones", "price": 800, "description": "Смартфоны"}
    }
)

XIAOMI = CivilCorporation(
    corp_id="civ_cn_007",
    name="Xiaomi",
    country="Китай",
    city="Пекин",
    description="Ведущий производитель бытовой электроники и умных устройств.",
    specialization=["consumer_electronics", "tech_equipment", "smartphones"],
    founded=2010,
    website="www.mi.com",
    products={
        "consumer_electronics": {"name": "Бытовая электроника", "type": "consumer_electronics", "price": 500, "description": "Смартфоны, планшеты, ТВ"},
        "tech_equipment": {"name": "Умные устройства", "type": "tech_equipment", "price": 300, "description": "Умный дом, IoT устройства"},
        "smartphones": {"name": "Xiaomi", "type": "smartphones", "price": 400, "description": "Смартфоны"}
    }
)

LENOVO = CivilCorporation(
    corp_id="civ_cn_002b",
    name="Lenovo Group",
    country="Китай",
    city="Пекин",
    description="Крупнейший производитель персональных компьютеров в мире.",
    specialization=["computers", "tech_equipment", "smartphones"],
    founded=1984,
    website="www.lenovo.com",
    products={
        "computers": {"name": "ThinkPad, Legion", "type": "computers", "price": 1200, "description": "Ноутбуки"},
        "tech_equipment": {"name": "Серверы", "type": "tech_equipment", "price": 15000, "description": "Корпоративное оборудование"},
        "smartphones": {"name": "Lenovo phones", "type": "smartphones", "price": 300, "description": "Смартфоны"}
    }
)

TENCENT = CivilCorporation(
    corp_id="civ_cn_002c",
    name="Tencent Holdings",
    country="Китай",
    city="Шэньчжэнь",
    description="Технологический конгломерат, владелец WeChat и крупнейший игровой компании.",
    specialization=["internet_services", "gaming", "media", "fintech"],
    founded=1998,
    website="www.tencent.com",
    products={
        "internet_services": {"name": "WeChat", "type": "internet_services", "price": 0, "description": "Мессенджер и соцсеть"},
        "gaming": {"name": "Игры Tencent", "type": "gaming", "price": 500, "description": "Видеоигры"},
        "media": {"name": "Tencent Video", "type": "media", "price": 10, "description": "Стриминг"},
        "fintech": {"name": "WeChat Pay", "type": "fintech", "price": 0, "description": "Платежная система"}
    }
)

ALIBABA = CivilCorporation(
    corp_id="civ_cn_002d",
    name="Alibaba Group",
    country="Китай",
    city="Ханчжоу",
    description="Крупнейшая компания электронной коммерции в мире.",
    specialization=["ecommerce", "cloud_services", "fintech", "logistics"],
    founded=1999,
    website="www.alibabagroup.com",
    products={
        "ecommerce": {"name": "Taobao, Tmall", "type": "ecommerce", "price": 0, "description": "Торговые платформы"},
        "cloud_services": {"name": "Alibaba Cloud", "type": "cloud_services", "price": 200, "description": "Облачные услуги"},
        "fintech": {"name": "Alipay", "type": "fintech", "price": 0, "description": "Платежная система"},
        "logistics": {"name": "Cainiao", "type": "logistics", "price": 50, "description": "Логистика"}
    }
)

BAIDU = CivilCorporation(
    corp_id="civ_cn_002e",
    name="Baidu, Inc.",
    country="Китай",
    city="Пекин",
    description="Ведущая китайская поисковая система и технологическая компания.",
    specialization=["internet_services", "cloud_services", "ai"],
    founded=2000,
    website="www.baidu.com",
    products={
        "internet_services": {"name": "Baidu Search", "type": "internet_services", "price": 0, "description": "Поисковая система"},
        "cloud_services": {"name": "Baidu Cloud", "type": "cloud_services", "price": 150, "description": "Облачные услуги"},
        "ai": {"name": "ИИ-технологии", "type": "tech_equipment", "price": 1000, "description": "Искусственный интеллект"}
    }
)

# Телекоммуникации
CHINA_MOBILE = CivilCorporation(
    corp_id="civ_cn_003",
    name="China Mobile",
    country="Китай",
    city="Пекин",
    description="Крупнейший оператор мобильной связи в мире.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1997,
    website="www.chinamobileltd.com",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 300, "description": "Сотовые тарифы"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 400, "description": "Широкополосный доступ"},
        "internet_services": {"name": "Корпоративная связь", "type": "internet_services", "price": 2000, "description": "B2B услуги"}
    }
)

CHINA_TELECOM = CivilCorporation(
    corp_id="civ_cn_003b",
    name="China Telecom",
    country="Китай",
    city="Пекин",
    description="Один из крупнейших операторов фиксированной и мобильной связи.",
    specialization=["telecom_services", "internet_services", "cloud_services"],
    founded=2002,
    website="www.chinatelecom-h.com",
    products={
        "telecom_services": {"name": "Телефонная связь", "type": "telecom_services", "price": 200, "description": "Домашний телефон"},
        "internet_services": {"name": "Интернет", "type": "internet_services", "price": 350, "description": "Доступ в интернет"},
        "cloud_services": {"name": "Облачные услуги", "type": "cloud_services", "price": 500, "description": "Корпоративные облака"}
    }
)

# Строительная техника
SANY = CivilCorporation(
    corp_id="civ_cn_004",
    name="SANY Group",
    country="Китай",
    city="Чанша, Хунань",
    description="Крупнейший производитель строительной техники в Китае.",
    specialization=["construction_machinery"],
    founded=1989,
    website="www.sany.com",
    products={
        "construction_machinery": {"name": "Строительная техника", "type": "construction_machinery", "price": 300000, "description": "Экскаваторы, краны"}
    }
)

# Энергетическое оборудование
GOLDWIND = CivilCorporation(
    corp_id="civ_cn_005",
    name="Goldwind",
    country="Китай",
    city="Пекин",
    description="Крупнейший производитель ветряных турбин в Китае.",
    specialization=["energy_equipment"],
    founded=1998,
    website="www.goldwind.com",
    products={
        "energy_equipment": {"name": "Ветряные турбины", "type": "energy_equipment", "price": 2000000, "description": "Ветроэнергетические установки"}
    }
)

# Железнодорожное оборудование
CRRC = CivilCorporation(
    corp_id="civ_cn_006",
    name="CRRC Corporation",
    country="Китай",
    city="Пекин",
    description="Крупнейший в мире производитель железнодорожной техники.",
    specialization=["industrial_equipment"],
    founded=2015,
    website="www.crrcgc.cc",
    products={
        "industrial_equipment": {"name": "Железнодорожная техника", "type": "industrial_equipment", "price": 1000000, "description": "Локомотивы, вагоны"}
    }
)

# Текстильная промышленность
TEXHONG = CivilCorporation(
    corp_id="civ_cn_007",
    name="Texhong Textile",
    country="Китай",
    city="Гонконг",
    description="Крупнейший производитель текстиля в Китае.",
    specialization=["clothing"],
    founded=1995,
    website="www.texhong.com",
    products={
        "clothing": {"name": "Текстиль и одежда", "type": "clothing", "price": 50, "description": "Ткани, готовая одежда"}
    }
)

# Бытовая электроника
DJI = CivilCorporation(
    corp_id="civ_cn_008",
    name="DJI (Da-Jiang Innovations)",
    country="Китай",
    city="Шэньчжэнь",
    description="Мировой лидер в производстве гражданских и промышленных дронов.",
    specialization=["fpv_drones", "drones", "consumer_electronics"],
    founded=2006,
    website="www.dji.com",
    products={
        "fpv_drones": {"name": "DJI Mavic FPV", "type": "fpv_drones", "price": 1000, "description": "FPV-дроны для армии"},
        "drones": {"name": "DJI промышленные", "type": "drones", "price": 15000, "description": "Промышленные дроны"},
        "consumer_electronics": {"name": "DJI потребительские", "type": "consumer_electronics", "price": 800, "description": "Дроны для съемки"}
    }
)

# Финансы
ICBC = CivilCorporation(
    corp_id="civ_cn_009",
    name="Industrial and Commercial Bank of China (ICBC)",
    country="Китай",
    city="Пекин",
    description="Крупнейший банк в мире по размеру активов.",
    specialization=["banking", "investments"],
    founded=1984,
    website="www.icbc.com.cn",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Кредиты, депозиты"},
        "investments": {"name": "Инвестиционные продукты", "type": "investments", "price": 1000, "description": "Управление активами"}
    }
)

PING_AN = CivilCorporation(
    corp_id="civ_cn_009b",
    name="Ping An Insurance",
    country="Китай",
    city="Шэньчжэнь",
    description="Крупнейшая страховая компания в Китае, также занимается банковскими и финансовыми услугами.",
    specialization=["insurance", "banking", "fintech"],
    founded=1988,
    website="www.pingan.com",
    products={
        "insurance": {"name": "Страховые услуги", "type": "insurance", "price": 2000, "description": "Страхование жизни и имущества"},
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Кредиты"},
        "fintech": {"name": "Ping An Technology", "type": "fintech", "price": 500, "description": "Финтех-решения"}
    }
)

# Ритейл
JD_COM = CivilCorporation(
    corp_id="civ_cn_010",
    name="JD.com",
    country="Китай",
    city="Пекин",
    description="Один из крупнейших онлайн-ритейлеров в Китае.",
    specialization=["ecommerce", "logistics", "retail"],
    founded=1998,
    website="www.jd.com",
    products={
        "ecommerce": {"name": "JD.com", "type": "ecommerce", "price": 0, "description": "Торговая платформа"},
        "logistics": {"name": "JD Logistics", "type": "logistics", "price": 50, "description": "Доставка"},
        "retail": {"name": "7Fresh", "type": "retail", "price": 0, "description": "Продуктовые магазины"}
    }
)

# Энергетика
CNPC = CivilCorporation(
    corp_id="civ_cn_011",
    name="China National Petroleum Corporation (CNPC)",
    country="Китай",
    city="Пекин",
    description="Крупнейшая нефтегазовая компания Китая.",
    specialization=["oil", "gas_supply", "energy_equipment"],
    founded=1988,
    website="www.cnpc.com.cn",
    products={
        "oil": {"name": "Нефть", "type": "oil", "price": 450, "description": "Сырая нефть"},
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 800, "description": "Газ"},
        "energy_equipment": {"name": "Оборудование", "type": "energy_equipment", "price": 50000, "description": "Нефтегазовое оборудование"}
    }
)

STATE_GRID = CivilCorporation(
    corp_id="civ_cn_011b",
    name="State Grid Corporation of China",
    country="Китай",
    city="Пекин",
    description="Крупнейшая в мире коммунальная компания, оператор электросетей.",
    specialization=["electricity", "energy_equipment"],
    founded=2002,
    website="www.sgcc.com.cn",
    products={
        "electricity": {"name": "Электроэнергия", "type": "electricity", "price": 100, "description": "Поставка электричества"},
        "energy_equipment": {"name": "Энергооборудование", "type": "energy_equipment", "price": 30000, "description": "Трансформаторы"}
    }
)


# ==================== КОРПОРАЦИИ ГЕРМАНИИ (расширенные) ====================

# Автомобилестроение
VOLKSWAGEN = CivilCorporation(
    corp_id="civ_de_001",
    name="Volkswagen Group",
    country="Германия",
    city="Вольфсбург",
    description="Крупнейший автомобильный концерн Европы, включает бренды Volkswagen, Audi, Porsche.",
    specialization=["cars", "trucks", "auto_parts"],
    founded=1937,
    website="www.volkswagen.com",
    products={
        "cars": {"name": "Volkswagen, Audi, Porsche", "type": "cars", "price": 35000, "description": "Легковые автомобили"},
        "trucks": {"name": "MAN", "type": "trucks", "price": 60000, "description": "Грузовики"},
        "auto_parts": {"name": "Автозапчасти", "type": "auto_parts", "price": 4000, "description": "Оригинальные запчасти"}
    }
)

BMW = CivilCorporation(
    corp_id="civ_de_002",
    name="BMW Group",
    country="Германия",
    city="Мюнхен",
    description="Производитель автомобилей премиум-класса и мотоциклов.",
    specialization=["cars", "auto_parts"],
    founded=1916,
    website="www.bmw.com",
    products={
        "cars": {"name": "BMW, Mini", "type": "cars", "price": 50000, "description": "Автомобили премиум"},
        "auto_parts": {"name": "Запчасти BMW", "type": "auto_parts", "price": 5000, "description": "Оригинальные запчасти"}
    }
)

MERCEDES = CivilCorporation(
    corp_id="civ_de_003",
    name="Mercedes-Benz Group",
    country="Германия",
    city="Штутгарт",
    description="Легендарный производитель автомобилей премиум-класса, грузовиков и автобусов.",
    specialization=["cars", "trucks", "buses", "auto_parts"],
    founded=1926,
    website="www.mercedes-benz.com",
    products={
        "cars": {"name": "Mercedes-Benz", "type": "cars", "price": 55000, "description": "Автомобили"},
        "trucks": {"name": "Mercedes-Benz Trucks", "type": "trucks", "price": 80000, "description": "Грузовики"},
        "buses": {"name": "Mercedes-Benz Buses", "type": "buses", "price": 200000, "description": "Автобусы"},
        "auto_parts": {"name": "Запчасти", "type": "auto_parts", "price": 6000, "description": "Оригинальные запчасти"}
    }
)

# Промышленное оборудование
SIEMENS = CivilCorporation(
    corp_id="civ_de_004",
    name="Siemens",
    country="Германия",
    city="Мюнхен",
    description="Глобальный технологический концерн, производитель промышленного оборудования и электроники.",
    specialization=["industrial_equipment", "electrical_equipment", "energy_equipment", "medical_equipment"],
    founded=1847,
    website="www.siemens.com",
    products={
        "industrial_equipment": {"name": "Промышленное оборудование", "type": "industrial_equipment", "price": 100000, "description": "Приводы, автоматизация"},
        "electrical_equipment": {"name": "Электротехника", "type": "electrical_equipment", "price": 20000, "description": "Трансформаторы"},
        "energy_equipment": {"name": "Турбины", "type": "energy_equipment", "price": 500000, "description": "Газовые турбины"},
        "medical_equipment": {"name": "Медицинское оборудование", "type": "medical_equipment", "price": 150000, "description": "МРТ, КТ"}
    }
)

# Химическая промышленность
BASF = CivilCorporation(
    corp_id="civ_de_005",
    name="BASF",
    country="Германия",
    city="Людвигсхафен",
    description="Крупнейший химический концерн в мире.",
    specialization=["chemicals", "pharmaceuticals", "fertilizers"],
    founded=1865,
    website="www.basf.com",
    products={
        "chemicals": {"name": "Химическая продукция", "type": "chemicals", "price": 500, "description": "Полимеры, растворители"},
        "pharmaceuticals": {"name": "Фармацевтика", "type": "pharmaceuticals", "price": 800, "description": "Лекарства"},
        "fertilizers": {"name": "Удобрения", "type": "fertilizers", "price": 400, "description": "Минеральные удобрения"}
    }
)

# Станкостроение
TRUMPF = CivilCorporation(
    corp_id="civ_de_006",
    name="Trumpf",
    country="Германия",
    city="Дитцинген",
    description="Мировой лидер в производстве станков и лазерного оборудования.",
    specialization=["machine_tools", "industrial_robots"],
    founded=1923,
    website="www.trumpf.com",
    products={
        "machine_tools": {"name": "Станки", "type": "machine_tools", "price": 250000, "description": "Лазерные станки"},
        "industrial_robots": {"name": "Промышленные роботы", "type": "industrial_robots", "price": 100000, "description": "Роботизированные системы"}
    }
)

# Фармацевтика
BAYER = CivilCorporation(
    corp_id="civ_de_007",
    name="Bayer",
    country="Германия",
    city="Леверкузен",
    description="Глобальная фармацевтическая компания, производитель лекарств и средств защиты растений.",
    specialization=["pharmaceuticals", "chemicals", "fertilizers"],
    founded=1863,
    website="www.bayer.com",
    products={
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 600, "description": "Рецептурные препараты"},
        "chemicals": {"name": "Средства защиты", "type": "chemicals", "price": 400, "description": "Гербициды"},
        "fertilizers": {"name": "Удобрения", "type": "fertilizers", "price": 350, "description": "Средства для растений"}
    }
)

SAP = CivilCorporation(
    corp_id="civ_de_008",
    name="SAP SE",
    country="Германия",
    city="Вальдорф",
    description="Мировой лидер в области корпоративного программного обеспечения.",
    specialization=["software", "cloud_services", "it_services"],
    founded=1972,
    website="www.sap.com",
    products={
        "software": {"name": "Корпоративное ПО", "type": "software", "price": 50000, "description": "ERP системы"},
        "cloud_services": {"name": "SAP Cloud", "type": "cloud_services", "price": 1000, "description": "Облачные решения"},
        "it_services": {"name": "Консалтинг", "type": "it_services", "price": 500, "description": "IT-консалтинг"}
    }
)

DEUTSCHE_TELEKOM = CivilCorporation(
    corp_id="civ_de_009",
    name="Deutsche Telekom",
    country="Германия",
    city="Бонн",
    description="Крупнейший телекоммуникационный оператор Германии.",
    specialization=["telecom_services", "mobile_services", "internet_services"],
    founded=1995,
    website="www.telekom.com",
    products={
        "telecom_services": {"name": "Домашний телефон", "type": "telecom_services", "price": 30, "description": "Фиксированная связь"},
        "mobile_services": {"name": "Magenta Mobilfunk", "type": "mobile_services", "price": 50, "description": "Мобильная связь"},
        "internet_services": {"name": "MagentaZuhause", "type": "internet_services", "price": 40, "description": "Домашний интернет"}
    }
)

ALLIANZ = CivilCorporation(
    corp_id="civ_de_010",
    name="Allianz SE",
    country="Германия",
    city="Мюнхен",
    description="Крупнейшая страховая компания в мире.",
    specialization=["insurance", "investments"],
    founded=1890,
    website="www.allianz.com",
    products={
        "insurance": {"name": "Страхование", "type": "insurance", "price": 1000, "description": "Страхование жизни и имущества"},
        "investments": {"name": "Управление активами", "type": "investments", "price": 1500, "description": "Инвестиционные продукты"}
    }
)

DEUTSCHE_BANK = CivilCorporation(
    corp_id="civ_de_011",
    name="Deutsche Bank",
    country="Германия",
    city="Франкфурт",
    description="Ведущий немецкий банк, предоставляет финансовые услуги по всему миру.",
    specialization=["banking", "investments"],
    founded=1870,
    website="www.db.com",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиционный банкинг", "type": "investments", "price": 2000, "description": "Управление капиталом"}
    }
)

ADIDAS = CivilCorporation(
    corp_id="civ_de_012",
    name="Adidas AG",
    country="Германия",
    city="Херцогенаурах",
    description="Один из крупнейших производителей спортивной одежды и обуви.",
    specialization=["clothing", "footwear"],
    founded=1949,
    website="www.adidas.com",
    products={
        "clothing": {"name": "Спортивная одежда", "type": "clothing", "price": 80, "description": "Футболки, штаны"},
        "footwear": {"name": "Кроссовки", "type": "footwear", "price": 120, "description": "Спортивная обувь"}
    }
)

PUMA = CivilCorporation(
    corp_id="civ_de_012b",
    name="Puma SE",
    country="Германия",
    city="Херцогенаурах",
    description="Крупный производитель спортивной одежды и обуви.",
    specialization=["clothing", "footwear"],
    founded=1948,
    website="www.puma.com",
    products={
        "clothing": {"name": "Спортивная одежда", "type": "clothing", "price": 70, "description": "Футболки"},
        "footwear": {"name": "Кроссовки", "type": "footwear", "price": 100, "description": "Спортивная обувь"}
    }
)

LUFTHANSA = CivilCorporation(
    corp_id="civ_de_013",
    name="Deutsche Lufthansa AG",
    country="Германия",
    city="Кёльн",
    description="Крупнейшая авиакомпания Германии, выполняет международные рейсы.",
    specialization=["airlines", "passenger_transport", "logistics"],
    founded=1953,
    website="www.lufthansa.com",
    products={
        "airlines": {"name": "Авиабилеты", "type": "airlines", "price": 400, "description": "Пассажирские перевозки"},
        "passenger_transport": {"name": "Бизнес-класс", "type": "passenger_transport", "price": 2000, "description": "Премиальные перелеты"},
        "logistics": {"name": "Lufthansa Cargo", "type": "logistics", "price": 800, "description": "Грузовые перевозки"}
    }
)

DHL = CivilCorporation(
    corp_id="civ_de_014",
    name="DHL Group",
    country="Германия",
    city="Бонн",
    description="Мировой лидер в области логистики и экспресс-доставки.",
    specialization=["logistics", "freight"],
    founded=1969,
    website="www.dhl.com",
    products={
        "logistics": {"name": "Экспресс-доставка", "type": "logistics", "price": 30, "description": "Доставка посылок"},
        "freight": {"name": "Грузоперевозки", "type": "freight", "price": 600, "description": "Перевозка грузов"}
    }
)

BOSCH = CivilCorporation(
    corp_id="civ_de_015",
    name="Robert Bosch GmbH",
    country="Германия",
    city="Герлинген",
    description="Крупнейший поставщик автомобильных компонентов и бытовой техники.",
    specialization=["auto_parts", "industrial_equipment", "household_goods"],
    founded=1886,
    website="www.bosch.com",
    products={
        "auto_parts": {"name": "Автокомпоненты", "type": "auto_parts", "price": 2000, "description": "Системы для авто"},
        "industrial_equipment": {"name": "Промышленное оборудование", "type": "industrial_equipment", "price": 50000, "description": "Инструменты"},
        "household_goods": {"name": "Бытовая техника", "type": "household_goods", "price": 500, "description": "Техника для дома"}
    }
)


# ==================== КОРПОРАЦИИ ВЕЛИКОБРИТАНИИ ====================

BP = CivilCorporation(
    corp_id="civ_uk_001",
    name="BP p.l.c.",
    country="Великобритания",
    city="Лондон",
    description="Глобальная нефтегазовая компания, одна из крупнейших в мире.",
    specialization=["oil", "gas_supply", "energy_equipment"],
    founded=1909,
    website="www.bp.com",
    products={
        "oil": {"name": "Нефть", "type": "oil", "price": 500, "description": "Сырая нефть"},
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 850, "description": "Газ"},
        "energy_equipment": {"name": "Оборудование", "type": "energy_equipment", "price": 45000, "description": "Нефтегазовое оборудование"}
    }
)

SHELL = CivilCorporation(
    corp_id="civ_uk_001b",
    name="Shell plc",
    country="Великобритания",
    city="Лондон",
    description="Глобальная энергетическая и нефтехимическая компания.",
    specialization=["oil", "gas_supply", "chemicals"],
    founded=1907,
    website="www.shell.com",
    products={
        "oil": {"name": "Нефтепродукты", "type": "oil", "price": 520, "description": "Топливо"},
        "gas_supply": {"name": "Газ", "type": "gas_supply", "price": 820, "description": "Природный газ"},
        "chemicals": {"name": "Нефтехимия", "type": "chemicals", "price": 400, "description": "Химическая продукция"}
    }
)

VODAFONE = CivilCorporation(
    corp_id="civ_uk_002",
    name="Vodafone Group",
    country="Великобритания",
    city="Ньюбери",
    description="Один из крупнейших операторов мобильной связи в мире.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1984,
    website="www.vodafone.com",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 40, "description": "Сотовые тарифы"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 35, "description": "Широкополосный доступ"},
        "internet_services": {"name": "Корпоративная связь", "type": "internet_services", "price": 500, "description": "B2B услуги"}
    }
)

BT_GROUP = CivilCorporation(
    corp_id="civ_uk_002b",
    name="BT Group",
    country="Великобритания",
    city="Лондон",
    description="Крупнейший оператор фиксированной связи в Великобритании.",
    specialization=["telecom_services", "internet_services", "media"],
    founded=1969,
    website="www.bt.com",
    products={
        "telecom_services": {"name": "Домашний телефон", "type": "telecom_services", "price": 25, "description": "Фиксированная связь"},
        "internet_services": {"name": "BT Broadband", "type": "internet_services", "price": 40, "description": "Интернет"},
        "media": {"name": "BT Sport", "type": "media", "price": 30, "description": "Спортивное ТВ"}
    }
)

GLAXOSMITHKLINE = CivilCorporation(
    corp_id="civ_uk_003",
    name="GSK plc",
    country="Великобритания",
    city="Брентфорд",
    description="Глобальная фармацевтическая компания, производитель лекарств и вакцин.",
    specialization=["pharmaceuticals", "medical_supplies"],
    founded=2000,
    website="www.gsk.com",
    products={
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 700, "description": "Рецептурные препараты"},
        "medical_supplies": {"name": "Медицинские изделия", "type": "medical_supplies", "price": 200, "description": "Средства ухода"}
    }
)

ASTRAZENECA = CivilCorporation(
    corp_id="civ_uk_003b",
    name="AstraZeneca",
    country="Великобритания",
    city="Кембридж",
    description="Глобальная фармацевтическая компания, известная вакциной от COVID-19.",
    specialization=["pharmaceuticals"],
    founded=1999,
    website="www.astrazeneca.com",
    products={
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 800, "description": "Рецептурные препараты"}
    }
)

HSBC = CivilCorporation(
    corp_id="civ_uk_004",
    name="HSBC Holdings",
    country="Великобритания",
    city="Лондон",
    description="Один из крупнейших банковских и финансовых конгломератов в мире.",
    specialization=["banking", "investments", "insurance"],
    founded=1991,
    website="www.hsbc.com",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Управление активами", "type": "investments", "price": 1200, "description": "Инвестиции"},
        "insurance": {"name": "Страхование", "type": "insurance", "price": 800, "description": "Страховые продукты"}
    }
)

BARCLAYS = CivilCorporation(
    corp_id="civ_uk_004b",
    name="Barclays",
    country="Великобритания",
    city="Лондон",
    description="Крупный британский банк с глобальным присутствием.",
    specialization=["banking", "investments"],
    founded=1690,
    website="www.barclays.com",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиционный банкинг", "type": "investments", "price": 1500, "description": "Управление капиталом"}
    }
)

LLOYDS = CivilCorporation(
    corp_id="civ_uk_004c",
    name="Lloyds Banking Group",
    country="Великобритания",
    city="Лондон",
    description="Крупнейший розничный банк в Великобритании.",
    specialization=["banking", "insurance"],
    founded=2009,
    website="www.lloydsbankinggroup.com",
    products={
        "banking": {"name": "Розничные банковские услуги", "type": "banking", "price": 0, "description": "Счета, ипотека"},
        "insurance": {"name": "Страхование", "type": "insurance", "price": 500, "description": "Страховые продукты"}
    }
)

UNILEVER = CivilCorporation(
    corp_id="civ_uk_005",
    name="Unilever plc",
    country="Великобритания",
    city="Лондон",
    description="Крупнейший производитель потребительских товаров, продуктов питания и косметики.",
    specialization=["food_products", "cosmetics", "household_goods", "sanitary_products"],
    founded=1929,
    website="www.unilever.com",
    products={
        "food_products": {"name": "Продукты питания", "type": "food_products", "price": 150, "description": "Мороженое, чай"},
        "cosmetics": {"name": "Косметика", "type": "cosmetics", "price": 200, "description": "Кремы, шампуни"},
        "household_goods": {"name": "Товары для дома", "type": "household_goods", "price": 100, "description": "Моющие средства"},
        "sanitary_products": {"name": "Средства гигиены", "type": "sanitary_products", "price": 80, "description": "Дезодоранты"}
    }
)

BRITISH_AMERICAN_TOBACCO = CivilCorporation(
    corp_id="civ_uk_006",
    name="British American Tobacco",
    country="Великобритания",
    city="Лондон",
    description="Один из крупнейших производителей табачных изделий в мире.",
    specialization=["consumer_electronics"],
    founded=1902,
    website="www.bat.com",
    products={
        "consumer_electronics": {"name": "Электронные сигареты", "type": "consumer_electronics", "price": 50, "description": "Вейпы"}
    }
)

ROLLS_ROYCE = CivilCorporation(
    corp_id="civ_uk_007",
    name="Rolls-Royce Holdings",
    country="Великобритания",
    city="Лондон",
    description="Производитель авиационных двигателей и энергетического оборудования.",
    specialization=["aerospace_equipment", "energy_equipment"],
    founded=1906,
    website="www.rolls-royce.com",
    products={
        "aerospace_equipment": {"name": "Авиадвигатели", "type": "aerospace_equipment", "price": 20000000, "description": "Реактивные двигатели"},
        "energy_equipment": {"name": "Энергооборудование", "type": "energy_equipment", "price": 300000, "description": "Турбины"}
    }
)

BAE_SYSTEMS = CivilCorporation(
    corp_id="civ_uk_008",
    name="BAE Systems",
    country="Великобритания",
    city="Лондон",
    description="Крупнейшая оборонная компания Великобритании, производит военную технику.",
    specialization=["aerospace_equipment", "drones", "industrial_equipment"],
    founded=1999,
    website="www.baesystems.com",
    products={
        "aerospace_equipment": {"name": "Авиационная техника", "type": "aerospace_equipment", "price": 15000000, "description": "Военные самолеты"},
        "drones": {"name": "Беспилотники", "type": "drones", "price": 2000000, "description": "Военные дроны"},
        "industrial_equipment": {"name": "Промышленное оборудование", "type": "industrial_equipment", "price": 500000, "description": "Оборудование для оборонки"}
    }
)

TESCO = CivilCorporation(
    corp_id="civ_uk_009",
    name="Tesco plc",
    country="Великобритания",
    city="Уэлин-Гарден-Сити",
    description="Крупнейшая сеть супермаркетов в Великобритании.",
    specialization=["retail", "supermarkets", "ecommerce"],
    founded=1919,
    website="www.tesco.com",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Товары повседневного спроса"},
        "supermarkets": {"name": "Tesco Superstores", "type": "supermarkets", "price": 0, "description": "Продуктовые магазины"},
        "ecommerce": {"name": "Tesco.com", "type": "ecommerce", "price": 0, "description": "Онлайн-доставка"}
    }
)

SAINSBURY = CivilCorporation(
    corp_id="civ_uk_009b",
    name="J Sainsbury plc",
    country="Великобритания",
    city="Лондон",
    description="Вторая по величине сеть супермаркетов в Великобритании.",
    specialization=["retail", "supermarkets"],
    founded=1869,
    website="www.sainsburys.co.uk",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Товары"},
        "supermarkets": {"name": "Sainsbury's", "type": "supermarkets", "price": 0, "description": "Продуктовые магазины"}
    }
)


# ==================== КОРПОРАЦИИ ФРАНЦИИ ====================

TOTALENERGIES = CivilCorporation(
    corp_id="civ_fr_001",
    name="TotalEnergies SE",
    country="Франция",
    city="Курбевуа",
    description="Многонациональная энергетическая компания, производит нефть, газ и электроэнергию.",
    specialization=["oil", "gas_supply", "energy_equipment"],
    founded=1924,
    website="www.totalenergies.com",
    products={
        "oil": {"name": "Нефтепродукты", "type": "oil", "price": 510, "description": "Топливо"},
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 830, "description": "Газ"},
        "energy_equipment": {"name": "Энергооборудование", "type": "energy_equipment", "price": 48000, "description": "Оборудование для энергетики"}
    }
)

LVMH = CivilCorporation(
    corp_id="civ_fr_002",
    name="LVMH Moët Hennessy Louis Vuitton",
    country="Франция",
    city="Париж",
    description="Крупнейший в мире производитель предметов роскоши.",
    specialization=["clothing", "footwear", "cosmetics", "beverages"],
    founded=1987,
    website="www.lvmh.com",
    products={
        "clothing": {"name": "Louis Vuitton, Dior", "type": "clothing", "price": 2000, "description": "Дизайнерская одежда"},
        "footwear": {"name": "Обувь", "type": "footwear", "price": 800, "description": "Брендовая обувь"},
        "cosmetics": {"name": "Christian Dior, Guerlain", "type": "cosmetics", "price": 300, "description": "Парфюмерия"},
        "beverages": {"name": "Moët & Chandon", "type": "beverages", "price": 100, "description": "Шампанское"}
    }
)

SANOFI = CivilCorporation(
    corp_id="civ_fr_003",
    name="Sanofi S.A.",
    country="Франция",
    city="Париж",
    description="Глобальная фармацевтическая компания, производитель лекарств и вакцин.",
    specialization=["pharmaceuticals", "medical_supplies"],
    founded=1973,
    website="www.sanofi.com",
    products={
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 650, "description": "Рецептурные препараты"},
        "medical_supplies": {"name": "Медицинские изделия", "type": "medical_supplies", "price": 180, "description": "Средства ухода"}
    }
)

ORANGE = CivilCorporation(
    corp_id="civ_fr_004",
    name="Orange S.A.",
    country="Франция",
    city="Париж",
    description="Крупнейший оператор мобильной и фиксированной связи во Франции.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1988,
    website="www.orange.com",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 45, "description": "Сотовые тарифы"},
        "telecom_services": {"name": "Домашний телефон", "type": "telecom_services", "price": 30, "description": "Фиксированная связь"},
        "internet_services": {"name": "Orange Internet", "type": "internet_services", "price": 40, "description": "Домашний интернет"}
    }
)

RENAULT = CivilCorporation(
    corp_id="civ_fr_005",
    name="Renault Group",
    country="Франция",
    city="Булонь-Бийанкур",
    description="Крупный французский автопроизводитель, входит в альянс Renault-Nissan.",
    specialization=["cars", "trucks", "auto_parts"],
    founded=1899,
    website="www.renaultgroup.com",
    products={
        "cars": {"name": "Renault", "type": "cars", "price": 25000, "description": "Легковые автомобили"},
        "trucks": {"name": "Renault Trucks", "type": "trucks", "price": 55000, "description": "Грузовики"},
        "auto_parts": {"name": "Запчасти", "type": "auto_parts", "price": 3000, "description": "Оригинальные запчасти"}
    }
)

PEUGEOT = CivilCorporation(
    corp_id="civ_fr_005b",
    name="Peugeot S.A.",
    country="Франция",
    city="Париж",
    description="Старейший французский автопроизводитель, часть концерна Stellantis.",
    specialization=["cars", "auto_parts"],
    founded=1882,
    website="www.peugeot.com",
    products={
        "cars": {"name": "Peugeot", "type": "cars", "price": 23000, "description": "Легковые автомобили"},
        "auto_parts": {"name": "Запчасти", "type": "auto_parts", "price": 2800, "description": "Оригинальные запчасти"}
    }
)

AIRBUS = CivilCorporation(
    corp_id="civ_fr_006",
    name="Airbus SE",
    country="Франция",
    city="Тулуза",
    description="Европейский авиастроительный концерн, главный конкурент Boeing.",
    specialization=["aerospace_equipment", "drones"],
    founded=1970,
    website="www.airbus.com",
    products={
        "aerospace_equipment": {"name": "Гражданские самолеты", "type": "aerospace_equipment", "price": 90000000, "description": "Airbus A320, A350"},
        "drones": {"name": "Беспилотники", "type": "drones", "price": 8000000, "description": "Военные и гражданские дроны"}
    }
)

CARREFOUR = CivilCorporation(
    corp_id="civ_fr_007",
    name="Carrefour S.A.",
    country="Франция",
    city="Масси",
    description="Крупнейшая сеть гипермаркетов в Европе.",
    specialization=["retail", "supermarkets", "ecommerce"],
    founded=1959,
    website="www.carrefour.com",
    products={
        "retail": {"name": "Гипермаркеты", "type": "retail", "price": 0, "description": "Товары"},
        "supermarkets": {"name": "Carrefour Market", "type": "supermarkets", "price": 0, "description": "Продуктовые магазины"},
        "ecommerce": {"name": "Carrefour Livraison", "type": "ecommerce", "price": 0, "description": "Онлайн-доставка"}
    }
)

BNP_PARIBAS = CivilCorporation(
    corp_id="civ_fr_008",
    name="BNP Paribas",
    country="Франция",
    city="Париж",
    description="Крупнейший банк Франции и один из крупнейших в Европе.",
    specialization=["banking", "investments", "insurance"],
    founded=2000,
    website="www.bnpparibas.com",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиционный банкинг", "type": "investments", "price": 1300, "description": "Управление капиталом"},
        "insurance": {"name": "Страхование", "type": "insurance", "price": 700, "description": "Страховые продукты"}
    }
)

SOCIETE_GENERALE = CivilCorporation(
    corp_id="civ_fr_008b",
    name="Société Générale S.A.",
    country="Франция",
    city="Париж",
    description="Один из крупнейших банков Франции.",
    specialization=["banking", "investments"],
    founded=1864,
    website="www.societegenerale.com",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 1100, "description": "Управление активами"}
    }
)

AXA = CivilCorporation(
    corp_id="civ_fr_009",
    name="AXA S.A.",
    country="Франция",
    city="Париж",
    description="Крупнейшая страховая группа в мире.",
    specialization=["insurance", "investments"],
    founded=1985,
    website="www.axa.com",
    products={
        "insurance": {"name": "Страхование", "type": "insurance", "price": 900, "description": "Страхование жизни и имущества"},
        "investments": {"name": "Управление активами", "type": "investments", "price": 1000, "description": "Инвестиционные продукты"}
    }
)

DANONE = CivilCorporation(
    corp_id="civ_fr_010",
    name="Danone S.A.",
    country="Франция",
    city="Париж",
    description="Мировой лидер в производстве молочных продуктов и воды.",
    specialization=["food_products", "beverages"],
    founded=1919,
    website="www.danone.com",
    products={
        "food_products": {"name": "Молочные продукты", "type": "food_products", "price": 120, "description": "Йогурты, творог"},
        "beverages": {"name": "Вода", "type": "beverages", "price": 20, "description": "Evian, Volvic"}
    }
)

HERMES = CivilCorporation(
    corp_id="civ_fr_011",
    name="Hermès International",
    country="Франция",
    city="Париж",
    description="Производитель предметов роскоши, особенно известный своими сумками и шелковыми платками.",
    specialization=["clothing", "footwear", "cosmetics"],
    founded=1837,
    website="www.hermes.com",
    products={
        "clothing": {"name": "Одежда", "type": "clothing", "price": 3000, "description": "Дизайнерская одежда"},
        "footwear": {"name": "Обувь", "type": "footwear", "price": 1500, "description": "Брендовая обувь"},
        "cosmetics": {"name": "Парфюмерия", "type": "cosmetics", "price": 400, "description": "Духи"}
    }
)


# ==================== КОРПОРАЦИИ УКРАИНЫ ====================

# Авіабудування
ANTONOV = CivilCorporation(
    corp_id="civ_ua_001",
    name="ДП «Антонов»",
    country="Україна",
    city="Київ",
    description="Всесвітньо відоме авіабудівне підприємство, виробник транспортних літаків Ан-124 «Руслан», Ан-225 «Мрія», Ан-148, Ан-158, Ан-178.",
    specialization=["aerospace_equipment", "drones"],
    founded=1946,
    website="www.antonov.com",
    products={
        "aerospace_equipment": {
            "name": "Ан-124 «Руслан», Ан-148, Ан-178",
            "type": "aerospace_equipment",
            "price": 80000000,
            "description": "Транспортні літаки"
        },
        "drones": {
            "name": "Безпілотники",
            "type": "drones",
            "price": 2000000,
            "description": "Розвідувальні БПЛА"
        }
    }
)

# Важке машинобудування
NOVOKRAMATORSK = CivilCorporation(
    corp_id="civ_ua_002",
    name="Новокраматорський машинобудівний завод",
    country="Україна",
    city="Краматорськ",
    description="Найбільший виробник важкого промислового обладнання в Україні.",
    specialization=["industrial_equipment", "construction_machinery"],
    founded=1934,
    website="www.nkmz.com",
    products={
        "industrial_equipment": {
            "name": "Прокатні стани",
            "type": "industrial_equipment",
            "price": 5000000,
            "description": "Обладнання для металургії"
        },
        "construction_machinery": {
            "name": "Крокуючі екскаватори",
            "type": "construction_machinery",
            "price": 3000000,
            "description": "Гірничодобувна техніка"
        }
    }
)

# Сільгосптехніка
UKRAVTOZAPCHAST = CivilCorporation(
    corp_id="civ_ua_003",
    name="Украгрозапчастина",
    country="Україна",
    city="Київ",
    description="Великий виробник сільськогосподарської техніки та запчастин.",
    specialization=["agricultural_machinery", "auto_parts"],
    founded=1991,
    website="www.ukravto.ua",
    products={
        "agricultural_machinery": {
            "name": "Сівалки, культиватори",
            "type": "agricultural_machinery",
            "price": 50000,
            "description": "Сільгосптехніка"
        },
        "auto_parts": {
            "name": "Запчастини",
            "type": "auto_parts",
            "price": 5000,
            "description": "Оригінальні запчастини"
        }
    }
)

# Енергетика
TURBOATOM = CivilCorporation(
    corp_id="civ_ua_004",
    name="Турбоатом",
    country="Україна",
    city="Харків",
    description="Виробник турбінного обладнання для електростанцій.",
    specialization=["energy_equipment"],
    founded=1934,
    website="www.turboatom.com.ua",
    products={
        "energy_equipment": {
            "name": "Парові та гідравлічні турбіни",
            "type": "energy_equipment",
            "price": 10000000,
            "description": "Турбіни для ТЕС, ГЕС, АЕС"
        }
    }
)

# Автомобілебудування
ZAZ = CivilCorporation(
    corp_id="civ_ua_005",
    name="Запорізький автомобілебудівний завод",
    country="Україна",
    city="Запоріжжя",
    description="Виробник легкових та комерційних автомобілів.",
    specialization=["cars", "auto_parts"],
    founded=1863,
    website="www.zaz.ua",
    products={
        "cars": {
            "name": "ZAZ Lanos, ZAZ Sens",
            "type": "cars",
            "price": 8000,
            "description": "Легкові автомобілі"
        },
        "auto_parts": {
            "name": "Автозапчастини",
            "type": "auto_parts",
            "price": 1500,
            "description": "Оригінальні запчастини"
        }
    }
)

# Продукти харчування
KERNEL = CivilCorporation(
    corp_id="civ_ua_006",
    name="Kernel",
    country="Україна",
    city="Київ",
    description="Найбільший виробник та експортер соняшникової олії в Україні.",
    specialization=["food_products"],
    founded=1994,
    website="www.kernel.ua",
    products={
        "food_products": {
            "name": "Соняшникова олія",
            "type": "food_products",
            "price": 100,
            "description": "Олія в пляшках"
        }
    }
)

# IT
EPAM = CivilCorporation(
    corp_id="civ_ua_007",
    name="EPAM Systems",
    country="Україна",
    city="Київ",
    description="Найбільша IT-компанія в Україні, розробка програмного забезпечення.",
    specialization=["software", "it_services", "cloud_services"],
    founded=1993,
    website="www.epam.com",
    products={
        "software": {
            "name": "Замовне ПЗ",
            "type": "software",
            "price": 50000,
            "description": "Розробка програмного забезпечення"
        },
        "it_services": {
            "name": "IT-консалтинг",
            "type": "it_services",
            "price": 500,
            "description": "Консультаційні послуги"
        },
        "cloud_services": {
            "name": "Хмарні рішення",
            "type": "cloud_services",
            "price": 1000,
            "description": "Розробка та підтримка хмарних сервісів"
        }
    }
)

# Рітейл
ATB = CivilCorporation(
    corp_id="civ_ua_008",
    name="АТБ-Маркет",
    country="Україна",
    city="Дніпро",
    description="Найбільша мережа супермаркетів в Україні.",
    specialization=["retail", "supermarkets"],
    founded=1993,
    website="www.atbmarket.com",
    products={
        "retail": {
            "name": "Роздрібна торгівля",
            "type": "retail",
            "price": 0,
            "description": "Товари повсякденного попиту"
        },
        "supermarkets": {
            "name": "Продукти харчування",
            "type": "supermarkets",
            "price": 0,
            "description": "Мережа супермаркетів"
        }
    }
)

# Енергетика
DTEK = CivilCorporation(
    corp_id="civ_ua_009",
    name="ДТЕК",
    country="Україна",
    city="Київ",
    description="Найбільший приватний енергетичний холдинг України.",
    specialization=["energy_equipment", "electricity"],
    founded=2005,
    website="www.dtek.com",
    products={
        "energy_equipment": {
            "name": "Енергетичне обладнання",
            "type": "energy_equipment",
            "price": 1000000,
            "description": "Обладнання для електростанцій"
        },
        "electricity": {
            "name": "Електроенергія",
            "type": "electricity",
            "price": 100,
            "description": "Постачання електроенергії"
        }
    }
)

# Телекомунікації
KYIVSTAR = CivilCorporation(
    corp_id="civ_ua_010",
    name="Київстар",
    country="Україна",
    city="Київ",
    description="Найбільший оператор мобільного зв'язку в Україні.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1994,
    website="www.kyivstar.ua",
    products={
        "mobile_services": {
            "name": "Мобільний зв'язок",
            "type": "mobile_services",
            "price": 200,
            "description": "Тарифи для населення"
        },
        "telecom_services": {
            "name": "Домашній інтернет",
            "type": "telecom_services",
            "price": 300,
            "description": "Широкосмуговий доступ"
        },
        "internet_services": {
            "name": "Корпоративний зв'язок",
            "type": "internet_services",
            "price": 2000,
            "description": "Послуги для бізнесу"
        }
    }
)

# Банки
PRIVATBANK = CivilCorporation(
    corp_id="civ_ua_011",
    name="ПриватБанк",
    country="Україна",
    city="Київ",
    description="Найбільший банк України, лідер роздрібного банкінгу.",
    specialization=["banking", "fintech"],
    founded=1992,
    website="www.privatbank.ua",
    products={
        "banking": {
            "name": "Банківські послуги",
            "type": "banking",
            "price": 0,
            "description": "Рахунки, картки, кредити"
        },
        "fintech": {
            "name": "Приват24",
            "type": "fintech",
            "price": 0,
            "description": "Мобільний банк"
        }
    }
)

# Медицина
BORYS = CivilCorporation(
    corp_id="civ_ua_012",
    name="Клініка Борис",
    country="Україна",
    city="Київ",
    description="Провідна приватна медична клініка в Україні.",
    specialization=["healthcare_services", "hospital_services"],
    founded=1994,
    website="www.borys.ua",
    products={
        "healthcare_services": {
            "name": "Медичні послуги",
            "type": "healthcare_services",
            "price": 1000,
            "description": "Консультації лікарів"
        },
        "hospital_services": {
            "name": "Стаціонарне лікування",
            "type": "hospital_services",
            "price": 5000,
            "description": "Госпіталізація"
        }
    }
)


# ==================== КОРПОРАЦИИ ИЗРАИЛЯ ====================

# Фармацевтика
TEVA = CivilCorporation(
    corp_id="civ_il_001",
    name="Teva Pharmaceuticals",
    country="Израиль",
    city="Петах-Тиква",
    description="Крупнейший производитель дженериков в мире.",
    specialization=["pharmaceuticals", "medical_supplies"],
    founded=1901,
    website="www.tevapharm.com",
    products={
        "pharmaceuticals": {
            "name": "Дженерики",
            "type": "pharmaceuticals",
            "price": 400,
            "description": "Недорогие аналоги лекарств"
        },
        "medical_supplies": {
            "name": "Медицинские изделия",
            "type": "medical_supplies",
            "price": 200,
            "description": "Расходные материалы"
        }
    }
)

# Кибербезопасность
CHECK_POINT = CivilCorporation(
    corp_id="civ_il_002",
    name="Check Point Software",
    country="Израиль",
    city="Тель-Авив",
    description="Мировой лидер в производстве оборудования для кибербезопасности.",
    specialization=["tech_equipment", "cybersecurity", "software"],
    founded=1993,
    website="www.checkpoint.com",
    products={
        "tech_equipment": {
            "name": "Межсетевые экраны",
            "type": "tech_equipment",
            "price": 10000,
            "description": "Аппаратные решения безопасности"
        },
        "cybersecurity": {
            "name": "Защита от кибератак",
            "type": "cybersecurity",
            "price": 5000,
            "description": "Программные комплексы"
        },
        "software": {
            "name": "ПО безопасности",
            "type": "software",
            "price": 2000,
            "description": "Лицензии на софт"
        }
    }
)

# Авиапром
ISRAEL_AEROSPACE = CivilCorporation(
    corp_id="civ_il_003",
    name="Israel Aerospace Industries",
    country="Израиль",
    city="Лод",
    description="Крупнейший производитель аэрокосмической техники в Израиле.",
    specialization=["aerospace_equipment", "drones"],
    founded=1953,
    website="www.iai.co.il",
    products={
        "aerospace_equipment": {
            "name": "Бизнес-джеты",
            "type": "aerospace_equipment",
            "price": 30000000,
            "description": "Модернизация самолетов"
        },
        "drones": {
            "name": "Разведывательные БПЛА",
            "type": "drones",
            "price": 5000000,
            "description": "Беспилотники"
        }
    }
)

# Агротех
NETAFIM = CivilCorporation(
    corp_id="civ_il_004",
    name="Netafim",
    country="Израиль",
    city="Тель-Авив",
    description="Пионер и мировой лидер в производстве систем капельного орошения.",
    specialization=["agricultural_machinery", "industrial_equipment"],
    founded=1965,
    website="www.netafim.com",
    products={
        "agricultural_machinery": {
            "name": "Капельное орошение",
            "type": "agricultural_machinery",
            "price": 5000,
            "description": "Системы полива"
        },
        "industrial_equipment": {
            "name": "Промышленные системы",
            "type": "industrial_equipment",
            "price": 20000,
            "description": "Оборудование для теплиц"
        }
    }
)

# Медицина
PHILIPS_ISRAEL = CivilCorporation(
    corp_id="civ_il_005",
    name="Philips Israel",
    country="Израиль",
    city="Хайфа",
    description="Производитель медицинского оборудования и решений для здравоохранения.",
    specialization=["medical_equipment"],
    founded=1948,
    website="www.philips.co.il",
    products={
        "medical_equipment": {
            "name": "Диагностическое оборудование",
            "type": "medical_equipment",
            "price": 80000,
            "description": "МРТ, КТ, УЗИ"
        }
    }
)

# IT
WIX = CivilCorporation(
    corp_id="civ_il_006",
    name="Wix.com",
    country="Израиль",
    city="Тель-Авив",
    description="Платформа для создания сайтов, одна из крупнейших в мире.",
    specialization=["software", "cloud_services", "it_services"],
    founded=2006,
    website="www.wix.com",
    products={
        "software": {
            "name": "Конструктор сайтов",
            "type": "software",
            "price": 200,
            "description": "Годовые подписки"
        },
        "cloud_services": {
            "name": "Хостинг",
            "type": "cloud_services",
            "price": 100,
            "description": "Размещение сайтов"
        },
        "it_services": {
            "name": "Шаблоны и поддержка",
            "type": "it_services",
            "price": 50,
            "description": "Техподдержка"
        }
    }
)

# Автомобили
MOBILEYE = CivilCorporation(
    corp_id="civ_il_007",
    name="Mobileye",
    country="Израиль",
    city="Иерусалим",
    description="Разработчик систем автономного вождения и технологий для автомобилей.",
    specialization=["auto_parts", "software", "tech_equipment"],
    founded=1999,
    website="www.mobileye.com",
    products={
        "auto_parts": {
            "name": "Системы помощи водителю",
            "type": "auto_parts",
            "price": 1000,
            "description": "Камеры и сенсоры"
        },
        "software": {
            "name": "ПО для автономного вождения",
            "type": "software",
            "price": 5000,
            "description": "Лицензии"
        },
        "tech_equipment": {
            "name": "Процессоры для авто",
            "type": "tech_equipment",
            "price": 500,
            "description": "Оборудование"
        }
    }
)

# Финансы
ISRAEL_DISCOUNT = CivilCorporation(
    corp_id="civ_il_008",
    name="Israel Discount Bank",
    country="Израиль",
    city="Тель-Авив",
    description="Один из крупнейших банков Израиля.",
    specialization=["banking", "investments"],
    founded=1935,
    website="www.discountbank.co.il",
    products={
        "banking": {
            "name": "Банковские услуги",
            "type": "banking",
            "price": 0,
            "description": "Счета, кредиты"
        },
        "investments": {
            "name": "Инвестиционные продукты",
            "type": "investments",
            "price": 500,
            "description": "Управление капиталом"
        }
    }
)

# Ритейл
SHUFERSAL = CivilCorporation(
    corp_id="civ_il_009",
    name="שופרסל (Shufersal)",
    country="Израиль",
    city="Ришон-ле-Цион",
    description="Крупнейшая сеть супермаркетов в Израиле.",
    specialization=["retail", "supermarkets", "food_products"],
    founded=1958,
    website="www.shufersal.co.il",
    products={
        "retail": {
            "name": "Розничная торговля",
            "type": "retail",
            "price": 0,
            "description": "Товары повседневного спроса"
        },
        "supermarkets": {
            "name": "Продуктовые магазины",
            "type": "supermarkets",
            "price": 0,
            "description": "Сеть супермаркетов"
        },
        "food_products": {
            "name": "Продукты питания",
            "type": "food_products",
            "price": 50,
            "description": "Собственные бренды"
        }
    }
)


# ==================== КОРПОРАЦИИ ИРАНА ====================

# Автомобилестроение
IRAN_KHODRO = CivilCorporation(
    corp_id="civ_ir_001",
    name="Iran Khodro",
    country="Иран",
    city="Тегеран",
    description="Крупнейший автопроизводитель Ирана, выпускает автомобили Samand, Dena.",
    specialization=["cars", "trucks", "auto_parts"],
    founded=1962,
    website="www.ikco.ir",
    products={
        "cars": {
            "name": "Samand, Dena",
            "type": "cars",
            "price": 15000,
            "description": "Легковые автомобили"
        },
        "trucks": {
            "name": "Грузовики и пикапы",
            "type": "trucks",
            "price": 30000,
            "description": "Коммерческий транспорт"
        },
        "auto_parts": {
            "name": "Автозапчасти",
            "type": "auto_parts",
            "price": 2000,
            "description": "Оригинальные запчасти"
        }
    }
)

SAIPA = CivilCorporation(
    corp_id="civ_ir_001b",
    name="SAIPA",
    country="Иран",
    city="Тегеран",
    description="Второй по величине автопроизводитель Ирана.",
    specialization=["cars", "auto_parts"],
    founded=1966,
    website="www.saipa.com",
    products={
        "cars": {
            "name": "Pride, Tiba",
            "type": "cars",
            "price": 12000,
            "description": "Недорогие автомобили"
        },
        "auto_parts": {
            "name": "Запчасти",
            "type": "auto_parts",
            "price": 1500,
            "description": "Комплектующие"
        }
    }
)

# Нефтегазовое оборудование
SADRA = CivilCorporation(
    corp_id="civ_ir_002",
    name="Sadra",
    country="Иран",
    city="Тегеран",
    description="Крупнейший производитель нефтегазового оборудования и морских платформ в Иране.",
    specialization=["industrial_equipment", "energy_equipment"],
    founded=1968,
    website="www.sadra.ir",
    products={
        "industrial_equipment": {
            "name": "Буровые установки",
            "type": "industrial_equipment",
            "price": 500000,
            "description": "Оборудование для бурения"
        },
        "energy_equipment": {
            "name": "Нефтяные платформы",
            "type": "energy_equipment",
            "price": 3000000,
            "description": "Морские платформы"
        }
    }
)

# Пищевая промышленность
KALLEH = CivilCorporation(
    corp_id="civ_ir_003",
    name="Kalleh",
    country="Иран",
    city="Амоль",
    description="Крупнейший производитель продуктов питания в Иране.",
    specialization=["food_products", "beverages"],
    founded=1991,
    website="www.kalleh.com",
    products={
        "food_products": {
            "name": "Мясные и молочные продукты",
            "type": "food_products",
            "price": 100,
            "description": "Колбасы, сыры, йогурты"
        },
        "beverages": {
            "name": "Напитки",
            "type": "beverages",
            "price": 50,
            "description": "Соки, газировка"
        }
    }
)

# Станкостроение
MACHINE_SAZI = CivilCorporation(
    corp_id="civ_ir_004",
    name="Machine Sazi Arak",
    country="Иран",
    city="Арак",
    description="Крупнейший производитель промышленного оборудования и станков в Иране.",
    specialization=["machine_tools", "industrial_equipment"],
    founded=1967,
    website="www.msa.ir",
    products={
        "machine_tools": {
            "name": "Токарные и фрезерные станки",
            "type": "machine_tools",
            "price": 100000,
            "description": "Металлообрабатывающие станки"
        },
        "industrial_equipment": {
            "name": "Котлы, теплообменники",
            "type": "industrial_equipment",
            "price": 200000,
            "description": "Промышленное оборудование"
        }
    }
)

# Фармацевтика
DAROU_PAKHSH = CivilCorporation(
    corp_id="civ_ir_005",
    name="Darou Pakhsh",
    country="Иран",
    city="Тегеран",
    description="Крупнейший производитель фармацевтической продукции в Иране.",
    specialization=["pharmaceuticals"],
    founded=1958,
    website="www.daroupakhsh.com",
    products={
        "pharmaceuticals": {
            "name": "Лекарственные препараты",
            "type": "pharmaceuticals",
            "price": 300,
            "description": "Рецептурные и безрецептурные лекарства"
        }
    }
)

# Телекоммуникации
TALYAI = CivilCorporation(
    corp_id="civ_ir_006",
    name="Talyaie",
    country="Иран",
    city="Тегеран",
    description="Крупнейший оператор мобильной связи в Иране.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=2005,
    website="www.talyaie.ir",
    products={
        "mobile_services": {
            "name": "Мобильная связь",
            "type": "mobile_services",
            "price": 150,
            "description": "Тарифы для населения"
        },
        "telecom_services": {
            "name": "Домашний интернет",
            "type": "telecom_services",
            "price": 200,
            "description": "Доступ в интернет"
        },
        "internet_services": {
            "name": "Корпоративная связь",
            "type": "internet_services",
            "price": 1000,
            "description": "Для бизнеса"
        }
    }
)

# IT
PISHGAMAN = CivilCorporation(
    corp_id="civ_ir_007",
    name="Pishgaman",
    country="Иран",
    city="Тегеран",
    description="Крупная IT-компания, разработчик ПО и системных решений.",
    specialization=["software", "it_services", "cloud_services"],
    founded=1998,
    website="www.pishgaman.net",
    products={
        "software": {
            "name": "Корпоративное ПО",
            "type": "software",
            "price": 10000,
            "description": "Разработка на заказ"
        },
        "it_services": {
            "name": "IT-консалтинг",
            "type": "it_services",
            "price": 300,
            "description": "Консультации"
        },
        "cloud_services": {
            "name": "Облачные услуги",
            "type": "cloud_services",
            "price": 500,
            "description": "Хостинг и облака"
        }
    }
)

# Банки
MELI_BANK = CivilCorporation(
    corp_id="civ_ir_008",
    name="Bank Melli Iran",
    country="Иран",
    city="Тегеран",
    description="Крупнейший банк Ирана, предоставляет полный спектр финансовых услуг.",
    specialization=["banking", "investments"],
    founded=1928,
    website="www.bmi.ir",
    products={
        "banking": {
            "name": "Банковские услуги",
            "type": "banking",
            "price": 0,
            "description": "Счета, кредиты"
        },
        "investments": {
            "name": "Инвестиционные продукты",
            "type": "investments",
            "price": 300,
            "description": "Управление капиталом"
        }
    }
)

# Ритейл
REFAAH = CivilCorporation(
    corp_id="civ_ir_009",
    name="Refaah",
    country="Иран",
    city="Тегеран",
    description="Крупная сеть супермаркетов и универмагов в Иране.",
    specialization=["retail", "supermarkets"],
    founded=1995,
    website="www.refaah.com",
    products={
        "retail": {
            "name": "Розничная торговля",
            "type": "retail",
            "price": 0,
            "description": "Товары народного потребления"
        },
        "supermarkets": {
            "name": "Продуктовые магазины",
            "type": "supermarkets",
            "price": 0,
            "description": "Сеть супермаркетов"
        }
    }
)

# Строительство
KAYSON = CivilCorporation(
    corp_id="civ_ir_010",
    name="Kayson",
    country="Иран",
    city="Тегеран",
    description="Крупная строительная и инжиниринговая компания.",
    specialization=["construction", "real_estate"],
    founded=1962,
    website="www.kayson.ir",
    products={
        "construction": {
            "name": "Строительные услуги",
            "type": "construction",
            "price": 1000000,
            "description": "Промышленное строительство"
        },
        "real_estate": {
            "name": "Продажа недвижимости",
            "type": "real_estate",
            "price": 500000,
            "description": "Жилая и коммерческая"
        }
    }
)
# ==================== КОРПОРАЦИИ БЕЛАРУСИ ====================

# Автомобилестроение
BELAZ = CivilCorporation(
    corp_id="civ_by_001",
    name="БелАЗ",
    country="Беларусь",
    city="Жодино",
    description="Крупнейший мировой производитель карьерных самосвалов и транспортного оборудования для горнодобывающей промышленности.",
    specialization=["industrial_equipment", "construction_machinery"],
    founded=1948,
    website="www.belaz.by",
    products={
        "industrial_equipment": {"name": "Карьерные самосвалы", "type": "industrial_equipment", "price": 2000000, "description": "Самосвалы грузоподъемностью до 450 тонн"},
        "construction_machinery": {"name": "Спецтехника", "type": "construction_machinery", "price": 800000, "description": "Бульдозеры, погрузчики"}
    }
)

MAZ = CivilCorporation(
    corp_id="civ_by_002",
    name="МАЗ (Минский автомобильный завод)",
    country="Беларусь",
    city="Минск",
    description="Крупнейший производитель грузовых автомобилей, автобусов и троллейбусов в Беларуси.",
    specialization=["trucks", "buses", "auto_parts"],
    founded=1944,
    website="www.maz.by",
    products={
        "trucks": {"name": "Грузовики МАЗ", "type": "trucks", "price": 70000, "description": "Седельные тягачи, самосвалы"},
        "buses": {"name": "Автобусы МАЗ", "type": "buses", "price": 150000, "description": "Городские и междугородние автобусы"},
        "auto_parts": {"name": "Запчасти МАЗ", "type": "auto_parts", "price": 2000, "description": "Оригинальные запчасти"}
    }
)

MTZ = CivilCorporation(
    corp_id="civ_by_003",
    name="МТЗ (Минский тракторный завод)",
    country="Беларусь",
    city="Минск",
    description="Один из крупнейших производителей сельскохозяйственной техники в мире, выпускает тракторы BELARUS.",
    specialization=["agricultural_machinery"],
    founded=1946,
    website="www.belarus-tractor.com",
    products={
        "agricultural_machinery": {"name": "Тракторы BELARUS", "type": "agricultural_machinery", "price": 50000, "description": "Колесные тракторы"}
    }
)

GOMMELMASH = CivilCorporation(
    corp_id="civ_by_003b",
    name="Гомсельмаш",
    country="Беларусь",
    city="Гомель",
    description="Крупный производитель сельскохозяйственной техники, специализируется на зерноуборочных и кормоуборочных комбайнах.",
    specialization=["agricultural_machinery"],
    founded=1930,
    website="www.gomselmash.by",
    products={
        "agricultural_machinery": {"name": "Комбайны ПАЛЕССЕ", "type": "agricultural_machinery", "price": 200000, "description": "Зерноуборочные комбайны"}
    }
)

# Продукты питания
SAVUSHKIN = CivilCorporation(
    corp_id="civ_by_004",
    name="Савушкин продукт",
    country="Беларусь",
    city="Брест",
    description="Крупнейший производитель молочной продукции в Беларуси.",
    specialization=["food_products"],
    founded=1997,
    website="www.savushkin.by",
    products={
        "food_products": {"name": "Молочная продукция", "type": "food_products", "price": 50, "description": "Молоко, сыры, йогурты"}
    }
)

SANTA_BREMOR = CivilCorporation(
    corp_id="civ_by_004b",
    name="Санта Бремор",
    country="Беларусь",
    city="Брест",
    description="Крупный производитель продуктов питания, включая мороженое, рыбные деликатесы и консервы.",
    specialization=["food_products"],
    founded=1998,
    website="www.santabremor.by",
    products={
        "food_products": {"name": "Мороженое и деликатесы", "type": "food_products", "price": 40, "description": "Мороженое, рыбная продукция"}
    }
)

SPARTAK = CivilCorporation(
    corp_id="civ_by_004c",
    name="Спартак",
    country="Беларусь",
    city="Гомель",
    description="Крупнейший производитель кондитерских изделий в Беларуси.",
    specialization=["food_products"],
    founded=1924,
    website="www.spartak.by",
    products={
        "food_products": {"name": "Кондитерские изделия", "type": "food_products", "price": 30, "description": "Шоколад, конфеты, печенье"}
    }
)

# IT
EPAM_BELARUS = CivilCorporation(
    corp_id="civ_by_005",
    name="EPAM Systems Belarus",
    country="Беларусь",
    city="Минск",
    description="Крупнейшая IT-компания в Беларуси, разработка программного обеспечения.",
    specialization=["software", "it_services", "cloud_services"],
    founded=1993,
    website="www.epam.by",
    products={
        "software": {"name": "Разработка ПО", "type": "software", "price": 50000, "description": "Заказная разработка"},
        "it_services": {"name": "IT-консалтинг", "type": "it_services", "price": 300, "description": "Консультации"},
        "cloud_services": {"name": "Облачные решения", "type": "cloud_services", "price": 800, "description": "Разработка и поддержка"}
    }
)

IBA = CivilCorporation(
    corp_id="civ_by_005b",
    name="IBA Group",
    country="Беларусь",
    city="Минск",
    description="Крупная IT-компания, специализирующаяся на разработке ПО и ИТ-услугах.",
    specialization=["software", "it_services"],
    founded=1993,
    website="www.ibagroup.eu",
    products={
        "software": {"name": "Корпоративное ПО", "type": "software", "price": 40000, "description": "Разработка на заказ"},
        "it_services": {"name": "IT-аутсорсинг", "type": "it_services", "price": 250, "description": "Поддержка и обслуживание"}
    }
)

# Телекоммуникации
VELCOM = CivilCorporation(
    corp_id="civ_by_006",
    name="Velcom (A1)",
    country="Беларусь",
    city="Минск",
    description="Один из крупнейших операторов мобильной связи в Беларуси.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1999,
    website="www.a1.by",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 15, "description": "Тарифы для населения"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 20, "description": "Доступ в интернет"},
        "internet_services": {"name": "Корпоративная связь", "type": "internet_services", "price": 100, "description": "Для бизнеса"}
    }
)

MTS_BELARUS = CivilCorporation(
    corp_id="civ_by_007",
    name="МТС Беларусь",
    country="Беларусь",
    city="Минск",
    description="Крупный оператор мобильной связи в Беларуси.",
    specialization=["mobile_services", "telecom_services"],
    founded=2002,
    website="www.mts.by",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 14, "description": "Тарифы"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 18, "description": "Интернет и ТВ"}
    }
)

BELTELECOM = CivilCorporation(
    corp_id="civ_by_007b",
    name="Белтелеком",
    country="Беларусь",
    city="Минск",
    description="Национальный оператор электросвязи Беларуси, предоставляет услуги интернета и телефонии.",
    specialization=["internet_services", "telecom_services"],
    founded=1995,
    website="www.beltelecom.by",
    products={
        "internet_services": {"name": "Интернет byfly", "type": "internet_services", "price": 16, "description": "Домашний интернет"},
        "telecom_services": {"name": "Телефония", "type": "telecom_services", "price": 8, "description": "Городская связь"}
    }
)

# Банки
BELARUSBANK = CivilCorporation(
    corp_id="civ_by_008",
    name="Беларусбанк",
    country="Беларусь",
    city="Минск",
    description="Крупнейший банк Беларуси, системно значимый кредитор.",
    specialization=["banking", "investments"],
    founded=1922,
    website="www.belarusbank.by",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты, карты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 200, "description": "Инвестиционные продукты"}
    }
)

BELAGROPROMBANK = CivilCorporation(
    corp_id="civ_by_008b",
    name="Белагропромбанк",
    country="Беларусь",
    city="Минск",
    description="Один из крупнейших банков Беларуси, специализируется на обслуживании агропромышленного комплекса.",
    specialization=["banking"],
    founded=1991,
    website="www.belapb.by",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Кредиты, депозиты"}
    }
)

# Ритейл
EUROOPT = CivilCorporation(
    corp_id="civ_by_009",
    name="Евроопт",
    country="Беларусь",
    city="Минск",
    description="Крупнейшая сеть супермаркетов в Беларуси.",
    specialization=["retail", "supermarkets"],
    founded=1995,
    website="www.euroopt.by",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Товары повседневного спроса"},
        "supermarkets": {"name": "Супермаркеты", "type": "supermarkets", "price": 0, "description": "Продуктовые магазины"}
    }
)

GREEN = CivilCorporation(
    corp_id="civ_by_009b",
    name="Green",
    country="Беларусь",
    city="Минск",
    description="Крупная сеть гипермаркетов и супермаркетов в Беларуси.",
    specialization=["retail", "supermarkets"],
    founded=2004,
    website="www.green.by",
    products={
        "retail": {"name": "Гипермаркеты", "type": "retail", "price": 0, "description": "Широкий ассортимент"},
        "supermarkets": {"name": "Продуктовые магазины", "type": "supermarkets", "price": 0, "description": "Продукты"}
    }
)

# Энергетика
BELNEFTEKHIM = CivilCorporation(
    corp_id="civ_by_010",
    name="Белнефтехим",
    country="Беларусь",
    city="Минск",
    description="Государственный концерн, объединяющий предприятия нефтехимической промышленности.",
    specialization=["oil", "chemicals", "energy_equipment"],
    founded=1991,
    website="www.belneftekhim.by",
    products={
        "oil": {"name": "Нефтепродукты", "type": "oil", "price": 400, "description": "Топливо, масла"},
        "chemicals": {"name": "Химическая продукция", "type": "chemicals", "price": 300, "description": "Полимеры, удобрения"},
        "energy_equipment": {"name": "Оборудование", "type": "energy_equipment", "price": 20000, "description": "Нефтегазовое оборудование"}
    }
)


# ==================== КОРПОРАЦИИ НОРВЕГИИ ====================

# Энергетика
EQUINOR = CivilCorporation(
    corp_id="civ_no_001",
    name="Equinor",
    country="Норвегия",
    city="Ставангер",
    description="Крупнейшая энергетическая компания Норвегии, специализируется на добыче нефти и газа.",
    specialization=["oil", "gas_supply", "energy_equipment"],
    founded=1972,
    website="www.equinor.com",
    products={
        "oil": {"name": "Нефть", "type": "oil", "price": 500, "description": "Сырая нефть"},
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 450, "description": "Газ для экспорта"},
        "energy_equipment": {"name": "Оборудование", "type": "energy_equipment", "price": 50000, "description": "Оборудование для шельфовой добычи"}
    }
)

# Морепродукты
MARINE_HARVEST = CivilCorporation(
    corp_id="civ_no_002",
    name="Marine Harvest (Mowi)",
    country="Норвегия",
    city="Берген",
    description="Крупнейший в мире производитель атлантического лосося и других морепродуктов.",
    specialization=["food_products"],
    founded=1965,
    website="www.mowi.com",
    products={
        "food_products": {"name": "Атлантический лосось", "type": "food_products", "price": 150, "description": "Свежая и замороженная рыба"}
    }
)

# Судостроение
AKER = CivilCorporation(
    corp_id="civ_no_003",
    name="Aker Solutions",
    country="Норвегия",
    city="Осло",
    description="Крупная инжиниринговая компания, специализирующаяся на оборудовании для нефтегазовой отрасли и судостроении.",
    specialization=["industrial_equipment", "energy_equipment"],
    founded=2004,
    website="www.akersolutions.com",
    products={
        "industrial_equipment": {"name": "Промышленное оборудование", "type": "industrial_equipment", "price": 100000, "description": "Оборудование для шельфа"},
        "energy_equipment": {"name": "Энергооборудование", "type": "energy_equipment", "price": 150000, "description": "Морские платформы"}
    }
)

# Телекоммуникации
TELENOR = CivilCorporation(
    corp_id="civ_no_004",
    name="Telenor",
    country="Норвегия",
    city="Осло",
    description="Крупнейший телекоммуникационный оператор Норвегии, работает в нескольких странах мира.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1855,
    website="www.telenor.com",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 40, "description": "Тарифы"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 45, "description": "Широкополосный доступ"},
        "internet_services": {"name": "Корпоративные решения", "type": "internet_services", "price": 300, "description": "B2B услуги"}
    }
)

# Банки
DNB = CivilCorporation(
    corp_id="civ_no_005",
    name="DNB",
    country="Норвегия",
    city="Осло",
    description="Крупнейшая финансовая группа Норвегии, предоставляет полный спектр банковских услуг.",
    specialization=["banking", "investments", "insurance"],
    founded=1822,
    website="www.dnb.no",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 500, "description": "Управление активами"},
        "insurance": {"name": "Страхование", "type": "insurance", "price": 400, "description": "Страховые продукты"}
    }
)

# Судоходство
WILHELMSEN = CivilCorporation(
    corp_id="civ_no_006",
    name="Wilhelmsen",
    country="Норвегия",
    city="Осло",
    description="Крупнейшая судоходная компания Норвегии, специализируется на морских перевозках и логистике.",
    specialization=["logistics", "freight", "passenger_transport"],
    founded=1861,
    website="www.wilhelmsen.com",
    products={
        "logistics": {"name": "Морская логистика", "type": "logistics", "price": 1000, "description": "Грузовые перевозки"},
        "freight": {"name": "Грузоперевозки", "type": "freight", "price": 800, "description": "Контейнерные перевозки"},
        "passenger_transport": {"name": "Пассажирские перевозки", "type": "passenger_transport", "price": 200, "description": "Круизы и паромы"}
    }
)

# Ритейл
REMA_1000 = CivilCorporation(
    corp_id="civ_no_007",
    name="Rema 1000",
    country="Норвегия",
    city="Осло",
    description="Крупная сеть продовольственных магазинов в Норвегии.",
    specialization=["retail", "supermarkets"],
    founded=1979,
    website="www.rema.no",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Продукты и товары"},
        "supermarkets": {"name": "Супермаркеты", "type": "supermarkets", "price": 0, "description": "Сеть магазинов"}
    }
)

# IT
KONGSBERG_DIGITAL = CivilCorporation(
    corp_id="civ_no_008",
    name="Kongsberg Digital",
    country="Норвегия",
    city="Конгсберг",
    description="IT-подразделение Kongsberg, специализируется на цифровых решениях для морской и энергетической отраслей.",
    specialization=["software", "it_services"],
    founded=2016,
    website="www.kongsberg.com",
    products={
        "software": {"name": "Цифровые решения", "type": "software", "price": 20000, "description": "ПО для моделирования"},
        "it_services": {"name": "IT-услуги", "type": "it_services", "price": 400, "description": "Консалтинг и поддержка"}
    }
)


# ==================== КОРПОРАЦИИ ТУРЦИИ ====================

# Автомобилестроение
TOFAS = CivilCorporation(
    corp_id="civ_tr_001",
    name="Tofaş",
    country="Турция",
    city="Бурса",
    description="Крупный производитель автомобилей, совместное предприятие с Fiat.",
    specialization=["cars", "auto_parts"],
    founded=1968,
    website="www.tofas.com.tr",
    products={
        "cars": {"name": "Автомобили Fiat/Tofaş", "type": "cars", "price": 20000, "description": "Легковые автомобили"},
        "auto_parts": {"name": "Автозапчасти", "type": "auto_parts", "price": 1500, "description": "Комплектующие"}
    }
)

FORD_OTOSAN = CivilCorporation(
    corp_id="civ_tr_001b",
    name="Ford Otosan",
    country="Турция",
    city="Коджаэли",
    description="Совместное предприятие Ford и Koç Holding, производит коммерческие автомобили.",
    specialization=["cars", "trucks"],
    founded=1959,
    website="www.fordotosan.com.tr",
    products={
        "cars": {"name": "Ford Transit", "type": "cars", "price": 30000, "description": "Коммерческие автомобили"},
        "trucks": {"name": "Грузовики Ford", "type": "trucks", "price": 50000, "description": "Тяжелые грузовики"}
    }
)

# Бытовая техника
ARCELIK = CivilCorporation(
    corp_id="civ_tr_002",
    name="Arçelik",
    country="Турция",
    city="Стамбул",
    description="Крупнейший производитель бытовой техники в Турции, владеет брендами Beko, Grundig.",
    specialization=["household_goods", "consumer_electronics"],
    founded=1955,
    website="www.arcelik.com.tr",
    products={
        "household_goods": {"name": "Бытовая техника", "type": "household_goods", "price": 500, "description": "Холодильники, стиральные машины"},
        "consumer_electronics": {"name": "Электроника", "type": "consumer_electronics", "price": 400, "description": "Телевизоры, аудиосистемы"}
    }
)

VESTEL = CivilCorporation(
    corp_id="civ_tr_002b",
    name="Vestel",
    country="Турция",
    city="Маниса",
    description="Крупный производитель электроники и бытовой техники, крупнейший производитель телевизоров в Европе.",
    specialization=["consumer_electronics", "household_goods"],
    founded=1984,
    website="www.vestel.com.tr",
    products={
        "consumer_electronics": {"name": "Телевизоры", "type": "consumer_electronics", "price": 600, "description": "LED и QLED телевизоры"},
        "household_goods": {"name": "Бытовая техника", "type": "household_goods", "price": 450, "description": "Мелкая и крупная техника"}
    }
)

# Текстиль
LCWAIKIKI = CivilCorporation(
    corp_id="civ_tr_003",
    name="LC Waikiki",
    country="Турция",
    city="Стамбул",
    description="Крупнейшая сеть магазинов одежды в Турции, производит доступную одежду.",
    specialization=["clothing", "footwear"],
    founded=1988,
    website="www.lcwaikiki.com.tr",
    products={
        "clothing": {"name": "Одежда", "type": "clothing", "price": 40, "description": "Повседневная одежда"},
        "footwear": {"name": "Обувь", "type": "footwear", "price": 50, "description": "Обувь для всей семьи"}
    }
)

MAVI = CivilCorporation(
    corp_id="civ_tr_003b",
    name="Mavi",
    country="Турция",
    city="Стамбул",
    description="Известный бренд джинсовой одежды и аксессуаров.",
    specialization=["clothing"],
    founded=1991,
    website="www.mavi.com",
    products={
        "clothing": {"name": "Джинсовая одежда", "type": "clothing", "price": 80, "description": "Джинсы, куртки"}
    }
)

# Строительство
RENAISSANCE = CivilCorporation(
    corp_id="civ_tr_004",
    name="Rönesans Holding",
    country="Турция",
    city="Анкара",
    description="Крупная международная строительная компания, реализует проекты в России, Европе и на Ближнем Востоке.",
    specialization=["construction", "real_estate"],
    founded=1993,
    website="www.ronesans.com",
    products={
        "construction": {"name": "Строительные услуги", "type": "construction", "price": 1000000, "description": "Промышленное и гражданское строительство"},
        "real_estate": {"name": "Недвижимость", "type": "real_estate", "price": 500000, "description": "Коммерческая недвижимость"}
    }
)

ENKA = CivilCorporation(
    corp_id="civ_tr_004b",
    name="Enka İnşaat",
    country="Турция",
    city="Стамбул",
    description="Одна из крупнейших строительных компаний Турции, работает на международном уровне.",
    specialization=["construction"],
    founded=1957,
    website="www.enka.com",
    products={
        "construction": {"name": "Строительство", "type": "construction", "price": 800000, "description": "Инфраструктурные проекты"}
    }
)

# Продукты питания
ULKER = CivilCorporation(
    corp_id="civ_tr_005",
    name="Ülker",
    country="Турция",
    city="Стамбул",
    description="Крупнейший производитель кондитерских изделий и продуктов питания в Турции.",
    specialization=["food_products"],
    founded=1944,
    website="www.ulker.com.tr",
    products={
        "food_products": {"name": "Кондитерские изделия", "type": "food_products", "price": 20, "description": "Печенье, шоколад"}
    }
)

ETI = CivilCorporation(
    corp_id="civ_tr_005b",
    name="Eti",
    country="Турция",
    city="Эскишехир",
    description="Крупный производитель продуктов питания, специализируется на снеках и кондитерских изделиях.",
    specialization=["food_products"],
    founded=1961,
    website="www.eti.com.tr",
    products={
        "food_products": {"name": "Снеки", "type": "food_products", "price": 15, "description": "Печенье, вафли"}
    }
)

# Банки
ISBANK = CivilCorporation(
    corp_id="civ_tr_006",
    name="İşbank",
    country="Турция",
    city="Стамбул",
    description="Крупнейший частный банк Турции, предоставляет полный спектр финансовых услуг.",
    specialization=["banking", "investments", "insurance"],
    founded=1924,
    website="www.isbank.com.tr",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 400, "description": "Управление активами"},
        "insurance": {"name": "Страхование", "type": "insurance", "price": 300, "description": "Страховые продукты"}
    }
)

GARANTI = CivilCorporation(
    corp_id="civ_tr_006b",
    name="Garanti BBVA",
    country="Турция",
    city="Стамбул",
    description="Один из крупнейших банков Турции, входит в испанскую группу BBVA.",
    specialization=["banking", "fintech"],
    founded=1946,
    website="www.garantibbva.com.tr",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Розничный банкинг"},
        "fintech": {"name": "Мобильный банк", "type": "fintech", "price": 0, "description": "Цифровые сервисы"}
    }
)

# Ритейл
BIM = CivilCorporation(
    corp_id="civ_tr_007",
    name="BİM",
    country="Турция",
    city="Стамбул",
    description="Крупнейшая сеть дискаунтеров в Турции.",
    specialization=["retail", "supermarkets"],
    founded=1995,
    website="www.bim.com.tr",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Продукты и товары"},
        "supermarkets": {"name": "Дискаунтеры", "type": "supermarkets", "price": 0, "description": "Сеть магазинов"}
    }
)

# Авиаперевозки
TURKISH_AIRLINES = CivilCorporation(
    corp_id="civ_tr_008",
    name="Turkish Airlines",
    country="Турция",
    city="Стамбул",
    description="Национальный авиаперевозчик Турции, выполняет рейсы в более чем 120 стран мира.",
    specialization=["airlines", "passenger_transport", "logistics"],
    founded=1933,
    website="www.turkishairlines.com",
    products={
        "airlines": {"name": "Авиабилеты", "type": "airlines", "price": 500, "description": "Пассажирские перевозки"},
        "passenger_transport": {"name": "Чартерные рейсы", "type": "passenger_transport", "price": 2000, "description": "Частные рейсы"},
        "logistics": {"name": "Грузовые перевозки", "type": "logistics", "price": 800, "description": "Turkish Cargo"}
    }
)


# ==================== КОРПОРАЦИИ СИРИИ ====================

# Цементная промышленность
LATTAKIA_CEMENT = CivilCorporation(
    corp_id="civ_sy_001",
    name="Lattakia Cement Company",
    country="Сирия",
    city="Латакия",
    description="Крупный производитель цемента и строительных материалов в Сирии.",
    specialization=["construction", "industrial_equipment"],
    founded=1975,
    website="",
    products={
        "construction": {"name": "Цемент", "type": "construction", "price": 100, "description": "Строительный цемент"},
        "industrial_equipment": {"name": "Оборудование", "type": "industrial_equipment", "price": 5000, "description": "Промышленное оборудование"}
    }
)

# Пищевая промышленность
SYRIAN_ARAB_COMPANY = CivilCorporation(
    corp_id="civ_sy_002",
    name="Syrian Arab Company for Food Industries",
    country="Сирия",
    city="Дамаск",
    description="Крупный производитель продуктов питания и напитков в Сирии.",
    specialization=["food_products", "beverages"],
    founded=1970,
    website="",
    products={
        "food_products": {"name": "Продукты питания", "type": "food_products", "price": 30, "description": "Консервы, макароны"},
        "beverages": {"name": "Напитки", "type": "beverages", "price": 15, "description": "Соки, газировка"}
    }
)

# Текстиль
SYRIAN_TEXTILE = CivilCorporation(
    corp_id="civ_sy_003",
    name="Syrian Textile Company",
    country="Сирия",
    city="Алеппо",
    description="Крупный производитель текстиля и готовой одежды в Сирии.",
    specialization=["clothing"],
    founded=1960,
    website="",
    products={
        "clothing": {"name": "Текстиль", "type": "clothing", "price": 20, "description": "Ткани, готовая одежда"}
    }
)

# Фармацевтика
SYRIAN_PHARM = CivilCorporation(
    corp_id="civ_sy_004",
    name="Syrian Pharmaceutical Company",
    country="Сирия",
    city="Дамаск",
    description="Крупнейший производитель лекарственных средств в Сирии.",
    specialization=["pharmaceuticals", "medical_supplies"],
    founded=1980,
    website="",
    products={
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 150, "description": "Рецептурные препараты"},
        "medical_supplies": {"name": "Медизделия", "type": "medical_supplies", "price": 50, "description": "Расходные материалы"}
    }
)


# ==================== КОРПОРАЦИИ КАНАДЫ ====================

# Авиастроение
BOMBARDIER = CivilCorporation(
    corp_id="civ_ca_001",
    name="Bombardier",
    country="Канада",
    city="Монреаль, Квебек",
    description="Крупный производитель бизнес-джетов и железнодорожной техники.",
    specialization=["aerospace_equipment", "industrial_equipment"],
    founded=1942,
    website="www.bombardier.com",
    products={
        "aerospace_equipment": {"name": "Бизнес-джеты", "type": "aerospace_equipment", "price": 25000000, "description": "Частные самолеты"},
        "industrial_equipment": {"name": "Железнодорожная техника", "type": "industrial_equipment", "price": 2000000, "description": "Поезда и вагоны"}
    }
)

# Горнодобывающая промышленность
BARRICK_GOLD = CivilCorporation(
    corp_id="civ_ca_002",
    name="Barrick Gold",
    country="Канада",
    city="Торонто, Онтарио",
    description="Крупнейшая золотодобывающая компания в мире.",
    specialization=["industrial_equipment"],
    founded=1983,
    website="www.barrick.com",
    products={
        "industrial_equipment": {"name": "Золото", "type": "industrial_equipment", "price": 60000, "description": "Золотые слитки"}
    }
)

# IT
OPEN_TEXT = CivilCorporation(
    corp_id="civ_ca_003",
    name="OpenText",
    country="Канада",
    city="Ватерлоо, Онтарио",
    description="Крупнейшая канадская IT-компания, специализируется на корпоративном ПО.",
    specialization=["software", "cloud_services", "it_services"],
    founded=1991,
    website="www.opentext.com",
    products={
        "software": {"name": "Корпоративное ПО", "type": "software", "price": 15000, "description": "Управление документами"},
        "cloud_services": {"name": "Облачные услуги", "type": "cloud_services", "price": 500, "description": "Хостинг"},
        "it_services": {"name": "IT-консалтинг", "type": "it_services", "price": 350, "description": "Поддержка"}
    }
)

SHOPIFY = CivilCorporation(
    corp_id="civ_ca_003b",
    name="Shopify",
    country="Канада",
    city="Оттава, Онтарио",
    description="Ведущая платформа для электронной коммерции.",
    specialization=["ecommerce", "software", "cloud_services"],
    founded=2006,
    website="www.shopify.com",
    products={
        "ecommerce": {"name": "Платформа для магазинов", "type": "ecommerce", "price": 30, "description": "Создание интернет-магазинов"},
        "software": {"name": "ПО для продаж", "type": "software", "price": 2000, "description": "Лицензии"},
        "cloud_services": {"name": "Облачный хостинг", "type": "cloud_services", "price": 100, "description": "Размещение магазинов"}
    }
)

# Банки
RBC = CivilCorporation(
    corp_id="civ_ca_004",
    name="Royal Bank of Canada",
    country="Канада",
    city="Торонто, Онтарио",
    description="Крупнейший банк Канады по размеру активов.",
    specialization=["banking", "investments", "insurance"],
    founded=1864,
    website="www.rbc.com",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 600, "description": "Управление капиталом"},
        "insurance": {"name": "Страхование", "type": "insurance", "price": 400, "description": "Страховые продукты"}
    }
)

TD_BANK = CivilCorporation(
    corp_id="civ_ca_004b",
    name="TD Bank Group",
    country="Канада",
    city="Торонто, Онтарио",
    description="Один из крупнейших банков Канады, работает также в США.",
    specialization=["banking", "investments"],
    founded=1955,
    website="www.td.com",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Розничный банкинг"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 500, "description": "Брокерские услуги"}
    }
)

# Энергетика
ENBRIDGE = CivilCorporation(
    corp_id="civ_ca_005",
    name="Enbridge",
    country="Канада",
    city="Калгари, Альберта",
    description="Крупнейшая энергетическая компания Канады, оператор трубопроводов.",
    specialization=["energy_equipment", "oil", "gas_supply"],
    founded=1949,
    website="www.enbridge.com",
    products={
        "energy_equipment": {"name": "Трубопроводы", "type": "energy_equipment", "price": 100000, "description": "Транспортировка нефти"},
        "oil": {"name": "Нефть", "type": "oil", "price": 450, "description": "Сырая нефть"},
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 400, "description": "Газ"}
    }
)

# Ритейл
LOBLAW = CivilCorporation(
    corp_id="civ_ca_006",
    name="Loblaw Companies",
    country="Канада",
    city="Брамптон, Онтарио",
    description="Крупнейшая сеть супермаркетов и аптек в Канаде.",
    specialization=["retail", "supermarkets", "pharmaceuticals"],
    founded=1956,
    website="www.loblaw.ca",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Продукты и товары"},
        "supermarkets": {"name": "Супермаркеты", "type": "supermarkets", "price": 0, "description": "Сеть Loblaws"},
        "pharmaceuticals": {"name": "Аптеки", "type": "pharmaceuticals", "price": 200, "description": "Лекарства"}
    }
)

# Телекоммуникации
ROGERS = CivilCorporation(
    corp_id="civ_ca_007",
    name="Rogers Communications",
    country="Канада",
    city="Торонто, Онтарио",
    description="Крупный оператор мобильной и фиксированной связи в Канаде.",
    specialization=["mobile_services", "telecom_services", "internet_services", "media"],
    founded=1960,
    website="www.rogers.com",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 60, "description": "Тарифы"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 70, "description": "Интернет"},
        "internet_services": {"name": "Корпоративные решения", "type": "internet_services", "price": 500, "description": "B2B услуги"},
        "media": {"name": "Медиа", "type": "media", "price": 30, "description": "Телевидение"}
    }
)

BELL = CivilCorporation(
    corp_id="civ_ca_007b",
    name="Bell Canada",
    country="Канада",
    city="Монреаль, Квебек",
    description="Крупнейший телекоммуникационный оператор Канады.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1880,
    website="www.bell.ca",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 65, "description": "Тарифы"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 75, "description": "Интернет"},
        "internet_services": {"name": "Корпоративная связь", "type": "internet_services", "price": 600, "description": "Для бизнеса"}
    }
)


# ==================== КОРПОРАЦИИ ПОЛЬШИ ====================

# Энергетика
PKN_ORLEN = CivilCorporation(
    corp_id="civ_pl_001",
    name="PKN Orlen",
    country="Польша",
    city="Плоцк",
    description="Крупнейшая нефтегазовая компания Польши, владеет сетью АЗС и НПЗ.",
    specialization=["oil", "gas_supply", "energy_equipment", "retail"],
    founded=1999,
    website="www.orlen.pl",
    products={
        "oil": {"name": "Нефтепродукты", "type": "oil", "price": 450, "description": "Топливо"},
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 400, "description": "Газ"},
        "energy_equipment": {"name": "Оборудование", "type": "energy_equipment", "price": 30000, "description": "Нефтегазовое оборудование"},
        "retail": {"name": "АЗС", "type": "retail", "price": 0, "description": "Сеть заправочных станций"}
    }
)

PGNIG = CivilCorporation(
    corp_id="civ_pl_001b",
    name="PGNiG",
    country="Польша",
    city="Варшава",
    description="Крупнейшая газодобывающая компания Польши.",
    specialization=["gas_supply"],
    founded=1982,
    website="www.pgnig.pl",
    products={
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 380, "description": "Добыча и поставки"}
    }
)

# Ритейл
DINO = CivilCorporation(
    corp_id="civ_pl_002",
    name="Dino Polska",
    country="Польша",
    city="Кротошин",
    description="Одна из крупнейших сетей супермаркетов в Польше.",
    specialization=["retail", "supermarkets"],
    founded=1999,
    website="www.dino.pl",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Продукты"},
        "supermarkets": {"name": "Супермаркеты", "type": "supermarkets", "price": 0, "description": "Сеть магазинов"}
    }
)

Biedronka = CivilCorporation(
    corp_id="civ_pl_002b",
    name="Biedronka",
    country="Польша",
    city="Кошалин",
    description="Крупнейшая сеть дискаунтеров в Польше, часть португальской группы Jerónimo Martins.",
    specialization=["retail", "supermarkets"],
    founded=1995,
    website="www.biedronka.pl",
    products={
        "retail": {"name": "Дискаунтеры", "type": "retail", "price": 0, "description": "Низкие цены"},
        "supermarkets": {"name": "Продукты", "type": "supermarkets", "price": 0, "description": "Продуктовые магазины"}
    }
)

# IT
CD_PROJEKT = CivilCorporation(
    corp_id="civ_pl_003",
    name="CD Projekt",
    country="Польша",
    city="Варшава",
    description="Крупнейший разработчик видеоигр в Польше, создатель серии The Witcher и Cyberpunk 2077.",
    specialization=["gaming", "software", "entertainment"],
    founded=1994,
    website="www.cdprojekt.com",
    products={
        "gaming": {"name": "Видеоигры", "type": "gaming", "price": 50, "description": "The Witcher, Cyberpunk"},
        "software": {"name": "ПО", "type": "software", "price": 30, "description": "GOG Galaxy"},
        "entertainment": {"name": "Развлечения", "type": "entertainment", "price": 40, "description": "Цифровая дистрибуция"}
    }
)

# Производство мебели
IKEA_POLAND = CivilCorporation(
    corp_id="civ_pl_004",
    name="IKEA Poland",
    country="Польша",
    city="Варшава",
    description="Крупнейший производитель мебели в Польше, часть шведской группы IKEA.",
    specialization=["furniture", "household_goods"],
    founded=1961,
    website="www.ikea.pl",
    products={
        "furniture": {"name": "Мебель", "type": "furniture", "price": 200, "description": "Мебель для дома"},
        "household_goods": {"name": "Товары для дома", "type": "household_goods", "price": 50, "description": "Аксессуары"}
    }
)

# Банки
PKO_BP = CivilCorporation(
    corp_id="civ_pl_005",
    name="PKO Bank Polski",
    country="Польша",
    city="Варшава",
    description="Крупнейший банк Польши, системно значимый кредитор.",
    specialization=["banking", "investments"],
    founded=1919,
    website="www.pkobp.pl",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 300, "description": "Управление активами"}
    }
)

# Телекоммуникации
ORANGE_POLAND = CivilCorporation(
    corp_id="civ_pl_006",
    name="Orange Polska",
    country="Польша",
    city="Варшава",
    description="Крупнейший оператор мобильной и фиксированной связи в Польше.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1991,
    website="www.orange.pl",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 30, "description": "Тарифы"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 35, "description": "Интернет и ТВ"},
        "internet_services": {"name": "Корпоративные решения", "type": "internet_services", "price": 200, "description": "B2B услуги"}
    }
)

PLAY = CivilCorporation(
    corp_id="civ_pl_006b",
    name="Play",
    country="Польша",
    city="Варшава",
    description="Крупный оператор мобильной связи в Польше.",
    specialization=["mobile_services"],
    founded=2007,
    website="www.play.pl",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 25, "description": "Тарифы"}
    }
)

# ==================== КОРПОРАЦИИ ШВЕЦИИ ====================

# Автомобилестроение
VOLVO_CARS = CivilCorporation(
    corp_id="civ_se_001",
    name="Volvo Cars",
    country="Швеция",
    city="Гётеборг",
    description="Легендарный производитель автомобилей, известный своей безопасностью.",
    specialization=["cars"],
    founded=1927,
    website="www.volvocars.com",
    products={
        "cars": {"name": "Автомобили Volvo", "type": "cars", "price": 45000, "description": "Легковые автомобили"}
    }
)

VOLVO_TRUCKS = CivilCorporation(
    corp_id="civ_se_001b",
    name="Volvo Trucks",
    country="Швеция",
    city="Гётеборг",
    description="Крупнейший производитель грузовых автомобилей в мире.",
    specialization=["trucks", "buses"],
    founded=1928,
    website="www.volvotrucks.com",
    products={
        "trucks": {"name": "Грузовики Volvo", "type": "trucks", "price": 100000, "description": "Тяжелые грузовики"},
        "buses": {"name": "Автобусы Volvo", "type": "buses", "price": 250000, "description": "Городские и туристические автобусы"}
    }
)

SCANIA = CivilCorporation(
    corp_id="civ_se_001c",
    name="Scania",
    country="Швеция",
    city="Сёдертелье",
    description="Крупный производитель грузовиков и автобусов, входит в концерн Traton.",
    specialization=["trucks", "buses"],
    founded=1891,
    website="www.scania.com",
    products={
        "trucks": {"name": "Грузовики Scania", "type": "trucks", "price": 95000, "description": "Тяжелые грузовики"},
        "buses": {"name": "Автобусы Scania", "type": "buses", "price": 230000, "description": "Шасси для автобусов"}
    }
)

# Телекоммуникации
ERICSSON = CivilCorporation(
    corp_id="civ_se_002",
    name="Ericsson",
    country="Швеция",
    city="Стокгольм",
    description="Мировой лидер в производстве телекоммуникационного оборудования.",
    specialization=["telecom_equipment", "tech_equipment", "it_services"],
    founded=1876,
    website="www.ericsson.com",
    products={
        "telecom_equipment": {"name": "Оборудование 5G", "type": "telecom_equipment", "price": 50000, "description": "Базовые станции"},
        "tech_equipment": {"name": "Сетевое оборудование", "type": "tech_equipment", "price": 20000, "description": "Маршрутизаторы"},
        "it_services": {"name": "Услуги", "type": "it_services", "price": 400, "description": "Консалтинг и поддержка"}
    }
)

# Банки
SEB = CivilCorporation(
    corp_id="civ_se_003",
    name="Skandinaviska Enskilda Banken (SEB)",
    country="Швеция",
    city="Стокгольм",
    description="Крупный банк Швеции, предоставляет полный спектр финансовых услуг.",
    specialization=["banking", "investments"],
    founded=1972,
    website="www.seb.se",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 500, "description": "Управление активами"}
    }
)

# Ритейл
H_M = CivilCorporation(
    corp_id="civ_se_004",
    name="H&M",
    country="Швеция",
    city="Стокгольм",
    description="Вторая по величине сеть магазинов одежды в мире.",
    specialization=["clothing", "footwear"],
    founded=1947,
    website="www.hm.com",
    products={
        "clothing": {"name": "Одежда", "type": "clothing", "price": 30, "description": "Модная одежда"},
        "footwear": {"name": "Обувь", "type": "footwear", "price": 40, "description": "Обувь"}
    }
)

# Мебель
IKEA = CivilCorporation(
    corp_id="civ_se_005",
    name="IKEA",
    country="Швеция",
    city="Эльмхульт",
    description="Крупнейший в мире производитель мебели и товаров для дома.",
    specialization=["furniture", "household_goods"],
    founded=1943,
    website="www.ikea.com",
    products={
        "furniture": {"name": "Мебель", "type": "furniture", "price": 150, "description": "Мебель для дома"},
        "household_goods": {"name": "Товары для дома", "type": "household_goods", "price": 30, "description": "Аксессуары"}
    }
)

# IT
SPOTIFY = CivilCorporation(
    corp_id="civ_se_006",
    name="Spotify",
    country="Швеция",
    city="Стокгольм",
    description="Крупнейший в мире стриминговый сервис для музыки и подкастов.",
    specialization=["streaming", "entertainment", "software"],
    founded=2006,
    website="www.spotify.com",
    products={
        "streaming": {"name": "Музыкальный стриминг", "type": "streaming", "price": 10, "description": "Подписка"},
        "entertainment": {"name": "Подкасты", "type": "entertainment", "price": 0, "description": "Бесплатный контент"},
        "software": {"name": "ПО", "type": "software", "price": 0, "description": "Приложения"}
    }
)
# Инжиниринг
ATLAS_COPCO = CivilCorporation(
    corp_id="civ_se_007",
    name="Atlas Copco",
    country="Швеция",
    city="Нака",
    description="Мировой лидер в производстве промышленного оборудования и компрессоров.",
    specialization=["industrial_equipment", "construction_machinery"],
    founded=1873,
    website="www.atlascopco.com",
    products={
        "industrial_equipment": {"name": "Компрессоры", "type": "industrial_equipment", "price": 50000, "description": "Промышленные компрессоры"},
        "construction_machinery": {"name": "Буровое оборудование", "type": "construction_machinery", "price": 200000, "description": "Оборудование для горных работ"}
    }
)

SANDVIK = CivilCorporation(
    corp_id="civ_se_007b",
    name="Sandvik",
    country="Швеция",
    city="Стокгольм",
    description="Крупный производитель горнодобывающего оборудования и твердосплавных материалов.",
    specialization=["industrial_equipment", "machine_tools"],
    founded=1862,
    website="www.sandvik.com",
    products={
        "industrial_equipment": {"name": "Горное оборудование", "type": "industrial_equipment", "price": 150000, "description": "Оборудование для добычи"},
        "machine_tools": {"name": "Металлообработка", "type": "machine_tools", "price": 30000, "description": "Инструменты и оснастка"}
    }
)

# Фармацевтика
ASTRAZENECA_SWEDEN = CivilCorporation(
    corp_id="civ_se_008",
    name="AstraZeneca Sweden",
    country="Швеция",
    city="Сёдертелье",
    description="Шведское подразделение глобальной фармацевтической компании.",
    specialization=["pharmaceuticals"],
    founded=1913,
    website="www.astrazeneca.se",
    products={
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 800, "description": "Рецептурные препараты"}
    }
)


# ==================== КОРПОРАЦИИ ФИНЛЯНДИИ ====================

# Телекоммуникации
NOKIA = CivilCorporation(
    corp_id="civ_fi_001",
    name="Nokia",
    country="Финляндия",
    city="Эспоо",
    description="Мировой лидер в производстве телекоммуникационного оборудования и технологий 5G.",
    specialization=["telecom_equipment", "tech_equipment", "it_services"],
    founded=1865,
    website="www.nokia.com",
    products={
        "telecom_equipment": {"name": "Оборудование 5G", "type": "telecom_equipment", "price": 60000, "description": "Базовые станции"},
        "tech_equipment": {"name": "Сетевое оборудование", "type": "tech_equipment", "price": 25000, "description": "Маршрутизаторы"},
        "it_services": {"name": "Услуги", "type": "it_services", "price": 500, "description": "Консалтинг и поддержка"}
    }
)

# Судостроение
MEYER_TURKU = CivilCorporation(
    corp_id="civ_fi_002",
    name="Meyer Turku",
    country="Финляндия",
    city="Турку",
    description="Одна из крупнейших верфей в мире, специализируется на строительстве круизных лайнеров.",
    specialization=["industrial_equipment"],
    founded=1737,
    website="www.meyerturku.fi",
    products={
        "industrial_equipment": {"name": "Круизные лайнеры", "type": "industrial_equipment", "price": 500000000, "description": "Пассажирские суда"}
    }
)

# Лесная промышленность
UPM = CivilCorporation(
    corp_id="civ_fi_003",
    name="UPM",
    country="Финляндия",
    city="Хельсинки",
    description="Крупнейшая лесопромышленная компания Финляндии, производит бумагу, целлюлозу и биотопливо.",
    specialization=["industrial_equipment", "chemicals"],
    founded=1996,
    website="www.upm.com",
    products={
        "industrial_equipment": {"name": "Бумага и целлюлоза", "type": "industrial_equipment", "price": 500, "description": "Офисная бумага"},
        "chemicals": {"name": "Биотопливо", "type": "chemicals", "price": 600, "description": "Экологичное топливо"}
    }
)

STORA_ENSO = CivilCorporation(
    corp_id="civ_fi_003b",
    name="Stora Enso",
    country="Финляндия",
    city="Хельсинки",
    description="Один из крупнейших в мире производителей бумаги и упаковки.",
    specialization=["industrial_equipment"],
    founded=1998,
    website="www.storaenso.com",
    products={
        "industrial_equipment": {"name": "Упаковка", "type": "industrial_equipment", "price": 300, "description": "Картон и упаковочные материалы"}
    }
)

# Инжиниринг
KONE = CivilCorporation(
    corp_id="civ_fi_004",
    name="KONE",
    country="Финляндия",
    city="Эспоо",
    description="Мировой лидер в производстве лифтов, эскалаторов и подъемного оборудования.",
    specialization=["industrial_equipment"],
    founded=1910,
    website="www.kone.com",
    products={
        "industrial_equipment": {"name": "Лифты", "type": "industrial_equipment", "price": 50000, "description": "Пассажирские лифты"}
    }
)

WARTSILA = CivilCorporation(
    corp_id="civ_fi_004b",
    name="Wärtsilä",
    country="Финляндия",
    city="Хельсинки",
    description="Крупный производитель двигателей и энергетического оборудования для морской отрасли.",
    specialization=["energy_equipment", "industrial_equipment"],
    founded=1834,
    website="www.wartsila.com",
    products={
        "energy_equipment": {"name": "Судовые двигатели", "type": "energy_equipment", "price": 200000, "description": "Двигатели для кораблей"},
        "industrial_equipment": {"name": "Энергоустановки", "type": "industrial_equipment", "price": 500000, "description": "Электростанции"}
    }
)

# Банки
NORDEA_FINLAND = CivilCorporation(
    corp_id="civ_fi_005",
    name="Nordea Finland",
    country="Финляндия",
    city="Хельсинки",
    description="Крупнейший банк Финляндии, входит в группу Nordea.",
    specialization=["banking", "investments"],
    founded=1820,
    website="www.nordea.fi",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 400, "description": "Управление активами"}
    }
)

# Ритейл
S_GROUP = CivilCorporation(
    corp_id="civ_fi_006",
    name="S-Group",
    country="Финляндия",
    city="Хельсинки",
    description="Крупнейшая сеть розничной торговли в Финляндии, включает супермаркеты, заправки и отели.",
    specialization=["retail", "supermarkets"],
    founded=1904,
    website="www.s-ryhma.fi",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Продукты и товары"},
        "supermarkets": {"name": "Супермаркеты", "type": "supermarkets", "price": 0, "description": "Сеть S-market, Prisma"}
    }
)


# ==================== КОРПОРАЦИИ ШВЕЙЦАРИИ ====================

# Банки
UBS = CivilCorporation(
    corp_id="civ_ch_001",
    name="UBS",
    country="Швейцария",
    city="Цюрих",
    description="Крупнейший банк Швейцарии, мировой лидер в управлении частным капиталом.",
    specialization=["banking", "investments"],
    founded=1862,
    website="www.ubs.com",
    products={
        "banking": {"name": "Private banking", "type": "banking", "price": 1000, "description": "Обслуживание состоятельных клиентов"},
        "investments": {"name": "Управление активами", "type": "investments", "price": 1500, "description": "Инвестиционные продукты"}
    }
)

CREDIT_SUISSE = CivilCorporation(
    corp_id="civ_ch_001b",
    name="Credit Suisse",
    country="Швейцария",
    city="Цюрих",
    description="Второй по величине банк Швейцарии, предоставляет полный спектр финансовых услуг.",
    specialization=["banking", "investments"],
    founded=1856,
    website="www.credit-suisse.com",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 900, "description": "Private banking"},
        "investments": {"name": "Инвестиционный банкинг", "type": "investments", "price": 1200, "description": "Управление капиталом"}
    }
)

# Страхование
ZURICH = CivilCorporation(
    corp_id="civ_ch_002",
    name="Zurich Insurance Group",
    country="Швейцария",
    city="Цюрих",
    description="Одна из крупнейших страховых компаний в мире.",
    specialization=["insurance", "investments"],
    founded=1872,
    website="www.zurich.com",
    products={
        "insurance": {"name": "Страхование", "type": "insurance", "price": 800, "description": "Страхование жизни и имущества"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 500, "description": "Управление активами"}
    }
)

SWISS_RE = CivilCorporation(
    corp_id="civ_ch_002b",
    name="Swiss Re",
    country="Швейцария",
    city="Цюрих",
    description="Один из крупнейших в мире перестраховочных компаний.",
    specialization=["insurance"],
    founded=1863,
    website="www.swissre.com",
    products={
        "insurance": {"name": "Перестрахование", "type": "insurance", "price": 2000, "description": "Страхование рисков страховых компаний"}
    }
)

# Фармацевтика
NOVARTIS = CivilCorporation(
    corp_id="civ_ch_003",
    name="Novartis",
    country="Швейцария",
    city="Базель",
    description="Одна из крупнейших фармацевтических компаний в мире.",
    specialization=["pharmaceuticals"],
    founded=1996,
    website="www.novartis.com",
    products={
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 1000, "description": "Рецептурные препараты"}
    }
)

ROCHE = CivilCorporation(
    corp_id="civ_ch_003b",
    name="Roche",
    country="Швейцария",
    city="Базель",
    description="Глобальная фармацевтическая компания, лидер в онкологии и диагностике.",
    specialization=["pharmaceuticals", "medical_equipment"],
    founded=1896,
    website="www.roche.com",
    products={
        "pharmaceuticals": {"name": "Лекарства", "type": "pharmaceuticals", "price": 1200, "description": "Онкологические препараты"},
        "medical_equipment": {"name": "Диагностика", "type": "medical_equipment", "price": 20000, "description": "Оборудование для диагностики"}
    }
)

# Продукты питания
NESTLE = CivilCorporation(
    corp_id="civ_ch_004",
    name="Nestlé",
    country="Швейцария",
    city="Веве",
    description="Крупнейший в мире производитель продуктов питания и напитков.",
    specialization=["food_products", "beverages"],
    founded=1866,
    website="www.nestle.com",
    products={
        "food_products": {"name": "Продукты питания", "type": "food_products", "price": 50, "description": "Кофе, шоколад, детское питание"},
        "beverages": {"name": "Напитки", "type": "beverages", "price": 30, "description": "Вода, соки"}
    }
)

# Часы
ROLEX = CivilCorporation(
    corp_id="civ_ch_005",
    name="Rolex",
    country="Швейцария",
    city="Женева",
    description="Легендарный производитель часов класса люкс.",
    specialization=["consumer_electronics"],
    founded=1905,
    website="www.rolex.com",
    products={
        "consumer_electronics": {"name": "Часы Rolex", "type": "consumer_electronics", "price": 8000, "description": "Престижные наручные часы"}
    }
)

OMEGA = CivilCorporation(
    corp_id="civ_ch_005b",
    name="Omega",
    country="Швейцария",
    city="Биль",
    description="Известный производитель часов, официальный хронометрист Олимпийских игр.",
    specialization=["consumer_electronics"],
    founded=1848,
    website="www.omegawatches.com",
    products={
        "consumer_electronics": {"name": "Часы Omega", "type": "consumer_electronics", "price": 5000, "description": "Наручные часы"}
    }
)

# Логистика
KUEHNE_NAGEL = CivilCorporation(
    corp_id="civ_ch_006",
    name="Kuehne + Nagel",
    country="Швейцария",
    city="Шиндельеги",
    description="Один из крупнейших в мире логистических операторов.",
    specialization=["logistics", "freight"],
    founded=1890,
    website="www.kuehne-nagel.com",
    products={
        "logistics": {"name": "Логистика", "type": "logistics", "price": 500, "description": "Транспортные услуги"},
        "freight": {"name": "Грузоперевозки", "type": "freight", "price": 600, "description": "Морские и авиаперевозки"}
    }
)


# ==================== КОРПОРАЦИИ ЕГИПТА ====================

# Телекоммуникации
ORANGE_EGYPT = CivilCorporation(
    corp_id="civ_eg_001",
    name="Orange Egypt",
    country="Египет",
    city="Каир",
    description="Крупный оператор мобильной и фиксированной связи в Египте.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=1998,
    website="www.orange.eg",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 10, "description": "Тарифы"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 15, "description": "Интернет"},
        "internet_services": {"name": "Корпоративные решения", "type": "internet_services", "price": 100, "description": "B2B услуги"}
    }
)

VODAFONE_EGYPT = CivilCorporation(
    corp_id="civ_eg_001b",
    name="Vodafone Egypt",
    country="Египет",
    city="Каир",
    description="Крупнейший оператор мобильной связи в Египте.",
    specialization=["mobile_services", "internet_services"],
    founded=1998,
    website="www.vodafone.com.eg",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 12, "description": "Тарифы"},
        "internet_services": {"name": "Домашний интернет", "type": "internet_services", "price": 14, "description": "Интернет и ТВ"}
    }
)

# Банки
NATIONAL_BANK_EGYPT = CivilCorporation(
    corp_id="civ_eg_002",
    name="National Bank of Egypt",
    country="Египет",
    city="Каир",
    description="Крупнейший банк Египта, предоставляет полный спектр финансовых услуг.",
    specialization=["banking", "investments"],
    founded=1898,
    website="www.nbe.com.eg",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 200, "description": "Управление активами"}
    }
)

BANQUE_MISR = CivilCorporation(
    corp_id="civ_eg_002b",
    name="Banque Misr",
    country="Египет",
    city="Каир",
    description="Второй по величине банк Египта, системно значимый кредитор.",
    specialization=["banking"],
    founded=1920,
    website="www.banquemisr.com",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Розничный банкинг"}
    }
)

# Строительство
ORASCOM = CivilCorporation(
    corp_id="civ_eg_003",
    name="Orascom Construction",
    country="Египет",
    city="Каир",
    description="Одна из крупнейших строительных компаний на Ближнем Востоке.",
    specialization=["construction", "real_estate"],
    founded=1950,
    website="www.orascom.com",
    products={
        "construction": {"name": "Строительные услуги", "type": "construction", "price": 500000, "description": "Инфраструктурные проекты"},
        "real_estate": {"name": "Недвижимость", "type": "real_estate", "price": 300000, "description": "Жилая и коммерческая"}
    }
)

# Цемент
SUEZ_CEMENT = CivilCorporation(
    corp_id="civ_eg_004",
    name="Suez Cement",
    country="Египет",
    city="Суэц",
    description="Крупный производитель цемента и строительных материалов в Египте.",
    specialization=["construction"],
    founded=1911,
    website="www.suezcement.com.eg",
    products={
        "construction": {"name": "Цемент", "type": "construction", "price": 80, "description": "Строительный цемент"}
    }
)

# Продукты питания
JUHANYNA = CivilCorporation(
    corp_id="civ_eg_005",
    name="Juhayna",
    country="Египет",
    city="Каир",
    description="Крупнейший производитель молочной продукции и соков в Египте.",
    specialization=["food_products", "beverages"],
    founded=1983,
    website="www.juhayna.com",
    products={
        "food_products": {"name": "Молочные продукты", "type": "food_products", "price": 20, "description": "Йогурты, молоко"},
        "beverages": {"name": "Соки", "type": "beverages", "price": 15, "description": "Фруктовые соки"}
    }
)

# Ритейл
CARREFOUR_EGYPT = CivilCorporation(
    corp_id="civ_eg_006",
    name="Carrefour Egypt",
    country="Египет",
    city="Каир",
    description="Сеть гипермаркетов и супермаркетов в Египте, часть международной сети Carrefour.",
    specialization=["retail", "supermarkets"],
    founded=2000,
    website="www.carrefouregypt.com",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Продукты и товары"},
        "supermarkets": {"name": "Гипермаркеты", "type": "supermarkets", "price": 0, "description": "Сеть магазинов"}
    }
)

# Энергетика
EGAS = CivilCorporation(
    corp_id="civ_eg_007",
    name="Egyptian Natural Gas Holding Company (EGAS)",
    country="Египет",
    city="Каир",
    description="Государственная компания по добыче и распределению природного газа.",
    specialization=["gas_supply", "energy_equipment"],
    founded=2001,
    website="www.egas.com.eg",
    products={
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 250, "description": "Газ для экспорта"},
        "energy_equipment": {"name": "Оборудование", "type": "energy_equipment", "price": 30000, "description": "Газовое оборудование"}
    }
)


# ==================== КОРПОРАЦИИ БРАЗИЛИИ ====================

# Авиастроение
EMBRAER = CivilCorporation(
    corp_id="civ_br_001",
    name="Embraer",
    country="Бразилия",
    city="Сан-Жозе-дус-Кампус",
    description="Третий по величине производитель гражданских самолетов в мире.",
    specialization=["aerospace_equipment"],
    founded=1969,
    website="www.embraer.com",
    products={
        "aerospace_equipment": {"name": "Региональные самолеты", "type": "aerospace_equipment", "price": 50000000, "description": "E-Jets"}
    }
)

# Горнодобывающая промышленность
VALE = CivilCorporation(
    corp_id="civ_br_002",
    name="Vale",
    country="Бразилия",
    city="Рио-де-Жанейро",
    description="Крупнейшая горнодобывающая компания в мире, лидер по добыче железной руды.",
    specialization=["industrial_equipment"],
    founded=1942,
    website="www.vale.com",
    products={
        "industrial_equipment": {"name": "Железная руда", "type": "industrial_equipment", "price": 100, "description": "Руда для металлургии"}
    }
)

# Нефтегазовая промышленность
PETROBRAS = CivilCorporation(
    corp_id="civ_br_003",
    name="Petrobras",
    country="Бразилия",
    city="Рио-де-Жанейро",
    description="Крупнейшая государственная нефтегазовая компания Бразилии.",
    specialization=["oil", "gas_supply", "energy_equipment"],
    founded=1953,
    website="www.petrobras.com.br",
    products={
        "oil": {"name": "Нефть", "type": "oil", "price": 450, "description": "Сырая нефть"},
        "gas_supply": {"name": "Природный газ", "type": "gas_supply", "price": 380, "description": "Газ"},
        "energy_equipment": {"name": "Оборудование", "type": "energy_equipment", "price": 40000, "description": "Нефтегазовое оборудование"}
    }
)

# Пищевая промышленность
JBS = CivilCorporation(
    corp_id="civ_br_004",
    name="JBS",
    country="Бразилия",
    city="Сан-Паулу",
    description="Крупнейший в мире производитель мяса.",
    specialization=["food_products"],
    founded=1953,
    website="www.jbs.com.br",
    products={
        "food_products": {"name": "Мясная продукция", "type": "food_products", "price": 80, "description": "Говядина, свинина, птица"}
    }
)

BRF = CivilCorporation(
    corp_id="civ_br_004b",
    name="BRF",
    country="Бразилия",
    city="Куритиба",
    description="Крупный производитель продуктов питания, владеет брендами Sadia, Perdigão.",
    specialization=["food_products"],
    founded=1934,
    website="www.brf-global.com",
    products={
        "food_products": {"name": "Замороженные продукты", "type": "food_products", "price": 60, "description": "Полуфабрикаты"}
    }
)

# Банки
ITAU = CivilCorporation(
    corp_id="civ_br_005",
    name="Itaú Unibanco",
    country="Бразилия",
    city="Сан-Паулу",
    description="Крупнейший банк Бразилии и Латинской Америки.",
    specialization=["banking", "investments", "insurance"],
    founded=2008,
    website="www.itau.com.br",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Счета, кредиты"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 400, "description": "Управление активами"},
        "insurance": {"name": "Страхование", "type": "insurance", "price": 300, "description": "Страховые продукты"}
    }
)

BRADESCO = CivilCorporation(
    corp_id="civ_br_005b",
    name="Bradesco",
    country="Бразилия",
    city="Озаску",
    description="Один из крупнейших банков Бразилии.",
    specialization=["banking", "investments"],
    founded=1943,
    website="www.bradesco.com.br",
    products={
        "banking": {"name": "Банковские услуги", "type": "banking", "price": 0, "description": "Розничный банкинг"},
        "investments": {"name": "Инвестиции", "type": "investments", "price": 350, "description": "Брокерские услуги"}
    }
)

# Ритейл
MAGAZINE_LUIZA = CivilCorporation(
    corp_id="civ_br_006",
    name="Magazine Luiza",
    country="Бразилия",
    city="Франка",
    description="Крупная сеть магазинов электроники и бытовой техники.",
    specialization=["retail", "ecommerce", "consumer_electronics"],
    founded=1957,
    website="www.magazineluiza.com.br",
    products={
        "retail": {"name": "Розничная торговля", "type": "retail", "price": 0, "description": "Электроника и техника"},
        "ecommerce": {"name": "Интернет-магазин", "type": "ecommerce", "price": 0, "description": "Онлайн-продажи"},
        "consumer_electronics": {"name": "Электроника", "type": "consumer_electronics", "price": 500, "description": "Товары"}
    }
)

# Телекоммуникации
VIVO = CivilCorporation(
    corp_id="civ_br_007",
    name="Vivo (Telefônica Brasil)",
    country="Бразилия",
    city="Сан-Паулу",
    description="Крупнейший оператор мобильной связи в Бразилии.",
    specialization=["mobile_services", "telecom_services", "internet_services"],
    founded=2003,
    website="www.vivo.com.br",
    products={
        "mobile_services": {"name": "Мобильная связь", "type": "mobile_services", "price": 25, "description": "Тарифы"},
        "telecom_services": {"name": "Домашний интернет", "type": "telecom_services", "price": 30, "description": "Интернет и ТВ"},
        "internet_services": {"name": "Корпоративные решения", "type": "internet_services", "price": 200, "description": "B2B услуги"}
    }
)

# ==================== СВОДНАЯ БАЗА ДАННЫХ ====================

ALL_CIVIL_CORPORATIONS = {
    "США": {
        "general_motors": GENERAL_MOTORS,
        "ford": FORD,
        "tesla": TESLA,
        "caterpillar": CATERPILLAR,
        "boeing": BOEING,
        "ibm": IBM,
        "microsoft": MICROSOFT,
        "apple": APPLE,
        "google": GOOGLE,
        "amazon": AMAZON,
        "johnson_johnson": JOHNSON_JOHNSON,
        "pfizer": PFIZER,
        "merck": MERCK,
        "att": AT_T,
        "verizon": VERIZON,
        "comcast": COMCAST,
        "jpmorgan": JPMORGAN,
        "goldman_sachs": GOLDMAN_SACHS,
        "visa": VISA,
        "mastercard": MASTERCARD,
        "walmart": WALMART,
        "costco": COSTCO,
        "target": TARGET,
        "mcdonalds": MCDONALDS,
        "starbucks": STARBUCKS,
        "yum_brands": YUM_BRANDS,
        "john_deere": JOHN_DEERE,
        "pepsico": PEPSICO,
        "coca_cola": COCA_COLA,
        "ge": GE,
        "delta": DELTA_AIR,
        "american_airlines": AMERICAN_AIR,
        "united": UNITED_AIR,
        "ups": UPS,
        "fedex": FEDEX,
        "disney": WALT_DISNEY,
        "netflix": NETFLIX,
        "warner": WARNER_BROS,
        "chegg": CHEGG,
        "coursera": COURSERA
    },
    "Россия": {
        "avtovaz": AVTOVAZ,
        "gaz": GAZ,
        "kamaz": KAMAZ,
        "mts": MTS,
        "megafon": MEGAFON,
        "beeline": BEELINE,
        "yandex": YANDEX,
        "vk": VK,
        "kaspersky": KASPERSKY,
        "sberbank": SBERBANK,
        "vtb": VTB,
        "tinkoff": TINKOFF,
        "magnit": MAGNIT,
        "x5": X5_GROUP,
        "wildberries": WILDBERRIES,
        "ozon": OZON,
        "gazprom": GAZPROM,
        "rosneft": ROSNEFT,
        "lukoil": LUKOIL,
        "rosatom": ROSATOM,
        "rostselmash": ROSTSELMASH,
        "power_machines": POWER_MACHINES,
        "uac": UAC,
        "rusagro": RUSAGRO,
        "pharmstandard": PHARMSTANDARD,
        "uralkali": URALKALI,
        "rzd": RZD,
        "rosven": ROSVEN,
        "medsi": MEDSI,
        "pik": PIK
    },
    "Китай": {
        "saic": SAIC,
        "byd": BYD,
        "huawei": HUAWEI,
        "xiaomi": XIAOMI,
        "lenovo": LENOVO,
        "tencent": TENCENT,
        "alibaba": ALIBABA,
        "baidu": BAIDU,
        "china_mobile": CHINA_MOBILE,
        "china_telecom": CHINA_TELECOM,
        "sany": SANY,
        "goldwind": GOLDWIND,
        "crrc": CRRC,
        "texhong": TEXHONG,
        "dji": DJI,
        "icbc": ICBC,
        "ping_an": PING_AN,
        "jd": JD_COM,
        "cnpc": CNPC,
        "state_grid": STATE_GRID
    },
    "Германия": {
        "volkswagen": VOLKSWAGEN,
        "bmw": BMW,
        "mercedes": MERCEDES,
        "siemens": SIEMENS,
        "basf": BASF,
        "trumpf": TRUMPF,
        "bayer": BAYER,
        "sap": SAP,
        "deutsche_telekom": DEUTSCHE_TELEKOM,
        "allianz": ALLIANZ,
        "deutsche_bank": DEUTSCHE_BANK,
        "adidas": ADIDAS,
        "puma": PUMA,
        "lufthansa": LUFTHANSA,
        "dhl": DHL,
        "bosch": BOSCH
    },
    "Великобритания": {
        "bp": BP,
        "shell": SHELL,
        "vodafone": VODAFONE,
        "bt": BT_GROUP,
        "gsk": GLAXOSMITHKLINE,
        "astrazeneca": ASTRAZENECA,
        "hsbc": HSBC,
        "barclays": BARCLAYS,
        "lloyds": LLOYDS,
        "unilever": UNILEVER,
        "bat": BRITISH_AMERICAN_TOBACCO,
        "rolls_royce": ROLLS_ROYCE,
        "bae": BAE_SYSTEMS,
        "tesco": TESCO,
        "sainsbury": SAINSBURY
    },
    "Франция": {
        "total": TOTALENERGIES,
        "lvmh": LVMH,
        "sanofi": SANOFI,
        "orange": ORANGE,
        "renault": RENAULT,
        "peugeot": PEUGEOT,
        "airbus": AIRBUS,
        "carrefour": CARREFOUR,
        "bnp": BNP_PARIBAS,
        "societe_generale": SOCIETE_GENERALE,
        "axa": AXA,
        "danone": DANONE,
        "hermes": HERMES
    },
    "Украина": {
        "antonov": ANTONOV,
        "novokramatorsk": NOVOKRAMATORSK,
        "ukravto": UKRAVTOZAPCHAST,
        "turboatom": TURBOATOM,
        "zaz": ZAZ,
        "kernel": KERNEL,
        "epam": EPAM,
        "atb": ATB,
        "dtek": DTEK,
        "kyivstar": KYIVSTAR,
        "privatbank": PRIVATBANK,
        "borys": BORYS
    },
    "Израиль": {
        "teva": TEVA,
        "checkpoint": CHECK_POINT,
        "iai": ISRAEL_AEROSPACE,
        "netafim": NETAFIM,
        "philips_israel": PHILIPS_ISRAEL,
        "wix": WIX,
        "mobileye": MOBILEYE,
        "israel_discount": ISRAEL_DISCOUNT,
        "shufersal": SHUFERSAL
    },
    "Иран": {
        "iran_khodro": IRAN_KHODRO,
        "saipa": SAIPA,
        "sadra": SADRA,
        "kalleh": KALLEH,
        "machine_sazi": MACHINE_SAZI,
        "darou_pakhsh": DAROU_PAKHSH,
        "talyaie": TALYAI,
        "pishgaman": PISHGAMAN,
        "meli_bank": MELI_BANK,
        "refaah": REFAAH,
        "kayson": KAYSON
    },
    # ============ НОВЫЕ СТРАНЫ ============
    "Беларусь": {
        "belaz": BELAZ,
        "maz": MAZ,
        "mtz": MTZ,
        "gomselmash": GOMMELMASH,
        "savushkin": SAVUSHKIN,
        "santa_bremor": SANTA_BREMOR,
        "spartak": SPARTAK,
        "epam_by": EPAM_BELARUS,
        "iba": IBA,
        "velcom": VELCOM,
        "mts_by": MTS_BELARUS,
        "beltelecom": BELTELECOM,
        "belarusbank": BELARUSBANK,
        "belagroprombank": BELAGROPROMBANK,
        "euroopt": EUROOPT,
        "green": GREEN,
        "belneftekhim": BELNEFTEKHIM
    },
    "Норвегия": {
        "equinor": EQUINOR,
        "marine_harvest": MARINE_HARVEST,
        "aker": AKER,
        "telenor": TELENOR,
        "dnb": DNB,
        "wilhelmsen": WILHELMSEN,
        "rema_1000": REMA_1000,
        "kongsberg_digital": KONGSBERG_DIGITAL
    },
    "Турция": {
        "tofas": TOFAS,
        "ford_otosan": FORD_OTOSAN,
        "arcelik": ARCELIK,
        "vestel": VESTEL,
        "lcwaikiki": LCWAIKIKI,
        "mavi": MAVI,
        "ronesans": RENAISSANCE,
        "enka": ENKA,
        "ulker": ULKER,
        "eti": ETI,
        "isbank": ISBANK,
        "garanti": GARANTI,
        "bim": BIM,
        "turkish_airlines": TURKISH_AIRLINES
    },
    "Сирия": {
        "lattakia_cement": LATTAKIA_CEMENT,
        "syrian_food": SYRIAN_ARAB_COMPANY,
        "syrian_textile": SYRIAN_TEXTILE,
        "syrian_pharm": SYRIAN_PHARM
    },
    "Канада": {
        "bombardier": BOMBARDIER,
        "barrick_gold": BARRICK_GOLD,
        "opentext": OPEN_TEXT,
        "shopify": SHOPIFY,
        "rbc": RBC,
        "td_bank": TD_BANK,
        "enbridge": ENBRIDGE,
        "loblaw": LOBLAW,
        "rogers": ROGERS,
        "bell": BELL
    },
    "Польша": {
        "pkn_orlen": PKN_ORLEN,
        "pgnig": PGNIG,
        "dino": DINO,
        "biedronka": Biedronka,
        "cd_projekt": CD_PROJEKT,
        "ikea_poland": IKEA_POLAND,
        "pko_bp": PKO_BP,
        "orange_poland": ORANGE_POLAND,
        "play": PLAY
    },
    "Бразилия": {
        "embraer": EMBRAER,
        "vale": VALE,
        "petrobras": PETROBRAS,
        "jbs": JBS,
        "brf": BRF,
        "itau": ITAU,
        "bradesco": BRADESCO,
        "magazine_luiza": MAGAZINE_LUIZA,
        "vivo": VIVO
    },
    "Швеция": {
        "volvo_trucks": VOLVO_TRUCKS,
        "scania": SCANIA,
        "ericsson": ERICSSON,
        "seb": SEB,
        "hm": H_M,
        "ikea": IKEA,
        "spotify": SPOTIFY,
        "atlas_copco": ATLAS_COPCO,
        "sandvik": SANDVIK,
        "astrazeneca_sweden": ASTRAZENECA_SWEDEN
    },
    "Финляндия": {
        "nokia": NOKIA,
        "meyer_turku": MEYER_TURKU,
        "upm": UPM,
        "stora_enso": STORA_ENSO,
        "kone": KONE,
        "wartsila": WARTSILA,
        "nordea_finland": NORDEA_FINLAND,
        "s_group": S_GROUP
    },
    "Швейцария": {
        "ubs": UBS,
        "credit_suisse": CREDIT_SUISSE,
        "zurich": ZURICH,
        "swiss_re": SWISS_RE,
        "novartis": NOVARTIS,
        "roche": ROCHE,
        "nestle": NESTLE,
        "rolex": ROLEX,
        "omega": OMEGA,
        "kuehne_nagel": KUEHNE_NAGEL
    },
    "Египет": {
        "orange_egypt": ORANGE_EGYPT,
        "vodafone_egypt": VODAFONE_EGYPT,
        "nbe": NATIONAL_BANK_EGYPT,
        "banque_misr": BANQUE_MISR,
        "orascom": ORASCOM,
        "suez_cement": SUEZ_CEMENT,
        "juhayna": JUHANYNA,
        "carrefour_egypt": CARREFOUR_EGYPT,
        "egas": EGAS
    }
}

# Словарь для быстрого поиска корпорации по ID
CIVIL_CORPORATIONS_BY_ID = {}
for country, corps in ALL_CIVIL_CORPORATIONS.items():
    for corp_id, corp in corps.items():
        CIVIL_CORPORATIONS_BY_ID[corp.id] = corp

# Словарь для быстрого поиска по специализации
CIVIL_CORPORATIONS_BY_SPECIALIZATION = {}
for country, corps in ALL_CIVIL_CORPORATIONS.items():
    for corp_id, corp in corps.items():
        for spec in corp.specialization:
            if spec not in CIVIL_CORPORATIONS_BY_SPECIALIZATION:
                CIVIL_CORPORATIONS_BY_SPECIALIZATION[spec] = []
            CIVIL_CORPORATIONS_BY_SPECIALIZATION[spec].append(corp)


def get_civil_corporations_by_country(country_name):
    """Получить все гражданские корпорации страны"""
    return ALL_CIVIL_CORPORATIONS.get(country_name, {})


def get_civil_corporation(corp_id):
    """Получить гражданскую корпорацию по ID"""
    return CIVIL_CORPORATIONS_BY_ID.get(corp_id)


def get_civil_corporations_by_specialization(specialization):
    """Получить все гражданские корпорации с указанной специализацией"""
    return CIVIL_CORPORATIONS_BY_SPECIALIZATION.get(specialization, [])


def get_all_civil_corporations():
    """Получить все гражданские корпорации"""
    result = []
    for corps in ALL_CIVIL_CORPORATIONS.values():
        result.extend(corps.values())
    return result


# ==================== ЭКСПОРТ ====================

__all__ = [
    'CivilCorporation',
    'get_civil_corporations_by_country',
    'get_civil_corporation',
    'get_civil_corporations_by_specialization',
    'get_all_civil_corporations',
    'CIVIL_PRODUCT_NAMES',
    'ALL_CIVIL_CORPORATIONS',
    'load_corporations_state',
    'save_corporations_state',
    'initialize_corporation_state',
    'initialize_all_corporations'
]


# ==================== ИНИЦИАЛИЗАЦИЯ ====================

# Инициализируем корпорации при запуске (только если файл не существует или force=True)
if __name__ != "__main__":
    # При импорте модуля проверяем, нужно ли инициализировать
    state = load_corporations_state()
    if not state["corporations"]:
        print("🏭 Первый запуск: инициализация корпораций с реальными данными...")
        initialize_all_corporations(force=True)
    else:
        print(f"🏭 Загружено {len(state['corporations'])} корпораций из файла")

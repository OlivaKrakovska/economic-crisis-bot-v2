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
    def __init__(self, id, name, country, city, description, specialization, products, 
                 founded=None, website=None, service_type="manufacturing"):
        self.id = id
        self.name = name
        self.country = country
        self.city = city
        self.description = description
        self.specialization = specialization  # Список типов продукции/услуг
        self.products = products  # Продукты (ключ: тип продукции)
        self.founded = founded
        self.website = website
        self.service_type = service_type  # "manufacturing", "telecom", "it", "finance", "retail", "healthcare"
        
        # ✅ ДИНАМИЧЕСКИЕ ПОЛЯ (будут сохраняться в отдельном файле)
        self.inventory = {}  # Запасы продукции {product_type: количество}
        self.budget = 0      # Деньги корпорации
        self.popularity = 50 # Популярность среди населения (0-100)
        self.market_share = {}  # Доля рынка по продуктам {product_type: процент}
        self.employees = 0   # Количество сотрудников
        self.last_update = str(datetime.now())
    
    def get_product(self, product_key):
        return self.products.get(product_key)
    
    def get_all_products(self):
        return list(self.products.values())
    
    def has_specialization(self, spec):
        return spec in self.specialization
    
    def add_to_inventory(self, product_type, quantity):
        """Добавить продукцию на склад"""
        if product_type not in self.inventory:
            self.inventory[product_type] = 0
        self.inventory[product_type] += quantity
    
    def remove_from_inventory(self, product_type, quantity):
        """Списать продукцию со склада (для продажи населению)"""
        if product_type in self.inventory and self.inventory[product_type] >= quantity:
            self.inventory[product_type] -= quantity
            return True
        return False
    
    def get_product_price(self, product_type):
        """Получить цену продукта"""
        if product_type in self.products:
            return self.products[product_type]['price']
        return 0
    
    def get_available_quantity(self, product_type):
        """Получить доступное количество продукта на складе"""
        return self.inventory.get(product_type, 0)
    
    def to_dict(self):
        """Сериализация для сохранения"""
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
    
    @classmethod
    def from_dict(cls, data):
        """Десериализация из словаря"""
        corp = cls(
            data["id"], data["name"], data["country"], data["city"],
            data["description"], data["specialization"], data["products"],
            data.get("founded"), data.get("website"), data.get("service_type", "manufacturing")
        )
        corp.inventory = data.get("inventory", {})
        corp.budget = data.get("budget", 0)
        corp.popularity = data.get("popularity", 50)
        corp.market_share = data.get("market_share", {})
        corp.employees = data.get("employees", 0)
        corp.last_update = data.get("last_update", str(datetime.now()))
        return corp


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
                corporations[corp_id] = CivilCorporation.from_dict(corp_data)
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
    id="civ_us_001",
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
    id="civ_us_001b",
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
    id="civ_us_001c",
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
    id="civ_us_002",
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
    id="civ_us_003",
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
    id="civ_us_004",
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
    id="civ_us_004b",
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
    id="civ_us_004c",
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
    id="civ_us_004d",
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
    id="civ_us_004e",
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
    id="civ_us_005",
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
    id="civ_us_005b",
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
    id="civ_us_005c",
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
    id="civ_us_006",
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
    id="civ_us_006b",
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
    id="civ_us_006c",
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
    id="civ_us_007",
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
    id="civ_us_007b",
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
    id="civ_us_007c",
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
    id="civ_us_007d",
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
    id="civ_us_008",
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
    id="civ_us_008b",
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
    id="civ_us_008c",
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
    id="civ_us_009",
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
    id="civ_us_009b",
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
    id="civ_us_009c",
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
    id="civ_us_010",
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
    id="civ_us_011",
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
    id="civ_us_011b",
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
    id="civ_us_012",
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
    id="civ_us_013",
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
    id="civ_us_013b",
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
    id="civ_us_013c",
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
    id="civ_us_014",
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
    id="civ_us_014b",
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
    id="civ_us_015",
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
    id="civ_us_015b",
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
    id="civ_us_015c",
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
    id="civ_us_016",
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
    id="civ_us_016b",
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
    id="civ_ru_001",
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
    id="civ_ru_001b",
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
    id="civ_ru_002",
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
    id="civ_ru_003",
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
    id="civ_ru_003b",
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
    id="civ_ru_003c",
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
    id="civ_ru_004",
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
    id="civ_ru_004b",
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
    id="civ_ru_004c",
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
    id="civ_ru_005",
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
    id="civ_ru_005b",
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
    id="civ_ru_005c",
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
    id="civ_ru_006",
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
    id="civ_ru_006b",
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
    id="civ_ru_006c",
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
    id="civ_ru_006d",
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
    id="civ_ru_007",
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
    id="civ_ru_007b",
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
    id="civ_ru_007c",
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
    id="civ_ru_007d",
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
    id="civ_ru_008",
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
    id="civ_ru_009",
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
    id="civ_ru_010",
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
    id="civ_ru_011",
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
    id="civ_ru_012",
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
    id="civ_ru_013",
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
    id="civ_ru_014",
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
    id="civ_ru_015",
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
    id="civ_ru_016",
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
    id="civ_ru_017",
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
    id="civ_cn_001",
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
    id="civ_cn_001b",
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
    id="civ_cn_002",
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
    id="civ_cn_007",
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
    id="civ_cn_002b",
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
    id="civ_cn_002c",
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
    id="civ_cn_002d",
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
    id="civ_cn_002e",
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
    id="civ_cn_003",
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
    id="civ_cn_003b",
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
    id="civ_cn_004",
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
    id="civ_cn_005",
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
    id="civ_cn_006",
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
    id="civ_cn_007",
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
    id="civ_cn_008",
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
    id="civ_cn_009",
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
    id="civ_cn_009b",
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
    id="civ_cn_010",
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
    id="civ_cn_011",
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
    id="civ_cn_011b",
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
    id="civ_de_001",
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
    id="civ_de_002",
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
    id="civ_de_003",
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
    id="civ_de_004",
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
    id="civ_de_005",
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
    id="civ_de_006",
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
    id="civ_de_007",
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
    id="civ_de_008",
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
    id="civ_de_009",
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
    id="civ_de_010",
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
    id="civ_de_011",
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
    id="civ_de_012",
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
    id="civ_de_012b",
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
    id="civ_de_013",
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
    id="civ_de_014",
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
    id="civ_de_015",
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
    id="civ_uk_001",
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
    id="civ_uk_001b",
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
    id="civ_uk_002",
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
    id="civ_uk_002b",
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
    id="civ_uk_003",
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
    id="civ_uk_003b",
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
    id="civ_uk_004",
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
    id="civ_uk_004b",
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
    id="civ_uk_004c",
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
    id="civ_uk_005",
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
    id="civ_uk_006",
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
    id="civ_uk_007",
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
    id="civ_uk_008",
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
    id="civ_uk_009",
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
    id="civ_uk_009b",
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
    id="civ_fr_001",
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
    id="civ_fr_002",
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
    id="civ_fr_003",
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
    id="civ_fr_004",
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
    id="civ_fr_005",
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
    id="civ_fr_005b",
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
    id="civ_fr_006",
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
    id="civ_fr_007",
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
    id="civ_fr_008",
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
    id="civ_fr_008b",
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
    id="civ_fr_009",
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
    id="civ_fr_010",
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
    id="civ_fr_011",
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
    id="civ_ua_001",
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
    id="civ_ua_002",
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
    id="civ_ua_003",
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
    id="civ_ua_004",
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
    id="civ_ua_005",
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
    id="civ_ua_006",
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
    id="civ_ua_007",
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
    id="civ_ua_008",
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
    id="civ_ua_009",
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
    id="civ_ua_010",
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
    id="civ_ua_011",
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
    id="civ_ua_012",
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
    id="civ_il_001",
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
    id="civ_il_002",
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
    id="civ_il_003",
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
    id="civ_il_004",
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
    id="civ_il_005",
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
    id="civ_il_006",
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
    id="civ_il_007",
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
    id="civ_il_008",
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
    id="civ_il_009",
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
    id="civ_ir_001",
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
    id="civ_ir_001b",
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
    id="civ_ir_002",
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
    id="civ_ir_003",
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
    id="civ_ir_004",
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
    id="civ_ir_005",
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
    id="civ_ir_006",
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
    id="civ_ir_007",
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
    id="civ_ir_008",
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
    id="civ_ir_009",
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
    id="civ_ir_010",
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

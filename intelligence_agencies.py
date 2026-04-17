# intelligence_agencies.py - База данных разведывательных агентств по странам
# ПОЛНОСТЬЮ ОБНОВЛЕНО: добавлены все новые государства (Беларусь, Норвегия,
# Великобритания, Франция, Япония, КНДР, Турция, Сирия, Канада, Польша,
# Бразилия, Швеция, Финляндия, Швейцария, Египет)

class IntelligenceAgency:
    """Класс, представляющий разведывательное агентство"""
    
    def __init__(self, id, name, country, description, founded, 
                 specialization, budget_multiplier=1.0, 
                 influence=30, corruption=20, 
                 personnel_base=1000, equipment_base=50):
        self.id = id
        self.name = name
        self.country = country
        self.description = description
        self.founded = founded
        self.specialization = specialization  # ["foreign", "counterintelligence", "cyber", "military", etc.]
        
        # Стартовые значения
        self.budget_multiplier = budget_multiplier  # множитель от госбюджета
        self.influence = influence  # влияние в государстве (0-100)
        self.corruption = corruption  # коррумпированность (0-100)
        
        # Персонал
        self.personnel_base = personnel_base  # базовая численность
        self.equipment_base = equipment_base  # базовая оснащённость
        
        # Динамические поля
        self.current_funding = 0
        self.total_personnel = 0
        self.available_personnel = 0
        self.equipment_level = 0
        self.operations_completed = 0
        self.operations_failed = 0
        self.personnel_lost = 0
    
    def to_dict(self):
        """Сериализация для сохранения"""
        return {
            "id": self.id,
            "name": self.name,
            "country": self.country,
            "description": self.description,
            "founded": self.founded,
            "specialization": self.specialization,
            "budget_multiplier": self.budget_multiplier,
            "influence": self.influence,
            "corruption": self.corruption,
            "personnel_base": self.personnel_base,
            "equipment_base": self.equipment_base,
            "current_funding": self.current_funding,
            "total_personnel": self.total_personnel,
            "available_personnel": self.available_personnel,
            "equipment_level": self.equipment_level,
            "operations_completed": self.operations_completed,
            "operations_failed": self.operations_failed,
            "personnel_lost": self.personnel_lost
        }
    
    @classmethod
    def from_dict(cls, data):
        """Десериализация из словаря"""
        agency = cls(
            data["id"], data["name"], data["country"], data["description"],
            data["founded"], data["specialization"], 
            data.get("budget_multiplier", 1.0),
            data.get("influence", 30), data.get("corruption", 20),
            data.get("personnel_base", 1000), data.get("equipment_base", 50)
        )
        agency.current_funding = data.get("current_funding", 0)
        agency.total_personnel = data.get("total_personnel", 0)
        agency.available_personnel = data.get("available_personnel", 0)
        agency.equipment_level = data.get("equipment_level", 0)
        agency.operations_completed = data.get("operations_completed", 0)
        agency.operations_failed = data.get("operations_failed", 0)
        agency.personnel_lost = data.get("personnel_lost", 0)
        return agency


# ==================== СУЩЕСТВУЮЩИЕ АГЕНТСТВА ====================

# США
CIA = IntelligenceAgency(
    id="us_int_001",
    name="Центральное разведывательное управление (CIA)",
    country="США",
    description="**CIA** - основное разведывательное агентство США, отвечающее за сбор и анализ информации о иностранных правительствах, корпорациях и отдельных лицах, а также за проведение тайных операций.",
    founded=1947,
    specialization=["foreign", "covert_ops", "analysis"],
    budget_multiplier=2.5,
    influence=45,
    corruption=15,
    personnel_base=20000,
    equipment_base=95
)

NSA = IntelligenceAgency(
    id="us_int_002",
    name="Агентство национальной безопасности (NSA)",
    country="США",
    description="**NSA** - разведывательное агентство США, специализирующееся на радиоэлектронной разведке и защите информационных систем правительства США.",
    founded=1952,
    specialization=["signals_intelligence", "cyber", "cryptography"],
    budget_multiplier=2.3,
    influence=40,
    corruption=12,
    personnel_base=30000,
    equipment_base=98
)

FBI = IntelligenceAgency(
    id="us_int_003",
    name="Федеральное бюро расследований (FBI)",
    country="США",
    description="**FBI** - федеральное правоохранительное и разведывательное агентство США, занимающееся контрразведкой и внутренней безопасностью.",
    founded=1908,
    specialization=["counterintelligence", "law_enforcement", "domestic"],
    budget_multiplier=1.8,
    influence=50,
    corruption=10,
    personnel_base=35000,
    equipment_base=90
)

DIA = IntelligenceAgency(
    id="us_int_004",
    name="Разведывательное управление Министерства обороны (DIA)",
    country="США",
    description="**DIA** - военная разведка США, обеспечивающая сбор и анализ военной информации для Министерства обороны.",
    founded=1961,
    specialization=["military_intelligence", "defense", "analysis"],
    budget_multiplier=1.9,
    influence=35,
    corruption=14,
    personnel_base=16000,
    equipment_base=92
)

# Россия
FSB = IntelligenceAgency(
    id="ru_int_001",
    name="Федеральная служба безопасности (ФСБ)",
    country="Россия",
    description="**ФСБ** - федеральный орган исполнительной власти России, осуществляющий контрразведывательную деятельность и борьбу с терроризмом.",
    founded=1995,
    specialization=["counterintelligence", "domestic", "border_security"],
    budget_multiplier=1.7,
    influence=65,
    corruption=45,
    personnel_base=40000,
    equipment_base=75
)

SVR = IntelligenceAgency(
    id="ru_int_002",
    name="Служба внешней разведки (СВР)",
    country="Россия",
    description="**СВР** - орган внешней разведки России, занимающийся сбором информации за рубежом политическими и военными методами.",
    founded=1991,
    specialization=["foreign", "human_intelligence", "covert_ops"],
    budget_multiplier=1.5,
    influence=55,
    corruption=40,
    personnel_base=15000,
    equipment_base=70
)

GRU = IntelligenceAgency(
    id="ru_int_003",
    name="Главное разведывательное управление (ГРУ)",
    country="Россия",
    description="**ГРУ** - орган военной разведки России, специализирующийся на сборе военной информации и проведении специальных операций.",
    founded=1918,
    specialization=["military_intelligence", "special_ops", "signals_intelligence"],
    budget_multiplier=1.6,
    influence=60,
    corruption=50,
    personnel_base=25000,
    equipment_base=72
)

FSO = IntelligenceAgency(
    id="ru_int_004",
    name="Федеральная служба охраны (ФСО)",
    country="Россия",
    description="**ФСО** - федеральный орган охраны, обеспечивающий безопасность высших должностных лиц и специальную связь.",
    founded=1996,
    specialization=["protection", "communications", "security"],
    budget_multiplier=1.2,
    influence=70,
    corruption=55,
    personnel_base=20000,
    equipment_base=68
)

# Китай
MSS = IntelligenceAgency(
    id="cn_int_001",
    name="Министерство государственной безопасности (MSS)",
    country="Китай",
    description="**MSS** - главное разведывательное и контрразведывательное ведомство Китая, отвечающее за внешнюю и внутреннюю безопасность.",
    founded=1983,
    specialization=["foreign", "counterintelligence", "domestic", "cyber"],
    budget_multiplier=2.0,
    influence=80,
    corruption=60,
    personnel_base=100000,
    equipment_base=80
)

PLA_Intel = IntelligenceAgency(
    id="cn_int_002",
    name="Разведывательное управление НОАК",
    country="Китай",
    description="**Разведывательное управление Народно-освободительной армии Китая** - военная разведка, занимающаяся сбором военной информации и технологическим шпионажем.",
    founded=1950,
    specialization=["military_intelligence", "tech_intelligence", "signals_intelligence"],
    budget_multiplier=1.8,
    influence=70,
    corruption=55,
    personnel_base=50000,
    equipment_base=75
)

# Германия
BND = IntelligenceAgency(
    id="de_int_001",
    name="Федеральная разведывательная служба (BND)",
    country="Германия",
    description="**BND** - внешняя разведка Германии, собирающая информацию о политических, экономических и военных процессах за рубежом.",
    founded=1956,
    specialization=["foreign", "analysis", "signals_intelligence"],
    budget_multiplier=1.3,
    influence=30,
    corruption=10,
    personnel_base=6500,
    equipment_base=85
)

BfV = IntelligenceAgency(
    id="de_int_002",
    name="Федеральное ведомство по охране конституции (BfV)",
    country="Германия",
    description="**BfV** - служба внутренней разведки Германии, занимающаяся наблюдением за экстремистскими организациями и контрразведкой.",
    founded=1950,
    specialization=["counterintelligence", "domestic", "extremism"],
    budget_multiplier=0.9,
    influence=25,
    corruption=12,
    personnel_base=3000,
    equipment_base=75
)

MAD = IntelligenceAgency(
    id="de_int_003",
    name="Служба военной контрразведки (MAD)",
    country="Германия",
    description="**MAD** - служба военной контрразведки Германии, обеспечивающая безопасность бундесвера.",
    founded=1956,
    specialization=["military_counterintelligence", "security"],
    budget_multiplier=0.7,
    influence=20,
    corruption=8,
    personnel_base=1200,
    equipment_base=70
)

# Великобритания
MI6 = IntelligenceAgency(
    id="uk_int_001",
    name="Секретная разведывательная служба (MI6)",
    country="Великобритания",
    description="**MI6** - внешняя разведка Великобритании, занимающаяся сбором информации за рубежом и проведением тайных операций.",
    founded=1909,
    specialization=["foreign", "covert_ops", "human_intelligence"],
    budget_multiplier=1.4,
    influence=35,
    corruption=10,
    personnel_base=3500,
    equipment_base=88
)

MI5 = IntelligenceAgency(
    id="uk_int_002",
    name="Служба безопасности (MI5)",
    country="Великобритания",
    description="**MI5** - служба внутренней разведки Великобритании, отвечающая за контрразведку и внутреннюю безопасность.",
    founded=1909,
    specialization=["counterintelligence", "domestic", "terrorism"],
    budget_multiplier=1.1,
    influence=30,
    corruption=8,
    personnel_base=4000,
    equipment_base=85
)

GCHQ = IntelligenceAgency(
    id="uk_int_003",
    name="Центр правительственной связи (GCHQ)",
    country="Великобритания",
    description="**GCHQ** - разведывательное агентство Великобритании, специализирующееся на радиоэлектронной разведке и кибербезопасности.",
    founded=1919,
    specialization=["signals_intelligence", "cyber", "cryptography"],
    budget_multiplier=1.3,
    influence=28,
    corruption=7,
    personnel_base=6000,
    equipment_base=92
)

# Франция
DGSE = IntelligenceAgency(
    id="fr_int_001",
    name="Главное управление внешней безопасности (DGSE)",
    country="Франция",
    description="**DGSE** - внешняя разведка Франции, занимающаяся сбором информации за рубежом и проведением специальных операций.",
    founded=1982,
    specialization=["foreign", "covert_ops", "signals_intelligence"],
    budget_multiplier=1.2,
    influence=32,
    corruption=15,
    personnel_base=5000,
    equipment_base=82
)

DGSI = IntelligenceAgency(
    id="fr_int_002",
    name="Главное управление внутренней безопасности (DGSI)",
    country="Франция",
    description="**DGSI** - служба внутренней разведки Франции, отвечающая за контрразведку и борьбу с терроризмом.",
    founded=2014,
    specialization=["counterintelligence", "domestic", "terrorism"],
    budget_multiplier=1.0,
    influence=28,
    corruption=12,
    personnel_base=4000,
    equipment_base=78
)

DRM = IntelligenceAgency(
    id="fr_int_003",
    name="Управление военной разведки (DRM)",
    country="Франция",
    description="**DRM** - военная разведка Франции, занимающаяся сбором и анализом военной информации.",
    founded=1992,
    specialization=["military_intelligence", "analysis"],
    budget_multiplier=0.8,
    influence=20,
    corruption=10,
    personnel_base=2000,
    equipment_base=75
)

# Украина
SBU = IntelligenceAgency(
    id="ua_int_001",
    name="Служба безпеки України (СБУ)",
    country="Украина",
    description="**СБУ** - главный орган государственной безопасности Украины, отвечающий за контрразведку, борьбу с терроризмом и защиту государственной тайны.",
    founded=1991,
    specialization=["counterintelligence", "domestic", "anti_corruption"],
    budget_multiplier=0.6,
    influence=45,
    corruption=55,
    personnel_base=27000,
    equipment_base=50
)

GUR = IntelligenceAgency(
    id="ua_int_002",
    name="Головне управління розвідки (ГУР)",
    country="Украина",
    description="**ГУР** - военная разведка Украины, занимающаяся сбором информации за рубежом и проведением специальных операций.",
    founded=1992,
    specialization=["military_intelligence", "foreign", "special_ops"],
    budget_multiplier=0.7,
    influence=40,
    corruption=45,
    personnel_base=5000,
    equipment_base=55
)

# Япония
PSIA = IntelligenceAgency(
    id="jp_int_001",
    name="Агентство общественной безопасности (PSIA)",
    country="Япония",
    description="**PSIA** - служба внутренней разведки Японии, занимающаяся контрразведкой и наблюдением за экстремистскими группами.",
    founded=1952,
    specialization=["counterintelligence", "domestic"],
    budget_multiplier=0.8,
    influence=25,
    corruption=8,
    personnel_base=2000,
    equipment_base=70
)

DIH = IntelligenceAgency(
    id="jp_int_002",
    name="Разведывательное управление штаба обороны (DIH)",
    country="Япония",
    description="**DIH** - военная разведка Японии, занимающаяся сбором и анализом военной информации.",
    founded=1997,
    specialization=["military_intelligence", "analysis"],
    budget_multiplier=0.7,
    influence=20,
    corruption=5,
    personnel_base=1500,
    equipment_base=72
)

CIRO = IntelligenceAgency(
    id="jp_int_003",
    name="Кабинетная разведывательная служба (CIRO)",
    country="Япония",
    description="**CIRO** - центральная разведывательная служба Японии, координирующая деятельность разведывательных органов.",
    founded=1956,
    specialization=["coordination", "analysis"],
    budget_multiplier=0.5,
    influence=18,
    corruption=5,
    personnel_base=500,
    equipment_base=65
)

# Иран
MOIS = IntelligenceAgency(
    id="ir_int_001",
    name="Министерство разведки (MOIS)",
    country="Иран",
    description="**MOIS** - главное разведывательное ведомство Ирана, занимающееся внешней разведкой, контрразведкой и внутренней безопасностью.",
    founded=1983,
    specialization=["foreign", "counterintelligence", "domestic"],
    budget_multiplier=1.1,
    influence=70,
    corruption=70,
    personnel_base=15000,
    equipment_base=45
)

IRGC_Intel = IntelligenceAgency(
    id="ir_int_002",
    name="Разведывательное управление КСИР",
    country="Иран",
    description="**Разведывательное управление Корпуса стражей исламской революции** - военная разведка, занимающаяся внешними операциями и поддержкой союзных группировок.",
    founded=1980,
    specialization=["military_intelligence", "foreign_ops", "covert_ops"],
    budget_multiplier=1.2,
    influence=75,
    corruption=75,
    personnel_base=10000,
    equipment_base=40
)

# Израиль
MOSSAD = IntelligenceAgency(
    id="il_int_mossad",
    name="Моссад",
    country="Израиль",
    description="Моссад - политическая разведка Израиля, одна из самых эффективных разведок мира. Занимается внешней разведкой и специальными операциями.",
    founded=1949,
    specialization=["foreign", "covert_ops", "assassination"],
    budget_multiplier=1.8,
    influence=65,
    corruption=12,
    personnel_base=7000,
    equipment_base=95
)

SHABAK = IntelligenceAgency(
    id="il_int_shabak",
    name="Шабак (SHABAK)",
    country="Израиль",
    description="Общая служба безопасности Израиля - контрразведка и внутренняя безопасность. Известна также как Шин-Бет.",
    founded=1948,
    specialization=["counterintelligence", "domestic", "anti_terror"],
    budget_multiplier=1.4,
    influence=60,
    corruption=10,
    personnel_base=5000,
    equipment_base=90
)

AMAN = IntelligenceAgency(
    id="il_int_aman",
    name="АМАН",
    country="Израиль",
    description="Военная разведка Израиля, отвечает за сбор информации о военных силах противника и стратегическое планирование.",
    founded=1950,
    specialization=["military_intelligence", "strategic", "analysis"],
    budget_multiplier=1.5,
    influence=55,
    corruption=8,
    personnel_base=8000,
    equipment_base=92
)

# ==================== НОВЫЕ АГЕНТСТВА ====================

# Беларусь
KGB_BELARUS = IntelligenceAgency(
    id="by_int_001",
    name="Комитет государственной безопасности (КГБ)",
    country="Беларусь",
    description="**КГБ** - спецслужба Беларуси, занимающаяся разведкой, контрразведкой и борьбой с организованной преступностью. Является преемником советского КГБ и сохраняет тесные связи с российскими спецслужбами.",
    founded=1991,
    specialization=["counterintelligence", "domestic", "foreign", "border_security"],
    budget_multiplier=0.5,
    influence=80,
    corruption=70,
    personnel_base=12000,
    equipment_base=35
)

# Норвегия
NIS = IntelligenceAgency(
    id="no_int_001",
    name="Норвежская разведывательная служба (NIS)",
    country="Норвегия",
    description="**NIS** - внешняя разведка Норвегии, занимающаяся сбором информации о политических, военных и экономических процессах. Тесно сотрудничает с разведками стран НАТО.",
    founded=1947,
    specialization=["foreign", "signals_intelligence", "military_intelligence"],
    budget_multiplier=0.6,
    influence=20,
    corruption=5,
    personnel_base=1000,
    equipment_base=75
)

PST = IntelligenceAgency(
    id="no_int_002",
    name="Полицейская служба безопасности (PST)",
    country="Норвегия",
    description="**PST** - служба внутренней разведки Норвегии, отвечающая за контрразведку и борьбу с терроризмом.",
    founded=1937,
    specialization=["counterintelligence", "domestic", "terrorism"],
    budget_multiplier=0.4,
    influence=15,
    corruption=3,
    personnel_base=500,
    equipment_base=70
)

# КНДР
RGB = IntelligenceAgency(
    id="kp_int_001",
    name="Разведывательное бюро Генерального штаба (RGB)",
    country="КНДР",
    description="**RGB** - главное разведывательное управление Корейской народной армии. Занимается внешней разведкой, специальными операциями и кибервойной.",
    founded=1948,
    specialization=["military_intelligence", "foreign", "covert_ops", "cyber"],
    budget_multiplier=0.8,
    influence=90,
    corruption=80,
    personnel_base=6000,
    equipment_base=30
)

MSS_KP = IntelligenceAgency(
    id="kp_int_002",
    name="Министерство государственной безопасности (MSS)",
    country="КНДР",
    description="**MSS** - главный орган внутренней безопасности КНДР, занимающийся контрразведкой, политическим контролем и борьбой с диссидентами.",
    founded=1973,
    specialization=["counterintelligence", "domestic", "political_control"],
    budget_multiplier=0.7,
    influence=95,
    corruption=85,
    personnel_base=30000,
    equipment_base=25
)

# Турция
MIT = IntelligenceAgency(
    id="tr_int_001",
    name="Национальная разведывательная организация (MİT)",
    country="Турция",
    description="**MİT** - главное разведывательное агентство Турции, отвечающее за внешнюю и внутреннюю разведку, контрразведку и борьбу с терроризмом.",
    founded=1965,
    specialization=["foreign", "counterintelligence", "domestic", "covert_ops"],
    budget_multiplier=0.9,
    influence=70,
    corruption=50,
    personnel_base=8000,
    equipment_base=60
)

JITEM = IntelligenceAgency(
    id="tr_int_002",
    name="Жандармская разведка (JİTEM)",
    country="Турция",
    description="**JİTEM** - разведывательное подразделение турецкой жандармерии, занимающееся борьбой с терроризмом и специальными операциями.",
    founded=1987,
    specialization=["counterintelligence", "domestic", "anti_terror"],
    budget_multiplier=0.5,
    influence=50,
    corruption=60,
    personnel_base=3000,
    equipment_base=45
)

# Сирия
GSD = IntelligenceAgency(
    id="sy_int_001",
    name="Главное управление безопасности (GSD)",
    country="Сирия",
    description="**GSD** - главная служба безопасности Сирии, отвечающая за внутреннюю безопасность, контрразведку и борьбу с оппозицией.",
    founded=1971,
    specialization=["domestic", "counterintelligence", "political_control"],
    budget_multiplier=0.4,
    influence=85,
    corruption=80,
    personnel_base=15000,
    equipment_base=25
)

AIF = IntelligenceAgency(
    id="sy_int_002",
    name="Управление военной разведки (AIF)",
    country="Сирия",
    description="**AIF** - военная разведка Сирии, занимающаяся сбором информации о военных силах противника и проведением специальных операций.",
    founded=1969,
    specialization=["military_intelligence", "foreign", "covert_ops"],
    budget_multiplier=0.5,
    influence=75,
    corruption=75,
    personnel_base=10000,
    equipment_base=30
)

# Канада
CSIS = IntelligenceAgency(
    id="ca_int_001",
    name="Канадская служба разведки и безопасности (CSIS)",
    country="Канада",
    description="**CSIS** - гражданская служба разведки Канады, отвечающая за сбор информации за рубежом и контрразведку внутри страны.",
    founded=1984,
    specialization=["foreign", "counterintelligence", "domestic"],
    budget_multiplier=0.8,
    influence=30,
    corruption=8,
    personnel_base=3000,
    equipment_base=80
)

CSE = IntelligenceAgency(
    id="ca_int_002",
    name="Центр безопасности коммуникаций (CSE)",
    country="Канада",
    description="**CSE** - агентство радиоэлектронной разведки Канады, отвечающее за перехват и анализ иностранных коммуникаций, а также кибербезопасность.",
    founded=1946,
    specialization=["signals_intelligence", "cyber", "cryptography"],
    budget_multiplier=0.7,
    influence=25,
    corruption=5,
    personnel_base=2500,
    equipment_base=85
)

# Польша
AW = IntelligenceAgency(
    id="pl_int_001",
    name="Агентство внешней разведки (AW)",
    country="Польша",
    description="**AW** - внешняя разведка Польши, занимающаяся сбором информации за рубежом и проведением специальных операций.",
    founded=2002,
    specialization=["foreign", "analysis", "covert_ops"],
    budget_multiplier=0.6,
    influence=30,
    corruption=25,
    personnel_base=2000,
    equipment_base=65
)

ABW = IntelligenceAgency(
    id="pl_int_002",
    name="Агентство внутренней безопасности (ABW)",
    country="Польша",
    description="**ABW** - служба внутренней безопасности Польши, отвечающая за контрразведку, борьбу с терроризмом и защиту государственной тайны.",
    founded=2002,
    specialization=["counterintelligence", "domestic", "terrorism"],
    budget_multiplier=0.5,
    influence=35,
    corruption=30,
    personnel_base=2500,
    equipment_base=60
)

SKW = IntelligenceAgency(
    id="pl_int_003",
    name="Военная контрразведка (SKW)",
    country="Польша",
    description="**SKW** - служба военной контрразведки Польши, обеспечивающая безопасность вооруженных сил.",
    founded=2006,
    specialization=["military_counterintelligence", "security"],
    budget_multiplier=0.4,
    influence=25,
    corruption=20,
    personnel_base=1500,
    equipment_base=55
)

# Бразилия
ABIN = IntelligenceAgency(
    id="br_int_001",
    name="Бразильское разведывательное агентство (ABIN)",
    country="Бразилия",
    description="**ABIN** - главное разведывательное агентство Бразилии, отвечающее за сбор и анализ информации о внешних и внутренних угрозах.",
    founded=1999,
    specialization=["foreign", "domestic", "analysis"],
    budget_multiplier=0.6,
    influence=40,
    corruption=45,
    personnel_base=4000,
    equipment_base=50
)

CIE = IntelligenceAgency(
    id="br_int_002",
    name="Центр армейской разведки (CIE)",
    country="Бразилия",
    description="**CIE** - военная разведка бразильской армии, занимающаяся сбором информации о военных угрозах.",
    founded=1967,
    specialization=["military_intelligence", "analysis"],
    budget_multiplier=0.4,
    influence=35,
    corruption=40,
    personnel_base=2000,
    equipment_base=45
)

# Швеция
MUST = IntelligenceAgency(
    id="se_int_001",
    name="Военная разведывательная служба (MUST)",
    country="Швеция",
    description="**MUST** - военная разведка Швеции, занимающаяся сбором информации о внешних военных угрозах и поддержкой операций.",
    founded=1994,
    specialization=["military_intelligence", "foreign", "analysis"],
    budget_multiplier=0.6,
    influence=25,
    corruption=5,
    personnel_base=1000,
    equipment_base=75
)

SAPO = IntelligenceAgency(
    id="se_int_002",
    name="Полиция безопасности (SÄPO)",
    country="Швеция",
    description="**SÄPO** - служба внутренней безопасности Швеции, отвечающая за контрразведку и борьбу с терроризмом.",
    founded=1989,
    specialization=["counterintelligence", "domestic", "terrorism"],
    budget_multiplier=0.5,
    influence=20,
    corruption=4,
    personnel_base=800,
    equipment_base=70
)

FRA = IntelligenceAgency(
    id="se_int_003",
    name="Национальное управление радиоэлектронной разведки (FRA)",
    country="Швеция",
    description="**FRA** - агентство радиоэлектронной разведки Швеции, занимающееся перехватом и анализом иностранных сигналов.",
    founded=1942,
    specialization=["signals_intelligence", "cyber", "cryptography"],
    budget_multiplier=0.5,
    influence=18,
    corruption=3,
    personnel_base=600,
    equipment_base=80
)

# Финляндия
SUPO = IntelligenceAgency(
    id="fi_int_001",
    name="Полиция безопасности (SUPO)",
    country="Финляндия",
    description="**SUPO** - служба внутренней безопасности Финляндии, отвечающая за контрразведку и борьбу с терроризмом.",
    founded=1949,
    specialization=["counterintelligence", "domestic", "terrorism"],
    budget_multiplier=0.5,
    influence=25,
    corruption=4,
    personnel_base=400,
    equipment_base=70
)

TIEDUSTELULAITOS = IntelligenceAgency(
    id="fi_int_002",
    name="Разведывательное управление (TIEDUSTELULAITOS)",
    country="Финляндия",
    description="**TIEDUSTELULAITOS** - военная разведка Финляндии, занимающаяся сбором информации о внешних военных угрозах.",
    founded=1918,
    specialization=["military_intelligence", "foreign"],
    budget_multiplier=0.4,
    influence=20,
    corruption=5,
    personnel_base=500,
    equipment_base=68
)

# Швейцария
NDB = IntelligenceAgency(
    id="ch_int_001",
    name="Федеральная разведывательная служба (NDB)",
    country="Швейцария",
    description="**NDB** - гражданская разведка Швейцарии, отвечающая за сбор информации о внешних и внутренних угрозах нейтралитету страны.",
    founded=2010,
    specialization=["foreign", "domestic", "analysis"],
    budget_multiplier=0.5,
    influence=15,
    corruption=3,
    personnel_base=300,
    equipment_base=70
)

MND = IntelligenceAgency(
    id="ch_int_002",
    name="Военная разведка (MND)",
    country="Швейцария",
    description="**MND** - военная разведка Швейцарии, занимающаяся сбором информации о военных угрозах и поддержкой нейтралитета.",
    founded=2010,
    specialization=["military_intelligence", "analysis"],
    budget_multiplier=0.4,
    influence=12,
    corruption=2,
    personnel_base=200,
    equipment_base=68
)

# Египет
GIS = IntelligenceAgency(
    id="eg_int_001",
    name="Общая разведывательная служба (GIS)",
    country="Египет",
    description="**GIS** - главное разведывательное агентство Египта, отвечающее за внешнюю разведку и сбор информации о региональных угрозах.",
    founded=1954,
    specialization=["foreign", "analysis", "covert_ops"],
    budget_multiplier=0.7,
    influence=70,
    corruption=60,
    personnel_base=5000,
    equipment_base=50
)

NSS = IntelligenceAgency(
    id="eg_int_002",
    name="Служба национальной безопасности (NSS)",
    country="Египет",
    description="**NSS** - служба внутренней безопасности Египта, занимающаяся контрразведкой и борьбой с терроризмом.",
    founded=1953,
    specialization=["counterintelligence", "domestic", "terrorism"],
    budget_multiplier=0.6,
    influence=75,
    corruption=65,
    personnel_base=15000,
    equipment_base=45
)

MID = IntelligenceAgency(
    id="eg_int_003",
    name="Военная разведка (MID)",
    country="Египет",
    description="**MID** - военная разведка Египта, занимающаяся сбором информации о военных угрозах в регионе.",
    founded=1952,
    specialization=["military_intelligence", "analysis"],
    budget_multiplier=0.5,
    influence=60,
    corruption=55,
    personnel_base=3000,
    equipment_base=48
)


# ==================== СВОДНАЯ БАЗА ДАННЫХ ====================

ALL_AGENCIES = {
    "США": {
        "cia": CIA,
        "nsa": NSA,
        "fbi": FBI,
        "dia": DIA
    },
    "Россия": {
        "fsb": FSB,
        "svr": SVR,
        "gru": GRU,
        "fso": FSO
    },
    "Китай": {
        "mss": MSS,
        "pla_intel": PLA_Intel
    },
    "Германия": {
        "bnd": BND,
        "bfv": BfV,
        "mad": MAD
    },
    "Великобритания": {
        "mi6": MI6,
        "mi5": MI5,
        "gchq": GCHQ
    },
    "Франция": {
        "dgse": DGSE,
        "dgsi": DGSI,
        "drm": DRM
    },
    "Украина": {
        "sbu": SBU,
        "gur": GUR
    },
    "Япония": {
        "psia": PSIA,
        "dih": DIH,
        "ciro": CIRO
    },
    "Иран": {
        "mois": MOIS,
        "irgc_intel": IRGC_Intel
    },
    "Израиль": {
        "mossad": MOSSAD,
        "shabak": SHABAK,
        "aman": AMAN
    },
    
    # ============ НОВЫЕ ГОСУДАРСТВА ============
    
    "Беларусь": {
        "kgb": KGB_BELARUS
    },
    "Норвегия": {
        "nis": NIS,
        "pst": PST
    },
    "КНДР": {
        "rgb": RGB,
        "mss_kp": MSS_KP
    },
    "Турция": {
        "mit": MIT,
        "jitem": JITEM
    },
    "Сирия": {
        "gsd": GSD,
        "aif": AIF
    },
    "Канада": {
        "csis": CSIS,
        "cse": CSE
    },
    "Польша": {
        "aw": AW,
        "abw": ABW,
        "skw": SKW
    },
    "Бразилия": {
        "abin": ABIN,
        "cie": CIE
    },
    "Швеция": {
        "must": MUST,
        "sapo": SAPO,
        "fra": FRA
    },
    "Финляндия": {
        "supo": SUPO,
        "tiedustelulaitos": TIEDUSTELULAITOS
    },
    "Швейцария": {
        "ndb": NDB,
        "mnd": MND
    },
    "Египет": {
        "gis": GIS,
        "nss": NSS,
        "mid": MID
    }
}

# Словарь для быстрого поиска агентства по ID
AGENCIES_BY_ID = {}
for country, agencies in ALL_AGENCIES.items():
    for agency_id, agency in agencies.items():
        AGENCIES_BY_ID[agency.id] = agency
        # Также добавляем по ключу из словаря
        AGENCIES_BY_ID[agency_id] = agency


def get_agencies_by_country(country_name):
    """Получить все разведывательные агентства страны"""
    return ALL_AGENCIES.get(country_name, {})


def get_agency(agency_id):
    """Получить агентство по ID"""
    return AGENCIES_BY_ID.get(agency_id)


def get_all_agencies():
    """Получить все агентства"""
    result = []
    for agencies in ALL_AGENCIES.values():
        result.extend(agencies.values())
    return result


# ==================== ЭКСПОРТ ====================

__all__ = [
    'IntelligenceAgency',
    'get_agencies_by_country',
    'get_agency',
    'get_all_agencies',
    'ALL_AGENCIES'
]

# game_time.py - Модуль для управления игровым временем
# Старт: 1 декабря 2022 года
# 1 игровой год = 3 реальных дня
# 8 реальных часов = 1 игровой месяц

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Tuple

# Файл для хранения игрового времени
GAME_TIME_FILE = 'game_time.json'

# Константы времени
REAL_DAYS_PER_GAME_YEAR = 3  # 3 реальных дня = 1 игровой год
REAL_HOURS_PER_GAME_MONTH = 8  # 8 реальных часов = 1 игровой месяц

# Стартовая дата
START_DATE = datetime(2022, 12, 1)
START_DATE_STR = "2022-12-01"

# ==================== ФУНКЦИИ ЗАГРУЗКИ/СОХРАНЕНИЯ ====================

def load_game_time():
    """Загружает игровое время из файла"""
    try:
        with open(GAME_TIME_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except (FileNotFoundError, json.JSONDecodeError):
        # Создаем начальные данные
        initial_data = {
            "last_real_update": str(datetime.now()),
            "game_date": START_DATE_STR,
            "total_game_days": 0,
            "total_real_seconds": 0
        }
        save_game_time(initial_data)
        return initial_data

def save_game_time(data):
    """Сохраняет игровое время в файл"""
    with open(GAME_TIME_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==================== ОСНОВНЫЕ ФУНКЦИИ ====================

def update_game_time() -> Dict:
    """
    Обновляет игровое время на основе прошедшего реального времени
    Вызывается периодически или перед важными событиями
    """
    data = load_game_time()
    
    last_update = datetime.fromisoformat(data["last_real_update"])
    now = datetime.now()
    
    real_seconds_passed = (now - last_update).total_seconds()
    
    # Конвертируем реальное время в игровое
    # 3 реальных дня = 1 игровой год (365 дней)
    # Значит 1 реальный день = 365/3 ≈ 121.67 игровых дней
    game_days_per_real_day = 365 / REAL_DAYS_PER_GAME_YEAR
    game_days_per_real_second = game_days_per_real_day / (24 * 3600)
    
    game_days_passed = real_seconds_passed * game_days_per_real_second
    
    # Обновляем счетчики
    data["total_real_seconds"] += real_seconds_passed
    data["total_game_days"] += game_days_passed
    data["last_real_update"] = str(now)
    
    # Пересчитываем игровую дату
    game_date = START_DATE + timedelta(days=data["total_game_days"])
    data["game_date"] = game_date.strftime("%Y-%m-%d")
    
    save_game_time(data)
    
    return {
        "real_date": now,
        "game_date": game_date,
        "real_seconds_passed": real_seconds_passed,
        "game_days_passed": game_days_passed,
        "total_game_days": data["total_game_days"]
    }

def get_current_game_time() -> Tuple[datetime, float]:
    """
    Возвращает текущее игровое время и количество прошедших реальных секунд
    Без сохранения (для быстрого доступа)
    """
    data = load_game_time()
    
    last_update = datetime.fromisoformat(data["last_real_update"])
    now = datetime.now()
    
    real_seconds_passed = (now - last_update).total_seconds()
    
    game_days_per_real_second = (365 / REAL_DAYS_PER_GAME_YEAR) / (24 * 3600)
    game_days_passed = real_seconds_passed * game_days_per_real_second
    
    total_game_days = data["total_game_days"] + game_days_passed
    game_date = START_DATE + timedelta(days=total_game_days)
    
    return game_date, real_seconds_passed

def get_game_date_formatted() -> str:
    """Возвращает отформатированную игровую дату"""
    game_date, _ = get_current_game_time()
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    return f"{game_date.day} {months[game_date.month-1]} {game_date.year} года"

def get_season(date: datetime = None) -> str:
    """Определяет время года по дате"""
    if date is None:
        date, _ = get_current_game_time()
    
    month = date.month
    
    if 3 <= month <= 5:
        return "весна"
    elif 6 <= month <= 8:
        return "лето"
    elif 9 <= month <= 11:
        return "осень"
    else:
        return "зима"

def get_month() -> int:
    """Возвращает текущий игровой месяц (1-12)"""
    game_date, _ = get_current_game_time()
    return game_date.month

def get_year() -> int:
    """Возвращает текущий игровой год"""
    game_date, _ = get_current_game_time()
    return game_date.year

def days_since_last_event(last_event_time: str) -> float:
    """
    Рассчитывает, сколько игровых дней прошло с последнего события
    """
    try:
        last_time = datetime.fromisoformat(last_event_time)
    except (ValueError, TypeError):
        return 0
    
    now = datetime.now()
    real_seconds_passed = (now - last_time).total_seconds()
    
    game_days_per_real_second = (365 / REAL_DAYS_PER_GAME_YEAR) / (24 * 3600)
    return real_seconds_passed * game_days_per_real_second

def months_since_last_event(last_event_time: str) -> float:
    """Рассчитывает, сколько игровых месяцев прошло с последнего события"""
    game_days = days_since_last_event(last_event_time)
    return game_days / 30

# ==================== ФОНОВАЯ ЗАДАЧА ====================

async def game_time_update_loop(bot_instance):
    """Фоновая задача для регулярного обновления игрового времени"""
    await bot_instance.wait_until_ready()
    
    while not bot_instance.is_closed():
        try:
            # Обновляем время (раз в минуту, чтобы файл не перезаписывался слишком часто)
            update = update_game_time()
            
            # Каждый игровой месяц выводим сообщение в консоль
            if abs(update["game_days_passed"] - 30) < 0.1:  # Приблизительно месяц
                game_date = update["game_date"]
                print(f"📅 Наступил {game_date.strftime('%B %Y')} в игровом мире")
            
            await asyncio.sleep(60)  # Проверка каждую минуту
            
        except Exception as e:
            print(f"❌ Ошибка в game_time_update_loop: {e}")
            await asyncio.sleep(60)

# ==================== ЭКСПОРТ ====================

__all__ = [
    'update_game_time',
    'get_current_game_time',
    'get_game_date_formatted',
    'get_season',
    'get_month',
    'get_year',
    'days_since_last_event',
    'months_since_last_event',
    'game_time_update_loop',
    'START_DATE',
    'REAL_DAYS_PER_GAME_YEAR',
    'REAL_HOURS_PER_GAME_MONTH'
]

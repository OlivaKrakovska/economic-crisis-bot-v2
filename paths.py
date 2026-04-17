# paths.py - Централизованное управление путями к файлам данных
import os
from typing import Dict

# Определяем корневую директорию для данных
# По умолчанию - текущая папка
DATA_DIR = os.path.dirname(os.path.abspath(__file__))

# Убеждаемся, что директория существует
os.makedirs(DATA_DIR, exist_ok=True)

# Словарь с путями ко всем файлам
DATA_FILES = {
    # Основные файлы
    'states': os.path.join(DATA_DIR, 'states.json'),
    'production_queue': os.path.join(DATA_DIR, 'production_queue.json'),
    'civil_production_queue': os.path.join(DATA_DIR, 'civil_production_queue.json'),
    'construction_queue': os.path.join(DATA_DIR, 'infra_construction.json'),
    'trades': os.path.join(DATA_DIR, 'trades.json'),
    'transfers': os.path.join(DATA_DIR, 'transfers.json'),
    'research': os.path.join(DATA_DIR, 'research_data.json'),
    'tariffs': os.path.join(DATA_DIR, 'tariffs.json'),
    'infrastructure': os.path.join(DATA_DIR, 'infrastructure.json'),
    'conflicts': os.path.join(DATA_DIR, 'conflicts.json'),
    'central_bank': os.path.join(DATA_DIR, 'central_bank.json'),
    'last_extraction': os.path.join(DATA_DIR, 'last_extraction.json'),
    
    # Новые файлы
    'corporations_state': os.path.join(DATA_DIR, 'corporations_state.json'),
    'corporations_starting': os.path.join(DATA_DIR, 'corporations_starting_data.json'),
    'mobilization': os.path.join(DATA_DIR, 'mobilization.json'),
    'game_time': os.path.join(DATA_DIR, 'game_time.json'),
    'satellites': os.path.join(DATA_DIR, 'satellites.json'),
    'military_doctrines': os.path.join(DATA_DIR, 'military_doctrines.json'),
    'espionage': os.path.join(DATA_DIR, 'espionage.json'),
    
    # Дополнительные файлы
    'distances': os.path.join(DATA_DIR, 'distances.json'),
    'strikes': os.path.join(DATA_DIR, 'strikes.json'),
    'strike_queue': os.path.join(DATA_DIR, 'strike_queue.json'),
    'political_laws': os.path.join(DATA_DIR, 'political_laws.json'),
    'alliances': os.path.join(DATA_DIR, 'alliances.json'),
    'technologies': os.path.join(DATA_DIR, 'technologies.json'),
}

def get_data_path(filename: str) -> str:
    """Получить полный путь к файлу данных"""
    if filename in DATA_FILES:
        return DATA_FILES[filename]
    # Если файл не в списке, создаем путь в DATA_DIR
    return os.path.join(DATA_DIR, filename)

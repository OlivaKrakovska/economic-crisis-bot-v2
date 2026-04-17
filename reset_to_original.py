# reset_to_original.py - Модуль для сброса государств к исходным значениям
# ОБНОВЛЁН: Добавлена поддержка сброса корпораций, расконсервации техники,
#           надводных дронов, ускоренной конверсии фабрик, а также
#           сброс данных ударов (включая новые типы целей) и блокад
#           Добавлена синхронизация ПВО между арсеналом и инфраструктурой
#           Добавлен сброс данных спутников (государственные, корпоративные, доступ)
#           Добавлен сброс данных трубопроводов (pipelines)
#           Добавлен сброс данных населения (population)
#           ИСПРАВЛЕНО: states.json теперь полностью перезаписывается из states_default.json

import discord
from discord.ext import commands
import json
import os
import shutil
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio

from config import ADMIN_LOG_CHANNEL_ID
from utils import load_states, save_states, DARK_THEME_COLOR

# ==================== ЗАГРУЗКА ОРИГИНАЛЬНЫХ ДАННЫХ ====================

def load_original_states() -> Dict:
    """Загружает оригинальные данные государств из файла states_default.json"""
    try:
        with open('states_default.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("Файл states_default.json не найден! Используются встроенные данные.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Ошибка в файле states_default.json: {e}")
        return {}

# Загружаем данные при импорте модуля
ORIGINAL_STATES = load_original_states()

# ==================== ФУНКЦИИ ДЛЯ РАБОТЫ С ПАПКОЙ SAVES ====================

def ensure_saves_folder():
    """Создаёт папку saves, если её нет"""
    if not os.path.exists('saves'):
        os.makedirs('saves')
        print("Создана папка saves")
    return 'saves'

def create_backup(backup_name: str, files_to_backup: list) -> str:
    """
    Создаёт резервную копию файлов в папке saves
    Возвращает путь к папке с бэкапом
    """
    saves_folder = ensure_saves_folder()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(saves_folder, f"{backup_name}_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)
    
    backed_up = []
    for filename in files_to_backup:
        if os.path.exists(filename):
            try:
                shutil.copy2(filename, os.path.join(backup_dir, filename))
                backed_up.append(filename)
            except Exception as e:
                print(f"Ошибка при копировании {filename}: {e}")
    
    if backed_up:
        print(f"Создана резервная копия в {backup_dir}: {', '.join(backed_up)}")
    else:
        print("Не найдено файлов для резервного копирования")
    
    return backup_dir


# ==================== ФУНКЦИИ ДЛЯ СБРОСА НАСЕЛЕНИЯ ====================

def reset_population(backup: bool = True) -> Dict:
    """
    Сбрасывает данные населения к исходным значениям
    """
    results = {
        "population_reset": False,
        "experts_reset": False,
        "backup_path": None
    }
    
    population_files = ['exported_experts.json', 'expert_requests.json']
    
    if backup:
        existing_files = [f for f in population_files if os.path.exists(f)]
        if existing_files:
            results["backup_path"] = create_backup("population_backup", existing_files)
    
    # Сбрасываем данные об экспортированных специалистах
    try:
        exported_data = {"exported": {}, "guards": {}}
        with open('exported_experts.json', 'w', encoding='utf-8') as f:
            json.dump(exported_data, f, ensure_ascii=False, indent=4)
        results["experts_reset"] = True
        print("Файл exported_experts.json сброшен (нет экспортированных специалистов)")
    except Exception as e:
        print(f"Ошибка при сбросе exported_experts.json: {e}")
    
    # Сбрасываем данные о запросах на специалистов
    try:
        requests_data = {"pending": [], "completed": [], "rejected": []}
        with open('expert_requests.json', 'w', encoding='utf-8') as f:
            json.dump(requests_data, f, ensure_ascii=False, indent=4)
        print("Файл expert_requests.json сброшен (нет активных запросов)")
    except Exception as e:
        print(f"Ошибка при сбросе expert_requests.json: {e}")
    
    # Данные населения хранятся в states.json
    try:
        states = load_states()
        for state_id, player_data in states["players"].items():
            # Инициализируем population_data пустым словарём, а не удаляем
            player_data["population_data"] = {}
            
            # Сбрасываем социальные показатели к исходным значениям из ORIGINAL_STATES
            if state_id in ORIGINAL_STATES:
                original = ORIGINAL_STATES[state_id]
                if "state" in original:
                    player_data["state"]["happiness"] = original["state"].get("happiness", 50)
                    player_data["state"]["stability"] = original["state"].get("stability", 50)
                    player_data["state"]["trust"] = original["state"].get("trust", 50)
                
                if "politics" in original:
                    player_data["politics"]["popularity"] = original["politics"].get("popularity", 50)
        
        save_states(states)
        results["population_reset"] = True
        print("Данные населения сброшены (социальные показатели восстановлены, population_data инициализирован)")
    except Exception as e:
        print(f"Ошибка при сбросе данных населения: {e}")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ СБРОСА ТРУБОПРОВОДОВ ====================

def reset_pipelines(backup: bool = True) -> Dict:
    """
    Сбрасывает данные трубопроводов к исходным значениям из DEFAULT_PIPELINES
    """
    import os
    import json
    from pipelines import DEFAULT_PIPELINES, PIPELINE_LENGTHS_BY_COUNTRY
    
    results = {
        "pipelines_reset": False,
        "construction_reset": False,
        "logs_reset": False,
        "diplomacy_reset": False,
        "backup_path": None
    }
    
    pipeline_files = ['pipelines.json', 'pipeline_construction.json', 'pipeline_logs.json', 'pipeline_diplomacy.json']
    
    if backup:
        existing_files = [f for f in pipeline_files if os.path.exists(f)]
        if existing_files:
            results["backup_path"] = create_backup("pipelines_backup", existing_files)
    
    # Сбрасываем основные данные трубопроводов
    try:
        # Создаём копию DEFAULT_PIPELINES с правильными структурами
        pipelines_data = {"pipelines": [], "stats": {}}
        for p in DEFAULT_PIPELINES:
            pipeline_copy = p.copy()
            # Убеждаемся, что все необходимые поля есть
            pipeline_copy["closed_sections"] = {}
            pipeline_copy["country_control"] = {}
            pipeline_copy["country_military"] = {}
            pipeline_copy["country_vehicles"] = {}
            pipeline_copy["country_uav"] = {}
            
            # Инициализируем контроль для каждой страны
            for country in pipeline_copy["countries_through"]:
                pipeline_copy["country_control"][country] = (pipeline_copy["country_length"].get(country, {}).get("land", 0) + 
                                                              pipeline_copy["country_length"].get(country, {}).get("sea", 0)) / pipeline_copy["total_length"] * 100
                pipeline_copy["country_military"][country] = {"infantry": 0}
                pipeline_copy["country_vehicles"][country] = {"armored_vehicles": 0}
                pipeline_copy["country_uav"][country] = {"attack_uav": 0, "recon_uav": 0}
            
            pipelines_data["pipelines"].append(pipeline_copy)
        
        with open('pipelines.json', 'w', encoding='utf-8') as f:
            json.dump(pipelines_data, f, ensure_ascii=False, indent=4)
        results["pipelines_reset"] = True
        print("Файл pipelines.json сброшен к исходным значениям")
    except Exception as e:
        print(f"Ошибка при сбросе pipelines.json: {e}")
    
    # Сбрасываем очередь строительства трубопроводов
    try:
        construction_data = {"active_projects": [], "completed_projects": [], "active_dismantles": [], "active_repairs": []}
        with open('pipeline_construction.json', 'w', encoding='utf-8') as f:
            json.dump(construction_data, f, ensure_ascii=False, indent=4)
        results["construction_reset"] = True
        print("Файл pipeline_construction.json сброшен")
    except Exception as e:
        print(f"Ошибка при сбросе pipeline_construction.json: {e}")
    
    # Сбрасываем логи трубопроводов
    try:
        logs_data = {"logs": []}
        with open('pipeline_logs.json', 'w', encoding='utf-8') as f:
            json.dump(logs_data, f, ensure_ascii=False, indent=4)
        results["logs_reset"] = True
        print("Файл pipeline_logs.json сброшен")
    except Exception as e:
        print(f"Ошибка при сбросе pipeline_logs.json: {e}")
    
    # Сбрасываем дипломатические соглашения по трубопроводам
    try:
        diplomacy_data = {"pending_projects": [], "approved_projects": []}
        with open('pipeline_diplomacy.json', 'w', encoding='utf-8') as f:
            json.dump(diplomacy_data, f, ensure_ascii=False, indent=4)
        results["diplomacy_reset"] = True
        print("Файл pipeline_diplomacy.json сброшен")
    except Exception as e:
        print(f"Ошибка при сбросе pipeline_diplomacy.json: {e}")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ СБРОСА СПУТНИКОВ ====================

def reset_satellites(backup: bool = True) -> Dict:
    """
    Сбрасывает данные о спутниках к исходным значениям
    """
    import os
    import json
    from satellites import STARTING_SATELLITES, SATELLITE_TYPES
    
    results = {
        "gov_satellites_reset": False,
        "corp_satellites_reset": False,
        "access_reset": False,
        "backup_path": None
    }
    
    satellite_files = ['satellites.json', 'corporate_satellites.json', 'satellite_access.json']
    
    if backup:
        existing_files = [f for f in satellite_files if os.path.exists(f)]
        if existing_files:
            results["backup_path"] = create_backup("satellites_backup", existing_files)
    
    # Сбрасываем государственные спутники
    try:
        gov_data = {"satellites": {}}
        for country, data in STARTING_SATELLITES.items():
            gov_data["satellites"][country] = {
                "military": data.get("military", 0),
                "civilian": data.get("civilian", 0),
                "launch_history": [],
                "last_maintenance": str(datetime.now()),
                "notes": data.get("notes", "")
            }
        
        with open('satellites.json', 'w', encoding='utf-8') as f:
            json.dump(gov_data, f, ensure_ascii=False, indent=4)
        results["gov_satellites_reset"] = True
        print("Файл satellites.json сброшен к исходным значениям")
    except Exception as e:
        print(f"Ошибка при сбросе satellites.json: {e}")
    
    # Сбрасываем корпоративные спутники
    try:
        from satellites import CORPORATE_SATELLITE_OWNERS
        
        corp_data = {
            "corporations": {},
            "subscriptions": {},
            "starlink_status": {
                "active": True,
                "last_crisis": None,
                "crisis_count": 0
            }
        }
        
        for corp_name, corp_info in CORPORATE_SATELLITE_OWNERS.items():
            corp_data["corporations"][corp_name] = {
                "name": corp_info["name"],
                "country": corp_info["country"],
                "civilian_satellites": corp_info["civilian_satellites"],
                "military_satellites": corp_info["military_satellites"],
                "description": corp_info["description"],
                "service_type": corp_info.get("service_type", "telecom_global"),
                "requires_subscription": corp_info.get("requires_subscription", True),
                "subscription_cost": corp_info.get("subscription_cost", 100000),
                "bonus_if_active": corp_info.get("bonus_if_active", {})
            }
        
        with open('corporate_satellites.json', 'w', encoding='utf-8') as f:
            json.dump(corp_data, f, ensure_ascii=False, indent=4)
        results["corp_satellites_reset"] = True
        print("Файл corporate_satellites.json сброшен к исходным значениям")
    except Exception as e:
        print(f"Ошибка при сбросе corporate_satellites.json: {e}")
    
    # Сбрасываем данные о доступе к спутникам
    try:
        access_data = {"access_grants": {}, "corporate_blocks": {}}
        
        with open('satellite_access.json', 'w', encoding='utf-8') as f:
            json.dump(access_data, f, ensure_ascii=False, indent=4)
        results["access_reset"] = True
        print("Файл satellite_access.json сброшен (доступ и блокировки очищены)")
    except Exception as e:
        print(f"Ошибка при сбросе satellite_access.json: {e}")
    
    return results


# ==================== ФУНКЦИЯ СИНХРОНИЗАЦИИ ПВО ====================

def sync_pvo_between_arsenal_and_infrastructure(player_data: Dict, country_name: str) -> Dict:
    """
    Синхронизирует ПВО между арсеналом и инфраструктурой.
    При инициализации страны ПВО из инфраструктуры списывается из арсенала.
    Возвращает словарь с результатами синхронизации.
    """
    from infra_build import load_infrastructure, save_infrastructure, get_all_regions_from_country, INFRASTRUCTURE_COSTS
    
    results = {"pvo_synced": False, "pvo_removed": 0, "pvo_types": {}}
    
    # Загружаем инфраструктуру
    infra_data = load_infrastructure()
    
    # Находим ID страны
    country_id = None
    for cid, data in infra_data["infrastructure"].items():
        if data.get("country") == country_name:
            country_id = cid
            break
    
    if not country_id:
        return results
    
    # Получаем все регионы
    regions = get_all_regions_from_country(infra_data, country_id)
    
    # Собираем все ПВО из инфраструктуры
    pvo_in_infra = {
        "long_range_air_defense": 0,
        "short_range_air_defense": 0,
        "zdprk": 0,
        "zas": 0,
        "radar_systems": 0
    }
    
    for region_data in regions.values():
        for pvo_type in pvo_in_infra.keys():
            count = region_data.get(pvo_type, 0)
            if count > 0:
                pvo_in_infra[pvo_type] += count
    
    # Если нет ПВО в инфраструктуре, ничего не делаем
    total_pvo_in_infra = sum(pvo_in_infra.values())
    if total_pvo_in_infra == 0:
        results["pvo_synced"] = True
        return results
    
    # Списываем ПВО из арсенала
    if "army" not in player_data:
        player_data["army"] = {}
    if "ground" not in player_data["army"]:
        player_data["army"]["ground"] = {}
    
    ground = player_data["army"]["ground"]
    
    pvo_removed = 0
    pvo_types_removed = {}
    
    for pvo_type, count in pvo_in_infra.items():
        if count > 0:
            current = ground.get(pvo_type, 0)
            if current >= count:
                ground[pvo_type] = current - count
                pvo_removed += count
                pvo_types_removed[pvo_type] = count
            else:
                # Если в арсенале меньше, чем в инфраструктуре, устанавливаем в 0
                pvo_removed += current
                pvo_types_removed[pvo_type] = current
                ground[pvo_type] = 0
                print(f"⚠️ Предупреждение: В арсенале недостаточно {pvo_type} для списания! Списано {current} из {count}")
    
    player_data["army"]["ground"] = ground
    results["pvo_synced"] = True
    results["pvo_removed"] = pvo_removed
    results["pvo_types"] = pvo_types_removed
    
    print(f"Синхронизировано ПВО: списано {pvo_removed} единиц из арсенала (установлены в инфраструктуре)")
    
    return results


def sync_all_countries_pvo() -> Dict:
    """
    Синхронизирует ПВО для всех стран при запуске бота или сбросе.
    Проходится по всем государствам и списывает из арсенала ПВО, уже установленные в инфраструктуре.
    """
    from infra_build import load_infrastructure, get_all_regions_from_country
    
    states = load_states()
    infra_data = load_infrastructure()
    
    results = {
        "total_countries": 0,
        "countries_updated": 0,
        "total_pvo_removed": 0,
        "details": {}
    }
    
    for state_id, player_data in states["players"].items():
        country_name = player_data["state"]["statename"]
        results["total_countries"] += 1
        
        # Синхронизируем для каждой страны
        sync_result = sync_pvo_between_arsenal_and_infrastructure(player_data, country_name)
        
        if sync_result["pvo_synced"] and sync_result["pvo_removed"] > 0:
            results["countries_updated"] += 1
            results["total_pvo_removed"] += sync_result["pvo_removed"]
            results["details"][country_name] = sync_result["pvo_types"]
    
    if results["total_pvo_removed"] > 0:
        save_states(states)
        print(f"Синхронизация ПВО завершена: обновлено {results['countries_updated']} стран, списано {results['total_pvo_removed']} единиц ПВО")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ СБРОСА КОРПОРАЦИЙ ====================

def reset_corporations(backup: bool = True) -> Dict:
    """
    Сбрасывает данные корпораций к исходным значениям из corporations_starting_data.json
    """
    import os
    import json
    from civil_corporations_db import load_corporations_state, save_corporations_state, load_starting_corporation_data, CivilCorporation
    
    results = {"corporations_reset": False, "state_reset": False, "backup_path": None, "corps_processed": 0}
    
    corporation_files = ['corporations_state.json']
    if backup:
        existing_files = [f for f in corporation_files if os.path.exists(f)]
        if existing_files:
            results["backup_path"] = create_backup("corporations_backup", existing_files)
    
    # Загружаем стартовые данные
    starting_data = load_starting_corporation_data()
    
    # Создаём новый файл состояния с данными из starting_data
    new_state = {"corporations": {}}
    
    for corp_id, corp_data in starting_data.items():
        # Создаём объект корпорации из стартовых данных
        corp = CivilCorporation(
            corp_id=corp_id,
            name=corp_data.get("name", "Неизвестно"),
            country=corp_data.get("country", "Неизвестно"),
            city=corp_data.get("city", ""),
            description=corp_data.get("description", ""),
            specialization=corp_data.get("specialization", []),
            products=corp_data.get("products", {}),
            founded=corp_data.get("founded"),
            website=corp_data.get("website"),
            service_type=corp_data.get("service_type", "manufacturing")
        )
        
        # Заполняем динамические данные из стартовых
        corp.inventory = corp_data.get("inventory", {})
        corp.budget = corp_data.get("budget", 10000000)
        corp.popularity = corp_data.get("popularity", 60)
        corp.market_share = corp_data.get("market_share", {})
        corp.employees = corp_data.get("employees", 0)
        corp.last_update = None
        
        new_state["corporations"][corp_id] = corp
        results["corps_processed"] += 1
    
    # Сохраняем новое состояние
    save_corporations_state(new_state)
    results["state_reset"] = True
    results["corporations_reset"] = True
    
    print(f"Сброшены данные {results['corps_processed']} корпораций")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ СБРОСА РАСКОНСЕРВАЦИИ ====================

def reset_reserves_conversion(backup: bool = True) -> Dict:
    """
    Сбрасывает данные расконсервации техники:
    - Удаляет очередь расконсервации
    - Сбрасывает данные о расконсервированной технике
    - Восстанавливает исходные резервы техники (включая надводные дроны)
    """
    import os
    import json
    from mobilization import MILITARY_RESERVES
    
    results = {
        "conversion_queue_reset": False,
        "reserves_reset": False,
        "activated_reset": False,
        "backup_path": None
    }
    
    # Файлы для сброса
    conversion_files = ['conversion_queue.json', 'reserves.json']
    
    if backup:
        existing_files = [f for f in conversion_files if os.path.exists(f)]
        if existing_files:
            results["backup_path"] = create_backup("reserves_backup", existing_files)
    
    # Сбрасываем очередь расконсервации
    conversion_queue_reset = {"active_conversions": [], "completed_conversions": []}
    try:
        with open('conversion_queue.json', 'w', encoding='utf-8') as f:
            json.dump(conversion_queue_reset, f, ensure_ascii=False, indent=4)
        results["conversion_queue_reset"] = True
        print("Файл conversion_queue.json сброшен")
    except Exception as e:
        print(f"Ошибка при сбросе conversion_queue.json: {e}")
    
    # Сбрасываем данные о резервах (возвращаем к исходным значениям)
    reserves_reset_data = {
        "activated": {},  # Очищаем список расконсервированной техники
        "remaining_reserves": MILITARY_RESERVES.copy()  # Восстанавливаем исходные резервы
    }
    try:
        with open('reserves.json', 'w', encoding='utf-8') as f:
            json.dump(reserves_reset_data, f, ensure_ascii=False, indent=4)
        results["reserves_reset"] = True
        results["activated_reset"] = True
        print("Файл reserves.json сброшен к исходным значениям (включая надводные дроны)")
    except Exception as e:
        print(f"Ошибка при сбросе reserves.json: {e}")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ СБРОСА УДАРОВ (ОБНОВЛЁННАЯ) ====================

def reset_strikes(backup: bool = True) -> Dict:
    """
    Сбрасывает данные ударов и очереди ударов
    Поддерживает все типы ударов (инфраструктура, ПВО, флот, торговые конвои)
    """
    import os
    import json
    
    results = {"strikes_reset": False, "queue_reset": False, "distances_reset": False, "backup_path": None}
    
    if backup:
        strikes_files = ['strikes.json', 'strike_queue.json', 'distances.json']
        existing_files = [f for f in strikes_files if os.path.exists(f)]
        if existing_files:
            results["backup_path"] = create_backup("strikes_backup", existing_files)
    
    # Сбрасываем историю ударов
    strikes_reset_data = {"strikes": [], "stats": {}}
    try:
        with open('strikes.json', 'w', encoding='utf-8') as f:
            json.dump(strikes_reset_data, f, ensure_ascii=False, indent=4)
        results["strikes_reset"] = True
        print("Файл strikes.json сброшен")
    except Exception as e:
        print(f"Ошибка при сбросе strikes.json: {e}")
    
    # Сбрасываем очередь ударов
    strike_queue_reset_data = {"active_strikes": [], "completed_strikes": []}
    try:
        with open('strike_queue.json', 'w', encoding='utf-8') as f:
            json.dump(strike_queue_reset_data, f, ensure_ascii=False, indent=4)
        results["queue_reset"] = True
        print("Файл strike_queue.json сброшен")
    except Exception as e:
        print(f"Файл strike_queue.json не найден или ошибка: {e}")
    
    # Сбрасываем расстояния (если файл существует)
    if os.path.exists('distances.json'):
        try:
            distances_reset_data = {}
            with open('distances.json', 'w', encoding='utf-8') as f:
                json.dump(distances_reset_data, f, ensure_ascii=False, indent=4)
            results["distances_reset"] = True
            print("Файл distances.json сброшен")
        except Exception as e:
            print(f"Ошибка при сбросе distances.json: {e}")
    else:
        results["distances_reset"] = True
        print("Файл distances.json не найден, пропущен")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ СБРОСА МОРСКОЙ ТОРГОВЛИ ====================

def reset_maritime_trade(backup: bool = True) -> Dict:
    """
    Сбрасывает данные морской торговли и сразу инициализирует новые корабли
    """
    import os
    import json
    from maritime_trade import initialize_fleet
    
    results = {"ships_reset": False, "strikes_reset": False, "initialized": False, "backup_path": None}
    
    if backup:
        maritime_files = ['maritime_data.json', 'ship_strikes.json', 'ship_strike_queue.json', 'priority_regions.json']
        existing_files = [f for f in maritime_files if os.path.exists(f)]
        if existing_files:
            results["backup_path"] = create_backup("maritime_backup", existing_files)
    
    if os.path.exists('maritime_data.json'):
        try:
            os.remove('maritime_data.json')
            results["ships_reset"] = True
            print("Файл maritime_data.json удалён")
        except Exception as e:
            print(f"Ошибка при удалении maritime_data.json: {e}")
    else:
        print("Файл maritime_data.json не найден")
    
    ship_strikes_reset_data = {"strikes": [], "stats": {}}
    try:
        with open('ship_strikes.json', 'w', encoding='utf-8') as f:
            json.dump(ship_strikes_reset_data, f, ensure_ascii=False, indent=4)
        results["strikes_reset"] = True
        print("Файл ship_strikes.json сброшен")
    except Exception as e:
        print(f"Ошибка при сбросе ship_strikes.json: {e}")
    
    ship_strike_queue_reset_data = {"active_strikes": [], "completed_strikes": []}
    try:
        with open('ship_strike_queue.json', 'w', encoding='utf-8') as f:
            json.dump(ship_strike_queue_reset_data, f, ensure_ascii=False, indent=4)
        print("Файл ship_strike_queue.json сброшен")
    except Exception as e:
        print(f"Файл ship_strike_queue.json не найден или ошибка: {e}")
    
    priority_regions_reset_data = {"export_priorities": {}}
    try:
        with open('priority_regions.json', 'w', encoding='utf-8') as f:
            json.dump(priority_regions_reset_data, f, ensure_ascii=False, indent=4)
        print("Файл priority_regions.json сброшен")
    except Exception as e:
        print(f"Ошибка при сбросе priority_regions.json: {e}")
    
    try:
        initialize_fleet()
        results["initialized"] = True
        print("Новые торговые корабли созданы")
    except Exception as e:
        print(f"Ошибка при инициализации торгового флота: {e}")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ СБРОСА ВОЕННО-МОРСКОГО ФЛОТА ====================

def reset_navy(backup: bool = True) -> Dict:
    """
    Сбрасывает данные военно-морского флота и инициализирует новые флоты
    (включая надводные дроны)
    """
    import os
    import json
    from navy import initialize_fleets
    
    results = {"navy_reset": False, "operations_reset": False, "initialized": False, "backup_path": None}
    
    if backup:
        navy_files = ['navy.json', 'naval_operations.json']
        existing_files = [f for f in navy_files if os.path.exists(f)]
        if existing_files:
            results["backup_path"] = create_backup("navy_backup", existing_files)
    
    if os.path.exists('navy.json'):
        try:
            os.remove('navy.json')
            results["navy_reset"] = True
            print("Файл navy.json удалён")
        except Exception as e:
            print(f"Ошибка при удалении navy.json: {e}")
    
    if os.path.exists('naval_operations.json'):
        try:
            os.remove('naval_operations.json')
            results["operations_reset"] = True
            print("Файл naval_operations.json удалён (блокады и патрули сброшены)")
        except Exception as e:
            print(f"Ошибка при удалении naval_operations.json: {e}")
    
    try:
        initialize_fleets()
        results["initialized"] = True
        print("Новые военно-морские флоты созданы (включая надводные дроны)")
    except Exception as e:
        print(f"Ошибка при инициализации флотов: {e}")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ СБРОСА ОПЕРАЦИЙ ФЛОТА ====================

def reset_naval_operations(backup: bool = True) -> Dict:
    """
    Сбрасывает только операции флота (блокады и патрули), не затрагивая сами флоты
    """
    import os
    import json
    
    results = {"operations_reset": False, "backup_path": None}
    
    if backup and os.path.exists('naval_operations.json'):
        results["backup_path"] = create_backup("naval_operations_backup", ['naval_operations.json'])
    
    naval_operations_reset_data = {"blockades": {}, "last_update": str(datetime.now())}
    
    try:
        with open('naval_operations.json', 'w', encoding='utf-8') as f:
            json.dump(naval_operations_reset_data, f, ensure_ascii=False, indent=4)
        results["operations_reset"] = True
        print("Файл naval_operations.json сброшен (блокады и патрули очищены)")
    except Exception as e:
        print(f"Ошибка при сбросе naval_operations.json: {e}")
    
    # Также обновляем статус всех флотов в navy.json
    if os.path.exists('navy.json'):
        try:
            with open('navy.json', 'r', encoding='utf-8') as f:
                navy_data = json.load(f)
            
            for fleet in navy_data.get("fleets", []):
                fleet["operation"] = "docked"
                fleet["blockade_targets"] = []
            
            with open('navy.json', 'w', encoding='utf-8') as f:
                json.dump(navy_data, f, ensure_ascii=False, indent=2)
            
            print("Статусы флотов обновлены (операции сброшены)")
        except Exception as e:
            print(f"Ошибка при обновлении статусов флотов: {e}")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ СБРОСА РАДИАЦИИ ====================

def reset_radiation(backup: bool = True) -> Dict:
    """
    Сбрасывает радиоактивное заражение во всех регионах
    """
    import os
    from infra_build import load_infrastructure, save_infrastructure
    
    results = {"radiation_cleared": 0, "backup_path": None}
    
    try:
        infra = load_infrastructure()
        
        if backup and os.path.exists('infrastructure.json'):
            results["backup_path"] = create_backup("infrastructure_backup", ['infrastructure.json'])
        
        cleared_count = 0
        for country_id, country_data in infra.get("infrastructure", {}).items():
            for econ_region, econ_data in country_data.get("economic_regions", {}).items():
                for region_name, region_data in econ_data.get("regions", {}).items():
                    if "radiation" in region_data:
                        del region_data["radiation"]
                        cleared_count += 1
        
        save_infrastructure(infra)
        results["radiation_cleared"] = cleared_count
        print(f"Радиоактивное заражение очищено в {cleared_count} регионах")
        
    except Exception as e:
        print(f"Ошибка при очистке радиации: {e}")
    
    return results


# ==================== ФУНКЦИИ ДЛЯ ПОЛНОГО СБРОСА ИНФРАСТРУКТУРЫ ====================

def reset_infrastructure(backup: bool = True) -> Dict:
    """
    Полный сброс инфраструктуры к исходным значениям из infrastructure_default.json
    """
    import os
    import json
    
    results = {"infrastructure_reset": False, "backup_path": None}
    
    if backup and os.path.exists('infrastructure.json'):
        results["backup_path"] = create_backup("infrastructure_full_backup", ['infrastructure.json'])
    
    if os.path.exists('infrastructure_default.json'):
        try:
            with open('infrastructure_default.json', 'r', encoding='utf-8') as src:
                default_data = json.load(src)
            
            with open('infrastructure.json', 'w', encoding='utf-8') as dst:
                json.dump(default_data, dst, ensure_ascii=False, indent=4)
            
            results["infrastructure_reset"] = True
            print("Инфраструктура сброшена к исходным значениям")
        except Exception as e:
            print(f"Ошибка при сбросе инфраструктуры: {e}")
    else:
        print("Файл infrastructure_default.json не найден")
    
    return results


# ==================== КЛАСС ПОДТВЕРЖДЕНИЯ ====================

class ResetConfirmView(discord.ui.View):
    """View для подтверждения сброса"""
    
    def __init__(self, ctx, reset_type: str, backup: bool = True):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.reset_type = reset_type
        self.backup = backup
        self.value = None
    
    @discord.ui.button(label="ПОДТВЕРДИТЬ", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        self.value = True
        self.stop()
        await interaction.response.defer()
    
    @discord.ui.button(label="ОТМЕНА", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Это не ваше меню!", ephemeral=True)
            return
        
        self.value = False
        self.stop()
        await interaction.response.defer()


# ==================== КОГ ДЛЯ СБРОСА ====================

class ResetCommands(commands.Cog):
    """Ког с командами для сброса государств"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='сброс')
    @commands.has_permissions(administrator=True)
    async def reset_states(self, ctx, backup: str = "yes"):
        """
        Обычный сброс всех государств к исходным значениям (назначения игроков сохраняются)
        Использование: !сброс [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА",
            description=f"Вы уверены, что хотите выполнить **ОБЫЧНЫЙ СБРОС** всех государств?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Тип сброса", value="Обычный (назначения сохраняются)", inline=False)
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Предупреждение",
            value="Все изменения будут потеряны. Это действие нельзя отменить!",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "обычный", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс...", embed=None, view=None)
        await self.perform_reset(ctx, backup_bool, full_reset=False)
    
    @commands.command(name='сброс_полный')
    @commands.has_permissions(administrator=True)
    async def reset_states_full(self, ctx, backup: str = "yes"):
        """
        ПОЛНЫЙ сброс всех государств к исходным значениям (включая назначения игроков)
        Использование: !сброс_полный [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ ПОЛНОГО СБРОСА",
            description=f"Вы уверены, что хотите выполнить **ПОЛНЫЙ СБРОС** всех государств?",
            color=discord.Color.red()
        )
        embed.add_field(name="Тип сброса", value="Полный (все назначения будут сброшены)", inline=False)
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ",
            value="Все игроки будут откреплены от государств. Это действие нельзя отменить!",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "полный", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется полный сброс...", embed=None, view=None)
        await self.perform_reset(ctx, backup_bool, full_reset=True)
    
    @commands.command(name='сброс_трубопроводов')
    @commands.has_permissions(administrator=True)
    async def reset_pipelines(self, ctx, backup: str = "yes"):
        """
        Сброс данных трубопроводов к исходным значениям
        Использование: !сброс_трубопроводов [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА ТРУБОПРОВОДОВ",
            description="Вы уверены, что хотите сбросить данные трубопроводов?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• Все трубопроводы (возврат к исходным данным)\n"
                  "• Очередь строительства и демонтажа\n"
                  "• Логи событий\n"
                  "• Дипломатические соглашения\n"
                  "• Закрытые участки\n"
                  "• Размещённые войска\n"
                  "• Контроль над участками",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "трубопроводы", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс трубопроводов...", embed=None, view=None)
        
        results = reset_pipelines(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс трубопроводов завершён",
            color=0x00ff00
        )
        
        status_text = []
        if results['pipelines_reset']:
            status_text.append("✅ Основные данные трубопроводов сброшены")
        if results['construction_reset']:
            status_text.append("✅ Очередь строительства и демонтажа очищена")
        if results['logs_reset']:
            status_text.append("✅ Логи событий очищены")
        if results['diplomacy_reset']:
            status_text.append("✅ Дипломатические соглашения очищены")
        
        result_embed.add_field(
            name="Результат",
            value="\n".join(status_text) if status_text else "Ничего не изменено",
            inline=False
        )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_населения')
    @commands.has_permissions(administrator=True)
    async def reset_population(self, ctx, backup: str = "yes"):
        """
        Сброс данных населения (специалисты, социальные показатели)
        Использование: !сброс_населения [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА НАСЕЛЕНИЯ",
            description="Вы уверены, что хотите сбросить данные населения?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• Экспортированные специалисты\n"
                  "• Активные запросы на специалистов\n"
                  "• Социальные показатели (счастье, стабильность, доверие, популярность)\n"
                  "• Данные населения будут пересчитаны при следующем обновлении",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "население", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс населения...", embed=None, view=None)
        
        results = reset_population(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс населения завершён",
            color=0x00ff00
        )
        
        status_text = []
        if results['experts_reset']:
            status_text.append("✅ Данные специалистов сброшены")
        if results['population_reset']:
            status_text.append("✅ Социальные показатели восстановлены")
        
        result_embed.add_field(
            name="Результат",
            value="\n".join(status_text) if status_text else "Ничего не изменено",
            inline=False
        )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_корпораций')
    @commands.has_permissions(administrator=True)
    async def reset_corporations(self, ctx, backup: str = "yes"):
        """
        Сброс корпораций к исходным значениям из corporations_starting_data.json
        Использование: !сброс_корпораций [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА КОРПОРАЦИЙ",
            description="Вы уверены, что хотите сбросить данные всех гражданских корпораций?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• Бюджеты корпораций\n• Запасы на складах\n• Популярность\n• Все изменения после запуска бота",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "корпорации", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс корпораций...", embed=None, view=None)
        
        results = reset_corporations(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс корпораций завершён",
            color=0x00ff00
        )
        
        result_embed.add_field(
            name="Результат",
            value=f"Сброшено данных: {results['corps_processed']} корпораций",
            inline=False
        )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_резервов')
    @commands.has_permissions(administrator=True)
    async def reset_reserves(self, ctx, backup: str = "yes"):
        """
        Сброс данных расконсервации техники (возврат к исходным резервам)
        Использование: !сброс_резервов [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА РЕЗЕРВОВ",
            description="Вы уверены, что хотите сбросить данные расконсервации техники?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• Очередь расконсервации\n• Записи о расконсервированной технике\n• Резервы будут восстановлены к исходным значениям (включая надводные дроны)",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "резервы", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс резервов...", embed=None, view=None)
        
        results = reset_reserves_conversion(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс резервов завершён",
            color=0x00ff00
        )
        
        status_text = []
        if results['conversion_queue_reset']:
            status_text.append("Очередь расконсервации очищена")
        if results['reserves_reset']:
            status_text.append("Резервы восстановлены к исходным значениям (включая надводные дроны)")
        if results['activated_reset']:
            status_text.append("Список расконсервированной техники очищен")
        
        result_embed.add_field(
            name="Результат",
            value="\n".join(status_text) if status_text else "Ничего не изменено",
            inline=False
        )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_ударов')
    @commands.has_permissions(administrator=True)
    async def reset_strikes(self, ctx, backup: str = "yes"):
        """
        Сброс данных ударов (очистка истории ударов, очереди и расстояний)
        Поддерживает все типы ударов (инфраструктура, ПВО, флот, торговые конвои)
        Использование: !сброс_ударов [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА УДАРОВ",
            description="Вы уверены, что хотите сбросить данные ударов?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• История ударов (включая удары по ПВО, флоту, торговым конвоям)\n• Очередь ударов\n• Статистика ударов\n• Расстояния между регионами",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "удары", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс ударов...", embed=None, view=None)
        
        results = reset_strikes(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс ударов завершён",
            color=0x00ff00
        )
        
        status_text = []
        if results['strikes_reset']:
            status_text.append("История ударов сброшена")
        if results['queue_reset']:
            status_text.append("Очередь ударов сброшена")
        if results['distances_reset']:
            status_text.append("Расстояния сброшены")
        
        result_embed.add_field(
            name="Результат",
            value="\n".join(status_text) if status_text else "Ничего не изменено",
            inline=False
        )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_спутников')
    @commands.has_permissions(administrator=True)
    async def reset_satellites(self, ctx, backup: str = "yes"):
        """
        Сброс данных о спутниках к исходным значениям
        Использование: !сброс_спутников [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА СПУТНИКОВ",
            description="Вы уверены, что хотите сбросить данные о спутниках?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• Государственные спутники (возврат к реальным данным)\n• Корпоративные спутники (Starlink и другие)\n• Подписки на корпорации\n• Предоставленный доступ к спутникам\n• Блокировки корпораций",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "спутники", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс спутников...", embed=None, view=None)
        
        results = reset_satellites(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс спутников завершён",
            color=0x00ff00
        )
        
        status_text = []
        if results['gov_satellites_reset']:
            status_text.append("✅ Государственные спутники сброшены")
        if results['corp_satellites_reset']:
            status_text.append("✅ Корпоративные спутники сброшены (Starlink и другие)")
        if results['access_reset']:
            status_text.append("✅ Данные доступа и блокировок очищены")
        
        result_embed.add_field(
            name="Результат",
            value="\n".join(status_text) if status_text else "Ничего не изменено",
            inline=False
        )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_торговли')
    @commands.has_permissions(administrator=True)
    async def reset_maritime(self, ctx, backup: str = "yes"):
        """
        Сброс данных морской торговли (корабли и удары по ним)
        Использование: !сброс_торговли [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА ТОРГОВЛИ",
            description="Вы уверены, что хотите сбросить данные морской торговли?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• Торговые корабли\n• Удары по кораблям\n• Очередь ударов\n• Приоритеты экспорта\n• Затем будут созданы новые корабли",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "торговля", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс морской торговли...", embed=None, view=None)
        
        results = reset_maritime_trade(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс морской торговли завершён",
            color=0x00ff00
        )
        
        status_text = []
        if results['ships_reset']:
            status_text.append("Корабли сброшены")
        if results['strikes_reset']:
            status_text.append("Удары сброшены")
        if results['initialized']:
            status_text.append("Новые корабли созданы")
        
        result_embed.add_field(
            name="Результат",
            value="\n".join(status_text) if status_text else "Ничего не изменено",
            inline=False
        )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_флота')
    @commands.has_permissions(administrator=True)
    async def reset_navy(self, ctx, backup: str = "yes"):
        """
        Сброс данных военно-морского флота (включая блокады, патрули и надводные дроны)
        Использование: !сброс_флота [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА ФЛОТА",
            description="Вы уверены, что хотите сбросить данные военно-морского флота?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• Все флоты (включая надводные дроны)\n• Позиции флотов\n• Блокады\n• Патрулирование\n• Затем будут созданы новые флоты",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "флот", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс флота...", embed=None, view=None)
        
        results = reset_navy(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс флота завершён",
            color=0x00ff00
        )
        
        status_text = []
        if results['navy_reset']:
            status_text.append("Данные флота сброшены (включая надводные дроны)")
        if results['operations_reset']:
            status_text.append("Блокады и патрули сброшены")
        if results['initialized']:
            status_text.append("Новые флоты созданы")
        
        result_embed.add_field(
            name="Результат",
            value="\n".join(status_text) if status_text else "Ничего не изменено",
            inline=False
        )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_операций')
    @commands.has_permissions(administrator=True)
    async def reset_naval_operations(self, ctx, backup: str = "yes"):
        """
        Сброс только операций флота (блокады и патрули), сами флоты не трогает
        Использование: !сброс_операций [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА ОПЕРАЦИЙ",
            description="Вы уверены, что хотите сбросить операции флота?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• Все активные блокады\n• Все активные патрули\n• Флоты вернутся в режим ожидания",
            inline=False
        )
        embed.add_field(
            name="Что НЕ будет сброшено",
            value="• Состав флотов\n• Позиции флотов\n• Корабли (включая надводные дроны)",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "операции", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс операций...", embed=None, view=None)
        
        results = reset_naval_operations(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс операций завершён",
            color=0x00ff00
        )
        
        if results['operations_reset']:
            result_embed.add_field(
                name="Результат",
                value="Все блокады и патрули сброшены. Флоты вернулись в режим ожидания.",
                inline=False
            )
        else:
            result_embed.add_field(
                name="Результат",
                value="Не удалось сбросить операции.",
                inline=False
            )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_радиации')
    @commands.has_permissions(administrator=True)
    async def reset_radiation(self, ctx, backup: str = "yes"):
        """
        Очистка радиоактивного заражения во всех регионах
        Использование: !сброс_радиации [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ ОЧИСТКИ РАДИАЦИИ",
            description="Вы уверены, что хотите очистить радиоактивное заражение во всех регионах?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сделано",
            value="• Удаление радиоактивного заражения из всех регионов\n• Восстановление нормальной жизни",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "радиация", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Очистка отменена.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Очистка отменена.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется очистка радиации...", embed=None, view=None)
        
        results = reset_radiation(backup_bool)
        
        result_embed = discord.Embed(
            title="Очистка радиации завершена",
            color=0x00ff00
        )
        
        result_embed.add_field(
            name="Результат",
            value=f"Очищено регионов: {results['radiation_cleared']}",
            inline=False
        )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='сброс_инфраструктуры')
    @commands.has_permissions(administrator=True)
    async def reset_infrastructure(self, ctx, backup: str = "yes"):
        """
        Полный сброс инфраструктуры к исходным значениям
        Использование: !сброс_инфраструктуры [yes/no]
        """
        backup_bool = backup.lower() == "yes"
        
        embed = discord.Embed(
            title="ПОДТВЕРЖДЕНИЕ СБРОСА ИНФРАСТРУКТУРЫ",
            description="Вы уверены, что хотите сбросить инфраструктуру к исходным значениям?",
            color=discord.Color.orange()
        )
        embed.add_field(name="Резервное копирование", value="Да" if backup_bool else "Нет", inline=False)
        embed.add_field(
            name="Что будет сброшено",
            value="• Все постройки\n• Фабрики\n• Электростанции\n• Все улучшения",
            inline=False
        )
        
        view = ResetConfirmView(ctx, "инфраструктура", backup_bool)
        msg = await ctx.send(embed=embed, view=view)
        
        await view.wait()
        
        if view.value is None:
            await msg.edit(content="Время ожидания истекло. Сброс отменён.", embed=None, view=None)
            return
        elif not view.value:
            await msg.edit(content="Сброс отменён.", embed=None, view=None)
            return
        
        await msg.edit(content="Выполняется сброс инфраструктуры...", embed=None, view=None)
        
        results = reset_infrastructure(backup_bool)
        
        result_embed = discord.Embed(
            title="Сброс инфраструктуры завершён",
            color=0x00ff00
        )
        
        if results['infrastructure_reset']:
            result_embed.add_field(
                name="Результат",
                value="Инфраструктура сброшена к исходным значениям.",
                inline=False
            )
        else:
            result_embed.add_field(
                name="Результат",
                value="Не удалось сбросить инфраструктуру. Файл infrastructure_default.json не найден.",
                inline=False
            )
        
        if results["backup_path"]:
            result_embed.add_field(
                name="Резервная копия",
                value=f"Сохранена в: `{results['backup_path']}`",
                inline=False
            )
        
        await ctx.send(embed=result_embed)
    
    @commands.command(name='синхронизировать_пво')
    @commands.has_permissions(administrator=True)
    async def sync_pvo(self, ctx):
        """
        Синхронизирует ПВО между арсеналом и инфраструктурой.
        Списывает из арсенала всё ПВО, которое уже установлено в регионах.
        """
        embed = discord.Embed(
            title="СИНХРОНИЗАЦИЯ ПВО",
            description="Выполняется синхронизация ПВО между арсеналом и инфраструктурой...",
            color=discord.Color.blue()
        )
        msg = await ctx.send(embed=embed)
        
        results = sync_all_countries_pvo()
        
        result_embed = discord.Embed(
            title="Синхронизация ПВО завершена",
            color=0x00ff00 if results["total_pvo_removed"] > 0 else discord.Color.blue()
        )
        
        result_embed.add_field(
            name="Результат",
            value=f"Обработано стран: {results['total_countries']}\n"
                  f"Обновлено стран: {results['countries_updated']}\n"
                  f"Списано ПВО из арсенала: {results['total_pvo_removed']}",
            inline=False
        )
        
        if results["details"]:
            details_text = ""
            for country, pvo_types in list(results["details"].items())[:10]:
                types_text = ", ".join([f"{t}: {c}" for t, c in pvo_types.items() if c > 0])
                details_text += f"• {country}: {types_text}\n"
            if details_text:
                result_embed.add_field(
                    name="Детали по странам",
                    value=details_text[:1024],
                    inline=False
                )
        
        await msg.edit(embed=result_embed)
    
    async def perform_reset(self, ctx, backup: bool, full_reset: bool):
        """Общая функция для выполнения полного сброса"""
        from corruption import STARTING_CORRUPTION
        import os
        import json
        import shutil
        from datetime import datetime
        
        if not ORIGINAL_STATES:
            await ctx.send("Ошибка: файл states_default.json не найден или пуст!")
            return
        
        # ============ СОХРАНЯЕМ НАЗНАЧЕНИЯ ПЕРЕД СБРОСОМ (ТОЛЬКО ДЛЯ ОБЫЧНОГО СБРОСА) ============
        
        assignments = {}
        if not full_reset:
            current_states = load_states()
            for state_id, data in current_states.get("players", {}).items():
                if "assigned_to" in data:
                    assignments[state_id] = {
                        "assigned_to": data["assigned_to"],
                        "assigned_at": data.get("assigned_at", str(datetime.now()))
                    }
        
        # ============ СПИСОК ВСЕХ ФАЙЛОВ ДЛЯ СБРОСА ============
        
        player_data_files = {
            'research_data.json': {'players': {}},
            'strikes.json': {'strikes': [], 'stats': {}},
            'strike_queue.json': {'active_strikes': [], 'completed_strikes': []},
            'trades.json': {'active_trades': [], 'completed_trades': []},
            'transfers.json': {'active_transfers': [], 'completed_transfers': []},
            'alliances.json': {'alliances': []},
            'mobilization.json': {'active_programs': [], 'completed_programs': []},
            'satellites.json': {'satellites': {}},
            'doctrines.json': {'active_doctrines': [], 'completed_doctrines': []},
            'focuses.json': {'active_focuses': [], 'completed_focuses': []},
            'infra_construction.json': {'active_projects': [], 'completed_projects': []}
        }
        
        new_system_files = {
            'central_bank.json': {'banks': {}},
            'production_queue.json': {'active_orders': [], 'completed_orders': []},
            'civil_production_queue.json': {'active_orders': [], 'completed_orders': []}
        }
        
        corruption_data = {"countries": {}}
        for country, level in STARTING_CORRUPTION.items():
            corruption_data["countries"][country] = {
                "level": level,
                "history": [{
                    "date": str(datetime.now()),
                    "level": level,
                    "reason": "Начальное значение после сброса"
                }],
                "last_update": str(datetime.now()),
                "total_stolen": 0,
                "anti_corruption_efforts": 0,
                "last_campaign": None,
                "campaign_count": 0,
                "public_trust": 50
            }
        
        tariffs_reset_data = None
        if os.path.exists('tariffs_default.json'):
            try:
                with open('tariffs_default.json', 'r', encoding='utf-8') as f:
                    tariffs_reset_data = json.load(f)
            except Exception as e:
                await ctx.send(f"Ошибка при чтении tariffs_default.json: {e}")
        elif os.path.exists('tariffs.json'):
            try:
                with open('tariffs.json', 'r', encoding='utf-8') as f:
                    tariffs_reset_data = json.load(f)
            except Exception as e:
                await ctx.send(f"Ошибка при чтении tariffs.json: {e}")
        
        infrastructure_reset_data = None
        if os.path.exists('infrastructure_default.json'):
            try:
                with open('infrastructure_default.json', 'r', encoding='utf-8') as f:
                    infrastructure_reset_data = json.load(f)
            except Exception as e:
                await ctx.send(f"Ошибка при чтении infrastructure_default.json: {e}")
        
        all_files = (list(player_data_files.keys()) + 
                    list(new_system_files.keys()) + 
                    ['states.json', 'corruption.json', 'tariffs.json', 'infrastructure.json',
                     'maritime_data.json', 'ship_strikes.json', 'ship_strike_queue.json',
                     'priority_regions.json', 'navy.json', 'naval_operations.json',
                     'conversion_queue.json', 'reserves.json', 'corporations_state.json',
                     'distances.json', 'corporate_satellites.json', 'satellite_access.json',
                     'pipelines.json', 'pipeline_construction.json', 'pipeline_logs.json', 'pipeline_diplomacy.json',
                     'exported_experts.json', 'expert_requests.json'])
        
        if backup:
            backup_path = create_backup("full_reset_backup", all_files)
            await ctx.send(f"Создана резервная копия в папке: `{backup_path}`")
        
        # ============ СБРОС ГОСУДАРСТВ (ПОЛНАЯ ПЕРЕЗАПИСЬ ИЗ states_default.json) ============
        
        new_states = {"players": {}}
        for state_id, original_data in ORIGINAL_STATES.items():
            new_states["players"][state_id] = original_data.copy()
        
        # Восстанавливаем назначения при обычном сбросе
        if not full_reset:
            for state_id, assignment in assignments.items():
                if state_id in new_states["players"]:
                    new_states["players"][state_id]["assigned_to"] = assignment["assigned_to"]
                    new_states["players"][state_id]["assigned_at"] = assignment["assigned_at"]
        
        save_states(new_states)
        
        if full_reset:
            await ctx.send("1/17: Государства сброшены (включая назначения)")
        else:
            await ctx.send("1/17: Государства сброшены (назначения сохранены)")
        
        # ============ СБРОС ИГРОВЫХ ДАННЫХ ============
        
        reset_count = 0
        for filename, default_content in player_data_files.items():
            if filename != 'states.json':
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(default_content, f, ensure_ascii=False, indent=4)
                    reset_count += 1
                except Exception as e:
                    await ctx.send(f"Ошибка при сбросе {filename}: {e}")
        
        await ctx.send(f"2/17: Игровые данные сброшены ({reset_count} файлов)")
        
        # ============ СБРОС НОВЫХ СИСТЕМ ============
        
        new_systems_count = 0
        for filename, default_content in new_system_files.items():
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(default_content, f, ensure_ascii=False, indent=4)
                new_systems_count += 1
            except Exception as e:
                await ctx.send(f"Ошибка при сбросе {filename}: {e}")
        
        await ctx.send(f"3/17: Новые системы сброшены ({new_systems_count} файлов)")
        
        # ============ СБРОС КОРРУПЦИИ ============
        
        try:
            with open('corruption.json', 'w', encoding='utf-8') as f:
                json.dump(corruption_data, f, ensure_ascii=False, indent=4)
            await ctx.send("4/17: Данные коррупции сброшены к исходным значениям")
        except Exception as e:
            await ctx.send(f"Ошибка при сбросе corruption.json: {e}")
        
        # ============ СБРОС ТАРИФОВ ============
        
        if tariffs_reset_data:
            try:
                with open('tariffs.json', 'w', encoding='utf-8') as f:
                    json.dump(tariffs_reset_data, f, ensure_ascii=False, indent=4)
                await ctx.send("5/17: Тарифная система сброшена к исходным значениям")
            except Exception as e:
                await ctx.send(f"Ошибка при сбросе tariffs.json: {e}")
        else:
            await ctx.send("Нет данных для сброса тарифов, tariffs.json не изменён")
        
        # ============ СБРОС ИНФРАСТРУКТУРЫ ============
        
        if infrastructure_reset_data:
            try:
                with open('infrastructure.json', 'w', encoding='utf-8') as f:
                    json.dump(infrastructure_reset_data, f, ensure_ascii=False, indent=4)
                await ctx.send("6/17: Инфраструктура сброшена к исходным значениям")
            except Exception as e:
                await ctx.send(f"Ошибка при сбросе infrastructure.json: {e}")
        else:
            await ctx.send("Файл infrastructure_default.json не найден, инфраструктура НЕ сброшена")
        
        # ============ СБРОС КОРПОРАЦИЙ ============
        
        corp_results = reset_corporations(backup=False)
        await ctx.send(f"7/17: Корпорации сброшены ({corp_results['corps_processed']} корпораций)")
        
        # ============ СБРОС РАСКОНСЕРВАЦИИ ============
        
        reserves_results = reset_reserves_conversion(backup=False)
        await ctx.send("8/17: Данные расконсервации техники сброшены (включая надводные дроны)")
        
        # ============ СБРОС УДАРОВ ============
        
        strikes_results = reset_strikes(backup=False)
        await ctx.send("9/17: Данные ударов сброшены (включая все типы целей)")
        
        # ============ СБРОС СПУТНИКОВ ============
        
        satellite_results = reset_satellites(backup=False)
        await ctx.send("10/17: Данные спутников сброшены (государственные, корпоративные, доступ)")
        
        # ============ СБРОС МОРСКОЙ ТОРГОВЛИ ============
        
        maritime_results = reset_maritime_trade(backup=False)
        maritime_text = []
        if maritime_results['ships_reset']:
            maritime_text.append("Корабли сброшены")
        if maritime_results['strikes_reset']:
            maritime_text.append("Удары сброшены")
        if maritime_results['initialized']:
            maritime_text.append("Новые корабли созданы")
        
        maritime_status = "\n".join(maritime_text) if maritime_text else "Морская торговля в порядке"
        await ctx.send(f"11/17: Морская торговля сброшена\n{maritime_status}")
        
        # ============ СБРОС ВОЕННО-МОРСКОГО ФЛОТА ============
        
        navy_results = reset_navy(backup=False)
        navy_text = []
        if navy_results['navy_reset']:
            navy_text.append("Данные флота сброшены (включая надводные дроны)")
        if navy_results['operations_reset']:
            navy_text.append("Блокады и патрули сброшены")
        if navy_results['initialized']:
            navy_text.append("Новые флоты созданы")
        
        navy_status = "\n".join(navy_text) if navy_text else "Флот в порядке"
        await ctx.send(f"12/17: Военно-морской флот сброшен\n{navy_status}")
        
        # ============ СБРОС ТРУБОПРОВОДОВ ============
        
        pipeline_results = reset_pipelines(backup=False)
        pipeline_text = []
        if pipeline_results['pipelines_reset']:
            pipeline_text.append("Трубопроводы сброшены к исходным данным")
        if pipeline_results['construction_reset']:
            pipeline_text.append("Очередь строительства очищена")
        if pipeline_results['logs_reset']:
            pipeline_text.append("Логи событий очищены")
        if pipeline_results['diplomacy_reset']:
            pipeline_text.append("Дипломатические соглашения очищены")
        
        pipeline_status = "\n".join(pipeline_text) if pipeline_text else "Трубопроводы в порядке"
        await ctx.send(f"13/17: Трубопроводная система сброшена\n{pipeline_status}")
        
        # ============ СБРОС НАСЕЛЕНИЯ ============
        
        population_results = reset_population(backup=False)
        population_text = []
        if population_results['experts_reset']:
            population_text.append("Данные специалистов сброшены")
        if population_results['population_reset']:
            population_text.append("Социальные показатели восстановлены")
        
        population_status = "\n".join(population_text) if population_text else "Население в порядке"
        await ctx.send(f"14/17: Данные населения сброшены\n{population_status}")
        
        # ============ ОЧИСТКА РАДИАЦИИ ============
        
        radiation_results = reset_radiation(backup=False)
        await ctx.send(f"15/17: Очищено регионов от радиации: {radiation_results['radiation_cleared']}")
        
        # ============ ОЧИСТКА СТАРЫХ ПРОИЗВОДСТВЕННЫХ ОЧЕРЕДЕЙ ============
        
        extra_queues = ['infra_construction.json', 'focuses.json', 'doctrines.json']
        for queue_file in extra_queues:
            if os.path.exists(queue_file):
                try:
                    if "infra" in queue_file:
                        default_content = {"active_projects": [], "completed_projects": []}
                    elif "focus" in queue_file:
                        default_content = {"active_focuses": [], "completed_focuses": []}
                    else:
                        default_content = {"active_doctrines": [], "completed_doctrines": []}
                    with open(queue_file, 'w', encoding='utf-8') as f:
                        json.dump(default_content, f, ensure_ascii=False, indent=4)
                except Exception as e:
                    await ctx.send(f"Ошибка при сбросе {queue_file}: {e}")
        
        await ctx.send("16/17: Все очереди производства очищены")
        
        # ============ СИНХРОНИЗАЦИЯ ПВО ============
        
        pvo_sync_results = sync_all_countries_pvo()
        await ctx.send(f"17/17: Синхронизация ПВО завершена (списано {pvo_sync_results['total_pvo_removed']} единиц из арсенала)")
        
        # ============ ЛОГИРОВАНИЕ ============
        
        try:
            channel = self.bot.get_channel(ADMIN_LOG_CHANNEL_ID)
            if channel:
                reset_type = "ПОЛНЫЙ сброс" if full_reset else "ОБЫЧНЫЙ сброс"
                await channel.send(f"**Админ {ctx.author.name}** выполнил {reset_type} сервера")
        except:
            pass
        
        # Итоговое сообщение
        reset_type_text = "ПОЛНЫЙ СБРОС (включая назначения)" if full_reset else "ОБЫЧНЫЙ СБРОС (назначения сохранены)"
        
        embed = discord.Embed(
            title=f"{reset_type_text} ЗАВЕРШЁН",
            description="Все данные успешно восстановлены к исходным значениям",
            color=0x00ff00
        )
        
        embed.add_field(
            name="Статистика сброса",
            value=f"• Государства: {len(ORIGINAL_STATES)}\n"
                  f"• Игровых файлов: {reset_count}\n"
                  f"• Новых систем: {new_systems_count}\n"
                  f"• Коррупция: 1 файл\n"
                  f"• Тарифы: 1 файл\n"
                  f"• Инфраструктура: 1 файл\n"
                  f"• Корпорации: {corp_results['corps_processed']} корпораций\n"
                  f"• Расконсервация: сброшена (включая надводные дроны)\n"
                  f"• Удары: сброшены (включая все типы целей)\n"
                  f"• Спутники: сброшены (государственные, корпоративные, доступ)\n"
                  f"• Морская торговля: 4 файла + инициализация\n"
                  f"• Военно-морской флот: 2 файла + инициализация (включая надводные дроны)\n"
                  f"• Трубопроводы: 4 файла сброшены\n"
                  f"• Население: 2 файла сброшены\n"
                  f"• Очищено регионов от радиации: {radiation_results['radiation_cleared']}\n"
                  f"• Синхронизация ПВО: списано {pvo_sync_results['total_pvo_removed']} единиц",
            inline=False
        )
        
        if not full_reset:
            embed.add_field(
                name="Назначения",
                value="Назначения игроков сохранены",
                inline=False
            )
        else:
            embed.add_field(
                name="Назначения",
                value="Все назначения игроков сброшены",
                inline=False
            )
        
        embed.add_field(
            name="Трубопроводы",
            value="Трубопроводная система сброшена к исходным данным. Все трубопроводы активны.",
            inline=False
        )
        
        embed.add_field(
            name="Население",
            value="Социальные показатели восстановлены. Данные специалистов очищены.",
            inline=False
        )
        
        await ctx.send(embed=embed)


# ==================== ЭКСПОРТ ====================

async def setup(bot):
    await bot.add_cog(ResetCommands(bot))

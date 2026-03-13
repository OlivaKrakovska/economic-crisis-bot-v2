# generate_distances.py

import json
import math
from region_coordinates import REGION_COORDINATES

def haversine_distance(lat1, lon1, lat2, lon2):
    """Рассчитывает расстояние между двумя точками на Земле"""
    R = 6371  # Радиус Земли в км
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat/2)**2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return round(R * c)

def generate_all_distances():
    """Генерирует расстояния между всеми регионами всех стран"""
    distances = {}
    countries = list(REGION_COORDINATES.keys())
    
    print(f"Найдено стран: {len(countries)}")
    print(f"Всего регионов: {sum(len(regions) for regions in REGION_COORDINATES.values())}")
    
    total_pairs = 0
    
    for attacker_country in countries:
        distances[attacker_country] = {}
        attacker_regions = REGION_COORDINATES[attacker_country]
        
        for target_country in countries:
            if attacker_country == target_country:
                continue  # Пропускаем расстояния внутри одной страны
                
            distances[attacker_country][target_country] = {}
            target_regions = REGION_COORDINATES[target_country]
            
            print(f"Генерация: {attacker_country} -> {target_country}")
            
            # Для каждого региона атакующей страны
            for attacker_region, attacker_coords in attacker_regions.items():
                # Находим ближайший регион в целевой стране
                min_distance = float('inf')
                
                for target_region, target_coords in target_regions.items():
                    dist = haversine_distance(
                        attacker_coords["lat"], attacker_coords["lon"],
                        target_coords["lat"], target_coords["lon"]
                    )
                    
                    if dist < min_distance:
                        min_distance = dist
                
                if min_distance != float('inf'):
                    distances[attacker_country][target_country][attacker_region] = min_distance
                    total_pairs += 1
    
    print(f"\n✅ Сгенерировано {total_pairs} пар расстояний")
    return distances

def save_distances(distances):
    """Сохраняет расстояния в файл в нужном формате"""
    output = {"distances": distances}
    
    with open('distances.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=4)
    
    print("✅ Файл distances.json успешно создан!")

if __name__ == "__main__":
    print("🚀 Начинаю генерацию расстояний...")
    distances = generate_all_distances()
    save_distances(distances)
    
    # Статистика
    print("\n📊 Статистика:")
    for country, targets in distances.items():
        regions_count = len(REGION_COORDINATES[country])
        targets_count = len(targets)
        print(f"  {country}: {regions_count} регионов, связи с {targets_count} странами")

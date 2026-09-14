import json
from functools import lru_cache
from typing import Dict, List, Tuple

from .config import CITIES_PATH, PROVINCES_PATH


@lru_cache(maxsize=1)
def load_locations() -> Tuple[List[Dict], Dict[int, List[Dict]]]:
    provinces_data = json.loads(PROVINCES_PATH.read_text(encoding='utf-8'))
    cities_data = json.loads(CITIES_PATH.read_text(encoding='utf-8'))

    provinces = provinces_data.get('provinces', []) if isinstance(provinces_data, dict) else []
    provinces = sorted(provinces, key=lambda item: item.get('name', ''))

    cities_by_province: Dict[int, List[Dict]] = {}
    for province in cities_data:
        province_id = int(province.get('id'))
        cities = province.get('cities', []) or []
        cities_by_province[province_id] = sorted(cities, key=lambda item: item.get('name', ''))

    return provinces, cities_by_province


def get_provinces() -> List[Dict]:
    provinces, _ = load_locations()
    return provinces


def get_cities_by_province(province_id: int) -> List[Dict]:
    _, cities_by_province = load_locations()
    return cities_by_province.get(int(province_id), [])

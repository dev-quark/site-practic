import json
from pathlib import Path
from typing import List, Dict

class ConfigLoader:
    """Загружает базы компонентов из ваших конкретных JSON файлов"""
    
    def __init__(self, base_path: str = "./data"):
        self.base_path = Path(base_path)
        self.data = {}
    
    def load_all(self) -> Dict[str, List]:
        """
        Загружает компоненты по вашим названиям файлов:
        cpu.json, motherboard.json, OZU.json, etc.
        """
        
        mapping = {
            "cpu": "cpu.json",
            "motherboard": "motherboard.json",
            "ram": "OZU.json",        # OZU = RAM
            "graphics_card": "video_card.json",
            "power_supply": "PowerCub.json",
            "storage": "PZU.json",     # PZU = Storage
            "cooler": "Cooler.json",
            "case": "frame.json"       # Frame = Case
        }
        
        for key, filename in mapping.items():
            filepath = self.base_path / filename
            
            if not filepath.exists():
                print(f"⚠️ Внимание: Файл '{filename}' не найден!")
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = json.load(f)
                    
                    # Если в файле список или объект — приводим к списку
                    if isinstance(content, list):
                        self.data[key] = content
                    else:
                        self.data[key] = [content]
                        
            except json.JSONDecodeError as e:
                print(f"❌ Ошибка чтения '{filename}': {str(e)}")
                
        return self.data
    
    def get_components(self) -> Dict[str, List]:
        """Готовая ссылка на загруженные данные"""
        return self.data
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from config_loader import ConfigLoader


class CompatibilityError(Enum):
    """Типы ошибок совместимости"""
    SOCKET_MISMATCH = "Неверный сокет процессора"
    RAM_TYPE_MISMATCH = "Несовместимый тип памяти"
    RAM_SPEED_UNSUPPORTED = "Частота памяти слишком высокая для платы"
    GPU_LENGTH_LIMIT = "Длина видеокарты не помещается в корпус"
    PSU_POWER_INSUFFICIENT = "Мощность блока питания недостаточна"
    CASE_FORM_FACTOR_MISMATCH = "Размер материнской платы не подходит к корпусу"


@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[CompatibilityError]
    warnings: List[str]
    
    def to_dict(self):
        return {
            "valid": self.is_valid,
            "errors": [e.value for e in self.errors],
            "warnings": self.warnings
        }

class CompatibilityChecker:
    """Главная логика проверки совместимости"""
    
    def __init__(self):
        self.loader = ConfigLoader()
        self.components = self.loader.load_all()
    
    @classmethod
    def validate_cpu_motherboard(cls, cpu: dict, motherboard: dict) -> ValidationResult:
        """Проверяет совпадение сокета процессора и платы"""
        errors = []
        warnings = []
        
        cpu_sockets = set(cpu.get("compatible_with_processors", []))
        mb_supported = set(motherboard.get("compatible_with_processors", []))
        
        intersection = cpu_sockets & mb_supported
        
        if not intersection:
            errors.append(CompatibilityError.SOCKET_MISMATCH)
            warnings.append(f"CPU требует: {cpu.get('socket_type', 'Unknown')}")
            warnings.append(f"Материнская плата поддерживает: {list(mb_supported)}")
        else:
            warnings.append(f"✅ Совпадение: {list(intersection)[0]}")
            
        return cls._make_result(len(errors) == 0, errors, warnings)
    
    @classmethod
    def validate_ram(cls, ram: dict, motherboard: dict) -> ValidationResult:
        """Проверяет тип и частоту памяти"""
        errors = []
        warnings = []
        
        ram_type = ram.get("type", "").upper()
        mb_ram_type = motherboard.get("ram_type", "").upper()
        
        if ram_type != mb_ram_type:
            errors.append(CompatibilityError.RAM_TYPE_MISMATCH)
            warnings.append(f"RAM ({ram_type}) ≠ Плата ({mb_ram_type})")
        
        speed = ram.get("speed_mhz", 0)
        max_speed = motherboard.get("max_ram_speed_mhz", 3200)
        
        if speed > max_speed:
            warnings.append(f"⚠ Частота RAM ({speed} MHz) > Макс. платы ({max_speed} MHz)")
            warnings.append("Система будет работать на пониженной частоте или требовать разгона BIOS.")
        
        capacity = ram.get("total_capacity_gb", 0)
        max_cap = motherboard.get("max_ram_capacity_gb", 64)
        
        if capacity > max_cap:
            errors.append("❌ Объём RAM превышает лимит материнской платы")
            warnings.append(f"Установлено: {capacity} GB | Максимум: {max_cap} GB")
            
        return cls._make_result(len(errors) == 0, errors, warnings)
    
    @classmethod
    def validate_gpu_case(cls, gpu: dict, case: dict) -> ValidationResult:
        """Проверяет влезание видеокарты в корпус"""
        errors = []
        warnings = []
        
        gpu_len = gpu.get("length_mm", 0)
        case_max_len = case.get("gpu_max_length_mm", 0)
        
        if gpu_len > case_max_len:
            errors.append(CompatibilityError.GPU_LENGTH_LIMIT)
            diff = gpu_len - case_max_len
            warnings.append(f"❌ Видеокарта длиннее корпуса на {diff} мм")
            
        # Проверка высоты кулера процессора (если есть)
        cooler_height = case.get("cpu_cooler_max_height_mm", 0)
        # Здесь можно добавить проверку радиатора AIO
        
        return cls._make_result(len(errors) == 0, errors, warnings)
    
    @classmethod
    def validate_psu(cls, psu: dict, components: list) -> ValidationResult:
        """Проверяет мощность блока питания"""
        errors = []
        warnings = []
        
        psu_power = psu.get("total_wattage_watts", 0)
        
        # Расчет потребления системы
        estimated_consumption = 200  # Базовое потребление
        estimated_consumption += sum(c.get("tgp_watts", c.get("tdp_watts", 0)) for c in components)
        
        if psu_power < estimated_consumption:
            errors.append(CompatibilityError.PSU_POWER_INSUFFICIENT)
            warnings.append(f"❌ БП ({psu_power}W) < Требуется (~{estimated_consumption}W)")
        elif psu_power < estimated_consumption * 1.25:
            warnings.append(f"⚠️ Рекомендуется увеличить запас мощности до ~{int(estimated_consumption * 1.25)} Вт")
            
        return cls._make_result(len(errors) == 0, errors, warnings)
    
    @staticmethod
    def _make_result(valid: bool, errors: List, warnings: List) -> ValidationResult:
        return ValidationResult(is_valid=valid, errors=errors, warnings=warnings)
    
    def check_build_compatibility(self, user_selection: Dict) -> Dict:
        """
        Основная функция проверки сборки пользователя
        Принимает словарь выбора пользователя:
        {"cpu_id": "...", "gpu_id": "...", ...}
        Возвращает детальный отчет о совместимости
        """
        
        results = {}
        
        # Извлекаем объекты из базы
        cpu = next((c for c in self.components["cpu"] if c.get("id") == user_selection.get("cpu_id")), None)
        motherboard = next((c for c in self.components["motherboard"] if c.get("id") == user_selection.get("motherboard_id")), None)
        ram = next((c for c in self.components["ram"] if c.get("id") == user_selection.get("ram_id")), None)
        gpu = next((c for c in self.components["graphics_card"] if c.get("id") == user_selection.get("gpu_id")), None)
        psu = next((c for c in self.components["power_supply"] if c.get("id") == user_selection.get("psu_id")), None)
        case = next((c for c in self.components["case"] if c.get("id") == user_selection.get("case_id")), None)
        
        if not all([cpu, motherboard]):
            return {"valid": False, "error": "Компоненты CPU/Motherboard не найдены"}
        
        # Проверки
        results["cpu_mb"] = self.validate_cpu_motherboard(cpu, motherboard)
        
        if ram:
            results["ram"] = self.validate_ram(ram, motherboard)
            
        if gpu and case:
            results["gpu_case"] = self.validate_gpu_case(gpu, case)
            
        if psu:
            results["psu"] = self.validate_psu(psu, [cpu, gpu] if gpu else [cpu])
            
        all_errors_sum = sum(len(r.errors) for r in results.values())
        
        return {
            "build_valid": all_errors_sum == 0,
            "details": {k: v.to_dict() for k, v in results.items()},
            "total_warnings": sum(len(r.warnings) for r in results.values())
        }
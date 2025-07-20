#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
統一配置管理模組
提供全專案的配置管理和依賴注入
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Type, TypeVar, Generic
from dataclasses import dataclass, field
import logging

T = TypeVar('T')


@dataclass
class ProcessingConfig:
    """處理相關配置"""
    pdf_engine: str = "pdfplumber"
    ocr_engine: str = "paddleocr"
    ocr_confidence_threshold: float = 0.4
    ocr_use_gpu: bool = True
    extract_tables: bool = True
    extract_text: bool = True
    max_retry: int = 3
    timeout: int = 30


@dataclass
class PathConfig:
    """路徑相關配置"""
    base_dir: Path = field(default_factory=lambda: Path.cwd())
    data_dir: str = "data"
    output_dir: str = "data/financial_reports"
    processed_dir: str = "data/processed"
    test_output_dir: str = "data/test_results"
    backup_dir: str = "data/backup"
    log_dir: str = "logs"
    
    def __post_init__(self):
        """確保路徑是絕對路徑"""
        if not isinstance(self.base_dir, Path):
            self.base_dir = Path(self.base_dir)
        
    @property
    def absolute_data_dir(self) -> Path:
        return self.base_dir / self.data_dir
    
    @property
    def absolute_output_dir(self) -> Path:
        return self.base_dir / self.output_dir
    
    @property
    def absolute_processed_dir(self) -> Path:
        return self.base_dir / self.processed_dir


@dataclass
class AppConfig:
    """應用程式主配置"""
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    auto_validation: bool = True
    generate_json: bool = True
    download_delay: int = 2
    debug_mode: bool = False
    log_level: str = "INFO"


class ConfigManager:
    """統一配置管理器 - 向後相容性類別"""
    
    _instance: Optional['ConfigManager'] = None
    _config: Optional[AppConfig] = None
    
    def __new__(cls) -> 'ConfigManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._config = self._load_default_config()
    
    @property
    def config(self) -> AppConfig:
        """獲取當前配置"""
        return self._config
    
    def _load_default_config(self) -> AppConfig:
        """載入預設配置"""
        return AppConfig(
            processing=ProcessingConfig(),
            paths=PathConfig(base_dir=Path(__file__).parent.parent.parent),
            auto_validation=True,
            generate_json=True,
            download_delay=2,
            debug_mode=False,
            log_level="INFO"
        )
    
    @staticmethod
    def load_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
        """靜態方法：載入配置 (向後相容性) - 返回字典格式"""
        config_dict = {
            'output_dir': 'data/financial_reports',
            'processed_dir': 'data/processed',
            'download_delay': 2,
            'max_retry': 3,
            'timeout': 30,
            'use_ocr': True,
            'ocr_engine': 'paddleocr',
            'use_gpu': True,
            'confidence_threshold': 0.4,
            'auto_validation': True,
            'generate_json': True,
            'debug_mode': False,
            'log_level': 'INFO'
        }
        
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    custom_config = json.load(f)
                    config_dict.update(custom_config)
                logging.info(f"已載入配置檔案: {config_path}")
            except Exception as e:
                logging.error(f"載入配置檔案失敗: {e}")
        
        return config_dict


class ServiceRegistry(Generic[T]):
    """服務註冊器 - 實現依賴注入"""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
    
    def register(self, name: str, service: T) -> None:
        """註冊服務實例"""
        self._services[name] = service
    
    def register_factory(self, name: str, factory: callable) -> None:
        """註冊服務工廠函數"""
        self._factories[name] = factory
    
    def get(self, name: str) -> T:
        """獲取服務"""
        if name in self._services:
            return self._services[name]
        
        if name in self._factories:
            service = self._factories[name]()
            self._services[name] = service
            return service
        
        raise ValueError(f"服務未註冊: {name}")
    
    def has(self, name: str) -> bool:
        """檢查服務是否存在"""
        return name in self._services or name in self._factories


# 全域配置和服務管理器
_global_config: Optional[AppConfig] = None
service_registry = ServiceRegistry()


def get_config() -> AppConfig:
    """獲取全域配置"""
    global _global_config
    if _global_config is None:
        _global_config = AppConfig(
            processing=ProcessingConfig(),
            paths=PathConfig(base_dir=Path(__file__).parent.parent.parent),
            auto_validation=True,
            generate_json=True,
            download_delay=2,
            debug_mode=False,
            log_level="INFO"
        )
    return _global_config


def get_service(name: str) -> Any:
    """獲取服務"""
    return service_registry.get(name)


def register_service(name: str, service: Any) -> None:
    """註冊服務"""
    service_registry.register(name, service)


def setup_logging(config: AppConfig) -> logging.Logger:
    """設置日誌系統"""
    log_dir = config.paths.base_dir / config.paths.log_dir
    log_dir.mkdir(exist_ok=True)
    
    # 設置日誌格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 檔案處理器
    file_handler = logging.FileHandler(
        log_dir / 'application.log', 
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # 控制台處理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 根日誌器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.log_level.upper()))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

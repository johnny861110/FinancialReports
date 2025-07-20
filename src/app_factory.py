#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
應用程式工廠和依賴注入設定
"""

from pathlib import Path
from typing import Optional

from .core.config import (
    ConfigManager, 
    setup_logging, 
    register_service, 
    get_config,
    AppConfig
)
from .core import (
    FinancialReport,
    ProcessingResult,
    ErrorHandler
)
from .processors.pdf_processor import ModernPDFProcessor
from .processors.smart_processor import SmartFinancialProcessor


class ApplicationFactory:
    """應用程式工廠"""
    
    @staticmethod
    def create_app(config_path: Optional[Path] = None) -> None:
        """創建和配置應用程式"""
        
        # 載入配置
        config_manager = ConfigManager()
        if config_path:
            config_manager.load_from_file(config_path)
        
        config = get_config()
        
        # 設置日誌
        setup_logging(config)
        
        # 註冊核心服務
        ApplicationFactory._register_core_services(config)
        
        # 註冊處理器
        ApplicationFactory._register_processors(config)
        
        # 註冊工具服務
        ApplicationFactory._register_utilities(config)
    
    @staticmethod
    def _register_core_services(config: AppConfig) -> None:
        """註冊核心服務"""
        
        # 配置管理器
        register_service('config_manager', ConfigManager())
        register_service('config', config)
        
        # 錯誤處理器
        register_service('error_handler', ErrorHandler())
    
    @staticmethod
    def _register_processors(config: AppConfig) -> None:
        """註冊處理器服務"""
        
        # PDF處理器
        register_service('pdf_processor', ModernPDFProcessor(config))
        
        # 智慧財務處理器
        register_service('smart_processor', SmartFinancialProcessor(config))
    
    @staticmethod
    def _register_utilities(config: AppConfig) -> None:
        """註冊工具服務"""
        
        # 財報工廠
        def financial_report_factory(stock_code: str, company_name: str, 
                                   year: int, season: str) -> FinancialReport:
            return FinancialReport(stock_code, company_name, year, season)
        
        register_service('financial_report_factory', financial_report_factory)
        
        # 結果工廠
        def result_factory(success: bool, message: str = "") -> ProcessingResult:
            return ProcessingResult(success, message)
        
        register_service('result_factory', result_factory)


def setup_application(config_path: Optional[Path] = None) -> AppConfig:
    """設置應用程式並返回配置"""
    ApplicationFactory.create_app(config_path)
    return get_config()


def get_processor(processor_type: str):
    """獲取處理器實例"""
    from .core.config import get_service
    
    processor_map = {
        'pdf': 'pdf_processor',
        'smart': 'smart_processor',
        'financial': 'smart_processor'
    }
    
    service_name = processor_map.get(processor_type.lower())
    if not service_name:
        raise ValueError(f"未知的處理器類型: {processor_type}")
    
    return get_service(service_name)


def create_financial_report(stock_code: str, company_name: str, 
                          year: int, season: str) -> FinancialReport:
    """創建財報實例"""
    from .core.config import get_service
    factory = get_service('financial_report_factory')
    return factory(stock_code, company_name, year, season)

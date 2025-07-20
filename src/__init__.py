# -*- coding: utf-8 -*-
"""
財務報告處理工具核心套件
"""

from .core import (
    BaseProcessor, 
    FinancialReport, 
    ProcessingResult, 
    get_config,
    AppConfig,
    Processor,
    Extractor,
    FinancialReportsException,
    ErrorHandler,
    handle_errors
)
from .core.config import ConfigManager, setup_logging, register_service, get_service
from .processors import PDFProcessor, SmartFinancialProcessor

__version__ = "2.0.0"
__all__ = [
    # 核心類別
    'BaseProcessor', 
    'FinancialReport', 
    'ProcessingResult', 
    'Processor',
    'Extractor',
    
    # 配置管理
    'AppConfig',
    'ConfigManager',
    'get_config',
    'setup_logging',
    'register_service',
    'get_service',
    
    # 異常處理
    'FinancialReportsException',
    'ErrorHandler',
    'handle_errors',
    
    # 處理器
    'PDFProcessor',
    'SmartFinancialProcessor'
]

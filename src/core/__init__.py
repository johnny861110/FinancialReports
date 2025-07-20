#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
核心模組 - 基礎類別和介面定義
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, List, Protocol, runtime_checkable
from datetime import datetime
import json
import logging

from .config import get_config, AppConfig, ConfigManager
from .exceptions import (
    FinancialReportsException, 
    ErrorHandler, 
    handle_errors,
    ValidationError,
    FileProcessingError,
    ErrorCode
)


@runtime_checkable
class Processor(Protocol):
    """處理器協議介面"""
    
    def process(self, input_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """處理主方法"""
        ...
    
    def validate_input(self, input_path: Path) -> bool:
        """驗證輸入"""
        ...


@runtime_checkable
class Extractor(Protocol):
    """資料提取器協議介面"""
    
    def extract_text(self, source: Any) -> str:
        """提取文字"""
        ...
    
    def extract_tables(self, source: Any) -> List[Dict]:
        """提取表格"""
        ...
    
    def extract_financial_data(self, source: Any) -> Dict[str, Any]:
        """提取財務數據"""
        ...


class BaseProcessor(ABC):
    """處理器基礎類別"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self.logger = self._setup_logging()
        self.error_handler = ErrorHandler()
    
    @abstractmethod
    def process(self, input_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """處理主方法"""
        pass
    
    def validate_input(self, input_path: Path) -> bool:
        """驗證輸入檔案"""
        if not input_path.exists():
            raise FileProcessingError(
                ErrorCode.FILE_NOT_FOUND,
                f"輸入檔案不存在: {input_path}",
                str(input_path)
            )
        
        if not input_path.is_file():
            raise ValidationError(
                f"輸入路徑不是檔案: {input_path}",
                {"path": str(input_path)}
            )
        
        return True
    
    def _setup_logging(self) -> logging.Logger:
        """設置日誌"""
        return logging.getLogger(self.__class__.__name__)
    
    @handle_errors
    def safe_process(self, input_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """安全處理方法，包含錯誤處理"""
        self.validate_input(input_path)
        return self.process(input_path, output_path)



class FinancialReport:
    """財報資料模型"""
    
    def __init__(self, stock_code: str, company_name: str, year: int, season: str):
        self.stock_code = stock_code
        self.company_name = company_name
        self.year = year
        self.season = season
        self.created_at = datetime.now()
        self.data = {}
        self.metadata = {}
        self.validation_errors = []
    
    def add_financial_data(self, data_type: str, data: Dict[str, Any]) -> None:
        """添加財務數據"""
        self.data[data_type] = data
    
    def add_metadata(self, key: str, value: Any) -> None:
        """添加元數據"""
        self.metadata[key] = value
    
    def validate(self) -> bool:
        """驗證財報數據完整性"""
        self.validation_errors = []
        
        # 基本資訊驗證
        if not self.stock_code:
            self.validation_errors.append("股票代碼不能為空")
        
        if not self.company_name:
            self.validation_errors.append("公司名稱不能為空")
        
        if self.year < 2000 or self.year > datetime.now().year + 1:
            self.validation_errors.append(f"年份無效: {self.year}")
        
        if self.season not in ['Q1', 'Q2', 'Q3', 'Q4']:
            self.validation_errors.append(f"季度無效: {self.season}")
        
        return len(self.validation_errors) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "stock_code": self.stock_code,
            "company_name": self.company_name,
            "report_year": self.year,
            "report_season": self.season,
            "currency": "TWD",
            "unit": "千元",
            "financials": self.data.get("financials", {}),
            "income_statement": self.data.get("income_statement", {}),
            "balance_sheet": self.data.get("balance_sheet", {}),
            "cash_flow": self.data.get("cash_flow", {}),
            "metadata": {
                **self.metadata,
                "created_at": self.created_at.isoformat(),
                "processor_version": "v2.0",
                "validation_status": "valid" if self.validate() else "invalid",
                "validation_errors": self.validation_errors
            }
        }
    
    @handle_errors
    def save(self, output_path: Path) -> None:
        """儲存為JSON檔案"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise FileProcessingError(
                ErrorCode.FILE_WRITE_ERROR,
                f"儲存財報檔案失敗: {e}",
                str(output_path),
                e
            )
    
    @classmethod
    @handle_errors
    def load(cls, file_path: Path) -> 'FinancialReport':
        """從JSON檔案載入財報"""
        if not file_path.exists():
            raise FileProcessingError(
                ErrorCode.FILE_NOT_FOUND,
                f"財報檔案不存在: {file_path}",
                str(file_path)
            )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            raise FileProcessingError(
                ErrorCode.FILE_READ_ERROR,
                f"讀取財報檔案失敗: {e}",
                str(file_path),
                e
            )
        
        # 創建財報實例
        report = cls(
            stock_code=data.get("stock_code", ""),
            company_name=data.get("company_name", ""),
            year=data.get("report_year", 0),
            season=data.get("report_season", "")
        )
        
        # 載入數據
        for key in ["financials", "income_statement", "balance_sheet", "cash_flow"]:
            if key in data:
                report.data[key] = data[key]
        
        # 載入元數據
        if "metadata" in data:
            report.metadata = data["metadata"]
        
        return report


class ProcessingResult:
    """處理結果封裝"""
    
    def __init__(self, success: bool, message: str = "", data: Any = None, 
                 errors: List[str] = None, warnings: List[str] = None):
        self.success = success
        self.message = message
        self.data = data
        self.errors = errors or []
        self.warnings = warnings or []
        self.timestamp = datetime.now()
        self.processing_time = 0.0
    
    def add_error(self, error: str) -> None:
        """添加錯誤"""
        self.errors.append(error)
        self.success = False
    
    def add_warning(self, warning: str) -> None:
        """添加警告"""
        self.warnings.append(warning)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "errors": self.errors,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat(),
            "processing_time": self.processing_time
        }


# 重新導出所有公用類別和函數
from .config import get_config, AppConfig
from .exceptions import (
    FinancialReportsException,
    ErrorHandler,
    handle_errors,
    ValidationError,
    FileProcessingError,
    PDFProcessingError,
    OCRError,
    DataExtractionError,
    ErrorCode
)

__all__ = [
    'BaseProcessor',
    'FinancialReport',
    'ProcessingResult',
    'Processor',
    'Extractor',
    'AppConfig',
    'ConfigManager',  # 向後相容性
    'get_config',
    'FinancialReportsException',
    'ErrorHandler',
    'handle_errors',
    'ValidationError',
    'FileProcessingError',
    'PDFProcessingError',
    'OCRError',
    'DataExtractionError',
    'ErrorCode'
]

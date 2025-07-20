#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
統一異常處理模組
定義專案中所有自定義異常和錯誤處理機制
"""

from typing import Optional, Any, Dict
import logging
from dataclasses import dataclass
from enum import Enum


class ErrorCode(Enum):
    """錯誤代碼枚舉"""
    # 一般錯誤
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    CONFIGURATION_ERROR = "CONFIG_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    
    # 檔案處理錯誤
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    FILE_WRITE_ERROR = "FILE_WRITE_ERROR"
    
    # PDF處理錯誤
    PDF_PARSE_ERROR = "PDF_PARSE_ERROR"
    PDF_CORRUPTION = "PDF_CORRUPTION"
    PDF_PASSWORD_PROTECTED = "PDF_PASSWORD_PROTECTED"
    
    # OCR錯誤
    OCR_ENGINE_ERROR = "OCR_ENGINE_ERROR"
    OCR_RECOGNITION_FAILED = "OCR_RECOGNITION_FAILED"
    
    # 數據處理錯誤
    DATA_EXTRACTION_ERROR = "DATA_EXTRACTION_ERROR"
    DATA_VALIDATION_ERROR = "DATA_VALIDATION_ERROR"
    DATA_CONVERSION_ERROR = "DATA_CONVERSION_ERROR"
    
    # 網路和爬蟲錯誤
    NETWORK_ERROR = "NETWORK_ERROR"
    CRAWLER_ERROR = "CRAWLER_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"


@dataclass
class ErrorDetails:
    """錯誤詳細資訊"""
    code: ErrorCode
    message: str
    context: Optional[Dict[str, Any]] = None
    original_exception: Optional[Exception] = None


class FinancialReportsException(Exception):
    """專案基礎異常類別"""
    
    def __init__(self, error_details: ErrorDetails):
        self.error_details = error_details
        super().__init__(error_details.message)
    
    @property
    def code(self) -> ErrorCode:
        return self.error_details.code
    
    @property
    def context(self) -> Optional[Dict[str, Any]]:
        return self.error_details.context
    
    @property
    def original_exception(self) -> Optional[Exception]:
        return self.error_details.original_exception


class ConfigurationError(FinancialReportsException):
    """配置錯誤"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        error_details = ErrorDetails(
            code=ErrorCode.CONFIGURATION_ERROR,
            message=message,
            context=context
        )
        super().__init__(error_details)


class ValidationError(FinancialReportsException):
    """驗證錯誤"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        error_details = ErrorDetails(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            context=context
        )
        super().__init__(error_details)


class FileProcessingError(FinancialReportsException):
    """檔案處理錯誤"""
    
    def __init__(self, code: ErrorCode, message: str, 
                 file_path: Optional[str] = None, 
                 original_exception: Optional[Exception] = None):
        context = {"file_path": file_path} if file_path else None
        error_details = ErrorDetails(
            code=code,
            message=message,
            context=context,
            original_exception=original_exception
        )
        super().__init__(error_details)


class PDFProcessingError(FinancialReportsException):
    """PDF處理錯誤"""
    
    def __init__(self, code: ErrorCode, message: str, 
                 pdf_path: Optional[str] = None, 
                 page_number: Optional[int] = None,
                 original_exception: Optional[Exception] = None):
        context = {}
        if pdf_path:
            context["pdf_path"] = pdf_path
        if page_number:
            context["page_number"] = page_number
        
        error_details = ErrorDetails(
            code=code,
            message=message,
            context=context if context else None,
            original_exception=original_exception
        )
        super().__init__(error_details)


class OCRError(FinancialReportsException):
    """OCR處理錯誤"""
    
    def __init__(self, message: str, 
                 engine: Optional[str] = None,
                 original_exception: Optional[Exception] = None):
        context = {"ocr_engine": engine} if engine else None
        error_details = ErrorDetails(
            code=ErrorCode.OCR_ENGINE_ERROR,
            message=message,
            context=context,
            original_exception=original_exception
        )
        super().__init__(error_details)


class DataExtractionError(FinancialReportsException):
    """數據提取錯誤"""
    
    def __init__(self, message: str, 
                 data_type: Optional[str] = None,
                 source_file: Optional[str] = None,
                 original_exception: Optional[Exception] = None):
        context = {}
        if data_type:
            context["data_type"] = data_type
        if source_file:
            context["source_file"] = source_file
        
        error_details = ErrorDetails(
            code=ErrorCode.DATA_EXTRACTION_ERROR,
            message=message,
            context=context if context else None,
            original_exception=original_exception
        )
        super().__init__(error_details)


class NetworkError(FinancialReportsException):
    """網路錯誤"""
    
    def __init__(self, message: str, 
                 url: Optional[str] = None,
                 status_code: Optional[int] = None,
                 original_exception: Optional[Exception] = None):
        context = {}
        if url:
            context["url"] = url
        if status_code:
            context["status_code"] = status_code
        
        error_details = ErrorDetails(
            code=ErrorCode.NETWORK_ERROR,
            message=message,
            context=context if context else None,
            original_exception=original_exception
        )
        super().__init__(error_details)


class ErrorHandler:
    """統一錯誤處理器"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def handle_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> ErrorDetails:
        """處理異常並返回標準化錯誤詳情"""
        
        if isinstance(exception, FinancialReportsException):
            # 已知的業務異常
            error_details = exception.error_details
            self._log_error(error_details)
            return error_details
        
        # 未知異常
        error_details = ErrorDetails(
            code=ErrorCode.UNKNOWN_ERROR,
            message=f"未預期的錯誤: {str(exception)}",
            context=context,
            original_exception=exception
        )
        
        self._log_error(error_details)
        return error_details
    
    def _log_error(self, error_details: ErrorDetails) -> None:
        """記錄錯誤日誌"""
        log_message = f"[{error_details.code.value}] {error_details.message}"
        
        if error_details.context:
            log_message += f" | Context: {error_details.context}"
        
        if error_details.original_exception:
            self.logger.error(log_message, exc_info=error_details.original_exception)
        else:
            self.logger.error(log_message)


def handle_errors(func):
    """錯誤處理裝飾器"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FinancialReportsException:
            # 重新拋出已知異常
            raise
        except Exception as e:
            # 包裝未知異常
            error_handler = ErrorHandler()
            error_details = error_handler.handle_exception(e)
            raise FinancialReportsException(error_details) from e
    
    return wrapper


def safe_execute(func, *args, **kwargs) -> tuple[bool, Any, Optional[ErrorDetails]]:
    """安全執行函數，返回 (成功標誌, 結果, 錯誤詳情)"""
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except FinancialReportsException as e:
        return False, None, e.error_details
    except Exception as e:
        error_handler = ErrorHandler()
        error_details = error_handler.handle_exception(e)
        return False, None, error_details

# -*- coding: utf-8 -*-
"""
處理器模組
"""

# 導入現代化處理器
from .pdf_processor import ModernPDFProcessor
from .smart_processor import SmartFinancialProcessor

# 提供統一的介面
PDFProcessor = ModernPDFProcessor

__all__ = ['PDFProcessor', 'ModernPDFProcessor', 'SmartFinancialProcessor']

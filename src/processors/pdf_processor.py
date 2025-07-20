#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
現代化PDF處理器 - 模組化架構
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json

try:
    import pdfplumber
except ImportError:
    raise ImportError("需要安裝 pdfplumber: pip install pdfplumber")

try:
    import cv2
    import numpy as np
    from paddleocr import PaddleOCR
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

from ..core import (
    BaseProcessor, 
    ProcessingResult, 
    Extractor,
    get_config,
    handle_errors,
    PDFProcessingError,
    OCRError,
    DataExtractionError,
    ValidationError,
    FileProcessingError,
    ErrorCode
)
from ..core.config import AppConfig


class PDFTextExtractor:
    """PDF文字提取器"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @handle_errors
    def extract_text(self, pdf_path: Path) -> str:
        """提取PDF中的所有文字"""
        all_text = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text()
                        if text and text.strip():
                            all_text.append(f"=== 第{page_num}頁 ===\n{text}\n")
                    except Exception as e:
                        self.logger.warning(f"無法提取第{page_num}頁文字: {e}")
                        continue
        
        except Exception as e:
            raise PDFProcessingError(
                ErrorCode.PDF_PARSE_ERROR,
                f"PDF文字提取失敗: {e}",
                str(pdf_path),
                original_exception=e
            )
        
        return "\n".join(all_text)


class PDFTableExtractor:
    """PDF表格提取器"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @handle_errors
    def extract_tables(self, pdf_path: Path) -> List[Dict]:
        """提取PDF中的所有表格"""
        all_tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        tables = page.extract_tables()
                        
                        for table_num, table in enumerate(tables):
                            if table and len(table) > 1:  # 至少要有標題和一行數據
                                table_dict = {
                                    'page': page_num,
                                    'table_index': table_num,
                                    'headers': table[0] if table else [],
                                    'rows': table[1:] if len(table) > 1 else [],
                                    'raw_data': table
                                }
                                all_tables.append(table_dict)
                                
                    except Exception as e:
                        self.logger.warning(f"無法提取第{page_num}頁表格: {e}")
                        continue
        
        except Exception as e:
            raise PDFProcessingError(
                ErrorCode.PDF_PARSE_ERROR,
                f"PDF表格提取失敗: {e}",
                str(pdf_path),
                original_exception=e
            )
        
        return all_tables


class PDFFinancialExtractor:
    """PDF財務數據提取器"""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self.patterns = self._load_financial_patterns()
    
    def _load_financial_patterns(self) -> Dict[str, List[str]]:
        """載入財務數據匹配模式"""
        return {
            'net_revenue': [
                r'營業收入[淨額]*\s*[：:]\s*([\d,]+)',
                r'淨?營收\s*[：:]\s*([\d,]+)',
                r'營收\s*[：:]\s*([\d,]+)',
                r'Net Revenue\s*[：:]\s*([\d,]+)'
            ],
            'gross_profit': [
                r'營業毛利\(損\)\s*[：:]\s*\(?([\d,]+)\)?',
                r'毛利\s*[：:]\s*([\d,]+)',
                r'Gross Profit\s*[：:]\s*([\d,]+)'
            ],
            'operating_income': [
                r'營業利益\(損失\)\s*[：:]\s*\(?([\d,]+)\)?',
                r'營業利益\s*[：:]\s*([\d,]+)',
                r'Operating Income\s*[：:]\s*([\d,]+)'
            ],
            'net_income': [
                r'本期淨利\(損\)\s*[：:]\s*\(?([\d,]+)\)?',
                r'淨利\s*[：:]\s*([\d,]+)',
                r'Net Income\s*[：:]\s*([\d,]+)'
            ],
            'eps': [
                r'基本每股盈餘\s*[：:]\s*([\d.]+)',
                r'每股盈餘\s*[：:]\s*([\d.]+)',
                r'EPS\s*[：:]\s*([\d.]+)',
                r'Earnings per Share\s*[：:]\s*([\d.]+)'
            ],
            'total_assets': [
                r'資產總額\s*[：:]\s*([\d,]+)',
                r'資產總計\s*[：:]\s*([\d,]+)',
                r'Total Assets\s*[：:]\s*([\d,]+)'
            ],
            'total_equity': [
                r'股東權益總額\s*[：:]\s*([\d,]+)',
                r'權益總計\s*[：:]\s*([\d,]+)',
                r'Total Equity\s*[：:]\s*([\d,]+)'
            ]
        }
    
    @handle_errors
    def extract_financial_data(self, text: str, tables: List[Dict]) -> Dict[str, Any]:
        """從文字和表格中提取財務數據"""
        financial_data = {}
        
        # 從文字中提取
        text_data = self._extract_from_text(text)
        financial_data.update(text_data)
        
        # 從表格中提取
        table_data = self._extract_from_tables(tables)
        financial_data.update(table_data)
        
        # 清理和驗證數據
        cleaned_data = self._clean_financial_data(financial_data)
        
        return cleaned_data
    
    def _extract_from_text(self, text: str) -> Dict[str, Any]:
        """從文字中提取財務數據"""
        extracted = {}
        
        for field_name, patterns in self.patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    # 取第一個匹配的值
                    value = matches[0].replace(',', '')
                    try:
                        if '.' in value:
                            extracted[field_name] = float(value)
                        else:
                            extracted[field_name] = int(value)
                        break  # 找到就停止
                    except ValueError:
                        continue
        
        return extracted
    
    def _extract_from_tables(self, tables: List[Dict]) -> Dict[str, Any]:
        """從表格中提取財務數據"""
        extracted = {}
        
        for table in tables:
            headers = table.get('headers', [])
            rows = table.get('rows', [])
            
            if not headers or not rows:
                continue
            
            # 尋找財務科目相關的表格
            for row in rows:
                if not row or len(row) == 0:
                    continue
                
                first_cell = str(row[0]).strip() if row[0] else ""
                
                # 檢查是否為財務科目
                for field_name, patterns in self.patterns.items():
                    for pattern in patterns:
                        if re.search(pattern.split('[：:]')[0], first_cell, re.IGNORECASE):
                            # 尋找數值欄位
                            for i, cell in enumerate(row[1:], 1):
                                if cell and str(cell).replace(',', '').replace('(', '').replace(')', '').strip().isdigit():
                                    try:
                                        value = str(cell).replace(',', '').replace('(', '').replace(')', '')
                                        if '.' in value:
                                            extracted[field_name] = float(value)
                                        else:
                                            extracted[field_name] = int(value)
                                        break
                                    except ValueError:
                                        continue
                            break
        
        return extracted
    
    def _clean_financial_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理和驗證財務數據"""
        cleaned = {}
        
        for key, value in data.items():
            if isinstance(value, (int, float)) and value != 0:
                cleaned[key] = value
        
        return cleaned


class ModernPDFProcessor(BaseProcessor):
    """現代化PDF處理器主類別"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        super().__init__(config)
        
        # 初始化提取器
        self.text_extractor = PDFTextExtractor(self.config)
        self.table_extractor = PDFTableExtractor(self.config)
        self.financial_extractor = PDFFinancialExtractor(self.config)
        
        # 初始化OCR（如果可用）
        self.ocr_engine = None
        if OCR_AVAILABLE and self.config.processing.ocr_engine == "paddleocr":
            try:
                self.ocr_engine = PaddleOCR(
                    use_angle_cls=True, 
                    lang='ch',
                    use_gpu=self.config.processing.ocr_use_gpu
                )
                self.logger.info("PaddleOCR初始化成功")
            except Exception as e:
                self.logger.warning(f"PaddleOCR初始化失敗: {e}")
    
    @handle_errors
    def process(self, input_path: Path, output_path: Optional[Path] = None) -> Dict[str, Any]:
        """處理PDF檔案"""
        self.validate_input(input_path)
        
        if input_path.suffix.lower() != '.pdf':
            raise ValidationError(
                f"輸入檔案必須是PDF格式: {input_path}",
                {"file_extension": input_path.suffix}
            )
        
        result = ProcessingResult(success=True, message="PDF處理完成")
        
        try:
            # 提取文字
            self.logger.info(f"開始提取PDF文字: {input_path}")
            text = self.text_extractor.extract_text(input_path)
            
            # 提取表格
            self.logger.info(f"開始提取PDF表格: {input_path}")
            tables = self.table_extractor.extract_tables(input_path)
            
            # 提取財務數據
            self.logger.info(f"開始提取財務數據: {input_path}")
            financial_data = self.financial_extractor.extract_financial_data(text, tables)
            
            # 構建結果
            processed_data = {
                "source_file": str(input_path),
                "text_content": text,
                "tables": tables,
                "financial_data": financial_data,
                "processing_info": {
                    "text_length": len(text),
                    "table_count": len(tables),
                    "financial_fields_found": len(financial_data),
                    "processor": "pdfplumber",
                    "ocr_available": self.ocr_engine is not None
                }
            }
            
            result.data = processed_data
            
            # 如果指定了輸出路徑，儲存結果
            if output_path:
                self._save_result(processed_data, output_path)
            
            self.logger.info(f"PDF處理完成: {input_path}")
            
        except Exception as e:
            result.success = False
            result.add_error(f"PDF處理失敗: {e}")
            self.logger.error(f"PDF處理失敗 {input_path}: {e}")
            raise
        
        return result.to_dict()
    
    def _save_result(self, data: Dict[str, Any], output_path: Path) -> None:
        """儲存處理結果"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise FileProcessingError(
                ErrorCode.FILE_WRITE_ERROR,
                f"儲存處理結果失敗: {e}",
                str(output_path),
                e
            )
    
    @handle_errors
    def extract_with_ocr(self, pdf_path: Path) -> str:
        """使用OCR提取PDF文字（備用方法）"""
        if not self.ocr_engine:
            raise OCRError("OCR引擎未初始化", self.config.processing.ocr_engine)
        
        try:
            import fitz  # PyMuPDF for image extraction
            
            doc = fitz.open(pdf_path)
            all_text = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap()
                img_data = pix.tobytes("png")
                
                # 轉換為OpenCV格式
                nparr = np.frombuffer(img_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # OCR識別
                result = self.ocr_engine.ocr(img, cls=True)
                
                page_text = []
                for line in result:
                    if line:
                        for word_info in line:
                            if len(word_info) >= 2:
                                text = word_info[1][0]
                                confidence = word_info[1][1]
                                if confidence >= self.config.processing.ocr_confidence_threshold:
                                    page_text.append(text)
                
                if page_text:
                    all_text.append(f"=== 第{page_num + 1}頁 (OCR) ===\n" + " ".join(page_text) + "\n")
            
            doc.close()
            return "\n".join(all_text)
            
        except Exception as e:
            raise OCRError(f"OCR處理失敗: {e}", self.config.processing.ocr_engine, e)


# 為了向後兼容，創建別名
PDFProcessor = ModernPDFProcessor

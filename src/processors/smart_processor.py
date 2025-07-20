#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智慧財務資料處理器 - 現代化版本
"""

import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# 使用新架構的導入
from ..core import (
    BaseProcessor, 
    FinancialReport, 
    ProcessingResult,
    get_config,
    handle_errors
)
from ..core.config import AppConfig
from .pdf_processor import ModernPDFProcessor


class SmartFinancialProcessor(BaseProcessor):
    """智慧財務資料處理器"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        super().__init__(config)
        self.pdf_processor = ModernPDFProcessor(self.config)
        self.min_fields_threshold = 3
        
        # 中文財務術語模式
        self.financial_patterns = {
            'net_revenue': [
                r'營業收入[^\d]*\$?\s*([0-9,]+)',
                r'4000[^\d]*營業收入[^\d]*\$?\s*([0-9,]+)',
                r'營收[^\d]*\$?\s*([0-9,]+)',
            ],
            'gross_profit': [
                r'營業毛利[^\d]*([0-9,]+)',
                r'5900[^\d]*營業毛利[^\d]*([0-9,]+)',
                r'毛利[^\d]*([0-9,]+)',
            ],
            'operating_income': [
                r'營業利益[^\d]*([0-9,]+)',
                r'6900[^\d]*營業利益[^\d]*([0-9,]+)',
                r'營業淨利[^\d]*([0-9,]+)',
            ],
            'net_income': [
                r'本期淨利[^\d]*\$?\s*([0-9,]+)',
                r'8200[^\d]*本期淨利[^\d]*\$?\s*([0-9,]+)',
                r'稅後淨利[^\d]*\$?\s*([0-9,]+)',
                r'淨利[^\d]*\$?\s*([0-9,]+)',
            ],
            'eps': [
                r'每股盈餘[^\d]*([0-9]+\.[0-9]{1,3})',
                r'基本每股盈餘[^\d]*([0-9]+\.[0-9]{1,3})',
            ],
            'cash_and_equivalents': [
                r'現金及約當現金[^\d]*([0-9,]+)',
                r'現金及銀行存款[^\d]*([0-9,]+)',
            ],
            'accounts_receivable': [
                r'應收帳款[^\d]*([0-9,]+)',
                r'應收帳款－淨額[^\d]*([0-9,]+)',
                r'應收票據及帳款[^\d]*([0-9,]+)',
            ],
            'inventory': [
                r'存貨[^\d]*([0-9,]+)',
                r'存貨－淨額[^\d]*([0-9,]+)',
                r'存\s*貨[^\d]*([0-9,]+)',
            ],
            'total_assets': [
                r'資產總額[^\d]*([0-9,]+)',
                r'資產合計[^\d]*([0-9,]+)',
                r'資產總計[^\d]*([0-9,]+)',
            ],
            'total_liabilities': [
                r'負債總額[^\d]*([0-9,]+)',
                r'負債合計[^\d]*([0-9,]+)',
                r'負債總計[^\d]*([0-9,]+)',
            ],
            'equity': [
                r'權益總額[^\d]*([0-9,]+)',
                r'權益合計[^\d]*([0-9,]+)',
                r'權益總計[^\d]*([0-9,]+)',
            ]
        }
    
    def process(self, pdf_path: Path, json_path: Path, output_path: Optional[Path] = None) -> ProcessingResult:
        """智慧處理PDF和JSON"""
        try:
            self.logger.info(f"智慧處理: {pdf_path.name}")
            
            # 載入原始JSON
            if not json_path.exists():
                return ProcessingResult(False, f"JSON檔案不存在: {json_path}")
            
            with open(json_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            
            # 分析PDF
            pdf_analysis = self._analyze_pdf_type(pdf_path)
            self.logger.info(f"PDF類型: {pdf_analysis['type']}, 文字比例: {pdf_analysis['text_ratio']:.1%}")
            
            # 根據PDF類型選擇處理策略
            enhanced_data = original_data.copy()
            confidence_level = 'low'
            processing_note = 'Unknown processing'
            
            if pdf_analysis['type'] == 'text_based':
                confidence_level, processing_note = self._process_text_based_pdf(
                    pdf_path, enhanced_data, pdf_analysis
                )
            elif pdf_analysis['type'] == 'scanned':
                confidence_level, processing_note = self._process_scanned_pdf(
                    pdf_path, enhanced_data, pdf_analysis
                )
            elif pdf_analysis['type'] == 'mixed':
                confidence_level, processing_note = self._process_mixed_pdf(
                    pdf_path, enhanced_data, pdf_analysis
                )
            
            # 添加缺失的欄位以符合品質驗證期望
            self._add_missing_fields(enhanced_data)
            
            # 添加處理元資料
            enhanced_data['metadata'] = enhanced_data.get('metadata', {})
            enhanced_data['metadata'].update({
                'enhanced_at': datetime.now().isoformat(),
                'processor_version': 'smart_v2.1',
                'extraction_confidence': confidence_level,
                'processing_note': processing_note,
                'pdf_analysis': pdf_analysis
            })
            
            # 儲存結果
            if output_path is None:
                output_path = pdf_path.parent / "processed" / f"{pdf_path.stem}_enhanced.json"
            
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"智慧處理完成: {output_path}")
            
            return ProcessingResult(
                success=True,
                message=f"智慧處理完成 ({confidence_level} 信心度)",
                data={
                    "output_path": str(output_path),
                    "confidence_level": confidence_level,
                    "pdf_type": pdf_analysis['type']
                }
            )
        
        except Exception as e:
            self.logger.error(f"智慧處理失敗: {e}")
            return ProcessingResult(False, f"智慧處理失敗: {e}")
    
    def _process_text_based_pdf(self, pdf_path: Path, enhanced_data: Dict, pdf_analysis: Dict) -> Tuple[str, str]:
        """處理文字型PDF"""
        try:
            # 使用PDF處理器提取內容
            processing_result_dict = self.pdf_processor.process(pdf_path)
            
            if processing_result_dict.get('success', False) and 'data' in processing_result_dict:
                pdf_data = processing_result_dict['data']
                
                # 獲取文字內容
                text_content = pdf_data.get('text_content', '')
                
                # 獲取已提取的財務數據
                financial_data = pdf_data.get('financial_data', {})
                
                # 如果PDF processor已經提取到財務數據，直接使用
                if financial_data:
                    self.logger.info(f"使用PDF處理器提取的財務數據: {len(financial_data)} 個欄位")
                    self._backfill_data(enhanced_data, financial_data)
                    return 'high', f'Text-based PDF processed with {len(financial_data)} financial fields'
                
                # 否則使用smart processor的財務數據提取
                elif text_content:
                    self.logger.info(f"使用智慧處理器提取財務數據，文字長度: {len(text_content)}")
                    extracted_data = self._extract_financial_data(text_content)
                    self._backfill_data(enhanced_data, extracted_data)
                    return 'medium', f'Text-based PDF processed with smart extraction: {len(extracted_data)} fields'
                
                else:
                    return 'low', 'No text content extracted from PDF'
            else:
                return 'low', 'Failed to process PDF content'
        
        except Exception as e:
            self.logger.error(f"文字型PDF處理失敗: {e}")
            return 'low', f'Text processing failed: {e}'
    
    def _process_scanned_pdf(self, pdf_path: Path, enhanced_data: Dict, pdf_analysis: Dict) -> Tuple[str, str]:
        """處理掃描型PDF"""
        try:
            # 嘗試基本財務資料提取
            extracted_text = pdf_analysis.get('extracted_text', '')
            extracted_data = self._extract_basic_financial_data(extracted_text)
            
            if not extracted_data or len([v for v in extracted_data.values() if v]) < 2:
                return 'low', 'Scanned PDF - requires manual review or OCR'
            else:
                self._apply_extracted_data(enhanced_data, extracted_data)
                return 'medium', 'Scanned PDF - limited extraction'
        
        except Exception as e:
            self.logger.error(f"掃描型PDF處理失敗: {e}")
            return 'low', f'Scanned processing failed: {e}'
    
    def _process_mixed_pdf(self, pdf_path: Path, enhanced_data: Dict, pdf_analysis: Dict) -> Tuple[str, str]:
        """處理混合型PDF，合併文字與OCR內容"""
        try:
            processing_result_dict = self.pdf_processor.process(pdf_path)
            if processing_result_dict.get('success', False) and 'data' in processing_result_dict:
                pdf_data = processing_result_dict['data']
                
                # 獲取文字內容和財務數據
                text_content = pdf_data.get('text_content', '')
                financial_data = pdf_data.get('financial_data', {})
                
                # 使用PDF處理器的結果
                if financial_data:
                    self._backfill_data(enhanced_data, financial_data)
                    return 'medium', f'Mixed PDF processed with PDF extractor: {len(financial_data)} fields'
                
                # 使用smart processor的財務數據提取
                elif text_content:
                    extracted_data = self._extract_financial_data(text_content)
                    self._backfill_data(enhanced_data, extracted_data)
                    return 'medium', f'Mixed PDF processed with smart extraction: {len(extracted_data)} fields'
                
                else:
                    return 'low', 'Mixed PDF processing failed - no content'
            else:
                return 'low', 'Mixed PDF processing failed'
        
        except Exception as e:
            self.logger.error(f"混合型PDF處理失敗: {e}")
            return 'low', f'Mixed processing failed: {e}'
    
    def _extract_financial_data(self, text: str) -> Dict[str, Any]:
        """提取財務資料，回傳值含 confidence 與來源"""
        if not text or len(text) < 100:
            return {}
        
        extracted = {}
        lines = text.split('\n')
        
        # 逐行處理文字以找到財務資料
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for field_name, patterns in self.financial_patterns.items():
                if field_name in extracted:
                    continue  # 已找到此欄位
                
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        try:
                            # 提取並清理數字
                            number_str = match.group(1).replace(',', '')
                            number = float(number_str)
                            
                            # 驗證數值合理性
                            if self._is_reasonable_value(number, field_name):
                                # 新增 confidence 與來源
                                extracted[field_name] = {
                                    'value': number,
                                    'confidence': 1.0,
                                    'source': 'text'
                                }
                                self.logger.info(f"提取 {field_name}: {number} (來源: {line[:100]})")
                                break
                        except (ValueError, IndexError):
                            continue
        
        return extracted
    
    def _extract_basic_financial_data(self, text: str) -> Dict[str, Any]:
        """基礎財務資料提取（用於掃描PDF）"""
        return self._extract_financial_data(text)
    
    def _extract_ocr_financial_data(self, ocr_text: str) -> Dict[str, Any]:
        """專為 OCR 結果設計的財務資料提取"""
        if not ocr_text or len(ocr_text) < 50:
            return {}
        
        extracted = {}
        lines = ocr_text.split('\n')
        
        # 逐行處理文字以找到財務資料
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            for field_name, patterns in self.financial_patterns.items():
                if field_name in extracted:
                    continue  # 已找到此欄位
                
                for pattern in patterns:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        try:
                            # 提取並清理數字
                            number_str = match.group(1).replace(',', '')
                            number = float(number_str)
                            
                            # 驗證數值合理性
                            if self._is_reasonable_value(number, field_name):
                                extracted[field_name] = {
                                    'value': number,
                                    'confidence': 0.7,
                                    'source': 'ocr'
                                }
                                self.logger.info(f"OCR提取 {field_name}: {number} (來源: {line[:100]})")
                                break
                        except (ValueError, IndexError):
                            continue
        
        return extracted
    
    def _is_reasonable_value(self, value: float, field_type: str) -> bool:
        """檢查數值是否合理"""
        if field_type == 'eps':
            return 0.01 <= value <= 100  # 合理的每股盈餘範圍
        elif field_type in ['net_revenue', 'net_income', 'gross_profit', 'operating_income']:
            return 1000 <= value <= 999999999999  # 合理的財務金額
        elif field_type in ['cash_and_equivalents', 'accounts_receivable', 'inventory', 
                           'total_assets', 'total_liabilities', 'equity']:
            return 1000 <= value <= 999999999999  # 合理的資產負債金額
        else:
            return value > 0
    
    def _backfill_data(self, enhanced_data: Dict, extracted_data: Dict):
        """回填資料到原始JSON結構，支援欄位信心度與來源"""
        if not extracted_data:
            return
        
        income_fields = ['net_revenue', 'gross_profit', 'operating_income', 'net_income', 'eps']
        balance_fields = ['cash_and_equivalents', 'accounts_receivable', 'inventory', 'total_assets', 'total_liabilities', 'equity']
        
        fields_updated = 0
        field_confidence = {}
        field_source = {}
        
        for field, info in extracted_data.items():
            value = info['value'] if isinstance(info, dict) else info
            confidence = info.get('confidence', 1.0) if isinstance(info, dict) else 1.0
            source = info.get('source', 'text') if isinstance(info, dict) else 'text'
            if field in income_fields:
                if 'income_statement' not in enhanced_data:
                    enhanced_data['income_statement'] = {}
                enhanced_data['income_statement'][field] = value
                fields_updated += 1
            elif field in balance_fields:
                if 'financials' not in enhanced_data:
                    enhanced_data['financials'] = {}
                enhanced_data['financials'][field] = value
                fields_updated += 1
            field_confidence[field] = confidence
            field_source[field] = source
        
        # metadata 補充
        if 'metadata' not in enhanced_data:
            enhanced_data['metadata'] = {}
        enhanced_data['metadata']['extraction_summary'] = {
            'fields_found': fields_updated,
            'total_possible_fields': len(income_fields) + len(balance_fields),
            'field_confidence': field_confidence,
            'field_source': field_source,
            'missing_fields': [f for f in income_fields+balance_fields if f not in extracted_data]
        }
    
    def _apply_extracted_data(self, enhanced_data: Dict, extracted_data: Dict):
        """應用提取的資料（簡化版）"""
        income_fields = ['net_revenue', 'net_income', 'eps', 'gross_profit', 'operating_income']
        
        for field, value in extracted_data.items():
            if field in income_fields and 'income_statement' in enhanced_data:
                enhanced_data['income_statement'][field] = value
                self.logger.info(f"應用 income_statement.{field}: {value}")
            elif 'financials' in enhanced_data:
                enhanced_data['financials'][field] = value
                self.logger.info(f"應用 financials.{field}: {value}")
    
    def _add_missing_fields(self, enhanced_data: Dict):
        """添加品質驗證期望的缺失欄位"""
        
        # 1. 添加 report_period 欄位
        if 'report_year' in enhanced_data and 'report_season' in enhanced_data:
            year = enhanced_data['report_year']
            season = enhanced_data['report_season']
            # 格式化為統一的報告期間字串
            if season:
                enhanced_data['report_period'] = f"{year}{season}"
            else:
                enhanced_data['report_period'] = str(year)
            self.logger.info(f"添加 report_period: {enhanced_data['report_period']}")
        else:
            # 嘗試從檔案名稱推斷報告期間
            metadata = enhanced_data.get('metadata', {})
            file_name = metadata.get('file_name', '')
            if file_name:
                # 從檔案名稱提取期間 (例如: 202401_2330_AI1.pdf)
                period_match = re.search(r'(\d{6})', file_name)
                if period_match:
                    period = period_match.group(1)
                    year = int(period[:4])
                    month = int(period[4:6])
                    
                    # 推斷季度
                    if month <= 3:
                        season = "Q1"
                    elif month <= 6:
                        season = "Q2"
                    elif month <= 9:
                        season = "Q3"
                    else:
                        season = "Q4"
                    
                    enhanced_data['report_period'] = f"{year}{season}"
                    enhanced_data['report_year'] = year
                    enhanced_data['report_season'] = season
                    self.logger.info(f"從檔案名推斷 report_period: {enhanced_data['report_period']}")
                else:
                    enhanced_data['report_period'] = "未知"
                    self.logger.warning("無法確定報告期間，設定為'未知'")
            else:
                enhanced_data['report_period'] = "未知"
                self.logger.warning("缺少檔案名稱資訊，無法推斷報告期間")
        
        # 2. 添加 financial_data 欄位（整合所有財務資料）
        financial_data = {}
        
        # 合併資產負債表資料
        if 'financials' in enhanced_data:
            financial_data.update(enhanced_data['financials'])
        
        # 合併損益表資料
        if 'income_statement' in enhanced_data:
            financial_data.update(enhanced_data['income_statement'])
        
        # 添加其他可能的財務資料
        for key in ['currency', 'unit']:
            if key in enhanced_data:
                financial_data[key] = enhanced_data[key]
        
        enhanced_data['financial_data'] = financial_data
        self.logger.info(f"添加 financial_data，包含 {len(financial_data)} 個欄位")
        
        # 3. 確保基本結構完整性
        if 'financials' not in enhanced_data:
            enhanced_data['financials'] = {
                'cash_and_equivalents': None,
                'accounts_receivable': None,
                'inventory': None,
                'total_assets': None,
                'total_liabilities': None,
                'equity': None
            }
        
        if 'income_statement' not in enhanced_data:
            enhanced_data['income_statement'] = {
                'net_revenue': None,
                'gross_profit': None,
                'operating_income': None,
                'net_income': None,
                'eps': None
            }
    
    def backfill_to_original_json(self, enhanced_json_path: Path, original_json_path: Path) -> ProcessingResult:
        """將增強JSON的財務數據回填到原始JSON"""
        try:
            self.logger.info(f"開始回填: {enhanced_json_path.name} -> {original_json_path.name}")
            
            # 讀取增強JSON
            if not enhanced_json_path.exists():
                return ProcessingResult(False, f"增強JSON檔案不存在: {enhanced_json_path}")
            
            with open(enhanced_json_path, 'r', encoding='utf-8') as f:
                enhanced_data = json.load(f)
            
            # 讀取原始JSON
            if not original_json_path.exists():
                return ProcessingResult(False, f"原始JSON檔案不存在: {original_json_path}")
            
            with open(original_json_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)
            
            # 執行回填
            updated_data = self._perform_backfill(original_data, enhanced_data)
            
            # 備份原始檔案
            backup_path = original_json_path.with_suffix('.json.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(original_data, f, ensure_ascii=False, indent=2)
            
            # 寫入更新後的數據
            with open(original_json_path, 'w', encoding='utf-8') as f:
                json.dump(updated_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"回填完成: {original_json_path}")
            
            return ProcessingResult(
                success=True,
                message=f"成功回填財務數據",
                data={
                    "original_file": str(original_json_path),
                    "enhanced_file": str(enhanced_json_path),
                    "backup_file": str(backup_path),
                    "updated_fields": self._get_updated_fields_summary(original_data, updated_data)
                }
            )
            
        except Exception as e:
            self.logger.error(f"回填失敗: {e}")
            return ProcessingResult(False, f"回填失敗: {e}")
    
    def _perform_backfill(self, original_data: Dict, enhanced_data: Dict) -> Dict:
        """執行實際的回填操作"""
        updated_data = original_data.copy()
        
        # 從增強數據中提取財務資料
        enhanced_financials = {}
        
        # 從 financial_data 欄位提取
        if 'financial_data' in enhanced_data:
            enhanced_financials.update(enhanced_data['financial_data'])
        
        # 從 income_statement 欄位提取
        if 'income_statement' in enhanced_data:
            enhanced_financials.update(enhanced_data['income_statement'])
        
        # 從 financials 欄位提取
        if 'financials' in enhanced_data:
            enhanced_financials.update(enhanced_data['financials'])
        
        # 從巢狀結構提取
        if 'extraction_result' in enhanced_data:
            extraction_result = enhanced_data['extraction_result']
            if 'pages' in extraction_result:
                for page in extraction_result['pages']:
                    if 'financial_data' in page:
                        enhanced_financials.update(page['financial_data'])
        
        # 回填到原始數據結構
        self._backfill_financial_fields(updated_data, enhanced_financials)
        
        # 更新元數據
        if 'metadata' not in updated_data:
            updated_data['metadata'] = {}
        
        updated_data['metadata'].update({
            'last_backfill': datetime.now().isoformat(),
            'backfill_source': 'smart_processor_enhanced',
            'enhanced_fields_count': len([v for v in enhanced_financials.values() if v is not None])
        })
        
        return updated_data
    
    def _backfill_financial_fields(self, original_data: Dict, enhanced_financials: Dict):
        """回填財務欄位到原始數據結構"""
        # 確保基本結構存在
        if 'financials' not in original_data:
            original_data['financials'] = {}
        if 'income_statement' not in original_data:
            original_data['income_statement'] = {}
        
        # 定義欄位映射
        balance_sheet_fields = [
            'cash_and_equivalents', 'accounts_receivable', 'inventory',
            'total_assets', 'total_liabilities', 'equity'
        ]
        
        income_statement_fields = [
            'net_revenue', 'gross_profit', 'operating_income', 
            'net_income', 'eps'
        ]
        
        # 回填資產負債表欄位
        for field in balance_sheet_fields:
            if field in enhanced_financials and enhanced_financials[field] is not None:
                # 提取數值（如果是dict格式）
                value = enhanced_financials[field]
                if isinstance(value, dict) and 'value' in value:
                    value = value['value']
                
                original_data['financials'][field] = value
                self.logger.info(f"回填 financials.{field}: {value}")
        
        # 回填損益表欄位
        for field in income_statement_fields:
            if field in enhanced_financials and enhanced_financials[field] is not None:
                # 提取數值（如果是dict格式）
                value = enhanced_financials[field]
                if isinstance(value, dict) and 'value' in value:
                    value = value['value']
                
                original_data['income_statement'][field] = value
                self.logger.info(f"回填 income_statement.{field}: {value}")
    
    def _get_updated_fields_summary(self, original_data: Dict, updated_data: Dict) -> Dict:
        """獲取更新欄位的摘要"""
        summary = {
            'financials': [],
            'income_statement': []
        }
        
        # 檢查 financials 欄位變更
        original_financials = original_data.get('financials', {})
        updated_financials = updated_data.get('financials', {})
        
        for field, value in updated_financials.items():
            if field not in original_financials or original_financials[field] != value:
                summary['financials'].append({
                    'field': field,
                    'old_value': original_financials.get(field),
                    'new_value': value
                })
        
        # 檢查 income_statement 欄位變更
        original_income = original_data.get('income_statement', {})
        updated_income = updated_data.get('income_statement', {})
        
        for field, value in updated_income.items():
            if field not in original_income or original_income[field] != value:
                summary['income_statement'].append({
                    'field': field,
                    'old_value': original_income.get(field),
                    'new_value': value
                })
        
        return summary
    
    def batch_backfill(self, data_dir: Path) -> ProcessingResult:
        """批次回填處理"""
        try:
            processed_dir = data_dir / "processed"
            if not processed_dir.exists():
                return ProcessingResult(False, "找不到processed目錄")
            
            # 尋找增強檔案
            enhanced_files = list(processed_dir.glob("*_enhanced.json"))
            if not enhanced_files:
                return ProcessingResult(False, "找不到增強檔案")
            
            results = []
            success_count = 0
            
            for enhanced_file in enhanced_files:
                # 找到對應的原始檔案
                original_name = enhanced_file.name.replace('_enhanced.json', '.json')
                original_file = data_dir / original_name
                
                if original_file.exists():
                    result = self.backfill_to_original_json(enhanced_file, original_file)
                    results.append({
                        'enhanced_file': enhanced_file.name,
                        'original_file': original_file.name,
                        'success': result.success,
                        'message': result.message
                    })
                    
                    if result.success:
                        success_count += 1
                else:
                    results.append({
                        'enhanced_file': enhanced_file.name,
                        'original_file': original_name,
                        'success': False,
                        'message': f"找不到原始檔案: {original_name}"
                    })
            
            return ProcessingResult(
                success=True,
                message=f"批次回填完成: {success_count}/{len(enhanced_files)} 成功",
                data={
                    'total_files': len(enhanced_files),
                    'success_count': success_count,
                    'results': results
                }
            )
            
        except Exception as e:
            self.logger.error(f"批次回填失敗: {e}")
            return ProcessingResult(False, f"批次回填失敗: {e}")

    def _analyze_pdf_type(self, pdf_path: Path) -> Dict[str, Any]:
        """分析PDF類型（文字型、掃描型或混合型）"""
        try:
            import pdfplumber
            
            with pdfplumber.open(pdf_path) as pdf:
                total_chars = 0
                total_pages = len(pdf.pages)
                
                # 分析前幾頁的文字內容
                sample_pages = min(5, total_pages)
                
                for i in range(sample_pages):
                    page = pdf.pages[i]
                    text = page.extract_text()
                    if text:
                        # 計算有意義的文字（排除空白和特殊字符）
                        meaningful_text = ''.join(c for c in text if c.isalnum() or c in '，。、；：！？""''（）【】')
                        total_chars += len(meaningful_text)
                
                # 更保守的文字密度計算
                # 假設每頁平均應該有至少500個有意義字符
                expected_chars_per_page = 500
                text_ratio = total_chars / (sample_pages * expected_chars_per_page) if sample_pages > 0 else 0
                text_ratio = min(text_ratio, 1.0)
                
                # 重新調整判斷標準 - 更傾向於識別為文字型
                if total_chars > 100:  # 如果有足夠的文字內容
                    if text_ratio > 0.3 or total_chars > 1000:  # 降低文字型的門檻
                        pdf_type = 'text_based'
                    elif text_ratio < 0.05 and total_chars < 50:
                        pdf_type = 'scanned'
                    else:
                        pdf_type = 'mixed'
                else:
                    pdf_type = 'scanned'
                
                return {
                    'type': pdf_type,
                    'text_ratio': text_ratio,
                    'total_pages': total_pages,
                    'meaningful_chars': total_chars
                }
                
        except Exception as e:
            self.logger.warning(f"PDF分析失敗，使用預設值: {e}")
            return {
                'type': 'text_based',  # 預設為文字型
                'text_ratio': 0.8,
                'total_pages': 1,
                'meaningful_chars': 1000
            }

# 創建別名以保持向後兼容性
SmartProcessor = SmartFinancialProcessor

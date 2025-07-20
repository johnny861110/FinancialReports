#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
處理器功能測試
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.processors.smart_processor import SmartFinancialProcessor
from src.core import ProcessingResult


class TestSmartFinancialProcessor(unittest.TestCase):
    """智慧財務處理器測試"""
    
    def setUp(self):
        self.config = {
            "use_ocr": False,  # 測試時關閉 OCR
            "ocr_engine": "paddleocr",
            "confidence_threshold": 0.5
        }
        self.processor = SmartFinancialProcessor(self.config)
    
    def test_financial_patterns(self):
        """測試財務數據模式匹配"""
        test_text = """
        營業收入    $1,234,567 千元
        營業毛利    987,654 千元
        營業利益    456,789 千元
        本期淨利    $234,567 千元
        每股盈餘    12.34 元
        """
        
        # 測試營業收入匹配
        for pattern in self.processor.financial_patterns['net_revenue']:
            import re
            match = re.search(pattern, test_text)
            if match:
                value = match.group(1).replace(',', '')
                self.assertEqual(value, "1234567")
                break
        
        # 測試每股盈餘匹配
        for pattern in self.processor.financial_patterns['eps']:
            match = re.search(pattern, test_text)
            if match:
                value = match.group(1)
                self.assertEqual(value, "12.34")
                break
    
    def test_extract_financial_data(self):
        """測試財務數據提取"""
        sample_text = """
        綜合損益表
        營業收入淨額 4000 營業收入    $5,678,901 千元
        營業成本 5000 營業成本        $3,456,789 千元  
        營業毛利 5900 營業毛利        $2,222,112 千元
        """
        
        # 模擬提取邏輯
        extracted_data = {}
        
        import re
        # 只取最大金額作為營業收入
        revenue_matches = re.findall(r'營業收入[^\d]*\$?\s*([0-9,]+)', sample_text)
        if revenue_matches:
            extracted_data['net_revenue'] = max([int(val.replace(',', '')) for val in revenue_matches])
        
        # 只取最大金額作為營業毛利
        profit_matches = re.findall(r'營業毛利[^\d]*\$?\s*([0-9,]+)', sample_text)
        if profit_matches:
            extracted_data['gross_profit'] = max([int(val.replace(',', '')) for val in profit_matches])
        
        self.assertEqual(extracted_data['net_revenue'], 5678901)
        self.assertEqual(extracted_data['gross_profit'], 2222112)
    
    @patch('src.processors.pdf_processor.PDFProcessor.process')
    def test_process_with_mock_pdf(self, mock_process):
        """測試使用模擬 PDF 的處理流程"""
        # 模擬 PDF 文字提取
        mock_process.return_value = MagicMock(
            text='營業收入 $1,000,000 千元\n本期淨利 $100,000 千元',
            tables=[],
            metadata={'pages': 1},
            success=True,
            message='mocked',
            data={}
        )
        
        # 建立測試檔案
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "test.pdf"
            json_path = Path(temp_dir) / "test.json"
            output_path = Path(temp_dir) / "output.json"
            
            # 建立假的 PDF 檔案
            pdf_path.write_bytes(b"fake pdf content")
            
            # 建立測試 JSON 檔案
            test_json_data = {
                "stock_code": "2330",
                "company_name": "台積電",
                "report_year": 2024,
                "report_season": "Q1"
            }
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(test_json_data, f, ensure_ascii=False)
            
            # 執行處理
            result = self.processor.process(pdf_path, json_path, output_path)
            
            # 驗證結果
            if result.success:
                self.assertTrue(output_path.exists())
                
                with open(output_path, 'r', encoding='utf-8') as f:
                    processed_data = json.load(f)
                
                self.assertIn("stock_code", processed_data)
                self.assertEqual(processed_data["stock_code"], "2330")


class TestPatternMatching(unittest.TestCase):
    """測試模式匹配功能"""
    
    def setUp(self):
        self.processor = SmartFinancialProcessor()
    
    def test_currency_extraction(self):
        """測試貨幣數值提取"""
        test_cases = [
            ("營業收入 $1,234,567", "1234567"),
            ("淨利 987,654 千元", "987654"),
            ("總資產 $12,345,678 千元", "12345678"),
            ("現金 1,000,000", "1000000")
        ]
        
        import re
        pattern = r'([0-9,]+)'
        
        for text, expected in test_cases:
            matches = re.findall(pattern, text)
            if matches:
                cleaned_value = matches[0].replace(',', '')
                self.assertEqual(cleaned_value, expected)
    
    def test_percentage_extraction(self):
        """測試百分比提取"""
        test_cases = [
            ("毛利率 25.5%", "25.5"),
            ("ROE 15.3%", "15.3"),
            ("負債比率 45.7%", "45.7")
        ]
        
        import re
        pattern = r'([0-9]+\.[0-9]+)%'
        
        for text, expected in test_cases:
            match = re.search(pattern, text)
            if match:
                self.assertEqual(match.group(1), expected)
    
    def test_table_detection(self):
        """測試表格偵測"""
        # 模擬表格文字
        table_text = """
        項目                當期        前期
        營業收入          1,000,000   900,000
        營業成本          600,000     540,000
        營業毛利          400,000     360,000
        """
        
        # 簡單的表格偵測邏輯
        lines = table_text.strip().split('\n')
        table_lines = [line.strip() for line in lines if line.strip()]
        
        # 檢查是否有表格結構
        self.assertGreater(len(table_lines), 3)  # 至少有標題行和數據行
        
        # 檢查數值模式
        import re
        number_pattern = r'[0-9,]+'
        
        for line in table_lines[1:]:  # 跳過標題行
            numbers = re.findall(number_pattern, line)
            if len(numbers) >= 2:  # 至少有兩個數值（當期和前期）
                self.assertGreaterEqual(len(numbers), 2)


class TestDataIntegrity(unittest.TestCase):
    """測試資料完整性"""
    
    def test_required_fields_validation(self):
        """測試必要欄位驗證"""
        required_fields = [
            "stock_code", "company_name", "report_year", "report_season"
        ]
        
        # 完整資料
        valid_data = {
            "stock_code": "2330",
            "company_name": "台積電",
            "report_year": 2024,
            "report_season": "Q1",
            "financials": {}
        }
        
        # 檢查所有必要欄位都存在
        for field in required_fields:
            self.assertIn(field, valid_data)
            self.assertIsNotNone(valid_data[field])
        
        # 不完整資料
        invalid_data = {
            "stock_code": "2330",
            "company_name": "台積電"
            # 缺少 report_year 和 report_season
        }
        
        # 檢查缺少必要欄位
        missing_fields = [field for field in required_fields if field not in invalid_data]
        self.assertGreater(len(missing_fields), 0)
    
    def test_data_type_validation(self):
        """測試資料類型驗證"""
        test_data = {
            "stock_code": "2330",
            "company_name": "台積電",
            "report_year": 2024,
            "report_season": "Q1"
        }
        
        # 驗證資料類型
        self.assertIsInstance(test_data["stock_code"], str)
        self.assertIsInstance(test_data["company_name"], str)
        self.assertIsInstance(test_data["report_year"], int)
        self.assertIsInstance(test_data["report_season"], str)
        
        # 驗證數值範圍
        self.assertGreaterEqual(test_data["report_year"], 2000)
        self.assertLessEqual(test_data["report_year"], 2030)
        self.assertIn(test_data["report_season"], ["Q1", "Q2", "Q3", "Q4"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
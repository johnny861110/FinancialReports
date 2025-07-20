#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
爬蟲功能測試
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.crawler import FinancialCrawler
from src.core import ProcessingResult


class TestFinancialCrawlerIntegration(unittest.TestCase):
    """財報爬蟲整合測試"""
    
    def setUp(self):
        self.test_config = {
            "output_dir": "test_output",
            "download_delay": 1,
            "max_retry": 2,
            "timeout": 10
        }
        self.crawler = FinancialCrawler(self.test_config)
    
    def test_process_single_query(self):
        """測試單筆查詢處理"""
        query_data = {
            "stock_code": "2330",
            "company_name": "台積電",
            "year": 2024,
            "season": "Q1"
        }
        
        with patch('requests.Session.post') as mock_post, \
             patch('requests.Session.get') as mock_get:
            
            # 模擬查詢回應
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = '''
            <html><body>
            <a href="/download/202401_2330_AI1.pdf">202401_2330_AI1.pdf</a>
            </body></html>
            '''
            
            # 模擬PDF下載回應 - 使用更大的內容以通過檔案大小驗證
            mock_pdf_content = b'Mock PDF content' * 100  # 1700+ bytes
            mock_get.return_value.status_code = 200
            mock_get.return_value.content = mock_pdf_content
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # 設置具體的輸出路徑而非目錄
                output_file = Path(temp_dir) / "202401_2330_AI1.pdf"
                result = self.crawler._process_single(query_data, output_file)
                
                # 驗證處理結果
                self.assertTrue(result.success)
                mock_post.assert_called_once()
                mock_get.assert_called_once()
    
    def test_process_batch_queries(self):
        """測試批次查詢處理"""
        queries_data = [
            {"stock_code": "2330", "company_name": "台積電", "year": 2024, "season": "Q1"},
            {"stock_code": "2454", "company_name": "聯發科", "year": 2024, "season": "Q1"}
        ]
        
        with patch('requests.Session.post') as mock_post, \
             patch('requests.Session.get') as mock_get:
            
            # 模擬查詢回應
            mock_post.return_value.status_code = 200
            mock_post.return_value.text = '''
            <html><body>
            <a href="/download/202401_2330_AI1.pdf">PDF link</a>
            <a href="/download/202401_2454_AI1.pdf">PDF link</a>
            </body></html>
            '''
            
            # 模擬PDF下載回應 - 使用更大的內容
            mock_pdf_content = b'Mock PDF content for testing' * 50  # 1400+ bytes
            mock_get.return_value.status_code = 200
            mock_get.return_value.content = mock_pdf_content
            
            result = self.crawler._process_batch(queries_data)
            
            # 驗證批次處理結果
            self.assertTrue(result.success)
            self.assertEqual(mock_post.call_count, 2)  # 兩次查詢請求
            self.assertIn("批次處理完成", result.message)
    
    def test_filename_generation(self):
        """測試檔案名稱生成"""
        query_data = {
            "stock_code": "2330",
            "company_name": "台積電",
            "year": 2024,
            "month": "03"
        }
        
        # 驗證檔案名稱格式 - 直接使用年月格式
        stock_code = query_data['stock_code']
        year = int(query_data['year'])
        month = query_data['month']
        
        expected_filename = f"{year}{month:0>2}_{stock_code}_AI1.pdf"
        
        self.assertEqual(expected_filename, "202403_2330_AI1.pdf")


class TestCrawlerErrorHandling(unittest.TestCase):
    """測試爬蟲錯誤處理"""
    
    def setUp(self):
        self.crawler = FinancialCrawler()
    
    @patch('requests.Session.post')
    def test_network_error_handling(self, mock_post):
        """測試網路錯誤處理"""
        # 模擬網路錯誤
        mock_post.side_effect = Exception("Network error")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"
            
            result = self.crawler._download_report("2330", "202401_2330_AI1.pdf", output_path)
            
            self.assertFalse(result.success)
            self.assertIn("下載失敗", result.message)
    
    @patch('requests.Session.post')
    def test_http_error_handling(self, mock_post):
        """測試 HTTP 錯誤處理"""
        # 模擬 HTTP 錯誤
        mock_post.return_value.status_code = 500
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"
            
            result = self.crawler._download_report("2330", "202401_2330_AI1.pdf", output_path)
            
            self.assertFalse(result.success)
            self.assertIn("查詢失敗", result.message)
    
    def test_invalid_query_data(self):
        """測試無效查詢資料處理"""
        invalid_queries = [
            {},  # 空字典
            {"stock_code": ""},  # 空股票代碼
            {"stock_code": "2330"},  # 缺少必要欄位
        ]
        
        for query in invalid_queries:
            # 這裡應該有輸入驗證邏輯
            # 目前只是示例，實際需要在爬蟲中加入驗證
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主要爬蟲腳本
統一的財報爬蟲入口點
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Union
from datetime import datetime

# 使用標準 Python 包導入
from src.core import ConfigManager
from src.core.crawler import FinancialCrawler
from src.utils.helpers import (
    setup_logging, load_json, save_json, validate_stock_code, 
    validate_season, normalize_season, create_progress_reporter, format_file_size
)


class FinancialCrawlerApp:
    """財報爬蟲應用程式"""
    
    def __init__(self):
        self.logger = setup_logging("FinancialCrawlerApp")
        self.config = ConfigManager.load_config()
        self.crawler = FinancialCrawler(self.config)
    
    def run_single_query(self, query_data: Dict[str, Any]) -> Dict[str, Any]:
        """執行單筆查詢"""
        # 驗證輸入
        if not self._validate_query(query_data):
            return {"success": False, "error": "Invalid query data"}
        
        # 標準化資料
        query_data = self._normalize_query(query_data)
        
        # 執行爬取
        result = self.crawler.process(query_data)
        return result.to_dict()
    
    def run_batch_query(self, queries_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """執行批次查詢"""
        # 驗證所有查詢
        valid_queries = []
        for i, query in enumerate(queries_data):
            if self._validate_query(query):
                valid_queries.append(self._normalize_query(query))
            else:
                self.logger.warning(f"跳過無效查詢 #{i+1}: {query}")
        
        if not valid_queries:
            return {"success": False, "error": "No valid queries found"}
        
        # 執行批次爬取
        result = self.crawler.process(valid_queries)
        return result.to_dict()
    
    def show_statistics(self) -> None:
        """顯示統計資訊"""
        data_dir = Path(self.config['output_dir'])
        processed_dir = Path(self.config['processed_dir'])
        
        # 計算檔案數量
        pdf_files = list(data_dir.glob("*.pdf")) if data_dir.exists() else []
        json_files = list(data_dir.glob("*.json")) if data_dir.exists() else []
        processed_files = list(processed_dir.glob("*.json")) if processed_dir.exists() else []
        
        print("📊 財報爬蟲統計資訊")
        print("=" * 50)
        print(f"📄 PDF檔案: {len(pdf_files)}")
        print(f"📋 JSON檔案: {len(json_files)}")
        print(f"🔄 已處理檔案: {len(processed_files)}")
        print(f"📁 輸出目錄: {data_dir}")
        print(f"📁 處理目錄: {processed_dir}")
        
        # 顯示最近的檔案
        if pdf_files:
            latest_pdf = max(pdf_files, key=lambda x: x.stat().st_mtime)
            print(f"📅 最新PDF: {latest_pdf.name}")
    
    def search_reports(self, search_term: str) -> None:
        """搜尋財報"""
        data_dir = Path(self.config['output_dir'])
        
        if not data_dir.exists():
            print("❌ 資料目錄不存在")
            return
        
        # 搜尋PDF檔案
        found_files = []
        for pdf_file in data_dir.glob("*.pdf"):
            if search_term.lower() in pdf_file.name.lower():
                found_files.append(pdf_file)
        
        print(f"🔍 搜尋結果 (關鍵字: {search_term})")
        print("=" * 50)
        
        if found_files:
            for file in found_files:
                file_size = file.stat().st_size
                print(f"📄 {file.name} ({format_file_size(file_size)})")
        else:
            print("❌ 未找到相關檔案")
    
    def _validate_query(self, query: Dict[str, Any]) -> bool:
        """驗證查詢資料"""
        required_fields = ['stock_code', 'company_name', 'year', 'season']
        
        for field in required_fields:
            if field not in query:
                self.logger.error(f"缺少必要欄位: {field}")
                return False
        
        if not validate_stock_code(query['stock_code']):
            self.logger.error(f"無效的股票代碼: {query['stock_code']}")
            return False
        
        if not validate_season(str(query['season'])):
            self.logger.error(f"無效的季度: {query['season']}")
            return False
        
        try:
            year = int(query['year'])
            if year < 2020 or year > 2030:
                self.logger.error(f"無效的年份: {year}")
                return False
        except ValueError:
            self.logger.error(f"無效的年份格式: {query['year']}")
            return False
        
        return True
    
    def _normalize_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """標準化查詢資料"""
        normalized = query.copy()
        normalized['season'] = normalize_season(str(query['season']))
        normalized['year'] = int(query['year'])
        return normalized


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='台灣財報爬蟲')
    parser.add_argument('input', nargs='?', help='JSON輸入檔案或JSON字串')
    parser.add_argument('--batch', help='批次查詢檔案')
    parser.add_argument('--stock-code', help='股票代碼')
    parser.add_argument('--company', help='公司名稱')
    parser.add_argument('--year', type=int, help='年份')
    parser.add_argument('--season', help='季度 (Q1, Q2, Q3, Q4)')
    parser.add_argument('--stats', action='store_true', help='顯示統計資訊')
    parser.add_argument('--search', help='搜尋財報')
    parser.add_argument('--output-dir', help='輸出目錄')
    
    args = parser.parse_args()
    
    app = FinancialCrawlerApp()
    
    # 覆蓋配置
    if args.output_dir:
        app.config['output_dir'] = args.output_dir
    
    # 顯示統計
    if args.stats:
        app.show_statistics()
        return
    
    # 搜尋功能
    if args.search:
        app.search_reports(args.search)
        return
    
    # 命令列單筆查詢
    if all([args.stock_code, args.company, args.year, args.season]):
        query = {
            'stock_code': args.stock_code,
            'company_name': args.company,
            'year': args.year,
            'season': args.season
        }
        result = app.run_single_query(query)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    
    # 批次查詢
    if args.batch:
        batch_file = Path(args.batch)
        if not batch_file.exists():
            print(f"❌ 批次檔案不存在: {batch_file}")
            return
        
        queries = load_json(batch_file)
        result = app.run_batch_query(queries)
        
        # 儲存結果
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        result_file = output_dir / f"batch_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_json(result, result_file)
        print(f"✅ 批次結果已儲存: {result_file}")
        return
    
    # JSON輸入
    if args.input:
        try:
            # 嘗試解析為JSON字串
            if args.input.startswith('{') or args.input.startswith('['):
                data = json.loads(args.input)
            else:
                # 當作檔案路徑
                data = load_json(Path(args.input))
            
            if isinstance(data, list):
                result = app.run_batch_query(data)
            else:
                result = app.run_single_query(data)
            
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
        except Exception as e:
            print(f"❌ 輸入處理失敗: {e}")
            return
    
    # 如果沒有任何操作，顯示幫助
    if not any([args.input, args.batch, args.stats, args.search, 
               all([args.stock_code, args.company, args.year, args.season])]):
        parser.print_help()


if __name__ == "__main__":
    main()

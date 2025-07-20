#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
智慧處理腳本
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime

# 使用標準 Python 包導入
from src.processors.smart_processor import SmartFinancialProcessor
from src.utils.helpers import setup_logging, create_progress_reporter


class SmartProcessorApp:
    """智慧處理應用程式"""
    
    def __init__(self, config=None):
        self.logger = setup_logging("SmartProcessorApp")
        self.processor = SmartFinancialProcessor(config)
    
    def process_single(self, pdf_path: Path, json_path: Path, output_path: Path = None):
        """處理單一檔案"""
        self.logger.info(f"智慧處理: {pdf_path.name}")
        
        result = self.processor.process(pdf_path, json_path, output_path)
        
        if result.success:
            self.logger.info(f"✅ 處理成功: {result.message}")
            return result.data
        else:
            self.logger.error(f"❌ 處理失敗: {result.message}")
            return None
    
    def process_batch(self, data_dir: Path):
        """批次處理目錄中的所有檔案"""
        if not data_dir.exists():
            self.logger.error(f"目錄不存在: {data_dir}")
            return
        
        # 尋找PDF和對應的JSON檔案
        pdf_files = list(data_dir.glob("*.pdf"))
        file_pairs = []
        
        for pdf_file in pdf_files:
            json_file = pdf_file.with_suffix('.json')
            if json_file.exists():
                file_pairs.append((pdf_file, json_file))
            else:
                self.logger.warning(f"找不到對應的JSON檔案: {json_file}")
        
        if not file_pairs:
            self.logger.warning("未找到可處理的檔案對")
            return
        
        self.logger.info(f"找到 {len(file_pairs)} 個檔案對進行處理")
        
        # 批次處理
        progress = create_progress_reporter(len(file_pairs), "智慧處理")
        success_count = 0
        
        for pdf_path, json_path in file_pairs:
            try:
                result = self.process_single(pdf_path, json_path)
                if result:
                    success_count += 1
            except Exception as e:
                self.logger.error(f"處理 {pdf_path.name} 時發生錯誤: {e}")
            
            progress.update()
        
        progress.finish()
        self.logger.info(f"批次處理完成: {success_count}/{len(file_pairs)} 成功")
    
    def check_processed_status(self, data_dir: Path):
        """檢查處理狀態"""
        if not data_dir.exists():
            self.logger.error(f"目錄不存在: {data_dir}")
            return
        
        pdf_files = list(data_dir.glob("*.pdf"))
        processed_dir = data_dir / "processed"
        
        print("🔍 處理狀態檢查")
        print("=" * 50)
        print(f"📁 資料目錄: {data_dir}")
        print(f"📄 PDF檔案數量: {len(pdf_files)}")
        
        if processed_dir.exists():
            processed_files = list(processed_dir.glob("*_enhanced.json"))
            print(f"✅ 已處理檔案: {len(processed_files)}")
            print(f"🔄 待處理檔案: {len(pdf_files) - len(processed_files)}")
            
            # 顯示未處理的檔案
            processed_names = {f.name.replace('_enhanced.json', '.pdf') for f in processed_files}
            unprocessed = [f for f in pdf_files if f.name not in processed_names]
            
            if unprocessed:
                print("\n📋 待處理檔案:")
                for file in unprocessed[:10]:  # 只顯示前10個
                    print(f"  - {file.name}")
                if len(unprocessed) > 10:
                    print(f"  ... 還有 {len(unprocessed) - 10} 個檔案")
        else:
            print("❌ 尚未建立處理目錄")
    
    def backfill_single(self, enhanced_path: Path, original_path: Path):
        """回填單一檔案"""
        self.logger.info(f"開始回填: {enhanced_path.name} -> {original_path.name}")
        
        result = self.processor.backfill_to_original_json(enhanced_path, original_path)
        
        if result.success:
            self.logger.info(f"✅ 回填成功: {result.message}")
            if 'updated_fields' in result.data:
                updated_fields = result.data['updated_fields']
                total_updates = len(updated_fields['financials']) + len(updated_fields['income_statement'])
                self.logger.info(f"📊 更新了 {total_updates} 個財務欄位")
            return result.data
        else:
            self.logger.error(f"❌ 回填失敗: {result.message}")
            return None
    
    def backfill_batch(self, data_dir: Path):
        """批次回填目錄中的所有檔案"""
        self.logger.info(f"開始批次回填: {data_dir}")
        
        result = self.processor.batch_backfill(data_dir)
        
        if result.success:
            data = result.data
            self.logger.info(f"✅ 批次回填完成: {data['success_count']}/{data['total_files']} 成功")
            
            # 顯示詳細結果
            for file_result in data['results']:
                if file_result['success']:
                    self.logger.info(f"  ✅ {file_result['enhanced_file']} -> {file_result['original_file']}")
                else:
                    self.logger.error(f"  ❌ {file_result['enhanced_file']}: {file_result['message']}")
            
            return data
        else:
            self.logger.error(f"❌ 批次回填失敗: {result.message}")
            return None


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='智慧財報處理器')
    parser.add_argument('pdf_path', nargs='?', help='PDF檔案路徑')
    parser.add_argument('json_path', nargs='?', help='對應的JSON檔案路徑')
    parser.add_argument('-o', '--output', help='輸出檔案路徑')
    parser.add_argument('--batch', help='批次處理目錄')
    parser.add_argument('--status', help='檢查處理狀態的目錄')
    parser.add_argument('--config', help='配置檔案路徑')
    parser.add_argument('--backfill', help='回填增強數據到原始JSON')
    parser.add_argument('--backfill-batch', help='批次回填目錄中的所有檔案')
    parser.add_argument('--enhanced-file', help='增強JSON檔案路徑（用於單一回填）')
    parser.add_argument('--original-file', help='原始JSON檔案路徑（用於單一回填）')
    
    args = parser.parse_args()
    
    # 載入配置
    config = None
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
    
    app = SmartProcessorApp(config)
    
    # 檢查狀態
    if args.status:
        status_dir = Path(args.status)
        app.check_processed_status(status_dir)
        return
    
    # 批次處理
    if args.batch:
        batch_dir = Path(args.batch)
        app.process_batch(batch_dir)
        return
    
    # 單一檔案處理
    if args.pdf_path and args.json_path:
        pdf_path = Path(args.pdf_path)
        json_path = Path(args.json_path)
        output_path = Path(args.output) if args.output else None
        
        if not pdf_path.exists():
            print(f"❌ PDF檔案不存在: {pdf_path}")
            return
        
        if not json_path.exists():
            print(f"❌ JSON檔案不存在: {json_path}")
            return
        
        result = app.process_single(pdf_path, json_path, output_path)
        if result:
            print(f"✅ 處理完成: {result.get('output_path')}")
        return
    
    # 批次回填
    if args.backfill_batch:
        batch_dir = Path(args.backfill_batch)
        app.backfill_batch(batch_dir)
        return
    
    # 單一檔案回填
    if args.backfill and args.enhanced_file and args.original_file:
        enhanced_path = Path(args.enhanced_file)
        original_path = Path(args.original_file)
        
        if not enhanced_path.exists():
            print(f"❌ 增強JSON檔案不存在: {enhanced_path}")
            return
        
        if not original_path.exists():
            print(f"❌ 原始JSON檔案不存在: {original_path}")
            return
        
        result = app.backfill_single(enhanced_path, original_path)
        if result:
            print(f"✅ 回填完成")
        return

    # 如果沒有提供參數，顯示幫助
    parser.print_help()


if __name__ == "__main__":
    main()

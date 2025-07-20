#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
財務數據回填工具 - 整合版
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import os

# 添加專案根目錄到路徑
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# 使用相對導入
from src.processors.smart_processor import SmartFinancialProcessor
from src.utils.helpers import setup_logging


class FinancialDataBackfiller:
    """財務數據回填工具"""
    
    def __init__(self, config=None):
        self.logger = setup_logging("FinancialDataBackfiller")
        self.processor = SmartFinancialProcessor(config)
    
    def backfill_single_file(self, enhanced_path: Path, original_path: Path):
        """回填單一檔案"""
        self.logger.info(f"🔄 開始回填: {enhanced_path.name} -> {original_path.name}")
        
        result = self.processor.backfill_to_original_json(enhanced_path, original_path)
        
        if result.success:
            self.logger.info(f"✅ 回填成功!")
            
            # 顯示更新摘要
            if 'updated_fields' in result.data:
                self._show_update_summary(result.data['updated_fields'])
            
            return True
        else:
            self.logger.error(f"❌ 回填失敗: {result.message}")
            return False
    
    def backfill_directory(self, data_dir: Path):
        """回填目錄中的所有檔案"""
        self.logger.info(f"🔄 開始批次回填: {data_dir}")
        
        result = self.processor.batch_backfill(data_dir)
        
        if result.success:
            data = result.data
            self.logger.info(f"✅ 批次回填完成!")
            self.logger.info(f"📊 成功: {data['success_count']}/{data['total_files']} 檔案")
            
            # 顯示詳細結果
            print("\n📋 處理結果:")
            print("=" * 80)
            
            for file_result in data['results']:
                status = "✅" if file_result['success'] else "❌"
                print(f"{status} {file_result['enhanced_file']} -> {file_result['original_file']}")
                if not file_result['success']:
                    print(f"   錯誤: {file_result['message']}")
            
            return data
        else:
            self.logger.error(f"❌ 批次回填失敗: {result.message}")
            return None
    
    def _show_update_summary(self, updated_fields):
        """顯示更新摘要"""
        financials_updates = updated_fields.get('financials', [])
        income_updates = updated_fields.get('income_statement', [])
        
        total_updates = len(financials_updates) + len(income_updates)
        
        if total_updates == 0:
            print("   ℹ️  沒有欄位需要更新")
            return
        
        print(f"   📊 更新了 {total_updates} 個財務欄位:")
        
        if financials_updates:
            print("   💰 資產負債表:")
            for update in financials_updates:
                old_val = update['old_value'] if update['old_value'] is not None else "無"
                new_val = update['new_value']
                print(f"      - {update['field']}: {old_val} → {new_val}")
        
        if income_updates:
            print("   📈 損益表:")
            for update in income_updates:
                old_val = update['old_value'] if update['old_value'] is not None else "無"
                new_val = update['new_value']
                print(f"      - {update['field']}: {old_val} → {new_val}")
    
    def find_backfill_pairs(self, data_dir: Path):
        """尋找可以回填的檔案對"""
        processed_dir = data_dir / "processed"
        
        if not processed_dir.exists():
            self.logger.warning("找不到processed目錄")
            return []
        
        enhanced_files = list(processed_dir.glob("*_enhanced.json"))
        pairs = []
        
        for enhanced_file in enhanced_files:
            original_name = enhanced_file.name.replace('_enhanced.json', '.json')
            original_file = data_dir / original_name
            
            if original_file.exists():
                pairs.append({
                    'enhanced': enhanced_file,
                    'original': original_file,
                    'status': 'ready'
                })
            else:
                pairs.append({
                    'enhanced': enhanced_file,
                    'original': original_name,
                    'status': 'missing_original'
                })
        
        return pairs
    
    def show_status(self, data_dir: Path):
        """顯示回填狀態"""
        pairs = self.find_backfill_pairs(data_dir)
        
        print("🔍 回填狀態檢查")
        print("=" * 60)
        print(f"📁 資料目錄: {data_dir}")
        
        ready_pairs = [p for p in pairs if p['status'] == 'ready']
        missing_pairs = [p for p in pairs if p['status'] == 'missing_original']
        
        print(f"✅ 可回填檔案對: {len(ready_pairs)}")
        print(f"❌ 缺少原始檔案: {len(missing_pairs)}")
        
        if ready_pairs:
            print("\n📋 可回填的檔案:")
            for pair in ready_pairs[:10]:  # 只顯示前10個
                print(f"  - {pair['enhanced'].name} -> {pair['original'].name}")
            if len(ready_pairs) > 10:
                print(f"  ... 還有 {len(ready_pairs) - 10} 個檔案對")
        
        if missing_pairs:
            print("\n⚠️  缺少原始檔案:")
            for pair in missing_pairs:
                print(f"  - {pair['enhanced'].name} (找不到 {pair['original']})")


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description='財務數據回填工具')
    parser.add_argument('--enhanced', help='增強JSON檔案路徑')
    parser.add_argument('--original', help='原始JSON檔案路徑')
    parser.add_argument('--directory', help='批次處理目錄')
    parser.add_argument('--status', help='檢查回填狀態的目錄')
    parser.add_argument('--config', help='配置檔案路徑')
    
    args = parser.parse_args()
    
    # 載入配置
    config = None
    if args.config:
        config_path = Path(args.config)
        if config_path.exists():
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
    
    backfiller = FinancialDataBackfiller(config)
    
    # 檢查狀態
    if args.status:
        status_dir = Path(args.status)
        backfiller.show_status(status_dir)
        return
    
    # 批次回填
    if args.directory:
        directory_path = Path(args.directory)
        if not directory_path.exists():
            print(f"❌ 目錄不存在: {directory_path}")
            return
        
        backfiller.backfill_directory(directory_path)
        return
    
    # 單一檔案回填
    if args.enhanced and args.original:
        enhanced_path = Path(args.enhanced)
        original_path = Path(args.original)
        
        if not enhanced_path.exists():
            print(f"❌ 增強JSON檔案不存在: {enhanced_path}")
            return
        
        if not original_path.exists():
            print(f"❌ 原始JSON檔案不存在: {original_path}")
            return
        
        success = backfiller.backfill_single_file(enhanced_path, original_path)
        if success:
            print("🎉 回填完成!")
        return
    
    # 如果沒有提供參數，顯示幫助
    parser.print_help()


if __name__ == "__main__":
    main()

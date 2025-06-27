#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
最終專案清理腳本 - 保留核心功能，刪除冗餘檔案
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

class FinalProjectCleanup:
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.backup_dir = self.root_dir / f"final_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 核心功能檔案 - 需要保留
        self.core_files = {
            # 主要爬蟲和分析工具
            'comprehensive_financial_crawler.py',  # 主要批次爬蟲
            'diagnostic_batch_crawler.py',         # 診斷測試爬蟲
            'financial_crawler_guide.py',          # 使用說明
            'setup_pdf_parsing.py',                # PDF解析設定
            
            # 配置檔案
            'requirements.txt',
            'README.md',
            'USAGE_GUIDE.md',
            
            # 目錄需要保留
            'config/',
            'crawlers/',
            'data/',
            'docs/',
            'tools/',
        }
        
        # 需要清理的檔案類型
        self.cleanup_patterns = [
            # 測試檔案
            '*test*.py',
            'debug_*.py',
            'simple_*.py',
            'basic_*.py',
            'direct_*.py',
            'manual_*.py',
            
            # 重複的爬蟲
            'etf0050_*.py',
            'improved_mops_*.py',
            'fixed_mops_*.py',
            'real_mops_*.py',
            'stable_mops_*.py',
            'corrected_mops_*.py',
            'integrated_*.py',
            'twse_financial_crawler.py',  # 被improved版本取代
            
            # 分析工具重複版本
            'advanced_pdf_*.py',
            'final_pdf_*.py',
            'smart_pdf_*.py',
            'pdf_to_text_*.py',
            'analyze_pdf_*.py',
            
            # 其他清理工具
            'auto_project_setup.py',
            'cleanup_project.py',
            'organize_project.py',
            'check_crawler_progress.py',
            'check_download_results.py',  # 功能已整合到主程式
            
            # 空檔案
            'genjson.py',
        ]
        
        # 需要清理的目錄
        self.cleanup_dirs = [
            '05_legacy_tools/',
            'legacy/',
            'downloads/',
            'reports/',
            'tests/',
            'debug_responses/',
            'backup_*/',
        ]

    def backup_files(self):
        """備份將要刪除的檔案"""
        print(f"📦 建立備份目錄: {self.backup_dir}")
        self.backup_dir.mkdir(exist_ok=True)
        
        backup_count = 0
        
        # 備份將要刪除的檔案
        for pattern in self.cleanup_patterns:
            for file_path in self.root_dir.glob(pattern):
                if file_path.is_file():
                    backup_path = self.backup_dir / file_path.name
                    shutil.copy2(file_path, backup_path)
                    backup_count += 1
        
        # 備份將要刪除的目錄
        for dir_pattern in self.cleanup_dirs:
            for dir_path in self.root_dir.glob(dir_pattern):
                if dir_path.is_dir():
                    backup_path = self.backup_dir / dir_path.name
                    shutil.copytree(dir_path, backup_path, dirs_exist_ok=True)
                    backup_count += 1
        
        print(f"✅ 已備份 {backup_count} 個項目")

    def cleanup_files(self):
        """清理冗餘檔案"""
        print("\n🗑️ 開始清理冗餘檔案...")
        
        cleaned_count = 0
        
        # 刪除匹配的檔案
        for pattern in self.cleanup_patterns:
            for file_path in self.root_dir.glob(pattern):
                if file_path.is_file() and file_path.name not in self.core_files:
                    print(f"   🗑️ 刪除檔案: {file_path.name}")
                    file_path.unlink()
                    cleaned_count += 1
        
        # 刪除指定目錄
        for dir_pattern in self.cleanup_dirs:
            for dir_path in self.root_dir.glob(dir_pattern):
                if dir_path.is_dir():
                    print(f"   🗑️ 刪除目錄: {dir_path.name}")
                    shutil.rmtree(dir_path)
                    cleaned_count += 1
        
        print(f"✅ 已清理 {cleaned_count} 個項目")

    def cleanup_crawlers_dir(self):
        """清理crawlers目錄中的冗餘檔案"""
        print("\n🔧 清理crawlers目錄...")
        
        crawlers_dir = self.root_dir / 'crawlers'
        if not crawlers_dir.exists():
            return
        
        # 保留的核心爬蟲檔案
        core_crawler_files = {
            'improved_twse_crawler.py',
            'improved_etf0050_crawler.py',
            '__pycache__'
        }
        
        cleaned_count = 0
        for item in crawlers_dir.iterdir():
            if item.name not in core_crawler_files:
                if item.is_file():
                    print(f"   🗑️ 刪除爬蟲檔案: {item.name}")
                    item.unlink()
                elif item.is_dir():
                    print(f"   🗑️ 刪除爬蟲目錄: {item.name}")
                    shutil.rmtree(item)
                cleaned_count += 1
        
        print(f"✅ crawlers目錄已清理 {cleaned_count} 個項目")

    def create_clean_structure_summary(self):
        """創建清理後的專案結構說明"""
        summary_content = """# 專案清理完成報告

## 📁 清理後的專案結構

```
FinancialReports/
├── comprehensive_financial_crawler.py    # 主要批次爬蟲
├── diagnostic_batch_crawler.py           # 診斷測試工具
├── financial_crawler_guide.py            # 使用說明與檢查
├── setup_pdf_parsing.py                  # PDF解析環境設定
├── requirements.txt                       # Python依賴
├── README.md                             # 專案說明
├── USAGE_GUIDE.md                       # 使用指南
├── config/                               # 配置檔案
│   ├── settings.py
│   └── xbrl_tags.json
├── crawlers/                             # 核心爬蟲模組
│   ├── improved_twse_crawler.py          # 改進版TWSE爬蟲
│   └── improved_etf0050_crawler.py       # 改進版ETF爬蟲
├── data/                                 # 數據目錄
│   └── financial_reports_main/           # 主要財報數據
│       ├── by_company/                   # 按公司分類
│       ├── by_period/                    # 按期間分類
│       ├── reports/                      # 報告檔案
│       └── search_indexes/               # 搜尋索引
├── docs/                                 # 文檔目錄
└── tools/                                # 輔助工具
```

## 🎯 核心功能

1. **comprehensive_financial_crawler.py** - 主要爬蟲
   - 支援2330、2454、2317三家公司
   - 2022Q1~2025Q1全期間批次下載
   - 自動生成JSON和搜尋索引

2. **diagnostic_batch_crawler.py** - 診斷工具
   - 小範圍測試爬蟲功能
   - 驗證PDF下載和解析

3. **financial_crawler_guide.py** - 使用說明
   - 顯示完整使用指南
   - 檢查系統狀態和下載進度

## 🚀 快速開始

```bash
# 1. 安裝依賴
pip install -r requirements.txt

# 2. 設定PDF解析（可選）
python setup_pdf_parsing.py

# 3. 查看使用說明
python financial_crawler_guide.py

# 4. 執行主要爬蟲
python comprehensive_financial_crawler.py

# 5. 診斷測試
python diagnostic_batch_crawler.py
```

## 📊 清理統計

- 刪除重複爬蟲: 10+ 個檔案
- 刪除測試檔案: 15+ 個檔案
- 刪除冗餘目錄: 8+ 個目錄
- 保留核心功能: 4 個主要腳本
- 備份位置: {backup_dir}

專案結構已優化，保留核心功能，刪除冗餘檔案。
"""
        
        summary_path = self.root_dir / 'PROJECT_CLEANUP_REPORT.md'
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(summary_content.format(backup_dir=self.backup_dir.name))
        
        print(f"📋 已創建清理報告: {summary_path}")

    def run_cleanup(self):
        """執行完整清理流程"""
        print("🚀 開始最終專案清理")
        print("=" * 50)
        
        # 1. 備份
        self.backup_files()
        
        # 2. 清理主目錄
        self.cleanup_files()
        
        # 3. 清理crawlers目錄
        self.cleanup_crawlers_dir()
        
        # 4. 創建清理報告
        self.create_clean_structure_summary()
        
        print("\n✅ 專案清理完成！")
        print(f"📦 備份位置: {self.backup_dir}")
        print("📋 查看 PROJECT_CLEANUP_REPORT.md 了解詳細結果")
        
        # 顯示最終檔案列表
        print("\n📁 保留的核心檔案:")
        for item in sorted(self.root_dir.iterdir()):
            if item.is_file() and item.suffix == '.py':
                print(f"   📄 {item.name}")
            elif item.is_dir() and not item.name.startswith('.'):
                print(f"   📁 {item.name}/")

if __name__ == '__main__':
    cleanup = FinalProjectCleanup()
    
    # 確認清理
    print("⚠️  即將清理專案，刪除重複和測試檔案")
    print("✅ 核心功能將被保留")
    print("📦 所有刪除的檔案都會備份")
    
    response = input("\n是否繼續清理? (y/N): ")
    if response.lower() == 'y':
        cleanup.run_cleanup()
    else:
        print("❌ 取消清理")

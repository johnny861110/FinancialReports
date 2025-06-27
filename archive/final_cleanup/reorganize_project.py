#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
專案資料夾整理腳本
清理重複檔案、整理目錄結構、統一管理不必要的內容
"""

import shutil
import json
from pathlib import Path
from datetime import datetime

def create_archive_folder():
    """建立歷史檔案存檔資料夾"""
    archive_path = Path(__file__).parent / "archive"
    archive_path.mkdir(exist_ok=True)
    
    # 建立子資料夾
    (archive_path / "old_docs").mkdir(exist_ok=True)
    (archive_path / "old_reports").mkdir(exist_ok=True)
    (archive_path / "duplicate_files").mkdir(exist_ok=True)
    (archive_path / "backup_data").mkdir(exist_ok=True)
    
    return archive_path

def identify_duplicate_docs():
    """識別重複的文檔檔案"""
    base_path = Path(__file__).parent
    
    # 根目錄中的重複檔案
    root_duplicates = [
        "FINAL_STATUS.md",
        "NEW_TARGETS_TEST_REPORT.md", 
        "PROJECT_COMPLETION_REPORT.md",
        "PROJECT_FINAL_STATUS.md",
        "PROJECT_STRUCTURE.md",
        "SIMPLIFIED_USAGE.md",
        "TEST_COMPLETION_REPORT.md",
        "USER_GUIDE.md"
    ]
    
    # docs 資料夾中重複的檔案
    docs_duplicates = [
        "docs/QUICK_START.md",  # 根目錄已有
        "docs/README.md"        # 可能重複
    ]
    
    return root_duplicates, docs_duplicates

def identify_redundant_data():
    """識別冗餘的資料檔案"""
    redundant_dirs = [
        "data/diagnostic_results",  # 診斷結果，可歸檔
        "data/financial_reports_main",  # 重複目錄
        "backup"  # 舊備份資料夾
    ]
    
    return redundant_dirs

def move_to_archive(source_path, archive_path, category):
    """移動檔案到存檔資料夾"""
    if isinstance(source_path, str):
        source_path = Path(source_path)
    
    if not source_path.exists():
        print(f"   ⚠️ 檔案不存在: {source_path}")
        return False
    
    target_dir = archive_path / category
    target_path = target_dir / source_path.name
    
    try:
        if source_path.is_dir():
            if target_path.exists():
                shutil.rmtree(target_path)
            shutil.move(str(source_path), str(target_path))
            print(f"   📁 移動目錄: {source_path} -> archive/{category}/")
        else:
            shutil.move(str(source_path), str(target_path))
            print(f"   📄 移動檔案: {source_path} -> archive/{category}/")
        return True
    except Exception as e:
        print(f"   ❌ 移動失敗: {source_path} - {e}")
        return False

def cleanup_empty_dirs(base_path):
    """清理空資料夾"""
    empty_dirs = []
    
    for path in Path(base_path).rglob("*"):
        if path.is_dir() and not any(path.iterdir()):
            empty_dirs.append(path)
    
    for empty_dir in empty_dirs:
        try:
            empty_dir.rmdir()
            print(f"   🗑️ 刪除空資料夾: {empty_dir}")
        except Exception as e:
            print(f"   ⚠️ 無法刪除資料夾: {empty_dir} - {e}")

def create_cleanup_summary(archive_path, moved_files, moved_dirs):
    """建立清理摘要檔案"""
    summary = {
        "cleanup_date": datetime.now().isoformat(),
        "total_moved_files": len(moved_files),
        "total_moved_dirs": len(moved_dirs),
        "moved_files": moved_files,
        "moved_directories": moved_dirs,
        "archive_location": str(archive_path),
        "description": "專案整理 - 移除重複和不必要的檔案"
    }
    
    summary_file = archive_path / "cleanup_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"   📊 清理摘要已儲存: {summary_file}")

def reorganize_project():
    """重新組織專案結構"""
    print("🗂️ 重新組織專案結構")
    print("-" * 40)
    
    base_path = Path(__file__).parent
    archive_path = create_archive_folder()
    
    moved_files = []
    moved_dirs = []
    
    print("1️⃣ 處理重複文檔...")
    
    # 處理根目錄重複檔案
    root_duplicates, docs_duplicates = identify_duplicate_docs()
    
    for file_name in root_duplicates:
        file_path = base_path / file_name
        if move_to_archive(file_path, archive_path, "old_docs"):
            moved_files.append(str(file_path))
    
    # 處理docs中的重複檔案  
    for file_path in docs_duplicates:
        full_path = base_path / file_path
        if move_to_archive(full_path, archive_path, "duplicate_files"):
            moved_files.append(str(full_path))
    
    print("\n2️⃣ 處理冗餘資料目錄...")
    
    redundant_dirs = identify_redundant_data()
    for dir_path in redundant_dirs:
        full_path = base_path / dir_path
        if move_to_archive(full_path, archive_path, "backup_data"):
            moved_dirs.append(str(full_path))
    
    print("\n3️⃣ 清理空資料夾...")
    cleanup_empty_dirs(base_path)
    
    print("\n4️⃣ 建立清理摘要...")
    create_cleanup_summary(archive_path, moved_files, moved_dirs)
    
    return len(moved_files), len(moved_dirs)

def show_new_structure():
    """顯示整理後的專案結構"""
    print("\n📁 整理後的專案結構:")
    print("=" * 50)
    
    structure = """
FinancialReports/
├── 📄 financial_crawler.py        # 主要爬蟲程式
├── 📄 test_crawler.py             # 測試腳本
├── 📄 requirements.txt            # 依賴套件
├── 📄 QUICK_START.md             # 快速開始指南
├── 📁 config/                    # 設定檔
├── 📁 data/                      # 資料目錄
│   ├── 📄 master_index.json      # 主索引檔案
│   ├── 📁 financial_reports/     # 財報檔案
│   └── 📁 test_results/          # 測試結果
├── 📁 examples/                  # 範例檔案
│   ├── 📄 single_query.json      # 單筆查詢範例
│   ├── 📄 batch_query.json       # 批次查詢範例
│   └── 📄 demo_master_index.py   # 主索引示範
├── 📁 scripts/                   # 工具腳本
│   ├── 📄 rebuild_master_index.py # 重建主索引
│   ├── 📁 crawlers/              # 爬蟲工具
│   ├── 📁 tests/                 # 測試工具
│   ├── 📁 tools/                 # 輔助工具
│   └── 📁 validation/            # 驗證工具
├── 📁 docs/                      # 文檔目錄
│   ├── 📁 guides/                # 使用指南
│   └── 📁 reports/               # 測試報告
├── 📁 output/                    # 輸出目錄
└── 📁 archive/                   # 存檔目錄 (新增)
    ├── 📁 old_docs/              # 舊文檔
    ├── 📁 old_reports/           # 舊報告
    ├── 📁 duplicate_files/       # 重複檔案
    └── 📁 backup_data/           # 備份資料
"""
    
    print(structure)

def main():
    """主程式"""
    print("🧹 專案資料夾整理工具")
    print("=" * 50)
    print("此工具將:")
    print("• 移除重複的文檔檔案")
    print("• 整理冗餘的資料目錄") 
    print("• 建立統一的存檔資料夾")
    print("• 清理空資料夾")
    print("• 優化專案結構")
    print("=" * 50)
    
    # 確認執行
    response = input("🤔 確定要執行整理嗎？(y/N): ").strip().lower()
    if response != 'y':
        print("❌ 取消整理")
        return
    
    print("\n🚀 開始整理...")
    
    try:
        moved_files, moved_dirs = reorganize_project()
        
        print(f"\n✅ 整理完成!")
        print(f"   📄 移動檔案: {moved_files} 個")
        print(f"   📁 移動目錄: {moved_dirs} 個")
        print(f"   🗂️ 存檔位置: archive/")
        
        show_new_structure()
        
        print("\n🎯 建議後續動作:")
        print("1. 檢查 archive/ 資料夾確認移動的檔案")
        print("2. 測試主要功能: python financial_crawler.py --stats")
        print("3. 執行完整測試: python test_crawler.py")
        print("4. 如確認無問題，可刪除 archive/ 資料夾")
        
    except Exception as e:
        print(f"❌ 整理過程發生錯誤: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())

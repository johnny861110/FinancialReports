#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
專案清理工具
刪除不必要的檔案和資料夾，保持專案整潔
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def cleanup_project():
    """清理專案中的不必要內容"""
    
    print("🧹 開始清理專案不必要內容...")
    print("=" * 50)
    
    project_root = Path(__file__).parent
    
    # 要刪除的資料夾清單
    folders_to_remove = [
        "final_backup_20250627_005036",  # 舊備份
        "debug_responses",               # 調試回應（已移動到data/debug_logs）
        "crawlers",                      # 舊版爬蟲目錄（已移動到scripts/crawlers/legacy）
        "tools",                         # 舊版工具目錄（已移動到scripts/tools/legacy）
    ]
    
    # 要刪除的檔案清單
    files_to_remove = [
        "organize_project.py",           # 空的組織腳本
        "organize_project_simple.py",   # 簡化版組織腳本（已完成任務）
        "__pycache__",                   # Python緩存目錄
    ]
    
    # 要保留但可能重複的檔案（檢查後決定）
    duplicate_files = [
        "docs/QUICK_START.md",           # 可能與根目錄重複
        "docs/README.md",                # 可能與guides中重複
    ]
    
    removed_count = 0
    
    # 刪除不必要的資料夾
    print("📁 刪除不必要的資料夾...")
    for folder_name in folders_to_remove:
        folder_path = project_root / folder_name
        if folder_path.exists() and folder_path.is_dir():
            try:
                shutil.rmtree(folder_path)
                print(f"   ✅ 已刪除資料夾: {folder_name}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ 刪除失敗 {folder_name}: {e}")
        else:
            print(f"   ⚠️ 資料夾不存在: {folder_name}")
    
    # 刪除不必要的檔案
    print("\n📄 刪除不必要的檔案...")
    for file_name in files_to_remove:
        file_path = project_root / file_name
        if file_path.exists():
            try:
                if file_path.is_file():
                    file_path.unlink()
                    print(f"   ✅ 已刪除檔案: {file_name}")
                elif file_path.is_dir():
                    shutil.rmtree(file_path)
                    print(f"   ✅ 已刪除目錄: {file_name}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ 刪除失敗 {file_name}: {e}")
        else:
            print(f"   ⚠️ 檔案不存在: {file_name}")
    
    # 檢查重複檔案
    print("\n🔍 檢查可能重複的檔案...")
    for file_path_str in duplicate_files:
        file_path = project_root / file_path_str
        if file_path.exists():
            file_size = file_path.stat().st_size
            print(f"   📄 {file_path_str} ({file_size} bytes)")
            
            # 檢查是否有對應的檔案在其他位置
            if "QUICK_START.md" in file_path_str:
                root_quick_start = project_root / "QUICK_START.md"
                if root_quick_start.exists():
                    root_size = root_quick_start.stat().st_size
                    print(f"   📄 QUICK_START.md (根目錄) ({root_size} bytes)")
                    if file_size == root_size:
                        try:
                            file_path.unlink()
                            print(f"   ✅ 刪除重複檔案: {file_path_str}")
                            removed_count += 1
                        except Exception as e:
                            print(f"   ❌ 刪除失敗: {e}")
    
    # 清理空的資料夾
    print("\n📂 清理空的資料夾...")
    empty_folders = []
    for root, dirs, files in os.walk(project_root):
        for dir_name in dirs:
            dir_path = Path(root) / dir_name
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                empty_folders.append(dir_path)
    
    for empty_folder in empty_folders:
        try:
            empty_folder.rmdir()
            print(f"   ✅ 已刪除空資料夾: {empty_folder.relative_to(project_root)}")
            removed_count += 1
        except Exception as e:
            print(f"   ❌ 刪除空資料夾失敗 {empty_folder.name}: {e}")
    
    # 清理__pycache__目錄
    print("\n🐍 清理Python緩存檔案...")
    pycache_dirs = list(project_root.rglob("__pycache__"))
    for pycache_dir in pycache_dirs:
        try:
            shutil.rmtree(pycache_dir)
            print(f"   ✅ 已刪除緩存: {pycache_dir.relative_to(project_root)}")
            removed_count += 1
        except Exception as e:
            print(f"   ❌ 刪除緩存失敗: {e}")
    
    # 清理.pyc檔案
    pyc_files = list(project_root.rglob("*.pyc"))
    for pyc_file in pyc_files:
        try:
            pyc_file.unlink()
            print(f"   ✅ 已刪除.pyc檔案: {pyc_file.relative_to(project_root)}")
            removed_count += 1
        except Exception as e:
            print(f"   ❌ 刪除.pyc檔案失敗: {e}")
    
    return removed_count

def show_final_structure():
    """顯示清理後的專案結構"""
    
    print("\n📁 清理後的專案結構:")
    print("=" * 40)
    
    project_root = Path(__file__).parent
    
    # 只顯示主要目錄和重要檔案
    important_items = [
        "scripts/",
        "data/",
        "docs/",
        "config/",
        "backup/",
        "output/",
        "QUICK_START.md",
        "PROJECT_STRUCTURE.md",
        "requirements.txt"
    ]
    
    for item in important_items:
        item_path = project_root / item
        if item_path.exists():
            if item_path.is_dir():
                # 計算目錄中的檔案數量
                file_count = len([f for f in item_path.rglob('*') if f.is_file()])
                print(f"📁 {item} ({file_count} 檔案)")
            else:
                file_size = item_path.stat().st_size
                print(f"📄 {item} ({file_size:,} bytes)")
        else:
            print(f"❌ {item} (不存在)")

def create_cleanup_report():
    """建立清理報告"""
    
    report_content = f"""# 專案清理報告

## 清理摘要

**清理時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**清理工具**: cleanup_project.py  

## 已刪除的內容

### 🗂️ 資料夾
- `final_backup_20250627_005036/` - 舊備份資料夾
- `debug_responses/` - 調試回應（已移動至data/debug_logs/）
- `crawlers/` - 舊版爬蟲目錄（已移動至scripts/crawlers/legacy/）
- `tools/` - 舊版工具目錄（已移動至scripts/tools/legacy/）

### 📄 檔案
- `organize_project.py` - 空的組織腳本
- `organize_project_simple.py` - 已完成任務的組織腳本
- `__pycache__/` - Python緩存目錄
- `*.pyc` - Python編譯檔案

### 🔄 重複檔案
- 檢查並清理重複的文件檔案

## 保留的核心內容

### 🔧 腳本檔案
- `scripts/crawlers/` - 爬蟲腳本
- `scripts/tests/` - 測試腳本
- `scripts/validation/` - 驗證腳本
- `scripts/tools/` - 工具腳本

### 💾 數據檔案
- `data/financial_reports/` - 主要財報數據
- `data/test_results/` - 測試結果
- `data/debug_logs/` - 調試記錄

### 📚 文件資料
- `docs/guides/` - 使用指南
- `docs/reports/` - 報告文件

### ⚙️ 配置和其他
- `config/` - 配置檔案
- `backup/` - 備份目錄
- `requirements.txt` - Python套件需求

## 清理效果

- ✅ 移除重複和過時的檔案
- ✅ 清理Python緩存檔案  
- ✅ 刪除空的資料夾
- ✅ 保持核心功能完整
- ✅ 維持清晰的專案結構

## 下一步建議

1. 檢查 `QUICK_START.md` 開始使用
2. 使用 `scripts/tests/improved_2330_test.py` 驗證功能
3. 查看 `docs/guides/HOW_TO_CRAWL.md` 了解詳細用法

---
**清理完成**: ✅ 專案已優化整理完畢
"""
    
    report_path = Path(__file__).parent / "docs" / "reports" / "CLEANUP_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report_content)
    
    print(f"\n📋 清理報告已建立: {report_path}")

def main():
    """主程式"""
    print("🧹 專案清理工具")
    print("=" * 50)
    
    start_time = datetime.now()
    
    # 執行清理
    removed_count = cleanup_project()
    
    # 顯示清理後結構
    show_final_structure()
    
    # 建立清理報告
    create_cleanup_report()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n✅ 清理完成！")
    print(f"🗑️ 共刪除 {removed_count} 個項目")
    print(f"⏱️ 耗時: {duration:.1f} 秒")
    
    print(f"\n📋 建議下一步:")
    print(f"   1. 檢查 QUICK_START.md 開始使用")
    print(f"   2. 驗證核心功能正常運作")
    print(f"   3. 查看 docs/reports/CLEANUP_REPORT.md")

if __name__ == '__main__':
    main()

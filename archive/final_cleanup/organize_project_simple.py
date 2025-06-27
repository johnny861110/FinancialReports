#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
專案資料夾整理工具
重新組織和清理財報爬蟲專案結構
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

def organize_project():
    """整理專案資料夾結構"""
    
    print("🗂️  開始整理專案資料夾...")
    print("=" * 50)
    
    project_root = Path(__file__).parent
    
    # 定義新的資料夾結構
    folders_to_create = [
        "scripts/crawlers",           # 爬蟲腳本
        "scripts/tests",              # 測試腳本  
        "scripts/tools",              # 工具腳本
        "scripts/validation",         # 驗證腳本
        "data/financial_reports",     # 主要財報數據
        "data/test_results",          # 測試結果
        "data/debug_logs",            # 調試記錄
        "docs/reports",               # 報告文件
        "docs/guides",                # 使用指南
        "backup/archives",            # 備份存檔
        "config/settings",            # 配置檔案
        "output/downloads",           # 下載檔案
        "output/logs"                 # 運行日誌
    ]
    
    # 建立資料夾結構
    print("📁 建立資料夾結構...")
    for folder in folders_to_create:
        folder_path = project_root / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {folder}")
    
    return True

def main():
    """主程式"""
    print("🗂️  財報爬蟲專案整理工具")
    print("=" * 50)
    
    start_time = datetime.now()
    
    # 整理專案結構
    success = organize_project()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    if success:
        print(f"\n✅ 整理完成，耗時: {duration:.1f} 秒")
    else:
        print(f"\n❌ 整理失敗")

if __name__ == '__main__':
    main()

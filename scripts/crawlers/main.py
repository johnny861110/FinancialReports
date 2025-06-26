#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
財報爬蟲系統主要入口
提供簡單的界面來執行各種財報相關任務
"""

import subprocess
import sys
from pathlib import Path

def show_menu():
    """顯示主菜單"""
    print("\n" + "="*60)
    print("📊 ETF 0050財報爬蟲與分析系統")
    print("="*60)
    print("1. 📚 查看使用說明與系統狀態")
    print("2. 🚀 執行完整財報爬取 (2330、2454、2317)")
    print("3. 🔍 診斷測試爬蟲功能")
    print("4. ⚙️  設定PDF解析環境")
    print("5. 📋 查看專案結構")
    print("6. ❌ 退出")
    print("="*60)

def run_script(script_name, description=""):
    """執行指定的腳本"""
    print(f"\n🚀 執行: {description or script_name}")
    print("-" * 40)
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=False, 
                              text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"❌ 執行失敗: {e}")
        return False

def show_project_structure():
    """顯示專案結構"""
    print("\n📁 專案結構:")
    print("-" * 40)
    
    root = Path(__file__).parent
    
    # 顯示主要檔案
    main_files = [
        ('comprehensive_financial_crawler.py', '主要批次爬蟲'),
        ('diagnostic_batch_crawler.py', '診斷測試工具'),
        ('financial_crawler_guide.py', '使用說明與檢查'),
        ('setup_pdf_parsing.py', 'PDF解析設定'),
        ('requirements.txt', 'Python依賴')
    ]
    
    print("📄 主要檔案:")
    for filename, desc in main_files:
        if (root / filename).exists():
            print(f"   ✅ {filename:<35} - {desc}")
        else:
            print(f"   ❌ {filename:<35} - {desc}")
    
    # 顯示主要目錄
    main_dirs = [
        ('config/', '配置檔案'),
        ('crawlers/', '核心爬蟲模組'),
        ('data/', '數據目錄'),
        ('docs/', '文檔目錄'),
        ('tools/', '輔助工具')
    ]
    
    print("\n📁 主要目錄:")
    for dirname, desc in main_dirs:
        if (root / dirname).exists():
            print(f"   ✅ {dirname:<35} - {desc}")
        else:
            print(f"   ❌ {dirname:<35} - {desc}")
    
    # 顯示數據狀態
    data_dir = root / 'data' / 'financial_reports_main'
    if data_dir.exists():
        pdf_count = len(list(data_dir.rglob("*.pdf")))
        json_count = len(list(data_dir.rglob("*.json")))
        print(f"\n📊 數據狀態:")
        print(f"   📄 PDF檔案: {pdf_count} 個")
        print(f"   🔧 JSON檔案: {json_count} 個")

def main():
    """主程式"""
    while True:
        show_menu()
        
        try:
            choice = input("\n請選擇功能 (1-6): ").strip()
            
            if choice == '1':
                run_script('financial_crawler_guide.py', '查看使用說明與系統狀態')
                
            elif choice == '2':
                print("\n⚠️  注意：這將下載2330、2454、2317三家公司")
                print("   2022Q1~2025Q1共39個期間的財報")
                confirm = input("   是否繼續? (y/N): ").strip().lower()
                if confirm == 'y':
                    run_script('comprehensive_financial_crawler.py', '執行完整財報爬取')
                else:
                    print("❌ 取消執行")
                    
            elif choice == '3':
                run_script('diagnostic_batch_crawler.py', '診斷測試爬蟲功能')
                
            elif choice == '4':
                run_script('setup_pdf_parsing.py', '設定PDF解析環境')
                
            elif choice == '5':
                show_project_structure()
                
            elif choice == '6':
                print("\n👋 感謝使用！")
                break
                
            else:
                print("❌ 無效選項，請選擇1-6")
                
        except KeyboardInterrupt:
            print("\n\n👋 程式已中斷")
            break
        except Exception as e:
            print(f"\n❌ 發生錯誤: {e}")
        
        # 等待用戶按鍵繼續
        if choice in ['1', '3', '4', '5']:
            input("\n按Enter鍵繼續...")

if __name__ == '__main__':
    main()

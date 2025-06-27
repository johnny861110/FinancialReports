#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🚀 財報爬蟲系統 - 快速入門示範

這個腳本將引導您完成：
1. 系統狀態檢查
2. 搜尋現有財報
3. 下載新的財報
4. 驗證下載結果
"""

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    """執行命令並顯示結果"""
    print(f"\n🔧 {description}")
    print("=" * 50)
    print(f"📝 執行命令: {cmd}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, text=True, cwd=Path(__file__).parent)
        if result.returncode == 0:
            print("✅ 執行成功")
        else:
            print("⚠️ 執行完成（可能有警告）")
        return True
    except Exception as e:
        print(f"❌ 執行失敗: {e}")
        return False

def main():
    """主示範程式"""
    print("🏢 台灣上市公司財報爬蟲系統 - 快速入門")
    print("=" * 60)
    print("🎯 本示範將引導您體驗系統的主要功能")
    print("⏱️ 預計需要 3-5 分鐘")
    print("=" * 60)
    
    # 確認開始
    response = input("\n🤔 是否開始示範？(Y/n): ").strip().lower()
    if response == 'n':
        print("👋 感謝您的關注！")
        return
    
    print("\n🚀 開始快速入門示範...")
    
    # 步驟1：檢查系統狀態
    run_command(
        "python financial_crawler.py --stats",
        "步驟1: 檢查系統狀態和現有財報"
    )
    
    input("\n⏸️ 按 Enter 鍵繼續下一步...")
    
    # 步驟2：搜尋示範
    print("\n📊 接下來示範搜尋功能...")
    
    run_command(
        "python financial_crawler.py --search 台積電",
        "步驟2a: 搜尋台積電相關財報"
    )
    
    run_command(
        "python financial_crawler.py --year 2024 --season 1",
        "步驟2b: 搜尋2024年第1季所有財報"
    )
    
    input("\n⏸️ 按 Enter 鍵繼續下一步...")
    
    # 步驟3：下載示範
    print("\n💾 接下來示範下載功能...")
    print("🎯 我們將下載一份範例財報（如果尚未存在）")
    
    response = input("📥 是否繼續下載示範？(Y/n): ").strip().lower()
    if response != 'n':
        run_command(
            "python financial_crawler.py examples/single_query.json",
            "步驟3: 下載範例財報"
        )
        
        input("\n⏸️ 按 Enter 鍵繼續下一步...")
        
        # 再次檢查狀態
        run_command(
            "python financial_crawler.py --stats",
            "步驟4: 確認下載結果（統計應該有變化）"
        )
    
    # 步驟4：測試功能
    print("\n🧪 最後，我們執行功能測試...")
    response = input("🔍 是否執行完整功能測試？(y/N): ").strip().lower()
    if response == 'y':
        run_command(
            "python test_crawler.py",
            "步驟5: 執行完整功能測試"
        )
    
    # 總結
    print("\n" + "=" * 60)
    print("🎉 快速入門示範完成！")
    print("=" * 60)
    
    print("\n📋 您已學會的功能:")
    print("✅ 檢查系統狀態: python financial_crawler.py --stats")
    print("✅ 搜尋功能: python financial_crawler.py --search [關鍵字]")
    print("✅ 下載財報: python financial_crawler.py examples/single_query.json")
    print("✅ 功能測試: python test_crawler.py")
    
    print("\n📚 進一步學習:")
    print("📖 完整說明: 查看 README.md")
    print("🚀 快速指南: 查看 QUICK_START.md")
    print("📂 範例檔案: 查看 examples/ 目錄")
    
    print("\n💡 提示:")
    print("• 修改 examples/single_query.json 來下載其他公司財報")
    print("• 使用 examples/batch_query.json 進行批次下載")
    print("• 查看 data/financial_reports/ 目錄中下載的檔案")
    
    print("\n🎯 現在您可以開始正式使用系統了！")

if __name__ == '__main__':
    main()

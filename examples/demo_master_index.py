#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主索引功能示範腳本
展示財報搜尋與統計功能
"""

import sys
from pathlib import Path

# 添加父目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

def demo_master_index():
    """示範主索引功能"""
    print("🗂️ 財報主索引功能示範")
    print("=" * 50)
    
    print("\n1️⃣ 查看統計資訊:")
    print("   命令: python financial_crawler.py --stats")
    print("   顯示: 總報告數、各公司分布、最新記錄等")
    
    print("\n2️⃣ 關鍵字搜尋:")
    print("   命令: python financial_crawler.py --search 台積電")
    print("   說明: 在股票代碼和公司名稱中搜尋")
    
    print("\n3️⃣ 股票代碼搜尋:")
    print("   命令: python financial_crawler.py --stock-code 2317")
    print("   說明: 精確搜尋特定股票代碼")
    
    print("\n4️⃣ 公司名稱搜尋:")
    print("   命令: python financial_crawler.py --company 鴻海")
    print("   說明: 模糊搜尋公司名稱")
    
    print("\n5️⃣ 年度季度搜尋:")
    print("   命令: python financial_crawler.py --year 2024 --season 1")
    print("   說明: 搜尋特定年度和季度的所有財報")
    
    print("\n6️⃣ 組合搜尋:")
    print("   命令: python financial_crawler.py --company 台積電 --year 2024")
    print("   說明: 多個條件組合搜尋")
    
    print("\n🔧 自動功能:")
    print("   • 每次下載財報時自動更新主索引")
    print("   • 記錄下載狀態、檔案大小、時間等")
    print("   • 支援失敗記錄追蹤")
    print("   • 檔案存在性驗證")
    
    print("\n📁 主索引檔案位置:")
    index_file = Path(__file__).parent.parent / "data" / "master_index.json"
    print(f"   {index_file}")
    
    if index_file.exists():
        print("   ✅ 檔案存在")
        size_kb = index_file.stat().st_size / 1024
        print(f"   📏 檔案大小: {size_kb:.1f} KB")
    else:
        print("   ❌ 檔案不存在，請先下載財報或執行重建腳本")
    
    print(f"\n🛠️ 主索引重建:")
    print("   命令: python scripts/rebuild_master_index.py")
    print("   說明: 掃描現有財報檔案重建主索引")

def demo_search_examples():
    """示範具體搜尋範例"""
    print("\n" + "=" * 50)
    print("🔍 搜尋功能實際範例")
    print("=" * 50)
    
    # 模擬執行搜尋命令的輸出
    examples = [
        {
            "command": "python financial_crawler.py --stats",
            "description": "統計資訊",
            "sample_output": """📊 財報主索引統計
========================================
總報告數: 7
最後更新: 2025-06-27T18:55:59
📈 各公司報告數:
   台積電: 1 份
   鴻海: 2 份
   國泰金: 1 份
🕒 最新下載記錄:
   1. 國泰金(2882) 2024Q1 ✅
   2. 台積電(2330) 2024Q1 ✅"""
        },
        {
            "command": "python financial_crawler.py --search 台積電",
            "description": "搜尋台積電",
            "sample_output": """🔍 搜尋結果: 找到 1 筆記錄
--------------------------------------------------
1. 台積電(2330) 2024Q1 ✅
   檔案: data/financial_reports/202401_2330_AI1.pdf
   大小: 7.7MB
   時間: 2025-06-27T18:43:08"""
        },
        {
            "command": "python financial_crawler.py --year 2024 --season 1",
            "description": "搜尋2024Q1所有財報",
            "sample_output": """🔍 搜尋結果: 找到 4 筆記錄
--------------------------------------------------
1. 國泰金(2882) 2024Q1 ✅
2. 富邦金(2881) 2024Q1 ✅
3. 聯發科(2454) 2024Q1 ✅
4. 台積電(2330) 2024Q1 ✅"""
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}️⃣ {example['description']}")
        print(f"   命令: {example['command']}")
        print("   輸出:")
        for line in example['sample_output'].split('\n'):
            print(f"      {line}")

def main():
    """主程式"""
    demo_master_index()
    demo_search_examples()
    
    print("\n" + "=" * 50)
    print("🎯 快速開始建議:")
    print("1. python financial_crawler.py --stats  (查看統計)")
    print("2. python financial_crawler.py --search 台積電  (搜尋測試)")
    print("3. 下載新的財報來測試自動更新功能")
    print("=" * 50)

if __name__ == '__main__':
    main()

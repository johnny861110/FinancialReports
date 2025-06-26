#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
財報爬蟲與解析功能使用說明
"""

def show_usage_guide():
    """顯示使用說明"""
    
    print("📚 ETF 0050財報爬蟲與解析系統使用說明")
    print("=" * 60)
    
    print("\n🎯 主要功能:")
    print("1. ✅ 自動爬取TWSE財報PDF檔案")
    print("2. ✅ 生成標準化財報JSON格式")
    print("3. ✅ 創建搜尋索引檔案")
    print("4. ✅ 批次處理多公司多期間")
    print("5. ⚠️  PDF內容解析（需要PyPDF2）")
    
    print("\n📁 檔案結構:")
    print("data/diagnostic_results/")
    print("├── 2330/")
    print("│   ├── 2024Q1/")
    print("│   │   ├── 202401_2330_AI1.pdf")
    print("│   │   └── 202401_2330_AI1.json")
    print("│   └── 2024Q2/")
    print("├── 2454/")
    print("├── 2317/")
    print("├── diagnostic_report_*.json")
    print("└── financial_search_index_*.json")
    
    print("\n🚀 使用方式:")
    print("1. 基本測試:")
    print("   python diagnostic_batch_crawler.py")
    
    print("\n2. 檢查結果:")
    print("   - 查看 diagnostic_report_*.json 了解爬取統計")
    print("   - 查看 financial_search_index_*.json 瀏覽所有財報")
    print("   - 查看各公司目錄下的個別JSON檔案")
    
    print("\n3. 啟用完整PDF解析:")
    print("   pip install PyPDF2")
    print("   python setup_pdf_parsing.py")
    
    print("\n📊 JSON檔案格式:")
    json_example = {
        "stock_code": "2330",
        "company_name": "台積電",
        "report_year": 2024,
        "report_season": "Q1",
        "currency": "TWD",
        "unit": "千元",
        "financials": {
            "cash_and_equivalents": "現金及約當現金",
            "accounts_receivable": "應收帳款",
            "inventory": "存貨",
            "total_assets": "資產總額",
            "total_liabilities": "負債總額",
            "equity": "權益總額"
        },
        "income_statement": {
            "net_revenue": "營業收入",
            "gross_profit": "毛利",
            "operating_income": "營業利益",
            "net_income": "本期淨利",
            "eps": "每股盈餘"
        },
        "metadata": {
            "source": "doc.twse.com.tw",
            "file_name": "202401_2330_AI1.pdf",
            "crawled_at": "2025-06-27T00:25:08",
            "parser_version": "v2.3"
        }
    }
    
    import json
    print(json.dumps(json_example, ensure_ascii=False, indent=2))
    
    print("\n🔍 搜尋索引功能:")
    print("- 所有公司財報資料整合在一個JSON檔案中")
    print("- 可快速查詢特定公司的所有期間資料")
    print("- 支援程式化批次分析和比較")
    
    print("\n✅ 當前狀態:")
    from pathlib import Path
    
    results_dir = Path("data/diagnostic_results")
    if results_dir.exists():
        pdf_count = len(list(results_dir.rglob("*.pdf")))
        json_count = len(list(results_dir.rglob("*.json")))
        
        print(f"   已下載PDF檔案: {pdf_count} 個")
        print(f"   已生成JSON檔案: {json_count} 個")
        
        companies = [d.name for d in results_dir.iterdir() if d.is_dir()]
        print(f"   涵蓋公司: {', '.join(companies)}")
    else:
        print("   尚未有下載結果")
    
    print("\n🔧 故障排除:")
    print("1. 如果爬取失敗:")
    print("   - 檢查網路連接")
    print("   - 查看 diagnostic_report_*.json 中的錯誤訊息")
    print("   - 嘗試減少並發請求數量")
    
    print("\n2. 如果JSON資料為null:")
    print("   - 安裝PyPDF2: pip install PyPDF2")
    print("   - 運行 setup_pdf_parsing.py")
    print("   - 檢查PDF檔案是否完整下載")
    
    print("\n3. 如果搜尋索引為空:")
    print("   - 確認已成功解析PDF內容")
    print("   - 檢查parsed_reports統計數據")
    
    print("\n📞 技術支援:")
    print("- 查看日誌輸出了解詳細錯誤")
    print("- 檢查debug_responses/目錄中的網站回應")
    print("- 確認目標公司代號和期間是否正確")

def check_system_status():
    """檢查系統狀態"""
    from pathlib import Path
    import json
    
    print("\n🔍 系統狀態檢查:")
    print("-" * 30)
    
    # 檢查結果目錄
    results_dir = Path("data/diagnostic_results")
    if results_dir.exists():
        print("✅ 結果目錄存在")
        
        # 檢查PDF檔案
        pdf_files = list(results_dir.rglob("*.pdf"))
        print(f"✅ PDF檔案: {len(pdf_files)} 個")
        
        # 檢查JSON檔案
        json_files = list(results_dir.rglob("*.json"))
        print(f"✅ JSON檔案: {len(json_files)} 個")
        
        # 檢查搜尋索引
        search_files = list(results_dir.glob("financial_search_index_*.json"))
        if search_files:
            latest_search = max(search_files, key=lambda x: x.stat().st_mtime)
            print(f"✅ 搜尋索引: {latest_search.name}")
            
            # 讀取搜尋索引內容
            try:
                with open(latest_search, 'r', encoding='utf-8') as f:
                    search_data = json.load(f)
                
                print(f"   📊 包含公司數: {search_data['index_info']['total_companies']}")
                print(f"   📊 總財報數: {search_data['index_info']['total_reports']}")
                
            except Exception as e:
                print(f"   ⚠️ 讀取搜尋索引失敗: {e}")
        else:
            print("⚠️ 未找到搜尋索引檔案")
        
        # 檢查診斷報告
        report_files = list(results_dir.glob("diagnostic_report_*.json"))
        if report_files:
            latest_report = max(report_files, key=lambda x: x.stat().st_mtime)
            print(f"✅ 診斷報告: {latest_report.name}")
            
            try:
                with open(latest_report, 'r', encoding='utf-8') as f:
                    report_data = json.load(f)
                
                stats = report_data['statistics']
                print(f"   📊 嘗試次數: {stats['total_attempts']}")
                print(f"   📊 成功下載: {stats['successful_downloads']}")
                print(f"   📊 失敗次數: {stats['failed_downloads']}")
                
            except Exception as e:
                print(f"   ⚠️ 讀取診斷報告失敗: {e}")
        else:
            print("⚠️ 未找到診斷報告")
            
    else:
        print("❌ 結果目錄不存在，請先運行爬蟲")
    
    # 檢查PyPDF2
    try:
        import PyPDF2
        print("✅ PyPDF2已安裝 - 支援完整PDF解析")
    except ImportError:
        print("⚠️ PyPDF2未安裝 - 僅支援基本檔案資訊")

if __name__ == '__main__':
    show_usage_guide()
    check_system_status()

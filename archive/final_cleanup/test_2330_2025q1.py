#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試專用：抓取台積電2330 2025Q1財報
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# 添加crawlers目錄到Python路徑
sys.path.insert(0, str(Path(__file__).parent / 'crawlers'))

from improved_twse_crawler import ImprovedTWSEFinancialCrawler

def test_tsmc_2025q1():
    """測試抓取台積電2025Q1財報"""
    
    print("🚀 測試抓取台積電(2330) 2025Q1財報")
    print("=" * 50)
    
    # 設定輸出目錄
    output_dir = Path(__file__).parent / 'data' / 'test_results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化爬蟲
    print("📥 初始化爬蟲...")
    crawler = ImprovedTWSEFinancialCrawler(max_retries=3, retry_delay=2)
    
    # 測試參數
    stock_code = "2330"
    company_name = "台積電"
    year = 2025
    quarter = 1
    
    print(f"📋 目標：{company_name}({stock_code}) {year}Q{quarter}")
    print("-" * 30)
    
    try:
        # 執行查詢
        print("🔍 開始查詢財報...")
        result = crawler.query_financial_reports(
            stock_code=stock_code,
            year=year,
            quarter=quarter,
            report_type='ifrs_consolidated'
        )
        
        print(f"📊 查詢結果：")
        if result and result.get('status') == 'success':
            pdf_files = result.get('pdf_files', [])
            print(f"   ✅ 找到 {len(pdf_files)} 個財報")
            
            # 下載每個PDF
            for i, pdf_info in enumerate(pdf_files, 1):
                filename = pdf_info.get('filename', f"unknown_{i}.pdf")
                print(f"   📄 [{i}] 準備下載: {filename}")
                
                # 建立檔案路徑
                file_path = output_dir / filename
                
                # 構建PDF下載連結
                pdf_link_info = {
                    'kind': pdf_info.get('kind', 'A'),
                    'co_id': pdf_info.get('co_id', stock_code),
                    'filename': filename,
                    'href': f"/server-java/t57sb01?TYPEK={pdf_info.get('kind', 'A')}&co_id={pdf_info.get('co_id', stock_code)}&filename={filename}"
                }
                
                # 下載PDF
                print(f"       🔗 準備下載...")
                download_success = crawler.download_pdf_file(pdf_link_info, str(file_path))
                
                if download_success and file_path.exists():
                    actual_size = file_path.stat().st_size
                    print(f"       ✅ 檔案下載成功，大小: {actual_size:,} bytes")
                    
                    # 生成對應的JSON檔案
                    json_path = file_path.with_suffix('.json')
                    json_data = {
                        "stock_code": stock_code,
                        "company_name": company_name,
                        "report_year": year,
                        "report_season": f"Q{quarter}",
                        "currency": "TWD",
                        "unit": "千元",
                        "financials": {
                            "cash_and_equivalents": None,
                            "accounts_receivable": None,
                            "inventory": None,
                            "total_assets": None,
                            "total_liabilities": None,
                            "equity": None
                        },
                        "income_statement": {
                            "net_revenue": None,
                            "gross_profit": None,
                            "operating_income": None,
                            "net_income": None,
                            "eps": None
                        },
                        "metadata": {
                            "source": "doc.twse.com.tw",
                            "file_name": filename,
                            "file_path": str(file_path),
                            "file_size": actual_size,
                            "crawled_at": datetime.now().isoformat(),
                            "parser_version": "v3.1_test",
                            "note": "測試模式：基本結構，可擴展PDF內容解析"
                        }
                    }
                    
                    # 儲存JSON檔案
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"       ✅ JSON已生成: {json_path.name}")
                else:
                    print(f"       ❌ 檔案下載失敗")
                    
            return True
        else:
            status = result.get('status', 'unknown') if result else 'no_result'
            message = result.get('message', '未知錯誤') if result else '無回應'
            
            print(f"   ❌ 查詢失敗: {status}")
            print(f"   📝 詳細訊息: {message}")
            print("   💡 可能原因：")
            
            if status == 'no_data':
                print("      - 2025Q1財報尚未公布")
            elif status == 'financial_holding':
                print("      - 台積電被誤認為金融控股公司")
            elif status == 'server_error':
                print("      - TWSE伺服器錯誤")
            else:
                print("      - 網站查詢條件需要調整")
                print("      - 網路連線問題")
            
            return False
            
    except Exception as e:
        print(f"❌ 測試過程發生錯誤: {e}")
        print(f"   錯誤類型: {type(e).__name__}")
        import traceback
        print(f"   詳細錯誤: {traceback.format_exc()}")
        return False

def check_existing_data():
    """檢查現有的台積電數據"""
    print("\n🔍 檢查現有台積電數據...")
    print("-" * 30)
    
    # 檢查主要數據目錄
    main_data_dir = Path(__file__).parent / 'data' / 'financial_reports_main' / 'by_company' / '2330_台積電'
    
    if main_data_dir.exists():
        periods = [d.name for d in main_data_dir.iterdir() if d.is_dir()]
        periods.sort()
        
        print(f"📁 現有期間: {len(periods)} 個")
        for period in periods:
            period_dir = main_data_dir / period
            pdf_files = list(period_dir.glob("*.pdf"))
            json_files = list(period_dir.glob("*.json"))
            
            print(f"   📅 {period}: PDF={len(pdf_files)}, JSON={len(json_files)}")
    else:
        print("❌ 未找到台積電數據目錄")
    
    # 檢查搜尋索引
    index_dir = Path(__file__).parent / 'data' / 'financial_reports_main' / 'search_indexes'
    if index_dir.exists():
        index_files = list(index_dir.glob("financial_index_*.json"))
        if index_files:
            latest_index = max(index_files, key=lambda x: x.stat().st_mtime)
            print(f"\n📊 最新搜尋索引: {latest_index.name}")
            
            try:
                with open(latest_index, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                if '2330' in index_data.get('companies', {}):
                    tsmc_data = index_data['companies']['2330']
                    periods = list(tsmc_data['periods'].keys())
                    print(f"   🏢 台積電索引期間: {len(periods)} 個")
                    print(f"   📅 期間列表: {', '.join(sorted(periods))}")
                else:
                    print("   ❌ 索引中未找到台積電數據")
                    
            except Exception as e:
                print(f"   ❌ 讀取索引失敗: {e}")

def main():
    """主程式"""
    print("🧪 台積電2330 2025Q1財報抓取測試")
    print("=" * 60)
    
    # 檢查現有數據
    check_existing_data()
    
    # 執行測試
    print(f"\n⏰ 開始時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = test_tsmc_2025q1()
    
    print(f"\n⏰ 結束時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if success:
        print("✅ 測試完成！")
        
        # 檢查測試結果
        test_dir = Path(__file__).parent / 'data' / 'test_results'
        if test_dir.exists():
            pdf_files = list(test_dir.glob("*.pdf"))
            json_files = list(test_dir.glob("*.json"))
            
            print(f"\n📊 測試結果統計:")
            print(f"   📄 PDF檔案: {len(pdf_files)} 個")
            print(f"   🔧 JSON檔案: {len(json_files)} 個")
            
            if pdf_files:
                print(f"\n📁 檔案位置: {test_dir}")
                for pdf_file in pdf_files:
                    size = pdf_file.stat().st_size
                    print(f"   📄 {pdf_file.name} ({size:,} bytes)")
    else:
        print("❌ 測試失敗")
        print("\n💡 建議：")
        print("   1. 檢查網路連線")
        print("   2. 確認2025Q1財報是否已公布")
        print("   3. 嘗試其他期間（如2024Q4）")
        print("   4. 查看詳細錯誤訊息")

if __name__ == '__main__':
    main()

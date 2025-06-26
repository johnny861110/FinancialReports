#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
簡化的批次爬蟲診斷腳本
"""

import sys
import json
import time
import re
# import PyPDF2  # 暫時註解，使用替代方案
from pathlib import Path
from datetime import datetime

# 添加crawlers目錄到Python路徑
sys.path.insert(0, str(Path(__file__).parent / 'crawlers'))

from improved_twse_crawler import ImprovedTWSEFinancialCrawler

# === 財報解析功能 ===

def extract_text_from_pdf(pdf_path):
    """從PDF檔案提取文字內容（簡化版本）"""
    try:
        # 由於PyPDF2可能不可用，暫時返回檔名信息
        # 實際使用時可以安裝: pip install PyPDF2
        return f"PDF檔案: {pdf_path.name} (需要安裝PyPDF2進行文字提取)"
    except Exception as e:
        print(f"❌ PDF讀取失敗: {e}")
        return ""

def extract_eps(text):
    """提取每股盈餘"""
    match = re.search(r"每股.*?盈餘.*?([\d\.]+)", text)
    if match:
        return float(match.group(1))
    return None

def extract_numbers_by_line(text, *keywords, min_value=1000000):
    """根據關鍵字從行首提取數字"""
    for line in text.splitlines():
        line_strip = line.strip()
        for keyword in keywords:
            # 只抓行首開頭的關鍵字
            if keyword and re.match(rf"^{re.escape(keyword)}", line_strip):
                matches = re.findall(r"[\d,]+", line_strip)
                nums = [int(m.replace(",", "")) for m in matches if len(m.replace(",", "")) > 3]
                nums = [n for n in nums if n >= min_value]
                if nums:
                    return [max(nums)]
    return None

def pick_first(nums):
    """選取第一個數字"""
    return nums[0] if nums and len(nums) > 0 else None

def calc_gross_profit(text):
    """計算毛利"""
    gross = extract_numbers_by_line(text, "毛利", "毛利總額", "營業毛利", "營業毛利總額")
    if gross:
        return pick_first(gross)
    revenue = extract_numbers_by_line(text, "營業收入", "收入合計")
    cost = extract_numbers_by_line(text, "營業成本")
    if revenue and cost:
        return pick_first(revenue) - pick_first(cost)
    return None

def calc_operating_income(text):
    """計算營業利益"""
    op = extract_numbers_by_line(text, "營業利益", "營業利益總額", "營業淨利", "營業收入淨額")
    if op:
        return pick_first(op)
    revenue = extract_numbers_by_line(text, "營業收入", "收入合計")
    cost = extract_numbers_by_line(text, "營業成本")
    expense = extract_numbers_by_line(text, "營業費用", "營業支出")
    if revenue and cost and expense:
        return pick_first(revenue) - pick_first(cost) - pick_first(expense)
    return None

def extract_net_income(text):
    """提取淨利"""
    ni = extract_numbers_by_line(text, "歸屬予母公司業主之本期淨利")
    if ni:
        return pick_first(ni)
    return pick_first(
        extract_numbers_by_line(text, "本期淨利", "稅後淨利", "稅後純益", "本期純益")
    )

def parse_financial_report(pdf_path, stock_code, company_name, year, quarter):
    """解析財報PDF並生成標準化JSON（簡化版本）"""
    text = extract_text_from_pdf(pdf_path)
    
    # 由於暫時無法提取PDF內容，創建基本結構
    result = {
        "stock_code": stock_code,
        "company_name": company_name,
        "report_year": year,
        "report_season": f"Q{quarter}",
        "currency": "TWD",
        "unit": "千元",
        "financials": {
            "cash_and_equivalents": None,  # 需要PDF解析
            "accounts_receivable": None,
            "inventory": None,
            "total_assets": None,
            "total_liabilities": None,
            "equity": None
        },
        "income_statement": {
            "net_revenue": None,  # 需要PDF解析
            "gross_profit": None,
            "operating_income": None,
            "net_income": None,
            "eps": None
        },
        "metadata": {
            "source": "doc.twse.com.tw",
            "file_name": pdf_path.name,
            "file_path": str(pdf_path),
            "file_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
            "crawled_at": datetime.now().isoformat(),
            "parser_version": "v2.3_basic",
            "note": "需要安裝PyPDF2進行完整財報數據解析"
        }
    }
    
    # 如果能夠解析PDF內容，則進行數據提取
    if text and "PDF檔案:" not in text:
        eps = extract_eps(text)
        
        # 更新財務數據
        result["financials"].update({
            "cash_and_equivalents": pick_first(
                extract_numbers_by_line(text, "現金及約當現金", "現金及銀行存款")
            ),
            "accounts_receivable": pick_first(
                extract_numbers_by_line(text, "應收帳款", "應收帳款－淨額", "應收票據及帳款")
            ),
            "inventory": pick_first(
                extract_numbers_by_line(text, "存貨", "存貨－淨額", "存  貨")
            ),
            "total_assets": pick_first(
                extract_numbers_by_line(text, "資產總額", "資產合計", "資產總計")
            ),
            "total_liabilities": pick_first(
                extract_numbers_by_line(text, "負債總額", "負債合計", "負債總計")
            ),
            "equity": pick_first(
                extract_numbers_by_line(text, "權益總額", "權益合計", "權益總計")
            )
        })
        
        result["income_statement"].update({
            "net_revenue": pick_first(
                extract_numbers_by_line(text, "營業收入", "收入合計")
            ),
            "gross_profit": calc_gross_profit(text),
            "operating_income": calc_operating_income(text),
            "net_income": extract_net_income(text),
            "eps": eps
        })
        
        result["metadata"]["parser_version"] = "v2.3_full"
        result["metadata"]["note"] = "完整財報數據解析"
    
    return result

def create_search_index(parsed_reports):
    """創建搜尋索引JSON檔案"""
    
    # 按公司和期間組織資料
    companies = {}
    
    for report in parsed_reports:
        stock_code = report['stock_code']
        company_name = report['company_name']
        period = f"{report['report_year']}Q{report['report_season'][-1]}"
        
        if stock_code not in companies:
            companies[stock_code] = {
                'stock_code': stock_code,
                'company_name': company_name,
                'periods': {}
            }
        
        companies[stock_code]['periods'][period] = {
            'report_year': report['report_year'],
            'report_season': report['report_season'],
            'financials': report['financials'],
            'income_statement': report['income_statement'],
            'metadata': report['metadata']
        }
    
    # 創建搜尋索引結構
    search_index = {
        'index_info': {
            'created_at': datetime.now().isoformat(),
            'total_companies': len(companies),
            'total_reports': len(parsed_reports),
            'data_source': 'TWSE',
            'index_version': '1.0'
        },
        'companies': companies,
        'summary': {
            'companies_list': [
                {
                    'stock_code': code,
                    'company_name': data['company_name'],
                    'periods_count': len(data['periods']),
                    'available_periods': list(data['periods'].keys())
                }
                for code, data in companies.items()
            ]
        }
    }
    
    return search_index

# === 原有的爬蟲功能 ===

def run_diagnostic_batch():
    """運行診斷批次爬取"""
    
    print("🚀 開始診斷批次爬取...")
    
    # ETF 0050部分成分股（簡化測試）
    test_stocks = {
        '2330': '台積電',
        '2454': '聯發科', 
        '2317': '鴻海'
    }
    
    # 測試期間
    test_periods = [
        (2024, 1),
        (2024, 2)
    ]
    
    # 統計數據
    stats = {
        'total_attempts': 0,
        'successful_downloads': 0,
        'failed_downloads': 0,
        'errors': [],
        'parsed_reports': []  # 新增：儲存解析後的財報資料
    }
    
    # 創建爬蟲
    crawler = ImprovedTWSEFinancialCrawler(max_retries=2, retry_delay=2)
    
    if not crawler.get_initial_page():
        print("❌ 無法初始化爬蟲")
        return
    
    print("✅ 爬蟲初始化成功")
    
    # 設置輸出目錄
    base_dir = Path.cwd() / 'data' / 'diagnostic_results'
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # 開始批次處理
    total_tasks = len(test_stocks) * len(test_periods)
    current_task = 0
    
    print(f"📊 總任務數: {total_tasks}")
    print()
    
    for stock_code, company_name in test_stocks.items():
        for year, quarter in test_periods:
            current_task += 1
            
            print(f"📋 [{current_task}/{total_tasks}] 處理 {stock_code} ({company_name}) {year}Q{quarter}...")
            
            try:
                # 查詢財報
                result = crawler.query_financial_reports(stock_code, year, quarter)
                stats['total_attempts'] += 1
                
                if result and result.get('status') == 'success' and result.get('pdf_files'):
                    print(f"   ✅ 查詢成功，找到 {len(result['pdf_files'])} 個PDF")
                    stats['successful_downloads'] += 1
                    
                    # 嘗試下載第一個PDF（測試用）
                    pdf_info = result['pdf_files'][0]
                    save_dir = base_dir / stock_code / f"{year}Q{quarter}"
                    save_path = save_dir / pdf_info['filename']
                    
                    if crawler.download_pdf_file(pdf_info, save_path):
                        print(f"   ✅ PDF下載成功: {pdf_info['filename']}")
                        
                        # 新增：解析PDF內容並生成JSON
                        try:
                            parsed_data = parse_financial_report(save_path, stock_code, company_name, year, quarter)
                            if parsed_data:
                                # 儲存單獨的JSON檔案
                                json_path = save_path.with_suffix('.json')
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(parsed_data, f, ensure_ascii=False, indent=2)
                                
                                stats['parsed_reports'].append(parsed_data)
                                print(f"   ✅ 財報解析成功: {json_path.name}")
                            else:
                                print(f"   ⚠️ 財報解析失敗: 無法提取內容")
                                stats['errors'].append(f"解析失敗: {pdf_info['filename']}")
                        except Exception as parse_e:
                            print(f"   ❌ 財報解析異常: {parse_e}")
                            stats['errors'].append(f"解析異常: {pdf_info['filename']} - {parse_e}")
                    else:
                        print(f"   ❌ PDF下載失敗: {pdf_info['filename']}")
                        stats['errors'].append(f"PDF下載失敗: {pdf_info['filename']}")
                
                elif result and result.get('status') in ['financial_holding', 'no_data']:
                    print(f"   ⚠️ 查詢狀態: {result['status']} - {result.get('message', '')}")
                    stats['errors'].append(f"查詢狀態: {result['status']}")
                else:
                    print(f"   ❌ 查詢失敗或狀態異常: {result.get('status') if result else 'None'}")
                    stats['failed_downloads'] += 1
                    stats['errors'].append(f"查詢失敗: {stock_code} {year}Q{quarter}")
                
            except Exception as e:
                print(f"   ❌ 處理異常: {e}")
                stats['failed_downloads'] += 1
                stats['errors'].append(f"處理異常: {stock_code} {year}Q{quarter} - {e}")
            
            # 延遲避免頻繁請求
            time.sleep(2.0)
            print()
    
    # 顯示總結
    success_rate = (stats['successful_downloads'] / stats['total_attempts'] * 100) if stats['total_attempts'] > 0 else 0
    
    print(f"🎉 診斷批次爬取完成!")
    print(f"📊 統計結果:")
    print(f"   總嘗試次數: {stats['total_attempts']}")
    print(f"   成功查詢: {stats['successful_downloads']}")
    print(f"   失敗查詢: {stats['failed_downloads']}")
    print(f"   解析成功: {len(stats['parsed_reports'])}")
    print(f"   成功率: {success_rate:.1f}%")
    
    # 生成搜尋檔案JSON
    if stats['parsed_reports']:
        search_index = create_search_index(stats['parsed_reports'])
        search_file = base_dir / f"financial_search_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(search_file, 'w', encoding='utf-8') as f:
            json.dump(search_index, f, ensure_ascii=False, indent=2)
        
        print(f"\n📋 搜尋檔案已生成: {search_file}")
        print(f"   包含 {len(search_index['companies'])} 家公司的財報資料")
    
    if stats['errors']:
        print(f"\n❌ 錯誤列表 ({len(stats['errors'])}個):")
        for i, error in enumerate(stats['errors'][:10], 1):  # 顯示前10個錯誤
            print(f"   {i}. {error}")
        
        if len(stats['errors']) > 10:
            print(f"   ... 還有 {len(stats['errors']) - 10} 個錯誤")
    
    # 儲存診斷報告
    report = {
        'timestamp': datetime.now().isoformat(),
        'statistics': stats,
        'test_stocks': test_stocks,
        'test_periods': test_periods
    }
    
    report_file = base_dir / f"diagnostic_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 診斷報告已儲存: {report_file}")

if __name__ == '__main__':
    run_diagnostic_batch()

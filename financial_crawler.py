#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
財報爬蟲統一介面
支援JSON輸入的單筆和批次查詢
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import argparse

# 添加scripts路徑以便導入模組
sys.path.append(str(Path(__file__).parent / "scripts"))

def load_config(config_path=None):
    """載入配置檔案"""
    if config_path is None:
        config_path = Path(__file__).parent / "config" / "crawler_config.json"
    
    default_config = {
        "output_dir": "data/financial_reports",
        "test_output_dir": "data/test_results",
        "download_delay": 2,
        "max_retry": 3,
        "timeout": 30,
        "auto_validation": True,
        "generate_json": True
    }
    
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            # 合併預設配置
            default_config.update(config)
    
    return default_config

def download_company_report(stock_code, company_name, year, season, output_dir="data/financial_reports"):
    """
    通用財報下載函數
    基於 improved_2330_test.py 的邏輯改寫為通用版本
    """
    import requests
    import re
    from urllib.parse import urljoin
    
    print(f"下載 {company_name}({stock_code}) {year}Q{season} 財報")
    
    # 設定輸出目錄
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"輸出目錄: {output_path}")
    
    # 建構PDF檔案名稱 (格式: YYYYMM_STOCKCODE_AI1.pdf)
    # 季度對應月份: Q1=01, Q2=02, Q3=03, Q4=04
    month_map = {'1': '01', '2': '02', '3': '03', '4': '04'}
    season_str = str(season)
    
    pdf_year = year
    pdf_month = month_map[season_str]
    
    # 使用完整年份
    filename = f"{pdf_year}{pdf_month}_{stock_code}_AI1.pdf"
    
    print(f"目標檔案: {filename}")
    print(f"PDF年份: {pdf_year}, 月份: {pdf_month}")
    
    # TWSE網站參數
    base_url = "https://doc.twse.com.tw"
    query_url = f"{base_url}/server-java/t57sb01"
    
    query_data = {
        'step': '9',
        'kind': 'A',
        'co_id': stock_code,
        'filename': filename
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': f'{base_url}/server-java/t57sb01'
    }
    
    print(f"查詢 URL: {query_url}")
    print(f"查詢參數: {query_data}")
    
    try:
        session = requests.Session()
        
        # 步驟1：查詢
        print("執行查詢...")
        response = session.post(query_url, data=query_data, headers=headers, timeout=30)
        
        print(f"回應狀態碼: {response.status_code}")
        
        if response.status_code != 200:
            print(f"查詢失敗，HTTP狀態碼: {response.status_code}")
            return False
        
        # 解析PDF連結
        content = response.text
        print(f"回應內容長度: {len(content)} 字符")
        
        # 保存查詢回應以供調試
        debug_dir = output_path / "debug"
        debug_dir.mkdir(exist_ok=True)
        debug_file = debug_dir / f"query_response_{stock_code}_{year}Q{season}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"查詢回應已保存: {debug_file}")
        
        pdf_link_pattern = r"href='(/pdf/[^']+)'"
        match = re.search(pdf_link_pattern, content)
        
        if not match:
            print("未找到PDF連結，可能該期間無財報資料")
            print("嘗試尋找其他可能的連結格式...")
            
            # 嘗試其他可能的連結格式
            alternative_patterns = [
                r"href=['\"]?(/pdf/[^'\">\s]+)",
                r"location\.href\s*=\s*['\"]?(/pdf/[^'\">\s]+)",
                r"window\.open\(['\"]?(/pdf/[^'\">\s]+)"
            ]
            
            for pattern in alternative_patterns:
                alt_match = re.search(pattern, content)
                if alt_match:
                    print(f"找到替代連結格式: {alt_match.group(1)}")
                    match = alt_match
                    break
            
            if not match:
                return False
        
        pdf_path = match.group(1)
        pdf_url = urljoin(base_url, pdf_path)
        print(f"找到PDF連結: {pdf_path}")
        print(f"完整PDF URL: {pdf_url}")
        
        # 步驟2：下載PDF
        print("下載PDF...")
        pdf_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
            'Referer': query_url
        }
        
        pdf_response = session.get(pdf_url, headers=pdf_headers, stream=True, timeout=60)
        
        print(f"PDF回應狀態碼: {pdf_response.status_code}")
        
        if pdf_response.status_code != 200:
            print(f"PDF下載失敗，HTTP狀態碼: {pdf_response.status_code}")
            return False
        
        # 檢查內容類型
        content_type = pdf_response.headers.get('Content-Type', '')
        print(f"內容類型: {content_type}")
        
        if 'pdf' not in content_type.lower() and 'application/octet-stream' not in content_type:
            print(f"下載的不是PDF檔案: {content_type}")
            return False
        
        # 儲存PDF檔案
        file_path = output_path / filename
        downloaded_size = 0
        
        print(f"儲存到: {file_path}")
        
        with open(file_path, 'wb') as f:
            for chunk in pdf_response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded_size += len(chunk)
        
        actual_size = file_path.stat().st_size
        print(f"PDF下載完成！")
        print(f"檔案大小: {actual_size:,} bytes")
        
        # 檢查檔案完整性
        if actual_size < 10000:  # 檔案太小可能是錯誤頁面
            print("檔案大小異常，可能下載不完整")
            # 檢查是否為錯誤頁面
            with open(file_path, 'rb') as f:
                first_bytes = f.read(100)
                if b'<html' in first_bytes.lower() or b'<body' in first_bytes.lower():
                    print("下載的是HTML錯誤頁面，非PDF檔案")
                    return False
            return False
        
        # 生成JSON檔案
        json_path = file_path.with_suffix('.json')
        json_data = {
            "stock_code": stock_code,
            "company_name": company_name,
            "report_year": year,
            "report_season": f"Q{season}",
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
                "download_url": pdf_url,
                "crawled_at": datetime.now().isoformat(),
                "parser_version": "unified_crawler_v1.0",
                "validation": {
                    "file_exists": file_path.exists(),
                    "size_reasonable": actual_size > 10000
                }
            }
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"JSON檔案已生成: {json_path.name}")
        
        # 更新主索引
        add_to_master_index(stock_code, company_name, year, season, str(file_path), str(json_path), actual_size, success=True)
        
        return True
        
    except requests.exceptions.Timeout:
        print("下載超時")
        # 記錄失敗到主索引
        add_to_master_index(stock_code, company_name, year, season, None, None, 0, success=False)
        return False
    except Exception as e:
        print(f"下載過程發生錯誤: {e}")
        import traceback
        print(f"錯誤詳情: {traceback.format_exc()}")
        # 記錄失敗到主索引
        add_to_master_index(stock_code, company_name, year, season, None, None, 0, success=False)
        return False

def process_single_query(query_data, config):
    """處理單筆查詢"""
    print(f"處理單筆查詢: {query_data.get('company_name', query_data.get('stock_code'))}")
    
    try:
        result = download_company_report(
            stock_code=query_data['stock_code'],
            company_name=query_data['company_name'],
            year=int(query_data['year']),
            season=str(query_data['season']).replace('Q', ''),
            output_dir=config['test_output_dir'] if query_data.get('test_mode', False) else config['output_dir']
        )
        
        return {
            "status": "success" if result else "failed",
            "stock_code": query_data['stock_code'],
            "company_name": query_data['company_name'],
            "period": f"{query_data['year']}Q{str(query_data['season']).replace('Q', '')}",
            "timestamp": datetime.now().isoformat(),
            "details": "下載完成" if result else "下載失敗，請檢查期間是否正確或網路連線"
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"處理過程發生錯誤: {error_msg}")
        return {
            "status": "error",
            "error": error_msg,
            "stock_code": query_data['stock_code'],
            "company_name": query_data.get('company_name', '未知'),
            "period": f"{query_data.get('year', '未知')}Q{str(query_data.get('season', '未知')).replace('Q', '')}",
            "timestamp": datetime.now().isoformat()
        }


def process_batch_query(queries_data, config):
    """處理批次查詢"""
    print(f"處理批次查詢: {len(queries_data)} 個查詢")
    
    results = []
    for i, query in enumerate(queries_data, 1):
        print(f"\n[{i}/{len(queries_data)}] 處理: {query.get('company_name', query.get('stock_code'))}")
        result = process_single_query(query, config)
        results.append(result)
        
        # 添加延遲避免請求過快
        if i < len(queries_data):
            import time
            time.sleep(config.get('download_delay', 2))
    
    return results

def validate_query_data(data):
    """驗證查詢數據格式"""
    required_fields = ['stock_code', 'company_name', 'year', 'season']
    
    if isinstance(data, list):
        # 批次查詢
        for i, item in enumerate(data):
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                raise ValueError(f"查詢 {i+1} 缺少必要欄位: {missing_fields}")
    else:
        # 單筆查詢
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise ValueError(f"缺少必要欄位: {missing_fields}")
    
    return True

def save_results(results, output_file=None):
    """儲存查詢結果"""
    if output_file is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"query_results_{timestamp}.json"
    
    output_path = Path(__file__).parent / "output" / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"結果已儲存至: {output_path}")
    return output_path

def load_master_index():
    """載入主索引檔案"""
    index_file = Path(__file__).parent / "data" / "master_index.json"
    
    if index_file.exists():
        try:
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 主索引檔案讀取錯誤: {e}")
            return {"version": "1.0", "last_updated": "", "total_reports": 0, "reports": []}
    else:
        return {"version": "1.0", "last_updated": "", "total_reports": 0, "reports": []}

def save_master_index(index_data):
    """儲存主索引檔案"""
    index_file = Path(__file__).parent / "data" / "master_index.json"
    index_file.parent.mkdir(parents=True, exist_ok=True)
    
    # 更新統計資訊
    index_data["last_updated"] = datetime.now().isoformat()
    index_data["total_reports"] = len(index_data["reports"])
    
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        print(f"主索引已更新: {index_file}")
        return True
    except Exception as e:
        print(f"警告: 主索引儲存失敗: {e}")
        return False

def add_to_master_index(stock_code, company_name, year, season, pdf_path, json_path, file_size, success=True):
    """將新的財報記錄添加到主索引"""
    index_data = load_master_index()
    
    # 建立新記錄
    report_record = {
        "id": f"{stock_code}_{year}Q{season}",
        "stock_code": stock_code,
        "company_name": company_name,
        "year": year,
        "season": f"Q{season}",
        "period": f"{year}Q{season}",
        "pdf_file": str(pdf_path),
        "json_file": str(json_path),
        "file_size": file_size,
        "download_success": success,
        "crawled_at": datetime.now().isoformat(),
        "file_exists": Path(pdf_path).exists() if pdf_path else False
    }
    
    # 檢查是否已存在相同記錄
    existing_index = -1
    for i, report in enumerate(index_data["reports"]):
        if report["id"] == report_record["id"]:
            existing_index = i
            break
    
    if existing_index >= 0:
        # 更新現有記錄
        index_data["reports"][existing_index] = report_record
        print(f"更新主索引記錄: {report_record['id']}")
    else:
        # 新增記錄
        index_data["reports"].append(report_record)
        print(f"新增主索引記錄: {report_record['id']}")
    
    # 按日期排序 (最新的在前)
    index_data["reports"].sort(key=lambda x: x["crawled_at"], reverse=True)
    
    return save_master_index(index_data)

def search_master_index(keyword=None, stock_code=None, company_name=None, year=None, season=None):
    """搜尋主索引中的財報記錄"""
    index_data = load_master_index()
    results = []
    
    for report in index_data["reports"]:
        match = True
        
        # 關鍵字搜尋 (股票代碼或公司名稱)
        if keyword:
            if keyword.lower() not in report["stock_code"].lower() and \
               keyword.lower() not in report["company_name"].lower():
                match = False
        
        # 股票代碼精確匹配
        if stock_code and report["stock_code"] != stock_code:
            match = False
            
        # 公司名稱模糊匹配
        if company_name and company_name.lower() not in report["company_name"].lower():
            match = False
            
        # 年度匹配
        if year and report["year"] != int(year):
            match = False
            
        # 季度匹配
        if season and report["season"] != f"Q{season}":
            match = False
        
        if match:
            results.append(report)
    
    return results

def show_master_index_stats():
    """顯示主索引統計資訊"""
    index_data = load_master_index()
    
    print("📊 財報主索引統計")
    print("=" * 40)
    print(f"總報告數: {index_data['total_reports']}")
    print(f"最後更新: {index_data.get('last_updated', '未知')}")
    
    if index_data["reports"]:
        # 統計各公司報告數量
        company_stats = {}
        year_stats = {}
        
        for report in index_data["reports"]:
            company = report["company_name"]
            year = str(report["year"])
            
            company_stats[company] = company_stats.get(company, 0) + 1
            year_stats[year] = year_stats.get(year, 0) + 1
        
        print(f"\n📈 各公司報告數:")
        for company, count in sorted(company_stats.items()):
            print(f"   {company}: {count} 份")
            
        print(f"\n📅 各年度報告數:")
        for year, count in sorted(year_stats.items(), reverse=True):
            print(f"   {year}: {count} 份")
        
        # 最新下載的5筆記錄
        print(f"\n🕒 最新下載記錄:")
        for i, report in enumerate(index_data["reports"][:5]):
            status = "✅" if report["download_success"] else "❌"
            print(f"   {i+1}. {report['company_name']}({report['stock_code']}) {report['period']} {status}")
    
    return index_data

def main():
    """主程式"""
    parser = argparse.ArgumentParser(description='財報爬蟲統一介面')
    parser.add_argument('input', nargs='?', help='JSON輸入檔案路徑或JSON字串')
    parser.add_argument('--config', help='配置檔案路徑')
    parser.add_argument('--output', help='結果輸出檔案路徑')
    parser.add_argument('--validate-only', action='store_true', help='僅驗證輸入格式')
    parser.add_argument('--search', help='搜尋已下載的財報 (關鍵字)')
    parser.add_argument('--stock-code', help='搜尋指定股票代碼')
    parser.add_argument('--company', help='搜尋指定公司名稱')
    parser.add_argument('--year', help='搜尋指定年度')
    parser.add_argument('--season', help='搜尋指定季度')
    parser.add_argument('--stats', action='store_true', help='顯示主索引統計資訊')
    
    args = parser.parse_args()
    
    print("財報爬蟲統一介面")
    print("=" * 50)
    
    # 如果是搜尋模式
    if args.search or args.stock_code or args.company or args.year or args.season or args.stats:
        if args.stats:
            show_master_index_stats()
            return 0
        
        # 執行搜尋
        results = search_master_index(
            keyword=args.search,
            stock_code=args.stock_code,
            company_name=args.company,
            year=args.year,
            season=args.season
        )
        
        if results:
            print(f"🔍 搜尋結果: 找到 {len(results)} 筆記錄")
            print("-" * 50)
            
            for i, report in enumerate(results, 1):
                status = "✅" if report["download_success"] and report["file_exists"] else "❌"
                size_mb = report["file_size"] / (1024*1024) if report["file_size"] > 0 else 0
                
                print(f"{i}. {report['company_name']}({report['stock_code']}) {report['period']} {status}")
                print(f"   檔案: {report['pdf_file']}")
                print(f"   大小: {size_mb:.1f}MB")
                print(f"   時間: {report['crawled_at'][:19]}")
                print()
                
        else:
            print("🔍 搜尋結果: 未找到符合條件的記錄")
        
        return 0
    
    # 如果沒有提供輸入，顯示幫助
    if not args.input:
        parser.print_help()
        print("\n📊 快速查看統計: python financial_crawler.py --stats")
        print("🔍 搜尋範例: python financial_crawler.py --search 台積電")
        return 1
    
    # 載入配置
    config = load_config(args.config)
    print("配置已載入")
    
    # 解析輸入
    try:
        if Path(args.input).exists():
            # 從檔案讀取
            with open(args.input, 'r', encoding='utf-8') as f:
                input_data = json.load(f)
            print(f"從檔案載入: {args.input}")
        else:
            # 直接解析JSON字串
            input_data = json.loads(args.input)
            print(f"直接解析JSON字串")
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"輸入解析錯誤: {e}")
        return 1
    
    # 驗證輸入格式
    try:
        validate_query_data(input_data)
        print("輸input格式驗證通過")
        
        if args.validate_only:
            print("僅驗證模式，結束")
            return 0
            
    except ValueError as e:
        print(f"輸入格式錯誤: {e}")
        return 1
    
    # 處理查詢
    start_time = datetime.now()
    
    if isinstance(input_data, list):
        # 批次查詢
        results = process_batch_query(input_data, config)
        query_type = "批次"
        query_count = len(input_data)
    else:
        # 單筆查詢
        result = process_single_query(input_data, config)
        results = [result]
        query_type = "單筆"
        query_count = 1
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # 統計結果
    success_count = sum(1 for r in results if r.get('status') == 'success')
    failed_count = query_count - success_count
    
    print(f"\n執行結果:")
    print(f"   查詢類型: {query_type}")
    print(f"   總查詢數: {query_count}")
    print(f"   成功: {success_count}")
    print(f"   失敗: {failed_count}")
    print(f"   耗時: {duration:.1f} 秒")
    
    # 儲存結果
    output_path = save_results(results, args.output)
    
    print(f"\n查詢完成！")
    print(f"詳細結果請查看: {output_path}")
    
    return 0 if failed_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())

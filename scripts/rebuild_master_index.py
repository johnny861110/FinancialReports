#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
重建主索引腳本
掃描現有的財報檔案並重建主索引
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import re

# 添加父目錄到路徑
sys.path.append(str(Path(__file__).parent.parent))

def parse_filename(filename):
    """解析檔案名稱，提取股票代碼、年份、季度等資訊"""
    # 檔名格式: YYYYMM_STOCKCODE_AI1.pdf
    # 例如: 202401_2330_AI1.pdf
    pattern = r'(\d{4})(\d{2})_(\d+)_AI1\.(pdf|json)'
    match = re.match(pattern, filename)
    
    if not match:
        return None
    
    year_str, month_str, stock_code, file_type = match.groups()
    year = int(year_str)
    month = int(month_str)
    
    # 月份對應季度
    season_map = {'01': '1', '02': '2', '03': '3', '04': '4'}
    season = season_map.get(month_str, '1')
    
    return {
        'year': year,
        'season': season,
        'stock_code': stock_code,
        'file_type': file_type
    }

def get_company_name_from_json(json_path):
    """從JSON檔案中讀取公司名稱"""
    try:
        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('company_name', '未知公司')
    except Exception as e:
        print(f"警告: 無法讀取 JSON 檔案 {json_path}: {e}")
    
    return '未知公司'

def scan_financial_reports():
    """掃描財報目錄，收集所有PDF檔案資訊"""
    reports_dir = Path(__file__).parent.parent / "data" / "financial_reports"
    
    if not reports_dir.exists():
        print(f"財報目錄不存在: {reports_dir}")
        return []
    
    reports = []
    print(f"掃描目錄: {reports_dir}")
    
    # 掃描PDF檔案
    for pdf_file in reports_dir.glob("*.pdf"):
        print(f"處理檔案: {pdf_file.name}")
        
        # 解析檔案名稱
        info = parse_filename(pdf_file.name)
        if not info:
            print(f"  跳過無法解析的檔案: {pdf_file.name}")
            continue
        
        # 尋找對應的JSON檔案
        json_file = pdf_file.with_suffix('.json')
        
        # 取得公司名稱
        company_name = get_company_name_from_json(json_file)
        
        # 取得檔案大小
        file_size = pdf_file.stat().st_size if pdf_file.exists() else 0
        
        # 取得檔案修改時間作為爬取時間
        crawled_at = datetime.fromtimestamp(pdf_file.stat().st_mtime).isoformat()
        
        report_record = {
            "id": f"{info['stock_code']}_{info['year']}Q{info['season']}",
            "stock_code": info['stock_code'],
            "company_name": company_name,
            "year": info['year'],
            "season": f"Q{info['season']}",
            "period": f"{info['year']}Q{info['season']}",
            "pdf_file": str(pdf_file),
            "json_file": str(json_file) if json_file.exists() else None,
            "file_size": file_size,
            "download_success": True,
            "crawled_at": crawled_at,
            "file_exists": pdf_file.exists()
        }
        
        reports.append(report_record)
        print(f"  ✅ 加入: {company_name}({info['stock_code']}) {info['year']}Q{info['season']}")
    
    return reports

def rebuild_master_index():
    """重建主索引檔案"""
    print("開始重建主索引檔案...")
    print("=" * 50)
    
    # 掃描現有財報
    reports = scan_financial_reports()
    
    if not reports:
        print("未找到任何財報檔案")
        return False
    
    # 按爬取時間排序 (最新的在前)
    reports.sort(key=lambda x: x["crawled_at"], reverse=True)
    
    # 建立主索引數據結構
    index_data = {
        "version": "1.0",
        "last_updated": datetime.now().isoformat(),
        "total_reports": len(reports),
        "reports": reports
    }
    
    # 儲存主索引檔案
    index_file = Path(__file__).parent.parent / "data" / "master_index.json"
    index_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 主索引重建完成!")
        print(f"   檔案位置: {index_file}")
        print(f"   總記錄數: {len(reports)}")
        print(f"   更新時間: {index_data['last_updated']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 主索引儲存失敗: {e}")
        return False

def main():
    """主程式"""
    print("主索引重建工具")
    print("=" * 50)
    
    success = rebuild_master_index()
    
    if success:
        print("\n🎉 重建完成！您現在可以使用搜尋功能：")
        print("   python financial_crawler.py --stats")
        print("   python financial_crawler.py --search 台積電")
        print("   python financial_crawler.py --stock-code 2330")
        return 0
    else:
        print("\n❌ 重建失敗")
        return 1

if __name__ == '__main__':
    sys.exit(main())

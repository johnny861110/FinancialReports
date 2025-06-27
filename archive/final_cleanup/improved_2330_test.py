#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
改進版：測試下載台積電2330 2025Q1財報
處理需要先查詢再下載的情況
"""

import sys
import json
import requests
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

def download_tsmc_2025q1():
    """下載台積電2025Q1財報"""
    
    print("🚀 台積電(2330) 2025Q1財報下載測試 (改進版)")
    print("=" * 60)
    
    # 設定輸出目錄
    output_dir = Path(__file__).parent / 'data' / 'test_results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # PDF資訊
    pdf_info = {
        'filename': '202501_2330_AI1.pdf',
        'size': 5715493,
        'upload_date': '114/05/15 13:40:15'
    }
    
    # 步驟1：先執行查詢以建立session
    base_url = "https://doc.twse.com.tw"
    query_url = f"{base_url}/server-java/t57sb01"
    
    # 查詢表單數據
    query_data = {
        'step': '9',
        'kind': 'A',
        'co_id': '2330',
        'filename': pdf_info['filename']
    }
    
    # 設置headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': f'{base_url}/server-java/t57sb01'
    }
    
    print(f"📁 目標檔案: {pdf_info['filename']}")
    print(f"📏 預期大小: {pdf_info['size']:,} bytes")
    print(f"📅 上傳日期: {pdf_info['upload_date']}")
    print("-" * 40)
    
    try:
        session = requests.Session()
        
        print("🔍 步驟1：執行查詢...")
        response = session.post(query_url, data=query_data, headers=headers)
        
        if response.status_code == 200:
            print("✅ 查詢成功")
            
            # 解析回應中的PDF連結
            content = response.text
            
            # 尋找PDF連結
            pdf_link_pattern = r"href='(/pdf/[^']+)'"
            match = re.search(pdf_link_pattern, content)
            
            if match:
                pdf_path = match.group(1)
                pdf_url = urljoin(base_url, pdf_path)
                
                print(f"✅ 找到PDF連結: {pdf_path}")
                print(f"🔗 完整URL: {pdf_url}")
                print("-" * 40)
                
                # 步驟2：下載PDF
                print("📥 步驟2：下載PDF...")
                
                pdf_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/pdf,application/octet-stream,*/*',
                    'Referer': query_url
                }
                
                pdf_response = session.get(pdf_url, headers=pdf_headers, stream=True)
                
                if pdf_response.status_code == 200:
                    content_type = pdf_response.headers.get('Content-Type', '')
                    print(f"📄 內容類型: {content_type}")
                    
                    if 'pdf' in content_type.lower() or 'application/octet-stream' in content_type:
                        # 儲存PDF檔案
                        file_path = output_dir / pdf_info['filename']
                        
                        with open(file_path, 'wb') as f:
                            downloaded_size = 0
                            for chunk in pdf_response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    downloaded_size += len(chunk)
                            
                        actual_size = file_path.stat().st_size
                        print(f"✅ PDF下載完成！")
                        print(f"📏 實際大小: {actual_size:,} bytes")
                        print(f"💾 儲存路徑: {file_path}")
                        
                        # 檢查檔案完整性
                        size_match = abs(actual_size - pdf_info['size']) / pdf_info['size'] < 0.1  # 10%容差
                        
                        if actual_size > 100000 and (size_match or actual_size > pdf_info['size'] * 0.8):
                            print("✅ 檔案大小正常，下載成功")
                            
                            # 生成JSON檔案
                            json_path = file_path.with_suffix('.json')
                            json_data = {
                                "stock_code": "2330",
                                "company_name": "台積電",
                                "report_year": 2025,
                                "report_season": "Q1",
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
                                    "file_name": pdf_info['filename'],
                                    "file_path": str(file_path),
                                    "file_size": actual_size,
                                    "expected_size": pdf_info['size'],
                                    "size_match": size_match,
                                    "upload_date": pdf_info['upload_date'],
                                    "download_url": pdf_url,
                                    "crawled_at": datetime.now().isoformat(),
                                    "parser_version": "v3.2_improved",
                                    "validation": {
                                        "file_exists": file_path.exists(),
                                        "size_reasonable": actual_size > 100000,
                                        "size_match_expected": size_match
                                    },
                                    "note": "改進版測試下載：台積電2025Q1財報"
                                }
                            }
                            
                            with open(json_path, 'w', encoding='utf-8') as f:
                                json.dump(json_data, f, ensure_ascii=False, indent=2)
                            
                            print(f"✅ JSON檔案已生成: {json_path.name}")
                            
                            # 簡單驗證PDF檔案
                            if validate_pdf_file(file_path):
                                print("✅ PDF檔案驗證通過")
                                return True
                            else:
                                print("⚠️ PDF檔案驗證警告")
                                return True  # 仍視為成功，但有警告
                        else:
                            print("⚠️ 檔案大小異常，可能下載不完整")
                            return False
                    else:
                        print(f"❌ 下載的不是PDF檔案: {content_type}")
                        return False
                else:
                    print(f"❌ PDF下載失敗，HTTP狀態碼: {pdf_response.status_code}")
                    return False
            else:
                print("❌ 在回應中未找到PDF連結")
                # 保存debug資訊
                debug_path = output_dir / f"debug_query_{datetime.now().strftime('%H%M%S')}.html"
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"🔍 查詢回應已保存: {debug_path}")
                return False
        else:
            print(f"❌ 查詢失敗，HTTP狀態碼: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 下載過程發生錯誤: {e}")
        import traceback
        print(f"🔍 錯誤詳情: {traceback.format_exc()}")
        return False

def validate_pdf_file(file_path):
    """簡單驗證PDF檔案"""
    try:
        with open(file_path, 'rb') as f:
            # 檢查PDF檔案頭
            header = f.read(4)
            if header != b'%PDF':
                print("⚠️ 檔案不是有效的PDF格式")
                return False
            
            # 檢查檔案尾（簡單檢查）
            f.seek(-1024, 2)  # 從檔案末尾往前1024字節
            tail = f.read()
            if b'%%EOF' not in tail:
                print("⚠️ PDF檔案可能不完整")
                return False
        
        return True
    except Exception as e:
        print(f"⚠️ PDF驗證錯誤: {e}")
        return False

def main():
    """主程式"""
    start_time = datetime.now()
    print(f"⏰ 開始時間: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = download_tsmc_2025q1()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n⏰ 結束時間: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ 耗時: {duration:.1f} 秒")
    
    if success:
        print("\n🎉 台積電2025Q1財報下載成功！")
        
        # 檢查結果
        test_dir = Path(__file__).parent / 'data' / 'test_results'
        pdf_files = list(test_dir.glob("*.pdf"))
        json_files = list(test_dir.glob("*.json"))
        
        print(f"\n📊 結果統計:")
        print(f"   📄 PDF檔案: {len(pdf_files)} 個")
        print(f"   🔧 JSON檔案: {len(json_files)} 個")
        
        if pdf_files:
            print(f"\n📁 下載的檔案:")
            for pdf_file in pdf_files:
                size = pdf_file.stat().st_size
                print(f"   📄 {pdf_file.name} ({size:,} bytes)")
                
                # 檢查對應的JSON檔案
                json_file = pdf_file.with_suffix('.json')
                if json_file.exists():
                    print(f"   🔧 {json_file.name} ✅")
                else:
                    print(f"   🔧 {json_file.name} ❌")
    else:
        print("\n❌ 下載失敗")

if __name__ == '__main__':
    main()

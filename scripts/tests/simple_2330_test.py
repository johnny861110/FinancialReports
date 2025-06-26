#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
簡化版：測試下載台積電2330 2025Q1財報
"""

import sys
import json
import requests
from pathlib import Path
from datetime import datetime

def download_tsmc_2025q1():
    """直接下載台積電2025Q1財報"""
    
    print("🚀 台積電(2330) 2025Q1財報下載測試")
    print("=" * 50)
    
    # 設定輸出目錄
    output_dir = Path(__file__).parent / 'data' / 'test_results'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 已知的PDF資訊（從debug_responses中獲得）
    pdf_info = {
        'filename': '202501_2330_AI1.pdf',
        'size': 5715493,
        'upload_date': '114/05/15 13:40:15'
    }
    
    # 構建下載URL
    download_url = "https://doc.twse.com.tw/server-java/t57sb01"
    
    # 表單數據
    form_data = {
        'step': '9',
        'kind': 'A',
        'co_id': '2330',
        'filename': pdf_info['filename']
    }
    
    # 設置headers
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/pdf,application/octet-stream,*/*',
        'Referer': 'https://doc.twse.com.tw/server-java/t57sb01'
    }
    
    file_path = output_dir / pdf_info['filename']
    
    print(f"📁 目標檔案: {pdf_info['filename']}")
    print(f"📏 預期大小: {pdf_info['size']:,} bytes")
    print(f"📅 上傳日期: {pdf_info['upload_date']}")
    print(f"💾 儲存路徑: {file_path}")
    print("-" * 30)
    
    try:
        print("🔗 開始下載...")
        
        session = requests.Session()
        response = session.post(download_url, data=form_data, headers=headers, stream=True)
        
        if response.status_code == 200:
            print("✅ 伺服器回應成功")
            
            # 檢查Content-Type
            content_type = response.headers.get('Content-Type', '')
            print(f"📄 內容類型: {content_type}")
            
            if 'pdf' in content_type.lower() or 'application/octet-stream' in content_type:
                # 下載檔案
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # 檢查檔案大小
                actual_size = file_path.stat().st_size
                print(f"✅ 下載完成！")
                print(f"📏 實際大小: {actual_size:,} bytes")
                
                if actual_size > 100000:  # 大於100KB認為是有效PDF
                    print("✅ 檔案大小正常，可能下載成功")
                    
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
                            "upload_date": pdf_info['upload_date'],
                            "crawled_at": datetime.now().isoformat(),
                            "parser_version": "v3.1_manual",
                            "note": "手動測試下載：台積電2025Q1財報"
                        }
                    }
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    
                    print(f"✅ JSON檔案已生成: {json_path.name}")
                    return True
                else:
                    print("⚠️ 檔案大小異常，可能下載失敗")
                    return False
            else:
                print(f"❌ 回應不是PDF檔案: {content_type}")
                # 保存回應內容以供debug
                debug_path = output_dir / f"debug_response_{datetime.now().strftime('%H%M%S')}.html"
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"🔍 Debug檔案已保存: {debug_path}")
                return False
        else:
            print(f"❌ 下載失敗，HTTP狀態碼: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 下載過程發生錯誤: {e}")
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
            for pdf_file in pdf_files:
                size = pdf_file.stat().st_size
                print(f"   📄 {pdf_file.name} ({size:,} bytes)")
    else:
        print("\n❌ 下載失敗")
        print("💡 這可能是因為需要先進行查詢才能下載")

if __name__ == '__main__':
    main()

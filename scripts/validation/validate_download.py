#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
驗證下載的台積電2025Q1財報PDF檔案
"""

import json
from pathlib import Path

def validate_tsmc_download():
    """驗證台積電2025Q1財報下載結果"""
    
    print("🔍 台積電(2330) 2025Q1財報驗證")
    print("=" * 50)
    
    test_dir = Path(__file__).parent / 'data' / 'test_results'
    pdf_file = test_dir / '202501_2330_AI1.pdf'
    json_file = test_dir / '202501_2330_AI1.json'
    
    results = {
        'pdf_exists': False,
        'json_exists': False,
        'pdf_valid': False,
        'json_valid': False,
        'size_match': False,
        'metadata_complete': False
    }
    
    # 檢查PDF檔案
    print("📄 檢查PDF檔案...")
    if pdf_file.exists():
        results['pdf_exists'] = True
        file_size = pdf_file.stat().st_size
        print(f"✅ PDF檔案存在: {pdf_file.name}")
        print(f"📏 檔案大小: {file_size:,} bytes")
        
        # 檢查PDF格式
        try:
            with open(pdf_file, 'rb') as f:
                header = f.read(8)
                if header.startswith(b'%PDF'):
                    results['pdf_valid'] = True
                    print("✅ PDF格式有效")
                    
                    # 檢查檔案完整性
                    f.seek(-100, 2)
                    tail = f.read()
                    if b'%%EOF' in tail:
                        print("✅ PDF檔案完整")
                    else:
                        print("⚠️ PDF檔案可能不完整")
                else:
                    print("❌ 不是有效的PDF格式")
        except Exception as e:
            print(f"❌ PDF檔案讀取錯誤: {e}")
    else:
        print("❌ PDF檔案不存在")
    
    print("-" * 30)
    
    # 檢查JSON檔案
    print("🔧 檢查JSON檔案...")
    if json_file.exists():
        results['json_exists'] = True
        print(f"✅ JSON檔案存在: {json_file.name}")
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results['json_valid'] = True
            print("✅ JSON格式有效")
            
            # 檢查關鍵欄位
            required_fields = ['stock_code', 'company_name', 'report_year', 'report_season', 'metadata']
            missing_fields = []
            
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            if not missing_fields:
                results['metadata_complete'] = True
                print("✅ JSON結構完整")
                
                # 檢查檔案大小匹配
                if 'metadata' in data and 'file_size' in data['metadata']:
                    json_size = data['metadata']['file_size']
                    if pdf_file.exists():
                        actual_size = pdf_file.stat().st_size
                        if json_size == actual_size:
                            results['size_match'] = True
                            print("✅ 檔案大小匹配")
                        else:
                            print(f"⚠️ 檔案大小不匹配: JSON記錄{json_size}, 實際{actual_size}")
                
                # 顯示關鍵資訊
                print(f"📊 股票代碼: {data.get('stock_code', 'N/A')}")
                print(f"🏢 公司名稱: {data.get('company_name', 'N/A')}")
                print(f"📅 報告期間: {data.get('report_year', 'N/A')}年{data.get('report_season', 'N/A')}")
                
                if 'metadata' in data:
                    metadata = data['metadata']
                    print(f"📥 下載時間: {metadata.get('crawled_at', 'N/A')}")
                    print(f"🔗 來源URL: {metadata.get('source', 'N/A')}")
            else:
                print(f"❌ JSON缺少必要欄位: {missing_fields}")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON格式錯誤: {e}")
        except Exception as e:
            print(f"❌ JSON檔案讀取錯誤: {e}")
    else:
        print("❌ JSON檔案不存在")
    
    print("-" * 30)
    
    # 總結
    print("📊 驗證結果:")
    total_checks = len(results)
    passed_checks = sum(results.values())
    
    for check, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {check.replace('_', ' ').title()}")
    
    print(f"\n🎯 驗證通過率: {passed_checks}/{total_checks} ({passed_checks/total_checks*100:.1f}%)")
    
    if passed_checks == total_checks:
        print("🎉 所有驗證項目通過！台積電2025Q1財報下載完全成功！")
        return True
    elif passed_checks >= total_checks * 0.8:
        print("✅ 大部分驗證項目通過，下載基本成功")
        return True
    else:
        print("❌ 多個驗證項目失敗，請檢查下載過程")
        return False

def main():
    """主程式"""
    print("🔍 財報檔案驗證工具")
    print("=" * 50)
    
    success = validate_tsmc_download()
    
    if success:
        print("\n💡 建議下一步:")
        print("   1. 可以嘗試用PDF閱讀器開啟檔案確認內容")
        print("   2. 可以擴充測試其他公司/期間的財報下載")
        print("   3. 可以整合PDF內容解析功能提取財務數據")
    else:
        print("\n💡 建議排除問題:")
        print("   1. 檢查網路連線是否正常")
        print("   2. 確認TWSE網站是否可正常存取")
        print("   3. 重新執行下載測試")

if __name__ == '__main__':
    main()

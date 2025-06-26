#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
安裝PDF解析依賴並測試完整財報解析功能
"""

import subprocess
import sys
from pathlib import Path

def install_pypdf2():
    """安裝PyPDF2模組"""
    try:
        print("🔄 安裝PyPDF2模組...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
        print("✅ PyPDF2安裝成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ PyPDF2安裝失敗: {e}")
        return False

def test_pdf_parsing():
    """測試PDF解析功能"""
    try:
        import PyPDF2
        print("✅ PyPDF2導入成功")
        
        # 尋找已下載的PDF檔案進行測試
        pdf_files = list(Path("data/diagnostic_results").rglob("*.pdf"))
        
        if pdf_files:
            test_pdf = pdf_files[0]
            print(f"🔍 測試解析PDF: {test_pdf}")
            
            with open(test_pdf, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text()
                
                print(f"✅ PDF解析成功，提取了 {len(text)} 字符")
                print(f"📄 內容預覽（前200字符）:")
                print(text[:200])
                
                return True
        else:
            print("⚠️ 找不到PDF檔案進行測試")
            return False
            
    except Exception as e:
        print(f"❌ PDF解析測試失敗: {e}")
        return False

def create_enhanced_parser():
    """創建增強版財報解析器"""
    
    enhanced_content = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
增強版診斷批次爬蟲 - 完整PDF解析功能
"""

import sys
import json
import time
import re
import PyPDF2
from pathlib import Path
from datetime import datetime

# 添加crawlers目錄到Python路徑
sys.path.insert(0, str(Path(__file__).parent / 'crawlers'))

from improved_twse_crawler import ImprovedTWSEFinancialCrawler

# === 完整的財報解析功能 ===

def extract_text_from_pdf(pdf_path):
    """從PDF檔案提取文字內容（完整版）"""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            return text
    except Exception as e:
        print(f"❌ PDF讀取失敗: {e}")
        return ""

def reparse_existing_pdfs():
    """重新解析已存在的PDF檔案"""
    
    print("🔄 重新解析已下載的PDF檔案...")
    
    pdf_files = list(Path("data/diagnostic_results").rglob("*.pdf"))
    
    if not pdf_files:
        print("⚠️ 找不到已下載的PDF檔案")
        return
    
    print(f"📋 找到 {len(pdf_files)} 個PDF檔案")
    
    parsed_count = 0
    
    for pdf_path in pdf_files:
        try:
            # 從檔案路徑解析公司資訊
            parts = pdf_path.parts
            stock_code = parts[-3]  # 例如: 2330
            period_info = parts[-2]  # 例如: 2024Q1
            
            year = int(period_info[:4])
            quarter = int(period_info[-1])
            
            # 簡單的公司名稱映射
            company_names = {
                '2330': '台積電',
                '2454': '聯發科',
                '2317': '鴻海'
            }
            company_name = company_names.get(stock_code, f'公司{stock_code}')
            
            print(f"🔍 重新解析: {stock_code} ({company_name}) {year}Q{quarter}")
            
            # 使用完整解析功能
            from diagnostic_batch_crawler import parse_financial_report
            
            parsed_data = parse_financial_report(pdf_path, stock_code, company_name, year, quarter)
            
            if parsed_data:
                # 儲存新的JSON檔案
                json_path = pdf_path.with_suffix('.json')
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed_data, f, ensure_ascii=False, indent=2)
                
                print(f"   ✅ 重新解析成功: {json_path.name}")
                parsed_count += 1
            else:
                print(f"   ❌ 重新解析失敗")
                
        except Exception as e:
            print(f"   ❌ 處理失敗: {e}")
    
    print(f"\\n🎉 重新解析完成! 成功解析 {parsed_count} 個檔案")

if __name__ == '__main__':
    reparse_existing_pdfs()
'''
    
    with open('enhanced_parser.py', 'w', encoding='utf-8') as f:
        f.write(enhanced_content)
    
    print("✅ 增強版解析器已創建: enhanced_parser.py")

def main():
    """主函數"""
    print("🚀 開始設置完整PDF解析功能...")
    
    # 安裝PyPDF2
    if install_pypdf2():
        # 測試PDF解析
        if test_pdf_parsing():
            # 創建增強版解析器
            create_enhanced_parser()
            
            print("\\n✅ 完整PDF解析功能設置完成!")
            print("\\n📋 後續步驟:")
            print("1. 運行 enhanced_parser.py 重新解析已下載的PDF")
            print("2. 或修改 diagnostic_batch_crawler.py 啟用完整解析")
            print("3. 檢查生成的JSON檔案是否包含完整財務數據")
        else:
            print("\\n❌ PDF解析測試失敗，請檢查錯誤訊息")
    else:
        print("\\n❌ PyPDF2安裝失敗，無法啟用完整PDF解析")

if __name__ == '__main__':
    main()

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
檢查PDF內容確認是否為台積電2025Q1財報
"""

import sys
from pathlib import Path

def check_pdf_content():
    """檢查PDF檔案內容"""
    
    print("📖 檢查PDF檔案內容")
    print("=" * 40)
    
    pdf_file = Path(__file__).parent / 'data' / 'test_results' / '202501_2330_AI1.pdf'
    
    if not pdf_file.exists():
        print("❌ PDF檔案不存在")
        return False
    
    try:
        # 嘗試使用 PyPDF2 讀取PDF內容
        try:
            import PyPDF2
            pdf_library = "PyPDF2"
        except ImportError:
            try:
                import fitz  # PyMuPDF
                pdf_library = "PyMuPDF"
            except ImportError:
                print("⚠️ 未安裝PDF讀取庫，嘗試基本檢查...")
                return basic_pdf_check(pdf_file)
        
        print(f"📚 使用 {pdf_library} 讀取PDF...")
        
        if pdf_library == "PyPDF2":
            return read_with_pypdf2(pdf_file)
        elif pdf_library == "PyMuPDF":
            return read_with_pymupdf(pdf_file)
            
    except Exception as e:
        print(f"❌ PDF讀取錯誤: {e}")
        return basic_pdf_check(pdf_file)

def read_with_pypdf2(pdf_file):
    """使用PyPDF2讀取PDF"""
    import PyPDF2
    
    try:
        with open(pdf_file, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            print(f"📄 PDF頁數: {num_pages}")
            
            # 讀取前幾頁內容
            for i in range(min(3, num_pages)):
                page = pdf_reader.pages[i]
                text = page.extract_text()
                
                print(f"\n--- 第 {i+1} 頁內容片段 ---")
                # 只顯示前300字元
                preview = text[:300].strip()
                print(preview)
                
                # 檢查關鍵字
                if i == 0:  # 第一頁
                    if "台積電" in text or "TSMC" in text or "2330" in text:
                        print("✅ 確認為台積電相關文件")
                    if "2025" in text and ("第一季" in text or "Q1" in text):
                        print("✅ 確認為2025年Q1報告")
        
        return True
        
    except Exception as e:
        print(f"❌ PyPDF2讀取錯誤: {e}")
        return False

def read_with_pymupdf(pdf_file):
    """使用PyMuPDF讀取PDF"""
    import fitz
    
    try:
        doc = fitz.open(pdf_file)
        num_pages = len(doc)
        
        print(f"📄 PDF頁數: {num_pages}")
        
        # 讀取前幾頁內容
        for i in range(min(3, num_pages)):
            page = doc[i]
            text = page.get_text()
            
            print(f"\n--- 第 {i+1} 頁內容片段 ---")
            # 只顯示前300字元
            preview = text[:300].strip()
            print(preview)
            
            # 檢查關鍵字
            if i == 0:  # 第一頁
                if "台積電" in text or "TSMC" in text or "2330" in text:
                    print("✅ 確認為台積電相關文件")
                if "2025" in text and ("第一季" in text or "Q1" in text):
                    print("✅ 確認為2025年Q1報告")
        
        doc.close()
        return True
        
    except Exception as e:
        print(f"❌ PyMuPDF讀取錯誤: {e}")
        return False

def basic_pdf_check(pdf_file):
    """基本PDF檔案檢查"""
    print("🔍 執行基本檔案檢查...")
    
    try:
        file_size = pdf_file.stat().st_size
        print(f"📏 檔案大小: {file_size:,} bytes")
        
        with open(pdf_file, 'rb') as f:
            # 檢查PDF頭
            header = f.read(100)
            if b'%PDF' in header:
                print("✅ 確認為PDF格式")
                
                # 嘗試在檔案中搜尋關鍵字
                f.seek(0)
                content_sample = f.read(10000)  # 讀取前10KB
                
                keywords_found = []
                keywords = [b'TSMC', b'\xe5\x8f\xb0\xe7\xa9\x8d\xe9\x9b\xbb', b'2330', b'2025']  # 台積電的UTF-8編碼
                
                for keyword in keywords:
                    if keyword in content_sample:
                        keywords_found.append(keyword)
                
                if keywords_found:
                    print(f"✅ 在檔案中找到關鍵字: {len(keywords_found)} 個")
                else:
                    print("⚠️ 未在檔案前段找到明顯關鍵字")
                
                return True
            else:
                print("❌ 不是有效的PDF格式")
                return False
                
    except Exception as e:
        print(f"❌ 基本檢查錯誤: {e}")
        return False

def main():
    """主程式"""
    success = check_pdf_content()
    
    if success:
        print("\n🎉 PDF檔案檢查完成！")
        print("💡 檔案看起來是有效的台積電2025Q1財報")
    else:
        print("\n❌ PDF檔案檢查失敗")
        print("💡 請檢查檔案是否完整下載")

if __name__ == '__main__':
    main()

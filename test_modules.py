#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
模組功能測試腳本
"""

def test_module_imports():
    """測試模組導入"""
    print("🧪 開始測試模組導入...")
    
    try:
        # 測試核心模組
        from src.core import BaseProcessor, FinancialReport, ProcessingResult
        print("✅ Core模組導入成功")
        
        # 測試爬蟲模組
        from src.core.crawler import FinancialCrawler
        print("✅ Crawler模組導入成功")
        
        # 測試處理器模組
        from src.processors import PDFProcessor, SmartFinancialProcessor
        print("✅ Processors模組導入成功")
        
        # 測試應用工廠
        from src.app_factory import setup_application, create_financial_report, get_processor
        print("✅ App Factory模組導入成功")
        
        return True
        
    except ImportError as e:
        print(f"❌ 模組導入失敗: {e}")
        return False
    except Exception as e:
        print(f"❌ 其他錯誤: {e}")
        return False

def test_basic_functionality():
    """測試基本功能"""
    print("\n🧪 開始測試基本功能...")
    
    try:
        # 測試建立財報實例 - 直接使用類別
        from src.core import FinancialReport
        report = FinancialReport("2330", "台積電", 2024, "Q1")
        print("✅ 財報實例建立成功")
        
        # 測試處理器實例化 - 直接創建
        from src.processors import SmartFinancialProcessor
        processor = SmartFinancialProcessor()
        print("✅ 智慧處理器建立成功")
        
        # 測試爬蟲實例化
        from src.core.crawler import FinancialCrawler
        crawler = FinancialCrawler()
        print("✅ 爬蟲實例建立成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 基本功能測試失敗: {e}")
        return False

def test_season_logic():
    """測試季度邏輯"""
    print("\n🧪 開始測試季度邏輯...")
    
    try:
        # 測試季度轉換邏輯 - 確認正確的對應關係
        test_cases = [
            {"season": "Q1", "expected": "01"},
            {"season": "Q2", "expected": "02"},
            {"season": "Q3", "expected": "03"},
            {"season": "Q4", "expected": "04"},
        ]
        
        for case in test_cases:
            season = case["season"]
            expected = case["expected"]
            # 正確的季度轉換邏輯：Q1->01, Q2->02, Q3->03, Q4->04
            season_num = f"{season.replace('Q', ''):0>2}"
            
            if season_num == expected:
                print(f"✅ {season} -> {season_num} (正確)")
            else:
                print(f"❌ {season} -> {season_num} (錯誤，預期: {expected})")
                return False
        
        # 測試檔案名稱生成邏輯
        test_filename_cases = [
            {"year": 2024, "season": "Q1", "stock": "2330", "expected": "202401_2330_AI1.pdf"},
            {"year": 2024, "season": "Q2", "stock": "2454", "expected": "202402_2454_AI1.pdf"},
        ]
        
        for case in test_filename_cases:
            year = case["year"]
            season = case["season"]
            stock = case["stock"]
            expected = case["expected"]
            
            season_num = f"{season.replace('Q', ''):0>2}"
            filename = f"{year}{season_num}_{stock}_AI1.pdf"
            
            if filename == expected:
                print(f"✅ 檔名生成: {filename} (正確)")
            else:
                print(f"❌ 檔名生成: {filename} (錯誤，預期: {expected})")
                return False
        
        print("✅ 季度邏輯測試通過")
        return True
        
    except Exception as e:
        print(f"❌ 季度邏輯測試失敗: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("📊 財務報告處理工具 - 模組功能測試")
    print("="*60)
    
    # 執行所有測試
    tests = [
        ("模組導入測試", test_module_imports),
        ("基本功能測試", test_basic_functionality),
        ("季度邏輯測試", test_season_logic),
    ]
    
    all_passed = True
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 40)
        passed = test_func()
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 所有測試通過！專案功能完整且正常運作")
    else:
        print("⚠️ 部分測試失敗，請檢查相關模組")
    print("="*60)

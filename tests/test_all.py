#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
執行所有測試的主要測試套件
"""

import unittest
import sys
from pathlib import Path

# 添加專案根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 導入所有測試模組
from tests.test_crawler import TestFinancialCrawlerIntegration, TestCrawlerErrorHandling
from tests.test_processor import TestSmartFinancialProcessor, TestPatternMatching, TestDataIntegrity


class TestSuiteRunner:
    """測試套件執行器"""
    
    def __init__(self):
        self.loader = unittest.TestLoader()
        self.suite = unittest.TestSuite()
        
    def add_test_modules(self):
        """添加所有測試模組"""
        # 核心功能測試
        try:
            from test_core import (
                TestFinancialReport, TestProcessingResult, 
                TestConfigManager, TestFinancialCrawler, TestDataValidation
            )
            
            self.suite.addTest(self.loader.loadTestsFromTestCase(TestFinancialReport))
            self.suite.addTest(self.loader.loadTestsFromTestCase(TestProcessingResult))
            self.suite.addTest(self.loader.loadTestsFromTestCase(TestConfigManager))
            self.suite.addTest(self.loader.loadTestsFromTestCase(TestFinancialCrawler))
            self.suite.addTest(self.loader.loadTestsFromTestCase(TestDataValidation))
            print("[OK] 已加載核心功能測試")
        except ImportError as e:
            print(f"[WARNING] 無法載入核心測試: {e}")
        
        # 爬蟲測試
        self.suite.addTest(self.loader.loadTestsFromTestCase(TestFinancialCrawlerIntegration))
        self.suite.addTest(self.loader.loadTestsFromTestCase(TestCrawlerErrorHandling))
        print("[OK] 已加載爬蟲測試")
        
        # 處理器測試
        self.suite.addTest(self.loader.loadTestsFromTestCase(TestSmartFinancialProcessor))
        self.suite.addTest(self.loader.loadTestsFromTestCase(TestPatternMatching))
        self.suite.addTest(self.loader.loadTestsFromTestCase(TestDataIntegrity))
        print("[OK] 已加載處理器測試")
    
    def run_tests(self, verbosity=2):
        """執行所有測試"""
        print("[TEST] 開始執行完整測試套件")
        print("=" * 60)
        
        self.add_test_modules()
        
        # 建立測試執行器
        runner = unittest.TextTestRunner(
            verbosity=verbosity,
            stream=sys.stdout,
            descriptions=True,
            failfast=False
        )
        
        # 執行測試
        result = runner.run(self.suite)
        
        # 顯示測試摘要
        self.print_summary(result)
        
        return result.wasSuccessful()
    
    def print_summary(self, result):
        """打印測試摘要"""
        print("\n" + "=" * 60)
        print("[SUMMARY] 測試結果摘要")
        print("=" * 60)
        
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped) if hasattr(result, 'skipped') else 0
        passed = total_tests - failures - errors - skipped
        
        print(f"總計測試: {total_tests}")
        print(f"[PASS] 通過: {passed}")
        print(f"[FAIL] 失敗: {failures}")
        print(f"[ERROR] 錯誤: {errors}")
        print(f"[SKIP] 跳過: {skipped}")
        
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        print(f"成功率: {success_rate:.1f}%")
        
        if result.wasSuccessful():
            print("\n[SUCCESS] 所有測試通過！")
        else:
            print(f"\n[WARNING] 有 {failures + errors} 個測試失敗")
            
            if result.failures:
                print("\n[FAIL] 失敗的測試:")
                for test, traceback in result.failures:
                    print(f"  - {test}")
            
            if result.errors:
                print("\n[ERROR] 錯誤的測試:")
                for test, traceback in result.errors:
                    print(f"  - {test}")


def run_specific_tests():
    """執行特定分類的測試"""
    import argparse
    
    parser = argparse.ArgumentParser(description="執行財務報表處理系統測試")
    parser.add_argument("--core", action="store_true", help="只執行核心功能測試")
    parser.add_argument("--crawler", action="store_true", help="只執行爬蟲測試")
    parser.add_argument("--processor", action="store_true", help="只執行處理器測試")
    parser.add_argument("--verbose", "-v", action="store_true", help="詳細輸出")
    
    args = parser.parse_args()
    
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    if args.core:
        try:
            from test_core import (
                TestFinancialReport, TestProcessingResult, 
                TestConfigManager, TestFinancialCrawler, TestDataValidation
            )
            suite.addTest(loader.loadTestsFromTestCase(TestFinancialReport))
            suite.addTest(loader.loadTestsFromTestCase(TestProcessingResult))
            suite.addTest(loader.loadTestsFromTestCase(TestConfigManager))
            suite.addTest(loader.loadTestsFromTestCase(TestFinancialCrawler))
            suite.addTest(loader.loadTestsFromTestCase(TestDataValidation))
            print("[CORE] 執行核心功能測試")
        except ImportError as e:
            print(f"[ERROR] 無法載入核心測試: {e}")
            return False
    
    elif args.crawler:
        suite.addTest(loader.loadTestsFromTestCase(TestFinancialCrawlerIntegration))
        suite.addTest(loader.loadTestsFromTestCase(TestCrawlerErrorHandling))
        print("[CRAWLER] 執行爬蟲測試")
    
    elif args.processor:
        suite.addTest(loader.loadTestsFromTestCase(TestSmartFinancialProcessor))
        suite.addTest(loader.loadTestsFromTestCase(TestPatternMatching))
        suite.addTest(loader.loadTestsFromTestCase(TestDataIntegrity))
        print("[PROCESSOR] 執行處理器測試")
    
    else:
        # 執行所有測試
        runner = TestSuiteRunner()
        return runner.run_tests(verbosity=2 if args.verbose else 1)
    
    # 執行選定的測試
    runner = unittest.TextTestRunner(
        verbosity=2 if args.verbose else 1,
        stream=sys.stdout
    )
    
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_specific_tests()
    sys.exit(0 if success else 1)
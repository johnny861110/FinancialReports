#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
財報爬蟲功能測試腳本
驗證單筆查詢、批次查詢和JSON格式驗證功能
"""

import subprocess
import json
import sys
from pathlib import Path

def run_command(cmd, description):
    """執行命令並返回結果"""
    print(f"\n🧪 測試: {description}")
    print(f"📝 命令: {cmd}")
    print("-" * 50)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print("✅ 測試成功")
            if result.stdout:
                print(f"📊 輸出:\n{result.stdout}")
        else:
            print("❌ 測試失敗")
            if result.stderr:
                print(f"🔍 錯誤:\n{result.stderr}")
                
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
        return False

def main():
    """主測試函數"""
    print("🚀 財報爬蟲功能測試")
    print("=" * 60)
    
    test_results = []
    
    # 測試1: JSON格式驗證
    test_results.append(run_command(
        "python financial_crawler.py examples/single_query.json --validate-only",
        "JSON格式驗證"
    ))
    
    # 測試2: 單筆查詢
    test_results.append(run_command(
        "python financial_crawler.py examples/single_query.json",
        "單筆查詢下載"
    ))
    
    # 測試3: 直接JSON字串查詢 (使用PowerShell兼容語法)
    json_str = '{\"stock_code\":\"2882\",\"company_name\":\"國泰金\",\"year\":2024,\"season\":\"Q3\"}'
    test_results.append(run_command(
        f"python financial_crawler.py '{json_str}' --validate-only",
        "直接JSON字串查詢驗證"
    ))
    
    # 測試4: 批次查詢（小批次）
    test_results.append(run_command(
        "python financial_crawler.py examples/batch_query.json",
        "批次查詢下載"
    ))
    
    # 總結
    print("\n" + "=" * 60)
    print("📊 測試結果總結")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(test_results)
    failed_tests = total_tests - passed_tests
    
    print(f"🔢 總測試數: {total_tests}")
    print(f"✅ 通過: {passed_tests}")
    print(f"❌ 失敗: {failed_tests}")
    print(f"📈 成功率: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests == 0:
        print("\n🎉 所有測試通過！爬蟲功能正常運作")
    else:
        print(f"\n⚠️ 有 {failed_tests} 個測試失敗，請檢查相關功能")
    
    # 檢查輸出檔案
    print(f"\n📁 檢查輸出檔案:")
    
    output_dirs = [
        "data/financial_reports",
        "output"
    ]
    
    for dir_path in output_dirs:
        full_path = Path(__file__).parent / dir_path
        if full_path.exists():
            files = list(full_path.glob("*"))
            print(f"   📂 {dir_path}: {len(files)} 個檔案")
            for file in files[:5]:  # 只顯示前5個檔案
                if file.is_file():
                    size = file.stat().st_size
                    print(f"      📄 {file.name} ({size:,} bytes)")
        else:
            print(f"   📂 {dir_path}: 目錄不存在")

if __name__ == '__main__':
    main()

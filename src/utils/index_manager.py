#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
主索引管理模組
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional


class MasterIndexManager:
    """主索引管理器"""
    
    def __init__(self, index_file: Optional[Path] = None):
        if index_file is None:
            self.index_file = Path(__file__).parent.parent.parent / "data" / "master_index.json"
        else:
            self.index_file = index_file
    
    def load_index(self) -> Dict[str, Any]:
        """載入主索引檔案"""
        if not self.index_file.exists():
            return self._create_empty_index()
        
        try:
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 載入主索引失敗: {e}")
            return self._create_empty_index()
    
    def save_index(self, index_data: Dict[str, Any]) -> bool:
        """儲存主索引檔案"""
        # 確保目錄存在
        self.index_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 更新統計資訊
        index_data["last_updated"] = datetime.now().isoformat()
        index_data["total_reports"] = len(index_data.get("reports", []))
        
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"警告: 主索引儲存失敗: {e}")
            return False
    
    def add_report(self, stock_code: str, company_name: str, year: int, season: str, 
                   pdf_path: Path, json_path: Path, file_size: int, success: bool = True) -> bool:
        """將新的財報記錄添加到主索引"""
        index_data = self.load_index()
        
        # 建立新記錄
        report_record = {
            "id": f"{stock_code}_{year}Q{season}",
            "stock_code": stock_code,
            "company_name": company_name,
            "year": year,
            "season": f"Q{season}",
            "period": f"{year}Q{season}",
            "pdf_file": str(pdf_path).replace('\\', '/'),
            "json_file": str(json_path).replace('\\', '/'),
            "file_size": file_size,
            "download_success": success,
            "crawled_at": datetime.now().isoformat(),
            "file_exists": pdf_path.exists() if pdf_path else False
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
            print(f"🔄 更新主索引記錄: {report_record['id']}")
        else:
            # 新增記錄
            index_data["reports"].append(report_record)
            print(f"➕ 新增主索引記錄: {report_record['id']}")
        
        # 按日期排序 (最新的在前)
        index_data["reports"].sort(key=lambda x: x["crawled_at"], reverse=True)
        
        return self.save_index(index_data)
    
    def search_reports(self, stock_code: Optional[str] = None, 
                      company_name: Optional[str] = None,
                      year: Optional[int] = None,
                      season: Optional[str] = None) -> List[Dict[str, Any]]:
        """搜尋財報記錄"""
        index_data = self.load_index()
        results = []
        
        for report in index_data["reports"]:
            match = True
            
            if stock_code and report["stock_code"] != stock_code:
                match = False
            if company_name and company_name.lower() not in report["company_name"].lower():
                match = False
            if year and report["year"] != year:
                match = False
            if season and report["season"] != f"Q{season}":
                match = False
            
            if match:
                results.append(report)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """取得統計資訊"""
        index_data = self.load_index()
        reports = index_data["reports"]
        
        # 統計公司數量
        companies = set(report["stock_code"] for report in reports)
        
        # 統計年份分佈
        years = {}
        for report in reports:
            year = report["year"]
            if year not in years:
                years[year] = 0
            years[year] += 1
        
        return {
            "total_reports": len(reports),
            "total_companies": len(companies),
            "companies": sorted(companies),
            "years_distribution": years,
            "last_updated": index_data.get("last_updated", "未知")
        }
    
    def _create_empty_index(self) -> Dict[str, Any]:
        """建立空的索引結構"""
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "total_reports": 0,
            "reports": []
        }

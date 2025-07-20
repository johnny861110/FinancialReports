#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工具模組
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    """設置日誌"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        # 控制台處理器
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # 檔案處理器
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / f"{name}.log", encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        logger.setLevel(level)
    
    return logger


def load_json(file_path: Path) -> Dict[str, Any]:
    """載入JSON檔案"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        raise Exception(f"載入JSON失敗 {file_path}: {e}")


def save_json(data: Dict[str, Any], file_path: Path) -> None:
    """儲存JSON檔案"""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise Exception(f"儲存JSON失敗 {file_path}: {e}")


def validate_stock_code(stock_code: str) -> bool:
    """驗證股票代碼格式"""
    if not stock_code:
        return False
    
    # 台灣股票代碼通常是4位數字
    return stock_code.isdigit() and len(stock_code) == 4


def validate_season(season: str) -> bool:
    """驗證季度格式"""
    if not season:
        return False
    
    # 支援 Q1, Q2, Q3, Q4 或 1, 2, 3, 4
    season = season.upper().replace('Q', '')
    return season in ['1', '2', '3', '4']


def normalize_season(season: str) -> str:
    """標準化季度格式"""
    season = season.upper().replace('Q', '')
    if season in ['1', '2', '3', '4']:
        return f"Q{season}"
    return season


def parse_filename(filename: str) -> Optional[Dict[str, Any]]:
    """解析檔案名稱"""
    import re
    
    # 支援格式: YYYYMM_STOCKCODE_AI1.pdf 或 YYMM_STOCKCODE_AI1.pdf
    patterns = [
        r'(\d{4})(\d{2})_(\d{4})_AI1\.pdf',  # YYYYMM_STOCKCODE_AI1.pdf
        r'(\d{2})(\d{2})_(\d{4})_AI1\.pdf'   # YYMM_STOCKCODE_AI1.pdf
    ]
    
    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            year_part, month, stock_code = match.groups()
            
            # 處理年份
            if len(year_part) == 2:
                year = int(year_part) + 2000  # 假設是20xx年
            else:
                year = int(year_part)
            
            # 月份對應季度 - 正確的對應關係: Q1→03, Q2→06, Q3→09, Q4→12
            month_to_season = {'03': 'Q1', '06': 'Q2', '09': 'Q3', '12': 'Q4'}
            season = month_to_season.get(month, 'Q1')
            
            return {
                'year': year,
                'season': season,
                'stock_code': stock_code,
                'filename': filename
            }
    
    return None


def get_company_name(stock_code: str) -> str:
    """根據股票代碼獲取公司名稱"""
    # 簡單的公司名稱對應
    company_mapping = {
        '2330': '台積電',
        '2454': '聯發科',
        '2317': '鴻海',
        '2363': '矽統',
        '2379': '瑞昱',
        '2881': '兆豐金',
        '2882': '國泰金',
        '2412': '中華電',
        '3661': '世芯-KY'
    }
    
    return company_mapping.get(stock_code, f"公司{stock_code}")


def format_file_size(size_bytes: int) -> str:
    """格式化檔案大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"


def create_progress_reporter(total_items: int, description: str = "Processing"):
    """創建進度報告器"""
    class ProgressReporter:
        def __init__(self, total: int, desc: str):
            self.total = total
            self.current = 0
            self.description = desc
            self.start_time = datetime.now()
        
        def update(self, increment: int = 1):
            self.current += increment
            percentage = (self.current / self.total) * 100
            elapsed = datetime.now() - self.start_time
            
            if self.current > 0:
                estimated_total = elapsed * (self.total / self.current)
                remaining = estimated_total - elapsed
                print(f"\r{self.description}: {self.current}/{self.total} ({percentage:.1f}%) "
                      f"- 剩餘: {remaining}", end="", flush=True)
            
            if self.current >= self.total:
                print(f"\n{self.description} 完成! 總用時: {elapsed}")
        
        def finish(self):
            self.current = self.total
            self.update(0)
    
    return ProgressReporter(total_items, description)


def batch_process(items: List[Any], processor_func, batch_size: int = 10, 
                 progress_desc: str = "Processing") -> List[Any]:
    """批次處理"""
    results = []
    total_batches = (len(items) + batch_size - 1) // batch_size
    
    progress = create_progress_reporter(len(items), progress_desc)
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        
        for item in batch:
            try:
                result = processor_func(item)
                results.append(result)
            except Exception as e:
                logger = setup_logging("batch_processor")
                logger.error(f"批次處理項目失敗: {e}")
                results.append({"error": str(e), "item": item})
            
            progress.update()
    
    progress.finish()
    return results


def merge_configs(*configs: Dict[str, Any]) -> Dict[str, Any]:
    """合併多個配置字典"""
    merged = {}
    for config in configs:
        if config:
            merged.update(config)
    return merged


def ensure_directories(*paths: Path) -> None:
    """確保目錄存在"""
    for path in paths:
        if isinstance(path, str):
            path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

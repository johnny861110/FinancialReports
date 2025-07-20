#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
處理進度追蹤和狀態管理系統
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict

from ..core import ProcessingResult


class ProcessingStatus(Enum):
    """處理狀態枚舉"""
    PENDING = "pending"          # 待處理
    DOWNLOADING = "downloading"   # 下載中
    DOWNLOADED = "downloaded"     # 已下載
    PROCESSING = "processing"     # 處理中
    PROCESSED = "processed"       # 已處理
    ENHANCED = "enhanced"         # 已增強
    FAILED = "failed"            # 失敗
    SKIPPED = "skipped"          # 跳過


@dataclass
class ProcessingTask:
    """處理任務"""
    id: str                      # 任務ID (格式: stockcode_YYYYQX)
    stock_code: str
    company_name: str
    year: int
    season: str
    status: ProcessingStatus
    created_at: datetime
    updated_at: datetime
    pdf_path: Optional[str] = None
    json_path: Optional[str] = None
    processed_path: Optional[str] = None
    enhanced_path: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None  # 處理時間(秒)
    retry_count: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ProcessingTracker:
    """處理進度追蹤器"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path("data/processing_tracker.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化資料庫"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS processing_tasks (
                    id TEXT PRIMARY KEY,
                    stock_code TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    season TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    pdf_path TEXT,
                    json_path TEXT,
                    processed_path TEXT,
                    enhanced_path TEXT,
                    error_message TEXT,
                    processing_time REAL,
                    retry_count INTEGER DEFAULT 0,
                    metadata TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status ON processing_tasks(status)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_year ON processing_tasks(stock_code, year, season)
            """)
    
    def create_task(self, stock_code: str, company_name: str, year: int, season: str) -> ProcessingTask:
        """創建新任務"""
        task_id = f"{stock_code}_{year}Q{season.replace('Q', '')}"
        now = datetime.now()
        
        task = ProcessingTask(
            id=task_id,
            stock_code=stock_code,
            company_name=company_name,
            year=year,
            season=season,
            status=ProcessingStatus.PENDING,
            created_at=now,
            updated_at=now
        )
        
        self._save_task(task)
        return task
    
    def get_task(self, task_id: str) -> Optional[ProcessingTask]:
        """取得任務"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM processing_tasks WHERE id = ?", (task_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return self._row_to_task(row)
            return None
    
    def update_task(self, task: ProcessingTask):
        """更新任務"""
        task.updated_at = datetime.now()
        self._save_task(task)
    
    def update_task_status(self, task_id: str, status: ProcessingStatus, 
                          error_message: Optional[str] = None,
                          processing_time: Optional[float] = None):
        """更新任務狀態"""
        task = self.get_task(task_id)
        if task:
            task.status = status
            task.updated_at = datetime.now()
            
            if error_message:
                task.error_message = error_message
                if status == ProcessingStatus.FAILED:
                    task.retry_count += 1
            
            if processing_time:
                task.processing_time = processing_time
            
            self._save_task(task)
    
    def update_task_paths(self, task_id: str, **paths):
        """更新任務檔案路徑"""
        task = self.get_task(task_id)
        if task:
            if 'pdf_path' in paths:
                task.pdf_path = paths['pdf_path']
            if 'json_path' in paths:
                task.json_path = paths['json_path']
            if 'processed_path' in paths:
                task.processed_path = paths['processed_path']
            if 'enhanced_path' in paths:
                task.enhanced_path = paths['enhanced_path']
            
            task.updated_at = datetime.now()
            self._save_task(task)
    
    def get_tasks_by_status(self, status: ProcessingStatus) -> List[ProcessingTask]:
        """按狀態取得任務列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM processing_tasks WHERE status = ? ORDER BY created_at",
                (status.value,)
            )
            return [self._row_to_task(row) for row in cursor.fetchall()]
    
    def get_all_tasks(self, order_by: str = "created_at") -> List[ProcessingTask]:
        """取得所有任務"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                f"SELECT * FROM processing_tasks ORDER BY {order_by}"
            )
            return [self._row_to_task(row) for row in cursor.fetchall()]
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """取得處理統計資訊"""
        with sqlite3.connect(self.db_path) as conn:
            # 狀態統計
            cursor = conn.execute("""
                SELECT status, COUNT(*) as count 
                FROM processing_tasks 
                GROUP BY status
            """)
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 公司統計
            cursor = conn.execute("""
                SELECT company_name, COUNT(*) as count 
                FROM processing_tasks 
                GROUP BY company_name 
                ORDER BY count DESC
            """)
            company_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 年度統計
            cursor = conn.execute("""
                SELECT year, COUNT(*) as count 
                FROM processing_tasks 
                GROUP BY year 
                ORDER BY year DESC
            """)
            year_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 處理時間統計
            cursor = conn.execute("""
                SELECT AVG(processing_time) as avg_time, 
                       MIN(processing_time) as min_time,
                       MAX(processing_time) as max_time
                FROM processing_tasks 
                WHERE processing_time IS NOT NULL
            """)
            time_stats = cursor.fetchone()
            
            # 錯誤統計
            cursor = conn.execute("""
                SELECT error_message, COUNT(*) as count 
                FROM processing_tasks 
                WHERE error_message IS NOT NULL 
                GROUP BY error_message 
                ORDER BY count DESC 
                LIMIT 10
            """)
            error_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                "total_tasks": sum(status_counts.values()),
                "status_distribution": status_counts,
                "company_distribution": company_counts,
                "year_distribution": year_counts,
                "processing_time": {
                    "average": time_stats[0] if time_stats[0] else 0,
                    "minimum": time_stats[1] if time_stats[1] else 0,
                    "maximum": time_stats[2] if time_stats[2] else 0
                },
                "common_errors": error_counts,
                "generated_at": datetime.now().isoformat()
            }
    
    def _save_task(self, task: ProcessingTask):
        """儲存任務到資料庫"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO processing_tasks 
                (id, stock_code, company_name, year, season, status, created_at, updated_at,
                 pdf_path, json_path, processed_path, enhanced_path, error_message, 
                 processing_time, retry_count, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.stock_code, task.company_name, task.year, task.season,
                task.status.value, task.created_at.isoformat(), task.updated_at.isoformat(),
                task.pdf_path, task.json_path, task.processed_path, task.enhanced_path,
                task.error_message, task.processing_time, task.retry_count,
                json.dumps(task.metadata, ensure_ascii=False) if task.metadata else None
            ))
    
    def _row_to_task(self, row) -> ProcessingTask:
        """將資料庫行轉換為任務物件"""
        return ProcessingTask(
            id=row['id'],
            stock_code=row['stock_code'],
            company_name=row['company_name'],
            year=row['year'],
            season=row['season'],
            status=ProcessingStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            pdf_path=row['pdf_path'],
            json_path=row['json_path'],
            processed_path=row['processed_path'],
            enhanced_path=row['enhanced_path'],
            error_message=row['error_message'],
            processing_time=row['processing_time'],
            retry_count=row['retry_count'],
            metadata=json.loads(row['metadata']) if row['metadata'] else {}
        )


class ProgressReporter:
    """進度報告生成器"""
    
    def __init__(self, tracker: ProcessingTracker):
        self.tracker = tracker
    
    def generate_progress_report(self) -> Dict[str, Any]:
        """生成進度報告"""
        stats = self.tracker.get_processing_statistics()
        
        # 計算完成率
        total = stats["total_tasks"]
        completed = stats["status_distribution"].get(ProcessingStatus.ENHANCED.value, 0)
        completion_rate = (completed / total * 100) if total > 0 else 0
        
        # 識別問題任務
        failed_tasks = self.tracker.get_tasks_by_status(ProcessingStatus.FAILED)
        retry_needed = [task for task in failed_tasks if task.retry_count < 3]
        
        # 計算預估剩餘時間
        avg_time = stats["processing_time"]["average"]
        pending_count = stats["status_distribution"].get(ProcessingStatus.PENDING.value, 0)
        estimated_time = (avg_time * pending_count) if avg_time > 0 else 0
        
        return {
            "overview": {
                "total_tasks": total,
                "completed_tasks": completed,
                "completion_rate": round(completion_rate, 2),
                "estimated_remaining_time_minutes": round(estimated_time / 60, 1) if estimated_time else 0
            },
            "status_breakdown": stats["status_distribution"],
            "performance": {
                "average_processing_time_seconds": round(stats["processing_time"]["average"], 2) if stats["processing_time"]["average"] else 0,
                "fastest_processing_seconds": stats["processing_time"]["minimum"],
                "slowest_processing_seconds": stats["processing_time"]["maximum"]
            },
            "issues": {
                "failed_tasks_count": len(failed_tasks),
                "tasks_need_retry": len(retry_needed),
                "common_errors": stats["common_errors"]
            },
            "recommendations": self._generate_recommendations(stats, failed_tasks),
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, stats: Dict, failed_tasks: List[ProcessingTask]) -> List[str]:
        """生成建議"""
        recommendations = []
        
        # 基於失敗率的建議
        total = stats["total_tasks"]
        failed_count = len(failed_tasks)
        if total > 0:
            failure_rate = failed_count / total
            if failure_rate > 0.2:  # 20%以上失敗率
                recommendations.append("失敗率較高，建議檢查PDF品質和OCR設定")
        
        # 基於處理時間的建議
        avg_time = stats["processing_time"]["average"]
        if avg_time and avg_time > 300:  # 超過5分鐘
            recommendations.append("處理時間較長，建議啟用並行處理或GPU加速")
        
        # 基於錯誤類型的建議
        common_errors = stats["common_errors"]
        for error, count in common_errors.items():
            if "OCR" in error or "文字識別" in error:
                recommendations.append("OCR相關錯誤較多，建議調整信心閾值或切換OCR引擎")
            elif "網路" in error or "下載" in error:
                recommendations.append("網路相關錯誤較多，建議增加重試次數或檢查網路連線")
        
        return recommendations
    
    def print_progress_summary(self):
        """列印進度摘要"""
        report = self.generate_progress_report()
        
        print("📊 處理進度報告")
        print("=" * 50)
        
        overview = report["overview"]
        print(f"總任務數: {overview['total_tasks']}")
        print(f"已完成: {overview['completed_tasks']}")
        print(f"完成率: {overview['completion_rate']}%")
        
        if overview['estimated_remaining_time_minutes'] > 0:
            print(f"預估剩餘時間: {overview['estimated_remaining_time_minutes']} 分鐘")
        
        print("\n📈 狀態分佈:")
        for status, count in report["status_breakdown"].items():
            print(f"  {status}: {count}")
        
        if report["issues"]["failed_tasks_count"] > 0:
            print(f"\n⚠️ 失敗任務: {report['issues']['failed_tasks_count']}")
            if report["issues"]["tasks_need_retry"] > 0:
                print(f"   需要重試: {report['issues']['tasks_need_retry']}")
        
        if report["recommendations"]:
            print("\n💡 建議:")
            for rec in report["recommendations"]:
                print(f"  - {rec}")


if __name__ == "__main__":
    # 測試進度追蹤器
    tracker = ProcessingTracker()
    reporter = ProgressReporter(tracker)
    
    # 創建測試任務
    task = tracker.create_task("2330", "台積電", 2024, "Q1")
    print(f"創建任務: {task.id}")
    
    # 更新狀態
    tracker.update_task_status(task.id, ProcessingStatus.DOWNLOADED)
    tracker.update_task_paths(task.id, pdf_path="test.pdf", json_path="test.json")
    
    # 生成報告
    reporter.print_progress_summary()

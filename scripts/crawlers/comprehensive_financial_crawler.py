#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
專案整理與大規模財報爬取腳本
測試目標：2330、2454、2317 三家公司 2022Q1~2025Q1 共39個期間
"""

import sys
import json
import time
import shutil
from pathlib import Path
from datetime import datetime

# 添加crawlers目錄到Python路徑
sys.path.insert(0, str(Path(__file__).parent / 'crawlers'))

from improved_twse_crawler import ImprovedTWSEFinancialCrawler

class ProjectReorganizer:
    """專案重新整理器"""
    
    def __init__(self):
        self.root_dir = Path(__file__).parent
        self.data_dir = self.root_dir / 'data'
        self.main_results_dir = self.data_dir / 'financial_reports_main'
        
        # 目標公司（3家重點公司）
        self.target_companies = {
            '2330': '台積電',
            '2454': '聯發科',
            '2317': '鴻海'
        }
        
        # 目標期間（2022Q1~2025Q1，共13季度）
        self.target_periods = []
        for year in range(2022, 2026):
            for quarter in range(1, 5):
                if year == 2025 and quarter > 1:  # 2025年只到Q1
                    break
                self.target_periods.append((year, quarter))
        
        print(f"📊 目標：{len(self.target_companies)} 家公司 × {len(self.target_periods)} 個期間 = {len(self.target_companies) * len(self.target_periods)} 個任務")
        
        # 統計數據
        self.stats = {
            'total_attempts': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'no_data_count': 0,
            'financial_holding_count': 0,
            'server_error_count': 0,
            'parsed_reports': [],
            'errors': []
        }
    
    def cleanup_old_data(self):
        """清理舊的測試資料"""
        print("🧹 清理舊的測試資料...")
        
        cleanup_targets = [
            self.data_dir / 'diagnostic_results',
            self.data_dir / 'etf0050_reports',
            self.root_dir / 'debug_responses',
        ]
        
        for target in cleanup_targets:
            if target.exists():
                try:
                    if target.is_dir():
                        shutil.rmtree(target)
                        print(f"   ✅ 已刪除目錄: {target}")
                    else:
                        target.unlink()
                        print(f"   ✅ 已刪除檔案: {target}")
                except Exception as e:
                    print(f"   ⚠️ 無法刪除 {target}: {e}")
    
    def setup_new_structure(self):
        """建立新的專案結構"""
        print("📁 建立新的專案結構...")
        
        # 主要目錄結構
        dirs_to_create = [
            self.main_results_dir,
            self.main_results_dir / 'by_company',
            self.main_results_dir / 'by_period',
            self.main_results_dir / 'reports',
            self.main_results_dir / 'search_indexes',
            self.root_dir / 'debug_responses'
        ]
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ 建立目錄: {dir_path}")
        
        # 為每家公司建立目錄
        for stock_code, company_name in self.target_companies.items():
            company_dir = self.main_results_dir / 'by_company' / f"{stock_code}_{company_name}"
            company_dir.mkdir(exist_ok=True)
            print(f"   ✅ 建立公司目錄: {company_dir}")
        
        # 為每個期間建立目錄
        for year, quarter in self.target_periods:
            period_dir = self.main_results_dir / 'by_period' / f"{year}Q{quarter}"
            period_dir.mkdir(exist_ok=True)
        
        print(f"   ✅ 建立 {len(self.target_periods)} 個期間目錄")

class ComprehensiveCrawler(ProjectReorganizer):
    """全面性財報爬蟲"""
    
    def __init__(self):
        super().__init__()
        self.crawler = None
    
    def initialize_crawler(self):
        """初始化爬蟲"""
        print("🚀 初始化改進版爬蟲...")
        
        try:
            self.crawler = ImprovedTWSEFinancialCrawler(max_retries=3, retry_delay=3)
            
            if self.crawler.get_initial_page():
                print("✅ 爬蟲初始化成功")
                return True
            else:
                print("❌ 爬蟲初始化失敗")
                return False
                
        except Exception as e:
            print(f"❌ 爬蟲初始化異常: {e}")
            return False
    
    def crawl_single_report(self, stock_code, company_name, year, quarter, progress_info=""):
        """爬取單一財報"""
        
        print(f"📋 {progress_info} 處理 {stock_code} ({company_name}) {year}Q{quarter}...")
        
        try:
            # 查詢財報
            result = self.crawler.query_financial_reports(stock_code, year, quarter)
            self.stats['total_attempts'] += 1
            
            if result and result.get('status') == 'success' and result.get('pdf_files'):
                print(f"   ✅ 查詢成功，找到 {len(result['pdf_files'])} 個PDF")
                
                # 建立儲存目錄
                company_dir = self.main_results_dir / 'by_company' / f"{stock_code}_{company_name}"
                period_dir = company_dir / f"{year}Q{quarter}"
                period_dir.mkdir(parents=True, exist_ok=True)
                
                # 下載並解析PDF
                download_success = False
                for pdf_info in result['pdf_files']:
                    save_path = period_dir / pdf_info['filename']
                    
                    if self.crawler.download_pdf_file(pdf_info, save_path):
                        print(f"   ✅ PDF下載成功: {pdf_info['filename']}")
                        download_success = True
                        
                        # 解析財報並生成JSON
                        try:
                            parsed_data = self.parse_financial_report(save_path, stock_code, company_name, year, quarter)
                            if parsed_data:
                                # 儲存個別JSON檔案
                                json_path = save_path.with_suffix('.json')
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(parsed_data, f, ensure_ascii=False, indent=2)
                                
                                self.stats['parsed_reports'].append(parsed_data)
                                print(f"   ✅ 財報解析成功: {json_path.name}")
                                
                                # 複製到期間目錄
                                period_summary_dir = self.main_results_dir / 'by_period' / f"{year}Q{quarter}"
                                period_summary_file = period_summary_dir / f"{stock_code}_{company_name}.json"
                                
                                with open(period_summary_file, 'w', encoding='utf-8') as f:
                                    json.dump(parsed_data, f, ensure_ascii=False, indent=2)
                            else:
                                print(f"   ⚠️ 財報解析失敗")
                                self.stats['errors'].append(f"解析失敗: {stock_code} {year}Q{quarter}")
                        except Exception as parse_e:
                            print(f"   ❌ 財報解析異常: {parse_e}")
                            self.stats['errors'].append(f"解析異常: {stock_code} {year}Q{quarter} - {parse_e}")
                    else:
                        print(f"   ❌ PDF下載失敗: {pdf_info['filename']}")
                        self.stats['errors'].append(f"下載失敗: {pdf_info['filename']}")
                
                if download_success:
                    self.stats['successful_downloads'] += 1
                    return True
                else:
                    self.stats['failed_downloads'] += 1
                    return False
            
            elif result and result.get('status') in ['financial_holding', 'no_data', 'server_error']:
                status = result.get('status')
                message = result.get('message', '')
                print(f"   ⚠️ 查詢狀態: {status} - {message}")
                
                if status == 'no_data':
                    self.stats['no_data_count'] += 1
                elif status == 'financial_holding':
                    self.stats['financial_holding_count'] += 1
                elif status == 'server_error':
                    self.stats['server_error_count'] += 1
                
                self.stats['errors'].append(f"查詢狀態: {status} - {stock_code} {year}Q{quarter}")
                return False
            else:
                print(f"   ❌ 查詢失敗或狀態異常: {result.get('status') if result else 'None'}")
                self.stats['failed_downloads'] += 1
                self.stats['errors'].append(f"查詢失敗: {stock_code} {year}Q{quarter}")
                return False
                
        except Exception as e:
            print(f"   ❌ 處理異常: {e}")
            self.stats['failed_downloads'] += 1
            self.stats['errors'].append(f"處理異常: {stock_code} {year}Q{quarter} - {e}")
            return False
    
    def parse_financial_report(self, pdf_path, stock_code, company_name, year, quarter):
        """解析財報（簡化版本，可後續擴展）"""
        
        # 基本的財報JSON結構
        result = {
            "stock_code": stock_code,
            "company_name": company_name,
            "report_year": year,
            "report_season": f"Q{quarter}",
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
                "file_name": pdf_path.name,
                "file_path": str(pdf_path),
                "file_size": pdf_path.stat().st_size if pdf_path.exists() else 0,
                "crawled_at": datetime.now().isoformat(),
                "parser_version": "v3.0_basic",
                "note": "基本結構，可擴展PDF內容解析"
            }
        }
        
        return result
    
    def run_comprehensive_crawl(self):
        """運行全面性爬取"""
        
        print("🚀 開始全面性財報爬取...")
        print(f"📊 目標範圍: {list(self.target_companies.values())} - {self.target_periods[0][0]}Q{self.target_periods[0][1]} 至 {self.target_periods[-1][0]}Q{self.target_periods[-1][1]}")
        
        # 初始化爬蟲
        if not self.initialize_crawler():
            print("❌ 無法初始化爬蟲，終止執行")
            return False
        
        total_tasks = len(self.target_companies) * len(self.target_periods)
        current_task = 0
        
        # 開始批次爬取
        for stock_code, company_name in self.target_companies.items():
            print(f"\n🏢 開始處理 {stock_code} ({company_name})...")
            
            for year, quarter in self.target_periods:
                current_task += 1
                progress = f"[{current_task}/{total_tasks}]"
                
                success = self.crawl_single_report(stock_code, company_name, year, quarter, progress)
                
                # 動態調整延遲
                if success:
                    delay = 2.0  # 成功時較短延遲
                else:
                    delay = 3.0  # 失敗時較長延遲
                
                # 每10個任務後重新初始化連接
                if current_task % 10 == 0:
                    print(f"🔄 已處理 {current_task} 個任務，重新初始化連接...")
                    if not self.initialize_crawler():
                        print("❌ 重新初始化失敗，終止執行")
                        break
                    delay += 2.0
                
                time.sleep(delay)
        
        # 生成總結報告
        self.generate_comprehensive_report()
        return True
    
    def generate_comprehensive_report(self):
        """生成全面性總結報告"""
        
        print("\n📋 生成全面性總結報告...")
        
        # 計算統計數據
        success_rate = (self.stats['successful_downloads'] / self.stats['total_attempts'] * 100) if self.stats['total_attempts'] > 0 else 0
        
        # 主要統計報告
        main_report = {
            'project_info': {
                'title': 'ETF重點成分股財報全面爬取',
                'target_companies': self.target_companies,
                'target_periods': self.target_periods,
                'created_at': datetime.now().isoformat()
            },
            'statistics': {
                'total_attempts': self.stats['total_attempts'],
                'successful_downloads': self.stats['successful_downloads'],
                'failed_downloads': self.stats['failed_downloads'],
                'no_data_count': self.stats['no_data_count'],
                'financial_holding_count': self.stats['financial_holding_count'],
                'server_error_count': self.stats['server_error_count'],
                'success_rate': f"{success_rate:.1f}%",
                'parsed_reports_count': len(self.stats['parsed_reports'])
            },
            'coverage_analysis': self.analyze_coverage(),
            'error_summary': self.analyze_errors()
        }
        
        # 儲存主要報告
        main_report_file = self.main_results_dir / 'reports' / f"comprehensive_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(main_report_file, 'w', encoding='utf-8') as f:
            json.dump(main_report, f, ensure_ascii=False, indent=2)
        
        # 生成搜尋索引
        if self.stats['parsed_reports']:
            search_index = self.create_comprehensive_search_index()
            search_file = self.main_results_dir / 'search_indexes' / f"financial_index_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(search_file, 'w', encoding='utf-8') as f:
                json.dump(search_index, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 搜尋索引已生成: {search_file}")
        
        # 顯示結果
        print(f"\n🎉 全面性爬取完成!")
        print(f"📊 統計結果:")
        print(f"   總嘗試次數: {self.stats['total_attempts']}")
        print(f"   成功下載: {self.stats['successful_downloads']}")
        print(f"   失敗次數: {self.stats['failed_downloads']}")
        print(f"   查無資料: {self.stats['no_data_count']}")
        print(f"   成功率: {success_rate:.1f}%")
        print(f"   解析報告數: {len(self.stats['parsed_reports'])}")
        
        print(f"\n📄 報告檔案:")
        print(f"   主要報告: {main_report_file}")
        if self.stats['parsed_reports']:
            print(f"   搜尋索引: {search_file}")
        
        if self.stats['errors']:
            print(f"\n❌ 錯誤統計 ({len(self.stats['errors'])}):")
            error_types = {}
            for error in self.stats['errors']:
                error_key = error.split(':')[0] if ':' in error else error[:20]
                error_types[error_key] = error_types.get(error_key, 0) + 1
            
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"   {error_type}: {count}")
    
    def analyze_coverage(self):
        """分析覆蓋率"""
        coverage = {
            'by_company': {},
            'by_period': {},
            'total_expected': len(self.target_companies) * len(self.target_periods)
        }
        
        # 按公司分析
        for stock_code, company_name in self.target_companies.items():
            company_reports = [r for r in self.stats['parsed_reports'] if r['stock_code'] == stock_code]
            coverage['by_company'][stock_code] = {
                'company_name': company_name,
                'reports_count': len(company_reports),
                'coverage_rate': f"{len(company_reports) / len(self.target_periods) * 100:.1f}%",
                'available_periods': [f"{r['report_year']}Q{r['report_season'][-1]}" for r in company_reports]
            }
        
        # 按期間分析
        for year, quarter in self.target_periods:
            period_key = f"{year}Q{quarter}"
            period_reports = [r for r in self.stats['parsed_reports'] 
                            if r['report_year'] == year and r['report_season'] == f"Q{quarter}"]
            coverage['by_period'][period_key] = {
                'reports_count': len(period_reports),
                'coverage_rate': f"{len(period_reports) / len(self.target_companies) * 100:.1f}%",
                'available_companies': [r['stock_code'] for r in period_reports]
            }
        
        return coverage
    
    def analyze_errors(self):
        """分析錯誤"""
        error_analysis = {
            'total_errors': len(self.stats['errors']),
            'error_types': {},
            'sample_errors': self.stats['errors'][:20]  # 前20個錯誤樣本
        }
        
        for error in self.stats['errors']:
            error_type = error.split(':')[0] if ':' in error else 'unknown'
            error_analysis['error_types'][error_type] = error_analysis['error_types'].get(error_type, 0) + 1
        
        return error_analysis
    
    def create_comprehensive_search_index(self):
        """創建全面性搜尋索引"""
        
        # 按公司和期間組織資料
        companies = {}
        
        for report in self.stats['parsed_reports']:
            stock_code = report['stock_code']
            company_name = report['company_name']
            period = f"{report['report_year']}Q{report['report_season'][-1]}"
            
            if stock_code not in companies:
                companies[stock_code] = {
                    'stock_code': stock_code,
                    'company_name': company_name,
                    'periods': {}
                }
            
            companies[stock_code]['periods'][period] = {
                'report_year': report['report_year'],
                'report_season': report['report_season'],
                'financials': report['financials'],
                'income_statement': report['income_statement'],
                'metadata': report['metadata']
            }
        
        # 創建搜尋索引結構
        search_index = {
            'index_info': {
                'title': 'ETF重點成分股財報搜尋索引',
                'created_at': datetime.now().isoformat(),
                'total_companies': len(companies),
                'total_reports': len(self.stats['parsed_reports']),
                'data_source': 'TWSE',
                'coverage_period': f"{self.target_periods[0][0]}Q{self.target_periods[0][1]} - {self.target_periods[-1][0]}Q{self.target_periods[-1][1]}",
                'index_version': '3.0'
            },
            'companies': companies,
            'period_summary': {
                f"{year}Q{quarter}": {
                    'available_companies': [
                        r['stock_code'] for r in self.stats['parsed_reports'] 
                        if r['report_year'] == year and r['report_season'] == f"Q{quarter}"
                    ]
                }
                for year, quarter in self.target_periods
            },
            'company_summary': {
                stock_code: {
                    'company_name': data['company_name'],
                    'periods_count': len(data['periods']),
                    'available_periods': sorted(list(data['periods'].keys()))
                }
                for stock_code, data in companies.items()
            }
        }
        
        return search_index

def main():
    """主函數"""
    print("🚀 ETF重點成分股財報全面爬取與整理系統")
    print("=" * 60)
    
    # 創建爬蟲實例
    crawler = ComprehensiveCrawler()
    
    print("📋 執行計劃:")
    print(f"   目標公司: {list(crawler.target_companies.values())}")
    print(f"   目標期間: {crawler.target_periods[0][0]}Q{crawler.target_periods[0][1]} - {crawler.target_periods[-1][0]}Q{crawler.target_periods[-1][1]} (共{len(crawler.target_periods)}季)")
    print(f"   總任務數: {len(crawler.target_companies) * len(crawler.target_periods)}")
    
    # 確認執行
    confirm = input("\n是否繼續執行? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ 取消執行")
        return
    
    # 步驟1: 清理舊資料
    crawler.cleanup_old_data()
    
    # 步驟2: 建立新結構
    crawler.setup_new_structure()
    
    # 步驟3: 執行全面爬取
    success = crawler.run_comprehensive_crawl()
    
    if success:
        print("\n✅ 專案整理與爬取完成!")
        print(f"📁 結果儲存在: {crawler.main_results_dir}")
    else:
        print("\n❌ 爬取過程中遇到問題，請檢查錯誤訊息")

if __name__ == '__main__':
    main()

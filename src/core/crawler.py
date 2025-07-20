#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
財報爬蟲模組
"""

import requests
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import urljoin
import re

from . import BaseProcessor, FinancialReport, ProcessingResult, ConfigManager
from ..utils.index_manager import MasterIndexManager


class FinancialCrawler(BaseProcessor):
    """財報爬蟲"""
    
    def __init__(self, config: Optional[Dict] = None):
        # 如果傳入字典，則保存字典格式供內部使用
        self.config_dict = config
        # 為父類提供 None，讓它使用預設配置
        super().__init__(None)
        self.base_url = "https://doc.twse.com.tw"
        self.query_url = f"{self.base_url}/server-java/t57sb01"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Referer': f'{self.base_url}/server-java/t57sb01'
        })
        # 初始化索引管理器
        self.index_manager = MasterIndexManager()
    
    def process(self, input_data: Dict[str, Any], output_path: Optional[Path] = None) -> ProcessingResult:
        """處理財報下載請求"""
        try:
            if isinstance(input_data, list):
                return self._process_batch(input_data, output_path)
            else:
                return self._process_single(input_data, output_path)
        except Exception as e:
            self.logger.error(f"處理失敗: {e}")
            return ProcessingResult(False, f"處理失敗: {e}")
    
    def _process_single(self, query_data: Dict[str, Any], output_path: Optional[Path] = None) -> ProcessingResult:
        """處理單筆下載"""
        stock_code = query_data['stock_code']
        company_name = query_data['company_name']
        year = int(query_data['year'])
        season = query_data.get('season', 'Q1')  # 使用季度格式
        
        # 將季度轉換為編號格式：Q1→01, Q2→02, Q3→03, Q4→04
        season_num = season.replace('Q', '').zfill(2)
        
        self.logger.info(f"下載 {company_name}({stock_code}) {year}{season} 財報")
        
        # 建構檔案名稱 - 使用年份+季度編號格式，與現有PDF檔案一致
        filename = f"{year}{season_num}_{stock_code}_AI1.pdf"
        
        # 設定輸出路徑
        if output_path is None:
            output_dir = Path(self.config_dict.get('output_dir', 'data/financial_reports') if self.config_dict else 'data/financial_reports')
            output_path = output_dir / filename
        elif output_path.is_dir():
            # 如果給定的是目錄，則在該目錄下建立檔案
            output_path = output_path / filename
        # 如果給定的是檔案路徑，則直接使用
        
        # 執行下載
        result = self._download_report(stock_code, filename, output_path)
        
        if result.success:
            # 生成對應的JSON檔案
            json_path = output_path.with_suffix('.json')
            report = FinancialReport(stock_code, company_name, year, season)
            report.metadata.update({
                "source": "doc.twse.com.tw",
                "file_name": filename,
                "file_path": str(output_path),
                "file_size": output_path.stat().st_size if output_path.exists() else 0
            })
            report.save(json_path)
            
            # 更新主索引
            file_size = output_path.stat().st_size if output_path.exists() else 0
            self.index_manager.add_report(
                stock_code=stock_code,
                company_name=company_name, 
                year=year,
                season=season,
                pdf_path=output_path,
                json_path=json_path,
                file_size=file_size,
                success=True
            )
            
            result.data = {
                "pdf_path": str(output_path),
                "json_path": str(json_path),
                "file_size": file_size
            }
        
        return result
    
    def _process_batch(self, queries_data: List[Dict[str, Any]], output_path: Optional[Path] = None) -> ProcessingResult:
        """處理批次下載"""
        results = []
        total = len(queries_data)
        
        self.logger.info(f"批次處理 {total} 個查詢")
        
        for i, query in enumerate(queries_data, 1):
            self.logger.info(f"[{i}/{total}] 處理: {query.get('company_name', query.get('stock_code'))}")
            
            result = self._process_single(query, output_path)
            results.append(result.to_dict())
            
            # 添加延遲避免請求過快
            if i < total:
                time.sleep(self.config.download_delay)
        
        success_count = sum(1 for r in results if r['success'])
        
        return ProcessingResult(
            success=success_count > 0,
            message=f"批次處理完成: {success_count}/{total} 成功",
            data=results
        )
    
    def _download_report(self, stock_code: str, filename: str, output_path: Path) -> ProcessingResult:
        """下載財報檔案"""
        query_data = {
            'step': '9',
            'kind': 'A',
            'co_id': stock_code,
            'filename': filename
        }
        
        max_retry = self.config.processing.max_retry
        timeout = self.config.processing.timeout
        
        for attempt in range(max_retry):
            try:
                # 步驟1：查詢
                self.logger.info(f"執行查詢 (嘗試 {attempt + 1}/{max_retry})")
                response = self.session.post(self.query_url, data=query_data, timeout=timeout)
                
                if response.status_code != 200:
                    raise Exception(f"查詢失敗，HTTP狀態碼: {response.status_code}")
                
                # 解析回應找到下載連結
                pdf_links = self._parse_pdf_links(response.text, filename)
                
                if not pdf_links:
                    raise Exception("未找到PDF下載連結")
                
                # 步驟2：下載PDF
                pdf_link = pdf_links[0]
                download_url = urljoin(self.base_url, pdf_link['url'])
                
                self.logger.info(f"下載PDF: {download_url}")
                
                pdf_response = self.session.get(download_url, timeout=timeout)
                
                if pdf_response.status_code != 200:
                    raise Exception(f"下載失敗，HTTP狀態碼: {pdf_response.status_code}")
                
                # 儲存檔案
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'wb') as f:
                    f.write(pdf_response.content)
                
                # 驗證檔案
                if output_path.exists() and output_path.stat().st_size > 1000:
                    self.logger.info(f"下載成功: {output_path} ({output_path.stat().st_size:,} bytes)")
                    return ProcessingResult(True, "下載成功")
                else:
                    raise Exception("下載的檔案無效或太小")
            
            except Exception as e:
                self.logger.warning(f"嘗試 {attempt + 1} 失敗: {e}")
                if attempt == max_retry - 1:
                    return ProcessingResult(False, f"下載失敗 (已重試 {max_retry} 次): {e}")
                time.sleep(2 ** attempt)  # 指數退避
        
        return ProcessingResult(False, "下載失敗")
    
    def _parse_pdf_links(self, html_content: str, target_filename: str) -> List[Dict[str, Any]]:
        """解析PDF下載連結"""
        pdf_links = []
        
        # 正則表達式匹配PDF連結
        link_pattern = r'<a[^>]+href=["\']([^"\']*\.pdf[^"\']*)["\'][^>]*>([^<]*)</a>'
        size_pattern = r'(\d+(?:,\d+)*)\s*bytes?'
        
        matches = re.findall(link_pattern, html_content, re.IGNORECASE)
        
        for url, text in matches:
            if target_filename in url or target_filename.replace('.pdf', '') in text:
                # 尋找檔案大小
                size_match = re.search(size_pattern, text)
                size = int(size_match.group(1).replace(',', '')) if size_match else 0
                
                pdf_links.append({
                    'url': url,
                    'text': text.strip(),
                    'size': size,
                    'filename': target_filename
                })
        
        return pdf_links

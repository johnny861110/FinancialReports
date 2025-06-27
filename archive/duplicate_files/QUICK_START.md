# 🚀 快速使用指南

## 最常用的工具

### 1. 🎯 完整財報提取 (推薦)
```bash
cd 02_extraction_tools
python final_pdf_extractor.py
```
**用途**: 使用所有可用方法提取財報數據的終極工具

### 2. 🧠 智能分析提取
```bash
cd 02_extraction_tools  
python smart_pdf_analyzer.py
```
**用途**: 智能分析 PDF 結構並選擇最佳提取策略

### 3. ⚡ 基礎快速提取
```bash
cd 02_extraction_tools
python genjson.py
```
**用途**: 快速從 TXT 檔案提取基礎財務數據

### 4. 🔧 手動數據補充
```bash
cd 02_extraction_tools
python manual_data_supplement.py
```
**用途**: 建立模板供手動填入缺失數據

### 5. 🎯 ETF 0050 批量爬蟲 (新增)
```bash
python etf0050_financial_crawler.py
```
**用途**: 批量爬取 0050 成分股 2020-2025Q1 財報並自動分類

### 6. 🚀 完整分析工具 (推薦新工具)  
```bash
python etf0050_complete_analyzer.py
```
**用途**: 整合爬蟲 + 數據提取 + 分析報告的一站式工具

## 📁 檔案放置位置

### 傳統工具的檔案位置:
- PDF 檔案 → `01_original_data/`
- TXT 檔案 → `01_original_data/`
- JSON 結果 → `03_extracted_json/`
- 報告檔案 → `04_reports_and_guides/`

### 0050 分析專案的檔案位置:
- 下載的PDF → `0050_financial_reports/downloaded_reports/`
- 提取的數據 → `0050_financial_reports/extracted_data/`
- 按公司分類 → `0050_financial_reports/analysis_by_company/`
- 按年份分類 → `0050_financial_reports/analysis_by_year/`
- 分析報告 → `0050_financial_reports/reports/`

## 💡 使用流程

### 🎯 0050 分析專案 (推薦流程)
1. **執行完整分析**: 運行 `etf0050_complete_analyzer.py`
2. **選擇模式**: 測試模式 (10個) / 小批量 (50個) / 完整下載 (630個)
3. **自動處理**: 工具會自動下載→提取→分析→生成報告
4. **查看結果**: 
   - HTML報告: `0050_financial_reports/reports/analysis_report.html`
   - JSON數據: `0050_financial_reports/extracted_data/`
   - 公司分析: `0050_financial_reports/analysis_by_company/`

### 🔧 傳統單檔處理流程

1. **準備數據**: 將 PDF 檔案放入 `01_original_data/`
2. **執行提取**: 使用 `final_pdf_extractor.py`
3. **檢查結果**: 查看 `03_extracted_json/` 中的 JSON 檔案
4. **補充數據**: 如有需要，手動填入 null 值
5. **查看報告**: 檢查 `04_reports_and_guides/` 中的完成報告

## 🔍 故障排除

### 問題: 提取結果為空或不完整
**解決**: 
1. 檢查 PDF 是否為圖片掃描版本
2. 使用手動補充工具建立模板
3. 參考線上工具指南

### 問題: 編碼錯誤
**解決**: 
1. 確保所有檔案使用 UTF-8 編碼
2. 檢查檔案路徑是否包含特殊字符

## 📞 需要幫助？

查看 `04_reports_and_guides/` 資料夾中的詳細指南和報告。

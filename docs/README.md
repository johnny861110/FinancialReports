# 財報分析專案

**專案描述**: 台灣上市公司財報 PDF 自動化提取和分析工具

**整理時間**: C:\Users\johnn\FinancialReports

## 📁 資料夾結構

### 01_original_data/
原始 PDF 和 TXT 檔案
- 存放下載的財報 PDF 檔案
- PDF 轉換後的 TXT 檔案

### 02_extraction_tools/
提取工具程式
- 主要的財報數據提取程式
- 各種 PDF 處理工具
- 智能分析器

### 03_extracted_json/
提取結果 JSON 檔案
- 最終的財務數據 JSON 檔案
- 各階段的提取結果
- 模板檔案

### 04_reports_and_guides/
報告和指南檔案
- 提取完成報告
- 使用指南
- 專案文檔

### 05_legacy_tools/
舊版或試驗工具
- 早期版本的工具
- 實驗性程式
- 不再使用的腳本

### 06_temp_and_debug/
暫時檔案和調試資料
- 調試輸出檔案
- 暫時檔案
- Jupyter notebook

## 🎯 主要工具

### 核心提取工具:
- `02_extraction_tools/final_pdf_extractor.py` - 最終版 PDF 提取器
- `02_extraction_tools/smart_pdf_analyzer.py` - 智能 PDF 分析器
- `02_extraction_tools/genjson.py` - 基礎 JSON 生成器

### 手動補充:
- `02_extraction_tools/manual_data_supplement.py` - 手動數據補充工具

## 📊 提取結果

最新的提取結果位於 `03_extracted_json/` 資料夾中:
- `2337_2025Q1_final.json` - 旺宏電子 2025Q1 最終結果
- 其他歷史版本和模板檔案

## 🚀 快速開始

1. 將 PDF 檔案放入 `01_original_data/`
2. 執行 `02_extraction_tools/final_pdf_extractor.py`
3. 檢查 `03_extracted_json/` 中的結果
4. 參考 `04_reports_and_guides/` 中的指南進行手動補充

## 📈 專案進展

### 已完成:
✅ PDF 文字提取功能
✅ 智能數據識別
✅ JSON 格式輸出
✅ 手動補充工具
✅ 多層次提取策略

### 已移動的檔案:
- 202101_2330_AI1.pdf → 01_original_data
- 202401_2330_AI1.pdf → 01_original_data
- 202501_2337_AI1.pdf → 01_original_data
- 202501_2337_AI1.txt → 01_original_data
- openai_api_key.txt → 01_original_data
- requirements.txt → 01_original_data
- genjson.py → 02_extraction_tools
- advanced_pdf_extractor.py → 02_extraction_tools
- smart_pdf_analyzer.py → 02_extraction_tools
- final_pdf_extractor.py → 02_extraction_tools
- manual_data_supplement.py → 02_extraction_tools
- analyze_pdf_completeness.py → 02_extraction_tools
- pdf_to_text_improved.py → 02_extraction_tools
- 2337_2025Q1.json → 03_extracted_json
- 2337_2025Q1_advanced.json → 03_extracted_json
- 2337_2025Q1_final.json → 03_extracted_json
- 2337_2025Q1_smart_文字提取備用.json → 03_extracted_json
- 2337_2025Q1_template.json → 03_extracted_json
- tifrs_2025Q1.json → 03_extracted_json
- extraction_completion_report.txt → 04_reports_and_guides
- extraction_guide.txt → 04_reports_and_guides
- online_extraction_guide.txt → 04_reports_and_guides
- README.md → 04_reports_and_guides
- fetcher.py → 05_legacy_tools
- fetch_financial_report.py → 05_legacy_tools
- try.py → 05_legacy_tools
- main.py → 05_legacy_tools
- install_dependencies.py → 05_legacy_tools
- try.ipynb → 06_temp_and_debug


## 🔧 技術架構

- **Python 3.7+**
- **Windows PowerShell** (用於 PDF 處理)
- **正則表達式** (數據模式識別)
- **JSON** (數據格式)

## 📞 支援

如需協助，請參考 `04_reports_and_guides/` 資料夾中的相關文檔。

---
*此專案由 GitHub Copilot 協助建立和整理*

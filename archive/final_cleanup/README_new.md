# 📊 ETF 0050財報爬蟲與分析系統

## 🎯 專案說明

自動化財報爬取與分析系統，專門針對台灣ETF 0050重點成分股（台積電2330、聯發科2454、鴻海2317）設計，支援2022Q1至2025Q1期間的完整財報數據收集與分析。

## ✨ 主要功能

- 🚀 **自動爬取**: 從TWSE官網下載財報PDF檔案
- 📄 **智能解析**: 解析PDF內容並生成標準化JSON格式  
- 🔍 **批次處理**: 支援多公司、多期間的批次下載
- 📊 **搜尋索引**: 建立完整的財報搜尋索引系統
- 📋 **進度追蹤**: 詳細的下載統計與錯誤報告

## 🚀 快速開始

### 方法一：使用主程式（推薦）

```bash
python main.py
```

### 方法二：直接執行腳本

```bash
# 1. 查看系統狀態與使用說明
python financial_crawler_guide.py

# 2. 診斷測試（小範圍測試）
python diagnostic_batch_crawler.py

# 3. 執行完整財報爬取
python comprehensive_financial_crawler.py

# 4. 設定PDF解析環境（可選）
python setup_pdf_parsing.py
```

## 📁 專案結構

```text
FinancialReports/
├── main.py                              # 主程式入口
├── comprehensive_financial_crawler.py   # 完整批次爬蟲
├── diagnostic_batch_crawler.py          # 診斷測試工具
├── financial_crawler_guide.py           # 使用說明與狀態檢查
├── setup_pdf_parsing.py                 # PDF解析環境設定
├── requirements.txt                      # Python依賴清單
├── config/                               # 配置檔案
├── crawlers/                             # 核心爬蟲模組
├── data/financial_reports_main/          # 主要數據目錄
│   ├── by_company/                       # 按公司分類
│   ├── by_period/                        # 按期間分類
│   ├── reports/                          # 統計報告
│   └── search_indexes/                   # 搜尋索引
├── docs/                                 # 專案文檔
└── tools/                                # 輔助工具
```

## 📊 目標數據

- **公司**: 台積電(2330)、聯發科(2454)、鴻海(2317)
- **期間**: 2022Q1 ~ 2025Q1 (共13季)
- **總量**: 39個財報期間

## 🔧 安裝需求

```bash
pip install -r requirements.txt
```

### 可選依賴（完整PDF解析）

```bash
pip install PyPDF2
```

## 📈 使用案例

1. **投資分析**: 追蹤重點科技股的財務表現
2. **研究用途**: 學術研究的數據來源
3. **自動化監控**: 定期更新財報數據

## 🔍 輸出格式

- **PDF檔案**: 原始財報文件
- **JSON檔案**: 結構化財報數據
- **搜尋索引**: 便於程式化查詢的索引檔案

## 🛠️ 故障排除

詳細的故障排除說明請執行：

```bash
python financial_crawler_guide.py
```

## 📞 技術支援

- 查看系統狀態: `python main.py` → 選項5
- 檢查日誌輸出了解詳細錯誤
- 確認網路連接和目標公司代號正確性

---

*最後更新: 2025年6月27日*

# 📊 ETF 0050財報爬蟲與分析系統

## 🎯 專案概述

自動化財報爬取與分析系統，專門針對台灣ETF 0050重點成分股設計，透過TWSE (台灣證券交易所) 官方網站自動收集財報資料。系統採用現代化的Python架構，從傳統的Selenium方案升級為高效能的requests-based爬蟲，大幅提升穩定性與效率。

### 🏆 重點功能特色
- **🎯 專業定位**: 專注於台灣科技龍頭股票（台積電2330、聯發科2454、鴻海2317）
- **📅 時間跨度**: 涵蓋2022Q1至2025Q1，共13個季度完整數據
- **🔄 全自動化**: 從下載、解析到索引建立的完整自動化流程
- **📊 標準化**: 產生統一格式的JSON數據，便於後續分析
- **🔍 智能檢索**: 建立完整的搜尋索引系統，支援快速查詢

## ✨ 核心技術功能

### 🚀 自動爬取系統
- **網站適配**: 針對TWSE新版財報查詢系統優化
- **表單處理**: 自動填寫查詢表單並處理驗證機制
- **反爬蟲對策**: 智能請求間隔、User-Agent輪換、Session管理
- **錯誤恢復**: 多層次重試機制，自動處理網路異常
- **進度監控**: 即時顯示下載進度與成功率統計

### 📄 智能解析引擎
- **PDF處理**: 支援多種PDF格式，自動識別財報結構
- **數據提取**: 提取關鍵財務指標（資產負債表、損益表、現金流量表）
- **格式標準化**: 轉換為統一的JSON格式，保持數據一致性
- **元數據管理**: 記錄來源、時間戳、版本等完整追蹤資訊

### 🔍 批次處理架構
- **並發控制**: 智能管理併發請求，避免伺服器負載過重
- **任務排程**: 按公司和期間組織下載任務
- **失敗處理**: 自動記錄失敗原因，支援部分重試
- **資料完整性**: 確保PDF與JSON檔案同步產生

### 📊 搜尋索引系統
- **全文檢索**: 建立完整的財報搜尋索引
- **交叉查詢**: 支援按公司、期間、財務指標多維度查詢
- **效能優化**: 預先建立索引，提升查詢速度
- **擴展性**: 支援新增公司和期間的動態擴展

## 🚀 快速開始指南

### 📋 系統需求
- **Python版本**: 3.7+ (建議 3.9+)
- **作業系統**: Windows 10/11, macOS, Linux
- **記憶體**: 最少2GB可用記憶體
- **硬碟空間**: 至少1GB用於存放財報數據
- **網路連線**: 穩定的網際網路連線

### 🔧 環境安裝

#### 1. 基本環境設置
```bash
# 複製專案
git clone [repository-url]
cd FinancialReports

# 安裝基本依賴
pip install -r requirements.txt
```

#### 2. 可選功能設置
```bash
# 安裝完整PDF解析功能
pip install PyPDF2 pdfplumber

# 安裝資料分析工具（可選）
pip install pandas matplotlib seaborn
```

### 🎮 使用方式

#### 方法一：主程式界面（推薦新手）
```bash
python main.py
```

啟動後會顯示互動式選單：
- 選項1：查看使用說明與系統狀態
- 選項2：執行完整財報爬取（39個任務）
- 選項3：診斷測試爬蟲功能
- 選項4：設定PDF解析環境
- 選項5：查看專案結構與數據統計

#### 方法二：直接執行腳本（進階用戶）
```bash
# 系統檢查與說明
python financial_crawler_guide.py

# 小範圍診斷測試（建議首次使用）
python diagnostic_batch_crawler.py

# 完整批次爬取（所有公司所有期間）
python comprehensive_financial_crawler.py

# PDF解析環境設定
python setup_pdf_parsing.py
```

## 📁 詳細專案結構

```text
FinancialReports/
├── 📄 核心程式檔案
│   ├── main.py                              # 🎮 主程式入口 (互動式選單)
│   ├── comprehensive_financial_crawler.py   # 🚀 完整批次爬蟲引擎
│   ├── diagnostic_batch_crawler.py          # 🔍 診斷測試工具
│   ├── financial_crawler_guide.py           # 📚 使用說明與系統檢查
│   └── setup_pdf_parsing.py                 # ⚙️ PDF解析環境設定
│
├── 📁 配置與模組
│   ├── requirements.txt                      # 📦 Python依賴清單
│   ├── config/                              # ⚙️ 系統配置
│   │   ├── settings.py                      # 基本設定 (爬蟲參數)
│   │   └── xbrl_tags.json                   # XBRL標籤對照表
│   └── crawlers/                            # 🤖 核心爬蟲模組
│       ├── improved_twse_crawler.py         # TWSE財報爬蟲核心
│       └── improved_etf0050_crawler.py      # ETF成分股專用爬蟲
│
├── 📊 數據目錄結構
│   └── data/financial_reports_main/         # 主要數據目錄
│       ├── by_company/                      # 📂 按公司分類
│       │   ├── 2330_台積電/                 # 台積電財報
│       │   │   ├── 2022Q1/
│       │   │   │   ├── 202201_2330_AI1.pdf
│       │   │   │   └── 202201_2330_AI1.json
│       │   │   ├── 2022Q2/ ... 2025Q1/
│       │   ├── 2454_聯發科/                 # 聯發科財報
│       │   └── 2317_鴻海/                   # 鴻海財報
│       ├── by_period/                       # 📅 按期間分類
│       │   ├── 2022Q1/ 2022Q2/ ... 2025Q1/
│       ├── reports/                         # 📋 統計報告
│       │   ├── crawl_summary_*.json         # 爬取統計報告
│       │   └── download_summary.json       # 下載結果彙總
│       └── search_indexes/                  # 🔍 搜尋索引
│           └── financial_index_*.json      # 財報搜尋索引檔案
│
├── 📚 文檔與說明
│   ├── README.md                           # 📖 專案說明 (本檔案)
│   ├── USAGE_GUIDE.md                      # 📋 詳細使用指南
│   ├── PROJECT_STATUS.md                   # 📊 專案狀態報告
│   └── docs/                               # 📚 其他文檔
│
└── 🔧 輔助工具
    └── tools/                              # 🛠️ 輔助工具程式
```

## 📊 目標數據詳情

### 🏢 目標公司資訊
| 股票代號 | 公司名稱 | 產業分類 | 市值規模 |
|---------|----------|----------|----------|
| 2330 | 台灣積體電路製造 | 半導體製造 | 超大型股 |
| 2454 | 聯發科技 | IC設計 | 大型股 |
| 2317 | 鴻海精密工業 | 電子代工 | 超大型股 |

### 📅 數據期間範圍
- **起始期間**: 2022年第1季 (2022Q1)
- **結束期間**: 2025年第1季 (2025Q1)
- **總季數**: 13季
- **總任務數**: 39個財報 (3公司 × 13季)

### 📈 預期數據規模
- **PDF檔案**: 約39個，總大小約100-200MB
- **JSON檔案**: 約39個，總大小約5-10MB
- **索引檔案**: 1個主索引，大小約1-2MB
- **報告檔案**: 多個統計報告，總大小約1-5MB

## 🔧 安裝與依賴詳情

### 📦 必要依賴套件
```txt
requests>=2.28.0          # HTTP請求處理
beautifulsoup4>=4.11.0     # HTML解析
lxml>=4.9.0                # XML/HTML解析器
urllib3>=1.26.0            # URL處理工具
pathlib2>=2.3.0            # 路徑處理 (Python 3.7以下)
```

### 🔍 可選依賴套件
```txt
PyPDF2>=3.0.0              # PDF文字提取
pdfplumber>=0.7.0          # 進階PDF解析
pandas>=1.5.0              # 數據分析
matplotlib>=3.6.0          # 圖表繪製
seaborn>=0.12.0            # 統計圖表
openpyxl>=3.0.0            # Excel檔案處理
```

### ⚙️ 系統配置選項
可在 `config/settings.py` 中調整：
```python
# 爬蟲行為設定
REQUEST_DELAY = 2.0        # 請求間隔秒數
MAX_RETRIES = 3           # 最大重試次數
TIMEOUT = 30              # 請求超時秒數

# 檔案處理設定
PDF_DOWNLOAD_PATH = "data/financial_reports_main"
JSON_OUTPUT_PATH = "data/financial_reports_main"

# 日誌設定
LOG_LEVEL = "INFO"        # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "crawler.log"  # 日誌檔案名稱
```

## 📈 實際使用案例

### 💼 投資分析範例
```python
# 載入財報搜尋索引
import json
with open('data/financial_reports_main/search_indexes/financial_index_latest.json', 'r', encoding='utf-8') as f:
    index = json.load(f)

# 查詢台積電2024Q1財報
tsmc_2024q1 = index['companies']['2330']['periods']['2024Q1']
print(f"營收: {tsmc_2024q1['income_statement']['net_revenue']}")
print(f"淨利: {tsmc_2024q1['income_statement']['net_income']}")
```

### 📊 趨勢分析範例
```python
# 比較三家公司同期表現
companies = ['2330', '2454', '2317']
period = '2024Q1'

for company in companies:
    if period in index['companies'][company]['periods']:
        data = index['companies'][company]['periods'][period]
        print(f"{index['companies'][company]['company_name']}: {data['income_statement']['net_revenue']}")
```

### 🔍 批次數據提取
```python
# 提取所有期間的EPS數據
def extract_eps_trend(company_code):
    company_data = index['companies'][company_code]
    eps_data = {}
    
    for period, data in company_data['periods'].items():
        eps = data['income_statement']['eps']
        if eps is not None:
            eps_data[period] = eps
    
    return eps_data

# 使用範例
tsmc_eps = extract_eps_trend('2330')
print("台積電EPS趨勢:", tsmc_eps)
```

## 🔍 輸出格式詳細說明

### 📄 PDF檔案
- **命名格式**: `YYYYQQ_股票代號_AI1.pdf`
- **範例**: `202401_2330_AI1.pdf` (2024Q1台積電財報)
- **內容**: TWSE官方完整財報PDF文件
- **檔案大小**: 通常1-10MB

### 📊 JSON檔案結構
```json
{
  "stock_code": "2330",
  "company_name": "台積電",
  "report_year": 2024,
  "report_season": "Q1",
  "currency": "TWD",
  "unit": "千元",
  "financials": {
    "cash_and_equivalents": "現金及約當現金數值",
    "accounts_receivable": "應收帳款數值",
    "inventory": "存貨數值",
    "total_assets": "資產總額",
    "total_liabilities": "負債總額",
    "equity": "權益總額"
  },
  "income_statement": {
    "net_revenue": "營業收入",
    "gross_profit": "毛利",
    "operating_income": "營業利益",
    "net_income": "本期淨利",
    "eps": "每股盈餘"
  },
  "metadata": {
    "source": "doc.twse.com.tw",
    "file_name": "202401_2330_AI1.pdf",
    "file_path": "完整檔案路徑",
    "file_size": 5389648,
    "crawled_at": "2025-06-27T00:33:34",
    "parser_version": "v3.0",
    "note": "處理說明"
  }
}
```

### 🔍 搜尋索引結構
搜尋索引檔案整合所有公司的財報數據，支援：
- **公司查詢**: 按股票代號快速定位
- **期間查詢**: 按季度查看所有公司數據
- **統計資訊**: 數據完整度、覆蓋率統計
- **元數據**: 建立時間、版本、數據來源

## 🛠️ 進階故障排除

### 🚨 常見問題與解決方案

#### 1. 網路連線問題
```bash
# 檢查網路連線
ping doc.twse.com.tw

# 檢查DNS解析
nslookup doc.twse.com.tw
```

#### 2. PDF下載失敗
- **症狀**: PDF檔案大小為0或下載中斷
- **原因**: 網路不穩定或伺服器限制
- **解決**: 調整 `REQUEST_DELAY` 到5秒以上

#### 3. JSON解析錯誤
- **症狀**: JSON檔案中數據為null
- **原因**: PDF內容格式變更或解析器版本問題
- **解決**: 執行 `python setup_pdf_parsing.py` 更新解析器

#### 4. 記憶體不足
- **症狀**: 程式執行中當機
- **原因**: 大量PDF檔案同時處理
- **解決**: 減少併發數量或分批執行

### 🔧 調試模式
```bash
# 啟用詳細日誌
export LOG_LEVEL=DEBUG
python comprehensive_financial_crawler.py

# 檢查特定公司
python diagnostic_batch_crawler.py --company 2330

# 驗證特定期間
python diagnostic_batch_crawler.py --period 2024Q1
```

### 📊 效能監控
系統會自動產生效能報告：
- `reports/crawl_summary_*.json`: 爬取統計
- `reports/error_log_*.json`: 錯誤記錄
- `reports/performance_*.json`: 效能指標

## 📞 技術支援與聯絡

### 🔍 自助診斷
1. **系統狀態檢查**: `python main.py` → 選項5
2. **詳細使用說明**: `python financial_crawler_guide.py`
3. **錯誤日誌查看**: 檢查 `crawler.log` 檔案
4. **網路連線測試**: 嘗試手動訪問 TWSE 網站

### 📋 問題回報格式
提交問題時請包含：
1. **錯誤訊息**: 完整的錯誤輸出
2. **系統環境**: Python版本、作業系統
3. **執行指令**: 導致錯誤的具體操作
4. **相關檔案**: 錯誤發生時的日誌檔案

### 🔄 版本更新
- 定期檢查 TWSE 網站格式變更
- 關注 Python 套件版本更新
- 備份重要數據後進行系統更新

---

## 📈 專案發展歷程

### 🚀 技術演進
- **v1.0**: 基於Selenium的初始版本
- **v2.0**: 切換至requests-based架構
- **v3.0**: 新增智能解析與搜尋索引
- **v3.1**: 優化效能與錯誤處理 (當前版本)

### 📊 數據覆蓋率
目前已成功收集：
- **台積電**: 2022Q1-2024Q2 (部分期間)
- **聯發科**: 2022Q2-2023Q3 (連續期間)
- **鴻海**: 測試階段

### 🎯 未來規劃
- 擴展至更多ETF 0050成分股
- 新增即時財報監控功能
- 整合技術分析指標
- 開發Web界面版本

---

*📅 最後更新: 2025年6月27日*  
*🔧 系統版本: v3.1*  
*📊 數據版本: 2022Q1-2025Q1*

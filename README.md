# 🏦 財務報告處理工具 v2.0

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![uv](https://img.shields.io/badge/uv-supported-orange.svg)](https://github.com/astral-sh/uv)

台灣證券交易所財務報告智慧處理工具，採用現代化架構設計，支援自動爬取、PDF 解析、OCR 識別和數據結構化。

## ✨ 主要特色

- 🚀 **現代化架構** - 基於工廠模式和依賴注入的模組化設計
- 📊 **智慧解析** - 主打 pdfplumber 引擎，輔以 PaddleOCR 增強 OCR 功能
- 🔄 **自動爬取** - 台股財報自動下載，支援歷史數據回填
- 📈 **數據處理** - 財務數據提取、結構化輸出和品質驗證
- 🛡️ **錯誤處理** - 統一異常處理機制，完整的錯誤追蹤
- 🎯 **批次處理** - 支援 JSON 配置檔案的大量檔案批次作業
- 🔧 **彈性配置** - 完整的配置管理系統，支援動態服務註冊
- 📋 **季度邏輯** - 正確的季度編號處理（Q1-Q4 對應 01-04）

## 🚀 快速開始

### 環境需求

- **Python 3.9-3.12** (推薦 3.10+)
- **UV 套件管理器** (推薦方式)
- **Windows/Linux/macOS**
- **記憶體**: 建議 4GB+ (OCR 處理需要)

### 安裝

```bash
# 1. 克隆專案
git clone <repository-url>
cd FinancialReports

# 2. 安裝 UV (如果尚未安裝)
pip install uv

# 3. 安裝依賴套件
uv sync

# 4. 驗證安裝 - 應該看到系統資訊
uv run python main.py --info
```

**✅ 安裝成功標誌**: 出現系統資訊面板，顯示可用處理器和配置狀態

## 📖 使用方式

### 基本命令

```bash
# 查看系統資訊和可用功能
uv run python main.py --info

# 處理單個 PDF 檔案
uv run python main.py --pdf path/to/report.pdf

# 財務報告完整處理 (季度格式: Q1, Q2, Q3, Q4)
uv run python main.py --financial \
  --pdf report.pdf \
  --stock 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1

# 批次處理 JSON 查詢檔案
uv run python main.py --batch examples/batch_query.json
```

### 🗓️ 季度對應邏輯

專案使用以下季度對應格式，與台股財報檔名規則一致：

- **Q1** → `01` (第一季度，對應檔名 `YYYY01_股票代碼_AI1.pdf`)
- **Q2** → `02` (第二季度，對應檔名 `YYYY02_股票代碼_AI1.pdf`)  
- **Q3** → `03` (第三季度，對應檔名 `YYYY03_股票代碼_AI1.pdf`)
- **Q4** → `04` (第四季度，對應檔名 `YYYY04_股票代碼_AI1.pdf`)

### 📝 批次查詢範例

創建 `batch_query.json` 檔案：

```json
[
  {
    "stock_code": "2330",
    "company_name": "台積電",
    "year": 2024,
    "season": "Q1"
  },
  {
    "stock_code": "2454", 
    "company_name": "聯發科",
    "year": 2024,
    "season": "Q1"
  }
]
```

然後執行：

```bash
uv run python main.py --batch batch_query.json
```

## 📁 專案架構

```text
FinancialReports/
├── 📄 main.py                    # 主程式入口點
├── 📋 pyproject.toml             # 專案配置和依賴管理 (uv)
├── 🔒 uv.lock                   # 依賴版本鎖定檔
├── 📚 src/                       # 核心程式碼模組
│   ├── 🏗️ core/                  # 核心架構模組
│   │   ├── **init**.py          # 基礎類別、介面與工廠函數
│   │   ├── config.py            # 配置管理與依賴注入容器
│   │   ├── crawler.py           # 財報爬蟲核心邏輯
│   │   └── exceptions.py        # 統一異常處理機制
│   ├── 🔧 processors/            # 數據處理器模組
│   │   ├── pdf_processor.py     # PDF 處理引擎 (pdfplumber + OCR)
│   │   └── smart_processor.py   # 智慧財務數據處理器
│   ├── 📊 tracking/              # 進度追蹤與監控
│   │   └── progress_tracker.py  # 處理進度實時追蹤
│   ├── 🛠️ utils/                 # 通用工具函數
│   │   └── helpers.py           # 季度轉換、檔案操作等
│   ├── ✅ validators/            # 數據驗證器
│   │   └── financial_validator.py # 財務數據品質驗證
│   └── 🏭 app_factory.py         # 應用程式工廠與服務配置
├── 📜 scripts/                   # 執行腳本集合
│   ├── financial_crawler.py     # 獨立財報爬蟲腳本
│   ├── financial_backfill.py    # 歷史數據回填腳本
│   ├── smart_processor.py       # 智慧處理器執行腳本
│   ├── batch_extract.py         # 批次提取執行腳本
│   └── backfill_financial_data.py # 財務數據回填腳本
├── ⚙️ config/                    # 配置檔案目錄
│   ├── crawler_config.json      # 爬蟲行為配置
│   └── xbrl_tags.json          # XBRL 標籤定義檔
├── 📊 data/                      # 數據存儲目錄
│   ├── financial_reports/       # 原始財報檔案 (PDF + JSON)
│   ├── processed/               # 處理後的結構化數據
│   ├── processing_tracker.db    # SQLite 追蹤資料庫
│   └── master_index.json       # 主索引檔案
├── 📋 examples/                  # 使用範例檔案
│   ├── batch_query.json         # 基本批次查詢範例
│   └── semiconductor_batch.json # 半導體產業批次查詢範例
├── 🧪 tests/                     # 測試套件
│   ├── test_crawler.py          # 爬蟲功能單元測試
│   ├── test_processor.py        # 處理器功能測試
│   ├── test_all.py             # 完整功能集成測試
│   └── fixtures/                # 測試用固定資料
├── 📚 docs/                      # 技術文檔
│   ├── API.md                   # API 使用文檔
│   ├── DEPLOYMENT.md            # 部署配置指南
│   └── DEVELOPMENT.md           # 開發環境設定
└── 📝 logs/                      # 系統日誌目錄
    └── application.log          # 主要應用程式日誌
```

## 🔧 核心功能

### 1. 財務報告爬取

- **自動下載**: 從台灣證券交易所自動下載財務報告 PDF
- **季度管理**: 支援 Q1-Q4 季度格式，自動轉換為檔案編號 01-04
- **批次處理**: 支援多家公司、多季度的批次下載作業
- **進度追蹤**: 實時顯示下載進度和處理狀態

### 2. PDF 智慧解析

- **主要引擎**: pdfplumber 高精度文字和表格提取
- **輔助 OCR**: PaddleOCR 針對圖像化內容進行文字識別
- **表格識別**: 自動識別和提取財務報表結構
- **錯誤處理**: 完整的異常捕獲和降級處理機制

### 3. 財務數據結構化

- **關鍵指標提取**: 自動提取營收、淨利、EPS 等關鍵財務指標
- **數據驗證**: 內建財務數據合理性和完整性驗證
- **格式統一**: 輸出標準化的 JSON 格式結構化數據
- **增強處理**: 智慧財務處理器提供進階分析和補強功能

## 🔨 API 參考

### 命令行參數

```bash
uv run python main.py [OPTIONS]

選項:
  --help                    顯示幫助資訊
  --info                    顯示系統資訊和可用功能
  --config CONFIG           指定配置檔案路徑 (預設: config/crawler_config.json)
  --output OUTPUT           指定輸出目錄 (預設: data/financial_reports)

處理模式:
  --pdf PDF                 處理單個 PDF 檔案
  --batch BATCH            批次處理 JSON 查詢檔案或目錄
  --financial              財務報告處理模式 (需搭配其他參數)

財務報告參數:
  --stock STOCK            股票代碼 (例: 2330)
  --company COMPANY        公司名稱 (例: "台積電") 
  --year YEAR              年份 (例: 2024)
  --season SEASON          季度 (Q1, Q2, Q3, Q4)
```

### 核心 API 使用

#### 1. PDF 處理引擎

```python
from src.core import get_config
from src.processors.pdf_processor import ModernPDFProcessor

# 初始化處理器
config = get_config()
processor = ModernPDFProcessor(config.processing)

# 處理 PDF 檔案
result = processor.process("report.pdf", "output.json")
if result.success:
    print(f"處理成功: {result.data}")
else:
    print(f"處理失敗: {result.error}")
```

#### 2. 財務報告處理

```python
from src.app_factory import setup_application, create_financial_report
from src.processors.smart_processor import SmartFinancialProcessor

# 設置應用程式環境
config = setup_application()

# 創建財報實例
report = create_financial_report("2330", "台積電", 2024, "Q1")

# 智慧處理
processor = SmartFinancialProcessor()
result = processor.process_financial_data(raw_data)
```

#### 3. 批次處理系統

```python
from pathlib import Path
import json

# 準備批次查詢配置
batch_config = [
    {
        "stock_code": "2330",
        "company_name": "台積電",
        "year": 2024,
        "season": "Q1"
    }
]

# 執行批次處理
from main import process_batch_file
results = process_batch_file(batch_config)
```

### 輸出格式

#### 財務報告 JSON 結構

```json
{
  "stock_code": "2330",
  "company_name": "台積電", 
  "year": 2024,
  "season": "Q1",
  "created_at": "2024-01-15T10:30:00",
  "metadata": {
    "source": "doc.twse.com.tw",
    "file_name": "202401_2330_AI1.pdf",
    "file_size": 1234567,
    "processing_engine": "pdfplumber",
    "ocr_used": false
  },
  "financial_data": {
    "balance_sheet": {
      "現金及銀行存款": 2373616720,
      "應收票據及帳款": 234443474,
      "存貨": 456789012
    },
    "income_statement": {
      "營業收入": 43655565,
      "營業成本": 32100000,
      "稅後淨利": 24855000,
      "基本每股盈餘": 13.95
    },
    "cash_flow": {
      "營業活動現金流量": 15000000,
      "投資活動現金流量": -8000000,
      "融資活動現金流量": -3000000
    }
  },
  "validation_results": {
    "passed": true,
    "warnings": [],
    "errors": []
  }
}
```

## 📦 進階腳本使用

### 財報爬蟲腳本

```bash
# 下載特定公司財報
uv run python scripts/financial_crawler.py \
  --stock-code 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1

# 批次下載多家公司
uv run python scripts/financial_crawler.py \
  --batch examples/semiconductor_batch.json
```

### 智慧處理器腳本

```bash
# 進階財務數據分析
uv run python scripts/smart_processor.py \
  --input data/financial_reports/ \
  --output data/processed/ \
  --enhanced

# 處理特定檔案
uv run python scripts/smart_processor.py \
  --pdf 202401_2330_AI1.pdf \
  --analysis-level advanced
```

### 數據回填腳本

```bash
# 回填指定期間的財報數據
uv run python scripts/financial_backfill.py \
  --start-year 2020 \
  --end-year 2024 \
  --quarters Q1,Q2,Q3,Q4

# 針對特定公司回填
uv run python scripts/backfill_financial_data.py \
  --stocks 2330,2454,2317 \
  --year 2024
```

## ⚙️ 配置管理

### 主配置檔案 (`config/crawler_config.json`)

```json
{
  "processing": {
    "pdf_engine": "pdfplumber",     // 主要 PDF 處理引擎
    "ocr_engine": "paddleocr",      // OCR 輔助引擎
    "auto_validate": true,          // 自動數據驗證
    "low_memory_mode": false        // 低記憶體模式
  },
  "crawler": {
    "delay": 1.0,                   // 請求間隔 (秒)
    "retries": 3,                   // 重試次數
    "timeout": 30,                  // 請求超時 (秒)
    "user_agent": "FinancialCrawler/2.0"
  },
  "paths": {
    "data_dir": "data",             // 數據目錄
    "output_dir": "data/financial_reports", // 輸出目錄
    "log_dir": "logs"               // 日誌目錄
  }
}
```

### 環境變數支援

```bash
# 日誌等級設定
export LOG_LEVEL=INFO

# 自定義數據目錄
export FINANCIAL_DATA_DIR=/custom/path/data

# OCR 模型快取目錄
export PADDLE_MODEL_DIR=/path/to/models

# 低記憶體模式
export LOW_MEMORY_MODE=true
```

## 🧪 測試與驗證

### 執行測試套件

```bash
# 完整測試套件 - 測試所有核心功能
uv run python tests/test_all.py

# 爬蟲功能專項測試
uv run python tests/test_crawler.py

# PDF 處理器專項測試  
uv run python tests/test_processor.py

# 執行所有測試並顯示覆蓋率
uv run pytest tests/ --cov=src --cov-report=html
```

### 功能驗證檢查清單

- ✅ **配置管理系統** - 依賴注入容器正常運作
- ✅ **PDF 處理引擎** - pdfplumber 文字和表格提取
- ✅ **OCR 輔助功能** - PaddleOCR 圖像文字識別
- ✅ **財務數據驗證** - 數值合理性和完整性檢查
- ✅ **季度邏輯處理** - Q1-Q4 與檔名 01-04 正確對應
- ✅ **批次處理系統** - JSON 配置檔案批次執行
- ✅ **異常處理機制** - 統一錯誤捕獲和回報
- ✅ **進度追蹤功能** - 實時處理狀態監控

## 📊 使用範例與實戰

### 範例 1: 單一財報處理

```bash
# 處理台積電 2024 Q1 財報
uv run python main.py --financial \
  --pdf "data/financial_reports/202401_2330_AI1.pdf" \
  --stock 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1
```

### 範例 2: 批次下載與處理

```bash
# Step 1: 批次下載財報
uv run python scripts/financial_crawler.py \
  --batch examples/semiconductor_batch.json

# Step 2: 批次處理下載的檔案
uv run python main.py --batch data/financial_reports/
```

### 範例 3: 歷史數據回填

```bash
# 回填台積電近 3 年所有季度數據
uv run python scripts/financial_backfill.py \
  --stocks 2330 \
  --start-year 2022 \
  --end-year 2024 \
  --quarters Q1,Q2,Q3,Q4
```

### 範例 4: 自定義批次配置

創建 `custom_batch.json`：

```json
[
  {"stock_code": "2330", "company_name": "台積電", "year": 2024, "season": "Q4"},
  {"stock_code": "2454", "company_name": "聯發科", "year": 2024, "season": "Q4"},
  {"stock_code": "2881", "company_name": "富邦金", "year": 2024, "season": "Q4"}
]
```

執行批次處理：

```bash
uv run python main.py --batch custom_batch.json
```

## 🔧 開發與擴展

### 添加自定義處理器

```python
# custom_processor.py
from src.core import BaseProcessor, ProcessingResult

class CustomAnalysisProcessor(BaseProcessor):
    """自定義財務分析處理器"""
    
    def process(self, input_path, output_path=None):
        try:
            # 實現自定義分析邏輯
            analysis_result = self._perform_custom_analysis(input_path)
            return ProcessingResult.success(analysis_result)
        except Exception as e:
            return ProcessingResult.failure(str(e))
    
    def _perform_custom_analysis(self, input_path):
        # 自定義分析實現
        return {"custom_metric": "calculated_value"}
```

### 註冊新處理器

```python
# 在 app_factory.py 中註冊
from src.core.config import register_service
from custom_processor import CustomAnalysisProcessor

# 註冊自定義處理器
register_service('custom_analysis', CustomAnalysisProcessor())
```

### 自定義配置擴展

```python
# 擴展配置系統
from src.core import get_config

config = get_config()
config.custom_settings = {
    "analysis_threshold": 0.95,
    "enable_advanced_metrics": True
}
```

## 🚨 常見問題解決

### Q: PaddleOCR 初始化很慢？

**A:** 首次使用會下載 AI 模型檔案（約 8MB），請耐心等候。後續使用會快很多。

```bash
# 預先下載模型到指定目錄
export PADDLE_MODEL_DIR=/path/to/models
uv run python -c "import paddleocr; paddleocr.PaddleOCR()"
```

### Q: PDF 處理失敗？

**A:** 確認檔案格式和路徑正確，檢查檔案是否損壞。

```bash
# 使用詳細模式查看錯誤信息
export LOG_LEVEL=DEBUG
uv run python main.py --pdf problematic_file.pdf
```

### Q: 爬蟲被網站阻擋？

**A:** 調整請求間隔和重試策略。

```json
// config/crawler_config.json
{
  "crawler": {
    "delay": 2.0,        // 增加延遲
    "retries": 5,        // 增加重試次數
    "timeout": 60        // 增加超時時間
  }
}
```

### Q: 記憶體使用過高？

**A:** 啟用低記憶體模式或調整批次大小。

```bash
# 方法 1: 環境變數
export LOW_MEMORY_MODE=true

# 方法 2: 分批處理
uv run python main.py --batch small_batch.json
```

## 📈 效能優化建議

- **GPU 加速**: 安裝 CUDA 版本的 PaddleOCR 以加速 OCR 處理
- **並行處理**: 在配置中啟用多執行緒處理模式
- **快取機制**: 使用處理結果快取減少重複計算
- **記憶體優化**: 大量檔案處理時啟用低記憶體模式

## 🤝 貢獻與開發

### 貢獻流程

1. **Fork 專案** - 在 GitHub 上 Fork 此專案
2. **創建分支** - `git checkout -b feature/amazing-feature`
3. **開發功能** - 遵循現有的程式碼風格和架構
4. **執行測試** - 確保所有測試通過
5. **提交變更** - `git commit -m 'Add amazing feature'`
6. **推送分支** - `git push origin feature/amazing-feature`
7. **發起 PR** - 開啟 Pull Request 並描述變更內容

### 開發環境設定

```bash
# 安裝開發依賴
uv sync --group dev

# 程式碼格式檢查
uv run black src/ tests/
uv run flake8 src/ tests/

# 型別檢查
uv run mypy src/
```

## 📄 授權與版權

本專案採用 **MIT 授權條款** - 詳見 [LICENSE](LICENSE) 檔案。

## 🔗 相關資源

- 📚 **[API 參考文檔](docs/API.md)** - 完整 API 使用說明
- 🚀 **[部署指南](docs/DEPLOYMENT.md)** - 生產環境部署配置
- 💻 **[開發指南](docs/DEVELOPMENT.md)** - 開發環境和工具鏈設定
- 📖 **[架構重構指南](docs/REFACTORING_GUIDE.md)** - 系統架構演進說明

## � 支援與回饋

遇到問題或有建議？歡迎透過以下方式聯繫：

- 📧 **提交 Issue** - 回報 Bug 或提出功能請求
- 💬 **參與討論** - 在 Discussion 區域分享經驗和想法
- 🌟 **給予 Star** - 如果專案對您有幫助，請給予 Star 支持

---

**🎯 現代化的財務報告處理解決方案，讓數據分析更簡單、更準確！**

⭐ **如果這個專案對您有幫助，請給予 Star 支持！** ⭐

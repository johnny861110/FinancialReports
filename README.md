# 🏦 財務報告處理工具 v2.0

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![uv](https://img.shields.io/badge/uv-supported-orange.svg)](https://github.com/astral-sh/uv)

台灣證券交易所財務報告智慧處理工具，採用現代化架構設計，支援自動爬取、PDF 解析、OCR 識別和數據結構化。

## ✨ 主要特色

- 🚀 **現代化架構** - 模組化設計，可擴展、易維護
- 📊 **智慧解析** - 支援 pdfplumber 和 PaddleOCR 雙引擎
- 🔄 **自動爬取** - 台股財報自動下載和更新
- 📈 **數據處理** - 財務數據提取和結構化
- 🛡️ **品質驗證** - 內建數據驗證和錯誤處理
- 🎯 **批次處理** - 支援大量檔案批次作業
- 🔧 **依賴注入** - 彈性的服務配置和管理

## 🚀 快速開始

### 環境需求

- **Python 3.9+**
- **UV 套件管理器** (推薦)
- **Windows/Linux/macOS**

### 安裝

```bash
# 1. 克隆專案
git clone <repository-url>
cd FinancialReports

# 2. 安裝 UV (如果尚未安裝)
pip install uv

# 3. 安裝依賴
uv sync

# 4. 驗證安裝
uv run python main.py --info
```

### 基本使用

```bash
# 查看系統資訊
uv run python main.py --info

# 處理單個 PDF 檔案
uv run python main.py --pdf path/to/report.pdf

# 財務報告完整處理
uv run python main.py --financial \
  --pdf report.pdf \
  --stock 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1

# 批次處理目錄中所有 PDF
uv run python main.py --batch pdf_directory/

# 執行架構測試
uv run python test_architecture.py --test

# 執行核心功能測試
uv run python test_core.py
```

## 📁 專案架構

```
FinancialReports/
├── 📄 main.py                    # 主程式入口
├── 🧪 test_architecture.py       # 架構測試
├── 🧪 test_core.py              # 核心功能測試
├── 📋 pyproject.toml             # 專案配置
├── 🔒 uv.lock                   # 依賴鎖定檔
├── 📚 src/                       # 核心程式碼
│   ├── 🏗️ core/                  # 核心模組
│   │   ├── __init__.py          # 基礎類別和介面
│   │   ├── config.py            # 配置管理與依賴注入
│   │   └── exceptions.py        # 統一異常處理
│   ├── 🔧 processors/            # 處理器模組
│   │   ├── pdf_processor.py     # PDF 處理引擎
│   │   └── smart_processor.py   # 智慧財務處理器
│   ├── 📊 tracking/              # 追蹤與監控
│   ├── 🛠️ utils/                 # 工具函數
│   ├── ✅ validators/            # 數據驗證器
│   └── 🏭 app_factory.py         # 應用程式工廠
├── 📜 scripts/                   # 執行腳本
│   ├── financial_crawler.py     # 財報爬蟲
│   ├── financial_backfill.py    # 數據回填
│   └── smart_processor.py       # 智慧處理器
├── ⚙️ config/                    # 配置檔案
│   ├── crawler_config.json      # 爬蟲配置
│   └── xbrl_tags.json          # XBRL 標籤定義
├── 📊 data/                      # 數據目錄
│   ├── financial_reports/       # 原始財報檔案
│   └── processed/               # 處理後數據
├── 📖 docs/                      # 文檔
├── 🧪 tests/                     # 測試檔案
├── 💡 examples/                  # 使用範例
└── 📝 logs/                      # 日誌檔案
```

## 🛠️ 核心功能

### 1. PDF 處理引擎

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
```

### 2. 財務報告爬蟲

```python
from scripts.financial_crawler import main as crawler_main

# 爬取特定公司財報
crawler_main([
    "--stock-code", "2330",
    "--company", "台積電", 
    "--year", "2024",
    "--season", "Q1"
])
```

### 3. 智慧數據處理

```python
from src.processors.smart_processor import SmartFinancialProcessor

processor = SmartFinancialProcessor()
processed_data = processor.process_financial_data(raw_data)
```

### 4. 批次處理

```python
from src.app_factory import setup_application, get_processor

# 設置應用程式
config = setup_application()
processor = get_processor('pdf')

# 批次處理目錄
for pdf_file in pdf_directory.glob("*.pdf"):
    result = processor.process(pdf_file)
    if result.success:
        print(f"✅ {pdf_file.name} 處理完成")
```

## ⚙️ 配置說明

### 基本配置 (`config/crawler_config.json`)

```json
{
  "processing": {
    "pdf_engine": "pdfplumber",
    "ocr_engine": "paddleocr", 
    "auto_validate": true
  },
  "crawler": {
    "delay": 1.0,
    "retries": 3,
    "timeout": 30
  }
}
```

### 環境變數

```bash
# 可選：設置日誌等級
export LOG_LEVEL=INFO

# 可選：設置數據目錄
export DATA_DIR=/path/to/data

# 可選：設置輸出目錄  
export OUTPUT_DIR=/path/to/output
```

## 🧪 測試

### 執行所有測試

```bash
# 架構相容性測試
uv run python test_architecture.py --test

# 核心功能測試
uv run python test_core.py

# 完整測試套件
uv run python run_tests.py
```

### 測試覆蓋範圍

- ✅ 配置管理系統
- ✅ PDF 處理引擎
- ✅ 數據驗證器
- ✅ 財務報告生成
- ✅ 爬蟲功能
- ✅ 異常處理

## 📊 使用範例

### 範例 1: 處理單個財報

```bash
uv run python main.py --financial \
  --pdf "data/financial_reports/202401_2330_AI1.pdf" \
  --stock 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1
```

### 範例 2: 批次爬取多家公司

```bash
# 使用範例配置檔案
uv run python scripts/financial_crawler.py \
  --batch examples/semiconductor_batch.json
```

### 範例 3: 數據回填

```bash
# 回填指定期間的財報數據
uv run python scripts/financial_backfill.py \
  --start-year 2023 \
  --end-year 2024 \
  --companies 2330,2454,2881
```

## 🔧 開發指南

### 擴展處理器

```python
from src.core import BaseProcessor, ProcessingResult

class CustomProcessor(BaseProcessor):
    def process(self, input_path, output_path=None):
        # 實現自定義處理邏輯
        try:
            # 處理邏輯
            result_data = self._custom_processing(input_path)
            return ProcessingResult.success(result_data)
        except Exception as e:
            return ProcessingResult.failure(str(e))
```

### 註冊服務

```python
from src.core.config import register_service

# 註冊自定義服務
register_service('custom_processor', CustomProcessor())
```

### 配置自定義設定

```python
from src.core import get_config

config = get_config()
config.processing.custom_setting = "value"
```

## 📦 依賴說明

### 核心依賴

- **requests** - HTTP 請求處理
- **pandas** - 數據分析和處理
- **pdfplumber** - PDF 文字提取
- **paddleocr** - OCR 文字識別
- **opencv-python** - 圖像處理
- **beautifulsoup4** - HTML 解析

### 開發依賴

- **pytest** - 測試框架
- **black** - 程式碼格式化
- **flake8** - 程式碼檢查

## 🚨 常見問題

### Q: PaddleOCR 初始化慢？
A: 首次使用會下載模型檔案，請耐心等候。可設置 `PADDLE_MODEL_DIR` 環境變數指定模型目錄。

### Q: PDF 處理失敗？
A: 確認檔案格式正確，可嘗試切換 PDF 引擎：`--pdf-engine pdfplumber`

### Q: 爬蟲被阻擋？
A: 調整 `config/crawler_config.json` 中的延遲時間和重試次數。

### Q: 記憶體使用過高？
A: 批次處理時可調整批次大小，或使用 `--low-memory` 模式。

## 📈 效能優化

- **GPU 加速**: 安裝 CUDA 版本的 PaddleOCR
- **並行處理**: 使用 `--parallel` 選項
- **快取機制**: 啟用 `--cache` 減少重複處理
- **記憶體優化**: 使用 `--low-memory` 模式

## 🤝 貢獻指南

1. Fork 專案
2. 創建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 開啟 Pull Request

## 📄 授權條款

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案。

## 🔗 相關連結

- [API 文檔](docs/API.md)
- [部署指南](docs/DEPLOYMENT.md)
- [開發指南](docs/DEVELOPMENT.md)
- [架構文檔](docs/REFACTORING_GUIDE.md)

## 📞 支援與回饋

如有問題或建議，歡迎：
- 📧 提交 Issue
- 💬 參與討論
- 🌟 給予 Star

---

⭐ **如果這個專案對您有幫助，請給予 Star 支持！** ⭐

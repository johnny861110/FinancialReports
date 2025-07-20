# 🚀 財務報告處理工具 - 快速開始指南

歡迎使用財務報告處理工具 v2.0！這份指南將幫助您在 5 分鐘內完成安裝並開始使用。

## 📋 系統需求檢查

### 基本要求

- **作業系統**: Windows 10/11, macOS 10.15+, 或 Linux
- **Python 版本**: 3.9-3.12 (強烈推薦 3.10+ 版本)
- **記憶體**: 至少 4GB RAM（推薦 8GB，OCR 處理需要）
- **磁碟空間**: 2GB 可用空間（包含 AI 模型）
- **網路連線**: 用於下載財報和首次 OCR 模型

### 環境檢查指令

```bash
# 檢查 Python 版本 (應顯示 3.9+ 版本)
python --version

# 檢查 pip 是否可用
pip --version
```

**⚠️ 注意**: 如果沒有 Python，請從 [官網](https://www.python.org/downloads/) 下載安裝。

## ⚡ 3 步驟快速安裝

### 步驟 1: 安裝 UV 套件管理器

```bash
# Windows (PowerShell), macOS, 或 Linux
pip install uv

# 驗證 UV 安裝成功
uv --version
```

**💡 提示**: UV 是現代化的 Python 套件管理器，比 pip 更快更可靠。

### 步驟 2: 取得專案檔案

```bash
# 方法 1: Git 克隆 (推薦)
git clone <your-repository-url>
cd FinancialReports

# 方法 2: 下載壓縮檔
# 下載並解壓縮到本地目錄
cd FinancialReports
```

### 步驟 3: 安裝依賴並驗證

```bash
# 一鍵安裝所有依賴套件 (約需 2-3 分鐘)
uv sync

# 驗證安裝成功 - 應該看到詳細系統資訊
uv run python main.py --info
```

### ✅ 安裝成功確認

如果看到類似以下輸出，表示安裝成功：

```text
============================================================
📊 財務報告處理工具 v2.0
============================================================
📁 工作目錄: /path/to/FinancialReports
� 數據目錄: /path/to/data
�🔧 PDF引擎: pdfplumber
👁️ OCR引擎: paddleocr
🛠️ 可用處理器:
   ✅ PDF處理器 (pdfplumber)
   ✅ 智慧財務處理器
✅ 系統就緒，準備處理財務報告！
============================================================
```

## 🎯 立即開始使用

### 1. 系統功能驗證

```bash
# 檢查所有命令行選項
uv run python main.py --help

# 查看詳細系統狀態
uv run python main.py --info

# 執行測試確認功能正常 (可選)
uv run python tests/test_all.py
```

### 2. 處理現有 PDF 檔案

如果您已有財報 PDF 檔案，可以立即開始：

```bash
# 基本 PDF 文字提取
uv run python main.py --pdf "your_report.pdf"

# 完整財務報告處理（需要股票資訊）
uv run python main.py --financial \
  --pdf "202401_2330_AI1.pdf" \
  --stock 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1
```

### 3. 使用內建範例

專案提供現成的批次查詢範例：

```bash
# 使用半導體產業範例
uv run python main.py --batch examples/semiconductor_batch.json

# 使用基本批次查詢範例  
uv run python main.py --batch examples/batch_query.json
```

## 🗓️ 季度格式重要說明

### 關鍵：季度編號對應

本工具使用特定的季度編號格式，與台股財報檔名規則完全一致：

| 季度 | 命令參數 | 檔案編號 | 範例檔名 |
|------|----------|----------|----------|
| 第一季 | Q1 | 01 | `202401_2330_AI1.pdf` |
| 第二季 | Q2 | 02 | `202402_2330_AI1.pdf` |
| 第三季 | Q3 | 03 | `202403_2330_AI1.pdf` |
| 第四季 | Q4 | 04 | `202404_2330_AI1.pdf` |

**💡 重要**: 使用命令時請用 Q1-Q4，工具會自動轉換為對應的檔案編號 01-04。

### 實際操作範例

```bash
# 處理 2024 年第一季台積電財報
uv run python main.py --financial \
  --pdf "202401_2330_AI1.pdf" \
  --stock 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1

# 處理 2024 年第三季聯發科財報  
uv run python main.py --financial \
  --pdf "202403_2454_AI1.pdf" \
  --stock 2454 \
  --company "聯發科" \
  --year 2024 \
  --season Q3
```

## 📂 重要目錄結構

```text
FinancialReports/
├── 📄 main.py              # 👈 主程式，從這裡開始
├── 📊 data/                # 👈 所有數據存放處
│   ├── financial_reports/  # 下載的原始 PDF 和處理後的 JSON
│   └── processed/          # 進階處理後的結構化數據
├── ⚙️ config/              # 配置檔案 (可自定義行為)
├── 📜 scripts/             # 獨立執行腳本
├── 📋 examples/            # 批次查詢範例檔案
└── 📝 logs/               # 系統運行日誌
```

## 🔧 常用操作指令

### 查看幫助

```bash
# 主程式完整說明
uv run python main.py --help

# 爬蟲腳本說明
uv run python scripts/financial_crawler.py --help
```

### 調整系統配置

編輯 `config/crawler_config.json` 來自定義系統行為：

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

## 🚨 常見初次使用問題

### 問題 1: PaddleOCR 初始化很慢

**原因**: 首次使用需要下載 AI 模型檔案（約 8MB）  
**解決**: 耐心等待，模型只需下載一次，後續使用會很快

### 問題 2: `uv` 命令找不到

**解決**:

```bash
# 重新安裝 UV
pip install --upgrade uv

# 或使用傳統 pip 方式
pip install -r requirements.txt
python main.py --info
```

### 問題 3: 權限錯誤

**解決**:

```bash
# Windows: 以管理員身分執行 PowerShell
# macOS/Linux: 檢查檔案權限
chmod +x scripts/*.py
```

## 🎉 恭喜！您已準備就緒

✅ **太好了！** 您已成功安裝並驗證財務報告處理工具

### 建議後續行動

1. **📖 深入了解**: 閱讀完整的 [README.md](README.md)
2. **🧪 執行測試**: 運行 `uv run python tests/test_all.py`
3. **💡 查看範例**: 研究 `examples/` 目錄中的配置檔案
4. **🔧 自定義設定**: 根據需求調整 `config/` 中的配置

### 立即體驗完整功能

```bash
# 如果您知道特定股票代碼，可以立即下載財報
uv run python scripts/financial_crawler.py \
  --stock-code 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1

# 然後處理下載的檔案
uv run python main.py --financial \
  --pdf data/financial_reports/202401_2330_AI1.pdf \
  --stock 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1
```

## 📞 需要協助嗎

- � **詳細文檔**: [API 使用文檔](docs/API.md)
- 🔧 **開發指南**: [開發環境設定](docs/DEVELOPMENT.md)  
- 🐛 **遇到問題**: 請提交 Issue 回報
- 💡 **改進建議**: 歡迎貢獻程式碼或想法

---

**🎯 5 分鐘完成設置，立即開始智慧化財務報告處理！**

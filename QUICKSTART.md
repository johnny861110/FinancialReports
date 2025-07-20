# 🚀 快速開始指南

歡迎使用財務報告處理工具！這份指南將幫助您在 5 分鐘內開始使用。

## 📋 準備工作

### 系統需求
- Windows 10/11, macOS 10.15+, 或 Linux
- Python 3.9 或更高版本
- 至少 4GB RAM（推薦 8GB）
- 2GB 可用磁碟空間

### 快速檢查
```bash
# 檢查 Python 版本
python --version

# 如果沒有 Python，請從官網下載：https://www.python.org/downloads/
```

## ⚡ 3 步驟安裝

### 步驟 1: 安裝 UV 套件管理器
```bash
# Windows (PowerShell)
pip install uv

# macOS/Linux
pip install uv
```

### 步驟 2: 克隆並進入專案
```bash
git clone <your-repository-url>
cd FinancialReports
```

### 步驟 3: 安裝依賴
```bash
# 一鍵安裝所有依賴
uv sync

# 驗證安裝成功
uv run python main.py --info
```

看到類似下面的輸出表示安裝成功：
```
============================================================
📊 財務報告處理工具 v2.0
============================================================
📁 工作目錄: /path/to/FinancialReports
🔧 PDF引擎: pdfplumber
👁️ OCR引擎: paddleocr
✅ 系統就緒
============================================================
```

## 🎯 第一次使用

### 測試系統功能
```bash
# 執行基本測試，確保一切正常
uv run python test_core.py
```

### 處理範例檔案
如果您有 PDF 財報檔案：
```bash
# 基本 PDF 處理
uv run python main.py --pdf your_report.pdf

# 完整財務報告處理
uv run python main.py --financial \
  --pdf your_report.pdf \
  --stock 2330 \
  --company "公司名稱" \
  --year 2024 \
  --season Q1
```

### 下載財報資料
```bash
# 下載特定公司的最新財報
uv run python scripts/financial_crawler.py \
  --stock-code 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1
```

## 📂 重要目錄說明

```
FinancialReports/
├── 📄 main.py              # 👈 主程式，從這裡開始
├── 📊 data/                # 👈 所有數據存放處
│   ├── financial_reports/  # 下載的原始 PDF 檔案
│   └── processed/          # 處理後的 JSON 數據
├── ⚙️ config/              # 配置檔案
├── 📜 scripts/             # 各種實用腳本
└── 📝 logs/               # 運行日誌
```

## 🔧 常用命令

### 查看幫助
```bash
# 主程式說明
uv run python main.py --help

# 爬蟲說明
uv run python scripts/financial_crawler.py --help
```

### 配置調整
編輯 `config/crawler_config.json` 來調整設定：
```json
{
  "processing": {
    "pdf_engine": "pdfplumber",
    "ocr_engine": "paddleocr"
  },
  "crawler": {
    "delay": 1.0,
    "retries": 3
  }
}
```

## 🚨 常見第一次使用問題

### 問題 1: PaddleOCR 初始化很慢
**原因**: 首次使用需要下載 AI 模型  
**解決**: 耐心等待，模型只需下載一次

### 問題 2: `uv` 命令找不到
**解決**: 
```bash
# 重新安裝 UV
pip install --upgrade uv

# 或使用 pip 方式運行
pip install -r requirements.txt
python main.py --info
```

### 問題 3: 權限錯誤
**解決**:
```bash
# Windows: 以管理員身分運行 PowerShell
# macOS/Linux: 使用 sudo 或檢查檔案權限
chmod +x scripts/*.py
```

## 🎉 成功！下一步做什麼？

✅ **恭喜！** 您已經成功設置財務報告處理工具

### 建議後續行動：

1. **📖 閱讀完整文檔**: 查看主要的 [README.md](README.md)
2. **🧪 執行測試**: `uv run python test_architecture.py --test`
3. **💡 查看範例**: 檢查 `examples/` 目錄中的範例檔案
4. **🔧 自定義配置**: 根據需求調整 `config/` 中的設定

### 立即嘗試：
```bash
# 如果您有台股代碼，可以立即下載財報
uv run python scripts/financial_crawler.py \
  --stock-code 2330 \
  --company "台積電" \
  --year 2024 \
  --season Q1

# 處理下載的檔案
uv run python main.py --batch data/financial_reports/
```

## 📞 需要幫助？

- 📋 查看 [API 文檔](docs/API.md)
- 🔧 查看 [開發指南](docs/DEVELOPMENT.md)  
- 🐛 遇到 Bug？請提交 Issue
- 💡 有建議？歡迎貢獻程式碼

---

**🎯 5 分鐘完成設置，立即開始處理財務報告！**

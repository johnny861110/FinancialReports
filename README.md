# 台灣上市公司財報爬蟲工具 📊

一個簡單易用的台灣上市公司財報自動下載工具，特別針對台灣50（0050）成分股設計。

## ✨ 主要特色

- 🎯 **簡單易用**：只需提供股票代碼和年季，即可自動下載財報
- 📦 **批次處理**：支援一次下載多家公司多個季度的財報
- ✅ **自動驗證**：下載後自動檢查檔案完整性
- 🔍 **智慧搜尋**：可依公司名稱、股票代碼、年份搜尋已下載的財報
- 📋 **統一格式**：所有財報統一儲存為 PDF 格式，並產生結構化 JSON 資料

## 🚀 快速開始

### 1. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 2. 下載單家公司財報

```bash
python financial_crawler.py examples/single_query.json
```

### 3. 批次下載多家公司財報

```bash
python financial_crawler.py examples/batch_query.json
```

### 4. 互動式新手導覽

```bash
python start_here.py
```

## 📁 專案結構

```text
FinancialReports/
├── 📂 data/                    # 財報資料儲存區
│   ├── financial_reports/      # PDF 財報檔案
│   ├── json_data/             # 結構化 JSON 資料
│   └── master_index.json      # 主索引檔案
├── 📂 examples/               # 使用範例
│   ├── single_query.json     # 單筆查詢範例
│   └── batch_query.json      # 批次查詢範例
├── 📂 scripts/                # 輔助腳本
├── 📂 config/                 # 配置檔案
├── 📄 financial_crawler.py    # 主程式
├── 📄 start_here.py          # 新手導覽腳本
└── 📄 test_crawler.py        # 測試腳本
```

## 📖 使用說明

### JSON 輸入格式

**單筆查詢**：

```json
{
  "stock_code": "2330",
  "company_name": "台積電",
  "year": 2024,
  "season": "Q1"
}
```

**批次查詢**：

```json
{
  "queries": [
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
}
```

### 搜尋已下載的財報

```bash
python financial_crawler.py --search "台積電"
python financial_crawler.py --search "2330"
python financial_crawler.py --search "2024"
```

### 檢視下載統計

```bash
python financial_crawler.py --stats
```

## 🛠️ 進階功能

### 自訂輸出目錄

```bash
python financial_crawler.py examples/single_query.json --output-dir custom_folder
```

### 測試模式（不實際下載）

```bash
python financial_crawler.py examples/single_query.json --test
```

### 驗證已下載的檔案

```bash
python test_crawler.py --validate data/financial_reports
```

## ❓ 常見問題

### Q: 如何知道支援哪些公司？

A: 本工具支援所有台灣上市櫃公司，建議先用台灣50成分股測試。

### Q: 下載的檔案儲存在哪裡？

A: 預設儲存在 `data/financial_reports/` 目錄，會依公司和年季自動分類。

### Q: 如何查看已下載的財報清單？

A: 執行 `python financial_crawler.py --stats` 可查看所有已下載的財報統計。

### Q: 下載失敗怎麼辦？

A: 工具會自動重試，如果還是失敗，請檢查網路連線或稍後再試。

## 📊 支援的財報格式

- **PDF 檔案**：原始財報 PDF 檔案
- **JSON 資料**：結構化的財務數據（營收、淨利、資產負債等）
- **主索引**：所有下載記錄的統一索引

## 🔧 系統需求

- Python 3.7+
- 網路連線
- 約 100MB 可用硬碟空間（用於快取）

## 📝 授權說明

本專案僅供學術研究和個人學習使用，請勿用於商業用途。財報資料版權歸原公司所有。

## 🤝 貢獻

歡迎提交 Issue 或 Pull Request 來改善這個專案！

---

**開始使用：** 執行 `python start_here.py` 進行互動式導覽！

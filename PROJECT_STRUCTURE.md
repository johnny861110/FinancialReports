# 📁 專案結構說明

> 🎯 **幫助初次使用者快速了解專案檔案組織**

---

## 🏠 根目錄檔案

| 📄 檔案名稱 | 🎯 用途 | 👤 適用對象 |
|-------------|---------|-------------|
| `README.md` | 專案總覽與安裝說明 | 所有用戶 ⭐ |
| `QUICK_START.md` | 3分鐘快速上手指南 | 新手用戶 ⭐ |
| `USER_GUIDE.md` | 完整使用教學指南 | 新手用戶 ⭐ |
| `NAVIGATION.md` | 文件導覽索引 | 所有用戶 ⭐ |
| `PROJECT_STRUCTURE.md` | 專案結構說明 | 所有用戶 |
| `start_here.py` | 互動式入門示範 | 新手用戶 ⭐ |
| `financial_crawler.py` | 主程式（所有功能入口） | 所有用戶 ⭐ |
| `test_crawler.py` | 系統功能測試 | 所有用戶 |
| `requirements.txt` | Python依賴套件清單 | 開發者 |

---

## 📂 主要目錄結構

### 📊 `data/` - 資料目錄

```
data/
├── 🗂️ master_index.json          # 主索引檔案（所有財報記錄）⭐
├── 💰 financial_reports/         # 正式下載的財報
│   ├── 202401_2330_AI1.pdf      #   PDF財報檔案
│   ├── 202401_2330_AI1.json     #   對應的JSON結構化資料
│   └── debug/                   #   調試記錄（可忽略）
└── 🧪 test_results/              # 測試下載結果
```

### 📝 `examples/` - 使用範例

```
examples/
├── 📄 single_query.json         # 單筆查詢範例 ⭐
├── 📄 batch_query.json          # 批次查詢範例 ⭐
├── 📄 semiconductor_batch_query.json # 半導體公司批次查詢 ⭐
└── 📄 demo_master_index.py      # 主索引功能示範
```

### 🔧 `scripts/` - 工具腳本

```
scripts/
├── 🛠️ rebuild_master_index.py   # 重建主索引工具
├── 🕷️ crawlers/                 # 爬蟲相關工具
│   ├── main.py                 #   爬蟲系統主菜單
│   ├── comprehensive_*.py      #   批次爬蟲工具
│   └── diagnostic_*.py         #   診斷工具
├── 🧪 tests/                    # 測試工具
└── ✅ validation/               # 驗證工具
```

### 📤 `output/` - 輸出目錄

```
output/
└── 📋 query_results_*.json      # 查詢執行結果記錄
```

### 🗄️ `archive/` - 存檔目錄

```
archive/
├── 📄 HOW_TO_CRAWL.md           # 舊版完整使用說明
├── 📄 README.md                # 舊版詳細專案說明  
├── 📄 USAGE_GUIDE.md           # 舊版使用者指南
├── 📄 PROJECT_SUMMARY.md       # 專案摘要
├── 📁 duplicate_files/         # 重複檔案
├── 📁 final_cleanup/           # 最終清理檔案
└── 📊 reports/                 # 專案報告檔案
    ├── CHECKLIST.md           #   使用檢查清單
    ├── CLEANUP_REPORT.md      #   清理報告
    ├── FINAL_COMPLETION.md    #   最終完成報告
    ├── FINAL_SUMMARY.md       #   最終摘要
    ├── PROJECT_CLEANUP_REPORT.md # 專案清理報告
    ├── PROJECT_FINAL_REPORT.md #   專案最終報告
    ├── PROJECT_STATUS.md      #   專案狀態
    ├── PROJECT_STATUS_UPDATE_20250627.md # 狀態更新
    ├── REORGANIZATION_SUMMARY.md # 重組摘要
    ├── SEMICONDUCTOR_DOWNLOAD_REPORT.md # 半導體下載報告
    └── TEST_REPORT_2330_2025Q1.md # 測試報告
```

---

## 🎯 使用路徑建議

### 🆕 **第一次使用者**

1. 📖 閱讀 `README.md` 了解專案
2. 🚀 執行 `python start_here.py` 互動式入門
3. 📋 查看 `QUICK_START.md` 快速指南
4. 📝 修改 `examples/single_query.json` 嘗試下載

### 👨‍💻 **日常使用者**

1. 🔍 `python financial_crawler.py --stats` 查看統計
2. 📥 `python financial_crawler.py examples/single_query.json` 下載財報
3. 🔍 `python financial_crawler.py --search [關鍵字]` 搜尋財報
4. 📊 檢查 `data/financial_reports/` 下載結果

### 🔧 **進階使用者**

1. 📝 修改 `examples/batch_query.json` 批次下載
2. 🛠️ 使用 `scripts/` 目錄下的工具腳本
3. 🧪 執行 `python test_crawler.py` 功能測試

---

## 📁 檔案命名規則

### PDF檔案格式

```
YYYYMM_STOCKCODE_AI1.pdf
例如: 202401_2330_AI1.pdf
說明: 2024年1月台積電(2330)財報
```

### JSON檔案格式

```
YYYYMM_STOCKCODE_AI1.json
例如: 202401_2330_AI1.json
說明: 對應PDF的結構化資料
```

### 季度對應關係

- **Q1** → 01月 (`202401_`)
- **Q2** → 02月 (`202402_`)
- **Q3** → 03月 (`202403_`)
- **Q4** → 04月 (`202404_`)

---

## 💡 重要檔案說明

### 🗂️ `data/master_index.json`

**所有財報的統一索引檔案**
- 記錄每次下載的財報資訊
- 支援搜尋功能的核心檔案
- 自動更新，無需手動維護

### 📄 `examples/single_query.json`

**單筆查詢範例檔案**
```json
{
  "stock_code": "2330",
  "company_name": "台積電",
  "year": 2024,
  "season": "Q1"
}
```

### 📄 `examples/batch_query.json`

**批次查詢範例檔案**
```json
[
  {"stock_code": "2330", "company_name": "台積電", "year": 2024, "season": "Q1"},
  {"stock_code": "2454", "company_name": "聯發科", "year": 2024, "season": "Q1"}
]
```

---

## 🎯 檔案使用頻率

### 📈 **經常使用**

- `financial_crawler.py` - 主程式
- `examples/single_query.json` - 範例修改
- `data/master_index.json` - 查看記錄
- `data/financial_reports/` - 下載結果

### 📊 **偶爾使用**

- `test_crawler.py` - 功能測試
- `examples/batch_query.json` - 批次下載
- `QUICK_START.md` - 查詢用法

### 📚 **參考資料**

- `README.md` - 完整說明
- `USER_GUIDE.md` - 使用指南
- `scripts/` - 工具腳本

---

## 🚀 快速定位

### 🎯 **我想要...**

- **下載財報** → `financial_crawler.py` + `examples/`
- **查看已下載的財報** → `financial_crawler.py --stats`
- **搜尋財報** → `financial_crawler.py --search`
- **學習使用** → `README.md` + `QUICK_START.md`
- **測試功能** → `test_crawler.py`
- **查看下載檔案** → `data/financial_reports/`

---

**📋 專案結構說明**  
**更新**: 2025-06-27 | **狀態**: ✅ 對新手友好
